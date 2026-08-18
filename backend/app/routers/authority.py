"""SOC autonomy-ladder control-room endpoints."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.authority_ladder import AuthorityManager, get_authority_manager

router = APIRouter()


class AuthorityAdvanceRequest(BaseModel):
    conservation_state: str | None = None
    shadow_decisions: int | None = Field(default=None, ge=0)
    measurement_decisions: int | None = Field(default=None, ge=0)
    improvement: float | None = None
    reason: str = "manual_advance"


def _manager() -> AuthorityManager:
    return get_authority_manager()


@router.get("/soc/authority")
async def get_authority() -> dict[str, Any]:
    return {"copilot": "soc", "categories": _manager().get_all()}


@router.get("/soc/authority/{category}")
async def get_authority_detail(category: str) -> dict[str, Any]:
    try:
        return _manager().get_detail(category)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/soc/authority/{category}/advance")
async def advance_authority(category: str, request: AuthorityAdvanceRequest) -> dict[str, Any]:
    try:
        evidence = request.model_dump(exclude_none=True)
        return _manager().advance(category, evidence)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/soc/authority/{category}/circuit-break")
async def circuit_break_authority(category: str) -> dict[str, Any]:
    try:
        return _manager().circuit_break(category)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
