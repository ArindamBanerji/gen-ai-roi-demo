# SOC Copilot — Design Document v3

**Date:** February 28 – March 1, 2026
**Version:** 3.0 (v1 + v2 addendum consolidated into single document)
**Status:** v4.1 tagged. v4.5 redesigned ("Make It Real"). Language: "product preview" not "demo."
**Repository:** soc-copilot (proprietary)
**Theme:** "Your tools, our decisions."
**Companion repos:**
- graph-attention-engine (standalone library — Apache 2.0). Design: `gae_design_v7.md`
- ci-platform (production infrastructure — v4.5+). Design: `ci_platform_design_v1.md`
- `design_decisions_v1.md` (rationale for v2 changes)

**Git remotes:**
- SOC copilot: git@github.com:ArindamBanerji/gen-ai-roi-demo.git (v4.0-dev branch)
- GAE library: graph-attention-engine (standalone repo)
- Experiments: git@github.com:ArindamBanerji/cross-graph-experiments.git

> **This document absorbs and supersedes:**
> - `v4_design_document_v7.md` — SOC copilot v4.0 build plan
> - `v4_5_design_v8.md` — INOVA, Docker, VPS
> - `soc_copilot_design_v1.md` — original three-repo design document
> - `soc_copilot_design_v2.md` — v2 addendum (gap-analysis-driven redesign)
>
> GAE-specific content (Tiers 1-5, scoring, learning, events, contracts) now lives in `gae_design_v7.md`.
> Platform-specific content (UCL, agents, event bus, governance) now lives in `ci_platform_design_v1.md`.

> **Changes from v1 → v3:**
> (1) v4.5 scope redesigned: INOVA → v6.0, Docker → v5.5, replaced with Simulation + Narrative + Discovery.
> (2) v5.0 redefined as "GAE as Platform + SOC as Product."
> (3) Phase D eliminated. CalibrationProfile moved to GAE preamble.
> (4) New sections: Simulation Mode (§15), NarrativeProvider (§16), Reset Semantics (§17), ATT&CK Integration (§18), Category Learning Curve (§19), v4.5 Prompt Specifications (§20).
> (5) SOCDomainConfig updated to provide CalibrationProfile + decay classes.
> (6) Language: "product" not "demo" throughout.

---

## 1. Architecture — SOC Copilot in Three-Repo Stack

### 1.1 Dependency Graph

```
graph-attention-engine           ← numpy-only, zero external deps
        ↑
ci-platform                      ← GAE + Neo4j + asyncio (v4.5+)
        ↑
soc-copilot [THIS REPO]          ← GAE + platform + SOC domain expertise
```

SOC copilot is the **top of the stack**. It imports from GAE and (eventually) ci-platform. Neither GAE nor ci-platform ever imports from soc-copilot.

### 1.2 What Lives Here

| Component | Purpose | Examples |
|---|---|---|
| **Domain factors** | SOC-specific FactorComputer implementations | TravelMatch, PatternHistory, ThreatIntel |
| **Domain config** | SOCDomainConfig — actions, initial W, temperature | `domains/soc/config.py` |
| **Situation classification** | Scoring-based alert classification | `domains/soc/situations.py` |
| **Seed data** | SOC-specific Neo4j seed parameters | `domains/soc/seed_data/` |
| **Factor orchestrator** | Async Neo4j → FactorComputer → GAE assembly | `domains/soc/orchestrator.py` |
| **Connectors** | Pulsedive, GreyNoise, Health-ISAC, CISA KEV | `connectors/` |
| **Frontend** | React UI (all tabs) | `frontend/` |
| **Routers** | FastAPI endpoints | `routers/` |
| **Deployment** | Docker, VPS, cloud | `deployment/` |
| **Event bus (v4.1)** | Lightweight bus (until ci-platform exists) | `services/event_bus.py` |

### 1.3 What Does NOT Live Here

| Component | Lives In | Why |
|---|---|---|
| Scoring matrix (Eq. 4) | graph-attention-engine | Pure math, domain-agnostic |
| Weight learning (Eq. 4b, 4c) | graph-attention-engine | Pure math |
| FactorComputer Protocol | graph-attention-engine | Abstract interface |
| Event TYPE definitions | graph-attention-engine | Pure dataclasses |
| SchemaContract, EmbeddingContract | graph-attention-engine | Demand-side declarations |
| CalibrationProfile | graph-attention-engine | Domain-configurable, not domain-specific |
| Production event bus | ci-platform (v4.5+) | Infrastructure |
| Entity resolution (INOVA) | ci-platform (v6.0) | Domain-agnostic |
| DomainOntology, SchemaValidator | ci-platform (v6.0+) | Governance |

---

## 2. Directory Structure

```
soc-copilot/
├── backend/
│   └── app/
│       ├── domains/
│       │   └── soc/
│       │       ├── __init__.py
│       │       ├── config.py               # SOCDomainConfig: actions, W, τ, CalibrationProfile
│       │       ├── factors.py              # 6 FactorComputer implementations
│       │       ├── orchestrator.py         # async Neo4j → compute → GAE assemble
│       │       ├── situations.py           # Scoring-based classification (v5.0)
│       │       ├── alerts/                 # Alert pool definitions (v4.5 SIM-3a)
│       │       └── seed_data/
│       │           ├── users.json
│       │           ├── assets.json
│       │           ├── threat_intel.json
│       │           └── travel_records.json
│       ├── connectors/
│       │   ├── pulsedive.py
│       │   ├── greynoise.py
│       │   ├── health_isac.py
│       │   └── cisa_kev.py
│       ├── routers/
│       │   ├── triage.py                   # POST /api/analyze → GAE scoring
│       │   ├── feedback.py                 # POST /api/feedback → GAE learning
│       │   ├── gae.py                      # GET /api/gae/weights, /convergence
│       │   ├── simulation.py              # POST /api/simulation/run (v4.5)
│       │   ├── admin.py                   # POST /api/admin/reset (v4.5)
│       │   ├── dashboard.py               # GET /api/dashboard/roi (v5.0)
│       │   └── evaluation.py              # Evaluation runner (v5.0)
│       ├── services/
│       │   ├── event_bus.py               # Lightweight bus (v4.1 — replaced by platform at v4.5)
│       │   ├── feedback.py                # Outcome recording + trust gate
│       │   ├── simulation.py              # SimulationOrchestrator (v4.5)
│       │   ├── narrative.py               # NarrativeProvider protocol (v4.5)
│       │   ├── state_manager.py           # Atomic soft/hard reset (v4.5)
│       │   ├── embedding.py               # EmbeddingProvider implementations (v4.5 Phase C)
│       │   ├── discovery.py               # Cross-graph discovery (v4.5 Phase C)
│       │   └── neo4j_client.py
│       ├── db/
│       │   ├── neo4j.py                   # Connection + query helpers
│       │   └── seed_neo4j.py              # Seed graph from domain seed_data
│       ├── config.py                       # Global config, GAE init
│       └── main.py                         # FastAPI app + startup hooks
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── TriageTab.tsx
│       │   ├── CompoundingTab.tsx          # Real convergence curves (GAE-3b)
│       │   ├── GraphTab.tsx
│       │   ├── SimulationPanel.tsx         # Simulation controls + category learning curve (v4.5)
│       │   └── DashboardTab.tsx            # ROI metrics (v5.0)
│       └── ...
├── deployment/
│   ├── docker/
│   │   ├── docker-compose.yml
│   │   ├── Dockerfile.backend
│   │   └── PARTNER_README.md
│   └── vps/
│       ├── setup.sh
│       └── cron/
├── tests/
│   ├── test_factors.py                    # Tests need Neo4j (integration)
│   ├── test_triage.py
│   ├── test_feedback.py
│   └── test_simulation.py                # Simulation pipeline tests (v4.5)
├── pyproject.toml                          # depends on: graph-attention-engine
└── README.md
```

