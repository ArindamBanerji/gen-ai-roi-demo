# SOC Perf Trace Summary

## Safety
- Read-only summary of existing JSONL trace events.
- No backend, graph, proof, or seed operations are performed.
- Nested phases are not additive; request-total phases are the authoritative route totals.

## Input
- trace_jsonl: `C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50\scratch\temp\soc_perf_trace_phase_c_25.jsonl`
- events_loaded: 675
- malformed_lines: 0
- route_filter: None
- phase_filter: None

## Route + Phase Aggregates
```text
route_phase                                              count  avg_ms    p50_ms    p95_ms    p99_ms    max_ms  
-------------------------------------------------------  -----  --------  --------  --------  --------  --------
/api/alert/analyze | analyze_request_total               25     3687.638  3704.297  5543.729  5672.553  5692.343
/api/alert/outcome | outcome_request_total               25     1489.34   1475.938  1682.75   1720.917  1729.069
/api/alert/outcome | l5_centroid_write                   25     425.376   430.059   488.801   543.171   557.291 
/api/alert/outcome | conservation_monitor                25     409.034   416.141   444.825   450.071   451.493 
/api/alert/outcome | l5_conservation_write               25     407.092   415.32    443.041   447.002   448.043 
/api/alert/analyze | factor_vector_construction          25     327.58    325.379   369.218   377.124   378.097 
/api/alert/outcome | learning_state_update               25     75.924    61.449    135.703   188.412   204.639 
/api/alert/analyze | decision_node_and_edge_write        25     86.494    85.661    101.105   133.244   142.779 
/api/alert/outcome | decision_lookup_and_outcome_update  25     84.302    80.889    96.959    101.574   102.933 
/api/alert/analyze | audit_write                         25     81.347    80.713    97.7      100.981   101.935 
/api/alert/analyze | alert_lookup                        25     79.18     80.115    97.757    100.409   100.976 
/api/alert/outcome | snapshot_evolution_logging          50     40.002    64.923    89.433    95.024    96.386  
/api/alert/analyze | security_context_lookup             25     83.205    82.756    93.737    95.793    96.367  
/api/alert/analyze | scorer_decision                     25     0.564     0.205     0.422     6.676     8.646   
/api/alert/analyze | category_resolution                 25     0.264     0.123     0.255     2.656     3.411   
/api/alert/analyze | metadata_logging_snapshot_write     25     0.749     0.374     2.996     3.319     3.401   
/api/alert/analyze | response_serialization              25     0.234     0.154     0.519     1.357     1.609   
/api/alert/outcome | outcome_audit_write                 25     0.536     0.414     1.198     1.451     1.523   
/api/alert/outcome | profile_scorer_update               25     0.167     0.153     0.283     0.414     0.454   
/api/alert/outcome | l5_dk_weight_write                  50     0.081     0.052     0.234     0.365     0.435   
/api/alert/analyze | scorer_readiness                    25     0.037     0.027     0.043     0.287     0.364   
/api/alert/outcome | response_serialization              25     0.032     0.029     0.05      0.068     0.073   
/api/alert/outcome | request_parse                       25     0.017     0.014     0.042     0.063     0.069   
/api/alert/outcome | duplicate_feedback_guard            25     0.014     0.012     0.021     0.044     0.051   
/api/alert/analyze | request_parse                       25     0.013     0.013     0.022     0.023     0.023   
```

## Phase Aggregates
```text
phase                               count  avg_ms    p50_ms    p95_ms    p99_ms    max_ms  
----------------------------------  -----  --------  --------  --------  --------  --------
analyze_request_total               25     3687.638  3704.297  5543.729  5672.553  5692.343
outcome_request_total               25     1489.34   1475.938  1682.75   1720.917  1729.069
l5_centroid_write                   25     425.376   430.059   488.801   543.171   557.291 
conservation_monitor                25     409.034   416.141   444.825   450.071   451.493 
l5_conservation_write               25     407.092   415.32    443.041   447.002   448.043 
factor_vector_construction          25     327.58    325.379   369.218   377.124   378.097 
learning_state_update               25     75.924    61.449    135.703   188.412   204.639 
decision_node_and_edge_write        25     86.494    85.661    101.105   133.244   142.779 
decision_lookup_and_outcome_update  25     84.302    80.889    96.959    101.574   102.933 
audit_write                         25     81.347    80.713    97.7      100.981   101.935 
alert_lookup                        25     79.18     80.115    97.757    100.409   100.976 
snapshot_evolution_logging          50     40.002    64.923    89.433    95.024    96.386  
security_context_lookup             25     83.205    82.756    93.737    95.793    96.367  
scorer_decision                     25     0.564     0.205     0.422     6.676     8.646   
category_resolution                 25     0.264     0.123     0.255     2.656     3.411   
metadata_logging_snapshot_write     25     0.749     0.374     2.996     3.319     3.401   
response_serialization              50     0.133     0.076     0.328     1.094     1.609   
outcome_audit_write                 25     0.536     0.414     1.198     1.451     1.523   
profile_scorer_update               25     0.167     0.153     0.283     0.414     0.454   
l5_dk_weight_write                  50     0.081     0.052     0.234     0.365     0.435   
scorer_readiness                    25     0.037     0.027     0.043     0.287     0.364   
request_parse                       50     0.015     0.014     0.024     0.058     0.069   
duplicate_feedback_guard            25     0.014     0.012     0.021     0.044     0.051   
```

## Graph Aggregates
```text
graph_name             count  avg_ms   p50_ms  p95_ms    p99_ms    max_ms  
---------------------  -----  -------  ------  --------  --------  --------
soc_graph_phasec_25_1  675    271.085  1.106   1514.687  4538.398  5692.343
```

