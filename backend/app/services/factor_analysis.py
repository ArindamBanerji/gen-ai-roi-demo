from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

import numpy as np

from gae.snr import SNRReport, compute_snr_report

from app.domains.soc.config import SCORER_ACTIONS, SOC_CATEGORIES, SOC_FACTORS
from app.services.gae_state import get_mu_zero, get_profile_scorer


def _sigma_profile() -> Dict[str, float]:
    from app.routers.soc import _FACTOR_SIGMA

    return {name: float(_FACTOR_SIGMA[name]) for name in SOC_FACTORS}


def _kernel_weights_for_scorer(scorer) -> Optional[np.ndarray]:
    kernel = getattr(scorer, "scoring_kernel", None)
    if kernel is None:
        return None
    if hasattr(kernel, "raw_weights"):
        return np.asarray(kernel.raw_weights, dtype=np.float64)
    if hasattr(kernel, "weights"):
        return np.asarray(kernel.weights, dtype=np.float64)
    return None


def _pairwise_factor_contribution(
    mu_c: np.ndarray,
    factor_names: List[str],
    weights: Optional[np.ndarray],
) -> Dict[str, float]:
    n_actions, n_factors = mu_c.shape
    scale = np.ones(n_factors, dtype=np.float64) if weights is None else np.abs(weights)
    totals = np.zeros(n_factors, dtype=np.float64)
    pair_count = 0
    for a1 in range(n_actions):
        for a2 in range(a1 + 1, n_actions):
            totals += np.abs(mu_c[a1] - mu_c[a2]) * scale
            pair_count += 1
    if pair_count > 0:
        totals /= pair_count
    grand_total = float(totals.sum())
    if grand_total > 0:
        totals = totals / grand_total
    return {
        factor_names[idx]: round(float(totals[idx]), 6)
        for idx in range(n_factors)
    }


def _report_to_dict(
    report: SNRReport,
    centroids: np.ndarray,
    sigma_profile: Dict[str, float],
    categories: List[str],
    actions: List[str],
    factor_names: List[str],
    kernel_weights: Optional[np.ndarray],
) -> Dict:
    category_rows = []
    weakest = None
    strongest = None
    weakest_factor = None
    if report.factor_importance:
        weakest_factor = min(report.factor_importance.items(), key=lambda item: item[1])[0]

    for row in report.categories:
        mu_c = np.asarray(centroids[row.category_index], dtype=np.float64)
        contributions = _pairwise_factor_contribution(mu_c, factor_names, kernel_weights)
        item = {
            "category": row.category_name,
            "mean_sep": round(float(row.action_separation), 6),
            "min_sep": round(float(row.weakest_pair_distance), 6),
            "weighted_noise": round(float(row.weighted_noise), 6),
            "snr_effective": round(float(row.snr), 6),
            "ceiling_estimate": round(float(row.ceiling_estimate) * 100.0, 2),
            "weakest_pair_names": list(row.weakest_action_pair),
            "status": row.status,
            "per_factor_contribution": contributions,
        }
        category_rows.append(item)
        if weakest is None or item["ceiling_estimate"] < weakest["ceiling_estimate"]:
            weakest = item
        if strongest is None or item["ceiling_estimate"] > strongest["ceiling_estimate"]:
            strongest = item

    proposed = {}
    if weakest is not None:
        proposed = {
            "target_category": weakest["category"],
            "weakest_pair_names": weakest["weakest_pair_names"],
            "weakest_factor": weakest_factor,
            "recommendation": report.proposed_improvement,
        }

    return {
        "overall_snr": round(float(report.mean_snr), 6),
        "overall_ceiling": round(float(report.mean_ceiling_estimate) * 100.0, 2),
        "weakest_category": weakest["category"] if weakest else None,
        "strongest_category": strongest["category"] if strongest else None,
        "categories": category_rows,
        "factor_importance": {
            key: round(float(value), 6) for key, value in report.factor_importance.items()
        },
        "proposed_improvement": proposed,
        "sigma_profile": {key: round(float(value), 6) for key, value in sigma_profile.items()},
        "kernel_weights": None if kernel_weights is None else {
            factor_names[idx]: round(float(kernel_weights[idx]), 6)
            for idx in range(len(factor_names))
        },
        "status_counts": dict(report.status_counts),
    }


async def run_factor_analysis() -> Dict:
    scorer = get_profile_scorer()
    if scorer is None:
        return {
            "error": "ProfileScorer not initialized",
            "status": "cold_start",
        }

    centroids = np.asarray(scorer.centroids, dtype=np.float64)
    sigma_profile = _sigma_profile()
    sigma = np.array([sigma_profile[name] for name in SOC_FACTORS], dtype=np.float64)
    kernel_weights = _kernel_weights_for_scorer(scorer)

    current_report = compute_snr_report(
        centroids=centroids,
        sigma=sigma,
        kernel_weights=kernel_weights,
        categories=list(SOC_CATEGORIES),
        actions=list(SCORER_ACTIONS),
        factor_names=list(SOC_FACTORS),
    )
    current = _report_to_dict(
        report=current_report,
        centroids=centroids,
        sigma_profile=sigma_profile,
        categories=list(SOC_CATEGORIES),
        actions=list(SCORER_ACTIONS),
        factor_names=list(SOC_FACTORS),
        kernel_weights=kernel_weights,
    )

    bootstrap = None
    snr_improved = None
    mu_zero = get_mu_zero()
    if mu_zero is not None:
        mu_zero = np.asarray(mu_zero, dtype=np.float64)
        if mu_zero.shape == centroids.shape:
            bootstrap_report = compute_snr_report(
                centroids=mu_zero,
                sigma=sigma,
                kernel_weights=kernel_weights,
                categories=list(SOC_CATEGORIES),
                actions=list(SCORER_ACTIONS),
                factor_names=list(SOC_FACTORS),
            )
            bootstrap = _report_to_dict(
                report=bootstrap_report,
                centroids=mu_zero,
                sigma_profile=sigma_profile,
                categories=list(SOC_CATEGORIES),
                actions=list(SCORER_ACTIONS),
                factor_names=list(SOC_FACTORS),
                kernel_weights=kernel_weights,
            )
            snr_improved = current["overall_snr"] > bootstrap["overall_snr"]

    return {
        "current": current,
        "bootstrap": bootstrap,
        "snr_improved": snr_improved,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }
