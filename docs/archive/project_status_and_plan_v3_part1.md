# Compounding Intelligence Platform
# Project Status & Plan v3 — Part 1: Foundation, Current State & Pre-Sprint Closure

**Version:** 3.1 · Part 1 of 2 · March 15, 2026
**Status:** v5.0 TAGGED (251 GAE tests, 111 SOC tests). v5.5 pre-sprint. 34 experiments. C=6, A=5 verified. CORR-1a routing fixed. ProfileScorer.update() bug fixed (March 15).
**Replaces:** project_status_and_plan (March 6, 2026 edition) — the v5.0 sprint plan
in that document is now obsolete. The 29-prompt v5.0 sprint is complete.
**Authority:** This document + Part 2 are the execution guide for v5.5 and v6.0.
All other documents are reference. When this document conflicts with an older document,
this document wins.

---

> **What this document does NOT contain:**
> The v5.0 sprint prompts. Those are complete. v5.0 is tagged.
> Do not look for them here.

---

## 1. How to Read These Documents

### Two-Part Structure

**Part 1 (this document):** Everything that must be true before the first v5.5 code
prompt runs. Current state. Claims you can and cannot make. Ordered pre-sprint execution
sequence. Completed work. Pending experiment catalog. Features, tech debt, document
update queue.

**Part 2:** The complete v5.5 sprint (phases, prompts, acceptance criteria). v6.0
architecture and requirements. Measures of success for both versions. Coverage maps
showing which sprint items close which product_strategy_v2 gaps.

### Reading Order Rule

**Before opening Part 2:** Read §4 of this document (Pre-Sprint Closure) completely.
Every item in §4 is either a blocking prerequisite for a specific v5.5 sprint prompt
or a calibration input that changes what a sprint prompt builds. Skipping §4 means
building sprint items with design gaps or wrong parameter values.

### First Action When Starting a New Session

```
1. Check §4.1 — which design documents are still not written?
   Write any pending design docs before running experiments or code.

2. Check §4.2 — which now-executable experiments have not yet run?
   Run PROD-3 and PROD-4 immediately. They need no sprint prerequisites.

3. Check §4.4 — what is the master execution state table?
   Find the first incomplete row. Execute it.

4. If all pre-sprint items are complete: open Part 2, find the first
   incomplete sprint phase, read the execution constraints (Part 2 §2),
   then run the first prompt.
```

### Document Authority Hierarchy

| Authority Level | Documents |
|---|---|
| **Authoritative (current)** | project_status_and_plan_v3 Parts 1+2, math_synopsis_v7, claims_registry_v2, gae_design_v9, soc_copilot_design_v5_4, soc_copilot_design_v5_3 (parts 1–3, pre-v5.4 sections), experiments_catalog_v8 (all 3 parts), product_strategy_v2, platform_roadmap_v14 |
| **Architecture narrative (external)** | compounding_intelligence_v7_part1.md, compounding_intelligence_v7_part2.md, compounding_intelligence_v7_part3.md (outputs) |
| **Reference (read for context)** | architecture_philosophy_v1, ci_platform_design_v5_1, cross_graph_attention_v3 |
| **Stale (do not cite)** | Any project_status_and_plan before v3. The published blogs at dakshineshwari.net. Any document before its current version number. **compounding_intelligence_v6 — superseded by v7.** |

---

## 2. Current State (v5.0 Tagged)

### Repositories

| Repo | Path | Branch | Tag | Tests | License |
|---|---|---|---|---|---|
| graph-attention-engine (GAE) | `C:\...\graph-attention-engine-v50` | v5.0-dev | v0.5.0 | 243 | Apache 2.0 |
| gen-ai-roi-demo-v4 (soc-copilot) | `C:\...\gen-ai-roi-demo-v4-v50` | v5.0-dev | v5.0 | 78 | Proprietary |
| cross-graph-experiments | `C:\...\cross-graph-experiments` | main | — | — | Internal |
| ci-platform | Designed, not yet extracted | — | — | — | Apache 2.0 |

Full paths:
- GAE: `C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\graph-attention-engine-v50`
- SOC: `C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50`
- Experiments: `C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\cross-graph-experiments`

### Runtime Environment

```
OS:          Windows 11, PowerShell
Python:      3.11
venv:        python_expts_venv
Neo4j:       localhost:7687 (bolt) · localhost:7474 (browser)
Backend:     localhost:8000
Frontend:    localhost:5174 (Vite) or localhost:3000
```

### What v5.0 Delivered

| Item | Status |
|---|---|
| ProfileScorer L2 scoring — replaces ScoringMatrix (TD-027) | ✅ Complete |
| τ=0.1 in all configs — replaces τ=0.25 (TD-030) | ✅ Complete |
| Append-only centroid update log in ProfileScorer.update() | ✅ Complete |
| refer_to_analyst as action index 4 (n_act=5 canonical) | ✅ Complete |
| Centroid tensor 6×5×6 = 180 values (n_cat=6, n_act=5, d=6) | ✅ Complete (corrected March 14) |
| Hook 1 (DecisionRecord on every score() call) | ✅ Verify: active from day 1 |
| Hook 2 (OutcomeRecord on every update() call) | ✅ Verify: active from day 1 |
| Hook 3 (ProfileSnapshot every 50 decisions) | ✅ Verify: active from day 1 |
| Realistic seed data (25 alert types, 6 SOC categories, healthcare REMOVED March 14) | ✅ Complete |
| 50-seed simulation pool (realistic distributions) | ✅ Complete |
| ci-platform extraction (Phases 8–9) | ✅ Complete |
| OracleProvider protocol (GAE-ORACLE-1) | ✅ Complete |
| Evaluation framework (GAE-EVAL-1 through GAE-DOC-1) | ✅ Complete |

> **Hook verification is critical.** Hooks 1/2/3 must be active from the moment
> v5.0 is deployed. Every day without Hook 1 writing DecisionRecords is permanently
> lost routing accuracy data — GATE-R cannot run retroactively against missing records.
> Verify Hook 1 write path before any live traffic reaches the v5.0 deployment.

### Centroid Tensor (v5.0 Canonical)

```
μ ∈ ℝ^(6 × 5 × 6) = 180 values  [CORRECTED March 14 — was 5×5×6=150]

Categories (n_cat = 6, ORDER IS PERMANENT):
  0: credential_access
  1: threat_intel_match       ← added as first-class category March 14
  2: lateral_movement
  3: data_exfiltration
  4: insider_threat
  5: cloud_infrastructure

Actions (n_act = 5):
  0: escalate
  1: close_false_positive
  2: request_more_info
  3: apply_automated_response
  4: refer_to_analyst          ← added v5.0; domain-configurable confidence floor

Factors (d = 6):
  0: travel_match
  1: asset_criticality
  2: threat_intel_enrichment
  3: pattern_history
  4: time_anomaly
  5: device_trust

Bootstrap: 1,200 synthetic decisions (10 rounds × 6 categories × 4 original actions
× 6 samples), σ=0.08, seed=42. Converged=True, drift=0.0097.
NOTE: Bootstrap ran with 4 actions (refer_to_analyst was not in original bootstrap).
The refer_to_analyst centroid μ[c,4,:] was initialized to expert-specified values,
not from bootstrap averaging. Verify these values are correct for each category.

Key corrected prior (v5.0): credential_access/escalate centroid —
travel_match = 0.72 (was 0.30 in v4.5). Validated: P(escalate|high_travel) = 0.913 ✅
```

---

## 3. Claims Landscape

This section governs all external communications: demos, investor materials, outreach,
and customer conversations. The claims registry (claims_registry_v2) is the authoritative
reference. This section is the working summary.

### 3.1 Unconditional Claim (Safe to State Right Now, No Conditions)

> **CLAIM-31 — Operational Consistency:**
> "Every analyst on your team receives the same starting recommendation, from the same
> reasoning, every time — regardless of which analyst is reviewing the alert, what time
> of day it is, or how long they have been on shift."

This claim requires no experiments, no gate results, and no qualifications. It is true
at v5.0 and will remain true at all future versions. SOC analyst consistency studies
show agreement rates of 60–70% on identical alerts. GAE eliminates 30–40% inter-analyst
variance before any centroid learns anything. Use in every demo, all outreach, and
investor conversations without condition.

### 3.2 Available with Mandatory Qualifier

