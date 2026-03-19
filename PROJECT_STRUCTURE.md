# SOC Copilot Demo — Project Structure

**Last Updated:** March 14, 2026
**Version:** v5.0.0 (branch: v5.0-dev)
**Architecture:** Three-loop compounding intelligence — Graph-Attention Engine (GAE) + ProfileScorer + Runtime Evolution

---

## Table of Contents

- [Directory Tree](#directory-tree)
- [Backend Files](#backend-files)
  - [Routers](#routers)
  - [Services](#services)
  - [Domains](#domains)
  - [Connectors](#connectors)
  - [Data](#data)
- [Frontend Files](#frontend-files)
  - [Tab Components](#tab-components)
  - [Supporting Components](#supporting-components)
  - [Libraries](#libraries)
- [SOC Domain Configuration](#soc-domain-configuration)
- [GAE Library Imports](#gae-library-imports)
- [Environment & Runtime](#environment--runtime)

---

## Directory Tree

```
gen-ai-roi-demo-v4-v50/
│
├── CLAUDE.md                          # Project rules and commands
├── PROJECT_STRUCTURE.md               # This file
├── docs/
│   ├── PROJECT_STRUCTURE.md           # Docs copy
│   └── soc_copilot_design_v1.md       # SOC copilot design spec
│
├── backend/
│   ├── requirements.txt
│   ├── conftest.py                    # Pytest fixtures
│   ├── seed_neo4j.py                  # Neo4j seed data script
│   └── app/
│       ├── main.py                    # FastAPI entry point (v5.0.0)
│       ├── models/
│       │   └── schemas.py             # Pydantic models (Alert, Decision, etc.)
│       ├── db/
│       │   └── neo4j.py               # Async Neo4j Aura client
│       ├── routers/
│       │   ├── soc.py                 # SOC Analytics + centroid-evolution + learning-state
│       │   ├── evolution.py           # Runtime Evolution (Tab 2)
│       │   ├── triage.py              # Alert Triage + outcome feedback (Tab 3)
│       │   ├── metrics.py             # Compounding Metrics (Tab 4)
│       │   ├── roi.py                 # ROI Calculator
│       │   ├── simulation.py          # Batch GAE simulation (SIM-1)
│       │   ├── audit.py               # Decision audit trail
│       │   ├── evaluation.py          # 36-scenario ground-truth evaluation
│       │   ├── judgment.py            # Human-readable decision judgment
│       │   ├── graph.py               # Graph intelligence + UCL connectors
│       │   ├── gae.py                 # GAE learning state endpoints
│       │   └── admin.py               # Privileged reset operations (TD-026)
│       ├── services/
│       │   ├── agent.py               # SOC Copilot agent (decide())
│       │   ├── evolver.py             # Prompt variant A/B evolver
│       │   ├── event_bus.py           # Lightweight event bus (v4.1)
│       │   ├── audit.py               # SHA-256 hash-chain audit ledger
│       │   ├── feedback.py            # Outcome feedback loop (v2.5)
│       │   ├── gae_state.py           # LearningState singleton manager
│       │   ├── iks.py                 # Institutional Knowledge Score
│       │   ├── snapshots.py           # ProfileSnapshot every 50 decisions
│       │   ├── simulation.py          # SimulationOrchestrator (SIM-1)
│       │   ├── threat_intel.py        # Threat intel service (backward-compat)
│       │   ├── situation.py           # Situation Analyzer (14 types)
│       │   ├── narrative.py           # Investigation narrative (NAR-1)
│       │   ├── policy.py              # Policy conflict resolution (v2.5)
│       │   ├── reasoning.py           # LLM reasoning narration (Vertex AI)
│       │   ├── triage.py              # Decision factor breakdown service
│       │   └── state_manager.py       # Atomic reset coordinator (TD-026)
│       ├── domains/
│       │   ├── base.py                # Abstract domain interface
│       │   └── soc/
│       │       ├── config.py          # SOC constants, centroids, ProfileScorer builder
│       │       ├── factors.py         # 6 FactorComputer implementations
│       │       ├── orchestrator.py    # Factor vector orchestration
│       │       ├── situations.py      # SOC situation types
│       │       └── policies.py        # SOC policy registry
│       ├── connectors/
│       │   ├── base.py                # UCLConnector protocol + ConnectorResult
│       │   ├── registry.py            # ConnectorRegistry singleton
│       │   ├── pulsedive.py           # Pulsedive threat intel connector
│       │   ├── greynoise.py           # GreyNoise IP reputation connector
│       │   ├── crowdstrike_mock.py    # CrowdStrike EDR mock connector
│       │   └── __init__.py
│       ├── core/
│       │   ├── domain_registry.py     # Domain registry pattern
│       │   └── state_manager.py       # State management (core layer)
│       ├── data/
│       │   ├── alert_pool.py          # 20 canonical alerts, 5 categories (SIM-3a)
│       │   ├── iks_bootstrap_soc.json # Bootstrap centroid priors μ₀
│       │   ├── soc_eval_scenarios.json # 36 ground-truth evaluation scenarios
│       │   └── gae_learning_state.json # Runtime W matrix (gitignored)
│       └── scripts/
│           ├── seed_realistic.py
│           ├── verify_realistic_seed.py
│           └── verify_seed_data.py
│
└── frontend/
    ├── index.html
    ├── package.json
    ├── tailwind.config.js             # soc-primary, soc-secondary, soc-bg, soc-card, soc-danger
    ├── vite.config.ts
    └── src/
        ├── main.tsx                   # React entry point
        ├── App.tsx                    # Tab router (4 tabs + vis2:navigate event listener)
        ├── index.css
        ├── types/
        │   └── roi.ts                 # ROIRequest, ROIResponse, ROIDefaults, ROISavings
        ├── lib/
        │   ├── api.ts                 # 43 exported API functions
        │   └── domain.ts              # domainConfig (single source of truth for labels)
        └── components/
            ├── tabs/
            │   ├── SOCAnalyticsTab.tsx      # Tab 1
            │   ├── RuntimeEvolutionTab.tsx  # Tab 2 — THE DIFFERENTIATOR
            │   ├── AlertTriageTab.tsx       # Tab 3
            │   └── CompoundingTab.tsx       # Tab 4
            ├── OutcomeFeedback.tsx          # Loop 3 feedback widget
            ├── PolicyConflict.tsx           # Policy conflict detector
            ├── ROICalculator.tsx            # ROI calculator modal
            └── SimulationPanel.tsx          # SIM-2 batch simulation
```

---

## Backend Files

### Routers

#### `soc.py` — SOC Analytics + VIS-2 endpoints
- `GET /api/soc/query` — natural-language metric query
- `GET /api/soc/threat-landscape` — threat landscape summary
- `GET /api/soc/attack-tactic-breakdown` — MITRE tactic counts
- `GET /api/soc/detection-engineering` — rule quality score + noise map per category
- `GET /api/soc/centroid-evolution?n=200&category=` — flat array of `{decision_number, id, centroid_delta_norm, category, action, correct, verified_at}` ordered by `verified_at` ASC. Returns `[]` if no qualified Decision nodes. Used by Tab-2 Section A/B and Tab-4 Chart A.
- `GET /api/soc/learning-state` — `{frozen, decision_count, last_verified_at, checkpoint_id}`
- `GET /api/soc/graph-stats` — Neo4j traversal stats

#### `evolution.py` — Runtime Evolution (Tab 2)
- `GET /api/deployments` — deployment registry with A/B traffic splits
- `POST /api/alert/process` — run alert through full GAE pipeline; returns `ProcessResult` with eval_gate, decision_trace, gae_scoring, prompt_evolution, triggered_evolution
- `POST /api/eval/simulate-failure` — synthetic failed eval gate
- `GET /api/rl/reward-summary` — Loop 3 RL signal (correct/incorrect counts, cumulative R(t))
- `GET /api/soc/profile` — ProfileScorer state: categories, actions, centroids (6×4×6), counts, decision_count, IKS
- `POST /api/alert/process` creates **DEC-XXXX** Decision nodes (short hex ID, no `factor_vector`)

#### `triage.py` — Alert Triage + Outcome Feedback (Tab 3)
- `GET /api/alerts/queue` — pending alert queue
- `POST /api/alert/analyze` — analyze alert; creates **UUID** Decision node with `factor_vector`; returns `recommendation.decision_id` (UUID)
- `POST /api/action/execute` — execute action; creates **DEC-XXXX** Decision node; returns `evidence.decision_id` (DEC-XXXX)
- `POST /api/alert/outcome` — report outcome; updates the UUID Decision node with `centroid_delta_norm`, `category`, `correct`, `verified_at`; triggers GAE weight update via `gae.learning.WeightUpdate`
- `GET /api/alert/outcome/{alert_id}` — check if feedback already given
- `POST /api/alerts/reset` — reset alert queue
- `GET /api/triage/decision-factors/{alert_id}` — 6-factor breakdown with contribution scores
- `GET /api/soc/profile` — ProfileScorer state (shared route, registered in this router)

**Two Decision node types per alert:**
| Type | ID format | Has factor_vector | Gets centroid update |
|------|-----------|-------------------|----------------------|
| Analyze | UUID (`str(uuid.uuid4())`) | Yes | Yes (via /alert/outcome) |
| Execute | DEC-XXXX (`DEC-{hex[:4].upper()}`) | No | No |

#### `metrics.py` — Compounding Metrics (Tab 4)
- `GET /api/metrics/compounding?weeks=N` — weekly metrics: auto_close_rate, mttr_minutes, fp_rate, pattern_count
- `GET /api/metrics/evolution-events?limit=N` — evolution event log
- `GET /api/metrics/decisions` — recent Decision nodes for audit display

#### `roi.py` — ROI Calculator
- `GET /api/roi/defaults` — default SOC prospect metrics
- `POST /api/roi/calculate` — prospect-specific ROI projections

#### `simulation.py` — Batch GAE Simulation (SIM-1)
- `POST /api/simulation/start` — kick off N-alert simulation
- `GET /api/simulation/progress/{sim_id}` — live step/accuracy stream
- `GET /api/simulation/result/{sim_id}` — full result with learning curves per category
- `GET /api/simulation/experiment-log/{sim_id}` — raw JSON event log

#### `audit.py` — Decision Audit Trail
- `GET /api/audit/decisions?format=json|csv` — full audit trail with SHA-256 hash chain
- `GET /api/audit/verify` — verify chain integrity

#### `evaluation.py` — Ground-Truth Evaluation (EVAL-2-SOC)
- Runs 36 scenarios from `data/soc_eval_scenarios.json` through live ProfileScorer
- Returns accuracy, confusion matrix, per-category breakdown

#### `judgment.py` — Human-Readable Judgment (JUDG-1-SOC)
- `POST /api/judgment` — translates raw ProfileScorer output to `JudgmentResult` with confidence, reasoning, alternative actions

#### `graph.py` — Graph Intelligence + UCL Connectors
- `POST /api/graph/threat-intel/refresh` — refresh all connectors (backward compat)
- `GET /api/graph/connectors` — list connectors + health status
- `POST /api/graph/connectors/refresh-all` — force refresh all
- `GET /api/graph/enrichment/aggregate/{indicator}` — unified enrichment (Pulsedive + GreyNoise + CrowdStrike)
- `GET /api/graph/enrichment/summary` — enrichment for all known indicators
- `GET /api/graph/enrichment/by-alert/{alert_id}` — enrichment via graph traversal

#### `gae.py` — GAE Learning State
- `GET /api/gae/weights` — W matrix + recent updates + convergence status
- `GET /api/gae/history?limit=N` — weight update history
- `GET /api/gae/convergence` — convergence metrics
- `GET /api/gae/confidence-trajectory` — confidence over time
- `GET /api/gae/trust-curve` — asymmetric trust tracking
- `GET /api/gae/before-after` — W matrix before vs. after learning
- `GET /api/gae/weight-evolution` — full W matrix history

#### `admin.py` — Privileged Reset (TD-026)
- `POST /api/admin/reset` — `{mode: "soft"|"hard", confirm: bool}`
  - **soft**: W→priors, clear Decision outcomes, fresh audit hash chain
  - **hard**: soft + delete Decision nodes + re-seed graph

---

### Services

| File | Purpose |
|------|---------|
| `agent.py` | `SOCAgent.decide()` → `DecisionResult(action, confidence, pattern_id, playbook_id)` |
| `evolver.py` | Prompt A/B variant tracking; promotes variants by success rate |
| `event_bus.py` | Event bus: `DecisionMade`, `OutcomeVerified`, `GraphMutated` (frozen dataclasses) |
| `audit.py` | In-memory SHA-256 hash-chain ledger: `record_decision()`, `verify_chain()` |
| `feedback.py` | `process_outcome()`, `get_feedback_status()`, `get_reward_summary()` |
| `gae_state.py` | `LearningState` singleton; `get_profile_scorer()`; persists to `data/gae_learning_state.json` |
| `iks.py` | IKS = 100 × min(mean(‖μ(t)−μ₀‖₂) / D_MAX, 1.0), D_MAX=0.30 |
| `snapshots.py` | `maybe_write_profile_snapshot(decision_count)` — writes to Neo4j every 50 decisions |
| `simulation.py` | `SimulationOrchestrator` — runs full GAE pipeline for N alerts with oracle feedback |
| `threat_intel.py` | Backward-compat wrapper delegating to `PulsediveConnector` |
| `situation.py` | `SituationType` enum (14 types) + `OptionEvaluated` scoring |
| `narrative.py` | `TemplateNarrativeProvider` (deterministic) + `OllamaNarrativeProvider` (with fallback) |
| `policy.py` | `detect_policy_conflicts()`, `get_conflict_history()` — security-first priority resolution |
| `reasoning.py` | `ReasoningNarrator.generate_reasoning()` — Vertex AI / Gemini 1.5-pro narration |
| `triage.py` | `get_decision_factors(alert_id)` — 6-factor matrix with contribution classification |
| `state_manager.py` | `StateManager.soft_reset()` / `.hard_reset()` — atomic multi-system coordinator |

---

### Domains

#### `domains/base.py`
Abstract domain interface: `DomainAction`, `DomainFactor`, `DomainSituationType`, `DomainPolicy`, `PromptVariant`, `DomainConfig` (ABC).

#### `domains/soc/config.py`
Single source of truth for all SOC domain constants. Key exports:
- `SOC_CATEGORIES` (6), `SOC_ACTIONS` (4), `SOC_FACTORS` (6) — see [SOC Domain Configuration](#soc-domain-configuration)
- `SOC_PROFILE_CENTROIDS` — (6, 4, 6) tensor — bootstrap centroid prior μ₀
- `build_profile_scorer()` — returns `ProfileScorer(mu=..., actions=SOC_ACTIONS, categories=SOC_CATEGORIES, kernel=KernelType.L2)`
- Bootstrap params: rounds=10, samples_per_action=5, sigma=0.08, convergence_tol=0.01, seed=42
- Asymmetry: penalty_ratio=20.0, temperature τ=0.1 (V3B validated ECE=0.036)

#### `domains/soc/factors.py`
Six `FactorComputer` implementations (async `.compute(alert, neo4j) → float`):
`TravelMatchFactor`, `AssetCriticalityFactor`, `ThreatIntelEnrichmentFactor`, `PatternHistoryFactor`, `TimeAnomalyFactor`, `DeviceTrustFactor`.

All factor Cypher queries traverse relationships (P10 rule: never read properties directly).

#### `domains/soc/orchestrator.py`
`compute_factor_vector(alert, computers, neo4j)` → calls each FactorComputer, assembles via `gae.factors.assemble_factor_vector()`.

---

### Connectors

UCL (Unified Connector Layer) — standardised external data source interface.

| Connector | Source | Data |
|-----------|--------|------|
| `pulsedive.py` | Pulsedive | Threat intel, indicator scores |
| `greynoise.py` | GreyNoise | IP reputation, noise classification |
| `crowdstrike_mock.py` | CrowdStrike (mock) | EDR status, prevention policy |

`registry.py` — `ConnectorRegistry` singleton: `register()`, `get()`, `refresh_all()`, `health_check_all()`.

---

### Data

| File | Contents |
|------|---------|
| `alert_pool.py` | 20 canonical alerts across 5 categories (SIM-3a canonical pool) |
| `iks_bootstrap_soc.json` | μ₀ — bootstrap centroid priors for IKS baseline |
| `soc_eval_scenarios.json` | 36 ground-truth evaluation scenarios (EVAL-2-SOC) |
| `gae_learning_state.json` | Live W matrix — runtime state, gitignored |

---

## Frontend Files

### Tab Components

#### `SOCAnalyticsTab.tsx` — Tab 1: Governed Security Metrics
- Metric queries, threat landscape bar chart, attack tactic breakdown
- Provenance tracking (data lineage display)
- Cross-source query examples (uses `domainConfig.defaultAlertId`)

#### `RuntimeEvolutionTab.tsx` — Tab 2: THE DIFFERENTIATOR
Key state: `result` (ProcessResult), `centroidEvolution` (CentroidEvolutionEntry[]), `pendingDecisionId`, `profileState`, `profileStateFull` (with IKS).

**Section A — This Decision**
- "Process Alert" button calls `processAlert(DEFAULT_ALERT_ID)` → populates `result`
- When `pendingDecisionId` set (from Tab-3 bridge link via sessionStorage `vis2_pending_decision`):
  - Finds `pendingEntry = centroidEvolution.find(e => e.id === pendingDecisionId)`
  - If found: shows centroid summary card (category, action, ‖Δμ‖, outcome)
  - If not found: shows "Decision was recorded — process a new alert" hint
- When `result` set: shows full eval gate, GAE scoring, centroid delta, decision trace

**Section B — Category Learning Curves**
- `centroidChartData` — rolling 20-window average of ‖Δμ‖ per decision
- `categoryConvergenceRows` — convergence status per SOC_CATEGORY (groups by `e.category`)
- Category filter dropdown (`availableCategories` derived from centroid data)

**Section C — Weight Matrix Evolution**

**Section D — Learning State / Rollback Status**
- Sources from `GET /api/soc/learning-state`

**Subtitle (required by test):** `"Institutional Intelligence Summary — How the system's judgment has evolved"`

**`CentroidEvolutionEntry` interface:**
```ts
interface CentroidEvolutionEntry {
  id: string           // UUID (from Tab-3 outcome) or DEC-XXXX (from Tab-2 processAlert)
  decision_number: number
  centroid_delta_norm: number
  correct: boolean
  category: string     // snake_case, e.g. "credential_access"
  action: string
  verified_at?: string
}
```

**`DEFAULT_ALERT_ID`** = `domainConfig.defaultAlertId` (centralised in domain.ts)

#### `AlertTriageTab.tsx` — Tab 3: Graph-Based Reasoning
- Alert queue sidebar (left panel)
- Alert analysis panel: 6-factor breakdown, threat intel enrichment, policy conflict
- Decision execution → `closedLoop` state
- `OutcomeFeedback` widget rendered when `closedLoop` is set

**`decisionId` prop to `OutcomeFeedback`:**
```ts
decisionId={analysis?.recommendation?.decision_id ?? closedLoop.evidence.decision_id}
```
`analysis.recommendation.decision_id` = UUID (truthy, takes precedence).
`closedLoop.evidence.decision_id` = DEC-XXXX (fallback, never reached in normal flow).

**Bridge link navigation** (in `OutcomeFeedback`):
```ts
sessionStorage.setItem('vis2_pending_decision', decisionId)
window.dispatchEvent(new CustomEvent('vis2:navigate', { detail: { tab: 'evolution' } }))
```
`App.tsx` listens for `vis2:navigate` and switches to the evolution tab.

#### `CompoundingTab.tsx` — Tab 4: The Compounding Moat
- Business Impact Banner (projected metrics from `domainConfig.metrics`)
- GAE Compounding Evidence (4 charts: Weight Evolution, Confidence Trajectory, Before/After, Trust Curve)
- `centroidEvolution: CentroidEvolutionEntry[]` state (flat array, same shape as Tab-2)
- Evidence Ledger with audit hash chain
- Weekly trend chart + Three-Loop Architecture narrative
- Evolution events log
- The Moat Message callout

---

### Supporting Components

#### `OutcomeFeedback.tsx` — Loop 3: Learning from Results
Rendered by `AlertTriageTab` when `closedLoop` is set and `isVisible=true`.

Props: `alertId`, `decisionId` (UUID), `isVisible`.

States:
1. **Initial** — "Confirmed Correct" / "Incorrect — Real Threat" buttons
2. **Submitted** — shows `OutcomeResponse` with graph updates table, centroid update card, next_alerts_override, narrative
3. **Already given** — immutable notice

**Centroid update card** (VIS-2): shown when `result.centroid_update?.centroid_delta_norm > 0`.
Includes bridge link button → navigates to Tab-2 via `vis2:navigate` event.

**Bridge link className:**
```
mt-3 flex items-center gap-2 px-3 py-2 rounded-md
bg-purple-900/40 border border-purple-500/60
text-purple-200 text-sm font-semibold
hover:bg-purple-800/60 cursor-pointer w-fit
```

#### `PolicyConflict.tsx`
`PolicyDefinition`, `PolicyResolution`, `PolicyConflictData`. Shows winning/losing policy with reason.

#### `ROICalculator.tsx`
Prospect input form + live ROI projection. `useCountUp()` hook for animated number display.

#### `SimulationPanel.tsx` — SIM-2 Batch Simulation
Configurable N-alert simulation at speed_ms. Real-time per-category learning curves. Export to JSON/CSV.

---

### Libraries

#### `lib/domain.ts` — `domainConfig` (single source of truth)

| Key | Value |
|-----|-------|
| `name` | `"soc"` |
| `displayName` | `"SOC Copilot"` |
| `triggerEntity` | `"Alert"` |
| `defaultAlertId` | `"ALERT-7823"` |
| `metrics.hrsSavedMonthly` | `847` |
| `metrics.costAvoidedQuarterly` | `127000` |
| `metrics.mttrReductionPct` | `75` |
| `metrics.backlogEliminated` | `2400` |
| `loop3BadgeLabel` | `"Security-first: penalty 20× reward"` |

#### `lib/api.ts` — 43 exported API functions

| Group | Functions |
|-------|-----------|
| SOC Analytics | `queryMetric`, `getThreatLandscape`, `getAttackTacticBreakdown` |
| Runtime Evolution | `getDeployments`, `processAlert`, `processAlertBlocked`, `simulateFailedGate`, `getRewardSummary` |
| Alert Triage | `getAlerts`, `analyzeAlert`, `executeAction`, `resetAlerts`, `getDecisionFactors` |
| Simulation | `startSimulation`, `getSimulationProgress`, `getSimulationResult`, `getSimulationExperimentLog` |
| Compounding | `getCompoundingMetrics`, `getEvolutionEvents`, `resetDemoData`, `resetAllDemoData`, `reseedDemoData`, `getWeightHistory`, `getConfidenceTrajectory`, `getTrustScores` |
| GAE Learning | `getGAEWeights`, `getGAEHistory`, `getGAEConvergence`, `getGAEConfidenceTrajectory`, `getGAETrustCurve`, `getGAEBeforeAfter`, `getGAEWeightEvolution` |
| ROI | `getROIDefaults`, `calculateROI` |
| Outcome Feedback | `getOutcomeStatus`, `reportOutcome` |
| Policy | `checkPolicyConflict` |
| Graph Intel | `refreshThreatIntel`, `getEnrichmentSummary`, `getAlertEnrichment` |
| Audit | `getAuditDecisions`, `verifyAuditChain` |

---

## SOC Domain Configuration

### Categories (6)
| Index | Key | Display |
|-------|-----|---------|
| 0 | `credential_access` | Credential Access |
| 1 | `threat_intel_match` | Threat Intel Match |
| 2 | `lateral_movement` | Lateral Movement |
| 3 | `data_exfiltration` | Data Exfiltration |
| 4 | `insider_threat` | Insider Threat |
| 5 | `cloud_infrastructure` | Cloud Infrastructure |

### Actions (4)
| Index | Key | Agent action(s) |
|-------|-----|----------------|
| 0 | `escalate` | `escalate_incident`, `escalate_tier2` |
| 1 | `investigate` | `enrich_and_wait` |
| 2 | `suppress` | `auto_remediate`, `false_positive_close` |
| 3 | `monitor` | watch for patterns |

### Factors (6)
| Index | Key | Meaning |
|-------|-----|---------|
| 0 | `travel_match` | Active travel vs. login geography |
| 1 | `asset_criticality` | Asset importance score |
| 2 | `threat_intel_enrichment` | Threat feed signal strength |
| 3 | `pattern_history` | Historical behavioral pattern match |
| 4 | `time_anomaly` | Off-hours / anomalous timing |
| 5 | `device_trust` | Device fingerprint trust score |

### ProfileScorer Shape
`μ` tensor shape: **(6 categories × 4 actions × 6 factors)**
- Temperature τ = 0.1 (V3B validated, ECE = 0.036)
- Asymmetry: penalty_ratio = 20.0 (false negative 20× worse than false positive)
- Learning rate: 0.02

---

## GAE Library Imports

The `gae` package is installed via `pip install -e ../../graph-attention-engine`.

```python
from gae.scoring import score_alert, ScoringResult
from gae.learning import LearningState, WeightUpdate, CalibrationProfile
from gae.factors import FactorComputer, assemble_factor_vector
from gae.contracts import SchemaContract, PropertySpec
from gae.store import save_state, load_state
from gae.convergence import get_convergence_metrics
from gae.evaluation import EvaluationScenario, EvaluationReport, run_evaluation
from gae.judgment import compute_judgment
```

**Rule**: No GAE math in copilot code — always delegate to `gae.*` library functions.

---

## Environment & Runtime

### Ports
- Backend: **8000** (uvicorn)
- Frontend: **5174** (vite)

### Commands
```bash
# Backend
cd backend
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npx vite --port 5174

# Seed Neo4j
python backend/seed_neo4j.py
```

### Environment Variables
| Variable | Purpose |
|----------|---------|
| `NEO4J_URI` | Neo4j Aura connection URI |
| `NEO4J_USER` | Neo4j username |
| `NEO4J_PASSWORD` | Neo4j password |
| `PROJECT_ID` | GCP project (Vertex AI) |
| `VERTEX_AI_LOCATION` | Vertex AI region (default: `us-central1`) |

### Branches
- **Working branch:** `v5.0-dev`
- **PR target (main):** `v4.5-dev`

### Key Design Rules (from CLAUDE.md)
- Factor Cypher queries MUST traverse relationships, not read properties (P10)
- Every graph mutation (decision, outcome) MUST emit events
- `f(t)` stored in graph (Decision node), not in-memory cache (R4)
- No GAE math in copilot — use `gae.scoring`, `gae.learning`, `gae.factors`
