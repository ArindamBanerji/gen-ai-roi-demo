# SOC Backend Line-by-Line Review — Part 1

## app/routers/triage.py (1887 lines)

### Architecture
- This module is the Tab 3 alert triage router plus adjacent feedback, policy, profile, reward, and graph-visualization helpers. It owns alert queue reads, alert analysis, legacy action execution, demo reset, outcome verification, policy checks, ProfileScorer display state, reward summary, decision-factor explainability, and graph-data shaping (`app/routers/triage.py:54-1887`).
- Product flows depending on it include Tab 3 alert queue/analyze/execute/outcome, Tab 2 centroid/profile heatmap through `/soc/profile`, Loop 3/RL governance through `/rl/reward-summary`, policy conflict UI through `/alert/policy-*`, and graph visualization inside analyze responses (`app/routers/triage.py:54`, `app/routers/triage.py:110`, `app/routers/triage.py:864`, `app/routers/triage.py:1541`, `app/routers/triage.py:1660`).
- Module comments claim "Graph-based reasoning and closed-loop execution" and "Tab 3" (`app/routers/triage.py:1-3`). The code actually mixes Tab 3 triage with profile/IKS, RL reward, policy state, ServiceNow mock creation, Sentinel write-back, campaign correlation, audit-chain writes, and evolution-edge creation.

### Function-by-Function Review

- **_node_id** (line 23-25)
  - Purpose: Normalizes node IDs from AGE/Neo4j-style dicts.
  - Inputs: `entity: dict`, optional `prefix`.
  - Logic: Returns `entity["id"]`, `{prefix}_id`, `{prefix}id`, or `"unknown"`.
  - Output: String-like ID value.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None; `entity=None` would raise, but callers check before passing in most cases (`app/routers/triage.py:1774`, `app/routers/triage.py:1788`).
  - AGE/Cypher calls if any: None.
  - Invariants/guards: Fallback ID guard to `"unknown"`.

- **get_alert_queue** (line 55-103)
  - Purpose: Implements `GET /alerts/queue` with `AlertQueueResponse`.
  - Inputs: No explicit request model; mounted under `/api` by `app/main.py`.
  - Logic: Runs a graph query for pending Alert nodes joined to User and Asset, orders by `timestamp_epoch`, limits to 50, and maps rows into alert summaries (`app/routers/triage.py:64-94`).
  - Output: `{"alerts": [...]}` matching `AlertQueueResponse` fields from `app/models/responses.py:158-170`.
  - Side effects: Prints diagnostic logs only.
  - GAE calls: None.
  - Error handling: Catches all exceptions, prints traceback, returns HTTP 500 (`app/routers/triage.py:96-103`).
  - AGE/Cypher calls if any: `neo4j_client.run_query(query)` with `MATCH`, relationship traversal, `ORDER BY`, `LIMIT` (`app/routers/triage.py:64-74`).
  - Invariants/guards: Requires Alert status exactly `'pending'`; defaults missing fields to `"unknown"`, `"medium"`, `"Unknown"`, or `0`.

