# SOC C9B Diagnostic F2 - Phase Transition + DK Proof

Date: 2026-06-08
Model: gpt-5.3
Task Type: Functional runtime verification; no source code changes
Repo: `C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50`
Diagnostic Graph: `soc_graph_diag_f2`

## Executive Summary
- Verdict: PROCESS_SPLIT_OR_RESTART_DETECTED.
- Runtime import path: `C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\ci-platform\ci_platform\graph\age_graph_store.py`.
- Backend/graph status: backend reachable; async AGE readback succeeded against `soc_graph_diag_f2`.
- Target category: `credential_access`.
- Target valid outcomes: 250 requested, 230 minimum.
- Actual target outcomes: 82 verified/correct `credential_access` outcomes in AGE readback.
- Phase transition: NOT PROVEN. Final endpoint readback still reported `phase="MEAN_CONVERGENCE"` and `decisions_in_category=164`.
- L5DKWeight: 0.
- Welford: absent; no `L5DKWeight` rows existed.
- Proceed to C9B proof: NO.
- Recommended next step: rerun Diagnostic F2 from a clean graph/ID set with a longer single-process command timeout or a local runner timeout comfortably above observed runtime. Do not resume this partial `DIAG-F2-CRED` run as a pass proof.

## Preconditions
- Diagnostic E status: `DIAGNOSTIC_E_PASS` in `soc_c9b_runtime_readiness_and_5_decision_verification.md`.
- Runtime import: source `ci-platform`, not site-packages.
- Backend health: `/health` returned `{"status":"healthy","components":{"posterior_store":{"healthy":true}}}` before seeding, after each seed batch, and after the interrupted long loop.
- AGE graph: `MATCH (n) RETURN count(n) AS total` returned `[{"total": 1}]` before F2 seeding.
- Seed contract: fixed C9B credential-access shape with `alert_type="anomalous_login"`, `category="credential_access"`, `severity="critical"`, `risk_score=0.92`, `Asset.criticality="critical"`, `mfa_completed=false`, `device_fingerprint_match=false`, User/Asset nodes, and `INVOLVES`/`DETECTED_ON` context.

Prior report confirmations:
- Diagnostic E proved fresh non-referral `investigate` actions, outcomes posted, `L5Centroid > 0`, and `SHAPED_BY > 0`.
- Diagnostic E allowed proceeding to F.
- Prior diagnostics state DK proof requires 230+ valid outcomes in one target category.
- `L5DKWeight=0` in Diagnostic E was expected below the DK threshold.
- Conservation proof is separate and was not the goal of this F2 run.

## Batched Seed Data
- method: temporary scratch script `scratch/temp/diag_f2_runner.py` using async `AGEClient.run_query`.
- batch size: 25.
- count: 300 alerts.
- IDs: `DIAG-F2-CRED-0001` through `DIAG-F2-CRED-0300`.
- alert_type: `anomalous_login`.
- criticality: categorical string `critical`.
- context: each alert has User, Asset, `Alert-[:INVOLVES]->User`, and `Alert-[:DETECTED_ON]->Asset`.
- graph: `soc_graph_diag_f2`.
- health after each batch: all 12 batch health checks returned HTTP 200 healthy.
- final seed readback: 300 `Alert` rows with `alert_id STARTS WITH 'DIAG-F2-CRED'`.

Batch readbacks:
- 1-25: health 200, readback 25 on first seed pass; 300 on second pass because alerts already existed from the first failed-parser attempt.
- 26-50: health 200, readback 50 on first seed pass; 300 on second pass.
- 51-75: health 200, readback 75 on first seed pass; 300 on second pass.
- 76-100: health 200, readback 100 on first seed pass; 300 on second pass.
- 101-125: health 200, readback 125 on first seed pass; 300 on second pass.
- 126-150: health 200, readback 150 on first seed pass; 300 on second pass.
- 151-175: health 200, readback 175 on first seed pass; 300 on second pass.
- 176-200: health 200, readback 200 on first seed pass; 300 on second pass.
- 201-225: health 200, readback 225 on first seed pass; 300 on second pass.
- 226-250: health 200, readback 250 on first seed pass; 300 on second pass.
- 251-275: health 200, readback 275 on first seed pass; 300 on second pass.
- 276-300: health 200, readback 300.

## One-Loop Sanity
- analyze: HTTP 200 for `DIAG-F2-CRED-0001`, category `credential_access`, action `investigate`, confidence `0.8770461205137833`, decision_id `f5e353cf-386f-4663-8937-2cbc789b5ca7`.
- outcome: HTTP 200 with `outcome="correct"`, `l5_centroid_persisted=true`, `l5_shaped_by_attempted=true`, skipped reason `null`.
- elapsed: 3.376 seconds total.
- result: PASS for one-loop sanity. The earlier parser attempt produced HTTP 200 analyze responses but posted no outcomes because the scratch parser initially expected top-level fields instead of nested `recommendation`/`gae_scoring` fields.

## Long Loop Progress
The required uninterrupted 250-target-category outcome loop did not finish. The single Python process was terminated by the shell command timeout after 900 seconds.

Progress emitted before timeout:
- 25 valid long-loop outcomes: attempts 25, cumulative including one-loop 26, last alert `DIAG-F2-CRED-0026`, elapsed 208.310 seconds.
- 50 valid long-loop outcomes: attempts 50, cumulative including one-loop 51, last alert `DIAG-F2-CRED-0051`, elapsed 444.758 seconds.
- 75 valid long-loop outcomes: attempts 75, cumulative including one-loop 76, last alert `DIAG-F2-CRED-0076`, elapsed 792.305 seconds.

