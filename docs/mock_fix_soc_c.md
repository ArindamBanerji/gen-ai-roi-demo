# MOCK-FIX-SOC-C — September 23, 2026

SOC-A's 27 changed files and SOC-B's three changed files were excluded. This pass reviewed the 26 remaining manifest files plus SOC-A's three KEEP entries. Twenty-four test files changed; five remain KEEP under the product-logic exception. Across A/B/C, all 59 classification entries have a disposition: 54 changed and five retained.

The new `backend/tests/support/campaign_graph.py` seeds disposable AGE graphs, delegates queries and transactions to the production client, records calls, and reads assertions from the database. It contains no query interpreter. Its materialization observer controls task timing around production repository writes; supplied event inputs isolate scheduling from event discovery. Missing acknowledgement and write-failure injection are explicit fault seams.

## File dispositions

Paths below are relative to `backend/tests/`.

| File | Disposition |
| --- | --- |
| integration/test_w2_read_path.py | AGE: actual verified decisions and evolution edges; weighted history and empty history. Static factor-order test retained. |
| test_audit_chain_wiring_extended.py | Deleted one circular local try/except simulation. Actual ledger and static wiring assertions retained. |
| test_audit_seed_timestamps.py | AGE: reverse insertion order, persisted timestamps, chronological ledger rebuild, null timestamp fallback. |
| test_bootstrap_decisions.py | AGE: production batch writer, repeat-call idempotency, fresh-connection count and native-array readback. |
| test_campaign_matcher.py | AGE: actual campaign writes, membership batches, deduplication, missing alerts, query-only tracing, decision-source normalization. Correlation and failure policy doubles retained. |
| test_campaign_measurement_instrumentation.py | AGE: aggregate override rate and quality from written decision properties. |
| test_campaign_phase3_async.py | AGE: materialization, persisted seed/edge state, storm convergence, positive/negative cache fallback reads. Scheduling-only doubles retained. |
| test_campaign_phase4_continues.py | AGE: adjacent-bucket topology, identity exclusions, persisted legacy fields, edge properties and duplicate counts. Cache timing uses a must-not-query spy. |
| test_campaign_seed_materialization.py | AGE: real transaction/advisory locks, seed promotion, repeat/concurrent writes, cleanup and duplicate counts. Identity arithmetic and unit latency retained. |
| test_campaign_timeline.py | AGE: read-only endpoint and Alert-to-Campaign links with nonempty assertions. Presentation/state boundary mocks retained. |
| test_campaign_v6_context.py | AGE: successful materialization populates cached context; dead V6 graph/repository emulators removed. Payload policy cases retained. |
| test_campaign_vld_topology.py | AGE: Decision-to-Alert-to-Campaign traversal, CONTINUES predecessor, missing decision. |
| test_executive_narrative.py | AGE: verified decision counts, campaign counts, and category accuracy excluding pending decisions. Narrative/presentation mocks retained. |
| test_f2_design.py | AGE: empty and populated noise maps with real outcomes and Alert links. Scorer drift arithmetic retained. |
| test_ingest_endpoint.py | AGE: escaped property values, repeated manifest write, exact persisted node/edge counts. HTTP validation mocks retained. |
| test_phase_07b_platform_guards.py | KEEP: profile-sensitive loader and HTTP namespace policy; no graph-result assertions. |
| test_seed_verified_decisions.py | AGE: seeding guard reads 101 real verified decisions and preserves count. |
| test_soc_entity_cache_route_readiness.py | KEEP: cache admission, hit/miss, freshness, invalidation and health response policy with controlled loaders. |
| test_soc_evidence.py | InMemoryGraphStore replaces FakeGraphClient. Production showcase registration supplies evidence; scorer geometry remains controlled. Registry test renamed to avoid claiming graph node creation. |
| test_soc_fabrication_fixes.py | AGE: historical/current metrics separation and preserved threat enrichment/staleness. Reset/HTTP policy doubles retained. |
| test_soc_situation_pattern.py | KEEP: adapter maps supplied security context to generic nodes/edges and validates intent/depth; no database traversal contract claimed. |
| test_spike_detector.py | AGE: daily alert counts drive baseline and spike decisions. Freeze/HTTP policy spies retained. |
| test_tab_content.py | AGE: GraphSnapshot restart reads 42 real verified decisions through separate clients. Tab presentation mocks retained. |
| test_threat_indicator.py | AGE: indicator upsert, idempotency, alert linkage and grouped summary. Assertions use the real `indicator` field; HTTP shape mocks retained. |
| test_w2_flywheel.py | AGE: persisted snapshot history and changing weighted result. Snapshot parser tests retained. |
| test_zero_day_timestamp_spread.py | AGE: dry-run queries real timestamp history and preserves stored timestamps. Deterministic assignment and sufficient-spread policy cases retained. |
| test_learning_health.py | Deleted two circular local copies of scorer conservation wiring. Production conservation arithmetic tests retained. |
| test_iks_stability.py | KEEP: scorer preservation across reset and state-manager dispatch policy; mock reset transport is outside the assertions. |
| test_evidence_room_conservation_fallback.py | KEEP: health/IKS fallback selection, errors and pre-activation policy. |

## Production correction

`backend/app/services/bootstrap_neo4j.py`: AGEClient serializes list parameters as JSON strings, so the old `UNWIND $decisions` failed against real AGE. The writer now serializes its fixed-schema batch as a native Cypher list of maps, including native factor arrays, with the production scalar escaping routine. Domain scoping and bootstrap idempotency remain covered by the real-store test.

## Validation

Baseline: 2,398 passed, 19 skipped, 174 AGE cases deselected. This pass moves 97 existing cases to AGE and removes three circular cases; expected non-AGE count is 2,298 and AGE count is 271. The requested literal non-AGE threshold of 2,398 must therefore be reconciled with those authorized changes, rather than represented as satisfied.

Final command results are recorded in `session_state.md`. No git commands used. Original target files were saved under `../.codex_tmp/mock_fix_soc_c_original/` for comparison.


Final results:

| Check | Result |
| --- | --- |
| Full non-AGE suite | 2,298 passed; 19 existing skips; 271 deselected; zero failures |
| AGE cases | 271 unique passed across initial run (100) and retry (171); zero unresolved skips/failures |
| Mypy app/ plus new helper | Clean, 206 files |
| Strengthened cache spies | 2 passed |
| Combined coverage | 2,569 passed; 19 existing skips |

The initial AGE run suffered a database connection timeout and then a setup connection closure. The retry selected every uncompleted case and excluded only completed passes, with database statement/lock timeouts. Both XML reports are retained; the final result does not claim an uninterrupted green AGE run. A standalone endpoint subset also encountered shared-graph initialization during import; full-suite collection and the final AGE selections succeeded.

Evidence is under `../.codex_tmp/mock_fix_soc_c_*`; machine-readable totals are in `mock_fix_soc_c_results.json`. Count reconciliation: 2,298 + 97 moved-to-AGE + 3 circular deletions = the 2,398 non-AGE baseline.
