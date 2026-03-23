# v5.5 Sprint — Blocker Experiment Prompts
## Steps 1, 2, 3, 5 (Pre-Sprint Experiments)

**Date:** March 13, 2026
**Status:** All four prompts exist in experiments_catalog_v8. This document extracts
them into execution-ready form with current-state corrections and the σ_max
derivation step added to FX-1-PROXY-REAL (which was in the design intent but
missing from the catalog prompt).

**Execution order within a single session:**
Steps 1, 2, 3, 5 can all run in parallel — none blocks the other.
Step 1 (PROD-3) produces a θ threshold that updates §23.4 after it runs.
Step 3 (FX-1-PROXY-REAL) produces σ_max that updates soc_copilot_design §9 after it runs.
Step 5 (EXP-S2-REPRO Arm 0) is a replication check — if it fails, STOP and diagnose.

**Repo for all four:** cross-graph-experiments
**Environment:** Windows 11, PowerShell, python_expts_venv activated
**Global rules:** Do NOT use git. Do NOT start the debugger. Log-based debugging only.

---

## Step 1: PROD-3 — Shadow Mode Agreement Rate Baseline

**Source:** experiments_catalog_v8_part3 §14 ✅ PROMPT READY (reproduced verbatim + corrections)
**Location:** `experiments/prod/prod3_shadow_baseline/`
**Compute:** Local, ~30 min
**Corrections from catalog:** None — prompt is accurate as written
**What it unblocks:** §23.4 per-category θ similarity threshold; Sprint Phase 4 (shadow mode) calibration table

---

