# FIX-ASTRA-SOC Verified Design

Date: 2026-09-27T16:09:07-07:00
Verified against: `8b0851c9fb4bcfb4b3443ad52828b93a95c21517`, **including the existing uncommitted SS/FIX-SOC working tree**.

This is source-based design verification, not implementation or runtime validation. Read `docs/session_state.md` and `docs/astra_sweep_soc_report.md`, inspected the named functions with surrounding context, and searched production, frontend, and test call sites. No pytest, mypy, application imports, server requests, fixtures, or fault probes were run. The recorded baseline remains the prior sweep's **2,669 passed / 0 failed / 0 skipped**, mypy clean in 205 files, frontend typecheck passing; those results were not re-established here.

Line references describe this working tree. Paths below are relative to `gen-ai-roi-demo-v4-v50/`. No separate proposed implementation document was supplied: the sweep's remedies are the proposals verified and corrected here.

## Split Decision

**Use two sequential implementation prompts.**

1. **Response contracts:** SOC-01, SOC-02, SOC-03, SOC-06, bundled SOC-10 and SOC-13, including their required serialization and display consumers.
2. **Evidence admission and action-write preconditions:** SOC-04 and SOC-05, including comparator admission and factor-service consumers.

The first group is not exclusively mechanical: SOC-03 must preserve partial snapshot data, and SOC-10 must reach the real executive endpoint's response model, PDF, and governance composition. These can nevertheless be tested independently of decision mutation. SOC-04 changes evidence admission; SOC-05 changes whether an action request may write a Decision. Give those their own behavioral checkpoint.

**There is no SOC-04 -> SOC-05 causal pipeline in the current application.** `routers/triage.py:620` returns the investigation result from a read-only shadow endpoint. `execute_action` at line 1779 independently reads context, calls `agent.decide`, and retrieves factors. It does not accept an InvestigationResult, its action, or its `v_final`. The frontend mounts `InvestigationPanel` at `AlertTriageTab.tsx:910` without `onResult`; its execute handler at line 528 sends only the alert ID. The two fixes share a source file and UI workflow, not a persisted vector. Do not introduce a coupling as part of this repair.

The actual causal relationship in the response group is **SOC-03 -> SOC-13's timeline availability**: changing a timeline failure from whole-result absence to a partial object makes `timeline is not None` insufficient to describe all of that object's components.

## Per-Finding Verified Specification

### Contract notation and scope

Defaults below are **wire defaults**, not authorization to invent internal evidence. A numeric default is usable only with its accompanying availability indicator. Healthy measured values, including a genuine zero, remain available. Flags are `bool`, never an optional boolean. Collections use fresh factories in models.

The requested no-null wire specification requires a small explicit extension beyond the named catches: existing absent bootstrap arrays, timeline ceilings/drifts, optional investigation labels, and balance-sheet ceilings currently contain nulls. Normalize these **at the touched HTTP boundary**, with separate availability flags where a numeric/boolean default could be mistaken for a measurement. Keep internal absence sentinels and helper tests intact. Update the listed frontend null-based presence checks in the same prompt. This is a deliberate wire-contract correction, not an instruction to change all nullable fields across the repository or alter the scoring algorithms.

For an optional heterogeneous record member, omission remains allowed; adding a null placeholder is not. Existing successful source records pass through unchanged unless the specific normalization below applies. The field inventories enumerate endpoint envelopes and owned nested records; arbitrary connector evidence is not a new universal schema.

### SOC-01 — Validate unavailable centroid support and stop claiming unmeasured GREEN

**Files to change:**

- `backend/app/routers/soc.py` — `get_centroid_support`.
- `backend/app/models/responses.py` — `CentroidSupportResponse`.
- `frontend/src/components/ContinuityPanel.tsx`.
- `frontend/src/components/tabs/RuntimeEvolutionTab.tsx`.
- Tests: `backend/tests/test_centroid_support.py`, `backend/tests/test_write_roundtrips.py`; add focused HTTP failure cases in the former.

**Response shape contract:**

Current decorator at `soc.py:4372` specifies `response_model=CentroidSupportResponse`, with **no** `response_model_exclude_none`. The handler returns a dict. Required current model fields are `overall_health`, `warning_count`, `threshold_sigma`, `interpretation`; `support_summary` and `note` have defaults. Unknown `status` and `reason` are currently filtered out.

Proposed complete HTTP 200 envelope:

- `support_summary: dict[str, dict[str, SupportEntry]] = {}`.
- `SupportEntry.support_status: str = ""`; `n_factors_outside: int = 0`; `max_deviation_sigma: float = 0.0`. Emit entries only for actually computed support.
- `overall_health: str = "UNAVAILABLE"`.
- `warning_count: int = 0`.
- `threshold_sigma: float = 2.0`.
- `interpretation: str = "Centroid support is unavailable."`.
- `note: str = ""`.
- `status: str = "unavailable"`; healthy `"ok"`, uninitialized/unqualified `"cold_start"`.
- `reason: str = ""`; use stable reasons `scorer_uninitialized`, `bootstrap_missing`, or `bootstrap_read_failed`.
- `support_available: bool = True`; set false for all three unavailable/unqualified cases.
- `degraded: bool = False`; true when support cannot be evaluated.

For cold start and missing bootstrap, use `overall_health="UNAVAILABLE"`, not GREEN. `status`/`reason` distinguish missing baseline from a failed read. Only a completed computation may select GREEN/AMBER/RED. A zero warning count with support unavailable is a placeholder, not a clean bill of health. Reject/mark unusable empty tensor dimensions before the zero-iteration loop can imply measured GREEN.

**Downstream consumers:**

- `models/responses.py:329` — validates/filter-serializes every response; currently rejects the exception branch's missing interpretation and noninteger count. **Must declare all new metadata.**
- `frontend/src/components/ContinuityPanel.tsx:19,31` — reads health and warning_count; does **not** check availability. Its line 36 badge always says measured state. **Must display unavailable support and avoid presenting placeholder warning count as measured.**
- `frontend/src/components/tabs/RuntimeEvolutionTab.tsx:537,934,3655` — reads overall_health and interpretation; does **not** check flags and styles every non-GREEN/non-AMBER status red. **Must add an unavailable state and flag to the local type.**
- No backend function calls `get_centroid_support` directly; it is a mounted route. No generated frontend CentroidSupportResponse consumer was found.

**Tests to update:**

- `test_centroid_support.py:46` / `test_centroid_support_overall_health_valid` currently only permits GREEN/AMBER/RED regardless of baseline readiness. Assert measured colors only when `support_available` is true; explicitly assert UNAVAILABLE and a reason for deterministic cold/missing/failing cases. Do not merely widen the allowed set.
- `test_centroid_support.py:35` accepts either zero or six categories without checking why. Pair the count with availability and use an initialized success case that must contain six categories.
- `test_write_roundtrips.py:105` checks field presence only. Extend mounted HTTP coverage to assert value types and metadata survives Pydantic serialization.
- Pure support geometry tests at lines 55 and 71 are correct; do not relax them.

**New tests needed:** scorer absent; bootstrap absent; bootstrap read raises; valid no-drift baseline; warning baseline; unusable empty tensor; HTTP model validation and UI unavailable rendering. Assert no null count/interpretation, no unmeasured GREEN, and warning logs on failed reads.

**Fix pseudocode:**

```text
if scorer absent: return typed_support_unavailable("scorer_uninitialized", cold_start=True)
bootstrap = read_bootstrap_or_log_failure()
if bootstrap absent/unusable: return typed_support_unavailable(reason)
return measured_support + {support_available: True, degraded: False, status: "ok", reason: ""}
```

