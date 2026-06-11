# SOC/AGE Performance Benchmark Suite

This directory contains safe, external diagnostics for isolating SOC/AGE runtime performance after Diagnostic F proved correctness but showed product-unusable latency.

## Current Evidence

Diagnostic F passed on `soc_graph_diag_f8` with prefix `DIAG-F8-CRED`:

- verdict: `EXTERNAL_DIAGNOSTIC_F_PASS`
- valid_outcomes: `250`
- decisions / verified / outcome_present: `250 / 250 / 250`
- L5Centroid / SHAPED_BY / L5DKWeight: `1 / 1 / 1`
- Welford present: `true`
- max_n_decisions_used: `250`
- avg_analyze_seconds: `25.602`
- max_analyze_seconds: `49.915`
- avg_outcome_seconds: `3.547`
- max_outcome_seconds: `8.301`

## Roadmap Hypotheses

The suite is intended to isolate:

- HTTP-only overhead
- AGE connection overhead
- AGE query complexity: point lookup versus prefix/O(N) scans
- full HTTP stack cost
- isolated AGE write cost

Current hypotheses:

- A: no AGE connection pool
- B: O(N) query in analyze hot path
- C: missing AGE property index on `alert_id` / `decision_id`
- D: synchronous centroid/checkpoint write

Decision gates:

- fresh/warm AGE ratio above 5x or 10x suggests connection setup/pooling cost
- point lookup average above 100 ms suggests missing index or slow label scan
- prefix scan much slower than point lookup suggests O(N) query pressure
- fast HTTP health with slow analyze suggests route-specific compute/write cost

## Safety Rules

- Default diagnostics are read-only except explicitly named scratch-graph write measurements.
- Do not call `/api/alert/analyze` on existing proof alerts such as `DIAG-F8-CRED`.
- Do not write to `soc_graph_diag_f8`.
- Do not run write benchmarks on proof graphs.
- Any write benchmark must be a separate script with proof-graph refusal checks and a dedicated scratch graph.
- Rule #40 applies: Windows-side AGE/PostgreSQL DSNs must use `localhost`, not `127.0.0.1`.

## Network Split Rule

On this Windows 11 + mirrored WSL2 setup, local database and local HTTP traffic use different loopback names:

- AGE/PostgreSQL DSNs use `host=localhost port=5433 ...`.
- FastAPI/uvicorn HTTP calls use `http://127.0.0.1:<port>`.

Measured behavior:

- Python `urllib` to `http://localhost:8001/health` is about 2.1 seconds.
- PowerShell `Invoke-WebRequest` to `http://localhost:8001/health` is about 2.1 seconds.
- PowerShell `Invoke-WebRequest` to `http://127.0.0.1:8001/health` is about 0.08-0.10 seconds.
- `curl.exe` to localhost is about 0.29 seconds.
- `psycopg` to `host=localhost port=5433` works.
- `psycopg` to `host=127.0.0.1 port=5433` times out.

Reason: localhost HTTP resolves `::1` first while uvicorn binds IPv4, causing fallback latency. AGE/PostgreSQL is reached through WSL2 mirrored networking via `localhost`; `127.0.0.1` does not reach that database listener from Windows.

## Script 01: Read-Only AGE

Command:

```powershell
python .\scripts\diagnostics\perf\soc_perf_01_readonly_age.py --graph-name soc_graph_diag_f8 --prefix DIAG-F8-CRED --graph-dsn "host=localhost port=5433 dbname=soc_copilot user=postgres password=postgres" --reps 5
```

This script measures:

- fresh client `RETURN 1`
- warm client `RETURN 1`
- warm `MATCH (n) RETURN count(n)`
- exact Alert lookups for early and late proof alerts
- Decision joins for early and late proof alerts
- Decision lookups by `decision_id` when obtainable
- prefix scans for Alerts, Decisions, verified Decisions, and outcome-present Decisions
- L5 current-state counts and DK/Welford readback
- total node and edge counts

Outputs are written to:

- `docs/implementation_plans/perf/soc_perf_01_readonly_age.json`
- `docs/implementation_plans/perf/soc_perf_01_readonly_age.md`

## Planned Scripts

Script 02: `soc_perf_02_readonly_http.py`

- read-only HTTP checks such as `/health`
- no analyze/outcome calls against proof alerts
- source-map report for `/api/alert/analyze` and `/api/alert/outcome`
- safe negative analyze call uses only `PERF-NONEXISTENT-DO-NOT-CREATE`, which source review shows returns before Decision creation

Command:

```powershell
python .\scripts\diagnostics\perf\soc_perf_02_readonly_http.py --backend-url http://127.0.0.1:8001 --graph-name soc_graph_diag_f8 --prefix DIAG-F8-CRED --graph-dsn "host=localhost port=5433 dbname=soc_copilot user=postgres password=postgres" --reps 5
```

Script 03: `soc_perf_03_phase3_commit_spike.py`

- measures committed Phase-3-like AGE transaction cost on a scratch graph
- creates synthetic Decision-like, audit-like, and counter-like rows
- cleans only matching `run_id`/`prefix` rows unless `--keep-graph` is set
- refuses known proof graphs

Command:

```powershell
python .\scripts\diagnostics\perf\soc_perf_03_phase3_commit_spike.py --reps 10
```

TODO 04: `soc_perf_04_summary.py`

- combines JSON reports into a single diagnosis summary
- no graph or HTTP access required by default
