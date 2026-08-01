# SOC Test Architecture After Correctness Unification

## §1 EXECUTIVE SUMMARY

The current suite has 38 failures in 9 test files. All 38 are Type A outcome-processing tests: they call `report_decision_outcome()` and therefore require the Decision to exist in the GraphStore before `write_outcome()` can materialize its read model. The failures are not 38 independent production defects; they share one fixture mismatch.

Production initializes a GraphConfig-resolved AGE-backed GraphStore for the SOC scorer and exposes that store through `SOCCompoundingScorerAdapter.graph_store` (`app/services/gae_state.py:204-221`, `app/domains/soc/scorer_adapter.py:45-48`). The post-unification route obtains that store and calls `get_decision()`/`write_outcome()` (`app/routers/triage.py:1777-1816`). The failing tests instead create a synthetic Decision only in a mocked `neo4j_client`; their scorer is either not patched at the route binding or has no matching GraphStore record (`tests/test_dual_update_fix.py:143-164`, `tests/test_factor_validation.py:63-81`, `tests/test_servicenow_triage_integration.py:81-105`).

Recommended architecture: use one stateful `InMemoryGraphStore(domain="soc")` as the Decision authority, wrap it in the production `SOCCompoundingScorerAdapter`, and provide a separate stateful SOC non-Decision client for alert, campaign, entity, and fire-and-forget integration behavior. A common test harness should seed Decisions through `write_decision()` and inject the same adapter instance used by the route. Do not make a Neo4j stub authoritative for Decisions, and do not add a production fallback that recreates the retired raw-Cypher path.

| Measure | Result |
|---|---:|
| Failing tests | 38 |
| Distinct failing files | 9 |
| Type A: outcome processing | 38 |
| Type B: incidental triage flow | 0 |
| Type C: obsolete Neo4j-specific behavior | 0 whole tests; several assertions are implementation-coupled |
| Type D: other | 0 |
| Current full-suite result | 2,166 passed, 38 failed, 14 skipped |

The current test doubles are not Rule-63-compliant Decision doubles: most return canned rows based on query text and record calls, but do not maintain a Decision state that `get_decision()` and `write_outcome()` can share (`tests/test_rl_triage_integration.py:15-84`, `tests/test_triggered_evolution.py:36-62`).

**Implementation readiness: YES, after the production route’s remaining Decision writes are separately resolved.** The test migration itself is well-defined, but the current route still directly sets `d.correct` during centroid persistence (`app/routers/triage.py:2322-2335`); that must not be hidden by a test fixture.

## §2 TEST INVENTORY

### 2.1 Failure counts by file

| File | Failed tests | Count | Classification |
|---|---|---:|---|
| `tests/test_dual_update_fix.py` | `test_single_update_per_outcome` (`:187`), `test_fix_preserves_referral_behavior` (`:261`), `test_fix_preserves_outcome_persistence` (`:275`) | 3 | A |
| `tests/test_factor_validation.py` | `test_empty_factor_vector_raises` (`:90`), `test_none_factor_vector_raises` (`:95`), `test_wrong_length_factor_vector_raises` (`:100`), `test_valid_factor_vector_scores_correctly` (`:105`), `test_factor_validation_message_includes_expected_length` (`:112`) | 5 | A |
| `tests/test_rl_full_pipeline.py` | `test_all_flags_true_pipeline_exercises_rl_paths` (`:20`) | 1 | A |
| `tests/test_rl_triage_integration.py` | `test_reward_computation_fires_on_outcome_when_flag_enabled` (`:135`), `test_outcome_persists_analyst_action_override_measurement_fields` (`:148`), `test_outcome_persists_non_override_measurement_fields` (`:164`), `test_outcome_without_analyst_action_does_not_fabricate_action` (`:177`), `test_campaign_measurement_fields_share_decision_node_with_cohort_flags` (`:192`), `test_reward_skipped_when_flag_false` (`:209`), `test_posterior_update_fires_when_explored_and_not_vetoed` (`:219`), `test_posterior_update_skipped_when_referral_vetoed` (`:239`), `test_chain_credit_fires_on_correct_outcome_when_enabled` (`:259`), `test_chain_credit_skipped_when_triggered_evolution_write_fails` (`:278`), `test_chain_credit_skipped_when_flag_false` (`:315`), `test_reward_failure_does_not_crash_outcome` (`:331`) | 12 | A |
| `tests/test_servicenow_triage_integration.py` | `test_confirmed_escalation_creates_servicenow_incident` (`:119`), `test_confirmed_escalation_is_idempotent` (`:131`), `test_non_escalate_does_not_create_servicenow_incident` (`:144`), `test_incorrect_escalation_does_not_create_incident` (`:151`) | 4 | A |
| `tests/test_soc_c9b_l5_proof.py` | `test_soc_c9b_full_flow_writes_all_three_l5_types` (`:160`) | 1 | A |
| `tests/test_soc_dk_l5.py` | `test_soc_outcome_l5_centroid_uses_actual_action_on_override` (`:406`), `test_soc_outcome_l5_centroid_uses_predicted_when_actual_equals_predicted` (`:427`), `test_soc_dk_persistence_skipped_when_reestimate_fails` (`:441`), `test_soc_dk_persistence_runs_when_reestimate_succeeds` (`:456`) | 4 | A |
| `tests/test_triage_routing_actions.py` | `test_refer_to_analyst_increments_decision_count` (`:111`), `test_refer_to_analyst_does_not_update_centroids` (`:121`), `test_fv_none_still_increments_decision_count` (`:134`) | 3 | A |
| `tests/test_triggered_evolution.py` | `test_correct_outcome_creates_triggered_evolution_edge` (`:119`), `test_incorrect_outcome_does_not_create_evolution_edge` (`:134`), `test_routing_action_does_not_create_evolution_edge` (`:147`), `test_evolution_edge_has_required_properties` (`:160`), `test_evolution_edge_failure_does_not_block_outcome` (`:196`) | 5 | A |
| **Total** |  | **38** | **A: 38** |

