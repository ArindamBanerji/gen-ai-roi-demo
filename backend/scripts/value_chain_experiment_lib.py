"""Shared helpers for SOC VLD value-chain experiments."""

from __future__ import annotations

import asyncio
import json
import statistics
from collections import Counter
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
from app.services.triage_providers import build_evidence_scoped_graph
from scripts.generate_score_keyed_alerts import DEFAULT_FIXTURE
from scripts.measure_rho import FixtureFactorProvider, FixtureGraphStore, action_truth_by_alert, load_fixture, vectors_by_alert

TRAINED_CENTROIDS_PATH = Path("data/trained_experiment_centroids.npy")
BOOTSTRAPPED_CENTROIDS_PATH = Path("data/bootstrapped_centroids.npy")

FACTOR_NAMES = list(getattr(SOCDomainConfig(), "factor_names", [])) or [
    "privileged_identity_context",
    "asset_criticality",
    "threat_intel_enrichment",
    "pattern_history",
    "time_anomaly",
    "device_trust",
]


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def centroid_mode(*, use_trained: bool = False, use_bootstrapped: bool = False) -> str:
    if use_bootstrapped and use_trained:
        raise ValueError("use_bootstrapped and use_trained are mutually exclusive")
    if use_bootstrapped:
        return "bootstrapped"
    if use_trained:
        return "trained"
    return "default"


def output_for_mode(default: Path, trained: Path, bootstrapped: Path, *, use_trained: bool = False, use_bootstrapped: bool = False) -> Path:
    mode = centroid_mode(use_trained=use_trained, use_bootstrapped=use_bootstrapped)
    if mode == "bootstrapped":
        return bootstrapped
    if mode == "trained":
        return trained
    return default


class ExperimentContext:
    def __init__(
        self,
        fixture_path: str | Path = DEFAULT_FIXTURE,
        *,
        use_trained: bool = False,
        use_bootstrapped: bool = False,
    ) -> None:
        self.fixture_path = Path(fixture_path)
        self.use_trained = bool(use_trained)
        self.use_bootstrapped = bool(use_bootstrapped)
        self.centroid_mode = centroid_mode(use_trained=self.use_trained, use_bootstrapped=self.use_bootstrapped)
        self.fixture = load_fixture(self.fixture_path)
        self.alerts = [dict(item) for item in self.fixture.get("alerts", []) if isinstance(item, dict)]
        self.decisions = [dict(item) for item in self.fixture.get("decisions", []) if isinstance(item, dict)]
        self.vectors = vectors_by_alert(self.decisions)
        self.action_truth = action_truth_by_alert(self.decisions)
        self.category_truth = {
            str(alert.get("alert_id")): str(alert.get("category"))
            for alert in self.alerts
            if alert.get("alert_id") and alert.get("category") in SOC_CATEGORIES and str(alert.get("alert_id")) in self.vectors
        }
        self.eval_alerts = [alert for alert in self.alerts if str(alert.get("alert_id")) in self.category_truth]
        self.scorer = get_experiment_scorer(use_trained=self.use_trained, use_bootstrapped=self.use_bootstrapped)
        self.router = InvestigationRouter(PATTERN_REGISTRY, L_max=3)
        self.provider = FixtureFactorProvider(self.vectors)
        self.graph = FixtureGraphStore({str(alert.get("alert_id")): alert for alert in self.alerts})

    def alert_id(self, alert: dict[str, Any]) -> str:
        return str(alert.get("alert_id") or alert.get("id") or "")

    def v0(self, alert: dict[str, Any]) -> np.ndarray:
        return cast(np.ndarray, np.asarray(self.vectors[self.alert_id(alert)], dtype=np.float64))

    def true_category(self, alert: dict[str, Any]) -> str:
        return str(self.category_truth[self.alert_id(alert)])

    def true_action(self, alert: dict[str, Any]) -> str | None:
        value = self.action_truth.get(self.alert_id(alert))
        return str(value) if value is not None else None


