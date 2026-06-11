# Package 5E Plan: Benchmark-Gated Route Policy Architecture

## 1. Executive Summary

Package 5D is closed. The hardened runner completed `false_baseline`, `true_compare`, and `proof_250` with final status `PASS`, route parity `PASS`, proof status `PASS`, zero shadow side effects, and no buyer-facing performance claim.

Package 5E is planning only. The current route remains canonical by default. Pipeline-served behavior must not be treated as a simple boolean switch and must only be selected through an explicit route policy after correctness, side-effect, proof, latency, scale, and rollback gates pass. Different copilots may end up with different route modes. Full route adoption remains blocked.

## 2. Current Architecture Inventory

SOC canonical analyze route:

- `backend/app/routers/triage.py`
- `analyze_alert()` at `POST /api/alert/analyze`
- Current path loads alert, loads security context, computes factors/scoring/referral/composite gate, writes a `Decision` node, builds the response, and then optionally attaches shadow diagnostics.

SOC runtime flags:

- `triage._soc_entity_cache_enabled()` reads `USE_ENTITY_CACHE`, default false.
- `triage._soc_decision_pipeline_shadow_enabled()` reads `USE_SOC_DECISION_PIPELINE_SHADOW`, default false.
- `USE_SOC_DECISION_PIPELINE_SHADOW` currently controls diagnostics only. It must not become the route selection mechanism for served output.

SOC shadow path:

- `triage._soc_maybe_attach_decision_pipeline_shadow(response, alert_data, context)` runs after canonical response assembly.
- It imports `run_soc_decision_pipeline_shadow()` from `backend/app/services/soc_domain_profile.py`.
- Shadow failures are fail-safe: canonical output is preserved and `_diagnostics.soc_decision_pipeline_shadow.status=shadow_failed` is attached when shadow is enabled.

DecisionPipeline entrypoint:

- Shared pipeline: `ci-platform/ci_platform/copilot_core/pipeline.py`
- `DecisionPipeline(profile, tasks=...).run(PipelineInput(...))`
- `DomainProfile` hooks: `load_subject`, `load_context`, `compute_decision`, `apply_gates`, `persist_decision`, `phase4_tasks`.
- `PipelineResult` freezes response-critical result fields.

SOC DomainProfile:

- `backend/app/services/soc_domain_profile.py`
- `SOCDomainProfile` implements the shared hooks for side-by-side/shadow use.
- `run_soc_decision_pipeline_shadow()` runs the pipeline with `persistence_strategy=shadow_noop`.
- `compare_soc_route_and_pipeline_outputs()` compares decision-critical route fields.
- `SOC_SHADOW_COMPARISON_FIELDS` covers recommendation action/confidence/routing zone, GAE factor vector/names/probabilities/routing metadata, referral, referral_debug, composite_gate, and decision metadata.

Side-effect boundaries:

- Canonical analyze writes `Decision` nodes in `triage.analyze_alert()` around the `decision_node_and_edge_write` block.
- Shadow mode reports `decision_writes=0`, `outcome_writes=0`, `proof_writes=0`, `counter_updates=0`, `graph_mutations=0`.
- `SOCDomainProfile.persist_decision()` is currently a side-by-side no-write persistence representation, not production graph persistence.
- Phase 4 remains non-decision-critical. `BackgroundTaskManager` is in `ci-platform/ci_platform/copilot_core/background.py`.

Proof/outcome path:

- Outcome route: `triage.report_decision_outcome()` at `POST /api/alert/outcome`.
- Outcome path mutates graph feedback, updates live scorer state, and performs DK/Welford logic including `_update_dk_welford_tracker(...)`.
- SOC proof runner: `scripts/diagnostics/run_soc_diag_f.py`.
- Route validation runner: `scripts/diagnostics/run_soc_route_validation.py`.
- Proof artifacts reviewed for 5D: `scratch/temp/route_validation_250_summary.json` and `docs/implementation_plans/soc_c9b_diag_f_runner_P5DRUNNER250.json`.

Runner/proof validation:

- `run_soc_route_validation.py` supports false/true/proof phases, strict contract validation, deterministic seeding, workload capture, shadow/entity_cache/generic compare profiles, and strict proof invariants.
- 5D proof evidence: `EXTERNAL_DIAGNOSTIC_F_PASS`, `valid_outcomes=250`, `seed_failures=0`, `l5_centroid=1`, `shaped_by=1`, `l5_dk_weight=1`, `dk_welford_rows=1`, `n_decisions_used=250`.
- P3 observability item: proof artifacts do not expose an explicit `graph_truth_proof_authority_preserved` boolean.

