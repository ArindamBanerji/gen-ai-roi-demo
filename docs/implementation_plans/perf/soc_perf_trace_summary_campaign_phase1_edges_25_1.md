# SOC Perf Trace Summary

## Safety
- Read-only summary of existing JSONL trace events.
- No backend, graph, proof, or seed operations are performed.
- Nested phases are not additive; request-total phases are the authoritative route totals.

## Input
- trace_jsonl: `C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50\scratch\temp\soc_perf_trace_campaign_phase1_edges_25_1.jsonl`
- events_loaded: 1270
- malformed_lines: 0
- route_filter: None
- phase_filter: None

## Route + Phase Aggregates
```text
route_phase                                                     count  avg_ms    p50_ms    p95_ms    p99_ms    max_ms  
--------------------------------------------------------------  -----  --------  --------  --------  --------  --------
/api/alert/analyze | analyze_request_total                      25     1741.035  1836.625  1921.668  1971.385  1986.526
/api/alert/outcome | outcome_request_total                      25     1642.483  1629.814  1822.001  1855.813  1865.626
/api/alert/analyze | campaign_correlation                       25     479.93    599.577   633.93    645.403   648.015 
/api/alert/analyze | campaign_correlation_summary               25     413.565   514.94    544.34    552.898   555.441 
/api/alert/outcome | l5_centroid_write                          25     448.209   455.684   499.881   516.005   519.727 
/api/alert/analyze | reasoning_generation                       25     104.125   85.808    120.623   398.592   485.663 
/api/alert/outcome | conservation_monitor                       25     429.098   436.234   457.884   460.95    461.557 
/api/alert/outcome | l5_conservation_write                      25     426.498   431.857   455.5     457.63    457.896 
/api/alert/outcome | learning_state_update                      25     137.577   121.204   242.161   352.266   384.839 
/api/alert/analyze | factor_vector_construction                 25     330.838   334.547   357.317   359.491   359.846 
/api/alert/analyze | referral_history_counts                    25     165.865   164.946   192.419   197.064   198.449 
/api/alert/analyze | campaign_query_member_edges_batch_create   19     89.079    86.306    110.166   150.602   160.711 
/api/alert/outcome | snapshot_evolution_logging                 50     48.477    70.099    112.925   136.232   148.808 
/api/alert/analyze | decision_node_and_edge_write               25     91.394    90.991    103.062   116.374   120.532 
/api/alert/analyze | graph_visualization_fetch                  25     88.594    89.565    105.074   113.831   116.476 
/api/alert/analyze | audit_write                                25     88.433    88.37     99.132    105.587   107.537 
/api/alert/analyze | alert_lookup                               25     83.053    80.995    103.165   105.185   105.525 
/api/alert/outcome | decision_lookup_and_outcome_update         25     85.52     86.491    95.819    102.98    105.15  
/api/alert/analyze | security_context_lookup                    25     88.766    88.995    98.872    101.56    102.308 
/api/alert/analyze | campaign_query_update_campaign             13     87.661    87.943    101.047   101.609   101.749 
/api/alert/analyze | campaign_query_fetch_recent_events         25     84.108    84.891    98.99     100.255   100.509 
/api/alert/analyze | campaign_query_check_campaign_exists       19     81.928    80.64     95.373    98.638    99.454  
/api/alert/analyze | campaign_query_member_edges_existing_read  19     81.864    81.851    93.469    98.047    99.192  
/api/alert/analyze | campaign_query_create_campaign             6      83.766    86.035    97.647    98.401    98.59   
/api/alert/analyze | composite_gate_evaluation                  25     80.297    82.413    92.005    95.559    96.66   
/api/alert/analyze | campaign_query_member_alert_nodes_read     19     81.827    84.513    92.793    93.668    93.887  
/api/alert/analyze | cluster_history_fetch                      25     78.14     79.053    87.084    89.941    90.771  
/api/alert/outcome | outcome_audit_write                        25     1.114     0.333     0.96      14.449    18.701  
/api/alert/analyze | post_scorer_confidence_gate                25     0.461     0.023     0.061     8.349     10.964  
/api/alert/analyze | category_resolution                        25     0.565     0.155     0.773     7.378     9.427   
/api/alert/analyze | scorer_decision                            25     0.528     0.243     0.555     5.426     6.957   
/api/alert/analyze | response_serialization                     25     3.449     3.125     5.347     5.435     5.454   
/api/alert/analyze | metadata_logging_snapshot_write            25     0.784     0.601     2.089     2.843     3.072   
/api/alert/outcome | l5_dk_weight_write                         50     0.153     0.085     0.314     1.427     2.424   
/api/alert/outcome | profile_scorer_update                      25     0.206     0.173     0.348     0.402     0.417   
/api/alert/analyze | provenance_build                           25     0.081     0.068     0.165     0.215     0.229   
/api/alert/analyze | routing_threshold_lookup                   25     0.02      0.011     0.028     0.168     0.211   
/api/alert/analyze | response_context_enrichment                25     0.041     0.031     0.06      0.146     0.173   
/api/alert/analyze | referral_gate_evaluation                   25     0.058     0.057     0.082     0.115     0.125   
/api/alert/analyze | shadow_compare_schedule                    25     0.027     0.021     0.095     0.12      0.123   
```

## Phase Aggregates
```text
phase                                      count  avg_ms    p50_ms    p95_ms    p99_ms    max_ms  
-----------------------------------------  -----  --------  --------  --------  --------  --------
analyze_request_total                      25     1741.035  1836.625  1921.668  1971.385  1986.526
outcome_request_total                      25     1642.483  1629.814  1822.001  1855.813  1865.626
campaign_correlation                       25     479.93    599.577   633.93    645.403   648.015 
campaign_correlation_summary               25     413.565   514.94    544.34    552.898   555.441 
l5_centroid_write                          25     448.209   455.684   499.881   516.005   519.727 
reasoning_generation                       25     104.125   85.808    120.623   398.592   485.663 
conservation_monitor                       25     429.098   436.234   457.884   460.95    461.557 
l5_conservation_write                      25     426.498   431.857   455.5     457.63    457.896 
learning_state_update                      25     137.577   121.204   242.161   352.266   384.839 
factor_vector_construction                 25     330.838   334.547   357.317   359.491   359.846 
referral_history_counts                    25     165.865   164.946   192.419   197.064   198.449 
campaign_query_member_edges_batch_create   19     89.079    86.306    110.166   150.602   160.711 
snapshot_evolution_logging                 50     48.477    70.099    112.925   136.232   148.808 
decision_node_and_edge_write               25     91.394    90.991    103.062   116.374   120.532 
graph_visualization_fetch                  25     88.594    89.565    105.074   113.831   116.476 
audit_write                                25     88.433    88.37     99.132    105.587   107.537 
alert_lookup                               25     83.053    80.995    103.165   105.185   105.525 
decision_lookup_and_outcome_update         25     85.52     86.491    95.819    102.98    105.15  
security_context_lookup                    25     88.766    88.995    98.872    101.56    102.308 
campaign_query_update_campaign             13     87.661    87.943    101.047   101.609   101.749 
campaign_query_fetch_recent_events         25     84.108    84.891    98.99     100.255   100.509 
campaign_query_check_campaign_exists       19     81.928    80.64     95.373    98.638    99.454  
campaign_query_member_edges_existing_read  19     81.864    81.851    93.469    98.047    99.192  
campaign_query_create_campaign             6      83.766    86.035    97.647    98.401    98.59   
composite_gate_evaluation                  25     80.297    82.413    92.005    95.559    96.66   
campaign_query_member_alert_nodes_read     19     81.827    84.513    92.793    93.668    93.887  
cluster_history_fetch                      25     78.14     79.053    87.084    89.941    90.771  
outcome_audit_write                        25     1.114     0.333     0.96      14.449    18.701  
post_scorer_confidence_gate                25     0.461     0.023     0.061     8.349     10.964  
category_resolution                        25     0.565     0.155     0.773     7.378     9.427   
scorer_decision                            25     0.528     0.243     0.555     5.426     6.957   
response_serialization                     50     1.739     0.864     5.169     5.416     5.454   
metadata_logging_snapshot_write            25     0.784     0.601     2.089     2.843     3.072   
l5_dk_weight_write                         50     0.153     0.085     0.314     1.427     2.424   
profile_scorer_update                      25     0.206     0.173     0.348     0.402     0.417   
provenance_build                           25     0.081     0.068     0.165     0.215     0.229   
routing_threshold_lookup                   25     0.02      0.011     0.028     0.168     0.211   
response_context_enrichment                25     0.041     0.031     0.06      0.146     0.173   
referral_gate_evaluation                   25     0.058     0.057     0.082     0.115     0.125   
shadow_compare_schedule                    25     0.027     0.021     0.095     0.12      0.123   
```

## Graph Aggregates
```text
graph_name                            count  avg_ms   p50_ms  p95_ms   p99_ms    max_ms  
------------------------------------  -----  -------  ------  -------  --------  --------
soc_graph_campaign_phase1_edges_25_1  1270   147.884  3.736   590.406  1837.938  1986.526
```

## Top Slow Events
```text
duration_ms  route               phase                  alert_id             decision_id                           attempt_index  status
-----------  ------------------  ---------------------  -------------------  ------------------------------------  -------------  ------
1986.526     /api/alert/analyze  analyze_request_total  CAMPAIGNP1EDGE-0018  1babc1b1-d426-4296-993f-ad6d261cd16c  None           ok    
1923.437     /api/alert/analyze  analyze_request_total  CAMPAIGNP1EDGE-0009  faaf7938-d745-4db0-91f3-b0ce49f249d0  None           ok    
1914.592     /api/alert/analyze  analyze_request_total  CAMPAIGNP1EDGE-0021  c0cfab2a-b93c-4750-ac9e-142d12434733  None           ok    
1905.713     /api/alert/analyze  analyze_request_total  CAMPAIGNP1EDGE-0012  d4db1f08-9292-49c6-b4c1-a193944b2462  None           ok    
1889.04      /api/alert/analyze  analyze_request_total  CAMPAIGNP1EDGE-0016  c76673c1-5adf-4d1f-84e6-06cfba02fac7  None           ok    
1887.14      /api/alert/analyze  analyze_request_total  CAMPAIGNP1EDGE-0022  868292ee-1da9-40a2-b38c-ae40bea521ac  None           ok    
1869.533     /api/alert/analyze  analyze_request_total  CAMPAIGNP1EDGE-0010  503eefee-7d5d-48fb-be0d-951bd5716400  None           ok    
1865.626     /api/alert/outcome  outcome_request_total  CAMPAIGNP1EDGE-0003  8b6d418d-5b5b-447f-ad14-fc89e9b077ee  None           ok    
1860.688     /api/alert/analyze  analyze_request_total  CAMPAIGNP1EDGE-0019  22898eb1-b17b-4b30-8b19-97b99760b893  None           ok    
1859.232     /api/alert/analyze  analyze_request_total  CAMPAIGNP1EDGE-0024  d1fd84db-15ef-4ca9-b7f9-c0d65d3eb55b  None           ok    
1853.963     /api/alert/analyze  analyze_request_total  CAMPAIGNP1EDGE-0025  717f370d-1cef-4e3d-8fa6-b6f5582804c1  None           ok    
1841.999     /api/alert/analyze  analyze_request_total  CAMPAIGNP1EDGE-0007  cd9bbf2c-b5e2-4a1d-bcb8-e21e5d1a3f62  None           ok    
1840.861     /api/alert/analyze  analyze_request_total  CAMPAIGNP1EDGE-0017  7ec80906-5b74-4139-b164-dfa779e73b01  None           ok    
1836.625     /api/alert/analyze  analyze_request_total  CAMPAIGNP1EDGE-0011  e4b70800-aabf-408c-b762-dbd4610f2b4a  None           ok    
1834.228     /api/alert/analyze  analyze_request_total  CAMPAIGNP1EDGE-0023  fe2c9edd-f329-4583-bb56-e265e39b0ac4  None           ok    
1833.327     /api/alert/analyze  analyze_request_total  CAMPAIGNP1EDGE-0020  723a402b-f786-4017-8311-adbd1ca92098  None           ok    
1824.739     /api/alert/outcome  outcome_request_total  CAMPAIGNP1EDGE-0016  c76673c1-5adf-4d1f-84e6-06cfba02fac7  None           ok    
1822.922     /api/alert/analyze  analyze_request_total  CAMPAIGNP1EDGE-0015  8811e891-e414-4585-90bf-0d95aa87ed17  None           ok    
1811.051     /api/alert/outcome  outcome_request_total  CAMPAIGNP1EDGE-0022  868292ee-1da9-40a2-b38c-ae40bea521ac  None           ok    
1799.479     /api/alert/analyze  analyze_request_total  CAMPAIGNP1EDGE-0008  c000d2ad-92de-4254-8d6a-74660f6f2d54  None           ok    
1791.317     /api/alert/analyze  analyze_request_total  CAMPAIGNP1EDGE-0013  27171bcc-8255-4ec2-9571-327ebc421d61  None           ok    
1780.921     /api/alert/analyze  analyze_request_total  CAMPAIGNP1EDGE-0014  5a53607b-f217-46a9-ba53-70427b843798  None           ok    
1774.07      /api/alert/outcome  outcome_request_total  CAMPAIGNP1EDGE-0015  8811e891-e414-4585-90bf-0d95aa87ed17  None           ok    
1759.062     /api/alert/outcome  outcome_request_total  CAMPAIGNP1EDGE-0018  1babc1b1-d426-4296-993f-ad6d261cd16c  None           ok    
1736.085     /api/alert/outcome  outcome_request_total  CAMPAIGNP1EDGE-0021  c0cfab2a-b93c-4750-ac9e-142d12434733  None           ok    
1724.468     /api/alert/analyze  analyze_request_total  CAMPAIGNP1EDGE-0001  bae0803e-b3c0-49bf-9bb9-f90e8be33108  None           ok    
1707.411     /api/alert/outcome  outcome_request_total  CAMPAIGNP1EDGE-0023  fe2c9edd-f329-4583-bb56-e265e39b0ac4  None           ok    
1699.431     /api/alert/outcome  outcome_request_total  CAMPAIGNP1EDGE-0020  723a402b-f786-4017-8311-adbd1ca92098  None           ok    
1670.524     /api/alert/outcome  outcome_request_total  CAMPAIGNP1EDGE-0012  d4db1f08-9292-49c6-b4c1-a193944b2462  None           ok    
1668.949     /api/alert/outcome  outcome_request_total  CAMPAIGNP1EDGE-0019  22898eb1-b17b-4b30-8b19-97b99760b893  None           ok    
```