- **analyze_alert** (line 111-638)
  - Purpose: Implements `POST /alert/analyze`, computes SOC factors, scores via ProfileScorer, writes a Decision node, emits events, evaluates referral/composite/provenance, and returns a rich analysis response.
  - Inputs: `ProcessAlertRequest` with `alert_id`, optional `deployment_version`, and `simulate_failure` (`app/models/schemas.py:33-37`); only `alert_id` is used (`app/routers/triage.py:137`).
  - Logic: Ensures a ProfileScorer exists or attempts `init_learning_state()` (`app/routers/triage.py:121-134`); loads alert and context (`app/routers/triage.py:142-153`); analyzes situation (`app/routers/triage.py:158-159`); computes factor vector with `SOCDomainConfig.get_factor_computers()` and `compute_factor_vector()` (`app/routers/triage.py:167-170`); resolves category and calls `_scorer.score(f.flatten(), category_index=...)` (`app/routers/triage.py:181-188`); applies confidence referral threshold and routing-zone rules (`app/routers/triage.py:194-225`); writes a Decision node and `DECIDED_ON` edge (`app/routers/triage.py:247-267`); writes audit-chain hash/index (`app/routers/triage.py:270-287`); appends confidence snapshot (`app/routers/triage.py:289-296`); attempts campaign correlation (`app/routers/triage.py:301-318`); optionally schedules Sentinel write-back (`app/routers/triage.py:329-350`); emits `DecisionMade` and `GraphMutated` (`app/routers/triage.py:355-364`); evaluates composite gate (`app/routers/triage.py:369-391`); builds provenance (`app/routers/triage.py:396-423`); builds graph data and key facts (`app/routers/triage.py:428-451`); computes probabilities/quality flags (`app/routers/triage.py:453-464`); evaluates `gae.referral.ReferralEngine` rules and can override to `refer_to_analyst` (`app/routers/triage.py:474-531`); returns assembled analysis/narrative response (`app/routers/triage.py:545-630`).
  - Output: Unmodeled dict response with `alert`, `attack_technique`, `attack_tactic`, `analysis`, `context`, `recommendation`, `gae_scoring`, `graph_data`, `situation_analysis`, `composite_gate`, `provenance`, `referral`, `referral_debug`, `decision_method`, and `narrative` (`app/routers/triage.py:545-630`).
  - Side effects: Graph Decision creation; audit ledger write; confidence-history mutation; possible campaign ID write; possible Sentinel async task; event bus emissions; possible Decision `auto_approved` write; logging/printing.
  - GAE calls: Imports `score_alert` at module line 42 but does not call it; uses ProfileScorer `_scorer.score()` (`app/routers/triage.py:186`) and `gae.referral.ReferralEngine` (`app/routers/triage.py:474-509`).
  - Error handling: Explicit 503 for missing scorer and 404 for missing alert/context; composite/provenance/campaign failures are non-blocking; broad final catch returns HTTP 500 (`app/routers/triage.py:121-153`, `app/routers/triage.py:317-318`, `app/routers/triage.py:384-391`, `app/routers/triage.py:421-423`, `app/routers/triage.py:632-638`).
  - AGE/Cypher calls if any: Decision create query (`app/routers/triage.py:249-267`); audit hash `SET` (`app/routers/triage.py:283-287`); campaign `SET` (`app/routers/triage.py:313-316`); composite auto-approve query uses `$id` named parameter (`app/routers/triage.py:380-383`); referral counts call graph-client helper methods (`app/routers/triage.py:480-481`); `get_graph_data()` runs a graph query (`app/routers/triage.py:428`, `app/routers/triage.py:1748-1761`).
  - Invariants/guards: Scorer readiness guard; alert/context existence guards; referral threshold guard; routing-zone thresholds; factor-vector JSON serialization; `softmax_sum` calculation; low-confidence and ambiguous flags; fallback narrative/provenance behavior.

- **execute_action** (line 646-807)
  - Purpose: Implements `POST /action/execute`, a legacy closed-loop execution path.
  - Inputs: `ProcessAlertRequest`; uses `alert_id`.
  - Logic: Loads context, calls legacy `agent.decide()`, generates reasoning, derives situation/factor names when possible, simulates target-system receipt, creates a Decision node with an empty factor vector, records an audit entry, emits events, sets Alert status to `resolved`, and returns receipt/verification/evidence/KPI impact (`app/routers/triage.py:657-801`).
  - Output: Unmodeled dict with `receipt`, `verification`, `evidence`, and `kpi_impact`.
  - Side effects: Creates Decision node, writes audit hash, emits `DecisionMade`/`GraphMutated`, and mutates Alert status (`app/routers/triage.py:712-770`).
  - GAE calls: None in the active code path.
  - Error handling: 404 if context missing; situation/factor derivation failures are printed and tolerated; broad final catch returns HTTP 500 (`app/routers/triage.py:663-686`, `app/routers/triage.py:803-807`).
  - AGE/Cypher calls if any: Atomic Decision create and `DECIDED_ON` edge (`app/routers/triage.py:712-728`); Decision audit-hash `SET` (`app/routers/triage.py:745-749`); Alert status `SET` (`app/routers/triage.py:764-766`).
  - Invariants/guards: Context existence guard; fallback `situation_type_str="unknown"` and `factor_names=[]`; uses `_S()` for interpolated values.

