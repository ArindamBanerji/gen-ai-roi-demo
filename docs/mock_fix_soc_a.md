# MOCK-FIX-SOC-A — September 23, 2026

Reviewed 30 of the 59 SOC REPLACE entries in the shared classification. The requested filename families cover fewer than 30 entries, so related learning/history tests complete this batch. SOC-B owns the 29 paths below.

27 targeted files changed; three policy-focused files retained under the prompt's KEEP exception. Shared `backend/tests/conftest.py` and the new `backend/tests/support/real_graph.py` also provide production stores and disposable AGE namespaces. No git commands used.

## Replacement decisions

| Target | Result |
| --- | --- |
| [soc_triage_harness.py](../backend/tests/support/soc_triage_harness.py) | Shared production-store harness; memory for policy tests, isolated AGE for persistence; Alert relationships seeded for real outcome reads. |
| [test_centroid_pitr.py](../backend/tests/test_centroid_pitr.py) | AGE checkpoint writes, fresh-connection listing and tensor restore. |
| [test_checkpoint_contract.py](../backend/tests/test_checkpoint_contract.py) | AGE checkpoint create/rollback, invalid payloads, immutable snapshots. |
| [test_evolution_ledger.py](../backend/tests/test_evolution_ledger.py) | AGE event writes and reads; persisted history ordering, limits, filters and restart reads; validation/HTTP mocks retained. |
| [test_graph_explorer.py](../backend/tests/test_graph_explorer.py) | AGE nodes, edges, domain filtering and prebuilt queries; HTTP validation tests retained. |
| [test_graph_snapshot.py](../backend/tests/test_graph_snapshot.py) | AGE counts and override statistics, foreign/pending records, new-connection restart reads. |
| [test_learning_health.py](../backend/tests/test_learning_health.py) | KEEP: conservation arithmetic, calibration and scorer-policy behavior; no graph-result contract claimed. |
| [test_rl_full_pipeline.py](../backend/tests/test_rl_full_pipeline.py) | AGE-backed outcome persistence and persisted TRIGGERED_EVOLUTION edge; controlled scoring/routing inputs retained. |
| [test_rl_triage_integration.py](../backend/tests/test_rl_triage_integration.py) | AGE outcome, override/cohort fields and RL learning reads; narrow write fault injection; analyze-policy mocks retained. |
| [test_l5_conservation_soc_hook.py](../backend/tests/test_l5_conservation_soc_hook.py) | Real AGE conservation inputs; InMemoryGraphStore conservation state, production writes, fault/lock spies. |
| [test_soc_learning_live.py](../backend/tests/test_soc_learning_live.py) | InMemoryGraphStore; calls the production outcome route instead of a copied learning-enabled implementation. |
| [test_soc_dk_l5.py](../backend/tests/test_soc_dk_l5.py) | InMemoryGraphStore centroid and DK persistence, readback and narrow spies; scorer-policy tests retained. |
| [test_soc_c9b_l5_proof.py](../backend/tests/test_soc_c9b_l5_proof.py) | AGE centroid/DK/conservation persistence and seed topology; rejects domainless/foreign decisions; dry-run and CLI mocks retained. |
| [test_p77_migration.py](../backend/tests/test_p77_migration.py) | InMemoryGraphStore centroid persistence and public readback; real scorer behavior retained. |
| [test_triggered_evolution.py](../backend/tests/test_triggered_evolution.py) | AGE persisted evolution edges, no-edge cases and narrow write-failure injection. |
| [test_iks_stability.py](../backend/tests/test_iks_stability.py) | KEEP: scorer preservation across reset and state-manager policy; graph transport is outside these assertions. |
| [test_soc_domain_isolation.py](../backend/tests/test_soc_domain_isolation.py) | Removed query interpreter; AGE reads, writes, archive selection and scoped deletion in disposable namespaces. |
| [test_accuracy_trajectory.py](../backend/tests/test_accuracy_trajectory.py) | AGE decision counts and domain exclusion through endpoint; numerical trajectory unit test retained. |
| [test_analyst_eta.py](../backend/tests/test_analyst_eta.py) | AGE analyst precision and minimum-count boundary; pure eta/HTTP tests retained. |
| [test_category_freeze.py](../backend/tests/test_category_freeze.py) | AGE alert category baselines; no-query policy and scorer freeze spies retained. |
| [test_cluster_history.py](../backend/tests/test_cluster_history.py) | AGE Decision-to-Alert relationships, pending/current exclusion, precision and quote serialization; fault injection retained. |
| [test_composite_gate.py](../backend/tests/test_composite_gate.py) | AGE decision-history inputs, maturity gate and auto-approval aggregates; HTTP/analyze mock retained. |
| [test_credit_assigner.py](../backend/tests/test_credit_assigner.py) | AGE evolution-linked history and query filters; score attribution and failure-policy tests retained. |
| [test_cross_graph_discovery.py](../backend/tests/test_cross_graph_discovery.py) | AGE entity/indicator/decision relationships, graph clock, exact windows, convergence and velocity; cache/error logic mocks retained. |
| [test_evidence_room_conservation_fallback.py](../backend/tests/test_evidence_room_conservation_fallback.py) | KEEP: health/IKS fallback selection policy, using controlled service responses. |
| [test_verification_health.py](../backend/tests/test_verification_health.py) | AGE verified/pending decisions across recent/prior/older windows; conservation-status policy input retained. |
| [test_h7_fix2.py](../backend/tests/test_h7_fix2.py) | AGE graph/decision counts; HTTP registration and explicit transport-failure test retained. |
| [test_h7_fix3.py](../backend/tests/test_h7_fix3.py) | AGE analytics and category counts; removed one circular local copy of decision-ID formatting. |
| [test_h7_fix4.py](../backend/tests/test_h7_fix4.py) | AGE decision economics and empty trend reads; endpoint registration checks retained. |
| [test_pattern_history_w2.py](../backend/tests/test_pattern_history_w2.py) | AGE evolution edges and production snapshot shape for recency-weighted pattern history. |

