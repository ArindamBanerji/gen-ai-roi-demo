"""SOC Learning Control Room and Frozen Twin routes."""

from __future__ import annotations

import os
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from app.models.responses import LearningControlRoomResponse
from app.services.soc_learning_control import SERVICE, build_control_room


router = APIRouter()


def demo_comparison_enabled() -> bool:
    """Demo presentation can survive restart without enabling snapshot writes."""
    return any(os.getenv(name, "").lower() == "true" for name in (
        "SOC_DEMO_COMPARISON_ENABLED", "SOC_DEMO_RESEED_ENABLED",
    ))


class DemoRefreezeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirm_demo_reseed: Literal[True]


@router.post("/demo/learning/re-freeze", status_code=201)
async def demo_refreeze(request: DemoRefreezeRequest) -> dict[str, Any]:
    """Explicit demo-only replacement; never overwrites the production twin."""
    if os.getenv("SOC_DEMO_RESEED_ENABLED", "").lower() != "true":
        raise HTTPException(status_code=403, detail="SOC_DEMO_RESEED_ENABLED=true is required")
    from app.services.gae_state import get_profile_scorer
    from app.services.iks import compute_iks_v2
    from app.services.learning_health import LearningHealthMonitor

    scorer = get_profile_scorer()
    if scorer is None:
        raise HTTPException(status_code=503, detail="SOC scorer unavailable")
    try:
        health = await LearningHealthMonitor.evaluate(_age_client())
        iks = await compute_iks_v2(_age_client())
        return SERVICE.demo_refreeze(scorer, health, float(iks["iks_v2"]))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=409, detail="Initialize the production twin first") from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Demo re-freeze unavailable; previous baseline retained") from exc


def _age_client() -> Any:
    from app.routers.framework_router import _get_age_client

    return _get_age_client()


@router.get("/soc/learning/control-room", response_model=LearningControlRoomResponse)
async def get_learning_control_room() -> dict[str, Any]:
    """Return the unified centroid/DK/conservation/IKS learning surface."""
    try:
        from app.services.gae_state import get_profile_scorer

        payload = await build_control_room(_age_client())
        try:
            payload["frozen_comparison"] = SERVICE.comparison(
                get_profile_scorer(), float(payload["iks"]["current"]), payload.get("verified_count")
            )
        except FileNotFoundError:
            payload["frozen_comparison"] = None
        return payload
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="SOC learning control room unavailable") from exc


@router.get("/soc/learning/frozen-comparison")
async def get_frozen_comparison(demo: bool = False) -> dict[str, Any]:
    """Return measured divergence between the live scorer and immutable day zero."""
    from app.services.gae_state import get_mu_zero, get_profile_scorer
    from app.services.iks import compute_iks_v2

    if demo and not demo_comparison_enabled():
        raise HTTPException(status_code=403, detail="Demo comparison is not enabled")
    scorer = get_profile_scorer()
    if scorer is None:
        raise HTTPException(status_code=503, detail="SOC ProfileScorer is not initialized")
    if get_mu_zero() is None:
        raise HTTPException(status_code=503, detail="SOC day-zero μ0 is unavailable; Frozen Twin not initialized")
    try:
        iks = await compute_iks_v2(_age_client())
        verified_count = None
        if demo and SERVICE.has_demo_twin():
            from app.services.learning_health import LearningHealthMonitor
            health = await LearningHealthMonitor.evaluate(_age_client())
            verified_count = health.get("components", {}).get("verified_decisions")
        return await SERVICE.measured_comparison(
            _age_client(), scorer, float(iks.get("iks_v2", 0.0) or 0.0), verified_count, demo=demo,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="SOC Frozen Twin has not been initialized") from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="SOC Frozen Twin comparison unavailable") from exc


@router.post("/soc/learning/frozen-comparison/freeze", status_code=201)
async def initialize_frozen_comparison() -> dict[str, Any]:
    """Create the one-time immutable SOC day-zero twin from bootstrap state."""
    from app.services.gae_state import get_mu_zero, get_profile_scorer
    from app.services.iks import compute_iks_v2
    from app.services.learning_health import LearningHealthMonitor

    scorer = get_profile_scorer()
    if scorer is None:
        raise HTTPException(status_code=503, detail="SOC ProfileScorer is not initialized")
    try:
        health = await LearningHealthMonitor.evaluate(_age_client())
        iks = await compute_iks_v2(_age_client())
        return SERVICE.freeze(
            scorer,
            health,
            float(iks.get("iks_v2", 0.0) or 0.0),
            get_mu_zero(),
        )
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="SOC Frozen Twin initialization failed") from exc


@router.get("/soc/learning/convergence")
async def get_learning_convergence() -> dict[str, Any]:
    """Return the per-category convergence section of the Control Room."""
    payload = await get_learning_control_room()
    return {
        "convergence": payload.get("convergence", []),
        "evidence": payload.get("evidence", {}),
    }
