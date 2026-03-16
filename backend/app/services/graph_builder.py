"""Build a DAG from courses and compute semester assignments via topological sort."""

from collections import defaultdict, deque
from app.models.schemas import Course, DegreeRequirement


def build_course_graph(degree: DegreeRequirement) -> dict:
    """Build adjacency list and in-degree map from course prerequisites."""
    course_map = {c.code: c for c in degree.courses}
    adj: dict[str, list[str]] = defaultdict(list)  # prereq -> dependents
    in_degree: dict[str, int] = {c.code: 0 for c in degree.courses}

    for course in degree.courses:
        for prereq in course.prerequisites:
            if prereq in course_map:
                adj[prereq].append(course.code)
                in_degree[course.code] += 1

    return {"course_map": course_map, "adj": adj, "in_degree": in_degree}


def assign_semesters(
    degree: DegreeRequirement,
    completed_courses: list[str] | None = None,
    current_semester: int = 1,
) -> list[dict]:
    """Assign courses to semesters using topological sort with credit constraints."""
    completed = set(completed_courses or [])
    graph = build_course_graph(degree)
    course_map: dict[str, Course] = graph["course_map"]
    adj: dict[str, list[str]] = graph["adj"]
    in_degree: dict[str, int] = dict(graph["in_degree"])
    max_credits = degree.max_credits_per_semester

    # Remove completed courses from the graph
    for code in completed:
        if code in in_degree:
            del in_degree[code]
            for dep in adj.get(code, []):
                if dep in in_degree:
                    in_degree[dep] -= 1

    # BFS-based topological sort with semester bucketing
    queue: deque[str] = deque()
    for code, deg in in_degree.items():
        if deg == 0 and code not in completed:
            queue.append(code)

    semester = current_semester
    result: list[dict] = []

    # Add completed courses at semester 0
    for code in completed:
        if code in course_map:
            c = course_map[code]
            result.append({
                "code": c.code,
                "name": c.name,
                "credits": c.credits,
                "prerequisites": c.prerequisites,
                "corequisites": c.corequisites,
                "category": c.category,
                "typical_semester": c.typical_semester,
                "is_required": c.is_required,
                "available_semesters": c.available_semesters,
                "status": "completed",
                "semester": 0,
                "dependents_count": len(adj.get(c.code, [])),
            })

    while queue:
        # Collect all courses available this semester
        available = list(queue)
        queue.clear()

        # Sort by: required first, then by typical_semester, then by dependents count
        available.sort(key=lambda c: (
            not course_map[c].is_required,
            course_map[c].typical_semester or 99,
            -len(adj.get(c, [])),
        ))

        credits_this_sem = 0
        deferred: list[str] = []

        for code in available:
            c = course_map[code]
            if credits_this_sem + c.credits <= max_credits:
                credits_this_sem += c.credits
                # Determine status
                dependents = len(adj.get(code, []))
                status = "bottleneck" if dependents >= 3 else (
                    "elective" if not c.is_required else "scheduled"
                )
                result.append({
                    "code": c.code,
                    "name": c.name,
                    "credits": c.credits,
                    "prerequisites": c.prerequisites,
                    "corequisites": c.corequisites,
                    "category": c.category,
                    "typical_semester": c.typical_semester,
                    "is_required": c.is_required,
                    "available_semesters": c.available_semesters,
                    "status": status,
                    "semester": semester,
                    "dependents_count": dependents,
                })
                # Unlock dependents
                for dep in adj.get(code, []):
                    if dep in in_degree:
                        in_degree[dep] -= 1
                        if in_degree[dep] == 0:
                            deferred.append(dep)
            else:
                deferred.append(code)

        queue.extend(deferred)
        semester += 1

    # Mark courses with unmet prereqs as locked
    assigned_codes = {r["code"] for r in result}
    for course in degree.courses:
        if course.code not in assigned_codes and course.code not in completed:
            result.append({
                "code": course.code,
                "name": course.name,
                "credits": course.credits,
                "prerequisites": course.prerequisites,
                "corequisites": course.corequisites,
                "category": course.category,
                "typical_semester": course.typical_semester,
                "is_required": course.is_required,
                "available_semesters": course.available_semesters,
                "status": "locked",
                "semester": semester,
                "dependents_count": 0,
            })

    return result