def get_experiment_scorer(*, use_trained: bool = False, use_bootstrapped: bool = False) -> Any:
    scorer = SOCDomainConfig().build_profile_scorer()
    mode = centroid_mode(use_trained=use_trained, use_bootstrapped=use_bootstrapped)
    if mode == "default":
        return scorer
    path = BOOTSTRAPPED_CENTROIDS_PATH if mode == "bootstrapped" else TRAINED_CENTROIDS_PATH
    if not path.exists():
        raise FileNotFoundError(f"{mode} centroids not found: {path}")
    mu = np.load(path)
    if mu.shape != np.asarray(scorer.centroids).shape:
        raise ValueError(f"{mode} centroid shape {mu.shape} does not match scorer shape {np.asarray(scorer.centroids).shape}")
    scorer.centroids = np.asarray(mu, dtype=np.float64).copy()
    scorer.mu = scorer.centroids
    return scorer


def score_best(v: np.ndarray, ctx: ExperimentContext) -> dict[str, Any]:
    best = ctx.router.score_best_from_centroids(np.asarray(v, dtype=np.float64), ctx.scorer)
    return {
        "category": best.category,
        "action": best.action,
        "category_index": best.category_index,
        "action_index": best.action_index,
        "distance": best.distance,
        "confidence": best.confidence,
    }


def score_in_category(v: np.ndarray, ctx: ExperimentContext, category: str) -> dict[str, Any]:
    centroids = np.asarray(ctx.scorer.centroids, dtype=np.float64)
    cat_index = SOC_CATEGORIES.index(category)
    vector = np.asarray(v, dtype=np.float64).reshape(-1)
    distances = np.linalg.norm(centroids[cat_index] - vector, axis=1)
    action_index = int(np.argmin(distances))
    return {
        "category": category,
        "action": SCORER_ACTIONS[action_index],
        "category_index": cat_index,
        "action_index": action_index,
        "distance": float(distances[action_index]),
    }


def accuracy(predictions: dict[str, str], truth: dict[str, str], ids: list[str] | None = None) -> float | None:
    population = ids if ids is not None else [key for key in predictions if key in truth]
    if not population:
        return None
    return sum(1 for key in population if predictions.get(key) == truth.get(key)) / float(len(population))


def valid_accuracy(value: float | None) -> bool:
    return value is not None and 0.0 <= value <= 1.0


def vector_has_bad_values(v: np.ndarray) -> bool:
    return bool(np.any(np.isnan(v)) or np.any(np.isinf(v)) or v.shape != (len(FACTOR_NAMES),))


def cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
    a = np.asarray(left, dtype=np.float64).reshape(-1)
    b = np.asarray(right, dtype=np.float64).reshape(-1)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom <= 1.0e-12:
        return 0.0
    return float(np.dot(a, b) / denom)


def full_distance(v: np.ndarray, target: np.ndarray) -> float:
    return float(np.linalg.norm(np.asarray(v, dtype=np.float64) - np.asarray(target, dtype=np.float64)))


async def run_vld(ctx: ExperimentContext, alert: dict[str, Any]) -> Any:
    return await InvestigationLoop(ctx.scorer, ctx.router, ctx.provider, L_max=3, residual_threshold=0.0).investigate(alert, ctx.graph)


async def v_after_pattern(ctx: ExperimentContext, alert: dict[str, Any], category: str) -> np.ndarray:
    pattern = PATTERN_REGISTRY[category]
    evidence = await pattern.execute(alert, ctx.graph)
    scoped = build_evidence_scoped_graph(ctx.graph, [evidence], ctx.v0(alert))
    v, _ = await ctx.provider.compute(alert, scoped)
    return cast(np.ndarray, np.asarray(v, dtype=np.float64).reshape(-1))


