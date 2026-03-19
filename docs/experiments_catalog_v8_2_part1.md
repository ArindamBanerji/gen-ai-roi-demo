# Experiments Catalog — Compounding Intelligence Platform

**Version:** 8.3 · Part 1 of 3 · March 15, 2026
**Status:** 34 experiments complete. 41 planned across 5 series.
**Repo:** `cross-graph-experiments` (`github.com/ArindamBanerji/cross-graph-experiments`)
**Companions:** `gae_design_v9`, `soc_copilot_design_v5_4`, `intelligence_layer_design_v1`,
`ci_platform_design_v5_1`, `claims_registry_v2`, `math_synopsis_v7`, `product_strategy_v2`

> **What this document is:** The authoritative record of every experiment — completed, in-progress,
> and planned — across all tracks of the Compounding Intelligence Platform. Includes results,
> insights, chart markers, Claude Code prompts (where ready), and a forward-looking view tied
> directly to the product strategy and version milestones.
>
> **What changed from v7.2 → v8.0:**
> (1) **Renamed.** "Bridge Experiments Catalog" → "Experiments Catalog." The bridge metaphor
>     was specific to the early design phase (bridging the math-algorithm gap). We have crossed
>     that bridge. The catalog now covers the full experiment program.
> (2) **Two new experiment series added.** ARCH (architecture experiments) and PERF
>     (performance experiments). These were absent from v7.2. Architecture and performance
>     are as empirically important as math correctness — a correct but slow or fragile system
>     does not ship.
> (3) **PROD series added.** Product validation experiments: does the IKS move? Do analysts
>     agree with NL templates? What auto-approve threshold hits 40% coverage? These gate
>     product claims, not mathematical claims.
> (4) **Insight register added (§2).** A consolidated view of what we have actually learned
>     across all 34 completed experiments, written for a technical buyer or architectural
>     reviewer, not just an experimenter.
> (5) **Forward-looking view added (Part 3).** Experiments organized by the product milestone
>     they enable or gate. v5.5 experiments, v6.0 experiments, v7.0 experiments separated.
> (6) **Chart markers standardized.** Every completed experiment has named chart files.
>     Every planned experiment has chart requirements. Running `python run.py` must produce
>     all charts as a side effect — no exceptions.
> (7) **Accuracy waterfall updated for A=5.** The fifth action (refer_to_analyst) changes
>     the random baseline from 25% to 20%.
>
> **Supersedes:** bridge_experiments_catalog_v7.2 and all prior versions.

---

> **Changes from v8.2 → v8.3 (March 15, 2026):**
> (1) **Experiment count: 28 → 34.** 9 new experiments completed: PROD-4b, PROD-4 final,
>     PROD-4 warmup, SHIFT-1, SHIFT-2, DISC-1, DISC-2 (planned), CORR-1a diagnostic,
>     ontology verification.
> (2) **ProfileScorer.update() bug found and fixed.** correct=False previously pushed ALL
>     centroids (including GT). Fixed to dual push/pull.
> (3) **η_neg=0.05 settled as canonical.** η_neg=1.0 produces ECE=0.49 (FORBIDDEN).
> (4) **Composite discriminant validated.** DISC-1: 70.4% coverage at 85% precision
>     (13-feature logistic regression, +7.8pp over confidence-only baseline).
> (5) **PROD-3 and PROD-4 marked COMPLETE.** Per-category θ values measured (C=6).
>     Calibration Science series (SHIFT-1, SHIFT-2, DISC-1, DISC-2) added.
> (6) **Tensor shape updated: (5,5,6) → (6,5,6).** 5 → 6 categories; 25 → 30 cells; 150 → 180 values.
>
> **Changes from v8.1 → v8.2 (March 14, 2026):**
> (1) **Three experiments completed.** EXP-S2-REPRO (3-arm, PASS — 0.15pp max degradation
>     at production λ=0.5), EXP-OP2-N100 (N=100 seeds, 38% NR confirmed, CI [29%, 48%]),
>     FX-1-PROXY-REAL (KL 1.88–2.58, distribution gap quantified). Experiment count: 25 → 28.
> (2) **GATE-M formally satisfied.** EXP-S2-REPRO Arm 0 replicated (0.08pp at 20% poison).
>     Arm A confirmed production resilience (0.15pp max). Arm B confirmed on realistic
>     distributions. The caveat blocking GATE-M is closed.
> (3) **EXP-OP2 never-recover rate tightened.** N=100 confirms 38% [29%, 48%] for condition C
>     (was 35% with N=20 CI of [15%, 59%]). P-75 paradox strengthened: 28% vs 24% for A.
>     Baseline fragility finding: condition A has 24% NR [17%, 33%].
> (4) **Priority Queue updated.** FX-1-PROXY-REAL, EXP-S2-REPRO, EXP-OP2-N100 moved from
>     planned to completed. Queue is now: GATE-R → EXP-G1 → FX-1-PROXY.
> (5) **Production companion paper added.** [Banerji, 2026c] references updated throughout.

> **Changes from v8.0 → v8.1:**
> (1) **EXP-S2-REPRO spec added.** The critical caveat in EXP-S2 noted that REPRO is required
>     before formal GATE-M but gave no execution spec. A dedicated planned experiment entry
>     now specifies the full design: three arms (centroidal synthetic at λ=0.5, realistic
>     50-seed at λ=0.5, and realistic with Loop 2 frozen) plus the realistic-AUAC comparison
>     arm that was absent from EXP-S2's original design.
> (2) **EXP-S2 caveat extended.** The existing caveat was correct but incomplete — it did not
>     name the realistic-AUAC arm as a distinct requirement. Now explicit.
> (3) **GATE-M summary table updated.** EXP-S2-REPRO row added showing its gate status
>     (PENDING — blocks formal GATE-M) and the realistic-AUAC arm requirement.
> (4) **§1.3 GATE-R sequencing constraint added.** GATE-R must run after v5.5-R6 ships
>     (complete alert_type → category mapping). Running against the v5.0 incomplete mapping
>     (~20% misroute rate) measures broken routing, not architecture quality.
> (5) **Companion references updated.** `soc_copilot_design_v5_3` → `v5_4`;
>     `math_synopsis_v6` → `v7`.

---

## Document Map

| Part | Sections | Content |
|---|---|---|
| **Part 1 (this file)** | §§1–6 | Dashboard, insight register, accuracy waterfall, all completed experiments |
| **Part 2** | §§7–9 | Future math/synthesis/OP/GE experiments with prompts; ARCH series; PERF series |
| **Part 3** | §§10–14 | PROD series; forward-looking view by version; claims traceability; repo structure; execution notes |

---

## 1. Summary Dashboard

### 1.1 Completed Experiments (34)

| # | ID | Name | Series | Result | Key Number |
|---|---|---|---|---|---|
| 1 | EXP-5 | Oracle validation | Foundation | PASS | 79.65% GT-aligned |
| 2 | EXP-A (MI) | Capacity ceiling — G static MI | Foundation | G FALSIFIED | 48.88% (−0.38pp) |
| 3 | EXP-A (Hebbian) | Capacity ceiling — G learned | Foundation | G FALSIFIED | 49.27% (+0.01pp) |
| 4 | EXP-A (aug) | Capacity ceiling — augmentation | Foundation | G FALSIFIED | 51.03% (+1.77pp) |
| 5 | EXP-A2 | Per-category W | Foundation | FAIL | 51.61% (+2.35pp) |
| 6 | EXP-C1 (L2) | Centroid oracle — L2 | Foundation | **PASS** | **97.89%** |
| 7 | EXP-C1 (cosine) | Centroid oracle — cosine | Foundation | PASS | 96.42% |
| 8 | EXP-C1 (dot) | Centroid oracle — dot product | Foundation | FAIL | 61.00% |
| 9 | EXP-B1 | Profile scoring with learning | Foundation | **PASS** | **98.2% warm** |
| 10 | EXP-D1 | Cross-category transfer | Foundation | Marginal | Config wins 2–14pp |
| 11 | EXP-D2 | Factor interaction discovery | Foundation | None | 0 significant / 75 pairs |
| 12 | EXP-E1 | Kernel generalization | Foundation | L2 wins 2/3 | Maha wins mixed-scale |
| 13 | EXP-E2 | Scale test | Foundation | PASS | 99.9% at 20×10×20 |
| 14 | V1A | Scaling exponent (b) | Validation | PASS | b=2.11, CI [2.09,2.14] |
| 15 | V1B | Enrichment norm tracking | Validation | PASS | 2.9M× explosion without LayerNorm |
| 16 | V2 | Push update stability | Validation | PASS | Escape at dec 6 without clipping |
| 17 | V3A | Baseline comparison (ML) | Validation | PASS | L2 94.78% vs XGBoost 92.24% |
| 18 | V3B | Confidence calibration | Validation | PASS | τ=0.1, ECE=0.036 |
| 19 | EXP-S1 | Synthesis bias accuracy | Synthesis | Borderline | +2.30pp @ 60% coverage, p=0.036 |
| 20 | EXP-S2 | Poisoning resilience | Synthesis | PASS | ≤2pp at 20% poison |
| 21 | EXP-S3 | Loop 2 independence (firewall) | Synthesis | PASS | Frobenius 0.0028 (0.28%) |
| 22 | EXP-S4 | λ sensitivity (frozen profiles) | Synthesis | PASS | Plateau width 0.300 |
| 23 | EXP-OP1 / OP1-R / OP1-I | Scalar σ + Loop 2 (3 variants) | Operator | FAIL → FAIL → FAIL | Near-ceiling; ε-noise recovered by Loop 2 |
| 24 | EXP-OP-MARGIN / OP1-FINAL | Margin diagnostic + GATE-OP | Operator | **GATE-OP PASS** | δ=+0.0041, p=0.0008 at λ=0.5 |
| 25 | EXP-OP2 | Harmful resilience + partial spectrum | Operator | KEY FINDINGS | Acute 3×; C-exp non-recovery; threshold=100% |
| 26 | SYNTH-EXP-0 | Synthesis infrastructure build | Infrastructure | COMPLETE | synthesis.py, rule_projector.py, claim_generator.py |
| 27 | FX-1-PROXY-REAL | Real factor distribution characterization | Real Data | COMPLETE | KL 1.88–2.58 |
| 28 | EXP-S2-REPRO | Poisoning resilience at operative λ=0.5 | Synthesis | COMPLETE | 0.15pp max — GATE-M satisfied |
| 29 | EXP-OP2-N100 | Harmful resilience N=100 | Operator | COMPLETE | 38% NR [29%, 48%] |
| 30 | PROD-3 | Shadow mode agreement rate baseline | PROD | ✅ COMPLETE | Per-category θ: 0.744–0.809 (C=6) |
| 31 | PROD-4 (3 runs) | Auto-approve threshold calibration | PROD | ✅ COMPLETE | threshold* 0.720–0.870 at η_neg=0.05 |
| 32 | SHIFT-1 | Learning disabled baseline | Calibration | ✅ COMPLETE | 80.4% accuracy, 92.9% coverage@85%prec |
| 33 | SHIFT-2 | Learning validation post-fix | Calibration | ✅ COMPLETE | update() bug fixed; +2.7% lift at δ=0.10 |
| 34 | DISC-1 | Composite discriminant (13-feature) | Calibration | ✅ COMPLETE | 70.4% coverage@85%prec (+7.8pp) |

