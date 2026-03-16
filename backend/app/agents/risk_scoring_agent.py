"""Risk Scoring Agent — computes a deterministic 0-100 graduation risk score.

This agent uses NO LLM calls. It analyzes the degree plan structure using
quantifiable signals: prerequisite chain depth, credit load distribution,
bottleneck density, and completion velocity. The result is a numeric risk
score that feeds into the Impact Report.

Risk score breakdown (100 = highest risk):
- Prerequisite chain depth:    0-25 pts (deeper chains = more fragile)
- Credit load variance:        0-20 pts (uneven loads = burnout risk)
- Bottleneck density:          0-20 pts (more bottlenecks = more fragile)
- Completion velocity:         0-20 pts (behind pace = at risk)
- Remaining semesters ratio:   0-15 pts (too many remaining = risk)
"""

import logging
import math
from collections import defaultdict
from app.agents.base_agent import BaseAgent
from app.models.schemas import AgentName, AgentEventType

logger = logging.getLogger(__name__)


def compute_risk_score(
    course_nodes: list[dict],
    degree_data: dict,
    completed_courses: list[str],
    current_semester: int,
    memory_bottlenecks: list[dict] | None = None,
) -> dict:
    """Compute a 0-100 graduation risk score from degree plan structure.

    Returns a dict with the overall score and per-factor breakdown.
    memory_bottlenecks: learned from prior sessions via agent memory feedback loop.
    """
    completed_set = set(completed_courses)
    remaining_nodes = [n for n in course_nodes if n.get("status") != "completed"]
    total_credits = degree_data.get("total_credits_required", 120)
    max_credits_per_sem = degree_data.get("max_credits_per_semester", 18)

    courses = degree_data.get("courses", [])
    course_map = {c["code"]: c for c in courses if isinstance(c, dict)}

    # --- Factor 1: Prerequisite chain depth (0-25) ---
    # Longest remaining prerequisite chain. Deeper = more fragile.
    adj = defaultdict(list)
    for c in courses:
        if isinstance(c, dict):
            for pre in c.get("prerequisites", []):
                if pre in course_map:
                    adj[pre].append(c["code"])

    def _chain_depth(code, visited=None):
        if visited is None:
            visited = set()
        if code in visited:
            return 0
        visited.add(code)
        if not adj[code]:
            return 0
        return 1 + max(_chain_depth(child, visited) for child in adj[code])

    remaining_codes = {n["code"] for n in remaining_nodes}
    max_depth = 0
    for code in remaining_codes:
        depth = _chain_depth(code)
        if depth > max_depth:
            max_depth = depth

    # 0 depth = 0 pts, 6+ depth = 25 pts
    chain_score = min(25, round(max_depth * 25 / 6))

    # --- Factor 2: Credit load variance (0-20) ---
    # High variance in per-semester credits = burnout risk.
    sem_credits = defaultdict(int)
    for n in remaining_nodes:
        sem_credits[n["semester"]] += n.get("credits", 3)

    if len(sem_credits) > 1:
        values = list(sem_credits.values())
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = math.sqrt(variance)
        # std_dev of 0 = 0 pts, std_dev of 6+ = 20 pts
        variance_score = min(20, round(std_dev * 20 / 6))
    else:
        variance_score = 0

    # --- Factor 3: Bottleneck density (0-20) ---
    # Courses with 3+ dependents that are not yet completed.
    dependents_count = defaultdict(int)
    for c in courses:
        if isinstance(c, dict):
            for pre in c.get("prerequisites", []):
                dependents_count[pre] += 1

    bottlenecks = [
        code for code in remaining_codes
        if dependents_count.get(code, 0) >= 3
    ]
    # 0 bottlenecks = 0 pts, 4+ = 20 pts
    bottleneck_score = min(20, len(bottlenecks) * 5)

    # --- Factor 4: Completion velocity (0-20) ---
    # Are they on pace? Compare expected vs actual completion percentage.
    completed_credits = sum(
        course_map.get(code, {}).get("credits", 3)
        for code in completed_set
        if code in course_map
    )
    completion_pct = (completed_credits / total_credits * 100) if total_credits > 0 else 0

    # Expected pace: linear over 8 semesters (4 years)
    expected_pct = min(100, (current_semester - 1) / 8 * 100) if current_semester > 1 else 0
    pace_gap = max(0, expected_pct - completion_pct)
    # 0% behind = 0 pts, 40%+ behind = 20 pts
    velocity_score = min(20, round(pace_gap * 20 / 40))

    # --- Factor 5: Remaining semesters ratio (0-15) ---
    # How many semesters left vs the 8-semester norm?
    if remaining_nodes:
        max_sem = max(n["semester"] for n in remaining_nodes)
        remaining_sems = max_sem - current_semester + 1
    else:
        remaining_sems = 0

    # 1-4 remaining = low risk, 8+ = high risk
    if remaining_sems <= 4:
        timeline_score = 0
    else:
        timeline_score = min(15, (remaining_sems - 4) * 3)

    # --- Factor 6: Memory-learned bottlenecks (0-10) ---
    # Courses that prior sessions identified as causing cascading delays.
    # This is the active feedback loop: past session outcomes influence current scoring.
    memory_score = 0
    memory_flagged = []
    if memory_bottlenecks:
        for mb in memory_bottlenecks:
            course_code = mb.get("course", "")
            if course_code in remaining_codes:
                memory_flagged.append(course_code)
                # Higher frequency = more confidence in the risk signal
                memory_score += min(3, mb.get("frequency", 1))
        memory_score = min(10, memory_score)

    # --- Overall ---
    overall = chain_score + variance_score + bottleneck_score + velocity_score + timeline_score + memory_score

    # Risk label
    if overall >= 70:
        risk_label = "critical"
    elif overall >= 50:
        risk_label = "high"
    elif overall >= 30:
        risk_label = "medium"
    else:
        risk_label = "low"

    factors = {
        "prerequisite_chain_depth": {"score": chain_score, "max": 25, "detail": f"Longest remaining chain: {max_depth} courses"},
        "credit_load_variance": {"score": variance_score, "max": 20, "detail": f"Std dev of per-semester credits: {std_dev:.1f}" if len(sem_credits) > 1 else "Single semester remaining"},
        "bottleneck_density": {"score": bottleneck_score, "max": 20, "detail": f"{len(bottlenecks)} bottleneck course(s) remaining"},
        "completion_velocity": {"score": velocity_score, "max": 20, "detail": f"{completion_pct:.0f}% complete vs {expected_pct:.0f}% expected at semester {current_semester}"},
        "remaining_timeline": {"score": timeline_score, "max": 15, "detail": f"{remaining_sems} semesters remaining"},
    }

    # Only include memory factor when agent memory contributed to the score
    if memory_score > 0:
        factors["memory_learned_risk"] = {
            "score": memory_score,
            "max": 10,
            "detail": f"{len(memory_flagged)} course(s) flagged by prior session learning: {', '.join(memory_flagged[:5])}",
        }

    return {
        "risk_score": overall,
        "risk_label": risk_label,
        "factors": factors,
        "bottleneck_courses": bottlenecks,
        "memory_flagged_courses": memory_flagged,
    }