Relevant tests:

- `backend/tests/test_soc_domain_profile_pipeline.py`
- `backend/tests/test_soc_route_validation_runner.py`
- `backend/tests/test_soc_entity_cache_route_readiness.py`
- `ci-platform/tests/test_decision_pipeline.py`
- `ci-platform/tests/test_background_task_manager.py`

Other copilot structures inspected:

- S2P/Supply Chain domain config: `backend/app/domains/supply_chain/config.py`.
- S2P preview UI: `frontend/src/components/tabs/S2PPreviewTab.tsx`, using `/api/s2p/preview/queue`, `/api/s2p/preview/conservation`, and `/api/s2p/preview/suppliers`.
- Shared domain framework: `backend/app/domains/base.py`, `backend/app/core/domain_registry.py`.
- Framework/scorer routes: `backend/app/routers/framework_router.py`, `backend/app/routers/evaluation.py`, `backend/app/routers/judgment.py`, `backend/app/routers/gae.py`.
- Trading/Purchasing/DataOps route-specific implementations were not present as concrete backend route modules in this repo snapshot; treat them as future copilot policy targets, not current implementation targets.

## 3. Route Policy Model

Package 5E should introduce a centralized route policy abstraction, not scattered route conditionals.

Conceptual components:

- `RoutePolicyResolver`: the only component allowed to read route-mode config/env and turn it into an execution decision. It resolves domain/copilot, route name, request-safe context, environment/config, and benchmark-gate metadata into a `RouteDecision`.
- `RouteExecutionMode`: typed enum values described below.
- `RoutePolicy`: per-copilot config, default mode, allowed modes, required gates, fallback policy, and diagnostics requirements.
- `RouteDecision`: selected mode, served-output source, diagnostic-evaluation source, reason, config source, fallback state, benchmark gate status, policy version, and audit metadata.
- Route decision diagnostics: safe `_diagnostics.route_policy` data for enabled diagnostic modes.
- Route adapter/facade boundary: route handlers ask for one `RouteDecision` and execute through a small policy adapter. Route handlers should not contain ad hoc policy branching beyond invoking the adapter.
- Benchmark gate metadata: mode eligibility, last validated artifact IDs, workload coverage, latency/tail thresholds, proof requirements, side-effect requirements, and approval state.

Route execution modes:

- `canonical_only`: canonical route output is served. Pipeline is not evaluated for served output. Writes are exactly current canonical writes. No fallback is needed. Diagnostics must identify canonical policy selection when diagnostics are enabled. This is the default and requires no promotion gate.
- `shadow_only`: canonical route output is served. Pipeline may be evaluated diagnostically after canonical output assembly. Shadow writes must be zero. Shadow failure must preserve canonical output and surface diagnostics. Required gates: shadow parity, zero side effects, fail-safe diagnostics, and acceptable shadow overhead.
- `pipeline_read_only`: canonical route output is served. Pipeline output may be exposed only in internal/read-only diagnostics or test artifacts. Pipeline writes must be zero unless separately approved for a non-served proof experiment. Required gates: shadow gates plus serialization/freeze safety and diagnostic sensitivity review.
- `pipeline_served`: pipeline output is served. Canonical output may still be computed for comparison during a guarded transition, but it is not the user-visible source. Writes must be explicitly mapped to canonical semantics and tested for equivalence. Required gates: explicit approval package, proof/readback invariants, parity, side-effect equivalence, latency/tail/scale gates, rollback drill, and no hidden fallback.
- `hybrid_fast_path`: future mode where low-risk cases use canonical fast path and selected cases use pipeline path. Served output varies by policy decision. Required gates: separate design review, case classifier correctness, per-case diagnostics, fallback safety, and workload-specific latency/tail proof.
- `fallback_to_canonical`: pipeline is attempted, but canonical output is served when the policy detects an approved fallback condition. Fallback must be visible and cannot be counted as parity pass or served-pipeline success. Required gates: explicit fallback taxonomy, alerting/diagnostics, no fake pass, and rollback validation.
- `disabled`: route unavailable or explicitly off. No canonical or pipeline output is served. This must fail closed with a clear internal error/diagnostic and must not silently fall back to a different mode.

Guardrails:

- Served output is never selected by `USE_SOC_DECISION_PIPELINE_SHADOW` alone.
- Any non-canonical served path must record route policy decision diagnostics.
- Any fallback must surface the fallback reason and cannot count as parity pass.
- Decision/proof/counter/graph-write semantics cannot move across modes without explicit tests.
- Invalid or unsupported modes fail closed in implementation/test contexts. User-facing route behavior must not silently upgrade to a served pipeline path.
- No copilot inherits another copilot's route mode automatically.

Anti-sprawl rule:

- No per-route ad hoc env checks except inside `RoutePolicyResolver` or its config loader.
- No scattered `if SOC_ROUTE_MODE == ...` branches across route handlers.
- Route handlers receive one `RouteDecision` and call a policy adapter/facade that owns mode-specific orchestration.
- Unit tests must cover resolver behavior, route adapter behavior, and the absence of served-output changes when diagnostic-only flags are enabled.

## 4. Flag and Config Model

Recommended 5E implementation start:

- `SOC_ROUTE_MODE=canonical_only|shadow_only|pipeline_read_only|pipeline_served|hybrid_fast_path|fallback_to_canonical|disabled`
- Default: absent or empty means `canonical_only`.
- Invalid value: fail closed with a clear internal error/diagnostic in tests and non-served validation paths; do not silently choose a served mode. For production route contexts, the resolver must either fail closed before serving or explicitly return `canonical_only` with an error diagnostic only if that fallback policy was approved and tested.
- 5E may start with `SOC_ROUTE_MODE` for narrow SOC scope, but the API shape must preserve migration to per-copilot policy without changing route handlers again.

Future multi-copilot model:

- `COPILOT_ROUTE_POLICY=soc:canonical_only,trading:canonical_only,purchasing:canonical_only,dataops:canonical_only,s2p:canonical_only`
- Longer term: config-file based policy with per-copilot allowed modes, gate thresholds, and fallback behavior.
- Future config should include policy version, approved modes, required benchmark artifacts, per-mode thresholds, and rollback mode.

Interactions:

- `USE_SOC_DECISION_PIPELINE_SHADOW` remains diagnostic-only unless `SOC_ROUTE_MODE` explicitly requires shadow behavior.
- Shadow flag alone must never change served output.
- `USE_ENTITY_CACHE` remains independent and default false.
- Materialized counters remain non-adopted by routes.
- All copilots default to `canonical_only`.

## 5. Per-Copilot Capability Matrix

Different copilots may end in different route modes. SOC is the first application only; its eventual mode must not become the default for Trading, Purchasing, DataOps, S2P, or future copilots.

| Copilot | Constraints | Likely initial mode | Required gates before promotion |
| --- | --- | --- | --- |
| SOC | Graph read/write dependence, Decision writes in analyze, separate Outcome proof path, strict DK/L5/Welford proof authority, high auditability need | `canonical_only`, then `shadow_only`; may remain shadow/read-only if overhead or proof risk fails gates | 5D-style route parity, zero shadow side effects, proof_250 pass, latency/tail/concurrency gates, rollback proof |
| Trading | Likely high latency sensitivity and risk-sensitive action semantics; route implementation not present in this repo snapshot | `canonical_only`; possible future `hybrid_fast_path` only after separate design | Domain profile inventory, synthetic and live-like parity, very tight tail latency, failure/fallback safety |
| Purchasing | May overlap S2P/supply-chain approval semantics; monetary approval side effects raise risk | `canonical_only` | Policy approval boundaries, stricter side-effect controls, no unintended purchase/order writes, audit gates, threshold-specific benchmarks |
| DataOps | Likely batch/operational workflows; may tolerate latency but needs determinism and reproducibility | `canonical_only` | Throughput/replay scale validation, job idempotence, failure replay semantics, deterministic batch comparisons |
| S2P | Preview must remain read-only facade over live learned scorer/model state where recommendations are expected; avoid isolated in-memory scorer drift | `canonical_only` / read-only preview policy | Live learned scorer/model-state consistency, conservation constraints, preview/read-only guarantees, no fake isolated scorer behavior |

## 6. Benchmark-Gated Promotion Criteria

Route behavior is decided by measured gates and operational requirements, not architectural preference.

Required gates before promotion beyond `canonical_only` / `shadow_only`:

