import logging
import aiofiles
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from a PDF file using PyPDF2."""
    from PyPDF2 import PdfReader

    reader = PdfReader(pdf_path)
    text_parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_parts.append(text)
    return "\n".join(text_parts)


async def read_file_bytes(file_path: str) -> bytes:
    """Read raw file bytes for sending to Nova content blocks (PDF, image, video)."""
    async with aiofiles.open(file_path, "rb") as f:
        return await f.read()


async def write_upload(path: str, content: bytes) -> None:
    """Write uploaded file content to disk (async)."""
    async with aiofiles.open(path, "wb") as f:
        await f.write(content)
