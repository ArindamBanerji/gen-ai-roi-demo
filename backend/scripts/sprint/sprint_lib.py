"""Shared helpers for the VLD geometry design sprint."""
from __future__ import annotations

import asyncio
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, cast

import numpy as np

from app.domains.soc.config import SCORER_ACTIONS, SOC_CATEGORIES, SOC_FACTORS, SOCDomainConfig
from app.services.investigation_patterns import PATTERN_REGISTRY
from app.services.investigation_router import InvestigationRouter
from app.services.triage_providers import build_evidence_scoped_graph
from scripts.value_chain_experiment_lib import ExperimentContext, get_experiment_scorer

SPRINT_DIR = Path("data/sprint")
SPRINT_DIR.mkdir(parents=True, exist_ok=True)
FACTOR_NAMES = list(SOC_FACTORS)
CATEGORY_NAMES = list(SOC_CATEGORIES)
ACTION_NAMES = list(SCORER_ACTIONS)


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(to_jsonable(payload), indent=2, sort_keys=True), encoding="utf-8")


def to_jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    return value


def centroid_hash(mu: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(mu, dtype=np.float64).tobytes()).hexdigest()[:16]


def load_scorer(use_trained: bool = False, use_bootstrapped: bool = False):
    return get_experiment_scorer(use_trained=use_trained, use_bootstrapped=use_bootstrapped)


def scorer_from_mu(mu: np.ndarray):
    scorer = SOCDomainConfig().build_profile_scorer()
    scorer.centroids = np.asarray(mu, dtype=float).copy()
    scorer.mu = scorer.centroids
    return scorer


def load_mu(use_trained: bool = False, use_bootstrapped: bool = False) -> np.ndarray:
    return cast(np.ndarray, np.asarray(load_scorer(use_trained=use_trained, use_bootstrapped=use_bootstrapped).centroids, dtype=float).copy())


def get_default_centroids() -> np.ndarray:
    return load_mu(False)


def get_trained_centroids() -> np.ndarray:
    return load_mu(True)


def get_bootstrapped_centroids() -> np.ndarray:
    return load_mu(use_bootstrapped=True)


def route_index_for_vector(v: np.ndarray, scorer: Any) -> int:
    router = InvestigationRouter(PATTERN_REGISTRY)
    distances = router.category_distances(np.asarray(v, dtype=float), scorer)
    cat_name = min(distances, key=distances.get)
    return CATEGORY_NAMES.index(cat_name)


def route_name_for_vector(v: np.ndarray, scorer: Any) -> str:
    return str(CATEGORY_NAMES[route_index_for_vector(v, scorer)])


def score_best_indices(v: np.ndarray, scorer: Any) -> tuple[int, int, float]:
    mu = np.asarray(scorer.centroids, dtype=float)
    vec = np.asarray(v, dtype=float).reshape(-1)
    best_c, best_a, best_d = 0, 0, float("inf")
    for c in range(mu.shape[0]):
        for a in range(mu.shape[1]):
            d = float(np.linalg.norm(vec - mu[c, a, :]))
            if d < best_d:
                best_c, best_a, best_d = c, a, d
    return best_c, best_a, best_d


def score_best_action(v: np.ndarray, scorer: Any) -> str:
    _, action_idx, _ = score_best_indices(v, scorer)
    return str(ACTION_NAMES[action_idx])


def score_in_category_action(v: np.ndarray, scorer: Any, category_idx: int) -> str:
    mu = np.asarray(scorer.centroids, dtype=float)
    distances = [float(np.linalg.norm(np.asarray(v, dtype=float) - mu[category_idx, a, :])) for a in range(mu.shape[1])]
    return str(ACTION_NAMES[int(np.argmin(distances))])


def top_dims(values: Iterable[float], n: int = 3) -> list[int]:
    return [i for i, _ in sorted(enumerate(values), key=lambda x: x[1], reverse=True)[:n]]