### 2.2 What the failures actually verify

- `test_dual_update_fix.py` verifies one learning update, referral behavior, and persistence fields. Its helper returns a factor-vector row from `_Neo4j`, but creates no Decision in a GraphStore (`tests/test_dual_update_fix.py:17-31`, `:118-164`, `:187-283`). The tests are outcome-processing tests, not tests of Neo4j itself.
- `test_factor_validation.py` verifies malformed and valid factor vectors after outcome lookup. Its `_make_neo4j()` returns a canned Decision-shaped row only when the query contains the factor-vector projection (`tests/test_factor_validation.py:39-61`). These tests need a Decision because the route must first validate that the requested Decision exists; the factor-vector assertions can remain independent of AGE.
- `test_rl_full_pipeline.py` verifies reward ledger, posterior, ETA, and chain-credit side effects after an outcome. It composes `_patch_common_outcome()` from the RL integration file (`tests/test_rl_full_pipeline.py:8-16`, `:35-96`). It needs a seeded Decision for the common route precondition, but does not need live AGE.
- `test_rl_triage_integration.py` verifies reward flags, analyst override metadata, campaign fields, exploration posterior updates, and chain credit. Its `FakeNeo4j` returns a fixed `_decision_record()` and records query strings, but has no Decision write/read state (`tests/test_rl_triage_integration.py:15-84`, `:92-123`, `:135-344`). These are outcome-processing and side-effect tests; campaign and exploration data are non-Decision context carried by the test client.
- `test_servicenow_triage_integration.py` verifies confirmed escalation creates one idempotent ServiceNow incident and that non-confirmed/non-escalation outcomes do not. Its AsyncMock returns only a factor-vector row and has no Decision state (`tests/test_servicenow_triage_integration.py:38-61`, `:81-115`). It needs a Decision for the route contract but not live alert/campaign data.
- `test_soc_c9b_l5_proof.py` verifies the full outcome path persists centroid, DK-weight, and conservation artifacts. `_C9BNeo4j` stores health rows locally but returns the factor-vector row from a hardcoded branch; it does not create the route Decision (`tests/test_soc_c9b_l5_proof.py:44-113`, `:160-230`). The conservation-only test at `:240-250` passes and is not part of the 38.
- `test_soc_dk_l5.py` verifies actual-action selection, predicted-action selection, DK failure handling, and DK success handling. `_RouteNeo4j` returns a fixed factor-vector record and has no Decision store (`tests/test_soc_dk_l5.py:283-326`, `:329-404`). These tests need a Decision only as the route’s input record.
- `test_triage_routing_actions.py` verifies routing outcomes increment counts without centroid mutation, including a null factor vector. Its AsyncMock returns the requested factor-vector row and the tests patch the route scorer independently (`tests/test_triage_routing_actions.py:33-61`, `:76-109`). They are outcome-processing tests; `refer_to_analyst` must be seeded as a Decision whose action is the routing action.
- `test_triggered_evolution.py` verifies the correct-outcome evolution edge, negative/routing suppression, required edge properties, and non-blocking failure. Its fake only captures queries containing `TRIGGERED_EVOLUTION` and returns a fixed factor-vector row (`tests/test_triggered_evolution.py:36-62`). The query-content assertions are partly implementation-coupled, but the behavior remains valid after the Decision authority moves to the GraphStore.