```
Repo: cross-graph-experiments
Location: experiments/prod/prod3_shadow_baseline/
Design spec: soc_copilot_design_v5_4 §23.4 (similar past cases similarity threshold)

CONSTRAINTS:
- Do NOT use git. Do NOT start the debugger. Log-based debugging only.
- tau = 0.1 always. Never use 0.25.
- A=5 (C=5, A=5, d=6) — refer_to_analyst is the 5th action.
- All results include 95% CI. Never report a point estimate alone.
- Regime label: ALL output carries "centroidal synthetic" regime label.

READ FIRST:
  src/models/profile_scorer.py  → verify ProfileScorer constructor signature
  src/models/oracle.py          → verify GTAlignedOracle class name and constructor
  src/data/category_alert_generator.py  → verify CategoryAlertGenerator API
  src/viz/bridge_common.py      → verify save_figure signature and COLORS dict
  paper_figures/                → note any existing PROD-3 files to avoid overwrite

FILES TO CREATE:
  1. experiments/prod/prod3_shadow_baseline/run.py
  2. experiments/prod/prod3_shadow_baseline/charts.py

run.py:
  from src.models.profile_scorer import ProfileScorer, build_profile_scorer
  from src.models.oracle import GTAlignedOracle
  from src.data.category_alert_generator import CategoryAlertGenerator
  import numpy as np, json
  from pathlib import Path

  PARAMETERS (config dict at top — do not scatter):
    N_seeds = 50
    N_warmup = 200        # warm-start (centroids learn, not in shadow)
    N_shadow = 200        # shadow period (record agreement, no learning)
    C, A, d = 5, 5, 6
    tau = 0.1
    noise_rate = 0.10     # oracle noise (realistic)
    confidence_thresholds = [0.5, 0.6, 0.7, 0.8, 0.9]
    CATEGORIES = ["credential_access", "lateral_movement", "insider_threat",
                  "data_exfiltration", "cloud_infrastructure"]
    RANDOM_SEED_BASE = 42

  Per seed:
    1. Build CategoryAlertGenerator(seed=RANDOM_SEED_BASE + seed_idx, C=C, A=A, d=d)
    2. Build ProfileScorer from DomainConfig warm-start centroids (categories=CATEGORIES)
    3. Build GTAlignedOracle(noise_rate=noise_rate, seed=RANDOM_SEED_BASE + seed_idx)

    Warmup phase (N_warmup decisions):
      score_result = scorer.score(alert.factors, alert.category_idx)
      oracle_action = oracle.get_action(alert)
      scorer.update(f=alert.factors, c=alert.category_idx, a=oracle_action, correct=True)
      # No shadow recording during warmup

    Shadow phase (N_shadow decisions):
      score_result = scorer.score(alert.factors, alert.category_idx)
      system_rec = score_result.action
      oracle_action = oracle.get_action(alert)
      confidence = score_result.confidence
      agreed = int(system_rec == oracle_action)
      # Record: (seed, decision_idx, category_idx, system_rec, oracle_action,
      #          confidence, agreed)
      # No centroid update during shadow phase — observation only

  Per seed compute:
    overall_agreement = mean(agreed) over N_shadow
    per_category_agreement = {CATEGORIES[c]: mean(agreed where category==c) for c in range(C)}
    high_conf_agreement = {t: mean(agreed where confidence>=t) for t in thresholds}
    high_conf_coverage = {t: mean(confidence>=t) for t in thresholds}
    # Also: compute cosine similarity distribution for §23.4 θ threshold:
    factor_vectors = [record.factor_vector for record in shadow_records]
    per_category_cosine_sims = {}
    for c in range(C):
      cat_vectors = [v for (v, cat) in zip(factor_vectors, categories) if cat==c]
      if len(cat_vectors) >= 2:
        sims = [cosine_sim(cat_vectors[i], cat_vectors[j])
                for i in range(len(cat_vectors)) for j in range(i+1, len(cat_vectors))]
        per_category_cosine_sims[CATEGORIES[c]] = sims

  Aggregate across 50 seeds:
    overall: mean, std, 95% CI (Wilson or bootstrap with N=1000)
    per_category: mean ± std per category
    high_conf: mean agreement ± std per threshold, mean coverage ± std per threshold
    cosine_sims: p25 of distribution per category → this IS the θ threshold for §23.4

  PRINT:
    "=== SHADOW MODE CALIBRATION TABLE (v5.5) ==="
    "Regime: centroidal synthetic, 50 seeds, noise_rate=0.10"
    "Overall agreement rate: {mean:.1%} ± {std:.1%} [{ci_low:.1%}, {ci_high:.1%}]"
    "Per-category:"
    for each category: "  {name}: {mean:.1%} [{ci_low:.1%}, {ci_high:.1%}]"
    "At P≥0.90: agreement={X:.1%} ± {Y:.1%}, coverage={Z:.1%} ± {W:.1%}"
    ""
    "=== §23.4 SIMILARITY THRESHOLD (θ) RECOMMENDATIONS ==="
    "Method: p25 of pairwise cosine similarity distribution within category"
    for each category: "  {name}: θ = {p25:.3f} (based on N={count} pairs)"
    ""
    "COPY THESE θ VALUES INTO soc_copilot_design_v5_4 §23.4.1"
    "They replace the placeholder θ=0.85 currently in the design document."

  WRITE to file:
    prod3_calibration_table.json:
    {
      "regime": "centroidal_synthetic",
      "n_seeds": 50,
      "overall": {"mean": X, "std": Y, "ci_low": Z, "ci_high": W},
      "per_category": {name: {"mean": X, "ci_low": Y, "ci_high": Z}},
      "high_conf": {threshold: {"agreement_mean": X, "coverage_mean": Y}},
      "theta_recommendations": {name: {"p25": X, "n_pairs": N}}
    }

  Call charts.py after printing.

charts.py:
  import matplotlib
  matplotlib.use("Agg")
  import sys
  from pathlib import Path
  sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
  from src.viz.bridge_common import save_figure, COLORS

  Chart 1 (prod3_agreement_rate_distribution):
    Histogram of per-seed overall agreement rates (50 values). 10 bins.
    Vertical dashed line at mean. Annotate: "mean={X:.1%}, 95% CI [{Y:.1%}, {Z:.1%}]"
    X-axis: "Agreement rate (centroidal synthetic)". Y-axis: "Seeds (out of 50)".
    save_figure(fig, "prod3_agreement_rate_distribution", output_dir="paper_figures")
    plt.close(); print("[CHART 1] prod3_agreement_rate_distribution saved")

  Chart 2 (prod3_per_category_agreement):
    Horizontal bar chart, 5 categories, highest-to-lowest agreement order.
    Error bars: 95% CI. Vertical dashed line at overall mean.
    Category colors from COLORS dict.
    X-axis: "Agreement rate". Title: "Per-category shadow agreement (centroidal synthetic)"
    save_figure; plt.close; print("[CHART 2]...")

  Chart 3 (prod3_high_confidence_agreement):
    Dual-axis line chart. X: confidence threshold (0.5 → 0.9).
    Left Y: agreement rate mean (blue) ± std (blue fill).
    Right Y: coverage mean (green dashed) ± std (green fill).
    Annotate at P≥0.9: "agreement={X:.1%}, coverage={Y:.1%}"
    Title: "Shadow agreement vs confidence threshold (calibration, centroidal synthetic)"
    save_figure; plt.close; print("[CHART 3]...")

TESTS before declaring done:
  - 50 seeds × 200 shadow decisions = 10,000 records (assert len == 10,000)
  - prod3_calibration_table.json exists and is valid JSON
  - All 5 categories appear in per_category with non-NaN values
  - theta_recommendations contains all 5 categories
  - All 3 chart .png and .pdf files exist in paper_figures/
  - No NaN in overall CI or per-category means

ACCEPTANCE CRITERION:
  prod3_calibration_table.json exists with theta_recommendations for all 5 categories,
  and the calibration table prints to stdout without errors.

AFTER THIS RUNS:
  Update soc_copilot_design_v5_4_part1 §23.4.1 with the per-category θ values.
  Replace "θ=0.85 placeholder" with the actual measured values per category.
```

---

## Step 2: PROD-4 — Per-Category Auto-Approve Threshold Calibration

**Source:** experiments_catalog_v8_part3 §14 ✅ PROMPT READY (reproduced verbatim + one correction)
**Location:** `experiments/prod/prod4_threshold_calibration/`
**Compute:** Local, ~2 hours (50 seeds × 1,000 decisions × 50 threshold sweep values)
**Corrections from catalog:** Category list had "travel_anomaly" — canonical name is "insider_threat"
**What it unblocks:** Sprint Phase 5 (auto-approve) per-category threshold table; refer_to_analyst confidence floor

---

