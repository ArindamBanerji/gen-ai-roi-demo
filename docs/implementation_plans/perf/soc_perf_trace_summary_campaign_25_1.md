# SOC Perf Trace Summary

## Safety
- Read-only summary of existing JSONL trace events.
- No backend, graph, proof, or seed operations are performed.
- Nested phases are not additive; request-total phases are the authoritative route totals.

## Input
- trace_jsonl: `C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50\scratch\temp\soc_perf_trace_campaign_25_1.jsonl`
- events_loaded: 1896
- malformed_lines: 0
- route_filter: None
- phase_filter: None

## Route + Phase Aggregates
```text
route_phase                                                 count  avg_ms    p50_ms    p95_ms    p99_ms    max_ms  
----------------------------------------------------------  -----  --------  --------  --------  --------  --------
/api/alert/analyze | analyze_request_total                  25     3831.923  3771.091  5851.146  5983.912  5999.716
/api/alert/analyze | campaign_correlation                   25     2608.661  2599.312  4651.159  4775.79   4781.637
/api/alert/analyze | campaign_correlation_summary           25     2526.695  2507.878  4567.974  4674.559  4674.777
/api/alert/outcome | outcome_request_total                  25     1575.812  1568.301  1732.556  1871.114  1912.781
/api/alert/outcome | l5_centroid_write                      25     415.968   423.404   468.093   475.782   477.696 
/api/alert/outcome | conservation_monitor                   25     412.864   411.245   472.491   476.352   476.377 
/api/alert/outcome | l5_conservation_write                  25     410.701   409.162   469.029   474.141   474.647 
/api/alert/outcome | learning_state_update                  25     131.082   122.692   203.521   402.237   463.733 
/api/alert/analyze | campaign_query_member_edge_create      324    85.634    83.121    102.508   161.966   463.142 
/api/alert/analyze | reasoning_generation                   25     94.662    79.531    106.655   319.024   386.016 
/api/alert/analyze | factor_vector_construction             25     324.767   315.939   356.976   373.78    378.784 
/api/alert/outcome | decision_lookup_and_outcome_update     25     95.914    81.031    186.046   281.028   304.312 
/api/alert/analyze | referral_history_counts                25     167.367   165.239   206.85    210.679   210.718 
/api/alert/analyze | cluster_history_fetch                  25     79.188    76.272    98.101    109.483   112.783 
/api/alert/analyze | campaign_query_member_edge_check       324    80.306    79.934    98.043    107.569   111.789 
/api/alert/analyze | security_context_lookup                25     82.586    82.638    97.132    107.802   111.151 
/api/alert/analyze | audit_write                            25     87.626    89.633    99.454    107.715   110.154 
/api/alert/analyze | campaign_query_create_campaign         24     83.677    86.095    97.331    103.625   105.467 
/api/alert/analyze | decision_node_and_edge_write           25     87.942    89.151    101.247   104.43    105.364 
/api/alert/analyze | graph_visualization_fetch              25     82.269    82.84     95.895    102.459   104.488 
/api/alert/outcome | snapshot_evolution_logging             50     43.794    67.233    99.167    102.113   103.555 
/api/alert/analyze | alert_lookup                           25     79.744    80.009    92.614    100.403   102.757 
/api/alert/analyze | campaign_query_check_campaign_exists   24     78.522    80.021    91.205    97.441    99.263  
/api/alert/analyze | composite_gate_evaluation              25     78.022    78.113    92.693    95.487    96.111  
/api/alert/analyze | campaign_query_fetch_recent_events     25     78.46     79.806    90.221    93.188    93.964  
/api/alert/analyze | campaign_query_find_matching_campaign  25     81.812    82.992    91.539    91.843    91.929  
/api/alert/analyze | response_serialization                 25     4.133     3.222     11.044    14.602    15.388  
/api/alert/analyze | metadata_logging_snapshot_write        25     0.796     0.311     2.812     6.872     8.046   
/api/alert/analyze | post_scorer_confidence_gate            25     0.232     0.016     0.039     4.065     5.336   
/api/alert/outcome | outcome_audit_write                    25     0.613     0.45      1.483     2.531     2.851   
/api/alert/analyze | category_resolution                    25     0.258     0.147     0.284     1.979     2.512   
/api/alert/outcome | l5_dk_weight_write                     50     0.131     0.097     0.436     0.79      1.099   
/api/alert/analyze | scorer_decision                        25     0.316     0.223     0.715     0.959     1.022   
/api/alert/outcome | profile_scorer_update                  25     0.254     0.248     0.537     0.582     0.585   
/api/alert/analyze | narrative_generation                   25     0.082     0.059     0.173     0.339     0.389   
/api/alert/analyze | provenance_build                       25     0.087     0.064     0.175     0.321     0.362   
/api/alert/outcome | duplicate_feedback_guard               25     0.027     0.01      0.037     0.266     0.338   
/api/alert/analyze | scorer_readiness                       25     0.033     0.019     0.035     0.251     0.319   
/api/alert/analyze | referral_gate_evaluation               25     0.057     0.048     0.093     0.103     0.105   
/api/alert/outcome | response_serialization                 25     0.033     0.026     0.062     0.089     0.098   
```

## Phase Aggregates
```text
phase                                  count  avg_ms    p50_ms    p95_ms    p99_ms    max_ms  
-------------------------------------  -----  --------  --------  --------  --------  --------
analyze_request_total                  25     3831.923  3771.091  5851.146  5983.912  5999.716
campaign_correlation                   25     2608.661  2599.312  4651.159  4775.79   4781.637
campaign_correlation_summary           25     2526.695  2507.878  4567.974  4674.559  4674.777
outcome_request_total                  25     1575.812  1568.301  1732.556  1871.114  1912.781
l5_centroid_write                      25     415.968   423.404   468.093   475.782   477.696 
conservation_monitor                   25     412.864   411.245   472.491   476.352   476.377 
l5_conservation_write                  25     410.701   409.162   469.029   474.141   474.647 
learning_state_update                  25     131.082   122.692   203.521   402.237   463.733 
campaign_query_member_edge_create      324    85.634    83.121    102.508   161.966   463.142 
reasoning_generation                   25     94.662    79.531    106.655   319.024   386.016 
factor_vector_construction             25     324.767   315.939   356.976   373.78    378.784 
decision_lookup_and_outcome_update     25     95.914    81.031    186.046   281.028   304.312 
referral_history_counts                25     167.367   165.239   206.85    210.679   210.718 
cluster_history_fetch                  25     79.188    76.272    98.101    109.483   112.783 
campaign_query_member_edge_check       324    80.306    79.934    98.043    107.569   111.789 
security_context_lookup                25     82.586    82.638    97.132    107.802   111.151 
audit_write                            25     87.626    89.633    99.454    107.715   110.154 
campaign_query_create_campaign         24     83.677    86.095    97.331    103.625   105.467 
decision_node_and_edge_write           25     87.942    89.151    101.247   104.43    105.364 
graph_visualization_fetch              25     82.269    82.84     95.895    102.459   104.488 
snapshot_evolution_logging             50     43.794    67.233    99.167    102.113   103.555 
alert_lookup                           25     79.744    80.009    92.614    100.403   102.757 
campaign_query_check_campaign_exists   24     78.522    80.021    91.205    97.441    99.263  
composite_gate_evaluation              25     78.022    78.113    92.693    95.487    96.111  
campaign_query_fetch_recent_events     25     78.46     79.806    90.221    93.188    93.964  
campaign_query_find_matching_campaign  25     81.812    82.992    91.539    91.843    91.929  
response_serialization                 50     2.083     1.022     6.411     13.783    15.388  
metadata_logging_snapshot_write        25     0.796     0.311     2.812     6.872     8.046   
post_scorer_confidence_gate            25     0.232     0.016     0.039     4.065     5.336   
outcome_audit_write                    25     0.613     0.45      1.483     2.531     2.851   
category_resolution                    25     0.258     0.147     0.284     1.979     2.512   
l5_dk_weight_write                     50     0.131     0.097     0.436     0.79      1.099   
scorer_decision                        25     0.316     0.223     0.715     0.959     1.022   
profile_scorer_update                  25     0.254     0.248     0.537     0.582     0.585   
narrative_generation                   25     0.082     0.059     0.173     0.339     0.389   
provenance_build                       25     0.087     0.064     0.175     0.321     0.362   
duplicate_feedback_guard               25     0.027     0.01      0.037     0.266     0.338   
scorer_readiness                       25     0.033     0.019     0.035     0.251     0.319   
referral_gate_evaluation               25     0.057     0.048     0.093     0.103     0.105   
narrative_context_build                25     0.043     0.035     0.067     0.081     0.086   
```

## Graph Aggregates
```text
graph_name               count  avg_ms   p50_ms  p95_ms   p99_ms    max_ms  
-----------------------  -----  -------  ------  -------  --------  --------
soc_graph_campaign_25_1  1896   207.481  75.35   869.872  4097.391  5999.716
```

## Top Slow Events
```text
duration_ms  route               phase                         alert_id          decision_id                           attempt_index  status
-----------  ------------------  ----------------------------  ----------------  ------------------------------------  -------------  ------
5999.716     /api/alert/analyze  analyze_request_total         CAMPAIGN25A-0025  4dbc996b-c6d4-4590-acfd-cc5980045b9f  None           ok    
5933.866     /api/alert/analyze  analyze_request_total         CAMPAIGN25A-0023  3a74f824-6853-4d6e-a32f-6e8f2dcd0b00  None           ok    
5520.265     /api/alert/analyze  analyze_request_total         CAMPAIGN25A-0021  8b23f766-0493-4a61-870e-f67ce4ea7a86  None           ok    
5433.81      /api/alert/analyze  analyze_request_total         CAMPAIGN25A-0022  76d9ab9b-c8df-4c49-8503-e9bc6680d3b5  None           ok    
5379.588     /api/alert/analyze  analyze_request_total         CAMPAIGN25A-0024  59062d63-4601-47bb-8b58-d7934e24d03d  None           ok    
5004.175     /api/alert/analyze  analyze_request_total         CAMPAIGN25A-0019  5ed88dc7-535e-4e17-8b44-fa7c29682a89  None           ok    
4820.304     /api/alert/analyze  analyze_request_total         CAMPAIGN25A-0020  65a0087a-ff59-44a2-8a91-99498feb8359  None           ok    
4781.637     /api/alert/analyze  campaign_correlation          CAMPAIGN25A-0025  4dbc996b-c6d4-4590-acfd-cc5980045b9f  None           ok    
4757.273     /api/alert/analyze  campaign_correlation          CAMPAIGN25A-0023  3a74f824-6853-4d6e-a32f-6e8f2dcd0b00  None           ok    
4674.777     /api/alert/analyze  campaign_correlation_summary  CAMPAIGN25A-0023  None                                  None           ok    
4673.87      /api/alert/analyze  campaign_correlation_summary  CAMPAIGN25A-0025  None                                  None           ok    
4655.852     /api/alert/analyze  analyze_request_total         CAMPAIGN25A-0018  caa40ad5-4166-40bd-b7d9-04964ea47dc7  None           ok    
4503.944     /api/alert/analyze  analyze_request_total         CAMPAIGN25A-0016  164d6e9d-381a-453d-af6b-134c25a1245b  None           ok    
4388.699     /api/alert/analyze  analyze_request_total         CAMPAIGN25A-0017  eb2fe29a-1ad1-40f1-9ccf-3b1aca14c7c9  None           ok    
4226.705     /api/alert/analyze  campaign_correlation          CAMPAIGN25A-0022  76d9ab9b-c8df-4c49-8503-e9bc6680d3b5  None           ok    
4223.555     /api/alert/analyze  campaign_correlation          CAMPAIGN25A-0021  8b23f766-0493-4a61-870e-f67ce4ea7a86  None           ok    
4144.388     /api/alert/analyze  campaign_correlation_summary  CAMPAIGN25A-0022  None                                  None           ok    
4135.163     /api/alert/analyze  campaign_correlation          CAMPAIGN25A-0024  59062d63-4601-47bb-8b58-d7934e24d03d  None           ok    
4134.407     /api/alert/analyze  campaign_correlation_summary  CAMPAIGN25A-0021  None                                  None           ok    
4095.443     /api/alert/analyze  analyze_request_total         CAMPAIGN25A-0015  59eaefdf-c37c-4b5f-b6fa-f103f281568d  None           ok    
```

## Early/Mid/Late Windows
```text
(none)
```

## Per-Alert Waterfall

### CAMPAIGN25A-0025
- event_count: 100
- total_observed_ms: 24169.33
- authoritative_total_ms: 5999.716
```text
duration_ms  route               phase                                  status
-----------  ------------------  -------------------------------------  ------
0.018        /api/alert/analyze  scorer_readiness                       ok    
0.011        /api/alert/analyze  request_parse                          ok    
81.283       /api/alert/analyze  alert_lookup                           ok    
94.424       /api/alert/analyze  security_context_lookup                ok    
0.147        /api/alert/analyze  category_resolution                    ok    
315.215      /api/alert/analyze  factor_vector_construction             ok    
0.207        /api/alert/analyze  scorer_decision                        ok    
0.02         /api/alert/analyze  post_scorer_confidence_gate            ok    
0.012        /api/alert/analyze  routing_threshold_lookup               ok    
0.017        /api/alert/analyze  rl_exploration_proposal                ok    
0.013        /api/alert/analyze  routing_zone_resolution                ok    
159.745      /api/alert/analyze  referral_history_counts                ok    
0.045        /api/alert/analyze  referral_gate_evaluation               ok    
82.67        /api/alert/analyze  reasoning_generation                   ok    
93.274       /api/alert/analyze  decision_node_and_edge_write           ok    
97.308       /api/alert/analyze  audit_write                            ok    
0.341        /api/alert/analyze  metadata_logging_snapshot_write        ok    
68.557       /api/alert/analyze  campaign_query_find_matching_campaign  ok    
71.747       /api/alert/analyze  campaign_query_fetch_recent_events     ok    
80.6         /api/alert/analyze  campaign_query_check_campaign_exists   ok    
88.936       /api/alert/analyze  campaign_query_create_campaign         ok    
63.629       /api/alert/analyze  campaign_query_member_edge_check       ok    
66.029       /api/alert/analyze  campaign_query_member_edge_create      ok    
86.872       /api/alert/analyze  campaign_query_member_edge_check       ok    
76.832       /api/alert/analyze  campaign_query_member_edge_create      ok    
97.0         /api/alert/analyze  campaign_query_member_edge_check       ok    
86.693       /api/alert/analyze  campaign_query_member_edge_create      ok    
84.932       /api/alert/analyze  campaign_query_member_edge_check       ok    
69.403       /api/alert/analyze  campaign_query_member_edge_create      ok    
65.385       /api/alert/analyze  campaign_query_member_edge_check       ok    
91.178       /api/alert/analyze  campaign_query_member_edge_create      ok    
71.099       /api/alert/analyze  campaign_query_member_edge_check       ok    
71.316       /api/alert/analyze  campaign_query_member_edge_create      ok    
75.92        /api/alert/analyze  campaign_query_member_edge_check       ok    
339.612      /api/alert/analyze  campaign_query_member_edge_create      ok    
92.073       /api/alert/analyze  campaign_query_member_edge_check       ok    
87.973       /api/alert/analyze  campaign_query_member_edge_create      ok    
79.952       /api/alert/analyze  campaign_query_member_edge_check       ok    
68.804       /api/alert/analyze  campaign_query_member_edge_create      ok    
87.226       /api/alert/analyze  campaign_query_member_edge_check       ok    
82.469       /api/alert/analyze  campaign_query_member_edge_create      ok    
84.96        /api/alert/analyze  campaign_query_member_edge_check       ok    
95.892       /api/alert/analyze  campaign_query_member_edge_create      ok    
64.177       /api/alert/analyze  campaign_query_member_edge_check       ok    
76.223       /api/alert/analyze  campaign_query_member_edge_create      ok    
67.036       /api/alert/analyze  campaign_query_member_edge_check       ok    
86.89        /api/alert/analyze  campaign_query_member_edge_create      ok    
73.762       /api/alert/analyze  campaign_query_member_edge_check       ok    
83.443       /api/alert/analyze  campaign_query_member_edge_create      ok    
75.569       /api/alert/analyze  campaign_query_member_edge_check       ok    
113.618      /api/alert/analyze  campaign_query_member_edge_create      ok    
73.782       /api/alert/analyze  campaign_query_member_edge_check       ok    
81.586       /api/alert/analyze  campaign_query_member_edge_create      ok    
108.032      /api/alert/analyze  campaign_query_member_edge_check       ok    
103.566      /api/alert/analyze  campaign_query_member_edge_create      ok    
86.622       /api/alert/analyze  campaign_query_member_edge_check       ok    
77.252       /api/alert/analyze  campaign_query_member_edge_create      ok    
63.718       /api/alert/analyze  campaign_query_member_edge_check       ok    
62.516       /api/alert/analyze  campaign_query_member_edge_create      ok    
84.615       /api/alert/analyze  campaign_query_member_edge_check       ok    
75.325       /api/alert/analyze  campaign_query_member_edge_create      ok    
63.829       /api/alert/analyze  campaign_query_member_edge_check       ok    
80.411       /api/alert/analyze  campaign_query_member_edge_create      ok    
85.007       /api/alert/analyze  campaign_query_member_edge_check       ok    
83.483       /api/alert/analyze  campaign_query_member_edge_create      ok    
82.935       /api/alert/analyze  campaign_query_member_edge_check       ok    
83.476       /api/alert/analyze  campaign_query_member_edge_create      ok    
89.562       /api/alert/analyze  campaign_query_member_edge_check       ok    
66.043       /api/alert/analyze  campaign_query_member_edge_create      ok    
60.63        /api/alert/analyze  campaign_query_member_edge_check       ok    
87.534       /api/alert/analyze  campaign_query_member_edge_create      ok    
4673.87      /api/alert/analyze  campaign_correlation_summary           ok    
4781.637     /api/alert/analyze  campaign_correlation                   ok    
0.044        /api/alert/analyze  decision_event_emit                    ok    
74.977       /api/alert/analyze  composite_gate_evaluation              ok    
0.055        /api/alert/analyze  provenance_build                       ok    
87.519       /api/alert/analyze  graph_visualization_fetch              ok    
0.048        /api/alert/analyze  response_context_enrichment            ok    
0.061        /api/alert/analyze  referral_debug_build                   ok    
0.016        /api/alert/analyze  shadow_compare_schedule                ok    
80.684       /api/alert/analyze  cluster_history_fetch                  ok    
0.03         /api/alert/analyze  narrative_context_build                ok    
0.068        /api/alert/analyze  narrative_generation                   ok    
2.285        /api/alert/analyze  response_serialization                 ok    
5999.716     /api/alert/analyze  analyze_request_total                  ok    
0.011        /api/alert/outcome  request_parse                          ok    
0.012        /api/alert/outcome  duplicate_feedback_guard               ok    
83.082       /api/alert/outcome  decision_lookup_and_outcome_update     ok    
0.586        /api/alert/outcome  outcome_audit_write                    ok    
75.349       /api/alert/outcome  learning_state_update                  ok    
431.272      /api/alert/outcome  l5_conservation_write                  ok    
434.841      /api/alert/outcome  conservation_monitor                   ok    
0.314        /api/alert/outcome  profile_scorer_update                  ok    
0.229        /api/alert/outcome  l5_dk_weight_write                     ok    
387.874      /api/alert/outcome  l5_centroid_write                      ok    
0.014        /api/alert/outcome  l5_dk_weight_write                     ok    
0.017        /api/alert/outcome  snapshot_evolution_logging             ok    
69.144       /api/alert/outcome  snapshot_evolution_logging             ok    
0.021        /api/alert/outcome  response_serialization                 ok    
1485.073     /api/alert/outcome  outcome_request_total                  ok    
```