- Correctness parity across decision-critical fields.
- Side effects zero where expected.
- Proof/readback invariants preserved.
- No hidden fallback or fake success.
- Average latency within per-copilot threshold.
- p95/p99 and max latency acceptable.
- Concurrency behavior acceptable.
- Scale test acceptable.
- Failure mode and rollback acceptable.
- Per-copilot constraints satisfied.

Initial SOC thresholds should be proposed before implementation and reviewed. Do not use one global threshold across copilots.

Promotion ladder:

1. `canonical_only`: default for every copilot.
2. `shadow_only`: allowed after side-effect-zero and fail-safe diagnostics tests.
3. `pipeline_read_only`: allowed after shadow parity, diagnostic safety, and benchmark evidence show it is useful without serving pipeline output.
4. `pipeline_served`: blocked until a separate approval package proves correctness, proof authority, side-effect equivalence, latency/tail/scale gates, and rollback.
5. `hybrid_fast_path` / `fallback_to_canonical`: blocked until separate design review because served output may vary by case or failure mode.

Route behavior is promoted only by measured gates and operational requirements. Pipeline-served behavior is not the natural destination; staying in `canonical_only`, `shadow_only`, or `pipeline_read_only` is acceptable when benchmark or risk gates do not justify serving pipeline output.

## 7. Safety and Boundary Rules

Hard invariants:

- Analyze route must not write proof/outcome artifacts unless current canonical semantics already do so and tests prove equivalence.
- Route path must not mutate counters unless current canonical path already does so and tests prove equivalence.
- Shadow diagnostics must remain side-effect zero.
- Proof path remains authoritative for L5/DK/Welford readback.
- AGE graph truth remains authoritative.
- No fallback should fake pass.
- No exception swallowing without surfaced diagnostics.
- Route policy decision must be observable in diagnostics.
- Materialized counters remain non-adopted unless a separate counter adoption package proves equivalence.
- EntityCache remains separately controlled and default off; EntityCache performance cannot be bundled into route-policy promotion.
- Pipeline diagnostics must not expose sensitive alert, user, asset, graph, or security-context payload beyond fields already present in current route output.
- Served-output source, fallback state, and gate status must be observable for every non-default mode.

## 8. Required Implementation Slices for Later Package

Do not implement these in this planning package.

- 5E-A: route policy inventory and `RoutePolicyResolver` skeleton.
- 5E-B: `SOC_ROUTE_MODE` default-off wiring with `canonical_only` and `shadow_only` only.
- 5E-C: route decision diagnostics/logging.
- 5E-D: SOC unit tests for `canonical_only` and `shadow_only`.
- 5E-E: `pipeline_read_only` / `pipeline_served` guarded path only if explicitly approved.
- 5E-F: route validation runner extensions for route mode config and benchmark gates.
- 5E-G: GPT-5.5 post-code review.
- 5E-P3: add explicit `graph_truth_proof_authority_preserved` field to proof artifacts.

## 9. Testing Plan

Add or update tests:

- `backend/tests/test_soc_route_policy.py`
- `backend/tests/test_soc_domain_profile_pipeline.py`
- `backend/tests/test_soc_route_validation_runner.py`
- `backend/tests/test_soc_entity_cache_route_readiness.py`
- `ci-platform/tests/test_decision_pipeline.py` only if shared interfaces change.

Required cases:

- Default absent route mode is `canonical_only`.
- Invalid route mode fails closed or surfaces clear error.
- `canonical_only` preserves current route output and does not run pipeline.
- `shadow_only` serves canonical output and keeps shadow side effects zero.
- `pipeline_read_only` does not serve pipeline output.
- `pipeline_served` cannot be enabled without explicit policy and gate metadata.
- Shadow flag alone does not change served output.
- Route decision diagnostics include selected mode and reason.
- Route decision diagnostics include gate status, fallback state, policy source, and served-output source.
- Proof/outcome path unchanged.
- Strict contract remains required.
- EntityCache remains off unless explicitly enabled.
- Materialized counters are not route-adopted.
- Per-copilot default policy is `canonical_only`.
- No copilot inherits SOC's mode automatically.
- S2P live-state preview constraint preserved in future policy planning.
- Negative tests for bad flags, invalid route-selection state, and forbidden mode transitions.
- Resolver tests prove env/config reads are centralized and route handlers do not perform ad hoc route-mode checks.

## 10. Live Validation Plan

Future validation sequence, not to be run during planning:

- Runner with `SOC_ROUTE_MODE=canonical_only`.
- Runner with `SOC_ROUTE_MODE=shadow_only`.
- Runner with `SOC_ROUTE_MODE=pipeline_read_only` if implemented.
- Runner with `SOC_ROUTE_MODE=pipeline_served` only if explicitly approved.
- `proof_250` for any served route mode.
- Compare profile must confirm parity or report exact deltas.
- Performance ledger must be updated per mode.
- Scale/concurrency validation must be added before route promotion.
- Workload-specific latency must be reviewed for `unique_once`, `repeat_same`, `mixed_reuse`, and proof aggregate runs.
- Any fallback must be reported as fallback, not as parity success.
- Buyer-facing claim remains NO unless separately approved.

## 11. Performance and Scale Gates

Carry forward:

- P2E baseline: avg analyze 0.193s at 250 outcomes, warm_fallback.
- P3G-D: avg analyze 0.202s, max 0.571s, avg outcome 0.440s; hits=0, misses=250, loads=250.
- P3H: EntityCache correct but current route wiring is not reliable speedup.
- 5D-A: unique_once 0.384314, repeat_same 0.169158, mixed_reuse 0.134437.
- 5D-B: unique_once 0.364990, repeat_same 0.356329, mixed_reuse 0.218911; shadow overhead exists but parity passed.
- 5D runner proof: avg analyze 0.169s, max analyze 0.476s, avg outcome 0.228s.
- Buyer-facing claim allowed: NO.

Future gates:

- Average latency threshold per copilot and mode, defined before promotion.
- p95/p99 threshold when measurable.
- Max latency threshold.
- Throughput/concurrency threshold.
- Graph read/write overhead threshold.
- Scale/replay threshold for batch or DataOps-like workflows.
- No unexplained latency regression.
- No correctness regression.
- Tail latency and concurrency failures block promotion even if average latency passes.
- Faster proof aggregate metrics do not automatically approve route adoption.
- Shadow overhead must be evaluated per workload and cannot be hidden by a favorable aggregate proof metric.
- SOC's observed shadow overhead in repeat/mixed workloads remains a promotion concern even though 5D parity passed.

## 12. Rollback Plan

- Set route mode back to `canonical_only`.
- Shadow diagnostics can remain independently enabled for diagnosis.
- No data migration is required for default-off route policy.
- No graph reset is required.
- No destructive cleanup is required.
- Route decision diagnostics must confirm rollback.

## 13. Risks and Open Questions

- P3: missing explicit `graph_truth_proof_authority_preserved` boolean in proof artifacts. This does not block 5E planning, but broader route adoption should harden this observability before approving served pipeline output.
- Route mode interaction with the existing shadow flag must be kept simple and explicit.
- Per-copilot policy complexity could grow; central resolver is required.
- Avoid scattered conditionals across route handlers.
- Runner-F3 addressed port lifecycle risk, but operational lifecycle remains important.
- AGE readback observability should improve.
- Route-level performance may need both workload comparison and proof aggregate comparison.
- SOC should remain the only 5E implementation target unless SDK/generalization is separately approved.
- `pipeline_served` should likely require a separate approval package after the policy framework lands.

## 14. Explicit Non-Goals

- Full route adoption.
- Buyer-facing performance claim.
- EntityCache adoption.
- Materialized counter adoption.
- Proof criteria changes.
- Route default-on changes.
- UI/product polish.
- Multi-copilot implementation in 5E unless separately approved.
- Served pipeline route without a separate approval package and benchmark gates.

## 15. Go/No-Go Checklist Before Implementation

- 5D closure artifacts reviewed and accepted.
- `SOC_ROUTE_MODE` semantics approved.
- Route policy default is `canonical_only`.
- Policy resolver design reviewed.
- `RouteDecision` schema reviewed.
- Invalid config and fail-closed behavior approved.
- Proof/counter/graph-write boundaries documented in target files.
- Tests listed above approved.
- Live validation plan approved.
- Performance thresholds drafted for SOC.
- Per-workload overhead thresholds drafted for SOC.
- Rollback behavior approved.
- Explicit agreement that `pipeline_served`, `hybrid_fast_path`, and `fallback_to_canonical` remain out of scope for initial implementation.
- Full route adoption explicitly remains out of scope.

## 16. 5E Prompt 1 Implementation Supplement - 2026-06-11

Package 5E Prompt 1 added the route policy skeleton only.

Files added or updated:

- `backend/app/services/route_policy.py`
- `backend/tests/test_route_policy_resolver.py`
- `docs/implementation_plans/route_policy_5e_benchmark_gated_adoption_plan.md`

