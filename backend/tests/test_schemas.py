"""Tests for Pydantic schemas and model serialization."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pydantic import ValidationError
import pytest
from app.models.schemas import (
    Course,
    DegreeRequirement,
    SimulationResult,
    AffectedCourse,
    AgentEvent,
    AgentName,
    AgentEventType,
    ScenarioType,
)


class TestCourseModel:
    def test_defaults(self):
        c = Course(code="CS101", name="Intro CS", credits=3, category="Core")
        assert c.prerequisites == []
        assert c.corequisites == []
        assert c.is_required is True
        assert c.available_semesters == ["fall", "spring"]
        assert c.typical_semester is None

    def test_all_fields(self):
        c = Course(
            code="CS201",
            name="Data Structures",
            credits=4,
            prerequisites=["CS101"],
            corequisites=["CS201L"],
            category="Core",
            typical_semester=3,
            is_required=True,
            available_semesters=["fall"],
        )
        assert c.prerequisites == ["CS101"]
        assert c.available_semesters == ["fall"]

    def test_missing_required_field(self):
        with pytest.raises(ValidationError):
            Course(code="CS101", name="Intro CS", credits=3)  # missing category


class TestDegreeRequirement:
    def test_defaults(self):
        d = DegreeRequirement(
            degree_name="CS BS",
            total_credits_required=120,
            courses=[],
        )
        assert d.max_credits_per_semester == 18
        assert d.categories == []
        assert d.constraints == []
        assert d.institution is None

    def test_round_trip_json(self):
        c = Course(code="CS101", name="Intro", credits=3, category="Core")
        d = DegreeRequirement(
            degree_name="CS BS",
            total_credits_required=120,
            courses=[c],
        )
        j = d.model_dump_json()
        d2 = DegreeRequirement.model_validate_json(j)
        assert d2.degree_name == "CS BS"
        assert len(d2.courses) == 1
        assert d2.courses[0].code == "CS101"


class TestSimulationResult:
    def test_minimal(self):
        r = SimulationResult(
            original_graduation="Spring 2027",
            new_graduation="Fall 2027",
            semesters_added=1,
            affected_courses=[],
            credit_impact=3,
        )
        assert r.risk_level == "low"
        assert r.reasoning_steps == []
        assert r.recommendations == []

    def test_with_affected_courses(self):
        ac = AffectedCourse(
            code="CS301",
            name="Algorithms",
            original_semester=4,
            new_semester=5,
            reason="Prerequisite delayed",
        )
        r = SimulationResult(
            original_graduation="Spring 2027",
            new_graduation="Fall 2027",
            semesters_added=1,
            affected_courses=[ac],
            credit_impact=3,
            risk_level="medium",
        )
        assert len(r.affected_courses) == 1
        assert r.affected_courses[0].code == "CS301"


class TestAgentEvent:
    def test_serialization(self):
        e = AgentEvent(
            agent=AgentName.interpreter,
            event_type=AgentEventType.thinking,
            step=1,
            message="Parsing PDF...",
            timestamp=0,
        )
        j = e.model_dump_json()
        assert '"interpreter"' in j
        assert '"thinking"' in j

    def test_all_agent_names(self):
        names = [e.value for e in AgentName]
        assert "interpreter" in names
        assert "simulator" in names
        assert "explanation" in names
        assert "overlap" in names
        assert "advisor" in names
        assert "risk_scoring" in names
        assert "jury" in names

    def test_all_scenario_types(self):
        types = [e.value for e in ScenarioType]
        assert set(types) == {"drop_course", "block_semester", "add_major", "set_goal", "add_minor", "study_abroad", "coop", "gap_semester"}
