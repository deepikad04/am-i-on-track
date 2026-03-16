import asyncio
import logging
from typing import AsyncGenerator
from app.models.schemas import AgentEvent, AgentEventType, AgentName, Scenario
from app.agents.degree_interpreter import DegreeInterpreterAgent
from app.agents.trajectory_simulator import TrajectorySimulatorAgent
from app.agents.explanation_agent import ExplanationAgent
from app.agents.overlap_analyzer import OverlapAnalyzerAgent
from app.agents.policy_agent import PolicyAgent
from app.agents.debate_agents import FastTrackAgent, SafePathAgent
from app.agents.risk_scoring_agent import RiskScoringAgent
from app.agents.jury_agent import JuryAgent

logger = logging.getLogger(__name__)

_SENTINEL = object()  # marks end of stream
_HEARTBEAT_INTERVAL = 15  # seconds


_MAX_CORRECTIONS = 2  # max self-correction iterations


def _build_course_nodes_from_simulation(
    degree_data: dict,
    completed_courses: list[str],
    current_semester: int,
    sim_result: dict,
) -> list[dict]:
    """Build course_nodes from sim_result for PolicyAgent validation.

    Merges the original degree courses with the simulator's affected_courses
    (semester reassignments) to produce the node format PolicyAgent expects.
    """
    courses = degree_data.get("courses", [])
    course_map = {c["code"]: c for c in courses if isinstance(c, dict)}
    completed_set = set(completed_courses)

    # Map of semester reassignments from affected_courses
    reassignments = {}
    for ac in sim_result.get("affected_courses", []):
        reassignments[ac["code"]] = ac.get("new_semester", current_semester)

    nodes = []
    for course in courses:
        if not isinstance(course, dict):
            continue
        code = course["code"]
        is_completed = code in completed_set

        if code in reassignments:
            semester = reassignments[code]
        elif is_completed:
            semester = 0
        else:
            semester = course.get("typical_semester") or current_semester

        nodes.append({
            "code": code,
            "name": course.get("name", code),
            "semester": semester,
            "credits": course.get("credits", 3),
            "status": "completed" if is_completed else "scheduled",
            "prerequisites": course.get("prerequisites", []),
        })

    return nodes


