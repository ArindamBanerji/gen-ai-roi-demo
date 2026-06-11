# SOC C9B Analyze Route to Scorer Call Chain Diagnostic

Date: 2026-06-08
Model: gpt-5.3
Task Type: Broken-code-friendly diagnostic audit only; no code changes
Repo: C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50

## Executive Summary
- Scorer chain verdict: OK
- Blocking fixer needed: NO
- Scorer source: module-level LearningState singleton from `app.services.gae_state.get_profile_scorer()`, initialized during app startup and read by the route.
- Category to category_index path: `resolve_alert_category(alert_type)` produces a category string, then `SOCDomainConfig.get_category_index(alert_category)` converts it to an index before scoring.
- Factor vector source: `compute_factor_vector(alert_data, computers, neo4j_client)` returns a NumPy vector from SOC factor computers.
- Scorer method: `_scorer.score(f.flatten(), category_index=_cat_idx)`.
- Decision write: inline AGE/Cypher `CREATE (d:Decision ...)` in `triage.py`, including `domain: 'soc'`.
- Decision ID format: UUID4 string from `str(uuid.uuid4())`.
- Returned action source: starts from scorer result, then may be overridden by low-confidence routing, RL exploration, and referral logic; the final `selected_action` is both written to Decision and returned.
- Non-blocking risks: request-time fallback initialization if scorer is absent; stale response text says "5 actions" while the active scorer action space is 4; one stale factor-order comment conflicts with active factor order.
- Recommended next step: no blocking fixer for Diagnostic B; optionally clean stale comments/response text and review the request-time scorer fallback.

## Path Resolution
- Repo path: `C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50`
- `backend/app/routers/triage.py` found: YES
- `backend/app` found: YES
- `docs` found: YES
- `docs/implementation_plans` found: YES
- Prior Diagnostic A found: YES
- Scorer state files found: `backend/app/services/gae_state.py`, `backend/app/main.py`
- Category mapping files found: `backend/app/domains/soc/config.py`
- Factor vector files found: `backend/app/domains/soc/orchestrator.py`, `backend/app/domains/soc/config.py`
- Decision write files found: `backend/app/routers/triage.py`

## Files and Functions Read
- `backend/app/routers/triage.py`: read `analyze_alert`, scorer lookup, category resolution, factor-vector computation, scorer call, Decision write, action/referral logic, and response construction.
- `backend/app/models/schemas.py`: read `ProcessAlertRequest`.
- `backend/app/services/gae_state.py`: read scorer singleton storage, `init_learning_state()`, `get_profile_scorer()`, and scorer attachment.
- `backend/app/main.py`: read startup initialization of learning state and router mounting context.
- `backend/app/domains/soc/config.py`: read category/action constants, `get_category_index()`, factor definitions, factor-computer order, centroid/scorer configuration, and `build_profile_scorer()`.
- `backend/app/domains/soc/orchestrator.py`: read `compute_factor_vector()`.
- `docs/implementation_plans/soc_c9b_seed_analyze_contract_diagnostic.md`: read prior Diagnostic A for context only.

## Q1 - Scorer Instance Source
The analyze route gets the scorer from the `gae_state` singleton accessor, not directly from `app.state` and not by constructing `ProfileScorer` on every normal request.

Evidence:
- `backend/app/routers/triage.py:158`: `from app.services.gae_state import get_profile_scorer as _get_scorer, init_learning_state as _init_ls`
- `backend/app/routers/triage.py:159`: `_scorer = _get_scorer()`
- `backend/app/services/gae_state.py:180`: `def init_learning_state() -> LearningState:`
- `backend/app/services/gae_state.py:184`: docstring says it is called once in `main.py startup_event()`.
- `backend/app/services/gae_state.py:191`: `_profile_scorer = _soc_cfg.build_profile_scorer()`
- `backend/app/services/gae_state.py:260`: `_learning_state.attach_profile_scorer(_profile_scorer)`
- `backend/app/services/gae_state.py:402`: `def get_profile_scorer():`
- `backend/app/services/gae_state.py:405`: `return get_learning_state().profile_scorer`
- `backend/app/main.py:268`: imports `init_learning_state`
- `backend/app/main.py:269`: `ls = init_learning_state()`

Classification:
- INFO_ONLY: active path uses a shared `gae_state` singleton initialized at startup.
- NON_BLOCKING_RISK: `backend/app/routers/triage.py:160-164` calls `_init_ls()` inside the request if the scorer is absent. That is a fallback, not normal per-request construction, but it is fragile because it can initialize scorer state from inside request handling.