### 2.1 Development Bridge

```bash
# During v4.1 development (before PyPI release):
cd soc-copilot
pip install -e ../graph-attention-engine
# pip install -e ../ci-platform            # when it exists (v4.5+)
```

---

## 3. Imports from GAE

```python
# What SOC copilot imports from graph-attention-engine:
from gae.scoring import score_alert, ScoringResult
from gae.learning import LearningState, WeightUpdate, PendingValidation
from gae.factors import FactorComputer, assemble_factor_vector
from gae.contracts import SchemaContract, EmbeddingContract, PropertySpec
from gae.events import DecisionMade, OutcomeVerified, GraphMutated
from gae.store import save_learning_state, load_learning_state
from gae.convergence import get_convergence_metrics
from gae.calibration import CalibrationProfile, soc_calibration_profile  # v4.5+
```

---

## 4. Completed Work

### 4.1 Phase 1: Connectors (Sessions 0-4, 13 prompts) ✅

UCL connectors, Pulsedive/GreyNoise enrichment, alert generation, Neo4j graph schema, basic triage flow.

### 4.2 Phase 5: UI (Sessions 5-6, 8 prompts) ✅

React frontend with 4 tabs (Triage, Graph, Compounding, Dashboard). Tab navigation, alert list, graph visualization.

### 4.3 Phase 3: Live Graph — ABSORBED into GAE Sprint

| Original | Absorbed Into | How |
|---|---|---|
| LG1 (feedback writes) | GAE-3a | Outcome write-back to Decision node |
| LG2 (feedback reads) | GAE-3a | f(t) retrieved from Decision node (R4) |
| LG3-R (Decision nodes) | GAE-2d | Decision node written after scoring |
| LG4-R (Trust persistence) | GAE-1c | Trust in LearningState, persisted by store.py |

**Zero remaining Phase 3 prompts.**

---

## 5. SOC Factor Implementations

Six FactorComputers, each implementing the GAE `FactorComputer` Protocol. Each has a Cypher query traversing at least one relationship (design principle P10) and a declared SchemaContract.

### 5.1 Factor Summary

| Factor | Cypher Pattern | Channels | Decay Class |
|---|---|---|---|
| TravelMatch | `(u:User)-[:HAS_TRAVEL]->(t:TravelRecord)` | C, D | campaign |
| AssetCriticality | `(a:Asset)-[:STORES]->(d:DataClass)` | C, D | permanent |
| ThreatIntelEnrichment | `(ti:ThreatIntel)-[:ASSOCIATED_WITH]->(a:Alert)` | C, D | campaign |
| PatternHistory | `(d:Decision)-[:DECIDED_ON]->(a:Alert)` | A, B | standard |
| TimeAnomaly | `(u:User)-[:ACTIVE_AT]->(ts:TimeSlot)` | C | standard |
| DeviceTrust | `(d:Device {id: $device})` | C | standard |

**Tech debt:** TimeAnomaly and DeviceTrust currently read alert properties in the v3.2 codebase. The v4.1 GAE-2c prompt must rewrite them to traverse relationships (`[:ACTIVE_AT]`, `[:USES_DEVICE]`). This is documented in the SHORTCUT-AUDIT (§9.1 of v1, now TD-014/TD-015).

### 5.2 PatternHistory — The Compounding Proof Factor

```python
class PatternHistoryFactor(FactorComputer):
    """
    THIS IS THE COMPOUNDING PROOF FACTOR.
    First alert: returns 0.5 (no history).
    After 5 correct decisions on same type: returns ~1.0.

    Cypher: MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)
            WHERE a.situation_type = $type AND d.outcome IS NOT NULL
    Score: correct / total (base rate). Minimum 5 decisions for non-default.
    Channels: A (Decision nodes), B (outcome markings)
    """
    name = "pattern_history"
```

This factor proves compounding: its output changes BECAUSE previous decisions accumulated in the graph. No other code path can produce this effect.

### 5.3 Factor Orchestrator

```python
# domains/soc/orchestrator.py
from gae.factors import assemble_factor_vector

async def compute_factor_vector(alert, computers, neo4j):
    """Async orchestrator. Calls each FactorComputer, then delegates to GAE."""
    values, names = [], []
    for computer in computers:
        raw = await computer.compute(alert, neo4j)
        values.append(raw)
        names.append(computer.name)
    return assemble_factor_vector(values, names)  # ← GAE function (synchronous, numpy)
```

### 5.4 Accumulation Channels

| Channel | What Accumulates | Who Benefits | Wired In |
|---|---|---|---|
| A: Decision | Decision nodes written to graph with f(t), action, confidence | PatternHistoryFactor (base rates) | GAE-2d |
| B: Outcome | Decision nodes marked correct/incorrect | PatternHistoryFactor (accuracy), W matrix | GAE-3a |
| C: Entity Ingestion | New TI campaigns, users, assets, devices with relationships | ThreatIntelEnrichment, TravelMatch, DeviceTrust | Seed + future ingestion |
| D: Relationship Enrichment | New edges ([:CALIBRATED_BY], analyst links) between existing entities | Any factor with relationship-traversing queries | v5.5 discoveries |
| E: Structural Expansion | New scoring dimensions → W expands (4×6) → (4×7) | All factors, all scoring | v5.5 meta loop |

---

## 6. Decision & Outcome Write-Back Specifications

These graph mutations make Channels A and B work. They run in the **copilot**, not in GAE.

### 6.1 Decision Write-Back (Channel A — GAE-2d)

```python
async def write_decision_to_graph(alert_id, result, f, neo4j):
    query = """
    MATCH (a:Alert {id: $alert_id})
    CREATE (d:Decision {
        id: randomUUID(),
        action: $action,
        confidence: $confidence,
        factor_vector: $factor_vector,   // f(t) — MUST be stored per R4
        W_snapshot: $W_snapshot,
        timestamp: datetime()
    })
    CREATE (d)-[:DECIDED_ON]->(a)
    RETURN d.id AS decision_id
    """
    result = await neo4j.execute_write(query, ...)
    return result["decision_id"]
```

### 6.2 Outcome Write-Back (Channel B — GAE-3a)

```python
async def mark_decision_outcome(decision_id, outcome, neo4j):
    query = """
    MATCH (d:Decision {id: $decision_id})
    SET d.outcome = $outcome,           // +1 or -1
        d.correct = ($outcome = 1),
        d.verified_at = datetime()
    RETURN d.action AS action
    """
    await neo4j.execute_write(query, ...)
```

### 6.3 Event Emission Pattern

```
After decision:  emit DecisionMade → emit GraphMutated(type="decision")
After outcome:   emit OutcomeVerified → emit GraphMutated(type="outcome")
```

Four events per decision-outcome cycle. The event types come from GAE; the bus is a lightweight copilot-local implementation until ci-platform provides the production bus.

---

## 7. v4.1 SOC Copilot Prompts (6 prompts — soc-copilot repo) ✅

> GAE repo prompts (GAE-0 through GAE-2a-protocol, 7 prompts) are in `gae_design_v7.md`.
> These SOC prompts BEGIN after GAE-2a-protocol is complete.

### 7.1 SOC Prompt Sequence

| Prompt | Scope | Creates/Modifies | Test |
|---|---|---|---|
| GAE-2a-soc | TravelMatch + AssetCriticality + orchestrator + seed | `domains/soc/factors.py`, `orchestrator.py`, `seed_neo4j.py` | Queries traverse relationships. Factor values ∈ [0,1]. |
| GAE-2b | ThreatIntelEnrichment + PatternHistory + seed | `domains/soc/factors.py`, `seed_neo4j.py` | PatternHistory returns 0.5 with <5 decisions. |
| GAE-2c | TimeAnomaly + DeviceTrust (rewrite to use relationships) | `domains/soc/factors.py`, `seed_neo4j.py` | **Must traverse [:ACTIVE_AT], [:USES_DEVICE].** |
| GAE-2d | Wire router + Decision write-back + events | `routers/triage.py`, `config.py`, `services/event_bus.py` | Decision node EXISTS after analyze. f(t) stored. Events emitted. |
| GAE-3a | Feedback → Eq. 4b + outcome write-back + trust gate | `services/feedback.py`, `routers/feedback.py` | f(t) from GRAPH (R4). Decision marked. Re-analyze → scores differ. |
| GAE-3b | Compounding dashboard — real data | `CompoundingTab.tsx`, `routers/gae.py` | Empty on first load. Real curves after 5 decisions. |

