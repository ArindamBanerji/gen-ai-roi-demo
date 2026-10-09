# ASTRA-SWEEP-SOC — Post-SS campaign review

Date: 2026-09-27T14:57:22-07:00 (America/Los_Angeles)  
Repository: `gen-ai-roi-demo-v4-v50`  
Reviewed checkout HEAD: `8b0851c9fb4bcfb4b3443ad52828b93a95c21517`, including the existing uncommitted campaign changes.

**Verdict: FINDINGS — 6 P1, 14 P2, 0 P3.** The requested validation matches the baseline exactly: **2,669 passed / 0 failed / 0 skipped**, mypy passes, and frontend TypeScript passes. These passing checks do not cover the partial-failure contracts identified below.

## Scope and method

This was a review-only sweep. No application or test source was changed. The report and session summary are the requested documentation writes; local validation logs and fault-probe results were also retained. The requested tests exercise their existing database and fixture side effects.

Reviewed all 48 changed production Python files in the working-tree campaign diff, changed/new tests, response models, and downstream callers. The function inventory appears below. Also reviewed the explicitly requested centroid-support, composite-gate, verification-health and triage critical paths, including relevant code already present in HEAD. Findings marked “carryover” are not claimed to have been introduced by the current diff.

Prompt attribution follows `backend/docs/session_state.md` and `docs/session_state.md`. Their actual file mapping differs from the request's shorthand: campaign code lives in `app/domains/soc/campaigns.py`; SS-13 covers graph/metrics/threat/evidence writes; SS-14 covers reports/analytics/exploration. The earlier C3/C4 records cover several named critical checks. There is no corresponding current SOC `services/security.py`/SAP/Celonis change to attribute to these prompts.

Inspection followed failure sentinels through helper, caller and HTTP model boundaries; scanned broad exception/default patterns and graph test doubles; and used isolated monkeypatched probes without real endpoint writes. Probe evidence is stated per finding. This was not an instrumented branch-coverage run, and a passing helper test is not treated as proof of the consuming HTTP contract.

## Validation

| Check | Result |
| --- | --- |
| Backend: `python -m pytest tests/ -q --timeout=120` | **2,669 passed / 0 failed / 0 skipped**; 5,392 warnings; 784.70 seconds |
| Backend: `python -m mypy app/ --config-file pyproject.toml` | **PASS**, no issues in 205 source files |
| Frontend: `npx tsc --noEmit` | **PASS**, exit 0 |
| Regression against 2,669 / 0 / 0 baseline | **None in the requested validation** |

The full pytest run reached 100%; no chunk was interrupted or excluded. Existing deprecation warnings account for the reported warnings. The correctness findings below are uncovered failure-path defects, not failed baseline tests.

Local execution evidence: [pytest log](../.codex_tmp/astra_sweep_soc_pytest.log), [mypy log](../.codex_tmp/astra_sweep_soc_mypy.log), [TypeScript log](../.codex_tmp/astra_sweep_soc_tsc.log), [fault-probe results](../.codex_tmp/astra_sweep_soc_probes.json), [mock scan](../.codex_tmp/astra_sweep_soc_mock_scan.txt). The relevant results are embedded in this report so the permanent record does not depend on those temporary logs.

## P1 — Correctness

### SOC-01 — Bootstrap-read failure produces an invalid response; missing support data can still be labelled GREEN.

- **FILE:** `backend/app/routers/soc.py:4411`; `backend/app/models/responses.py:329`
- **FUNCTION:** `get_centroid_support`
- **SEVERITY:** P1
- **ISSUE:** Bootstrap-read failure produces an invalid response; missing support data can still be labelled GREEN.
- **DETAIL:** The exception branch returns warning_count=None and omits the required interpretation string. CentroidSupportResponse requires an integer and a string, so FastAPI rejects the intended degraded payload. Its status/reason fields are also absent from the response model. Separately, scorer=None or a missing bootstrap still returns overall_health='GREEN' and 'All centroids within data support region.' without having measured support. Preserve warning_count=0 and interpretation as a string, declare availability metadata in the model, and distinguish unavailable/unqualified support from measured GREEN.
- **SS-PROMPT:** SS-09 review scope; P1-095 was recorded under C4-SILENT-SUB (carryover, not a newly introduced SS-09 hunk)
- **EVIDENCE:** An isolated FastAPI request with a failing bootstrap read returned HTTP 500. ResponseValidationError identified warning_count and interpretation. The missing-baseline GREEN branch is directly visible in _COLD_START.

