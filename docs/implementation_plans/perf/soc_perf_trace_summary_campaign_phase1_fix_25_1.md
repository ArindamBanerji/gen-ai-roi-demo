# SOC Perf Trace Summary

## Safety
- Read-only summary of existing JSONL trace events.
- No backend, graph, proof, or seed operations are performed.
- Nested phases are not additive; request-total phases are the authoritative route totals.

## Input
- trace_jsonl: `C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50\scratch\temp\soc_perf_trace_campaign_phase1_fix_25_1.jsonl`
- events_loaded: 1270
- malformed_lines: 0
- route_filter: None
- phase_filter: None

## Route + Phase Aggregates
```text
route_phase                                                     count  avg_ms    p50_ms    p95_ms    p99_ms    max_ms  
--------------------------------------------------------------  -----  --------  --------  --------  --------  --------
/api/alert/outcome | outcome_request_total                      25     1939.655  1959.433  2198.802  2353.851  2401.812
/api/alert/analyze | analyze_request_total                      25     1993.576  2089.351  2199.223  2219.017  2224.361
/api/alert/analyze | campaign_correlation                       25     550.007   676.23    738.657   763.75    771.225 
/api/alert/analyze | campaign_correlation_summary               25     469.308   572.904   633.752   640.157   641.279 
/api/alert/outcome | l5_centroid_write                          25     518.707   520.962   582.609   601.545   606.74  
/api/alert/outcome | conservation_monitor                       25     500.471   509.791   576.719   586.993   588.537 
/api/alert/outcome | l5_conservation_write                      25     497.496   507.108   573.37    584.636   586.42  
/api/alert/outcome | learning_state_update                      25     191.853   170.718   420.807   509.516   520.98  
/api/alert/analyze | factor_vector_construction                 25     381.795   381.267   430.15    486.12    503.543 
/api/alert/analyze | reasoning_generation                       25     121.552   102.167   313.305   395.852   412.589 
/api/alert/analyze | referral_history_counts                    25     187.271   188.794   214.805   217.813   218.536 
/api/alert/outcome | snapshot_evolution_logging                 50     52.799    40.878    126.901   140.314   147.339 
/api/alert/outcome | decision_lookup_and_outcome_update         25     104.485   104.391   126.323   141.689   146.339 
/api/alert/analyze | audit_write                                25     100.884   101.705   118.531   130.81    134.308 
/api/alert/analyze | campaign_query_create_campaign             6      101.267   97.704    124.644   131.042   132.642 
/api/alert/analyze | decision_node_and_edge_write               25     101.536   102.824   116.396   123.819   125.788 
/api/alert/analyze | campaign_query_member_edges_batch_create   19     89.28     84.417    109.603   121.609   124.61  
/api/alert/analyze | cluster_history_fetch                      25     93.139    91.392    110.391   120.863   123.501 
/api/alert/analyze | security_context_lookup                    25     96.466    96.94     117.998   120.898   121.603 
/api/alert/analyze | composite_gate_evaluation                  25     94.838    95.557    112.744   118.962   120.566 
/api/alert/analyze | campaign_query_member_edges_existing_read  19     101.05    102.533   113.953   115.474   115.854 
/api/alert/analyze | campaign_query_update_campaign             13     96.126    92.482    110.757   112.827   113.345 
/api/alert/analyze | alert_lookup                               25     91.227    91.837    107.713   111.927   113.199 
/api/alert/analyze | graph_visualization_fetch                  25     94.984    96.411    107.7     110.835   111.731 
/api/alert/analyze | campaign_query_member_alert_nodes_read     19     93.156    91.07     110.048   111.35    111.675 
/api/alert/analyze | campaign_query_fetch_recent_events         25     97.143    97.267    109.336   110.335   110.627 
/api/alert/analyze | campaign_query_check_campaign_exists       19     89.709    89.936    98.83     99.972    100.257 
/api/alert/analyze | metadata_logging_snapshot_write            25     1.081     0.395     2.651     10.988    13.582  
/api/alert/outcome | profile_scorer_update                      25     0.786     0.318     0.476     9.267     12.041  
/api/alert/analyze | response_serialization                     25     4.974     4.798     7.336     8.846     9.257   
/api/alert/analyze | post_scorer_confidence_gate                25     0.256     0.038     0.113     4.175     5.453   
/api/alert/analyze | category_resolution                        25     0.38      0.264     0.574     2.361     2.923   
/api/alert/outcome | l5_dk_weight_write                         50     0.217     0.085     0.658     1.735     2.632   
/api/alert/outcome | outcome_audit_write                        25     0.698     0.464     1.858     2.079     2.14    
/api/alert/analyze | referral_debug_build                       25     0.113     0.063     0.103     1.011     1.297   
/api/alert/analyze | scorer_decision                            25     0.497     0.479     0.736     0.81      0.833   
/api/alert/analyze | narrative_generation                       25     0.138     0.102     0.324     0.456     0.495   
/api/alert/analyze | provenance_build                           25     0.142     0.136     0.22      0.385     0.434   
/api/alert/analyze | response_context_enrichment                25     0.067     0.054     0.081     0.345     0.428   
/api/alert/analyze | decision_event_emit                        25     0.075     0.056     0.24      0.29      0.295   
```

## Phase Aggregates
```text
phase                                      count  avg_ms    p50_ms    p95_ms    p99_ms    max_ms  
-----------------------------------------  -----  --------  --------  --------  --------  --------
outcome_request_total                      25     1939.655  1959.433  2198.802  2353.851  2401.812
analyze_request_total                      25     1993.576  2089.351  2199.223  2219.017  2224.361
campaign_correlation                       25     550.007   676.23    738.657   763.75    771.225 
campaign_correlation_summary               25     469.308   572.904   633.752   640.157   641.279 
l5_centroid_write                          25     518.707   520.962   582.609   601.545   606.74  
conservation_monitor                       25     500.471   509.791   576.719   586.993   588.537 
l5_conservation_write                      25     497.496   507.108   573.37    584.636   586.42  
learning_state_update                      25     191.853   170.718   420.807   509.516   520.98  
factor_vector_construction                 25     381.795   381.267   430.15    486.12    503.543 
reasoning_generation                       25     121.552   102.167   313.305   395.852   412.589 
referral_history_counts                    25     187.271   188.794   214.805   217.813   218.536 
snapshot_evolution_logging                 50     52.799    40.878    126.901   140.314   147.339 
decision_lookup_and_outcome_update         25     104.485   104.391   126.323   141.689   146.339 
audit_write                                25     100.884   101.705   118.531   130.81    134.308 
campaign_query_create_campaign             6      101.267   97.704    124.644   131.042   132.642 
decision_node_and_edge_write               25     101.536   102.824   116.396   123.819   125.788 
campaign_query_member_edges_batch_create   19     89.28     84.417    109.603   121.609   124.61  
cluster_history_fetch                      25     93.139    91.392    110.391   120.863   123.501 
security_context_lookup                    25     96.466    96.94     117.998   120.898   121.603 
composite_gate_evaluation                  25     94.838    95.557    112.744   118.962   120.566 
campaign_query_member_edges_existing_read  19     101.05    102.533   113.953   115.474   115.854 
campaign_query_update_campaign             13     96.126    92.482    110.757   112.827   113.345 
alert_lookup                               25     91.227    91.837    107.713   111.927   113.199 
graph_visualization_fetch                  25     94.984    96.411    107.7     110.835   111.731 
campaign_query_member_alert_nodes_read     19     93.156    91.07     110.048   111.35    111.675 
campaign_query_fetch_recent_events         25     97.143    97.267    109.336   110.335   110.627 
campaign_query_check_campaign_exists       19     89.709    89.936    98.83     99.972    100.257 
metadata_logging_snapshot_write            25     1.081     0.395     2.651     10.988    13.582  
profile_scorer_update                      25     0.786     0.318     0.476     9.267     12.041  
response_serialization                     50     2.511     1.585     6.185     8.419     9.257   
post_scorer_confidence_gate                25     0.256     0.038     0.113     4.175     5.453   
category_resolution                        25     0.38      0.264     0.574     2.361     2.923   
l5_dk_weight_write                         50     0.217     0.085     0.658     1.735     2.632   
outcome_audit_write                        25     0.698     0.464     1.858     2.079     2.14    
referral_debug_build                       25     0.113     0.063     0.103     1.011     1.297   
scorer_decision                            25     0.497     0.479     0.736     0.81      0.833   
narrative_generation                       25     0.138     0.102     0.324     0.456     0.495   
provenance_build                           25     0.142     0.136     0.22      0.385     0.434   
response_context_enrichment                25     0.067     0.054     0.081     0.345     0.428   
decision_event_emit                        25     0.075     0.056     0.24      0.29      0.295   
```

## Graph Aggregates
```text
graph_name                          count  avg_ms  p50_ms  p95_ms   p99_ms    max_ms  
----------------------------------  -----  ------  ------  -------  --------  --------
soc_graph_campaign_phase1_fix_25_1  1270   171.26  4.809   653.287  2133.053  2401.812
```

## Top Slow Events
```text
duration_ms  route               phase                  alert_id            decision_id                           attempt_index  status
-----------  ------------------  ---------------------  ------------------  ------------------------------------  -------------  ------
2401.812     /api/alert/outcome  outcome_request_total  CAMPAIGNP1FIX-0025  cda1d414-8304-4687-8fc3-7655be9ec145  None           ok    
2224.361     /api/alert/analyze  analyze_request_total  CAMPAIGNP1FIX-0024  34774f06-a7b2-4466-a383-df6ff123539b  None           ok    
2202.094     /api/alert/analyze  analyze_request_total  CAMPAIGNP1FIX-0012  b7d7e4ab-3169-45af-8617-d89ba37bfb94  None           ok    
2201.974     /api/alert/outcome  outcome_request_total  CAMPAIGNP1FIX-0005  59f8fa88-34a2-44d8-84f4-998d5bd22bc4  None           ok    
2187.739     /api/alert/analyze  analyze_request_total  CAMPAIGNP1FIX-0009  7a489584-4e8f-42e0-a37c-e6c3947c3f0e  None           ok    
2186.355     /api/alert/analyze  analyze_request_total  CAMPAIGNP1FIX-0017  f6738b69-19af-4fa2-9a37-fb38521671bb  None           ok    
2186.116     /api/alert/outcome  outcome_request_total  CAMPAIGNP1FIX-0001  0cd69e4a-7d20-47a1-8b11-916d08a6d47e  None           ok    
2179.198     /api/alert/analyze  analyze_request_total  CAMPAIGNP1FIX-0011  b9f20169-f963-46b6-bea4-b2477a7862fe  None           ok    
2165.986     /api/alert/analyze  analyze_request_total  CAMPAIGNP1FIX-0025  cda1d414-8304-4687-8fc3-7655be9ec145  None           ok    
2163.488     /api/alert/analyze  analyze_request_total  CAMPAIGNP1FIX-0016  b5efbee8-115d-4857-bc99-f8625539c92b  None           ok    
2156.863     /api/alert/analyze  analyze_request_total  CAMPAIGNP1FIX-0015  a0159fb7-e140-49b9-832a-3e16a58b06e2  None           ok    
2148.449     /api/alert/analyze  analyze_request_total  CAMPAIGNP1FIX-0013  f8a8be54-f338-46a7-b7e9-8e8cc3af120e  None           ok    
2147.554     /api/alert/analyze  analyze_request_total  CAMPAIGNP1FIX-0007  5fdea1b6-8967-48a7-8e1a-69372f399dd8  None           ok    
2126.538     /api/alert/analyze  analyze_request_total  CAMPAIGNP1FIX-0014  41e49407-e02f-40a5-ba9b-aadbf12cdcaa  None           ok    
2093.636     /api/alert/analyze  analyze_request_total  CAMPAIGNP1FIX-0010  ead71d8e-8e9a-451c-8929-03f795e3cd6d  None           ok    
2089.351     /api/alert/analyze  analyze_request_total  CAMPAIGNP1FIX-0022  a8898e30-d546-4776-ba8e-de6f516315de  None           ok    
2080.337     /api/alert/analyze  analyze_request_total  CAMPAIGNP1FIX-0019  962834b3-5fb7-4108-ab6c-f6ced099712b  None           ok    
2060.816     /api/alert/outcome  outcome_request_total  CAMPAIGNP1FIX-0004  a7e958dc-3657-4deb-b197-7fdc65a0d2d7  None           ok    
2039.488     /api/alert/analyze  analyze_request_total  CAMPAIGNP1FIX-0020  acc70bb1-a157-4828-be7c-912fdb5b688f  None           ok    
2034.531     /api/alert/outcome  outcome_request_total  CAMPAIGNP1FIX-0006  66887afa-7eb8-4566-a976-37a3bd445408  None           ok    
2034.253     /api/alert/outcome  outcome_request_total  CAMPAIGNP1FIX-0002  cec04a30-8765-403b-bfe4-1b57bba23e85  None           ok    
2027.664     /api/alert/analyze  analyze_request_total  CAMPAIGNP1FIX-0023  c44e2552-6bf4-4359-bf04-73944e3bee3e  None           ok    
2024.872     /api/alert/outcome  outcome_request_total  CAMPAIGNP1FIX-0009  7a489584-4e8f-42e0-a37c-e6c3947c3f0e  None           ok    
1998.993     /api/alert/outcome  outcome_request_total  CAMPAIGNP1FIX-0012  b7d7e4ab-3169-45af-8617-d89ba37bfb94  None           ok    
1996.639     /api/alert/outcome  outcome_request_total  CAMPAIGNP1FIX-0016  b5efbee8-115d-4857-bc99-f8625539c92b  None           ok    
1985.388     /api/alert/outcome  outcome_request_total  CAMPAIGNP1FIX-0024  34774f06-a7b2-4466-a383-df6ff123539b  None           ok    
1982.552     /api/alert/outcome  outcome_request_total  CAMPAIGNP1FIX-0015  a0159fb7-e140-49b9-832a-3e16a58b06e2  None           ok    
1980.225     /api/alert/analyze  analyze_request_total  CAMPAIGNP1FIX-0001  0cd69e4a-7d20-47a1-8b11-916d08a6d47e  None           ok    
1978.312     /api/alert/outcome  outcome_request_total  CAMPAIGNP1FIX-0019  962834b3-5fb7-4108-ab6c-f6ced099712b  None           ok    
1978.236     /api/alert/analyze  analyze_request_total  CAMPAIGNP1FIX-0003  234df384-d9f0-4c55-86e6-b143e08cb133  None           ok    
```

