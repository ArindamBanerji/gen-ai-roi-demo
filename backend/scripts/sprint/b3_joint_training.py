from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.sprint.sprint_lib import evaluate_option, interpolate_mu, load_mu, run, scorer_from_mu, write_json


def main() -> None:
    default_mu = load_mu(False)
    trained_mu = load_mu(True)
    rows = []
    for i in range(11):
        alpha = i / 10.0
        scorer = scorer_from_mu(interpolate_mu(alpha, default_mu, trained_mu))
        row = run(evaluate_option(f"B3 joint alpha={alpha:.1f}", scorer, scorer, "routed"))
        row["alpha"] = alpha
        rows.append(row)
    best = max(rows, key=lambda r: (r["rho"] or 0.0 > 0.5, r["delta_vs_sp"], r["accuracy"]))
    viable = [r for r in rows if (r["rho"] or 0.0) > 0.5 and r["delta_vs_sp"] > 0]
    classification = "HYPO: joint interpolation has a viable Pareto point" if viable else "ARCH: no single interpolated tensor achieved rho>0.5 and delta>0"
    payload = {"experiment": "B3 joint training interpolation", "design_justification": "Linear interpolation maps the Pareto tradeoff between routing-shaped and action-shaped centroids without modifying production state.", "rows": rows, "best_by_delta": best, "viable_rows": viable, "classification": classification}
    write_json("data/sprint/b3_joint_training.json", payload)
    print("B3 joint training")
    print(f"viable={len(viable)}, best_alpha={best['alpha']}, best_delta={best['delta_vs_sp']:.4f}, best_rho={best['rho']:.4f}")
    print(classification)


if __name__ == "__main__":
    main()
