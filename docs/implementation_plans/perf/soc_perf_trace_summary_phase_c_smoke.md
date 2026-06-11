# SOC Perf Trace Summary

## Safety
- Read-only summary of existing JSONL trace events.
- No backend, graph, proof, or seed operations are performed.
- Nested phases are not additive; request-total phases are the authoritative route totals.

## Input
- trace_jsonl: `C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50\scratch\temp\soc_perf_trace_phase_c_smoke.jsonl`
- events_loaded: 27
- malformed_lines: 0
- route_filter: None
- phase_filter: None

## Route + Phase Aggregates
```text
route_phase                                              count  avg_ms    p50_ms    p95_ms    p99_ms    max_ms  
-------------------------------------------------------  -----  --------  --------  --------  --------  --------
/api/alert/analyze | analyze_request_total               1      1688.737  1688.737  1688.737  1688.737  1688.737
/api/alert/outcome | outcome_request_total               1      1594.014  1594.014  1594.014  1594.014  1594.014
/api/alert/outcome | l5_centroid_write                   1      482.751   482.751   482.751   482.751   482.751 
/api/alert/outcome | conservation_monitor                1      430.826   430.826   430.826   430.826   430.826 
/api/alert/outcome | l5_conservation_write               1      428.623   428.623   428.623   428.623   428.623 
/api/alert/analyze | factor_vector_construction          1      335.627   335.627   335.627   335.627   335.627 
/api/alert/outcome | learning_state_update               1      108.379   108.379   108.379   108.379   108.379 
/api/alert/analyze | decision_node_and_edge_write        1      105.865   105.865   105.865   105.865   105.865 
/api/alert/outcome | snapshot_evolution_logging          2      49.526    49.526    93.03     96.897    97.864  
/api/alert/analyze | security_context_lookup             1      88.545    88.545    88.545    88.545    88.545  
/api/alert/outcome | decision_lookup_and_outcome_update  1      83.044    83.044    83.044    83.044    83.044  
/api/alert/analyze | audit_write                         1      82.685    82.685    82.685    82.685    82.685  
/api/alert/analyze | alert_lookup                        1      79.268    79.268    79.268    79.268    79.268  
/api/alert/analyze | category_resolution                 1      4.045     4.045     4.045     4.045     4.045   
/api/alert/outcome | outcome_audit_write                 1      0.583     0.583     0.583     0.583     0.583   
/api/alert/analyze | metadata_logging_snapshot_write     1      0.474     0.474     0.474     0.474     0.474   
/api/alert/analyze | scorer_decision                     1      0.353     0.353     0.353     0.353     0.353   
/api/alert/outcome | l5_dk_weight_write                  2      0.143     0.143     0.256     0.266     0.269   
/api/alert/analyze | response_serialization              1      0.175     0.175     0.175     0.175     0.175   
/api/alert/outcome | profile_scorer_update               1      0.143     0.143     0.143     0.143     0.143   
/api/alert/analyze | scorer_readiness                    1      0.029     0.029     0.029     0.029     0.029   
/api/alert/outcome | response_serialization              1      0.021     0.021     0.021     0.021     0.021   
/api/alert/analyze | request_parse                       1      0.017     0.017     0.017     0.017     0.017   
/api/alert/outcome | duplicate_feedback_guard            1      0.008     0.008     0.008     0.008     0.008   
/api/alert/outcome | request_parse                       1      0.006     0.006     0.006     0.006     0.006   
```

## Phase Aggregates
```text
phase                               count  avg_ms    p50_ms    p95_ms    p99_ms    max_ms  
----------------------------------  -----  --------  --------  --------  --------  --------
analyze_request_total               1      1688.737  1688.737  1688.737  1688.737  1688.737
outcome_request_total               1      1594.014  1594.014  1594.014  1594.014  1594.014
l5_centroid_write                   1      482.751   482.751   482.751   482.751   482.751 
conservation_monitor                1      430.826   430.826   430.826   430.826   430.826 
l5_conservation_write               1      428.623   428.623   428.623   428.623   428.623 
factor_vector_construction          1      335.627   335.627   335.627   335.627   335.627 
learning_state_update               1      108.379   108.379   108.379   108.379   108.379 
decision_node_and_edge_write        1      105.865   105.865   105.865   105.865   105.865 
snapshot_evolution_logging          2      49.526    49.526    93.03     96.897    97.864  
security_context_lookup             1      88.545    88.545    88.545    88.545    88.545  
decision_lookup_and_outcome_update  1      83.044    83.044    83.044    83.044    83.044  
audit_write                         1      82.685    82.685    82.685    82.685    82.685  
alert_lookup                        1      79.268    79.268    79.268    79.268    79.268  
category_resolution                 1      4.045     4.045     4.045     4.045     4.045   
outcome_audit_write                 1      0.583     0.583     0.583     0.583     0.583   
metadata_logging_snapshot_write     1      0.474     0.474     0.474     0.474     0.474   
scorer_decision                     1      0.353     0.353     0.353     0.353     0.353   
l5_dk_weight_write                  2      0.143     0.143     0.256     0.266     0.269   
response_serialization              2      0.098     0.098     0.167     0.173     0.175   
profile_scorer_update               1      0.143     0.143     0.143     0.143     0.143   
scorer_readiness                    1      0.029     0.029     0.029     0.029     0.029   
request_parse                       2      0.011     0.011     0.016     0.017     0.017   
duplicate_feedback_guard            1      0.008     0.008     0.008     0.008     0.008   
```

## Graph Aggregates
```text
graph_name                count  avg_ms   p50_ms  p95_ms    p99_ms    max_ms  
------------------------  -----  -------  ------  --------  --------  --------
soc_graph_phasec_smoke_1  27     207.909  4.045   1260.635  1664.109  1688.737
```

