# Diagnostic Report - D-04 (OLS CUSUM Reset) + D-08 (DK Normalization)

## Authority / Source-of-Truth Rule

Implementation overrides design docs. Design documents provide intent, terminology,
architecture, and historical rationale, but they are not proof of implemented
behavior. Live source code defines current behavior, and live tests validate the
behavior that is expected today.

When design docs and code disagree, the discrepancy is a reportable gap, not an
automatic fix. This report labels those discrepancies as `CODE-DOC CONFLICT` or
`DOC INTENT ONLY` and requires an explicit future implementation decision before
any code change.

## Executive Summary

New design documents were found and reviewed:

- `graph-attention-engine-v50/docs/design/gae_design_v10_8.md`
- `graph-attention-engine-v50/docs/design/math_synopsis_v15.md`
- `gen-ai-roi-demo-v4-v50/backend/docs/design/soc_copilot_design_v5_8.md`

The originally requested issue-index path
`gen-ai-roi-demo-v4-v50/backend/design_issues_v1.md` is absent. The file
`gen-ai-roi-demo-v4-v50/backend/design_issues.md` exists, identifies itself as
"Design Issues v1 - Decision Index," and is used here as the issue-index source
for D-04 and D-08. This issue-index source records D-04 as Option B, reset on
GREEN conservation status, and D-08 as Option A, always normalize DK weights
(`design_issues.md:1-4`, `design_issues.md:19-28`). Implementation still
overrides this design intent.

D-04 update: the new docs clarify that GREEN conservation status means learning
resume after AMBER/RED pause, and that conservation `q` is rolling verified
accuracy. They do not fully define "reset on GREEN" for OLS CUSUM. Live code
still shows `OLSMonitor` resets CUSUM only after an alarm, and SOC `get_ols_status`
still recreates a monitor and replays OLS history per request. Prior D-04
implementation conclusion is unchanged: reset-on-GREEN is not implemented.

D-08 update: the new docs clarify a raw-vs-normalized distinction. Sigma-derived
`DiagonalKernel.weights` are max-normalized for scoring, while `raw_weights`
preserve true `1/sigma^2` for eta_eff/enrichment ROI. The math synopsis also
renames learned DK weights as discriminative precision weights, not inverse
variances. Live code matches max-normalization on the `sigma` path, but not a
blanket "always normalize" rule: direct `weights=...`, learned `_dk_weights`,
phase-two shrinkage weights, and `get_dk_weights()` are not normalized on every
path. Prior D-08 conclusion changes from "centralize always normalize" to
"resolve the raw-vs-normalized contract before implementation."

Recommendation: D-04 and D-08 should remain separate implementation prompts.
D-08 may be implementable first if the intended accessor/scoring contract is
confirmed. D-04 should not be implemented until reset semantics are explicitly
defined.

Confidence is high for current source behavior. Remaining uncertainty is
implementation intent detail: D-04 reset semantics are still ambiguous despite
the Option B decision, and D-08 external accessor semantics are not fully
specified despite the Option A normalization decision.

## 1. D-04: OLS CUSUM Reset

### 1.1 Implementation Location

`graph-attention-engine-v50/gae/convergence.py::OLSMonitor` is the GAE OLS CUSUM
implementation. It is a stateful CUSUM-based monitor with plateau-snapshot
baseline, not ordinary least-squares regression. Source evidence:
`gae/convergence.py:809-850` defines the monitor and CUSUM equations;
`gae/convergence.py:852-872` initializes history, baseline, threshold, CUSUM,
and warning state.

`gen-ai-roi-demo-v4-v50/backend/app/framework/ols_status.py::get_ols_status` is
the SOC dashboard OLS status computation. It is stateless recomputation from
provided OLS history: `app/framework/ols_status.py:16-21` defines the function,
and `app/framework/ols_status.py:67-72` creates a fresh `OLSMonitor()` and
replays every OLS value.

`graph-attention-engine-v50/gae/convergence.py::ConservationMonitor` is a
separate conservation/quality monitor. It maintains Layer 2 CUSUM state and
Layer 1 conservation status at `gae/convergence.py:672-693`, and status
propagation occurs in `gae/convergence.py:698-713`.

