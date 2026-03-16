"""Tests for the Orchestrator self-correction loop and debate flow."""

import pytest
import sys
from unittest.mock import AsyncMock, MagicMock
from app.models.schemas import AgentEvent, AgentEventType, AgentName, Scenario, ScenarioType


def _make_orchestrator():
    """Create an Orchestrator with all agents mocked (bypass import-time agent construction)."""
    # Import the module directly — conftest already mocks boto3
    from app.agents import orchestrator as orch_mod

    orch = orch_mod.Orchestrator.__new__(orch_mod.Orchestrator)
    orch.interpreter = MagicMock()
    orch.simulator = MagicMock()
    orch.explanation = MagicMock()
    orch.overlap = MagicMock()
    orch.policy = MagicMock()
    orch.fast_track = MagicMock()
    orch.safe_path = MagicMock()
    orch.risk_scorer = MagicMock()
    orch.jury = MagicMock()

    # Make all run methods async
    orch.simulator.run = AsyncMock()
    orch.policy.run = AsyncMock()
    orch.explanation.run = AsyncMock()
    orch.risk_scorer.run = AsyncMock()
    orch.overlap.run = AsyncMock()
    orch.fast_track.run = AsyncMock()
    orch.safe_path.run = AsyncMock()
    orch.jury.run = AsyncMock()
    orch.interpreter.run = AsyncMock()
    return orch


@pytest.fixture
def orchestrator():
    return _make_orchestrator()


@pytest.fixture
def sample_scenario():
    return Scenario(
        type=ScenarioType.drop_course,
        parameters={"course_code": "CS301"},
        session_id="test-session",
        degree_id="test-degree",
    )


@pytest.fixture
def sample_degree():
    return {
        "degree_name": "BS Computer Science",
        "total_credits_required": 120,
        "max_credits_per_semester": 18,
        "courses": [
            {"code": "CS101", "name": "Intro CS", "credits": 3, "prerequisites": [], "category": "Core", "typical_semester": 1},
            {"code": "CS201", "name": "Data Structures", "credits": 3, "prerequisites": ["CS101"], "category": "Core", "typical_semester": 2},
            {"code": "CS301", "name": "Algorithms", "credits": 3, "prerequisites": ["CS201"], "category": "Core", "typical_semester": 3},
        ],
    }


@pytest.mark.asyncio
async def test_no_correction_when_policy_passes(orchestrator, sample_scenario, sample_degree):
    """Simulation runs once when policy returns no error violations."""
    orchestrator.simulator.run.return_value = {
        "result": {"affected_courses": [], "semesters_added": 1, "risk_level": "low"}
    }
    orchestrator.policy.run.return_value = {
        "violations": [{"rule": "Low Load", "severity": "warning", "detail": "Light semester"}],
        "passed": True,
        "summary": "Warnings only",
    }
    orchestrator.risk_scorer.run.return_value = {"risk_score": 20, "risk_label": "low"}
    orchestrator.explanation.run.return_value = {"explanation": "All good."}

    events = []
    async for event in orchestrator.run_simulation(
        scenario=sample_scenario, degree_data=sample_degree,
        completed_courses=["CS101"], current_semester=2,
    ):
        if event is not None:
            events.append(event)

    assert orchestrator.simulator.run.call_count == 1
    assert orchestrator.policy.run.call_count == 1


@pytest.mark.asyncio
async def test_self_correction_on_error_violations(orchestrator, sample_scenario, sample_degree):
    """Simulator re-runs when policy finds error-severity violations."""
    orchestrator.simulator.run.return_value = {
        "result": {"affected_courses": [], "semesters_added": 1, "risk_level": "medium"}
    }
    orchestrator.policy.run.side_effect = [
        {"violations": [{"rule": "Credit Cap", "severity": "error", "detail": "Too many credits"}], "passed": False, "summary": "1 violation"},
        {"violations": [], "passed": True, "summary": "All clear"},
    ]
    orchestrator.risk_scorer.run.return_value = {"risk_score": 30, "risk_label": "medium"}
    orchestrator.explanation.run.return_value = {"explanation": "Corrected."}

    events = []
    async for event in orchestrator.run_simulation(
        scenario=sample_scenario, degree_data=sample_degree,
        completed_courses=[], current_semester=1,
    ):
        if event is not None:
            events.append(event)

    assert orchestrator.simulator.run.call_count == 2
    assert orchestrator.policy.run.call_count == 2
    second_call_input = orchestrator.simulator.run.call_args_list[1][0][0]
    assert "policy_violations" in second_call_input


