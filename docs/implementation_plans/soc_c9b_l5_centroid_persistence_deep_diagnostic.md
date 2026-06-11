# SOC C9B Deep Diagnostic — Outcome L5Centroid/SHAPED_BY Persistence

Date: 2026-06-08
Model: gpt-5.3
Task Type: Deep diagnostic audit; follow-up targeted fixer applied
Repo: C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50
Diagnostic Graph: soc_graph_diag

## Executive Summary
- Root cause classification: B. Gate skip, specifically conservation RED/auto-pause blocks the ProfileScorer L5 path before `persist_soc_centroid()` is reached.
- Outcome path reached: YES. DIAG-E2 Decisions are present with `domain='soc'`, `outcome='correct'`, `correct=true`, and factor vectors.
- centroid_update payload returned: YES, but source trace shows this payload comes from legacy `learning_state.update()` / `wu.centroid_update`, not from L5 persistence.
- persist_soc_centroid called: NOT PROVEN for DIAG-E2. Source only calls it when `_cu is not None`; conservation RED can make `guarded_update()` return `None` first.
- learning_store: AVAILABLE. `L5ConservationState` exists in `soc_graph_diag`, and source initializes the store from `GRAPH_DSN` plus `AGE_GRAPH_NAME`.
- update_centroid: Source writes `L5Centroid` with `domain`, `category`, `action`, `vector_json`, `delta_norm`, and optional `SHAPED_BY`.
- L5Centroid readback: 0 total and 0 for `domain='soc'`.
- SHAPED_BY readback: 0.
- Conservation readback: one `L5ConservationState` with `status='RED'`, `alpha=0.1667`, `q=1.0`, `V=5`, `product=0.833333`, `theta_min=28.236`.
- Decision ID mismatch risk: Secondary/rejected for current `L5Centroid=0`; Decision IDs align, and `update_centroid()` creates `L5Centroid` before attempting `SHAPED_BY`.
- Follow-up fix applied: YES. The outcome route now treats under-calibrated SOC conservation RED/AMBER as non-pausing for the ProfileScorer L5 path, preserves true auto-pause/calibrated RED behavior, and surfaces L5 persistence status in the response.
- Future fixer needed: NO for the diagnosed gate; runtime rerun is required after backend restart.
- Recommended next step: Restart the backend, rerun Diagnostic E with fresh IDs, and do not run Diagnostic F until E proves `L5Centroid > 0` and `SHAPED_BY > 0`.

## Latest Diagnostic E Evidence
- Latest Diagnostic E reported five DIAG-E2 alerts resolving to `credential_access`, all with non-referral `action='investigate'`.
- All five outcome posts succeeded.
- Decision IDs from the report:
  - `DIAG-E2-001`: `4f3bce21-e490-44f3-b25b-2a4723c9d772`
  - `DIAG-E2-002`: `d3331ac4-4357-497b-8c64-0741de2379a2`
  - `DIAG-E2-003`: `b211b9d3-fa13-488e-9ba4-577dcb6c2daa`
  - `DIAG-E2-004`: `4765c909-d4d3-46d5-af61-3cb053f1fc40`
  - `DIAG-E2-005`: `a646eeaf-954f-48d0-9bbd-580c3deac638`
- The latest report states `L5Centroid=0`, `SHAPED_BY=0`, `L5ConservationState=1`, and verdict `BROKEN_LINK_4_5_CENTROID`.

## Runtime/Graph Status
- Backend health: `GET http://127.0.0.1:8001/health` returned `{"status":"healthy","components":{"posterior_store":{"healthy":true}}}`.
- Current graph: runtime probes used `GRAPH_BACKEND=age`, `GRAPH_DSN=host=127.0.0.1 port=5433 dbname=soc_copilot user=postgres password=postgres`, and `AGE_GRAPH_NAME=soc_graph_diag`.
- Relevant counts:
  - SOC Decisions: 12 total.
  - DIAG-E2 Decisions by known IDs: 5.
  - DIAG-E2 Decisions by Alert link: 5.
  - `L5Centroid`: 0.
  - `SHAPED_BY`: 0.
  - `L5DKWeight`: 0.
  - `L5ConservationState`: 1.

