from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.sprint.sprint_lib import (  # noqa: E402
    ACTION_NAMES,
    CATEGORY_NAMES,
    ExperimentContext,
    get_default_centroids,
    get_trained_centroids,
    list_accuracy,
    load_scorer,
    route_name_for_vector,
    score_best_action,
    score_best_indices,
    vector_after_categories,
    write_json,
)

PENALTY_PROFILES = {
    "SOC": {"wrong_penalty": 20.0, "abstain_cost": 1.0},
    "S2P": {"wrong_penalty": 5.0, "abstain_cost": 0.5},
    "Trading": {"wrong_penalty": 3.0, "abstain_cost": 0.3},
}
THRESHOLDS = [round(i / 20.0, 2) for i in range(21)]
EXPECTED_DUAL_ACCURACY = 0.22283609576427257


def compute_utility(correct: int, wrong: int, abstained: int, wrong_penalty: float, abstain_cost: float) -> float:
    total = correct + wrong + abstained
    if total == 0:
        return 0.0
    return (correct - wrong_penalty * wrong - abstain_cost * abstained) / float(total)


def action_margin(v: np.ndarray, trained_mu: np.ndarray) -> float:
    vector = np.asarray(v, dtype=float).reshape(-1)
    action_distances = []
    for action_idx in range(trained_mu.shape[1]):
        dist = min(float(np.linalg.norm(vector - trained_mu[category_idx, action_idx, :])) for category_idx in range(trained_mu.shape[0]))
        action_distances.append(dist)
    ordered = sorted(action_distances)
    return float(ordered[1] - ordered[0]) if len(ordered) >= 2 else 0.0


async def build_decision_rows() -> list[dict[str, Any]]:
    ctx = ExperimentContext(use_trained=False)
    default_scorer = load_scorer(False)
    trained_scorer = load_scorer(True)
    trained_mu = get_trained_centroids()
    rows = []
    for alert in ctx.eval_alerts:
        alert_id = ctx.alert_id(alert)
        v0 = ctx.v0(alert)
        true_action = str(ctx.action_truth[alert_id])
        true_category = str(ctx.category_truth[alert_id])
        default_category = route_name_for_vector(v0, default_scorer)
        trained_category = route_name_for_vector(v0, trained_scorer)
        v_dual = await vector_after_categories(ctx, alert, [default_category])
        dual_action = score_best_action(v_dual, trained_scorer)
        sp_action = score_best_action(v0, default_scorer)
        trained_sp_action = score_best_action(v0, trained_scorer)
        final_category_idx, final_action_idx, final_distance = score_best_indices(v_dual, trained_scorer)
        rows.append(
            {
                "alert_id": alert_id,
                "true_action": true_action,
                "true_category": true_category,
                "default_category": default_category,
                "trained_category": trained_category,
                "final_category": CATEGORY_NAMES[final_category_idx],
                "final_action": ACTION_NAMES[final_action_idx],
                "final_distance": final_distance,
                "dual_action": dual_action,
                "sp_action": sp_action,
                "trained_sp_action": trained_sp_action,
                "margin": action_margin(v_dual, trained_mu),
                "geometry_disagrees": default_category != trained_category,
                "dual_correct": dual_action == true_action,
                "sp_correct": sp_action == true_action,
                "trained_sp_correct": trained_sp_action == true_action,
            }
        )
    return rows


