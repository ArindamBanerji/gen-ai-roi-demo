# SOC Copilot — Design Document v1

**Date:** February 28, 2026
**Version:** 1.0
**Status:** v4.1 GAE Foundation sprint next. Phase 1 ✅, Phase 5 UI ✅.
**Repository:** soc-copilot (proprietary)
**Theme:** "Your tools, our decisions."
**Companion repos:**
- graph-attention-engine (standalone library — Apache 2.0). Design: `gae_design_v5.md`
- ci-platform (production infrastructure — v4.5+). Design: `ci_platform_design_v1.md`

**Git remotes:**
- SOC copilot: git@github.com:ArindamBanerji/gen-ai-roi-demo.git (v4.0-dev branch)
- GAE library: graph-attention-engine (standalone repo)
- Experiments: git@github.com:ArindamBanerji/cross-graph-experiments.git

> **This document absorbs and supersedes:**
> - `v4_design_document_v7.md` — SOC copilot v4.0 build plan
> - `v4_5_design_v8.md` — INOVA, Docker, VPS
> 
> GAE-specific content (Tiers 1-5, scoring, learning, events, contracts) now lives in `gae_design_v5.md`.
> Platform-specific content (UCL, agents, event bus, governance) now lives in `ci_platform_design_v1.md`.

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
| Production event bus | ci-platform (v4.5+) | Infrastructure |
| Entity resolution (INOVA) | ci-platform (v4.5+) | Domain-agnostic |
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
│       │       ├── config.py               # SOCDomainConfig: actions, W, τ
│       │       ├── factors.py              # 6 FactorComputer implementations
│       │       ├── orchestrator.py         # async Neo4j → compute → GAE assemble
│       │       ├── situations.py           # Scoring-based classification (v5.0)
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
│       │   └── dashboard.py               # GET /api/dashboard/roi (v5.0)
│       ├── services/
│       │   ├── event_bus.py               # Lightweight bus (v4.1 — replaced by platform at v4.5)
│       │   ├── feedback.py                # Outcome recording + trust gate
│       │   ├── narrative.py               # LLM narrative generation (v5.0)
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
│   └── test_feedback.py
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

**Tech debt:** TimeAnomaly and DeviceTrust currently read alert properties in the v3.2 codebase. The v4.1 GAE-2c prompt must rewrite them to traverse relationships (`[:ACTIVE_AT]`, `[:USES_DEVICE]`). This is documented in the SHORTCUT-AUDIT (§9.1).

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

## 7. v4.1 SOC Copilot Prompts (6 prompts — soc-copilot repo)

> GAE repo prompts (GAE-0 through GAE-2a-protocol, 7 prompts) are in `gae_design_v5.md`.
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

**Post-sprint gate:** 10-cycle compounding verification (§8). If it passes → TAG v4.1.

---

## 8. End-to-End Compounding Verification (Post-Sprint Gate)

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

**If this passes, the system compounds. If any step fails, a causal link is broken.**

---

## 9. v4.5 Scope (After v4.1 Tagged)

### 9.1 SHORTCUT-AUDIT (Pre-gate, 0 prompts)

Two focused questions before building v4.5:

**Q1: Which factor queries traverse relationships vs. read properties?**

| Factor | Pattern | Accumulates? |
|---|---|---|
| TravelMatch | `(u)-[:HAS_TRAVEL]->(t)` | ✅ Channel C, D |
| AssetCriticality | `(a:Asset)-[:STORES]->(dc)` | ✅ Channel C, D |
| ThreatIntelEnrichment | `(ti)-[:ASSOCIATED_WITH]->(a)` | ✅ Channel C, D |
| PatternHistory | `(d:Decision)-[:DECIDED_ON]->(a)` | ✅ Channel A, B |
| TimeAnomaly | `(u:User)-[:ACTIVE_AT]->(ts:TimeSlot)` | ✅ Fixed in GAE-2c |
| DeviceTrust | `(d:Device {id: $device})` | ⚠️ Acceptable for v4.5 |

**Q2: Which graph mutations emit events?** All decision/outcome mutations emit after GAE-2d/GAE-3a. TI ingest and discovery emit after v4.5 INOVA.

### 9.2 INOVA MVP (Sessions A-E, 14 prompts)

Entity resolution using Intuitive Near-Overlap Verification Algorithm. Discovers relationships between entities that share attributes but aren't yet linked.

