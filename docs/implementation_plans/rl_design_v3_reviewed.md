# RL Design v3 — Architecture Review and Fine-Tuning

## 1. Executive Summary

**Overall verdict: PASS_WITH_REVISIONS for implementation planning, not direct implementation.** The design is conceptually strong where it frames CI RL as a contextual bandit, keeps `ProfileScorer` as the policy, and separates graded reward from binary conservation quality. The source design explicitly states that this is not deep RL, not an MDP, and not policy-gradient training, and that `q` remains binary rolling accuracy while graded rewards only modulate learning-rate magnitude (docs/implementation_plans/rl_design_v3.md:26, docs/implementation_plans/rl_design_v3.md:30, docs/implementation_plans/rl_design_v3.md:32, docs/implementation_plans/rl_design_v3.md:37).

The strongest parts are the safety boundary around conservation, the explicit refusal to feed graded rewards into `q`, and the referral-veto posterior skip. Those align with live code where conservation currently computes `q` from binary verified outcomes only (backend/app/services/learning_health.py:80, backend/app/services/learning_health.py:82, backend/app/services/learning_health.py:100, backend/app/services/learning_health.py:104) and centroid mutation is currently gated by `LEARNING_ENABLED` in the verified outcome path (backend/app/routers/triage.py:1080, backend/app/routers/triage.py:1097, backend/app/routers/triage.py:1114).

The biggest design risks are live-code compatibility gaps:

- The design proposes `guarded_update(..., eta_weight=...)`, but the live `ProfileScorer.update()` signature has no `eta_weight` parameter (../graph-attention-engine-v50/gae/profile_scorer.py:780, ../graph-attention-engine-v50/gae/profile_scorer.py:787), and `guarded_update()` forwards unknown kwargs directly into `scorer.update()` (backend/app/services/gae_state.py:735, backend/app/services/gae_state.py:754, backend/app/services/gae_state.py:788).
- The design assumes exploration can run after score and before referral, but the live triage path writes the `Decision` node before the ReferralEngine veto block (backend/app/routers/triage.py:247, backend/app/routers/triage.py:252, backend/app/routers/triage.py:265, backend/app/routers/triage.py:467, backend/app/routers/triage.py:511).
- The design's chain-credit query shape does not match the current `TRIGGERED_EVOLUTION` write. Live code stores `factor_snapshot`, `decision_number`, and `action_index` on the `Decision`, not the `EvolutionEvent` (backend/app/routers/triage.py:1267, backend/app/routers/triage.py:1270, backend/app/routers/triage.py:1285, backend/app/routers/triage.py:1288).
- DuckDB and SciPy are design dependencies, not verified direct backend dependencies. The backend requirements file lists FastAPI, Pydantic, Google, Neo4j, async/auth libraries, and editable local packages, but not DuckDB or SciPy (backend/requirements.txt:1, backend/requirements.txt:7, backend/requirements.txt:19, backend/requirements.txt:31).

Implementation go/no-go: **NO-GO for direct coding from `rl_design_v3.md`; GO for phase-by-phase implementation planning using this reviewed document.** Resolve the DESIGN-P1 items in Phase 0 before touching triage.

Key recommendations:

- Keep the contextual-bandit framing and P16 separation.
- Use a durable `RewardLedger` first, before any learning-rate or posterior changes.
- Replace the proposed `eta_weight` API with an explicit, reviewed integration contract: either a GAE `ProfileScorer.update(..., eta_weight=...)` change or a backend-scoped temporary eta multiplier under `acquire_scorer()`.
- Move exploration metadata design into the actual triage order: score, confidence gate, exploration proposal, referral veto, final action, then a single coherent Decision write or post-write `SET`.
- Revise chain credit to query the live `Decision`/relationship fields rather than assuming richer `EvolutionEvent` fields.
- Use stdlib `sqlite3` for the initial posterior store unless a dependency review approves DuckDB.

## 2. Design Intent Restatement

RL Design v3 should be described as **conservation-bounded contextual bandit adaptation around an existing centroid policy**, not as a new RL stack.

