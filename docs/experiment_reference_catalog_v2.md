# Experiment Reference Catalog — Compounding Intelligence Platform
**Version:** v2 · March 21, 2026 | **Repo:** `cross-graph-experiments`
**Total experiments:** ~104 complete · ~20 planned
**Update from v1:** +59 experiments. New series: Block 5A/5B harnesses, Phase 1 persona sweeps (24 personas, 72 runs), Priority 1 validation (9 personas), V-MV-KERNEL factorial (360 cells), kernel deliverables (shrinkage test, S2P hetero, selector). DiagonalKernel validated (+13pp SOC). Explanation A confirmed. ShrinkageKernel deprioritized. Referral architecture settled (4 experiments: A=4 confirmed, rules ship, confidence gate rejected).

> **How to use this document:**
> 1. **Find an experiment** — use the Quick Index table below
> 2. **Look up details** — jump to the series section for description, question, method, result, and files
> 3. **Find a chart** — every entry lists exact filenames in `paper_figures/`
> 4. **Find a result file** — every entry lists the results file path in `experiments/`

---

## CANONICAL CONFIGURATION (always use these)

| Parameter | Value | Source | Forbidden |
|---|---|---|---|
| **Default kernel** | **DiagonalKernel(1/σ²) for noise_ratio > 1.5; L2 fallback** | **V-MV-KERNEL factorial** | Dot product (61%) |
| Temperature τ | 0.1 (per-customer via TD-034) | V3B | 0.25 (ECE=0.190) |
| **η_confirm** | **0.05** | **P0 fix, 24 personas** | — |
| **η_override** | **0.01** | **P0 fix, 24 personas** | **η_neg=1.0 (ECE=0.49, FORBIDDEN)** |
| η_neg | 0.05 | SHIFT-2 | **1.0 (FORBIDDEN)** |
| λ (synthesis) | 0.5 | OP1-FINAL | 0.8 (harm:benefit 5:1) |
| **Tensor shape** | **(6,4,6) = 144 values** | **A=4 migration** | (6,5,6) = old A=5; (5,5,6) = older |
| **Actions A** | **4: escalate, investigate, suppress, monitor** | **A=4 migration** | A=5 was interim |
| IKS κ | 0.20 | PROD-1 | 0.30 (near-floor) |
| **θ_min** | **0.467** | **T_max=21 days canonical** | 0.434 (old, too lenient) |
| **LEARNING_ENABLED** | **False default. Enable per-customer after shadow.** | **Deployment qualification** | True without qualification |
| **Noise ceiling (L2)** | **σ ≤ 0.157 GREEN. σ > 0.157 RED.** | **1D sweep, V-B3** | — |
| **Noise ceiling (Diagonal)** | **σ ≤ 0.25 GREEN. σ > 0.25 RED.** | **V-MV-KERNEL, V-HC-CONFIG** | — |
| **ShrinkageKernel** | **DEPRIORITIZED to v7.0** | **Deliverables D2/D3: <1pp gap** | Ship at v6.0 |
| Mahalanobis | Only with ECE validation | FX-1 | On realistic data (ECE=0.275) |

---

## QUICK INDEX — All Experiments

### Series 0-8 (v3.0-v5.5 — 45 experiments, unchanged from v1)

| ID | Series | One-line description | Status | Key number |
|---|---|---|---|---|
| EXP-1 | S0 | ScoringMatrix convergence (pre-ProfileScorer) | ✅ | 59.6% at dec 500 |
| EXP-2 | S0 | Cross-graph discovery, normalization ablation | ✅ | 145.2× above random |
| EXP-3 | S0 | Multi-domain scaling preliminary (b=2.30) | ✅ | b=2.30, n=2–6 |
| EXP-4 | S0 | Parameter sensitivity: asymmetry_ratio + embedding_dim | ✅ | Phase transition σ=0.3 |
| EXP-5 | S1 | Oracle quality ceiling with dot product | ✅ | 79.65% ceiling |
| EXP-A | S1 | G matrix variants — all falsified | ✅ | +1.77pp max |
| EXP-A2 | S1 | Per-category W gating | ✅ | 51.61% |
| **EXP-C1** ⭐ | S1 | **Kernel comparison — THE BREAKTHROUGH** | ✅ | **L2 97.89% vs dot 61.00%** |
| EXP-B1 | S1 | Profile scoring with learning | ✅ | 98.2% warm (pre-fix) |
| EXP-D1 | S1 | Cross-category transfer | ✅ | Config beats transfer 6–14pp |
| EXP-D2 | S1 | Factor interaction discovery | ✅ | 0/75 pairs significant |
| EXP-E1 | S1 | Kernel generalization across distributions | ✅ | L2 wins [0,1]; Maha wins mixed-scale |
| EXP-E2 | S1 | Scale test (large tensor) | ✅ | 99.9% warm at 20×10×20 |
| V1A | S2 | Scaling exponent b=2.11 | ✅ | b=2.11, CI [2.09,2.14], R²=0.999 |
| V1B | S2 | Norm explosion without LayerNorm | ✅ | 2.9M× explosion |
| V2 | S2 | Push update stability / centroid clipping | ✅ | Escape at dec 6 without clipping |
| V3A | S2 | ML baseline comparison | ✅ | L2 94.78% vs XGBoost 92.24% |
| V3B | S2 | Confidence calibration | ✅ | τ=0.1, ECE=0.036 |
| SYNTH-EXP-0 | S3 | Synthesis infrastructure build | ✅ | synthesis.py, rule_projector.py |
| EXP-S1 | S3 | Synthesis bias accuracy | ✅ | +2.30pp @ 60% coverage |
| EXP-S2 | S3 | Poisoning resilience (original) | ✅ | ≤2pp at 20% poison |
| EXP-S2-REPRO | S3 | Poisoning at production λ=0.5 — GATE-M | ✅ | 0.15pp max, GATE-M satisfied |
| EXP-S3 | S3 | Loop 2 firewall independence | ✅ | Frobenius 0.28% |
| EXP-S4 | S3 | λ sensitivity (frozen profiles) | ✅ | Plateau width 0.300 |
| EXP-S5a | S3 | CISA KEV/NVD ingestion | ✅ | 460 claims, σ_saturated |
| EXP-S5b | S3 | Claim extraction quality | ✅ | LLM F1=0.877 |
| EXP-OP1 | S4 | Scalar σ base variant | ✅ | FAIL — near-ceiling |
| EXP-OP1-R | S4 | Realistic profiles variant | ✅ | FAIL |
| EXP-OP1-I | S4 | ε-noise investigation | ✅ | Loop 2 recovers ε≤0.20 |
| EXP-OP-MARGIN | S4 | L2 margin distribution + λ threshold | ✅ | Operative window λ∈[0.5,0.6] |
| EXP-OP1-FINAL | S4 | GATE-OP at λ=0.5 | ✅ | δ=+0.0041, p=0.0008 |
| EXP-OP2 | S4 | Harmful resilience + partial spectrum | ✅ | TTL sufficient at η_neg=0.05 |
| EXP-OP2-N100 | S4 | N=100 confirmation | ✅ | 38% NR (η_neg=1.0, A=5 — stale) |
| EXP-OP3 | S4 | Residual tracker early-warning | ✅⚠️ | AUC≈0.749 (recheck at η_neg=0.05) |
| FX-1r | S5 | Real IOC distribution characterization | ✅ | KL 1.88–2.58 |
| FX-1 scoring | S5 | Accuracy under realistic distributions | ✅ | 71.5% combined, L2 only |
| FX-1 learning | S5 | Learning recovery on realistic data | ✅ | +8.5pp by dec 1500 |
| FX-2 | S5 | Production noise / analyst bias patterns | ✅ | Persistent bias causes lasting drift |
| FX-T5 | S5 | Auto-approve band action analysis | ✅ | Monitor 85.9% (A=5 — re-run A=4) |
| FX-DI07 | S5 | shadow_discount parameter validation | ✅ | GATE FAIL — all values fail |
| SHIFT-1 | S6 | Learning disabled baseline | ✅ | 80.4%, 92.9% coverage@85%prec |
| SHIFT-2 | S6 | Learning validation post bug-fix | ✅ | +2.7% lift, η_neg=0.05 canonical |
| DISC-1 | S6 | Composite discriminant 13-feature | ✅ | 70.4% coverage@85%prec |
| DISC-2 | S6 | Frozen vs learned through composite gate | ✅ | +14pp at δ=0.20 |
| CORR-1a | S6 | Alert routing fix diagnostic | ✅ | 68% misroute eliminated |
| PROD-1 | S7 | IKS sensitivity — κ calibration | ✅ | κ*=0.20 |
| PROD-3 | S7 | Shadow mode agreement baseline | ✅ | θ: 0.744–0.809 per category |
| PROD-4 | S7 | Auto-approve threshold calibration | ✅⚠️ | θ*=0.72–0.87 (A=5 — re-run A=4) |