### 7.2 Additional Copilot-Level Prompt

| Prompt | Scope | Creates/Modifies | Test |
|---|---|---|---|
| GAE-3c | Convergence monitoring + failure modes | `routers/gae.py` | Alternating outcomes → instability warning. |

**Post-sprint gate:** 10-cycle compounding verification (§8). If it passes → TAG v4.1. ✅

---

## 8. End-to-End Compounding Verification (Post-Sprint Gate) ✅

```
SETUP: Fresh graph seed. Learning state reset to priors.

CYCLE 1 — BASELINE:
  Analyze ALERT-7823 (travel). Record factors_1, scores_1, confidence_1.
  Verify: Decision node in Neo4j with f(t). PatternHistory = 0.5.

CYCLE 2 — FIRST FEEDBACK:
  Submit correct. Verify: f(t) from graph (R4). W changed. 
  Decision marked correct. GraphMutated emitted.

CYCLE 3 — ACCUMULATION:
  Analyze ALERT-7824 (travel, different user).
  Verify: PatternHistory finds 1 resolved decision. scores_3 ≠ scores_1.

CYCLES 4-8: Correct outcomes for travel alerts.

CYCLE 9 — COMPOUNDING VISIBLE:
  PatternHistory ~1.0. Confidence >> Cycle 1. Tab 4 real curves.

CYCLE 10 — TRUST ASYMMETRY:
  Incorrect outcome. ~20x update. Trust drops. Action changes.
```

**If this passes, the system compounds. If any step fails, a causal link is broken.** ✅ Passed at v4.1 tag.

---

## 9. v4.5 Scope — "Make It Real"

### 9.0 Guiding Principle

v4.5 closes the credibility gaps between published blog claims and live product proof. Three phases, each gated. No INOVA. No Docker. No VPS. Every prompt produces measurable progress toward a product preview that withstands technical scrutiny.

### 9.1 v4.5 Structure

```
GAE Preamble (2-3 prompts, GAE repo)  ← CalibrationProfile + per-factor decay
        ↓
Phase A: Simulation Mode (6 prompts)   ← "After ten thousand decisions" proof
        ↓
Phase B: CISO Readability (4 prompts)  ← Investigation narrative + Tab 2 rewire
        ↓ [Loom v2 recording]
Phase C: Cross-Graph Discovery (6 prompts, HARD GATED)  ← Axis 3 proof
```

**Phase D from v1 (Docker/VPS/CalibrationProfile) is eliminated.**
- CalibrationProfile moves to GAE preamble
- Docker/VPS deferred to v5.5
- This keeps v4.5 focused on product capability, not distribution

### 9.2 GAE Preamble (GAE Repo — 2-3 prompts)

See `gae_design_v7.md` §23 for full prompt specs (GAE-CAL-1, GAE-CAL-2, optionally GAE-CAL-3).

**Why this comes first:** Phase A's simulation mode exercises the learning loop 50+ times. CalibrationProfile and per-factor decay must be in place before simulation makes them visible. Running 50 decisions through uniform decay and then changing decay semantics forces re-validation.

**SOC copilot impact after GAE preamble:**
- `domains/soc/config.py`: SOCDomainConfig.get_calibration_profile() returns soc_calibration_profile()
- `services/gae_state.py`: LearningState constructed with profile from DomainConfig
- `routers/triage.py`: score_alert() passes profile (or just temperature — backward compatible)

### 9.3 Phase A: Simulation Mode + Alert Corpus (6 prompts)

**Gap closed:** GAP-1 (no simulation mode), GAP-2 (no ATT&CK), GAP-3 (limited alert corpus)

| Prompt | Scope | Creates/Modifies | Gate |
|---|---|---|---|
| **SIM-FIX** | TD-026 fix — atomic reset | `services/state_manager.py`, audit store | Soft reset: GAE + audit + Neo4j outcomes clear atomically. |
| **SIM-1** | SimulationOrchestrator backend | `services/simulation.py`, `routers/simulation.py` | 10-decision API test passes |
| **SIM-2** | Frontend simulation panel | `SimulationPanel.tsx` or integration in existing tab | Real-time chart updates during simulation. Category learning curve chart. |
| **SIM-3a** | Alert pool expansion — 15-20 alerts | `domains/soc/alerts/`, seed data expansion | 5 categories × 3-4 alerts each. Each category activates different dominant factors. |
| **SIM-3b** | Alert pool wiring — orchestrator uses expanded pool | `services/simulation.py`, `routers/simulation.py` | Simulation runs across all categories. PatternHistory differentiates by category. |
| **SIM-4** | ATT&CK technique IDs on all alerts | Alert definitions, Tab 3, Tab 1 | T1078, T1566.001, T1021.001, T1567, T1048 visible. |

**Phase A Gate:** Run 50-decision simulation → clear learning visible in charts. Category learning curve shows per-category accuracy divergence. Weight evolution chart shows meaningful progression. Record 60-second screen capture.

### 9.4 Phase B: CISO Readability (4 prompts)

**Gap closed:** GAP-4 (no investigation narrative), TD-019 (dual decision paths), TD-020 (execute_action events)

| Prompt | Scope | Creates/Modifies | Gate |
|---|---|---|---|
| **NAR-1** | NarrativeProvider protocol + implementations | `services/narrative.py` | Template narrative generates for any alert. Ollama narrative generates if available. |
| **NAR-2** | Tab 3 narrative panel | Frontend, `routers/triage.py` | 3-5 sentence narrative with "calibrated from N outcomes" line. Graceful degradation if no LLM. |
| **TAB2-1** | Rewire Tab 2 Runtime Evolution to GAE pipeline | `routers/evolution.py`, frontend | Tab 2 shows real GAE weight changes. No more parallel decision paths. Closes TD-019. |
| **TAB2-2** | AgentEvolver shows real GAE data | `services/evolver.py`, frontend | execute_action events fire. Closes TD-020. |

**Phase B Gate:** Tab 2 uses GAE end-to-end. Investigation narrative appears with calibration line. Loom v2 recording of full product walkthrough on local machine.

### 9.5 Phase C: Cross-Graph Discovery (6 prompts, HARD GATED)

**Gap addressed:** GAP-5 (no cross-graph discovery / Axis 3)

| Prompt | Scope | Creates/Modifies | Gate |
|---|---|---|---|
| **DISC-1** | EmbeddingProvider implementations in SOC context | `services/embedding.py`, SOC property extraction | PropertyEmbeddingProvider produces embeddings from SOC entities. |
| **DISC-2** | Cross-graph attention sweep | `services/discovery.py` | Discovery sweep runs. Candidates extracted with logit scores. |
| **DISC-3** | Discovery → expand_weight_matrix integration | `services/discovery.py`, `services/gae_state.py` | Validated discovery triggers W expansion. New factor registered. |
| **DISC-4** | Scenario seed data (Singapore + CFO + threat spike) | Seed data expansion | 5 planted discovery patterns across alert categories. |
| **DISC-5** | Tab 4 discovery panel | Frontend | Show discovered relationship, confidence shift, provenance. |
| **GATE-B3** | Embedding quality gate | Test script | F1 > 0.2 against planted patterns in DISC-4 data. |

