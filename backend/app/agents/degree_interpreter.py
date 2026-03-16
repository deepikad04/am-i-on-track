import json
import logging
import re
from app.agents.base_agent import BaseAgent
from app.models.schemas import AgentName, AgentEventType, DegreeRequirement, DEGREE_TOOL_SCHEMA
from app.services.bedrock_client import bedrock
from app.services.pdf_processor import extract_text_from_pdf, read_file_bytes
from app.agents.prompts.interpreter import DEGREE_INTERPRETER_SYSTEM, DEGREE_INTERPRETER_PROMPT

logger = logging.getLogger(__name__)

JSON_FALLBACK_PROMPT = """Analyze this degree requirements document and return ONLY a valid JSON object (no markdown, no explanation).

The JSON must have this exact structure:
{
  "degree_name": "string",
  "institution": "string or empty",
  "total_credits_required": integer,
  "max_credits_per_semester": integer,
  "courses": [
    {
      "code": "exact code from document",
      "name": "exact name from document",
      "credits": integer,
      "prerequisites": ["course codes"],
      "category": "Core|Elective|General Education|Math/Science|Major Elective",
      "typical_semester": integer,
      "is_required": boolean,
      "available_semesters": ["fall", "spring"]
    }
  ],
  "constraints": ["string"]
}

Rules:
- Use EXACT course codes and names from the document
- Extract EVERY course — do not skip any
- You MUST return valid JSON only, nothing else"""


def _extract_json(text: str) -> dict | None:
    """Try to extract a JSON object from text that may contain markdown fences."""
    text = text.strip()
    if text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    start = text.find("{")
    if start >= 0:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break
    return None


def _validate_degree(data: dict) -> DegreeRequirement | None:
    """Validate and return a DegreeRequirement if it has courses, else None."""
    try:
        degree = DegreeRequirement.model_validate(data)
        if len(degree.courses) > 0:
            return degree
    except Exception as e:
        logger.warning(f"Validation failed: {e}")
    return None


