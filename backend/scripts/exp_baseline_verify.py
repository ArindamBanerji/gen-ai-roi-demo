"""E-BASELINE: verify Phase 1b value-chain baseline numbers and scorer sanity."""

from __future__ import annotations

import json
import argparse
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np

from app.domains.soc.config import SCORER_ACTIONS, SOC_CATEGORIES
from scripts.value_chain_experiment_lib import (
    ExperimentContext,
    action_distribution,
    accuracy,
    centroid_cell_counts,
    centroid_mode,
    centroid_separation,
    output_for_mode,
    prediction_tables,
    run_async,
    score_best,
    vector_has_bad_values,
    write_json,
)

OUTPUT = Path("data/exp_baseline_verification.json")
TRAINED_OUTPUT = Path("data/exp_baseline_verification_trained.json")
BOOTSTRAPPED_OUTPUT = Path("data/exp_baseline_verification_bootstrapped.json")
PHASE1B_REPORT = Path("data/rho_measurement_report.json")
TRAINED_META = Path("data/trained_centroids_metadata.json")
BOOTSTRAPPED_META = Path("data/bootstrapped_centroids_metadata.json")
TOL = 0.001


async def run_experiment(*, use_trained: bool = False, use_bootstrapped: bool = False) -> dict[str, Any]:
    ctx = ExperimentContext(use_trained=use_trained, use_bootstrapped=use_bootstrapped)
    mode = centroid_mode(use_trained=use_trained, use_bootstrapped=use_bootstrapped)
    phase1b = json.loads(PHASE1B_REPORT.read_text(encoding="utf-8"))
    predictions = await prediction_tables(ctx)
    sp_accuracy = accuracy(predictions["single_pass"], ctx.action_truth)
    vld_accuracy = accuracy(predictions["vld"], ctx.action_truth)
    route_accuracy = accuracy(predictions["routes"], ctx.category_truth)
    checks: list[dict[str, Any]] = []

    checks.append({
        "check": "sp_accuracy_recompute",
        "expected": phase1b.get("single_pass_accuracy") if mode == "default" else f"{mode}_mode_no_phase1b_match_required",
        "actual": sp_accuracy,
        "passed": sp_accuracy is not None and (mode != "default" or abs(sp_accuracy - float(phase1b.get("single_pass_accuracy"))) <= TOL),
    })
    checks.append({
        "check": "vld_accuracy_recompute",
        "expected": phase1b.get("vld_action_accuracy") if mode == "default" else f"{mode}_mode_no_phase1b_match_required",
        "actual": vld_accuracy,
        "passed": vld_accuracy is not None and (mode != "default" or abs(vld_accuracy - float(phase1b.get("vld_action_accuracy"))) <= TOL),
    })

    samples: list[dict[str, Any]] = []
    bad_vectors = 0
    for alert in ctx.eval_alerts[:10]:
        alert_id = ctx.alert_id(alert)
        v0 = ctx.v0(alert)
        vld = predictions["vld_results"][alert_id]
        v_l = np.asarray(vld.v_final, dtype=np.float64)
        if vector_has_bad_values(v0) or vector_has_bad_values(v_l):
            bad_vectors += 1
        nearest0 = score_best(v0, ctx)
        nearest_l = score_best(v_l, ctx)
        samples.append({
            "alert_id": alert_id,
            "v0": [float(x) for x in v0.tolist()],
            "v_l": [float(x) for x in v_l.tolist()],
            "l2_delta": float(np.linalg.norm(v_l - v0)),
            "nearest_v0": nearest0,
            "nearest_v_l": nearest_l,
        })
    checks.append({"check": "factor_vector_sanity", "bad_vectors": bad_vectors, "passed": bad_vectors == 0})

    centroid_failures: list[dict[str, Any]] = []
    for category in SOC_CATEGORIES:
        c = SOC_CATEGORIES.index(category)
        for action in SCORER_ACTIONS:
            a = SCORER_ACTIONS.index(action)
            scored = score_best(np.asarray(ctx.scorer.centroids[c, a], dtype=np.float64), ctx)
            if scored["category"] != category or scored["action"] != action:
                centroid_failures.append({"category": category, "action": action, "scored": scored})
    checks.append({"check": "scorer_centroid_sanity", "failures": centroid_failures, "passed": not centroid_failures})

    verified_outcomes = len(ctx.action_truth)
    checks.append({"check": "verified_outcome_count", "actual": verified_outcomes, "passed": verified_outcomes > 0})

    separation = centroid_separation(ctx)
    meta_path = BOOTSTRAPPED_META if use_bootstrapped else TRAINED_META
    if mode != "default" and meta_path.exists():
        loaded_meta = json.loads(meta_path.read_text(encoding="utf-8"))
        separation["training_inter_intra_ratio"] = float(loaded_meta["inter_intra_ratio"])
        ratio = separation["training_inter_intra_ratio"]
    else:
        ratio = separation.get("inter_intra_ratio")
    checks.append({
        "check": "centroid_quality_inter_intra",
        "actual": ratio,
        "threshold": 1.5,
        "passed": bool(ratio is not None and ratio >= 1.5),
        "issue_category": "EXPERIMENT DESIGN ISSUE" if ratio is None or ratio < 1.5 else None,
    })

    per_category_actions = action_distribution(ctx)
    degenerate = [category for category, counts in per_category_actions.items() if sum(counts.values()) > 0 and len(counts) <= 1]
    checks.append({
        "check": "action_distribution_per_category",
        "degenerate_categories": degenerate,
        "passed": not degenerate,
        "issue_category": "EXPERIMENT DESIGN ISSUE" if degenerate else None,
    })

    report = {
        "experiment": "E-BASELINE",
        "centroid_mode": mode,
        "fixture": str(ctx.fixture_path),
        "sample": {"alerts": len(ctx.alerts), "eval_alerts": len(ctx.eval_alerts), "verified_outcomes": verified_outcomes},
        "sp_accuracy": sp_accuracy,
        "vld_accuracy": vld_accuracy,
        "rho_scorekey": route_accuracy,
        "checks": checks,
        "all_checks_pass": all(bool(check["passed"]) for check in checks),
        "factor_vector_samples": samples,
        "centroid_separation": separation,
        "centroid_cell_counts": centroid_cell_counts(ctx),
        "action_distribution_per_category": per_category_actions,
    }
    write_json(output_for_mode(OUTPUT, TRAINED_OUTPUT, BOOTSTRAPPED_OUTPUT, use_trained=use_trained, use_bootstrapped=use_bootstrapped), report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trained", action="store_true", help="Use data/trained_experiment_centroids.npy")
    parser.add_argument("--bootstrapped", action="store_true", help="Use data/bootstrapped_centroids.npy")
    args = parser.parse_args()
    report = run_async(run_experiment(use_trained=args.trained, use_bootstrapped=args.bootstrapped))
    print("=== E-BASELINE ===")
    print(f"SP accuracy: {report['sp_accuracy']}")
    print(f"VLD accuracy: {report['vld_accuracy']}")
    print(f"rho_scorekey: {report['rho_scorekey']}")
    print(f"All checks pass: {report['all_checks_pass']}")
    for check in report["checks"]:
        print(f"- {check['check']}: {check['passed']}")


if __name__ == "__main__":
    main()

