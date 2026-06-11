# SOC Perf Trace Summary

## Safety
- Read-only summary of existing JSONL trace events.
- No backend, graph, proof, or seed operations are performed.
- Nested phases are not additive; request-total phases are the authoritative route totals.

## Input
- trace_jsonl: `C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50\scratch\temp\soc_perf_trace_phased_25.jsonl`
- events_loaded: 1125
- malformed_lines: 0
- route_filter: None
- phase_filter: None

## Route + Phase Aggregates
```text
route_phase                                              count  avg_ms    p50_ms    p95_ms    p99_ms    max_ms  
-------------------------------------------------------  -----  --------  --------  --------  --------  --------
/api/alert/analyze | analyze_request_total               25     3910.363  4053.19   5555.467  5582.263  5589.964
/api/alert/analyze | campaign_correlation                25     2649.519  2724.251  4329.03   4348.23   4350.764
/api/alert/outcome | outcome_request_total               25     1696.246  1587.839  2352.68   2447.461  2472.0  
/api/alert/outcome | conservation_monitor                25     458.854   423.141   706.054   1051.931  1143.342
/api/alert/outcome | l5_conservation_write               25     456.757   421.569   704.333   1050.556  1141.892
/api/alert/outcome | learning_state_update               25     156.268   114.17    565.175   752.16    780.171 
/api/alert/analyze | factor_vector_construction          25     330.369   320.284   392.525   502.285   535.853 
/api/alert/outcome | l5_centroid_write                   25     429.572   416.999   519.276   527.08    528.897 
/api/alert/analyze | reasoning_generation                25     108.92    90.579    224.9     370.541   407.887 
/api/alert/analyze | referral_history_counts             25     170.049   162.269   216.563   234.933   240.549 
/api/alert/outcome | snapshot_evolution_logging          50     48.843    33.705    120.376   216.123   227.827 
/api/alert/analyze | security_context_lookup             25     88.828    83.65     101.185   194.563   223.508 
/api/alert/outcome | decision_lookup_and_outcome_update  25     92.654    87.24     135.811   162.951   171.052 
/api/alert/analyze | composite_gate_evaluation           25     83.611    77.263    113.018   143.191   151.975 
/api/alert/analyze | alert_lookup                        25     79.418    75.556    119.075   139.356   144.395 
/api/alert/analyze | graph_visualization_fetch           25     85.571    82.191    119.188   131.931   134.187 
/api/alert/analyze | decision_node_and_edge_write        25     89.198    84.994    121.252   128.947   130.237 
/api/alert/analyze | cluster_history_fetch               25     87.845    83.998    120.55    126.73    128.35  
/api/alert/analyze | audit_write                         25     80.928    80.21     97.34     98.614    98.769  
/api/alert/analyze | scorer_decision                     25     0.778     0.208     0.53      10.541    13.696  
/api/alert/analyze | response_serialization              25     3.91      3.257     8.021     8.434     8.55    
/api/alert/analyze | post_scorer_confidence_gate         25     0.307     0.017     0.039     5.457     7.167   
/api/alert/outcome | outcome_audit_write                 25     0.594     0.321     0.739     5.333     6.775   
/api/alert/analyze | category_resolution                 25     0.36      0.153     0.322     3.931     5.063   
/api/alert/analyze | metadata_logging_snapshot_write     25     0.495     0.265     0.881     3.569     4.409   
/api/alert/outcome | profile_scorer_update               25     0.301     0.184     0.423     2.086     2.605   
/api/alert/analyze | referral_debug_build                25     0.064     0.033     0.081     0.508     0.642   
/api/alert/outcome | l5_dk_weight_write                  50     0.114     0.052     0.4       0.539     0.597   
/api/alert/analyze | decision_event_emit                 25     0.056     0.027     0.118     0.405     0.495   
/api/alert/analyze | referral_gate_evaluation            25     0.067     0.048     0.107     0.312     0.376   
/api/alert/analyze | narrative_generation                25     0.081     0.061     0.194     0.207     0.21    
/api/alert/analyze | shadow_compare_schedule             25     0.028     0.018     0.049     0.157     0.191   
/api/alert/analyze | provenance_build                    25     0.079     0.058     0.158     0.163     0.163   
/api/alert/analyze | narrative_context_build             25     0.046     0.041     0.068     0.113     0.127   
/api/alert/analyze | rl_exploration_proposal             25     0.022     0.014     0.03      0.104     0.127   
/api/alert/outcome | response_serialization              25     0.036     0.031     0.05      0.09      0.103   
/api/alert/analyze | response_context_enrichment         25     0.033     0.026     0.06      0.071     0.074   
/api/alert/outcome | duplicate_feedback_guard            25     0.016     0.012     0.039     0.045     0.046   
/api/alert/analyze | routing_zone_resolution             25     0.021     0.019     0.036     0.039     0.04    
/api/alert/analyze | scorer_readiness                    25     0.02      0.019     0.032     0.038     0.04    
```

## Phase Aggregates
```text
phase                               count  avg_ms    p50_ms    p95_ms    p99_ms    max_ms  
----------------------------------  -----  --------  --------  --------  --------  --------
analyze_request_total               25     3910.363  4053.19   5555.467  5582.263  5589.964
campaign_correlation                25     2649.519  2724.251  4329.03   4348.23   4350.764
outcome_request_total               25     1696.246  1587.839  2352.68   2447.461  2472.0  
conservation_monitor                25     458.854   423.141   706.054   1051.931  1143.342
l5_conservation_write               25     456.757   421.569   704.333   1050.556  1141.892
learning_state_update               25     156.268   114.17    565.175   752.16    780.171 
factor_vector_construction          25     330.369   320.284   392.525   502.285   535.853 
l5_centroid_write                   25     429.572   416.999   519.276   527.08    528.897 
reasoning_generation                25     108.92    90.579    224.9     370.541   407.887 
referral_history_counts             25     170.049   162.269   216.563   234.933   240.549 
snapshot_evolution_logging          50     48.843    33.705    120.376   216.123   227.827 
security_context_lookup             25     88.828    83.65     101.185   194.563   223.508 
decision_lookup_and_outcome_update  25     92.654    87.24     135.811   162.951   171.052 
composite_gate_evaluation           25     83.611    77.263    113.018   143.191   151.975 
alert_lookup                        25     79.418    75.556    119.075   139.356   144.395 
graph_visualization_fetch           25     85.571    82.191    119.188   131.931   134.187 
decision_node_and_edge_write        25     89.198    84.994    121.252   128.947   130.237 
cluster_history_fetch               25     87.845    83.998    120.55    126.73    128.35  
audit_write                         25     80.928    80.21     97.34     98.614    98.769  
scorer_decision                     25     0.778     0.208     0.53      10.541    13.696  
response_serialization              50     1.973     0.619     7.81      8.312     8.55    
post_scorer_confidence_gate         25     0.307     0.017     0.039     5.457     7.167   
outcome_audit_write                 25     0.594     0.321     0.739     5.333     6.775   
category_resolution                 25     0.36      0.153     0.322     3.931     5.063   
metadata_logging_snapshot_write     25     0.495     0.265     0.881     3.569     4.409   
profile_scorer_update               25     0.301     0.184     0.423     2.086     2.605   
referral_debug_build                25     0.064     0.033     0.081     0.508     0.642   
l5_dk_weight_write                  50     0.114     0.052     0.4       0.539     0.597   
decision_event_emit                 25     0.056     0.027     0.118     0.405     0.495   
referral_gate_evaluation            25     0.067     0.048     0.107     0.312     0.376   
narrative_generation                25     0.081     0.061     0.194     0.207     0.21    
shadow_compare_schedule             25     0.028     0.018     0.049     0.157     0.191   
provenance_build                    25     0.079     0.058     0.158     0.163     0.163   
narrative_context_build             25     0.046     0.041     0.068     0.113     0.127   
rl_exploration_proposal             25     0.022     0.014     0.03      0.104     0.127   
response_context_enrichment         25     0.033     0.026     0.06      0.071     0.074   
duplicate_feedback_guard            25     0.016     0.012     0.039     0.045     0.046   
routing_zone_resolution             25     0.021     0.019     0.036     0.039     0.04    
scorer_readiness                    25     0.02      0.019     0.032     0.038     0.04    
routing_threshold_lookup            25     0.012     0.011     0.017     0.033     0.038   
```

## Graph Aggregates
```text
graph_name             count  avg_ms   p50_ms  p95_ms    p99_ms   max_ms  
---------------------  -----  -------  ------  --------  -------  --------
soc_graph_phased_25_1  1125   248.005  0.244   1587.465  4348.23  5589.964
```

## Top Slow Events
```text
duration_ms  route               phase                  alert_id       decision_id                           attempt_index  status
-----------  ------------------  ---------------------  -------------  ------------------------------------  -------------  ------
5589.964     /api/alert/analyze  analyze_request_total  PHASED25-0021  521a46fd-8dd3-4695-8f7a-b28a61599127  None           ok    
5557.877     /api/alert/analyze  analyze_request_total  PHASED25-0022  36adc7e3-a1dc-416f-81a9-bc435350f6e4  None           ok    
5545.825     /api/alert/analyze  analyze_request_total  PHASED25-0024  7cb048fc-58dd-46f8-bbc9-69f1992bc1a1  None           ok    
5471.03      /api/alert/analyze  analyze_request_total  PHASED25-0023  346716a0-241c-42f4-a763-9e35dcdb4f31  None           ok    
5254.511     /api/alert/analyze  analyze_request_total  PHASED25-0019  c2de3067-6a18-4bcb-a8c3-0f05e4624324  None           ok    
5204.55      /api/alert/analyze  analyze_request_total  PHASED25-0025  98cd68b3-dcff-4a9d-a3ae-662d4347ea35  None           ok    
5117.941     /api/alert/analyze  analyze_request_total  PHASED25-0017  a4fc7b3d-77ab-4570-a618-1ef2bc398186  None           ok    
4953.555     /api/alert/analyze  analyze_request_total  PHASED25-0020  ef3e59ac-04b0-4874-8270-f06dac06ffe5  None           ok    
4732.234     /api/alert/analyze  analyze_request_total  PHASED25-0015  42a5c9c9-3c36-4461-9515-c77587f0c330  None           ok    
4616.82      /api/alert/analyze  analyze_request_total  PHASED25-0018  5446fcb3-bc64-4037-9a36-7f550b1de4c4  None           ok    
4405.535     /api/alert/analyze  analyze_request_total  PHASED25-0014  14656dad-a5a5-4611-b3d3-e1f85cb8e0a4  None           ok    
4350.764     /api/alert/analyze  campaign_correlation   PHASED25-0024  7cb048fc-58dd-46f8-bbc9-69f1992bc1a1  None           ok    
4340.206     /api/alert/analyze  campaign_correlation   PHASED25-0021  521a46fd-8dd3-4695-8f7a-b28a61599127  None           ok    
4288.276     /api/alert/analyze  analyze_request_total  PHASED25-0016  7010d47f-873b-4687-8ca3-b10b1876c03a  None           ok    
4284.326     /api/alert/analyze  campaign_correlation   PHASED25-0022  36adc7e3-a1dc-416f-81a9-bc435350f6e4  None           ok    
4251.084     /api/alert/analyze  campaign_correlation   PHASED25-0023  346716a0-241c-42f4-a763-9e35dcdb4f31  None           ok    
4142.356     /api/alert/analyze  campaign_correlation   PHASED25-0025  98cd68b3-dcff-4a9d-a3ae-662d4347ea35  None           ok    
4053.19      /api/alert/analyze  analyze_request_total  PHASED25-0013  44fb78c7-351e-441f-99d2-14bfbdaa2ed5  None           ok    
3968.877     /api/alert/analyze  campaign_correlation   PHASED25-0019  c2de3067-6a18-4bcb-a8c3-0f05e4624324  None           ok    
3759.696     /api/alert/analyze  campaign_correlation   PHASED25-0020  ef3e59ac-04b0-4874-8270-f06dac06ffe5  None           ok    
```

## Early/Mid/Late Windows
```text
(none)
```

## Per-Alert Waterfall

### PHASED25-0021
- event_count: 45
- total_observed_ms: 14620.949
- authoritative_total_ms: 5589.964
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.014        /api/alert/analyze  scorer_readiness                    ok    
0.008        /api/alert/analyze  request_parse                       ok    
144.395      /api/alert/analyze  alert_lookup                        ok    
80.48        /api/alert/analyze  security_context_lookup             ok    
0.12         /api/alert/analyze  category_resolution                 ok    
334.121      /api/alert/analyze  factor_vector_construction          ok    
0.175        /api/alert/analyze  scorer_decision                     ok    
0.017        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.007        /api/alert/analyze  routing_threshold_lookup            ok    
0.012        /api/alert/analyze  rl_exploration_proposal             ok    
0.015        /api/alert/analyze  routing_zone_resolution             ok    
140.163      /api/alert/analyze  referral_history_counts             ok    
0.038        /api/alert/analyze  referral_gate_evaluation            ok    
94.068       /api/alert/analyze  reasoning_generation                ok    
104.734      /api/alert/analyze  decision_node_and_edge_write        ok    
89.776       /api/alert/analyze  audit_write                         ok    
0.455        /api/alert/analyze  metadata_logging_snapshot_write     ok    
4340.206     /api/alert/analyze  campaign_correlation                ok    
0.11         /api/alert/analyze  decision_event_emit                 ok    
75.614       /api/alert/analyze  composite_gate_evaluation           ok    
0.064        /api/alert/analyze  provenance_build                    ok    
65.673       /api/alert/analyze  graph_visualization_fetch           ok    
0.026        /api/alert/analyze  response_context_enrichment         ok    
0.037        /api/alert/analyze  referral_debug_build                ok    
0.013        /api/alert/analyze  shadow_compare_schedule             ok    
69.392       /api/alert/analyze  cluster_history_fetch               ok    
0.065        /api/alert/analyze  narrative_context_build             ok    
0.042        /api/alert/analyze  narrative_generation                ok    
2.523        /api/alert/analyze  response_serialization              ok    
5589.964     /api/alert/analyze  analyze_request_total               ok    
0.008        /api/alert/outcome  request_parse                       ok    
0.007        /api/alert/outcome  duplicate_feedback_guard            ok    
89.904       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.22         /api/alert/outcome  outcome_audit_write                 ok    
106.878      /api/alert/outcome  learning_state_update               ok    
476.359      /api/alert/outcome  l5_conservation_write               ok    
480.426      /api/alert/outcome  conservation_monitor                ok    
0.353        /api/alert/outcome  profile_scorer_update               ok    
0.321        /api/alert/outcome  l5_dk_weight_write                  ok    
486.488      /api/alert/outcome  l5_centroid_write                   ok    
0.021        /api/alert/outcome  l5_dk_weight_write                  ok    
0.018        /api/alert/outcome  snapshot_evolution_logging          ok    
101.342      /api/alert/outcome  snapshot_evolution_logging          ok    
0.019        /api/alert/outcome  response_serialization              ok    
1746.258     /api/alert/outcome  outcome_request_total               ok    
```

### PHASED25-0022
- event_count: 45
- total_observed_ms: 14240.523
- authoritative_total_ms: 5557.877
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.017        /api/alert/analyze  scorer_readiness                    ok    
0.011        /api/alert/analyze  request_parse                       ok    
95.394       /api/alert/analyze  alert_lookup                        ok    
88.623       /api/alert/analyze  security_context_lookup             ok    
0.21         /api/alert/analyze  category_resolution                 ok    
341.663      /api/alert/analyze  factor_vector_construction          ok    
0.236        /api/alert/analyze  scorer_decision                     ok    
0.025        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.014        /api/alert/analyze  routing_threshold_lookup            ok    
0.024        /api/alert/analyze  rl_exploration_proposal             ok    
0.024        /api/alert/analyze  routing_zone_resolution             ok    
162.269      /api/alert/analyze  referral_history_counts             ok    
0.073        /api/alert/analyze  referral_gate_evaluation            ok    
80.829       /api/alert/analyze  reasoning_generation                ok    
83.056       /api/alert/analyze  decision_node_and_edge_write        ok    
98.123       /api/alert/analyze  audit_write                         ok    
0.25         /api/alert/analyze  metadata_logging_snapshot_write     ok    
4284.326     /api/alert/analyze  campaign_correlation                ok    
0.019        /api/alert/analyze  decision_event_emit                 ok    
94.976       /api/alert/analyze  composite_gate_evaluation           ok    
0.103        /api/alert/analyze  provenance_build                    ok    
76.893       /api/alert/analyze  graph_visualization_fetch           ok    
0.027        /api/alert/analyze  response_context_enrichment         ok    
0.026        /api/alert/analyze  referral_debug_build                ok    
0.013        /api/alert/analyze  shadow_compare_schedule             ok    
89.298       /api/alert/analyze  cluster_history_fetch               ok    
0.068        /api/alert/analyze  narrative_context_build             ok    
0.092        /api/alert/analyze  narrative_generation                ok    
5.361        /api/alert/analyze  response_serialization              ok    
5557.877     /api/alert/analyze  analyze_request_total               ok    
0.014        /api/alert/outcome  request_parse                       ok    
0.009        /api/alert/outcome  duplicate_feedback_guard            ok    
129.857      /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.456        /api/alert/outcome  outcome_audit_write                 ok    
118.51       /api/alert/outcome  learning_state_update               ok    
435.251      /api/alert/outcome  l5_conservation_write               ok    
436.482      /api/alert/outcome  conservation_monitor                ok    
2.605        /api/alert/outcome  profile_scorer_update               ok    
0.16         /api/alert/outcome  l5_dk_weight_write                  ok    
392.23       /api/alert/outcome  l5_centroid_write                   ok    
0.014        /api/alert/outcome  l5_dk_weight_write                  ok    
0.016        /api/alert/outcome  snapshot_evolution_logging          ok    
77.128       /api/alert/outcome  snapshot_evolution_logging          ok    
0.032        /api/alert/outcome  response_serialization              ok    
1587.839     /api/alert/outcome  outcome_request_total               ok    
```