Implemented skeleton:

- `RouteExecutionMode` with all planned modes.
- `RouteDecision` diagnostic metadata for selected mode, requested mode, config source, served-output source, side-effect policy, benchmark gate placeholder, fallback state, warnings, and errors.
- `RoutePolicyResolver` centralized config parsing for SOC-first `SOC_ROUTE_MODE` and future `COPILOT_ROUTE_POLICY`.
- Default absent SOC route mode resolves to `canonical_only`.
- Per-copilot defaults resolve to `canonical_only` for SOC, Trading, Purchasing, DataOps, and S2P.
- Invalid route mode fails closed with explicit diagnostics.
- `pipeline_served`, `hybrid_fast_path`, and `fallback_to_canonical` are represented but blocked without a later approval package.

Explicit non-implementation:

- No SOC route handler was wired to the resolver.
- No served SOC analyze output changed.
- No pipeline-served behavior was enabled.
- No DecisionPipeline default was enabled.
- No EntityCache default was enabled.
- No materialized counter route adoption was added.
- No proof, counter, graph-write, or outcome criteria changed.
- Full route adoption remains blocked.

## 17. 5E Prompt 2 Plan - No-Behavior-Change SOC Route Decision Diagnostics Hook

Prompt 1 is closed with `PASS_WITH_P3`. Prompt 2 remains planning only. The next implementation should add a no-behavior-change SOC route decision diagnostics hook through a centralized adapter/facade boundary. Canonical served output remains unchanged, `pipeline_served` remains blocked, and full route adoption remains blocked.

Prompt 2 must not serve pipeline output. It should make route policy resolution observable without changing the decision-critical SOC analyze response fields.

### Source Inventory for Prompt 2

SOC analyze route:

- `backend/app/routers/triage.py`
- `analyze_alert(request: ProcessAlertRequest)` at `POST /api/alert/analyze`.

Canonical output construction:

- `triage.py` builds the canonical response dictionary beginning at the `response = { ... }` block around line 1205.
- Decision-critical fields include `recommendation`, `gae_scoring`, `referral`, `referral_debug`, `composite_gate`, `decision_method`, and decision metadata embedded in existing payload fields.
- Narrative is added after canonical response construction through `response["narrative"] = get_narrative_provider().generate(...)`.

Existing shadow diagnostics hook:

- `triage._soc_maybe_attach_decision_pipeline_shadow(response, alert_data, context)` is defined near line 111.
- `analyze_alert()` calls it after narrative generation in the `decision_pipeline_shadow_compare` performance phase around line 1318.
- The hook preserves canonical output and attaches `_diagnostics.soc_decision_pipeline_shadow` only when `USE_SOC_DECISION_PIPELINE_SHADOW=true`.

Existing side-effect and write points:

- Canonical analyze writes the `Decision` node and `DECIDED_ON` edge in the `decision_node_and_edge_write` block around lines 781-820.
- Analyze also records audit data after the decision write.
- Outcome/proof mutation is separate in `triage.report_decision_outcome()`.
- Prompt 2 must not add proof writes, outcome writes, graph mutations, counter updates, or new AGE readbacks.

Resolver and diagnostics projection:

- `backend/app/services/route_policy.py`
- `RoutePolicyResolver.resolve(copilot="soc", route_name="analyze")`
- `RouteDecision.to_diagnostics()` exposes selected mode, requested mode, config source, reason, served output source, diagnostic evaluation source, diagnostics flag, side-effect policy, benchmark gate metadata, fallback state, warnings/errors, approval state, and blocked status.

Relevant tests:

- `backend/tests/test_route_policy_resolver.py`
- `backend/tests/test_soc_domain_profile_pipeline.py`
- `backend/tests/test_soc_entity_cache_route_readiness.py`
- `backend/tests/test_triage_routing_actions.py`

### Proposed Adapter / Hook Design

Add a SOC-local route adapter/facade, for example:

- `app.services.route_policy.resolve_soc_analyze_route_decision(...)`, or
- `app.services.soc_route_policy_adapter.SocRouteDecisionAdapter`.

Preferred implementation shape:

- Keep config/env parsing inside `RoutePolicyResolver`.
- Route handler calls one adapter/facade boundary and does not parse `SOC_ROUTE_MODE`.
- Adapter resolves `RouteDecision` for `copilot="soc"` and `route_name="analyze"`.
- Adapter returns safe diagnostics via `RouteDecision.to_diagnostics()`.
- Adapter does not choose served pipeline output.
- Adapter does not call `DecisionPipeline`.
- Adapter does not read graph state, write graph state, mutate counters, or touch proof/outcome code.

Prompt 2 hook placement should be after canonical response construction and narrative generation, near the existing shadow diagnostics seam. This keeps policy diagnostics out of decision computation and makes it easier to prove canonical output is unchanged after removing `_diagnostics`.

### Diagnostics Placement

Safest initial placement:

- Attach route policy diagnostics under `_diagnostics.route_policy` only.
- Do not add a new top-level response metadata field.
- Do not alter `recommendation`, `gae_scoring`, `referral`, `referral_debug`, `composite_gate`, `decision_method`, `graph_data`, `analysis`, `context`, `alert`, or `narrative`.

Required diagnostic fields:

- `selected_mode`
- `requested_mode`
- `config_source`
- `reason`
- `served_output_source`
- `diagnostic_evaluation_source`
- `diagnostics_enabled`
- `side_effect_policy`
- `benchmark_gate_status`
- `fallback_state`
- `warnings`
- `errors`
- `approved_for_serving`
- `blocked`

Diagnostics must be safe for unit tests and runner inspection. They must not expose alert payloads, user identifiers, asset identifiers, graph query contents, stack traces, raw exception messages, or sensitive security context values.

### Prompt 2 Mode Behavior

| Mode | Prompt 2 behavior |
| --- | --- |
| `canonical_only` | Canonical output served. `_diagnostics.route_policy` may report `canonical_only`, default/config source, and canonical side-effect policy. No pipeline evaluation. |
| `shadow_only` | Canonical output served. Existing shadow diagnostics may remain controlled by current shadow flag/logic. Route policy diagnostics report `shadow_only` if configured. Shadow side effects must remain zero. |
| `pipeline_read_only` | Canonical output served. Pipeline output must not be served. If no read-only route hook exists, diagnostics should report not implemented / diagnostic-only skeleton behavior. |
| `pipeline_served` | Blocked/fail-closed. No served output change. No pipeline output served. Requires a separate approval package before any serving behavior. |
| `hybrid_fast_path` | Blocked/fail-closed. No case classifier or hybrid serving behavior implemented. |
| `fallback_to_canonical` | Blocked/fail-closed for served behavior. May only be represented in diagnostics; no fallback success can be counted as parity pass. |
| `disabled` | Explicit fail-closed policy state. See invalid/disabled behavior below. |

### Invalid and Disabled Config Behavior

Prompt 2 should fail closed for invalid `SOC_ROUTE_MODE`, `disabled`, and blocked served modes rather than silently serving canonical output with a hidden diagnostic. The safer behavior is:

- Return a clear route-policy error response, or raise a clear HTTP error from the route boundary, before decision-critical work proceeds.
- Include sanitized route policy diagnostics with no alert/security context values if the response shape permits it.
- Do not write a Decision node, proof artifact, outcome artifact, counters, or graph mutations after policy fail-closed.
- Do not count fail-closed policy behavior as route parity success.

Rationale: Prompt 2 introduces an explicit route policy. A bad route policy should be visible immediately and should not silently fall back to canonical behavior, because silent fallback would hide bad deployment config and create fake pass risk.

### Prompt 2 Test Plan

Add or update non-live tests, likely in:

- `backend/tests/test_route_policy_resolver.py`
- `backend/tests/test_soc_domain_profile_pipeline.py` or a new `backend/tests/test_soc_route_policy_diagnostics.py`
- `backend/tests/test_soc_entity_cache_route_readiness.py` only if source-level route readiness checks need updating.

Required tests:

- Default absent `SOC_ROUTE_MODE` preserves full canonical analyze response except `_diagnostics.route_policy` if diagnostics are attached.
- `_diagnostics.route_policy` shows `canonical_only`, `config_source=default`, `served_output_source=canonical_route`, and canonical side-effect policy.
- `SOC_ROUTE_MODE=canonical_only` preserves canonical output.
- `SOC_ROUTE_MODE=shadow_only` still serves canonical output and does not change decision-critical fields.
- Existing `USE_SOC_DECISION_PIPELINE_SHADOW` flag alone does not change served output.
- `SOC_ROUTE_MODE=pipeline_read_only` does not serve pipeline output.
- `SOC_ROUTE_MODE=pipeline_served` is blocked and cannot change served output.
- `SOC_ROUTE_MODE=hybrid_fast_path` and `SOC_ROUTE_MODE=fallback_to_canonical` are blocked.
- Invalid `SOC_ROUTE_MODE` surfaces the chosen clear fail-closed behavior.
- `SOC_ROUTE_MODE=disabled` surfaces the chosen clear fail-closed behavior.
- No proof/outcome writes are added.
- No counter behavior changes.
- No graph mutation behavior changes beyond current canonical analyze writes.
- No EntityCache behavior changes.
- Route handler does not parse route env directly; env parsing remains inside resolver/config boundary.
- RouteDecision diagnostics include all required fields.
- `COPILOT_ROUTE_POLICY=trading:pipeline_served` does not affect SOC and is blocked/default for Trading in resolver tests.
- Malformed colonless `COPILOT_ROUTE_POLICY` entry behavior is tested and documented.
- Source-level anti-sprawl test confirms no scattered `SOC_ROUTE_MODE` checks in route handlers.

Prompt 2 tests should compare canonical response after removing `_diagnostics` so added diagnostics are the only permitted response-shape difference.

### Live Validation Plan After Prompt 2 Implementation

Do not run live validation during planning or implementation.

Future sequence after Prompt 2 code review:

- Run targeted non-live route diagnostics tests first.
- Run 5D-style route validation runner with `SOC_ROUTE_MODE=canonical_only`.
- Run 5D-style route validation runner with `SOC_ROUTE_MODE=shadow_only` only if Prompt 2 touches shadow-adjacent diagnostics.
- Run `proof_250` only if route output, proof-adjacent behavior, or write boundaries changed.
- Compare profile must report parity or exact deltas.
- Update performance ledger only if live validation runs.
- Buyer-facing claim remains NO.

### Performance and Overhead Guardrails

Prompt 2 must not claim a performance improvement.

Guardrails:

- Route policy diagnostics overhead must be measured before any promotion beyond diagnostics.
- Diagnostics attachment must be lightweight dictionary construction only.
- Route policy resolution must not perform per-request graph reads.
- Route policy resolution must not trigger AGE readback.
- Route policy resolution must not invoke `DecisionPipeline`.
- Route policy resolution must not trigger EntityCache loading or materialized counter reads.
- Benchmark-gated promotion remains required for any future non-canonical behavior.

Ledger carried forward:

- P2E baseline: avg analyze 0.193s at 250 outcomes, warm_fallback.
- P3G-D: avg analyze 0.202s, max 0.571s, avg outcome 0.440s; hits=0, misses=250, loads=250.
- P3H: EntityCache correct but current route wiring is not reliable speedup.
- 5D-A: unique_once 0.384314, repeat_same 0.169158, mixed_reuse 0.134437.
- 5D-B: unique_once 0.364990, repeat_same 0.356329, mixed_reuse 0.218911.
- 5D runner proof: avg analyze 0.169s, max analyze 0.476s, avg outcome 0.228s.
- 5E Prompt 1 actual: policy skeleton only; no route latency.
- Buyer-facing claim allowed: NO.

### P3 Items Carried Forward

- Add future resolver test for `COPILOT_ROUTE_POLICY=trading:pipeline_served` proving non-SOC served modes are blocked through the multi-copilot path.
- Harden or document malformed colonless `COPILOT_ROUTE_POLICY` token handling.
- Add explicit `graph_truth_proof_authority_preserved` observability field before broader served-route adoption.

### Prompt 2 Non-Goals

- Serve pipeline output.
- Approve `pipeline_served`.
- Implement `hybrid_fast_path`.
- Implement `fallback_to_canonical` route serving.
- Adopt EntityCache.
- Adopt materialized counters.
- Change proof criteria.
- Change graph/proof/counter writes.
- Run live validation.
- Run 250 proof.
- Approve full route adoption.
- Make buyer-facing performance claims.

### Prompt 2 Implementation Slice for Later

Future Prompt 2 implementation should be a single narrow package:

- SOC route policy adapter/facade skeleton.
- `_diagnostics.route_policy` attachment after canonical response assembly.
- Fail-closed handling for invalid/blocked route policy config.
- Unit tests proving no decision-critical response change.
- Unit/source tests proving route handlers do not parse route env directly.
- Plan supplement update.
- No live validation.

Then request GPT-5.5 review before any runner or live validation.
