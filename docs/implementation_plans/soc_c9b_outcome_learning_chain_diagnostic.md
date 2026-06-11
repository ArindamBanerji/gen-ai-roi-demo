# SOC C9B Outcome Route -> Learning Chain Diagnostic

Date: 2026-06-08
Model: gpt-5.3
Task Type: Critical broken-code-friendly diagnostic audit only
Repo: C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50

## Executive Summary
- Learning chain verdict: CONDITIONAL_SKIP_RISK.
- Outcome endpoint: POST /api/alert/outcome, implemented by report_decision_outcome().
- Outcome write: Decision properties are verified in AGE by setting outcome, correct, verified_at_epoch, override_comment, and verified_by; no Outcome node or HAS_OUTCOME edge is created by this active handler.
- Factor vector source: d.factor_vector returned from the Decision node and JSON-decoded if stored as a string.
- Scorer update: ProfileScorer.update() is only reached through guarded_update() when _soc_learning_enabled() is true, action_name is in SCORER_ACTIONS, conservation does not fail closed, and spike/freeze guards allow the update.
- DK reestimate: attempted after a successful guarded ProfileScorer update via getattr(_ps_out, "reestimate_dk") and _reestimate_dk().
- DK persistence: attempted only when reestimate succeeds, through persist_soc_dk_weights() and persist_dk_after_reestimate(); it requires an initialized L5 learning store and Welford observations.
- Centroid update: attempted only after a successful ProfileScorer update through persist_soc_centroid(); it writes L5Centroid/SHAPED_BY only when a learning store exists and the category phase is MEAN_CONVERGENCE.
- Conservation update: LearningHealthMonitor.evaluate() is called before ProfileScorer update; L5ConservationState persistence is conditional and skipped for CALIBRATING status.
- Learning store source: app.services.gae_state initializes an AGEGraphStoreAdapter only when GRAPH_DSN is set; AGE_GRAPH_NAME defaults to soc_graph.
- Blocks 5-decision proof: YES, under current defaults, because LEARNING_ENABLED defaults False and therefore the ProfileScorer/L5 centroid/SHAPED_BY branch is inactive unless SOC_LEARNING_ENABLED is set true.
- Blocks 210 DK proof: YES, under current defaults, because the same disabled branch prevents ProfileScorer update, Welford update, DK reestimate, and DK persistence.
- Future fixer needed: YES.
- Recommended next step: Run a targeted fixer or runtime setup prompt that explicitly enables SOC learning for diagnostic graphs and verifies GRAPH_DSN/AGE_GRAPH_NAME before attempting Diagnostic E/F.

## Path Resolution
- Repo path: C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50.
- Outcome endpoint candidates: backend/app/routers/triage.py contains /alert/outcome and /action/execute candidates from route searches.
- Selected endpoint: backend/app/routers/triage.py:1038-1039, @router.post("/alert/outcome") and report_decision_outcome(request: OutcomeRequest).
- API prefix evidence: prior Diagnostic B and current main.py search show triage router mounted with prefix="/api"; selected runtime path is /api/alert/outcome.
- Files/functions read: backend/app/routers/triage.py report_decision_outcome; backend/app/models/schemas.py OutcomeRequest; backend/app/domains/soc/config.py LEARNING_ENABLED/build_profile_scorer; backend/app/services/gae_state.py learning store, scorer lock, Welford, DK/centroid persistence, guarded_update; backend/app/services/learning_health.py conservation evaluation/persistence; ci-platform/ci_platform/graph/age_sdk_adapter.py L5 adapter methods; ci-platform/ci_platform/graph/age_graph_store.py L5 write and verified-outcome methods.
- Prior diagnostics found: soc_c9b_seed_analyze_contract_diagnostic.md and soc_c9b_analyze_scorer_call_chain_diagnostic.md were present and read for context.

## Q1 - Endpoint Path, Method, Function
- Method/path/function: POST /api/alert/outcome -> report_decision_outcome().
- Evidence: backend/app/routers/triage.py:1038 has @router.post("/alert/outcome") and backend/app/routers/triage.py:1039 defines async def report_decision_outcome(request: OutcomeRequest).
- Prefix: main.py mounts the triage router with /api, so the external route is /api/alert/outcome.