### SOC-02 — The degraded centroid export changes iks_score from a number to null.

- **FILE:** `backend/app/routers/soc.py:4243`; `backend/tests/test_soc_degraded_paths.py:136`
- **FUNCTION:** `get_centroid_export; test_centroid_export_does_not_use_zero_iks`
- **SEVERITY:** P1
- **ISSUE:** The degraded centroid export changes iks_score from a number to null.
- **DETAIL:** iks_score is now initialized to None and remains None on an IKS exception or missing score. iks_available=False and degraded=True are useful separate fields, but do not make changing the existing numeric field's type safe. Keep a numeric 0.0 at the HTTP boundary while preserving the failure flag. The new test explicitly asserts None and therefore enforces the opposite of the requested contract.
- **SS-PROMPT:** SS-09
- **EVIDENCE:** Source inspection of the export assembly and the new degraded-path assertion.

### SOC-03 — An unavailable IKS result turns the entire timeline HTTP response into JSON null.

- **FILE:** `backend/app/services/time_machine.py:363`; `backend/app/routers/time_machine_router.py:68`
- **FUNCTION:** `get_evolution_timeline; get_timeline_endpoint`
- **SEVERITY:** P1
- **ISSUE:** An unavailable IKS result turns the entire timeline HTTP response into JSON null.
- **DETAIL:** The service now returns None when the IKS interpretation is unavailable. The unchanged router directly returns that value and only handles RuntimeError. A response that normally contains timeline, current, ceiling metadata, categories, actions and factors is therefore replaced by null, also discarding independently gathered snapshot data. Handle None at the router boundary with the established field types and explicit availability metadata; preserve available partial data.
- **SS-PROMPT:** SS-14
- **EVIDENCE:** A read-only fault-injection probe of the route returned None when compute_iks_v2 raised.

### SOC-04 — Failed investigation reads still inject synthetic evidence into the scoring vector.

- **FILE:** `backend/app/services/investigation_patterns.py:86`; `backend/app/services/investigation_loop.py:74`; `backend/app/services/triage_providers.py:21`
- **FUNCTION:** `BaseInvestigationPattern.execute; InvestigationLoop.investigate; EvidenceScopedGraphAdapter.__init__; _apply_vld_reextraction`
- **SEVERITY:** P1
- **ISSUE:** Failed investigation reads still inject synthetic evidence into the scoring vector.
- **DETAIL:** execute marks evidence_available=False/degraded=True after a bounded graph-read failure but still returns the pattern's nonempty vld_factor_vector. InvestigationLoop unconditionally admits that evidence, and EvidenceScopedGraphAdapter accepts it without checking availability. Re-extraction consequently alters the vector and can alter the decision using evidence that was never fetched. The trace does not preserve these availability fields as an explicit degradation result. Exclude unavailable evidence, preserve the preceding vector, and report the failed investigation or halt reason.
- **SS-PROMPT:** SS-14
- **EVIDENCE:** With a failing graph, the credential pattern returned evidence_available=False and vector [0.88,0,0,0.72,0,0]. Re-extraction changed a [0.5,0.5,0.5,0.5,0.5,0.5] surface to [0.69,0.25,0.25,0.61,0.25,0.25].

### SOC-05 — A failed factor lookup can still persist a fabricated neutral Decision.factor_vector.

- **FILE:** `backend/app/routers/triage.py:1809`; `backend/app/services/triage.py:242`
- **FUNCTION:** `execute_action; get_decision_factors`
- **SEVERITY:** P1
- **ISSUE:** A failed factor lookup can still persist a fabricated neutral Decision.factor_vector.
- **DETAIL:** execute_action initializes six factors to 0.5, keeps them when get_decision_factors returns None, and also swallows exceptions from that helper. It then creates a Decision node with that vector and reports the action flow normally. A partial graph outage that affects factor reads but permits the later write therefore stores invented evidence in the decision history. Reject or explicitly defer the factor-dependent write; do not persist an ordinary valid vector for unavailable factors. The safer analyze path does not protect this separate action endpoint.
- **SS-PROMPT:** SS-08 / SS-12 triage-file review; explicitly requested P1-129/P1-130 check, originally recorded under C3-SILENT-SUB (carryover)
- **EVIDENCE:** Source trace from the default at line 1809 through the guarded helper call to CREATE Decision and factor_vector serialization near line 1856. No real action/write was invoked by the review.