### PHASED25-0024
- event_count: 45
- total_observed_ms: 14133.733
- authoritative_total_ms: 5545.825
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.016        /api/alert/analyze  scorer_readiness                    ok    
0.006        /api/alert/analyze  request_parse                       ok    
75.367       /api/alert/analyze  alert_lookup                        ok    
80.598       /api/alert/analyze  security_context_lookup             ok    
0.195        /api/alert/analyze  category_resolution                 ok    
320.284      /api/alert/analyze  factor_vector_construction          ok    
0.314        /api/alert/analyze  scorer_decision                     ok    
0.029        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.015        /api/alert/analyze  routing_threshold_lookup            ok    
0.014        /api/alert/analyze  rl_exploration_proposal             ok    
0.013        /api/alert/analyze  routing_zone_resolution             ok    
160.549      /api/alert/analyze  referral_history_counts             ok    
0.072        /api/alert/analyze  referral_gate_evaluation            ok    
75.98        /api/alert/analyze  reasoning_generation                ok    
106.813      /api/alert/analyze  decision_node_and_edge_write        ok    
65.167       /api/alert/analyze  audit_write                         ok    
0.208        /api/alert/analyze  metadata_logging_snapshot_write     ok    
4350.764     /api/alert/analyze  campaign_correlation                ok    
0.04         /api/alert/analyze  decision_event_emit                 ok    
86.403       /api/alert/analyze  composite_gate_evaluation           ok    
0.089        /api/alert/analyze  provenance_build                    ok    
81.791       /api/alert/analyze  graph_visualization_fetch           ok    
0.023        /api/alert/analyze  response_context_enrichment         ok    
0.051        /api/alert/analyze  referral_debug_build                ok    
0.021        /api/alert/analyze  shadow_compare_schedule             ok    
81.162       /api/alert/analyze  cluster_history_fetch               ok    
0.067        /api/alert/analyze  narrative_context_build             ok    
0.056        /api/alert/analyze  narrative_generation                ok    
3.787        /api/alert/analyze  response_serialization              ok    
5545.825     /api/alert/analyze  analyze_request_total               ok    
0.019        /api/alert/outcome  request_parse                       ok    
0.042        /api/alert/outcome  duplicate_feedback_guard            ok    
137.299      /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.19         /api/alert/outcome  outcome_audit_write                 ok    
114.855      /api/alert/outcome  learning_state_update               ok    
433.454      /api/alert/outcome  l5_conservation_write               ok    
435.034      /api/alert/outcome  conservation_monitor                ok    
0.184        /api/alert/outcome  profile_scorer_update               ok    
0.143        /api/alert/outcome  l5_dk_weight_write                  ok    
375.956      /api/alert/outcome  l5_centroid_write                   ok    
0.014        /api/alert/outcome  l5_dk_weight_write                  ok    
0.049        /api/alert/outcome  snapshot_evolution_logging          ok    
77.937       /api/alert/outcome  snapshot_evolution_logging          ok    
0.023        /api/alert/outcome  response_serialization              ok    
1522.815     /api/alert/outcome  outcome_request_total               ok    
```

### PHASED25-0023
- event_count: 45
- total_observed_ms: 13912.283
- authoritative_total_ms: 5471.03
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.015        /api/alert/analyze  scorer_readiness                    ok    
0.009        /api/alert/analyze  request_parse                       ok    
64.209       /api/alert/analyze  alert_lookup                        ok    
86.993       /api/alert/analyze  security_context_lookup             ok    
0.117        /api/alert/analyze  category_resolution                 ok    
344.543      /api/alert/analyze  factor_vector_construction          ok    
0.166        /api/alert/analyze  scorer_decision                     ok    
0.015        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.007        /api/alert/analyze  routing_threshold_lookup            ok    
0.014        /api/alert/analyze  rl_exploration_proposal             ok    
0.014        /api/alert/analyze  routing_zone_resolution             ok    
157.335      /api/alert/analyze  referral_history_counts             ok    
0.035        /api/alert/analyze  referral_gate_evaluation            ok    
78.966       /api/alert/analyze  reasoning_generation                ok    
94.836       /api/alert/analyze  decision_node_and_edge_write        ok    
90.957       /api/alert/analyze  audit_write                         ok    
0.13         /api/alert/analyze  metadata_logging_snapshot_write     ok    
4251.084     /api/alert/analyze  campaign_correlation                ok    
0.022        /api/alert/analyze  decision_event_emit                 ok    
79.232       /api/alert/analyze  composite_gate_evaluation           ok    
0.049        /api/alert/analyze  provenance_build                    ok    
80.024       /api/alert/analyze  graph_visualization_fetch           ok    
0.02         /api/alert/analyze  response_context_enrichment         ok    
0.027        /api/alert/analyze  referral_debug_build                ok    
0.011        /api/alert/analyze  shadow_compare_schedule             ok    
91.54        /api/alert/analyze  cluster_history_fetch               ok    
0.057        /api/alert/analyze  narrative_context_build             ok    
0.078        /api/alert/analyze  narrative_generation                ok    
5.436        /api/alert/analyze  response_serialization              ok    
5471.03      /api/alert/analyze  analyze_request_total               ok    
0.017        /api/alert/outcome  request_parse                       ok    
0.016        /api/alert/outcome  duplicate_feedback_guard            ok    
97.717       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.765        /api/alert/outcome  outcome_audit_write                 ok    
137.15       /api/alert/outcome  learning_state_update               ok    
390.086      /api/alert/outcome  l5_conservation_write               ok    
391.425      /api/alert/outcome  conservation_monitor                ok    
0.137        /api/alert/outcome  profile_scorer_update               ok    
0.214        /api/alert/outcome  l5_dk_weight_write                  ok    
418.031      /api/alert/outcome  l5_centroid_write                   ok    
0.022        /api/alert/outcome  l5_dk_weight_write                  ok    
0.016        /api/alert/outcome  snapshot_evolution_logging          ok    
64.608       /api/alert/outcome  snapshot_evolution_logging          ok    
0.021        /api/alert/outcome  response_serialization              ok    
1515.087     /api/alert/outcome  outcome_request_total               ok    
```

### PHASED25-0019
- event_count: 45
- total_observed_ms: 15905.032
- authoritative_total_ms: 5254.511
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.013        /api/alert/analyze  scorer_readiness                    ok    
0.012        /api/alert/analyze  request_parse                       ok    
69.154       /api/alert/analyze  alert_lookup                        ok    
89.267       /api/alert/analyze  security_context_lookup             ok    
0.097        /api/alert/analyze  category_resolution                 ok    
329.449      /api/alert/analyze  factor_vector_construction          ok    
0.171        /api/alert/analyze  scorer_decision                     ok    
0.013        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.007        /api/alert/analyze  routing_threshold_lookup            ok    
0.012        /api/alert/analyze  rl_exploration_proposal             ok    
0.013        /api/alert/analyze  routing_zone_resolution             ok    
217.147      /api/alert/analyze  referral_history_counts             ok    
0.044        /api/alert/analyze  referral_gate_evaluation            ok    
90.281       /api/alert/analyze  reasoning_generation                ok    
130.237      /api/alert/analyze  decision_node_and_edge_write        ok    
81.056       /api/alert/analyze  audit_write                         ok    
0.907        /api/alert/analyze  metadata_logging_snapshot_write     ok    
3968.877     /api/alert/analyze  campaign_correlation                ok    
0.495        /api/alert/analyze  decision_event_emit                 ok    
75.687       /api/alert/analyze  composite_gate_evaluation           ok    
0.045        /api/alert/analyze  provenance_build                    ok    
82.191       /api/alert/analyze  graph_visualization_fetch           ok    
0.025        /api/alert/analyze  response_context_enrichment         ok    
0.026        /api/alert/analyze  referral_debug_build                ok    
0.012        /api/alert/analyze  shadow_compare_schedule             ok    
65.894       /api/alert/analyze  cluster_history_fetch               ok    
0.025        /api/alert/analyze  narrative_context_build             ok    
0.035        /api/alert/analyze  narrative_generation                ok    
1.89         /api/alert/analyze  response_serialization              ok    
5254.511     /api/alert/analyze  analyze_request_total               ok    
0.019        /api/alert/outcome  request_parse                       ok    
0.013        /api/alert/outcome  duplicate_feedback_guard            ok    
68.346       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.282        /api/alert/outcome  outcome_audit_write                 ok    
129.213      /api/alert/outcome  learning_state_update               ok    
1141.892     /api/alert/outcome  l5_conservation_write               ok    
1143.342     /api/alert/outcome  conservation_monitor                ok    
0.262        /api/alert/outcome  profile_scorer_update               ok    
0.222        /api/alert/outcome  l5_dk_weight_write                  ok    
511.074      /api/alert/outcome  l5_centroid_write                   ok    
0.017        /api/alert/outcome  l5_dk_weight_write                  ok    
0.027        /api/alert/outcome  snapshot_evolution_logging          ok    
82.937       /api/alert/outcome  snapshot_evolution_logging          ok    
0.04         /api/alert/outcome  response_serialization              ok    
2369.753     /api/alert/outcome  outcome_request_total               ok    
```

### PHASED25-0025
- event_count: 45
- total_observed_ms: 12857.441
- authoritative_total_ms: 5204.55
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.013        /api/alert/analyze  scorer_readiness                    ok    
0.007        /api/alert/analyze  request_parse                       ok    
68.216       /api/alert/analyze  alert_lookup                        ok    
68.799       /api/alert/analyze  security_context_lookup             ok    
0.121        /api/alert/analyze  category_resolution                 ok    
289.202      /api/alert/analyze  factor_vector_construction          ok    
0.117        /api/alert/analyze  scorer_decision                     ok    
0.011        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.011        /api/alert/analyze  routing_threshold_lookup            ok    
0.018        /api/alert/analyze  rl_exploration_proposal             ok    
0.024        /api/alert/analyze  routing_zone_resolution             ok    
166.893      /api/alert/analyze  referral_history_counts             ok    
0.027        /api/alert/analyze  referral_gate_evaluation            ok    
90.579       /api/alert/analyze  reasoning_generation                ok    
77.85        /api/alert/analyze  decision_node_and_edge_write        ok    
65.037       /api/alert/analyze  audit_write                         ok    
0.471        /api/alert/analyze  metadata_logging_snapshot_write     ok    
4142.356     /api/alert/analyze  campaign_correlation                ok    
0.024        /api/alert/analyze  decision_event_emit                 ok    
69.808       /api/alert/analyze  composite_gate_evaluation           ok    
0.046        /api/alert/analyze  provenance_build                    ok    
66.148       /api/alert/analyze  graph_visualization_fetch           ok    
0.02         /api/alert/analyze  response_context_enrichment         ok    
0.024        /api/alert/analyze  referral_debug_build                ok    
0.011        /api/alert/analyze  shadow_compare_schedule             ok    
66.096       /api/alert/analyze  cluster_history_fetch               ok    
0.02         /api/alert/analyze  narrative_context_build             ok    
0.026        /api/alert/analyze  narrative_generation                ok    
1.135        /api/alert/analyze  response_serialization              ok    
5204.55      /api/alert/analyze  analyze_request_total               ok    
0.009        /api/alert/outcome  request_parse                       ok    
0.008        /api/alert/outcome  duplicate_feedback_guard            ok    
63.839       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.22         /api/alert/outcome  outcome_audit_write                 ok    
38.171       /api/alert/outcome  learning_state_update               ok    
333.299      /api/alert/outcome  l5_conservation_write               ok    
334.202      /api/alert/outcome  conservation_monitor                ok    
0.111        /api/alert/outcome  profile_scorer_update               ok    
0.067        /api/alert/outcome  l5_dk_weight_write                  ok    
366.721      /api/alert/outcome  l5_centroid_write                   ok    
0.011        /api/alert/outcome  l5_dk_weight_write                  ok    
0.026        /api/alert/outcome  snapshot_evolution_logging          ok    
77.723       /api/alert/outcome  snapshot_evolution_logging          ok    
0.029        /api/alert/outcome  response_serialization              ok    
1265.345     /api/alert/outcome  outcome_request_total               ok    
```

