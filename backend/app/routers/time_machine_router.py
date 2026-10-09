"""
API routes for Centroid Time Machine.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.db.graph_client import graph_client
from app.services.time_machine import (
    SnapshotCorruptError,
    SnapshotNotFoundError,
    compare_snapshots,
    compare_to_bootstrap,
    get_evolution_timeline,
    get_snapshot,
    list_snapshots,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _unavailable_timeline(reason: str) -> dict[str, object]:
    """Return the stable HTTP envelope when timeline construction fails."""
    return {
        "timeline": [],
        "current": {
            "iks_v2": 0.0,
            "components": {},
            "interpretation": "unavailable",
        },
        "ceiling_estimate": 0.0,
        "ceiling_note": "",
        "ceiling_available": False,
        "categories": [],
        "actions": [],
        "factors": [],
        "timeline_available": False,
        "iks_available": False,
        "data_available": False,
        "degraded": True,
        "reason": reason,
    }


@router.get("/time-machine/snapshots")
async def list_snapshots_endpoint():
    try:
        return {"snapshots": list_snapshots()}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/time-machine/snapshots/{snapshot_id}")
async def get_snapshot_endpoint(snapshot_id: str):
    try:
        return get_snapshot(snapshot_id)
    except SnapshotNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SnapshotCorruptError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/time-machine/compare")
async def compare_snapshots_endpoint(a: str, b: str):
    try:
        return compare_snapshots(a, b)
    except SnapshotNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SnapshotCorruptError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/time-machine/compare-bootstrap")
async def compare_bootstrap_endpoint(snapshot_id: str):
    try:
        return compare_to_bootstrap(snapshot_id)
    except SnapshotNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SnapshotCorruptError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/time-machine/timeline")
async def get_timeline_endpoint():
    try:
        timeline = await get_evolution_timeline(graph_client)
    except Exception as exc:
        logger.warning("Timeline construction failed: %s", exc)
        timeline = None
    if timeline is None:
        return _unavailable_timeline("Timeline construction failed")
    return timeline