`gen-ai-roi-demo-v4-v50/backend/app/services/learning_health.py::LearningHealthMonitor`
computes SOC learning health and conservation status. It extracts alpha, q, and
V from learning history at `app/services/learning_health.py:57-109`, then
computes `CALIBRATING`, `GREEN`, `AMBER`, or `RED` in
`app/services/learning_health.py:173-244`.

Classification:

- `IMPLEMENTED`: stateful GAE OLS CUSUM exists in `OLSMonitor`.
- `IMPLEMENTED`: SOC dashboard recomputes OLS status by replaying history.
- `IMPLEMENTED`: conservation status pause/resume exists in `ProfileScorer`.
- `DOC INTENT ONLY`: `design_issues.md:1-4` records D-04 as "Option B -
  reset on GREEN conservation status."
- `FUTURE DECISION`: `design_issues.md:11-17` leaves the exact reset target
  open: accumulator, alarm state, red-day/consecutive counter, replay
  epoch/dashboard-visible history, or a combination.

### 1.2 Current Reset Behavior

`OLSMonitor` state includes:

- `ols_history`
- `baseline_ols`
- `baseline_frozen`
- `_h`
- `cusum`
- `yellow_warning`
- `yellow_reason`

Evidence: `gae/convergence.py:863-872` initializes these fields.

Current reset behavior:

- `IMPLEMENTED`: `OLSMonitor` resets `cusum` after an alarm. Evidence:
  `gae/convergence.py:949-958` accumulates post-plateau CUSUM, sets warning
  fields when `cusum > _h`, and then sets `self.cusum = 0.0`.
- `IMPLEMENTED`: SOC dashboard state resets through instance recreation.
  Evidence: `app/framework/ols_status.py:67-72` creates a fresh monitor and
  replays `ols_history`.
- `NOT IMPLEMENTED`: no source evidence shows `OLSMonitor` resetting on GREEN
  conservation status.
- `NOT IMPLEMENTED`: no source evidence shows GREEN clearing OLS alarm state,
  red-day history, OLS replay epoch, dashboard-visible state, or rolling windows.

The current component is mixed stateful/stateless by layer: GAE `OLSMonitor` is
stateful, while SOC `get_ols_status()` is stateless recomputation from history.

### 1.3 Conservation Status Integration

Design-doc evidence:

- `design_issues.md:1-4` identifies the file as the Design Issues v1 decision
  index and records D-04 as "Option B - reset on GREEN conservation status."
- `design_issues.md:11-17` states that "reset on GREEN" still needs exact
  definition and lists candidate reset targets: CUSUM accumulator, alarm state,
  red-day/consecutive counter, replay epoch/dashboard-visible history, or a
  combination.
- `gae_design_v10_8.md:588-594` describes conservation integration where
  AMBER/RED pause and GREEN resumes learning.
- `gae_design_v10_8.md:751-765` defines AMBER/RED trigger conditions and says
  the GREEN resume condition is rolling accuracy above the AMBER threshold for
  at least 100 consecutive decisions.
- `gae_design_v10_8.md:1498-1537` defines `check_conservation()` and states
  GREEN/AMBER/RED are based on `alpha * q * V`, with q as rolling verified
  accuracy over the last 400 decisions.
- `soc_copilot_design_v5_8.md:2772-2784` separates the conservation-law Circuit
  Breaker from the Flywheel Health Monitor and lists CUSUM on OLS as
  `OLSMonitor`, h=5.0, plateau-snapshot baseline.
- `soc_copilot_design_v5_8.md:2821-2845` identifies GAE `gae/convergence.py`
  as the OLSMonitor location and describes `cusum_alarm` output.

Live implementation comparison:

- `IMPLEMENTED`: SOC computes rolling q from verified learning history.
  Evidence: `app/services/learning_health.py:57-109`.
- `IMPLEMENTED`: SOC computes current health status and red-day fields.
  Evidence: `app/services/learning_health.py:173-244`.
- `IMPLEMENTED`: `ProfileScorer.set_conservation_status()` pauses on AMBER/RED
  and resumes on GREEN. Evidence: `gae/profile_scorer.py:698-717`.
- `NOT IMPLEMENTED`: `ProfileScorer.set_conservation_status()` does not reset
  OLS CUSUM or OLS alarm fields. Evidence: `gae/profile_scorer.py:713-717`
  only stores status and toggles `_paused_by_conservation`.
