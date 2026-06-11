# SOC Perf Trace Summary

## Safety
- Read-only summary of existing JSONL trace events.
- No backend, graph, proof, or seed operations are performed.
- Nested phases are not additive; request-total phases are the authoritative route totals.

## Input
- trace_jsonl: `C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50\scratch\temp\soc_perf_trace_campaign_phase1_25_1.jsonl`
- events_loaded: 1175
- malformed_lines: 0
- route_filter: None
- phase_filter: None

## Route + Phase Aggregates
```text
route_phase                                              count  avg_ms    p50_ms    p95_ms    p99_ms    max_ms  
-------------------------------------------------------  -----  --------  --------  --------  --------  --------
/api/alert/analyze | analyze_request_total               25     1569.217  1558.743  1662.113  2035.464  2152.684
/api/alert/outcome | outcome_request_total               25     1957.381  1950.936  2062.384  2109.509  2122.401
/api/alert/outcome | l5_centroid_write                   25     528.649   531.722   583.814   603.302   608.069 
/api/alert/outcome | conservation_monitor                25     499.033   508.028   541.079   545.968   547.139 
/api/alert/outcome | l5_conservation_write               25     496.137   505.166   538.245   543.826   545.276 
/api/alert/analyze | reasoning_generation                25     96.843    73.868    114.762   385.567   470.483 
/api/alert/analyze | factor_vector_construction          25     387.32    391.487   418.675   419.578   419.696 
/api/alert/outcome | learning_state_update               25     180.464   165.395   222.781   365.598   409.264 
/api/alert/analyze | referral_history_counts             25     195.92    195.463   214.917   259.175   273.07  
/api/alert/outcome | snapshot_evolution_logging          50     57.007    80.71     124.981   151.032   169.715 
/api/alert/analyze | campaign_correlation                25     107.833   105.896   124.809   158.798   169.433 
/api/alert/analyze | campaign_correlation_summary        25     105.221   103.245   122.265   155.281   165.599 
/api/alert/analyze | campaign_query_fetch_recent_events  25     101.692   99.123    118.702   151.596   161.858 
/api/alert/analyze | audit_write                         25     103.183   100.884   128.137   152.31    159.16  
/api/alert/analyze | decision_node_and_edge_write        25     105.49    104.284   117.185   145.727   154.512 
/api/alert/outcome | decision_lookup_and_outcome_update  25     109.413   110.076   130.964   136.733   138.461 
/api/alert/analyze | security_context_lookup             25     102.359   100.58    127.254   130.566   130.835 
/api/alert/analyze | composite_gate_evaluation           25     95.926    92.991    110.569   117.032   119.065 
/api/alert/analyze | cluster_history_fetch               25     94.988    93.009    112.629   116.737   117.419 
/api/alert/analyze | graph_visualization_fetch           25     99.436    98.446    115.651   116.194   116.298 
/api/alert/analyze | alert_lookup                        25     94.432    93.574    109.403   112.703   113.622 
/api/alert/analyze | post_scorer_confidence_gate         25     1.205     0.04      0.048     22.2      29.196  
/api/alert/analyze | category_resolution                 25     0.889     0.275     0.512     11.879    15.465  
/api/alert/analyze | response_serialization              25     6.25      5.212     11.445    12.34     12.572  
/api/alert/analyze | scorer_decision                     25     0.821     0.441     2.244     6.219     7.372   
/api/alert/outcome | outcome_audit_write                 25     1.058     0.587     3.403     5.545     6.164   
/api/alert/analyze | metadata_logging_snapshot_write     25     0.529     0.367     1.607     1.98      2.049   
/api/alert/analyze | referral_debug_build                25     0.125     0.067     0.359     0.952     1.129   
/api/alert/outcome | l5_dk_weight_write                  50     0.168     0.093     0.411     0.569     0.674   
/api/alert/analyze | narrative_generation                25     0.133     0.107     0.282     0.528     0.596   
/api/alert/outcome | profile_scorer_update               25     0.342     0.35      0.418     0.52      0.551   
/api/alert/analyze | provenance_build                    25     0.153     0.128     0.331     0.459     0.489   
/api/alert/analyze | referral_gate_evaluation            25     0.102     0.086     0.242     0.307     0.319   
/api/alert/analyze | routing_zone_resolution             25     0.047     0.039     0.052     0.224     0.278   
/api/alert/analyze | shadow_compare_schedule             25     0.051     0.036     0.174     0.238     0.251   
/api/alert/analyze | narrative_context_build             25     0.072     0.069     0.101     0.178     0.201   
/api/alert/analyze | rl_exploration_proposal             25     0.036     0.033     0.038     0.153     0.189   
/api/alert/outcome | response_serialization              25     0.061     0.055     0.108     0.158     0.173   
/api/alert/analyze | decision_event_emit                 25     0.055     0.053     0.087     0.106     0.112   
/api/alert/analyze | response_context_enrichment         25     0.063     0.064     0.08      0.082     0.082   
```

## Phase Aggregates
```text
phase                               count  avg_ms    p50_ms    p95_ms    p99_ms    max_ms  
----------------------------------  -----  --------  --------  --------  --------  --------
analyze_request_total               25     1569.217  1558.743  1662.113  2035.464  2152.684
outcome_request_total               25     1957.381  1950.936  2062.384  2109.509  2122.401
l5_centroid_write                   25     528.649   531.722   583.814   603.302   608.069 
conservation_monitor                25     499.033   508.028   541.079   545.968   547.139 
l5_conservation_write               25     496.137   505.166   538.245   543.826   545.276 
reasoning_generation                25     96.843    73.868    114.762   385.567   470.483 
factor_vector_construction          25     387.32    391.487   418.675   419.578   419.696 
learning_state_update               25     180.464   165.395   222.781   365.598   409.264 
referral_history_counts             25     195.92    195.463   214.917   259.175   273.07  
snapshot_evolution_logging          50     57.007    80.71     124.981   151.032   169.715 
campaign_correlation                25     107.833   105.896   124.809   158.798   169.433 
campaign_correlation_summary        25     105.221   103.245   122.265   155.281   165.599 
campaign_query_fetch_recent_events  25     101.692   99.123    118.702   151.596   161.858 
audit_write                         25     103.183   100.884   128.137   152.31    159.16  
decision_node_and_edge_write        25     105.49    104.284   117.185   145.727   154.512 
decision_lookup_and_outcome_update  25     109.413   110.076   130.964   136.733   138.461 
security_context_lookup             25     102.359   100.58    127.254   130.566   130.835 
composite_gate_evaluation           25     95.926    92.991    110.569   117.032   119.065 
cluster_history_fetch               25     94.988    93.009    112.629   116.737   117.419 
graph_visualization_fetch           25     99.436    98.446    115.651   116.194   116.298 
alert_lookup                        25     94.432    93.574    109.403   112.703   113.622 
post_scorer_confidence_gate         25     1.205     0.04      0.048     22.2      29.196  
category_resolution                 25     0.889     0.275     0.512     11.879    15.465  
response_serialization              50     3.155     1.018     10.273    12.099    12.572  
scorer_decision                     25     0.821     0.441     2.244     6.219     7.372   
outcome_audit_write                 25     1.058     0.587     3.403     5.545     6.164   
metadata_logging_snapshot_write     25     0.529     0.367     1.607     1.98      2.049   
referral_debug_build                25     0.125     0.067     0.359     0.952     1.129   
l5_dk_weight_write                  50     0.168     0.093     0.411     0.569     0.674   
narrative_generation                25     0.133     0.107     0.282     0.528     0.596   
profile_scorer_update               25     0.342     0.35      0.418     0.52      0.551   
provenance_build                    25     0.153     0.128     0.331     0.459     0.489   
referral_gate_evaluation            25     0.102     0.086     0.242     0.307     0.319   
routing_zone_resolution             25     0.047     0.039     0.052     0.224     0.278   
shadow_compare_schedule             25     0.051     0.036     0.174     0.238     0.251   
narrative_context_build             25     0.072     0.069     0.101     0.178     0.201   
rl_exploration_proposal             25     0.036     0.033     0.038     0.153     0.189   
decision_event_emit                 25     0.055     0.053     0.087     0.106     0.112   
response_context_enrichment         25     0.063     0.064     0.08      0.082     0.082   
request_parse                       50     0.025     0.022     0.05      0.067     0.079   
```

## Graph Aggregates
```text
graph_name                      count  avg_ms   p50_ms  p95_ms  p99_ms    max_ms  
------------------------------  -----  -------  ------  ------  --------  --------
soc_graph_campaign_phase1_25_1  1175   152.285  0.524   545.46  1975.565  2152.684
```