```
Repo: cross-graph-experiments
Location: experiments/prod/prod4_threshold_calibration/
Design spec: soc_copilot_design_v5_4 §15 (auto-approve policy), product_strategy_v2 §v5.5-R1

CONSTRAINTS:
- Do NOT use git. Do NOT start the debugger. Log-based debugging only.
- tau = 0.1 always. Never use 0.25.
- A=5 (C=5, A=5, d=6).
- Gate threshold (accuracy ≥ 0.85) is pre-declared. Do NOT change it after seeing results.
- Regime label: ALL output carries "centroidal synthetic" regime label.

READ FIRST:
  src/models/profile_scorer.py  → verify constructor and score() signature
  src/models/oracle.py          → verify GTAlignedOracle
  src/data/category_alert_generator.py  → verify CategoryAlertGenerator
  src/viz/bridge_common.py      → verify save_figure + COLORS
  paper_figures/                → note any existing PROD-4 files

FILES TO CREATE:
  1. experiments/prod/prod4_threshold_calibration/run.py
  2. experiments/prod/prod4_threshold_calibration/charts.py

run.py:
  from src.models.profile_scorer import ProfileScorer, build_profile_scorer
  from src.models.oracle import GTAlignedOracle
  from src.data.category_alert_generator import CategoryAlertGenerator
  import numpy as np, json
  from pathlib import Path

  PARAMETERS:
    N_seeds = 50
    N_decisions = 1000
    N_warmup = 200        # pre-decisions before threshold sweep window
    C, A, d = 5, 5, 6
    tau = 0.1
    noise_rate = 0.10
    threshold_sweep = np.arange(0.50, 1.00, 0.01)   # 50 values
    CATEGORIES = ["credential_access", "lateral_movement", "insider_threat",
                  "data_exfiltration", "cloud_infrastructure"]
    # NOTE: "insider_threat" is correct — NOT "travel_anomaly" (catalog typo)
    RANDOM_SEED_BASE = 42
    ACCURACY_GATE = 0.85       # pre-declared, do not change

  Per seed:
    1. Build ProfileScorer with warm-start centroids (categories=CATEGORIES, actions=5)
    2. Build GTAlignedOracle(noise_rate=noise_rate, seed=RANDOM_SEED_BASE + seed)
    3. Build CategoryAlertGenerator(seed=RANDOM_SEED_BASE + seed, C=C, A=A, d=d)

    Warmup (N_warmup decisions, not recorded):
      score, get oracle action, update centroids — discard results

    Decision window (N_decisions decisions, record all):
      score_result = scorer.score(alert.factors, alert.category_idx)
      oracle_action = oracle.get_action(alert)
      scorer.update(f=alert.factors, c=alert.category_idx, a=oracle_action, correct=True)
      is_correct = (score_result.action == oracle_action)
      # Record: (seed, category_idx, confidence, is_correct)

  Per seed × category × threshold:
    decisions_above = [(conf, correct) where category==c and confidence >= threshold]
    accuracy_at_threshold = mean(correct for d in decisions_above) if decisions_above else NaN
    coverage_at_threshold = len(decisions_above) / N_decisions

  Aggregate across 50 seeds per category × threshold:
    accuracy_mean[c, t] = mean across seeds (ignoring NaN seeds)
    accuracy_ci_low, accuracy_ci_high = 95% CI (bootstrap N=1000, ignoring NaN seeds)
    coverage_mean[c, t] = mean across seeds

  Per category — find threshold*:
    threshold_star[c] = minimum threshold t where accuracy_mean[c, t] >= ACCURACY_GATE
    If no threshold achieves this: threshold_star[c] = NaN → flag as below-gate category

  For refer_to_analyst confidence floor:
    Compute: at what threshold does coverage drop below 10% for each category?
    This is the natural lower bound for the refer_to_analyst floor.
    Report: "refer_to_analyst confidence floor per category:
      {name}: recommend {max(0.70, threshold_where_coverage_drops_below_10%):.2f}"

  PRINT:
    "=== PROD-4 THRESHOLD CALIBRATION (centroidal synthetic, 50 seeds) ==="
    Table: Category | threshold* | accuracy_at_threshold* | coverage_at_threshold*
    Gate verdict: "N/5 categories achieve threshold* <= 0.75"
    ""
    "=== refer_to_analyst CONFIDENCE FLOOR RECOMMENDATIONS ==="
    For each category: "{name}: {floor:.2f}"
    ""
    "COPY threshold* VALUES INTO project_status_and_plan_v3_part2 Phase 5 (AUTO-*) sprint prompt"
    "REPLACE the design-estimate thresholds labeled 'pending PROD-4'"

  WRITE:
    prod4_threshold_table.json:
    {
      "regime": "centroidal_synthetic",
      "n_seeds": 50, "n_decisions": 1000, "n_warmup": 200,
      "accuracy_gate": 0.85,
      "categories": {
        "credential_access": {"threshold_star": X, "accuracy": Y, "coverage": Z},
        ...
      },
      "gate_verdict": "N/5 categories pass",
      "refer_to_analyst_floors": {"credential_access": X, ...}
    }

  Call charts.py.

charts.py:
  import matplotlib
  matplotlib.use("Agg")
  import sys
  from pathlib import Path
  sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
  from src.viz.bridge_common import save_figure, COLORS

  Chart 1 (prod4_accuracy_vs_threshold_by_category):
    5 curves, one per category. X: threshold_sweep (0.50 → 0.99).
    Y: accuracy_mean per curve, ± std fill.
    Horizontal dashed line at 0.85 (ACCURACY_GATE).
    Mark threshold* per category with dot + label.
    Legend. Title: "Auto-approve accuracy vs threshold (centroidal synthetic, 50 seeds)"
    save_figure; plt.close; print("[CHART 1]...")

  Chart 2 (prod4_coverage_vs_threshold_by_category):
    5 curves. X: threshold_sweep. Y: coverage_mean ± std fill.
    Vertical dashed line at current global threshold (0.90).
    Horizontal dashed line at current global coverage (11.5%).
    Mark threshold* per category with dot.
    Title: "Auto-approve coverage vs threshold (centroidal synthetic, 50 seeds)"
    save_figure; plt.close; print("[CHART 2]...")

  Chart 3 (prod4_threshold_recommendation_table):
    5-row matplotlib table. Columns: Category | threshold* | accuracy at threshold* | coverage.
    Cell background: green if threshold* <= 0.75 and accuracy >= 0.85,
                     orange if threshold* > 0.75,
                     red if threshold* is NaN (below-gate).
    Title: "Recommended per-category thresholds — v5.5-R1 (PROD-4)"
    Caption: "Gate: ≥3 categories pass (threshold* ≤ 0.75, accuracy ≥ 0.85)"
    save_figure; plt.close; print("[CHART 3]...")

TESTS before declaring done:
  - 50 seeds × 1000 decisions = 50,000 recorded decisions (assert total == 50,000)
  - threshold_star computed for all 5 categories (NaN is valid if below-gate)
  - Gate verdict N/5 printed
  - prod4_threshold_table.json exists and has "refer_to_analyst_floors" key
  - All 3 chart .png and .pdf files exist in paper_figures/

ACCEPTANCE CRITERION:
  prod4_threshold_table.json exists with threshold_star for all 5 categories
  and gate verdict "N/5 categories pass" printed to stdout.
  If any category has threshold_star = NaN: note which category, but do not
  consider this a prompt failure — it is informative data.

AFTER THIS RUNS:
  1. Update project_status_and_plan_v3_part2 Phase 5 (AUTO-*) sprint prompt
     with the actual threshold* values from prod4_threshold_table.json.
  2. Update refer_to_analyst confidence floor in soc_copilot_design_v5_4 §15.
     Replace "0.70 (design estimate — pending PROD-4)" with measured per-category floors.
  3. Update math_synopsis_v7 §14 threshold table with PROD-4 results.
```

