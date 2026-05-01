from __future__ import annotations

from typing import List

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from app.services.whatif_service import PRESETS, WhatIfScenario, get_presets, run_preset, run_whatif


router = APIRouter()


class WhatIfScenarioPayload(BaseModel):
    name: str = "custom"
    description: str = ""
    alpha: float = 0.25
    V: float = 200.0
    q_initial: float = 0.80
    q_target: float = 0.80
    q_ramp_days: int = 0
    horizon_days: int = 30
    disruption_day: int | None = None
    disruption_delta: float = 0.0
    eta: float = 0.05
    n_half: float = 14.0
    t_max_days: float = 21.0
    iks_initial: float = 50.0
    iks_gain_green: float = 0.8
    iks_gain_amber: float = 0.3
    iks_gain_red: float = -0.2


def _validate_payload(p: WhatIfScenarioPayload) -> List[str]:
    """FIX-15: Return a list of validation error strings; empty = valid."""
    errors: List[str] = []
    if not (0.0 <= p.q_initial <= 1.0):
        errors.append(f"q_initial must be in [0, 1], got {p.q_initial}")
    if not (0.0 <= p.q_target <= 1.0):
        errors.append(f"q_target must be in [0, 1], got {p.q_target}")
    if not (0.001 <= p.alpha <= 1.0):
        errors.append(f"alpha must be in [0.001, 1], got {p.alpha}")
    if not (1 <= p.V <= 10000):
        errors.append(f"V must be in [1, 10000], got {p.V}")
    if not (1 <= p.horizon_days <= 365):
        errors.append(f"horizon_days must be in [1, 365], got {p.horizon_days}")
    if p.q_ramp_days < 0:
        errors.append(f"q_ramp_days must be >= 0, got {p.q_ramp_days}")
    if not (0.001 <= p.eta <= 1.0):
        errors.append(f"eta must be in [0.001, 1], got {p.eta}")
    return errors


@router.post("/whatif/project")
async def project_whatif(body: WhatIfScenarioPayload):
    errors = _validate_payload(body)
    if errors:
        raise HTTPException(status_code=400, detail=errors)
    scenario = WhatIfScenario(**body.model_dump())
    return run_whatif(scenario).to_dict()


@router.get("/whatif/presets")
async def list_whatif_presets():
    presets = get_presets()
    return {
        "count": len(presets),
        "presets": presets,
    }


@router.get("/whatif/presets/{preset_name}")
async def run_whatif_preset(preset_name: str):
    if preset_name not in PRESETS:
        raise HTTPException(status_code=404, detail=f"Unknown preset: {preset_name}")
    return run_preset(preset_name).to_dict()
