"""Dynamic Model Router — complexity-aware Nova model selection.

Instead of static Pro/Lite assignment per agent, this router analyzes
the actual input to determine complexity and selects the optimal model.
This is a genuine routing decision, not a lookup table.

Complexity signals:
- Course count: more courses = more constraint interactions
- Prerequisite depth: deeper chains = more reasoning required
- Scenario type: some scenarios inherently need more reasoning
- Correction iteration: re-runs after policy failure need stronger model
- Overlap presence: dual-degree adds combinatorial complexity

Routing thresholds:
- score < 30: Nova Lite (fast, cheap, sufficient for simple tasks)
- score >= 30: Nova Pro (deeper reasoning for complex constraint solving)
"""

import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


def compute_complexity_score(
    degree_data: dict | None = None,
    scenario_type: str | None = None,
    completed_courses: list[str] | None = None,
    correction_iteration: int = 0,
    has_overlap: bool = False,
    memory_pattern_count: int = 0,
) -> dict:
    """Compute a 0-100 complexity score from input signals.

    Returns a dict with the score, the selected model tier, and a breakdown
    of contributing factors (visible in SSE events for transparency).
    """
    score = 0
    factors = []

    # --- Factor 1: Course count (0-20) ---
    if degree_data:
        course_count = len(degree_data.get("courses", []))
        if course_count > 40:
            pts = 20
            factors.append(f"{course_count} courses (very large catalog)")
        elif course_count > 25:
            pts = 12
            factors.append(f"{course_count} courses (large catalog)")
        elif course_count > 15:
            pts = 6
            factors.append(f"{course_count} courses (medium catalog)")
        else:
            pts = 0
            factors.append(f"{course_count} courses (small catalog)")
        score += pts

    # --- Factor 2: Prerequisite chain depth (0-25) ---
    if degree_data:
        courses = degree_data.get("courses", [])
        course_codes = {c["code"] for c in courses if isinstance(c, dict)}
        adj = defaultdict(list)
        for c in courses:
            if isinstance(c, dict):
                for pre in c.get("prerequisites", []):
                    if pre in course_codes:
                        adj[pre].append(c["code"])

        def _max_depth(code, visited=None):
            if visited is None:
                visited = set()
            if code in visited:
                return 0
            visited.add(code)
            if not adj[code]:
                return 0
            return 1 + max(_max_depth(child, visited) for child in adj[code])

        max_depth = max((_max_depth(code) for code in course_codes), default=0)
        if max_depth >= 5:
            pts = 25
        elif max_depth >= 3:
            pts = 15
        elif max_depth >= 2:
            pts = 8
        else:
            pts = 0
        score += pts
        factors.append(f"prerequisite depth {max_depth}")

    # --- Factor 3: Scenario complexity (0-20) ---
    scenario_weights = {
        "drop_course": 10,      # moderate — cascading effects
        "block_semester": 12,   # harder — must redistribute
        "add_major": 20,        # hardest — combinatorial explosion
        "add_minor": 15,        # hard — dual constraint sets
        "set_goal": 8,          # moderate
        "study_abroad": 12,     # blocks + redistribution
        "coop": 10,             # similar to block
        "gap_semester": 10,     # similar to block
    }
    if scenario_type:
        pts = scenario_weights.get(scenario_type, 5)
        score += pts
        factors.append(f"scenario={scenario_type} (weight {pts})")

    # --- Factor 4: Correction iteration (0-15) ---
    if correction_iteration > 0:
        pts = min(15, correction_iteration * 8)
        score += pts
        factors.append(f"correction iteration {correction_iteration} — needs stronger reasoning")

    # --- Factor 5: Overlap / dual-degree (0-10) ---
    if has_overlap:
        score += 10
        factors.append("dual-degree overlap active")

    # --- Factor 6: Completion ratio pressure (0-10) ---
    if degree_data and completed_courses is not None:
        total_courses = len(degree_data.get("courses", []))
        completed_count = len(completed_courses)
        if total_courses > 0:
            ratio = completed_count / total_courses
            if ratio > 0.7:
                # Near graduation — small errors matter more
                pts = 10
                factors.append(f"{ratio:.0%} complete — near-graduation precision needed")
                score += pts

    # Clamp to 100
    score = min(100, score)

    # Route decision
    if score >= 30:
        model_tier = "pro"
        reason = "Complex input — routing to Nova Pro for deeper reasoning"
    else:
        model_tier = "lite"
        reason = "Straightforward input — routing to Nova Lite for speed"

    result = {
        "complexity_score": score,
        "model_tier": model_tier,
        "reason": reason,
        "factors": factors,
    }

    logger.info(f"Model router | score={score} tier={model_tier} factors={factors}")
    return result


def select_model_id(
    bedrock_client,
    degree_data: dict | None = None,
    scenario_type: str | None = None,
    completed_courses: list[str] | None = None,
    correction_iteration: int = 0,
    has_overlap: bool = False,
) -> tuple[str, dict]:
    """Convenience: compute complexity and return (model_id, routing_info).

    Returns the actual model ID string from the bedrock client,
    plus the full routing breakdown for SSE transparency.
    """
    routing = compute_complexity_score(
        degree_data=degree_data,
        scenario_type=scenario_type,
        completed_courses=completed_courses,
        correction_iteration=correction_iteration,
        has_overlap=has_overlap,
    )

    if routing["model_tier"] == "pro":
        model_id = bedrock_client.pro_model_id
    else:
        model_id = bedrock_client.model_id

    return model_id, routing