## Q2 - Request Body Format
- Pydantic model: OutcomeRequest.
- Fields:
  - alert_id: str.
  - decision_id: str.
  - outcome: Literal["correct", "incorrect"].
  - analyst_action: Optional[str] = None.
  - override_comment: Optional[str] = None.
- Evidence: backend/app/models/schemas.py:40-49 defines class OutcomeRequest and these fields. The handler receives OutcomeRequest at backend/app/routers/triage.py:1039.
- The request includes both actual outcome semantics and decision_id; the actual analyst action field is named analyst_action, not actual_action.

## Q3 - Outcome Write / Decision Verification
- Present: YES, the handler marks the Decision verified by setting properties on the Decision node.
- Exact write: backend/app/routers/triage.py:1089-1108 runs a MATCH on Decision by decision_id, optionally matches the Alert, then sets d.outcome, d.correct, d.verified_at_epoch, d.override_comment, and d.verified_by.
- verified_at_epoch: YES, set at backend/app/routers/triage.py:1095.
- status: NO, no d.status assignment appears in the active verification query.
- is_correct: NO, the active field is d.correct, not d.is_correct.
- OutcomeEntry node/HAS_OUTCOME edge: NO evidence in this route. The handler records a framework audit event and stores d.outcome_entry_hash/d.outcome_chain_index at backend/app/routers/triage.py:1121-1133, but the active Cypher does not create an Outcome node or HAS_OUTCOME edge.
- Risk: NON_BLOCKING_RISK for a property-based 5-decision smoke, but a possible BLOCKS_210_DK_PROOF risk for components that use graph-store verified-outcome queries, because ci-platform/ci_platform/graph/age_graph_store.py:1538-1555 expects MATCH (d:Decision)-[:HAS_OUTCOME]->(o:Outcome) for get_verified_decisions/count_verified.

## Q4 - Factor Vector Source
- Present: YES.
- Source field: d.factor_vector.
- Retrieval: backend/app/routers/triage.py:1098 returns d.factor_vector AS factor_vector.
- Parsing: backend/app/routers/triage.py:1160-1167 reads record.get("factor_vector") and json.loads() it when it is a string; parse failure sets fv = None.
- Validation: backend/app/routers/triage.py:1222 passes fv to _validate_scoring_factor_vector(fv) before learning for scorable actions.
- Same vector as score time: the handler uses the Decision node's stored factor_vector, which is the intended score-time vector; this audit did not execute runtime to verify the stored value.

## Q5 - Scorer Update Call
- ProfileScorer.update is present but conditional.
- Legacy update: backend/app/routers/triage.py:1224-1232 calls learning_state.update(action_index=..., action_name=..., outcome=..., f=..., confidence_at_decision=...). This updates the legacy LearningState, not the ProfileScorer/L5 DK chain.
- ProfileScorer branch gate: backend/app/routers/triage.py:1277-1281 states ProfileScorer.update is gated by LEARNING_ENABLED and checks if _soc_learning_enabled() and action_name in SCORER_ACTIONS.
- Exact ProfileScorer call path: backend/app/routers/triage.py:1355-1363 calls _guarded_update(_ps_out, f=f.flatten(), category_index=_cat_idx_out, action_index=action_index, correct=_correct, category_name=_cat_name_out, gt_action_index=_gt_idx).
- Leaf call: backend/app/services/gae_state.py:899-953 defines guarded_update() and returns scorer.update(f=f, category_index=category_index, action_index=action_index, correct=correct, **kwargs) after guard checks.
- Category derivation: backend/app/routers/triage.py:1282-1290 resolves alert_type to category and maps it with SOCDomainConfig().get_category_index().
- Action derivation: backend/app/routers/triage.py:1223 maps action_name through list(SCORER_ACTIONS).index(action_name); backend/app/routers/triage.py:1292-1302 uses analyst_action when valid or falls back to the predicted action and correct flag.
- Severity: BLOCKS_5_DECISION and BLOCKS_210_DK_PROOF under current defaults because config.py sets LEARNING_ENABLED = False.