No failed test is a pure Type C test of the retired Neo4j Decision implementation. Assertions such as “query contains `d.correct`” or “query contains `EvolutionEvent`” should be rewritten as state/behavior assertions, not deleted as obsolete (`tests/test_rl_triage_integration.py:148-188`, `tests/test_triggered_evolution.py:160-191`).

## §3 MOCK ARCHITECTURE

### 3.1 Current mock surface

| Mock surface | Current behavior | Real production equivalent | Assessment |
|---|---|---|---|
| `neo4j_client.run_query()` | Returns canned rows based on query substrings; captures query text | AGE client query execution through `app.db.neo4j.neo4j_client` | Useful for non-Decision query contracts, not a Decision authority (`tests/test_factor_validation.py:39-61`) |
| `neo4j_client.get_alert()` / `get_security_context()` | Returns fixed dictionaries | AGE-backed Alert/entity/context reads | Appropriate only for non-Decision route context (`tests/test_rl_triage_integration.py:22-84`) |
| Sequence/cross-category methods | Returns configured integer counters | Legacy-compatible referral-count methods on the graph client | Non-Decision behavior; retain behind a stateful client double (`tests/test_rl_triage_integration.py:78-84`) |
| Query list / `_evo` list | Records calls and permits string assertions | No direct production equivalent; represents observability of calls | Replace most string assertions with state assertions where a GraphStore API exists (`tests/test_triggered_evolution.py:39-62`, `:119-211`) |
| Patched scorer / learning state | Canned scorer or context manager, often independent of the route’s real store | `SOCCompoundingScorerAdapter` wrapping `CompoundingScorer` and a GraphStore | Must be replaced by one adapter/store pair for outcome tests (`tests/test_dual_update_fix.py:118-164`, `tests/test_soc_dk_l5.py:329-404`) |
| Audit/event/health/service doubles | AsyncMock or MagicMock side effects | Audit ledger, event bus, health monitor, ServiceNow connector | Keep where the test targets that boundary, but do not let them stand in for Decision storage (`tests/test_servicenow_triage_integration.py:81-103`) |

### 3.2 State tracking and Rule 63

The doubles partially track interactions (`queries`, `_evo`, configurable counters), but they do not track the Decision lifecycle. `_Neo4j`, `_RouteNeo4j`, and the ServiceNow `_make_neo4j()` return hardcoded factor-vector rows; `FakeNeo4j` stores one fixed record and returns it for every factor-vector query (`tests/test_dual_update_fix.py:17-31`, `tests/test_soc_dk_l5.py:283-300`, `tests/test_rl_triage_integration.py:15-39`, `tests/test_servicenow_triage_integration.py:38-61`). They therefore cannot answer the contract operation “does Decision X exist, and what is its current status/correct value?” from their own state.

The shared `conftest.py` does not provide a Neo4j mock or a GraphStore fixture; it provides only an optional live-backend marker and an isolated AGE graph fixture (`tests/conftest.py:16-29`, `:40-66`). The failing files independently construct their stubs, which explains why there is no common state authority to repair.

### 3.3 Existing correct GraphStore pattern

SOC already has a usable pattern: construct `InMemoryGraphStore(domain="soc")`, pass it into `CompoundingScorer.from_preset("soc", graph_store=store, profile="test")`, and seed Decisions followed by `write_outcome()` (`tests/test_j6_state_capture.py:22-64`). The adapter tests independently construct `SOCCompoundingScorerAdapter(graph_store=InMemoryGraphStore(domain="soc"))` (`tests/test_scorer_adapter.py:20-35`, `:44-57`). These tests prove the SDK store and scorer can run without live AGE; the missing piece is making the triage route use that same object.

## §4 PRODUCTION VS TEST MISMATCH

### 4.1 Production flow

