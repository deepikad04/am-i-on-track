"""End-to-end integration tests that hit the full FastAPI + SSE pipeline.

These tests use DEMO_MODE to get deterministic responses from MockBedrockClient,
then verify the SSE stream format, agent event sequencing, and data persistence.
Runs with an in-memory SQLite database — no external services needed.
"""

import asyncio
import json
import os
import sys
from unittest.mock import MagicMock, AsyncMock

import pytest
import pytest_asyncio

# --- Environment & mocking setup ---
os.environ["DEMO_MODE"] = "true"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

# Mock external deps before app imports
for mod_name in [
    "boto3", "botocore", "botocore.exceptions", "botocore.config",
    "aiofiles", "pypdf",
]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database.db import engine, async_session, Base
from app.database.models import Session, Degree, User, StudentProgressRecord, gen_id
from app.services.auth import get_current_user


# --- Fixtures ---

_DEMO_DEGREE = {
    "degree_name": "Computer Science BS",
    "institution": "Test University",
    "total_credits_required": 120,
    "max_credits_per_semester": 18,
    "courses": [
        {"code": "CS 101", "name": "Intro to CS", "credits": 3, "prerequisites": [], "category": "Core", "typical_semester": 1, "is_required": True, "available_semesters": ["fall", "spring"]},
        {"code": "CS 201", "name": "Data Structures", "credits": 4, "prerequisites": ["CS 101"], "category": "Core", "typical_semester": 2, "is_required": True, "available_semesters": ["fall", "spring"]},
        {"code": "CS 301", "name": "Algorithms", "credits": 4, "prerequisites": ["CS 201"], "category": "Core", "typical_semester": 3, "is_required": True, "available_semesters": ["fall", "spring"]},
        {"code": "CS 401", "name": "Operating Systems", "credits": 3, "prerequisites": ["CS 301"], "category": "Core", "typical_semester": 4, "is_required": True, "available_semesters": ["fall"]},
        {"code": "MATH 101", "name": "Calculus I", "credits": 4, "prerequisites": [], "category": "Math/Science", "typical_semester": 1, "is_required": True, "available_semesters": ["fall", "spring"]},
        {"code": "MATH 201", "name": "Calculus II", "credits": 4, "prerequisites": ["MATH 101"], "category": "Math/Science", "typical_semester": 2, "is_required": True, "available_semesters": ["fall", "spring"]},
        {"code": "ENG 101", "name": "English Composition", "credits": 3, "prerequisites": [], "category": "General Education", "typical_semester": 1, "is_required": True, "available_semesters": ["fall", "spring"]},
        {"code": "PHYS 101", "name": "Physics I", "credits": 4, "prerequisites": ["MATH 101"], "category": "Math/Science", "typical_semester": 2, "is_required": True, "available_semesters": ["fall", "spring"]},
    ],
    "constraints": ["Must complete all Core courses"],
}

_test_user = User(id="test-user-001", email="test@test.com", name="Test User", password_hash="dummy")


async def _override_get_current_user():
    return _test_user


app.dependency_overrides[get_current_user] = _override_get_current_user


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create tables and seed test data in memory DB before each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        # Create test user
        db.add(User(id="test-user-001", email="test@test.com", name="Test User", password_hash="dummy"))
        await db.flush()

        # Create test session + degree
        session = Session(id="e2e_session", student_name="E2E Student", user_id="test-user-001")
        db.add(session)
        await db.flush()

        degree = Degree(
            id="e2e_degree",
            session_id="e2e_session",
            degree_name="Computer Science BS",
            parsed_json=json.dumps(_DEMO_DEGREE),
            status="parsed",
        )
        db.add(degree)

        # Create demo_session for debate endpoint
        demo_session = Session(id="demo_session", student_name="Demo Student")
        db.add(demo_session)
        await db.flush()
        demo_degree = Degree(
            id="demo_degree",
            session_id="demo_session",
            degree_name="Computer Science BS",
            parsed_json=json.dumps(_DEMO_DEGREE),
            status="parsed",
        )
        db.add(demo_degree)

        await db.commit()

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def _parse_sse_events(raw: str) -> list[dict]:
    """Parse raw SSE text into a list of JSON event dicts."""
    events = []
    for line in raw.split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            payload = line[6:]
            try:
                events.append(json.loads(payload))
            except json.JSONDecodeError:
                pass  # heartbeat comments or malformed lines
    return events