## Top Slow Events
```text
duration_ms  route               phase                  alert_id       decision_id                           attempt_index  status
-----------  ------------------  ---------------------  -------------  ------------------------------------  -------------  ------
5692.343     /api/alert/analyze  analyze_request_total  PHASEC25-0025  57bb3716-4c44-4f33-a622-7759d7e6eaea  None           ok    
5609.883     /api/alert/analyze  analyze_request_total  PHASEC25-0024  b6efeb11-e8ae-4323-b4f5-d66b37c160f8  None           ok    
5279.115     /api/alert/analyze  analyze_request_total  PHASEC25-0023  f0e9166b-ec34-4619-b530-851cfb1cd42d  None           ok    
5189.614     /api/alert/analyze  analyze_request_total  PHASEC25-0022  54843b46-48a5-4a3d-b81c-405174aa085e  None           ok    
5097.088     /api/alert/analyze  analyze_request_total  PHASEC25-0021  b5971dde-ad09-4d78-94d6-f5dd81afe1bc  None           ok    
4814.853     /api/alert/analyze  analyze_request_total  PHASEC25-0020  ff0036ab-e779-4c07-98fc-de7bb9abb6d6  None           ok    
4638.823     /api/alert/analyze  analyze_request_total  PHASEC25-0018  167edc5e-e439-4106-90a3-ffc61560b46c  None           ok    
4503.113     /api/alert/analyze  analyze_request_total  PHASEC25-0019  18b30b05-0c2d-4289-9a01-28c128cf58aa  None           ok    
4239.696     /api/alert/analyze  analyze_request_total  PHASEC25-0017  607781d2-2f20-483b-8311-192258237fd4  None           ok    
4182.408     /api/alert/analyze  analyze_request_total  PHASEC25-0016  bb91a51e-ef70-478d-8ccc-9f05b1a9b533  None           ok    
3901.007     /api/alert/analyze  analyze_request_total  PHASEC25-0014  8e3d50ac-373a-4687-9a58-816b7ce975e4  None           ok    
3843.819     /api/alert/analyze  analyze_request_total  PHASEC25-0015  6ac0caf4-81c5-4c72-a9dd-d054f9f3d08f  None           ok    
3704.297     /api/alert/analyze  analyze_request_total  PHASEC25-0012  15c39c23-e037-4e3e-b8e6-bfbfe5c7e09f  None           ok    
3592.619     /api/alert/analyze  analyze_request_total  PHASEC25-0013  6cb5e2bb-2843-499c-8cef-e95324e1e763  None           ok    
3369.858     /api/alert/analyze  analyze_request_total  PHASEC25-0011  b9b008e3-7960-4469-8d2e-496f631a9a29  None           ok    
3060.469     /api/alert/analyze  analyze_request_total  PHASEC25-0010  49235123-49d5-4795-b1a4-f55449f06def  None           ok    
2910.905     /api/alert/analyze  analyze_request_total  PHASEC25-0009  61bc52ce-15cd-403d-b52f-fee15ae4da95  None           ok    
2710.987     /api/alert/analyze  analyze_request_total  PHASEC25-0008  1c60e884-6142-4fe3-ad11-60cc63189214  None           ok    
2705.697     /api/alert/analyze  analyze_request_total  PHASEC25-0007  5c26715d-76be-4309-8d30-53c3778c474d  None           ok    
2458.936     /api/alert/analyze  analyze_request_total  PHASEC25-0006  dba9d1ac-738e-4665-889a-22f758481117  None           ok    
```

## Early/Mid/Late Windows
```text
(none)
```

## Per-Alert Waterfall

### PHASEC25-0025
- event_count: 27
- total_observed_ms: 9303.621
- authoritative_total_ms: 5692.343
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.039        /api/alert/analyze  scorer_readiness                    ok    
0.017        /api/alert/analyze  request_parse                       ok    
70.863       /api/alert/analyze  alert_lookup                        ok    
89.653       /api/alert/analyze  security_context_lookup             ok    
0.114        /api/alert/analyze  category_resolution                 ok    
378.097      /api/alert/analyze  factor_vector_construction          ok    
0.254        /api/alert/analyze  scorer_decision                     ok    
87.724       /api/alert/analyze  decision_node_and_edge_write        ok    
77.743       /api/alert/analyze  audit_write                         ok    
1.325        /api/alert/analyze  metadata_logging_snapshot_write     ok    
0.159        /api/alert/analyze  response_serialization              ok    
5692.343     /api/alert/analyze  analyze_request_total               ok    
0.015        /api/alert/outcome  request_parse                       ok    
0.018        /api/alert/outcome  duplicate_feedback_guard            ok    
80.889       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
1.106        /api/alert/outcome  outcome_audit_write                 ok    
40.764       /api/alert/outcome  learning_state_update               ok    
417.003      /api/alert/outcome  l5_conservation_write               ok    
418.272      /api/alert/outcome  conservation_monitor                ok    
0.094        /api/alert/outcome  profile_scorer_update               ok    
0.068        /api/alert/outcome  l5_dk_weight_write                  ok    
401.48       /api/alert/outcome  l5_centroid_write                   ok    
0.015        /api/alert/outcome  l5_dk_weight_write                  ok    
0.019        /api/alert/outcome  snapshot_evolution_logging          ok    
77.865       /api/alert/outcome  snapshot_evolution_logging          ok    
0.019        /api/alert/outcome  response_serialization              ok    
1467.663     /api/alert/outcome  outcome_request_total               ok    
```

### PHASEC25-0024
- event_count: 27
- total_observed_ms: 9222.409
- authoritative_total_ms: 5609.883
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.035        /api/alert/analyze  scorer_readiness                    ok    
0.016        /api/alert/analyze  request_parse                       ok    
98.615       /api/alert/analyze  alert_lookup                        ok    
79.034       /api/alert/analyze  security_context_lookup             ok    
0.124        /api/alert/analyze  category_resolution                 ok    
322.44       /api/alert/analyze  factor_vector_construction          ok    
0.125        /api/alert/analyze  scorer_decision                     ok    
73.129       /api/alert/analyze  decision_node_and_edge_write        ok    
80.713       /api/alert/analyze  audit_write                         ok    
0.672        /api/alert/analyze  metadata_logging_snapshot_write     ok    
0.153        /api/alert/analyze  response_serialization              ok    
5609.883     /api/alert/analyze  analyze_request_total               ok    
0.017        /api/alert/outcome  request_parse                       ok    
0.018        /api/alert/outcome  duplicate_feedback_guard            ok    
77.602       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.163        /api/alert/outcome  outcome_audit_write                 ok    
36.111       /api/alert/outcome  learning_state_update               ok    
418.08       /api/alert/outcome  l5_conservation_write               ok    
419.306      /api/alert/outcome  conservation_monitor                ok    
0.13         /api/alert/outcome  profile_scorer_update               ok    
0.102        /api/alert/outcome  l5_dk_weight_write                  ok    
449.219      /api/alert/outcome  l5_centroid_write                   ok    
0.018        /api/alert/outcome  l5_dk_weight_write                  ok    
0.022        /api/alert/outcome  snapshot_evolution_logging          ok    
72.322       /api/alert/outcome  snapshot_evolution_logging          ok    
0.033        /api/alert/outcome  response_serialization              ok    
1484.327     /api/alert/outcome  outcome_request_total               ok    
```

