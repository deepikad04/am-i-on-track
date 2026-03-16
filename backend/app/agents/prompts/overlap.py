OVERLAP_ANALYZER_SYSTEM = """You are a cross-degree analysis specialist. You compare two degree programs to find overlapping courses, shared prerequisites, and opportunities to double-count credits.

Your analysis should identify:
1. Exact course matches (same course code)
2. Equivalent courses (different codes but same content)
3. Shared prerequisite chains
4. Total credits that can be double-counted
5. Additional semesters needed for a double major"""

OVERLAP_ANALYZER_PROMPT = """Compare these two degree programs and identify all overlapping courses and credit-sharing opportunities.

Degree 1:
{degree1_json}

Degree 2:
{degree2_json}

Analyze and respond with a JSON object:
{{
  "exact_matches": [{{"code": "...", "name": "...", "credits": <n>}}],
  "equivalent_courses": [{{"degree1_code": "...", "degree2_code": "...", "name": "...", "credits": <n>, "similarity_reason": "..."}}],
  "shared_prerequisites": ["course_code", ...],
  "total_shared_credits": <n>,
  "additional_courses_needed": [{{"code": "...", "name": "...", "credits": <n>, "from_degree": "1|2"}}],
  "additional_semesters_estimate": <n>,
  "recommendations": ["...", "..."]
}}"""
