"""Read-only aggregation for the SOC Learning Control Room.

The service deliberately does not own or mutate scorer learning.  It samples
the existing live scorer, graph history, conservation monitor, and evolution
ledger into one UI contract.  Frozen Twin persistence is delegated to the
shared SDK service and is created only through the explicit initializer route.
"""

from __future__ import annotations

import copy
import math
import threading
from datetime import datetime, timezone
from typing import Any

import numpy as np

from copilot_sdk.twin import FrozenTwin, FrozenTwinStore


_DOMAIN = "soc"
_COPILOT = "soc"
_TIER_OBSERVED = "T_O"
_TIER_SYNTHETIC = "T_S"
_EPSILON = 0.001


class _DayZeroScorerView:
    """Read-only scorer-shaped view using the persisted bootstrap centroids."""

    def __init__(self, live_scorer: Any, centroids: np.ndarray) -> None:
        self._live_scorer = live_scorer
        self.centroids = np.asarray(centroids, dtype=np.float64).copy()
        self.mu = self.centroids
        self.actions = copy.deepcopy(getattr(live_scorer, "actions", []))
        self.categories = copy.deepcopy(getattr(live_scorer, "categories", None))
        self.kernel = getattr(live_scorer, "kernel", "l2")
        self.scoring_kernel = getattr(live_scorer, "scoring_kernel", None)
        self.decision_count = 0

    def get_checkpoint_state(self) -> dict[str, Any]:
        checkpoint_method = getattr(self._live_scorer, "get_checkpoint_state", None)
        checkpoint = copy.deepcopy(checkpoint_method() if callable(checkpoint_method) else {})
        checkpoint["centroids"] = self.centroids.copy()
        if isinstance(checkpoint.get("decision_counts"), list):
            checkpoint["decision_counts"] = [0] * len(checkpoint["decision_counts"])
        return checkpoint