### CAMPAIGN25A-0023
- event_count: 96
- total_observed_ms: 24129.634
- authoritative_total_ms: 5933.866
```text
duration_ms  route               phase                                  status
-----------  ------------------  -------------------------------------  ------
0.035        /api/alert/analyze  scorer_readiness                       ok    
0.007        /api/alert/analyze  request_parse                          ok    
83.31        /api/alert/analyze  alert_lookup                           ok    
85.55        /api/alert/analyze  security_context_lookup                ok    
0.29         /api/alert/analyze  category_resolution                    ok    
315.019      /api/alert/analyze  factor_vector_construction             ok    
0.218        /api/alert/analyze  scorer_decision                        ok    
0.033        /api/alert/analyze  post_scorer_confidence_gate            ok    
0.008        /api/alert/analyze  routing_threshold_lookup               ok    
0.021        /api/alert/analyze  rl_exploration_proposal                ok    
0.04         /api/alert/analyze  routing_zone_resolution                ok    
167.899      /api/alert/analyze  referral_history_counts                ok    
0.05         /api/alert/analyze  referral_gate_evaluation               ok    
76.332       /api/alert/analyze  reasoning_generation                   ok    
88.891       /api/alert/analyze  decision_node_and_edge_write           ok    
73.916       /api/alert/analyze  audit_write                            ok    
0.264        /api/alert/analyze  metadata_logging_snapshot_write        ok    
85.765       /api/alert/analyze  campaign_query_find_matching_campaign  ok    
79.823       /api/alert/analyze  campaign_query_fetch_recent_events     ok    
91.34        /api/alert/analyze  campaign_query_check_campaign_exists   ok    
73.001       /api/alert/analyze  campaign_query_create_campaign         ok    
80.457       /api/alert/analyze  campaign_query_member_edge_check       ok    
75.647       /api/alert/analyze  campaign_query_member_edge_create      ok    
85.185       /api/alert/analyze  campaign_query_member_edge_check       ok    
79.599       /api/alert/analyze  campaign_query_member_edge_create      ok    
74.352       /api/alert/analyze  campaign_query_member_edge_check       ok    
96.376       /api/alert/analyze  campaign_query_member_edge_create      ok    
72.567       /api/alert/analyze  campaign_query_member_edge_check       ok    
78.967       /api/alert/analyze  campaign_query_member_edge_create      ok    
68.842       /api/alert/analyze  campaign_query_member_edge_check       ok    
91.0         /api/alert/analyze  campaign_query_member_edge_create      ok    
68.339       /api/alert/analyze  campaign_query_member_edge_check       ok    
82.813       /api/alert/analyze  campaign_query_member_edge_create      ok    
81.589       /api/alert/analyze  campaign_query_member_edge_check       ok    
90.677       /api/alert/analyze  campaign_query_member_edge_create      ok    
77.219       /api/alert/analyze  campaign_query_member_edge_check       ok    
70.617       /api/alert/analyze  campaign_query_member_edge_create      ok    
96.695       /api/alert/analyze  campaign_query_member_edge_check       ok    
96.994       /api/alert/analyze  campaign_query_member_edge_create      ok    
77.234       /api/alert/analyze  campaign_query_member_edge_check       ok    
463.142      /api/alert/analyze  campaign_query_member_edge_create      ok    
75.062       /api/alert/analyze  campaign_query_member_edge_check       ok    
196.344      /api/alert/analyze  campaign_query_member_edge_create      ok    
83.172       /api/alert/analyze  campaign_query_member_edge_check       ok    
73.767       /api/alert/analyze  campaign_query_member_edge_create      ok    
76.524       /api/alert/analyze  campaign_query_member_edge_check       ok    
63.627       /api/alert/analyze  campaign_query_member_edge_create      ok    
83.859       /api/alert/analyze  campaign_query_member_edge_check       ok    
92.194       /api/alert/analyze  campaign_query_member_edge_create      ok    
88.323       /api/alert/analyze  campaign_query_member_edge_check       ok    
65.064       /api/alert/analyze  campaign_query_member_edge_create      ok    
65.202       /api/alert/analyze  campaign_query_member_edge_check       ok    
102.546      /api/alert/analyze  campaign_query_member_edge_create      ok    
81.761       /api/alert/analyze  campaign_query_member_edge_check       ok    
91.541       /api/alert/analyze  campaign_query_member_edge_create      ok    
65.487       /api/alert/analyze  campaign_query_member_edge_check       ok    
100.35       /api/alert/analyze  campaign_query_member_edge_create      ok    
88.487       /api/alert/analyze  campaign_query_member_edge_check       ok    
90.78        /api/alert/analyze  campaign_query_member_edge_create      ok    
91.569       /api/alert/analyze  campaign_query_member_edge_check       ok    
80.157       /api/alert/analyze  campaign_query_member_edge_create      ok    
83.93        /api/alert/analyze  campaign_query_member_edge_check       ok    
86.873       /api/alert/analyze  campaign_query_member_edge_create      ok    
76.453       /api/alert/analyze  campaign_query_member_edge_check       ok    
90.381       /api/alert/analyze  campaign_query_member_edge_create      ok    
70.977       /api/alert/analyze  campaign_query_member_edge_check       ok    
68.735       /api/alert/analyze  campaign_query_member_edge_create      ok    
4674.777     /api/alert/analyze  campaign_correlation_summary           ok    
4757.273     /api/alert/analyze  campaign_correlation                   ok    
0.021        /api/alert/analyze  decision_event_emit                    ok    
77.23        /api/alert/analyze  composite_gate_evaluation              ok    
0.061        /api/alert/analyze  provenance_build                       ok    
88.221       /api/alert/analyze  graph_visualization_fetch              ok    
0.023        /api/alert/analyze  response_context_enrichment            ok    
0.032        /api/alert/analyze  referral_debug_build                   ok    
0.012        /api/alert/analyze  shadow_compare_schedule                ok    
66.458       /api/alert/analyze  cluster_history_fetch                  ok    
0.029        /api/alert/analyze  narrative_context_build                ok    
0.389        /api/alert/analyze  narrative_generation                   ok    
2.3          /api/alert/analyze  response_serialization                 ok    
5933.866     /api/alert/analyze  analyze_request_total                  ok    
0.008        /api/alert/outcome  request_parse                          ok    
0.01         /api/alert/outcome  duplicate_feedback_guard               ok    
76.908       /api/alert/outcome  decision_lookup_and_outcome_update     ok    
0.313        /api/alert/outcome  outcome_audit_write                    ok    
75.114       /api/alert/outcome  learning_state_update                  ok    
425.392      /api/alert/outcome  l5_conservation_write                  ok    
428.012      /api/alert/outcome  conservation_monitor                   ok    
0.389        /api/alert/outcome  profile_scorer_update                  ok    
0.108        /api/alert/outcome  l5_dk_weight_write                     ok    
417.256      /api/alert/outcome  l5_centroid_write                      ok    
0.032        /api/alert/outcome  l5_dk_weight_write                     ok    
0.026        /api/alert/outcome  snapshot_evolution_logging             ok    
90.965       /api/alert/outcome  snapshot_evolution_logging             ok    
0.06         /api/alert/outcome  response_serialization                 ok    
1551.061     /api/alert/outcome  outcome_request_total                  ok    
```

### CAMPAIGN25A-0021
- event_count: 92
- total_observed_ms: 22353.787
- authoritative_total_ms: 5520.265
```text
duration_ms  route               phase                                  status
-----------  ------------------  -------------------------------------  ------
0.012        /api/alert/analyze  scorer_readiness                       ok    
0.007        /api/alert/analyze  request_parse                          ok    
85.751       /api/alert/analyze  alert_lookup                           ok    
85.733       /api/alert/analyze  security_context_lookup                ok    
0.163        /api/alert/analyze  category_resolution                    ok    
340.378      /api/alert/analyze  factor_vector_construction             ok    
0.351        /api/alert/analyze  scorer_decision                        ok    
0.015        /api/alert/analyze  post_scorer_confidence_gate            ok    
0.018        /api/alert/analyze  routing_threshold_lookup               ok    
0.027        /api/alert/analyze  rl_exploration_proposal                ok    
0.015        /api/alert/analyze  routing_zone_resolution                ok    
175.809      /api/alert/analyze  referral_history_counts                ok    
0.048        /api/alert/analyze  referral_gate_evaluation               ok    
80.107       /api/alert/analyze  reasoning_generation                   ok    
92.227       /api/alert/analyze  decision_node_and_edge_write           ok    
110.154      /api/alert/analyze  audit_write                            ok    
0.628        /api/alert/analyze  metadata_logging_snapshot_write        ok    
88.853       /api/alert/analyze  campaign_query_find_matching_campaign  ok    
84.373       /api/alert/analyze  campaign_query_fetch_recent_events     ok    
75.225       /api/alert/analyze  campaign_query_check_campaign_exists   ok    
86.773       /api/alert/analyze  campaign_query_create_campaign         ok    
97.318       /api/alert/analyze  campaign_query_member_edge_check       ok    
74.973       /api/alert/analyze  campaign_query_member_edge_create      ok    
67.184       /api/alert/analyze  campaign_query_member_edge_check       ok    
83.736       /api/alert/analyze  campaign_query_member_edge_create      ok    
66.549       /api/alert/analyze  campaign_query_member_edge_check       ok    
77.007       /api/alert/analyze  campaign_query_member_edge_create      ok    
95.1         /api/alert/analyze  campaign_query_member_edge_check       ok    
76.977       /api/alert/analyze  campaign_query_member_edge_create      ok    
105.052      /api/alert/analyze  campaign_query_member_edge_check       ok    
85.217       /api/alert/analyze  campaign_query_member_edge_create      ok    
90.88        /api/alert/analyze  campaign_query_member_edge_check       ok    
81.702       /api/alert/analyze  campaign_query_member_edge_create      ok    
85.139       /api/alert/analyze  campaign_query_member_edge_check       ok    
176.039      /api/alert/analyze  campaign_query_member_edge_create      ok    
83.087       /api/alert/analyze  campaign_query_member_edge_check       ok    
88.584       /api/alert/analyze  campaign_query_member_edge_create      ok    
84.935       /api/alert/analyze  campaign_query_member_edge_check       ok    
74.142       /api/alert/analyze  campaign_query_member_edge_create      ok    
77.527       /api/alert/analyze  campaign_query_member_edge_check       ok    
87.731       /api/alert/analyze  campaign_query_member_edge_create      ok    
89.001       /api/alert/analyze  campaign_query_member_edge_check       ok    
88.833       /api/alert/analyze  campaign_query_member_edge_create      ok    
85.578       /api/alert/analyze  campaign_query_member_edge_check       ok    
91.199       /api/alert/analyze  campaign_query_member_edge_create      ok    
105.086      /api/alert/analyze  campaign_query_member_edge_check       ok    
114.853      /api/alert/analyze  campaign_query_member_edge_create      ok    
73.523       /api/alert/analyze  campaign_query_member_edge_check       ok    
70.281       /api/alert/analyze  campaign_query_member_edge_create      ok    
82.674       /api/alert/analyze  campaign_query_member_edge_check       ok    
82.921       /api/alert/analyze  campaign_query_member_edge_create      ok    
80.878       /api/alert/analyze  campaign_query_member_edge_check       ok    
75.758       /api/alert/analyze  campaign_query_member_edge_create      ok    
80.906       /api/alert/analyze  campaign_query_member_edge_check       ok    
72.601       /api/alert/analyze  campaign_query_member_edge_create      ok    
84.986       /api/alert/analyze  campaign_query_member_edge_check       ok    
96.59        /api/alert/analyze  campaign_query_member_edge_create      ok    
84.955       /api/alert/analyze  campaign_query_member_edge_check       ok    
88.782       /api/alert/analyze  campaign_query_member_edge_create      ok    
83.669       /api/alert/analyze  campaign_query_member_edge_check       ok    
100.893      /api/alert/analyze  campaign_query_member_edge_create      ok    
103.225      /api/alert/analyze  campaign_query_member_edge_check       ok    
93.973       /api/alert/analyze  campaign_query_member_edge_create      ok    
4134.407     /api/alert/analyze  campaign_correlation_summary           ok    
4223.555     /api/alert/analyze  campaign_correlation                   ok    
0.037        /api/alert/analyze  decision_event_emit                    ok    
83.29        /api/alert/analyze  composite_gate_evaluation              ok    
0.102        /api/alert/analyze  provenance_build                       ok    
84.185       /api/alert/analyze  graph_visualization_fetch              ok    
0.04         /api/alert/analyze  response_context_enrichment            ok    
0.051        /api/alert/analyze  referral_debug_build                   ok    
0.053        /api/alert/analyze  shadow_compare_schedule                ok    
94.116       /api/alert/analyze  cluster_history_fetch                  ok    
0.067        /api/alert/analyze  narrative_context_build                ok    
0.076        /api/alert/analyze  narrative_generation                   ok    
4.518        /api/alert/analyze  response_serialization                 ok    
5520.265     /api/alert/analyze  analyze_request_total                  ok    
0.025        /api/alert/outcome  request_parse                          ok    
0.338        /api/alert/outcome  duplicate_feedback_guard               ok    
95.588       /api/alert/outcome  decision_lookup_and_outcome_update     ok    
1.517        /api/alert/outcome  outcome_audit_write                    ok    
105.212      /api/alert/outcome  learning_state_update                  ok    
393.958      /api/alert/outcome  l5_conservation_write                  ok    
395.139      /api/alert/outcome  conservation_monitor                   ok    
0.149        /api/alert/outcome  profile_scorer_update                  ok    
0.109        /api/alert/outcome  l5_dk_weight_write                     ok    
469.722      /api/alert/outcome  l5_centroid_write                      ok    
0.035        /api/alert/outcome  l5_dk_weight_write                     ok    
0.055        /api/alert/outcome  snapshot_evolution_logging             ok    
96.555       /api/alert/outcome  snapshot_evolution_logging             ok    
0.025        /api/alert/outcome  response_serialization                 ok    
1653.887     /api/alert/outcome  outcome_request_total                  ok    
```

