"""
GAE learning state endpoints — weight matrix, history, convergence.

Exposes the live LearningState singleton for dashboard display and
convergence monitoring.  All responses come from the in-process
singleton; no Neo4j queries needed.

Reference: docs/soc_copilot_design_v1.md §14.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from typing import Any, Dict, List

import numpy as np
from gae.convergence import get_convergence_metrics

from app.services.gae_state import get_learning_state

router = APIRouter()

_NO_DATA_MSG = (
    "Process alerts and provide feedback to see learning curves"
)
_MIN_CONVERGENCE_DECISIONS = 20
_CONVERGENCE_MIN_MSG = (
    "Minimum 20 decisions required for convergence assessment"
)

# Trust-curve simulation constants (mirror the 20:1 asymmetric learning ratio).
_TRUST_INITIAL    = 0.50   # starting trust level per action
_TRUST_EARN       = 0.03   # correct outcome → slow trust gain
_TRUST_LOSE       = 0.60   # incorrect outcome → fast trust loss (≈ 20:1)
_REVIEW_THRESHOLD = 0.30   # trust below this → flag for human review


def _wu_timestamp(wu) -> str:
    """Convert a WeightUpdate unix timestamp to ISO-8601 string."""
    try:
        return datetime.fromtimestamp(wu.timestamp, tz=timezone.utc).isoformat()
    except Exception:
        return str(wu.timestamp)


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
    Convergence is suppressed (converged=False) when decision_count < 20:
    a sample this small makes stability=0 and accuracy=1.0 by construction,
    which would falsely report converged=True after just a handful of decisions.
    """
    try:
        state = get_learning_state()
        metrics = get_convergence_metrics(state)

        if state.decision_count < 3:
            message = _NO_DATA_MSG
        elif state.decision_count < _MIN_CONVERGENCE_DECISIONS:
            message = _CONVERGENCE_MIN_MSG
        else:
            message = None

        # Suppress false-positive convergence for small sample sizes.
        # stability=0 AND accuracy=1.0 satisfy the criterion by construction
        # when fewer than 20 decisions exist — not meaningful signal.
        if state.decision_count < _MIN_CONVERGENCE_DECISIONS:
            metrics = {**metrics, "converged": False}

        # weight_snapshots: last 10 Frobenius norms for sparkline display.
        weight_snapshots = [
            round(float(np.linalg.norm(wu.W_after, "fro")), 6)
            for wu in state.history[-10:]
        ]

        return {**metrics, "weight_snapshots": weight_snapshots, "message": message}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"gae/convergence failed: {exc}")


# ============================================================================
# GET /api/gae/confidence-trajectory
# ============================================================================

@router.get("/gae/confidence-trajectory")
async def gae_confidence_trajectory() -> Dict[str, Any]:
    """
    Return per-action confidence over time, sourced from learning_state history.

    Each WeightUpdate.confidence_at_decision records the softmax max-probability
    at the moment the decision was made.  Entries are grouped by action_name for
    a multi-line chart showing how confident the model became for each action
    class as the W matrix learned.

    Empty state: returns trajectories={} when no outcomes have been submitted.
    """
    try:
        state = get_learning_state()
        if not state.history:
            return {"trajectories": {}, "message": _NO_DATA_MSG}

        trajectories: Dict[str, List[Dict[str, Any]]] = {}
        for wu in state.history:
            action = wu.action_name
            if action not in trajectories:
                trajectories[action] = []
            trajectories[action].append({
                "decision_number": wu.decision_number,
                "confidence":      round(wu.confidence_at_decision, 4),
                "action":          action,
                "outcome":         wu.outcome,
                "timestamp":       _wu_timestamp(wu),
            })

        return {"trajectories": trajectories, "message": None}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"gae/confidence-trajectory failed: {exc}")


# ============================================================================
# GET /api/gae/trust-curve
# ============================================================================

