"""Read-only aggregation for the SOC Learning Control Room.

The service deliberately does not own or mutate scorer learning.  It samples
the existing live scorer, graph history, conservation monitor, and evolution
ledger into one UI contract.  Frozen Twin persistence is delegated to the
shared SDK service and is created only through the explicit initializer route.
"""

from __future__ import annotations

import copy
import json
import math
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np

from copilot_sdk.twin import FrozenTwin, FrozenTwinStore
from copilot_sdk.graph.protocol import GraphStore
from app.domains.soc.scorer_adapter import SOCCompoundingScorerAdapter


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
        checkpoint: dict[str, Any] = copy.deepcopy(checkpoint_method() if callable(checkpoint_method) else {})
        checkpoint["centroids"] = self.centroids.copy()
        if isinstance(checkpoint.get("decision_counts"), list):
            checkpoint["decision_counts"] = [0] * len(checkpoint["decision_counts"])
        return checkpoint


class SOCLearningControlService:
    """Build Control Room payloads and manage the immutable SOC twin handle."""

    def __init__(self, twin_store: FrozenTwinStore | None = None) -> None:
        self._lock = threading.RLock()
        self._configured_twin = FrozenTwin(twin_store) if twin_store is not None else None
        self._dk_history: list[dict[str, Any]] = []

    def configure_graph_store(self, graph_store: GraphStore) -> None:
        with self._lock:
            self._configured_twin = FrozenTwin(FrozenTwinStore(graph_store, _DOMAIN))

    @property
    def _twin(self) -> FrozenTwin:
        if self._configured_twin is None:
            raise RuntimeError("SOC learning control requires the configured graph store")
        return self._configured_twin

    def has_demo_twin(self) -> bool:
        return self._twin.store.graph_store.get_governance(_DOMAIN, "demo_twin_active") is not None

    def _comparison_twin(self) -> FrozenTwin:
        if not self.has_demo_twin():
            return self._load_twin()
        pointer = self._twin.store.graph_store.get_governance(_DOMAIN, "demo_twin_active")
        if pointer is None:
            return self._load_twin()
        run_id = str(pointer["run_id"])
        if uuid.UUID(hex=run_id).hex != run_id:
            raise ValueError("Invalid demo twin reference")
        twin = FrozenTwin(self._twin.store)
        twin.load(f"soc-demo-{run_id}")
        return twin

    def demo_refreeze(self, scorer: Any, conservation_state: dict[str, Any], iks: float) -> dict[str, Any]:
        """Archive the previous comparison, leaving the production day-zero file intact."""
        if not math.isfinite(iks):
            raise ValueError("Demo freeze requires finite observed IKS")
        count = conservation_state.get("components", {}).get("verified_decisions")
        if not isinstance(count, int) or count < 0:
            raise ValueError("Demo freeze requires a verified population count")
        with self._lock:
            previous = self._comparison_twin()
            if not previous.is_frozen():
                raise FileNotFoundError("Initialize the production day-zero twin before demo re-freeze")
            old = previous.get_snapshot()
            if not old.verify_integrity():
                raise ValueError("Previous twin failed integrity verification")
            run_id = uuid.uuid4().hex
            self._twin.store.graph_store.save_evolution(
                _DOMAIN, f"frozen_twin_archive:{run_id}", {"snapshot": json.loads(old.to_json())}
            )
            provenance = {"origin": "demo_reseed", "archived_previous": True,
                          "previous_checksum": old.checksum, "archive_id": run_id,
                          "planted": True, "evidence_tier": "T-sim"}
            twin = FrozenTwin(self._twin.store)
            snapshot = twin.freeze(scorer, {**conservation_state, "demo_provenance": provenance,
                                           "demo_verified_count": count}, iks, f"soc-demo-{run_id}")
            # Publish the reference only after the immutable graph snapshot exists.
            self._twin.store.graph_store.save_governance(
                _DOMAIN, "demo_twin_active", {"run_id": run_id}
            )
            return {"frozen": True, "created": True, "checksum": snapshot.checksum,
                    "snapshot_time": snapshot.metadata["timestamp"], "provenance": provenance}

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

    def comparison(self, scorer: Any, current_iks: float | None = None,
                   verified_count: int | None = None, *, demo: bool = False,
                   decisions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        twin = self._comparison_twin() if demo else self._load_twin()
        if not twin.is_frozen():
            raise FileNotFoundError("SOC Frozen Twin has not been initialized")
        report = twin.get_drift_report(scorer)
        snapshot = twin.get_snapshot()
        if not snapshot.verify_integrity():
            raise ValueError("Frozen snapshot integrity check failed")
        points: list[dict[str, Any]] = []
        excluded = 0
        # One isolated live geometry for the whole request; no learning, audit
        # writes or live scorer counters are changed by this GET.
        # The adapter owns a database connection; clone only its scoring geometry.
        geometry = scorer._scorer if isinstance(scorer, SOCCompoundingScorerAdapter) else scorer
        live = copy.deepcopy(geometry) if decisions else None
        categories = list(getattr(scorer, "categories", None) or [])
        for row in decisions or []:
            try:
                verified_at = float(row["verified_at_epoch"])
                if not math.isfinite(verified_at):
                    raise ValueError("Invalid verification time")
                if verified_at > 100_000_000_000:
                    verified_at /= 1000.0  # Legacy AGE verification epochs are milliseconds.
                if verified_at <= float(snapshot.metadata["timestamp"]):
                    continue
                category = str(row["category"])
                category_index = categories.index(category)
                vector = row["factor_vector"]
                if isinstance(vector, str):
                    vector = json.loads(vector)
                values = np.asarray(vector, dtype=np.float64)
                if (values.shape != (scorer.n_factors,) or not np.all(np.isfinite(values))
                        or not row.get("decision_id")):
                    raise ValueError("Invalid stored comparison input")
            except (KeyError, TypeError, ValueError):
                excluded += 1
                continue
            parallel = twin.score_parallel(values, category_index, live)
            frozen_confidence = float(parallel.frozen_result.confidence)
            live_confidence = float(parallel.live_result.confidence)
            if not all(math.isfinite(value) and 0 <= value <= 1 for value in (frozen_confidence, live_confidence)):
                raise ValueError("Non-finite or out-of-range comparison confidence")
            points.append({
                "decision_id": str(row["decision_id"]), "category": category,
                "verified_at_epoch": verified_at,
                "frozen": {"action": parallel.frozen_result.action_name, "confidence": frozen_confidence},
                "live": {"action": parallel.live_result.action_name, "confidence": live_confidence},
                "confidence_delta": live_confidence - frozen_confidence,
            })
        provenance = snapshot.conservation_state.get("demo_provenance")
        decisions_since_freeze = int(report.decision_count_since_freeze)
        if provenance:
            # The in-memory scorer counter resets at restart. Demo evidence is
            # the persisted verified population delta, not analyze-call count.
            decisions_since_freeze = max(0, verified_count - int(snapshot.conservation_state["demo_verified_count"])) if verified_count is not None else 0
        measured = decisions_since_freeze > 0
        tier = _TIER_OBSERVED if measured else _TIER_SYNTHETIC
        label = "measured" if measured else "synthetic / modelled — awaiting post-freeze decisions"
        if provenance:
            tier = _TIER_SYNTHETIC
            label = "synthetic demo — measured on planted outcomes, not pilot evidence"
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
            "current_iks": current_iks_value,
            "centroid_drift": _finite_float(report.centroid_drift, 0.0),
            "weight_drift": _finite_float(weight_drift, 0.0),
            "conservation_drift": _finite_float(report.conservation_drift, 0.0),
            "iks_delta": _finite_float(current_iks_value - snapshot.iks_value, 0.0),
            "decisions_since_freeze": decisions_since_freeze,
            "comparison_points": points,
            "compared_decisions": len(points),
            "excluded_comparison_rows": excluded,
            "mean_confidence_delta": (sum(point["confidence_delta"] for point in points) / len(points)) if points else None,
            "comparison_scope": "Latest 500 verified SOC decisions, restricted to post-freeze verification times",
            "confidence_note": "Same stored input, frozen versus current geometry. Confidence change is not measured accuracy improvement.",
            **({"provenance": provenance} if provenance else {}),
            "evidence_tier": tier,
            "evidence_label": label,
            "measured": measured,
            "note": (
                ("Observed divergence from the archived demo baseline." if provenance else "Observed divergence from the immutable day-0 scorer.")
                if measured
                else "The twin exists, but measured compounding begins after a post-freeze verified decision."
            ),
        }

    async def measured_comparison(self, age_client: Any, scorer: Any, current_iks: float,
                                  verified_count: int | None = None, *, demo: bool = False) -> dict[str, Any]:
        """Fetch a bounded, domain-scoped verified cohort; read failures propagate."""
        from app.db.graph_client import soc_decision_where
        from app.services.learning_health import _soc_verified_predicate

        rows = await age_client.run_query(
            f"MATCH (d:Decision) WHERE {soc_decision_where()} AND {_soc_verified_predicate()} "
            "RETURN d.decision_id AS decision_id, d.category AS category, "
            "d.factor_vector AS factor_vector, d.verified_at_epoch AS verified_at_epoch "
            "ORDER BY CASE WHEN d.verified_at_epoch > 100000000000 "
            "THEN d.verified_at_epoch / 1000.0 ELSE d.verified_at_epoch END DESC, "
            "d.decision_id ASC LIMIT 500"
        )
        return self.comparison(scorer, current_iks, verified_count, demo=demo,
                               decisions=[dict(row) for row in rows])

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
