# SOC C9B Deep Diagnostic — persist_soc_centroid returned false

Date: 2026-06-08
Model: gpt-5.3
Task Type: Deep diagnostic audit only, no code changes
Repo: C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50
Diagnostic Graph: soc_graph_diag

## Executive Summary
- Root cause: E. STORE_WRITE_FAILS. The AGE store `update_centroid()` replaces an existing `L5Centroid` for the same `(domain, category, action)` using plain `DELETE c`; when that centroid already has a `SHAPED_BY` edge, AGE rejects the delete with "Cannot delete a vertex that has edge(s)." `persist_soc_centroid()` catches that exception and returns `False`.
- Why latest Diagnostic E still failed: The first earlier mixed-category DIAG-E3 run wrote `L5Centroid(domain='soc', category='credential_access', action='investigate')` with `SHAPED_BY` to `DIAG-E3-001`. The later credential_access-only DIAG-E3-CRED outcomes tried to update the same centroid key and hit the delete-with-edge failure.
- persist_soc_centroid false path: `backend/app/services/gae_state.py:387-399` catches any `store.update_centroid()` exception and returns `False`; the caller collapses this to `persist_soc_centroid_returned_false` at `backend/app/routers/triage.py:1431-1452`.
- category/action mapping: No mismatch found. `credential_access` is category index 0; `investigate` is action index 1 in the four-action scorer space.
- phase: `/api/triage/learning-state?category=credential_access` returned `phase="MEAN_CONVERGENCE"`, `alpha=0.5`, and `decisions_in_category=13`; phase is not the blocker.
- store/update_centroid: Installed `ci_platform.graph.age_graph_store.py:1379-1388` deletes the prior centroid then creates a new one; `age_graph_store.py:1389-1401` creates `SHAPED_BY` after centroid creation.
- direct store probe: Confirmed. A diagnostic-only probe category wrote successfully once, then failed on a second write after it had a `SHAPED_BY` edge, with the same AGE error.
- blast-radius summary: This affects every repeated L5 centroid update for any SOC category/action once the existing centroid has any relationship, not just C9B or credential_access.
- future fixer needed: YES.
- recommended next step: Fix the canonical AGE `update_centroid()` replacement semantics to delete/detach existing centroid relationships before deleting the centroid, or update in place, then add tests covering repeated centroid writes with `SHAPED_BY`.

## Latest Diagnostic E Evidence
- Fresh proof IDs: `DIAG-E3-CRED-001` through `DIAG-E3-CRED-005`.
- Analyze path: all five returned `action="investigate"` with `category="credential_access"`.
- Outcome path: all five returned HTTP 200 and wrote `outcome="correct"`, `correct=true`.
- Outcome response fields: `centroid_update` was present, `l5_centroid_persisted=false`, and `l5_persistence_skipped_reason="persist_soc_centroid_returned_false"` for all five.
- AGE readback: five DIAG-E3-CRED Decisions exist with `domain='soc'`, `action='investigate'`, `category='credential_access'`, factor vectors of length 6, `outcome='correct'`, and `correct=true`.
- Existing L5 rows: `L5Centroid` total for `domain='soc'` was 2 before the diagnostic probe; those rows were caused by earlier mixed-category alerts `DIAG-E3-001` and `DIAG-E3-003`, not DIAG-E3-CRED.
- DK note: `L5DKWeight=0` remains expected below the 200-decision threshold and is not part of this failure.