**HARD GATE at GATE-B3:**
- **Pass (F1 ≥ 0.2):** Discovery is real. Ship it. Update blogs with Axis 3 proof.
- **Fail (F1 < 0.2):** Document honestly: "mathematically validated in controlled experiments (F1=0.293 on clean data), production embedding quality requires further research." Do NOT claim Axis 3 in outreach. Do NOT disable the UI — show it with an honest quality annotation.

**B3 threshold rationale:** 0.2 is strict enough to demonstrate meaningful signal (well above random), achievable based on 0.293 in controlled experiments, and low enough that some quality degradation from realistic data doesn't automatically fail us. Revisited holistically at v5.5 with downstream accuracy impact as additional criterion.

### 9.6 v4.5 Prompt Totals

| Phase | SOC Prompts | GAE Prompts | Total |
|---|---|---|---|
| GAE Preamble | 0 | 2-3 | 2-3 |
| Phase A (Simulation) | 6 | 0 | 6 |
| Phase B (Narrative) | 4 | 0 | 4 |
| Phase C (Discovery) | 6 | 0 | 6 |
| **v4.5 Total** | **16** | **2-3** | **18-19** |

Down from v1's 30 prompts. The reduction comes from removing INOVA (14 prompts), Docker (5 prompts), VPS (4 prompts), Flash Tier (4 prompts), and Polish (3 prompts) — and adding simulation (6), narrative (4), and discovery (6).

---

## 10. v5.0 SOC Copilot Scope — "Product Polish"

### 10.1 v5.0 Context

v5.0 is "GAE as Platform + SOC as Product." The SOC copilot's v5.0 work focuses on making the product withstand technical scrutiny: realistic data, ground truth evaluation, ROI quantification, and confirmation bias mitigation.

### 10.2 v5.0 SOC Prompts

| Prompt | Scope | Creates/Modifies | Depends On |
|---|---|---|---|
| **SEED-2** | Realistic seed data (200+ users, power-law alerts, noise) | `seed_realistic.py`, graph expansion | Phase A complete |
| **EVAL-1-SOC** | 30-40 evaluation scenarios from ATT&CK × graph context | `domains/soc/evaluation_scenarios.json` | SEED-2 (scenarios reference realistic data) |
| **EVAL-2-SOC** | Run evaluation + produce report | `services/evaluation.py`, `routers/evaluation.py` | GAE-EVAL-1 (evaluation framework), EVAL-1-SOC |
| **ECON-1** | ROI dashboard ($/time/risk metrics) | `routers/dashboard.py`, Tab 4 expansion | Phase A (needs decision history for metrics) |
| **JUDG-1-SOC** | Institutional judgment display | `services/judgment.py`, Tab 4 expansion | GAE-JUDG-1, EVAL-2-SOC |
| **A1-FIX** | Tune discount_strength from evaluation results | `domains/soc/config.py` (CalibrationProfile update) | EVAL-2-SOC (need before/after comparison) |
| **SIT-1** | Scoring-based situation classification (GAE-4a/4b) | `domains/soc/situations.py` | GAE preamble (CalibrationProfile) |
| **SIT-2** | Classification learning from analyst corrections | Frontend, `routers/triage.py` | SIT-1 |

**v5.0 SOC Total: 8 prompts.**

### 10.3 v5.0 Dependencies on Other Repos

| SOC Prompt | Requires from GAE | Requires from ci-platform |
|---|---|---|
| EVAL-1-SOC | gae/evaluation.py (EvaluationScenario format) | — |
| EVAL-2-SOC | gae/evaluation.py (run_evaluation, EvaluationReport) | — |
| JUDG-1-SOC | gae/judgment.py (InstitutionalJudgmentMetrics) | — |
| A1-FIX | CalibrationProfile.discount_strength | — |
| SIT-1, SIT-2 | gae/scoring.py (CalibrationProfile-aware) | — |
| SEED-2 | — | DomainSchemaSpec (validates seed against schema) |

### 10.4 What Moved Out of v5.0

| Item | Was v5.0 in v1 | Now | Reason |
|---|---|---|---|
| Splunk ingest | v5.0 | v6.0 | Customer deployment concern, not product capability |
| SAML auth | v5.0 | v6.0 | Same |
| PII redaction | v5.0 | v6.0 | Same |
| Cloud deployment | v5.0 | v6.0 | Same |
| ATT&CK heatmap | v5.0 | v4.5 (SIM-4 for IDs, v5.5+ for heatmap) | ATT&CK IDs are table stakes, pulled earlier |
| Shift handoff | v5.0 | v6.0 | Customer workflow, not core capability |

---

## 11. Product Flow

### 11.1 Before GAE (v3.2 — historical)

```
Alert → hardcoded factors → if-else scoring → template narrative
  → human clicks approve → trust counter ±delta → counter chart
```

### 11.2 After GAE v4.1 (current)

```
Alert → graph traversal computes 6 factors from Neo4j (Connector 1)
  → GAE Eq. 4: f · Wᵀ / τ → softmax → action probabilities (Connector 2)
  → Decision node written to graph with f(t) (R4) ← CHANNEL A
  → Events emitted
  → Human reviews, decides, gives feedback
  → f(t) retrieved from graph (R4)
  → GAE Eq. 4b: W update with 20:1 asymmetry + per-factor decay (Connector 3)
  → Decision node marked correct/incorrect ← CHANNEL B
  → Events emitted
  → Tab 4 shows REAL convergence from accumulated decisions
  → NEXT CYCLE: richer graph → different factors → different decision
```

### 11.3 After v4.5: Simulation + Narrative + Discovery

```
  NEW: "Run 50 Decisions" button → SimulationOrchestrator
    → Batch: same GAE pipeline × 50, Bernoulli oracle outcomes
    → Charts update in real-time (polling)
    → Category learning curve shows per-category accuracy divergence
    → Weight evolution shows meaningful progression
    → Summary: "50 decisions processed. Accuracy: 68% → 87%. Strongest: travel_anomaly."

  NEW: Investigation narrative on Tab 3
    → NarrativeProvider (Ollama/Qwen default, template fallback)
    → "ALERT-7823: TRAVEL_ANOMALY (T1078). travel_match (0.82) and device_trust (0.91)
       are dominant factors. Recommendation: suppress at 91% confidence.
       Calibrated from 12 verified outcomes on similar alerts."

  NEW: ATT&CK technique IDs visible
    → Tab 3: T1078 (Valid Accounts) with tactic label
    → Tab 1: alerts grouped by ATT&CK tactic

  NEW: Discovery panel on Tab 4 (if Phase C gate passes)
    → "Discovered: User jsmith role change (→CFO) correlates with
       active Singapore credential campaign (SG-CRED-2026).
       Confidence shift: 89% → 34%. New scoring dimension added."
```

### 11.4 After v5.0: Evaluated Product

```
  NEW: Realistic data (200+ users, noise, missing properties)
  NEW: Evaluation results: "89% action accuracy, 84% factor accuracy
       across 35 ground-truth scenarios. Strongest: travel_anomaly (94%).
       Weakest: credential_access (76%). Learning delta: +21%."
  NEW: ROI dashboard: "47 analyst hours saved this month.
       Auto-triage rate: 73%. MTTR: 12.4min → 3.1min."
  NEW: Institutional Judgment Score: 47/100 (after 200 decisions)
  NEW: Ablation comparison: "Full system 89%. Without learning: 68%.
       Without graph context: 61%. The difference is institutional judgment."
  NEW: Confirmation bias measured and mitigated (discount_strength tuned)
```

**The UI barely changes. What changes is everything behind it.**

---

## 12. Build Sequence

