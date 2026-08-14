"""Explicit, provenance-preserving ShadowDecision promotion policy.

Shadow outcomes remain diagnostic data until an analyst explicitly approves a
single promotion.  In particular, this module has no call from the shadow
runner, outcome-fill path, startup, or the F9 synthetic loader.
"""

from __future__ import annotations

import time
import os
from dataclasses import dataclass, field
from typing import Any


SHADOW_PROMOTION_RULE_VERSION = "shadow-to-observation-v1"
SHADOW_PROMOTION_CONFIDENCE_THRESHOLD = 0.5
SHADOW_PROMOTION_MIN_SAMPLES = 10
F9_SYNTHETIC_SOURCE = "v_shadow_synthetic_v3"


@dataclass(frozen=True)
class ShadowPromotionDecision:
    status: str
    reason: str
    evidence: dict[str, Any]
    observation: dict[str, Any] | None = field(default=None)


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_f9_synthetic(source: str) -> bool:
    return source.strip().lower() == F9_SYNTHETIC_SOURCE


def evaluate_shadow_promotion(
    shadow: dict[str, Any],
    *,
    manual_approval: bool = False,
    approval_token: str | None = None,
    actor: str | None = None,
    sample_count: int | None = None,
    safety_paused: bool = False,
) -> ShadowPromotionDecision:
    """Evaluate promotion gates without changing graph state."""

    decision_id = str(shadow.get("decision_id") or "").strip()
    source = str(shadow.get("source") or "").strip()
    category = str(shadow.get("category") or "").strip()
    confidence = _number(shadow.get("ai_confidence"))
    analyst_action = str(shadow.get("analyst_action") or "").strip()
    outcome_filled = bool(analyst_action) and shadow.get("analyst_correct") is not None
    evidence = {
        "decision_id": decision_id,
        "source": source,
        "category": category,
        "confidence": confidence,
        "sample_count": sample_count,
        "rule_version": SHADOW_PROMOTION_RULE_VERSION,
        "actor": actor,
    }

    if not decision_id or not source or not category:
        return ShadowPromotionDecision("reject", "field validation failed: identity, provenance, and category are required", evidence)
    if _is_f9_synthetic(source):
        return ShadowPromotionDecision("reject", "F9 synthetic ShadowDecision population is never promotable", evidence)
    if not outcome_filled:
        return ShadowPromotionDecision("hold", "shadow outcome is not filled", evidence)
    if isinstance(shadow.get("ai_confidence"), bool) or confidence is None or not 0.0 <= confidence <= 1.0:
        return ShadowPromotionDecision("reject", "field validation failed: confidence must be between 0 and 1", evidence)
    if not isinstance(shadow.get("analyst_correct"), bool):
        return ShadowPromotionDecision("reject", "field validation failed: analyst_correct must be boolean", evidence)
    if confidence < SHADOW_PROMOTION_CONFIDENCE_THRESHOLD:
        return ShadowPromotionDecision("reject", "shadow confidence is below threshold", evidence)
    if safety_paused:
        return ShadowPromotionDecision("hold", "promotion is safety-paused", evidence)
    if isinstance(sample_count, bool) or not isinstance(sample_count, int) or sample_count < SHADOW_PROMOTION_MIN_SAMPLES:
        return ShadowPromotionDecision("hold", "insufficient shadow samples", evidence)
    if not manual_approval or not approval_token or not actor:
        return ShadowPromotionDecision("hold", "explicit approval, token, and actor are required", evidence)

    evidence["approval_token_present"] = True
    return ShadowPromotionDecision("promote", "all explicit promotion gates passed", evidence)


def _cypher_string(value: Any) -> str:
    return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'"


async def _get_shadow(shadow_decision_id: str, graph_client: Any) -> dict[str, Any] | None:
    rows = await graph_client.run_query(
        """
        MATCH (sd:ShadowDecision {decision_id: $decision_id})
        RETURN sd.decision_id AS decision_id, sd.source AS source,
               sd.category AS category, sd.ai_confidence AS ai_confidence,
               sd.analyst_action AS analyst_action,
               sd.analyst_correct AS analyst_correct
        """,
        {"decision_id": shadow_decision_id},
    )
    return dict(rows[0]) if rows else None


async def _sample_count(source: str, graph_client: Any) -> int:
    rows = await graph_client.run_query(
        """
        MATCH (sd:ShadowDecision {source: $source})
        WHERE sd.analyst_action IS NOT NULL AND sd.analyst_correct IS NOT NULL
        RETURN count(sd) AS sample_count
        """,
        {"source": source},
    )
    return int(rows[0].get("sample_count") or 0) if rows else 0


async def _existing_observation(shadow_decision_id: str, graph_client: Any) -> bool:
    rows = await graph_client.run_query(
        """
        MATCH (o:Observation {source_shadow_decision_id: $decision_id})
        RETURN count(o) AS count
        """,
        {"decision_id": shadow_decision_id},
    )
    return bool(rows and int(rows[0].get("count") or 0))