**Risk:** Returning only extra dict keys does not repair a filtered Pydantic response. Turning absent data into GREEN, or rendering unavailable as RED, gives an incorrect operational conclusion.

### SOC-02 — Keep centroid-export IKS numeric and identify unavailable evidence

**Files to change:**

- `backend/app/routers/soc.py` — `get_centroid_export`.
- `frontend/src/components/tabs/RuntimeEvolutionTab.tsx` — export type and download message.
- `backend/tests/test_soc_degraded_paths.py`, `backend/tests/test_centroid_export.py`.
- Do not change the internal `build_centroid_export` contract just to normalize HTTP output.

**Response shape contract:**

`soc.py:4170` has no Pydantic response_model/exclusion options; the handler returns a dict. `gae_state.py:864` supplies the raw export. Preserve these fields, applying wire defaults only when unavailable:

- `export_version: str = ""`; `generated_at_epoch: int = 0`; `gae_version: str = ""`.
- `tensor_shape: list[int] = []`; `current_mu: list[list[list[float]]] = []`; `bootstrap_mu: list[list[list[float]]] = []`.
- `decision_count: int = 0`; `categories: list[str] = []`; `actions: list[str] = []`; `sha256: str = ""`.
- `exported_at: int = 0`; `factors: list[str] = []`.
- `centroids: dict[str, dict[str, list[float]]] = {}`.
- `drift_from_bootstrap: dict[str, float] = {}`; unavailable per-category values are 0.0 with `bootstrap_available=false`.
- `checksum: str = ""`; `iks_score: float = 0.0`.
- `iks_available: bool = True`; false for an exception, absent IKS, or an explicitly unavailable IKS result.
- `bootstrap_available: bool = True`; false for an absent baseline.
- `centroids_available: bool = True`; false for scorer cold start.
- `degraded: bool = False`; aggregate unavailable requested measurements.
- `status: str = "ok"`; `message: str = ""`; cold start uses `"cold_start"` and the existing explanatory message.

`format=summary` still **omits** `current_mu`, `bootstrap_mu`, and `centroids`; it retains availability metadata. No null IKS. Do not use truthiness to reject a measured `iks_v2=0.0`. Keep hashes and real tensor values unchanged. A complete typed cold-start envelope may add keys to the existing two-key cold-start response; it must remain recognizably cold-start and not pretend to contain an exportable tensor.

**Downstream consumers:**

- `frontend/src/lib/api.ts:160` — fetch wrapper, no shape/flag interpretation. No change needed to transport.
- `frontend/src/components/tabs/RuntimeEvolutionTab.tsx:220,951` — downloads the entire object and reads timestamp, tensor_shape, sha256, decision_count. Does **not** check IKS/degraded/status. Add a partial-export message, preserve metadata in the downloaded JSON, and do not announce a tensor export for cold start.
- No other frontend import/use of `fetchCentroidExport` was found.
- `services/balance_sheet.py:123` and `services/governance_report.py:130` call **the raw helper**, not this endpoint. Its internal absence semantics must stay unchanged; there is no automatic causal fix to these consumers from changing SOC-02.

**Tests to update:**

- `test_soc_degraded_paths.py:136` / `test_centroid_export_does_not_use_zero_iks` explicitly asserts `iks_score is None` at line 150. Rename to reflect typed unavailable IKS; assert numeric 0.0, `iks_available is False`, `degraded is True`, and retained tensor content through HTTP.
- `test_centroid_export.py:209,227,242,260` skip payload checks on cold start and do not exercise IKS failure. Retain healthy assertions but use a deterministic initialized scorer for the new failure test; a cold-start skip cannot satisfy it.
- Summary test around line 135 must also assert `centroids` is omitted and both JSON/summary retain IKS flags.
- **Keep** raw-helper missing-bootstrap assertions at `test_centroid_export.py:126`: internal absence is legitimate. Only the endpoint serializer normalizes it.

**New tests needed:** IKS raises with healthy raw export; missing IKS key; valid zero IKS; absent bootstrap with real centroids; summary parity; scorer cold start. Assert a failing optional IKS read does not discard healthy tensor/hash data. A primary bootstrap read failure is a distinct issue listed below; do not claim the IKS-only test covers it.

**Fix pseudocode:**

```text
raw = await build_centroid_export(...)  # internal absence semantics unchanged
iks = await read_iks_or_none_with_warning()
export = normalize_export_for_http(raw, iks_score=0.0 if iks is None else iks)
export.update(iks_available=iks is not None, degraded=any_required_measurement_unavailable)
return omit_tensor_fields(export) if format == "summary" else export
```

**Risk:** A numeric fallback without the flag invents measured IKS; a null fallback breaks the promised field type. Normalizing the raw helper globally would alter balance-sheet/governance assumptions and valid internal tests.

### SOC-03 — Preserve partial time-machine data when current IKS is unavailable

**Files to change:**

- `backend/app/services/time_machine.py` — `get_evolution_timeline` and a narrowly scoped IKS-read result/assembler if needed.
- `backend/app/routers/time_machine_router.py` — `get_timeline_endpoint` wire normalization.
- `backend/app/services/balance_sheet.py` — `_safe_timeline`/availability interpretation, coordinated with SOC-13.
- `frontend/src/components/tabs/RuntimeEvolutionTab.tsx` — timeline types, partial-state message, chart availability.
- Tests: `backend/tests/test_time_machine.py`, `backend/tests/test_ss14_reports_analytics_degraded.py`, `backend/tests/test_balance_sheet.py`.

**Response shape contract:**

No response_model/exclude_none; current router returns the service result directly and translates RuntimeError into HTTP 503. Current service annotation permits a whole-result absence. **Correct the proposed router-only fix:** synthesizing an empty envelope after that absence would lose already fetched snapshots. Retain a partial service object and normalize only its missing IKS component at the HTTP boundary.

- `timeline: list[TimelinePoint] = []`.
- Each point: `snapshot_id: str = ""`; `timestamp: int = 0`; `timestamp_epoch: int = 0`; `decision_count: int = 0`; `sha256: str = ""`; `file_path: str = ""`; `drift_from_bootstrap: float = 0.0`; `iks_estimate: float = 0.0`; `ceiling_estimate: float = 0.0`.
- Point measurement metadata: `drift_available: bool = True`, `iks_estimate_available: bool = True`, `ceiling_available: bool = True`; false when the underlying estimate is absent. Historical `iks_estimate` is currently a drift alias, not current IKS; do not silently redefine it.
- `current: object = {iks_v2: 0.0, components: {}, interpretation: "unavailable"}`.
- `current.iks_v2: float = 0.0`; `current.components: dict[str, float] = {}`; `current.interpretation: str = "unavailable"`.
- `ceiling_estimate: float = 0.0`; `ceiling_note: str = ""`; `ceiling_available: bool = True`.
- `categories: list[str] = []`; `actions: list[str] = []`; `factors: list[str] = []`. Preserve configured names when available.
- `timeline_available: bool = True`; `iks_available: bool = True`; `data_available: bool = True`; `degraded: bool = False`.

When only IKS fails: retain timeline, names, ceiling and note; `timeline_available=true`, `iks_available=false`, aggregate unavailable/degraded. Checkpoint-store RuntimeError remains a deliberate HTTP 503 (`detail: str`), not a fabricated successful empty timeline. Internal ceiling absence remains distinguishable from a measured zero.

**Downstream consumers:**

