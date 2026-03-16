# Am I On Track?

> Every semester, thousands of students drop a single course — and don't realize until too late that it pushes graduation back an entire year, costing $10K-$40K+ in extra tuition. **Am I On Track?** lets them see that cascade *before* they commit.

An agentic AI-powered academic trajectory simulator built with **Amazon Nova Lite**, **Amazon Nova Pro**, and **Amazon Nova Embed** on AWS Bedrock — featuring dynamic complexity-based model routing, multimodal input (PDF + image + video), Nova Canvas roadmap generation, multi-document comparison, and cross-session agent memory.

**Category:** Agentic AI | #AmazonNova

---

## The Problem

Academic advising at most universities operates at **800:1 student-to-advisor ratios**. Students make scheduling decisions blind — there is no way to preview the cascading effects of dropping a course, taking a semester off, or switching majors. The result: 60% of students take longer than four years to graduate, and every extra semester costs $5,500-$40,000+ in tuition alone.

## The Solution

Upload a degree requirements PDF, image (screenshot/photo), or screen recording (scroll through your university portal). A multi-agent pipeline powered by Amazon Nova:

1. **Parses** the document into structured course data using Nova **tool-use** (not free-form prompts — structured, validated JSON)
2. Builds an interactive **dependency graph** showing your entire degree path
3. Runs **what-if simulations** — drop a course, block a semester, add a second major/minor (with PDF upload + integrated overlap analysis), study abroad, co-op, gap semester, set a graduation goal
4. A **self-correction loop** validates the proposed schedule against university policies and automatically re-plans if violations are found
5. Two opposing advisors **debate** the optimal path — Fast Track runs first, then Safe Path **rebuts** with a counter-proposal referencing the aggressive plan
6. Everything streams in **real time** via SSE — you see agent thinking steps as they happen

## Why Amazon Nova?

Nova isn't just "the LLM" — it's the backbone of every agent interaction:

- **Nova Tool Use** makes this project possible. Free-form JSON from an LLM is unreliable for degree parsing (missing fields, wrong types). Nova's native tool-use schemas guarantee structured output that passes Pydantic validation — with automatic retry when validation fails.
- **Nova ConverseStream** enables token-by-token course explanations that render incrementally in the UI, not a spinner followed by a wall of text.
- **Nova Embed** precomputes course similarity vectors at parse time so subsequent "related courses" queries use pure math with zero API calls.
- **Nova Converse** powers 10 distinct agent personas (simulator, policy checker, risk scorer, two debate advisors, jury, overlap analyzer, explanation generator, course advisor, degree interpreter) — each with role-specific system prompts and temperature tuning.
- **Dynamic Model Routing** analyzes 6 complexity signals (course count, prerequisite depth, scenario type, correction iteration, dual-degree overlap, completion ratio) to score each request 0-100 and route to Nova Lite (fast) or Nova Pro (deep reasoning) per-call — not a static per-agent assignment.
- **Cross-Session Agent Memory** stores scenario outcomes and bottleneck patterns across sessions; agents actively recall learned patterns to adjust risk scoring and simulation context.
- **Multimodal Input** — Nova's document, image, and video content blocks enable PDF parsing, vision-based screenshot analysis, and screen-recording-based degree extraction (students record their university portal, Nova extracts course data from video frames).
- **Nova Canvas** generates shareable visual semester roadmap infographics — especially useful for double major/minor plans where the merged timeline is complex. Students download the image and bring it to advisor meetings.
- **Multi-Document Comparison** — two PDFs in a single Converse call for double major/minor overlap analysis. Nova compares both degree requirement documents side-by-side to find shared courses and optimal course-sharing strategies.

