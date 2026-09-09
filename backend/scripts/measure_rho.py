"""Measure SOC VLD score-keyed routing rho against comparator policies."""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
import sys
from typing import Any, Protocol, cast

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np

from app.domains.soc.config import SOC_CATEGORIES, SOCDomainConfig
from app.models.investigation import InvestigationResult
from app.services.investigation_comparators import (
    BreadthPolicy,
    ContentRulePolicy,
    MajorityBranchPolicy,
    RandomBranchPolicy,
    SinglePassPolicy,
)
from app.services.investigation_loop import InvestigationLoop
from app.services.investigation_patterns import PATTERN_REGISTRY
from app.services.investigation_router import InvestigationRouter
from scripts.generate_score_keyed_alerts import DEFAULT_FIXTURE, DEFAULT_OUTPUT, DEFAULT_TRUTH, generate_score_keyed_alerts

REPORT_PATH = Path("data/rho_measurement_report.json")


class ComparatorPolicy(Protocol):
    async def investigate(self, alert_context: dict[str, Any], scorer: Any, factor_provider: Any, graph_store: Any) -> InvestigationResult:
        ...


class FixtureGraphStore:
    def __init__(self, rows_by_alert: dict[str, dict[str, Any]] | None = None) -> None:
        self.rows_by_alert = rows_by_alert or {}
        self.queries: list[str] = []

    async def get_security_context(self, alert_id: str) -> dict[str, Any]:
        return dict(self.rows_by_alert.get(alert_id, {"alert_id": alert_id, "nodes_consulted": 1}))

    async def run_query(self, query: str) -> list[dict[str, Any]]:
        self.queries.append(query)
        return []


class FixtureFactorProvider:
    def __init__(self, vectors_by_alert: dict[str, list[float]]) -> None:
        self.vectors_by_alert = vectors_by_alert

    async def compute(self, alert: dict[str, Any], context: Any) -> tuple[np.ndarray, dict[str, dict[str, Any]]]:
        alert_id = str(alert.get("alert_id") or alert.get("id") or "")
        base = np.asarray(self.vectors_by_alert.get(alert_id, [0.5] * 6), dtype=np.float64)
        surface = getattr(context, "vld_surface_vector", None)
        evidence_vectors = getattr(context, "vld_factor_vectors", None)
        if surface is not None and evidence_vectors:
            arrays = [np.asarray(surface, dtype=np.float64)] + [np.asarray(item, dtype=np.float64) for item in evidence_vectors]
            return cast(np.ndarray, np.clip(sum(arrays) / float(len(arrays)), 0.0, 1.0)), {"fixture": {"source": "vld_evidence"}}
        return base.copy(), {"fixture": {"source": "decision_factor_vector"}}


def load_fixture(path: str | Path = DEFAULT_FIXTURE) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(Path(path).read_text(encoding="utf-8")))


def vectors_by_alert(decisions: list[dict[str, Any]]) -> dict[str, list[float]]:
    vectors: dict[str, list[float]] = {}
    for decision in decisions:
        alert_id = str(decision.get("alert_id") or "")
        vector = decision.get("factor_vector")
        if alert_id and alert_id not in vectors and isinstance(vector, list) and len(vector) == 6:
            vectors[alert_id] = [float(x) for x in vector]
    return vectors


def truth_by_alert(alerts: list[dict[str, Any]]) -> dict[str, str]:
    return {
        str(alert.get("alert_id") or alert.get("id")): str(alert.get("category"))
        for alert in alerts
        if (alert.get("alert_id") or alert.get("id")) and alert.get("category") in SOC_CATEGORIES
    }


def action_truth_by_alert(decisions: list[dict[str, Any]]) -> dict[str, str]:
    votes: dict[str, Counter[str]] = defaultdict(Counter)
    for decision in decisions:
        if decision.get("correct") is True and decision.get("action"):
            votes[str(decision.get("alert_id"))][str(decision.get("action"))] += 1
    return {alert_id: counter.most_common(1)[0][0] for alert_id, counter in votes.items() if counter}


def compute_rho(predicted: list[str], truth: list[str]) -> float | None:
    if not truth:
        return None
    correct = sum(1 for pred, actual in zip(predicted, truth) if pred == actual)
    return correct / float(len(truth))


def category_distances(v: np.ndarray, scorer: Any) -> dict[str, float]:
    return cast(dict[str, float], InvestigationRouter(PATTERN_REGISTRY).category_distances(v, scorer))


def margin_from_distances(distances: dict[str, float]) -> float:
    ordered = sorted(float(value) for value in distances.values())
    if len(ordered) < 2:
        return 0.0
    return ordered[1] - ordered[0]


def vector_skew(v0: np.ndarray, v_l: np.ndarray) -> float:
    return float(np.linalg.norm(np.asarray(v_l, dtype=np.float64) - np.asarray(v0, dtype=np.float64)))