async def evaluate_eligibility(shadow_decision_id: str, graph_client: Any = None) -> dict[str, Any]:
    """Return a read-only eligibility result for one ShadowDecision."""

    if graph_client is None:
        from app.db.graph_client import graph_client as default_graph_client
        graph_client = default_graph_client
    shadow = await _get_shadow(shadow_decision_id, graph_client)
    if shadow is None:
        return {"eligible": False, "reasons": ["shadow decision was not found"], "decision_id": shadow_decision_id}
    sample_count = await _sample_count(str(shadow.get("source") or ""), graph_client)
    result = evaluate_shadow_promotion(
        shadow, manual_approval=True, approval_token="eligibility-check", actor="eligibility-check",
        sample_count=sample_count, safety_paused=os.getenv("SOC_SHADOW_PROMOTION_PAUSED") == "1",
    )
    reasons = [] if result.status == "promote" else [result.reason]
    if await _existing_observation(shadow_decision_id, graph_client):
        reasons.append("shadow decision was already promoted")
    return {"eligible": not reasons, "reasons": reasons, "evidence": result.evidence}


async def preview_promotion(shadow_decision_id: str, graph_client: Any = None) -> dict[str, Any]:
    """Return the promotion decision without requiring approval or mutating state."""

    if graph_client is None:
        from app.db.graph_client import graph_client as default_graph_client
        graph_client = default_graph_client
    shadow = await _get_shadow(shadow_decision_id, graph_client)
    if shadow is None:
        return {"status": "reject", "reason": "shadow decision was not found", "decision_id": shadow_decision_id}
    sample_count = await _sample_count(str(shadow.get("source") or ""), graph_client)
    result = evaluate_shadow_promotion(
        shadow, sample_count=sample_count,
        safety_paused=os.getenv("SOC_SHADOW_PROMOTION_PAUSED") == "1",
    )
    return {"status": result.status, "reason": result.reason, "evidence": result.evidence, "dry_run": True}


async def promote_shadow_decision(
    shadow: dict[str, Any],
    graph_client: Any,
    *,
    manual_approval: bool = False,
    approval_token: str | None = None,
    actor: str | None = None,
    sample_count: int | None = None,
    safety_paused: bool = False,
) -> ShadowPromotionDecision:
    """Promote exactly one approved ShadowDecision to an Observation."""

    decision = evaluate_shadow_promotion(
        shadow,
        manual_approval=manual_approval,
        approval_token=approval_token,
        actor=actor,
        sample_count=sample_count,
        safety_paused=safety_paused,
    )
    if decision.status != "promote":
        return decision

    decision_id = str(shadow["decision_id"])
    source = str(shadow["source"])
    if await _existing_observation(decision_id, graph_client):
        return ShadowPromotionDecision("reject", "shadow decision was already promoted", decision.evidence)

    now = time.time()
    query = f"""
    MATCH (sd:ShadowDecision {{decision_id: {_cypher_string(decision_id)}}})
    WHERE sd.source = {_cypher_string(source)}
    CREATE (o:Observation {{source_shadow_decision_id: {_cypher_string(decision_id)},
                            source_shadow: {_cypher_string(source)},
                            decision_id: sd.decision_id,
                            category: sd.category,
                            source: 'shadow-promotion',
                            promotion_type: 'explicit',
                            rule_version: {_cypher_string(SHADOW_PROMOTION_RULE_VERSION)},
                            actor: {_cypher_string(actor)},
                            approval_token: {_cypher_string(approval_token)},
                            promoted_at: {now}}})
    CREATE (sd)-[:PROMOTED_TO]->(o)
    RETURN o.source_shadow_decision_id AS source_shadow_decision_id,
           o.source_shadow AS source_shadow, o.category AS category,
           o.promotion_type AS promotion_type
    """
    rows = await graph_client.run_query(query)
    if not rows:
        return ShadowPromotionDecision("reject", "shadow decision was not found", decision.evidence)
    return ShadowPromotionDecision("promote", decision.reason, decision.evidence, dict(rows[0]))


async def promote(shadow_decision_id: str, approval_token: str, actor: str, graph_client: Any = None) -> dict[str, Any]:
    """Explicit promotion command; approval is required at the API boundary."""

    if graph_client is None:
        from app.db.graph_client import graph_client as default_graph_client
        graph_client = default_graph_client
    shadow = await _get_shadow(shadow_decision_id, graph_client)
    if shadow is None:
        return {"status": "reject", "reason": "shadow decision was not found", "decision_id": shadow_decision_id}
    sample_count = await _sample_count(str(shadow.get("source") or ""), graph_client)
    result = await promote_shadow_decision(
        shadow, graph_client, manual_approval=True, approval_token=approval_token,
        actor=actor, sample_count=sample_count,
        safety_paused=os.getenv("SOC_SHADOW_PROMOTION_PAUSED") == "1",
    )
    return {"status": result.status, "reason": result.reason, "evidence": result.evidence, "observation": result.observation}


__all__ = [
    "F9_SYNTHETIC_SOURCE", "SHADOW_PROMOTION_CONFIDENCE_THRESHOLD",
    "SHADOW_PROMOTION_MIN_SAMPLES", "SHADOW_PROMOTION_RULE_VERSION",
    "ShadowPromotionDecision", "evaluate_eligibility", "evaluate_shadow_promotion",
    "preview_promotion", "promote", "promote_shadow_decision",
]