### SOC-06 — An exception from the secondary indicator service triggers UnboundLocalError in the degraded response.

- **FILE:** `backend/app/routers/graph.py:400`
- **FUNCTION:** `get_enrichment_summary`
- **SEVERITY:** P1
- **ISSUE:** An exception from the secondary indicator service triggers UnboundLocalError in the degraded response.
- **DETAIL:** ti_summary is assigned only inside the try. If ThreatIndicatorService.get_all_indicators raises, the except branch creates typed threat_indicators defaults, but the return then evaluates ti_summary to compute availability. This raises instead of returning the degraded result. Initialize state before the try and base flags on whether the secondary read and processing succeeded. A malformed non-None summary can similarly enter the except branch while still being reported available.
- **SS-PROMPT:** SS-13 (graph/metrics changes, as recorded in the repository)
- **EVIDENCE:** Primary enrichment read succeeded with []; a patched secondary service raised. The handler raised UnboundLocalError: cannot access local variable 'ti_summary' where it is not associated with a value. Ordinary secondary query failures that the service converts to None take a different, non-crashing branch.

## P2 — Observability and test-quality gaps

### SOC-07 — The timeline caller collapses the new campaign failure sentinel back into an unmarked empty list.

- **FILE:** `backend/app/routers/soc.py:2031`
- **FUNCTION:** `get_campaign_timeline`
- **SEVERITY:** P2
- **ISSUE:** The timeline caller collapses the new campaign failure sentinel back into an unmarked empty list.
- **DETAIL:** The handler uses await repo.get_campaigns(...) or [], then returns a bare timeline list. Repository None on a failed read is indistinguishable from a successful empty graph. Carry availability to an explicit supported response contract, or return a deliberate service-unavailable error for this legacy list endpoint. Do not convert the failure sentinel into successful emptiness.
- **SS-PROMPT:** SS-08 / SS-12 campaign changes
- **EVIDENCE:** Fault injection of the repository read produced [] with no degradation metadata.

### SOC-08 — Category-history outages are still explained as insufficient experience.

- **FILE:** `backend/app/framework/composite_gate.py:116`
- **FUNCTION:** `CompositeDiscriminant.evaluate`
- **SEVERITY:** P2
- **ISSUE:** Category-history outages are still explained as insufficient experience.
- **DETAIL:** The catch for get_category_stats creates cat_count=0, rolling_accuracy=0.5 and verified_count=0. The gate then returns an ordinary maturity rejection such as 'cat_count 0 < 50' with no history availability flag. It fails closed for approval, but misreports the reason and makes an outage indistinguishable from an immature category. Retain conservative approval behavior and emit a graph-history-unavailable reason plus separate metadata through the triage response.
- **SS-PROMPT:** SS-11 framework review scope; explicitly requested category-history fallback check (carryover)
- **EVIDENCE:** Failing history probe returned auto_approve=False and reason_codes=['cat_count 0 < 50 (maturity gate)']; no unavailable status was returned.

### SOC-09 — Rules that return the new failure sentinel can leave scan_complete=True and degraded=False.

- **FILE:** `backend/app/services/variant_generator.py:777`; `backend/app/routers/admin.py:435`
- **FUNCTION:** `VariantGenerator.scan_for_opportunities; admin_evolution_scan`
- **SEVERITY:** P2
- **ISSUE:** Rules that return the new failure sentinel can leave scan_complete=True and degraded=False.
- **DETAIL:** The scanner only marks scan_complete=False for thrown exceptions. For last_data_available=False it recognizes class names containing plateau or drift, but entirely drops CoverageGapRule's failure. An unavailable coverage scan consequently looks like a successful scan with no opportunities. Aggregate unavailable rule outcomes consistently into rules_failed/scan_complete and the endpoint flag. History None also leaves the aggregate flag unchanged and is converted to action='proceed'; history availability should remain explicit and history-dependent generation should have an intentional failure policy.
- **SS-PROMPT:** SS-15
- **EVIDENCE:** A real CoverageGapRule with BrokenGraph reported last_data_available=False, yet the aggregate had all availability booleans True, scan_complete=True, rules_failed=[] and no variants.

### SOC-10 — The executive tab discards the narrative's sections_degraded metadata.