- `NOT IMPLEMENTED`: `ConservationMonitor.update_conservation_signal()` does
  not reset OLS CUSUM. Evidence: `gae/convergence.py:698-713` stores status and
  forwards it to scorer only.

Code-doc conflict:

- `CODE-DOC CONFLICT`: docs describe a GREEN resume condition requiring at
  least 100 consecutive decisions above the AMBER threshold
  (`gae_design_v10_8.md:765`). The live method read here,
  `gae/profile_scorer.py:698-717`, immediately resumes when called with
  `GREEN`; the 100-decision gate is not visible in that method.
- `DOC INTENT ONLY`: docs describe conservation q computation and display
  architecture, but they do not define OLS CUSUM reset-on-GREEN semantics.

### 1.4 Proposed Change

Diagnostic recommendation only; no implementation was performed.

"Reset on GREEN" semantics are still ambiguous. The exact remaining question is:

Does reset on GREEN mean reset CUSUM accumulator only, alarm state, red-day
counter, replay epoch/dashboard-visible state, or a combination?

Based on live code, the least invasive interpretation would be a transition-only
reset of transient OLS alarm state:

- reset `OLSMonitor.cusum`
- clear `OLSMonitor.yellow_warning`
- clear `OLSMonitor.yellow_reason`
- preserve `baseline_ols` and `baseline_frozen`
- preserve `ols_history` unless a new replay epoch is explicitly required

This is a `FUTURE DECISION`, not an implemented behavior. If SOC dashboard reset
must be visible, a replay epoch or reset marker would also be needed because
`get_ols_status()` currently reconstructs the monitor from all OLS history on
every request.

Future implementation decision points:

- `graph-attention-engine-v50/gae/convergence.py::OLSMonitor`: likely location
  for an explicit reset method if stateful reset is required.
- `graph-attention-engine-v50/gae/convergence.py::ConservationMonitor.update_conservation_signal`:
  possible trigger point if conservation status owns transition detection.
- `graph-attention-engine-v50/gae/profile_scorer.py::set_conservation_status`:
  possible trigger point only if scorer pause/resume owns the transition.
- `gen-ai-roi-demo-v4-v50/backend/app/framework/ols_status.py::get_ols_status`:
  only if SOC dashboard replay needs GREEN-aware segmentation.

### 1.5 Files and Tests Affected

Future source files, if D-04 is implemented:

- `graph-attention-engine-v50/gae/convergence.py`
- `graph-attention-engine-v50/gae/profile_scorer.py`
- `gen-ai-roi-demo-v4-v50/backend/app/framework/ols_status.py`
- `gen-ai-roi-demo-v4-v50/backend/app/routers/triage.py`, only if SOC wiring
  becomes the GREEN transition trigger

Existing coverage to update or extend:

- GAE convergence tests touching CUSUM/OLSMonitor.
- SOC `backend/tests/test_ols_status.py`.
- SOC `backend/tests/test_learning_health.py`.
- SOC conservation enforcement/extended tests if GREEN transition wiring changes.

Regression risks:

- Resetting baseline or OLS history can alter plateau detection and alarm timing.
- Resetting `cusum` without clearing warning fields can leave stale alarm state.
- SOC replay can hide stateful reset behavior unless reset epochs are persisted
  or represented in OLS history.
- Adding status arguments or response fields to OLS endpoints can affect API
  consumers.

## 2. D-08: DK Normalization

### 2.1 Implementation Location

Issue-index evidence:

- `design_issues.md:19-20` records D-08 as "Option A - always normalize DK
  weights."
- `design_issues.md:27-28` states implementation intent: centralize DK
  normalization in GAE and explicitly decide whether external accessors return
  raw weights, normalized weights, or both.

`graph-attention-engine-v50/gae/kernels.py::DiagonalKernel` implements DK
construction, distance, gradient, raw weights, and sigma refresh.

Evidence:

- `gae/kernels.py:132-186` implements constructor behavior for `sigma` and
  direct `weights`.
- `gae/kernels.py:188-202` computes weighted squared L2 distance.
- `gae/kernels.py:204-227` computes gradient as `self.weights / w_max`.
- `gae/kernels.py:244-253` exposes raw inverse-variance weights.
- `gae/kernels.py:255-278` refreshes sigma-derived weights through a new kernel.