### PHASEC25-0023
- event_count: 27
- total_observed_ms: 8901.329
- authoritative_total_ms: 5279.115
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.028        /api/alert/analyze  scorer_readiness                    ok    
0.017        /api/alert/analyze  request_parse                       ok    
94.324       /api/alert/analyze  alert_lookup                        ok    
80.981       /api/alert/analyze  security_context_lookup             ok    
0.106        /api/alert/analyze  category_resolution                 ok    
313.652      /api/alert/analyze  factor_vector_construction          ok    
0.257        /api/alert/analyze  scorer_decision                     ok    
89.054       /api/alert/analyze  decision_node_and_edge_write        ok    
73.371       /api/alert/analyze  audit_write                         ok    
0.119        /api/alert/analyze  metadata_logging_snapshot_write     ok    
0.198        /api/alert/analyze  response_serialization              ok    
5279.115     /api/alert/analyze  analyze_request_total               ok    
0.007        /api/alert/outcome  request_parse                       ok    
0.006        /api/alert/outcome  duplicate_feedback_guard            ok    
73.593       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.329        /api/alert/outcome  outcome_audit_write                 ok    
50.405       /api/alert/outcome  learning_state_update               ok    
415.32       /api/alert/outcome  l5_conservation_write               ok    
416.141      /api/alert/outcome  conservation_monitor                ok    
0.084        /api/alert/outcome  profile_scorer_update               ok    
0.064        /api/alert/outcome  l5_dk_weight_write                  ok    
446.041      /api/alert/outcome  l5_centroid_write                   ok    
0.018        /api/alert/outcome  l5_dk_weight_write                  ok    
0.012        /api/alert/outcome  snapshot_evolution_logging          ok    
75.397       /api/alert/outcome  snapshot_evolution_logging          ok    
0.073        /api/alert/outcome  response_serialization              ok    
1492.617     /api/alert/outcome  outcome_request_total               ok    
```

### PHASEC25-0022
- event_count: 27
- total_observed_ms: 8928.455
- authoritative_total_ms: 5189.614
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.01         /api/alert/analyze  scorer_readiness                    ok    
0.006        /api/alert/analyze  request_parse                       ok    
58.925       /api/alert/analyze  alert_lookup                        ok    
85.531       /api/alert/analyze  security_context_lookup             ok    
0.085        /api/alert/analyze  category_resolution                 ok    
325.379      /api/alert/analyze  factor_vector_construction          ok    
0.127        /api/alert/analyze  scorer_decision                     ok    
88.671       /api/alert/analyze  decision_node_and_edge_write        ok    
73.273       /api/alert/analyze  audit_write                         ok    
0.159        /api/alert/analyze  metadata_logging_snapshot_write     ok    
0.18         /api/alert/analyze  response_serialization              ok    
5189.614     /api/alert/analyze  analyze_request_total               ok    
0.016        /api/alert/outcome  request_parse                       ok    
0.014        /api/alert/outcome  duplicate_feedback_guard            ok    
80.761       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.346        /api/alert/outcome  outcome_audit_write                 ok    
43.023       /api/alert/outcome  learning_state_update               ok    
423.533      /api/alert/outcome  l5_conservation_write               ok    
425.657      /api/alert/outcome  conservation_monitor                ok    
0.153        /api/alert/outcome  profile_scorer_update               ok    
0.127        /api/alert/outcome  l5_dk_weight_write                  ok    
400.292      /api/alert/outcome  l5_centroid_write                   ok    
0.011        /api/alert/outcome  l5_dk_weight_write                  ok    
96.386       /api/alert/outcome  snapshot_evolution_logging          ok    
74.44        /api/alert/outcome  snapshot_evolution_logging          ok    
0.042        /api/alert/outcome  response_serialization              ok    
1561.694     /api/alert/outcome  outcome_request_total               ok    
```

