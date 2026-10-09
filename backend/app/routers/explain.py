"""SOC no-precedent and factor counterfactual inspection endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.domains.soc.config import resolve_alert_category
from app.db.graph_client import graph_client
from app.services.soc_explainability import build_detector, build_inspector
from app.services.triage import (
    FactorReadUnavailable, get_decision_factors, validated_decision_factors,
)
from copilot_sdk.backend.graph_access import GRAPH_CONNECTION_ERRORS

router = APIRouter()


async def _explain_context(alert_id: str) -> tuple[str, list[float]]:
    # Guard provider fetch and vector construction together. A failed read is
    # not a missing alert, and absent values must never become neutral evidence.
    try:
        alert = await graph_client.get_alert(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
        factors = await get_decision_factors(alert_id)
        _, values = validated_decision_factors(factors)
    except (FactorReadUnavailable, *GRAPH_CONNECTION_ERRORS) as exc:
        raise HTTPException(status_code=503, detail="Decision factors unavailable") from exc
    context = await graph_client.get_security_context(alert_id)
    alert_type = (context or {}).get("alert_type") or alert.get("alert_type") or ""
    category = resolve_alert_category(alert_type)
    if category == "unclassified":
        raise HTTPException(status_code=422, detail="Alert type is not mapped to a SOC category")
    return category, values


@router.get("/soc/explain/no-precedent")
async def no_precedent(alert_id: str = Query(..., min_length=1)) -> dict[str, Any]:
    category, values = await _explain_context(alert_id)
    try:
        return build_detector().detect(values, category).to_dict()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/soc/explain/what-if")
async def what_if(
    alert_id: str = Query(..., min_length=1),
    current_action: str | None = Query(default=None),
) -> dict[str, Any]:
    category, values = await _explain_context(alert_id)
    try:
        inspector = build_inspector()
        action = current_action
        if action is None:
            from app.services.gae_state import get_profile_scorer

            scorer = get_profile_scorer()
            if scorer is None:
                raise RuntimeError("SOC ProfileScorer is not initialized")
            action = scorer.score(values, category_index=inspector.detector._category_index(category)).action_name
        return inspector.inspect(values, category, action).to_dict()
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