- The policy remains `ProfileScorer.score()`. Live triage already computes a factor vector and calls `_scorer.score(f.flatten(), category_index=_cat_idx)` to select an action and confidence (backend/app/routers/triage.py:167, backend/app/routers/triage.py:180, backend/app/routers/triage.py:186, backend/app/routers/triage.py:195).
- `ProfileScorer` remains Level 1 scoring state. Its update equation is centroid pull/push with `eta_eff` and `eta_neg_eff`, not a bandit posterior update (../graph-attention-engine-v50/gae/profile_scorer.py:790, ../graph-attention-engine-v50/gae/profile_scorer.py:793, ../graph-attention-engine-v50/gae/profile_scorer.py:915, ../graph-attention-engine-v50/gae/profile_scorer.py:945).
- Binary conservation quality remains separate. `LearningHealthMonitor._extract_components()` computes `q` from `wu.outcome == 1` over verified history, not from any graded reward (backend/app/services/learning_health.py:89, backend/app/services/learning_health.py:100, backend/app/services/learning_health.py:104).
- Graded rewards should be used for economics, transparency, `eta` magnitude modulation, and posterior accounting only. They must never replace `correct_bool` or `LearningState.update()` binary outcomes.
- Exploration should select occasional alternative actions from the same action space as `ProfileScorer` can score. In SOC, this means `SCORER_ACTIONS` is four actions and `refer_to_analyst` is routing/referral, not a scorer action (backend/app/domains/soc/config.py:45, backend/app/domains/soc/config.py:47, backend/app/domains/soc/config.py:50).
- Conservation-bounded exploration means exploration probability must be zero when the canonical conservation margin is non-positive and must shrink as status approaches AMBER/RED. The live health response exposes `signal`, `theta_min`, and `conservation.headroom`, so a margin can be derived without changing conservation math (backend/app/services/learning_health.py:196, backend/app/services/learning_health.py:199, backend/app/services/learning_health.py:202, backend/app/services/learning_health.py:283).
- P16 separation means the posterior store and reward ledger are Level 2 operational exploration records. They cannot mutate centroids unless `LEARNING_ENABLED` allows the existing learning path to do so (backend/app/domains/soc/config.py:58, backend/app/domains/soc/config.py:61, backend/app/routers/triage.py:1080).

## 3. Live-Code Compatibility Map

| Design element | Intended integration point | Live code evidence | Compatibility | Required design adjustment |
|---|---|---|---|---|
| RewardComputer | Verified outcome path after `correct_bool` is known | The outcome path resolves scorer action/correctness and enters the learning branch at `LEARNING_ENABLED and action_name in SCORER_ACTIONS` (backend/app/routers/triage.py:1080, backend/app/routers/triage.py:1085, backend/app/routers/triage.py:1095). | PARTIAL | Compute `RewardResult` before the `LEARNING_ENABLED` branch so reward/posterior can update even while centroid mutation stays frozen. Do not feed `graded_reward` into `correct_bool`. |
| RewardLedger | New durable append-only reward record | Existing `feedback_base.get_reward_summary()` is in-memory and derives a simple asymmetric reward from `FEEDBACK_GIVEN` (backend/app/framework/feedback_base.py:147, backend/app/framework/feedback_base.py:159, backend/app/framework/feedback_base.py:162). | NEEDS NEW COMPONENT | Define a separate `RewardLedger` schema and do not overload `FEEDBACK_GIVEN` or AgentEvolver `EvolutionEvent` lifecycle records. |
| η modulation | Proposed `guarded_update(..., eta_weight=...)` | `guarded_update()` forwards kwargs to `scorer.update()` (backend/app/services/gae_state.py:735, backend/app/services/gae_state.py:754, backend/app/services/gae_state.py:788), but `ProfileScorer.update()` has no `eta_weight` parameter (../graph-attention-engine-v50/gae/profile_scorer.py:780, ../graph-attention-engine-v50/gae/profile_scorer.py:787). | FAIL until revised | DESIGN-P1: choose either a GAE API change or a backend-scoped temporary eta multiplier under `acquire_scorer()`. Tests must prove original eta values are restored. |
| ExplorationPolicy | Analyze flow after score, before referral | Live scoring produces `selected_action` and confidence (backend/app/routers/triage.py:195, backend/app/routers/triage.py:196), then a confidence gate may route to `refer_to_analyst` (backend/app/routers/triage.py:201, backend/app/routers/triage.py:214). A later ReferralEngine veto can also override to `refer_to_analyst` after the Decision node is already written (backend/app/routers/triage.py:247, backend/app/routers/triage.py:467, backend/app/routers/triage.py:511). | PARTIAL | Exploration must be inserted after `ProfileScorer.score()` and confidence gate, but before the final Decision write or with a post-write `SET` after referral veto. Do not explore into `refer_to_analyst`; referral can veto exploration. |
| referral-veto skip | Posterior update skipped if exploration was vetoed by referral | ReferralEngine veto is independent and wins if rules fire (backend/app/routers/triage.py:467, backend/app/routers/triage.py:470, backend/app/routers/triage.py:511). | PASS conceptually, integration incomplete | Persist `explored=true`, `exploration_vetoed_by_referral=true`, `original_action`, `explored_action`, and `final_action`. Posterior update must require `explored=true` and `exploration_vetoed_by_referral=false`. |
| PosteriorStore | Durable Beta posterior `(category, action)` | Backend requirements do not include DuckDB or SciPy directly (backend/requirements.txt:1, backend/requirements.txt:31). | PARTIAL | Use stdlib `sqlite3` initially; make DuckDB a later dependency decision. Use Python `random.betavariate` or a small adapter rather than requiring SciPy for MVP. |
| CreditAssigner | Outcome path after `TRIGGERED_EVOLUTION` history exists | The live flywheel path creates `EvolutionEvent` plus `TRIGGERED_EVOLUTION`, but action index and factor snapshot are set on `Decision` (backend/app/routers/triage.py:1267, backend/app/routers/triage.py:1278, backend/app/routers/triage.py:1285, backend/app/routers/triage.py:1288). | FAIL until revised | DESIGN-P1: revise chain-credit queries to return `d.action_index`, `d.decision_number`, and `d.factor_snapshot`, not `e.action_index` or `e.factor_snapshot`. |
| TRIGGERED_EVOLUTION chain credit | Chain predecessor lookup | Graph schema recognizes `TRIGGERED_EVOLUTION` as `Decision -> EvolutionEvent` with min_count 0 (backend/app/graph_schema.py:143, backend/app/graph_schema.py:150). | PARTIAL | Chain credit must tolerate absent edges and not assume dense graph. It should be explanatory/ledger-only until enough edges exist. |
| Tab 6 contributing decisions | API/UI surface for chain-credit explanation | The existing visible surface around `TRIGGERED_EVOLUTION` is in RuntimeEvolutionTab's decision/evolution display, not a verified chain-credit/contributing-decisions API (frontend/src/components/tabs/RuntimeEvolutionTab.tsx:1697, frontend/src/components/tabs/RuntimeEvolutionTab.tsx:1706, frontend/src/components/tabs/RuntimeEvolutionTab.tsx:1711). | DESIGN INTENT | Defer Tab 6 chain-credit UI/API until backend ledger and query contracts are stable. |
| domain severity/impact config | SOC and S2P domain configuration | SOC exposes ordered categories/actions and explicitly splits `SCORER_ACTIONS` from full routing actions (backend/app/domains/soc/config.py:45, backend/app/domains/soc/config.py:50, backend/app/domains/soc/config.py:63). Supply-chain exists as `supply_chain`, not `s2p`, and is a smoke-test stub with unimplemented classify/factor/query templates (backend/app/domains/supply_chain/config.py:1, backend/app/domains/supply_chain/config.py:16, backend/app/domains/supply_chain/config.py:31). | PARTIAL | Rename S2P paths in the design to `supply_chain`; treat S2P reward weights as DESIGN INTENT until live domain scoring/outcome paths exist. |

