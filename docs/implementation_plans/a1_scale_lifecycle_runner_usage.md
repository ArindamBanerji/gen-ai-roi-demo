# A1 Scale Measurement Runner Usage

`scripts/diagnostics/run_soc_diag_f.py` is a T2/proof-only harness. It expects an
already-running backend and a matching diagnostic backend contract.

Use `scripts/diagnostics/run_soc_route_validation.py` for A1 scale measurements.
It owns stale-port cleanup, backend startup, contract readiness, strict contract
validation, proof execution, artifact writing, and backend cleanup.

## A1 500

```powershell
$ownerProcessIds = @(Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique)
foreach ($ownerProcessId in $ownerProcessIds) {
  if ($ownerProcessId) { Stop-Process -Id $ownerProcessId -Force -ErrorAction SilentlyContinue }
}

python .\scripts\diagnostics\run_soc_route_validation.py `
  --phase proof `
  --port 8001 `
  --prefix A1SCALE500 `
  --proof-graph soc_graph_a1_scale_500_1 `
  --proof-env "USE_SOC_DECISION_PIPELINE_SHADOW=false,USE_ENTITY_CACHE=false,USE_MATERIALIZED_COUNTERS=false,AGE_USE_POOL=true" `
  --proof-target-outcomes 500 `
  --proof-max-attempts 800 `
  --strict-contract `
  --out-dir scratch/temp
```

## A1 1000

```powershell
$ownerProcessIds = @(Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique)
foreach ($ownerProcessId in $ownerProcessIds) {
  if ($ownerProcessId) { Stop-Process -Id $ownerProcessId -Force -ErrorAction SilentlyContinue }
}

python .\scripts\diagnostics\run_soc_route_validation.py `
  --phase proof `
  --port 8001 `
  --prefix A1SCALE1000 `
  --proof-graph soc_graph_a1_scale_1000_1 `
  --proof-env "USE_SOC_DECISION_PIPELINE_SHADOW=false,USE_ENTITY_CACHE=false,USE_MATERIALIZED_COUNTERS=false,AGE_USE_POOL=true" `
  --proof-target-outcomes 1000 `
  --proof-max-attempts 1500 `
  --strict-contract `
  --out-dir scratch/temp
```

Both commands keep current canonical route behavior, keep EntityCache and
materialized counters off, and do not approve full route adoption or
buyer-facing performance claims.