- **reset_demo_alerts** (line 815-857)
  - Purpose: Implements `POST /alerts/reset` for demo-cycle reset.
  - Inputs: None.
  - Logic: Sets only `Alert` nodes with `origin = 'zero_day_demo'` back to `pending`, runs `state_manager.reset_except(["learning_state"])`, resets ServiceNow mock, and returns reset metadata (`app/routers/triage.py:823-850`).
  - Output: Dict with `status`, `message`, `reset_count`, and timestamp.
  - Side effects: Mutates demo Alert statuses, resets registered state except learning state, resets ServiceNow mock.
  - GAE calls: None.
  - Error handling: Broad final catch returns HTTP 500 (`app/routers/triage.py:852-857`).
  - AGE/Cypher calls if any: `MATCH (alert:Alert) WHERE alert.origin = 'zero_day_demo' SET alert.status = 'pending' RETURN count(alert) as reset_count` (`app/routers/triage.py:825-833`).
  - Invariants/guards: Explicit origin guard protects `zero_day_synthetic`; deliberate learning-state exclusion.

- **report_decision_outcome** (line 865-1360)
  - Purpose: Implements `POST /alert/outcome`, records correctness feedback, updates Decision graph properties, updates learning state where allowed, writes audit/evolution/snapshot side effects, and returns feedback-loop response.
  - Inputs: `OutcomeRequest` with `alert_id`, `decision_id`, `outcome: Literal["correct", "incorrect"]`, optional `analyst_action`, optional `override_comment` (`app/models/schemas.py:40-49`).
  - Logic: Rejects duplicate feedback via in-memory status (`app/routers/triage.py:881-888`); maps outcome to `+1/-1` and bool (`app/routers/triage.py:897-899`); attempts to derive analyst identity from `request.state.user` (`app/routers/triage.py:904-909`); updates Decision outcome fields and returns factor/action/category data (`app/routers/triage.py:911-927`); writes outcome audit chain hash/index (`app/routers/triage.py:929-946`); optionally computes per-analyst eta (`app/routers/triage.py:948-966`); parses `factor_vector` (`app/routers/triage.py:968-990`); increments learning count or calls `LearningState.update()` (`app/routers/triage.py:992-1025`); evaluates learning health/conservation (`app/routers/triage.py:1027-1043`); optionally calls ProfileScorer guarded update under lock when `LEARNING_ENABLED` and scorer action are valid (`app/routers/triage.py:1044-1101`); writes centroid delta metadata (`app/routers/triage.py:1108-1120`); updates GraphSnapshot and IKS (`app/routers/triage.py:1137-1182`); queues distance logging (`app/routers/triage.py:1191-1220`); creates `EvolutionEvent` and `TRIGGERED_EVOLUTION` edge on correct scorer actions (`app/routers/triage.py:1228-1272`); writes centroid snapshot (`app/routers/triage.py:1279-1295`); emits outcome events (`app/routers/triage.py:1303-1315`); calls `process_outcome()` and optionally creates ServiceNow mock incident (`app/routers/triage.py:1317-1349`).
  - Output: `process_outcome(...).model_dump()` plus `centroid_update`, not declared as a FastAPI response model (`app/routers/triage.py:1347-1349`).
  - Side effects: Decision outcome mutation, audit-chain mutation, learning-state mutation and persistence, ProfileScorer centroid mutation when enabled, graph snapshot mutation, async distance-log task, EvolutionEvent/edge graph write, event-bus emissions, feedback/trust state mutation, optional ServiceNow mock incident.
  - GAE calls: `LearningState.update()` (`app/routers/triage.py:1017-1025`); `gae.calibration.compute_eta_override()` (`app/routers/triage.py:959-962`); ProfileScorer guarded update via `app.services.gae_state.guarded_update()` (`app/routers/triage.py:1067-1090`).
  - Error handling: Duplicate feedback returns 400; audit, eta, snapshot, distance-log, evolution, centroid-snapshot, and ServiceNow failures are non-blocking; broad final catch returns HTTP 500 (`app/routers/triage.py:881-888`, `app/routers/triage.py:945-966`, `app/routers/triage.py:1178-1182`, `app/routers/triage.py:1219-1220`, `app/routers/triage.py:1268-1272`, `app/routers/triage.py:1291-1295`, `app/routers/triage.py:1344-1345`, `app/routers/triage.py:1351-1360`).
  - AGE/Cypher calls if any: Decision outcome `SET` and return query (`app/routers/triage.py:912-927`); outcome audit hash `SET` (`app/routers/triage.py:940-944`); analyst quality query (`app/routers/triage.py:951-955`); centroid delta `SET` (`app/routers/triage.py:1112-1120`); EvolutionEvent/`TRIGGERED_EVOLUTION` create query (`app/routers/triage.py:1234-1258`).
  - Invariants/guards: Pydantic literal restricts outcome to correct/incorrect; duplicate-feedback guard; `SCORER_ACTIONS` guard skips routing actions; conservation fail-closed flag; scorer lock around guarded ProfileScorer update; non-blocking side-effect guards.

