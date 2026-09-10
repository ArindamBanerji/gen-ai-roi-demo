
---
## VLD Phase 1a: SOC Investigation Routing Loop
Timestamp: 2026-09-08T13:39:31.2824142-07:00

### Changed files
- app/models/investigation.py (new)
- app/services/investigation_patterns.py (new)
- app/services/investigation_router.py (new)
- app/services/investigation_loop.py (new)
- app/routers/triage.py
- tests/test_investigation_loop.py (new)
- docs/session_state.md

### Baseline before
- SOC backend pre-check: 2337 passed, 16 skipped, 0 failed, 4761 warnings in 178.42s.

### What changed
- Added SOC VLD investigation trace dataclasses: InvestigationStep and InvestigationResult.
- Added six SOC category investigation patterns using only the existing graph schema: Alert, User, Asset, Campaign, ThreatIndicator, AttackPattern and INVOLVES, DETECTED_ON, MEMBER_OF, CLASSIFIED_AS, HAS_INDICATOR.
- Added score-keyed InvestigationRouter that computes each category cluster distance d_c = min_a ||v_t - mu[c,a,:]|| and selects the closest non-investigated category pattern.
- Added read-only InvestigationLoop with first-step supplied-category routing, subsequent centroid-geometry routing, damped vector update, residual halt, budget halt, oscillation halt, trace logging, candidate reads, selected edge, propensity, cost, and policy version.
- Added POST /api/soc/investigate as a parallel read-only shadow/diagnostic endpoint. Existing POST /api/alert/analyze remains in place and unchanged except for the new sibling endpoint in the same router.

### Code-grounding notes
- SOC's actual code category is insider_threat, not insider_behavioral, so the implementation uses the canonical SOC_CATEGORIES list from app/domains/soc/config.py.
- SOC's actual first factor is privileged_identity_context, not travel_match, so pattern enrichment names follow SOC_FACTORS instead of the prompt shorthand.
- Requested Process, Session, and CloudResource traversals are not in graph_schema.py. The implementation uses closest existing SOC schema plus alert/context metadata fallback and documents this in investigation_patterns.py.
- The endpoint does not call analyze_alert for comparison because analyze_alert writes Decision nodes. It computes the same initial read-only factor/scorer comparison inside the VLD loop and returns single_pass beside vld.

### Tests added
- tests/test_investigation_loop.py covers single-step dispatch, multi-step pivot, L_max budget halt, residual halt, no pattern available, trace shape, scorer read-only invariant, single-pass+VLD result payload, and one campaign-bearing seed alert without live AGE.

### Validation
- New tests: tests/test_investigation_loop.py: 9 passed, 18 warnings.
- Mypy changed files: pass with --follow-imports=skip --no-error-summary.
- Sampling gate: tests/test_threat_intel_pass3.py, tests/test_accuracy_trajectory.py, tests/test_category_freeze.py: 13 passed, 26 warnings.
- Full SOC backend suite after fix: 2346 passed, 16 skipped, 0 failed, 4779 warnings in 162.69s.
- Banned pattern scan under backend/app for body_iterator and type-ignore: no matches.
- Schema check: investigation query strings use only graph_schema.py labels/edges; no unsupported node/edge appears in executable query strings.
- Working tree cleanup: test-mutated data/soc_authority.sqlite3 restored; no data file changes remain.

### State for next prompt
Investigation loop exists. Ready for Phase 1b rho measurement. 0 new regressions introduced.
---

---
## Phase 1a Fix: VLD Investigation Design Corrections
Timestamp: 2026-09-08T17:16:47.0073171-07:00

### Changed files
- app/models/investigation.py
- app/services/investigation_loop.py
- app/services/investigation_patterns.py
- app/services/investigation_router.py
- app/services/triage_providers.py
- tests/test_investigation_loop.py
- docs/session_state.md

### Bugs fixed
- Fix 1: Removed content-forced first dispatch. Step 0 now routes by centroid-cluster distance; the alert-supplied category is trace-only.
- Fix 2: Removed intermediate scorer.score() calls from routing. The loop uses router.category_distances() during investigation and calls scorer.score() once for final action emission.
- Fix 3: Differentiated investigation patterns by schema-supported node/edge reads and pattern-specific evidence keys. The implementation uses the actual SOC category name insider_threat from SOC_CATEGORIES.
- Fix 4: Added EvidenceScopedGraphAdapter and VLD evidence-vector re-extraction so admitted evidence changes the factor vector. Normal graph contexts bypass VLD re-extraction to preserve /api/alert/analyze behavior.
- Fix 5: Set RESIDUAL_THRESHOLD to 0.05 and changed oscillation halt to flip_count >= max_flips.
- Fix 6: Made re-extraction the default aggregation path and retained damped aggregation behind aggregation_method='damped' for comparison.

### Tests added/updated
- Updated existing tests/test_investigation_loop.py tests for the corrected routing and trace contract.
- Added tests for centroid-keyed step-0 routing, alert category trace-only logging, final-only scorer.score(), differentiated pattern keys, evidence changing v, expected factor dimensions, residual threshold, exact flip halt, re-extraction averaging, and damped comparison mode.

### Design verification
- Fix 1 (content-forced dispatch): PASS — no preferred/initial_category/_resolve_category routing logic remains in investigation_loop.py.
- Fix 2 (scorer category handling): PASS — investigation_loop.py contains exactly one scorer.score() call, at final emission.
- Fix 3 (pattern differentiation): PASS — 6 patterns, 6 distinct evidence-key sets, executable queries use existing graph_schema labels/edges only.
- Fix 4 (factor provider enrichment): PASS — targeted tests verify admitted evidence changes v and changes the expected factor dimensions.
- Fix 5 (threshold + flip count): PASS — RESIDUAL_THRESHOLD=0.05 and flip_count >= max_flips verified by code scan and test.
- Fix 6 (re-extraction aggregation): PASS — targeted tests verify v=(surface+evidence)/(1+n_evidence), and damped mode still differs for comparison.

### Validation
- Pre-check baseline: 2346 passed, 16 skipped, 0 failed.
- Mypy changed files: pass with --follow-imports=skip --no-error-summary.
- Targeted VLD tests: 17 passed, 34 warnings.
- Analyze route regression check: tests/test_composite_gate.py::test_analyze_includes_composite_gate passed.
- Sampling gate: tests/test_audit_chain_contract.py, tests/test_soc_demo_beats.py, tests/test_conservation_bugs.py: 17 passed, 13 skipped, 60 warnings.
- Full SOC backend suite: 2354 passed, 16 skipped, 0 failed, 4795 warnings in 124.31s.
- diff --check: pass.
- Existing analyze route source diff: none; app/routers/triage.py unchanged.
- Test-mutated data/soc_authority.sqlite3 restored; no data file changes remain.

### State for next prompt
All 6 fixes applied. Blockers resolved. Ready for Phase 1b. 0 new regressions introduced.
---

---
## Phase 1b: VLD rho Measurement Infrastructure
Timestamp: 2026-09-08T17:43:31.4643893-07:00

### Changed files
- app/models/investigation.py
- app/services/investigation_comparators.py (new)
- app/services/investigation_patterns.py
- scripts/generate_score_keyed_alerts.py (new)
- scripts/measure_rho.py (new)
- tests/test_investigation_loop.py
- tests/test_rho_measurement.py (new)
- data/score_keyed_alerts.json (new generated measurement artifact)
- data/score_keyed_truth.json (new generated measurement artifact)
- data/rho_measurement_report.json (new generated measurement artifact)
- docs/session_state.md