| Nova Capability | Where It's Used |
|---|---|
| **Converse API + Tool Use** | Degree parsing (structured extraction with retry), trajectory simulation, overlap analysis, policy checking, jury convergence scoring |
| **Converse API** | Policy compliance reasoning, agent debate (multi-turn rebuttal + jury synthesis), plain-English explanations |
| **ConverseStream** | Real-time token streaming for course explanations |
| **Nova Embed** | Course similarity search via precomputed cosine similarity vectors |
| **Document Content Block** | PDF degree audit parsing via native document processing |
| **Image Content Block** | Vision-based parsing of degree audit screenshots and photos (PNG, JPEG, WebP) |
| **Video Content Block** | Screen recording parsing — students record scrolling through their university portal degree audit page (MP4, WebM) |
| **Nova Canvas (Text-to-Image)** | Generate visual semester roadmap infographics students can download and share with advisors |
| **Multi-Document Comparison** | Two degree PDFs in a single Converse call for overlap analysis in double-major/minor scenarios |
| **Dynamic Model Routing** | Complexity-scored (0-100) per-request routing between Nova Lite and Nova Pro |
| **Bedrock Guardrails** | Content safety on user-uploaded files (PDF, images, video) with trace logging for audit |

### Multi-Agent Architecture (10 Agents)

```
PDF / Image / Video Upload  ──or──  URL(s)
    |                                  |
    v                                  v
[Degree Interpreter Agent] ←── Nova tool-use (document / image / video content blocks)
    |
    v                          ┌─────────────────────────────┐
[Trajectory Simulator Agent] ←─┤ Dynamic Model Router        │
    |                          │ 6-signal complexity scorer   │
    v                          │ score < 30 → Nova Lite       │
[Policy Agent] ─── self-      │ score ≥ 30 → Nova Pro        │
    |          correction     └─────────────────────────────┘
    |          loop (max 2x)
    v
[Risk Scoring Agent] -- deterministic 0-100 + agent memory feedback
    |                   (runs in parallel with ↓)
[Explanation Agent]  -- Nova generates student-friendly summary
    |
[Course Advisor Agent] -- contextual course explanations (ConverseStream)
[Overlap Analyzer Agent] -- double major feasibility (Nova tool-use)
[Fast Track Advisor] ─┐
                      ├── Agent Debate (sequential rebuttal + jury)
[Safe Path Advisor]  ─┘
         |
         v
[Jury Agent] ─── synthesizes both proposals into one optimal plan (Nova Pro)
```

All agents are orchestrated via an async supervisor pattern with real-time SSE event streaming, dynamic Lite/Pro model routing, cross-session memory recall, and parallel execution where possible.

## Key Technical Features

