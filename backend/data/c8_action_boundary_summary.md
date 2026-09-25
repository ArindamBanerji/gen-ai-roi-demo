# C8 — Action-Value Boundary

Tier: REAL_COMPONENT SOC centroid geometry + SIMULATED synthetic fixture/evidence/action-vote labels. Metric: action_accuracy (predicted action equals fixture action vote). `routing_quality` is not measured for the new action-rescoring sweep; `category_accuracy` is not measured there either.

## Scope

SOC only. This repository has a SOC scorer/pattern harness and the 543-alert fixture. The only other domain config is supply_chain/S2P, a smoke-test stub without `build_profile_scorer()` or a compatible fixture; Trading, Purchasing, and DataOps domain configs are absent. The copilot-SDK geometry files are not application configs/fixtures for this harness.

## Existing SOC A–E results

| Geometry | A current VLD | B route+surface | C selective | D route+selective | E oracle-category | Single-pass | Harness verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| default | 31.31% | 53.78% | 53.78% | 53.78% | 36.10% | 53.78% | ARCHITECTURE ISSUE: oracle <= SP. Investigation cannot improve actions on this data. VLD value limited to structured triage. |
| trained | 20.44% | 15.10% | 21.92% | 22.47% | 23.39% | 15.10% | VLD VALUE = SELECTIVE ENRICHMENT: selective strategy beats SP. |
| bootstrapped | 19.52% | 51.93% | 47.15% | 48.43% | 38.49% | 51.93% | ARCHITECTURE ISSUE: oracle <= SP. Investigation cannot improve actions on this data. VLD value limited to structured triage. |

The existing artifacts contain one evaluation run per geometry, each n=543; seed variance was not measured. Default and bootstrapped verdicts are ARCHITECTURE ISSUE (oracle action_accuracy is no better than single-pass). Trained verdict is VLD VALUE = SELECTIVE ENRICHMENT. At trained geometry, E is the top A–E strategy and exceeds A by 2.947pp, just below the preregistered 3pp boundary. The strategy-A/Phase-1b match flags are retained from the original harness.

## New K-informed action scoring (trained geometry)

Both strategies learn pairwise feature weights on 400 training alerts per seed and re-score within the category chosen by current VLD, using the same B=2 evidence vector. K-global pools learned weights across categories; K-category retains category-specific weights. The matched baseline is current VLD with the same B=2 cap and held-out 143 alerts. Existing A–E scores are retained separately and are not compared as if they were matched to these new splits.

| Strategy | action_accuracy mean ± SD | Per-seed action_accuracy (Δ vs matched A) | Seeds >3pp |
|---|---:|---|---:|
| K_global_weighted_action | 23.78% ± 2.80pp | 42: 20.98% (+2.80pp), 123: 26.57% (+2.80pp), 7: 23.78% (+1.40pp) | 0/3 |
| K_category_weighted_action | 23.08% ± 2.42pp | 42: 21.68% (+3.50pp), 123: 25.87% (+2.10pp), 7: 21.68% (-0.70pp) | 1/3 |

K-informed scoring is architecturally feasible as a standalone scorer adapter: the function can use centroid residuals, the routed category, and learned K weights without changing source or adding evidence reads. The current production path does not pass K weights into action scoring; production integration would require a separately reviewed architecture change.

## Boundary, cross-campaign context, and paper wording

Neither K strategy beat matched current-VLD B=2 by >3pp in at least two seeds. Under this test the current action-scoring boundary is not materially exceeded, but the result does not establish the geometry's absolute ceiling or rule out other learning/scoring rules.

Paper sentence: ‘Across three seeded 400/143 splits of the synthetic SOC fixture at trained geometry, the tested global and category-conditioned K-weighted action scorers did not improve held-out action_accuracy by more than 3pp in at least two seeds over matched B=2 VLD; this bounds these K-scoring variants, not all possible action models.’

C7 cross-reference: the separate VLD experiment found SOC action_accuracy +4pp from depth-3 rescoring while `routing_quality` moved only +0.33pp; C8 keeps these metrics separate. C6's Trading/S2P abstention lifts at 75% selection were +0.16pp/+0.25pp, but risk-coverage abstention is not an action-scoring ceiling experiment and does not establish a lower ceiling.

Fixture note: E-SPLIT uses all 543 alerts from `support/setup/zero_day_decisions_v5.json`, SHA-256 `1b7c30d517d29565794746209f9d3afdd5ad16dc9185ed92fe4067f1ad102032`, also used by C1's historical external-baseline comparison. The C1 ordered 400/143 split and C8's seeded shuffled 400/143 splits differ; cross-reference values are not treated as paired.

Null-stakes: a >3pp result would justify a candidate action-scoring change only for the tested trained geometry and fixture; it would not upgrade routing_quality or operational action accuracy. A null result only bounds these two K-weighted variants. Existing geometry-state outputs remain single-run and do not identify seed uncertainty.

Two independent rebuilds matched byte-for-byte for each new seed. Full per-seed weights, held-out counts, paired deltas, and rebuild hashes are in the JSON.
