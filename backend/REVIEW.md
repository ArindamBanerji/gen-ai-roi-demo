# SOC Copilot Backend Line-by-Line Code Review

## Scope
- Eight files reviewed: `app/routers/triage.py`, `app/services/gae_state.py`, `app/services/feedback.py`, `app/domains/soc/config.py`, `app/domains/soc/factors.py`, `app/services/evidence_room.py`, `app/services/learning_health.py`, and `app/graph_schema.py`.
- Backend source was read-only during review generation.
- Generated from `REVIEW.part1.md` through `REVIEW.part4.md`.

## Executive Summary
- P1 findings summary: 16 total. Highest-impact issues are AGE-incompatible `$param` query usage in runtime/monitoring paths, scorer/factor contract mismatches, polarity inversions for threat/device factors, feedback/scorer lifecycle defects, audit evidence fail-open behavior, and destructive/partial seed risks in graph schema tooling.
- P2 findings summary: 40 total. Repeated themes are mutable shared state without locking, fail-soft health/evidence paths that can hide broken dependencies, stale or ambiguous action/factor vocabularies, query/result-shape fragility, and graph/session-state inconsistencies.
- P3 findings summary: 29 total. Most are stale comments, unused imports, hardcoded export/schema values, TODO stubs, and documentation drift around active ownership of scoring, graph, and evidence behavior.
- Highest-risk modules: `app/domains/soc/factors.py` and `app/services/learning_health.py` for AGE query compatibility; `app/domains/soc/config.py` plus `factors.py` for scorer semantics; `app/services/gae_state.py` and `app/services/feedback.py` for mutable learning state; `app/graph_schema.py` for destructive clean/partial seed behavior.
- AGE/Cypher anti-pattern summary: `$param` appears in factor and learning-health queries; triage has an AGE-unsafe composite-gate query; W2 factor logic reads `d.factor_snapshot[3]` even though AGE-compatible storage serializes arrays as JSON strings; `graph_schema.py` mostly follows inline `_S()` usage but intentionally uses `DETACH DELETE` in seed clean.
- Global state/thread-safety summary: learning state, audit memory, graph snapshot, and evidence/health reads are shared mutable runtime state. Multiple modules read or update these structures without explicit locking or transaction-level snapshots, so concurrent request/outcome flows can produce stale or mixed metrics.
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


# SOC Backend Line-by-Line Review — Part 2

## app/services/gae_state.py (847 lines)

### Architecture
- This module owns the process-local GAE `LearningState`/ProfileScorer lifecycle, checkpoint path, bootstrap metadata, centroid PITR backups, DeploymentState persistence, centroid export/restore, analyst eta weights, spike/freeze guards, and the `guarded_update()` wrapper used by triage outcome learning (`app/services/gae_state.py:34-847`).
- Demo and product features depending on it include startup initialization, Tab 2 profile/centroid/IKS display, outcome learning updates, conservation/spike gates, centroid export/time-machine features, bootstrap-state persistence, and demo/admin reset handlers (`app/services/gae_state.py:116-209`, `app/services/gae_state.py:365-397`, `app/services/gae_state.py:452-590`, `app/services/gae_state.py:681-735`).
- It bridges the SOC backend to GAE by constructing `CalibrationProfile`, creating/loading `LearningState`, building a SOC `ProfileScorer` via `SOCDomainConfig`, running `gae.bootstrap_calibration`, attaching the ProfileScorer to the live state, and exposing update guards around `scorer.update()` (`app/services/gae_state.py:23-30`, `app/services/gae_state.py:85-99`, `app/services/gae_state.py:129-200`, `app/services/gae_state.py:734-735`).

### Function-by-Function Review

- **get_scorer_lock** (line 37-38)
  - Purpose: Exposes the module-level `asyncio.Lock`.
  - Inputs: None.
  - Logic: Returns `_scorer_lock`.
  - Output: `asyncio.Lock`.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Callers must use it; this function does not enforce locking itself.

- **_S** (line 41-51)
  - Purpose: Serializes Python values to inline AGE-safe Cypher literals.
  - Inputs: Any value.
  - Logic: Converts `None`, bools, numbers, lists/tuples as JSON strings, and other values as escaped strings.
  - Output: String containing a Cypher literal.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Avoids named `$param` use; escapes backslashes and single quotes for scalar strings.

- **_soc_profile** (line 85-91)
  - Purpose: Builds the SOC GAE calibration profile.
  - Inputs: None.
  - Logic: Returns `CalibrationProfile(learning_rate=0.02, penalty_ratio=20.0, temperature=0.1)`.
  - Output: `gae.learning.CalibrationProfile`.
  - Side effects: None.
  - GAE calls: Instantiates GAE `CalibrationProfile`.
  - Error handling: None.
  - Invariants/guards: Encodes asymmetry 20:1 and tau 0.1.

- **_make_fresh_state** (line 94-99)
  - Purpose: Creates a fresh `LearningState` from SOC expert priors.
  - Inputs: None.
  - Logic: Reads initial `W` and factor names from `SOCDomainConfig`, then calls `_fw.make_state()`.
  - Output: `LearningState`.
  - Side effects: Imports SOC config locally.
  - GAE calls: Indirect through framework state construction with a GAE calibration profile.
  - Error handling: None.
  - Invariants/guards: Assumes initial W shape and factor-computer order match SOC runtime.

- **_load_from_file** (line 102-104)
  - Purpose: Loads a `LearningState` checkpoint.
  - Inputs: None.
  - Logic: Calls `_fw.load_from_file(_STATE_PATH, _soc_profile())`.
  - Output: `LearningState`.
  - Side effects: Reads JSON checkpoint.
  - GAE calls: Indirect framework deserialization.
  - Error handling: None here; caller catches in `init_learning_state()`.
  - Invariants/guards: Uses the module checkpoint path.

- **_read_checkpoint_metadata** (line 107-109)
  - Purpose: Reads checkpoint metadata.
  - Inputs: None.
  - Logic: Delegates to `_fw.read_checkpoint_metadata(_STATE_PATH)`.
  - Output: Dict, usually `{}` if absent.
  - Side effects: Reads JSON checkpoint.
  - GAE calls: None.
  - Error handling: Delegated.
  - Invariants/guards: None in this wrapper.

- **init_learning_state** (line 116-209)
  - Purpose: Initializes `_learning_state`, bootstrap metadata/result, and ProfileScorer.
  - Inputs: None.
  - Logic: Builds a new SOC ProfileScorer, asserts `eta_override` is present, then either loads a bootstrapped checkpoint, loads/falls back from a legacy/corrupt checkpoint and bootstraps, or creates a fresh state and bootstraps (`app/services/gae_state.py:129-198`). It persists pre-bootstrap `mu_zero`, runs `bootstrap_calibration()`, records bootstrap metadata, attaches the ProfileScorer to `_learning_state`, and saves state when bootstrap ran (`app/services/gae_state.py:166-207`).
  - Output: Live `LearningState`.
  - Side effects: Mutates `_learning_state`, `_bootstrap_metadata`, `_bootstrap_result`; writes `iks_bootstrap_soc.json`; may overwrite `gae_learning_state.json`; prints/logs startup messages.
  - GAE calls: `SOCDomainConfig.build_profile_scorer()`, `gae.bootstrap_calibration()`, `LearningState.attach_profile_scorer()`.
  - Error handling: Checkpoint load failure logs warning and uses fresh state; `mu_zero` write failure logs warning and continues; bootstrap failures are not caught.
  - Invariants/guards: Assertion requires ProfileScorer `eta_override`; checkpoint metadata flag `bootstrap=True` prevents re-bootstrap; `needs_bootstrap` controls persistence.

- **get_profile_scorer** (line 212-217)
  - Purpose: Returns the global ProfileScorer if initialized.
  - Inputs: None.
  - Logic: Calls `get_learning_state().profile_scorer`.
  - Output: ProfileScorer or `None`.
  - Side effects: None.
  - GAE calls: Reads ProfileScorer attached to GAE state.
  - Error handling: Converts `RuntimeError` from uninitialized state into `None`.
  - Invariants/guards: Does not validate scorer shape or readiness beyond initialization.

- **get_mu_zero** (line 220-240)
  - Purpose: Loads persisted bootstrap baseline centroids.
  - Inputs: None.
  - Logic: Reads `_MU_ZERO_PATH`, parses JSON key `mu_zero`, converts to `np.float64` array.
  - Output: NumPy array or `None`.
  - Side effects: File read; warning logs.
  - GAE calls: None.
  - Error handling: Missing file or parse errors return `None`.
  - Invariants/guards: Converts dtype to float64; no shape validation.

- **get_bootstrap_result** (line 243-250)
  - Purpose: Exposes the last startup bootstrap result.
  - Inputs: None.
  - Logic: Returns `_bootstrap_result`.
  - Output: `BootstrapResult` or `None`.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Existing checkpoint startup returns `None`.

- **get_learning_state** (line 253-266)
  - Purpose: Returns the live `LearningState`.
  - Inputs: None.
  - Logic: Raises if `_learning_state is None`; otherwise returns it.
  - Output: `LearningState`.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Raises `RuntimeError` before initialization.
  - Invariants/guards: Enforces startup initialization.

- **save_learning_state** (line 269-274)
  - Purpose: Persists current learning state.
  - Inputs: None.
  - Logic: Calls `_fw.save_state(_learning_state, _bootstrap_metadata, _STATE_PATH)`.
  - Output: None.
  - Side effects: Writes checkpoint file.
  - GAE calls: Indirect serialization of GAE state.
  - Error handling: None in wrapper.
  - Invariants/guards: Docstring says no-op if uninitialized, but the code always delegates `_learning_state`, even if `None`.

- **reset_learning_state** (line 277-285)
  - Purpose: Resets learning state for reset handlers.
  - Inputs: None.
  - Logic: Replaces `_learning_state` with `_make_fresh_state()`, saves it, prints reset message.
  - Output: None.
  - Side effects: Mutates singleton and checkpoint.
  - GAE calls: Indirect `LearningState` construction.
  - Error handling: None.
  - Invariants/guards: Does not attach a ProfileScorer after reset.

- **_ensure_backup_dir** (line 295-297)
  - Purpose: Ensures centroid backup directory exists.
  - Inputs: None.
  - Logic: Calls `_BACKUP_DIR.mkdir(parents=True, exist_ok=True)`.
  - Output: Backup `Path`.
  - Side effects: Creates directory.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Uses fixed path under `app/data/centroid_backups`.

- **serialize_centroid_tensor** (line 300-322)
  - Purpose: Serializes scorer centroids with integrity hash.
  - Inputs: `scorer` with `centroids` and optional `decision_count`.
  - Logic: Builds payload with `mu`, `shape`, `step`, `timestamp_epoch`, `version`, hashes canonical JSON excluding `sha256`, and returns payload.
  - Output: Dict with SHA-256.
  - Side effects: None.
  - GAE calls: Reads ProfileScorer centroid tensor.
  - Error handling: None.
  - Invariants/guards: Hash is over payload before `sha256` is added.

- **write_centroid_backup** (line 325-353)
  - Purpose: Writes timestamped and latest centroid backup files.
  - Inputs: `scorer`, optional metadata dict.
  - Logic: Serializes centroids, creates UUID-suffixed backup ID, merges metadata, writes both `{backup_id}.json` and `centroid_backup_latest.json`.
  - Output: Backup payload.
  - Side effects: File writes.
  - GAE calls: Reads ProfileScorer through serializer.
  - Error handling: None.
  - Invariants/guards: UUID suffix avoids same-millisecond collisions.

- **maybe_write_centroid_snapshot** (line 365-397)
  - Purpose: Auto-snapshots centroids every `SNAPSHOT_INTERVAL`.
  - Inputs: `scorer`, optional `decision_id`, category.
  - Logic: Increments `_snapshot_decision_count`; writes backup only when the count is a positive multiple of 10.
  - Output: Boolean written/not written.
  - Side effects: Mutates `_snapshot_decision_count`; may write backup files.
  - GAE calls: Reads ProfileScorer centroids.
  - Error handling: Catches/logs backup failures and returns False.
  - Invariants/guards: Interval gate; no lock around counter.

- **list_centroid_backups** (line 400-419)
  - Purpose: Lists timestamped centroid backups.
  - Inputs: None.
  - Logic: Reads matching JSON files sorted reverse, parses selected metadata fields, ignores unreadable files.
  - Output: List of backup summaries.
  - Side effects: Directory creation through `_ensure_backup_dir()`.
  - GAE calls: None.
  - Error handling: Bare `except Exception: pass` skips bad files.
  - Invariants/guards: Only `centroid_backup_[0-9]*.json` files included.

- **load_centroid_backup** (line 422-434)
  - Purpose: Loads a specific or latest backup payload.
  - Inputs: Optional `backup_id`.
  - Logic: Resolves path and parses JSON.
  - Output: Backup dict.
  - Side effects: Directory creation/read.
  - GAE calls: None.
  - Error handling: Raises `FileNotFoundError`; JSON parse errors propagate.
  - Invariants/guards: Uses latest when backup ID missing.

- **write_bootstrap_state** (line 452-502)
  - Purpose: Persists bootstrap centroid tensor to a graph `DeploymentState` node.
  - Inputs: `neo4j_client`, `scorer`.
  - Logic: Serializes current centroids, shape, timestamp, and GAE version; checks for `DeploymentState {id: 'current'}`; updates if present or creates otherwise; returns payload regardless of graph write success.
  - Output: Dict with bootstrap tensor metadata.
  - Side effects: Graph write and logs.
  - GAE calls: Reads ProfileScorer centroids.
  - Error handling: Catches all graph-write exceptions, logs warning, still returns payload.
  - Invariants/guards: Uses `_S()` for JSON/timestamp/version inline literals.

- **get_bootstrap_centroids** (line 505-530)
  - Purpose: Reads bootstrap centroids from graph DeploymentState.
  - Inputs: `neo4j_client`.
  - Logic: Runs `READ_DEPLOYMENT_STATE`, returns `None` if absent, parses JSON strings for `bootstrap_mu` and `bootstrap_shape`.
  - Output: Dict `{mu, shape, stored_at, gae_version}` or `None`.
  - Side effects: Graph read.
  - GAE calls: None.
  - Error handling: Catches/logs exceptions and returns `None`.
  - Invariants/guards: Handles AGE stringified nested lists.