## Runtime Readback
- backend health: `GET http://127.0.0.1:8001/health` returned `{"status":"healthy","components":{"posterior_store":{"healthy":true}}}`.
- DIAG-E3-CRED Decisions:
```json
[
  {"alert_id": "DIAG-E3-CRED-001", "decision_id": "3fc7afa8-1e32-475d-a0a3-c9dfdaf76d85", "category": "credential_access", "action": "investigate", "outcome": "correct", "correct": true, "factor_vector": [0.825, 1.0, 0.0, 0.4, 0.7, 0.6666666666666666]},
  {"alert_id": "DIAG-E3-CRED-002", "decision_id": "8d449202-4015-4782-9247-04c055c87fe1", "category": "credential_access", "action": "investigate", "outcome": "correct", "correct": true, "factor_vector": [0.825, 1.0, 0.0, 0.4, 0.7, 0.6666666666666666]},
  {"alert_id": "DIAG-E3-CRED-003", "decision_id": "1450fe66-e213-4d67-9d93-56cc22e4243a", "category": "credential_access", "action": "investigate", "outcome": "correct", "correct": true, "factor_vector": [0.825, 1.0, 0.0, 0.4000000000000001, 0.7, 0.6666666666666666]},
  {"alert_id": "DIAG-E3-CRED-004", "decision_id": "3a2071d9-4fae-4245-8cd1-657482b4eedd", "category": "credential_access", "action": "investigate", "outcome": "correct", "correct": true, "factor_vector": [0.825, 1.0, 0.0, 0.4000000000000001, 0.7, 0.6666666666666666]},
  {"alert_id": "DIAG-E3-CRED-005", "decision_id": "fcdc582a-41c0-49a0-8952-ff891efaf5ac", "category": "credential_access", "action": "investigate", "outcome": "correct", "correct": true, "factor_vector": [0.825, 1.0, 0.0, 0.4000000000000001, 0.7, 0.6666666666666666]}
]
```
- existing L5Centroid:
```json
[
  {"domain": "soc", "category": "credential_access", "action": "investigate", "caused_by_decision_id": "01bdb790-b279-4648-88e2-fdf8078f2241", "delta_norm": 0.012247448713915901},
  {"domain": "soc", "category": "lateral_movement", "action": "investigate", "caused_by_decision_id": "58eb40e2-1e1d-4ccf-af04-bb3cc174a247", "delta_norm": 0.012247448713915901}
]
```
- existing SHAPED_BY:
```json
[
  {"alert_id": "DIAG-E3-001", "category": "credential_access", "action": "investigate", "caused_by_decision_id": "01bdb790-b279-4648-88e2-fdf8078f2241"},
  {"alert_id": "DIAG-E3-003", "category": "lateral_movement", "action": "investigate", "caused_by_decision_id": "58eb40e2-1e1d-4ccf-af04-bb3cc174a247"}
]
```
- conservation state: `L5ConservationState` readback returned `status="RED"`, `alpha=0.1667`, `q=1.0`, `V=5`, `theta_min=28.236`, and `categories_with_data=1`.
- read-only learning state: `GET /api/triage/learning-state?category=credential_access` returned `strategy="two_phase"`, `phase="MEAN_CONVERGENCE"`, `alpha=0.5`, `dk_weights=null`, `freeze_point=null`, and `decisions_in_category=13`.
- raw query outputs: see values above. All runtime probes used `AGE_GRAPH_NAME=soc_graph_diag`.

## Source Trace — persist_soc_centroid false paths
Function: `backend/app/services/gae_state.py:358-399`.

False paths:
- Missing learning store or missing `update_centroid`: `backend/app/services/gae_state.py:370-372`. Evidence against this runtime cause: conservation persisted through the same store path, and direct store probe wrote a diagnostic `L5Centroid`.
- Non-MEAN_CONVERGENCE phase: `backend/app/services/gae_state.py:373-375`. Evidence against: read-only learning-state endpoint returned `phase="MEAN_CONVERGENCE"`.
- Missing post centroid: `backend/app/services/gae_state.py:376-378`. Evidence against: action/category indexes are valid and `ProfileScorer.update()` returned centroid_update payloads; `get_soc_centroid()` indexes the scorer centroid tensor at `backend/app/services/gae_state.py:345-355`.
- Store exception: `backend/app/services/gae_state.py:387-399`. Evidence for: direct store probe reproduced an exception on the second write for a category/action that already had `SHAPED_BY`; latest outcome responses collapsed this to `persist_soc_centroid_returned_false`.

