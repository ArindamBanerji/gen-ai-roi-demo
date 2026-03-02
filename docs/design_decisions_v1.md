# Design Decisions — v4.5/v5.0 Planning Session

**Date:** March 1, 2026
**Context:** Post-v4.1 tag, post-gap analysis. Planning v4.5 ("Make It Real") and redefining v5.0 for MVP.
**MVP Definition:** GAE layer is broad and usable for multiple domains (like HuggingFace transformers) + SOC copilot and CI reach demonstrable product stage.
**Language:** "Product preview" externally. "Product" internally. Not "demo."

---

## Decision Summary

### Decision 1: CalibrationProfile — GAE Library Feature

**Resolution:** CalibrationProfile is a GAE dataclass. DomainConfig provides one. LearningState accepts one at construction.

**Design:**
```python
@dataclass
class CalibrationProfile:
    # Core (v4.5 — GAE preamble)
    learning_rate: float = 0.02
    penalty_ratio: float = 20.0
    temperature: float = 0.25
    decay_rates: dict[str, float] = field(default_factory=dict)
    discount_strength: float = 0.0   # A1 confirmation bias fix (default off)

    # Extension point — future params land here first,
    # graduate to named fields when stable
    extensions: dict[str, Any] = field(default_factory=dict)
```

**Extensibility:** Defaults on everything + extensions dict for experimental parameters. Future candidates (convergence behavior, cold-start handling, factor-specific overrides) named in roadmap without commitment.

**S2P validation:** Different temperature, penalty ratio, and decay rates for procurement domain. All configurable through the same profile. ✅

---

### Decision 2: Per-Factor Decay Semantics — Three-Layer Design

**Resolution:** Three layers, clean separation of concerns.

| Layer | Who | What | Where |
|---|---|---|---|
| Domain schema | Domain expert | Declares factor's temporal nature (decay class) | `domain_schema.yaml` in copilot repo |
| CalibrationProfile | Operational tuning | Maps decay class → ε value | CalibrationProfile in GAE |
| Learning loop | GAE math | Applies the rate in Eq. 4c | `gae/learning.py` |

**Decay classes:** permanent (ε=0.0001), standard (ε=0.001), campaign (ε=0.003), transient (ε=0.01). Extensible — new classes are schema + profile config, not code changes.

**FactorComputer Protocol unchanged.** `compute(entity_id, context) → float`. Decay is metadata about the factor, not behavior of the factor.

**GAE impact at v4.5:** LearningState refactored to accept CalibrationProfile, Eq. 4c becomes decay-class-aware. Must happen before SIM-1 (simulation exercises learning loop 50+ times).

---

### Decision 3: Ground Truth and Evaluation — Three-Tier Progression

**Resolution:**

| Tier | Version | Method | What It Proves |
|---|---|---|---|
| Tier 1 | v4.5 | Bernoulli oracle (simulation mode) | Learning mechanism works |
| Tier 2 | v5.0 | 30-40 constructed scenarios from ATT&CK × graph context | Product makes correct decisions |
| Tier 3 | v6.0 | Live analyst decisions with delayed validation | Product works in production |

**Ground truth source:** Constructed from ATT&CK techniques × graph context combinations. Each scenario has planted signals with deterministic correct answers. No external labeled data required.

**Evaluation scenario format — GAE-level capability:**

```python
@dataclass
class EvaluationScenario:
    scenario_id: str              # "SOC-T1078-FP-01"
    description: str
    domain: str                   # "soc", "s2p", "finserv"
    category: str
    technique_id: str | None      # ATT&CK for SOC, N/A for S2P
    confidence_tier: str          # "high", "medium", "low"
    graph_context: dict           # Entities + relationships + absent conditions
    alert: dict                   # Alert parameters
    expected_action: str
    expected_dominant_factors: list[str]
    planted_relationship: dict | None      # For discovery (B3) scenarios
    expected_confidence_shift: dict | None # For discovery scenarios
    learning_prerequisite: dict | None     # For compounding test scenarios
```

**Three consumers:** EVAL-1 (accuracy), SEED-2 (planted patterns), B3 gate (discovery test cases).

**`expected_dominant_factors`:** Tests whether the system gets the right answer for the right reasons. Getting the right action from wrong factors is a false pass.