---

## Step 3: FX-1-PROXY-REAL — Realistic L2 Margin Distribution Characterization

**Source:** experiments_catalog_v8_part2a §7 ✅ PROMPT READY + **σ_max derivation step ADDED**
**Location:** `experiments/expFX1_proxy_real/`
**Compute:** Local, public APIs (CISA KEV, NVD, MITRE ATT&CK STIX — no auth required)
**Corrections:** Added σ_max derivation (Step 5 in run.py) which was in design intent
  (math_synopsis_v7 §9) but missing from catalog prompt
**What it unblocks:** σ_max empirical value (replaces placeholder 1.0); EXP-S2-REPRO Arm A parameterization

---

```
Repo: cross-graph-experiments
Location: experiments/expFX1_proxy_real/
Design spec: math_synopsis_v7 §9 (σ_max = p10 of empirical L2 margin distribution)

CONSTRAINTS:
- Do NOT use git. Do NOT start debugger. Log-based debugging only.
- Cache all API responses to data/raw/ subdirectory — avoid re-pulling on reruns.
- τ = 0.1 for baseline ECE comparison. Run sweep to find τ_optimal.
- All L2 margin computations use ProfileScorer with GT-initialized centroids.
- Regime: "real IOC data + synthetic factor mapping" — label all output accordingly.

READ FIRST:
  src/models/profile_scorer.py → verify score() returns confidence and action
  src/viz/bridge_common.py     → verify save_figure, COLORS
  src/data/category_alert_generator.py → verify factor vector structure (d=6)
  soc_copilot_design_v5_4 §9  → current σ_max=1.0 placeholder — this experiment replaces it

PUBLIC APIs (no authentication required):
  CISA KEV:     https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json
  NVD CVE:      https://services.nvd.nist.gov/rest/json/cves/2.0 (max 2000/day, paginate)
  MITRE ATT&CK: https://github.com/mitre/cti/raw/master/enterprise-attack/enterprise-attack.json

FILES TO CREATE:
  1. experiments/expFX1_proxy_real/data_pull.py
  2. experiments/expFX1_proxy_real/factor_mapper.py
  3. experiments/expFX1_proxy_real/distribution_analysis.py
  4. experiments/expFX1_proxy_real/run.py
  5. experiments/expFX1_proxy_real/charts.py

data_pull.py:
  - fetch_cisa_kev() → list[dict]
    Pull full JSON. Cache to data/raw/cisa_kev.json.
    If cache exists and is < 24h old: read from cache. Else: fetch and cache.
    Print: "[DATA] Pulled N CISA KEV records"

  - fetch_nvd_cves(max_results=500) → list[dict]
    Paginate through NVD API (resultsPerPage=100, startIndex iterates).
    Cache to data/raw/nvd_cves.json.
    Print: "[DATA] Pulled M NVD CVEs"

  - fetch_mitre_attack() → list[dict]
    Pull STIX bundle from GitHub raw URL.
    Filter to type=="attack-pattern" objects. Extract: id, name, x_mitre_platforms,
    x_mitre_tactic_type fields.
    Cache to data/raw/mitre_attack.json.
    Print: "[DATA] Pulled K ATT&CK techniques"

factor_mapper.py:
  Map IOC data to 3 of the 6 SOC factors (the 3 that can be derived from threat intel):
    Factor 2: threat_intel_enrichment → normalize CVSS baseScore / 10.0 → [0, 1]
      If no CVSS: use 0.5 (neutral)
    Factor 1: asset_criticality proxy → CWE type mapping:
      authentication/privilege escalation → 0.85
      memory corruption / code execution → 0.75
      info disclosure → 0.45
      other / no CWE → 0.30
    Factor 3: pattern_history proxy → KEV recurrence count:
      N appearances across KEV advisories → min(N / 10.0, 1.0)
      Single appearance → 0.10

  category_proxy inference from KEV "product" field:
    "windows/active directory/ldap/kerberos" → credential_access
    "web/api/cloud/s3/azure/gcp" → cloud_infrastructure
    "vpn/rdp/citrix/remote" → lateral_movement
    "email/phishing/browser/pdf" → data_exfiltration
    "other/uncategorized" → insider_threat (default)

  map_to_factors(records) → pd.DataFrame with columns:
    [threat_intel_val, asset_crit_val, pattern_hist_val, category_proxy, source_id]

distribution_analysis.py:
  - fit_gaussian(values: np.ndarray) → (mean: float, std: float)
  - kl_divergence(p_real, p_synth, n_bins=50) → float  (epsilon-smoothed)
  - distribution_stats(values) → {"mean", "std", "skewness", "kurtosis", "p10", "p25", "p90"}
  - tau_ece_sweep(real_factor_data, tau_values) → list[float]
    For each τ:
      Build ProfileScorer with GT-initialized centroids (expert μ₀, tau=τ)
      For each row in real_factor_data: score using GT-aligned factor vector (pad 3 unmapped
        factors with 0.5 neutral)
      Compute ECE (10 bins) comparing confidence to oracle correctness
    Return [ece_at_tau for tau in tau_values]

  # σ_max derivation (NEW — not in original catalog):
  - compute_l2_margin_distribution(real_factor_data, scorer) → np.ndarray
    For each row in real_factor_data:
      f = factor_vector (6-dim, 3 real + 3 neutral)
      c = category_proxy_idx
      Compute all A=5 L2 distances: dist[a] = ||f - μ[c,a,:]||²
      Sort distances ascending: dist_sorted[0] ≤ dist_sorted[1] ≤ ...
      margin = dist_sorted[1] - dist_sorted[0]  # gap between best and second-best action
      Record margin
    Return array of margins (one per IOC record)

  - sigma_max_from_margin_distribution(margins: np.ndarray) → float
    """
    σ_max = p10 of empirical L2 margin distribution.
    Rationale (math_synopsis_v7 §9): σ_max must be < the typical margin between
    best and second-best action distance, so synthesis bias cannot override
    clear-majority decisions. p10 is conservative — it uses the tight end of the
    margin distribution.
    """
    return float(np.percentile(margins, 10))

run.py:
  PARAMETERS:
    tau_sweep = [0.01, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5]
    RANDOM_SEED = 42

  Step 1: Pull data
    records = fetch_cisa_kev() + fetch_nvd_cves(500) + fetch_mitre_attack()
    Print: "[RUN] Total records: N"

  Step 2: Map to factor space
    factor_data = map_to_factors(records)
    Print: "[RUN] Factor mapping complete. N={len(factor_data)} rows."
    For each of 3 factors: print distribution_stats summary

  Step 3: KL divergence from synthetic
    synthetic_reference = {
      "threat_intel_enrichment": (mean=0.65, std=0.20),  # from SOCDomainConfig centroidal
      "asset_criticality": (mean=0.70, std=0.18),
      "pattern_history": (mean=0.50, std=0.25),
    }
    For each factor: compute KL between real distribution and synthetic reference Gaussian
    Print: "KL divergences from synthetic centroidal reference:"
    For each factor: print "  {name}: KL={val:.3f} ({'LOW' if val < 0.1 else 'MODERATE' if val < 0.5 else 'HIGH'})"

  Step 4: τ-ECE sweep on real data
    ece_values = tau_ece_sweep(factor_data, tau_sweep)
    tau_optimal = tau_sweep[np.argmin(ece_values)]
    Print: "τ-ECE sweep on real IOC data:"
    For each (τ, ECE): print "  τ={τ:.2f}: ECE={ECE:.4f}"
    Print: "Optimal τ (real data): {tau_optimal}"
    Print: "V3B τ=0.1 ECE on synthetic: 0.036"
    Print: "Recalibration required: {'YES' if abs(tau_optimal - 0.1) > 0.05 else 'NO'}"

  Step 5: σ_max derivation (CRITICAL OUTPUT — gates Arm A of EXP-S2-REPRO)
    Build ProfileScorer with GT-initialized centroids (tau=0.1, categories=CATEGORIES)
    margins = compute_l2_margin_distribution(factor_data, scorer)
    sigma_max = sigma_max_from_margin_distribution(margins)
    Print: "=== σ_max DERIVATION (math_synopsis_v7 §9) ==="
    Print: "L2 margin distribution statistics:"
    Print margin_stats = distribution_stats(margins)
    Print: "σ_max = p10 = {sigma_max:.4f}"
    Print: "Previous placeholder: σ_max = 1.0"
    Print: "COPY THIS VALUE INTO soc_copilot_design_v5_4 §9 σ_max field"
    Print: "COPY THIS VALUE INTO EXP-S2-REPRO Arm A σ injection parameters"
    Print: "If σ_max < 0.10: flag as 'tightly-bounded synthesis' — σ influence is minimal"
    Print: "If σ_max > 0.50: flag as 'loosely-bounded synthesis' — review safety architecture"

  Step 6: Call charts.py

  WRITE:
    fx1r_results.json:
    {
      "n_records": N,
      "kl_divergences": {"threat_intel": X, "asset_criticality": Y, "pattern_history": Z},
      "tau_optimal_real_data": tau_optimal,
      "tau_0_1_ece_real": ECE_at_0_1,
      "recalibration_required": bool,
      "l2_margin_stats": margin_stats,
      "sigma_max": sigma_max,
      "sigma_max_source": "p10 of empirical L2 margin distribution (FX-1-PROXY-REAL)"
    }

charts.py:
  import matplotlib; matplotlib.use("Agg")
  import sys; from pathlib import Path
  sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
  from src.viz.bridge_common import save_figure, COLORS

  Chart 1 (fx1r_factor_distributions):
    3-panel subplot (one per mapped factor). Each panel:
      Histogram of real values (30 bins, blue alpha=0.6)
      Gaussian fit overlay (red dashed)
      Synthetic centroidal reference Gaussian (green dashed)
      Annotate: skewness, KL divergence from synthetic
    save_figure; plt.close; print("[CHART 1]...")

  Chart 2 (fx1r_kl_divergence):
    3 horizontal bars, one per factor. X: KL divergence.
    Reference lines at 0.10 (low, green) and 0.50 (high, red).
    Bar color: green if <0.1, orange if 0.1–0.5, red if >0.5.
    save_figure; plt.close; print("[CHART 2]...")

  Chart 3 (fx1r_tau_ece_real):
    Line plot: ECE vs τ (blue, real IOC data) + V3B synthetic result (gray dashed).
    Vertical dashed at τ=0.1 (V3B validated).
    Mark τ_optimal with a dot + label.
    Annotate: "Recalibration: YES/NO"
    save_figure; plt.close; print("[CHART 3]...")

  Chart 4 (fx1r_l2_margin_distribution):  [NEW — not in catalog]
    Histogram of L2 margin values (50 bins). Blue fill.
    Vertical dashed line at σ_max (p10). Label: "σ_max = {val:.4f}"
    Vertical dashed line at p50 (median margin).
    X-axis: "L2 margin (best vs 2nd-best action)"
    Y-axis: "Count"
    Title: "L2 margin distribution — σ_max derivation (FX-1-PROXY-REAL)"
    save_figure; plt.close; print("[CHART 4] fx1r_l2_margin_distribution saved")

TESTS before declaring done:
  - ≥ 500 total records pulled across all 3 sources (or print "RATE LIMITED: N records")
  - factor_data has ≥ 100 rows with non-NaN values
  - fx1r_results.json exists with "sigma_max" key
  - sigma_max is finite (not NaN, not inf)
  - All 4 chart .png and .pdf files exist in paper_figures/
  - τ-ECE curve has a minimum (not flat — assert min(ece_values) < max(ece_values))
  - Print: "Recalibration required: YES/NO"

ACCEPTANCE CRITERION:
  fx1r_results.json exists with sigma_max field.
  σ_max value is printed to stdout.
  Chart 4 (fx1r_l2_margin_distribution) exists in paper_figures/.

AFTER THIS RUNS:
  1. Update soc_copilot_design_v5_4_part1 §9 σ_max:
     Replace "σ_max = 1.0 (placeholder)" with "σ_max = {value} (FX-1-PROXY-REAL p10)"
  2. Update EXP-S2-REPRO Arm A config: set σ injection to use derived σ_max.
  3. If recalibration_required = YES:
     Add to tech debt: "TD-NEW: τ recalibration required before first customer deployment.
     τ_optimal={value} differs from V3B τ=0.1 by > 0.05. Run VPS recalibration before live."
```

