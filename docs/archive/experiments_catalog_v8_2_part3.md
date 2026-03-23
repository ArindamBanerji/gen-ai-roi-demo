# Experiments Catalog — Compounding Intelligence Platform

**Version:** 8.3 · Part 3 of 3 · March 15, 2026
**Covers:** §§14–19 — PROD series (product/deployment experiments), forward-looking view
by product version (v5.5 / v6.0 / v7.0+), claims traceability matrix, repository
structure (all three repos + experiments repo), execution notes and operating rules.

**Cross-references:**
- Part 1: §§1–6 — Dashboard, Insight Register, accuracy waterfall, completed experiments
  (foundation, synthesis, operator series EXP-OP1 and EXP-OP2), OP series summary
- Part 2: §§7–13 — Priority queue (6 experiments), OP3–OP6, GE1–GE4, FX series,
  synthesis pipeline S5a–S8, ARCH series, PERF series
- This Part 3: §§14–19 — PROD series, version roadmap, claims traceability, repos,
  execution notes

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
>     Calibration Science series (SHIFT-1, SHIFT-2, DISC-1, DISC-2) added to §14.
> (6) **GATE-R unblocked.** CORR-1a routing fix: 68% misroute eliminated.
> (7) **Tensor shape: (5,5,6) → (6,5,6).** 5 → 6 categories; 25 → 30 cells; 150 → 180 values.
>
> **Changes from v8.1 → v8.2 (March 14, 2026):**
> (1) **§15 v5.5 experiment gates updated.** FX-1-PROXY-REAL, EXP-S2-REPRO marked complete.
>     GATE-M decision updated from "end of v5.5 sprint" to "formally satisfied March 14."
>     FUTURE-03 and FUTURE-09 marked promotable.
> (2) **§16 claims traceability updated.** CLAIM-17 NR rate: 38% [29%, 48%] (was 35%, N=20).
>     CLAIM-27 experiment count: 28 (was 25). FUTURE-03 and FUTURE-09 promotion status added.
> (3) **§18.6 prompt readiness updated.** 3 experiments moved from Full Prompt to Complete.
>     Immediately executable list updated.
> (4) **§19.2 pending updates refreshed.** New row: experiments_catalog v8.1 → v8.2.
>     claims_registry update needed (FUTURE-03, FUTURE-09 promotion). math_synopsis σ_max note.
> (5) **§19.3 execution order updated.** Items 2–4 (FX1, S2-REPRO, OP2-N100) marked complete.
>     Next actions: GATE-R (still blocked) → write §17.5 → PROD-3 → EXP-G1.
> (6) **Production companion paper reference added.** [Banerji, 2026c] — 29 experiments
>     including adversarial robustness, poisoning resilience, distribution characterization.

> **Changes from v8.0 → v8.1:**
> (1) **Companion references updated throughout.** `soc_copilot_design_v5_3` → `v5_4`
>     in PROD-1, PROD-2, PROD-5, §17.4 repo structure, and §18.7 deferred updates table.
>     `math_synopsis_v6` → `v7` in §16.1 claims table (CLAIM-22 through CLAIM-25).
>     CLAIM-27 updated from "v8.0 catalog" to "v8.1 catalog".
> (2) **§15 GATE-R execution constraint added.** GATE-R appears in both the v5.0 and v5.5
>     experiment sections. Both now note that GATE-R is execution-blocked until v5.5-R6
>     ships (complete alert_type → category mapping, TD-037). The priority position is
>     unchanged — the prompt is correct, the execution is blocked.
> (3) **§18.3 GATE-M pass condition updated.** EXP-S2-REPRO now requires both Arm A
>     (production condition: λ=0.5, Loop 2 running) and Arm B (realistic-AUAC arm) to
>     complete before formal GATE-M is declared. Arm B has an open gate (domain expert
>     review required before pass/fail). Updated to match Parts 1 and 2.
> (4) **§18.6 prompt readiness table corrected.** ARCH-3 moved from ✅ Full Prompt to
>     🔧 Spec Ready (blocked by §17.5 not yet written — failure test protocol depends on
>     rollback execution semantics). EXP-S6 and EXP-S7 promoted from 🔲 Design Pending
>     to 📐 Partial (judge rubrics now written in Part 2). Totals updated accordingly.
>     GATE-R execution constraint noted.
> (5) **§18.7 deferred updates table updated.** `soc_copilot_design_v5_3` → `v5_4`.
>     New row added: `soc_copilot_design_v5_4 §17.5` (rollback execution semantics — not
>     yet written, blocks ARCH-3).
> (6) **§19.2 pending updates refreshed.** `math_synopsis_v7` row marked complete (done).
>     New row added for experiments catalog v8.1 updates. Remaining pending items updated
>     to reflect current session work.
> (7) **§19.3 execution order updated.** GATE-R step now carries execution-blocked note.
>     EXP-S2-REPRO step notes 3-arm design (Arm 0 replication / Arm A production / Arm B
>     realistic-AUAC).

---

## 14. PROD Series — Product and Deployment Experiments

> **Why these exist:** The math is validated (34 experiments). The architecture is tested
> (ARCH series). The performance is characterized (PERF series). The PROD series answers
> the final category of questions: does the product work for a real enterprise buyer?
>
> These experiments are product-facing, not math-facing. They test customer-visible
> features: the Institutional Knowledge Score, the NL template readability, the shadow
> mode agreement baseline, the category-specific threshold calibration, and the category
> learning convergence timeline. All five directly gate claims the sales team needs to
> make in CISO conversations.
>
> **Run venue:** soc-copilot repo (not cross-graph-experiments). Most require v5.5 features.
> **Dependency on ARCH/PERF:** ARCH-3 (hook reliability) and PERF-1 (scorer latency) should
> pass before PROD experiments run — product experiments assume the infrastructure works.

**Execution order within PROD:** PROD-3 → PROD-1 → PROD-4 → PROD-2 → PROD-5.
PROD-3 (shadow mode baseline) first because it requires the least new infrastructure.
PROD-1 (IKS) second because its metric drives PROD-2 and PROD-5 interpretation.

---

### PROD-1: Institutional Knowledge Score (IKS) Sensitivity Analysis 🔧 SPEC READY

**Compute: local | Version: v5.5-R4 | Prerequisite: IKS feature built (v5.5 sprint)**

**Background:** The IKS formula (from soc_copilot_design_v5_4 §3.4) is:
`IKS = 100 × min(mean_L2_distance(μ(t), μ(0)) / 0.30, 1.0)`

The normalization constant 0.30 is a design choice — it sets the maximum centroid drift
that corresponds to IKS=100. The formula has not been empirically calibrated. Two risks:
(1) centroid drift is so small that IKS stays near 0 forever (Chart A showing ≈0 is still
the documented failure), and (2) a genuine shift of 0.30 Frobenius per cell is only reached
after hundreds of decisions, making IKS hard to interpret during the demo window (first
200 decisions). This experiment validates the IKS formula on the simulation pool and
proposes a calibrated normalization constant.

**Question:** Under the simulation pool (50-seed realistic, 200 decisions),
what range does IKS typically reach? Does a warmup of 200 decisions produce a
"demonstrable" IKS value (IKS ≥ 15) in the demo window? What normalization constant
produces a 0–100 trajectory that a CISO can interpret as "this system is learning"?

**Setup:** 50 seeds, 200 decisions each, realistic distribution, no synthesis. At each
decision: compute IKS using the formula above. Sweep normalization constant κ ∈
{0.05, 0.10, 0.15, 0.20, 0.25, 0.30}. Report: IKS(t) trajectory, IKS at t=50/100/200,
and the κ value at which IKS(200) ≥ 15 in ≥90% of seeds.

**Gate:** Identify κ* such that IKS(200) ∈ [15, 40] in ≥90% of seeds (not too low, not
saturated). If no κ achieves this, flag for formula redesign. Gate is characterization,
not pass/fail.

**Decision output:** Recommend κ* for v5.5-R4 IKS implementation. Document
"IKS ≥ 15 after 200 decisions is the expected demo outcome — not a claim, a calibration."

**Charts (3 PNG + 3 PDF):**
- 📊 `prod1_iks_trajectory_by_kappa` — IKS(t) mean ± std over 200 decisions for all 6 κ
  values. Horizontal dashed lines at 15 and 40 (interpretable range). Vertical at t=200
  (demo window boundary). Legend: "κ=[value], IKS(200)=mean±std"
- 📊 `prod1_iks_at_decision_milestones` — bar chart: IKS value at t=50, t=100, t=200 for
  each κ. 95% CI across 50 seeds. Reference band: 15–40. Bars outside band colored red.
- 📊 `prod1_kappa_recommendation` — scatter: κ vs IKS(200) mean. Color: green if IKS(200)
  ∈ [15,40], red otherwise. Annotate recommended κ*. Include a table: "Demo outcome at
  recommended κ: IKS ≥ 15 in X% of seeds after 200 decisions."

**Claude Code Prompt:**

```
PROD-1: IKS Sensitivity Analysis

Venue: soc-copilot repo (or cross-graph-experiments with simulation pool)
Location: tests/prod/prod1_iks_sensitivity/ (create directory)

Files to create:
  1. tests/prod/prod1_iks_sensitivity/run.py
  2. tests/prod/prod1_iks_sensitivity/charts.py

run.py:
  from src.models.profile_scorer import ProfileScorer, build_profile_scorer
  from src.data.category_alert_generator import CategoryAlertGenerator
  import numpy as np

Parameters:
  N_seeds = 50
  N_decisions = 200
  C, A, d = 6, 5, 6
  tau = 0.1
  kappa_values = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]

IKS formula per kappa:
  def compute_iks(mu_t, mu_0, kappa):
    """IKS = 100 * min(mean_L2_distance(mu_t, mu_0) / kappa, 1.0)"""
    # mu shape: (C, A, d)
    per_cell = np.linalg.norm(mu_t - mu_0, axis=-1)  # shape (C, A)
    mean_drift = per_cell.mean()
    return min(100.0 * mean_drift / kappa, 100.0)

For each kappa:
  For each seed:
    1. Build CategoryAlertGenerator(seed=seed, C=C, A=A, d=d)
    2. Build ProfileScorer from DomainConfig warm-start centroids
    3. mu_0 = scorer.centroids.copy()
    4. For each decision in range(N_decisions):
       - sample alert, score, simulate oracle feedback (GTAlignedOracle, noise=0.10)
       - scorer.update(...)
       - record IKS(t) = compute_iks(scorer.centroids, mu_0, kappa)
  
  Per kappa:
    - IKS_matrix: shape (N_seeds, N_decisions)
    - IKS_mean, IKS_std per timestep
    - IKS_at_50:  mean ± std across seeds at t=50
    - IKS_at_100: mean ± std across seeds at t=100
    - IKS_at_200: mean ± std across seeds at t=200
    - pct_seeds_above_15_at_200: fraction of seeds where IKS(200) >= 15

Print per kappa:
  "kappa={k}: IKS(200)={mean:.1f}±{std:.1f}, pct>=15: {pct:.0%}"

Identify kappa* = first kappa where IKS(200) mean >= 15 AND mean <= 40.
Print: "Recommended kappa*: {kappa*}. IKS(200) at kappa*: {mean}±{std}."
If no kappa achieves this: print "FLAG: IKS formula redesign required."

Call charts.py.

charts.py:
  import matplotlib
  matplotlib.use("Agg")
  import sys
  from pathlib import Path
  sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
  from src.viz.bridge_common import save_figure, COLORS

  Chart 1 (prod1_iks_trajectory_by_kappa):
    6 curves (one per kappa). X: decisions 1-200. Y: IKS mean. Std fill.
    Horizontal dashed at 15 (green, "interpretable floor") and 40 (orange, "saturation").
    Vertical dashed at t=200 (demo window). Legend per kappa.
    save_figure; plt.close; print("[CHART 1] prod1_iks_trajectory_by_kappa.png + .pdf")

  Chart 2 (prod1_iks_at_decision_milestones):
    3-group bar chart: t=50, t=100, t=200. Within each group: 6 bars (one per kappa).
    Error bars: 95% CI. Y-axis: 0-100. Shade band 15-40. Bars outside: red.
    save_figure; plt.close; print("[CHART 2]...")

  Chart 3 (prod1_kappa_recommendation):
    Scatter: kappa (x) vs IKS(200) mean (y). Error bars on y.
    Color: green if mean in [15,40], red otherwise. Annotate kappa*.
    Table printed below chart: Demo outcome summary.
    save_figure; plt.close; print("[CHART 3]...")

Tests before declaring done:
  50 seeds × 200 decisions × 6 kappa = 60,000 IKS values computed.
  kappa* identified or "FLAG" printed.
  All 3 chart files in paper_figures/ as .png and .pdf.

Do not use git. Do not start debugger. Log-based debugging only.
```