### Series 10-12 (v5.5→v6.0 — ~55 experiments, NEW in v2)

| ID | Series | One-line description | Status | Key number |
|---|---|---|---|---|
| TD-034 | S10 | τ sweep on soc_product_v50 | ✅ | τ=0.08 optimal (ECE=0.052) |
| PROD-5 | S10 | 60-day convergence simulation | ✅ | ε=0.10, safety_factor=2.0 |
| B-A Phase B | S10 | 90-day A/B Level 2 simulation | ✅ | +10.1pp acceptance, +9.5pp accuracy |
| B5B-PROXY | S10 | 9 LLM-judge persona stress test (3 judges × 3 industries) | ✅ | 4 findings → P0 fix |
| η-SWEEP | S10 | η_override validation (9 personas × 6 values = 54 runs) | ✅ | η_override=0.01 optimal |
| MIN-CONF | S10 | min_confidence gate validation | ✅ | FAIL — confidence stays high during degradation |
| SWEEP-1C | S11 | Quality sweep (5 personas, q̄=0.57-0.91) | ✅ | η_override=0.01 across full spectrum |
| SWEEP-1A | S11 | Volume sweep (5 personas, V=30-400) | ✅ | V=30 viable, all 6 categories by Day 45 |
| SWEEP-1B | S11 | Team size sweep (5 personas, 2-12 analysts) | ✅ | B-A needs ≥8, night shift 18pp gap |
| SWEEP-2D | S11 | Correlated error (2 personas, campaign impact) | ✅ | Conservation detects Day 24. Starvation protective. |
| SWEEP-1D | S11 | Noise sweep (5 personas, σ=0.05-0.25) | ✅ | σ≤0.105 safe, σ>0.157 RED, σ>0.215 degrades |
| SWEEP-2G | S11 | Enrichment shock (2 personas, pre/post enrichment) | ✅ | +7-13pp, no dip, diverging→converging |
| V-B3 | S11 | σ=0.157 cross-validation at q̄=0.60 (4 personas) | ✅ | Ceiling is three-variable (σ×V×q̄) |
| V-B1 | S11 | η=0.01 at AMBER noise (3 personas, σ=0.12-0.155) | ✅ | ALL PASS (+3.3 to +5.1pp) |
| V-CL-RECOVER | S11 | Post-campaign recovery at V=50 and V=100 | ✅ | Recovery 1.0d (V=50), 0.93d (V=100) |
| V-HC-CONFIG-MASK | S12 | Factor quarantine mask on healthcare persona | ✅ | Mask halves degradation but insufficient |
| V-HC-CONFIG-DIAG | S12 | DiagonalKernel on healthcare persona | ✅ | **+3.7pp (Diagonal) vs +0.3pp (L2)** |
| V-MV-KERNEL-UNI | S12 | 216-cell factorial, uniform noise | ✅ | All kernels identical (uniform σ = L2) |
| V-MV-KERNEL-HET | S12 | 144-cell factorial, heterogeneous noise | ✅ | **Diagonal +13.2pp SOC, +6.8pp S2P** |
| V-HC-SHRINKAGE | S12 | Shrinkage vs diagonal on healthcare (3 conditions) | ✅ | B-C gap 0.8pp → Explanation A |
| V-S2P-HETERO | S12 | 18 S2P cells, heterogeneous noise, 3 kernels | ✅ | Shrinkage-diagonal gap -0.2pp |
| SELECTOR-TEST | S12 | KernelSelector self-test on 2 deployments | ✅ | Phase 2 wrong 2/2. Need rolling window. |
| SELECTOR-FIX | S12 | Trajectory selector + simplified rule + 4 HC personas | ✅ | Rolling corrects cumulative. Corr=0.990. |
| **EXP-A4-DIAGONAL** | **S13** | **A=4 vs A=5 under DiagonalKernel** | **✅** | **13pp gap, kernel-independent. A=4 confirmed.** |
| **EXP-REFER-LEARN** | **S13** | **Three referral mechanisms (centroid/LR/KNN)** | **✅** | **All gates fail. Factor vectors insufficient.** |
| **EXP-REFER-COVERAGE** | **S13** | **Referral problem decomposition (10-reason taxonomy)** | **✅** | **65.5% rule, 13.8% context, 20.7% emergent** |
| **EXP-REFER-LAYERED** | **S13** | **4-layer referral architecture head-to-head** | **✅** | **Rules 72.7% DR / 12% FPR. Layer 2 ships.** |