---

## Step 5: EXP-S2-REPRO — Arm 0 Only (Replication Check)

**Source:** experiments_catalog_v8_part2a §7 ✅ PROMPT READY (Arm 0 only — Arm A requires σ_max from Step 3)
**Location:** `experiments/synthesis/expS2_repro/`
**Compute:** Local, ~15 min (10 seeds × 3 poison rates × 500 decisions)
**Corrections:** None — Arm 0 prompt is accurate. Arm A and B deliberately excluded until σ_max is known.
**What it unblocks:** Arm A eligibility (Arm A requires Arm 0 PASS + σ_max from FX-1-PROXY-REAL)

---

```
Repo: cross-graph-experiments
Location: experiments/synthesis/expS2_repro/
Design spec: experiments_catalog_v8_part2a §7 (Arm 0 only)

CONSTRAINTS:
- Do NOT use git. Do NOT start debugger. Log-based debugging only.
- Arm 0 ONLY. Do NOT run Arms A or B in this prompt.
- A=5 (C=5, A=5, d=6) — refer_to_analyst is the 5th action.
- tau = 0.1 always.
- STOP AND PRINT "ARM 0 FAIL" if ≤2pp result is not replicated. Do not proceed to Arm A.
- Regime: centroidal synthetic. Label all output.

HARD GATE (pre-declared, immutable):
  Arm 0 PASS: accuracy degradation at 20% poison ≤ 2pp vs λ=0 baseline
  Arm 0 FAIL: degradation > 2pp
  Do NOT change this threshold after seeing results.
  If FAIL: print diagnosis and stop. Do not run Arm A.

READ FIRST:
  src/models/profile_scorer.py   → verify ProfileScorer + build_profile_scorer
  src/models/synthesis.py        → verify SynthesisBias class and constructor
  src/data/category_alert_generator.py → verify CategoryAlertGenerator
  src/eval/auac.py               → verify compute_auac function signature
  src/eval/op_harness.py         → verify run_with_loop2 function (if it exists)
    If op_harness.py does not exist: implement the operator loop inline in run.py
  paper_figures/                 → check for existing expS2* files

FILES TO CREATE:
  1. experiments/synthesis/expS2_repro/run.py
  2. experiments/synthesis/expS2_repro/charts.py

run.py:
  from src.models.profile_scorer import ProfileScorer, build_profile_scorer
  from src.models.synthesis import SynthesisBias
  from src.data.category_alert_generator import CategoryAlertGenerator
  from src.eval.auac import compute_auac
  import numpy as np, json
  from pathlib import Path

  ARM_0 = {
    "lambda_val": 0.2,
    "loop2": False,         # Arm 0: Loop 2 is FROZEN (centroids do not update)
    "seeds": 10,
    "poison_rates": [0.0, 0.20, 0.40],
    "N_pre": 0,             # Arm 0: no warmup, cold start
    "N_post": 500,          # 500 decisions with operator active
    "generator": "centroidal",
    "tau": 0.1,
  }

  REPLICATION_TARGET = {
    "poison_rate_0_20": {"auac_delta_max": 0.02},  # ≤ 2pp at 20% poison
    "source": "EXP-S2 original result"
  }
  RANDOM_SEED_BASE = 42

  # σ tensor construction:
  def build_sigma(C, A, poison_rate, lambda_val, seed):
    """
    σ[c,a] = +0.4 for correct cells (λ-weighted toward oracle),
             -0.4 for poisoned cells (fraction = poison_rate of cells)
    poison_rate fraction of (C×A) cells get -0.4 injection.
    """
    np.random.seed(seed)
    sigma = np.zeros((C, A))
    n_poison = int(poison_rate * C * A)
    flat_indices = np.random.choice(C * A, size=n_poison, replace=False)
    sigma_flat = np.full(C * A, 0.4)
    sigma_flat[flat_indices] = -0.4
    return sigma_flat.reshape(C, A)

  # Arm 0 execution:
  results_arm0 = {}  # key: (seed, poison_rate) → auac_delta

  for seed_idx in range(ARM_0["seeds"]):
    for poison_rate in ARM_0["poison_rates"]:
      seed = RANDOM_SEED_BASE + seed_idx
      gen = CategoryAlertGenerator(seed=seed, C=5, A=5, d=6)
      scorer = build_profile_scorer(C=5, A=5, d=6, tau=ARM_0["tau"])
      sigma = build_sigma(5, 5, poison_rate, ARM_0["lambda_val"], seed=seed+1000)

      # Baseline (λ=0, no σ influence):
      scorer_baseline = build_profile_scorer(C=5, A=5, d=6, tau=ARM_0["tau"])
      baseline_scores = []
      for _ in range(ARM_0["N_post"]):
        alert = gen.next()
        result = scorer_baseline.score(alert.factors, alert.category_idx)
        baseline_scores.append(result.action == alert.oracle_action)
        # loop2=False: do not update centroids

      auac_baseline = compute_auac(baseline_scores)

      # With operator (λ=0.2, σ active):
      scorer_op = build_profile_scorer(C=5, A=5, d=6, tau=ARM_0["tau"])
      gen.reset(seed=seed)  # reset to same sequence
      op_scores = []
      for _ in range(ARM_0["N_post"]):
        alert = gen.next()
        # Scoring with synthesis bias: score = L2_score + lambda * sigma[c, a]
        # If SynthesisBias integrates into scorer: use SynthesisBias API
        # If not: apply manually: adjusted_probs = raw_probs * exp(lambda * sigma[c, :])
        result = scorer_op.score_with_sigma(
            f=alert.factors, c=alert.category_idx,
            sigma=sigma, lambda_val=ARM_0["lambda_val"]
        )
        # If score_with_sigma doesn't exist: implement inline per Eq. 4-synthesis
        op_scores.append(result.action == alert.oracle_action)
        # loop2=False: do not update centroids

      auac_op = compute_auac(op_scores)
      auac_delta = auac_op - auac_baseline
      results_arm0[(seed_idx, poison_rate)] = auac_delta

  # Gate evaluation:
  delta_at_20pct = [results_arm0[(s, 0.20)] for s in range(ARM_0["seeds"])]
  mean_delta = np.mean(delta_at_20pct)
  ci_low, ci_high = np.percentile(
    [np.mean(np.random.choice(delta_at_20pct, size=len(delta_at_20pct), replace=True))
     for _ in range(1000)], [2.5, 97.5])
  degradation = -mean_delta  # positive = degradation

  print("=== EXP-S2-REPRO ARM 0: Replication Check ===")
  print(f"λ=0.2 (frozen, original EXP-S2 conditions)")
  print(f"Regime: centroidal synthetic, {ARM_0['seeds']} seeds")
  print()
  for pr in ARM_0["poison_rates"]:
    deltas = [results_arm0[(s, pr)] for s in range(ARM_0["seeds"])]
    print(f"Poison {pr*100:.0f}%: AUAC delta = {np.mean(deltas):.4f} "
          f"[{np.percentile(deltas, 2.5):.4f}, {np.percentile(deltas, 97.5):.4f}]")
  print()
  print(f"At 20% poison: degradation = {degradation:.4f} ({degradation*100:.2f}pp)")
  print(f"Replication target: ≤ 0.02 (≤ 2pp) — from EXP-S2 original")

  if degradation <= 0.02:
    print("ARM 0: PASS ✓ — replication confirmed")
    print("Next step: Run FX-1-PROXY-REAL (Step 3) to get σ_max, then run Arm A.")
  else:
    print(f"ARM 0: FAIL ✗ — degradation {degradation:.4f} > 0.02 threshold")
    print("STOP. Do not run Arm A or Arm B until discrepancy is diagnosed.")
    print("Check: Was loop2=False enforced? Was N_pre=0 as in original EXP-S2?")
    print("Check: Does SynthesisBias.apply() match original EXP-S2 σ injection formula?")

  Call charts.py.
  Write to expS2r_arm0_results.json.

charts.py:
  import matplotlib; matplotlib.use("Agg")
  import sys; from pathlib import Path
  sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
  from src.viz.bridge_common import save_figure, COLORS

  Chart 1 (expS2r_arm0_replication):
    Side-by-side bars for poison rates 0%, 20%, 40%.
    Two bar groups per poison rate:
      "Arm 0 (this run)": mean AUAC delta, error bar = 95% CI
      "EXP-S2 original": reference value (lookup from prior results or use 0.02 as reference)
    Horizontal dashed at 0 (no change). Horizontal dashed at -0.02 (gate threshold).
    Gate verdict annotated in top-right corner.
    Title: "EXP-S2-REPRO Arm 0: Replication Check (λ=0.2, frozen, centroidal synthetic)"
    save_figure(fig, "expS2r_arm0_replication", output_dir="paper_figures")
    plt.close(); print("[CHART 1] expS2r_arm0_replication saved")

TESTS before declaring done:
  - 10 seeds × 3 poison rates = 30 runs complete
  - results_arm0 has 30 entries (all (seed, poison_rate) combinations)
  - expS2r_arm0_results.json exists
  - Chart 1 exists in paper_figures/ as .png and .pdf
  - Gate verdict printed: either "PASS" or "FAIL"

ACCEPTANCE CRITERION:
  Gate verdict printed ("ARM 0: PASS" or "ARM 0: FAIL").
  expS2r_arm0_results.json exists with all 30 (seed, poison_rate) entries.

AFTER THIS RUNS:
  If PASS: Arm A is eligible once FX-1-PROXY-REAL (Step 3) completes and σ_max is known.
           Update §4.4 master execution table: Step 5 → ✅ DONE.
           Update Step 6 status: "READY — waiting for FX-1-PROXY-REAL σ_max"
  If FAIL: Stop. Add to tech debt: "EXP-S2-REPRO Arm 0 FAIL — σ injection
           formula or loop2 freeze mechanism changed between EXP-S2 and v5.0.
           Must diagnose before any synthesis layer work proceeds."
```