## Early/Mid/Late Windows
```text
(none)
```

## Per-Alert Waterfall

### CAMPAIGNP1FIX-0025
- event_count: 52
- total_observed_ms: 10129.991
- authoritative_total_ms: 2401.812
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.03         /api/alert/analyze  scorer_readiness                           ok    
0.021        /api/alert/analyze  request_parse                              ok    
92.916       /api/alert/analyze  alert_lookup                               ok    
97.303       /api/alert/analyze  security_context_lookup                    ok    
0.269        /api/alert/analyze  category_resolution                        ok    
411.97       /api/alert/analyze  factor_vector_construction                 ok    
0.516        /api/alert/analyze  scorer_decision                            ok    
0.044        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.018        /api/alert/analyze  routing_threshold_lookup                   ok    
0.032        /api/alert/analyze  rl_exploration_proposal                    ok    
0.031        /api/alert/analyze  routing_zone_resolution                    ok    
183.788      /api/alert/analyze  referral_history_counts                    ok    
0.083        /api/alert/analyze  referral_gate_evaluation                   ok    
74.413       /api/alert/analyze  reasoning_generation                       ok    
99.473       /api/alert/analyze  decision_node_and_edge_write               ok    
107.742      /api/alert/analyze  audit_write                                ok    
0.338        /api/alert/analyze  metadata_logging_snapshot_write            ok    
84.585       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
90.148       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
91.186       /api/alert/analyze  campaign_query_update_campaign             ok    
91.29        /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
111.675      /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
88.495       /api/alert/analyze  campaign_query_member_edges_batch_create   error 
576.743      /api/alert/analyze  campaign_correlation_summary               ok    
714.237      /api/alert/analyze  campaign_correlation                       ok    
0.056        /api/alert/analyze  decision_event_emit                        ok    
113.883      /api/alert/analyze  composite_gate_evaluation                  ok    
0.162        /api/alert/analyze  provenance_build                           ok    
95.172       /api/alert/analyze  graph_visualization_fetch                  ok    
0.056        /api/alert/analyze  response_context_enrichment                ok    
0.054        /api/alert/analyze  referral_debug_build                       ok    
0.047        /api/alert/analyze  shadow_compare_schedule                    ok    
90.771       /api/alert/analyze  cluster_history_fetch                      ok    
0.064        /api/alert/analyze  narrative_context_build                    ok    
0.119        /api/alert/analyze  narrative_generation                       ok    
5.393        /api/alert/analyze  response_serialization                     ok    
2165.986     /api/alert/analyze  analyze_request_total                      ok    
0.032        /api/alert/outcome  request_parse                              ok    
0.026        /api/alert/outcome  duplicate_feedback_guard                   ok    
146.339      /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.358        /api/alert/outcome  outcome_audit_write                        ok    
520.98       /api/alert/outcome  learning_state_update                      ok    
528.939      /api/alert/outcome  l5_conservation_write                      ok    
531.122      /api/alert/outcome  conservation_monitor                       ok    
0.255        /api/alert/outcome  profile_scorer_update                      ok    
0.282        /api/alert/outcome  l5_dk_weight_write                         ok    
502.713      /api/alert/outcome  l5_centroid_write                          ok    
0.045        /api/alert/outcome  l5_dk_weight_write                         ok    
0.071        /api/alert/outcome  snapshot_evolution_logging                 ok    
107.859      /api/alert/outcome  snapshot_evolution_logging                 ok    
0.049        /api/alert/outcome  response_serialization                     ok    
2401.812     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1FIX-0024
- event_count: 52
- total_observed_ms: 9566.853
- authoritative_total_ms: 2224.361
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.036        /api/alert/analyze  scorer_readiness                           ok    
0.022        /api/alert/analyze  request_parse                              ok    
85.018       /api/alert/analyze  alert_lookup                               ok    
97.158       /api/alert/analyze  security_context_lookup                    ok    
0.221        /api/alert/analyze  category_resolution                        ok    
426.962      /api/alert/analyze  factor_vector_construction                 ok    
0.706        /api/alert/analyze  scorer_decision                            ok    
0.04         /api/alert/analyze  post_scorer_confidence_gate                ok    
0.018        /api/alert/analyze  routing_threshold_lookup                   ok    
0.03         /api/alert/analyze  rl_exploration_proposal                    ok    
0.029        /api/alert/analyze  routing_zone_resolution                    ok    
191.652      /api/alert/analyze  referral_history_counts                    ok    
0.077        /api/alert/analyze  referral_gate_evaluation                   ok    
74.959       /api/alert/analyze  reasoning_generation                       ok    
101.75       /api/alert/analyze  decision_node_and_edge_write               ok    
105.169      /api/alert/analyze  audit_write                                ok    
0.608        /api/alert/analyze  metadata_logging_snapshot_write            ok    
105.368      /api/alert/analyze  campaign_query_fetch_recent_events         ok    
96.224       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
106.469      /api/alert/analyze  campaign_query_update_campaign             ok    
113.742      /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
91.07        /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
101.582      /api/alert/analyze  campaign_query_member_edges_batch_create   error 
636.602      /api/alert/analyze  campaign_correlation_summary               ok    
771.225      /api/alert/analyze  campaign_correlation                       ok    
0.103        /api/alert/analyze  decision_event_emit                        ok    
98.493       /api/alert/analyze  composite_gate_evaluation                  ok    
0.434        /api/alert/analyze  provenance_build                           ok    
103.958      /api/alert/analyze  graph_visualization_fetch                  ok    
0.032        /api/alert/analyze  response_context_enrichment                ok    
0.05         /api/alert/analyze  referral_debug_build                       ok    
0.03         /api/alert/analyze  shadow_compare_schedule                    ok    
99.526       /api/alert/analyze  cluster_history_fetch                      ok    
0.062        /api/alert/analyze  narrative_context_build                    ok    
0.331        /api/alert/analyze  narrative_generation                       ok    
4.349        /api/alert/analyze  response_serialization                     ok    
2224.361     /api/alert/analyze  analyze_request_total                      ok    
0.021        /api/alert/outcome  request_parse                              ok    
0.021        /api/alert/outcome  duplicate_feedback_guard                   ok    
95.121       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.313        /api/alert/outcome  outcome_audit_write                        ok    
162.597      /api/alert/outcome  learning_state_update                      ok    
494.833      /api/alert/outcome  l5_conservation_write                      ok    
497.316      /api/alert/outcome  conservation_monitor                       ok    
0.279        /api/alert/outcome  profile_scorer_update                      ok    
0.318        /api/alert/outcome  l5_dk_weight_write                         ok    
572.67       /api/alert/outcome  l5_centroid_write                          ok    
0.04         /api/alert/outcome  l5_dk_weight_write                         ok    
0.043        /api/alert/outcome  snapshot_evolution_logging                 ok    
119.387      /api/alert/outcome  snapshot_evolution_logging                 ok    
0.04         /api/alert/outcome  response_serialization                     ok    
1985.388     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1FIX-0012
- event_count: 52
- total_observed_ms: 9545.84
- authoritative_total_ms: 2202.094
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.062        /api/alert/analyze  scorer_readiness                           ok    
0.03         /api/alert/analyze  request_parse                              ok    
99.117       /api/alert/analyze  alert_lookup                               ok    
96.868       /api/alert/analyze  security_context_lookup                    ok    
0.268        /api/alert/analyze  category_resolution                        ok    
384.033      /api/alert/analyze  factor_vector_construction                 ok    
0.377        /api/alert/analyze  scorer_decision                            ok    
0.039        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.022        /api/alert/analyze  routing_threshold_lookup                   ok    
0.032        /api/alert/analyze  rl_exploration_proposal                    ok    
0.049        /api/alert/analyze  routing_zone_resolution                    ok    
191.792      /api/alert/analyze  referral_history_counts                    ok    
0.225        /api/alert/analyze  referral_gate_evaluation                   ok    
104.485      /api/alert/analyze  reasoning_generation                       ok    
106.155      /api/alert/analyze  decision_node_and_edge_write               ok    
134.308      /api/alert/analyze  audit_write                                ok    
0.329        /api/alert/analyze  metadata_logging_snapshot_write            ok    
88.885       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
83.627       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
132.642      /api/alert/analyze  campaign_query_create_campaign             ok    
96.029       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
88.883       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
105.331      /api/alert/analyze  campaign_query_member_edges_batch_create   error 
616.334      /api/alert/analyze  campaign_correlation_summary               ok    
700.188      /api/alert/analyze  campaign_correlation                       ok    
0.058        /api/alert/analyze  decision_event_emit                        ok    
85.211       /api/alert/analyze  composite_gate_evaluation                  ok    
0.109        /api/alert/analyze  provenance_build                           ok    
97.691       /api/alert/analyze  graph_visualization_fetch                  ok    
0.044        /api/alert/analyze  response_context_enrichment                ok    
0.049        /api/alert/analyze  referral_debug_build                       ok    
0.037        /api/alert/analyze  shadow_compare_schedule                    ok    
112.511      /api/alert/analyze  cluster_history_fetch                      ok    
0.068        /api/alert/analyze  narrative_context_build                    ok    
0.098        /api/alert/analyze  narrative_generation                       ok    
5.298        /api/alert/analyze  response_serialization                     ok    
2202.094     /api/alert/analyze  analyze_request_total                      ok    
0.019        /api/alert/outcome  request_parse                              ok    
0.025        /api/alert/outcome  duplicate_feedback_guard                   ok    
108.177      /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.431        /api/alert/outcome  outcome_audit_write                        ok    
145.116      /api/alert/outcome  learning_state_update                      ok    
550.897      /api/alert/outcome  l5_conservation_write                      ok    
555.185      /api/alert/outcome  conservation_monitor                       ok    
0.28         /api/alert/outcome  profile_scorer_update                      ok    
0.204        /api/alert/outcome  l5_dk_weight_write                         ok    
561.38       /api/alert/outcome  l5_centroid_write                          ok    
0.039        /api/alert/outcome  l5_dk_weight_write                         ok    
0.093        /api/alert/outcome  snapshot_evolution_logging                 ok    
91.564       /api/alert/outcome  snapshot_evolution_logging                 ok    
0.059        /api/alert/outcome  response_serialization                     ok    
1998.993     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1FIX-0005
- event_count: 47
- total_observed_ms: 7392.414
- authoritative_total_ms: 2201.974
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.021        /api/alert/analyze  scorer_readiness                    ok    
0.008        /api/alert/analyze  request_parse                       ok    
72.599       /api/alert/analyze  alert_lookup                        ok    
84.776       /api/alert/analyze  security_context_lookup             ok    
0.109        /api/alert/analyze  category_resolution                 ok    
338.84       /api/alert/analyze  factor_vector_construction          ok    
0.334        /api/alert/analyze  scorer_decision                     ok    
0.032        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.021        /api/alert/analyze  routing_threshold_lookup            ok    
0.027        /api/alert/analyze  rl_exploration_proposal             ok    
0.039        /api/alert/analyze  routing_zone_resolution             ok    
187.904      /api/alert/analyze  referral_history_counts             ok    
0.055        /api/alert/analyze  referral_gate_evaluation            ok    
109.196      /api/alert/analyze  reasoning_generation                ok    
93.207       /api/alert/analyze  decision_node_and_edge_write        ok    
89.268       /api/alert/analyze  audit_write                         ok    
0.447        /api/alert/analyze  metadata_logging_snapshot_write     ok    
110.627      /api/alert/analyze  campaign_query_fetch_recent_events  ok    
113.455      /api/alert/analyze  campaign_correlation_summary        ok    
115.868      /api/alert/analyze  campaign_correlation                ok    
0.039        /api/alert/analyze  decision_event_emit                 ok    
100.278      /api/alert/analyze  composite_gate_evaluation           ok    
0.116        /api/alert/analyze  provenance_build                    ok    
102.025      /api/alert/analyze  graph_visualization_fetch           ok    
0.428        /api/alert/analyze  response_context_enrichment         ok    
0.105        /api/alert/analyze  referral_debug_build                ok    
0.037        /api/alert/analyze  shadow_compare_schedule             ok    
101.909      /api/alert/analyze  cluster_history_fetch               ok    
0.058        /api/alert/analyze  narrative_context_build             ok    
0.186        /api/alert/analyze  narrative_generation                ok    
6.498        /api/alert/analyze  response_serialization              ok    
1460.187     /api/alert/analyze  analyze_request_total               ok    
0.023        /api/alert/outcome  request_parse                       ok    
0.021        /api/alert/outcome  duplicate_feedback_guard            ok    
126.966      /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.464        /api/alert/outcome  outcome_audit_write                 ok    
473.212      /api/alert/outcome  learning_state_update               ok    
421.353      /api/alert/outcome  l5_conservation_write               ok    
422.803      /api/alert/outcome  conservation_monitor                ok    
0.161        /api/alert/outcome  profile_scorer_update               ok    
0.124        /api/alert/outcome  l5_dk_weight_write                  ok    
509.153      /api/alert/outcome  l5_centroid_write                   ok    
0.027        /api/alert/outcome  l5_dk_weight_write                  ok    
0.021        /api/alert/outcome  snapshot_evolution_logging          ok    
147.339      /api/alert/outcome  snapshot_evolution_logging          ok    
0.074        /api/alert/outcome  response_serialization              ok    
2201.974     /api/alert/outcome  outcome_request_total               ok    
```

### CAMPAIGNP1FIX-0009
- event_count: 52
- total_observed_ms: 9510.795
- authoritative_total_ms: 2187.739
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.034        /api/alert/analyze  scorer_readiness                           ok    
0.024        /api/alert/analyze  request_parse                              ok    
86.077       /api/alert/analyze  alert_lookup                               ok    
98.867       /api/alert/analyze  security_context_lookup                    ok    
0.264        /api/alert/analyze  category_resolution                        ok    
378.515      /api/alert/analyze  factor_vector_construction                 ok    
0.484        /api/alert/analyze  scorer_decision                            ok    
0.129        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.022        /api/alert/analyze  routing_threshold_lookup                   ok    
0.033        /api/alert/analyze  rl_exploration_proposal                    ok    
0.037        /api/alert/analyze  routing_zone_resolution                    ok    
208.103      /api/alert/analyze  referral_history_counts                    ok    
0.099        /api/alert/analyze  referral_gate_evaluation                   ok    
104.524      /api/alert/analyze  reasoning_generation                       ok    
117.582      /api/alert/analyze  decision_node_and_edge_write               ok    
101.053      /api/alert/analyze  audit_write                                ok    
0.187        /api/alert/analyze  metadata_logging_snapshot_write            ok    
103.803      /api/alert/analyze  campaign_query_fetch_recent_events         ok    
86.444       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
100.649      /api/alert/analyze  campaign_query_create_campaign             ok    
106.602      /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
97.62        /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
95.121       /api/alert/analyze  campaign_query_member_edges_batch_create   error 
611.709      /api/alert/analyze  campaign_correlation_summary               ok    
730.142      /api/alert/analyze  campaign_correlation                       ok    
0.048        /api/alert/analyze  decision_event_emit                        ok    
96.464       /api/alert/analyze  composite_gate_evaluation                  ok    
0.113        /api/alert/analyze  provenance_build                           ok    
92.178       /api/alert/analyze  graph_visualization_fetch                  ok    
0.036        /api/alert/analyze  response_context_enrichment                ok    
0.067        /api/alert/analyze  referral_debug_build                       ok    
0.118        /api/alert/analyze  shadow_compare_schedule                    ok    
87.877       /api/alert/analyze  cluster_history_fetch                      ok    
0.064        /api/alert/analyze  narrative_context_build                    ok    
0.102        /api/alert/analyze  narrative_generation                       ok    
5.181        /api/alert/analyze  response_serialization                     ok    
2187.739     /api/alert/analyze  analyze_request_total                      ok    
0.022        /api/alert/outcome  request_parse                              ok    
0.044        /api/alert/outcome  duplicate_feedback_guard                   ok    
104.068      /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.509        /api/alert/outcome  outcome_audit_write                        ok    
181.953      /api/alert/outcome  learning_state_update                      ok    
507.754      /api/alert/outcome  l5_conservation_write                      ok    
511.354      /api/alert/outcome  conservation_monitor                       ok    
0.482        /api/alert/outcome  profile_scorer_update                      ok    
0.269        /api/alert/outcome  l5_dk_weight_write                         ok    
585.094      /api/alert/outcome  l5_centroid_write                          ok    
0.048        /api/alert/outcome  l5_dk_weight_write                         ok    
0.036        /api/alert/outcome  snapshot_evolution_logging                 ok    
96.147       /api/alert/outcome  snapshot_evolution_logging                 ok    
0.032        /api/alert/outcome  response_serialization                     ok    
2024.872     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1FIX-0017
- event_count: 52
- total_observed_ms: 9496.419
- authoritative_total_ms: 2186.355
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.037        /api/alert/analyze  scorer_readiness                           ok    
0.023        /api/alert/analyze  request_parse                              ok    
91.723       /api/alert/analyze  alert_lookup                               ok    
96.94        /api/alert/analyze  security_context_lookup                    ok    
0.276        /api/alert/analyze  category_resolution                        ok    
407.428      /api/alert/analyze  factor_vector_construction                 ok    
0.427        /api/alert/analyze  scorer_decision                            ok    
0.028        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.022        /api/alert/analyze  routing_threshold_lookup                   ok    
0.035        /api/alert/analyze  rl_exploration_proposal                    ok    
0.043        /api/alert/analyze  routing_zone_resolution                    ok    
199.471      /api/alert/analyze  referral_history_counts                    ok    
0.083        /api/alert/analyze  referral_gate_evaluation                   ok    
98.927       /api/alert/analyze  reasoning_generation                       ok    
101.105      /api/alert/analyze  decision_node_and_edge_write               ok    
104.066      /api/alert/analyze  audit_write                                ok    
0.299        /api/alert/analyze  metadata_logging_snapshot_write            ok    
101.949      /api/alert/analyze  campaign_query_fetch_recent_events         ok    
93.221       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
89.875       /api/alert/analyze  campaign_query_update_campaign             ok    
107.482      /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
109.569      /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
81.337       /api/alert/analyze  campaign_query_member_edges_batch_create   error 
601.33       /api/alert/analyze  campaign_correlation_summary               ok    
706.196      /api/alert/analyze  campaign_correlation                       ok    
0.051        /api/alert/analyze  decision_event_emit                        ok    
100.843      /api/alert/analyze  composite_gate_evaluation                  ok    
0.15         /api/alert/analyze  provenance_build                           ok    
106.245      /api/alert/analyze  graph_visualization_fetch                  ok    
0.053        /api/alert/analyze  response_context_enrichment                ok    
0.06         /api/alert/analyze  referral_debug_build                       ok    
0.035        /api/alert/analyze  shadow_compare_schedule                    ok    
91.679       /api/alert/analyze  cluster_history_fetch                      ok    
0.091        /api/alert/analyze  narrative_context_build                    ok    
0.495        /api/alert/analyze  narrative_generation                       ok    
5.802        /api/alert/analyze  response_serialization                     ok    
2186.355     /api/alert/analyze  analyze_request_total                      ok    
0.024        /api/alert/outcome  request_parse                              ok    
0.022        /api/alert/outcome  duplicate_feedback_guard                   ok    
123.752      /api/alert/outcome  decision_lookup_and_outcome_update         ok    
2.14         /api/alert/outcome  outcome_audit_write                        ok    
170.557      /api/alert/outcome  learning_state_update                      ok    
578.988      /api/alert/outcome  l5_conservation_write                      ok    
582.103      /api/alert/outcome  conservation_monitor                       ok    
0.333        /api/alert/outcome  profile_scorer_update                      ok    
0.243        /api/alert/outcome  l5_dk_weight_write                         ok    
505.045      /api/alert/outcome  l5_centroid_write                          ok    
0.018        /api/alert/outcome  l5_dk_weight_write                         ok    
0.037        /api/alert/outcome  snapshot_evolution_logging                 ok    
99.798       /api/alert/outcome  snapshot_evolution_logging                 ok    
0.037        /api/alert/outcome  response_serialization                     ok    
1949.571     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1FIX-0001
- event_count: 47
- total_observed_ms: 8329.868
- authoritative_total_ms: 2186.116
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.039        /api/alert/analyze  scorer_readiness                    ok    
0.021        /api/alert/analyze  request_parse                       ok    
95.856       /api/alert/analyze  alert_lookup                        ok    
94.579       /api/alert/analyze  security_context_lookup             ok    
2.923        /api/alert/analyze  category_resolution                 ok    
400.566      /api/alert/analyze  factor_vector_construction          ok    
0.723        /api/alert/analyze  scorer_decision                     ok    
5.453        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.029        /api/alert/analyze  routing_threshold_lookup            ok    
0.038        /api/alert/analyze  rl_exploration_proposal             ok    
0.101        /api/alert/analyze  routing_zone_resolution             ok    
190.446      /api/alert/analyze  referral_history_counts             ok    
0.126        /api/alert/analyze  referral_gate_evaluation            ok    
412.589      /api/alert/analyze  reasoning_generation                ok    
125.788      /api/alert/analyze  decision_node_and_edge_write        ok    
100.187      /api/alert/analyze  audit_write                         ok    
0.506        /api/alert/analyze  metadata_logging_snapshot_write     ok    
93.724       /api/alert/analyze  campaign_query_fetch_recent_events  ok    
97.155       /api/alert/analyze  campaign_correlation_summary        ok    
101.161      /api/alert/analyze  campaign_correlation                ok    
0.089        /api/alert/analyze  decision_event_emit                 ok    
96.004       /api/alert/analyze  composite_gate_evaluation           ok    
0.114        /api/alert/analyze  provenance_build                    ok    
107.997      /api/alert/analyze  graph_visualization_fetch           ok    
0.063        /api/alert/analyze  response_context_enrichment         ok    
0.079        /api/alert/analyze  referral_debug_build                ok    
0.04         /api/alert/analyze  shadow_compare_schedule             ok    
123.501      /api/alert/analyze  cluster_history_fetch               ok    
0.088        /api/alert/analyze  narrative_context_build             ok    
0.095        /api/alert/analyze  narrative_generation                ok    
4.502        /api/alert/analyze  response_serialization              ok    
1980.225     /api/alert/analyze  analyze_request_total               ok    
0.021        /api/alert/outcome  request_parse                       ok    
0.018        /api/alert/outcome  duplicate_feedback_guard            ok    
107.484      /api/alert/outcome  decision_lookup_and_outcome_update  ok    
1.752        /api/alert/outcome  outcome_audit_write                 ok    
192.636      /api/alert/outcome  learning_state_update               ok    
528.989      /api/alert/outcome  l5_conservation_write               ok    
535.036      /api/alert/outcome  conservation_monitor                ok    
0.396        /api/alert/outcome  profile_scorer_update               ok    
0.801        /api/alert/outcome  l5_dk_weight_write                  ok    
606.74       /api/alert/outcome  l5_centroid_write                   ok    
0.047        /api/alert/outcome  l5_dk_weight_write                  ok    
1.986        /api/alert/outcome  snapshot_evolution_logging          ok    
133.003      /api/alert/outcome  snapshot_evolution_logging          ok    
0.036        /api/alert/outcome  response_serialization              ok    
2186.116     /api/alert/outcome  outcome_request_total               ok    
```