- **build_centroid_export** (line 543-590)
  - Purpose: Builds portable centroid export artifact.
  - Inputs: `scorer`, `neo4j_client`.
  - Logic: Reads bootstrap centroids, computes mean absolute drift if available, hashes current mu, and returns export metadata.
  - Output: Dict with export version, generated time, GAE version, tensor shape, current/bootstrap mu, drift, decision count, categories, actions, hash.
  - Side effects: Graph read via `get_bootstrap_centroids()`.
  - GAE calls: Reads ProfileScorer centroids and decision count.
  - Error handling: None around drift shape mismatch or hash serialization; exceptions propagate.
  - Invariants/guards: Uses hardcoded export categories/actions and version strings.

- **restore_centroid_from_backup** (line 593-622)
  - Purpose: Restores live ProfileScorer centroids from backup after checksum verification.
  - Inputs: Optional `backup_id`.
  - Logic: Loads backup, recomputes hash excluding `sha256` and `backup_id`, raises on mismatch, gets live scorer, converts `mu` to float64 array, assigns `scorer.centroids`.
  - Output: Backup payload.
  - Side effects: Mutates live ProfileScorer centroids.
  - GAE calls: Reads and mutates ProfileScorer.
  - Error handling: Raises `ValueError` on checksum mismatch, `RuntimeError` if scorer missing; file/JSON errors propagate.
  - Invariants/guards: Checksum guard; scorer readiness guard; no shape compatibility guard.

- **apply_analyst_eta_weights** (line 629-649)
  - Purpose: Stores analyst eta weights globally and on scorer.
  - Inputs: `scorer`, `eta_weights`.
  - Logic: Copies input dict to `_analyst_eta_weights`; attempts dynamic `scorer.eta_weights` attachment.
  - Output: None.
  - Side effects: Mutates module global and possibly scorer object.
  - GAE calls: Mutates ProfileScorer dynamic attribute.
  - Error handling: Dynamic attach failure logged at debug and otherwise ignored.
  - Invariants/guards: Comments state weights should be `[0.5, 1.5]`, but no bounds are enforced.

- **get_analyst_eta_weights** (line 652-654)
  - Purpose: Returns current eta weights.
  - Inputs: None.
  - Logic: Returns a shallow copy.
  - Output: Dict.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Copy prevents direct caller mutation of global dict.

- **set_volume_spike** (line 661-673)
  - Purpose: Sets global volume spike flag.
  - Inputs: `active`.
  - Logic: Casts to bool, stores `_volume_spike_active`, logs set/clear.
  - Output: None.
  - Side effects: Mutates global flag.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Does not clear frozen categories despite docstring saying they clear automatically elsewhere.

- **is_volume_spike_active** (line 676-678)
  - Purpose: Reads spike flag.
  - Inputs: None.
  - Logic: Returns `_volume_spike_active`.
  - Output: Bool.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: None.

- **guarded_update** (line 681-735)
  - Purpose: Enforces spike, category-freeze, conservation pause, and spike-cap gates before ProfileScorer updates.
  - Inputs: `scorer`, factor vector `f`, `category_index`, `action_index`, `correct`, optional `category_name`, forwarded kwargs.
  - Logic: Returns `None` if volume spike active, category frozen, scorer paused, or spike cap exhausted; otherwise calls `scorer.update(f=f, category_index=..., action_index=..., correct=..., **kwargs)`.
  - Output: CentroidUpdate-like object or `None`.
  - Side effects: May increment spike counter; may mutate ProfileScorer through update.
  - GAE calls: Direct `ProfileScorer.update()`.
  - Error handling: None around scorer update.
  - Invariants/guards: D3 spike freeze, D2 category freeze, conservation pause, D7 cap; no input bounds on indexes or vector shape.

- **set_frozen_categories** (line 742-759)
  - Purpose: Replaces frozen category set.
  - Inputs: List of category names.
  - Logic: Converts to set and logs set/clear.
  - Output: None.
  - Side effects: Mutates `_frozen_categories`.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Comment says should only be called during spike, but code does not enforce spike coupling.

- **get_frozen_categories** (line 762-764)
  - Purpose: Reads frozen categories.
  - Inputs: None.
  - Logic: Returns copy of set.
  - Output: Set.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Copy prevents direct mutation.

- **is_category_frozen** (line 767-769)
  - Purpose: Checks one category.
  - Inputs: Category string.
  - Logic: Membership test in `_frozen_categories`.
  - Output: Bool.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: None.

- **set_spike_cap** (line 776-789)
  - Purpose: Sets D7 cap to `int(1.5 * baseline_daily)`.
  - Inputs: `baseline_daily`.
  - Logic: Computes int cap and logs.
  - Output: None.
  - Side effects: Mutates `_spike_update_cap`.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: No lower bound; negative baseline creates negative cap.

- **reset_spike_counter** (line 792-800)
  - Purpose: Resets cadence counter.
  - Inputs: None.
  - Logic: Sets `_spike_update_count=0`.
  - Output: None.
  - Side effects: Mutates global counter.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: None.

- **increment_spike_counter** (line 803-822)
  - Purpose: Applies D7 counter/cap.
  - Inputs: None.
  - Logic: Returns True outside spike or without cap; returns False if cap exhausted; otherwise increments counter and returns True.
  - Output: Bool allow/deny.
  - Side effects: Mutates `_spike_update_count` only when active and cap configured.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Cap check before increment.

- **get_spike_cap_status** (line 825-847)
  - Purpose: Returns spike/cap state for endpoint/monitoring.
  - Inputs: None.
  - Logic: Computes `cap_reached` and returns state dict.
  - Output: Dict.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: `cap_reached` requires active spike and positive cap.

### Invariants Enforced
- `get_learning_state()` raises before initialization (`app/services/gae_state.py:253-266`).
- `init_learning_state()` asserts ProfileScorer has `eta_override` (`app/services/gae_state.py:129-136`).
- Bootstrapped checkpoint metadata skips re-bootstrap; legacy/missing checkpoint runs bootstrap (`app/services/gae_state.py:140-166`).
- `mu_zero` and checkpoint files are persisted on bootstrap, and ProfileScorer is attached before returning (`app/services/gae_state.py:166-209`).
- `_S()` avoids `$param` by producing inline AGE literals (`app/services/gae_state.py:41-51`).
- Centroid backups carry SHA-256 hashes, and restore verifies the hash before mutation (`app/services/gae_state.py:300-322`, `app/services/gae_state.py:603-621`).
- Auto-snapshot writes only on multiples of `SNAPSHOT_INTERVAL=10` (`app/services/gae_state.py:360-397`).
- DeploymentState parsing handles AGE JSON strings for nested lists (`app/services/gae_state.py:515-521`).
- `guarded_update()` blocks on volume spike, frozen category, conservation pause, and spike cap before calling `scorer.update()` (`app/services/gae_state.py:681-735`).
- Getter functions return copies for eta weights and frozen categories (`app/services/gae_state.py:652-654`, `app/services/gae_state.py:762-764`).

### Potential Issues

#### P1
- `reset_learning_state()` replaces `_learning_state` with `_make_fresh_state()` and saves it, but does not attach a ProfileScorer (`app/services/gae_state.py:277-285`). Any later `get_profile_scorer()` call can return missing/invalid scorer state even though `_learning_state` is initialized, which can break analyze/profile flows after a hard reset.
- `restore_centroid_from_backup()` verifies checksum but does not validate restored tensor shape against the live scorer before assigning `scorer.centroids = mu_array` (`app/services/gae_state.py:603-621`). A valid backup with incompatible dimensions can corrupt live scorer state.

#### P2
- Module-level state is broadly mutable and mostly unlocked: `_learning_state`, `_bootstrap_metadata`, `_analyst_eta_weights`, spike flags/counters, frozen categories, and snapshot counter can be read/written concurrently (`app/services/gae_state.py:55-78`, `app/services/gae_state.py:360-397`, `app/services/gae_state.py:629-847`). Only callers that explicitly use `get_scorer_lock()` are protected.
- `_scorer_lock = asyncio.Lock()` is created at import time (`app/services/gae_state.py:34`). If tests or server lifecycle create/reuse event loops differently, an import-time lock can be awkward; current code assumes one process/event-loop lifecycle.
- `save_learning_state()` docstring says no-op when uninitialized, but code delegates `_learning_state` unconditionally (`app/services/gae_state.py:269-274`). Actual behavior depends on `_fw.save_state()` and may not match the comment.
- `set_volume_spike(False)` does not clear `_frozen_categories`, despite `set_frozen_categories()` docstring saying frozen categories clear automatically when spike clears (`app/services/gae_state.py:661-673`, `app/services/gae_state.py:742-749`). Stale frozen categories can block later updates if `guarded_update()` reaches the category check.
- `write_bootstrap_state()` catches graph-write failures and still returns a payload that looks successfully stored (`app/services/gae_state.py:472-502`). Callers cannot distinguish persisted vs only computed state.
- `build_centroid_export()` assumes bootstrap/current centroid shapes match; shape mismatch raises during drift computation (`app/services/gae_state.py:565-571`).

#### P3
- Top docstring says "single source of truth for the W matrix" (`app/services/gae_state.py:1-6`), but active code is mostly ProfileScorer/centroid based and W-matrix comments are stale relative to current behavior.
- `_GAE_VERSION` is `"0.7.20"` for DeploymentState while export `_EXPORT_GAE_VERSION` is `"0.7.21"` (`app/services/gae_state.py:441`, `app/services/gae_state.py:540`), which may confuse artifact comparisons.
- Several comments state policy constraints without enforcement, including eta weight bounds and category-freeze coupling (`app/services/gae_state.py:60-62`, `app/services/gae_state.py:637-640`, `app/services/gae_state.py:742-748`).
- `list_centroid_backups()` silently skips bad files with bare `except` (`app/services/gae_state.py:408-419`), hiding backup corruption.

### Cross-Module Dependencies
- Depends on `gae.learning.LearningState`, `CalibrationProfile`, `gae.bootstrap_calibration`, and `BootstrapResult` for learning and bootstrap lifecycle (`app/services/gae_state.py:23-24`).
- Depends on `app.domains.soc.config` for SOC bootstrap constants, categories, scorer actions, initial W, factor computers, and ProfileScorer construction (`app/services/gae_state.py:25-30`, `app/services/gae_state.py:94-99`, `app/services/gae_state.py:129-131`).
- Depends on `app.framework.learning_state` for state serialization/deserialization/checkpoint metadata (`app/services/gae_state.py:30`, `app/services/gae_state.py:94-109`, `app/services/gae_state.py:269-274`).
- Triage outcome code assumes `guarded_update()` enforces conservation/spike/freeze and calls ProfileScorer update, and uses `get_scorer_lock()` externally for thread safety (`app/services/gae_state.py:37-38`, `app/services/gae_state.py:681-735`).
- Centroid export/backup routes and time-machine features assume backup files are JSON at `_BACKUP_DIR` and DeploymentState has `bootstrap_mu`, `bootstrap_shape`, `bootstrap_stored_at`, and `gae_version` (`app/services/gae_state.py:292-353`, `app/services/gae_state.py:443-530`).

## app/services/feedback.py (451 lines)

### Architecture
- This module implements the in-memory feedback/trust simulation used after outcome submission. It defines response models, mutable simulated pattern/edge/precedent state, maps SOC categories to edge keys, records whether feedback was already given, mutates trust, seeds trust history, and resets demo state (`app/services/feedback.py:12-451`).
- Demo flows depending on it include `POST /api/alert/outcome`, `GET /api/alert/outcome/status`, `GET /api/rl/reward-summary`, reset handlers, and Tab 3 outcome narrative/graph update display (`app/services/feedback.py:122-314`, `app/services/feedback.py:336-451`).
- It does not bridge directly to GAE. GAE outcome learning, `guarded_update()`, ProfileScorer updates, conservation checks, audit-chain writes, and `TRIGGERED_EVOLUTION` graph writes are performed in `app/routers/triage.py`; this file only handles local feedback/trust/pattern simulation (`app/services/feedback.py:122-289`).

### Function-by-Function Review

- **GraphUpdate** (line 92-98)
  - Purpose: Pydantic model for one simulated graph update.
  - Inputs: `entity`, `field`, `before`, `after`, `direction`.
  - Logic: Pydantic validates fields; `direction` is limited to `"strengthened"` or `"weakened"`.
  - Output: Model instance.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Pydantic validation errors if fields invalid.
  - Invariants/guards: Literal direction validation.

- **NextAlertsOverride** (line 101-105)
  - Purpose: Pydantic model for manual-review override guidance.
  - Inputs: `action`, `count`, `reason`.
  - Logic: Pydantic validation only.
  - Output: Model instance.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Pydantic validation errors.
  - Invariants/guards: No bounds on `count`.

- **OutcomeResponse** (line 108-115)
  - Purpose: Pydantic model returned by `process_outcome()`.
  - Inputs: Alert/outcome fields, update list, consequence, optional next override, narrative.
  - Logic: Pydantic validation and nested model coercion.
  - Output: Model instance.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Pydantic validation errors.
  - Invariants/guards: `graph_updates` must be a list of `GraphUpdate`.

- **process_outcome** (line 122-289)
  - Purpose: Processes correct/incorrect outcome into simulated pattern, edge, precedent, feedback, trust, and narrative state.
  - Inputs: `alert_id`, `decision_id`, `outcome: Literal["correct", "incorrect"]`, optional `alert_category`.
  - Logic: If category missing, maps alert IDs containing `7823` to `credential_access`, `7824` to `malware_execution`, otherwise `_default` (`app/services/feedback.py:143-159`). It gets a pattern ID from `SOCDomainConfig`, an edge key from `_CATEGORY_EDGE_MAP`, then for correct outcomes increases pattern confidence by `0.003` capped at `0.99`, edge weight by `0.02` capped at `0.99`, increments precedent count, and builds positive narrative (`app/services/feedback.py:161-219`). For incorrect outcomes it decreases pattern confidence by `0.06` floored at `0.50`, edge weight by `0.05` floored at `0.50`, and returns a next-5-alerts Tier 2 override (`app/services/feedback.py:221-267`). It stores `FEEDBACK_GIVEN[alert_id]`, calls `update_trust(alert_category, outcome)`, and returns `OutcomeResponse` (`app/services/feedback.py:269-289`).
  - Output: `OutcomeResponse`.
  - Side effects: Mutates `PATTERN_CONFIDENCE`, `EDGE_WEIGHTS`, `PRECEDENT_COUNTS`, imported `FEEDBACK_GIVEN`, and trust state in `feedback_base`.
  - GAE calls: None.
  - Error handling: None; missing pattern IDs/edge keys or invalid outcomes can propagate exceptions if caller bypasses Pydantic validation.
  - Invariants/guards: Confidence caps/floors; edge caps/floors; correct/incorrect branch; fallback category mapping.