class Orchestrator:
    """Multi-agent coordinator using supervisor pattern with self-correction."""

    def __init__(self):
        self.interpreter = DegreeInterpreterAgent()
        self.simulator = TrajectorySimulatorAgent()
        self.explanation = ExplanationAgent()
        self.overlap = OverlapAnalyzerAgent()
        self.policy = PolicyAgent()
        self.fast_track = FastTrackAgent()
        self.safe_path = SafePathAgent()
        self.risk_scorer = RiskScoringAgent()
        self.jury = JuryAgent()

    async def run_parse(
        self,
        pdf_path: str | None = None,
        text: str | None = None,
        image_path: str | None = None,
        image_format: str | None = None,
        video_path: str | None = None,
        video_format: str | None = None,
    ) -> AsyncGenerator[AgentEvent | None, None]:
        """Run the degree interpreter agent and yield events in real time.
        Accepts a pdf_path, pre-extracted text, image_path (multimodal), or video_path (screen recording).
        Yields None as a heartbeat marker when idle."""
        queue: asyncio.Queue = asyncio.Queue()
        result_holder: list[dict] = [{}]

        async def emit(event: AgentEvent):
            await queue.put(event)

        async def _run():
            try:
                input_data = {}
                if text:
                    input_data["text"] = text
                elif video_path:
                    input_data["video_path"] = video_path
                    input_data["video_format"] = video_format or "mp4"
                elif image_path:
                    input_data["image_path"] = image_path
                    input_data["image_format"] = image_format or "png"
                elif pdf_path:
                    input_data["pdf_path"] = pdf_path
                result_holder[0] = await self.interpreter.run(input_data, emit)
            except Exception as e:
                logger.error(f"Interpreter agent error: {e}")
                await queue.put(AgentEvent(
                    agent=AgentName.interpreter,
                    event_type=AgentEventType.error,
                    message=str(e),
                    timestamp=0,
                ))
            finally:
                await queue.put(_SENTINEL)

        task = asyncio.create_task(_run())
        try:
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=_HEARTBEAT_INTERVAL)
                except asyncio.TimeoutError:
                    yield None  # heartbeat marker
                    continue
                if item is _SENTINEL:
                    break
                yield item

            # Yield final result
            result = result_holder[0]
            if "degree" in result:
                yield AgentEvent(
                    agent=AgentName.interpreter,
                    event_type=AgentEventType.complete,
                    message="Degree parsing complete",
                    data=result,
                    timestamp=0,
                )
        except (asyncio.CancelledError, GeneratorExit):
            task.cancel()
            logger.info("Client disconnected during parse, task cancelled")
            raise

    async def run_simulation(
        self,
        scenario: Scenario,
        degree_data: dict,
        completed_courses: list[str],
        current_semester: int,
        second_degree_data: dict | None = None,
        pdf_path_1: str | None = None,
        pdf_path_2: str | None = None,
    ) -> AsyncGenerator[AgentEvent | None, None]:
        """Run simulation pipeline: simulator -> explanation agent. Events stream in real time."""
        queue: asyncio.Queue = asyncio.Queue()
        combined_holder: list[dict] = [{}]

        async def emit(event: AgentEvent):
            await queue.put(event)

        async def _run():
            try:
                correction_count = 0
                policy_violations_context = None
                policy_result = None
                overlap_result = None

                # For add_major/add_minor: run overlap analysis first
                if scenario.type.value in ("add_major", "add_minor") and second_degree_data:
                    await emit(AgentEvent(
                        agent=AgentName.overlap,
                        event_type=AgentEventType.start,
                        message="Running overlap analysis between degrees...",
                        timestamp=0,
                    ))
                    overlap_input = {"degree1": degree_data, "degree2": second_degree_data}
                    if pdf_path_1:
                        overlap_input["pdf_path_1"] = pdf_path_1
                    if pdf_path_2:
                        overlap_input["pdf_path_2"] = pdf_path_2
                    overlap_raw = await self.overlap.run(overlap_input, emit)
                    overlap_result = overlap_raw.get("overlap", {})

                    # Merge: add non-overlapping courses from second degree into primary
                    primary_codes = {c["code"] for c in degree_data.get("courses", []) if isinstance(c, dict)}
                    overlap_codes = set()
                    for m in overlap_result.get("exact_matches", []):
                        overlap_codes.add(m.get("code", ""))
                    for eq in overlap_result.get("equivalent_courses", []):
                        overlap_codes.add(eq.get("degree2_code", ""))

                    additional_courses = []
                    for c in second_degree_data.get("courses", []):
                        if isinstance(c, dict) and c["code"] not in primary_codes and c["code"] not in overlap_codes:
                            additional_courses.append(c)

                    # Build merged degree data for the simulator
                    merged_degree = dict(degree_data)
                    merged_degree["courses"] = list(degree_data.get("courses", [])) + additional_courses
                    merged_degree["total_credits_required"] = (
                        degree_data.get("total_credits_required", 120) +
                        second_degree_data.get("total_credits_required", 0) -
                        overlap_result.get("total_shared_credits", 0)
                    )
                    degree_for_sim = merged_degree
                else:
                    degree_for_sim = degree_data

                sim_input = {
                    "degree": degree_for_sim,
                    "scenario_type": scenario.type.value,
                    "parameters": scenario.parameters,
                    "completed_courses": completed_courses,
                    "current_semester": current_semester,
                }

                # Inject agent memory context from prior sessions
                memory_insights = None
                try:
                    from app.services.agent_memory import memory_store
                    from app.database.db import async_session as _mem_session
                    async with _mem_session() as mem_db:
                        memory_context = await memory_store.get_context_for_simulation(
                            mem_db, scenario.type.value,
                        )
                        if memory_context:
                            sim_input["memory_context"] = memory_context

                        # Fetch structured insights for the feedback loop
                        scenario_history = await memory_store.get_scenario_history(
                            mem_db, scenario.type.value, limit=3,
                        )
                        known_bottlenecks = await memory_store.get_known_bottlenecks(
                            mem_db, min_frequency=1,
                        )

                        if scenario_history or known_bottlenecks:
                            memory_insights = {
                                "scenario_history": scenario_history,
                                "known_bottlenecks": known_bottlenecks,
                            }
                            # Emit visible memory recall event so UI shows the feedback loop
                            recall_parts = []
                            if scenario_history:
                                recall_parts.append(
                                    f"Recalled {len(scenario_history)} past {scenario.type.value} outcome(s)"
                                )
                            if known_bottlenecks:
                                codes = [b["course"] for b in known_bottlenecks[:5]]
                                recall_parts.append(
                                    f"Known bottlenecks: {', '.join(codes)}"
                                )
                            await emit(AgentEvent(
                                agent=AgentName.simulator,
                                event_type=AgentEventType.thinking,
                                message=f"Memory recall: {' | '.join(recall_parts)}",
                                step=0,
                                data={"memory_recall": memory_insights},
                                timestamp=0,
                            ))
                except Exception as mem_err:
                    logger.debug(f"Agent memory lookup skipped: {mem_err}")

                # Add context about overlap for the simulator prompt
                if overlap_result:
                    sim_input["overlap_info"] = {
                        "shared_credits": overlap_result.get("total_shared_credits", 0),
                        "additional_courses_count": len(degree_for_sim.get("courses", [])) - len(degree_data.get("courses", [])),
                        "second_degree_name": second_degree_data.get("degree_name", "Second Degree") if second_degree_data else "",
                    }

                for iteration in range(_MAX_CORRECTIONS + 1):
                    # Inject violation context on correction iterations
                    if policy_violations_context is not None:
                        sim_input["policy_violations"] = policy_violations_context

                    # Phase 1: Run trajectory simulator
                    sim_result = await self.simulator.run(sim_input, emit)
                    if "error" in sim_result:
                        return

                    # Phase 2: Policy self-correction check
                    course_nodes = _build_course_nodes_from_simulation(
                        degree_for_sim, completed_courses, current_semester,
                        sim_result.get("result", {}),
                    )

                    policy_result = await self.policy.run(
                        {
                            "degree": degree_for_sim,
                            "course_nodes": course_nodes,
                            "completed_courses": completed_courses,
                            "current_semester": current_semester,
                        },
                        emit,
                    )

                    # Check for error-severity violations
                    error_violations = [
                        v for v in policy_result.get("violations", [])
                        if v.get("severity") == "error"
                    ]

                    if not error_violations or iteration == _MAX_CORRECTIONS:
                        break

                    # Feed violations back for correction
                    correction_count += 1
                    policy_violations_context = error_violations
                    await emit(AgentEvent(
                        agent=AgentName.simulator,
                        event_type=AgentEventType.thinking,
                        message=f"Policy violations detected — re-running simulation (correction {correction_count}/{_MAX_CORRECTIONS})",
                        step=None,
                        data={"correction_attempt": correction_count, "violations_count": len(error_violations)},
                        timestamp=0,
                    ))

                # Phase 3 & 4: Run risk scoring + explanation in parallel
                # (no dependency between them — risk uses graph data, explanation uses sim result)
                # Inject memory-learned bottlenecks into risk scoring for active feedback loop
                risk_input = {
                    "course_nodes": course_nodes,
                    "degree": degree_for_sim,
                    "completed_courses": completed_courses,
                    "current_semester": current_semester,
                }
                if memory_insights and memory_insights.get("known_bottlenecks"):
                    risk_input["memory_bottlenecks"] = memory_insights["known_bottlenecks"]

                scenario_desc = f"{scenario.type.value}: {scenario.parameters}"
                risk_result, explanation_result = await asyncio.gather(
                    self.risk_scorer.run(risk_input,
                        emit,
                    ),
                    self.explanation.run(
                        {
                            "simulation_result": sim_result.get("result", {}),
                            "scenario_description": scenario_desc,
                        },
                        emit,
                    ),
                )

                combined = {
                    "simulation": sim_result.get("result", {}),
                    "explanation": explanation_result.get("explanation", ""),
                    "policy_check": policy_result,
                    "risk_score": risk_result,
                    "correction_count": correction_count,
                }
                if overlap_result:
                    combined["overlap"] = overlap_result
                combined_holder[0] = combined
            except Exception as e:
                logger.error(f"Simulation pipeline error: {e}")
                await queue.put(AgentEvent(
                    agent=AgentName.simulator,
                    event_type=AgentEventType.error,
                    message=str(e),
                    timestamp=0,
                ))
            finally:
                await queue.put(_SENTINEL)

        task = asyncio.create_task(_run())
        try:
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=_HEARTBEAT_INTERVAL)
                except asyncio.TimeoutError:
                    yield None  # heartbeat marker
                    continue
                if item is _SENTINEL:
                    break
                yield item

            # Yield final combined result
            if combined_holder[0]:
                yield AgentEvent(
                    agent=AgentName.explanation,
                    event_type=AgentEventType.complete,
                    message="Full analysis complete",
                    data=combined_holder[0],
                    timestamp=0,
                )
        except (asyncio.CancelledError, GeneratorExit):
            task.cancel()
            logger.info("Client disconnected during simulation, task cancelled")
            raise

    async def run_overlap_analysis(
        self,
        degree1: dict,
        degree2: dict,
        pdf_path_1: str | None = None,
        pdf_path_2: str | None = None,
    ) -> AsyncGenerator[AgentEvent | None, None]:
        """Run overlap analysis between two degrees. Uses multi-document PDF comparison when both PDFs are available."""
        queue: asyncio.Queue = asyncio.Queue()
        result_holder: list[dict] = [{}]

        async def emit(event: AgentEvent):
            await queue.put(event)

        async def _run():
            try:
                overlap_input = {"degree1": degree1, "degree2": degree2}
                if pdf_path_1:
                    overlap_input["pdf_path_1"] = pdf_path_1
                if pdf_path_2:
                    overlap_input["pdf_path_2"] = pdf_path_2
                result_holder[0] = await self.overlap.run(overlap_input, emit)
            except Exception as e:
                logger.error(f"Overlap analysis error: {e}")
                await queue.put(AgentEvent(
                    agent=AgentName.overlap,
                    event_type=AgentEventType.error,
                    message=str(e),
                    timestamp=0,
                ))
            finally:
                await queue.put(_SENTINEL)

        task = asyncio.create_task(_run())
        try:
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=_HEARTBEAT_INTERVAL)
                except asyncio.TimeoutError:
                    yield None  # heartbeat marker
                    continue
                if item is _SENTINEL:
                    break
                yield item

            if "overlap" in result_holder[0]:
                yield AgentEvent(
                    agent=AgentName.overlap,
                    event_type=AgentEventType.complete,
                    message="Overlap analysis complete",
                    data=result_holder[0],
                    timestamp=0,
                )
        except (asyncio.CancelledError, GeneratorExit):
            task.cancel()
            logger.info("Client disconnected during overlap analysis, task cancelled")
            raise


    async def run_policy_check(
        self,
        degree_data: dict,
        course_nodes: list[dict],
        completed_courses: list[str],
        current_semester: int,
    ) -> AsyncGenerator[AgentEvent | None, None]:
        """Run policy agent with real-time SSE events."""
        queue: asyncio.Queue = asyncio.Queue()
        result_holder: list[dict] = [{}]

        async def emit(event: AgentEvent):
            await queue.put(event)

        async def _run():
            try:
                result_holder[0] = await self.policy.run(
                    {
                        "degree": degree_data,
                        "course_nodes": course_nodes,
                        "completed_courses": completed_courses,
                        "current_semester": current_semester,
                    },
                    emit,
                )
            except Exception as e:
                logger.error(f"Policy agent error: {e}")
                await queue.put(AgentEvent(
                    agent=AgentName.policy,
                    event_type=AgentEventType.error,
                    message=str(e),
                    timestamp=0,
                ))
            finally:
                await queue.put(_SENTINEL)

        task = asyncio.create_task(_run())
        try:
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=_HEARTBEAT_INTERVAL)
                except asyncio.TimeoutError:
                    yield None
                    continue
                if item is _SENTINEL:
                    break
                yield item

            if result_holder[0]:
                yield AgentEvent(
                    agent=AgentName.policy,
                    event_type=AgentEventType.complete,
                    message=result_holder[0].get("summary", "Policy check complete"),
                    data=result_holder[0],
                    timestamp=0,
                )
        except (asyncio.CancelledError, GeneratorExit):
            task.cancel()
            logger.info("Client disconnected during policy check, task cancelled")
            raise


    async def run_debate(
        self,
        degree_data: dict,
        completed_courses: list[str],
        current_semester: int,
        remaining_courses: str,
    ) -> AsyncGenerator[AgentEvent | None, None]:
        """Run multi-turn debate: Fast Track proposes first, then Safe Path rebuts.

        This is a genuine multi-turn agent interaction — the Safe Path advisor
        receives the Fast Track proposal and writes a specific rebuttal referencing
        risks in the aggressive plan.
        """
        queue: asyncio.Queue = asyncio.Queue()
        results: dict = {}

        async def emit(event: AgentEvent):
            await queue.put(event)

        input_data = {
            "degree_name": degree_data.get("degree_name", "Unknown"),
            "total_credits": degree_data.get("total_credits_required", 120),
            "completed_courses": ", ".join(completed_courses) or "None",
            "current_semester": current_semester,
            "remaining_courses": remaining_courses,
        }

        async def _run():
            try:
                # Phase 1: Fast Track proposes first
                results["fast"] = await self.fast_track.run(input_data, emit)

                # Phase 2: Safe Path rebuts with Fast Track's proposal as context
                await emit(AgentEvent(
                    agent=AgentName.debate_safe,
                    event_type=AgentEventType.thinking,
                    message="Analyzing Fast Track proposal for risks and overloads...",
                    step=0, timestamp=0,
                ))
                safe_input = dict(input_data)
                fast_proposal = results.get("fast", {}).get("proposal", "")
                if fast_proposal:
                    safe_input["fast_track_proposal"] = fast_proposal
                results["safe"] = await self.safe_path.run(safe_input, emit)

                # Phase 3: Jury synthesizes both proposals
                jury_input = {
                    "fast_proposal": results.get("fast", {}).get("proposal", ""),
                    "safe_proposal": results.get("safe", {}).get("proposal", ""),
                    "degree_name": input_data.get("degree_name", "Unknown"),
                    "completed_courses": input_data.get("completed_courses", "None"),
                    "current_semester": input_data.get("current_semester", 1),
                }
                results["jury"] = await self.jury.run(jury_input, emit)
            except Exception as e:
                logger.error(f"Debate pipeline error: {e}")
                await queue.put(AgentEvent(
                    agent=AgentName.debate_fast,
                    event_type=AgentEventType.error,
                    message=str(e), timestamp=0,
                ))
            finally:
                await queue.put(_SENTINEL)

        task = asyncio.create_task(_run())
        try:
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=_HEARTBEAT_INTERVAL)
                except asyncio.TimeoutError:
                    yield None
                    continue
                if item is _SENTINEL:
                    break
                yield item

            # Yield combined debate result
            yield AgentEvent(
                agent=AgentName.debate_fast,
                event_type=AgentEventType.complete,
                message="Debate complete",
                data={
                    "fast": results.get("fast", {}).get("proposal", ""),
                    "safe": results.get("safe", {}).get("proposal", ""),
                    "jury": results.get("jury", {}).get("verdict", ""),
                },
                timestamp=0,
            )
        except (asyncio.CancelledError, GeneratorExit):
            task.cancel()
            logger.info("Client disconnected during debate, task cancelled")
            raise


orchestrator = Orchestrator()
