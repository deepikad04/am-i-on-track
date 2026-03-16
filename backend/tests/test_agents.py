"""Unit tests for individual agents — mock Bedrock to test parsing and logic."""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from app.models.schemas import AgentEventType


# --- Helper to build a Bedrock-style response ---

def make_bedrock_response(text: str = "", tool_input: dict | None = None) -> dict:
    """Build a mock Converse API response."""
    content = []
    if text:
        content.append({"text": text})
    if tool_input is not None:
        content.append({"toolUse": {"toolUseId": "t1", "name": "test", "input": tool_input}})
    return {
        "output": {"message": {"role": "assistant", "content": content}},
        "usage": {"inputTokens": 100, "outputTokens": 50},
        "ResponseMetadata": {"RequestId": "test-123"},
    }


# ============================================================
# TrajectorySimulatorAgent
# ============================================================

@pytest.mark.asyncio
async def test_simulator_tool_use_success():
    """Simulator extracts structured output from tool-use response."""
    tool_data = {
        "original_graduation": "Spring 2027",
        "new_graduation": "Fall 2027",
        "semesters_added": 1,
        "affected_courses": [
            {"code": "CS301", "name": "Algorithms", "original_semester": 3, "new_semester": 4, "reason": "Prereq shifted"}
        ],
        "credit_impact": 3,
        "risk_level": "medium",
    }

    with patch("app.agents.trajectory_simulator.bedrock") as mock_bedrock:
        mock_bedrock.converse_async = AsyncMock(return_value=make_bedrock_response(tool_input=tool_data))
        mock_bedrock.extract_tool_use = MagicMock(return_value=tool_data)
        mock_bedrock.extract_text_response = MagicMock(return_value="")

        from app.agents.trajectory_simulator import TrajectorySimulatorAgent
        agent = TrajectorySimulatorAgent()
        emitted = []
        result = await agent.run(
            {
                "degree": {"courses": [], "total_credits_required": 120},
                "scenario_type": "drop_course",
                "parameters": {"course_code": "CS301"},
                "completed_courses": [],
                "current_semester": 1,
            },
            AsyncMock(side_effect=lambda e: emitted.append(e)),
        )

    assert "result" in result
    assert result["result"]["semesters_added"] == 1
    assert result["result"]["risk_level"] == "medium"
    # Should have start, thinking, and complete events
    event_types = [e.event_type for e in emitted]
    assert AgentEventType.start in event_types
    assert AgentEventType.complete in event_types


@pytest.mark.asyncio
async def test_simulator_text_fallback():
    """Simulator falls back to text parsing when tool-use fails."""
    json_text = json.dumps({
        "original_graduation": "Spring 2027",
        "new_graduation": "Spring 2027",
        "semesters_added": 0,
        "affected_courses": [],
        "credit_impact": 0,
        "risk_level": "low",
    })

    with patch("app.agents.trajectory_simulator.bedrock") as mock_bedrock:
        mock_bedrock.converse_async = AsyncMock(return_value=make_bedrock_response(text=f"```json\n{json_text}\n```"))
        mock_bedrock.extract_tool_use = MagicMock(return_value=None)
        mock_bedrock.extract_text_response = MagicMock(return_value=f"```json\n{json_text}\n```")

        from app.agents.trajectory_simulator import TrajectorySimulatorAgent
        agent = TrajectorySimulatorAgent()
        result = await agent.run(
            {
                "degree": {"courses": []},
                "scenario_type": "drop_course",
                "parameters": {},
                "completed_courses": [],
                "current_semester": 1,
            },
            AsyncMock(),
        )

    assert "result" in result
    assert result["result"]["risk_level"] == "low"


@pytest.mark.asyncio
async def test_simulator_policy_violation_injection():
    """Simulator includes policy violations in prompt on correction iterations."""
    tool_data = {
        "original_graduation": "Spring 2027",
        "new_graduation": "Fall 2027",
        "semesters_added": 1,
        "affected_courses": [],
        "credit_impact": 0,
        "risk_level": "low",
    }

    with patch("app.agents.trajectory_simulator.bedrock") as mock_bedrock:
        mock_bedrock.converse_async = AsyncMock(return_value=make_bedrock_response(tool_input=tool_data))
        mock_bedrock.extract_tool_use = MagicMock(return_value=tool_data)

        from app.agents.trajectory_simulator import TrajectorySimulatorAgent
        agent = TrajectorySimulatorAgent()
        emitted = []
        result = await agent.run(
            {
                "degree": {"courses": []},
                "scenario_type": "drop_course",
                "parameters": {},
                "completed_courses": [],
                "current_semester": 1,
                "policy_violations": [
                    {"rule": "Credit Cap", "severity": "error", "detail": "Overloaded", "suggestion": "Move courses"}
                ],
            },
            AsyncMock(side_effect=lambda e: emitted.append(e)),
        )

    # The start event should mention re-running
    start_events = [e for e in emitted if e.event_type == AgentEventType.start]
    assert any("Re-running" in e.message or "fix" in e.message.lower() for e in start_events)

    # Prompt sent to bedrock should contain correction context
    call_args = mock_bedrock.converse_async.call_args
    prompt_text = call_args[1]["messages"][0]["content"][0]["text"]
    assert "IMPORTANT CORRECTION" in prompt_text


