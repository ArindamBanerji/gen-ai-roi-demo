"""
FEATURE-01 evaluation service.

Runs uploaded CSV rows through a deep-copied ProfileScorer so production
state remains byte-identical before and after evaluation.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple
import math
import time

import numpy as np

from gae.snr import compute_snr_report

from app.domains.soc.config import (
    SCORER_ACTIONS,
    SOC_CATEGORIES,
    SOC_FACTORS,
    SOC_FACTOR_SIGMA,
)
from app.services.gae_state import get_mu_zero, get_profile_scorer


REQUIRED_COLUMNS: List[str] = ["category", "ground_truth_action"] + list(SOC_FACTORS)
TEMPLATE_FORMATS: Tuple[str, ...] = ("generic", "sentinel", "splunk")


@dataclass
class EvalResult:
    total_rows: int
    evaluated_rows: int
    invalid_rows: int
    accuracy: float
    accuracy_trajectory: List[Dict] = field(default_factory=list)
    confidence_trajectory: List[Dict] = field(default_factory=list)
    convergence_trajectory: List[Dict] = field(default_factory=list)
    per_decision_log: List[Dict] = field(default_factory=list)
    per_category_results: List[Dict[str, Any]] = field(default_factory=list)
    category_accuracy: Dict[str, float] = field(default_factory=dict)
    category_counts: Dict[str, int] = field(default_factory=dict)
    duration_seconds: float = 0.0
    warnings: List[str] = field(default_factory=list)
    confidence_note: Optional[str] = None
    learning_direction: str = "insufficient_data"
    distance_change_pct: float = 0.0
    convergence_summary: Dict[str, Any] = field(default_factory=dict)
    calibration_warning: bool = False
    calibration_status: str = "unknown"
    calibration_note: Optional[str] = None
    ambiguity_summary: Dict[str, Any] = field(default_factory=dict)
    majority_baseline: Dict = field(default_factory=dict)
    learning_advantage_over_majority: float = 0.0
    ceiling_estimate: Dict[str, Any] = field(default_factory=dict)


_CEILING_NOTE = (
    "Approximate structural estimate only for relative comparison; not predicted accuracy."
)
_CONVERGENCE_N_HALF = 13.51


def _compute_structural_ceiling(centroids: np.ndarray) -> Dict[str, Any]:
    sigma = np.array([SOC_FACTOR_SIGMA[f] for f in SOC_FACTORS], dtype=np.float64)
    report = compute_snr_report(
        centroids=np.asarray(centroids, dtype=np.float64),
        sigma=sigma,
        categories=list(SOC_CATEGORIES),
        actions=list(SCORER_ACTIONS),
        factor_names=list(SOC_FACTORS),
    )
    per_category = {
        category: float(row.ceiling_estimate * 100.0)
        for category, row in zip(SOC_CATEGORIES, report.categories)
    }
    return {
        "overall": float(report.mean_ceiling_estimate * 100.0),
        "per_category": per_category,
        "note": _CEILING_NOTE,
    }


def example_template_rows() -> List[Dict[str, object]]:
    return [
        {
            "row_id": "example-1",
            "category": "credential_access",
            "ground_truth_action": "escalate",
            "privileged_identity_context": 0.95,
            "asset_criticality": 0.90,
            "threat_intel_enrichment": 0.85,
            "pattern_history": 0.75,
            "time_anomaly": 0.80,
            "device_trust": 0.10,
        },
        {
            "row_id": "example-2",
            "category": "malware_execution",
            "ground_truth_action": "investigate",
            "privileged_identity_context": 0.20,
            "asset_criticality": 0.75,
            "threat_intel_enrichment": 0.65,
            "pattern_history": 0.70,
            "time_anomaly": 0.45,
            "device_trust": 0.35,
        },
        {
            "row_id": "example-3",
            "category": "cloud_infrastructure",
            "ground_truth_action": "monitor",
            "privileged_identity_context": 0.15,
            "asset_criticality": 0.55,
            "threat_intel_enrichment": 0.25,
            "pattern_history": 0.30,
            "time_anomaly": 0.35,
            "device_trust": 0.80,
        },
    ]


def validate_csv_rows(
    rows: Iterable[Tuple[int, Dict[str, str]]]
) -> Tuple[List[Dict], List[Dict], List[str]]:
    clean_rows: List[Dict] = []
    errors: List[Dict] = []
    warnings: List[str] = []

    for row_number, row in rows:
        row_errors: List[str] = []
        category = (row.get("category") or "").strip()
        ground_truth_action = (row.get("ground_truth_action") or "").strip()

        if not category:
            row_errors.append("category is required")
        elif category not in SOC_CATEGORIES:
            row_errors.append(
                f"category must be one of {list(SOC_CATEGORIES)}, got {category!r}"
            )

        if not ground_truth_action:
            row_errors.append("ground_truth_action is required")
        elif ground_truth_action not in SCORER_ACTIONS:
            row_errors.append(
                "ground_truth_action must be one of "
                f"{list(SCORER_ACTIONS)}, got {ground_truth_action!r}"
            )

        factors: Dict[str, float] = {}
        for factor_name in SOC_FACTORS:
            raw_value = row.get(factor_name)
            if raw_value is None or str(raw_value).strip() == "":
                row_errors.append(f"{factor_name} is required")
                continue

            try:
                factor_value = float(str(raw_value).strip())
            except ValueError:
                row_errors.append(f"{factor_name} must be numeric, got {raw_value!r}")
                continue

            if not math.isfinite(factor_value):
                row_errors.append(f"{factor_name} must be finite, got {raw_value!r}")
                continue
            if factor_value < 0.0 or factor_value > 1.0:
                row_errors.append(
                    f"{factor_name} must be in [0.0, 1.0], got {factor_value}"
                )
                continue

            factors[factor_name] = factor_value

        if row_errors:
            errors.append({
                "row_number": row_number,
                "errors": row_errors,
            })
            continue

        clean_rows.append({
            "row_number": row_number,
            "row_id": (row.get("row_id") or f"row-{row_number}").strip(),
            "category": category,
            "ground_truth_action": ground_truth_action,
            "factors": factors,
        })

    if errors:
        warnings.append(f"{len(errors)} row(s) failed validation and may be skipped.")

    return clean_rows, errors, warnings


def run_evaluation(rows: List[Dict]) -> EvalResult:
    scorer = get_profile_scorer()
    if scorer is None:
        raise RuntimeError("ProfileScorer not initialized")

    scorer_copy = deepcopy(scorer)
    start_ts = time.time()

    mu_zero = get_mu_zero()
    drift_reference = None
    warnings: List[str] = []
    if isinstance(mu_zero, np.ndarray) and mu_zero.shape == scorer_copy.centroids.shape:
        drift_reference = mu_zero.astype(np.float64, copy=True)
    else:
        drift_reference = np.array(scorer_copy.centroids, dtype=np.float64, copy=True)
        warnings.append(
            "mu_zero snapshot unavailable or shape-mismatched; convergence uses scorer copy baseline."
        )

    correct_total = 0
    category_totals: Dict[str, int] = {category: 0 for category in SOC_CATEGORIES}
    category_correct: Dict[str, int] = {category: 0 for category in SOC_CATEGORIES}
    accuracy_trajectory: List[Dict] = []
    confidence_trajectory: List[Dict] = []
    convergence_trajectory: List[Dict] = []
    per_decision_log: List[Dict] = []
    confidence_running_sum = 0.0
    confidence_values: List[float] = []

    for decision_number, row in enumerate(rows, start=1):
        factor_vector = np.array(
            [row["factors"][factor_name] for factor_name in SOC_FACTORS],
            dtype=np.float64,
        )
        category = row["category"]
        category_index = SOC_CATEGORIES.index(category)
        gt_action = row["ground_truth_action"]
        gt_action_index = SCORER_ACTIONS.index(gt_action)

        scoring = scorer_copy.score(factor_vector, category_index=category_index)
        predicted_index = int(getattr(scoring, "action_index"))
        predicted_action = str(getattr(scoring, "action_name"))
        confidence = float(getattr(scoring, "confidence"))
        probabilities = getattr(scoring, "probabilities", None)
        probability_list = (
            np.asarray(probabilities, dtype=np.float64).tolist()
            if probabilities is not None
            else []
        )
        correct = predicted_index == gt_action_index

        scorer_copy.update(
            f=factor_vector,
            category_index=category_index,
            action_index=predicted_index,
            correct=correct,
            gt_action_index=gt_action_index,
            confidence=confidence,
        )

        category_totals[category] += 1
        if correct:
            correct_total += 1
            category_correct[category] += 1

        confidence_running_sum += confidence
        confidence_values.append(confidence)
        accuracy_trajectory.append({
            "decision_number": decision_number,
            "accuracy": round(correct_total / decision_number, 6),
            "correct_total": correct_total,
        })
        confidence_trajectory.append({
            "decision_number": decision_number,
            "confidence": round(confidence, 6),
            "mean_confidence": round(confidence_running_sum / decision_number, 6),
        })
        convergence_trajectory.append({
            "decision_number": decision_number,
            "drift_from_mu_zero": round(
                float(
                    np.linalg.norm(
                        np.asarray(scorer_copy.centroids, dtype=np.float64) - drift_reference
                    )
                ),
                6,
            ),
        })
        top_two_probs = sorted(probability_list, reverse=True)[:2]
        prob_gap = float(top_two_probs[0] - top_two_probs[1]) if len(top_two_probs) == 2 else 1.0
        decision_record = {
            "decision_number": decision_number,
            "row_number": int(row["row_number"]),
            "row_id": row["row_id"],
            "category": category,
            "category_index": category_index,
            "ground_truth_action": gt_action,
            "ground_truth_action_index": gt_action_index,
            "predicted_action": predicted_action,
            "predicted_action_index": predicted_index,
            "correct": bool(correct),
            "confidence": round(confidence, 6),
            "probabilities": probability_list,
            "factor_vector": factor_vector.tolist(),
            "ambiguous": bool(confidence < 0.30 and prob_gap < 0.10),
        }
        if decision_record["ambiguous"]:
            decision_record["ambiguity_note"] = (
                "Structurally ambiguous — top two actions are nearly "
                "equally likely. Disagreement here is expected, not an error."
            )
        per_decision_log.append(decision_record)

    evaluated_rows = len(rows)
    category_accuracy = {
        category: round(category_correct[category] / category_totals[category], 6)
        for category in SOC_CATEGORIES
        if category_totals[category] > 0
    }
    category_counts = {
        category: int(count)
        for category, count in category_totals.items()
        if count > 0
    }
    per_category_results: List[Dict[str, Any]] = []
    n_actions = len(SCORER_ACTIONS)
    for category in SOC_CATEGORIES:
        verified_count = int(category_totals[category])
        if verified_count <= 0:
            continue
        updates_per_pair = verified_count / n_actions if n_actions > 0 else 0.0
        convergence_pct = (1.0 - 0.5 ** (updates_per_pair / _CONVERGENCE_N_HALF)) * 100.0
        remaining_for_90 = max(0.0, _CONVERGENCE_N_HALF * 3.32 * n_actions - verified_count)
        per_category_results.append({
            "category": category,
            "verified_count": verified_count,
            "accuracy": float(category_accuracy.get(category, 0.0)),
            "convergence_pct": round(float(convergence_pct), 1),
            "decisions_to_90pct": int(remaining_for_90),
        })

    max_confidence = max(confidence_values) if confidence_values else 0.0
    confidence_note = None
    if max_confidence < 0.30:
        confidence_note = (
            "Confidence is near the random baseline (0.25). "
            "This is expected with uncalibrated or early-stage centroids. "
            "Confidence sharpens as centroids calibrate to your data — "
            "look at the accuracy trend for the learning signal."
        )
    elif max_confidence < 0.50:
        confidence_note = (
            "Confidence is moderate. Centroids are beginning to separate "
            "action profiles. Higher confidence emerges with more verified decisions."
        )

    if len(convergence_trajectory) < 5:
        learning_direction = "insufficient_data"
        distance_change_pct = 0.0
    else:
        first_drift = convergence_trajectory[0]["drift_from_mu_zero"]
        last_drift = convergence_trajectory[-1]["drift_from_mu_zero"]
        learning_direction = "correct" if last_drift < first_drift else "wrong"
        if first_drift == 0.0:
            distance_change_pct = 0.0
        else:
            distance_change_pct = round(((last_drift - first_drift) / first_drift) * 100, 2)
    calibration_warning = learning_direction == "wrong"
    total_verified = sum(int(c["verified_count"]) for c in per_category_results)
    avg_convergence = (
        sum(float(c["convergence_pct"]) for c in per_category_results) / len(per_category_results)
        if per_category_results
        else 0.0
    )
    convergence_summary = {
        "average_convergence_pct": round(float(avg_convergence), 1),
        "total_verified": int(total_verified),
        "note": f"Based on N_half={_CONVERGENCE_N_HALF} decisions per category-action pair.",
    }

    # OBS-FIX-04: centroid calibration heuristic
    centroids_flat = np.asarray(scorer_copy.centroids, dtype=np.float64).ravel()
    if (
        np.all(centroids_flat >= 0.3)
        and np.all(centroids_flat <= 0.7)
        and float(np.std(centroids_flat)) < 0.15
    ):
        calibration_status = "uncalibrated"
        calibration_note = (
            "All centroid values lie in [0.3, 0.7] with std < 0.15 — "
            "centroids may not have been trained from domain-specific data."
        )
    else:
        calibration_status = "calibrated"
        calibration_note = None

    # MAJORITY BASELINE: per-category majority-action accuracy
    per_category_gt: Dict[str, List[str]] = {cat: [] for cat in SOC_CATEGORIES}
    for row in rows:
        per_category_gt[row["category"]].append(row["ground_truth_action"])

    majority_per_category: Dict[str, Dict] = {}
    majority_correct = 0
    majority_total = 0
    for cat in SOC_CATEGORIES:
        gt_list = per_category_gt[cat]
        if not gt_list:
            continue
        counter = Counter(gt_list)
        maj_action, maj_count = counter.most_common(1)[0]
        cat_total = len(gt_list)
        majority_correct += maj_count
        majority_total += cat_total
        majority_per_category[cat] = {
            "majority_action": maj_action,
            "accuracy": round(maj_count / cat_total, 6),
        }

    majority_accuracy = round(majority_correct / max(majority_total, 1), 6)
    majority_baseline = {
        "accuracy": majority_accuracy,
        "per_category": majority_per_category,
    }
    learning_advantage_over_majority = round(
        correct_total / max(evaluated_rows, 1) - majority_accuracy, 6
    )
    ambiguous_count = sum(1 for d in per_decision_log if d.get("ambiguous", False))
    ambiguous_pct = round((ambiguous_count / len(per_decision_log) * 100.0), 1) if per_decision_log else 0.0
    ambiguity_summary = {
        "ambiguous_decisions": int(ambiguous_count),
        "ambiguous_pct": float(ambiguous_pct),
        "note": (
            f"{ambiguous_count} of {len(per_decision_log)} decisions ({ambiguous_pct:.0f}%) "
            f"are in the ambiguous zone where the top two actions are nearly "
            f"equally likely. These are structural ties, not system errors."
        ) if ambiguous_count > 0 else None,
    }
    ceiling_estimate = _compute_structural_ceiling(
        np.asarray(scorer_copy.centroids, dtype=np.float64)
    )

    return EvalResult(
        total_rows=evaluated_rows,
        evaluated_rows=evaluated_rows,
        invalid_rows=0,
        accuracy=round(correct_total / max(evaluated_rows, 1), 6),
        accuracy_trajectory=accuracy_trajectory,
        confidence_trajectory=confidence_trajectory,
        convergence_trajectory=convergence_trajectory,
        per_decision_log=per_decision_log,
        per_category_results=per_category_results,
        category_accuracy=category_accuracy,
        category_counts=category_counts,
        duration_seconds=round(time.time() - start_ts, 6),
        warnings=warnings,
        confidence_note=confidence_note,
        learning_direction=learning_direction,
        distance_change_pct=distance_change_pct,
        convergence_summary=convergence_summary,
        calibration_warning=calibration_warning,
        calibration_status=calibration_status,
        calibration_note=calibration_note,
        ambiguity_summary=ambiguity_summary,
        majority_baseline=majority_baseline,
        learning_advantage_over_majority=learning_advantage_over_majority,
        ceiling_estimate=ceiling_estimate,
    )
