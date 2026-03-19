> **ARXIV CHANGE NOTE (March 15, 2026 — v8→v9 update):**
>
> Authors referencing math_synopsis for paper drafts: the following changes
> affect equations and parameter values. Search for [CHANGED v9] markers.
>
> **(1) Tensor dimensions:** C=5→6, A preserved at 5, tensor 150→180.
> Category list corrected to match code. Random baseline unchanged (1/5=20%).
>
> **(2) Eq 4b update rule CORRECTED.** The correct=False branch previously
> described as "push centroid away" was ambiguous about WHICH centroid.
> The corrected rule: push PREDICTED (wrong) centroid away from f, AND
> pull GROUND TRUTH centroid toward f. Prior implementation pushed ALL
> centroids (a bug, fixed March 15, SHIFT-2 validated).
>
> **(3) η_neg design decision.** η_neg=0.05 (symmetric with η) is canonical.
> η_neg=1.0 produces catastrophic miscalibration (ECE=0.49, PROD-4b).
>
> **(4) Frozen scorer baseline established.** Frozen μ₀ (expert prior, no
> learning): 80.4% accuracy, 92.9% coverage at 85% precision (zero noise).
> At 10% noise: 72.5% accuracy, 62.6% coverage. These are the verified
> baseline numbers for the architecture.
>
> **(5) Learning validated post-fix.** With corrected update rule: +2.7%
> accuracy lift at noise=0/δ=0.10/warmup=1000. +1.5% at noise=0.10.
> Learning works when prior mismatch exists. Noise is the remaining constraint.

# Compounding Intelligence: Mathematical Synopsis

**Version:** 9.0 · March 15, 2026
**Purpose:** Complete mathematical framework in one document. For experts and LLMs.
**Status:** v5.0 TAGGED. Eq. 1–4b validated (14 experiments + 50-seed realistic suite).
Eq. 4-synthesis is PROPOSAL (5 experiments pending, gates define what ships). GATE-M satisfied (March 14).
Realistic accuracy numbers supersede centroidal synthetic numbers for all product claims.
**Sources:** cross_graph_attention_v3 (authoritative math), compounding_intelligence_v6
(authoritative architecture), intelligence_layer_design_v1 (synthesis proposal),
design_strategy_updates_v1 (open issues analysis), product_strategy_v2 (gap analysis),
experiments_catalog_v8 (gate definitions and experiment specs).

---

**What changed from v8:** [CHANGED v9]

- **§1:** Tensor updated to 180 values (6×5×6). C=5→6 (threat_intel_match added).
- **§3 Eq. 4b:** Update rule corrected. correct=False now dual push/pull:
  push predicted away AND pull ground truth toward f. Prior version pushed ALL
  centroids (bug fixed March 15, SHIFT-2 validated: -9% → +2.7% lift).
- **§3 η_neg:** η_neg=0.05 canonical (symmetric with η). η_neg=1.0 FORBIDDEN.
  The 20:1 asymmetry lives in consequence weighting (decision layer), not
  learning rate. Old constraint row updated.
- **§6:** Canonical dimensions updated to C=6, tensor 180 values. Category list
  updated (threat_intel_match added, reordered to match code).
- **§7:** Frozen scorer baseline added (SHIFT-2, March 15). Learning lift table added.
- **§8:** SHIFT-2 and DISC-1 rows added.
- **§13:** DISC-1 composite discriminant result added.
- **§16:** n_cat=6 updated. η_neg constraint corrected to 0.05 canonical.
- **§17/§18:** Notation and equation index updated.

**What changed from v7:**

- **§4:** λ operative window transfer confirmed. EXP-S2-REPRO completed March 14 —
  production poisoning resilience validated at λ=0.5 (0.15pp max). Realistic arm (Arm B)
  confirmed negligible poisoning effect. "Pending EXP-S2-REPRO" notes resolved throughout.
- **§7:** Segmented accuracy table: FX-1-PROXY-REAL note updated. Real factor distributions
  now characterized (KL 1.88–2.58). Segmented accuracy still INTERNAL ESTIMATE — real
  labeled data still needed for head-to-head measurement.
- **§9:** σ_max status updated. FX-1-PROXY-REAL complete — distributions characterized
  (bimodal threat intel, skewed pattern history). The p10 L2 margin at realistic AUAC is
  not directly measured by FX1 (it measured factor distributions, not margin distributions).
  σ_max derivation still requires computing margins from the characterized distributions.
- **§10:** EXP-OP2-N100 complete: 38% NR [29%, 48%] (was 35% at N=20). P-75 paradox confirmed.
- **§12:** Experiment count 25→28. FX-1-PROXY-REAL, EXP-S2-REPRO, EXP-OP2-N100 marked complete.
- **§13:** GATE-M formally satisfied. FUTURE-03 and FUTURE-09 activated.

**What changed from v6:**

- **§1:** Centroid tensor corrected to 150 values (5×5×6, not 6×4×6=144)
- **§3:** IKS formula added (Eq. IKS). Category-specific threshold model added (Eq. T*).
  Both are product formulas tied to v5.5-R1 and v5.5-R4.
- **§4:** τ_mod PERMANENTLY REJECTED from Eq. 4-synthesis. Equation simplified.
  λ operative window now states AUAC regime condition — transfer to realistic
  AUAC≈0.80 confirmed by EXP-S2-REPRO (March 14).
- **§6:** Tensor dimensions corrected: C=5, A=5, d=6 = 150 values. Actions updated to
  include refer_to_analyst (action index 4). Random baseline corrected to 20% (1/5).
- **§7:** Consistency claim added (unconditional, no experiments required).
  Segmented accuracy estimate added (INTERNAL ESTIMATE, FX-1-PROXY-REAL complete March 14).
- **§9:** σ_max corrected — not hardcoded at 1.0. FX-1-PROXY-REAL complete (March 14);
  σ_max derivation from L2 margin distribution is a computation step, not a new experiment.
- **NEW §13:** Claims Evolution Roadmap — what each gate unlocks, what claims become
  available, what forbidden claims are unblocked. Reference for all external
  communications before a gate result is known.
- **§14 (was §12):** v5.5 requirements updated — NL template engine, IKS,
  shadow mode, fifth action, EU AI Act compliance added.
- **§15 (was §13):** v6 requirements updated — synthesis layer conditional language
  tightened, S2P second domain added.
- **§16 (was §14):** Constraints & Invariants — four new rows: verification rate floor,
  N3 endogenous loop, n_act=5 canonical, τ_mod rejected.
- **§17 (was §15):** Equation index — τ_mod removed, IKS and T* added.
- **§18 (was §16):** Notation table — τ_mod row replaced with REJECTED note,
  n_cat and n_act explicit with canonical SOC values, λ operative window AUAC
  condition stated.

---

## 1. The Architecture in One Paragraph

A knowledge graph accumulates operational context. FactorComputers traverse the graph
to produce a factor vector f ∈ [0,1]^d for each decision. A ProfileScorer computes
action probabilities using L2 distance between f and learned profile centroids μ[c,a,:].
Verified outcomes update centroids via pull/push with asymmetric trust (20:1 penalty
ratio). An optional synthesis bias σ[c,a] (PROPOSAL, gated by EXP-S1–S8) shifts action
preferences based on external intelligence. The system compounds: every verified
decision reshapes centroids, making the next decision on similar alerts more accurate.
The moat is the centroid tensor — readable institutional judgment encoded in 180 numbers
(6 categories × 5 actions × 6 factors). [CHANGED v9]

---

## 2. Five Layers

| Layer | Name | Contains | Changes At |
|---|---|---|---|
| 1 | Domain Ontology | Categories, actions, factors, initial centroids μ₀, rules | Configuration time |
| 2 | Meta-Graph (Compiled State) | μ[c,a,:] (experience), σ[c,a] (awareness, PROPOSAL) | Decision time (μ slow, σ fast) |
| 3 | Mathematical Engine | ProfileScorer, kernels, softmax, calibration | Never (deterministic) |
| 4 | Knowledge Graph | Neo4j nodes/edges, FactorComputers, write-back | Every decision |
| 5 | Control Plane | Four feedback loops (3 validated + 1 proposed) | Per outcome |

---

## 3. Core Equations (VALIDATED)

### Eq. 4-final — Scoring

```
P(a|f,c) = softmax(−K(f, μ[c,a,:]) / τ)
```

- f ∈ [0,1]^d: factor vector from graph traversal (d=6 for SOC)
- μ[c,a,:] ∈ [0,1]^d: profile centroid for category c, action a
- K: kernel function. Default L2: K(f,μ) = ‖f − μ‖²
- τ = 0.1: temperature (V3B validated, ECE=0.036). Fixed. Never change.
- Softmax over n_act actions: P sums to 1, selected action = argmax

**Interpretation:** Each action has a prototype factor pattern (the centroid). The action
whose prototype is closest to the observed factors wins. Temperature τ=0.1 controls
decision sharpness — validated as optimal by V3B (ECE=0.036 vs 0.19 at τ=0.25).