---

## SERIES 0-8 — UNCHANGED FROM v1

> Series 0 through 8 are unchanged from experiment_reference_catalog_v1.md (March 18, 2026).
> See that document for full details of all 45 experiments in those series.
> Key results carried forward: EXP-C1 (36.89pp L2 breakthrough), V3B (τ=0.1, ECE=0.036),
> GATE-OP (λ=0.5, p=0.0008), EXP-S2-REPRO (GATE-M satisfied), PROD-1 (κ*=0.20),
> SHIFT-2 (η_neg=0.05 canonical), DISC-1 (70.4% coverage@85%prec).

---

## SERIES 10 — Persona Infrastructure (Block 5A/5B, March 19-20)

> Harness validation + LLM-judge persona methodology. These experiments built the
> infrastructure that enabled Phase 1 sweeps and the kernel factorial.

---

### TD-034 — τ Sweep on soc_product_v50
**Question:** Is τ=0.10 optimal on the actual SOC product config, or does it need recalibration?
**Method:** τ sweep [0.05, 0.08, 0.10, 0.12, 0.15] on soc_product_v50. 50 seeds × 200 decisions. ECE measurement at each τ.
**Result:** τ=0.08 optimal (ECE=0.052). τ=0.10 ECE=0.069 (slightly worse). Reference for per-customer TD-034 during onboarding.
**Status:** ✅ COMPLETE
**Results file:** `experiments/td034_tau_recalibration/`

---

### PROD-5 — 60-Day Convergence Simulation
**Question:** Does the convergence checker work correctly? What ε threshold avoids false convergence at the noise floor?
**Method:** 60-day simulation, 15 seeds, realistic analyst quality. Original ε=0.05 was AT the noise floor.
**Result:** ε=0.05 hits noise floor (false convergence). Fixed: ε=0.10 + safety_factor=2.0. Accuracy 84.5→90.1% healthy trajectory.
**Impact:** convergence.py v2: EPSILON_DEFAULT=0.10. GAE 285→291 tests.
**Status:** ✅ COMPLETE
**Results file:** `experiments/prod5_convergence/`

---

### B-A Phase B — 90-Day A/B Level 2 Simulation
**Question:** Does Level 2 (AgentEvolver, K=2) produce measurable improvement over 90 days?
**Method:** 90-day simulation. Group A (control) vs Group B (variant). N/2 decisions each. Five-condition gate.
**Result:** Group B +10.1pp acceptance, +9.5pp accuracy, p<0.0001. 73% promotion at K=2.
**Status:** ✅ COMPLETE
**Results file:** `experiments/bridge_a_phase_b/`

---

### B5B-PROXY — 9 LLM-Judge Persona Stress Test ⭐
**Question:** What happens when realistic analyst quality (not 100% oracle) drives the learning system?
**Method:** Three LLM judges (Grok, GPT-4o, Gemini) × 3 industries (FinServ, Healthcare, Technology) = 9 personas. 27 harness runs in 1.6 minutes. Each persona has realistic override_rate, override_quality, fatigue_factor.
**Result:** Four findings not visible in Bernoulli testing:
1. [CALIBRATION] τ=0.10 wrong for 8/9 personas — industry-driven split
2. [ACCURACY] 13-27pp centroid degradation from realistic analyst quality → **P0 BLOCKER**
3. [CONSERVATION] 3-analyst teams breach conservation law systematically
4. [POWER] B-A underpowered at real team sizes (78-308 vs 380 target)
**Impact:** Led to asymmetric η (P0 fix). The most important finding of the persona exercise.
**Status:** ✅ COMPLETE
**Results file:** `experiments/block5b_proxy/results/all_harness_results.json`
**Persona file:** `experiments/block5b_proxy/personas_all.json`

---

### η-SWEEP — η_override Validation (P0 Fix)
**Question:** What η_override value prevents centroid degradation from low-quality overrides?
**Method:** 9 personas × 6 η values [0.005, 0.01, 0.02, 0.03, 0.04, 0.05] = 54 runs.
**Result:** η_override=0.01 captures 80%+ of gain. High-quality teams (financial): +4-6pp. Low-quality (healthcare): zero regression. 0.005 is too slow. 0.02+ starts degrading.
**Impact:** η_override=0.01 canonical. Implemented in ProfileScorer.update().
**Status:** ✅ COMPLETE
**Results file:** `experiments/block5b_proxy/results/eta_override_sweep.json`

---

### MIN-CONF — min_confidence Gate Validation
**Question:** Can a min_confidence gate on update() prevent degradation (alternative to asymmetric η)?
**Method:** Same 9 personas. Gate: only update centroids when system confidence > threshold.
**Result:** FAIL. Confidence stays high (>0.85) even as centroids degrade — A=4 well-separated centroids have min distance 0.35. Gate never fires when it should.
**Impact:** min_confidence gate REJECTED as P0 fix. Asymmetric η is the correct mechanism.
**Status:** ✅ COMPLETE — FAIL
**Results file:** `experiments/block5b_proxy/results/min_confidence_validation.json`

---

## SERIES 11 — Persona Sweeps + Priority 1 Validation (March 20-21)

> Phase 1 sweeps: 6 sweeps, 24 personas, 72 harness runs.
> Priority 1 validation: 3 experiments, 9 personas, gates v6.0.
> All use run_harness.py from experiments/persona_sweeps/.

---

### SWEEP-1C — Quality Spectrum (5 personas)
**Question:** Does η_override=0.01 work across the full analyst quality spectrum?
**Method:** 5 personas at q̄ = 0.57, 0.65, 0.75, 0.82, 0.91. Same noise and volume.
**Result:** ALL PASS. η_override=0.01 validated at every quality level. At q̄=0.57 (worst): +0.5pp with η_override=0.01 (no degradation). At q̄=0.91: +4-6pp.
**Gate:** ✅ PASS — η_override works across full spectrum.
**Status:** ✅ COMPLETE
**Results file:** `experiments/persona_sweeps/results/sweep_1c_quality/`
**Persona file:** `experiments/persona_sweeps/personas_sweep_1c_quality.json`

---

### SWEEP-1A — Volume Spectrum (5 personas)
**Question:** What is the minimum viable alert volume for learning?
**Method:** 5 personas at V = 30, 50, 100, 200, 400 alerts/day.
**Result:** V=30 viable. All 6 categories converge by Day 45. L-08 conservative at V<50 (up to 70%). Below V=30: some categories don't converge within 60 days.
**Gate:** ✅ PASS — V=30 is floor.
**Status:** ✅ COMPLETE
**Results file:** `experiments/persona_sweeps/results/sweep_1a_volume/`
**Persona file:** `experiments/persona_sweeps/personas_sweep_1a_volume.json`