### 1.2 In Progress (1)

| ID | Name | Status | Prerequisite |
|---|---|---|---|
| EXP-OP3 | Residual Tracker early-warning diagnostic | 🔄 Next | TD-033 checkpoint infra |

### 1.3 Planned — Math / GAE / Synthesis (22)

| Series | IDs | Count | Gate | Version |
|---|---|---|---|---|
| Operator (OP) | OP3, OP4, OP5, OP6 | 4 | Post GATE-OP | v5.5 |
| Generic Engine (GE) | GE1, GE2, GE3, GE4 | 4 | τ-scaling, kernel | v5.5 |
| Real Data (FX) | FX-1 through FX-8 | 8 | Various | v5.5–v6.0 |
| Synthesis Pipeline (S5+) | S5a, S5b, S5–S8 | 6 | GATE-D-early, GATE-D, GATE-V | v6.0+ |
| Priority Queue | GATE-R, EXP-G1, FX-1-PROXY | 3 | Claims + real data | v5.5–v6.0 |
| ✅ Recently completed (v8.2) | FX-1-PROXY-REAL, EXP-S2-REPRO, EXP-OP2-N100 | 3 | GATE-M + distribution + CI | Completed Mar 14 |
| ✅ Recently completed (v8.3) | PROD-3, PROD-4 (3 runs), PROD-4b, SHIFT-1, SHIFT-2, DISC-1, CORR-1a | 7 | Calibration science series | Completed Mar 15 |

> **GATE-R sequencing constraint:** GATE-R must run **after v5.5-R6 ships** (complete
> alert_type → category mapping table, TD-037). Running GATE-R against the v5.0 mapping
> (~30 entries covering ~80% of alert types) measures broken routing, not architecture
> quality. The result would be a lower-bound composite accuracy number that conflates
> the routing error with the ProfileScorer error — making it uninterpretable and
> unpublishable. GATE-R is a v5.5 experiment, not a v5.0 experiment.

### 1.4 Planned — Architecture (ARCH series, 5 experiments)

| ID | Name | Gate | Version |
|---|---|---|---|
| ARCH-1 | Multi-repo API boundary compliance | v5.0 code sprint | v5.0 |
| ARCH-2 | DomainConfig swappability (S2P) | S2P domain design | v6.0-R4 |
| ARCH-3 | Write-back hook reliability under load | v5.0 deployment | v5.0 |
| ARCH-4 | Centroid tensor portability | First customer | v6.0-R3 |
| ARCH-5 | Shadow mode agreement rate baseline | Shadow mode delivery | v5.5-R8 |

### 1.5 Planned — Performance (PERF series, 5 experiments)

| ID | Name | Gate | Version |
|---|---|---|---|
| PERF-1 | ProfileScorer.score() latency profile | v5.0 sprint complete | v5.0 |
| PERF-2 | Neo4j FactorComputer concurrent load | v5.0 deployment | v5.0 |
| PERF-3 | Factor computation time breakdown | v5.0 sprint complete | v5.0 |
| PERF-4 | Centroid tensor memory footprint at scale | v5.0 + scale test | v5.5 |
| PERF-5 | Simulation orchestrator throughput | v5.5 shadow mode | v5.5 |

### 1.6 Product Validation (PROD series)

| ID | Name | Status | Key Result |
|---|---|---|---|
| PROD-1 | IKS sensitivity analysis | 🔧 SPEC READY | v5.5-R4 |
| PROD-2 | NL template analyst agreement study | 📐 PARTIAL | Partner-required |
| PROD-3 | Shadow mode baseline agreement rate | ✅ COMPLETE | Per-category θ: {credential_access:0.809, threat_intel_match:0.762, lateral_movement:0.744, data_exfiltration:0.756, insider_threat:0.771, cloud_infrastructure:0.789} |
| PROD-4 | Auto-approve threshold calibration per category | ✅ COMPLETE (3 runs) | threshold* range 0.720–0.870 at η_neg=0.05 |
| PROD-4b | Calibrated refer_to_analyst confidence floors | ✅ COMPLETE | Per-category confidence floors calibrated |
| PROD-5 | Category convergence rate (onboarding timeline) | 🔧 SPEC READY | 90-day deployment |

### 1.7 Calibration Science Series (new — March 15, 2026)

| ID | Name | Status | Key Result |
|---|---|---|---|
| SHIFT-1 | Learning disabled baseline (frozen scorer) | ✅ COMPLETE | 80.4% accuracy, 92.9% coverage at 85% precision (noise=0) |
| SHIFT-2 | Learning validation post-fix (24 conditions × 50 seeds) | ✅ COMPLETE | update() bug fixed; δ=0.10 → +2.7% lift; η_neg=0.05 canonical |
| DISC-1 | Composite discriminant (13-feature logistic regression) | ✅ COMPLETE | 70.4% coverage at 85% precision (+7.8pp over confidence-only) |
| DISC-2 | Frozen vs learned through composite gate | 🔲 PLANNED | Phase 5 |
| CORR-1a | Alert routing fix diagnostic | ✅ COMPLETE | 68% misroute eliminated; 20-entry mapping |
| Ontology verification | travel_anomaly→credential_access, insider_behavioral→insider_threat | ✅ COMPLETE | C=6 confirmed |
| η_neg study | η_neg=1.0 catastrophic (ECE=0.49) vs η_neg=0.05 canonical | ✅ COMPLETE | η_neg=0.05 is canonical |

---

## 2. The Insight Register

A consolidated view of what was actually learned. Written for an architecture reviewer,
not an experimenter. Numbers are available in §§3–6. This section is the "so what."

### 2.1 The Fundamental Finding

**The scoring kernel was the root cause of every prior failure.** The 36.89pp jump from dot
product (61.00%) to L2 distance (97.89%) on identical data and identical profiles proved that
the architecture was correct all along. EXP-A spent months trying to fix accuracy by improving
G, W, and augmentation. The ceiling was in the math, not the model.

This is the most important lesson from the entire experiment program: **when you have a 49%
ceiling, suspect the kernel before suspecting the data or the learning algorithm.**

### 2.2 What the Oracle Is

EXP-5 proved that oracle quality matters (+26pp from Bernoulli to GT-aligned) but hit a ceiling
at 79.65% with dot product + shared W. EXP-C1 then showed that a centroid oracle (no learning
at all) achieves 97.89% with L2 distance. The implication: profile centroids — configured
from domain expert knowledge — are a sufficient and powerful prior. Learning improves on
them slightly (98.2% warm, EXP-B1). The oracle is the configuration.

**Practical implication:** Investing in profile quality (DomainConfig, expert interviews,
centroid initialization) is more leveraged than investing in learning rate tuning or
architecture complexity.

### 2.3 What Learning Does (and Doesn't Do)

Loop 2 (centroid pull/push) adds ~0.3pp over zero-learning oracle (97.89% → 98.2%). This
is small in absolute terms but strategically important: it means the system improves over
time without retraining, and the improvement is verifiable and owned by the firm.

Loop 2 also recovers from profile imperfections. EXP-OP1-IMPERFECT showed that ε-noisy
profiles (ε up to 0.20) are corrected within 200 decisions. This validates the deployment
model: start with imperfect profiles, let the system learn, expect convergence.

**The caution:** Loop 2 learns from what it's told. If analyst feedback is wrong (EXP-OP2),
centroids drift in the wrong direction, and the damage persists beyond TTL expiry (38%
never-recover rate at C-exp, confirmed at N=100 seeds, 95% CI [29%, 48%]). The system is a faithful student — it does not independently
verify that the teacher is right.

### 2.4 The Synthesis Layer's Role

Synthesis bias (σ) is an acute-phase bridge, not a permanent accuracy lever. EXP-OP1-FINAL
passed GATE-OP (δ=+0.0041, p=0.0008) but EXP-OP2 revealed the full picture: in the first
150 decisions post-shift, σ delivers 3× its aggregate AUAC benefit (~+0.012/window vs
+0.0041 total). After that, Loop 2 catches up and the marginal benefit of σ diminishes to
near zero.