- **get_feedback_status** (line 292-314)
  - Purpose: Reports whether feedback has already been submitted for an alert.
  - Inputs: `alert_id`.
  - Logic: Looks up `FEEDBACK_GIVEN` and returns status dict with immutable flag.
  - Output: Dict.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Once present, `can_modify=False`.

- **get_current_pattern_state** (line 317-333)
  - Purpose: Returns current simulated pattern and edge state for display.
  - Inputs: None.
  - Logic: Builds a pattern dict with confidence and precedent count; returns a shallow copy of edges.
  - Output: Dict.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Edge dict is copied; nested pattern data is newly built.

- **seed_trust_history** (line 336-390)
  - Purpose: Seeds trust history with a 12-point asymmetry demo.
  - Inputs: None.
  - Logic: Creates timestamped entries for nine correct, one incorrect, two correct outcomes; appends them to `TRUST_HISTORY`; sets `TRUST_SCORES["travel_login_anomaly"] = 0.23`; sets low-trust flag true.
  - Output: None.
  - Side effects: Mutates imported trust lists/dicts and prints.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Fixed final trust `0.23`; no idempotence guard.

- **reset_trust_state** (line 397-406)
  - Purpose: Resets trust state to seeded baseline.
  - Inputs: None.
  - Logic: Clears trust dict/list/flags, calls `seed_trust_history()`, prints.
  - Output: None.
  - Side effects: Mutates imported trust state.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Clears before seeding, making it idempotent.

- **reset_feedback_state** (line 409-451)
  - Purpose: Resets feedback and simulated graph state to initial values.
  - Inputs: None.
  - Logic: Clears `FEEDBACK_GIVEN`; assigns initial values for all pattern confidences, edge weights, and precedent counts.
  - Output: None.
  - Side effects: Mutates imported feedback store and local module dicts.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Does not delete extra keys that may have been added to pattern/edge/precedent dicts.

### Invariants Enforced
- `GraphUpdate.direction` is limited to `"strengthened"`/`"weakened"` by `Literal` (`app/services/feedback.py:92-98`).
- Correct outcome caps pattern confidence at `0.99` and edge weight at `0.99` (`app/services/feedback.py:170-200`).
- Incorrect outcome floors pattern confidence and edge weight at `0.50` (`app/services/feedback.py:221-238`).
- Unknown category falls back to `_default` only when caller omitted `alert_category`; supplied unknown categories rely on config/map behavior (`app/services/feedback.py:146-163`).
- Feedback is stored by `alert_id`, and status reports it immutable (`app/services/feedback.py:269-280`, `app/services/feedback.py:292-314`).
- `reset_trust_state()` clears trust stores before reseeding (`app/services/feedback.py:397-406`).
- `reset_feedback_state()` clears feedback and restores known baseline values (`app/services/feedback.py:409-451`).

### Potential Issues

#### P1
- No P1 issue found in `feedback.py` itself. The graph/audit/ProfileScorer outcome risks are in the router path that calls this module, not in this file.

#### P2
- All feedback, pattern, edge, precedent, and trust state is process-local mutable state with no lock (`app/services/feedback.py:12-24`, `app/services/feedback.py:36-85`, `app/services/feedback.py:269-280`, `app/services/feedback.py:397-451`). Concurrent outcome submissions or resets can race.
- `process_outcome()` is not idempotent; duplicate calls for the same alert mutate pattern/edge/precedent/trust again before/without an internal duplicate guard (`app/services/feedback.py:170-280`). The router checks duplicate feedback, but the service does not enforce it.
- `seed_trust_history()` appends fixed baseline entries without clearing first (`app/services/feedback.py:336-390`). It is safe through `reset_trust_state()` but duplicate direct calls duplicate seeded history.
- `reset_feedback_state()` restores known keys but does not remove unknown extra keys from `PATTERN_CONFIDENCE`, `EDGE_WEIGHTS`, or `PRECEDENT_COUNTS` (`app/services/feedback.py:409-451`).

#### P3
- Module docstring says it "updates the graph" (`app/services/feedback.py:1-5`), but this file only updates in-memory simulated dictionaries; graph writes happen elsewhere.
- `alert_type = alert_category.replace("_", " ")` is assigned and unused (`app/services/feedback.py:163`).
- Imported `get_trust_status`, `get_all_trust_scores`, and `get_reward_summary` are re-exported for callers but not used internally (`app/services/feedback.py:13-21`); that is intentional per comments but easy to mistake for dead imports.
- Comments for `seed_trust_history()` say "Called at end of reset_trust_state() AND at module import" (`app/services/feedback.py:347-349`), while active code says it is called explicitly from `main.py` startup, not import (`app/services/feedback.py:393-394`).

### Cross-Module Dependencies
- Imports `FEEDBACK_GIVEN` from `app.framework.feedback_store` and re-exports it for callers (`app/services/feedback.py:12`).
- Imports trust stores/functions from `app.framework.feedback_base`, including `TRUST_SCORES`, `TRUST_HISTORY`, `LOW_TRUST_FLAGS`, `update_trust`, and reward/trust query functions (`app/services/feedback.py:13-21`).
- Depends on `SOCDomainConfig.get_pattern_for_category()` to map SOC category to pattern ID (`app/services/feedback.py:11`, `app/services/feedback.py:161`).
- `app/routers/triage.py` depends on `process_outcome()`, `get_feedback_status()`, `get_reward_summary()`, `reset_feedback_state()`, `reset_trust_state()`, and `seed_trust_history()` for outcome and reset flows.
- The service assumes caller-level request validation for `outcome` and duplicate-feedback prevention; direct callers can bypass both.

### AGE Cypher Queries
- `gae_state.py` has graph queries in DeploymentState helpers:
  - `write_bootstrap_state()` existence read: `MATCH (ds:DeploymentState {id: 'current'}) RETURN ds` (`app/services/gae_state.py:473-475`). No `MERGE`, `$param`, `datetime()`, `labels[0]`, list-parameter `IN`, `ON CREATE SET`, or reserved `count` alias.
  - `write_bootstrap_state()` update: `MATCH ... SET ds.bootstrap_mu = ..., ds.bootstrap_shape = ..., ds.bootstrap_stored_at = ..., ds.gae_version = ...` (`app/services/gae_state.py:477-483`). Uses property-level `SET`, not destructive `SET n = {props}`; uses `_S()` inline values.
  - `write_bootstrap_state()` create: `CREATE (ds:DeploymentState {...})` (`app/services/gae_state.py:485-493`). Uses `_S()` inline values; no `MERGE`.
  - `get_bootstrap_centroids()` read via `READ_DEPLOYMENT_STATE`: `MATCH (ds:DeploymentState {id: "current"}) RETURN ...` (`app/services/gae_state.py:443-449`, `app/services/gae_state.py:511`). No listed anti-pattern.
- `feedback.py` contains no Cypher or graph-client calls. Its comments say "graph updates," but the active code mutates in-memory dicts and returns simulated update models (`app/services/feedback.py:122-289`).


# SOC Backend Line-by-Line Review — Part 3

## app/domains/soc/config.py (884 lines)

### Architecture
- This module centralizes SOC domain constants, ProfileScorer geometry, alert-type routing, category/action/factor metadata, policy/situation/prompt/metrics metadata, gate configuration, and calibration formulas (`app/domains/soc/config.py:1-884`).
- Demo and product features depending on it include triage scoring/routing, GAE bootstrap, ProfileScorer construction, outcome feedback pattern selection, domain registry warm-up, simulation, Tab 2 profile/IKS surfaces, campaign correlation defaults, and threshold/gate behavior (`app/domains/soc/config.py:45-120`, `app/domains/soc/config.py:122-230`, `app/domains/soc/config.py:276-312`, `app/domains/soc/config.py:672-745`, `app/domains/soc/config.py:782-884`).
- It encodes compiled SOC expertise as static action/category/factor lists, centroid tensors, W priors, bootstrap distributions, thresholds, alert-type mappings, pattern mappings, campaign settings, and deployment gate formulas. Comments claim constants were extracted from existing services (`app/domains/soc/config.py:1-11`); the active code is now also a primary source for current ProfileScorer action/category/factor contracts.

### Function-by-Function Review

- **SOC_ACTIONS** (line 45)
  - Purpose: Full routing action list.
  - Inputs: None.
  - Logic: Static list `["escalate", "investigate", "suppress", "monitor", "refer_to_analyst"]`.
  - Output: Module constant.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Defines A=5 routing surface.

- **SCORER_ACTIONS / SOC_SCORING_ACTIONS / SOC_ROUTING_ACTIONS / SOC_N_ACT** (line 50-56)
  - Purpose: Splits A=4 scorer actions from A=5 routing actions.
  - Inputs: None.
  - Logic: `SCORER_ACTIONS` excludes `refer_to_analyst`; aliases and count derive from it.
  - Output: Module constants.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Scorer geometry must use `SCORER_ACTIONS`; routing/NL can use full list.

- **LEARNING_ENABLED** (line 61)
  - Purpose: Global feature flag for ProfileScorer updates after verified outcomes.
  - Inputs: None.
  - Logic: Static `False`.
  - Output: Bool constant.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Keeps live ProfileScorer frozen unless changed.

- **SOC_CATEGORIES / BOOTSTRAP_CATEGORY_WEIGHTS** (line 63-83)
  - Purpose: Ordered category axis and bootstrap sampling distribution.
  - Inputs: None.
  - Logic: Six categories and weights summing to 1.0 by inspection.
  - Output: Lists/dicts consumed by scorer/bootstrap.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: No runtime assertion checks weight sum or category coverage.

- **SOC_FACTORS / N_FACTORS / N_CATEGORIES / N_ACTIONS / SOC_FACTOR_SIGMA** (line 89-111)
  - Purpose: Ordered factor axis, derived tensor dimensions, and per-factor sigma.
  - Inputs: None.
  - Logic: Factor order is `privileged_identity_context`, `asset_criticality`, `threat_intel_enrichment`, `pattern_history`, `time_anomaly`, `device_trust`; dimensions derive from list lengths; sigma maps by factor name.
  - Output: Constants used by tensor reshape and explainability.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: `SOC_PROFILE_CENTROIDS` reshape enforces product size later; no explicit sigma coverage assertion.

- **SOC_BOOTSTRAP_* constants** (line 116-120)
  - Purpose: GAE bootstrap calibration parameters.
  - Inputs: None.
  - Logic: Rounds 10, samples/action 5, sigma 0.08, tolerance 0.01, seed 42.
  - Output: Constants consumed by `gae_state.init_learning_state()`.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Static values only.

- **SOC_PROFILE_CENTROIDS / SCORER_PROFILE_CENTROIDS** (line 122-205)
  - Purpose: ProfileScorer centroid tensor.
  - Inputs: None.
  - Logic: Builds a NumPy array and reshapes to `(N_CATEGORIES, N_ACTIONS, N_FACTORS)` = `(6, 4, 6)`; `SCORER_PROFILE_CENTROIDS` aliases it.
  - Output: NumPy tensor.
  - Side effects: Raises at import if reshape size mismatches.
  - GAE calls: None directly; consumed by `ProfileScorer`.
  - Error handling: NumPy reshape errors would propagate at import.
  - Invariants/guards: Shape is enforced by `.reshape(N_CATEGORIES, N_ACTIONS, N_FACTORS)`.

- **SOC_AUTO_APPROVE_THRESHOLDS / SOC_CATEGORY_CONFIDENCE_FLOORS / SOC_AGENT_ZONE_ELEVATED** (line 213-230)
  - Purpose: Triage routing threshold configuration.
  - Inputs: None.
  - Logic: Auto-approve only escalate/investigate/suppress at 0.90; monitor and refer are excluded; credential access floor is 0.95; malware/cloud categories are elevated to agent zone.
  - Output: Dict constants consumed by triage.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: `None` values intentionally block auto-approval.

- **ALERT_TYPE_CATEGORY_MAP / DEFAULT_CATEGORY / resolve_alert_category** (line 235-298)
  - Purpose: Single alert-type to SOC category router.
  - Inputs: `resolve_alert_category(alert_type: str)`.
  - Logic: Looks up the map; on missing key logs `ROUTING_FAILURE` and falls back to `"credential_access"`.
  - Output: Category string.
  - Side effects: Error logging on unmapped alert type.
  - GAE calls: None.
  - Error handling: No exception for unknown types; fallback is returned.
  - Invariants/guards: Comments assert this is the single routing point; code does not enforce that no other mappings exist.

- **resolve_alert_category** (line 276-298)
  - Purpose: Explicit function coverage alias for the alert-type router reviewed above.
  - Inputs: `alert_type: str`.
  - Logic: Map lookup with error-log fallback to `DEFAULT_CATEGORY`.
  - Output: SOC category string.
  - Side effects: Error log on missing mapping.
  - GAE calls: None.
  - Error handling: Unknown types do not raise.
  - Invariants/guards: Fallback category is always returned.

- **CATEGORY_PATTERN_MAP** (line 303-312)
  - Purpose: Maps SOC category to canonical pattern ID for feedback.
  - Inputs: None.
  - Logic: Static dict with `_default`.
  - Output: Dict consumed by `get_pattern_for_category()` and feedback.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: `_default` fallback exists.

- **SOCDomainConfig.name / display_name / trigger_entity** (line 323-332)
  - Purpose: Domain identity metadata.
  - Inputs: `self`.
  - Logic: Returns `"soc"`, `"SOC Copilot"`, and `"Alert"`.
  - Output: Strings.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Fixed metadata.

- **SOCDomainConfig.factors** (line 348-395)
  - Purpose: Returns human-readable domain factor metadata.
  - Inputs: `self`.
  - Logic: Returns six `DomainFactor` objects.
  - Output: List of `DomainFactor`.
  - Side effects: Allocates new objects on each access.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: No assertion that this display order matches `SOC_FACTORS`.

- **SOCDomainConfig.actions** (line 406-443)
  - Purpose: Returns legacy/domain action metadata.
  - Inputs: `self`.
  - Logic: Returns five `DomainAction` objects with time/cost/risk metadata from older action vocabulary.
  - Output: List of `DomainAction`.
  - Side effects: Allocates objects.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Does not match `SCORER_ACTIONS` or `SOC_ACTIONS` IDs.

- **SOCDomainConfig.situation_types** (line 453-508)
  - Purpose: Returns six situation-type descriptors for UI/domain registry.
  - Inputs: `self`.
  - Logic: Static list of `DomainSituationType` objects with IDs, labels, descriptions, colors.
  - Output: List.
  - Side effects: Allocates objects.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: No cross-check against `services/situation.py`.

- **SOCDomainConfig.policies** (line 519-561)
  - Purpose: Returns SOC policy descriptors.
  - Inputs: `self`.
  - Logic: Static list of four `DomainPolicy` objects.
  - Output: List.
  - Side effects: Allocates objects.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: No cross-check against runtime policy registry.

- **SOCDomainConfig.asymmetry_ratio** (line 571-572)
  - Purpose: Exposes asymmetric reward ratio.
  - Inputs: `self`.
  - Logic: Returns `20.0`.
  - Output: Float.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Hardcoded.

- **SOCDomainConfig.prompt_variants** (line 583-609)
  - Purpose: Returns prompt-variant metadata.
  - Inputs: `self`.
  - Logic: Static list of four `PromptVariant` objects.
  - Output: List.
  - Side effects: Allocates objects.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: No runtime sync with evolver state.

- **SOCDomainConfig.metrics_config** (line 617-623)
  - Purpose: Returns business impact constants.
  - Inputs: `self`.
  - Logic: Static dict for saved hours, avoided cost, MTTR reduction, backlog eliminated.
  - Output: Dict.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Hardcoded numbers with no source check in code.

- **SOCDomainConfig.get_profile_centroids / get_initial_centroids / get_categories** (line 630-644)
  - Purpose: Accessors for centroid tensor and category order.
  - Inputs: `self`.
  - Logic: Return copies/lists of constants.
  - Output: NumPy tensor copy or category list.
  - Side effects: None.
  - GAE calls: None directly.
  - Error handling: None.
  - Invariants/guards: Tensor access returns copies to prevent direct mutation.

- **SOCDomainConfig.get_category_index** (line 646-654)
  - Purpose: Maps category name to category-axis index.
  - Inputs: Category string.
  - Logic: Uses `SOC_CATEGORIES.index()`; wraps `ValueError` with valid categories.
  - Output: Int.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Raises `ValueError` on unknown category.
  - Invariants/guards: Unknown category guard.

- **SOCDomainConfig.get_auto_approve_threshold / get_pattern_for_category** (line 656-670)
  - Purpose: Lookup helpers for routing threshold and feedback pattern.
  - Inputs: Action or category string.
  - Logic: Returns threshold or `None`; returns category pattern with `_default` fallback.
  - Output: Float/None or pattern ID string.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: No exception.
  - Invariants/guards: Pattern fallback; no action validation.

- **SOCDomainConfig.build_profile_scorer** (line 672-689)
  - Purpose: Constructs GAE ProfileScorer for SOC.
  - Inputs: `self`.
  - Logic: Calls `ProfileScorer(mu=SCORER_PROFILE_CENTROIDS.copy(), actions=SCORER_ACTIONS, kernel=KernelType.L2, categories=SOC_CATEGORIES, eta_override=0.01, auto_pause_on_amber=True)`.
  - Output: GAE `ProfileScorer`.
  - Side effects: Allocates scorer.
  - GAE calls: Direct `ProfileScorer` constructor and `KernelType.L2`.
  - Error handling: Constructor exceptions propagate.
  - Invariants/guards: Uses copied centroids and A=4 actions; hardcodes `eta_override=0.01`.

- **SOCDomainConfig.get_actions / get_factor_computers / get_campaign_config** (line 692-718)
  - Purpose: Static accessors for routing actions, ordered factor computers, and campaign defaults.
  - Inputs: None.
  - Logic: Returns copies/new instances. Factor order is `PrivilegedIdentityContextFactor`, `AssetCriticalityFactor`, `ThreatIntelEnrichmentFactor`, `PatternHistoryFactorComputer`, `TimeAnomalyFactor`, `DeviceTrustFactor`.
  - Output: List/dict.
  - Side effects: Allocates factor computers.
  - GAE calls: Returns `FactorComputer` implementations.
  - Error handling: None.
  - Invariants/guards: Factor-computer order matches `SOC_FACTORS`.

- **SOCDomainConfig.get_factor_computers** (line 700-709)
  - Purpose: Explicit method coverage alias for the ordered GAE factor-computer factory reviewed above.
  - Inputs: None.
  - Logic: Instantiates the six scorer factors in `SOC_FACTORS` order.
  - Output: List of factor-computer instances.
  - Side effects: Allocates new objects each call.
  - GAE calls: Returns GAE `FactorComputer` implementations.
  - Error handling: None.
  - Invariants/guards: Order must remain synchronized with centroid factor axis.

- **SOCDomainConfig.get_initial_W / get_temperature** (line 726-745)
  - Purpose: Legacy/GAE W-matrix priors and softmax temperature.
  - Inputs: None.
  - Logic: Returns `(N_ACTIONS, N_FACTORS)` NumPy matrix and `0.1`.
  - Output: Matrix/float.
  - Side effects: None.
  - GAE calls: None directly; consumed by learning-state creation.
  - Error handling: Reshape errors propagate if dimensions mismatch.
  - Invariants/guards: W row order matches `SCORER_ACTIONS`; tau fixed at 0.1.

- **SOCDomainConfig.get_seed_queries / get_graph_query_templates / get_narration_templates** (line 751-761)
  - Purpose: Stub extension points.
  - Inputs: `self`.
  - Logic: Return empty list/dicts.
  - Output: Empty collections.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Explicit TODO stubs.

- **soc_config / MAX_ETA_DELTA** (line 765-775)
  - Purpose: Singleton domain config and eta delta constant.
  - Inputs: None.
  - Logic: Instantiates `SOCDomainConfig`; sets max eta delta to `0.005`.
  - Output: Module globals.
  - Side effects: Singleton allocation at import.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: `MAX_ETA_DELTA` mirrors external GAE enforcement by comment, not local code.

- **compute_theta_min** (line 782-795)
  - Purpose: Computes minimum analyst quality threshold.
  - Inputs: `alpha`, `V`.
  - Logic: Returns infinity if either is nonpositive; otherwise `23.53 / (alpha * V)`.
  - Output: Float.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Nonpositive guard.
  - Invariants/guards: Division-by-zero guard.

- **compute_phase3_minimum** (line 802-812)
  - Purpose: Computes minimum verified decisions before self-calibrating gates.
  - Inputs: `V`, `alpha`.
  - Logic: `max(1000, int(20 * V * alpha))`.
  - Output: Int.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Lower bound of 1000 decisions.

- **GateConfig dataclass and fields** (line 820-830)
  - Purpose: Holds deployment gate inputs.
  - Inputs: `n_decisions`, optional `V`, `alpha`, `vol_std`, `per_analyst_precision`.
  - Logic: Dataclass stores fields with defaults.
  - Output: Config object.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Uses `default_factory=dict` for per-analyst precision.

- **GateConfig.n_min / calibrated / spike_sigma / eta_cap / eta_weights / summary** (line 833-884)
  - Purpose: Derived gate properties and summary serialization.
  - Inputs: `self`.
  - Logic: `n_min` calls `compute_phase3_minimum`; `calibrated` compares decisions; `spike_sigma` returns 5.0 before calibration and 3.0 after; `eta_cap` returns 2.0 before calibration, otherwise derived from `vol_std`; `eta_weights` returns uniform or mean-normalized precision weights clipped to `[0.5, 1.5]`; `summary` returns a dict.
  - Output: Int/bool/float/dict.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Negative precision values fall back to uniform weights.
  - Invariants/guards: Eta weights clipped; nonpositive mean precision falls back to uniform.

### Invariants Enforced
- Tensor shape is enforced by `SOC_PROFILE_CENTROIDS.reshape(N_CATEGORIES, N_ACTIONS, N_FACTORS)` (`app/domains/soc/config.py:122-199`).
- ProfileScorer scoring action list is A=4 and excludes `refer_to_analyst` (`app/domains/soc/config.py:45-56`, `app/domains/soc/config.py:672-689`).
- Temperature is fixed at `0.1` in `get_temperature()` (`app/domains/soc/config.py:744-745`).
- Unknown category names raise in `get_category_index()` (`app/domains/soc/config.py:646-654`).
- Unknown alert types log an error and fall back to `DEFAULT_CATEGORY` (`app/domains/soc/config.py:273-298`).
- `compute_theta_min()` returns infinity for nonpositive inputs (`app/domains/soc/config.py:782-795`).
- `compute_phase3_minimum()` enforces a 1000-decision floor (`app/domains/soc/config.py:802-812`).
- `GateConfig.eta_weights` clips calibrated weights to `[0.5, 1.5]` and falls back to uniform for invalid precision inputs (`app/domains/soc/config.py:855-874`).

### Potential Issues

#### P1
- Display/domain factor order in `SOCDomainConfig.factors` is `[privileged_identity_context, asset_criticality, threat_intel_enrichment, time_anomaly, device_trust, pattern_history]` (`app/domains/soc/config.py:348-395`), while scorer/tensor/factor-computer order is `[privileged_identity_context, asset_criticality, threat_intel_enrichment, pattern_history, time_anomaly, device_trust]` (`app/domains/soc/config.py:89-96`, `app/domains/soc/config.py:700-709`). Any consumer treating `config.factors` as the tensor order will mislabel factor values.
- `DeviceTrustFactor` computes higher values for less trusted devices (`app/domains/soc/factors.py:580-590`), but the centroid tensor comments and values treat low `device_trust` as risky/escalating and high `device_trust` as suppressing/trusted (`app/domains/soc/config.py:129-136`, `app/domains/soc/config.py:141-148`, `app/domains/soc/config.py:193-196`). This inversion can materially mis-score device trust.

#### P2
- `SOCDomainConfig.actions` exposes legacy action IDs (`false_positive_close`, `auto_remediate`, `enrich_and_wait`, `escalate_tier2`, `escalate_incident`) that do not match `SOC_ACTIONS`/`SCORER_ACTIONS` (`app/domains/soc/config.py:45-56`, `app/domains/soc/config.py:406-443`). Domain registry/UI consumers can receive a different action vocabulary than triage/scoring.
- `resolve_alert_category()` logs but still falls back to `credential_access` for unmapped alert types (`app/domains/soc/config.py:273-298`). That keeps demos alive but can route unknown production alerts into a specific category.
- Bootstrap weights claim "must sum to 1.0" but no assertion enforces sum or coverage against `SOC_CATEGORIES` (`app/domains/soc/config.py:72-83`).
- `MAX_ETA_DELTA` is declared locally but not enforced locally (`app/domains/soc/config.py:775`); the comment says enforcement lives in GAE.

#### P3
- Import `build_profile_scorer` and `CalibrationProfile` are unused in this file (`app/domains/soc/config.py:15-16`).
- The module docstring says constants are extracted from existing service files (`app/domains/soc/config.py:1-11`), but this file now defines active scorer geometry and gate formulas; the comment understates current ownership.
- `get_seed_queries()`, `get_graph_query_templates()`, and `get_narration_templates()` are TODO stubs returning empty structures (`app/domains/soc/config.py:751-761`).

### Cross-Module Dependencies
- `app/services/gae_state.py` consumes bootstrap constants, categories/actions, ProfileScorer construction, and initial W (`app/domains/soc/config.py:25-30`, `app/domains/soc/config.py:116-120`, `app/domains/soc/config.py:672-738`).
- `app/routers/triage.py` consumes thresholds, elevated categories, `LEARNING_ENABLED`, `SCORER_ACTIONS`, `resolve_alert_category()`, `get_category_index()`, factor computers, and campaign config (`app/domains/soc/config.py:213-230`, `app/domains/soc/config.py:276-298`, `app/domains/soc/config.py:646-718`).
- `app/services/feedback.py` consumes `get_pattern_for_category()` and category pattern mapping (`app/domains/soc/config.py:303-312`, `app/domains/soc/config.py:663-670`).
- `app/core/domain_registry.py` relies on `soc_config = SOCDomainConfig()` and properties such as factors/actions/situation_types/policies/prompt variants/metrics (`app/domains/soc/config.py:315-765`).
- GAE ProfileScorer requires the category/action/factor axis order to remain synchronized across `SOC_CATEGORIES`, `SCORER_ACTIONS`, `SOC_FACTORS`, `SCORER_PROFILE_CENTROIDS`, and factor-computer output (`app/domains/soc/config.py:50-100`, `app/domains/soc/config.py:122-205`, `app/domains/soc/config.py:672-709`).

## app/domains/soc/factors.py (884 lines)

### Architecture
- This module implements SOC factor computers and legacy decision-factor templates. Its active GAE path exposes factor classes for privileged identity, asset criticality, threat intel/campaign enrichment, pattern history/W2, time anomaly, and device trust (`app/domains/soc/factors.py:50-590`).
- Triage scoring depends on `SOCDomainConfig.get_factor_computers()` instantiating these classes in the order expected by `SOC_FACTORS`; explainability/legacy endpoints depend on `SOC_FACTOR_TEMPLATES`, `_contribution()`, and `compute_soc_factors()` (`app/domains/soc/config.py:700-709`, `app/domains/soc/factors.py:601-884`).
- It bridges to GAE through `gae.contracts.SchemaContract`, `PropertySpec`, and `gae.factors.FactorComputer` (`app/domains/soc/factors.py:17-18`). Comments claim four factors use Cypher traversal and two read properties (`app/domains/soc/factors.py:1-9`); active code includes a non-scorer `TravelMatchFactor` and both relationship-traversal and property-read paths.