```
COMPLETED:
  Phases 1-5: (21 prompts) ✅ (pre-GAE work)
  v4.1 GAE Foundation: (13 prompts across 2 repos) ✅
    GAE repo: 7 prompts (GAE-0 through GAE-2a-protocol)
    SOC repo: 6 prompts (GAE-2a-soc through GAE-3c)
  POST-SPRINT GATE: 10-cycle compounding verification ✅
  TAG: v4.1 ✅

v4.5 "MAKE IT REAL":
  GAE Preamble: (2-3 prompts, GAE repo)
    GAE-CAL-1: CalibrationProfile + LearningState refactor
    GAE-CAL-2: Per-factor decay + decay class mapping
    [GAE-CAL-3: Domain schema format — may defer to v5.0]
  
  Phase A — Simulation Mode: (6 prompts, SOC repo)
    SIM-FIX: TD-026 atomic reset
    SIM-1: SimulationOrchestrator backend
    SIM-2: Frontend simulation panel + category learning curve
    SIM-3a: Alert pool expansion (15-20 alerts, 5 categories)
    SIM-3b: Alert pool wiring + orchestrator integration
    SIM-4: ATT&CK technique IDs
    GATE: 50-decision simulation → clear learning in charts
  
  Phase B — CISO Readability: (4 prompts, SOC repo)
    NAR-1: NarrativeProvider protocol + implementations
    NAR-2: Tab 3 narrative panel
    TAB2-1: Rewire Tab 2 to GAE (close TD-019)
    TAB2-2: AgentEvolver shows GAE data (close TD-020)
    GATE: Tab 2 GAE end-to-end. Narrative with calibration line.
    LOOM V2: Record product walkthrough on local machine.
  
  Phase C — Cross-Graph Discovery: (6 prompts, SOC repo, HARD GATED)
    DISC-1: EmbeddingProvider implementations
    DISC-2: Cross-graph attention sweep
    DISC-3: Discovery → expand_weight_matrix
    DISC-4: Scenario seed data (5 planted patterns)
    DISC-5: Tab 4 discovery panel
    GATE-B3: F1 > 0.2 against planted patterns
    IF PASS: Update blogs with Axis 3 proof
    IF FAIL: Document honestly. No Axis 3 claims.
  
  TAG: v4.5

v5.0 "GAE AS PLATFORM + SOC AS PRODUCT":
  GAE repo: 7 prompts (GAE-EVAL-1, GAE-JUDG-1, GAE-ABL-1, GAE-ENG-1/2/3, GAE-DOC-1)
  ci-platform repo: 3-5 prompts (extraction + schema + ContractChecker)
  SOC repo: 8 prompts (SEED-2, EVAL-1/2-SOC, ECON-1, JUDG-1-SOC, A1-FIX, SIT-1/2)
  TAG: v5.0

v5.5: Docker + VPS + schema drift detection + production event bus
v6.0: Customer POC (Splunk, SAML, PII, INOVA, agent pipeline)
```

**Prompt totals:**

| Version | SOC Prompts | GAE Prompts | Platform Prompts | Total |
|---|---|---|---|---|
| Phase 1-5 (pre-GAE) | 21 | 0 | 0 | 21 ✅ |
| v4.1 GAE Foundation | 6 | 7 | 0 | 13 ✅ |
| v4.5 Make It Real | 16 | 2-3 | 0 | 18-19 |
| v5.0 Platform + Product | 8 | 7 | 3-5 | 18-20 |
| **Running total** | **51** | **16-17** | **3-5** | **70-73** |

---

## 13. Claude Code Rules (All SOC Copilot Prompts)

```
RULES — SOC COPILOT REPO:
- Do NOT use git directly. I handle all git operations.
- Do NOT start the debugger. Log-based debugging only.
- Read before write. One concern per prompt.
- Import from gae library: from gae.scoring import score_alert
- Import CalibrationProfile: from gae.calibration import CalibrationProfile
- Factor Cypher queries MUST traverse relationships, not read properties (P10).
- Every graph mutation (decision, outcome) MUST emit events.
- f(t) stored in graph (Decision node), not in-memory cache (R4).
- No GAE math in copilot — use gae.scoring, gae.learning, gae.factors.
- LearningState MUST be constructed with CalibrationProfile from DomainConfig.
- NarrativeProvider: use protocol, not direct LLM calls.
- Reset: use StateManager for atomic soft/hard reset.
- Language: "product" not "demo" in all comments, docstrings, UI text.
```

---

## 14. SOCDomainConfig

```python
# domains/soc/config.py
from gae.factors import FactorComputer
from gae.calibration import CalibrationProfile, soc_calibration_profile

class SOCDomainConfig:
    """SOC domain configuration — the copilot's domain expertise.
    
    Provides:
    - Factor computers (graph traversal implementations)
    - Initial weight matrix (security expert priors)
    - CalibrationProfile (learning hyperparameters)
    - Action definitions
    """

    @staticmethod
    def get_actions() -> list:
        return ["escalate", "investigate", "suppress", "monitor"]

    @staticmethod
    def get_factor_computers() -> list:
        return [
            TravelMatchFactor(), AssetCriticalityFactor(),
            ThreatIntelEnrichmentFactor(), PatternHistoryFactor(),
            TimeAnomalyFactor(), DeviceTrustFactor(),
        ]

    @staticmethod
    def get_calibration_profile() -> CalibrationProfile:
        """SOC-specific learning hyperparameters.
        
        Key choices:
        - penalty_ratio=20.0: One missed threat ≈ $4.44M average breach cost.
          System earns trust slowly, loses it fast.
        - temperature=0.25: Sharp softmax — SOC triage is time-critical,
          decisive recommendations preferred over hedged distributions.
        - discount_strength=0.0: Confirmation bias mitigation disabled at v4.5.
          Enable at v5.0 after evaluation scenarios quantify the bias.
        """
        return soc_calibration_profile()

    @staticmethod
    def get_initial_W():
        """W₀: 4 actions × 6 factors. Security expert priors.
        
        These are DOMAIN EXPERTISE, not operational tuning.
        CalibrationProfile controls how W evolves from here.
        """
        import numpy as np
        return np.array([
            # travel  asset  threat  pattern  time  device
            [ 0.8,   0.9,    0.9,    0.3,    0.4,   0.3],   # escalate
            [ 0.5,   0.5,    0.7,    0.5,    0.6,   0.5],   # investigate
            [-0.3,  -0.2,   -0.5,    0.7,   -0.3,  -0.2],   # suppress
            [ 0.2,   0.3,    0.4,    0.4,    0.3,   0.4],   # monitor
        ], dtype=np.float64)

    @staticmethod
    def get_factor_decay_classes() -> dict[str, str]:
        """Map factor name → decay class for CalibrationProfile consumption.
        
        Source of truth: domain_schema.yaml (when implemented at v5.0).
        For v4.5: hardcoded here, consistent with SchemaContract.decay_class.
        """
        return {
            "travel_match": "campaign",
            "asset_criticality": "permanent",
            "threat_intel_enrichment": "campaign",
            "pattern_history": "standard",
            "time_anomaly": "standard",
            "device_trust": "standard",
        }
```

---

## 15. Simulation Mode

### 15.1 Design

Simulation mode runs N decisions through the identical GAE pipeline that manual triage uses. No shortcuts. No parallel scoring path. The only difference: outcomes are generated by a Bernoulli oracle instead of a human analyst.

**Why Bernoulli:** It proves the learning mechanism works without introducing confirmation bias (A1). The oracle is independent of the system's recommendation. This is honest: "Simulation mode demonstrates the learning mechanism. Accuracy numbers reflect the synthetic oracle, not real-world triage quality."

### 15.2 SimulationOrchestrator

