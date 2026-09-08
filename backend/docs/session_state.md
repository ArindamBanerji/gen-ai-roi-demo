
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
