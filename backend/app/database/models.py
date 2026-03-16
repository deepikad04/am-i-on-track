import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer
from app.database.db import Base


def gen_id() -> str:
    return uuid.uuid4().hex[:12]


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=gen_id)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    institution_id = Column(String, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Session(Base):
    __tablename__ = "sessions"
    id = Column(String, primary_key=True, default=gen_id)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    student_name = Column(String, nullable=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    institution_id = Column(String, nullable=True, index=True)


class Degree(Base):
    __tablename__ = "degrees"
    id = Column(String, primary_key=True, default=gen_id)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    degree_name = Column(String, nullable=True)
    raw_pdf_path = Column(String, nullable=True)
    parsed_json = Column(Text, nullable=True)  # JSON string of DegreeRequirement
    embeddings_json = Column(Text, nullable=True)  # JSON: {course_code: [float,...]}
    status = Column(String, default="pending")  # pending, parsing, parsed, error


class StudentProgressRecord(Base):
    __tablename__ = "student_progress"
    id = Column(String, primary_key=True, default=gen_id)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    degree_id = Column(String, ForeignKey("degrees.id"), nullable=False)
    completed_courses = Column(Text, default="[]")  # JSON list of course codes
    current_semester = Column(Integer, default=1)


class Simulation(Base):
    __tablename__ = "simulations"
    id = Column(String, primary_key=True, default=gen_id)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    degree_id = Column(String, ForeignKey("degrees.id"), nullable=False)
    scenario_type = Column(String, nullable=False)
    parameters = Column(Text, default="{}")  # JSON
    result = Column(Text, nullable=True)  # JSON of SimulationResult
    explanation = Column(Text, nullable=True)
    parent_simulation_id = Column(String, ForeignKey("simulations.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class CourseExplanationCache(Base):
    __tablename__ = "course_explanation_cache"
    id = Column(String, primary_key=True, default=gen_id)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    course_code = Column(String, nullable=False)
    completed_hash = Column(String, nullable=False)
    explanation = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