`graph-attention-engine-v50/gae/profile_scorer.py` consumes learned DK weights:

- `gae/profile_scorer.py:450-475` uses phase-two `w_tilde` via
  `DiagonalKernel(weights=w_tilde)`.
- `gae/profile_scorer.py:1003-1007` returns learned DK weights.
- `gae/profile_scorer.py:1009-1024` re-estimates and stores learned DK weights.

`graph-attention-engine-v50/gae/dk_estimator.py` estimates learned DK weights:

- `gae/dk_estimator.py:64-70` defines candidate weights including values above
  1.0.
- `gae/dk_estimator.py:129-198` initializes, optimizes, and returns weights
  without normalization.

`graph-attention-engine-v50/gae/shrinkage.py::compute_effective_weights` blends
learned weights with neutral all-ones weights:

- `gae/shrinkage.py:77-81` returns `alpha * w_dk + (1.0 - alpha)`.

Classification:

- `DOC INTENT ONLY`: `design_issues.md:19-20` records D-08 as "Option A -
  always normalize DK weights."
- `FUTURE DECISION`: `design_issues.md:27-28` requires an explicit
  raw-vs-normalized external accessor decision.
- `IMPLEMENTED`: sigma-derived DK weights are max-normalized.
- `IMPLEMENTED`: raw inverse-variance weights are exposed.
- `IMPLEMENTED`: learned DK weights can be raw/discriminative and above 1.0.
- `NOT IMPLEMENTED`: blanket always-normalize behavior across all DK paths.

### 2.2 Current Normalization Behavior

Design-doc evidence:

- `design_issues.md:19-20` records D-08 as "Option A - always normalize DK
  weights."
- `design_issues.md:27-28` states the implementation intent to centralize DK
  normalization in GAE and decide whether external accessors return raw weights,
  normalized weights, or both.
- `soc_copilot_design_v5_8.md:592-595` explicitly separates
  `DiagonalKernel.raw_weights` as true `1/sigma^2` for eta_eff/enrichment ROI
  from `DiagonalKernel.weights` as pre-normalized `[0,1]` for scoring.
- `math_synopsis_v15.md:2205` states DK weights are discriminative precision
  weights estimated by coordinate descent for accuracy, not inverse variances.
- `math_synopsis_v15.md:2215` defines shrinkage weights as
  `w_tilde = alpha * w_DK + (1-alpha)`.
- `math_synopsis_v15.md:2226-2236` defines T1 profile state as DK precision
  weights and says deployed DK weights are not inverse variances.
- `soc_copilot_design_v5_8.md:6270-6277` repeats the shrinkage equation and
  says DK precision weights replace P28 weights in Phase 2.
- `soc_copilot_design_v5_8.md:6366-6387` describes phase-two factor weights as
  classification-optimal importance scores and gives examples such as
  `w_DK=3.0`.

Live implementation comparison:

- `IMPLEMENTED`: `DiagonalKernel(sigma=...)` uses max-normalization:
  `W = 1.0 / sigma ** 2`; `self.weights = W / self._W_baseline_max`.
  Evidence: `gae/kernels.py:183-186`.
- `IMPLEMENTED`: `DiagonalKernel(weights=...)` stores direct weights without
  normalization. Evidence: `gae/kernels.py:161-173`.
- `IMPLEMENTED`: `compute_distance()` uses stored weights directly. Evidence:
  `gae/kernels.py:188-202`.
- `IMPLEMENTED`: `compute_gradient()` normalizes by current max at use time.
  Evidence: `gae/kernels.py:204-227`.
- `IMPLEMENTED`: `raw_weights` returns true `1/sigma^2`. Evidence:
  `gae/kernels.py:244-253`.
- `IMPLEMENTED`: learned DK estimator returns candidate values directly, with
  possible weights above 1.0. Evidence: `gae/dk_estimator.py:64-70`,
  `gae/dk_estimator.py:129-198`.
- `IMPLEMENTED`: phase-two scoring uses unnormalized `w_tilde` through
  `DiagonalKernel(weights=w_tilde)`. Evidence: `gae/profile_scorer.py:450-475`
  and `gae/shrinkage.py:77-81`.
- `IMPLEMENTED`: `get_dk_weights()` returns raw stored category weights.
  Evidence: `gae/profile_scorer.py:1003-1007`.