## Source Trace — Outcome Handler
- Endpoint: `backend/app/routers/triage.py:1038-1039` defines `@router.post("/alert/outcome")` and `report_decision_outcome()`, mounted under `/api` by `backend/app/main.py:122`.
- Request/Decision lookup: `backend/app/routers/triage.py:1089-1108` matches `Decision {decision_id: request.decision_id}`, sets `outcome`, `correct`, `verified_at_epoch`, `override_comment`, and `verified_by`, and returns `factor_vector`, `action`, `confidence`, `category`, and `alert_type`.
- Legacy centroid update path: `backend/app/routers/triage.py:1221-1232` validates the factor vector and calls `learning_state.update(...)` for scorer actions.
- Response payload creation: `backend/app/routers/triage.py:1433-1460` uses `wu.centroid_update`, writes `d.centroid_delta_norm`, and builds `centroid_update_payload`.
- Response attachment: `backend/app/routers/triage.py:1726-1728` returns `response_body["centroid_update"] = centroid_update_payload`.
- L5 persistence call path: `backend/app/routers/triage.py:1281` gates ProfileScorer learning on `_soc_learning_enabled()` and scorer actions; `backend/app/routers/triage.py:1355-1363` calls `_guarded_update(...)`; `backend/app/routers/triage.py:1364-1397` calls `_persist_soc_centroid(...)` only when `_cu is not None`.

Meaningful operation order:
1. Parse `OutcomeRequest`.
2. Match and verify `Decision`.
3. Legacy `learning_state.update()` creates `wu.centroid_update`.
4. Evaluate conservation health.
5. If `_soc_learning_enabled()` and action is scorable, acquire ProfileScorer.
6. Set scorer conservation status.
7. Call `guarded_update()`.
8. Only if `_cu is not None`, call `persist_soc_centroid()`.
9. Write legacy centroid delta to the Decision and return `centroid_update` payload.

## Source Trace — Gates
- `_soc_learning_enabled()`: `backend/app/routers/triage.py:49-55` returns `is_learning_enabled()` unless the imported constant has been monkeypatched.
- Env-aware learning gate: `backend/app/domains/soc/config.py:66-74` defaults `LEARNING_ENABLED=False`, but `is_learning_enabled()` treats `SOC_LEARNING_ENABLED` values `1/true/yes/on` as enabled.
- Conservation evaluation before ProfileScorer update: `backend/app/routers/triage.py:1263-1275` calls `LearningHealthMonitor.evaluate()`, then sets `_eff_status` from health status or `RED` when `auto_pause_active`.
- Conservation status applied to scorer: `backend/app/routers/triage.py:1350-1352` calls `_ps_out.set_conservation_status(_eff_status)` before `guarded_update()`.
- Guard skip: `backend/app/services/gae_state.py:938-944` returns `None` when `scorer.is_paused` is true.
- ProfileScorer pause behavior: `graph-attention-engine-v50/gae/profile_scorer.py:213-216` documents that `auto_pause_on_amber=True` blocks centroid updates for AMBER/RED; `graph-attention-engine-v50/gae/profile_scorer.py:731-744` pauses on AMBER/RED and exposes that through `is_paused`.
- Current runtime conservation state is RED, so the source path can set `scorer.is_paused=True` before `guarded_update()`.
- Phase gate: `backend/app/services/gae_state.py:373-375` only persists centroid when phase is `MEAN_CONVERGENCE`. Read-only `/api/triage/learning-state?category=credential_access` returned `phase="MEAN_CONVERGENCE"`, so phase is not the observed blocker.
- Try/except behavior: `backend/app/routers/triage.py:1398-1402` logs centroid persistence exceptions as warnings; `backend/app/services/gae_state.py:396-398` catches store exceptions and returns `False`.

## Source Trace — persist_soc_centroid
- Function: `backend/app/services/gae_state.py:358-399`.
- Store lookup: `backend/app/services/gae_state.py:370-372` returns `False` if no store or no `update_centroid`.
- Phase gate: `backend/app/services/gae_state.py:373-375` returns `False` unless the category phase is `MEAN_CONVERGENCE`.
- Post-centroid lookup: `backend/app/services/gae_state.py:376-378` returns `False` if no centroid is available.
- Store write: `backend/app/services/gae_state.py:387-395` calls:
  - `domain="soc"`
  - `category=category`
  - `action=action`
  - `centroid_vector=post`
  - `delta_norm=delta_norm`
  - `caused_by_decision_id=caused_by_decision_id`
- Call site args: `backend/app/routers/triage.py:1385-1397` passes the ProfileScorer, category/action names and indexes, `request.decision_id`, and pre-centroid.
- Skip/error behavior: The function returns `False` without logging for missing store, non-`MEAN_CONVERGENCE` phase, or missing post centroid; it logs and returns `False` on exceptions. The route does not inspect the returned boolean.

## Source Trace — Learning Store / update_centroid
- Store initialization: `backend/app/services/gae_state.py:156-166` reads `GRAPH_DSN` and `AGE_GRAPH_NAME`, constructs `AGEGraphStoreAdapter(dsn=dsn, graph_name=graph_name)`, and logs graph/domain.
- Store access: `backend/app/services/gae_state.py:269` initializes `_learning_store`; `backend/app/services/gae_state.py:275-277` returns it.
- Adapter: installed `ci_platform.graph.age_sdk_adapter.py:291-307` delegates `update_centroid()` to the underlying AGE graph store.
- Runtime store proof: `L5ConservationState` exists in `soc_graph_diag`, and `learning_health.py:554-598` uses the same `get_learning_store()` path to call `store.update_conservation_state(domain="soc", ...)`.
- `update_centroid()` implementation: installed `ci_platform.graph.age_graph_store.py:1351-1388` deletes the prior `L5Centroid` for the same domain/category/action and creates `CREATE (c:L5Centroid {props}) RETURN c`.
- `L5Centroid` properties: installed `age_graph_store.py:1368-1377` includes `domain`, `category`, `action`, `vector_json`, `delta_norm`, `caused_by_decision_id`, and `updated_at_epoch`.
- `SHAPED_BY` creation: installed `age_graph_store.py:1389-1408` then matches the just-created centroid and `Decision {decision_id: caused_by_value}` and creates `(c)-[:SHAPED_BY]->(d)`, logging only on edge failure.
- Domain handling: `persist_soc_centroid()` passes `domain="soc"`, and store props include that domain.
- Important: because `update_centroid()` creates `L5Centroid` before attempting `SHAPED_BY`, a Decision ID mismatch would explain missing `SHAPED_BY` but not `L5Centroid=0`.

## Source Trace — Decision ID Alignment
- Analyze write: Diagnostic B and `backend/app/routers/triage.py:415-425` show a UUID `decision_id` is generated and written to `Decision.decision_id` with `domain='soc'`.
- Outcome lookup: `backend/app/routers/triage.py:1089-1108` matches the same `request.decision_id`.
- L5 edge target: `backend/app/routers/triage.py:1392` passes `request.decision_id` to persistence; installed `age_graph_store.py:1397-1398` matches `Decision {decision_id: caused_by_value}` for `SHAPED_BY`.
- Runtime probe by known DIAG-E2 IDs returned all five Decisions with the expected IDs and linked Alert IDs.
- Risk: Decision ID mismatch is not the primary cause for this run. It remains a secondary edge-only risk if future audit IDs diverge, but it does not explain `L5Centroid=0`.

## Runtime Readback Probe
DIAG-E2 Decision properties:
- Five Decisions were found by known IDs and by `Decision-[:DECIDED_ON]->Alert`.
- Each had `domain='soc'`, `action='investigate'`, `outcome='correct'`, `correct=true`, `category='credential_access'`, and factor vector `[0.825, 1.0, 0.0, 0.4, 0.7, 0.6666666666666666]`.
- `DIAG-E2-001` had `centroid_delta_norm=0.012247448713915891`; the other four had `centroid_delta_norm=0.0`.

L5/readback:
- `MATCH (c:L5Centroid) RETURN count(c) AS total` returned `0`.
- `MATCH (c:L5Centroid) WHERE c.domain = 'soc' RETURN count(c) AS total` returned `0`.
- `MATCH ()-[r:SHAPED_BY]->() RETURN count(r) AS total` returned `0`.
- `MATCH (w:L5DKWeight) RETURN count(w) AS total` returned `0`, expected below the 200-decision DK threshold.
- `MATCH (cs:L5ConservationState)` returned one row:
  - `domain='soc'`
  - `status='RED'`
  - `alpha=0.1667`
  - `q=1.0`
  - `V=5`
  - `theta_min=28.236`
  - `product=0.833333`
  - `categories_total=6`
  - `categories_with_data=1`
  - `complacency_flag='false'`
- Verified SOC Decisions: 5.
- Correct SOC Decisions: 5.

Read-only state endpoint:
- `GET /api/triage/learning-state?category=credential_access` returned `strategy="two_phase"`, `phase="MEAN_CONVERGENCE"`, `alpha=0.5`, `dk_weights=null`, and `decisions_in_category=1`.
- `backend/app/routers/framework_router.py:1031-1117` shows this endpoint reads the in-process ProfileScorer phase/category state.

Raw query notes:
- Initial ad hoc AGE queries using `AS count` or unsupported list predicates produced syntax errors; the final probe used `AS total` and explicit labels/IDs.
- The final probe was read-only and did not mutate graph data.

## Root Cause Classification
- Primary: B. Gate skip: conservation RED/auto-pause makes the ProfileScorer `guarded_update()` return `None`, so `persist_soc_centroid()` is not reached for DIAG-E2 outcomes.
- Secondary:
  - The response `centroid_update` payload is from legacy `learning_state.update()`, so it can appear even when L5 persistence is skipped.
  - `persist_soc_centroid()` and the route swallow or ignore persistence false/exception results, so this failure is not surfaced in the HTTP response.
  - `learning_health._is_learning_enabled()` reads the static `LEARNING_ENABLED` constant rather than env-aware `is_learning_enabled()`, which is a configuration consistency risk, but the observed blocker is RED conservation pause, not default disabled learning.
- Rationale:
  - Store/graph availability is proven by persisted `L5ConservationState`.
  - Phase is `MEAN_CONVERGENCE`, so the phase gate is not the current blocker.
  - Decision IDs align, and missing `SHAPED_BY` cannot explain missing `L5Centroid` because the store creates `L5Centroid` before attempting the edge.
  - Runtime conservation state is `RED`; source sets that status on the scorer before `guarded_update()`; ProfileScorer pauses on AMBER/RED; `guarded_update()` returns `None` when paused; persistence only runs when `_cu is not None`.

Why other causes were rejected:
- A. `PERSIST_FUNC_NOT_CALLED`: true as an execution effect, but not the root source wiring problem. Source contains the call; conservation pause prevents reaching it.
- C. `PHASE_GATE_SKIPS_CENTROID`: rejected for this run because `/api/triage/learning-state` returned `MEAN_CONVERGENCE`.
- D. `LEARNING_STORE_MISSING`: rejected because `L5ConservationState` persisted through the same optional store access pattern.
- E. `WRONG_STORE_OR_GRAPH`: rejected because readback from `soc_graph_diag` sees the conservation state written by the runtime.
- F. `UPDATE_CENTROID_NOOP_OR_WRONG_LABEL`: rejected by source; installed store uses `CREATE (c:L5Centroid ...)`.
- G. `UPDATE_CENTROID_EXCEPTION_SWALLOWED`: possible in general, but not needed to explain this run because conservation pause stops before persistence.
- H. `DECISION_ID_MISMATCH`: rejected as primary because DIAG-E2 Decision IDs align and `L5Centroid` creation precedes edge creation.
- I. `DOMAIN_MISMATCH`: rejected by source; persistence passes and writes `domain='soc'`.
- J. `QUERY_MISMATCH`: rejected because direct all-label `L5Centroid` queries returned 0 and source uses that exact label.

## Future Fixer Scope (Superseded by Follow-up Fix)
- Files/functions:
  - `backend/app/routers/triage.py`, `report_decision_outcome()`, around the conservation evaluation and ProfileScorer update block.
  - `backend/app/services/learning_health.py`, if the calibration/diagnostic conservation status should not hard-freeze small proof runs.
  - Tests under `backend/tests` covering outcome learning, conservation pause, and L5 persistence.