## Q6 - DK Reestimate
- Present but conditional.
- Call: backend/app/routers/triage.py:1374-1379 obtains _reestimate_dk = getattr(_ps_out, "reestimate_dk", None), calls it if callable, and sets _reestimate_ok = True.
- Exception behavior: backend/app/routers/triage.py:1380-1384 catches any exception and logs a warning; the endpoint does not fail the request.
- Source availability: the local repo search did not find a concrete gae/profile_scorer.py file under the repo, but SOC config imports ProfileScorer from gae.profile_scorer at backend/app/domains/soc/config.py:17-18. Therefore this audit verifies the route's call shape, not the external ProfileScorer implementation body.
- Severity: BLOCKS_210_DK_PROOF if callable reestimate_dk is absent, if it throws, or if the ProfileScorer branch is disabled; not needed for a 5-decision smoke below the 200-decision threshold.

## Q7 - DK Persistence
- Present but conditional.
- Handler call: backend/app/routers/triage.py:1403-1405 calls _persist_soc_dk_weights(_ps_out, logger=logger) only when _reestimate_ok is true.
- Exception behavior: backend/app/routers/triage.py:1406-1410 logs DK persistence exceptions without failing the endpoint.
- Store gate: backend/app/services/gae_state.py:312-333 defines persist_soc_dk_weights(); it returns False if get_learning_store() is None or DK weights cannot be read.
- Welford gate: backend/app/routers/triage.py:1368 updates the DK Welford tracker only after a successful ProfileScorer update; copilot_sdk/scoring/dk_persistence.py logic was imported at backend/app/services/gae_state.py:28 and persist_dk_after_reestimate requires Welford state.
- L5 write evidence: ci-platform/ci_platform/graph/age_sdk_adapter.py:312-333 exposes update_dk_weights(); ci-platform/ci_platform/graph/age_graph_store.py:1696-1751 writes L5DKWeight and Welford JSON fields including confirmed_mean_json and confirmed_m2_json.
- Severity: BLOCKS_210_DK_PROOF when the ProfileScorer branch is disabled, the learning store is absent, Welford has no observations, reestimate fails, or persistence fails. It is NOT_NEEDED_FOR_5_DECISION below the 200-decision DK threshold.

## Q8 - Centroid Update
- Present but conditional.
- Handler call: backend/app/routers/triage.py:1385-1397 calls _persist_soc_centroid(... caused_by_decision_id=request.decision_id, pre_centroid=...).
- Store/phase gates: backend/app/services/gae_state.py:358-399 defines persist_soc_centroid(); it returns False if no store/update_centroid method exists, if phase != "MEAN_CONVERGENCE", or if the post centroid is unavailable.
- L5 write evidence: ci-platform/ci_platform/graph/age_sdk_adapter.py:291-307 exposes update_centroid(); ci-platform/ci_platform/graph/age_graph_store.py:1604-1641 writes L5Centroid and a SHAPED_BY edge when caused_by_decision_id is present.
- Legacy write: backend/app/routers/triage.py:1433-1460 also writes centroid_delta_norm/category/correct/verified_at_epoch back to the Decision when legacy learning_state.update returns a centroid_update, but that is not the L5Centroid/SHAPED_BY persistence path.
- Severity: BLOCKS_5_DECISION if LEARNING_ENABLED remains false or the learning store is absent, because L5Centroid and SHAPED_BY are produced only through the ProfileScorer/L5 persistence branch.