### PHASEC25-0021
- event_count: 27
- total_observed_ms: 8586.51
- authoritative_total_ms: 5097.088
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.015        /api/alert/analyze  scorer_readiness                    ok    
0.009        /api/alert/analyze  request_parse                       ok    
68.789       /api/alert/analyze  alert_lookup                        ok    
78.241       /api/alert/analyze  security_context_lookup             ok    
0.112        /api/alert/analyze  category_resolution                 ok    
347.93       /api/alert/analyze  factor_vector_construction          ok    
0.149        /api/alert/analyze  scorer_decision                     ok    
85.221       /api/alert/analyze  decision_node_and_edge_write        ok    
62.672       /api/alert/analyze  audit_write                         ok    
0.294        /api/alert/analyze  metadata_logging_snapshot_write     ok    
0.108        /api/alert/analyze  response_serialization              ok    
5097.088     /api/alert/analyze  analyze_request_total               ok    
0.01         /api/alert/outcome  request_parse                       ok    
0.012        /api/alert/outcome  duplicate_feedback_guard            ok    
79.978       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.414        /api/alert/outcome  outcome_audit_write                 ok    
38.683       /api/alert/outcome  learning_state_update               ok    
385.406      /api/alert/outcome  l5_conservation_write               ok    
386.335      /api/alert/outcome  conservation_monitor                ok    
0.1          /api/alert/outcome  profile_scorer_update               ok    
0.113        /api/alert/outcome  l5_dk_weight_write                  ok    
448.332      /api/alert/outcome  l5_centroid_write                   ok    
0.017        /api/alert/outcome  l5_dk_weight_write                  ok    
0.018        /api/alert/outcome  snapshot_evolution_logging          ok    
85.116       /api/alert/outcome  snapshot_evolution_logging          ok    
0.019        /api/alert/outcome  response_serialization              ok    
1421.329     /api/alert/outcome  outcome_request_total               ok    
```

### PHASEC25-0020
- event_count: 27
- total_observed_ms: 8274.031
- authoritative_total_ms: 4814.853
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.029        /api/alert/analyze  scorer_readiness                    ok    
0.015        /api/alert/analyze  request_parse                       ok    
93.753       /api/alert/analyze  alert_lookup                        ok    
81.288       /api/alert/analyze  security_context_lookup             ok    
0.144        /api/alert/analyze  category_resolution                 ok    
315.46       /api/alert/analyze  factor_vector_construction          ok    
0.235        /api/alert/analyze  scorer_decision                     ok    
93.193       /api/alert/analyze  decision_node_and_edge_write        ok    
91.319       /api/alert/analyze  audit_write                         ok    
3.058        /api/alert/analyze  metadata_logging_snapshot_write     ok    
0.08         /api/alert/analyze  response_serialization              ok    
4814.853     /api/alert/analyze  analyze_request_total               ok    
0.012        /api/alert/outcome  request_parse                       ok    
0.009        /api/alert/outcome  duplicate_feedback_guard            ok    
70.816       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.289        /api/alert/outcome  outcome_audit_write                 ok    
35.822       /api/alert/outcome  learning_state_update               ok    
409.628      /api/alert/outcome  l5_conservation_write               ok    
410.982      /api/alert/outcome  conservation_monitor                ok    
0.121        /api/alert/outcome  profile_scorer_update               ok    
0.095        /api/alert/outcome  l5_dk_weight_write                  ok    
400.979      /api/alert/outcome  l5_centroid_write                   ok    
0.01         /api/alert/outcome  l5_dk_weight_write                  ok    
0.011        /api/alert/outcome  snapshot_evolution_logging          ok    
73.364       /api/alert/outcome  snapshot_evolution_logging          ok    
0.036        /api/alert/outcome  response_serialization              ok    
1378.43      /api/alert/outcome  outcome_request_total               ok    
```

### PHASEC25-0018
- event_count: 27
- total_observed_ms: 8171.897
- authoritative_total_ms: 4638.823
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.033        /api/alert/analyze  scorer_readiness                    ok    
0.023        /api/alert/analyze  request_parse                       ok    
93.682       /api/alert/analyze  alert_lookup                        ok    
81.843       /api/alert/analyze  security_context_lookup             ok    
0.119        /api/alert/analyze  category_resolution                 ok    
374.041      /api/alert/analyze  factor_vector_construction          ok    
0.194        /api/alert/analyze  scorer_decision                     ok    
103.051      /api/alert/analyze  decision_node_and_edge_write        ok    
90.932       /api/alert/analyze  audit_write                         ok    
0.152        /api/alert/analyze  metadata_logging_snapshot_write     ok    
0.093        /api/alert/analyze  response_serialization              ok    
4638.823     /api/alert/analyze  analyze_request_total               ok    
0.012        /api/alert/outcome  request_parse                       ok    
0.01         /api/alert/outcome  duplicate_feedback_guard            ok    
90.235       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.227        /api/alert/outcome  outcome_audit_write                 ok    
37.345       /api/alert/outcome  learning_state_update               ok    
377.443      /api/alert/outcome  l5_conservation_write               ok    
378.306      /api/alert/outcome  conservation_monitor                ok    
0.084        /api/alert/outcome  profile_scorer_update               ok    
0.062        /api/alert/outcome  l5_dk_weight_write                  ok    
438.409      /api/alert/outcome  l5_centroid_write                   ok    
0.023        /api/alert/outcome  l5_dk_weight_write                  ok    
0.029        /api/alert/outcome  snapshot_evolution_logging          ok    
75.195       /api/alert/outcome  snapshot_evolution_logging          ok    
0.029        /api/alert/outcome  response_serialization              ok    
1391.502     /api/alert/outcome  outcome_request_total               ok    
```

### PHASEC25-0019
- event_count: 27
- total_observed_ms: 8041.828
- authoritative_total_ms: 4503.113
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.028        /api/alert/analyze  scorer_readiness                    ok    
0.013        /api/alert/analyze  request_parse                       ok    
100.976      /api/alert/analyze  alert_lookup                        ok    
96.367       /api/alert/analyze  security_context_lookup             ok    
0.153        /api/alert/analyze  category_resolution                 ok    
342.006      /api/alert/analyze  factor_vector_construction          ok    
0.227        /api/alert/analyze  scorer_decision                     ok    
78.476       /api/alert/analyze  decision_node_and_edge_write        ok    
78.57        /api/alert/analyze  audit_write                         ok    
0.349        /api/alert/analyze  metadata_logging_snapshot_write     ok    
0.169        /api/alert/analyze  response_serialization              ok    
4503.113     /api/alert/analyze  analyze_request_total               ok    
0.011        /api/alert/outcome  request_parse                       ok    
0.008        /api/alert/outcome  duplicate_feedback_guard            ok    
80.54        /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.559        /api/alert/outcome  outcome_audit_write                 ok    
37.769       /api/alert/outcome  learning_state_update               ok    
384.626      /api/alert/outcome  l5_conservation_write               ok    
386.488      /api/alert/outcome  conservation_monitor                ok    
0.153        /api/alert/outcome  profile_scorer_update               ok    
0.156        /api/alert/outcome  l5_dk_weight_write                  ok    
449.612      /api/alert/outcome  l5_centroid_write                   ok    
0.029        /api/alert/outcome  l5_dk_weight_write                  ok    
0.02         /api/alert/outcome  snapshot_evolution_logging          ok    
76.582       /api/alert/outcome  snapshot_evolution_logging          ok    
0.035        /api/alert/outcome  response_serialization              ok    
1424.793     /api/alert/outcome  outcome_request_total               ok    
```