@router.get("/gae/trust-curve")
async def gae_trust_curve() -> Dict[str, Any]:
    """
    Simulate cumulative trust per action class from learning history.

    Trust logic mirrors the 20:1 asymmetric learning ratio (LAMBDA_NEG=20):
        correct   → trust += 0.03  (slow earn)
        incorrect → trust -= 0.60  (fast lose)
    Clamped to [0, 1].  Initialised at 0.50 per action.

    below_threshold flags points where trust fell under review_threshold (0.30),
    indicating the action class needs human oversight.

    Grouped by action_name.  Empty state: curves={} when no decisions exist.
    """
    try:
        state = get_learning_state()
        if not state.history:
            return {
                "curves":           {},
                "review_threshold": _REVIEW_THRESHOLD,
                "message":          _NO_DATA_MSG,
            }

        trust: Dict[str, float] = {}
        curves: Dict[str, List[Dict[str, Any]]] = {}

        for wu in state.history:
            action = wu.action_name
            if action not in trust:
                trust[action] = _TRUST_INITIAL
                curves[action] = []

            if wu.outcome == 1:
                trust[action] = min(1.0, trust[action] + _TRUST_EARN)
            else:
                trust[action] = max(0.0, trust[action] - _TRUST_LOSE)

            curves[action].append({
                "decision_number": wu.decision_number,
                "trust_level":     round(trust[action], 4),
                "outcome":         wu.outcome,
                "below_threshold": trust[action] < _REVIEW_THRESHOLD,
                "timestamp":       _wu_timestamp(wu),
            })

        return {
            "curves":           curves,
            "review_threshold": _REVIEW_THRESHOLD,
            "message":          None,
        }
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"gae/trust-curve failed: {exc}")


# ============================================================================
# GET /api/gae/before-after
# ============================================================================

@router.get("/gae/before-after")
async def gae_before_after() -> Dict[str, Any]:
    """
    Compare first vs latest decision confidence from learning history.

    Returns first and last WeightUpdate entries with confidence values, an
    improvement_pp (percentage-point delta), total decision count, and the
    set of action names seen.

    Returns ready=false when fewer than 2 outcomes have been submitted.
    """
    try:
        state = get_learning_state()
        if len(state.history) < 2:
            return {
                "ready":   False,
                "message": "Need at least 2 decisions to show before/after comparison",
            }

        first  = state.history[0]
        latest = state.history[-1]

        improvement_pp = round(
            (latest.confidence_at_decision - first.confidence_at_decision) * 100, 2
        )
        actions_seen = list({wu.action_name for wu in state.history})

        return {
            "ready": True,
            "first_decision": {
                "decision_number": first.decision_number,
                "confidence":      round(first.confidence_at_decision, 4),
                "action":          first.action_name,
                "timestamp":       _wu_timestamp(first),
            },
            "latest_decision": {
                "decision_number": latest.decision_number,
                "confidence":      round(latest.confidence_at_decision, 4),
                "action":          latest.action_name,
                "timestamp":       _wu_timestamp(latest),
            },
            "improvement_pp":       improvement_pp,
            "total_decisions":      state.decision_count,
            "situation_types_seen": actions_seen,
            "message":              None,
        }
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"gae/before-after failed: {exc}")


# ============================================================================
# GET /api/gae/weight-evolution
# ============================================================================

@router.get("/gae/weight-evolution")
async def gae_weight_evolution() -> Dict[str, Any]:
    """
    Return per-update weight change magnitudes for sparkline display.

    Each entry: decision_number, action, outcome, delta_norm (||delta_applied||),
    W_norm_after (||W_after||_F).

    Empty state: returns evolution=[] when no outcomes have been submitted.
    """
    try:
        state = get_learning_state()
        if not state.history:
            return {"evolution": [], "message": _NO_DATA_MSG}

        evolution = [
            {
                "decision_number": wu.decision_number,
                "action":          wu.action_name,
                "outcome":         wu.outcome,
                "delta_norm":      round(float(np.linalg.norm(wu.delta_applied)), 6),
                "W_norm_after":    round(float(np.linalg.norm(wu.W_after, "fro")), 6),
            }
            for wu in state.history
        ]

        return {"evolution": evolution, "message": None}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"gae/weight-evolution failed: {exc}")
