# SOC Performance Instrumentation Design

Date: 2026-06-09
Task Type: Design only
Product Code Changed: No

## Current Evidence Summary

Diagnostic F passed on `soc_graph_diag_f8` with prefix `DIAG-F8-CRED`:

- verdict: `EXTERNAL_DIAGNOSTIC_F_PASS`
- valid_outcomes: `250`
- decisions / verified / outcome_present: `250 / 250 / 250`
- L5Centroid / SHAPED_BY / L5DKWeight: `1 / 1 / 1`
- Welford present: `true`
- max_n_decisions_used: `250`

Performance from the F8 proof is not product-usable:

- avg_analyze_seconds: `25.602`
- max_analyze_seconds: `49.915`
- avg_outcome_seconds: `3.547`
- max_outcome_seconds: `8.301`

Read-only benchmarks do not explain that latency:

- Simple AGE reads are about `0.09-0.11s` for `RETURN 1`, point lookups, prefix scans, and L5/Welford reads.
- `MATCH ()-[r]->() RETURN count(r)` is about `0.23s` average and `0.45s` max.
- Safe HTTP endpoints are fast when called through IPv4 loopback: `/health` around `0.145s`, negative missing-alert analyze around `0.098s`, and `/api/soc/profile` around `0.101s`.

Conclusion: the remaining 20-50s gap is specific to the successful analyze route path, not generic HTTP or simple AGE read cost.

## Network Split Rule

On this Windows 11 + mirrored WSL2 setup:

- Database/AGE/PostgreSQL DSNs use `localhost`, for example `host=localhost port=5433 dbname=soc_copilot user=postgres password=postgres`.
- Local HTTP/FastAPI/uvicorn calls use `127.0.0.1`, for example `http://127.0.0.1:8001`.

Reason:

- HTTP `localhost` resolves `::1` first while uvicorn binds IPv4, causing a ~2 second fallback penalty.
- AGE/PostgreSQL is reached through WSL2 mirrored networking via `localhost`; `127.0.0.1` times out from Windows.

## Proposed Environment Variables

All instrumentation is off by default.

```text
SOC_PERF_TRACE_ENABLED=false
SOC_PERF_TRACE_LEVEL=summary
SOC_PERF_TRACE_OUTPUT=scratch/temp/soc_perf_trace.jsonl
SOC_PERF_TRACE_SLOW_MS=500
SOC_PERF_TRACE_INCLUDE_CYPHER=false
SOC_PERF_TRACE_INCLUDE_FACTOR_VECTOR=false
SOC_PERF_TRACE_SAMPLE_RATE=1.0
SOC_PERF_TRACE_MAX_EVENTS_PER_REQUEST=500
SOC_PERF_TRACE_FLUSH_EVERY_N=25
```

Allowed levels:

- `summary`: route-level and major phase totals only.
- `detailed`: nested phase events and AGE query events.

Sensitive data defaults:

- No DSN passwords.
- No full alert payloads.
- No full factor vectors unless `SOC_PERF_TRACE_INCLUDE_FACTOR_VECTOR=true`.
- No full Cypher unless `SOC_PERF_TRACE_INCLUDE_CYPHER=true`.

## JSONL Event Schema

Each line is one JSON object.

```json
{
  "event_type": "phase_timing",
  "trace_id": "uuid-or-runner-attempt-id",
  "request_id": "alert-or-decision-scoped-id",
  "route": "/api/alert/analyze",
  "phase": "decision_node_write",
  "query_label": null,
  "started_epoch": 1781000000.123,
  "duration_ms": 124.5,
  "status": "ok",
  "row_count": 1,
  "exception_type": null,
  "graph_name": "soc_graph_diag_f8",
  "alert_id": "DIAG-F8-CRED-0250",
  "decision_id": "redacted-or-short-id",
  "attempt_index": 250,
  "sampled": true,
  "metadata": {
    "category": "credential_access",
    "action": "investigate",
    "cypher_hash": "sha256:...",
    "cypher_shape": "MATCH_CREATE_DECISION_DECIDED_ON",
    "factor_vector_len": 6
  }
}
```

Required common fields:

- `event_type`
- `trace_id`
- `route`
- `phase`
- `duration_ms`
- `status`
- `graph_name`

Optional fields:

- `query_label`
- `row_count`
- `exception_type`
- `alert_id`
- `decision_id`
- `attempt_index`
- `metadata`

## Timer Pseudocode

