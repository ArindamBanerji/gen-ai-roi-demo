# SOC Copilot Demo - Project Structure

**Last Updated:** February 25, 2026
**Version:** v3.2 (Domain-Agnostic Refactoring Complete)
**Total Files:** ~42 code files (~14,000+ lines)
**Architecture:** Domain-agnostic two-loop compounding intelligence — Situation Analyzer (Loop 1) + AgentEvolver (Loop 2) — with Evidence Ledger, live Threat Intel, Decision Explainer, and pluggable domain modules
**ACCP Progress:** 12/18 capabilities implemented

---

## Table of Contents

- [Directory Tree](#directory-tree)
- [Version History](#version-history)
- [Backend Files](#backend-files)
  - [Main Application](#main-application)
  - [Routers](#routers)
  - [Services](#services)
  - [Core Package (v3.2)](#core-package-v32)
  - [Domains Package (v3.2)](#domains-package-v32)
  - [Database Clients](#database-clients)
  - [Models](#models)
- [Frontend Files](#frontend-files)
  - [Core Application](#core-application)
  - [Tab Components](#tab-components)
  - [Shared Components](#shared-components)
  - [API Client and Types](#api-client-and-types)
- [Dependency Diagram](#dependency-diagram)
- [Tab Support Matrix](#tab-support-matrix)
- [ACCP Capability Map](#accp-capability-map)
- [Key Architectural Patterns](#key-architectural-patterns)
- [File Size Summary](#file-size-summary)
- [Ports and Commands](#ports-and-commands)

---

## Directory Tree

```
gen-ai-roi-demo-v3.2/
│
├── .gitignore
├── CLAUDE.md                             # Project instructions (always read first)
├── docs/
│   ├── PROJECT_STRUCTURE.md              # THIS FILE
│   └── (other design docs)
│
├── backend/
│   ├── requirements.txt                  # Python dependencies
│   ├── seed_neo4j.py                     # Standalone Neo4j seed script
│   ├── test_policy_endpoints.py          # Policy endpoint smoke tests
│   └── app/
│       ├── main.py                       # FastAPI app entry point
│       │
│       ├── routers/
│       │   ├── __init__.py
│       │   ├── soc.py                    # Tab 1: SOC Analytics
│       │   ├── evolution.py              # Tab 2: Runtime Evolution ★ THE DIFFERENTIATOR
│       │   ├── triage.py                 # Tab 3: Alert Triage (+ feedback, policy, decision factors)
│       │   ├── metrics.py                # Tab 4: Compounding Metrics (+ /api/demo/domains v3.2)
│       │   ├── roi.py                    # ROI Calculator endpoint
│       │   ├── audit.py                  # ★ NEW v3.0: Evidence Ledger (JSON/CSV export + chain verify)
│       │   └── graph.py                  # ★ NEW v3.0: Threat Intel refresh endpoint
│       │
│       ├── services/
│       │   ├── __init__.py
│       │   ├── agent.py                  # Simple rule-based decision engine
│       │   ├── reasoning.py              # LLM narration (Gemini 1.5 Pro)
│       │   ├── situation.py              # Loop 1: Situation Analyzer (delegates to domains/soc/)
│       │   ├── evolver.py                # Loop 2: AgentEvolver
│       │   ├── feedback.py               # Outcome Feedback (asymmetric 20:1 penalty)
│       │   ├── policy.py                 # Policy Conflict Resolution (delegates to domains/soc/)
│       │   ├── seed_neo4j.py             # Neo4j seed data constants
│       │   ├── audit.py                  # ★ NEW v3.0: SHA-256 hash-chain decision ledger
│       │   ├── threat_intel.py           # ★ NEW v3.0: Pulsedive + hardcoded IOC enrichment
│       │   └── triage.py                 # ★ NEW v3.0: Decision factor breakdown (delegates to domains/soc/)
│       │
│       ├── core/                         # ★ NEW v3.2: Framework layer (domain-agnostic)
│       │   ├── __init__.py
│       │   ├── state_manager.py          # Centralized demo reset coordinator
│       │   └── domain_registry.py        # Registry of all available domain configs
│       │
│       ├── domains/                      # ★ NEW v3.2: Domain module layer
│       │   ├── __init__.py
│       │   ├── base.py                   # DomainConfig ABC + dataclasses
│       │   ├── soc/                      # SOC domain implementation (active)
│       │   │   ├── __init__.py
│       │   │   ├── config.py             # SOCDomainConfig (implements DomainConfig)
│       │   │   ├── factors.py            # SOC factor computation (extracted from triage.py)
│       │   │   ├── situations.py         # SOC situation classification (extracted from situation.py)
│       │   │   └── policies.py           # SOC policy definitions (extracted from policy.py)
│       │   └── supply_chain/             # S2P domain stub (smoke test — not active)
│       │       ├── __init__.py
│       │       └── config.py             # S2PDomainConfig (full schema, stubs for classify/compute)
│       │
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
        │   ├── api.ts                    # Backend API client
        │   └── domain.ts                 # ★ NEW v3.2: Frontend domain config singleton
        ├── types/
        │   └── roi.ts                    # ROI TypeScript types
        └── components/
            ├── OutcomeFeedback.tsx       # Correct/Incorrect feedback panel
            ├── PolicyConflict.tsx        # Policy conflict detection panel
            ├── ROICalculator.tsx         # ROI Calculator modal
            └── tabs/
                ├── SOCAnalyticsTab.tsx        # Tab 1: SOC Analytics
                ├── RuntimeEvolutionTab.tsx    # Tab 2: Runtime Evolution ★
                ├── AlertTriageTab.tsx         # Tab 3: Alert Triage
                └── CompoundingTab.tsx         # Tab 4: Compounding Dashboard
```

---

## Version History

**Branch:** `main`
**Current:** v3.2 — domain-agnostic refactoring complete

---

### Waves 1–6E: Two-Loop Architecture ✅ (v2.0)

See v2.5 documentation for details. Key additions:
- **Waves 1–6:** Situation Analyzer (Loop 1), AgentEvolver (Loop 2), eval gate animation, business impact banner, two-loop hero diagram, CMA labels
- Resulted in: `situation.py`, `evolver.py`, expanded `evolution.py`, `triage.py`, `metrics.py`

---

### Waves 7–9: Interactivity Layer ✅ (v2.5)

- **Wave 7:** ROI Calculator — `roi.py` (NEW), `ROICalculator.tsx` (NEW), `roi.ts` (NEW); $428K–$5.1M projections
- **Wave 8:** Outcome Feedback — `feedback.py` (NEW), `OutcomeFeedback.tsx` (NEW); asymmetric 20:1 penalty, `preserveFeedbackRef` stale-closure fix
- **Wave 9:** Policy Conflict Resolution — `policy.py` (NEW), `PolicyConflict.tsx` (NEW); 4 policies, CON-2026-XXXX audit IDs

---

### Session 4: Evidence Ledger ✅ (v3.0)

- **Files:** `services/audit.py` (NEW), `routers/audit.py` (NEW)
- **Features:**
  - SHA-256 hash-chain decision ledger — each record chains off the previous hash (genesis: `SOC_COPILOT_GENESIS_2026`)
  - Immutable fields hashed: `id`, `alert_id`, `timestamp`, `situation_type`, `action_taken`, `factors`, `confidence`
  - Mutable fields (`outcome`, `analyst_confirmed`) excluded from hash so verify passes after feedback
  - `reconstruct_from_memory()` — back-fills ledger from `FEEDBACK_GIVEN` without touching other services
  - `GET /api/audit/decisions?format=json|csv` — JSON array or CSV file download (`soc_decision_audit.csv`)
  - `GET /api/audit/verify` — SHA-256 chain walk, returns `verified=True|False` + chain_length
- **ACCP:** Implements capability #14 (Evidence Ledger / compliance audit trail)

---

### Session 5: Decision Explainer + Live Threat Intel ✅ (v3.0)

- **Files:** `services/threat_intel.py` (NEW), `services/triage.py` (NEW), `routers/graph.py` (NEW)
- **Features:**
  - **Threat Intel Service** — fetches 5 curated IOCs from Pulsedive live API (when `PULSEDIVE_API_KEY` set) or hardcoded fallback. MERGEs `:ThreatIntel` nodes and `:ASSOCIATED_WITH` edges into Neo4j
  - **Decision Factor Service** — 6-factor breakdown for any alert: 5 static factors + 1 live `threat_intel_enrichment` factor queried from Neo4j. Final order: travel_match/campaign_signature → asset_criticality → **threat_intel_enrichment** → time_anomaly → device_trust → pattern_history
  - **Graph Router** — `POST /api/graph/threat-intel/refresh` triggers live enrichment
  - `services/triage.py` delegates factor computation to `domains/soc/factors.py`
- **Neo4j schema addition:** `:ThreatIntel` nodes with `ASSOCIATED_WITH` edges to `:Alert`

---

### v3.1: Code Review HIGH Findings ✅ (v3.1)

- **Files:** Various (services, routers, frontend)
- **Fixes:** HIGH-severity issues from CODE_REVIEW_V31_PASS1.md — ~12K lines at this point

---

### v3.2: Domain-Agnostic Refactoring ✅ (v3.2 — R1–R12 + S2P Smoke Test)

**Principle:** Core framework (`core/`) is domain-agnostic. Domain-specific logic lives in `domains/soc/` or `domains/supply_chain/`. Adding a new domain requires no changes to `core/`.

**R1–R8: Backend domain extraction**
- Created `core/` package: `state_manager.py` (reset coordinator), `domain_registry.py` (domain registry)
- Created `domains/` package: `base.py` (DomainConfig ABC + dataclasses)
- Created `domains/soc/` module: `config.py`, `factors.py`, `situations.py`, `policies.py`
- Extracted SOC-specific logic from `services/situation.py` → `domains/soc/situations.py`
- Extracted SOC-specific logic from `services/policy.py` → `domains/soc/policies.py`
- Extracted SOC-specific logic from `services/triage.py` → `domains/soc/factors.py`

**R9–R11: Frontend parameterization**
- Created `frontend/src/lib/domain.ts` — single source of truth for all domain-specific frontend labels
- Parameterized `CompoundingTab.tsx` (R9), `RuntimeEvolutionTab.tsx` (R10), `AlertTriageTab.tsx` (R11), `App.tsx` header
- All domain-specific UI strings now imported from `domainConfig` instead of hardcoded

**R12: M-3 fix + domain.ts audit**
- Fixed `setTimeout` leak in `AlertTriageTab.tsx` — `timerIdsRef` + cleanup `useEffect`
- Audited `domain.ts` completeness — all used fields confirmed, unused speculatively-added fields documented

**S2P Smoke Test:**
- Created `domains/supply_chain/config.py` — full `S2PDomainConfig` (6 factors, 5 actions, 6 situation types, 4 policies, 4 prompt variants)
- Registered in `domain_registry.py` alongside `soc_config`
- `ACTIVE_DOMAIN = "soc"` — S2P is registered but not active

**Domain endpoint:**
- Added `GET /api/demo/domains` to `metrics.py` — lists all registered domains and active domain

---

## Backend Files

### Main Application

#### `backend/app/main.py`

**Purpose:** FastAPI application entry point with CORS and router registration.

**Routers registered:** evolution, triage, soc, metrics, roi, audit (v3.0), graph (v3.0)

**Tab Support:** All tabs

**Lines:** ~70

---

### Routers

#### `backend/app/routers/soc.py`

**Purpose:** Tab 1 (SOC Analytics) — natural language metric queries with governance and provenance.

**Key Functions/Exports:**
- `query_soc_metrics(request)` — POST /api/soc/query — keyword match → chart + contract + provenance + sprawl
- `list_metrics()` — GET /api/soc/metrics
- `check_for_sprawl(metric_id)` — Rule sprawl detection ($18K/month waste found)

**Key Data:** `METRIC_REGISTRY` — 6 metrics: MTTR, auto-close rate, FP rate, escalation rate, MTTD, analyst efficiency

**Tab Support:** Tab 1

**Lines:** ~403

---

#### `backend/app/routers/evolution.py`

**Purpose:** Tab 2 (Runtime Evolution) — TRIGGERED_EVOLUTION. THE KEY DIFFERENTIATOR.

**Key Functions/Exports:**
- `get_deployments()` — GET /api/deployments — returns v3.1 (active) + v3.2 (canary)
- `process_alert(request)` — POST /api/alert/process — 9-step main flow:
  1. Get security context (47 nodes from Neo4j)
  2. Situation analysis (`situation.py` → `domains/soc/situations.py`)
  3. Agent decision (rule-based `agent.py`)
  4. LLM reasoning narration (`reasoning.py`)
  5. Eval gate (4 checks)
  6. Create decision trace in Neo4j
  7. Check if evolution triggers
  8. Create `(:Decision)-[:TRIGGERED_EVOLUTION]->(:EvolutionEvent)` relationship
  9. Get prompt evolution summary (`evolver.py`)
- `process_alert_blocked(request)` — POST /api/alert/process-blocked — simulates eval gate failure

**Tab Support:** Tab 2 ★ THE DIFFERENTIATOR

**Lines:** ~350

---

#### `backend/app/routers/triage.py`

**Purpose:** Tab 3 (Alert Triage) — graph-based analysis, closed-loop execution, feedback, policy, and decision factors.

**Key Functions/Exports:**
- `get_alert_queue()` — GET /api/triage/alerts — 5 pending alerts
- `analyze_alert(alert_id)` — POST /api/triage/analyze — graph traversal + situation analysis + recommendation
- `execute_action(request)` — POST /api/triage/execute — 4-step closed loop
- `get_decision_factors_endpoint(alert_id)` — GET /api/triage/decision-factors/{alert_id} — 6-factor breakdown (v3.0)
- `record_outcome(request)` — POST /api/alert/outcome — correct/incorrect feedback
- `get_outcome_status(alert_id)` — GET /api/alert/outcome/status
- `check_policy(alert_id)` — GET /api/alert/policy-check
- `get_policy_history(alert_id)` — GET /api/alert/policy-history

**Tab Support:** Tab 3

**Lines:** ~670

---

#### `backend/app/routers/metrics.py`

**Purpose:** Tab 4 (Compounding Dashboard) — week-over-week intelligence growth, business impact, demo utilities.

**Key Functions/Exports:**
- `get_compounding_metrics(weeks=4)` — GET /api/metrics/compounding
- `get_evolution_events(limit=10)` — GET /api/metrics/evolution-events
- `seed_neo4j()` — POST /api/demo/seed
- `reset_all_demo_data()` — POST /api/demo/reset-all — re-seeds + calls `state_manager.reset_all()`
- `reset_demo_data()` — POST /api/demo/reset — legacy Week 1 reset
- `get_registered_domains()` — GET /api/demo/domains — ★ NEW v3.2: lists all registered domain configs

**Key Numbers:**
- Week 1: 23 patterns, 68% auto-close → Week 4: 127 patterns, 89% auto-close
- Business Impact: 847 hrs/month, $127K/quarter, 75% MTTR reduction, 2,400 backlog eliminated

**Tab Support:** Tab 4

**Lines:** ~405

---

#### `backend/app/routers/roi.py`

**Purpose:** ROI Calculator — prospect-specific savings projections.

**Key Functions/Exports:**
- `calculate_roi(request)` — POST /api/roi/calculate — 6 inputs → annual savings + payback + ROI multiple + CFO narrative
- `get_roi_defaults()` — GET /api/roi/defaults

**Range:** $428K (small SOC) to $5.1M (large SOC)

**Tab Support:** Tab 4 (modal trigger)

**Lines:** ~282

---

#### `backend/app/routers/audit.py` ★ NEW v3.0

**Purpose:** Evidence Ledger — decision audit trail with JSON/CSV export and SHA-256 chain verification.

**Key Functions/Exports:**
- `get_audit_decisions(format="json")` — GET /api/audit/decisions?format=json|csv
  - JSON: `{ decisions: [...], total: N }`
  - CSV: `soc_decision_audit.csv` file download (columns: id, alert_id, timestamp, situation_type, action_taken, factors, confidence, outcome, hash)
- `verify_audit_chain()` — GET /api/audit/verify
  - Returns: `{ chain_length, verified, first_record, last_record }` (plus `broken_at_index` if false)

**Key Design:** Calls `reconstruct_from_memory()` on every request to back-fill from `feedback.py` state before returning.

**Tab Support:** Tab 4 (Evidence Ledger panel)

**Lines:** ~147

---

#### `backend/app/routers/graph.py` ★ NEW v3.0

**Purpose:** Graph Intelligence — Threat Intel refresh endpoint.

**Key Functions/Exports:**
- `refresh_threat_intel_endpoint()` — POST /api/graph/threat-intel/refresh
  - Delegates to `services/threat_intel.refresh_threat_intel()`
  - Returns: source, indicators_ingested, relationships_created, enrichment_summary, live_attempted, live_succeeded, timestamp

**Tab Support:** Tab 3 (Refresh Threat Intel button)

**Lines:** ~42

---

### Services

#### `backend/app/services/agent.py`

**Purpose:** Simple rule-based decision engine. Intentionally deterministic for demo reliability.

**Key Functions/Exports:**
- `SecurityAgent` class:
  - `decide(alert_type, context) -> Decision` — 4 primary rules
  - `evaluate_gates(decision, context, reasoning) -> EvalGateResult` — 4 checks: Faithfulness, Safe Action, Playbook Match, SLA
  - `maybe_trigger_evolution(decision, context) -> EvolutionTrigger | None`

**Alert types:** `anomalous_login`, `phishing`, `malware_detection`, `data_exfiltration`

**Tab Support:** Tab 2 (decision engine), Tab 3 (recommendations)

**Lines:** ~374

---

#### `backend/app/services/reasoning.py`

**Purpose:** LLM narration — Gemini 1.5 Pro generates 2-3 sentence justification AFTER the decision is made ("intelligence theater").

**Key Functions/Exports:**
- `ReasoningNarrator.generate_reasoning(alert_type, decision, context) -> str`
- Falls back to hardcoded template if LLM unavailable (no demo breakage)

**Tab Support:** Tab 2, Tab 3

**Lines:** ~97

---

#### `backend/app/services/situation.py` — Loop 1

**Purpose:** Situation Analyzer — classifies alert situations, evaluates options with decision economics. **Delegates SOC-specific logic to `domains/soc/situations.py`.**

**Key Functions/Exports:**
- `SituationType` enum — 6 types: `TRAVEL_LOGIN_ANOMALY`, `KNOWN_PHISHING_CAMPAIGN`, `CRITICAL_ASSET_MALWARE`, `DATA_EXFILTRATION_DETECTED`, `UNKNOWN_LOGIN_PATTERN`, `ROUTINE_MALWARE_SCAN`
- `classify_situation(alert_type, context) -> SituationType`
- `evaluate_options(situation_type, context) -> List[OptionEvaluated]` — 3-4 options with time/cost/risk per option
- `analyze_situation(alert_type, context) -> SituationAnalysis` — includes `decision_economics` summary

**Tab Support:** Tab 2 (context), Tab 3 (situation panel)

**Lines:** ~490

---

#### `backend/app/services/evolver.py` — Loop 2

**Purpose:** AgentEvolver — tracks prompt variant performance, promotes winners, computes operational impact.

**Key Functions/Exports:**
- `PROMPT_STATS` (in-memory): TRAVEL_CONTEXT_v1 (71%), TRAVEL_CONTEXT_v2 (89%), PHISHING_RESPONSE_v1 (82%), PHISHING_RESPONSE_v2 (80%)
- `get_prompt_variant(alert_type) -> str`
- `record_decision_outcome(decision_id, prompt_variant, success)`
- `check_for_promotion(alert_type) -> Optional[Dict]` — promotes if >5% improvement + 10 samples
- `generate_what_changed_narrative(alert_type, old_rate, new_rate) -> str`
- `calculate_operational_impact(old_rate, new_rate) -> OperationalImpact`
- `get_evolution_summary(alert_type) -> PromptEvolution`

**Tab Support:** Tab 2 (AgentEvolver panel)

**Lines:** ~359

---

#### `backend/app/services/feedback.py`

**Purpose:** Outcome Feedback — processes correct/incorrect analyst verdicts with asymmetric confidence updates.

**Key Functions/Exports:**
- `process_outcome(alert_id, decision_id, outcome, analyst_notes) -> FeedbackResult`
  - `correct` → confidence +0.3
  - `incorrect` → confidence -6.0 (20:1 asymmetric ratio — security-first)
  - Incorrect triggers Tier 2 routing for next 5 similar alerts
- `get_outcome_status(alert_id) -> OutcomeStatus`

**Tab Support:** Tab 3 (post-execution feedback)

**Lines:** ~284

---

#### `backend/app/services/policy.py`

**Purpose:** Policy Conflict Resolution — detects conflicting policies, resolves by priority, generates audit trail. **Delegates policy definitions to `domains/soc/policies.py`.**

**Key Functions/Exports:**
- `detect_policy_conflicts(alert_id, context) -> PolicyConflictResult`
  - ALERT-7823 triggers: POLICY-SOC-003 (travel auto-close, priority 3) vs POLICY-SEC-007 (high-risk escalate, priority 1)
  - Resolved by priority (lower number = higher priority): POLICY-SEC-007 wins
  - Generates audit ID: CON-2026-XXXX
- `get_policy_history(alert_id) -> List[PolicyAuditEntry]`
- `POLICY_REGISTRY` — 4 demo policies pre-registered

**Tab Support:** Tab 3 (policy conflict panel)

**Lines:** ~440

---

#### `backend/app/services/seed_neo4j.py`

**Purpose:** Neo4j seed data constants as a service module. Called by `/api/demo/seed` and `/api/demo/reset-all`.

**Key Exports:** ASSETS, USERS, ALERT_TYPES, PATTERNS, PLAYBOOKS, seed functions. Includes Mary Chen / ALERT-7824 / PAT-PHISH-KNOWN / PhishingCampaign (Operation DarkHook).

**Tab Support:** Tab 2, Tab 3

**Lines:** ~360

---

#### `backend/app/services/audit.py` ★ NEW v3.0

**Purpose:** SHA-256 hash-chain decision ledger — Evidence Ledger core implementation.

**Key Constants:**
- `_GENESIS_HASH = "SOC_COPILOT_GENESIS_2026"` — chain seed
- `_HASH_FIELDS` — immutable fields included in hash: id, alert_id, timestamp, situation_type, action_taken, factors, confidence
- `_ALERT_DEFAULTS` — demo-derived defaults for ALERT-7823 and ALERT-7824

**Key Functions/Exports:**
- `record_decision(alert_id, situation_type, action_taken, factors, confidence) -> Dict`
  - Creates record, computes `SHA-256(previous_hash + JSON(immutable_fields))`, appends to `_DECISIONS`
- `record_outcome(alert_id, outcome, analyst_notes) -> Optional[Dict]`
  - Mutates outcome/analyst_confirmed; hash NOT recomputed (outcome is mutable by design)
- `get_decisions() -> List[Dict]` — most recent first
- `reconstruct_from_memory() -> int` — back-fills from `feedback.FEEDBACK_GIVEN` without touching other modules
- `reset_audit_state()` — clears ledger (called by `state_manager.reset_all()`)
- `verify_chain() -> Dict` — walks ledger chronologically, recomputes hashes, returns verified=True|False

**Tab Support:** Tab 4 (Evidence Ledger panel) + accessible via curl

**Lines:** ~299

---

#### `backend/app/services/threat_intel.py` ★ NEW v3.0

**Purpose:** Pulsedive integration with hardcoded fallback — enriches Neo4j security graph with live IOC data.

**Key Constants:**
- `PULSEDIVE_API_KEY` — from env (optional; no key = full hardcoded fallback)
- `DEMO_IOCS` — 5 curated indicators: Singapore IP, Tor exit node, Cobalt Strike C2 domain, recon scanner, malware tracker
- `HARDCODED_FALLBACK` — complete enrichment data for all 5 IOCs (no API key required for demo)
- `ALERT_IOC_MAP` — `{"ALERT-7823": ["103.15.42.17"]}` — direct IOC-to-alert linkages

**Key Functions/Exports:**
- `refresh_threat_intel() -> Dict` — full enrichment pipeline:
  1. Fetch from Pulsedive live API (if key present, 0.5s between calls for rate limiting)
  2. Per-IOC fallback on failure; full hardcoded fallback if no key
  3. MERGE `:ThreatIntel` nodes into Neo4j (idempotent — updates if node exists)
  4. MERGE `:ASSOCIATED_WITH` edges to `:Alert` nodes per `ALERT_IOC_MAP`
  5. Return summary dict

**Neo4j additions:** `:ThreatIntel {value, type, severity, source, risk_factors, first_seen, last_updated, context, refreshed_at}` with `(:ThreatIntel)-[:ASSOCIATED_WITH]->(:Alert)` edges

**Tab Support:** Tab 3 (Refresh Threat Intel button → decision factors)

**Lines:** ~357

---

#### `backend/app/services/triage.py` ★ NEW v3.0

**Purpose:** Decision Factor Breakdown service — 6-factor explainability for agent decisions. The 6th factor (`threat_intel_enrichment`) is queried live from Neo4j.

**Key Functions/Exports:**
- `get_decision_factors(alert_id) -> Optional[Dict]`
  - Calls `domains/soc/factors.compute_soc_factors(alert_id, ti_factor)` with 5 static factors
  - Queries Neo4j for `(:ThreatIntel)-[:ASSOCIATED_WITH]->(:Alert {id: alert_id})` to build the 6th live factor
  - Inserts `threat_intel_enrichment` at index 2 in final factor list

**Factor order:**
1. travel_match / campaign_signature_match / alert_severity
2. asset_criticality / sender_domain_risk
3. **threat_intel_enrichment** ← live Neo4j query
4. time_anomaly
5. device_trust / asset_criticality
6. pattern_history

**Tab Support:** Tab 3 (Decision Explainer / decision factors panel)

**Lines:** ~128

---

### Core Package (v3.2)

#### `backend/app/core/state_manager.py` ★ NEW v3.2

**Purpose:** Centralized demo reset coordinator — every stateful service registers a reset handler here. Reset endpoints call `state_manager.reset_all()` instead of knowing about individual services.

**Key Exports:**
- `DemoStateManager` class:
  - `register(name, reset_handler)` — idempotent handler registration
  - `reset_all()` — calls every registered handler
  - `get_registered() -> List[str]`
- `state_manager` — module-level singleton

**Registered handlers:** `evolver`, `audit`, `feedback`, `policy` (each service registers itself at import time)

**Lines:** ~45

---

#### `backend/app/core/domain_registry.py` ★ NEW v3.2

**Purpose:** Registry of all available domain configs. Tracks `ACTIVE_DOMAIN` and provides `get_domain_config()` accessor.

**Key Exports:**
- `ACTIVE_DOMAIN: str = "soc"` — the currently active domain
- `_DOMAIN_CONFIGS: Dict[str, DomainConfig]` — `{"soc": soc_config, "supply_chain": s2p_config}`
- `get_active_domain() -> str`
- `get_domain_config(domain_name: Optional[str] = None) -> DomainConfig`
  - `None` → returns active domain config
  - Named → returns that domain's config (raises `KeyError` if not registered)

**How to add a domain:** Add `from app.domains.new_domain.config import new_config` + `"new_domain": new_config` to `_DOMAIN_CONFIGS`. No core/ changes needed.

**Lines:** ~44

---

### Domains Package (v3.2)

#### `backend/app/domains/base.py` ★ NEW v3.2

**Purpose:** Abstract base class (`DomainConfig`) and shared dataclasses that all domain modules must implement.

**Key Exports:**

*Dataclasses:*
- `DomainAction` — `id, label, time_saved_min, cost_dollars, risk_level`
- `DomainFactor` — `id, label, description`
- `DomainSituationType` — `id, label, description, color`
- `DomainPolicy` — `id, name, rule, priority, action_override`
- `PromptVariant` — `id, category, version, description`

*Abstract class `DomainConfig(ABC)`:*
- **10 abstract properties:** `name`, `display_name`, `trigger_entity`, `factors`, `actions`, `situation_types`, `policies`, `asymmetry_ratio`, `prompt_variants`, `metrics_config`
- **3 abstract methods:** `get_seed_queries()`, `get_graph_query_templates()`, `get_narration_templates()`

**Lines:** ~122

---

#### `backend/app/domains/soc/` ★ NEW v3.2 (extracted from services/)

**`config.py` — SOCDomainConfig:**
- Implements all 13 abstract members of `DomainConfig`
- `name="soc"`, `display_name="SOC Copilot"`, `trigger_entity="Alert"`
- 6 factors: travel_match, asset_criticality, time_anomaly, device_trust, pattern_history, behavioral_baseline
- 5 actions: false_positive_close, auto_remediate, enrich_and_wait, escalate_tier2, escalate_incident
- 6 situation types: TRAVEL_LOGIN_ANOMALY, KNOWN_PHISHING_CAMPAIGN, CRITICAL_ASSET_MALWARE, DATA_EXFILTRATION_DETECTED, UNKNOWN_LOGIN_PATTERN, ROUTINE_MALWARE_SCAN
- 4 policies with priority-1 conflict pair (POLICY-SOC-003 vs POLICY-SEC-007 for ALERT-7823)
- `asymmetry_ratio = 20.0` — security-first: earn trust slowly, lose it fast
- `soc_config = SOCDomainConfig()` singleton

**`factors.py` — SOC Factor Computation:**
- `compute_soc_factors(alert_id, ti_factor) -> Dict` — builds 5 static factors + inserts `ti_factor` at index 2
- `_contribution(value, weight) -> str` — "high" / "medium" / "low" / "none"
- `SOC_FACTOR_TEMPLATES` — static factor data per alert ID + `"_default"` fallback

**`situations.py` — SOC Situation Classification:**
- `classify_soc_situation(alert_type, context) -> (str, float, List[str])` — tuple: (situation_type_id, confidence, primary_factors)
- `get_soc_options(situation_type, context) -> List[Dict]` — 3-4 options per situation with time/cost/risk
- `SOC_SITUATION_TYPES` — metadata dict for all 6 situation types
- `SOC_OPTIONS` — raw option data per situation type (plain dicts)

**`policies.py` — SOC Policy Definitions:**
- `get_applicable_soc_policies(alert_id, context) -> List[Dict]` — returns applicable policies for an alert
- `SOC_POLICIES` — 4 SOC policy definitions as plain dicts

---

#### `backend/app/domains/supply_chain/` ★ NEW v3.2 (smoke test stub)

**`config.py` — S2PDomainConfig:**
- Implements all 13 abstract members — full schema, not yet operationally connected
- `name="supply_chain"`, `display_name="Procurement Copilot"`, `trigger_entity="Purchase Order"`
- 6 factors: price_variance, demand_urgency, supplier_reliability, geopolitical_risk, alternative_availability, spend_pattern_history
- 5 actions: auto_approve_po, flag_for_review, trigger_dual_sourcing, escalate_to_procurement_lead, hold_pending_compliance
- 6 situation types: ROUTINE_REORDER, PRICE_ANOMALY, SUPPLY_RISK, DEMAND_SPIKE, SINGLE_SOURCE_DEPENDENCY, COMPLIANCE_FLAG
- 4 policies: POLICY-PROC-001 (priority 3), POLICY-COST-002 (priority 2), POLICY-RISK-003 (priority 1), POLICY-DUAL-004 (priority 1) — ⚠ priority-1 tie (RF-3)
- `asymmetry_ratio = 12.0` — lower than SOC (procurement errors are recoverable)
- 4 prompt variants: PO_APPROVAL_v1/v2, RISK_ASSESSMENT_v1/v2
- S2P-specific metrics keys: `po_auto_approved_monthly`, `cost_avoided_quarterly`, `cycle_time_reduction_pct`, `supplier_risk_mitigated`
- `classify_situation()` and `compute_factors()` raise `NotImplementedError` (stubs)
- `s2p_config = S2PDomainConfig()` singleton

**Known limitations (smoke test report):**
- RF-1: `metrics_config` docstring in `base.py` lists SOC-specific key names (documentation debt — no runtime impact)
- RF-2: `classify_situation`/`compute_factors` are not abstract methods in `DomainConfig` ABC (they live in `services/`, not enforced by interface)
- RF-3: POLICY-RISK-003 and POLICY-DUAL-004 both have priority=1 with different actions — winner determined by list position (stable sort limitation in `services/policy.py`)

**Lines:** ~369

---

### Database Clients

#### `backend/app/db/neo4j.py`

**Purpose:** Neo4j Aura async client for security graph operations.

**Key Functions/Exports:**
- `Neo4jClient.connect() / close()` — lifecycle
- `get_security_context(alert_id) -> SecurityContext` — traverses to 47 nodes
- `create_decision_trace(...)` — creates `(:Decision)` + `(:DecisionContext)` nodes
- `create_evolution_event(...)` — creates `(:EvolutionEvent)` + `(:Decision)-[:TRIGGERED_EVOLUTION]->(:EvolutionEvent)`
- `get_alert_details(alert_id)` — fetch alert + asset + user + type
- `get_precedent_decisions(alert_type, limit)` — similar past decisions
- `run_query(query, params)` — generic query execution (used by threat_intel.py, triage.py)

**Key Principle:** All Cypher is fixed — predictable 47-node count, injection-safe

**The Key Relationship:** `(:Decision)-[:TRIGGERED_EVOLUTION]->(:EvolutionEvent)` — what SIEMs don't have

**Tab Support:** Tab 2 (context + evolution), Tab 3 (graph traversal + threat intel)

**Lines:** ~500

---

### Models

#### `backend/app/models/schemas.py`

**Purpose:** Pydantic v2 models for all request/response validation.

**Key Classes:**

*Tab 1:* SOCQueryRequest, MetricContract, MetricDataPoint, Provenance, SprawlAlert

*Tab 2:* ProcessAlertRequest, Deployment, EvalGateCheck, EvalGateResult, TriggeredEvolution, ExecutionStats, PromptEvolution, OperationalImpact

*Tab 3:* AlertSummary, ActionRequest, Receipt, Verification, Evidence, KpiImpact, SituationAnalysis, SituationType, OptionEvaluated, DecisionEconomics, FeedbackRequest, FeedbackResult, PolicyConflictResult

*Tab 4:* WeeklyMetrics, EvolutionEvent, CompoundingResponse, BusinessImpact, ROIRequest, ROIResponse

*Core:* SecurityContext, Decision, EvolutionTrigger

**Lines:** ~190+

---

## Frontend Files

### Core Application

#### `frontend/src/main.tsx`

**Purpose:** React 18 entry point — mounts `<App />` in StrictMode.

**Lines:** ~10

---

#### `frontend/src/App.tsx`

**Purpose:** Root component — 4-tab navigation shell. Defaults to Tab 2 (THE DIFFERENTIATOR). v3.2: header title and subtitle read from `domainConfig`.

**Tab order:** SOC Analytics (1) | Runtime Evolution (2) ★ DEFAULT | Alert Triage (3) | Compounding (4)

**Lines:** ~80

---

### Tab Components

#### `frontend/src/components/tabs/SOCAnalyticsTab.tsx`

**Purpose:** Tab 1 — governed security metrics with natural language queries.

**Key Features:** NL query input, 5 example questions, metric chart (Recharts), metric contract panel, provenance panel, rule sprawl alert ($18K/month waste)

**API Calls:** POST /api/soc/query

**Lines:** ~466

---

#### `frontend/src/components/tabs/RuntimeEvolutionTab.tsx`

**Purpose:** Tab 2 — TRIGGERED_EVOLUTION. THE KEY DIFFERENTIATOR.

**v3.2 Changes:** Parameterized with `domainConfig` (R10) — `triggerEntity`, `loop3BadgeLabel`, `guaranteesLabel` labels imported from `domain.ts`.

**Key Features:**
- Deployment registry table (active v3.1 / canary v3.2)
- Process Alert button (ALERT-7823)
- **Eval Gate panel** — 4 checks, 800ms sequential animation per check
- **TRIGGERED_EVOLUTION panel** (purple) — THE KEY FEATURE
- **BLOCKED banner** — shown when eval gate fails
- **AgentEvolver panel** (Loop 2) — variant bars, promotion status, "What Changed" narrative, 5 operational impact cards

**API Calls:** GET /api/deployments, POST /api/alert/process, POST /api/alert/process-blocked

**Tab Support:** Tab 2 ★

**Lines:** ~777

---

#### `frontend/src/components/tabs/AlertTriageTab.tsx`

**Purpose:** Tab 3 — graph-based alert triage with closed-loop execution, feedback, policy conflict, and decision factors.

**v3.2 Changes:** Parameterized with `domainConfig` (R11) — 7 label replacements including `tabs.decision`, `domainAdjective`, `triggerEntity`, `triggerEntityPlural`. M-3 fix (R12): `timerIdsRef = useRef<...[]>([])` + cleanup `useEffect` for 3 `setTimeout` calls in `executeActionHandler`.

**Key Features:**
- Alert queue sidebar (5 alerts)
- Graph visualization (colored node/edge display)
- **Situation Analyzer panel** — type badge, key factors, options bar chart, decision economics (time/cost/risk)
- **Decision Explainer panel** — 6-factor breakdown with live threat intel enrichment factor
- **Refresh Threat Intel button** — triggers `POST /api/graph/threat-intel/refresh`
- **Policy Conflict panel** (`PolicyConflict` component)
- **Recommendation panel** with confidence
- **Closed Loop Execution** — 4 sequential steps: EXECUTED → VERIFIED → EVIDENCE → KPI IMPACT
- **Outcome Feedback panel** (`OutcomeFeedback` component)

**API Calls:** GET /api/triage/alerts, POST /api/triage/analyze, POST /api/triage/execute, GET /api/triage/decision-factors/{id}, POST /api/graph/threat-intel/refresh

**Tab Support:** Tab 3

**Lines:** ~792 (+ M-3 fix additions)

---

#### `frontend/src/components/tabs/CompoundingTab.tsx`

**Purpose:** Tab 4 — compounding intelligence dashboard proving the moat.

**v3.2 Changes:** Parameterized with `domainConfig` (R9) — `impactLabels.hrsSaved`, `impactLabels.backlog`, `operationsLabel` labels.

**Key Features:**
- `useCountUp` hook — 3-second ease-out counter animation
- **Business Impact Banner** — 4 animated cards (847 analyst hours, $127K/quarter, 75% MTTR, 2,400 backlog)
- **Headline Metrics** — Week 1 vs Week 4 with animated counters
- **Weekly Trend Chart** — Recharts LineChart
- **Two-Loop Hero Diagram** — center Neo4j graph (pulse animation), Loop 1 (blue) + Loop 2 (purple), TRIGGERED_EVOLUTION badge, stats row
- **Evolution Events Timeline**
- **ROI Calculator trigger button**

**API Calls:** GET /api/metrics/compounding?weeks=4, POST /api/demo/reset-all

**Tab Support:** Tab 4

**Lines:** ~730

---

### Shared Components

#### `frontend/src/components/OutcomeFeedback.tsx`

**Purpose:** Post-execution outcome feedback panel — Correct/Incorrect rating with asymmetric confidence update display.

**API Calls:** POST /api/alert/outcome

**Lines:** ~273

---

#### `frontend/src/components/PolicyConflict.tsx`

**Purpose:** Policy conflict detection panel — side-by-side comparison when two policies conflict.

**API Calls:** GET /api/alert/policy-check, GET /api/alert/policy-history

**Lines:** ~258

---

#### `frontend/src/components/ROICalculator.tsx`

**Purpose:** ROI Calculator modal — 6 input sliders, real-time projections ($428K–$5.1M), CFO narrative.

**API Calls:** POST /api/roi/calculate, GET /api/roi/defaults

**Lines:** ~589

---

### API Client and Types

#### `frontend/src/lib/api.ts`

**Purpose:** Typed API client for all backend communication.

**Key Functions:**

*Tab 1:* `queryMetric(query)`

*Tab 2:* `getDeployments()`, `processAlert(alertId, simulateFailure)`, `processAlertBlocked(alertId)`

*Tab 3:* `getAlerts()`, `analyzeAlert(alertId)`, `executeAction(alertId, action)`, `getDecisionFactors(alertId)`, `refreshThreatIntel()`, `recordOutcome(...)`, `getOutcomeStatus(alertId)`, `checkPolicy(alertId)`, `getPolicyHistory(alertId)`

*Tab 4:* `getCompoundingMetrics(weeks)`, `resetAllDemoData()`, `calculateROI(inputs)`, `getROIDefaults()`

*Audit:* `getAuditDecisions(format)`, `verifyAuditChain()`

*Demo:* `getRegisteredDomains()`

**Lines:** ~200

---

#### `frontend/src/lib/domain.ts` ★ NEW v3.2

**Purpose:** Single source of truth for all domain-specific frontend labels and numbers. Components import `domainConfig` instead of hardcoding SOC-specific strings.

**Key Export:**
```typescript
export const domainConfig = {
  name: "soc",
  displayName: "SOC Copilot",
  version: "v3.2",
  triggerEntity: "Alert",
  triggerEntityPlural: "Alerts",
  tabs: { analytics, evolution, decision, compounding },
  metrics: { hrsSavedMonthly, costAvoidedQuarterly, mttrReductionPct, backlogEliminated },
  impactLabels: { hrsSaved, backlog },
  operationsLabel: "security operations",
  domainAdjective: "Security",
  loop3BadgeLabel: "Security-first: penalty 20× reward",
  guaranteesLabel: "security guarantees",
  headerTitle: "SOC Copilot Demo",
  headerSubtitle: "AI-Augmented Security Operations with Runtime Evolution",
} as const
```

**Selective parameterization rule:** Only UI labels that change per domain are extracted here. Architecture terms (TRIGGERED_EVOLUTION, SIEM, eval gate), soundbites, data keys, TypeScript interfaces, and console.log messages are left hardcoded.

**Lines:** ~57

---

#### `frontend/src/types/roi.ts`

**Purpose:** TypeScript interfaces for ROI Calculator request/response shapes.

**Key Types:** `ROIInputs`, `ROISavingsBreakdown`, `ROIResponse`

**Lines:** ~45

---

## Dependency Diagram

### Backend Dependency Flow (v3.2)

```
                         main.py
                    (FastAPI Entry Point)
        Registers: evolution, triage, soc, metrics, roi, audit, graph
                              │
     ┌──────┬─────────┬───────┼───────┬────────┬────────┐
     ▼      ▼         ▼       ▼       ▼        ▼        ▼
evolution triage    soc    metrics  roi     audit ★  graph ★
(Tab 2)  (Tab 3)  (Tab 1) (Tab 4) (ROI)  (Ledger)  (TI)
     │      │                               │         │
     │   ┌──┴──────────────────────────┐    │         │
     │   │                            │    │         │
     ▼   ▼                            │    ▼         ▼
situation.py               feedback  audit.py ★  threat_intel.py ★
(Loop 1)                   policy.py
     │
     ▼
  domains/soc/                  triage.py ★ (Decision Factors)
  situations.py                      │
                                     ▼
policy.py → domains/soc/        domains/soc/
             policies.py         factors.py
     │
     ▼
evolver.py              agent.py        reasoning.py
(Loop 2)            (Decision Engine)   (LLM Narration)
                           │
                    ┌──────┴──────┐
                    ▼             ▼
                neo4j.py      schemas.py
              (Graph Client) (Pydantic Models)

             core/
             ├── state_manager.py  ← reset coordination
             └── domain_registry.py ← domain lookup

             domains/
             ├── base.py           ← DomainConfig ABC
             ├── soc/              ← active domain
             └── supply_chain/     ← S2P stub (not active)

★ = New in v3.0 or v3.2
```

### Frontend Dependency Flow (v3.2)

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
              .tsx              .tsx           .tsx
          └──────────┴──────────┴──────────┘
                              │
                           api.ts
                        (API Client)
                              │
                        ┌─────┴──────┐
                     roi.ts       domain.ts ★
                  (ROI Types)  (Domain Config)

★ = New in v3.2
```

---

## Tab Support Matrix (v3.2)

| File | Tab 1 | Tab 2 | Tab 3 | Tab 4 | Notes |
|------|-------|-------|-------|-------|-------|
| **Backend** |
| `main.py` | ✓ | ✓ | ✓ | ✓ | Entry point |
| `routers/soc.py` | ✓ | — | — | — | NL queries |
| `routers/evolution.py` | — | ✓ | — | — | THE DIFFERENTIATOR ★ |
| `routers/triage.py` | — | — | ✓ | — | + feedback, policy, factors |
| `routers/metrics.py` | — | — | — | ✓ | + /demo/domains (v3.2) |
| `routers/roi.py` | — | — | — | ✓ | ROI Calculator |
| `routers/audit.py` ★ | — | — | — | ✓ | Evidence Ledger (v3.0) |
| `routers/graph.py` ★ | — | — | ✓ | — | Threat Intel refresh (v3.0) |
| `services/agent.py` | — | ✓ | ✓ | — | Rule-based decision |
| `services/reasoning.py` | — | ✓ | ✓ | — | LLM narration |
| `services/situation.py` | — | ✓ | ✓ | — | Loop 1 |
| `services/evolver.py` | — | ✓ | — | — | Loop 2 |
| `services/feedback.py` | — | — | ✓ | — | Outcome feedback |
| `services/policy.py` | — | — | ✓ | — | Policy conflict |
| `services/seed_neo4j.py` | — | ✓ | ✓ | — | Seed data |
| `services/audit.py` ★ | — | — | — | ✓ | SHA-256 ledger (v3.0) |
| `services/threat_intel.py` ★ | — | — | ✓ | — | IOC enrichment (v3.0) |
| `services/triage.py` ★ | — | — | ✓ | — | Decision factors (v3.0) |
| `core/state_manager.py` ★ | — | — | — | ✓ | Reset coord. (v3.2) |
| `core/domain_registry.py` ★ | — | — | — | ✓ | Domain lookup (v3.2) |
| `domains/base.py` ★ | — | — | — | — | Framework ABC (v3.2) |
| `domains/soc/config.py` ★ | — | — | — | — | SOC constants (v3.2) |
| `domains/soc/factors.py` ★ | — | — | ✓ | — | SOC factors (v3.2) |
| `domains/soc/situations.py` ★ | — | ✓ | ✓ | — | SOC situations (v3.2) |
| `domains/soc/policies.py` ★ | — | — | ✓ | — | SOC policies (v3.2) |
| `domains/supply_chain/config.py` ★ | — | — | — | — | S2P stub (v3.2) |
| `db/neo4j.py` | — | ✓ | ✓ | — | Graph operations |
| `models/schemas.py` | ✓ | ✓ | ✓ | ✓ | Validation layer |
| **Frontend** |
| `main.tsx` | ✓ | ✓ | ✓ | ✓ | Entry point |
| `App.tsx` | ✓ | ✓ | ✓ | ✓ | Navigation |
| `tabs/SOCAnalyticsTab.tsx` | ✓ | — | — | — | Tab 1 UI |
| `tabs/RuntimeEvolutionTab.tsx` | — | ✓ | — | — | Tab 2 UI ★ (+ domain params v3.2) |
| `tabs/AlertTriageTab.tsx` | — | — | ✓ | — | Tab 3 UI (+ domain params, M-3 fix v3.2) |
| `tabs/CompoundingTab.tsx` | — | — | — | ✓ | Tab 4 UI (+ domain params v3.2) |
| `components/OutcomeFeedback.tsx` | — | — | ✓ | — | Feedback |
| `components/PolicyConflict.tsx` | — | — | ✓ | — | Policy |
| `components/ROICalculator.tsx` | — | — | — | ✓ | ROI modal |
| `lib/api.ts` | ✓ | ✓ | ✓ | ✓ | API client |
| `lib/domain.ts` ★ | ✓ | ✓ | ✓ | ✓ | Domain config (v3.2) |
| `types/roi.ts` | — | — | — | ✓ | ROI types |

★ = New in v3.0 or v3.2

---

## ACCP Capability Map

The demo is the progressive reference implementation of the **Agentic Cognitive Control Plane (ACCP)** — an architectural pattern for governed, self-improving enterprise AI.

**Current Progress: 12/18 capabilities (67%)**

| # | ACCP Capability | Version | Status | Where |
|---|---|---|---|---|
| 1 | Context graph substrate | v1.0 | ✅ Done | Neo4j schema, neo4j.py |
| 2 | Situation classification (Typed-Intent) | v2.0 | ✅ Done | situation.py → domains/soc/situations.py |
| 3 | Eval gates (structural safety) | v2.0 | ✅ Done | agent.py, evolution.py, Tab 2 |
| 4 | TRIGGERED_EVOLUTION | v2.0 | ✅ Done | neo4j.py → EvolutionEvent, Tab 2 purple panel |
| 5 | Decision economics | v2.0 | ✅ Done | situation.py options, Tab 3 |
| 6 | Loop 1: Situational Mesh | v2.0 | ✅ Done | situation.py, Tab 3 Situation panel |
| 7 | Loop 2: AgentEvolver | v2.0 | ✅ Done | evolver.py, Tab 2 AgentEvolver panel |
| 8 | ROI Calculator | v2.5 | ✅ Done | roi.py, ROICalculator.tsx |
| 9 | Outcome Feedback (completes TRIGGERED_EVOLUTION) | v2.5 | ✅ Done | feedback.py, OutcomeFeedback.tsx |
| 10 | Policy Conflict Resolution | v2.5 | ✅ Done | policy.py, PolicyConflict.tsx |
| 11 | Decision Explainer (factor breakdown) | v3.0 | ✅ Done | services/triage.py, domains/soc/factors.py, Tab 3 |
| 12 | Evidence Ledger (compliance audit trail) | v3.0 | ✅ Done | services/audit.py, routers/audit.py, Tab 4 |
| 13 | External context ingestion (live threat intel) | v3.0 | ✅ Done | services/threat_intel.py, routers/graph.py, Tab 3 |
| 14 | Domain-agnostic architecture | v3.2 | ✅ Done | core/, domains/, domain.ts |
| 15 | Prompt Hub / Smart Queries | v3.5 | Planned | — |
| 16 | Full Situational Mesh (sub-150ms) | v3.5 | Vision | — |
| 17 | Formal Typed-Intent Bus | v4.0 | Vision | — |
| 18 | Second domain copilot (active S2P) | v4.0 | Vision | S2P stub created; needs situations.py, factors.py |

---

## Key Architectural Patterns

### 1. Simple Rule-Based Agent
**File:** `services/agent.py`

Intentionally deterministic (~374 lines). The demo proves the ARCHITECTURE, not agent sophistication. Same input → same output every demo.

### 2. LLM as Narrator Only
**File:** `services/reasoning.py`

Gemini 1.5 Pro generates justification AFTER the decision is made. Hardcoded fallback templates prevent demo breakage without an API key.

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

### 6. SHA-256 Hash Chain (Evidence Ledger)
**File:** `services/audit.py`

Each decision record hashes its immutable fields chained off the previous record's hash. Mutable fields (outcome, analyst_confirmed) are excluded so `verify_chain()` remains valid after analyst feedback.

### 7. Domain-Agnostic Architecture
**Files:** `core/domain_registry.py`, `domains/base.py`, `domains/soc/`, `domains/supply_chain/`

`core/` = framework (knows about `DomainConfig` interface, not about SOC or S2P specifics).
`domains/soc/` = SOC implementation.
`domains/supply_chain/` = S2P stub.
Adding a new domain: create `domains/new_domain/config.py` + register in `domain_registry.py`. Zero changes to `core/`.

### 8. Selective Frontend Parameterization
**File:** `frontend/src/lib/domain.ts`

Only UI labels that change per domain are extracted to `domainConfig`. Architecture terms (TRIGGERED_EVOLUTION, SIEM, eval gate), soundbites, TypeScript interfaces, and data keys remain hardcoded. Prevents over-abstraction while enabling domain switching for demos.

---

## File Size Summary (v3.2)

| Category | Files | Approx Lines |
|----------|-------|-------------|
| **Backend Routers** | 7 | ~2,294 |
| **Backend Services** | 10 | ~3,139 |
| **Backend Core (v3.2)** | 2 | ~89 |
| **Backend Domains (v3.2)** | 6 | ~1,300 |
| **Backend DB** | 1 | ~500 |
| **Backend Models** | 1 | ~190 |
| **Frontend Tabs** | 4 | ~2,765 |
| **Frontend Shared Components** | 3 | ~1,120 |
| **Frontend Core** | 2 | ~90 |
| **Frontend API + Types + Domain** | 3 | ~302 |
| **Total** | **~39** | **~11,789** |

*v3.0 added 5 new files (+834 lines) vs v2.5.*
*v3.2 added 11 new files (+1,820 lines) and modified 8 existing files vs v3.0.*

---

## The Eight Key Files (Core v3.2 Demo)

If you read only 8 files to understand the full v3.2 demo:

1. **`routers/evolution.py`** — Full Tab 2 flow: situation, agent decision, eval gate, TRIGGERED_EVOLUTION, AgentEvolver
2. **`services/situation.py`** — Loop 1: Situation Analyzer with 6 types and decision economics
3. **`services/evolver.py`** — Loop 2: AgentEvolver with variant tracking and operational impact
4. **`services/audit.py`** — Evidence Ledger: SHA-256 hash chain, reconstruct, verify
5. **`services/threat_intel.py`** — Live Threat Intel: Pulsedive → Neo4j `:ThreatIntel` nodes
6. **`domains/base.py`** — DomainConfig ABC: 10 abstract properties + 3 abstract methods
7. **`tabs/RuntimeEvolutionTab.tsx`** — The UI showing both loops, eval gate animation, and operational impact
8. **`tabs/AlertTriageTab.tsx`** — The UI showing situation analysis, decision factors, closed loop, feedback, policy

---

## Ports and Commands

```bash
# Backend (port 8001)
cd backend
uvicorn app.main:app --reload --port 8001

# Frontend (port 5174)
cd frontend
npx vite --port 5174

# Seed Neo4j (required for Tab 3)
python backend/seed_neo4j.py

# View demo
http://localhost:5174

# Smoke test: verify domain registry
curl http://localhost:8001/api/demo/domains

# Smoke test: verify Evidence Ledger
curl http://localhost:8001/api/audit/verify

# Smoke test: refresh threat intel (writes to Neo4j)
curl -X POST http://localhost:8001/api/graph/threat-intel/refresh
```

## Environment Variables

```bash
# Neo4j Aura (required for Tabs 2, 3)
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password

# Vertex AI (optional — reasoning.py has fallback)
VERTEX_AI_LOCATION=us-central1
VERTEX_AI_MODEL=gemini-1.5-pro-002

# Pulsedive (optional — threat_intel.py has hardcoded fallback)
PULSEDIVE_API_KEY=your-key
```

---

## Known Issues (v3.2)

| Issue | Severity | Notes |
|-------|----------|-------|
| In-memory state (feedback, policy, audit, evolver) | Medium | Fine for 10-min demo; fails across server restarts. Fix: persist to Neo4j in v3.5 |
| Floating point display (0.8300000001) | Low | Round to 1 decimal in OutcomeFeedback |
| Policy Conflict doesn't override Recommendation | Design gap | Policy says escalate, Recommendation says auto-close. Presenter narrates override |
| S2P `classify_situation` / `compute_factors` not enforced by ABC | Design debt (RF-2) | These methods exist in service layer, not as abstract methods in `DomainConfig` |
| S2P `metrics_config` docstring lists SOC key names | Documentation debt (RF-1) | No runtime impact — return type is `Dict` |
| S2P POLICY-RISK-003 / POLICY-DUAL-004 priority-1 tie | Design limitation (RF-3) | Winner determined by list position; stable sort is a known policy.py limitation |
| `domain.ts` has 4 speculative unused fields | Low | `name`, `tabs.analytics`, `tabs.evolution`, `tabs.compounding` added for future use; App.tsx tab labels still hardcoded |

---

**Last Updated:** February 25, 2026
**Status:** v3.2 Complete. ACCP 12/14 implemented capabilities (67% of 18 total; 14 implemented if counting domain-agnostic architecture). Next: S2P domain full implementation (situations.py, factors.py, seed_neo4j.py) OR Docker packaging OR v3.5 planning.
**Key Principle:** The demo proves the ARCHITECTURE (two loops → compounding), not agent sophistication.
**v3.2 Focus:** Domain-agnostic architecture — the framework now supports adding a second vertical without changing core code. S2P stub validates the pattern.
