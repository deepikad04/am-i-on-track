import json
import logging
from pathlib import Path
from app.agents.base_agent import BaseAgent
from app.models.schemas import AgentName, AgentEventType, OVERLAP_TOOL_SCHEMA
from app.services.bedrock_client import bedrock
from app.services.pdf_processor import read_file_bytes
from app.agents.prompts.overlap import OVERLAP_ANALYZER_SYSTEM, OVERLAP_ANALYZER_PROMPT

logger = logging.getLogger(__name__)

MULTI_DOC_PROMPT = """Compare these two degree requirement documents side by side. Identify all overlapping courses, equivalent courses, shared prerequisites, and credit-sharing opportunities for a student pursuing both degrees.

Respond with a JSON object:
{
  "exact_matches": [{"code": "...", "name": "...", "credits": <n>}],
  "equivalent_courses": [{"degree1_code": "...", "degree2_code": "...", "name": "...", "credits": <n>, "similarity_reason": "..."}],
  "shared_prerequisites": ["course_code", ...],
  "total_shared_credits": <n>,
  "additional_courses_needed": [{"code": "...", "name": "...", "credits": <n>, "from_degree": "1|2"}],
  "additional_semesters_estimate": <n>,
  "recommendations": ["...", "..."]
}"""


class OverlapAnalyzerAgent(BaseAgent):
    name = AgentName.overlap
    display_name = "Overlap Analyzer"

    async def run(self, input_data: dict, emit) -> dict:
        degree1 = input_data.get("degree1", {})
        degree2 = input_data.get("degree2", {})
        pdf_path_1 = input_data.get("pdf_path_1")
        pdf_path_2 = input_data.get("pdf_path_2")

        await emit(self.emit(AgentEventType.start, "Starting cross-degree overlap analysis"))

        # Try multi-document comparison when both original uploads are PDFs
        if (pdf_path_1 and pdf_path_2
                and Path(pdf_path_1).suffix.lower() == ".pdf"
                and Path(pdf_path_2).suffix.lower() == ".pdf"
                and Path(pdf_path_1).exists()
                and Path(pdf_path_2).exists()):
            result = await self._run_with_documents(pdf_path_1, pdf_path_2, emit)
            if result and "error" not in result:
                return result
            logger.warning("Multi-document comparison failed, falling back to JSON-based analysis")

        # Fall back to JSON-based analysis
        return await self._run_with_json(degree1, degree2, emit)

    async def _run_with_documents(self, pdf_path_1: str, pdf_path_2: str, emit) -> dict:
        """Compare two raw PDFs using Nova's multi-document Converse capability."""
        await emit(self.emit(AgentEventType.thinking, "Reading both degree PDFs...", step=1))
        try:
            pdf_bytes_1 = await read_file_bytes(pdf_path_1)
            pdf_bytes_2 = await read_file_bytes(pdf_path_2)
        except Exception as e:
            logger.warning(f"Failed to read PDFs for multi-doc comparison: {e}")
            return {"error": str(e)}

        await emit(self.emit(AgentEventType.thinking, "Comparing both PDFs side-by-side with Nova multi-document analysis...", step=2))
        try:
            response = await bedrock.converse_with_documents_async(
                pdf_bytes_1=pdf_bytes_1,
                pdf_bytes_2=pdf_bytes_2,
                prompt=MULTI_DOC_PROMPT,
                tools=[OVERLAP_TOOL_SCHEMA],
                max_tokens=8192,
                guardrail=True,
            )
        except Exception as e:
            logger.warning(f"Multi-document Converse call failed: {e}")
            return {"error": str(e)}

        await emit(self.emit(AgentEventType.thinking, "Processing multi-document overlap results...", step=3))
        result = self._parse_response(response)
        if "error" not in result:
            overlap_data = result["overlap"]
            await emit(self.emit(
                AgentEventType.complete,
                f"Found {overlap_data.get('total_shared_credits', 0)} shared credits (multi-document analysis)",
                data=overlap_data,
            ))
        return result

    async def _run_with_json(self, degree1: dict, degree2: dict, emit) -> dict:
        """Compare two degrees using pre-parsed JSON (fallback path)."""
        # Step 1: Prepare prompt
        await emit(self.emit(AgentEventType.thinking, "Comparing degree structures...", step=1))

        prompt = OVERLAP_ANALYZER_PROMPT.format(
            degree1_json=json.dumps(degree1, indent=2),
            degree2_json=json.dumps(degree2, indent=2),
        )

        # Step 2: Call Nova
        await emit(self.emit(AgentEventType.thinking, "Analyzing course overlaps with Nova...", step=2))
        try:
            response = await bedrock.converse_async(
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                system=OVERLAP_ANALYZER_SYSTEM,
                tools=[OVERLAP_TOOL_SCHEMA],
                max_tokens=4096,
                temperature=0.2,
            )
        except Exception as e:
            await emit(self.emit(AgentEventType.error, f"Nova API error: {e}"))
            return {"error": str(e)}

        # Step 3: Parse response
        await emit(self.emit(AgentEventType.thinking, "Processing overlap results...", step=3))
        result = self._parse_response(response)
        if "error" in result:
            await emit(self.emit(AgentEventType.error, f"Failed to parse overlap result: {result['error']}"))
        else:
            overlap_data = result["overlap"]
            await emit(self.emit(
                AgentEventType.complete,
                f"Found {overlap_data.get('total_shared_credits', 0)} shared credits",
                data=overlap_data,
            ))
        return result

    def _parse_response(self, response: dict) -> dict:
        """Extract overlap data from a Converse response (tool-use or text)."""
        try:
            overlap_data = bedrock.extract_tool_use(response)

            if overlap_data is None:
                import re
                text = bedrock.extract_text_response(response)
                json_str = text
                fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
                if fence_match:
                    json_str = fence_match.group(1).strip()
                else:
                    start = text.find("{")
                    if start >= 0:
                        depth = 0
                        for i in range(start, len(text)):
                            if text[i] == "{":
                                depth += 1
                            elif text[i] == "}":
                                depth -= 1
                                if depth == 0:
                                    json_str = text[start:i + 1]
                                    break
                overlap_data = json.loads(json_str.strip())

            return {"overlap": overlap_data}
        except Exception as e:
            text = bedrock.extract_text_response(response)
            return {"error": str(e), "raw_response": text[:500]}
