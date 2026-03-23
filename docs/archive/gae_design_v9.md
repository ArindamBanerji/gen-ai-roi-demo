# Graph Attention Engine — Design & Architecture v9

**Date:** March 12, 2026
**Version:** 9.2 (v9.1 + ProfileScorer.update() bug fix — gt_action_index dual push/pull; 251 tests)
**Date:** March 15, 2026: ProfileScorer.update() bug fix — gt_action_index parameter added; dual push/pull replaces push-all; SHIFT-2 validated.
**Status:** v5.0 TAGGED. Scoring architecture SETTLED. All Phase 1–6 prompts executed. Open-source release planned for v5.5.
**Repository:** graph-attention-engine (standalone, numpy-only, Apache 2.0)
**Scope:**
- v4.1 (Tiers 1-3 foundation)
- v4.5 (CalibrationProfile, per-factor decay)
- **v5.0 COMPLETE** (ProfileScorer + OracleProvider + Evaluation + Judgment + Ablation + Users Guide — 251 tests post-WIRING-1 + bug fix)
- v5.5 (Tiers 4-5 embedding + attention infrastructure + open-source release target)
- v7.0 (Level 2: GraphAttentionBridge — designed, not implemented)
- v8.0 (Level 3: Cross-Domain Discovery — designed, not implemented)

**Companion repos:**
- ci-platform (UCL, agents, event bus, governance — Apache 2.0)
- soc-copilot (SOC domain expertise — proprietary)
- cross-graph-experiments (25 experiments: 9 bridge + 5 validation + 11 OP/synthesis, 100+ charts)

**Supersedes:** gae_design_v7, v8, v8.1, v8.2, v8.3 + bridge_layer_design_v1 + bridge_experiments_design_v1.

---