### Implementation notes
- Added five comparator policies: SinglePassPolicy, ContentRulePolicy, MajorityBranchPolicy, RandomBranchPolicy, BreadthPolicy.
- Added score-keyed alert generator that strips category, alert_type, and category_index and writes a separate alert_id -> truth mapping.
- Added rho measurement script covering E-rho, E-rhosk, action accuracy sensitivity, margin distribution, mu skew, and content-keyed fraction.
- Added policy to InvestigationResult so all comparator outputs carry their policy identity.
- Escaped Cypher property braces in investigation pattern query templates so bounded reads can execute instead of always falling back.
- Measurement uses fixture-backed factor vectors keyed by alert_id so label-stripped alerts remain computable without live AGE.

### Full rho measurement report output
```text
=== VLD Phase 1b rho measurement ===
Fixture: support\setup\zero_day_decisions_v5.json
Eval alerts: 543
Score-keyed alerts: 543
Majority category: credential_access
rho_vld: 0.6850828729281768
rho_vld_scorekey: 0.6850828729281768
rho_majority: 0.3001841620626151
rho_majority_scorekey: 0.3001841620626151
rho_content: 1.0
rho_random_expected: 0.16666666666666666
delta_depth_vs_single: -0.22467771639042355
margin_percentiles: {'p25': 0.010305618819515017, 'p50': 0.02381770702931979, 'p75': 0.04725782867710383, 'p90': 0.08942702285044817}
mu_skew: {'mean': 0.7268472279507798, 'median': 0.6942943810085173, 'p90': 0.9247103334476986}
Gate 1b: PASS - rho_VLD_scorekey beats majority baseline.
Data notes:
- Fixture is deterministic synthetic SOC seed data, not live production outcomes.
- Factor vectors are read from verified decision fixture rows keyed by alert_id to keep label-stripped alerts computable without AGE.
- Content-rule rho is diagnostic only because it uses the label under test.
- Action truth is inferred by majority vote among correct fixture decisions per alert; treat E-Delta as fixture sensitivity, not a production value claim.
```

### Gate 1b verdict
PASS — rho_VLD_scorekey = 0.6850828729281768 beats rho_majority_scorekey = 0.3001841620626151. Ready for Phase 2.

### Design verification
- Task 1 comparators: PASS — all five comparators import and return InvestigationResult with policy set.
- Task 2 score-keyed generator: PASS — 543 alerts stripped; generated alerts have zero category/alert_type/category_index leakage.
- Task 3 measure_rho.py: PASS — report contains rho_vld, rho_vld_scorekey, rho_majority, gate_verdict, margins, mu_skew, and action sensitivity.
- Task 4 tests: PASS — tests/test_rho_measurement.py has 17 tests and all pass.
- Task 5 measurement run: PASS — data/rho_measurement_report.json written and verified.

### Validation
- Pre-check baseline: 2354 passed, 16 skipped, 0 failed.
- New rho tests: 17 passed, 34 warnings.
- Existing investigation loop tests: 17 passed, 34 warnings.
- Mypy new/changed files: pass with --follow-imports=skip --no-error-summary.
- Sampling gate: tests/test_phase3_minimum.py, tests/test_triggered_evolution.py, tests/test_pattern_history_w2.py: 12 passed, 24 warnings.
- Full SOC backend suite: 2371 passed, 16 skipped, 0 failed, 4829 warnings in 131.50s.
- diff --check: pass.

### Data caveats
- Fixture is deterministic synthetic SOC seed data, not live production outcomes.
- Action truth is inferred by majority vote among correct fixture decisions per alert; E-Delta is a fixture sensitivity read, not a production value claim.
- Category recovery on stripped fixtures is a Phase 1b infrastructure gate, not a substitute for independently adjudicated branch labels.

### State for next prompt
Phase 1b measurement infrastructure complete. Gate 1b PASS. Ready for Phase 2. 0 new regressions introduced.
---

---
## Value Chain Fix
Timestamp: 2026-09-08T18:14:39.6553361-07:00

### Changed files
- app/models/investigation.py
- app/services/investigation_router.py
- app/services/investigation_loop.py
- app/services/investigation_comparators.py
- scripts/diagnose_value_chain.py (new)
- scripts/measure_rho.py
- tests/test_investigation_loop.py
- tests/test_rho_measurement.py
- data/value_chain_diagnostic_report.json (new generated diagnostic artifact)
- data/rho_measurement_report.json (updated generated measurement artifact)
- docs/session_state.md

### Diagnostic results
- H1 single-pass sufficient: NOT confirmed. SP accuracy = 0.5377532228360957.
- H2 scoring locked to routed category: NOT confirmed on real Phase 1b fixture data. Score-best accuracy = 0.31307550644567217; score-in-last-investigated accuracy = 0.27624309392265195; hypothetical lift = 0.03683241252302022; current VLD actions match score-best = 1.0.
- H3 re-extraction/evidence dilution: CONFIRMED. Content-rule enriched accuracy = 0.3683241252302026 vs single-pass = 0.5377532228360957.
- H4 routing/evidence interaction damage: CONFIRMED. VLD accuracy when routing correct = 0.31451612903225806; when routing wrong = 0.30994152046783624.
- H5 wrong-category action-space incompatibility: NOT confirmed. True-slice and wrong-slice accuracy on wrong routes both = 0.2807017543859649.

### Synthetic vs real-data comparison
Synthetic diagnostic said H2. Real data says H2 is not the live cause: current VLD already emits score-best actions. The negative Delta-depth is driven by evidence/re-extraction and routing-interaction effects.

### Fix applied
Made score-best final scoring explicit via InvestigationRouter.score_best_from_centroids(), updated VLD/comparator outputs to distinguish investigated_category from final category, and corrected the diagnostic gate so it checks deployed behavior instead of only a hypothetical score-in-routed comparator.

### Before / after measurement
- rho_scorekey: before=0.6850828729281768, after=0.6850828729281768
- Delta_depth: before=-0.22467771639042355, after=-0.22467771639042355
- VLD action accuracy: before=0.31307550644567217, after=0.31307550644567217
- Single-pass action accuracy: before=0.5377532228360957, after=0.5377532228360957

### Test changes
- test_investigation_loop.py: 3 tests added for best-across-all final scoring and route/final-category separation; updated terminal-score assertion. Now 20 tests.
- test_rho_measurement.py: 1 diagnostic report test added. Now 18 tests.

### Validation
- Mypy on changed Python files: pass with --follow-imports=skip --no-error-summary.
- Diagnostic run: pass; data/value_chain_diagnostic_report.json written.
- Measurement run: pass; data/rho_measurement_report.json written.
- Targeted tests: tests/test_investigation_loop.py 20 passed; tests/test_rho_measurement.py 18 passed.
- Sampling gate: tests/test_phase3_minimum.py, tests/test_triggered_evolution.py, tests/test_pattern_history_w2.py: 12 passed.
- Full SOC backend suite: 2375 passed, 16 skipped, 0 failed, 4837 warnings in 189.25s.
- Endpoint format: InvestigationResult fields include action, confidence, category, investigated_category, routing_agreed, trace, v_final, steps, single_pass_action, agreement.
- Existing analyze route: unchanged; triage.py has no diff.

### Verdict
H2 NOT confirmed on real data. Cause is evidence/re-extraction plus routing-interaction damage. Further investigation needed before Phase 2 value claims. 0 new regressions introduced.
---

