"""Tests for policy agent guardrails, debate rebuttal flow, and new scenario validation."""

import sys
import os
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.schemas import (
    Course, DegreeRequirement, Scenario, ScenarioType,
    AgentEvent, AgentEventType, AgentName,
)


# --- Helpers ---

def _make_course(code, name="", credits=3, prereqs=None, required=True):
    return Course(
        code=code,
        name=name or code,
        credits=credits,
        prerequisites=prereqs or [],
        category="Core",
        is_required=required,
    )


def _make_degree(courses, max_credits=18, total_credits=None):
    return DegreeRequirement(
        degree_name="Test BS",
        total_credits_required=total_credits or sum(c.credits for c in courses),
        courses=courses,
        max_credits_per_semester=max_credits,
    )


def _run_async(coro):
    """Run an async coroutine in a new event loop (for test compatibility)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# --- Policy Agent Guardrails ---

class TestPolicyGuardrails:
    """Tests for the deterministic safety guardrails in PolicyAgent."""

    def _run_policy(self, degree_dict, course_nodes, completed=None, current_sem=1):
        """Run PolicyAgent synchronously for testing, mocking Nova."""
        from app.agents.policy_agent import PolicyAgent

        agent = PolicyAgent()
        events = []

        async def emit(event):
            events.append(event)

        # Mock the Nova converse_async call so tests don't need AWS credentials
        with patch("app.agents.policy_agent.bedrock") as mock_bedrock:
            mock_bedrock.converse_async = AsyncMock(return_value={
                "output": {"message": {"content": [{"text": "[]"}]}}
            })
            mock_bedrock.extract_text_response = lambda r: "[]"

            result = _run_async(agent.run(
                {
                    "degree": degree_dict,
                    "course_nodes": course_nodes,
                    "completed_courses": completed or [],
                    "current_semester": current_sem,
                },
                emit,
            ))
        return result, events

    def test_hard_credit_ceiling_triggers(self):
        """Semester with >21 credits triggers hard ceiling error."""
        degree_dict = {
            "degree_name": "Test BS",
            "total_credits_required": 120,
            "max_credits_per_semester": 30,  # misconfigured — way too high
            "courses": [
                {"code": f"C{i}", "name": f"Course {i}", "credits": 4, "prerequisites": []}
                for i in range(8)
            ],
        }
        # Put all 8 courses (32 credits) into semester 1
        course_nodes = [
            {"code": f"C{i}", "name": f"Course {i}", "semester": 1, "credits": 4,
             "status": "scheduled", "prerequisites": []}
            for i in range(8)
        ]

        result, _ = self._run_policy(degree_dict, course_nodes)
        rules = [v["rule"] for v in result["violations"]]
        assert "Hard Credit Ceiling" in rules

    def test_hard_credit_ceiling_does_not_trigger_at_21(self):
        """Exactly 21 credits should NOT trigger hard ceiling."""
        degree_dict = {
            "degree_name": "Test BS",
            "total_credits_required": 21,
            "max_credits_per_semester": 21,
            "courses": [
                {"code": f"C{i}", "name": f"Course {i}", "credits": 3, "prerequisites": []}
                for i in range(7)
            ],
        }
        course_nodes = [
            {"code": f"C{i}", "name": f"Course {i}", "semester": 1, "credits": 3,
             "status": "scheduled", "prerequisites": []}
            for i in range(7)
        ]

        result, _ = self._run_policy(degree_dict, course_nodes)
        rules = [v["rule"] for v in result["violations"]]
        assert "Hard Credit Ceiling" not in rules

    def test_zero_elective_warning(self):
        """120+ credit degree with no electives triggers warning."""
        courses_data = [
            {"code": f"CORE{i}", "name": f"Core Course {i}", "credits": 3, "prerequisites": []}
            for i in range(40)
        ]
        degree_dict = {
            "degree_name": "Test BS",
            "total_credits_required": 120,
            "max_credits_per_semester": 18,
            "courses": courses_data,
        }
        course_nodes = [
            {"code": c["code"], "name": c["name"], "semester": (i // 6) + 1,
             "credits": 3, "status": "scheduled", "prerequisites": []}
            for i, c in enumerate(courses_data)
        ]

        result, _ = self._run_policy(degree_dict, course_nodes)
        rules = [v["rule"] for v in result["violations"]]
        assert "No Electives Detected" in rules

    def test_elective_present_no_warning(self):
        """Degree with elective slots should NOT trigger zero-elective warning."""
        courses_data = [
            {"code": "CORE1", "name": "Core Course 1", "credits": 3, "prerequisites": []},
            {"code": "ELEC1", "name": "Free Elective", "credits": 3, "prerequisites": []},
        ]
        degree_dict = {
            "degree_name": "Test BS",
            "total_credits_required": 6,
            "max_credits_per_semester": 18,
            "courses": courses_data,
        }
        course_nodes = [
            {"code": "CORE1", "name": "Core Course 1", "semester": 1, "credits": 3,
             "status": "scheduled", "prerequisites": []},
            {"code": "ELEC1", "name": "Free Elective", "semester": 1, "credits": 3,
             "status": "scheduled", "prerequisites": []},
        ]

        result, _ = self._run_policy(degree_dict, course_nodes)
        rules = [v["rule"] for v in result["violations"]]
        assert "No Electives Detected" not in rules

    def test_excessive_timeline_warning(self):
        """Plan spanning >12 remaining semesters triggers warning."""
        courses_data = [
            {"code": f"C{i}", "name": f"Course {i}", "credits": 3, "prerequisites": []}
            for i in range(14)
        ]
        degree_dict = {
            "degree_name": "Test BS",
            "total_credits_required": 42,
            "max_credits_per_semester": 3,  # only 1 course per semester
            "courses": courses_data,
        }
        # One course per semester = 14 semesters
        course_nodes = [
            {"code": f"C{i}", "name": f"Course {i}", "semester": i + 1,
             "credits": 3, "status": "scheduled", "prerequisites": []}
            for i in range(14)
        ]

        result, _ = self._run_policy(degree_dict, course_nodes, current_sem=1)
        rules = [v["rule"] for v in result["violations"]]
        assert "Excessive Timeline" in rules

    def test_credit_cap_violation(self):
        """Semester exceeding max_credits_per_semester triggers error."""
        degree_dict = {
            "degree_name": "Test BS",
            "total_credits_required": 24,
            "max_credits_per_semester": 12,
            "courses": [
                {"code": f"C{i}", "name": f"Course {i}", "credits": 4, "prerequisites": []}
                for i in range(6)
            ],
        }
        # Put all 6 courses (24 credits) in semester 1 — exceeds 12 cap
        course_nodes = [
            {"code": f"C{i}", "name": f"Course {i}", "semester": 1, "credits": 4,
             "status": "scheduled", "prerequisites": []}
            for i in range(6)
        ]

        result, _ = self._run_policy(degree_dict, course_nodes)
        rules = [v["rule"] for v in result["violations"]]
        assert "Credit Cap" in rules

    def test_prereq_ordering_violation(self):
        """Prerequisite scheduled after dependent triggers error."""
        degree_dict = {
            "degree_name": "Test BS",
            "total_credits_required": 6,
            "max_credits_per_semester": 18,
            "courses": [
                {"code": "A", "name": "Intro", "credits": 3, "prerequisites": []},
                {"code": "B", "name": "Advanced", "credits": 3, "prerequisites": ["A"]},
            ],
        }
        # B in semester 1, A in semester 2 — violation
        course_nodes = [
            {"code": "A", "name": "Intro", "semester": 2, "credits": 3,
             "status": "scheduled", "prerequisites": []},
            {"code": "B", "name": "Advanced", "semester": 1, "credits": 3,
             "status": "scheduled", "prerequisites": ["A"]},
        ]

        result, _ = self._run_policy(degree_dict, course_nodes)
        rules = [v["rule"] for v in result["violations"]]
        assert "Prerequisite Ordering" in rules

    def test_clean_plan_passes(self):
        """A well-structured plan should pass all checks."""
        degree_dict = {
            "degree_name": "Test BS",
            "total_credits_required": 12,
            "max_credits_per_semester": 18,
            "courses": [
                {"code": "A", "name": "Free Elective A", "credits": 3, "prerequisites": []},
                {"code": "B", "name": "Core B", "credits": 3, "prerequisites": ["A"]},
                {"code": "C", "name": "Core C", "credits": 3, "prerequisites": []},
                {"code": "D", "name": "Core D", "credits": 3, "prerequisites": ["B"]},
            ],
        }
        course_nodes = [
            {"code": "A", "name": "Free Elective A", "semester": 1, "credits": 3,
             "status": "scheduled", "prerequisites": []},
            {"code": "C", "name": "Core C", "semester": 1, "credits": 3,
             "status": "scheduled", "prerequisites": []},
            {"code": "B", "name": "Core B", "semester": 2, "credits": 3,
             "status": "scheduled", "prerequisites": ["A"]},
            {"code": "D", "name": "Core D", "semester": 3, "credits": 3,
             "status": "scheduled", "prerequisites": ["B"]},
        ]

        result, _ = self._run_policy(degree_dict, course_nodes)
        assert result["passed"] is True


# --- Debate Rebuttal Flow ---

class TestDebateRebuttal:
    """Tests for the multi-turn debate: Fast Track proposes, Safe Path rebuts."""

    def test_safe_path_receives_fast_track_proposal(self):
        """SafePathAgent should use SAFE_REBUTTAL_PROMPT when fast_track_proposal is provided."""
        from app.agents.debate_agents import SafePathAgent

        agent = SafePathAgent()
        events = []
        captured_prompt = []

        async def emit(event):
            events.append(event)

        mock_response = {
            "output": {"message": {"content": [{"text": "My rebuttal: the fast plan is too risky..."}]}}
        }

        with patch("app.agents.debate_agents.bedrock") as mock_bedrock:
            async def capture_converse(**kwargs):
                msgs = kwargs.get("messages", [])
                if msgs:
                    captured_prompt.append(msgs[0]["content"][0]["text"])
                return mock_response

            mock_bedrock.converse_async = capture_converse
            mock_bedrock.extract_text_response = lambda r: r["output"]["message"]["content"][0]["text"]

            result = _run_async(agent.run(
                {
                    "degree_name": "CS BS",
                    "total_credits": 120,
                    "completed_courses": "CS 101",
                    "current_semester": 3,
                    "remaining_courses": "CS 201, CS 301",
                    "fast_track_proposal": "Take 21 credits in semester 4 with CS 201, CS 301, CS 302...",
                },
                emit,
            ))

        assert result["strategy"] == "safe"
        assert "rebuttal" in result["proposal"].lower() or len(result["proposal"]) > 0
        # The prompt should contain the Fast Track proposal
        assert any("FAST TRACK PROPOSAL" in p for p in captured_prompt)

    def test_safe_path_falls_back_without_fast_track(self):
        """SafePathAgent should use DEBATE_PROMPT when no fast_track_proposal is provided."""
        from app.agents.debate_agents import SafePathAgent

        agent = SafePathAgent()
        events = []
        captured_prompt = []

        async def emit(event):
            events.append(event)

        mock_response = {
            "output": {"message": {"content": [{"text": "My balanced plan..."}]}}
        }

        with patch("app.agents.debate_agents.bedrock") as mock_bedrock:
            async def capture_converse(**kwargs):
                msgs = kwargs.get("messages", [])
                if msgs:
                    captured_prompt.append(msgs[0]["content"][0]["text"])
                return mock_response

            mock_bedrock.converse_async = capture_converse
            mock_bedrock.extract_text_response = lambda r: r["output"]["message"]["content"][0]["text"]

            result = _run_async(agent.run(
                {
                    "degree_name": "CS BS",
                    "total_credits": 120,
                    "completed_courses": "CS 101",
                    "current_semester": 3,
                    "remaining_courses": "CS 201, CS 301",
                },
                emit,
            ))

        assert result["strategy"] == "safe"
        # Should NOT contain the rebuttal prompt
        assert not any("FAST TRACK PROPOSAL" in p for p in captured_prompt)

    def test_fast_track_agent_emits_events(self):
        """FastTrackAgent should emit start, thinking, and complete events."""
        from app.agents.debate_agents import FastTrackAgent

        agent = FastTrackAgent()
        events = []

        async def emit(event):
            events.append(event)

        mock_response = {
            "output": {"message": {"content": [{"text": "Take max credits every semester..."}]}}
        }

        with patch("app.agents.debate_agents.bedrock") as mock_bedrock:
            mock_bedrock.converse_async = AsyncMock(return_value=mock_response)
            mock_bedrock.extract_text_response = lambda r: r["output"]["message"]["content"][0]["text"]

            result = _run_async(agent.run(
                {
                    "degree_name": "CS BS",
                    "total_credits": 120,
                    "completed_courses": "None",
                    "current_semester": 1,
                    "remaining_courses": "CS 101, CS 201",
                },
                emit,
            ))

        event_types = [e.event_type for e in events]
        assert AgentEventType.start in event_types
        assert AgentEventType.thinking in event_types
        assert AgentEventType.complete in event_types
        assert result["strategy"] == "fast"


# --- New Scenario Validation ---

class TestNewScenarioValidation:
    """Tests for the new scenario types added: add_minor, study_abroad, coop, gap_semester."""

    def test_add_minor_requires_degree_session_id(self):
        s = Scenario(type=ScenarioType.add_minor, parameters={}, session_id="x", degree_id="y")
        assert s.validate_parameters() is not None
        assert "degree_session_id" in s.validate_parameters()

        s2 = Scenario(type=ScenarioType.add_minor, parameters={"degree_session_id": "abc"}, session_id="x", degree_id="y")
        assert s2.validate_parameters() is None

    def test_study_abroad_requires_semester(self):
        s = Scenario(type=ScenarioType.study_abroad, parameters={}, session_id="x", degree_id="y")
        assert s.validate_parameters() is not None

        s2 = Scenario(type=ScenarioType.study_abroad, parameters={"semester": 4}, session_id="x", degree_id="y")
        assert s2.validate_parameters() is None

    def test_study_abroad_requires_int_semester(self):
        s = Scenario(type=ScenarioType.study_abroad, parameters={"semester": "four"}, session_id="x", degree_id="y")
        assert s.validate_parameters() is not None

    def test_coop_requires_semester(self):
        s = Scenario(type=ScenarioType.coop, parameters={}, session_id="x", degree_id="y")
        assert s.validate_parameters() is not None

        s2 = Scenario(type=ScenarioType.coop, parameters={"semester": 5}, session_id="x", degree_id="y")
        assert s2.validate_parameters() is None

    def test_gap_semester_requires_semester(self):
        s = Scenario(type=ScenarioType.gap_semester, parameters={}, session_id="x", degree_id="y")
        assert s.validate_parameters() is not None

        s2 = Scenario(type=ScenarioType.gap_semester, parameters={"semester": 3}, session_id="x", degree_id="y")
        assert s2.validate_parameters() is None

    def test_gap_semester_requires_int(self):
        s = Scenario(type=ScenarioType.gap_semester, parameters={"semester": "three"}, session_id="x", degree_id="y")
        assert s.validate_parameters() is not None


# --- Risk Scoring Agent ---

class TestRiskScoring:
    """Tests for the deterministic Risk Scoring Agent (0-100 score)."""

    def test_low_risk_simple_plan(self):
        """A simple plan with few remaining courses should score low."""
        from app.agents.risk_scoring_agent import compute_risk_score

        degree_data = {
            "total_credits_required": 12,
            "max_credits_per_semester": 18,
            "courses": [
                {"code": "A", "name": "A", "credits": 3, "prerequisites": []},
                {"code": "B", "name": "B", "credits": 3, "prerequisites": []},
                {"code": "C", "name": "C", "credits": 3, "prerequisites": []},
                {"code": "D", "name": "D", "credits": 3, "prerequisites": []},
            ],
        }
        course_nodes = [
            {"code": "A", "semester": 0, "credits": 3, "status": "completed"},
            {"code": "B", "semester": 0, "credits": 3, "status": "completed"},
            {"code": "C", "semester": 3, "credits": 3, "status": "scheduled"},
            {"code": "D", "semester": 3, "credits": 3, "status": "scheduled"},
        ]

        result = compute_risk_score(course_nodes, degree_data, ["A", "B"], 3)
        assert result["risk_score"] < 30
        assert result["risk_label"] == "low"

    def test_high_risk_deep_chains(self):
        """A plan with deep prerequisite chains should score higher."""
        from app.agents.risk_scoring_agent import compute_risk_score

        courses = [{"code": f"C{i}", "name": f"C{i}", "credits": 3,
                     "prerequisites": [f"C{i-1}"] if i > 0 else []}
                    for i in range(8)]
        degree_data = {
            "total_credits_required": 24,
            "max_credits_per_semester": 18,
            "courses": courses,
        }
        course_nodes = [
            {"code": f"C{i}", "semester": i + 1, "credits": 3, "status": "scheduled"}
            for i in range(8)
        ]

        result = compute_risk_score(course_nodes, degree_data, [], 1)
        assert result["risk_score"] > 20
        assert result["factors"]["prerequisite_chain_depth"]["score"] > 0

    def test_bottleneck_detection(self):
        """Courses with 3+ dependents should increase bottleneck score."""
        from app.agents.risk_scoring_agent import compute_risk_score

        courses = [
            {"code": "ROOT", "name": "Root", "credits": 3, "prerequisites": []},
            {"code": "D1", "name": "D1", "credits": 3, "prerequisites": ["ROOT"]},
            {"code": "D2", "name": "D2", "credits": 3, "prerequisites": ["ROOT"]},
            {"code": "D3", "name": "D3", "credits": 3, "prerequisites": ["ROOT"]},
        ]
        degree_data = {
            "total_credits_required": 12,
            "max_credits_per_semester": 18,
            "courses": courses,
        }
        course_nodes = [
            {"code": "ROOT", "semester": 1, "credits": 3, "status": "scheduled"},
            {"code": "D1", "semester": 2, "credits": 3, "status": "scheduled"},
            {"code": "D2", "semester": 2, "credits": 3, "status": "scheduled"},
            {"code": "D3", "semester": 2, "credits": 3, "status": "scheduled"},
        ]

        result = compute_risk_score(course_nodes, degree_data, [], 1)
        assert "ROOT" in result["bottleneck_courses"]
        assert result["factors"]["bottleneck_density"]["score"] > 0

    def test_all_completed_zero_risk(self):
        """When all courses are completed, risk should be minimal."""
        from app.agents.risk_scoring_agent import compute_risk_score

        courses = [
            {"code": "A", "name": "A", "credits": 3, "prerequisites": []},
            {"code": "B", "name": "B", "credits": 3, "prerequisites": []},
        ]
        degree_data = {
            "total_credits_required": 6,
            "max_credits_per_semester": 18,
            "courses": courses,
        }
        course_nodes = [
            {"code": "A", "semester": 0, "credits": 3, "status": "completed"},
            {"code": "B", "semester": 0, "credits": 3, "status": "completed"},
        ]

        result = compute_risk_score(course_nodes, degree_data, ["A", "B"], 5)
        assert result["risk_score"] <= 20  # velocity might add a few points
        assert result["risk_label"] == "low"

    def test_risk_score_has_all_factors(self):
        """Result should contain all 5 risk factors."""
        from app.agents.risk_scoring_agent import compute_risk_score

        degree_data = {
            "total_credits_required": 6,
            "max_credits_per_semester": 18,
            "courses": [{"code": "A", "name": "A", "credits": 3, "prerequisites": []}],
        }
        course_nodes = [{"code": "A", "semester": 1, "credits": 3, "status": "scheduled"}]

        result = compute_risk_score(course_nodes, degree_data, [], 1)
        factors = result["factors"]
        assert "prerequisite_chain_depth" in factors
        assert "credit_load_variance" in factors
        assert "bottleneck_density" in factors
        assert "completion_velocity" in factors
        assert "remaining_timeline" in factors

    def test_uneven_credit_distribution_increases_variance(self):
        """Semesters with very different credit loads should increase variance score."""
        from app.agents.risk_scoring_agent import compute_risk_score

        courses = [
            {"code": "C1", "name": "C1", "credits": 18, "prerequisites": []},
            {"code": "C2", "name": "C2", "credits": 3, "prerequisites": []},
        ]
        degree_data = {
            "total_credits_required": 21,
            "max_credits_per_semester": 18,
            "courses": courses,
        }
        course_nodes = [
            {"code": "C1", "semester": 1, "credits": 18, "status": "scheduled"},
            {"code": "C2", "semester": 2, "credits": 3, "status": "scheduled"},
        ]

        result = compute_risk_score(course_nodes, degree_data, [], 1)
        assert result["factors"]["credit_load_variance"]["score"] > 0
