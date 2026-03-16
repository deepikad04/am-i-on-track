"""Agent Memory — cross-session learning for the orchestrator.

Stores patterns and insights from previous simulations so agents can
improve recommendations over time. This addresses the "no agent memory
across sessions" limitation.

Memory types:
- scenario_outcomes: What happened when a student ran X scenario
- course_patterns: Which courses frequently cause cascading delays
- policy_corrections: Which policy violations recur and how they were fixed
"""

import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Integer, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.db import Base

logger = logging.getLogger(__name__)


class AgentMemory(Base):
    """Persistent memory store for cross-session agent learning."""
    __tablename__ = "agent_memory"

    id = Column(String, primary_key=True)
    memory_type = Column(String, nullable=False, index=True)  # scenario_outcomes, course_patterns, policy_corrections
    key = Column(String, nullable=False, index=True)  # e.g., "drop_course:CS 225" or "bottleneck:CS 374"
    value = Column(Text, nullable=False)  # JSON payload
    frequency = Column(Integer, default=1)  # how often this pattern has been observed
    last_seen = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class AgentMemoryStore:
    """Read/write interface for agent memory, used by the orchestrator."""

    async def record_simulation_outcome(
        self,
        db: AsyncSession,
        scenario_type: str,
        parameters: dict,
        semesters_added: int,
        risk_level: str,
        correction_count: int,
        affected_courses: list[str],
    ):
        """Store a simulation outcome so future runs can reference past patterns."""
        from app.database.models import gen_id

        key = f"{scenario_type}:{json.dumps(sorted(parameters.items()))}"
        result = await db.execute(
            select(AgentMemory).where(
                AgentMemory.memory_type == "scenario_outcomes",
                AgentMemory.key == key,
            )
        )
        existing = result.scalar_one_or_none()

        outcome = {
            "semesters_added": semesters_added,
            "risk_level": risk_level,
            "correction_count": correction_count,
            "affected_courses": affected_courses,
        }

        if existing:
            # Merge with existing — keep running averages
            prev = json.loads(existing.value)
            freq = existing.frequency
            prev["semesters_added"] = round(
                (prev["semesters_added"] * freq + semesters_added) / (freq + 1), 1
            )
            prev["correction_count"] = round(
                (prev["correction_count"] * freq + correction_count) / (freq + 1), 1
            )
            # Track all affected courses across sessions
            all_courses = set(prev.get("affected_courses", []) + affected_courses)
            prev["affected_courses"] = list(all_courses)[:20]  # cap at 20
            prev["risk_level"] = risk_level  # latest wins
            existing.value = json.dumps(prev)
            existing.frequency += 1
            existing.last_seen = datetime.now(timezone.utc)
        else:
            mem = AgentMemory(
                id=gen_id(),
                memory_type="scenario_outcomes",
                key=key,
                value=json.dumps(outcome),
            )
            db.add(mem)

    async def record_course_bottleneck(
        self,
        db: AsyncSession,
        course_code: str,
        cascading_delays: int,
        downstream_courses: list[str],
    ):
        """Track courses that frequently cause cascading delays."""
        from app.database.models import gen_id

        key = f"bottleneck:{course_code}"
        result = await db.execute(
            select(AgentMemory).where(
                AgentMemory.memory_type == "course_patterns",
                AgentMemory.key == key,
            )
        )
        existing = result.scalar_one_or_none()

        pattern = {
            "cascading_delays": cascading_delays,
            "downstream_courses": downstream_courses,
        }

        if existing:
            prev = json.loads(existing.value)
            all_downstream = set(prev.get("downstream_courses", []) + downstream_courses)
            prev["downstream_courses"] = list(all_downstream)[:15]
            prev["cascading_delays"] = max(prev.get("cascading_delays", 0), cascading_delays)
            existing.value = json.dumps(prev)
            existing.frequency += 1
            existing.last_seen = datetime.now(timezone.utc)
        else:
            mem = AgentMemory(
                id=gen_id(),
                memory_type="course_patterns",
                key=key,
                value=json.dumps(pattern),
            )
            db.add(mem)

    async def record_policy_correction(
        self,
        db: AsyncSession,
        violation_rule: str,
        correction_applied: str,
    ):
        """Track which policy violations recur and how they were resolved."""
        from app.database.models import gen_id

        key = f"policy:{violation_rule}"
        result = await db.execute(
            select(AgentMemory).where(
                AgentMemory.memory_type == "policy_corrections",
                AgentMemory.key == key,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            prev = json.loads(existing.value)
            corrections = prev.get("corrections", [])
            if correction_applied not in corrections:
                corrections.append(correction_applied)
            prev["corrections"] = corrections[-10:]  # keep last 10
            existing.value = json.dumps(prev)
            existing.frequency += 1
            existing.last_seen = datetime.now(timezone.utc)
        else:
            mem = AgentMemory(
                id=gen_id(),
                memory_type="policy_corrections",
                key=key,
                value=json.dumps({"corrections": [correction_applied]}),
            )
            db.add(mem)

    async def get_scenario_history(
        self,
        db: AsyncSession,
        scenario_type: str,
        limit: int = 5,
    ) -> list[dict]:
        """Retrieve past scenario outcomes for a given type, ordered by frequency."""
        result = await db.execute(
            select(AgentMemory)
            .where(
                AgentMemory.memory_type == "scenario_outcomes",
                AgentMemory.key.startswith(f"{scenario_type}:"),
            )
            .order_by(AgentMemory.frequency.desc())
            .limit(limit)
        )
        memories = result.scalars().all()
        return [
            {"key": m.key, "frequency": m.frequency, **json.loads(m.value)}
            for m in memories
        ]

    async def get_known_bottlenecks(
        self,
        db: AsyncSession,
        min_frequency: int = 2,
    ) -> list[dict]:
        """Get courses known to cause cascading delays, based on past sessions."""
        result = await db.execute(
            select(AgentMemory)
            .where(
                AgentMemory.memory_type == "course_patterns",
                AgentMemory.frequency >= min_frequency,
            )
            .order_by(AgentMemory.frequency.desc())
            .limit(10)
        )
        memories = result.scalars().all()
        return [
            {"course": m.key.replace("bottleneck:", ""), "frequency": m.frequency, **json.loads(m.value)}
            for m in memories
        ]

    async def get_context_for_simulation(
        self,
        db: AsyncSession,
        scenario_type: str,
    ) -> str:
        """Build a memory context string to inject into agent prompts.

        Gives agents awareness of past outcomes for similar scenarios.
        """
        history = await self.get_scenario_history(db, scenario_type, limit=3)
        bottlenecks = await self.get_known_bottlenecks(db, min_frequency=2)

        if not history and not bottlenecks:
            return ""

        lines = ["AGENT MEMORY (learned from prior sessions):"]

        if history:
            lines.append("Past outcomes for similar scenarios:")
            for h in history:
                lines.append(
                    f"  - Seen {h['frequency']}x: avg {h.get('semesters_added', '?')} extra semesters, "
                    f"risk={h.get('risk_level', '?')}, corrections={h.get('correction_count', 0)}"
                )

        if bottlenecks:
            lines.append("Known bottleneck courses (cause cascading delays):")
            for b in bottlenecks:
                lines.append(
                    f"  - {b['course']} (seen {b['frequency']}x): "
                    f"delays {b.get('cascading_delays', '?')} downstream courses"
                )

        return "\n".join(lines)


# Singleton
memory_store = AgentMemoryStore()
