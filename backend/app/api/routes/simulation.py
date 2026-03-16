import asyncio
import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.db import get_db
from app.database.models import Degree, Session, StudentProgressRecord, Simulation, User, gen_id
from pydantic import BaseModel
from app.models.schemas import Scenario, ScenarioType, DegreeRequirement
from app.agents.orchestrator import orchestrator
from app.services.auth import get_current_user
from app.services.graph_builder import assign_semesters

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/simulate")
async def run_simulation(
    scenario: Scenario,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run a what-if simulation and stream agent events via SSE."""
    # Validate scenario parameters
    validation_error = scenario.validate_parameters()
    if validation_error:
        raise HTTPException(status_code=422, detail=validation_error)

    # Load degree data with ownership check
    result = await db.execute(
        select(Degree).join(Session).where(
            Degree.session_id == scenario.session_id,
            (Session.user_id == user.id) | (scenario.session_id == "demo_session"),
        )
    )
    degree = result.scalar_one_or_none()
    if not degree or not degree.parsed_json:
        raise HTTPException(status_code=404, detail="No parsed degree found for this session")

    degree_data = json.loads(degree.parsed_json)

    # Load second degree for add_major/add_minor scenarios
    second_degree_data = None
    second_degree = None
    if scenario.type in (ScenarioType.add_major, ScenarioType.add_minor):
        degree_session_id = scenario.parameters.get("degree_session_id")
        if not degree_session_id:
            raise HTTPException(status_code=422, detail="degree_session_id is required for add_major/add_minor scenarios")
        if degree_session_id:
            second_result = await db.execute(
                select(Degree).join(Session).where(
                    Degree.session_id == degree_session_id,
                    (Session.user_id == user.id) | (degree_session_id == "demo_session"),
                )
            )
            second_degree = second_result.scalar_one_or_none()
            if not second_degree:
                logger.warning(f"Second degree not found for session {degree_session_id}")
                raise HTTPException(status_code=404, detail="Second degree not found. Please re-upload the PDF.")
            if not second_degree.parsed_json:
                logger.warning(f"Second degree found but not parsed: session={degree_session_id} status={second_degree.status}")
                raise HTTPException(status_code=400, detail="Second degree PDF was not parsed successfully. Please re-upload.")
            second_degree_data = json.loads(second_degree.parsed_json)

    # Load student progress
    progress_result = await db.execute(
        select(StudentProgressRecord).where(
            StudentProgressRecord.session_id == scenario.session_id,
            StudentProgressRecord.degree_id == degree.id,
        )
    )
    progress = progress_result.scalar_one_or_none()
    completed = json.loads(progress.completed_courses) if progress else []
    current_sem = progress.current_semester if progress else 1

    # Create simulation record
    sim_id = gen_id()

    async def event_stream():
        try:
            final_data = None
            async for event in orchestrator.run_simulation(
                scenario=scenario,
                degree_data=degree_data,
                completed_courses=completed,
                current_semester=current_sem,
                second_degree_data=second_degree_data,
                pdf_path_1=degree.raw_pdf_path,
                pdf_path_2=second_degree.raw_pdf_path if second_degree else None,
            ):
                if event is None:
                    yield ": heartbeat\n\n"
                    continue
                yield f"data: {event.model_dump_json()}\n\n"
                if event.data and "simulation" in event.data:
                    final_data = event.data

            # Save simulation result
            if final_data:
                sim = Simulation(
                    id=sim_id,
                    session_id=scenario.session_id,
                    degree_id=degree.id,
                    scenario_type=scenario.type.value,
                    parameters=json.dumps(scenario.parameters),
                    result=json.dumps(final_data.get("simulation", {})),
                    explanation=final_data.get("explanation", ""),
                    parent_simulation_id=scenario.parent_simulation_id,
                )
                db.add(sim)
                await db.commit()

                # Record to agent memory for cross-session learning
                try:
                    from app.services.agent_memory import memory_store
                    sim_data = final_data.get("simulation", {})
                    await memory_store.record_simulation_outcome(
                        db=db,
                        scenario_type=scenario.type.value,
                        parameters=scenario.parameters,
                        semesters_added=sim_data.get("semesters_added", 0),
                        risk_level=sim_data.get("risk_level", "low"),
                        correction_count=final_data.get("correction_count", 0),
                        affected_courses=[c.get("code", "") for c in sim_data.get("affected_courses", [])],
                    )
                    # Track bottleneck courses
                    for course in sim_data.get("affected_courses", []):
                        if course.get("reason", "").lower().startswith("prerequisite"):
                            await memory_store.record_course_bottleneck(
                                db=db,
                                course_code=course["code"],
                                cascading_delays=len(sim_data.get("affected_courses", [])),
                                downstream_courses=[c["code"] for c in sim_data.get("affected_courses", [])],
                            )
                    await db.commit()
                except Exception as mem_err:
                    logger.debug(f"Agent memory recording skipped: {mem_err}")

        except (asyncio.CancelledError, GeneratorExit):
            logger.info(f"Client disconnected during simulation for session {scenario.session_id}")
            raise
        except Exception as e:
            logger.error(f"Simulation stream error: {e}")
            from app.models.schemas import AgentEvent, AgentName, AgentEventType
            err_event = AgentEvent(
                agent=AgentName.simulator, event_type=AgentEventType.error,
                message=str(e), timestamp=0,
            )
            yield f"data: {err_event.model_dump_json()}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/simulate/{simulation_id}/result")
async def get_simulation_result(
    simulation_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch a cached simulation result."""
    result = await db.execute(
        select(Simulation).join(Session, Simulation.session_id == Session.id).where(
            Simulation.id == simulation_id,
            (Session.user_id == user.id) | (Session.id == "demo_session"),
        )
    )
    sim = result.scalar_one_or_none()
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")

    return {
        "id": sim.id,
        "scenario_type": sim.scenario_type,
        "parameters": json.loads(sim.parameters),
        "result": json.loads(sim.result) if sim.result else None,
        "explanation": sim.explanation,
    }


@router.get("/simulate/{session_id}/history")
async def get_simulation_history(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all past simulations for a session, enabling scenario comparison."""
    result = await db.execute(
        select(Simulation).join(Session, Simulation.session_id == Session.id).where(
            Simulation.session_id == session_id,
            (Session.user_id == user.id) | (Session.id == "demo_session"),
        ).order_by(Simulation.id)
    )
    sims = result.scalars().all()
    return [
        {
            "id": sim.id,
            "scenario_type": sim.scenario_type,
            "parameters": json.loads(sim.parameters),
            "result": json.loads(sim.result) if sim.result else None,
            "explanation": sim.explanation,
            "parent_simulation_id": sim.parent_simulation_id,
        }
        for sim in sims
    ]


class DebateRequest(BaseModel):
    session_id: str


@router.post("/simulate/debate")
async def run_debate(
    request: DebateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Agent Debate: Fast Track vs Safe Path, streamed via SSE in parallel."""
    if request.session_id == "demo_session":
        result = await db.execute(
            select(Degree).where(Degree.session_id == request.session_id)
        )
    else:
        result = await db.execute(
            select(Degree).join(Session).where(
                Degree.session_id == request.session_id,
                Session.user_id == user.id,
            )
        )
    degree = result.scalar_one_or_none()
    if not degree or not degree.parsed_json:
        raise HTTPException(status_code=404, detail="No parsed degree found")

    degree_data = json.loads(degree.parsed_json)
    degree_req = DegreeRequirement.model_validate(degree_data)

    progress_result = await db.execute(
        select(StudentProgressRecord).where(
            StudentProgressRecord.session_id == request.session_id,
            StudentProgressRecord.degree_id == degree.id,
        )
    )
    progress = progress_result.scalar_one_or_none()
    completed = json.loads(progress.completed_courses) if progress else []
    current_sem = progress.current_semester if progress else 1

    course_nodes = assign_semesters(degree_req, completed, current_sem)
    remaining = [n for n in course_nodes if n["status"] != "completed"]
    remaining_text = ", ".join(f"{n['code']} ({n['credits']}cr)" for n in remaining[:30])

    async def event_stream():
        try:
            async for event in orchestrator.run_debate(
                degree_data=degree_data,
                completed_courses=completed,
                current_semester=current_sem,
                remaining_courses=remaining_text,
            ):
                if event is None:
                    yield ": heartbeat\n\n"
                    continue
                yield f"data: {event.model_dump_json()}\n\n"
        except (asyncio.CancelledError, GeneratorExit):
            logger.info("Client disconnected during debate")
            raise
        except Exception as e:
            logger.error(f"Debate stream error: {e}")
            from app.models.schemas import AgentEvent, AgentName, AgentEventType
            err_event = AgentEvent(
                agent=AgentName.debate_fast, event_type=AgentEventType.error,
                message=str(e), timestamp=0,
            )
            yield f"data: {err_event.model_dump_json()}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
