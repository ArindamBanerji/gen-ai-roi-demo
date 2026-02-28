"""
GAE learning state endpoints — weight matrix, history, convergence.

Exposes the live LearningState singleton for dashboard display and
convergence monitoring.  All responses come from the in-process
singleton; no Neo4j queries needed.

Reference: docs/soc_copilot_design_v1.md §14.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from typing import Any, Dict

import numpy as np
from gae.convergence import get_convergence_metrics

from app.services.gae_state import get_learning_state

router = APIRouter()

_NO_DATA_MSG = (
    "Process alerts and provide feedback to see learning curves"
)


# ============================================================================
# GET /api/gae/weights
# ============================================================================

@router.get("/gae/weights")
async def gae_weights() -> Dict[str, Any]:
    """
    Return the live W matrix, factor names, action names, and decision count.

    W is a nested list (n_actions × n_factors) so it is JSON-serializable.
    Rows correspond to SOCDomainConfig.get_actions() order:
        [0] escalate  [1] investigate  [2] suppress  [3] monitor
    """
    try:
        state = get_learning_state()
        from app.domains.soc.config import SOCDomainConfig
        return {
            "W":             state.W.tolist(),
            "factor_names":  state.factor_names,
            "action_names":  SOCDomainConfig.get_actions(),
            "decision_count": state.decision_count,
            "shape":         list(state.W.shape),
        }
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"gae/weights failed: {exc}")


# ============================================================================
# GET /api/gae/history
# ============================================================================

@router.get("/gae/history")
async def gae_history(limit: int = Query(50, ge=1, le=200)) -> Dict[str, Any]:
    """
    Return the last N WeightUpdate records from learning_state.history.

    Each record is serialized with JSON-friendly fields:
        decision_number, action, outcome (+1/-1), delta_norm,
        timestamp (ISO), alpha_effective, confidence_at_decision.

    Returns an empty history with a placeholder message when
    decision_count < 3 (not enough data to show a meaningful curve).
    """
    try:
        state = get_learning_state()

        if state.decision_count < 3:
            return {
                "history": [],
                "total":   0,
                "message": _NO_DATA_MSG,
            }

        recent = state.history[-limit:]
        history_out = []
        for wu in recent:
            try:
                ts = datetime.fromtimestamp(
                    wu.timestamp, tz=timezone.utc
                ).isoformat()
            except Exception:
                ts = str(wu.timestamp)

            history_out.append({
                "decision_number":        wu.decision_number,
                "action":                 wu.action_name,
                "outcome":                wu.outcome,          # +1 or -1
                "delta_norm":             round(float(np.linalg.norm(wu.delta_applied)), 6),
                "timestamp":              ts,
                "alpha_effective":        round(wu.alpha_effective, 6),
                "confidence_at_decision": round(wu.confidence_at_decision, 4),
            })

        return {
            "history": history_out,
            "total":   len(history_out),
            "message": None,
        }
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"gae/history failed: {exc}")


# ============================================================================
# GET /api/gae/convergence
# ============================================================================

@router.get("/gae/convergence")
async def gae_convergence() -> Dict[str, Any]:
    """
    Return convergence metrics computed from the live LearningState.

    Uses gae.convergence.get_convergence_metrics() — see that module for
    the full criterion definition:

        stability  = std(||W_after||_F) over last 10 updates
        accuracy   = fraction of outcome==+1 over last 20 updates
        converged  = stability < 0.05 AND accuracy > 0.80

    Returns a placeholder message when decision_count < 3.
    """
    try:
        state = get_learning_state()
        metrics = get_convergence_metrics(state)
        message = _NO_DATA_MSG if state.decision_count < 3 else None
        return {**metrics, "message": message}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"gae/convergence failed: {exc}")