Known formula:

- For sigma-derived DK weights, the normalization formula is known:
  max-normalization of inverse variance,
  `(1 / sigma**2) / max(1 / sigma**2)`.
- This is not sum-to-one normalization and not L2 normalization.

Skipped normalization paths:

- direct `DiagonalKernel(weights=...)`
- `_dk_weights` stored by `ProfileScorer.reestimate_dk()`
- `ProfileScorer.get_dk_weights()`
- `compute_effective_weights()`
- phase-two `DiagonalKernel(weights=w_tilde)`

Code-doc conflict / intent classification:

- `CODE-DOC CONFLICT` if D-08 is interpreted as "always normalize every DK
  value before use or exposure": live code does not do that.
- `DOC INTENT ONLY` for Tab 3/Tab 4 DK display described in the SOC design doc;
  the searched live frontend source did not contain direct `dk_weights`,
  `get_dk_weights`, `DiagonalKernel`, or `LearningStatePanel` consumers.
- `FUTURE DECISION`: the docs distinguish raw sigma weights, normalized sigma
  scoring weights, and learned discriminative DK weights. The accessor contract
  for raw-vs-normalized learned DK output remains undecided.

### 2.3 Consumers of DK Weights

GAE consumers:

- `ProfileScorer.score()` consumes phase-two effective weights through
  `DiagonalKernel(weights=w_tilde)`. Evidence: `gae/profile_scorer.py:450-475`.
- `ProfileScorer.get_dk_weights()` exposes learned weights. Evidence:
  `gae/profile_scorer.py:1003-1007`.
- `ProfileScorer.reestimate_dk()` stores estimator output. Evidence:
  `gae/profile_scorer.py:1009-1024`.
- `DiagonalKernel.compute_distance()` uses stored weights directly. Evidence:
  `gae/kernels.py:188-202`.
- `DiagonalKernel.compute_gradient()` max-normalizes at use time. Evidence:
  `gae/kernels.py:204-227`.

SOC backend consumers:

- `gen-ai-roi-demo-v4-v50/backend/app/services/factor_analysis.py` prefers
  `kernel.raw_weights` when available, then falls back to `kernel.weights`.
  Evidence: `app/services/factor_analysis.py:20-28`.
- SOC router display computes normalized factor weights from sigma-style raw
  values. Evidence: `app/routers/soc.py:2740-2744`.
- SOC router exposes `kernel_weights` and `kernel_label` in factor/display
  output. Evidence: `app/routers/soc.py:3631-3693`.

UI/API consumers:

- `DOC INTENT ONLY`: `soc_copilot_design_v5_8.md:6281-6306` specifies a Tab 3
  LearningStatePanel with DK weight visualization and an endpoint returning
  `dk_weights`.
- `DOC INTENT ONLY`: `soc_copilot_design_v5_8.md:6330-6333` specifies Tab 4
  channel decomposition behavior.
- Live search found backend `/api/soc/learning-state` references, but no direct
  live frontend matches for `dk_weights`, `get_dk_weights`, `DiagonalKernel`, or
  `LearningStatePanel`.

Assumptions consumers appear to make:

- Sigma-derived scoring weights are normalized `[0,1]`.
- Raw inverse-variance weights remain meaningful for eta_eff/enrichment ROI.
- Learned DK weights are dimensional importance / discriminative precision
  weights and may exceed 1.0 in the design intent.

### 2.4 Proposed Change

Diagnostic recommendation only; no implementation was performed.

Normalization formula is now known for the sigma-derived DK path:
max-normalized inverse variance. Raw-vs-normalized accessor semantics remain a
future decision for learned DK weights.

Future implementation decision points:

- `graph-attention-engine-v50/gae/kernels.py::DiagonalKernel.__init__`: decide
  whether direct `weights=...` should normalize, remain raw/effective, or require
  explicit mode names.
- `graph-attention-engine-v50/gae/profile_scorer.py::get_dk_weights`: decide
  whether public learned DK output should be raw, normalized, or both.
- `graph-attention-engine-v50/gae/profile_scorer.py::reestimate_dk`: decide
  whether learned weights are stored raw only, normalized only, or as paired
  raw/normalized state.
- `graph-attention-engine-v50/gae/shrinkage.py::compute_effective_weights`:
  decide whether `w_tilde` is normalized after blending.
