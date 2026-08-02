"""
API routes for Centroid Time Machine.
"""

from __future__ import annotations

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


@router.get("/time-machine/snapshots")
async def list_snapshots_endpoint():
    return {"snapshots": list_snapshots()}


@router.get("/time-machine/snapshots/{snapshot_id}")
async def get_snapshot_endpoint(snapshot_id: str):
    try:
        return get_snapshot(snapshot_id)
    except SnapshotNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SnapshotCorruptError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/time-machine/compare")
async def compare_snapshots_endpoint(a: str, b: str):
    try:
        return compare_snapshots(a, b)
    except SnapshotNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SnapshotCorruptError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


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
    return await get_evolution_timeline(graph_client)
