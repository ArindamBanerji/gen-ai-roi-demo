# SOC C9B Runtime Readiness Audit + 5-Decision Verification

Date: 2026-06-08
Model: gpt-5.3
Task Type: Functional verification; no source code changes
Repo: `C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50`
Diagnostic Graph: `soc_graph_diag_e4`

## Executive Summary
- Verdict: DIAGNOSTIC_E_PASS.
- Runtime import path: `C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\ci-platform\ci_platform\graph\age_graph_store.py`.
- A-D readiness: PASS for the contracts needed by this rerun: route body, category mapping, scorer call chain, outcome write path, ProfileScorer lifecycle, and L5 persistence gates.
- Fixed seed shape confirmed: YES. Credential-access seed uses categorical `Asset.criticality="critical"` and produces the expected six-factor vector with criticality factor `1.0`.
- L5-UPSERT fix accepted: YES per prior review/user-supplied context; this rerun verified the active runtime imports source `ci-platform` and not stale site-packages.
- Live verification run: YES. Five fresh `DIAG-E4-CRED` alerts produced five non-referral scorer actions and five successful outcomes.
- Runtime env verification: backend health 200; AGE graph readback succeeded; live L5 persistence response fields were present and true.
- Main blocker or pass finding: Fresh `L5Centroid` and `SHAPED_BY` evidence exists for the DIAG-E4 decision set.
- Code fixer needed: NO.
- Runtime rerun needed: NO for Diagnostic E.
- Proceed to Diagnostic F: YES.
- Recommended next step: Run Diagnostic F against the same corrected runtime assumptions, using its own fresh proof IDs and graph safeguards.

Readiness matrix:

| Gate | Result | Evidence |
| --- | --- | --- |
| SOC backend reachable | PASS | `/health` returned `{"status":"healthy","components":{"posterior_store":{"healthy":true}}}` |
| Source import aligned | PASS | `ci_platform.graph.age_graph_store` resolved to source `ci-platform` |
| AGE graph reachable | PASS | `MATCH (n) RETURN count(n)` on `soc_graph_diag_e4` returned `[{"total": 1}]` before seeding |
| Fixed seed shape | PASS | Seed script/test contract and live factor vector confirm categorical criticality |
| Analyze loops | PASS | 5/5 HTTP 200, action `investigate` |
| Outcome loops | PASS | 5/5 HTTP 200 |
| Decision verification fields | PASS | 5 decisions have `outcome="correct"` and `correct=true` |
| L5Centroid | PASS | count `1` |
| DIAG-E4-caused L5Centroid | PASS | count `1` |
| SHAPED_BY | PASS | count `1` |
| DIAG-E4 SHAPED_BY | PASS | count `1` |
| L5DKWeight | INFO | count `0`, expected below 200-decision DK threshold |

## Runtime Environment
- SOC backend reachable: YES.
- ci_platform import path: `C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\ci-platform\ci_platform\graph\age_graph_store.py`.
- AGE graph readback: YES, `soc_graph_diag_e4` returned `[{"total": 1}]` before seeding.
- Startup log evidence supplied by user: `[BACKEND] GRAPH_BACKEND=age ... Graph=soc_graph_diag_e4`; `[STARTUP] Backend=AGE | Client=AGEClient | Nodes=0 | Status=VERIFIED`; `Application startup complete`.
- Health endpoint: HTTP 200 with `status=healthy` and `posterior_store.healthy=true`.
- Runtime env status: aligned for this rerun. User supplied `SOC_LEARNING_ENABLED=true`, `AGE_GRAPH_NAME=soc_graph_diag_e4`, and `GRAPH_DSN=host=127.0.0.1 port=5433 dbname=soc_copilot user=postgres password=postgres`; live outcomes also returned `l5_centroid_persisted=true`.

## Fixed Seed Shape Verification
- Seed script: `scripts/soc_c9b_seed_alerts.py` plus scratch runner `scratch/temp/diag_e4_runner.py` for exact five IDs.
- Alert IDs: `DIAG-E4-CRED-001` through `DIAG-E4-CRED-005`.
- alert field: graph `Alert.alert_type`.
- alert value/casing: `anomalous_login`, lowercase.
- Asset.criticality: categorical string `critical`.
- severity: `critical`.
- risk_score: `0.92`.
- mfa_completed: `false`.
- device_fingerprint_match: `false`.
- User/Asset/edge context: each alert has a User, an Asset, `Alert-[:INVOLVES]->User`, and `Alert-[:DETECTED_ON]->Asset`.
- Expected non-referral behavior: confirmed. All five analyze calls returned `action="investigate"` and no referral rule fired.