- **FILE:** `backend/app/routers/soc.py:3580`; `backend/app/services/executive_narrative.py`
- **FUNCTION:** `_tab5_content; build_executive_narrative_async`
- **SEVERITY:** P2
- **ISSUE:** The executive tab discards the narrative's sections_degraded metadata.
- **DETAIL:** The narrative now returns sections_degraded for failed reads. _tab5_content copies narrative text but does not merge those sections into its own degraded_fields or expose them separately. If its other reads succeed, it returns data_available=True despite narrative fetch failures. Preserve and aggregate the narrative availability information at this HTTP-facing composition boundary.
- **SS-PROMPT:** SS-09 / SS-14
- **EVIDENCE:** Injected narrative with sections_degraded=['what_changed','campaigns_detected'] and healthy other dependencies yielded data_available=True, degraded_fields=[] and no sections_degraded field.

### SOC-11 — The boolean wrapper erases graph failures for asset and pattern-history provenance.

- **FILE:** `backend/app/domains/soc/orchestrator.py:184`
- **FUNCTION:** `_query_has_rows; _factor_provenance`
- **SEVERITY:** P2
- **ISSUE:** The boolean wrapper erases graph failures for asset and pattern-history provenance.
- **DETAIL:** _query_rows correctly returns None on failure, but _query_has_rows returns bool(rows). Its asset_criticality and pattern_history callers therefore take the same fixture_fallback branch for a failed query and for a successful query with no rows. The threat-intel branch received explicit handling; these other callers did not. Preserve the tri-state result and label unavailable provenance separately from a legitimate fixture fallback.
- **SS-PROMPT:** SS-13
- **EVIDENCE:** Failing asset provenance query produced source='fixture_fallback', detail='neutral asset default', value=0.5, with no unavailable metadata.

### SOC-12 — A later successful variant flush clears an earlier failure in the same batch.

- **FILE:** `backend/app/services/shadow_runner.py:172`
- **FUNCTION:** `_flush_shadow_batch`
- **SEVERITY:** P2
- **ISSUE:** A later successful variant flush clears an earlier failure in the same batch.
- **DETAIL:** flush_failed is set True on a failed variant write and reset False after each successful variant write. Failed records remain buffered, so the final flag depends on iteration order rather than batch success. Also, repository search found no production consumer of this new flag, so it does not reach the existing result/status surfaces. Aggregate failures across the batch, retain pending-write diagnostics, and expose them to a caller or status endpoint.
- **SS-PROMPT:** SS-15
- **EVIDENCE:** An isolated two-variant probe failed the first write and succeeded on the second. It ended with flush_failed=False and 25 failed records still pending.

### SOC-13 — The balance sheet still substitutes an unavailable IKS score with an unmarked zero.

- **FILE:** `backend/app/services/balance_sheet.py:108`
- **FUNCTION:** `_safe_overall_iks; generate_balance_sheet`
- **SEVERITY:** P2
- **ISSUE:** The balance sheet still substitutes an unavailable IKS score with an unmarked zero.
- **DETAIL:** _safe_overall_iks now explicitly maps compute_visible_iks(None result) to 0.0, and its exception branch also returns 0.0. LearningBalanceSheet has availability flags for centroid drift, auto approval and timeline, but none for overall IKS. A failed IKS query therefore becomes an apparently measured overall score and can feed derived contributions. Preserve None inside the helper, then emit a typed numeric default plus an IKS availability flag in the report.
- **SS-PROMPT:** SS-14
- **EVIDENCE:** Source inspection of the helper, dataclass and report assembly.

### SOC-14 — The new override-detector load-failure flag never reaches the learning display.

- **FILE:** `backend/app/services/override_detector.py:43`; `backend/app/routers/soc.py:3040`
- **FUNCTION:** `load_from_graph; _tab2_content`
- **SEVERITY:** P2
- **ISSUE:** The new override-detector load-failure flag never reaches the learning display.
- **DETAIL:** load_from_graph correctly sets graph_loaded=False and preserves previous examples on a read failure. The tab only inspects activated and example_count, so it reports a normal inactive detector on cold failure or a normal active detector with stale data. Repository-wide production search found graph_loaded only at its definition and assignments, with no reader. Expose the load failure/staleness and include it in the tab's degraded fields.
- **SS-PROMPT:** SS-14 / SS-09
- **EVIDENCE:** Search for graph_loaded and source trace through _tab2_content.

### SOC-15 — Historical-context query failures do not affect the compounding response's availability flags.

