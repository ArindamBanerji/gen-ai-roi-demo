
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