- **get_outcome_status** (line 1368-1391)
  - Purpose: Implements `GET /alert/outcome/status`.
  - Inputs: Query parameter `alert_id: str`.
  - Logic: Calls `get_feedback_status(alert_id)` and returns the status dict (`app/routers/triage.py:1381-1384`).
  - Output: Unmodeled feedback-status dict.
  - Side effects: Prints logs only.
  - GAE calls: None.
  - Error handling: Broad final catch returns HTTP 500 (`app/routers/triage.py:1386-1391`).
  - AGE/Cypher calls if any: None.
  - Invariants/guards: No explicit validation beyond FastAPI string parsing.

- **_build_policy_context** (line 1413-1461)
  - Purpose: Builds policy-rule input context from graph Alert/User/Asset/AttackPattern/TravelContext data.
  - Inputs: `alert_id: str`.
  - Logic: Runs optional graph matches, returns fallback legacy demo contexts if no rows, otherwise maps row fields into policy context (`app/routers/triage.py:1415-1461`).
  - Output: Dict with user risk, alert type, asset criticality, travel/VPN status, and campaign signature.
  - Side effects: None except graph read.
  - GAE calls: None.
  - Error handling: None inside helper; callers catch.
  - AGE/Cypher calls if any: Graph read query using `_S(alert_id)` (`app/routers/triage.py:1415-1434`).
  - Invariants/guards: Fallbacks to risk `0.5`, alert type `"unknown"`, and asset criticality `"medium"` (`app/routers/triage.py:1436-1453`).

- **check_policy_conflicts** (line 1465-1503)
  - Purpose: Implements `GET /alert/policy-check`.
  - Inputs: Query parameter `alert_id: str`.
  - Logic: Builds policy context, calls `detect_policy_conflicts()`, logs conflict details, and returns model dump (`app/routers/triage.py:1477-1494`).
  - Output: PolicyConflict model dumped to dict.
  - Side effects: Policy service may record conflict history depending on its implementation; this router logs/prints.
  - GAE calls: None.
  - Error handling: Broad final catch prints traceback and returns HTTP 500 (`app/routers/triage.py:1496-1503`).
  - AGE/Cypher calls if any: Indirect via `_build_policy_context()`.
  - Invariants/guards: None beyond fallback context construction.

- **get_policy_history** (line 1511-1534)
  - Purpose: Implements `GET /alert/policy-history`.
  - Inputs: None.
  - Logic: Reads conflict history and serializes each resolution (`app/routers/triage.py:1520-1527`).
  - Output: Dict with `conflicts` and `total_count`.
  - Side effects: None beyond logging.
  - GAE calls: None.
  - Error handling: Broad final catch returns HTTP 500 (`app/routers/triage.py:1529-1534`).
  - AGE/Cypher calls if any: None.
  - Invariants/guards: None.