---

### Eq. 4b-final — Centroid Learning [CHANGED v9]

```
When correct (a_pred = a_gt):
  μ[c, a_pred, :] ← μ[c, a_pred, :] + η_eff · (f − μ[c, a_pred, :])         [pull]

When incorrect (a_pred ≠ a_gt), dual update:
  μ[c, a_pred, :] ← μ[c, a_pred, :] − η_neg_eff · (f − μ[c, a_pred, :])     [push wrong away]
  μ[c, a_gt, :]   ← μ[c, a_gt, :]   + η_eff     · (f − μ[c, a_gt, :])       [pull correct toward]
  All other action centroids in category c: unchanged.

η_eff     = η / (1 + n[c, a_pred] · decay_rate)
η_neg_eff = η_neg / (1 + n[c, a_pred] · decay_rate)

Where:
  a_pred = predicted action (argmax of P(a|f,c))
  a_gt   = ground truth action (from verified analyst outcome)
```

- η = 0.05: base learning rate
- η_neg = 0.05: canonical (symmetric with η). **FORBIDDEN: η_neg=1.0 — ECE=0.49 (PROD-4b).**
- n[c,a]: cumulative verified-outcome count for (category, action) pair
- decay_rate = 0.001: count-based decay — stability increases with experience
- **INVARIANT:** μ ← clip(μ, 0.0, 1.0) after every update (V2 validated, mandatory)

**Bug fix note (March 15, 2026):** Prior to this fix, the incorrect branch pushed ALL
action centroids in category c away from f (including the ground truth centroid). This
caused centroid degradation. SHIFT-2 validated the fix: -9.0% accuracy lift before fix,
+2.7% after fix (noise=0, δ=0.10, warmup=1000).

**Interpretation:** Correct outcomes pull the predicted centroid toward the observed
factor pattern. Incorrect outcomes push the wrong centroid away AND pull the correct
centroid closer. The 20:1 consequence asymmetry lives in the decision layer (consequence
weighting), not in η_neg. Count decay ensures early decisions carry more weight per-update
than later decisions — the system front-loads learning and stabilizes with experience.

---

### Available Kernels

| Kernel | K(f,μ) | When to Use | Accuracy |
|---|---|---|---|
| **L2 (default)** | ‖f − μ‖² | Most cases. Factors in [0,1]. | **97.89%** |
| Mahalanobis | (f−μ)ᵀΣ⁻¹(f−μ) | Mixed-scale factors | Competitive with L2 |
| Cosine | 1 − cos(f,μ) | Pre-normalized factors | 96.42% |
| Dot product | −f·μᵀ | **DO NOT USE.** Magnitude confounding. | 61.00% |

The 36.89pp gap between dot product and L2 on identical data (EXP-C1) proves the
kernel choice is the critical architectural decision. Cosine is competitive (96.42%)
but L2 wins in 2 of 3 head-to-head comparisons (EXP-E1) and is the default.

---

### Eq. IKS — Institutional Knowledge Score (v5.5)

```
IKS(t) = 100 · min( D(t) / κ*, 1.0 )

where D(t) = (1 / (n_cat · n_act)) · Σ_{c,a} ‖μ[c,a,:](t) − μ[c,a,:](0)‖₂
```

- μ(0): centroid tensor at bootstrap completion (1,200 synthetic calibration decisions)
- **Shape note (v9) [CHANGED v9]:** mean_drift averages over 30 (c,a) cells (6×5).
  D_MAX=0.30 was set for 24 cells (6×4). PROD-1 should validate at (6,5,6)=180. Not blocking.
- μ(t): centroid tensor after t verified analyst decisions
- κ*: normalization constant — the D(t) value at which IKS should read ≈50-70 after
  the typical CISO demo window (200 decisions). **κ* is empirically derived by PROD-1.**
  Design estimate: κ ≈ 0.30. PROD-1 sweeps κ ∈ {0.05, 0.10, 0.15, 0.20, 0.25, 0.30}
  to find κ* such that IKS(200) ∈ [15, 40] in ≥90% of simulation seeds.
- IKS = 0: centroid tensor has not moved from bootstrap baseline
- IKS = 100: centroid tensor has drifted the full normalization distance (saturated)

**Acceptance criterion (v5.5-R4):** IKS increases after every batch of verified analyst
decisions. IKS trend chart shows a non-flat line after 10 verified decisions. The score
and its weekly delta are displayed in Tab 2 header.

**Interpretation for a CISO:** "Day 1: IKS = 0. Day 30: IKS = 14. Day 90: IKS = 47."
The system has accumulated 47 units of firm-specific institutional knowledge that
did not exist at deployment. This is the single most important number for answering
Demo Question 2: "Show me it's getting smarter."

---

### Eq. T* — Category-Specific Auto-Approve Threshold Model (v5.5)

```
threshold*(c) = min{ θ ∈ [0, 1] : accuracy(θ, c) ≥ target_accuracy(c) }
```

- accuracy(θ, c): fraction of alerts in category c where the auto-approved action
  matches the oracle, measured on the 50-seed simulation pool at threshold θ
- target_accuracy(c): minimum acceptable accuracy for auto-approve in category c.
  Risk-stratified defaults:
  - insider_threat, lateral_movement: target = 0.92 (catastrophic miss cost)
  - credential_access, data_exfiltration: target = 0.88
  - cloud_infrastructure, threat_intel_match: target = 0.85

**Empirical derivation:** Run PROD-4 (full prompt in experiments_catalog_v8 Part 3 §14).
Sweep θ ∈ {0.70, 0.75, 0.80, 0.85, 0.90, 0.95} for each category × 50 seeds. Fit the
accuracy(θ, c) curve. Find threshold*(c) for each target_accuracy level. Compute
weighted coverage using realistic alert distribution. Gate: ≥3 of 5 categories achieve
threshold*(c) ≤ 0.82 → v5.5-R1 PASS (40%+ weighted coverage achievable).

**Current state (v5.0):** global threshold = 0.90, coverage = 11.5%. The global
threshold is category-blind — it imposes lateral_movement conservatism on
cloud_infrastructure alerts that do not warrant it. Category-specific thresholds
are expected to raise coverage to 40%+ while maintaining or improving
per-category accuracy.

---

## 4. Synthesis Extension (PROPOSAL — Eq. 4-synthesis)

### The Problem

Eq. 4-final learns from the system's OWN verified decisions (experience). A human
analyst also reads the morning threat brief (awareness). When an active campaign
appears, their priors shift, their attention shifts, their caution shifts. The
current architecture has no mechanism to encode this temporal context — it treats
every alert with the same priors regardless of whether an active ransomware campaign
was disclosed this morning.

### Eq. 4-synthesis — Scoring with Awareness

```
P(a|f,c,σ) = softmax( −( ‖f − μ[c,a,:]‖² + λ·σ[c,a] ) / τ )
```

- σ[c,a] ∈ ℝ: synthesis bias for (category c, action a). Negative = action more
  likely. Positive = less likely.
- λ ∈ [0, 0.5]: coupling constant. **λ=0 → exact Eq. 4-final (kill switch).**
  Operative window: λ ∈ [0.5, 0.6] — identified at centroidal synthetic AUAC≈0.97
  (GATE-OP passed, p=0.0008). **Transfer to realistic AUAC confirmed by EXP-S2-REPRO
  (March 14, 2026).** Arm A: 0.15pp max AUAC degradation at λ=0.5, Loop 2 running,
  0–30% poison. Arm B: negligible effect on realistic distributions (AUAC 0.58–0.60).
  The operative window [0.5, 0.6] is validated for production deployment.
- τ = 0.1: temperature. Fixed. Same as Eq. 4-final.

**Note on τ_mod: PERMANENTLY REJECTED.**
An earlier formulation (Eq. 4-synthesis v0) included a temperature modifier τ_mod
in the denominator: (τ · τ_mod). This was rejected after finding ECE +0.138 at any
τ_mod ≠ 1.0 on synthetic calibration data (calibration failure). τ_mod has been
removed from all documents. τ is fixed at 0.1. There is no urgency-based temperature
adjustment. Any document still referencing τ_mod is out of date.

**Properties:**
- σ=0 → exact Eq. 4-final. Zero regression when synthesis layer is inactive.
- λ=0 → exact Eq. 4-final regardless of σ. Full kill switch at coupling constant.
- At σ_max and λ=0.5 (operative), max synthesis influence = σ_max × 0.5 distance
  units. Typical L2 distances ≈ 0.5–2.0. Experience (μ) always dominates awareness
  (σ) unless σ_max is set incorrectly.

