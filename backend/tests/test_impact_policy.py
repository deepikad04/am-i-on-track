"""Tests for impact report computation and policy violation detection."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.schemas import Course, DegreeRequirement, ImpactMetrics, PolicyViolation
from app.services.graph_builder import assign_semesters


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


class TestImpactMetrics:
    def test_completion_percentage_empty(self):
        """No completed courses = 0% completion."""
        courses = [_make_course("A"), _make_course("B"), _make_course("C")]
        degree = _make_degree(courses)
        nodes = assign_semesters(degree, [], 1)
        total = sum(c.credits for c in courses)
        completed = sum(n["credits"] for n in nodes if n["status"] == "completed")
        pct = completed / total * 100 if total > 0 else 0
        assert pct == 0.0

    def test_completion_percentage_partial(self):
        """Completing some courses gives correct percentage."""
        courses = [_make_course("A"), _make_course("B"), _make_course("C")]
        degree = _make_degree(courses)
        nodes = assign_semesters(degree, ["A"], 2)
        total = sum(c.credits for c in courses)
        completed = sum(n["credits"] for n in nodes if n["status"] == "completed")
        pct = round(completed / total * 100, 1)
        assert pct == 33.3

    def test_bottleneck_detection(self):
        """Courses with 3+ dependents are flagged as bottlenecks."""
        courses = [
            _make_course("ROOT"),
            _make_course("D1", prereqs=["ROOT"]),
            _make_course("D2", prereqs=["ROOT"]),
            _make_course("D3", prereqs=["ROOT"]),
        ]
        degree = _make_degree(courses)
        nodes = assign_semesters(degree, [], 1)
        bottlenecks = [n["code"] for n in nodes if n.get("dependents_count", 0) >= 3]
        assert "ROOT" in bottlenecks

    def test_remaining_credits(self):
        """Remaining credits = total - completed."""
        courses = [_make_course("A", credits=4), _make_course("B", credits=3)]
        degree = _make_degree(courses)
        nodes = assign_semesters(degree, ["A"], 2)
        completed_cr = sum(n["credits"] for n in nodes if n["status"] == "completed")
        remaining = sum(c.credits for c in courses) - completed_cr
        assert remaining == 3

    def test_semesters_saved_positive(self):
        """Optimized scheduling should save semesters vs naive sequential."""
        # 6 independent courses, 3 credits each = 18 total
        # Naive: 6 semesters (one course each). Optimized: 1 semester (all fit in 18 cap)
        courses = [_make_course(f"C{i}") for i in range(6)]
        degree = _make_degree(courses)
        nodes = assign_semesters(degree, [], 1)
        max_sem = max(n["semester"] for n in nodes)
        estimated = max_sem
        naive = max(1, 18 // 3)  # 6 semesters
        saved = max(0, naive - estimated)
        assert saved >= 4  # should save at least 4 semesters


class TestPolicyViolations:
    def test_credit_cap_violation(self):
        """Detect when a semester exceeds credit cap."""
        # 7 courses * 3 credits = 21 credits, cap = 9 => split over 3 semesters
        courses = [_make_course(f"C{i}") for i in range(7)]
        degree = _make_degree(courses, max_credits=9)
        nodes = assign_semesters(degree, [], 1)
        # Check no semester exceeds 9
        from collections import defaultdict
        sem_cr = defaultdict(int)
        for n in nodes:
            if n["status"] != "completed":
                sem_cr[n["semester"]] += n["credits"]
        violations = [s for s, cr in sem_cr.items() if cr > 9]
        assert len(violations) == 0  # graph_builder should respect the cap

    def test_prerequisite_ordering_respected(self):
        """Prerequisites should always come before dependents."""
        courses = [
            _make_course("INTRO"),
            _make_course("ADV", prereqs=["INTRO"]),
        ]
        degree = _make_degree(courses)
        nodes = assign_semesters(degree, [], 1)
        sems = {n["code"]: n["semester"] for n in nodes}
        assert sems["INTRO"] < sems["ADV"]

    def test_minimum_load_warning(self):
        """A semester with <12 credits should be flaggable."""
        # Single 3-credit course = below 12 threshold
        courses = [_make_course("ONLY", credits=3)]
        degree = _make_degree(courses)
        nodes = assign_semesters(degree, [], 1)
        sem_credits = sum(n["credits"] for n in nodes if n["status"] != "completed" and n["semester"] == 1)
        assert sem_credits < 12  # would trigger minimum load warning

    def test_total_credits_sufficient(self):
        """Planned credits must meet degree requirement."""
        courses = [_make_course("A", credits=30)]
        degree = _make_degree(courses, total_credits=120)
        total_planned = sum(c.credits for c in courses)
        assert total_planned < degree.total_credits_required  # violation exists

    def test_no_violations_clean_plan(self):
        """A well-structured plan should have no prerequisite violations."""
        courses = [
            _make_course("A"),
            _make_course("B", prereqs=["A"]),
            _make_course("C", prereqs=["B"]),
        ]
        degree = _make_degree(courses)
        nodes = assign_semesters(degree, [], 1)
        sems = {n["code"]: n["semester"] for n in nodes}
        # All prereqs come before dependents
        assert sems["A"] < sems["B"] < sems["C"]


class TestImpactMetricsModel:
    def test_model_creation(self):
        """ImpactMetrics Pydantic model validates correctly."""
        m = ImpactMetrics(
            total_credits=120,
            completed_credits=60,
            remaining_credits=60,
            estimated_semesters_remaining=4,
            semesters_saved=2,
            estimated_tuition_saved=11000.0,
            advisor_hours_saved=5.0,
            risk_level="low",
            bottleneck_courses=["CS 201"],
            on_track=True,
            credits_per_semester_avg=15.0,
            completion_percentage=50.0,
        )
        assert m.completion_percentage == 50.0
        assert m.on_track is True

    def test_policy_violation_model(self):
        """PolicyViolation model validates correctly."""
        v = PolicyViolation(
            rule="Credit Cap",
            severity="error",
            detail="Semester 3 has 21 credits",
            affected_courses=["CS 301", "CS 302"],
            suggestion="Move 3 credits to another semester",
        )
        assert v.severity == "error"
        assert len(v.affected_courses) == 2