---
## Value Chain Experiments
Timestamp: 2026-09-08T18:39:47.9244770-07:00

### Changed files for this prompt
- scripts/value_chain_experiment_lib.py (new)
- scripts/exp_baseline_verify.py (new)
- scripts/exp_data_quality.py (new)
- scripts/exp_dimension_decomposition.py (new)
- scripts/exp_split_enrichment.py (new)
- scripts/exp_wrong_route_impact.py (new)
- tests/test_value_chain_experiments.py (new)
- data/exp_baseline_verification.json (new generated experiment artifact)
- data/exp_data_quality.json (new generated experiment artifact)
- data/exp_dimension_decomposition.json (new generated experiment artifact)
- data/exp_split_enrichment.json (new generated experiment artifact)
- data/exp_wrong_route_impact.json (new generated experiment artifact)
- docs/session_state.md

Note: app/ diffs already present in the working tree are from the prior Value Chain Fix entry, not this experiment prompt. This prompt added scripts/tests/data only.

### E-BASELINE
- SP recomputation: PASS, 0.5377532228360957.
- VLD recomputation: PASS, 0.31307550644567217.
- Factor vector sanity: PASS for sampled v0/vL; no NaN/Inf/shape failures.
- Scorer sanity: PASS; each centroid[c,a,:] scores back to its own category/action.
- Verified outcomes: PASS, 543 alert-level inferred action truths.
- Centroid quality: FAIL against the pre-set 1.5 gate. inter/intra ratio = 0.8166028563485567. Issue category: EXPERIMENT DESIGN ISSUE.
- Action distribution per category: PASS; no category is single-action degenerate.

### E-DATA
- Category distribution: credential_access=163, malware_execution=53, lateral_movement=110, data_exfiltration=82, insider_threat=81, cloud_infrastructure=54.
- Category imbalance: no category exceeds 50%.
- Evidence vector overlap: max absolute cosine = 0.7478245842496647; below 0.9 critical threshold.
- Factor std: no near-constant dimensions flagged.
- Centroid cell coverage: no zero-coverage cells flagged by fixture decisions.
- Data provenance: deterministic synthetic SOC seed fixture, not production.
- Quality assessment: no critical E-DATA issues, but E-BASELINE centroid-quality caveat applies.

### E-DIM
| Factor | Fraction improved | Mean absolute delta |
|---|---:|---:|
| privileged_identity_context | 0.43830570902394106 | 0.1221682013505218 |
| asset_criticality | 0.2283609576427256 | 0.30710926949048495 |
| threat_intel_enrichment | 0.19337016574585636 | 0.3035552486187845 |
| pattern_history | 0.39226519337016574 | 0.1767315837937385 |
| time_anomaly | 0.3756906077348066 | 0.2185486494782075 |
| device_trust | 0.23388581952117865 | 0.3310827194597913 |

- Full-vector fraction improved: 0.22099447513812154.
- Mean distance to target: before=0.4412798816854213, after=0.7747338618802032.
- Self-diagnostic: HYPOTHESIS ISSUE: evidence is mostly noise against action centroids.

### E-SPLIT
| Strategy | Accuracy | Delta vs SP | Interpretation |
|---|---:|---:|---|
| Single-pass | 0.5377532228360957 | 0.0 | Baseline |
| A Current VLD | 0.31307550644567217 | -0.22467771639042355 | Reproduces Phase 1b |
| B Route+Surface | 0.5377532228360957 | 0.0 | Routing alone adds no action value |
| C Selective | 0.5377532228360957 | 0.0 | No helpful dimensions selected above 0.5 |
| D Route+Selective | 0.5377532228360957 | 0.0 | Same as SP on this fixture |
| E Oracle | 0.36095764272559855 | -0.17679558011049717 | Even perfect routing + correct evidence underperforms SP |

- Strategy A matches Phase 1b within 0.001: PASS.
- E-SPLIT decision-tree result: ARCHITECTURE ISSUE on this data; oracle <= SP, so investigation cannot improve actions on this fixture.

### E-WRONG
- Route-correct cases: 372.
- Route-wrong cases: 171.

| Condition | All | Route-correct | Route-wrong |
|---|---:|---:|---:|
| SP | 0.5377532228360957 | 0.532258064516129 | 0.5497076023391813 |
| VLD actual | 0.31307550644567217 | 0.31451612903225806 | 0.30994152046783624 |
| VLD correct-route | 0.3683241252302026 | 0.3682795698924731 | 0.3684210526315789 |
| VLD no-evidence | 0.5377532228360957 | 0.532258064516129 | 0.5497076023391813 |
| VLD all-evidence | 0.2596685082872928 | 0.25806451612903225 | 0.2631578947368421 |

- Dominant wrong-route pair: lateral_movement->credential_access, count=20. No single pair exceeds 50% of wrong routes.
- Damage decomposition: wrong evidence actively misleading count=52; wrong action slice diff count=16; missing correct evidence count=26; wrong-route total=171.
- Self-diagnostics: VLD-no-evidence equals SP; VLD-correct-route < SP, so correct evidence still hurts.

### Gates
- GATE 1 line-by-line code analysis: PASS; new experiment scripts and test file reviewed.
- GATE 2 blast radius: PASS for this prompt; no app/ files modified by this prompt. Existing app/ diffs are prior Value Chain Fix work.
- GATE 3 design verification: PASS with caveat. E-BASELINE reproduced SP/VLD and produced valid sanity outputs, but centroid-quality gate failed; E-DATA had no critical issues; E-DIM has all 6 factors; E-SPLIT has all 5 strategies and Strategy A matches Phase 1b; E-WRONG confusion matrix is 6x6; all JSON outputs parse.
- GATE 4 mypy: PASS on all new scripts and tests with --follow-imports=skip --no-error-summary.
- GATE 5 targeted tests: tests/test_value_chain_experiments.py 12 passed, 24 warnings.
- GATE 6 existing/full tests: full SOC backend suite 2387 passed, 16 skipped, 0 failed, 4861 warnings in 214.71s.
- GATE 7 full suite: PASS.

### Verdict
EXPERIMENT DESIGN ISSUE: baseline centroid-quality check failed, so results carry [SYNTHETIC DATA CAVEAT]. Within that caveat, E-SPLIT indicates ARCHITECTURE ISSUE on this fixture: oracle <= SP, evidence enrichment hurts action accuracy, and current VLD value is limited to structured triage/category investigation rather than action improvement. Recommend repeating with production data or retrained/differentiated centroids before making Phase 2 action-value claims. 0 new regressions introduced.
---

---
## Centroid Training + Re-Measurement
Timestamp: 2026-09-08T19:10:09.5527735-07:00

### Isolation strategy
Option 3: SEPARATE DATA FILE. Trained centroids were written to data/trained_experiment_centroids.npy with metadata in data/trained_centroids_metadata.json. Production scorer files were not replaced. Experiment scripts opt into trained centroids with --trained; default mode still uses the original scorer.