- `routers/time_machine_router.py:70` — forwards all service fields without checks. Must serialize the partial result; never return the whole-result failure sentinel as JSON.
- `services/balance_sheet.py:159,225,232` — reads timeline existence and ceiling; currently `timeline_available = timeline is not None`. Must use the explicit timeline section flag. Current IKS failure does not mean checkpoint history is absent; preserve its independent IKS flag under SOC-13.
- `frontend/src/lib/api.ts:546` — unchanged transport.
- `RuntimeEvolutionTab.tsx:325,755,761` — reads only timeline into state, discarding all top-level metadata. Must store/display availability; an empty healthy timeline and failed current IKS must differ visibly.
- `RuntimeEvolutionTab.tsx:1278,1285,3093` — reads timestamp/count/drift/ceiling and uses non-null ceiling to display a chart. **Must check new flags before plotting wire-default zero or showing the ceiling series.** Chart-local gaps may still use the chart library's absent-value representation; this does not change the HTTP contract.
- No other production callers of `get_evolution_timeline` were found.

**Tests to update:**

- `test_ss14_reports_analytics_degraded.py:35` asserts `_safe_timeline(BrokenGraph()) is None`. This is ambiguous: it may fail earlier because no scorer/checkpoint store exists. Split it: checkpoint dependency failure remains absence/503; initialized checkpoint history plus failed IKS must return partial timeline, not absence.
- `test_time_machine.py:41,51,62,74` test list/detail/compare/missing snapshot, **not timeline HTTP output**. Keep their expectations; they are insufficient evidence for SOC-03.
- `test_balance_sheet.py:90,267` timeline stubs must model section availability in new partial tests, without changing unrelated existing happy-path cases.

**New tests needed:** nonempty snapshots survive failed IKS; complete route JSON types; successful empty timeline versus failed IKS; healthy zero IKS; checkpoint RuntimeError still 503; balance sheet retains available timeline when only IKS fails; no unavailable-zero chart points/ceilings displayed.

**Fix pseudocode:**

```text
timeline, ceiling, names = collect_checkpoint_data()  # preserve explicit store failure
iks = await read_current_iks_or_none_with_warning()
partial = assemble_timeline(timeline, current=iks, iks_available=iks is not None)
return partial  # service retains independent data; router normalizes absent components
```

**Risk:** A whole-result fallback throws away good history. Conversely, merely returning a nonempty dict can make the balance sheet falsely call every component available. Numeric ceiling normalization without chart flags creates a fictitious zero ceiling.

### SOC-04 — Exclude unavailable investigation evidence before re-extraction

**Files to change:**

- `backend/app/services/investigation_patterns.py` — BaseInvestigationPattern execution failure payload.
- `backend/app/services/investigation_loop.py` — evidence admission and failure trace.
- `backend/app/services/triage_providers.py` — defensive adapter admission filter.
- `backend/app/models/investigation.py` — additive step/result flags and wire serialization support.
- `backend/app/services/investigation_comparators.py` — shared comparator admission loop/result propagation.
- `backend/app/routers/triage.py` — investigation response propagation only; preserve read-only/oracle separation.
- `frontend/src/components/InvestigationPanel.tsx`.
- Tests: `backend/tests/test_ss14_reports_analytics_degraded.py`, `backend/tests/test_investigation_loop.py`, `backend/tests/test_rho_measurement.py`; add non-planted route coverage and frontend degraded trace coverage.

**Response shape contract:**

`InvestigationResult`/`InvestigationStep` are **dataclasses**, not Pydantic response models. `/api/soc/investigate` returns a dict, with no exclude_none. Do not apply a response_model-only fix.

Internal pattern result keeps its dict contract:

- `investigation_category`, `investigation_pattern`, `traversal`, `selected_edge`, `candidate_read`, `graph_query`, `schema_source`: `str = ""` each.
- `candidate_reads`, `enriched_factors`, `evidence_keys`: `list[str] = []` each.
- `vld_factor_vector: list[float] = []` on failed read; **never a fabricated six-number vector**.
- `read_cost: float = 0.0` if unknown; `evidence_available: bool = True`; `degraded: bool = False`; `failure_reason: str = ""`.
- Pattern-specific successful evidence keys remain unchanged. On failure do not invent values for them or claim their names were observed; retain requested traversal metadata separately.

Complete main HTTP envelope:

- `status: str = "ok"` (use `"degraded"` for a failed investigation); `mode: str = "vld_read_only_shadow"`; `alert_id: str = ""`.
- `single_pass: object` with `action: str = ""`, `confidence: float = 0.0`, `category: str = ""`.
- `vld: InvestigationResultWire`; `investigation_trace: list[InvestigationStepWire] = []`; `conservation_emit_gate: str = "not_evaluated_read_only"`.
- `evidence_available: bool = True`; `degraded: bool = False`; `failed_patterns: list[str] = []` (also present inside `vld`, because the UI consumes that object).

`InvestigationResultWire` fields:

- `action`, `category`, `investigated_category`, `single_pass_action`, `fixture_source`: `str = ""` each.
- `confidence`, `single_pass_confidence`: `float = 0.0` each.
- `routing_agreed: bool = True`; `agreement: bool = True`; `trace: list[InvestigationStepWire] = []`; `v_final: list[float] = []`; `steps: int = 0`.
- `conservation_emit_gate: str = "not_evaluated_read_only"`; `halt_reason: str = "unknown"`; `policy: str = "vld"`.
- `evidence_available: bool = True`; `degraded: bool = False`; `failed_patterns: list[str] = []`.

`InvestigationStepWire` fields:

- `step: int = 0`; `pattern`, `alert_category`, `selected_edge`, `timestamp`, `policy_version`, `halt_reason`, `failure_reason`: `str = ""` each.
- `v_before`, `v_after`: `list[float] = []` each; `cat_distances_before`, `cat_distances_after`: `dict[str, float] = {}` each.
- `evidence_keys`, `candidate_reads`: `list[str] = []` each.
- `propensity`, `cost`, `residual`: `float = 0.0` each.
- `evidence_available: bool = True`; `evidence_admitted: bool = True`.

For this fix choose a deterministic **halt-on-unavailable-read** policy. Log/trace the attempted read with `evidence_available=false`, `evidence_admitted=false`, `v_after == v_before`, identical before/after distances, residual 0.0, and `halt_reason="evidence_unavailable"`. Do not rerun extraction or update flip counts. Preserve the preceding valid vector (not always the initial vector after prior successful steps). Result action/confidence are scored from that retained vector. Trace length includes the failed attempt, so `steps == len(trace)`. Initial surface extraction failure has no valid prior vector: fail explicitly rather than fabricate one.

Internal optional labels may remain internal absence sentinels; normalize to strings when producing wire output. Additive dataclass flags must have defaults so existing healthy comparator/planted constructors remain valid. Do not change oracle eligibility or allow an investigation to write decisions/learn.

**Downstream consumers:**