# --- Integration Tests ---

@pytest.mark.asyncio
async def test_simulation_sse_pipeline():
    """Full E2E: POST /api/simulate -> SSE stream with agent events -> simulation result."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/simulate",
            json={
                "type": "drop_course",
                "parameters": {"course_code": "CS 301"},
                "session_id": "e2e_session",
                "degree_id": "e2e_degree",
            },
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")

        events = _parse_sse_events(response.text)
        assert len(events) > 0, "Expected at least one SSE event"

        # Verify agent event structure
        for event in events:
            if "agent" in event:
                assert "event_type" in event
                assert "message" in event
                assert event["event_type"] in ("start", "thinking", "complete", "error")

        # Should contain events from simulator, policy, risk_scoring, and explanation agents
        agent_names = {e.get("agent") for e in events if "agent" in e}
        assert "simulator" in agent_names, f"Expected simulator agent events, got: {agent_names}"

        # Final event should contain combined simulation data
        complete_events = [e for e in events if e.get("event_type") == "complete" and e.get("data")]
        assert len(complete_events) > 0, "Expected at least one complete event with data"


@pytest.mark.asyncio
async def test_debate_sse_pipeline():
    """Full E2E: POST /api/simulate/debate -> Fast Track -> Safe Path -> Jury -> SSE stream."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/simulate/debate",
            json={"session_id": "demo_session"},
        )

        assert response.status_code == 200
        events = _parse_sse_events(response.text)
        assert len(events) > 0

        agent_names = {e.get("agent") for e in events if "agent" in e}
        # Debate should involve fast track, safe path, and jury agents
        assert "debate_fast" in agent_names, f"Expected debate_fast, got: {agent_names}"

        # Final complete event should have debate data
        final_events = [e for e in events if e.get("event_type") == "complete" and e.get("data")]
        assert len(final_events) > 0


@pytest.mark.asyncio
async def test_policy_check_sse_pipeline():
    """Full E2E: GET /api/degree/{session}/policy-check -> SSE policy agent events."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/degree/e2e_session/policy-check")

        assert response.status_code == 200
        events = _parse_sse_events(response.text)
        assert len(events) > 0

        agent_names = {e.get("agent") for e in events if "agent" in e}
        assert "policy" in agent_names

        # Should have thinking steps and a complete event
        thinking_events = [e for e in events if e.get("event_type") == "thinking"]
        assert len(thinking_events) >= 1, "Expected policy agent thinking steps"


@pytest.mark.asyncio
async def test_sse_events_are_valid_agent_events():
    """Verify ALL SSE events conform to the AgentEvent Pydantic schema (no raw strings)."""
    from app.models.schemas import AgentEvent

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/simulate",
            json={
                "type": "drop_course",
                "parameters": {"course_code": "CS 301"},
                "session_id": "e2e_session",
                "degree_id": "e2e_degree",
            },
        )

        events = _parse_sse_events(response.text)
        for event in events:
            if "agent" in event:
                # Every agent event should parse as a valid AgentEvent
                parsed = AgentEvent.model_validate(event)
                assert parsed.agent is not None
                assert parsed.event_type is not None
                assert isinstance(parsed.message, str)


@pytest.mark.asyncio
async def test_health_check_demo_mode():
    """Health endpoint should report bedrock_connected=True in demo mode."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["bedrock_connected"] is True


@pytest.mark.asyncio
async def test_degree_endpoint():
    """GET /api/degree/{session} should return parsed degree with course nodes."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/degree/e2e_session")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "parsed"
        assert data["degree"]["degree_name"] == "Computer Science BS"
        assert "course_nodes" in data
        assert len(data["course_nodes"]) == len(_DEMO_DEGREE["courses"])


@pytest.mark.asyncio
async def test_impact_report():
    """GET /api/degree/{session}/impact should compute metrics."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/degree/e2e_session/impact")
        assert response.status_code == 200
        data = response.json()
        assert "total_credits" in data
        assert "risk_score" in data
        assert data["total_credits"] > 0