---

### PROD-2: NL Template Analyst Agreement Study 📐 PARTIAL

**Compute: partner-required | Version: v6.0-R3 | Prerequisite: NL template engine built**

**Background:** The NL template engine (v5.5-T1-1, soc_copilot_design_v5_4 §4.2) converts
profile centroids into human-readable statements: "For lateral_movement alerts, the system
treats high asset_criticality (>0.8) combined with elevated pattern_history as a strong
signal for escalation." These templates are deterministic — no LLM. The question is whether
real analysts read these templates and correctly understand what the system has learned.

**Question:** When presented with the NL template description of a profile centroid, do SOC
analysts (a) accurately report what factor value the system considers "important," and
(b) agree with the centroid's recommendation on 5 test alerts?

**Setup:** 10 centroid-template pairs × 5 analysts. Per pair: present the NL template
description, ask the analyst to (a) predict the system's action on 3 presented alerts,
and (b) rate the template's accuracy on a 5-point scale. Measure interpretation accuracy
(prediction agreement) and template acceptability rating.

**Gate:** Interpretation accuracy ≥ 70% (analyst predictions match system decisions).
Template acceptability ≥ 3.5/5.0 mean. If interpretation accuracy < 70%: flag template
format for revision (too complex, wrong factor emphasis, wrong vocabulary).

**Decision output:** FUTURE-13 ("system is measurably more accurate than deployment day")
requires IKS live and interpretable. NL templates are the interpretability layer. If this
study shows analysts cannot read templates correctly, the IKS story is incomplete.

**Why partial prompt:** Study protocol requires SOC analyst access (partner-required).
Full protocol document exists in soc_copilot_design_v5_4 §4.2.3. Prompt will be written
when analyst cohort is confirmed.

**Charts (2 PNG + 2 PDF):**
- 📊 `prod2_interpretation_accuracy_by_template` — bar: prediction accuracy per template
  (10 templates). Reference dashed at 70%. Red bars below threshold.
- 📊 `prod2_acceptability_distribution` — histogram of acceptability ratings (1–5) across
  all 50 responses. Reference dashed at 3.5. Mean annotated.

---

### PROD-3: Shadow Mode Agreement Rate Baseline ✅ COMPLETE

**Compute: local | Version: v5.5-R8 | Prerequisite: Shadow mode feature built**

**Status:** ✅ COMPLETE (March 14, 2026)

**Results:**
- Per-category θ values (C=6 categories):
  - credential_access (idx 0): θ = 0.809
  - threat_intel_match (idx 1): θ = 0.762
  - lateral_movement (idx 2): θ = 0.744
  - data_exfiltration (idx 3): θ = 0.756
  - insider_threat (idx 4): θ = 0.771
  - cloud_infrastructure (idx 5): θ = 0.789
- All 6 categories covered (C=6, tensor shape 6×5×6 = 180 values)
- Frozen baseline: 80.4% accuracy, 92.9% coverage at 85% precision

**Background:** Shadow mode records the system's recommendation alongside the analyst's
actual decision. The "agreement rate" is the fraction where the system would have made the
same decision. Before first deployment, we need to know what agreement rate to expect on
the simulation pool (known-good centroids, ground-truth oracle) so we can interpret real
customer agreement rates.

**Question:** On the simulation pool with warm-start centroids (200 decisions warmup),
what is the expected shadow mode agreement rate between the ProfileScorer recommendation
and the GTAlignedOracle ground truth? Per-category? At different confidence thresholds?

**This is a calibration experiment, not a pass/fail gate.** The result is the expected
agreement rate baseline — the number the first customer's shadow report will be compared
against.

**Setup:** 50 seeds, 200 warmup decisions, 200 shadow decisions. For each shadow decision:
record (system recommendation, oracle ground truth, confidence). Compute agreement rate
overall and per-category. Compute "high-confidence agreement rate" (agreements at P ≥ 0.7,
P ≥ 0.8, P ≥ 0.9).

**Output:** The calibration table that ships with v5.5 shadow mode documentation:
"On our simulation pool (warm-start centroids, 200-decision warmup), expected shadow
mode agreement rate is [X%]. Per category: credential_access [X%], lateral_movement
[X%], ..." This table enables the first customer conversation: "Your system agreed
87% of the time with analysts. The simulation baseline is 81%. Your environment is
within [6pp] of expected."

**Charts (3 PNG + 3 PDF):**
- 📊 `prod3_agreement_rate_distribution` — histogram of per-seed agreement rates across
  50 seeds (overall). Annotate mean ± std. Vertical dashed at mean.
- 📊 `prod3_per_category_agreement` — bar chart: per-category agreement rate mean ± std.
  Ordered highest to lowest. This shows which categories the warm-start centroids handle
  best (and where first customers should expect the most disagreement).
- 📊 `prod3_high_confidence_agreement` — line: agreement rate vs confidence threshold
  (0.5, 0.6, 0.7, 0.8, 0.9). Shows the tradeoff: higher threshold = fewer decisions,
  higher agreement. Annotates: "auto-approve threshold at P≥0.9: [X%] agreement rate,
  [Y%] coverage."

**Claude Code Prompt:**

```
PROD-3: Shadow Mode Agreement Rate Baseline

Venue: cross-graph-experiments (until shadow mode is built in soc-copilot)
Location: experiments/prod/prod3_shadow_baseline/

Objective: Measure expected shadow mode agreement rate (ProfileScorer vs GTAlignedOracle)
on simulation pool with warm-start centroids. Produce calibration table for v5.5 docs.

Files to create:
  1. experiments/prod/prod3_shadow_baseline/run.py
  2. experiments/prod/prod3_shadow_baseline/charts.py

run.py:
  from src.models.profile_scorer import ProfileScorer, build_profile_scorer
  from src.models.oracle import GTAlignedOracle
  from src.data.category_alert_generator import CategoryAlertGenerator
  import numpy as np

Parameters:
  N_seeds = 50
  N_warmup = 200       # warm-start period (system learns but not in "shadow")
  N_shadow = 200       # shadow period (record agreement, no learning)
  C, A, d = 6, 5, 6
  tau = 0.1
  noise_rate = 0.10    # oracle noise (realistic)
  confidence_thresholds = [0.5, 0.6, 0.7, 0.8, 0.9]

Per seed:
  1. Build CategoryAlertGenerator(seed=seed, C=C, A=A, d=d)
  2. Build ProfileScorer from DomainConfig warm-start centroids
  3. Build GTAlignedOracle(noise_rate=noise_rate)
  
  Warmup phase (N_warmup decisions):
    - Score alert, get oracle ground truth, update centroids
    - No shadow recording during warmup
  
  Shadow phase (N_shadow decisions):
    - score_result = scorer.score(alert.factors, alert.category)
    - system_rec = score_result.action  (what system WOULD recommend)
    - oracle_action = oracle.get_action(alert)  (ground truth)
    - confidence = score_result.confidence
    - agreed = (system_rec == oracle_action)
    - record: (seed, decision, category, system_rec, oracle_action, confidence, agreed)
  
Per seed: compute
  - overall_agreement_rate = mean(agreed over N_shadow decisions)
  - per_category_agreement: {c: mean(agreed where category==c) for c in C}
  - high_conf_agreement_rate: {t: mean(agreed where confidence>=t) for t in thresholds}
  - high_conf_coverage: {t: mean(confidence>=t) for t in thresholds}

Aggregate across seeds:
  - overall: mean ± std, 95% CI (Wilson)
  - per_category: mean ± std per category
  - high_conf: mean agreement ± std per threshold, mean coverage ± std per threshold

Print calibration table:
  "=== SHADOW MODE CALIBRATION TABLE (v5.5) ==="
  "Overall agreement rate: {mean:.1%} ± {std:.1%} [{ci_low:.1%}, {ci_high:.1%}]"
  "Per-category: credential_access={X:.1%}, lateral_movement={X:.1%}, ..."
  "At P≥0.9: agreement={X:.1%}, coverage={X:.1%}"
  Print: "This table is the calibration reference for first customer shadow reports."

Call charts.py.

charts.py:
  matplotlib.use("Agg"); save_figure; plt.close; print per chart.

  Chart 1 (prod3_agreement_rate_distribution):
    Histogram of per-seed overall agreement rates (50 values). 10 bins.
    Vertical dashed at mean. Annotate: mean ± std, 95% CI.
    X-axis: "Agreement rate". Y-axis: "Seed count (out of 50)".

  Chart 2 (prod3_per_category_agreement):
    Horizontal bar chart: 6 categories ordered highest agreement to lowest.
    Error bars: 95% CI. Vertical dashed at overall mean.
    Color: category colors from COLORS dict.

  Chart 3 (prod3_high_confidence_agreement):
    Dual-axis line chart. X: confidence threshold (0.5 → 0.9).
    Left Y: agreement rate (blue, mean ± std fill). Right Y: coverage (green, mean ± std).
    Annotate: "P≥0.9: agreement={X:.1%}, coverage={Y:.1%}".
    Title: "Shadow mode agreement vs confidence threshold — simulation calibration"

Tests: 50 seeds × 200 shadow decisions = 10,000 shadow records. All 3 charts in paper_figures/.
Print calibration table to stdout AND write to prod3_calibration_table.json.

Do not use git. Do not start debugger.
```