```python
class PerfTracer:
    def enabled(self) -> bool:
        return os.getenv("SOC_PERF_TRACE_ENABLED", "false").lower() == "true"

    @contextmanager
    def phase(self, phase, *, route=None, alert_id=None, decision_id=None, **metadata):
        if not self.enabled() or not self.sample():
            yield
            return
        started = time.perf_counter()
        status = "ok"
        exc_type = None
        try:
            yield
        except Exception as exc:
            status = "error"
            exc_type = type(exc).__name__
            raise
        finally:
            duration_ms = (time.perf_counter() - started) * 1000
            self.emit_best_effort({
                "event_type": "phase_timing",
                "phase": phase,
                "route": route,
                "alert_id": alert_id,
                "decision_id": decision_id,
                "duration_ms": round(duration_ms, 3),
                "status": status,
                "exception_type": exc_type,
                "metadata": sanitize(metadata),
            })
```

Safety requirements:

- `emit_best_effort()` catches and logs trace write failures at debug level only.
- File writes are append-only JSONL.
- Buffer length is capped by `SOC_PERF_TRACE_MAX_EVENTS_PER_REQUEST`.
- Flush cadence follows `SOC_PERF_TRACE_FLUSH_EVERY_N`.

## Runner Instrumentation

Current runner coarse timings exist in `scripts/diagnostics/run_soc_diag_f.py`:

- `http_json()` at line 297.
- `final_readback()` at line 587.
- `progress_readback()` at line 634.
- `record_latency()` at line 681.
- `seed_one_with_retries()` at line 1111.
- `run_analyze_outcome_pair()` at line 1254.
- `write_reports()` at line 1160.

Add optional runner trace phases:

- `seed_direct_age`
- `analyze_http_request`
- `outcome_http_request`
- `retry_backoff_wait`
- `analyze_timeout_readback`
- `outcome_timeout_readback`
- `progress_readback`
- `final_readback`
- `report_write`
- `total_attempt`

Runner trace metadata:

- `scenario`
- `graph_name`
- `prefix`
- `attempt_index`
- `alert_id`
- `decision_id`
- `target_outcomes`
- `valid_outcomes_before`
- `valid_outcomes_after`
- `retry_count`
- `recovered_by_readback`

Runner insertion points:

- Wrap `seed_one_with_retries()` body as `seed_direct_age`.
- Wrap `http_json("POST", "/api/alert/analyze", ...)` as `analyze_http_request`.
- Wrap `http_json("POST", "/api/alert/outcome", ...)` as `outcome_http_request`.
- Wrap `asyncio.sleep(backoff)` as `retry_backoff_wait`, so retry sleep is not counted as HTTP latency.
- Wrap `latest_decision_for_alert()` as `analyze_timeout_readback`.
- Wrap `outcome_for_decision()` as `outcome_timeout_readback`.
- Wrap `progress_readback()` and `final_readback()`.
- Wrap `write_reports()`.
- Wrap each streaming loop attempt from seed start through outcome/skip as `total_attempt`.

## Analyze Route Instrumentation

Source route:

- `/api/alert/analyze` is defined in `backend/app/routers/triage.py:173`.
- It writes a Decision node and `DECIDED_ON` edge in the normal successful path at `backend/app/routers/triage.py:442-463`.
- It writes audit/metadata afterward at `backend/app/routers/triage.py:466-483` and additional metadata/event paths later in the route.

Proposed phases:

- `request_parse`
- `scorer_readiness`
- `alert_lookup`
- `security_context_lookup`
- `category_resolution`
- `factor_vector_construction`
- `scorer_decision`
- `decision_node_write`
- `decided_on_edge_write`
- `audit_write`
- `metadata_logging_snapshot_write`
- `response_serialization`

Insertion map:

- `request_parse`: immediately after function entry, before `alert_id = request.alert_id`.
- `scorer_readiness`: guard at `triage.py:184-197`.
- `alert_lookup`: `neo4j_client.get_alert(alert_id)` at `triage.py:205`.
- `security_context_lookup`: `neo4j_client.get_security_context(alert_id)` at `triage.py:213`.
- `category_resolution`: `resolve_alert_category(alert_type)` at `triage.py:223-238`.
- `factor_vector_construction`: factor computer/orchestrator block beginning near `triage.py:240`.
- `scorer_decision`: scorer action selection and exploration policy before Decision write.
- `decision_node_write` and `decided_on_edge_write`: current combined query at `triage.py:444-463`. If not split in code, label as `decision_node_and_edge_write`.
- `audit_write`: `record_decision()` at `triage.py:466-475`.
- `metadata_logging_snapshot_write`: Decision metadata `SET` calls and event/provenance sections after `triage.py:479`.
- `response_serialization`: final response object assembly before return.