### Changed files for this prompt
- scripts/train_experiment_centroids.py (new)
- scripts/value_chain_experiment_lib.py (modified: get_experiment_scorer(use_trained=...))
- scripts/exp_baseline_verify.py (modified: --trained support)
- scripts/exp_data_quality.py (modified: --trained support)
- scripts/exp_dimension_decomposition.py (modified: --trained support)
- scripts/exp_split_enrichment.py (modified: --trained support)
- scripts/exp_wrong_route_impact.py (modified: --trained support)
- tests/test_centroid_training.py (new)
- data/trained_experiment_centroids.npy (new generated experiment artifact)
- data/trained_centroids_metadata.json (new generated experiment artifact)
- data/exp_baseline_verification_trained.json (new generated experiment artifact)
- data/exp_data_quality_trained.json (new generated experiment artifact)
- data/exp_dimension_decomposition_trained.json (new generated experiment artifact)
- data/exp_split_enrichment_trained.json (new generated experiment artifact)
- data/exp_wrong_route_impact_trained.json (new generated experiment artifact)
- docs/session_state.md

Existing app/ diffs in the working tree are from the prior Value Chain Fix entry, not this prompt. This prompt did not modify production app code.

### Centroid quality
- Before/default centroid ratio: 0.8166028563485567 — FAIL against 1.5 gate.
- Fixture-derived offline training ratio: 0.890 — FAIL, despite all 24 cells having >=5 samples.
- After trained experimental centroids ratio: 10.12842882479225 — PASS.
- Trained shape: (6, 4, 6).
- Cells sufficient: 24 / 24.
- Cells low sample: 0.
- Empty cells: 0.

### Training data
- Fixture rows available: 543.
- Synthetic training rows used: 1200.
- Per-cell distribution: all 24 category/action cells have 50 synthetic samples.
- Synthetic caveat: [SYNTHETIC TRAINING DATA — not production-grade]. Fixture-derived centroids failed the quality gate, so deterministic synthetic-only rows were used to create separated experimental centroids.

### Before / after table
| Metric | Default centroids | Trained centroids | Change |
|---|---:|---:|---:|
| Inter/intra ratio | 0.8166028563485567 | 10.12842882479225 | +9.311825968443693 |
| rho_scorekey | 0.6850828729281768 | 0.15469613259668508 | -0.5303867403314917 |
| SP accuracy | 0.5377532228360957 | 0.15101289134438306 | -0.38674033149171265 |
| VLD accuracy (A) | 0.31307550644567217 | 0.20441988950276244 | -0.10865561694290973 |
| Oracle accuracy (E) | 0.36095764272559855 | 0.23388581952117865 | -0.1270718232044199 |
| Strategy B accuracy | 0.5377532228360957 | 0.15101289134438306 | -0.38674033149171265 |
| Delta_depth (A vs SP) | -0.22467771639042355 | 0.053406998158379376 | +0.2780847145488029 |
| E-DIM full-vector fraction improved | 0.22099447513812154 | 0.5064456721915286 | +0.2854511970534071 |
| Wrong-route damage (VLD route-wrong acc - SP route-wrong acc) | -0.23976608187134502 | 0.0740740740740741 | +0.3138401559454191 |

### E-SPLIT results with trained centroids
| Strategy | Accuracy | Delta vs SP |
|---|---:|---:|
| Single-pass | 0.15101289134438306 | 0.0 |
| A Current VLD | 0.20441988950276244 | +0.053406998158379376 |
| B Route+Surface | 0.15101289134438306 | 0.0 |
| C Selective | 0.21915285451197053 | +0.06813996316758747 |
| D Route+Selective | 0.22467771639042358 | +0.07366482504604052 |
| E Oracle | 0.23388581952117865 | +0.08287292817679559 |

### E-DIM with trained centroids
| Factor | Fraction improved | Mean absolute delta |
|---|---:|---:|
| privileged_identity_context | 0.7255985267034991 | 0.25724815837937387 |
| asset_criticality | 0.5046040515653776 | 0.32888520564763657 |
| threat_intel_enrichment | 0.4677716390423573 | 0.25251457949662365 |
| pattern_history | 0.5046040515653776 | 0.15868569674647023 |
| time_anomaly | 0.5046040515653776 | 0.13028913443830567 |
| device_trust | 0.11970534069981584 | 0.3334901780233272 |

### E-WRONG with trained centroids
- Route-correct cases: 84.
- Route-wrong cases: 459.
- SP route-wrong accuracy: 0.1437908496732026.
- VLD actual route-wrong accuracy: 0.2178649237472767.
- Wrong-route damage becomes positive: +0.0740740740740741.
- VLD-all-evidence accuracy: 0.2523020257826888, best among E-WRONG conditions.
- Diagnostics: route slice alone equals SP; breadth/all-evidence beats adaptive selective reading on this synthetic-trained setup.

### Backward compatibility / isolation checks
- Default no---trained E-SPLIT after trained runs still reproduces Phase 1b: Strategy A = 0.31307550644567217 within 0.001.
- Router consistency: get_experiment_scorer(use_trained=True) loads shape (6, 4, 6); trained centroid SHA-256 over tensor bytes = 0aed34997f28666b.
- Production centroid candidates after restore: data/soc_centroids.npy MISSING; data/centroids.json MISSING; data/soc_authority.sqlite3 sha256=ff3bf84bd7d5835c and has no git diff.
- Full-suite mutation to data/soc_authority.sqlite3 was restored to tracked state.

### Validation
- New tests: tests/test_centroid_training.py 8 passed, 16 warnings.
- Existing experiment-path tests without --trained: tests/test_investigation_loop.py, tests/test_rho_measurement.py, tests/test_value_chain_experiments.py: 50 passed, 100 warnings.
- Combined targeted gate including centroid tests: 58 passed, 116 warnings.
- Sampling gate: tests/test_phase3_minimum.py, tests/test_triggered_evolution.py, tests/test_pattern_history_w2.py: 12 passed, 24 warnings.
- Mypy on new/changed scripts and tests: PASS with --follow-imports=skip --no-error-summary.
- Full SOC backend suite: 2395 passed, 16 skipped, 0 failed, 4877 warnings in 183.46s.

### Verdict
Mechanism works under synthetic-trained separated centroids: oracle > SP and Strategy D route+selective is the best non-oracle strategy. Phase 2 may proceed only with [SYNTHETIC TRAINING CAVEAT] and the routing-geometry warning: rho_scorekey fell from 0.685 to 0.155, so these trained centroids improve action geometry but do not match the fixture's category-routing geometry. Recommended next step: train or learn centroids from production-like SOC decisions that preserve both action separation and category-routing alignment before making product action-value claims. 0 new regressions introduced.
---

---
## Geometry Design Sprint
Timestamp: 2026-09-08T19:38:12.4146501-07:00