- **get_profile_state** (line 1542-1653)
  - Purpose: Implements `GET /soc/profile` with `ProfileResponse`.
  - Inputs: None.
  - Logic: Reads current ProfileScorer; if absent, returns zero arrays with SOC categories/actions (`app/routers/triage.py:1548-1580`); otherwise uses `scorer.counts.shape` as source of truth, computes decision count, computes IKS and delta, builds switching-cost metadata from fixed `V=200`, `alpha=0.25`, and returns centroids/counts/IKS (`app/routers/triage.py:1582-1653`).
  - Output: `ProfileResponse` with categories, actions, centroids, counts, decision count, and IKS (`app/models/responses.py:69-75`).
  - Side effects: None; reads in-memory ProfileScorer and IKS services.
  - GAE calls: Uses ProfileScorer state through `get_profile_scorer()`; no direct `gae.*` call in this function.
  - Error handling: There is a bare `except Exception: pass` around unused learning-state/profile introspection (`app/routers/triage.py:1602-1611`); no outer catch.
  - AGE/Cypher calls if any: Indirect async `_compute_delta_7d()` may query graph; not visible in this file (`app/routers/triage.py:1594`).
  - Invariants/guards: Scorer absent fallback; shape derived from `scorer.counts.shape`; fixed decision-rate defaults; response model validates shape types.

- **rl_reward_summary** (line 1661-1681)
  - Purpose: Implements `GET /rl/reward-summary`.
  - Inputs: None.
  - Logic: Calls `get_reward_summary()` and returns its dict (`app/routers/triage.py:1671-1674`).
  - Output: Unmodeled reward summary dict.
  - Side effects: Prints logs only.
  - GAE calls: None directly.
  - Error handling: Broad final catch returns HTTP 500 (`app/routers/triage.py:1676-1681`).
  - AGE/Cypher calls if any: None.
  - Invariants/guards: None.

- **decision_factors** (line 1689-1735)
  - Purpose: Implements `GET /triage/decision-factors/{alert_id}` with `DecisionFactorsResponse`.
  - Inputs: Path parameter `alert_id: str`.
  - Logic: Calls service `get_decision_factors(alert_id)`, returns 404 if `None`, otherwise returns service result (`app/routers/triage.py:1713-1726`).
  - Output: `DecisionFactorsResponse` (`app/models/responses.py:237-245`).
  - Side effects: Prints logs only.
  - GAE calls: None in this router; service may use graph/GAE state.
  - Error handling: Preserves HTTPException; broad final catch returns 500 (`app/routers/triage.py:1716-1735`).
  - AGE/Cypher calls if any: Indirect through service.
  - Invariants/guards: `None` result becomes 404.

- **get_graph_data** (line 1742-1887)
  - Purpose: Helper used by `analyze_alert()` to shape graph nodes/relationships for frontend visualization.
  - Inputs: `alert_id: str`.
  - Logic: Queries Alert, Asset, User, optional AttackPattern, TravelContext, matched pattern, and Playbook (`app/routers/triage.py:1748-1758`); converts returned entities into node dicts and relationship dicts (`app/routers/triage.py:1760-1883`).
  - Output: Dict with `nodes` and `relationships`.
  - Side effects: None except graph read and error print.
  - GAE calls: None.
  - Error handling: Empty result or any exception returns empty graph instead of failing analyze (`app/routers/triage.py:1763-1764`, `app/routers/triage.py:1885-1887`).
  - AGE/Cypher calls if any: Relationship-traversal graph read using `_S(alert_id)` (`app/routers/triage.py:1748-1761`).
  - Invariants/guards: Per-node existence checks; missing graph data degrades to empty visualization.