### CAMPAIGN25A-0022
- event_count: 94
- total_observed_ms: 21935.479
- authoritative_total_ms: 5433.81
```text
duration_ms  route               phase                                  status
-----------  ------------------  -------------------------------------  ------
0.017        /api/alert/analyze  scorer_readiness                       ok    
0.006        /api/alert/analyze  request_parse                          ok    
78.869       /api/alert/analyze  alert_lookup                           ok    
82.638       /api/alert/analyze  security_context_lookup                ok    
0.138        /api/alert/analyze  category_resolution                    ok    
350.906      /api/alert/analyze  factor_vector_construction             ok    
0.188        /api/alert/analyze  scorer_decision                        ok    
0.021        /api/alert/analyze  post_scorer_confidence_gate            ok    
0.007        /api/alert/analyze  routing_threshold_lookup               ok    
0.015        /api/alert/analyze  rl_exploration_proposal                ok    
0.043        /api/alert/analyze  routing_zone_resolution                ok    
152.971      /api/alert/analyze  referral_history_counts                ok    
0.046        /api/alert/analyze  referral_gate_evaluation               ok    
85.296       /api/alert/analyze  reasoning_generation                   ok    
89.151       /api/alert/analyze  decision_node_and_edge_write           ok    
90.983       /api/alert/analyze  audit_write                            ok    
0.402        /api/alert/analyze  metadata_logging_snapshot_write        ok    
90.566       /api/alert/analyze  campaign_query_find_matching_campaign  ok    
90.729       /api/alert/analyze  campaign_query_fetch_recent_events     ok    
99.263       /api/alert/analyze  campaign_query_check_campaign_exists   ok    
92.272       /api/alert/analyze  campaign_query_create_campaign         ok    
86.329       /api/alert/analyze  campaign_query_member_edge_check       ok    
90.553       /api/alert/analyze  campaign_query_member_edge_create      ok    
84.821       /api/alert/analyze  campaign_query_member_edge_check       ok    
90.939       /api/alert/analyze  campaign_query_member_edge_create      ok    
82.838       /api/alert/analyze  campaign_query_member_edge_check       ok    
85.269       /api/alert/analyze  campaign_query_member_edge_create      ok    
82.341       /api/alert/analyze  campaign_query_member_edge_check       ok    
107.458      /api/alert/analyze  campaign_query_member_edge_create      ok    
89.319       /api/alert/analyze  campaign_query_member_edge_check       ok    
81.732       /api/alert/analyze  campaign_query_member_edge_create      ok    
88.499       /api/alert/analyze  campaign_query_member_edge_check       ok    
79.173       /api/alert/analyze  campaign_query_member_edge_create      ok    
68.611       /api/alert/analyze  campaign_query_member_edge_check       ok    
73.034       /api/alert/analyze  campaign_query_member_edge_create      ok    
76.185       /api/alert/analyze  campaign_query_member_edge_check       ok    
86.69        /api/alert/analyze  campaign_query_member_edge_create      ok    
90.107       /api/alert/analyze  campaign_query_member_edge_check       ok    
85.977       /api/alert/analyze  campaign_query_member_edge_create      ok    
73.285       /api/alert/analyze  campaign_query_member_edge_check       ok    
88.976       /api/alert/analyze  campaign_query_member_edge_create      ok    
89.184       /api/alert/analyze  campaign_query_member_edge_check       ok    
85.747       /api/alert/analyze  campaign_query_member_edge_create      ok    
82.242       /api/alert/analyze  campaign_query_member_edge_check       ok    
86.778       /api/alert/analyze  campaign_query_member_edge_create      ok    
85.448       /api/alert/analyze  campaign_query_member_edge_check       ok    
83.788       /api/alert/analyze  campaign_query_member_edge_create      ok    
80.327       /api/alert/analyze  campaign_query_member_edge_check       ok    
67.801       /api/alert/analyze  campaign_query_member_edge_create      ok    
83.328       /api/alert/analyze  campaign_query_member_edge_check       ok    
98.786       /api/alert/analyze  campaign_query_member_edge_create      ok    
83.343       /api/alert/analyze  campaign_query_member_edge_check       ok    
87.363       /api/alert/analyze  campaign_query_member_edge_create      ok    
68.058       /api/alert/analyze  campaign_query_member_edge_check       ok    
71.319       /api/alert/analyze  campaign_query_member_edge_create      ok    
82.511       /api/alert/analyze  campaign_query_member_edge_check       ok    
85.607       /api/alert/analyze  campaign_query_member_edge_create      ok    
68.766       /api/alert/analyze  campaign_query_member_edge_check       ok    
87.128       /api/alert/analyze  campaign_query_member_edge_create      ok    
88.435       /api/alert/analyze  campaign_query_member_edge_check       ok    
78.033       /api/alert/analyze  campaign_query_member_edge_create      ok    
83.039       /api/alert/analyze  campaign_query_member_edge_check       ok    
91.38        /api/alert/analyze  campaign_query_member_edge_create      ok    
75.351       /api/alert/analyze  campaign_query_member_edge_check       ok    
81.343       /api/alert/analyze  campaign_query_member_edge_create      ok    
4144.388     /api/alert/analyze  campaign_correlation_summary           ok    
4226.705     /api/alert/analyze  campaign_correlation                   ok    
0.021        /api/alert/analyze  decision_event_emit                    ok    
70.547       /api/alert/analyze  composite_gate_evaluation              ok    
0.056        /api/alert/analyze  provenance_build                       ok    
79.694       /api/alert/analyze  graph_visualization_fetch              ok    
0.025        /api/alert/analyze  response_context_enrichment            ok    
0.034        /api/alert/analyze  referral_debug_build                   ok    
0.014        /api/alert/analyze  shadow_compare_schedule                ok    
71.245       /api/alert/analyze  cluster_history_fetch                  ok    
0.035        /api/alert/analyze  narrative_context_build                ok    
0.036        /api/alert/analyze  narrative_generation                   ok    
2.275        /api/alert/analyze  response_serialization                 ok    
5433.81      /api/alert/analyze  analyze_request_total                  ok    
0.008        /api/alert/outcome  request_parse                          ok    
0.011        /api/alert/outcome  duplicate_feedback_guard               ok    
71.199       /api/alert/outcome  decision_lookup_and_outcome_update     ok    
0.26         /api/alert/outcome  outcome_audit_write                    ok    
87.846       /api/alert/outcome  learning_state_update                  ok    
378.904      /api/alert/outcome  l5_conservation_write                  ok    
380.706      /api/alert/outcome  conservation_monitor                   ok    
0.253        /api/alert/outcome  profile_scorer_update                  ok    
0.115        /api/alert/outcome  l5_dk_weight_write                     ok    
373.63       /api/alert/outcome  l5_centroid_write                      ok    
0.014        /api/alert/outcome  l5_dk_weight_write                     ok    
94.629       /api/alert/outcome  snapshot_evolution_logging             ok    
71.385       /api/alert/outcome  snapshot_evolution_logging             ok    
0.026        /api/alert/outcome  response_serialization                 ok    
1475.84      /api/alert/outcome  outcome_request_total                  ok    
```

### CAMPAIGN25A-0024
- event_count: 98
- total_observed_ms: 22089.593
- authoritative_total_ms: 5379.588
```text
duration_ms  route               phase                                  status
-----------  ------------------  -------------------------------------  ------
0.014        /api/alert/analyze  scorer_readiness                       ok    
0.006        /api/alert/analyze  request_parse                          ok    
72.264       /api/alert/analyze  alert_lookup                           ok    
88.828       /api/alert/analyze  security_context_lookup                ok    
0.173        /api/alert/analyze  category_resolution                    ok    
353.139      /api/alert/analyze  factor_vector_construction             ok    
0.464        /api/alert/analyze  scorer_decision                        ok    
0.014        /api/alert/analyze  post_scorer_confidence_gate            ok    
0.007        /api/alert/analyze  routing_threshold_lookup               ok    
0.013        /api/alert/analyze  rl_exploration_proposal                ok    
0.014        /api/alert/analyze  routing_zone_resolution                ok    
177.259      /api/alert/analyze  referral_history_counts                ok    
0.096        /api/alert/analyze  referral_gate_evaluation               ok    
79.531       /api/alert/analyze  reasoning_generation                   ok    
74.209       /api/alert/analyze  decision_node_and_edge_write           ok    
91.586       /api/alert/analyze  audit_write                            ok    
0.201        /api/alert/analyze  metadata_logging_snapshot_write        ok    
91.419       /api/alert/analyze  campaign_query_find_matching_campaign  ok    
84.449       /api/alert/analyze  campaign_query_fetch_recent_events     ok    
88.133       /api/alert/analyze  campaign_query_check_campaign_exists   ok    
74.679       /api/alert/analyze  campaign_query_create_campaign         ok    
65.181       /api/alert/analyze  campaign_query_member_edge_check       ok    
75.69        /api/alert/analyze  campaign_query_member_edge_create      ok    
76.858       /api/alert/analyze  campaign_query_member_edge_check       ok    
66.491       /api/alert/analyze  campaign_query_member_edge_create      ok    
66.578       /api/alert/analyze  campaign_query_member_edge_check       ok    
81.838       /api/alert/analyze  campaign_query_member_edge_create      ok    
87.424       /api/alert/analyze  campaign_query_member_edge_check       ok    
79.989       /api/alert/analyze  campaign_query_member_edge_create      ok    
60.534       /api/alert/analyze  campaign_query_member_edge_check       ok    
66.648       /api/alert/analyze  campaign_query_member_edge_create      ok    
72.231       /api/alert/analyze  campaign_query_member_edge_check       ok    
66.921       /api/alert/analyze  campaign_query_member_edge_create      ok    
61.091       /api/alert/analyze  campaign_query_member_edge_check       ok    
74.757       /api/alert/analyze  campaign_query_member_edge_create      ok    
73.331       /api/alert/analyze  campaign_query_member_edge_check       ok    
80.23        /api/alert/analyze  campaign_query_member_edge_create      ok    
70.338       /api/alert/analyze  campaign_query_member_edge_check       ok    
93.858       /api/alert/analyze  campaign_query_member_edge_create      ok    
87.43        /api/alert/analyze  campaign_query_member_edge_check       ok    
70.347       /api/alert/analyze  campaign_query_member_edge_create      ok    
66.078       /api/alert/analyze  campaign_query_member_edge_check       ok    
78.456       /api/alert/analyze  campaign_query_member_edge_create      ok    
79.087       /api/alert/analyze  campaign_query_member_edge_check       ok    
79.631       /api/alert/analyze  campaign_query_member_edge_create      ok    
78.692       /api/alert/analyze  campaign_query_member_edge_check       ok    
74.549       /api/alert/analyze  campaign_query_member_edge_create      ok    
67.123       /api/alert/analyze  campaign_query_member_edge_check       ok    
67.4         /api/alert/analyze  campaign_query_member_edge_create      ok    
66.61        /api/alert/analyze  campaign_query_member_edge_check       ok    
71.804       /api/alert/analyze  campaign_query_member_edge_create      ok    
71.595       /api/alert/analyze  campaign_query_member_edge_check       ok    
88.035       /api/alert/analyze  campaign_query_member_edge_create      ok    
68.359       /api/alert/analyze  campaign_query_member_edge_check       ok    
64.392       /api/alert/analyze  campaign_query_member_edge_create      ok    
78.925       /api/alert/analyze  campaign_query_member_edge_check       ok    
76.221       /api/alert/analyze  campaign_query_member_edge_create      ok    
79.244       /api/alert/analyze  campaign_query_member_edge_check       ok    
79.779       /api/alert/analyze  campaign_query_member_edge_create      ok    
81.518       /api/alert/analyze  campaign_query_member_edge_check       ok    
69.151       /api/alert/analyze  campaign_query_member_edge_create      ok    
74.801       /api/alert/analyze  campaign_query_member_edge_check       ok    
85.308       /api/alert/analyze  campaign_query_member_edge_create      ok    
80.106       /api/alert/analyze  campaign_query_member_edge_check       ok    
77.998       /api/alert/analyze  campaign_query_member_edge_create      ok    
77.896       /api/alert/analyze  campaign_query_member_edge_check       ok    
71.867       /api/alert/analyze  campaign_query_member_edge_create      ok    
82.941       /api/alert/analyze  campaign_query_member_edge_check       ok    
103.956      /api/alert/analyze  campaign_query_member_edge_create      ok    
4051.486     /api/alert/analyze  campaign_correlation_summary           ok    
4135.163     /api/alert/analyze  campaign_correlation                   ok    
0.041        /api/alert/analyze  decision_event_emit                    ok    
66.88        /api/alert/analyze  composite_gate_evaluation              ok    
0.064        /api/alert/analyze  provenance_build                       ok    
82.109       /api/alert/analyze  graph_visualization_fetch              ok    
0.031        /api/alert/analyze  response_context_enrichment            ok    
0.065        /api/alert/analyze  referral_debug_build                   ok    
0.028        /api/alert/analyze  shadow_compare_schedule                ok    
99.033       /api/alert/analyze  cluster_history_fetch                  ok    
0.067        /api/alert/analyze  narrative_context_build                ok    
0.107        /api/alert/analyze  narrative_generation                   ok    
6.774        /api/alert/analyze  response_serialization                 ok    
5379.588     /api/alert/analyze  analyze_request_total                  ok    
0.022        /api/alert/outcome  request_parse                          ok    
0.008        /api/alert/outcome  duplicate_feedback_guard               ok    
304.312      /api/alert/outcome  decision_lookup_and_outcome_update     ok    
0.45         /api/alert/outcome  outcome_audit_write                    ok    
89.298       /api/alert/outcome  learning_state_update                  ok    
381.463      /api/alert/outcome  l5_conservation_write                  ok    
383.647      /api/alert/outcome  conservation_monitor                   ok    
0.2          /api/alert/outcome  profile_scorer_update                  ok    
1.099        /api/alert/outcome  l5_dk_weight_write                     ok    
429.624      /api/alert/outcome  l5_centroid_write                      ok    
0.029        /api/alert/outcome  l5_dk_weight_write                     ok    
0.017        /api/alert/outcome  snapshot_evolution_logging             ok    
76.071       /api/alert/outcome  snapshot_evolution_logging             ok    
0.023        /api/alert/outcome  response_serialization                 ok    
1706.109     /api/alert/outcome  outcome_request_total                  ok    
```