def centroid_geometry(mu: np.ndarray) -> dict[str, Any]:
    mu = np.asarray(mu, dtype=float)
    inter_category = []
    for c1 in range(mu.shape[0]):
        for c2 in range(c1 + 1, mu.shape[0]):
            inter_category.append(float(np.linalg.norm(mu[c1, :, :].ravel() - mu[c2, :, :].ravel())))
    inter_action_by_category: dict[str, list[float]] = {}
    inter_action = []
    for c in range(mu.shape[0]):
        vals = []
        for a1 in range(mu.shape[1]):
            for a2 in range(a1 + 1, mu.shape[1]):
                vals.append(float(np.linalg.norm(mu[c, a1, :] - mu[c, a2, :])))
        inter_action_by_category[CATEGORY_NAMES[c]] = vals
        inter_action.extend(vals)
    flat = mu.reshape((-1, mu.shape[-1]))
    cells = [(c, a) for c in range(mu.shape[0]) for a in range(mu.shape[1])]
    nearest: list[dict[str, Any]] = []
    same_category_neighbors = 0
    for i, vec in enumerate(flat):
        dists = [(j, float(np.linalg.norm(vec - other))) for j, other in enumerate(flat) if j != i]
        dists.sort(key=lambda x: x[1])
        nn = []
        for j, d in dists[:2]:
            same = cells[i][0] == cells[j][0]
            if same:
                same_category_neighbors += 1
            nn.append({"category": CATEGORY_NAMES[cells[j][0]], "action": ACTION_NAMES[cells[j][1]], "distance": d, "same_category": same})
        nearest.append({"cell": {"category": CATEGORY_NAMES[cells[i][0]], "action": ACTION_NAMES[cells[i][1]]}, "neighbors": nn})
    category_variance = []
    action_variance = []
    for d in range(mu.shape[-1]):
        category_variance.append(float(np.var(np.mean(mu[:, :, d], axis=1))))
        action_variance.append(float(np.mean(np.var(mu[:, :, d], axis=1))))
    mean_inter_category = float(np.mean(inter_category)) if inter_category else 0.0
    mean_inter_action = float(np.mean(inter_action)) if inter_action else 0.0
    return {
        "shape": list(mu.shape),
        "hash": centroid_hash(mu),
        "mean_inter_category_distance": mean_inter_category,
        "mean_inter_action_distance": mean_inter_action,
        "inter_category_to_action_ratio": mean_inter_category / mean_inter_action if mean_inter_action else math.inf,
        "inter_action_by_category_mean": {k: float(np.mean(v)) if v else 0.0 for k, v in inter_action_by_category.items()},
        "nearest_neighbors": nearest,
        "nearest_neighbor_same_category_fraction": same_category_neighbors / max(len(nearest) * 2, 1),
        "dimension_variance": [
            {"factor": FACTOR_NAMES[d], "category_variance": category_variance[d], "action_variance": action_variance[d], "category_to_action_variance_ratio": category_variance[d] / action_variance[d] if action_variance[d] else math.inf}
            for d in range(mu.shape[-1])
        ],
        "routing_dimensions": [FACTOR_NAMES[i] for i in top_dims(category_variance, n=3)],
        "action_dimensions": [FACTOR_NAMES[i] for i in top_dims(action_variance, n=3)],
    }


def eta_squared(x: np.ndarray, labels: list[int]) -> float:
    x = np.asarray(x, dtype=float)
    labels_arr = np.asarray(labels)
    grand = float(np.mean(x))
    ss_total = float(np.sum((x - grand) ** 2))
    if ss_total <= 1e-12:
        return 0.0
    ss_between = 0.0
    for label in sorted(set(labels)):
        group = x[labels_arr == label]
        if len(group):
            ss_between += float(len(group) * (float(np.mean(group)) - grand) ** 2)
    return max(0.0, min(1.0, ss_between / ss_total))