### PHASED25-0017
- event_count: 45
- total_observed_ms: 13319.626
- authoritative_total_ms: 5117.941
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.032        /api/alert/analyze  scorer_readiness                    ok    
0.008        /api/alert/analyze  request_parse                       ok    
69.755       /api/alert/analyze  alert_lookup                        ok    
223.508      /api/alert/analyze  security_context_lookup             ok    
0.116        /api/alert/analyze  category_resolution                 ok    
535.853      /api/alert/analyze  factor_vector_construction          ok    
0.177        /api/alert/analyze  scorer_decision                     ok    
0.016        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.008        /api/alert/analyze  routing_threshold_lookup            ok    
0.012        /api/alert/analyze  rl_exploration_proposal             ok    
0.016        /api/alert/analyze  routing_zone_resolution             ok    
192.461      /api/alert/analyze  referral_history_counts             ok    
0.038        /api/alert/analyze  referral_gate_evaluation            ok    
106.242      /api/alert/analyze  reasoning_generation                ok    
84.994       /api/alert/analyze  decision_node_and_edge_write        ok    
88.664       /api/alert/analyze  audit_write                         ok    
0.778        /api/alert/analyze  metadata_logging_snapshot_write     ok    
3525.669     /api/alert/analyze  campaign_correlation                ok    
0.026        /api/alert/analyze  decision_event_emit                 ok    
65.605       /api/alert/analyze  composite_gate_evaluation           ok    
0.058        /api/alert/analyze  provenance_build                    ok    
96.151       /api/alert/analyze  graph_visualization_fetch           ok    
0.025        /api/alert/analyze  response_context_enrichment         ok    
0.033        /api/alert/analyze  referral_debug_build                ok    
0.012        /api/alert/analyze  shadow_compare_schedule             ok    
90.403       /api/alert/analyze  cluster_history_fetch               ok    
0.03         /api/alert/analyze  narrative_context_build             ok    
0.041        /api/alert/analyze  narrative_generation                ok    
2.176        /api/alert/analyze  response_serialization              ok    
5117.941     /api/alert/analyze  analyze_request_total               ok    
0.007        /api/alert/outcome  request_parse                       ok    
0.009        /api/alert/outcome  duplicate_feedback_guard            ok    
74.655       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.279        /api/alert/outcome  outcome_audit_write                 ok    
80.286       /api/alert/outcome  learning_state_update               ok    
434.129      /api/alert/outcome  l5_conservation_write               ok    
436.971      /api/alert/outcome  conservation_monitor                ok    
0.268        /api/alert/outcome  profile_scorer_update               ok    
0.214        /api/alert/outcome  l5_dk_weight_write                  ok    
454.142      /api/alert/outcome  l5_centroid_write                   ok    
0.029        /api/alert/outcome  l5_dk_weight_write                  ok    
0.029        /api/alert/outcome  snapshot_evolution_logging          ok    
69.87        /api/alert/outcome  snapshot_evolution_logging          ok    
0.029        /api/alert/outcome  response_serialization              ok    
1567.861     /api/alert/outcome  outcome_request_total               ok    
```

### PHASED25-0020
- event_count: 45
- total_observed_ms: 13095.051
- authoritative_total_ms: 4953.555
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.019        /api/alert/analyze  scorer_readiness                    ok    
0.014        /api/alert/analyze  request_parse                       ok    
70.512       /api/alert/analyze  alert_lookup                        ok    
102.903      /api/alert/analyze  security_context_lookup             ok    
0.178        /api/alert/analyze  category_resolution                 ok    
337.326      /api/alert/analyze  factor_vector_construction          ok    
0.155        /api/alert/analyze  scorer_decision                     ok    
0.015        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.007        /api/alert/analyze  routing_threshold_lookup            ok    
0.013        /api/alert/analyze  rl_exploration_proposal             ok    
0.011        /api/alert/analyze  routing_zone_resolution             ok    
153.507      /api/alert/analyze  referral_history_counts             ok    
0.04         /api/alert/analyze  referral_gate_evaluation            ok    
90.493       /api/alert/analyze  reasoning_generation                ok    
98.887       /api/alert/analyze  decision_node_and_edge_write        ok    
82.965       /api/alert/analyze  audit_write                         ok    
0.265        /api/alert/analyze  metadata_logging_snapshot_write     ok    
3759.696     /api/alert/analyze  campaign_correlation                ok    
0.031        /api/alert/analyze  decision_event_emit                 ok    
64.718       /api/alert/analyze  composite_gate_evaluation           ok    
0.055        /api/alert/analyze  provenance_build                    ok    
83.476       /api/alert/analyze  graph_visualization_fetch           ok    
0.027        /api/alert/analyze  response_context_enrichment         ok    
0.03         /api/alert/analyze  referral_debug_build                ok    
0.013        /api/alert/analyze  shadow_compare_schedule             ok    
69.509       /api/alert/analyze  cluster_history_fetch               ok    
0.031        /api/alert/analyze  narrative_context_build             ok    
0.21         /api/alert/analyze  narrative_generation                ok    
3.577        /api/alert/analyze  response_serialization              ok    
4953.555     /api/alert/analyze  analyze_request_total               ok    
0.013        /api/alert/outcome  request_parse                       ok    
0.012        /api/alert/outcome  duplicate_feedback_guard            ok    
82.163       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.326        /api/alert/outcome  outcome_audit_write                 ok    
109.867      /api/alert/outcome  learning_state_update               ok    
377.971      /api/alert/outcome  l5_conservation_write               ok    
379.137      /api/alert/outcome  conservation_monitor                ok    
0.147        /api/alert/outcome  profile_scorer_update               ok    
0.105        /api/alert/outcome  l5_dk_weight_write                  ok    
379.302      /api/alert/outcome  l5_centroid_write                   ok    
0.023        /api/alert/outcome  l5_dk_weight_write                  ok    
0.019        /api/alert/outcome  snapshot_evolution_logging          ok    
107.799      /api/alert/outcome  snapshot_evolution_logging          ok    
0.049        /api/alert/outcome  response_serialization              ok    
1785.88      /api/alert/outcome  outcome_request_total               ok    
```