## Top Slow Events
```text
duration_ms  route               phase                  alert_id             decision_id                           attempt_index  status
-----------  ------------------  ---------------------  -------------------  ------------------------------------  -------------  ------
2152.684     /api/alert/analyze  analyze_request_total  CAMPAIGNPHASE1-0001  be79e631-4ed1-42cd-97c6-a505182ecd55  None           ok    
2122.401     /api/alert/outcome  outcome_request_total  CAMPAIGNPHASE1-0022  dcbcdd44-b3d6-4236-a92b-e6ae2af29091  None           ok    
2068.686     /api/alert/outcome  outcome_request_total  CAMPAIGNPHASE1-0011  994b3425-5109-447d-bb60-53c3a618b1e1  None           ok    
2037.177     /api/alert/outcome  outcome_request_total  CAMPAIGNPHASE1-0005  72bfce18-b2d6-4d61-a845-4e141a9aae33  None           ok    
2030.763     /api/alert/outcome  outcome_request_total  CAMPAIGNPHASE1-0001  be79e631-4ed1-42cd-97c6-a505182ecd55  None           ok    
2014.286     /api/alert/outcome  outcome_request_total  CAMPAIGNPHASE1-0002  5f133740-6b52-4cfe-a66d-5caba3d17c1c  None           ok    
2013.769     /api/alert/outcome  outcome_request_total  CAMPAIGNPHASE1-0008  78bd3959-ae3b-4fc9-829f-d59aa476ce7b  None           ok    
1997.319     /api/alert/outcome  outcome_request_total  CAMPAIGNPHASE1-0024  e256df39-7180-488a-8ec3-7710beb2e449  None           ok    
1993.124     /api/alert/outcome  outcome_request_total  CAMPAIGNPHASE1-0023  b245c3e1-2582-4e5c-b217-315a0827dd00  None           ok    
1991.352     /api/alert/outcome  outcome_request_total  CAMPAIGNPHASE1-0003  2e925246-a547-423e-9922-922e42da5d89  None           ok    
1986.631     /api/alert/outcome  outcome_request_total  CAMPAIGNPHASE1-0007  9a8a4086-314f-428d-b3d5-66ac0390311e  None           ok    
1982.999     /api/alert/outcome  outcome_request_total  CAMPAIGNPHASE1-0014  7849edca-b201-48f9-bcf6-143ca283aca4  None           ok    
1972.953     /api/alert/outcome  outcome_request_total  CAMPAIGNPHASE1-0013  76ed1019-7a15-43d2-89d1-6783ff31d7f1  None           ok    
1950.936     /api/alert/outcome  outcome_request_total  CAMPAIGNPHASE1-0016  e8957787-cbaf-47d2-9588-d2bdb1fcf6aa  None           ok    
1944.121     /api/alert/outcome  outcome_request_total  CAMPAIGNPHASE1-0017  792437f0-7f8d-485b-a7f0-2727371511aa  None           ok    
1942.917     /api/alert/outcome  outcome_request_total  CAMPAIGNPHASE1-0010  ddb93eaa-2d6a-4047-bfc7-fb4747bc5cc3  None           ok    
1941.453     /api/alert/outcome  outcome_request_total  CAMPAIGNPHASE1-0009  a0261d32-2c9f-486f-9604-eb5655db8d06  None           ok    
1937.684     /api/alert/outcome  outcome_request_total  CAMPAIGNPHASE1-0025  2f5f2f93-5910-4310-9aff-c6a38d6a978e  None           ok    
1937.601     /api/alert/outcome  outcome_request_total  CAMPAIGNPHASE1-0012  baae715e-3b22-4e3b-8104-912999434dbb  None           ok    
1917.249     /api/alert/outcome  outcome_request_total  CAMPAIGNPHASE1-0018  a49715b6-b87d-4eba-9867-2519c6670011  None           ok    
```

## Early/Mid/Late Windows
```text
(none)
```

## Per-Alert Waterfall

### CAMPAIGNPHASE1-0001
- event_count: 47
- total_observed_ms: 8396.652
- authoritative_total_ms: 2152.684
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.042        /api/alert/analyze  scorer_readiness                    ok    
0.02         /api/alert/analyze  request_parse                       ok    
90.182       /api/alert/analyze  alert_lookup                        ok    
129.714      /api/alert/analyze  security_context_lookup             ok    
15.465       /api/alert/analyze  category_resolution                 ok    
419.206      /api/alert/analyze  factor_vector_construction          ok    
7.372        /api/alert/analyze  scorer_decision                     ok    
29.196       /api/alert/analyze  post_scorer_confidence_gate         ok    
0.028        /api/alert/analyze  routing_threshold_lookup            ok    
0.036        /api/alert/analyze  rl_exploration_proposal             ok    
0.053        /api/alert/analyze  routing_zone_resolution             ok    
192.226      /api/alert/analyze  referral_history_counts             ok    
0.144        /api/alert/analyze  referral_gate_evaluation            ok    
470.483      /api/alert/analyze  reasoning_generation                ok    
154.512      /api/alert/analyze  decision_node_and_edge_write        ok    
81.794       /api/alert/analyze  audit_write                         ok    
0.241        /api/alert/analyze  metadata_logging_snapshot_write     ok    
84.235       /api/alert/analyze  campaign_query_fetch_recent_events  ok    
87.919       /api/alert/analyze  campaign_correlation_summary        ok    
90.308       /api/alert/analyze  campaign_correlation                ok    
0.088        /api/alert/analyze  decision_event_emit                 ok    
102.211      /api/alert/analyze  composite_gate_evaluation           ok    
0.201        /api/alert/analyze  provenance_build                    ok    
89.922       /api/alert/analyze  graph_visualization_fetch           ok    
0.076        /api/alert/analyze  response_context_enrichment         ok    
0.073        /api/alert/analyze  referral_debug_build                ok    
0.035        /api/alert/analyze  shadow_compare_schedule             ok    
114.576      /api/alert/analyze  cluster_history_fetch               ok    
0.105        /api/alert/analyze  narrative_context_build             ok    
0.122        /api/alert/analyze  narrative_generation                ok    
10.803       /api/alert/analyze  response_serialization              ok    
2152.684     /api/alert/analyze  analyze_request_total               ok    
0.017        /api/alert/outcome  request_parse                       ok    
0.022        /api/alert/outcome  duplicate_feedback_guard            ok    
105.353      /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.652        /api/alert/outcome  outcome_audit_write                 ok    
157.955      /api/alert/outcome  learning_state_update               ok    
545.276      /api/alert/outcome  l5_conservation_write               ok    
547.139      /api/alert/outcome  conservation_monitor                ok    
0.35         /api/alert/outcome  profile_scorer_update               ok    
0.281        /api/alert/outcome  l5_dk_weight_write                  ok    
545.889      /api/alert/outcome  l5_centroid_write                   ok    
0.05         /api/alert/outcome  l5_dk_weight_write                  ok    
12.843       /api/alert/outcome  snapshot_evolution_logging          ok    
125.942      /api/alert/outcome  snapshot_evolution_logging          ok    
0.048        /api/alert/outcome  response_serialization              ok    
2030.763     /api/alert/outcome  outcome_request_total               ok    
```

### CAMPAIGNPHASE1-0022
- event_count: 47
- total_observed_ms: 7456.947
- authoritative_total_ms: 2122.401
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.03         /api/alert/analyze  scorer_readiness                    ok    
0.019        /api/alert/analyze  request_parse                       ok    
88.645       /api/alert/analyze  alert_lookup                        ok    
87.689       /api/alert/analyze  security_context_lookup             ok    
0.233        /api/alert/analyze  category_resolution                 ok    
402.977      /api/alert/analyze  factor_vector_construction          ok    
0.319        /api/alert/analyze  scorer_decision                     ok    
0.044        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.023        /api/alert/analyze  routing_threshold_lookup            ok    
0.036        /api/alert/analyze  rl_exploration_proposal             ok    
0.041        /api/alert/analyze  routing_zone_resolution             ok    
199.656      /api/alert/analyze  referral_history_counts             ok    
0.069        /api/alert/analyze  referral_gate_evaluation            ok    
69.193       /api/alert/analyze  reasoning_generation                ok    
103.599      /api/alert/analyze  decision_node_and_edge_write        ok    
100.451      /api/alert/analyze  audit_write                         ok    
0.465        /api/alert/analyze  metadata_logging_snapshot_write     ok    
101.063      /api/alert/analyze  campaign_query_fetch_recent_events  ok    
105.514      /api/alert/analyze  campaign_correlation_summary        ok    
108.187      /api/alert/analyze  campaign_correlation                ok    
0.055        /api/alert/analyze  decision_event_emit                 ok    
92.782       /api/alert/analyze  composite_gate_evaluation           ok    
0.123        /api/alert/analyze  provenance_build                    ok    
95.174       /api/alert/analyze  graph_visualization_fetch           ok    
0.064        /api/alert/analyze  response_context_enrichment         ok    
0.077        /api/alert/analyze  referral_debug_build                ok    
0.044        /api/alert/analyze  shadow_compare_schedule             ok    
102.422      /api/alert/analyze  cluster_history_fetch               ok    
0.07         /api/alert/analyze  narrative_context_build             ok    
0.125        /api/alert/analyze  narrative_generation                ok    
12.572       /api/alert/analyze  response_serialization              ok    
1544.827     /api/alert/analyze  analyze_request_total               ok    
0.019        /api/alert/outcome  request_parse                       ok    
0.026        /api/alert/outcome  duplicate_feedback_guard            ok    
114.183      /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.524        /api/alert/outcome  outcome_audit_write                 ok    
159.062      /api/alert/outcome  learning_state_update               ok    
539.235      /api/alert/outcome  l5_conservation_write               ok    
542.259      /api/alert/outcome  conservation_monitor                ok    
0.551        /api/alert/outcome  profile_scorer_update               ok    
0.46         /api/alert/outcome  l5_dk_weight_write                  ok    
537.604      /api/alert/outcome  l5_centroid_write                   ok    
0.041        /api/alert/outcome  l5_dk_weight_write                  ok    
120.773      /api/alert/outcome  snapshot_evolution_logging          ok    
103.161      /api/alert/outcome  snapshot_evolution_logging          ok    
0.06         /api/alert/outcome  response_serialization              ok    
2122.401     /api/alert/outcome  outcome_request_total               ok    
```