**σ_max note:** The safety architecture (§9) references σ_max = 1.0 as a design
default. The correct value is **σ_max = p10 of the empirical L2 margin distribution**
at realistic AUAC — the 10th percentile of ‖f − μ[c,a*,:]‖² − ‖f − μ[c,a,:]‖²
where a* is the top action. This ensures synthesis can shift decisions at the margin
without overriding clear-majority decisions. **FX-1-PROXY-REAL is complete (March 14)**
— it characterized real factor distributions (KL 1.88–2.58) but measured factor shapes,
not L2 margin distributions directly. σ_max derivation requires computing margins from
the characterized distributions — a computation step, not a new experiment. Until this
computation runs, σ_max = 1.0 remains the conservative design default.

---

### Eq. S1 — SynthesisProjector Protocol

```
SynthesisProjector(active_claims) → σ[c,a]
```

Maps structured claims (from threat feeds, vendor advisories, CISO directives, work
artifacts extracted by ContextConnectors) to scalar bias values in the σ tensor.
Projector implementations: RuleBasedProjector (deterministic, v5.5 candidate),
LLMProjector (flexible, v6.0 candidate).

---

### Eq. S2 — Bias Accumulation with Decay

```
σ[c,a] = Σ_k direction_k[a] · confidence_k · decay(age_k)
         clipped to [−σ_max, +σ_max]
```

- direction_k[a]: per-action signed bias from claim k (e.g., escalate bias = −0.3)
- confidence_k = source_trust_tier × extraction_confidence ∈ [0, 1]
- decay(age_k): exponential decay over claim age (TTL-based, reuses CalibrationProfile
  decay infrastructure)
- Clipping enforces safety layer S3 (§9)

---

### Eq. S4 — Gate-M Validation Metric

```
Δ_accuracy(λ) = mean_over_seeds( accuracy_with_σ(λ) − accuracy_without_σ )
```

Paired comparison across seeds. Conditions for GATE-M PASS:
1. Δ_accuracy(λ*) ≥ 3pp, p < 0.05 (Bonferroni-corrected, k=6 → p < 0.0083)
2. ECE degradation ≤ +0.02 (synthesis must not harm calibration)
3. EXP-S2-REPRO: poisoning ≤ 2pp degradation at 20% bad claims, λ=0.5, Loop 2
   running — MUST include realistic-AUAC arm (centroidal-only result is insufficient)
4. EXP-S3: centroid divergence from Loop 2 contamination ≤ 5%

**GATE-M outcomes:**
- PASS all 4 conditions → σ activates in scoring pipeline at v6.0
- FAIL condition 1 or 2 → σ computed but display-only (Tab 5 Panel A shows awareness
  intelligence without affecting recommendations)
- Tab 5 has value at every gate outcome. GATE-M failure is not a product failure.

---

## 5. Four Feedback Loops

| Loop | Updates | Signal | Rate | Temporal Role |
|---|---|---|---|---|
| **1: Score** | Decisions | f from graph | Every alert | Instant |
| **2: Learn** | μ (centroids) | Verified outcomes | Slow (η=0.05, decaying) | Past (months) |
| **3: Reward** | Learning rate | 20:1 asymmetry + count decay | Per outcome | Meta (permanent) |
| **4: Synthesize** (PROPOSAL) | σ (bias) | External + internal claims | Fast (daily) | Present (days) |

**Critical invariant — epistemic separation:**
Loop 2 centroid updates NEVER use σ. μ encodes what decision patterns LOOK LIKE
(experience from verified outcomes). σ encodes what actions are APPROPRIATE RIGHT
NOW (awareness from current intelligence). These are different epistemic categories.
Contaminating μ with σ would cause the system to "remember" a temporary campaign
as a permanent operational pattern. This is enforced in ProfileScorer.update()
which has no σ parameter.

**Layer 2 has two residents:**
- μ[c,a,:] ∈ [0,1]^d — operational centroids. Analogy: analyst's years of experience.
- σ[c,a] ∈ ℝ — synthesis bias. Analogy: this morning's threat brief. Fast to update,
  fast to decay. Never bleeds into the slow layer.

**"μ is what you've learned. σ is what you know right now. The good analyst uses both."**

---

## 6. The Centroid Tensor

**Canonical SOC v5.0+ dimensions:** μ ∈ ℝ^(6×5×6) = **180 values** [CHANGED v9]

```
Categories (n_cat = 6): [CHANGED v9]
  0: credential_access
  1: threat_intel_match
  2: lateral_movement
  3: data_exfiltration
  4: insider_threat
  5: cloud_infrastructure

Actions (n_act = 5):
  0: escalate
  1: close_false_positive
  2: request_more_info
  3: apply_automated_response
  4: refer_to_analyst            ← added in v5.0; action index 4

Factors (d = 6):
  0: travel_match
  1: asset_criticality
  2: threat_intel_enrichment
  3: pattern_history
  4: time_anomaly
  5: device_trust
```

**Note on threat_intel_match [CHANGED v9]:** threat_intel_match was added as a first-class
category in v5.0 (not v5.5 as previously planned). The canonical tensor is now 6×5×6 = 180
values. The category list above reflects the production code (C=6, ORDER IS PERMANENT).
Any document or experiment using n_cat must state which version it targets. Prior drafts
stating n_cat=5 or tensor=150 should be treated as v4.x references.

Each μ[c,a,:] is a 6-dimensional profile: "what does a credential_access alert that
should be escalated typically look like?" The centroids ARE the institutional judgment —
readable, auditable, and correctable by domain experts without touching code.

**Key prior (v5.0 corrected):** credential_access/escalate centroid — travel_match
set to 0.72 (was 0.30 in v4.5). Rationale: anomalous travel + credential access is the
primary escalation trigger. Validated: high-travel vector → P(escalate) = 0.913 ✅

**Bootstrap calibration:** 1,200 synthetic decisions (10 rounds × 5 categories ×
4 original actions × 6 samples), σ=0.08, seed=42. Converged=True, drift=0.0097.
This is the warm-start baseline μ(0) for every deployment and the reference point
for IKS calculation.

**Synthesis tensor (PROPOSAL):** σ ∈ ℝ^(6×5) = 30 scalar values. [CHANGED v9]
"How should current intelligence shift action preferences for each category?"

---

## 7. Accuracy Numbers

### Two Accuracy Regimes — Never Mix Them

**Centroidal synthetic (EXP-C1, EXP-B1):** Tests the math in ideal conditions.
Oracle-generated factor vectors that perfectly align with centroids. Perfect routing.
These are the ARCHITECTURE VALIDATION numbers. Use to explain the mechanism.
Do NOT use as product claims.

**Realistic (50-seed validated):** Tests the product in realistic conditions.
Bernoulli oracle decisions (noisier), all FactorComputers with realistic noise,
full pipeline, realistic alert type distribution. These are the PRODUCT CLAIM numbers.
Use in customer communications, demos, and investor materials.

---

### Canonical Product Claim Numbers (50-seed validated, R50)

| Metric | Value | 95% CI | Condition |
|---|---|---|---|
| Static accuracy | 71.7% | [71.4%, 71.9%] | Combined realistic, no learning |
| Learning @ dec 1,000 | 78.9% | [78.1%, 79.6%] | Combined realistic, full learning |
| credential_access @ dec 1,000 | 68.0% | [66.7%, 69.1%] | Hardest category |
| Auto-approve accuracy (≥0.90) | 90.7% | [90.1%, 91.2%] | High-confidence suppress |
| Auto-approve coverage | 11.5% | ±0.70% | Alerts meeting ≥0.90 threshold |

**Frozen scorer baseline (SHIFT-2, March 15, 2026):** [CHANGED v9]
Verified baselines for μ₀ (expert prior, no learning — zero real decisions):

| Condition | Accuracy | Coverage at 85% precision |
|---|---|---|
| noise=0.00 | 80.4% | 92.9% |
| noise=0.10 | 72.5% | 62.6% |

**Learning lift (corrected update rule, δ=0.10, warmup=1000):**

| Condition | Accuracy lift | Coverage lift |
|---|---|---|
| noise=0.00 | +2.7% | +3.7% |
| noise=0.05 | +2.5% | -0.3% |
| noise=0.10 | +1.5% | +0.4% |

Note: At δ=0.00 (circular generator, μ₀ = μ_true), -1.4% / -5.0% is expected —
centroids drift from an already-optimal position. Learning is positive when prior
mismatch exists (δ>0). Noise is the remaining constraint on lift magnitude.

---

### Architecture Validation Numbers (centroidal synthetic — qualify always)

| Metric | Value | Experiment | Condition Qualifier |
|---|---|---|---|
| L2 zero-learning accuracy | 97.89% | EXP-C1 | Centroidal synthetic, correct routing |
| L2 with-learning accuracy | 98.2% | EXP-B1 | Centroidal synthetic, warm-start |
| Calibration ECE at τ=0.1 | 0.036 | V3B | Centroidal synthetic |

When stating 97.89% or 98.2%: always append "validated on centroidal synthetic data
with oracle routing. Real-data routing accuracy pending GATE-R." Omitting this
qualifier is a forbidden claim (see §13).

---

### The Consistency Claim (Unconditional — No Experiments Required)