### PHASED25-0015
- event_count: 45
- total_observed_ms: 14313.398
- authoritative_total_ms: 4732.234
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.022        /api/alert/analyze  scorer_readiness                    ok    
0.008        /api/alert/analyze  request_parse                       ok    
123.401      /api/alert/analyze  alert_lookup                        ok    
83.169       /api/alert/analyze  security_context_lookup             ok    
0.107        /api/alert/analyze  category_resolution                 ok    
378.683      /api/alert/analyze  factor_vector_construction          ok    
0.153        /api/alert/analyze  scorer_decision                     ok    
0.013        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.006        /api/alert/analyze  routing_threshold_lookup            ok    
0.012        /api/alert/analyze  rl_exploration_proposal             ok    
0.016        /api/alert/analyze  routing_zone_resolution             ok    
214.227      /api/alert/analyze  referral_history_counts             ok    
0.061        /api/alert/analyze  referral_gate_evaluation            ok    
65.717       /api/alert/analyze  reasoning_generation                ok    
101.741      /api/alert/analyze  decision_node_and_edge_write        ok    
71.901       /api/alert/analyze  audit_write                         ok    
0.151        /api/alert/analyze  metadata_logging_snapshot_write     ok    
3254.096     /api/alert/analyze  campaign_correlation                ok    
0.12         /api/alert/analyze  decision_event_emit                 ok    
151.975      /api/alert/analyze  composite_gate_evaluation           ok    
0.049        /api/alert/analyze  provenance_build                    ok    
124.787      /api/alert/analyze  graph_visualization_fetch           ok    
0.028        /api/alert/analyze  response_context_enrichment         ok    
0.031        /api/alert/analyze  referral_debug_build                ok    
0.018        /api/alert/analyze  shadow_compare_schedule             ok    
116.356      /api/alert/analyze  cluster_history_fetch               ok    
0.027        /api/alert/analyze  narrative_context_build             ok    
0.046        /api/alert/analyze  narrative_generation                ok    
1.866        /api/alert/analyze  response_serialization              ok    
4732.234     /api/alert/analyze  analyze_request_total               ok    
0.024        /api/alert/outcome  request_parse                       ok    
0.011        /api/alert/outcome  duplicate_feedback_guard            ok    
110.226      /api/alert/outcome  decision_lookup_and_outcome_update  ok    
6.775        /api/alert/outcome  outcome_audit_write                 ok    
663.459      /api/alert/outcome  learning_state_update               ok    
455.832      /api/alert/outcome  l5_conservation_write               ok    
460.075      /api/alert/outcome  conservation_monitor                ok    
0.441        /api/alert/outcome  profile_scorer_update               ok    
0.465        /api/alert/outcome  l5_dk_weight_write                  ok    
495.069      /api/alert/outcome  l5_centroid_write                   ok    
0.034        /api/alert/outcome  l5_dk_weight_write                  ok    
0.036        /api/alert/outcome  snapshot_evolution_logging          ok    
227.827      /api/alert/outcome  snapshot_evolution_logging          ok    
0.103        /api/alert/outcome  response_serialization              ok    
2472.0       /api/alert/outcome  outcome_request_total               ok    
```

### PHASED25-0018
- event_count: 45
- total_observed_ms: 12366.795
- authoritative_total_ms: 4616.82
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.024        /api/alert/analyze  scorer_readiness                    ok    
0.01         /api/alert/analyze  request_parse                       ok    
77.512       /api/alert/analyze  alert_lookup                        ok    
87.167       /api/alert/analyze  security_context_lookup             ok    
0.146        /api/alert/analyze  category_resolution                 ok    
316.957      /api/alert/analyze  factor_vector_construction          ok    
0.182        /api/alert/analyze  scorer_decision                     ok    
0.023        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.011        /api/alert/analyze  routing_threshold_lookup            ok    
0.025        /api/alert/analyze  rl_exploration_proposal             ok    
0.017        /api/alert/analyze  routing_zone_resolution             ok    
150.166      /api/alert/analyze  referral_history_counts             ok    
0.049        /api/alert/analyze  referral_gate_evaluation            ok    
95.656       /api/alert/analyze  reasoning_generation                ok    
81.679       /api/alert/analyze  decision_node_and_edge_write        ok    
94.21        /api/alert/analyze  audit_write                         ok    
0.278        /api/alert/analyze  metadata_logging_snapshot_write     ok    
3430.595     /api/alert/analyze  campaign_correlation                ok    
0.022        /api/alert/analyze  decision_event_emit                 ok    
72.911       /api/alert/analyze  composite_gate_evaluation           ok    
0.046        /api/alert/analyze  provenance_build                    ok    
82.013       /api/alert/analyze  graph_visualization_fetch           ok    
0.023        /api/alert/analyze  response_context_enrichment         ok    
0.025        /api/alert/analyze  referral_debug_build                ok    
0.034        /api/alert/analyze  shadow_compare_schedule             ok    
80.894       /api/alert/analyze  cluster_history_fetch               ok    
0.025        /api/alert/analyze  narrative_context_build             ok    
0.035        /api/alert/analyze  narrative_generation                ok    
2.101        /api/alert/analyze  response_serialization              ok    
4616.82      /api/alert/analyze  analyze_request_total               ok    
0.013        /api/alert/outcome  request_parse                       ok    
0.01         /api/alert/outcome  duplicate_feedback_guard            ok    
85.625       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.189        /api/alert/outcome  outcome_audit_write                 ok    
91.353       /api/alert/outcome  learning_state_update               ok    
406.625      /api/alert/outcome  l5_conservation_write               ok    
407.854      /api/alert/outcome  conservation_monitor                ok    
0.122        /api/alert/outcome  profile_scorer_update               ok    
0.109        /api/alert/outcome  l5_dk_weight_write                  ok    
399.149      /api/alert/outcome  l5_centroid_write                   ok    
0.017        /api/alert/outcome  l5_dk_weight_write                  ok    
0.018        /api/alert/outcome  snapshot_evolution_logging          ok    
130.357      /api/alert/outcome  snapshot_evolution_logging          ok    
0.03         /api/alert/outcome  response_serialization              ok    
1655.668     /api/alert/outcome  outcome_request_total               ok    
```

### PHASED25-0014
- event_count: 45
- total_observed_ms: 13308.347
- authoritative_total_ms: 4405.535
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.02         /api/alert/analyze  scorer_readiness                    ok    
0.012        /api/alert/analyze  request_parse                       ok    
78.931       /api/alert/analyze  alert_lookup                        ok    
79.468       /api/alert/analyze  security_context_lookup             ok    
0.222        /api/alert/analyze  category_resolution                 ok    
338.302      /api/alert/analyze  factor_vector_construction          ok    
0.331        /api/alert/analyze  scorer_decision                     ok    
0.035        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.017        /api/alert/analyze  routing_threshold_lookup            ok    
0.029        /api/alert/analyze  rl_exploration_proposal             ok    
0.04         /api/alert/analyze  routing_zone_resolution             ok    
161.227      /api/alert/analyze  referral_history_counts             ok    
0.075        /api/alert/analyze  referral_gate_evaluation            ok    
70.935       /api/alert/analyze  reasoning_generation                ok    
80.826       /api/alert/analyze  decision_node_and_edge_write        ok    
76.226       /api/alert/analyze  audit_write                         ok    
0.692        /api/alert/analyze  metadata_logging_snapshot_write     ok    
3172.3       /api/alert/analyze  campaign_correlation                ok    
0.021        /api/alert/analyze  decision_event_emit                 ok    
84.054       /api/alert/analyze  composite_gate_evaluation           ok    
0.039        /api/alert/analyze  provenance_build                    ok    
83.72        /api/alert/analyze  graph_visualization_fetch           ok    
0.026        /api/alert/analyze  response_context_enrichment         ok    
0.026        /api/alert/analyze  referral_debug_build                ok    
0.01         /api/alert/analyze  shadow_compare_schedule             ok    
128.35       /api/alert/analyze  cluster_history_fetch               ok    
0.024        /api/alert/analyze  narrative_context_build             ok    
0.034        /api/alert/analyze  narrative_generation                ok    
1.722        /api/alert/analyze  response_serialization              ok    
4405.535     /api/alert/analyze  analyze_request_total               ok    
0.023        /api/alert/outcome  request_parse                       ok    
0.023        /api/alert/outcome  duplicate_feedback_guard            ok    
171.052      /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.637        /api/alert/outcome  outcome_audit_write                 ok    
172.037      /api/alert/outcome  learning_state_update               ok    
761.327      /api/alert/outcome  l5_conservation_write               ok    
762.461      /api/alert/outcome  conservation_monitor                ok    
0.12         /api/alert/outcome  profile_scorer_update               ok    
0.1          /api/alert/outcome  l5_dk_weight_write                  ok    
503.579      /api/alert/outcome  l5_centroid_write                   ok    
0.015        /api/alert/outcome  l5_dk_weight_write                  ok    
0.015        /api/alert/outcome  snapshot_evolution_logging          ok    
66.735       /api/alert/outcome  snapshot_evolution_logging          ok    
0.036        /api/alert/outcome  response_serialization              ok    
2106.938     /api/alert/outcome  outcome_request_total               ok    
```

### PHASED25-0016
- event_count: 45
- total_observed_ms: 11800.345
- authoritative_total_ms: 4288.276
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.022        /api/alert/analyze  scorer_readiness                    ok    
0.009        /api/alert/analyze  request_parse                       ok    
75.781       /api/alert/analyze  alert_lookup                        ok    
80.681       /api/alert/analyze  security_context_lookup             ok    
0.153        /api/alert/analyze  category_resolution                 ok    
323.519      /api/alert/analyze  factor_vector_construction          ok    
0.153        /api/alert/analyze  scorer_decision                     ok    
0.012        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.006        /api/alert/analyze  routing_threshold_lookup            ok    
0.011        /api/alert/analyze  rl_exploration_proposal             ok    
0.012        /api/alert/analyze  routing_zone_resolution             ok    
240.549      /api/alert/analyze  referral_history_counts             ok    
0.097        /api/alert/analyze  referral_gate_evaluation            ok    
77.487       /api/alert/analyze  reasoning_generation                ok    
71.046       /api/alert/analyze  decision_node_and_edge_write        ok    
77.628       /api/alert/analyze  audit_write                         ok    
0.309        /api/alert/analyze  metadata_logging_snapshot_write     ok    
3032.772     /api/alert/analyze  campaign_correlation                ok    
0.018        /api/alert/analyze  decision_event_emit                 ok    
99.265       /api/alert/analyze  composite_gate_evaluation           ok    
0.058        /api/alert/analyze  provenance_build                    ok    
82.445       /api/alert/analyze  graph_visualization_fetch           ok    
0.022        /api/alert/analyze  response_context_enrichment         ok    
0.026        /api/alert/analyze  referral_debug_build                ok    
0.009        /api/alert/analyze  shadow_compare_schedule             ok    
83.723       /api/alert/analyze  cluster_history_fetch               ok    
0.023        /api/alert/analyze  narrative_context_build             ok    
0.06         /api/alert/analyze  narrative_generation                ok    
2.724        /api/alert/analyze  response_serialization              ok    
4288.276     /api/alert/analyze  analyze_request_total               ok    
0.014        /api/alert/outcome  request_parse                       ok    
0.009        /api/alert/outcome  duplicate_feedback_guard            ok    
80.561       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.213        /api/alert/outcome  outcome_audit_write                 ok    
53.081       /api/alert/outcome  learning_state_update               ok    
385.678      /api/alert/outcome  l5_conservation_write               ok    
386.796      /api/alert/outcome  conservation_monitor                ok    
0.105        /api/alert/outcome  profile_scorer_update               ok    
0.088        /api/alert/outcome  l5_dk_weight_write                  ok    
528.897      /api/alert/outcome  l5_centroid_write                   ok    
0.019        /api/alert/outcome  l5_dk_weight_write                  ok    
0.022        /api/alert/outcome  snapshot_evolution_logging          ok    
80.571       /api/alert/outcome  snapshot_evolution_logging          ok    
0.042        /api/alert/outcome  response_serialization              ok    
1747.353     /api/alert/outcome  outcome_request_total               ok    
```