### CAMPAIGNPHASE1-0011
- event_count: 47
- total_observed_ms: 7519.855
- authoritative_total_ms: 2068.686
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.033        /api/alert/analyze  scorer_readiness                    ok    
0.02         /api/alert/analyze  request_parse                       ok    
97.439       /api/alert/analyze  alert_lookup                        ok    
130.835      /api/alert/analyze  security_context_lookup             ok    
0.244        /api/alert/analyze  category_resolution                 ok    
393.291      /api/alert/analyze  factor_vector_construction          ok    
0.951        /api/alert/analyze  scorer_decision                     ok    
0.03         /api/alert/analyze  post_scorer_confidence_gate         ok    
0.014        /api/alert/analyze  routing_threshold_lookup            ok    
0.023        /api/alert/analyze  rl_exploration_proposal             ok    
0.043        /api/alert/analyze  routing_zone_resolution             ok    
198.913      /api/alert/analyze  referral_history_counts             ok    
0.07         /api/alert/analyze  referral_gate_evaluation            ok    
69.106       /api/alert/analyze  reasoning_generation                ok    
108.673      /api/alert/analyze  decision_node_and_edge_write        ok    
130.62       /api/alert/analyze  audit_write                         ok    
0.735        /api/alert/analyze  metadata_logging_snapshot_write     ok    
106.87       /api/alert/analyze  campaign_query_fetch_recent_events  ok    
110.431      /api/alert/analyze  campaign_correlation_summary        ok    
113.982      /api/alert/analyze  campaign_correlation                ok    
0.065        /api/alert/analyze  decision_event_emit                 ok    
95.982       /api/alert/analyze  composite_gate_evaluation           ok    
0.109        /api/alert/analyze  provenance_build                    ok    
101.818      /api/alert/analyze  graph_visualization_fetch           ok    
0.056        /api/alert/analyze  response_context_enrichment         ok    
0.062        /api/alert/analyze  referral_debug_build                ok    
0.025        /api/alert/analyze  shadow_compare_schedule             ok    
95.469       /api/alert/analyze  cluster_history_fetch               ok    
0.083        /api/alert/analyze  narrative_context_build             ok    
0.104        /api/alert/analyze  narrative_generation                ok    
4.5          /api/alert/analyze  response_serialization              ok    
1621.751     /api/alert/analyze  analyze_request_total               ok    
0.021        /api/alert/outcome  request_parse                       ok    
0.021        /api/alert/outcome  duplicate_feedback_guard            ok    
129.777      /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.475        /api/alert/outcome  outcome_audit_write                 ok    
150.786      /api/alert/outcome  learning_state_update               ok    
534.285      /api/alert/outcome  l5_conservation_write               ok    
536.357      /api/alert/outcome  conservation_monitor                ok    
0.352        /api/alert/outcome  profile_scorer_update               ok    
0.278        /api/alert/outcome  l5_dk_weight_write                  ok    
608.069      /api/alert/outcome  l5_centroid_write                   ok    
0.04         /api/alert/outcome  l5_dk_weight_write                  ok    
0.052        /api/alert/outcome  snapshot_evolution_logging          ok    
108.252      /api/alert/outcome  snapshot_evolution_logging          ok    
0.057        /api/alert/outcome  response_serialization              ok    
2068.686     /api/alert/outcome  outcome_request_total               ok    
```

### CAMPAIGNPHASE1-0005
- event_count: 47
- total_observed_ms: 6826.642
- authoritative_total_ms: 2037.177
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.039        /api/alert/analyze  scorer_readiness                    ok    
0.026        /api/alert/analyze  request_parse                       ok    
96.155       /api/alert/analyze  alert_lookup                        ok    
107.418      /api/alert/analyze  security_context_lookup             ok    
0.227        /api/alert/analyze  category_resolution                 ok    
316.663      /api/alert/analyze  factor_vector_construction          ok    
0.189        /api/alert/analyze  scorer_decision                     ok    
0.018        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.018        /api/alert/analyze  routing_threshold_lookup            ok    
0.014        /api/alert/analyze  rl_exploration_proposal             ok    
0.016        /api/alert/analyze  routing_zone_resolution             ok    
184.234      /api/alert/analyze  referral_history_counts             ok    
0.09         /api/alert/analyze  referral_gate_evaluation            ok    
95.928       /api/alert/analyze  reasoning_generation                ok    
87.057       /api/alert/analyze  decision_node_and_edge_write        ok    
88.247       /api/alert/analyze  audit_write                         ok    
0.279        /api/alert/analyze  metadata_logging_snapshot_write     ok    
92.5         /api/alert/analyze  campaign_query_fetch_recent_events  ok    
96.373       /api/alert/analyze  campaign_correlation_summary        ok    
97.916       /api/alert/analyze  campaign_correlation                ok    
0.03         /api/alert/analyze  decision_event_emit                 ok    
74.54        /api/alert/analyze  composite_gate_evaluation           ok    
0.142        /api/alert/analyze  provenance_build                    ok    
88.846       /api/alert/analyze  graph_visualization_fetch           ok    
0.025        /api/alert/analyze  response_context_enrichment         ok    
0.026        /api/alert/analyze  referral_debug_build                ok    
0.012        /api/alert/analyze  shadow_compare_schedule             ok    
72.124       /api/alert/analyze  cluster_history_fetch               ok    
0.032        /api/alert/analyze  narrative_context_build             ok    
0.126        /api/alert/analyze  narrative_generation                ok    
4.977        /api/alert/analyze  response_serialization              ok    
1370.856     /api/alert/analyze  analyze_request_total               ok    
0.009        /api/alert/outcome  request_parse                       ok    
0.024        /api/alert/outcome  duplicate_feedback_guard            ok    
104.974      /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.412        /api/alert/outcome  outcome_audit_write                 ok    
409.264      /api/alert/outcome  learning_state_update               ok    
420.266      /api/alert/outcome  l5_conservation_write               ok    
422.325      /api/alert/outcome  conservation_monitor                ok    
0.26         /api/alert/outcome  profile_scorer_update               ok    
0.299        /api/alert/outcome  l5_dk_weight_write                  ok    
485.807      /api/alert/outcome  l5_centroid_write                   ok    
0.049        /api/alert/outcome  l5_dk_weight_write                  ok    
0.042        /api/alert/outcome  snapshot_evolution_logging          ok    
70.568       /api/alert/outcome  snapshot_evolution_logging          ok    
0.023        /api/alert/outcome  response_serialization              ok    
2037.177     /api/alert/outcome  outcome_request_total               ok    
```

### CAMPAIGNPHASE1-0002
- event_count: 47
- total_observed_ms: 7400.989
- authoritative_total_ms: 2014.286
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.039        /api/alert/analyze  scorer_readiness                    ok    
0.023        /api/alert/analyze  request_parse                       ok    
113.622      /api/alert/analyze  alert_lookup                        ok    
100.912      /api/alert/analyze  security_context_lookup             ok    
0.275        /api/alert/analyze  category_resolution                 ok    
409.373      /api/alert/analyze  factor_vector_construction          ok    
2.567        /api/alert/analyze  scorer_decision                     ok    
0.032        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.022        /api/alert/analyze  routing_threshold_lookup            ok    
0.029        /api/alert/analyze  rl_exploration_proposal             ok    
0.045        /api/alert/analyze  routing_zone_resolution             ok    
157.306      /api/alert/analyze  referral_history_counts             ok    
0.068        /api/alert/analyze  referral_gate_evaluation            ok    
107.148      /api/alert/analyze  reasoning_generation                ok    
113.173      /api/alert/analyze  decision_node_and_edge_write        ok    
112.174      /api/alert/analyze  audit_write                         ok    
0.406        /api/alert/analyze  metadata_logging_snapshot_write     ok    
101.758      /api/alert/analyze  campaign_query_fetch_recent_events  ok    
106.12       /api/alert/analyze  campaign_correlation_summary        ok    
109.565      /api/alert/analyze  campaign_correlation                ok    
0.062        /api/alert/analyze  decision_event_emit                 ok    
110.47       /api/alert/analyze  composite_gate_evaluation           ok    
0.489        /api/alert/analyze  provenance_build                    ok    
116.298      /api/alert/analyze  graph_visualization_fetch           ok    
0.066        /api/alert/analyze  response_context_enrichment         ok    
0.07         /api/alert/analyze  referral_debug_build                ok    
0.04         /api/alert/analyze  shadow_compare_schedule             ok    
117.419      /api/alert/analyze  cluster_history_fetch               ok    
0.064        /api/alert/analyze  narrative_context_build             ok    
0.596        /api/alert/analyze  narrative_generation                ok    
4.824        /api/alert/analyze  response_serialization              ok    
1664.268     /api/alert/analyze  analyze_request_total               ok    
0.025        /api/alert/outcome  request_parse                       ok    
0.027        /api/alert/outcome  duplicate_feedback_guard            ok    
138.461      /api/alert/outcome  decision_lookup_and_outcome_update  ok    
6.164        /api/alert/outcome  outcome_audit_write                 ok    
190.795      /api/alert/outcome  learning_state_update               ok    
479.388      /api/alert/outcome  l5_conservation_write               ok    
483.39       /api/alert/outcome  conservation_monitor                ok    
0.408        /api/alert/outcome  profile_scorer_update               ok    
0.253        /api/alert/outcome  l5_dk_weight_write                  ok    
537.225      /api/alert/outcome  l5_centroid_write                   ok    
0.05         /api/alert/outcome  l5_dk_weight_write                  ok    
0.088        /api/alert/outcome  snapshot_evolution_logging          ok    
101.047      /api/alert/outcome  snapshot_evolution_logging          ok    
0.059        /api/alert/outcome  response_serialization              ok    
2014.286     /api/alert/outcome  outcome_request_total               ok    
```

### CAMPAIGNPHASE1-0008
- event_count: 47
- total_observed_ms: 7117.842
- authoritative_total_ms: 2013.769
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.029        /api/alert/analyze  scorer_readiness                    ok    
0.017        /api/alert/analyze  request_parse                       ok    
84.358       /api/alert/analyze  alert_lookup                        ok    
101.044      /api/alert/analyze  security_context_lookup             ok    
0.234        /api/alert/analyze  category_resolution                 ok    
381.741      /api/alert/analyze  factor_vector_construction          ok    
0.412        /api/alert/analyze  scorer_decision                     ok    
0.048        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.017        /api/alert/analyze  routing_threshold_lookup            ok    
0.024        /api/alert/analyze  rl_exploration_proposal             ok    
0.037        /api/alert/analyze  routing_zone_resolution             ok    
191.017      /api/alert/analyze  referral_history_counts             ok    
0.101        /api/alert/analyze  referral_gate_evaluation            ok    
77.016       /api/alert/analyze  reasoning_generation                ok    
117.906      /api/alert/analyze  decision_node_and_edge_write        ok    
115.983      /api/alert/analyze  audit_write                         ok    
0.996        /api/alert/analyze  metadata_logging_snapshot_write     ok    
88.634       /api/alert/analyze  campaign_query_fetch_recent_events  ok    
90.955       /api/alert/analyze  campaign_correlation_summary        ok    
93.076       /api/alert/analyze  campaign_correlation                ok    
0.112        /api/alert/analyze  decision_event_emit                 ok    
87.795       /api/alert/analyze  composite_gate_evaluation           ok    
0.156        /api/alert/analyze  provenance_build                    ok    
98.112       /api/alert/analyze  graph_visualization_fetch           ok    
0.07         /api/alert/analyze  response_context_enrichment         ok    
0.058        /api/alert/analyze  referral_debug_build                ok    
0.034        /api/alert/analyze  shadow_compare_schedule             ok    
87.335       /api/alert/analyze  cluster_history_fetch               ok    
0.073        /api/alert/analyze  narrative_context_build             ok    
0.142        /api/alert/analyze  narrative_generation                ok    
5.212        /api/alert/analyze  response_serialization              ok    
1511.829     /api/alert/analyze  analyze_request_total               ok    
0.046        /api/alert/outcome  request_parse                       ok    
0.024        /api/alert/outcome  duplicate_feedback_guard            ok    
113.131      /api/alert/outcome  decision_lookup_and_outcome_update  ok    
1.262        /api/alert/outcome  outcome_audit_write                 ok    
157.695      /api/alert/outcome  learning_state_update               ok    
517.921      /api/alert/outcome  l5_conservation_write               ok    
520.947      /api/alert/outcome  conservation_monitor                ok    
0.421        /api/alert/outcome  profile_scorer_update               ok    
0.276        /api/alert/outcome  l5_dk_weight_write                  ok    
553.919      /api/alert/outcome  l5_centroid_write                   ok    
0.057        /api/alert/outcome  l5_dk_weight_write                  ok    
0.041        /api/alert/outcome  snapshot_evolution_logging          ok    
103.705      /api/alert/outcome  snapshot_evolution_logging          ok    
0.055        /api/alert/outcome  response_serialization              ok    
2013.769     /api/alert/outcome  outcome_request_total               ok    
```

