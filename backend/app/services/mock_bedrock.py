"""Deterministic mock Bedrock client for local demo mode.

Returns pre-built responses that mimic Nova's output format
so the entire SSE pipeline works end-to-end without live AWS credentials.
Activated by setting DEMO_MODE=true in the environment.
"""

import json
import logging

logger = logging.getLogger(__name__)

# --------------- Canned responses for each agent scenario ---------------

_SIMULATION_RESULT = {
    "original_graduation": "Spring 2027",
    "new_graduation": "Fall 2027",
    "semesters_added": 1,
    "affected_courses": [
        {"code": "CS 421", "name": "Programming Languages", "original_semester": 6, "new_semester": 7, "reason": "Prerequisite chain shifted by dropped course"},
        {"code": "CS 461", "name": "Computer Security", "original_semester": 7, "new_semester": 8, "reason": "Moved to balance credit load"},
    ],
    "credit_impact": 6,
    "risk_level": "medium",
    "reasoning_steps": [
        "Identified CS 225 as a critical prerequisite for 4 downstream courses",
        "Cascading delay propagates through CS 374 -> CS 421 chain",
        "Redistributed credits across semesters 6-8 to stay under 18-credit cap",
    ],
    "recommendations": [
        "Consider taking CS 225 in the summer session to recover the lost semester",
        "Register early for CS 374 as it fills quickly",
    ],
    "constraint_checks": [
        {"label": "Credit cap", "passed": True, "severity": "ok", "detail": "All semesters within 18-credit limit"},
        {"label": "Prerequisites", "passed": True, "severity": "ok", "detail": "All prerequisites satisfied"},
    ],
}

_EXPLANATION_TEXT = (
    "Dropping this course creates a ripple effect through your degree plan. "
    "Two courses need to shift to later semesters because they depend on prerequisites "
    "that are now delayed. The overall impact is moderate — you'll likely need one additional "
    "semester, but your per-semester credit load stays manageable. Consider summer courses "
    "to get back on track without overloading any single semester."
)

_POLICY_VIOLATIONS = {
    "violations": []
}

_OVERLAP_RESULT = {
    "exact_matches": [
        {"code": "MATH 241", "name": "Calculus III", "credits": 4},
        {"code": "PHYS 211", "name": "University Physics: Mechanics", "credits": 4},
    ],
    "equivalent_courses": [],
    "shared_prerequisites": ["MATH 231", "MATH 241"],
    "total_shared_credits": 8,
    "additional_courses_needed": [],
    "additional_semesters_estimate": 2,
    "recommendations": [
        "Share MATH and PHYS prerequisites to reduce total coursework",
        "Consider summer sessions for additional major-specific courses",
    ],
}

_FAST_TRACK_PROPOSAL = (
    "FAST TRACK GRADUATION PLAN:\n\n"
    "Semester 5 (18 credits): CS 374, CS 357, STAT 400, CS 498 (special topics), MATH 415, GEN ED\n"
    "Semester 6 (18 credits): CS 421, CS 425, CS 461, CS 440, MATH 463, GEN ED\n"
    "Semester 7 (15 credits): CS 411, CS 498 (senior project), remaining electives\n\n"
    "This plan graduates you in 7 semesters by maximizing every semester at 18 credits. "
    "Risk: high course load with multiple hard CS courses per semester."
)

_SAFE_PATH_PROPOSAL = (
    "SAFE PATH GRADUATION PLAN:\n\n"
    "Semester 5 (15 credits): CS 374, STAT 400, GEN ED, GEN ED, MATH 415\n"
    "Semester 6 (15 credits): CS 421, CS 357, CS 425, GEN ED, elective\n"
    "Semester 7 (15 credits): CS 461, CS 440, CS 411, elective, elective\n"
    "Semester 8 (12 credits): CS 498 (senior project), remaining electives\n\n"
    "This plan keeps a steady 12-15 credit load to protect your GPA. "
    "It adds one semester compared to the aggressive plan but reduces burnout risk."
)

