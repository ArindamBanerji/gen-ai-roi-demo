# P2 Diagnostic Report — SOC (gen-ai-roi-demo-v4-v50)
Date: 2026-09-28
Scanner: P2-DIAG-SOC (terra/high)
Baseline: 2767 passed, 0 skipped

## Scan Scope

Production files scanned: 155
Test files scanned: 276
Known findings excluded: 20 (SOC-01 through SOC-20)

Every Python file in the requested directories was parsed and scanned. Candidate exception fallbacks, sentinels, availability assignments, route responses, fixtures, live HTTP checks, and failure tests were then reviewed in context and traced to their consumers. Findings below exclude the named SOC-01 through SOC-20 issues.

## New Production Findings

### P2 — User-Visible Data Quality

| ID | File | Line | Function | Pattern | Description |
|----|------|------|----------|---------|-------------|
| SOC-P2-N01 | `backend/app/routers/framework_router.py` | 940 | `factor_contribution` | Collapsed error state / missing availability | A scorer lookup or kernel-weight failure becomes `dk_weights=None`, after which the endpoint manufactures a uniform 100% contribution distribution and top/weakest rankings. The frontend renders these as factor measurements and has no availability field with which to identify the fallback. |
| SOC-P2-N02 | `backend/app/routers/framework_router.py` | 1090 | `get_triage_learning_state` | Collapsed error state / wrong reason | Scorer, phase, alpha, DK, and category-state failures are converted to the same continuous/mean-convergence/zero-decision response used for a legitimate cold start. The UI can hide the panel or show zero learning state without knowing the read failed. |
| SOC-P2-N03 | `backend/app/routers/framework_router.py` | 1179 | `get_channel_decomposition` | Collapsed error state / wrong reason | Scorer and learning-state failures become zero decisions and an inactive scorer channel. A graph-snapshot exception changes only the description while leaving the graph channel `status="active"`; totals are still computed from zero placeholders and no availability metadata is returned. |
| SOC-P2-N04 | `backend/app/routers/soc.py` | 2785 | `get_gate_config` | Wrong reason on fail-closed | A learning-state read failure is logged and treated as `n_decisions=0`. The endpoint returns a normal conservative GateConfig summary, so consumers interpret an outage as an uncalibrated deployment. |
| SOC-P2-N05 | `backend/app/routers/soc.py` | 3912 | `get_analyst_eta_weights_endpoint`, `get_analyst_weights` | Collapsed error state / incorrect availability | Both endpoints turn a learning-state failure into `n_decisions=0` and default/un-calibrated analyst weights. The first has no availability flag; the second can still return `data_available=true` because its `degraded` flag tracks a different graph query only. |
| SOC-P2-N06 | `backend/app/routers/soc.py` | 2431 | `get_f9_report` | Availability propagation lost | The wrapped benchmarking endpoint reports `data_available`, `degraded`, and `degraded_fields`, including partial per-category/archetype/day failures. The report wrapper drops all three, so a partially failed report is returned without its outage state. |
| SOC-P2-N07 | `backend/app/routers/soc.py` | 2674 | `get_reconvergence_log` | Collapsed error state | `read_reconvergence_events()` returns `[]` for both an empty graph and a failed graph read. The HTTP response reports zero events and says collection is active, with no availability or degraded field. |
| SOC-P2-N08 | `backend/app/routers/soc.py` | 4576 | `get_decision_distance_log` | Collapsed error state / wrong reason | `read_decision_distance_log()` swallows graph failures as `[]`; the endpoint therefore returns `total=0` and `convergence_trend="insufficient_data"`, indistinguishable from a healthy graph with too little history. |
| SOC-P2-N09 | `backend/app/routers/soc.py` | 4713 | `get_epistemic_state` | Collapsed error state | A snapshot `RuntimeError` returns `categories={}` and `total_verified=0`, exactly the legitimate empty state, without `state_available` or `degraded`. |
| SOC-P2-N10 | `backend/app/routers/judgment.py` | 151 | `explain_decision_get` | Sentinel erasure / missing availability | A genuinely absent decision and a present but malformed decision both return the same all-null explanation envelope. There is no status or availability field, so API consumers cannot distinguish “not found” from unusable stored evidence. |
| SOC-P2-N11 | `backend/app/services/iks.py` | 307 | `_compute_delta_7d` | Collapsed computation failure | Missing history legitimately produces `0.0`, but malformed snapshot JSON/tensors also produce `0.0`. `/api/soc/profile` exposes that value as a real seven-day IKS delta without a delta-availability flag. |
| SOC-P2-N12 | `backend/app/services/time_machine.py` | 117 | `_decision_count` | Collapsed parse failure | Invalid snapshot decision-count metadata is converted to `0`, the same as a true day-zero snapshot. Time-machine list, comparison, and timeline responses expose the zero without per-field validity metadata. |
| SOC-P2-N13 | `backend/app/services/evidence_room.py` | 173 | `_collect_conservation` | Sticky-true availability | `iks_available` starts as `True`. If conservation collection fails, the IKS fallback is not attempted; if fallback setup raises, the exception also leaves the flag true. The evidence-room response can therefore claim IKS availability when no IKS read succeeded. |

