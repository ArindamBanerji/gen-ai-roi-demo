"""
Centroid Time Machine service helpers.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, cast

import numpy as np

from gae.snr import compute_snr_report

from app.domains.soc.config import SCORER_ACTIONS, SOC_FACTORS, SOC_FACTOR_SIGMA
from app.services.gae_state import (
    _EXPORT_ACTIONS,
    _EXPORT_CATEGORIES,
    _BACKUP_DIR as GAE_BACKUP_DIR,
    get_mu_zero,
    get_profile_scorer,
)
from app.services.iks import compute_iks_v2

_CEILING_NOTE = (
    "Ceiling values are an approximate structural estimate for relative comparison only; "
    "they are not predicted accuracy."
)

log = logging.getLogger(__name__)

_BACKUP_DIR = GAE_BACKUP_DIR
_DEFAULT_FACTORS = list(SOC_FACTORS)


class SnapshotNotFoundError(FileNotFoundError):
    """Raised when a requested snapshot file does not exist."""


class SnapshotCorruptError(ValueError):
    """Raised when a snapshot file is unreadable or fails validation."""


def _ensure_backup_dir() -> Path:
    _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return _BACKUP_DIR


def _snapshot_path(snapshot_id: str) -> Path:
    return _ensure_backup_dir() / f"{snapshot_id}.json"


def _canonical_snapshot_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if key not in {"sha256", "backup_id", "metadata"}
    }


def _read_snapshot_file(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SnapshotCorruptError(f"Failed to read snapshot {path.name}: {exc}") from exc

    if not isinstance(payload, dict):
        raise SnapshotCorruptError(f"Snapshot {path.name} did not contain a JSON object")

    required = {"mu", "shape", "timestamp_epoch", "sha256"}
    missing = required - set(payload)
    if missing:
        raise SnapshotCorruptError(
            f"Snapshot {path.name} missing required keys: {sorted(missing)}"
        )

    try:
        canonical = json.dumps(_canonical_snapshot_payload(payload), sort_keys=True)
        expected_sha = __import__("hashlib").sha256(canonical.encode()).hexdigest()
    except Exception as exc:
        raise SnapshotCorruptError(f"Snapshot {path.name} could not be hashed: {exc}") from exc

    if payload.get("sha256") != expected_sha:
        raise SnapshotCorruptError(
            f"Snapshot {path.name} checksum mismatch: stored={payload.get('sha256')!r} "
            f"computed={expected_sha!r}"
        )

    return payload


def _safe_read_snapshot(path: Path) -> dict[str, Any] | None:
    try:
        return _read_snapshot_file(path)
    except SnapshotCorruptError as exc:
        log.warning("[TIME_MACHINE] Skipping corrupted snapshot %s: %s", path.name, exc)
        return None


def _coerce_tensor(payload: dict[str, Any], snapshot_id: str) -> np.ndarray:
    try:
        tensor = np.array(payload["mu"], dtype=np.float64)
    except Exception as exc:
        raise SnapshotCorruptError(f"Snapshot {snapshot_id} tensor parse failed: {exc}") from exc

    shape = payload.get("shape")
    if list(tensor.shape) != list(cast(Any, shape)):
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


def _snapshot_meta(payload: dict[str, Any], path: Path) -> dict[str, Any]:
    return {
        "snapshot_id": payload.get("backup_id", path.stem),
        "timestamp": int(payload.get("timestamp_epoch", 0)),
        "timestamp_epoch": int(payload.get("timestamp_epoch", 0)),
        "decision_count": _decision_count(payload),
        "step": int(payload.get("step", 0) or 0),
        "sha256": payload.get("sha256", ""),
        "file_path": str(path),
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
    results: list[dict[str, Any]] = []
    for path in _ensure_backup_dir().glob("centroid_backup_[0-9]*.json"):
        payload = _safe_read_snapshot(path)
        if payload is None:
            continue
        results.append(_snapshot_meta(payload, path))

    results.sort(key=lambda item: (item["timestamp_epoch"], item["snapshot_id"]))
    return results


def _load_snapshot(snapshot_id: str) -> tuple[dict[str, Any], Path]:
    path = _snapshot_path(snapshot_id)
    if not path.exists():
        raise SnapshotNotFoundError(f"Snapshot not found: {snapshot_id}")
    return _read_snapshot_file(path), path


def get_snapshot(snapshot_id: str) -> dict[str, Any]:
    payload, path = _load_snapshot(snapshot_id)
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
        **_snapshot_meta(payload, path),
        "centroids": payload["mu"],
        "drift_from_bootstrap": drift_from_bootstrap,
        "drift_from_bootstrap_mean_abs": drift_from_bootstrap_mean_abs,
        "drift_from_current": drift_from_current,
    }


def compare_snapshots(id_a: str, id_b: str) -> dict[str, Any]:
    payload_a, path_a = _load_snapshot(id_a)
    payload_b, path_b = _load_snapshot(id_b)
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
        "snapshot_a": _snapshot_meta(payload_a, path_a),
        "snapshot_b": _snapshot_meta(payload_b, path_b),
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
    payload, path = _load_snapshot(snapshot_id)
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
        "snapshot_a": _snapshot_meta(payload, path),
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


async def get_evolution_timeline(neo4j_client: Any) -> dict[str, Any]:
    timeline: list[dict[str, Any]] = []
    mu_zero = get_mu_zero()
    current_ceiling = _compute_current_ceiling_estimate()

    for meta in list_snapshots():
        payload, _ = _load_snapshot(meta["snapshot_id"])
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
        current_iks = await compute_iks_v2(neo4j_client)
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
