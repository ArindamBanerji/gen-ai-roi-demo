"""
Centroid Time Machine service helpers.
"""

from __future__ import annotations

import logging
import json
from typing import Any

import numpy as np

from gae.snr import compute_snr_report

from app.domains.soc.config import SCORER_ACTIONS, SOC_FACTORS, SOC_FACTOR_SIGMA
from app.services.gae_state import (
    _EXPORT_ACTIONS,
    _EXPORT_CATEGORIES,
    get_mu_zero,
    get_profile_scorer,
)
from app.services.iks import compute_iks_v2

_CEILING_NOTE = (
    "Ceiling values are an approximate structural estimate for relative comparison only; "
    "they are not predicted accuracy."
)

log = logging.getLogger(__name__)

_DEFAULT_FACTORS = list(SOC_FACTORS)


class SnapshotNotFoundError(FileNotFoundError):
    """Raised when a requested AGE checkpoint does not exist."""


class SnapshotCorruptError(ValueError):
    """Raised when an AGE checkpoint is unreadable or fails validation."""


def _age_store() -> Any:
    scorer = get_profile_scorer()
    if scorer is None:
        raise RuntimeError("SOC scorer is unavailable; AGE checkpoint access cannot proceed")
    store = getattr(scorer, "graph_store", None)
    if store is None:
        raise RuntimeError("SOC GraphStore is unavailable; AGE checkpoint access cannot proceed")
    return store


def _checkpoint_payload(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise SnapshotCorruptError("AGE checkpoint did not contain an object")
    centroids = raw.get("centroids", raw.get("mu"))
    if isinstance(centroids, str):
        try:
            centroids = json.loads(centroids)
        except json.JSONDecodeError as exc:
            raise SnapshotCorruptError("AGE checkpoint centroid tensor is invalid JSON") from exc
    if centroids is None:
        raise SnapshotCorruptError("AGE checkpoint does not contain centroid tensor")
    metadata = raw.get("metadata") or {}
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError as exc:
            raise SnapshotCorruptError("AGE checkpoint metadata is invalid JSON") from exc
    if not isinstance(metadata, dict):
        metadata = {}
    created_at = raw.get("created_at", raw.get("timestamp_epoch", 0))
    timestamp_epoch = int(float(created_at) * 1000) if created_at else 0
    if timestamp_epoch < 10_000_000_000:
        timestamp_epoch *= 1000
    checkpoint_id = str(raw.get("checkpoint_id") or raw.get("id") or "")
    tensor = _coerce_tensor(
        {"mu": centroids, "shape": raw.get("shape") or np.asarray(centroids).shape},
        checkpoint_id or "unknown",
    )
    return {
        "backup_id": checkpoint_id,
        "mu": tensor.tolist(),
        "shape": list(tensor.shape),
        "timestamp_epoch": timestamp_epoch,
        "step": int(raw.get("step", raw.get("decisions_count", 0)) or 0),
        "sha256": str(raw.get("sha256") or metadata.get("sha256") or ""),
        "version": raw.get("version", "age-checkpoint"),
        "metadata": metadata,
    }


def _age_payloads() -> list[dict[str, Any]]:
    rows = _age_store().get_centroid_checkpoints("soc", include_v2=True, limit=None)
    payloads: list[dict[str, Any]] = []
    for row in rows:
        try:
            payloads.append(_checkpoint_payload(row))
        except SnapshotCorruptError as exc:
            log.warning("[TIME_MACHINE] Skipping incomplete AGE checkpoint: %s", exc)
    return payloads


def _coerce_tensor(payload: dict[str, Any], snapshot_id: str) -> np.ndarray:
    try:
        tensor = np.array(payload["mu"], dtype=np.float64)
    except Exception as exc:
        raise SnapshotCorruptError(f"Snapshot {snapshot_id} tensor parse failed: {exc}") from exc

    shape = payload.get("shape")
    if list(tensor.shape) != list(shape or []):
        raise SnapshotCorruptError(
            f"Snapshot {snapshot_id} shape mismatch: payload={shape}, actual={list(tensor.shape)}"
        )
    return tensor


def _decision_count(payload: dict[str, Any]) -> int:
    metadata = payload.get("metadata") or {}
    value = metadata.get("decision_count", payload.get("step", 0))
    try:
        return int(value)
    except Exception:
        return 0


def _snapshot_meta(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "snapshot_id": payload.get("backup_id", ""),
        "timestamp": int(payload.get("timestamp_epoch", 0)),
        "timestamp_epoch": int(payload.get("timestamp_epoch", 0)),
        "decision_count": _decision_count(payload),
        "step": int(payload.get("step", 0) or 0),
        "sha256": payload.get("sha256", ""),
        "file_path": "",
        "version": payload.get("version"),
        "shape": payload.get("shape"),
        "metadata": payload.get("metadata"),
    }


def _frobenius_distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b))


def _mean_abs_distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean(np.abs(a - b)))