class DegreeInterpreterAgent(BaseAgent):
    name = AgentName.interpreter
    display_name = "Degree Interpreter"

    async def run(self, input_data: dict, emit) -> dict:
        pdf_path = input_data.get("pdf_path")
        pre_extracted_text = input_data.get("text")
        image_path = input_data.get("image_path")
        image_format = input_data.get("image_format")  # png, jpeg, webp
        video_path = input_data.get("video_path")
        video_format = input_data.get("video_format")  # mp4, webm

        if not pdf_path and not pre_extracted_text and not image_path and not video_path:
            await emit(self.emit(AgentEventType.error, "No PDF, image, video, or text provided"))
            return {"error": "No PDF, image, video, or text provided"}

        await emit(self.emit(AgentEventType.start, "Starting degree requirements extraction"))

        # For pre-extracted text (URL uploads), use text-based parsing
        if pre_extracted_text:
            await emit(self.emit(AgentEventType.thinking, "Processing web page content...", step=1))
            return await self._parse_from_text(pre_extracted_text, emit)

        # For video, use Nova's video understanding capability
        if video_path:
            await emit(self.emit(AgentEventType.thinking, "Processing screen recording...", step=1))
            return await self._parse_from_video(video_path, video_format or "mp4", emit)

        # For images, use Nova's multimodal vision capability
        if image_path:
            await emit(self.emit(AgentEventType.thinking, "Analyzing degree image with Nova vision...", step=1))
            return await self._parse_from_image(image_path, image_format or "png", emit)

        # For PDFs, send the raw PDF directly to Nova (avoids text extraction issues)
        await emit(self.emit(AgentEventType.thinking, "Reading PDF document...", step=1))
        try:
            pdf_bytes = await read_file_bytes(pdf_path)
        except Exception as e:
            await emit(self.emit(AgentEventType.error, f"Failed to read PDF: {e}"))
            return {"error": str(e)}

        # Step 2: Send raw PDF to Nova via document content block
        await emit(self.emit(AgentEventType.thinking, "Sending PDF to Nova for analysis...", step=2))
        try:
            response = await bedrock.converse_with_document_async(
                pdf_bytes=pdf_bytes,
                prompt=JSON_FALLBACK_PROMPT,
                max_tokens=8192,
                guardrail=True,
            )
        except Exception as e:
            logger.warning(f"Direct PDF analysis failed: {e}")
            # Fall back to text extraction
            await emit(self.emit(AgentEventType.thinking, "Falling back to text extraction...", step=2))
            try:
                pdf_text = extract_text_from_pdf(pdf_path)
                if pdf_text.strip():
                    return await self._parse_from_text(pdf_text, emit)
            except Exception:
                pass
            await emit(self.emit(AgentEventType.error, f"PDF analysis failed: {e}"))
            return {"error": str(e)}

        # Step 3: Extract and validate
        await emit(self.emit(AgentEventType.thinking, "Extracting structured degree data...", step=3))
        result = self._extract_result(response)
        if result:
            degree = _validate_degree(result)
            if degree:
                await emit(self.emit(
                    AgentEventType.complete,
                    f"Successfully parsed {degree.degree_name}: {len(degree.courses)} courses extracted",
                    data={"course_count": len(degree.courses), "degree_name": degree.degree_name},
                ))
                return {"degree": degree.model_dump()}

        # Step 4: If direct PDF failed, try text extraction as fallback
        await emit(self.emit(AgentEventType.thinking, "Retrying with text extraction...", step=4))
        try:
            pdf_text = extract_text_from_pdf(pdf_path)
            if pdf_text.strip():
                return await self._parse_from_text(pdf_text, emit)
        except Exception as e:
            logger.warning(f"Text extraction fallback failed: {e}")

        await emit(self.emit(AgentEventType.error, "Failed to parse degree requirements"))
        return {"error": "All parsing methods failed"}

    async def _parse_from_text(self, text: str, emit) -> dict:
        """Parse degree from extracted text using JSON prompt."""
        await emit(self.emit(AgentEventType.thinking, "Analyzing content with Nova...", step=3))
        try:
            prompt = f"{JSON_FALLBACK_PROMPT}\n\n--- DEGREE REQUIREMENTS DOCUMENT ---\n{text}"
            response = await bedrock.converse_async(
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                max_tokens=8192,
                guardrail=True,
            )
            resp_text = bedrock.extract_text_response(response)
            if resp_text:
                parsed = _extract_json(resp_text)
                if parsed:
                    degree = _validate_degree(parsed)
                    if degree:
                        await emit(self.emit(
                            AgentEventType.complete,
                            f"Parsed {degree.degree_name}: {len(degree.courses)} courses",
                            data={"course_count": len(degree.courses), "degree_name": degree.degree_name},
                        ))
                        return {"degree": degree.model_dump()}

            await emit(self.emit(AgentEventType.error, "Could not extract degree data from response"))
            return {"error": "Parsing failed", "raw_response": (resp_text or "")[:500]}
        except Exception as e:
            await emit(self.emit(AgentEventType.error, f"Analysis failed: {e}"))
            return {"error": str(e)}

    async def _parse_from_video(self, video_path: str, video_format: str, emit) -> dict:
        """Parse degree requirements from a screen recording using Nova's video understanding.

        Students can record their screen while scrolling through their university portal's
        degree audit page. Nova analyzes the video frames to extract course data.
        Supports MP4, WebM formats.
        """
        try:
            video_bytes = await read_file_bytes(video_path)  # reuse async file reader
        except Exception as e:
            await emit(self.emit(AgentEventType.error, f"Failed to read video: {e}"))
            return {"error": str(e)}

        await emit(self.emit(AgentEventType.thinking, "Analyzing screen recording with Nova video understanding...", step=2))
        try:
            response = await bedrock.converse_with_video_async(
                video_bytes=video_bytes,
                video_format=video_format,
                prompt=JSON_FALLBACK_PROMPT,
                max_tokens=8192,
                guardrail=True,
            )
        except Exception as e:
            await emit(self.emit(AgentEventType.error, f"Video analysis failed: {e}"))
            return {"error": str(e)}

        await emit(self.emit(AgentEventType.thinking, "Extracting structured degree data from video...", step=3))
        result = self._extract_result(response)
        if result:
            degree = _validate_degree(result)
            if degree:
                await emit(self.emit(
                    AgentEventType.complete,
                    f"Successfully parsed {degree.degree_name} from screen recording: {len(degree.courses)} courses extracted",
                    data={"course_count": len(degree.courses), "degree_name": degree.degree_name, "source": "multimodal_video"},
                ))
                return {"degree": degree.model_dump()}

        await emit(self.emit(AgentEventType.error, "Failed to parse degree requirements from video"))
        return {"error": "Video parsing failed"}

    async def _parse_from_image(self, image_path: str, image_format: str, emit) -> dict:
        """Parse degree requirements from an image using Nova's multimodal vision.

        Supports PNG, JPEG, WebP — enables parsing from screenshots, photos,
        and scanned degree audits without OCR preprocessing.
        """
        try:
            image_bytes = await read_file_bytes(image_path)  # reuse async file reader
        except Exception as e:
            await emit(self.emit(AgentEventType.error, f"Failed to read image: {e}"))
            return {"error": str(e)}

        await emit(self.emit(AgentEventType.thinking, "Sending image to Nova multimodal for analysis...", step=2))
        try:
            response = await bedrock.converse_with_image_async(
                image_bytes=image_bytes,
                image_format=image_format,
                prompt=JSON_FALLBACK_PROMPT,
                max_tokens=8192,
                guardrail=True,
            )
        except Exception as e:
            await emit(self.emit(AgentEventType.error, f"Image analysis failed: {e}"))
            return {"error": str(e)}

        await emit(self.emit(AgentEventType.thinking, "Extracting structured degree data from image...", step=3))
        result = self._extract_result(response)
        if result:
            degree = _validate_degree(result)
            if degree:
                await emit(self.emit(
                    AgentEventType.complete,
                    f"Successfully parsed {degree.degree_name} from image: {len(degree.courses)} courses extracted",
                    data={"course_count": len(degree.courses), "degree_name": degree.degree_name, "source": "multimodal_image"},
                ))
                return {"degree": degree.model_dump()}

        await emit(self.emit(AgentEventType.error, "Failed to parse degree requirements from image"))
        return {"error": "Image parsing failed"}

    def _extract_result(self, response: dict) -> dict | None:
        """Try to extract structured data from a Converse response (tool use or text)."""
        # Try tool use first
        tool_input = bedrock.extract_tool_use(response)
        if tool_input:
            return tool_input

        # Try text response
        text = bedrock.extract_text_response(response)
        if text:
            return _extract_json(text)

        return None