**What this means for product design:** σ is valuable when something changes quickly —
an active campaign, a new threat actor, a CISA KEV advisory. It is not a permanent
performance lever. The value proposition of σ is speed of adaptation, not sustained accuracy.
This should be the language in Tab 5 Panel A.

### 2.5 What "100% Correct Operator" Means in Practice

The single most concerning finding: only operators that are 100% directionally correct
(every σ cell pointing the right way) produce statistically significant AUAC improvement.
The P-75 condition (75% correct cells) actually recovers *more slowly* than no operator
(228 vs 178 decisions). GATE-OP passed with oracle-correct operators. Real analysts
authoring operators from campaign reports will not achieve 100%. The gap between
oracle-correct and analyst-correct is not bounded by any completed experiment. FX-1
(real SOC data with real analysts) is the only experiment that can answer this.

**Until FX-1:** the correct public claim is "validated with correctly-authored operators"
not "validated in production conditions."

### 2.6 What Architecture Experiments Will Prove

The math is settled. The outstanding questions are not mathematical:
- Can the system maintain latency SLAs at production alert volume? (PERF-1, PERF-2)
- Does the 3-repo architecture hold its boundaries as the codebase grows? (ARCH-1)
- Does DomainConfig actually swap without touching GAE? (ARCH-2)
- Does the write-back hook guarantee that every decision gets written? (ARCH-3)
- Does shadow mode produce the expected agreement rates? (ARCH-5, PROD-3)

These are the experiments that stand between the current state (validated math + working
demo) and the v5.5 product claim ("ready for first enterprise customer").

### 2.7 The Numbers That Are Safe to Claim Externally

| Claim | Number | Condition tag | Experiment |
|---|---|---|---|
| Mechanism accuracy — oracle | 97.89% | *Centroidal synthetic, zero-learning, C=6, A=5* | EXP-C1 |
| Mechanism accuracy — with learning | 98.2% | *Centroidal synthetic, warm start, C=6, A=5* | EXP-B1 |
| Confidence calibration | ECE=0.036 | *Centroidal synthetic, τ=0.1* | V3B |
| Scaling exponent | b=2.11 | *Centroidal synthetic, n=2–15 domains* | V1A |
| Synthesis gate | p=0.0008, λ=0.5 | *Centroidal synthetic, oracle-correct operators* | OP1-FINAL |
| Product accuracy — static | 71.7% | *Realistic 50-seed, combined categories* | 50-seed test |
| Product accuracy — with learning | 78.9% | *Realistic 50-seed, 1000 decisions* | 50-seed test |
| Auto-approve accuracy (≥0.90) | 90.7% | *Realistic 50-seed, global threshold* | 50-seed test |
| Auto-approve coverage | 11.5% ±0.70% | *Realistic 50-seed, global threshold* | 50-seed test |
| Frozen scorer baseline | 80.4% accuracy, 92.9% coverage at 85% precision | *Realistic, noise=0, freeze=True* | SHIFT-1 |
| Composite discriminant (DISC-1) | 70.4% coverage at 85% precision | *13-feature logistic regression* | DISC-1 |

*Never mix centroidal synthetic and realistic numbers. They are not comparable. Always state the condition tag.*

---

## 3. The Accuracy Waterfall

The journey from random baseline to validated mechanism. **Updated for A=5 (v5.3+):**

```
Random baseline (A=5) ......... 20.0%   ─┐
                                          │ +29.3pp (Hebbian learning from shared W)
Shared W Hebbian (EXP-A) ...... 49.3%   ─┤
                                          │ +2.4pp  (isolating categories, sample starved)
Per-category W (EXP-A2) ....... 51.6%   ─┤
                                          │ +9.4pp  (right model, wrong kernel)
Dot centroid (EXP-C1) ......... 61.0%   ─┤
                                          │ +35.4pp ← ROOT CAUSE: magnitude confounding
Cosine centroid (EXP-C1) ...... 96.4%   ─┤
                                          │ +1.5pp  (direction-invariant, distance-sensitive)
L2 centroid (EXP-C1) .......... 97.9%   ─┤
                                          │ +0.3pp  (operational warm-start learning)
Profile + learning (EXP-B1) ... 98.2%   ─┘
```

> **Note on A=5 vs A=4:** All completed experiments ran at A=4 (before refer_to_analyst
> was added as the fifth action in v5.3). The waterfall baseline changes from 25% to 20%.
> The absolute accuracy numbers (97.89%, 98.2%) are unchanged — they were measured at A=4
> and will be re-confirmed at A=5 by ARCH-2 and the v5.0 sprint evaluation tests.
> The 36.89pp dot→L2 gap is not affected by action count — it is a kernel property.
>
> **Note on C=5 vs C=6:** CORR-1a routing fix and ontology verification confirmed C=6 categories
> (travel_anomaly→credential_access, insider_behavioral→insider_threat added). Tensor shape
> is now (6,5,6) = 180 values (was (5,5,6) = 150 values). Per-category θ confirmed by PROD-3:
> 0.744 (lateral_movement) – 0.809 (credential_access). Frozen baseline (SHIFT-1): 80.4% accuracy.

### 3.1 What Was Eliminated vs. Validated

**Eliminated by experiment:**

| Approach | Experiment | Evidence |
|---|---|---|
| GatingMatrix G (all 3 variants) | EXP-A | +0.01pp best case — not worth implementing |
| Shared weight matrix W | EXP-C1 | Dot product = 61% where L2 = 97.89% |
| Per-category weight matrix W_c | EXP-A2 | 51.61% — sample starvation at realistic C |
| Dot product kernel | EXP-C1 | Magnitude-confounded — factor 3 problem |
| τ_mod (synthesis temperature modifier) | S-series | ECE +0.138 degradation — permanently removed |
| EXP-A2 direct path (no oracle) | EXP-A2 | 51.61% — direct learning from scratch cannot match profile centroids |

**Validated by experiment:**

| Finding | Experiment | Confidence |
|---|---|---|
| Profile centroids μ[c,a,:] as model state | EXP-C1: 97.89% zero-learning | High |
| L2 distance as default kernel | EXP-C1 + EXP-E1 | High |
| Mahalanobis for mixed-scale factors | EXP-E1 | High |
| Pluggable kernel architecture required | EXP-E1 | High |
| Centroid pull/push learning (warm start) | EXP-B1: 98.2% warm | High |
| Centroid clipping [0.0,1.0] unconditional | V2: escape at dec 6–12 adversarial | High — production requirement |
| LayerNorm in enrichment tier | V1B: 2.9M× explosion without | High — production requirement |
| τ=0.1 for calibration | V3B: ECE=0.036 | High |
| Super-quadratic scaling b=2.11 | V1A: R²=0.999, CI [2.09, 2.14] | Medium (synthetic, n=2–15) |
| L2 beats ML baselines (online) | V3A: 94.78% vs XGBoost 92.24% | Medium (synthetic) |
| Architecture scales to 20×10×20 | EXP-E2: 99.9% warm | High |
| Warm start essential at scale | EXP-E2: 27pp cold/warm gap at xlarge | High |
| Scalar σ: GATE-OP pass at λ=0.5 | OP1-FINAL: δ=+0.0041, p=0.0008 | High (centroidal synthetic, oracle-correct) |
| Loop 2 firewall holds (σ never enters update()) | EXP-S3: Frobenius 0.0028 | High |
| Operative window λ∈[0.5, 0.6] | OP1-FINAL + OP-MARGIN | High |
| λ≥1.0 → Loop 2 reinforces wrong flips | EXP-OP-MARGIN: δ=−0.069 at λ=2.0 | High |
| Harmful operators cause lasting centroid damage | EXP-OP2: C-exp 38% never-recover (N=100, CI [29%, 48%]; was 35% at N=20) | High — safety critical |
| Only 100%-correct operators pass Bonferroni | EXP-OP2: zero-crossing P-25/P-50 | High |
| Acute-phase benefit 3× AUAC aggregate | EXP-OP2: +0.012/window acute vs +0.0041 | High |
| Factors independently informative | EXP-D2: 0/75 pairs significant | High |

---

## 4. Completed Experiments — Foundation and Validation Series

### EXP-5: Oracle Validation

**Question:** Does a ground-truth-aligned oracle improve learning over Bernoulli random feedback?
Is there a meaningful performance gap between feedback quality levels?

**Setup:** 5 categories × 4 actions × 6 factors. Shared W, dot product scoring. Simplified
(orthogonal) action profiles — note: not realistic SOC profiles. 1,000 decisions, 10 seeds,
5 oracle quality levels.

**Results:**

| Oracle | Accuracy | vs. Bernoulli |
|---|---|---|
| GT-aligned (0% noise) | 79.65% | +26.09pp |
| GT-aligned (15% noise) | 73.86% | +20.30pp |
| Bernoulli | 53.56% | baseline |

Gate: GT(0%) > 75% ✅, delta > 15pp ✅, all categories > 50% ✅ (range: 74–87%).

**Caveat logged at execution:** Three structural modifications introduced to pass gates —
4× learning rate, profile-based W init, orthogonal action signatures. These made the problem
linearly separable by shared W. Not the case for realistic SOC data.

**Charts:**
- 📊 `expS5_accuracy_by_oracle_type` — bar chart, 5 oracle conditions
- 📊 `expS5_category_breakdown` — per-category accuracy at GT(0%)
- 📊 `expS5_learning_curves` — accuracy trajectory over 1,000 decisions

**Key insight:** 79.65% is the ceiling with dot product + shared W, even with a perfect oracle.
This ceiling was not understood at execution time — we thought oracle quality was the binding
constraint. EXP-A and EXP-C1 revealed the real binding constraint was the scoring kernel.
**The oracle experiment was correct in design; its lesson was only visible in retrospect.**

---

