"""Tests for URL extractor utilities and bedrock client helpers."""

import pytest
from app.services.url_extractor import _clean_html, _dedupe_urls


# ============================================================
# URL Extractor — _clean_html
# ============================================================

def test_clean_html_removes_scripts():
    """_clean_html strips script and style tags."""
    html = """
    <html>
    <head><style>body{color:red}</style></head>
    <body>
        <script>alert('xss')</script>
        <nav>Nav content</nav>
        <main><p>Important content here</p></main>
        <footer>Footer</footer>
    </body>
    </html>
    """
    result = _clean_html(html)
    assert "Important content here" in result
    assert "alert" not in result
    assert "Nav content" not in result
    assert "Footer" not in result


def test_clean_html_prefers_main_content():
    """_clean_html extracts from <main> when available."""
    html = """
    <html><body>
        <div>Sidebar junk</div>
        <main><h1>Degree Requirements</h1><p>CS 101 - 3 credits</p></main>
    </body></html>
    """
    result = _clean_html(html)
    assert "Degree Requirements" in result
    assert "CS 101" in result


def test_clean_html_handles_empty():
    """_clean_html handles empty/minimal HTML."""
    result = _clean_html("<html><body></body></html>")
    assert result == ""


# ============================================================
# URL Extractor — _dedupe_urls
# ============================================================

def test_dedupe_urls_removes_fragment_duplicates():
    """Fragment-only duplicates are deduped."""
    urls = [
        "https://catalog.example.com/cs",
        "https://catalog.example.com/cs#requirements",
        "https://catalog.example.com/cs#courses",
        "https://catalog.example.com/math",
    ]
    result = _dedupe_urls(urls)
    assert len(result) == 2
    assert "https://catalog.example.com/cs" in result
    assert "https://catalog.example.com/math" in result


def test_dedupe_urls_preserves_order():
    """Deduplication preserves first-seen order."""
    urls = [
        "https://example.com/b",
        "https://example.com/a",
        "https://example.com/b#section",
    ]
    result = _dedupe_urls(urls)
    assert result == ["https://example.com/b", "https://example.com/a"]


# ============================================================
# BedrockClient helpers — extract_text_response, extract_tool_use
# ============================================================

def test_extract_text_response():
    """extract_text_response pulls text from Converse API response."""
    from app.services.bedrock_client import BedrockClient
    client = BedrockClient.__new__(BedrockClient)

    response = {
        "output": {"message": {"role": "assistant", "content": [{"text": "Hello world"}]}},
    }
    assert client.extract_text_response(response) == "Hello world"


def test_extract_text_response_empty():
    """extract_text_response returns empty string when no text block."""
    from app.services.bedrock_client import BedrockClient
    client = BedrockClient.__new__(BedrockClient)

    response = {"output": {"message": {"role": "assistant", "content": []}}}
    assert client.extract_text_response(response) == ""


def test_extract_tool_use():
    """extract_tool_use pulls tool input from Converse API response."""
    from app.services.bedrock_client import BedrockClient
    client = BedrockClient.__new__(BedrockClient)

    response = {
        "output": {"message": {"role": "assistant", "content": [
            {"toolUse": {"toolUseId": "t1", "name": "parse", "input": {"key": "value"}}}
        ]}},
    }
    assert client.extract_tool_use(response) == {"key": "value"}


def test_extract_tool_use_none():
    """extract_tool_use returns None when no tool use in response."""
    from app.services.bedrock_client import BedrockClient
    client = BedrockClient.__new__(BedrockClient)

    response = {"output": {"message": {"role": "assistant", "content": [{"text": "just text"}]}}}
    assert client.extract_tool_use(response) is None