# ============================================================
# RiskScoringAgent (deterministic, no LLM)
# ============================================================

@pytest.mark.asyncio
async def test_risk_scoring_low_risk():
    """Simple plan with no bottlenecks scores low risk."""
    from app.agents.risk_scoring_agent import compute_risk_score

    course_nodes = [
        {"code": "CS201", "semester": 3, "credits": 3, "status": "scheduled", "prerequisites": ["CS101"]},
        {"code": "CS301", "semester": 4, "credits": 3, "status": "scheduled", "prerequisites": ["CS201"]},
    ]
    degree = {
        "total_credits_required": 120,
        "max_credits_per_semester": 18,
        "courses": [
            {"code": "CS101", "credits": 3, "prerequisites": []},
            {"code": "CS201", "credits": 3, "prerequisites": ["CS101"]},
            {"code": "CS301", "credits": 3, "prerequisites": ["CS201"]},
        ],
    }

    result = compute_risk_score(course_nodes, degree, ["CS101"], 2)
    assert result["risk_label"] == "low"
    assert result["risk_score"] < 30


@pytest.mark.asyncio
async def test_risk_scoring_detects_bottlenecks():
    """Courses with 3+ dependents are flagged as bottlenecks."""
    from app.agents.risk_scoring_agent import compute_risk_score

    courses = [
        {"code": "CORE", "credits": 3, "prerequisites": []},
        {"code": "A", "credits": 3, "prerequisites": ["CORE"]},
        {"code": "B", "credits": 3, "prerequisites": ["CORE"]},
        {"code": "C", "credits": 3, "prerequisites": ["CORE"]},
    ]
    course_nodes = [
        {"code": "CORE", "semester": 2, "credits": 3, "status": "scheduled", "prerequisites": []},
        {"code": "A", "semester": 3, "credits": 3, "status": "scheduled", "prerequisites": ["CORE"]},
        {"code": "B", "semester": 3, "credits": 3, "status": "scheduled", "prerequisites": ["CORE"]},
        {"code": "C", "semester": 3, "credits": 3, "status": "scheduled", "prerequisites": ["CORE"]},
    ]
    degree = {"total_credits_required": 12, "courses": courses}

    result = compute_risk_score(course_nodes, degree, [], 1)
    assert "CORE" in result["bottleneck_courses"]


# ============================================================
# PolicyAgent — deterministic checks only (mock LLM part)
# ============================================================

@pytest.mark.asyncio
async def test_policy_credit_cap_violation():
    """Policy detects when semester exceeds credit cap."""
    with patch("app.agents.policy_agent.bedrock") as mock_bedrock:
        mock_bedrock.converse_async = AsyncMock(return_value=make_bedrock_response(tool_input={"violations": []}))
        mock_bedrock.extract_tool_use = MagicMock(return_value={"violations": []})

        from app.agents.policy_agent import PolicyAgent
        agent = PolicyAgent()
        # 7 courses * 3 credits = 21 > 18 cap
        course_nodes = [
            {"code": f"CS{i}", "semester": 3, "credits": 3, "status": "scheduled", "prerequisites": []}
            for i in range(7)
        ]
        degree = {
            "degree_name": "BS CS",
            "total_credits_required": 120,
            "max_credits_per_semester": 18,
            "courses": [{"code": f"CS{i}", "credits": 3, "prerequisites": [], "name": f"CS{i}"} for i in range(7)],
        }

        result = await agent.run(
            {"degree": degree, "course_nodes": course_nodes, "completed_courses": [], "current_semester": 1},
            AsyncMock(),
        )

    assert not result["passed"]
    credit_violations = [v for v in result["violations"] if v["rule"] == "Credit Cap"]
    assert len(credit_violations) >= 1


