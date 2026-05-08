# Design Issues v1 — Decision Index

## D-04 — OLS CUSUM reset
Decision: Option B — reset on GREEN conservation status.

Context:
- See graph-attention-engine-v50/docs/design/gae_design_v10_8.md for OLSMonitor, conservation q, AMBER/GREEN behavior, and GAE monitoring architecture.
- See graph-attention-engine-v50/docs/design/math_synopsis_v15.md for q as rolling verified accuracy.
- See gen-ai-roi-demo-v4-v50/backend/docs/design/soc_copilot_design_v5_8.md for SOC learning-health / conservation display implications.

Open semantic question:
Define exactly what “reset on GREEN” means:
1. reset only CUSUM accumulator,
2. reset alarm state,
3. reset red-day/consecutive counter,
4. reset replay epoch/dashboard-visible history,
5. or some combination.

## D-08 — DK normalization
Decision: Option A — always normalize DK weights.

Context:
- See graph-attention-engine-v50/docs/design/gae_design_v10_8.md for DiagonalKernel / DK calibration architecture.
- See graph-attention-engine-v50/docs/design/math_synopsis_v15.md for DK as discriminative precision weights and max-normalized W behavior.
- See gen-ai-roi-demo-v4-v50/backend/docs/design/soc_copilot_design_v5_8.md for SOC display / learning-state implications.

Implementation intent:
Centralize DK normalization in GAE. Decide explicitly whether external accessors return raw weights, normalized weights, or both.