- **FILE:** `backend/app/routers/metrics.py:241`
- **FUNCTION:** `get_compounding_metrics`
- **SEVERITY:** P2
- **ISSUE:** Historical-context query failures do not affect the compounding response's availability flags.
- **DETAIL:** When measured weekly buckets are all zero, the endpoint queries older synthetic-decision context. That catch only logs and leaves historical data absent. data_available is later calculated solely from weekly_available and evolution_available, so this partial failure is reported as fully available. Add a historical-context availability flag, and aggregate it only when that optional lookup was actually attempted.
- **SS-PROMPT:** SS-13
- **EVIDENCE:** Source trace from the _all_zero historical query branch to final data_available/degraded assignment.

### SOC-16 — The campaign fixture does not own an isolated disposable campaign.

- **FILE:** `backend/tests/test_campaign_frontend.py:26`
- **FUNCTION:** `campaign_contract_fixture; campaign list/detail contract tests`
- **SEVERITY:** P2
- **ISSUE:** The campaign fixture does not own an isolated disposable campaign.
- **DETAIL:** It uses one fixed campaign ID in the global application graph. If that ID already exists, setup returns without creating anything, but teardown always deletes it. Concurrent sessions can reuse and delete each other's row. Several tests then recorrelate shared data and inspect campaigns[0], not the fixture's row, so successful assertions need not exercise the seeded campaign. Use a unique test-owned ID and preferably an isolated graph; clean up only owned data and explicitly select the fixture campaign.
- **SS-PROMPT:** FIX-SOC-SKIPS
- **EVIDENCE:** Setup's existing-row early return, unconditional DETACH DELETE teardown, and selection of the first listed campaign. Normal module teardown is present; the issue is ownership/isolation, not absence of cleanup.

### SOC-17 — The stable SOC DSN is not used for the fixture's preliminary availability check.

- **FILE:** `backend/tests/conftest.py:90`; `../copilot-sdk/copilot_sdk/testing/fixtures.py:23`
- **FUNCTION:** `soc_stress_test_graph; age_available`
- **SEVERITY:** P2
- **ISSUE:** The stable SOC DSN is not used for the fixture's preliminary availability check.
- **DETAIL:** The fixture connects using captured _SESSION_GRAPH_DSN, correctly sourced from application SOC configuration or explicit test settings. Before doing so, however, it calls imported age_available(), which resolves AGE_TEST_DSN or GraphConfig.load('trading') and caches that result. With different SOC/trading destinations, the fixture can skip a reachable SOC database based on another destination. Probe the same captured DSN that the fixture will actually use.
- **SS-PROMPT:** FIX-SOC-SKIPS
- **EVIDENCE:** Source comparison of the fixture and SDK helper. This is a configuration-dependent defect; the present validation environment can still pass.

### SOC-18 — Live tests can validate an unrelated server, and startup failures are converted into skips.

- **FILE:** `backend/tests/conftest.py:141`
- **FUNCTION:** `pytest_collection_modifyitems; pytest_sessionfinish`
- **SEVERITY:** P2
- **ISSUE:** Live tests can validate an unrelated server, and startup failures are converted into skips.
- **DETAIL:** Any HTTP 200 at fixed port 8001 is accepted without checking code/session identity; thus these tests need not exercise the checkout under review. When a server is spawned it inherits the pre-fixture environment: the function-scoped SOC_PROFILE=test fixture has not run during collection. Startup errors are hidden by DEVNULL and, after the 30-second poll, tests are skipped rather than failing the promised zero-skip gate. Use a test-configured owned server or verify an explicitly supplied server, retain diagnostics, and fail required-live-test setup on startup failure. Teardown terminates/waits, but the kill fallback should also wait/reap.
- **SS-PROMPT:** FIX-SOC-SKIPS
- **EVIDENCE:** Source inspection. A 30-second health deadline and normal owned-process cleanup do exist; no actual startup failure or orphan process is claimed for this run.

### SOC-19 — Several advertised outage tests never exercise or assert the failure they claim to cover.

- **FILE:** `backend/tests/test_ss15_variant_rl_degraded.py:83`; `backend/tests/test_ss13_graph_metrics_degraded.py:62`; `backend/tests/test_ss14_reports_analytics_degraded.py`
- **FUNCTION:** `test_shadow_batch_flush_failure; test_seed_graph_partial_failure; test_executive_narrative_partial_failure`
- **SEVERITY:** P2
- **ISSUE:** Several advertised outage tests never exercise or assert the failure they claim to cover.
- **DETAIL:** The shadow test empties the buffer, returns before any write, and only checks hasattr(flush_failed). The seed test supplies empty datasets and asserts failed_count==0/seeding_complete=True, so its failing writer is never exercised. The executive narrative test only asserts that sections_degraded is a list, allowing an empty list on failure. Many helper-only tests do not verify the final HTTP schema, which missed SOC-01 through SOC-03 and lost flags. Trigger nonempty failing operations, assert the expected failed component, and verify both typed defaults and flags through the consuming boundary.
- **SS-PROMPT:** SS-13 / SS-14 / SS-15; FIX-SOC coverage review
- **EVIDENCE:** Direct inspection of these test bodies; the shadow mixed-success probe demonstrates a defect the existing test misses. This is not a claim of measured line/branch coverage.