- **Real-time SSE streaming** — agents push events to an `asyncio.Queue`; the orchestrator yields them immediately (not batched) with `: heartbeat` SSE comments every 15 s and `asyncio.CancelledError` propagation on client disconnect
- **Tool-use for structured output** — the degree interpreter and trajectory simulator use Bedrock tool-use schemas instead of free-form JSON, with Pydantic validation and automatic retry on failure
- **Precomputed embeddings** — Nova Embed vectors are computed once at parse time and stored in the DB; subsequent similarity queries use pure cosine math with no additional API calls (falls back to on-the-fly Bedrock embedding if precomputed vectors are missing)
- **Explanation caching** — course explanations are cached by `(session, course, progress_state)` hash to eliminate redundant Bedrock calls
- **Concurrency control** — a global semaphore (5 concurrent) prevents thundering-herd throttles; retries use exponential backoff + jitter
- **Observability** — every Bedrock call logs model ID, latency, request ID, and token usage
- **Server-side scenario validation** — parameters are validated per scenario type before reaching Nova
- **Topological sort DAG** — semester assignment uses BFS-based topological sort respecting credit limits, prerequisite chains, and course availability
- **Impact Report** — quantified outcomes panel showing semesters saved, tuition avoided, advisor hours replaced, risk level, and degree completion progress
- **Self-correction loop** — after the trajectory simulator proposes a schedule, the Policy Agent validates it; if error-severity violations are found (credit cap, prereq ordering), the violations are fed back to the simulator as correction context and the simulation re-runs (up to 2 correction iterations) — a genuine agentic feedback loop
- **Policy Agent (hybrid)** — Phase 1: deterministic checks (credit cap, prereq ordering, min load, total credits); Phase 2: Nova reasoning for nuanced policy analysis, deduped and streamed via SSE
- **Agent Debate (multi-turn) + Jury Synthesis** — Fast Track Advisor proposes first; Safe Path Advisor writes a **rebuttal** referencing specific risks; then a **Jury Agent** synthesizes both into one optimal plan — a 3-agent multi-turn interaction
- **Structured outputs everywhere** — Degree Interpreter, Trajectory Simulator, Overlap Analyzer, and Policy Agent all use Nova **tool-use schemas** for validated structured output (no string-split JSON parsing)
- **Per-user rate limiting + request tracing** — every request gets an `X-Request-ID` header with full request logging; per-user concurrency is capped at 5 via `asyncio.Semaphore` with automatic cleanup
- **Scenario Tree visualization** — interactive tree view showing all explored futures branching from the current plan, with pinning (up to 4) for side-by-side comparison, sortable by risk/delay/time
- **Institution Dashboard** — cohort-level analytics endpoint showing aggregate risk distribution, graduation trends, bottleneck courses, and retention impact
- **Course explanation token streaming** — uses Bedrock `ConverseStream` API to emit tokens as `type: "chunk"` SSE events; the frontend renders text incrementally as it arrives
- **Advising Summary Export** — one-click plain-text export of the full semester-by-semester action plan for advisor review
- **Scenario History** — compare past simulation results side-by-side to evaluate tradeoffs between different academic decisions
- **Overlap Analysis UI** — cross-degree comparison to find shared courses and evaluate double-major feasibility using Nova
- **Error Boundary** — React Error Boundary catches component crashes with a recovery UI instead of a blank screen
- **Bedrock Guardrails** — content safety guardrails applied to user-uploaded file processing (PDF, images, video) via Bedrock's native guardrail configuration, with trace logging for audit
- **Multi-tenant architecture** — `institution_id` on users and sessions enables tenant-scoped data isolation; dashboard endpoint returns institution-specific analytics
- **Debate convergence scoring** — Jury Agent uses Nova tool-use to produce structured verdicts with agreement scores (0-100), key agreements/disagreements, and convergence paths
- **Branching scenario tree** — simulations store `parent_simulation_id` to form a real tree structure, enabling counterfactual exploration where each what-if branches from a previous result
- **Accessibility (a11y)** — ARIA labels, roles, keyboard navigation, `aria-live` regions for agent status updates, and `aria-busy` indicators on async operations across all interactive components
- **Async I/O throughout** — file uploads and PDF reads use `aiofiles` to avoid blocking the event loop

## Tech Stack

### Backend
- **Framework:** FastAPI + Uvicorn (async)
- **AI:** Amazon Bedrock (Nova Lite + Nova Pro + Nova Embed + Nova Canvas) via boto3 — dynamic complexity-based routing, multimodal (document + image + video), text-to-image generation, multi-document comparison
- **Database:** PostgreSQL 16 + async SQLAlchemy + asyncpg
- **Auth:** JWT (PyJWT + bcrypt)
- **PDF:** PyPDF2

### Frontend
- **Framework:** React 19 + TypeScript + Vite
- **Visualization:** @xyflow/react + dagre (graph layout)
- **Styling:** TailwindCSS + Framer Motion
- **HTTP:** Axios + native fetch for SSE streams

### Infrastructure
- Docker Compose (frontend + backend + PostgreSQL)
- Persistent volumes for database and uploads
- Health checks with service dependency ordering

## Getting Started

### Prerequisites
- Docker & Docker Compose
- AWS credentials with Bedrock access (Nova Lite + Nova Pro + Nova Embed enabled in us-east-1)

### Run