### CAMPAIGNP1FIX-0011
- event_count: 52
- total_observed_ms: 9345.065
- authoritative_total_ms: 2179.198
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.042        /api/alert/analyze  scorer_readiness                           ok    
0.018        /api/alert/analyze  request_parse                              ok    
98.468       /api/alert/analyze  alert_lookup                               ok    
102.369      /api/alert/analyze  security_context_lookup                    ok    
0.365        /api/alert/analyze  category_resolution                        ok    
378.392      /api/alert/analyze  factor_vector_construction                 ok    
0.537        /api/alert/analyze  scorer_decision                            ok    
0.037        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.023        /api/alert/analyze  routing_threshold_lookup                   ok    
0.018        /api/alert/analyze  rl_exploration_proposal                    ok    
0.039        /api/alert/analyze  routing_zone_resolution                    ok    
192.835      /api/alert/analyze  referral_history_counts                    ok    
0.085        /api/alert/analyze  referral_gate_evaluation                   ok    
98.312       /api/alert/analyze  reasoning_generation                       ok    
107.179      /api/alert/analyze  decision_node_and_edge_write               ok    
109.236      /api/alert/analyze  audit_write                                ok    
0.471        /api/alert/analyze  metadata_logging_snapshot_write            ok    
93.562       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
89.936       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
90.396       /api/alert/analyze  campaign_query_create_campaign             ok    
96.848       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
106.429      /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
107.936      /api/alert/analyze  campaign_query_member_edges_batch_create   error 
601.922      /api/alert/analyze  campaign_correlation_summary               ok    
715.98       /api/alert/analyze  campaign_correlation                       ok    
0.046        /api/alert/analyze  decision_event_emit                        ok    
103.341      /api/alert/analyze  composite_gate_evaluation                  ok    
0.11         /api/alert/analyze  provenance_build                           ok    
106.513      /api/alert/analyze  graph_visualization_fetch                  ok    
0.061        /api/alert/analyze  response_context_enrichment                ok    
0.06         /api/alert/analyze  referral_debug_build                       ok    
0.041        /api/alert/analyze  shadow_compare_schedule                    ok    
88.92        /api/alert/analyze  cluster_history_fetch                      ok    
0.084        /api/alert/analyze  narrative_context_build                    ok    
0.283        /api/alert/analyze  narrative_generation                       ok    
4.798        /api/alert/analyze  response_serialization                     ok    
2179.198     /api/alert/analyze  analyze_request_total                      ok    
0.013        /api/alert/outcome  request_parse                              ok    
0.023        /api/alert/outcome  duplicate_feedback_guard                   ok    
110.21       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.507        /api/alert/outcome  outcome_audit_write                        ok    
156.707      /api/alert/outcome  learning_state_update                      ok    
481.548      /api/alert/outcome  l5_conservation_write                      ok    
484.275      /api/alert/outcome  conservation_monitor                       ok    
0.276        /api/alert/outcome  profile_scorer_update                      ok    
0.602        /api/alert/outcome  l5_dk_weight_write                         ok    
567.117      /api/alert/outcome  l5_centroid_write                          ok    
0.04         /api/alert/outcome  l5_dk_weight_write                         ok    
0.073        /api/alert/outcome  snapshot_evolution_logging                 ok    
109.306      /api/alert/outcome  snapshot_evolution_logging                 ok    
0.045        /api/alert/outcome  response_serialization                     ok    
1959.433     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1FIX-0016
- event_count: 52
- total_observed_ms: 9444.575
- authoritative_total_ms: 2163.488
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.034        /api/alert/analyze  scorer_readiness                           ok    
0.029        /api/alert/analyze  request_parse                              ok    
91.849       /api/alert/analyze  alert_lookup                               ok    
95.828       /api/alert/analyze  security_context_lookup                    ok    
0.223        /api/alert/analyze  category_resolution                        ok    
380.825      /api/alert/analyze  factor_vector_construction                 ok    
0.633        /api/alert/analyze  scorer_decision                            ok    
0.038        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.022        /api/alert/analyze  routing_threshold_lookup                   ok    
0.034        /api/alert/analyze  rl_exploration_proposal                    ok    
0.038        /api/alert/analyze  routing_zone_resolution                    ok    
211.927      /api/alert/analyze  referral_history_counts                    ok    
0.098        /api/alert/analyze  referral_gate_evaluation                   ok    
78.029       /api/alert/analyze  reasoning_generation                       ok    
102.824      /api/alert/analyze  decision_node_and_edge_write               ok    
110.453      /api/alert/analyze  audit_write                                ok    
0.555        /api/alert/analyze  metadata_logging_snapshot_write            ok    
99.074       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
100.257      /api/alert/analyze  campaign_query_check_campaign_exists       ok    
113.345      /api/alert/analyze  campaign_query_update_campaign             ok    
103.01       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
104.273      /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
84.417       /api/alert/analyze  campaign_query_member_edges_batch_create   error 
622.353      /api/alert/analyze  campaign_correlation_summary               ok    
732.963      /api/alert/analyze  campaign_correlation                       ok    
0.062        /api/alert/analyze  decision_event_emit                        ok    
95.557       /api/alert/analyze  composite_gate_evaluation                  ok    
0.108        /api/alert/analyze  provenance_build                           ok    
93.525       /api/alert/analyze  graph_visualization_fetch                  ok    
0.083        /api/alert/analyze  response_context_enrichment                ok    
0.069        /api/alert/analyze  referral_debug_build                       ok    
0.044        /api/alert/analyze  shadow_compare_schedule                    ok    
90.024       /api/alert/analyze  cluster_history_fetch                      ok    
0.084        /api/alert/analyze  narrative_context_build                    ok    
0.084        /api/alert/analyze  narrative_generation                       ok    
4.955        /api/alert/analyze  response_serialization                     ok    
2163.488     /api/alert/analyze  analyze_request_total                      ok    
0.026        /api/alert/outcome  request_parse                              ok    
0.03         /api/alert/outcome  duplicate_feedback_guard                   ok    
113.945      /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.775        /api/alert/outcome  outcome_audit_write                        ok    
174.404      /api/alert/outcome  learning_state_update                      ok    
507.108      /api/alert/outcome  l5_conservation_write                      ok    
509.791      /api/alert/outcome  conservation_monitor                       ok    
0.356        /api/alert/outcome  profile_scorer_update                      ok    
0.33         /api/alert/outcome  l5_dk_weight_write                         ok    
535.825      /api/alert/outcome  l5_centroid_write                          ok    
0.043        /api/alert/outcome  l5_dk_weight_write                         ok    
0.095        /api/alert/outcome  snapshot_evolution_logging                 ok    
123.913      /api/alert/outcome  snapshot_evolution_logging                 ok    
0.081        /api/alert/outcome  response_serialization                     ok    
1996.639     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1FIX-0015
- event_count: 52
- total_observed_ms: 9374.006
- authoritative_total_ms: 2156.863
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.053        /api/alert/analyze  scorer_readiness                           ok    
0.025        /api/alert/analyze  request_parse                              ok    
95.912       /api/alert/analyze  alert_lookup                               ok    
94.145       /api/alert/analyze  security_context_lookup                    ok    
0.235        /api/alert/analyze  category_resolution                        ok    
406.828      /api/alert/analyze  factor_vector_construction                 ok    
0.738        /api/alert/analyze  scorer_decision                            ok    
0.047        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.171        /api/alert/analyze  routing_threshold_lookup                   ok    
0.032        /api/alert/analyze  rl_exploration_proposal                    ok    
0.048        /api/alert/analyze  routing_zone_resolution                    ok    
196.083      /api/alert/analyze  referral_history_counts                    ok    
0.086        /api/alert/analyze  referral_gate_evaluation                   ok    
102.412      /api/alert/analyze  reasoning_generation                       ok    
106.251      /api/alert/analyze  decision_node_and_edge_write               ok    
105.357      /api/alert/analyze  audit_write                                ok    
0.395        /api/alert/analyze  metadata_logging_snapshot_write            ok    
91.402       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
88.87        /api/alert/analyze  campaign_query_check_campaign_exists       ok    
107.991      /api/alert/analyze  campaign_query_update_campaign             ok    
111.007      /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
87.089       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
81.833       /api/alert/analyze  campaign_query_member_edges_batch_create   error 
589.108      /api/alert/analyze  campaign_correlation_summary               ok    
695.561      /api/alert/analyze  campaign_correlation                       ok    
0.046        /api/alert/analyze  decision_event_emit                        ok    
84.474       /api/alert/analyze  composite_gate_evaluation                  ok    
0.141        /api/alert/analyze  provenance_build                           ok    
90.188       /api/alert/analyze  graph_visualization_fetch                  ok    
0.057        /api/alert/analyze  response_context_enrichment                ok    
0.066        /api/alert/analyze  referral_debug_build                       ok    
0.031        /api/alert/analyze  shadow_compare_schedule                    ok    
90.135       /api/alert/analyze  cluster_history_fetch                      ok    
0.09         /api/alert/analyze  narrative_context_build                    ok    
0.087        /api/alert/analyze  narrative_generation                       ok    
5.354        /api/alert/analyze  response_serialization                     ok    
2156.863     /api/alert/analyze  analyze_request_total                      ok    
0.018        /api/alert/outcome  request_parse                              ok    
0.02         /api/alert/outcome  duplicate_feedback_guard                   ok    
101.624      /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.46         /api/alert/outcome  outcome_audit_write                        ok    
157.633      /api/alert/outcome  learning_state_update                      ok    
537.316      /api/alert/outcome  l5_conservation_write                      ok    
540.343      /api/alert/outcome  conservation_monitor                       ok    
0.336        /api/alert/outcome  profile_scorer_update                      ok    
0.704        /api/alert/outcome  l5_dk_weight_write                         ok    
556.255      /api/alert/outcome  l5_centroid_write                          ok    
0.035        /api/alert/outcome  l5_dk_weight_write                         ok    
0.12         /api/alert/outcome  snapshot_evolution_logging                 ok    
107.305      /api/alert/outcome  snapshot_evolution_logging                 ok    
0.074        /api/alert/outcome  response_serialization                     ok    
1982.552     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1FIX-0013
- event_count: 52
- total_observed_ms: 9284.539
- authoritative_total_ms: 2148.449
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.036        /api/alert/analyze  scorer_readiness                           ok    
0.027        /api/alert/analyze  request_parse                              ok    
91.837       /api/alert/analyze  alert_lookup                               ok    
115.33       /api/alert/analyze  security_context_lookup                    ok    
0.54         /api/alert/analyze  category_resolution                        ok    
385.038      /api/alert/analyze  factor_vector_construction                 ok    
0.227        /api/alert/analyze  scorer_decision                            ok    
0.05         /api/alert/analyze  post_scorer_confidence_gate                ok    
0.01         /api/alert/analyze  routing_threshold_lookup                   ok    
0.035        /api/alert/analyze  rl_exploration_proposal                    ok    
0.026        /api/alert/analyze  routing_zone_resolution                    ok    
186.173      /api/alert/analyze  referral_history_counts                    ok    
0.081        /api/alert/analyze  referral_gate_evaluation                   ok    
74.009       /api/alert/analyze  reasoning_generation                       ok    
100.285      /api/alert/analyze  decision_node_and_edge_write               ok    
86.446       /api/alert/analyze  audit_write                                ok    
0.447        /api/alert/analyze  metadata_logging_snapshot_write            ok    
91.991       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
85.627       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
109.031      /api/alert/analyze  campaign_query_update_campaign             ok    
115.854      /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
94.775       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
124.61       /api/alert/analyze  campaign_query_member_edges_batch_create   error 
641.279      /api/alert/analyze  campaign_correlation_summary               ok    
740.081      /api/alert/analyze  campaign_correlation                       ok    
0.042        /api/alert/analyze  decision_event_emit                        ok    
108.186      /api/alert/analyze  composite_gate_evaluation                  ok    
0.163        /api/alert/analyze  provenance_build                           ok    
93.725       /api/alert/analyze  graph_visualization_fetch                  ok    
0.064        /api/alert/analyze  response_context_enrichment                ok    
0.073        /api/alert/analyze  referral_debug_build                       ok    
0.035        /api/alert/analyze  shadow_compare_schedule                    ok    
91.865       /api/alert/analyze  cluster_history_fetch                      ok    
0.091        /api/alert/analyze  narrative_context_build                    ok    
0.085        /api/alert/analyze  narrative_generation                       ok    
5.428        /api/alert/analyze  response_serialization                     ok    
2148.449     /api/alert/analyze  analyze_request_total                      ok    
0.023        /api/alert/outcome  request_parse                              ok    
0.026        /api/alert/outcome  duplicate_feedback_guard                   ok    
111.54       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.586        /api/alert/outcome  outcome_audit_write                        ok    
170.718      /api/alert/outcome  learning_state_update                      ok    
470.793      /api/alert/outcome  l5_conservation_write                      ok    
474.838      /api/alert/outcome  conservation_monitor                       ok    
0.248        /api/alert/outcome  profile_scorer_update                      ok    
0.361        /api/alert/outcome  l5_dk_weight_write                         ok    
505.185      /api/alert/outcome  l5_centroid_write                          ok    
0.041        /api/alert/outcome  l5_dk_weight_write                         ok    
0.04         /api/alert/outcome  snapshot_evolution_logging                 ok    
129.345      /api/alert/outcome  snapshot_evolution_logging                 ok    
0.042        /api/alert/outcome  response_serialization                     ok    
1928.702     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1FIX-0007
- event_count: 52
- total_observed_ms: 9138.226
- authoritative_total_ms: 2147.554
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.037        /api/alert/analyze  scorer_readiness                           ok    
0.02         /api/alert/analyze  request_parse                              ok    
106.976      /api/alert/analyze  alert_lookup                               ok    
97.556       /api/alert/analyze  security_context_lookup                    ok    
0.295        /api/alert/analyze  category_resolution                        ok    
430.947      /api/alert/analyze  factor_vector_construction                 ok    
0.481        /api/alert/analyze  scorer_decision                            ok    
0.027        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.024        /api/alert/analyze  routing_threshold_lookup                   ok    
0.035        /api/alert/analyze  rl_exploration_proposal                    ok    
0.037        /api/alert/analyze  routing_zone_resolution                    ok    
181.638      /api/alert/analyze  referral_history_counts                    ok    
0.162        /api/alert/analyze  referral_gate_evaluation                   ok    
104.593      /api/alert/analyze  reasoning_generation                       ok    
109.245      /api/alert/analyze  decision_node_and_edge_write               ok    
105.784      /api/alert/analyze  audit_write                                ok    
2.774        /api/alert/analyze  metadata_logging_snapshot_write            ok    
77.885       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
89.551       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
96.832       /api/alert/analyze  campaign_query_create_campaign             ok    
89.923       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
92.952       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
76.044       /api/alert/analyze  campaign_query_member_edges_batch_create   error 
534.84       /api/alert/analyze  campaign_correlation_summary               ok    
632.067      /api/alert/analyze  campaign_correlation                       ok    
0.274        /api/alert/analyze  decision_event_emit                        ok    
89.468       /api/alert/analyze  composite_gate_evaluation                  ok    
0.128        /api/alert/analyze  provenance_build                           ok    
111.731      /api/alert/analyze  graph_visualization_fetch                  ok    
0.063        /api/alert/analyze  response_context_enrichment                ok    
0.042        /api/alert/analyze  referral_debug_build                       ok    
0.028        /api/alert/analyze  shadow_compare_schedule                    ok    
91.392       /api/alert/analyze  cluster_history_fetch                      ok    
0.07         /api/alert/analyze  narrative_context_build                    ok    
0.296        /api/alert/analyze  narrative_generation                       ok    
9.257        /api/alert/analyze  response_serialization                     ok    
2147.554     /api/alert/analyze  analyze_request_total                      ok    
0.02         /api/alert/outcome  request_parse                              ok    
0.021        /api/alert/outcome  duplicate_feedback_guard                   ok    
113.623      /api/alert/outcome  decision_lookup_and_outcome_update         ok    
1.884        /api/alert/outcome  outcome_audit_write                        ok    
154.173      /api/alert/outcome  learning_state_update                      ok    
495.296      /api/alert/outcome  l5_conservation_write                      ok    
497.7        /api/alert/outcome  conservation_monitor                       ok    
0.318        /api/alert/outcome  profile_scorer_update                      ok    
0.236        /api/alert/outcome  l5_dk_weight_write                         ok    
560.319      /api/alert/outcome  l5_centroid_write                          ok    
0.043        /api/alert/outcome  l5_dk_weight_write                         ok    
0.083        /api/alert/outcome  snapshot_evolution_logging                 ok    
85.983       /api/alert/outcome  snapshot_evolution_logging                 ok    
0.028        /api/alert/outcome  response_serialization                     ok    
1947.471     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1FIX-0014
- event_count: 52
- total_observed_ms: 9201.575
- authoritative_total_ms: 2126.538
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.043        /api/alert/analyze  scorer_readiness                           ok    
0.015        /api/alert/analyze  request_parse                              ok    
88.306       /api/alert/analyze  alert_lookup                               ok    
97.971       /api/alert/analyze  security_context_lookup                    ok    
0.459        /api/alert/analyze  category_resolution                        ok    
398.572      /api/alert/analyze  factor_vector_construction                 ok    
0.261        /api/alert/analyze  scorer_decision                            ok    
0.033        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.014        /api/alert/analyze  routing_threshold_lookup                   ok    
0.035        /api/alert/analyze  rl_exploration_proposal                    ok    
0.038        /api/alert/analyze  routing_zone_resolution                    ok    
215.525      /api/alert/analyze  referral_history_counts                    ok    
0.093        /api/alert/analyze  referral_gate_evaluation                   ok    
79.753       /api/alert/analyze  reasoning_generation                       ok    
97.576       /api/alert/analyze  decision_node_and_edge_write               ok    
96.223       /api/alert/analyze  audit_write                                ok    
0.385        /api/alert/analyze  metadata_logging_snapshot_write            ok    
95.577       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
89.563       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
92.482       /api/alert/analyze  campaign_query_update_campaign             ok    
99.162       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
109.867      /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
96.134       /api/alert/analyze  campaign_query_member_edges_batch_create   error 
602.41       /api/alert/analyze  campaign_correlation_summary               ok    
713.318      /api/alert/analyze  campaign_correlation                       ok    
0.067        /api/alert/analyze  decision_event_emit                        ok    
88.91        /api/alert/analyze  composite_gate_evaluation                  ok    
0.152        /api/alert/analyze  provenance_build                           ok    
103.14       /api/alert/analyze  graph_visualization_fetch                  ok    
0.075        /api/alert/analyze  response_context_enrichment                ok    
0.065        /api/alert/analyze  referral_debug_build                       ok    
0.039        /api/alert/analyze  shadow_compare_schedule                    ok    
78.273       /api/alert/analyze  cluster_history_fetch                      ok    
0.086        /api/alert/analyze  narrative_context_build                    ok    
0.053        /api/alert/analyze  narrative_generation                       ok    
3.089        /api/alert/analyze  response_serialization                     ok    
2126.538     /api/alert/analyze  analyze_request_total                      ok    
0.02         /api/alert/outcome  request_parse                              ok    
0.015        /api/alert/outcome  duplicate_feedback_guard                   ok    
100.632      /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.638        /api/alert/outcome  outcome_audit_write                        ok    
159.141      /api/alert/outcome  learning_state_update                      ok    
530.162      /api/alert/outcome  l5_conservation_write                      ok    
533.717      /api/alert/outcome  conservation_monitor                       ok    
0.408        /api/alert/outcome  profile_scorer_update                      ok    
0.238        /api/alert/outcome  l5_dk_weight_write                         ok    
520.962      /api/alert/outcome  l5_centroid_write                          ok    
0.039        /api/alert/outcome  l5_dk_weight_write                         ok    
0.03         /api/alert/outcome  snapshot_evolution_logging                 ok    
79.77        /api/alert/outcome  snapshot_evolution_logging                 ok    
0.038        /api/alert/outcome  response_serialization                     ok    
1901.463     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1FIX-0010
- event_count: 52
- total_observed_ms: 8998.262
- authoritative_total_ms: 2093.636
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.04         /api/alert/analyze  scorer_readiness                           ok    
0.019        /api/alert/analyze  request_parse                              ok    
92.201       /api/alert/analyze  alert_lookup                               ok    
96.236       /api/alert/analyze  security_context_lookup                    ok    
0.277        /api/alert/analyze  category_resolution                        ok    
388.154      /api/alert/analyze  factor_vector_construction                 ok    
0.457        /api/alert/analyze  scorer_decision                            ok    
0.039        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.021        /api/alert/analyze  routing_threshold_lookup                   ok    
0.033        /api/alert/analyze  rl_exploration_proposal                    ok    
0.041        /api/alert/analyze  routing_zone_resolution                    ok    
188.794      /api/alert/analyze  referral_history_counts                    ok    
0.082        /api/alert/analyze  referral_gate_evaluation                   ok    
106.685      /api/alert/analyze  reasoning_generation                       ok    
104.692      /api/alert/analyze  decision_node_and_edge_write               ok    
104.54       /api/alert/analyze  audit_write                                ok    
0.362        /api/alert/analyze  metadata_logging_snapshot_write            ok    
90.936       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
92.192       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
98.576       /api/alert/analyze  campaign_query_create_campaign             ok    
102.533      /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
76.674       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
82.03        /api/alert/analyze  campaign_query_member_edges_batch_create   error 
557.301      /api/alert/analyze  campaign_correlation_summary               ok    
648.498      /api/alert/analyze  campaign_correlation                       ok    
0.057        /api/alert/analyze  decision_event_emit                        ok    
91.119       /api/alert/analyze  composite_gate_evaluation                  ok    
0.142        /api/alert/analyze  provenance_build                           ok    
99.589       /api/alert/analyze  graph_visualization_fetch                  ok    
0.065        /api/alert/analyze  response_context_enrichment                ok    
0.073        /api/alert/analyze  referral_debug_build                       ok    
0.04         /api/alert/analyze  shadow_compare_schedule                    ok    
93.457       /api/alert/analyze  cluster_history_fetch                      ok    
0.07         /api/alert/analyze  narrative_context_build                    ok    
0.144        /api/alert/analyze  narrative_generation                       ok    
4.67         /api/alert/analyze  response_serialization                     ok    
2093.636     /api/alert/analyze  analyze_request_total                      ok    
0.02         /api/alert/outcome  request_parse                              ok    
0.026        /api/alert/outcome  duplicate_feedback_guard                   ok    
108.545      /api/alert/outcome  decision_lookup_and_outcome_update         ok    
1.033        /api/alert/outcome  outcome_audit_write                        ok    
172.166      /api/alert/outcome  learning_state_update                      ok    
499.122      /api/alert/outcome  l5_conservation_write                      ok    
502.093      /api/alert/outcome  conservation_monitor                       ok    
0.338        /api/alert/outcome  profile_scorer_update                      ok    
0.193        /api/alert/outcome  l5_dk_weight_write                         ok    
510.872      /api/alert/outcome  l5_centroid_write                          ok    
0.025        /api/alert/outcome  l5_dk_weight_write                         ok    
0.025        /api/alert/outcome  snapshot_evolution_logging                 ok    
112.741      /api/alert/outcome  snapshot_evolution_logging                 ok    
0.032        /api/alert/outcome  response_serialization                     ok    
1876.556     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1FIX-0022
- event_count: 52
- total_observed_ms: 8816.675
- authoritative_total_ms: 2089.351
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.025        /api/alert/analyze  scorer_readiness                           ok    
0.016        /api/alert/analyze  request_parse                              ok    
92.692       /api/alert/analyze  alert_lookup                               ok    
95.699       /api/alert/analyze  security_context_lookup                    ok    
0.213        /api/alert/analyze  category_resolution                        ok    
325.439      /api/alert/analyze  factor_vector_construction                 ok    
0.45         /api/alert/analyze  scorer_decision                            ok    
0.048        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.022        /api/alert/analyze  routing_threshold_lookup                   ok    
0.059        /api/alert/analyze  rl_exploration_proposal                    ok    
0.025        /api/alert/analyze  routing_zone_resolution                    ok    
184.978      /api/alert/analyze  referral_history_counts                    ok    
0.102        /api/alert/analyze  referral_gate_evaluation                   ok    
195.123      /api/alert/analyze  reasoning_generation                       ok    
78.442       /api/alert/analyze  decision_node_and_edge_write               ok    
79.918       /api/alert/analyze  audit_write                                ok    
0.366        /api/alert/analyze  metadata_logging_snapshot_write            ok    
97.267       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
74.469       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
98.574       /api/alert/analyze  campaign_query_update_campaign             ok    
107.47       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
107.001      /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
81.209       /api/alert/analyze  campaign_query_member_edges_batch_create   error 
581.392      /api/alert/analyze  campaign_correlation_summary               ok    
684.045      /api/alert/analyze  campaign_correlation                       ok    
0.087        /api/alert/analyze  decision_event_emit                        ok    
84.769       /api/alert/analyze  composite_gate_evaluation                  ok    
0.148        /api/alert/analyze  provenance_build                           ok    
96.411       /api/alert/analyze  graph_visualization_fetch                  ok    
0.052        /api/alert/analyze  response_context_enrichment                ok    
0.058        /api/alert/analyze  referral_debug_build                       ok    
0.033        /api/alert/analyze  shadow_compare_schedule                    ok    
99.993       /api/alert/analyze  cluster_history_fetch                      ok    
0.079        /api/alert/analyze  narrative_context_build                    ok    
0.099        /api/alert/analyze  narrative_generation                       ok    
5.588        /api/alert/analyze  response_serialization                     ok    
2089.351     /api/alert/analyze  analyze_request_total                      ok    
0.024        /api/alert/outcome  request_parse                              ok    
0.024        /api/alert/outcome  duplicate_feedback_guard                   ok    
104.391      /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.411        /api/alert/outcome  outcome_audit_write                        ok    
211.185      /api/alert/outcome  learning_state_update                      ok    
441.848      /api/alert/outcome  l5_conservation_write                      ok    
443.661      /api/alert/outcome  conservation_monitor                       ok    
0.297        /api/alert/outcome  profile_scorer_update                      ok    
0.338        /api/alert/outcome  l5_dk_weight_write                         ok    
455.872      /api/alert/outcome  l5_centroid_write                          ok    
0.017        /api/alert/outcome  l5_dk_weight_write                         ok    
0.031        /api/alert/outcome  snapshot_evolution_logging                 ok    
95.651       /api/alert/outcome  snapshot_evolution_logging                 ok    
0.037        /api/alert/outcome  response_serialization                     ok    
1801.176     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1FIX-0019
- event_count: 52
- total_observed_ms: 9210.073
- authoritative_total_ms: 2080.337
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.045        /api/alert/analyze  scorer_readiness                           ok    
0.025        /api/alert/analyze  request_parse                              ok    
99.304       /api/alert/analyze  alert_lookup                               ok    
85.712       /api/alert/analyze  security_context_lookup                    ok    
0.326        /api/alert/analyze  category_resolution                        ok    
377.743      /api/alert/analyze  factor_vector_construction                 ok    
0.479        /api/alert/analyze  scorer_decision                            ok    
0.038        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.022        /api/alert/analyze  routing_threshold_lookup                   ok    
0.02         /api/alert/analyze  rl_exploration_proposal                    ok    
0.041        /api/alert/analyze  routing_zone_resolution                    ok    
190.309      /api/alert/analyze  referral_history_counts                    ok    
0.059        /api/alert/analyze  referral_gate_evaluation                   ok    
93.847       /api/alert/analyze  reasoning_generation                       ok    
103.78       /api/alert/analyze  decision_node_and_edge_write               ok    
97.358       /api/alert/analyze  audit_write                                ok    
0.491        /api/alert/analyze  metadata_logging_snapshot_write            ok    
98.027       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
95.063       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
88.177       /api/alert/analyze  campaign_query_update_campaign             ok    
98.869       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
86.686       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
89.024       /api/alert/analyze  campaign_query_member_edges_batch_create   error 
572.904      /api/alert/analyze  campaign_correlation_summary               ok    
676.23       /api/alert/analyze  campaign_correlation                       ok    
0.045        /api/alert/analyze  decision_event_emit                        ok    
105.848      /api/alert/analyze  composite_gate_evaluation                  ok    
0.102        /api/alert/analyze  provenance_build                           ok    
98.764       /api/alert/analyze  graph_visualization_fetch                  ok    
0.032        /api/alert/analyze  response_context_enrichment                ok    
0.052        /api/alert/analyze  referral_debug_build                       ok    
0.014        /api/alert/analyze  shadow_compare_schedule                    ok    
83.038       /api/alert/analyze  cluster_history_fetch                      ok    
0.055        /api/alert/analyze  narrative_context_build                    ok    
0.064        /api/alert/analyze  narrative_generation                       ok    
3.776        /api/alert/analyze  response_serialization                     ok    
2080.337     /api/alert/analyze  analyze_request_total                      ok    
0.024        /api/alert/outcome  request_parse                              ok    
0.012        /api/alert/outcome  duplicate_feedback_guard                   ok    
93.788       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.51         /api/alert/outcome  outcome_audit_write                        ok    
181.34       /api/alert/outcome  learning_state_update                      ok    
549.298      /api/alert/outcome  l5_conservation_write                      ok    
552.213      /api/alert/outcome  conservation_monitor                       ok    
0.276        /api/alert/outcome  profile_scorer_update                      ok    
0.221        /api/alert/outcome  l5_dk_weight_write                         ok    
519.524      /api/alert/outcome  l5_centroid_write                          ok    
0.056        /api/alert/outcome  l5_dk_weight_write                         ok    
0.039        /api/alert/outcome  snapshot_evolution_logging                 ok    
107.698      /api/alert/outcome  snapshot_evolution_logging                 ok    
0.056        /api/alert/outcome  response_serialization                     ok    
1978.312     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1FIX-0004
- event_count: 47
- total_observed_ms: 7467.048
- authoritative_total_ms: 2060.816
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.043        /api/alert/analyze  scorer_readiness                    ok    
0.027        /api/alert/analyze  request_parse                       ok    
113.199      /api/alert/analyze  alert_lookup                        ok    
111.168      /api/alert/analyze  security_context_lookup             ok    
0.261        /api/alert/analyze  category_resolution                 ok    
376.722      /api/alert/analyze  factor_vector_construction          ok    
0.64         /api/alert/analyze  scorer_decision                     ok    
0.025        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.025        /api/alert/analyze  routing_threshold_lookup            ok    
0.038        /api/alert/analyze  rl_exploration_proposal             ok    
0.023        /api/alert/analyze  routing_zone_resolution             ok    
173.487      /api/alert/analyze  referral_history_counts             ok    
0.098        /api/alert/analyze  referral_gate_evaluation            ok    
107.582      /api/alert/analyze  reasoning_generation                ok    
111.437      /api/alert/analyze  decision_node_and_edge_write        ok    
101.705      /api/alert/analyze  audit_write                         ok    
2.16         /api/alert/analyze  metadata_logging_snapshot_write     ok    
109.035      /api/alert/analyze  campaign_query_fetch_recent_events  ok    
116.051      /api/alert/analyze  campaign_correlation_summary        ok    
131.519      /api/alert/analyze  campaign_correlation                ok    
0.083        /api/alert/analyze  decision_event_emit                 ok    
82.83        /api/alert/analyze  composite_gate_evaluation           ok    
0.045        /api/alert/analyze  provenance_build                    ok    
81.97        /api/alert/analyze  graph_visualization_fetch           ok    
0.024        /api/alert/analyze  response_context_enrichment         ok    
0.096        /api/alert/analyze  referral_debug_build                ok    
0.013        /api/alert/analyze  shadow_compare_schedule             ok    
90.502       /api/alert/analyze  cluster_history_fetch               ok    
0.039        /api/alert/analyze  narrative_context_build             ok    
0.103        /api/alert/analyze  narrative_generation                ok    
3.712        /api/alert/analyze  response_serialization              ok    
1568.036     /api/alert/analyze  analyze_request_total               ok    
0.008        /api/alert/outcome  request_parse                       ok    
0.019        /api/alert/outcome  duplicate_feedback_guard            ok    
113.734      /api/alert/outcome  decision_lookup_and_outcome_update  ok    
1.303        /api/alert/outcome  outcome_audit_write                 ok    
189.874      /api/alert/outcome  learning_state_update               ok    
586.42       /api/alert/outcome  l5_conservation_write               ok    
588.537      /api/alert/outcome  conservation_monitor                ok    
0.361        /api/alert/outcome  profile_scorer_update               ok    
0.113        /api/alert/outcome  l5_dk_weight_write                  ok    
558.497      /api/alert/outcome  l5_centroid_write                   ok    
0.034        /api/alert/outcome  l5_dk_weight_write                  ok    
0.029        /api/alert/outcome  snapshot_evolution_logging          ok    
84.523       /api/alert/outcome  snapshot_evolution_logging          ok    
0.082        /api/alert/outcome  response_serialization              ok    
2060.816     /api/alert/outcome  outcome_request_total               ok    
```

### CAMPAIGNP1FIX-0020
- event_count: 52
- total_observed_ms: 8452.717
- authoritative_total_ms: 2039.488
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.049        /api/alert/analyze  scorer_readiness                           ok    
0.023        /api/alert/analyze  request_parse                              ok    
90.041       /api/alert/analyze  alert_lookup                               ok    
121.603      /api/alert/analyze  security_context_lookup                    ok    
0.274        /api/alert/analyze  category_resolution                        ok    
381.267      /api/alert/analyze  factor_vector_construction                 ok    
0.727        /api/alert/analyze  scorer_decision                            ok    
0.048        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.016        /api/alert/analyze  routing_threshold_lookup                   ok    
0.027        /api/alert/analyze  rl_exploration_proposal                    ok    
0.03         /api/alert/analyze  routing_zone_resolution                    ok    
183.375      /api/alert/analyze  referral_history_counts                    ok    
0.078        /api/alert/analyze  referral_gate_evaluation                   ok    
95.901       /api/alert/analyze  reasoning_generation                       ok    
111.652      /api/alert/analyze  decision_node_and_edge_write               ok    
119.734      /api/alert/analyze  audit_write                                ok    
0.21         /api/alert/analyze  metadata_logging_snapshot_write            ok    
101.531      /api/alert/analyze  campaign_query_fetch_recent_events         ok    
93.037       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
76.334       /api/alert/analyze  campaign_query_update_campaign             ok    
93.129       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
77.691       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
77.711       /api/alert/analyze  campaign_query_member_edges_batch_create   error 
533.211      /api/alert/analyze  campaign_correlation_summary               ok    
617.705      /api/alert/analyze  campaign_correlation                       ok    
0.038        /api/alert/analyze  decision_event_emit                        ok    
85.262       /api/alert/analyze  composite_gate_evaluation                  ok    
0.085        /api/alert/analyze  provenance_build                           ok    
81.712       /api/alert/analyze  graph_visualization_fetch                  ok    
0.042        /api/alert/analyze  response_context_enrichment                ok    
0.049        /api/alert/analyze  referral_debug_build                       ok    
0.02         /api/alert/analyze  shadow_compare_schedule                    ok    
79.24        /api/alert/analyze  cluster_history_fetch                      ok    
0.057        /api/alert/analyze  narrative_context_build                    ok    
0.068        /api/alert/analyze  narrative_generation                       ok    
3.738        /api/alert/analyze  response_serialization                     ok    
2039.488     /api/alert/analyze  analyze_request_total                      ok    
0.015        /api/alert/outcome  request_parse                              ok    
0.014        /api/alert/outcome  duplicate_feedback_guard                   ok    
79.045       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.423        /api/alert/outcome  outcome_audit_write                        ok    
119.799      /api/alert/outcome  learning_state_update                      ok    
465.626      /api/alert/outcome  l5_conservation_write                      ok    
467.906      /api/alert/outcome  conservation_monitor                       ok    
0.452        /api/alert/outcome  profile_scorer_update                      ok    
0.193        /api/alert/outcome  l5_dk_weight_write                         ok    
459.919      /api/alert/outcome  l5_centroid_write                          ok    
0.024        /api/alert/outcome  l5_dk_weight_write                         ok    
0.022        /api/alert/outcome  snapshot_evolution_logging                 ok    
97.204       /api/alert/outcome  snapshot_evolution_logging                 ok    
0.034        /api/alert/outcome  response_serialization                     ok    
1696.838     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1FIX-0006
- event_count: 47
- total_observed_ms: 7164.907
- authoritative_total_ms: 2034.531
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.031        /api/alert/analyze  scorer_readiness                    ok    
0.017        /api/alert/analyze  request_parse                       ok    
73.943       /api/alert/analyze  alert_lookup                        ok    
67.494       /api/alert/analyze  security_context_lookup             ok    
0.118        /api/alert/analyze  category_resolution                 ok    
333.174      /api/alert/analyze  factor_vector_construction          ok    
0.833        /api/alert/analyze  scorer_decision                     ok    
0.034        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.02         /api/alert/analyze  routing_threshold_lookup            ok    
0.033        /api/alert/analyze  rl_exploration_proposal             ok    
0.047        /api/alert/analyze  routing_zone_resolution             ok    
207.075      /api/alert/analyze  referral_history_counts             ok    
0.084        /api/alert/analyze  referral_gate_evaluation            ok    
101.704      /api/alert/analyze  reasoning_generation                ok    
104.447      /api/alert/analyze  decision_node_and_edge_write        ok    
113.72       /api/alert/analyze  audit_write                         ok    
0.228        /api/alert/analyze  metadata_logging_snapshot_write     ok    
107.657      /api/alert/analyze  campaign_query_fetch_recent_events  ok    
111.563      /api/alert/analyze  campaign_correlation_summary        ok    
113.949      /api/alert/analyze  campaign_correlation                ok    
0.06         /api/alert/analyze  decision_event_emit                 ok    
107.682      /api/alert/analyze  composite_gate_evaluation           ok    
0.158        /api/alert/analyze  provenance_build                    ok    
100.117      /api/alert/analyze  graph_visualization_fetch           ok    
0.07         /api/alert/analyze  response_context_enrichment         ok    
1.297        /api/alert/analyze  referral_debug_build                ok    
0.035        /api/alert/analyze  shadow_compare_schedule             ok    
100.46       /api/alert/analyze  cluster_history_fetch               ok    
0.063        /api/alert/analyze  narrative_context_build             ok    
0.103        /api/alert/analyze  narrative_generation                ok    
7.546        /api/alert/analyze  response_serialization              ok    
1511.961     /api/alert/analyze  analyze_request_total               ok    
0.02         /api/alert/outcome  request_parse                       ok    
0.009        /api/alert/outcome  duplicate_feedback_guard            ok    
86.78        /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.406        /api/alert/outcome  outcome_audit_write                 ok    
193.212      /api/alert/outcome  learning_state_update               ok    
504.509      /api/alert/outcome  l5_conservation_write               ok    
508.354      /api/alert/outcome  conservation_monitor                ok    
0.354        /api/alert/outcome  profile_scorer_update               ok    
0.339        /api/alert/outcome  l5_dk_weight_write                  ok    
561.856      /api/alert/outcome  l5_centroid_write                   ok    
0.048        /api/alert/outcome  l5_dk_weight_write                  ok    
0.076        /api/alert/outcome  snapshot_evolution_logging          ok    
108.645      /api/alert/outcome  snapshot_evolution_logging          ok    
0.045        /api/alert/outcome  response_serialization              ok    
2034.531     /api/alert/outcome  outcome_request_total               ok    
```

