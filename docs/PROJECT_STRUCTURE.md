# SOC Copilot Demo - Project Structure

**Last Updated:** February 20, 2026
**Version:** v2.5 (Complete and Tagged)
**Total Files:** 27 code files (~9,450 lines)
**Architecture:** Two-loop compounding intelligence — Situation Analyzer (Loop 1) + AgentEvolver (Loop 2) — with interactivity layer (ROI Calculator, Outcome Feedback, Policy Conflict)
**ACCP Progress:** 10/18 capabilities implemented

---

## Table of Contents

- [Directory Tree](#directory-tree)
- [Version History (Waves)](#version-history-waves)
- [Backend Files](#backend-files)
  - [Main Application](#main-application)
  - [Routers](#routers)
  - [Services](#services)
  - [Database Clients](#database-clients)
  - [Models](#models)
  - [Utilities](#utilities)
- [Frontend Files](#frontend-files)
  - [Core Application](#core-application)
  - [Tab Components](#tab-components)
  - [Shared Components](#shared-components)
  - [API Client and Types](#api-client-and-types)
- [Dependency Diagram](#dependency-diagram)
- [Tab Support Matrix](#tab-support-matrix)
- [ACCP Capability Map](#accp-capability-map)

---

## Directory Tree

```
gen-ai-roi-demo-v2/
│
├── .gitignore
├── CLAUDE.md                             # Project instructions (always read first)
├── PROJECT_STRUCTURE.md                  # THIS FILE
├── README.md
│
├── backend/
│   ├── requirements.txt                  # Python dependencies
│   ├── seed_neo4j.py                     # Neo4j seed data script (standalone)
│   ├── test_policy_endpoints.py          # Policy endpoint smoke tests
│   └── app/
│       ├── main.py                       # FastAPI app entry point
│       ├── routers/
│       │   ├── __init__.py
│       │   ├── soc.py                    # Tab 1: SOC Analytics
│       │   ├── evolution.py              # Tab 2: Runtime Evolution ★ THE DIFFERENTIATOR
│       │   ├── triage.py                 # Tab 3: Alert Triage (v2.5: + feedback, policy endpoints)
│       │   ├── metrics.py                # Tab 4: Compounding Metrics
│       │   └── roi.py                    # ★ NEW v2.5: ROI Calculator endpoint
│       ├── services/
│       │   ├── __init__.py
│       │   ├── agent.py                  # Simple rule-based decision engine
│       │   ├── reasoning.py              # LLM narration (Gemini 1.5 Pro)
│       │   ├── situation.py              # ★ NEW v2.0: Situation Analyzer — Loop 1
│       │   ├── evolver.py                # ★ NEW v2.0: AgentEvolver — Loop 2
│       │   ├── feedback.py               # ★ NEW v2.5: Outcome Feedback service
│       │   ├── policy.py                 # ★ NEW v2.5: Policy Conflict service
│       │   └── seed_neo4j.py             # Neo4j seed data constants (service module)
│       ├── db/
│       │   ├── __init__.py
│       │   └── neo4j.py                  # Neo4j Aura async client
│       └── models/
│           ├── __init__.py
│           └── schemas.py                # Pydantic v2 models
│
└── frontend/
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts                    # Vite dev server (port 5174, proxy /api → 8001)
    ├── tailwind.config.js
    └── src/
        ├── main.tsx                      # React entry point
        ├── App.tsx                       # 4-tab navigation root
        ├── index.css                     # Global styles (dark SOC theme)
        ├── lib/
        │   └── api.ts                    # Backend API client (v2.5: + feedback, policy, ROI)
        ├── types/
        │   └── roi.ts                    # ★ NEW v2.5: ROI TypeScript types
        └── components/
            ├── OutcomeFeedback.tsx       # ★ NEW v2.5: Correct/Incorrect feedback panel
            ├── PolicyConflict.tsx        # ★ NEW v2.5: Policy conflict detection panel
            ├── ROICalculator.tsx         # ★ NEW v2.5: ROI Calculator modal
            └── tabs/
                ├── SOCAnalyticsTab.tsx        # Tab 1: SOC Analytics
                ├── RuntimeEvolutionTab.tsx    # Tab 2: Runtime Evolution ★
                ├── AlertTriageTab.tsx         # Tab 3: Alert Triage (v2.5: + feedback, policy)
                └── CompoundingTab.tsx         # Tab 4: Compounding Dashboard (v2.5: + ROI modal)
```

---

## Version History (Waves)

**Branch:** `main` (v2.5 tagged at commit e63bc85)
**Previous:** `feature/v2-enhancements` (synced with main, can be deleted)
**Base:** v1.0 (frozen on separate directory)

### Wave 1: Labels + Visual Polish ✅ (v2.0)
- **Files:** RuntimeEvolutionTab.tsx, AlertTriageTab.tsx, CompoundingTab.tsx, App.tsx
- **Features:** CONSUME/MUTATE/ACTIVATE CMA labels, eval gate sequential animation (800ms per check), counter animations in Tab 4 (3-second count-up), version bump to v2.0

### Wave 2: Blocking Demo ✅ (v2.0)
- **Files:** evolution.py, RuntimeEvolutionTab.tsx, api.ts
- **Features:** POST /api/alert/process-blocked endpoint, "Simulate Failed Gate" button in Tab 2, BLOCKED banner when eval gate fails

### Wave 3: Situation Analyzer — Backend ✅ (v2.0)
- **Files:** situation.py (NEW), evolution.py, triage.py
- **Features:** 6 situation types, classify_situation(), evaluate_options(), analyze_situation(); situation_analysis in API responses

### Wave 4: Situation Analyzer — Frontend ✅ (v2.0)
- **Files:** AlertTriageTab.tsx
- **Features:** Situation panel with type badge (color-coded), key factors list, options bar chart (Recharts), reasoning text

### Wave 5: AgentEvolver + Second Alert ✅ (v2.0)
- **Files:** evolver.py (NEW), evolution.py, RuntimeEvolutionTab.tsx, seed_neo4j.py
- **Features:** Prompt variant tracking, promotion logic (>5% improvement), AgentEvolver panel in Tab 2, ALERT-7824 (phishing — Mary Chen), PAT-PHISH-KNOWN, PhishingCampaign node

### Wave 6: Business Impact + Documentation ✅ (v2.0)
- **Sub-waves:**
  - **6A:** Decision economics — time/cost/risk per option (situation.py, AlertTriageTab.tsx)
  - **6B:** Operational impact narrative — "what changed", 5 impact cards (evolver.py, RuntimeEvolutionTab.tsx)
  - **6C:** Business impact banner — 847 hrs, $127K, 75% MTTR, 2,400 backlog (metrics.py, CompoundingTab.tsx)
  - **6D:** Two-loop hero diagram — dark slate, Loop 1 & 2 panels, TRIGGERED_EVOLUTION badge, stats row (CompoundingTab.tsx)
  - **6E:** Documentation updates (CLAUDE.md, PROJECT_STRUCTURE.md)

### Wave 7: ROI Calculator ✅ (v2.5)
- **Files:** roi.py (NEW), ROICalculator.tsx (NEW), roi.ts (NEW), CompoundingTab.tsx, api.ts
- **Features:** POST /api/roi/calculate + GET /api/roi/defaults, modal with 6 input sliders, real-time projections ($428K–$5.1M range), payback period, ROI multiple, CFO narrative

### Wave 8: Outcome Feedback ✅ (v2.5)
- **Files:** feedback.py (NEW), OutcomeFeedback.tsx (NEW), triage.py, AlertTriageTab.tsx, api.ts
- **Features:** POST /api/alert/outcome + GET /api/alert/outcome/status, correct/incorrect buttons after closed loop, asymmetric updates (+0.3 correct / -6.0 incorrect), self-correction (Tier 2 routing for 5 similar alerts), stale closure bug fixed with useRef pattern

### Wave 9: Policy Conflict Resolution ✅ (v2.5)
- **Files:** policy.py (NEW), PolicyConflict.tsx (NEW), triage.py, AlertTriageTab.tsx, api.ts
- **Features:** GET /api/alert/policy-check + GET /api/alert/policy-history, 4 demo policies, ALERT-7823 triggers travel auto-close vs high-risk escalate conflict, resolution by priority, audit trail with CON-2026-XXXX IDs

---

## Backend Files

### Main Application

#### `backend/app/main.py`

**Purpose:** FastAPI application entry point with CORS and router registration.

**Key Functions/Exports:**
- `app` — FastAPI application instance
- `root()` — Health check (GET /)
- `health()` — Health check (GET /health)
- `startup_event()` — Initialize Neo4j connection
- `shutdown_event()` — Close Neo4j connection

**Routers registered:** evolution, triage, soc, metrics, roi (v2.5)

**Tab Support:** All tabs

**Lines:** ~62

---

### Routers

#### `backend/app/routers/soc.py`

**Purpose:** Tab 1 (SOC Analytics) — natural language metric queries with governance and provenance.

**Key Functions/Exports:**
- `query_soc_metrics(request)` — POST /api/soc/query — keyword match → chart + contract + provenance + sprawl
- `list_metrics()` — GET /api/soc/metrics
- `match_metric(question)` — Internal keyword matching
- `check_for_sprawl(metric_id)` — Rule sprawl detection ($18K/month waste found)

**Key Data Structures:**
- `METRIC_REGISTRY` — 6 metrics: MTTR, auto-close rate, FP rate, escalation rate, MTTD, analyst efficiency

**Notable Features:** Mock BigQuery data (no GCP setup required), keyword-based matching

**Tab Support:** Tab 1

**Lines:** ~403

---

#### `backend/app/routers/evolution.py`

**Purpose:** Tab 2 (Runtime Evolution) — TRIGGERED_EVOLUTION. THE KEY DIFFERENTIATOR.

**Key Functions/Exports:**
- `get_deployments()` — GET /api/deployments — returns v3.1 (active, 90%) + v3.2 (canary, 10%)
- `process_alert(request)` — POST /api/alert/process — **THE MAIN FLOW** (9 steps):
  1. Get security context (47 nodes from Neo4j)
  2. Situation analysis (situation.py)
  3. Agent decision (rule-based)
  4. LLM reasoning (narration)
  5. Eval gate (4 checks)
  6. Create decision trace in Neo4j
  7. Check if evolution triggers
  8. Create TRIGGERED_EVOLUTION relationship
  9. Get prompt evolution summary (evolver.py)
- `process_alert_blocked(request)` — POST /api/alert/process-blocked — simulates eval gate failure

**Tab Support:** Tab 2 ★ THE DIFFERENTIATOR

**Lines:** ~350

---

#### `backend/app/routers/triage.py`

**Purpose:** Tab 3 (Alert Triage) — graph-based analysis, closed-loop execution, feedback, and policy.

**v2.5 Updates:** Added outcome feedback and policy conflict endpoints.

**Key Functions/Exports:**
- `get_alert_queue()` — GET /api/triage/alerts — 5 pending alerts (ALERT-7823, ALERT-7824, etc.)
- `analyze_alert(alert_id)` — POST /api/triage/analyze — graph traversal + situation analysis + recommendation
- `execute_action(request)` — POST /api/triage/execute — 4-step closed loop (EXECUTED → VERIFIED → EVIDENCE → KPI IMPACT)
- `record_outcome(request)` — POST /api/alert/outcome — correct/incorrect feedback (v2.5)
- `get_outcome_status(alert_id)` — GET /api/alert/outcome/status (v2.5)
- `check_policy(alert_id)` — GET /api/alert/policy-check — detect conflicts for alert (v2.5)
- `get_policy_history(alert_id)` — GET /api/alert/policy-history — audit trail (v2.5)

**Tab Support:** Tab 3

**Lines:** 670

---

#### `backend/app/routers/metrics.py`

**Purpose:** Tab 4 (Compounding Dashboard) — week-over-week intelligence growth and business impact.

**Key Functions/Exports:**
- `get_compounding_metrics(weeks=4)` — GET /api/metrics/compounding — headline + trend + evolution events + business_impact
- `get_evolution_events(limit=10)` — GET /api/metrics/evolution-events
- `seed_neo4j()` — POST /api/demo/seed
- `reset_all_demo_data()` — POST /api/demo/reset-all — comprehensive reset via re-seeding
- `reset_demo_data()` — POST /api/demo/reset — legacy reset to Week 1

**Key Numbers:**
- Week 1: 23 patterns, 68% auto-close
- Week 4: 127 patterns, 89% auto-close
- Business Impact: 847 hrs/month, $127K/quarter, 75% MTTR reduction, 2,400 backlog eliminated

**Tab Support:** Tab 4

**Lines:** ~350

---

#### `backend/app/routers/roi.py` ★ NEW v2.5

**Purpose:** ROI Calculator — prospect-specific savings projections.

**Key Functions/Exports:**
- `calculate_roi(request)` — POST /api/roi/calculate
  - Inputs: alerts_per_day, analysts, avg_salary, current_mttr_minutes, current_auto_close_pct, escalation_cost
  - Outputs: annual_savings breakdown, payback_period_months, roi_multiple, cfо_narrative
  - Range: $428K (small SOC) to $5.1M (large SOC)
- `get_roi_defaults()` — GET /api/roi/defaults — pre-populated slider values

**Tab Support:** Tab 4 (modal trigger)

**Lines:** 282

---

### Services

#### `backend/app/services/agent.py`

**Purpose:** Simple rule-based decision engine. Intentionally deterministic for demo reliability.

**Key Functions/Exports:**
- `SecurityAgent` class
  - `decide(alert_type, context) -> Decision` — 4 primary rules
  - `evaluate_gates(decision, context, reasoning) -> EvalGateResult` — 4 checks: Faithfulness, Safe Action, Playbook Match, SLA
  - `maybe_trigger_evolution(decision, context) -> EvolutionTrigger | None`

**Alert Types:**
1. `anomalous_login` — travel matching → false_positive_close or escalate
2. `phishing` — known campaign signature → auto_remediate or escalate
3. `malware_detection` — asset criticality → auto_remediate or escalate_incident
4. `data_exfiltration` — always escalate_incident

**Why simple:** Demo reliability, auditability, architecture-over-sophistication thesis

**Tab Support:** Tab 2 (decision engine), Tab 3 (recommendations)

**Lines:** ~374

---

#### `backend/app/services/reasoning.py`

**Purpose:** LLM narration — Gemini 1.5 Pro generates 2-3 sentence justification AFTER decision is made.

**Key Functions/Exports:**
- `ReasoningNarrator` class
  - `generate_reasoning(alert_type, decision, context) -> str` — "intelligence theater"
  - Falls back to hardcoded template if LLM unavailable

**Tab Support:** Tab 2 (narration), Tab 3 (recommendation text)

**Lines:** ~97

---

#### `backend/app/services/situation.py` ★ NEW v2.0 — Loop 1

**Purpose:** Situation Analyzer — classifies alert situations, evaluates options with decision economics.

**Key Functions/Exports:**
- `SituationType` enum — 6 types:
  - `TRAVEL_LOGIN_ANOMALY`, `KNOWN_PHISHING_CAMPAIGN`, `CRITICAL_ASSET_MALWARE`
  - `DATA_EXFILTRATION_DETECTED`, `UNKNOWN_LOGIN_PATTERN`, `ROUTINE_MALWARE_SCAN`
- `classify_situation(alert_type, context) -> SituationType`
- `evaluate_options(situation_type, context) -> List[OptionEvaluated]`
  - 3-4 options per situation with: reasoning, confidence, estimated_resolution_time, estimated_analyst_cost, risk_if_wrong
- `analyze_situation(alert_type, context) -> SituationAnalysis`
  - Full analysis including `decision_economics` summary (time saved, cost avoided, monthly projection)

**Tab Support:** Tab 2 (context), Tab 3 (situation panel)

**Lines:** ~490

---

#### `backend/app/services/evolver.py` ★ NEW v2.0 — Loop 2

**Purpose:** AgentEvolver — tracks prompt variant performance, promotes winners, computes operational impact.

**Key Functions/Exports:**
- `PROMPT_STATS` (in-memory): TRAVEL_CONTEXT_v1 (71%), TRAVEL_CONTEXT_v2 (89%), PHISHING_RESPONSE_v1 (82%), PHISHING_RESPONSE_v2 (80%)
- `ACTIVE_PROMPTS` (in-memory): current active variant per alert type
- `get_prompt_variant(alert_type) -> str`
- `record_decision_outcome(decision_id, prompt_variant, success)`
- `check_for_promotion(alert_type) -> Optional[Dict]` — promotes if >5% improvement + 10 samples
- `generate_what_changed_narrative(alert_type, old_rate, new_rate) -> str` — plain English explanation
- `calculate_operational_impact(old_rate, new_rate) -> OperationalImpact`
  - Returns: fewer_false_escalations_pct, fewer_false_escalations_monthly, analyst_hours_recovered, estimated_monthly_savings, missed_threats (always 0)
- `get_evolution_summary(alert_type) -> PromptEvolution` — current state + what_changed_narrative + operational_impact

**Tab Support:** Tab 2 (AgentEvolver panel)

**Lines:** ~359

---

#### `backend/app/services/feedback.py` ★ NEW v2.5

**Purpose:** Outcome Feedback — processes correct/incorrect analyst verdicts and asymmetrically updates pattern confidence.

**Key Functions/Exports:**
- `process_outcome(alert_id, decision_id, outcome, analyst_notes) -> FeedbackResult`
  - `outcome="correct"` → confidence +0.3
  - `outcome="incorrect"` → confidence -6.0 (20:1 asymmetric ratio, security-first)
  - Incorrect triggers Tier 2 routing for next 5 similar alerts (self-correction)
- `get_outcome_status(alert_id) -> OutcomeStatus` — retrieve current feedback state
- `FeedbackResult` model — includes consequence_narrative, graph_updates, next_similar_alert_routing

**Key Design:** Asymmetric penalty (20:1) reflects security-first principle — earn trust slowly, lose it fast.

**Tab Support:** Tab 3 (post-execution feedback)

**Lines:** 284

---

#### `backend/app/services/policy.py` ★ NEW v2.5

**Purpose:** Policy Conflict Resolution — detects conflicting policies, resolves by priority, generates audit trail.

**Key Functions/Exports:**
- `detect_policy_conflicts(alert_id, context) -> PolicyConflictResult`
  - ALERT-7823 triggers: POLICY-SOC-003 (travel auto-close, priority 3) vs POLICY-SEC-007 (high-risk escalate, priority 1)
  - Resolved by priority: POLICY-SEC-007 wins (escalate)
  - Generates audit ID: CON-2026-XXXX
- `get_policy_history(alert_id) -> List[PolicyAuditEntry]` — immutable resolution log
- `POLICY_REGISTRY` — 4 demo policies pre-registered

**Key Design:** Security-first resolution (higher security priority always wins), every conflict gets an audit ID.

**Tab Support:** Tab 3 (policy conflict panel between Situation Analyzer and Recommendation)

**Lines:** 440

---

#### `backend/app/services/seed_neo4j.py`

**Purpose:** Neo4j seed data constants as a service module.

**v2 Updates:** Added Mary Chen user, PAT-PHISH-KNOWN pattern, PhishingCampaign node (Operation DarkHook), ALERT-7824

**Key Exports:** ASSETS, USERS, ALERT_TYPES, PATTERNS, PLAYBOOKS, seed functions

**Tab Support:** Tab 2, Tab 3

**Lines:** ~360

---

### Database Clients

#### `backend/app/db/neo4j.py`

**Purpose:** Neo4j Aura async client for security graph operations.

**Key Functions/Exports:**
- `Neo4jClient` class
  - `connect()` / `close()` — lifecycle
  - `get_security_context(alert_id) -> SecurityContext` — traverses to 47 nodes
  - `create_decision_trace(...)` — creates (:Decision), (:DecisionContext) nodes
  - `create_evolution_event(...)` — creates (:EvolutionEvent) + **(:Decision)-[:TRIGGERED_EVOLUTION]->(:EvolutionEvent)**
  - `get_alert_details(alert_id)` — fetch alert + asset + user + type
  - `get_precedent_decisions(alert_type, limit)` — similar past decisions

**Key Principle:** All Cypher is fixed (no dynamic generation) — predictable 47-node count, injection-safe

**The Key Relationship:** `(:Decision)-[:TRIGGERED_EVOLUTION]->(:EvolutionEvent)` — what SIEMs don't have

**Tab Support:** Tab 2 (context + evolution), Tab 3 (graph traversal)

**Lines:** ~500

---

### Models

#### `backend/app/models/schemas.py`

**Purpose:** Pydantic v2 models for all request/response validation.

**v2.5 Updates:** Added ROIRequest, ROIResponse, FeedbackRequest, FeedbackResult, PolicyConflictResult, PolicyAuditEntry models.

**Key Classes:**

*Tab 1:* SOCQueryRequest, MetricContract, MetricDataPoint, Provenance, SprawlAlert

*Tab 2:* ProcessAlertRequest, Deployment, EvalGateCheck, EvalGateResult, TriggeredEvolution, ExecutionStats, PromptEvolution, OperationalImpact

*Tab 3:* AlertSummary, ActionRequest, Receipt, Verification, Evidence, KpiImpact, SituationAnalysis, SituationType, OptionEvaluated, DecisionEconomics, FeedbackRequest, FeedbackResult, PolicyConflictResult

*Tab 4:* WeeklyMetrics, EvolutionEvent, CompoundingResponse, BusinessImpact, ROIRequest, ROIResponse

*Core:* SecurityContext, Decision, EvolutionTrigger

**Tab Support:** All tabs

**Lines:** ~190+ (schemas expanded across versions)

---

### Utilities

#### `backend/seed_neo4j.py`

**Purpose:** Standalone script to seed Neo4j with demo data.

**Usage:**
```bash
python backend/seed_neo4j.py
```

**Creates:** 5 users, 5 assets, 4 alert types, 6+ patterns, 4 playbooks, 6+ alerts, travel context, phishing campaign node

**Lines:** ~250

---

## Frontend Files

### Core Application

#### `frontend/src/main.tsx`

**Purpose:** React 18 entry point — mounts `<App />` in StrictMode.

**Lines:** ~10

---

#### `frontend/src/App.tsx`

**Purpose:** Root component — 4-tab navigation shell. Defaults to Tab 2 (THE DIFFERENTIATOR).

**Tab order:** SOC Analytics (1) | Runtime Evolution (2) ★ DEFAULT | Alert Triage (3) | Compounding (4)

**Lines:** ~80

---

### Tab Components

#### `frontend/src/components/tabs/SOCAnalyticsTab.tsx`

**Purpose:** Tab 1 — governed security metrics with natural language queries.

**Key Features:** NL query input, 5 example questions, metric chart (Recharts), metric contract panel, provenance panel, rule sprawl alert ($18K/month waste)

**API Calls:** POST /api/soc/query

**Tab Support:** Tab 1

**Lines:** ~466

---

#### `frontend/src/components/tabs/RuntimeEvolutionTab.tsx`

**Purpose:** Tab 2 — TRIGGERED_EVOLUTION. THE KEY DIFFERENTIATOR.

**v2.0 + v2.5 Features:**
- Deployment registry table (active v3.1 / canary v3.2)
- Process Alert button (ALERT-7823)
- **Eval Gate panel** — 4 checks, 800ms sequential animation per check
- **TRIGGERED_EVOLUTION panel** (purple) — THE KEY FEATURE
- **BLOCKED banner** — shown when eval gate fails (simulate failed gate button)
- **AgentEvolver panel** (Loop 2):
  - Variant comparison bars (TRAVEL_CONTEXT_v1 71% vs v2 89%)
  - Promotion status badge (green "Promoted ✓" or gray "Active (monitoring)")
  - "What Changed" narrative box (lightbulb icon, italic plain English)
  - Operational impact cards (5): fewer escalations %, Tier 2 reviews/month, analyst hours, monthly savings ($4,800), missed threats (always 0)
- CMA labels (CONSUME/MUTATE badges)

**API Calls:** GET /api/deployments, POST /api/alert/process, POST /api/alert/process-blocked

**Soundbites:** "Splunk gets better rules. Our copilot gets smarter." | "Loop 2 makes the agent smarter ACROSS decisions."

**Tab Support:** Tab 2 ★

**Lines:** ~777

---

#### `frontend/src/components/tabs/AlertTriageTab.tsx`

**Purpose:** Tab 3 — graph-based alert triage with closed-loop execution, feedback, and policy conflict.

**v2.0 Features:**
- Alert queue sidebar (5 alerts — travel login + phishing + more)
- Graph visualization (colored node/edge display)
- **Situation Analyzer panel:** type badge (color-coded), key factors, options bar chart, decision economics (time/cost/risk columns), economics summary box
- Recommendation panel with confidence
- **Closed Loop Execution** — 4 sequential steps: EXECUTED → VERIFIED → EVIDENCE → KPI IMPACT
- CMA label (ACTIVATE badge)

**v2.5 Features:**
- **Policy Conflict panel** (PolicyConflict component) — between Situation Analyzer and Recommendation
- **Outcome Feedback panel** (OutcomeFeedback component) — after closed loop execution

**API Calls:** GET /api/triage/alerts, POST /api/triage/analyze, POST /api/triage/execute

**Soundbite:** "A SIEM stops at detect. We close the loop."

**Tab Support:** Tab 3

**Lines:** 792

---

#### `frontend/src/components/tabs/CompoundingTab.tsx`

**Purpose:** Tab 4 — compounding intelligence dashboard proving the moat.

**v2.0 + v2.5 Features:**
- `useCountUp` custom hook — 3-second ease-out counter animation
- **Business Impact Banner** — 4 animated cards: 847 analyst hours, $127K/quarter, 75% MTTR reduction, 2,400 alerts eliminated
- **Headline Metrics** — Week 1 vs Week 4 with animated counters
- **Weekly Trend Chart** — Recharts LineChart (patterns + auto-close rate)
- **Two-Loop Hero Diagram** — dark slate background, center Neo4j graph (pulse animation), Loop 1 (blue) + Loop 2 (purple) panels, TRIGGERED_EVOLUTION badge, stats row (2→6 situation types, 0→4 prompt variants, Travel 47 / Phishing 31 patterns)
- **Evolution Events Timeline**
- **ROI Calculator trigger button** (v2.5) — opens ROICalculator modal
- Reset Demo Data button

**API Calls:** GET /api/metrics/compounding?weeks=4, POST /api/demo/reset-all

**Soundbites:** "847 analyst hours. $127K per quarter. That's the board slide." | "SIEMs get better rules. Our copilot becomes a better copilot."

**Tab Support:** Tab 4

**Lines:** 730

---

### Shared Components

#### `frontend/src/components/OutcomeFeedback.tsx` ★ NEW v2.5

**Purpose:** Post-execution outcome feedback panel — analyst rates the AI decision as correct or incorrect.

**Key Features:**
- Correct (green) / Incorrect (red) buttons — shown after closed loop completes
- Asymmetric update display: correct = +0.3 confidence, incorrect = -6.0 (20:1 ratio)
- Consequence narrative: "Confidence updated. Next 5 similar alerts → Tier 2." (if incorrect)
- Graph updates list (shows what changed in the security graph)
- `preserveFeedbackRef` pattern — fixes stale closure bug from auto-select guard

**API Calls:** POST /api/alert/outcome

**Tab Support:** Tab 3

**Lines:** 273

---

#### `frontend/src/components/PolicyConflict.tsx` ★ NEW v2.5

**Purpose:** Policy conflict detection panel — shows when two policies conflict and how the system resolves it.

**Key Features:**
- Triggered for ALERT-7823 (travel login): POLICY-SOC-003 vs POLICY-SEC-007 conflict
- Side-by-side policy comparison (auto-close priority 3 vs escalate priority 1)
- Resolution badge: "Security Policy Wins (Priority 1)" in amber
- Audit trail: CON-2026-XXXX ID, timestamp, resolution reasoning
- Security-first messaging: "When policies conflict, the more security-conservative action is taken."

**API Calls:** GET /api/alert/policy-check, GET /api/alert/policy-history

**Tab Support:** Tab 3

**Lines:** 258

---

#### `frontend/src/components/ROICalculator.tsx` ★ NEW v2.5

**Purpose:** ROI Calculator modal — prospect enters their own numbers and gets personalized savings projections.

**Key Features:**
- 6 input sliders: alerts/day, number of analysts, average salary, current MTTR, current auto-close %, escalation cost per Tier 2
- Real-time projections: annual savings breakdown, payback period, ROI multiple
- CFO narrative: pre-written paragraph with prospect-specific numbers
- Range: $428K (small SOC, 100 alerts/day) to $5.1M (large SOC, 1,000+ alerts/day)
- Soundbite: "Plug in YOUR numbers. See YOUR savings. Take this to YOUR CFO."

**API Calls:** POST /api/roi/calculate, GET /api/roi/defaults

**Tab Support:** Tab 4 (modal)

**Lines:** 589

---

### API Client and Types

#### `frontend/src/lib/api.ts`

**Purpose:** Typed API client for all backend communication.

**v2.5 Updates:** Added recordOutcome(), getOutcomeStatus(), checkPolicy(), getPolicyHistory(), calculateROI(), getROIDefaults().

**Key Functions:**

*Tab 1:* `queryMetric(query)`

*Tab 2:* `getDeployments()`, `processAlert(alertId, simulateFailure)`, `processAlertBlocked(alertId)`

*Tab 3:* `getAlerts()`, `analyzeAlert(alertId)`, `executeAction(alertId, action)`, `recordOutcome(alertId, decisionId, outcome)` (v2.5), `getOutcomeStatus(alertId)` (v2.5), `checkPolicy(alertId)` (v2.5), `getPolicyHistory(alertId)` (v2.5)

*Tab 4:* `getCompoundingMetrics(weeks)`, `resetAllDemoData()`, `calculateROI(inputs)` (v2.5), `getROIDefaults()` (v2.5)

**Tab Support:** All tabs

**Lines:** 175

---

#### `frontend/src/types/roi.ts` ★ NEW v2.5

**Purpose:** TypeScript interfaces for ROI Calculator request/response shapes.

**Key Types:** `ROIInputs`, `ROISavingsBreakdown`, `ROIResponse`

**Lines:** 45

---

## Dependency Diagram

### Backend Dependency Flow (v2.5)

```
                         main.py
                    (FastAPI Entry Point)
            Registers: evolution, triage, soc, metrics, roi
                              │
     ┌────────────┬───────────┼────────────┬────────────┐
     ▼            ▼           ▼            ▼            ▼
evolution.py  triage.py   soc.py      metrics.py    roi.py ★
(Tab 2 API)  (Tab 3 API) (Tab 1 API) (Tab 4 API) (ROI API)
     │            │
     │    ┌───────┴────────────────────┐
     │    │                           │
     ▼    ▼                           ▼
situation.py ★              feedback.py ★    policy.py ★
(Loop 1)                    (v2.5)           (v2.5)
     │
     ▼
evolver.py ★                agent.py         reasoning.py
(Loop 2)               (Decision Engine)    (LLM Narration)
                               │                  │
                    ┌──────────┴──────────┐        │
                    ▼                     ▼        ▼
                neo4j.py              schemas.py
              (Graph Client)       (Pydantic Models)

★ = New in v2.0 or v2.5
```

### Frontend Dependency Flow (v2.5)

```
                         main.tsx
                              │
                           App.tsx
                    (4-Tab Navigation)
          ┌──────────┬──────────┬──────────┐
          ▼          ▼          ▼          ▼
  SOCAnalytics  RuntimeEvol  AlertTriage  Compounding
    Tab.tsx       Tab.tsx      Tab.tsx     Tab.tsx
                              │  │           │
                    ┌─────────┘  └──┐        │
                    ▼              ▼         ▼
           OutcomeFeedback   PolicyConflict  ROICalculator
              .tsx ★            .tsx ★          .tsx ★
          └──────────┴──────────┴──────────┘
                              │
                           api.ts
                        (API Client)
                              │
                           roi.ts ★
                         (ROI Types)

★ = New in v2.5
```

---

## Tab Support Matrix (v2.5)

| File | Tab 1 | Tab 2 | Tab 3 | Tab 4 | Notes |
|------|-------|-------|-------|-------|-------|
| **Backend** |
| `main.py` | ✓ | ✓ | ✓ | ✓ | Entry point |
| `routers/soc.py` | ✓ | — | — | — | NL queries, mock BigQuery |
| `routers/evolution.py` | — | ✓ | — | — | THE DIFFERENTIATOR ★ |
| `routers/triage.py` | — | — | ✓ | — | + feedback & policy (v2.5) |
| `routers/metrics.py` | — | — | — | ✓ | Business impact |
| `routers/roi.py` ★ | — | — | — | ✓ | ROI Calculator (v2.5) |
| `services/agent.py` | — | ✓ | ✓ | — | Rule-based decision |
| `services/reasoning.py` | — | ✓ | ✓ | — | LLM narration |
| `services/situation.py` ★ | — | ✓ | ✓ | — | Loop 1 (v2.0) |
| `services/evolver.py` ★ | — | ✓ | — | — | Loop 2 (v2.0) |
| `services/feedback.py` ★ | — | — | ✓ | — | Outcome feedback (v2.5) |
| `services/policy.py` ★ | — | — | ✓ | — | Policy conflict (v2.5) |
| `services/seed_neo4j.py` | — | ✓ | ✓ | — | Seed data module |
| `db/neo4j.py` | — | ✓ | ✓ | — | Graph operations |
| `models/schemas.py` | ✓ | ✓ | ✓ | ✓ | Validation layer |
| **Frontend** |
| `main.tsx` | ✓ | ✓ | ✓ | ✓ | Entry point |
| `App.tsx` | ✓ | ✓ | ✓ | ✓ | Navigation |
| `tabs/SOCAnalyticsTab.tsx` | ✓ | — | — | — | Tab 1 UI |
| `tabs/RuntimeEvolutionTab.tsx` | — | ✓ | — | — | Tab 2 UI ★ |
| `tabs/AlertTriageTab.tsx` | — | — | ✓ | — | Tab 3 UI + feedback + policy |
| `tabs/CompoundingTab.tsx` | — | — | — | ✓ | Tab 4 UI + ROI trigger |
| `components/OutcomeFeedback.tsx` ★ | — | — | ✓ | — | v2.5 |
| `components/PolicyConflict.tsx` ★ | — | — | ✓ | — | v2.5 |
| `components/ROICalculator.tsx` ★ | — | — | — | ✓ | v2.5 |
| `lib/api.ts` | ✓ | ✓ | ✓ | ✓ | API client |
| `types/roi.ts` ★ | — | — | — | ✓ | ROI types (v2.5) |

★ = New in v2.0 or v2.5

---

## ACCP Capability Map

The demo is the progressive reference implementation of the **Agentic Cognitive Control Plane (ACCP)** — an architectural pattern for governed, self-improving enterprise AI.

**Current Progress: 10/18 capabilities (56%)**

| # | ACCP Capability | Version | Status | Where |
|---|---|---|---|---|
| 1 | Context graph substrate | v1.0 | ✅ Done | Neo4j schema, neo4j.py |
| 2 | Situation classification (Typed-Intent) | v2.0 | ✅ Done | situation.py, Tab 3 |
| 3 | Eval gates (structural safety) | v2.0 | ✅ Done | agent.py, evolution.py, Tab 2 |
| 4 | TRIGGERED_EVOLUTION | v2.0 | ✅ Done | neo4j.py → EvolutionEvent, Tab 2 purple panel |
| 5 | Decision economics | v2.0 | ✅ Done | situation.py options, Tab 3 |
| 6 | Loop 1: Situational Mesh | v2.0 | ✅ Done | situation.py, Tab 3 Situation panel |
| 7 | Loop 2: AgentEvolver | v2.0 | ✅ Done | evolver.py, Tab 2 AgentEvolver panel |
| 8 | ROI Calculator | v2.5 | ✅ Done | roi.py, ROICalculator.tsx |
| 9 | Outcome Feedback (completes TRIGGERED_EVOLUTION) | v2.5 | ✅ Done | feedback.py, OutcomeFeedback.tsx |
| 10 | Policy Conflict Resolution | v2.5 | ✅ Done | policy.py, PolicyConflict.tsx |
| 11 | Prompt Hub / Smart Queries | v3.0 | Planned | — |
| 12 | Live graph integration (de-fake backend) | v3.0 | Planned | — |
| 13 | External context ingestion (CONSUME) | v3.0 | Planned | — |
| 14 | Evidence Ledger (compliance) | v3.0 | Planned | — |
| 15 | Process intelligence integration | v3.0 | Planned | — |
| 16 | Full Situational Mesh (sub-150ms) | v3.5 | Vision | — |
| 17 | Formal Typed-Intent Bus | v3.5 | Vision | — |
| 18 | Second domain copilot + Control Tower | v4.0 | Vision | — |

---

## Key Architectural Patterns

### 1. Simple Rule-Based Agent
**File:** `services/agent.py`

Intentionally deterministic (~374 lines). The demo proves the ARCHITECTURE, not agent sophistication. Same input → same output every demo.

### 2. LLM as Narrator Only
**File:** `services/reasoning.py`

Gemini 1.5 Pro generates justification AFTER the decision is made. No LLM = no demo breakage (hardcoded fallback templates).

### 3. Fixed Cypher Queries
**File:** `db/neo4j.py`

All Neo4j queries are fixed — predictable 47-node count, no injection risks, fast execution.

### 4. TRIGGERED_EVOLUTION Relationship
**Files:** `db/neo4j.py`, `routers/evolution.py`

`(:Decision)-[:TRIGGERED_EVOLUTION]->(:EvolutionEvent)` — this graph relationship is THE DIFFERENTIATOR from SIEMs.

### 5. Two-Loop Architecture
**Files:** `services/situation.py` (Loop 1), `services/evolver.py` (Loop 2)

- **Loop 1:** Smarter WITHIN each decision — classify situation, evaluate options, provide economics
- **Loop 2:** Smarter ACROSS all decisions — track prompt variants, promote winners, compute impact
- Both loops write to the same graph → **COMPOUNDING**

### 6. Asymmetric Feedback (v2.5)
**File:** `services/feedback.py`

Correct = +0.3, Incorrect = -6.0 (20:1 ratio). Security-first: earn trust slowly, lose it fast.

### 7. Priority-Based Policy Resolution (v2.5)
**File:** `services/policy.py`

When policies conflict, higher security priority wins. Every resolution gets an immutable audit ID.

---

## File Size Summary (v2.5)

| Category | Files | Total Lines |
|----------|-------|-------------|
| **Backend Routers** | 5 | ~2,055 |
| **Backend Services** | 7 | ~2,404 |
| **Backend DB** | 1 | ~500 |
| **Backend Models** | 1 | ~190 |
| **Backend Utils** | 1 | ~250 |
| **Frontend Tabs** | 4 | ~2,765 |
| **Frontend Shared Components** | 3 | ~1,120 |
| **Frontend Core** | 2 | ~90 |
| **Frontend API + Types** | 2 | ~220 |
| **Total** | **26** | **~9,594** |

*v2.5 added 7 new files (+2,171 lines) and expanded 4 existing files (+~400 lines) vs v2.0.*

---

## The Seven Key Files (Core v2.5 Demo)

If you read only 7 files to understand the full v2.5 demo:

1. **`routers/evolution.py`** — Full Tab 2 flow: situation, agent decision, eval gate, TRIGGERED_EVOLUTION, AgentEvolver
2. **`services/situation.py`** — Loop 1: Situation Analyzer with 6 types and decision economics
3. **`services/evolver.py`** — Loop 2: AgentEvolver with variant tracking and operational impact
4. **`services/feedback.py`** — v2.5: Asymmetric outcome learning (20:1 penalty ratio)
5. **`services/policy.py`** — v2.5: Policy conflict detection and priority resolution
6. **`tabs/RuntimeEvolutionTab.tsx`** — The UI showing both loops, eval gate animation, and operational impact
7. **`tabs/AlertTriageTab.tsx`** — The UI showing situation analysis, closed loop, feedback, and policy

These 7 files (~3,320 lines) contain the complete v2.5 demo thesis.

---

## Ports and Commands

```bash
# Backend (v2.5 uses port 8001)
cd backend
uvicorn app.main:app --reload --port 8001

# Frontend (v2.5 uses port 5174)
cd frontend
npx vite --port 5174

# Seed Neo4j (required for Tab 3)
python backend/seed_neo4j.py

# View demo
http://localhost:5174
```

## Environment Variables

```bash
# GCP
PROJECT_ID=soc-copilot-demo
REGION=us-central1

# Neo4j Aura (required for Tabs 2, 3)
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password

# Vertex AI (optional — reasoning.py has fallback)
VERTEX_AI_LOCATION=us-central1
VERTEX_AI_MODEL=gemini-1.5-pro-002
```

---

## Known Issues (v2.5)

| Issue | Severity | Notes |
|-------|----------|-------|
| In-memory state for feedback/policy | Medium | Fine for 10-min demo; fails 30-min deep dive. Fix planned for v3.0 (Live Graph Integration) |
| Floating point display (0.8300000001) | Low | Round to 1 decimal in OutcomeFeedback |
| Policy Conflict doesn't override Recommendation | Design gap | Policy says escalate, Recommendation says auto-close. Presenter narrates override. Fix in v3.0 |
| Tab 1 regression not formally verified | Low | Quick pass to verify NL queries still work after v2.5 changes |

---

**Last Updated:** February 20, 2026
**Status:** v2.5 Complete and Tagged. ACCP 10/18 (56%). Next: Docker packaging (D1-D4) OR Loom v2 script OR v3.0 build.
**Key Principle:** The demo proves the ARCHITECTURE (two loops → compounding), not agent sophistication.
**v2.5 Focus:** Interactivity — the prospect can input their own numbers (ROI), see decisions learn (Feedback), and watch policy conflicts resolve (Policy).