- `investigation_loop.py:74,77,79,134` — currently appends every pattern result, re-extracts, and returns a result without availability. **Must gate before append/compute and serialize the failure trace.**
- `triage_providers.py:31,33,49` — adapter copies all evidence into both vector list and merged security context. **Filter unavailable evidence from both surfaces**, not only `vld_factor_vectors`.
- `_RealFactorVectorProvider.compute`, `triage_providers.py:95,107` — invokes orchestrator then `_apply_vld_reextraction`. With no admitted vectors, `_apply_vld_reextraction` returns the newly computed base vector, not necessarily the preceding vector. **Therefore adapter filtering alone is not sufficient; loop must skip compute on failure.**
- `investigation_comparators.py:146` — same unconditional admission in `_one_or_many_pattern_result`. Used by ContentRulePolicy (46), MajorityBranchPolicy (67), RandomBranchPolicy (88), BreadthPolicy (110). Apply the same exclusion/trace policy. SinglePassPolicy (21) performs no evidence reads and remains unchanged.
- `routers/triage.py:620,621,631` — calls investigate, serializes result, returns `vld` and aliased trace. Propagate aggregate flags; do not keep a misleading unconditional status ok.
- `routers/triage.py:563,668` and `services/multihop_scenarios.py:336,390` — planted and oracle paths construct the same result dataclass through a different algorithm. Defaults/wire serialization must stay compatible. These are not consumers of BaseInvestigationPattern's failed AGE read; do not rewrite their scenario data.
- `frontend/src/lib/api.ts:181` — transport only.
- `frontend/src/components/InvestigationPanel.tsx:24,110,181,199,217` — reads nested result action/confidence/category, trace, vectors/distances, steps, routing_agreed, agreement, halt reason; no availability fields. Must show failed/not-admitted trace and degraded summary, not “No investigation needed”/successful enrichment. Preserve valid preceding score as explicitly partial shadow advice.
- `AlertTriageTab.tsx:910` — mounts the panel without a result callback. **No action-write consumer.** The `onResult` prop at InvestigationPanel line 59 has no production caller in the searched frontend.
- Comparator evaluation tests consume result/action/v_final/trace; retain healthy geometry and damping semantics. No production `scorer.learn`/`submit_outcome` path reads InvestigationResult or `vld_factor_vector` in this repository.
- Additional non-application consumers: `backend/scripts/measure_rho.py:172,177,215` compares policy results and final vectors; `backend/scripts/diagnose_value_chain.py:162` reads `v_final`. They do not inspect failure flags. Their configured `FixtureGraphStore.run_query` (`measure_rho.py:50`) successfully returns an empty list, so the failure-only admission change must leave these healthy fixture measurements unchanged. Do not change this fixture to return failure or relabel successful emptiness to make an outage test pass.

**Tests to update:**

- `test_ss14_reports_analytics_degraded.py:95` currently requires a truthy vector after a failed read (line 99). That is wrong. Require an empty typed vector, false availability, and no claimed admitted evidence.
- `test_investigation_loop.py:270` checks trace shape but no failure admission. Add flags to the contract and add a real failing-read case; do not simply compare an empty trace.
- Existing successful geometry tests at `test_investigation_loop.py:353,370,385` and `test_rho_measurement.py:195,204` are **not wrong**: their reads succeed. Keep evidence averaging/damping expectations.
- `test_multihop_wiring.py:159` tests a planted alert, so it does not cover the ordinary AGE investigation branch. Keep it and add a separate non-planted failure test.

**New tests needed:** first read fails; success then failure retains last vector; both reextract/damped modes; adapter given a failed payload cannot merge its fields/vector; all four comparator policies; non-planted HTTP flags/trace; successful empty read distinct from exception; unchanged scorer centroids/no Decision or outcome writes; unavailable trace UI.

**Fix pseudocode:**

```text
evidence = await pattern.execute(...)
if not evidence_available(evidence): record_unchanged_failed_step(); halt("evidence_unavailable")
else: admit(evidence); reextract_and_update_vector()
return result_from_last_valid_vector(trace, failed_patterns, degraded=bool(failed_patterns))
```

**Risk:** Filtering only the vector leaves synthetic context fields available to factor computers; filtering only the adapter can still recompute/change the vector. Reverting to the initial vector after a later failure loses valid earlier evidence. Treating all successful empty reads as outages would change healthy/offline behavior outside this fix.

### SOC-05 — Require valid factors before creating an action Decision

**Files to change:**

- `backend/app/routers/triage.py` — `execute_action`; factor GET consumer correction below.
- `backend/app/services/triage.py` — narrow failure classification if needed, keeping healthy factor computation unchanged.
- `backend/app/routers/explain.py` — companion consumers of unavailable factor results.
- `frontend/src/components/tabs/AlertTriageTab.tsx` — display execution failure; no success animation/receipt.
- `frontend/src/lib/api.ts` only if needed to display the server's detail for executeAction; keep other request behavior stable.
- Add focused backend execute-action/factor-unavailability tests using the existing triage harness; extend `backend/tests/test_soc_explainability.py` and `test_write_roundtrips.py` for consumer status contracts.

**Response shape contract:**

`/api/action/execute` returns a dict and has no response_model/exclude_none. The successful response is **unchanged**:

- `receipt: object`: `id`, `action`, `timestamp`, `target_system`, `target_system_response`: `str = ""` each.
- `verification: object`: `verified: bool = False`; `verification_method: str = ""`.
- `evidence: object`: `decision_id: str = ""`; `trace_captured: bool = False`; `nodes_consulted: int = 0`.
- `kpi_impact: object`: `metric: str = ""`; `contribution: str = ""`; `previous_avg: float = 0.0`; `new_avg: float = 0.0`.

**Failure is HTTP 503 with `detail: str = "Decision factors unavailable; action was not executed."`**, not a success-shaped receipt with fake factors. No receipt, Decision, audit entry, graph mutation event, resolved alert status, KPI success, or learning operation may be produced after this precondition fails. A missing Alert continues to be 404. Internal computation defects should not all be relabelled database outages: use a specific factor-read-unavailable exception for failed reads, while preserving ordinary programming-error visibility.

Do not persist `[]`, zeros, or six 0.5 values as a degraded Decision vector. Read the six explicit values, require the expected count and valid numeric values using `validated_factor_vector` (`domains/soc/factor_vector.py:11`), and do not pad missing factors or default missing `value` to 0.5. An explicit valid measured value 0.5 remains legal. Preserve the existing successful ordering in this repair; a separate canonical-factor migration is not implied.

`get_decision_factors` currently returns absence only when `_build_threat_intel_factor` is unavailable (`services/triage.py:264`); `_get_alert_type` can throw. Its healthy no-indicator result is still a populated factor response. Resolve both failure forms before side effects. If adding a specific exception, update **all three** helper callers listed below.

**Downstream consumers:**

- `routers/triage.py:1816,1849` — consumes helper factors/name/value and writes serialized vector. Must reject failed/missing/malformed factors before Step 1, not after CREATE.
- `routers/triage.py:3489` — `/api/triage/decision-factors/{alert_id}`, Pydantic `DecisionFactorsResponse` (`responses.py:302`), currently maps helper absence to 404 and other failures to 500. Must map unavailable read to 503. Healthy response fields remain alert_id, factors, recommended_action, confidence, decision_method, weights_note, optional existing kernel_note. Do not turn outage into a synthetic successful factor matrix.
- `routers/explain.py:21` — `_explain_context` maps unavailable factors to missing/404; consumed by `/soc/explain/no-precedent` at line 35 and `/soc/explain/what-if` at line 47. Must distinguish a genuinely absent alert from unavailable factors (503). These are missed consumers of the helper, not new execute-action callers.
- `frontend/src/lib/api.ts:188` — sends only alert_id; `fetchJSON` line 27 throws on non-2xx. No body-shape break from the deliberate 503.
- `AlertTriageTab.tsx:521` — success reads receipt/verification/evidence/kpi_impact, schedules four success steps and refreshes queue. Catch at line 541 only logs. Must surface a visible action-unavailable error without success animation; keep `closedLoop` empty.

Persisted Decision.factor_vector consumers found in the trace (none checks a factors-available flag, so preventing the write is essential):