### PHASEC25-0017
- event_count: 27
- total_observed_ms: 7870.632
- authoritative_total_ms: 4239.696
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.011        /api/alert/analyze  scorer_readiness                    ok    
0.013        /api/alert/analyze  request_parse                       ok    
70.599       /api/alert/analyze  alert_lookup                        ok    
86.377       /api/alert/analyze  security_context_lookup             ok    
0.079        /api/alert/analyze  category_resolution                 ok    
319.031      /api/alert/analyze  factor_vector_construction          ok    
0.205        /api/alert/analyze  scorer_decision                     ok    
91.461       /api/alert/analyze  decision_node_and_edge_write        ok    
88.654       /api/alert/analyze  audit_write                         ok    
2.75         /api/alert/analyze  metadata_logging_snapshot_write     ok    
0.113        /api/alert/analyze  response_serialization              ok    
4239.696     /api/alert/analyze  analyze_request_total               ok    
0.012        /api/alert/outcome  request_parse                       ok    
0.007        /api/alert/outcome  duplicate_feedback_guard            ok    
78.575       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.451        /api/alert/outcome  outcome_audit_write                 ok    
45.152       /api/alert/outcome  learning_state_update               ok    
439.106      /api/alert/outcome  l5_conservation_write               ok    
441.367      /api/alert/outcome  conservation_monitor                ok    
0.198        /api/alert/outcome  profile_scorer_update               ok    
0.165        /api/alert/outcome  l5_dk_weight_write                  ok    
437.708      /api/alert/outcome  l5_centroid_write                   ok    
0.018        /api/alert/outcome  l5_dk_weight_write                  ok    
0.028        /api/alert/outcome  snapshot_evolution_logging          ok    
71.101       /api/alert/outcome  snapshot_evolution_logging          ok    
0.046        /api/alert/outcome  response_serialization              ok    
1457.709     /api/alert/outcome  outcome_request_total               ok    
```

### PHASEC25-0016
- event_count: 27
- total_observed_ms: 7673.848
- authoritative_total_ms: 4182.408
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.028        /api/alert/analyze  scorer_readiness                    ok    
0.014        /api/alert/analyze  request_parse                       ok    
83.205       /api/alert/analyze  alert_lookup                        ok    
89.199       /api/alert/analyze  security_context_lookup             ok    
0.134        /api/alert/analyze  category_resolution                 ok    
346.268      /api/alert/analyze  factor_vector_construction          ok    
0.345        /api/alert/analyze  scorer_decision                     ok    
71.086       /api/alert/analyze  decision_node_and_edge_write        ok    
64.989       /api/alert/analyze  audit_write                         ok    
0.118        /api/alert/analyze  metadata_logging_snapshot_write     ok    
0.154        /api/alert/analyze  response_serialization              ok    
4182.408     /api/alert/analyze  analyze_request_total               ok    
0.015        /api/alert/outcome  request_parse                       ok    
0.014        /api/alert/outcome  duplicate_feedback_guard            ok    
102.933      /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.366        /api/alert/outcome  outcome_audit_write                 ok    
41.983       /api/alert/outcome  learning_state_update               ok    
431.267      /api/alert/outcome  l5_conservation_write               ok    
432.815      /api/alert/outcome  conservation_monitor                ok    
0.209        /api/alert/outcome  profile_scorer_update               ok    
0.133        /api/alert/outcome  l5_dk_weight_write                  ok    
384.543      /api/alert/outcome  l5_centroid_write                   ok    
0.01         /api/alert/outcome  l5_dk_weight_write                  ok    
0.022        /api/alert/outcome  snapshot_evolution_logging          ok    
64.842       /api/alert/outcome  snapshot_evolution_logging          ok    
0.032        /api/alert/outcome  response_serialization              ok    
1376.716     /api/alert/outcome  outcome_request_total               ok    
```

