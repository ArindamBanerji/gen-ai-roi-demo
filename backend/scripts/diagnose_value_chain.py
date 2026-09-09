"""Diagnose the SOC VLD value chain on Phase 1b fixture data."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter, defaultdict
from pathlib import Path
import sys
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np

from app.domains.soc.config import SCORER_ACTIONS, SOC_CATEGORIES, SOCDomainConfig
from app.services.investigation_loop import InvestigationLoop
from app.services.investigation_patterns import PATTERN_REGISTRY
from app.services.investigation_router import InvestigationRouter
from scripts.generate_score_keyed_alerts import DEFAULT_FIXTURE
from scripts.measure_rho import FixtureFactorProvider, FixtureGraphStore, action_truth_by_alert, load_fixture, vectors_by_alert

REPORT_PATH = Path("data/value_chain_diagnostic_report.json")


def score_best(v: np.ndarray, scorer: Any) -> dict[str, Any]:
    centroids_raw = getattr(scorer, "centroids", None)
    if centroids_raw is None:
        centroids_raw = getattr(scorer, "mu", None)
    if centroids_raw is None:
        raise ValueError("scorer does not expose centroids/mu")
    centroids = np.asarray(centroids_raw, dtype=np.float64)
    vector = np.asarray(v, dtype=np.float64).reshape(-1)
    best_cat = 0
    best_act = 0
    best_d = float("inf")
    for cat_idx in range(centroids.shape[0]):
        for action_idx in range(centroids.shape[1]):
            distance = float(np.linalg.norm(vector - centroids[cat_idx, action_idx]))
            if distance < best_d:
                best_cat = cat_idx
                best_act = action_idx
                best_d = distance
    return {
        "category": SOC_CATEGORIES[best_cat],
        "action": SCORER_ACTIONS[best_act],
        "category_index": best_cat,
        "action_index": best_act,
        "distance": best_d,
    }


def score_in_category(v: np.ndarray, scorer: Any, category: str) -> dict[str, Any]:
    centroids_raw = getattr(scorer, "centroids", None)
    if centroids_raw is None:
        centroids_raw = getattr(scorer, "mu", None)
    if centroids_raw is None:
        raise ValueError("scorer does not expose centroids/mu")
    centroids = np.asarray(centroids_raw, dtype=np.float64)
    cat_idx = SOC_CATEGORIES.index(category)
    vector = np.asarray(v, dtype=np.float64).reshape(-1)
    distances = np.linalg.norm(centroids[cat_idx] - vector, axis=1)
    action_idx = int(np.argmin(distances))
    return {
        "category": category,
        "action": SCORER_ACTIONS[action_idx],
        "category_index": cat_idx,
        "action_index": action_idx,
        "distance": float(distances[action_idx]),
    }


def _accuracy(predictions: dict[str, str], truth: dict[str, str], ids: list[str] | None = None) -> float | None:
    population = ids if ids is not None else [key for key in predictions if key in truth]
    if not population:
        return None
    return sum(1 for key in population if predictions.get(key) == truth.get(key)) / float(len(population))


def _delta(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return left - right


def _factor_dimension_effects(records: list[dict[str, Any]], scorer: Any) -> list[dict[str, Any]]:
    centroids_raw = getattr(scorer, "centroids", None)
    if centroids_raw is None:
        centroids_raw = getattr(scorer, "mu", None)
    if centroids_raw is None:
        raise ValueError("scorer does not expose centroids/mu")
    centroids = np.asarray(centroids_raw, dtype=np.float64)
    effects: list[dict[str, Any]] = []
    for dim in range(centroids.shape[2]):
        closer = 0
        further = 0
        unchanged = 0
        deltas: list[float] = []
        for record in records:
            true_category = record["true_category"]
            true_idx = SOC_CATEGORIES.index(true_category)
            final_action_idx = SCORER_ACTIONS.index(record["best_action"])
            target = float(centroids[true_idx, final_action_idx, dim])
            before = abs(float(record["v0"][dim]) - target)
            after = abs(float(record["v_l"][dim]) - target)
            delta = after - before
            deltas.append(delta)
            if delta < -1.0e-9:
                closer += 1
            elif delta > 1.0e-9:
                further += 1
            else:
                unchanged += 1
        effects.append(
            {
                "dimension": dim,
                "mean_after_minus_before_abs_error": float(np.mean(deltas)) if deltas else None,
                "closer_count": closer,
                "further_count": further,
                "unchanged_count": unchanged,
            }
        )
    return effects


async def run_diagnostic(fixture_path: str | Path = DEFAULT_FIXTURE) -> dict[str, Any]:
    fixture = load_fixture(fixture_path)
    alerts = [dict(item) for item in fixture.get("alerts", []) if isinstance(item, dict)]
    decisions = [dict(item) for item in fixture.get("decisions", []) if isinstance(item, dict)]
    vectors = vectors_by_alert(decisions)
    action_truth = action_truth_by_alert(decisions)
    category_truth = {
        str(alert.get("alert_id")): str(alert.get("category"))
        for alert in alerts
        if alert.get("alert_id") and alert.get("category") in SOC_CATEGORIES and str(alert.get("alert_id")) in vectors
    }
    eval_alerts = [alert for alert in alerts if str(alert.get("alert_id")) in category_truth]
    scorer = SOCDomainConfig().build_profile_scorer()
    router = InvestigationRouter(PATTERN_REGISTRY, L_max=3)
    provider = FixtureFactorProvider(vectors)
    graph = FixtureGraphStore({str(alert.get("alert_id")): alert for alert in alerts})

    sp_predictions: dict[str, str] = {}
    vld_current_predictions: dict[str, str] = {}
    best_predictions: dict[str, str] = {}
    initial_routed_predictions: dict[str, str] = {}
    last_routed_predictions: dict[str, str] = {}
    true_slice_predictions: dict[str, str] = {}
    content_enriched_predictions: dict[str, str] = {}
    records: list[dict[str, Any]] = []
    routing_correct_ids: list[str] = []
    routing_wrong_ids: list[str] = []

    for alert in eval_alerts:
        alert_id = str(alert.get("alert_id"))
        v0 = np.asarray(vectors[alert_id], dtype=np.float64)
        initial_route = router.route_decision(v0, scorer, set(), alert_context=alert)
        routed_category = initial_route.selected_category or min(router.category_distances(v0, scorer), key=router.category_distances(v0, scorer).get)
        vld = await InvestigationLoop(scorer, router, provider, L_max=3, residual_threshold=0.0).investigate(alert, graph)
        v_l = np.asarray(vld.v_final, dtype=np.float64)
        last_routed_category = vld.investigated_category or routed_category
        best = score_best(v_l, scorer)
        in_routed = score_in_category(v_l, scorer, routed_category)
        in_last_routed = score_in_category(v_l, scorer, last_routed_category)
        in_true = score_in_category(v_l, scorer, category_truth[alert_id])
        sp = score_best(v0, scorer)
        content_pattern = PATTERN_REGISTRY.get(category_truth[alert_id])
        if content_pattern is not None:
            evidence = await content_pattern.execute(alert, graph)
            from app.services.triage_providers import build_evidence_scoped_graph
            ev_graph = build_evidence_scoped_graph(graph, [evidence], v0)
            v_content, _ = await provider.compute(alert, ev_graph)
            content_best = score_best(np.asarray(v_content, dtype=np.float64), scorer)
            content_enriched_predictions[alert_id] = str(content_best["action"])
        sp_predictions[alert_id] = str(sp["action"])
        vld_current_predictions[alert_id] = vld.action
        best_predictions[alert_id] = str(best["action"])
        initial_routed_predictions[alert_id] = str(in_routed["action"])
        last_routed_predictions[alert_id] = str(in_last_routed["action"])
        true_slice_predictions[alert_id] = str(in_true["action"])
        if routed_category == category_truth[alert_id]:
            routing_correct_ids.append(alert_id)
        else:
            routing_wrong_ids.append(alert_id)
        records.append(
            {
                "alert_id": alert_id,
                "true_category": category_truth[alert_id],
                "routed_category": routed_category,
                "last_investigated_category": last_routed_category,
                "vld_result_category": vld.category,
                "sp_action": sp["action"],
                "vld_current_action": vld.action,
                "best_action": best["action"],
                "routed_action": in_routed["action"],
                "last_routed_action": in_last_routed["action"],
                "true_slice_action": in_true["action"],
                "v0": [float(x) for x in v0.tolist()],
                "v_l": [float(x) for x in v_l.tolist()],
            }
        )

    h1_sp_accuracy = _accuracy(sp_predictions, action_truth)
    h2_best_accuracy = _accuracy(best_predictions, action_truth)
    h2_initial_routed_accuracy = _accuracy(initial_routed_predictions, action_truth)
    h2_last_routed_accuracy = _accuracy(last_routed_predictions, action_truth)
    current_vld_accuracy = _accuracy(vld_current_predictions, action_truth)
    score_best_matches_current = (
        sum(1 for alert_id, action in best_predictions.items() if vld_current_predictions.get(alert_id) == action) / float(len(best_predictions))
        if best_predictions
        else None
    )
    h3_content_accuracy = _accuracy(content_enriched_predictions, action_truth)
    h4_vld_right = _accuracy(best_predictions, action_truth, routing_correct_ids)
    h4_vld_wrong = _accuracy(best_predictions, action_truth, routing_wrong_ids)
    h4_sp_right = _accuracy(sp_predictions, action_truth, routing_correct_ids)
    h4_sp_wrong = _accuracy(sp_predictions, action_truth, routing_wrong_ids)
    h5_wrong_slice = _accuracy(initial_routed_predictions, action_truth, routing_wrong_ids)
    h5_true_slice = _accuracy(true_slice_predictions, action_truth, routing_wrong_ids)
    h2_hypothetical_lift = _delta(h2_best_accuracy, h2_last_routed_accuracy)
    h2_live_confirmed = (
        h2_hypothetical_lift is not None
        and h2_hypothetical_lift > 0.0
        and (score_best_matches_current is None or score_best_matches_current < 0.999)
    )

    report = {
        "fixture": str(fixture_path),
        "sample": {
            "alerts": len(alerts),
            "eval_alerts": len(eval_alerts),
            "action_truth_alerts": len(action_truth),
            "routing_correct": len(routing_correct_ids),
            "routing_wrong": len(routing_wrong_ids),
        },
        "hypotheses": {
            "H1_single_pass_sufficient": {
                "sp_accuracy": h1_sp_accuracy,
                "confirmed": bool(h1_sp_accuracy is not None and h1_sp_accuracy > 0.7),
            },
            "H2_scoring_locked_to_routed_category": {
                "score_best_accuracy": h2_best_accuracy,
                "score_in_initial_routed_accuracy": h2_initial_routed_accuracy,
                "score_in_last_investigated_accuracy": h2_last_routed_accuracy,
                "hypothetical_lift_best_minus_last_investigated": h2_hypothetical_lift,
                "current_vld_matches_score_best": score_best_matches_current,
                "confirmed": h2_live_confirmed,
                "interpretation": (
                    "current implementation is locked to the investigated category"
                    if h2_live_confirmed
                    else "current implementation already emits score-best; routed-category lock is not the live cause"
                ),
            },
            "H3_reextraction_dilutes": {
                "single_pass_accuracy": h1_sp_accuracy,
                "content_rule_enriched_accuracy": h3_content_accuracy,
                "confirmed": bool(h3_content_accuracy is not None and h1_sp_accuracy is not None and h3_content_accuracy < h1_sp_accuracy),
            },
            "H4_wrong_routing_damage": {
                "vld_accuracy_when_routing_correct": h4_vld_right,
                "vld_accuracy_when_routing_wrong": h4_vld_wrong,
                "sp_accuracy_same_correct_split": h4_sp_right,
                "sp_accuracy_same_wrong_split": h4_sp_wrong,
                "confirmed": bool(h4_vld_wrong is not None and h4_vld_right is not None and h4_vld_wrong < h4_vld_right),
            },
            "H5_wrong_category_action_space": {
                "wrong_route_score_in_wrong_slice_accuracy": h5_wrong_slice,
                "wrong_route_score_in_true_slice_accuracy": h5_true_slice,
                "lift_true_minus_wrong_slice": _delta(h5_true_slice, h5_wrong_slice),
                "confirmed": bool(h5_true_slice is not None and h5_wrong_slice is not None and h5_true_slice > h5_wrong_slice),
            },
        },
        "current_vld_action_accuracy": current_vld_accuracy,
        "score_best_matches_current_vld_actions": score_best_matches_current,
        "factor_dimension_analysis": _factor_dimension_effects(records, scorer),
        "synthetic_comparison": {
            "synthetic_claim": "H2 scoring locked to routed category was likely cause.",
            "real_data_result": "H2 confirmed" if h2_live_confirmed else "H2 not confirmed",
        },
        "conclusion": (
            "H2 confirmed on fixture data; current VLD is locked to the investigated category."
            if h2_live_confirmed
            else "H2 not confirmed on fixture data; current VLD action already matches score-best. Negative delta is driven by evidence/re-extraction and routing-interaction effects."
        ),
    }
    return report


def print_report(report: dict[str, Any]) -> None:
    print("=== VLD value-chain diagnostic on Phase 1b data ===")
    print(f"Fixture: {report['fixture']}")
    print(f"Eval alerts: {report['sample']['eval_alerts']}")
    for name, payload in report["hypotheses"].items():
        print(f"{name}: {payload}")
    print(f"current_vld_action_accuracy: {report['current_vld_action_accuracy']}")
    print(f"score_best_matches_current_vld_actions: {report['score_best_matches_current_vld_actions']}")
    print(f"Synthetic said H2. Real data says {report['synthetic_comparison']['real_data_result']}.")
    print(f"Conclusion: {report['conclusion']}")


async def _amain(args: argparse.Namespace) -> None:
    report = await run_diagnostic(args.fixture)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print_report(report)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE))
    parser.add_argument("--output", default=str(REPORT_PATH))
    args = parser.parse_args()
    asyncio.run(_amain(args))


if __name__ == "__main__":
    main()