> **Changes from v8.3 → v9 (March 9, 2026 — v5.0 complete):**
>
> (1) **§10 completely rewritten.** All GAE v5.0 Phase 6 modules now exist as live code with tests. Interfaces reflect actual implemented APIs, not design specs. Replaces the "Tier 0–1 prompt descriptions" with the actual shipped API contract.
> (2) **New §10.6: OracleProvider.** oracle.py is the ground-truth interface for the evaluation pipeline. Three implementations: OracleProvider protocol, GTAlignedOracle, BernoulliOracle. This module was not in v8.3.
> (3) **New §10.7: Evaluation.** evaluation.py: EvaluationScenario, run_evaluation(), EvaluationReport, compute_ece(). Actual field names confirmed from implementation.
> (4) **New §10.8: Judgment.** judgment.py: compute_judgment(), JudgmentResult, three confidence tiers (high ≥0.80, medium ≥0.50, discovery). Signed function signature confirmed.
> (5) **New §10.9: Ablation.** ablation.py: run_ablation(), AblationReport, factor importance ranking. accuracy_drop > 0 means factor helps.
> (6) **§10.4 ScoringResult field correction.** Field is `.probabilities` not `.scores`. Confirmed from implementation and users_guide.md.
> (7) **New §15: Open-Source Strategy.** First-class section on what it takes to make GAE a successful open-source project — not just "Apache 2.0 license" but README, contributing guide, PyPI, CI, issue templates, community, and the "why open-source" strategic argument.
> (8) **§17 (What's Built vs Next) substantially rewritten.** v5.0 marked COMPLETE with test counts. v5.5 next steps expanded. Phase 6 completion status added.
> (9) **§18 repo structure updated.** All v5.0 files marked ✅. v5.5 and v7/v8 targets clarified.
> (10) **Test count updated.** 187 (v4.1) → 211 (v5.0-alpha: Phase 1) → 235 (v5.0 Phase 6 GAE) → **243 (v5.0 TAGGED, post-SOC fixes).**
> (11) **Realistic accuracy numbers integrated.** math_synopsis_v6 50-seed validated numbers now present alongside synthetic numbers. Both are correct and serve different purposes.
>
> **v9.1 additions (March 12, 2026 — post-tag WIRING-1):**
>
> (12) **CentroidUpdate dataclass added.** `ProfileScorer.update()` now returns `CentroidUpdate` with fields `centroid_delta_norm`, `category_index`, `action_index`, `category_name`, `action_name`, `decision_count`, `gt_delta_norm` (v9.2: added). Enables the `centroid_delta_norm` wiring in SOC triage endpoint and Tab-3 centroid delta display.
> (13) **freeze()/unfreeze() added.** `ProfileScorer.freeze()` halts centroid updates (returns `CentroidUpdate` with delta_norm=0.0 from `update()`). `ProfileScorer.unfreeze()` resumes. `LearningState` exposes frozen status. Test count: 243 → **246**.
>
> **v9.2 additions (March 15, 2026 — ProfileScorer.update() bug fix):**
>
> (15) **gt_action_index parameter added to update().** Prior implementation pushed ALL action centroids away from f when correct=False, including the ground truth centroid. Fixed: only the predicted (wrong) action is pushed away; ground truth action is pulled toward f. `gt_action_index: Optional[int] = None` added to signature. Callers without gt_action_index fall back to push-only with DeprecationWarning. Test count: 246 → **251**.
> (16) **CentroidUpdate.gt_delta_norm field added.** `CentroidUpdate` dataclass gains `gt_delta_norm: float = 0.0` — the L2 norm of the ground truth centroid pull vector. Zero when correct=True or when gt_action_index is not provided.
> (17) **SHIFT-2 experiment validates fix.** Learning lift was -9.0% before fix, +2.7% after fix (noise=0, δ=0.10, warmup=1000). 24 conditions × 50 seeds. Positive lift confirmed when signal exists (δ>0).
> (14) **Two-level institutional judgment framing added (§5, §9).** ProfileScorer is explicitly named as **Level 1 — Decision Intelligence** (what to decide; centroids μ; slow-moving, months). AgentEvolver (in SOC copilot) is **Level 2 — Deployment Intelligence** (how to operate; variant selection; moderate, weeks). GAE owns Level 1 only. Level 2 is implemented in the domain copilot layer.

---

## 1. Requirements: Why This Document Exists

### 1.1 The Problem

The SOC Copilot's published math blog describes a precise computational system: cross-graph attention (Eq. 6), weight learning (Eq. 4b), entity embeddings (Eq. 5), discovery extraction (Eq. 8a-8c), and scoring matrices (Eq. 4). The demo codebase implements a subset. The GAE is the computational substrate that implements the math — and must eventually stand alone as an open-source library that others can use to build their own compounding intelligence systems.

### 1.2 Requirements

**R1 — Equation traceability.** Every equation maps to exactly one function in exactly one file.

**R2 — Causal closure.** Outputs of one cycle become inputs to the next. Six causal connectors (§7) wire computation into closed loops.

**R3 — Event-driven architecture.** Three causal loops at different timescales trigger each other via events.

**R4 — Factor vector preservation.** Decision nodes store f(t) from the ORIGINAL decision. Recomputed f at outcome time would corrupt the learning signal.

**R5 — Dynamic dimensionality.** Profile centroids μ accommodate new factor dimensions via profile augmentation (adding dimensions to μ), not W expansion. EXP-D2 found zero significant factor interactions in SOC data, so augmentation is unlikely in practice — R5 is preserved for generality.

**R6 — Technology selection justification.** NumPy for v5.0 (24 multiply-adds per scoring). Backend-swappable for future scale.

**R7 — Single-concern prompt decomposition.** Build decomposed into single-file, tightly-scoped prompts. Each prompt is one concern.

**R8 — Accumulation channel completeness.** Every graph mutation produces a write-back read by downstream computation.

**R9 — Open-source API stability.** Public classes versioned and backward-compatible. Engine never imports from product code (P12). API surface is the contract with the open-source community — changes are breaking.

**R10 (NEW v9) — Self-contained documentation.** The library must be fully understandable without reading the SOC copilot or the math blog. A new engineer working on a procurement domain must be able to use GAE from README + users_guide.md alone.

---

## 2. Technology Analysis

### 2.1 What Transformer Attention Is

Core insight preserved: HuggingFace BertSelfAttention is 5 lines of math + 245 lines of infrastructure. We take the math, build our own infrastructure.

### 2.2 What Changed: The Kernel

The v7 analysis mapped Eq. 4 to transformer dot-product attention. **The experiments proved this mapping is wrong for our data.**

| Component | v7 Mapping | v9 Mapping (Validated) |
|---|---|---|
| Queries (Q) | f · W (linear projection) | f (factor vector directly) |
| Keys (K) | W rows | μ[c,a,:] (profile centroids) |
| Similarity | Q · K^T (dot product) | **−‖f − μ[c,a,:]‖² (L2 distance)** |
| Routing | Shared W across categories | **μ[c,:,:] per category (MoE)** |
| Learning | Hebbian W update | **Centroid pull/push** |

**Why this matters for open-source positioning:** Most graph ML libraries use dot-product attention (GNNs, transformers). GAE uses distance-kernel attention. This is a genuine technical differentiation — not just a parameter choice. EXP-C1 (36.89pp gap between L2 and dot product on the same data) makes this claim defensible to a technical audience.

### 2.3 Transformer Parallel (the "Rosetta Stone")

```
Transformer:  tokens attend to tokens  via dot-product similarity
GAE:          graph domains attend to  via distance-kernel similarity
              profile prototypes       to factor vectors
              
MoE parallel: category c = expert head selector (externally defined)
              μ[c,:,:] = expert parameters
              f = the query routed to expert c
```

This parallel makes GAE legible to engineers who know transformers. Use it in README, talks, and the math blog update.

---

## 3. Architectural Principles

*P1–P12 unchanged from v7. P13–P16 added in v8. Reproduced for completeness.*

| # | Principle | Implication |
|---|---|---|
| P1 | Exact equation traceability | One equation → one function → one file |
| P2 | Causal closure | Every output is someone's input |
| P3 | Event-driven decoupling | Loops communicate via events, not direct calls |
| P4 | Factor preservation | f(t) stored at decision time, never recomputed |
| P5 | Domain-agnostic engine | SOC logic cannot live in GAE |
| P6 | Technology justification | Every technology choice is documented |
| P7 | Prompt decomposition | One concern per Claude Code prompt |
| P8 | Accumulation completeness | Every graph mutation has a write-back |
| P9 | API stability | Breaking changes require major version bump |
| P10 | Separation of scoring and learning | score() never updates μ; update() never scores |
| P11 | CalibrationProfile as domain contract | Hyperparameters are domain choices, not engine choices |
| P12 | One-way dependency | GAE → zero. Domain copilot → GAE. Never reverse. |
| P13 | Profiles as first-class constituents | μ is the model, not W |
| P14 | Experimental evidence for architecture | No architecture decision without experimental basis |
| P15 | Warm start essential | DomainConfig MUST provide initial profiles |
| P16 | Synthesis firewall | update() has NO synthesis parameter — by design, forever |

---

## 4. Experimental Foundation

### 4.1 Experiment Summary (25 total)

| Group | Count | Key Findings |
|---|---|---|
| Bridge (EXP-5, A, A2, B1, C1, D1, D2, E1, E2) | 9 | G falsified; dot product root cause; L2=97.89%; profiling approach validated |
| Validation (V1A, V1B, V2, V3A, V3B) | 5 | b=2.11; LayerNorm required; clipping required; XGBoost beaten; τ=0.1 |
| OP/Synthesis (S1-S3, OP1-OP4, others) | 11 | GATE-OP PASSED; τ_mod rejected; Loop 2/4 firewall validated; operative window λ∈[0.5, 0.6] |

### 4.2 Key Validated Numbers

| Metric | Value | Condition | Source |
|---|---|---|---|
| Zero-learning accuracy | 97.89% | Synthetic centroidal data, GT profiles | EXP-C1 |
| With-learning accuracy | 98.2% | Synthetic, warm-start, noise-free oracle | EXP-B1 |
| **Realistic static accuracy** | **71.7%** [71.4%, 71.9%] | **50 seeds, realistic distributions, combined categories** | **math_synopsis_v6** |
| **Realistic at decision 1,000** | **78.9%** [78.1%, 79.6%] | **50 seeds, realistic distributions** | **math_synopsis_v6** |
| **Auto-approve accuracy (≥0.90)** | **90.7%** [90.1%, 91.2%] | **50 seeds, realistic distributions** | **math_synopsis_v6** |
| Auto-approve coverage | 11.5% ± 0.70% | Combined realistic, 50 seeds | math_synopsis_v6 |
| Calibration ECE | 0.036 at τ=0.1 | Synthetic | V3B |
| L2 vs XGBoost | 94.78% vs 92.24% | Synthetic held-out data | V3A |
| Domain scaling exponent | b=2.11, CI [2.09, 2.14] | Simulation, R²=0.9999 | V1A |
| Max scale tested | 20×10×20 (4,000 params) | Synthetic, GT profiles | EXP-E2 |

**Note on the two accuracy regimes:** The 97.89% / 98.2% numbers are centroidal synthetic (ground-truth profiles, oracle-initialized centroids). The 71.7% / 78.9% numbers are realistic (profiles estimated from domain knowledge, realistic factor distributions, 50 seeds). Both are correct — they measure different things. The centroidal numbers validate the scoring mechanism. The realistic numbers are the honest product claim. **Never mix these in the same sentence.**

### 4.3 Architecture Decisions Made by Experiments

| Decision | Evidence | Status |
|---|---|---|
| L2 as default kernel | EXP-C1: 36.89pp gap | Settled |
| Pluggable kernels | EXP-E1: L2 wins 2/3 scenarios | Settled |
| Profile centroids (not W matrix) | EXP-C1, EXP-B1 | Settled |
| G (gating matrix) eliminated | EXP-A: +0.01pp | Settled |
| Count-based decay (not Ψ) | EXP-B1: natural phase behavior | Settled |
| τ = 0.1 (not 0.25) | V3B: ECE 0.19→0.036 | Settled |
| Clipping to [0,1] required | V2: escape at dec 6-12 | Settled |
| τ_modifier rejected | OP series: ECE +0.138 degradation | Settled, permanent |
| Loop 2/4 firewall | EXP-S3: Frobenius 0.0028 | Settled, permanent |
| Operative window λ∈[0.5, 0.6] | EXP-OP2 | Settled |
| Checkpoint/rollback required | EXP-OP2: 35% never recover | TD-033 requirement |
| LayerNorm required (Level 2) | V1B: 2.9M× norm explosion | Settled, permanent |
| γ is estimated (~1.5) | Not yet measured | EXP-G1 pending |

---

## 5. The Ontological Architecture

*(Unchanged from v8 §5. Reproduced for completeness.)*

**The deepest conceptual insight:** Profile centroids are compiled ontologies.

A domain ontology statement — "for insider_behavioral alerts, escalate when asset_criticality is high and pattern_history is low" — is compiled into a point in n_f-dimensional factor space:

```
μ[insider_behavioral, escalate, :] = [0.35, 0.85, 0.60, 0.15, 0.50, 0.30]
                                       ↑      ↑                 ↑
                                    travel  asset           pattern
                                    (low)  (HIGH)           (LOW)
```

Three consequences:

1. **The math does not understand the domain.** ProfileScorer computes pure L2 distance. It works identically for SOC alerts, procurement decisions, and financial compliance — only the centroid values change. This is why GAE can be domain-agnostic.

2. **Learning is geometric, not symbolic.** Verified outcomes pull/push centroids toward observed patterns. After 1,000 decisions, centroids have drifted from expert opinion toward empirical reality.

3. **The meta-graph is the moat.** Evolved centroids cannot be copied without running the decisions that evolved them. Initial centroids are opinion. Evolved centroids are evidence.

**Three-layer design:**

```
Layer 1: Domain Ontology (expert knowledge)
    → compiled into →
Layer 2: Meta-Graph (profile centroids μ — "compiled ontology")
    → scored via →
Layer 3: Mathematical Engine (ProfileScorer, distance kernel)
```

**Two levels of institutional judgment — GAE owns Level 1:**

ProfileScorer implements **Level 1 — Decision Intelligence**: the system learns *what to decide*. Per-category profile centroids μ[c,a,:] encode verified organizational judgment as geometric objects. Centroid updates from verified outcomes (Eq. 4b-final) are the mechanism. Slow-moving (months, hundreds of decisions). EXP-C1: 97.89% zero-learning accuracy; EXP-B1: 98.2% warm-start.

**Level 2 — Deployment Intelligence** (AgentEvolver) is implemented in the domain copilot layer, not in GAE. It learns *how to operate* — which prompt variants, framing, and context structure work in this deployment. Moderate-moving (weeks). GATE-OP confirmed the operative window (λ=0.5, p=0.0008). The GAE `bridge.py` (v7.0) and `discovery_engine.py` (v8.0) are **Level 2/3 architecture** in the cross-domain enrichment sense — distinct from the Decision/Deployment Intelligence naming. Both namings are in use; context disambiguates.

**The critical separation** (P16, permanent): `update()` has NO synthesis parameter. μ learns from verified operational experience only. Level 2 Deployment Intelligence signals never contaminate Level 1 centroid evolution. Architecturally enforced, not configurable.

---

## 6. Package Structure — Three-Repository Architecture

```
graph-attention-engine  (Apache 2.0 — THIS REPO)
    Pure math, numpy-only, zero external dependencies
    Exports: ProfileScorer, ScoringResult, KernelType,
             CalibrationProfile, FactorComputer, LearningState,
             OracleProvider, GTAlignedOracle, BernoulliOracle,
             EvaluationScenario, run_evaluation, EvaluationReport,
             compute_judgment, JudgmentResult,
             run_ablation, AblationReport
         ↑
ci-platform             (Apache 2.0)
    UCL, agents, event bus, governance, DomainConfig protocol
         ↑
soc-copilot             (Proprietary)
    SOC domain expertise, FactorComputer implementations,
    SOCDomainConfig, Neo4j seed data, connectors, UI
```

**The one-way dependency (P12) is the architectural contract.** GAE has zero imports from ci-platform or any domain copilot. If a GAE module needs something from a domain, it must be passed in as a parameter (e.g., CalibrationProfile). This is what makes GAE publishable as an independent open-source library.

---

## 7. Causal Architecture: Three Loops, Four Connectors

### 7.1 Four Causal Loops

```
╔══════════════════════════════════════════════════════════════════╗
║  LOOP 1: FAST LOOP (per-alert, seconds) — LIVE in v5.0          ║
║                                                                  ║
║  Alert → FactorComputers → f (1×n_f)                            ║
║            ↑ reads graph           ↓                             ║
║            │          SituationAnalyzer → category c            ║
║            │                       ↓                             ║
║            │          ProfileScorer.score(f, c)                  ║
║            │          Eq. 4-final: softmax(-K(f, μ[c,:,:])/τ)   ║
║            │                       ↓                             ║
║            │          ScoringResult: action, confidence,         ║
║            │          probabilities, distances, factor_vector    ║
║            │                       ↓                             ║
║            │          compute_judgment() → JudgmentResult        ║
║            │                       ↓                             ║
║            │          Human/Auto decision → Outcome              ║
║            │                       ↓                             ║
║            │          ProfileScorer.update(f, c, a, correct)     ║
║            │          Eq. 4b-final: centroid pull/push, clip     ║
║            │                       ↓                             ║
║            │          Graph Write-Back (Decision + Outcome)      ║
║            │                       │                             ║
║            └───────────────────────┘                             ║
║                                                                  ║
║  CLOSURE: Graph is richer. Profiles are refined.                 ║
╚══════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════╗
║  LOOP 2: SLOW LOOP (periodic, hours/daily) — v5.5 target        ║
║  Entity embeddings + cross-graph attention sweep                 ║
║  GraphAttentionBridge.sweep() — designed in §11                  ║
╚══════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════╗
║  LOOP 3: META LOOP (rare, structural) — v6.0+                   ║
║  Drift detection → profile recalibration → ontology update       ║
╚══════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════╗
║  LOOP 4: SYNTHESIS LOOP (external intelligence) — PROPOSAL       ║
║  GATED BY: GATE-M (math), GATE-D (pipeline), GATE-V (decisions) ║
║                                                                  ║
║  External claims → σ[c,a] → Eq. 4-synthesis                     ║
║  P(a|f,c,σ) = softmax(-(‖f-μ‖²+λ·σ[c,a])/(τ))                  ║
║  λ∈[0.5,0.6] operative window (GATE-OP passed, p=0.0008)        ║
║                                                                  ║
║  ARCHITECTURAL FIREWALL (PERMANENT):                             ║
║    ProfileScorer.update() has NO synthesis parameter.            ║
║    μ is NEVER updated using σ. σ flows through score() only.     ║
║    Temperature τ=0.1 REGARDLESS of synthesis state.              ║
║    τ_modifier permanently rejected (ECE +0.138 degradation).     ║
╚══════════════════════════════════════════════════════════════════╝
```

### 7.2 Four Causal Connectors

**Connector 1 — Graph → Factors:** FactorComputers traverse Neo4j → produce f ∈ [0,1]^n_f

**Connector 2 — Factors + Profiles → Decision:**
- Input: f (factor vector), μ[c,:,:] (category centroid slice), τ, actions
- Output: ScoringResult with action, confidence, probabilities, distances
- Mechanism: Eq. 4-final — `softmax(-K(f, μ[c,a,:]) / τ)` for each action a
- Kernel K: L2 default, pluggable via KernelType

**Connector 3 — Decision + Outcome → Profile Update:**
- Trigger: verified outcome (human review or auto-approve)
- Mechanism: Eq. 4b-final — centroid pull (correct) / push (incorrect), count-based decay, clip to [0,1]
- Asymmetry: penalty_ratio (20:1 SOC default) via CalibrationProfile

**Connector 4 — Level 1 Data Hooks → Level 2/3:**
- DecisionRecord, OutcomeRecord, ProfileSnapshot written by every domain
- These are the substrate Level 2 (GraphAttentionBridge) reads
- See §11.4 for the full specification

---

## 8. Tier 1 — Factor Protocol & Assembly (`gae/factors.py`)

**FactorComputer Protocol** (domain-agnostic):

```python
class FactorComputer(Protocol):
    """
    Computes a single normalized factor value [0,1] from graph data.
    Implementations live in domain repos (e.g., SOC TravelMatchFactor).
    GAE defines the interface only.
    """
    @property
    def factor_name(self) -> str: ...
    
    async def compute(self, alert: AlertContext, graph: GraphClient) -> float:
        """Returns value in [0.0, 1.0]. Never raises — returns 0.5 on error."""
        ...

def assemble_factor_vector(
    computers: List[FactorComputer],
    alert: AlertContext,
    graph: GraphClient,
) -> np.ndarray:
    """
    Runs all FactorComputers, returns f of shape (n_factors,).
    Order matches the order of computers list — must match centroid dimension order.
    """
```

**Important:** f is the QUERY in Eq. 4-final. The factor vector is not the answer — it is the question the engine scores against μ. The semantics: "how close is THIS ALERT to what each action looks like for this category?"

---

## 9. Tier 2 — Profile-Based Scoring (`gae/profile_scorer.py`)

**Role in the two-level architecture:** ProfileScorer is **Level 1 — Decision Intelligence**. It learns *what to decide* by maintaining per-category profile centroids that encode verified organizational judgment as geometry. See §5 for the full two-level framing. This section specifies the implementation contract.

### 9.1 Equation

**Eq. 4-final:**
```
P(a | f, c) = softmax(-K(f, μ[c,a,:]) / τ)

where K(f, μ[c,a,:]) = ‖f − μ[c,a,:]‖²   (L2 default)
```

Three first-class constituents:
- **f** (query): factor vector, shape (n_f,), produced by FactorComputers
- **μ** (keys): profile centroids, shape (n_c × n_a × n_f), compiled ontology
- **c** (router): category index, from SituationAnalyzer (MoE head selector)

### 9.2 KernelType Enum

```python
class KernelType(Enum):
    L2 = "l2"                    # Default. -||f - μ||². 97.89% validated.
    MAHALANOBIS = "mahalanobis"  # Scale-invariant. Use for mixed-scale factors.
    COSINE = "cosine"            # Shape-based. Use for pre-normalized embeddings.
    DOT = "dot"                  # WARNED. 61% on [0,1] data. Legacy/comparison only.
```

**Kernel selection guidance** (from docs/users_guide.md):
- All factors in [0,1] → L2 (default). This is the validated configuration.
- Mixed scales (some 0-1, some 0-100) → Mahalanobis.
- Pre-normalized embeddings → Cosine.
- Never use Dot on [0,1] data — EXP-C1 shows 61% accuracy vs L2's 97.89%.

### 9.3 ScoringResult

```python
@dataclass
class ScoringResult:
    """Output of Eq. 4-final. All fields are populated on every score() call."""
    action_probabilities: np.ndarray  # shape (n_a,) — softmax output
    selected_action: str              # argmax action name
    confidence: float                 # max probability value
    distances: np.ndarray             # raw distance values (before softmax), shape (n_a,)
    factor_vector: np.ndarray         # f — preserved per R4, shape (n_f,)
    category_index: int               # c — which profile set was used
    temperature: float                # τ used (always 0.1 in production)
    kernel: str                       # which kernel was used
    probabilities: np.ndarray         # alias for action_probabilities — primary field name
    
    # NOTE: The primary field name is .probabilities, not .scores.
    # This is confirmed in docs/users_guide.md §5.2.
```

### 9.4 ProfileScorer Interface

```python
class ProfileScorer:
    def __init__(
        self,
        mu: np.ndarray,          # shape (n_c, n_a, n_f) — MUST match factor order
        actions: List[str],      # action names, length n_a
        tau: float = 0.1,        # V3B validated. NEVER use 0.25.
        kernel_type: KernelType = KernelType.L2,
        calibration: Optional[CalibrationProfile] = None,
    ) -> None: ...

    def score(
        self,
        f: np.ndarray,           # shape (n_f,) or (1, n_f)
        category_index: int,     # from SituationAnalyzer
        synthesis: None = None,  # ALWAYS None in v5.0. Loop 4 PROPOSAL only.
    ) -> ScoringResult: ...

    def update(
        self,
        f: np.ndarray,           # original factor vector (R4 — never recomputed)
        category_index: int,
        action_index: int,
        correct: bool,           # was the recommendation correct?
        gt_action_index: Optional[int] = None,  # ground-truth action; required when correct=False
        # NOTE: NO synthesis parameter — Loop 2/4 firewall, permanent (P16)
    ) -> CentroidUpdate: ...

    def diagnostics(self) -> Dict[str, Any]:
        """
        Per-category centroid separation metrics.
        Returns: {
            'centroid_separation': np.ndarray (n_c × n_a × n_a),
            'min_separation': float,
            'converged': bool,
            'observation_counts': np.ndarray (n_c × n_a),
        }
        Centroid separation > 0.5 recommended for discriminative profiles.
        """
        ...

    def checkpoint(self) -> Dict:
        """
        Serialize centroid state for rollback (TD-033).
        Returns dict with mu, counts, timestamp.
        Required: checkpoint every 50 decisions when synthesis loop active.
        """
        ...

    def rollback(self, checkpoint: Dict) -> None:
        """Restore centroid state from checkpoint (TD-033)."""
        ...

    def reset_to_config(self, profile_config: Dict) -> None:
        """
        Reinitialize μ from DomainConfig profiles and zero counts.
        The migration path from deprecated ScoringMatrix state (TD-027).
        Never migrate W→μ — always reset to configured profiles.
        """
        ...

@classmethod
def build_profile_scorer(
    mu: np.ndarray,
    actions: List[str],
    calibration: Optional[CalibrationProfile] = None,
    kernel_type: KernelType = KernelType.L2,
) -> ProfileScorer:
    """Factory function. Preferred construction method for external code."""
    ...
```

### 9.5 Learning Equation

**Eq. 4b-final:**
```
Correct outcome:  μ[c,a,:] ← μ[c,a,:] + η(n)·(f − μ[c,a,:])      (pull predicted == GT)

Incorrect outcome (with gt_action_index — canonical):
  Push predicted (wrong) centroid away:
    μ[c, action_index, :]    -= η_neg(n)·(f − μ[c, action_index, :])
  Pull ground truth centroid toward f:
    μ[c, gt_action_index, :] += η(n)·(f − μ[c, gt_action_index, :])
  All other action centroids: unchanged.

Incorrect outcome (without gt_action_index — deprecated):
  Push predicted centroid only. Emits DeprecationWarning.

Where η(n) = η₀ / (1 + n·count_decay)   (count-based learning rate decay)

REQUIRED: all μ values clipped to [0, 1] after every update (V2 validated)
REQUIRED: τ = 0.1 always — never modified by synthesis or any other condition
CANONICAL: η_neg = 0.05 (symmetric with η). FORBIDDEN: η_neg=1.0 (ECE=0.49, catastrophic).
```

**When correct=False (with gt_action_index provided):**
Two centroid updates:
1. Push the PREDICTED (wrong) action's centroid away from f:
   μ[c, action_index, :] -= η_neg_eff · (f − μ[c, action_index, :])
2. Pull the GROUND TRUTH action's centroid toward f:
   μ[c, gt_action_index, :] += η_eff · (f − μ[c, gt_action_index, :])
All other action centroids are unchanged.

**When correct=False (without gt_action_index — deprecated):**
Push only the predicted action's centroid away. Emits DeprecationWarning.
Callers should always provide gt_action_index for proper learning.

**Bug fix note (March 15, 2026):** Prior to this fix, the correct=False branch pushed ALL
action centroids away from f, including the ground truth action. This caused centroid
degradation: every incorrect prediction made the correct centroid worse. The bug was
confirmed by SHIFT-2 experiment: learning lift was -9.0% before fix, +2.7% after fix
(at noise=0, delta=0.10, warmup=1000). The fix adds the gt_action_index parameter for
dual push/pull. See §9.6 for SHIFT-2 validation results.

**CentroidUpdate dataclass (v9.1+, extended v9.2):**
```python
@dataclass
class CentroidUpdate:
    centroid_delta_norm: float        # L2 norm of predicted centroid move
    category_index: int
    action_index: int
    category_name: str
    action_name: str
    decision_count: int
    gt_delta_norm: float = 0.0        # L2 norm of GT centroid pull. 0.0 when
                                      # correct=True or gt_action_index not provided.
```
When `ProfileScorer.frozen=True`, update() returns CentroidUpdate with
centroid_delta_norm=0.0 and gt_delta_norm=0.0 (no centroid movement).

**freeze()/unfreeze():**
- `freeze()`: blocks update() centroid movement but not score(). Sets frozen=True.
- `unfreeze()`: re-enables centroid updates. Sets frozen=False.
- When frozen, update() increments decision_count but returns CentroidUpdate with delta_norm=0.0.

### 9.6 SHIFT-2 Validation (March 15, 2026)

The corrected update rule was validated across 24 conditions
(3 noise rates × 2 prior shifts × 4 warmup levels, 50 seeds each):

| Condition | Accuracy lift (w=1000) | Coverage lift |
|---|---|---|
| noise=0.00, δ=0.10 | +2.7% | +3.7% |
| noise=0.05, δ=0.10 | +2.5% | -0.3% |
| noise=0.10, δ=0.10 | +1.5% | +0.4% |
| noise=0.00, δ=0.00 | -1.4% | -5.0% |

Learning is positive when there is signal to learn (δ>0). At δ=0 (circular generator,
μ₀ = μ_true), small negative lift is expected — centroids drift from an already-optimal
position. Noise (10%) is the remaining constraint on learning lift magnitude.

**Pre-fix baseline (push-all, same conditions):** noise=0, δ=0.10, w=1000 → -9.0% accuracy lift.
The fix converts a -9.0% degradation into a +2.7% improvement. Net delta: +11.7pp.

---

## 10. v5.0 Complete API Surface

### 10.1 Module Overview

All modules shipped in v5.0. 251 tests (post-WIRING-1 + gt_action_index fix). v0.5.0 tagged.

```
gae/
├── profile_scorer.py    ✅ ProfileScorer, ScoringResult, KernelType, WeightUpdate
├── calibration.py       ✅ CalibrationProfile (updated for profile parameters)
├── factors.py           ✅ FactorComputer protocol, assemble_factor_vector
├── learning.py          ✅ LearningState (delegates to ProfileScorer.update)
├── scoring.py           ✅ score_alert() DEPRECATED — forwards to ProfileScorer
├── oracle.py            ✅ OracleProvider, GTAlignedOracle, BernoulliOracle (NEW v5.0)
├── evaluation.py        ✅ run_evaluation, EvaluationScenario, EvaluationReport (NEW v5.0)
├── judgment.py          ✅ compute_judgment, JudgmentResult (NEW v5.0)
├── ablation.py          ✅ run_ablation, AblationReport (NEW v5.0)
├── convergence.py       ✅ Unchanged
├── contracts.py         ✅ Unchanged
├── primitives.py        ✅ Unchanged
├── events.py            ✅ Unchanged
├── store.py             ✅ Updated: ProfileScorer state persistence
├── types.py             ✅ Unchanged
├── embeddings.py        📋 Tier 4 (v5.5 target)
├── bridge.py            📋 Level 2 GraphAttentionBridge (v7.0 target)
└── discovery_engine.py  📋 Level 3 Cross-Domain Discovery (v8.0 target)
```

### 10.2 CalibrationProfile

```python
@dataclass
class CalibrationProfile:
    """Domain-configurable hyperparameters for the scoring and learning pipeline."""
    
    # Core (validated)
    temperature: float = 0.1             # V3B: ECE=0.036 at τ=0.1. Never use 0.25.
    penalty_ratio: float = 20.0          # SOC default. 5.0 for procurement.
    
    # Learning rates (in extensions dict for backward compat — will move to top-level v5.5)
    extensions: dict = field(default_factory=lambda: {
        "eta": 0.05,           # base learning rate (correct outcomes)
        "eta_neg": 0.05,       # base penalty rate (incorrect outcomes) — CANONICAL. NEVER use 1.0.
        "count_decay": 0.001,  # count-based decay: η(n) = η₀/(1 + n·count_decay)
        "kernel": "l2",        # default kernel type
    })
    
    # Per-factor decay (v5.5)
    decay_class_rates: dict = field(default_factory=lambda: {
        "permanent": 0.0001, "standard": 0.001,
        "campaign": 0.003, "transient": 0.01,
    })
    
    # v7 backward compat (deprecated — used by ScoringMatrix only)
    learning_rate: float = 0.02          # DEPRECATED. Use extensions["eta"].
    
    # TODO v5.5: Add category_thresholds dict for per-category auto-approve thresholds
    # This enables 40%+ auto-approve coverage (v5.5-R1 from product_requirements_v1)
    # category_thresholds: dict = field(default_factory=dict)
```

**CalibrationProfile defaults:** tau=0.1, eta=0.05, eta_neg=0.05, decay=0.001.

**η_neg production constraint:** η_neg=0.05 is canonical for production (symmetric with η).
η_neg=1.0 is **FORBIDDEN** — produces catastrophic miscalibration (ECE=0.49, PROD-4b).
See soc_copilot_design_v5_6 §22.6 for the design decision record.

### 10.3 LearningState

```python
@dataclass
class LearningState:
    """
    Wraps ProfileScorer and manages the learning loop.
    Handles bootstrap calibration, rollback, and checkpoint.
    """
    profile_scorer: ProfileScorer        # THE scoring mechanism (TD-029)
    calibration: CalibrationProfile
    decision_history: List[WeightUpdate]
    
    def update(
        self,
        f: np.ndarray,
        category_index: int,
        action_index: int,
        correct: bool,
    ) -> Optional[WeightUpdate]:
        """
        Delegates to ProfileScorer.update().
        Records update to history (for GATE-R, EXP-G1).
        Returns WeightUpdate with delta_applied, centroid snapshot.
        """
        ...
    
    def bootstrap_calibrate(
        self,
        n_decisions: int = 1200,
        seed: int = 42,
    ) -> None:
        """
        Bootstrap warm-start: generate synthetic decisions from current μ.
        Converges centroids before real data arrives.
        SOC: 1,200 decisions, converged=True, drift=0.0097 confirmed.
        """
        ...
```

### 10.4 OracleProvider (`gae/oracle.py`) — NEW v5.0

```python
class OracleProvider(Protocol):
    """
    Ground-truth provider for evaluation scenarios.
    The oracle answers "what is the correct action for this (f, c) pair?"
    Used in run_evaluation() to compute accuracy against a known ground truth.
    """
    def get_correct_action(
        self,
        f: np.ndarray,
        category_index: int,
    ) -> OracleResult:
        """Returns the ground-truth action and confidence in that ground truth."""
        ...

@dataclass
class OracleResult:
    """Ground truth for a single scoring event."""
    correct_action_index: int
    correct_action_name: str
    ground_truth_confidence: float   # how certain is the oracle about this ground truth?

class GTAlignedOracle:
    """
    Ground-truth oracle aligned with profile centroids.
    Correct answer = argmin L2 distance from f to μ[c,:,:].
    This is the oracle used in all synthetic experiments (EXP-C1, EXP-B1).
    Achieves 97.89% zero-learning accuracy because scoring and oracle agree on geometry.
    """
    def __init__(self, mu: np.ndarray, actions: List[str]) -> None: ...

class BernoulliOracle:
    """
    Probabilistic oracle: each action correct with probability p_correct.
    Used to simulate imperfect feedback (noise robustness testing).
    EXP-B1 showed 98.1% accuracy maintained at 30% oracle noise.
    """
    def __init__(self, base_oracle: OracleProvider, p_correct: float = 0.7) -> None: ...
```

### 10.5 Evaluation (`gae/evaluation.py`) — NEW v5.0

```python
@dataclass
class EvaluationScenario:
    """
    A single (f, c) → ground_truth_action test case.
    Human-authored scenarios (EVAL-1-SOC: 36 SOC scenarios across all 6 categories).
    """
    name: str                        # "credential_access_singapore_login"
    description: str
    f: np.ndarray                    # factor vector, shape (n_f,)
    category_index: int              # SituationAnalyzer output for this scenario
    expected_action: str             # ground truth action name
    expected_action_index: int

@dataclass
class EvaluationReport:
    """Output of run_evaluation()."""
    accuracy: float                  # fraction correct
    per_category_accuracy: Dict[str, float]
    confusion_matrix: np.ndarray     # shape (n_a, n_a)
    ece: float                       # Expected Calibration Error (compute_ece())
    n_scenarios: int
    scenarios_by_outcome: Dict[str, List[str]]  # "correct"/"incorrect" → scenario names

def run_evaluation(
    profile_scorer: ProfileScorer,
    scenarios: List[EvaluationScenario],
    oracle: OracleProvider,
    learn: bool = False,             # if True: call update() after each score
) -> EvaluationReport:
    """
    Evaluate ProfileScorer against provided scenarios.
    When learn=True: simulates online learning — each decision updates μ.
    """
    ...

def compute_ece(
    probabilities: np.ndarray,      # shape (n_scenarios, n_a)
    correct_indices: np.ndarray,    # shape (n_scenarios,)
    n_bins: int = 10,
) -> float:
    """
    Expected Calibration Error.
    V3B validated: ECE=0.036 at τ=0.1 (well-calibrated).
    ECE=0.19 at τ=0.25 (poorly calibrated — 5× worse).
    """
    ...
```

### 10.6 Judgment (`gae/judgment.py`) — NEW v5.0

```python
@dataclass
class JudgmentResult:
    """
    Human-readable explanation of a scoring decision.
    Bridges the gap between raw ScoringResult and analyst-facing explanation.
    """
    action: str                      # selected action
    confidence: float                # confidence value
    confidence_tier: str             # "high" / "medium" / "discovery"
    top_factors: List[Tuple[str, float]]  # [(factor_name, value), ...] sorted by influence
    rationale: str                   # plain-English explanation template
    should_auto_approve: bool        # confidence >= auto_approve_threshold
    centroid_distance: float         # L2 distance to winning centroid
    margin: float                    # confidence − second-highest probability

def compute_judgment(
    scoring_result: ScoringResult,
    f: np.ndarray,
    mu: np.ndarray,
    category_index: int,
    factor_names: List[str],
    actions: List[str],
    auto_approve_threshold: float = 0.90,
) -> JudgmentResult:
    """
    Compute human-readable judgment from scoring result.
    
    Confidence tiers:
        high:      confidence >= 0.80 (system recommends; analyst can accept quickly)
        medium:    confidence >= 0.50 (system suggests; analyst should review)
        discovery: confidence <  0.50 (system uncertain; escalate to human review)
    """
    ...
```

### 10.7 Ablation (`gae/ablation.py`) — NEW v5.0

```python
@dataclass
class AblationReport:
    """Output of run_ablation()."""
    factor_importance: Dict[str, float]    # factor_name → accuracy_drop when removed
    full_accuracy: float                   # baseline accuracy with all factors
    per_factor_accuracy: Dict[str, float]  # accuracy without each factor
    top_factors: List[str]                 # sorted by importance (most important first)
    dead_factors: List[str]                # accuracy_drop <= 0 (removing helps or neutral)

def run_ablation(
    profile_scorer: ProfileScorer,
    scenarios: List[EvaluationScenario],
    factor_names: List[str],
) -> AblationReport:
    """
    Leave-one-factor-out ablation study.
    
    For each factor i:
        1. Zero out dimension i in every scenario's f
        2. Re-evaluate with ProfileScorer
        3. accuracy_drop = full_accuracy − accuracy_without_factor_i
        4. accuracy_drop > 0 → factor helps
        5. accuracy_drop <= 0 → factor is a "dead factor" (neutral or harmful)
    
    Note: EXP-D2 found 0 significant factor interactions in SOC data.
    Ablation is therefore independent-factor analysis, not interaction study.
    """
    ...
```

### 10.8 Public API (`gae/__init__.py`)

```python
# All symbols exported from gae/__init__.py as of v5.0
from gae import (
    # Core scoring
    ProfileScorer,
    ScoringResult,
    KernelType,
    WeightUpdate,
    build_profile_scorer,
    
    # Configuration
    CalibrationProfile,
    
    # Factor protocol
    FactorComputer,
    assemble_factor_vector,
    
    # Learning
    LearningState,
    
    # Oracle
    OracleProvider,
    GTAlignedOracle,
    BernoulliOracle,
    OracleResult,
    
    # Evaluation
    EvaluationScenario,
    run_evaluation,
    EvaluationReport,
    compute_ece,
    
    # Judgment
    compute_judgment,
    JudgmentResult,
    
    # Ablation
    run_ablation,
    AblationReport,
    
    # Deprecated (remove at v6.0)
    # score_alert,  # Use ProfileScorer.score() instead
)
```

**Verification:**
```python
python -c "from gae import ProfileScorer, KernelType, OracleProvider, run_evaluation, compute_judgment, run_ablation"
# Must succeed with no errors.
```

---

## 11. Level 2/3 — Design Specification (v7/v8 Targets)

*(Unchanged from v8.3 §11. Reproduced in brief. Full specification in v8.3.)*

### 11.1 Tier 4 — Entity Embeddings (`gae/embeddings.py`, v5.5)

EmbeddingProvider protocol. Two implementations: PropertyEmbedding (linear projection), TransformerEmbedding (sentence transformer). These are the inputs to Level 2.

### 11.2 Level 2 — GraphAttentionBridge (`gae/bridge.py`, v7.0 target)

Cross-graph attention enrichment. Given embedding matrices from two knowledge graph domains, compute attention-weighted enrichment. **V1B production requirement: LayerNorm after every enrichment sweep (mandatory, not optional).**

Equation:
```
E_i^enriched = LayerNorm(E_i + Σ_{j≠i} CrossAttention(G_i, G_j))
```

**Architectural constraint (permanent):** GraphAttentionBridge does NOT call ProfileScorer.update(). The Loop 2/4 firewall extends to Level 2.

### 11.3 Level 3 — Cross-Domain Discovery (`gae/discovery_engine.py`, v8.0 target)

Uses enriched embeddings from Level 2 to discover cross-domain connections. Outputs new entities, relationships, and scoring dimensions that feed back to Level 1 via profile augmentation.

**γ constraint:** 𝒮(n,t) ~ O(n^{2.11}·t^γ). The t^γ term requires EXP-G1 before any external claim. γ≈1.5 is estimated. Not measured.

### 11.4 Level 1 Data Preservation Hooks (every domain must write)

```python
# Every Level 1 domain writes these on every decision cycle (PLAT-4 validated):

@dataclass
class DecisionRecord:
    """Hook 1 — written at score time."""
    decision_id: str
    alert_id: str
    category: str
    category_index: int
    action: str
    action_index: int
    confidence: float
    factor_vector: List[float]      # MUST be serialized to list, not np.ndarray
    centroid_snapshot: List[List[List[float]]]  # μ[c,:,:] at decision time
    timestamp: str
    domain_id: str

@dataclass
class OutcomeRecord:
    """Hook 2 — written at outcome verification time."""
    decision_id: str                # links to DecisionRecord
    correct: bool
    verified_by: str                # "human" | "auto_approve" | "oracle"
    timestamp: str

@dataclass
class ProfileSnapshot:
    """Hook 3 — written on checkpoint (every 50 decisions when synthesis active)."""
    domain_id: str
    snapshot_id: str
    mu: List[List[List[float]]]     # full centroid array
    counts: List[List[int]]
    decision_count: int
    timestamp: str
    trigger: str                    # "checkpoint_interval" | "operator_start" | "manual"
```

---

## 12. Contracts, API Pipeline, Accumulation

### 12.1 Public API Pipeline (v5.0 → v5.5)

```
# v5.0 pipeline (LIVE):
alert → FactorComputers → f
f → SituationAnalyzer → c
f, c → ProfileScorer.score(f, c) → ScoringResult
ScoringResult → compute_judgment(...) → JudgmentResult
outcome → ProfileScorer.update(f, c, a, correct) → WeightUpdate

# Evaluation pipeline (LIVE):
scenarios, oracle → run_evaluation(scorer, scenarios, oracle) → EvaluationReport
scoring_results → run_ablation(scorer, scenarios, factor_names) → AblationReport

# v5.5 additions:
GraphSnapshot → EmbeddingProvider.embed_graph() → E (n_entities × d)
E_i, E_j → GraphAttentionBridge.enrich() → E_enriched (with LayerNorm)
```

### 12.2 Semantic Accumulation Channels

| Channel | What Accumulates | When |
|---|---|---|
| A — Profile centroids | μ[c,a,:] ← pull/push via Eq. 4b-final | Every verified outcome |
| B — Decision nodes | DecisionRecord written to graph | Every score() call |
| C — Outcome nodes | OutcomeRecord linked to Decision | Every verified outcome |
| D — Profile snapshots | ProfileSnapshot for rollback | Every 50 decisions (when synthesis active) |
| E — Enriched embeddings | Level 2 enrichment (v5.5+) | Periodic sweep |

---

## 13. Equation Traceability Matrix

| Equation | Paper Section | File | Function | Version | Status |
|---|---|---|---|---|---|
| **Eq. 4-final** | §3 | `gae/profile_scorer.py` | `ProfileScorer.score()` | v5.0 | ✅ LIVE |
| **Eq. 4b-final** | §3 | `gae/profile_scorer.py` | `ProfileScorer.update()` | v5.0 | ✅ LIVE |
| Eq. 4 (published) | §3 original | `gae/scoring.py` | `score_alert()` | v4.1 | ⚠️ DEPRECATED (v6.0) |
| Eq. 4b (published) | §3 original | `gae/learning.py` | `LearningState.update()` | v4.1 | ⚠️ DEPRECATED (v6.0) |
| Eq. 4c (decay) | §3 | `gae/learning.py` | `apply_decay()` | v4.1 | ✅ Preserved |
| **Eq. 4-synthesis** | §5 (PROPOSAL) | `gae/profile_scorer.py` | `ProfileScorer.score(synthesis=σ)` | v6.0 | 🔵 GATED (GATE-M) |
| Eq. 5 (embeddings) | §4 | `gae/embeddings.py` | `embed_graph()` | v5.5 | 📋 Designed |
| Eq. 6 (cross-attention) | §4 | `gae/bridge.py` | `GraphAttentionBridge.enrich()` | v7.0 | 📋 Designed |
| Eq. 8a-8c (discovery) | §4 | `gae/discovery_engine.py` | `discover()` | v8.0 | 📋 Designed |
| ECE computation | - | `gae/evaluation.py` | `compute_ece()` | v5.0 | ✅ LIVE |

---

## 14. Design Decisions Log

### 14.1 Original Design Decisions (v4.1)

*(See prior versions for full record. Summary:)*
NumPy-only (24 multiply-adds don't need PyTorch), three-repo architecture (enforce P12), FactorComputer Protocol in GAE (abstract interface), f(t) stored in Decision nodes (R4).

### 14.2 Experiment-Driven Decisions (v8+)

| Decision | Evidence | Impact |
|---|---|---|
| L2 as default kernel | EXP-C1: 36.89pp gap | Settled |
| Dot product warned | EXP-C1: 61% on [0,1] | KernelType.DOT emits warning |
| Profile centroids | EXP-C1: 97.89% zero-learning | W matrix eliminated |
| G eliminated | EXP-A: +0.01pp | No GatingMatrix anywhere |
| τ = 0.1 | V3B: ECE 0.19 → 0.036 | Hard default, never override |
| Clipping required | V2: escape at dec 6-12 | All updates clip to [0,1] |
| τ_modifier rejected | OP: ECE +0.138 | No τ_modifier field, ever |
| Loop 2/4 firewall | EXP-S3: Frobenius 0.0028 | update() has NO synthesis param |
| Checkpoint required | EXP-OP2: 35% never recover | TD-033: checkpoint every 50 |
| LayerNorm required | V1B: 2.9M× explosion | Level 2: LayerNorm non-negotiable |
| γ is estimated | Not measured | EXP-G1 before public claim |
| Realistic ≠ synthetic | math_synopsis_v6 50-seed | Two accuracy regimes documented |

### 14.3 Open-Source Strategy Decisions (v9 NEW)

| Decision | Rationale | Implementation |
|---|---|---|
| Apache 2.0 (not MIT or GPL) | Compatible with enterprise use; preserves attribution; permits relicensing in products | `LICENSE` file at repo root |
| Open math, proprietary domain expertise | The engine is a commodity; the SOC DomainConfig is the moat | GAE exports Protocol, not SOC implementation |
| Users guide as first-class deliverable | A library without good docs is unused | `docs/users_guide.md` shipped in v5.0 |
| Minimal example in repo | "Does this work?" answered in 3 minutes | `examples/minimal_domain/` runnable standalone |
| No SOC-specific code in GAE | Prevents leakage; keeps GAE genuinely domain-agnostic | P12 enforced by tests |
| Published math as credibility | Open-source adoption requires trust; equations are peer-reviewable | Blog + paper link in README |

---

## 15. Open-Source Strategy

### 15.1 Why Open-Source GAE

The strategic argument for open-sourcing the engine (not the domain expertise) has three parts:

**Trust.** The competitive moat is the graph — the accumulated institutional knowledge in profile centroids. Opening the math does not give away the moat. A competitor who forks GAE and deploys it at their customer starts at zero centroids. The customer's 10,000 verified decisions are not in the fork. Trust comes from the math being visible and peer-reviewable.

**Ecosystem.** If GAE becomes the standard library for compounding-intelligence systems, every new domain (procurement, AML, ITSM, clinical trials) that uses GAE is potential infrastructure for a Dakshineshwari domain copilot. Open-source is the distribution mechanism.

**Recruiting and credibility.** Strong technical talent evaluates open-source repos. A clean, tested, well-documented Apache 2.0 library with peer-reviewed math is a better hiring signal than a closed-source demo.

### 15.2 What a Successful Open-Source Release Requires

A GitHub repo is not an open-source project. An open-source project has the following (current status in brackets):

**Code quality:**
- [✅] Apache 2.0 LICENSE at repo root
- [✅] 251 tests, all passing
- [✅] NumPy-only — zero external dependency to install
- [✅] Type hints throughout
- [⚠️] Docstrings complete on public classes (need audit — v5.5)
- [📋] `py.typed` marker file (PEP 561 — v5.5)

**Documentation:**
- [✅] `docs/users_guide.md` — 289 lines, 8 sections, runnable code
- [✅] `examples/minimal_domain/` — canonical new domain example
- [📋] `README.md` — THE landing page. Currently minimal. Must be substantially rewritten for v5.5. (See §15.3)
- [📋] `docs/equations.md` — Eq. 4-final through Eq. 4b-final with links to paper (update for v5.5)
- [📋] `CHANGELOG.md` — v0.1.0 → v0.5.0 with breaking changes noted
- [📋] `docs/CONTRIBUTING.md` — how to submit a PR, coding standards, test requirements

**Packaging:**
- [✅] `pyproject.toml` with version 0.5.0
- [📋] PyPI publish: `pip install graph-attention-engine` (target: v5.5 release)
- [📋] GitHub Release v0.5.0 with notes (target: immediately after v5.5 open-source prep)
- [📋] `pip install graph-attention-engine` installs correctly and `from gae import ProfileScorer` works

**CI/CD:**
- [📋] GitHub Actions: `pytest` on push (every PR runs the full test suite)
- [📋] GitHub Actions: lint (ruff or flake8) on push
- [📋] GitHub Actions: type-check (mypy --strict on public API) on push
- [📋] Badge: [![Tests](passing)](actions) [![License: Apache 2.0](...)] in README

**Community:**
- [📋] GitHub Issues enabled with labeled templates: Bug Report, Feature Request, New Domain
- [📋] GitHub Discussions enabled (Q&A tab)
- [📋] `SECURITY.md` — how to report vulnerabilities (required for enterprise adoption)
- [📋] `CODE_OF_CONDUCT.md` — standard Contributor Covenant

**Discoverability:**
- [📋] GitHub Topics: `machine-learning`, `knowledge-graph`, `decision-intelligence`, `numpy`, `enterprise-ai`, `online-learning`
- [📋] PyPI classifiers: Python version, license, topic
- [📋] Link from math blog to repo
- [📋] Link from compounding intelligence blog to repo

### 15.3 The README Problem

The README is the most important document in the repo. It is the first thing every potential contributor, user, and evaluator reads. It determines whether they continue or close the tab.

**Current state:** Minimal. Does not tell the story.

**Required sections for v5.5 README:**

```markdown
# Graph Attention Engine

> Distance-kernel attention for enterprise decision intelligence.
> Learn from every verified decision. Profiles are the model. 
> Math is open. The accumulated judgment is yours.

## What This Is

A scoring library that implements compounding intelligence —
AI systems that get measurably better at their job over time.

Core equation: P(a|f,c) = softmax(−‖f − μ[c,a,:]‖² / τ)
- f: your situation encoded as a factor vector
- μ: domain expert knowledge compiled into profile centroids  
- c: situational category (Mixture-of-Experts routing)
- τ: temperature (validated at 0.1, ECE=0.036)

## 30-Second Quick Start

pip install graph-attention-engine

from gae import ProfileScorer, build_profile_scorer
import numpy as np

# 3 categories × 2 actions × 3 factors
mu = np.array([...])  # your domain expertise
scorer = build_profile_scorer(mu, actions=["approve", "escalate"])

f = np.array([0.8, 0.3, 0.6])  # this situation
result = scorer.score(f, category_index=0)
print(result.selected_action, result.confidence)

scorer.update(f, 0, result.action_index, correct=True)  # learn

## Why Not Dot Product? (The Key Insight)

[The 36.89pp gap chart — expC1_comparison_waterfall.png]
[1 paragraph: proximity vs alignment]

## Validated Numbers

| Metric | Value | Condition |
|---|---|---|
| Zero-learning accuracy | 97.89% | Synthetic centroidal, GT profiles |
| With-learning accuracy | 98.2% | Synthetic, warm-start |
| Realistic static accuracy | 71.7% | 50-seed realistic distributions |
| Realistic at 1k decisions | 78.9% | 50-seed realistic distributions |
| Calibration ECE | 0.036 | τ=0.1 (use this, never 0.25) |
| Domain scaling exponent | n^2.11 | Simulation, R²=0.9999 |

See math/blog for derivation. See experiments repo for raw data.

## Building a New Domain

[Link to docs/users_guide.md §6 — 6-step onboarding]

## Architecture

[The five-layer diagram]
[Link to the math blog]
[Link to the experiments repo]

## License

Apache 2.0 — use it in your products. The math is open.
The competitive moat is your accumulated graph, not the equations.
```

**Key principle for the README:** Serve three audiences simultaneously — (1) a developer evaluating whether to use GAE (30-second quick start), (2) a ML practitioner who wants to understand the approach (the dot product section + validated numbers), (3) a technical evaluator doing due diligence (architecture + experiments link).

### 15.4 The Helpdesk Example Problem

The current `examples/minimal_domain/` uses a "helpdesk" domain. This is technically correct but misses the opportunity to demonstrate a compelling use case. Consider adding a second example domain for v5.5:

- **`examples/procurement_approval/`** — S2P use case proof. 3 categories (price_variance, vendor_risk, contract_compliance), 3 actions (approve, escalate, flag), 4 factors. Demonstrates that GAE generalizes beyond security operations without any changes to the engine.

This example serves three purposes: (1) proves the platform claim, (2) gives procurement teams an on-ramp, (3) demonstrates that DomainConfig design is accessible to non-ML engineers.

### 15.5 Version Naming Strategy

| Version | PyPI Tag | GitHub Tag | Theme |
|---|---|---|---|
| v0.5.0 | 0.5.0 | v0.5.0 | ProfileScorer + full evaluation API (current, tagged) |
| v0.6.0 | 0.6.0 | v0.6.0 | Open-source release prep: README, CI, PyPI, CONTRIBUTING |
| v0.7.0 | 0.7.0 | v0.7.0 | Tier 4-5: embeddings + attention infrastructure |
| v1.0.0 | 1.0.0 | v1.0.0 | GraphAttentionBridge (Level 2) — first major release |
| v2.0.0 | 2.0.0 | v2.0.0 | Cross-domain discovery (Level 3) |

**Why 0.x until GraphAttentionBridge?** The API is stable within 0.x (no breaking changes without a minor version bump) but the 1.0.0 signal means "this is the long-term supported API." That signal should coincide with the Level 2 implementation, which is when external developers can build the cross-domain compounding story themselves.

---

## 16. Production Constraints (All Hard — Not Configurable)

These are constraints derived from experiments. They are not guidelines. Code that violates them is wrong.

| Constraint | Value | Evidence | What Fails Without It |
|---|---|---|---|
| τ (temperature) | Always 0.1 | V3B: ECE 0.19→0.036 | Miscalibrated confidence → wrong auto-approve decisions |
| Centroid clipping | [0.0, 1.0] | V2: escape at dec 6-12 | Adversarial escape; 4,608× norms by dec 200 |
| update() has no synthesis param | Permanent | EXP-S3: Frobenius 0.0028 | μ contaminated by external intelligence |
| LayerNorm in Level 2 | Mandatory | V1B: 2.9M× explosion | Embedding norms blow up after 5 sweeps |
| λ ≤ 0.6 for synthesis | Hard ceiling | EXP-OP2: harmful above 0.6 | Operator damage scales 5:1 vs benefit |
| Checkpoint every 50 (synthesis) | Required | EXP-OP2: 35% never recover | Irreversible centroid damage after bad synthesis operator |
| Factor vectors in [0.0, 1.0] | Hard contract | EXP-C1: L2 validated on [0,1] | L2 distances become meaningless at other scales |
| τ_modifier | REJECTED | OP series: ECE +0.138 | Never add this field; test that it doesn't exist |

---

## 17. What's Built vs What's Next

### 17.1 v5.0 — COMPLETE ✅ (251 tests including post-tag WIRING-1 + gt_action_index fix)

**GAE Phase 1 (ProfileScorer integration):**
- `gae/profile_scorer.py` — ProfileScorer, ScoringResult, KernelType (GAE-PROF-1)
- `gae/scoring.py` — deprecated, forwards to ProfileScorer (GAE-PROF-2)
- `gae/learning.py` — delegates to ProfileScorer.update() (GAE-PROF-3)
- Orchestrator wired: SituationAnalyzer → c → μ[c,:,:] (GAE-PROF-4)
- Oracle integration: OracleProvider protocol (GAE-ORACLE-1)

**GAE Phase 6 (Evaluation + API):**
- `gae/evaluation.py` — EvaluationScenario, run_evaluation(), EvaluationReport (GAE-EVAL-1)
- `gae/judgment.py` — compute_judgment(), JudgmentResult, confidence tiers (GAE-JUDG-1)
- `gae/ablation.py` — run_ablation(), AblationReport (GAE-ABL-1)
- `gae/__init__.py` — full public API surface, all symbols (GAE-ENG-1)
- `examples/minimal_domain/` — canonical onboarding example (GAE-ENG-2)
- `docs/users_guide.md` — 289 lines, 8 sections, runnable code (GAE-DOC-1)

**Test count progression:**
```
v4.1 tagged:     177 tests
v4.5 preamble:   187 tests  (+CalibrationProfile)
v5.0-alpha:      211 tests  (+ProfileScorer)
v5.0 Phase 6:   235 tests  (+Evaluation/Judgment/Ablation)
v5.0 TAGGED:     243 tests  (+SOC integration fixes)
v5.0 post-tag:   246 tests  (+WIRING-1: CentroidUpdate, freeze/unfreeze)
v5.0 bug fix:    251 tests  (+gt_action_index dual push/pull, SHIFT-2 validated)
```

### 17.2 v5.5 — Open-Source Release Target

**Open-source prep (v0.6.0):**
- `README.md` complete rewrite (§15.3 spec)
- `CONTRIBUTING.md` + `CODE_OF_CONDUCT.md` + `SECURITY.md`
- `CHANGELOG.md` from v0.1.0 → v0.5.0
- GitHub Actions: pytest + lint + mypy on push
- PyPI publish: `pip install graph-attention-engine`
- `examples/procurement_approval/` (§15.4)
- Docstring audit: all public classes fully documented
- `py.typed` marker (PEP 561)
- GitHub Issues templates (Bug, Feature, New Domain)

**Tier 4-5: Embeddings + Attention infrastructure (v0.7.0 / v5.5 product):**
- `gae/embeddings.py` — EmbeddingProvider, PropertyEmbedding, TransformerEmbedding
- `gae/graph_schema.py` — GraphSchema dataclass (§11.4)
- Infrastructure for GraphAttentionBridge (writes hooks, no bridge logic yet)
- V1B LayerNorm: full test coverage before Level 2 ships
- CalibrationProfile category_thresholds (enables 40%+ auto-approve coverage)

**Meta-graph diagnostics:**
- Centroid drift visualization (Chart A fix — currently shows ≈0.0)
- Ψ diagnostic functions (anomaly detection, stability tracking)
- Profile convergence report: "Your system is X% more accurate than deployment day"

### 17.3 v7.0 — GraphAttentionBridge (Level 2)

- `gae/bridge.py` — GraphAttentionBridge.register_domain(), enrich(), sweep()
- Prerequisite: EmbeddingProvider for all domains (v5.5)
- Prerequisite: Level 1 data hooks writing correctly (PLAT-4)
- Prerequisite: EXP-G1 validates γ before cross-domain compounding claims
- LayerNorm is a hard production requirement (V1B — no configuration option)
- First major GAE release: v1.0.0

### 17.4 v8.0 — Cross-Domain Discovery (Level 3)

- `gae/discovery_engine.py` — DiscoveryEngine.discover()
- Prerequisite: GraphAttentionBridge validated (v7.0)
- Uses enriched embeddings as input
- Outputs new scoring dimensions → profile augmentation
- EXP-G1 must have passed and γ published

---

## 18. Repository Structure

```
graph-attention-engine/
├── gae/
│   ├── __init__.py              ✅ Full public API surface (v5.0)
│   ├── profile_scorer.py        ✅ ProfileScorer, ScoringResult, KernelType
│   ├── calibration.py           ✅ CalibrationProfile
│   ├── factors.py               ✅ FactorComputer protocol
│   ├── learning.py              ✅ LearningState (delegates to ProfileScorer)
│   ├── oracle.py                ✅ OracleProvider, GTAlignedOracle, BernoulliOracle
│   ├── evaluation.py            ✅ run_evaluation, EvaluationReport, compute_ece
│   ├── judgment.py              ✅ compute_judgment, JudgmentResult
│   ├── ablation.py              ✅ run_ablation, AblationReport
│   ├── scoring.py               ⚠️ DEPRECATED — forwards to ProfileScorer
│   ├── convergence.py           ✅ Unchanged
│   ├── contracts.py             ✅ Unchanged
│   ├── primitives.py            ✅ Unchanged
│   ├── events.py                ✅ Unchanged
│   ├── store.py                 ✅ ProfileScorer state persistence
│   ├── types.py                 ✅ Unchanged
│   ├── embeddings.py            📋 Tier 4 — v5.5
│   ├── graph_schema.py          📋 Level 1 hooks contract — v5.5
│   ├── bridge.py                📋 Level 2 GraphAttentionBridge — v7.0
│   └── discovery_engine.py      📋 Level 3 — v8.0
├── tests/
│   ├── test_profile_scorer.py   ✅ L2, Mahalanobis, cosine, dot
│   ├── test_calibration.py      ✅
│   ├── test_oracle.py           ✅
│   ├── test_evaluation.py       ✅
│   ├── test_judgment.py         ✅
│   ├── test_ablation.py         ✅
│   ├── test_learning.py         ✅
│   └── test_scoring.py          ✅ (backward compat)
├── examples/
│   ├── minimal_domain/          ✅ Helpdesk domain, runnable standalone
│   │   ├── config.py
│   │   ├── run_example.py
│   │   └── README.md
│   └── procurement_approval/    📋 S2P domain — v5.5 (§15.4)
├── docs/
│   ├── users_guide.md           ✅ 289 lines, 8 sections (v5.0)
│   ├── equations.md             📋 Equation reference with paper links — v5.5
│   └── EXPORTS.md               📋 Full public API reference — v5.5
├── .github/
│   ├── workflows/
│   │   ├── pytest.yml           📋 CI — v5.5
│   │   └── lint.yml             📋 CI — v5.5
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.yml       📋 v5.5
│       └── new_domain.yml       📋 v5.5
├── README.md                    ⚠️ Minimal — REWRITE TARGET for v5.5 (§15.3)
├── CONTRIBUTING.md              📋 v5.5
├── CHANGELOG.md                 📋 v5.5
├── SECURITY.md                  📋 v5.5
├── CODE_OF_CONDUCT.md           📋 v5.5
├── pyproject.toml               ✅ v0.5.0
└── LICENSE                      ✅ Apache 2.0
```

---

## Appendix A: Experiment Parameters

*(Unchanged from v8.3 Appendix A. See that version for full table.)*

## Appendix B: Chart Inventory

*(Unchanged from v8.3 Appendix B. Key chart for README: expC1_comparison_waterfall.png — the 25%→98% waterfall that visualizes the kernel finding.)*

---

*Graph Attention Engine — Design & Architecture v9.1 | March 12, 2026*
*v5.0 COMPLETE: 251 tests (post-WIRING-1 + gt_action_index fix). ProfileScorer + Evaluation + Judgment + Ablation + Users Guide + CentroidUpdate + freeze/unfreeze.*
*update() bug fix (March 15): gt_action_index dual push/pull replaces push-all. SHIFT-2: +2.7% lift at noise=0, δ=0.10 (was -9.0% pre-fix).*
*Two-level institutional judgment: ProfileScorer = Level 1 (Decision Intelligence, what to decide). AgentEvolver (domain copilot layer) = Level 2 (Deployment Intelligence, how to operate). GAE owns Level 1.*
*Open-source release target: v5.5 (README rewrite + CI + PyPI + CONTRIBUTING + procurement example).*
*Scoring architecture SETTLED: Eq. 4-final (L2 distance). Two accuracy regimes: synthetic (97.89%, 98.2%) and realistic 50-seed (71.7% static, 78.9% at 1k decisions, 90.7% auto-approve).*
*API: ProfileScorer.score() → ScoringResult.probabilities (not .scores). compute_judgment() returns JudgmentResult. run_ablation() → AblationReport.*
*Production constraints: τ=0.1, clipping [0,1], update() has NO synthesis param, LayerNorm in Level 2, λ≤0.6.*
*v5.5: open-source prep + Tier 4-5 embeddings. v7.0: Level 2 GraphAttentionBridge (v1.0.0). v8.0: Level 3 Discovery.*
*"The profiles ARE the institutional judgment. Not weights — knowledge you can read, audit, and trust."*
*"The math is open. The competitive moat is the accumulated graph."*