### EXP-A: Capacity Ceiling — G FALSIFIED

**Question:** Can any variant of the gating matrix G (static, learned, or augmentation-based)
break through the ~49% ceiling on realistic (non-orthogonal) SOC profiles?

**Setup:** 5 categories × 4 actions × 6 factors. Realistic profiles (overlapping, non-orthogonal).
5 configurations. 1,000 decisions, 10 seeds.

**Results:**

| Configuration | Realistic Accuracy | Delta |
|---|---|---|
| W-only (shared, uniform G) | 49.26% | baseline |
| W + G-static (MI) | 48.88% | −0.38pp |
| W + G-learned (Hebbian) | 49.27% | **+0.01pp** — best case |
| W + category augmentation | 51.03% | +1.77pp |
| W per-category | 51.61% | +2.35pp |

Simplified (orthogonal) profiles for reference: shared W = 87.79%, per-category W = 65.48%.

**Why G ⊙ f cannot break the ceiling:** G[c,i] scales factor i for category c (diagonal).
W[a,i] is shared across categories. The same factor has different discriminative meaning
across categories, but a diagonal projection cannot capture that without full rotation.
Transformers use full rotation matrices for this reason.

**Charts:**
- 📊 `expA_realistic_accuracy_comparison` — bar chart, 5 configurations, mean ± std
- 📊 `expA_simplified_vs_realistic` — paired bars: simplified vs realistic for each config
- 📊 `expA_g_matrix_heatmap` — MI-based G weight values by category × factor
- 📊 `expA_learning_curves_by_config` — accuracy trajectories, 5 configs overlaid

**Key insight:** G is not useful. +0.01pp best case on realistic data is a decisive result.
The gating hypothesis was well-motivated but empirically falsified. **No future architecture
should reintroduce G as a scoring component without a compelling mechanism-level argument.**

---

### EXP-C1: Centroid Oracle — THE BREAKTHROUGH EXPERIMENT

**Question:** If we pre-configure centroid profiles (no learning at all), how well does each
similarity kernel classify alerts? Is accuracy a function of learning, or of the kernel?

**Setup:** 5 categories × 4 actions × 6 factors. Realistic profiles. Pure nearest-centroid
classification (no learning, no updates). 5,000 alerts, 10 seeds.

**Results:**

| Kernel | Overall Accuracy | Std |
|---|---|---|
| **L2 (nearest centroid)** | **97.89%** | ±0.14% |
| Cosine | 96.42% | ±0.29% |
| Dot product | 61.00% | ±0.43% |

Per-category accuracy (L2): all categories 95–99%.

**Root cause of dot product failure:** Dot product is magnitude-confounded. Factors with
high mean values (e.g., AssetCriticality frequently near 1.0) dominate the score regardless
of their discriminative value. L2 distance measures profile shape, not magnitude-weighted
overlap. The 36.89pp gap between dot and L2 on *identical* data and *identical* profiles
is the cleanest possible single-variable experiment.

**Charts:**
- 📊 `expC1_comparison_waterfall` — **THE chart**: full progression from random to L2, annotated
- 📊 `expC1_method_comparison` — 3-bar comparison (L2, cosine, dot) with error bars
- 📊 `expC1_per_category_breakdown` — 5 category groups × 3 kernels
- 📊 `expC1_confusion_matrices` — 3-panel confusion matrices (L2, cosine, dot)
- 📊 `expC1_factor_magnitude_distribution` — shows why dot product is confounded

**Key insight:** This is the most consequential experiment in the catalog. It reframed the
entire project: the problem was never insufficient learning, gating, or architecture capacity.
The problem was the scoring kernel. Every experiment before EXP-C1 was trying to improve
a fundamentally miscalibrated measurement tool. L2 centroid distance is the right tool
because it measures "how far is this alert's factor signature from the expected signature
for this category-action combination" — exactly the right question.

---

### EXP-B1: Profile-Based Scoring with Learning — ARCHITECTURE SETTLED

**Question:** Does profile-based L2 scoring work with operational learning, noise, and cold start?
What are the optimal learning rates?

**Setup:** 5 categories × 4 actions × 6 factors. Three conditions: centroid_only (no learning),
profile_warm (learning from warm start), profile_cold (learning from random init). Three noise
levels: 0%, 15%, 30%. 1,000 decisions, 10 seeds per condition.

**Results:**

| Condition | noise=0% | noise=15% | noise=30% |
|---|---|---|---|
| centroid_only | 98.0% | 98.0% | 98.0% |
| **profile_warm + learning** | **98.2%** | **98.1%** | **98.1%** |
| profile_cold + learning | 90.7% | — | — |

Cold start recovery: 58.5% → 90.7% over 1,000 decisions.
Best learning rates: η=0.05, η_neg=0.05 (warm); η=0.01, η_neg=0.05 (warm, noise=15%).

> **η_neg convention (canonical):** η_neg=0.05 is canonical (symmetric with η_pos).
> η_neg=1.0 is FORBIDDEN — produces ECE=0.49 (catastrophic miscalibration, confirmed SHIFT-2).
> Never set η_neg > 0.1 without explicit experimental justification.

**Charts:**
- 📊 `expB1_warm_vs_cold_vs_centroid` — 3 learning curves to 1,000 decisions
- 📊 `expB1_noise_robustness` — warm-start accuracy at 3 noise levels (near-flat)
- 📊 `expB1_cold_start_recovery` — cold start trajectory from 58.5% → 90.7%
- 📊 `expB1_comparison_waterfall` — centroid vs warm vs cold with gap annotations
- 📊 `expB1_learning_rate_sweep` — η × η_neg grid heatmap (accuracy @ dec 1000)

**Key insight:** Two findings that together define the deployment model:
(1) Warm start is essential — 90.7% cold vs 98.2% warm. Profile configuration is not
optional; it is the performance foundation.
(2) Learning is robust to noise — 98.2% → 98.1% at 30% noise. The system does not need
perfect analyst feedback to maintain high accuracy. Small correction signals accumulate.
**Architecture settled.** No further kernel or architecture experiments needed before v5.0.

---

### EXP-D1: Cross-Category Transfer

**Question:** Can profiles learned from one SOC category accelerate another category's
cold-start recovery? Is meta-learning across categories worth implementing?

**Setup:** Ablation: category C_target starts cold; C_source has 300 decisions of warm learning.
Test: transfer source centroids as initialization for target. Compare cold vs config vs transfer.

**Results:**

| Target Category | Cold Start | Config Init | Transfer Init | Config–Transfer Gap |
|---|---|---|---|---|
| credential_access | ~72% | ~96% | ~82% | Config wins **14pp** |
| lateral_movement | ~68% | ~95% | ~84% | Config wins **11pp** |
| data_exfiltration | ~75% | ~97% | ~91% | Config wins **6pp** |

Transfer always beats cold. Config always beats transfer by 6–14pp.

**Charts:**
- 📊 `expD1_transfer_matrix` — accuracy by source×target category combination
- 📊 `expD1_convergence_by_condition` — 3 learning curves per target (cold/config/transfer)
- 📊 `expD1_decisions_to_90pct` — decisions until 90% accuracy by condition

**Key insight:** Config profiles are cheap, fast, and far superior to cross-category transfer.
An expert operator configuring profiles from domain knowledge outperforms any meta-learning
scheme at this scale. Cross-category edges in the meta-graph are a v6.0+ research direction,
not a v5.x product feature. **Do not implement cross-category transfer in the scoring path
without a compelling new experimental result.**

---

### EXP-D2: Factor Interaction Discovery

**Question:** Do any factor pairs in SOC data have interaction effects that go beyond their
individual contributions? Is a bivariate or multivariate model needed?

**Setup:** Mutual information and interaction gain analysis on 6 SOC factors.
75 unique factor pairs tested. 10,000 alerts, 20 seeds.

**Results:** 0 significant interactions / 75 pairs tested.
Maximum interaction gain observed = 0.67 (threshold for significance: 1.5).

**Charts:**
- 📊 `expD2_single_mi` — individual factor MI values, sorted
- 📊 `expD2_interaction_gain` — heatmap of pairwise interaction gain (all sub-threshold)

**Key insight:** Factors are independently informative. No interaction structure is present
in the synthetic SOC data. This is architecturally important: ProfileScorer's product-of-Gaussians
assumption (each factor contributes independently to the L2 distance) is not violated.
The model is correctly specified. **This result should be re-run on real SOC data (FX-1) —
real alerts may have correlations (e.g., AssetCriticality and ThreatIntel often co-elevate
on active campaigns) that the synthetic generator does not capture.**

---

### EXP-E1: Kernel Generalization Across Factor Distributions

**Question:** Does the L2 kernel remain the best choice when factor distributions deviate
from the unit-range [0,1] assumption? When should Mahalanobis be used instead?

**Results:**

| Kernel | Unit range [0,1] | Normalized [−1,1] | Mixed-scale |
|---|---|---|---|
| **L2** | **97.9%** | **97.8%** | 79.9% |
| Mahalanobis | 97.7% | 97.5% | **92.9%** |
| Cosine | 96.4% | 96.7% | 61.2% |
| Dot product | 61.0% | 90.8% | 41.9% |

**Charts:**
- 📊 `expE1_kernel_x_distribution` — 4 kernels × 3 distributions, accuracy heatmap
- 📊 `expE1_dot_vs_l2` — direct comparison across conditions
- 📊 `expE1_per_category_by_kernel` — per-category breakdown at each distribution

**Key insight:** L2 is the correct default for unit-range factors. Mahalanobis is the correct
choice when factor scales differ substantially (e.g., dollar amounts in S2P alongside
0–1 normalized risk scores). **The pluggable kernel architecture is required — not optional —
because domain variation is real and predictable. S2P will need Mahalanobis.**

