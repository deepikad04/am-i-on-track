import logging
from app.agents.base_agent import BaseAgent
from app.models.schemas import AgentName, AgentEventType
from app.services.bedrock_client import bedrock
from app.agents.prompts.debate import (
    FAST_AGENT_SYSTEM, SAFE_AGENT_SYSTEM,
    DEBATE_PROMPT, SAFE_REBUTTAL_PROMPT,
)

logger = logging.getLogger(__name__)


class FastTrackAgent(BaseAgent):
    """Proposes the fastest graduation path, maximizing course load."""
    name = AgentName.debate_fast
    display_name = "Fast Track Advisor"

    async def run(self, input_data: dict, emit) -> dict:
        await emit(self.emit(AgentEventType.start, "Fast Track agent analyzing..."))
        await emit(self.emit(AgentEventType.thinking, "Building aggressive schedule...", step=1))

        prompt = DEBATE_PROMPT.format(**input_data)

        try:
            response = await bedrock.converse_async(
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                system=FAST_AGENT_SYSTEM,
                max_tokens=1536,
                temperature=0.6,
            )
        except Exception as e:
            await emit(self.emit(AgentEventType.error, f"Nova API error: {e}"))
            return {"error": str(e)}

        proposal = bedrock.extract_text_response(response)
        await emit(self.emit(
            AgentEventType.complete,
            "Fast Track proposal ready",
            data={"proposal": proposal, "strategy": "fast"},
        ))
        return {"proposal": proposal, "strategy": "fast"}


class SafePathAgent(BaseAgent):
    """Proposes the safest graduation path, protecting GPA. Rebuts the Fast Track proposal."""
    name = AgentName.debate_safe
    display_name = "Safe Path Advisor"

    async def run(self, input_data: dict, emit) -> dict:
        await emit(self.emit(AgentEventType.start, "Safe Path agent analyzing..."))

        fast_track_proposal = input_data.get("fast_track_proposal")

        if fast_track_proposal:
            # Multi-turn rebuttal: Safe Path references and rebuts the Fast Track proposal
            await emit(self.emit(
                AgentEventType.thinking,
                "Reviewing Fast Track proposal and preparing rebuttal...",
                step=1,
            ))
            prompt = SAFE_REBUTTAL_PROMPT.format(
                fast_track_proposal=fast_track_proposal,
                degree_name=input_data.get("degree_name", "Unknown"),
                total_credits=input_data.get("total_credits", 120),
                completed_courses=input_data.get("completed_courses", "None"),
                current_semester=input_data.get("current_semester", 1),
                remaining_courses=input_data.get("remaining_courses", ""),
            )
        else:
            # Fallback: independent proposal (no Fast Track result available)
            await emit(self.emit(AgentEventType.thinking, "Building balanced schedule...", step=1))
            prompt = DEBATE_PROMPT.format(**input_data)

        try:
            response = await bedrock.converse_async(
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                system=SAFE_AGENT_SYSTEM,
                max_tokens=1536,
                temperature=0.6,
            )
        except Exception as e:
            await emit(self.emit(AgentEventType.error, f"Nova API error: {e}"))
            return {"error": str(e)}

        proposal = bedrock.extract_text_response(response)
        await emit(self.emit(
            AgentEventType.complete,
            "Safe Path rebuttal ready" if fast_track_proposal else "Safe Path proposal ready",
            data={"proposal": proposal, "strategy": "safe"},
        ))
        return {"proposal": proposal, "strategy": "safe"}