def summarize_strategy(name: str, threshold: float, rows: list[dict[str, Any]], *, use_margin: bool, use_disagreement: bool) -> dict[str, Any]:
    committed_rows = []
    abstained_rows = []
    for row in rows:
        abstain = False
        if use_disagreement and row["geometry_disagrees"]:
            abstain = True
        if use_margin and row["margin"] < threshold:
            abstain = True
        if abstain:
            abstained_rows.append(row)
        else:
            committed_rows.append(row)
    correct = sum(1 for row in committed_rows if row["dual_correct"])
    wrong = len(committed_rows) - correct
    sp_correct = sum(1 for row in committed_rows if row["sp_correct"])
    dual_accuracy = list_accuracy([str(row["dual_action"]) for row in committed_rows], [str(row["true_action"]) for row in committed_rows])
    sp_accuracy = list_accuracy([str(row["sp_action"]) for row in committed_rows], [str(row["true_action"]) for row in committed_rows])
    utilities = {
        profile: compute_utility(correct, wrong, len(abstained_rows), params["wrong_penalty"], params["abstain_cost"])
        for profile, params in PENALTY_PROFILES.items()
    }
    return {
        "strategy": name,
        "threshold": threshold,
        "committed": len(committed_rows),
        "abstained": len(abstained_rows),
        "abstain_rate": len(abstained_rows) / max(len(rows), 1),
        "accuracy": dual_accuracy,
        "sp_accuracy_committed": sp_accuracy,
        "delta_vs_sp_committed": dual_accuracy - sp_accuracy,
        "delta_vs_dual_always": dual_accuracy - EXPECTED_DUAL_ACCURACY,
        "correct": correct,
        "wrong": wrong,
        "sp_correct_committed": sp_correct,
        "utility": utilities,
    }


def disagreement_characterization(rows: list[dict[str, Any]]) -> dict[str, Any]:
    disagreements = [row for row in rows if row["geometry_disagrees"]]
    agreements = [row for row in rows if not row["geometry_disagrees"]]
    matrix: dict[str, dict[str, int]] = {left: {right: 0 for right in CATEGORY_NAMES} for left in CATEGORY_NAMES}
    for row in disagreements:
        matrix[str(row["default_category"])][str(row["trained_category"])] += 1
    pair_counts: defaultdict[str, int] = defaultdict(int)
    for row in disagreements:
        pair_counts[f"{row['default_category']}->{row['trained_category']}"] += 1
    dominant = sorted(pair_counts.items(), key=lambda item: item[1], reverse=True)[:5]
    return {
        "total": len(rows),
        "disagreement_count": len(disagreements),
        "disagreement_rate": len(disagreements) / max(len(rows), 1),
        "agreement_count": len(agreements),
        "vld_accuracy_on_disagreement": list_accuracy([str(row["dual_action"]) for row in disagreements], [str(row["true_action"]) for row in disagreements]),
        "sp_accuracy_on_disagreement": list_accuracy([str(row["sp_action"]) for row in disagreements], [str(row["true_action"]) for row in disagreements]),
        "vld_accuracy_on_agreement": list_accuracy([str(row["dual_action"]) for row in agreements], [str(row["true_action"]) for row in agreements]),
        "sp_accuracy_on_agreement": list_accuracy([str(row["sp_action"]) for row in agreements], [str(row["true_action"]) for row in agreements]),
        "confusion_matrix_default_route_to_trained_route": matrix,
        "dominant_pairs": [{"pair": pair, "count": count} for pair, count in dominant],
        "signal_interpretation": "informative" if disagreements and list_accuracy([str(row["dual_action"]) for row in disagreements], [str(row["true_action"]) for row in disagreements]) < list_accuracy([str(row["dual_action"]) for row in agreements], [str(row["true_action"]) for row in agreements]) else "weak_or_noisy",
    }