## Q2 - Scorer Variable Name
The scorer variable in the handler is `_scorer`.

Evidence:
- `backend/app/routers/triage.py:159`: `_scorer = _get_scorer()`
- `backend/app/routers/triage.py:160`: `if _scorer is None:`
- `backend/app/routers/triage.py:163`: `_scorer = _get_scorer()`
- `backend/app/routers/triage.py:236`: `_scoring_result = _scorer.score(f.flatten(), category_index=_cat_idx)`

## Q3 - Category String to category_index
The route resolves the category string from alert type, rejects `unclassified`, then converts the category string to an integer with `SOCDomainConfig.get_category_index()`.

Evidence:
- `backend/app/routers/triage.py:194`: `alert_type = context.get("alert_type") or "unknown"`
- `backend/app/routers/triage.py:197`: `alert_category = resolve_alert_category(alert_type)`
- `backend/app/routers/triage.py:198-211`: `unclassified` category raises HTTP 422.
- `backend/app/routers/triage.py:233`: `_cfg = SOCDomainConfig()`
- `backend/app/routers/triage.py:235`: `_cat_idx = _cfg.get_category_index(alert_category)`
- `backend/app/routers/triage.py:236`: `_scoring_result = _scorer.score(f.flatten(), category_index=_cat_idx)`
- `backend/app/domains/soc/config.py:90-98`: `SOC_CATEGORIES` contains `credential_access`, `malware_execution`, `lateral_movement`, `data_exfiltration`, `insider_threat`, `cloud_infrastructure`.
- `backend/app/domains/soc/config.py:679`: `def get_category_index(self, category: str) -> int:`
- `backend/app/domains/soc/config.py:682`: `return SOC_CATEGORIES.index(category)`
- `backend/app/domains/soc/config.py:683-687`: unknown category raises `ValueError`.

Verdict:
- No CATEGORY_INDEX_MISMATCH found in the active analyze path.

## Q4 - Factor Vector Computation
The factor vector is computed by `compute_factor_vector(alert_data, computers, neo4j_client)`.

Evidence:
- `backend/app/routers/triage.py:220`: `computers = SOCDomainConfig.get_factor_computers()`
- `backend/app/routers/triage.py:221`: `f = await compute_factor_vector(alert_data, computers, neo4j_client)`
- `backend/app/routers/triage.py:222`: `f_2d = f.reshape(1, -1)`
- `backend/app/domains/soc/orchestrator.py:13`: `async def compute_factor_vector(alert: Dict[str, Any], computers: List[Any], neo4j) -> np.ndarray:`
- `backend/app/domains/soc/orchestrator.py:19-29`: docstring states it returns `np.ndarray, shape (d_f,)`.
- `backend/app/domains/soc/orchestrator.py:33-36`: iterates factor computers and appends float values and names.
- `backend/app/domains/soc/orchestrator.py:47`: `return assemble_factor_vector(raw_dict, schema)`
- `backend/app/domains/soc/config.py:120-127`: `SOC_FACTORS` has six factors: `privileged_identity_context`, `asset_criticality`, `threat_intel_enrichment`, `pattern_history`, `time_anomaly`, `device_trust`.
- `backend/app/domains/soc/config.py:129`: `N_FACTORS = len(SOC_FACTORS)`
- `backend/app/domains/soc/config.py:738-746`: `get_factor_computers()` returns the six factor computers in the active execution order.

Actual shape/type:
- Type: NumPy array.
- Expected dimension: six SOC factors.
- Active order: privileged identity context, asset criticality, threat intel enrichment, pattern history, time anomaly, device trust.

Non-blocking risk:
- `backend/app/domains/soc/config.py:371-377` contains a comment whose listed factor order places `pattern_history` after `device_trust`, while the active `SOC_FACTORS` and `get_factor_computers()` order place `pattern_history` before `time_anomaly` and `device_trust`. The active code path is internally consistent; the comment is stale.

## Q5 - Scorer Method Call
The route calls `ProfileScorer.score()` through `_scorer.score(...)` with the flattened factor vector and category index.

Evidence:
- `backend/app/routers/triage.py:235`: `_cat_idx = _cfg.get_category_index(alert_category)`
- `backend/app/routers/triage.py:236`: `_scoring_result = _scorer.score(f.flatten(), category_index=_cat_idx)`
- `backend/app/routers/triage.py:245`: `selected_action = _scoring_result.action_name`
- `backend/app/routers/triage.py:246`: `confidence = _scoring_result.confidence`

Call arguments:
- `f.flatten()`: factor vector flattened to one-dimensional form.
- `category_index=_cat_idx`: integer category index from `SOCDomainConfig.get_category_index()`.

