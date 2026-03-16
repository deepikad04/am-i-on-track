"""Tests for the graph builder / semester assignment logic."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.schemas import Course, DegreeRequirement
from app.services.graph_builder import assign_semesters, build_course_graph


def _make_course(code, name="", credits=3, prereqs=None, required=True):
    return Course(
        code=code,
        name=name or code,
        credits=credits,
        prerequisites=prereqs or [],
        category="Core",
        is_required=required,
    )


def _make_degree(courses, max_credits=18):
    return DegreeRequirement(
        degree_name="Test BS",
        total_credits_required=sum(c.credits for c in courses),
        courses=courses,
        max_credits_per_semester=max_credits,
    )


class TestBuildCourseGraph:
    def test_empty_degree(self):
        degree = _make_degree([])
        g = build_course_graph(degree)
        assert g["course_map"] == {}
        assert g["in_degree"] == {}

    def test_linear_chain(self):
        courses = [
            _make_course("A"),
            _make_course("B", prereqs=["A"]),
            _make_course("C", prereqs=["B"]),
        ]
        g = build_course_graph(_make_degree(courses))
        assert g["in_degree"]["A"] == 0
        assert g["in_degree"]["B"] == 1
        assert g["in_degree"]["C"] == 1
        assert "B" in g["adj"]["A"]
        assert "C" in g["adj"]["B"]

    def test_diamond_dependency(self):
        courses = [
            _make_course("A"),
            _make_course("B", prereqs=["A"]),
            _make_course("C", prereqs=["A"]),
            _make_course("D", prereqs=["B", "C"]),
        ]
        g = build_course_graph(_make_degree(courses))
        assert g["in_degree"]["D"] == 2


class TestAssignSemesters:
    def test_no_prereqs_same_semester(self):
        courses = [_make_course("A"), _make_course("B"), _make_course("C")]
        result = assign_semesters(_make_degree(courses))
        semesters = {r["code"]: r["semester"] for r in result}
        # All can go in semester 1
        assert semesters["A"] == 1
        assert semesters["B"] == 1
        assert semesters["C"] == 1

    def test_prereqs_force_ordering(self):
        courses = [
            _make_course("A"),
            _make_course("B", prereqs=["A"]),
        ]
        result = assign_semesters(_make_degree(courses))
        semesters = {r["code"]: r["semester"] for r in result}
        assert semesters["A"] < semesters["B"]

    def test_credit_limit_respected(self):
        courses = [_make_course(f"C{i}", credits=6) for i in range(4)]
        result = assign_semesters(_make_degree(courses, max_credits=12))
        semesters = {r["code"]: r["semester"] for r in result}
        # 4 courses x 6 credits = 24, max 12/sem, needs at least 2 semesters
        assert max(semesters.values()) >= 2

    def test_completed_courses_at_semester_zero(self):
        courses = [
            _make_course("A"),
            _make_course("B", prereqs=["A"]),
        ]
        result = assign_semesters(_make_degree(courses), completed_courses=["A"])
        status_map = {r["code"]: r for r in result}
        assert status_map["A"]["status"] == "completed"
        assert status_map["A"]["semester"] == 0
        assert status_map["B"]["semester"] == 1

    def test_bottleneck_status_for_high_dependents(self):
        courses = [
            _make_course("ROOT"),
            _make_course("D1", prereqs=["ROOT"]),
            _make_course("D2", prereqs=["ROOT"]),
            _make_course("D3", prereqs=["ROOT"]),
        ]
        result = assign_semesters(_make_degree(courses))
        root = next(r for r in result if r["code"] == "ROOT")
        assert root["status"] == "bottleneck"

    def test_elective_status(self):
        courses = [_make_course("ELEC", required=False)]
        result = assign_semesters(_make_degree(courses))
        assert result[0]["status"] == "elective"

    def test_external_prereq_treated_as_satisfied(self):
        # A prereq not in the degree list is treated as already satisfied
        courses = [
            _make_course("A", prereqs=["MISSING"]),
        ]
        result = assign_semesters(_make_degree(courses))
        assert result[0]["status"] == "scheduled"

    def test_locked_when_prereq_unresolvable(self):
        # A course with an in-degree prereq that never gets scheduled stays locked
        courses = [
            _make_course("A", prereqs=["B"]),
            _make_course("B", prereqs=["A"]),  # circular — neither can be scheduled
        ]
        result = assign_semesters(_make_degree(courses))
        statuses = {r["code"]: r["status"] for r in result}
        assert statuses["A"] == "locked"
        assert statuses["B"] == "locked"

    def test_current_semester_offset(self):
        courses = [_make_course("A")]
        result = assign_semesters(_make_degree(courses), current_semester=3)
        assert result[0]["semester"] == 3


class TestScenarioValidation:
    def test_drop_course_requires_code(self):
        from app.models.schemas import Scenario, ScenarioType

        s = Scenario(type=ScenarioType.drop_course, parameters={}, session_id="x", degree_id="y")
        assert s.validate_parameters() is not None

        s2 = Scenario(type=ScenarioType.drop_course, parameters={"course_code": "CS101"}, session_id="x", degree_id="y")
        assert s2.validate_parameters() is None

    def test_block_semester_requires_int(self):
        from app.models.schemas import Scenario, ScenarioType

        s = Scenario(type=ScenarioType.block_semester, parameters={}, session_id="x", degree_id="y")
        assert s.validate_parameters() is not None

        s2 = Scenario(type=ScenarioType.block_semester, parameters={"semester": 3}, session_id="x", degree_id="y")
        assert s2.validate_parameters() is None

    def test_set_goal_requires_target(self):
        from app.models.schemas import Scenario, ScenarioType

        s = Scenario(type=ScenarioType.set_goal, parameters={}, session_id="x", degree_id="y")
        assert s.validate_parameters() is not None

    def test_add_major_requires_name(self):
        from app.models.schemas import Scenario, ScenarioType

        s = Scenario(type=ScenarioType.add_major, parameters={}, session_id="x", degree_id="y")
        assert s.validate_parameters() is not None

        s2 = Scenario(type=ScenarioType.add_major, parameters={"degree_session_id": "abc123"}, session_id="x", degree_id="y")
        assert s2.validate_parameters() is None


class TestAssignSemestersAdvanced:
    def test_deep_chain_respects_order(self):
        """A chain of 5 courses must be scheduled across 5 semesters."""
        courses = [_make_course("C1")]
        for i in range(2, 6):
            courses.append(_make_course(f"C{i}", prereqs=[f"C{i-1}"]))
        result = assign_semesters(_make_degree(courses))
        semesters = {r["code"]: r["semester"] for r in result}
        for i in range(1, 5):
            assert semesters[f"C{i}"] < semesters[f"C{i+1}"]

    def test_mixed_required_and_elective_priority(self):
        """Required courses are prioritized over electives when credit-constrained."""
        courses = [
            _make_course("REQ1", credits=9),
            _make_course("REQ2", credits=9),
            _make_course("ELEC1", credits=9, required=False),
        ]
        result = assign_semesters(_make_degree(courses, max_credits=18))
        sem_map = {r["code"]: r["semester"] for r in result}
        # Both required courses should be in semester 1, elective deferred
        assert sem_map["REQ1"] == 1
        assert sem_map["REQ2"] == 1
        assert sem_map["ELEC1"] == 2

    def test_all_completed_returns_only_completed(self):
        """When all courses are completed, everything should be at semester 0."""
        courses = [_make_course("A"), _make_course("B")]
        result = assign_semesters(_make_degree(courses), completed_courses=["A", "B"])
        for r in result:
            assert r["status"] == "completed"
            assert r["semester"] == 0

    def test_diamond_dependency_ordering(self):
        """In a diamond A -> B,C -> D, D must come after both B and C."""
        courses = [
            _make_course("A"),
            _make_course("B", prereqs=["A"]),
            _make_course("C", prereqs=["A"]),
            _make_course("D", prereqs=["B", "C"]),
        ]
        result = assign_semesters(_make_degree(courses))
        semesters = {r["code"]: r["semester"] for r in result}
        assert semesters["A"] < semesters["B"]
        assert semesters["A"] < semesters["C"]
        assert semesters["B"] <= semesters["D"]
        assert semesters["C"] <= semesters["D"]
        assert semesters["D"] > semesters["A"]