---

### PROD-4: Auto-Approve Threshold Calibration Per Category ✅ COMPLETE

**Compute: local | Version: v5.5-R1 | Prerequisite: v5.0 ProfileScorer complete**

**Status:** ✅ COMPLETE (3 runs, March 14–15, 2026)

**Runs:**
- PROD-4 warmup: threshold* exploration, δ=0.05
- PROD-4 final: threshold* range 0.720–0.870 across categories at η_neg=0.05
- PROD-4b: calibrated refer_to_analyst confidence floors per category

**Key findings:**
- threshold* range: 0.720–0.870 across the 6 categories
- η_neg=0.05 is canonical. η_neg=1.0 produces ECE=0.49 (FORBIDDEN — catastrophic miscalibration)
- Per-category confidence floors now calibrated (see PROD-4b)

**Background:** The current global auto-approve threshold is P ≥ 0.90, producing 11.5%
coverage at 90.7% accuracy. The v5.5-R1 plan is category-specific thresholds designed
to reach 40%+ coverage at ≥85% per-category accuracy. This experiment determines what
those per-category thresholds should be.

**Question:** For each SOC category (credential_access, threat_intel_match, lateral_movement,
data_exfiltration, insider_threat, cloud_infrastructure), what confidence threshold achieves
≥85% accuracy while maximizing coverage?

> **η_neg convention:** η_neg=0.05 is canonical (symmetric with η_pos). η_neg=1.0 is FORBIDDEN
> — produces ECE=0.49 (catastrophic miscalibration, confirmed SHIFT-2). The per-category θ
> design estimate of θ=0.85 is superseded by PROD-3 results: per-category θ: 0.744–0.809.
> The confidence_floor=0.70 design estimate is superseded by PROD-4b per-category floors.

**Setup:** 50 seeds, 1,000 decisions each, realistic distributions. For each decision:
record (category, confidence, correct_or_wrong). At each threshold sweep value: measure
per-category accuracy and coverage. Find threshold* per category = lowest threshold
achieving ≥85% accuracy.

**Gate:** ≥3 of 6 categories achieve threshold* ≤ 0.75 (coverage ≥ 30% with ≥85% accuracy).
If only 1–2 categories pass: flag for IKS-gated auto-approve (hold categories below threshold
in human-review until IKS reaches 50, then lower threshold). If 0 categories pass at any
threshold: flag for centroid initialization review.

**Claims unlocked:** FUTURE-12 ("40%+ coverage at ≥85% per-category accuracy").

**Charts (3 PNG + 3 PDF):**
- 📊 `prod4_accuracy_vs_threshold_by_category` — 6 curves (one per category). X: threshold
  (0.5–0.99). Y: accuracy (of decisions above threshold). Horizontal dashed at 85%.
  Mark threshold* per category. Color-coded by category.
- 📊 `prod4_coverage_vs_threshold_by_category` — 6 curves (one per category). X: threshold.
  Y: fraction of decisions above threshold (coverage). Mark threshold* for each.
- 📊 `prod4_threshold_recommendation_table` — 6×3 table rendered as chart:
  Category | threshold* | accuracy at threshold* | coverage at threshold*.
  Green: accuracy ≥ 85%. Red: below. Caption: "Recommended per-category thresholds for v5.5-R1."

**Claude Code Prompt:**

```
PROD-4: Per-Category Auto-Approve Threshold Calibration

Venue: cross-graph-experiments
Location: experiments/prod/prod4_threshold_calibration/

Files to create:
  1. experiments/prod/prod4_threshold_calibration/run.py
  2. experiments/prod/prod4_threshold_calibration/charts.py

run.py:
  from src.models.profile_scorer import ProfileScorer, build_profile_scorer
  from src.models.oracle import GTAlignedOracle
  from src.data.category_alert_generator import CategoryAlertGenerator
  import numpy as np

Parameters:
  N_seeds = 50
  N_decisions = 1000
  C, A, d = 6, 5, 6
  tau = 0.1
  noise_rate = 0.10
  threshold_sweep = np.arange(0.50, 1.00, 0.01)  # 50 threshold values
  CATEGORIES = ["credential_access", "threat_intel_match", "lateral_movement",
                "data_exfiltration", "insider_threat", "cloud_infrastructure"]

Per seed:
  1. Build warm-start ProfileScorer (realistic, N_warmup=200 pre-run)
  2. For N_decisions: score, get oracle, update
  3. Record per-decision: (category_idx, confidence, is_correct)

Per seed × category × threshold:
  - decisions_above = decisions where category == c and confidence >= threshold
  - accuracy_at_threshold = mean(is_correct for decisions in decisions_above)
    (NaN if no decisions above threshold)
  - coverage_at_threshold = len(decisions_above) / N_decisions

Aggregate across seeds per category × threshold:
  - accuracy: mean across seeds (ignoring NaN seeds)
  - accuracy_ci: 95% CI (Wilson)
  - coverage: mean ± std

Per category: find threshold* = minimum threshold where accuracy_mean >= 0.85
If no threshold achieves this for a category: threshold* = NaN (flag)

Print recommendation table:
  For each category: threshold*, accuracy at threshold*, coverage at threshold*
  Gate verdict: "N/6 categories achieve threshold* <= 0.75"

Call charts.py.

charts.py:
  matplotlib.use("Agg"); save_figure; plt.close; print per chart.

  Chart 1 (prod4_accuracy_vs_threshold_by_category):
    5 curves, one per category. X: threshold_sweep. Y: accuracy mean.
    Std fill per curve. Horizontal dashed at 0.85 (gate threshold).
    Mark threshold* per category with a dot + label.
    COLORS: use COLORS dict from bridge_common.

  Chart 2 (prod4_coverage_vs_threshold_by_category):
    5 curves, one per category. X: threshold_sweep. Y: coverage mean.
    Std fill. Mark threshold* per category with a dot.
    Show: current global threshold (0.90) as vertical dashed line.
    Show: current global coverage (11.5%) as horizontal dashed line.

  Chart 3 (prod4_threshold_recommendation_table):
    6-row table rendered as matplotlib table. Columns: Category | threshold* | accuracy | coverage.
    Background: green if accuracy >= 0.85, red if below (or NaN).
    Title: "Recommended per-category thresholds — v5.5-R1 (per-category floors: PROD-4b)".
    Caption below: "Gate: >=3 categories pass (threshold* <= 0.75). Per-category θ: 0.744–0.809 (PROD-3)"

Tests: 50 seeds × 1000 decisions complete. threshold* computed for all 6 categories.
Gate verdict printed. All 3 charts in paper_figures/ as .png and .pdf.

Do not use git. Do not start debugger.
```

---

---

### SHIFT-1: Learning Disabled Baseline

**Status:** ✅ COMPLETE (March 14, 2026)
**Purpose:** Establish frozen scorer performance as baseline before enabling learning.
**Method:** ProfileScorer with update() disabled (freeze=True), 50 seeds.
**Results:**
- Accuracy: 80.4% (frozen baseline)
- Coverage at 85% precision: 92.9%
- This is the "floor" — learning must improve on this

---

### SHIFT-2: Learning Validation Post-Fix

**Status:** ✅ COMPLETE (March 15, 2026)
**Purpose:** Validate ProfileScorer.update() fix across noise/drift conditions.
**Method:** 24 conditions × 50 seeds (δ ∈ {0.05, 0.10, 0.20, 0.30} × noise ∈ {0, 0.05, 0.10, 0.15, 0.20, 0.25})
**Bug fixed:** correct=False previously pushed ALL centroids (including GT). Fixed to dual push/pull: push predicted away, pull GT toward.
**Key results:**
- δ=0.10: +2.7% lift (pre-fix: 0% or negative)
- Learning validated: centroid updates correctly directional post-fix
- η_neg=0.05: symmetric negative learning rate (canonical)
- η_neg=1.0: ECE=0.49 (FORBIDDEN — catastrophic miscalibration)
**Validation:** 24 conditions × 50 seeds = 1,200 runs

---

### DISC-1: Composite Discriminant Calibration

**Status:** ✅ COMPLETE (March 15, 2026)
**Purpose:** Validate composite discriminant gate for triage routing (replaces confidence-threshold-only).
**Method:** 13-feature logistic regression. Features include: confidence score, rolling_accuracy (key signal), factor vector components, IKS score, decision history.
**Results:**
- Model E: 70.4% coverage at 85% precision (vs 62.6% confidence-only baseline)
- +7.8 pp coverage improvement over confidence-only
- Per-category coverage: varies by category (credential_access highest)
- Rolling_accuracy identified as key discriminant signal

**Models evaluated:**

| Model | Features | Coverage@85%prec |
|-------|----------|-----------------|
| A | confidence only | 62.6% |
| B | confidence + IKS | 65.1% |
| C | confidence + rolling_accuracy | 68.3% |
| D | 8-feature subset | 69.7% |
| E | 13-feature full | 70.4% |

---

### DISC-2: Frozen vs Learned Through Composite Gate

**Status:** 🔲 PLANNED (Phase 5)
**Purpose:** Compare frozen scorer vs learned scorer when routed through composite discriminant gate.
**Hypothesis:** Composite gate will improve precision for both frozen and learned, but learned+gate will outperform frozen+gate.
**Dependencies:** DISC-1 ✅, SHIFT-2 ✅, composite gate implementation

---

### PROD-5: Category Convergence Rate and Onboarding Timeline 🔧 SPEC READY

**Compute: local | Version: v6.0-R3 | Prerequisite: v5.5 realistic seed data + PROD-4**

**Background:** One of the most important questions in a CISO conversation is:
"How long does it take before the system is useful for my environment?" The answer is
currently "it depends on the category and the volume of verified decisions." This experiment
produces the evidence for a specific, defensible answer.

**Question:** Starting from warm-start expert centroids (IKS=0), how many verified
decisions does each category need before the learning curve plateaus? What is the
"time-to-plateau" in days given a typical SOC alert volume (N alerts/day)?

**Setup:** 50 seeds, 2,000 decisions. For each category: compute rolling 100-window
accuracy. Plateau = first decision where rolling accuracy stays within 2pp of its own
maximum for 200 subsequent decisions. Report T_plateau per category.

**Convert to days:** Parameterize by SOC alert volume (V = 20, 50, 100, 200 verified
decisions/day). Time-to-plateau in days = T_plateau / V. This gives the "onboarding
timeline" claim.