Do not add graph writes for instrumentation. Emit only JSONL trace events.

## Outcome Route Instrumentation

Source route:

- `/api/alert/outcome` is defined at `backend/app/routers/triage.py:1065`.
- It updates Decision outcome fields at `triage.py:1125-1133`.
- It writes audit hash metadata at `triage.py:1166-1170`.
- It scans analyst history at `triage.py:1177-1180`.
- It updates learning/ProfileScorer, conservation, DK, L5 centroid, snapshots, and evolution logs later in the route.

Proposed phases:

- `request_parse`
- `duplicate_feedback_guard`
- `decision_lookup`
- `decision_outcome_update`
- `outcome_audit_write`
- `analyst_history_scan`
- `learning_state_update`
- `profile_scorer_update`
- `conservation_monitor`
- `l5_centroid_write`
- `l5_dk_weight_write`
- `l5_conservation_write`
- `snapshot_evolution_logging`
- `response_serialization`

Insertion map:

- `request_parse`: after function entry at `triage.py:1066`.
- `duplicate_feedback_guard`: `get_feedback_status()` at `triage.py:1082-1089`.
- `decision_lookup` and `decision_outcome_update`: current combined `MATCH/SET/RETURN` at `triage.py:1125-1145`. If not split, label as `decision_lookup_and_outcome_update`.
- `outcome_audit_write`: `record_outcome()` and Decision hash `SET` at `triage.py:1155-1170`.
- `analyst_history_scan`: query at `triage.py:1177-1180`.
- `learning_state_update`: `learning_state.update(...)` around `triage.py:1261-1269`.
- `conservation_monitor`: health/effective conservation block around `triage.py:1297-1313`.
- `profile_scorer_update`: guarded scorer update block around `triage.py:1395-1430`.
- `l5_dk_weight_write`: `_update_dk_welford_tracker(...)` at `triage.py:1413`.
- `l5_centroid_write`: `_persist_soc_centroid(...)` at `triage.py:1431-1459`.
- `l5_conservation_write`: conservation state persistence, if invoked in the health monitor/store path.
- `snapshot_evolution_logging`: snapshot, distance, and evolution sections at `triage.py:1491-1779`.
- `response_serialization`: final response payload construction before return.

## AGEClient and Store Instrumentation

Source points:

- `AGEClient` is in `ci-platform/ci_platform/graph/age_client.py:73`.
- `AGEClient.run_query()` is at `age_client.py:399`.
- AGE uses sync psycopg per query under `asyncio.to_thread`; the source comment notes this at `age_client.py:16` and implementation calls `_sync_execute` through `run_query`.
- `AGEGraphStore` owns an AGEClient at `age_graph_store.py:39`.
- L5 store write entrypoints are `update_centroid()` at `age_graph_store.py:1604`, `update_dk_weights()` at `age_graph_store.py:1696`, and `update_conservation_state()` at `age_graph_store.py:1821`.
- `_l5_upsert_current()` is at `age_graph_store.py:78`.

Design:

- Add optional wrapper inside `AGEClient.run_query()`.
- Emit one event per query when tracing is enabled.
- Include:
  - `query_label`
  - `phase`
  - `duration_ms`
  - `row_count`
  - `exception_type`
  - `graph_name`
  - `caller route/attempt id`, if contextvars are set
  - `cypher_hash`
  - optional `cypher` only when `SOC_PERF_TRACE_INCLUDE_CYPHER=true`
- Use Python `contextvars` for route, alert_id, decision_id, phase, and attempt_id.
- Do not log full Cypher by default.
- Do not log parameters containing secrets.

Suggested query labeling:

- Explicit labels at call sites where easy, such as `alert_lookup`, `security_context_lookup`, `decision_node_write`, `outcome_update`, `l5_centroid_write`.
- Fallback label from Cypher shape hash and first verb/pattern.

Store-specific labels:

- `_l5_upsert_current`: `l5_upsert_current`
- `update_centroid`: `l5_update_centroid`
- `update_dk_weights`: `l5_update_dk_weights`
- `update_conservation_state`: `l5_update_conservation_state`