## 4. Conceptual Review

### Contextual Bandit Framing

**PASS.** The design correctly models the problem as contextual bandit exploration around a one-step decision, not a sequential MDP. Live triage computes a context vector, calls `ProfileScorer.score()`, and chooses a single action for that alert (backend/app/routers/triage.py:167, backend/app/routers/triage.py:186, backend/app/routers/triage.py:195). There is no live evidence of multi-step policy gradients or replay buffers.

Recommendation: keep the language strict. Say "contextual bandit overlay" and "posterior over action cells," not "RL agent policy."

### Reward Shaping

**PARTIAL.** Separating `graded_reward` from `binary_outcome` is correct. The live conservation code uses binary `wu.outcome == 1` for q (backend/app/services/learning_health.py:100, backend/app/services/learning_health.py:104), so graded reward can remain external. The design needs to define the exact reward ledger schema before integration because the existing reward summary is in-memory and simplistic (backend/app/framework/feedback_base.py:147, backend/app/framework/feedback_base.py:159, backend/app/framework/feedback_base.py:162).

Recommendation: implement `RewardComputer` as a pure function and `RewardLedger` before adding eta modulation.

### Conservation Separation

**PASS with one revision.** The invariant that `q` remains binary is correct and must be tested. However, the design should define conservation margin as `health["signal"] - health["theta_min"]` or `health["conservation"]["headroom"]` from `LearningHealthMonitor.evaluate()`, because no standalone margin API exists in current code (backend/app/services/learning_health.py:202, backend/app/services/learning_health.py:283, backend/app/services/learning_health.py:287, backend/app/services/learning_health.py:290).

Recommendation: use `conservation.headroom` if present; fall back to `signal - theta_min`; if status is RED/AMBER or margin <= 0, exploration probability is zero.

### Exploration Policy

**PARTIAL.** Thompson sampling with Beta posteriors per `(category, action)` is a reasonable MVP for binary success/failure exploration. It fits the SOC scorer action cells because `SCORER_ACTIONS` is ordered and excludes `refer_to_analyst` (backend/app/domains/soc/config.py:47, backend/app/domains/soc/config.py:50).

The design needs to handle two live referral paths: the confidence gate that changes low-confidence outputs to `refer_to_analyst` (backend/app/routers/triage.py:201, backend/app/routers/triage.py:214), and the independent ReferralEngine veto that can override after the current Decision write (backend/app/routers/triage.py:467, backend/app/routers/triage.py:511).

Recommendation: exploration can only choose among `SCORER_ACTIONS`; it must never override a referral veto.

### Posterior Persistence