```python
# backend/app/services/simulation.py

class SimulationOrchestrator:
    """Batch decision processing using the same GAE pipeline as manual triage.
    
    CRITICAL: Reuses EXACT same code path as triage.py:
      compute_factor_vector → score_entity → write_decision → update_learning
    Do NOT create a parallel scoring path. TD-019 taught us this lesson.
    """
    
    def __init__(self, alert_pool, neo4j_service, factor_computers, 
                 learning_state, domain_config):
        self.alert_pool = alert_pool
        self.neo4j = neo4j_service
        self.computers = factor_computers
        self.learning_state = learning_state
        self.domain_config = domain_config
        self.progress = {"running": False, "current": 0, "total": 0, 
                        "history": [], "by_category": {}}
        self.stop_flag = False
    
    async def run(self, n_decisions: int, correctness_rate: float = 0.8,
                  speed_ms: int = 100):
        """Run N decisions through GAE pipeline.
        
        Args:
            n_decisions: How many decisions to simulate (1-200)
            correctness_rate: Bernoulli parameter for oracle (default 0.8)
            speed_ms: Delay between decisions in ms (for UI update visibility)
        """
        # Atomic reset before simulation (clean learning progression)
        await self._reset_learning_state()
        
        self.progress = {
            "running": True, "current": 0, "total": n_decisions,
            "history": [], "by_category": {},
            "correctness_rate": correctness_rate,
        }
        self.stop_flag = False
        
        for i in range(n_decisions):
            if self.stop_flag:
                break
            
            # Pick alert (cycle through pool)
            alert = self.alert_pool[i % len(self.alert_pool)]
            alert_id = alert["id"]
            category = alert.get("situation_type", "unknown")
            
            # === SAME PIPELINE AS triage.py ===
            # Connector 1: Factor computation
            f, metadata = await compute_factor_vector(alert, self.computers, self.neo4j)
            
            # Connector 2: Scoring
            profile = self.domain_config.get_calibration_profile()
            result = score_entity(f, self.learning_state.W,
                                  self.domain_config.get_actions(),
                                  tau=profile.temperature)
            
            # Channel A: Decision write-back
            decision_id = await write_decision_to_graph(alert_id, result, f, self.neo4j)
            
            # Bernoulli oracle (independent of system recommendation)
            correct = random.random() < correctness_rate
            outcome = +1 if correct else -1
            
            # Connector 3: Weight update
            update = self.learning_state.update(
                action_index=result.selected_action_index,
                action_name=result.selected_action,
                outcome=outcome,
                f=f,
                confidence_at_decision=result.confidence,
            )
            save_learning_state(self.learning_state)
            
            # Channel B: Outcome write-back
            await mark_decision_outcome(decision_id, outcome, self.neo4j)
            # === END SAME PIPELINE ===
            
            # Track per-category accuracy
            if category not in self.progress["by_category"]:
                self.progress["by_category"][category] = {"correct": 0, "total": 0}
            self.progress["by_category"][category]["total"] += 1
            if correct:
                self.progress["by_category"][category]["correct"] += 1
            
            # Record
            self.progress["current"] = i + 1
            self.progress["history"].append({
                "decision_number": i + 1,
                "alert_id": alert_id,
                "category": category,
                "action": result.selected_action,
                "confidence": float(result.confidence),
                "correct": correct,
                "weight_norm": float(np.linalg.norm(self.learning_state.W)),
            })
            
            if speed_ms > 0:
                await asyncio.sleep(speed_ms / 1000.0)
        
        self.progress["running"] = False
        self.progress["summary"] = self._compute_summary()
    
    def _compute_summary(self) -> dict:
        """Generate summary after simulation."""
        history = self.progress["history"]
        total = len(history)
        correct = sum(1 for h in history if h["correct"])
        
        # Accuracy over time (sliding window)
        window = 10
        accuracy_curve = []
        for i in range(window, total + 1):
            window_correct = sum(1 for h in history[i-window:i] if h["correct"])
            accuracy_curve.append(window_correct / window)
        
        return {
            "total_decisions": total,
            "overall_accuracy": correct / total if total > 0 else 0,
            "accuracy_curve": accuracy_curve,
            "by_category": self.progress["by_category"],
            "final_weight_norm": history[-1]["weight_norm"] if history else 0,
        }
```

### 15.3 API Endpoints

```python
# backend/app/routers/simulation.py

POST /api/simulation/run
  Body: {"n_decisions": int, "correctness_rate": float, "speed_ms": int}
  Validation: 1 ≤ n ≤ 200, 0.0 ≤ rate ≤ 1.0, 0 ≤ speed_ms ≤ 2000
  Returns: {"started": true, "n_decisions": N}
  Notes: Runs in background (asyncio.create_task). Only one simulation at a time.

GET /api/simulation/status
  Returns: {
    "running": bool, "current": int, "total": int,
    "history": [...], "by_category": {...},
    "summary": {...} (only when complete)
  }

POST /api/simulation/stop
  Returns: {"stopped": true, "completed": int}
```

### 15.4 Alert Pool (Phase A — SIM-3a/3b)

Five categories, 15-20 alerts total:

| Category | ATT&CK Technique | Count | Dominant Factors | Example |
|---|---|---|---|---|
| Travel/VPN Anomaly | T1078 (Valid Accounts) | 4 | travel_match, device_trust | Singapore login, known traveler |
| Credential/Access | T1078.004, T1110 | 3 | pattern_history, time_anomaly | After-hours credential stuffing |
| Threat Intel Match | T1566.001 (Phishing) | 3 | threat_intel, asset_criticality | Spear-phishing target matches active campaign |
| Insider/Behavioral | T1567 (Exfiltration) | 3 | pattern_history, asset_criticality | Unusual data access pattern |
| Cloud/Infrastructure | T1048 (Exfiltration over Alt Protocol) | 3 | device_trust, threat_intel | Cloud storage upload from unknown device |

Each category activates different dominant factors → the learning curve diverges per category → visible proof of institutional judgment.

---

## 16. NarrativeProvider

### 16.1 Design

Local-first, protocol-based. The product runs fully self-contained without external API dependencies.

### 16.2 Interface

```python
# backend/app/services/narrative.py

from typing import Protocol
from dataclasses import dataclass

@dataclass
class NarrativeContext:
    """Structured input for narrative generation.
    
    All fields computed by GAE pipeline — the LLM is just
    the rendering layer. The intelligence is in the graph.
    """
    alert_id: str
    alert_type: str
    technique_id: str | None       # "T1078"
    technique_name: str | None     # "Valid Accounts"
    factors: dict[str, float]      # {"travel_match": 0.82, ...}
    dominant_factors: list[str]    # ["travel_match", "device_trust"]
    action: str                    # "suppress"
    confidence: float              # 0.91
    calibration_count: int         # How many prior outcomes inform this decision
    weight_changes: dict | None    # What changed since last similar alert
    user_context: dict | None      # User profile summary (from graph)
    asset_context: dict | None     # Asset details (from graph)

class NarrativeProvider(Protocol):
    """Protocol for investigation narrative generation."""
    async def generate(self, context: NarrativeContext) -> str: ...

class TemplateNarrativeProvider:
    """Zero-dependency fallback. Always available.
    Produces correct but mechanical narratives."""
    
    async def generate(self, context: NarrativeContext) -> str:
        technique_str = f" ({context.technique_id})" if context.technique_id else ""
        dominant = " and ".join(context.dominant_factors[:2])
        
        return (
            f"Alert {context.alert_id}: {context.alert_type}{technique_str}. "
            f"Dominant factors: {dominant}. "
            f"Recommendation: {context.action} at {context.confidence:.0%} confidence. "
            f"Calibrated from {context.calibration_count} verified outcomes."
        )

class OllamaNarrativeProvider:
    """Local LLM via Ollama. Default for production.
    No API key. No network dependency. Near-zero cost."""
    
    def __init__(self, model: str = "qwen2.5:7b",
                 base_url: str = "http://localhost:11434",
                 prompt_template: str | None = None):
        self.model = model
        self.base_url = base_url
        self.template = prompt_template or self._default_template()
    
    async def generate(self, context: NarrativeContext) -> str:
        prompt = self.template.format(**self._context_to_dict(context))
        try:
            response = await self._call_ollama(prompt)
            return response
        except Exception:
            # Graceful degradation to template
            fallback = TemplateNarrativeProvider()
            return await fallback.generate(context)
    
    def _default_template(self) -> str:
        return """You are a security operations analyst writing an investigation summary.

Alert: {alert_id} ({alert_type}, {technique_id})
Factors: {factors_formatted}
Dominant: {dominant_factors}
Recommendation: {action} at {confidence:.0%} confidence
Prior outcomes: {calibration_count} verified decisions on similar alerts

Write a 3-5 sentence investigation narrative. Be specific about the factors.
End with: "Calibrated from {calibration_count} verified outcomes."
"""

class GeminiNarrativeProvider:
    """Optional. Requires GEMINI_API_KEY in environment."""
    # ... existing Gemini integration, wrapped in NarrativeProvider protocol

class AnthropicNarrativeProvider:
    """Optional. Requires ANTHROPIC_API_KEY in environment."""
    # ... Claude API wrapper
```