## Q9 - Conservation Update
- Present but conditional.
- Handler call: backend/app/routers/triage.py:1267-1275 calls LearningHealthMonitor.evaluate(neo4j_client) and fail-closes by setting _conservation_block = True on exception.
- Persistence call: backend/app/services/learning_health.py:368 calls await _persist_l5_conservation_state(result) only after baseline evaluation, not during early CALIBRATING returns.
- Persistence gates: backend/app/services/learning_health.py:539-556 skips persistence unless status is GREEN/AMBER/RED and a learning store exists.
- L5 write evidence: backend/app/services/learning_health.py:583-598 calls store.update_conservation_state(domain="soc", ...); ci-platform/ci_platform/graph/age_sdk_adapter.py:338-370 and ci-platform/ci_platform/graph/age_graph_store.py:1821-1875 provide the L5ConservationState write path.
- Calibration behavior: backend/app/services/learning_health.py:34 sets CALIBRATION_DECISIONS = 300; backend/app/services/learning_health.py:295-319 returns CALIBRATING before that threshold and does not call _persist_l5_conservation_state.
- Severity: NON_BLOCKING_RISK for 5-decision centroid/SHAPED_BY smoke. For 210-decision DK proof, conservation persistence may still be absent because the configured conservation calibration threshold is 300, so classify as NON_BLOCKING_RISK unless the proof explicitly requires L5ConservationState by 210.

## Q10 - Exact Operation Order
1. Request parse into OutcomeRequest.
2. Duplicate feedback check with get_feedback_status(request.alert_id) at backend/app/routers/triage.py:1057-1062.
3. Compute outcome_int/correct_bool/outcome_label at backend/app/routers/triage.py:1071-1073.
4. Determine analyst_id, defaulting to anonymous when request.state is absent at backend/app/routers/triage.py:1078-1082.
5. MATCH Decision, optionally match Alert, set Decision verification fields, and return factor_vector/action/category/alert_type at backend/app/routers/triage.py:1089-1108.
6. If no Decision row, raise 404 at backend/app/routers/triage.py:1110-1117.
7. Record audit outcome and store hash/index on the Decision if audit succeeds at backend/app/routers/triage.py:1121-1133.
8. Parse factor_vector and resolve category at backend/app/routers/triage.py:1160-1180.
9. If action is not in SCORER_ACTIONS, skip learning update and increment legacy decision_count at backend/app/routers/triage.py:1204-1220.
10. If action is scorable, validate factor_vector and call legacy learning_state.update at backend/app/routers/triage.py:1222-1232.
11. Evaluate conservation health before ProfileScorer update at backend/app/routers/triage.py:1263-1275.
12. If _soc_learning_enabled() and action is scorable, resolve category index, derive gt_action_index/correct, acquire the live scorer, and call guarded_update at backend/app/routers/triage.py:1281-1363.
13. If guarded_update returns a CentroidUpdate, update DK Welford, attempt reestimate_dk, persist L5Centroid/SHAPED_BY, and persist L5DKWeight/Welford if reestimate succeeded at backend/app/routers/triage.py:1364-1410.
14. Write legacy centroid_delta_norm back to the Decision when legacy learning_state.update produced a centroid update at backend/app/routers/triage.py:1433-1460.
15. Response construction continues after the inspected block; this diagnostic did not run the route.