def _compute_current_ceiling_estimate() -> float | None:
    scorer = get_profile_scorer()
    if scorer is None:
        return None
    try:
        sigma = np.array([SOC_FACTOR_SIGMA[f] for f in SOC_FACTORS], dtype=np.float64)
        report = compute_snr_report(
            centroids=np.asarray(scorer.centroids, dtype=np.float64),
            sigma=sigma,
            categories=list(_EXPORT_CATEGORIES),
            actions=list(SCORER_ACTIONS),
            factor_names=list(SOC_FACTORS),
        )
        return float(report.mean_ceiling_estimate * 100.0)
    except Exception:
        return None


def list_snapshots() -> list[dict[str, Any]]:
    """
    Return valid snapshot metadata sorted by timestamp ascending.
    """
    results = [_snapshot_meta(payload) for payload in _age_payloads()]

    results.sort(key=lambda item: (item["timestamp_epoch"], item["snapshot_id"]))
    return results


def _load_snapshot(snapshot_id: str) -> dict[str, Any]:
    payloads = _age_payloads()
    if not snapshot_id:
        if not payloads:
            raise SnapshotNotFoundError("No AGE centroid checkpoints are available")
        return max(payloads, key=lambda item: (item["timestamp_epoch"], item["snapshot_id"]))
    for payload in payloads:
        if payload.get("backup_id") == snapshot_id:
            return payload
    raise SnapshotNotFoundError(f"Snapshot not found: {snapshot_id}")


def get_snapshot(snapshot_id: str) -> dict[str, Any]:
    payload = _load_snapshot(snapshot_id)
    tensor = _coerce_tensor(payload, snapshot_id)

    mu_zero = get_mu_zero()
    drift_from_bootstrap = None
    drift_from_bootstrap_mean_abs = None
    if mu_zero is not None and list(mu_zero.shape) == list(tensor.shape):
        drift_from_bootstrap = _frobenius_distance(tensor, mu_zero)
        drift_from_bootstrap_mean_abs = _mean_abs_distance(tensor, mu_zero)

    scorer = get_profile_scorer()
    drift_from_current = None
    if scorer is not None:
        current = np.array(scorer.centroids, dtype=np.float64)
        if list(current.shape) == list(tensor.shape):
            drift_from_current = _frobenius_distance(tensor, current)

    return {
        **_snapshot_meta(payload),
        "centroids": payload["mu"],
        "drift_from_bootstrap": drift_from_bootstrap,
        "drift_from_bootstrap_mean_abs": drift_from_bootstrap_mean_abs,
        "drift_from_current": drift_from_current,
    }


def compare_snapshots(id_a: str, id_b: str) -> dict[str, Any]:
    payload_a = _load_snapshot(id_a)
    payload_b = _load_snapshot(id_b)
    tensor_a = _coerce_tensor(payload_a, id_a)
    tensor_b = _coerce_tensor(payload_b, id_b)

    if tensor_a.shape != tensor_b.shape:
        raise SnapshotCorruptError(
            f"Snapshot shapes do not match: {list(tensor_a.shape)} vs {list(tensor_b.shape)}"
        )

    diff = tensor_b - tensor_a
    overall_distance = _frobenius_distance(tensor_b, tensor_a)

    per_category_distances: dict[str, float] = {}
    per_category_action_distances: dict[str, dict[str, float]] = {}
    movers: list[dict[str, Any]] = []

    for cat_idx, category in enumerate(_EXPORT_CATEGORIES):
        cat_slice = diff[cat_idx]
        per_category_distances[category] = float(np.linalg.norm(cat_slice))
        action_distances: dict[str, float] = {}
        for action_idx, action in enumerate(_EXPORT_ACTIONS):
            action_distance = float(np.linalg.norm(cat_slice[action_idx]))
            action_distances[action] = action_distance
            movers.append({
                "category": category,
                "action": action,
                "distance": action_distance,
            })
        per_category_action_distances[category] = action_distances

    movers.sort(key=lambda item: (-item["distance"], item["category"], item["action"]))
    top_movers = movers[:5]

    mu_zero = get_mu_zero()
    drift_a = None
    drift_b = None
    movement_direction = "unknown"
    if mu_zero is not None and list(mu_zero.shape) == list(tensor_a.shape):
        drift_a = _frobenius_distance(tensor_a, mu_zero)
        drift_b = _frobenius_distance(tensor_b, mu_zero)
        if drift_b < drift_a:
            movement_direction = "toward_bootstrap"
        elif drift_b > drift_a:
            movement_direction = "away_from_bootstrap"
        else:
            movement_direction = "unchanged"

    return {
        "snapshot_a": _snapshot_meta(payload_a),
        "snapshot_b": _snapshot_meta(payload_b),
        "overall_frobenius_distance": overall_distance,
        "per_category_distances": per_category_distances,
        "per_category_action_distances": per_category_action_distances,
        "top_movers": top_movers,
        "movement_direction": movement_direction,
        "drift_from_bootstrap": {
            "snapshot_a": drift_a,
            "snapshot_b": drift_b,
        },
        "timeline": {
            "timestamps": [
                int(payload_a.get("timestamp_epoch", 0)),
                int(payload_b.get("timestamp_epoch", 0)),
            ],
            "decision_counts": [
                _decision_count(payload_a),
                _decision_count(payload_b),
            ],
        },
    }