### PHASED25-0013
- event_count: 45
- total_observed_ms: 11384.247
- authoritative_total_ms: 4053.19
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.019        /api/alert/analyze  scorer_readiness                    ok    
0.008        /api/alert/analyze  request_parse                       ok    
78.15        /api/alert/analyze  alert_lookup                        ok    
94.311       /api/alert/analyze  security_context_lookup             ok    
0.188        /api/alert/analyze  category_resolution                 ok    
363.335      /api/alert/analyze  factor_vector_construction          ok    
0.216        /api/alert/analyze  scorer_decision                     ok    
0.02         /api/alert/analyze  post_scorer_confidence_gate         ok    
0.014        /api/alert/analyze  routing_threshold_lookup            ok    
0.02         /api/alert/analyze  rl_exploration_proposal             ok    
0.032        /api/alert/analyze  routing_zone_resolution             ok    
183.953      /api/alert/analyze  referral_history_counts             ok    
0.048        /api/alert/analyze  referral_gate_evaluation            ok    
76.183       /api/alert/analyze  reasoning_generation                ok    
80.507       /api/alert/analyze  decision_node_and_edge_write        ok    
77.784       /api/alert/analyze  audit_write                         ok    
0.159        /api/alert/analyze  metadata_logging_snapshot_write     ok    
2724.251     /api/alert/analyze  campaign_correlation                ok    
0.024        /api/alert/analyze  decision_event_emit                 ok    
85.799       /api/alert/analyze  composite_gate_evaluation           ok    
0.039        /api/alert/analyze  provenance_build                    ok    
134.187      /api/alert/analyze  graph_visualization_fetch           ok    
0.02         /api/alert/analyze  response_context_enrichment         ok    
0.02         /api/alert/analyze  referral_debug_build                ok    
0.009        /api/alert/analyze  shadow_compare_schedule             ok    
98.498       /api/alert/analyze  cluster_history_fetch               ok    
0.127        /api/alert/analyze  narrative_context_build             ok    
0.134        /api/alert/analyze  narrative_generation                ok    
8.55         /api/alert/analyze  response_serialization              ok    
4053.19      /api/alert/analyze  analyze_request_total               ok    
0.013        /api/alert/outcome  request_parse                       ok    
0.012        /api/alert/outcome  duplicate_feedback_guard            ok    
88.477       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.349        /api/alert/outcome  outcome_audit_write                 ok    
103.173      /api/alert/outcome  learning_state_update               ok    
421.569      /api/alert/outcome  l5_conservation_write               ok    
423.141      /api/alert/outcome  conservation_monitor                ok    
0.185        /api/alert/outcome  profile_scorer_update               ok    
0.158        /api/alert/outcome  l5_dk_weight_write                  ok    
406.027      /api/alert/outcome  l5_centroid_write                   ok    
0.019        /api/alert/outcome  l5_dk_weight_write                  ok    
0.022        /api/alert/outcome  snapshot_evolution_logging          ok    
203.942      /api/alert/outcome  snapshot_evolution_logging          ok    
0.038        /api/alert/outcome  response_serialization              ok    
1677.327     /api/alert/outcome  outcome_request_total               ok    
```

### PHASED25-0012
- event_count: 45
- total_observed_ms: 9899.604
- authoritative_total_ms: 3419.175
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.016        /api/alert/analyze  scorer_readiness                    ok    
0.007        /api/alert/analyze  request_parse                       ok    
78.412       /api/alert/analyze  alert_lookup                        ok    
88.719       /api/alert/analyze  security_context_lookup             ok    
0.134        /api/alert/analyze  category_resolution                 ok    
313.01       /api/alert/analyze  factor_vector_construction          ok    
0.196        /api/alert/analyze  scorer_decision                     ok    
0.016        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.007        /api/alert/analyze  routing_threshold_lookup            ok    
0.017        /api/alert/analyze  rl_exploration_proposal             ok    
0.018        /api/alert/analyze  routing_zone_resolution             ok    
173.973      /api/alert/analyze  referral_history_counts             ok    
0.037        /api/alert/analyze  referral_gate_evaluation            ok    
77.544       /api/alert/analyze  reasoning_generation                ok    
90.318       /api/alert/analyze  decision_node_and_edge_write        ok    
79.378       /api/alert/analyze  audit_write                         ok    
0.263        /api/alert/analyze  metadata_logging_snapshot_write     ok    
2263.378     /api/alert/analyze  campaign_correlation                ok    
0.04         /api/alert/analyze  decision_event_emit                 ok    
72.514       /api/alert/analyze  composite_gate_evaluation           ok    
0.074        /api/alert/analyze  provenance_build                    ok    
73.01        /api/alert/analyze  graph_visualization_fetch           ok    
0.023        /api/alert/analyze  response_context_enrichment         ok    
0.033        /api/alert/analyze  referral_debug_build                ok    
0.012        /api/alert/analyze  shadow_compare_schedule             ok    
65.547       /api/alert/analyze  cluster_history_fetch               ok    
0.04         /api/alert/analyze  narrative_context_build             ok    
0.046        /api/alert/analyze  narrative_generation                ok    
2.319        /api/alert/analyze  response_serialization              ok    
3419.175     /api/alert/analyze  analyze_request_total               ok    
0.011        /api/alert/outcome  request_parse                       ok    
0.009        /api/alert/outcome  duplicate_feedback_guard            ok    
77.678       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.321        /api/alert/outcome  outcome_audit_write                 ok    
105.714      /api/alert/outcome  learning_state_update               ok    
414.141      /api/alert/outcome  l5_conservation_write               ok    
415.242      /api/alert/outcome  conservation_monitor                ok    
0.241        /api/alert/outcome  profile_scorer_update               ok    
0.267        /api/alert/outcome  l5_dk_weight_write                  ok    
416.999      /api/alert/outcome  l5_centroid_write                   ok    
0.024        /api/alert/outcome  l5_dk_weight_write                  ok    
0.025        /api/alert/outcome  snapshot_evolution_logging          ok    
91.722       /api/alert/outcome  snapshot_evolution_logging          ok    
0.05         /api/alert/outcome  response_serialization              ok    
1578.884     /api/alert/outcome  outcome_request_total               ok    
```

