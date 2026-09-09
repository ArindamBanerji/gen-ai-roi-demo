from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.sprint.sprint_lib import ACTION_NAMES, ExperimentContext, list_accuracy, load_mu, score_ensemble, write_json


def evaluate_beta(beta: float) -> dict:
    ctx = ExperimentContext(use_trained=False)
    default_mu = load_mu(False)
    trained_mu = load_mu(True)
    preds = []
    trained_preds = []
    default_preds = []
    truths = []
    for alert in ctx.eval_alerts:
        v = ctx.v0(alert)
        _, a, _ = score_ensemble(v, default_mu, trained_mu, beta)
        _, a_trained, _ = score_ensemble(v, default_mu, trained_mu, 0.0)
        _, a_default, _ = score_ensemble(v, default_mu, trained_mu, 1.0)
        preds.append(ACTION_NAMES[a])
        trained_preds.append(ACTION_NAMES[a_trained])
        default_preds.append(ACTION_NAMES[a_default])
        truths.append(str(ctx.action_truth[ctx.alert_id(alert)]))
    return {"beta": beta, "accuracy": list_accuracy(preds, truths), "trained_endpoint_accuracy": list_accuracy(trained_preds, truths), "default_endpoint_accuracy": list_accuracy(default_preds, truths)}


def main() -> None:
    rows = [evaluate_beta(i / 10.0) for i in range(11)]
    best = max(rows, key=lambda r: r["accuracy"])
    payload = {
        "experiment": "B5 ensemble scoring",
        "design_justification": "Distance-level interpolation tests whether the two centroid geometries can be combined without retraining a single tensor.",
        "rows": rows,
        "best": best,
        "classification": "HYPO: distance ensemble improves scoring" if best["accuracy"] > max(rows[0]["accuracy"], rows[-1]["accuracy"]) else "ARCH: distance ensemble does not beat the endpoints",
    }
    write_json("data/sprint/b5_ensemble.json", payload)
    print("B5 ensemble")
    print(f"best_beta={best['beta']}, best_accuracy={best['accuracy']:.4f}")
    print(payload["classification"])


if __name__ == "__main__":
    main()
