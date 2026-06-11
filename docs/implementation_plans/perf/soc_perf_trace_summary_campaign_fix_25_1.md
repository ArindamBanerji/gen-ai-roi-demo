# SOC Perf Trace Summary

## Safety
- Read-only summary of existing JSONL trace events.
- No backend, graph, proof, or seed operations are performed.
- Nested phases are not additive; request-total phases are the authoritative route totals.

## Input
- trace_jsonl: `C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50\scratch\temp\soc_perf_trace_campaign_fix_25_1.jsonl`
- events_loaded: 1320
- malformed_lines: 0
- route_filter: None
- phase_filter: None

## Route + Phase Aggregates
```text
route_phase                                                     count  avg_ms    p50_ms    p95_ms    p99_ms    max_ms  
--------------------------------------------------------------  -----  --------  --------  --------  --------  --------
/api/alert/analyze | analyze_request_total                      25     1942.674  1942.687  2027.934  2029.954  2030.319
/api/alert/outcome | outcome_request_total                      25     1623.572  1612.076  1766.037  1914.38   1953.247
/api/alert/analyze | campaign_correlation                       25     673.883   695.694   753.124   766.127   769.923 
/api/alert/analyze | campaign_correlation_summary               25     587.36    608.13    646.304   670.62    678.007 
/api/alert/outcome | l5_centroid_write                          25     454.267   456.31    484.006   565.491   590.928 
/api/alert/outcome | conservation_monitor                       25     423.939   425.286   455.136   463.002   465.389 
/api/alert/outcome | l5_conservation_write                      25     421.577   423.736   451.818   460.659   463.381 
/api/alert/outcome | learning_state_update                      25     113.927   99.723    156.365   373.993   442.548 
/api/alert/analyze | reasoning_generation                       25     96.94     73.488    198.957   349.812   390.574 
/api/alert/analyze | factor_vector_construction                 25     332.192   335.416   357.112   367.528   370.564 
/api/alert/analyze | decision_node_and_edge_write               25     96.622    92.013    111.124   201.887   230.513 
/api/alert/analyze | referral_history_counts                    25     171.418   171.161   186.13    186.574   186.709 
/api/alert/analyze | campaign_query_create_campaign             24     89.724    87.394    106.99    117.067   119.928 
/api/alert/analyze | campaign_query_fetch_recent_events         25     85.122    82.607    108.299   115.642   117.471 
/api/alert/analyze | campaign_query_find_matching_campaign      25     86.454    85.658    102.063   112.234   115.337 
/api/alert/analyze | security_context_lookup                    25     89.44     89.214    103.943   111.603   113.738 
/api/alert/outcome | snapshot_evolution_logging                 50     42.917    35.091    96.642    108.907   111.336 
/api/alert/outcome | decision_lookup_and_outcome_update         25     91.289    93.098    107.434   110.085   110.902 
/api/alert/analyze | campaign_query_member_alert_nodes_read     24     82.816    79.758    103.79    106.397   106.868 
/api/alert/analyze | alert_lookup                               25     79.844    78.435    98.583    103.238   104.526 
/api/alert/analyze | campaign_query_check_campaign_exists       24     81.508    81.103    94.4      102.221   104.482 
/api/alert/analyze | campaign_query_member_edges_existing_read  24     81.756    81.774    98.23     102.487   103.522 
/api/alert/analyze | audit_write                                25     89.464    88.57     101.449   102.815   102.836 
/api/alert/analyze | cluster_history_fetch                      25     82.468    83.92     97.536    100.608   101.472 
/api/alert/analyze | graph_visualization_fetch                  25     84.076    85.897    97.441    99.613    99.91   
/api/alert/analyze | composite_gate_evaluation                  25     81.485    82.425    94.273    97.383    98.31   
/api/alert/analyze | campaign_query_member_edges_batch_create   24     81.483    81.173    96.738    97.554    97.734  
/api/alert/outcome | outcome_audit_write                        25     0.986     0.411     0.928     11.002    14.177  
/api/alert/analyze | response_serialization                     25     4.81      5.016     8.26      10.349    10.918  
/api/alert/analyze | post_scorer_confidence_gate                25     0.248     0.022     0.032     4.334     5.693   
/api/alert/analyze | category_resolution                        25     0.28      0.145     0.364     2.287     2.886   
/api/alert/analyze | metadata_logging_snapshot_write            25     0.478     0.36      0.919     2.117     2.485   
/api/alert/analyze | rl_exploration_proposal                    25     0.105     0.022     0.028     1.654     2.167   
/api/alert/outcome | l5_dk_weight_write                         50     0.16      0.105     0.459     1.104     1.376   
/api/alert/analyze | scorer_decision                            25     0.296     0.3       0.502     0.722     0.788   
/api/alert/outcome | profile_scorer_update                      25     0.228     0.234     0.372     0.456     0.481   
/api/alert/analyze | narrative_generation                       25     0.092     0.087     0.201     0.305     0.334   
/api/alert/analyze | provenance_build                           25     0.096     0.078     0.177     0.218     0.231   
/api/alert/analyze | response_context_enrichment                25     0.038     0.027     0.069     0.147     0.171   
/api/alert/analyze | referral_gate_evaluation                   25     0.056     0.048     0.085     0.117     0.127   
```

## Phase Aggregates
```text
phase                                      count  avg_ms    p50_ms    p95_ms    p99_ms    max_ms  
-----------------------------------------  -----  --------  --------  --------  --------  --------
analyze_request_total                      25     1942.674  1942.687  2027.934  2029.954  2030.319
outcome_request_total                      25     1623.572  1612.076  1766.037  1914.38   1953.247
campaign_correlation                       25     673.883   695.694   753.124   766.127   769.923 
campaign_correlation_summary               25     587.36    608.13    646.304   670.62    678.007 
l5_centroid_write                          25     454.267   456.31    484.006   565.491   590.928 
conservation_monitor                       25     423.939   425.286   455.136   463.002   465.389 
l5_conservation_write                      25     421.577   423.736   451.818   460.659   463.381 
learning_state_update                      25     113.927   99.723    156.365   373.993   442.548 
reasoning_generation                       25     96.94     73.488    198.957   349.812   390.574 
factor_vector_construction                 25     332.192   335.416   357.112   367.528   370.564 
decision_node_and_edge_write               25     96.622    92.013    111.124   201.887   230.513 
referral_history_counts                    25     171.418   171.161   186.13    186.574   186.709 
campaign_query_create_campaign             24     89.724    87.394    106.99    117.067   119.928 
campaign_query_fetch_recent_events         25     85.122    82.607    108.299   115.642   117.471 
campaign_query_find_matching_campaign      25     86.454    85.658    102.063   112.234   115.337 
security_context_lookup                    25     89.44     89.214    103.943   111.603   113.738 
snapshot_evolution_logging                 50     42.917    35.091    96.642    108.907   111.336 
decision_lookup_and_outcome_update         25     91.289    93.098    107.434   110.085   110.902 
campaign_query_member_alert_nodes_read     24     82.816    79.758    103.79    106.397   106.868 
alert_lookup                               25     79.844    78.435    98.583    103.238   104.526 
campaign_query_check_campaign_exists       24     81.508    81.103    94.4      102.221   104.482 
campaign_query_member_edges_existing_read  24     81.756    81.774    98.23     102.487   103.522 
audit_write                                25     89.464    88.57     101.449   102.815   102.836 
cluster_history_fetch                      25     82.468    83.92     97.536    100.608   101.472 
graph_visualization_fetch                  25     84.076    85.897    97.441    99.613    99.91   
composite_gate_evaluation                  25     81.485    82.425    94.273    97.383    98.31   
campaign_query_member_edges_batch_create   24     81.483    81.173    96.738    97.554    97.734  
outcome_audit_write                        25     0.986     0.411     0.928     11.002    14.177  
response_serialization                     50     2.42      0.973     6.953     9.757     10.918  
post_scorer_confidence_gate                25     0.248     0.022     0.032     4.334     5.693   
category_resolution                        25     0.28      0.145     0.364     2.287     2.886   
metadata_logging_snapshot_write            25     0.478     0.36      0.919     2.117     2.485   
rl_exploration_proposal                    25     0.105     0.022     0.028     1.654     2.167   
l5_dk_weight_write                         50     0.16      0.105     0.459     1.104     1.376   
scorer_decision                            25     0.296     0.3       0.502     0.722     0.788   
profile_scorer_update                      25     0.228     0.234     0.372     0.456     0.481   
narrative_generation                       25     0.092     0.087     0.201     0.305     0.334   
provenance_build                           25     0.096     0.078     0.177     0.218     0.231   
response_context_enrichment                25     0.038     0.027     0.069     0.147     0.171   
referral_gate_evaluation                   25     0.056     0.048     0.085     0.117     0.127   
```

## Graph Aggregates
```text
graph_name                   count  avg_ms   p50_ms  p95_ms   p99_ms    max_ms  
---------------------------  -----  -------  ------  -------  --------  --------
soc_graph_campaign_fix_25_1  1320   155.355  66.411  678.712  1942.402  2030.319
```