### CAMPAIGNPHASE1-0024
- event_count: 47
- total_observed_ms: 7143.059
- authoritative_total_ms: 1997.319
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.031        /api/alert/analyze  scorer_readiness                    ok    
0.017        /api/alert/analyze  request_parse                       ok    
97.174       /api/alert/analyze  alert_lookup                        ok    
105.783      /api/alert/analyze  security_context_lookup             ok    
0.424        /api/alert/analyze  category_resolution                 ok    
400.753      /api/alert/analyze  factor_vector_construction          ok    
0.672        /api/alert/analyze  scorer_decision                     ok    
0.034        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.024        /api/alert/analyze  routing_threshold_lookup            ok    
0.036        /api/alert/analyze  rl_exploration_proposal             ok    
0.278        /api/alert/analyze  routing_zone_resolution             ok    
201.746      /api/alert/analyze  referral_history_counts             ok    
0.099        /api/alert/analyze  referral_gate_evaluation            ok    
91.08        /api/alert/analyze  reasoning_generation                ok    
104.373      /api/alert/analyze  decision_node_and_edge_write        ok    
97.347       /api/alert/analyze  audit_write                         ok    
0.225        /api/alert/analyze  metadata_logging_snapshot_write     ok    
81.081       /api/alert/analyze  campaign_query_fetch_recent_events  ok    
83.503       /api/alert/analyze  campaign_correlation_summary        ok    
85.318       /api/alert/analyze  campaign_correlation                ok    
0.054        /api/alert/analyze  decision_event_emit                 ok    
91.127       /api/alert/analyze  composite_gate_evaluation           ok    
0.057        /api/alert/analyze  provenance_build                    ok    
106.516      /api/alert/analyze  graph_visualization_fetch           ok    
0.069        /api/alert/analyze  response_context_enrichment         ok    
0.391        /api/alert/analyze  referral_debug_build                ok    
0.04         /api/alert/analyze  shadow_compare_schedule             ok    
91.685       /api/alert/analyze  cluster_history_fetch               ok    
0.057        /api/alert/analyze  narrative_context_build             ok    
0.109        /api/alert/analyze  narrative_generation                ok    
4.541        /api/alert/analyze  response_serialization              ok    
1560.448     /api/alert/analyze  analyze_request_total               ok    
0.02         /api/alert/outcome  request_parse                       ok    
0.019        /api/alert/outcome  duplicate_feedback_guard            ok    
95.301       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.549        /api/alert/outcome  outcome_audit_write                 ok    
197.377      /api/alert/outcome  learning_state_update               ok    
484.797      /api/alert/outcome  l5_conservation_write               ok    
487.941      /api/alert/outcome  conservation_monitor                ok    
0.31         /api/alert/outcome  profile_scorer_update               ok    
0.674        /api/alert/outcome  l5_dk_weight_write                  ok    
549.735      /api/alert/outcome  l5_centroid_write                   ok    
0.033        /api/alert/outcome  l5_dk_weight_write                  ok    
0.037        /api/alert/outcome  snapshot_evolution_logging          ok    
123.807      /api/alert/outcome  snapshot_evolution_logging          ok    
0.048        /api/alert/outcome  response_serialization              ok    
1997.319     /api/alert/outcome  outcome_request_total               ok    
```

### CAMPAIGNPHASE1-0023
- event_count: 47
- total_observed_ms: 7246.347
- authoritative_total_ms: 1993.124
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.035        /api/alert/analyze  scorer_readiness                    ok    
0.023        /api/alert/analyze  request_parse                       ok    
104.834      /api/alert/analyze  alert_lookup                        ok    
96.331       /api/alert/analyze  security_context_lookup             ok    
0.282        /api/alert/analyze  category_resolution                 ok    
419.696      /api/alert/analyze  factor_vector_construction          ok    
0.884        /api/alert/analyze  scorer_decision                     ok    
0.033        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.023        /api/alert/analyze  routing_threshold_lookup            ok    
0.039        /api/alert/analyze  rl_exploration_proposal             ok    
0.048        /api/alert/analyze  routing_zone_resolution             ok    
198.991      /api/alert/analyze  referral_history_counts             ok    
0.066        /api/alert/analyze  referral_gate_evaluation            ok    
99.169       /api/alert/analyze  reasoning_generation                ok    
93.928       /api/alert/analyze  decision_node_and_edge_write        ok    
100.884      /api/alert/analyze  audit_write                         ok    
0.367        /api/alert/analyze  metadata_logging_snapshot_write     ok    
100.476      /api/alert/analyze  campaign_query_fetch_recent_events  ok    
103.806      /api/alert/analyze  campaign_correlation_summary        ok    
105.896      /api/alert/analyze  campaign_correlation                ok    
0.046        /api/alert/analyze  decision_event_emit                 ok    
107.628      /api/alert/analyze  composite_gate_evaluation           ok    
0.134        /api/alert/analyze  provenance_build                    ok    
91.424       /api/alert/analyze  graph_visualization_fetch           ok    
0.033        /api/alert/analyze  response_context_enrichment         ok    
0.072        /api/alert/analyze  referral_debug_build                ok    
0.032        /api/alert/analyze  shadow_compare_schedule             ok    
80.551       /api/alert/analyze  cluster_history_fetch               ok    
0.083        /api/alert/analyze  narrative_context_build             ok    
0.1          /api/alert/analyze  narrative_generation                ok    
5.047        /api/alert/analyze  response_serialization              ok    
1582.053     /api/alert/analyze  analyze_request_total               ok    
0.02         /api/alert/outcome  request_parse                       ok    
0.024        /api/alert/outcome  duplicate_feedback_guard            ok    
101.81       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.487        /api/alert/outcome  outcome_audit_write                 ok    
204.611      /api/alert/outcome  learning_state_update               ok    
507.15       /api/alert/outcome  l5_conservation_write               ok    
510.605      /api/alert/outcome  conservation_monitor                ok    
0.265        /api/alert/outcome  profile_scorer_update               ok    
0.187        /api/alert/outcome  l5_dk_weight_write                  ok    
520.451      /api/alert/outcome  l5_centroid_write                   ok    
0.036        /api/alert/outcome  l5_dk_weight_write                  ok    
0.057        /api/alert/outcome  snapshot_evolution_logging          ok    
114.44       /api/alert/outcome  snapshot_evolution_logging          ok    
0.066        /api/alert/outcome  response_serialization              ok    
1993.124     /api/alert/outcome  outcome_request_total               ok    
```