class RiskScoringAgent(BaseAgent):
    """Deterministic agent that computes a 0-100 graduation risk score.

    Uses NO LLM calls — pure computation from degree plan structure.
    """
    name = AgentName.risk_scoring
    display_name = "Risk Scoring Agent"

    async def run(self, input_data: dict, emit) -> dict:
        await emit(self.emit(AgentEventType.start, "Computing graduation risk score"))

        course_nodes = input_data.get("course_nodes", [])
        degree_data = input_data.get("degree", {})
        completed = input_data.get("completed_courses", [])
        current_sem = input_data.get("current_semester", 1)
        memory_bottlenecks = input_data.get("memory_bottlenecks")

        if memory_bottlenecks:
            await emit(self.emit(
                AgentEventType.thinking,
                f"Incorporating {len(memory_bottlenecks)} learned bottleneck(s) from prior sessions into risk model",
                step=1,
                data={"memory_feedback_active": True, "bottleneck_count": len(memory_bottlenecks)},
            ))
        else:
            await emit(self.emit(AgentEventType.thinking, "Analyzing prerequisite chains and bottlenecks...", step=1))

        result = compute_risk_score(course_nodes, degree_data, completed, current_sem, memory_bottlenecks)

        await emit(self.emit(AgentEventType.thinking, f"Risk score: {result['risk_score']}/100 ({result['risk_label']})", step=2))

        await emit(self.emit(
            AgentEventType.complete,
            f"Risk assessment complete: {result['risk_score']}/100 ({result['risk_label']})",
            data=result,
        ))

        return result