## Top Slow Events
```text
duration_ms  route               phase                  alert_id            decision_id                           attempt_index  status
-----------  ------------------  ---------------------  ------------------  ------------------------------------  -------------  ------
2030.319     /api/alert/analyze  analyze_request_total  CAMPAIGNFIX25-0019  39b69189-a9bd-483d-bc5a-61d5445de1f7  None           ok    
2028.799     /api/alert/analyze  analyze_request_total  CAMPAIGNFIX25-0017  83107546-9895-49ae-9025-c4465544dd65  None           ok    
2024.473     /api/alert/analyze  analyze_request_total  CAMPAIGNFIX25-0020  0529e51d-6d5b-40cc-b3c2-8308a29ddd9b  None           ok    
2023.928     /api/alert/analyze  analyze_request_total  CAMPAIGNFIX25-0025  852a1c5c-f04b-45e6-b88e-df9de7ab1e89  None           ok    
2020.92      /api/alert/analyze  analyze_request_total  CAMPAIGNFIX25-0005  4dfd3c10-5eec-4274-90e1-484ce1e85a56  None           ok    
2002.546     /api/alert/analyze  analyze_request_total  CAMPAIGNFIX25-0002  aa912963-29ef-45f3-a947-0a3f400bf1fa  None           ok    
1989.399     /api/alert/analyze  analyze_request_total  CAMPAIGNFIX25-0024  e12c4163-2a50-4a38-be9d-57d21ba61d84  None           ok    
1985.877     /api/alert/analyze  analyze_request_total  CAMPAIGNFIX25-0012  4accfea9-852f-4cbb-9d29-3029f8f6ebd8  None           ok    
1977.954     /api/alert/analyze  analyze_request_total  CAMPAIGNFIX25-0003  6f33bd6a-90f1-463d-bc50-a5c10fc7c3ee  None           ok    
1970.719     /api/alert/analyze  analyze_request_total  CAMPAIGNFIX25-0021  5763633d-0a8d-4ed5-8e04-d684dfa07f6f  None           ok    
1967.593     /api/alert/analyze  analyze_request_total  CAMPAIGNFIX25-0010  a97ab9d9-591b-4d04-be42-89bb0f866484  None           ok    
1953.247     /api/alert/outcome  outcome_request_total  CAMPAIGNFIX25-0005  4dfd3c10-5eec-4274-90e1-484ce1e85a56  None           ok    
1943.654     /api/alert/analyze  analyze_request_total  CAMPAIGNFIX25-0018  9de0fa4f-9d25-4a11-b973-6a8d2fda4600  None           ok    
1942.687     /api/alert/analyze  analyze_request_total  CAMPAIGNFIX25-0004  e11ea5c3-828f-414c-815d-4551936ca8e6  None           ok    
1941.187     /api/alert/analyze  analyze_request_total  CAMPAIGNFIX25-0023  8703e3d3-10f7-440a-a786-9bad4758806c  None           ok    
1931.029     /api/alert/analyze  analyze_request_total  CAMPAIGNFIX25-0008  04547397-06ae-4569-855d-42c82dfa0cbf  None           ok    
1920.521     /api/alert/analyze  analyze_request_total  CAMPAIGNFIX25-0022  f2e8d26d-85ec-4576-9e84-28c9145c7892  None           ok    
1912.301     /api/alert/analyze  analyze_request_total  CAMPAIGNFIX25-0014  9953fb88-c509-4b06-9ffc-072f9651f7a7  None           ok    
1907.352     /api/alert/analyze  analyze_request_total  CAMPAIGNFIX25-0009  41fb67f1-ea8e-444d-969f-0971a34773a2  None           ok    
1899.091     /api/alert/analyze  analyze_request_total  CAMPAIGNFIX25-0015  fe5779df-dc7a-4a38-9cb5-b038ebf9d64d  None           ok    
```

## Early/Mid/Late Windows
```text
(none)
```

## Per-Alert Waterfall

