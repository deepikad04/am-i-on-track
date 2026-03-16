import asyncio
import os
import json
import logging
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.db import get_db, async_session
from app.database.models import Session, Degree, User, gen_id
from app.agents.orchestrator import orchestrator
from app.config import UPLOAD_DIR
from app.models.schemas import UploadResponse
from app.services.auth import get_current_user
from pydantic import BaseModel
from app.services.pdf_processor import write_upload
from app.services.url_extractor import extract_text_from_urls

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_PDF_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_CONTENT_TYPES = {
    "application/pdf": "pdf",
    "image/png": "png",
    "image/jpeg": "jpeg",
    "image/jpg": "jpeg",
    "image/webp": "webp",
    "video/mp4": "mp4",
    "video/webm": "webm",
}


def _schedule_embedding_precompute(session_id: str, degree_id: str, degree_data: dict):
    """Schedule embedding precompute as a background task so the SSE stream can close immediately."""
    async def _compute():
        try:
            from app.services.bedrock_client import bedrock
            from app.models.schemas import DegreeRequirement

            deg_req = DegreeRequirement.model_validate(degree_data)
            texts = [
                f"{c.code} {c.name} — {c.category}, {c.credits} credits"
                for c in deg_req.courses
            ]
            vecs = await bedrock.embed_batch_async(texts)
            async with async_session() as db:
                deg = await db.get(Degree, degree_id)
                if deg:
                    deg.embeddings_json = json.dumps(
                        {c.code: v for c, v in zip(deg_req.courses, vecs)}
                    )
                    await db.commit()
                    logger.info(f"Embeddings committed for session {session_id}")
        except Exception as emb_err:
            logger.warning(f"Embedding precompute skipped: {emb_err}")

    asyncio.create_task(_compute())