**NEEDS REVISION.** Persistence across restart is required, but DuckDB is not currently a backend dependency (backend/requirements.txt:1, backend/requirements.txt:31). Python stdlib `sqlite3` avoids a dependency change and is enough for a small posterior table.

Recommendation: Phase 2 should start with sqlite, schema-versioned, single-writer, fail-open-to-no-exploration on corruption or unavailable DB. DuckDB can be revisited after tests prove value.

### Credit Assignment

**NEEDS REVISION.** Finite-difference factor attribution is safe only if it calls `ProfileScorer.score()` read-only. The score path validates input and computes distances/probabilities without centroid writes in the visible scoring block (../graph-attention-engine-v50/gae/profile_scorer.py:420, ../graph-attention-engine-v50/gae/profile_scorer.py:427, ../graph-attention-engine-v50/gae/profile_scorer.py:438). But chain credit must be ledger/explainability only because the live `TRIGGERED_EVOLUTION` schema does not match the proposed query (backend/app/routers/triage.py:1267, backend/app/routers/triage.py:1285, backend/app/routers/triage.py:1288).

Recommendation: keep `CHAIN_DISCOUNT=0.5` only for explanatory attribution and require `sum(chain_credit) <= 0.5 * direct_reward_abs` per event.

### Domain Portability

**PARTIAL.** SOC is ready for category/action cell posteriors because it has explicit category/action order (backend/app/domains/soc/config.py:45, backend/app/domains/soc/config.py:50, backend/app/domains/soc/config.py:63). Supply-chain is not ready for full RL integration because the config file says several required domain functions are not implemented (backend/app/domains/supply_chain/config.py:16, backend/app/domains/supply_chain/config.py:21).

Recommendation: implement SOC first; keep S2P reward constants as DESIGN INTENT until supply-chain analyze/outcome flows exist.

## 5. Critical Design Invariants

Implementation must preserve these invariants:

1. **Binary q only:** `LearningHealthMonitor._extract_components()` must continue computing `q` from binary `wu.outcome == 1` only (backend/app/services/learning_health.py:100, backend/app/services/learning_health.py:104).
2. **Graded reward never enters conservation:** `graded_reward` must not be written into `LearningState.history.outcome`, `correct_bool`, or any `q` calculation.
3. **Centroid mutation remains gated:** `ProfileScorer.update()` calls must remain under `LEARNING_ENABLED and action_name in SCORER_ACTIONS` unless a later approved design changes learning activation (backend/app/routers/triage.py:1080).
4. **Posterior update is not centroid mutation:** posterior and reward ledger updates may run while `LEARNING_ENABLED=False`; they must not call `ProfileScorer.update()`.
5. **Referral veto wins:** if the confidence gate or ReferralEngine routes to human review, exploration must not force an autonomous action (backend/app/routers/triage.py:201, backend/app/routers/triage.py:467, backend/app/routers/triage.py:511).
6. **Referral-vetoed exploration skip:** posterior updates must skip explored alternatives that were vetoed before execution/verification.
7. **Exploration bounded by conservation:** exploration probability is zero when health is RED/AMBER, margin <= 0, or health cannot be read safely.
8. **No deep RL dependencies:** no policy-gradient library, replay buffer, neural policy, or environment simulator is added.
9. **Credit assignment is non-mutating:** finite-difference factor attribution calls scorer read-only and never calls `guarded_update()` or `ProfileScorer.update()`.
10. **Chain credit is transparent:** direct reward and attributed chain credit are stored separately so economics cannot double-count explanatory attribution.
11. **AGE query safety:** new graph writes use `_S()` or approved serializers for strings, inline safe numerics, no `$params` in AGE paths, and no full-map `SET`.
12. **Persistence failure fail-open:** posterior/ledger persistence failures must not crash triage. Reward loss should be logged; exploration should disable itself until store health recovers.

## 6. Design Gaps and Revisions

