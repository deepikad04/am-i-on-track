import logging
from app.agents.base_agent import BaseAgent
from app.models.schemas import AgentName, AgentEventType
from app.services.bedrock_client import bedrock

logger = logging.getLogger(__name__)

JURY_SYSTEM = """You are the Jury Agent — a senior academic advisor who synthesizes two opposing strategies into one optimal plan.

You receive:
1. A "Fast Track" proposal (aggressive, minimize semesters)
2. A "Safe Path" proposal (conservative, protect GPA)

Your job:
- Identify the BEST ideas from each proposal
- Resolve conflicts by prioritizing student success
- Produce a single, concrete semester-by-semester plan
- Flag any remaining risks with mitigation strategies
- Keep it to 3-4 short paragraphs with specific course codes

Additionally, provide a convergence assessment:
- agreement_score: 0-100 (how much the two proposals align, 100 = fully agree)
- key_agreements: list of specific points both advisors agree on
- key_disagreements: list of specific points they disagree on
- convergence_path: how to resolve remaining disagreements"""

JURY_PROMPT = """Synthesize these two advisor proposals into one optimal graduation plan.

--- FAST TRACK PROPOSAL ---
{fast_proposal}

--- SAFE PATH PROPOSAL ---
{safe_proposal}

Student context:
Degree: {degree_name}
Completed: {completed_courses}
Current semester: {current_semester}

Create a balanced plan that takes the best of both approaches. Be specific about which courses go in which semesters."""


JURY_CONVERGENCE_TOOL_SCHEMA = {
    "toolSpec": {
        "name": "submit_jury_verdict",
        "description": "Submit the jury's synthesized verdict with convergence analysis",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "verdict": {"type": "string", "description": "The synthesized semester-by-semester plan"},
                    "agreement_score": {"type": "integer", "description": "0-100 score of how aligned the two proposals are"},
                    "key_agreements": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Points both advisors agree on"
                    },
                    "key_disagreements": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Points the advisors disagree on"
                    },
                    "convergence_path": {"type": "string", "description": "How to resolve remaining disagreements"},
                    "recommended_strategy": {
                        "type": "string",
                        "enum": ["fast_track", "safe_path", "balanced"],
                        "description": "Which overall strategy the jury recommends"
                    }
                },
                "required": ["verdict", "agreement_score", "key_agreements", "key_disagreements", "convergence_path", "recommended_strategy"]
            }
        }
    }
}


class JuryAgent(BaseAgent):
    """Reconciles Fast Track and Safe Path into a final balanced plan."""
    name = AgentName.jury
    display_name = "Jury Agent"

    async def run(self, input_data: dict, emit) -> dict:
        await emit(self.emit(AgentEventType.start, "Jury agent deliberating..."))
        await emit(self.emit(AgentEventType.thinking, "Weighing both proposals...", step=1))
        await emit(self.emit(AgentEventType.thinking, "Computing convergence score between proposals...", step=2))

        prompt = JURY_PROMPT.format(
            fast_proposal=input_data.get("fast_proposal", ""),
            safe_proposal=input_data.get("safe_proposal", ""),
            degree_name=input_data.get("degree_name", "Unknown"),
            completed_courses=input_data.get("completed_courses", "None"),
            current_semester=input_data.get("current_semester", 1),
        )

        # Jury always uses Pro — synthesis of competing proposals requires deep reasoning
        await emit(self.emit(
            AgentEventType.thinking,
            "Routing to Nova Pro — multi-proposal synthesis requires maximum reasoning depth",
            step=None,
            data={"model_routing": {"complexity_score": 85, "model_tier": "pro", "reason": "Jury synthesis always uses Pro"}},
        ))
        try:
            response = await bedrock.converse_async(
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                system=JURY_SYSTEM,
                max_tokens=1536,
                temperature=0.4,
                tools=[JURY_CONVERGENCE_TOOL_SCHEMA],
                model_id=bedrock.pro_model_id,
            )
        except Exception as e:
            await emit(self.emit(AgentEventType.error, f"Nova API error: {e}"))
            return {"error": str(e)}

        tool_result = bedrock.extract_tool_use(response)
        text_verdict = bedrock.extract_text_response(response)

        if tool_result:
            result = {
                "verdict": tool_result.get("verdict", text_verdict),
                "strategy": tool_result.get("recommended_strategy", "balanced"),
                "agreement_score": tool_result.get("agreement_score", 50),
                "key_agreements": tool_result.get("key_agreements", []),
                "key_disagreements": tool_result.get("key_disagreements", []),
                "convergence_path": tool_result.get("convergence_path", ""),
            }
        else:
            result = {
                "verdict": text_verdict,
                "strategy": "balanced",
                "agreement_score": 50,
                "key_agreements": [],
                "key_disagreements": [],
                "convergence_path": "",
            }

        await emit(self.emit(
            AgentEventType.complete,
            "Final recommendation ready",
            data=result,
        ))
        return result