class SOCLearningControlService:
    """Build Control Room payloads and manage the immutable SOC twin handle."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._twin = FrozenTwin(FrozenTwinStore())
        self._dk_history: list[dict[str, Any]] = []

    def _load_twin(self) -> FrozenTwin:
        with self._lock:
            if not self._twin.is_frozen():
                try:
                    self._twin.load(_COPILOT)
                except FileNotFoundError:
                    pass
            return self._twin

    def freeze(
        self,
        scorer: Any,
        conservation_state: dict[str, Any],
        iks: float,
        mu_zero: Any | None,
    ) -> dict[str, Any]:
        with self._lock:
            twin = self._load_twin()
            if twin.is_frozen():
                snapshot = twin.get_snapshot()
                return {
                    "frozen": True,
                    "created": False,
                    "checksum": snapshot.checksum,
                    "snapshot_time": snapshot.metadata.get("timestamp"),
                }

            if mu_zero is None:
                raise ValueError("SOC day-zero μ0 is unavailable; refusing to freeze a live scorer as baseline")
            baseline = np.asarray(mu_zero, dtype=np.float64)
            baseline_view = _DayZeroScorerView(scorer, baseline)
            snapshot = twin.freeze(
                baseline_view,
                conservation_state,
                float(iks),
                _COPILOT,
            )
            return {
                "frozen": True,
                "created": True,
                "checksum": snapshot.checksum,
                "snapshot_time": snapshot.metadata.get("timestamp"),
            }

    def comparison(self, scorer: Any, current_iks: float | None = None) -> dict[str, Any]:
        twin = self._load_twin()
        if not twin.is_frozen():
            raise FileNotFoundError("SOC Frozen Twin has not been initialized")
        report = twin.get_drift_report(scorer)
        snapshot = twin.get_snapshot()
        measured = int(report.decision_count_since_freeze) > 0
        tier = _TIER_OBSERVED if measured else _TIER_SYNTHETIC
        label = "measured" if measured else "synthetic / modelled — awaiting post-freeze decisions"
        current_iks_value = _finite_float(
            current_iks if current_iks is not None else getattr(scorer, "iks", snapshot.iks_value),
            snapshot.iks_value,
        )
        live_weights = getattr(getattr(scorer, "scoring_kernel", None), "weights", None)
        frozen_weights = snapshot.kernel_state.get("weights")
        weight_drift = report.weight_drift
        if live_weights is not None and frozen_weights is not None:
            weight_drift = float(np.linalg.norm(
                np.asarray(live_weights, dtype=np.float64) - np.asarray(frozen_weights, dtype=np.float64)
            ))
        return {
            "frozen_snapshot_time": snapshot.metadata.get("timestamp"),
            "frozen_iks": _finite_float(snapshot.iks_value, 0.0),
            "current_iks": current_iks,
            "centroid_drift": _finite_float(report.centroid_drift, 0.0),
            "weight_drift": _finite_float(weight_drift, 0.0),
            "conservation_drift": _finite_float(report.conservation_drift, 0.0),
            "iks_delta": _finite_float(current_iks_value - snapshot.iks_value, 0.0),
            "decisions_since_freeze": int(report.decision_count_since_freeze),
            "evidence_tier": tier,
            "evidence_label": label,
            "measured": measured,
            "note": (
                "Observed divergence from the immutable day-0 scorer."
                if measured
                else "The twin exists, but measured compounding begins after a post-freeze verified decision."
            ),
        }

    def record_dk_snapshot(self, categories: list[str], weights: dict[str, list[float]]) -> list[dict[str, Any]]:
        """Keep a small in-process change trace for the UI without fabricating history."""
        snapshot = {
            "sampled_at": datetime.now(timezone.utc).isoformat(),
            "weights": copy.deepcopy(weights),
        }
        with self._lock:
            if not self._dk_history or self._dk_history[-1]["weights"] != snapshot["weights"]:
                self._dk_history.append(snapshot)
            return copy.deepcopy(self._dk_history[-20:])


SERVICE = SOCLearningControlService()


def _finite_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def _json_number(value: Any) -> float:
    return _finite_float(value, 0.0)


async def build_control_room(age_client: Any) -> dict[str, Any]:
    """Collect all Control Room panels from current production sources."""
    from app.domains.soc.config import SOC_CATEGORIES, SOCDomainConfig, is_learning_enabled
    from app.services.gae_state import get_learning_state, get_mu_zero, get_profile_scorer
    from app.services.learning_health import LearningHealthMonitor
    from gae.evolution import get_evolution_summary

    scorer = get_profile_scorer()
    if scorer is None:
        raise RuntimeError("SOC ProfileScorer is not initialized")
    categories = [str(category) for category in SOC_CATEGORIES]
    factor_names = [str(factor.id) for factor in SOCDomainConfig().factors]

    history_rows = await age_client.run_query(
        "MATCH (d:Decision) "
        "WHERE d.domain = $domain AND d.centroid_delta_norm IS NOT NULL "
        "RETURN d.decision_id AS id, d.category AS category, "
        "d.centroid_delta_norm AS movement, d.verified_at_epoch AS verified_at "
        "ORDER BY d.verified_at_epoch ASC LIMIT 500",
        {"domain": _DOMAIN},
    )
    centroid_history = [
        {
            "decision_number": index + 1,
            "id": str(row.get("id") or ""),
            "category": str(row.get("category") or "unknown"),
            "movement": _json_number(row.get("movement")),
            "verified_at": str(row.get("verified_at") or ""),
        }
        for index, row in enumerate(history_rows or [])
    ]

    category_rows = await age_client.run_query(
        "MATCH (d:Decision) WHERE d.domain = $domain "
        "RETURN d.category AS category, count(d) AS cnt",
        {"domain": _DOMAIN},
    )
    category_counts = {str(row.get("category")): int(row.get("cnt") or 0) for row in category_rows or []}
    verified_total = int(await age_client.count_verified_decisions())

    weights: dict[str, list[float]] = {}
    for index, category in enumerate(categories):
        getter = getattr(scorer, "get_dk_weights", None)
        raw = getter(index) if callable(getter) else None
        if raw is not None:
            weights[category] = [_json_number(value) for value in np.asarray(raw, dtype=np.float64).reshape(-1)]
    dk_history = SERVICE.record_dk_snapshot(categories, weights)

    centroids = np.asarray(getattr(scorer, "centroids", []), dtype=np.float64)
    mu_zero = get_mu_zero()
    centroid_state: list[dict[str, Any]] = []
    convergence: list[dict[str, Any]] = []
    for index, category in enumerate(categories):
        current = centroids[index].tolist() if centroids.ndim == 3 and index < len(centroids) else []
        baseline = np.asarray(mu_zero[index], dtype=np.float64) if mu_zero is not None and index < len(mu_zero) else None
        drift = float(np.linalg.norm(np.asarray(current, dtype=np.float64) - baseline)) if baseline is not None else 0.0
        movements = [_json_number(row["movement"]) for row in centroid_history if row["category"] == category]
        recent = movements[-10:]
        rate = sum(recent) / len(recent) if recent else 0.0
        stable = bool(recent) and rate < _EPSILON
        centroid_state.append({"category": category, "centroids": current, "drift_from_day_zero": _json_number(drift)})
        convergence.append({
            "category": category,
            "decisions_to_stable": len(movements) if stable else None,
            "current_movement_rate": _json_number(rate),
            "estimated_remaining": 0 if stable else None,
            "stable": stable,
        })

    health = await LearningHealthMonitor.evaluate(age_client)
    iks = await _iks_payload(age_client)
    evolution = await get_evolution_summary(age_client)
    return {
        "centroid_history": centroid_history,
        "centroid_state": centroid_state,
        "dk_weights": {
            "factor_names": factor_names,
            "current": weights,
            "history": dk_history,
            "history_scope": "control-room samples; no synthetic backfill",
        },
        "conservation": {
            **health,
            "phase": health.get("status", "UNKNOWN"),
        },
        "iks": iks,
        "verified_count": {
            "total": verified_total,
            "per_category": {category: category_counts.get(category, 0) for category in categories},
        },
        "evolution_summary": evolution,
        "convergence": convergence,
        "learning_enabled": bool(is_learning_enabled()),
        "evidence": {
            "centroid_history": _TIER_OBSERVED if verified_total else _TIER_SYNTHETIC,
            "dk_weights": _TIER_OBSERVED if weights else _TIER_SYNTHETIC,
            "conservation": _TIER_OBSERVED,
            "iks": _TIER_OBSERVED if verified_total else _TIER_SYNTHETIC,
            "verified_decisions": _TIER_OBSERVED,
            "disclaimer": "T_O = observed runtime data; T_S = synthetic/modelled or not yet measured.",
        },
    }


async def _iks_payload(age_client: Any) -> dict[str, Any]:
    from app.services.iks import compute_iks_v2

    current = await compute_iks_v2(age_client)
    trend_point = {
        "decisions": int(current.get("total_decisions", 0) or 0),
        "iks": _json_number(current.get("iks_v2")),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return {
        "current": _json_number(current.get("iks_v2")),
        "trajectory": [trend_point],
        "components": current.get("components") or {},
        "interpretation": str(current.get("interpretation") or ""),
    }