@pytest.mark.asyncio
async def test_max_corrections_respected(orchestrator, sample_scenario, sample_degree):
    """Self-correction stops after _MAX_CORRECTIONS iterations."""
    orchestrator.simulator.run.return_value = {
        "result": {"affected_courses": [], "semesters_added": 2, "risk_level": "high"}
    }
    orchestrator.policy.run.return_value = {
        "violations": [{"rule": "Credit Cap", "severity": "error", "detail": "Overloaded"}],
        "passed": False, "summary": "Violation persists",
    }
    orchestrator.risk_scorer.run.return_value = {"risk_score": 60, "risk_label": "high"}
    orchestrator.explanation.run.return_value = {"explanation": "Issues remain."}

    events = []
    async for event in orchestrator.run_simulation(
        scenario=sample_scenario, degree_data=sample_degree,
        completed_courses=[], current_semester=1,
    ):
        if event is not None:
            events.append(event)

    # initial + 2 corrections = 3 total
    assert orchestrator.simulator.run.call_count == 3
    assert orchestrator.policy.run.call_count == 3


@pytest.mark.asyncio
async def test_debate_flow_multi_turn(orchestrator):
    """Debate runs Fast Track -> Safe Path (with fast proposal) -> Jury."""
    orchestrator.fast_track.run.return_value = {"proposal": "Take 21 credits per semester"}
    orchestrator.safe_path.run.return_value = {"proposal": "Take 15 credits, add summer"}
    orchestrator.jury.run.return_value = {"verdict": "Compromise at 18 credits"}

    events = []
    async for event in orchestrator.run_debate(
        degree_data={"degree_name": "BS CS", "total_credits_required": 120},
        completed_courses=["CS101"], current_semester=2,
        remaining_courses="CS201 (3cr), CS301 (3cr)",
    ):
        if event is not None:
            events.append(event)

    safe_call_input = orchestrator.safe_path.run.call_args[0][0]
    assert "fast_track_proposal" in safe_call_input
    assert safe_call_input["fast_track_proposal"] == "Take 21 credits per semester"

    jury_call_input = orchestrator.jury.run.call_args[0][0]
    assert jury_call_input["fast_proposal"] == "Take 21 credits per semester"
    assert jury_call_input["safe_proposal"] == "Take 15 credits, add summer"

    final = events[-1]
    assert final.data["fast"] == "Take 21 credits per semester"
    assert final.data["safe"] == "Take 15 credits, add summer"
    assert final.data["jury"] == "Compromise at 18 credits"


@pytest.mark.asyncio
async def test_overlap_triggered_for_add_major(orchestrator, sample_degree):
    """Overlap analysis runs when scenario is add_major."""
    scenario = Scenario(
        type=ScenarioType.add_major,
        parameters={"degree_session_id": "other-session"},
        session_id="test-session", degree_id="test-degree",
    )
    second_degree = {
        "degree_name": "BA Mathematics", "total_credits_required": 90,
        "courses": [{"code": "MATH101", "name": "Calculus I", "credits": 4, "prerequisites": [], "category": "Core"}],
    }
    orchestrator.overlap.run.return_value = {
        "overlap": {"exact_matches": [], "equivalent_courses": [], "total_shared_credits": 12}
    }
    orchestrator.simulator.run.return_value = {
        "result": {"affected_courses": [], "semesters_added": 2, "risk_level": "medium"}
    }
    orchestrator.policy.run.return_value = {"violations": [], "passed": True, "summary": "OK"}
    orchestrator.risk_scorer.run.return_value = {"risk_score": 40, "risk_label": "medium"}
    orchestrator.explanation.run.return_value = {"explanation": "Adding math major."}

    events = []
    async for event in orchestrator.run_simulation(
        scenario=scenario, degree_data=sample_degree,
        completed_courses=[], current_semester=1,
        second_degree_data=second_degree,
    ):
        if event is not None:
            events.append(event)

    assert orchestrator.overlap.run.call_count == 1


@pytest.mark.asyncio
async def test_events_emitted_in_order(orchestrator, sample_scenario, sample_degree):
    """Events are emitted and the final one is complete."""
    orchestrator.simulator.run.return_value = {
        "result": {"affected_courses": [], "semesters_added": 0, "risk_level": "low"}
    }
    orchestrator.policy.run.return_value = {"violations": [], "passed": True, "summary": "OK"}
    orchestrator.risk_scorer.run.return_value = {"risk_score": 10, "risk_label": "low"}
    orchestrator.explanation.run.return_value = {"explanation": "No impact."}

    events = []
    async for event in orchestrator.run_simulation(
        scenario=sample_scenario, degree_data=sample_degree,
        completed_courses=["CS101"], current_semester=2,
    ):
        if event is not None:
            events.append(event)

    assert len(events) >= 1
    assert events[-1].event_type == AgentEventType.complete