Current response precision:
- `persist_soc_centroid()` returns only bool and logs the exception at `backend/app/services/gae_state.py:396-398`.
- The route sets `l5_persistence_skipped_reason` to `persist_soc_centroid_returned_false` for any false return at `backend/app/routers/triage.py:1443-1452`, losing the actual AGE exception type/message.

## Source Trace — Outcome Caller
- `_cu`: Created by `_guarded_update()` at `backend/app/routers/triage.py:1399-1407`. The DIAG-E3-CRED responses had `centroid_update` payloads, so `_cu` was non-null.
- category/action args: The caller passes `category=getattr(_cu, "category_name", _cat_name_out)` and `action=_actual_action_name` at `backend/app/routers/triage.py:1431-1436`.
- pre/post centroid data: The caller captures pre-centroid from `get_soc_centroid()` before update at `backend/app/routers/triage.py:1366-1372`; `persist_soc_centroid()` retrieves post-centroid from scorer state at `backend/app/services/gae_state.py:376`.
- decision_id: The caller passes `caused_by_decision_id=request.decision_id` at `backend/app/routers/triage.py:1437`.
- status fields: The response exposes `l5_centroid_persisted`, `l5_shaped_by_attempted`, `l5_persistence_skipped_reason`, and `l5_persistence` at `backend/app/routers/triage.py:1779-1792`.
- missing precision: Any false return from `persist_soc_centroid()` becomes `persist_soc_centroid_returned_false`, without distinguishing store delete failure from store absence, phase gate, post-centroid absence, or other guard.

## Source Trace — ProfileScorer State and Mapping
- category order: `backend/app/domains/soc/config.py:92-99` lists `credential_access` first, so `credential_access` index is 0.
- action order: `backend/app/domains/soc/config.py:49-57` defines `SCORER_ACTIONS=["escalate","investigate","suppress","monitor"]`; `investigate` index is 1.
- category_index: `SOCDomainConfig.get_category_index()` returns `SOC_CATEGORIES.index(category)` at `backend/app/domains/soc/config.py:682-686`.
- action_index: outcome caller uses `list(SCORER_ACTIONS).index(action_name)` at `backend/app/routers/triage.py:1258-1261`.
- centroid shape/action space: `build_profile_scorer()` uses `SCORER_PROFILE_CENTROIDS.copy()` and `actions=list(SCORER_ACTIONS)` at `backend/app/domains/soc/config.py:705-727`; `refer_to_analyst` is routing-only, not in the scorer action space.
- phase: `ProfileScorer.get_phase()` returns category state phase when a learning strategy exists; runtime endpoint reports `MEAN_CONVERGENCE`.
- mismatch risks: No evidence that category/action mapping caused this failure. The store failure reproduces independently with a diagnostic category/action after a `SHAPED_BY` edge exists.

## Source Trace — Store update_centroid Contract
- adapter: `ci_platform.graph.age_sdk_adapter.py:291-307` forwards `update_centroid()` to the underlying store and returns `None`.
- store: installed `ci_platform.graph.age_graph_store.py:1351-1406`.
- return value: `update_centroid()` returns `None` on success; `persist_soc_centroid()` does not inspect the return and would return `True` after a non-throwing call.
- write behavior: store normalizes props at `age_graph_store.py:1360-1377`, then runs a prior-centroid delete at `age_graph_store.py:1379-1387`, then creates `L5Centroid` at `age_graph_store.py:1388`.
- SHAPED_BY behavior: if `caused_by_decision_id` is present, store matches `Decision {decision_id: ...}` and creates `SHAPED_BY` at `age_graph_store.py:1389-1401`; only SHAPED_BY creation is wrapped in try/except at `age_graph_store.py:1402-1406`.
- error behavior: the delete-before-create query is not wrapped locally. If the existing centroid has a relationship, AGE raises before the new centroid is created; `persist_soc_centroid()` catches and returns `False`.