### 16.3 Configuration

```python
# .env
NARRATIVE_PROVIDER=ollama          # or: template, gemini, anthropic
NARRATIVE_MODEL=qwen2.5:7b         # model within provider
NARRATIVE_PROVIDER_SIMULATION=template  # skip LLM during batch runs
```

### 16.4 Graceful Degradation

```
If NARRATIVE_PROVIDER=ollama and Ollama not running:
  → Fall back to template provider
  → Log warning: "Ollama not available, using template narratives"
  → UI shows narrative (template-generated) — functional but less polished

If NARRATIVE_PROVIDER=gemini and no API key:
  → Fall back to template provider
  → Log warning

If NARRATIVE_PROVIDER=template:
  → Direct template generation, no fallback needed
```

---

## 17. Reset Semantics

### 17.1 Reset Contract

| Level | W | Learning History | Convergence | Neo4j Decisions | Audit Trail | Graph Structure |
|---|---|---|---|---|---|---|
| **Soft** | → priors | Cleared | Cleared | Outcomes cleared (nodes remain) | RESET marker, new chain | Preserved |
| **Hard** | → priors | Cleared | Cleared | Nodes deleted | RESET marker, new chain | Re-seeded |

### 17.2 Implementation

```python
# backend/app/services/state_manager.py

class StateManager:
    """Coordinates reset across GAE state + audit store + Neo4j.
    
    Fixes TD-026: audit store and GAE history were out of sync on reset.
    All reset operations are atomic — partial reset is worse than no reset.
    """
    
    def __init__(self, learning_state, audit_store, neo4j_service, domain_config):
        self.learning_state = learning_state
        self.audit_store = audit_store
        self.neo4j = neo4j_service
        self.domain_config = domain_config
    
    async def soft_reset(self):
        """Reset learning state to priors. Preserve graph structure.
        Use case: evaluation runs, parameter tuning."""
        try:
            # 1. GAE state → priors
            self.learning_state.W = self.domain_config.get_initial_W()
            self.learning_state.decision_count = 0
            self.learning_state.history = []
            self.learning_state.epsilon_vector = self.learning_state._build_epsilon_vector()
            save_learning_state(self.learning_state)
            
            # 2. Neo4j: clear outcomes but keep Decision nodes
            await self.neo4j.execute_write("""
                MATCH (d:Decision) 
                SET d.outcome = null, d.correct = null, d.verified_at = null
            """)
            
            # 3. Audit trail: RESET marker + new chain
            self.audit_store.append_reset_marker("soft")
            self.audit_store.start_new_chain()
            
        except Exception as e:
            # If any step fails, log and raise — don't leave partial state
            raise ResetError(f"Soft reset failed at step: {e}")
    
    async def hard_reset(self):
        """Full reset to day zero. Re-seed graph.
        Use case: development, fresh start."""
        try:
            # Steps 1, 3 same as soft reset
            self.learning_state.W = self.domain_config.get_initial_W()
            self.learning_state.decision_count = 0
            self.learning_state.history = []
            self.learning_state.epsilon_vector = self.learning_state._build_epsilon_vector()
            save_learning_state(self.learning_state)
            
            # 2. Neo4j: delete Decision nodes, re-seed
            await self.neo4j.execute_write("MATCH (d:Decision) DETACH DELETE d")
            await reseed_graph(self.neo4j)
            
            # 3. Audit trail
            self.audit_store.append_reset_marker("hard")
            self.audit_store.start_new_chain()
            
        except Exception as e:
            raise ResetError(f"Hard reset failed at step: {e}")
```

### 17.3 API Endpoint

```python
# backend/app/routers/admin.py

POST /api/admin/reset
  Body: {"mode": "soft"|"hard", "confirm": true}
  Validation: confirm must be true (prevent accidental resets)
  Returns: {"reset": "soft"|"hard", "timestamp": "..."}
  Notes: Not visible in standard UI. Development/evaluation tool only.
         Logged in audit trail as an auditable event.
```

### 17.4 Reset and Simulation

SimulationOrchestrator calls `state_manager.soft_reset()` before starting. This ensures:
- Clean learning progression from priors (charts start from baseline)
- Decision history in Neo4j visible (PatternHistory can read them) but outcomes cleared
- Audit trail has a RESET marker so post-simulation analysis knows the starting point

---

## 18. ATT&CK Integration

### 18.1 Scope (v4.5 SIM-4)

Every alert carries an ATT&CK technique ID and tactic label. This is table stakes — every competitor speaks ATT&CK language. No detection logic changes; this is labeling and display.

### 18.2 Alert Schema Addition

```python
# Each alert in the pool includes:
{
    "id": "ALERT-7823",
    "situation_type": "TRAVEL_ANOMALY",
    "technique_id": "T1078",           # NEW
    "technique_name": "Valid Accounts", # NEW
    "tactic": "Initial Access",        # NEW
    # ... existing fields
}
```

### 18.3 UI Changes

**Tab 3 (Decision Detail):**
- Technique badge: `T1078 · Valid Accounts · Initial Access`
- Appears above the six-factor breakdown

**Tab 1 (Alert List):**
- Optional grouping: "Group by ATT&CK Tactic" toggle
- Tactic column in alert table

**Tab 4 (Compounding Metrics):**
- Per-technique accuracy in learning curve (future, post-v5.0)

### 18.4 Technique Mapping

| Situation Type | Technique | Tactic |
|---|---|---|
| TRAVEL_ANOMALY | T1078 Valid Accounts | Initial Access |
| CREDENTIAL_ACCESS | T1078.004 Cloud Accounts | Credential Access |
| PHISHING_MATCH | T1566.001 Spearphishing Attachment | Initial Access |
| DATA_EXFIL | T1567 Exfiltration Over Web Service | Exfiltration |
| CLOUD_ANOMALY | T1048 Exfiltration Over Alternative Protocol | Exfiltration |

---

## 19. Category Learning Curve

### 19.1 The Visual Proof of Institutional Judgment

A multi-line chart on Tab 4: x-axis is total decisions, y-axis is per-category accuracy, one line per alert category. The lines diverge over time — categories with more exposure improve faster.

This is the single most important visualization for proving compounding intelligence to a CISO or VC. "Same model, same code. Different categories learn at different rates. That's institutional judgment."

### 19.2 Data Source

SimulationOrchestrator tracks `by_category` accuracy during simulation. The chart updates via polling (GET /api/simulation/status). After simulation, the data persists in the learning state history.

### 19.3 Chart Specification

```
Chart: Category Learning Curve
Type: Multi-line time series
X-axis: Decision number (1 to N)
Y-axis: Rolling accuracy (window=10 decisions) per category
Lines: One per alert category (5 lines with SIM-3 alert pool)
Colors: Distinct per category
Annotations: 
  - Horizontal dashed line at baseline (random = 25% for 4 actions)
  - Vertical line at any error event (shows recovery speed)
Legend: Category name + current accuracy
```

### 19.4 Implementation (SIM-2 prompt scope)