### PHASED25-0011
- event_count: 45
- total_observed_ms: 9536.006
- authoritative_total_ms: 3339.119
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.011        /api/alert/analyze  scorer_readiness                    ok    
0.006        /api/alert/analyze  request_parse                       ok    
71.394       /api/alert/analyze  alert_lookup                        ok    
91.653       /api/alert/analyze  security_context_lookup             ok    
0.126        /api/alert/analyze  category_resolution                 ok    
314.828      /api/alert/analyze  factor_vector_construction          ok    
0.181        /api/alert/analyze  scorer_decision                     ok    
0.019        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.013        /api/alert/analyze  routing_threshold_lookup            ok    
0.013        /api/alert/analyze  rl_exploration_proposal             ok    
0.014        /api/alert/analyze  routing_zone_resolution             ok    
176.947      /api/alert/analyze  referral_history_counts             ok    
0.038        /api/alert/analyze  referral_gate_evaluation            ok    
75.233       /api/alert/analyze  reasoning_generation                ok    
78.494       /api/alert/analyze  decision_node_and_edge_write        ok    
72.143       /api/alert/analyze  audit_write                         ok    
0.16         /api/alert/analyze  metadata_logging_snapshot_write     ok    
2179.108     /api/alert/analyze  campaign_correlation                ok    
0.021        /api/alert/analyze  decision_event_emit                 ok    
83.184       /api/alert/analyze  composite_gate_evaluation           ok    
0.039        /api/alert/analyze  provenance_build                    ok    
72.795       /api/alert/analyze  graph_visualization_fetch           ok    
0.021        /api/alert/analyze  response_context_enrichment         ok    
0.026        /api/alert/analyze  referral_debug_build                ok    
0.023        /api/alert/analyze  shadow_compare_schedule             ok    
81.883       /api/alert/analyze  cluster_history_fetch               ok    
0.043        /api/alert/analyze  narrative_context_build             ok    
0.063        /api/alert/analyze  narrative_generation                ok    
3.257        /api/alert/analyze  response_serialization              ok    
3339.119     /api/alert/analyze  analyze_request_total               ok    
0.013        /api/alert/outcome  request_parse                       ok    
0.021        /api/alert/outcome  duplicate_feedback_guard            ok    
82.366       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.218        /api/alert/outcome  outcome_audit_write                 ok    
114.305      /api/alert/outcome  learning_state_update               ok    
371.794      /api/alert/outcome  l5_conservation_write               ok    
373.6        /api/alert/outcome  conservation_monitor                ok    
0.263        /api/alert/outcome  profile_scorer_update               ok    
0.227        /api/alert/outcome  l5_dk_weight_write                  ok    
421.919      /api/alert/outcome  l5_centroid_write                   ok    
0.014        /api/alert/outcome  l5_dk_weight_write                  ok    
0.019        /api/alert/outcome  snapshot_evolution_logging          ok    
79.543       /api/alert/outcome  snapshot_evolution_logging          ok    
0.03         /api/alert/outcome  response_serialization              ok    
1450.819     /api/alert/outcome  outcome_request_total               ok    
```

### PHASED25-0010
- event_count: 45
- total_observed_ms: 9551.917
- authoritative_total_ms: 3324.529
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.019        /api/alert/analyze  scorer_readiness                    ok    
0.016        /api/alert/analyze  request_parse                       ok    
68.537       /api/alert/analyze  alert_lookup                        ok    
79.848       /api/alert/analyze  security_context_lookup             ok    
0.149        /api/alert/analyze  category_resolution                 ok    
312.959      /api/alert/analyze  factor_vector_construction          ok    
0.336        /api/alert/analyze  scorer_decision                     ok    
0.034        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.017        /api/alert/analyze  routing_threshold_lookup            ok    
0.03         /api/alert/analyze  rl_exploration_proposal             ok    
0.036        /api/alert/analyze  routing_zone_resolution             ok    
167.345      /api/alert/analyze  referral_history_counts             ok    
0.06         /api/alert/analyze  referral_gate_evaluation            ok    
75.87        /api/alert/analyze  reasoning_generation                ok    
74.652       /api/alert/analyze  decision_node_and_edge_write        ok    
80.21        /api/alert/analyze  audit_write                         ok    
0.215        /api/alert/analyze  metadata_logging_snapshot_write     ok    
2176.413     /api/alert/analyze  campaign_correlation                ok    
0.021        /api/alert/analyze  decision_event_emit                 ok    
67.458       /api/alert/analyze  composite_gate_evaluation           ok    
0.073        /api/alert/analyze  provenance_build                    ok    
80.764       /api/alert/analyze  graph_visualization_fetch           ok    
0.027        /api/alert/analyze  response_context_enrichment         ok    
0.048        /api/alert/analyze  referral_debug_build                ok    
0.026        /api/alert/analyze  shadow_compare_schedule             ok    
85.987       /api/alert/analyze  cluster_history_fetch               ok    
0.028        /api/alert/analyze  narrative_context_build             ok    
0.05         /api/alert/analyze  narrative_generation                ok    
2.015        /api/alert/analyze  response_serialization              ok    
3324.529     /api/alert/analyze  analyze_request_total               ok    
0.025        /api/alert/outcome  request_parse                       ok    
0.007        /api/alert/outcome  duplicate_feedback_guard            ok    
93.587       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.444        /api/alert/outcome  outcome_audit_write                 ok    
86.313       /api/alert/outcome  learning_state_update               ok    
383.3        /api/alert/outcome  l5_conservation_write               ok    
385.929      /api/alert/outcome  conservation_monitor                ok    
0.246        /api/alert/outcome  profile_scorer_update               ok    
0.244        /api/alert/outcome  l5_dk_weight_write                  ok    
400.638      /api/alert/outcome  l5_centroid_write                   ok    
0.017        /api/alert/outcome  l5_dk_weight_write                  ok    
0.026        /api/alert/outcome  snapshot_evolution_logging          ok    
77.561       /api/alert/outcome  snapshot_evolution_logging          ok    
0.027        /api/alert/outcome  response_serialization              ok    
1525.781     /api/alert/outcome  outcome_request_total               ok    
```

### PHASED25-0005
- event_count: 45
- total_observed_ms: 9245.25
- authoritative_total_ms: 3149.972
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.026        /api/alert/analyze  scorer_readiness                    ok    
0.012        /api/alert/analyze  request_parse                       ok    
79.849       /api/alert/analyze  alert_lookup                        ok    
83.986       /api/alert/analyze  security_context_lookup             ok    
0.195        /api/alert/analyze  category_resolution                 ok    
298.311      /api/alert/analyze  factor_vector_construction          ok    
0.453        /api/alert/analyze  scorer_decision                     ok    
0.027        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.012        /api/alert/analyze  routing_threshold_lookup            ok    
0.021        /api/alert/analyze  rl_exploration_proposal             ok    
0.026        /api/alert/analyze  routing_zone_resolution             ok    
201.53       /api/alert/analyze  referral_history_counts             ok    
0.109        /api/alert/analyze  referral_gate_evaluation            ok    
96.683       /api/alert/analyze  reasoning_generation                ok    
78.455       /api/alert/analyze  decision_node_and_edge_write        ok    
89.603       /api/alert/analyze  audit_write                         ok    
0.296        /api/alert/analyze  metadata_logging_snapshot_write     ok    
1836.756     /api/alert/analyze  campaign_correlation                ok    
0.047        /api/alert/analyze  decision_event_emit                 ok    
115.377      /api/alert/analyze  composite_gate_evaluation           ok    
0.1          /api/alert/analyze  provenance_build                    ok    
92.407       /api/alert/analyze  graph_visualization_fetch           ok    
0.041        /api/alert/analyze  response_context_enrichment         ok    
0.642        /api/alert/analyze  referral_debug_build                ok    
0.051        /api/alert/analyze  shadow_compare_schedule             ok    
102.2        /api/alert/analyze  cluster_history_fetch               ok    
0.064        /api/alert/analyze  narrative_context_build             ok    
0.197        /api/alert/analyze  narrative_generation                ok    
5.769        /api/alert/analyze  response_serialization              ok    
3149.972     /api/alert/analyze  analyze_request_total               ok    
0.024        /api/alert/outcome  request_parse                       ok    
0.015        /api/alert/outcome  duplicate_feedback_guard            ok    
91.758       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.256        /api/alert/outcome  outcome_audit_write                 ok    
110.992      /api/alert/outcome  learning_state_update               ok    
403.16       /api/alert/outcome  l5_conservation_write               ok    
405.448      /api/alert/outcome  conservation_monitor                ok    
0.171        /api/alert/outcome  profile_scorer_update               ok    
0.13         /api/alert/outcome  l5_dk_weight_write                  ok    
368.327      /api/alert/outcome  l5_centroid_write                   ok    
0.02         /api/alert/outcome  l5_dk_weight_write                  ok    
0.019        /api/alert/outcome  snapshot_evolution_logging          ok    
86.924       /api/alert/outcome  snapshot_evolution_logging          ok    
0.038        /api/alert/outcome  response_serialization              ok    
1544.751     /api/alert/outcome  outcome_request_total               ok    
```

### PHASED25-0009
- event_count: 45
- total_observed_ms: 9149.365
- authoritative_total_ms: 3068.735
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.031        /api/alert/analyze  scorer_readiness                    ok    
0.009        /api/alert/analyze  request_parse                       ok    
80.572       /api/alert/analyze  alert_lookup                        ok    
83.65        /api/alert/analyze  security_context_lookup             ok    
0.163        /api/alert/analyze  category_resolution                 ok    
318.532      /api/alert/analyze  factor_vector_construction          ok    
0.549        /api/alert/analyze  scorer_decision                     ok    
0.035        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.017        /api/alert/analyze  routing_threshold_lookup            ok    
0.023        /api/alert/analyze  rl_exploration_proposal             ok    
0.023        /api/alert/analyze  routing_zone_resolution             ok    
137.891      /api/alert/analyze  referral_history_counts             ok    
0.048        /api/alert/analyze  referral_gate_evaluation            ok    
99.535       /api/alert/analyze  reasoning_generation                ok    
86.839       /api/alert/analyze  decision_node_and_edge_write        ok    
69.242       /api/alert/analyze  audit_write                         ok    
0.185        /api/alert/analyze  metadata_logging_snapshot_write     ok    
1855.544     /api/alert/analyze  campaign_correlation                ok    
0.027        /api/alert/analyze  decision_event_emit                 ok    
70.74        /api/alert/analyze  composite_gate_evaluation           ok    
0.058        /api/alert/analyze  provenance_build                    ok    
96.794       /api/alert/analyze  graph_visualization_fetch           ok    
0.061        /api/alert/analyze  response_context_enrichment         ok    
0.043        /api/alert/analyze  referral_debug_build                ok    
0.013        /api/alert/analyze  shadow_compare_schedule             ok    
103.19       /api/alert/analyze  cluster_history_fetch               ok    
0.06         /api/alert/analyze  narrative_context_build             ok    
0.15         /api/alert/analyze  narrative_generation                ok    
7.767        /api/alert/analyze  response_serialization              ok    
3068.735     /api/alert/analyze  analyze_request_total               ok    
0.021        /api/alert/outcome  request_parse                       ok    
0.025        /api/alert/outcome  duplicate_feedback_guard            ok    
95.002       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.426        /api/alert/outcome  outcome_audit_write                 ok    
123.189      /api/alert/outcome  learning_state_update               ok    
407.724      /api/alert/outcome  l5_conservation_write               ok    
410.815      /api/alert/outcome  conservation_monitor                ok    
0.299        /api/alert/outcome  profile_scorer_update               ok    
0.208        /api/alert/outcome  l5_dk_weight_write                  ok    
419.23       /api/alert/outcome  l5_centroid_write                   ok    
0.023        /api/alert/outcome  l5_dk_weight_write                  ok    
0.02         /api/alert/outcome  snapshot_evolution_logging          ok    
84.362       /api/alert/outcome  snapshot_evolution_logging          ok    
0.036        /api/alert/outcome  response_serialization              ok    
1527.459     /api/alert/outcome  outcome_request_total               ok    
```