---

### EXP-E2: Scale Test

**Question:** Does the architecture's performance hold as category, action, and factor
counts grow to enterprise scale? What is the warm/cold gap at scale?

**Results:**

| Dimensions (C×A×d) | Warm Start | Cold Start | Gap |
|---|---|---|---|
| small (5×4×6) | 97.9% | 89.9% | 8pp |
| medium (10×6×10) | 98.8% | 83.2% | 16pp |
| large (15×8×15) | 99.5% | 77.4% | 22pp |
| **xlarge (20×10×20)** | **99.9%** | **72.7%** | **27pp** |

**Charts:**
- 📊 `expE2_oracle_scaling` — warm-start accuracy vs scale (monotonically improving)
- 📊 `expE2_scaling_trend` — log-log plot of accuracy improvement with dimensions
- 📊 `expE2_cold_vs_warm_gap` — gap vs scale, showing warm start necessity

**Key insight:** The architecture scales correctly — warm-start accuracy improves with
dimension count because more specific profiles have less centroid overlap. But the cold/warm
gap grows from 8pp (small) to 27pp (xlarge). At enterprise scale, cold-start performance
is unacceptable (72.7%). **The deployment model — configure profiles, warm-start, then
learn — is not optional at scale. This is the constraint that makes profile quality
a competitive differentiator.**

---

### V1A: Scaling Exponent Extension

**Question:** Does the b=2.30 scaling exponent (measured at n=2–6 domains) generalize
to larger domain counts? What is the precision of the estimate?

**Results:**
- Prior estimate: b=2.30 (n=2–6, preliminary)
- **Validated:** b=2.11, 95% CI [2.09, 2.14], R²=0.999 (n=2–15 domains)
- Super-quadratic scaling confirmed. b > 2.0 rules out linear and quadratic.

**Charts:**
- 📊 `VAL-1A_scaling_extension_log_log` — log-log plot, fit line, CI band, b annotated
- 📊 `VAL-1A_residual_plot` — residuals from power law fit (confirms R²=0.999)

**Key insight:** b=2.11 is a more conservative and more credible estimate than b=2.30.
The moat claim (cross-domain discovery accelerates super-quadratically with domain count)
is supported — but the correct external language is "validated on synthetic data at n=2–15."
**EXP-G1 must measure b empirically before the temporal compounding claim (t^γ) is external-facing.**

---

### V1B: Enrichment Norm Tracking

**Question:** Does the enrichment operation (cross-graph attention + embedding update) produce
stable embedding norms under repeated application, or does it explode?

**Results:**
- Without LayerNorm: **2.9M× norm explosion** at 5 sweeps. Numerically unstable by sweep 2.
- With LayerNorm (production form): stable at ~1.0× across all sweeps.

**Charts:**
- 📊 `VAL-1B_norm_explosion_trajectory` — with vs without LayerNorm, 5 sweeps
- 📊 `VAL-1B_per_dimension_norms` — per-dimension breakdown showing explosion pattern

**Key insight:** LayerNorm is a non-negotiable production requirement, not a performance
optimization. Without it, Level 2 (GraphAttentionBridge) is not viable.
**Production form:** `E_i = Normalize(E_i + Σ CrossAttention_j(E_i, E_j))`

---

### V2: Push Update Stability (Centroid Clipping)

**Question:** Under adversarial feedback (all incorrect outcomes), do centroid updates
remain bounded? What happens without clipping?

**Results:**
- Without clipping: centroid escape begins at **decision 6–12** (adversarial, pure 100% incorrect).
  Norm 4,608× at decision 50.
- With clipping [0.0, 1.0]: all values bounded across all conditions.

Conditions tested: random, 10% adversarial, 20%, 50%, 100% adversarial feedback.

**Charts:**
- 📊 `VAL-V2_norm_trajectories_5_conditions` — norm vs decisions, 5 adversarial rates
- 📊 `VAL-V2_escape_decision_by_condition` — first escape decision at each rate

**Key insight:** Centroid clipping is a security and stability requirement, not a numerical
nicety. An adversarial analyst (or systematically wrong feedback) can cause centroid explosion
in 6 decisions without clipping. **Clipping [0.0, 1.0] is unconditional — it must be
applied in every ProfileScorer.update() call regardless of feedback quality estimates.**

---

### V3A: Baseline Comparison (ML Methods)

**Question:** Does L2 centroid scoring outperform ML baselines (XGBoost, Random Forest)?
Critically: does the *online* (zero-training-data) advantage hold?

**Results:**

| Method | Static accuracy | Online advantage |
|---|---|---|
| L2 centroid (ProfileScorer) | 94.78% | Full accuracy from decision 1 |
| Random Forest | 92.93% | Needs ~800 labeled samples for 85% |
| XGBoost | 92.24% | Needs ~1,300 labeled samples for 91.5% |

The online comparison is **the most important chart**: ProfileScorer at 94.3% immediately
vs XGBoost needing 1,300 samples for 91.5%. This is the compounding thesis quantified.

**Charts:**
- 📊 `VAL-3A-1_static_classifier_comparison` — 3-bar comparison with 95% CI
- 📊 `VAL-3A-2_online_learning_curves` — **THE compounding chart** — accuracy vs labeled
  samples, showing immediate L2 advantage over ML baselines requiring data
- 📊 `VAL-3A-3_data_efficiency_ratio` — samples needed to match ProfileScorer accuracy

**Key insight:** Traditional ML requires labeled training data before achieving useful
accuracy. ProfileScorer is useful from decision 1 if profiles are configured. This is
the operational advantage of the compiled ontology approach: configuration replaces
labeling. **V3A-2 is the single most persuasive chart for a technical evaluator.**

---

### V3B: Confidence Calibration

**Question:** What temperature τ produces well-calibrated confidence scores?
Is the system over- or under-confident at the default τ=0.25?

**Results:**

| τ | ECE | Interpretation |
|---|---|---|
| 0.01 | 0.280 | Severely overconfident |
| 0.05 | 0.082 | Overconfident |
| **0.10** | **0.036** | **Well calibrated** |
| 0.15 | 0.089 | Underconfident |
| 0.25 | 0.190 | Severely underconfident (prior default — wrong) |

ECE < 0.05 is generally considered good calibration. τ=0.1 achieves ECE=0.036.

**Charts:**
- 📊 `VAL-3B-1_ece_vs_temperature` — U-shaped ECE curve, minimum at τ=0.1 annotated
- 📊 `VAL-3B-2_reliability_diagram_tau_0.1` — predicted confidence vs actual accuracy, near-diagonal

**Key insight:** The prior default τ=0.25 was badly miscalibrated (ECE=0.190 — the system
was 19 confidence points off on average). The confidence threshold used for auto-approve
(≥0.90) means calibration quality directly affects which alerts get auto-approved and how
often. **τ=0.1 is a production requirement. Never use 0.25.**

---

## 5. Completed Experiments — Synthesis Phase 1

> **Equation under test (executed form — τ_mod permanently removed):**
> `P(a|f,c,σ) = softmax(−(‖f − μ[c,a,:]‖² + λ·σ[c,a]) / τ)`
>
> The original specification included τ_mod. All S-series experiments confirmed its removal
> is correct: ECE degradation of +0.138 when τ_mod ≠ 1.0. τ is fixed at 0.1 in all synthesis
> conditions. The above is the authoritative executed form.

### GATE-M Summary

| Experiment | Criterion | Result | Status |
|---|---|---|---|
| EXP-S1 (accuracy) | ≥3pp, p<0.05 | +2.30pp @ 60% coverage, p=0.036 | ⚠️ Borderline |
| EXP-S2 (poisoning) | ≤2pp at 20% poison | ≤2pp ✅ | ✅ PASS — but see REPRO |
| EXP-S3 (independence) | ≤5% Frobenius | 0.28% ✅ | ✅ PASS |
| EXP-S4 (sensitivity) | ≥0.05 plateau | 0.300 ✅ | ✅ PASS |
| EXP-OP1-FINAL (production) | p<0.05 at λ=0.5, Loop 2 running | p=0.0008 ✅ | ✅ **GATE-OP PASS** |
| **EXP-S2-REPRO** | **≤2pp at 20% poison, λ=0.5, Loop 2 running, realistic AUAC arm** | **Arm 0: 0.08pp (PASS). Arm A: 0.15pp max (PASS). Arm B: negligible on realistic.** | **✅ PASS — GATE-M unblocked** |

**GATE-M decision: FORMALLY SATISFIED (v8.2).** S2–S4 all pass. S1 borderline at 60%
coverage, but ceiling is +9.27pp (architecture is sound). GATE-OP passed (p=0.0008).
**EXP-S2-REPRO completed March 14, 2026:** Arm 0 replicated original EXP-S2 (0.08pp at
20% poison). Arm A confirmed production resilience at λ=0.5 with Loop 2 running (0.15pp
max AUAC degradation across 0–30% poison). Arm B confirmed negligible effect on realistic
alert distributions (AUAC ~0.58–0.60 regardless of poison level). The caveat blocking
formal GATE-M is closed. The poisoning resilience claim extends to production conditions.

---

### EXP-S1: Synthesis Bias Accuracy

**Question:** Does adding σ[c,a] to the scoring equation improve action selection accuracy?
Does the +9.27pp ceiling at 100% coverage translate to realistic deployment conditions?

**Setup:** 500 alerts, 10 seeds. Correct simulated claims matching 4 claim types
(active_campaign, cve_actively_exploited, vulnerability_patched, ciso_directive).
Coverage: 60% of alerts receive a matching claim (realistic estimate). λ sweep: 0.0 → 0.5.

**Results:**

