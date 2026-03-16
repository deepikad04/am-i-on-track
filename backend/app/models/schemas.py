from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# --- Degree Models ---

class Course(BaseModel):
    code: str
    name: str
    credits: int
    prerequisites: list[str] = []
    corequisites: list[str] = []
    category: str
    typical_semester: Optional[int] = None
    is_required: bool = True
    available_semesters: list[str] = ["fall", "spring"]


class CategoryRequirement(BaseModel):
    name: str
    min_credits: int
    min_courses: int
    courses: list[str]


class DegreeRequirement(BaseModel):
    degree_name: str
    institution: Optional[str] = None
    total_credits_required: int
    courses: list[Course]
    categories: list[CategoryRequirement] = []
    constraints: list[str] = []
    max_credits_per_semester: int = 18


# --- Student Progress ---

class StudentProgress(BaseModel):
    completed_courses: list[str] = []
    current_semester: int = 1


# --- Simulation Models ---

class ScenarioType(str, Enum):
    drop_course = "drop_course"
    block_semester = "block_semester"
    add_major = "add_major"
    add_minor = "add_minor"
    set_goal = "set_goal"
    study_abroad = "study_abroad"
    coop = "coop"
    gap_semester = "gap_semester"


class Scenario(BaseModel):
    type: ScenarioType
    parameters: dict = {}
    session_id: str
    degree_id: str
    parent_simulation_id: str | None = None

    def validate_parameters(self) -> str | None:
        """Validate parameters for the given scenario type. Returns error message or None."""
        p = self.parameters
        if self.type == ScenarioType.drop_course:
            if not p.get("course_code"):
                return "drop_course requires 'course_code' parameter"
        elif self.type == ScenarioType.block_semester:
            if not isinstance(p.get("semester"), int):
                return "block_semester requires integer 'semester' parameter"
        elif self.type in (ScenarioType.add_major, ScenarioType.add_minor):
            if not p.get("degree_session_id"):
                return f"{self.type.value} requires 'degree_session_id' parameter"
        elif self.type == ScenarioType.set_goal:
            if not p.get("target_semester"):
                return "set_goal requires 'target_semester' parameter"
        elif self.type == ScenarioType.study_abroad:
            if not isinstance(p.get("semester"), int):
                return "study_abroad requires integer 'semester' parameter"
        elif self.type == ScenarioType.coop:
            if not isinstance(p.get("semester"), int):
                return "coop requires integer 'semester' parameter"
        elif self.type == ScenarioType.gap_semester:
            if not isinstance(p.get("semester"), int):
                return "gap_semester requires integer 'semester' parameter"
        return None


class AffectedCourse(BaseModel):
    code: str
    name: str
    original_semester: int
    new_semester: int
    reason: str


class ConstraintCheck(BaseModel):
    label: str
    passed: bool
    severity: str = "ok"  # ok, warning, error
    detail: str
    related_courses: list[str] = []


class PlanComparison(BaseModel):
    graduation_date: tuple[str, str]
    avg_credits_per_term: tuple[float, float]
    risk_level: tuple[str, str]
    summer_reliance: tuple[str, str]
    gpa_protection_score: tuple[int, int]


class SimulationResult(BaseModel):
    original_graduation: str
    new_graduation: str
    semesters_added: int
    affected_courses: list[AffectedCourse]
    credit_impact: int
    risk_level: str = "low"  # low, medium, high
    reasoning_steps: list[str] = []
    recommendations: list[str] = []
    constraint_checks: list[ConstraintCheck] = []
    plan_comparison: Optional[PlanComparison] = None


# --- Agent Models ---

class ImpactMetrics(BaseModel):
    """Quantified outcomes for institutional impact reporting."""
    total_credits: int
    completed_credits: int
    remaining_credits: int
    estimated_semesters_remaining: int
    semesters_saved: int = 0  # vs naive sequential scheduling
    estimated_tuition_saved: float = 0.0  # semesters_saved * avg tuition
    advisor_hours_saved: float = 0.0  # estimated manual advising time replaced
    risk_level: str = "low"  # overall risk: low, medium, high
    bottleneck_courses: list[str] = []  # courses blocking 3+ dependents
    on_track: bool = True  # whether student is on track for target graduation
    credits_per_semester_avg: float = 0.0
    completion_percentage: float = 0.0


class PolicyViolation(BaseModel):
    """A university policy violation detected by the Policy Agent."""
    rule: str
    severity: str = "warning"  # warning, error
    detail: str
    affected_courses: list[str] = []
    suggestion: str = ""


class PolicyCheckResult(BaseModel):
    """Result of policy agent checking a degree plan."""
    violations: list[PolicyViolation] = []
    passed: bool = True
    summary: str = ""


class AgentName(str, Enum):
    interpreter = "interpreter"
    overlap = "overlap"
    simulator = "simulator"
    explanation = "explanation"
    advisor = "advisor"
    policy = "policy"
    debate_fast = "debate_fast"
    debate_safe = "debate_safe"
    risk_scoring = "risk_scoring"
    jury = "jury"


class AgentEventType(str, Enum):
    start = "start"
    thinking = "thinking"
    complete = "complete"
    error = "error"


class AgentEvent(BaseModel):
    agent: AgentName
    event_type: AgentEventType
    step: Optional[int] = None
    message: str
    data: Optional[dict] = None
    timestamp: float


# --- API Response Models ---

class UploadResponse(BaseModel):
    session_id: str
    message: str = "PDF uploaded and processing started"


class HealthResponse(BaseModel):
    status: str = "ok"
    bedrock_connected: bool = False