### PHASEC25-0014
- event_count: 27
- total_observed_ms: 7663.661
- authoritative_total_ms: 3901.007
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.027        /api/alert/analyze  scorer_readiness                    ok    
0.018        /api/alert/analyze  request_parse                       ok    
85.64        /api/alert/analyze  alert_lookup                        ok    
83.221       /api/alert/analyze  security_context_lookup             ok    
0.155        /api/alert/analyze  category_resolution                 ok    
313.14       /api/alert/analyze  factor_vector_construction          ok    
0.165        /api/alert/analyze  scorer_decision                     ok    
81.028       /api/alert/analyze  decision_node_and_edge_write        ok    
86.463       /api/alert/analyze  audit_write                         ok    
0.237        /api/alert/analyze  metadata_logging_snapshot_write     ok    
0.211        /api/alert/analyze  response_serialization              ok    
3901.007     /api/alert/analyze  analyze_request_total               ok    
0.017        /api/alert/outcome  request_parse                       ok    
0.02         /api/alert/outcome  duplicate_feedback_guard            ok    
89.677       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
1.04         /api/alert/outcome  outcome_audit_write                 ok    
83.137       /api/alert/outcome  learning_state_update               ok    
443.707      /api/alert/outcome  l5_conservation_write               ok    
445.566      /api/alert/outcome  conservation_monitor                ok    
0.286        /api/alert/outcome  profile_scorer_update               ok    
0.249        /api/alert/outcome  l5_dk_weight_write                  ok    
428.189      /api/alert/outcome  l5_centroid_write                   ok    
0.019        /api/alert/outcome  l5_dk_weight_write                  ok    
0.034        /api/alert/outcome  snapshot_evolution_logging          ok    
72.901       /api/alert/outcome  snapshot_evolution_logging          ok    
0.023        /api/alert/outcome  response_serialization              ok    
1547.484     /api/alert/outcome  outcome_request_total               ok    
```

### PHASEC25-0015
- event_count: 27
- total_observed_ms: 7553.931
- authoritative_total_ms: 3843.819
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.015        /api/alert/analyze  scorer_readiness                    ok    
0.016        /api/alert/analyze  request_parse                       ok    
63.955       /api/alert/analyze  alert_lookup                        ok    
80.546       /api/alert/analyze  security_context_lookup             ok    
0.123        /api/alert/analyze  category_resolution                 ok    
292.232      /api/alert/analyze  factor_vector_construction          ok    
0.186        /api/alert/analyze  scorer_decision                     ok    
78.498       /api/alert/analyze  decision_node_and_edge_write        ok    
66.602       /api/alert/analyze  audit_write                         ok    
0.374        /api/alert/analyze  metadata_logging_snapshot_write     ok    
0.154        /api/alert/analyze  response_serialization              ok    
3843.819     /api/alert/analyze  analyze_request_total               ok    
0.014        /api/alert/outcome  request_parse                       ok    
0.012        /api/alert/outcome  duplicate_feedback_guard            ok    
80.583       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
1.034        /api/alert/outcome  outcome_audit_write                 ok    
130.405      /api/alert/outcome  learning_state_update               ok    
424.172      /api/alert/outcome  l5_conservation_write               ok    
431.471      /api/alert/outcome  conservation_monitor                ok    
0.454        /api/alert/outcome  profile_scorer_update               ok    
0.293        /api/alert/outcome  l5_dk_weight_write                  ok    
436.441      /api/alert/outcome  l5_centroid_write                   ok    
0.013        /api/alert/outcome  l5_dk_weight_write                  ok    
0.018        /api/alert/outcome  snapshot_evolution_logging          ok    
76.295       /api/alert/outcome  snapshot_evolution_logging          ok    
0.039        /api/alert/outcome  response_serialization              ok    
1546.167     /api/alert/outcome  outcome_request_total               ok    
```

### PHASEC25-0012
- event_count: 27
- total_observed_ms: 7526.038
- authoritative_total_ms: 3704.297
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.011        /api/alert/analyze  scorer_readiness                    ok    
0.018        /api/alert/analyze  request_parse                       ok    
69.458       /api/alert/analyze  alert_lookup                        ok    
92.791       /api/alert/analyze  security_context_lookup             ok    
0.119        /api/alert/analyze  category_resolution                 ok    
300.242      /api/alert/analyze  factor_vector_construction          ok    
0.157        /api/alert/analyze  scorer_decision                     ok    
64.474       /api/alert/analyze  decision_node_and_edge_write        ok    
83.44        /api/alert/analyze  audit_write                         ok    
0.465        /api/alert/analyze  metadata_logging_snapshot_write     ok    
0.121        /api/alert/analyze  response_serialization              ok    
3704.297     /api/alert/analyze  analyze_request_total               ok    
0.017        /api/alert/outcome  request_parse                       ok    
0.008        /api/alert/outcome  duplicate_feedback_guard            ok    
93.399       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
1.221        /api/alert/outcome  outcome_audit_write                 ok    
118.298      /api/alert/outcome  learning_state_update               ok    
417.425      /api/alert/outcome  l5_conservation_write               ok    
420.496      /api/alert/outcome  conservation_monitor                ok    
0.244        /api/alert/outcome  profile_scorer_update               ok    
0.216        /api/alert/outcome  l5_dk_weight_write                  ok    
445.112      /api/alert/outcome  l5_centroid_write                   ok    
0.013        /api/alert/outcome  l5_dk_weight_write                  ok    
0.015        /api/alert/outcome  snapshot_evolution_logging          ok    
93.607       /api/alert/outcome  snapshot_evolution_logging          ok    
0.02         /api/alert/outcome  response_serialization              ok    
1620.354     /api/alert/outcome  outcome_request_total               ok    
```

### PHASEC25-0013
- event_count: 27
- total_observed_ms: 7487.503
- authoritative_total_ms: 3592.619
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.028        /api/alert/analyze  scorer_readiness                    ok    
0.012        /api/alert/analyze  request_parse                       ok    
87.215       /api/alert/analyze  alert_lookup                        ok    
93.974       /api/alert/analyze  security_context_lookup             ok    
0.124        /api/alert/analyze  category_resolution                 ok    
349.924      /api/alert/analyze  factor_vector_construction          ok    
0.314        /api/alert/analyze  scorer_decision                     ok    
85.231       /api/alert/analyze  decision_node_and_edge_write        ok    
90.264       /api/alert/analyze  audit_write                         ok    
0.422        /api/alert/analyze  metadata_logging_snapshot_write     ok    
0.218        /api/alert/analyze  response_serialization              ok    
3592.619     /api/alert/analyze  analyze_request_total               ok    
0.015        /api/alert/outcome  request_parse                       ok    
0.021        /api/alert/outcome  duplicate_feedback_guard            ok    
94.308       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.657        /api/alert/outcome  outcome_audit_write                 ok    
112.763      /api/alert/outcome  learning_state_update               ok    
434.025      /api/alert/outcome  l5_conservation_write               ok    
435.214      /api/alert/outcome  conservation_monitor                ok    
0.169        /api/alert/outcome  profile_scorer_update               ok    
0.132        /api/alert/outcome  l5_dk_weight_write                  ok    
432.93       /api/alert/outcome  l5_centroid_write                   ok    
0.026        /api/alert/outcome  l5_dk_weight_write                  ok    
0.019        /api/alert/outcome  snapshot_evolution_logging          ok    
67.795       /api/alert/outcome  snapshot_evolution_logging          ok    
0.019        /api/alert/outcome  response_serialization              ok    
1609.065     /api/alert/outcome  outcome_request_total               ok    
```