## Store/query replacements

- Custom graph/store classes removed in 10 files: centroid PITR, checkpoint contract, explorer, L5 conservation hook, C9B proof, P77 migration, domain isolation, cluster history, composite gate and credit assigner.
- AGE-family doubles removed in five files: `_MockAGE`, explorer `_FakeAGE`, C9B `_C9BAGE`/`_SeedFakeClient`, `InMemorySocGraphClient`, and composite `FakeAGE`. The literal `_FakeAGE` class was removed from one file. RL analyze-policy `FakeAGE` remains only for controlled routing/scoring behavior.
- Canned `AsyncMock.run_query` results replaced by actual AGE queries in 10 files: evolution ledger, accuracy trajectory, analyst eta, category freeze, cross-graph discovery, verification health, H7 fixes 2/3/4, and pattern history. GraphSnapshot's mocked aggregate methods were also replaced. Wrapping spies delegate to real operations; deliberate failure mocks remain.
- 158 AGE-marked test cases (149 test functions, including parameter expansion). InMemoryGraphStore remains the protocol implementation for offline persistence and learning checks.
- One circular test deleted: `test_h7_fix3.py::test_dec_prefix_not_doubled`, which only tested a locally copied implementation.
- The C9B domainless-row test was replaced with a real domain-isolation check: canonical SOC decisions count; domainless and foreign decisions do not.

## Production corrections exposed by real queries

- `app/services/graph_explorer.py`: AGE-compatible label exclusion syntax for top-node queries.
- `app/domains/soc/factors.py`: pattern history accepts decoded list/tuple snapshots as well as JSON strings.
- Existing mypy errors corrected in nine files: `services/posterior_store.py`, `services/cohort_status.py`, `framework/intervention_controls.py`, `domains/soc/scorer_adapter.py`, `services/gae_state.py`, `services/soc_learning_control.py`, `routers/platform.py`, `routers/cohort_status_router.py`, and `routers/compat_router.py`. Changes specify return types/conversions and the existing dict-or-JSONResponse contract; no type-check suppression added.

## SOC-B — remaining 29 files

- `backend/tests/integration/test_w2_read_path.py`
- `backend/tests/test_audit_chain_wiring_extended.py`
- `backend/tests/test_audit_seed_timestamps.py`
- `backend/tests/test_bootstrap_decisions.py`
- `backend/tests/test_campaign_matcher.py`
- `backend/tests/test_campaign_measurement_instrumentation.py`
- `backend/tests/test_campaign_phase3_async.py`
- `backend/tests/test_campaign_phase4_continues.py`
- `backend/tests/test_campaign_seed_materialization.py`
- `backend/tests/test_campaign_timeline.py`
- `backend/tests/test_campaign_v6_context.py`
- `backend/tests/test_campaign_vld_topology.py`
- `backend/tests/test_econ1.py`
- `backend/tests/test_executive_narrative.py`
- `backend/tests/test_f2_design.py`
- `backend/tests/test_f4_overlay.py`
- `backend/tests/test_ingest_endpoint.py`
- `backend/tests/test_kill_chain.py`
- `backend/tests/test_phase_07b_platform_guards.py`
- `backend/tests/test_seed_verified_decisions.py`
- `backend/tests/test_soc_entity_cache_route_readiness.py`
- `backend/tests/test_soc_evidence.py`
- `backend/tests/test_soc_fabrication_fixes.py`
- `backend/tests/test_soc_situation_pattern.py`
- `backend/tests/test_spike_detector.py`
- `backend/tests/test_tab_content.py`
- `backend/tests/test_threat_indicator.py`
- `backend/tests/test_w2_flywheel.py`
- `backend/tests/test_zero_day_timestamp_spread.py`

## Verification

- Baseline: 2,573 passed, 19 skipped. Baseline mypy: 18 errors in nine application files.
- `python -m pytest tests/ -q --timeout=120 -x -m "not age"`: **2,414 passed, 19 skipped, 158 deselected** (212.11 s).
- `python -m pytest tests/ -v --timeout=120 -x -m age`: **158 passed, 0 skipped, 2,433 deselected** (247.52 s). All AGE cases ran against disposable graphs.
- Combined: **2,572 passed, 19 skipped, 0 failures**. Reconciliation: 2,414 + 158 + one authorized circular-test deletion = 2,573 baseline passes. The literal numerical gate is lower by the one deleted circular test; no additional test loss or new skips.
- Final snapshot readback check, after strengthening override-rate/quality assertions: **17 passed**.
- Application mypy: **clean, 205 source files**. Application plus shared fixtures: **clean, 208 source files**.
- Logs/XML: `../../.codex_tmp/mock_fix_soc_a_final_nonage.{log,xml}`, `../../.codex_tmp/mock_fix_soc_a_final_age.{log,xml}`, `../../.codex_tmp/mock_fix_soc_a_final_mypy.log`, `../../.codex_tmp/mock_fix_soc_a_snapshot.log` (relative to this document).
- Three KEEP files and all 29 SOC-B files were left unchanged.