No resume was performed because resuming would split the required proof across processes and create a false pass.

## Milestones
Required milestones were not reached in the uninterrupted long loop.

- 195: not reached.
- 200: not reached.
- 201: not reached.
- 205: not reached.
- 215: not reached.
- 230: not reached.
- 250: not reached.

Final learning-state endpoint after timeout:
- `category="credential_access"`.
- `phase="MEAN_CONVERGENCE"`.
- `alpha=0.5`.
- `dk_weights=null`.
- `freeze_point=null`.
- `decisions_in_category=164`.
- `novelty_rate=null`.
- `batch_pipeline=null`.

## Final AGE Readback
- DIAG-F2-CRED decisions: 86.
- target category outcomes: 82 verified/correct `credential_access` decisions.
- L5Centroid: 1.
- SHAPED_BY: 1.
- L5DKWeight: 0.
- n_decisions_used: absent.
- Welford fields: absent because no `L5DKWeight` rows existed.
- L5ConservationState: no `L5ConservationState(domain="soc")` rows returned in this graph at final readback.

Raw query outputs:

```json
{
  "alerts": [{"cnt": 300}],
  "by_category": [{"category": "credential_access", "cnt": 86}],
  "correct_by_category": [{"category": "credential_access", "cnt": 82}],
  "decisions": [{"cnt": 86}],
  "verified_correct": [{"cnt": 82}],
  "l5_centroid": [{"cnt": 1}],
  "shaped_by": [{"cnt": 1}],
  "l5_dk_weight": [{"cnt": 0}],
  "dk_fields": [],
  "conservation": []
}
```

## Stop Condition Evaluation
- DIAGNOSTIC_F_PASS: not selected; target valid outcomes, phase transition, DK weight, and Welford evidence were not proven.
- RUNTIME_IMPORT_NOT_ALIGNED: not selected; import resolved to source `ci-platform`.
- APP_UNREACHABLE: not selected; backend health stayed reachable.
- AGE_GRAPH_READBACK_FAILED: not selected; async AGE readbacks succeeded.
- SEED_RUNTIME_FAILURE: not selected; 300 alerts were seeded and health checks passed.
- SEED_DATA_ISSUE: not selected for the corrected parser run; one-loop produced `credential_access` and non-referral `investigate`.
- REQUEST_FORMAT_ISSUE: not selected; outcome payload with `analyst_action` succeeded.
- PROCESS_SPLIT_OR_RESTART_DETECTED: SELECTED. The one required long-loop process was terminated by command timeout before reaching 250 valid target outcomes; resuming would split the proof.
- TARGET_CATEGORY_NOT_REACHED: also true as an effect; only 82 verified/correct target outcomes were read back.
- PHASE_TRANSITION_MISSING: also true as an effect; final phase was still `MEAN_CONVERGENCE`.
- DK_REESTIMATE_MISSING: also true as an effect; no DK reestimate evidence was produced.
- L5DKWEIGHT_MISSING: also true as an effect; `L5DKWeight=0`.
- WELFORD_MISSING: also true as an effect; Welford fields were absent.
- UNEXPECTED_RUNTIME_ERROR: not selected as primary; the backend stayed healthy, but runtime throughput exceeded the shell timeout.

## Final Verdict
- Verdict: PROCESS_SPLIT_OR_RESTART_DETECTED.
- Rationale: F2 requires 230+ valid target-category outcomes and the DK phase-transition proof in one uninterrupted backend process and one uninterrupted long outcome loop. This run seeded the correct graph and proved one-loop L5 persistence, but the long-loop driver was killed by timeout after 75 emitted valid long-loop outcomes. Final AGE readback showed only 82 verified/correct target outcomes, no phase transition, `L5DKWeight=0`, and no Welford fields.
- Code fixer scope if needed: none proven by this run.
- Runtime rerun scope if needed: YES. Use a fresh graph/ID prefix or otherwise explicitly reset to a clean F2 proof surface, keep the backend running with source `ci-platform`, `SOC_LEARNING_ENABLED=true`, `GRAPH_BACKEND=age`, `AGE_GRAPH_NAME` set to the fresh proof graph, and run the entire 250-target outcome loop in one process with a timeout above observed runtime.
- Proceed to final C9B proof: NO.

## Limitations
- One process proof required; this run did not satisfy it because the shell command timed out.
- This proves one target category seed/analyze/outcome shape, not all SOC categories.
- Conservation proof is separate/already covered by prior diagnostics where applicable.
- No source code was modified.
- Temporary diagnostic scripts were written only under `scratch/temp`.

## Follow-up Runtime Harness
- A deterministic runtime harness has been added in `docs/implementation_plans/soc_c9b_runtime_harness_plan.md`.
- SOC diagnostic backend launch can now use `copilot-sdk/demo.py --soc --diag-mode --backend-only --graph-name soc_graph_diag_f2 --learning-enabled --source-ci-platform --ensure-graph --no-browser` or `scripts/diagnostics/run_soc_diag_backend.ps1`.
- Diagnostic F should be rerun with `scripts/diagnostics/run_soc_diag_f.py` so batched seeding, health checks, analyze/outcome loops, milestone capture, and DK/Welford readback happen in one deterministic runner process.
- This follow-up does not claim Diagnostic F has passed. Final C9B remains blocked until Diagnostic F passes.