- `gen-ai-roi-demo-v4-v50/backend/app/services/factor_analysis.py`: decide
  whether API-facing explainability should continue preferring raw weights.
- SOC learning-state/UI code: implement only after accessor semantics are fixed.

If normalization is centralized, it should be centralized in GAE, not copied in
SOC display code. The helper should distinguish at least:

- sigma-derived raw weights: `1/sigma^2`
- sigma-derived scoring weights: max-normalized `[0,1]`
- learned discriminative DK weights: raw and/or normalized according to the
  future contract

### 2.5 Files and Tests Affected

Future source files, if D-08 is implemented:

- `graph-attention-engine-v50/gae/kernels.py`
- `graph-attention-engine-v50/gae/profile_scorer.py`
- `graph-attention-engine-v50/gae/dk_estimator.py`
- `graph-attention-engine-v50/gae/shrinkage.py`
- `gen-ai-roi-demo-v4-v50/backend/app/services/factor_analysis.py`
- `gen-ai-roi-demo-v4-v50/backend/app/routers/soc.py`, only if API payloads
  change or DK display is implemented
- frontend Tab 3/Tab 4 files only if the doc-intended DK display is implemented

Existing coverage to update or extend:

- GAE kernel tests for sigma-path max-normalization.
- GAE tests for direct `weights=...` semantics.
- GAE profile scorer tests for phase-two scoring and `get_dk_weights()`.
- SOC factor-analysis/router tests if display weights or API payloads change.

Regression risks:

- Normalizing learned weights can change distances, probabilities, confidence,
  and calibration.
- Changing direct `weights=...` semantics can break phase-two scoring where
  docs describe above-one importance weights.
- Changing `get_dk_weights()` can break future or downstream display contracts.
- Changing SOC factor analysis from raw to normalized can alter eta_eff/ROI or
  explainability outputs.

## 3. Combined Implementation Plan

### 3.1 One Prompt or Two?

Recommendation: two prompts.

D-04 and D-08 are independent and touch different subsystems. D-04 is a
conservation/OLS state-transition question. D-08 is a DK scoring/accessor
contract question.

### 3.2 Recommended Sequence

D-08 may be implementable first if the raw-vs-normalized learned DK contract is
confirmed. The sigma normalization formula is already clear, and the code paths
that skip normalization are identifiable.

D-04 should wait for an explicit reset-semantics decision. The docs clarify
GREEN as resume, but they do not define whether OLS CUSUM reset means clearing
only the accumulator, alarm state, red-day counter, replay epoch/dashboard-visible
state, or a combination.

### 3.3 Dependency Between Them

D-04 does not depend on D-08. D-08 does not depend on D-04. No shared targeted
test set was identified.

### 3.4 Estimated Test Impact

GAE targeted tests:

- D-04: convergence/OLSMonitor/conservation monitor tests.
- D-08: kernel, DK estimator, shrinkage, and profile scorer tests.

SOC backend targeted tests:

- D-04: `test_ols_status.py`, `test_learning_health.py`, conservation
  enforcement/extended tests if wiring changes.
- D-08: factor analysis and SOC router/API tests if display or payload semantics
  change.

Full suites:

- D-04: run targeted GAE/SOC tests first; full GAE and SOC backend suites are
  recommended if conservation pause/resume wiring changes.
- D-08: full GAE suite is recommended because scoring math can shift. SOC
  targeted tests should follow for API/display consumers.

Frontend/build impact:

- No frontend impact is expected from this documentation update.
- A future D-08 display implementation may require frontend build/tests if Tab 3
  or Tab 4 DK visualization is added.

## 4. Evidence Table