```bash
# Set your AWS credentials
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret

# Start both services
docker compose up --build

# Or run locally without AWS (deterministic demo mode — no Bedrock calls)
DEMO_MODE=true uvicorn app.main:app --reload
```

Frontend: http://localhost:5173
Backend API: http://localhost:8000/docs

### Run Tests

```bash
# Backend: 122 unit + integration + E2E tests (agents, orchestrator, routes, services, SSE stress)
cd backend
pip install -r requirements.txt
pytest tests/ -v

# Frontend: 18 tests (SSE parser, hook state, error boundary, API services)
cd frontend
npm install
npx vitest run
```

## Project Structure

```
am-i-on-track/
  backend/
    app/
      agents/           # 10 AI agents + orchestrator (Policy, Debate, Risk, Jury, etc.)
        prompts/        # Agent system prompts
      api/routes/       # FastAPI endpoints (upload, degree, simulation, auth)
      database/         # SQLAlchemy models + seed data
      models/           # Pydantic schemas + tool-use definitions
      services/         # Bedrock client, PDF processor, graph builder, auth
    tests/              # 122 tests (agents, orchestrator, routes, services, graph, schemas, similarity, policy, risk, debate, model router, E2E SSE stress)
  frontend/
    src/
      components/       # React components (degree-map, simulator, agents, auth, landing)
      hooks/            # Custom hooks (useAgentStream, useDegreeData, useSimulation)
      services/         # API client + SSE stream helpers
      contexts/         # Auth context
      types/            # TypeScript interfaces
  docker-compose.yml
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/upload` | Upload degree file — PDF, image (PNG/JPEG/WebP), or video screen recording (MP4/WebM), 10MB limit |
| POST | `/api/upload/url` | Upload degree requirements from 1-5 web page URLs |
| GET | `/api/upload/{id}/parse` | Stream parsing events via SSE |
| GET | `/api/upload/{id}/parse-url` | Stream URL-based parsing events via SSE |
| GET | `/api/degree/{id}` | Get parsed degree + course nodes |
| POST | `/api/degree/{id}/progress` | Update completed courses |
| POST | `/api/explain/course` | Stream course explanation via SSE (cached) |
| POST | `/api/degree/similar-courses` | Find related courses (Nova Embed) |
| POST | `/api/degree/overlap` | Stream cross-degree overlap analysis via SSE |
| POST | `/api/simulate` | Run what-if scenario via SSE |
| GET | `/api/simulate/{id}/result` | Fetch cached simulation result |
| GET | `/api/simulate/{id}/history` | List all simulations for scenario comparison |
| POST | `/api/simulate/debate` | Agent Debate: Fast Track → Safe Path rebuttal → Jury synthesis via SSE |
| GET | `/api/degree/{id}/impact` | Impact report (semesters saved, tuition, risk) |
| GET | `/api/degree/{id}/policy-check` | Policy Agent: validate plan against university rules (SSE) |
| POST | `/api/degree/{id}/roadmap-image` | Generate visual semester roadmap infographic via Nova Canvas (returns PNG) |
| GET | `/api/degree/{id}/export-summary` | Export advising summary as plain text |
| GET | `/api/dashboard/cohort` | Cohort analytics — real aggregation from simulation data (falls back to seed data on cold start) |
| GET | `/api/agent-memory/insights` | Cross-session learned patterns: scenario outcomes + known bottleneck courses |
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Login (JWT) |
| GET | `/api/health` | Health check + Bedrock connectivity |

## What Makes It Truly Agentic

Most "AI apps" send a prompt and show the response. **Am I On Track?** has agents that *reason, validate, and self-correct*:

1. **The agent pivots when it hits an obstacle.** The Trajectory Simulator proposes a schedule. The Policy Agent finds a credit-cap violation. Instead of showing the broken plan, the system feeds the violation back to the simulator with correction instructions — and the simulator re-plans. This happens automatically, up to 2x, until the schedule is policy-compliant. The user sees the entire loop in real-time via SSE.