### CAMPAIGNPHASE1-0003
- event_count: 47
- total_observed_ms: 7555.254
- authoritative_total_ms: 1991.352
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.017        /api/alert/analyze  scorer_readiness                    ok    
0.053        /api/alert/analyze  request_parse                       ok    
107.845      /api/alert/analyze  alert_lookup                        ok    
107.777      /api/alert/analyze  security_context_lookup             ok    
0.325        /api/alert/analyze  category_resolution                 ok    
382.253      /api/alert/analyze  factor_vector_construction          ok    
0.274        /api/alert/analyze  scorer_decision                     ok    
0.037        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.011        /api/alert/analyze  routing_threshold_lookup            ok    
0.033        /api/alert/analyze  rl_exploration_proposal             ok    
0.02         /api/alert/analyze  routing_zone_resolution             ok    
179.361      /api/alert/analyze  referral_history_counts             ok    
0.098        /api/alert/analyze  referral_gate_evaluation            ok    
99.331       /api/alert/analyze  reasoning_generation                ok    
104.416      /api/alert/analyze  decision_node_and_edge_write        ok    
100.312      /api/alert/analyze  audit_write                         ok    
0.353        /api/alert/analyze  metadata_logging_snapshot_write     ok    
161.858      /api/alert/analyze  campaign_query_fetch_recent_events  ok    
165.599      /api/alert/analyze  campaign_correlation_summary        ok    
169.433      /api/alert/analyze  campaign_correlation                ok    
0.066        /api/alert/analyze  decision_event_emit                 ok    
104.332      /api/alert/analyze  composite_gate_evaluation           ok    
0.15         /api/alert/analyze  provenance_build                    ok    
94.508       /api/alert/analyze  graph_visualization_fetch           ok    
0.064        /api/alert/analyze  response_context_enrichment         ok    
0.082        /api/alert/analyze  referral_debug_build                ok    
0.047        /api/alert/analyze  shadow_compare_schedule             ok    
100.679      /api/alert/analyze  cluster_history_fetch               ok    
0.04         /api/alert/analyze  narrative_context_build             ok    
0.067        /api/alert/analyze  narrative_generation                ok    
11.606       /api/alert/analyze  response_serialization              ok    
1634.539     /api/alert/analyze  analyze_request_total               ok    
0.018        /api/alert/outcome  request_parse                       ok    
0.023        /api/alert/outcome  duplicate_feedback_guard            ok    
107.386      /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.545        /api/alert/outcome  outcome_audit_write                 ok    
192.396      /api/alert/outcome  learning_state_update               ok    
530.571      /api/alert/outcome  l5_conservation_write               ok    
533.359      /api/alert/outcome  conservation_monitor                ok    
0.28         /api/alert/outcome  profile_scorer_update               ok    
0.281        /api/alert/outcome  l5_dk_weight_write                  ok    
566.243      /api/alert/outcome  l5_centroid_write                   ok    
0.049        /api/alert/outcome  l5_dk_weight_write                  ok    
0.164        /api/alert/outcome  snapshot_evolution_logging          ok    
106.946      /api/alert/outcome  snapshot_evolution_logging          ok    
0.055        /api/alert/outcome  response_serialization              ok    
1991.352     /api/alert/outcome  outcome_request_total               ok    
```

### CAMPAIGNPHASE1-0007
- event_count: 47
- total_observed_ms: 7246.027
- authoritative_total_ms: 1986.631
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.032        /api/alert/analyze  scorer_readiness                    ok    
0.025        /api/alert/analyze  request_parse                       ok    
101.955      /api/alert/analyze  alert_lookup                        ok    
95.94        /api/alert/analyze  security_context_lookup             ok    
0.334        /api/alert/analyze  category_resolution                 ok    
416.55       /api/alert/analyze  factor_vector_construction          ok    
0.39         /api/alert/analyze  scorer_decision                     ok    
0.035        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.021        /api/alert/analyze  routing_threshold_lookup            ok    
0.021        /api/alert/analyze  rl_exploration_proposal             ok    
0.036        /api/alert/analyze  routing_zone_resolution             ok    
195.673      /api/alert/analyze  referral_history_counts             ok    
0.108        /api/alert/analyze  referral_gate_evaluation            ok    
68.817       /api/alert/analyze  reasoning_generation                ok    
104.284      /api/alert/analyze  decision_node_and_edge_write        ok    
159.16       /api/alert/analyze  audit_write                         ok    
1.76         /api/alert/analyze  metadata_logging_snapshot_write     ok    
104.905      /api/alert/analyze  campaign_query_fetch_recent_events  ok    
108.082      /api/alert/analyze  campaign_correlation_summary        ok    
110.019      /api/alert/analyze  campaign_correlation                ok    
0.037        /api/alert/analyze  decision_event_emit                 ok    
100.14       /api/alert/analyze  composite_gate_evaluation           ok    
0.151        /api/alert/analyze  provenance_build                    ok    
89.647       /api/alert/analyze  graph_visualization_fetch           ok    
0.081        /api/alert/analyze  response_context_enrichment         ok    
0.053        /api/alert/analyze  referral_debug_build                ok    
0.055        /api/alert/analyze  shadow_compare_schedule             ok    
104.839      /api/alert/analyze  cluster_history_fetch               ok    
0.063        /api/alert/analyze  narrative_context_build             ok    
0.118        /api/alert/analyze  narrative_generation                ok    
6.667        /api/alert/analyze  response_serialization              ok    
1626.266     /api/alert/analyze  analyze_request_total               ok    
0.023        /api/alert/outcome  request_parse                       ok    
0.026        /api/alert/outcome  duplicate_feedback_guard            ok    
99.889       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.603        /api/alert/outcome  outcome_audit_write                 ok    
172.682      /api/alert/outcome  learning_state_update               ok    
462.971      /api/alert/outcome  l5_conservation_write               ok    
465.771      /api/alert/outcome  conservation_monitor                ok    
0.323        /api/alert/outcome  profile_scorer_update               ok    
0.266        /api/alert/outcome  l5_dk_weight_write                  ok    
555.931      /api/alert/outcome  l5_centroid_write                   ok    
0.046        /api/alert/outcome  l5_dk_weight_write                  ok    
0.036        /api/alert/outcome  snapshot_evolution_logging          ok    
104.516      /api/alert/outcome  snapshot_evolution_logging          ok    
0.049        /api/alert/outcome  response_serialization              ok    
1986.631     /api/alert/outcome  outcome_request_total               ok    
```

### CAMPAIGNPHASE1-0014
- event_count: 47
- total_observed_ms: 7030.531
- authoritative_total_ms: 1982.999
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.041        /api/alert/analyze  scorer_readiness                    ok    
0.019        /api/alert/analyze  request_parse                       ok    
94.066       /api/alert/analyze  alert_lookup                        ok    
98.834       /api/alert/analyze  security_context_lookup             ok    
0.218        /api/alert/analyze  category_resolution                 ok    
372.208      /api/alert/analyze  factor_vector_construction          ok    
0.493        /api/alert/analyze  scorer_decision                     ok    
0.046        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.023        /api/alert/analyze  routing_threshold_lookup            ok    
0.034        /api/alert/analyze  rl_exploration_proposal             ok    
0.038        /api/alert/analyze  routing_zone_resolution             ok    
195.463      /api/alert/analyze  referral_history_counts             ok    
0.07         /api/alert/analyze  referral_gate_evaluation            ok    
73.089       /api/alert/analyze  reasoning_generation                ok    
103.98       /api/alert/analyze  decision_node_and_edge_write        ok    
86.613       /api/alert/analyze  audit_write                         ok    
0.282        /api/alert/analyze  metadata_logging_snapshot_write     ok    
97.477       /api/alert/analyze  campaign_query_fetch_recent_events  ok    
100.446      /api/alert/analyze  campaign_correlation_summary        ok    
103.194      /api/alert/analyze  campaign_correlation                ok    
0.06         /api/alert/analyze  decision_event_emit                 ok    
89.096       /api/alert/analyze  composite_gate_evaluation           ok    
0.123        /api/alert/analyze  provenance_build                    ok    
93.529       /api/alert/analyze  graph_visualization_fetch           ok    
0.073        /api/alert/analyze  response_context_enrichment         ok    
0.048        /api/alert/analyze  referral_debug_build                ok    
0.036        /api/alert/analyze  shadow_compare_schedule             ok    
91.178       /api/alert/analyze  cluster_history_fetch               ok    
0.07         /api/alert/analyze  narrative_context_build             ok    
0.072        /api/alert/analyze  narrative_generation                ok    
5.172        /api/alert/analyze  response_serialization              ok    
1478.549     /api/alert/analyze  analyze_request_total               ok    
0.026        /api/alert/outcome  request_parse                       ok    
0.024        /api/alert/outcome  duplicate_feedback_guard            ok    
91.846       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.587        /api/alert/outcome  outcome_audit_write                 ok    
154.446      /api/alert/outcome  learning_state_update               ok    
524.348      /api/alert/outcome  l5_conservation_write               ok    
526.873      /api/alert/outcome  conservation_monitor                ok    
0.35         /api/alert/outcome  profile_scorer_update               ok    
0.226        /api/alert/outcome  l5_dk_weight_write                  ok    
532.455      /api/alert/outcome  l5_centroid_write                   ok    
0.025        /api/alert/outcome  l5_dk_weight_write                  ok    
0.039        /api/alert/outcome  snapshot_evolution_logging          ok    
131.587      /api/alert/outcome  snapshot_evolution_logging          ok    
0.06         /api/alert/outcome  response_serialization              ok    
1982.999     /api/alert/outcome  outcome_request_total               ok    
```

### CAMPAIGNPHASE1-0013
- event_count: 47
- total_observed_ms: 7149.26
- authoritative_total_ms: 1972.953
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.033        /api/alert/analyze  scorer_readiness                    ok    
0.02         /api/alert/analyze  request_parse                       ok    
98.271       /api/alert/analyze  alert_lookup                        ok    
107.163      /api/alert/analyze  security_context_lookup             ok    
0.227        /api/alert/analyze  category_resolution                 ok    
382.64       /api/alert/analyze  factor_vector_construction          ok    
0.422        /api/alert/analyze  scorer_decision                     ok    
0.044        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.027        /api/alert/analyze  routing_threshold_lookup            ok    
0.033        /api/alert/analyze  rl_exploration_proposal             ok    
0.045        /api/alert/analyze  routing_zone_resolution             ok    
189.14       /api/alert/analyze  referral_history_counts             ok    
0.074        /api/alert/analyze  referral_gate_evaluation            ok    
66.262       /api/alert/analyze  reasoning_generation                ok    
112.217      /api/alert/analyze  decision_node_and_edge_write        ok    
100.39       /api/alert/analyze  audit_write                         ok    
0.347        /api/alert/analyze  metadata_logging_snapshot_write     ok    
102.47       /api/alert/analyze  campaign_query_fetch_recent_events  ok    
106.007      /api/alert/analyze  campaign_correlation_summary        ok    
108.878      /api/alert/analyze  campaign_correlation                ok    
0.058        /api/alert/analyze  decision_event_emit                 ok    
91.542       /api/alert/analyze  composite_gate_evaluation           ok    
0.163        /api/alert/analyze  provenance_build                    ok    
98.446       /api/alert/analyze  graph_visualization_fetch           ok    
0.078        /api/alert/analyze  response_context_enrichment         ok    
0.074        /api/alert/analyze  referral_debug_build                ok    
0.196        /api/alert/analyze  shadow_compare_schedule             ok    
95.94        /api/alert/analyze  cluster_history_fetch               ok    
0.058        /api/alert/analyze  narrative_context_build             ok    
0.314        /api/alert/analyze  narrative_generation                ok    
5.649        /api/alert/analyze  response_serialization              ok    
1527.173     /api/alert/analyze  analyze_request_total               ok    
0.03         /api/alert/outcome  request_parse                       ok    
0.023        /api/alert/outcome  duplicate_feedback_guard            ok    
113.548      /api/alert/outcome  decision_lookup_and_outcome_update  ok    
2.673        /api/alert/outcome  outcome_audit_write                 ok    
169.173      /api/alert/outcome  learning_state_update               ok    
504.478      /api/alert/outcome  l5_conservation_write               ok    
507.9        /api/alert/outcome  conservation_monitor                ok    
0.39         /api/alert/outcome  profile_scorer_update               ok    
0.303        /api/alert/outcome  l5_dk_weight_write                  ok    
588.207      /api/alert/outcome  l5_centroid_write                   ok    
0.06         /api/alert/outcome  l5_dk_weight_write                  ok    
0.063        /api/alert/outcome  snapshot_evolution_logging          ok    
95.004       /api/alert/outcome  snapshot_evolution_logging          ok    
0.054        /api/alert/outcome  response_serialization              ok    
1972.953     /api/alert/outcome  outcome_request_total               ok    
```