| Claim | Mandatory Qualifier | Risk if Omitted |
|---|---|---|
| "97.89% accuracy" | "Validated on centroidal synthetic data with oracle routing. Real-data routing accuracy unknown. ~20% of alert_type values currently misroute to default category (v5.0 — G-L1-1 pending v5.5-R6)." | Active misrepresentation risk. Forbidden until routing gap qualified. |
| "98.2% accuracy with learning" | Same as above, plus "warm-start with synthetic centroids." | Same |
| "Scales super-quadratically (b=2.11)" | "Simulation result (V1A). Real deployment trajectory uncharacterized — requires real SIEM data (v6.0)." | N/A for demo, but required in investor materials |
| "71.7% realistic accuracy" | "50-seed simulation, Bernoulli oracle, realistic FactorComputer noise. Not production measurement." | Low — this is the honest number, but qualifier prevents overinterpretation |
| "78.9% at 1,000 decisions" | Same as above. 95% CI: [78.1%, 79.6%]. | Same |
| "90.7% auto-approve accuracy at ≥0.90" | "50-seed simulation, 11.5% coverage at that threshold." | Misleading if coverage is not stated alongside accuracy |
| "System learns" | "In simulation. Real-data learning trajectory requires real SIEM data (v6.0)." | Oversell risk |

### 3.3 Forbidden Claims (v5.0 State)

Do not state any of the following until the named gate passes:

| Forbidden Claim | Gate That Unlocks It |
|---|---|
| Any routing accuracy percentage | GATE-R (runs after v5.5-R6 ships) |
| "97.89% accurate" without centroidal synthetic + routing gap qualifier | v5.5-R6 + GATE-R |
| "40% auto-approve coverage" | PROD-4 + v5.5-R1 ships |
| "System adjusts scoring based on current threat intelligence" | GATE-M passes |
| "Four feedback loops all validated" | GATE-V passes |
| "X% per-category accuracy with specific thresholds" | PROD-4 runs |
| "Compounding over time at your firm" without simulation qualifier | v6.0 first customer data |
| "IKS of N reflects N decisions worth of learning" | PROD-1 runs (κ* calibrated) |

### 3.4 Gate-by-Gate Claims Unlock Path

Each gate below unlocks specific new claims. Read math_synopsis_v7 §13 for the full
claims evolution roadmap. Summary:

| Gate | Prerequisite | Unlocks |
|---|---|---|
| GATE-R (run after v5.5-R6) | Alert_type mapping complete | FUTURE-01: routing accuracy % with 95% CI; composite claim derivation |
| FX-1-PROXY-REAL | CISA KEV + NVD APIs (public) | σ_max finalized; segmented accuracy estimates upgrade from INTERNAL ESTIMATE |
| PROD-1 (after IKS built) | v5.5 Phase 3 complete | FUTURE-18: IKS trajectory claim; IKS can ship with calibrated κ* |
| PROD-3 (run now) | v5.0 simulation pool | FUTURE-19: shadow mode expected agreement rate with 95% CI |
| PROD-4 (run now) | v5.0 ProfileScorer | FUTURE-12: 40%+ coverage at ≥85% per-category accuracy claim |
| GATE-M (after EXP-S2-REPRO all arms) | FX-1-PROXY-REAL + domain expert | σ activates in scoring pipeline OR display-only; "awareness intelligence" claim |
| GATE-D | EXP-S5a, S5b, S5, S6 pass | Live CISA KEV → σ update pipeline; ContextConnectors |
| GATE-V | EXP-S8 with real deployment | Full four-loop validated claim |

---

## 4. Pre-Sprint Closure — Ordered Execution Sequence

This section answers: **"What must be done before the first v5.5 sprint prompt runs?"**

Pre-sprint work falls into three categories:

- **Category A — Design Documents:** Write before specific sprint prompts. No code. No
  experiments. Design reasoning. Typically 1–3 hours each.

- **Category B — Now-Executable Experiments:** Use v5.0 simulation infrastructure only.
  No v5.5 features needed. Run immediately. Their results are either inputs to sprint
  prompt design or calibration tables shipped with v5.5 features.

- **Category C — Mid-Sprint Experiments:** Triggered by a specific sprint phase
  completing. Run immediately after the triggering item ships — do not batch these.

### 4.1 Category A: Design Documents to Write

#### A-1: soc_copilot_design_v5_4 §17.5 — Rollback Execution Semantics

**Priority:** HIGHEST. Write this first, before any other pre-sprint work.
**Blocks:** ARCH-3 (hook reliability failure test protocol), TD-033 sprint prompt
(v5.5 Phase 4 checkpoint/rollback implementation).
**Status:** NOT YET WRITTEN. The section number is reserved but the content does not exist.

What §17.5 must specify:

```
1. Trigger conditions (three categories):
   a. Automatic trigger: P_max(recent N decisions) < 0.55 for N consecutive
      decisions in the same category. Default N = 10. Configurable in
      CalibrationProfile.
   b. Consistency failure: ‖μ[c,a,:](t) − μ[c,a,:](checkpoint)‖₂ >
      S4_bound[c] in any 50-decision window. S4_bound pending PROD-1b derivation
      (target: per-cell drift causing 2pp accuracy degradation). Placeholder: 0.30.
   c. Manual trigger: POST /api/soc/rollback called by CISO or SOC architect.
      Requires: operator_id, target_checkpoint_id, reason_code.

2. Rollback-and-resume semantics:
   a. Rollback: replace μ (centroids) with the ProfileSnapshot at
      target_checkpoint_id. Emit CENTROID_ROLLED_BACK event to audit log with:
      target_checkpoint_id, decision_count_at_checkpoint, decision_count_at_trigger,
      trigger_reason, operator_id.
   b. Centroid write access during rollback: LOCKED. No updates until resume.
   c. Resume: manual only. POST /api/soc/resume-learning. Requires explicit
      acknowledgment from operator who triggered rollback. Emits LEARNING_RESUMED.
   d. Decisions scored during rollback window: scored against rolled-back centroids.
      These decisions are NOT written as OutcomeRecords (no learning from the
      post-trigger degraded window).
   e. Alert to Neo4j: rollback event written as a RollbackEvent node, linked to
      the affected ProfileSnapshot nodes (pre and post).

3. Hook 2 / Hook 3 interaction:
   a. Hook 2 (OutcomeRecord): suspended from trigger to resume. All
      ProfileScorer.update() calls during the frozen window log a
      SKIPPED_ROLLBACK_FROZEN record without modifying centroids.
   b. Hook 3 (ProfileSnapshot): continues every 50 scored decisions.
      Snapshots during frozen window carry frozen=True flag. These snapshots
      record the centroid state (frozen) plus the decision count, so drift
      during the frozen window is observable.
   c. When learning resumes: the first ProfileSnapshot after LEARNING_RESUMED
      carries resumed=True, post_rollback=True. This is the new drift baseline.

4. What rollback does NOT do:
   - Does NOT delete DecisionRecords (routing accuracy data is permanent).
   - Does NOT delete OutcomeRecords written before the trigger (compounding
     history is permanent).
   - Does NOT affect the scoring pipeline — recommendations continue.
   - Does NOT affect σ (synthesis bias). Rollback is centroid-only (μ only).
   - Does NOT change the checkpoint schedule.

5. Checkpoint schedule (TD-033):
   ProfileSnapshot written every 50 decisions (existing Hook 3).
   Retention: last 20 checkpoints (1,000 decisions of history). Configurable.
   Oldest checkpoint purged when limit reached.
   Export: GET /api/soc/checkpoints returns list with checkpoint_id,
   decision_count, created_at, centroid_drift_since_prior.
```

**Acceptance:** §17.5 exists in soc_copilot_design_v5_4. ARCH-3 failure test protocol
can be completed. TD-033 sprint prompt can be written against this spec.

---

#### A-2: soc_copilot_design_v5_4 §23.5 — LLM Judge Rubric for NL Template Quality

**Priority:** HIGH. Must exist before v5.5 Phase 2 (T1-1) acceptance criterion is
written and before the sprint prompt is executed.
**Blocks:** T1-1 acceptance criterion (the "LLM judge rubric must be specified" gate
in soc_copilot_design_v5_4 §4.2).
**Status:** Written in issue_calibration_table.md as a design change. Needs to be
formalized as a section in soc_copilot_design_v5_4.
**No experiment prerequisites.** Can be written now.

What §23.5 must specify:

```
Study design:
  N = 5 SOC analysts (or proxy: 5 sessions with domain-expert review)
  M = 10 centroid-template pairs
  Total judgments: 50

Per judgment (analyst receives centroid NL template + 3 test alerts):
  1. Rate template quality on 4 criteria:
     a. Factual Accuracy (does it correctly describe the centroid?): 1–5, ≥4.0 required
     b. Specificity (does it name a real entity — user, asset, IOC, alert type?): 1–5, ≥3.5
     c. Actionability (is the recommended action clear from the text?): 1–5, ≥3.5
     d. Non-Redundancy (no tautological phrases like "this is a security alert"): 1–5, ≥3.0
  2. Predict system action on 3 presented alerts.
     Interpretation accuracy = fraction of correct predictions.
     Gate: ≥70% across all 50 pairs.

Template selection for the 10-pair study:
  Include at least 2 templates per category. Include at least 1 borderline case
  (centroid near-equal between two actions).

Output file: tests/nl_template_judge_results.json
  {
    "centroid_id": "credential_access__escalate",
    "analyst_id": "A001",   // anonymized
    "criteria_scores": [4, 4, 3, 4],
    "interpretation_accuracy": 0.67,
    "raw_predictions": [...]
  }

Aggregate pass criteria:
  Mean Factual Accuracy ≥ 4.0 across all 50 judgments.
  Mean Interpretation Accuracy ≥ 70%.
  If either fails: flag template format for revision.

What to do if criteria fail:
  Factual Accuracy < 4.0: centroid value mapping is wrong or template variable
    substitution is incorrect. Audit the template → factor_value → text logic.
  Specificity < 3.5: templates are using generic phrases. Add more entity
    resolution calls to Neo4j (user name, asset name, IOC value).
  Interpretation Accuracy < 70%: template is ambiguous about the action threshold.
    Add explicit confidence language ("system recommends escalation with 89% confidence
    — above the 85% threshold for this category").
```

**Acceptance:** §23.5 exists in soc_copilot_design_v5_4. T1-1 sprint prompt acceptance
criterion can be written.

---

#### A-3: soc_copilot_design_v5_4 §23.4 — Similar Past Cases Similarity Spec

**Priority:** HIGH. Required before T1-1 sidebar implementation.
**Blocks:** T1-1 "similar past cases" sidebar in v5.5 Phase 2.
**Status:** Defined in issue_calibration_table.md as a design change. Needs formalization
as a section in soc_copilot_design_v5_4.
**Prerequisite: PROD-3 must run first.** The similarity threshold is derived from the
cosine distance distribution over the simulation pool. Do not pre-specify it.

What §23.4 must specify (finalize after PROD-3 runs):

```
Feature: "Similar Past Cases" sidebar on Tab 3 alert detail.

Query: Given current alert with factor vector f ∈ [0,1]^6 and category c:
  1. Retrieve all DecisionRecords with category == c from Neo4j.
  2. For each DecisionRecord with factor_vector f_i:
     similarity(f, f_i) = cosine_similarity(f, f_i) = (f · f_i) / (‖f‖ · ‖f_i‖)
  3. Filter to similarity ≥ θ (threshold — derive from PROD-3 below).
  4. Sort by similarity descending, then by recency descending.
  5. Return top k = 3.
  6. If fewer than min_prior = 5 DecisionRecords in this category: suppress sidebar
     (show "Not enough prior decisions in this category yet").

Similarity threshold θ:
  From PROD-3 output: compute the distribution of cosine similarities between all
  pairs of factor vectors in the simulation pool, within the same category.
  Set θ = p25 of this distribution (25th percentile — "bottom quartile of similar
  pairs"). Rationale: we want the top-3 results to be meaningfully similar, not
  just the least dissimilar available. Recompute per category if distributions differ
  significantly across categories. Log the per-category θ values in
  soc_copilot_design_v5_4 §23.4.1 after PROD-3 completes.

Display per matched case:
  - Action taken (escalate / close / etc.)
  - Confidence at time of decision
  - Whether outcome was verified and what it was (if available)
  - Similarity score (shown as percentage)
  - Time elapsed since decision ("3 days ago")
  - Anonymized: do not show original analyst ID

Performance SLA:
  Sidebar query must complete in < 200ms P95 given N < 10,000 DecisionRecords.
  For N > 10,000: index factor_vector by category, limit scan to last 500 decisions
  in category. PERF-3 will verify this.
```

**Acceptance:** §23.4 exists with θ values from PROD-3. T1-1 implementation can proceed.

---

### 4.2 Category B: Now-Executable Experiments

These experiments need only the v5.0 simulation pool. Run them before starting
the sprint. Their outputs change what specific sprint prompts build or ship.

---

#### B-1: PROD-3 — Shadow Mode Agreement Rate Baseline

**Run in:** cross-graph-experiments
**Location:** `experiments/prod/prod3_shadow_baseline/`
**Prompt status:** ✅ Full prompt in experiments_catalog_v8 Part 3 §14
**Compute:** Local (~30 min)
**Prerequisites:** v5.0 ProfileScorer (done)

**Why now:** Two outputs needed before sprint:
1. Calibration table for shadow mode documentation — first customers need to know
   what agreement rate to expect before their data looks "normal." Without this,
   the shadow report from the first customer is uninterpretable.
2. Cosine distance distribution over simulation pool — needed to set the similarity
   threshold θ in §23.4 (similar past cases). Without PROD-3, §23.4 cannot be finalized.

**Expected output:**
```
=== SHADOW MODE CALIBRATION TABLE (v5.5) ===
Overall agreement rate: [X%] ± [Y%] [CI_low, CI_high] (50 seeds)
Per-category:
  credential_access: [X%]
  lateral_movement: [X%]
  insider_threat: [X%]
  data_exfiltration: [X%]
  cloud_infrastructure: [X%]
At P≥0.90: agreement=[X%], coverage=[Y%]
```

**Gate:** Calibration (no pass/fail). Required before shadow mode ships.

**Claude Code Prompt:** See experiments_catalog_v8 Part 3 §14 (PROD-3 section).
Execute it verbatim. Parameters: N_seeds=50, N_warmup=200, N_shadow=200, τ=0.1,
noise_rate=0.10, confidence_thresholds=[0.5, 0.6, 0.7, 0.8, 0.9].

---

#### B-2: PROD-4 — Per-Category Auto-Approve Threshold Calibration

**Run in:** cross-graph-experiments
**Location:** `experiments/prod/prod4_threshold_calibration/`
**Prompt status:** ✅ Full prompt in experiments_catalog_v8 Part 3 §14
**Compute:** Local (~2 hrs — 50 seeds × 1,000 decisions × 50 threshold sweep values)
**Prerequisites:** v5.0 ProfileScorer (done)

**Why now:** Without PROD-4, the v5.5-R1 sprint prompt ships with design-estimate
thresholds (the table in product_strategy_v2 Part 8 §v5.5-R1 gives starting values
that are explicitly labeled as "proposed"). The correct thresholds come from measured
accuracy-vs-confidence curves. Running PROD-4 before the sprint means the threshold
table in the sprint prompt has real numbers, not estimates.