### CAMPAIGN25A-0019
- event_count: 88
- total_observed_ms: 20171.769
- authoritative_total_ms: 5004.175
```text
duration_ms  route               phase                                  status
-----------  ------------------  -------------------------------------  ------
0.035        /api/alert/analyze  scorer_readiness                       ok    
0.015        /api/alert/analyze  request_parse                          ok    
102.757      /api/alert/analyze  alert_lookup                           ok    
111.151      /api/alert/analyze  security_context_lookup                ok    
0.256        /api/alert/analyze  category_resolution                    ok    
337.014      /api/alert/analyze  factor_vector_construction             ok    
0.224        /api/alert/analyze  scorer_decision                        ok    
0.03         /api/alert/analyze  post_scorer_confidence_gate            ok    
0.014        /api/alert/analyze  routing_threshold_lookup               ok    
0.023        /api/alert/analyze  rl_exploration_proposal                ok    
0.027        /api/alert/analyze  routing_zone_resolution                ok    
177.566      /api/alert/analyze  referral_history_counts                ok    
0.069        /api/alert/analyze  referral_gate_evaluation               ok    
87.792       /api/alert/analyze  reasoning_generation                   ok    
82.874       /api/alert/analyze  decision_node_and_edge_write           ok    
99.991       /api/alert/analyze  audit_write                            ok    
0.417        /api/alert/analyze  metadata_logging_snapshot_write        ok    
90.59        /api/alert/analyze  campaign_query_find_matching_campaign  ok    
80.79        /api/alert/analyze  campaign_query_fetch_recent_events     ok    
88.889       /api/alert/analyze  campaign_query_check_campaign_exists   ok    
66.226       /api/alert/analyze  campaign_query_create_campaign         ok    
64.58        /api/alert/analyze  campaign_query_member_edge_check       ok    
97.802       /api/alert/analyze  campaign_query_member_edge_create      ok    
86.325       /api/alert/analyze  campaign_query_member_edge_check       ok    
91.567       /api/alert/analyze  campaign_query_member_edge_create      ok    
77.038       /api/alert/analyze  campaign_query_member_edge_check       ok    
72.123       /api/alert/analyze  campaign_query_member_edge_create      ok    
67.743       /api/alert/analyze  campaign_query_member_edge_check       ok    
87.267       /api/alert/analyze  campaign_query_member_edge_create      ok    
74.142       /api/alert/analyze  campaign_query_member_edge_check       ok    
83.405       /api/alert/analyze  campaign_query_member_edge_create      ok    
71.984       /api/alert/analyze  campaign_query_member_edge_check       ok    
82.927       /api/alert/analyze  campaign_query_member_edge_create      ok    
79.426       /api/alert/analyze  campaign_query_member_edge_check       ok    
89.075       /api/alert/analyze  campaign_query_member_edge_create      ok    
79.453       /api/alert/analyze  campaign_query_member_edge_check       ok    
71.047       /api/alert/analyze  campaign_query_member_edge_create      ok    
79.773       /api/alert/analyze  campaign_query_member_edge_check       ok    
90.856       /api/alert/analyze  campaign_query_member_edge_create      ok    
83.219       /api/alert/analyze  campaign_query_member_edge_check       ok    
84.473       /api/alert/analyze  campaign_query_member_edge_create      ok    
80.352       /api/alert/analyze  campaign_query_member_edge_check       ok    
86.21        /api/alert/analyze  campaign_query_member_edge_create      ok    
75.188       /api/alert/analyze  campaign_query_member_edge_check       ok    
100.071      /api/alert/analyze  campaign_query_member_edge_create      ok    
75.775       /api/alert/analyze  campaign_query_member_edge_check       ok    
86.271       /api/alert/analyze  campaign_query_member_edge_create      ok    
72.695       /api/alert/analyze  campaign_query_member_edge_check       ok    
72.971       /api/alert/analyze  campaign_query_member_edge_create      ok    
69.279       /api/alert/analyze  campaign_query_member_edge_check       ok    
94.314       /api/alert/analyze  campaign_query_member_edge_create      ok    
78.908       /api/alert/analyze  campaign_query_member_edge_check       ok    
97.751       /api/alert/analyze  campaign_query_member_edge_create      ok    
81.269       /api/alert/analyze  campaign_query_member_edge_check       ok    
89.269       /api/alert/analyze  campaign_query_member_edge_create      ok    
88.913       /api/alert/analyze  campaign_query_member_edge_check       ok    
86.803       /api/alert/analyze  campaign_query_member_edge_create      ok    
92.095       /api/alert/analyze  campaign_query_member_edge_check       ok    
90.509       /api/alert/analyze  campaign_query_member_edge_create      ok    
3544.182     /api/alert/analyze  campaign_correlation_summary           ok    
3634.251     /api/alert/analyze  campaign_correlation                   ok    
0.04         /api/alert/analyze  decision_event_emit                    ok    
96.111       /api/alert/analyze  composite_gate_evaluation              ok    
0.086        /api/alert/analyze  provenance_build                       ok    
104.488      /api/alert/analyze  graph_visualization_fetch              ok    
0.035        /api/alert/analyze  response_context_enrichment            ok    
0.052        /api/alert/analyze  referral_debug_build                   ok    
0.031        /api/alert/analyze  shadow_compare_schedule                ok    
90.332       /api/alert/analyze  cluster_history_fetch                  ok    
0.045        /api/alert/analyze  narrative_context_build                ok    
0.094        /api/alert/analyze  narrative_generation                   ok    
5.968        /api/alert/analyze  response_serialization                 ok    
5004.175     /api/alert/analyze  analyze_request_total                  ok    
0.006        /api/alert/outcome  request_parse                          ok    
0.007        /api/alert/outcome  duplicate_feedback_guard               ok    
84.89        /api/alert/outcome  decision_lookup_and_outcome_update     ok    
0.574        /api/alert/outcome  outcome_audit_write                    ok    
149.543      /api/alert/outcome  learning_state_update                  ok    
454.991      /api/alert/outcome  l5_conservation_write                  ok    
457.359      /api/alert/outcome  conservation_monitor                   ok    
0.157        /api/alert/outcome  profile_scorer_update                  ok    
0.218        /api/alert/outcome  l5_dk_weight_write                     ok    
389.625      /api/alert/outcome  l5_centroid_write                      ok    
0.014        /api/alert/outcome  l5_dk_weight_write                     ok    
0.017        /api/alert/outcome  snapshot_evolution_logging             ok    
85.6         /api/alert/outcome  snapshot_evolution_logging             ok    
0.034        /api/alert/outcome  response_serialization                 ok    
1609.226     /api/alert/outcome  outcome_request_total                  ok    
```

### CAMPAIGN25A-0020
- event_count: 90
- total_observed_ms: 19935.6
- authoritative_total_ms: 4820.304
```text
duration_ms  route               phase                                  status
-----------  ------------------  -------------------------------------  ------
0.027        /api/alert/analyze  scorer_readiness                       ok    
0.018        /api/alert/analyze  request_parse                          ok    
91.272       /api/alert/analyze  alert_lookup                           ok    
77.051       /api/alert/analyze  security_context_lookup                ok    
0.157        /api/alert/analyze  category_resolution                    ok    
283.67       /api/alert/analyze  factor_vector_construction             ok    
0.224        /api/alert/analyze  scorer_decision                        ok    
0.021        /api/alert/analyze  post_scorer_confidence_gate            ok    
0.01         /api/alert/analyze  routing_threshold_lookup               ok    
0.014        /api/alert/analyze  rl_exploration_proposal                ok    
0.034        /api/alert/analyze  routing_zone_resolution                ok    
192.023      /api/alert/analyze  referral_history_counts                ok    
0.063        /api/alert/analyze  referral_gate_evaluation               ok    
76.946       /api/alert/analyze  reasoning_generation                   ok    
98.878       /api/alert/analyze  decision_node_and_edge_write           ok    
88.755       /api/alert/analyze  audit_write                            ok    
0.177        /api/alert/analyze  metadata_logging_snapshot_write        ok    
80.404       /api/alert/analyze  campaign_query_find_matching_campaign  ok    
84.478       /api/alert/analyze  campaign_query_fetch_recent_events     ok    
81.777       /api/alert/analyze  campaign_query_check_campaign_exists   ok    
94.367       /api/alert/analyze  campaign_query_create_campaign         ok    
105.07       /api/alert/analyze  campaign_query_member_edge_check       ok    
102.572      /api/alert/analyze  campaign_query_member_edge_create      ok    
93.041       /api/alert/analyze  campaign_query_member_edge_check       ok    
101.684      /api/alert/analyze  campaign_query_member_edge_create      ok    
76.868       /api/alert/analyze  campaign_query_member_edge_check       ok    
84.147       /api/alert/analyze  campaign_query_member_edge_create      ok    
97.618       /api/alert/analyze  campaign_query_member_edge_check       ok    
90.233       /api/alert/analyze  campaign_query_member_edge_create      ok    
87.44        /api/alert/analyze  campaign_query_member_edge_check       ok    
103.929      /api/alert/analyze  campaign_query_member_edge_create      ok    
93.293       /api/alert/analyze  campaign_query_member_edge_check       ok    
79.103       /api/alert/analyze  campaign_query_member_edge_create      ok    
72.344       /api/alert/analyze  campaign_query_member_edge_check       ok    
78.1         /api/alert/analyze  campaign_query_member_edge_create      ok    
65.288       /api/alert/analyze  campaign_query_member_edge_check       ok    
68.227       /api/alert/analyze  campaign_query_member_edge_create      ok    
74.946       /api/alert/analyze  campaign_query_member_edge_check       ok    
68.045       /api/alert/analyze  campaign_query_member_edge_create      ok    
61.732       /api/alert/analyze  campaign_query_member_edge_check       ok    
65.369       /api/alert/analyze  campaign_query_member_edge_create      ok    
70.399       /api/alert/analyze  campaign_query_member_edge_check       ok    
78.64        /api/alert/analyze  campaign_query_member_edge_create      ok    
70.079       /api/alert/analyze  campaign_query_member_edge_check       ok    
69.626       /api/alert/analyze  campaign_query_member_edge_create      ok    
67.084       /api/alert/analyze  campaign_query_member_edge_check       ok    
63.977       /api/alert/analyze  campaign_query_member_edge_create      ok    
74.866       /api/alert/analyze  campaign_query_member_edge_check       ok    
68.04        /api/alert/analyze  campaign_query_member_edge_create      ok    
79.12        /api/alert/analyze  campaign_query_member_edge_check       ok    
66.22        /api/alert/analyze  campaign_query_member_edge_create      ok    
91.242       /api/alert/analyze  campaign_query_member_edge_check       ok    
84.358       /api/alert/analyze  campaign_query_member_edge_create      ok    
60.694       /api/alert/analyze  campaign_query_member_edge_check       ok    
69.846       /api/alert/analyze  campaign_query_member_edge_create      ok    
66.105       /api/alert/analyze  campaign_query_member_edge_check       ok    
75.022       /api/alert/analyze  campaign_query_member_edge_create      ok    
86.806       /api/alert/analyze  campaign_query_member_edge_check       ok    
81.331       /api/alert/analyze  campaign_query_member_edge_create      ok    
70.469       /api/alert/analyze  campaign_query_member_edge_check       ok    
84.265       /api/alert/analyze  campaign_query_member_edge_create      ok    
3562.359     /api/alert/analyze  campaign_correlation_summary           ok    
3638.457     /api/alert/analyze  campaign_correlation                   ok    
0.023        /api/alert/analyze  decision_event_emit                    ok    
63.529       /api/alert/analyze  composite_gate_evaluation              ok    
0.064        /api/alert/analyze  provenance_build                       ok    
76.852       /api/alert/analyze  graph_visualization_fetch              ok    
0.029        /api/alert/analyze  response_context_enrichment            ok    
0.033        /api/alert/analyze  referral_debug_build                   ok    
0.012        /api/alert/analyze  shadow_compare_schedule                ok    
70.507       /api/alert/analyze  cluster_history_fetch                  ok    
0.034        /api/alert/analyze  narrative_context_build                ok    
0.045        /api/alert/analyze  narrative_generation                   ok    
1.99         /api/alert/analyze  response_serialization                 ok    
4820.304     /api/alert/analyze  analyze_request_total                  ok    
0.008        /api/alert/outcome  request_parse                          ok    
0.007        /api/alert/outcome  duplicate_feedback_guard               ok    
207.294      /api/alert/outcome  decision_lookup_and_outcome_update     ok    
0.572        /api/alert/outcome  outcome_audit_write                    ok    
141.273      /api/alert/outcome  learning_state_update                  ok    
380.665      /api/alert/outcome  l5_conservation_write                  ok    
382.005      /api/alert/outcome  conservation_monitor                   ok    
0.171        /api/alert/outcome  profile_scorer_update                  ok    
0.155        /api/alert/outcome  l5_dk_weight_write                     ok    
433.927      /api/alert/outcome  l5_centroid_write                      ok    
0.018        /api/alert/outcome  l5_dk_weight_write                     ok    
0.031        /api/alert/outcome  snapshot_evolution_logging             ok    
76.384       /api/alert/outcome  snapshot_evolution_logging             ok    
0.024        /api/alert/outcome  response_serialization                 ok    
1681.224     /api/alert/outcome  outcome_request_total                  ok    
```

### CAMPAIGN25A-0018
- event_count: 86
- total_observed_ms: 19075.761
- authoritative_total_ms: 4655.852
```text
duration_ms  route               phase                                  status
-----------  ------------------  -------------------------------------  ------
0.018        /api/alert/analyze  scorer_readiness                       ok    
0.009        /api/alert/analyze  request_parse                          ok    
71.972       /api/alert/analyze  alert_lookup                           ok    
77.678       /api/alert/analyze  security_context_lookup                ok    
0.149        /api/alert/analyze  category_resolution                    ok    
339.977      /api/alert/analyze  factor_vector_construction             ok    
0.223        /api/alert/analyze  scorer_decision                        ok    
0.015        /api/alert/analyze  post_scorer_confidence_gate            ok    
0.013        /api/alert/analyze  routing_threshold_lookup               ok    
0.028        /api/alert/analyze  rl_exploration_proposal                ok    
0.017        /api/alert/analyze  routing_zone_resolution                ok    
144.559      /api/alert/analyze  referral_history_counts                ok    
0.04         /api/alert/analyze  referral_gate_evaluation               ok    
80.298       /api/alert/analyze  reasoning_generation                   ok    
74.114       /api/alert/analyze  decision_node_and_edge_write           ok    
89.633       /api/alert/analyze  audit_write                            ok    
8.046        /api/alert/analyze  metadata_logging_snapshot_write        ok    
71.287       /api/alert/analyze  campaign_query_find_matching_campaign  ok    
76.61        /api/alert/analyze  campaign_query_fetch_recent_events     ok    
79.442       /api/alert/analyze  campaign_query_check_campaign_exists   ok    
72.161       /api/alert/analyze  campaign_query_create_campaign         ok    
66.4         /api/alert/analyze  campaign_query_member_edge_check       ok    
77.994       /api/alert/analyze  campaign_query_member_edge_create      ok    
74.257       /api/alert/analyze  campaign_query_member_edge_check       ok    
89.783       /api/alert/analyze  campaign_query_member_edge_create      ok    
82.003       /api/alert/analyze  campaign_query_member_edge_check       ok    
78.363       /api/alert/analyze  campaign_query_member_edge_create      ok    
78.874       /api/alert/analyze  campaign_query_member_edge_check       ok    
77.904       /api/alert/analyze  campaign_query_member_edge_create      ok    
73.57        /api/alert/analyze  campaign_query_member_edge_check       ok    
74.38        /api/alert/analyze  campaign_query_member_edge_create      ok    
96.029       /api/alert/analyze  campaign_query_member_edge_check       ok    
104.573      /api/alert/analyze  campaign_query_member_edge_create      ok    
73.915       /api/alert/analyze  campaign_query_member_edge_check       ok    
74.806       /api/alert/analyze  campaign_query_member_edge_create      ok    
85.057       /api/alert/analyze  campaign_query_member_edge_check       ok    
76.689       /api/alert/analyze  campaign_query_member_edge_create      ok    
68.19        /api/alert/analyze  campaign_query_member_edge_check       ok    
109.858      /api/alert/analyze  campaign_query_member_edge_create      ok    
85.796       /api/alert/analyze  campaign_query_member_edge_check       ok    
88.993       /api/alert/analyze  campaign_query_member_edge_create      ok    
70.401       /api/alert/analyze  campaign_query_member_edge_check       ok    
94.074       /api/alert/analyze  campaign_query_member_edge_create      ok    
107.176      /api/alert/analyze  campaign_query_member_edge_check       ok    
89.789       /api/alert/analyze  campaign_query_member_edge_create      ok    
70.164       /api/alert/analyze  campaign_query_member_edge_check       ok    
77.525       /api/alert/analyze  campaign_query_member_edge_create      ok    
80.682       /api/alert/analyze  campaign_query_member_edge_check       ok    
101.81       /api/alert/analyze  campaign_query_member_edge_create      ok    
87.213       /api/alert/analyze  campaign_query_member_edge_check       ok    
81.667       /api/alert/analyze  campaign_query_member_edge_create      ok    
98.118       /api/alert/analyze  campaign_query_member_edge_check       ok    
92.083       /api/alert/analyze  campaign_query_member_edge_create      ok    
67.281       /api/alert/analyze  campaign_query_member_edge_check       ok    
73.436       /api/alert/analyze  campaign_query_member_edge_create      ok    
77.447       /api/alert/analyze  campaign_query_member_edge_check       ok    
77.251       /api/alert/analyze  campaign_query_member_edge_create      ok    
3349.931     /api/alert/analyze  campaign_correlation_summary           ok    
3458.763     /api/alert/analyze  campaign_correlation                   ok    
0.038        /api/alert/analyze  decision_event_emit                    ok    
93.51        /api/alert/analyze  composite_gate_evaluation              ok    
0.055        /api/alert/analyze  provenance_build                       ok    
84.599       /api/alert/analyze  graph_visualization_fetch              ok    
0.027        /api/alert/analyze  response_context_enrichment            ok    
0.041        /api/alert/analyze  referral_debug_build                   ok    
0.018        /api/alert/analyze  shadow_compare_schedule                ok    
71.022       /api/alert/analyze  cluster_history_fetch                  ok    
0.066        /api/alert/analyze  narrative_context_build                ok    
0.11         /api/alert/analyze  narrative_generation                   ok    
12.112       /api/alert/analyze  response_serialization                 ok    
4655.852     /api/alert/analyze  analyze_request_total                  ok    
0.017        /api/alert/outcome  request_parse                          ok    
0.029        /api/alert/outcome  duplicate_feedback_guard               ok    
91.591       /api/alert/outcome  decision_lookup_and_outcome_update     ok    
0.197        /api/alert/outcome  outcome_audit_write                    ok    
128.964      /api/alert/outcome  learning_state_update                  ok    
393.557      /api/alert/outcome  l5_conservation_write                  ok    
397.005      /api/alert/outcome  conservation_monitor                   ok    
0.281        /api/alert/outcome  profile_scorer_update                  ok    
0.405        /api/alert/outcome  l5_dk_weight_write                     ok    
454.324      /api/alert/outcome  l5_centroid_write                      ok    
0.027        /api/alert/outcome  l5_dk_weight_write                     ok    
0.032        /api/alert/outcome  snapshot_evolution_logging             ok    
99.16        /api/alert/outcome  snapshot_evolution_logging             ok    
0.098        /api/alert/outcome  response_serialization                 ok    
1614.09      /api/alert/outcome  outcome_request_total                  ok    
```