---

### SWEEP-1B — Team Size Spectrum (5 personas)
**Question:** What team size is required for Level 2 (A/B testing)?
**Method:** 5 personas at team sizes 2, 4, 6, 8, 12 analysts.
**Result:** B-A needs ≥8 analysts (not 4 as originally designed). Night shift shows 18pp quality gap. Teams 3-7: use before/after (sequential 250-decision comparison). Teams ≤2: defer to 180 days.
**Gate:** 3/4 PASS. B-A boundary revised.
**Status:** ✅ COMPLETE
**Results file:** `experiments/persona_sweeps/results/sweep_1b_teamsize/`
**Persona file:** `experiments/persona_sweeps/personas_sweep_1b_teamsize.json`

---

### SWEEP-2D — Correlated Error / Campaign Impact (2 personas)
**Question:** What happens when analyst errors are correlated (campaign confusion)?
**Method:** 2 personas with phishing campaign at Day 20-30. 80% of analysts misclassify campaign alerts.
**Result:** Conservation AMBER fires Day 24 (ratio 0.684). Recovery 57.8 decisions (~1.2 days at V=200). **Starvation is PROTECTIVE** — low volume limits corruption when analyst quality drops.
**Key insight:** Risk is "too many bad updates" not "too few updates."
**Gate:** 2/4 PASS.
**Status:** ✅ COMPLETE
**Results file:** `experiments/persona_sweeps/results/sweep_2d_correlated/`
**Persona file:** `experiments/persona_sweeps/personas_sweep_2d_correlated.json`

---

