"""
SOC Judgment API — JUDG-1-SOC

Translates a raw ProfileScorer decision into a human-readable JudgmentResult:
why an action was recommended, which factors dominated, and confidence tier.

Reference: docs/soc_copilot_design_v1.md §18; gae/judgment.py.
"""

from typing import Dict, Optional

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from gae.judgment import compute_judgment
from app.domains.soc.config import SOC_CATEGORIES, SOC_FACTORS, SOC_ACTIONS
from app.db.neo4j import neo4j_client

router = APIRouter()

# ── Constants ────────────────────────────────────────────────────────────────
# Factor names in centroid order — derived from SOC_FACTORS in config.py.
# Do not hardcode factor names here; use SOC_FACTORS directly.
# SOC_ACTIONS imported from config — do not redeclare here (v5.5)
# SOC_ACTIONS = ["escalate", "investigate", "suppress", "monitor", "refer_to_analyst"]

# Backward-compat map: current factor name → legacy persisted property name
_LEGACY_FACTOR_NAMES: dict[str, str] = {
    "privileged_identity_context": "travel_match",
}


# ── Request model ─────────────────────────────────────────────────────────────

class JudgmentRequest(BaseModel):
    category: str
    factors: Dict[str, float]
    alert_id: Optional[str] = None


# ── Pure helper — exported for tests ─────────────────────────────────────────

def _build_factor_vector(factors: Dict[str, float]) -> np.ndarray:
    return np.array(
        [factors.get(f, 0.5) for f in SOC_FACTORS],
        dtype=np.float64,
    )


def build_judgment_response(
    category: str,
    factors: Dict[str, float],
    scorer,
    alert_id: Optional[str] = None,
) -> dict:
    """
    Pure computation helper: score + compute_judgment -> response dict.
    Exported so tests can call it directly without the HTTP layer.
    Assumes category is valid (in SOC_CATEGORIES) and all modeled factors are present.
    """
    category_index = SOC_CATEGORIES.index(category)
    f = _build_factor_vector(factors)
    scoring_result = scorer.score(f, category_index)
    judgment = compute_judgment(
        scoring_result=scoring_result,
        f=f,
        mu=scorer.centroids,
        category_index=category_index,
        factor_names=SOC_FACTORS,
        actions=scorer.actions,
    )
    return {
        "alert_id": alert_id,
        "category": category,
        "action": judgment.action,
        "confidence": judgment.confidence,
        "confidence_tier": judgment.confidence_tier,
        "dominant_factors": judgment.dominant_factors,
        "factor_contributions": judgment.factor_contributions,
        "rationale": judgment.rationale,
        "action_scores": judgment.action_scores,
        "auto_approvable": judgment.auto_approvable,
    }


# ── POST /judgment/explain ────────────────────────────────────────────────────

@router.post("/judgment/explain")
async def explain_decision_post(request: JudgmentRequest):
    """
    Explain a ProfileScorer decision for a given factor vector.
    Returns human-readable rationale, dominant factors, and confidence tier.
    Does NOT trigger learning.
    """
    from app.services.gae_state import get_profile_scorer

    if request.category not in SOC_CATEGORIES:
        raise HTTPException(
            status_code=422,
            detail={"error": f"Unknown category: {request.category}"},
        )

    missing = [f for f in SOC_FACTORS if f not in request.factors]
    if missing:
        raise HTTPException(
            status_code=422,
            detail={"error": f"Missing factors: {missing}"},
        )

    if any(not (0.0 <= v <= 1.0) for v in request.factors.values()):
        raise HTTPException(
            status_code=422,
            detail={"error": "Factor values must be in [0.0, 1.0]"},
        )

    try:
        scorer = get_profile_scorer()
    except Exception:
        scorer = None

    if scorer is None:
        raise HTTPException(
            status_code=503,
            detail={"error": "ProfileScorer not available"},
        )

    return build_judgment_response(
        category=request.category,
        factors=request.factors,
        scorer=scorer,
        alert_id=request.alert_id,
    )


# ── GET /judgment/explain/{alert_id} ─────────────────────────────────────────

@router.get("/judgment/explain/{alert_id}")
async def explain_decision_get(alert_id: str):
    """
    Explain the most recent Decision for a given alert_id.
    Loads factor values from the Decision node in Neo4j.
    Returns the same shape as POST /explain.
    """
    from app.services.gae_state import get_profile_scorer

    try:
        rows = await neo4j_client.run_query(
            "MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert {alert_id: $alert_id}) "
            "RETURN d ORDER BY d.timestamp_epoch DESC LIMIT 1",
            {"alert_id": alert_id},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Neo4j query failed: {exc}")

    if not rows:
        return {
            "alert_id": alert_id,
            "category": None,
            "action": None,
            "confidence": None,
            "confidence_tier": None,
            "dominant_factors": [],
            "factor_contributions": [],
            "rationale": None,
            "action_scores": {},
            "auto_approvable": None,
        }

    d = rows[0]["d"]

    try:
        factors = {}
        for fname in SOC_FACTORS:
            legacy = _LEGACY_FACTOR_NAMES.get(fname, fname)
            val = d.get(fname) if d.get(fname) is not None else d.get(legacy)
            if val is None:
                raise KeyError(fname)
            factors[fname] = float(val)
    except (KeyError, TypeError):
        return {
            "alert_id": alert_id,
            "category": None,
            "action": None,
            "confidence": None,
            "confidence_tier": None,
            "dominant_factors": [],
            "factor_contributions": [],
            "rationale": None,
            "action_scores": {},
            "auto_approvable": None,
        }

    category = d.get("category") or d.get("alert_category", "")
    if not category or category not in SOC_CATEGORIES:
        return {
            "alert_id": alert_id,
            "category": None,
            "action": None,
            "confidence": None,
            "confidence_tier": None,
            "dominant_factors": [],
            "factor_contributions": [],
            "rationale": None,
            "action_scores": {},
            "auto_approvable": None,
        }

    try:
        scorer = get_profile_scorer()
    except Exception:
        scorer = None

    if scorer is None:
        raise HTTPException(
            status_code=503,
            detail={"error": "ProfileScorer not available"},
        )

    return build_judgment_response(
        category=category,
        factors=factors,
        scorer=scorer,
        alert_id=alert_id,
    )