## Q11 - Learning Skip Gates
- Duplicate feedback gate: get_feedback_status can return has_feedback and raise 400 before verification, backend/app/routers/triage.py:1057-1062. Severity: INFO_ONLY.
- Decision not found: raises 404 before any learning, backend/app/routers/triage.py:1110-1117. Severity: INFO_ONLY.
- Routing action gate: action_name not in SCORER_ACTIONS skips learning update, backend/app/routers/triage.py:1204-1220. Severity: BLOCKS_5_DECISION if all diagnostic actions are refer_to_analyst; otherwise expected routing behavior.
- Factor vector validation: _validate_scoring_factor_vector(fv) at backend/app/routers/triage.py:1222 can fail before learning when fv is missing/invalid. Severity: BLOCKS_5_DECISION.
- Conservation health fail-closed: exception during LearningHealthMonitor.evaluate sets _conservation_block = True, backend/app/routers/triage.py:1267-1275. Severity: BLOCKS_5_DECISION and BLOCKS_210_DK_PROOF when triggered.
- ProfileScorer learning gate: _soc_learning_enabled() must be true at backend/app/routers/triage.py:1281. Default is false in backend/app/domains/soc/config.py:63-74. Severity: BLOCKS_5_DECISION and BLOCKS_210_DK_PROOF under current defaults.
- Unclassified category: resolve_alert_category returning unclassified raises ValueError, backend/app/routers/triage.py:1282-1289. Severity: BLOCKS_5_DECISION if seed/analyze category is wrong.
- guarded_update gates: volume spike, frozen category, scorer pause, and spike cap can return None at backend/app/services/gae_state.py:924-953. Severity: CONDITIONAL_SKIP_RISK.
- L5 store gate: GRAPH_DSN absent makes _init_learning_store return None, backend/app/services/gae_state.py:156-173; DK and centroid persistence return False without a store at backend/app/services/gae_state.py:314-316 and 370-372. Severity: BLOCKS_5_DECISION for L5Centroid/SHAPED_BY and BLOCKS_210_DK_PROOF for DK persistence.
- Centroid phase gate: persist_soc_centroid skips unless phase == MEAN_CONVERGENCE, backend/app/services/gae_state.py:373-375. Severity: INFO_ONLY for post-transition DK phase, but BLOCKS_5_DECISION if phase is not MEAN_CONVERGENCE during the smoke.
- Conservation CALIBRATING gate: LearningHealthMonitor returns before persistence when decision_count < 300, backend/app/services/learning_health.py:295-319. Severity: NON_BLOCKING_RISK for 5/210 unless L5ConservationState is explicitly required at those counts.

## Q12 - Learning Store Source
- Source: app.services.gae_state._init_learning_store().
- Initialization: backend/app/services/gae_state.py:156-173 reads GRAPH_DSN, returns None when blank, uses AGE_GRAPH_NAME or "soc_graph", loads AGEGraphStoreAdapter, and returns the adapter.
- Lifecycle: backend/app/services/gae_state.py:176-272 initializes the module-level LearningState and ProfileScorer once during startup initialization and assigns _learning_store at line 269.
- Startup evidence: backend/app/main.py:268-269 imports and calls init_learning_state() during startup_event().
- Same store use: get_learning_store() at backend/app/services/gae_state.py:275-277 is used by persist_soc_dk_weights(), persist_soc_centroid(), and LearningHealthMonitor._persist_l5_conservation_state().
- Persistent or in-memory: the L5 store is persistent AGE only when GRAPH_DSN is present. Otherwise L5 persistence paths are disabled by returning False/None.

## Full Learning Chain Matrix
| Step | Present? | Function/Call | Store/Args | Evidence | Risk |
| --- | --- | --- | --- | --- | --- |
| write_outcome | Partial | Active route sets Decision outcome fields; no graph Outcome node from this route | Decision by decision_id | triage.py:1089-1108; triage.py:1121-1133 | NON_BLOCKING_RISK; possible BLOCKS_210_DK_PROOF for graph-store verified queries |
| Decision verified fields | Yes | SET d.outcome, d.correct, d.verified_at_epoch, d.override_comment, d.verified_by | AGE Decision node | triage.py:1091-1097 | OK for property-based verification |
| factor_vector retrieval | Yes | RETURN d.factor_vector; json.loads if string | Decision factor_vector | triage.py:1098; triage.py:1160-1167 | BLOCKS_5_DECISION if missing/invalid |
| scorer.update | Conditional | guarded_update(...)->scorer.update(...) | f.flatten(), category_index, action_index, correct, gt_action_index | triage.py:1281-1363; gae_state.py:899-953 | BLOCKS_5_DECISION and BLOCKS_210_DK_PROOF under LEARNING_ENABLED default false |
| reestimate_dk | Conditional | getattr(_ps_out, "reestimate_dk")(); warning on exception | live ProfileScorer | triage.py:1374-1384 | BLOCKS_210_DK_PROOF if absent/failing/skipped |
| persist_dk/L5DKWeight | Conditional | persist_soc_dk_weights()->persist_dk_after_reestimate()->update_dk_weights | domain="soc", Welford tracker snapshot | triage.py:1403-1410; gae_state.py:312-333; age_graph_store.py:1696-1751 | BLOCKS_210_DK_PROOF if store/Welford/reestimate missing |
| update_centroid/L5Centroid | Conditional | persist_soc_centroid()->store.update_centroid | domain="soc", category, action, caused_by_decision_id | triage.py:1385-1397; gae_state.py:358-399; age_graph_store.py:1604-1641 | BLOCKS_5_DECISION if disabled/store missing |
| update_conservation | Conditional | LearningHealthMonitor.evaluate()->_persist_l5_conservation_state()->store.update_conservation_state | domain="soc", status, alpha, q, V, theta | triage.py:1267-1275; learning_health.py:368; learning_health.py:539-606 | NON_BLOCKING_RISK for 5/210 below 300-decision calibration |