### Function-by-Function Review

- **log** (line 20)
  - Purpose: Module logger.
  - Inputs: None.
  - Logic: `logging.getLogger(__name__)`.
  - Output: Logger.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: None.

- **_get** (line 27-31)
  - Purpose: Unified dict/object value getter.
  - Inputs: Object/dict, key, default.
  - Logic: Uses `dict.get()` for dicts, otherwise `getattr()`.
  - Output: Value or default.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: None.

- **_S** (line 34-42)
  - Purpose: Serializes values into inline AGE Cypher literals.
  - Inputs: Any scalar-like value.
  - Logic: Handles `None`, bool, int/float, escaped string.
  - Output: Cypher literal string.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Avoids `$param` when used; does not support list/tuple JSON unlike `gae_state._S`.

- **PrivilegedIdentityContextFactor constants** (line 58-68)
  - Purpose: Names factor and declares optional schema property default `0.5`.
  - Inputs: None.
  - Logic: Static `name` and `SchemaContract`.
  - Output: Class constants.
  - Side effects: Instantiates GAE contract objects at import.
  - GAE calls: `SchemaContract`, `PropertySpec`.
  - Error handling: None.
  - Invariants/guards: Default neutral value `0.5`.

- **PrivilegedIdentityContextFactor._clamp** (line 71-72)
  - Purpose: Bounds values to `[0, 1]`.
  - Inputs: Float-like value.
  - Logic: Converts to float, clamps min/max.
  - Output: Float.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Conversion errors propagate.
  - Invariants/guards: Range clamp.

- **PrivilegedIdentityContextFactor._title_risk** (line 75-85)
  - Purpose: Converts user title into risk heuristic.
  - Inputs: Optional title.
  - Logic: Admin/service/system tokens -> 0.9; executive tokens -> 0.7; other nonempty title -> 0.2; missing/blank -> None.
  - Output: Float or None.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Case/whitespace normalization.

- **PrivilegedIdentityContextFactor._resolve_context / compute** (line 88-136)
  - Purpose: Computes privileged identity factor from resolved context.
  - Inputs: Entity/alert/context.
  - Logic: Selects context from explicit `context`, entity, or nested `security_context`; averages available user risk, title risk, MFA risk, and fingerprint risk; returns neutral `0.5` if no components.
  - Output: Float in `[0, 1]`.
  - Side effects: None.
  - GAE calls: Implements GAE `FactorComputer` protocol.
  - Error handling: Bad `risk_score` conversion is ignored.
  - Invariants/guards: Missing context -> 0.5; final clamp.

- **TravelMatchFactor constants / compute** (line 139-197)
  - Purpose: Computes travel-match factor from User->TravelRecord traversal.
  - Inputs: Alert-like object and graph client.
  - Logic: Requires user ID and source location; queries matching travel records; score is `cnt/(cnt+3)` plus recent travel boost capped at 1.0.
  - Output: Float in `[0, 1]` or 0.5 fallback.
  - Side effects: Graph read.
  - GAE calls: Uses GAE contract objects but does not subclass `FactorComputer`.
  - Error handling: Query errors log warning and return 0.5; recency conversion errors are swallowed.
  - Invariants/guards: Missing user/geo -> 0.5; count zero -> 0.5; clamp.

- **AssetCriticalityFactor constants / compute** (line 200-256)
  - Purpose: Computes asset criticality and data sensitivity factor.
  - Inputs: Alert-like object and graph client.
  - Logic: Requires alert ID; traverses Alert->Asset and optional Asset->DataClass; maps criticality to score and adds 0.1 sensitivity boost capped at 1.0.
  - Output: Float.
  - Side effects: Graph read.
  - GAE calls: Uses GAE contract objects.
  - Error handling: Query errors log warning and return 0.5.
  - Invariants/guards: Missing/no result -> 0.5; sensitivity cap.

- **ThreatIntelEnrichmentFactor constants** (line 268-282)
  - Purpose: Names factor, schema contract, and severity map.
  - Inputs: None.
  - Logic: Defines optional default `0.0` and severity map from info to critical.
  - Output: Class constants.
  - Side effects: Instantiates GAE contract objects.
  - GAE calls: `SchemaContract`, `PropertySpec`.
  - Error handling: None.
  - Invariants/guards: Default no-intel value 0.0.

- **ThreatIntelEnrichmentFactor.compute** (line 284-320)
  - Purpose: Combines IOC and internal campaign threat-intel scoring.
  - Inputs: Alert-like object and graph client.
  - Logic: Gets alert ID; pass 1 queries `HAS_INDICATOR` severities/sources, maps max severity plus multi-source boost; pass 3 calls `_internal_campaign_score`; returns the pass with the lowest `value`.
  - Output: Float.
  - Side effects: Graph reads.
  - GAE calls: Implements GAE factor protocol.
  - Error handling: Pass 1 errors log and continue with 0.0; campaign helper handles its own errors.
  - Invariants/guards: Missing alert ID -> 0.0.

- **ThreatIntelEnrichmentFactor._internal_campaign_score** (line 322-372)
  - Purpose: Scores campaign membership.
  - Inputs: Alert ID and graph client.
  - Logic: Queries Alert->Campaign membership, returns neutral 0.50 if absent; high severity -> 0.05, medium -> 0.20, low -> 0.40 plus provenance.
  - Output: Dict with `value`, `provenance_nodes`, `contribution`.
  - Side effects: Graph read.
  - GAE calls: None directly.
  - Error handling: Any exception logs and returns neutral 0.50.
  - Invariants/guards: Never raises by design.

- **PatternHistoryFactor constants / compute** (line 375-429)
  - Purpose: Legacy historical accuracy factor by alert type.
  - Inputs: Alert-like object and graph client.
  - Logic: Reads alert type/situation type; queries Decision->Alert outcomes for same alert type; returns 0.5 until at least 5 resolved, then correct/total clipped.
  - Output: Float in `[0, 1]`.
  - Side effects: Graph read.
  - GAE calls: Uses GAE contract objects.
  - Error handling: Query errors log and return 0.5.
  - Invariants/guards: Missing type -> 0.5; minimum decision count 5; clip.

- **PatternHistoryFactorComputer constants / compute / _fallback_compute** (line 432-523)
  - Purpose: W2 compounding pattern-history factor used in scorer order.
  - Inputs: Alert-like object, graph client, optional action index.
  - Logic: Reads category or alert type; if no category returns fallback 0.40; otherwise queries `TRIGGERED_EVOLUTION` decisions optionally by action, reads `d.factor_snapshot[3]` and `d.decision_number`, computes recency-weighted mean with half-life 30, clips to `[0,1]`; fallback returns 0.40.
  - Output: Float.
  - Side effects: Graph read.
  - GAE calls: Uses GAE contract objects.
  - Error handling: Query errors log and fallback; no guard around malformed result values after query succeeds.
  - Invariants/guards: Missing/no results -> 0.40; recency weighting; clip.

- **TimeAnomalyFactor constants / compute** (line 526-556)
  - Purpose: Scores time anomaly from alert properties.
  - Inputs: Alert-like object and unused graph client.
  - Logic: Weekend login -> 1.0; business hours true -> 0.0; business hours false -> 0.7; missing -> 0.7.
  - Output: Float.
  - Side effects: None.
  - GAE calls: Uses GAE contract objects.
  - Error handling: None.
  - Invariants/guards: Conservative missing-data default 0.7.

- **DeviceTrustFactor constants / compute** (line 559-590)
  - Purpose: Scores device trust/untrustedness from alert properties.
  - Inputs: Alert-like object and unused graph client.
  - Logic: Coerces MFA, fingerprint, and VPN flags to bool; missing VPN inferred from `vpn_provider`; returns count of untrusted flags divided by 3.
  - Output: Float from 0.0 to 1.0.
  - Side effects: None.
  - GAE calls: Uses GAE contract objects.
  - Error handling: None.
  - Invariants/guards: Missing flags count as untrusted except VPN provider inference.

- **SOC_FACTOR_TEMPLATES** (line 601-802)
  - Purpose: Backward-compatible static explainability templates.
  - Inputs: None.
  - Logic: Dict keyed by alert ID, alert type, and `_default`; each template has recommended action, confidence, and five static factors; `compute_soc_factors()` inserts threat-intel at position 2.
  - Output: Module constant.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: `_default` exists; some template factor names are legacy/non-SOC names.

- **_contribution** (line 805-814)
  - Purpose: Maps `value * weight` to contribution label.
  - Inputs: Numeric value and weight.
  - Logic: >0.5 high, >0.25 medium, >0 low, otherwise none.
  - Output: String label.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Numeric errors propagate.
  - Invariants/guards: Threshold ordering.

- **compute_soc_factors** (line 817-884)
  - Purpose: Builds six-factor explainability breakdown for legacy/services route.
  - Inputs: `alert_id`, optional `ti_factor`, optional `alert_type`.
  - Logic: Chooses template by alert ID, alert type, or `_default`; computes contribution labels for static factors; creates default threat-intel factor if absent; returns static first two + threat-intel + remaining static factors plus recommendation/confidence/notes.
  - Output: Dict matching decision-factor endpoint shape.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Template structure errors propagate.
  - Invariants/guards: Fallback template and default threat-intel factor.

### Invariants Enforced
- Most factor `contract` objects define optional properties with default values (`app/domains/soc/factors.py:59-68`, `app/domains/soc/factors.py:211-216`, `app/domains/soc/factors.py:269-274`, `app/domains/soc/factors.py:451-456`, `app/domains/soc/factors.py:538-543`, `app/domains/soc/factors.py:573-578`).
- Factors generally return bounded scores: privileged identity clamps to `[0,1]`; travel clamps; asset caps sensitivity boost; pattern history clips; W2 weighted mean clips; time/device formulas are bounded by branch/math (`app/domains/soc/factors.py:71-136`, `app/domains/soc/factors.py:178-194`, `app/domains/soc/factors.py:245-253`, `app/domains/soc/factors.py:421-426`, `app/domains/soc/factors.py:509-516`, `app/domains/soc/factors.py:545-590`).
- Missing data fallbacks are explicit: privileged identity 0.5, travel 0.5, asset 0.5, threat intel 0.0 or campaign 0.5, legacy pattern history 0.5, W2 pattern history 0.40, time anomaly 0.7, device missing flags as untrusted (`app/domains/soc/factors.py:108-136`, `app/domains/soc/factors.py:156-197`, `app/domains/soc/factors.py:228-256`, `app/domains/soc/factors.py:284-372`, `app/domains/soc/factors.py:400-523`, `app/domains/soc/factors.py:545-590`).
- W2 factor uses recency decay with half-life 30 decisions (`app/domains/soc/factors.py:458`, `app/domains/soc/factors.py:506-515`).
- `compute_soc_factors()` always inserts a threat-intel factor at position 2 and has `_default` fallback (`app/domains/soc/factors.py:817-884`).

### Potential Issues

#### P1
- Multiple factor queries use Neo4j-style named `$param` parameters despite the repo AGE rule forbidding `$param`: `TravelMatchFactor` (`app/domains/soc/factors.py:162-170`), `AssetCriticalityFactor` (`app/domains/soc/factors.py:233-242`), campaign pass 3 (`app/domains/soc/factors.py:335-343`), legacy `PatternHistoryFactor` (`app/domains/soc/factors.py:408-416`), and W2 `PatternHistoryFactorComputer` (`app/domains/soc/factors.py:474-499`). On AGE these can fail or rely on unsafe substitution behavior.
- W2 `PatternHistoryFactorComputer` queries `d.factor_snapshot[3]` (`app/domains/soc/factors.py:480`, `app/domains/soc/factors.py:492`), while the outcome path writes `factor_snapshot` as a JSON string for AGE compatibility. AGE also does not support array properties per `CLAUDE.md`; this likely makes the W2 flywheel read path fail or return unusable values.
- `ThreatIntelEnrichmentFactor` returns the lowest pass value as strongest signal (`app/domains/soc/factors.py:314-320`) and campaign HIGH severity returns 0.05 (`app/domains/soc/factors.py:354-356`), but SOC centroids model higher `threat_intel_enrichment` values as stronger escalation/investigation signal (`app/domains/soc/config.py:141-148`, `app/domains/soc/config.py:189-196`). This polarity mismatch can invert threat-intel scoring.
- `DeviceTrustFactor` polarity appears inverted relative to centroid semantics, as noted in the config findings (`app/domains/soc/factors.py:580-590`, `app/domains/soc/config.py:129-136`).

#### P2
- `AssetCriticalityFactor` gets `alert_id = _get(alert, "id", "")` but queries `Alert {alert_id: ...}` (`app/domains/soc/factors.py:228-242`). If alert dicts carry `alert_id` but not `id`, this returns neutral 0.5.
- `TravelMatchFactor` does not subclass `FactorComputer` and is not included in `SOCDomainConfig.get_factor_computers()` (`app/domains/soc/factors.py:139-197`, `app/domains/soc/config.py:700-709`), despite being documented among factor-computer implementations.
- W2 result processing assumes every query row has numeric `pattern_value` and `decision_num`; malformed/null values can raise after a successful query and are not caught outside the query `try` block (`app/domains/soc/factors.py:501-516`).
- `compute_soc_factors()` legacy templates contain factor names that do not match `SOC_FACTORS` for several alert types, such as `failure_rate`, `source_reputation`, and `campaign_signature_match` (`app/domains/soc/factors.py:601-802`). These are explainability-only but can confuse consumers expecting the six SOC factor names.
- `PatternHistoryFactorComputer` uses `category = alert.category or alert.alert_type` without resolving alert type to canonical category (`app/domains/soc/factors.py:469-471`), so W2 category matching can miss rows written with canonical categories.

#### P3
- The top docstring says "Four use Cypher relationship traversal; two read alert properties" (`app/domains/soc/factors.py:1-9`), but active code includes `TravelMatchFactor` plus both `PatternHistoryFactor` and `PatternHistoryFactorComputer`, making the count ambiguous.
- Several query comments claim relationship traversal, but the active query style still uses `$param`, contrary to the repo's AGE guidance (`app/domains/soc/factors.py:139-170`, `app/domains/soc/factors.py:200-242`, `app/domains/soc/factors.py:375-416`).
- `SOC_FACTOR_TEMPLATES` is large static legacy data in the same file as live GAE factor computers (`app/domains/soc/factors.py:601-802`), increasing review and drift risk.