| Severity | Gap | Why it matters | Recommended revision |
|---|---|---|---|
| DESIGN-P1 | `eta_weight` API does not exist on `ProfileScorer.update()` | Passing `eta_weight` through `guarded_update()` would raise because kwargs are forwarded to `scorer.update()` and the live signature lacks that argument (backend/app/services/gae_state.py:754, backend/app/services/gae_state.py:788, ../graph-attention-engine-v50/gae/profile_scorer.py:780). | Phase 0 must choose and test one contract: GAE API extension or backend-scoped eta multiplier under `acquire_scorer()`. |
| DESIGN-P1 | Exploration insertion conflicts with current Decision write/referral order | The Decision node is created before the ReferralEngine veto, so exploration metadata and final action can become inconsistent unless the flow is refactored (backend/app/routers/triage.py:247, backend/app/routers/triage.py:265, backend/app/routers/triage.py:467, backend/app/routers/triage.py:511). | Refactor the plan to determine final action before the Decision write, or add an explicit post-referral `SET` with final/exploration fields. |
| DESIGN-P1 | Chain-credit query assumes wrong `TRIGGERED_EVOLUTION` property placement | Live flywheel fields required for attribution are on `Decision`, while the design query expects them on `EvolutionEvent` (backend/app/routers/triage.py:1270, backend/app/routers/triage.py:1285, backend/app/routers/triage.py:1288). | Revise CreditAssigner query to `MATCH (d:Decision)-[r:TRIGGERED_EVOLUTION]->(e:EvolutionEvent)` and read `d.factor_snapshot`, `d.action_index`, `d.decision_number`, plus `r.action/r.category`. |
| DESIGN-P2 | DuckDB dependency not present | Adding DuckDB changes deployment/test surface and violates "no new dependency" unless explicitly approved (backend/requirements.txt:1, backend/requirements.txt:31). | Use sqlite for MVP; make DuckDB a later optional backend. |
| DESIGN-P2 | SciPy Beta sampling not verified in backend dependencies | Requirements do not list SciPy directly (backend/requirements.txt:1, backend/requirements.txt:31). | Use `random.betavariate(alpha, beta)` for Thompson samples or isolate SciPy behind optional adapter. |
| DESIGN-P2 | RewardLedger schema is under-specified | Existing reward summary is in-memory and aggregate-only (backend/app/framework/feedback_base.py:147, backend/app/framework/feedback_base.py:164). | Define durable fields before integration: `decision_id`, `alert_id`, `category`, `action`, `binary_outcome`, `graded_reward`, `eta_weight`, `explored`, `vetoed`, `posterior_updated`, `timestamp_epoch`, `schema_version`. |
| DESIGN-P2 | Posterior reset semantics are not wired to live conservation state | Health status is available from `LearningHealthMonitor.evaluate()` (backend/app/services/learning_health.py:283, backend/app/services/learning_health.py:304), but no posterior reset hook exists. | Reset/lower posteriors only in explicit exploration policy evaluation, not through hidden background mutation. Log reset events in PosteriorStore. |
| DESIGN-P2 | `target_headroom=10.0` lacks unit calibration | `LearningHealthMonitor` returns signal, theta, and headroom, but the design does not validate that a fixed target of 10 has consistent scale across domains (backend/app/services/learning_health.py:283, backend/app/services/learning_health.py:290). | Phase 0 synthetic validation must fit `target_headroom` from live ranges; default to zero exploration if uncalibrated. |
| DESIGN-P2 | Supply-chain/S2P paths are wrong or premature | There is no `backend/app/domains/s2p/config.py`; supply-chain exists but declares scoring/classification/query pieces unimplemented (backend/app/domains/supply_chain/config.py:16, backend/app/domains/supply_chain/config.py:21). | Rename paths to `supply_chain`; mark S2P RL as future until live domain outcome flow exists. |
| DESIGN-P2 | Chain credit can double-count reward | The design does not say whether chain credit contributes to economics or only explainability. | Store `direct_reward` and `attributed_chain_credit` separately; exclude chain credit from q and posterior updates. |
| DESIGN-P2 | Referral skip semantics need both gates | The live system has a confidence gate and an independent ReferralEngine veto (backend/app/routers/triage.py:201, backend/app/routers/triage.py:467). | Treat both as vetoes. Posterior update only if explored action was final non-referral action and outcome was verified. |
| DESIGN-P3 | Existing AE ledger should not be overloaded | AgentEvolver `EvolutionEvent` validates fixed lifecycle event types and artifact types (backend/app/framework/evolution_ledger.py:34, backend/app/framework/evolution_ledger.py:41, backend/app/framework/evolution_ledger.py:56, backend/app/framework/evolution_ledger.py:307). | RewardLedger should be separate from AE ledger; link by IDs only. |
| DESIGN-P3 | Tab 6 chain-credit UI is premature | Existing UI shows `TRIGGERED_EVOLUTION`, not a stable chain-credit surface (frontend/src/components/tabs/RuntimeEvolutionTab.tsx:1697, frontend/src/components/tabs/RuntimeEvolutionTab.tsx:1711). | Defer frontend until backend ledger APIs exist. |

## 7. Fine-Tuned Architecture

### Components

1. **RewardComputer**
   - Pure function: inputs `DecisionOutcomeContext`, domain config, optional analyst metadata.
   - Output: `RewardResult(binary_outcome, graded_reward, eta_weight, components, explanation)`.
   - It must not call `ProfileScorer.update()` or mutate posterior state.

2. **RewardLedger**
   - New append-only durable store.
   - Initial implementation should be sqlite or AGE `RewardEvent` only after query-safety review.
   - It owns reward transparency and replay/backfill support.
   - It is separate from `app.framework.evolution_ledger`, whose event types are fixed for AgentEvolver lifecycle events (backend/app/framework/evolution_ledger.py:34, backend/app/framework/evolution_ledger.py:48).