def _percentiles(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"p25": None, "p50": None, "p75": None, "p90": None}
    arr = np.asarray(values, dtype=np.float64)
    return {"p25": float(np.percentile(arr, 25)), "p50": float(np.percentile(arr, 50)), "p75": float(np.percentile(arr, 75)), "p90": float(np.percentile(arr, 90))}


async def run_measurement(fixture_path: str | Path = DEFAULT_FIXTURE) -> dict[str, Any]:
    fixture = load_fixture(fixture_path)
    alerts = [dict(item) for item in fixture.get("alerts", []) if isinstance(item, dict)]
    decisions = [dict(item) for item in fixture.get("decisions", []) if isinstance(item, dict)]
    truth = truth_by_alert(alerts)
    vectors = vectors_by_alert(decisions)
    action_truth = action_truth_by_alert(decisions)
    eval_alerts = [alert for alert in alerts if str(alert.get("alert_id")) in truth and str(alert.get("alert_id")) in vectors]
    majority_category = Counter(truth.values()).most_common(1)[0][0] if truth else SOC_CATEGORIES[0]
    scorer = SOCDomainConfig().build_profile_scorer()
    provider = FixtureFactorProvider(vectors)
    graph = FixtureGraphStore({str(alert.get("alert_id")): alert for alert in alerts})
    router = InvestigationRouter(PATTERN_REGISTRY, L_max=3)

    routed: list[str] = []
    labels: list[str] = []
    margins: list[float] = []
    rho_by_quartile_records: list[tuple[float, bool]] = []
    content_agree = 0
    vld_results: dict[str, InvestigationResult] = {}
    single_results: dict[str, InvestigationResult] = {}
    comparator_results: dict[str, dict[str, InvestigationResult]] = {}
    comparators: dict[str, ComparatorPolicy] = {
        "single_pass": SinglePassPolicy(),
        "content_rule": ContentRulePolicy(PATTERN_REGISTRY),
        "majority_branch": MajorityBranchPolicy(majority_category, PATTERN_REGISTRY),
        "random_branch": RandomBranchPolicy(PATTERN_REGISTRY, seed=17),
        "breadth_all": BreadthPolicy(PATTERN_REGISTRY),
    }

    for alert in eval_alerts:
        alert_id = str(alert.get("alert_id"))
        v0, _ = await provider.compute(alert, graph)
        distances = router.category_distances(v0, scorer)
        route = router.route_decision(v0, scorer, set(), alert_context=alert)
        routed_category = route.selected_category or min(distances, key=distances.get)
        routed.append(routed_category)
        labels.append(truth[alert_id])
        if routed_category == truth[alert_id]:
            content_agree += 1
        margin = margin_from_distances(distances)
        margins.append(margin)
        rho_by_quartile_records.append((margin, routed_category == truth[alert_id]))
        vld = await InvestigationLoop(scorer, router, provider, L_max=3, residual_threshold=0.0).investigate(alert, graph)
        vld_results[alert_id] = vld
        single_results[alert_id] = await comparators["single_pass"].investigate(alert, scorer, provider, graph)
        comparator_results[alert_id] = {}
        for name, policy in comparators.items():
            comparator_results[alert_id][name] = await policy.investigate(alert, scorer, provider, graph)

    stripped_summary = generate_score_keyed_alerts(DEFAULT_FIXTURE, DEFAULT_OUTPUT, DEFAULT_TRUTH)
    stripped_alerts = cast(list[dict[str, Any]], json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8")))
    stripped_truth = cast(dict[str, str], json.loads(DEFAULT_TRUTH.read_text(encoding="utf-8")))
    stripped_eval = [alert for alert in stripped_alerts if str(alert.get("alert_id")) in stripped_truth and str(alert.get("alert_id")) in vectors]
    stripped_preds: list[str] = []
    stripped_labels: list[str] = []
    for alert in stripped_eval:
        v0, _ = await provider.compute(alert, graph)
        distances = router.category_distances(v0, scorer)
        route = router.route_decision(v0, scorer, set(), alert_context=alert)
        stripped_preds.append(route.selected_category or min(distances, key=distances.get))
        stripped_labels.append(stripped_truth[str(alert.get("alert_id"))])

    rho_vld = compute_rho(routed, labels)
    rho_majority = labels.count(majority_category) / float(len(labels)) if labels else None
    rho_content = 1.0 if labels else None
    rho_random_expected = 1.0 / float(len(SOC_CATEGORIES)) if labels else None
    rho_vld_scorekey = compute_rho(stripped_preds, stripped_labels)
    rho_majority_scorekey = stripped_labels.count(majority_category) / float(len(stripped_labels)) if stripped_labels else None

    action_population = [alert_id for alert_id in vld_results if alert_id in action_truth]
    action_accuracy: dict[str, float | None] = {}
    if action_population:
        for name in ["vld", *comparators.keys()]:
            correct = 0
            for alert_id in action_population:
                result = vld_results[alert_id] if name == "vld" else comparator_results[alert_id][name]
                correct += int(result.action == action_truth[alert_id])
            action_accuracy[name] = correct / float(len(action_population))
    else:
        action_accuracy = {name: None for name in ["vld", *comparators.keys()]}

    skew_values = []
    for alert in eval_alerts:
        alert_id = str(alert.get("alert_id"))
        v0 = np.asarray(vectors[alert_id], dtype=np.float64)
        skew_values.append(vector_skew(v0, np.asarray(vld_results[alert_id].v_final, dtype=np.float64)))

    quartiles: dict[str, dict[str, Any]] = {}
    if rho_by_quartile_records:
        sorted_records = sorted(rho_by_quartile_records, key=lambda item: item[0])
        chunks = np.array_split(np.asarray(sorted_records, dtype=object), 4)
        for idx, chunk in enumerate(chunks, start=1):
            if len(chunk) == 0:
                continue
            rows = list(chunk)
            quartiles[f"q{idx}"] = {
                "n": len(rows),
                "margin_min": float(min(row[0] for row in rows)),
                "margin_max": float(max(row[0] for row in rows)),
                "rho": sum(1 for _margin, ok in rows if ok) / float(len(rows)),
            }

    if rho_vld_scorekey is None or rho_majority_scorekey is None:
        gate_verdict = "INSUFFICIENT DATA"
        gate_reason = "No score-keyed labeled fixture alerts with factor vectors."
    elif rho_vld_scorekey > rho_majority_scorekey:
        gate_verdict = "PASS"
        gate_reason = "rho_VLD_scorekey beats majority baseline."
    else:
        gate_verdict = "FAIL"
        gate_reason = "rho_VLD_scorekey does not beat majority baseline."

    vld_action_accuracy = action_accuracy.get("vld")
    single_pass_accuracy = action_accuracy.get("single_pass")
    return {
        "fixture": str(fixture_path),
        "data_notes": [
            "Fixture is deterministic synthetic SOC seed data, not live production outcomes.",
            "Factor vectors are read from verified decision fixture rows keyed by alert_id to keep label-stripped alerts computable without AGE.",
            "Content-rule rho is diagnostic only because it uses the label under test.",
            "Action truth is inferred by majority vote among correct fixture decisions per alert; treat E-Delta as fixture sensitivity, not a production value claim.",
        ],
        "sample": {
            "alerts_total": len(alerts),
            "decisions_total": len(decisions),
            "eval_alerts_with_labels_and_vectors": len(eval_alerts),
            "score_keyed_alerts": len(stripped_eval),
            "action_truth_alerts": len(action_population),
            "majority_category": majority_category,
            "category_counts": dict(Counter(labels)),
            "stripped_generation": stripped_summary,
        },
        "rho_vld": rho_vld,
        "rho_vld_scorekey": rho_vld_scorekey,
        "rho_majority": rho_majority,
        "rho_majority_scorekey": rho_majority_scorekey,
        "rho_content": rho_content,
        "rho_random_expected": rho_random_expected,
        "content_keyed_fraction": content_agree / float(len(labels)) if labels else None,
        "action_accuracy": action_accuracy,
        "vld_action_accuracy": vld_action_accuracy,
        "single_pass_accuracy": single_pass_accuracy,
        "delta_depth_vs_single": _delta(vld_action_accuracy, single_pass_accuracy),
        "margin_distribution": {"percentiles": _percentiles(margins), "rho_by_quartile": quartiles},
        "mu_skew": {
            "mean": statistics.fmean(skew_values) if skew_values else None,
            "median": statistics.median(skew_values) if skew_values else None,
            "p90": float(np.percentile(np.asarray(skew_values), 90)) if skew_values else None,
        },
        "gate_verdict": gate_verdict,
        "gate_reason": gate_reason,
    }


def _delta(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return left - right


def print_report(report: dict[str, Any]) -> None:
    print("=== VLD Phase 1b rho measurement ===")
    print(f"Fixture: {report['fixture']}")
    print(f"Eval alerts: {report['sample']['eval_alerts_with_labels_and_vectors']}")
    print(f"Score-keyed alerts: {report['sample']['score_keyed_alerts']}")
    print(f"Majority category: {report['sample']['majority_category']}")
    print(f"rho_vld: {report['rho_vld']}")
    print(f"rho_vld_scorekey: {report['rho_vld_scorekey']}")
    print(f"rho_majority: {report['rho_majority']}")
    print(f"rho_majority_scorekey: {report['rho_majority_scorekey']}")
    print(f"rho_content: {report['rho_content']}")
    print(f"rho_random_expected: {report['rho_random_expected']}")
    print(f"delta_depth_vs_single: {report['delta_depth_vs_single']}")
    print(f"margin_percentiles: {report['margin_distribution']['percentiles']}")
    print(f"mu_skew: {report['mu_skew']}")
    print(f"Gate 1b: {report['gate_verdict']} - {report['gate_reason']}")
    print("Data notes:")
    for note in report["data_notes"]:
        print(f"- {note}")


async def _amain(args: argparse.Namespace) -> None:
    report = await run_measurement(args.fixture)
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
