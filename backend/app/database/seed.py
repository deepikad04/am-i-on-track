"""Pre-load sample degree data so the demo never depends on live API latency."""

import json
import logging
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.models import Session, Degree, gen_id

logger = logging.getLogger(__name__)

SAMPLE_DIR = Path(__file__).parent.parent / "data" / "sample_degrees"


async def seed_sample_data(db: AsyncSession):
    """Load sample degree data into the database if not already present."""
    # Check if sample session already exists
    result = await db.execute(select(Session).where(Session.id == "demo_session"))
    if result.scalar_one_or_none():
        logger.info("Sample data already seeded")
        return

    # Load CS BS sample
    cs_path = SAMPLE_DIR / "cs_bs_parsed.json"
    if not cs_path.exists():
        logger.warning(f"Sample file not found: {cs_path}")
        return

    cs_data = json.loads(cs_path.read_text())

    # Create demo session — flush first so FK exists for the degree insert
    session = Session(id="demo_session", student_name="Demo Student")
    db.add(session)
    await db.flush()

    # Create degree record with pre-parsed data
    degree = Degree(
        id="demo_degree",
        session_id="demo_session",
        degree_name=cs_data["degree_name"],
        parsed_json=json.dumps(cs_data),
        status="parsed",
    )
    db.add(degree)

    await db.commit()
    logger.info(f"Seeded sample data: {cs_data['degree_name']} with {len(cs_data['courses'])} courses")
