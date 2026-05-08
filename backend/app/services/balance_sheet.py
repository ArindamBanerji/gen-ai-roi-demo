from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

_log = logging.getLogger(__name__)

import numpy as np

from gae.snr import compute_snr_report

from app.domains.soc.config import SCORER_ACTIONS, SOC_CATEGORIES, SOC_FACTORS, SOC_FACTOR_SIGMA
from app.services.gae_state import build_centroid_export, get_profile_scorer
from app.services.iks import compute_visible_iks
from app.services.learning_health import LearningHealthMonitor
from app.services.time_machine import get_evolution_timeline
from app.state.graph_snapshot import get_snapshot

_CEILING_NOTE = (
    "Ceiling values are an approximate structural estimate for relative comparison only; "
    "they are not predicted accuracy."
)


@dataclass
class CategoryBalance:
    category: str
    epistemic_band: str
    verified_count: int
    centroid_drift: float
    auto_approve_rate: float
    accuracy: float
    accuracy_note: str | None
    iks_contribution: float
    ceiling_estimate: float | None
    status: str


@dataclass
class LearningBalanceSheet:
    categories: list[CategoryBalance]
    overall_iks: float
    health_status: str
    overall_ceiling: float | None
    summary: dict[str, Any]
    generated_at: str = ""
    total_verified: int = 0
    notes: list[str] = field(default_factory=list)
    sources: dict[str, str] = field(default_factory=dict)


def _compute_status(
    verified_count: int,
    epistemic_band: str,
    centroid_drift: float,
    ceiling_estimate: float | None = None,
) -> str:
    if verified_count < 10:
        return "insufficient_data"
    if epistemic_band == "expert":
        if ceiling_estimate is not None and ceiling_estimate < 75:
            return "at_ceiling"
        return "converging"
    if ceiling_estimate is not None and ceiling_estimate < 70:
        return "at_ceiling"
    if centroid_drift > 0.05:
        return "converging"
    return "early"


def _compute_structural_ceiling_report() -> tuple[float | None, dict[str, float]]:
    scorer = get_profile_scorer()
    if scorer is None:
        return None, {}
    try:
        sigma = np.array([SOC_FACTOR_SIGMA[f] for f in SOC_FACTORS], dtype=np.float64)
        report = compute_snr_report(
            centroids=np.asarray(scorer.centroids, dtype=np.float64),
            sigma=sigma,
            categories=list(SOC_CATEGORIES),
            actions=list(SCORER_ACTIONS),
            factor_names=list(SOC_FACTORS),
        )
    except Exception as exc:
        _log.warning("ceiling_estimate(balance_sheet): SNR computation failed — returning None (source=fallback): %s", exc)
        return None, {}
    return (
        float(report.mean_ceiling_estimate * 100.0),
        {
            row.category_name: float(row.ceiling_estimate * 100.0)
            for row in report.categories
        },
    )


def _safe_epistemic_state() -> tuple[dict[str, dict[str, Any]], int]:
    try:
        snap = get_snapshot()
        return snap.get_epistemic_state(), int(getattr(snap, "verified_decisions", 0) or 0)
    except RuntimeError:
        return {}, 0


async def _safe_overall_iks(neo4j_service: Any) -> float:
    try:
        return float(await compute_visible_iks(neo4j_service))
    except Exception as exc:
        _log.warning("overall_iks(balance_sheet): IKS computation failed — returning 0.0 (source=fallback): %s", exc)
        return 0.0