> **Every analyst on your team receives the same starting recommendation, from the
> same reasoning, every time — regardless of which analyst is reviewing the alert,
> what time of day it is, or how long they have been on shift.**

This claim requires no experiments, no gate results, and no qualifications. It is
true at v5.0 today and will remain true at all future versions. Studies of SOC analyst
consistency show agreement rates of 60–70% on identical alerts between two experienced
analysts. GAE's day-1 value proposition is not accuracy competition — it is consistency
multiplication. The system eliminates the 30–40% inter-analyst variance before a single
centroid learns anything.

This is the strongest available claim for the ICP trigger (recent inconsistency
incident). It should appear in every demo, all outreach materials, and investor
communications without any condition tag. No GATE-R result changes it.

---

### Segmented Accuracy Estimate (INTERNAL ESTIMATE — FX-1-PROXY-REAL complete, real labels still needed)

The 71.7% static accuracy is a combined average across alert types. The distribution
is not uniform:

| Alert Type | GAE Day 1 | Rule-based SIEM | GAE Day 1,000 | Note |
|---|---|---|---|---|
| Known pattern, matches existing rule | ~80% | 90–95% | ~90% | Rules strongest here |
| Known category, novel variant | ~70% | 30–50% | ~80% | GAE advantage grows |
| Novel pattern, no existing rule | ~65% | 5–20% | ~75% | GAE structural advantage |
| Routine suppress, known benign | ~85% | 95%+ | ~92% | High overlap with rules |

**Label ALL of the above as INTERNAL ESTIMATE.** These numbers are derived from
synthetic data distributions and competitive positioning logic — not from head-to-head
measurement on real SOC data. **FX-1-PROXY-REAL (complete March 14)** characterized
real factor distributions: bimodal threat intel (KL=2.578), right-skewed pattern history
(KL=2.434), high-mean asset criticality (KL=1.880). These distributions are qualitatively
different from the centroidal Gaussian assumption — the segmented accuracy table above
may understate the GAE advantage on novel patterns (where real distributions diverge most
from rule-based assumptions) and overstate it on routine patterns. Real labeled data from
FX-1 (partner-required) is needed before these numbers can be refined. These numbers
inform the competitive framing but MUST NOT appear in customer materials as stated
percentages.

---

### The Accuracy Waterfall (14 Experiments)

```
Random baseline ..................... 20.0%   (1/5 actions — n_act = 5)
Shared W + Hebbian (EXP-A) ......... 49.3%   original architecture
Per-category W (EXP-A2) ............ 51.6%   attempted fix
Dot product centroid (EXP-C1) ...... 61.0%   right model, wrong kernel
Cosine centroid (EXP-C1) ........... 96.4%   magnitude confounding removed
L2 centroid zero-shot (EXP-C1) ..... 97.89%  ← THE ARCHITECTURE (centroidal)
L2 + learning (EXP-B1) ............. 98.2%   operational refinement (centroidal)
XGBoost (V3A, 1,300 samples) ....... 92.2%   ML baseline needs training data
Realistic static ................... 71.7%   ← PRODUCT CLAIM (50-seed)
Realistic @ 1,000 decisions ........ 78.9%   ← PRODUCT CLAIM (50-seed)
Frozen μ₀ baseline (SHIFT-2) ....... 80.4%   ← FROZEN EXPERT PRIOR (noise=0) [CHANGED v9]
Frozen μ₀ + learning (δ=0.10) ...... 83.1%   ← 80.4% + 2.7% lift (noise=0) [CHANGED v9]
```

**Note:** Earlier versions of this document stated random baseline = 25.0% (implying
4 actions). Corrected to 20.0% with n_act=5 (including refer_to_analyst).

**Why the gap between 97.89% and 71.7%?** The centroidal test uses oracle factor
vectors that perfectly align with centroids. The realistic test uses Bernoulli oracle
decisions (noisier targets) and realistic FactorComputer noise. The gap is real and
expected — it measures the noise floor of the realistic deployment pipeline, not a
flaw in the underlying architecture. The architecture validation numbers prove the math
is correct. The realistic numbers describe what customers will see.

---

## 8. Key Experimental Results

| Exp | Question | Result | Status |
|---|---|---|---|
| EXP-5 | GT-aligned oracle works? | 79.65% (was 40–44% Bernoulli) | ✅ PASS |
| EXP-A | Gating Matrix G helps? | **FALSIFIED** (+0.01pp, 4 variants) | ✅ FALSIFIED |
| EXP-C1 | Profile centroids work? | **97.89% L2** (settles architecture) | ✅ PASS |
| EXP-B1 | Learning improves centroids? | 98.2% warm, 90.7% cold, robust to 30% noise | ✅ PASS |
| EXP-D1 | Cross-category transfer? | Marginal (config wins 2–14pp) | ✅ DONE |
| EXP-D2 | Factor interactions? | None significant (75 pairs) | ✅ DONE |
| EXP-E1 | Which kernel? | L2 wins 2/3, pluggable for mixed-scale | ✅ DONE |
| EXP-E2 | Scales? | 99.9% at 20×10×20 | ✅ PASS |
| GATE-G | Gating obsolete? | ✅ PASSED — ProfileScorer is THE scorer | ✅ PASS |
| GATE-OP | λ=0.5 operative? | ✅ PASSED — p=0.0008 at centroidal AUAC≈0.97 | ✅ PASS |
| V1A | Scaling exponent? | b=2.11 ± 0.03, R²=0.9999 | ✅ VALIDATED |
| V1B | Norm explosion? | 2.9M× without LayerNorm → required | ✅ VALIDATED |
| V2 | Push stability? | Centroid escape → [0,1] clipping required | ✅ VALIDATED |
| V3A | Beats ML baselines? | L2 94.78% vs XGBoost 92.24% vs RF 92.93% | ✅ VALIDATED |
| V3B | Calibration? | ECE=0.036 at τ=0.1 (ECE=0.19 at τ=0.25) | ✅ VALIDATED |
| SHIFT-2 | Update rule corrected? | +2.7% lift (was -9.0% pre-fix). Dual push/pull confirmed. | ✅ PASS [CHANGED v9] |
| DISC-1 | Composite discriminant? | 70.4% coverage vs 62.6% confidence-alone (+7.8pp) | ✅ PASS [CHANGED v9] |

---

### Synthesis and Validation Experiments (PLANNED)

| Exp | Question | Gate | AUAC Condition |
|---|---|---|---|
| EXP-S1 | Does σ improve accuracy? | GATE-M: ≥3pp, p<0.0083, ECE ≤+0.02 | Centroidal |
| EXP-S2 | Poisoning resilience? | GATE-M: ≤2pp at 20% bad claims | **Both: centroidal + realistic** |
| EXP-S3 | σ contaminates μ? | GATE-M: ≤5% centroid divergence | Centroidal |
| EXP-S4 | λ sensitivity? | GATE-M: plateau ≥0.05 wide | Centroidal |
| EXP-S5a | Real CISA KEV → σ? | GATE-D-early: ≥3 σ cells updated in <60s | Real data |
| EXP-S5b | Work artifact → claims? | GATE-D-early: LLM F1 ≥ 0.70 | Real data |
| EXP-S5 | Full pipeline? | GATE-D: end-to-end latency <200ms P95 | Real data + v6.0 |
| EXP-S6 | INTSUM-quality briefing? | GATE-D: ≥80% claim coverage, LLM judge | Real data |
| EXP-S7 | Ask-the-Graph improvement? | GATE-D: ≥10/15 correct (3 conditions) | v5.0 baseline |
| EXP-S8 | Real synthesis → real decisions? | GATE-V: ≥3pp treatment, ≤1pp irrelevant degradation | Real deployment |
| GATE-R | Routing accuracy? | Run AFTER v5.5-R6. 95% CI on routing accuracy | Real pipeline |
| ~~FX-1-PROXY-REAL~~ ✅ | Real factor distributions | KL 1.88–2.58. Bimodal, skewed. σ_max derivation pending. | ✅ Complete (Mar 14) |
| PROD-1 | IKS κ* calibration? | IKS(200) ∈ [15,40] in ≥90% seeds | Simulation |
| PROD-3 | Shadow mode baseline? | Agreement rate distribution, 50 seeds | Simulation |
| PROD-4 | Per-category threshold*? | ≥3/5 categories at threshold*(c) ≤ 0.82 | Simulation |

---

## 9. Safety Architecture

### Synthesis Safety Layers

| Layer | Mechanism | Prevents |
|---|---|---|
| S1 | Extraction confidence gate (≥0.80) | Low-quality claims affecting σ |
| S2 | Source trust weighting (tier × confidence) | Untrusted sources dominating |
| S3 | Magnitude clipping σ ∈ [−σ_max, +σ_max] | Any combination of claims overriding μ |
| S4 | Human confirmation for high-impact Δσ | Misinterpreted or manipulated claims |
| S5 | Full rollback audit trail (claim provenance) | Damage assessment and reversal |