## Runtime Micro-Probes
Direct store write probe:
- Probe category: `diagnostic_probe_persist_false_20260608`.
- First write through `AGEGraphStoreAdapter.update_centroid(domain="soc", category=probe, action="investigate", caused_by_decision_id="3fc7afa8-...")` succeeded and returned `None`; readback showed a diagnostic `L5Centroid` and `SHAPED_BY` to `DIAG-E3-CRED-001`.
- Second write to the same `(domain, category, action)` failed with:
```text
Cannot delete a vertex that has edge(s). Delete the edge(s) first, or try DETACH DELETE.
```
- The failing query was the store's `DELETE c` query for the existing `L5Centroid`.
- This probe wrote only diagnostic nodes/edges in `soc_graph_diag`; no production/default graph was touched.

Read-only state endpoint:
- `/api/triage/learning-state?category=credential_access` returned phase `MEAN_CONVERGENCE`.
- `/api/soc/learning-state` returned `frozen=false`, `decision_count=19`, `verified_decisions=19`, and graph-derived IKS fields.

Results:
- The store can write a new centroid.
- The store cannot replace an existing centroid after `SHAPED_BY` exists because it uses plain `DELETE`.
- This exactly matches why the first earlier credential_access/investigate L5 row exists, while later DIAG-E3-CRED credential_access/investigate L5 writes return false.

Limitations:
- The direct probe intentionally left a diagnostic `L5Centroid` category in `soc_graph_diag` because no safe cleanup helper was used and deleting related nodes manually would be outside this diagnostic's scope.

## Root Cause Classification
- Primary: E. STORE_WRITE_FAILS.
- Secondary: response observability is incomplete because `persist_soc_centroid()` returns bool only and the route collapses all false causes to `persist_soc_centroid_returned_false`.
- rejected causes:
  - A. POST_CENTROID_MISSING: rejected. Runtime `_cu`/centroid_update exists; phase and indexes are valid.
  - B. CATEGORY_ACTION_INDEX_MISMATCH: rejected. Source and runtime agree on `credential_access` index 0 and `investigate` index 1.
  - C. PHASE_GATE_FALSE: rejected. Runtime learning-state endpoint returns `MEAN_CONVERGENCE`.
  - D. STORE_UNAVAILABLE_OR_WRONG_SHAPE: rejected. Conservation state persists and direct store probe can write a new `L5Centroid`.
  - F. STORE_RETURN_CONTRACT_MISMATCH: rejected. Adapter returns `None` on success, but `persist_soc_centroid()` would still return `True` after a non-throwing call; runtime readback proves the DIAG-E3-CRED write did not happen.
  - G. DECISION_ID_OR_SHAPED_BY_ONLY: rejected as primary. SHAPED_BY edge issues cannot explain no new `L5Centroid`; here the delete fails before create.
  - H. WRONG_GRAPH_OR_DOMAIN: rejected. All probes and readbacks used `soc_graph_diag` and `domain="soc"`.
  - I. RESPONSE_STATUS_BUG: rejected. AGE readback confirms no DIAG-E3-CRED-caused L5Centroid/SHAPED_BY.
- evidence: existing credential_access/investigate centroid has `SHAPED_BY`; store update tries to delete it with `DELETE c`; direct probe reproduced that exact failure on a diagnostic category.

## Blast-Radius and Hack-vs-Systemic Analysis
Candidate 1 — Fix category/action index mapping.
- Classification: INCOMPLETE.
- Files/functions: `backend/app/routers/triage.py`, `backend/app/domains/soc/config.py`.
- Blast radius: would affect all SOC learning/action indexing if changed.
- Rationale: no mapping mismatch was found. Changing indexes would not fix AGE delete failure.
- Tests required if touched: category/action index round-trip tests and non-referral route tests.
- Hack risk: high if used to make C9B pass without addressing store failure.

Candidate 2 — Fix persist_soc_centroid post-centroid retrieval.
- Classification: INCOMPLETE.
- Files/functions: `backend/app/services/gae_state.py`.
- Blast radius: all SOC L5 centroid persistence status.
- Rationale: post-centroid retrieval is valid; store exception is the blocker. Improving diagnostic return detail here is useful but not enough alone.
- Tests required: missing-store, phase-skip, missing-post-centroid, store-exception reason tests.
- Hack risk: low for observability; incomplete for persistence.