### P3 — Internal Observability / Type Contract

| ID | File | Line | Function | Pattern | Description |
|----|------|------|----------|---------|-------------|
| SOC-P3-N01 | `backend/app/services/balance_sheet.py` | 38 | `CategoryBalance` / `generate_balance_sheet` | Dead flag | `iks_contribution_available` is populated and serialized, but no production or frontend consumer reads it; the frontend type merely declares it. The typed zero remains correctly guarded elsewhere, so this is dormant contract debt rather than a current user-visible error. |
| SOC-P3-N02 | `backend/app/services/iks.py` | 144 | `get_iks_trend` | Collapsed error state in unused helper | The helper returns `[]` for both no snapshots and an AGE outage. No production caller currently invokes it, so the ambiguity is latent. |
| SOC-P3-N03 | `backend/app/services/threat_indicator.py` | 199 | `cleanup_expired` | Collapsed error state in unused helper | A cleanup failure returns `0`, identical to “nothing expired.” There is no production caller today, so the lost failure state is internal debt. |
| SOC-P3-N04 | `backend/app/services/cohort_status.py` | 141 | `CohortStatusService._read_decisions` | Collapsed error state in inactive path | The optional graph-store path returns `[]` on exceptions. The HTTP router uses its own sentinel-aware reader and passes explicit records, leaving this ambiguous path unused in production. |
| SOC-P3-N05 | `backend/app/services/reconvergence_logger.py` | 53 | `log_reconvergence_event`, `log_decision_distance` | Dead failure result | Both telemetry writes return `None` on failure, but their current callers do not inspect the result or expose a persistence status. Failures are logged only and do not misstate the primary decision response. |
| SOC-P3-N06 | `backend/app/routers/framework_router.py` | 904 | `factor_analysis_summary` | Missing machine-readable availability | The response can return `bootstrap_improved=None` and `weakest_category_ceiling=None` without availability booleans. Its recommendation text explicitly says the comparison is unavailable, preventing current human misinterpretation, but the API contract remains ambiguous for automated consumers. |
| SOC-P3-N07 | `backend/app/routers/framework_router.py` | 1057 | `intervention_history` | Inconsistent availability contract | Failure returns `history_available=false`, while success omits `history_available=true`. No current frontend consumer reads the flag, but a future consumer cannot use a stable boolean contract. |

### P4 — Cosmetic / Style

None found.

## New Test Quality Findings

### P2

| ID | File | Line | Pattern | Description |
|----|------|------|---------|-------------|
| SOC-T2-N01 | `backend/tests/test_sentinel_real.py` | 111 | Hollow failure test | `test_sentinel_mock_connector_still_passes` explicitly accepts HTTP 500 from `/api/alerts/queue`. A user-visible endpoint regression can therefore pass the test. |

### P3

| ID | File | Line | Pattern | Description |
|----|------|------|---------|-------------|
| SOC-T3-N01 | `backend/tests/test_audit_chain_wiring_extended.py` | 132 | Hollow failure test | The ValueError-path test asserts only that the result is an `int`; an incorrect positive reconstructed count or partial mutation would still pass. |
| SOC-T3-N02 | `backend/tests/test_l5_conservation_soc_hook.py` | 6 | Mock instead of MagicMock | The file imports and uses `unittest.mock.Mock`, contrary to the C-5 test-double rule. |

### P4

None found.

## Totals

| Severity | Production | Test Quality | Total |
|----------|------------|--------------|-------|
| P2       | 13         | 1            | 14    |
| P3       | 7          | 2            | 9     |
| P4       | 0          | 0            | 0     |
| **Total**| 20         | 3            | 23    |
