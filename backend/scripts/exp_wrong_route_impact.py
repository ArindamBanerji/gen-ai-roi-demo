"""E-WRONG: characterize damage from wrong SOC VLD investigation routes."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np

from app.domains.soc.config import SOC_CATEGORIES
from scripts.value_chain_experiment_lib import ExperimentContext, accuracy, route_category, run_async, run_vld, score_best, score_in_category, v_after_all_patterns, v_after_pattern, write_json

OUTPUT = Path("data/exp_wrong_route_impact.json")
TRAINED_OUTPUT = Path("data/exp_wrong_route_impact_trained.json")


async def run_experiment(*, use_trained: bool = False) -> dict[str, Any]:
    ctx = ExperimentContext(use_trained=use_trained)
    predictions: dict[str, dict[str, str]] = {name: {} for name in ["SP", "VLD_actual", "VLD_correct_route", "VLD_no_evidence", "VLD_all_evidence"]}
    route_correct_ids: list[str] = []
    route_wrong_ids: list[str] = []
    confusion: dict[str, dict[str, int]] = {routed: {true: 0 for true in SOC_CATEGORIES} for routed in SOC_CATEGORIES}
    wrong_slice_diff = 0
    correct_route_lift = 0
    wrong_evidence_misleading = 0

    for alert in ctx.eval_alerts:
        alert_id = ctx.alert_id(alert)
        truth_action = ctx.true_action(alert)
        if truth_action is None:
            continue
        true_category = ctx.true_category(alert)
        v0 = ctx.v0(alert)
        routed = route_category(ctx, v0, alert)
        confusion[routed][true_category] += 1
        if routed == true_category:
            route_correct_ids.append(alert_id)
        else:
            route_wrong_ids.append(alert_id)

        predictions["SP"][alert_id] = str(score_best(v0, ctx)["action"])
        vld = await run_vld(ctx, alert)
        predictions["VLD_actual"][alert_id] = vld.action
        v_correct = await v_after_pattern(ctx, alert, true_category)
        predictions["VLD_correct_route"][alert_id] = str(score_best(v_correct, ctx)["action"])
        predictions["VLD_no_evidence"][alert_id] = str(score_in_category(v0, ctx, routed)["action"])
        v_all = await v_after_all_patterns(ctx, alert)
        predictions["VLD_all_evidence"][alert_id] = str(score_best(v_all, ctx)["action"])

        if routed != true_category:
            wrong_action = str(score_in_category(np.asarray(vld.v_final, dtype=np.float64), ctx, routed)["action"])
            right_action = str(score_in_category(np.asarray(vld.v_final, dtype=np.float64), ctx, true_category)["action"])
            wrong_slice_diff += int(wrong_action != right_action)
            wrong_evidence_misleading += int(vld.action != truth_action and predictions["SP"][alert_id] == truth_action)
            correct_route_lift += int(predictions["VLD_correct_route"][alert_id] == truth_action and vld.action != truth_action)

    condition_accuracy: dict[str, dict[str, float | None]] = {}
    for name, pred in predictions.items():
        condition_accuracy[name] = {
            "all": accuracy(pred, ctx.action_truth),
            "route_correct": accuracy(pred, ctx.action_truth, route_correct_ids),
            "route_wrong": accuracy(pred, ctx.action_truth, route_wrong_ids),
        }

    wrong_pairs: Counter[str] = Counter()
    for routed, row in confusion.items():
        for true, count in row.items():
            if routed != true and count:
                wrong_pairs[f"{routed}->{true}"] += count
    total_wrong = sum(wrong_pairs.values())
    dominant_pair = wrong_pairs.most_common(1)[0] if wrong_pairs else None
    diagnostics: list[str] = []
    if condition_accuracy["VLD_no_evidence"]["all"] == condition_accuracy["SP"]["all"]:
        diagnostics.append("VLD-no-evidence equals SP: route slice does not alter action or routing is not used")
    if (condition_accuracy["VLD_correct_route"]["all"] or 0.0) < (condition_accuracy["SP"]["all"] or 0.0):
        diagnostics.append("VLD-correct-route < SP: correct evidence still hurts")
    best_condition = max(condition_accuracy, key=lambda name: condition_accuracy[name]["all"] or -1.0)
    if best_condition == "VLD_all_evidence":
        diagnostics.append("VLD-all-evidence is best: breadth beats adaptive selective reading")
    if dominant_pair and total_wrong and dominant_pair[1] / float(total_wrong) > 0.5:
        diagnostics.append(f"one confusion pair dominates wrong routes: {dominant_pair[0]}")

    report = {
        "experiment": "E-WRONG",
        "centroid_mode": "trained" if use_trained else "default",
        "sample": {"route_correct": len(route_correct_ids), "route_wrong": len(route_wrong_ids)},
        "condition_accuracy": condition_accuracy,
        "confusion_matrix": confusion,
        "damage_decomposition": {
            "wrong_evidence_actively_misleading_count": wrong_evidence_misleading,
            "wrong_action_slice_diff_count": wrong_slice_diff,
            "missing_correct_evidence_count": correct_route_lift,
            "wrong_route_total": len(route_wrong_ids),
        },
        "dominant_wrong_route_pair": {"pair": dominant_pair[0], "count": dominant_pair[1]} if dominant_pair else None,
        "self_diagnostics": diagnostics,
    }
    write_json(TRAINED_OUTPUT if use_trained else OUTPUT, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trained", action="store_true", help="Use data/trained_experiment_centroids.npy")
    args = parser.parse_args()
    report = run_async(run_experiment(use_trained=args.trained))
    print("=== E-WRONG ===")
    print(f"Sample: {report['sample']}")
    for name, payload in report["condition_accuracy"].items():
        print(f"{name}: {payload}")
    print(f"Dominant wrong pair: {report['dominant_wrong_route_pair']}")
    print(f"Diagnostics: {report['self_diagnostics']}")


if __name__ == "__main__":
    main()