### Invariants Enforced
- Scorer readiness: `analyze_alert()` returns 503 if `get_profile_scorer()` remains `None` after `init_learning_state()` (`app/routers/triage.py:121-134`).
- Alert/context existence: `analyze_alert()` returns 404 for missing alert or missing security context (`app/routers/triage.py:142-153`); `execute_action()` returns 404 for missing context (`app/routers/triage.py:660-664`).
- Pydantic request validation: `ProcessAlertRequest.alert_id` is required (`app/models/schemas.py:33-37`); `OutcomeRequest.outcome` is restricted to `"correct"` or `"incorrect"` (`app/models/schemas.py:40-49`).
- Response validation: `get_alert_queue()`, `get_profile_state()`, and `decision_factors()` declare response models (`app/routers/triage.py:54`, `app/routers/triage.py:1541`, `app/routers/triage.py:1688`).
- Referral threshold guard: confidence below category threshold overrides scorer action to `refer_to_analyst` (`app/routers/triage.py:198-206`).
- Routing-zone guards: refer always human review; monitor and elevated categories route to agent zone; action/category thresholds can route to auto approve (`app/routers/triage.py:208-225`).
- Composite-gate guard: auto-approve write only when `_composite["auto_approve"]` and shadow mode is disabled (`app/routers/triage.py:379-383`).
- Duplicate outcome guard: feedback is rejected if `get_feedback_status(alert_id)["has_feedback"]` is already true (`app/routers/triage.py:881-888`).
- Scorer-action guard: routing action `refer_to_analyst` skips LearningState update and ProfileScorer update because it is not in `SCORER_ACTIONS` (`app/routers/triage.py:1002-1014`).
- Learning enable guard: ProfileScorer guarded update only runs when `LEARNING_ENABLED` and `action_name in SCORER_ACTIONS` (`app/routers/triage.py:1048-1101`).
- Conservation guard: learning-health failure sets `_conservation_block=True` and blocks ProfileScorer guarded update fail-closed (`app/routers/triage.py:1033-1043`, `app/routers/triage.py:1066-1094`).
- Lock guard: ProfileScorer status and guarded update are performed under `async with get_scorer_lock()` (`app/routers/triage.py:1072-1092`).
- Demo reset guard: reset mutates only `Alert` nodes with `origin = 'zero_day_demo'` (`app/routers/triage.py:823-830`).
- Graph mutation event rule visible in code: Decision writes emit `DecisionMade` and `GraphMutated`; outcome writes emit `OutcomeVerified` and `GraphMutated`; evolution write emits `GraphMutated` (`app/routers/triage.py:352-364`, `app/routers/triage.py:751-770`, `app/routers/triage.py:1259-1262`, `app/routers/triage.py:1303-1315`).
- Fallback/clip-style bounds: profile fallback returns zero arrays when scorer is absent (`app/routers/triage.py:1552-1580`); `get_graph_data()` returns empty graph on no result or exception (`app/routers/triage.py:1763-1764`, `app/routers/triage.py:1885-1887`).
- No Python `assert` statements were found in this file.

### Potential Issues

#### P1
- `report_decision_outcome()` can return success for a nonexistent `decision_id`. The graph `MATCH`/`SET` returns no rows when the Decision is absent (`app/routers/triage.py:912-927`), but the code only prints that the node was not found (`app/routers/triage.py:1297-1301`) and still emits outcome events plus calls `process_outcome()` (`app/routers/triage.py:1303-1325`). This can record in-memory feedback/trust for a decision that was never mutated in the graph.
- The composite auto-approve write uses a named `$id` parameter (`app/routers/triage.py:380-383`), directly violating the repo's AGE rule that named `$param` parameters are unsupported. Because it is inside a broad non-blocking `try`, auto-approved decisions may silently lack `d.auto_approved = true` on AGE (`app/routers/triage.py:384-391`).