### CAMPAIGNFIX25-0019
- event_count: 53
- total_observed_ms: 8558.184
- authoritative_total_ms: 2030.319
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.014        /api/alert/analyze  scorer_readiness                           ok    
0.006        /api/alert/analyze  request_parse                              ok    
67.526       /api/alert/analyze  alert_lookup                               ok    
73.616       /api/alert/analyze  security_context_lookup                    ok    
0.185        /api/alert/analyze  category_resolution                        ok    
357.912      /api/alert/analyze  factor_vector_construction                 ok    
0.319        /api/alert/analyze  scorer_decision                            ok    
0.018        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.016        /api/alert/analyze  routing_threshold_lookup                   ok    
0.012        /api/alert/analyze  rl_exploration_proposal                    ok    
0.025        /api/alert/analyze  routing_zone_resolution                    ok    
167.418      /api/alert/analyze  referral_history_counts                    ok    
0.041        /api/alert/analyze  referral_gate_evaluation                   ok    
84.306       /api/alert/analyze  reasoning_generation                       ok    
89.292       /api/alert/analyze  decision_node_and_edge_write               ok    
102.836      /api/alert/analyze  audit_write                                ok    
0.476        /api/alert/analyze  metadata_logging_snapshot_write            ok    
102.408      /api/alert/analyze  campaign_query_find_matching_campaign      ok    
84.031       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
82.181       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
107.491      /api/alert/analyze  campaign_query_create_campaign             ok    
80.483       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
88.865       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
81.149       /api/alert/analyze  campaign_query_member_edges_batch_create   error 
647.227      /api/alert/analyze  campaign_correlation_summary               ok    
749.196      /api/alert/analyze  campaign_correlation                       ok    
0.039        /api/alert/analyze  decision_event_emit                        ok    
84.396       /api/alert/analyze  composite_gate_evaluation                  ok    
0.114        /api/alert/analyze  provenance_build                           ok    
87.678       /api/alert/analyze  graph_visualization_fetch                  ok    
0.034        /api/alert/analyze  response_context_enrichment                ok    
0.044        /api/alert/analyze  referral_debug_build                       ok    
0.026        /api/alert/analyze  shadow_compare_schedule                    ok    
101.472      /api/alert/analyze  cluster_history_fetch                      ok    
0.058        /api/alert/analyze  narrative_context_build                    ok    
0.087        /api/alert/analyze  narrative_generation                       ok    
5.189        /api/alert/analyze  response_serialization                     ok    
2030.319     /api/alert/analyze  analyze_request_total                      ok    
0.024        /api/alert/outcome  request_parse                              ok    
0.015        /api/alert/outcome  duplicate_feedback_guard                   ok    
93.725       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.418        /api/alert/outcome  outcome_audit_write                        ok    
105.092      /api/alert/outcome  learning_state_update                      ok    
428.862      /api/alert/outcome  l5_conservation_write                      ok    
431.334      /api/alert/outcome  conservation_monitor                       ok    
0.27         /api/alert/outcome  profile_scorer_update                      ok    
0.204        /api/alert/outcome  l5_dk_weight_write                         ok    
480.274      /api/alert/outcome  l5_centroid_write                          ok    
0.013        /api/alert/outcome  l5_dk_weight_write                         ok    
0.017        /api/alert/outcome  snapshot_evolution_logging                 ok    
88.319       /api/alert/outcome  snapshot_evolution_logging                 ok    
0.02         /api/alert/outcome  response_serialization                     ok    
1653.092     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNFIX25-0017
- event_count: 53
- total_observed_ms: 8389.642
- authoritative_total_ms: 2028.799
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.015        /api/alert/analyze  scorer_readiness                           ok    
0.007        /api/alert/analyze  request_parse                              ok    
66.007       /api/alert/analyze  alert_lookup                               ok    
88.139       /api/alert/analyze  security_context_lookup                    ok    
0.127        /api/alert/analyze  category_resolution                        ok    
310.112      /api/alert/analyze  factor_vector_construction                 ok    
0.177        /api/alert/analyze  scorer_decision                            ok    
0.013        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.008        /api/alert/analyze  routing_threshold_lookup                   ok    
0.013        /api/alert/analyze  rl_exploration_proposal                    ok    
0.014        /api/alert/analyze  routing_zone_resolution                    ok    
180.186      /api/alert/analyze  referral_history_counts                    ok    
0.055        /api/alert/analyze  referral_gate_evaluation                   ok    
69.692       /api/alert/analyze  reasoning_generation                       ok    
230.513      /api/alert/analyze  decision_node_and_edge_write               ok    
74.85        /api/alert/analyze  audit_write                                ok    
0.438        /api/alert/analyze  metadata_logging_snapshot_write            ok    
76.604       /api/alert/analyze  campaign_query_find_matching_campaign      ok    
117.471      /api/alert/analyze  campaign_query_fetch_recent_events         ok    
83.683       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
98.829       /api/alert/analyze  campaign_query_create_campaign             ok    
76.508       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
71.449       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
77.049       /api/alert/analyze  campaign_query_member_edges_batch_create   error 
616.906      /api/alert/analyze  campaign_correlation_summary               ok    
714.019      /api/alert/analyze  campaign_correlation                       ok    
0.044        /api/alert/analyze  decision_event_emit                        ok    
82.954       /api/alert/analyze  composite_gate_evaluation                  ok    
0.065        /api/alert/analyze  provenance_build                           ok    
77.619       /api/alert/analyze  graph_visualization_fetch                  ok    
0.023        /api/alert/analyze  response_context_enrichment                ok    
0.028        /api/alert/analyze  referral_debug_build                       ok    
0.012        /api/alert/analyze  shadow_compare_schedule                    ok    
82.034       /api/alert/analyze  cluster_history_fetch                      ok    
0.057        /api/alert/analyze  narrative_context_build                    ok    
0.077        /api/alert/analyze  narrative_generation                       ok    
5.634        /api/alert/analyze  response_serialization                     ok    
2028.799     /api/alert/analyze  analyze_request_total                      ok    
0.009        /api/alert/outcome  request_parse                              ok    
0.011        /api/alert/outcome  duplicate_feedback_guard                   ok    
85.765       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.846        /api/alert/outcome  outcome_audit_write                        ok    
113.621      /api/alert/outcome  learning_state_update                      ok    
400.919      /api/alert/outcome  l5_conservation_write                      ok    
402.565      /api/alert/outcome  conservation_monitor                       ok    
0.195        /api/alert/outcome  profile_scorer_update                      ok    
0.107        /api/alert/outcome  l5_dk_weight_write                         ok    
455.647      /api/alert/outcome  l5_centroid_write                          ok    
0.025        /api/alert/outcome  l5_dk_weight_write                         ok    
0.126        /api/alert/outcome  snapshot_evolution_logging                 ok    
87.477       /api/alert/outcome  snapshot_evolution_logging                 ok    
0.023        /api/alert/outcome  response_serialization                     ok    
1612.076     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNFIX25-0020
- event_count: 53
- total_observed_ms: 8781.762
- authoritative_total_ms: 2024.473
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.019        /api/alert/analyze  scorer_readiness                           ok    
0.015        /api/alert/analyze  request_parse                              ok    
68.125       /api/alert/analyze  alert_lookup                               ok    
85.078       /api/alert/analyze  security_context_lookup                    ok    
0.132        /api/alert/analyze  category_resolution                        ok    
353.91       /api/alert/analyze  factor_vector_construction                 ok    
0.323        /api/alert/analyze  scorer_decision                            ok    
0.025        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.016        /api/alert/analyze  routing_threshold_lookup                   ok    
0.024        /api/alert/analyze  rl_exploration_proposal                    ok    
0.026        /api/alert/analyze  routing_zone_resolution                    ok    
181.407      /api/alert/analyze  referral_history_counts                    ok    
0.059        /api/alert/analyze  referral_gate_evaluation                   ok    
82.243       /api/alert/analyze  reasoning_generation                       ok    
111.237      /api/alert/analyze  decision_node_and_edge_write               ok    
82.772       /api/alert/analyze  audit_write                                ok    
0.184        /api/alert/analyze  metadata_logging_snapshot_write            ok    
79.401       /api/alert/analyze  campaign_query_find_matching_campaign      ok    
82.607       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
78.454       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
99.095       /api/alert/analyze  campaign_query_create_campaign             ok    
88.201       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
97.961       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
97.734       /api/alert/analyze  campaign_query_member_edges_batch_create   error 
642.611      /api/alert/analyze  campaign_correlation_summary               ok    
754.106      /api/alert/analyze  campaign_correlation                       ok    
0.039        /api/alert/analyze  decision_event_emit                        ok    
85.822       /api/alert/analyze  composite_gate_evaluation                  ok    
0.105        /api/alert/analyze  provenance_build                           ok    
87.714       /api/alert/analyze  graph_visualization_fetch                  ok    
0.031        /api/alert/analyze  response_context_enrichment                ok    
0.045        /api/alert/analyze  referral_debug_build                       ok    
0.012        /api/alert/analyze  shadow_compare_schedule                    ok    
70.409       /api/alert/analyze  cluster_history_fetch                      ok    
0.028        /api/alert/analyze  narrative_context_build                    ok    
0.04         /api/alert/analyze  narrative_generation                       ok    
2.1          /api/alert/analyze  response_serialization                     ok    
2024.473     /api/alert/analyze  analyze_request_total                      ok    
0.008        /api/alert/outcome  request_parse                              ok    
0.01         /api/alert/outcome  duplicate_feedback_guard                   ok    
83.128       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
14.177       /api/alert/outcome  outcome_audit_write                        ok    
115.5        /api/alert/outcome  learning_state_update                      ok    
423.0        /api/alert/outcome  l5_conservation_write                      ok    
425.286      /api/alert/outcome  conservation_monitor                       ok    
0.267        /api/alert/outcome  profile_scorer_update                      ok    
0.213        /api/alert/outcome  l5_dk_weight_write                         ok    
590.928      /api/alert/outcome  l5_centroid_write                          ok    
0.015        /api/alert/outcome  l5_dk_weight_write                         ok    
0.033        /api/alert/outcome  snapshot_evolution_logging                 ok    
81.29        /api/alert/outcome  snapshot_evolution_logging                 ok    
0.023        /api/alert/outcome  response_serialization                     ok    
1791.301     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNFIX25-0025
- event_count: 53
- total_observed_ms: 8550.23
- authoritative_total_ms: 2023.928
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.014        /api/alert/analyze  scorer_readiness                           ok    
0.006        /api/alert/analyze  request_parse                              ok    
80.684       /api/alert/analyze  alert_lookup                               ok    
84.516       /api/alert/analyze  security_context_lookup                    ok    
0.145        /api/alert/analyze  category_resolution                        ok    
335.015      /api/alert/analyze  factor_vector_construction                 ok    
0.328        /api/alert/analyze  scorer_decision                            ok    
0.03         /api/alert/analyze  post_scorer_confidence_gate                ok    
0.019        /api/alert/analyze  routing_threshold_lookup                   ok    
0.028        /api/alert/analyze  rl_exploration_proposal                    ok    
0.036        /api/alert/analyze  routing_zone_resolution                    ok    
167.975      /api/alert/analyze  referral_history_counts                    ok    
0.06         /api/alert/analyze  referral_gate_evaluation                   ok    
75.064       /api/alert/analyze  reasoning_generation                       ok    
96.452       /api/alert/analyze  decision_node_and_edge_write               ok    
87.372       /api/alert/analyze  audit_write                                ok    
0.188        /api/alert/analyze  metadata_logging_snapshot_write            ok    
99.578       /api/alert/analyze  campaign_query_find_matching_campaign      ok    
109.851      /api/alert/analyze  campaign_query_fetch_recent_events         ok    
78.467       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
90.274       /api/alert/analyze  campaign_query_create_campaign             ok    
85.322       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
104.819      /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
87.794       /api/alert/analyze  campaign_query_member_edges_batch_create   error 
678.007      /api/alert/analyze  campaign_correlation_summary               ok    
769.923      /api/alert/analyze  campaign_correlation                       ok    
0.041        /api/alert/analyze  decision_event_emit                        ok    
83.32        /api/alert/analyze  composite_gate_evaluation                  ok    
0.112        /api/alert/analyze  provenance_build                           ok    
86.184       /api/alert/analyze  graph_visualization_fetch                  ok    
0.044        /api/alert/analyze  response_context_enrichment                ok    
0.032        /api/alert/analyze  referral_debug_build                       ok    
0.025        /api/alert/analyze  shadow_compare_schedule                    ok    
84.622       /api/alert/analyze  cluster_history_fetch                      ok    
0.086        /api/alert/analyze  narrative_context_build                    ok    
0.113        /api/alert/analyze  narrative_generation                       ok    
8.549        /api/alert/analyze  response_serialization                     ok    
2023.928     /api/alert/analyze  analyze_request_total                      ok    
0.035        /api/alert/outcome  request_parse                              ok    
0.033        /api/alert/outcome  duplicate_feedback_guard                   ok    
93.977       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.239        /api/alert/outcome  outcome_audit_write                        ok    
72.653       /api/alert/outcome  learning_state_update                      ok    
442.141      /api/alert/outcome  l5_conservation_write                      ok    
443.809      /api/alert/outcome  conservation_monitor                       ok    
0.13         /api/alert/outcome  profile_scorer_update                      ok    
0.22         /api/alert/outcome  l5_dk_weight_write                         ok    
473.074      /api/alert/outcome  l5_centroid_write                          ok    
0.025        /api/alert/outcome  l5_dk_weight_write                         ok    
0.029        /api/alert/outcome  snapshot_evolution_logging                 ok    
87.1         /api/alert/outcome  snapshot_evolution_logging                 ok    
0.023        /api/alert/outcome  response_serialization                     ok    
1617.719     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNFIX25-0005
- event_count: 53
- total_observed_ms: 9091.714
- authoritative_total_ms: 2020.92
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.036        /api/alert/analyze  scorer_readiness                           ok    
0.015        /api/alert/analyze  request_parse                              ok    
85.202       /api/alert/analyze  alert_lookup                               ok    
89.214       /api/alert/analyze  security_context_lookup                    ok    
0.236        /api/alert/analyze  category_resolution                        ok    
345.0        /api/alert/analyze  factor_vector_construction                 ok    
0.423        /api/alert/analyze  scorer_decision                            ok    
0.032        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.017        /api/alert/analyze  routing_threshold_lookup                   ok    
0.02         /api/alert/analyze  rl_exploration_proposal                    ok    
0.029        /api/alert/analyze  routing_zone_resolution                    ok    
181.919      /api/alert/analyze  referral_history_counts                    ok    
0.04         /api/alert/analyze  referral_gate_evaluation                   ok    
103.082      /api/alert/analyze  reasoning_generation                       ok    
87.473       /api/alert/analyze  decision_node_and_edge_write               ok    
87.056       /api/alert/analyze  audit_write                                ok    
0.183        /api/alert/analyze  metadata_logging_snapshot_write            ok    
77.963       /api/alert/analyze  campaign_query_find_matching_campaign      ok    
77.116       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
94.65        /api/alert/analyze  campaign_query_check_campaign_exists       ok    
83.57        /api/alert/analyze  campaign_query_create_campaign             ok    
93.748       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
73.595       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
96.952       /api/alert/analyze  campaign_query_member_edges_batch_create   error 
614.015      /api/alert/analyze  campaign_correlation_summary               ok    
709.217      /api/alert/analyze  campaign_correlation                       ok    
0.035        /api/alert/analyze  decision_event_emit                        ok    
77.51        /api/alert/analyze  composite_gate_evaluation                  ok    
0.116        /api/alert/analyze  provenance_build                           ok    
84.967       /api/alert/analyze  graph_visualization_fetch                  ok    
0.044        /api/alert/analyze  response_context_enrichment                ok    
0.053        /api/alert/analyze  referral_debug_build                       ok    
0.03         /api/alert/analyze  shadow_compare_schedule                    ok    
97.871       /api/alert/analyze  cluster_history_fetch                      ok    
0.053        /api/alert/analyze  narrative_context_build                    ok    
0.092        /api/alert/analyze  narrative_generation                       ok    
5.009        /api/alert/analyze  response_serialization                     ok    
2020.92      /api/alert/analyze  analyze_request_total                      ok    
0.017        /api/alert/outcome  request_parse                              ok    
0.028        /api/alert/outcome  duplicate_feedback_guard                   ok    
110.902      /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.411        /api/alert/outcome  outcome_audit_write                        ok    
442.548      /api/alert/outcome  learning_state_update                      ok    
443.283      /api/alert/outcome  l5_conservation_write                      ok    
445.852      /api/alert/outcome  conservation_monitor                       ok    
0.289        /api/alert/outcome  profile_scorer_update                      ok    
0.231        /api/alert/outcome  l5_dk_weight_write                         ok    
432.997      /api/alert/outcome  l5_centroid_write                          ok    
0.017        /api/alert/outcome  l5_dk_weight_write                         ok    
0.038        /api/alert/outcome  snapshot_evolution_logging                 ok    
74.327       /api/alert/outcome  snapshot_evolution_logging                 ok    
0.024        /api/alert/outcome  response_serialization                     ok    
1953.247     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNFIX25-0002
- event_count: 53
- total_observed_ms: 8432.106
- authoritative_total_ms: 2002.546
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.039        /api/alert/analyze  scorer_readiness                           ok    
0.014        /api/alert/analyze  request_parse                              ok    
96.281       /api/alert/analyze  alert_lookup                               ok    
89.902       /api/alert/analyze  security_context_lookup                    ok    
0.392        /api/alert/analyze  category_resolution                        ok    
259.859      /api/alert/analyze  factor_vector_construction                 ok    
0.208        /api/alert/analyze  scorer_decision                            ok    
0.013        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.007        /api/alert/analyze  routing_threshold_lookup                   ok    
0.012        /api/alert/analyze  rl_exploration_proposal                    ok    
0.016        /api/alert/analyze  routing_zone_resolution                    ok    
150.764      /api/alert/analyze  referral_history_counts                    ok    
0.048        /api/alert/analyze  referral_gate_evaluation                   ok    
220.734      /api/alert/analyze  reasoning_generation                       ok    
110.673      /api/alert/analyze  decision_node_and_edge_write               ok    
85.615       /api/alert/analyze  audit_write                                ok    
0.34         /api/alert/analyze  metadata_logging_snapshot_write            ok    
98.412       /api/alert/analyze  campaign_query_find_matching_campaign      ok    
89.107       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
81.898       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
83.563       /api/alert/analyze  campaign_query_create_campaign             ok    
86.64        /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
96.563       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
62.687       /api/alert/analyze  campaign_query_member_edges_batch_create   error 
608.13       /api/alert/analyze  campaign_correlation_summary               ok    
684.745      /api/alert/analyze  campaign_correlation                       ok    
0.026        /api/alert/analyze  decision_event_emit                        ok    
65.98        /api/alert/analyze  composite_gate_evaluation                  ok    
0.074        /api/alert/analyze  provenance_build                           ok    
86.557       /api/alert/analyze  graph_visualization_fetch                  ok    
0.072        /api/alert/analyze  response_context_enrichment                ok    
0.079        /api/alert/analyze  referral_debug_build                       ok    
0.012        /api/alert/analyze  shadow_compare_schedule                    ok    
83.92        /api/alert/analyze  cluster_history_fetch                      ok    
0.077        /api/alert/analyze  narrative_context_build                    ok    
0.147        /api/alert/analyze  narrative_generation                       ok    
7.102        /api/alert/analyze  response_serialization                     ok    
2002.546     /api/alert/analyze  analyze_request_total                      ok    
0.012        /api/alert/outcome  request_parse                              ok    
0.019        /api/alert/outcome  duplicate_feedback_guard                   ok    
107.18       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.818        /api/alert/outcome  outcome_audit_write                        ok    
154.208      /api/alert/outcome  learning_state_update                      ok    
425.42       /api/alert/outcome  l5_conservation_write                      ok    
426.945      /api/alert/outcome  conservation_monitor                       ok    
0.28         /api/alert/outcome  profile_scorer_update                      ok    
0.388        /api/alert/outcome  l5_dk_weight_write                         ok    
420.036      /api/alert/outcome  l5_centroid_write                          ok    
0.07         /api/alert/outcome  l5_dk_weight_write                         ok    
0.071        /api/alert/outcome  snapshot_evolution_logging                 ok    
106.379      /api/alert/outcome  snapshot_evolution_logging                 ok    
0.046        /api/alert/outcome  response_serialization                     ok    
1636.98      /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNFIX25-0024
- event_count: 53
- total_observed_ms: 8302.562
- authoritative_total_ms: 1989.399
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.016        /api/alert/analyze  scorer_readiness                           ok    
0.006        /api/alert/analyze  request_parse                              ok    
68.842       /api/alert/analyze  alert_lookup                               ok    
104.841      /api/alert/analyze  security_context_lookup                    ok    
0.196        /api/alert/analyze  category_resolution                        ok    
343.211      /api/alert/analyze  factor_vector_construction                 ok    
0.31         /api/alert/analyze  scorer_decision                            ok    
0.014        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.007        /api/alert/analyze  routing_threshold_lookup                   ok    
0.012        /api/alert/analyze  rl_exploration_proposal                    ok    
0.014        /api/alert/analyze  routing_zone_resolution                    ok    
164.896      /api/alert/analyze  referral_history_counts                    ok    
0.067        /api/alert/analyze  referral_gate_evaluation                   ok    
68.435       /api/alert/analyze  reasoning_generation                       ok    
92.802       /api/alert/analyze  decision_node_and_edge_write               ok    
102.749      /api/alert/analyze  audit_write                                ok    
0.401        /api/alert/analyze  metadata_logging_snapshot_write            ok    
92.114       /api/alert/analyze  campaign_query_find_matching_campaign      ok    
78.255       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
79.623       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
100.338      /api/alert/analyze  campaign_query_create_campaign             ok    
85.175       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
77.679       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
91.929       /api/alert/analyze  campaign_query_member_edges_batch_create   error 
623.84       /api/alert/analyze  campaign_correlation_summary               ok    
713.407      /api/alert/analyze  campaign_correlation                       ok    
0.041        /api/alert/analyze  decision_event_emit                        ok    
94.447       /api/alert/analyze  composite_gate_evaluation                  ok    
0.118        /api/alert/analyze  provenance_build                           ok    
92.523       /api/alert/analyze  graph_visualization_fetch                  ok    
0.025        /api/alert/analyze  response_context_enrichment                ok    
0.037        /api/alert/analyze  referral_debug_build                       ok    
0.02         /api/alert/analyze  shadow_compare_schedule                    ok    
78.384       /api/alert/analyze  cluster_history_fetch                      ok    
0.052        /api/alert/analyze  narrative_context_build                    ok    
0.215        /api/alert/analyze  narrative_generation                       ok    
5.016        /api/alert/analyze  response_serialization                     ok    
1989.399     /api/alert/analyze  analyze_request_total                      ok    
0.018        /api/alert/outcome  request_parse                              ok    
0.008        /api/alert/outcome  duplicate_feedback_guard                   ok    
75.802       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.38         /api/alert/outcome  outcome_audit_write                        ok    
93.538       /api/alert/outcome  learning_state_update                      ok    
422.649      /api/alert/outcome  l5_conservation_write                      ok    
425.266      /api/alert/outcome  conservation_monitor                       ok    
0.149        /api/alert/outcome  profile_scorer_update                      ok    
0.105        /api/alert/outcome  l5_dk_weight_write                         ok    
460.64       /api/alert/outcome  l5_centroid_write                          ok    
0.027        /api/alert/outcome  l5_dk_weight_write                         ok    
0.035        /api/alert/outcome  snapshot_evolution_logging                 ok    
82.814       /api/alert/outcome  snapshot_evolution_logging                 ok    
0.042        /api/alert/outcome  response_serialization                     ok    
1591.633     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNFIX25-0012
- event_count: 53
- total_observed_ms: 8385.167
- authoritative_total_ms: 1985.877
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.023        /api/alert/analyze  scorer_readiness                           ok    
0.014        /api/alert/analyze  request_parse                              ok    
74.889       /api/alert/analyze  alert_lookup                               ok    
75.723       /api/alert/analyze  security_context_lookup                    ok    
0.212        /api/alert/analyze  category_resolution                        ok    
370.564      /api/alert/analyze  factor_vector_construction                 ok    
0.325        /api/alert/analyze  scorer_decision                            ok    
0.025        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.017        /api/alert/analyze  routing_threshold_lookup                   ok    
0.024        /api/alert/analyze  rl_exploration_proposal                    ok    
0.026        /api/alert/analyze  routing_zone_resolution                    ok    
186.709      /api/alert/analyze  referral_history_counts                    ok    
0.07         /api/alert/analyze  referral_gate_evaluation                   ok    
69.598       /api/alert/analyze  reasoning_generation                       ok    
83.53        /api/alert/analyze  decision_node_and_edge_write               ok    
88.024       /api/alert/analyze  audit_write                                ok    
0.486        /api/alert/analyze  metadata_logging_snapshot_write            ok    
79.538       /api/alert/analyze  campaign_query_find_matching_campaign      ok    
87.361       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
104.482      /api/alert/analyze  campaign_query_check_campaign_exists       ok    
83.97        /api/alert/analyze  campaign_query_create_campaign             ok    
103.522      /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
65.859       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
87.927       /api/alert/analyze  campaign_query_member_edges_batch_create   error 
629.0        /api/alert/analyze  campaign_correlation_summary               ok    
712.921      /api/alert/analyze  campaign_correlation                       ok    
0.05         /api/alert/analyze  decision_event_emit                        ok    
81.752       /api/alert/analyze  composite_gate_evaluation                  ok    
0.061        /api/alert/analyze  provenance_build                           ok    
99.91        /api/alert/analyze  graph_visualization_fetch                  ok    
0.021        /api/alert/analyze  response_context_enrichment                ok    
0.028        /api/alert/analyze  referral_debug_build                       ok    
0.013        /api/alert/analyze  shadow_compare_schedule                    ok    
79.979       /api/alert/analyze  cluster_history_fetch                      ok    
0.036        /api/alert/analyze  narrative_context_build                    ok    
0.046        /api/alert/analyze  narrative_generation                       ok    
4.238        /api/alert/analyze  response_serialization                     ok    
1985.877     /api/alert/analyze  analyze_request_total                      ok    
0.029        /api/alert/outcome  request_parse                              ok    
0.035        /api/alert/outcome  duplicate_feedback_guard                   ok    
94.073       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.245        /api/alert/outcome  outcome_audit_write                        ok    
99.723       /api/alert/outcome  learning_state_update                      ok    
412.989      /api/alert/outcome  l5_conservation_write                      ok    
416.146      /api/alert/outcome  conservation_monitor                       ok    
0.234        /api/alert/outcome  profile_scorer_update                      ok    
0.331        /api/alert/outcome  l5_dk_weight_write                         ok    
457.836      /api/alert/outcome  l5_centroid_write                          ok    
0.035        /api/alert/outcome  l5_dk_weight_write                         ok    
0.042        /api/alert/outcome  snapshot_evolution_logging                 ok    
85.343       /api/alert/outcome  snapshot_evolution_logging                 ok    
0.044        /api/alert/outcome  response_serialization                     ok    
1661.212     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNFIX25-0003
- event_count: 53
- total_observed_ms: 8393.471
- authoritative_total_ms: 1977.954
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.031        /api/alert/analyze  scorer_readiness                           ok    
0.014        /api/alert/analyze  request_parse                              ok    
82.652       /api/alert/analyze  alert_lookup                               ok    
93.123       /api/alert/analyze  security_context_lookup                    ok    
0.23         /api/alert/analyze  category_resolution                        ok    
328.117      /api/alert/analyze  factor_vector_construction                 ok    
0.514        /api/alert/analyze  scorer_decision                            ok    
0.026        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.015        /api/alert/analyze  routing_threshold_lookup                   ok    
0.024        /api/alert/analyze  rl_exploration_proposal                    ok    
0.026        /api/alert/analyze  routing_zone_resolution                    ok    
171.26       /api/alert/analyze  referral_history_counts                    ok    
0.127        /api/alert/analyze  referral_gate_evaluation                   ok    
101.79       /api/alert/analyze  reasoning_generation                       ok    
86.463       /api/alert/analyze  decision_node_and_edge_write               ok    
94.916       /api/alert/analyze  audit_write                                ok    
0.184        /api/alert/analyze  metadata_logging_snapshot_write            ok    
92.789       /api/alert/analyze  campaign_query_find_matching_campaign      ok    
94.36        /api/alert/analyze  campaign_query_fetch_recent_events         ok    
69.809       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
75.58        /api/alert/analyze  campaign_query_create_campaign             ok    
85.604       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
97.588       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
81.197       /api/alert/analyze  campaign_query_member_edges_batch_create   error 
606.996      /api/alert/analyze  campaign_correlation_summary               ok    
690.289      /api/alert/analyze  campaign_correlation                       ok    
0.021        /api/alert/analyze  decision_event_emit                        ok    
82.385       /api/alert/analyze  composite_gate_evaluation                  ok    
0.058        /api/alert/analyze  provenance_build                           ok    
85.748       /api/alert/analyze  graph_visualization_fetch                  ok    
0.034        /api/alert/analyze  response_context_enrichment                ok    
0.05         /api/alert/analyze  referral_debug_build                       ok    
0.029        /api/alert/analyze  shadow_compare_schedule                    ok    
84.247       /api/alert/analyze  cluster_history_fetch                      ok    
0.053        /api/alert/analyze  narrative_context_build                    ok    
0.07         /api/alert/analyze  narrative_generation                       ok    
10.918       /api/alert/analyze  response_serialization                     ok    
1977.954     /api/alert/analyze  analyze_request_total                      ok    
0.02         /api/alert/outcome  request_parse                              ok    
0.019        /api/alert/outcome  duplicate_feedback_guard                   ok    
79.86        /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.301        /api/alert/outcome  outcome_audit_write                        ok    
82.5         /api/alert/outcome  learning_state_update                      ok    
463.381      /api/alert/outcome  l5_conservation_write                      ok    
465.389      /api/alert/outcome  conservation_monitor                       ok    
0.139        /api/alert/outcome  profile_scorer_update                      ok    
0.117        /api/alert/outcome  l5_dk_weight_write                         ok    
477.338      /api/alert/outcome  l5_centroid_write                          ok    
0.821        /api/alert/outcome  l5_dk_weight_write                         ok    
0.043        /api/alert/outcome  snapshot_evolution_logging                 ok    
84.608       /api/alert/outcome  snapshot_evolution_logging                 ok    
0.023        /api/alert/outcome  response_serialization                     ok    
1643.621     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNFIX25-0021
- event_count: 53
- total_observed_ms: 8437.21
- authoritative_total_ms: 1970.719
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.017        /api/alert/analyze  scorer_readiness                           ok    
0.006        /api/alert/analyze  request_parse                              ok    
73.502       /api/alert/analyze  alert_lookup                               ok    
89.516       /api/alert/analyze  security_context_lookup                    ok    
0.122        /api/alert/analyze  category_resolution                        ok    
321.744      /api/alert/analyze  factor_vector_construction                 ok    
0.163        /api/alert/analyze  scorer_decision                            ok    
0.025        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.007        /api/alert/analyze  routing_threshold_lookup                   ok    
0.011        /api/alert/analyze  rl_exploration_proposal                    ok    
0.021        /api/alert/analyze  routing_zone_resolution                    ok    
183.927      /api/alert/analyze  referral_history_counts                    ok    
0.037        /api/alert/analyze  referral_gate_evaluation                   ok    
89.741       /api/alert/analyze  reasoning_generation                       ok    
93.646       /api/alert/analyze  decision_node_and_edge_write               ok    
86.377       /api/alert/analyze  audit_write                                ok    
0.777        /api/alert/analyze  metadata_logging_snapshot_write            ok    
85.971       /api/alert/analyze  campaign_query_find_matching_campaign      ok    
102.093      /api/alert/analyze  campaign_query_fetch_recent_events         ok    
73.948       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
88.779       /api/alert/analyze  campaign_query_create_campaign             ok    
81.556       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
84.175       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
94.699       /api/alert/analyze  campaign_query_member_edges_batch_create   error 
631.285      /api/alert/analyze  campaign_correlation_summary               ok    
741.315      /api/alert/analyze  campaign_correlation                       ok    
0.041        /api/alert/analyze  decision_event_emit                        ok    
77.256       /api/alert/analyze  composite_gate_evaluation                  ok    
0.175        /api/alert/analyze  provenance_build                           ok    
81.423       /api/alert/analyze  graph_visualization_fetch                  ok    
0.043        /api/alert/analyze  response_context_enrichment                ok    
0.035        /api/alert/analyze  referral_debug_build                       ok    
0.02         /api/alert/analyze  shadow_compare_schedule                    ok    
65.103       /api/alert/analyze  cluster_history_fetch                      ok    
0.03         /api/alert/analyze  narrative_context_build                    ok    
0.04         /api/alert/analyze  narrative_generation                       ok    
2.174        /api/alert/analyze  response_serialization                     ok    
1970.719     /api/alert/analyze  analyze_request_total                      ok    
0.016        /api/alert/outcome  request_parse                              ok    
0.009        /api/alert/outcome  duplicate_feedback_guard                   ok    
107.498      /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.828        /api/alert/outcome  outcome_audit_write                        ok    
98.441       /api/alert/outcome  learning_state_update                      ok    
433.059      /api/alert/outcome  l5_conservation_write                      ok    
435.395      /api/alert/outcome  conservation_monitor                       ok    
0.153        /api/alert/outcome  profile_scorer_update                      ok    
0.342        /api/alert/outcome  l5_dk_weight_write                         ok    
464.535      /api/alert/outcome  l5_centroid_write                          ok    
0.027        /api/alert/outcome  l5_dk_weight_write                         ok    
0.028        /api/alert/outcome  snapshot_evolution_logging                 ok    
111.336      /api/alert/outcome  snapshot_evolution_logging                 ok    
0.044        /api/alert/outcome  response_serialization                     ok    
1664.98      /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNFIX25-0010
- event_count: 53
- total_observed_ms: 8175.295
- authoritative_total_ms: 1967.593
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.02         /api/alert/analyze  scorer_readiness                           ok    
0.014        /api/alert/analyze  request_parse                              ok    
99.159       /api/alert/analyze  alert_lookup                               ok    
87.211       /api/alert/analyze  security_context_lookup                    ok    
0.115        /api/alert/analyze  category_resolution                        ok    
345.994      /api/alert/analyze  factor_vector_construction                 ok    
0.302        /api/alert/analyze  scorer_decision                            ok    
0.027        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.02         /api/alert/analyze  routing_threshold_lookup                   ok    
0.027        /api/alert/analyze  rl_exploration_proposal                    ok    
0.016        /api/alert/analyze  routing_zone_resolution                    ok    
158.1        /api/alert/analyze  referral_history_counts                    ok    
0.045        /api/alert/analyze  referral_gate_evaluation                   ok    
69.494       /api/alert/analyze  reasoning_generation                       ok    
90.343       /api/alert/analyze  decision_node_and_edge_write               ok    
95.784       /api/alert/analyze  audit_write                                ok    
0.778        /api/alert/analyze  metadata_logging_snapshot_write            ok    
88.83        /api/alert/analyze  campaign_query_find_matching_campaign      ok    
76.51        /api/alert/analyze  campaign_query_fetch_recent_events         ok    
87.296       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
76.83        /api/alert/analyze  campaign_query_create_campaign             ok    
70.235       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
92.271       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
82.659       /api/alert/analyze  campaign_query_member_edges_batch_create   error 
589.526      /api/alert/analyze  campaign_correlation_summary               ok    
681.827      /api/alert/analyze  campaign_correlation                       ok    
0.036        /api/alert/analyze  decision_event_emit                        ok    
98.31        /api/alert/analyze  composite_gate_evaluation                  ok    
0.092        /api/alert/analyze  provenance_build                           ok    
98.671       /api/alert/analyze  graph_visualization_fetch                  ok    
0.022        /api/alert/analyze  response_context_enrichment                ok    
0.044        /api/alert/analyze  referral_debug_build                       ok    
0.021        /api/alert/analyze  shadow_compare_schedule                    ok    
74.389       /api/alert/analyze  cluster_history_fetch                      ok    
0.057        /api/alert/analyze  narrative_context_build                    ok    
0.334        /api/alert/analyze  narrative_generation                       ok    
5.061        /api/alert/analyze  response_serialization                     ok    
1967.593     /api/alert/analyze  analyze_request_total                      ok    
0.016        /api/alert/outcome  request_parse                              ok    
0.024        /api/alert/outcome  duplicate_feedback_guard                   ok    
94.834       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.754        /api/alert/outcome  outcome_audit_write                        ok    
102.065      /api/alert/outcome  learning_state_update                      ok    
404.825      /api/alert/outcome  l5_conservation_write                      ok    
407.712      /api/alert/outcome  conservation_monitor                       ok    
0.377        /api/alert/outcome  profile_scorer_update                      ok    
0.211        /api/alert/outcome  l5_dk_weight_write                         ok    
440.092      /api/alert/outcome  l5_centroid_write                          ok    
0.013        /api/alert/outcome  l5_dk_weight_write                         ok    
0.024        /api/alert/outcome  snapshot_evolution_logging                 ok    
78.99        /api/alert/outcome  snapshot_evolution_logging                 ok    
0.024        /api/alert/outcome  response_serialization                     ok    
1607.271     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNFIX25-0018
- event_count: 53
- total_observed_ms: 8204.048
- authoritative_total_ms: 1943.654
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.02         /api/alert/analyze  scorer_readiness                           ok    
0.009        /api/alert/analyze  request_parse                              ok    
84.259       /api/alert/analyze  alert_lookup                               ok    
72.454       /api/alert/analyze  security_context_lookup                    ok    
0.114        /api/alert/analyze  category_resolution                        ok    
333.648      /api/alert/analyze  factor_vector_construction                 ok    
0.229        /api/alert/analyze  scorer_decision                            ok    
0.022        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.016        /api/alert/analyze  routing_threshold_lookup                   ok    
0.024        /api/alert/analyze  rl_exploration_proposal                    ok    
0.025        /api/alert/analyze  routing_zone_resolution                    ok    
166.59       /api/alert/analyze  referral_history_counts                    ok    
0.034        /api/alert/analyze  referral_gate_evaluation                   ok    
69.924       /api/alert/analyze  reasoning_generation                       ok    
88.09        /api/alert/analyze  decision_node_and_edge_write               ok    
92.176       /api/alert/analyze  audit_write                                ok    
2.485        /api/alert/analyze  metadata_logging_snapshot_write            ok    
87.808       /api/alert/analyze  campaign_query_find_matching_campaign      ok    
82.661       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
84.513       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
104.148      /api/alert/analyze  campaign_query_create_campaign             ok    
81.992       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
82.076       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
69.167       /api/alert/analyze  campaign_query_member_edges_batch_create   error 
609.577      /api/alert/analyze  campaign_correlation_summary               ok    
701.232      /api/alert/analyze  campaign_correlation                       ok    
0.04         /api/alert/analyze  decision_event_emit                        ok    
84.143       /api/alert/analyze  composite_gate_evaluation                  ok    
0.177        /api/alert/analyze  provenance_build                           ok    
88.009       /api/alert/analyze  graph_visualization_fetch                  ok    
0.04         /api/alert/analyze  response_context_enrichment                ok    
0.051        /api/alert/analyze  referral_debug_build                       ok    
0.026        /api/alert/analyze  shadow_compare_schedule                    ok    
92.599       /api/alert/analyze  cluster_history_fetch                      ok    
0.106        /api/alert/analyze  narrative_context_build                    ok    
0.076        /api/alert/analyze  narrative_generation                       ok    
5.391        /api/alert/analyze  response_serialization                     ok    
1943.654     /api/alert/analyze  analyze_request_total                      ok    
0.019        /api/alert/outcome  request_parse                              ok    
0.018        /api/alert/outcome  duplicate_feedback_guard                   ok    
93.361       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.186        /api/alert/outcome  outcome_audit_write                        ok    
100.065      /api/alert/outcome  learning_state_update                      ok    
429.469      /api/alert/outcome  l5_conservation_write                      ok    
430.855      /api/alert/outcome  conservation_monitor                       ok    
0.248        /api/alert/outcome  profile_scorer_update                      ok    
0.218        /api/alert/outcome  l5_dk_weight_write                         ok    
430.212      /api/alert/outcome  l5_centroid_write                          ok    
0.028        /api/alert/outcome  l5_dk_weight_write                         ok    
0.032        /api/alert/outcome  snapshot_evolution_logging                 ok    
83.012       /api/alert/outcome  snapshot_evolution_logging                 ok    
0.022        /api/alert/outcome  response_serialization                     ok    
1608.698     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNFIX25-0004
- event_count: 53
- total_observed_ms: 8076.454
- authoritative_total_ms: 1942.687
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.019        /api/alert/analyze  scorer_readiness                           ok    
0.013        /api/alert/analyze  request_parse                              ok    
85.191       /api/alert/analyze  alert_lookup                               ok    
82.814       /api/alert/analyze  security_context_lookup                    ok    
0.227        /api/alert/analyze  category_resolution                        ok    
351.482      /api/alert/analyze  factor_vector_construction                 ok    
0.199        /api/alert/analyze  scorer_decision                            ok    
0.029        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.015        /api/alert/analyze  routing_threshold_lookup                   ok    
0.011        /api/alert/analyze  rl_exploration_proposal                    ok    
0.013        /api/alert/analyze  routing_zone_resolution                    ok    
186.148      /api/alert/analyze  referral_history_counts                    ok    
0.044        /api/alert/analyze  referral_gate_evaluation                   ok    
111.847      /api/alert/analyze  reasoning_generation                       ok    
92.013       /api/alert/analyze  decision_node_and_edge_write               ok    
82.959       /api/alert/analyze  audit_write                                ok    
0.234        /api/alert/analyze  metadata_logging_snapshot_write            ok    
80.641       /api/alert/analyze  campaign_query_find_matching_campaign      ok    
92.408       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
84.067       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
68.031       /api/alert/analyze  campaign_query_create_campaign             ok    
70.164       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
78.387       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
63.61        /api/alert/analyze  campaign_query_member_edges_batch_create   error 
549.191      /api/alert/analyze  campaign_correlation_summary               ok    
647.533      /api/alert/analyze  campaign_correlation                       ok    
0.04         /api/alert/analyze  decision_event_emit                        ok    
82.425       /api/alert/analyze  composite_gate_evaluation                  ok    
0.054        /api/alert/analyze  provenance_build                           ok    
68.172       /api/alert/analyze  graph_visualization_fetch                  ok    
0.022        /api/alert/analyze  response_context_enrichment                ok    
0.038        /api/alert/analyze  referral_debug_build                       ok    
0.013        /api/alert/analyze  shadow_compare_schedule                    ok    
96.195       /api/alert/analyze  cluster_history_fetch                      ok    
0.051        /api/alert/analyze  narrative_context_build                    ok    
0.133        /api/alert/analyze  narrative_generation                       ok    
6.77         /api/alert/analyze  response_serialization                     ok    
1942.687     /api/alert/analyze  analyze_request_total                      ok    
0.018        /api/alert/outcome  request_parse                              ok    
0.028        /api/alert/outcome  duplicate_feedback_guard                   ok    
82.184       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.194        /api/alert/outcome  outcome_audit_write                        ok    
119.937      /api/alert/outcome  learning_state_update                      ok    
417.121      /api/alert/outcome  l5_conservation_write                      ok    
419.368      /api/alert/outcome  conservation_monitor                       ok    
0.292        /api/alert/outcome  profile_scorer_update                      ok    
1.376        /api/alert/outcome  l5_dk_weight_write                         ok    
412.18       /api/alert/outcome  l5_centroid_write                          ok    
0.029        /api/alert/outcome  l5_dk_weight_write                         ok    
0.046        /api/alert/outcome  snapshot_evolution_logging                 ok    
99.153       /api/alert/outcome  snapshot_evolution_logging                 ok    
0.021        /api/alert/outcome  response_serialization                     ok    
1600.617     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNFIX25-0023
- event_count: 53
- total_observed_ms: 8166.935
- authoritative_total_ms: 1941.187
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.016        /api/alert/analyze  scorer_readiness                           ok    
0.006        /api/alert/analyze  request_parse                              ok    
81.385       /api/alert/analyze  alert_lookup                               ok    
91.0         /api/alert/analyze  security_context_lookup                    ok    
0.13         /api/alert/analyze  category_resolution                        ok    
314.341      /api/alert/analyze  factor_vector_construction                 ok    
0.166        /api/alert/analyze  scorer_decision                            ok    
0.019        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.01         /api/alert/analyze  routing_threshold_lookup                   ok    
0.024        /api/alert/analyze  rl_exploration_proposal                    ok    
0.014        /api/alert/analyze  routing_zone_resolution                    ok    
174.227      /api/alert/analyze  referral_history_counts                    ok    
0.07         /api/alert/analyze  referral_gate_evaluation                   ok    
73.488       /api/alert/analyze  reasoning_generation                       ok    
74.241       /api/alert/analyze  decision_node_and_edge_write               ok    
93.845       /api/alert/analyze  audit_write                                ok    
0.952        /api/alert/analyze  metadata_logging_snapshot_write            ok    
86.402       /api/alert/analyze  campaign_query_find_matching_campaign      ok    
89.661       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
80.031       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
89.847       /api/alert/analyze  campaign_query_create_campaign             ok    
76.276       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
106.868      /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
76.95        /api/alert/analyze  campaign_query_member_edges_batch_create   error 
623.896      /api/alert/analyze  campaign_correlation_summary               ok    
712.314      /api/alert/analyze  campaign_correlation                       ok    
0.042        /api/alert/analyze  decision_event_emit                        ok    
85.59        /api/alert/analyze  composite_gate_evaluation                  ok    
0.112        /api/alert/analyze  provenance_build                           ok    
87.16        /api/alert/analyze  graph_visualization_fetch                  ok    
0.171        /api/alert/analyze  response_context_enrichment                ok    
0.052        /api/alert/analyze  referral_debug_build                       ok    
0.025        /api/alert/analyze  shadow_compare_schedule                    ok    
87.021       /api/alert/analyze  cluster_history_fetch                      ok    
0.055        /api/alert/analyze  narrative_context_build                    ok    
0.108        /api/alert/analyze  narrative_generation                       ok    
5.222        /api/alert/analyze  response_serialization                     ok    
1941.187     /api/alert/analyze  analyze_request_total                      ok    
0.022        /api/alert/outcome  request_parse                              ok    
0.024        /api/alert/outcome  duplicate_feedback_guard                   ok    
90.603       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.426        /api/alert/outcome  outcome_audit_write                        ok    
68.206       /api/alert/outcome  learning_state_update                      ok    
416.144      /api/alert/outcome  l5_conservation_write                      ok    
418.892      /api/alert/outcome  conservation_monitor                       ok    
0.249        /api/alert/outcome  profile_scorer_update                      ok    
0.114        /api/alert/outcome  l5_dk_weight_write                         ok    
456.31       /api/alert/outcome  l5_centroid_write                          ok    
0.013        /api/alert/outcome  l5_dk_weight_write                         ok    
0.045        /api/alert/outcome  snapshot_evolution_logging                 ok    
82.262       /api/alert/outcome  snapshot_evolution_logging                 ok    
0.024        /api/alert/outcome  response_serialization                     ok    
1580.677     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNFIX25-0008
- event_count: 53
- total_observed_ms: 8067.747
- authoritative_total_ms: 1931.029
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.03         /api/alert/analyze  scorer_readiness                           ok    
0.015        /api/alert/analyze  request_parse                              ok    
94.361       /api/alert/analyze  alert_lookup                               ok    
95.537       /api/alert/analyze  security_context_lookup                    ok    
0.17         /api/alert/analyze  category_resolution                        ok    
338.529      /api/alert/analyze  factor_vector_construction                 ok    
0.3          /api/alert/analyze  scorer_decision                            ok    
0.023        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.019        /api/alert/analyze  routing_threshold_lookup                   ok    
0.02         /api/alert/analyze  rl_exploration_proposal                    ok    
0.027        /api/alert/analyze  routing_zone_resolution                    ok    
183.355      /api/alert/analyze  referral_history_counts                    ok    
0.082        /api/alert/analyze  referral_gate_evaluation                   ok    
66.834       /api/alert/analyze  reasoning_generation                       ok    
97.77        /api/alert/analyze  decision_node_and_edge_write               ok    
91.066       /api/alert/analyze  audit_write                                ok    
0.444        /api/alert/analyze  metadata_logging_snapshot_write            ok    
82.882       /api/alert/analyze  campaign_query_find_matching_campaign      ok    
75.804       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
69.534       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
86.009       /api/alert/analyze  campaign_query_create_campaign             ok    
80.137       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
76.165       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
79.331       /api/alert/analyze  campaign_query_member_edges_batch_create   error 
565.097      /api/alert/analyze  campaign_correlation_summary               ok    
644.145      /api/alert/analyze  campaign_correlation                       ok    
0.041        /api/alert/analyze  decision_event_emit                        ok    
81.004       /api/alert/analyze  composite_gate_evaluation                  ok    
0.063        /api/alert/analyze  provenance_build                           ok    
89.779       /api/alert/analyze  graph_visualization_fetch                  ok    
0.031        /api/alert/analyze  response_context_enrichment                ok    
0.055        /api/alert/analyze  referral_debug_build                       ok    
0.027        /api/alert/analyze  shadow_compare_schedule                    ok    
79.56        /api/alert/analyze  cluster_history_fetch                      ok    
0.058        /api/alert/analyze  narrative_context_build                    ok    
0.103        /api/alert/analyze  narrative_generation                       ok    
4.183        /api/alert/analyze  response_serialization                     ok    
1931.029     /api/alert/analyze  analyze_request_total                      ok    
0.026        /api/alert/outcome  request_parse                              ok    
0.019        /api/alert/outcome  duplicate_feedback_guard                   ok    
98.281       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.358        /api/alert/outcome  outcome_audit_write                        ok    
130.047      /api/alert/outcome  learning_state_update                      ok    
411.7        /api/alert/outcome  l5_conservation_write                      ok    
414.098      /api/alert/outcome  conservation_monitor                       ok    
0.138        /api/alert/outcome  profile_scorer_update                      ok    
0.288        /api/alert/outcome  l5_dk_weight_write                         ok    
434.706      /api/alert/outcome  l5_centroid_write                          ok    
0.018        /api/alert/outcome  l5_dk_weight_write                         ok    
0.018        /api/alert/outcome  snapshot_evolution_logging                 ok    
83.713       /api/alert/outcome  snapshot_evolution_logging                 ok    
0.022        /api/alert/outcome  response_serialization                     ok    
1580.696     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNFIX25-0022
- event_count: 53
- total_observed_ms: 8209.189
- authoritative_total_ms: 1920.521
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.015        /api/alert/analyze  scorer_readiness                           ok    
0.013        /api/alert/analyze  request_parse                              ok    
78.435       /api/alert/analyze  alert_lookup                               ok    
97.713       /api/alert/analyze  security_context_lookup                    ok    
0.119        /api/alert/analyze  category_resolution                        ok    
317.288      /api/alert/analyze  factor_vector_construction                 ok    
0.453        /api/alert/analyze  scorer_decision                            ok    
0.028        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.015        /api/alert/analyze  routing_threshold_lookup                   ok    
0.021        /api/alert/analyze  rl_exploration_proposal                    ok    
0.027        /api/alert/analyze  routing_zone_resolution                    ok    
168.931      /api/alert/analyze  referral_history_counts                    ok    
0.062        /api/alert/analyze  referral_gate_evaluation                   ok    
68.169       /api/alert/analyze  reasoning_generation                       ok    
100.071      /api/alert/analyze  decision_node_and_edge_write               ok    
96.249       /api/alert/analyze  audit_write                                ok    
0.502        /api/alert/analyze  metadata_logging_snapshot_write            ok    
87.114       /api/alert/analyze  campaign_query_find_matching_campaign      ok    
64.292       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
92.984       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
93.811       /api/alert/analyze  campaign_query_create_campaign             ok    
82.748       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
82.418       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
87.747       /api/alert/analyze  campaign_query_member_edges_batch_create   error 
610.092      /api/alert/analyze  campaign_correlation_summary               ok    
697.016      /api/alert/analyze  campaign_correlation                       ok    
0.04         /api/alert/analyze  decision_event_emit                        ok    
66.655       /api/alert/analyze  composite_gate_evaluation                  ok    
0.058        /api/alert/analyze  provenance_build                           ok    
77.483       /api/alert/analyze  graph_visualization_fetch                  ok    
0.026        /api/alert/analyze  response_context_enrichment                ok    
0.029        /api/alert/analyze  referral_debug_build                       ok    
0.012        /api/alert/analyze  shadow_compare_schedule                    ok    
75.483       /api/alert/analyze  cluster_history_fetch                      ok    
0.03         /api/alert/analyze  narrative_context_build                    ok    
0.038        /api/alert/analyze  narrative_generation                       ok    
2.1          /api/alert/analyze  response_serialization                     ok    
1920.521     /api/alert/analyze  analyze_request_total                      ok    
0.008        /api/alert/outcome  request_parse                              ok    
0.008        /api/alert/outcome  duplicate_feedback_guard                   ok    
73.07        /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.462        /api/alert/outcome  outcome_audit_write                        ok    
78.881       /api/alert/outcome  learning_state_update                      ok    
443.16       /api/alert/outcome  l5_conservation_write                      ok    
446.471      /api/alert/outcome  conservation_monitor                       ok    
0.264        /api/alert/outcome  profile_scorer_update                      ok    
0.208        /api/alert/outcome  l5_dk_weight_write                         ok    
469.429      /api/alert/outcome  l5_centroid_write                          ok    
0.025        /api/alert/outcome  l5_dk_weight_write                         ok    
0.034        /api/alert/outcome  snapshot_evolution_logging                 ok    
83.755       /api/alert/outcome  snapshot_evolution_logging                 ok    
0.028        /api/alert/outcome  response_serialization                     ok    
1644.578     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNFIX25-0014
- event_count: 53
- total_observed_ms: 8127.883
- authoritative_total_ms: 1912.301
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.038        /api/alert/analyze  scorer_readiness                           ok    
0.009        /api/alert/analyze  request_parse                              ok    
67.977       /api/alert/analyze  alert_lookup                               ok    
97.345       /api/alert/analyze  security_context_lookup                    ok    
0.198        /api/alert/analyze  category_resolution                        ok    
349.009      /api/alert/analyze  factor_vector_construction                 ok    
0.2          /api/alert/analyze  scorer_decision                            ok    
0.013        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.006        /api/alert/analyze  routing_threshold_lookup                   ok    
0.026        /api/alert/analyze  rl_exploration_proposal                    ok    
0.027        /api/alert/analyze  routing_zone_resolution                    ok    
156.081      /api/alert/analyze  referral_history_counts                    ok    
0.034        /api/alert/analyze  referral_gate_evaluation                   ok    
74.728       /api/alert/analyze  reasoning_generation                       ok    
93.641       /api/alert/analyze  decision_node_and_edge_write               ok    
89.872       /api/alert/analyze  audit_write                                ok    
0.789        /api/alert/analyze  metadata_logging_snapshot_write            ok    
79.352       /api/alert/analyze  campaign_query_find_matching_campaign      ok    
79.312       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
74.296       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
119.928      /api/alert/analyze  campaign_query_create_campaign             ok    
83.761       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
77.896       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
71.766       /api/alert/analyze  campaign_query_member_edges_batch_create   error 
601.164      /api/alert/analyze  campaign_correlation_summary               ok    
708.864      /api/alert/analyze  campaign_correlation                       ok    
0.023        /api/alert/analyze  decision_event_emit                        ok    
68.333       /api/alert/analyze  composite_gate_evaluation                  ok    
0.064        /api/alert/analyze  provenance_build                           ok    
75.0         /api/alert/analyze  graph_visualization_fetch                  ok    
0.027        /api/alert/analyze  response_context_enrichment                ok    
0.041        /api/alert/analyze  referral_debug_build                       ok    
0.011        /api/alert/analyze  shadow_compare_schedule                    ok    
77.551       /api/alert/analyze  cluster_history_fetch                      ok    
0.027        /api/alert/analyze  narrative_context_build                    ok    
0.039        /api/alert/analyze  narrative_generation                       ok    
2.011        /api/alert/analyze  response_serialization                     ok    
1912.301     /api/alert/analyze  analyze_request_total                      ok    
0.008        /api/alert/outcome  request_parse                              ok    
0.007        /api/alert/outcome  duplicate_feedback_guard                   ok    
86.653       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.222        /api/alert/outcome  outcome_audit_write                        ok    
76.729       /api/alert/outcome  learning_state_update                      ok    
432.299      /api/alert/outcome  l5_conservation_write                      ok    
434.946      /api/alert/outcome  conservation_monitor                       ok    
0.481        /api/alert/outcome  profile_scorer_update                      ok    
0.21         /api/alert/outcome  l5_dk_weight_write                         ok    
475.099      /api/alert/outcome  l5_centroid_write                          ok    
0.015        /api/alert/outcome  l5_dk_weight_write                         ok    
0.019        /api/alert/outcome  snapshot_evolution_logging                 ok    
77.542       /api/alert/outcome  snapshot_evolution_logging                 ok    
0.024        /api/alert/outcome  response_serialization                     ok    
1581.869     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNFIX25-0009
- event_count: 53
- total_observed_ms: 8237.323
- authoritative_total_ms: 1907.352
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.027        /api/alert/analyze  scorer_readiness                           ok    
0.013        /api/alert/analyze  request_parse                              ok    
76.451       /api/alert/analyze  alert_lookup                               ok    
77.822       /api/alert/analyze  security_context_lookup                    ok    
0.121        /api/alert/analyze  category_resolution                        ok    
292.919      /api/alert/analyze  factor_vector_construction                 ok    
0.287        /api/alert/analyze  scorer_decision                            ok    
0.021        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.015        /api/alert/analyze  routing_threshold_lookup                   ok    
0.024        /api/alert/analyze  rl_exploration_proposal                    ok    
0.024        /api/alert/analyze  routing_zone_resolution                    ok    
178.49       /api/alert/analyze  referral_history_counts                    ok    
0.041        /api/alert/analyze  referral_gate_evaluation                   ok    
84.755       /api/alert/analyze  reasoning_generation                       ok    
98.465       /api/alert/analyze  decision_node_and_edge_write               ok    
88.586       /api/alert/analyze  audit_write                                ok    
0.36         /api/alert/analyze  metadata_logging_snapshot_write            ok    
85.658       /api/alert/analyze  campaign_query_find_matching_campaign      ok    
98.945       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
82.994       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
81.149       /api/alert/analyze  campaign_query_create_campaign             ok    
99.021       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
71.246       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
77.207       /api/alert/analyze  campaign_query_member_edges_batch_create   error 
609.533      /api/alert/analyze  campaign_correlation_summary               ok    
695.694      /api/alert/analyze  campaign_correlation                       ok    
0.021        /api/alert/analyze  decision_event_emit                        ok    
93.577       /api/alert/analyze  composite_gate_evaluation                  ok    
0.231        /api/alert/analyze  provenance_build                           ok    
75.191       /api/alert/analyze  graph_visualization_fetch                  ok    
0.026        /api/alert/analyze  response_context_enrichment                ok    
0.027        /api/alert/analyze  referral_debug_build                       ok    
0.013        /api/alert/analyze  shadow_compare_schedule                    ok    
84.859       /api/alert/analyze  cluster_history_fetch                      ok    
0.079        /api/alert/analyze  narrative_context_build                    ok    
0.047        /api/alert/analyze  narrative_generation                       ok    
4.78         /api/alert/analyze  response_serialization                     ok    
1907.352     /api/alert/analyze  analyze_request_total                      ok    
0.016        /api/alert/outcome  request_parse                              ok    
0.018        /api/alert/outcome  duplicate_feedback_guard                   ok    
101.255      /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.197        /api/alert/outcome  outcome_audit_write                        ok    
70.35        /api/alert/outcome  learning_state_update                      ok    
450.937      /api/alert/outcome  l5_conservation_write                      ok    
455.444      /api/alert/outcome  conservation_monitor                       ok    
0.258        /api/alert/outcome  profile_scorer_update                      ok    
0.219        /api/alert/outcome  l5_dk_weight_write                         ok    
463.447      /api/alert/outcome  l5_centroid_write                          ok    
0.03         /api/alert/outcome  l5_dk_weight_write                         ok    
0.036        /api/alert/outcome  snapshot_evolution_logging                 ok    
78.25        /api/alert/outcome  snapshot_evolution_logging                 ok    
0.042        /api/alert/outcome  response_serialization                     ok    
1650.753     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNFIX25-0015
- event_count: 53
- total_observed_ms: 7944.941
- authoritative_total_ms: 1899.091
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.017        /api/alert/analyze  scorer_readiness                           ok    
0.006        /api/alert/analyze  request_parse                              ok    
67.573       /api/alert/analyze  alert_lookup                               ok    
113.738      /api/alert/analyze  security_context_lookup                    ok    
0.123        /api/alert/analyze  category_resolution                        ok    
338.369      /api/alert/analyze  factor_vector_construction                 ok    
0.34         /api/alert/analyze  scorer_decision                            ok    
0.018        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.019        /api/alert/analyze  routing_threshold_lookup                   ok    
2.167        /api/alert/analyze  rl_exploration_proposal                    ok    
0.017        /api/alert/analyze  routing_zone_resolution                    ok    
171.161      /api/alert/analyze  referral_history_counts                    ok    
0.037        /api/alert/analyze  referral_gate_evaluation                   ok    
70.426       /api/alert/analyze  reasoning_generation                       ok    
79.444       /api/alert/analyze  decision_node_and_edge_write               ok    
88.57        /api/alert/analyze  audit_write                                ok    
0.487        /api/alert/analyze  metadata_logging_snapshot_write            ok    
84.376       /api/alert/analyze  campaign_query_find_matching_campaign      ok    
76.67        /api/alert/analyze  campaign_query_fetch_recent_events         ok    
91.113       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
97.49        /api/alert/analyze  campaign_query_create_campaign             ok    
77.453       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
74.527       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
69.814       /api/alert/analyze  campaign_query_member_edges_batch_create   error 
586.722      /api/alert/analyze  campaign_correlation_summary               ok    
658.926      /api/alert/analyze  campaign_correlation                       ok    
0.022        /api/alert/analyze  decision_event_emit                        ok    
83.069       /api/alert/analyze  composite_gate_evaluation                  ok    
0.053        /api/alert/analyze  provenance_build                           ok    
85.897       /api/alert/analyze  graph_visualization_fetch                  ok    
0.059        /api/alert/analyze  response_context_enrichment                ok    
0.037        /api/alert/analyze  referral_debug_build                       ok    
0.013        /api/alert/analyze  shadow_compare_schedule                    ok    
78.641       /api/alert/analyze  cluster_history_fetch                      ok    
0.029        /api/alert/analyze  narrative_context_build                    ok    
0.04         /api/alert/analyze  narrative_generation                       ok    
1.899        /api/alert/analyze  response_serialization                     ok    
1899.091     /api/alert/analyze  analyze_request_total                      ok    
0.008        /api/alert/outcome  request_parse                              ok    
0.008        /api/alert/outcome  duplicate_feedback_guard                   ok    
88.186       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.198        /api/alert/outcome  outcome_audit_write                        ok    
76.127       /api/alert/outcome  learning_state_update                      ok    
396.528      /api/alert/outcome  l5_conservation_write                      ok    
399.334      /api/alert/outcome  conservation_monitor                       ok    
0.354        /api/alert/outcome  profile_scorer_update                      ok    
0.105        /api/alert/outcome  l5_dk_weight_write                         ok    
430.989      /api/alert/outcome  l5_centroid_write                          ok    
0.012        /api/alert/outcome  l5_dk_weight_write                         ok    
0.028        /api/alert/outcome  snapshot_evolution_logging                 ok    
93.573       /api/alert/outcome  snapshot_evolution_logging                 ok    
0.02         /api/alert/outcome  response_serialization                     ok    
1561.018     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNFIX25-0006
- event_count: 53
- total_observed_ms: 8135.713
- authoritative_total_ms: 1892.207
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.014        /api/alert/analyze  scorer_readiness                           ok    
0.006        /api/alert/analyze  request_parse                              ok    
75.022       /api/alert/analyze  alert_lookup                               ok    
99.226       /api/alert/analyze  security_context_lookup                    ok    
0.123        /api/alert/analyze  category_resolution                        ok    
323.717      /api/alert/analyze  factor_vector_construction                 ok    
0.177        /api/alert/analyze  scorer_decision                            ok    
0.016        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.007        /api/alert/analyze  routing_threshold_lookup                   ok    
0.01         /api/alert/analyze  rl_exploration_proposal                    ok    
0.013        /api/alert/analyze  routing_zone_resolution                    ok    
178.876      /api/alert/analyze  referral_history_counts                    ok    
0.071        /api/alert/analyze  referral_gate_evaluation                   ok    
96.636       /api/alert/analyze  reasoning_generation                       ok    
76.125       /api/alert/analyze  decision_node_and_edge_write               ok    
87.664       /api/alert/analyze  audit_write                                ok    
0.355        /api/alert/analyze  metadata_logging_snapshot_write            ok    
76.379       /api/alert/analyze  campaign_query_find_matching_campaign      ok    
70.082       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
89.531       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
90.775       /api/alert/analyze  campaign_query_create_campaign             ok    
80.057       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
78.645       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
81.998       /api/alert/analyze  campaign_query_member_edges_batch_create   error 
579.073      /api/alert/analyze  campaign_correlation_summary               ok    
656.672      /api/alert/analyze  campaign_correlation                       ok    
0.021        /api/alert/analyze  decision_event_emit                        ok    
72.904       /api/alert/analyze  composite_gate_evaluation                  ok    
0.052        /api/alert/analyze  provenance_build                           ok    
85.345       /api/alert/analyze  graph_visualization_fetch                  ok    
0.044        /api/alert/analyze  response_context_enrichment                ok    
0.056        /api/alert/analyze  referral_debug_build                       ok    
0.026        /api/alert/analyze  shadow_compare_schedule                    ok    
84.443       /api/alert/analyze  cluster_history_fetch                      ok    
0.059        /api/alert/analyze  narrative_context_build                    ok    
0.089        /api/alert/analyze  narrative_generation                       ok    
5.559        /api/alert/analyze  response_serialization                     ok    
1892.207     /api/alert/analyze  analyze_request_total                      ok    
0.019        /api/alert/outcome  request_parse                              ok    
0.021        /api/alert/outcome  duplicate_feedback_guard                   ok    
93.098       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.444        /api/alert/outcome  outcome_audit_write                        ok    
128.238      /api/alert/outcome  learning_state_update                      ok    
439.328      /api/alert/outcome  l5_conservation_write                      ok    
441.403      /api/alert/outcome  conservation_monitor                       ok    
0.135        /api/alert/outcome  profile_scorer_update                      ok    
0.136        /api/alert/outcome  l5_dk_weight_write                         ok    
447.882      /api/alert/outcome  l5_centroid_write                          ok    
0.017        /api/alert/outcome  l5_dk_weight_write                         ok    
0.048        /api/alert/outcome  snapshot_evolution_logging                 ok    
85.256       /api/alert/outcome  snapshot_evolution_logging                 ok    
0.029        /api/alert/outcome  response_serialization                     ok    
1617.584     /api/alert/outcome  outcome_request_total                      ok    
```

## Nested Phase Warning
Nested phase durations should not be summed blindly. Use analyze_request_total, outcome_request_total, or total_attempt as authoritative totals.