```text
startup_event()
  -> gae_state.init_learning_state()
  -> GraphConfig.load("soc")
  -> create_graph_store(...)
  -> SOCCompoundingScorerAdapter(graph_store=graph_store)
  -> LearningState.profile_scorer

report_decision_outcome()
  -> get_profile_scorer()
  -> adapter.graph_store
  -> get_decision(decision_id, domain="soc")
  -> write_outcome(..., domain="soc")
  -> neo4j_client for remaining graph reads/side effects
```

The startup path constructs the contract store at `app/services/gae_state.py:199-221`, attaches the adapter at `:290`, and returns it through `get_profile_scorer()` at `:440-445`. The adapter exposes the wrapped store at `app/domains/soc/scorer_adapter.py:45-48`. The route uses that store for the pre-read and outcome write at `app/routers/triage.py:1777-1816`, then still uses `neo4j_client` for the context projection, audit-chain metadata, analyst history, evolution, and other side effects (`app/routers/triage.py:1817-1833`, `:1843-1865`, `:1877-1882`, `:2464-2488`).

The physical graph is intended to be shared, but the Python wrappers are distinct: `app/db/neo4j.py` creates the AGE client from the same GraphConfig graph/DSN at `:28-54`, while `gae_state.py` separately creates the scorer GraphStore at `:208-215`. Tests must therefore share the test store explicitly; patching only `neo4j_client` cannot satisfy the scorer-store lookup.

There is also a residual production correctness risk: after the contract write, centroid persistence still directly sets `d.correct` and `d.verified_at_epoch` at `app/routers/triage.py:2322-2335`. That conflicts with C2 and should be handled as a separate production cleanup before declaring the route fully unified. The test architecture must expose this rather than mask it.

### 4.2 Test flow today

```text
test helper
  -> mocked neo4j_client.run_query() returns Decision-shaped row
  -> patched or unpatched scorer/learning state

report_decision_outcome()
  -> real route-bound get_profile_scorer()
  -> adapter.graph_store.get_decision(decision_id)
  -> no matching record
  -> HTTP 404 before outcome/learning assertions
```

The mismatch is primarily (a): tests create the Decision-shaped response in a mock but do not create the Decision in the GraphStore. It is also (c) in tests that patch a scorer or `gae_state.get_profile_scorer` without patching the route’s already-imported binding (`tests/test_factor_validation.py:67-81`, `tests/test_servicenow_triage_integration.py:81-103`). It is not a missing global setup in `conftest.py`, because that file has no such Decision fixture (`tests/conftest.py:1-80`).

### 4.3 Decision reads/writes by triage operation

| Operation in `triage.py` | GraphStore | `neo4j_client` | Design consequence |
|---|---|---|---|
| Outcome existence and materialization | Yes: `get_decision` and `write_outcome` (`:1777-1816`) | No for the contract write | Must use shared test store |
| Outcome context projection | No | Yes: factor/action/campaign/exploration read (`:1817-1833`) | Keep non-Decision client temporarily, or migrate this read to GraphStore |
| Audit hash/index attachment | No contract method | Yes, raw `SET` (`:1843-1865`) | Separate audit metadata path; do not use it to create correctness |
| Analyst history | No | Yes, domain-scoped read (`:1877-1882`) | Non-authoritative query double is sufficient |
| Centroid delta projection | No | Yes, raw Decision `SET`, including `d.correct` (`:2322-2335`) | Production C2 cleanup required |
| Triggered evolution | No | Yes, Decision-linked write (`:2443-2488`) | Prefer a future GraphStore method; harness may capture it as a non-contract side effect until then |
| Alert/campaign/entity/referral context | No direct GraphStore API in the route | Yes, including client methods and campaign repository (`:197-222`, `:522-752`, `:957-981`) | Retain a separate stateful non-Decision double |

## §5 MIGRATION DESIGN

### 5.1 Answers to D1-D6

**D1 — Use InMemoryGraphStore as the authority, wrapped by the production adapter.** Do not create a second SOC-specific Decision database. A small SOC test harness may provide SOC-specific builders and non-Decision context, but its Decision operations must delegate to `InMemoryGraphStore`. This matches the existing adapter/state-capture pattern (`tests/test_j6_state_capture.py:22-64`) and production construction (`app/services/gae_state.py:208-221`).