## Early/Mid/Late Windows
```text
(none)
```

## Per-Alert Waterfall

### CAMPAIGNP1EDGE-0018
- event_count: 52
- total_observed_ms: 8448.102
- authoritative_total_ms: 1986.526
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.028        /api/alert/analyze  scorer_readiness                           ok    
0.017        /api/alert/analyze  request_parse                              ok    
83.978       /api/alert/analyze  alert_lookup                               ok    
102.308      /api/alert/analyze  security_context_lookup                    ok    
0.889        /api/alert/analyze  category_resolution                        ok    
338.606      /api/alert/analyze  factor_vector_construction                 ok    
0.188        /api/alert/analyze  scorer_decision                            ok    
0.013        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.007        /api/alert/analyze  routing_threshold_lookup                   ok    
0.013        /api/alert/analyze  rl_exploration_proposal                    ok    
0.015        /api/alert/analyze  routing_zone_resolution                    ok    
192.678      /api/alert/analyze  referral_history_counts                    ok    
0.036        /api/alert/analyze  referral_gate_evaluation                   ok    
97.489       /api/alert/analyze  reasoning_generation                       ok    
86.915       /api/alert/analyze  decision_node_and_edge_write               ok    
94.834       /api/alert/analyze  audit_write                                ok    
1.421        /api/alert/analyze  metadata_logging_snapshot_write            ok    
91.48        /api/alert/analyze  campaign_query_fetch_recent_events         ok    
99.454       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
99.851       /api/alert/analyze  campaign_query_update_campaign             ok    
82.487       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
91.212       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
77.617       /api/alert/analyze  campaign_query_member_edges_batch_create   ok    
555.441      /api/alert/analyze  campaign_correlation_summary               ok    
648.015      /api/alert/analyze  campaign_correlation                       ok    
0.021        /api/alert/analyze  decision_event_emit                        ok    
88.927       /api/alert/analyze  composite_gate_evaluation                  ok    
0.106        /api/alert/analyze  provenance_build                           ok    
89.565       /api/alert/analyze  graph_visualization_fetch                  ok    
0.044        /api/alert/analyze  response_context_enrichment                ok    
0.051        /api/alert/analyze  referral_debug_build                       ok    
0.112        /api/alert/analyze  shadow_compare_schedule                    ok    
90.771       /api/alert/analyze  cluster_history_fetch                      ok    
0.079        /api/alert/analyze  narrative_context_build                    ok    
0.044        /api/alert/analyze  narrative_generation                       ok    
4.607        /api/alert/analyze  response_serialization                     ok    
1986.526     /api/alert/analyze  analyze_request_total                      ok    
0.018        /api/alert/outcome  request_parse                              ok    
0.021        /api/alert/outcome  duplicate_feedback_guard                   ok    
90.241       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.4          /api/alert/outcome  outcome_audit_write                        ok    
183.183      /api/alert/outcome  learning_state_update                      ok    
431.576      /api/alert/outcome  l5_conservation_write                      ok    
433.841      /api/alert/outcome  conservation_monitor                       ok    
0.216        /api/alert/outcome  profile_scorer_update                      ok    
0.183        /api/alert/outcome  l5_dk_weight_write                         ok    
464.472      /api/alert/outcome  l5_centroid_write                          ok    
0.013        /api/alert/outcome  l5_dk_weight_write                         ok    
0.015        /api/alert/outcome  snapshot_evolution_logging                 ok    
78.992       /api/alert/outcome  snapshot_evolution_logging                 ok    
0.024        /api/alert/outcome  response_serialization                     ok    
1759.062     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1EDGE-0009
- event_count: 52
- total_observed_ms: 8058.007
- authoritative_total_ms: 1923.437
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.014        /api/alert/analyze  scorer_readiness                           ok    
0.006        /api/alert/analyze  request_parse                              ok    
88.888       /api/alert/analyze  alert_lookup                               ok    
97.586       /api/alert/analyze  security_context_lookup                    ok    
0.155        /api/alert/analyze  category_resolution                        ok    
344.339      /api/alert/analyze  factor_vector_construction                 ok    
0.182        /api/alert/analyze  scorer_decision                            ok    
0.024        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.03         /api/alert/analyze  routing_threshold_lookup                   ok    
0.021        /api/alert/analyze  rl_exploration_proposal                    ok    
0.06         /api/alert/analyze  routing_zone_resolution                    ok    
198.449      /api/alert/analyze  referral_history_counts                    ok    
0.038        /api/alert/analyze  referral_gate_evaluation                   ok    
79.027       /api/alert/analyze  reasoning_generation                       ok    
93.538       /api/alert/analyze  decision_node_and_edge_write               ok    
76.691       /api/alert/analyze  audit_write                                ok    
0.24         /api/alert/analyze  metadata_logging_snapshot_write            ok    
79.806       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
75.964       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
94.819       /api/alert/analyze  campaign_query_create_campaign             ok    
92.833       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
73.978       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
93.246       /api/alert/analyze  campaign_query_member_edges_batch_create   ok    
522.217      /api/alert/analyze  campaign_correlation_summary               ok    
618.694      /api/alert/analyze  campaign_correlation                       ok    
0.037        /api/alert/analyze  decision_event_emit                        ok    
96.66        /api/alert/analyze  composite_gate_evaluation                  ok    
0.075        /api/alert/analyze  provenance_build                           ok    
92.39        /api/alert/analyze  graph_visualization_fetch                  ok    
0.029        /api/alert/analyze  response_context_enrichment                ok    
0.034        /api/alert/analyze  referral_debug_build                       ok    
0.027        /api/alert/analyze  shadow_compare_schedule                    ok    
83.865       /api/alert/analyze  cluster_history_fetch                      ok    
0.06         /api/alert/analyze  narrative_context_build                    ok    
0.085        /api/alert/analyze  narrative_generation                       ok    
4.634        /api/alert/analyze  response_serialization                     ok    
1923.437     /api/alert/analyze  analyze_request_total                      ok    
0.018        /api/alert/outcome  request_parse                              ok    
0.019        /api/alert/outcome  duplicate_feedback_guard                   ok    
94.657       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.365        /api/alert/outcome  outcome_audit_write                        ok    
79.447       /api/alert/outcome  learning_state_update                      ok    
412.781      /api/alert/outcome  l5_conservation_write                      ok    
415.105      /api/alert/outcome  conservation_monitor                       ok    
0.296        /api/alert/outcome  profile_scorer_update                      ok    
0.158        /api/alert/outcome  l5_dk_weight_write                         ok    
456.187      /api/alert/outcome  l5_centroid_write                          ok    
0.021        /api/alert/outcome  l5_dk_weight_write                         ok    
0.016        /api/alert/outcome  snapshot_evolution_logging                 ok    
148.808      /api/alert/outcome  snapshot_evolution_logging                 ok    
0.042        /api/alert/outcome  response_serialization                     ok    
1617.909     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1EDGE-0021
- event_count: 52
- total_observed_ms: 8266.308
- authoritative_total_ms: 1914.592
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.014        /api/alert/analyze  scorer_readiness                           ok    
0.006        /api/alert/analyze  request_parse                              ok    
73.873       /api/alert/analyze  alert_lookup                               ok    
91.34        /api/alert/analyze  security_context_lookup                    ok    
0.103        /api/alert/analyze  category_resolution                        ok    
358.365      /api/alert/analyze  factor_vector_construction                 ok    
0.254        /api/alert/analyze  scorer_decision                            ok    
0.025        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.016        /api/alert/analyze  routing_threshold_lookup                   ok    
0.028        /api/alert/analyze  rl_exploration_proposal                    ok    
0.03         /api/alert/analyze  routing_zone_resolution                    ok    
179.758      /api/alert/analyze  referral_history_counts                    ok    
0.065        /api/alert/analyze  referral_gate_evaluation                   ok    
98.912       /api/alert/analyze  reasoning_generation                       ok    
83.559       /api/alert/analyze  decision_node_and_edge_write               ok    
82.191       /api/alert/analyze  audit_write                                ok    
0.795        /api/alert/analyze  metadata_logging_snapshot_write            ok    
87.27        /api/alert/analyze  campaign_query_fetch_recent_events         ok    
73.7         /api/alert/analyze  campaign_query_check_campaign_exists       ok    
91.607       /api/alert/analyze  campaign_query_update_campaign             ok    
78.869       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
92.672       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
94.244       /api/alert/analyze  campaign_query_member_edges_batch_create   ok    
531.325      /api/alert/analyze  campaign_correlation_summary               ok    
610.502      /api/alert/analyze  campaign_correlation                       ok    
0.022        /api/alert/analyze  decision_event_emit                        ok    
71.33        /api/alert/analyze  composite_gate_evaluation                  ok    
0.05         /api/alert/analyze  provenance_build                           ok    
116.476      /api/alert/analyze  graph_visualization_fetch                  ok    
0.026        /api/alert/analyze  response_context_enrichment                ok    
0.051        /api/alert/analyze  referral_debug_build                       ok    
0.028        /api/alert/analyze  shadow_compare_schedule                    ok    
85.522       /api/alert/analyze  cluster_history_fetch                      ok    
0.057        /api/alert/analyze  narrative_context_build                    ok    
0.076        /api/alert/analyze  narrative_generation                       ok    
4.953        /api/alert/analyze  response_serialization                     ok    
1914.592     /api/alert/analyze  analyze_request_total                      ok    
0.019        /api/alert/outcome  request_parse                              ok    
0.014        /api/alert/outcome  duplicate_feedback_guard                   ok    
105.15       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.17         /api/alert/outcome  outcome_audit_write                        ok    
175.621      /api/alert/outcome  learning_state_update                      ok    
432.611      /api/alert/outcome  l5_conservation_write                      ok    
436.756      /api/alert/outcome  conservation_monitor                       ok    
0.24         /api/alert/outcome  profile_scorer_update                      ok    
0.21         /api/alert/outcome  l5_dk_weight_write                         ok    
458.221      /api/alert/outcome  l5_centroid_write                          ok    
0.022        /api/alert/outcome  l5_dk_weight_write                         ok    
0.03         /api/alert/outcome  snapshot_evolution_logging                 ok    
98.425       /api/alert/outcome  snapshot_evolution_logging                 ok    
0.028        /api/alert/outcome  response_serialization                     ok    
1736.085     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1EDGE-0012
- event_count: 52
- total_observed_ms: 8130.234
- authoritative_total_ms: 1905.713
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.02         /api/alert/analyze  scorer_readiness                           ok    
0.042        /api/alert/analyze  request_parse                              ok    
104.107      /api/alert/analyze  alert_lookup                               ok    
91.398       /api/alert/analyze  security_context_lookup                    ok    
0.179        /api/alert/analyze  category_resolution                        ok    
344.446      /api/alert/analyze  factor_vector_construction                 ok    
0.34         /api/alert/analyze  scorer_decision                            ok    
0.017        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.008        /api/alert/analyze  routing_threshold_lookup                   ok    
0.012        /api/alert/analyze  rl_exploration_proposal                    ok    
0.027        /api/alert/analyze  routing_zone_resolution                    ok    
157.218      /api/alert/analyze  referral_history_counts                    ok    
0.057        /api/alert/analyze  referral_gate_evaluation                   ok    
82.288       /api/alert/analyze  reasoning_generation                       ok    
88.083       /api/alert/analyze  decision_node_and_edge_write               ok    
84.094       /api/alert/analyze  audit_write                                ok    
0.771        /api/alert/analyze  metadata_logging_snapshot_write            ok    
84.362       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
87.471       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
83.151       /api/alert/analyze  campaign_query_create_campaign             ok    
75.988       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
84.813       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
91.427       /api/alert/analyze  campaign_query_member_edges_batch_create   ok    
518.44       /api/alert/analyze  campaign_correlation_summary               ok    
612.425      /api/alert/analyze  campaign_correlation                       ok    
0.026        /api/alert/analyze  decision_event_emit                        ok    
89.301       /api/alert/analyze  composite_gate_evaluation                  ok    
0.087        /api/alert/analyze  provenance_build                           ok    
103.54       /api/alert/analyze  graph_visualization_fetch                  ok    
0.047        /api/alert/analyze  response_context_enrichment                ok    
0.05         /api/alert/analyze  referral_debug_build                       ok    
0.026        /api/alert/analyze  shadow_compare_schedule                    ok    
81.761       /api/alert/analyze  cluster_history_fetch                      ok    
0.063        /api/alert/analyze  narrative_context_build                    ok    
0.079        /api/alert/analyze  narrative_generation                       ok    
5.376        /api/alert/analyze  response_serialization                     ok    
1905.713     /api/alert/analyze  analyze_request_total                      ok    
0.021        /api/alert/outcome  request_parse                              ok    
0.015        /api/alert/outcome  duplicate_feedback_guard                   ok    
92.143       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.782        /api/alert/outcome  outcome_audit_write                        ok    
140.547      /api/alert/outcome  learning_state_update                      ok    
445.474      /api/alert/outcome  l5_conservation_write                      ok    
448.449      /api/alert/outcome  conservation_monitor                       ok    
0.159        /api/alert/outcome  profile_scorer_update                      ok    
0.105        /api/alert/outcome  l5_dk_weight_write                         ok    
472.517      /api/alert/outcome  l5_centroid_write                          ok    
0.026        /api/alert/outcome  l5_dk_weight_write                         ok    
0.041        /api/alert/outcome  snapshot_evolution_logging                 ok    
82.158       /api/alert/outcome  snapshot_evolution_logging                 ok    
0.02         /api/alert/outcome  response_serialization                     ok    
1670.524     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1EDGE-0016
- event_count: 52
- total_observed_ms: 8405.089
- authoritative_total_ms: 1889.04
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.025        /api/alert/analyze  scorer_readiness                           ok    
0.013        /api/alert/analyze  request_parse                              ok    
97.885       /api/alert/analyze  alert_lookup                               ok    
86.554       /api/alert/analyze  security_context_lookup                    ok    
0.114        /api/alert/analyze  category_resolution                        ok    
353.123      /api/alert/analyze  factor_vector_construction                 ok    
0.198        /api/alert/analyze  scorer_decision                            ok    
0.023        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.011        /api/alert/analyze  routing_threshold_lookup                   ok    
0.029        /api/alert/analyze  rl_exploration_proposal                    ok    
0.015        /api/alert/analyze  routing_zone_resolution                    ok    
164.946      /api/alert/analyze  referral_history_counts                    ok    
0.038        /api/alert/analyze  referral_gate_evaluation                   ok    
75.527       /api/alert/analyze  reasoning_generation                       ok    
91.038       /api/alert/analyze  decision_node_and_edge_write               ok    
99.412       /api/alert/analyze  audit_write                                ok    
0.818        /api/alert/analyze  metadata_logging_snapshot_write            ok    
79.01        /api/alert/analyze  campaign_query_fetch_recent_events         ok    
91.512       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
73.727       /api/alert/analyze  campaign_query_update_campaign             ok    
85.791       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
86.848       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
85.88        /api/alert/analyze  campaign_query_member_edges_batch_create   ok    
514.94       /api/alert/analyze  campaign_correlation_summary               ok    
604.427      /api/alert/analyze  campaign_correlation                       ok    
0.021        /api/alert/analyze  decision_event_emit                        ok    
82.652       /api/alert/analyze  composite_gate_evaluation                  ok    
0.068        /api/alert/analyze  provenance_build                           ok    
97.388       /api/alert/analyze  graph_visualization_fetch                  ok    
0.173        /api/alert/analyze  response_context_enrichment                ok    
0.044        /api/alert/analyze  referral_debug_build                       ok    
0.123        /api/alert/analyze  shadow_compare_schedule                    ok    
76.342       /api/alert/analyze  cluster_history_fetch                      ok    
0.043        /api/alert/analyze  narrative_context_build                    ok    
0.049        /api/alert/analyze  narrative_generation                       ok    
4.107        /api/alert/analyze  response_serialization                     ok    
1889.04      /api/alert/analyze  analyze_request_total                      ok    
0.018        /api/alert/outcome  request_parse                              ok    
0.03         /api/alert/outcome  duplicate_feedback_guard                   ok    
89.173       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.456        /api/alert/outcome  outcome_audit_write                        ok    
249.117      /api/alert/outcome  learning_state_update                      ok    
438.464      /api/alert/outcome  l5_conservation_write                      ok    
441.898      /api/alert/outcome  conservation_monitor                       ok    
0.417        /api/alert/outcome  profile_scorer_update                      ok    
0.18         /api/alert/outcome  l5_dk_weight_write                         ok    
519.727      /api/alert/outcome  l5_centroid_write                          ok    
0.016        /api/alert/outcome  l5_dk_weight_write                         ok    
0.027        /api/alert/outcome  snapshot_evolution_logging                 ok    
98.841       /api/alert/outcome  snapshot_evolution_logging                 ok    
0.032        /api/alert/outcome  response_serialization                     ok    
1824.739     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1EDGE-0022
- event_count: 52
- total_observed_ms: 8317.155
- authoritative_total_ms: 1887.14
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.035        /api/alert/analyze  scorer_readiness                           ok    
0.014        /api/alert/analyze  request_parse                              ok    
105.525      /api/alert/analyze  alert_lookup                               ok    
82.663       /api/alert/analyze  security_context_lookup                    ok    
0.114        /api/alert/analyze  category_resolution                        ok    
327.923      /api/alert/analyze  factor_vector_construction                 ok    
0.315        /api/alert/analyze  scorer_decision                            ok    
0.03         /api/alert/analyze  post_scorer_confidence_gate                ok    
0.016        /api/alert/analyze  routing_threshold_lookup                   ok    
0.026        /api/alert/analyze  rl_exploration_proposal                    ok    
0.026        /api/alert/analyze  routing_zone_resolution                    ok    
163.874      /api/alert/analyze  referral_history_counts                    ok    
0.068        /api/alert/analyze  referral_gate_evaluation                   ok    
83.043       /api/alert/analyze  reasoning_generation                       ok    
100.233      /api/alert/analyze  decision_node_and_edge_write               ok    
90.796       /api/alert/analyze  audit_write                                ok    
0.699        /api/alert/analyze  metadata_logging_snapshot_write            ok    
85.22        /api/alert/analyze  campaign_query_fetch_recent_events         ok    
93.591       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
80.618       /api/alert/analyze  campaign_query_update_campaign             ok    
81.851       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
86.254       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
80.046       /api/alert/analyze  campaign_query_member_edges_batch_create   ok    
520.076      /api/alert/analyze  campaign_correlation_summary               ok    
601.859      /api/alert/analyze  campaign_correlation                       ok    
0.021        /api/alert/analyze  decision_event_emit                        ok    
86.289       /api/alert/analyze  composite_gate_evaluation                  ok    
0.05         /api/alert/analyze  provenance_build                           ok    
94.76        /api/alert/analyze  graph_visualization_fetch                  ok    
0.029        /api/alert/analyze  response_context_enrichment                ok    
0.028        /api/alert/analyze  referral_debug_build                       ok    
0.012        /api/alert/analyze  shadow_compare_schedule                    ok    
84.073       /api/alert/analyze  cluster_history_fetch                      ok    
0.044        /api/alert/analyze  narrative_context_build                    ok    
0.061        /api/alert/analyze  narrative_generation                       ok    
3.395        /api/alert/analyze  response_serialization                     ok    
1887.14      /api/alert/analyze  analyze_request_total                      ok    
0.021        /api/alert/outcome  request_parse                              ok    
0.025        /api/alert/outcome  duplicate_feedback_guard                   ok    
86.491       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.241        /api/alert/outcome  outcome_audit_write                        ok    
184.756      /api/alert/outcome  learning_state_update                      ok    
419.483      /api/alert/outcome  l5_conservation_write                      ok    
423.74       /api/alert/outcome  conservation_monitor                       ok    
0.244        /api/alert/outcome  profile_scorer_update                      ok    
0.193        /api/alert/outcome  l5_dk_weight_write                         ok    
468.706      /api/alert/outcome  l5_centroid_write                          ok    
0.026        /api/alert/outcome  l5_dk_weight_write                         ok    
91.837       /api/alert/outcome  snapshot_evolution_logging                 ok    
89.5         /api/alert/outcome  snapshot_evolution_logging                 ok    
0.024        /api/alert/outcome  response_serialization                     ok    
1811.051     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1EDGE-0010
- event_count: 52
- total_observed_ms: 7746.243
- authoritative_total_ms: 1869.533
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.028        /api/alert/analyze  scorer_readiness                           ok    
0.017        /api/alert/analyze  request_parse                              ok    
84.099       /api/alert/analyze  alert_lookup                               ok    
92.63        /api/alert/analyze  security_context_lookup                    ok    
0.223        /api/alert/analyze  category_resolution                        ok    
359.846      /api/alert/analyze  factor_vector_construction                 ok    
0.347        /api/alert/analyze  scorer_decision                            ok    
0.032        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.018        /api/alert/analyze  routing_threshold_lookup                   ok    
0.027        /api/alert/analyze  rl_exploration_proposal                    ok    
0.029        /api/alert/analyze  routing_zone_resolution                    ok    
168.062      /api/alert/analyze  referral_history_counts                    ok    
0.073        /api/alert/analyze  referral_gate_evaluation                   ok    
101.543      /api/alert/analyze  reasoning_generation                       ok    
70.568       /api/alert/analyze  decision_node_and_edge_write               ok    
81.798       /api/alert/analyze  audit_write                                ok    
0.148        /api/alert/analyze  metadata_logging_snapshot_write            ok    
71.79        /api/alert/analyze  campaign_query_fetch_recent_events         ok    
67.601       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
64.336       /api/alert/analyze  campaign_query_create_campaign             ok    
82.14        /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
84.513       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
91.679       /api/alert/analyze  campaign_query_member_edges_batch_create   ok    
474.451      /api/alert/analyze  campaign_correlation_summary               ok    
585.51       /api/alert/analyze  campaign_correlation                       ok    
0.022        /api/alert/analyze  decision_event_emit                        ok    
87.745       /api/alert/analyze  composite_gate_evaluation                  ok    
0.074        /api/alert/analyze  provenance_build                           ok    
94.106       /api/alert/analyze  graph_visualization_fetch                  ok    
0.027        /api/alert/analyze  response_context_enrichment                ok    
0.034        /api/alert/analyze  referral_debug_build                       ok    
0.012        /api/alert/analyze  shadow_compare_schedule                    ok    
84.704       /api/alert/analyze  cluster_history_fetch                      ok    
0.029        /api/alert/analyze  narrative_context_build                    ok    
0.036        /api/alert/analyze  narrative_generation                       ok    
2.065        /api/alert/analyze  response_serialization                     ok    
1869.533     /api/alert/analyze  analyze_request_total                      ok    
0.023        /api/alert/outcome  request_parse                              ok    
0.008        /api/alert/outcome  duplicate_feedback_guard                   ok    
78.195       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.212        /api/alert/outcome  outcome_audit_write                        ok    
63.381       /api/alert/outcome  learning_state_update                      ok    
456.789      /api/alert/outcome  l5_conservation_write                      ok    
459.027      /api/alert/outcome  conservation_monitor                       ok    
0.277        /api/alert/outcome  profile_scorer_update                      ok    
0.208        /api/alert/outcome  l5_dk_weight_write                         ok    
434.872      /api/alert/outcome  l5_centroid_write                          ok    
0.026        /api/alert/outcome  l5_dk_weight_write                         ok    
0.03         /api/alert/outcome  snapshot_evolution_logging                 ok    
71.842       /api/alert/outcome  snapshot_evolution_logging                 ok    
0.022        /api/alert/outcome  response_serialization                     ok    
1561.436     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1EDGE-0003
- event_count: 47
- total_observed_ms: 6442.021
- authoritative_total_ms: 1865.626
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.014        /api/alert/analyze  scorer_readiness                    ok    
0.011        /api/alert/analyze  request_parse                       ok    
68.844       /api/alert/analyze  alert_lookup                        ok    
88.995       /api/alert/analyze  security_context_lookup             ok    
0.143        /api/alert/analyze  category_resolution                 ok    
302.754      /api/alert/analyze  factor_vector_construction          ok    
0.172        /api/alert/analyze  scorer_decision                     ok    
0.02         /api/alert/analyze  post_scorer_confidence_gate         ok    
0.01         /api/alert/analyze  routing_threshold_lookup            ok    
0.013        /api/alert/analyze  rl_exploration_proposal             ok    
0.012        /api/alert/analyze  routing_zone_resolution             ok    
191.381      /api/alert/analyze  referral_history_counts             ok    
0.054        /api/alert/analyze  referral_gate_evaluation            ok    
111.652      /api/alert/analyze  reasoning_generation                ok    
120.532      /api/alert/analyze  decision_node_and_edge_write        ok    
91.717       /api/alert/analyze  audit_write                         ok    
0.502        /api/alert/analyze  metadata_logging_snapshot_write     ok    
81.254       /api/alert/analyze  campaign_query_fetch_recent_events  ok    
82.622       /api/alert/analyze  campaign_correlation_summary        ok    
83.581       /api/alert/analyze  campaign_correlation                ok    
0.041        /api/alert/analyze  decision_event_emit                 ok    
68.208       /api/alert/analyze  composite_gate_evaluation           ok    
0.054        /api/alert/analyze  provenance_build                    ok    
72.463       /api/alert/analyze  graph_visualization_fetch           ok    
0.036        /api/alert/analyze  response_context_enrichment         ok    
0.035        /api/alert/analyze  referral_debug_build                ok    
0.014        /api/alert/analyze  shadow_compare_schedule             ok    
66.349       /api/alert/analyze  cluster_history_fetch               ok    
0.03         /api/alert/analyze  narrative_context_build             ok    
0.043        /api/alert/analyze  narrative_generation                ok    
2.084        /api/alert/analyze  response_serialization              ok    
1314.702     /api/alert/analyze  analyze_request_total               ok    
0.007        /api/alert/outcome  request_parse                       ok    
0.01         /api/alert/outcome  duplicate_feedback_guard            ok    
92.43        /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.586        /api/alert/outcome  outcome_audit_write                 ok    
384.839      /api/alert/outcome  learning_state_update               ok    
407.569      /api/alert/outcome  l5_conservation_write               ok    
409.697      /api/alert/outcome  conservation_monitor                ok    
0.21         /api/alert/outcome  profile_scorer_update               ok    
0.197        /api/alert/outcome  l5_dk_weight_write                  ok    
416.07       /api/alert/outcome  l5_centroid_write                   ok    
0.282        /api/alert/outcome  l5_dk_weight_write                  ok    
0.026        /api/alert/outcome  snapshot_evolution_logging          ok    
116.102      /api/alert/outcome  snapshot_evolution_logging          ok    
0.028        /api/alert/outcome  response_serialization              ok    
1865.626     /api/alert/outcome  outcome_request_total               ok    
```

### CAMPAIGNP1EDGE-0019
- event_count: 52
- total_observed_ms: 7999.675
- authoritative_total_ms: 1860.688
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.03         /api/alert/analyze  scorer_readiness                           ok    
0.017        /api/alert/analyze  request_parse                              ok    
94.167       /api/alert/analyze  alert_lookup                               ok    
85.055       /api/alert/analyze  security_context_lookup                    ok    
0.307        /api/alert/analyze  category_resolution                        ok    
321.945      /api/alert/analyze  factor_vector_construction                 ok    
0.258        /api/alert/analyze  scorer_decision                            ok    
0.024        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.018        /api/alert/analyze  routing_threshold_lookup                   ok    
0.023        /api/alert/analyze  rl_exploration_proposal                    ok    
0.026        /api/alert/analyze  routing_zone_resolution                    ok    
168.852      /api/alert/analyze  referral_history_counts                    ok    
0.067        /api/alert/analyze  referral_gate_evaluation                   ok    
87.907       /api/alert/analyze  reasoning_generation                       ok    
83.047       /api/alert/analyze  decision_node_and_edge_write               ok    
90.906       /api/alert/analyze  audit_write                                ok    
2.116        /api/alert/analyze  metadata_logging_snapshot_write            ok    
90.584       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
92.523       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
87.943       /api/alert/analyze  campaign_query_update_campaign             ok    
87.732       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
84.708       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
86.306       /api/alert/analyze  campaign_query_member_edges_batch_create   ok    
542.326      /api/alert/analyze  campaign_correlation_summary               ok    
621.126      /api/alert/analyze  campaign_correlation                       ok    
0.047        /api/alert/analyze  decision_event_emit                        ok    
69.892       /api/alert/analyze  composite_gate_evaluation                  ok    
0.053        /api/alert/analyze  provenance_build                           ok    
90.876       /api/alert/analyze  graph_visualization_fetch                  ok    
0.023        /api/alert/analyze  response_context_enrichment                ok    
0.035        /api/alert/analyze  referral_debug_build                       ok    
0.015        /api/alert/analyze  shadow_compare_schedule                    ok    
76.91        /api/alert/analyze  cluster_history_fetch                      ok    
0.031        /api/alert/analyze  narrative_context_build                    ok    
0.04         /api/alert/analyze  narrative_generation                       ok    
3.404        /api/alert/analyze  response_serialization                     ok    
1860.688     /api/alert/analyze  analyze_request_total                      ok    
0.008        /api/alert/outcome  request_parse                              ok    
0.008        /api/alert/outcome  duplicate_feedback_guard                   ok    
83.322       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.23         /api/alert/outcome  outcome_audit_write                        ok    
100.599      /api/alert/outcome  learning_state_update                      ok    
436.004      /api/alert/outcome  l5_conservation_write                      ok    
437.663      /api/alert/outcome  conservation_monitor                       ok    
0.138        /api/alert/outcome  profile_scorer_update                      ok    
2.424        /api/alert/outcome  l5_dk_weight_write                         ok    
451.886      /api/alert/outcome  l5_centroid_write                          ok    
0.018        /api/alert/outcome  l5_dk_weight_write                         ok    
0.021        /api/alert/outcome  snapshot_evolution_logging                 ok    
88.346       /api/alert/outcome  snapshot_evolution_logging                 ok    
0.032        /api/alert/outcome  response_serialization                     ok    
1668.949     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1EDGE-0024
- event_count: 52
- total_observed_ms: 7973.608
- authoritative_total_ms: 1859.232
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.039        /api/alert/analyze  scorer_readiness                           ok    
0.006        /api/alert/analyze  request_parse                              ok    
80.995       /api/alert/analyze  alert_lookup                               ok    
97.513       /api/alert/analyze  security_context_lookup                    ok    
0.123        /api/alert/analyze  category_resolution                        ok    
343.792      /api/alert/analyze  factor_vector_construction                 ok    
0.311        /api/alert/analyze  scorer_decision                            ok    
0.015        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.007        /api/alert/analyze  routing_threshold_lookup                   ok    
0.012        /api/alert/analyze  rl_exploration_proposal                    ok    
0.012        /api/alert/analyze  routing_zone_resolution                    ok    
179.96       /api/alert/analyze  referral_history_counts                    ok    
0.056        /api/alert/analyze  referral_gate_evaluation                   ok    
79.591       /api/alert/analyze  reasoning_generation                       ok    
91.513       /api/alert/analyze  decision_node_and_edge_write               ok    
87.642       /api/alert/analyze  audit_write                                ok    
1.98         /api/alert/analyze  metadata_logging_snapshot_write            ok    
83.889       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
84.375       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
91.812       /api/alert/analyze  campaign_query_update_campaign             ok    
85.045       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
77.936       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
90.365       /api/alert/analyze  campaign_query_member_edges_batch_create   ok    
522.697      /api/alert/analyze  campaign_correlation_summary               ok    
599.577      /api/alert/analyze  campaign_correlation                       ok    
0.037        /api/alert/analyze  decision_event_emit                        ok    
75.143       /api/alert/analyze  composite_gate_evaluation                  ok    
0.055        /api/alert/analyze  provenance_build                           ok    
83.649       /api/alert/analyze  graph_visualization_fetch                  ok    
0.051        /api/alert/analyze  response_context_enrichment                ok    
0.04         /api/alert/analyze  referral_debug_build                       ok    
0.013        /api/alert/analyze  shadow_compare_schedule                    ok    
79.769       /api/alert/analyze  cluster_history_fetch                      ok    
0.03         /api/alert/analyze  narrative_context_build                    ok    
0.037        /api/alert/analyze  narrative_generation                       ok    
2.07         /api/alert/analyze  response_serialization                     ok    
1859.232     /api/alert/analyze  analyze_request_total                      ok    
0.007        /api/alert/outcome  request_parse                              ok    
0.008        /api/alert/outcome  duplicate_feedback_guard                   ok    
88.029       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.867        /api/alert/outcome  outcome_audit_write                        ok    
127.192      /api/alert/outcome  learning_state_update                      ok    
423.72       /api/alert/outcome  l5_conservation_write                      ok    
426.148      /api/alert/outcome  conservation_monitor                       ok    
0.138        /api/alert/outcome  profile_scorer_update                      ok    
0.118        /api/alert/outcome  l5_dk_weight_write                         ok    
482.528      /api/alert/outcome  l5_centroid_write                          ok    
0.012        /api/alert/outcome  l5_dk_weight_write                         ok    
0.022        /api/alert/outcome  snapshot_evolution_logging                 ok    
83.413       /api/alert/outcome  snapshot_evolution_logging                 ok    
0.022        /api/alert/outcome  response_serialization                     ok    
1641.995     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1EDGE-0025
- event_count: 52
- total_observed_ms: 7973.042
- authoritative_total_ms: 1853.963
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.034        /api/alert/analyze  scorer_readiness                           ok    
0.008        /api/alert/analyze  request_parse                              ok    
76.389       /api/alert/analyze  alert_lookup                               ok    
89.575       /api/alert/analyze  security_context_lookup                    ok    
0.177        /api/alert/analyze  category_resolution                        ok    
346.402      /api/alert/analyze  factor_vector_construction                 ok    
0.576        /api/alert/analyze  scorer_decision                            ok    
0.067        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.013        /api/alert/analyze  routing_threshold_lookup                   ok    
0.02         /api/alert/analyze  rl_exploration_proposal                    ok    
0.021        /api/alert/analyze  routing_zone_resolution                    ok    
169.452      /api/alert/analyze  referral_history_counts                    ok    
0.059        /api/alert/analyze  referral_gate_evaluation                   ok    
77.476       /api/alert/analyze  reasoning_generation                       ok    
89.538       /api/alert/analyze  decision_node_and_edge_write               ok    
88.503       /api/alert/analyze  audit_write                                ok    
0.284        /api/alert/analyze  metadata_logging_snapshot_write            ok    
97.141       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
70.416       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
94.227       /api/alert/analyze  campaign_query_update_campaign             ok    
84.77        /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
85.245       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
83.018       /api/alert/analyze  campaign_query_member_edges_batch_create   ok    
527.943      /api/alert/analyze  campaign_correlation_summary               ok    
606.271      /api/alert/analyze  campaign_correlation                       ok    
0.021        /api/alert/analyze  decision_event_emit                        ok    
82.784       /api/alert/analyze  composite_gate_evaluation                  ok    
0.053        /api/alert/analyze  provenance_build                           ok    
85.035       /api/alert/analyze  graph_visualization_fetch                  ok    
0.061        /api/alert/analyze  response_context_enrichment                ok    
0.102        /api/alert/analyze  referral_debug_build                       ok    
0.028        /api/alert/analyze  shadow_compare_schedule                    ok    
79.053       /api/alert/analyze  cluster_history_fetch                      ok    
0.027        /api/alert/analyze  narrative_context_build                    ok    
0.067        /api/alert/analyze  narrative_generation                       ok    
4.069        /api/alert/analyze  response_serialization                     ok    
1853.963     /api/alert/analyze  analyze_request_total                      ok    
0.016        /api/alert/outcome  request_parse                              ok    
0.01         /api/alert/outcome  duplicate_feedback_guard                   ok    
85.401       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.983        /api/alert/outcome  outcome_audit_write                        ok    
140.217      /api/alert/outcome  learning_state_update                      ok    
450.346      /api/alert/outcome  l5_conservation_write                      ok    
453.314      /api/alert/outcome  conservation_monitor                       ok    
0.139        /api/alert/outcome  profile_scorer_update                      ok    
0.1          /api/alert/outcome  l5_dk_weight_write                         ok    
439.346      /api/alert/outcome  l5_centroid_write                          ok    
0.02         /api/alert/outcome  l5_dk_weight_write                         ok    
0.039        /api/alert/outcome  snapshot_evolution_logging                 ok    
84.974       /api/alert/outcome  snapshot_evolution_logging                 ok    
0.019        /api/alert/outcome  response_serialization                     ok    
1625.23      /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1EDGE-0007
- event_count: 52
- total_observed_ms: 7760.653
- authoritative_total_ms: 1841.999
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.032        /api/alert/analyze  scorer_readiness                           ok    
0.016        /api/alert/analyze  request_parse                              ok    
86.056       /api/alert/analyze  alert_lookup                               ok    
96.982       /api/alert/analyze  security_context_lookup                    ok    
0.155        /api/alert/analyze  category_resolution                        ok    
321.404      /api/alert/analyze  factor_vector_construction                 ok    
0.471        /api/alert/analyze  scorer_decision                            ok    
0.039        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.022        /api/alert/analyze  routing_threshold_lookup                   ok    
0.032        /api/alert/analyze  rl_exploration_proposal                    ok    
0.036        /api/alert/analyze  routing_zone_resolution                    ok    
141.789      /api/alert/analyze  referral_history_counts                    ok    
0.045        /api/alert/analyze  referral_gate_evaluation                   ok    
101.797      /api/alert/analyze  reasoning_generation                       ok    
76.545       /api/alert/analyze  decision_node_and_edge_write               ok    
72.443       /api/alert/analyze  audit_write                                ok    
1.098        /api/alert/analyze  metadata_logging_snapshot_write            ok    
66.558       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
86.281       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
72.778       /api/alert/analyze  campaign_query_create_campaign             ok    
69.371       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
77.178       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
160.711      /api/alert/analyze  campaign_query_member_edges_batch_create   ok    
544.844      /api/alert/analyze  campaign_correlation_summary               ok    
637.131      /api/alert/analyze  campaign_correlation                       ok    
0.075        /api/alert/analyze  decision_event_emit                        ok    
91.088       /api/alert/analyze  composite_gate_evaluation                  ok    
0.151        /api/alert/analyze  provenance_build                           ok    
83.267       /api/alert/analyze  graph_visualization_fetch                  ok    
0.057        /api/alert/analyze  response_context_enrichment                ok    
0.033        /api/alert/analyze  referral_debug_build                       ok    
0.02         /api/alert/analyze  shadow_compare_schedule                    ok    
63.128       /api/alert/analyze  cluster_history_fetch                      ok    
0.032        /api/alert/analyze  narrative_context_build                    ok    
0.052        /api/alert/analyze  narrative_generation                       ok    
2.254        /api/alert/analyze  response_serialization                     ok    
1841.999     /api/alert/analyze  analyze_request_total                      ok    
0.018        /api/alert/outcome  request_parse                              ok    
0.008        /api/alert/outcome  duplicate_feedback_guard                   ok    
78.997       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.368        /api/alert/outcome  outcome_audit_write                        ok    
125.624      /api/alert/outcome  learning_state_update                      ok    
413.397      /api/alert/outcome  l5_conservation_write                      ok    
416.234      /api/alert/outcome  conservation_monitor                       ok    
0.173        /api/alert/outcome  profile_scorer_update                      ok    
0.304        /api/alert/outcome  l5_dk_weight_write                         ok    
384.668      /api/alert/outcome  l5_centroid_write                          ok    
0.016        /api/alert/outcome  l5_dk_weight_write                         ok    
0.015        /api/alert/outcome  snapshot_evolution_logging                 ok    
91.303       /api/alert/outcome  snapshot_evolution_logging                 ok    
0.03         /api/alert/outcome  response_serialization                     ok    
1553.528     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1EDGE-0017
- event_count: 52
- total_observed_ms: 7756.623
- authoritative_total_ms: 1840.861
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.015        /api/alert/analyze  scorer_readiness                           ok    
0.012        /api/alert/analyze  request_parse                              ok    
72.643       /api/alert/analyze  alert_lookup                               ok    
94.47        /api/alert/analyze  security_context_lookup                    ok    
0.117        /api/alert/analyze  category_resolution                        ok    
341.86       /api/alert/analyze  factor_vector_construction                 ok    
0.163        /api/alert/analyze  scorer_decision                            ok    
0.013        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.013        /api/alert/analyze  routing_threshold_lookup                   ok    
0.044        /api/alert/analyze  rl_exploration_proposal                    ok    
0.019        /api/alert/analyze  routing_zone_resolution                    ok    
170.372      /api/alert/analyze  referral_history_counts                    ok    
0.084        /api/alert/analyze  referral_gate_evaluation                   ok    
76.618       /api/alert/analyze  reasoning_generation                       ok    
95.137       /api/alert/analyze  decision_node_and_edge_write               ok    
95.086       /api/alert/analyze  audit_write                                ok    
1.069        /api/alert/analyze  metadata_logging_snapshot_write            ok    
99.452       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
73.204       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
73.835       /api/alert/analyze  campaign_query_update_campaign             ok    
78.983       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
82.292       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
86.991       /api/alert/analyze  campaign_query_member_edges_batch_create   ok    
504.405      /api/alert/analyze  campaign_correlation_summary               ok    
594.412      /api/alert/analyze  campaign_correlation                       ok    
0.028        /api/alert/analyze  decision_event_emit                        ok    
70.672       /api/alert/analyze  composite_gate_evaluation                  ok    
0.059        /api/alert/analyze  provenance_build                           ok    
94.647       /api/alert/analyze  graph_visualization_fetch                  ok    
0.023        /api/alert/analyze  response_context_enrichment                ok    
0.029        /api/alert/analyze  referral_debug_build                       ok    
0.012        /api/alert/analyze  shadow_compare_schedule                    ok    
86.172       /api/alert/analyze  cluster_history_fetch                      ok    
0.029        /api/alert/analyze  narrative_context_build                    ok    
0.039        /api/alert/analyze  narrative_generation                       ok    
2.297        /api/alert/analyze  response_serialization                     ok    
1840.861     /api/alert/analyze  analyze_request_total                      ok    
0.007        /api/alert/outcome  request_parse                              ok    
0.01         /api/alert/outcome  duplicate_feedback_guard                   ok    
91.544       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.25         /api/alert/outcome  outcome_audit_write                        ok    
77.86        /api/alert/outcome  learning_state_update                      ok    
397.628      /api/alert/outcome  l5_conservation_write                      ok    
399.229      /api/alert/outcome  conservation_monitor                       ok    
0.15         /api/alert/outcome  profile_scorer_update                      ok    
0.232        /api/alert/outcome  l5_dk_weight_write                         ok    
472.742      /api/alert/outcome  l5_centroid_write                          ok    
0.012        /api/alert/outcome  l5_dk_weight_write                         ok    
0.024        /api/alert/outcome  snapshot_evolution_logging                 ok    
94.57        /api/alert/outcome  snapshot_evolution_logging                 ok    
0.026        /api/alert/outcome  response_serialization                     ok    
1586.162     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1EDGE-0011
- event_count: 52
- total_observed_ms: 7754.054
- authoritative_total_ms: 1836.625
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.024        /api/alert/analyze  scorer_readiness                           ok    
0.014        /api/alert/analyze  request_parse                              ok    
77.144       /api/alert/analyze  alert_lookup                               ok    
99.193       /api/alert/analyze  security_context_lookup                    ok    
0.113        /api/alert/analyze  category_resolution                        ok    
334.547      /api/alert/analyze  factor_vector_construction                 ok    
0.34         /api/alert/analyze  scorer_decision                            ok    
0.028        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.007        /api/alert/analyze  routing_threshold_lookup                   ok    
0.011        /api/alert/analyze  rl_exploration_proposal                    ok    
0.011        /api/alert/analyze  routing_zone_resolution                    ok    
185.901      /api/alert/analyze  referral_history_counts                    ok    
0.062        /api/alert/analyze  referral_gate_evaluation                   ok    
81.821       /api/alert/analyze  reasoning_generation                       ok    
86.745       /api/alert/analyze  decision_node_and_edge_write               ok    
84.801       /api/alert/analyze  audit_write                                ok    
0.304        /api/alert/analyze  metadata_logging_snapshot_write            ok    
100.509      /api/alert/analyze  campaign_query_fetch_recent_events         ok    
80.64        /api/alert/analyze  campaign_query_check_campaign_exists       ok    
98.59        /api/alert/analyze  campaign_query_create_campaign             ok    
77.504       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
63.544       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
77.773       /api/alert/analyze  campaign_query_member_edges_batch_create   ok    
507.024      /api/alert/analyze  campaign_correlation_summary               ok    
578.663      /api/alert/analyze  campaign_correlation                       ok    
0.022        /api/alert/analyze  decision_event_emit                        ok    
72.01        /api/alert/analyze  composite_gate_evaluation                  ok    
0.075        /api/alert/analyze  provenance_build                           ok    
98.4         /api/alert/analyze  graph_visualization_fetch                  ok    
0.046        /api/alert/analyze  response_context_enrichment                ok    
0.05         /api/alert/analyze  referral_debug_build                       ok    
0.026        /api/alert/analyze  shadow_compare_schedule                    ok    
76.257       /api/alert/analyze  cluster_history_fetch                      ok    
0.06         /api/alert/analyze  narrative_context_build                    ok    
0.082        /api/alert/analyze  narrative_generation                       ok    
5.454        /api/alert/analyze  response_serialization                     ok    
1836.625     /api/alert/analyze  analyze_request_total                      ok    
0.018        /api/alert/outcome  request_parse                              ok    
0.027        /api/alert/outcome  duplicate_feedback_guard                   ok    
89.896       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.246        /api/alert/outcome  outcome_audit_write                        ok    
70.224       /api/alert/outcome  learning_state_update                      ok    
419.277      /api/alert/outcome  l5_conservation_write                      ok    
422.495      /api/alert/outcome  conservation_monitor                       ok    
0.317        /api/alert/outcome  profile_scorer_update                      ok    
0.153        /api/alert/outcome  l5_dk_weight_write                         ok    
453.771      /api/alert/outcome  l5_centroid_write                          ok    
0.025        /api/alert/outcome  l5_dk_weight_write                         ok    
0.016        /api/alert/outcome  snapshot_evolution_logging                 ok    
85.129       /api/alert/outcome  snapshot_evolution_logging                 ok    
0.026        /api/alert/outcome  response_serialization                     ok    
1588.014     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1EDGE-0023
- event_count: 52
- total_observed_ms: 8079.112
- authoritative_total_ms: 1834.228
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.034        /api/alert/analyze  scorer_readiness                           ok    
0.017        /api/alert/analyze  request_parse                              ok    
80.552       /api/alert/analyze  alert_lookup                               ok    
87.138       /api/alert/analyze  security_context_lookup                    ok    
0.105        /api/alert/analyze  category_resolution                        ok    
325.84       /api/alert/analyze  factor_vector_construction                 ok    
0.163        /api/alert/analyze  scorer_decision                            ok    
0.014        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.007        /api/alert/analyze  routing_threshold_lookup                   ok    
0.011        /api/alert/analyze  rl_exploration_proposal                    ok    
0.011        /api/alert/analyze  routing_zone_resolution                    ok    
157.166      /api/alert/analyze  referral_history_counts                    ok    
0.067        /api/alert/analyze  referral_gate_evaluation                   ok    
85.808       /api/alert/analyze  reasoning_generation                       ok    
103.206      /api/alert/analyze  decision_node_and_edge_write               ok    
86.388       /api/alert/analyze  audit_write                                ok    
0.817        /api/alert/analyze  metadata_logging_snapshot_write            ok    
87.664       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
83.592       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
100.579      /api/alert/analyze  campaign_query_update_campaign             ok    
78.229       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
78.232       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
91.113       /api/alert/analyze  campaign_query_member_edges_batch_create   ok    
531.769      /api/alert/analyze  campaign_correlation_summary               ok    
619.68       /api/alert/analyze  campaign_correlation                       ok    
0.02         /api/alert/analyze  decision_event_emit                        ok    
69.891       /api/alert/analyze  composite_gate_evaluation                  ok    
0.052        /api/alert/analyze  provenance_build                           ok    
84.528       /api/alert/analyze  graph_visualization_fetch                  ok    
0.046        /api/alert/analyze  response_context_enrichment                ok    
0.05         /api/alert/analyze  referral_debug_build                       ok    
0.027        /api/alert/analyze  shadow_compare_schedule                    ok    
76.602       /api/alert/analyze  cluster_history_fetch                      ok    
0.031        /api/alert/analyze  narrative_context_build                    ok    
0.05         /api/alert/analyze  narrative_generation                       ok    
3.345        /api/alert/analyze  response_serialization                     ok    
1834.228     /api/alert/analyze  analyze_request_total                      ok    
0.007        /api/alert/outcome  request_parse                              ok    
0.008        /api/alert/outcome  duplicate_feedback_guard                   ok    
73.238       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.194        /api/alert/outcome  outcome_audit_write                        ok    
214.339      /api/alert/outcome  learning_state_update                      ok    
443.588      /api/alert/outcome  l5_conservation_write                      ok    
444.963      /api/alert/outcome  conservation_monitor                       ok    
0.135        /api/alert/outcome  profile_scorer_update                      ok    
0.105        /api/alert/outcome  l5_dk_weight_write                         ok    
438.518      /api/alert/outcome  l5_centroid_write                          ok    
0.02         /api/alert/outcome  l5_dk_weight_write                         ok    
0.033        /api/alert/outcome  snapshot_evolution_logging                 ok    
89.413       /api/alert/outcome  snapshot_evolution_logging                 ok    
0.068        /api/alert/outcome  response_serialization                     ok    
1707.411     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1EDGE-0020
- event_count: 52
- total_observed_ms: 8002.724
- authoritative_total_ms: 1833.327
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.013        /api/alert/analyze  scorer_readiness                           ok    
0.009        /api/alert/analyze  request_parse                              ok    
88.759       /api/alert/analyze  alert_lookup                               ok    
83.536       /api/alert/analyze  security_context_lookup                    ok    
0.242        /api/alert/analyze  category_resolution                        ok    
293.991      /api/alert/analyze  factor_vector_construction                 ok    
0.252        /api/alert/analyze  scorer_decision                            ok    
0.029        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.015        /api/alert/analyze  routing_threshold_lookup                   ok    
0.016        /api/alert/analyze  rl_exploration_proposal                    ok    
0.031        /api/alert/analyze  routing_zone_resolution                    ok    
147.417      /api/alert/analyze  referral_history_counts                    ok    
0.035        /api/alert/analyze  referral_gate_evaluation                   ok    
90.326       /api/alert/analyze  reasoning_generation                       ok    
89.948       /api/alert/analyze  decision_node_and_edge_write               ok    
88.37        /api/alert/analyze  audit_write                                ok    
3.072        /api/alert/analyze  metadata_logging_snapshot_write            ok    
76.239       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
94.92        /api/alert/analyze  campaign_query_check_campaign_exists       ok    
101.749      /api/alert/analyze  campaign_query_update_campaign             ok    
81.711       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
93.887       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
71.576       /api/alert/analyze  campaign_query_member_edges_batch_create   ok    
529.881      /api/alert/analyze  campaign_correlation_summary               ok    
614.308      /api/alert/analyze  campaign_correlation                       ok    
0.021        /api/alert/analyze  decision_event_emit                        ok    
92.073       /api/alert/analyze  composite_gate_evaluation                  ok    
0.094        /api/alert/analyze  provenance_build                           ok    
93.415       /api/alert/analyze  graph_visualization_fetch                  ok    
0.02         /api/alert/analyze  response_context_enrichment                ok    
0.022        /api/alert/analyze  referral_debug_build                       ok    
0.01         /api/alert/analyze  shadow_compare_schedule                    ok    
84.286       /api/alert/analyze  cluster_history_fetch                      ok    
0.045        /api/alert/analyze  narrative_context_build                    ok    
0.074        /api/alert/analyze  narrative_generation                       ok    
5.229        /api/alert/analyze  response_serialization                     ok    
1833.327     /api/alert/analyze  analyze_request_total                      ok    
0.019        /api/alert/outcome  request_parse                              ok    
0.031        /api/alert/outcome  duplicate_feedback_guard                   ok    
89.172       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.493        /api/alert/outcome  outcome_audit_write                        ok    
110.332      /api/alert/outcome  learning_state_update                      ok    
440.494      /api/alert/outcome  l5_conservation_write                      ok    
441.816      /api/alert/outcome  conservation_monitor                       ok    
0.13         /api/alert/outcome  profile_scorer_update                      ok    
0.39         /api/alert/outcome  l5_dk_weight_write                         ok    
457.466      /api/alert/outcome  l5_centroid_write                          ok    
0.025        /api/alert/outcome  l5_dk_weight_write                         ok    
0.019        /api/alert/outcome  snapshot_evolution_logging                 ok    
103.934      /api/alert/outcome  snapshot_evolution_logging                 ok    
0.024        /api/alert/outcome  response_serialization                     ok    
1699.431     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1EDGE-0015
- event_count: 52
- total_observed_ms: 8165.12
- authoritative_total_ms: 1822.922
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.024        /api/alert/analyze  scorer_readiness                           ok    
0.01         /api/alert/analyze  request_parse                              ok    
78.165       /api/alert/analyze  alert_lookup                               ok    
75.464       /api/alert/analyze  security_context_lookup                    ok    
0.155        /api/alert/analyze  category_resolution                        ok    
326.225      /api/alert/analyze  factor_vector_construction                 ok    
0.243        /api/alert/analyze  scorer_decision                            ok    
0.026        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.211        /api/alert/analyze  routing_threshold_lookup                   ok    
0.015        /api/alert/analyze  rl_exploration_proposal                    ok    
0.012        /api/alert/analyze  routing_zone_resolution                    ok    
154.427      /api/alert/analyze  referral_history_counts                    ok    
0.066        /api/alert/analyze  referral_gate_evaluation                   ok    
85.894       /api/alert/analyze  reasoning_generation                       ok    
88.795       /api/alert/analyze  decision_node_and_edge_write               ok    
107.537      /api/alert/analyze  audit_write                                ok    
0.399        /api/alert/analyze  metadata_logging_snapshot_write            ok    
84.891       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
80.445       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
79.927       /api/alert/analyze  campaign_query_update_campaign             ok    
99.192       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
85.863       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
75.21        /api/alert/analyze  campaign_query_member_edges_batch_create   ok    
521.276      /api/alert/analyze  campaign_correlation_summary               ok    
615.378      /api/alert/analyze  campaign_correlation                       ok    
0.02         /api/alert/analyze  decision_event_emit                        ok    
74.549       /api/alert/analyze  composite_gate_evaluation                  ok    
0.051        /api/alert/analyze  provenance_build                           ok    
82.575       /api/alert/analyze  graph_visualization_fetch                  ok    
0.031        /api/alert/analyze  response_context_enrichment                ok    
0.046        /api/alert/analyze  referral_debug_build                       ok    
0.026        /api/alert/analyze  shadow_compare_schedule                    ok    
79.683       /api/alert/analyze  cluster_history_fetch                      ok    
0.029        /api/alert/analyze  narrative_context_build                    ok    
0.048        /api/alert/analyze  narrative_generation                       ok    
2.867        /api/alert/analyze  response_serialization                     ok    
1822.922     /api/alert/analyze  analyze_request_total                      ok    
0.009        /api/alert/outcome  request_parse                              ok    
0.007        /api/alert/outcome  duplicate_feedback_guard                   ok    
77.547       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
18.701       /api/alert/outcome  outcome_audit_write                        ok    
185.124      /api/alert/outcome  learning_state_update                      ok    
445.862      /api/alert/outcome  l5_conservation_write                      ok    
449.537      /api/alert/outcome  conservation_monitor                       ok    
0.189        /api/alert/outcome  profile_scorer_update                      ok    
0.162        /api/alert/outcome  l5_dk_weight_write                         ok    
504.219      /api/alert/outcome  l5_centroid_write                          ok    
0.025        /api/alert/outcome  l5_dk_weight_write                         ok    
0.034        /api/alert/outcome  snapshot_evolution_logging                 ok    
86.892       /api/alert/outcome  snapshot_evolution_logging                 ok    
0.045        /api/alert/outcome  response_serialization                     ok    
1774.07      /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1EDGE-0008
- event_count: 52
- total_observed_ms: 7723.992
- authoritative_total_ms: 1799.479
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.03         /api/alert/analyze  scorer_readiness                           ok    
0.043        /api/alert/analyze  request_parse                              ok    
80.577       /api/alert/analyze  alert_lookup                               ok    
76.719       /api/alert/analyze  security_context_lookup                    ok    
0.22         /api/alert/analyze  category_resolution                        ok    
321.687      /api/alert/analyze  factor_vector_construction                 ok    
0.197        /api/alert/analyze  scorer_decision                            ok    
0.013        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.014        /api/alert/analyze  routing_threshold_lookup                   ok    
0.019        /api/alert/analyze  rl_exploration_proposal                    ok    
0.012        /api/alert/analyze  routing_zone_resolution                    ok    
156.957      /api/alert/analyze  referral_history_counts                    ok    
0.049        /api/alert/analyze  referral_gate_evaluation                   ok    
68.547       /api/alert/analyze  reasoning_generation                       ok    
99.419       /api/alert/analyze  decision_node_and_edge_write               ok    
86.559       /api/alert/analyze  audit_write                                ok    
0.601        /api/alert/analyze  metadata_logging_snapshot_write            ok    
74.725       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
76.832       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
88.92        /api/alert/analyze  campaign_query_create_campaign             ok    
83.831       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
73.732       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
76.55        /api/alert/analyze  campaign_query_member_edges_batch_create   ok    
488.423      /api/alert/analyze  campaign_correlation_summary               ok    
569.795      /api/alert/analyze  campaign_correlation                       ok    
0.045        /api/alert/analyze  decision_event_emit                        ok    
86.306       /api/alert/analyze  composite_gate_evaluation                  ok    
0.108        /api/alert/analyze  provenance_build                           ok    
105.457      /api/alert/analyze  graph_visualization_fetch                  ok    
0.03         /api/alert/analyze  response_context_enrichment                ok    
0.042        /api/alert/analyze  referral_debug_build                       ok    
0.022        /api/alert/analyze  shadow_compare_schedule                    ok    
87.312       /api/alert/analyze  cluster_history_fetch                      ok    
0.055        /api/alert/analyze  narrative_context_build                    ok    
0.098        /api/alert/analyze  narrative_generation                       ok    
5.095        /api/alert/analyze  response_serialization                     ok    
1799.479     /api/alert/analyze  analyze_request_total                      ok    
0.018        /api/alert/outcome  request_parse                              ok    
0.027        /api/alert/outcome  duplicate_feedback_guard                   ok    
96.109       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.377        /api/alert/outcome  outcome_audit_write                        ok    
109.657      /api/alert/outcome  learning_state_update                      ok    
457.896      /api/alert/outcome  l5_conservation_write                      ok    
461.557      /api/alert/outcome  conservation_monitor                       ok    
0.353        /api/alert/outcome  profile_scorer_update                      ok    
0.128        /api/alert/outcome  l5_dk_weight_write                         ok    
424.844      /api/alert/outcome  l5_centroid_write                          ok    
0.017        /api/alert/outcome  l5_dk_weight_write                         ok    
0.017        /api/alert/outcome  snapshot_evolution_logging                 ok    
74.74        /api/alert/outcome  snapshot_evolution_logging                 ok    
0.024        /api/alert/outcome  response_serialization                     ok    
1589.708     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1EDGE-0013
- event_count: 52
- total_observed_ms: 7815.166
- authoritative_total_ms: 1791.317
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.031        /api/alert/analyze  scorer_readiness                           ok    
0.016        /api/alert/analyze  request_parse                              ok    
99.399       /api/alert/analyze  alert_lookup                               ok    
81.066       /api/alert/analyze  security_context_lookup                    ok    
0.116        /api/alert/analyze  category_resolution                        ok    
327.846      /api/alert/analyze  factor_vector_construction                 ok    
0.195        /api/alert/analyze  scorer_decision                            ok    
0.031        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.007        /api/alert/analyze  routing_threshold_lookup                   ok    
0.012        /api/alert/analyze  rl_exploration_proposal                    ok    
0.012        /api/alert/analyze  routing_zone_resolution                    ok    
146.015      /api/alert/analyze  referral_history_counts                    ok    
0.037        /api/alert/analyze  referral_gate_evaluation                   ok    
72.206       /api/alert/analyze  reasoning_generation                       ok    
90.991       /api/alert/analyze  decision_node_and_edge_write               ok    
97.899       /api/alert/analyze  audit_write                                ok    
0.287        /api/alert/analyze  metadata_logging_snapshot_write            ok    
88.576       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
79.495       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
82.391       /api/alert/analyze  campaign_query_update_campaign             ok    
76.526       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
83.195       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
74.197       /api/alert/analyze  campaign_query_member_edges_batch_create   ok    
495.061      /api/alert/analyze  campaign_correlation_summary               ok    
577.874      /api/alert/analyze  campaign_correlation                       ok    
0.02         /api/alert/analyze  decision_event_emit                        ok    
85.87        /api/alert/analyze  composite_gate_evaluation                  ok    
0.169        /api/alert/analyze  provenance_build                           ok    
82.558       /api/alert/analyze  graph_visualization_fetch                  ok    
0.04         /api/alert/analyze  response_context_enrichment                ok    
0.048        /api/alert/analyze  referral_debug_build                       ok    
0.017        /api/alert/analyze  shadow_compare_schedule                    ok    
75.693       /api/alert/analyze  cluster_history_fetch                      ok    
0.036        /api/alert/analyze  narrative_context_build                    ok    
0.048        /api/alert/analyze  narrative_generation                       ok    
2.606        /api/alert/analyze  response_serialization                     ok    
1791.317     /api/alert/analyze  analyze_request_total                      ok    
0.014        /api/alert/outcome  request_parse                              ok    
0.008        /api/alert/outcome  duplicate_feedback_guard                   ok    
90.788       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.314        /api/alert/outcome  outcome_audit_write                        ok    
116.801      /api/alert/outcome  learning_state_update                      ok    
437.076      /api/alert/outcome  l5_conservation_write                      ok    
439.914      /api/alert/outcome  conservation_monitor                       ok    
0.132        /api/alert/outcome  profile_scorer_update                      ok    
0.1          /api/alert/outcome  l5_dk_weight_write                         ok    
468.944      /api/alert/outcome  l5_centroid_write                          ok    
0.026        /api/alert/outcome  l5_dk_weight_write                         ok    
0.051        /api/alert/outcome  snapshot_evolution_logging                 ok    
90.494       /api/alert/outcome  snapshot_evolution_logging                 ok    
0.024        /api/alert/outcome  response_serialization                     ok    
1658.577     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1EDGE-0014
- event_count: 52
- total_observed_ms: 7657.861
- authoritative_total_ms: 1780.921
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.031        /api/alert/analyze  scorer_readiness                           ok    
0.019        /api/alert/analyze  request_parse                              ok    
84.702       /api/alert/analyze  alert_lookup                               ok    
92.144       /api/alert/analyze  security_context_lookup                    ok    
0.208        /api/alert/analyze  category_resolution                        ok    
344.6        /api/alert/analyze  factor_vector_construction                 ok    
0.289        /api/alert/analyze  scorer_decision                            ok    
0.015        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.01         /api/alert/analyze  routing_threshold_lookup                   ok    
0.012        /api/alert/analyze  rl_exploration_proposal                    ok    
0.015        /api/alert/analyze  routing_zone_resolution                    ok    
152.353      /api/alert/analyze  referral_history_counts                    ok    
0.046        /api/alert/analyze  referral_gate_evaluation                   ok    
69.928       /api/alert/analyze  reasoning_generation                       ok    
91.094       /api/alert/analyze  decision_node_and_edge_write               ok    
83.176       /api/alert/analyze  audit_write                                ok    
0.218        /api/alert/analyze  metadata_logging_snapshot_write            ok    
73.196       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
64.622       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
81.331       /api/alert/analyze  campaign_query_update_campaign             ok    
72.565       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
68.613       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
104.55       /api/alert/analyze  campaign_query_member_edges_batch_create   ok    
475.71       /api/alert/analyze  campaign_correlation_summary               ok    
562.296      /api/alert/analyze  campaign_correlation                       ok    
0.038        /api/alert/analyze  decision_event_emit                        ok    
70.09        /api/alert/analyze  composite_gate_evaluation                  ok    
0.052        /api/alert/analyze  provenance_build                           ok    
95.824       /api/alert/analyze  graph_visualization_fetch                  ok    
0.024        /api/alert/analyze  response_context_enrichment                ok    
0.054        /api/alert/analyze  referral_debug_build                       ok    
0.014        /api/alert/analyze  shadow_compare_schedule                    ok    
76.347       /api/alert/analyze  cluster_history_fetch                      ok    
0.045        /api/alert/analyze  narrative_context_build                    ok    
0.043        /api/alert/analyze  narrative_generation                       ok    
3.073        /api/alert/analyze  response_serialization                     ok    
1780.921     /api/alert/analyze  analyze_request_total                      ok    
0.012        /api/alert/outcome  request_parse                              ok    
0.008        /api/alert/outcome  duplicate_feedback_guard                   ok    
82.722       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.205        /api/alert/outcome  outcome_audit_write                        ok    
77.639       /api/alert/outcome  learning_state_update                      ok    
431.857      /api/alert/outcome  l5_conservation_write                      ok    
437.934      /api/alert/outcome  conservation_monitor                       ok    
0.217        /api/alert/outcome  profile_scorer_update                      ok    
0.214        /api/alert/outcome  l5_dk_weight_write                         ok    
465.654      /api/alert/outcome  l5_centroid_write                          ok    
0.022        /api/alert/outcome  l5_dk_weight_write                         ok    
0.033        /api/alert/outcome  snapshot_evolution_logging                 ok    
83.23        /api/alert/outcome  snapshot_evolution_logging                 ok    
0.032        /api/alert/outcome  response_serialization                     ok    
1629.814     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1EDGE-0001
- event_count: 47
- total_observed_ms: 6483.506
- authoritative_total_ms: 1724.468
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.044        /api/alert/analyze  scorer_readiness                    ok    
0.017        /api/alert/analyze  request_parse                       ok    
80.639       /api/alert/analyze  alert_lookup                        ok    
97.556       /api/alert/analyze  security_context_lookup             ok    
9.427        /api/alert/analyze  category_resolution                 ok    
313.459      /api/alert/analyze  factor_vector_construction          ok    
6.957        /api/alert/analyze  scorer_decision                     ok    
10.964       /api/alert/analyze  post_scorer_confidence_gate         ok    
0.007        /api/alert/analyze  routing_threshold_lookup            ok    
0.019        /api/alert/analyze  rl_exploration_proposal             ok    
0.018        /api/alert/analyze  routing_zone_resolution             ok    
162.707      /api/alert/analyze  referral_history_counts             ok    
0.125        /api/alert/analyze  referral_gate_evaluation            ok    
485.663      /api/alert/analyze  reasoning_generation                ok    
102.488      /api/alert/analyze  decision_node_and_edge_write        ok    
73.306       /api/alert/analyze  audit_write                         ok    
0.182        /api/alert/analyze  metadata_logging_snapshot_write     ok    
71.042       /api/alert/analyze  campaign_query_fetch_recent_events  ok    
72.386       /api/alert/analyze  campaign_correlation_summary        ok    
73.718       /api/alert/analyze  campaign_correlation                ok    
0.038        /api/alert/analyze  decision_event_emit                 ok    
70.587       /api/alert/analyze  composite_gate_evaluation           ok    
0.07         /api/alert/analyze  provenance_build                    ok    
68.802       /api/alert/analyze  graph_visualization_fetch           ok    
0.03         /api/alert/analyze  response_context_enrichment         ok    
0.036        /api/alert/analyze  referral_debug_build                ok    
0.02         /api/alert/analyze  shadow_compare_schedule             ok    
76.438       /api/alert/analyze  cluster_history_fetch               ok    
0.038        /api/alert/analyze  narrative_context_build             ok    
0.058        /api/alert/analyze  narrative_generation                ok    
3.125        /api/alert/analyze  response_serialization              ok    
1724.468     /api/alert/analyze  analyze_request_total               ok    
0.02         /api/alert/outcome  request_parse                       ok    
0.009        /api/alert/outcome  duplicate_feedback_guard            ok    
72.925       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.333        /api/alert/outcome  outcome_audit_write                 ok    
81.151       /api/alert/outcome  learning_state_update               ok    
412.913      /api/alert/outcome  l5_conservation_write               ok    
414.351      /api/alert/outcome  conservation_monitor                ok    
0.166        /api/alert/outcome  profile_scorer_update               ok    
0.323        /api/alert/outcome  l5_dk_weight_write                  ok    
404.18       /api/alert/outcome  l5_centroid_write                   ok    
0.021        /api/alert/outcome  l5_dk_weight_write                  ok    
5.89         /api/alert/outcome  snapshot_evolution_logging          ok    
109.043      /api/alert/outcome  snapshot_evolution_logging          ok    
0.023        /api/alert/outcome  response_serialization              ok    
1477.724     /api/alert/outcome  outcome_request_total               ok    
```