Candidate 3 — Fix store.update_centroid return/status handling.
- Classification: SYSTEMIC if it changes replacement semantics to safely remove existing `SHAPED_BY`/related edges before replacing the centroid, or updates the centroid in place.
- Files/functions: installed `ci_platform.graph.age_graph_store.AGEGraphStore.update_centroid`; adapter tests for `AGEGraphStoreAdapter.update_centroid`.
- Blast radius: all L5Centroid updates for all domains/categories/actions using this store. This is intended because repeated centroid update is a canonical operation.
- Risk: must avoid false success; verify actual row exists and SHAPED_BY edge is correct after repeated writes.
- Tests required: first centroid write, repeated write after SHAPED_BY exists, SHAPED_BY points to the latest Decision, no duplicate active centroid for same `(domain, category, action)`, no wrong graph/domain writes.
- Hack risk: low if implemented in canonical store semantics; high if it just swallows delete errors.

Candidate 4 — Improve response skip reason precision.
- Classification: SYSTEMIC as observability, INCOMPLETE as a persistence fix.
- Files/functions: `backend/app/services/gae_state.py`, `backend/app/routers/triage.py`.
- Blast radius: response fields and logs for all SOC L5 persistence attempts.
- Rationale: would expose `store_delete_failed_existing_relationship` or equivalent instead of `persist_soc_centroid_returned_false`.
- Tests required: response reason tests for store exception, phase gate, missing store.
- Hack risk: low, but it does not make Diagnostic E pass by itself.

Candidate 5 — Add fallback persistence from `_cu` update payload.
- Classification: HACK / TOO_RISKY.
- Rationale: unless it still writes through canonical store semantics and verified scorer state, this risks treating legacy/update payload as L5 proof and bypassing the real failing store path.
- Blast radius: could create fake or duplicate L5 evidence and invalidate Diagnostic F.
- Reject unless it is only used as validated data passed to the canonical fixed store.

Candidate 6 — Loosen conservation/phase gate further.
- Classification: HACK / TOO_RISKY.
- Rationale: gate is not the current blocker; learning-state shows `MEAN_CONVERGENCE`, and the outcome response already reaches `persist_soc_centroid()`.
- Blast radius: could weaken conservation safety across production SOC learning.
- Reject.

## Recommended Future Fixer
- selected candidate: Candidate 3, plus Candidate 4 for precise response/log status.
- files/functions:
  - Primary: `ci_platform.graph.age_graph_store.AGEGraphStore.update_centroid`.
  - Secondary observability: `backend/app/services/gae_state.persist_soc_centroid` and `backend/app/routers/triage.report_decision_outcome`.
- required behavior:
  - Repeated `update_centroid(domain, category, action, ...)` must safely replace or update the active `L5Centroid` for that key even when the existing centroid has `SHAPED_BY`.
  - Preserve one active centroid per `(domain, category, action)` unless the product explicitly designs centroid history.
  - Create or refresh `SHAPED_BY` to the actual AGE `Decision.decision_id`.
  - Return/surface precise status: success, skipped by phase/store absence/post-centroid absence, or store exception with safe error type.
- tests:
  - AGE store unit/integration test for first write and repeated write with existing `SHAPED_BY`.
  - SOC outcome test where two successful outcomes for the same category/action both report `l5_centroid_persisted=true`.
  - Test that SHAPED_BY points to the latest real Decision ID.
  - Test that store exceptions are surfaced as precise skip/failure reasons without faking success.
- safeguards:
  - Do not change action selection or scorer update behavior.
  - Do not disable conservation or phase gates.
  - Keep all writes on the configured `AGE_GRAPH_NAME`.
  - Verify actual row/edge readback in Diagnostic E after backend restart.