### SOC-20 — Happy-path mocked graph stores remain outside the error-path-double exception.

- **FILE:** `backend/tests/test_fix_05_06_07.py:97`; `backend/tests/test_override_detector.py:85`
- **FUNCTION:** `test_simulation_does_not_mutate_production_state; test_simulation_empty_pool_returns_gracefully; test_load_from_graph_activates_with_50_results; test_load_from_graph_inactive_with_49_results`
- **SEVERITY:** P2
- **ISSUE:** Happy-path mocked graph stores remain outside the error-path-double exception.
- **DETAIL:** The simulation tests construct the scorer with a MagicMock graph_store; the override-detector success tests use AsyncMock graph reads returning 50/49 fabricated rows. These are normal-state paths, not injected read/write failures. They cannot verify real store persistence or query semantics and do not satisfy the requested zero non-error graph-store-mock check. Use InMemoryGraphStore for scorer state and the existing real AGE fixture/adapters for graph-query behavior. Keep targeted failure doubles and non-graph scorer/narrator mocks.
- **SS-PROMPT:** FIX-SOC mock-cleanup/coverage requirement (remaining pre-existing tests)
- **EVIDENCE:** Full backend mock scan plus inspection of these concrete success-path uses. Names containing 'mock' that wrap age_graph, and BrokenGraph/raising AsyncMock error doubles, were not counted as violations.

## P3 — Style/maintenance

None reported.

## Explicit critical-check results

| Requested check | Review result |
| --- | --- |
| P1-095, centroid support | **Unresolved:** unavailable payload fails response validation; unmeasured cold-start/missing-bootstrap support still says GREEN. SOC-01. |
| P1-096, analyze-alert RL health/headroom | The caught health/headroom failure sets `exploration_status="degraded_health"` and `rl_exploration.health_error`, and skips the exploration proposal. Outer proposal failure is also exposed as unavailable. No additional finding for this catch path. |
| P1-097, outcome history / learning rate | The analyst-history catch explicitly sets `_analyst_eta=0.0` and `eta_source="fallback"`; the override learning-rate assignment uses that value, and the source is added to persistence status. It no longer silently uses the ordinary override rate on that failure path. This does not mean all other learning operations are paused. |
| P1-119, verification-health window failure | **Corrected for the named failure:** failed window queries add failed components and force overall status `degraded`. A probe with otherwise healthy coverage and GREEN conservation returned `degraded` and both failed window names, not GREEN. |
| P1-129/P1-130, factor breakdown and persisted vectors | **Incomplete:** helper failure propagation does not protect the separate `execute_action` write path. SOC-05. Investigation vector admission has a related correctness gap, SOC-04. |
| Composite category history | **Unresolved:** fails closed for approval but reports maturity/experience instead of unavailable history. SOC-08. |

## FIX-SOC regression review

The repository's actual FIX-SOC record corrects part of the supplied recap. The six regressions are six test cases, not six independently changed test files.

- **Credit assigner:** query-failure tests expect `None`, including the SS-15 BrokenGraph test. Legitimate no-store, no-history and zero-reward cases continue to expect `[]`; those are not failed graph reads. Converting all three healthy/no-op cases to `None` would not match current behavior.
- **Simulation:** the missing-store path returns a complete result with typed empty/zero fields and `context_degraded=["graph_store"]`. The focused SS-15 test checks the flag, and the revised cold-start test checks the completed result. The router preserves the flag. The shadow-flush test in the same file is a separate coverage problem, SOC-19.
- **Variant history:** a successful read with no prior events returns `{"action": "proceed"}`; a query failure returns `None`. The legacy failure test was updated to assert `None`. The aggregate scanner's handling is still incomplete, SOC-09.
- **Posterior health:** the meaningful fix is in `app.main.health`: an unhealthy posterior-store probe sets `payload["ready"]=False` before choosing the HTTP status. The current health test exercises that readiness/status behavior. This is not merely a mock adjusted to bypass the actual check.
- All these tests are included in the passing full run. No expectation-only change is proposed by this review.