### Cross-Module Dependencies
- `SOCDomainConfig.get_factor_computers()` constructs `PrivilegedIdentityContextFactor`, `AssetCriticalityFactor`, `ThreatIntelEnrichmentFactor`, `PatternHistoryFactorComputer`, `TimeAnomalyFactor`, and `DeviceTrustFactor` in scorer factor order (`app/domains/soc/config.py:700-709`).
- `app.domains.soc.orchestrator.compute_factor_vector()` likely depends on each factor exposing `name`, `contract`, and async `compute()` with compatible arguments.
- `app/services/triage.py` and the decision-factor endpoint depend on `SOC_FACTOR_TEMPLATES`, `_contribution()`, and `compute_soc_factors()` for backward-compatible explainability (`app/domains/soc/factors.py:601-884`).
- W2/flywheel behavior depends on triage outcome writing `TRIGGERED_EVOLUTION`, `verified_correct`, `factor_snapshot`, `decision_number`, and `action_index` fields that this module reads (`app/domains/soc/factors.py:474-499`).
- Campaign scoring depends on campaign correlation writing `Alert-[:MEMBER_OF]->Campaign` with `confidence`, `severity`, `campaign_id`, `nl_summary`, and `trigger_rule` fields (`app/domains/soc/factors.py:322-372`).

### AGE Cypher Queries
- `TravelMatchFactor.compute()` uses `MATCH (u:User {id: $user})-[:HAS_TRAVEL]->(t:TravelRecord) WHERE t.destination = $geo RETURN count(t) AS cnt ...` (`app/domains/soc/factors.py:162-170`). It uses named `$user`/`$geo`, violating AGE no-`$param`; `cnt` alias is compliant.
- `AssetCriticalityFactor.compute()` uses `MATCH (a:Alert {alert_id: $alert})-[:DETECTED_ON]->(asset:Asset) OPTIONAL MATCH ...` (`app/domains/soc/factors.py:233-242`). It uses named `$alert`, violating AGE no-`$param`.
- `ThreatIntelEnrichmentFactor.compute()` IOC pass uses inline `_S(alert_id)` and `HAS_INDICATOR` traversal (`app/domains/soc/factors.py:292-296`). No listed AGE anti-pattern in that query.
- `ThreatIntelEnrichmentFactor._internal_campaign_score()` uses `MATCH (a:Alert {alert_id: $alert_id})-[:MEMBER_OF]->(c:Campaign)` with params (`app/domains/soc/factors.py:335-343`). It uses named `$alert_id`, violating AGE no-`$param`.
- `PatternHistoryFactor.compute()` uses `WHERE a.alert_type = $type` with params and returns `count(d) AS total` plus sum correct (`app/domains/soc/factors.py:408-416`). It uses named `$type`, violating AGE no-`$param`; alias is `total`, not reserved `count`.
- `PatternHistoryFactorComputer.compute()` uses `WHERE d.category = $category` and optional `d.action_index = $action_index`, and returns `d.factor_snapshot[3]` (`app/domains/soc/factors.py:474-499`). It uses named parameters and array-style indexing on a graph property; both are unsafe for AGE given repo rules and current JSON-string storage.
- No Cypher appears in `config.py`.


# SOC Backend Line-by-Line Review — Part 4

## app/services/evidence_room.py (243 lines)

### Architecture
- This module builds Act 7 evidence-room payloads from the in-memory audit chain, conservation health, and graph snapshot state (`app/services/evidence_room.py:1-243`).
- It does not write graph data or GAE state directly; it aggregates evidence for summary/export routes and degrades to empty structures when upstream audit, graph snapshot, or learning-health dependencies fail (`app/services/evidence_room.py:88-239`).
- The code comments are minimal. The active behavior is fail-soft evidence collection rather than a strict evidence verifier.

### Function-by-Function Review

- **log** (line 8)
  - Purpose: Module logger.
  - Inputs: None.
  - Logic: `logging.getLogger(__name__)`.
  - Output: Logger.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: None.

- **SUMMARY_LIMIT / EXPORT_LIMIT / FORMAT_VERSION / PRODUCT_NAME / KNOWN_STATUSES** (line 10-14)
  - Purpose: Module-level evidence serialization constants.
  - Inputs: None.
  - Logic: Summary exports first 20 audit rows; full export caps at 10,000 rows; known conservation statuses are fixed.
  - Output: Constants.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Status normalization later only allows `GREEN`, `AMBER`, `RED`, `CALIBRATING`, and `UNKNOWN`.

- **_now_iso** (line 17-18)
  - Purpose: UTC timestamp helper.
  - Inputs: None.
  - Logic: Formats `datetime.now(timezone.utc)` as second-resolution `Z` timestamp.
  - Output: String timestamp.
  - Side effects: Reads current clock.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Uses UTC timezone explicitly.

- **_safe_float** (line 21-27)
  - Purpose: Defensive float coercion.
  - Inputs: Any value and default.
  - Logic: Returns default for `None`, `TypeError`, or `ValueError`; otherwise `float(value)`.
  - Output: Float.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Swallows type/value conversion errors.
  - Invariants/guards: Does not reject NaN/Inf.

- **_safe_int** (line 30-36)
  - Purpose: Defensive integer coercion.
  - Inputs: Any value and default.
  - Logic: Returns default for `None`, `TypeError`, or `ValueError`; otherwise `int(value)`.
  - Output: Int.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Swallows type/value conversion errors.
  - Invariants/guards: None.

- **_clamp_rate** (line 39-40)
  - Purpose: Clamp rate-like values to `[0, 1]`.
  - Inputs: Any numeric-like value.
  - Logic: Calls `_safe_float()` then min/max clamps.
  - Output: Float.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Conversion errors become 0.0 via `_safe_float()`.
  - Invariants/guards: Enforces rate bounds.

- **_truncate** (line 43-45)
  - Purpose: Shorten IDs/hashes for summary display.
  - Inputs: Any value and max length.
  - Logic: Converts `None` to empty string, otherwise `str(value)`, then slices.
  - Output: String.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Fixed default length of 12.

- **_json_safe** (line 48-57)
  - Purpose: Recursively convert arbitrary payload values to JSON-compatible values.
  - Inputs: Any value.
  - Logic: Recurses into dict/list/tuple/set, passes primitive values, calls `tolist()` when present, and stringifies everything else.
  - Output: JSON-serializable structure.
  - Side effects: Iterates unordered sets into list order.
  - GAE calls: None.
  - Error handling: No explicit exception handling for failing `tolist()`.
  - Invariants/guards: Dict keys are stringified.

- **_empty_audit_trail** (line 60-61)
  - Purpose: Empty fallback for audit collection.
  - Inputs: None.
  - Logic: Returns `{"entries": [], "total": 0}`.
  - Output: Dict.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: None.

- **_empty_hash_chain** (line 64-65)
  - Purpose: Empty fallback for hash-chain verification.
  - Inputs: None.
  - Logic: Returns `verified=True`, `entries=0`, `status="VERIFIED"`.
  - Output: Dict.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: No distinction between no evidence and verified evidence.

- **_empty_conservation** (line 68-75)
  - Purpose: Empty conservation fallback.
  - Inputs: None.
  - Logic: Returns unknown status, zero signal/threshold/count, and not frozen.
  - Output: Dict.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: None.

- **_empty_override_analysis** (line 78-85)
  - Purpose: Empty override-analysis fallback.
  - Inputs: None.
  - Logic: Returns zero totals and empty per-category map.
  - Output: Dict.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: None.

- **EvidenceRoomService** (line 88-239)
  - Purpose: Aggregates evidence summary/export data.
  - Inputs: Method-specific only.
  - Logic: Calls audit, conservation, and override collectors and returns JSON-safe payloads.
  - Output: Summary/export dicts.
  - Side effects: Imports runtime services lazily and can trigger audit reconstruction from memory.
  - GAE calls: Indirectly calls `LearningHealthMonitor.evaluate()`, which reads `get_learning_state()`.
  - Error handling: Collection helpers catch broad exceptions and return degraded evidence.
  - Invariants/guards: Status normalization and JSON-safety wrappers.

- **EvidenceRoomService.get_evidence_summary** (line 89-99)
  - Purpose: Build compact evidence-room summary.
  - Inputs: `self`.
  - Logic: Collects non-export audit entries, conservation status, and override analysis; adds generation timestamp.
  - Output: JSON-safe dict with `generated_at`, `audit_trail`, `conservation`, `override_analysis`, and `hash_chain`.
  - Side effects: Calls `_collect_audit(export=False)`, `_collect_conservation()`, and `_collect_override_analysis()`.
  - GAE calls: Indirect through conservation.
  - Error handling: Delegated to helper methods.
  - Invariants/guards: Summary limit is applied in `_collect_audit()`.

- **EvidenceRoomService.export_evidence_pack** (line 101-116)
  - Purpose: Build full export evidence pack.
  - Inputs: `self`.
  - Logic: Collects export-mode audit entries, conservation, override analysis, and export metadata.
  - Output: JSON-safe dict with export metadata and evidence sections.
  - Side effects: Same collectors as summary path.
  - GAE calls: Indirect through conservation.
  - Error handling: Delegated to helper methods.
  - Invariants/guards: Export metadata includes format version and product name.

- **EvidenceRoomService._collect_audit** (line 118-144)
  - Purpose: Read audit rows and hash-chain verification.
  - Inputs: `export` boolean.
  - Logic: Imports audit helpers, reconstructs memory chain, reads rows and verification result, formats up to summary/export limit, and returns raw rows for later analysis.
  - Output: `(audit_trail, hash_chain, rows)` tuple.
  - Side effects: Calls `reconstruct_from_memory()`; reads in-memory audit state.
  - GAE calls: None.
  - Error handling: Broad exception logs warning and returns empty audit trail plus `_empty_hash_chain()`.
  - Invariants/guards: Export cap 10,000; summary cap 20; chain status is `"VERIFIED"` if `verification["verified"]` is truthy or missing.

- **EvidenceRoomService._format_summary_entry** (line 146-158)
  - Purpose: Compact one audit row for summary display.
  - Inputs: Audit row dict.
  - Logic: Selects decision ID, action, category, confidence, outcome, timestamp, and truncated hash.
  - Output: Dict.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Missing keys fall back to empty strings/defaults.
  - Invariants/guards: Full decision ID is retained separately as `decision_id_full`.

- **EvidenceRoomService._format_export_entry** (line 160-171)
  - Purpose: Format one audit row for export.
  - Inputs: Audit row dict.
  - Logic: Preserves full ID/hash and chain index with action/category/confidence/outcome/timestamp.
  - Output: Dict.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Missing keys fall back to empty strings/defaults.
  - Invariants/guards: Confidence coerced to float.

- **EvidenceRoomService._collect_conservation** (line 173-207)
  - Purpose: Gather conservation health and verified-decision count.
  - Inputs: `self`.
  - Logic: Calls `LearningHealthMonitor.evaluate(neo4j_client)`; normalizes status; prefers graph snapshot verified count and falls back to learning-state decision count.
  - Output: Dict with `status`, `product`, `threshold`, `verified_decisions`, and `frozen`.
  - Side effects: Imports `neo4j_client`, learning-health monitor, graph snapshot, and GAE state lazily.
  - GAE calls: Indirect `get_learning_state()` fallback and inside learning-health evaluation.
  - Error handling: Broad exceptions log warning/debug and continue with default values.
  - Invariants/guards: Unknown statuses become `"UNKNOWN"`; numeric values go through safe coercion.

- **EvidenceRoomService._collect_override_analysis** (line 209-239)
  - Purpose: Calculate override/confirmation totals and per-category counts.
  - Inputs: Raw audit rows.
  - Logic: Counts rows, counts truthy `analyst_confirmed` as overrides, counts `outcome == "correct"` as confirmations, then overlays graph snapshot totals when no audit rows are present and always reads snapshot override rate/per-category counts when available.
  - Output: Dict with totals, override rate, and per-category counts.
  - Side effects: Reads graph snapshot state.
  - GAE calls: None.
  - Error handling: Snapshot failures are debug-logged and ignored.
  - Invariants/guards: Override rate is clamped to `[0, 1]`.

- **dumps_json_safe** (line 242-243)
  - Purpose: Serialize JSON-safe payloads for export or debugging.
  - Inputs: Payload dict.
  - Logic: Runs `_json_safe()` then `json.dumps(indent=2, sort_keys=True)`.
  - Output: JSON string.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: `json.dumps()` errors propagate.
  - Invariants/guards: Sorts keys for stable output.

### Invariants Enforced
- Summary audit output is limited to 20 entries and export output to 10,000 entries (`app/services/evidence_room.py:10-11`, `app/services/evidence_room.py:129-133`).
- Conservation status is uppercased and constrained to known status values (`app/services/evidence_room.py:14`, `app/services/evidence_room.py:184-186`).
- Rate outputs are clamped to `[0, 1]` (`app/services/evidence_room.py:39-40`, `app/services/evidence_room.py:235`).
- Numeric conversions fall back instead of raising (`app/services/evidence_room.py:21-36`).
- JSON export recursively converts unsupported values to strings or lists (`app/services/evidence_room.py:48-57`).

### Potential Issues

#### P1
- Audit collection failure returns `_empty_hash_chain()` with `verified=True` and `status="VERIFIED"` (`app/services/evidence_room.py:64-65`, `app/services/evidence_room.py:118-124`). In an Act 7 evidence surface, an unavailable audit chain can be reported as verified rather than unknown or failed.

#### P2
- Override analysis treats truthy `analyst_confirmed` as an override count (`app/services/evidence_room.py:211-212`). If that field means analyst confirmation, as the name implies, the evidence room can invert confirmation/override reporting.
- `_collect_conservation()` catches learning-health failures and returns `UNKNOWN` with zero signal/threshold (`app/services/evidence_room.py:173-207`). This keeps the UI alive but can hide broken conservation monitoring unless logs are watched.
- `_collect_audit()` slices the first rows returned by `get_decision_rows()` without sorting (`app/services/evidence_room.py:126-133`). If the audit layer does not guarantee newest-first order, summaries may show stale evidence.
- The service reads mutable in-memory audit and snapshot state without locking (`app/services/evidence_room.py:118-239`). Concurrent outcome writes can produce internally inconsistent totals, rates, and hash-chain counts.