### CAMPAIGNPHASE1-0016
- event_count: 47
- total_observed_ms: 7001.406
- authoritative_total_ms: 1950.936
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.034        /api/alert/analyze  scorer_readiness                    ok    
0.023        /api/alert/analyze  request_parse                       ok    
83.13        /api/alert/analyze  alert_lookup                        ok    
117.416      /api/alert/analyze  security_context_lookup             ok    
0.197        /api/alert/analyze  category_resolution                 ok    
399.148      /api/alert/analyze  factor_vector_construction          ok    
0.436        /api/alert/analyze  scorer_decision                     ok    
0.04         /api/alert/analyze  post_scorer_confidence_gate         ok    
0.017        /api/alert/analyze  routing_threshold_lookup            ok    
0.036        /api/alert/analyze  rl_exploration_proposal             ok    
0.034        /api/alert/analyze  routing_zone_resolution             ok    
176.418      /api/alert/analyze  referral_history_counts             ok    
0.075        /api/alert/analyze  referral_gate_evaluation            ok    
70.179       /api/alert/analyze  reasoning_generation                ok    
94.541       /api/alert/analyze  decision_node_and_edge_write        ok    
87.497       /api/alert/analyze  audit_write                         ok    
0.496        /api/alert/analyze  metadata_logging_snapshot_write     ok    
92.138       /api/alert/analyze  campaign_query_fetch_recent_events  ok    
95.512       /api/alert/analyze  campaign_correlation_summary        ok    
98.08        /api/alert/analyze  campaign_correlation                ok    
0.029        /api/alert/analyze  decision_event_emit                 ok    
81.452       /api/alert/analyze  composite_gate_evaluation           ok    
0.138        /api/alert/analyze  provenance_build                    ok    
103.034      /api/alert/analyze  graph_visualization_fetch           ok    
0.076        /api/alert/analyze  response_context_enrichment         ok    
0.23         /api/alert/analyze  referral_debug_build                ok    
0.019        /api/alert/analyze  shadow_compare_schedule             ok    
101.214      /api/alert/analyze  cluster_history_fetch               ok    
0.06         /api/alert/analyze  narrative_context_build             ok    
0.094        /api/alert/analyze  narrative_generation                ok    
5.874        /api/alert/analyze  response_serialization              ok    
1486.49      /api/alert/analyze  analyze_request_total               ok    
0.055        /api/alert/outcome  request_parse                       ok    
0.025        /api/alert/outcome  duplicate_feedback_guard            ok    
131.261      /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.591        /api/alert/outcome  outcome_audit_write                 ok    
168.601      /api/alert/outcome  learning_state_update               ok    
508.23       /api/alert/outcome  l5_conservation_write               ok    
510.531      /api/alert/outcome  conservation_monitor                ok    
0.275        /api/alert/outcome  profile_scorer_update               ok    
0.266        /api/alert/outcome  l5_dk_weight_write                  ok    
526.341      /api/alert/outcome  l5_centroid_write                   ok    
0.036        /api/alert/outcome  l5_dk_weight_write                  ok    
0.038        /api/alert/outcome  snapshot_evolution_logging          ok    
110.012      /api/alert/outcome  snapshot_evolution_logging          ok    
0.051        /api/alert/outcome  response_serialization              ok    
1950.936     /api/alert/outcome  outcome_request_total               ok    
```

### CAMPAIGNPHASE1-0017
- event_count: 47
- total_observed_ms: 7090.755
- authoritative_total_ms: 1944.121
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.044        /api/alert/analyze  scorer_readiness                    ok    
0.025        /api/alert/analyze  request_parse                       ok    
91.639       /api/alert/analyze  alert_lookup                        ok    
92.772       /api/alert/analyze  security_context_lookup             ok    
0.28         /api/alert/analyze  category_resolution                 ok    
400.398      /api/alert/analyze  factor_vector_construction          ok    
0.536        /api/alert/analyze  scorer_decision                     ok    
0.044        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.023        /api/alert/analyze  routing_threshold_lookup            ok    
0.032        /api/alert/analyze  rl_exploration_proposal             ok    
0.036        /api/alert/analyze  routing_zone_resolution             ok    
208.112      /api/alert/analyze  referral_history_counts             ok    
0.267        /api/alert/analyze  referral_gate_evaluation            ok    
72.59        /api/alert/analyze  reasoning_generation                ok    
102.23       /api/alert/analyze  decision_node_and_edge_write        ok    
92.596       /api/alert/analyze  audit_write                         ok    
0.527        /api/alert/analyze  metadata_logging_snapshot_write     ok    
111.551      /api/alert/analyze  campaign_query_fetch_recent_events  ok    
114.589      /api/alert/analyze  campaign_correlation_summary        ok    
116.242      /api/alert/analyze  campaign_correlation                ok    
0.05         /api/alert/analyze  decision_event_emit                 ok    
84.293       /api/alert/analyze  composite_gate_evaluation           ok    
0.114        /api/alert/analyze  provenance_build                    ok    
106.103      /api/alert/analyze  graph_visualization_fetch           ok    
0.053        /api/alert/analyze  response_context_enrichment         ok    
0.051        /api/alert/analyze  referral_debug_build                ok    
0.031        /api/alert/analyze  shadow_compare_schedule             ok    
91.199       /api/alert/analyze  cluster_history_fetch               ok    
0.08         /api/alert/analyze  narrative_context_build             ok    
0.106        /api/alert/analyze  narrative_generation                ok    
9.625        /api/alert/analyze  response_serialization              ok    
1541.012     /api/alert/analyze  analyze_request_total               ok    
0.036        /api/alert/outcome  request_parse                       ok    
0.035        /api/alert/outcome  duplicate_feedback_guard            ok    
113.06       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.872        /api/alert/outcome  outcome_audit_write                 ok    
186.23       /api/alert/outcome  learning_state_update               ok    
491.642      /api/alert/outcome  l5_conservation_write               ok    
494.79       /api/alert/outcome  conservation_monitor                ok    
0.39         /api/alert/outcome  profile_scorer_update               ok    
0.333        /api/alert/outcome  l5_dk_weight_write                  ok    
530.952      /api/alert/outcome  l5_centroid_write                   ok    
0.044        /api/alert/outcome  l5_dk_weight_write                  ok    
0.056        /api/alert/outcome  snapshot_evolution_logging          ok    
90.852       /api/alert/outcome  snapshot_evolution_logging          ok    
0.092        /api/alert/outcome  response_serialization              ok    
1944.121     /api/alert/outcome  outcome_request_total               ok    
```