### CAMPAIGN25A-0016
- event_count: 82
- total_observed_ms: 18503.022
- authoritative_total_ms: 4503.944
```text
duration_ms  route               phase                                  status
-----------  ------------------  -------------------------------------  ------
0.02         /api/alert/analyze  scorer_readiness                       ok    
0.007        /api/alert/analyze  request_parse                          ok    
66.151       /api/alert/analyze  alert_lookup                           ok    
88.962       /api/alert/analyze  security_context_lookup                ok    
0.19         /api/alert/analyze  category_resolution                    ok    
330.523      /api/alert/analyze  factor_vector_construction             ok    
0.354        /api/alert/analyze  scorer_decision                        ok    
0.015        /api/alert/analyze  post_scorer_confidence_gate            ok    
0.007        /api/alert/analyze  routing_threshold_lookup               ok    
0.026        /api/alert/analyze  rl_exploration_proposal                ok    
0.013        /api/alert/analyze  routing_zone_resolution                ok    
165.239      /api/alert/analyze  referral_history_counts                ok    
0.105        /api/alert/analyze  referral_gate_evaluation               ok    
78.589       /api/alert/analyze  reasoning_generation                   ok    
91.642       /api/alert/analyze  decision_node_and_edge_write           ok    
93.742       /api/alert/analyze  audit_write                            ok    
0.298        /api/alert/analyze  metadata_logging_snapshot_write        ok    
88.523       /api/alert/analyze  campaign_query_find_matching_campaign  ok    
86.295       /api/alert/analyze  campaign_query_fetch_recent_events     ok    
81.185       /api/alert/analyze  campaign_query_check_campaign_exists   ok    
91.41        /api/alert/analyze  campaign_query_create_campaign         ok    
69.6         /api/alert/analyze  campaign_query_member_edge_check       ok    
74.4         /api/alert/analyze  campaign_query_member_edge_create      ok    
84.233       /api/alert/analyze  campaign_query_member_edge_check       ok    
84.86        /api/alert/analyze  campaign_query_member_edge_create      ok    
105.415      /api/alert/analyze  campaign_query_member_edge_check       ok    
90.956       /api/alert/analyze  campaign_query_member_edge_create      ok    
85.315       /api/alert/analyze  campaign_query_member_edge_check       ok    
88.314       /api/alert/analyze  campaign_query_member_edge_create      ok    
87.099       /api/alert/analyze  campaign_query_member_edge_check       ok    
77.266       /api/alert/analyze  campaign_query_member_edge_create      ok    
82.887       /api/alert/analyze  campaign_query_member_edge_check       ok    
88.111       /api/alert/analyze  campaign_query_member_edge_create      ok    
72.984       /api/alert/analyze  campaign_query_member_edge_check       ok    
95.222       /api/alert/analyze  campaign_query_member_edge_create      ok    
78.865       /api/alert/analyze  campaign_query_member_edge_check       ok    
75.184       /api/alert/analyze  campaign_query_member_edge_create      ok    
76.225       /api/alert/analyze  campaign_query_member_edge_check       ok    
90.33        /api/alert/analyze  campaign_query_member_edge_create      ok    
80.387       /api/alert/analyze  campaign_query_member_edge_check       ok    
94.74        /api/alert/analyze  campaign_query_member_edge_create      ok    
87.698       /api/alert/analyze  campaign_query_member_edge_check       ok    
84.286       /api/alert/analyze  campaign_query_member_edge_create      ok    
100.507      /api/alert/analyze  campaign_query_member_edge_check       ok    
98.409       /api/alert/analyze  campaign_query_member_edge_create      ok    
88.951       /api/alert/analyze  campaign_query_member_edge_check       ok    
95.278       /api/alert/analyze  campaign_query_member_edge_create      ok    
79.652       /api/alert/analyze  campaign_query_member_edge_check       ok    
89.94        /api/alert/analyze  campaign_query_member_edge_create      ok    
80.229       /api/alert/analyze  campaign_query_member_edge_check       ok    
87.65        /api/alert/analyze  campaign_query_member_edge_create      ok    
81.885       /api/alert/analyze  campaign_query_member_edge_check       ok    
91.901       /api/alert/analyze  campaign_query_member_edge_create      ok    
3194.63      /api/alert/analyze  campaign_correlation_summary           ok    
3281.205     /api/alert/analyze  campaign_correlation                   ok    
0.042        /api/alert/analyze  decision_event_emit                    ok    
82.873       /api/alert/analyze  composite_gate_evaluation              ok    
0.109        /api/alert/analyze  provenance_build                       ok    
82.84        /api/alert/analyze  graph_visualization_fetch              ok    
0.049        /api/alert/analyze  response_context_enrichment            ok    
0.029        /api/alert/analyze  referral_debug_build                   ok    
0.012        /api/alert/analyze  shadow_compare_schedule                ok    
76.272       /api/alert/analyze  cluster_history_fetch                  ok    
0.035        /api/alert/analyze  narrative_context_build                ok    
0.043        /api/alert/analyze  narrative_generation                   ok    
2.138        /api/alert/analyze  response_serialization                 ok    
4503.944     /api/alert/analyze  analyze_request_total                  ok    
0.02         /api/alert/outcome  request_parse                          ok    
0.009        /api/alert/outcome  duplicate_feedback_guard               ok    
84.235       /api/alert/outcome  decision_lookup_and_outcome_update     ok    
0.526        /api/alert/outcome  outcome_audit_write                    ok    
87.436       /api/alert/outcome  learning_state_update                  ok    
447.584      /api/alert/outcome  l5_conservation_write                  ok    
450.94       /api/alert/outcome  conservation_monitor                   ok    
0.254        /api/alert/outcome  profile_scorer_update                  ok    
0.208        /api/alert/outcome  l5_dk_weight_write                     ok    
477.696      /api/alert/outcome  l5_centroid_write                      ok    
0.029        /api/alert/outcome  l5_dk_weight_write                     ok    
0.016        /api/alert/outcome  snapshot_evolution_logging             ok    
94.253       /api/alert/outcome  snapshot_evolution_logging             ok    
0.047        /api/alert/outcome  response_serialization                 ok    
1623.473     /api/alert/outcome  outcome_request_total                  ok    
```

### CAMPAIGN25A-0017
- event_count: 84
- total_observed_ms: 17659.317
- authoritative_total_ms: 4388.699
```text
duration_ms  route               phase                                  status
-----------  ------------------  -------------------------------------  ------
0.018        /api/alert/analyze  scorer_readiness                       ok    
0.006        /api/alert/analyze  request_parse                          ok    
64.54        /api/alert/analyze  alert_lookup                           ok    
89.489       /api/alert/analyze  security_context_lookup                ok    
0.213        /api/alert/analyze  category_resolution                    ok    
308.817      /api/alert/analyze  factor_vector_construction             ok    
0.759        /api/alert/analyze  scorer_decision                        ok    
0.029        /api/alert/analyze  post_scorer_confidence_gate            ok    
0.02         /api/alert/analyze  routing_threshold_lookup               ok    
0.018        /api/alert/analyze  rl_exploration_proposal                ok    
0.031        /api/alert/analyze  routing_zone_resolution                ok    
162.68       /api/alert/analyze  referral_history_counts                ok    
0.046        /api/alert/analyze  referral_gate_evaluation               ok    
72.558       /api/alert/analyze  reasoning_generation                   ok    
100.34       /api/alert/analyze  decision_node_and_edge_write           ok    
73.861       /api/alert/analyze  audit_write                            ok    
0.135        /api/alert/analyze  metadata_logging_snapshot_write        ok    
85.054       /api/alert/analyze  campaign_query_find_matching_campaign  ok    
88.189       /api/alert/analyze  campaign_query_fetch_recent_events     ok    
77.949       /api/alert/analyze  campaign_query_check_campaign_exists   ok    
80.319       /api/alert/analyze  campaign_query_create_campaign         ok    
79.856       /api/alert/analyze  campaign_query_member_edge_check       ok    
101.054      /api/alert/analyze  campaign_query_member_edge_create      ok    
76.147       /api/alert/analyze  campaign_query_member_edge_check       ok    
74.325       /api/alert/analyze  campaign_query_member_edge_create      ok    
68.927       /api/alert/analyze  campaign_query_member_edge_check       ok    
88.855       /api/alert/analyze  campaign_query_member_edge_create      ok    
97.414       /api/alert/analyze  campaign_query_member_edge_check       ok    
83.181       /api/alert/analyze  campaign_query_member_edge_create      ok    
91.154       /api/alert/analyze  campaign_query_member_edge_check       ok    
75.045       /api/alert/analyze  campaign_query_member_edge_create      ok    
83.883       /api/alert/analyze  campaign_query_member_edge_check       ok    
76.107       /api/alert/analyze  campaign_query_member_edge_create      ok    
82.503       /api/alert/analyze  campaign_query_member_edge_check       ok    
81.707       /api/alert/analyze  campaign_query_member_edge_create      ok    
89.571       /api/alert/analyze  campaign_query_member_edge_check       ok    
85.679       /api/alert/analyze  campaign_query_member_edge_create      ok    
107.687      /api/alert/analyze  campaign_query_member_edge_check       ok    
101.263      /api/alert/analyze  campaign_query_member_edge_create      ok    
83.011       /api/alert/analyze  campaign_query_member_edge_check       ok    
93.63        /api/alert/analyze  campaign_query_member_edge_create      ok    
80.551       /api/alert/analyze  campaign_query_member_edge_check       ok    
75.484       /api/alert/analyze  campaign_query_member_edge_create      ok    
85.637       /api/alert/analyze  campaign_query_member_edge_check       ok    
82.799       /api/alert/analyze  campaign_query_member_edge_create      ok    
74.164       /api/alert/analyze  campaign_query_member_edge_check       ok    
67.142       /api/alert/analyze  campaign_query_member_edge_create      ok    
83.19        /api/alert/analyze  campaign_query_member_edge_check       ok    
82.744       /api/alert/analyze  campaign_query_member_edge_create      ok    
73.543       /api/alert/analyze  campaign_query_member_edge_check       ok    
68.259       /api/alert/analyze  campaign_query_member_edge_create      ok    
77.997       /api/alert/analyze  campaign_query_member_edge_check       ok    
72.476       /api/alert/analyze  campaign_query_member_edge_create      ok    
62.205       /api/alert/analyze  campaign_query_member_edge_check       ok    
67.534       /api/alert/analyze  campaign_query_member_edge_create      ok    
3171.803     /api/alert/analyze  campaign_correlation_summary           ok    
3249.717     /api/alert/analyze  campaign_correlation                   ok    
0.037        /api/alert/analyze  decision_event_emit                    ok    
71.477       /api/alert/analyze  composite_gate_evaluation              ok    
0.078        /api/alert/analyze  provenance_build                       ok    
70.822       /api/alert/analyze  graph_visualization_fetch              ok    
0.034        /api/alert/analyze  response_context_enrichment            ok    
0.041        /api/alert/analyze  referral_debug_build                   ok    
0.017        /api/alert/analyze  shadow_compare_schedule                ok    
69.547       /api/alert/analyze  cluster_history_fetch                  ok    
0.036        /api/alert/analyze  narrative_context_build                ok    
0.048        /api/alert/analyze  narrative_generation                   ok    
2.759        /api/alert/analyze  response_serialization                 ok    
4388.699     /api/alert/analyze  analyze_request_total                  ok    
0.014        /api/alert/outcome  request_parse                          ok    
0.01         /api/alert/outcome  duplicate_feedback_guard               ok    
72.976       /api/alert/outcome  decision_lookup_and_outcome_update     ok    
0.274        /api/alert/outcome  outcome_audit_write                    ok    
82.814       /api/alert/outcome  learning_state_update                  ok    
354.114      /api/alert/outcome  l5_conservation_write                  ok    
355.382      /api/alert/outcome  conservation_monitor                   ok    
0.218        /api/alert/outcome  profile_scorer_update                  ok    
0.114        /api/alert/outcome  l5_dk_weight_write                     ok    
363.08       /api/alert/outcome  l5_centroid_write                      ok    
0.013        /api/alert/outcome  l5_dk_weight_write                     ok    
0.017        /api/alert/outcome  snapshot_evolution_logging             ok    
85.866       /api/alert/outcome  snapshot_evolution_logging             ok    
0.026        /api/alert/outcome  response_serialization                 ok    
1339.489     /api/alert/outcome  outcome_request_total                  ok    
```