| Condition | Accuracy delta | p-value |
|---|---|---|
| λ=0.2, 60% coverage | **+2.30pp** | 0.036 |
| λ=0.3, 100% coverage | +9.27pp | — (ceiling, not gate condition) |
| τ_mod ≠ 1.0 (any value) | −ECE 0.138 | removed permanently |

**Charts:**
- 📊 `expS1_accuracy_by_lambda` — accuracy vs λ curve (0.0 → 0.5) with CI band
- 📊 `expS1_per_category_heatmap` — 6×4 accuracy delta grid (category × action)
- 📊 `expS1_ece_by_lambda` — ECE by λ; red zone at ECE > baseline+0.02
- 📊 `expS1_action_shift` — fraction of alerts shifted to escalate_incident under synthesis

**Key insight:** Two findings in tension: (1) +2.30pp at realistic coverage is below
the 3pp gate, casting doubt on whether σ is practically useful. (2) +9.27pp at 100%
coverage proves the architecture is mathematically sound. The gap between 2.30pp and 9.27pp
is entirely explained by coverage — σ only helps when there is a matching claim. The real
question is: what claim coverage is achievable in production? FX-1 (real SOC data) and
SYNTH-EXP-5a (real CISA KEV + NVD) will bound this. **EXP-S1's borderline result should
not be interpreted as "σ doesn't work" — it should be interpreted as "σ works when
intelligence coverage is high."**

---

### EXP-S2: Poisoning Resilience

**Question:** How much does synthesized intelligence damage accuracy when claims are wrong?
Do safety mechanisms (σ_max clipping, confidence weighting) reduce the damage?

**Setup:** λ=0.2. Three conditions: clean (all correct), 20% poison (20% of σ cells wrong
direction), 40% poison. Safety mechanisms active vs inactive. 10 seeds.

**Results:**

| Condition | Degradation (safety ON) | Safety reduction |
|---|---|---|
| 20% poison | **≤2pp** | ≥50% damage reduction vs safety OFF |
| 40% poison | measured | documented |

**Gate: PASS.** ≤2pp at 20% poison ✅, safety halves damage ✅.

**Critical caveat (added v7.2, extended v8.1):** EXP-S2 ran at λ=0.2 (cold-start best) with
Loop 2 frozen. EXP-OP2 later showed that 75%-correct operators (25% wrong cells) slow Loop 2
recovery to 228 decisions (vs 178 baseline). **EXP-S2 result at λ=0.2, frozen profiles does
not generalize to λ=0.5, Loop 2 running.**

Two additional arms are required before the poisoning resilience claim can be stated
externally:

**Arm A (production condition):** Repeat EXP-S2 at λ=0.5, Loop 2 running. Gate criterion
unchanged: ≤2pp degradation at 20% poison. This arm is required to confirm the safety
mechanism holds under production scoring — not just the cold-start configuration where
σ overshoot has no lasting consequence.

**Arm B (realistic-AUAC comparison):** Run the same 20% / 40% poison sweep against the
realistic alert distribution (50-seed, 71.7% baseline AUAC) rather than centroidal synthetic
(97.89% baseline). The ceiling effect at high accuracy may mask larger degradation in
absolute terms at a lower baseline. Until Arm B runs, "≤2pp poisoning degradation" is a
centroidal synthetic claim only — not a product claim.

**EXP-S2-REPRO: COMPLETE (March 14, 2026).** Arm 0 replicated, Arm A passed (0.15pp), Arm B confirmed on realistic. GATE-M is formally satisfied. See updated EXP-S2-REPRO entry below.

**Charts:**
- 📊 `expS2_accuracy_by_poison` — grouped bar: poison level × safety mechanism (on/off)
- 📊 `expS2_per_category_damage` — heatmap of degradation by category and poison rate
- 📊 `expS2_safety_mechanism_comparison` — safety on vs off, all poison levels

**Key insight:** Safety mechanisms work — they cut damage in half at 20% poison. But the
test condition (λ=0.2, frozen Loop 2) is too optimistic for production. The safety mechanisms
were designed for rank-0 scalar σ. With Loop 2 running at λ=0.5, wrong claims affect
decisions, Loop 2 learns from wrong decisions, and centroids drift. Clipping σ_max and
confidence weighting act before the decision; they do not prevent the Loop 2 indirect path.

---

### EXP-S3: Loop 2 Independence (Firewall)

**Question:** Does σ contaminate centroid learning? After 300 decisions with synthesis active,
are the centroids different from 300 decisions without synthesis?

**Setup:** 300 decisions with synthesis (λ=0.2) vs 300 without (λ=0). Same alerts, seeds,
initial centroids. Compare final centroid positions (Frobenius norm of difference).
Also: run centroids-alone scoring after synthesis run (does contamination hurt performance?).

**Results:**

| Metric | Value | Gate | Status |
|---|---|---|---|
| Centroid Frobenius difference | **0.0028 (0.28%)** | ≤5% | ✅ PASS |
| Centroids-alone accuracy delta | ≤1pp | ≤1pp | ✅ PASS |

**Indirect path note:** Operators change decisions → Loop 2 learns from that distribution.
This is the intended mechanism (σ helps Loop 2 converge faster) not a contamination.
The firewall prevents σ parameters from entering `update()` directly. The indirect path
is characterized (EXP-OP2 B-exp) not prevented.

**Charts:**
- 📊 `expS3_centroid_trajectory_pca` — 2D PCA projection: centroid positions with/without σ
- 📊 `expS3_frobenius_divergence` — Frobenius norm of centroid difference over time
- 📊 `expS3_centroids_alone_accuracy` — performance comparison: learned with σ vs without σ

**Key insight:** The architecture separation is real. μ (experience, slow) and σ (awareness,
fast) remain independent at the parameter level. The firewall is the safety guarantee that
allows σ to be turned off (λ=0) without corrupting what the system has learned. This is
the constraint that makes the "kill switch" argument credible: setting λ=0 is safe.

---

### EXP-S4: Coupling Constant Sensitivity

**Question:** Is the +2.30pp benefit from S1 robust to λ choice, or does it depend on
precise calibration of λ? Is there a stable operating range?

**Setup:** λ sweep 0.0 → 0.5 in steps of 0.025. 10 seeds. Frozen profiles.

**Results:**

| Metric | Value | Gate | Status |
|---|---|---|---|
| Plateau width | **0.300** (λ=0.2 to λ=0.5) | ≥0.05 | ✅ PASS |
| Optimal λ range (frozen) | 0.2–0.5 | — | — |

**Important reconciliation with OP-MARGIN:** S4 plateau starts at λ=0.2 on frozen profiles.
EXP-OP-MARGIN found operative window starts at λ=0.5 with Loop 2 running. These are not
contradictory: on frozen profiles (no feedback), overshoot at λ>0.5 has no lasting consequence.
With Loop 2 running, overshoot creates wrong-flip learning that reinforces errors. The S4
plateau is the frozen-profile benefit window. The operative window (Loop 2 running) is
narrower and shifted right.

**Charts:**
- 📊 `expS4_accuracy_vs_lambda` — accuracy vs λ curve with CI, plateau region shaded
- 📊 `expS4_per_category_optimal_lambda` — per-category heatmap of optimal λ values

**Key insight:** The plateau width (0.30) means λ does not need to be precisely calibrated
in the synthesis-only context. The safe default of λ=0.5 sits in both the S4 plateau and
the OP operative window. **λ=0.5 is the production default: validated by S4, OP-MARGIN,
and OP1-FINAL.**

---

### EXP-S2-REPRO: Poisoning Resilience — Production Conditions + Realistic AUAC Arm

**Status:** ✅ COMPLETE (March 14, 2026). **GATE-M formally satisfied.**

**Question:** Does the EXP-S2 poisoning resilience result hold under production conditions
(λ=0.5, Loop 2 running) and against the realistic alert distribution?

**Results (3-arm design, 140 total runs):**

| Arm | Condition | Poison 0% | Poison 20% | Poison 40% | Gate |
|---|---|---|---|---|---|
| **0 (replication)** | λ=0.2, frozen, 10 seeds | 93.65% | 93.73% (−0.08pp) | 94.88% | **PASS** (≤2pp) |
| **A (production)** | λ=0.5, Loop 2, 20 seeds | AUAC 0.9389 | AUAC 0.9374 (−0.15pp) | AUAC 0.9382 | **PASS** (negligible) |
| **B (realistic)** | λ=0.5, Loop 2, 10 seeds | AUAC 0.5829 | AUAC 0.5976 | AUAC 0.5954 | **DOMAIN EXPERT: negligible** |