**σ_max status:** Design default = 1.0. **FX-1-PROXY-REAL complete (March 14)** —
factor distributions characterized (KL 1.88–2.58, bimodal threat intel, extreme
right-skew in pattern history). However, FX1 measured factor shapes, not L2 margin
distributions. The correct σ_max = p10 of empirical L2 margin distribution at
realistic AUAC≈0.80. **Deriving σ_max requires a computation step:** run ProfileScorer
with the FX1-characterized distributions and measure the resulting margin distribution.
This is a computation, not a new experiment. Until it runs, σ_max = 1.0 remains the
conservative default. The bimodal and skewed factor distributions from FX1 suggest
that margins may be narrower than on centroidal synthetic data — σ_max may need to
be smaller than 1.0 for safe operation.

**Architectural guarantee (provisional, to be reconfirmed):** At σ_max=1.0 and
λ=0.5 (operative), max synthesis influence = 0.5 distance units. Typical L2
distances = 0.5–2.0 at centroidal AUAC. EXP-S2-REPRO confirmed this guarantee holds
for poisoning resilience (0.15pp max at production λ). The guarantee must still be
reconfirmed for realistic factor distributions — margin distributions may be compressed,
requiring σ_max adjustment.

### Verification Safety Architecture

**Asymmetric trust (20:1):** Incorrect outcomes push centroids 20× harder than
correct outcomes pull them. This means a single confirmed mistake has more corrective
force than 20 confirmations. The system is harder to break than to fix.

**Count decay:** η_eff decreases with n[c,a]. Early decisions (low n) produce large
centroid moves. Late decisions (high n) produce small refinements. A mature category
profile (high n) is resistant to individual noisy feedback events.

**N3 endogenous loop (KNOWN RISK — no intervention point designed):**
Calibration error → biased verification selection → learning from biased data →
worse calibration → repeat. No intervention point has been designed for this loop.
Mitigation: shadow mode data from first deployment allows measurement of whether
verification is systematically biased. Disclosed in EU AI Act Article 9 risk log
and shadow mode deployment documentation. Full characterization requires EXP-S8
with real analyst decisions.

---

## 10. Scaling Properties

**Domain scaling:** Information gain I(n) ~ O(n^b) where b=2.11 ± 0.03 (V1A,
simulation). Super-quadratic: adding the 10th domain provides more than 10× the
information gain of the 1st. This is the mathematical basis for the compounding moat.
**Condition:** b=2.11 validated in simulation only. EXP-G1 (planned) will test
whether γ > 1.0 holds on real multi-domain data. Do not state "compounding" without
EXP-G1 result.

**Category scaling:** 99.9% accuracy at 20 categories × 10 actions × 20 factors
(EXP-E2, centroidal synthetic). No degradation with tensor dimensionality.

**Temporal compounding:** Cold start 52% → 90.7% accuracy at 1,000 decisions (EXP-B1,
centroidal). Warm start 97.89% at decision 1 (EXP-C1). The gap between warm and cold
IS the quantified value of institutional judgment encoded in the centroid tensor.

---

## 11. Gap Analysis — Five Customer Problems vs Current Architecture

### Problem 1 — Unmanageable threat landscape with unknown dependencies

**What v5.0 has:** threat_intel_enrichment factor (Pulsedive live), ThreatIntel nodes
in graph, CISA KEV planned for EXP-S5a.

**What's missing:** dependency map (which assets connect to which threats), attack chain
correlation (if alert A is real, what else is at risk?), multi-hop graph queries across
alert → asset → vulnerability → blast radius.

**Gap severity:** HIGH. Current system answers "is this real?" but not "what does it
mean?" The blast radius question justifies executive attention and security program
investment.

**Roadmap:** v6.0 (multi-hop queries, blast radius). EXP-S5a is step 1.

---

### Problem 2 — Ad hoc decisions, context impossible to reconstruct

**What v5.0 has:** full decision audit trail (Evidence Ledger, tamper-evident hash
chain), factor breakdown per decision, decision nodes in Neo4j with factor_vector,
closed loop: ticket → verification → trace → KPI.

**What's missing:** "show your work" as a first-class Tab 3 UI surface, per-decision
explainability showing which graph NODES drove each factor score, natural language
audit trail, decision timeline showing how the recommendation for a given alert type
has changed over time.

**Gap severity:** MEDIUM. The data exists. This is a surfacing gap, not a math gap.

**Roadmap:** v5.5 — factor node provenance (v5.5-R3), NL template engine.

---

### Problem 3 — Alert volume overwhelming

**What v5.0 has:** auto-approve zone at ≥0.90 confidence, 90.7% accuracy on
auto-approved alerts, 11.5% coverage.

**What's missing:** 11.5% is operationally insufficient. A single analyst handling
100 alerts per shift needs 40–50% auto-resolution to feel relief. Category-specific
thresholds are required. The fifth action ("refer_to_analyst") moves another 35%
of alerts from 15-minute reviews to 3-minute pre-analyzed reviews.

**Gap severity:** CRITICAL. This is the #1 operational adoption metric.

**Math:** Category-specific threshold*(c) via Eq. T* (§3). Additionally, the fifth
action creates a three-tier dispatch:
- Auto-approve (≥threshold*(c)): ~40% of alerts, 30-second confirmation
- Refer to tier-1 analyst (0.70–threshold*(c)): ~35% of alerts, 3-minute review
- Full review (<0.70): ~25% of alerts, tier-2 analyst, 10–20 minutes

The 0.70 confidence floor for "refer_to_analyst" is a design estimate.
**Empirical derivation required from PROD-4 accuracy curves before hardcoding.**

**Roadmap:** v5.5-R1 (category thresholds), v5.5 fifth action + PROD-4.

---

### Problem 4 — Exec democratization (budget holders can't see value)

**What v5.0 has:** Tab 4 ROI calculator (projected), Decision Economics, Evidence
Ledger.

**What's missing:** weekly digest "here's what happened this week and what your
system handled," trend over time (is the system getting better?), IKS as the
single proof-of-compounding number visible to a non-technical buyer, board-ready
narrative in one paragraph.

**Gap severity:** HIGH for buying decisions. The ROI calculator is a presales tool.
The exec needs operational proof during the trial period — a number that goes up.

**Roadmap:** v5.5 — IKS (Eq. IKS), Tab 5 Panel A (metrics-based, no σ required).

---

### Problem 5 — True autonomy

**What v5.0 has:** auto-approve for high-confidence suppress, 20:1 asymmetric
penalty, trust < 30% → human review, full audit trail.

**What's DELIBERATELY missing:** autonomous escalation without confirmation,
autonomous remediation (block IP, quarantine host, revoke credential).

**Design principle:** Autonomy is earned, not built.
1. Demonstrated accuracy → auto-approve suppress at 11.5% (v5.0)
2. Explainability → "show your work" (v5.5)
3. Widened envelope → 40%+ coverage (v5.5)
4. Conservative escalation autonomy → (v6.0, only after trust established)

**Roadmap:** Deliberately constrained until trust is earned and demonstrated.

---

### Gap Analysis Summary

| Problem | v5.0 Coverage | Key Gap | Roadmap |
|---|---|---|---|
| Threat landscape | 40% | No blast radius, no attack chain | v6.0 |
| Decision reconstruction | 70% | "Show your work" not surfaced | v5.5 |
| Alert volume | 20% | 11.5% → need 40%+ | v5.5 CRITICAL |
| Exec democratization | 30% | No IKS, no weekly digest | v5.5 |
| Autonomy | 15% | Deliberately constrained | v6.0 (earned) |

**Buying decision features** (gets the contract signed):
IKS + weekly synthesis briefing (exec sees value), 40%+ auto-approve (analyst feels
relief), shadow mode → realized ROI numbers.

**Usage decision features** (keeps the product in production):
"Show your work" explainability, decision audit trail, correctness at the alert level.

---

## 12. Open Math Issues for v5.5 and v6

The following issues have no current empirical resolution. They must be resolved
before the components that depend on them are built. Each has a designated
experiment and a document home (design_strategy_updates_v1.md §2.1 is the
authoritative assignment table).

| Issue | Depends On | Blocks | Experiment |
|---|---|---|---|
| IKS κ* value | L2 margin at realistic AUAC | v5.5-R4 (IKS display) | PROD-1 |
| σ_max correct value | p10 of L2 margin distribution | v5.5/v6.0 synthesis layer safety | FX-1-PROXY-REAL |
| λ operative window at realistic AUAC | EXP-S2-REPRO realistic arm | GATE-M production validity | EXP-S2-REPRO (amend spec) |
| Confidence floor 0.70 derivation | Accuracy-vs-threshold curve per category | refer_to_analyst routing design | PROD-4 |
| S4 bound at 2pp accuracy degradation | Per-cell drift vs accuracy sweep | IKS saturation threshold | PROD-1b |
| Minimum verification rate floor | Derivation from update equations | Core compounding claim, first customer | Math derivation + simulation |
| Segmented accuracy by alert type | Realistic L2 margin distribution | Competitive claims, CISO demo | FX-1-PROXY-REAL |