#### P2
- Analyst identity is effectively never captured from authenticated requests in `report_decision_outcome()`: `OutcomeRequest` is a Pydantic body model with no `state` attribute (`app/models/schemas.py:40-49`), so `request.state.user` raises `AttributeError` and `analyst_id` falls back to `"anonymous"` (`app/routers/triage.py:904-909`). That makes the per-analyst eta query path unreachable for normal FastAPI requests (`app/routers/triage.py:948-966`).
- If a Decision has `factor_vector` missing or unparsable, the code increments in-memory `decision_count` but does not call `save_learning_state()` in that branch (`app/routers/triage.py:992-997`). Verified-decision count can diverge from persisted learning state after restart.
- Several fire-and-forget tasks have no completion callback or exception observation after scheduling: Sentinel write-back (`app/routers/triage.py:338-346`) and EXP-G1 distance logging (`app/routers/triage.py:1203-1215`). Exceptions after task creation are not handled by the surrounding `try`.
- `execute_action()` is a legacy path using `agent.decide()` and empty `factor_vector` (`app/routers/triage.py:667-669`, `app/routers/triage.py:712-728`) while `analyze_alert()` uses ProfileScorer and full factor vectors (`app/routers/triage.py:167-188`, `app/routers/triage.py:249-267`). If both paths remain user-facing, they create materially different Decision records.
- `get_graph_data()` shadows the `alert_id` parameter with the normalized alert node ID (`app/routers/triage.py:1772-1775`). Current relationship construction works, but this makes later maintenance fragile if the original request ID is needed after line 1774.
- `get_profile_state()` uses hardcoded `V=200` and `alpha=0.25` while comments say deployment config is not wired (`app/routers/triage.py:1597-1613`). This is acceptable as an explicit placeholder, but it is displayed metric logic with a bare `except Exception: pass` nearby (`app/routers/triage.py:1602-1611`).

#### P3
- Module-level imports include apparently unused names: `List` (`app/routers/triage.py:8`), `dataclasses` (`app/routers/triage.py:27`), `score_alert` (`app/routers/triage.py:42`), and `get_learning_state/save_learning_state` are used later but the import placement immediately after `_node_id()` is visually irregular (`app/routers/triage.py:23-28`).
- Comments in `analyze_alert()` still describe deprecated W-matrix/`score_alert` behavior and a `MATCH (a:Alert {id: $alert_id})` pattern (`app/routers/triage.py:162-174`, `app/routers/triage.py:239-245`), while active code uses ProfileScorer, `alert_id`, `_S()`, and `timestamp_epoch` (`app/routers/triage.py:181-188`, `app/routers/triage.py:249-267`).
- `analyze_alert()` is over 500 lines and mixes scoring, persistence, eventing, referral, provenance, campaign, Sentinel, graph visualization, and narrative assembly (`app/routers/triage.py:111-638`). This makes line-by-line verification and future changes high risk.
- Many handlers print directly instead of using `logger` consistently (`app/routers/triage.py:60-103`, `app/routers/triage.py:167-238`, `app/routers/triage.py:821-857`, `app/routers/triage.py:878-879`).
- `get_graph_data()` swallows all exceptions and returns an empty graph (`app/routers/triage.py:1885-1887`), which may hide schema drift during demos.

### AGE Cypher Queries
- `get_alert_queue()` query (lines 64-71): uses `MATCH`, relationship traversal, `RETURN ... as user_name`, `ORDER BY`, `LIMIT`. No `MERGE`, `datetime()`, `$param`, `labels[0]`, `ON CREATE SET`, `ON MATCH SET`, or list parameter `IN`. Alias names are not `count`.
- `analyze_alert()` Decision create query (lines 249-267): uses `_S()` interpolation for string values, `CREATE` Decision and `DECIDED_ON` edge atomically. No `MERGE`, `datetime()`, `$param`, `labels[0]`, `ON CREATE SET`, `ON MATCH SET`, or list parameter `IN`.
- `analyze_alert()` audit hash update (lines 283-287): uses `_S()` for string hash and scalar chain index. No listed anti-pattern.
- `analyze_alert()` campaign update (lines 313-316): uses `_S()` for campaign ID. No listed anti-pattern.
- `analyze_alert()` composite auto-approve update (lines 380-383): `MATCH (d:Decision {decision_id: $id}) SET d.auto_approved = true` uses named `$id`; this violates the AGE no `$param` rule.
- `execute_action()` Decision create query (lines 712-728): uses `_S()` interpolation and atomic Decision/edge create. No listed anti-pattern.
- `execute_action()` audit hash update (lines 745-749): uses `_S()` and scalar chain index. No listed anti-pattern.
- `execute_action()` alert status update (lines 764-766): uses `_S(alert_id)` and property `SET`; no listed anti-pattern.
- `reset_demo_alerts()` query (lines 825-830): uses origin guard and `RETURN count(alert) as reset_count`. It does not alias as reserved `count`; no listed anti-pattern.
- `report_decision_outcome()` outcome update query (lines 912-927): uses `_S()` for strings and property-level `SET`; no listed anti-pattern.
- `report_decision_outcome()` outcome audit update (lines 940-944): uses `_S()` and scalar chain index; no listed anti-pattern.
- `report_decision_outcome()` analyst-quality query (lines 951-955): uses `_S(analyst_id)`; no listed anti-pattern.
- `report_decision_outcome()` centroid delta update (lines 1112-1120): property-level `SET`; no listed anti-pattern.
- `report_decision_outcome()` evolution query (lines 1234-1258): creates EvolutionEvent and `TRIGGERED_EVOLUTION` edge, then property-level `SET`; no listed anti-pattern.
- `_build_policy_context()` query (lines 1415-1434): optional relationship traversal, `_S(alert_id)`, `CASE WHEN`; no listed anti-pattern.
- `get_graph_data()` query (lines 1748-1758): relationship traversal and `_S(alert_id)`; no listed anti-pattern.