2. **Two agents disagree — on purpose.** The Fast Track Advisor maximizes course load and targets earliest graduation. The Safe Path Advisor then receives the Fast Track proposal and writes a **rebuttal** — referencing specific risks in the aggressive plan and proposing a safer alternative. This is genuine multi-turn agent interaction: the second agent's output is informed by the first agent's reasoning. The student sees both proposals side-by-side to make their own informed decision.

3. **Deterministic rules + AI reasoning work together.** The Policy Agent doesn't just ask Nova "is this plan valid?" — it runs hard-coded checks first (credit cap, prereq ordering, min load, total credits), then asks Nova for nuanced analysis, and deduplicates the results. If Nova fails, the deterministic checks still protect the student.

## Enterprise & Community Impact

**Am I On Track?** delivers measurable value at both the individual student and institutional level:

- **Student impact:** Every extra semester costs $5,500-$40,000+ in tuition. By visualizing cascading effects *before* students drop courses or change majors, this tool prevents the #1 cause of delayed graduation — uninformed scheduling decisions.
- **Institutional impact:** At 800:1 student-to-advisor ratios, advisors can't run what-if analyses for every student. This tool automates the most time-consuming advising task (trajectory planning), freeing advisors to focus on mentorship and at-risk interventions. The Impact Report quantifies: semesters saved, tuition avoided, and advisor hours replaced.
- **Equity impact:** First-generation college students and transfer students disproportionately lack advising access. A self-service AI advisor available 24/7 levels the playing field — no appointment needed, no waitlist.
- **Retention impact:** Universities lose $16,000+ per dropout. Early identification of at-risk trajectories (via the Policy Agent's automated compliance checks and the Risk Scoring Agent's 0-100 quantified risk metric) enables proactive intervention before students fall behind.

### ROI: Back-of-Napkin Math

| Metric | Conservative Estimate |
|---|---|
| Students who delay graduation by dropping one wrong course | ~15% of undergrads |
| Extra cost per delayed student (1 semester) | $5,500 - $22,000 |
| If this tool prevents even 10% of those delays at a 20,000-student university | 300 students x $11,000 avg = **$3.3M saved/year** |
| Advisor time saved per student (manual what-if analysis) | ~2 hours |
| At 20,000 students x $50/hr advisor cost | **$2M/year in advising labor** |
| Total institutional ROI | **$5.3M/year** for a single mid-size university |

These are conservative estimates — the real number is higher when accounting for student loan interest on delayed graduation, lost early-career earnings, and institutional reputation effects on enrollment yield.

### Data Privacy & FERPA Compliance

Academic records are protected under FERPA (Family Educational Rights and Privacy Act). This application is designed with privacy in mind:

- **No student records stored** — the app processes degree *requirements* (public catalog data), not student transcripts or grades
- **Session-scoped data** — uploaded PDFs and parsed data are tied to ephemeral sessions, not permanent student profiles
- **JWT authentication** — all API endpoints require authentication; degree data is scoped to the authenticated user
- **No third-party data sharing** — Bedrock API calls process degree requirements only; no PII is sent to external services
- **Self-hosted option** — Docker Compose deployment means institutions can run the entire stack on-premises behind their firewall

## Roadmap

How we'd scale this beyond the hackathon:

- **Multi-university support** — university-specific policy rule packs (credit caps, GPA requirements, co-op policies) loaded from config instead of hardcoded
- **Advisor dashboard** — let academic advisors see aggregate student trajectories, identify at-risk students, and approve/override AI suggestions
- **Transfer credit intelligence** — use Nova Embed to match courses across universities for transfer students (community college → 4-year)
- **Real-time catalog sync** — integrate with university registrar APIs (Banner, PeopleSoft) for live course availability and section data
- **Collaborative planning** — students share scenarios with advisors or peers for review before committing
- **Mobile companion** — push notifications when registration opens for bottleneck courses the system identified