**Priority:** FX-1-PROXY-REAL and PROD-1 are the two most blocking experiments.
FX-1-PROXY-REAL unblocks σ_max, segmented accuracy, and the realistic GATE-M AUAC
arm. PROD-1 unblocks the IKS display in every CISO demo.

---

## 13. Claims Evolution Roadmap

**Purpose:** For each gate or experiment milestone, this section states exactly what
changes in the claims landscape: what claims become available, what conditions are
removed from existing claims, and what was previously forbidden that becomes
stateable. This is the reference document for all external communications before
a gate result is known.

**Current status (v5.0 TAGGED):** Centroidal claims fully available (with qualifiers).
Realistic 50-seed claims available. Consistency claim available unconditionally.
Synthesis claims gated. Routing accuracy unknown.

---

### Gate 0: v5.0 TAGGED (current baseline)

**Claims available now without condition:**
- CLAIM-31 (consistency): "Every analyst receives the same recommendation, same
  reasoning, every time." Unconditional.
- CLAIM-12 (scaling): "b=2.11, R²=0.9999" — simulation, permanent.
- CLAIM-22/23/24 (realistic 50-seed): 71.7% static, 78.9% at 1,000 decisions,
  90.7% auto-approve accuracy. Permanent with CI.
- CLAIM-35 (frozen baseline, SHIFT-2) [CHANGED v9]: "Expert prior alone achieves 80.4%
  accuracy at 92.9% coverage (85% precision) — before any real decisions."
- CLAIM-36 (learning lift, SHIFT-2) [CHANGED v9]: "After correcting the update rule,
  learning adds +2.7% accuracy lift when prior mismatch exists (δ=0.10, noise=0)."
- CLAIM-37 (composite discriminant, DISC-1) [CHANGED v9]: "Composite gating achieves
  70.4% coverage at 85% precision vs 62.6% for confidence alone (+7.8pp)."

**Claims available with mandatory qualifier:**
- CLAIM-01 (97.89%): must append "validated on centroidal synthetic data with
  oracle routing. Real-data routing accuracy unknown. ~20% of alert_type values
  currently misroute to default category (v5.0, G-L1-1)."
- "The system learns": must append "in simulation. Real-data learning trajectory
  requires real SIEM data (v6.0)."

**Forbidden at Gate 0:**
- "97.89% accuracy" without centroidal synthetic qualifier
- "Compounding over time" without b=2.11 simulation qualifier
- "40% auto-approve coverage" (11.5% is the validated number)
- Any routing accuracy percentage (GATE-R not yet run)
- "Synthesis improves decisions" (GATE-M not passed)

---

### Gate 1: v5.5-R6 ships + GATE-R runs (routing accuracy measured)

**Prerequisite:** alert_type → category mapping table complete for all 20+ alert
types (v5.5-R6). GATE-R experiment run with corrected routing. Produces routing
accuracy with 95% CI.

**Unlocks:**
- FUTURE-01: State routing accuracy percentage with 95% CI (e.g., "94.3% [93.1%,
  95.4%] routing accuracy after mapping fix"). Can now qualify CLAIM-01 precisely.
- Remove vague "assumes correct routing" from CLAIM-01 — replace with measured %.
- Can state: "The 97.89% centroidal accuracy assumes correct routing. At measured
  routing accuracy of X%, composite expected accuracy is [derived range]."

**Remains forbidden:**
- Unqualified "97.89%" without both regime and routing qualifiers

---

### Gate 2: FX-1-PROXY-REAL runs (realistic L2 margin distribution measured)

**Prerequisite:** Realistic factor vector distribution extracted from real or
high-fidelity simulated SOC data. L2 margin distribution at realistic AUAC≈0.80
measured across all (category, action) pairs.

**Unlocks:**
- σ_max finalized: compute p10 of margin distribution, set σ_max = that value
- activation_threshold finalized: confidence level at which σ effect is meaningful
- Segmented accuracy estimates upgraded from INTERNAL ESTIMATE to measured ranges
  (with qualifier "simulated realistic distributions, not production data")
- FUTURE-03: "At high-confidence decisions (≥0.90), per-category accuracy is
  [X%]–[Y%]" — the segmented claim with real margin data behind it
- Competitive comparison framing becomes defensible: rule-based vs GAE segmented

**Remains forbidden:**
- Head-to-head comparison using real SOC data (requires FX-1 real data, partner)

---

### Gate 3: PROD-1 runs (IKS κ* calibrated)

**Prerequisite:** PROD-1 sweep across κ ∈ {0.05–0.30}, finding κ* such that
IKS(200) ∈ [15, 40] in ≥90% simulation seeds.

**Unlocks:**
- FUTURE-18: "After 200 decisions, Institutional Knowledge Score is expected to
  reach [15–40] range (simulation)." The IKS claim becomes statable.
- IKS displayed in Tab 2 and Tab 4. Demo Question 2 ("Show me it's getting smarter")
  is answerable with a calibrated metric.
- v5.5-R4 can ship: Centroid Drift Visualization + IKS header.

---

### Gate DISC-1: Composite Discriminant (SHIFT-2 regime) [CHANGED v9]

**Result (March 15, 2026):** DISC-1 COMPLETE.
Composite discriminant: logistic regression on {confidence, margin, entropy, distance
features, factor features, rolling_accuracy, cat_count} achieves 70.4% coverage at 85%
precision vs 62.6% for confidence alone (+7.8pp lift). rolling_accuracy is the strongest
orthogonal signal (corr with confidence = 0.09).

**Unlocks:**
- CLAIM-37: composite gating is statable as a product claim.
- v5.5 auto-approve can use composite gating (not just confidence threshold).
- Further work: validate on realistic factor distributions (FX-1 regime).

---

### Gate 4: PROD-3 runs (shadow mode agreement rate baseline)

**Prerequisite:** Shadow mode simulation — 50 seeds, realistic oracle, measuring
system–analyst agreement rate across categories.

**Unlocks:**
- FUTURE-19: "In shadow mode, the system is expected to agree with experienced
  analysts approximately [X%] of the time overall, ranging from [Y%] to [Z%]
  across categories (simulation baseline)."
- Shadow mode reports from first customers become interpretable: if measured
  agreement is near the simulation baseline, system is behaving as expected.
- v5.5-R8 (shadow mode feature) can be shipped with a calibrated expectation
  rather than a blank slate.

---

### Gate 5: PROD-4 runs (category-specific threshold calibration)

**Prerequisite:** PROD-4 accuracy-vs-threshold sweep across all categories,
50 seeds. threshold*(c) derived for each target_accuracy level.

**Unlocks:**
- FUTURE-12: "With category-specific thresholds, the system can achieve approximately
  40% auto-approve coverage at ≥85% per-category accuracy (simulation)."
  The "11.5% → 40%" story becomes a concrete, numbered claim.
- Confidence floor 0.70 for refer_to_analyst either confirmed or replaced with
  PROD-4-derived value. The three-tier dispatch economics claim becomes specific.
- CLAIM-25 promoted: "Auto-approve coverage [X%] at ≥85% accuracy across
  [N] categories, with category-specific thresholds set by Eq. T*."

---

### Gate 6: GATE-M passes (synthesis improves accuracy)

**Prerequisites:** EXP-S1 (Δ≥3pp, p<0.0083), EXP-S2-REPRO (poisoning ≤2pp at
realistic AUAC), EXP-S3 (μ independence ≤5%), EXP-S4 (λ plateau ≥0.05 wide).
All conditions must pass.

**Unlocks:**
- σ activates in scoring pipeline at v6.0
- "The system adjusts its triage posture based on current threat intelligence before
  any alert fires." (With qualifier: validated on synthetic data with simulated σ;
  real data pending GATE-D.)
- Loop 4 can be described as "validated in controlled conditions, deploying in
  production" rather than "proposed."
- Tab 5 Panel A displays σ contribution alongside μ-based scoring.

**If GATE-M fails (any condition):**
- σ remains computed but display-only
- Tab 5 Panel A shows "Awareness Intelligence" panel — synthesis intelligence visible
  without affecting recommendations. Still valuable product surface.
- "The system is aware of current threat intelligence" remains statable.
  "The system adjusts scoring based on current threat intelligence" is forbidden.

---

### Gate 7: GATE-D passes (real data pipeline works)

**Prerequisites:** EXP-S5a (≥3 real σ cells from CISA KEV in <60s), EXP-S5b
(LLM extraction F1 ≥ 0.70), EXP-S5 (full pipeline latency <200ms P95),
EXP-S6 (INTSUM-quality briefing, LLM judge ≥80% claim coverage).

**Unlocks:**
- FUTURE-04: "Live CISA KEV → σ update pipeline. When a new critical vulnerability
  is disclosed, the system's triage posture adjusts within minutes."
