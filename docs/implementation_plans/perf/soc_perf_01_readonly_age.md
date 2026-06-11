# SOC Perf 01 Read-Only AGE Benchmark

## Safety
- read_only: `True`
- graph_name: `soc_graph_diag_f8`
- prefix: `DIAG-F8-CRED`
- graph_dsn_redacted: `host=localhost port=5433 dbname=soc_copilot user=postgres password=***`
- Rule40 validated: `True`
- no writes performed: `True`
- analyze/outcome endpoints called: `False`

## Measurements
| label | reps | avg_s | p50_s | p95_s | max_s | error |
|---|---:|---:|---:|---:|---:|---|
| tier_a_fresh_client_return_1 | 10 | 0.07679 | 0.073044 | 0.093334 | 0.099435 |  |
| tier_a_warm_client_return_1 | 10 | 0.072755 | 0.070388 | 0.085589 | 0.088896 |  |
| tier_a_warm_count_nodes | 10 | 0.078248 | 0.078095 | 0.089096 | 0.09228 |  |
| tier_b_alert_exact_early | 10 | 0.072164 | 0.070943 | 0.07892 | 0.081624 |  |
| tier_b_alert_exact_late | 10 | 0.077239 | 0.076884 | 0.089056 | 0.092563 |  |
| tier_b_decision_join_early | 10 | 0.07712 | 0.078423 | 0.08424 | 0.085329 |  |
| tier_b_decision_join_late | 10 | 0.082716 | 0.082136 | 0.089803 | 0.09046 |  |
| tier_b_decision_by_id_early | 10 | 0.077865 | 0.076687 | 0.094832 | 0.100327 |  |
| tier_b_decision_by_id_late | 10 | 0.083889 | 0.080113 | 0.097491 | 0.10118 |  |
| tier_c_alerts_prefix_count | 10 | 0.083342 | 0.088996 | 0.094959 | 0.095581 |  |
| tier_c_decisions_prefix_count | 10 | 0.077865 | 0.076059 | 0.095254 | 0.099104 |  |
| tier_c_verified_prefix_count | 10 | 0.078571 | 0.078068 | 0.097001 | 0.105766 |  |
| tier_c_outcome_present_prefix_count | 10 | 0.069116 | 0.066206 | 0.085226 | 0.089637 |  |
| tier_d_l5_centroid_count | 10 | 0.070369 | 0.069723 | 0.077758 | 0.081604 |  |
| tier_d_shaped_by_count | 10 | 0.073208 | 0.072594 | 0.084536 | 0.087466 |  |
| tier_d_l5_dk_weight_count | 10 | 0.076226 | 0.076843 | 0.082777 | 0.084377 |  |
| tier_d_dk_welford_read | 10 | 0.068987 | 0.068809 | 0.076233 | 0.077739 |  |
| tier_d_count_all_nodes | 10 | 0.078821 | 0.077591 | 0.094214 | 0.095431 |  |
| tier_d_count_all_edges | 10 | 0.13413 | 0.117012 | 0.214585 | 0.266304 |  |

## Diagnosis
```json
{
  "fresh_warm_ratio": 1.055,
  "point_lookup_avg_s": 0.078499,
  "point_lookup_slow": false,
  "prefix_scan_avg_s": 0.077224,
  "prefix_scan_ratio": 0.984,
  "likely_root_cause_candidates": [
    "no_age_read_only_gate_exceeded_by_script_01"
  ]
}
```