class DegreeResponse(BaseModel):
    session_id: str
    degree_id: str
    status: str
    degree: Optional[DegreeRequirement] = None


# --- Tool Use schema for Nova ---

DEGREE_TOOL_SCHEMA = {
    "toolSpec": {
        "name": "parse_degree_requirements",
        "description": "Parse degree requirements from a PDF into structured JSON format",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "degree_name": {"type": "string", "description": "Name of the degree program"},
                    "institution": {"type": "string", "description": "University or college name"},
                    "total_credits_required": {"type": "integer", "description": "Total credits needed to graduate"},
                    "max_credits_per_semester": {"type": "integer", "description": "Maximum credits allowed per semester"},
                    "courses": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "code": {"type": "string", "description": "Course code (e.g., CS 101)"},
                                "name": {"type": "string", "description": "Course name"},
                                "credits": {"type": "integer", "description": "Number of credits"},
                                "prerequisites": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "List of prerequisite course codes"
                                },
                                "corequisites": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "List of corequisite course codes"
                                },
                                "category": {"type": "string", "description": "Category (e.g., Core, Elective, General Education)"},
                                "typical_semester": {"type": "integer", "description": "Recommended semester to take this course"},
                                "is_required": {"type": "boolean", "description": "Whether this course is required"},
                                "available_semesters": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Semesters when offered (fall, spring, summer)"
                                }
                            },
                            "required": ["code", "name", "credits", "category"]
                        }
                    },
                    "categories": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "min_credits": {"type": "integer"},
                                "min_courses": {"type": "integer"},
                                "courses": {"type": "array", "items": {"type": "string"}}
                            },
                            "required": ["name", "min_credits", "min_courses", "courses"]
                        }
                    },
                    "constraints": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Additional degree constraints or notes"
                    }
                },
                "required": ["degree_name", "total_credits_required", "courses"]
            }
        }
    }
}

SIMULATION_TOOL_SCHEMA = {
    "toolSpec": {
        "name": "submit_simulation_result",
        "description": "Submit the structured simulation result analyzing the impact of an academic scenario",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "original_graduation": {"type": "string", "description": "Original graduation date (e.g. Spring 2027)"},
                    "new_graduation": {"type": "string", "description": "New graduation date after scenario"},
                    "semesters_added": {"type": "integer", "description": "Number of additional semesters needed"},
                    "affected_courses": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "code": {"type": "string"},
                                "name": {"type": "string"},
                                "original_semester": {"type": "integer"},
                                "new_semester": {"type": "integer"},
                                "reason": {"type": "string"}
                            },
                            "required": ["code", "name", "original_semester", "new_semester", "reason"]
                        }
                    },
                    "credit_impact": {"type": "integer", "description": "Total credits shifted"},
                    "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
                    "reasoning_steps": {"type": "array", "items": {"type": "string"}},
                    "recommendations": {"type": "array", "items": {"type": "string"}},
                    "constraint_checks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "label": {"type": "string"},
                                "passed": {"type": "boolean"},
                                "severity": {"type": "string", "enum": ["ok", "warning", "error"]},
                                "detail": {"type": "string"},
                                "related_courses": {"type": "array", "items": {"type": "string"}}
                            },
                            "required": ["label", "passed", "detail"]
                        }
                    }
                },
                "required": ["original_graduation", "new_graduation", "semesters_added", "affected_courses", "credit_impact", "risk_level"]
            }
        }
    }
}

OVERLAP_TOOL_SCHEMA = {
    "toolSpec": {
        "name": "submit_overlap_analysis",
        "description": "Submit the structured overlap analysis comparing two degree programs",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "exact_matches": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "code": {"type": "string"},
                                "name": {"type": "string"},
                                "credits": {"type": "integer"}
                            },
                            "required": ["code", "name", "credits"]
                        },
                        "description": "Courses that appear identically in both degrees"
                    },
                    "equivalent_courses": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "degree1_code": {"type": "string"},
                                "degree2_code": {"type": "string"},
                                "name": {"type": "string"},
                                "credits": {"type": "integer"},
                                "similarity_reason": {"type": "string"}
                            },
                            "required": ["degree1_code", "degree2_code", "name", "credits", "similarity_reason"]
                        },
                        "description": "Courses that are equivalent across the two degrees"
                    },
                    "shared_prerequisites": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Prerequisites shared by both degrees"
                    },
                    "total_shared_credits": {
                        "type": "integer",
                        "description": "Total number of credits shared between both degrees"
                    },
                    "additional_courses_needed": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "code": {"type": "string"},
                                "name": {"type": "string"},
                                "credits": {"type": "integer"},
                                "from_degree": {"type": "string"}
                            },
                            "required": ["code", "name", "credits", "from_degree"]
                        },
                        "description": "Additional courses needed to complete both degrees"
                    },
                    "additional_semesters_estimate": {
                        "type": "integer",
                        "description": "Estimated additional semesters needed for the second degree"
                    },
                    "recommendations": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Recommendations for pursuing both degrees"
                    }
                },
                "required": ["exact_matches", "total_shared_credits", "additional_semesters_estimate"]
            }
        }
    }
}

POLICY_TOOL_SCHEMA = {
    "toolSpec": {
        "name": "submit_policy_violations",
        "description": "Submit policy violations found in a degree plan",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "violations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "rule": {"type": "string"},
                                "severity": {"type": "string", "enum": ["warning", "error"]},
                                "detail": {"type": "string"},
                                "affected_courses": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "suggestion": {"type": "string"}
                            },
                            "required": ["rule", "severity", "detail"]
                        },
                        "description": "List of policy violations detected in the degree plan"
                    }
                },
                "required": ["violations"]
            }
        }
    }
}