- FUTURE-05: "Work artifacts (CISO emails, vendor advisories, Slack messages) →
  structured claims → σ. The system reads what your team reads."
- Tab 5 Panel B (Ask the Graph) ships at v6.0 with real-data grounding.

---

### Gate 8: GATE-V passes (synthesis improves real decisions)

**Prerequisites:** EXP-S8 — treatment group ≥3pp improvement over control,
overall ≥2pp improvement, irrelevant category degradation ≤1pp.

**Unlocks:**
- FUTURE-07: "Loop 4 (Synthesize) improves real analyst decision quality by ≥3pp
  on security-relevant scenarios. Validated with real analyst decisions."
- Full synthesis claims in product materials. The "intelligence layer" becomes
  a product feature, not a research capability.
- Can state: "The system improves not just from its own decisions (Loop 2) but from
  the current threat landscape (Loop 4)." Four-loop architecture fully validated.

**If GATE-V fails (GATE-M passed, GATE-D passed):**
- Tab 5 is a full enrichment dashboard — threat intelligence visibility, briefing,
  ask-the-graph — but synthesis does not affect scoring.
- Different ICP: firms wanting operational intelligence rather than adaptive triage.
- Different pricing tier. Not a product failure — a different product.

---

## 14. v5.5 Requirements (Derived from Gap Analysis + Design Updates)

All requirements below address at least one of the five CISO demo questions (Q1–Q5)
or a blocking operational gap. Nothing ships because it is mathematically interesting.

### v5.5-T1-1: NL Template Engine [CRITICAL — Demo Q1]
**Current:** Factor breakdown as numbers (travel_match: 0.87, asset_criticality: 0.92).
**Target:** Plain-English explanation below every recommendation. Example:
"ESCALATE recommended (89% confidence). Singapore login from unrecognized device,
critical infrastructure asset, no prior travel in profile. Your analysts have escalated
6 comparable alerts in the past 90 days — this recommendation aligns with 74%."
**Approach:** 6 categories × 5 actions = 30 base templates. Each template fills 3–5
variables from factor values + Neo4j graph queries (user, asset, ThreatIndicator).
Deterministic, no LLM dependency, fully auditable. "Similar past cases" sidebar:
top-3 prior decisions by cosine similarity on d=6 factor vectors (specification
required before building — see soc_copilot_design_v5_3 §4.2).
**Acceptance:** Every Tab 3 recommendation shows plain-English explanation containing
≥1 real graph entity. LLM judge rubric must be specified and verified.

### v5.5-R1: Auto-Approve Coverage 40%+ [CRITICAL — Demo Q3]
**Current:** 11.5% at global ≥0.90 threshold.
**Target:** 40%+ at ≥85% per-category accuracy.
**Math:** Eq. T* (§3). Run PROD-4 first. Ship threshold*(c) values derived from
PROD-4 data, not from design estimates.

### v5.5-R4: Institutional Knowledge Score [CRITICAL — Demo Q2]
**Current:** No metric proving "the system got smarter."
**Target:** IKS(t) ∈ [0, 100] (Eq. IKS, §3). Displayed in Tab 2 header with weekly
delta. Run PROD-1 first to calibrate κ*. Ship only after κ* is empirically determined.

### v5.5-R3: Chart A — Centroid Drift Visualization
**Current:** Chart A shows delta_norm ≈ 0.0 (wrong metric — ProfileScorer updates
centroids not W; the chart was designed for ScoringMatrix and never updated).
**Fix:** ‖μ[c,a,:](t) − μ[c,a,:](t-1)‖₂ per feedback event. Color-coded: green =
correct pull, red = incorrect push.

### v5.5-R5: Factor Node Provenance ("Show Your Work")
**Current:** Factor scores as numbers with no source.
**Target:** travel_match = 0.87 → "derived from TravelRecord node: Singapore,
2026-03-10, unconfirmed by HR." Every factor score traces to specific Neo4j nodes.
**Impact:** Closes Demo Q4 ("what if wrong?") and the technical evaluator gap.

### v5.5-R6: Alert Type → Category Mapping Fix [BLOCKING for GATE-R]
**Current:** ~20% of alert_type values fall through to default category (G-L1-1).
**Fix:** Complete mapping table for all 20+ alert types. Add ERROR logging on
unrecognized types. **Must ship before GATE-R runs — GATE-R measures corrected
routing accuracy, not v5.0 incomplete routing accuracy.**

### v5.5-R7: Threat Intelligence Write-Back
**Current:** Every alert re-queries Pulsedive (expensive, no accumulation).
**Fix:** ThreatIndicator nodes written on first IOC query, referenced on subsequent
alerts. After 6 months: 400+ firm-specific IOCs with decision history and outcomes.
This is the concrete answer to Demo Q5 ("why not Security Copilot?").

### v5.5-R8: Shadow Mode + Shadow Report
**Current:** No on-ramp for skeptical first customers.
**Target:** 30-day shadow run (scores logged, recommendations hidden). Shadow report:
"Your analysts and the system agreed 74.3% of the time. Here are the 26.7% where
they disagreed and why." Then: "Activate live mode" button.
**Critical:** This turns skepticism into curiosity. The shadow report becomes the
demo artifact for subsequent customers. Run PROD-3 to calibrate expected agreement
rate before first deployment.

### v5.5-NEW: Fifth Action — Refer to Analyst
**Current:** A=4 (excluding refer_to_analyst). Binary: auto-approve or full review.
**Target:** A=5, confidence floor 0.70 domain-configurable. Three-tier dispatch.
**Math:** Confidence floor must be derived from PROD-4 accuracy-vs-threshold curves,
not from design estimate of 0.70. Checkbox/rollback semantics must be specified in
soc_copilot_design_v5_3 §5 before building.

### v5.5-NEW: Tab 5 Panel A — Executive Briefing (no σ required)
**Current:** No executive surface.
**Target:** Weekly digest: alerts processed, auto-approved, escalated, human review.
Accuracy trend. "What your system learned this week" (top 3 centroid shifts in plain
English). IKS trend. Risk posture change. Built entirely from existing graph
metrics — σ makes it richer but is not required.

### v5.5-NEW: EU AI Act Compliance Evidence
**Scope:** Articles 9 (risk management), 12 (logging), 13 (transparency), 14 (human
oversight), 15 (robustness). August 2026 enforcement deadline.
**What we have:** audit trail, readable centroids, human review triggers, factor
breakdown. **What's missing:** formal documentation template, GDPR right-to-erasure
for decision nodes, Article 13 transparency notice, compliance package.
**N3 disclosure:** EU AI Act Article 9 risk log must include the N3 endogenous loop
as a known risk with the current mitigation (shadow mode measurement at first
deployment).

### v5.5-NEW: PyPI Release
**`pip install graph-attention-engine`** — removes the last friction point for
open-source adoption and technical evaluation by ML engineers at prospect
organizations. Required for the outreach strategy (Loom v2, LinkedIn, demo URL).

---

## 15. v6.0 Requirements (Real Data + Synthesis Layer)

### v6-R1: Synthesis Layer (conditional — GATE-M + GATE-D required)
- Eq. 4-synthesis live in scoring pipeline (if GATE-M passes)
- σ tensor updated from CISA KEV, NVD, vendor advisories via EXP-S5a pipeline
- ContextConnectors (email, Slack, docs) → claims → σ (if EXP-S5b passes)
- Tab 5 Panel B (Ask the Graph) — prompt-driven executive analysis
- **If GATE-M fails:** σ displayed in Tab 5 Panel A but not used in scoring pipeline.
  Product is an enrichment dashboard. Different ICP, different pricing tier.

### v6-R2: Attack Chain Correlation
- Multi-hop graph queries: alert → asset → CVE → blast radius
- "If this alert is real, what else is at risk?" as a first-class product query
- Requires: asset dependency map in graph, CVE linkage (CISA KEV integration from
  EXP-S5a), per-asset CVE patch status node

### v6-R3: Real SIEM Integration (Splunk + Sentinel)
- TAM doubles without Sentinel. ~60% of enterprise prospects use one of the two.
- Sentinel connector = the single most impactful single-component addition for
  first enterprise contract.

### v6-R4: S2P Second Domain
- Platform claim becomes real only with a second domain implementation.
- S2PDomainConfig + 10 seed scenarios + basic UI.
- Architectural work ~20% of SOC work — math and infrastructure domain-agnostic.
- The 80% is domain expertise (procurement factors, action space, category ontology).

### v6-R5: Autonomy Envelope Widening
- Auto-approve escalation (not just suppress) after trust demonstrated in v5.5
- Conservative: insider_threat and lateral_movement excluded from escalation autonomy
- Prerequisite: 40%+ coverage at v5.5 demonstrated and sustained for ≥90 days
- Prerequisite: "show your work" explainability in production at v5.5