The stock seeder was not used directly because it cycles categories and formats IDs as four digits. The scratch runner reused the fixed shape and wrote the exact requested IDs to `soc_graph_diag_e4`.

## L5-UPSERT Fix Verification
- Runtime imported source ci-platform: YES.
- Response fields observed: all outcome responses included `centroid_update`, `l5_centroid_persisted`, `l5_shaped_by_attempted`, `l5_persistence_skipped_reason`, and nested `l5_persistence`.
- l5_centroid_persisted: `true` for all five outcome responses.
- l5_persistence_skipped_reason: `null` for all five outcome responses.
- L5Centroid readback: `1`.
- DIAG-E4-caused L5Centroid readback: `1`, caused by decision `6d03cdb4-2522-4919-8be3-9a0eecf37d8a`.
- SHAPED_BY readback: `1`.
- DIAG-E4 SHAPED_BY readback: `1`, linked to `DIAG-E4-CRED-005`.

## Runtime Contract from Prior Diagnostics
- alert field: `Alert.alert_type`.
- analyze body: `POST /api/alert/analyze` with `{"alert_id": "<id>"}`.
- outcome body: `POST /api/alert/outcome` with `{"alert_id": "<id>", "decision_id": "<decision_id>", "outcome": "correct", "analyst_action": "<returned action>"}`.
- required context: graph Alert, User, Asset, `INVOLVES`, and `DETECTED_ON`.
- category mapping: `anomalous_login` maps to `credential_access`.
- action handling: `refer_to_analyst` is routing-only; scorable actions are `escalate`, `investigate`, `suppress`, and `monitor`.
- expected L5 behavior: successful scorable outcomes in `MEAN_CONVERGENCE` write/update `L5Centroid` and attach `SHAPED_BY` when a decision ID is supplied.

Prior diagnostic confirmations:
- Diagnostic A: seed/analyze contract uses `alert_type="anomalous_login"` and analyze posts only `alert_id`.
- Diagnostic B: analyze gets shared ProfileScorer, resolves category index, computes six factors, writes `Decision(domain="soc")`, and returns final routed action.
- Diagnostic C: outcome route sets Decision `outcome`, `correct`, and verification timestamp, then runs learning for scorable actions.
- Diagnostic D: normal runtime path uses the startup scorer singleton; Diagnostic F remained blocked until Diagnostic E proved L5 persistence.
- L5 deep diagnostics: earlier blocker was `AGEGraphStore.update_centroid()` replacement semantics when existing `L5Centroid` had `SHAPED_BY`.
- Persist-false deep diagnostic follow-up: `AGEGraphStore` now uses `_l5_upsert_current()` for current-state L5 nodes, and Diagnostic F stayed blocked until this rerun showed fresh `L5Centroid > 0` and `SHAPED_BY > 0`.

## Seed Data
- method: temporary scratch script `scratch/temp/diag_e4_runner.py` using async `AGEClient.run_query` and the fixed C9B credential-access seed shape.
- alert IDs: `DIAG-E4-CRED-001`, `DIAG-E4-CRED-002`, `DIAG-E4-CRED-003`, `DIAG-E4-CRED-004`, `DIAG-E4-CRED-005`.
- alert properties: `category="credential_access"`, `alert_type="anomalous_login"`, `severity="critical"`, `risk_score=0.92`, `mfa_completed=false`, `device_fingerprint_match=false`, `vpn_provider="c9b_seed"`.
- User/Asset/edge context: each alert has a matching `*-USER`, `*-ASSET`, `INVOLVES`, and `DETECTED_ON`.
- graph used: `soc_graph_diag_e4`.
- count seeded: 5 created, 0 existing.