async def _safe_centroid_drift(neo4j_service: Any) -> dict[str, float]:
    try:
        scorer = get_profile_scorer()
        if scorer is None:
            return {category: 0.0 for category in SOC_CATEGORIES}

        export = await build_centroid_export(scorer, neo4j_service)
        current_mu = export.get("current_mu")
        bootstrap_mu = export.get("bootstrap_mu")
        categories = export.get("categories") or list(SOC_CATEGORIES)
        if current_mu is None or bootstrap_mu is None:
            return {category: 0.0 for category in SOC_CATEGORIES}

        curr_arr = np.array(current_mu, dtype=np.float64)
        boot_arr = np.array(bootstrap_mu, dtype=np.float64)
        drift_by_category: dict[str, float] = {}
        for idx, category in enumerate(categories):
            diff = curr_arr[idx] - boot_arr[idx]
            drift_by_category[category] = round(float(np.mean(np.linalg.norm(diff, axis=1))), 4)
        return {category: float(drift_by_category.get(category, 0.0)) for category in SOC_CATEGORIES}
    except Exception as exc:
        _log.warning("centroid_drift(balance_sheet): drift computation failed — returning 0.0 per category (source=fallback): %s", exc)
        return {category: 0.0 for category in SOC_CATEGORIES}


async def _safe_learning_health(neo4j_service: Any) -> dict[str, Any]:
    try:
        return await LearningHealthMonitor.evaluate(neo4j_service)
    except Exception:
        return {"status": "unavailable"}


async def _safe_auto_approve_stats() -> dict[str, Any]:
    try:
        from app.routers.framework_router import auto_approve_stats

        return await auto_approve_stats()
    except Exception as exc:
        _log.warning("auto_approve_coverage_pct(balance_sheet): stats fetch failed — returning 0.0 (source=fallback): %s", exc)
        return {"by_category": {}, "coverage_pct": 0.0, "total_decisions": 0, "auto_approved": 0}


async def _safe_timeline(neo4j_service: Any) -> dict[str, Any]:
    try:
        return await get_evolution_timeline(neo4j_service)
    except Exception:
        return {"timeline": [], "ceiling_estimate": None}


def _category_score(balance: CategoryBalance) -> tuple[float, float, float]:
    band_score = {
        "novice": 0.0,
        "learning": 1.0,
        "calibrating": 2.0,
        "expert": 3.0,
    }.get(balance.epistemic_band, 0.0)
    return (band_score, float(balance.verified_count), -float(balance.centroid_drift))


def _build_recommendation(
    weakest: CategoryBalance,
    health_status: str,
    accuracy_fallback_used: bool,
    pre_activation: bool = False,
) -> str:
    category_label = weakest.category.replace("_", " ")
    if health_status == "CALIBRATING" or pre_activation:
        return (
            f"Learning health is in pre-activation: conservation monitoring is configured "
            f"but learning is not yet enabled; continue validation for {category_label} "
            f"before widening autonomy."
        )
    if weakest.epistemic_band == "novice":
        return (
            f"Prioritize verified feedback in {category_label}; it remains in the novice band "
            f"with only {weakest.verified_count} verified decisions."
        )
    if weakest.centroid_drift >= 1.0:
        return (
            f"Review recent {category_label} outcomes before widening autonomy; centroid drift "
            f"is elevated at {weakest.centroid_drift:.3f}."
        )
    if health_status in {"RED", "AMBER"}:
        return (
            f"Keep auto-approve conservative while learning health is {health_status}; focus on "
            f"stabilizing {category_label} first."
        )
    if accuracy_fallback_used:
        return (
            f"Expand verified-outcome capture for {category_label}; accuracy is currently a "
            f"fallback proxy until measured per-category accuracy is wired."
        )
    return (
        f"{category_label.title()} is the weakest learning area; add reviewed decisions there "
        f"before increasing its auto-approve envelope."
    )