### PHASEC25-0011
- event_count: 27
- total_observed_ms: 6797.742
- authoritative_total_ms: 3369.858
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.017        /api/alert/analyze  scorer_readiness                    ok    
0.02         /api/alert/analyze  request_parse                       ok    
73.197       /api/alert/analyze  alert_lookup                        ok    
79.027       /api/alert/analyze  security_context_lookup             ok    
0.078        /api/alert/analyze  category_resolution                 ok    
306.651      /api/alert/analyze  factor_vector_construction          ok    
0.134        /api/alert/analyze  scorer_decision                     ok    
84.947       /api/alert/analyze  decision_node_and_edge_write        ok    
101.935      /api/alert/analyze  audit_write                         ok    
1.474        /api/alert/analyze  metadata_logging_snapshot_write     ok    
0.116        /api/alert/analyze  response_serialization              ok    
3369.858     /api/alert/analyze  analyze_request_total               ok    
0.014        /api/alert/outcome  request_parse                       ok    
0.009        /api/alert/outcome  duplicate_feedback_guard            ok    
91.064       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.191        /api/alert/outcome  outcome_audit_write                 ok    
42.069       /api/alert/outcome  learning_state_update               ok    
385.362      /api/alert/outcome  l5_conservation_write               ok    
386.434      /api/alert/outcome  conservation_monitor                ok    
0.115        /api/alert/outcome  profile_scorer_update               ok    
0.082        /api/alert/outcome  l5_dk_weight_write                  ok    
413.045      /api/alert/outcome  l5_centroid_write                   ok    
0.013        /api/alert/outcome  l5_dk_weight_write                  ok    
0.015        /api/alert/outcome  snapshot_evolution_logging          ok    
73.963       /api/alert/outcome  snapshot_evolution_logging          ok    
0.023        /api/alert/outcome  response_serialization              ok    
1387.889     /api/alert/outcome  outcome_request_total               ok    
```

### PHASEC25-0010
- event_count: 27
- total_observed_ms: 6289.721
- authoritative_total_ms: 3060.469
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.037        /api/alert/analyze  scorer_readiness                    ok    
0.019        /api/alert/analyze  request_parse                       ok    
75.246       /api/alert/analyze  alert_lookup                        ok    
73.814       /api/alert/analyze  security_context_lookup             ok    
0.123        /api/alert/analyze  category_resolution                 ok    
303.293      /api/alert/analyze  factor_vector_construction          ok    
0.178        /api/alert/analyze  scorer_decision                     ok    
87.441       /api/alert/analyze  decision_node_and_edge_write        ok    
96.666       /api/alert/analyze  audit_write                         ok    
0.56         /api/alert/analyze  metadata_logging_snapshot_write     ok    
0.559        /api/alert/analyze  response_serialization              ok    
3060.469     /api/alert/analyze  analyze_request_total               ok    
0.016        /api/alert/outcome  request_parse                       ok    
0.015        /api/alert/outcome  duplicate_feedback_guard            ok    
87.129       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.597        /api/alert/outcome  outcome_audit_write                 ok    
67.75        /api/alert/outcome  learning_state_update               ok    
353.194      /api/alert/outcome  l5_conservation_write               ok    
353.924      /api/alert/outcome  conservation_monitor                ok    
0.09         /api/alert/outcome  profile_scorer_update               ok    
0.074        /api/alert/outcome  l5_dk_weight_write                  ok    
351.808      /api/alert/outcome  l5_centroid_write                   ok    
0.022        /api/alert/outcome  l5_dk_weight_write                  ok    
0.02         /api/alert/outcome  snapshot_evolution_logging          ok    
66.74        /api/alert/outcome  snapshot_evolution_logging          ok    
0.022        /api/alert/outcome  response_serialization              ok    
1309.915     /api/alert/outcome  outcome_request_total               ok    
```

### PHASEC25-0009
- event_count: 27
- total_observed_ms: 6062.431
- authoritative_total_ms: 2910.905
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.011        /api/alert/analyze  scorer_readiness                    ok    
0.005        /api/alert/analyze  request_parse                       ok    
65.036       /api/alert/analyze  alert_lookup                        ok    
74.22        /api/alert/analyze  security_context_lookup             ok    
0.087        /api/alert/analyze  category_resolution                 ok    
332.281      /api/alert/analyze  factor_vector_construction          ok    
0.166        /api/alert/analyze  scorer_decision                     ok    
86.391       /api/alert/analyze  decision_node_and_edge_write        ok    
79.178       /api/alert/analyze  audit_write                         ok    
0.174        /api/alert/analyze  metadata_logging_snapshot_write     ok    
0.085        /api/alert/analyze  response_serialization              ok    
2910.905     /api/alert/analyze  analyze_request_total               ok    
0.069        /api/alert/outcome  request_parse                       ok    
0.007        /api/alert/outcome  duplicate_feedback_guard            ok    
79.483       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
1.523        /api/alert/outcome  outcome_audit_write                 ok    
35.853       /api/alert/outcome  learning_state_update               ok    
346.045      /api/alert/outcome  l5_conservation_write               ok    
346.812      /api/alert/outcome  conservation_monitor                ok    
0.092        /api/alert/outcome  profile_scorer_update               ok    
0.064        /api/alert/outcome  l5_dk_weight_write                  ok    
354.619      /api/alert/outcome  l5_centroid_write                   ok    
0.024        /api/alert/outcome  l5_dk_weight_write                  ok    
0.028        /api/alert/outcome  snapshot_evolution_logging          ok    
76.924       /api/alert/outcome  snapshot_evolution_logging          ok    
0.044        /api/alert/outcome  response_serialization              ok    
1272.305     /api/alert/outcome  outcome_request_total               ok    
```

### PHASEC25-0008
- event_count: 27
- total_observed_ms: 6465.342
- authoritative_total_ms: 2710.987
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.044        /api/alert/analyze  scorer_readiness                    ok    
0.01         /api/alert/analyze  request_parse                       ok    
81.467       /api/alert/analyze  alert_lookup                        ok    
76.679       /api/alert/analyze  security_context_lookup             ok    
0.127        /api/alert/analyze  category_resolution                 ok    
321.99       /api/alert/analyze  factor_vector_construction          ok    
0.436        /api/alert/analyze  scorer_decision                     ok    
87.951       /api/alert/analyze  decision_node_and_edge_write        ok    
81.648       /api/alert/analyze  audit_write                         ok    
0.146        /api/alert/analyze  metadata_logging_snapshot_write     ok    
0.096        /api/alert/analyze  response_serialization              ok    
2710.987     /api/alert/analyze  analyze_request_total               ok    
0.012        /api/alert/outcome  request_parse                       ok    
0.014        /api/alert/outcome  duplicate_feedback_guard            ok    
71.438       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.556        /api/alert/outcome  outcome_audit_write                 ok    
204.639      /api/alert/outcome  learning_state_update               ok    
391.936      /api/alert/outcome  l5_conservation_write               ok    
393.172      /api/alert/outcome  conservation_monitor                ok    
0.137        /api/alert/outcome  profile_scorer_update               ok    
0.09         /api/alert/outcome  l5_dk_weight_write                  ok    
395.231      /api/alert/outcome  l5_centroid_write                   ok    
0.02         /api/alert/outcome  l5_dk_weight_write                  ok    
0.017        /api/alert/outcome  snapshot_evolution_logging          ok    
83.592       /api/alert/outcome  snapshot_evolution_logging          ok    
0.019        /api/alert/outcome  response_serialization              ok    
1562.888     /api/alert/outcome  outcome_request_total               ok    
```