- do-not-do list:
  - Do not hardcode DIAG-E3/C9B/credential_access/investigate.
  - Do not replace `DELETE` failure with swallowed success.
  - Do not write fake L5Centroid/SHAPED_BY rows outside the canonical store.
  - Do not treat legacy `centroid_update` as proof of L5 persistence.
  - Do not loosen conservation/phase gates for this issue.
- restart: YES, backend restart required after code/package change.
- rerun: YES, rerun Diagnostic E with fresh IDs; Diagnostic F remains blocked until Diagnostic E shows `L5Centroid > 0` and `SHAPED_BY > 0` for the fresh proof IDs.

## Diagnostic Limitations
- No code was modified.
- No tests were run.
- No app server was restarted.
- A direct write probe used only `soc_graph_diag` and diagnostic category `diagnostic_probe_persist_false_20260608`.
- Diagnostic E must be rerun after the future fix.

## Follow-up Fix — L5 current-state upsert in AGEGraphStore

Date: June 8, 2026

- v6.7 Roadmap decision: `AGEGraphStore` uses one `_l5_upsert_current()` current-state method for `L5Centroid`, `L5ConservationState`, and `L5DKWeight`.
- Implementation summary: `_l5_upsert_current()` performs create-on-empty, in-place `SET` on an existing current node, explicit both-direction edge cleanup for garbled duplicate states, and optional latest-edge replacement for `SHAPED_BY` / `TRIGGERED_BY`.
- Chosen semantics: one current node per identity, latest provenance edge only, no centroid version history, no `DETACH DELETE` for normal L5 updates, and no DK archive chain in normal `update_dk_weights()`.
- Files changed:
  - `ci-platform/tests/test_l5_upsert_current.py`
- Source status:
  - `ci-platform/ci_platform/graph/age_graph_store.py` already contains `_l5_upsert_current()`.
  - `update_centroid()`, `update_conservation_state()`, and `update_dk_weights()` already call `_l5_upsert_current()`.
  - `ci-platform/ci_platform/graph/age_sdk_adapter.py` signatures remain unchanged.
- Tests run:
  - `cd ci-platform; python -m pytest tests/test_l5_upsert_current.py -q --tb=short` -> 33 passed.
  - `cd ci-platform; python -m pytest tests -q --timeout=120 -k "l5 or centroid or conservation or dk or SHAPED_BY or TRIGGERED_BY or update_centroid or update_dk"` -> 167 passed, 2 skipped, 326 deselected.
  - `cd gen-ai-roi-demo-v4-v50; $env:PYTHONPATH = "..\ci-platform;$env:PYTHONPATH"; python -m pytest backend/tests/test_soc_dk_l5.py backend/tests/test_soc_c9b_l5_proof.py backend/tests/test_rl_feature_flags.py -q --tb=short` -> 44 passed.
- ci-platform import path / runtime action needed:
  - Default Python import path still resolves `ci_platform` to site-packages: `C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\proj-envs\python_expts_venv\Lib\site-packages\ci_platform\graph\age_graph_store.py`.
  - SOC targeted tests validated the source repo only after `PYTHONPATH=..\ci-platform`.
  - Before live Diagnostic E rerun, install the source package with `pip install -e .\ci-platform` or start the backend with `PYTHONPATH` including the source `ci-platform` path.
- Expected behavior after fix:
  - Repeated `update_centroid(domain, category, action, ...)` no longer deletes an edge-bearing `L5Centroid`; it updates the current node and replaces only the outgoing `SHAPED_BY` edge.
  - `update_conservation_state()` keeps one current `L5ConservationState` per domain and preserves same-status `TRIGGERED_BY` edges.
  - `update_dk_weights()` keeps one current `L5DKWeight` per domain and preserves Welford fields as current audit state.
- Backend restart / editable install requirement: YES.
- Diagnostic E rerun required: YES, on a fresh graph such as `soc_graph_diag_e4` with fresh IDs.
- Diagnostic F remains blocked until Diagnostic E passes with `L5Centroid > 0` and `SHAPED_BY > 0`.
- This follow-up does not claim Diagnostic E has passed; it records the source-level store fix and targeted regression results only.
