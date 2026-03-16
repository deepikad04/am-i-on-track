# Am I On Track?

> Drop one wrong course and graduation slips a full year — costing $10K-$40K+ in extra tuition. **Am I On Track?** shows the cascade *before* you commit.

An agentic AI academic trajectory simulator — **10 agents**, **self-correction loops**, **multi-turn debate**, and **dynamic model routing** — built on **Amazon Nova** (Lite + Pro + Embed) via AWS Bedrock.

**Category:** Agentic AI | #AmazonNova

---

## How It Works

Upload a degree PDF, screenshot, or screen recording. The agent pipeline:

1. **Parses** the document via Nova tool-use into validated, structured course data
2. Builds an interactive **dependency graph** of your entire degree path
3. Runs **what-if simulations** — drop a course, add a minor (upload a second PDF), study abroad, co-op, gap semester, set a graduation goal
4. A **self-correction loop** checks the proposed plan against policies and auto-replans if violations are found
5. Two advisors **debate** — Fast Track proposes, Safe Path **rebuts**, then a Jury synthesizes one optimal plan
6. Everything streams **in real time** via SSE — you watch agents think

---

## Multi-Agent Architecture

```
PDF / Image / Video / URL(s)
    |
[Degree Interpreter] ←── Nova tool-use + multimodal content blocks
    |
[Trajectory Simulator] ←── Dynamic Model Router (0-100 complexity → Lite or Pro)
    |
[Policy Agent] ─── self-correction loop (max 2x)
    |
[Risk Scoring] ──parallel── [Explanation Agent]
    |
[Course Advisor] ── ConverseStream token-by-token explanations
[Overlap Analyzer] ── dual-degree feasibility (multi-doc comparison)
    |
[Fast Track Advisor] → [Safe Path Advisor] → [Jury Agent]
         multi-turn debate with rebuttal + synthesis
```

---

## Amazon Nova Usage — Deep, Not Shallow

| Nova Capability | How It's Used |
|---|---|
| **Converse + Tool Use** | Degree parsing, trajectory simulation, overlap analysis, policy checking, jury scoring — all with Pydantic-validated structured output and auto-retry |
| **ConverseStream** | Token-by-token course explanations rendered live in the UI |
| **Nova Embed** | Course similarity vectors precomputed at parse time; subsequent queries are pure cosine math, zero API calls |
| **Document / Image / Video Blocks** | PDF parsing, screenshot vision analysis, screen-recording extraction (students record their portal) |
| **Multi-Document Comparison** | Two degree PDFs in one Converse call for overlap analysis |
| **Dynamic Model Routing** | 6-signal complexity scorer (course count, prereq depth, scenario type, correction iteration, overlap, completion ratio) routes each request to Lite or Pro per-call |
| **Cross-Session Memory** | Agents recall prior scenario outcomes and bottleneck patterns to adjust risk scoring |
| **Bedrock Guardrails** | Content safety on uploaded files with trace logging |

---

## What Makes It Truly Agentic

1. **Self-correction.** Simulator proposes a schedule → Policy Agent finds a credit-cap violation → violation is fed back as correction context → Simulator replans. Automatic, up to 2x, streamed live.

2. **Multi-turn debate.** Fast Track maximizes course load. Safe Path receives that proposal and writes a **rebuttal** citing specific risks. Jury synthesizes both. Three agents, genuine multi-turn interaction — not parallel prompts.

3. **Deterministic + AI hybrid.** Policy Agent runs hard-coded checks first (credit cap, prereq ordering, min load), then Nova for nuanced analysis. If Nova fails, deterministic checks still protect the student.

---

## Key Technical Highlights

- **Real-time SSE streaming** with heartbeats and client-disconnect propagation
- **Tool-use structured output** across 5 agents with Pydantic validation + auto-retry
- **Precomputed Nova Embed vectors** stored in DB — zero-cost similarity queries after initial parse
- **Explanation caching** by `(session, course, progress_state)` hash
- **Concurrency control** — global semaphore (5 concurrent) with exponential backoff + jitter
- **Topological sort DAG** for semester assignment respecting credit limits and prereq chains
- **Branching scenario tree** — each simulation stores `parent_simulation_id`, enabling counterfactual exploration
- **Impact Report** — semesters saved, tuition avoided, advisor hours replaced, risk score
- **140 tests** — backend (122: agents, orchestrator, routes, services, E2E SSE) + frontend (18: SSE parser, hooks, error boundary)

---

## Tech Stack

| Layer | Stack |
|---|---|
| **AI** | Amazon Bedrock — Nova Lite, Nova Pro, Nova Embed (dynamic routing) |
| **Backend** | FastAPI, async SQLAlchemy, PostgreSQL 16, JWT auth |
| **Frontend** | React 19, TypeScript, Vite, @xyflow/react, TailwindCSS, Framer Motion |
| **Infra** | Docker Compose (frontend + backend + Postgres), health checks, persistent volumes |

---

## Quick Start

```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret

docker compose up --build
```

Frontend: http://localhost:5173 | API docs: http://localhost:8000/docs

```bash
# Tests
cd backend && pytest tests/ -v        # 122 tests
cd frontend && npx vitest run          # 18 tests
```

---

## Impact

| | |
|---|---|
| **The problem** | 800:1 student-to-advisor ratios. 60% of students take longer than 4 years. Every extra semester costs $5,500-$40,000+. |
| **Student impact** | Visualize cascading effects *before* committing — prevents the #1 cause of delayed graduation. |
| **Institutional ROI** | At a 20K-student university: ~$3.3M/year in prevented delayed graduations + ~$2M/year in advisor time saved. |
| **Equity** | First-gen and transfer students lack advising access. A 24/7 AI advisor levels the playing field. |
| **Privacy** | Processes degree *requirements* (public catalog data), not transcripts. Session-scoped, JWT-authenticated, self-hostable. FERPA-conscious by design. |