#### P3
- `_empty_conservation()` and `_empty_override_analysis()` are defined but `_empty_conservation()` is not used by `_collect_conservation()` (`app/services/evidence_room.py:68-85`, `app/services/evidence_room.py:173-207`).
- `_safe_float()` accepts NaN/Inf and `_json_safe()` passes floats through unchanged (`app/services/evidence_room.py:21-27`, `app/services/evidence_room.py:48-57`), which can produce non-strict JSON values.
- Export format version is hardcoded in this module with no schema object or compatibility test visible here (`app/services/evidence_room.py:12`, `app/services/evidence_room.py:101-116`).

### AGE Cypher Queries
- No Cypher query strings appear directly in `evidence_room.py`.
- AGE/Cypher behavior is indirect through `LearningHealthMonitor.evaluate(neo4j_client)` (`app/services/evidence_room.py:173-181`).

### Cross-Module Dependencies
- Depends on `app.framework.audit.get_decision_rows`, `reconstruct_from_memory`, and `verify_chain` for audit rows and hash verification (`app/services/evidence_room.py:119-123`).
- Depends on `app.services.learning_health.LearningHealthMonitor.evaluate()` and `app.db.neo4j.neo4j_client` for conservation status (`app/services/evidence_room.py:176-179`).
- Depends on `app.state.graph_snapshot.get_snapshot()` for verified decision counts, override rate, correct counts, and category counts (`app/services/evidence_room.py:189-197`, `app/services/evidence_room.py:217-229`).
- Falls back to `app.services.gae_state.get_learning_state().decision_count` when graph snapshot is unavailable (`app/services/evidence_room.py:198-204`).

## app/services/learning_health.py (708 lines)

### Architecture
- This module implements conservation monitoring, auto-pause red-day counting, alert volume spike detection, category freeze detection, analyst precision weighting, and verification-rate health (`app/services/learning_health.py:1-708`).
- Tab 2 runtime evolution, Act 7 evidence, deployment gates, and feedback safety surfaces depend on it. It bridges to GAE via `gae.calibration` helpers and `get_learning_state()` (`app/services/learning_health.py:26-28`).
- Comments explicitly describe rolling conservation semantics and AGE parameter limitations in `_count_red_days()` (`app/services/learning_health.py:1-17`, `app/services/learning_health.py:251-266`), but several later queries still use named `$param` syntax.

### Function-by-Function Review

- **log** (line 31)
  - Purpose: Module logger.
  - Inputs: None.
  - Logic: `logging.getLogger(__name__)`.
  - Output: Logger.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: None.

- **CALIBRATION_DECISIONS / CALIBRATION_DAYS / AUTO_PAUSE_RED_DAYS / AUTO_PAUSE_LOOKBACK_DAYS / WINDOW_DECISIONS** (line 33-42)
  - Purpose: Conservation and rollout threshold constants.
  - Inputs: None.
  - Logic: Sets 300-decision calibration, 30-day calibration/lookback, 14 RED-day auto-pause threshold, and 50-decision rolling alpha/V window.
  - Output: Constants.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Comments state RED counting is cumulative over lookback, not consecutive.

- **LearningHealthMonitor class constants** (line 45-51)
  - Purpose: Public class-level mirror of thresholds and sigma levels.
  - Inputs: None.
  - Logic: Copies module constants and sets amber/red sigma to 2.0/3.0.
  - Output: Class constants.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: None.

- **LearningHealthMonitor._extract_components** (line 58-109)
  - Purpose: Extract `alpha`, `q`, `V`, and history count from verified update history.
  - Inputs: `history`, `window=50`, `q_window=400`.
  - Logic: Uses recent alpha_effective values, last 400 outcomes for q, and timestamp spread for V with raw-count fallback.
  - Output: Dict with numeric components and `n`.
  - Side effects: Logs debug on timestamp parsing failure.
  - GAE calls: Reads GAE WeightUpdate-like objects by attribute.
  - Error handling: Empty history returns zeros; timestamp parse errors fall back to raw count.
  - Invariants/guards: Span is floored at one minute to avoid division by zero.

- **LearningHealthMonitor._compute_signal** (line 116-118)
  - Purpose: Composite conservation signal.
  - Inputs: `alpha`, `q`, `V`.
  - Logic: Multiplies the three values.
  - Output: Float.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Numeric errors propagate.
  - Invariants/guards: None.

- **LearningHealthMonitor._build_calibration_baseline** (line 121-144)
  - Purpose: Build baseline mean/std from first 300 decisions.
  - Inputs: History list.
  - Logic: Samples every 10th point, extracts rolling components for each chunk, computes signal, then mean/std.
  - Output: `(baseline_mean, baseline_std)`.
  - Side effects: None.
  - GAE calls: Indirectly processes GAE WeightUpdate-like objects.
  - Error handling: Empty calibration window/signals return zero baseline/std.
  - Invariants/guards: Uses at most first 300 decisions.

- **LearningHealthMonitor.evaluate** (line 151-244)
  - Purpose: Main conservation-health evaluation.
  - Inputs: Optional Neo4j/AGE service.
  - Logic: Reads learning state/history, extracts components, computes theta minimum and conservation result, returns calibrating before 300 decisions, otherwise compares signal with absolute and relative floors and counts RED days.
  - Output: Dict with status, signal, theta, conservation, components, baseline, red days, auto-pause, and interpretation.
  - Side effects: Reads mutable learning state and optionally graph HealthLog nodes.
  - GAE calls: `get_learning_state()`, `compute_theta_min()`, `derive_theta_min()`, and `check_conservation()`.
  - Error handling: `compute_theta_min()` `ValueError` falls back to `derive_theta_min()`; other GAE/calibration errors propagate.
  - Invariants/guards: Calibration phase before 300 decisions; RED if conservation fails or signal drops below baseline-3sigma; AMBER below baseline-2sigma.

- **LearningHealthMonitor._count_red_days** (line 251-277)
  - Purpose: Count distinct RED days within 30-day lookback.
  - Inputs: Neo4j/AGE service or `None`.
  - Logic: Computes cutoff epoch in Python, inlines integer literal into query, returns count of distinct day buckets.
  - Output: Int red-day count.
  - Side effects: Graph read.
  - GAE calls: None.
  - Error handling: `None` client or query failure returns 0.
  - Invariants/guards: Avoids `$param` by inlining computed integer; uses `red_days` alias, not `count`.

- **LearningHealthMonitor._interpret** (line 284-302)
  - Purpose: Human-readable status explanation.
  - Inputs: Status, signal, theta minimum, red days.
  - Logic: Returns fixed strings for GREEN/AMBER/RED and generic fallback otherwise.
  - Output: String.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Auto-pause wording when red-day threshold is reached.

- **_round_comps** (line 309-310)
  - Purpose: Round float component values for API output.
  - Inputs: Component dict.
  - Logic: Rounds floats to 4 decimals, preserves non-floats.
  - Output: Dict.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: None.

- **_VOLUME_WINDOW_DAYS** (line 317)
  - Purpose: Rolling window constant for volume/category baselines.
  - Inputs: None.
  - Logic: Fixed 30 days.
  - Output: Int constant.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: None.

- **compute_volume_baseline** (line 320-383)
  - Purpose: Calculate 30-day alert-volume baseline and spike threshold.
  - Inputs: `neo4j_client`.
  - Logic: Queries daily alert counts after cutoff, computes mean/std with std floor 1.0, gets current decision count, creates `GateConfig`, and derives spike sigma/threshold.
  - Output: Dict with mean, std, threshold, sigma, window, and data point count.
  - Side effects: Graph read and learning-state read.
  - GAE calls: Indirect `get_learning_state().decision_count`.
  - Error handling: Query failures log warning and return zero baseline with std floor.
  - Invariants/guards: Std floor prevents zero-variance threshold; spike sigma comes from `GateConfig`.

- **detect_volume_spike** (line 386-424)
  - Purpose: Compare today's alert count to volume baseline.
  - Inputs: `neo4j_client`, `today_count`.
  - Logic: Calls `compute_volume_baseline()`, compares count to threshold, logs warning if exceeded.
  - Output: Dict with spike flag and baseline values.
  - Side effects: Graph read through baseline and warning log on spike.
  - GAE calls: Indirect through baseline.
  - Error handling: Baseline exceptions are handled in baseline function.
  - Invariants/guards: Strict `>` threshold.

- **_FREEZE_MULTIPLIER** (line 431)
  - Purpose: Category freeze multiplier.
  - Inputs: None.
  - Logic: Fixed 2.0.
  - Output: Float constant.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: None.

- **compute_category_baseline** (line 434-467)
  - Purpose: Compute 30-day baseline category distribution.
  - Inputs: `neo4j_client`.
  - Logic: Queries alert counts by category after cutoff, computes fractional share per category.
  - Output: Dict category -> share.
  - Side effects: Graph read.
  - GAE calls: None.
  - Error handling: Query failure logs warning and returns `{}`.
  - Invariants/guards: Returns `{}` if total is zero; rounds shares to 6 decimals.

- **detect_frozen_categories** (line 470-519)
  - Purpose: Identify categories to freeze during an active volume spike.
  - Inputs: `neo4j_client`, today's category counts.
  - Logic: Exits unless volume spike is active, computes today's shares, compares to 2x baseline share, and returns categories exceeding threshold.
  - Output: List of category names.
  - Side effects: Reads GAE state volume-spike flag and graph category baseline; logs warnings.
  - GAE calls: `is_volume_spike_active()` from `gae_state`.
  - Error handling: Baseline query errors become empty baseline; no exception for no spike/no counts.
  - Invariants/guards: No freeze without active volume spike; zero baseline skips category.

- **_MIN_ANALYST_DECISIONS / _MIN_ANALYSTS_REQUIRED** (line 526-527)
  - Purpose: Analyst precision qualification thresholds.
  - Inputs: None.
  - Logic: Requires 10 decisions per analyst and at least 2 qualifying analysts.
  - Output: Int constants.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Used to suppress sparse analyst weighting.

- **compute_analyst_precision** (line 530-569)
  - Purpose: Compute analyst precision weights from verified Decision nodes.
  - Inputs: `neo4j_client`.
  - Logic: Queries decisions grouped by verifier, filters analysts below 10 decisions, computes precision, then suppresses output unless at least two analysts qualify.
  - Output: Dict analyst -> precision.
  - Side effects: Graph read.
  - GAE calls: None.
  - Error handling: Query failure logs warning and returns `{}`.
  - Invariants/guards: Minimum decisions and minimum analyst count.

- **compute_verification_health** (line 576-708)
  - Purpose: Calculate verification coverage/drift/conservation health.
  - Inputs: `neo4j_client`.
  - Logic: Counts total and verified decisions, computes last/prior 7-day verification rates, calls `LearningHealthMonitor.evaluate()`, and maps three conditions to GREEN/AMBER/RED.
  - Output: Dict with status, coverage/drift/conservation booleans and counts.
  - Side effects: Multiple graph reads and conservation evaluation.
  - GAE calls: Indirect `get_learning_state()` via `evaluate()`.
  - Error handling: Individual graph/conservation failures are debug-logged and default to zero/UNKNOWN.
  - Invariants/guards: Coverage healthy at >=0.20; drift healthy at >=80% of prior rate; prior zero drift treated healthy; coverage zero forces RED.

### Invariants Enforced
- Empty learning history returns zero components (`app/services/learning_health.py:75-76`).
- Timestamp span for V is floored at one minute (`app/services/learning_health.py:99-100`).
- Calibration mode holds until 300 decisions (`app/services/learning_health.py:169-188`).
- RED status is selected for failed conservation or signal below baseline-3sigma; AMBER below baseline-2sigma (`app/services/learning_health.py:197-203`).
- Auto-pause activates at 14 RED days in the 30-day lookback (`app/services/learning_health.py:207-208`, `app/services/learning_health.py:291-296`).
- Volume std is floored at 1.0 before spike threshold computation (`app/services/learning_health.py:363-364`).
- Category freeze requires an active volume spike (`app/services/learning_health.py:490-492`).
- Analyst precision excludes analysts with fewer than 10 decisions and returns no weights unless at least two analysts qualify (`app/services/learning_health.py:526-569`).
- Verification coverage zero forces RED (`app/services/learning_health.py:690-695`).

### Potential Issues

#### P1
- Several functions use named `$param` query parameters despite the same file documenting that `$param` is forbidden for AGE: `compute_volume_baseline()` (`app/services/learning_health.py:344-350`), `compute_category_baseline()` (`app/services/learning_health.py:446-452`), `compute_analyst_precision()` (`app/services/learning_health.py:544-554`), and `compute_verification_health()` last/prior window queries (`app/services/learning_health.py:628-653`). These monitoring paths can fail under the AGE rules that `_count_red_days()` explicitly follows.
- `compute_volume_baseline()` silently returns a zero mean/std baseline after query failure, then floors std to 1.0 and returns a finite spike threshold of 5.0 or 3.0 depending on gate state (`app/services/learning_health.py:344-375`). A broken graph query can therefore make spike detection compare live traffic against a synthetic low threshold.

#### P2
- `LearningHealthMonitor.evaluate()` reads mutable learning-state history without locking or snapshot copy before deriving alpha/q/V and baseline (`app/services/learning_health.py:151-244`). Concurrent updates can produce mixed-window health results.
- `_count_red_days()` returns 0 on query failure, disabling auto-pause even if HealthLog access is broken (`app/services/learning_health.py:251-277`).
- Calibration baseline can have zero standard deviation; then AMBER/RED relative thresholds collapse to the same baseline value (`app/services/learning_health.py:121-144`, `app/services/learning_health.py:197-203`).
- `compute_verification_health()` defaults conservation status to `UNKNOWN` and treats `UNKNOWN` as healthy (`app/services/learning_health.py:671-680`). A conservation-monitor failure can improve the health rollup.
- The total/verified decision queries return aliases `total` and `verified` instead of `cnt`; the standing AGE guidance explicitly says to avoid `count as alias` and use `cnt` (`app/services/learning_health.py:600-615`).
- `count(CASE WHEN ...)` is used for conditional verification counts (`app/services/learning_health.py:633-635`, `app/services/learning_health.py:650-652`); AGE support for this syntax should be verified because no fallback query is provided.