**Gate:** Characterization. T_plateau across all categories ≤ 500 decisions in ≥80%
of seeds. If any category plateaus after 1,000 decisions: flag for expert centroid
review (initial centroids may not be close enough to the customer's real patterns).

**Claims unlocked:** FUTURE-13 ("system is measurably more accurate than deployment day"
— requires knowing when "measurably better" begins). This experiment also informs the
onboarding timeline narrative: "Within [X] days at your alert volume, each category
reaches its learned accuracy plateau."

**Charts (3 PNG + 3 PDF):**
- 📊 `prod5_learning_curves_by_category` — 5 learning curves (rolling 100-window accuracy)
  over 2,000 decisions. Each shaded ± std across 50 seeds. Plateau markers per category.
- 📊 `prod5_time_to_plateau_distribution` — boxplot: T_plateau per category. Ordered
  fastest to slowest. Reference dashed at 500 decisions (gate threshold).
- 📊 `prod5_onboarding_calendar` — heatmap: category (rows) × alert volume (columns:
  20/50/100/200 verified/day) → time-to-plateau in days. Color: green ≤ 30 days,
  orange 30–90 days, red > 90 days.

**Prompt ready once v5.5 realistic seed data (SEED-2) is built** — requires the 200+
user simulation pool from soc_copilot_design_v5_4 Phase 7 (SOC-SEED-2 prompt).

---

## 15. Forward-Looking View by Product Version

> **Reading guide:** Each section lists the experiments that must run before the version
> ships, the experiments that run during that version's deployment window, and the claims
> those experiments unlock. Version boundaries are hard gates — a version does not ship
> without its experiment prerequisites passing.
>
> **Timeline note:** Months are relative to first customer agreement. v5.0 is self-funded
> development. v5.5 produces the hosted preview. v6.0 requires a data processing agreement.

---

### v5.0 — ProfileScorer + Evaluation + Data Realism

**Status:** 29-prompt sprint in progress. Targeting tagged release before v5.5 sprint starts.
**Experiment obligations created by v5.0 (not gates — write obligations):**

| Obligation | What | Why It Cannot Wait |
|---|---|---|
| Hook 1: DecisionRecord active from day 1 | Every `score()` call writes a DecisionRecord with category assignment | GATE-R cannot run retroactively. Every day without Hook 1 is permanently lost routing accuracy data |
| Hook 2: OutcomeRecord active | Every `update()` call writes an OutcomeRecord | Loop 2 audit trail. Required for composite accuracy claims |
| Hook 3: ProfileSnapshot every 50 decisions | Full centroid tensor snapshots | TD-033 checkpoint/rollback prereq; Level 2/3 substrate |

**Experiments that run immediately after v5.0 ships (no v5.5 prereqs needed):**
- GATE-R (§7, Priority 1): routing accuracy. Needs Hook 1. Local compute. **⚠️ Execution blocked until v5.5-R6 ships** (complete alert_type → category mapping). Prompt is ready — verify and stage it now. Do not execute against the incomplete v5.0 mapping.
- ~~FX-1-PROXY-REAL (§7, Priority 2)~~: ✅ COMPLETE (March 14). KL 1.88–2.58.
- ~~EXP-S2-REPRO (§7, Priority 3)~~: ✅ COMPLETE (March 14). GATE-M satisfied. 0.15pp max.
- ~~EXP-OP2-N100 (§7, Priority 4)~~: ✅ COMPLETE (March 14). 38% [29%, 48%].
- ARCH-1 (§12): import boundary compliance. Runs against all three repos. Local.
- ARCH-4 (§12): centroid tensor portability. GAE repo. Local.
- PERF-1 (§13): ProfileScorer latency profile. GAE repo. Local.

**Claims state at v5.0 tag:**
- Unconditional: CLAIM-08 through CLAIM-14, CLAIM-17 through CLAIM-21, CLAIM-22 through CLAIM-29
- Conditional: CLAIM-01 through CLAIM-07, CLAIM-15, CLAIM-16, CLAIM-25, CLAIM-30
- Future (blocked): FUTURE-01 through FUTURE-17 (all blocked — see traceability §17)

---

### v5.5 — Deployable + Shadow Mode + EU AI Act

**Theme:** First customer-accessible deployment. Shadow mode on-ramp. Docker + VPS.
EU AI Act compliance evidence generation.

**Experiment gates for v5.5 (must run and pass before v5.5 ships):**

| Experiment | Gate | Version Impact If Fail |
|---|---|---|
| GATE-R | FUTURE-01 (composite accuracy) — **✅ UNBLOCKED March 15 (CORR-1a routing fix complete)** | Can ship v5.5 after GATE-R executes |
| ~~FX-1-PROXY-REAL~~ | ✅ COMPLETE: KL 1.88–2.58. Distribution gap quantified. | Synthetic condition labeling still recommended |
| ~~EXP-S2-REPRO~~ | ✅ COMPLETE: GATE-M formally satisfied. 0.15pp max at production λ. | Tab 5 σ activation can proceed to v6.0 |
| ~~PROD-3~~ | ✅ COMPLETE (March 14): per-category θ: 0.744–0.809 (C=6). Calibration table ready. | Shadow mode calibration table: available |
| ~~PROD-4~~ | ✅ COMPLETE (3 runs, March 14–15): threshold* 0.720–0.870. PROD-4b floors calibrated. | Per-category thresholds: available for v5.5-R1 |
| ARCH-3 | Hook write reliability — **⚠️ blocked by §17.5 (not yet written)** | Block shadow mode if any hook condition fails |
| PERF-1 | ProfileScorer latency SLA (p95 < 1ms) | Investigate and fix if fails; do not ship hosted product with latency issue |

**Experiments running during v5.5 deployment window:**

| Experiment | Purpose | Expected Output |
|---|---|---|
| ARCH-5 | Shadow mode agreement baseline (synthetic) | Calibration reference for first customer report |
| PROD-1 | IKS sensitivity analysis | Validated κ* for IKS formula |
| EXP-OP3 (if TD-033 ships) | Residual tracker early-warning | Safety policy update |
| FX-2 | Analyst bias patterns | Centroid drift bounds under real usage patterns |
| PERF-2 | FactorComputer concurrent load | Production neo4j SLA verification |
| PERF-3 | Factor computation breakdown | Bottleneck identification for v5.5 optimization |
| GE1 | Factor dimensionality scaling | τ recalibration guidance if d grows |
| FX-1-PROXY | Non-centroidal distributions | τ recalibration guidance backup |

**Claims unlocked at v5.5 (if experiment gates pass):**

| Claim | Gate | Condition After |
|---|---|---|
| FUTURE-01 → active | GATE-R passes | "Composite system accuracy: routing% × 97.89%" |
| FUTURE-03 → **PROMOTABLE** | ✅ EXP-S2-REPRO PASSED (March 14) | "σ with Loop 2 at operative λ: 0.15pp max poisoning degradation — GATE-M PASSED" |
| FUTURE-09 → **PROMOTABLE** | ✅ FX-1-PROXY-REAL COMPLETE (March 14) | "Real factor distributions characterized: KL 1.88–2.58 vs centroidal Gaussian" |
| FUTURE-12 → active | PROD-4 + v5.5-R1 ships | "40%+ coverage at ≥85% per-category accuracy" |
| FUTURE-16 → active | PyPI publish | "pip install graph-attention-engine" |
| FUTURE-17 → active | GATE-R completes | "Routing accuracy: [X%]" |
| CLAIM-25 promoted | PROD-4 + v5.5-R1 | Coverage claim strengthened with per-category data |
| CLAIM-30 promoted | PyPI | Condition removed |

**GATE-M Decision: FORMALLY SATISFIED (March 14, 2026).**
GATE-OP ✅ + EXP-S2-REPRO ✅ → **GATE-M PASS.**
- Tab 5 σ activation proceeds to v6.0 full integration
- Poisoning resilience confirmed at production λ=0.5 with Loop 2 running (0.15pp max)
- Realistic distributions show negligible poisoning effect (Arm B)

---

### v6.0 — First Customer POC + Multi-SIEM + Attack Chains

**Theme:** Real customer data. Real SIEM integration. Real analyst feedback.
First deployment that generates "firm-specific institutional knowledge."

**Experiment gates for v6.0:**

| Experiment | Gate | Version Impact If Fail |
|---|---|---|
| EXP-S5a + EXP-S5b | GATE-D-EARLY (data pipeline feasibility) | Tab 5 Phase 2 (F13/F15) deferred |
| EXP-S5 | GATE-D (full pipeline end-to-end) | σ scoring deferred; Tab 5 Panel A display-only |
| EXP-G1 | FUTURE-07 (temporal compounding γ) | γ stays "projected — EXP-G1 pending" |
| PROD-2 | NL template analyst agreement | Analyst-facing centroid interpretation confidence |
| FX-3 | Concept drift characterization | Proactive re-centroid guidance for customers |

**Experiments running during v6.0 deployment window:**

| Experiment | Purpose |
|---|---|
| EXP-S6 | Synthesis briefing quality (Tab 5 Panel A analyst survey) |
| EXP-S7 | Ask-the-Graph 3-condition comparison (Tab 5 Panel B) |
| EXP-OP4 | Direct vs indirect path separation (firewall characterization) |
| GE2 | (C, A) space scaling — relevant for multi-tenant dimension variety |
| GE3 | Kernel robustness under real distributions |
| FX-5 | AgentEvolver 3-tier confidence routing |
| PROD-5 | Category convergence timeline (onboarding calendar) |
| PERF-4 | Centroid tensor memory footprint at scale |
| PERF-5 | Simulation orchestrator throughput |

**Claims unlocked at v6.0:**

| Claim | Gate | Condition After |
|---|---|---|
| FUTURE-04 → active | GATE-D passes | "INTSUM-quality threat briefing validated" |
| FUTURE-05 → active | EXP-S7 passes | "Ask the Graph answers [X/20] queries correctly" |
| FUTURE-07 → active | EXP-G1 passes | "Temporal compounding γ=[X]>1.0 confirmed" |
| FUTURE-08 → partial | Shadow + real decisions | "Deployed in production: [X%] accuracy over [N] decisions" |
| FUTURE-11 → active | FX-1-PROXY-REAL + real baseline | "L2 beats XGBoost on real SOC distributions" |
| FUTURE-13 → active | IKS live + 90-day deployment | "System is measurably more accurate than deployment day" |
| FUTURE-14 → active | Shadow mode + 30-day pilot | "Shadow agreement rate: [X%]" |
| FUTURE-15 → active | S2P DomainConfig + demo | "S2P second domain: same learning trajectory" |

**Intelligence Layer outcome at v6.0 (GATE-M result drives this):**
See synthesis outcome matrix in Part 1 §6 and Part 2 §11.

---

### v6.5 — Flash Tier + NHI Baselines + Additional SIEMs

**Theme:** Production hardening. Streaming detection. New entity types.

**Experiments:** FX-3 (concept drift characterization) informs streaming decision policy.
EXP-OP5 (rank-1 θ*) — if θ* ≥ 45°, rank-1 operators are v6.5 candidate for
sophisticated customers who can specify alert shift directions.

**Claims:** FUTURE-10 ("fourth feedback loop fully operational") requires all three gates
(GATE-M + GATE-D + GATE-V + TD-033). If GATE-V has not run by v6.5, this claim remains blocked.

---

### v7.0 — Multi-Tenant + Level 2 GraphAttentionBridge

**Theme:** Multiple customers sharing infrastructure (isolated tenants). Level 2
cross-domain enrichment via GraphAttentionBridge.

**Level 2 prerequisite experiments (all must run before GraphAttentionBridge ships):**

| Experiment | Gate | Why |
|---|---|---|
| EXP-G1 | FUTURE-07: γ > 1.0 confirmed | Level 2 compounding claim requires γ validated |
| V1B (done ✅) | LayerNorm required in enrichment sweeps | Already validated; must be implemented |
| GE4 | Cold start + TTL calibration | Level 2 cold-start from multi-tenant onboarding |
| FX-4 | S2P domain validation | Level 2 cross-domain requires ≥2 real domains tested |
| FX-6 | Kernel learning (adaptive selection) | Level 2 may encounter distributions not in training |
| ARCH-2 | DomainConfig swappability | Level 2 must work with any DomainConfig |

**Claims potentially unlocked at v7.0:**
- CLAIM-07 condition removal (20×10×20 scale): real multi-domain deployment replaces GT-profile condition
- FUTURE-10: if all three gates (GATE-M, GATE-D, GATE-V) pass by this point
- FUTURE-07: if EXP-G1 runs (colab-pro, scheduled before v7.0 sprint)

---

### v8.0 — Level 3: DiscoveryEngine

**Theme:** Autonomous cross-domain pattern discovery.

**Critical gate:** EXP-G1 must have confirmed γ > 1.0 before Level 3 ships. The entire
"each enrichment sweep is more productive than the last" claim rests on measured γ.
If γ ≤ 1.0 (temporal compounding not super-linear), Level 3 still ships but the
compounding claim is narrowed to spatial only (b=2.11 validated, γ-temporal not).

---

## 16. Experiment → Claims Traceability Matrix

> **Purpose:** For every public-facing claim, this matrix shows exactly which experiment
> established it and which future experiment will promote or constrain it. Use this matrix
> when writing blog posts (never cite a claim without knowing its experiment), investor
> materials (use §1.5 claims; use this matrix to verify their experiment basis), and
> during technical due diligence (the experiment evidence is in cross-graph-experiments
> on GitHub, fully public).
>
> **Two regimes are marked explicitly.** Centroidal synthetic = CS. Realistic 50-seed = R50.
> Never mix them in the same sentence.

### 16.1 Current Claims — Traceability

| Claim ID | Status | Statement (abbreviated) | Established By | Conditions | Promotion Gate |
|---|---|---|---|---|---|
| CLAIM-01 | ⚠️ COND | 97.89% zero-learning accuracy | EXP-C1 | CS — GT profiles — assumes correct routing | GATE-R → FUTURE-01 |
| CLAIM-02 | ⚠️ COND | 98.2% with centroid learning | EXP-B1 | CS — warm-start — noise-free oracle | GATE-R + FX-1-PROXY-REAL |
| CLAIM-03 | ⚠️ COND | 98.1% at 30% oracle noise | EXP-B1 | CS — warm-start | Real-data noise study |
| CLAIM-04 | ⚠️ COND | ECE=0.036 at τ=0.1 | V3B | CS — τ=0.1 required | TD-034 ≥200 real alerts |
| CLAIM-05 | ⚠️ COND | L2 beats XGBoost: 94.78% vs 92.24% | V3A | CS — synthetic held-out | FX-1-PROXY-REAL |
| CLAIM-06 | ⚠️ COND | 94.3% accuracy at decision 1 | V3A | CS — XGBoost needs ≥1,300 samples | FX-1-PROXY-REAL |
| CLAIM-07 | ⚠️ COND | 99.9% at 20×10×20 scale | EXP-E2 | CS — GT profiles required | Real multi-domain deployment |
| CLAIM-08 | ✅ UNCOND | Gating Matrix G falsified (+0.01pp) | EXP-A | — | Permanent |
| CLAIM-09 | ✅ UNCOND | Dot product rejected (61% vs L2 97.89%) | EXP-C1 | — | Permanent |
| CLAIM-10 | ✅ UNCOND | Clipping to [0,1] is required safety constraint | V2 | — | Permanent |
| CLAIM-11 | ✅ UNCOND | τ_modifier permanently rejected (ECE +0.138) | OP series | — | Permanent |
| CLAIM-12 | ✅ UNCOND | Scaling exponent b=2.11 ± 0.03 (R²=0.9999) | V1A | Simulation — not real multi-domain | Permanent (simulation validated) |
| CLAIM-13 | 🔵 INTERNAL | γ≈1.5 estimated temporal compounding | V1A (projection) | Not measured | EXP-G1 |
| CLAIM-14 | ✅ UNCOND | LayerNorm required in enrichment sweeps | V1B | — | Permanent |
| CLAIM-15 | ⚠️ COND | σ at λ=0.5: AUAC δ=+0.0041, p=0.0008 | EXP-OP2/GATE-OP | CS — 100%-correct op — acute phase | GATE-M (EXP-S2-REPRO) |
| CLAIM-16 | ⚠️ COND | Operative window λ∈[0.5, 0.6] | EXP-OP2 | CS — 100%-correct op — Loop 2 running | GATE-M |
| CLAIM-17 | ✅ UNCOND | P-75 operator: 38% never-recover [29%, 48%]; TD-033 required | EXP-OP2 + EXP-OP2-N100 | N=100 confirmed (CI tightened from [15%,59%]) | — (CI sufficient) |
| CLAIM-18 | ✅ UNCOND | Loop 2/Loop 4 firewall: 0.0028 divergence | EXP-S3 | Direct path only; indirect quantified by EXP-OP4 | EXP-OP4 |
| CLAIM-19 | ✅ UNCOND | Profile centroids are compiled domain ontologies | Architecture | Conceptual | Permanent |
| CLAIM-20 | ✅ UNCOND | SOC bridge has 4 components | Architecture | Structural | Permanent |
| CLAIM-21 | ✅ UNCOND | GAE v5.0 complete: 243 tests, Apache 2.0 | v5.0 tag | Level 2/3 designed, not built | v7.0 (Level 2), v8.0 (Level 3) |
| CLAIM-22 | ✅ UNCOND | 71.7% [71.4%, 71.9%] static realistic accuracy | math_synopsis_v7 | R50 — combined realistic — 50 seeds | Permanent (R50 validated) |
| CLAIM-23 | ✅ UNCOND | 78.9% [78.1%, 79.6%] after 1,000 verified decisions | math_synopsis_v7 | R50 — credential_access — 50 seeds | Permanent (R50 validated) |
| CLAIM-24 | ✅ UNCOND | 90.7% [90.1%, 91.2%] auto-approve accuracy at P≥0.90 | math_synopsis_v7 | R50 — global threshold | Per-category PROD-4 strengthens |
| CLAIM-25 | ⚠️ COND | 11.5% ± 0.70% auto-approve coverage | math_synopsis_v7 | R50 — global threshold | PROD-4 + v5.5-R1 → FUTURE-12 |
| CLAIM-26 | ✅ UNCOND | Two regimes disclosed together | Disclosure practice | — | Permanent |
| CLAIM-27 | ✅ UNCOND | 34 experiments public at github.com/ArindamBanerji | v8.3 catalog | 14 bridge + 10 OP/synthesis + 1 infra + 3 extension + 6 calibration (Mar 15) | Grows with each new experiment |
| CLAIM-28 | ✅ UNCOND | Apache 2.0, zero licensing risk | License | — | Permanent |
| CLAIM-29 | ✅ UNCOND | Zero external runtime dependencies (NumPy only) | Architecture | — | Permanent |
| CLAIM-30 | ⚠️ COND | Available as Python library v0.5.0, 243 tests | v5.0 tag | pip install -e . only; not PyPI | v5.5 PyPI → FUTURE-16 |

### 16.2 Future Claims — Traceability

| Claim ID | Statement (abbreviated) | Blocking Experiment(s) | Version | Priority |
|---|---|---|---|---|
| FUTURE-01 | Composite accuracy: routing% × 97.89% | GATE-R | v5.5 | **Highest** |
| FUTURE-02 | ECE calibrated on real SOC data | TD-034 (≥200 real alerts) | v5.5 deploy | High |
| FUTURE-03 | σ + Loop 2 at operative λ: GATE-M PASSED | EXP-S2-REPRO | v5.5 | High |
| FUTURE-04 | INTSUM briefing validated end-to-end | S5a + S5b + S5 (GATE-D) | v6.0 | Medium |
| FUTURE-05 | Ask the Graph accuracy: [X/20] queries | EXP-S7 | v5.5/v6.0 | Medium |
| FUTURE-06 | Synthesis improves real analyst decisions ≥3pp | EXP-S8 (GATE-V) | v6.0+ | Medium |
| FUTURE-07 | γ=[X]>1.0 temporal compounding confirmed | EXP-G1 | v6.0 | Medium |
| FUTURE-08 | Deployed: [X%] accuracy over [N] decisions | Shadow + real SIEM + ≥200 verified | v5.5+ | High (BD driven) |
| FUTURE-09 | Real factor distributions characterized | FX-1-PROXY-REAL | Next | **Highest** |
| FUTURE-10 | Fourth feedback loop fully operational | GATE-M + GATE-D + GATE-V + TD-033 | v6.5 | Long-range |
| FUTURE-11 | L2 beats XGBoost on real SOC data | FX-1-PROXY-REAL + real baseline | v6.0 | Medium |
| FUTURE-12 | 40%+ auto-approve at ≥85% per-category | PROD-4 + v5.5-R1 | v5.5 | High |
| FUTURE-13 | System measurably more accurate than deployment day | IKS live + 90-day deploy | v5.5 | High |
| FUTURE-14 | Shadow agreement rate: [X%] before go-live | Shadow + 30-day pilot | v5.5+ | High (sales) |
| FUTURE-15 | S2P: same learning trajectory as SOC | S2P DomainConfig + PROD-5 | v6.0 | Medium |
| FUTURE-16 | pip install graph-attention-engine works | PyPI publish | v5.5 | High |
| FUTURE-17 | Routing accuracy: [X%] | GATE-R | v5.5 | **Highest** |

### 16.3 Forbidden Claims Traceability

All forbidden claims are listed in claims_registry_v2 Appendix. Each maps to a blocked
future claim. Key links for quick reference:

| Forbidden | Why | Path to Allowed |
|---|---|---|
| "97.89% accuracy" (unqualified) | Routing not measured | GATE-R → FUTURE-01 |
| "Compounds over time" | γ projected, not measured | EXP-G1 → FUTURE-07 |
| "Loop 4 active" | Loop 4 is PROPOSAL | All 3 gates + TD-033 → FUTURE-10 |
| "Poisoning-resistant" (unqualified) | EXP-S2 at cold-start λ only | EXP-S2-REPRO → FUTURE-03 |
| "40% auto-approve" | Global threshold = 11.5% | PROD-4 + v5.5-R1 → FUTURE-12 |
| "Adapts to threat landscape" | σ is PROPOSAL | GATE-M + GATE-D → FUTURE-03/04 |
| "Real-world accuracy of X%" | All measurements synthetic or simulated | Production deploy → FUTURE-08 |

---

## 17. Repository Structure

> This section documents the as-built (v5.0) and planned (v5.5+) structure of all four
> repositories. It is maintained here because experiments must be run in the correct repo
> and must respect the stated dependency direction. Any import that violates the direction
> is flagged by ARCH-1.
>
> **Dependency direction (enforced):** soc-copilot → ci-platform → gae (one-way).
> GAE never imports from soc-copilot. soc-copilot imports from gae via published API only.

---

### 17.1 graph-attention-engine (GAE) — Apache 2.0

**Repo:** `github.com/ArindamBanerji/graph-attention-engine`
**Local:** `C:\Users\baner\...\graph-attention-engine-v50`
**Branch:** `v5.0-dev` | **Version:** `v0.5.0` | **Tests:** 243 | **Runtime dep:** NumPy only

**Published API (gae/__init__.py — everything via explicit `__all__`):**

```
gae/
├── __init__.py            # Public API — all exports + __version__
├── profile_scorer.py      # v5.0 NEW — ProfileScorer, build_profile_scorer (Eq. 4-final)
├── oracle.py              # v5.0 NEW — OracleProvider protocol (TD-032)
├── evaluation.py          # v5.0 NEW — EvaluationScenario, run_evaluation, EvaluationReport
├── judgment.py            # v5.0 NEW — compute_judgment, JudgmentResult
├── ablation.py            # v5.0 NEW — run_ablation, AblationReport
├── engine.py              # v5.0 NEW — GAE public entry point
├── primitives.py          # Tier 1: softmax, scaled_dot_product_attention (Eq. 1)
├── scoring.py             # Tier 2: ScoringResult, score_entity (Eq. 4 — deprecated path)
├── learning.py            # Tier 3: LearningState, weight learning (Eq. 4b/4c)
├── convergence.py         # Convergence monitoring + diagnostics
├── calibration.py         # CalibrationProfile, domain hyperparameters
├── contracts.py           # PropertySpec, EmbeddingContract, SchemaContract
├── events.py              # Frozen event dataclasses
├── factors.py             # FactorComputer Protocol + assemble_factor_vector
├── hooks.py               # v5.0 NEW — DecisionRecord, OutcomeRecord, ProfileSnapshot (Hooks 1/2/3)
└── store.py               # JSON persistence
```

**Planned v5.5+ additions (Tiers 4 and 5, NOT in v5.0):**
```
gae/
├── embeddings.py          # v5.5 — Tier 4: entity embeddings (Eq. 5)
├── attention.py           # v7.0 — Tier 5: cross-graph attention (Eqs. 6, 7, 9)
└── discovery.py           # v8.0 — Tier 5: DiscoveryEngine, measure_marginal_yield (Eq. 8a-8c)
```

**ARCH-1 rule for GAE:** No imports from soc_copilot or ci_platform anywhere in `gae/`.
Verified by ARCH-1 static analysis.

**Key invariants (enforced by tests and V2):**
- τ default = 0.1 everywhere. Never 0.25 (was deprecated at V3B).
- All centroid updates clip to [0.0, 1.0] (V2 required).
- `profile_scorer.py` is THE scoring mechanism. `scoring.py` backward-compat only.
- `f_original` preserved at decision time (Requirement R4).

---

### 17.2 ci-platform — Apache 2.0

**Local:** To be created (Phase 8-9 of v5.0 sprint)
**Dependency direction:** imports from gae; never from soc-copilot

```
ci-platform/
├── platform/
│   ├── domain/
│   │   ├── config.py        # DomainConfig ABC (get_profile_centroids, get_source_connectors)
│   │   ├── registry.py      # Domain registry — maps domain name → DomainConfig
│   │   └── schema.py        # SchemaParser, ContractChecker
│   ├── state/
│   │   └── manager.py       # StateManager — centroid persistence + lifecycle
│   ├── connectors/
│   │   ├── protocol.py      # SourceConnector protocol, SourceNode/SourceEdge dataclasses
│   │   ├── registry.py      # SourceRegistry — connector lifecycle
│   │   ├── ingester.py      # GraphIngester — SourceNode/SourceEdge → Neo4j writes
│   │   └── trust.py         # v5.5 — SourceTrustWeighting (Tier 1/2/3/4 source trust)
│   └── events/
│       └── bus.py           # v5.5 — GraphEventBus (production async event dispatch)
└── tests/
    └── ...
```

**v5.0 scope (Phase 8-9 sprint):**
DomainConfig ABC, StateManager, domain registry, schema parser, ContractChecker,
SourceConnectorProtocol, SourceRegistry, GraphIngester.

**v5.5 additions:**
SourceTrustWeighting, GraphEventBus (replaces SOC's local lightweight bus).

---

### 17.3 gen-ai-roi-demo-v4 (soc-copilot) — Proprietary

**Local:** `C:\Users\baner\...\gen-ai-roi-demo-v4-v50`
**Branch:** `v5.0-dev` | **Version:** `v5.0` | **Tests:** 78

```
soc-copilot/
├── connectors/
│   ├── cisa_kev.py          # v5.0 — CISA KEV SourceConnector (real connector #1)
│   └── nvd.py               # v5.0 — NVD SourceConnector (real connector #2)
├── domain/
│   └── soc_domain_config.py # SOCDomainConfig (extends ci-platform DomainConfig)
│                            # Contains: 5 categories × 5 actions × 6 factors × τ=0.1
│                            # NOTE: refer_to_analyst is 5th action (A=5, not A=4)
├── services/
│   ├── situation_analyzer.py  # SituationAnalyzer (MoE head selector for profile routing)
│   ├── simulation_orchestrator.py  # SimulationOrchestrator — decision loop driver
│   ├── narrative_provider.py  # NarrativeProvider — LLM narrative generation
│   └── shadow_mode.py         # v5.5 — ShadowModeService
├── factor_computers/
│   ├── pattern_history.py
│   ├── threat_intel.py
│   ├── travel_match.py
│   ├── asset_criticality.py
│   ├── time_anomaly.py
│   └── device_trust.py
├── api/
│   └── routes.py             # FastAPI routes including POST /api/soc/query (F14 foundation)
├── tests/
│   ├── arch/                 # ARCH-3, ARCH-5 hook reliability tests
│   └── prod/                 # PROD-1, PROD-3, PROD-4 experiment scripts
└── frontend/
    └── src/
        └── components/
            └── Tab5/         # v5.5 — synthesis briefing + Ask the Graph UI
```

**Critical SOC design constants (must be consistent everywhere):**
- C=6 categories, A=5 actions (refer_to_analyst is 5th), d=6 factors
- τ=0.1 (never 0.25)
- Centroid tensor shape: (6, 5, 6) = 180 values — updated from (5,5,6)=150 (CORR-1a + ontology verification, Mar 15)
- Per-category θ: 0.744–0.809 (PROD-3). Per-category confidence floors: PROD-4b.
- η_neg=0.05 canonical. η_neg=1.0 FORBIDDEN (ECE=0.49).
- EvaluationReport uses `by_category` not `by_technique` (TD-036 fix)
- Language: "product" not "demo" in all docstrings, UI text, comments
- No git from Claude Code. Log-based debugging only.

---

### 17.4 cross-graph-experiments — Public

**Repo:** `github.com/ArindamBanerji/cross-graph-experiments`
**Local:** `C:\Users\baner\...\cross-graph-experiments`
**Completed experiments:** 25 | **Paper figures:** 88 | **Commits:** 9+

```
cross-graph-experiments/
├── CLAUDE.md                    # Project guidelines and rules
├── EXPERIMENTS.md               # Experiment specifications (v5 series + OP series)
├── configs/
│   └── default.yaml             # Central config — no magic numbers in source files
├── src/
│   ├── data/
│   │   ├── alert_generator.py        # Exp 1-4 (Phase 1 core framework)
│   │   ├── category_alert_generator.py  # 5-category, A=5, d=6 (Exp 5+ bridge layer)
│   │   └── generic_alert_generator.py   # Parameterized (C, A, d) for GE/FX experiments
│   ├── models/
│   │   ├── scoring_matrix.py         # Eq. 4 (Phase 1)
│   │   ├── cross_attention.py        # Eqs. 5-8 (Phase 1)
│   │   ├── oracle.py                 # BernoulliOracle + GTAlignedOracle
│   │   ├── profile_scorer.py         # ProfileScorer — THE scorer (EXP-C1, EXP-B1+)
│   │   ├── synthesis.py              # SynthesisBias — σ operator (OP series)
│   │   ├── rule_projector.py         # SYNTH-EXP-0 — σ claim projection
│   │   ├── claim_generator.py        # SYNTH-EXP-0 — structured claim generation
│   │   └── gating.py                 # Gating mechanisms (Exp 7-9, A — deprecated)
│   ├── eval/
│   │   ├── auac.py                   # compute_auac, compute_t_recovery
│   │   └── op_harness.py             # run_with_loop2 — operator evaluation harness
│   └── viz/
│       ├── bridge_common.py          # save_figure, COLORS, VIZ_DEFAULTS, setup_axes
│       └── exp*_charts.py            # Per-experiment chart modules (one per exp)
├── experiments/
│   ├── exp1_scoring_convergence/     # Phase 1
│   ├── exp2_cross_graph_discovery/
│   ├── exp3_multidomain_scaling/
│   ├── exp4_sensitivity/
│   ├── exp5_oracle_fix/              # Phase 2 bridge
│   ├── expA_capacity_ceiling/
│   ├── expB1_profile_scoring/
│   ├── expC1_centroid_oracle/
│   ├── expD1_cross_category_transfer/
│   ├── expD2_factor_interactions/
│   ├── expE1_kernel_generalization/
│   ├── expE2_scale_test/
│   ├── validation/                   # V1A, V1B, V2, V3A, V3B
│   ├── synthesis/                    # EXP-S1 through EXP-S4, SYNTH-EXP-0
│   │   ├── expS1_sigma_accuracy/
│   │   ├── expS2_poisoning/
│   │   ├── expS2_repro/              # NEW — EXP-S2-REPRO (§7, Priority 3)
│   │   ├── expS3_independence/
│   │   ├── expS4_lambda/
│   │   └── synth_exp_0_infra/
│   ├── op_series/                    # EXP-OP1, EXP-OP1-IMPERFECT, EXP-OP1-FINAL
│   │   ├── expOP1_imperfect/         # OP-MARGIN, OP1-FINAL (GATE-OP PASSED)
│   │   ├── expOP2_lifetime/
│   │   ├── expOP2_n100/              # NEW — EXP-OP2-N100 (§7, Priority 4)
│   │   ├── expOP3_residual/          # SPEC READY — blocked on TD-033
│   │   ├── expOP4_firewall/
│   │   ├── expOP5_rank1/
│   │   └── expOP6_generality/
│   ├── ge_series/                    # GE1-GE4 (generic engine)
│   │   ├── expGE1_factor_dim/
│   │   ├── expGE2_ca_scaling/
│   │   ├── expGE3_kernel_robustness/
│   │   └── expGE4_cold_start/
│   ├── fx_series/                    # FX real data + robustness
│   │   ├── expFX1_proxy_real/        # NEW — PRIORITY 2
│   │   ├── expFX1_proxy/             # NEW — PRIORITY 6
│   │   ├── expFX2_noise/
│   │   ├── expFX3_drift/
│   │   └── expFX5_agent_evolver/
│   ├── gate_r/                       # NEW — GATE-R (PRIORITY 1)
│   ├── expG1_gamma/                  # EXP-G1 (spec ready, colab-pro)
│   └── prod/                         # PROD series (PROD-1, PROD-3, PROD-4)
│       ├── prod1_iks_sensitivity/
│       ├── prod3_shadow_baseline/
│       └── prod4_threshold_calibration/
└── paper_figures/                    # 88 PNG + 88 PDF = 176 total publication figures
```

**chart.py universal requirement (applies to every new experiment):**
```python
import matplotlib
matplotlib.use("Agg")  # MUST be first import before any pyplot
import matplotlib.pyplot as plt
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[N]))  # N = depth to repo root
from src.viz.bridge_common import save_figure, COLORS

# Per chart:
fig, ax = plt.subplots(...)
# ... draw ...
save_figure(fig, "expXX_chartname", output_dir="paper_figures")
plt.close(fig)
print("[CHART N] expXX_chartname.png + .pdf saved")
```

---

## 18. Execution Notes and Operating Rules

> These rules apply to every experiment in this catalog and every Claude Code session
> in all four repos. They are not guidelines — they are hard constraints. Violating
> them creates technical debt (often in the form of wrong numbers in the catalog) that
> takes multiple sessions to repair.

---

### 18.1 The Five Non-Negotiable Rules

**Rule 1: Do not use git.** The user handles all git operations. No `git commit`, `git push`,
`git checkout`, or `git merge` from any Claude Code session. Verification is fine: `git status`
or `git log --oneline -5` may be run to understand state, but never write operations.

**Rule 2: Do not start the debugger.** Log-based debugging only. If something fails:
add print statements, re-run, read output. `pdb`, `breakpoint()`, and IDE debugger
invocations are forbidden.

**Rule 3: A=5 throughout.** The SOC copilot has 5 actions: escalate_incident,
close_as_false_positive, request_more_info, apply_automated_response, refer_to_analyst.
refer_to_analyst is action index 4 (0-based). Random baseline is 20% (not 25%).
Every experiment using CategoryAlertGenerator must use A=5, not A=4.

**Rule 4: τ=0.1 always.** The V3B-validated default. Never τ=0.25 in any new experiment.
All calibration sweeps must include τ=0.1 as the reference point, not as a candidate.

**Rule 5: ProfileScorer is THE scorer.** ScoringMatrix is deprecated (TD-029). All new
experiments import from `src.models.profile_scorer`, not `src.models.scoring_matrix`.
ARCH-1 verifies this at the repo level.

---

### 18.2 Accuracy Regime Rules

**Never mix centroidal synthetic (CS) and realistic 50-seed (R50) numbers in the same
sentence or comparison.** This is the single most common error in technical communication.

| Regime | Numbers | Condition | Used For |
|---|---|---|---|
| CS — Centroidal Synthetic | 97.89%, 98.2%, 94.78% | GT profiles, GT-aligned oracle, noise-free | Mechanism validation, technical presentations |
| R50 — Realistic 50-seed | 71.7%, 78.9%, 90.7% | Realistic distributions, 50 seeds, oracle noise | Product claims, CISO conversations |

**When an experiment produces a new number:** Immediately identify which regime it belongs
to. Label it in the experiment results summary. Do not strip the condition when adding to
the catalog.

**When re-running an existing experiment at new conditions:** The new result is a new
experiment. Do not overwrite the original. Create a new experiment ID (e.g., EXP-S2-REPRO,
not EXP-S2 updated).

---

### 18.3 Gate Definitions

| Gate | Experiment(s) | Pass Condition | What Opens |
|---|---|---|---|
| GATE-G | V3A | L2 centroid accuracy > 90% on held-out synthetic | ✅ PASSED — architecture settled |
| GATE-OP | EXP-OP1-FINAL | B vs A AUAC δ > 0 (p < Bonferroni), C vs A δ < 0 | ✅ PASSED (p=0.0008, λ=0.5) |
| GATE-M | EXP-S2-REPRO + GATE-OP | Arm A: T_recovery(p90) < 100 decisions at 20% poison; never-recover ≤ 5% at λ=0.5, Loop 2 running. Arm B (realistic-AUAC): degradation measured and domain-expert-reviewed (open gate — no pre-specified number; must complete before formal GATE-M). Both arms required. | Tab 5 σ activation (v6.0) |
| GATE-D | EXP-S5a + S5b + S5 | ≥5 claims from real sources, pipeline latency < 200ms P95 | F13/F15 ContextConnectors + SynthesisNode |
| GATE-D-EARLY | EXP-S5a + EXP-S5b only | S5a: ≥3 σ cells, latency < 60s. S5b: LLM F1 ≥ 0.70 | Tab 5 Panel A display builds |
| GATE-V | EXP-S8 | Treatment improvement ≥ 3pp, overall ≥ 2pp, irrelevant degradation ≤ 1pp | σ active in scoring |
| GATE-R | DecisionRecord Hook + routing eval | Routing accuracy measured with 95% CI | FUTURE-01, FUTURE-17 |
| GATE-θ* | EXP-OP5 | θ* ≥ 45° (rank-1 practically useful) | v6.0 rank-1 operators |
| GATE-DISC | DISC-1 ✅ + composite gate implementation | DISC-1 passed (70.4% coverage@85%prec); composite discriminant deployed | Phase 5 deployment |

**GATE-R Status (March 15, 2026): ✅ UNBLOCKED**
- CORR-1a routing fix: 68% misroute eliminated
- Alert type → category mapping: 20 entries, resolve_alert_category() implemented
- SOC tests: 78 → 111 (routing coverage expanded)
- GATE-R is now executable (v5.5-R6 alert mapping complete)

**Gate failure policy:**
- Failed gates do not get re-run with weaker criteria. The gate is either re-designed
  (with explicit rationale documenting why the original criteria was wrong) or the
  feature does not ship.
- GATE-V failure: σ goes to advisory-only. No automatic fallback pivots. Human review
  determines root cause before any re-design decision.
- GATE-M failure: Tab 5 ships display-only. σ remains at λ=0 (no scoring impact).

---

### 18.4 Statistical Standards

All experiments use these standards unless the experiment spec explicitly overrides:

| Standard | Value | Rationale |
|---|---|---|
| Default seed count | 20 (local), 50 (product claims) | 20 for mechanism validation; 50 for claims |
| Significance threshold | p < 0.05 (Bonferroni if k > 1 comparison) | Bonferroni k=6 → threshold p < 0.0083 |
| Confidence intervals | 95% Wilson interval for proportions; 95% t-interval for means | Wilson handles small proportions correctly |
| Pre/post RNG isolation | post_gen: seed + 10,000 | Prevents pre/post correlation |
| Never-recover sentinel | N_post + 1 (decision count) | Allows computing means across seeds including never-recover |
| T_recovery window | Rolling 50-decision mean within 1pp of pre-shift | Consistent with EXP-OP2 definition |

**Critical: when reporting a number from an experiment, always include:**
1. The experiment ID (e.g., EXP-OP2)
2. The condition (e.g., "condition B, λ=0.5, 20 seeds")
3. The metric (e.g., "AUAC delta")
4. The value with uncertainty (e.g., "+0.0041 ± 0.0048")
5. The p-value if a hypothesis test was run (e.g., "p=0.0008")

---

### 18.5 Compute Venue Guide

| Tag | Meaning | Examples | Notes |
|---|---|---|---|
| `local` | Runs on development machine, Windows 11, Python 3.11 | All GE, FX-PROXY, GATE-R, OP3-OP4, ARCH, PERF, PROD | pip install in venv: python_expts_venv |
| `colab-pro` | Requires GPU or large RAM (embedding operations) | EXP-G1 (Level 2 mock), GE4 at d=50 with Mahalanobis | Schedule separately; colab-pro session |
| `partner-required` | Cannot run without external SOC data or analysts | FX-1 (real alert corpus), PROD-2 (analyst study), EXP-S8 | BD pipeline dependency |
| `soc-copilot-v60` | Requires v6.0 soc-copilot running with live SIEM | EXP-S5, S6, S7, S8 | Cannot run before v6.0 ships |

**Environment details (local):**
- OS: Windows 11, PowerShell
- Python: 3.11, venv: `python_expts_venv`
- GAE dir: `C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\graph-attention-engine-v50`
- SOC dir: `C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50`
- Experiments dir: `C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\cross-graph-experiments`
- Neo4j: `localhost:7687` (bolt), `localhost:7474` (browser)
- Backend: `localhost:8000` | Frontend: `localhost:5174` (Vite) or `localhost:3000`

---

### 18.6 Prompt Readiness Status Summary

Complete tally across all three parts of this catalog:

| Series | Total | ✅ Complete | ✅ Full Prompt | 🔧 Spec Ready | 📐 Partial | 🔲 Design Pending |
|---|---|---|---|---|---|---|
| Priority Queue | 6 | **3 (FX-1-PROXY-REAL, S2-REPRO, OP2-N100)** | 1 (GATE-R ⚠️) + FX-1-PROXY ✅ | 1 (EXP-G1) | 0 | 0 |
| OP series (OP3-OP6) | 4 | 0 | 2 (OP3, OP4) | 2 (OP5, OP6) | 0 |
| GE series (GE1-GE4) | 4 | 4 | 0 | 0 | 0 |
| FX series (FX-1 through FX-8) | 9 | 2 (FX-1-PROXY, FX-1-PROXY-REAL) | 4 (FX-2, FX-3, FX-5, FX-8) | 2 (FX-4, FX-6) | 1 (FX-7) |
| Synthesis pipeline (S5a-S8) | 6 | 0 | 2 (S5a, S5b) | 2 (S6, S7) | 2 (S5, S8) |
| ARCH series | 5 | 2 (ARCH-1, ARCH-4) | 2 (ARCH-2, ARCH-3 ⚠️§17.5) | 1 (ARCH-5) | 0 |
| PERF series | 5 | 1 (PERF-1) | 4 (PERF-2, 3, 4, 5) | 0 | 0 |
| PROD series | 5 | 2 (PROD-3, PROD-4) | 2 (PROD-1 ✅, PROD-5) | 1 (PROD-2) | 0 |
| **Total** | **44** | **16** | **17** | **8** | **3** |

> **Changes from v8.0 table:**
> - ARCH-3 moved ✅ Full Prompt → 🔧 Spec Ready: blocked by `soc_copilot_design_v5_4 §17.5`
>   (rollback execution semantics not yet written). Failure test protocol cannot be finalized.
>   Sequential and concurrent test prompts are complete; failure test protocol is blocked.
> - EXP-S6 and EXP-S7 moved 🔲 Design Pending → 📐 Partial: judge rubrics written in
>   Part 2 §11. Study protocol structure is defined; full prompts require soc-copilot v6.0.
> - GATE-R ⚠️: prompt is ✅ Full Prompt but execution is blocked until v5.5-R6 ships.
>   Counted as Full Prompt because the prompt itself is complete and correct.
> - Totals: 16 full prompts, 17 spec-ready, 8 partial, 3 design-pending (was 17/16/6/5).

Note: FX-1-PROXY-REAL, EXP-S2-REPRO, and EXP-OP2-N100 are now ✅ COMPLETE (March 14, 2026).
Results in Part 2 §7. Prompts retained for reproducibility.

**Immediately executable (no infrastructure prerequisites):**
GATE-R ⚠️ (prompt ready, execution blocked until v5.5-R6), FX-1-PROXY, ARCH-1, ARCH-4,
PERF-1, PROD-1, PROD-3, PROD-4, GE1, GE2, GE3, GE4.

**Next-executable after v5.5 features ship:**
ARCH-5 (shadow mode), PROD-5 (SEED-2).

**Blocked by specific prerequisites:**
- ARCH-3: blocked by §17.5 (rollback execution semantics not yet written)
- GATE-R: blocked by v5.5-R6 (complete alert_type → category mapping, TD-037)

**Requires TD-033 (checkpoint infrastructure):** EXP-OP3.

**Requires colab-pro:** EXP-G1.

**Requires partner/deployment:** FX-1 (real SOC), PROD-2 (analyst study), S5–S8.

---

### 18.7 Deferred Document Updates

Seven design documents are intentionally NOT updated with intelligence layer content
until experiments validate. This is the same experiment-first discipline applied to the
bridge layer. The list is preserved here as a reminder:

| Document | What's Deferred | Gate Trigger |
|---|---|---|
| gae_design_v9 | ProfileScorer σ parameter, synthesis-aware score() | GATE-M passes |
| soc_copilot_design_v5_4 | Tab 5 implementation details, ContextConnectors spec | GATE-D-EARLY + GATE-M |
| **soc_copilot_design_v5_4 §17.5** | **Rollback execution semantics** (trigger conditions, rollback-and-resume mode, Hook 2/3 interaction) — **NOT YET WRITTEN. Blocks ARCH-3.** | Write before ARCH-3 executes |
| compounding_intelligence_v6 | Loop 4 as validated loop (not proposal) | GATE-V passes |
| architecture_philosophy_v1 | Loop 4 in the five-layer model | GATE-V passes |
| platform_roadmap_v13 | σ activation as shipped feature | GATE-M decision |
| cross_graph_attention_v3 | Eq. 4-synthesis as validated equation | GATE-M + GATE-D |
| claims_registry_v2 | FUTURE-03 → CLAIM | EXP-S2-REPRO passes |

**Rule:** If an experiment passes its gate, the corresponding document update is the
FIRST item in the next session's task list before any new code is written. Documents
become stale faster than code — and stale documents create wrong experiments.

---

## 19. Document Changelog and Next Steps

### 19.1 Changes from bridge_experiments_catalog_v7_2 to experiments_catalog_v8

**Structural:**
- Renamed from "Bridge Experiments Catalog" to "Experiments Catalog" (bridge metaphor retired)
- Split into 3 parts (v7_2 was a single 1,637-line document; v8 is ~5,000 lines across 3 parts)
- Dashboard expanded: 4 series (Math/GAE/Synthesis, ARCH, PERF, PROD) — 15 new experiments
- Insight Register (§2, Part 1): 7 consolidated findings for technical buyers
- Forward-looking view by version (§15, this part): first time experiments are mapped to version gates

**Accuracy corrections:**
- A=5 throughout (random baseline 20%, not 25%) — applied to all accuracy waterfall charts and experiment setups
- EXP-OP2-N100 added (N=20 is insufficient for 35% never-recover CI)
- EXP-S2-REPRO added (GATE-OP ≠ GATE-M; re-run required at operative λ=0.5)
- GATE-R formalized as Priority 1 (composite accuracy is the most externally credible number)

**New content:**
- Priority Queue (§7, Part 2): 6 experiments ordered by execution priority with rationale
- ARCH series (§12, Part 2): 5 experiments verifying architectural properties, not math
- PERF series (§13, Part 2): 5 experiments with SLA targets and baselines
- PROD series (§14, this part): 5 experiments verifying customer-facing product quality
- Claims traceability matrix (§16): every claim mapped to its experiment and promotion gate
- Repository structure (§17): as-built v5.0 layout + planned v5.5/v7.0/v8.0 additions
- Execution notes (§18): rules, statistical standards, gate definitions, compute venues

**Experiment counts:**
- v7_2: 25 completed + 18 planned (bridge/synthesis/FX) = 43 cataloged
- v8.0: 25 completed + 44 planned (all series) = 69 cataloged
- v8.2: 28 completed + 41 planned = 69 cataloged (3 moved from planned to completed)
- v8.3: 34 completed + 41 planned = 75 cataloged (6 new: PROD-3, PROD-4×3, SHIFT-1, SHIFT-2, DISC-1; DISC-2 added as planned)

### 19.2 Pending Document Updates (Next Session)

These documents are known to need updating but were not in scope for this session:

| Document | Update Needed | Status |
|---|---|---|
| claims_registry_v3 | §4 Open Issues + §5 Product Direction from issue_calibration_table | 🔲 Pending — next claims review session |
| platform_roadmap_v14 | Incorporate product_strategy_v2 findings + v5.5 experiment additions | 🔲 Pending — after v5.5 sprint scoped |
| project_status_and_plan v3 | v5.5 sprint ordered by demo conversion impact | 🔲 Pending — after v5.0 tagged |
| next_session_startup_guide | Update to reflect v8.1 catalog complete, experiment execution order, GATE-R execution block | 🔲 Pending — this session or next |
| soc_copilot_design_v5_4 §17.5 | Write rollback execution semantics (trigger conditions, rollback-and-resume mode, Hook 2/3 interaction) | 🔲 Pending — blocks ARCH-3 |
| math_synopsis_v7 | ~~Claims evolution roadmap section~~ | ✅ Complete (done in prior session) |
| experiments_catalog_v8 (all 3 parts) | v8.0 → v8.1 updates (companion refs, judge rubrics, GATE-R constraint, EXP-S2-REPRO Arm B, ARCH-3 §17.5 block) | ✅ Complete (v8.1 session) |
| experiments_catalog_v8 (all 3 parts) | v8.1 → v8.2 updates (3 experiments complete, GATE-M satisfied, priority queue, claims, prompt readiness) | ✅ Complete (v8.2 session, Mar 14) |
| experiments_catalog_v8 (all 3 parts) | v8.2 → v8.3 updates (PROD-3 ✅, PROD-4 ✅ 3 runs, SHIFT-1 ✅, SHIFT-2 ✅, DISC-1 ✅, CORR-1a ✅, tensor 6×5×6, GATE-R unblocked) | ✅ Complete (v8.3 session, Mar 15) |
| claims_registry_v2 → v3 | FUTURE-03 promotion (S2-REPRO passed), FUTURE-09 promotion (FX1 complete), CLAIM-17 CI update (38% [29%,48%]) | 🔲 Pending — next session |
| math_synopsis_v7 | σ_max note: FX1 complete, distributions characterized, σ_max derivation still pending | 🔲 Pending — minor |
| graphics_inventory.md | Add eq_synth_musigma.png + 10 new experiment chart PNGs | 🔲 Pending — minor |

### 19.3 Execution Order for Next Session

**Dependency graph (v8.3 state):**
- SHIFT-2 depends on SHIFT-1 ✅ and BUG-FIX ✅ (update() fix applied)
- DISC-1 depends on SHIFT-1 ✅ (frozen baseline established)
- DISC-2 depends on DISC-1 ✅ and SHIFT-2 ✅
- Phase 5 deployment depends on DISC-1 ✅ and GATE-R ✅ (now unblocked)
- GATE-R now unblocked (CORR-1a routing fix complete, v5.5-R6 alert mapping complete)

Recommended first actions in priority order:

1. ~~**Stage GATE-R**~~ — ✅ UNBLOCKED (March 15, 2026). CORR-1a routing fix complete. 20-entry alert_type → category mapping. **Execute GATE-R now.**
   → `cross-graph-experiments/experiments/gate_r/` — prompt in Part 2 §7
2. ~~**Run FX-1-PROXY-REAL**~~ — ✅ COMPLETE (March 14, 2026). KL 1.88–2.58. FUTURE-09 promotable.
3. ~~**Run EXP-S2-REPRO**~~ — ✅ COMPLETE (March 14, 2026). 0.15pp max. GATE-M satisfied.
4. ~~**Run EXP-OP2-N100**~~ — ✅ COMPLETE (March 14, 2026). 38% [29%, 48%]. 900 runs in 0.4 min.
5. ~~**Run PROD-3**~~ — ✅ COMPLETE (March 14, 2026). Per-category θ: 0.744–0.809 (C=6).
6. ~~**Run PROD-4**~~ — ✅ COMPLETE (3 runs, March 14–15, 2026). threshold* 0.720–0.870.
7. **Write soc_copilot_design_v5_4 §17.5** (rollback execution semantics) — unblocks ARCH-3 and the shadow mode safety chain
8. **Run DISC-2** (frozen vs learned through composite gate, Phase 5) — depends on DISC-1 ✅ + SHIFT-2 ✅
9. **Run EXP-G1** (γ validation, colab-pro) — next in priority queue
10. **Update claims_registry** — promote FUTURE-03, FUTURE-09; update CLAIM-17 CI; add SHIFT/DISC findings
11. **Deploy Phase 5** — GATE-R unblocked + DISC-1 ✅ → composite discriminant gate deployable
12. **Continue v5.0 sprint** if any of Phases 1-9 remain incomplete

---

*Experiments Catalog v8.3 — Complete (3 parts) · March 15, 2026*
*34 experiments complete. 41 planned. 75 total cataloged across Math/GAE/Synthesis, ARCH, PERF, PROD, Calibration series.*
*GATE-M formally satisfied (EXP-S2-REPRO complete March 14). GATE-R unblocked (CORR-1a routing fix March 15).*
*NR rate confirmed: 38% [29%, 48%] at N=100 (EXP-OP2-N100). Distribution gap quantified (FX-1-PROXY-REAL: KL 1.88–2.58).*
*Calibration science: SHIFT-1 (frozen baseline 80.4%), SHIFT-2 (update() bug fixed, +2.7% at δ=0.10), DISC-1 (70.4% coverage@85%prec).*
*Tensor: (6,5,6) = 180 values. Per-category θ: 0.744–0.809 (PROD-3). η_neg=0.05 canonical (η_neg=1.0 FORBIDDEN: ECE=0.49).*
*Priority Queue: GATE-R (✅ unblocked March 15 — execute now) → DISC-2 (Phase 5) → EXP-G1 → FX-1-PROXY.*
*ARCH-3 blocked by §17.5 (not yet written). Write §17.5 before shadow mode safety chain can close.*
*Companions: soc_copilot_design_v5_4, math_synopsis_v8, claims_registry_v3_1, gae_design_v9, production_paper_v5.*
*"Experiments decide what ships. Documents record what experiments proved. The graph remembers everything."*