- `routers/triage.py:2175,2256,2364,2583` — outcome endpoint reads/parses the vector; for scorable actions validates it then passes it to guarded ProfileScorer update. A structurally valid fabricated vector passes validation. Non-scorable routing actions intentionally skip centroid updates; do not claim every execute action necessarily learns.
- `domains/soc/scorer_adapter.py:68,87` — forwards the supplied factor vector to the underlying scorer update. `triage.py:2644,2674` persists learning artifacts/outcome/centroid after update. Actual production path uses guarded update and artifact persistence; no literal production `scorer.learn()` or `submit_outcome()` caller was found by search. Do not invent one.
- `services/gae_state.py:389` / `triage.py:2621` — DK Welford tracking consumes the learned vector; `gae_state.py:166,205` serializes/restores update vectors.
- `routers/soc.py:1165,1192` — explain-decision maps vector values into factor explanations; it cannot distinguish an invented valid vector.
- `framework/provenance.py:318,339` — reads factor vector and rebuilds named provenance.
- `framework/similar_cases_base.py:86,99,152` — parses verified vectors and computes similarity; `services/similar_cases.py:61` delegates to it.
- `services/cross_graph_discovery.py:659,669,866` — pattern convergence and downstream factor anomaly calculations parse stored vectors.
- `services/soc_learning_control.py:267,187` — measured frozen-twin comparison reads stored vectors and scores them.
- `services/nl_templates.py:370` — shadow-disagreement formatter reads vector values (and has its own neutral fallback for absent input); it is not called by execute_action.
- `services/soc_domain_profile.py:178` consumes the analyze pipeline's supplied draft vector, not a vector returned by investigation. `services/simulation.py:397,581` produces/records its own vector. These matches are separate producers, not an SOC-04 -> SOC-05 bridge.

**Tests to update:**

- No current backend test was found asserting “factor read failed but execute succeeded”; add a route-level regression rather than changing a nonexistent test.
- `test_audit_chain_wiring_extended.py:247` is labelled execute wiring but calls the audit recorder directly, not the endpoint. Keep its ledger assertion; do not use it as evidence that no action write occurs on failed factors.
- `test_write_roundtrips.py:95,173` test healthy factor shape only; retain six-factor requirements and add failed-read status coverage.
- `test_soc_explainability.py:138` genuine missing alert must remain 404. Add separate factor-outage cases rather than weakening this test.

**New tests needed:** helper returns absence; helper raises classified read failure; empty/short/missing-value/nonfinite factor matrix; healthy six factors preserved byte-for-byte after read-back; valid 0.5 accepted; failure graph permits writes but the endpoint performs none; no audit/events/alert mutation; factor GET and both explanation routes return 503 on outage; frontend renders error and no receipt.

**Fix pseudocode:**

```text
factors = await read_factors_or_raise_unavailable(alert_id)
if factors unavailable or incomplete: raise HTTP503_before_any_action_side_effect()
vector = validated_factor_vector([factor["value"] for factor in factors])  # no padding
perform_existing_action_write_audit_events_and_return_existing_success_shape(vector)
```

**Risk:** Persisting a flagged but apparently valid neutral vector still contaminates readers that ignore metadata. Rejecting after action/audit writes creates partial execution. Catching every exception as a connectivity error conceals programming defects.

### SOC-06 — Initialize and validate secondary enrichment availability

**Files to change:** `backend/app/routers/graph.py`; `backend/tests/test_ss13_graph_metrics_degraded.py` (or a focused graph-enrichment route test file).

**Response shape contract:**

`/api/graph/enrichment/summary` returns a dict, no response_model or exclude_none. Preserve:

- `indicators: list[EnrichmentView] = []`.
- `EnrichmentView.indicator: str = ""`; `sources: dict[str, object] = {}`; `source_count: int = 0`; `consensus_severity: str = "unknown"`. Source-specific successful records remain their existing schema; failed secondary reads do not rewrite primary source objects.
- `total: int = 0`.
- `by_severity: dict[str, int] = {critical: 0, high: 0, medium: 0, low: 0, unknown: 0}`.
- `threat_indicators: object = {total: 0, by_type: {}, by_severity: {}}`; nested total is int and both maps are `dict[str, int]`.
- `enrichment_available: bool = True`; `indicators_available: bool = True`; `degraded: bool = False`.

Secondary read raises/returns failure sentinel/returns malformed summary: retain valid primary `indicators`, total, severity; secondary typed defaults with `indicators_available=false`, `degraded=true`. Set the flag true **only after validation and assembly succeeds**. Healthy zero secondary total remains available. Preserve existing primary-failure behavior (both flags false); do not add a new independent secondary query on that early-return path merely to fix this finding.

**Downstream consumers:**

- `services/threat_indicator.py` `get_all_indicators` is the upstream source, not an HTTP consumer. Its normal failed-query sentinel is different from a thrown service exception; test both.
- `frontend/src/lib/api.ts:460` exposes `getEnrichmentSummary`, returns raw JSON and does not interpret fields/flags. Search found **no frontend call site** of that wrapper and no backend call of the handler. Do not invent a UI component needing modification.
- HTTP/API clients still receive every original top-level field, with booleans rather than uninitialized-variable errors.

**Tests to update:** `test_ss13_graph_metrics_degraded.py:15` exercises only the primary-query exception and returns before the bug. Keep it and assert all typed defaults/flags; add distinct primary-success/secondary-failure cases. No existing assertion requiring the crashing secondary behavior was found.

**New tests needed:** secondary throws before assignment; returns failure sentinel; missing/malformed total/maps; valid zero summary; nonempty primary views survive each failure. Through HTTP assert 200, not UnboundLocalError/500, and correct flag values. Assert the secondary service actually ran.

**Fix pseudocode:**

```text
threat_indicators = typed_empty_summary(); indicators_available = False
try: raw = await secondary_read(); threat_indicators = validate_and_project(raw); indicators_available = True
except read_or_projection_failure as exc: log_warning(exc)
return primary_fields + secondary_fields + explicit_availability_booleans
```

**Risk:** Initializing only `ti_summary` fixes UnboundLocalError but leaves malformed nonempty results falsely available. Replacing the whole response loses healthy primary enrichment.

### SOC-10 — Preserve narrative degradation through tab, model, and report consumers

**Files to change:**

- `backend/app/routers/soc.py` — `_tab5_content`, executive PDF composition.
- `backend/app/models/responses.py` — `ExecutiveNarrativeResponse` metadata and relevant wire defaults.
- `backend/app/services/governance_report.py` — narrative evidence/availability composition.
- `frontend/src/components/tabs/ExecutiveNarrativeTab.tsx` — flags in types and partial-report display.
- `backend/app/services/executive_narrative.py` only for required wire normalization and the separately identified missing IKS failure signals if bundled; retain independent section reads.
- Tests: `backend/tests/test_soc_degraded_paths.py`, `test_tab_content.py`, `test_executive_narrative.py`, `test_governance_report.py`, `test_ss14_reports_analytics_degraded.py`.

**Response shape contract:**

`_tab5_content` is a dict helper behind `/api/soc/tab/{n}/content`, **not the live ExecutiveNarrativeTab request**. That wrapper has no response_model. Wrapper fields: `tab: int = 5`, `tab_name: str = ""`, `content: object`, `generated_at_epoch: int = 0`.

Complete tab-5 content:

- `headline: str = ""`; `sections: list[dict] = []`; `what_changed: list[TopShift] = []` (TopShift: label/description strings, magnitude float).
- `what_discovered: object` with `campaign_count: int = 0`, `chain_count: int = 0`, `mechanism: str = ""`.
- `what_system_knows: object` with `iks: float = 0.0`, `categories_calibrated: int = 0`, `health_status: str = "UNAVAILABLE"`, `operational_knowledge_status: str = ""`, `pre_activation: bool = False`, `learning_enabled: bool = False`, `health_source: str = ""`, `status_reason: str = ""`, `learning_enabled_available: bool = True`.
- Same object: `flywheel_message`, `flywheel_status`, `flywheel_claim`, `flywheel_detail`, `flywheel_activation_note`, `centroid_summary`, `conservation_narrative`: `str = ""` each; `flywheel_edge_count: int = 0`.
- `competitive_test: object` with `title: str = ""`, `questions: list[{question: str, our_answer: str}] = []`.
- `research_backing: object`: experiments, factorial_cells, independent_judges, conservation_validation, framework_version are strings; falsifications is int. Preserve configured claim values.
- `sections_degraded: list[str] = []`; `degraded_fields: list[str] = []`; `data_available: bool = True`; `degraded: bool = False`.

Merge exact narrative keys into `sections_degraded`; merge namespaced `narrative.<section>` entries into existing degraded_fields, preserving local `iks`/`flywheel_edge_count` failures, deduplicated in stable order. A successful local read must not erase a different failed narrative section.

The separate `/api/soc/executive-narrative` at `soc.py:1698` has `response_model=ExecutiveNarrativeResponse`, no exclude_none, and returns a dict. Required model fields: headline, what_changed, what_discovered, what_knows, metrics, generated_at, pdf_available. `sections` is presently optional. **The model currently has no sections_degraded and filters it out. Add it explicitly.** Full dedicated response:

- `headline: str = ""`; `generated_at: str = ""`; `pdf_available: bool = True`; `sections: list[dict] = []`; `sections_degraded: list[str] = []`; `data_available: bool = True`; `degraded: bool = False`.
- `what_changed`: `total_verified: int = 0`, `total_centroid_updates: int = 0`, `top_shifts: list[TopShift] = []`, `iks_delta: float = 0.0`.
- `what_discovered`: `attack_chains_detected: int = 0`, `chain_summaries: list[str] = []`, `new_entities: {users: int = 0, assets: int = 0, threat_indicators: int = 0}`, `graph_growth: {nodes_added: int = 0, relationships_added: int = 0}`.
- `what_knows`: `iks_current: float = 0.0`, `categories_calibrated: int = 0`, `categories_total: int = 6`, `health_status: str = "UNAVAILABLE"`, `operational_knowledge_status: str = ""`, `pre_activation: bool = False`, `learning_enabled: bool = False`, `learning_enabled_available: bool = True`, `health_source: str = ""`, `status_reason: str = ""`, `conservation_narrative: str = ""`.
- `metrics`: alerts_total, decisions_verified, campaigns_detected are integers with default 0; iks_current is float with default 0.0.
- Section records remain heterogeneous: common title/content strings; health section adds status string, verified_count/correct_count integers, q/theta_min numbers; learned section adds iks number, decision_count integer, strongest_categories array of name/accuracy records, weakest_category object plus `weakest_category_available` boolean; recommendations section adds items array of type/category/message string records. Missing optional members may be omitted; no new null substitution.

PDF stays `application/pdf` bytes, not a JSON wrapper. Render a clear partial-data warning listing unavailable sections. Governance report's existing evidence object should retain `sections_degraded`/availability and mark the affected transparency section ATTENTION rather than unconditional READY. This does not certify legal compliance or change unrelated article evidence.

**Downstream consumers:**

- `soc.py:3586` tab helper copies headline, sections, changes, discoveries, knows; loses metadata. Must merge it.
- `soc.py:3786,3804` tab dispatch/wrapper forwards content; no extra change except coverage. No frontend/src caller of `/soc/tab/{n}/content` was found; this is an evaluation/export surface.
- `soc.py:1702` / `models/responses.py:279` live narrative endpoint/model: **must preserve flags through serialization**.
- `soc.py:1717` PDF: reads narrative fields to render report; ignores flags. Must visibly label partial output.
- `services/governance_report.py:142,175,227` collects narrative then selects headline/changed/discovered/knows, discarding flags and setting Art 13 READY. Must propagate partial evidence status.
- `ExecutiveNarrativeTab.tsx:83,428,479,534` — actual live consumer reads headline, changed/discovered/knows, metrics, sections, generated_at/pdf_available; no degraded metadata in interface. Must warn on unavailable sections and avoid interpreting defaults as measured facts. It also links PDF (514) and displays governance summary/report (interfaces at 94/110), so downstream degraded reports must remain usable.
- `ContinuityPanel` is mounted by the executive tab but fetches separate learning-state/support endpoints; SOC-01 fixes its support display independently.

**Tests to update:**

- `test_ss14_reports_analytics_degraded.py:64` only asserts `sections_degraded` is a list; it passes even if empty after every read fails. Assert specific failed section names and HTTP preservation.
- `test_soc_degraded_paths.py:60` stubs narrative as `{}` and fails other dependencies; it does not exercise the lost narrative metadata. Add a nonempty degraded narrative with healthy local dependencies and assert aggregate unavailable.
- Healthy `_tab5_content` tests throughout `test_tab_content.py` (notably 126/190/392/461/502/579/692/792/866/901/937) keep current text/claim/section expectations. They contain no requirement to discard flags. Add explicit empty degraded_fields/available assertions for controlled healthy dependencies.
- `test_executive_narrative.py:96,113,123` tests existing HTTP keys/types, not flag preservation. Add failed-section HTTP assertions; keep numeric types. PDF byte test at 373 needs a partial-PDF content assertion in addition to a PDF signature.
- `test_governance_report.py:178,203,215` healthy evidence/summary/endpoint tests remain valid. Add a partial-narrative case that cannot satisfy unconditional READY.

**New tests needed:** each of the 11 recorded section keys propagates independently; mixed local+narrative failures union correctly; false aggregate on partial response; no null replacements; Pydantic model retains metadata; partial PDF and governance warning; successful local IKS cannot clear unrelated failure; real Executive tab renders partial state.

**Fix pseudocode:**

```text
narrative = await build_narrative(); missing = sorted(set(narrative.sections_degraded))
content = compose_existing_content(narrative); content.sections_degraded = missing
content.degraded_fields = union(local_failures, ["narrative." + key for key in missing])
serialize_declared_flags_and_render_partial_warnings(content, narrative, pdf, governance)
```

**Risk:** Fixing the tab helper alone misses the actual UI endpoint. Merely annotating booleans is insufficient when the response model filters fields or downstream PDFs/governance summaries omit them.

### SOC-13 — Mark unavailable overall IKS and dependent contributions

**Files to change:**

- `backend/app/services/balance_sheet.py` — `_safe_overall_iks`, `LearningBalanceSheet`, contribution assembly and timeline integration; `_safe_epistemic_state` for the required DV-06 aggregate-availability correction.
- `backend/app/routers/framework_router.py` — balance-sheet HTTP wire normalization for existing optional fields.
- `frontend/src/components/tabs/CompoundingTab.tsx` — type and unavailable IKS/ceiling display.
- `backend/tests/test_balance_sheet.py`, `backend/tests/test_ss14_reports_analytics_degraded.py`.

**Response shape contract:**

`framework_router.py:803` has no response_model/exclude_none. Handler currently returns `asdict(await generate_balance_sheet(...))`. LearningBalanceSheet is a dataclass. `_safe_overall_iks` must return internal absence on failed/unavailable score, not 0.0; report assembly converts it to numeric default with a flag before multiplication/rounding.