### v6-R6: Centroid Editor UI / Management API
- SOC architect inspects and corrects μ[c,a,:] values without modifying config.py
- Centroid read: display 6-dimensional profile as factor-labeled radar chart
- Centroid write: factor-delta UI (Increase/Decrease/None × intensity), system
  normalizes to valid centroid. No direct tensor editing.
- This changes the customer relationship: from vendor-managed model to
  customer-owned institutional knowledge. The customer is preserving their learning,
  not renewing software.

### v6-R7: Analyst Benchmarking Report
- "Your team's accuracy: X%. System's accuracy: Y%. On the Z% of disagreements,
  here's what happened — analyst was right N₁ times, system was right N₂ times."
- Generates the reference customer quote. Turns pilot into champion.
- Also directly measures whether Loop 2 is learning from correct or biased signals.

---

## 16. Constraints & Invariants

| Constraint | Source | Enforced By | Status |
|---|---|---|---|
| μ ∈ [0, 1]^d | V2 (centroid escape without clipping) | np.clip after every update | ✅ VALIDATED |
| τ = 0.1, fixed | V3B (ECE=0.036 vs 0.19 at τ=0.25) | CalibrationProfile default | ✅ VALIDATED |
| η_neg = 0.05 (canonical, symmetric with η) [CHANGED v9] | η_neg=1.0 FORBIDDEN (ECE=0.49, PROD-4b). 20:1 asymmetry is in consequence weighting, not learning rate. | CalibrationProfile default | ✅ VALIDATED |
| σ ∈ [−σ_max, +σ_max] | Safety S3 | RuleBasedProjector clipping | ✅ Designed; σ_max pending |
| Loop 2 never uses σ | Epistemic separation | ProfileScorer.update() ignores σ | ✅ Enforced |
| LayerNorm before Tier 5 | V1B (2.9M× explosion without it) | Required for embedding ops | ✅ VALIDATED |
| Centroids readable by humans | Architecture choice — auditability | μ[c,a,:] is inspectable d-vector | ✅ Design |
| factor_vector stored as list | v5.0 fix (was JSON string, fragile) | json.loads() parse on read | ✅ v5.0 |
| ProfileScorer is THE scorer | TD-029 (ScoringMatrix deprecated) | ScoringMatrix removed | ✅ v5.0 |
| τ_mod = REJECTED | ECE +0.138 at any τ_mod ≠ 1.0 | Removed from all equations | ✅ REJECTED |
| n_act = 5 (SOC canonical) | refer_to_analyst added (v5.0) | DomainConfig | ✅ v5.0 |
| n_cat = 6 (SOC v5.0+) [CHANGED v9] | threat_intel_match added as first-class category. ORDER PERMANENT. | DomainConfig | ✅ v5.0+ |
| Verification rate ≥ f_min | Compounding requires feedback signal | **f_min UNCHARACTERIZED** | ⚠️ Open issue |
| N3 endogenous loop | Known calibration-feedback risk | **No intervention designed** | ⚠️ Known risk |

**Verification rate floor:** Compounding holds when the rate of verified decisions
exceeds a minimum f_min that depends on η, η_neg, decay_rate, and noise level.
Analytical derivation from Eq. 4b-final is pending (math_synopsis_v7 §12 open issue).
Estimate: f_min ≈ 15% of total decisions must be verified for Loop 2 to overcome
random noise. If production SOCs verify <15%, Loop 2 may not produce measurable
improvement — this would undermine the core product promise. Must be characterized
before first customer deployment.

**N3 endogenous loop:** Calibration error → biased verification selection → biased
learning → worse calibration → repeat. No intervention point has been designed.
Disclosed as known risk in v5.5 EU AI Act Article 9 documentation. Shadow mode
data from first deployment provides the first measurement opportunity.

---

## 17. Equation Index

| Equation | Status | Location | Purpose |
|---|---|---|---|
| **Eq. 4-final** | ✅ VALIDATED | §3 | L2 distance scoring (production) |
| **Eq. 4b-final** | ✅ VALIDATED | §3 | Centroid pull/push learning |
| **Count decay** | ✅ VALIDATED | §3 | Stability from experience |
| **Eq. IKS** | ✅ DESIGNED (κ* pending PROD-1) | §3 | Institutional Knowledge Score |
| **Eq. T*** | ✅ DESIGNED (threshold*(c) pending PROD-4) | §3 | Category-specific auto-approve |
| Eq. 4-synthesis | PROPOSAL (GATE-M pending) | §4 | Scoring with awareness bias |
| Eq. S1 | PROPOSAL | §4 | SynthesisProjector protocol |
| Eq. S2 | PROPOSAL | §4 | Bias accumulation with decay |
| Eq. S4 | PROPOSAL | §4 | GATE-M validation metric |
| ~~Eq. S3 (τ_mod)~~ | **REJECTED** | — | Urgency temperature modifier (ECE +0.138) |
| Eq. 5 (embeddings) | DESIGNED | cross_graph_attention_v3 §4 | Property → embedding (Tier 4, v6+) |
| Eq. 6–9 (cross-attention) | DESIGNED | cross_graph_attention_v3 §4–5 | Multi-domain attention (Tier 5, v7+) |

---

## 18. Notation Summary

| Symbol | Meaning | Shape | Range / Value | Status |
|---|---|---|---|---|
| f | Factor vector | (d,) | [0, 1] | ✅ |
| μ | Profile centroids (experience) | (n_cat, n_act, d) | [0, 1] | ✅ |
| σ | Synthesis bias (awareness) | (n_cat, n_act) | [−σ_max, σ_max] | PROPOSAL |
| τ | Temperature | scalar | **0.1 — fixed, never change** | ✅ |
| ~~τ_mod~~ | ~~Urgency modifier~~ | — | **REJECTED — ECE +0.138** | ❌ REMOVED |
| λ | Coupling constant | scalar | [0, 0.5]; operative window [0.5, 0.6] at centroidal AUAC≈0.97. **Realistic AUAC≈0.80 pending EXP-S2-REPRO.** Kill switch at λ=0. | PROPOSAL |
| η | Learning rate | scalar | 0.05 (default) | ✅ |
| η_neg | Negative learning rate | scalar | **0.05 (canonical, symmetric with η). FORBIDDEN: η_neg=1.0 (ECE=0.49).** [CHANGED v9] | ✅ |
| decay_rate | Count-based decay | scalar | 0.001 | ✅ |
| c | Category index | int | [0, n_cat); **n_cat=6 (SOC v5.0+)** [CHANGED v9] | ✅ |
| a | Action index | int | [0, n_act); **n_act=5 (SOC canonical)**. Random baseline = **20%** (1/5). | ✅ |
| K | Kernel function | f,μ → ℝ | L2 default | ✅ |
| n[c,a] | Observation count | (n_cat, n_act) | ℕ | ✅ |
| b | Scaling exponent | scalar | 2.11 ± 0.03 (V1A, simulation) | ✅ |
| κ* | IKS normalization constant | scalar | **Pending PROD-1.** Design estimate 0.30. | Pending |
| σ_max | Synthesis clipping bound | scalar | **Pending FX-1-PROXY-REAL.** Design estimate 1.0. | Pending |
| f_min | Minimum verification rate | scalar | **Uncharacterized.** Estimate ~15%.| Open |
| IKS | Institutional Knowledge Score | scalar | [0, 100] | Designed |
| threshold*(c) | Category auto-approve threshold | (n_cat,) | **Pending PROD-4.** | Pending |

---

*Mathematical Synopsis v9.0 | March 15, 2026*
*v5.0 TAGGED. 14 experiments + 50-seed realistic validation + SHIFT-2 + DISC-1 (Mar 15).*
*Centroid tensor: 6×5×6 = 180 values. [CHANGED v9: was 5×5×6=150]*
*n_act = 5 canonical (includes refer_to_analyst). n_cat = 6 (threat_intel_match added). Random baseline = 20%.*
*τ_mod permanently rejected. λ operative window validated by EXP-S2-REPRO (0.15pp max at production λ).*
*Eq. 4b CORRECTED (March 15): dual push/pull. Bug: prior version pushed ALL centroids when incorrect.*
*η_neg = 0.05 canonical (symmetric with η). η_neg=1.0 FORBIDDEN (ECE=0.49, PROD-4b). [CHANGED v9]*
*Frozen μ₀ baseline: 80.4% accuracy, 92.9% coverage (noise=0). Learning adds +2.7% (δ=0.10). [CHANGED v9]*
*DISC-1: composite gating 70.4% vs 62.6% confidence-alone (+7.8pp). rolling_accuracy is key signal. [CHANGED v9]*
*Realistic accuracy: 71.7% static, 78.9% at 1,000 decisions (50-seed validated).*
*Auto-approve: 90.7% accuracy, 11.5% coverage → v5.5 target 40%+ via Eq. T*.*
*Consistency claim: unconditional, no qualifier, true at v5.0 today.*
*"μ is what you've learned. σ is what you know right now. The good analyst uses both."*
*"The moat is the graph, not the model. The profiles prove it. The synthesis enriches it."*