@router.post("/upload", response_model=UploadResponse)
async def upload_degree_pdf(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a degree PDF, image (PNG/JPEG/WebP), or video screen recording (MP4/WebM) for parsing.

    Supports Nova's full multimodal capability:
    - **PDF**: Document parsing via Nova's document content blocks
    - **Images**: Vision-based analysis of degree audit screenshots and photos
    - **Video**: Screen recording analysis via Nova's video understanding —
      students can record their screen scrolling through their university portal's
      degree audit page and Nova extracts structured course data from the video frames.
    """
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Accepted formats: PDF, PNG, JPEG, WebP, MP4, WebM. Got: {file.content_type}",
        )

    content = await file.read()
    if len(content) > MAX_PDF_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 10 MB limit")

    # Create session linked to user
    session_id = gen_id()
    session = Session(id=session_id, student_name=user.name, user_id=user.id)
    db.add(session)
    await db.flush()

    # Save file (async) — use correct extension for PDFs vs images
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_format = ALLOWED_CONTENT_TYPES[file.content_type]
    file_ext = "pdf" if file_format == "pdf" else file_format
    pdf_path = os.path.join(UPLOAD_DIR, f"{session_id}.{file_ext}")
    await write_upload(pdf_path, content)

    # Create degree record
    degree_id = gen_id()
    degree = Degree(id=degree_id, session_id=session_id, raw_pdf_path=pdf_path, status="pending")
    db.add(degree)
    await db.commit()

    return UploadResponse(session_id=session_id)


@router.get("/upload/{session_id}/parse")
async def parse_degree_stream(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stream the degree parsing process via SSE."""
    # Find the degree record and verify ownership
    result = await db.execute(
        select(Degree).join(Session).where(
            Degree.session_id == session_id,
            Session.user_id == user.id,
        )
    )
    degree = result.scalar_one_or_none()
    if not degree:
        raise HTTPException(status_code=404, detail="Session not found")

    # Capture immutable values before the DI session closes
    degree_id = degree.id
    pdf_path = degree.raw_pdf_path

    # Detect if this is an image or video upload (multimodal) vs PDF
    _IMAGE_EXTS = {".png", ".jpeg", ".jpg", ".webp"}
    _IMAGE_FORMAT_MAP = {".png": "png", ".jpeg": "jpeg", ".jpg": "jpeg", ".webp": "webp"}
    _VIDEO_EXTS = {".mp4", ".webm"}
    _VIDEO_FORMAT_MAP = {".mp4": "mp4", ".webm": "webm"}
    file_ext = os.path.splitext(pdf_path or "")[1].lower() if pdf_path else ""
    is_image = file_ext in _IMAGE_EXTS
    is_video = file_ext in _VIDEO_EXTS

    degree.status = "parsing"
    await db.commit()

    async def event_stream():
        # Use an independent session that outlives FastAPI's DI lifecycle
        async with async_session() as stream_db:
            try:
                if is_video:
                    parse_gen = orchestrator.run_parse(
                        video_path=pdf_path,
                        video_format=_VIDEO_FORMAT_MAP.get(file_ext, "mp4"),
                    )
                elif is_image:
                    parse_gen = orchestrator.run_parse(
                        image_path=pdf_path,
                        image_format=_IMAGE_FORMAT_MAP.get(file_ext, "png"),
                    )
                else:
                    parse_gen = orchestrator.run_parse(pdf_path)
                async for event in parse_gen:
                    if event is None:
                        yield ": heartbeat\n\n"
                        continue

                    logger.info(f"SSE event: type={event.event_type} agent={event.agent} data_keys={list(event.data.keys()) if event.data else None} message={event.message}")

                    # If error event, update degree status
                    if event.event_type == "error":
                        logger.error(f"Agent error for session {session_id}: {event.message}")
                        deg = await stream_db.get(Degree, degree_id)
                        if deg:
                            deg.status = "error"
                            await stream_db.commit()

                    # If complete with degree data, save and commit BEFORE yielding
                    if event.event_type == "complete" and event.data and "degree" in event.data:
                        logger.info(f"Saving degree data for session {session_id}")
                        deg = await stream_db.get(Degree, degree_id)
                        if deg:
                            deg.parsed_json = json.dumps(event.data["degree"])
                            deg.degree_name = event.data["degree"].get("degree_name", "Unknown")
                            deg.status = "parsed"
                            await stream_db.commit()
                            logger.info(f"Degree committed: status={deg.status} session={session_id}")

                    # Yield event to client immediately
                    yield f"data: {event.model_dump_json()}\n\n"

                    # Fire-and-forget: precompute embeddings in background task
                    # so the SSE stream can close and the client isn't blocked
                    if event.event_type == "complete" and event.data and "degree" in event.data:
                        _schedule_embedding_precompute(session_id, degree_id, event.data["degree"])
            except (asyncio.CancelledError, GeneratorExit):
                logger.info(f"Client disconnected during parse stream for session {session_id}")
                raise
            except Exception as e:
                logger.error(f"Parse stream error: {e}")
                try:
                    deg = await stream_db.get(Degree, degree_id)
                    if deg:
                        deg.status = "error"
                        await stream_db.commit()
                except Exception:
                    pass
                from app.models.schemas import AgentEvent, AgentName, AgentEventType
                err_event = AgentEvent(
                    agent=AgentName.interpreter, event_type=AgentEventType.error,
                    message=str(e), timestamp=0,
                )
                yield f"data: {err_event.model_dump_json()}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


class UrlUploadRequest(BaseModel):
    urls: list[str]


@router.post("/upload/url", response_model=UploadResponse)
async def upload_degree_urls(
    request: UrlUploadRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload degree requirements from 1-5 web page URLs."""
    if not request.urls or len(request.urls) > 5:
        raise HTTPException(status_code=400, detail="Provide 1-5 URLs")

    # Create session
    session_id = gen_id()
    session = Session(id=session_id, student_name=user.name, user_id=user.id)
    db.add(session)
    await db.flush()

    # Store URLs in raw_pdf_path as JSON (reusing the field)
    degree_id = gen_id()
    degree = Degree(id=degree_id, session_id=session_id, raw_pdf_path=json.dumps(request.urls), status="pending")
    db.add(degree)
    await db.commit()

    return UploadResponse(session_id=session_id, message="URLs received, parsing started")


@router.get("/upload/{session_id}/parse-url")
async def parse_url_stream(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch URLs, extract text, and stream degree parsing via SSE."""
    result = await db.execute(
        select(Degree).join(Session).where(
            Degree.session_id == session_id,
            Session.user_id == user.id,
        )
    )
    degree = result.scalar_one_or_none()
    if not degree:
        raise HTTPException(status_code=404, detail="Session not found")

    # Capture values before the DI session closes
    degree_id = degree.id
    urls_json = degree.raw_pdf_path
    if not urls_json:
        raise HTTPException(status_code=404, detail="No URLs found for this session")

    try:
        urls = json.loads(urls_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid URL data")

    degree.status = "parsing"
    await db.commit()

    async def event_stream():
        async with async_session() as stream_db:
            try:
                # First extract text from all URLs
                extracted_text = await extract_text_from_urls(urls)

                async for event in orchestrator.run_parse(text=extracted_text):
                    if event is None:
                        yield ": heartbeat\n\n"
                        continue

                    if event.event_type == "error":
                        logger.error(f"Agent error for session {session_id}: {event.message}")
                        deg = await stream_db.get(Degree, degree_id)
                        if deg:
                            deg.status = "error"
                            await stream_db.commit()

                    if event.event_type == "complete" and event.data and "degree" in event.data:
                        deg = await stream_db.get(Degree, degree_id)
                        if deg:
                            deg.parsed_json = json.dumps(event.data["degree"])
                            deg.degree_name = event.data["degree"].get("degree_name", "Unknown")
                            deg.status = "parsed"
                            await stream_db.commit()

                    # Yield event to client immediately
                    yield f"data: {event.model_dump_json()}\n\n"

                    # Fire-and-forget: precompute embeddings in background task
                    if event.event_type == "complete" and event.data and "degree" in event.data:
                        _schedule_embedding_precompute(session_id, degree_id, event.data["degree"])
            except (asyncio.CancelledError, GeneratorExit):
                logger.info(f"Client disconnected during URL parse for session {session_id}")
                raise
            except Exception as e:
                logger.error(f"URL parse stream error: {e}")
                try:
                    deg = await stream_db.get(Degree, degree_id)
                    if deg:
                        deg.status = "error"
                        await stream_db.commit()
                except Exception:
                    pass
                from app.models.schemas import AgentEvent, AgentName, AgentEventType
                err_event = AgentEvent(
                    agent=AgentName.interpreter, event_type=AgentEventType.error,
                    message=str(e), timestamp=0,
                )
                yield f"data: {err_event.model_dump_json()}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