**D2 — Keep `neo4j_client` available for non-Decision operations during this migration.** The current GraphStore protocol/store does not provide the alert, campaign, entity, security-context, or referral-count methods used by triage; the route explicitly calls those client methods (`app/routers/triage.py:197-222`, `:750-752`, `:957-981`). The test double should be stateful and limited to those operations. Decision context reads should be moved to the GraphStore in a later production cleanup, or the harness should provide a read projection sourced from the same builder data—not an independent Decision authority.

**D3 — No whole failed test is obsolete.** The behavior under test remains relevant: learning, RL, ServiceNow, routing, L5 persistence, and evolution behavior still exist. Query-string assertions are obsolete where they assert the old write mechanism (`tests/test_rl_triage_integration.py:148-188`); replace them with Decision property assertions and side-effect state. The triggered-evolution behavior is not obsolete, but its required-property assertions should inspect the stateful edge/event double or a GraphStore read rather than a raw query string (`tests/test_triggered_evolution.py:160-191`).

**D4 — Minimal sound change: one shared harness plus targeted fixture rewiring.** Add a support module and fixture, not a production fallback:

1. Build one `InMemoryGraphStore(domain="soc")`.
2. Build one `SOCCompoundingScorerAdapter(graph_store=store)` using the test profile and isolated outbox.
3. Seed the requested Decision via `store.write_decision()`, including category, action, factor vector, campaign/exploration metadata, and recommended action.
4. Inject that adapter into the route’s actual `triage.get_profile_scorer` binding and the scorer-acquisition path used by learning code. The route binding matters because `triage.py` imports `get_profile_scorer` at module scope (`app/routers/triage.py:34`); patching only `app.services.gae_state.get_profile_scorer` is insufficient.
5. Supply a separate `SOCNonDecisionClient` that answers alert/context/campaign/referral calls from its own dictionaries and records evolution/audit side effects.
6. Convert the nine failing files to use the harness. Keep their domain-specific assertions, but replace raw Decision-write query assertions with reads from the store or explicit non-Decision side-effect state.

**D5 — Use builders, not a giant autouse seed.** A `DecisionBuilder` should create exactly the requested Decision and return its ID. A fixture should own lifecycle and cleanup. Required builder fields should include `decision_id` (or a deterministic returned ID), category, action, factor vector, confidence, campaign ID, exploration flags, and recommended action. Tests that need a missing Decision should deliberately omit the builder call and assert 404. This prevents test order dependence and preserves the existing missing-decision test (`tests/test_triage_routing_actions.py:144-183`).

**D6 — Blast radius is bounded but not zero.** `tests/test_rl_full_pipeline.py` imports the common outcome helper from `test_rl_triage_integration.py` (`tests/test_rl_full_pipeline.py:8-16`), so that helper must remain compatible. The same RL file also uses the fake for analyze-alert tests (`tests/test_rl_triage_integration.py:389-445`); split outcome and analyze fixtures instead of globally replacing `FakeNeo4j`. The shared `conftest.py` has no Neo4j fixture (`tests/conftest.py:1-80`), so other test files are not automatically affected. Existing InMemory-based adapter/J6 tests should remain unchanged (`tests/test_j6_state_capture.py:22-112`, `tests/test_scorer_adapter.py:20-35`).

### 5.2 Proposed harness shape

```python
class SOCTriageHarness:
    store: InMemoryGraphStore
    scorer: SOCCompoundingScorerAdapter
    graph_client: SOCNonDecisionClient

    def add_decision(...):
        # sole Decision setup path: store.write_decision(...)
        # return the actual generated decision_id

    def decision(self, decision_id):
        return self.store.get_decision(decision_id, domain="soc")

    def outcome(self, decision_id, ...):
        return self.store.get_decision(decision_id, domain="soc")
```

The harness should use real `InMemoryGraphStore` and real `SOCCompoundingScorerAdapter`; only external boundary behavior should be represented by a stateful `SOCNonDecisionClient`. The client must not implement `get_decision`, `write_decision`, or `write_outcome`. Those methods belong exclusively to the store.

## §6 IMPLEMENTATION PLAN

### Phase 0 — Production contract audit

1. Resolve the remaining direct `d.correct` write in `triage.py:2322-2335`; route centroid metadata through an approved GraphStore method or remove the duplicate correctness assignment. Add a scanner regression for this exact path.
2. Decide whether the factor/action context read at `triage.py:1817-1833` should become a GraphStore read. If not, document it as a non-Decision projection and make the test harness source it from the seeded Decision fixture.
3. Verify that triggered-evolution writes at `triage.py:2443-2488` have a supported stateful test surface.