def compare_to_bootstrap(snapshot_id: str) -> dict[str, Any]:
    """
    Compare a snapshot against mu_zero (bootstrap centroids).

    Returns the same shape as compare_snapshots so the frontend can use the
    existing comparison UI without changes.
    """
    payload = _load_snapshot(snapshot_id)
    tensor = _coerce_tensor(payload, snapshot_id)

    mu_zero = get_mu_zero()
    if mu_zero is None:
        raise RuntimeError("Bootstrap centroids (mu_zero) not available")

    mu_zero_arr = np.asarray(mu_zero, dtype=np.float64)
    if tensor.shape != mu_zero_arr.shape:
        raise SnapshotCorruptError(
            f"Snapshot shape {list(tensor.shape)} does not match bootstrap shape {list(mu_zero_arr.shape)}"
        )

    diff = mu_zero_arr - tensor
    overall_distance = _frobenius_distance(tensor, mu_zero_arr)

    per_category_distances: dict[str, float] = {}
    per_category_action_distances: dict[str, dict[str, float]] = {}
    movers: list[dict[str, Any]] = []

    for cat_idx, category in enumerate(_EXPORT_CATEGORIES):
        cat_slice = diff[cat_idx]
        per_category_distances[category] = float(np.linalg.norm(cat_slice))
        action_distances: dict[str, float] = {}
        for action_idx, action in enumerate(_EXPORT_ACTIONS):
            action_distance = float(np.linalg.norm(cat_slice[action_idx]))
            action_distances[action] = action_distance
            movers.append({"category": category, "action": action, "distance": action_distance})
        per_category_action_distances[category] = action_distances

    movers.sort(key=lambda item: (-item["distance"], item["category"], item["action"]))

    movement_direction = "unchanged" if overall_distance == 0.0 else "away_from_bootstrap"

    bootstrap_meta = {
        "snapshot_id": "bootstrap",
        "timestamp": 0,
        "timestamp_epoch": 0,
        "decision_count": 0,
        "step": 0,
        "sha256": "",
        "file_path": "",
        "version": "bootstrap",
        "shape": list(mu_zero_arr.shape),
        "metadata": None,
    }

    return {
        "snapshot_a": _snapshot_meta(payload),
        "snapshot_b": bootstrap_meta,
        "overall_frobenius_distance": overall_distance,
        "per_category_distances": per_category_distances,
        "per_category_action_distances": per_category_action_distances,
        "top_movers": movers[:5],
        "movement_direction": movement_direction,
        "drift_from_bootstrap": {
            "snapshot_a": overall_distance,
            "snapshot_b": 0.0,
        },
        "timeline": {
            "timestamps": [int(payload.get("timestamp_epoch", 0)), 0],
            "decision_counts": [_decision_count(payload), 0],
        },
    }


async def get_evolution_timeline(graph_client: Any) -> dict[str, Any]:
    timeline: list[dict[str, Any]] = []
    mu_zero = get_mu_zero()
    current_ceiling = _compute_current_ceiling_estimate()

    for payload in _age_payloads():
        meta = _snapshot_meta(payload)
        tensor = _coerce_tensor(payload, meta["snapshot_id"])
        drift = None
        if mu_zero is not None and list(mu_zero.shape) == list(tensor.shape):
            drift = _frobenius_distance(tensor, mu_zero)

        timeline.append({
            "snapshot_id": meta["snapshot_id"],
            "timestamp": meta["timestamp_epoch"],
            "timestamp_epoch": meta["timestamp_epoch"],
            "decision_count": meta["decision_count"],
            "sha256": meta["sha256"],
            "file_path": meta["file_path"],
            "drift_from_bootstrap": drift,
            "iks_estimate": drift,
            "ceiling_estimate": current_ceiling,
        })

    current_iks = {
        "iks_v2": 0.0,
        "components": {},
        "interpretation": "unavailable",
    }
    try:
        current_iks = await compute_iks_v2(graph_client)
    except Exception as exc:
        log.warning("[TIME_MACHINE] IKS estimate unavailable: %s", exc)

    return {
        "timeline": timeline,
        "current": {
            "iks_v2": current_iks.get("iks_v2", 0.0),
            "components": current_iks.get("components", {}),
            "interpretation": current_iks.get("interpretation", "unavailable"),
        },
        "ceiling_estimate": current_ceiling,
        "ceiling_note": _CEILING_NOTE,
        "categories": list(_EXPORT_CATEGORIES),
        "actions": list(_EXPORT_ACTIONS),
        "factors": list(_DEFAULT_FACTORS),
    }
