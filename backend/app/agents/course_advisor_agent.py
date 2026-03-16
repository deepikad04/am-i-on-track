import asyncio
import logging
from app.agents.base_agent import BaseAgent
from app.models.schemas import AgentName, AgentEventType
from app.services.bedrock_client import bedrock
from app.agents.prompts.course_advisor import COURSE_ADVISOR_SYSTEM, COURSE_ADVISOR_PROMPT

logger = logging.getLogger(__name__)


class CourseAdvisorAgent(BaseAgent):
    name = AgentName.advisor
    display_name = "Course Advisor"

    async def run(self, input_data: dict, emit) -> dict:
        course = input_data.get("course", {})
        degree_context = input_data.get("degree_context", {})
        stream_chunks = input_data.get("stream_chunks", False)
        chunk_callback = input_data.get("chunk_callback", None)

        await emit(self.emit(AgentEventType.start, f"Analyzing {course.get('code', 'course')}"))

        await emit(self.emit(AgentEventType.thinking, "Building course context...", step=1))

        prompt = COURSE_ADVISOR_PROMPT.format(
            course_code=course.get("code", ""),
            course_name=course.get("name", ""),
            credits=course.get("credits", 0),
            category=course.get("category", ""),
            semester=course.get("semester", ""),
            status=course.get("status", ""),
            is_required=course.get("is_required", True),
            available_semesters=", ".join(course.get("available_semesters", [])),
            prerequisites=", ".join(course.get("prerequisites", [])) or "None",
            dependents=", ".join(course.get("dependents", [])) or "None",
            degree_name=degree_context.get("degree_name", ""),
            total_credits=degree_context.get("total_credits", 0),
            completed_courses=", ".join(degree_context.get("completed_courses", [])) or "None",
            current_semester=degree_context.get("current_semester", 1),
        )

        await emit(self.emit(AgentEventType.thinking, "Asking Nova for course insight...", step=2))

        try:
            if stream_chunks and chunk_callback:
                # Stream tokens live via converse_stream_async (runs in ThreadPoolExecutor).
                # on_chunk is a sync callback invoked in the worker thread; we bridge
                # chunks back to the async event loop via a thread-safe queue.
                chunk_queue: asyncio.Queue[str | None] = asyncio.Queue()
                loop = asyncio.get_event_loop()

                def on_chunk(chunk: str):
                    loop.call_soon_threadsafe(chunk_queue.put_nowait, chunk)

                async def _stream():
                    return await bedrock.converse_stream_async(
                        messages=[{"role": "user", "content": [{"text": prompt}]}],
                        system=COURSE_ADVISOR_SYSTEM,
                        max_tokens=1024,
                        temperature=0.5,
                        on_chunk=on_chunk,
                    )

                stream_task = asyncio.create_task(_stream())
                explanation = ""
                while not stream_task.done():
                    try:
                        chunk = await asyncio.wait_for(chunk_queue.get(), timeout=0.1)
                        explanation += chunk
                        await chunk_callback(chunk)
                    except asyncio.TimeoutError:
                        continue
                # Drain remaining chunks
                while not chunk_queue.empty():
                    chunk = chunk_queue.get_nowait()
                    explanation += chunk
                    await chunk_callback(chunk)
                # Ensure task completed without error
                explanation = await stream_task
            else:
                response = await bedrock.converse_async(
                    messages=[{"role": "user", "content": [{"text": prompt}]}],
                    system=COURSE_ADVISOR_SYSTEM,
                    max_tokens=1024,
                    temperature=0.5,
                )
                explanation = bedrock.extract_text_response(response)
        except Exception as e:
            await emit(self.emit(AgentEventType.error, f"Nova API error: {e}"))
            return {"error": str(e)}

        await emit(self.emit(
            AgentEventType.complete,
            "Course analysis complete",
            data={"explanation_length": len(explanation)},
        ))

        return {"explanation": explanation}
