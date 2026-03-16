import json
import logging
from collections import defaultdict
from app.agents.base_agent import BaseAgent
from app.models.schemas import AgentName, AgentEventType, PolicyViolation, POLICY_TOOL_SCHEMA
from app.services.bedrock_client import bedrock
from app.services.model_router import compute_complexity_score
from app.agents.prompts.policy import POLICY_AGENT_SYSTEM, POLICY_AGENT_PROMPT

logger = logging.getLogger(__name__)


class PolicyAgent(BaseAgent):
    """Enforces university rules on a degree plan using both deterministic checks and Nova reasoning."""
    name = AgentName.policy
    display_name = "Policy Agent"

    async def run(self, input_data: dict, emit) -> dict:
        degree = input_data.get("degree", {})
        course_nodes = input_data.get("course_nodes", [])
        completed = input_data.get("completed_courses", [])
        current_sem = input_data.get("current_semester", 1)

        await emit(self.emit(AgentEventType.start, "Starting policy compliance check"))

        violations: list[dict] = []

        # ---- Phase 1: Deterministic rule checks ----
        await emit(self.emit(AgentEventType.thinking, "Checking credit caps per semester...", step=1))

        course_map = {c["code"]: c for c in (degree.get("courses") or []) if isinstance(c, dict)}
        max_credits = degree.get("max_credits_per_semester", 18)

        sem_courses: dict[int, list[str]] = defaultdict(list)
        node_sems: dict[str, int] = {}
        for n in course_nodes:
            if n.get("status") != "completed":
                sem_courses[n["semester"]].append(n["code"])
            node_sems[n["code"]] = n["semester"]

        # Rule 1: Credit cap
        for sem, codes in sem_courses.items():
            total = sum(course_map.get(c, {}).get("credits", 3) for c in codes)
            if total > max_credits:
                violations.append({
                    "rule": "Credit Cap",
                    "severity": "error",
                    "detail": f"Semester {sem} has {total} credits, exceeding the {max_credits}-credit cap.",
                    "affected_courses": codes,
                    "suggestion": f"Move {total - max_credits} credits to a lighter semester.",
                })

        await emit(self.emit(AgentEventType.thinking, "Checking prerequisite ordering...", step=2))

        # Rule 2: Prerequisite ordering
        for n in course_nodes:
            if n.get("status") == "completed":
                continue
            for prereq in n.get("prerequisites", []):
                prereq_sem = node_sems.get(prereq)
                if prereq_sem is not None and prereq_sem >= n["semester"]:
                    violations.append({
                        "rule": "Prerequisite Ordering",
                        "severity": "error",
                        "detail": f"{n['code']} is in semester {n['semester']} but prerequisite {prereq} is in semester {prereq_sem}.",
                        "affected_courses": [n["code"], prereq],
                        "suggestion": f"Schedule {prereq} before semester {n['semester']}.",
                    })

        await emit(self.emit(AgentEventType.thinking, "Checking minimum full-time load...", step=3))

        # Rule 3: Minimum full-time load
        for sem, codes in sem_courses.items():
            total = sum(course_map.get(c, {}).get("credits", 3) for c in codes)
            if 0 < total < 12:
                violations.append({
                    "rule": "Minimum Full-Time Load",
                    "severity": "warning",
                    "detail": f"Semester {sem} has only {total} credits — below the 12-credit full-time threshold.",
                    "affected_courses": codes,
                    "suggestion": "Consider adding electives to maintain full-time status and financial aid eligibility.",
                })

        # Rule 4: Total credits
        total_planned = sum(c.get("credits", 3) for c in (degree.get("courses") or []) if isinstance(c, dict))
        total_required = degree.get("total_credits_required", 120)
        if total_planned < total_required:
            violations.append({
                "rule": "Total Credit Requirement",
                "severity": "error",
                "detail": f"Planned courses total {total_planned} credits but {total_required} are required.",
                "affected_courses": [],
                "suggestion": f"Add {total_required - total_planned} more credits of coursework.",
            })

        await emit(self.emit(AgentEventType.thinking, "Checking safety guardrails...", step=4))

        # Rule 5: Hard credit ceiling (safety guardrail — even if max_credits is misconfigured)
        HARD_CREDIT_CEILING = 21
        for sem, codes in sem_courses.items():
            total = sum(course_map.get(c, {}).get("credits", 3) for c in codes)
            if total > HARD_CREDIT_CEILING:
                violations.append({
                    "rule": "Hard Credit Ceiling",
                    "severity": "error",
                    "detail": f"Semester {sem} has {total} credits — exceeds the absolute maximum of {HARD_CREDIT_CEILING} credits.",
                    "affected_courses": codes,
                    "suggestion": f"No university permits more than {HARD_CREDIT_CEILING} credits in a single semester. Redistribute courses.",
                })

        # Rule 6: Zero-elective warning
        elective_keywords = ("elective", "free elective", "general elective")
        has_electives = any(
            any(kw in (c.get("name", "") or "").lower() for kw in elective_keywords)
            for c in (degree.get("courses") or []) if isinstance(c, dict)
        )
        if not has_electives and total_required >= 120:
            violations.append({
                "rule": "No Electives Detected",
                "severity": "warning",
                "detail": "The degree plan has no elective slots. Most 120+ credit programs require free electives.",
                "affected_courses": [],
                "suggestion": "Verify that the parsed degree includes elective requirements. Missing electives may indicate incomplete parsing.",
            })

        # Rule 7: Excessive semester count
        if sem_courses:
            max_sem = max(sem_courses.keys())
            remaining_sems = max_sem - current_sem + 1
            if remaining_sems > 12:
                violations.append({
                    "rule": "Excessive Timeline",
                    "severity": "warning",
                    "detail": f"Plan spans {remaining_sems} remaining semesters (including summers). This may indicate scheduling inefficiency.",
                    "affected_courses": [],
                    "suggestion": "Consider consolidating courses into fewer semesters or adding summer terms.",
                })

        await emit(self.emit(AgentEventType.thinking, "Consulting Nova for deeper analysis...", step=5))

        # ---- Phase 2: Nova-powered analysis for nuanced checks ----
        sem_plan_lines = []
        for sem in sorted(sem_courses.keys()):
            codes = sem_courses[sem]
            cr = sum(course_map.get(c, {}).get("credits", 3) for c in codes)
            sem_plan_lines.append(f"  Semester {sem} ({cr} cr): {', '.join(codes)}")
        semester_plan_text = "\n".join(sem_plan_lines) or "  (no scheduled courses)"

        prompt = POLICY_AGENT_PROMPT.format(
            degree_name=degree.get("degree_name", "Unknown"),
            total_credits_required=total_required,
            max_credits_per_semester=max_credits,
            completed_courses=", ".join(completed) or "None",
            current_semester=current_sem,
            semester_plan=semester_plan_text,
        )

        # Dynamic model routing — policy benefits from Pro on complex plans
        routing = compute_complexity_score(degree_data=degree, completed_courses=completed)
        policy_model = bedrock.pro_model_id if routing["complexity_score"] >= 30 else bedrock.model_id
        await emit(self.emit(
            AgentEventType.thinking,
            f"Policy check routed to Nova {routing['model_tier'].title()} (complexity {routing['complexity_score']}/100)",
            step=None,
            data={"model_routing": routing},
        ))

        try:
            response = await bedrock.converse_async(
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                system=POLICY_AGENT_SYSTEM,
                tools=[POLICY_TOOL_SCHEMA],
                max_tokens=2048,
                temperature=0.1,
                model_id=policy_model,
            )

            # Prefer structured tool-use output
            tool_result = bedrock.extract_tool_use(response)
            if tool_result is not None:
                nova_violations = tool_result.get("violations", [])
            else:
                # Fall back to regex-based JSON extraction (robust against nested fences)
                import re
                text = bedrock.extract_text_response(response)
                json_str = text
                fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
                if fence_match:
                    json_str = fence_match.group(1).strip()
                else:
                    # Brace-matching fallback for unfenced JSON
                    start = text.find("[")
                    brace_start = text.find("{")
                    if brace_start >= 0 and (start < 0 or brace_start < start):
                        start = brace_start
                    if start >= 0:
                        json_str = text[start:]
                nova_violations = json.loads(json_str.strip())

            if isinstance(nova_violations, list):
                # Deduplicate — only add Nova findings that don't overlap with deterministic checks
                existing_details = {v["detail"] for v in violations}
                for nv in nova_violations:
                    if nv.get("detail") not in existing_details:
                        violations.append(nv)

        except Exception as e:
            logger.warning(f"Nova policy analysis failed (deterministic checks still valid): {e}")

        passed = all(v.get("severity") != "error" for v in violations)
        summary = "All policy checks passed." if passed else f"{sum(1 for v in violations if v.get('severity') == 'error')} policy violation(s) found."

        await emit(self.emit(
            AgentEventType.complete,
            summary,
            data={"violations": violations, "passed": passed, "summary": summary},
        ))

        return {"violations": violations, "passed": passed, "summary": summary}