### PHASED25-0008
- event_count: 45
- total_observed_ms: 10437.66
- authoritative_total_ms: 2946.086
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.018        /api/alert/analyze  scorer_readiness                    ok    
0.006        /api/alert/analyze  request_parse                       ok    
61.4         /api/alert/analyze  alert_lookup                        ok    
67.486       /api/alert/analyze  security_context_lookup             ok    
0.172        /api/alert/analyze  category_resolution                 ok    
395.986      /api/alert/analyze  factor_vector_construction          ok    
0.279        /api/alert/analyze  scorer_decision                     ok    
0.017        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.014        /api/alert/analyze  routing_threshold_lookup            ok    
0.014        /api/alert/analyze  rl_exploration_proposal             ok    
0.029        /api/alert/analyze  routing_zone_resolution             ok    
162.099      /api/alert/analyze  referral_history_counts             ok    
0.068        /api/alert/analyze  referral_gate_evaluation            ok    
115.391      /api/alert/analyze  reasoning_generation                ok    
88.464       /api/alert/analyze  decision_node_and_edge_write        ok    
89.239       /api/alert/analyze  audit_write                         ok    
0.139        /api/alert/analyze  metadata_logging_snapshot_write     ok    
1684.199     /api/alert/analyze  campaign_correlation                ok    
0.029        /api/alert/analyze  decision_event_emit                 ok    
75.31        /api/alert/analyze  composite_gate_evaluation           ok    
0.112        /api/alert/analyze  provenance_build                    ok    
76.723       /api/alert/analyze  graph_visualization_fetch           ok    
0.053        /api/alert/analyze  response_context_enrichment         ok    
0.046        /api/alert/analyze  referral_debug_build                ok    
0.037        /api/alert/analyze  shadow_compare_schedule             ok    
75.842       /api/alert/analyze  cluster_history_fetch               ok    
0.041        /api/alert/analyze  narrative_context_build             ok    
0.08         /api/alert/analyze  narrative_generation                ok    
3.995        /api/alert/analyze  response_serialization              ok    
2946.086     /api/alert/analyze  analyze_request_total               ok    
0.022        /api/alert/outcome  request_parse                       ok    
0.024        /api/alert/outcome  duplicate_feedback_guard            ok    
78.442       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.287        /api/alert/outcome  outcome_audit_write                 ok    
780.171      /api/alert/outcome  learning_state_update               ok    
459.734      /api/alert/outcome  l5_conservation_write               ok    
461.267      /api/alert/outcome  conservation_monitor                ok    
0.167        /api/alert/outcome  profile_scorer_update               ok    
0.127        /api/alert/outcome  l5_dk_weight_write                  ok    
450.511      /api/alert/outcome  l5_centroid_write                   ok    
0.028        /api/alert/outcome  l5_dk_weight_write                  ok    
0.033        /api/alert/outcome  snapshot_evolution_logging          ok    
79.062       /api/alert/outcome  snapshot_evolution_logging          ok    
0.022        /api/alert/outcome  response_serialization              ok    
2284.389     /api/alert/outcome  outcome_request_total               ok    
```

### PHASED25-0006
- event_count: 45
- total_observed_ms: 8887.186
- authoritative_total_ms: 2810.569
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.019        /api/alert/analyze  scorer_readiness                    ok    
0.007        /api/alert/analyze  request_parse                       ok    
80.808       /api/alert/analyze  alert_lookup                        ok    
88.217       /api/alert/analyze  security_context_lookup             ok    
0.229        /api/alert/analyze  category_resolution                 ok    
335.157      /api/alert/analyze  factor_vector_construction          ok    
0.222        /api/alert/analyze  scorer_decision                     ok    
0.016        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.012        /api/alert/analyze  routing_threshold_lookup            ok    
0.014        /api/alert/analyze  rl_exploration_proposal             ok    
0.019        /api/alert/analyze  routing_zone_resolution             ok    
167.068      /api/alert/analyze  referral_history_counts             ok    
0.047        /api/alert/analyze  referral_gate_evaluation            ok    
100.484      /api/alert/analyze  reasoning_generation                ok    
77.989       /api/alert/analyze  decision_node_and_edge_write        ok    
69.701       /api/alert/analyze  audit_write                         ok    
0.158        /api/alert/analyze  metadata_logging_snapshot_write     ok    
1537.204     /api/alert/analyze  campaign_correlation                ok    
0.061        /api/alert/analyze  decision_event_emit                 ok    
103.584      /api/alert/analyze  composite_gate_evaluation           ok    
0.144        /api/alert/analyze  provenance_build                    ok    
96.101       /api/alert/analyze  graph_visualization_fetch           ok    
0.074        /api/alert/analyze  response_context_enrichment         ok    
0.082        /api/alert/analyze  referral_debug_build                ok    
0.039        /api/alert/analyze  shadow_compare_schedule             ok    
94.783       /api/alert/analyze  cluster_history_fetch               ok    
0.03         /api/alert/analyze  narrative_context_build             ok    
0.052        /api/alert/analyze  narrative_generation                ok    
2.651        /api/alert/analyze  response_serialization              ok    
2810.569     /api/alert/analyze  analyze_request_total               ok    
0.031        /api/alert/outcome  request_parse                       ok    
0.046        /api/alert/outcome  duplicate_feedback_guard            ok    
84.464       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.229        /api/alert/outcome  outcome_audit_write                 ok    
123.627      /api/alert/outcome  learning_state_update               ok    
471.203      /api/alert/outcome  l5_conservation_write               ok    
473.269      /api/alert/outcome  conservation_monitor                ok    
0.166        /api/alert/outcome  profile_scorer_update               ok    
0.128        /api/alert/outcome  l5_dk_weight_write                  ok    
411.696      /api/alert/outcome  l5_centroid_write                   ok    
0.018        /api/alert/outcome  l5_dk_weight_write                  ok    
0.044        /api/alert/outcome  snapshot_evolution_logging          ok    
102.399      /api/alert/outcome  snapshot_evolution_logging          ok    
0.026        /api/alert/outcome  response_serialization              ok    
1654.299     /api/alert/outcome  outcome_request_total               ok    
```

## Nested Phase Warning
Nested phase durations should not be summed blindly. Use analyze_request_total, outcome_request_total, or total_attempt as authoritative totals.