### Cross-Module Dependencies
- Assumes `app.db.neo4j.neo4j_client` provides `run_query()`, `get_alert()`, `get_security_context()`, `get_sequence_count()`, and `get_cross_category_count()` (`app/routers/triage.py:30`, `app/routers/triage.py:142-150`, `app/routers/triage.py:480-481`).
- Assumes `app.graph_schema._S()` returns AGE-safe inline literals for string/JSON interpolation (`app/routers/triage.py:31`, `app/routers/triage.py:249-267`).
- Assumes `app.services.gae_state` owns process-wide LearningState/ProfileScorer, persistence, locks, guarded updates, mu-zero, and centroid snapshots (`app/routers/triage.py:26`, `app/routers/triage.py:121-127`, `app/routers/triage.py:994-1025`, `app/routers/triage.py:1067-1090`, `app/routers/triage.py:1279-1290`).
- Assumes SOC domain config provides factor computers, temperature, categories/actions, action thresholds, confidence floors, elevated categories, alert-category resolution, campaign config, and `LEARNING_ENABLED` (`app/routers/triage.py:34-41`, `app/routers/triage.py:168-185`, `app/routers/triage.py:208-225`, `app/routers/triage.py:1048-1051`).
- Assumes `compute_factor_vector()` returns a NumPy-compatible vector with stable SOC factor ordering (`app/routers/triage.py:167-170`, `app/routers/triage.py:227`).
- Assumes `app.services.feedback` provides in-memory duplicate feedback status and `process_outcome()` response model/dump (`app/routers/triage.py:16`, `app/routers/triage.py:881-888`, `app/routers/triage.py:1320-1349`).
- Assumes audit services write an in-memory/framework audit chain and return hash/index keys (`app/routers/triage.py:19`, `app/routers/triage.py:270-287`, `app/routers/triage.py:929-946`).
- Assumes frontend/API consumers accept unmodeled analyze, execute, outcome, policy, reward, and graph-data response shapes; only alert queue, profile, and decision-factors have explicit response models in this router (`app/routers/triage.py:54`, `app/routers/triage.py:110`, `app/routers/triage.py:645`, `app/routers/triage.py:864`, `app/routers/triage.py:1541`, `app/routers/triage.py:1688`).
- Other modules likely assume this router emits event-bus events for graph mutations, preserves `ALERT-` demo queue behavior, writes Decision nodes with `decision_id`, `factor_vector`, `category`, `source_id`, `user_id`, `timestamp_epoch`, `entry_hash`, and chain-index fields, and updates outcome/evolution fields used by analytics and tests (`app/routers/triage.py:249-287`, `app/routers/triage.py:912-927`, `app/routers/triage.py:1234-1258`, `app/routers/triage.py:1303-1315`).
