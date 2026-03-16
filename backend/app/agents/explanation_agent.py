import json
import logging
from app.agents.base_agent import BaseAgent
from app.models.schemas import AgentName, AgentEventType
from app.services.bedrock_client import bedrock
from app.agents.prompts.explanation import EXPLANATION_SYSTEM, EXPLANATION_PROMPT

logger = logging.getLogger(__name__)


class ExplanationAgent(BaseAgent):
    name = AgentName.explanation
    display_name = "Explanation Agent"

    async def run(self, input_data: dict, emit) -> dict:
        result_json = input_data.get("simulation_result", {})
        scenario_description = input_data.get("scenario_description", "unknown scenario")

        await emit(self.emit(AgentEventType.start, "Generating plain-English explanation"))

        # Step 1: Format prompt
        await emit(self.emit(AgentEventType.thinking, "Analyzing simulation results...", step=1))

        prompt = EXPLANATION_PROMPT.format(
            result_json=json.dumps(result_json, indent=2),
            scenario_description=scenario_description,
        )

        # Step 2: Call Nova
        await emit(self.emit(AgentEventType.thinking, "Writing student-friendly explanation...", step=2))
        try:
            response = await bedrock.converse_async(
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                system=EXPLANATION_SYSTEM,
                max_tokens=2048,
                temperature=0.5,
            )
        except Exception as e:
            await emit(self.emit(AgentEventType.error, f"Nova API error: {e}"))
            return {"error": str(e)}

        # Step 3: Extract explanation
        explanation = bedrock.extract_text_response(response)
        await emit(self.emit(
            AgentEventType.complete,
            "Explanation generated successfully",
            data={"explanation_length": len(explanation)},
        ))

        return {"explanation": explanation}