### CAMPAIGNPHASE1-0010
- event_count: 47
- total_observed_ms: 7053.952
- authoritative_total_ms: 1942.917
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.034        /api/alert/analyze  scorer_readiness                    ok    
0.026        /api/alert/analyze  request_parse                       ok    
90.842       /api/alert/analyze  alert_lookup                        ok    
114.908      /api/alert/analyze  security_context_lookup             ok    
0.523        /api/alert/analyze  category_resolution                 ok    
391.487      /api/alert/analyze  factor_vector_construction          ok    
0.345        /api/alert/analyze  scorer_decision                     ok    
0.043        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.017        /api/alert/analyze  routing_threshold_lookup            ok    
0.019        /api/alert/analyze  rl_exploration_proposal             ok    
0.042        /api/alert/analyze  routing_zone_resolution             ok    
196.735      /api/alert/analyze  referral_history_counts             ok    
0.068        /api/alert/analyze  referral_gate_evaluation            ok    
71.012       /api/alert/analyze  reasoning_generation                ok    
112.385      /api/alert/analyze  decision_node_and_edge_write        ok    
92.491       /api/alert/analyze  audit_write                         ok    
0.437        /api/alert/analyze  metadata_logging_snapshot_write     ok    
93.099       /api/alert/analyze  campaign_query_fetch_recent_events  ok    
99.075       /api/alert/analyze  campaign_correlation_summary        ok    
102.066      /api/alert/analyze  campaign_correlation                ok    
0.053        /api/alert/analyze  decision_event_emit                 ok    
93.84        /api/alert/analyze  composite_gate_evaluation           ok    
0.112        /api/alert/analyze  provenance_build                    ok    
99.035       /api/alert/analyze  graph_visualization_fetch           ok    
0.06         /api/alert/analyze  response_context_enrichment         ok    
0.057        /api/alert/analyze  referral_debug_build                ok    
0.251        /api/alert/analyze  shadow_compare_schedule             ok    
91.994       /api/alert/analyze  cluster_history_fetch               ok    
0.069        /api/alert/analyze  narrative_context_build             ok    
0.153        /api/alert/analyze  narrative_generation                ok    
4.784        /api/alert/analyze  response_serialization              ok    
1536.313     /api/alert/analyze  analyze_request_total               ok    
0.025        /api/alert/outcome  request_parse                       ok    
0.029        /api/alert/outcome  duplicate_feedback_guard            ok    
119.233      /api/alert/outcome  decision_lookup_and_outcome_update  ok    
3.585        /api/alert/outcome  outcome_audit_write                 ok    
156.019      /api/alert/outcome  learning_state_update               ok    
531.298      /api/alert/outcome  l5_conservation_write               ok    
533.905      /api/alert/outcome  conservation_monitor                ok    
0.259        /api/alert/outcome  profile_scorer_update               ok    
0.234        /api/alert/outcome  l5_dk_weight_write                  ok    
454.533      /api/alert/outcome  l5_centroid_write                   ok    
0.016        /api/alert/outcome  l5_dk_weight_write                  ok    
0.014        /api/alert/outcome  snapshot_evolution_logging          ok    
119.455      /api/alert/outcome  snapshot_evolution_logging          ok    
0.055        /api/alert/outcome  response_serialization              ok    
1942.917     /api/alert/outcome  outcome_request_total               ok    
```

### CAMPAIGNPHASE1-0009
- event_count: 47
- total_observed_ms: 7285.612
- authoritative_total_ms: 1941.453
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.035        /api/alert/analyze  scorer_readiness                    ok    
0.022        /api/alert/analyze  request_parse                       ok    
89.948       /api/alert/analyze  alert_lookup                        ok    
99.59        /api/alert/analyze  security_context_lookup             ok    
0.254        /api/alert/analyze  category_resolution                 ok    
412.906      /api/alert/analyze  factor_vector_construction          ok    
0.441        /api/alert/analyze  scorer_decision                     ok    
0.043        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.024        /api/alert/analyze  routing_threshold_lookup            ok    
0.036        /api/alert/analyze  rl_exploration_proposal             ok    
0.042        /api/alert/analyze  routing_zone_resolution             ok    
273.07       /api/alert/analyze  referral_history_counts             ok    
0.095        /api/alert/analyze  referral_gate_evaluation            ok    
73.868       /api/alert/analyze  reasoning_generation                ok    
103.03       /api/alert/analyze  decision_node_and_edge_write        ok    
103.383      /api/alert/analyze  audit_write                         ok    
0.425        /api/alert/analyze  metadata_logging_snapshot_write     ok    
94.795       /api/alert/analyze  campaign_query_fetch_recent_events  ok    
97.537       /api/alert/analyze  campaign_correlation_summary        ok    
99.511       /api/alert/analyze  campaign_correlation                ok    
0.044        /api/alert/analyze  decision_event_emit                 ok    
119.065      /api/alert/analyze  composite_gate_evaluation           ok    
0.124        /api/alert/analyze  provenance_build                    ok    
110.405      /api/alert/analyze  graph_visualization_fetch           ok    
0.082        /api/alert/analyze  response_context_enrichment         ok    
0.066        /api/alert/analyze  referral_debug_build                ok    
0.033        /api/alert/analyze  shadow_compare_schedule             ok    
89.739       /api/alert/analyze  cluster_history_fetch               ok    
0.068        /api/alert/analyze  narrative_context_build             ok    
0.11         /api/alert/analyze  narrative_generation                ok    
4.85         /api/alert/analyze  response_serialization              ok    
1653.494     /api/alert/analyze  analyze_request_total               ok    
0.018        /api/alert/outcome  request_parse                       ok    
0.018        /api/alert/outcome  duplicate_feedback_guard            ok    
115.324      /api/alert/outcome  decision_lookup_and_outcome_update  ok    
1.336        /api/alert/outcome  outcome_audit_write                 ok    
152.053      /api/alert/outcome  learning_state_update               ok    
486.842      /api/alert/outcome  l5_conservation_write               ok    
489.891      /api/alert/outcome  conservation_monitor                ok    
0.368        /api/alert/outcome  profile_scorer_update               ok    
0.398        /api/alert/outcome  l5_dk_weight_write                  ok    
560.514      /api/alert/outcome  l5_centroid_write                   ok    
0.042        /api/alert/outcome  l5_dk_weight_write                  ok    
0.074        /api/alert/outcome  snapshot_evolution_logging          ok    
110.098      /api/alert/outcome  snapshot_evolution_logging          ok    
0.048        /api/alert/outcome  response_serialization              ok    
1941.453     /api/alert/outcome  outcome_request_total               ok    
```

### CAMPAIGNPHASE1-0025
- event_count: 47
- total_observed_ms: 7141.427
- authoritative_total_ms: 1937.684
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.033        /api/alert/analyze  scorer_readiness                    ok    
0.023        /api/alert/analyze  request_parse                       ok    
92.23        /api/alert/analyze  alert_lookup                        ok    
98.54        /api/alert/analyze  security_context_lookup             ok    
0.277        /api/alert/analyze  category_resolution                 ok    
409.524      /api/alert/analyze  factor_vector_construction          ok    
0.357        /api/alert/analyze  scorer_decision                     ok    
0.047        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.025        /api/alert/analyze  routing_threshold_lookup            ok    
0.032        /api/alert/analyze  rl_exploration_proposal             ok    
0.037        /api/alert/analyze  routing_zone_resolution             ok    
190.369      /api/alert/analyze  referral_history_counts             ok    
0.063        /api/alert/analyze  referral_gate_evaluation            ok    
73.738       /api/alert/analyze  reasoning_generation                ok    
111.064      /api/alert/analyze  decision_node_and_edge_write        ok    
89.068       /api/alert/analyze  audit_write                         ok    
0.248        /api/alert/analyze  metadata_logging_snapshot_write     ok    
119.098      /api/alert/analyze  campaign_query_fetch_recent_events  ok    
122.608      /api/alert/analyze  campaign_correlation_summary        ok    
125.119      /api/alert/analyze  campaign_correlation                ok    
0.045        /api/alert/analyze  decision_event_emit                 ok    
97.95        /api/alert/analyze  composite_gate_evaluation           ok    
0.117        /api/alert/analyze  provenance_build                    ok    
91.422       /api/alert/analyze  graph_visualization_fetch           ok    
0.062        /api/alert/analyze  response_context_enrichment         ok    
0.067        /api/alert/analyze  referral_debug_build                ok    
0.035        /api/alert/analyze  shadow_compare_schedule             ok    
92.889       /api/alert/analyze  cluster_history_fetch               ok    
0.074        /api/alert/analyze  narrative_context_build             ok    
0.088        /api/alert/analyze  narrative_generation                ok    
4.203        /api/alert/analyze  response_serialization              ok    
1558.743     /api/alert/analyze  analyze_request_total               ok    
0.024        /api/alert/outcome  request_parse                       ok    
0.025        /api/alert/outcome  duplicate_feedback_guard            ok    
111.197      /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.608        /api/alert/outcome  outcome_audit_write                 ok    
155.745      /api/alert/outcome  learning_state_update               ok    
517.275      /api/alert/outcome  l5_conservation_write               ok    
520.022      /api/alert/outcome  conservation_monitor                ok    
0.369        /api/alert/outcome  profile_scorer_update               ok    
0.37         /api/alert/outcome  l5_dk_weight_write                  ok    
516.295      /api/alert/outcome  l5_centroid_write                   ok    
0.023        /api/alert/outcome  l5_dk_weight_write                  ok    
0.024        /api/alert/outcome  snapshot_evolution_logging          ok    
103.509      /api/alert/outcome  snapshot_evolution_logging          ok    
0.062        /api/alert/outcome  response_serialization              ok    
1937.684     /api/alert/outcome  outcome_request_total               ok    
```

### CAMPAIGNPHASE1-0012
- event_count: 47
- total_observed_ms: 7039.888
- authoritative_total_ms: 1937.601
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.042        /api/alert/analyze  scorer_readiness                    ok    
0.023        /api/alert/analyze  request_parse                       ok    
93.574       /api/alert/analyze  alert_lookup                        ok    
100.58       /api/alert/analyze  security_context_lookup             ok    
0.183        /api/alert/analyze  category_resolution                 ok    
376.632      /api/alert/analyze  factor_vector_construction          ok    
0.549        /api/alert/analyze  scorer_decision                     ok    
0.046        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.02         /api/alert/analyze  routing_threshold_lookup            ok    
0.189        /api/alert/analyze  rl_exploration_proposal             ok    
0.039        /api/alert/analyze  routing_zone_resolution             ok    
213.884      /api/alert/analyze  referral_history_counts             ok    
0.319        /api/alert/analyze  referral_gate_evaluation            ok    
75.077       /api/alert/analyze  reasoning_generation                ok    
104.173      /api/alert/analyze  decision_node_and_edge_write        ok    
115.985      /api/alert/analyze  audit_write                         ok    
0.304        /api/alert/analyze  metadata_logging_snapshot_write     ok    
99.123       /api/alert/analyze  campaign_query_fetch_recent_events  ok    
103.245      /api/alert/analyze  campaign_correlation_summary        ok    
106.436      /api/alert/analyze  campaign_correlation                ok    
0.059        /api/alert/analyze  decision_event_emit                 ok    
89.866       /api/alert/analyze  composite_gate_evaluation           ok    
0.364        /api/alert/analyze  provenance_build                    ok    
115.863      /api/alert/analyze  graph_visualization_fetch           ok    
0.064        /api/alert/analyze  response_context_enrichment         ok    
0.069        /api/alert/analyze  referral_debug_build                ok    
0.035        /api/alert/analyze  shadow_compare_schedule             ok    
103.216      /api/alert/analyze  cluster_history_fetch               ok    
0.056        /api/alert/analyze  narrative_context_build             ok    
0.079        /api/alert/analyze  narrative_generation                ok    
6.88         /api/alert/analyze  response_serialization              ok    
1575.758     /api/alert/analyze  analyze_request_total               ok    
0.034        /api/alert/outcome  request_parse                       ok    
0.025        /api/alert/outcome  duplicate_feedback_guard            ok    
104.024      /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.381        /api/alert/outcome  outcome_audit_write                 ok    
227.324      /api/alert/outcome  learning_state_update               ok    
410.612      /api/alert/outcome  l5_conservation_write               ok    
412.379      /api/alert/outcome  conservation_monitor                ok    
0.257        /api/alert/outcome  profile_scorer_update               ok    
0.127        /api/alert/outcome  l5_dk_weight_write                  ok    
494.377      /api/alert/outcome  l5_centroid_write                   ok    
0.038        /api/alert/outcome  l5_dk_weight_write                  ok    
0.206        /api/alert/outcome  snapshot_evolution_logging          ok    
169.715      /api/alert/outcome  snapshot_evolution_logging          ok    
0.056        /api/alert/outcome  response_serialization              ok    
1937.601     /api/alert/outcome  outcome_request_total               ok    
```