**`confidence_tier`:** Enables honest reporting — high/medium/low difficulty. Low tier is where analysts disagree; lower accuracy there is expected.

**`learning_prerequisite`:** Enables compounding tests — "evaluate after 20 prior correct decisions on similar alerts."

**Ordered vs independent sequences:** Decision deferred to v5.0 implementation. Format supports both.

---

### Decision 4: Confirmation Bias (A1) — Honest Framing + Roadmap Fix

**Resolution:** Don't fix mechanism at v4.5. Measure it. Fix at v5.0.

**Framing:**
- Simulation mode avoids confirmation bias entirely (Bernoulli oracle independent of system recommendation)
- 20:1 asymmetric penalty limits damage
- Convergence monitor flags instability symptoms
- Evaluation scenarios can measure confirmation bias directly (sequence of 20 confirmations followed by true positive)

**Fix:** `discount_strength` field in CalibrationProfile (Decision 1). Default 0.0 at v4.5. SOC sets tuned value at v5.0 based on evaluation scenario results.

**Formula:** `α_effective = α × (1 - discount_strength × max(P))`

---

### Decision 5: Cold-Start and Reset Semantics

**Initial W matrix:** Lives in DomainConfig (domain expertise). CalibrationProfile controls how W evolves from there (operational tuning).

**Reset contract — two levels:**

| Level | What Resets | What Persists | Use Case |
|---|---|---|---|
| Soft reset | W → priors, learning history, convergence metrics, Decision outcomes cleared, audit trail new chain | Graph structure (Users, Assets, Alerts, ThreatIntel), Decision nodes (without outcomes) | Evaluation runs, parameter tuning |
| Hard reset | Everything in soft + Decision nodes deleted, graph re-seeded | Nothing — back to day zero | Development, fresh start |

**Reset is atomic:** StateManager coordinates GAE reset + audit reset + Neo4j cleanup in single operation. Fixes TD-026.

**Reset endpoint:** Behind admin route (`POST /api/admin/reset?confirm=true&mode=soft|hard`). Logged in audit trail. Not visible in standard UI.

**Cold-start indicator:** If `total_decisions < N`, UI shows "Calibrating" message. Implementation timing TBD.

---

### Decision 6: Embedding Approach — Design for B, Test C First

**Resolution:** Option B architecture (optional dependency) with Option C tested first.

**Design:**
- GAE defines: `EntityEmbedding` dataclass, `EmbeddingProvider` protocol
- Default: `PropertyEmbeddingProvider` (numpy-only, ships with GAE core)
- Optional: `TransformerEmbeddingProvider` via `pip install graph-attention-engine[embeddings]` (adds torch + sentence-transformers, ~2GB)
- Phase C starts with PropertyEmbeddingProvider
- B3 gate tests property-based first; if F1 < 0.2, falls back to transformer-based

**The 2GB dependency:** PyTorch (~1.5-2GB) + transformers + model weights. Never in GAE core. Always optional.

**Core product story preserved:** `pip install graph-attention-engine` stays lightweight, numpy-only.

---

### Decision 7: Narrative LLM — Local-First, Provider Abstraction

**Resolution:** NarrativeProvider protocol with multiple implementations. Ollama/Qwen as default.

**Provider spectrum:**

| Provider | Cost | Dependency | Default For |
|---|---|---|---|
| Template (no LLM) | Zero | None | Simulation batch runs |
| Ollama/Qwen (local) | Near zero | Local Ollama | Default for manual triage |
| Gemini Flash | Low | API key + network | Optional |
| Gemini Pro / Claude | Higher | API key + network | Optional |

**Config:** `NARRATIVE_PROVIDER=ollama`, `NARRATIVE_MODEL=qwen2.5:7b`, `NARRATIVE_PROVIDER_SIMULATION=template`

**Prompt templates:** Per-provider configuration. Smaller models need more explicit structure.

**Product story:** Fully self-contained — GAE (numpy), narratives (Ollama), graph (Neo4j). Zero external API dependencies.

**Simulation optimization:** Narratives skipped during batch runs. Summary narrative generated at end only.

---

### Decision 8: Proving Better Decisions + Institutional Judgment

**8a: Ablation methodology — proving decisions are better:**

Four comparison baselines, all runnable within the product:

| Baseline | Description | What's Missing |
|---|---|---|
| Static | Fixed W at expert priors, never learns | No Axis 2 |
| Flat learning | Symmetric reinforcement (no 20:1) | No risk-aware governance |
| No graph context | Random/uniform factors, W still learns | No Axis 1 |
| Full system | Everything | The product |

**Measurements:** Action accuracy, learning curve shape, recovery time after errors, confidence calibration, confirmation-bias resistance.

**Design:** `AblationConfig` + `AblationReport` as GAE-level capability. Any domain copilot can run ablation studies.

**8b: Institutional Judgment — three metrics:**

| Metric | What It Measures | Visualization |
|---|---|---|
| Prior Divergence × Accuracy | How far W moved from priors AND that the movement improved decisions | Single score, tracked over time |
| Organizational Specificity | Two instances trained on different distributions perform differently on swapped scenarios | Cross-training comparison |
| Category Learning Curve | Per-category accuracy over total decisions | Multi-line chart — the visual proof |

**Domain-specific translation:** GAE computes abstract metrics. Domain copilot translates to operational language.

- SOC: "analyst hours saved," "auto-triage rate," "MTTR reduction"
- S2P: "processing time saved," "exception detection rate," "compliance improvement"

**B3 gate:** Five initial discovery pattern categories (role change × access, campaign correlation, device trust × threat intel, behavioral drift, policy conflict emergence). Starting point — revisited holistically at v5.5-v6.0 with downstream accuracy impact as additional criterion.

---

### Cross-Cutting Decisions

**Language:** "Product preview" externally, "product" internally. Not "demo."

**Docker/VPS:** Deferred to v5.5. All v4.5 and v5.0 work runs locally. Loom v2 records on local machine.

**ci-platform timing:** v5.0 is first real code (v0.1.0). v5.0 design will identify minimal scaffolding to pull into v4.5.

**S2P validation:** All design decisions validated against S2P use case. v5.0 design includes "S2P validation walkthrough" section. FactorComputer stays `compute() → float` — categorical encoding is copilot's responsibility, declared in domain schema.

**Ontology:**
- Level 0 (v4.1): Implicit — exists in seed scripts and Cypher queries
- Level 1 (v5.0): Declared + validated — `domain_schema.yaml` + ContractChecker at startup
- Level 2 (v6.0): Enforced — SchemaValidator gates all write paths
- Schema format defined in GAE (protocol). Actual schema files live in copilots (domain content). Schema becomes single source of truth for CalibrationProfile decay classes, SchemaContracts, and seed data structure.

---

## Updated v4.5 Structure

GAE preamble (2-3 prompts) → Phase A (simulation, 6 prompts) → Phase B (narrative, 4 prompts) → Phase C (discovery, gated, 6 prompts)

**Phase D eliminated.** Docker/VPS deferred to v5.5. CalibrationProfile moves to GAE preamble.

**GAE preamble (NEW — before Phase A):**

| Prompt | Repo | What |
|---|---|---|
| GAE-CAL-1 | GAE | CalibrationProfile dataclass + LearningState refactor to accept it |
| GAE-CAL-2 | GAE | Per-factor decay in learning loop + decay class mapping |

---

## v5.0 Redefinition: "GAE as Platform + SOC as Product"

**GAE v0.2.0 (platform breadth):**
- CalibrationProfile API hardening (stable after v4.5 usage)
- Domain schema format + parser
- EvaluationScenario format + eval_scorer + AblationConfig
- EmbeddingProvider protocol (preparing for Phase C or standalone use)
- Example domain (E3) — Hello World DomainConfig
- API surface design + import lint (E1, E2)
- Engine test suite independence (E4)
- GAE Users Guide (E5)

**ci-platform v0.1.0 (first real code):**
- DomainConfig base (extracted from SOC)
- Domain schema format + parser integration
- ContractChecker (validates SchemaContracts against domain schema)
- StateManager (extracted from SOC, with soft/hard reset)
- domain_registry (extracted from SOC)

**SOC copilot (product polish):**
- SEED-2 — realistic data (200+ users, noise, power-law distributions)
- EVAL-1 — 30-40 evaluation scenarios constructed from ATT&CK × graph context
- ECON-1 — ROI dashboard with operational metrics
- Situation classification (GAE-4a/4b)
- Confidence-discounted learning (A1 fix — tuned discount_strength)
- Institutional Judgment metrics on Tab 4