3. **EtaModulationAdapter**
   - Phase 0 design decision.
   - Preferred conservative path: backend-scoped temporary multiplier under `acquire_scorer()` because live triage already temporarily adjusts `eta_override` under lock and restores it in `finally` (backend/app/routers/triage.py:1104, backend/app/routers/triage.py:1105, backend/app/routers/triage.py:1123).
   - If changing GAE, extend `ProfileScorer.update()` and all tests explicitly; do not rely on unknown kwargs.

4. **PosteriorStore**
   - sqlite table keyed by `(domain, category, action)`.
   - Fields: `alpha`, `beta`, `successes`, `failures`, `last_updated_epoch`, `schema_version`, `disabled_reason`.
   - Failure behavior: if read fails, exploration disabled; if write fails after outcome, log and do not crash.

5. **ExplorationPolicy**
   - Reads current scorer action and confidence.
   - Samples only among domain scorer actions, not full routing/referral actions.
   - Uses conservation health from `LearningHealthMonitor.evaluate()` and sets `exploration_rate=0` when status is RED/AMBER, pre-activation, or margin <= 0.
   - Returns `ExplorationDecision(original_action, explored_action, final_candidate_action, explored, reason, posterior_snapshot)`.

6. **CreditAssigner**
   - Pure/read-only attribution.
   - Finite-difference factor attribution calls `score()` only.
   - Chain credit reads live `Decision` and relationship fields and writes only RewardLedger explanation rows.

### Data Flow

Analyze:

1. Compute factors.
2. Call `ProfileScorer.score()`.
3. Apply confidence gate.
4. Call `ExplorationPolicy.propose()` only if candidate action is in `SCORER_ACTIONS`.
5. Apply ReferralEngine veto.
6. Write a Decision node containing both final action and exploration metadata.
7. Never let exploration override referral to human review.

Outcome:

1. Read existing Decision node and final action.
2. Compute `RewardResult`.
3. Append RewardLedger row.
4. If explored and not referral-vetoed, update posterior from `binary_outcome`.
5. If `LEARNING_ENABLED` and action is a scorer action, call guarded centroid update with approved eta integration.
6. If correct, keep the existing `TRIGGERED_EVOLUTION` flywheel path and add chain-credit explanation asynchronously/non-blocking.

### State Ownership

- `ProfileScorer`: owns centroids and scoring policy.
- `LearningState`: owns binary verified history and conservation q.
- `RewardLedger`: owns graded rewards and reward explanations.
- `PosteriorStore`: owns exploration posterior parameters.
- AgentEvolver ledger: owns operational artifact lifecycle only.

### Failure Behavior

- Reward computation errors: log, write no reward, continue existing outcome path.
- RewardLedger write errors: log warning, do not block triage outcome.
- PosteriorStore read errors: disable exploration for request.
- PosteriorStore write errors: keep reward ledger row with `posterior_update_failed=true`.
- CreditAssigner errors: log only; never block outcome response.
- Conservation health read errors: exploration disabled.

### Feature Flags

- `RL_REWARD_LEDGER_ENABLED`: defaults false until Phase 1 tests pass.
- `RL_ETA_MODULATION_ENABLED`: defaults false until Phase 0 eta contract is approved.
- `RL_EXPLORATION_ENABLED`: defaults false until PosteriorStore and conservation gate tests pass.
- `RL_CHAIN_CREDIT_ENABLED`: defaults false until schema/query review passes.
- `RL_FORCE_NO_EXPLORE_ON_PRE_ACTIVATION`: defaults true because Task A can return CALIBRATING/pre-activation when learning is disabled.

### Reset Semantics

- Demo reset must clear in-memory posterior cache and optionally sqlite posterior rows if operator chooses a "reset RL exploration" action.
- State reset must not delete RewardLedger by default; use explicit admin maintenance for reward-ledger truncation.
- AMBER/RED response should dampen exploration immediately by setting rate zero; posterior reset to `(2,2)` should be an explicit store operation with audit/logging, not hidden in health polling.

### Observability

- Log exploration proposals, referral vetoes, posterior updates/skips, eta weights, and RewardLedger append failures.
- Add non-mutating debug endpoint only after backend services are stable: reward summary, posterior summary, last N reward events, exploration disabled reason.

## 8. Revised Implementation Sequence