#### P3
- `Optional` is imported but not used (`app/services/learning_health.py:24`).
- `compute_theta_min` is imported from GAE and `GateConfig.compute_theta_min` also exists in SOC config, so the name can confuse readers about which theta formula is active (`app/services/learning_health.py:26`, `app/domains/soc/config.py:782-795`).
- The module docstring references `docs/project_status_and_plan_v3_part2.md P9` but the review did not verify that doc as part of this backend-source pass (`app/services/learning_health.py:1-17`).

### AGE Cypher Queries
- `_count_red_days()` uses inline integer cutoff and `RETURN count(DISTINCT (...)) AS red_days` (`app/services/learning_health.py:266-273`). It avoids `$param`; alias is not `count`; no `datetime()`, `labels[0]`, `ON CREATE SET`, `ON MATCH SET`, or list-parameter `IN`.
- `compute_volume_baseline()` uses `$cutoff_epoch` and a parameter dict (`app/services/learning_health.py:344-351`). This violates the no-`$param` AGE rule.
- `compute_category_baseline()` uses `$cutoff_epoch` and a parameter dict (`app/services/learning_health.py:446-453`). This violates the no-`$param` AGE rule.
- `compute_analyst_precision()` uses `$min_decisions` and a parameter dict (`app/services/learning_health.py:544-555`). This violates the no-`$param` AGE rule.
- `compute_verification_health()` total/verified count queries use no params but return aliases `total` and `verified` (`app/services/learning_health.py:600-615`), which diverges from the standing `cnt` alias convention.
- `compute_verification_health()` last/prior 7-day queries use `$last_start`, `$now`, and `$prior_start` parameter dicts (`app/services/learning_health.py:628-654`). These violate the no-`$param` AGE rule.
- No `ON CREATE SET`, `ON MATCH SET`, `datetime()`, `labels[0]`, or list-parameter `IN` patterns appear in this file.

### Cross-Module Dependencies
- GAE dependency: `gae.calibration.compute_theta_min`, `derive_theta_min`, and `check_conservation` (`app/services/learning_health.py:26`).
- GAE state dependency: `app.services.gae_state.get_learning_state()` for history/decision count and `is_volume_spike_active()` for category freeze gating (`app/services/learning_health.py:28`, `app/services/learning_health.py:490`).
- SOC config dependency: `GateConfig` drives spike sigma based on current decision count (`app/services/learning_health.py:340-341`, `app/services/learning_health.py:371-373`).
- Graph dependency: caller-supplied `neo4j_client` must support `run_query()` with the query/parameter style used in each helper.
- Evidence dependency: `EvidenceRoomService._collect_conservation()` calls `LearningHealthMonitor.evaluate()` and exposes its output (`app/services/evidence_room.py:173-207`).

## app/graph_schema.py (819 lines)

### Architecture
- This module is the declared single source of truth for SOC graph structure, seed data loading, health verification, and CLI seed/verify commands (`app/graph_schema.py:1-32`).
- It is intentionally allowed to perform destructive seed cleanup for controlled labels/origins, unlike runtime request paths (`app/graph_schema.py:20-27`, `app/graph_schema.py:420-773`).
- It bridges to `ci_platform.graph.get_graph_client()` when no client is provided and uses `_S()` for AGE-safe inline literals (`app/graph_schema.py:46-69`, `app/graph_schema.py:210-221`, `app/graph_schema.py:420-431`).

### Function-by-Function Review

- **log** (line 35)
  - Purpose: Module logger.
  - Inputs: None.
  - Logic: `logging.getLogger(__name__)`.
  - Output: Logger.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: None.

- **SYNTHETIC_ORIGIN / DEMO_ORIGIN** (line 38-39)
  - Purpose: Origin labels for protected training data and resettable demo alerts.
  - Inputs: None.
  - Logic: Static string constants.
  - Output: Constants.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Comments define ownership semantics.

- **_S** (line 46-69)
  - Purpose: Serialize Python values into inline AGE Cypher literals.
  - Inputs: Any scalar/list/tuple/numpy-like value.
  - Logic: Emits `null`, lowercase booleans, numeric strings, JSON-string-encoded list/tuple/numpy arrays, and escaped quoted strings; rejects NaN/Inf.
  - Output: Cypher literal string.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Raises `ValueError` for NaN/Inf.
  - Invariants/guards: Avoids AGE array properties by storing lists as JSON strings; escapes backslashes and single quotes.

- **GRAPH_CONTRACT** (line 76-195)
  - Purpose: Declarative graph-node/edge/invariant contract.
  - Inputs: None.
  - Logic: Defines required node labels, min counts, required/optional fields, edge counts/endpoints, and invariant query strings.
  - Output: Dict constant.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Verification code later consumes these required fields and count thresholds.

- **_BACKBONE_LABELS / _DATA_LABELS / _DATA_ORIGINS** (line 200-203)
  - Purpose: Clean-phase label/origin allowlists.
  - Inputs: None.
  - Logic: Backbone labels are fully owned and deleted wholesale; Decision/Alert are deleted only for synthetic/demo origins.
  - Output: Lists.
  - Side effects: None at import.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Intended to constrain destructive seed cleanup.

- **verify_graph** (line 210-356)
  - Purpose: Validate the live graph against `GRAPH_CONTRACT`.
  - Inputs: Optional client.
  - Logic: Lazily obtains graph client, checks node counts and sample fields, edge counts and endpoint labels, then invariant queries.
  - Output: Report dict with `healthy`, `issues`, `warnings`, and `counts`.
  - Side effects: Sets default `GRAPH_BACKEND=age` if no client is supplied; graph reads.
  - GAE calls: None.
  - Error handling: Count/sample/edge/invariant query failures are captured as issues or warnings.
  - Invariants/guards: Counts always populated; missing required fields mark unhealthy; unexpected fields become warnings.

- **_validate_json** (line 363-413)
  - Purpose: Validate seed JSON before graph mutation.
  - Inputs: Parsed JSON dict.
  - Logic: Checks top-level sections, required fields on first three items in each section, decision-alert references, and campaign-alert references.
  - Output: None on success.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Raises `ValueError` with accumulated errors.
  - Invariants/guards: Only samples first three items for field validation; referential checks cover all decisions and campaign alert IDs.

- **seed_graph** (line 420-773)
  - Purpose: Load and optionally clean/recreate the complete SOC graph from v5 JSON.
  - Inputs: `json_path`, `clean=False`, optional client.
  - Logic: Gets graph client, loads/validates JSON, optionally deletes owned labels/origins, creates nodes, creates relationships, creates training decisions with `DECIDED_ON` edges atomically, then runs `verify_graph()`.
  - Output: Verification report.
  - Side effects: Reads JSON file, prints progress, mutates graph extensively, can delete graph nodes when `clean=True`, sets `GRAPH_BACKEND=age`, and calls `client.ensure_graph()`.
  - GAE calls: None.
  - Error handling: JSON validation fails before mutation; many edge/decision creation errors are logged/count-tracked and seeding continues; verification result is returned even if unhealthy.
  - Invariants/guards: Decision + `DECIDED_ON` edge are created in one query; seed lists are serialized through `_S()`.

- **CLI entry point** (line 780-819)
  - Purpose: Support `python -m app.graph_schema verify` and `seed`.
  - Inputs: `sys.argv`.
  - Logic: Sets graph backend and Python path, validates command, adjusts Windows event-loop policy, runs verify/seed, and exits nonzero on unhealthy/not found cases.
  - Output: Console output and process exit code.
  - Side effects: Mutates `os.environ`, `sys.path`, event loop policy, and graph state for seed command.
  - GAE calls: None.
  - Error handling: Bad usage or missing file exits 1; unhealthy verify/seed exits 1.
  - Invariants/guards: Seed defaults to `support/setup/zero_day_decisions_v5.json`.

### Invariants Enforced
- `_S()` rejects NaN/Inf and serializes lists as JSON strings to avoid AGE array properties (`app/graph_schema.py:46-69`).
- `verify_graph()` enforces minimum counts for labels and edge types from `GRAPH_CONTRACT` (`app/graph_schema.py:224-244`, `app/graph_schema.py:288-307`).
- `verify_graph()` samples synthetic-origin nodes for required fields and flags unexpected fields as warnings (`app/graph_schema.py:247-282`).
- `verify_graph()` checks declared edge endpoint labels when edges exist (`app/graph_schema.py:310-327`).
- Contract invariants enforce no orphan decisions, no missing synthetic outcomes, pending demo alert presence, non-null decision categories, and seeded alerts with users/assets (`app/graph_schema.py:145-195`, `app/graph_schema.py:331-356`).
- `_validate_json()` raises before graph mutation when required top-level keys, sampled required fields, or referential integrity checks fail (`app/graph_schema.py:363-413`).
- `seed_graph()` keeps session decisions with `origin=NULL` during clean, according to comments and query filters (`app/graph_schema.py:446-494`).
- Training decisions and `DECIDED_ON` edges are created atomically in one query (`app/graph_schema.py:725-750`).

### Potential Issues

#### P1
- `seed_graph(clean=True)` deletes all nodes for `_BACKBONE_LABELS` without origin filtering (`app/graph_schema.py:446-482`). The comments say these labels are fully owned, but if runtime campaign correlation or non-seed data also writes `User`, `Asset`, `Campaign`, `ThreatIndicator`, or `AttackPattern`, a seed clean can destroy non-seed graph data.
- `_validate_json()` checks required fields only on the first three items of each section (`app/graph_schema.py:377-392`). Later malformed rows can pass validation and then fail mid-seed, leaving a partially rebuilt graph after the clean phase.
- `seed_graph()` continues after edge and decision creation failures, then returns the verification report rather than rolling back (`app/graph_schema.py:603-756`). With `clean=True`, a partially seeded graph can remain live after failures.

#### P2
- `verify_graph()` samples only one synthetic-origin node per label for required field presence (`app/graph_schema.py:247-282`). It can report healthy while most nodes of that label are missing required fields.
- `seed_graph(clean=False)` always uses `CREATE` and comments acknowledge it duplicates data if run twice (`app/graph_schema.py:420-427`). There is no duplicate-detection guard before non-clean seeding.
- `GRAPH_CONTRACT["Decision"]["required_fields"]` includes `factor_vector` but the seed path serializes list values to JSON strings via `_S()` (`app/graph_schema.py:83-86`, `app/graph_schema.py:735-738`). Consumers expecting a list must parse the string consistently.
- Clean-phase deletion of `Decision`/`Alert` is scoped by origin, but verification count requirements include all nodes with the label (`app/graph_schema.py:224-244`, `app/graph_schema.py:486-494`). Existing session decisions can affect health counts and warnings.
- CLI mutates `sys.path` using `os.path.join(os.path.dirname(__file__), "..")` (`app/graph_schema.py:785`). When run from unusual working directories, module resolution may differ from the package runtime.

#### P3
- The module docstring says "Three public symbols" but several module constants and CLI behavior are also operationally significant (`app/graph_schema.py:1-32`, `app/graph_schema.py:38-203`, `app/graph_schema.py:780-819`).
- `_validate_json()` does not validate field types, numeric ranges, category/action vocabularies, or factor-vector length (`app/graph_schema.py:363-413`).
- Progress output uses `print()` throughout `seed_graph()` instead of structured logging (`app/graph_schema.py:433-771`).
- `verify_graph()` treats unexpected fields as warnings based on a single sampled node, which can be noisy when data evolves intentionally (`app/graph_schema.py:268-275`).

### AGE Cypher Queries
- `GRAPH_CONTRACT` invariant queries use `count(...) AS n` and inline origin constants (`app/graph_schema.py:145-195`). They do not use `$param`, `datetime()`, `labels[0]`, `ON CREATE SET`, or `ON MATCH SET`.
- `verify_graph()` node and edge counts use `RETURN count(...) AS cnt` (`app/graph_schema.py:224-227`, `app/graph_schema.py:288-291`, `app/graph_schema.py:314-317`). This follows the `cnt` alias convention.
- `verify_graph()` sample query inlines `_S(SYNTHETIC_ORIGIN)` (`app/graph_schema.py:247-250`). No named params.
- `seed_graph(clean=True)` uses `DETACH DELETE` for backbone labels and scoped Decision/Alert origins (`app/graph_schema.py:476-494`). This is a destructive query by design and is explicitly documented as special-case seed behavior.
- Seed node/edge creation uses `CREATE`, `MATCH`, and inline `_S()` literals throughout phases 2-8 (`app/graph_schema.py:515-750`). No `MERGE`, named `$param`, `ON CREATE SET`, `ON MATCH SET`, `datetime()`, `labels[0]`, or list-parameter `IN` appears.
- `_S()` serializes list-like values as JSON strings, avoiding AGE array properties but requiring consumers to parse strings for fields such as `category_sequence` and `factor_vector` (`app/graph_schema.py:57-62`, `app/graph_schema.py:549-554`, `app/graph_schema.py:735-738`).
- No APOC calls appear in this file.

### Cross-Module Dependencies
- Depends on `ci_platform.graph.get_graph_client()` when no graph client is injected (`app/graph_schema.py:216-221`, `app/graph_schema.py:426-431`).
- `conftest.py` and the CLI depend on `verify_graph()` according to the module docstring (`app/graph_schema.py:8-18`).
- Tests around destructive decision queries must allowlist this file because seed clean uses `DETACH DELETE` (`app/graph_schema.py:20-27`).
- Factor and triage paths depend on seeded relationships such as `INVOLVES`, `DETECTED_ON`, `CLASSIFIED_AS`, `HAS_INDICATOR`, `MEMBER_OF`, and `DECIDED_ON` (`app/graph_schema.py:583-750`).
- Runtime W2/feedback paths depend on Decision fields and `TRIGGERED_EVOLUTION` edges, but this seed path only declares a zero-min-count `TRIGGERED_EVOLUTION` contract and does not create evolution events (`app/graph_schema.py:139`, `app/graph_schema.py:76-195`, `app/graph_schema.py:725-750`).