## Severity Matrix
| Link | Severity | Evidence | Future fixer scope |
| --- | --- | --- | --- |
| ProfileScorer/L5 branch disabled by default | BLOCKS_5_DECISION; BLOCKS_210_DK_PROOF | config.py:63-74 sets LEARNING_ENABLED = False unless SOC_LEARNING_ENABLED is true; triage.py:1277-1281 gates ProfileScorer.update on _soc_learning_enabled() | For diagnostic/proof runs, require SOC_LEARNING_ENABLED=true and document startup contract; for product behavior, decide whether C9B should enable live learning by default or via explicit diagnostic mode |
| L5 learning store optional on GRAPH_DSN | BLOCKS_5_DECISION; BLOCKS_210_DK_PROOF when unset | gae_state.py:156-173 returns None without GRAPH_DSN; gae_state.py:314-316 and 370-372 return False without a store | Ensure diagnostic startup sets GRAPH_DSN and AGE_GRAPH_NAME and assert store availability before C9B runtime proof |
| No Outcome node/HAS_OUTCOME edge in active route | NON_BLOCKING_RISK; possible BLOCKS_210_DK_PROOF for graph-store verified-count consumers | triage.py:1089-1108 sets Decision fields only; age_graph_store.py:1538-1555 verified queries expect Decision-[:HAS_OUTCOME]->Outcome | Decide whether /api/alert/outcome should call AGE graph-store write_outcome or whether property-based verification is canonical |
| Routing action skips learning | BLOCKS_5_DECISION if all loops return refer_to_analyst; otherwise INFO_ONLY | triage.py:1204-1220 | Use seed/context that produces scorable actions or explicitly allow outcome for referral-only routing |
| Conservation/spike/freeze guarded_update skips | CONDITIONAL_SKIP_RISK | triage.py:1267-1275; gae_state.py:924-953 | Surface skip reason in proof logs/response and ensure diagnostic graph does not trigger freeze/spike guards |
| DK reestimate/persist warnings do not fail route | BLOCKS_210_DK_PROOF if warning path occurs | triage.py:1380-1410 | For DK proof, promote reestimate/persist failure to explicit diagnostic failure or expose status in response/log contract |

## Chain Verdict
- Verdict labels: CONDITIONAL_SKIP_RISK.
- Blocks 5-decision proof: YES under current defaults.
- Blocks 210 DK proof: YES under current defaults.
- Rationale: the endpoint contains the intended write/update/reestimate/persist calls, but the ProfileScorer/L5 branch that produces L5Centroid, SHAPED_BY, Welford, and L5DKWeight is gated by _soc_learning_enabled(); SOC config defaults this to False. L5 persistence also requires GRAPH_DSN-backed learning_store, and several guards can skip learning without failing the HTTP request.
- Future fixer scope: minimal runtime/proof setup fixer should require SOC_LEARNING_ENABLED=true, GRAPH_DSN set, AGE_GRAPH_NAME set to the throwaway graph, and should assert learning_store availability before Diagnostic E/F. A design fixer is needed if property-only Decision verification is insufficient and HAS_OUTCOME Outcome nodes are required by canonical graph-store consumers.

## Diagnostic Limitations
- No code was modified.
- No tests were run.
- No app server was run.
- No seed scripts were run.
- No smoke scripts were run.
- Analysis is source-level only.