def baseline_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    dual_acc = list_accuracy([str(row["dual_action"]) for row in rows], [str(row["true_action"]) for row in rows])
    sp_acc = list_accuracy([str(row["sp_action"]) for row in rows], [str(row["true_action"]) for row in rows])
    trained_sp_acc = list_accuracy([str(row["trained_sp_action"]) for row in rows], [str(row["true_action"]) for row in rows])
    correct_dual = sum(1 for row in rows if row["dual_correct"])
    wrong_dual = len(rows) - correct_dual
    correct_sp = sum(1 for row in rows if row["sp_correct"])
    wrong_sp = len(rows) - correct_sp
    return {
        "single_pass_phase1b_accuracy": sp_acc,
        "trained_single_pass_accuracy": trained_sp_acc,
        "dual_centroid_always_accuracy": dual_acc,
        "dual_centroid_matches_sprint": abs(dual_acc - EXPECTED_DUAL_ACCURACY) <= 0.001,
        "dual_centroid_always_utility": {
            profile: compute_utility(correct_dual, wrong_dual, 0, params["wrong_penalty"], params["abstain_cost"])
            for profile, params in PENALTY_PROFILES.items()
        },
        "single_pass_always_utility": {
            profile: compute_utility(correct_sp, wrong_sp, 0, params["wrong_penalty"], params["abstain_cost"])
            for profile, params in PENALTY_PROFILES.items()
        },
    }


def classify(best_soc: dict[str, Any], baseline: dict[str, Any], disagreement: dict[str, Any]) -> str:
    dual_soc = float(baseline["dual_centroid_always_utility"]["SOC"])
    best_soc_utility = float(best_soc["utility"]["SOC"])
    if best_soc_utility <= dual_soc:
        return "ABSTENTION DOESN'T HELP"
    if disagreement["signal_interpretation"] == "weak_or_noisy" and best_soc["strategy"] == "disagreement":
        return "DISAGREEMENT IS NOISE"
    return "ABSTENTION IMPROVES"


async def run_experiment() -> dict[str, Any]:
    rows = await build_decision_rows()
    baseline = baseline_summary(rows)
    strategy_rows = []
    for threshold in THRESHOLDS:
        strategy_rows.append(summarize_strategy("margin", threshold, rows, use_margin=True, use_disagreement=False))
        strategy_rows.append(summarize_strategy("disagreement", threshold, rows, use_margin=False, use_disagreement=True))
        strategy_rows.append(summarize_strategy("combined", threshold, rows, use_margin=True, use_disagreement=True))
    best_soc = max(strategy_rows, key=lambda row: row["utility"]["SOC"])
    disagreement = disagreement_characterization(rows)
    payload = {
        "experiment": "Dual-Centroid + Abstention",
        "thresholds": THRESHOLDS,
        "penalty_profiles": PENALTY_PROFILES,
        "baseline": baseline,
        "strategies": strategy_rows,
        "best_soc": best_soc,
        "disagreement_characterization": disagreement,
        "classification": classify(best_soc, baseline, disagreement),
        "self_diagnostics": {
            "impl_dual_accuracy_matches_sprint": baseline["dual_centroid_matches_sprint"],
            "exp_strategies_differentiate": len({round(row["accuracy"], 6) for row in strategy_rows}) > 1,
            "hypo_disagreement_predicts_lower_vld_accuracy": disagreement["signal_interpretation"] == "informative",
            "arch_best_soc_utility_positive": best_soc["utility"]["SOC"] > 0,
        },
    }
    return payload


def main() -> None:
    import asyncio

    payload = asyncio.run(run_experiment())
    write_json("data/sprint/combined_dual_abstain.json", payload)
    print("Dual-Centroid + Abstention")
    print(f"dual_accuracy={payload['baseline']['dual_centroid_always_accuracy']:.4f}")
    print(f"sp_phase1b_accuracy={payload['baseline']['single_pass_phase1b_accuracy']:.4f}")
    best = payload["best_soc"]
    print(f"best_soc={best['strategy']} threshold={best['threshold']} utility={best['utility']['SOC']:.4f} accuracy={best['accuracy']:.4f} abstain_rate={best['abstain_rate']:.4f}")
    disagreement = payload["disagreement_characterization"]
    print(f"disagreement_rate={disagreement['disagreement_rate']:.4f} vld_disagreement_acc={disagreement['vld_accuracy_on_disagreement']:.4f} sp_disagreement_acc={disagreement['sp_accuracy_on_disagreement']:.4f}")
    print(payload["classification"])


if __name__ == "__main__":
    main()