async def generate_balance_sheet(neo4j_service: Any = None) -> LearningBalanceSheet:
    epistemic_state, total_verified = _safe_epistemic_state()
    overall_iks = await _safe_overall_iks(neo4j_service)
    centroid_drift = await _safe_centroid_drift(neo4j_service)
    learning_health = await _safe_learning_health(neo4j_service)
    auto_approve = await _safe_auto_approve_stats()
    timeline = await _safe_timeline(neo4j_service)
    overall_ceiling, snr_by_cat = _compute_structural_ceiling_report()

    auto_by_category = auto_approve.get("by_category") or {}
    timeline_ceiling = timeline.get("ceiling_estimate")
    accuracy_note = "Per-category measured accuracy is unavailable from assembled internal sources; using 0.0 placeholder."
    accuracy_fallback_used = True

    categories: list[CategoryBalance] = []
    for category in SOC_CATEGORIES:
        ep_data = epistemic_state.get(category) or {}
        verified_count = int(ep_data.get("count") or 0)
        epistemic_band = ep_data.get("band") or "novice"
        cat_auto = auto_by_category.get(category) or {}
        auto_approve_rate = float(cat_auto.get("coverage_pct") or 0.0) / 100.0
        contribution = (
            round(overall_iks * (verified_count / total_verified), 4)
            if total_verified > 0 else 0.0
        )
        categories.append(
            CategoryBalance(
                category=category,
                epistemic_band=epistemic_band,
                verified_count=verified_count,
                centroid_drift=float(centroid_drift.get(category, 0.0) or 0.0),
                auto_approve_rate=round(auto_approve_rate, 4),
                accuracy=0.0,
                accuracy_note=accuracy_note,
                iks_contribution=contribution,
                ceiling_estimate=snr_by_cat.get(category),
                status=_compute_status(
                    verified_count=verified_count,
                    epistemic_band=epistemic_band,
                    centroid_drift=float(centroid_drift.get(category, 0.0) or 0.0),
                    ceiling_estimate=snr_by_cat.get(category),
                ),
            )
        )

    strongest = max(categories, key=_category_score) if categories else None
    weakest = min(categories, key=_category_score) if categories else None
    summary = {
        "categories_at_expert": sum(1 for item in categories if item.epistemic_band == "expert"),
        "categories_at_learning": sum(1 for item in categories if item.epistemic_band == "learning"),
        "categories_at_novice": sum(1 for item in categories if item.epistemic_band == "novice"),
        "strongest_category": strongest.category if strongest else None,
        "weakest_category": weakest.category if weakest else None,
        "recommendation": _build_recommendation(
            weakest=weakest or CategoryBalance(
                category=SOC_CATEGORIES[0],
                epistemic_band="novice",
                verified_count=0,
                centroid_drift=0.0,
                auto_approve_rate=0.0,
                accuracy=0.0,
                accuracy_note=accuracy_note,
                iks_contribution=0.0,
                ceiling_estimate=None,
                status="insufficient_data",
            ),
            health_status=str(learning_health.get("status") or "unavailable"),
            accuracy_fallback_used=accuracy_fallback_used,
            pre_activation=bool(learning_health.get("pre_activation", False)),
        ),
    }

    notes = [accuracy_note]
    if overall_ceiling is not None:
        notes.append(_CEILING_NOTE)
    if timeline_ceiling is None and overall_ceiling is None:
        notes.append("ceiling_estimate is present and null until GAP-1 is implemented.")

    from datetime import datetime, timezone
    generated_at   = datetime.now(timezone.utc).isoformat()
    total_verified = sum(c.verified_count for c in categories)

    return LearningBalanceSheet(
        categories=categories,
        overall_iks=round(overall_iks, 4),
        health_status=str(learning_health.get("status") or "unavailable"),
        overall_ceiling=overall_ceiling,
        generated_at=generated_at,
        total_verified=total_verified,
        summary=summary,
        notes=notes,
        sources={
            "epistemic_state": "graph_snapshot.get_snapshot().get_epistemic_state()",
            "overall_iks": "compute_visible_iks()",
            "centroid_drift": "build_centroid_export() reconstructed per category",
            "learning_health": "LearningHealthMonitor.evaluate()",
            "auto_approve": "framework_router.auto_approve_stats()",
            "timeline": "get_evolution_timeline()",
        },
    )