### CAMPAIGNP1FIX-0002
- event_count: 47
- total_observed_ms: 7087.74
- authoritative_total_ms: 2034.253
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.067        /api/alert/analyze  scorer_readiness                    ok    
0.023        /api/alert/analyze  request_parse                       ok    
107.897      /api/alert/analyze  alert_lookup                        ok    
111.847      /api/alert/analyze  security_context_lookup             ok    
0.244        /api/alert/analyze  category_resolution                 ok    
426.543      /api/alert/analyze  factor_vector_construction          ok    
0.268        /api/alert/analyze  scorer_decision                     ok    
0.021        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.014        /api/alert/analyze  routing_threshold_lookup            ok    
0.018        /api/alert/analyze  rl_exploration_proposal             ok    
0.029        /api/alert/analyze  routing_zone_resolution             ok    
155.29       /api/alert/analyze  referral_history_counts             ok    
0.052        /api/alert/analyze  referral_gate_evaluation            ok    
105.946      /api/alert/analyze  reasoning_generation                ok    
93.746       /api/alert/analyze  decision_node_and_edge_write        ok    
73.204       /api/alert/analyze  audit_write                         ok    
0.548        /api/alert/analyze  metadata_logging_snapshot_write     ok    
78.272       /api/alert/analyze  campaign_query_fetch_recent_events  ok    
79.649       /api/alert/analyze  campaign_correlation_summary        ok    
81.389       /api/alert/analyze  campaign_correlation                ok    
0.024        /api/alert/analyze  decision_event_emit                 ok    
90.042       /api/alert/analyze  composite_gate_evaluation           ok    
0.136        /api/alert/analyze  provenance_build                    ok    
77.148       /api/alert/analyze  graph_visualization_fetch           ok    
0.04         /api/alert/analyze  response_context_enrichment         ok    
0.074        /api/alert/analyze  referral_debug_build                ok    
0.036        /api/alert/analyze  shadow_compare_schedule             ok    
93.078       /api/alert/analyze  cluster_history_fetch               ok    
0.043        /api/alert/analyze  narrative_context_build             ok    
0.053        /api/alert/analyze  narrative_generation                ok    
3.203        /api/alert/analyze  response_serialization              ok    
1474.71      /api/alert/analyze  analyze_request_total               ok    
0.012        /api/alert/outcome  request_parse                       ok    
0.027        /api/alert/outcome  duplicate_feedback_guard            ok    
87.581       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.464        /api/alert/outcome  outcome_audit_write                 ok    
182.814      /api/alert/outcome  learning_state_update               ok    
531.083      /api/alert/outcome  l5_conservation_write               ok    
533.939      /api/alert/outcome  conservation_monitor                ok    
0.315        /api/alert/outcome  profile_scorer_update               ok    
0.421        /api/alert/outcome  l5_dk_weight_write                  ok    
564.093      /api/alert/outcome  l5_centroid_write                   ok    
0.049        /api/alert/outcome  l5_dk_weight_write                  ok    
0.04         /api/alert/outcome  snapshot_evolution_logging          ok    
98.923       /api/alert/outcome  snapshot_evolution_logging          ok    
0.072        /api/alert/outcome  response_serialization              ok    
2034.253     /api/alert/outcome  outcome_request_total               ok    
```

### CAMPAIGNP1FIX-0023
- event_count: 52
- total_observed_ms: 9048.143
- authoritative_total_ms: 2027.664
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.046        /api/alert/analyze  scorer_readiness                           ok    
0.022        /api/alert/analyze  request_parse                              ok    
79.372       /api/alert/analyze  alert_lookup                               ok    
77.004       /api/alert/analyze  security_context_lookup                    ok    
0.085        /api/alert/analyze  category_resolution                        ok    
333.597      /api/alert/analyze  factor_vector_construction                 ok    
0.416        /api/alert/analyze  scorer_decision                            ok    
0.038        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.016        /api/alert/analyze  routing_threshold_lookup                   ok    
0.021        /api/alert/analyze  rl_exploration_proposal                    ok    
0.04         /api/alert/analyze  routing_zone_resolution                    ok    
162.958      /api/alert/analyze  referral_history_counts                    ok    
0.074        /api/alert/analyze  referral_gate_evaluation                   ok    
90.654       /api/alert/analyze  reasoning_generation                       ok    
95.193       /api/alert/analyze  decision_node_and_edge_write               ok    
99.432       /api/alert/analyze  audit_write                                ok    
0.3          /api/alert/analyze  metadata_logging_snapshot_write            ok    
94.439       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
98.671       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
93.928       /api/alert/analyze  campaign_query_update_campaign             ok    
109.917      /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
90.625       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
89.118       /api/alert/analyze  campaign_query_member_edges_batch_create   error 
596.672      /api/alert/analyze  campaign_correlation_summary               ok    
721.94       /api/alert/analyze  campaign_correlation                       ok    
0.295        /api/alert/analyze  decision_event_emit                        ok    
120.566      /api/alert/analyze  composite_gate_evaluation                  ok    
0.182        /api/alert/analyze  provenance_build                           ok    
88.895       /api/alert/analyze  graph_visualization_fetch                  ok    
0.073        /api/alert/analyze  response_context_enrichment                ok    
0.057        /api/alert/analyze  referral_debug_build                       ok    
0.033        /api/alert/analyze  shadow_compare_schedule                    ok    
87.396       /api/alert/analyze  cluster_history_fetch                      ok    
0.098        /api/alert/analyze  narrative_context_build                    ok    
0.09         /api/alert/analyze  narrative_generation                       ok    
4.783        /api/alert/analyze  response_serialization                     ok    
2027.664     /api/alert/analyze  analyze_request_total                      ok    
0.023        /api/alert/outcome  request_parse                              ok    
0.024        /api/alert/outcome  duplicate_feedback_guard                   ok    
102.083      /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.429        /api/alert/outcome  outcome_audit_write                        ok    
164.383      /api/alert/outcome  learning_state_update                      ok    
516.412      /api/alert/outcome  l5_conservation_write                      ok    
518.358      /api/alert/outcome  conservation_monitor                       ok    
0.386        /api/alert/outcome  profile_scorer_update                      ok    
0.181        /api/alert/outcome  l5_dk_weight_write                         ok    
526.162      /api/alert/outcome  l5_centroid_write                          ok    
0.041        /api/alert/outcome  l5_dk_weight_write                         ok    
0.035        /api/alert/outcome  snapshot_evolution_logging                 ok    
113.727      /api/alert/outcome  snapshot_evolution_logging                 ok    
0.059        /api/alert/outcome  response_serialization                     ok    
1941.13      /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1FIX-0003
- event_count: 47
- total_observed_ms: 7616.438
- authoritative_total_ms: 1978.236
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.034        /api/alert/analyze  scorer_readiness                    ok    
0.018        /api/alert/analyze  request_parse                       ok    
81.208       /api/alert/analyze  alert_lookup                        ok    
98.982       /api/alert/analyze  security_context_lookup             ok    
0.583        /api/alert/analyze  category_resolution                 ok    
503.543      /api/alert/analyze  factor_vector_construction          ok    
0.643        /api/alert/analyze  scorer_decision                     ok    
0.049        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.034        /api/alert/analyze  routing_threshold_lookup            ok    
0.046        /api/alert/analyze  rl_exploration_proposal             ok    
0.082        /api/alert/analyze  routing_zone_resolution             ok    
218.536      /api/alert/analyze  referral_history_counts             ok    
0.093        /api/alert/analyze  referral_gate_evaluation            ok    
342.851      /api/alert/analyze  reasoning_generation                ok    
89.132       /api/alert/analyze  decision_node_and_edge_write        ok    
111.078      /api/alert/analyze  audit_write                         ok    
13.582       /api/alert/analyze  metadata_logging_snapshot_write     ok    
104.555      /api/alert/analyze  campaign_query_fetch_recent_events  ok    
107.488      /api/alert/analyze  campaign_correlation_summary        ok    
109.548      /api/alert/analyze  campaign_correlation                ok    
0.053        /api/alert/analyze  decision_event_emit                 ok    
106.613      /api/alert/analyze  composite_gate_evaluation           ok    
0.13         /api/alert/analyze  provenance_build                    ok    
100.587      /api/alert/analyze  graph_visualization_fetch           ok    
0.054        /api/alert/analyze  response_context_enrichment         ok    
0.066        /api/alert/analyze  referral_debug_build                ok    
0.036        /api/alert/analyze  shadow_compare_schedule             ok    
95.594       /api/alert/analyze  cluster_history_fetch               ok    
0.054        /api/alert/analyze  narrative_context_build             ok    
0.109        /api/alert/analyze  narrative_generation                ok    
4.371        /api/alert/analyze  response_serialization              ok    
1978.236     /api/alert/analyze  analyze_request_total               ok    
0.02         /api/alert/outcome  request_parse                       ok    
0.02         /api/alert/outcome  duplicate_feedback_guard            ok    
107.188      /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.552        /api/alert/outcome  outcome_audit_write                 ok    
119.827      /api/alert/outcome  learning_state_update               ok    
514.062      /api/alert/outcome  l5_conservation_write               ok    
521.019      /api/alert/outcome  conservation_monitor                ok    
12.041       /api/alert/outcome  profile_scorer_update               ok    
2.632        /api/alert/outcome  l5_dk_weight_write                  ok    
427.566      /api/alert/outcome  l5_centroid_write                   ok    
0.011        /api/alert/outcome  l5_dk_weight_write                  ok    
0.02         /api/alert/outcome  snapshot_evolution_logging          ok    
84.735       /api/alert/outcome  snapshot_evolution_logging          ok    
0.038        /api/alert/outcome  response_serialization              ok    
1758.719     /api/alert/outcome  outcome_request_total               ok    
```