- `categories: list[CategoryBalance] = []` (normally all six configured categories).
- `overall_iks: float = 0.0`; `iks_available: bool = True`.
- `health_status: str = "unavailable"`; `overall_ceiling: float = 0.0`; `ceiling_available: bool = True`.
- `summary: object`: categories_at_expert/categories_at_learning/categories_at_novice are int = 0; strongest_category/weakest_category/recommendation are str = "".
- `generated_at: str = ""`; `total_verified: int = 0`; `notes: list[str] = []`; `sources: dict[str, str] = {}`.
- `centroid_drift_available: bool = True`; `auto_approve_available: bool = True`; `timeline_available: bool = True`; `epistemic_state_available: bool = True`; `data_available: bool = True`; `degraded: bool = False`.
- Category fields: `category: str = ""`, `epistemic_band: str = ""`, `verified_count: int = 0`, `centroid_drift: float = 0.0`, `auto_approve_rate: float = 0.0`, `accuracy: float = 0.0`, `accuracy_note: str = ""`, `iks_contribution: float = 0.0`, `iks_contribution_available: bool = True`, `ceiling_estimate: float = 0.0`, `ceiling_available: bool = True`, `status: str = "insufficient_data"`.

When overall IKS is unavailable, contributions remain numeric zero with false contribution availability. Keep counts and independent measurements. For DV-06, `_safe_epistemic_state` must retain an internal failure sentinel rather than an ordinary empty tuple; assembly sets `epistemic_state_available=false`, keeps count/map defaults typed, and uses an unavailable recommendation instead of recommending action from a fabricated novice population. Contribution availability requires both IKS and its population to be available. Do not relabel independent conservation health as GREEN or paused because IKS failed. `data_available` aggregates the explicitly tracked reads and an unavailable learning-health status; it must not silently advertise completeness for untracked dependencies.

Keep structural ceiling helpers/dataclass internal absence if needed; normalize on the HTTP boundary and use availability in the UI. Preserve correct pre-activation recommendation semantics. This is why internal cold-start ceiling tests need not be rewritten merely to meet the wire contract.

**Downstream consumers:**

- `balance_sheet.py:218,244,306` — helper result is multiplied and rounded; must narrow before arithmetic. Category contributions depend on overall IKS and verified population.
- `balance_sheet.py:225,232` — timeline dependency changes with SOC-03. Use explicit timeline section availability; do not mark retained history unavailable merely because its separate current IKS failed.
- `framework_router.py:808` — serializes every dataclass field; no Pydantic field declaration necessary here. Wire normalization must not drop new flags.
- `frontend/src/lib/api.ts:323` — transport only.
- `CompoundingTab.tsx:113,124,991,1204,1984` — reads categories, overall_iks, health_status, ceiling, summary, generated_at, verified counts, notes/sources; it renders `(overall_iks ?? 0).toFixed(1)` with no IKS flag. **Must show unavailable IKS, retain other rows, and not treat zero contributions as measured.**
- `CompoundingTab.tsx:1209,1976,2012,2030` uses ceiling non-null presence. Must switch to ceiling flags when normalizing absent ceilings at the wire boundary.
- No other production caller of `generate_balance_sheet` or `_safe_overall_iks` was found.

**Tests to update:**

- `test_balance_sheet.py:114` positive-score test is a healthy case, not outage coverage. Preserve it and assert true availability.
- `test_balance_sheet.py:208` stubs the entire generator; the test cannot verify helper-to-report failure propagation. Add an endpoint case with the real generator and only the intended IKS failure injected.
- That endpoint test's `overall_ceiling is None` assertion at line 243 becomes zero plus `ceiling_available=false` under the full no-null wire contract. **Do not change** internal cold-start ceiling assertion at line 279, or healthy helper absence tests.
- `test_balance_sheet.py:254` fake_visible_iks returns a legitimate 0.0. Do not reclassify it as failed; add a separate helper-absence case.
- Existing SS-14 drift/auto-approve/timeline helper tests do not cover overall IKS; retain them and add focused coverage.

**New tests needed:** helper raises; helper returns absence; healthy measured zero; positive IKS; contributions zero+unavailable on failed IKS or population; separate epistemic-read failure retains measured IKS but marks counts/contributions/recommendation unavailable; HTTP serialization retains bool flags and types; independent drift/auto/timeline preserved; partial SOC-03 timeline interaction; UI unavailable score and absent ceiling series.

**Fix pseudocode:**

```text
raw_iks = await _safe_overall_iks(...)  # returns absence and logs on failure
iks_available = raw_iks is not None; overall_iks = raw_iks if iks_available else 0.0
build_categories(contribution=measured_share_or_zero, iks_contribution_available=iks_available and population_available)
return report_with_typed_values_and_independent_availability_flags()
```

**Risk:** Converting before recording availability loses the distinction permanently. A flag only on overall IKS leaves downstream derived contributions misleading; using truthiness marks a valid zero unavailable.

## Missed Findings

Eight additional defects were confirmed during this trace beyond the eight requested finding boundaries. These are source findings, not newly executed fault probes. Consumer repairs tightly required by the specified fixes are included above; independent follow-ups are explicitly identified.

| ID | Severity | Evidence and issue | Disposition |
| --- | --- | --- | --- |
| DV-01 | P1 | `services/investigation_comparators.py:146` admits failed pattern evidence into all four multi-read comparator policies without checking availability; `_result` reports ordinary budget exhaustion. | Include with SOC-04. Fixing only InvestigationLoop leaves the shared evidence path inconsistent. |
| DV-02 | P2 | `routers/triage.py:3491` and `routers/explain.py:22` turn factor-service unavailable into not-found; alert-type lookup exceptions can become 500. A healthy missing alert is a different case. | Include with SOC-05's helper failure classification. |
| DV-03 | P2 | `models/responses.py:279` lacks sections_degraded, so `soc.py:1698` filters it out of the actual executive HTTP endpoint even though the service produced it. | Include with SOC-10. This is separate from the sweep's tab-helper loss. |
| DV-04 | P2 | `soc.py:1717` PDF and `services/governance_report.py:227` select narrative facts without metadata; Art 13 is unconditionally READY. | Include narrow warning/status propagation with SOC-10. |
| DV-05 | P2 | `services/executive_narrative.py:486` catches failed fallback `compute_iks_v2` with bare pass at 491; line 643 maps unavailable visible IKS to zero without adding iks_fallback. Thus even correctly forwarded sections_degraded can omit the IKS failure. | Recommended small prerequisite in SOC-10: record both attempted failure forms. Keep successful drift-derived IKS intact. |
| DV-06 | P2 | `services/balance_sheet.py:100` catches snapshot RuntimeError and returns empty epistemic state/zero verified population without a flag; generator then reports novice/zero counts and computes recommendations. | Include the narrow epistemic_state_available propagation with SOC-13 because this design adds aggregate data_available. Mark population-dependent contributions/recommendations unavailable too. This extends the original IKS-only fix and must be tested separately. |
| DV-07 | P2 | `services/time_machine.py:92` skips SnapshotCorruptError rows with only a warning; list/timeline omit those checkpoints without reporting partial history. | Separate follow-up: expose skipped/corrupt checkpoint count and partial-history status. Do not silently fold corrupt data into the IKS-unavailable case. |
| DV-08 | P2 | `soc.py:4207` calls raw centroid export before the optional IKS catch; `gae_state.py:886` performs an uncaught bootstrap read. A graph outage there never reaches the proposed typed IKS fallback. | Explicit follow-up for required-bootstrap failure policy (e.g. deliberate 503). SOC-02 regression must isolate an IKS failure after a successful raw export; do not assert it solves whole-graph outages. |