**Key requirement:** After writing `[:CALIBRATED_BY]`, emit `GraphMutated(mutation_type="discovery")`. If new dimension: emit `DiscoveryValidated`. This enables cross-domain accumulation (Channel D).

### 9.3 Flash Tier Mimic (Session F, 4 prompts)

Simulated streaming response for demo realism.

### 9.4 Docker for Partners (Session G, 5 prompts)

**Named volumes (not anonymous):**
```yaml
volumes:
  neo4j_data:
    name: soc-copilot-neo4j-data    # Decision nodes, f(t), outcomes
  gae_state:
    name: soc-copilot-gae-state     # W matrix, learning history
```

**PARTNER_README:** Document that volumes contain accumulated intelligence. Provide backup/restore commands. Warn that `docker-compose down -v` destroys learned state.

### 9.5 VPS Hosting (Session H, 4 prompts)

Public demo → reset every 4h. Partner instance → NO auto-reset, backup cron instead.

### 9.6 Polish (Session I, 3 prompts)

**v4.5 Total: 30 prompts, 11 sessions.**

---

## 10. v5.0 SOC Copilot Additions

| Prompt | Scope | Creates/Modifies | Test |
|---|---|---|---|
| GAE-4a | Scoring-based situation classification | `domains/soc/situations.py` | 5 alert types → ≥4/5 correct |
| GAE-4b | Classification learning from corrections | `domains/soc/situations.py`, frontend | Override 2 → next similar classified better |
| GAE-5a | LLM investigation narrative | `services/narrative.py`, Anthropic API | Narrative references graph entities |
| GAE-5b | Narrative quality + display | Frontend narrative panel | Different alerts → different narratives |
| GAE-1g | Contract validation endpoint + startup hook | `routers/gae.py`, `main.py` | Startup logs 6 contracts validated |
| SEED-2 | Realistic seed data with noise | `seed_realistic.py` | 200+ users, power-law alerts, 10% missing props |
| ECON-1 | ROI dashboard endpoint + Tab 4 panel | `routers/dashboard.py`, `DashboardTab.tsx` | GET /api/dashboard/roi → weekly savings |
| EVAL-1-soc | SOC evaluation scenarios (30 ground-truth) | `domains/soc/evaluation_scenarios.json` | Scored by GAE eval_scorer |

**v5.0 SOC additions: 8 prompts.**

---

## 11. Demo Flow Transformation

### Before GAE (v3.2 — current)

```
Alert → hardcoded factors → if-else scoring → template narrative
  → human clicks approve → trust counter ±delta → counter chart
```

### After GAE v4.1 Foundation

```
Alert → graph traversal computes 6 factors from Neo4j (Connector 1)
  → GAE Eq. 4: f · Wᵀ / τ → softmax → action probabilities (Connector 2)
  → Decision node written to graph with f(t) (R4) ← CHANNEL A
  → DecisionMade + GraphMutated events emitted
  → human reviews, decides, gives feedback
  → f(t) retrieved from Decision node in graph (R4, not memory)
  → GAE Eq. 4b: W update with 20:1 asymmetry + per-factor decay (Connector 3)
  → Decision node marked correct/incorrect ← CHANNEL B
  → OutcomeVerified + GraphMutated events emitted
  → dashboard shows REAL convergence from REAL accumulated decisions
  → NEXT CYCLE: PatternHistoryFactor reads accumulated decisions → richer f
```

### After v4.5 + INOVA

```
  + Entity resolution discovers hidden relationships ← CHANNEL D
  + Discovery nodes written with [:CALIBRATED_BY]
  + Docker preserves accumulated intelligence across restarts
```

### After v5.0

```
  + Scoring-based situation classification (from factors, not hardcoded)
  + LLM narratives reference actual graph entities
  + ROI dashboard shows time-saved vs. manual triage
```

**The UI barely changes. What changes is everything behind it.**

---

## 12. Build Sequence

