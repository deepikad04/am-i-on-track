"""Extract text content from university web pages for degree parsing."""

import asyncio
import logging
from urllib.parse import urldefrag

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_TIMEOUT = 20  # seconds per request
_MAX_URLS = 5
_MAX_TEXT_LENGTH = 50_000  # characters — keeps Nova prompt reasonable
_RETRY_DELAY = 2  # seconds between retries for 202 responses
_MAX_RETRIES = 3

# Browser-like User-Agent so university sites serve full HTML
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Some catalog systems have a print-friendly URL variant
_PRINT_SUFFIXES = ["&print", "?print"]


def _clean_html(html: str) -> str:
    """Extract readable text from HTML, stripping nav/footer/script noise."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove non-content elements
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "iframe", "noscript"]):
        tag.decompose()

    # Try to find main content area first (common patterns)
    main = (
        soup.find("main")
        or soup.find("div", {"id": "main-content"})
        or soup.find("div", {"id": "content"})
        or soup.find("div", {"role": "main"})
        or soup.find("article")
        or soup
    )

    text = main.get_text(separator="\n", strip=True)

    # Collapse excessive blank lines
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def _dedupe_urls(urls: list[str]) -> list[str]:
    """Remove fragment-only duplicates (same base URL with different #anchors)."""
    seen: set[str] = set()
    deduped: list[str] = []
    for url in urls:
        base, _ = urldefrag(url)
        if base not in seen:
            seen.add(base)
            deduped.append(base)
    return deduped


async def _fetch_with_retry(client: httpx.AsyncClient, url: str) -> httpx.Response | None:
    """Fetch a URL, retrying on HTTP 202 (common with JS-heavy catalog systems)."""
    for attempt in range(_MAX_RETRIES):
        response = await client.get(url)
        if response.status_code == 202:
            logger.info(f"Got 202 for {url}, retrying in {_RETRY_DELAY}s (attempt {attempt + 1})")
            await asyncio.sleep(_RETRY_DELAY)
            continue
        response.raise_for_status()
        return response
    # Last attempt was still 202 — return it anyway
    return response


async def extract_text_from_urls(urls: list[str]) -> str:
    """Fetch 1-5 URLs and return combined extracted text."""
    if len(urls) > _MAX_URLS:
        raise ValueError(f"Maximum {_MAX_URLS} URLs allowed")

    # Deduplicate URLs that differ only by fragment
    urls = _dedupe_urls(urls)
    logger.info(f"Fetching {len(urls)} unique URL(s)")

    parts: list[str] = []

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=_TIMEOUT,
        headers={"User-Agent": _USER_AGENT},
    ) as client:
        for i, url in enumerate(urls):
            try:
                response = await _fetch_with_retry(client, url)
                if response is None:
                    logger.warning(f"No response from {url}")
                    parts.append(f"--- PAGE {i + 1}: {url} ---\n[No response]")
                    continue

                text = _clean_html(response.text)

                # If no text extracted, try print-friendly variant
                if not text:
                    for suffix in _PRINT_SUFFIXES:
                        print_url = url + suffix
                        try:
                            pr = await _fetch_with_retry(client, print_url)
                            if pr:
                                text = _clean_html(pr.text)
                                if text:
                                    logger.info(f"Got text from print URL: {print_url}")
                                    break
                        except Exception:
                            continue

                if text:
                    parts.append(f"--- PAGE {i + 1}: {url} ---\n{text}")
                    logger.info(f"Extracted {len(text)} chars from {url}")
                else:
                    logger.warning(f"No text extracted from {url} (page may require JavaScript)")
                    parts.append(
                        f"--- PAGE {i + 1}: {url} ---\n"
                        "[Page returned no extractable text — it may require JavaScript to render. "
                        "Try uploading a PDF instead.]"
                    )
            except Exception as e:
                logger.warning(f"Failed to fetch {url}: {e}")
                parts.append(f"--- PAGE {i + 1}: {url} ---\n[Failed to fetch: {e}]")

    combined = "\n\n".join(parts)

    # Truncate if too long
    if len(combined) > _MAX_TEXT_LENGTH:
        combined = combined[:_MAX_TEXT_LENGTH] + "\n\n[Content truncated — exceeded character limit]"

    return combined