### CAMPAIGNP1EDGE-0006
- event_count: 47
- total_observed_ms: 5692.397
- authoritative_total_ms: 1535.764
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.015        /api/alert/analyze  scorer_readiness                    ok    
0.009        /api/alert/analyze  request_parse                       ok    
64.172       /api/alert/analyze  alert_lookup                        ok    
87.929       /api/alert/analyze  security_context_lookup             ok    
0.141        /api/alert/analyze  category_resolution                 ok    
287.53       /api/alert/analyze  factor_vector_construction          ok    
0.233        /api/alert/analyze  scorer_decision                     ok    
0.018        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.015        /api/alert/analyze  routing_threshold_lookup            ok    
0.013        /api/alert/analyze  rl_exploration_proposal             ok    
0.013        /api/alert/analyze  routing_zone_resolution             ok    
175.222      /api/alert/analyze  referral_history_counts             ok    
0.053        /api/alert/analyze  referral_gate_evaluation            ok    
84.804       /api/alert/analyze  reasoning_generation                ok    
97.82        /api/alert/analyze  decision_node_and_edge_write        ok    
98.013       /api/alert/analyze  audit_write                         ok    
0.319        /api/alert/analyze  metadata_logging_snapshot_write     ok    
80.849       /api/alert/analyze  campaign_query_fetch_recent_events  ok    
82.673       /api/alert/analyze  campaign_correlation_summary        ok    
84.182       /api/alert/analyze  campaign_correlation                ok    
0.037        /api/alert/analyze  decision_event_emit                 ok    
73.536       /api/alert/analyze  composite_gate_evaluation           ok    
0.085        /api/alert/analyze  provenance_build                    ok    
86.926       /api/alert/analyze  graph_visualization_fetch           ok    
0.028        /api/alert/analyze  response_context_enrichment         ok    
0.033        /api/alert/analyze  referral_debug_build                ok    
0.022        /api/alert/analyze  shadow_compare_schedule             ok    
70.579       /api/alert/analyze  cluster_history_fetch               ok    
0.038        /api/alert/analyze  narrative_context_build             ok    
0.056        /api/alert/analyze  narrative_generation                ok    
2.973        /api/alert/analyze  response_serialization              ok    
1260.365     /api/alert/analyze  analyze_request_total               ok    
0.011        /api/alert/outcome  request_parse                       ok    
0.016        /api/alert/outcome  duplicate_feedback_guard            ok    
77.985       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.24         /api/alert/outcome  outcome_audit_write                 ok    
121.204      /api/alert/outcome  learning_state_update               ok    
393.197      /api/alert/outcome  l5_conservation_write               ok    
394.028      /api/alert/outcome  conservation_monitor                ok    
0.097        /api/alert/outcome  profile_scorer_update               ok    
0.069        /api/alert/outcome  l5_dk_weight_write                  ok    
455.684      /api/alert/outcome  l5_centroid_write                   ok    
0.013        /api/alert/outcome  l5_dk_weight_write                  ok    
0.029        /api/alert/outcome  snapshot_evolution_logging          ok    
75.335       /api/alert/outcome  snapshot_evolution_logging          ok    
0.024        /api/alert/outcome  response_serialization              ok    
1535.764     /api/alert/outcome  outcome_request_total               ok    
```

### CAMPAIGNP1EDGE-0004
- event_count: 47
- total_observed_ms: 5692.165
- authoritative_total_ms: 1530.859
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.015        /api/alert/analyze  scorer_readiness                    ok    
0.006        /api/alert/analyze  request_parse                       ok    
81.472       /api/alert/analyze  alert_lookup                        ok    
85.848       /api/alert/analyze  security_context_lookup             ok    
0.17         /api/alert/analyze  category_resolution                 ok    
305.24       /api/alert/analyze  factor_vector_construction          ok    
0.187        /api/alert/analyze  scorer_decision                     ok    
0.017        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.008        /api/alert/analyze  routing_threshold_lookup            ok    
0.014        /api/alert/analyze  rl_exploration_proposal             ok    
0.017        /api/alert/analyze  routing_zone_resolution             ok    
147.215      /api/alert/analyze  referral_history_counts             ok    
0.062        /api/alert/analyze  referral_gate_evaluation            ok    
100.015      /api/alert/analyze  reasoning_generation                ok    
82.188       /api/alert/analyze  decision_node_and_edge_write        ok    
93.999       /api/alert/analyze  audit_write                         ok    
0.245        /api/alert/analyze  metadata_logging_snapshot_write     ok    
91.09        /api/alert/analyze  campaign_query_fetch_recent_events  ok    
92.501       /api/alert/analyze  campaign_correlation_summary        ok    
93.564       /api/alert/analyze  campaign_correlation                ok    
0.021        /api/alert/analyze  decision_event_emit                 ok    
77.675       /api/alert/analyze  composite_gate_evaluation           ok    
0.054        /api/alert/analyze  provenance_build                    ok    
76.308       /api/alert/analyze  graph_visualization_fetch           ok    
0.047        /api/alert/analyze  response_context_enrichment         ok    
0.082        /api/alert/analyze  referral_debug_build                ok    
0.021        /api/alert/analyze  shadow_compare_schedule             ok    
79.162       /api/alert/analyze  cluster_history_fetch               ok    
0.031        /api/alert/analyze  narrative_context_build             ok    
0.074        /api/alert/analyze  narrative_generation                ok    
2.845        /api/alert/analyze  response_serialization              ok    
1267.471     /api/alert/analyze  analyze_request_total               ok    
0.014        /api/alert/outcome  request_parse                       ok    
0.008        /api/alert/outcome  duplicate_feedback_guard            ok    
73.384       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.196        /api/alert/outcome  outcome_audit_write                 ok    
93.592       /api/alert/outcome  learning_state_update               ok    
400.068      /api/alert/outcome  l5_conservation_write               ok    
402.246      /api/alert/outcome  conservation_monitor                ok    
0.326        /api/alert/outcome  profile_scorer_update               ok    
0.153        /api/alert/outcome  l5_dk_weight_write                  ok    
405.062      /api/alert/outcome  l5_centroid_write                   ok    
0.018        /api/alert/outcome  l5_dk_weight_write                  ok    
0.019        /api/alert/outcome  snapshot_evolution_logging          ok    
108.518      /api/alert/outcome  snapshot_evolution_logging          ok    
0.038        /api/alert/outcome  response_serialization              ok    
1530.859     /api/alert/outcome  outcome_request_total               ok    
```