## FIX-SOC-SKIPS quality review

- **AGE DSN:** sourced from `AGE_TEST_DSN`, `GRAPH_DSN`, or `GraphConfig.load("soc")`, not a hardcoded database URL. The captured destination is used for connection creation. The preliminary availability check uses a different configuration path, SOC-17.
- **Disposable AGE graphs:** names include process ID and a UUID; teardown drops the graph and closes the connection using nested `finally` blocks. No separate cleanup finding for this fixture.
- **Live backend:** HTTPX is used by the live tests. The harness probes health, has a 30-second startup deadline, and terminates/waits for an owned process at session finish. Shared-port identity, child environment, error reporting and kill/reap gaps remain, SOC-18.
- **Campaign fixture:** module-scoped and has normal teardown, but uses a fixed ID in shared application state and does not establish ownership, SOC-16.
- **FastAPI Query defaults:** the direct call now passes `category=None, n=200`, matching ordinary endpoint values rather than passing FastAPI `Query` objects into application logic. This fix is correct for the inspected call.
- **Millisecond timestamps:** recent evolution converts modern millisecond epochs to seconds before `datetime.utcfromtimestamp`, while leaving ordinary current seconds unchanged. Correct for the stored SOC timestamp convention; no finding for this change.
- The full run has **zero skips**, but that observed result does not prove the setup hooks can no longer skip on a different configuration or failed startup.

## Coverage, mocks and remaining substitution assessment

The requested “every fixed function has a degraded-path test asserting typed defaults and a flag” condition is **not met**. New focused files provide useful helper coverage, but incomplete caller coverage and vacuous tests remain. SOC-19 records concrete examples, and SOC-02 identifies a test that actively enforces the wrong HTTP field type. Existing full-suite success cannot substitute for these assertions.

The zero non-error graph-store-mock condition is also **not met** under the requested real-store standard; SOC-20 lists concrete normal-state uses. The scan was classified by behavior, not by names alone:

| Scan category | Assessment |
| --- | --- |
| Normal-state graph/store replacements | Remaining examples in simulation and override-detector tests, SOC-20. |
| Deliberate error-path doubles | Keep: `BrokenGraph`, raising `AsyncMock`, and explicit failed read/write injection in the SS tests and existing failure tests. |
| Real AGE wrappers with “mock” in their names | Not counted as fake stores when backed by `age_graph`/real fixture adapters. |
| Non-graph mocks and narrow behavioral spies | Not counted as graph-store violations merely because they use `MagicMock`. |
| Production graph-store mocks | No new production Mock/MagicMock store introduced in the reviewed diff. A mock external connector such as CrowdStrike is not itself a mocked graph store. |

Remaining broad catches/defaults that erase failure are documented at the consuming boundary: campaign timeline, composite history, provenance booleans, overall IKS, historical metrics, and action factors. New metadata that is set but not properly consumed is documented for executive narrative, override loading, shadow flushing, variant scanning and investigation evidence. These are why the sweep is not CLEAN despite all requested commands passing.

## Reviewed production-function inventory

This is the changed-function inventory for the 48 production files reviewed. Names are grouped by file; repeated method names such as `detect` and `__init__` represent the changed class methods in that file. Data-model changes were reviewed separately. Downstream unchanged callers and explicitly requested carryover paths are listed in the findings and critical-check table above. Inventory inclusion denotes inspection, not a claim of complete branch-test coverage.

