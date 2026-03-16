"""Tests for API route logic — scenario validation, history format, etc."""

import pytest
import json
from app.models.schemas import Scenario, ScenarioType


class TestScenarioValidation:
    """Test Scenario.validate_parameters() which routes use for input validation."""

    def test_drop_course_valid(self):
        s = Scenario(type=ScenarioType.drop_course, parameters={"course_code": "CS301"},
                     session_id="s1", degree_id="d1")
        assert s.validate_parameters() is None

    def test_drop_course_missing_code(self):
        s = Scenario(type=ScenarioType.drop_course, parameters={},
                     session_id="s1", degree_id="d1")
        assert s.validate_parameters() is not None
        assert "course_code" in s.validate_parameters()

    def test_block_semester_valid(self):
        s = Scenario(type=ScenarioType.block_semester, parameters={"semester": 3},
                     session_id="s1", degree_id="d1")
        assert s.validate_parameters() is None

    def test_block_semester_requires_int(self):
        s = Scenario(type=ScenarioType.block_semester, parameters={"semester": "three"},
                     session_id="s1", degree_id="d1")
        assert s.validate_parameters() is not None

    def test_add_major_requires_degree_session_id(self):
        s = Scenario(type=ScenarioType.add_major, parameters={},
                     session_id="s1", degree_id="d1")
        assert s.validate_parameters() is not None
        assert "degree_session_id" in s.validate_parameters()

    def test_add_major_valid(self):
        s = Scenario(type=ScenarioType.add_major, parameters={"degree_session_id": "s2"},
                     session_id="s1", degree_id="d1")
        assert s.validate_parameters() is None

    def test_set_goal_requires_target(self):
        s = Scenario(type=ScenarioType.set_goal, parameters={},
                     session_id="s1", degree_id="d1")
        assert s.validate_parameters() is not None

    def test_study_abroad_requires_int_semester(self):
        s = Scenario(type=ScenarioType.study_abroad, parameters={"semester": "fall"},
                     session_id="s1", degree_id="d1")
        assert s.validate_parameters() is not None

    def test_coop_valid(self):
        s = Scenario(type=ScenarioType.coop, parameters={"semester": 5},
                     session_id="s1", degree_id="d1")
        assert s.validate_parameters() is None

    def test_gap_semester_valid(self):
        s = Scenario(type=ScenarioType.gap_semester, parameters={"semester": 4},
                     session_id="s1", degree_id="d1")
        assert s.validate_parameters() is None

    def test_parent_simulation_id_optional(self):
        s = Scenario(type=ScenarioType.drop_course, parameters={"course_code": "CS301"},
                     session_id="s1", degree_id="d1", parent_simulation_id="sim-parent")
        assert s.parent_simulation_id == "sim-parent"
        assert s.validate_parameters() is None

    def test_parent_simulation_id_default_none(self):
        s = Scenario(type=ScenarioType.drop_course, parameters={"course_code": "CS301"},
                     session_id="s1", degree_id="d1")
        assert s.parent_simulation_id is None


class TestBuildCourseNodes:
    """Test _build_course_nodes_from_simulation in orchestrator."""

    def test_builds_nodes_with_reassignments(self):
        from app.agents.orchestrator import _build_course_nodes_from_simulation

        degree_data = {
            "courses": [
                {"code": "CS101", "name": "Intro", "credits": 3, "prerequisites": [], "typical_semester": 1},
                {"code": "CS201", "name": "DS", "credits": 3, "prerequisites": ["CS101"], "typical_semester": 2},
            ],
        }
        sim_result = {
            "affected_courses": [
                {"code": "CS201", "new_semester": 4},
            ],
        }

        nodes = _build_course_nodes_from_simulation(degree_data, ["CS101"], 2, sim_result)
        assert len(nodes) == 2

        cs101 = next(n for n in nodes if n["code"] == "CS101")
        assert cs101["status"] == "completed"
        assert cs101["semester"] == 0

        cs201 = next(n for n in nodes if n["code"] == "CS201")
        assert cs201["semester"] == 4  # reassigned
        assert cs201["status"] == "scheduled"

    def test_no_reassignments(self):
        from app.agents.orchestrator import _build_course_nodes_from_simulation

        degree_data = {
            "courses": [
                {"code": "CS101", "name": "Intro", "credits": 3, "prerequisites": [], "typical_semester": 1},
            ],
        }
        nodes = _build_course_nodes_from_simulation(degree_data, [], 1, {"affected_courses": []})
        assert len(nodes) == 1
        assert nodes[0]["semester"] == 1