@pytest.mark.asyncio
async def test_simulation_persists_result():
    """After simulation SSE completes, result should be queryable via history endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Run simulation
        await client.post(
            "/api/simulate",
            json={
                "type": "drop_course",
                "parameters": {"course_code": "CS 301"},
                "session_id": "e2e_session",
                "degree_id": "e2e_degree",
            },
        )

        # Check history
        history = await client.get("/api/simulate/e2e_session/history")
        assert history.status_code == 200
        data = history.json()
        assert isinstance(data, list)
        # At least one simulation should be saved
        assert len(data) >= 1
        assert data[0]["scenario_type"] == "drop_course"


@pytest.mark.asyncio
async def test_sse_heartbeat_format():
    """Verify heartbeat comments use SSE comment format (': heartbeat')."""
    # This is more of a unit check but validates the SSE wire format
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/simulate",
            json={
                "type": "drop_course",
                "parameters": {"course_code": "CS 301"},
                "session_id": "e2e_session",
                "degree_id": "e2e_degree",
            },
        )
        # All non-empty lines should either be SSE data or SSE comments
        for line in response.text.split("\n"):
            line = line.strip()
            if line:
                assert line.startswith("data: ") or line.startswith(":"), \
                    f"Invalid SSE line format: {line!r}"


@pytest.mark.asyncio
async def test_concurrent_sse_streams():
    """Stress test: 5 concurrent SSE simulation streams should all complete without errors.

    Validates that the async pipeline, DB connection pool, and mock Bedrock
    client handle parallel load correctly.
    """
    transport = ASGITransport(app=app)

    async def run_one_simulation(client: AsyncClient, idx: int):
        response = await client.post(
            "/api/simulate",
            json={
                "type": "drop_course",
                "parameters": {"course_code": "CS 301"},
                "session_id": "e2e_session",
                "degree_id": "e2e_degree",
            },
        )
        assert response.status_code == 200, f"Stream {idx} failed with {response.status_code}"
        assert response.headers["content-type"].startswith("text/event-stream")
        events = _parse_sse_events(response.text)
        assert len(events) > 0, f"Stream {idx} produced no events"
        # Verify every event is valid JSON with expected fields
        for event in events:
            if "agent" in event:
                assert "event_type" in event
                assert "message" in event
        return events

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Launch 5 concurrent simulation streams
        results = await asyncio.gather(
            *[run_one_simulation(client, i) for i in range(5)],
            return_exceptions=True,
        )

        # All 5 should succeed — no exceptions
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"Stream {i} raised: {result}"
            assert len(result) > 0, f"Stream {i} returned empty events"

        # Verify all streams produced agent events
        for i, events in enumerate(results):
            agent_names = {e.get("agent") for e in events if "agent" in e}
            assert "simulator" in agent_names, f"Stream {i} missing simulator events"


@pytest.mark.asyncio
async def test_concurrent_mixed_endpoints():
    """Stress test: concurrent calls to different SSE endpoints simultaneously.

    Simulates realistic load: simulation + debate + policy check running at the same time.
    """
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        sim_task = client.post(
            "/api/simulate",
            json={
                "type": "drop_course",
                "parameters": {"course_code": "CS 301"},
                "session_id": "e2e_session",
                "degree_id": "e2e_degree",
            },
        )
        debate_task = client.post(
            "/api/simulate/debate",
            json={"session_id": "demo_session"},
        )
        policy_task = client.get("/api/degree/e2e_session/policy-check")

        results = await asyncio.gather(sim_task, debate_task, policy_task)

        # All three should return 200
        for i, resp in enumerate(results):
            assert resp.status_code == 200, f"Endpoint {i} returned {resp.status_code}"

        # Each should produce valid SSE events
        sim_events = _parse_sse_events(results[0].text)
        debate_events = _parse_sse_events(results[1].text)
        policy_events = _parse_sse_events(results[2].text)

        assert len(sim_events) > 0
        assert len(debate_events) > 0
        assert len(policy_events) > 0

        # Verify correct agents appeared in each stream
        sim_agents = {e.get("agent") for e in sim_events if "agent" in e}
        debate_agents = {e.get("agent") for e in debate_events if "agent" in e}
        policy_agents = {e.get("agent") for e in policy_events if "agent" in e}

        assert "simulator" in sim_agents
        assert "debate_fast" in debate_agents
        assert "policy" in policy_agents