| File (relative to backend/app) | Changed functions inspected |
| --- | --- |
| `connectors/base.py` | `to_dict` |
| `connectors/crowdstrike_mock.py` | `refresh` |
| `connectors/greynoise.py` | `existing_observation`, `fallback_entry`, `refresh` |
| `connectors/pulsedive.py` | `existing_observation`, `fallback_entry`, `refresh` |
| `connectors/registry.py` | `refresh_all` |
| `domains/soc/campaigns.py` | `__init__`, `_check_alert_impl`, `_check_materialized_campaign`, `_materialize_alert`, `_materialize_in_background`, `campaigns_exist`, `check_alert_timed`, `fetch_all_events`, `fetch_recent_events`, `fetch_single_alert_event`, `get_campaign_detail`, `get_campaigns`, `persist_campaign_seed`, `reset_for_tests` |
| `domains/soc/orchestrator.py` | `_query_rows`, `_threat_intel_provenance` |
| `evidence_provider.py` | `__init__`, `_read_from_graph_client`, `read_evidence` |
| `framework/checkpoint.py` | `list_checkpoints` |
| `framework/intervention_controls.py` | `_log_intervention`, `get_current_state`, `get_intervention_history` |
| `framework/override_detector.py` | `__init__` |
| `framework/provenance.py` | `get_provenance_from_graph` |
| `framework/shadow_mode.py` | `get_shadow_report` |
| `framework/similar_cases_base.py` | `_fetch_verified_decisions`, `get_similar_cases` |
| `graph_schema.py` | `seed_graph` |
| `main.py` | `health`, `startup_event` |
| `models/responses.py` | Response-model fields and defaults |
| `routers/admin.py` | `admin_evolution_scan` |
| `routers/cohort_status_router.py` | `_read_decision_records`, `get_campaign_cohort_status` |
| `routers/evolution.py` | `get_recent_evolution` |
| `routers/framework_router.py` | `checkpoint_list`, `graph_node_neighbors`, `graph_summary`, `graph_top_nodes`, `intervention_history`, `intervention_state`, `shadow_report` |
| `routers/graph.py` | `get_enrichment_summary`, `refresh_threat_intel_endpoint` |
| `routers/metrics.py` | `get_board_export`, `get_compounding_metrics`, `get_economics` |
| `routers/simulation.py` | `_run_simulation_bg` |
| `routers/soc.py` | `_tab1_content`, `_tab2_content`, `_tab3_content`, `_tab4_content`, `_tab5_content`, `attack_chains`, `benchmarking_report`, `explain_decision`, `get_analyst_benchmarking`, `get_analyst_weights`, `get_attack_tactic_breakdown`, `get_campaign_detail`, `get_campaign_timeline`, `get_campaigns`, `get_centroid_export`, `get_decision_provenance`, `get_detection_engineering`, `get_enrichment_advisor`, `get_learning_state_endpoint`, `get_spike_cap_status_endpoint`, `get_threat_intel_for_alert`, `get_volume_baseline`, `query_soc_metrics`, `recorrelate_campaigns` |
| `routers/soc_demo_beats.py` | `centroid_timeline` |
| `routers/triage.py` | `analyze_alert`, `report_decision_outcome` |
| `services/attack_chain.py` | `__init__`, `_fetch_recent_alerts`, `scan_recent_alerts` |
| `services/balance_sheet.py` | `_safe_auto_approve_stats`, `_safe_centroid_drift`, `_safe_overall_iks`, `_safe_timeline`, `generate_balance_sheet` |
| `services/benchmarking_report.py` | `_fetch_verified_decisions`, `generate_report` |
| `services/cross_graph_discovery.py` | `refresh` |
| `services/evidence_room.py` | `_collect_conservation` |
| `services/executive_narrative.py` | `build_executive_narrative_async` |
| `services/graph_explorer.py` | `get_graph_summary`, `get_node_neighbors`, `get_top_nodes` |
| `services/iks.py` | `compute_visible_iks` |
| `services/investigation_patterns.py` | `_bounded_read`, `execute` |
| `services/learning_health.py` | `compute_volume_baseline`, `detect_volume_spike` |
| `services/override_detector.py` | `load_from_graph` |
| `services/promotion_gate.py` | `_compute_batch_std`, `_get_shadow_batch_stats`, `evaluate_promotion` |
| `services/rl_engine.py` | `assign_chain_credit` |
| `services/shadow_runner.py` | `_flush_shadow_batch` |
| `services/simulation.py` | `run` |
| `services/snapshots.py` | `_write_profile_snapshot`, `maybe_write_profile_snapshot` |
| `services/threat_indicator.py` | `get_all_indicators`, `get_indicators_for_alert`, `upsert_indicator` |
| `services/threat_intel.py` | `refresh_threat_intel` |
| `services/time_machine.py` | `get_evolution_timeline` |
| `services/variant_generator.py` | `__init__`, `_consult_history`, `_get_per_category_accuracy_trends`, `_load_accuracy_trajectory`, `detect`, `scan_for_opportunities` |
| `state/graph_snapshot.py` | `from_graph` |

## Verdict

**FINDINGS — 6 P1, 14 P2, 0 P3.** Validation has no baseline regression, but the failure-path correctness and observability gaps above remain. No fixes were made during this review.

