# SOC Phase-3 Committed Transaction Spike

## Summary
Diagnostic-only measurement of a committed Phase-3-like AGE transaction on a scratch graph.

## Safety
- Graph: `soc_graph_phase3_commit_spike_1`
- DSN: `host=localhost port=5433 dbname=soc_copilot user=postgres password=***`
- Run ID: `PHASE3-SPIKE-20260609T225104Z-06d78ffe`
- Prefix: `PHASE3-SPIKE`
- Synthetic spike type: `phase3_commit_measurement`
- Cleanup performed: `True`
- Synthetic nodes after cleanup/readback: `0`
- Synthetic edges after cleanup/readback: `0`

## Results
| mode | count | avg_ms | p50_ms | p95_ms | max_ms | min_ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| committed | 10 | 8.782 | 8.103 | 11.597 | 12.121 | 7.149 |
| rollback | 10 | 3.862 | 3.699 | 4.517 | 4.705 | 3.121 |

- Commit overhead estimate: `4.920 ms`

## Interpretation
- The committed measurement is authoritative for this Package 0 planning check.
- The rollback measurement is secondary context only.
- These are diagnostic dev-box numbers, not buyer-facing latency claims.
- WSL2 dev-box fsync/WAL behavior may differ from pilot storage and must be re-confirmed.