### SWEEP-1D — Noise Spectrum (5 personas)
**Question:** What is the noise ceiling for learning?
**Method:** 5 personas at σ_mean = 0.05, 0.08, 0.105, 0.157, 0.215.
**Result:** σ≤0.105: GREEN (full value, Day60>93%). 0.105<σ≤0.157: AMBER (marginal). σ>0.157: RED (don't deploy learning). σ>0.215: STOP (scorer actively degrades). data_exfiltration most sensitive (first to lose convergence).
**Gate:** 3/5 PASS.
**Impact:** Established product boundaries. Led to P28 deployment qualification gate.
**Status:** ✅ COMPLETE
**Results file:** `experiments/persona_sweeps/results/sweep_1d_noise/`
**Persona file:** `experiments/persona_sweeps/personas_sweep_1d_noise.json`

---

### SWEEP-2G — Enrichment Shock (2 personas)
**Question:** Does connecting a new data source (enrichment) cause a temporary accuracy dip?
**Method:** 2 personas: one pre-enrichment (high noise), one post-enrichment (noise reduced).
**Result:** No dip at enrichment. +7-13pp from noise reduction. One persona was DIVERGING pre-enrichment — enrichment connection caused convergence.
**Gate:** 2/3 PASS.
**Status:** ✅ COMPLETE
**Results file:** `experiments/persona_sweeps/results/sweep_2g_enrichment/`
**Persona file:** `experiments/persona_sweeps/personas_sweep_2g_enrichment.json`

---

### V-B3 — σ=0.157 Cross-Validation at q̄=0.60 (4 personas)
**Question:** Is σ=0.157 the correct noise ceiling for junior teams at low volume?
**Method:** 4 personas: VB3-1 (σ=0.157/V=50), VB3-2 (σ=0.130/V=50), VB3-3 (σ=0.190/V=50), VB3-4 (σ=0.157/V=200). All at q̄≈0.60.
**Result:** NUANCED. VB3-2 improves (+3.3pp) ✅. VB3-3 does NOT degrade (+1.5pp) — too starved to corrupt ❌. VB3-4 degrades (-1.2pp) — volume enables corruption ❌.
**Key finding:** The noise ceiling is a three-variable joint condition: σ × V × q̄. Low volume is protective (same as 2D starvation). The corruption vector is override_volume × noise × low_quality.
**Gate:** V-B3 Gate A PASS, Gate B FAIL, Gate D FAIL (inverted).
**Status:** ✅ COMPLETE
**Results file:** `experiments/persona_sweeps/results/priority1_vb3/`
**Persona file:** `experiments/persona_sweeps/priority1/personas_priority1_vb3.json`

---

### V-B1 — η=0.01 at AMBER Noise (3 personas)
**Question:** Does η_override=0.01 hold across the full AMBER zone (σ=0.12-0.157)?
**Method:** 3 personas: VB1-1 (σ=0.120/V=200), VB1-2 (σ=0.140/V=300), VB1-3 (σ=0.155/V=250).
**Result:** ALL PASS. +5.1pp at σ=0.120, +3.8pp at σ=0.140, +3.3pp at σ=0.155. AMBER zone confirmed safe.
**Gate:** ✅ ALL PASS.
**Status:** ✅ COMPLETE
**Results file:** `experiments/persona_sweeps/results/priority1_vb1/`
**Persona file:** `experiments/persona_sweeps/priority1/personas_priority1_vb1.json`

---

### V-CL-RECOVER — Post-Campaign Recovery at Low Volume (2 personas)
**Question:** Is the 3-day/150-decision recovery claim volume-normalized?
**Method:** 2 personas: VCL-1 (V=50) and VCL-2 (V=100). Both with phishing campaign at Day 20-30.
**Result:** Recovery 15 decisions / 1.0 day at V=50. Recovery 32.5 decisions / 0.93 day at V=100. The 3-day claim is CONSERVATIVE at all volumes — η_override=0.01 attenuates drift itself (peak +0.026-0.059 vs +0.072 at V=200 in 2D-CE1).
**Gate:** ✅ ALL PASS (recovery ≤3 days at both volumes).
**Status:** ✅ COMPLETE
**Results file:** `experiments/persona_sweeps/results/priority1_vcl_recover/`
**Persona file:** `experiments/persona_sweeps/priority1/personas_priority1_vcl_recover.json`

---

---

## SERIES 12 — Kernel Architecture (March 21, 2026) ⭐

> The kernel architecture experiments. Settled the scoring kernel question definitively.
> DiagonalKernel(1/σ²) is v6.0 default. ShrinkageKernel deprioritized to v7.0.
> Explanation A confirmed: noise ratio alone drives kernel advantage. Correlation adds nothing.
> All experiments in experiments/factorial/.

---

### V-HC-CONFIG-MASK — Factor Quarantine Mask on Healthcare
**Question:** Does binary factor masking (exclude 2 noisiest factors) rescue healthcare at σ>0.20?
**Method:** Healthcare persona (σ_mean=0.22, device_trust=0.28, time_anomaly=0.25). Two conditions: A (L2 no mask, control), B (L2 + mask on indices 3,5). 15 seeds × 60 days.
**Result:**
| Condition | Day 1 | Day 60 | Δ |
|---|---|---|---|
| A: L2 no mask | 71.3% | 63.9% | -7.4pp |
| B: L2 + mask | 64.1% | 62.2% | -3.5pp |

Mask halves degradation rate but doesn't rescue. Day 1 drops 7pp from zeroed factors distorting cold-start geometry. Convergence improves (rescues 3/6 categories) but accuracy still degrades. **Binary mask insufficient at σ>0.20.**
**Impact:** Factor mask DEPRECATED when DiagonalKernel proved superior.
**Status:** ✅ COMPLETE — INSUFFICIENT
**Results file:** `experiments/persona_sweeps/results/priority1_vhc_config/vhc_config_results.json`

---

### V-HC-CONFIG-DIAG — DiagonalKernel on Healthcare ⭐
**Question:** Does DiagonalKernel(1/σ²) rescue healthcare where binary mask failed?
**Method:** Same healthcare persona. Three conditions: A (L2), B (L2+mask), C (DiagonalKernel). Weights: travel_match=1.00, asset_criticality=0.81, threat_intel=0.90, time_anomaly=0.52, pattern_history=0.67, device_trust=0.41. 15 seeds × 60 days.
**Result:**
| Condition | Day 1 | Day 60 | Δ |
|---|---|---|---|
| A: L2 only | 69.2% | 69.5% | +0.3pp |
| B: L2 + mask | 64.1% | 65.1% | +1.0pp |
| **C: Diagonal** | **70.2%** | **73.9%** | **+3.7pp** |

DiagonalKernel: highest Day 1 AND strongest learning trajectory. Binary mask HURT Day 1 by 6pp (zeroed factors distort geometry). DiagonalKernel's continuous weighting (device_trust at 0.41, not 0.0) preserves weak signal without letting noise dominate.
**Impact:** Healthcare segment opens at v6.0. Factor mask deprecated. Noise ceiling moves from σ=0.157 (L2) to σ≈0.25 (Diagonal).
**Status:** ✅ COMPLETE — **HEALTHCARE RESCUED**
**Results file:** `experiments/factorial/results/vhc_diagonal/`

---

### V-MV-KERNEL-UNI — Factorial, Uniform Noise (216 cells)
**Question:** Do kernels differ across 5 variables × 2 domains?
**Method:** Full factorial: 3 kernels × 3 σ_eff × 2 q̄ × 2 V × 3 ρ_max = 108 cells per domain (SOC + S2P). UNIFORM noise across all factors within each cell.
**Result:** ALL KERNELS IDENTICAL in both domains. Reason: uniform σ means diag(1/σ²) = scalar × I = L2 after softmax normalization. The factorial was testing nothing — a design flaw.
**Key finding:** σ_eff is the dominant variable (-33.7pp SOC, -17.8pp S2P from σ=0.08→0.22). ρ costs ~8-9pp at ρ=0.6 in both domains.
**Impact:** Identified the need for heterogeneous noise factorial.
**Status:** ✅ COMPLETE — NULL RESULT (design flaw: uniform noise)
**Results file:** `experiments/factorial/results/factorial_soc_results.json`, `factorial_s2p_results.json`

---

### V-MV-KERNEL-HET — Factorial, Heterogeneous Noise (144 cells) ⭐
**Question:** Do kernels differ when factors have different noise levels (the real-world case)?
**Method:** Corrected factorial: 3 kernels × 3 σ_eff × 2 q̄ × 2 V × 2 noise_modes (uniform/heterogeneous) = 72 cells per domain. SOC ratios: 0.5-2.0×. S2P ratios: 0.6-1.8×.
**Result:**
| Domain | L2 (hetero) | Diagonal (hetero) | Lift |
|---|---|---|---|
| SOC | 79.5% | 92.7% | **+13.2pp** |
| S2P | 42.2% | 49.0% | **+6.8pp** |
| SOC at σ=0.22 | 61-64% | 83-85% | **+20-22pp** |

Every real deployment has heterogeneous noise. The diagonal advantage is real, large, and consistent.
**Impact:** DiagonalKernel becomes v6.0 default. The single most important experimental result since EXP-C1.
**Status:** ✅ COMPLETE — **DIAGONAL VALIDATED**
**Results file:** `experiments/factorial/results/heterogeneous_rerun.json`

---

### V-HC-SHRINKAGE — Shrinkage vs Diagonal on Healthcare (Deliverable 2)
**Question:** Does off-diagonal covariance (Σ⁻¹) help beyond diagonal (1/σ²)?
**Method:** Same healthcare persona. Three conditions: A (DiagonalKernel), B (Shrinkage proxy with ρ=0.45 device_trust↔time_anomaly), C (Shrinkage proxy with ρ=0, control).
**Result:**
| Condition | Day 1 | Day 60 | Δ |
|---|---|---|---|
| A: Diagonal | 70.2% | 73.9% | +3.65% |
| B: Shrinkage ρ=0.45 | 70.0% | 73.1% | +3.13% |
| C: Shrinkage ρ=0 | 70.2% | 73.9% | +3.65% |

|B-C| = 0.8pp → **Explanation A confirmed.** Off-diagonal correlation slightly HURTS (upweights correlated noisy dimensions). Noise ratio alone drives the kernel advantage.
**Impact:** ShrinkageKernel deprioritized to v7.0. DiagonalKernel is sufficient.
**Status:** ✅ COMPLETE — EXPLANATION A CONFIRMED
**Results file:** `experiments/factorial/results/kernel_deliverables.json` (deliverable_2)

---

### V-S2P-HETERO — S2P Heterogeneous Noise, 3 Kernels (Deliverable 3)
**Question:** Does the shrinkage vs diagonal gap differ for S2P (denser correlations)?
**Method:** 18 S2P cells (3 kernels × 3 σ_eff × 2 q̄, V=200, heterogeneous noise). Shrinkage uses full Regime A 8×8 correlation matrix (avg ρ≈0.43).
**Result:**
| Kernel | Mean D60 | Mean Δ |
|---|---|---|
| L2 | 44.4% | +2.32% |
| Diagonal | 51.8% | +9.55% |
| Shrinkage | 51.6% | +9.71% |

Shrinkage vs Diagonal gap = -0.18pp. Despite dense S2P correlations, off-diagonal adds nothing. **Explanation A holds for BOTH domains.**
**Impact:** Correlation density does NOT independently matter. One-parameter rule (noise_ratio) is sufficient.
**Status:** ✅ COMPLETE — EXPLANATION A CONFIRMED (both domains)
**Results file:** `experiments/factorial/results/kernel_deliverables.json` (deliverable_3)

---

### SELECTOR-TEST — KernelSelector Self-Test (Deliverable 4)
**Question:** Does KernelSelector pick the right kernel? How many decisions to stabilize?
**Method:** Run KernelSelector on two deployments (Healthcare SOC, S2P Manufacturing) as if in shadow mode. 500 decisions each. Track Phase 2 vs Phase 4 recommendation.
**Result:**
| Deployment | Phase 2 (rule) | Phase 4 (empirical) | Agree? | Stabilized |
|---|---|---|---|---|
| Healthcare SOC | diagonal | L2 | DIFFER | ~350 dec |
| S2P Manufacturing | shrinkage | diagonal | DIFFER | ~350 dec |

Phase 2 rules wrong in 2/2 cases (ρ_max variable caused error). Healthcare flipped at n=350 (diagonal→L2 under cumulative tracking). Selector needs rolling window to catch learning trajectory.
**Impact:** Rolling 100-decision window replaces cumulative. Simplified Phase 2 rule (noise_ratio only, drop ρ_max).
**Status:** ✅ COMPLETE
**Results file:** `experiments/factorial/results/kernel_deliverables.json` (deliverable_4)

---

### SELECTOR-FIX — Trajectory Selector + Simplified Rule + 4 HC Personas ⭐
**Question:** Three asks from roadmap session:
  Ask 1: Does rolling window fix cumulative bias?
  Ask 2: Does simplified Phase 2 rule (noise_ratio > 1.5 → diagonal) work?
  Ask 3: Does diagonal advantage scale with noise ratio across more personas?
**Method:** Ask 1: cumulative vs rolling 100-window on same data stream. Ask 2: 4 test deployments. Ask 3: 4 healthcare personas at ratios 1.6×, 1.9×, 3.2×, 4.6×.
**Result:**

Ask 1 — Rolling CORRECTS cumulative:
  Healthcare: rolling picks diagonal at n=250 (cumulative biased by cold start)
  S2P: rolling CORRECTS from L2 to diagonal

Ask 2 — Simplified rule 4/4 correct:
| Deployment | Ratio | Rule | Expected | Match |
|---|---|---|---|---|
| Healthcare SOC | 1.6× | diagonal | diagonal | YES |
| S2P Manufacturing | 3.0× | diagonal | diagonal | YES |
| FinServ (uniform) | 1.0× | l2 | l2 | YES |
| Startup (extreme) | 6.0× | diagonal | diagonal | YES |

Ask 3 — Diagonal advantage scales perfectly (Corr=0.990):
| Persona | Ratio | L2 Δ | Diagonal Δ | Advantage |
|---|---|---|---|---|
| HC-C (extreme) | 4.6× | -6.3pp | +8.0pp | **+14.3pp** |
| HC-A (one noisy factor) | 3.2× | -3.3pp | +6.4pp | **+9.6pp** |
| HC-B (moderate) | 1.9× | +3.2pp | +5.5pp | +2.3pp |
| HC-D (original) | 1.6× | +0.1pp | +2.3pp | +2.2pp |

Above ratio 1.9×: L2 actively degrades while Diagonal improves. Corr(ratio, advantage) = 0.990. Nearly perfect linear relationship.

**Impact:** KernelSelector updated with rolling window. Simplified Phase 2 rule adopted. Healthcare go-to-market claim backed by 4 personas.
**Status:** ✅ COMPLETE — ALL THREE ASKS ANSWERED
**Results file:** `experiments/factorial/results/selector_fixes.json`

---

## SERIES 13 — Referral Architecture (March 21, 2026) [NEW v2.1]

> Four experiments settled the referral routing architecture. Confidence gate
> REJECTED for referral (14% precision). Policy rules R1-R7 ship at v6.0.
> Override learning deferred to v6.5 (needs 50+ production positives).
> All experiments in experiments/exp_a4_diagonal/, exp_refer_learn/,
> exp_refer_coverage/, exp_refer_layered/.

---

### EXP-A4-DIAGONAL — A=4 vs A=5 Under DiagonalKernel
**Question:** Does DiagonalKernel recover the 13pp accuracy gap between A=4 and A=5?
**Method:** 5 personas × 4 conditions (A=4/A=5 × L2/Diagonal) × 15 seeds = 300 runs. 300 warmup + 200 eval.
**Result:**
| Persona | Ratio | A=4+L2 | A=4+Diag | A=5+L2 | A=5+Diag | Gap(Diag) | Recovery |
|---|---|---|---|---|---|---|---|
| FinServ | 1.0× | 96.7% | 96.7% | 84.6% | 84.6% | 12.1pp | 0% |
| Healthcare | 2.5× | 71.6% | 75.2% | 59.0% | 62.9% | 12.3pp | 31% |
| Technology | 1.5× | 90.2% | 89.8% | 75.4% | 75.6% | 14.2pp | 2% |
| Startup | 3.0× | 78.2% | 84.0% | 64.6% | 70.8% | 13.2pp | 46% |
| Enterprise | 1.0× | 93.4% | 93.4% | 81.5% | 81.5% | 11.9pp | 0% |

Mean gap under Diagonal: 12.7pp. DiagonalKernel recovers only 16% overall. Gap is structural (centroid overlap), not noise. Corr(noise_ratio, D-C advantage) = 0.978.
**Impact:** A=4 CONFIRMED. refer_to_analyst does NOT belong in centroid tensor.
**Status:** ✅ COMPLETE — A=4 CONFIRMED
**Results file:** `experiments/exp_a4_diagonal/results/results.json`

---

### EXP-REFER-LEARN — Three Referral Mechanisms (Factor-Only)
**Question:** Can a separate learned classifier detect referral-worthy alerts from factor vectors?
**Method:** 5 personas × 4 conditions (baseline + 3 mechanisms) × 15 seeds = 300 runs. M1: single centroid per category. M2: 13-feature logistic regression. M3: KNN cosine similarity. 15% should-refer alerts.
**Result:**
| Mechanism | Mean DR | Mean FPR | S1 Impact | Verdict |
|---|---|---|---|---|
| BASELINE (conf gate) | 53.8% | 39.3% | 0pp | Fail (DR<60%, FPR>>10%) |
| M1 (centroid) | 36.8% | 11.2% | -7.6pp | Fail (DR<60%, S1 hit) |
| M2 (logistic) | 47.0% | 9.3% | -7.2pp | Fail (DR<60%, S1 hit) |
| M3 (KNN) | 94.9% | 91.4% | -3.8pp | Fail (FPR catastrophic) |

DR/FPR tradeoff structurally unresolvable at 500 decisions with factor-only features. M2 hits FPR<10% but can only reach 47% DR. The referral signal lives in context, not factor geometry.
**Impact:** Factor-only referral classifiers REJECTED. Richer features needed.
**Status:** ✅ COMPLETE — ALL GATES FAIL
**Results file:** `experiments/exp_refer_learn/results/results.json`

---

### EXP-REFER-COVERAGE — Referral Problem Decomposition ⭐
**Question:** What fraction of the referral problem is rule-expressible vs emergent vs unlearnable?
**Method:** 10-reason referral taxonomy (R1-R10). 5,000 alerts across 5 personas. Measure theoretical coverage at each layer.
**Result:**
| Layer | DR | FPR |
|---|---|---|
| Confidence gate only | 39.6% | 38.7% (noisy) |
| Rules R1-R6 only | 61.1% | 12.0% (precise) |
| + Context R7 | +6.8pp | 0pp delta |
| Theoretical max | 97.1% | — |

Problem decomposition: 65.5% rule-expressible, 13.8% context-dependent, 20.7% emergent.
**Impact:** Rules are the primary mechanism. Confidence gate is a noisy safety net, not a precision trigger. Override learning targets the 20.7% emergent fraction.
**Status:** ✅ COMPLETE
**Results file:** `experiments/exp_refer_coverage/results/coverage_analysis.json`

---

### EXP-REFER-LAYERED — 4-Layer Architecture Head-to-Head ⭐
**Question:** What referral mechanism ships at v6.0? What's the marginal value of each layer?
**Method:** 5 personas × 5 layers × 15 seeds = 375 runs. 1,500 warmup + 500 eval. 19-feature override model (not 6-feature). 15% should-refer alerts.
**Result:**
| Layer | DR | FPR | Precision | Net min/100 |
|---|---|---|---|---|
| L1: Conf gate | 33.3% | 34.9% | 14.0% | 367 |
| **L2: Rules only** | **72.7%** | **12.0%** | **50.7%** | **978** |
| L3: Rules+Conf | 80.4% | 42.4% | 24.3% | 544 |
| L4: Rules+Learn | 73.8% | 13.5% | 48.1% | 960 |

L1→L2: +39.4pp DR, -22.8pp FPR — rules strictly dominate confidence gate.
L3 REJECTED: +7.7pp DR but FPR jumps to 42.4%, net value drops below L0.
L4 REJECTED for v6.0: +1.1pp marginal DR, 24:1 class imbalance, zero learning signal at 1,500 decisions.
**Ship decision: v6.0 SHIPS Layer 2 (Rules R1-R7 only).**
**Impact:** Referral architecture settled. Three phases: Rules (v6.0) → Override learning (v6.5, ≥50 positives) → Retrain (v7.0).
**Status:** ✅ COMPLETE — LAYER 2 SHIPS
**Results file:** `experiments/exp_refer_layered/results/results.json`

---

## SERIES 8 — Arxiv Paper Figures (Reference, unchanged from v1)

> See v1 catalog for full list. All present in `paper_figures/`.

---

## SERIES 9 — Planned / In Queue (Updated)

| ID | Description | Status | Gate / Blocker |
|---|---|---|---|
| **PROD-4 A=4 re-run** | Re-run threshold table on A=4 — BLOCKING | 🔲 Phase 2 priority | A=4 migration ✅ |
| **EXP-OP3-RECHECK** | Residual tracker at η_neg=0.05 | 🔲 Phase 2 | — |
| **FX-T5 A=4 re-run** | Monitor accuracy — may resolve at A=4 | 🔲 Phase 2 | PROD-4 A=4 first |
| V-MV-REGIME | 18 S2P cells with mid-stream correlation shift | 🔲 Lower priority | Kernel code ready |
| V-MV-INCOMPLETE | 36 S2P cells with Financial Risk omitted | 🔲 Lower priority | Tests factor completeness |
| V-B3 extended | σ=0.157 at additional (V, q̄) combinations | 🔲 Nice to have | Refines three-variable boundary |
| GATE-R | Routing accuracy measurement | 🔧 PROMPT READY | Execute now |
| EXP-G1 | γ exponent validation | 🔧 SPEC READY | Colab-pro |
| **Phase 2 sweeps** | 2E fatigue, 2F turnover, Level 3 cross-dimension | 🔲 v6.5 | 25-35 personas |
| **Priority 2 validation** | V-D2 through V-NIGHT (25 personas, v6.5 gates) | 🔲 v6.5 | Gated by v6.5 design |
| **Priority 3 validation** | V-SIM, V-TRIPLE-STRESS, V-CAMPAIGN-INTENSITY | 🔲 Pre-ship | Synthetic streams |
| EXP-OP4–OP6 | Operator decay, multi-operator, analyst quality | 🔧/📐/🔲 | Post GATE-OP |
| EXP-GE1–GE4 | Generic engine series | 🔧/📐/🔲 | GATE-OP |
| FX-3–FX-8 | Real data series | 🔧/📐/🔲 | Various |
| EXP-S5–S8 | Synthesis pipeline | 🔲/📐 | Various |
| ARCH-1–ARCH-5 | Architecture compliance | 🔧/📐 | v5.0/v5.5 |
| PERF-1–PERF-5 | Performance series | 🔧 | v5.0/v5.5 |

---

## V6.0 BACKLOG (Updated)

| Item | Source | Priority | Notes |
|---|---|---|---|
| PROD-4 A=4 re-run | A=4 migration | HIGH | Threshold table stale (A=5 numbers) |
| FX-T5 A=4 re-run | A=4 migration | HIGH | Monitor action may resolve at A=4 |
| EXP-OP3 recheck at η_neg=0.05 | P0 fix | MED | Original at η_neg=1.0 (FORBIDDEN) |
| EXP-OP2 full A=4 re-run | A=4 migration | MED | σ benefit unvalidated on A=4 geometry |
| FX-1/FX-2 A=4 re-run | A=4 migration | LOW | Distribution numbers, likely improve |
| σ normalization for bulk ingestion | EXP-S5a σ_saturated | MED | Prevents ±1.0 ceiling |
| fetch_mitre.py — MITRE ingestion | EXP-S5a | LOW | Completes ingestion pipeline |
| incident_report extraction path | EXP-S5b F1=0.50 | LOW | Both LLM and template fail |
| **KernelSelector rolling window update** | **SELECTOR-FIX** | **✅ DONE** | **447 GAE tests** |
| **DiagonalKernel integration into P28** | **V-MV-KERNEL-HET** | **HIGH** | **Thresholds need Diagonal column** |
| **V-B3 revised deployment gate** | **V-B3** | **MED** | **Three-variable: σ×V×q̄ not σ alone** |
| **V-MV-REGIME (regime shift tracking)** | **Design note §7.5** | **LOW** | **Tests covariance under shift — doesn't affect scoring** |

---

## KEY CORRECTIONS vs PUBLISHED NUMBERS (Updated)

| Published | Correct | Source |
|---|---|---|
| EXP-2: 111× above random | **145.2×** | normalization_summary.json |
| EXP-B1: 90.7% cold start | **96.0% post-fix** (old geometry) | expB1_cold_recovery |
| EXP-B1: 98.2% warm | **80.6% on soc_product_v50** (config gap) | expB1_recheck |
| PROD-4 κ=0.30 (IKS) | **κ=0.20** | PROD-1 experiment |
| OP2: "Lasting damage" | **TTL sufficient at η_neg=0.05** | expOP2_recheck |
| 38% NR "unconditional" | **Conditional — η_neg=1.0, A=5** | claims registry v3.3 |
| **Noise ceiling σ=0.157 absolute** | **Kernel-dependent: L2=0.157, Diagonal=0.25** | V-MV-KERNEL-HET |
| **Noise ceiling σ-only** | **Three-variable: σ×V×q̄** | V-B3 |
| **Factor mask rescues RED zone** | **INSUFFICIENT — DiagonalKernel supersedes** | V-HC-CONFIG-MASK vs V-HC-CONFIG-DIAG |
| **ShrinkageKernel adds correlation value** | **<1pp in both domains — noise ratio alone** | V-HC-SHRINKAGE, V-S2P-HETERO |
| **All kernels equal** | **Only under uniform noise (design flaw)** | V-MV-KERNEL-UNI vs V-MV-KERNEL-HET |
| **Confidence gate catches referrals** | **14% precision — active harm for referral routing** | EXP-REFER-LAYERED |
| **A=5 recoverable with DiagonalKernel** | **13pp gap kernel-independent. A=4 confirmed.** | EXP-A4-DIAGONAL |
| **Factor vectors distinguish referrals** | **All mechanisms fail. Signal is context, not geometry.** | EXP-REFER-LEARN |

---

## PRODUCT BOUNDARIES (from Phase 1 sweeps + kernel factorial)

| Dimension | Boundary (L2) | Boundary (Diagonal) | Evidence |
|---|---|---|---|
| Factor noise | σ≤0.105 GREEN, ≤0.157 AMBER | **σ≤0.157 GREEN, ≤0.25 AMBER** | 1D + V-MV-KERNEL-HET |
| Alert volume | V≥30 viable | Same | 1A sweep |
| Team quality | q̄≥0.70 for full lift | Same (η_override handles low quality) | 1C sweep |
| Team size (L2) | A/B needs ≥8, 3-7 before/after | Same | 1B sweep |
| Graph enrichment | +7 to +13pp | Same (may be larger with Diagonal) | 2G sweep |
| Correlated error | Conservation detects in 5 days | Same | 2D sweep |
| Noise ceiling | σ>0.157 don't deploy learning | **σ>0.25 don't deploy** | V-B3 + V-MV-KERNEL-HET |
| Healthcare | Frozen scorer + remediation first | **Learning from Day 1 with Diagonal** | V-HC-CONFIG-DIAG |
| Kernel selection | — | noise_ratio > 1.5 → Diagonal, else L2 | SELECTOR-FIX Ask 2 (4/4) |
| Selector stabilization | — | ~250 decisions (rolling window) | SELECTOR-FIX Ask 1 |
| **Referral routing** | **Rules R1-R7: 72.7% DR, 12% FPR** | **Same (kernel-independent)** | **EXP-REFER-LAYERED** |
| **Referral mechanism** | **Confidence gate REJECTED (14% precision)** | **Same** | **EXP-REFER-LAYERED** |
| **Override learning** | **v6.5 (≥50 production positives)** | **Same** | **EXP-REFER-LAYERED L4** |

---

## EXPERIMENT SERIES SUMMARY

| Series | Experiments | Time period | Theme |
|---|---|---|---|
| S0 | 4 | Feb 2026 | Pre-catalog: ScoringMatrix paradigm |
| S1 | 9 | Feb-Mar 2026 | Foundation: kernel & architecture |
| S2 | 5 | Mar 2026 | Validation: mathematical properties |
| S3 | 8 | Mar 2026 | Synthesis: Loop 2 / σ operator |
| S4 | 7 | Mar 2026 | Operator: σ in production conditions |
| S5 | 6 | Mar 2026 | Real data: FX series |
| S6 | 5 | Mar 2026 | Calibration science |
| S7 | 4 | Mar 2026 | Product validation: PROD series |
| S8 | — | Mar 2026 | Paper figures (reference) |
| **S10** | **6** | **Mar 19-20** | **Persona infrastructure: harnesses + LLM-judge** |
| **S11** | **9** | **Mar 20-21** | **Phase 1 sweeps + Priority 1 validation** |
| **S12** | **8** | **Mar 21** | **Kernel architecture: factorial + deliverables** |
| **S13** | **4** | **Mar 21** | **Referral architecture: A=4 confirmed, rules ship** |
| S9 | ~20 planned | Ongoing | Planned / in queue |
| **Total** | **~104 complete** | **Feb-Mar 2026** | |

---

*Experiment Reference Catalog v2.1 · March 21, 2026 · cross-graph-experiments repo*
*~104 experiments complete. DiagonalKernel validated (+13pp SOC, +7pp S2P). Explanation A confirmed.*
*Referral architecture settled: Rules R1-R7 = 72.7% DR / 12% FPR. Confidence gate REJECTED (14% precision).*
*A=4 confirmed (13pp structural gap, kernel-independent). Override learning deferred to v6.5 (≥50 positives).*
*Product boundaries established: 6 sweeps, 24 personas, 72 runs, 360 factorial cells, 4 HC personas.*
*Kernel selection: noise_ratio > 1.5 → Diagonal. Rolling 100-window. ~250 decisions to stabilize.*
*ShrinkageKernel deprioritized to v7.0 (<1pp gap in both domains).*
*Factor mask deprecated (Diagonal supersedes: +3.7pp vs mask's -3.5pp on healthcare).*
*"The confidence gate catches uncertainty. The rules catch policy. The experiments proved which is which."*