```
COMPLETED:
  Phase 1: (Sessions 0-4, 13 prompts) ✅
  Phase 5: (Sessions 5-6, 8 prompts) ✅

v4.1 GAE FOUNDATION: (13 prompts across 2 repos)

  GAE REPO (graph-attention-engine) — 7 prompts:
    Session 7:  GAE-0 (scaffold) + GAE-1a (scoring) + GAE-1b (learning) + GAE-1c (store)
    Session 8a: GAE-1d (primitives) + GAE-1e (event types) + GAE-2a-protocol (factors)

  SOC COPILOT REPO [THIS REPO] — 6 prompts:
    Session 8b: GAE-2a-soc (TravelMatch + AssetCriticality + orchestrator + seed)
    Session 9:  GAE-2b (ThreatIntel + PatternHistory) + GAE-2c (Time + Device) + GAE-2d (wire + write-back)
    Session 10: GAE-3a (feedback + outcome) + GAE-3b (dashboard) + GAE-3c (convergence)

  POST-SPRINT GATE: 10-cycle compounding verification (§8)
  TAG: v4.1

v4.5: (30 prompts, 11 sessions — after v4.1 tagged)
  SHORTCUT-AUDIT → INOVA → Flash Tier → Docker → VPS → Polish
  TAG: v4.5

v5.0 SOC ADDITIONS: (8 prompts)
  Classification → Narratives → Contract validation → Seed → ROI → Eval
  TAG: v5.0-soc
```

**Prompt totals:**
| Version | SOC Prompts | GAE Prompts | Total |
|---|---|---|---|
| Phase 1 + Phase 5 | 21 | 0 | 21 ✅ |
| v4.1 GAE Foundation | 6 | 7 | 13 |
| v4.5 | 30 | 0 | 30 |
| v5.0 SOC | 8 | 3-4 | 11-12 |
| **Running total** | **65** | **10-11** | **75-76** |

---

## 13. Claude Code Rules (All SOC Copilot Prompts)

```
RULES — SOC COPILOT REPO:
- Do NOT use git directly. I handle all git operations.
- Do NOT start the debugger. Log-based debugging only.
- Read before write. One concern per prompt.
- Import from gae library: from gae.scoring import score_alert
- Factor Cypher queries MUST traverse relationships, not read properties (P10).
- Every graph mutation (decision, outcome) MUST emit events.
- f(t) stored in graph (Decision node), not in-memory cache (R4).
- No GAE math in copilot — use gae.scoring, gae.learning, gae.factors.
```

---

## 14. SOCDomainConfig

```python
# domains/soc/config.py
from gae.factors import FactorComputer
from gae.learning import LearningState

class SOCDomainConfig:
    """SOC domain configuration — the copilot's domain expertise."""

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
    def get_initial_W():
        """Initial weight matrix (4 actions × 6 factors). Security expert priors."""
        import numpy as np
        return np.array([
            # travel  asset  threat  pattern  time  device
            [ 0.8,   0.9,    0.9,    0.3,    0.4,   0.3],   # escalate
            [ 0.5,   0.5,    0.7,    0.5,    0.6,   0.5],   # investigate
            [-0.3,  -0.2,   -0.5,    0.7,   -0.3,  -0.2],   # suppress
            [ 0.2,   0.3,    0.4,    0.4,    0.3,   0.4],   # monitor
        ], dtype=np.float64)

    @staticmethod
    def get_temperature() -> float:
        return 0.25
```

---

## Appendix A: Version History

| Version | Date | Changes |
|---|---|---|
| v4_design 1.0–7.0 | Feb 24–27 | Through GAE Foundation sprint planning |
| v4_5_design 1.0–8.0 | Feb 24–27 | Through Docker/VPS causal impacts |
| **soc_copilot_design 1.0** | **Feb 28** | **Three-repo restructure. Absorbs v4_design_v7 + v4_5_design_v8. GAE content → gae_design_v5. Platform content → ci_platform_design_v1.** |

## Appendix B: Superseded Documents

| Old Document | Status | Content Destination |
|---|---|---|
| `v4_design_document_v7.md` | **Superseded** | SOC content → this doc. GAE prompts → gae_design_v5. Claude Code rules → session_continuation_v17. |
| `v4_5_design_v8.md` | **Superseded** | All content → this doc §9. |

---

*SOC Copilot — Design Document v1 | February 28, 2026*
*Three-repo stack: GAE (math) → ci-platform (infra) → soc-copilot (domain)*
*v4.1: 6 SOC prompts + 7 GAE prompts = 13 total. Every cycle leaves the graph richer.*
*v4.5: 30 prompts (INOVA, Docker, VPS). v5.0: 8 SOC additions.*