| Decision | Finding | Evidence | Classification | Confidence | Notes |
|---|---|---|---|---|---|
| D-04 | `design_issues_v1.md` is absent, but `design_issues.md` exists and identifies itself as Design Issues v1. | `design_issues.md:1-4` | DOC INTENT ONLY | High | D-04 decision text is Option B: reset on GREEN conservation status. |
| D-04 | D-04 reset target remains explicitly open in the issue index. | `design_issues.md:11-17` | FUTURE DECISION | High | Candidate targets are accumulator, alarm state, red-day/consecutive counter, replay epoch/dashboard-visible history, or combination. |
| D-08 | `design_issues_v1.md` is absent, but `design_issues.md` exists and identifies itself as Design Issues v1. | `design_issues.md:1`, `design_issues.md:19-20` | DOC INTENT ONLY | High | D-08 decision text is Option A: always normalize DK weights. |
| D-08 | D-08 accessor behavior remains explicitly open in the issue index. | `design_issues.md:27-28` | FUTURE DECISION | High | Issue index says to decide whether external accessors return raw weights, normalized weights, or both. |
| D-04 | GREEN is documented as learning resume, not OLS reset. | `gae_design_v10_8.md:588-594`, `:759-765` | DOC INTENT ONLY | High | Code implements immediate scorer unpause when called with GREEN. |
| D-04 | Conservation q is rolling verified accuracy. | `gae_design_v10_8.md:1498-1537`; `app/services/learning_health.py:57-109` | IMPLEMENTED | High | SOC implementation computes q from verified learning history. |
| D-04 | OLS CUSUM monitor is stateful with plateau baseline. | `gae/convergence.py:809-872`, `:929-958`; `soc_copilot_design_v5_8.md:2772-2784` | IMPLEMENTED | High | Docs and code agree on OLSMonitor identity. |
| D-04 | OLS CUSUM resets after alarm. | `gae/convergence.py:949-958` | IMPLEMENTED | High | Only accumulator reset was found. |
| D-04 | OLS CUSUM reset on GREEN is absent. | `gae/profile_scorer.py:698-717`; `gae/convergence.py:698-713`; `app/framework/ols_status.py:67-72` | CODE-DOC CONFLICT | High | Conflict applies only if D-04 decision is reset-on-GREEN. |
| D-04 | GREEN >=100-decision resume gate is not visible in scorer method. | `gae_design_v10_8.md:765`; `gae/profile_scorer.py:713-717` | CODE-DOC CONFLICT | Medium | Gate may exist elsewhere, but not in method read here. |
| D-08 | Sigma-derived DK weights are max-normalized. | `gae/kernels.py:183-186`; `soc_copilot_design_v5_8.md:592-595` | IMPLEMENTED | High | Formula is `(1/sigma^2)/max`. |
| D-08 | Raw inverse-variance weights are intentionally exposed. | `gae/kernels.py:244-253`; `soc_copilot_design_v5_8.md:592-595` | IMPLEMENTED | High | Used for eta_eff/enrichment ROI by design. |
| D-08 | Learned DK weights are discriminative precision weights, not inverse variances. | `math_synopsis_v15.md:2205`, `:2226-2236`; `soc_copilot_design_v5_8.md:6366-6387` | DOC INTENT ONLY | High | Live estimator returns coordinate-descent weights but does not encode terminology. |
| D-08 | Direct `weights=...` path skips normalization. | `gae/kernels.py:161-173` | IMPLEMENTED | High | Conflicts with blanket always-normalize interpretation. |
| D-08 | Phase-two scoring uses unnormalized `w_tilde`. | `gae/profile_scorer.py:450-475`; `gae/shrinkage.py:77-81` | IMPLEMENTED | High | May align with learned DK docs; conflicts with blanket normalization. |
| D-08 | `get_dk_weights()` returns raw learned weights. | `gae/profile_scorer.py:1003-1007` | IMPLEMENTED | High | Accessor contract remains future decision. |
| D-08 | Tab 3 DK display endpoint/panel is described in docs but not found as live frontend DK consumer. | `soc_copilot_design_v5_8.md:6281-6306`; frontend search results | DOC INTENT ONLY | Medium | Backend `/api/soc/learning-state` exists, but searched frontend lacks DK-specific consumer names. |

## 5. Open Questions

- D-04: Does reset on GREEN mean reset CUSUM accumulator only, alarm state,
  red-day counter, replay epoch/dashboard-visible state, or a combination?
- D-04: Should the reset apply to `OLSMonitor`, `ConservationMonitor`, SOC
  dashboard replay state, or more than one of these?
- D-08: Should `get_dk_weights()` expose normalized learned weights, raw learned
  weights, or both under explicit accessors?
- D-08: Should phase-two learned discriminative weights remain above-one scoring
  weights, or be max-normalized before distance computation?
- D-08: Should SOC factor analysis continue to prefer `raw_weights`, or should
  API-facing explainability use normalized weights consistently?