Also: the confidence floor for refer_to_analyst (designed at 0.70, labeled "design
estimate — pending PROD-4" in multiple documents) is validated or replaced.

**Expected output:**
```
Per-category recommendation table:
  credential_access:    threshold* = [X],  accuracy = [Y%],  coverage = [Z%]
  lateral_movement:     threshold* = [X],  accuracy = [Y%],  coverage = [Z%]
  insider_threat:       threshold* = [X],  accuracy = [Y%],  coverage = [Z%]
  data_exfiltration:    threshold* = [X],  accuracy = [Y%],  coverage = [Z%]
  cloud_infrastructure: threshold* = [X],  accuracy = [Y%],  coverage = [Z%]
Gate verdict: N/5 categories achieve threshold* <= 0.75
```

**Gate:** ≥3/5 categories achieve threshold*(c) ≤ 0.75 (coverage ≥ 30% at ≥85%
accuracy). If < 3 categories pass: per-category thresholds ship with honest labels
("below threshold in [N] categories — IKS-gated auto-approve strategy recommended
for those categories"). Do not block the sprint for a PROD-4 gate failure — just
adjust what the v5.5-R1 prompt builds.

**Claude Code Prompt:** See experiments_catalog_v8 Part 3 §14 (PROD-4 section).
Execute it verbatim.

---

#### B-3: FX-1-PROXY-REAL — Realistic L2 Margin Distribution

**Run in:** cross-graph-experiments
**Location:** `experiments/expFX1_proxy_real/`
**Prompt status:** ✅ Full prompt in experiments_catalog_v8 Part 2 §7
**Compute:** Local, public APIs (CISA KEV + NVD)
**Prerequisites:** Internet access to CISA KEV and NVD APIs

**Why now:** Two outputs are needed for the synthesis layer design:
1. σ_max empirical value. The synthesis safety architecture (math_synopsis_v7 §9) states
   σ_max = p10 of empirical L2 margin distribution. The current design uses σ_max = 1.0
   as a placeholder. The correct value is derived from the p10 of the distribution of
   ‖f − μ[c,a*,:]‖² − ‖f − μ[c,a,:]‖² across realistic (c, a) pairs. Without this,
   EXP-S2-REPRO Arm A cannot correctly parameterize the σ injection.
2. Segmented accuracy estimates upgrade from INTERNAL ESTIMATE to measured ranges
   (still with "simulated" qualifier, but from real factor distributions).

**Expected output:**
- L2 margin distribution plots (paper_figures/)
- σ_max candidate: p10 of margin distribution
- activation_threshold candidate: confidence level at which σ effect is meaningful
- Update soc_copilot_design_v5_4 §9 σ_max with the empirically derived value
  immediately after this experiment completes.

**Gate:** Characterization (no pass/fail). Required before EXP-S2-REPRO Arm A executes.

---

#### B-4: EXP-S2-REPRO Arm 0 — Cold-Start Replication Check

**Run in:** cross-graph-experiments
**Location:** `experiments/synthesis/expS2_repro/`
**Prompt status:** ✅ Full prompt in experiments_catalog_v8 Part 2 §7
**Compute:** Local
**Prerequisites:** None beyond v5.0

**Why this arm first:** Arm 0 verifies that the original EXP-S2 result (poisoning ≤ 2pp
at 20% bad claims at centroidal AUAC) is reproducible with the current codebase and
v5.0 ProfileScorer. If Arm 0 does not reproduce the original result, something in the
v5.0 codebase has changed the behavior. Fix before proceeding to Arms A and B.

**Three-arm design (full EXP-S2-REPRO):**

| Arm | Condition | Gate Contribution | Prerequisite |
|---|---|---|---|
| Arm 0 | Cold-start replication (λ=0.5, Loop 2 OFF, centroidal AUAC) | Reproducibility check | None — run now |
| Arm A | Production condition (λ=0.5, Loop 2 ON, centroidal AUAC) | GATE-M co-gate primary | σ_max from FX-1-PROXY-REAL |
| Arm B | Realistic-AUAC baseline (λ=0.5, Loop 2 ON, realistic 50-seed) | GATE-M co-gate secondary | Arm A passed + domain expert review |

**Execution rule:** Run Arm 0. If it passes (≤ 2pp degradation at 20% poison):
run FX-1-PROXY-REAL in parallel, then run Arm A. Then run Arm B.
If Arm 0 fails: STOP. Diagnose before proceeding. Do not run Arm A or B until
the Arm 0 discrepancy is understood.

**Gate for Arm B:** Open gate. Arm B result requires domain expert review before
pass/fail is declared for GATE-M. The question domain expert must answer:
"Is the poisoning level in Arm B (realistic AUAC, Loop 2 running) acceptable for
the enterprise security context?" — this is a judgment call, not a threshold.

---

### 4.3 Category C: Mid-Sprint Experiments

These experiments cannot run before the sprint because they depend on v5.5 features.
Run them immediately when the triggering feature ships — do not defer.

| Experiment | Trigger | What It Produces | What Happens If Deferred |
|---|---|---|---|
| **GATE-R** | v5.5 Phase 1 complete (R6 routing fix ships) | Routing accuracy % with 95% CI | Cannot state composite accuracy; CLAIM-01 misrepresentation risk persists |
| **PROD-1** | v5.5 Phase 3 complete (IKS feature built) | Calibrated κ* for IKS formula | IKS ships with 0.30 normalization placeholder — risk of always-near-zero IKS |
| **ARCH-3** | §17.5 written + v5.5 Phase 4 complete (shadow mode + TD-033) | Hook reliability in rollback scenario | Shadow mode ships without failure-mode safety verification |
| **EXP-S2-REPRO Arms A+B** | FX-1-PROXY-REAL complete | GATE-M co-gate input | GATE-M cannot be formally declared without all 3 arms |
| **PROD-2** | NL template engine built + analyst cohort confirmed | Analyst interpretation accuracy study | FUTURE-13 claim remains unavailable; template quality unverified |

**GATE-R execution rule:** The GATE-R prompt is staged and ready. Do NOT execute it
against the v5.0 incomplete routing mapping. Execute it the moment Phase 1 of the
v5.5 sprint ships and the routing mapping table is verified complete.

**PROD-1 execution rule:** Run PROD-1 immediately when IKS is built (Phase 3 of v5.5
sprint). Check the κ* result. If IKS(200) is outside [15, 40] in ≥90% seeds,
recalibrate the normalization constant (κ parameter) before shipping v5.5-R4.
Do not ship IKS with the design default 0.30 normalization constant without running
this experiment first.

---

### 4.4 Master Execution State Table

This is the single source of truth for pre-sprint status. Update this table as items
complete. When starting a new session, find the first row without ✅ and execute it.

| Step | Action | Type | Unblocks | Timing | Status |
|---|---|---|---|---|---|
| **0a** | Write §17.5 rollback execution semantics in soc_copilot_design_v5_4 | Design doc | ARCH-3, TD-033 sprint prompt (Phase 4) | Before Phase 4 of sprint | ✅ DONE (Mar 11 — soc_copilot_design_v5_4_part1.md §17.5) |
| **0b** | Write §23.5 NL judge rubric for template quality in soc_copilot_design_v5_4 | Design doc | T1-1 acceptance criterion (Phase 2) | Before Phase 2 of sprint | ✅ DONE (Mar 11 — soc_copilot_design_v5_4_part1.md §23.5) |
| **0c** | GAE-WIRING-1: CentroidUpdate dataclass + update() return type + freeze()/unfreeze() | Code (GAE) | SOC WIRING-1 import | Pre-VIS-2 | ✅ DONE (Mar 12 — 246 GAE tests passing; pushed origin v5.0-dev) |
| **0d** | SOC WIRING-1: centroid_delta_norm wiring + IKS service + μ₀ sidecar bootstrap | Code (SOC) | VIS-2 live data | Pre-VIS-2 | ✅ DONE (Mar 12 — IKS as module-level functions; iks_bootstrap_soc.json shape=[6,4,6]) |
| **0e** | VIS-2: Tab-2/Tab-3/Tab-4 redesign + centroid-evolution + learning-state endpoints | Code (SOC) | Visual validation complete | Pre-sprint | ✅ DONE (Mar 12 — all tabs confirmed live; category convergence working; bridge link working) |
| **1** | Run PROD-3 (shadow mode baseline) | Experiment | §23.4 θ threshold; shadow mode calibration table | Now — no prereqs | ✅ DONE March 14. Overall 71.9% [71.1%, 72.7%]. Per-category θ: cred=0.787, TI=0.745, lat=0.809, exfil=0.772, insider=0.792, cloud=0.744. §23.4 updated. |
| **2** | Run PROD-4 (per-category threshold calibration) | Experiment | v5.5-R1 threshold values; 5th action confidence floor | Now — no prereqs | ✅ DONE March 14-15 (3 runs). PROD-4 original (η_neg=1.0): INVALID — catastrophic miscalibration. PROD-4b: η_neg=0.05 canonical (ECE=0.026). PROD-4 final (η_neg=0.05): all 6 categories ≥85% accuracy. threshold* range 0.720–0.870. PROD-4b refer floors: cred=0.93, TI=0.95, lat=0.97, exfil=0.95, insider=0.96, cloud=0.95. |
| **3** | Run FX-1-PROXY-REAL (realistic L2 margins) | Experiment | σ_max empirical value; EXP-S2-REPRO Arm A parameterization | Now — public APIs | 🔲 NOT DONE |
| **4** | Write §23.4 similar past cases spec (uses PROD-3 θ) | Design doc | T1-1 sidebar (Phase 2) | θ placeholder (0.85) used; update after PROD-3 | ✅ DONE (Mar 11 — soc_copilot_design_v5_4_part1.md §23.4; θ=0.85 placeholder, PROD-3-calibration-needed TODOs in place) |
| **5** | Run EXP-S2-REPRO Arm 0 (replication check) | Experiment | Arm A eligibility | Now — no prereqs | 🔲 NOT DONE |
| **6** | Run EXP-S2-REPRO Arm A (operative λ, Loop 2 ON) | Experiment | GATE-M co-gate primary | After Steps 3+5 | 🔄 BLOCKED (wait for Steps 3, 5) |
| **7** | Run EXP-S2-REPRO Arm B (realistic-AUAC) + domain expert review | Experiment | GATE-M formal declaration | After Step 6 | 🔄 BLOCKED (wait for Step 6) |
| — | **BEGIN v5.5 SPRINT** (Part 2) | — | — | After Steps 1, 2, 3 complete (0a–0e, 4 ✅) | — |
| **S1** | Sprint Phase 1: R6 routing fix + G-L2-3 + G-L4-2 | Code | GATE-R; correct routing for all downstream | First in sprint | 🔲 NOT STARTED |
| **S2** | Run GATE-R immediately after Phase 1 ships | Experiment | FUTURE-01: composite accuracy claim | After S1 | 🔄 BLOCKED (wait for S1) |
| **S3** | Sprint Phase 2: T1-1 NL template engine | Code | Demo Q1 answerable | After Steps 1+2+3 (design prereqs ✅) | 🔄 BLOCKED (wait for PROD-3, PROD-4, FX-1-PROXY-REAL) |
| **S4** | Sprint Phase 3: IKS + Chart A correction | Code | Demo Q2 answerable | After Phase 2 | — |
| **S5** | Run PROD-1 (IKS κ* calibration) immediately after Phase 3 | Experiment | IKS ships with calibrated κ* | After S4 | 🔄 BLOCKED (wait for S4) |
| **S6** | Sprint Phase 4: Shadow Mode + TD-033 checkpoint/rollback | Code | Demo Q3/Q4; ARCH-3 | After Step 1 (PROD-3 result in docs; §17.5 ✅ Mar 11) | 🔲 READY once PROD-3 done |
| **S7** | Sprint Phase 5: Auto-approve + graduated review + 5th action | Code | Demo Q3 analyst relief | After Step 2 (PROD-4 result in sprint prompt) | 🔄 REDESIGNED — see Part 2 Phase 5 |
| **CORR-1a** | Routing fix — ALERT_TYPE_CATEGORY_MAP (20 entries) + resolve_alert_category() | Code (SOC) | Correct routing for all downstream; 68% misroute eliminated | Done March 14 | ✅ DONE March 14. 78→111 SOC tests. |
| **Ontology** | C=6 verified (not 5), A=5, tensor (6,5,6)=180. Healthcare removed. τ=0.25 bug fixed. | Verification | Category names corrected in all docs | Done March 14 | ✅ DONE March 14. |
| **η_neg** | η_neg design decision: 0.05 canonical; 1.0 FORBIDDEN (ECE=0.49). 20:1 asymmetry in consequence weighting, not learning rates. | Design decision | All experiments use 0.05. PROD-4 original results INVALID. | Settled March 14-15 | ✅ SETTLED March 14-15. |
| **SHIFT-1** | Frozen vs learned diagnostic. Learning negative at all 15 conditions. Triggered bug investigation. | Experiment | Root cause found | March 15 | ✅ DONE March 15. |
| **SHIFT-2** | Rigorous update() bug verification. Pre-fix: -9% lift at noise=0. Post-fix: +2.7% (δ=0.10, w=1000). | Experiment | Bug confirmed and fixed. | March 15 | ✅ DONE March 15. 24 conditions × 50 seeds. |
| **DISC-1** | Composite discriminant on frozen scorer. Model E (13 features): 70.4% coverage at 85% precision vs 62.6% confidence-only (+7.8pp). rolling_accuracy strongest orthogonal signal (coef=5.06). IKS v2 validated. | Experiment | Phase 5 redesign input | March 15 | ✅ DONE March 15. |
| **BUG-FIX** | ProfileScorer.update() bug: correct=False pushed ALL centroids (incl. GT). Fixed: push predicted, pull GT. | Code (GAE) | Learning works. 246→251 GAE tests. | March 15 | ✅ DONE March 15. |
| **S8** | Sprint Phases 6-9 | Code | Demo Q5; deployment; compliance | See Part 2 | — |

**Parallel execution rules:**
- Steps 0a and 0b can be written in parallel.
- Steps 1, 2, 3, 5 can ALL run in parallel. None blocks the other.
- Step 4 requires Step 1 (PROD-3 result). All other design docs can proceed.
- The v5.5 sprint can START with Phase 1 (S1) the moment Steps 0a–4 are done.
  Phases 3, 4, 5 in the sprint may begin before all pre-sprint items complete,
  as long as their specific blocking items are done (see "Blocked (wait for)"
  column for each sprint step).

---

## 5. Completed Work

### Code Releases

| Version | Key Deliverables |
|---|---|
| v2.0–v3.2 | Core platform, alert ingestion, Neo4j connectors, tab UI |
| v4.0 | Real connectors + GAE data pipeline |
| v4.1 | GAE foundation: 9 modules, 187 tests, Opus-reviewed architecture |
| v4.5 | CalibrationProfile, simulation pool, NL narratives, healthcare domain, audit trail |
| **v5.0** | ProfileScorer (TD-027), τ=0.1 (TD-030), refer_to_analyst action (n_act=5), Hook 1/2/3 write obligations, realistic 50-seed suite, OracleProvider, eval framework, ci-platform extraction (Phases 8–9). 243 GAE tests, 78 SOC tests. |
| **v5.0 post-tag (Mar 12)** | GAE-WIRING-1: CentroidUpdate dataclass, update() return type, freeze()/unfreeze(), 246 GAE tests. SOC WIRING-1: centroid_delta_norm wiring, IKS service (module-level functions), μ₀ sidecar bootstrap. VIS-2: Tab-2 full redesign (IKS summary panel, Section A–D, left-rail navigator), Tab-3 centroid delta + bridge link, Tab-4 Loop 2 two-mechanism copy. New endpoints: GET /api/soc/centroid-evolution, GET /api/soc/learning-state. Fixes: cat_0 category name, shape mismatch ×2, bridge link CSS, hardcoded ALERT-7823 moved to domain.ts. |
| **v5.0 post-tag (Mar 14-15)** | CORR-1a: ALERT_TYPE_CATEGORY_MAP 20 entries + resolve_alert_category(). Ontology verified C=6 A=5. Healthcare removed. PROD-3/4/4b complete. η_neg=0.05 settled. ProfileScorer.update() bug fixed (gt_action_index dual push/pull). 78→111 SOC tests, 246→251 GAE tests. soc_copilot_design_v5_4 updated to v5.6. gae_design updated to v9.2. math_synopsis updated to v9.0. SHIFT-1/2/DISC-1 experiments complete (34 total). |
| **Writing (Mar 12 session 2)** | compounding_intelligence_v7 Parts 1/2/3 (~11,800 words, supersedes v6). CI v7 gap analysis (9 content gaps, 4 impact gaps). All 9 gaps fixed in-session. Document update priority list (14 documents, 4 priorities). |

### Bridge + Validation Experiments (25 Complete)

| Experiment | Result | Key Number |
|---|---|---|
| EXP-5 | PASS — GT-aligned oracle resolves cold-start | 79.65% |
| EXP-A | G FALSIFIED — shared W architecture falsified | 49.27% |
| EXP-A2 | Per-category W improvement negligible | 51.61% |
| EXP-C1 | ProfileScorer L2 zero-learning PASS | **97.89%** |
| EXP-B1 | ProfileScorer with learning PASS | **98.2%** |
| EXP-D1 | Cross-category transfer marginal | Config wins 2–14pp |
| EXP-D2 | No significant factor interactions | 75 pairs tested |
| EXP-E1 | L2 wins 2/3 kernel comparisons | Pluggable |
| EXP-E2 | Scales to 20×10×20 | 99.9% |
| V1A | Domain scaling exponent confirmed | **b=2.11, R²=0.9999** |
| V1B | Norm explosion without LayerNorm | Required for d > 6 |
| V2 | Centroid escape → clipping required | [0,1] enforced |
| V3A | L2 beats ML baselines | 94.78% vs XGBoost 92.24% |
| V3B | Calibration at τ=0.1 | **ECE=0.036** (vs 0.19 at τ=0.25) |
| GATE-G | G matrix architecture obsolete | ProfileScorer confirmed |
| GATE-OP | λ=0.5 operative window confirmed | p=0.0008 at centroidal AUAC |
| EXP-OP1 | T_recovery survival — N=20 seeds | Preliminary — EXP-OP2-N100 needed |
| EXP-OP2 | Never-recover rate (N=20) | 35% CI too wide — EXP-OP2-N100 needed |
| EXP-OP3 (planned) | — | Blocked by TD-033 |
| EXP-OP4 (planned) | — | Cost-weight metric pending |
| 50-seed simulation | Realistic accuracy suite | 71.7% / 78.9% / 90.7% |
| PROD-3 | Per-category θ values from cosine distance distribution | 0.744–0.809 per category |
| PROD-4b | η_neg calibration diagnostic | η_neg=0.05 ECE=0.026; η_neg=1.0 ECE=0.49 |
| PROD-4 final | Per-category threshold* at η_neg=0.05 | threshold* 0.720–0.870; all 6 ≥85% |
| SHIFT-1 | Frozen vs learned learning diagnostic | Learning negative pre-fix; triggered bug hunt |
| SHIFT-2 | Update rule verification (pre/post fix) | Pre-fix -9.0% → post-fix +2.7% (δ=0.10, w=1000) |
| DISC-1 | Composite discriminant on frozen scorer | 70.4% coverage vs 62.6% (+7.8pp at 85% precision) |

### 50-Seed Validated Product Numbers (Canonical — Never Mix With Centroidal Numbers)

| Metric | Value | 95% CI |
|---|---|---|
| Static realistic accuracy | 71.7% | [71.4%, 71.9%] |
| Learning @ 1,000 decisions | 78.9% | [78.1%, 79.6%] |
| credential_access @ 1,000 decisions | 68.0% | [66.7%, 69.1%] |
| Auto-approve accuracy (≥0.90 global) | 90.7% | [90.1%, 91.2%] |
| Auto-approve coverage (≥0.90 global) | 11.5% | ±0.70% |

**Architecture validation numbers (separate regime — always qualify):**

| Metric | Value | Experiment |
|---|---|---|
| L2 zero-learning accuracy | 97.89% | EXP-C1 (centroidal synthetic) |
| L2 with-learning accuracy | 98.2% | EXP-B1 (centroidal synthetic) |
| ECE at τ=0.1 | 0.036 | V3B (centroidal synthetic) |

---

## 6. Pending Experiments by Timing Band

### 6.1 Now-Executable (No Sprint Prerequisites)

| Experiment | Location | Prompt | Expected Output | Unblocks |
|---|---|---|---|---|
| PROD-3 (shadow baseline) | `experiments/prod/prod3_shadow_baseline/` | ✅ DONE March 14 | Per-category θ values in soc_copilot_design §23.4.1 | ✅ COMPLETE |
| PROD-4 (threshold calibration) | `experiments/prod/prod4_threshold_calibration/` | ✅ DONE March 14-15 (3 runs) | threshold*(c) values in soc_copilot_design §10.6-R1; refer floors in §10.6-R11 | ✅ COMPLETE |
| FX-1-PROXY-REAL (L2 margins) | `experiments/expFX1_proxy_real/` | ✅ Full — catalog Part 2 §7 | σ_max empirical; segmented accuracy | EXP-S2-REPRO Arm A |
| EXP-S2-REPRO Arm 0 (replication) | `experiments/synthesis/expS2_repro/` | ✅ Full — catalog Part 2 §7 | Reproducibility confirmed | Arm A eligibility |
| EXP-OP2-N100 (never-recover N=100) | `experiments/synthesis/expOP2_n100/` | ✅ Full — catalog Part 2 §7 | Never-recover CI with N=100 seeds | Safety policy update |
| ARCH-1 (import boundary) | GAE repo | ✅ Full — catalog Part 2 §12 | Import boundary compliance | Architecture hygiene |
| ARCH-4 (centroid portability) | GAE repo | ✅ Full — catalog Part 2 §12 | Tensor export/import round-trip | Deployment story |
| PERF-1 (ProfileScorer latency) | GAE repo | ✅ Full — catalog Part 2 §13 | P95 latency < 1ms gate | Hosted product SLA |
| GE1–GE4 (factor scaling) | cross-graph-experiments | ✅ Full — catalog Part 2 §10 | Factor dimensionality guidance | v6.0 design |

### 6.2 Mid-Sprint (Triggered by Specific Feature Shipping)

| Experiment | Trigger Event | Prompt | Gate/Output |
|---|---|---|---|
| GATE-R | v5.5-R6 routing fix ships (Phase 1) | ✅ Staged — catalog Part 2 §7 | FUTURE-01: routing accuracy % with 95% CI |
| PROD-1 | IKS feature built (Phase 3) | 🔧 Spec ready — catalog Part 3 §14 | κ* for IKS normalization |
| ARCH-3 | §17.5 written + TD-033 ships (Phase 4) | 🔧 Blocked by §17.5 | Hook reliability in rollback scenario |
| ARCH-5 | Shadow mode ships (Phase 4) | 📐 Partial | Shadow mode synthetic baseline |
| EXP-S2-REPRO Arm A | FX-1-PROXY-REAL complete + Arm 0 passes | ✅ Full (in Arm 0 prompt) | GATE-M co-gate primary |
| EXP-S2-REPRO Arm B | Arm A complete | ✅ Full (in Arm 0 prompt) | GATE-M co-gate secondary (domain expert) |
| PERF-2 | Neo4j live (v5.5 deployment) | 🔧 Spec ready | Concurrent FactorComputer SLA |
| PERF-3 | NL template engine built | 🔧 Spec ready | Factor computation bottleneck |

### 6.3 Post-Sprint / Requires Partner (v6.0 Window)

| Experiment | Prerequisite | Gate |
|---|---|---|
| FX-1 (real SOC data) | SOC partner with SIEM access | Real-data centroid distribution; τ recalibration |
| **EXP-S1** (does σ improve accuracy?) | FX-1-PROXY-REAL + v5.0 simulation pool | GATE-M: Δ_accuracy ≥ 3pp, p < 0.0083, ECE ≤ +0.02 |
| **EXP-S3** (σ contaminates μ?) | v5.0 simulation pool | GATE-M: centroid divergence ≤ 5% |
| **EXP-S4** (λ sensitivity plateau) | v5.0 simulation pool | GATE-M: plateau ≥ 0.05 wide |
| PROD-2 (NL template analyst study) | NL template built + analyst cohort confirmed | FUTURE-13 claim; template revision triggers |
| PROD-5 (convergence rate + onboarding timeline) | v5.5 SEED-2 realistic pool built | FUTURE-20: onboarding calendar claim |
| EXP-S5a (CISA KEV → σ) | v5.5 source connector infrastructure | GATE-D-early |
| EXP-S5b (work artifact extraction) | ContextConnector built | GATE-D-early |
| EXP-S5 (full synthesis pipeline) | v6.0 soc-copilot | GATE-D |
| EXP-S6 (INTSUM briefing quality) | v6.0 Tab 5 Panel A | GATE-D |
| EXP-S7 (Ask-the-Graph 3-condition) | v5.0 baseline + v6.0 Panel B | GATE-D |
| EXP-S8 (synthesis vs real decisions) | First production customer + deployment | GATE-V |
| EXP-G1 (γ validation) | Level 2/3 pipeline + longitudinal data | γ claim |
| FX-2 through FX-8 | Varies — see catalog Part 2 §7 | Varies |

> **GATE-M requires all four conditions:** EXP-S2-REPRO (all arms, including Arm B
> domain expert review), EXP-S1 (Δ ≥ 3pp, p < 0.0083), EXP-S3 (≤ 5% divergence),
> EXP-S4 (λ plateau ≥ 0.05 wide). All four must pass. Any single failure → σ is
> display-only, not live in scoring pipeline. Tab 5 has value at every GATE-M outcome.

---

## 7. Features F1–F15 (Updated Status)

| ID | Feature | Impact | Target | Status |
|---|---|---|---|---|
| **F1** | **Shadow Mode** | ★★★★★ | v5.5 | 🔧 Designed (soc_copilot_design_v5_4 §17) |
| F2 | Detection Engineering Feedback | ★★★★☆ | v5.0 ✅ | ✅ Done (F2-DESIGN prompt complete) |
| **F3** | **EU AI Act Compliance Evidence** | ★★★★★ | v5.5 | 🔧 Designed — August 2026 deadline |
| F4 | Operational Outcome Metrics | ★★★★★ | v5.0 ✅ | ✅ Done (F4-OVERLAY prompt complete) |
| F5 | Multi-SIEM | ★★★★★ | v6.0 | 🔧 Designed — extends F11-A (v5.0 SourceConnector) |
| F6 | Attack Chain Correlation (Blast Radius) | ★★★★☆ | v6.0 | 🔧 Designed |
| F7 | NHI Behavioral Baseline | ★★★★☆ | v6.5 | 📐 Partial |
| F8 | Cross-Tenant Meta-Intelligence | ★★☆☆☆ | v7.0 | 📐 Partial |
| F9 | Analyst Benchmarking | ★★★★☆ | v6.0 | Requires F1 (shadow mode) |
| F10 | A2A/MCP Protocol | ★★★☆☆ | v7.0 | 📐 Partial |
| F11-A | Multi-Source Context (SourceConnector) | ★★★★★ | v5.0 ✅ | ✅ Done (PLAT-5/6/7 complete) |
| F11-B | Source Trust Scoring | ★★★★☆ | v5.5 | 🔲 Not started |
| F11-C | Multi-SIEM Normalization | ★★★★★ | v6.0 | Depends on F5 |
| **F12** | **INTSUM Threat Briefing (Tab 5 Panel A)** | ★★★★★ | v5.5 (no σ) / v6.0 (with σ) | 🔧 Designed — σ-free version at v5.5 |
| **F13** | **ContextConnectors (email/Slack/docs)** | ★★★★☆ | v6.5 | PROPOSAL — gated by GATE-D |
| **F14** | **Ask the Graph (Tab 5 Panel B)** | ★★★★★ | v5.5-basic / v6.0-full | PROPOSAL — basic at v5.5; full gated by GATE-D |
| **F15** | **SynthesisNode** | ★★★★☆ | v6.5 | PROPOSAL — gated by GATE-M + GATE-V |

**v5.5 closes:** F1, F3, F11-B, F12 (σ-free version), and the v5.5-basic component of F14.
**v6.0 closes:** F5, F6, F9, and the σ-dependent versions of F12/F13/F14 (if GATE-M passes).
**v6.5+:** F7, F8, F10, F13, F15.

---

## 8. Tech Debt (Updated from issue_calibration_table.md)

> **Status key:** ✅ DONE · 🔵 PENDING · 🔄 BLOCKED

| ID | Severity | Issue | Target | Status |
|---|---|---|---|---|
| **TD-027** | HIGH | ScoringMatrix → ProfileScorer | v5.0 | ✅ DONE |
| **TD-030** | MED | τ=0.25 → τ=0.1 | v5.0 | ✅ DONE |
| — | — | Append-only centroid update log | v5.0 | ✅ DONE |
| TD-014/015 | LOW | TimeAnomaly/DeviceTrust property reads | v5.5 | 🔵 PENDING |
| TD-017 | HIGH | Hardening state persistence | v5.5 | 🔵 PENDING |
| TD-018 | MED | Dual persistence paths | v5.5 | 🔵 PENDING |
| TD-023 | LOW | Backward-compat block | v5.5 | 🔵 PENDING |
| TD-024 | LOW | Two LearningState classes | v5.0 ✅ (GAE-PROF-3) | ✅ Verify done |
| TD-029 | LOW | Remove deprecated ScoringMatrix | v5.5 | 🔵 PENDING |
| TD-031 | MED | LayerNorm for Tier 5 (V1B required) | v5.5 | 🔵 PENDING |
| TD-032 | LOW | OracleProvider protocol | v5.0 ✅ | ✅ DONE |
| **TD-033** | **HIGH** | Checkpoint/rollback mechanism | **v5.5** | 🔵 PENDING (§17.5 written Mar 11 — unblocked) |
| **G-L1-1** | **HIGH** | Alert type → category mapping (~20% misroute) | **v5.5-R6** | 🔵 PENDING — blocks GATE-R |
| **G-L2-3** | MED | Bootstrap decisions not written to Neo4j | v5.5 | 🔵 PENDING |
| **G-L4-2** | MED | factor_vector stored as JSON string in Neo4j | v5.5 | 🔵 PENDING |
| G-L1-2 | LOW | Bootstrap distribution uniform (non-uniform in real SOC) | v5.5 | 🔵 PENDING |
| G-L1-3 | LOW | No centroid editor UI / management API | v6.0 | 🔵 PENDING |
| G-L2-1 | HIGH | Chart A measures wrong thing (≈0.0 always) | v5.5-R3 | 🔵 PENDING |
| G-L2-2 | HIGH | No compounding-proof metric | v5.5-R4 | 🔵 PENDING |
| G-L4-1 | HIGH | Factor source nodes invisible (no provenance) | v5.5-R2 (F5) | 🔵 PENDING |
| G-L4-3 | MED | Pulsedive queried per alert, not persisted | v5.5-R7 | 🔵 PENDING |
| G-L5-4 | HIGH | Auto-approve coverage 11.5% (target 40%) | v5.5-R1 | 🔵 PENDING |
| **TD-034** | LOW | `DEC-DEC-XXXX` double prefix in Recent Evolution Events (Tab-4) — Evolution node id already starts with "DEC-", frontend prepends a second "DEC-" | v5.5 | 🔵 PENDING |

---

## 9. Document Update Queue

When sprint items and experiments complete, update the relevant documents immediately —
before starting the next sprint item. Do not batch document updates.

### 9.1 Pending Design Doc Writes (§4.1 above)

| Document | Section | Trigger | Status |
|---|---|---|---|
| soc_copilot_design_v5_4 | §17.5 rollback execution semantics | Now (Step 0a) | ✅ DONE (Mar 11) |
| soc_copilot_design_v5_4 | §23.5 NL judge rubric | Now (Step 0b) | ✅ DONE (Mar 11) |
| soc_copilot_design_v5_4 | §23.4 similar past cases spec | θ=0.85 placeholder; update per-category θ after PROD-3 | ✅ DONE (Mar 11 — θ placeholder in place) |
| soc_copilot_design_v5_4 | §22.3 IKS service — correct class → module-level functions | Mar 12 session | ✅ DONE (Mar 15 — v5.6 Part 1) |
| soc_copilot_design_v5_4 | §22.5 Add GET /api/soc/centroid-evolution + GET /api/soc/learning-state specs | Mar 12 session | ✅ DONE (Mar 15 — v5.6 Part 1) |
| soc_copilot_design_v5_4 | §11.5 Tab-2 Section A — update to purple summary card pattern (not full eval gate trace until live triage) | Mar 12 session | ✅ DONE (Mar 15 — v5.6 Part 1) |
| gae_design_v9.md | §9–10 ProfileScorer: add CentroidUpdate dataclass, freeze()/unfreeze(), update() return type | Mar 12 session | ✅ DONE (Mar 15 — v9.2: gt_action_index, CentroidUpdate.gt_delta_norm, SHIFT-2 §9.6) |
| soc_copilot_design_v5_4 | §23.4.1 per-category θ values from PROD-3 | PROD-3 completes | ✅ DONE (Mar 15 — PROD-3 values in v5.6 Part 1) |
| soc_copilot_design_v5_4 | §10.6-R1 PROD-4 threshold table (η_neg=0.05) | PROD-4 completes | ✅ DONE (Mar 15 — v5.6 Part 1) |
| soc_copilot_design_v5_4 | §10.6-R11 refer_to_analyst confidence floors (PROD-4b) | PROD-4b completes | ✅ DONE (Mar 15 — v5.6 Part 1) |
| math_synopsis | v7→v9: tensor 150→180, Eq 4b dual push/pull, frozen baseline, SHIFT-2, DISC-1 | Mar 15 session | ✅ DONE (Mar 15 — math_synopsis_v9.md) |

### 9.2 Pending Document Updates (Experiment-Triggered)

| Document | What to Update | Trigger |
|---|---|---|
| soc_copilot_design_v5_4 §9 | σ_max value (replace 1.0 placeholder with empirical p10) | FX-1-PROXY-REAL completes |
| soc_copilot_design_v5_4 §23.4 | Per-category θ values from PROD-3 cosine distance distribution | PROD-3 completes | ✅ DONE Mar 15 |
| claims_registry_v2 | FUTURE-12 claim promoted (40%+ coverage with composite discriminant, DISC-1) | PROD-4 + DISC-1 complete | 🔵 PENDING |
| math_synopsis_v9 §7 | threshold*(c) table with PROD-4 results; frozen baseline; SHIFT-2 | PROD-4/SHIFT-2 complete | ✅ DONE Mar 15 |
| Any document with "0.70 confidence floor — design estimate" | Replace with PROD-4b-derived values (0.93–0.97 per category) | PROD-4 completes | ✅ DONE Mar 15 (v5.6 Part 1 §10.6-R11) |
| claims_registry_v2 | FUTURE-01 promoted (routing accuracy %) | GATE-R completes |
| math_synopsis_v7 §7 | CLAIM-01 qualifier updated with measured routing % | GATE-R completes |
| claims_registry_v2 | FUTURE-18 promoted (IKS trajectory with κ*) | PROD-1 completes |
| soc_copilot_design_v5_4 §3.4 | κ* updated from 0.30 placeholder to calibrated value | PROD-1 completes |

### 9.3 Gated by Experiment Outcomes (Intentionally Deferred)

These documents must NOT be updated until the named gate passes. Same
experiment-first discipline applied to the bridge layer.

| Document | What's Deferred | Gate |
|---|---|---|
| gae_design_v9 | ProfileScorer σ parameter, synthesis-aware score() | GATE-M passes |
| soc_copilot_design_v5_4 | Tab 5 full implementation, ContextConnectors | GATE-D-EARLY + GATE-M |
| compounding_intelligence_v6 | Loop 4 as validated loop (not proposal) | GATE-V passes |
| architecture_philosophy_v1 | Loop 4 in five-layer model | GATE-V passes |
| platform_roadmap_v14 | σ activation as shipped feature | GATE-M decision |
| cross_graph_attention_v3 | Eq. 4-synthesis as validated equation | GATE-M + GATE-D |
| cross_graph_attention_v3 | Blog text accuracy qualifiers, compounding language | Pass 3 (after experiment figures available) |
| compounding_intelligence_v6 | Blog text: "compounding intelligence" → "institutional judgment" language | Pass 3 |

**Rule:** When a gate passes, the corresponding document update is the FIRST task in
the following session. Documents that reflect stale gate states create wrong experiments.

### 9.4 Document Update Priority Queue (CI v7 — Mar 12)

14 documents needing update following compounding_intelligence_v7 completion.
Full details in `document_update_priority_list.md` (outputs).

| Priority | Document | Core Change | Status |
|---|---|---|---|
| **1A** | next_session_startup_guide.md | v5.0 state, v7 authority, experiment count, paths | ✅ Done Mar 12 |
| **1B** | session_log_v55.md | Mar 12 session 2 entry | ✅ Done Mar 12 |
| **1C** | project_status_and_plan_v3_part1.md | Mar 12 session 2, v7 authority, Track D | ✅ Done Mar 12 |
| **2A** | platform_roadmap_v14.md | v7 as CI source; two-level + McKinsey in competitive section | 🔵 Before blog publish |
| **2B** | architecture_philosophy_v1_2.md | Insertion guide rewritten for v7 sections | 🔵 Before blog publish |
| **2C** | compounding_intelligence_v6.md | 3-line deprecation header | 🔵 Before blog publish |
| **3A** | gae_design_v9.md | Two-level naming; ProfileScorer = Level 1 | 🔵 Before v5.5 sprint |
| **3B** | soc_copilot_design_v5_4_part1.md | McKinsey case; two-level competitive; failure mode diagnostics | 🔵 Before v5.5 sprint |
| **3C** | intelligence_layer_design_v2.md | McKinsey framing aligned to v7; Flywheel/Generation cross-ref | 🔵 Before v5.5 sprint |
| **3D** | architecture_philosophy_v1.md | Loop 2 two-mechanism; CI Blog note → v7 | 🔵 Before v5.5 sprint |
| **4A–4D** | bridge_experiments_catalog, s2p_copilot, product_strategy, math_synopsis | v7 vocabulary; supply chain case; Generation taxonomy | 🔵 Before v6.0 planning |

---

## 9.5 March 14-15 Session Findings

### Finding 1: ProfileScorer.update() Bug — Found and Fixed
correct=False branch pushed ALL action centroids away from f, including the ground truth
action. This caused centroid degradation: every incorrect prediction made the correct
centroid worse. Fixed: push predicted away, pull GT toward f. GAE 251 tests.
SHIFT-2 validated: -9% lift → +2.7% lift (noise=0, δ=0.10, w=1000).
**Impact on prior experiments:** EXP-B1/SHIFT-1 results at noise>0 had attenuated learning
lift due to bug. Relative comparisons within those experiments remain valid. Absolute
learning numbers should be re-read with corrected update rule.

### Finding 2: Frozen Scorer Is the Strongest Cold-Start
μ₀ (expert prior, no learning, no real decisions): 80.4% accuracy, 92.9% coverage at
85% precision (zero noise). At 10% noise: 72.5% accuracy, 62.6% coverage.
Learning adds +2.7% accuracy when prior mismatch exists (δ>0).
**Decision:** Ship frozen scorer as default. Enable learning after shadow validation.
The frozen scorer is already a strong product. Learning is incremental improvement.

### Finding 3: Composite Discriminant Lifts Coverage
Logistic regression on {confidence, margin, entropy, distance features, factor features,
rolling_accuracy, cat_count}: 70.4% coverage at 85% precision vs 62.6% confidence-only
(+7.8pp lift). rolling_accuracy is the strongest orthogonal signal (coef=5.06, corr
with confidence=0.09). IKS v2 trajectory validated (43→82 over 1000 decisions).
**Decision:** Phase 5 AUTO-1 should use composite discriminant, not confidence threshold alone.

### Finding 4: η_neg=1.0 Is Catastrophically Miscalibrated (ECE=0.49)
All prior PROD experiments run at η_neg=1.0 have invalid absolute calibration numbers.
Relative findings (GATE-OP, EXP-S2-REPRO — same η_neg both arms) remain valid.
η_neg=0.05 is the canonical production value (symmetric with η).
The 20:1 penalty ratio lives in consequence weighting (decision layer), not learning rates.

### Finding 5: Generator Circularity Masked Learning Capacity
CategoryAlertGenerator samples from μ₀ = μ_true (centroidal regime). Nothing to learn.
SHIFT-2 with δ>0 confirms learning works when prior mismatch exists. Realistic deployment
(real alerts, genuine prior mismatch) should show positive learning lift.

### Finding 6: SOC Product Was Always Frozen
SOC product calls LearningState.update() (old W-matrix path), not ProfileScorer.update()
directly. The update() bug affected only experiments. Product was using frozen scorer
all along — which explains the good baseline results. The fix enables learning going forward.

---

## 10. Five Parallel Tracks (Updated Status)

| Track | Status | Next Action |
|---|---|---|
| **A: v5.5 Code Sprint** | 🔄 Pre-sprint closure DONE (Steps 1-2 complete). Phase 1 READY to start. | Open Part 2 Phase 1 (CORR-1a already done, verify GATE-R). Phase 5 redesigned — see §9.5 Finding 3 + Part 2. |
| **B: Intelligence Layer Experiments** | 🔄 In progress — EXP-S2-REPRO Arm 0 can start now | Run Arm 0, then FX-1-PROXY-REAL → Arm A → Arm B |
| **C: Math Paper Update** | 🔵 Staged | cross_graph_attention_update_spec_v2 §1 + math_paper_session_note (16-step execution). Blocked only by researcher bandwidth. |
| **D: Outreach** | 🔄 Blocked until v5.5-alpha | Demo blurb v4.0, Loom v2, LinkedIn. Sources: cross_graph_attention_v3, **compounding_intelligence_v7 Parts 1/2/3** (supersedes v6). Start after shadow mode demo is live. |
| **E: Graphics** | 🔵 Ready | ARCH-01 spec in architecture_philosophy_v1. CGA-06 spec in cross_graph_attention_update_spec_v2. Can proceed independently. |

---

*Project Status & Plan v3.1 · Part 1 of 2 · Last updated March 15, 2026*
*v5.0 tagged: 251 GAE tests, 111 SOC tests. 34 experiments. CORR-1a routing fixed. update() bug fixed. PROD-3/4/4b complete.*
*Two accuracy regimes: centroidal (97.89%) and realistic 50-seed (71.7%). Never mix them.*
*CLAIM-31 (consistency) is the only unconditional claim. Use it in every conversation.*
*Pre-sprint closure: Steps 0a–0e, 1, 2 ✅. PROD-3/4/4b complete. Phase 1 (S1/GATE-R) is next. Phase 5 redesigned (composite discriminant).*
*Known cosmetic gap: TD-034 DEC-DEC- double prefix in Tab-4 Recent Evolution Events.*
*IKS service is module-level functions — use `from app.services.iks import compute_iks, interpret`.*
*centroid-evolution returns flat array [] not {evolution:[]}. Frontend state: useState<CentroidEvolutionEntry[]>([]).*
*Part 2 contains: v5.5 sprint phases + prompts, v6.0 architecture + requirements,*
*measures of success, product_strategy_v2 coverage maps.*
*"v5.5 is the product. v5.0 is the foundation. The compounding must be made visible."*