The sweep's other SOC-07/08/09/11/12/14/15/16/17/18/19/20 findings remain separately tracked; they are not silently marked fixed by this design. In particular, the primary campaign timeline and the centroid time-machine timeline are different endpoints.

## Fixture Rules

- Reuse `backend/tests/conftest.py:58` `memory_store`: a real `InMemoryGraphStore(domain="soc")` for store API state tests.
- Reuse `age_graph` (`conftest.py:65`) / `soc_stress_test_graph` (`:92`) for query semantics requiring AGE. An in-memory store is not automatically an async Cypher `run_query` implementation; do not pretend it is interchangeable.
- Reuse `soc_triage_harness` (`conftest.py:127`, implementation `backend/tests/support/soc_triage_harness.py`) and its real memory/AGE ownership pattern for Decision/outcome read-back. Confirm the execute path's raw Cypher support before selecting the memory variant; use AGE for that integration when required.
- Reuse real `SOCDomainConfig().build_profile_scorer()` and the controlled factor-provider seams in `test_investigation_loop.py:41,84,93`. Query failure injection is a legitimate error-path double; do not replace all healthy graph behavior with a MagicMock merely to make a route return 200.
- Reuse snapshot payload shape from `test_time_machine.py:11`, preserving 6x4x6 tensor shape, IDs, timestamps, and step counts. Ensure the IKS failure test has nonempty checkpoint history; otherwise it can pass while discarding nothing.
- Reuse initialized export setup from `test_centroid_export.py`; preserve raw-helper absence tests and exercise mounted endpoints to catch response-model filtering.
- Reuse targeted `BrokenGraph`/raising AsyncMock patterns from SS tests only to force the actual failing dependency. Assert it was called; make all unrelated dependencies healthy. Do not convert a failed test into a skip or inspect only key existence.
- **Must not modify shared fixture infrastructure** (`backend/tests/conftest.py`, AGE DSN/skip/live-server lifecycle), campaign fixture ownership, or global seed data to satisfy these fixes. Their sweep findings are separate work.
- **Must not modify planted Stage-1 scenario/ground-truth fixtures**, VLD geometry/aggregation thresholds, canonical SOC factor/category/action configuration, bootstrap centroid data, or frozen SDK investigation/scoring code. Successful fixture evidence remains successful; adding an explicit failure case is not permission to neutralize every test vector.
- Existing healthy values/text checks remain. Update only identified wrong contracts: unavailable support limited to measured colors; null HTTP IKS; truthy failed evidence; whole-timeline absence for IKS-only failure; and HTTP null ceilings if applying the specified complete wire normalization. Internal absence tests are not wrong contracts.

## Interaction Matrix

Row -> column. Diagonal is NONE (self). Use the strongest applicable relation; SHARED_FILE means backend or required frontend edits overlap without data dependency. SHARED_PATH means a common upstream or composed presentation path, not one endpoint invoking another.

| P1 | SOC-01 | SOC-02 | SOC-03 | SOC-04 | SOC-05 | SOC-06 |
| --- | --- | --- | --- | --- | --- | --- |
| SOC-01 | NONE | SHARED_FILE | SHARED_FILE | NONE | NONE | NONE |
| SOC-02 | SHARED_FILE | NONE | SHARED_PATH | NONE | NONE | NONE |
| SOC-03 | SHARED_FILE | SHARED_PATH | NONE | NONE | NONE | NONE |
| SOC-04 | NONE | NONE | NONE | NONE | SHARED_FILE | NONE |
| SOC-05 | NONE | NONE | NONE | SHARED_FILE | NONE | NONE |
| SOC-06 | NONE | NONE | NONE | NONE | NONE | NONE |

- 01/02 share `soc.py` and RuntimeEvolutionTab; 01/03 share RuntimeEvolutionTab. No support response is consumed by export or timeline.
- 02/03 both consume `compute_iks_v2` and share RuntimeEvolutionTab; repairing a response does not automatically repair the other's response.
- 04/05 share `routers/triage.py` and the triage screen, but **neither feeds the other**. No CAUSAL pair among these six was found. Do not manufacture a direction solely because both mention factor vectors.
- Outside the requested 6x6: **SOC-03 -> SOC-13 is CAUSAL** through `_safe_timeline` and timeline availability. SOC-01/SOC-10 share `models/responses.py`, `soc.py`, and executive presentation; SOC-02/SOC-10 share `soc.py`; SOC-13 shares IKS dependencies with 02/03/10. These are reasons to keep bundled P2s in the first prompt and execute prompts sequentially.

## Recommended Prompt Split

**Prompt A — response contracts and required display consumers:** SOC-01, SOC-02, SOC-03, SOC-06, SOC-10, SOC-13; include DV-03/04/05 as required SOC-10 completion and DV-06's narrow epistemic availability propagation for an honest aggregate balance-sheet data_available flag. DV-07/08 remain separately tracked follow-ups, not assumed fixed.

Execution/checkpoint order for the implementer (none executed in this design task):

1. Implement SOC-01 model + handler + both displays. Run targeted support and HTTP roundtrip tests; confirm unavailable flags survive serialization and no unmeasured GREEN.
2. SOC-02 numeric IKS and export normalization + UI. Run export/degraded tests for JSON, summary, healthy zero, and isolated IKS outage; retain internal helper absence tests.
3. SOC-03 partial timeline, then SOC-13 report integration and associated UI flags. Run time-machine and balance-sheet tests together, including checkpoint-success/IKS-failure and inverse cases; verify chart presence checks after wire normalization.
4. SOC-06 independently test primary-success/secondary-failure, sentinel, malformed and successful-zero branches through HTTP.
5. SOC-10 tab merge + dedicated model + direct UI + PDF/governance propagation. Run narrative/tab/governance tests and the strengthened SS-14 section test; include missing IKS catch-site coverage and exact degraded-key assertions.
6. Run mypy on changed backend files, frontend TypeScript, and focused frontend contract/render tests. Run the full SOC backend suite and compare against the **recorded 2,669/0/0** baseline. Do not pass by weakening fixtures or accepting new skips. Record actual counts and any known independent failures.

**Prompt B — evidence admission and action-write safety:** SOC-04 and SOC-05; include DV-01 and DV-02. Execute after Prompt A so shared-file and UI edits are reviewed against one settled baseline.

1. Implement failed pattern payload, loop admission/unchanged trace, defensive adapter filter, result flags, and comparator parity. Check first failure and later failure, real factor provider plus controlled provider, both aggregation modes; preserve happy geometry tests and planted/oracle contracts.
2. Propagate degraded investigation metadata through ordinary HTTP and InvestigationPanel; assert no writes/learning. Do not confuse a planted-route pass with ordinary AGE coverage.
3. Implement execute factor preconditions with narrow failure classification and update factor GET/explanation consumers. Verify no writes/audit/events/receipt/alert resolution when reads fail but writes would succeed, then verify healthy persisted-vector read-back and outcome handling.
4. Run focused investigation/rho/multihop, execute/factor, audit and outcome tests. Run changed-file mypy and frontend typecheck/render coverage. Then full SOC backend validation against Prompt A's measured baseline. No change to conservation/freeze/spike or accepted-outcome semantics is authorized.

**Completeness check:** all six P1s and both bundled P2s have explicit response/model contracts, consumer actions, wrong-contract/vacuous-test notes, new tests, pseudocode, and risks above; all 36 matrix cells are filled. The split is justified by actual call paths, not inferred from filenames. This document deliberately distinguishes a specified future test from a test run: **no validation commands were executed for this design review.**