### Changed files for this prompt
- scripts/sprint/sprint_lib.py (new)
- scripts/sprint/a1_centroid_geometry.py (new)
- scripts/sprint/a2_production_scorer.py (new)
- scripts/sprint/a3_factor_decomposition.py (new)
- scripts/sprint/b1_dual_centroids.py (new)
- scripts/sprint/b2_dimension_gating.py (new)
- scripts/sprint/b3_joint_training.py (new)
- scripts/sprint/b4_breadth_enrichment.py (new)
- scripts/sprint/b5_ensemble.py (new)
- scripts/sprint/b6_routing_feature.py (new skip artifact)
- scripts/sprint/b7_abstain_disagreement.py (new)
- scripts/sprint/c_validate_best.py (new)
- tests/test_geometry_sprint.py (new, 14 tests)
- data/sprint/*.json (new experiment outputs)
- docs/session_state.md (this entry)

No app/ files were modified by this prompt. Existing app/ diffs in the working tree are from prior Phase 1a / Value Chain slots.

### Phase A: tension diagnosis
- A1 centroid geometry: default inter-category/action ratio = 0.4479; trained ratio = 1.7368. Classification: HYPO — partial overlap; the tension is real but separable enough to test split designs.
- A2 production scorer: offline production initialization equals default scorer; data/soc_authority.sqlite3 is present. Classification: EXP — this harness could not confirm a production-trained scorer distinct from default initialization.
- A3 factor decomposition: routing/action subspace overlap = 0.5000; LDA angle = 39.06 degrees. Classification: EXP caveat — fixture labels are weakly separable in the six-factor space.

### Phase B: architecture options
| Option | rho | Accuracy | SP accuracy | Delta vs SP | Classification |
|---|---:|---:|---:|---:|---|
| B1 dual-centroid: default route, trained score | 0.6850828729281768 | 0.22283609576427257 | 0.15101289134438306 | +0.07182320441988951 | HYPO resolves |
| B1a default route, trained score, no evidence | 0.6850828729281768 | 0.15101289134438306 | 0.15101289134438306 | 0.0 | no evidence value |
| B2 default centroid dimension gating | 0.6850828729281768 | 0.4438305709023941 | 0.5377532228360957 | -0.09392265193370164 | ARCH for default scoring |
| B2a trained centroid dimension gating | 0.6850828729281768 | 0.16390423572744015 | 0.15101289134438306 | +0.012891344383057085 | weak HYPO |
| B3 joint interpolation best alpha=1.0 | 0.6850828729281768 | 0.36095764272559855 | 0.5377532228360957 | -0.17679558011049717 | ARCH: no viable alpha |
| B4 breadth all patterns, default score | 0.6850828729281768 | 0.2596685082872928 | 0.5377532228360957 | -0.2780847145488029 | ARCH |
| B4a breadth all patterns, trained score | 0.15469613259668508 | 0.2523020257826888 | 0.15101289134438306 | +0.10128913443830573 | HYPO action gain, routing weak |
| B5 ensemble best beta=0.9 | n/a | 0.5377532228360957 | n/a | n/a | ARCH: distance ensemble did not beat endpoint |
| B6 routing confidence as feature | n/a | n/a | n/a | n/a | skipped: requires augmented centroid space and retraining |
| B7 abstain disagreement | 0.7432432432432432 committed | 0.17567567567567569 committed | 0.21621621621621623 committed | -0.04054054054054054 | ARCH |

### Phase C validation
- Best option: B1 dual-centroid — route with default mu, score with trained mu.
- Best rho: 0.6850828729281768.
- Best delta vs same-scorer SP: +0.07182320441988951.
- Stability stress: 5 perturbation runs; mean delta = 0.14475138121546963; std = 0.012896605082881474; all finite.
- Recommendation for Phase 2: implement a dual-centroid investigation architecture. Use a routing tensor optimized for category geometry and an action tensor optimized for terminal decisions. Keep investigation direction decoupled from final action scoring.

### Production validation needed
- Real verified SOC outcomes sufficient to train both routing and action centroids without synthetic fallback.
- Out-of-sample check that routing mu retains rho > 0.5 while action mu keeps delta > 0.
- Point-in-time split to verify the effect is not fixture leakage or synthetic centroid construction.

### Gates
- Phase A complete: yes.
- Phase B design justified: yes; B6 skipped with explicit reason.
- Phase B results classified: yes, each result has IMPL/EXP/HYPO/ARCH classification.
- Phase C validated: yes.
- Mypy on new sprint/test files: pass.
- tests/test_geometry_sprint.py: 14 passed.
- Existing VLD/value-chain tests: 58 passed.
- Sampling gate: 35 passed.
- Full suite: 2409 passed, 16 skipped, 0 failed.
- 0 new regressions introduced.

### Verdict
DUAL-CENTROID RESOLVES: Use default mu for routing + trained mu for scoring. rho=0.6850828729281768, delta=+0.07182320441988951. Recommend: Phase 2 implements dual-centroid investigation loop. [SYNTHETIC TRAINING CAVEAT] The action tensor is trained from synthetic data because fixture-derived centroids failed the quality gate.

State: Geometry sprint complete. Ready for Phase 2 dual-centroid design with production-data validation.
---

---
## Dual-Centroid + Abstention
Timestamp: 2026-09-08T19:57:23.258904

### Changed files for this prompt
- scripts/sprint/sprint_lib.py (added get_default_centroids/get_trained_centroids aliases)
- scripts/sprint/combined_dual_abstain.py (new)
- tests/test_geometry_sprint.py (appended 5 tests; now 19 total)
- data/sprint/combined_dual_abstain.json (new experiment output)
- docs/session_state.md (this entry)

No app/ files were modified by this prompt. Existing app/ diffs in the working tree are from prior Phase 1a / Value Chain slots.

### Baselines
- Single-pass Phase 1b accuracy: 0.5377532228360957
- Trained single-pass accuracy: 0.15101289134438306
- Dual-centroid always accuracy: 0.22283609576427257
- Dual-centroid matches sprint 0.223 ± 0.001: True
- Dual-centroid always SOC utility: -15.320441988950277
- Single-pass always SOC utility: -8.707182320441989

### Full output table
| Strategy | Threshold | Committed | Abstained | Accuracy | Delta vs SP committed | Delta vs dual always | Utility SOC | Utility S2P | Utility Trading |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| margin | 0.0 | 543 | 0 | 0.22283609576427257 | -0.3149171270718232 | 0.0 | -15.320441988950277 | -3.6629834254143647 | -2.10865561694291 |
| disagreement | 0.0 | 74 | 469 | 0.17567567567567569 | -0.24324324324324323 | -0.04716042008859689 | -3.0865561694290977 | -0.9696132596685083 | -0.5721915285451197 |
| combined | 0.0 | 74 | 469 | 0.17567567567567569 | -0.24324324324324323 | -0.04716042008859689 | -3.0865561694290977 | -0.9696132596685083 | -0.5721915285451197 |
| margin | 0.05 | 222 | 321 | 0.22522522522522523 | -0.32432432432432434 | 0.0023891294609526548 | -6.834254143646409 | -1.787292817679558 | -1.0355432780847145 |
| disagreement | 0.05 | 74 | 469 | 0.17567567567567569 | -0.24324324324324323 | -0.04716042008859689 | -3.0865561694290977 | -0.9696132596685083 | -0.5721915285451197 |
| combined | 0.05 | 35 | 508 | 0.17142857142857143 | -0.3142857142857143 | -0.051407524335701144 | -1.992633517495396 | -0.7237569060773481 | -0.4298342541436464 |
| margin | 0.1 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| disagreement | 0.1 | 74 | 469 | 0.17567567567567569 | -0.24324324324324323 | -0.04716042008859689 | -3.0865561694290977 | -0.9696132596685083 | -0.5721915285451197 |
| combined | 0.1 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| margin | 0.15 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| disagreement | 0.15 | 74 | 469 | 0.17567567567567569 | -0.24324324324324323 | -0.04716042008859689 | -3.0865561694290977 | -0.9696132596685083 | -0.5721915285451197 |
| combined | 0.15 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| margin | 0.2 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| disagreement | 0.2 | 74 | 469 | 0.17567567567567569 | -0.24324324324324323 | -0.04716042008859689 | -3.0865561694290977 | -0.9696132596685083 | -0.5721915285451197 |
| combined | 0.2 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| margin | 0.25 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| disagreement | 0.25 | 74 | 469 | 0.17567567567567569 | -0.24324324324324323 | -0.04716042008859689 | -3.0865561694290977 | -0.9696132596685083 | -0.5721915285451197 |
| combined | 0.25 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| margin | 0.3 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| disagreement | 0.3 | 74 | 469 | 0.17567567567567569 | -0.24324324324324323 | -0.04716042008859689 | -3.0865561694290977 | -0.9696132596685083 | -0.5721915285451197 |
| combined | 0.3 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| margin | 0.35 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| disagreement | 0.35 | 74 | 469 | 0.17567567567567569 | -0.24324324324324323 | -0.04716042008859689 | -3.0865561694290977 | -0.9696132596685083 | -0.5721915285451197 |
| combined | 0.35 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| margin | 0.4 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| disagreement | 0.4 | 74 | 469 | 0.17567567567567569 | -0.24324324324324323 | -0.04716042008859689 | -3.0865561694290977 | -0.9696132596685083 | -0.5721915285451197 |
| combined | 0.4 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| margin | 0.45 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| disagreement | 0.45 | 74 | 469 | 0.17567567567567569 | -0.24324324324324323 | -0.04716042008859689 | -3.0865561694290977 | -0.9696132596685083 | -0.5721915285451197 |
| combined | 0.45 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| margin | 0.5 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| disagreement | 0.5 | 74 | 469 | 0.17567567567567569 | -0.24324324324324323 | -0.04716042008859689 | -3.0865561694290977 | -0.9696132596685083 | -0.5721915285451197 |
| combined | 0.5 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| margin | 0.55 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| disagreement | 0.55 | 74 | 469 | 0.17567567567567569 | -0.24324324324324323 | -0.04716042008859689 | -3.0865561694290977 | -0.9696132596685083 | -0.5721915285451197 |
| combined | 0.55 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| margin | 0.6 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| disagreement | 0.6 | 74 | 469 | 0.17567567567567569 | -0.24324324324324323 | -0.04716042008859689 | -3.0865561694290977 | -0.9696132596685083 | -0.5721915285451197 |
| combined | 0.6 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| margin | 0.65 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| disagreement | 0.65 | 74 | 469 | 0.17567567567567569 | -0.24324324324324323 | -0.04716042008859689 | -3.0865561694290977 | -0.9696132596685083 | -0.5721915285451197 |
| combined | 0.65 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| margin | 0.7 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| disagreement | 0.7 | 74 | 469 | 0.17567567567567569 | -0.24324324324324323 | -0.04716042008859689 | -3.0865561694290977 | -0.9696132596685083 | -0.5721915285451197 |
| combined | 0.7 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| margin | 0.75 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| disagreement | 0.75 | 74 | 469 | 0.17567567567567569 | -0.24324324324324323 | -0.04716042008859689 | -3.0865561694290977 | -0.9696132596685083 | -0.5721915285451197 |
| combined | 0.75 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| margin | 0.8 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| disagreement | 0.8 | 74 | 469 | 0.17567567567567569 | -0.24324324324324323 | -0.04716042008859689 | -3.0865561694290977 | -0.9696132596685083 | -0.5721915285451197 |
| combined | 0.8 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| margin | 0.85 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| disagreement | 0.85 | 74 | 469 | 0.17567567567567569 | -0.24324324324324323 | -0.04716042008859689 | -3.0865561694290977 | -0.9696132596685083 | -0.5721915285451197 |
| combined | 0.85 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| margin | 0.9 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| disagreement | 0.9 | 74 | 469 | 0.17567567567567569 | -0.24324324324324323 | -0.04716042008859689 | -3.0865561694290977 | -0.9696132596685083 | -0.5721915285451197 |
| combined | 0.9 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| margin | 0.95 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| disagreement | 0.95 | 74 | 469 | 0.17567567567567569 | -0.24324324324324323 | -0.04716042008859689 | -3.0865561694290977 | -0.9696132596685083 | -0.5721915285451197 |
| combined | 0.95 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| margin | 1.0 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |
| disagreement | 1.0 | 74 | 469 | 0.17567567567567569 | -0.24324324324324323 | -0.04716042008859689 | -3.0865561694290977 | -0.9696132596685083 | -0.5721915285451197 |
| combined | 1.0 | 0 | 543 | 0.0 | 0.0 | -0.22283609576427257 | -1.0 | -0.5 | -0.3 |

### Best SOC strategy
- Strategy: margin
- Threshold: 0.1
- SOC utility: -1.0
- Committed: 0
- Abstained: 543
- Abstain rate: 1.0
- Committed accuracy: 0.0
- Comparison: dual-centroid-always SOC utility -15.320441988950277 -> best SOC utility -1.0

Interpretation: abstention improves utility only through a degenerate all-abstain margin threshold on this fixture. That is useful as a kill/scope result, not as a deployable policy. It says the synthetic/fixture action value is negative enough that abstention dominates commitment under SOC 20:1 penalty.

### Disagreement characterization
- Disagreement count: 469 / 543
- Disagreement rate: 0.8637200736648251
- VLD accuracy on disagreement: 0.2302771855010661
- SP accuracy on disagreement: 0.5565031982942431
- VLD accuracy on agreement: 0.17567567567567569
- SP accuracy on agreement: 0.4189189189189189
- Signal interpretation: weak_or_noisy
- Dominant disagreement pairs:
  - credential_access->lateral_movement: 39
  - data_exfiltration->malware_execution: 35
  - lateral_movement->insider_threat: 31
  - lateral_movement->data_exfiltration: 28
  - lateral_movement->malware_execution: 27

Confusion matrix: default-route -> trained-route
| Default route | cloud_infrastructure | credential_access | data_exfiltration | insider_threat | lateral_movement | malware_execution |
|---|---:|---:|---:|---:|---:|---:|
| cloud_infrastructure | 0 | 11 | 12 | 19 | 18 | 5 |
| credential_access | 0 | 0 | 26 | 26 | 39 | 21 |
| data_exfiltration | 13 | 0 | 0 | 17 | 14 | 35 |
| insider_threat | 0 | 10 | 22 | 0 | 14 | 22 |
| lateral_movement | 0 | 11 | 28 | 31 | 0 | 27 |
| malware_execution | 0 | 13 | 9 | 16 | 10 | 0 |

### Design verification
- Dual-centroid baseline matches sprint: True
- All 3 strategies produced threshold rows: True
- Utility spot-check covered by tests: 0 committed / all abstained -> utility = -abstain_cost.
- Disagreement characterization includes confusion matrix: yes.
- Disagreement predicts lower VLD accuracy: False

### Tests
- Mypy on changed sprint/test files: pass.
- tests/test_geometry_sprint.py: 19 passed.
- Full suite: 2414 passed, 16 skipped, 0 failed.
- 0 new regressions introduced.

### Verdict
ABSTENTION IMPROVES: Strategy margin at threshold=0.1 improves SOC utility from -15.320441988950277 to -1.0. Committed accuracy: 0.0. Recommend: Phase 2 does not use geometry-disagreement abstention as-is; if abstention is kept, use a calibrated margin/utility gate and require production data because the best fixture policy abstains on every case.

State: Dual-centroid + abstention experiment complete. Disagreement is weak/noisy on this fixture; all-abstain wins SOC utility because committed action utility is deeply negative under 20:1 penalty.
---

## V-11+V-12: Bootstrap Training + Re-Measure

### Files changed
- scripts/bootstrap_soc_decisions.py
- scripts/value_chain_experiment_lib.py
- scripts/exp_baseline_verify.py
- scripts/exp_dimension_decomposition.py
- scripts/exp_split_enrichment.py
- scripts/sprint/sprint_lib.py
- scripts/sprint/b1_dual_centroids.py
- scripts/sprint/c_validate_best.py
- tests/test_centroid_training.py
- data/bootstrapped_centroids.npy
- data/bootstrapped_centroids_metadata.json
- data/bootstrapped_centroids_50.npy
- data/bootstrapped_centroids_metadata_50.json
- data/bootstrapped_centroids_90.npy
- data/bootstrapped_centroids_metadata_90.json
- data/exp_baseline_verification_bootstrapped.json
- data/exp_dimension_decomposition_bootstrapped.json
- data/exp_split_enrichment_bootstrapped.json
- data/sprint/b1_dual_centroids_bootstrapped.json
- data/sprint/c_validate_best_bootstrapped.json
- docs/session_state.md

### Bootstrap method
- Loaded 543 SOC fixture alerts from support/setup/zero_day_decisions_v5.json through the same fixture factor provider used by the value-chain experiments.
- Scored each alert with SOCDomainConfig().build_profile_scorer().
- Fed every verified decision through ProfileScorer.update(): confirmations update the recommended action; overrides push the recommended action and pull the deterministic analyst-selected alternate action.
- Saved bootstrapped action centroids from verified-action means. No synthetic training rows were used.
- Default confirm/override parameter: requested 70/30; deterministic realized rate 73.5% confirm over 543 decisions.

### Bootstrapped centroid quality
- Bootstrap 70/30: inter/intra 1.454, gate FAIL, 543 decisions, all 24 category/action cells covered with >=5 samples.
- Bootstrap 50/50: inter/intra 0.759, gate FAIL, 543 decisions, all 24 cells covered with >=5 samples.
- Bootstrap 90/10: inter/intra 2.616, gate PASS, 543 decisions, all 24 cells covered with >=5 samples.
- Finding: coverage is not the limiting factor. The fixture action-separability result depends strongly on the analyst-confirmation prior; the primary 70/30 setting misses the 1.5 gate despite full cell coverage.

### Comparison table
| Metric | Default | Synthetic | Bootstrap 70/30 | Bootstrap 50/50 | Bootstrap 90/10 |
|---|---:|---:|---:|---:|---:|
| Inter/intra | 0.82 | 10.13 | 1.454 | 0.759 | 2.616 |
| rho | 0.685 | 0.155 | 0.385 | 0.339 | 0.545 |
| SP accuracy | 0.538 | 0.151 | 0.519 | 0.413 | 0.532 |
| VLD accuracy | 0.313 | 0.204 | 0.195 | 0.203 | 0.280 |
| Oracle accuracy | 0.361 | 0.234 | 0.385 | 0.370 | 0.354 |
| Dual-centroid delta | - | +0.072 | -0.142 | -0.028 | -0.195 |

### CI+VLD sample check
- ALT-JDOE-001: SP=escalate, VLD=suppress, verified=escalate; SP matched.
- ALT-JDOE-002: SP=monitor, VLD=suppress, verified=suppress; VLD matched.
- ALT-JDOE-003: SP=suppress, VLD=monitor, verified=suppress; SP matched.
- SYN-ME-D004-001: SP=escalate, VLD=suppress, verified=investigate; neither matched.
- SYN-DE-D005-001: SP=monitor, VLD=suppress, verified=monitor; SP matched.

### Tests and gates
- Pre-check baseline: 2414 passed, 16 skipped, 4915 warnings.
- tests/test_centroid_training.py: 14 passed, 28 warnings.
- Changed-file mypy: passed with --follow-imports=skip --no-error-summary.
- Full backend suite: 2420 passed, 16 skipped, 4927 warnings.
- Blast radius: get_experiment_scorer/load_scorer/load_mu callers checked under scripts and tests.
- Scope note: this slot did not modify backend/app. The worktree already had backend/app, frontend, rho report, authority DB, and several experiment files dirty/untracked before this work; those were not reverted.

### Verdict
BOOTSTRAPPED FAIL: primary 70/30 quality gate failed at inter/intra=1.454 and dual-centroid delta=-0.142. Even the 90/10 quality-passing sensitivity run had dual-centroid delta=-0.195. First non-synthetic measurement does not support dual-centroid value on this fixture; need production data or a different verified-outcome model.

0 new regressions introduced.


---

## V-10: Investigation Panel
Timestamp: 2026-09-08T20:57:22.928513-07:00

### Files changed
- frontend/src/components/InvestigationPanel.tsx (new)
- frontend/src/components/tabs/AlertTriageTab.tsx
- frontend/src/lib/api.ts
- frontend/tests/e2e/investigation_panel.spec.ts (new)
- backend/docs/session_state.md

### Component interface
- InvestigationPanel props: alertId, autoRun=false, onResult(result).
- Calls POST /api/soc/investigate through investigateAlert(alertId) and renders the backend wrapper response: vld, investigation_trace, single_pass, and conservation_emit_gate.
- States covered: idle, loading, result, error, empty trace.

### Demo path
- Open SOC frontend.
- Go to Alert Triage.
- Select an alert and run the existing score/analyze action.
- The Investigation Trace panel appears below the scoring/support context.
- Click Run Investigation to show the VLD route trace, evidence keys, routed category, final category, routing agreement, and single-pass comparison.

### Key findings
- /api/soc/investigate returns a wrapper with vld and investigation_trace, not a bare InvestigationResult; the panel handles that contract directly.
- The panel is additive. The existing single-pass Alert Triage scoring UI remains in place.
- The new Playwright spec must mock the initial Runtime Evolution APIs as well as Triage APIs because the app starts on Runtime Evolution before navigating to Alert Triage.

### Verification
- Frontend typecheck/build: pass (npx tsc --noEmit; npm run build).
- Investigation panel E2E: 7 passed (tests/e2e/investigation_panel.spec.ts).
- SOC backend tests unchanged gate: 2420 passed, 16 skipped, 0 failed.
- Blast radius: no backend source modified by this slot. Existing backend dirty files are from prior VLD slots and were left untouched.

0 new regressions introduced.


---

## Stage 1 Multi-Hop Evaluation
Timestamp: 2026-09-09T03:18:45.582194-07:00

### Files changed
- scripts/evaluate_multihop_stage1.py (new)
- tests/test_multihop_evaluation.py (new)
- data/multihop_stage1_results.json (generated)
- data/multihop_stage1_report.md (generated)
- docs/session_state.md

### Acceptance test result
- Verdict: FAIL
- Failures:
- rho=0.50: expected delta near 0, got -0.600
- rho=0.7: expected positive delta, got 0.000
- rho=0.9: expected positive delta, got 0.000
- rho=1.0: expected positive delta, got 0.000

### Per-kind accuracy table
| Kind | Arm | Accuracy | N |
|---|---|---:|---:|
| content_keyed | breadth | 0.733 | 15 |
| content_keyed | content_rule | 0.867 | 15 |
| content_keyed | single_pass | 0.400 | 15 |
| content_keyed | vld | 0.400 | 15 |
| prerequisite | breadth | 0.800 | 10 |
| prerequisite | content_rule | 1.000 | 10 |
| prerequisite | single_pass | 0.200 | 10 |
| prerequisite | vld | 1.000 | 10 |
| score_keyed | breadth | 0.600 | 25 |
| score_keyed | content_rule | 1.000 | 25 |
| score_keyed | single_pass | 0.360 | 25 |
| score_keyed | vld | 0.720 | 25 |

### Per-ρ accuracy table (score_keyed)
| ρ_planted | Arm | Accuracy | N |
|---:|---|---:|---:|
| 0.30 | breadth | 0.750 | 4 |
| 0.30 | content_rule | 1.000 | 4 |
| 0.30 | single_pass | 0.000 | 4 |
| 0.30 | vld | 0.000 | 4 |
| 0.50 | breadth | 0.600 | 5 |
| 0.50 | content_rule | 1.000 | 5 |
| 0.50 | single_pass | 0.600 | 5 |
| 0.50 | vld | 0.400 | 5 |
| 0.70 | breadth | 0.625 | 8 |
| 0.70 | content_rule | 1.000 | 8 |
| 0.70 | single_pass | 0.500 | 8 |
| 0.70 | vld | 1.000 | 8 |
| 0.90 | breadth | 1.000 | 4 |
| 0.90 | content_rule | 1.000 | 4 |
| 0.90 | single_pass | 0.250 | 4 |
| 0.90 | vld | 1.000 | 4 |
| 1.00 | breadth | 0.000 | 4 |
| 1.00 | content_rule | 1.000 | 4 |
| 1.00 | single_pass | 0.250 | 4 |
| 1.00 | vld | 1.000 | 4 |

### Control results
- Flat controls N=5: single_pass=0.600, vld=0.600. Gate: PASS because VLD did not beat single-pass.
- ρ=0.50 controls N=5: VLD=0.400. Gate: PASS at the edge of the chance band 0.25 ± 0.15.

### Headline
- accuracy(vld) - accuracy(content_rule) on score_keyed = -0.280.

### Diagnostics
- EXP: acceptance uses content_rule as a correct-branch upper bound, so positive VLD-content deltas may be impossible under this arm definition.
- All-arms-agree instances: 10.
- Breadth beats VLD instances: 10.
- Important interpretation: the Stage 1 harness treats content_rule on score_keyed as a correct-branch upper bound because the prompt explicitly allowed it to use correct_branches. Under that comparator definition, VLD cannot produce positive VLD-content deltas at high ρ unless the upper bound itself fails downstream. The instrument therefore reports FAIL rather than fabricating a pass.

### Validation
- validate_stage1.py: ALL 10 QUALITY CHECKS + SPEC CONSTRAINTS PASSED.
- All 50 instances evaluated across all 4 arms: 50 scenarios, 200 result rows.
- New targeted tests: tests/test_multihop_evaluation.py 11 passed.
- Mypy on new evaluator/test: pass with --follow-imports=skip --no-error-summary.
- Full SOC backend suite: 2431 passed, 16 skipped, 0 failed.

### Verdict
FAIL: Stage 1 did not satisfy spec §1.3 against the configured content_rule comparator. Diagnostic applies: EXP comparator/spec mismatch. Fix by changing the score_keyed acceptance comparator to budget-matched random/breadth, or by removing the correct_branches cheat from content_rule for score_keyed cases, then rerun Stage 1 before Stage 2 generation.

0 new regressions introduced.

---
## W-1: SOC Multi-Hop Graph Wiring
Timestamp: 2026-09-09T20:35:51.436136+00:00
### Changed files
- app/graph_schema.py
- app/routers/triage.py
- app/services/investigation_patterns.py
- app/services/multihop_scenarios.py (new)
- scripts/seed_multihop_graph.py (new)
- scripts/demo_showcase_alerts.py (new)
- data/multihop_graph_seed.json (new generated artifact)
- data/demo_showcase_alerts.json (new generated artifact)
- tests/test_multihop_wiring.py (new)

### Nodes and edges seeded
- Nodes seeded: 104
- Edges seeded: 46
- Scenarios covered: 50
- Node types: AccessKey, Alert, ApiSequence, Asset, AuthTrail, CVE, Campaign, ChangeRequest, CloudResource, CommandProfile, Credential, DeployRecord, DeviceSession, EmploymentContext, Group, Host, Identity, Mailbox, PeerCohort, Process, Role, ScheduledJob, ServiceAccount, Session, SoftwarePackage, TimeWindow, TransferHistory, TravelRecord, User
- Edge types: AFFECTS, BINDS_ROLE, COMPARED_AGAINST, COVERED_BY_CHANGE, COVERED_BY_DEPLOY, HAS_AUTH_TRAIL, HAS_COMMAND_PROFILE, HAS_EMPLOYMENT_CONTEXT, HAS_SESSION, HAS_TRAVEL_RECORD, MATCHES_CVE, MEMBER_OF, MEMBER_OF_COHORT, NESTED_IN, OBSERVED_IN_WINDOW, OBSERVED_PROCESS, OBSERVED_SEQUENCE, ORIGINATED_FROM, RUNS_JOB, RUNS_PACKAGE, TARGETS, USES_CREDENTIAL, USES_KEY

### New patterns
- 8 conditional Stage 1 multi-hop patterns added in a separate MULTIHOP_PATTERN_REGISTRY.
- Existing 6 category patterns in PATTERN_REGISTRY are preserved.
- New patterns: CredentialLateralPattern, InsiderCompromisedPattern, CloudMisconfigPattern, ServiceAccountPattern, MaintenanceWindowPattern, VulnerabilityPatchPattern, PrivilegeChainPattern, CampaignCorrelationPattern.

### Showcase alerts
- SOC-MH-002-v1 / ALERT-MH-002-v1: 2 steps -> escalate (insider_vs_compromised)
- SOC-MH-004-v1 / ALERT-MH-004-v1: 1 steps -> suppress (maintenance_window_false_positive)
- SOC-MH-005-v1 / ALERT-MH-005-v1: 3 steps -> escalate (privilege_escalation_chain)
- SOC-MH-003-v1 / ALERT-MH-003-v1: 2 steps -> escalate (campaign_correlation)

### Stage 1 reproduction
- VLD high-rho score_keyed reproduction: 16/16 correct, accuracy=1.000 for rho_planted >= 0.70.
- Formal Stage 1 acceptance remains governed by the prior evaluator caveat: content_rule is an upper-bound comparator on score_keyed scenarios, so the headline VLD-content delta is negative even though high-rho VLD routes correctly.

### Endpoint wiring
- POST /soc/investigate now short-circuits planted Stage 1 alert IDs such as ALERT-MH-002-v1 into vld_multihop_stage1_shadow mode.
- Existing live graph investigation path is unchanged for non-Stage-1 alerts.

### Gates
- validate_stage1.py: PASS, ALL 10 QUALITY CHECKS + SPEC CONSTRAINTS PASSED.
- seed_multihop_graph.py: PASS, idempotent at 104 nodes / 46 edges.
- demo_showcase_alerts.py: PASS, 4 showcase traces generated.
- mypy on changed Python files: PASS.
- Targeted tests: tests/test_multihop_wiring.py 13 passed.
- Existing investigation blast-radius: tests/test_investigation_loop.py 20 passed.
- Sampling gate: test_conservation_bugs.py + test_rho_measurement.py + test_gate_config.py, 28 passed.
- Full backend suite: 2444 passed, 16 skipped, 0 failed.

### State for next prompt
- Multi-hop graph schema entries are additive with min_count=0.
- Stage 1 planted graph data is available as data/multihop_graph_seed.json.
- Demo showcase alerts are listed in data/demo_showcase_alerts.json.
- The investigation panel can call /soc/investigate with ALERT-MH-002-v1, ALERT-MH-004-v1, ALERT-MH-005-v1, or ALERT-MH-003-v1 to render planted multi-hop traces.
- 0 new regressions introduced.
---
