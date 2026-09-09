"""E-DIM: decompose how SOC VLD evidence changes each factor dimension."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np

from app.domains.soc.config import SCORER_ACTIONS, SOC_CATEGORIES
from scripts.value_chain_experiment_lib import ExperimentContext, FACTOR_NAMES, accuracy, centroid_mode, full_distance, output_for_mode, route_category, run_async, run_vld, score_best, write_json

OUTPUT = Path("data/exp_dimension_decomposition.json")
TRAINED_OUTPUT = Path("data/exp_dimension_decomposition_trained.json")
BOOTSTRAPPED_OUTPUT = Path("data/exp_dimension_decomposition_bootstrapped.json")


async def run_experiment(*, use_trained: bool = False, use_bootstrapped: bool = False) -> dict[str, Any]:
    ctx = ExperimentContext(use_trained=use_trained, use_bootstrapped=use_bootstrapped)
    rows: list[dict[str, Any]] = []
    sp_predictions: dict[str, str] = {}
    vld_predictions: dict[str, str] = {}
    for alert in ctx.eval_alerts:
        alert_id = ctx.alert_id(alert)
        truth_action = ctx.true_action(alert)
        if truth_action is None:
            continue
        v0 = ctx.v0(alert)
        vld = await run_vld(ctx, alert)
        v_l = np.asarray(vld.v_final, dtype=np.float64)
        true_category = ctx.true_category(alert)
        true_action_index = SCORER_ACTIONS.index(truth_action)
        true_category_index = SOC_CATEGORIES.index(true_category)
        target = np.asarray(ctx.scorer.centroids[true_category_index, true_action_index], dtype=np.float64)
        routed = route_category(ctx, v0, alert)
        sp_predictions[alert_id] = str(score_best(v0, ctx)["action"])
        vld_predictions[alert_id] = vld.action
        rows.append({
            "alert_id": alert_id,
            "true_category": true_category,
            "true_action": truth_action,
            "routed_category": routed,
            "route_correct": routed == true_category,
            "vld_correct": vld.action == truth_action,
            "v0": v0,
            "v_l": v_l,
            "target": target,
            "full_before": full_distance(v0, target),
            "full_after": full_distance(v_l, target),
        })

    dimensions: list[dict[str, Any]] = []
    for dim, name in enumerate(FACTOR_NAMES):
        deltas = [float(row["v_l"][dim] - row["v0"][dim]) for row in rows]
        improved = [abs(float(row["v_l"][dim] - row["target"][dim])) < abs(float(row["v0"][dim] - row["target"][dim])) for row in rows]
        correct_route = [idx for idx, row in enumerate(rows) if row["route_correct"]]
        wrong_route = [idx for idx, row in enumerate(rows) if not row["route_correct"]]
        delta_abs = [abs(delta) for delta in deltas]
        correctness = np.asarray([1.0 if row["vld_correct"] else 0.0 for row in rows], dtype=np.float64)
        delta_arr = np.asarray(delta_abs, dtype=np.float64)
        corr = float(np.corrcoef(delta_arr, correctness)[0, 1]) if len(delta_arr) > 1 and float(np.std(delta_arr)) > 0.0 and float(np.std(correctness)) > 0.0 else None
        dimensions.append({
            "dimension": dim,
            "factor": name,
            "mean_abs_delta": float(np.mean(delta_abs)) if delta_abs else None,
            "fraction_improved": sum(improved) / float(len(improved)) if improved else None,
            "fraction_improved_correct_route": sum(improved[i] for i in correct_route) / float(len(correct_route)) if correct_route else None,
            "fraction_improved_wrong_route": sum(improved[i] for i in wrong_route) / float(len(wrong_route)) if wrong_route else None,
            "correlation_abs_delta_with_action_correct": corr,
        })

    full_improved = [row["full_after"] < row["full_before"] for row in rows]
    delta_zero = all((dim["mean_abs_delta"] or 0.0) <= 1.0e-10 for dim in dimensions)
    all_degrade = all((dim["fraction_improved"] or 0.0) < 0.5 for dim in dimensions)
    per_dim_mean = float(np.mean([float(dim["fraction_improved"] or 0.0) for dim in dimensions])) if dimensions else 0.0
    full_fraction = sum(full_improved) / float(len(full_improved)) if full_improved else None
    if delta_zero:
        diagnosis = "IMPLEMENTATION ISSUE: evidence not reaching provider"
    elif all_degrade:
        diagnosis = "HYPOTHESIS ISSUE: evidence is mostly noise against action centroids"
    elif full_fraction is not None and per_dim_mean > 0.5 and full_fraction < 0.5:
        diagnosis = "dimensional interaction: per-dimension gains do not combine into full-vector gains"
    else:
        diagnosis = "mixed dimension effects"

    report = {
        "experiment": "E-DIM",
        "centroid_mode": centroid_mode(use_trained=use_trained, use_bootstrapped=use_bootstrapped),
        "sample": {"alerts": len(rows)},
        "sp_accuracy": accuracy(sp_predictions, ctx.action_truth),
        "vld_accuracy": accuracy(vld_predictions, ctx.action_truth),
        "dimensions": dimensions,
        "full_vector": {
            "fraction_improved": full_fraction,
            "mean_before_distance": float(np.mean([row["full_before"] for row in rows])) if rows else None,
            "mean_after_distance": float(np.mean([row["full_after"] for row in rows])) if rows else None,
        },
        "self_diagnostic": diagnosis,
    }
    write_json(output_for_mode(OUTPUT, TRAINED_OUTPUT, BOOTSTRAPPED_OUTPUT, use_trained=use_trained, use_bootstrapped=use_bootstrapped), report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trained", action="store_true", help="Use data/trained_experiment_centroids.npy")
    parser.add_argument("--bootstrapped", action="store_true", help="Use data/bootstrapped_centroids.npy")
    args = parser.parse_args()
    report = run_async(run_experiment(use_trained=args.trained, use_bootstrapped=args.bootstrapped))
    print("=== E-DIM ===")
    for dim in report["dimensions"]:
        print(f"{dim['dimension']} {dim['factor']}: improved={dim['fraction_improved']} mean_abs_delta={dim['mean_abs_delta']}")
    print(f"Full-vector improved: {report['full_vector']['fraction_improved']}")
    print(f"Diagnostic: {report['self_diagnostic']}")


if __name__ == "__main__":
    main()