### Phase 1 — Shared harness

1. Add `backend/tests/support/soc_triage_harness.py` and a fixture in `tests/conftest.py`.
2. Use `CompoundingScorer.from_preset("soc", graph_store=store, profile="test", enable_rl=False)` or the production adapter constructor, following `tests/test_j6_state_capture.py:22-40`.
3. Add an isolated `CI_PERSISTENCE_OUTBOX_PATH` fixture, following `tests/test_j6_state_capture.py:14-20`.
4. Implement a stateful non-Decision client for factor/action projections, alert/context reads, sequence/cross-category counts, evolution capture, and configured failure injection.
5. Add harness conformance tests: Decision creation is visible through `get_decision`; `write_outcome` updates correct/status; unknown IDs are rejected; non-Decision client state is independent and cannot satisfy Decision lookup.

### Phase 2 — Migrate the nine failing files

1. Replace each local outcome mock setup with the harness fixture.
2. Preserve the semantic test data per file: factor-vector edge cases, RL flags, ServiceNow action/outcome combinations, routing action, L5 phase behavior, and evolution failure injection.
3. Replace raw-query assertions:
   - `test_factor_validation.py`: keep factor-vector error assertions, read the seeded Decision through the store.
   - `test_rl_triage_integration.py` and `test_dual_update_fix.py`: assert `decision["correct"]`, status, optional SOC metadata, RL ledger, and scorer state; use the non-Decision client only for projection/evolution observability.
   - `test_triggered_evolution.py`: assert stateful evolution event/edge records or a dedicated event sink, not literal Cypher formatting.
   - `test_soc_c9b_l5_proof.py` and `test_soc_dk_l5.py`: keep L5 store assertions and seed the route Decision through the harness.
4. Preserve `test_outcome_for_nonexistent_decision_returns_404` as the negative contract test; it must not seed a Decision.

### Phase 3 — Verification

Run in order:

```text
python -m pytest tests/test_soc_triage_harness.py -q --timeout=60
python -m pytest tests/test_dual_update_fix.py tests/test_factor_validation.py tests/test_rl_full_pipeline.py tests/test_rl_triage_integration.py -q --timeout=120
python -m pytest tests/test_servicenow_triage_integration.py tests/test_soc_c9b_l5_proof.py tests/test_soc_dk_l5.py tests/test_triage_routing_actions.py tests/test_triggered_evolution.py -q --timeout=180
python -m pytest tests/ -q --timeout=300
```

Also run the correctness scanner and the SDK/CI contract suites after the production C2 cleanup. The acceptance condition is zero new failures and all 38 formerly failing tests passing without reintroducing raw Decision correctness writes.

## §7 RISK ASSESSMENT

| Risk | Failure mode | Mitigation |
|---|---|---|
| Separate scorer/store instances | Route still returns 404 or writes to a different store | Harness creates exactly one store and one adapter; assert object identity |
| Patching wrong scorer binding | `triage.get_profile_scorer` remains live while test patches `gae_state` | Patch/inject the route dependency at `app/routers/triage.py:34`, or introduce a provider seam |
| Global fixture pollution | RL state, outbox, or Decision records leak between tests | Function-scoped harness, unique IDs, isolated outbox, reset RL state |
| Replacing `FakeNeo4j` globally | Analyze-alert tests lose alert/campaign/referral behavior | Split outcome and analyze clients; retain non-Decision fake APIs (`tests/test_rl_triage_integration.py:389-445`) |
| Query assertions removed too broadly | Evolution/audit behavior becomes untested | Replace with stateful event/edge assertions, not delete coverage |
| InMemory lacks SOC-specific APIs | Campaign/entity behavior is forced into the wrong store | Keep non-Decision client separate; add only narrow test-side context builders |
| Production raw correctness write remains | Tests pass while C2 is still violated | Resolve `triage.py:2322-2335` first and keep scanner coverage |
| Missing Decision negative case disappears | Route silently creates or accepts unknown IDs | Preserve explicit 404 test at `tests/test_triage_routing_actions.py:144-183` |

## §8 NEW TESTS NEEDED

### Positive