**Old v5.0 content (Splunk, SAML, PII redaction, cloud deployment) → v6.0**

---

## Updated Technology Gap Tracking

### Gaps Affected by These Decisions

| Gap ID | Gap | Original Version | New Status | Changed By |
|---|---|---|---|---|
| A1 | Confirmation bias | v5.5-v6.0 | **v4.5 (measured) + v5.0 (fixed)** | Decision 4: discount_strength in CalibrationProfile |
| A2 | Uniform temporal decay | v5.5 | **v4.5 (GAE preamble)** | Decision 2: per-factor decay via CalibrationProfile |
| A4 | False discovery propagation | v5.5 | Unchanged — v5.5 | Only matters if Phase C gate passes |
| B3 | Embeddings at scale | v5.0 | **v4.5 Phase C (test) + v5.5 (revisit)** | Decision 6: test property-based first, threshold 0.2 |
| E1 | Engine API surface | v5.0 | v5.0 (unchanged) | — |
| E2 | Dependency enforcement | v5.0 | v5.0 (unchanged) | — |
| E3 | Example domain | v5.0 | v5.0 (unchanged) | — |
| E4 | Engine test suite | v5.0 | v5.0 (unchanged) | — |
| E5 | Engine documentation | v5.5 | v5.0 (pulled earlier) | v5.0 redefinition includes GAE Users Guide |
| H4 | Decision economics | v5.0 | v5.0 (unchanged) | — |
| H5 | Data realism | v5.0 | v5.0 (unchanged) | — |
| H6 | Evaluation ground truth | v5.0 | v5.0 (unchanged) | Decision 3: evaluation scenario format designed |
| TD-026 | Audit/GAE sync on reset | Phase A | **v4.5 (pre-SIM-1 or SIM-1)** | Decision 5: atomic reset via StateManager |

### New Gaps Identified in This Session

| Gap ID | Gap | Severity | Version | Description |
|---|---|---|---|---|
| **D1** | Ablation framework | MEDIUM | v5.0 | Four-baseline comparison needed to prove architectural value |
| **D2** | Institutional Judgment metrics | HIGH | v4.5 (partial) + v5.0 (full) | Category learning curve at v4.5 (SIM-2), full metrics at v5.0 |
| **D3** | Domain schema format | HIGH | v4.5 (design) + v5.0 (implement) | Single source of truth for factor metadata. Design now, build at v5.0. |
| **D4** | ci-platform extraction | MEDIUM | v5.0 | DomainConfig, StateManager, domain_registry extracted from SOC |
| **D5** | NarrativeProvider abstraction | MEDIUM | v4.5 Phase B | Protocol + Ollama/Qwen default + template fallback |
| **D6** | Organizational specificity test | MEDIUM | v5.0 | Cross-trained systems prove learning is firm-specific |
| **D7** | S2P validation walkthrough | MEDIUM | v5.0 | Design check that all abstractions work for second domain |

### Complete Gap Registry — Current State

**Critical (must address for MVP):**

| ID | Gap | Status | Version | Owner |
|---|---|---|---|---|
| GAP-1 | No simulation mode | Phase A (SIM-1 through SIM-4) | v4.5 | SOC |
| GAP-2 | No ATT&CK | Phase A (SIM-4) | v4.5 | SOC |
| GAP-3 | Limited alert corpus | Phase A (SIM-3) | v4.5 | SOC |
| GAP-5 | No cross-graph discovery | Phase C (gated) | v4.5 | GAE + SOC |
| D2 | Institutional Judgment metrics | Designed | v4.5 (partial) + v5.0 | GAE + SOC |
| D3 | Domain schema format | Designed | v4.5 (design) + v5.0 | GAE |

**High (product credibility):**

