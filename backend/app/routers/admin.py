"""
Admin router — privileged reset operations (TD-026).

POST /api/admin/reset   Atomic soft or hard reset via StateManager.

Requires {"confirm": true} in the request body as an explicit safety gate.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

_VALID_MODES = {"soft", "hard"}


class ResetRequest(BaseModel):
    mode:    str  = "soft"   # "soft" | "hard"
    confirm: bool = False    # must be set to true explicitly — no default allow


@router.post("/admin/reset")
async def admin_reset(body: ResetRequest):
    """
    Atomically reset GAE learning state, audit chain, and Neo4j.

    - **soft**: reset W → priors, clear Decision outcomes (keep nodes), fresh audit chain.
    - **hard**: same as soft, plus delete Decision nodes and re-seed graph.

    `confirm` must be `true` — acts as an explicit safety acknowledgement.

    Returns
    -------
    {
      "status": "reset_complete",
      "mode":   "soft" | "hard",
      "learning_state": {"W_shape": [n_a, n_f], "decision_count": 0}
    }
    """
    if not body.confirm:
        raise HTTPException(
            status_code=400,
            detail="confirm must be true to execute a reset",
        )

    if body.mode not in _VALID_MODES:
        raise HTTPException(
            status_code=400,
            detail=f"mode must be one of {sorted(_VALID_MODES)}",
        )

    from app.services.state_manager import StateManager, ResetError
    from app.services import gae_state, audit as audit_store
    from app.db.neo4j import neo4j_client
    from app.core.domain_registry import get_domain_config

    sm = StateManager(
        learning_state_service=gae_state,
        audit_store=audit_store,
        neo4j_service=neo4j_client,
        domain_config=get_domain_config(),
    )

    try:
        if body.mode == "soft":
            learning_state = await sm.soft_reset()
        else:
            learning_state = await sm.hard_reset()
    except ResetError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "status":         "reset_complete",
        "mode":           body.mode,
        "learning_state": learning_state,
    }