## Safety and Overhead Plan

Guarantees:

- Zero behavior change when disabled.
- No graph writes for instrumentation.
- No blocking network calls.
- Best-effort file writes only.
- Trace write failure never fails analyze/outcome.
- Bounded memory with per-request event cap.
- Sampling is supported.
- No secrets or DSN passwords.
- No full factor vectors by default.
- No full alert payloads by default.
- No full Cypher by default.

Overhead controls:

- Branch quickly when `SOC_PERF_TRACE_ENABLED=false`.
- Resolve env/config once at startup and cache.
- Use append-only JSONL with buffered flush.
- Drop events beyond `SOC_PERF_TRACE_MAX_EVENTS_PER_REQUEST`.
- Emit only slow events above `SOC_PERF_TRACE_SLOW_MS` when level is `summary`.

## Summary Tooling

Future script:

```text
scripts/diagnostics/perf/soc_perf_trace_summary.py
```

Inputs:

- `--trace-jsonl scratch/temp/soc_perf_trace.jsonl`
- `--output-json docs/implementation_plans/perf/soc_perf_trace_summary.json`
- `--output-md docs/implementation_plans/perf/soc_perf_trace_summary.md`

Aggregations:

- p50 / p95 / p99 / max by phase
- top 20 slow events
- per-alert waterfall
- analyze vs outcome phase comparison
- AGE query label breakdown
- route-level totals
- early / mid / late window comparison, for example attempts 1-25, 100-125, 225-250

## Validation Plan

Phase B runner-only implementation:

```powershell
python -m py_compile .\scripts\diagnostics\run_soc_diag_f.py
python .\scripts\diagnostics\run_soc_diag_f.py --help
```

Phase C triage route timers:

```powershell
python -m py_compile .\backend\app\routers\triage.py
python -m pytest backend/tests/test_soc_dk_l5.py backend/tests/test_soc_c9b_l5_proof.py -q --tb=short
```

Phase D AGE wrapper:

```powershell
cd ..\ci-platform
python -m py_compile .\ci_platform\graph\age_client.py .\ci_platform\graph\age_graph_store.py
python -m pytest tests/test_l5_upsert_current.py -q --tb=short
```

Phase E summary script:

```powershell
python -m py_compile .\scripts\diagnostics\perf\soc_perf_trace_summary.py
python .\scripts\diagnostics\perf\soc_perf_trace_summary.py --help
```

Do not rerun proof until each phase has GPT-5.5 review.

## Rollout Plan

Phase A: design doc only.

Phase B: implement shared `perf_trace` helper and runner-only instrumentation.

Phase C: add `triage.py` analyze/outcome phase timers.

Phase D: add AGEClient/store query wrapper instrumentation.

Phase E: add `soc_perf_trace_summary.py`.

Each phase:

- keep tracing disabled by default
- run `py_compile`
- run only small read-only validation unless explicitly approved
- review before proof rerun

## Exact Next Implementation Prompt

```text
/model gpt-5.3
Echo the current model name in the first line of output.

TASK: Implement Phase B SOC perf trace helper + runner-only instrumentation
TASK TYPE: Diagnostic tooling only. LIMITED CODE CHANGES.

Read:
- docs/implementation_plans/soc_perf_instrumentation_design.md
- scripts/diagnostics/run_soc_diag_f.py
- scripts/diagnostics/perf/soc_perf_common.py

Implement only:
- scripts/diagnostics/perf/soc_perf_trace.py
- runner-only instrumentation in scripts/diagnostics/run_soc_diag_f.py

Do not change product routes, AGEClient, graph-store, scorer, DK, L5, conservation, or frontend.
Tracing must be disabled by default and controlled by SOC_PERF_TRACE_* env vars.
Instrument runner phases:
- seed_direct_age
- analyze_http_request
- outcome_http_request
- retry_backoff_wait
- analyze_timeout_readback
- outcome_timeout_readback
- progress_readback
- final_readback
- report_write
- total_attempt

Safety:
- no graph writes
- no extra network calls
- best-effort JSONL writes only
- no secrets
- no full factor vectors or full Cypher
- trace write failure must not fail proof

Validation only:
- python -m py_compile .\scripts\diagnostics\perf\soc_perf_trace.py
- python -m py_compile .\scripts\diagnostics\run_soc_diag_f.py
- python .\scripts\diagnostics\run_soc_diag_f.py --help

Do not run proof, seed data, benchmarks, or backend.
```
