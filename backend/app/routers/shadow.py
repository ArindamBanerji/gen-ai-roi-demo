"""Explicit ShadowDecision promotion controls."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.services import shadow_promotion

router = APIRouter()


class ShadowPromotionRequest(BaseModel):
    shadow_decision_id: str
    approval_token: str
    actor: str


class ShadowDecisionRequest(BaseModel):
    shadow_decision_id: str


@router.get("/shadow/eligibility/{shadow_decision_id}")
async def shadow_eligibility(shadow_decision_id: str):
    return await shadow_promotion.evaluate_eligibility(shadow_decision_id)


@router.post("/shadow/preview")
async def shadow_preview(request: ShadowDecisionRequest):
    return await shadow_promotion.preview_promotion(request.shadow_decision_id)


@router.post("/shadow/promote")
async def shadow_promote(request: ShadowPromotionRequest):
    return await shadow_promotion.promote(
        request.shadow_decision_id, request.approval_token, request.actor,
    )