## Loop Results
Loop 1:
- Alert: `DIAG-E4-CRED-001`.
- Analyze: HTTP 200, category `credential_access`, action `investigate`, confidence `0.8770461205137833`, decision `c4b4e9fa-b2cd-48f8-abd4-619bbfa98d33`.
- Factor vector: `[0.825, 1.0, 0.0, 0.4, 0.7, 0.6666666666666666]`, length 6.
- Routing/referral: `routing_zone="agent_zone"`, `should_refer=false`.
- Outcome: HTTP 200, `outcome="correct"`, `centroid_update.action_name="investigate"`, `centroid_delta_norm=0.012247448713915891`, `l5_centroid_persisted=true`, skipped reason `null`.

Loop 2:
- Alert: `DIAG-E4-CRED-002`.
- Analyze: HTTP 200, category `credential_access`, action `investigate`, confidence `0.9102820463848372`, decision `37b8b697-3b92-4d10-a215-c100602708b6`.
- Factor vector: `[0.825, 1.0, 0.0, 0.4, 0.7, 0.6666666666666666]`, length 6.
- Routing/referral: `routing_zone="agent_zone"`, `should_refer=false`.
- Outcome: HTTP 200, `outcome="correct"`, `centroid_update.action_name="investigate"`, `centroid_delta_norm=0.012247448713915891`, `l5_centroid_persisted=true`, skipped reason `null`.

Loop 3:
- Alert: `DIAG-E4-CRED-003`.
- Analyze: HTTP 200, category `credential_access`, action `investigate`, confidence `0.934466659781363`, decision `56018fa9-7c74-44bd-847b-ae330335a077`.
- Factor vector: `[0.825, 1.0, 0.0, 0.4, 0.7, 0.6666666666666666]`, length 6.
- Routing/referral: non-referral, no referral rule fired.
- Outcome: HTTP 200, `outcome="correct"`, `centroid_update.action_name="investigate"`, `centroid_delta_norm=0.012247448713915891`, `l5_centroid_persisted=true`, skipped reason `null`.

Loop 4:
- Alert: `DIAG-E4-CRED-004`.
- Analyze: HTTP 200, category `credential_access`, action `investigate`, confidence `0.9519262035604401`, decision `17452968-d5c8-4627-a47c-e7db4e947f74`.
- Factor vector: `[0.825, 1.0, 0.0, 0.4, 0.7, 0.6666666666666666]`, length 6.
- Routing/referral: non-referral, no referral rule fired.
- Outcome: HTTP 200, `outcome="correct"`, `centroid_update.action_name="investigate"`, `centroid_delta_norm=0.012247448713915891`, `l5_centroid_persisted=true`, skipped reason `null`.

Loop 5:
- Alert: `DIAG-E4-CRED-005`.
- Analyze: HTTP 200, category `credential_access`, action `investigate`, confidence `0.964500221047202`, decision `6d03cdb4-2522-4919-8be3-9a0eecf37d8a`.
- Factor vector: `[0.825, 1.0, 0.0, 0.39999999999999997, 0.7, 0.6666666666666666]`, length 6.
- Routing/referral: `routing_zone="auto_approve"`, `should_refer=false`.
- Outcome: HTTP 200, `outcome="correct"`, `centroid_update.action_name="investigate"`, `centroid_delta_norm=0.012247448713915891`, `l5_centroid_persisted=true`, skipped reason `null`.

## AGE Readback
- Decisions domain=soc for DIAG-E4-CRED: `5`.
- Non-referral decisions: `5`.
- Outcomes posted: `5`.
- L5Centroid: `1`.
- DIAG-E4-caused L5Centroid: `1`.
- SHAPED_BY: `1`.
- DIAG-E4 SHAPED_BY: `1`.
- L5DKWeight: `0`.
- L5ConservationState: `0`.
- raw query outputs:

```json
{
  "counts": {
    "decisions_domain": 5,
    "non_referral": 5,
    "outcomes_posted": 5,
    "l5_centroid": 1,
    "diag_caused_l5_centroid": 1,
    "shaped_by": 1,
    "diag_shaped_by": 1,
    "l5_dk_weight": 0,
    "l5_conservation": 0
  },
  "decision_rows": [
    {"alert_id": "DIAG-E4-CRED-001", "decision_id": "c4b4e9fa-b2cd-48f8-abd4-619bbfa98d33", "category": "credential_access", "action": "investigate", "confidence": 0.8770461205137833, "outcome": "correct", "correct": true},
    {"alert_id": "DIAG-E4-CRED-002", "decision_id": "37b8b697-3b92-4d10-a215-c100602708b6", "category": "credential_access", "action": "investigate", "confidence": 0.9102820463848372, "outcome": "correct", "correct": true},
    {"alert_id": "DIAG-E4-CRED-003", "decision_id": "56018fa9-7c74-44bd-847b-ae330335a077", "category": "credential_access", "action": "investigate", "confidence": 0.934466659781363, "outcome": "correct", "correct": true},
    {"alert_id": "DIAG-E4-CRED-004", "decision_id": "17452968-d5c8-4627-a47c-e7db4e947f74", "category": "credential_access", "action": "investigate", "confidence": 0.9519262035604401, "outcome": "correct", "correct": true},
    {"alert_id": "DIAG-E4-CRED-005", "decision_id": "6d03cdb4-2522-4919-8be3-9a0eecf37d8a", "category": "credential_access", "action": "investigate", "confidence": 0.964500221047202, "outcome": "correct", "correct": true}
  ],
  "diag_l5_rows": [
    {"domain": "soc", "category": "credential_access", "action": "investigate", "caused_by_decision_id": "6d03cdb4-2522-4919-8be3-9a0eecf37d8a", "delta_norm": 0.012247448713915901}
  ],
  "diag_shaped_rows": [
    {"alert_id": "DIAG-E4-CRED-005", "decision_id": "6d03cdb4-2522-4919-8be3-9a0eecf37d8a", "category": "credential_access", "action": "investigate", "caused_by_decision_id": "6d03cdb4-2522-4919-8be3-9a0eecf37d8a"}
  ]
}
```

## Stop Condition Evaluation
- DIAGNOSTIC_E_PASS: SELECTED. Backend reachable, source import aligned, graph reachable, fixed seed shape confirmed, five non-referral scorer actions, five outcomes posted, verified Decision fields present, `L5Centroid > 0`, DIAG-E4-caused `L5Centroid > 0`, `SHAPED_BY > 0`, and DIAG-E4 `SHAPED_BY > 0`.
- RUNTIME_IMPORT_NOT_ALIGNED: not selected; import path resolves to source `ci-platform`.
- RUNTIME_VERIFICATION_BLOCKED: not selected; live verification completed.
- BLOCKED_BY_RUNTIME_CONFIG: not selected; runtime config was sufficient for this proof.
- BLOCKED_BY_CODE: not selected.
- APP_UNREACHABLE: not selected; `/health` returned 200.
- AGE_GRAPH_READBACK_FAILED: not selected; async `AGEClient.run_query` succeeded.
- REQUEST_FORMAT_ISSUE: not selected; endpoint bodies came from prior diagnostics/source and worked.
- FIXED_SEED_NOT_FOUND: not selected; fixed seed shape confirmed.
- SEED_DATA_ISSUE: not selected; five exact alerts were created with required context.
- ALL_ACTIONS_REFER_TO_ANALYST: not selected; all five actions were `investigate`.
- NO_OUTCOMES_POSTED: not selected; five outcomes posted.
- BROKEN_LINK_2_DOMAIN_TAGGING: not selected; five `Decision(domain="soc")` rows were read back.
- BROKEN_LINK_4_5_CENTROID: not selected; fresh DIAG-E4-caused `L5Centroid` exists.
- BROKEN_LINK_7_SHAPED_BY: not selected; fresh DIAG-E4 `SHAPED_BY` exists.
- UNEXPECTED_RUNTIME_ERROR: not selected.

## Final Verdict
- Verdict: DIAGNOSTIC_E_PASS.
- Rationale: The fresh `DIAG-E4-CRED` proof exercised the accepted L5 upsert runtime and produced five verified SOC decisions plus fresh L5 centroid and SHAPED_BY evidence in `soc_graph_diag_e4`.
- Code fixer scope if needed: none.
- Runtime rerun scope if needed: none for Diagnostic E.
- Proceed to Diagnostic F: YES.

## Limitations
- DKWeight 0 is expected for 5 decisions because this run is below the 200-decision DK threshold.
- `L5ConservationState` remained 0 in this graph; this is not a pass blocker for Diagnostic E under the requested criteria.
- No source code was modified by this prompt.
- Temporary diagnostic artifacts were written only under `scratch/temp`.