- Required change:
  - Preserve conservation pause for genuine unsafe AMBER/RED production states.
  - For diagnostic/proof or under-calibrated small-run conditions, avoid treating the RED conservation state as a hard block before the first L5 centroid evidence can be persisted, or surface a clear explicit `l5_persistence_skipped_reason` instead of returning a successful outcome with only legacy `centroid_update`.
  - Ensure `persist_soc_centroid()` success/failure is observable in the response or logs for Diagnostic E/F.
  - Align `learning_health._is_learning_enabled()` with env-aware `is_learning_enabled()` if health status should reflect runtime `SOC_LEARNING_ENABLED`.
- Required tests:
  - Non-referral `credential_access` outcome with healthy/calibrating diagnostic conditions calls `persist_soc_centroid()` and writes/records L5 persistence.
  - RED/AMBER conservation with `auto_pause_on_amber=True` still blocks ProfileScorer updates in genuine unsafe cases.
  - Outcome response/reporting distinguishes legacy `centroid_update` from L5 persistence status.
  - `SHAPED_BY` uses the returned AGE Decision `decision_id`.
- Do-not-do list:
  - Do not disable conservation globally.
  - Do not hardcode DIAG-E2 IDs or C9B-only bypasses.
  - Do not fake `L5Centroid` or `SHAPED_BY` evidence.
  - Do not force all credential_access actions to a fixed action.
  - Do not make Diagnostic F run before Diagnostic E proves `L5Centroid` and `SHAPED_BY`.
- Backend restart: YES after any code fix.
- Required rerun: Rerun Diagnostic E after the fix; do not run Diagnostic F until E passes with at least one outcome, `L5Centroid > 0`, and `SHAPED_BY > 0`.

## Follow-up Fix — L5Centroid/SHAPED_BY persistence gate
- Selected option: A — under-calibrated-state bypass of hard auto-pause for real ProfileScorer/L5 evidence.
- Root cause addressed: Runtime conservation health can report RED in a small proof graph because SOC verified coverage is below the calibration threshold. The route passed that RED directly into `ProfileScorer.set_conservation_status()`, causing `guarded_update()` to return `None` before `persist_soc_centroid()` could run.
- Files changed:
  - `backend/app/routers/triage.py`
  - `backend/tests/test_soc_dk_l5.py`
  - `backend/tests/test_soc_c9b_l5_proof.py`
  - `backend/tests/test_rl_feature_flags.py`
- Required behavior after fix:
  - Health `status=CALIBRATING` or `status=RED/AMBER` with `components.verified_decisions < CALIBRATION_DECISIONS` no longer hard-pauses the ProfileScorer L5 branch for successful non-referral outcomes.
  - `auto_pause_active=true` still forces effective RED.
  - Calibrated RED/AMBER states still pause the scorer and preserve conservation safety.
  - The route now records the boolean result from `persist_soc_centroid()` instead of ignoring it.
- L5 persistence response fields added:
  - `l5_centroid_persisted`
  - `l5_shaped_by_attempted`
  - `l5_persistence_skipped_reason`
  - `l5_persistence`
- Tests run:
  - `python -m pytest backend/tests/test_soc_dk_l5.py backend/tests/test_soc_c9b_l5_proof.py -q --tb=short` -> 36 passed.
  - `python -m pytest backend/tests -q --tb=short -k "outcome or centroid or shaped_by or l5 or conservation or learning"` -> 282 passed, 3 skipped, 1531 deselected.
  - `python -m pytest backend/tests -q --tb=short -k "triage or analyze or c9b or referral or credential or learning"` -> 167 passed, 1649 deselected.
- Conservation safety preserved:
  - Tests prove calibrated RED remains RED and `auto_pause_active` still forces RED.
  - Existing conservation enforcement tests still pass in the targeted learning subset.
- Backend restart required: YES. The currently running uvicorn process will not pick up the changed source until restart.
- Required rerun: Rerun Diagnostic E with fresh IDs after restart. Diagnostic F remains blocked until E passes with `L5Centroid > 0` and `SHAPED_BY > 0`.

## Diagnostic Limitations
- This original diagnostic was source/readback-only; the follow-up fixer section above records subsequent code and test changes.
- The app server was not restarted by the fixer.
- Runtime probes were read-only.
- The diagnostic did not inspect live uvicorn foreground logs; it used source, health, API state, and AGE readback.
- Diagnostic E must be rerun after any fix.