### CAMPAIGN25A-0015
- event_count: 80
- total_observed_ms: 16763.961
- authoritative_total_ms: 4095.443
```text
duration_ms  route               phase                                  status
-----------  ------------------  -------------------------------------  ------
0.017        /api/alert/analyze  scorer_readiness                       ok    
0.007        /api/alert/analyze  request_parse                          ok    
73.325       /api/alert/analyze  alert_lookup                           ok    
74.594       /api/alert/analyze  security_context_lookup                ok    
0.132        /api/alert/analyze  category_resolution                    ok    
313.062      /api/alert/analyze  factor_vector_construction             ok    
0.185        /api/alert/analyze  scorer_decision                        ok    
0.014        /api/alert/analyze  post_scorer_confidence_gate            ok    
0.007        /api/alert/analyze  routing_threshold_lookup               ok    
0.021        /api/alert/analyze  rl_exploration_proposal                ok    
0.054        /api/alert/analyze  routing_zone_resolution                ok    
156.625      /api/alert/analyze  referral_history_counts                ok    
0.042        /api/alert/analyze  referral_gate_evaluation               ok    
72.09        /api/alert/analyze  reasoning_generation                   ok    
75.134       /api/alert/analyze  decision_node_and_edge_write           ok    
74.741       /api/alert/analyze  audit_write                            ok    
3.154        /api/alert/analyze  metadata_logging_snapshot_write        ok    
73.772       /api/alert/analyze  campaign_query_find_matching_campaign  ok    
86.777       /api/alert/analyze  campaign_query_fetch_recent_events     ok    
72.542       /api/alert/analyze  campaign_query_check_campaign_exists   ok    
74.72        /api/alert/analyze  campaign_query_create_campaign         ok    
67.776       /api/alert/analyze  campaign_query_member_edge_check       ok    
83.957       /api/alert/analyze  campaign_query_member_edge_create      ok    
72.217       /api/alert/analyze  campaign_query_member_edge_check       ok    
83.808       /api/alert/analyze  campaign_query_member_edge_create      ok    
71.496       /api/alert/analyze  campaign_query_member_edge_check       ok    
86.938       /api/alert/analyze  campaign_query_member_edge_create      ok    
91.585       /api/alert/analyze  campaign_query_member_edge_check       ok    
70.919       /api/alert/analyze  campaign_query_member_edge_create      ok    
74.818       /api/alert/analyze  campaign_query_member_edge_check       ok    
87.709       /api/alert/analyze  campaign_query_member_edge_create      ok    
72.425       /api/alert/analyze  campaign_query_member_edge_check       ok    
72.792       /api/alert/analyze  campaign_query_member_edge_create      ok    
68.896       /api/alert/analyze  campaign_query_member_edge_check       ok    
76.539       /api/alert/analyze  campaign_query_member_edge_create      ok    
79.247       /api/alert/analyze  campaign_query_member_edge_check       ok    
92.721       /api/alert/analyze  campaign_query_member_edge_create      ok    
70.914       /api/alert/analyze  campaign_query_member_edge_check       ok    
74.855       /api/alert/analyze  campaign_query_member_edge_create      ok    
66.233       /api/alert/analyze  campaign_query_member_edge_check       ok    
94.665       /api/alert/analyze  campaign_query_member_edge_create      ok    
71.144       /api/alert/analyze  campaign_query_member_edge_check       ok    
84.72        /api/alert/analyze  campaign_query_member_edge_create      ok    
75.971       /api/alert/analyze  campaign_query_member_edge_check       ok    
106.914      /api/alert/analyze  campaign_query_member_edge_create      ok    
111.789      /api/alert/analyze  campaign_query_member_edge_check       ok    
80.465       /api/alert/analyze  campaign_query_member_edge_create      ok    
100.189      /api/alert/analyze  campaign_query_member_edge_check       ok    
95.123       /api/alert/analyze  campaign_query_member_edge_create      ok    
83.98        /api/alert/analyze  campaign_query_member_edge_check       ok    
91.098       /api/alert/analyze  campaign_query_member_edge_create      ok    
2830.581     /api/alert/analyze  campaign_correlation_summary           ok    
2931.317     /api/alert/analyze  campaign_correlation                   ok    
0.042        /api/alert/analyze  decision_event_emit                    ok    
85.132       /api/alert/analyze  composite_gate_evaluation              ok    
0.107        /api/alert/analyze  provenance_build                       ok    
96.033       /api/alert/analyze  graph_visualization_fetch              ok    
0.045        /api/alert/analyze  response_context_enrichment            ok    
0.055        /api/alert/analyze  referral_debug_build                   ok    
0.027        /api/alert/analyze  shadow_compare_schedule                ok    
85.555       /api/alert/analyze  cluster_history_fetch                  ok    
0.058        /api/alert/analyze  narrative_context_build                ok    
0.065        /api/alert/analyze  narrative_generation                   ok    
5.179        /api/alert/analyze  response_serialization                 ok    
4095.443     /api/alert/analyze  analyze_request_total                  ok    
0.008        /api/alert/outcome  request_parse                          ok    
0.008        /api/alert/outcome  duplicate_feedback_guard               ok    
101.055      /api/alert/outcome  decision_lookup_and_outcome_update     ok    
0.418        /api/alert/outcome  outcome_audit_write                    ok    
122.692      /api/alert/outcome  learning_state_update                  ok    
383.664      /api/alert/outcome  l5_conservation_write                  ok    
384.938      /api/alert/outcome  conservation_monitor                   ok    
0.152        /api/alert/outcome  profile_scorer_update                  ok    
0.13         /api/alert/outcome  l5_dk_weight_write                     ok    
410.361      /api/alert/outcome  l5_centroid_write                      ok    
0.015        /api/alert/outcome  l5_dk_weight_write                     ok    
0.016        /api/alert/outcome  snapshot_evolution_logging             ok    
80.266       /api/alert/outcome  snapshot_evolution_logging             ok    
0.02         /api/alert/outcome  response_serialization                 ok    
1537.661     /api/alert/outcome  outcome_request_total                  ok    
```

### CAMPAIGN25A-0014
- event_count: 78
- total_observed_ms: 16734.331
- authoritative_total_ms: 3947.704
```text
duration_ms  route               phase                                  status
-----------  ------------------  -------------------------------------  ------
0.02         /api/alert/analyze  scorer_readiness                       ok    
0.009        /api/alert/analyze  request_parse                          ok    
71.868       /api/alert/analyze  alert_lookup                           ok    
71.426       /api/alert/analyze  security_context_lookup                ok    
0.167        /api/alert/analyze  category_resolution                    ok    
315.939      /api/alert/analyze  factor_vector_construction             ok    
0.133        /api/alert/analyze  scorer_decision                        ok    
0.011        /api/alert/analyze  post_scorer_confidence_gate            ok    
0.006        /api/alert/analyze  routing_threshold_lookup               ok    
0.01         /api/alert/analyze  rl_exploration_proposal                ok    
0.014        /api/alert/analyze  routing_zone_resolution                ok    
171.384      /api/alert/analyze  referral_history_counts                ok    
0.053        /api/alert/analyze  referral_gate_evaluation               ok    
88.545       /api/alert/analyze  reasoning_generation                   ok    
66.692       /api/alert/analyze  decision_node_and_edge_write           ok    
66.251       /api/alert/analyze  audit_write                            ok    
0.334        /api/alert/analyze  metadata_logging_snapshot_write        ok    
68.634       /api/alert/analyze  campaign_query_find_matching_campaign  ok    
79.806       /api/alert/analyze  campaign_query_fetch_recent_events     ok    
64.157       /api/alert/analyze  campaign_query_check_campaign_exists   ok    
105.467      /api/alert/analyze  campaign_query_create_campaign         ok    
82.591       /api/alert/analyze  campaign_query_member_edge_check       ok    
86.341       /api/alert/analyze  campaign_query_member_edge_create      ok    
82.71        /api/alert/analyze  campaign_query_member_edge_check       ok    
85.993       /api/alert/analyze  campaign_query_member_edge_create      ok    
93.87        /api/alert/analyze  campaign_query_member_edge_check       ok    
92.549       /api/alert/analyze  campaign_query_member_edge_create      ok    
84.102       /api/alert/analyze  campaign_query_member_edge_check       ok    
99.964       /api/alert/analyze  campaign_query_member_edge_create      ok    
92.438       /api/alert/analyze  campaign_query_member_edge_check       ok    
65.773       /api/alert/analyze  campaign_query_member_edge_create      ok    
68.257       /api/alert/analyze  campaign_query_member_edge_check       ok    
86.29        /api/alert/analyze  campaign_query_member_edge_create      ok    
86.397       /api/alert/analyze  campaign_query_member_edge_check       ok    
94.801       /api/alert/analyze  campaign_query_member_edge_create      ok    
93.105       /api/alert/analyze  campaign_query_member_edge_check       ok    
87.516       /api/alert/analyze  campaign_query_member_edge_create      ok    
92.457       /api/alert/analyze  campaign_query_member_edge_check       ok    
90.347       /api/alert/analyze  campaign_query_member_edge_create      ok    
86.509       /api/alert/analyze  campaign_query_member_edge_check       ok    
80.546       /api/alert/analyze  campaign_query_member_edge_create      ok    
86.321       /api/alert/analyze  campaign_query_member_edge_check       ok    
83.062       /api/alert/analyze  campaign_query_member_edge_create      ok    
70.409       /api/alert/analyze  campaign_query_member_edge_check       ok    
68.928       /api/alert/analyze  campaign_query_member_edge_create      ok    
71.443       /api/alert/analyze  campaign_query_member_edge_check       ok    
78.703       /api/alert/analyze  campaign_query_member_edge_create      ok    
111.662      /api/alert/analyze  campaign_query_member_edge_check       ok    
72.509       /api/alert/analyze  campaign_query_member_edge_create      ok    
2765.005     /api/alert/analyze  campaign_correlation_summary           ok    
2846.268     /api/alert/analyze  campaign_correlation                   ok    
0.03         /api/alert/analyze  decision_event_emit                    ok    
65.746       /api/alert/analyze  composite_gate_evaluation              ok    
0.069        /api/alert/analyze  provenance_build                       ok    
67.742       /api/alert/analyze  graph_visualization_fetch              ok    
0.041        /api/alert/analyze  response_context_enrichment            ok    
0.043        /api/alert/analyze  referral_debug_build                   ok    
0.017        /api/alert/analyze  shadow_compare_schedule                ok    
71.327       /api/alert/analyze  cluster_history_fetch                  ok    
0.044        /api/alert/analyze  narrative_context_build                ok    
0.055        /api/alert/analyze  narrative_generation                   ok    
3.222        /api/alert/analyze  response_serialization                 ok    
3947.704     /api/alert/analyze  analyze_request_total                  ok    
0.012        /api/alert/outcome  request_parse                          ok    
0.013        /api/alert/outcome  duplicate_feedback_guard               ok    
76.833       /api/alert/outcome  decision_lookup_and_outcome_update     ok    
0.349        /api/alert/outcome  outcome_audit_write                    ok    
207.499      /api/alert/outcome  learning_state_update                  ok    
472.539      /api/alert/outcome  l5_conservation_write                  ok    
476.274      /api/alert/outcome  conservation_monitor                   ok    
0.574        /api/alert/outcome  profile_scorer_update                  ok    
0.206        /api/alert/outcome  l5_dk_weight_write                     ok    
437.616      /api/alert/outcome  l5_centroid_write                      ok    
0.018        /api/alert/outcome  l5_dk_weight_write                     ok    
0.023        /api/alert/outcome  snapshot_evolution_logging             ok    
69.584       /api/alert/outcome  snapshot_evolution_logging             ok    
0.032        /api/alert/outcome  response_serialization                 ok    
1678.927     /api/alert/outcome  outcome_request_total                  ok    
```

### CAMPAIGN25A-0013
- event_count: 76
- total_observed_ms: 15568.477
- authoritative_total_ms: 3771.091
```text
duration_ms  route               phase                                  status
-----------  ------------------  -------------------------------------  ------
0.022        /api/alert/analyze  scorer_readiness                       ok    
0.028        /api/alert/analyze  request_parse                          ok    
74.382       /api/alert/analyze  alert_lookup                           ok    
77.504       /api/alert/analyze  security_context_lookup                ok    
0.258        /api/alert/analyze  category_resolution                    ok    
297.323      /api/alert/analyze  factor_vector_construction             ok    
0.25         /api/alert/analyze  scorer_decision                        ok    
0.019        /api/alert/analyze  post_scorer_confidence_gate            ok    
0.01         /api/alert/analyze  routing_threshold_lookup               ok    
0.016        /api/alert/analyze  rl_exploration_proposal                ok    
0.048        /api/alert/analyze  routing_zone_resolution                ok    
147.155      /api/alert/analyze  referral_history_counts                ok    
0.08         /api/alert/analyze  referral_gate_evaluation               ok    
74.11        /api/alert/analyze  reasoning_generation                   ok    
94.764       /api/alert/analyze  decision_node_and_edge_write           ok    
88.446       /api/alert/analyze  audit_write                            ok    
0.205        /api/alert/analyze  metadata_logging_snapshot_write        ok    
68.49        /api/alert/analyze  campaign_query_find_matching_campaign  ok    
79.077       /api/alert/analyze  campaign_query_fetch_recent_events     ok    
72.771       /api/alert/analyze  campaign_query_check_campaign_exists   ok    
75.936       /api/alert/analyze  campaign_query_create_campaign         ok    
87.06        /api/alert/analyze  campaign_query_member_edge_check       ok    
80.89        /api/alert/analyze  campaign_query_member_edge_create      ok    
80.311       /api/alert/analyze  campaign_query_member_edge_check       ok    
80.263       /api/alert/analyze  campaign_query_member_edge_create      ok    
83.7         /api/alert/analyze  campaign_query_member_edge_check       ok    
76.399       /api/alert/analyze  campaign_query_member_edge_create      ok    
75.047       /api/alert/analyze  campaign_query_member_edge_check       ok    
82.153       /api/alert/analyze  campaign_query_member_edge_create      ok    
82.462       /api/alert/analyze  campaign_query_member_edge_check       ok    
102.291      /api/alert/analyze  campaign_query_member_edge_create      ok    
96.48        /api/alert/analyze  campaign_query_member_edge_check       ok    
97.577       /api/alert/analyze  campaign_query_member_edge_create      ok    
67.957       /api/alert/analyze  campaign_query_member_edge_check       ok    
78.087       /api/alert/analyze  campaign_query_member_edge_create      ok    
87.438       /api/alert/analyze  campaign_query_member_edge_check       ok    
95.589       /api/alert/analyze  campaign_query_member_edge_create      ok    
98.551       /api/alert/analyze  campaign_query_member_edge_check       ok    
84.704       /api/alert/analyze  campaign_query_member_edge_create      ok    
68.325       /api/alert/analyze  campaign_query_member_edge_check       ok    
72.272       /api/alert/analyze  campaign_query_member_edge_create      ok    
90.76        /api/alert/analyze  campaign_query_member_edge_check       ok    
83.699       /api/alert/analyze  campaign_query_member_edge_create      ok    
77.751       /api/alert/analyze  campaign_query_member_edge_check       ok    
67.643       /api/alert/analyze  campaign_query_member_edge_create      ok    
70.341       /api/alert/analyze  campaign_query_member_edge_check       ok    
83.376       /api/alert/analyze  campaign_query_member_edge_create      ok    
2507.878     /api/alert/analyze  campaign_correlation_summary           ok    
2599.312     /api/alert/analyze  campaign_correlation                   ok    
0.04         /api/alert/analyze  decision_event_emit                    ok    
82.506       /api/alert/analyze  composite_gate_evaluation              ok    
0.079        /api/alert/analyze  provenance_build                       ok    
93.406       /api/alert/analyze  graph_visualization_fetch              ok    
0.035        /api/alert/analyze  response_context_enrichment            ok    
0.04         /api/alert/analyze  referral_debug_build                   ok    
0.016        /api/alert/analyze  shadow_compare_schedule                ok    
81.237       /api/alert/analyze  cluster_history_fetch                  ok    
0.043        /api/alert/analyze  narrative_context_build                ok    
0.059        /api/alert/analyze  narrative_generation                   ok    
3.531        /api/alert/analyze  response_serialization                 ok    
3771.091     /api/alert/analyze  analyze_request_total                  ok    
0.012        /api/alert/outcome  request_parse                          ok    
0.028        /api/alert/outcome  duplicate_feedback_guard               ok    
79.331       /api/alert/outcome  decision_lookup_and_outcome_update     ok    
0.389        /api/alert/outcome  outcome_audit_write                    ok    
144.361      /api/alert/outcome  learning_state_update                  ok    
419.383      /api/alert/outcome  l5_conservation_write                  ok    
422.802      /api/alert/outcome  conservation_monitor                   ok    
0.333        /api/alert/outcome  profile_scorer_update                  ok    
0.227        /api/alert/outcome  l5_dk_weight_write                     ok    
431.021      /api/alert/outcome  l5_centroid_write                      ok    
0.015        /api/alert/outcome  l5_dk_weight_write                     ok    
0.017        /api/alert/outcome  snapshot_evolution_logging             ok    
75.9         /api/alert/outcome  snapshot_evolution_logging             ok    
0.046        /api/alert/outcome  response_serialization                 ok    
1553.319     /api/alert/outcome  outcome_request_total                  ok    
```