def lda_direction(vectors: np.ndarray, labels: list[int]) -> np.ndarray:
    vectors = np.asarray(vectors, dtype=float)
    labels_arr = np.asarray(labels)
    overall = np.mean(vectors, axis=0)
    means = []
    for label in sorted(set(labels)):
        group = vectors[labels_arr == label]
        if len(group):
            means.append(np.mean(group, axis=0) - overall)
    if not means:
        return cast(np.ndarray, np.zeros(vectors.shape[1]))
    mat = np.asarray(means, dtype=float)
    _, _, vt = np.linalg.svd(mat, full_matrices=False)
    return cast(np.ndarray, np.asarray(vt[0], dtype=float))


def vector_angle_degrees(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom <= 1e-12:
        return 90.0
    cos = abs(float(np.dot(a, b)) / denom)
    cos = max(-1.0, min(1.0, cos))
    return float(np.degrees(np.arccos(cos)))


def factor_decomposition(ctx: ExperimentContext) -> dict[str, Any]:
    vectors = np.asarray([ctx.vectors[ctx.alert_id(a)] for a in ctx.eval_alerts], dtype=float)
    category_labels = [CATEGORY_NAMES.index(ctx.category_truth[ctx.alert_id(a)]) for a in ctx.eval_alerts]
    action_labels = [ACTION_NAMES.index(ctx.action_truth[ctx.alert_id(a)]) for a in ctx.eval_alerts]
    category_eta = [eta_squared(vectors[:, d], category_labels) for d in range(vectors.shape[1])]
    action_eta = [eta_squared(vectors[:, d], action_labels) for d in range(vectors.shape[1])]
    routing_idx = set(top_dims(category_eta, n=3))
    action_idx = set(top_dims(action_eta, n=3))
    overlap = len(routing_idx & action_idx) / max(len(routing_idx | action_idx), 1)
    cat_dir = lda_direction(vectors, category_labels)
    act_dir = lda_direction(vectors, action_labels)
    return {
        "n_alerts": len(ctx.eval_alerts),
        "dimension_scores": [
            {"factor": FACTOR_NAMES[d], "category_eta_squared": category_eta[d], "action_eta_squared": action_eta[d]}
            for d in range(vectors.shape[1])
        ],
        "routing_dimensions": [FACTOR_NAMES[i] for i in sorted(routing_idx)],
        "action_dimensions": [FACTOR_NAMES[i] for i in sorted(action_idx)],
        "routing_dimension_indices": sorted(routing_idx),
        "action_dimension_indices": sorted(action_idx),
        "overlap": overlap,
        "lda_angle_degrees": vector_angle_degrees(cat_dir, act_dir),
        "category_direction_norm": float(np.linalg.norm(cat_dir)),
        "action_direction_norm": float(np.linalg.norm(act_dir)),
        "max_category_eta_squared": float(max(category_eta) if category_eta else 0.0),
        "max_action_eta_squared": float(max(action_eta) if action_eta else 0.0),
    }


async def vector_after_categories(ctx: ExperimentContext, alert: dict[str, Any], categories: list[str]) -> np.ndarray:
    v0 = np.asarray(ctx.vectors[ctx.alert_id(alert)], dtype=float)
    admitted: list[dict[str, Any]] = []
    v = v0.copy()
    for category in categories:
        pattern = PATTERN_REGISTRY.get(category)
        if pattern is None:
            continue
        evidence = await pattern.execute(alert, ctx.graph)
        admitted.append(evidence)
        scoped = build_evidence_scoped_graph(ctx.graph, admitted, v0)
        enriched, _metadata = await ctx.provider.compute(alert, scoped)
        v = np.asarray(enriched, dtype=float).reshape(-1)
    return cast(np.ndarray, v)


async def evaluate_option(
    name: str,
    route_scorer: Any | None,
    score_scorer: Any,
    evidence_mode: str = "routed",
    selected_dims: list[int] | None = None,
    require_route_agreement: bool = False,
) -> dict[str, Any]:
    ctx = ExperimentContext(use_trained=False)
    sp_preds: list[str] = []
    preds: list[str] = []
    truths: list[str] = []
    route_truths: list[str] = []
    routes: list[str] = []
    committed = 0
    abstained = 0
    for alert in ctx.eval_alerts:
        alert_id = ctx.alert_id(alert)
        truth = str(ctx.action_truth[alert_id])
        true_cat = str(ctx.category_truth[alert_id])
        v0 = np.asarray(ctx.vectors[alert_id], dtype=float)
        scorer_for_route = route_scorer or score_scorer
        route_cat = route_name_for_vector(v0, scorer_for_route)
        trained_route_cat = route_name_for_vector(v0, score_scorer)
        if require_route_agreement and route_cat != trained_route_cat:
            abstained += 1
            continue
        if evidence_mode == "none":
            v_eval = v0.copy()
        elif evidence_mode == "all":
            v_eval = await vector_after_categories(ctx, alert, list(PATTERN_REGISTRY))
        elif evidence_mode == "true":
            v_eval = await vector_after_categories(ctx, alert, [true_cat])
        else:
            v_eval = await vector_after_categories(ctx, alert, [route_cat])
        if selected_dims is not None:
            gated = v0.copy()
            gated[selected_dims] = v_eval[selected_dims]
            v_eval = gated
        preds.append(score_best_action(v_eval, score_scorer))
        sp_preds.append(score_best_action(v0, score_scorer))
        truths.append(truth)
        route_truths.append(true_cat)
        routes.append(route_cat)
        committed += 1
    acc = list_accuracy(preds, truths)
    sp_acc = list_accuracy(sp_preds, truths)
    rho = list_accuracy(routes, route_truths) if routes else None
    return {
        "name": name,
        "n": len(truths),
        "committed": committed,
        "abstained": abstained,
        "abstain_rate": abstained / max(len(ctx.eval_alerts), 1),
        "rho": rho,
        "accuracy": acc,
        "sp_accuracy": sp_acc,
        "delta_vs_sp": acc - sp_acc,
        "classification": classify_option(rho, acc - sp_acc, abstained / max(len(ctx.eval_alerts), 1)),
    }



def list_accuracy(predictions: list[str], truths: list[str]) -> float:
    if not truths:
        return 0.0
    return sum(1 for p, t in zip(predictions, truths) if p == t) / float(len(truths))


def classify_option(rho: float | None, delta: float, abstain_rate: float = 0.0) -> str:
    if rho is not None and rho > 0.5 and delta > 0:
        return "HYPO: resolves routing/action tension for this fixture geometry"
    if abstain_rate > 0.0 and delta > 0:
        return "HYPO: disagreement gating improves committed decisions"
    if delta > 0:
        return "HYPO: improves action scoring but routing remains weak"
    return "ARCH: this option does not recover positive action value"


def run(coro: Any) -> Any:
    return asyncio.run(coro)


def interpolate_mu(alpha: float, routing_mu: np.ndarray, action_mu: np.ndarray) -> np.ndarray:
    return cast(np.ndarray, alpha * np.asarray(routing_mu, dtype=float) + (1.0 - alpha) * np.asarray(action_mu, dtype=float))


def score_ensemble(v: np.ndarray, default_mu: np.ndarray, trained_mu: np.ndarray, beta: float) -> tuple[int, int, float]:
    best = (0, 0, math.inf)
    vec = np.asarray(v, dtype=float)
    for c in range(default_mu.shape[0]):
        for a in range(default_mu.shape[1]):
            dist = beta * float(np.linalg.norm(vec - default_mu[c, a, :])) + (1.0 - beta) * float(np.linalg.norm(vec - trained_mu[c, a, :]))
            if dist < best[2]:
                best = (c, a, dist)
    return best