@pytest.mark.asyncio
async def test_policy_prerequisite_ordering_violation():
    """Policy detects when a course is scheduled before its prerequisite."""
    with patch("app.agents.policy_agent.bedrock") as mock_bedrock:
        mock_bedrock.converse_async = AsyncMock(return_value=make_bedrock_response(tool_input={"violations": []}))
        mock_bedrock.extract_tool_use = MagicMock(return_value={"violations": []})

        from app.agents.policy_agent import PolicyAgent
        agent = PolicyAgent()
        course_nodes = [
            {"code": "CS201", "semester": 2, "credits": 3, "status": "scheduled", "prerequisites": ["CS101"]},
            {"code": "CS101", "semester": 3, "credits": 3, "status": "scheduled", "prerequisites": []},  # AFTER CS201!
        ]
        degree = {
            "degree_name": "BS CS",
            "total_credits_required": 120,
            "max_credits_per_semester": 18,
            "courses": [
                {"code": "CS101", "credits": 3, "prerequisites": [], "name": "Intro"},
                {"code": "CS201", "credits": 3, "prerequisites": ["CS101"], "name": "DS"},
            ],
        }

        result = await agent.run(
            {"degree": degree, "course_nodes": course_nodes, "completed_courses": [], "current_semester": 1},
            AsyncMock(),
        )

    prereq_violations = [v for v in result["violations"] if v["rule"] == "Prerequisite Ordering"]
    assert len(prereq_violations) >= 1


# ============================================================
# ExplanationAgent
# ============================================================

@pytest.mark.asyncio
async def test_explanation_agent_returns_text():
    """Explanation agent extracts text from Nova response."""
    with patch("app.agents.explanation_agent.bedrock") as mock_bedrock:
        mock_bedrock.converse_async = AsyncMock(
            return_value=make_bedrock_response(text="Dropping CS301 delays graduation by one semester.")
        )
        mock_bedrock.extract_text_response = MagicMock(return_value="Dropping CS301 delays graduation by one semester.")

        from app.agents.explanation_agent import ExplanationAgent
        agent = ExplanationAgent()
        result = await agent.run(
            {"simulation_result": {"semesters_added": 1}, "scenario_description": "drop_course: CS301"},
            AsyncMock(),
        )

    assert result["explanation"] == "Dropping CS301 delays graduation by one semester."


# ============================================================
# Model Router — dynamic complexity-based routing
# ============================================================

def test_model_router_simple_plan_routes_lite():
    """A small, simple degree plan should route to Lite."""
    from app.services.model_router import compute_complexity_score

    degree = {
        "courses": [
            {"code": "CS101", "credits": 3, "prerequisites": []},
            {"code": "CS201", "credits": 3, "prerequisites": ["CS101"]},
        ],
    }
    result = compute_complexity_score(degree_data=degree, scenario_type="drop_course")
    assert result["model_tier"] == "lite"
    assert result["complexity_score"] < 30


def test_model_router_complex_plan_routes_pro():
    """A large plan with deep prerequisites and add_major scenario should route to Pro."""
    from app.services.model_router import compute_complexity_score

    # Build a 30-course plan with deep prerequisite chains
    courses = [{"code": f"CS{i}", "credits": 3, "prerequisites": [f"CS{i-1}"] if i > 0 else []} for i in range(30)]
    degree = {"courses": courses}
    result = compute_complexity_score(degree_data=degree, scenario_type="add_major")
    assert result["model_tier"] == "pro"
    assert result["complexity_score"] >= 30
    assert len(result["factors"]) >= 3


def test_model_router_correction_boosts_score():
    """Correction iterations should increase complexity (need stronger model)."""
    from app.services.model_router import compute_complexity_score

    base = compute_complexity_score(scenario_type="drop_course")
    corrected = compute_complexity_score(scenario_type="drop_course", correction_iteration=2)
    assert corrected["complexity_score"] > base["complexity_score"]


# ============================================================
# Risk Scoring — memory feedback loop
# ============================================================

def test_risk_scoring_with_memory_bottlenecks():
    """Memory-learned bottlenecks should increase the risk score."""
    from app.agents.risk_scoring_agent import compute_risk_score

    course_nodes = [
        {"code": "CORE", "semester": 2, "credits": 3, "status": "scheduled", "prerequisites": []},
        {"code": "A", "semester": 3, "credits": 3, "status": "scheduled", "prerequisites": ["CORE"]},
    ]
    degree = {
        "total_credits_required": 120,
        "courses": [
            {"code": "CORE", "credits": 3, "prerequisites": []},
            {"code": "A", "credits": 3, "prerequisites": ["CORE"]},
        ],
    }

    # Without memory
    base = compute_risk_score(course_nodes, degree, [], 1)

    # With memory-learned bottleneck for CORE
    memory_bottlenecks = [{"course": "CORE", "frequency": 3, "cascading_delays": 5, "downstream_courses": ["A", "B"]}]
    with_memory = compute_risk_score(course_nodes, degree, [], 1, memory_bottlenecks=memory_bottlenecks)

    assert with_memory["risk_score"] > base["risk_score"]
    assert "CORE" in with_memory["memory_flagged_courses"]
    assert "memory_learned_risk" in with_memory["factors"]