### CAMPAIGN25A-0012
- event_count: 74
- total_observed_ms: 14390.935
- authoritative_total_ms: 3440.108
```text
duration_ms  route               phase                                  status
-----------  ------------------  -------------------------------------  ------
0.011        /api/alert/analyze  scorer_readiness                       ok    
0.005        /api/alert/analyze  request_parse                          ok    
86.349       /api/alert/analyze  alert_lookup                           ok    
76.204       /api/alert/analyze  security_context_lookup                ok    
0.13         /api/alert/analyze  category_resolution                    ok    
310.433      /api/alert/analyze  factor_vector_construction             ok    
0.197        /api/alert/analyze  scorer_decision                        ok    
0.019        /api/alert/analyze  post_scorer_confidence_gate            ok    
0.009        /api/alert/analyze  routing_threshold_lookup               ok    
0.015        /api/alert/analyze  rl_exploration_proposal                ok    
0.014        /api/alert/analyze  routing_zone_resolution                ok    
164.793      /api/alert/analyze  referral_history_counts                ok    
0.029        /api/alert/analyze  referral_gate_evaluation               ok    
68.301       /api/alert/analyze  reasoning_generation                   ok    
73.351       /api/alert/analyze  decision_node_and_edge_write           ok    
71.974       /api/alert/analyze  audit_write                            ok    
0.311        /api/alert/analyze  metadata_logging_snapshot_write        ok    
91.569       /api/alert/analyze  campaign_query_find_matching_campaign  ok    
76.479       /api/alert/analyze  campaign_query_fetch_recent_events     ok    
90.139       /api/alert/analyze  campaign_query_check_campaign_exists   ok    
67.524       /api/alert/analyze  campaign_query_create_campaign         ok    
78.354       /api/alert/analyze  campaign_query_member_edge_check       ok    
105.581      /api/alert/analyze  campaign_query_member_edge_create      ok    
81.413       /api/alert/analyze  campaign_query_member_edge_check       ok    
79.336       /api/alert/analyze  campaign_query_member_edge_create      ok    
78.869       /api/alert/analyze  campaign_query_member_edge_check       ok    
79.474       /api/alert/analyze  campaign_query_member_edge_create      ok    
84.24        /api/alert/analyze  campaign_query_member_edge_check       ok    
83.299       /api/alert/analyze  campaign_query_member_edge_create      ok    
80.276       /api/alert/analyze  campaign_query_member_edge_check       ok    
79.518       /api/alert/analyze  campaign_query_member_edge_create      ok    
90.691       /api/alert/analyze  campaign_query_member_edge_check       ok    
74.374       /api/alert/analyze  campaign_query_member_edge_create      ok    
61.281       /api/alert/analyze  campaign_query_member_edge_check       ok    
62.646       /api/alert/analyze  campaign_query_member_edge_create      ok    
79.049       /api/alert/analyze  campaign_query_member_edge_check       ok    
85.68        /api/alert/analyze  campaign_query_member_edge_create      ok    
75.618       /api/alert/analyze  campaign_query_member_edge_check       ok    
67.827       /api/alert/analyze  campaign_query_member_edge_create      ok    
71.061       /api/alert/analyze  campaign_query_member_edge_check       ok    
67.13        /api/alert/analyze  campaign_query_member_edge_create      ok    
69.967       /api/alert/analyze  campaign_query_member_edge_check       ok    
77.696       /api/alert/analyze  campaign_query_member_edge_create      ok    
68.965       /api/alert/analyze  campaign_query_member_edge_check       ok    
73.888       /api/alert/analyze  campaign_query_member_edge_create      ok    
2244.162     /api/alert/analyze  campaign_correlation_summary           ok    
2318.404     /api/alert/analyze  campaign_correlation                   ok    
0.039        /api/alert/analyze  decision_event_emit                    ok    
71.838       /api/alert/analyze  composite_gate_evaluation              ok    
0.191        /api/alert/analyze  provenance_build                       ok    
75.633       /api/alert/analyze  graph_visualization_fetch              ok    
0.042        /api/alert/analyze  response_context_enrichment            ok    
0.043        /api/alert/analyze  referral_debug_build                   ok    
0.02         /api/alert/analyze  shadow_compare_schedule                ok    
73.19        /api/alert/analyze  cluster_history_fetch                  ok    
0.049        /api/alert/analyze  narrative_context_build                ok    
0.067        /api/alert/analyze  narrative_generation                   ok    
3.714        /api/alert/analyze  response_serialization                 ok    
3440.108     /api/alert/analyze  analyze_request_total                  ok    
0.015        /api/alert/outcome  request_parse                          ok    
0.012        /api/alert/outcome  duplicate_feedback_guard               ok    
79.55        /api/alert/outcome  decision_lookup_and_outcome_update     ok    
0.329        /api/alert/outcome  outcome_audit_write                    ok    
152.419      /api/alert/outcome  learning_state_update                  ok    
384.997      /api/alert/outcome  l5_conservation_write                  ok    
387.443      /api/alert/outcome  conservation_monitor                   ok    
0.221        /api/alert/outcome  profile_scorer_update                  ok    
0.187        /api/alert/outcome  l5_dk_weight_write                     ok    
422.836      /api/alert/outcome  l5_centroid_write                      ok    
0.023        /api/alert/outcome  l5_dk_weight_write                     ok    
0.027        /api/alert/outcome  snapshot_evolution_logging             ok    
100.613      /api/alert/outcome  snapshot_evolution_logging             ok    
0.035        /api/alert/outcome  response_serialization                 ok    
1600.639     /api/alert/outcome  outcome_request_total                  ok    
```

### CAMPAIGN25A-0011
- event_count: 72
- total_observed_ms: 13463.843
- authoritative_total_ms: 3236.352
```text
duration_ms  route               phase                                  status
-----------  ------------------  -------------------------------------  ------
0.319        /api/alert/analyze  scorer_readiness                       ok    
0.009        /api/alert/analyze  request_parse                          ok    
66.792       /api/alert/analyze  alert_lookup                           ok    
63.623       /api/alert/analyze  security_context_lookup                ok    
0.123        /api/alert/analyze  category_resolution                    ok    
291.621      /api/alert/analyze  factor_vector_construction             ok    
0.117        /api/alert/analyze  scorer_decision                        ok    
0.01         /api/alert/analyze  post_scorer_confidence_gate            ok    
0.005        /api/alert/analyze  routing_threshold_lookup               ok    
0.012        /api/alert/analyze  rl_exploration_proposal                ok    
0.009        /api/alert/analyze  routing_zone_resolution                ok    
154.967      /api/alert/analyze  referral_history_counts                ok    
0.039        /api/alert/analyze  referral_gate_evaluation               ok    
72.255       /api/alert/analyze  reasoning_generation                   ok    
96.623       /api/alert/analyze  decision_node_and_edge_write           ok    
81.439       /api/alert/analyze  audit_write                            ok    
0.977        /api/alert/analyze  metadata_logging_snapshot_write        ok    
70.086       /api/alert/analyze  campaign_query_find_matching_campaign  ok    
65.896       /api/alert/analyze  campaign_query_fetch_recent_events     ok    
61.865       /api/alert/analyze  campaign_query_check_campaign_exists   ok    
72.836       /api/alert/analyze  campaign_query_create_campaign         ok    
75.428       /api/alert/analyze  campaign_query_member_edge_check       ok    
78.67        /api/alert/analyze  campaign_query_member_edge_create      ok    
77.723       /api/alert/analyze  campaign_query_member_edge_check       ok    
88.078       /api/alert/analyze  campaign_query_member_edge_create      ok    
82.472       /api/alert/analyze  campaign_query_member_edge_check       ok    
85.655       /api/alert/analyze  campaign_query_member_edge_create      ok    
62.25        /api/alert/analyze  campaign_query_member_edge_check       ok    
61.232       /api/alert/analyze  campaign_query_member_edge_create      ok    
73.708       /api/alert/analyze  campaign_query_member_edge_check       ok    
92.583       /api/alert/analyze  campaign_query_member_edge_create      ok    
76.028       /api/alert/analyze  campaign_query_member_edge_check       ok    
81.031       /api/alert/analyze  campaign_query_member_edge_create      ok    
72.857       /api/alert/analyze  campaign_query_member_edge_check       ok    
81.663       /api/alert/analyze  campaign_query_member_edge_create      ok    
65.392       /api/alert/analyze  campaign_query_member_edge_check       ok    
92.82        /api/alert/analyze  campaign_query_member_edge_create      ok    
75.626       /api/alert/analyze  campaign_query_member_edge_check       ok    
83.982       /api/alert/analyze  campaign_query_member_edge_create      ok    
81.919       /api/alert/analyze  campaign_query_member_edge_check       ok    
82.718       /api/alert/analyze  campaign_query_member_edge_create      ok    
80.813       /api/alert/analyze  campaign_query_member_edge_check       ok    
74.382       /api/alert/analyze  campaign_query_member_edge_create      ok    
2045.158     /api/alert/analyze  campaign_correlation_summary           ok    
2137.865     /api/alert/analyze  campaign_correlation                   ok    
0.044        /api/alert/analyze  decision_event_emit                    ok    
81.968       /api/alert/analyze  composite_gate_evaluation              ok    
0.362        /api/alert/analyze  provenance_build                       ok    
71.53        /api/alert/analyze  graph_visualization_fetch              ok    
0.037        /api/alert/analyze  response_context_enrichment            ok    
0.044        /api/alert/analyze  referral_debug_build                   ok    
0.02         /api/alert/analyze  shadow_compare_schedule                ok    
68.53        /api/alert/analyze  cluster_history_fetch                  ok    
0.035        /api/alert/analyze  narrative_context_build                ok    
0.043        /api/alert/analyze  narrative_generation                   ok    
2.633        /api/alert/analyze  response_serialization                 ok    
3236.352     /api/alert/analyze  analyze_request_total                  ok    
0.02         /api/alert/outcome  request_parse                          ok    
0.024        /api/alert/outcome  duplicate_feedback_guard               ok    
85.511       /api/alert/outcome  decision_lookup_and_outcome_update     ok    
0.965        /api/alert/outcome  outcome_audit_write                    ok    
116.176      /api/alert/outcome  learning_state_update                  ok    
432.642      /api/alert/outcome  l5_conservation_write                  ok    
434.078      /api/alert/outcome  conservation_monitor                   ok    
0.157        /api/alert/outcome  profile_scorer_update                  ok    
0.109        /api/alert/outcome  l5_dk_weight_write                     ok    
360.83       /api/alert/outcome  l5_centroid_write                      ok    
0.012        /api/alert/outcome  l5_dk_weight_write                     ok    
0.017        /api/alert/outcome  snapshot_evolution_logging             ok    
79.015       /api/alert/outcome  snapshot_evolution_logging             ok    
0.023        /api/alert/outcome  response_serialization                 ok    
1482.99      /api/alert/outcome  outcome_request_total                  ok    
```

### CAMPAIGN25A-0010
- event_count: 70
- total_observed_ms: 12786.478
- authoritative_total_ms: 3211.302
```text
duration_ms  route               phase                                  status
-----------  ------------------  -------------------------------------  ------
0.019        /api/alert/analyze  scorer_readiness                       ok    
0.007        /api/alert/analyze  request_parse                          ok    
92.949       /api/alert/analyze  alert_lookup                           ok    
69.218       /api/alert/analyze  security_context_lookup                ok    
0.118        /api/alert/analyze  category_resolution                    ok    
306.803      /api/alert/analyze  factor_vector_construction             ok    
0.189        /api/alert/analyze  scorer_decision                        ok    
0.013        /api/alert/analyze  post_scorer_confidence_gate            ok    
0.008        /api/alert/analyze  routing_threshold_lookup               ok    
0.023        /api/alert/analyze  rl_exploration_proposal                ok    
0.016        /api/alert/analyze  routing_zone_resolution                ok    
210.557      /api/alert/analyze  referral_history_counts                ok    
0.041        /api/alert/analyze  referral_gate_evaluation               ok    
72.182       /api/alert/analyze  reasoning_generation                   ok    
75.24        /api/alert/analyze  decision_node_and_edge_write           ok    
92.189       /api/alert/analyze  audit_write                            ok    
0.374        /api/alert/analyze  metadata_logging_snapshot_write        ok    
82.122       /api/alert/analyze  campaign_query_find_matching_campaign  ok    
80.66        /api/alert/analyze  campaign_query_fetch_recent_events     ok    
72.278       /api/alert/analyze  campaign_query_check_campaign_exists   ok    
76.777       /api/alert/analyze  campaign_query_create_campaign         ok    
80.455       /api/alert/analyze  campaign_query_member_edge_check       ok    
96.742       /api/alert/analyze  campaign_query_member_edge_create      ok    
88.65        /api/alert/analyze  campaign_query_member_edge_check       ok    
89.122       /api/alert/analyze  campaign_query_member_edge_create      ok    
69.717       /api/alert/analyze  campaign_query_member_edge_check       ok    
71.062       /api/alert/analyze  campaign_query_member_edge_create      ok    
90.483       /api/alert/analyze  campaign_query_member_edge_check       ok    
76.81        /api/alert/analyze  campaign_query_member_edge_create      ok    
83.375       /api/alert/analyze  campaign_query_member_edge_check       ok    
72.14        /api/alert/analyze  campaign_query_member_edge_create      ok    
100.804      /api/alert/analyze  campaign_query_member_edge_check       ok    
85.756       /api/alert/analyze  campaign_query_member_edge_create      ok    
78.155       /api/alert/analyze  campaign_query_member_edge_check       ok    
82.231       /api/alert/analyze  campaign_query_member_edge_create      ok    
77.493       /api/alert/analyze  campaign_query_member_edge_check       ok    
71.063       /api/alert/analyze  campaign_query_member_edge_create      ok    
64.734       /api/alert/analyze  campaign_query_member_edge_check       ok    
72.591       /api/alert/analyze  campaign_query_member_edge_create      ok    
72.662       /api/alert/analyze  campaign_query_member_edge_check       ok    
67.428       /api/alert/analyze  campaign_query_member_edge_create      ok    
1952.062     /api/alert/analyze  campaign_correlation_summary           ok    
2040.067     /api/alert/analyze  campaign_correlation                   ok    
0.022        /api/alert/analyze  decision_event_emit                    ok    
62.729       /api/alert/analyze  composite_gate_evaluation              ok    
0.06         /api/alert/analyze  provenance_build                       ok    
65.791       /api/alert/analyze  graph_visualization_fetch              ok    
0.023        /api/alert/analyze  response_context_enrichment            ok    
0.032        /api/alert/analyze  referral_debug_build                   ok    
0.014        /api/alert/analyze  shadow_compare_schedule                ok    
78.933       /api/alert/analyze  cluster_history_fetch                  ok    
0.031        /api/alert/analyze  narrative_context_build                ok    
0.037        /api/alert/analyze  narrative_generation                   ok    
1.945        /api/alert/analyze  response_serialization                 ok    
3211.302     /api/alert/analyze  analyze_request_total                  ok    
0.01         /api/alert/outcome  request_parse                          ok    
0.009        /api/alert/outcome  duplicate_feedback_guard               ok    
65.819       /api/alert/outcome  decision_lookup_and_outcome_update     ok    
0.195        /api/alert/outcome  outcome_audit_write                    ok    
66.703       /api/alert/outcome  learning_state_update                  ok    
364.897      /api/alert/outcome  l5_conservation_write                  ok    
366.098      /api/alert/outcome  conservation_monitor                   ok    
0.144        /api/alert/outcome  profile_scorer_update                  ok    
0.108        /api/alert/outcome  l5_dk_weight_write                     ok    
341.1        /api/alert/outcome  l5_centroid_write                      ok    
0.014        /api/alert/outcome  l5_dk_weight_write                     ok    
0.016        /api/alert/outcome  snapshot_evolution_logging             ok    
66.837       /api/alert/outcome  snapshot_evolution_logging             ok    
0.019        /api/alert/outcome  response_serialization                 ok    
1278.205     /api/alert/outcome  outcome_request_total                  ok    
```

### CAMPAIGN25A-0009
- event_count: 68
- total_observed_ms: 13139.56
- authoritative_total_ms: 3181.84
```text
duration_ms  route               phase                                  status
-----------  ------------------  -------------------------------------  ------
0.031        /api/alert/analyze  scorer_readiness                       ok    
0.016        /api/alert/analyze  request_parse                          ok    
88.01        /api/alert/analyze  alert_lookup                           ok    
87.267       /api/alert/analyze  security_context_lookup                ok    
0.135        /api/alert/analyze  category_resolution                    ok    
307.966      /api/alert/analyze  factor_vector_construction             ok    
0.53         /api/alert/analyze  scorer_decision                        ok    
0.036        /api/alert/analyze  post_scorer_confidence_gate            ok    
0.018        /api/alert/analyze  routing_threshold_lookup               ok    
0.039        /api/alert/analyze  rl_exploration_proposal                ok    
0.03         /api/alert/analyze  routing_zone_resolution                ok    
165.244      /api/alert/analyze  referral_history_counts                ok    
0.044        /api/alert/analyze  referral_gate_evaluation               ok    
68.806       /api/alert/analyze  reasoning_generation                   ok    
101.474      /api/alert/analyze  decision_node_and_edge_write           ok    
96.34        /api/alert/analyze  audit_write                            ok    
0.252        /api/alert/analyze  metadata_logging_snapshot_write        ok    
73.609       /api/alert/analyze  campaign_query_find_matching_campaign  ok    
72.23        /api/alert/analyze  campaign_query_fetch_recent_events     ok    
82.497       /api/alert/analyze  campaign_query_check_campaign_exists   ok    
86.721       /api/alert/analyze  campaign_query_create_campaign         ok    
77.056       /api/alert/analyze  campaign_query_member_edge_check       ok    
86.557       /api/alert/analyze  campaign_query_member_edge_create      ok    
93.647       /api/alert/analyze  campaign_query_member_edge_check       ok    
69.097       /api/alert/analyze  campaign_query_member_edge_create      ok    
78.017       /api/alert/analyze  campaign_query_member_edge_check       ok    
70.65        /api/alert/analyze  campaign_query_member_edge_create      ok    
83.718       /api/alert/analyze  campaign_query_member_edge_check       ok    
80.288       /api/alert/analyze  campaign_query_member_edge_create      ok    
69.34        /api/alert/analyze  campaign_query_member_edge_check       ok    
89.467       /api/alert/analyze  campaign_query_member_edge_create      ok    
83.619       /api/alert/analyze  campaign_query_member_edge_check       ok    
99.292       /api/alert/analyze  campaign_query_member_edge_create      ok    
84.137       /api/alert/analyze  campaign_query_member_edge_check       ok    
96.96        /api/alert/analyze  campaign_query_member_edge_create      ok    
78.87        /api/alert/analyze  campaign_query_member_edge_check       ok    
87.263       /api/alert/analyze  campaign_query_member_edge_create      ok    
99.785       /api/alert/analyze  campaign_query_member_edge_check       ok    
90.999       /api/alert/analyze  campaign_query_member_edge_create      ok    
1878.107     /api/alert/analyze  campaign_correlation_summary           ok    
1970.228     /api/alert/analyze  campaign_correlation                   ok    
0.046        /api/alert/analyze  decision_event_emit                    ok    
74.006       /api/alert/analyze  composite_gate_evaluation              ok    
0.097        /api/alert/analyze  provenance_build                       ok    
85.792       /api/alert/analyze  graph_visualization_fetch              ok    
0.032        /api/alert/analyze  response_context_enrichment            ok    
0.044        /api/alert/analyze  referral_debug_build                   ok    
0.021        /api/alert/analyze  shadow_compare_schedule                ok    
67.427       /api/alert/analyze  cluster_history_fetch                  ok    
0.053        /api/alert/analyze  narrative_context_build                ok    
0.04         /api/alert/analyze  narrative_generation                   ok    
3.431        /api/alert/analyze  response_serialization                 ok    
3181.84      /api/alert/analyze  analyze_request_total                  ok    
0.006        /api/alert/outcome  request_parse                          ok    
0.015        /api/alert/outcome  duplicate_feedback_guard               ok    
93.799       /api/alert/outcome  decision_lookup_and_outcome_update     ok    
0.516        /api/alert/outcome  outcome_audit_write                    ok    
158.665      /api/alert/outcome  learning_state_update                  ok    
400.414      /api/alert/outcome  l5_conservation_write                  ok    
402.046      /api/alert/outcome  conservation_monitor                   ok    
0.143        /api/alert/outcome  profile_scorer_update                  ok    
0.211        /api/alert/outcome  l5_dk_weight_write                     ok    
392.082      /api/alert/outcome  l5_centroid_write                      ok    
0.019        /api/alert/outcome  l5_dk_weight_write                     ok    
0.031        /api/alert/outcome  snapshot_evolution_logging             ok    
90.365       /api/alert/outcome  snapshot_evolution_logging             ok    
0.062        /api/alert/outcome  response_serialization                 ok    
1589.965     /api/alert/outcome  outcome_request_total                  ok    
```