| Phase | Scope | Allowed files | Exit criteria | Tests | Review model |
|---|---|---|---|---|---|
| Phase 0 | Validation gates and eta contract decision | Documentation only, then targeted scorer/adapter tests in a later prompt | Decide GAE API change vs backend adapter; synthetic bandit validation passes; no triage edits | Eta contract tests, synthetic offline simulation, no-conservation-regression tests | GPT-5.5 review required |
| Phase 1 | RewardComputer / RewardLedger | New `backend/app/services/rl_engine.py`, new ledger module/test only | Pure reward computation works; durable append/read works; no triage integration | Reward formulas, binary separation, ledger schema, failure handling, no dependency change | GPT-5.5 review required |
| Phase 2 | PosteriorStore / ExplorationPolicy | New posterior store module/test only | sqlite persistence round-trip; exploration disabled safely on bad health/store failures | Thompson sampling, referral-veto skip function, conservation margin zero-rate, restart persistence | GPT-5.5 review required |
| Phase 3 | CreditAssigner | New credit module/test only | Read-only factor attribution and live-schema chain query are correct | Score non-mutation, query safety, chain discount bound, missing edge tolerance | GPT-5.5 review required |
| Phase 4 | Triage integration | `backend/app/routers/triage.py` plus tests only after Phases 1-3 pass | Reward ledger and posterior update run on verified outcomes; centroid mutation remains gated; exploration metadata is coherent | Analyze exploration, outcome reward, referral veto, LEARNING_ENABLED false, eta adapter, AGE query safety | GPT-5.5 review required |
| Phase 5 | APIs / Tab visibility | Backend read-only APIs, then frontend only if needed | Reward/posterior summaries available without mutation; Tab 6 chain-credit deferred unless API stable | API contract, frontend smoke/build, no live graph mutation | GPT-5.5 review recommended |
| Phase 6 | Retroactive grading / synthetic bandit validation | Support scripts/tests only | Retroactive graded reward correlates with binary q at approved threshold; no writes without explicit apply | dry-run/apply separation, correlation thresholds, reproducibility, rollback plan | GPT-5.5 review required |

## 9. Expanded Test Plan

### RewardComputer

- `test_reward_computer_returns_binary_and_graded`: verifies both fields exist and binary is only derived from correctness.
- `test_graded_reward_does_not_change_binary_outcome`: high/low severity changes graded reward but not binary outcome.
- `test_eta_weight_clip_bounds`: asserts `[0.1, 3.0]` or revised bounds.
- `test_override_learning_weight_is_conservative`: override/incorrect paths do not exceed approved eta cap.
- `test_reference_reward_bootstrap_soc`: validates SOC reference reward constants against deterministic fixtures.
- `test_reward_components_explain_formula`: output includes severity, impact, analyst correction, and final clipping.

### Conservation Separation

- `test_learning_health_q_uses_binary_history_only`: inserts fake graded values and proves `q` still uses `outcome == 1`.
- `test_reward_ledger_not_used_by_learning_health`: monkeypatch RewardLedger to fail and prove health evaluation unaffected.
- `test_pre_activation_disables_exploration`: CALIBRATING/pre-activation health yields zero exploration.

### Eta Modulation

- `test_eta_contract_rejects_unknown_kwarg_before_adapter`: documents current incompatibility if GAE API is not changed.
- `test_scoped_eta_multiplier_restores_eta`: if adapter chosen, original `eta`, `eta_neg`, and `eta_override` restored after update.
- `test_eta_modulation_under_acquire_scorer_lock`: prevents concurrent leakage.
- `test_centroid_mutation_still_requires_learning_enabled`: reward and posterior update can run while centroid update does not.

### PosteriorStore / ExplorationPolicy

- `test_posterior_sqlite_round_trip`.
- `test_posterior_store_corrupt_disables_exploration`.
- `test_thompson_sampling_uses_category_action_cell`.
- `test_no_exploration_when_margin_non_positive`.
- `test_no_exploration_on_red_or_amber`.
- `test_referral_vetoed_exploration_does_not_update_posterior`.
- `test_verified_non_vetoed_exploration_updates_posterior`.
- `test_boundary_no_scorer_action_no_exploration` for `refer_to_analyst`.
- `test_posterior_reset_on_red_is_explicit_and_logged`.

### CreditAssigner

- `test_factor_attribution_calls_score_only`.
- `test_factor_attribution_does_not_mutate_mu_counts_or_decision_count`.
- `test_chain_credit_query_uses_decision_fields`.
- `test_chain_credit_missing_edges_returns_empty`.
- `test_chain_discount_sum_lte_half_direct_reward`.
- `test_chain_credit_separate_from_direct_reward`.
- `test_age_query_safety_for_chain_credit`.

### Triage Integration

- `test_analyze_records_exploration_metadata`.
- `test_referral_veto_final_action_human_review_and_posterior_skip`.
- `test_decision_node_final_action_matches_response`.
- `test_outcome_reward_update_runs_when_learning_disabled`.
- `test_centroid_update_does_not_run_when_learning_disabled`.
- `test_existing_triggerevolution_path_unchanged_for_correct_scorer_actions`.
- `test_reward_failure_does_not_crash_outcome`.
- `test_posterior_write_failure_does_not_crash_outcome`.

### Persistence / Startup / Reset

- `test_posterior_store_initializes_on_startup_without_mutating_graph`.
- `test_restart_preserves_posteriors`.
- `test_reset_clears_in_memory_cache_but_not_reward_ledger_by_default`.
- `test_feature_flag_off_preserves_current_behavior`.

### Retroactive Grading