| ID | Gap | Status | Version | Owner |
|---|---|---|---|---|
| GAP-4 | No investigation narrative | Phase B (NAR-1/NAR-2) | v4.5 | SOC |
| A1 | Confirmation bias | Measured v4.5, fixed v5.0 | v4.5 + v5.0 | GAE |
| A2 | Uniform temporal decay | GAE preamble | v4.5 | GAE |
| H4 | Decision economics | ECON-1 | v5.0 | SOC |
| H5 | Data realism | SEED-2 | v5.0 | SOC |
| H6 | Evaluation ground truth | EVAL-1 (format designed) | v5.0 | GAE + SOC |
| E1 | Engine API surface | ENG-1 | v5.0 | GAE |
| E2 | Dependency enforcement | ENG-1 lint | v5.0 | GAE |
| D5 | NarrativeProvider abstraction | Phase B | v4.5 | SOC |

**Medium (platform maturity):**

| ID | Gap | Status | Version | Owner |
|---|---|---|---|---|
| E3 | Example domain | ENG-2 | v5.0 | GAE |
| E4 | Engine test suite | Follows ENG-1 | v5.0 | GAE |
| E5 | Engine documentation | GAE Users Guide | v5.0 | GAE |
| D1 | Ablation framework | Designed | v5.0 | GAE |
| D4 | ci-platform extraction | Planned | v5.0 | Platform |
| D6 | Organizational specificity test | Designed | v5.0 | GAE + SOC |
| D7 | S2P validation walkthrough | Planned | v5.0 | Platform |
| TD-026 | Audit/GAE sync on reset | Pre-SIM-1 | v4.5 | SOC |

**Deferred (v5.5+):**

| ID | Gap | Status | Version | Owner |
|---|---|---|---|---|
| A3 | Cross-graph quadratic scaling | Known solution (domain clustering) | v7.0 | GAE |
| A4 | False discovery propagation | Known solution (provisional dimensions) | v5.5 | GAE |
| B1 | Ground truth noise propagation | Experiment needed | v5.5 | GAE |
| B2 | Weight learning × artifact evolution interaction | Experiment needed | v5.5 | GAE |
| B3 | Embeddings at scale (revisit) | v4.5 Phase C initial test, v5.5 holistic revisit | v5.5 | GAE |
| C1 | Ontology drift × weight learning | Known solution (monitoring + pause) | v6.0 | Platform |
| C2 | Discovery expansion × eval timing | Known solution (W shape lock) | v6.0 | Platform |
| C3 | Autonomy × confirmation bias | Known solution (delayed validation) | v6.0 | Platform |
| H1 | Promotion pipeline concentration | Standalone module | v5.5 | Platform |
| H2 | Embedding sophistication | Multi-scale + hybrid | v5.5-v6.5 | GAE |
| H3 | Autonomy cluster | Graduated autonomy | v6.0 | SOC |

---

## Documents That Need Updating

| Document | Current | Target | Priority | Key Changes |
|---|---|---|---|---|
| `gae_design_v5` | v5 | **v6** | **1st** | CalibrationProfile, per-factor decay, evaluation framework, embedding provider protocol, v4.5 GAE preamble prompts |
| `soc_copilot_design_v1` | v1 | **v2** | **2nd** | v4.5 phases rewritten (A-C + GAE preamble), Phase D removed, NarrativeProvider, reset semantics, no INOVA at v4.5 |
| `ci_platform_design_v1` | v1 | **v2** | **3rd** | Timeline updated, v5.0 first code, minimal v4.5 scaffolding TBD from v5.0 design |
| `technology_portfolio_map_v1_3` | v1.3 | **v1.4** | **4th** | Version reassignments (ATT&CK → v4.5, CalibrationProfile → v4.5, INOVA → v6.0) |
| `soc_copilot_roadmap_v5` | v5 | **v6** | **5th** | v4.5 redesigned, v5.0 redefined, Docker → v5.5, old v5.0 → v6.0 |
| `gap_analysis` | v1.1 | **v2** | **6th** | New gaps D1-D7, version shifts, B3 threshold confirmed at 0.2 |
| `backlog_v20` | v20 | **v21** | **7th** | v5.0 section added, GAE preamble added, Phase D removed, priority queue updated |
| `session_continuation_v18` | v18 | **v19** | **8th** | Updated plan, new decisions, GAE preamble prompts |

---

*Design Decisions v1 | March 1, 2026*
*8 issues resolved. 7 new gaps identified (D1-D7). Gap registry: 30+ items tracked across 4 severity levels.*
*"The moat is the graph, not the model. The product proves it."*
