# Campaign v6.0 Scan 3 Results

Scan 3 completed. Pipeline validation: 4/4 experiments pass.

AnalystOracle:
- known_effect=0.10
- known_accuracy_effect=0.05

Experiments:
- Exp1: lift recovered. Recovered lift=0.075 vs injected 0.10.
- Exp2: null recovered. Recovered lift=-0.015 vs injected 0.0.
- Exp3: floor N=1568 per arm. This is a gaussian lower bound; real pilot N is higher with overdispersion.
- Exp4: accuracy guard works. Recovered lift=0.075, accuracy_delta=-0.050, gate=REJECT.

Status: CLOSED.