Part of the frontend simulation panel. Recharts multi-line chart. Data from GET /api/simulation/status → by_category accuracy per decision. The chart renders during simulation (polling updates) and persists after simulation completes.

---

## 20. v4.5 Complete Prompt Specifications

### 20.1 SIM-FIX (TD-026 — Atomic Reset)

```
REFERENCE: Read backend/app/services/gae_state.py. Read backend/app/core/state_manager.py
(if exists). Read backend/app/services/audit_store.py (or equivalent).

TASK [SIM-FIX]: Fix TD-026 — make reset atomic across GAE state, audit store, and Neo4j.

1. Create or update backend/app/services/state_manager.py:
   - StateManager class with soft_reset() and hard_reset() methods
   - soft_reset: W → priors, history cleared, Neo4j outcomes cleared, audit RESET marker
   - hard_reset: Everything in soft + Decision nodes deleted + re-seed
   - Both methods are atomic: if any step fails, raise error (no partial state)

2. Create backend/app/routers/admin.py:
   - POST /api/admin/reset with mode=soft|hard, confirm=true
   - Register in main.py

3. Update existing reset-all endpoint to use StateManager.hard_reset()

TESTS:
   # Test 1: StateManager imports
   python -c "from app.services.state_manager import StateManager; print('PASS')"
   
   # Test 2: API endpoint (server running)
   curl -X POST http://localhost:8000/api/admin/reset \
     -H "Content-Type: application/json" \
     -d '{"mode": "soft", "confirm": true}'
   # Should return 200 with reset confirmation

Do NOT start the debugger. Do NOT use git directly.
```

### 20.2 SIM-1 (SimulationOrchestrator)

See session_continuation_v18 Part 4 for the ready-to-paste prompt. Updated requirements:

- **Addition:** Use CalibrationProfile from DomainConfig (if GAE preamble complete)
- **Addition:** Call state_manager.soft_reset() before simulation start
- **Addition:** Track by_category accuracy in progress dict
- **Unchanged:** Same GAE pipeline as triage.py. No parallel scoring path.

### 20.3 SIM-2 (Frontend Simulation Panel)

```
REFERENCE: Read frontend/src/tabs/ to understand tab structure.
Read backend/app/routers/simulation.py (created in SIM-1).

TASK [SIM-2]: Create frontend simulation panel with real-time updates.

1. Add simulation controls to appropriate tab (Tab 4 or new tab):
   - "Run Simulation" button with inputs: n_decisions (default 50), speed slider
   - Progress bar showing current/total
   - "Stop" button (calls POST /api/simulation/stop)

2. Category Learning Curve chart:
   - Multi-line Recharts chart
   - X: decision number, Y: rolling accuracy per category
   - One line per category (5 lines), distinct colors
   - Horizontal dashed line at 25% (random baseline)
   - Updates during simulation via polling (GET /api/simulation/status every 500ms)

3. Simulation summary panel (shown when complete):
   - Total decisions, overall accuracy, strongest/weakest category
   - Final weight norm

TESTS:
   # Start simulation via API, verify frontend shows progress
   # After completion, verify category learning curve has diverging lines
   # Verify all existing tabs still work

Do NOT start the debugger. Do NOT use git directly.
```

### 20.4 NAR-1 (NarrativeProvider)

```
REFERENCE: Read backend/app/services/reasoning.py (existing Gemini integration).
Read backend/app/routers/triage.py (where narrative would be generated).

TASK [NAR-1]: Create NarrativeProvider protocol with three implementations.

1. Create backend/app/services/narrative.py:
   - NarrativeContext dataclass (see §16.2)
   - NarrativeProvider protocol
   - TemplateNarrativeProvider (zero dependency, always works)
   - OllamaNarrativeProvider (local Qwen via Ollama, graceful fallback to template)
   
2. Provider selection from .env:
   NARRATIVE_PROVIDER=ollama (default)
   NARRATIVE_MODEL=qwen2.5:7b (default)
   NARRATIVE_PROVIDER_SIMULATION=template

3. Wire into triage response — add narrative field to triage analysis response.

TESTS:
   # Test 1: Template provider
   python -c "
   import asyncio
   from app.services.narrative import TemplateNarrativeProvider, NarrativeContext
   provider = TemplateNarrativeProvider()
   ctx = NarrativeContext(alert_id='ALERT-7823', alert_type='TRAVEL_ANOMALY',
       technique_id='T1078', technique_name='Valid Accounts',
       factors={'travel_match': 0.82, 'device_trust': 0.91},
       dominant_factors=['travel_match', 'device_trust'],
       action='suppress', confidence=0.91, calibration_count=12,
       weight_changes=None, user_context=None, asset_context=None)
   result = asyncio.run(provider.generate(ctx))
   assert 'ALERT-7823' in result
   assert 'calibrated from 12' in result.lower() or 'Calibrated from 12' in result
   print(f'Narrative: {result}')
   print('TEST 1 PASS')
   "

Do NOT start the debugger. Do NOT use git directly.
```

---

## Appendix A: Version History

| Version | Date | Changes |
|---|---|---|
| v4_design 1.0–7.0 | Feb 24–27 | Through GAE Foundation sprint planning |
| v4_5_design 1.0–8.0 | Feb 24–27 | Through Docker/VPS causal impacts |
| **soc_copilot_design 1.0** | **Feb 28** | Three-repo restructure. GAE → gae_design_v5. Platform → ci_platform_design_v1. |
| **soc_copilot_design 2.0** | **Mar 1** | v4.5 redesigned ("Make It Real"). INOVA → v6.0. Docker → v5.5. Simulation mode, NarrativeProvider, reset semantics, ATT&CK, category learning curve. CalibrationProfile integration. v5.0 redefined. Language: "product preview." |
| **soc_copilot_design 3.0** | **Mar 1** | v1 + v2 consolidated into single document. All sections current. |

## Appendix B: Technical Debt Status

| ID | Description | Status | Version |
|---|---|---|---|
| TD-014 | TimeAnomaly reads properties | LOW — acceptable | v5.5 |
| TD-015 | DeviceTrust reads properties | LOW — acceptable | v5.5 |
| TD-017 | Hardening state not fully persisted | HIGH | v5.0 |
| TD-018 | Dual persistence paths | MED | v5.0 |
| TD-019 | Dual decision paths | **CLOSE at v4.5 Phase B (TAB2-1)** | v4.5 |
| TD-020 | execute_action without events | **CLOSE at v4.5 Phase B (TAB2-2)** | v4.5 |
| TD-023 | Backward-compat block | LOW | v5.5 |
| TD-024 | Two LearningState classes | LOW | v5.0 |
| TD-025 | No CalibrationProfile | **CLOSE at v4.5 GAE preamble** | v4.5 |
| TD-026 | Audit/GAE sync on reset | **CLOSE at v4.5 SIM-FIX** | v4.5 |

## Appendix C: Superseded Documents

| Old Document | Status | Content Destination |
|---|---|---|
| `v4_design_document_v7.md` | **Superseded** | SOC content → this doc. GAE prompts → gae_design_v7. Claude Code rules → session_continuation. |
| `v4_5_design_v8.md` | **Superseded** | All content → this doc. |
| `soc_copilot_design_v1.md` | **Superseded** | Absorbed into this doc (v3). |
| `soc_copilot_design_v2.md` | **Superseded** | Absorbed into this doc (v3). |

---

*SOC Copilot — Design Document v3 | February 28 – March 1, 2026*
*Three-repo stack: GAE (math) → ci-platform (infra) → soc-copilot (domain)*
*v4.1: 34 prompts complete. v4.5: 18-19 prompts (Make It Real). v5.0: 18-20 prompts.*
*Companion: gae_design_v7, ci_platform_design_v1, design_decisions_v1, gap_analysis_v3*
*"The moat is the graph, not the model. The product proves it."*