### CAMPAIGNP1EDGE-0005
- event_count: 47
- total_observed_ms: 5756.673
- authoritative_total_ms: 1478.802
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.02         /api/alert/analyze  scorer_readiness                    ok    
0.018        /api/alert/analyze  request_parse                       ok    
62.775       /api/alert/analyze  alert_lookup                        ok    
84.534       /api/alert/analyze  security_context_lookup             ok    
0.301        /api/alert/analyze  category_resolution                 ok    
335.475      /api/alert/analyze  factor_vector_construction          ok    
0.18         /api/alert/analyze  scorer_decision                     ok    
0.013        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.007        /api/alert/analyze  routing_threshold_lookup            ok    
0.011        /api/alert/analyze  rl_exploration_proposal             ok    
0.034        /api/alert/analyze  routing_zone_resolution             ok    
168.85       /api/alert/analyze  referral_history_counts             ok    
0.066        /api/alert/analyze  referral_gate_evaluation            ok    
102.381      /api/alert/analyze  reasoning_generation                ok    
84.908       /api/alert/analyze  decision_node_and_edge_write        ok    
78.643       /api/alert/analyze  audit_write                         ok    
0.804        /api/alert/analyze  metadata_logging_snapshot_write     ok    
89.627       /api/alert/analyze  campaign_query_fetch_recent_events  ok    
92.209       /api/alert/analyze  campaign_correlation_summary        ok    
94.661       /api/alert/analyze  campaign_correlation                ok    
0.024        /api/alert/analyze  decision_event_emit                 ok    
91.734       /api/alert/analyze  composite_gate_evaluation           ok    
0.058        /api/alert/analyze  provenance_build                    ok    
67.824       /api/alert/analyze  graph_visualization_fetch           ok    
0.025        /api/alert/analyze  response_context_enrichment         ok    
0.031        /api/alert/analyze  referral_debug_build                ok    
0.014        /api/alert/analyze  shadow_compare_schedule             ok    
69.192       /api/alert/analyze  cluster_history_fetch               ok    
0.034        /api/alert/analyze  narrative_context_build             ok    
0.057        /api/alert/analyze  narrative_generation                ok    
2.627        /api/alert/analyze  response_serialization              ok    
1297.536     /api/alert/analyze  analyze_request_total               ok    
0.018        /api/alert/outcome  request_parse                       ok    
0.008        /api/alert/outcome  duplicate_feedback_guard            ok    
80.286       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.247        /api/alert/outcome  outcome_audit_write                 ok    
136.502      /api/alert/outcome  learning_state_update               ok    
434.288      /api/alert/outcome  l5_conservation_write               ok    
436.234      /api/alert/outcome  conservation_monitor                ok    
0.134        /api/alert/outcome  profile_scorer_update               ok    
0.205        /api/alert/outcome  l5_dk_weight_write                  ok    
396.833      /api/alert/outcome  l5_centroid_write                   ok    
0.025        /api/alert/outcome  l5_dk_weight_write                  ok    
0.036        /api/alert/outcome  snapshot_evolution_logging          ok    
68.356       /api/alert/outcome  snapshot_evolution_logging          ok    
0.026        /api/alert/outcome  response_serialization              ok    
1478.802     /api/alert/outcome  outcome_request_total               ok    
```

### CAMPAIGNP1EDGE-0002
- event_count: 47
- total_observed_ms: 5712.884
- authoritative_total_ms: 1469.613
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.039        /api/alert/analyze  scorer_readiness                    ok    
0.02         /api/alert/analyze  request_parse                       ok    
80.522       /api/alert/analyze  alert_lookup                        ok    
70.962       /api/alert/analyze  security_context_lookup             ok    
0.132        /api/alert/analyze  category_resolution                 ok    
349.715      /api/alert/analyze  factor_vector_construction          ok    
0.178        /api/alert/analyze  scorer_decision                     ok    
0.014        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.007        /api/alert/analyze  routing_threshold_lookup            ok    
0.012        /api/alert/analyze  rl_exploration_proposal             ok    
0.014        /api/alert/analyze  routing_zone_resolution             ok    
145.615      /api/alert/analyze  referral_history_counts             ok    
0.047        /api/alert/analyze  referral_gate_evaluation            ok    
122.866      /api/alert/analyze  reasoning_generation                ok    
97.009       /api/alert/analyze  decision_node_and_edge_write        ok    
96.027       /api/alert/analyze  audit_write                         ok    
0.418        /api/alert/analyze  metadata_logging_snapshot_write     ok    
86.464       /api/alert/analyze  campaign_query_fetch_recent_events  ok    
88.482       /api/alert/analyze  campaign_correlation_summary        ok    
90.595       /api/alert/analyze  campaign_correlation                ok    
0.041        /api/alert/analyze  decision_event_emit                 ok    
82.413       /api/alert/analyze  composite_gate_evaluation           ok    
0.229        /api/alert/analyze  provenance_build                    ok    
74.073       /api/alert/analyze  graph_visualization_fetch           ok    
0.04         /api/alert/analyze  response_context_enrichment         ok    
0.047        /api/alert/analyze  referral_debug_build                ok    
0.026        /api/alert/analyze  shadow_compare_schedule             ok    
63.531       /api/alert/analyze  cluster_history_fetch               ok    
0.028        /api/alert/analyze  narrative_context_build             ok    
0.04         /api/alert/analyze  narrative_generation                ok    
1.66         /api/alert/analyze  response_serialization              ok    
1329.779     /api/alert/analyze  analyze_request_total               ok    
0.009        /api/alert/outcome  request_parse                       ok    
0.008        /api/alert/outcome  duplicate_feedback_guard            ok    
78.171       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.405        /api/alert/outcome  outcome_audit_write                 ok    
90.475       /api/alert/outcome  learning_state_update               ok    
380.103      /api/alert/outcome  l5_conservation_write               ok    
381.274      /api/alert/outcome  conservation_monitor                ok    
0.161        /api/alert/outcome  profile_scorer_update               ok    
0.285        /api/alert/outcome  l5_dk_weight_write                  ok    
408.098      /api/alert/outcome  l5_centroid_write                   ok    
0.02         /api/alert/outcome  l5_dk_weight_write                  ok    
0.045        /api/alert/outcome  snapshot_evolution_logging          ok    
123.143      /api/alert/outcome  snapshot_evolution_logging          ok    
0.029        /api/alert/outcome  response_serialization              ok    
1469.613     /api/alert/outcome  outcome_request_total               ok    
```

## Nested Phase Warning
Nested phase durations should not be summed blindly. Use analyze_request_total, outcome_request_total, or total_attempt as authoritative totals.