### PHASEC25-0007
- event_count: 27
- total_observed_ms: 6317.147
- authoritative_total_ms: 2705.697
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.03         /api/alert/analyze  scorer_readiness                    ok    
0.013        /api/alert/analyze  request_parse                       ok    
74.074       /api/alert/analyze  alert_lookup                        ok    
84.462       /api/alert/analyze  security_context_lookup             ok    
0.152        /api/alert/analyze  category_resolution                 ok    
310.467      /api/alert/analyze  factor_vector_construction          ok    
0.18         /api/alert/analyze  scorer_decision                     ok    
93.321       /api/alert/analyze  decision_node_and_edge_write        ok    
69.822       /api/alert/analyze  audit_write                         ok    
0.829        /api/alert/analyze  metadata_logging_snapshot_write     ok    
0.212        /api/alert/analyze  response_serialization              ok    
2705.697     /api/alert/analyze  analyze_request_total               ok    
0.046        /api/alert/outcome  request_parse                       ok    
0.012        /api/alert/outcome  duplicate_feedback_guard            ok    
93.901       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.341        /api/alert/outcome  outcome_audit_write                 ok    
107.468      /api/alert/outcome  learning_state_update               ok    
371.45       /api/alert/outcome  l5_conservation_write               ok    
373.462      /api/alert/outcome  conservation_monitor                ok    
0.138        /api/alert/outcome  profile_scorer_update               ok    
0.104        /api/alert/outcome  l5_dk_weight_write                  ok    
450.177      /api/alert/outcome  l5_centroid_write                   ok    
0.015        /api/alert/outcome  l5_dk_weight_write                  ok    
0.05         /api/alert/outcome  snapshot_evolution_logging          ok    
79.477       /api/alert/outcome  snapshot_evolution_logging          ok    
0.051        /api/alert/outcome  response_serialization              ok    
1501.196     /api/alert/outcome  outcome_request_total               ok    
```

### PHASEC25-0006
- event_count: 27
- total_observed_ms: 5933.951
- authoritative_total_ms: 2458.936
```text
duration_ms  route               phase                               status
-----------  ------------------  ----------------------------------  ------
0.022        /api/alert/analyze  scorer_readiness                    ok    
0.006        /api/alert/analyze  request_parse                       ok    
66.181       /api/alert/analyze  alert_lookup                        ok    
70.298       /api/alert/analyze  security_context_lookup             ok    
0.119        /api/alert/analyze  category_resolution                 ok    
327.013      /api/alert/analyze  factor_vector_construction          ok    
0.295        /api/alert/analyze  scorer_decision                     ok    
79.004       /api/alert/analyze  decision_node_and_edge_write        ok    
73.739       /api/alert/analyze  audit_write                         ok    
0.119        /api/alert/analyze  metadata_logging_snapshot_write     ok    
0.132        /api/alert/analyze  response_serialization              ok    
2458.936     /api/alert/analyze  analyze_request_total               ok    
0.01         /api/alert/outcome  request_parse                       ok    
0.008        /api/alert/outcome  duplicate_feedback_guard            ok    
95.715       /api/alert/outcome  decision_lookup_and_outcome_update  ok    
0.477        /api/alert/outcome  outcome_audit_write                 ok    
81.412       /api/alert/outcome  learning_state_update               ok    
392.676      /api/alert/outcome  l5_conservation_write               ok    
394.577      /api/alert/outcome  conservation_monitor                ok    
0.142        /api/alert/outcome  profile_scorer_update               ok    
0.117        /api/alert/outcome  l5_dk_weight_write                  ok    
384.757      /api/alert/outcome  l5_centroid_write                   ok    
0.016        /api/alert/outcome  l5_dk_weight_write                  ok    
0.063        /api/alert/outcome  snapshot_evolution_logging          ok    
65.004       /api/alert/outcome  snapshot_evolution_logging          ok    
0.025        /api/alert/outcome  response_serialization              ok    
1443.088     /api/alert/outcome  outcome_request_total               ok    
```

## Nested Phase Warning
Nested phase durations should not be summed blindly. Use analyze_request_total, outcome_request_total, or total_attempt as authoritative totals.