## Top Slow Events
```text
duration_ms  route               phase                               alert_id           decision_id                           attempt_index  status
-----------  ------------------  ----------------------------------  -----------------  ------------------------------------  -------------  ------
1688.737     /api/alert/analyze  analyze_request_total               PHASEC-SMOKE-0001  68841173-1da9-40f2-96b3-bb4df73e5a30  None           ok    
1594.014     /api/alert/outcome  outcome_request_total               PHASEC-SMOKE-0001  68841173-1da9-40f2-96b3-bb4df73e5a30  None           ok    
482.751      /api/alert/outcome  l5_centroid_write                   PHASEC-SMOKE-0001  68841173-1da9-40f2-96b3-bb4df73e5a30  None           ok    
430.826      /api/alert/outcome  conservation_monitor                PHASEC-SMOKE-0001  68841173-1da9-40f2-96b3-bb4df73e5a30  None           ok    
428.623      /api/alert/outcome  l5_conservation_write               PHASEC-SMOKE-0001  68841173-1da9-40f2-96b3-bb4df73e5a30  None           ok    
335.627      /api/alert/analyze  factor_vector_construction          PHASEC-SMOKE-0001  None                                  None           ok    
108.379      /api/alert/outcome  learning_state_update               PHASEC-SMOKE-0001  68841173-1da9-40f2-96b3-bb4df73e5a30  None           ok    
105.865      /api/alert/analyze  decision_node_and_edge_write        PHASEC-SMOKE-0001  68841173-1da9-40f2-96b3-bb4df73e5a30  None           ok    
97.864       /api/alert/outcome  snapshot_evolution_logging          PHASEC-SMOKE-0001  68841173-1da9-40f2-96b3-bb4df73e5a30  None           ok    
88.545       /api/alert/analyze  security_context_lookup             PHASEC-SMOKE-0001  None                                  None           ok    
83.044       /api/alert/outcome  decision_lookup_and_outcome_update  PHASEC-SMOKE-0001  68841173-1da9-40f2-96b3-bb4df73e5a30  None           ok    
82.685       /api/alert/analyze  audit_write                         PHASEC-SMOKE-0001  68841173-1da9-40f2-96b3-bb4df73e5a30  None           ok    
79.268       /api/alert/analyze  alert_lookup                        PHASEC-SMOKE-0001  None                                  None           ok    
4.045        /api/alert/analyze  category_resolution                 PHASEC-SMOKE-0001  None                                  None           ok    
1.188        /api/alert/outcome  snapshot_evolution_logging          PHASEC-SMOKE-0001  68841173-1da9-40f2-96b3-bb4df73e5a30  None           ok    
0.583        /api/alert/outcome  outcome_audit_write                 PHASEC-SMOKE-0001  68841173-1da9-40f2-96b3-bb4df73e5a30  None           ok    
0.474        /api/alert/analyze  metadata_logging_snapshot_write     PHASEC-SMOKE-0001  68841173-1da9-40f2-96b3-bb4df73e5a30  None           ok    
0.353        /api/alert/analyze  scorer_decision                     PHASEC-SMOKE-0001  None                                  None           ok    
0.269        /api/alert/outcome  l5_dk_weight_write                  PHASEC-SMOKE-0001  68841173-1da9-40f2-96b3-bb4df73e5a30  None           ok    
0.175        /api/alert/analyze  response_serialization              PHASEC-SMOKE-0001  68841173-1da9-40f2-96b3-bb4df73e5a30  None           ok    
```

## Early/Mid/Late Windows
```text
(none)
```

## Per-Alert Waterfall

### PHASEC-SMOKE-0001
- event_count: 27
- total_observed_ms: 5613.556
- authoritative_total_ms: 1688.737
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.029        /api/alert/analyze  scorer_readiness                    ok    
0.017        /api/alert/analyze  request_parse                       ok    
79.268       /api/alert/analyze  alert_lookup                        ok    
88.545       /api/alert/analyze  security_context_lookup             ok    
4.045        /api/alert/analyze  category_resolution                 ok    
335.627      /api/alert/analyze  factor_vector_construction          ok    
0.353        /api/alert/analyze  scorer_decision                     ok    
105.865      /api/alert/analyze  decision_node_and_edge_write        ok    
82.685       /api/alert/analyze  audit_write                         ok    
0.474        /api/alert/analyze  metadata_logging_snapshot_write     ok    
0.175        /api/alert/analyze  response_serialization              ok    
1688.737     /api/alert/analyze  analyze_request_total               ok    
0.006        /api/alert/outcome  request_parse                       ok    
0.008        /api/alert/outcome  duplicate_feedback_guard            ok    
83.044       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.583        /api/alert/outcome  outcome_audit_write                 ok    
108.379      /api/alert/outcome  learning_state_update               ok    
428.623      /api/alert/outcome  l5_conservation_write               ok    
430.826      /api/alert/outcome  conservation_monitor                ok    
0.143        /api/alert/outcome  profile_scorer_update               ok    
0.269        /api/alert/outcome  l5_dk_weight_write                  ok    
482.751      /api/alert/outcome  l5_centroid_write                   ok    
0.017        /api/alert/outcome  l5_dk_weight_write                  ok    
1.188        /api/alert/outcome  snapshot_evolution_logging          ok    
97.864       /api/alert/outcome  snapshot_evolution_logging          ok    
0.021        /api/alert/outcome  response_serialization              ok    
1594.014     /api/alert/outcome  outcome_request_total               ok    
```

## Nested Phase Warning
Nested phase durations should not be summed blindly. Use analyze_request_total, outcome_request_total, or total_attempt as authoritative totals.