_JURY_VERDICT = {
    "verdict": (
        "BALANCED PLAN:\n\n"
        "Semester 5 (15 credits): CS 374, STAT 400, MATH 415, GEN ED, GEN ED\n"
        "Semester 6 (18 credits): CS 421, CS 357, CS 425, CS 440, elective\n"
        "Semester 7 (15 credits): CS 461, CS 411, CS 498 (senior project), elective\n\n"
        "This compromise front-loads one heavy semester (6) when you've built momentum, "
        "keeps the critical CS 374 early, and finishes in 7 semesters. "
        "Semester 8 is reserved as a safety net if any course needs repeating."
    ),
    "agreement_score": 72,
    "key_agreements": [
        "Both advisors prioritize CS 374 early due to its prerequisite chain",
        "Both agree STAT 400 should be taken in semester 5",
        "Both recommend finishing core CS before electives",
    ],
    "key_disagreements": [
        "Fast Track loads 18 credits in multiple semesters; Safe Path caps at 15",
        "Fast Track skips summer; Safe Path uses semester 8 as buffer",
    ],
    "convergence_path": "Use one heavy semester (18 credits) in semester 6 after building confidence, then ease back to 15 credits.",
    "recommended_strategy": "balanced",
}

_COURSE_EXPLANATION = (
    "CS 225 (Data Structures) is a foundational course in your Computer Science degree. "
    "It covers arrays, linked lists, trees, graphs, and hash tables — concepts used in nearly "
    "every upper-division CS course. Four courses in your plan directly require CS 225 as a "
    "prerequisite: CS 374, CS 421, CS 425, and CS 461. Dropping or delaying this course would "
    "cascade into at least a one-semester delay. Given your current progress, you should prioritize "
    "this course for the earliest available semester."
)

_DEGREE_PARSED = {
    "degree_name": "Computer Science BS",
    "institution": "Demo University",
    "total_credits_required": 128,
    "max_credits_per_semester": 18,
    "courses": [
        {"code": "CS 124", "name": "Intro to CS I", "credits": 3, "prerequisites": [], "category": "Core", "typical_semester": 1, "is_required": True, "available_semesters": ["fall", "spring"]},
        {"code": "CS 128", "name": "Intro to CS II", "credits": 3, "prerequisites": ["CS 124"], "category": "Core", "typical_semester": 2, "is_required": True, "available_semesters": ["fall", "spring"]},
        {"code": "CS 225", "name": "Data Structures", "credits": 4, "prerequisites": ["CS 128"], "category": "Core", "typical_semester": 3, "is_required": True, "available_semesters": ["fall", "spring"]},
        {"code": "CS 374", "name": "Algorithms", "credits": 4, "prerequisites": ["CS 225"], "category": "Core", "typical_semester": 5, "is_required": True, "available_semesters": ["fall", "spring"]},
        {"code": "CS 421", "name": "Programming Languages", "credits": 3, "prerequisites": ["CS 374"], "category": "Core", "typical_semester": 6, "is_required": True, "available_semesters": ["fall"]},
    ],
    "constraints": ["Must complete all Core courses", "Maximum 18 credits per semester"],
}


def _tool_use_response(tool_name: str, tool_input: dict) -> dict:
    """Build a mock Bedrock Converse response containing a tool-use block."""
    return {
        "output": {
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "toolUse": {
                            "toolUseId": "mock-tool-001",
                            "name": tool_name,
                            "input": tool_input,
                        }
                    }
                ],
            }
        },
        "usage": {"inputTokens": 100, "outputTokens": 200},
        "ResponseMetadata": {"RequestId": "mock-request-id"},
    }


def _text_response(text: str) -> dict:
    """Build a mock Bedrock Converse response containing a text block."""
    return {
        "output": {
            "message": {
                "role": "assistant",
                "content": [{"text": text}],
            }
        },
        "usage": {"inputTokens": 100, "outputTokens": 200},
        "ResponseMetadata": {"RequestId": "mock-request-id"},
    }


