"""E-SPLIT: compare value-chain strategies that separate routing and enrichment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np

from app.domains.soc.config import SOC_CATEGORIES
from scripts.exp_dimension_decomposition import OUTPUT as DIM_OUTPUT, run_experiment as run_dim_experiment
from scripts.value_chain_experiment_lib import ExperimentContext, accuracy, centroid_mode, output_for_mode, route_category, run_async, run_vld, score_best, score_in_category, v_after_pattern, write_json

OUTPUT = Path("data/exp_split_enrichment.json")
TRAINED_OUTPUT = Path("data/exp_split_enrichment_trained.json")
BOOTSTRAPPED_OUTPUT = Path("data/exp_split_enrichment_bootstrapped.json")
PHASE1B_REPORT = Path("data/rho_measurement_report.json")


async def _selective_dims(*, use_trained: bool = False, use_bootstrapped: bool = False) -> set[int]:
    path = output_for_mode(DIM_OUTPUT, Path("data/exp_dimension_decomposition_trained.json"), Path("data/exp_dimension_decomposition_bootstrapped.json"), use_trained=use_trained, use_bootstrapped=use_bootstrapped)
    if not path.exists():
        await run_dim_experiment(use_trained=use_trained, use_bootstrapped=use_bootstrapped)
    dim_report = json.loads(path.read_text(encoding="utf-8"))
    return {int(row["dimension"]) for row in dim_report.get("dimensions", []) if (row.get("fraction_improved") or 0.0) > 0.5}


async def run_experiment(*, use_trained: bool = False, use_bootstrapped: bool = False) -> dict[str, Any]:
    ctx = ExperimentContext(use_trained=use_trained, use_bootstrapped=use_bootstrapped)
    mode = centroid_mode(use_trained=use_trained, use_bootstrapped=use_bootstrapped)
    selected_dims = await _selective_dims(use_trained=use_trained, use_bootstrapped=use_bootstrapped)
    predictions: dict[str, dict[str, str]] = {name: {} for name in ["A_current_vld", "B_route_surface", "C_selective", "D_route_selective", "E_oracle"]}
    phase1b = json.loads(PHASE1B_REPORT.read_text(encoding="utf-8"))

    for alert in ctx.eval_alerts:
        alert_id = ctx.alert_id(alert)
        if alert_id not in ctx.action_truth:
            continue
        v0 = ctx.v0(alert)
        routed = route_category(ctx, v0, alert)
        true_category = ctx.true_category(alert)
        current = await run_vld(ctx, alert)
        predictions["A_current_vld"][alert_id] = current.action
        predictions["B_route_surface"][alert_id] = str(score_in_category(v0, ctx, routed)["action"])

        v_l = np.asarray(current.v_final, dtype=np.float64)
        v_selective = v0.copy()
        for dim in selected_dims:
            v_selective[dim] = v_l[dim]
        predictions["C_selective"][alert_id] = str(score_best(v_selective, ctx)["action"])
        predictions["D_route_selective"][alert_id] = str(score_in_category(v_selective, ctx, routed)["action"])

        v_oracle = await v_after_pattern(ctx, alert, true_category)
        predictions["E_oracle"][alert_id] = str(score_in_category(v_oracle, ctx, true_category)["action"])

    single_pass_predictions = {ctx.alert_id(alert): str(score_best(ctx.v0(alert), ctx)["action"]) for alert in ctx.eval_alerts if ctx.alert_id(alert) in ctx.action_truth}
    sp_acc = accuracy(single_pass_predictions, ctx.action_truth)
    strategies: dict[str, dict[str, Any]] = {}
    for name, pred in predictions.items():
        acc = accuracy(pred, ctx.action_truth)
        strategies[name] = {
            "accuracy": acc,
            "delta_vs_sp": acc - sp_acc if acc is not None and sp_acc is not None else None,
            "n": len(pred),
        }

    a_acc = strategies["A_current_vld"]["accuracy"]
    a_matches_phase1b = bool(a_acc is not None and (mode != "default" or abs(a_acc - float(phase1b["vld_action_accuracy"])) <= 0.001))
    e_acc = strategies["E_oracle"]["accuracy"]
    b_acc = strategies["B_route_surface"]["accuracy"]
    c_acc = strategies["C_selective"]["accuracy"]
    d_acc = strategies["D_route_selective"]["accuracy"]
    if not a_matches_phase1b:
        verdict = "IMPLEMENTATION ISSUE: Strategy A does not reproduce Phase 1b. Debug required before interpreting results."
    elif e_acc is not None and sp_acc is not None and e_acc <= sp_acc:
        verdict = "ARCHITECTURE ISSUE: oracle <= SP. Investigation cannot improve actions on this data. VLD value limited to structured triage."
    elif e_acc is not None and sp_acc is not None and b_acc is not None and e_acc > sp_acc and b_acc > sp_acc:
        verdict = "VLD VALUE = CATEGORY IDENTIFICATION: Strategy B > SP. Evidence enrichment is harmful."
    elif e_acc is not None and sp_acc is not None and e_acc > sp_acc and ((c_acc is not None and c_acc > sp_acc) or (d_acc is not None and d_acc > sp_acc)):
        verdict = "VLD VALUE = SELECTIVE ENRICHMENT: selective strategy beats SP."
    elif e_acc is not None and sp_acc is not None and e_acc > sp_acc:
        verdict = "ROUTING BOTTLENECK: oracle works but no non-oracle strategy beats SP."
    else:
        verdict = "EXPERIMENT DESIGN ISSUE: insufficient interpretable strategy results."

    report = {
        "experiment": "E-SPLIT",
        "centroid_mode": mode,
        "single_pass_accuracy": sp_acc,
        "selected_dimensions_for_selective": sorted(selected_dims),
        "strategies": strategies,
        "strategy_a_matches_phase1b": a_matches_phase1b,
        "verdict": verdict,
    }
    write_json(output_for_mode(OUTPUT, TRAINED_OUTPUT, BOOTSTRAPPED_OUTPUT, use_trained=use_trained, use_bootstrapped=use_bootstrapped), report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trained", action="store_true", help="Use data/trained_experiment_centroids.npy")
    parser.add_argument("--bootstrapped", action="store_true", help="Use data/bootstrapped_centroids.npy")
    args = parser.parse_args()
    report = run_async(run_experiment(use_trained=args.trained, use_bootstrapped=args.bootstrapped))
    print("=== E-SPLIT ===")
    print(f"Single-pass: {report['single_pass_accuracy']}")
    for name, payload in report["strategies"].items():
        print(f"{name}: accuracy={payload['accuracy']} delta={payload['delta_vs_sp']}")
    print(report["verdict"])


if __name__ == "__main__":
    main()