## Q6 - Decision Write and domain=soc
The handler writes the Decision node directly through `neo4j_client.run_query(...)`. The Decision write includes `domain: 'soc'`.

Evidence:
- `backend/app/routers/triage.py:415`: `decision_id = str(uuid.uuid4())`
- `backend/app/routers/triage.py:417`: `await neo4j_client.run_query(f"""`
- `backend/app/routers/triage.py:419`: `MATCH (a:Alert {alert_id: ...})`
- `backend/app/routers/triage.py:420`: `CREATE (d:Decision {`
- `backend/app/routers/triage.py:421`: `decision_id: {_S(decision_id)},`
- `backend/app/routers/triage.py:422`: `domain: 'soc',`
- `backend/app/routers/triage.py:423`: `action: {_S(selected_action)},`
- `backend/app/routers/triage.py:424`: `confidence: {confidence},`
- `backend/app/routers/triage.py:425`: `factor_vector: {_S(json.dumps(fv_list))},`
- `backend/app/routers/triage.py:426`: `category: {_S(alert_category)},`
- `backend/app/routers/triage.py:434`: `CREATE (d)-[:DECIDED_ON]->(a)`

Verdict:
- No DECISION_DOMAIN_MISSING defect found for the graph Decision write.

## Q7 - decision_id Format
The Decision ID is a random UUID4 string.

Evidence:
- `backend/app/routers/triage.py:415`: `decision_id = str(uuid.uuid4())`

Classification:
- UUID, not counter, not timestamp, not derived from `alert_id`.

## Q8 - Returned Action Logic
The returned action begins as the scorer's selected action, then can be changed by routing and referral logic. The final action is stored in `selected_action`, written to the Decision node, and returned in the response.

Evidence:
- `backend/app/routers/triage.py:245`: `selected_action = _scoring_result.action_name`
- `backend/app/routers/triage.py:246`: `confidence = _scoring_result.confidence`
- `backend/app/routers/triage.py:248-250`: confidence threshold is read from `CompositeDiscriminant.CATEGORY_CONFIDENCE_THRESHOLDS`.
- `backend/app/routers/triage.py:251-252`: if confidence is below threshold, `selected_action = "refer_to_analyst"`.
- `backend/app/routers/triage.py:270-305`: if RL exploration is enabled and selected action is a scorer action, RL can propose and replace the selected action.
- `backend/app/routers/triage.py:379-381`: if referral engine says to refer, `selected_action = "refer_to_analyst"` and `routing_zone = "human_review"`.
- `backend/app/routers/triage.py:423`: Decision `action` uses `{_S(selected_action)}`.
- `backend/app/routers/triage.py:725-731`: response recommendation includes `"action": selected_action`, confidence, routing zone, reasoning, pattern/playbook IDs, and `decision_id`.
- `backend/app/routers/triage.py:761`: response `decision_method` is `referral_override` if referral is active, otherwise the RL/scorer decision method.

Verdict:
- No ACTION_ROUTING_MISMATCH found. Returned action may differ from raw scorer output, but the final routed `selected_action` is consistently written and returned.

Non-blocking risk:
- `backend/app/routers/triage.py:745-749` describes the decision method as `n_factors x 5 actions x n_categories`, while active scorer actions come from `SCORER_ACTIONS` and exclude `refer_to_analyst`, giving four scorer actions. This appears to be stale explanatory response text, not an active scoring bug.

## Chain Verdict
- Verdict labels: OK
- OK severity: INFO_ONLY
- Rationale: The active analyze path gets a shared scorer from `gae_state`, resolves category to `category_index`, computes a six-factor vector, invokes `_scorer.score(...)` with that index, writes a Decision node with `domain: 'soc'`, and returns the same final routed action written to the Decision.
- Blocking fixer needed: NO

Severity classification:
- CHAIN_BLOCKER: None found.
- NON_BLOCKING_RISK: request-time scorer fallback initialization if startup state is missing; stale response text says five scorer actions; stale factor-order comment conflicts with active factor order.
- INFO_ONLY: returned action intentionally comes from the full routing pipeline, not only the raw scorer result.

Future fixer scope:
- No blocking fixer required for Diagnostic B.
- Optional cleanup: update stale "5 actions" response text, correct the stale factor-order comment, and consider replacing request-time `_init_ls()` fallback with a clearer startup-health failure path.

## Diagnostic Limitations
- No code was modified.
- No tests were run.
- No app server was run.
- No seed or smoke scripts were run.
- Analysis is source-level only.