class MockBedrockClient:
    """Drop-in replacement for BedrockClient that returns deterministic responses.

    Routes requests to the correct canned response by inspecting the tool config
    or system prompt keywords.
    """

    def __init__(self):
        self.model_id = "mock-nova-lite"
        self.pro_model_id = "mock-nova-pro"
        self.embed_model_id = "mock-nova-embed"
        self._call_log: list[dict] = []
        logger.info("MockBedrockClient initialized — DEMO_MODE is active")

    def check_connection(self) -> bool:
        return True

    async def check_connection_async(self) -> bool:
        return True

    def _route_response(self, tools=None, system=None, messages=None, **kwargs):
        """Determine which canned response to return based on request context."""
        tool_names = set()
        if tools:
            for t in tools:
                spec = t.get("toolSpec", {})
                tool_names.add(spec.get("name", ""))

        system_text = (system or "").lower()
        msg_text = ""
        if messages:
            for m in messages:
                for c in m.get("content", []):
                    if isinstance(c, dict) and "text" in c:
                        msg_text += c["text"].lower()

        # Log the call for debugging / assertions in tests
        self._call_log.append({"tools": list(tool_names), "system_hint": system_text[:80]})

        # Route by tool name
        if "submit_simulation_result" in tool_names:
            return _tool_use_response("submit_simulation_result", _SIMULATION_RESULT)
        if "submit_policy_violations" in tool_names:
            return _tool_use_response("submit_policy_violations", _POLICY_VIOLATIONS)
        if "submit_overlap_analysis" in tool_names:
            return _tool_use_response("submit_overlap_analysis", _OVERLAP_RESULT)
        if "submit_jury_verdict" in tool_names:
            return _tool_use_response("submit_jury_verdict", _JURY_VERDICT)
        if "parse_degree_requirements" in tool_names:
            return _tool_use_response("parse_degree_requirements", _DEGREE_PARSED)

        # Route by system prompt content
        if "fast track" in system_text or "aggressive" in system_text:
            return _text_response(_FAST_TRACK_PROPOSAL)
        if "safe" in system_text or "conservative" in system_text:
            return _text_response(_SAFE_PATH_PROPOSAL)
        if "jury" in system_text or "synthesize" in system_text:
            return _tool_use_response("submit_jury_verdict", _JURY_VERDICT)
        if "course advisor" in system_text or "explain this course" in system_text:
            return _text_response(_COURSE_EXPLANATION)
        if "explanation" in system_text or "plain-english" in system_text or "plain english" in system_text:
            return _text_response(_EXPLANATION_TEXT)

        # Route by message content for degree parsing
        if "degree requirements" in msg_text and ("json" in msg_text or "parse" in msg_text):
            return _text_response(json.dumps(_DEGREE_PARSED))

        # Default: return a generic text response
        return _text_response("Mock response — no specific handler matched for this request.")

    def converse(self, messages, system=None, tools=None, max_tokens=4096, temperature=0.3, guardrail=False, model_id=None):
        return self._route_response(tools=tools, system=system, messages=messages)

    async def converse_async(self, messages, system=None, tools=None, max_tokens=4096, temperature=0.3, guardrail=False, model_id=None):
        return self._route_response(tools=tools, system=system, messages=messages)

    def converse_with_document(self, pdf_bytes, prompt, tools=None, max_tokens=4096, guardrail=False):
        return self._route_response(tools=tools, messages=[{"role": "user", "content": [{"text": prompt}]}])

    async def converse_with_document_async(self, pdf_bytes, prompt, tools=None, max_tokens=4096, guardrail=False):
        return self._route_response(tools=tools, messages=[{"role": "user", "content": [{"text": prompt}]}])

    def converse_with_image(self, image_bytes, image_format, prompt, tools=None, max_tokens=4096, guardrail=False):
        """Mock multimodal image analysis — returns degree parsing result."""
        return self._route_response(tools=tools, messages=[{"role": "user", "content": [{"text": prompt}]}])

    async def converse_with_image_async(self, image_bytes, image_format, prompt, tools=None, max_tokens=4096, guardrail=False):
        """Mock async multimodal image analysis."""
        return self._route_response(tools=tools, messages=[{"role": "user", "content": [{"text": prompt}]}])

    def converse_stream(self, messages, system=None, max_tokens=4096, temperature=0.3):
        """Yield deterministic token chunks to mimic streaming."""
        resp = self._route_response(system=system, messages=messages)
        text = self.extract_text_response(resp)
        # Yield ~20 char chunks to simulate streaming
        for i in range(0, len(text), 20):
            yield text[i:i + 20]

    async def converse_stream_async(self, messages, system=None, max_tokens=4096, temperature=0.3, on_chunk=None):
        """Async streaming mock — calls on_chunk synchronously for each token chunk."""
        resp = self._route_response(system=system, messages=messages)
        text = self.extract_text_response(resp)
        for i in range(0, len(text), 20):
            chunk = text[i:i + 20]
            if on_chunk:
                on_chunk(chunk)
        return text

    def embed(self, text: str) -> list[float]:
        """Return a deterministic 384-dim embedding based on text hash."""
        import hashlib
        h = hashlib.sha256(text.encode()).hexdigest()
        # Generate reproducible floats from hash
        vec = []
        for i in range(0, min(len(h), 384 * 2), 2):
            if len(vec) >= 384:
                break
            vec.append((int(h[i:i + 2], 16) - 128) / 128.0)
        # Pad to 384 if needed
        while len(vec) < 384:
            vec.append(0.0)
        return vec[:384]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]

    def generate_image(self, prompt: str, width: int = 1024, height: int = 1024) -> bytes:
        """Mock Canvas — returns a minimal valid 1x1 PNG."""
        # Minimal valid PNG (1x1 pixel, white)
        import base64
        return base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        )

    async def generate_image_async(self, prompt: str, width: int = 1024, height: int = 1024) -> bytes:
        return self.generate_image(prompt, width, height)

    def converse_with_documents(self, pdf_bytes_1, pdf_bytes_2, prompt, tools=None, max_tokens=8192, guardrail=False):
        """Mock multi-document comparison — routes through standard handler."""
        return self._route_response(tools=tools, messages=[{"role": "user", "content": [{"text": prompt}]}])

    async def converse_with_documents_async(self, pdf_bytes_1, pdf_bytes_2, prompt, tools=None, max_tokens=8192, guardrail=False):
        return self.converse_with_documents(pdf_bytes_1, pdf_bytes_2, prompt, tools, max_tokens, guardrail)

    def converse_with_video(self, video_bytes, video_format, prompt, tools=None, max_tokens=8192, guardrail=False):
        """Mock video understanding — returns degree parsing result."""
        return self._route_response(tools=tools, messages=[{"role": "user", "content": [{"text": prompt}]}])

    async def converse_with_video_async(self, video_bytes, video_format, prompt, tools=None, max_tokens=8192, guardrail=False):
        return self.converse_with_video(video_bytes, video_format, prompt, tools, max_tokens, guardrail)

    async def embed_async(self, text: str) -> list[float]:
        return self.embed(text)

    async def embed_batch_async(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]

    def extract_text_response(self, response: dict) -> str:
        output = response.get("output", {})
        message = output.get("message", {})
        for block in message.get("content", []):
            if "text" in block:
                return block["text"]
        return ""

    def extract_tool_use(self, response: dict) -> dict | None:
        output = response.get("output", {})
        message = output.get("message", {})
        for block in message.get("content", []):
            if "toolUse" in block:
                return block["toolUse"].get("input", {})
        return None