async def v_after_all_patterns(ctx: ExperimentContext, alert: dict[str, Any]) -> np.ndarray:
    surface = ctx.v0(alert)
    admitted: list[dict[str, Any]] = []
    v = surface.copy()
    for category in SOC_CATEGORIES:
        evidence = await PATTERN_REGISTRY[category].execute(alert, ctx.graph)
        admitted.append(evidence)
        scoped = build_evidence_scoped_graph(ctx.graph, admitted, surface)
        v_raw, _ = await ctx.provider.compute(alert, scoped)
        v = np.asarray(v_raw, dtype=np.float64).reshape(-1)
    return v


def route_category(ctx: ExperimentContext, v: np.ndarray, alert: dict[str, Any]) -> str:
    route = ctx.router.route_decision(v, ctx.scorer, set(), alert_context=alert)
    if route.selected_category:
        return str(route.selected_category)
    distances = ctx.router.category_distances(v, ctx.scorer)
    return str(min(distances, key=lambda category: distances[category]))


async def prediction_tables(ctx: ExperimentContext) -> dict[str, Any]:
    sp: dict[str, str] = {}
    vld: dict[str, str] = {}
    routes: dict[str, str] = {}
    vlds: dict[str, Any] = {}
    for alert in ctx.eval_alerts:
        alert_id = ctx.alert_id(alert)
        v0 = ctx.v0(alert)
        sp[alert_id] = str(score_best(v0, ctx)["action"])
        routes[alert_id] = route_category(ctx, v0, alert)
        result = await run_vld(ctx, alert)
        vlds[alert_id] = result
        vld[alert_id] = result.action
    return {"single_pass": sp, "vld": vld, "routes": routes, "vld_results": vlds}


def centroid_cell_counts(ctx: ExperimentContext) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for decision in ctx.decisions:
        category = str(decision.get("category") or "")
        action = str(decision.get("action") or "")
        if category in SOC_CATEGORIES and action in SCORER_ACTIONS:
            counts[f"{category}:{action}"] += 1
    return {f"{category}:{action}": int(counts[f"{category}:{action}"]) for category in SOC_CATEGORIES for action in SCORER_ACTIONS}


def centroid_separation(ctx: ExperimentContext) -> dict[str, float | None]:
    mu = np.asarray(ctx.scorer.centroids, dtype=np.float64)
    intra: list[float] = []
    inter: list[float] = []
    for c in range(mu.shape[0]):
        for a1 in range(mu.shape[1]):
            for a2 in range(a1 + 1, mu.shape[1]):
                intra.append(float(np.linalg.norm(mu[c, a1] - mu[c, a2])))
    for c1 in range(mu.shape[0]):
        for c2 in range(c1 + 1, mu.shape[0]):
            for a1 in range(mu.shape[1]):
                for a2 in range(mu.shape[1]):
                    inter.append(float(np.linalg.norm(mu[c1, a1] - mu[c2, a2])))
    mean_intra = statistics.fmean(intra) if intra else None
    mean_inter = statistics.fmean(inter) if inter else None
    ratio = mean_inter / mean_intra if mean_inter is not None and mean_intra is not None and mean_intra != 0.0 else None
    return {"mean_intra": mean_intra, "mean_inter": mean_inter, "inter_intra_ratio": ratio}


def action_distribution(ctx: ExperimentContext) -> dict[str, dict[str, int]]:
    out: dict[str, Counter[str]] = {category: Counter() for category in SOC_CATEGORIES}
    for alert_id, action in ctx.action_truth.items():
        category = ctx.category_truth.get(alert_id)
        if category in out:
            out[category][action] += 1
    return {category: dict(counter) for category, counter in out.items()}


def summarize_flags(flags: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "all_checks_pass": not any(flag.get("severity") == "critical" for flag in flags),
        "critical_count": sum(1 for flag in flags if flag.get("severity") == "critical"),
        "warning_count": sum(1 for flag in flags if flag.get("severity") == "warning"),
        "flags": flags,
    }


def run_async(coro: Any) -> Any:
    return asyncio.run(coro)