- Harness-created Decision is visible to the route’s scorer GraphStore and `write_outcome` sets `correct`, status, and SOC optional properties.
- Correct and incorrect outcomes preserve RL, ServiceNow, routing, and L5 behavior using the same store instance.
- A scorer action creates the expected evolution side effect; a routing action does not.
- Factor-vector validation still rejects missing, malformed, and wrong-length vectors after contract lookup.

### Negative

- Unknown Decision ID returns 404 and does not call audit, learning, ServiceNow, or evolution side effects.
- A Decision present only in the non-Decision client is still treated as absent by the GraphStore contract.
- Raw `SET d.correct` outside `write_outcome` is detected by the scanner, including the current centroid path at `app/routers/triage.py:2322-2335`.
- Incorrect outcomes do not create positive evolution patterns or confirmed ServiceNow incidents.

### Regression

- Existing InMemory adapter/J6 tests remain unchanged and pass (`tests/test_j6_state_capture.py:71-112`, `tests/test_scorer_adapter.py:44-57`).
- Analyze-alert tests continue to use non-Decision alert/campaign state and retain their current query/correlation assertions (`tests/test_rl_triage_integration.py:506-845`).
- C9B conservation-only tests continue to use their stateful health rows (`tests/test_soc_c9b_l5_proof.py:240-250`).
- The audit ledger remains independent and is still asserted separately from GraphStore outcome materialization (`tests/test_triage_outcome_contract.py:62-84`).

## §9 READING LOG

Files read fully for this investigation:

- `gen-ai-roi-demo-v4-v50/backend/tests/conftest.py`
- `gen-ai-roi-demo-v4-v50/backend/app/routers/triage.py`
- `gen-ai-roi-demo-v4-v50/backend/app/domains/soc/scorer_adapter.py`
- `gen-ai-roi-demo-v4-v50/backend/app/services/gae_state.py`
- `gen-ai-roi-demo-v4-v50/backend/app/main.py`
- `gen-ai-roi-demo-v4-v50/backend/app/db/neo4j.py`
- `gen-ai-roi-demo-v4-v50/backend/tests/test_dual_update_fix.py`
- `gen-ai-roi-demo-v4-v50/backend/tests/test_factor_validation.py`
- `gen-ai-roi-demo-v4-v50/backend/tests/test_rl_full_pipeline.py`
- `gen-ai-roi-demo-v4-v50/backend/tests/test_rl_triage_integration.py`
- `gen-ai-roi-demo-v4-v50/backend/tests/test_servicenow_triage_integration.py`
- `gen-ai-roi-demo-v4-v50/backend/tests/test_soc_c9b_l5_proof.py`
- `gen-ai-roi-demo-v4-v50/backend/tests/test_soc_dk_l5.py`
- `gen-ai-roi-demo-v4-v50/backend/tests/test_triage_routing_actions.py`
- `gen-ai-roi-demo-v4-v50/backend/tests/test_triggered_evolution.py`
- `gen-ai-roi-demo-v4-v50/backend/tests/test_j6_state_capture.py`
- `gen-ai-roi-demo-v4-v50/backend/tests/test_soc_learning_live.py`
- `gen-ai-roi-demo-v4-v50/backend/tests/test_scorer_adapter.py`
- `copilot-sdk/copilot_sdk/graph/memory_store.py` (relevant store API scan)

Test command evidence:

- `python -m pytest tests/ -q --timeout=300 --tb=no`: 38 failed, 2,166 passed, 14 skipped.

DOCUMENT_PATH: `gen-ai-roi-demo-v4-v50/backend/docs/soc_test_architecture_v1.md`
FAILING_TESTS: 38
FILES_AFFECTED: 9 failing test files, plus the shared test harness/conftest and the production C2 cleanup seam
TYPE_A_COUNT: 38
TYPE_B_COUNT: 0
TYPE_C_COUNT: 0 whole tests; implementation-coupled assertions require rewrite
TYPE_D_COUNT: 0
MOCK_IS_RULE63_COMPLIANT: NO
RECOMMENDED_APPROACH: One stateful InMemoryGraphStore-backed SOC scorer harness for all Decision authority, with a separate stateful non-Decision client for alerts/campaigns/entities and side-effect observation.
ESTIMATED_EFFORT: 3–5 days, including the remaining production C2 cleanup and full-suite verification
READY_FOR_IMPLEMENTATION: YES, after resolving the residual direct d.correct write identified at app/routers/triage.py:2322-2335