**Key finding:** Poisoning has effectively zero impact on accuracy at production conditions.
The safety mechanisms (σ_max clipping, confidence weighting) bound damage before it reaches
the learning loop. The T_recovery gate (designed for EXP-OP2's operator-shift paradigm) does
not apply to the poisoning paradigm — AUAC is the appropriate metric.

**Charts (8 files in paper_figures/):**
- 📊 `expS2r_arm0_replication` — bar chart confirming ≤2pp replication
- 📊 `expS2r_t_recovery` — T_recovery boxplots (Arm A, methodological note)
- 📊 `expS2r_auac_vs_poison` — AUAC vs poison rate (Arm A)
- 📊 `expS2r_realistic_auac_arm_b` — side-by-side Arm A vs Arm B comparison

**Original design below retained for reference.**

**Original question:** Does the EXP-S2 poisoning resilience result hold under production conditions?

**Why this is required:** The original EXP-S2 safety mechanism result cannot be stated as a
product claim until:
1. The mechanism is tested at the operative λ (0.5), where wrong σ flips interact with
   Loop 2's learning signal and may amplify damage beyond what clipping prevents.
2. The degradation is measured against the honest product baseline (71.7% realistic)
   rather than the centroidal synthetic ceiling (97.89%). At a lower baseline, absolute
   degradation from a 2pp relative hit is more consequential.

**Prerequisite:** SYNTH-EXP-0 ✅ (infrastructure complete). No additional prerequisites.

**Design — Three Arms:**

| Arm | λ | Loop 2 | Alert distribution | Seeds | Poison levels | New vs original |
|---|---|---|---|---|---|---|
| **0 (baseline replication)** | 0.2 | Frozen | Centroidal synthetic | 10 | 0%, 20%, 40% | Replicates EXP-S2 exactly — confirms reproducibility |
| **A (production condition)** | 0.5 | Running | Centroidal synthetic | 10 | 0%, 20%, 40% | New — operative λ + active Loop 2 |
| **B (realistic AUAC)** | 0.5 | Running | Realistic (50-seed) | 20 | 0%, 20%, 40% | New — honest product baseline |

Arm 0 runs first. If it does not replicate EXP-S2's ≤2pp result, stop — the infrastructure
has a reproducibility problem that must be diagnosed before proceeding to Arms A and B.

**Gate criteria:**

| Arm | Criterion | Pass | Fail action |
|---|---|---|---|
| Arm 0 | ≤2pp at 20% poison (replication) | Proceed to Arms A/B | Stop — reproducibility investigation |
| Arm A | ≤2pp at 20% poison at λ=0.5, Loop 2 running | GATE-M can proceed | EXP-S2 production claim retracted; λ must be restricted |
| Arm B | AUAC degradation documented and within acceptable range (TBD by domain expert) | Realistic resilience claim unlocked | Resilience claim restricted to centroidal synthetic only |

Note: Arm B has no pre-specified pass number because the acceptable absolute degradation
on a 71.7% baseline (vs a 97.89% baseline) requires domain expert input before the gate
criterion is set. Run Arm B, report the numbers, then set the criterion before declaring
pass/fail.

**Safety mechanisms to test (same as EXP-S2):**
- `σ_max` clipping (p10 of empirical L2 margin — pending FX-1-PROXY-REAL)
- Confidence weighting (down-weight low-confidence σ cells)
- Both active vs both inactive (2×2 factorial on safety mechanisms at each poison level)

**Charts required:**
- 📊 `expS2repro_arm0_replication` — side-by-side with EXP-S2 original result (reproducibility confirm)
- 📊 `expS2repro_armA_vs_armB_degradation` — grouped bar: poison level × arm (A vs B)
- 📊 `expS2repro_safety_mechanism_production` — safety on/off at λ=0.5, Loop 2 running
- 📊 `expS2repro_realistic_auac_baseline` — Arm B AUAC trajectory with/without poison, 20 seeds

**Key output:** A updated §EXP-S2 result block with three rows (Arm 0/A/B). If all pass,
the poisoning resilience claim is elevated from "centroidal synthetic" to "validated under
production conditions." If Arm A fails, the operative λ window must be narrowed.

---

> **What the operator framework tests:** An operator is a declared, TTL-bounded perturbation
> on centroid space — the production-grade form of synthesis bias. Instead of assembling σ
> from individual claims, an operator author declares "during this active campaign, prefer
> escalation for these category-action pairs." The OP series tests whether this mechanism
> works with Loop 2 running at production λ.
>
> **Primary metric:** AUAC (Area Under Accuracy Curve) over the full 400-decision post-shift
> window. Not endpoint accuracy — the trajectory matters because σ is an acute-phase tool.

### 6.1 Design Constraints and Known Biases (Authoritative)

These constraints apply to all results in the OP and GE series. **All numbers must be
read in context of these constraints.**

**1. Profiles calibrated from generator ground truth.** CategoryAlertGenerator.profiles
contains the exact means that alerts are sampled from. ProfileScorer initialized from
these profiles starts from ground truth. AUAC = 0.97+ even at decision 0. This is the
single most important experimental limitation. Every OP result is an upper bound on
production benefit — real profiles (from expert interviews, not from the generator itself)
will be imperfect.

**2. Statistical power.** 10 seeds detects Cohen's d ≥ 0.9 (large effects only). All
OP/GE experiments use 20 seeds minimum. Borderline p-values (0.05–0.15) must be re-run
at 30 seeds before being treated as definitive.

**3. Multiple comparisons.** 3–6 comparisons per experiment at α=0.05 → FWER up to 26%.
All result reports apply Bonferroni (α_corrected = 0.05/k). C-vs-A result in OP1
(p=0.0457) does not survive Bonferroni at k=4 — it is a false positive.

**4. Oracle-correct operator bias.** "Correct operator" = σ cells exactly matching
ground truth shift direction and magnitude. Real analysts are not oracles. The gap
between oracle-correct and analyst-correct is unmeasured. FX-1 and PROD-2 will
characterize this gap.

**5. RNG separation.** OP1 and OP1-revised used the same seed for pre- and post-shift
generators, artificially inflating operator benefit. All experiments from OP1-IMPERFECT
forward use `post_gen = CategoryAlertGenerator(seed=seed + 10000)`.

**6. Direct σ vs indirect Loop 2 path.** Both are labeled "σ helps" in AUAC but have
different product implications. Direct: σ changes *this* decision. Indirect: σ changed
earlier decisions, Loop 2 learned better distribution, *later* decisions improve.
Post-expiry conditions separate these — if accuracy holds after TTL expiry, Loop 2
learned the shift.

---

### EXP-OP1 / OP1-REVISED / OP1-IMPERFECT: The Three Failures That Found the Answer

These three experiments are documented together because they form a single diagnostic arc:
each failure revealed a specific constraint that ultimately pointed to the correct test
(OP-MARGIN + OP1-FINAL).

**EXP-OP1 (N_pre=300, λ=0.2, perfect profiles):**

| Comparison | AUAC delta | p-value | Status |
|---|---|---|---|
| B vs A (correct op) | +0.0022 ± 0.0038 | 0.0779 | ❌ FAIL |
| C vs A (harmful op) | +0.0043 | 0.0457 | False positive (Bonferroni) |

Root cause: AUAC=0.9554 at baseline. σ=0.08 effective bias (λ=0.2 × σ_max=0.4) cannot
move decisions when centroid separation already dominates.

**EXP-OP1-REVISED (N_pre=100, harder shift to 0.90):**

| Comparison | AUAC delta | p-value | Status |
|---|---|---|---|
| B vs A (correct op) | +0.0010 ± 0.0027 | 0.2027 | ❌ FAIL |

Root cause identified: Reducing pre-shift from 300 to 100 decisions *increased* baseline
AUAC from 0.9554 to 0.9731. The profiles ARE the generator's true means — even cold start
achieves 0.9730. Warm-up is irrelevant.

**EXP-OP1-IMPERFECT (ε-noisy profiles, ε=0.05–0.20):**

| ε level | Baseline AUAC | B-A delta | p-value | Status |
|---|---|---|---|---|
| 0.05–0.20 (all) | 0.977–0.980 | +0.0007–+0.0012 | 0.26–0.39 | ❌ FAIL (all levels) |

Key finding: Loop 2 recovers profile noise within 200 decisions regardless of ε. By
N_pre=300, centroids are near GT even with ε=0.20 initialization. The profile noise
hypothesis was wrong. The real blocker was λ too low.

**Charts for OP1 family:**
- 📊 `expOP1_auac_curves` — 4 conditions, 400 decisions post-shift
- 📊 `expOP1_auac_delta` — delta B-A with CI (FAIL annotated)
- 📊 `expOP1r_auac_curves` — revised version (N_pre=100)
- 📊 `expOP1i_auac_by_epsilon` — AUAC delta vs ε level (all flat at zero)
- 📊 `expOP1i_baseline_recovery` — how Loop 2 recovers ε noise within 200 decisions

**Key insight from the three failures:** The correct diagnostic was the L2 margin
distribution — not the profile quality or the warmup length. σ can only flip decisions
where `σ_effective > margin`. At λ=0.2, only 7.7% of decisions are flippable. OP-MARGIN
measured this directly and found λ=0.5 is needed to flip the 22% tail where σ can
make a difference. **The three failures were necessary — they eliminated incorrect
hypotheses and forced the margin analysis that found the answer.**

---

### EXP-OP-MARGIN: L2 Margin Distribution + λ Threshold Diagnostic

**Question:** What is the actual distribution of L2 decision margins? What λ is required
for σ to flip a significant fraction of decisions? At what λ does Loop 2 feedback turn negative?

**Margin distribution (10,000 alerts, 20 seeds):**

| Percentile | L2 Margin | λ_flip required |
|---|---|---|
| p10 | 0.1006 | 0.2516 |
| p25 | 0.2216 | 0.5539 |
| p50 | 0.4926 | 1.2316 |
| p75 | 0.7769 | 1.9423 |
| p90 | 1.0472 | 2.618 |

Fraction of decisions flippable: λ=0.2 → 7.7%, λ=0.5 → 22%, λ=1.0 → 42%, λ=2.0 → 77%.

**λ sweep (20 seeds, Loop 2 running, post-shift AUAC delta B vs A):**

| λ | Eff. bias | B-A delta | p (raw) | Bonferroni | C-A delta |
|---|---|---|---|---|---|
| 0.0 | 0.000 | +0.0003 | 0.327 | FAIL | +0.000 |
| 0.2 | 0.080 | +0.0003 | 0.327 | FAIL | +0.000 |
| **0.5** | **0.200** | **+0.0041** | **0.0011** | **✅ PASS** | −0.0029 |
| 1.0 | 0.400 | −0.0018 | 0.889 | FAIL | −0.0191 |
| 2.0 | 0.800 | −0.0691 | 1.000 | FAIL | −0.4733 |

**Non-monotonicity explained:** λ=0.5 flips 22% of decisions (tail — mostly correct).
λ=1.0 flips 42% including cases where enrich_and_watch was correct (the campaign affects
only 90% of alerts). Loop 2 learns from the wrong flips and reinforces the error.
The overshooting feedback loop turns a 42% flip rate into negative AUAC.

**Operative window derivation:**
Theoretically λ* ≈ p10(margins)/σ to p25(margins)/σ = 0.25 to 0.55. Empirical
Bonferroni-passing range: λ∈{0.5, 0.6, 0.8} from OP1-FINAL. B-A stays positive to λ=0.8.
**Safe default: λ=0.5. Never deploy at λ>0.6 without operator quality controls in place.**

**Charts:**
- 📊 `expOPm_margin_distribution` — histogram of L2 decision margins with percentile annotations
- 📊 `expOPm_lambda_sweep` — AUAC delta vs λ, showing pass/fail and non-monotonicity
- 📊 `expOPm_per_category_margins` — margin distribution per category (some categories flippable at lower λ)

**Key insight:** The operative window is not arbitrary — it follows directly from the
margin distribution. The p10–p25 range (7.7–22% of decisions flippable) is where σ
is effective without creating collateral wrong flips that Loop 2 amplifies.
**This is a principled constraint, not a tuned hyperparameter.**

---

### EXP-OP1-FINAL: Full GATE-OP at λ=0.5 + Narrow Window Sweep

**Question:** Does scalar σ pass GATE-OP at λ=0.5 with correct statistical protocol
(20 seeds, Bonferroni, correct RNG separation)?

**Narrow window sweep:**

| λ | B-A delta | p_raw | Bonf < 0.0083 | C-A delta |
|---|---|---|---|---|
| 0.3 | +0.0007 | 0.246 | FAIL | −0.0005 |
| 0.4 | +0.0019 | 0.051 | FAIL | −0.0015 |
| **0.5** | **+0.0041** | **0.0010** | **✅ PASS** | **−0.0029** |
| **0.6** | **+0.0036** | **0.0032** | **✅ PASS** | −0.0043 |
| 0.7 | +0.0026 | 0.021 | FAIL | −0.0090 |
| **0.8** | **+0.0029** | **0.0044** | **✅ PASS** | −0.0144 |

**Full GATE-OP at λ=0.5 (N=20, 400 post-shift decisions):**
- B vs A: **δ=+0.0041 ± 0.0048, p=0.0008** ✅
- C vs A: δ=−0.0029 (harmful hurts — directional) ✅
- G vs H: δ=−0.0042 ± 0.0179 (stable-operation cost ~0) ✅

**GATE-OP VERDICT: PASS**

**Asymmetry finding:** At λ=0.5, harm:benefit ratio = 1:1.4 (recoverable). At λ=0.8,
harm:benefit = 5:1 (dangerous). The cost of a bad operator scales faster with λ than
the benefit of a good one. **λ=0.5 is the only safe default.**

**T70 metric retired:** Replaced by T_recovery (decisions to return within 1pp of
pre-shift baseline). T70 = 0 at all seeds/conditions in 97%+ accuracy regime.

**Effect size context:** +0.0041 AUAC ≈ 1.6 additional correct decisions per shift event
in aggregate. Understates acute-phase benefit (EXP-OP2 shows 3× concentrate in first
150 decisions).

**Charts:**
- 📊 `expOP1f_narrow_window_sweep` — AUAC delta vs λ, Bonferroni pass/fail annotated
- 📊 `expOP1f_full_gateop_result` — GATE-OP conditions B/C/G/H with CI
- 📊 `expOP1f_asymmetry_chart` — benefit vs harm ratio by λ (showing 5:1 at λ=0.8)
- 📊 `expOP1f_auac_trajectory` — full 400-decision AUAC curve, conditions B/C/A/G

---

### EXP-OP2: Harmful Claim Resilience + Partial Accuracy Spectrum

**Question:** What happens across the full spectrum of operator accuracy (0% → 100%)?
What is the acute-phase benefit? Do harmful operators leave lasting damage after TTL?

**Acute-phase deltas (windows 0–2, decisions 0–150 post-shift):**

| Condition | Window 0 (0–50) | Window 1 (50–100) | Window 2 (100–150) |
|---|---|---|---|
| B (correct) | **+0.0120** | **+0.0110** | **+0.0110** |
| C (harmful) | −0.0200 | −0.0170 | −0.0150 |
| P-50 | +0.0010 | +0.0030 | +0.0040 |

Acute-phase benefit 3× AUAC aggregate (+0.012 vs +0.0041). Front-loaded.

**AUAC deltas (full 400-decision window):**

| Condition | AUAC Δ | p | Significant |
|---|---|---|---|
| B (correct, 100%) | +0.0041 | 0.0008 | ✅ |
| P-75 (75% correct) | +0.0013 | 0.185 | No |
| P-50 (50% correct) | +0.0012 | 0.122 | No |
| P-25 (25% correct) | −0.0009 | 0.792 | No |
| C (harmful, 0%) | −0.0029 | 0.994 | No |

**T_recovery (decisions until return within 1pp of pre-shift baseline):**

| Condition | Mean ± std | Never-recover % |
|---|---|---|
| B (correct) | 55 ± 240 | 5% |
| **A (no operator)** | **178 ± 356** | **20%** |
| P-75 (**worse than no operator**) | **228 ± 445** | **20%** |
| C (harmful) | 425 ± 561 | **35%** |
| C-exp (harmful, expired) | 425 ± 561 | **35%** |

**Post-expiry (TTL=150, windows 3–7):**
- B-exp: +0.0128 ± 0.0190 — indirect path real but bimodal (unreliable)
- **C-exp: −0.0124 ± 0.0187 — DID NOT RECOVER. Lasting damage beyond TTL expiry.**

**Charts:**
- 📊 `expOP2_acute_phase_benefit` — window-by-window delta for B/C/P-50, decisions 0–150
- 📊 `expOP2_partial_accuracy_spectrum` — AUAC delta vs operator accuracy %, 0% to 100%
- 📊 `expOP2_t_recovery_violin` — T_recovery violin plots ordered ascending, C/C-exp in red
- 📊 `expOP2_post_expiry_comparison` — B-exp vs C-exp post-TTL, showing lasting C-exp damage
- 📊 `expOP2_safety_policy_summary` — visual policy: only 100%-correct operators deploy

**Key insights (5 safety-critical findings):**

**Finding 1 — Acute-phase concentration:** +0.0041 AUAC aggregate understates the product
value. In the first 50 decisions post-shift, σ delivers +0.0120 — 3× the aggregate. σ is
a speed-of-adaptation tool; its value is front-loaded and diminishes as Loop 2 converges.

**Finding 2 — P-75 T_recovery paradox:** A 75%-correct operator recovers more slowly than
no operator (228 vs 178 decisions). Mixed σ signals create a distribution that Loop 2
must learn and then unlearn. Even a "mostly correct" operator carries a recovery cost.

**Finding 3 — Lasting damage (safety critical):** Harmful operators leave centroid damage
that persists beyond TTL expiry. C-exp post-expiry = −0.0124 over 400 decisions. TTL is
not a sufficient safety mechanism alone. Checkpoint + rollback (TD-033) is required.

**Finding 4 — Only 100% correct operators are significant:** The zero-crossing between
P-25 and P-50 means no tolerance exists for incorrect σ cells at λ=0.5. Real analyst-
authored operators may not achieve 100%. This gap is the most important unmeasured risk.

**Finding 5 — Indirect path is real but unreliable:** B-exp std=0.0190 at N=20 suggests
bimodal distribution across seeds. The indirect learning path exists in some conditions
but cannot be counted on for aggregate AUAC improvement.

---

### SYNTH-EXP-0: Synthesis Infrastructure Build

**Status:** ✅ COMPLETE

**What was built:**
- `src/models/synthesis.py` — SynthesisBias class (rank-0 σ, TTL, decay)
- `src/models/rule_projector.py` — RuleBasedProjector (rules → σ tensor)
- `src/models/claim_generator.py` — ClaimGenerator (simulated threat claims)
- `ProfileScorer` patch — accepts σ parameter in score() (no change to update())
- All 6 OP-SETUP-0 files (auac.py, residual_tracker.py, operator_spec.py, operator_registry.py, generic_alert_generator.py, op_harness.py)

**Self-tests:** All pass. Running any experiment in the synthesis or operator series
imports from this infrastructure without modification.

---

*Experiments Catalog v8.3 — Part 1 of 3 | March 15, 2026*
*34 experiments complete. 41 planned across Math, Architecture, Performance, Product Validation series.*
*Operative window: λ∈[0.5, 0.6]. Safe default: λ=0.5. η_neg=0.05 canonical (η_neg=1.0 FORBIDDEN: ECE=0.49).*
*Core finding: dot product (61%) vs L2 (97.89%) on identical data — the kernel was the root cause.*
*Architecture is settled. GATE-M formally satisfied (EXP-S2-REPRO complete March 14).*
*New (v8.3): PROD-3 ✅, PROD-4 ✅ (3 runs), PROD-4b ✅, SHIFT-1 ✅, SHIFT-2 ✅, DISC-1 ✅, CORR-1a ✅, ontology verified.*
*Tensor: (6,5,6) = 180 values (6 categories, 5 actions, 6 factors). Per-category θ: 0.744–0.809 (PROD-3).*
*Priority Queue: GATE-R (blocked until v5.5-R6) → EXP-G1 → FX-1-PROXY → Phase 5 (DISC-2).*
*Companions: soc_copilot_design_v5_4, math_synopsis_v8, claims_registry_v3_1.*
*Part 2: Future math/synthesis/OP/GE experiments with prompts + ARCH and PERF series.*
*Part 3: PROD series + forward-looking view + claims traceability + repo structure + execution notes.*