### CAMPAIGN25A-0007
- event_count: 64
- total_observed_ms: 12384.483
- authoritative_total_ms: 3039.07
```text
duration_ms  route               phase                                  status
-----------  ------------------  -------------------------------------  ------
0.017        /api/alert/analyze  scorer_readiness                       ok    
0.006        /api/alert/analyze  request_parse                          ok    
89.305       /api/alert/analyze  alert_lookup                           ok    
92.61        /api/alert/analyze  security_context_lookup                ok    
0.129        /api/alert/analyze  category_resolution                    ok    
332.589      /api/alert/analyze  factor_vector_construction             ok    
0.355        /api/alert/analyze  scorer_decision                        ok    
0.029        /api/alert/analyze  post_scorer_confidence_gate            ok    
0.007        /api/alert/analyze  routing_threshold_lookup               ok    
0.013        /api/alert/analyze  rl_exploration_proposal                ok    
0.011        /api/alert/analyze  routing_zone_resolution                ok    
210.718      /api/alert/analyze  referral_history_counts                ok    
0.044        /api/alert/analyze  referral_gate_evaluation               ok    
71.218       /api/alert/analyze  reasoning_generation                   ok    
83.565       /api/alert/analyze  decision_node_and_edge_write           ok    
85.281       /api/alert/analyze  audit_write                            ok    
0.237        /api/alert/analyze  metadata_logging_snapshot_write        ok    
88.762       /api/alert/analyze  campaign_query_find_matching_campaign  ok    
93.964       /api/alert/analyze  campaign_query_fetch_recent_events     ok    
73.594       /api/alert/analyze  campaign_query_check_campaign_exists   ok    
96.6         /api/alert/analyze  campaign_query_create_campaign         ok    
95.342       /api/alert/analyze  campaign_query_member_edge_check       ok    
92.537       /api/alert/analyze  campaign_query_member_edge_create      ok    
76.11        /api/alert/analyze  campaign_query_member_edge_check       ok    
85.883       /api/alert/analyze  campaign_query_member_edge_create      ok    
82.656       /api/alert/analyze  campaign_query_member_edge_check       ok    
96.133       /api/alert/analyze  campaign_query_member_edge_create      ok    
96.768       /api/alert/analyze  campaign_query_member_edge_check       ok    
77.156       /api/alert/analyze  campaign_query_member_edge_create      ok    
95.537       /api/alert/analyze  campaign_query_member_edge_check       ok    
88.476       /api/alert/analyze  campaign_query_member_edge_create      ok    
87.031       /api/alert/analyze  campaign_query_member_edge_check       ok    
78.691       /api/alert/analyze  campaign_query_member_edge_create      ok    
93.645       /api/alert/analyze  campaign_query_member_edge_check       ok    
85.148       /api/alert/analyze  campaign_query_member_edge_create      ok    
1629.98      /api/alert/analyze  campaign_correlation_summary           ok    
1718.784     /api/alert/analyze  campaign_correlation                   ok    
0.039        /api/alert/analyze  decision_event_emit                    ok    
83.629       /api/alert/analyze  composite_gate_evaluation              ok    
0.066        /api/alert/analyze  provenance_build                       ok    
83.075       /api/alert/analyze  graph_visualization_fetch              ok    
0.024        /api/alert/analyze  response_context_enrichment            ok    
0.03         /api/alert/analyze  referral_debug_build                   ok    
0.016        /api/alert/analyze  shadow_compare_schedule                ok    
112.783      /api/alert/analyze  cluster_history_fetch                  ok    
0.086        /api/alert/analyze  narrative_context_build                ok    
0.18         /api/alert/analyze  narrative_generation                   ok    
15.388       /api/alert/analyze  response_serialization                 ok    
3039.07      /api/alert/analyze  analyze_request_total                  ok    
0.029        /api/alert/outcome  request_parse                          ok    
0.032        /api/alert/outcome  duplicate_feedback_guard               ok    
88.96        /api/alert/outcome  decision_lookup_and_outcome_update     ok    
1.348        /api/alert/outcome  outcome_audit_write                    ok    
128.965      /api/alert/outcome  learning_state_update                  ok    
393.591      /api/alert/outcome  l5_conservation_write                  ok    
395.156      /api/alert/outcome  conservation_monitor                   ok    
0.158        /api/alert/outcome  profile_scorer_update                  ok    
0.148        /api/alert/outcome  l5_dk_weight_write                     ok    
437.67       /api/alert/outcome  l5_centroid_write                      ok    
0.033        /api/alert/outcome  l5_dk_weight_write                     ok    
0.02         /api/alert/outcome  snapshot_evolution_logging             ok    
103.555      /api/alert/outcome  snapshot_evolution_logging             ok    
0.026        /api/alert/outcome  response_serialization                 ok    
1601.475     /api/alert/outcome  outcome_request_total                  ok    
```

### CAMPAIGN25A-0008
- event_count: 66
- total_observed_ms: 11851.34
- authoritative_total_ms: 2843.608
```text
duration_ms  route               phase                                  status
-----------  ------------------  -------------------------------------  ------
0.015        /api/alert/analyze  scorer_readiness                       ok    
0.006        /api/alert/analyze  request_parse                          ok    
78.806       /api/alert/analyze  alert_lookup                           ok    
96.828       /api/alert/analyze  security_context_lookup                ok    
0.255        /api/alert/analyze  category_resolution                    ok    
301.912      /api/alert/analyze  factor_vector_construction             ok    
0.205        /api/alert/analyze  scorer_decision                        ok    
0.015        /api/alert/analyze  post_scorer_confidence_gate            ok    
0.007        /api/alert/analyze  routing_threshold_lookup               ok    
0.013        /api/alert/analyze  rl_exploration_proposal                ok    
0.02         /api/alert/analyze  routing_zone_resolution                ok    
144.665      /api/alert/analyze  referral_history_counts                ok    
0.07         /api/alert/analyze  referral_gate_evaluation               ok    
71.526       /api/alert/analyze  reasoning_generation                   ok    
95.298       /api/alert/analyze  decision_node_and_edge_write           ok    
83.903       /api/alert/analyze  audit_write                            ok    
0.151        /api/alert/analyze  metadata_logging_snapshot_write        ok    
76.055       /api/alert/analyze  campaign_query_find_matching_campaign  ok    
69.007       /api/alert/analyze  campaign_query_fetch_recent_events     ok    
82.285       /api/alert/analyze  campaign_query_check_campaign_exists   ok    
86.53        /api/alert/analyze  campaign_query_create_campaign         ok    
79.916       /api/alert/analyze  campaign_query_member_edge_check       ok    
83.772       /api/alert/analyze  campaign_query_member_edge_create      ok    
84.187       /api/alert/analyze  campaign_query_member_edge_check       ok    
84.57        /api/alert/analyze  campaign_query_member_edge_create      ok    
71.156       /api/alert/analyze  campaign_query_member_edge_check       ok    
74.212       /api/alert/analyze  campaign_query_member_edge_create      ok    
86.081       /api/alert/analyze  campaign_query_member_edge_check       ok    
73.231       /api/alert/analyze  campaign_query_member_edge_create      ok    
87.769       /api/alert/analyze  campaign_query_member_edge_check       ok    
68.566       /api/alert/analyze  campaign_query_member_edge_create      ok    
84.482       /api/alert/analyze  campaign_query_member_edge_check       ok    
78.54        /api/alert/analyze  campaign_query_member_edge_create      ok    
77.345       /api/alert/analyze  campaign_query_member_edge_check       ok    
86.379       /api/alert/analyze  campaign_query_member_edge_create      ok    
71.078       /api/alert/analyze  campaign_query_member_edge_check       ok    
80.842       /api/alert/analyze  campaign_query_member_edge_create      ok    
1626.816     /api/alert/analyze  campaign_correlation_summary           ok    
1695.047     /api/alert/analyze  campaign_correlation                   ok    
0.025        /api/alert/analyze  decision_event_emit                    ok    
63.64        /api/alert/analyze  composite_gate_evaluation              ok    
0.058        /api/alert/analyze  provenance_build                       ok    
69.825       /api/alert/analyze  graph_visualization_fetch              ok    
0.021        /api/alert/analyze  response_context_enrichment            ok    
0.021        /api/alert/analyze  referral_debug_build                   ok    
0.01         /api/alert/analyze  shadow_compare_schedule                ok    
94.372       /api/alert/analyze  cluster_history_fetch                  ok    
0.032        /api/alert/analyze  narrative_context_build                ok    
0.06         /api/alert/analyze  narrative_generation                   ok    
3.762        /api/alert/analyze  response_serialization                 ok    
2843.608     /api/alert/analyze  analyze_request_total                  ok    
0.017        /api/alert/outcome  request_parse                          ok    
0.019        /api/alert/outcome  duplicate_feedback_guard               ok    
80.339       /api/alert/outcome  decision_lookup_and_outcome_update     ok    
0.675        /api/alert/outcome  outcome_audit_write                    ok    
77.738       /api/alert/outcome  learning_state_update                  ok    
418.432      /api/alert/outcome  l5_conservation_write                  ok    
420.403      /api/alert/outcome  conservation_monitor                   ok    
0.585        /api/alert/outcome  profile_scorer_update                  ok    
0.112        /api/alert/outcome  l5_dk_weight_write                     ok    
433.673      /api/alert/outcome  l5_centroid_write                      ok    
0.029        /api/alert/outcome  l5_dk_weight_write                     ok    
0.041        /api/alert/outcome  snapshot_evolution_logging             ok    
79.839       /api/alert/outcome  snapshot_evolution_logging             ok    
0.029        /api/alert/outcome  response_serialization                 ok    
1482.414     /api/alert/outcome  outcome_request_total                  ok    
```

### CAMPAIGN25A-0006
- event_count: 62
- total_observed_ms: 11222.289
- authoritative_total_ms: 2722.825
```text
duration_ms  route               phase                                  status
-----------  ------------------  -------------------------------------  ------
0.033        /api/alert/analyze  scorer_readiness                       ok    
0.008        /api/alert/analyze  request_parse                          ok    
69.929       /api/alert/analyze  alert_lookup                           ok    
69.286       /api/alert/analyze  security_context_lookup                ok    
0.127        /api/alert/analyze  category_resolution                    ok    
344.112      /api/alert/analyze  factor_vector_construction             ok    
0.539        /api/alert/analyze  scorer_decision                        ok    
0.04         /api/alert/analyze  post_scorer_confidence_gate            ok    
0.033        /api/alert/analyze  routing_threshold_lookup               ok    
0.033        /api/alert/analyze  rl_exploration_proposal                ok    
0.076        /api/alert/analyze  routing_zone_resolution                ok    
174.975      /api/alert/analyze  referral_history_counts                ok    
0.075        /api/alert/analyze  referral_gate_evaluation               ok    
103.51       /api/alert/analyze  reasoning_generation                   ok    
83.065       /api/alert/analyze  decision_node_and_edge_write           ok    
85.688       /api/alert/analyze  audit_write                            ok    
0.463        /api/alert/analyze  metadata_logging_snapshot_write        ok    
91.929       /api/alert/analyze  campaign_query_find_matching_campaign  ok    
85.106       /api/alert/analyze  campaign_query_fetch_recent_events     ok    
90.439       /api/alert/analyze  campaign_query_check_campaign_exists   ok    
81.371       /api/alert/analyze  campaign_query_create_campaign         ok    
77.726       /api/alert/analyze  campaign_query_member_edge_check       ok    
76.58        /api/alert/analyze  campaign_query_member_edge_create      ok    
76.713       /api/alert/analyze  campaign_query_member_edge_check       ok    
91.866       /api/alert/analyze  campaign_query_member_edge_create      ok    
88.716       /api/alert/analyze  campaign_query_member_edge_check       ok    
81.845       /api/alert/analyze  campaign_query_member_edge_create      ok    
76.846       /api/alert/analyze  campaign_query_member_edge_check       ok    
83.84        /api/alert/analyze  campaign_query_member_edge_create      ok    
90.357       /api/alert/analyze  campaign_query_member_edge_check       ok    
81.169       /api/alert/analyze  campaign_query_member_edge_create      ok    
86.823       /api/alert/analyze  campaign_query_member_edge_check       ok    
95.888       /api/alert/analyze  campaign_query_member_edge_create      ok    
1386.297     /api/alert/analyze  campaign_correlation_summary           ok    
1459.924     /api/alert/analyze  campaign_correlation                   ok    
0.023        /api/alert/analyze  decision_event_emit                    ok    
84.297       /api/alert/analyze  composite_gate_evaluation              ok    
0.057        /api/alert/analyze  provenance_build                       ok    
91.632       /api/alert/analyze  graph_visualization_fetch              ok    
0.031        /api/alert/analyze  response_context_enrichment            ok    
0.051        /api/alert/analyze  referral_debug_build                   ok    
0.027        /api/alert/analyze  shadow_compare_schedule                ok    
94.137       /api/alert/analyze  cluster_history_fetch                  ok    
0.03         /api/alert/analyze  narrative_context_build                ok    
0.143        /api/alert/analyze  narrative_generation                   ok    
2.687        /api/alert/analyze  response_serialization                 ok    
2722.825     /api/alert/analyze  analyze_request_total                  ok    
0.012        /api/alert/outcome  request_parse                          ok    
0.007        /api/alert/outcome  duplicate_feedback_guard               ok    
76.303       /api/alert/outcome  decision_lookup_and_outcome_update     ok    
0.699        /api/alert/outcome  outcome_audit_write                    ok    
123.452      /api/alert/outcome  learning_state_update                  ok    
409.162      /api/alert/outcome  l5_conservation_write                  ok    
411.245      /api/alert/outcome  conservation_monitor                   ok    
0.252        /api/alert/outcome  profile_scorer_update                  ok    
0.219        /api/alert/outcome  l5_dk_weight_write                     ok    
422.358      /api/alert/outcome  l5_centroid_write                      ok    
0.016        /api/alert/outcome  l5_dk_weight_write                     ok    
0.015        /api/alert/outcome  snapshot_evolution_logging             ok    
78.852       /api/alert/outcome  snapshot_evolution_logging             ok    
0.029        /api/alert/outcome  response_serialization                 ok    
1568.301     /api/alert/outcome  outcome_request_total                  ok    
```

## Nested Phase Warning
Nested phase durations should not be summed blindly. Use analyze_request_total, outcome_request_total, or total_attempt as authoritative totals.
