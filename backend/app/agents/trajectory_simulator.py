import json
import logging
from app.agents.base_agent import BaseAgent
from app.models.schemas import AgentName, AgentEventType, SimulationResult, SIMULATION_TOOL_SCHEMA
from app.services.bedrock_client import bedrock
from app.services.model_router import select_model_id
from app.agents.prompts.simulator import TRAJECTORY_SIMULATOR_SYSTEM, TRAJECTORY_SIMULATOR_PROMPT

logger = logging.getLogger(__name__)


def _extract_json_from_text(text: str) -> str:
    """Extract JSON from text that may be wrapped in markdown code blocks.

    Uses regex for robust extraction instead of fragile string splits.
    Falls back to brace-matching if no markdown fence is found.
    """
    import re
    # Prefer explicit ```json ... ``` or ``` ... ``` blocks (regex handles nested fences)
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        candidate = match.group(1).strip()
        if candidate:
            return candidate

    # Fallback: find first balanced { ... } in the text
    start = text.find("{")
    if start >= 0:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]

    return text


class TrajectorySimulatorAgent(BaseAgent):
    name = AgentName.simulator
    display_name = "Trajectory Simulator"

    async def run(self, input_data: dict, emit) -> dict:
        degree_json = input_data.get("degree")
        scenario_type = input_data.get("scenario_type")
        parameters = input_data.get("parameters", {})
        completed_courses = input_data.get("completed_courses", [])
        current_semester = input_data.get("current_semester", 1)
        policy_violations = input_data.get("policy_violations")

        if policy_violations:
            await emit(self.emit(AgentEventType.start, f"Re-running {scenario_type} simulation to fix policy violations"))
            await emit(self.emit(AgentEventType.thinking, f"Incorporating {len(policy_violations)} policy violation(s) as constraints...", step=1))
        else:
            await emit(self.emit(AgentEventType.start, f"Starting {scenario_type} simulation"))
            await emit(self.emit(AgentEventType.thinking, "Analyzing current degree plan structure...", step=1))

        prompt = TRAJECTORY_SIMULATOR_PROMPT.format(
            degree_json=json.dumps(degree_json, indent=2),
            completed_courses=json.dumps(completed_courses),
            current_semester=current_semester,
            scenario_type=scenario_type,
            parameters=json.dumps(parameters),
        )

        # Append overlap context for add_major/add_minor
        overlap_info = input_data.get("overlap_info")
        if overlap_info:
            prompt += f"""

OVERLAP CONTEXT: This is a combined degree plan. The student is adding "{overlap_info.get('second_degree_name', 'a second program')}".
- {overlap_info.get('shared_credits', 0)} shared credits have been removed (overlap courses already counted)
- {overlap_info.get('additional_courses_count', 0)} additional courses from the second program have been added to the plan
- Schedule the additional courses into available semesters while respecting prerequisites and credit limits"""

        # Append correction context if this is a self-correction iteration
        if policy_violations:
            violation_text = "\n".join(
                f"- [{v['rule']}] {v['detail']} Suggestion: {v.get('suggestion', 'N/A')}"
                for v in policy_violations
            )
            prompt += f"""

IMPORTANT CORRECTION: Your previous simulation produced a schedule that violates these university policies:
{violation_text}

You MUST fix these violations in your revised schedule. Specifically:
- Respect the credit cap per semester
- Ensure all prerequisites are scheduled before their dependent courses
- Ensure total credits meet degree requirements
Produce a corrected schedule that resolves ALL of the above violations."""

        # Append agent memory context if available (cross-session learning)
        memory_context = input_data.get("memory_context")
        if memory_context:
            prompt += f"\n\n{memory_context}"

        # Step 2: Dynamic model routing based on input complexity
        correction_iter = len(policy_violations) if policy_violations else 0
        model_id, routing_info = select_model_id(
            bedrock,
            degree_data=degree_json,
            scenario_type=scenario_type,
            completed_courses=completed_courses,
            correction_iteration=correction_iter,
            has_overlap=bool(input_data.get("overlap_info")),
        )
        await emit(self.emit(
            AgentEventType.thinking,
            f"Routing to Nova {routing_info['model_tier'].title()} "
            f"(complexity: {routing_info['complexity_score']}/100) — "
            f"{routing_info['reason']}",
            step=2,
            data={"model_routing": routing_info},
        ))
        try:
            response = await bedrock.converse_async(
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                system=TRAJECTORY_SIMULATOR_SYSTEM,
                tools=[SIMULATION_TOOL_SCHEMA],
                max_tokens=4096,
                temperature=0.2,
                model_id=model_id,
            )
        except Exception as e:
            await emit(self.emit(AgentEventType.error, f"Nova API error: {e}"))
            return {"error": str(e)}

        # Step 3: Extract structured result — prefer tool-use, fallback to text
        await emit(self.emit(AgentEventType.thinking, "Parsing simulation results...", step=3))

        tool_input = bedrock.extract_tool_use(response)
        if tool_input:
            try:
                result = SimulationResult.model_validate(tool_input)
                await self._emit_success(emit, result)
                return {"result": result.model_dump()}
            except Exception as e:
                logger.warning(f"Tool-use output validation failed, falling back to text: {e}")

        # Fallback: parse text response
        text = bedrock.extract_text_response(response)
        try:
            json_str = _extract_json_from_text(text)
            result_data = json.loads(json_str.strip())
            result = SimulationResult.model_validate(result_data)
            await self._emit_success(emit, result)
            return {"result": result.model_dump()}
        except Exception as e:
            await emit(self.emit(AgentEventType.error, f"Failed to parse simulation result: {e}"))
            return {"error": str(e), "raw_response": text[:500]}

    async def _emit_success(self, emit, result: SimulationResult):
        await emit(self.emit(
            AgentEventType.thinking,
            f"Identified {len(result.affected_courses)} affected courses",
            step=4,
            data={"affected_count": len(result.affected_courses)},
        ))
        await emit(self.emit(AgentEventType.thinking, "Validating degree constraints...", step=5))
        await emit(self.emit(
            AgentEventType.complete,
            f"Simulation complete: {result.semesters_added} semester(s) impact, risk level: {result.risk_level}",
            data={
                "semesters_added": result.semesters_added,
                "risk_level": result.risk_level,
                "affected_courses": len(result.affected_courses),
            },
        ))