### CAMPAIGNP1FIX-0008
- event_count: 52
- total_observed_ms: 8460.242
- authoritative_total_ms: 1965.623
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.042        /api/alert/analyze  scorer_readiness                           ok    
0.024        /api/alert/analyze  request_parse                              ok    
84.677       /api/alert/analyze  alert_lookup                               ok    
90.749       /api/alert/analyze  security_context_lookup                    ok    
0.174        /api/alert/analyze  category_resolution                        ok    
342.751      /api/alert/analyze  factor_vector_construction                 ok    
0.301        /api/alert/analyze  scorer_decision                            ok    
0.024        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.024        /api/alert/analyze  routing_threshold_lookup                   ok    
0.037        /api/alert/analyze  rl_exploration_proposal                    ok    
0.042        /api/alert/analyze  routing_zone_resolution                    ok    
186.404      /api/alert/analyze  referral_history_counts                    ok    
0.085        /api/alert/analyze  referral_gate_evaluation                   ok    
102.167      /api/alert/analyze  reasoning_generation                       ok    
109.053      /api/alert/analyze  decision_node_and_edge_write               ok    
89.453       /api/alert/analyze  audit_write                                ok    
0.444        /api/alert/analyze  metadata_logging_snapshot_write            ok    
105.83       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
89.272       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
88.508       /api/alert/analyze  campaign_query_create_campaign             ok    
88.898       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
83.422       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
81.545       /api/alert/analyze  campaign_query_member_edges_batch_create   error 
555.236      /api/alert/analyze  campaign_correlation_summary               ok    
643.607      /api/alert/analyze  campaign_correlation                       ok    
0.056        /api/alert/analyze  decision_event_emit                        ok    
76.661       /api/alert/analyze  composite_gate_evaluation                  ok    
0.145        /api/alert/analyze  provenance_build                           ok    
83.783       /api/alert/analyze  graph_visualization_fetch                  ok    
0.028        /api/alert/analyze  response_context_enrichment                ok    
0.063        /api/alert/analyze  referral_debug_build                       ok    
0.03         /api/alert/analyze  shadow_compare_schedule                    ok    
84.406       /api/alert/analyze  cluster_history_fetch                      ok    
0.067        /api/alert/analyze  narrative_context_build                    ok    
0.127        /api/alert/analyze  narrative_generation                       ok    
4.534        /api/alert/analyze  response_serialization                     ok    
1965.623     /api/alert/analyze  analyze_request_total                      ok    
0.021        /api/alert/outcome  request_parse                              ok    
0.021        /api/alert/outcome  duplicate_feedback_guard                   ok    
88.222       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.364        /api/alert/outcome  outcome_audit_write                        ok    
158.834      /api/alert/outcome  learning_state_update                      ok    
457.554      /api/alert/outcome  l5_conservation_write                      ok    
460.042      /api/alert/outcome  conservation_monitor                       ok    
0.302        /api/alert/outcome  profile_scorer_update                      ok    
0.134        /api/alert/outcome  l5_dk_weight_write                         ok    
454.113      /api/alert/outcome  l5_centroid_write                          ok    
0.043        /api/alert/outcome  l5_dk_weight_write                         ok    
0.024        /api/alert/outcome  snapshot_evolution_logging                 ok    
109.203      /api/alert/outcome  snapshot_evolution_logging                 ok    
0.051        /api/alert/outcome  response_serialization                     ok    
1773.022     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1FIX-0018
- event_count: 52
- total_observed_ms: 8179.907
- authoritative_total_ms: 1959.244
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.034        /api/alert/analyze  scorer_readiness                           ok    
0.025        /api/alert/analyze  request_parse                              ok    
90.693       /api/alert/analyze  alert_lookup                               ok    
118.665      /api/alert/analyze  security_context_lookup                    ok    
0.262        /api/alert/analyze  category_resolution                        ok    
347.524      /api/alert/analyze  factor_vector_construction                 ok    
0.427        /api/alert/analyze  scorer_decision                            ok    
0.031        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.02         /api/alert/analyze  routing_threshold_lookup                   ok    
0.035        /api/alert/analyze  rl_exploration_proposal                    ok    
0.039        /api/alert/analyze  routing_zone_resolution                    ok    
158.117      /api/alert/analyze  referral_history_counts                    ok    
0.086        /api/alert/analyze  referral_gate_evaluation                   ok    
70.697       /api/alert/analyze  reasoning_generation                       ok    
90.499       /api/alert/analyze  decision_node_and_edge_write               ok    
92.924       /api/alert/analyze  audit_write                                ok    
0.298        /api/alert/analyze  metadata_logging_snapshot_write            ok    
109.411      /api/alert/analyze  campaign_query_fetch_recent_events         ok    
91.182       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
92.023       /api/alert/analyze  campaign_query_update_campaign             ok    
105.435      /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
76.746       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
83.711       /api/alert/analyze  campaign_query_member_edges_batch_create   error 
572.047      /api/alert/analyze  campaign_correlation_summary               ok    
657.205      /api/alert/analyze  campaign_correlation                       ok    
0.045        /api/alert/analyze  decision_event_emit                        ok    
89.58        /api/alert/analyze  composite_gate_evaluation                  ok    
0.229        /api/alert/analyze  provenance_build                           ok    
87.89        /api/alert/analyze  graph_visualization_fetch                  ok    
0.039        /api/alert/analyze  response_context_enrichment                ok    
0.06         /api/alert/analyze  referral_debug_build                       ok    
0.032        /api/alert/analyze  shadow_compare_schedule                    ok    
82.78        /api/alert/analyze  cluster_history_fetch                      ok    
0.072        /api/alert/analyze  narrative_context_build                    ok    
0.113        /api/alert/analyze  narrative_generation                       ok    
4.82         /api/alert/analyze  response_serialization                     ok    
1959.244     /api/alert/analyze  analyze_request_total                      ok    
0.03         /api/alert/outcome  request_parse                              ok    
0.021        /api/alert/outcome  duplicate_feedback_guard                   ok    
84.145       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.407        /api/alert/outcome  outcome_audit_write                        ok    
182.706      /api/alert/outcome  learning_state_update                      ok    
368.954      /api/alert/outcome  l5_conservation_write                      ok    
370.201      /api/alert/outcome  conservation_monitor                       ok    
0.285        /api/alert/outcome  profile_scorer_update                      ok    
0.252        /api/alert/outcome  l5_dk_weight_write                         ok    
455.573      /api/alert/outcome  l5_centroid_write                          ok    
0.031        /api/alert/outcome  l5_dk_weight_write                         ok    
0.064        /api/alert/outcome  snapshot_evolution_logging                 ok    
104.384      /api/alert/outcome  snapshot_evolution_logging                 ok    
0.05         /api/alert/outcome  response_serialization                     ok    
1629.764     /api/alert/outcome  outcome_request_total                      ok    
```

### CAMPAIGNP1FIX-0021
- event_count: 52
- total_observed_ms: 7237.662
- authoritative_total_ms: 1722.074
```text
duration_ms  route               phase                                      status
-----------  ------------------  -----------------------------------------  ------
0.025        /api/alert/analyze  scorer_readiness                           ok    
0.015        /api/alert/analyze  request_parse                              ok    
78.797       /api/alert/analyze  alert_lookup                               ok    
66.802       /api/alert/analyze  security_context_lookup                    ok    
0.236        /api/alert/analyze  category_resolution                        ok    
279.506      /api/alert/analyze  factor_vector_construction                 ok    
0.339        /api/alert/analyze  scorer_decision                            ok    
0.012        /api/alert/analyze  post_scorer_confidence_gate                ok    
0.005        /api/alert/analyze  routing_threshold_lookup                   ok    
0.024        /api/alert/analyze  rl_exploration_proposal                    ok    
0.022        /api/alert/analyze  routing_zone_resolution                    ok    
135.108      /api/alert/analyze  referral_history_counts                    ok    
0.077        /api/alert/analyze  referral_gate_evaluation                   ok    
109.432      /api/alert/analyze  reasoning_generation                       ok    
77.915       /api/alert/analyze  decision_node_and_edge_write               ok    
83.739       /api/alert/analyze  audit_write                                ok    
0.292        /api/alert/analyze  metadata_logging_snapshot_write            ok    
93.184       /api/alert/analyze  campaign_query_fetch_recent_events         ok    
77.123       /api/alert/analyze  campaign_query_check_campaign_exists       ok    
90.221       /api/alert/analyze  campaign_query_update_campaign             ok    
82.756       /api/alert/analyze  campaign_query_member_edges_existing_read  ok    
76.909       /api/alert/analyze  campaign_query_member_alert_nodes_read     ok    
69.14        /api/alert/analyze  campaign_query_member_edges_batch_create   error 
503.939      /api/alert/analyze  campaign_correlation_summary               ok    
595.548      /api/alert/analyze  campaign_correlation                       ok    
0.046        /api/alert/analyze  decision_event_emit                        ok    
68.868       /api/alert/analyze  composite_gate_evaluation                  ok    
0.044        /api/alert/analyze  provenance_build                           ok    
73.638       /api/alert/analyze  graph_visualization_fetch                  ok    
0.042        /api/alert/analyze  response_context_enrichment                ok    
0.04         /api/alert/analyze  referral_debug_build                       ok    
0.023        /api/alert/analyze  shadow_compare_schedule                    ok    
100.156      /api/alert/analyze  cluster_history_fetch                      ok    
0.054        /api/alert/analyze  narrative_context_build                    ok    
0.056        /api/alert/analyze  narrative_generation                       ok    
3.705        /api/alert/analyze  response_serialization                     ok    
1722.074     /api/alert/analyze  analyze_request_total                      ok    
0.013        /api/alert/outcome  request_parse                              ok    
0.009        /api/alert/outcome  duplicate_feedback_guard                   ok    
93.151       /api/alert/outcome  decision_lookup_and_outcome_update         ok    
0.339        /api/alert/outcome  outcome_audit_write                        ok    
100.366      /api/alert/outcome  learning_state_update                      ok    
368.542      /api/alert/outcome  l5_conservation_write                      ok    
369.871      /api/alert/outcome  conservation_monitor                       ok    
0.122        /api/alert/outcome  profile_scorer_update                      ok    
0.193        /api/alert/outcome  l5_dk_weight_write                         ok    
385.161      /api/alert/outcome  l5_centroid_write                          ok    
0.033        /api/alert/outcome  l5_dk_weight_write                         ok    
0.013        /api/alert/outcome  snapshot_evolution_logging                 ok    
88.628       /api/alert/outcome  snapshot_evolution_logging                 ok    
0.026        /api/alert/outcome  response_serialization                     ok    
1441.283     /api/alert/outcome  outcome_request_total                      ok    
```

## Nested Phase Warning
Nested phase durations should not be summed blindly. Use analyze_request_total, outcome_request_total, or total_attempt as authoritative totals.
