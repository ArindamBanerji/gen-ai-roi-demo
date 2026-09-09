# Stage 1 Multi-Hop Evaluation

PLANTED SYNTHETIC — POSITIVE CONTROL — NOT A MEASUREMENT OF VLD VALUE ON REAL DECISIONS.

## 1. Acceptance Test

Verdict: **FAIL**

Failures:

- rho=0.50: expected delta near 0, got -0.600
- rho=0.7: expected positive delta, got 0.000
- rho=0.9: expected positive delta, got 0.000
- rho=1.0: expected positive delta, got 0.000

| rho_planted | N | Delta VLD-content_rule |
|---:|---:|---:|
| 0.30 | 4 | -1.000 |
| 0.50 | 5 | -0.600 |
| 0.70 | 8 | 0.000 |
| 0.90 | 4 | 0.000 |
| 1.00 | 4 | 0.000 |

## 2. Per-Kind Results

| Kind | Arm | Accuracy | N |
|---|---|---:|---:|
| content_keyed | breadth | 0.733 | 15 |
| content_keyed | content_rule | 0.867 | 15 |
| content_keyed | single_pass | 0.400 | 15 |
| content_keyed | vld | 0.400 | 15 |
| prerequisite | breadth | 0.800 | 10 |
| prerequisite | content_rule | 1.000 | 10 |
| prerequisite | single_pass | 0.200 | 10 |
| prerequisite | vld | 1.000 | 10 |
| score_keyed | breadth | 0.600 | 25 |
| score_keyed | content_rule | 1.000 | 25 |
| score_keyed | single_pass | 0.360 | 25 |
| score_keyed | vld | 0.720 | 25 |

## 3. Control Results

Flat controls N=5: single_pass=0.600, vld=0.600.
rho=0.50 controls N=5: VLD=0.400; chance target is 0.25 ± 0.15.

## 4. Per-rho Results (score_keyed only)

| rho_planted | Arm | Accuracy | N |
|---:|---|---:|---:|
| 0.30 | breadth | 0.750 | 4 |
| 0.30 | content_rule | 1.000 | 4 |
| 0.30 | single_pass | 0.000 | 4 |
| 0.30 | vld | 0.000 | 4 |
| 0.50 | breadth | 0.600 | 5 |
| 0.50 | content_rule | 1.000 | 5 |
| 0.50 | single_pass | 0.600 | 5 |
| 0.50 | vld | 0.400 | 5 |
| 0.70 | breadth | 0.625 | 8 |
| 0.70 | content_rule | 1.000 | 8 |
| 0.70 | single_pass | 0.500 | 8 |
| 0.70 | vld | 1.000 | 8 |
| 0.90 | breadth | 1.000 | 4 |
| 0.90 | content_rule | 1.000 | 4 |
| 0.90 | single_pass | 0.250 | 4 |
| 0.90 | vld | 1.000 | 4 |
| 1.00 | breadth | 0.000 | 4 |
| 1.00 | content_rule | 1.000 | 4 |
| 1.00 | single_pass | 0.250 | 4 |
| 1.00 | vld | 1.000 | 4 |

## 5. Deviation Note

- SOC-MH-002 route-aware correctness is supported: when ground_truth_route is present, action alone is insufficient.
- All-arms-agree instances: 10.
- Breadth beats VLD instances: 10.

## 6. Self-Diagnostics

EXP: acceptance uses content_rule as a correct-branch upper bound, so positive VLD-content deltas may be impossible under this arm definition.

## Headline

accuracy(vld) - accuracy(content_rule) on score_keyed = -0.280.
