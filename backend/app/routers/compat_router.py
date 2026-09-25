"""SDK-compatible read aliases for SOC demo and cross-copilot tooling."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse


router = APIRouter()


def _json_safe(value: Any) -> Any:
    if is_dataclass(value):
        return _json_safe(asdict(value))
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "tolist"):
        return _json_safe(value.tolist())
    return value


def _compound_scorer() -> Any:
    from app.services.gae_state import get_profile_scorer

    scorer = get_profile_scorer()
    if scorer is None:
        raise HTTPException(status_code=503, detail="SOC scorer is not initialized")
    return getattr(scorer, "_compound", scorer)


@router.get("/fingerprint")
async def fingerprint_alias() -> dict[str, Any]:
    """Expose SOC geometry and factor reliability at the standard SDK path."""

    from app.domains.soc.config import SCORER_ACTIONS, SOC_CATEGORIES, SOC_FACTORS

    scorer = _compound_scorer()
    try:
        raw = _json_safe(scorer.fingerprint())
        payload = dict(raw) if isinstance(raw, dict) else {}
        tensor_shape = [len(SOC_CATEGORIES), len(SCORER_ACTIONS), len(SOC_FACTORS)]
        payload.update(
            {
                "engine": {"domain": "soc", "version": "5.148"},
                "categories": list(SOC_CATEGORIES),
                "actions": list(SCORER_ACTIONS),
                "factor_names": list(SOC_FACTORS),
                "tensor_shape": tensor_shape,
                "geometry": {
                    "category_count": len(SOC_CATEGORIES),
                    "action_count": len(SCORER_ACTIONS),
                    "factor_count": len(SOC_FACTORS),
                    "tensor_shape": tensor_shape,
                },
            }
        )
        return payload
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="SOC fingerprint unavailable") from exc


@router.get("/trajectory")
async def trajectory_alias() -> dict[str, Any]:
    """Expose the SOC compound scorer trajectory at the standard SDK path."""

    scorer = _compound_scorer()
    try:
        raw = _json_safe(scorer.trajectory())
        if not isinstance(raw, dict):
            raise TypeError("SOC trajectory returned an unsupported payload")
        raw.setdefault("points", [])
        raw.setdefault("current_iks", 0.0)
        raw.setdefault("current_win_rate", 0.0)
        raw.setdefault("decisions_total", 0)
        raw.setdefault("days_active", 0.0)
        raw.setdefault("engine", {"domain": "soc", "version": "5.148"})
        return raw
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="SOC trajectory unavailable") from exc


@router.get("/conservation/status", response_model=None)
async def conservation_status_alias() -> dict[str, Any] | JSONResponse:
    """Delegate the SDK-standard conservation path to SOC learning health."""

    from app.routers.framework_router import learning_health

    try:
        raw = await learning_health()
        if not isinstance(raw, dict):
            raise TypeError("SOC conservation returned an unsupported payload")
        components = raw.get("components")
        components = components if isinstance(components, dict) else {}
        nested = raw.get("conservation")
        nested = nested if isinstance(nested, dict) else {}
        verified_count = int(components.get("V", components.get("n", 0)) or 0)
        status = str(raw.get("status") or nested.get("status") or "UNKNOWN")
        return {
            **raw,
            "engine": {"domain": "soc", "version": "5.148"},
            "domain": "soc",
            "verified_count": verified_count,
            "correct_count": int(components.get("correct_count", 0) or 0),
            "total_decisions": int(components.get("n", verified_count) or 0),
            "alpha": float(components.get("alpha", raw.get("alpha", 0.0)) or 0.0),
            "q": float(components.get("q", raw.get("q", 0.0)) or 0.0),
            "V": verified_count,
            "baseline": raw.get("baseline"),
            "baseline_q": raw.get("baseline_q", raw.get("baseline")),
            "passed": status == "GREEN",
            "status": status,
        }
    except RuntimeError as exc:
        return JSONResponse(
            status_code=503,
            content={
                "status": "UNAVAILABLE",
                "reason": "Conservation dependency unavailable",
                "detail": str(exc),
            },
        )