### CAMPAIGNPHASE1-0018
- event_count: 47
- total_observed_ms: 7096.696
- authoritative_total_ms: 1917.249
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.044        /api/alert/analyze  scorer_readiness                    ok    
0.022        /api/alert/analyze  request_parse                       ok    
106.737      /api/alert/analyze  alert_lookup                        ok    
96.59        /api/alert/analyze  security_context_lookup             ok    
0.47         /api/alert/analyze  category_resolution                 ok    
405.949      /api/alert/analyze  factor_vector_construction          ok    
0.284        /api/alert/analyze  scorer_decision                     ok    
0.037        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.028        /api/alert/analyze  routing_threshold_lookup            ok    
0.032        /api/alert/analyze  rl_exploration_proposal             ok    
0.039        /api/alert/analyze  routing_zone_resolution             ok    
186.946      /api/alert/analyze  referral_history_counts             ok    
0.086        /api/alert/analyze  referral_gate_evaluation            ok    
69.192       /api/alert/analyze  reasoning_generation                ok    
111.846      /api/alert/analyze  decision_node_and_edge_write        ok    
111.251      /api/alert/analyze  audit_write                         ok    
0.374        /api/alert/analyze  metadata_logging_snapshot_write     ok    
100.269      /api/alert/analyze  campaign_query_fetch_recent_events  ok    
103.877      /api/alert/analyze  campaign_correlation_summary        ok    
106.191      /api/alert/analyze  campaign_correlation                ok    
0.051        /api/alert/analyze  decision_event_emit                 ok    
92.467       /api/alert/analyze  composite_gate_evaluation           ok    
0.101        /api/alert/analyze  provenance_build                    ok    
101.289      /api/alert/analyze  graph_visualization_fetch           ok    
0.067        /api/alert/analyze  response_context_enrichment         ok    
0.084        /api/alert/analyze  referral_debug_build                ok    
0.037        /api/alert/analyze  shadow_compare_schedule             ok    
97.806       /api/alert/analyze  cluster_history_fetch               ok    
0.085        /api/alert/analyze  narrative_context_build             ok    
0.107        /api/alert/analyze  narrative_generation                ok    
6.631        /api/alert/analyze  response_serialization              ok    
1562.551     /api/alert/analyze  analyze_request_total               ok    
0.023        /api/alert/outcome  request_parse                       ok    
0.024        /api/alert/outcome  duplicate_feedback_guard            ok    
105.35       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.508        /api/alert/outcome  outcome_audit_write                 ok    
159.666      /api/alert/outcome  learning_state_update               ok    
505.166      /api/alert/outcome  l5_conservation_write               ok    
508.028      /api/alert/outcome  conservation_monitor                ok    
0.388        /api/alert/outcome  profile_scorer_update               ok    
0.355        /api/alert/outcome  l5_dk_weight_write                  ok    
531.722      /api/alert/outcome  l5_centroid_write                   ok    
0.038        /api/alert/outcome  l5_dk_weight_write                  ok    
0.046        /api/alert/outcome  snapshot_evolution_logging          ok    
106.42       /api/alert/outcome  snapshot_evolution_logging          ok    
0.173        /api/alert/outcome  response_serialization              ok    
1917.249     /api/alert/outcome  outcome_request_total               ok    
```

### CAMPAIGNPHASE1-0019
- event_count: 47
- total_observed_ms: 6958.539
- authoritative_total_ms: 1914.297
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.046        /api/alert/analyze  scorer_readiness                    ok    
0.02         /api/alert/analyze  request_parse                       ok    
87.917       /api/alert/analyze  alert_lookup                        ok    
94.663       /api/alert/analyze  security_context_lookup             ok    
0.217        /api/alert/analyze  category_resolution                 ok    
370.482      /api/alert/analyze  factor_vector_construction          ok    
0.276        /api/alert/analyze  scorer_decision                     ok    
0.045        /api/alert/analyze  post_scorer_confidence_gate         ok    
0.01         /api/alert/analyze  routing_threshold_lookup            ok    
0.033        /api/alert/analyze  rl_exploration_proposal             ok    
0.023        /api/alert/analyze  routing_zone_resolution             ok    
195.362      /api/alert/analyze  referral_history_counts             ok    
0.082        /api/alert/analyze  referral_gate_evaluation            ok    
71.234       /api/alert/analyze  reasoning_generation                ok    
90.05        /api/alert/analyze  decision_node_and_edge_write        ok    
108.816      /api/alert/analyze  audit_write                         ok    
0.282        /api/alert/analyze  metadata_logging_snapshot_write     ok    
111.855      /api/alert/analyze  campaign_query_fetch_recent_events  ok    
115.02       /api/alert/analyze  campaign_correlation_summary        ok    
118.27       /api/alert/analyze  campaign_correlation                ok    
0.056        /api/alert/analyze  decision_event_emit                 ok    
92.213       /api/alert/analyze  composite_gate_evaluation           ok    
0.148        /api/alert/analyze  provenance_build                    ok    
98.891       /api/alert/analyze  graph_visualization_fetch           ok    
0.067        /api/alert/analyze  response_context_enrichment         ok    
0.065        /api/alert/analyze  referral_debug_build                ok    
0.037        /api/alert/analyze  shadow_compare_schedule             ok    
85.051       /api/alert/analyze  cluster_history_fetch               ok    
0.052        /api/alert/analyze  narrative_context_build             ok    
0.114        /api/alert/analyze  narrative_generation                ok    
4.682        /api/alert/analyze  response_serialization              ok    
1488.967     /api/alert/analyze  analyze_request_total               ok    
0.02         /api/alert/outcome  request_parse                       ok    
0.024        /api/alert/outcome  duplicate_feedback_guard            ok    
117.214      /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.468        /api/alert/outcome  outcome_audit_write                 ok    
165.395      /api/alert/outcome  learning_state_update               ok    
496.076      /api/alert/outcome  l5_conservation_write               ok    
499.094      /api/alert/outcome  conservation_monitor                ok    
0.274        /api/alert/outcome  profile_scorer_update               ok    
0.188        /api/alert/outcome  l5_dk_weight_write                  ok    
522.25       /api/alert/outcome  l5_centroid_write                   ok    
0.04         /api/alert/outcome  l5_dk_weight_write                  ok    
0.08         /api/alert/outcome  snapshot_evolution_logging          ok    
108.021      /api/alert/outcome  snapshot_evolution_logging          ok    
0.052        /api/alert/outcome  response_serialization              ok    
1914.297     /api/alert/outcome  outcome_request_total               ok    
```

## Nested Phase Warning
Nested phase durations should not be summed blindly. Use analyze_request_total, outcome_request_total, or total_attempt as authoritative totals.