- `test_retro_grading_dry_run_no_writes`.
- `test_retro_grading_correlation_pass_threshold`.
- `test_retro_grading_warning_floor`.
- `test_retro_grading_rejects_low_correlation`.
- `test_retro_grading_reproducible`.

### API/UI Visibility

- `test_reward_summary_api_read_only`.
- `test_posterior_summary_api_redacts_internal_paths`.
- `test_tab6_chain_credit_contract_only_after_backend_api`.

## 10. Implementation Prompt Guidance

Split future Codex prompts by phase. Do not ask one prompt to implement triage integration, persistence, credit assignment, and frontend visibility together.

Recommended prompt sequence:

1. **Prompt RL-0:** finalize eta contract and write an implementation sub-plan. Stop if it requires external GAE changes.
2. **Prompt RL-1:** implement pure `RewardComputer` and ledger tests only. No triage edits.
3. **Prompt RL-2:** implement sqlite `PosteriorStore` and pure `ExplorationPolicy`. No triage edits.
4. **Prompt RL-3:** implement `CreditAssigner` read-only attribution. No triage edits.
5. **Prompt RL-4:** integrate reward/posterior/exploration into triage behind feature flags. This requires GPT-5.5 review before merge.
6. **Prompt RL-5:** add read-only observability APIs.
7. **Prompt RL-6:** add frontend/Tab 6 surfaces only after API contracts are stable.

Stop conditions:

- Any proposed change feeds graded reward into `LearningHealthMonitor.q`.
- Any exploration path overrides referral/human-review safety.
- Any posterior update occurs without verified outcome.
- Any unknown kwarg is passed into `ProfileScorer.update()`.
- Any new dependency is needed without explicit dependency-review approval.
- Any AGE write uses unsafe string interpolation without `_S()` or approved serialization.
- Any implementation prompt needs to edit both backend triage and frontend UI in the same phase.

## 11. Open Questions / Human Decisions

1. **Eta integration contract:** Should the project change the external GAE `ProfileScorer.update()` API to accept `eta_weight`, or should the backend use a scoped temporary eta multiplier under `acquire_scorer()`?
2. **Persistence backend:** Is sqlite acceptable for the MVP posterior store, or is DuckDB required despite a dependency change?
3. **Exploration in demo/pre-activation:** Should exploration be completely disabled while `LEARNING_ENABLED=False`, or should posterior-only exploration proposals be logged but never acted on? The source design says reward/exploration update regardless of `LEARNING_ENABLED` (docs/implementation_plans/rl_design_v3.md:64, docs/implementation_plans/rl_design_v3.md:668), but current demo pre-activation semantics may argue for no live action exploration.
4. **Action-space scope:** Should exploration ever choose `monitor`/`suppress` when the current routing zone would be human review, or should it only choose among autonomous-safe actions above a confidence floor?
5. **S2P timing:** Should supply-chain/S2P remain in design docs only until the `supply_chain` domain implements factor computation and query templates?

## Reading Log

- `CLAUDE.md`: lines 1-80.
- `docs/implementation_plans/rl_design_v3.md`: lines 1-894.
- `backend/app/routers/triage.py`: lines 111-638, 865-1360, plus cited ranges 167-225, 247-270, 467-515, 1080-1130, 1254-1305.
- `backend/app/services/gae_state.py`: lines 42-55, 303-320, 735-790.
- `../graph-attention-engine-v50/gae/profile_scorer.py`: lines 160-295, 342-370, 420-511, 591-681, 703-749, 780-824, 915-1004.
- `backend/app/services/learning_health.py`: lines 1-43, 80-123, 190-304, 310-330.
- `backend/app/framework/feedback_base.py`: lines 1-175.
- `backend/app/db/neo4j.py`: lines 55-120, 162-218, 234-271, 289-345.
- `backend/app/framework/evolution_ledger.py`: lines 1-180, 302-362.
- `backend/app/graph_schema.py`: lines 80-165.
- `backend/app/domains/soc/config.py`: lines 31-70, 632-697, 773-856.
- `backend/app/domains/supply_chain/config.py`: lines 1-180.
- `backend/app/services/variant_generator.py`: lines 760-810.
- `backend/app/services/shadow_runner.py`: lines 1-65, 180-235.
- `backend/app/services/promotion_gate.py`: lines 1-115, 145-205.
- `backend/app/routers/soc.py`: lines 3090-3130 and search hits for `TRIGGERED_EVOLUTION`.
- `frontend/src/components/tabs/RuntimeEvolutionTab.tsx`: lines 1688-1728 and search hits for `TRIGGERED_EVOLUTION`.
- `backend/requirements.txt`: lines 1-31.
- Discovery commands: `Test-Path backend/pyproject.toml` returned `False`; `Get-ChildItem backend/app/domains -Directory` returned `soc` and `supply_chain`; `Test-Path backend/app/domains/s2p/config.py` and `config_v2.py` returned `False`.