---

## Summary: Execution Checklist

```
Pre-flight (before any experiment):
  □ cd cross-graph-experiments
  □ Activate python_expts_venv
  □ python -c "from src.models.profile_scorer import ProfileScorer; print('OK')"
    If ImportError: fix import path before proceeding.
  □ ls paper_figures/ → note current count (new charts will be added)

Parallel execution (all 4 can run simultaneously):
  □ Step 1 (PROD-3): python experiments/prod/prod3_shadow_baseline/run.py
  □ Step 2 (PROD-4): python experiments/prod/prod4_threshold_calibration/run.py  [~2hrs]
  □ Step 3 (FX-1-PROXY-REAL): python experiments/expFX1_proxy_real/run.py
  □ Step 5 (EXP-S2-REPRO Arm 0): python experiments/synthesis/expS2_repro/run.py

Post-experiment updates (after each run completes):
  After PROD-3: Update soc_copilot_design_v5_4_part1 §23.4 θ values
  After PROD-4: Update sprint Part 2 Phase 5 threshold table; update §15 confidence floor
  After FX-1:   Update soc_copilot_design §9 σ_max; check τ recalibration flag
  After Arm 0:  Update §4.4 master execution table; if PASS → note Arm A readiness

These 4 steps collectively unblock:
  → Sprint Phase 2 (NL template engine, T1-1) — needs PROD-3 + PROD-4 results
  → Sprint Phase 4 (shadow mode) — needs PROD-3 calibration table
  → Sprint Phase 5 (auto-approve) — needs PROD-4 threshold table
  → EXP-S2-REPRO Arm A — needs Arm 0 PASS + FX-1-PROXY-REAL σ_max
  → soc_copilot_design §9 σ_max — needs FX-1-PROXY-REAL
```

---

*v5.5 Sprint Blocker Prompts · March 13, 2026*
*Sources: experiments_catalog_v8_part2a §7 (FX-1-PROXY-REAL, EXP-S2-REPRO),*
*experiments_catalog_v8_part3 §14 (PROD-3, PROD-4).*
*Corrections: "insider_threat" replaces "travel_anomaly" in PROD-4 category list.*
*Addition: σ_max derivation (Step 5 + Chart 4) added to FX-1-PROXY-REAL.*
*EXP-S2-REPRO: Arm 0 only. Arms A and B require σ_max from FX-1-PROXY-REAL first.*
