"""SOC demo-beat read models backed by the live AGE graph.

These routes are deliberately thin presentation adapters.  The learning,
authority, explainability, evolution, and audit services remain the sources
of truth; this module gives the SOC tabs stable, beat-oriented endpoints.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.domains.soc.config import SOC_CATEGORIES, SOC_FACTORS
from app.db.graph_client import graph_client
from app.routers.authority import get_authority
from app.routers.explain import no_precedent as explain_no_precedent
from app.routers.explain import what_if as explain_what_if
from app.routers.soc_learning import get_frozen_comparison, get_learning_control_room
from app.services.accuracy_trajectory import build_accuracy_trajectory
from app.services.authority_ladder import get_authority_manager
from app.services.gae_state import get_profile_scorer

router = APIRouter()


async def _decision_counts() -> dict[str, int]:
    """Read live SOC decision counts, including categories with no history."""
    try:
        rows = await graph_client.run_query(
            "MATCH (d:Decision) "
            "WHERE d.domain = 'soc' "
            "RETURN d.category AS category, count(*) AS decisions",
            {},
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail="SOC AGE decision counts unavailable") from exc
    counts = {category: 0 for category in SOC_CATEGORIES}
    for row in rows:
        category = row.get("category")
        if category in counts:
            counts[category] = int(row.get("decisions") or 0)
    return counts


async def _recent_decisions(limit: int = 100) -> list[dict[str, Any]]:
    try:
        rows = await graph_client.run_query(
            "MATCH (d:Decision) "
            "WHERE d.domain = 'soc' "
            "RETURN d.decision_id AS decision_id, d.category AS category, "
            "d.action AS action, d.correct AS correct, "
            "d.timestamp_epoch AS timestamp_epoch "
            "ORDER BY d.timestamp_epoch DESC LIMIT $limit",
            {"limit": limit},
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail="SOC AGE decision history unavailable") from exc
    return [dict(row) for row in rows]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/learning/control-room")
async def learning_control_room() -> dict[str, Any]:
    """Stable alias for the live SOC learning control room."""
    payload = await get_learning_control_room()
    convergence = payload.get("convergence") or []
    categories = [item.get("category") for item in convergence if item.get("category")]
    if not categories:
        categories = list(SOC_CATEGORIES)
    scorer = get_profile_scorer()
    learning_rate = getattr(scorer, "eta_override", None) if scorer is not None else None
    return {
        **payload,
        "categories": categories,
        "learning_rate": learning_rate,
        "recent_centroid_shifts": (payload.get("centroid_history") or [])[-20:],
        "source": "live AGE GraphStore",
        "generated_at": _now(),
    }


@router.get("/learning/autonomy-ladder")
async def autonomy_ladder() -> dict[str, Any]:
    """Expose earned autonomy with the persisted per-category stage records."""
    authority = await get_authority()
    records = authority.get("categories", [])
    return {
        "stages": ["shadow", "qualified", "autonomous"],
        "categories": records,
        "time_in_stage": [
            {
                "category": record.get("category"),
                "stage": record.get("stage") or record.get("authority"),
                "entered_at": record.get("updated_at") or record.get("created_at"),
            }
            for record in records
        ],
        "source": "persisted SOC authority ladder",
    }


@router.get("/learning/frozen-twin")
async def frozen_twin() -> dict[str, Any]:
    """Expose the measured frozen-vs-live comparison and replay scope."""
    comparison = await get_frozen_comparison()
    decisions = await _recent_decisions()
    return {
        **comparison,
        "current_vs_frozen": comparison,
        "decisions_frozen_would_have_missed": comparison.get("decisions_since_freeze", []),
        "replay_candidates": [item.get("decision_id") for item in decisions],
        "source": "live AGE decisions and immutable SOC day-zero snapshot",
    }


@router.get("/context/no-precedent")
async def no_precedent_alerts(limit: int = Query(50, ge=1, le=200)) -> dict[str, Any]:
    """List live SOC alerts that have no linked historical decision."""
    try:
        rows = await graph_client.run_query(
            "MATCH (a:Alert) WHERE a.domain = 'soc' "
            "OPTIONAL MATCH (d:Decision)-[:DECIDED_ON]->(a) "
            "WITH a, count(d) AS similar_count WHERE similar_count = 0 "
            "RETURN a.alert_id AS alert_id, a.category AS category, "
            "a.alert_type AS alert_type, 1.0 AS novelty_score, "
            "[] AS nearest_matches LIMIT $limit",
            {"limit": limit},
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail="SOC AGE novelty query unavailable") from exc
    alerts = [dict(row) for row in rows]
    return {
        "alerts": alerts,
        "count": len(alerts),
        "novelty_definition": "1.0 means no historical Decision is linked to the alert",
        "source": "live AGE GraphStore",
    }


@router.get("/context/what-if/{alert_id}")
async def what_if_alert(alert_id: str) -> dict[str, Any]:
    """Return measured factor boundaries that would change an alert action."""
    return await explain_what_if(alert_id=alert_id, current_action=None)


@router.get("/diagnostics/day-zero")
async def day_zero() -> dict[str, Any]:
    """Report live category coverage and the remaining readiness gaps."""
    counts = await _decision_counts()
    readiness = []
    for category in SOC_CATEGORIES:
        verified = counts[category]
        readiness.append({
            "category": category,
            "decision_count": verified,
            "coverage": "covered" if verified else "gap",
            "ready": bool(verified),
            "missing": [] if verified else ["verified decisions", "category-specific evidence"],
        })
    return {
        "ready": all(item["ready"] for item in readiness),
        "categories": readiness,
        "coverage_gaps": [item["category"] for item in readiness if not item["ready"]],
        "checklist": ["source coverage", "provenance", "verified evidence", "authority gate"],
        "source": "live AGE GraphStore; no learned weights used for readiness",
    }


@router.get("/diagnostics/frontier")
async def frontier() -> dict[str, Any]:
    """Show which live categories have crossed the current safety bar."""
    counts = await _decision_counts()
    control = await get_learning_control_room()
    conservation = control.get("conservation") or {}
    safety_bar = int(conservation.get("theta_min") or 0)
    categories = [
        {"category": category, "decisions": count, "above_safety_bar": count >= safety_bar}
        for category, count in counts.items()
    ]
    return {
        "safety_bar": safety_bar,
        "above": [item["category"] for item in categories if item["above_safety_bar"]],
        "below": [item["category"] for item in categories if not item["above_safety_bar"]],
        "frontier": categories,
        "trend": "measured from live decision counts; historical trend requires additional AGE timestamps",
        "source": "live AGE GraphStore and conservation state",
    }


# SC-11 → SC-16 stable aliases. Existing routes remain canonical and are not
# duplicated; these adapters make the tab contracts explicit.
@router.get("/diagnostics/centroid-timeline")
async def centroid_timeline() -> dict[str, Any]:
    from app.routers.framework_router import get_centroid_evolution

    return {"timeline": await get_centroid_evolution()}


@router.get("/diagnostics/accuracy-alerts")
async def accuracy_alerts() -> dict[str, Any]:
    counts = await _decision_counts()
    trajectory = build_accuracy_trajectory(counts)
    return {"alerts": [], "trajectory": trajectory, "source": "live decision counts"}


@router.get("/evolution/rule-genealogy")
async def rule_genealogy() -> dict[str, Any]:
    from app.routers.evolution import get_recent_events

    return {"events": await get_recent_events(limit=100), "source": "live evolution ledger"}


@router.get("/diagnostics/decision-explorer")
async def decision_explorer(limit: int = Query(50, ge=1, le=200)) -> dict[str, Any]:
    return {"decisions": await _recent_decisions(limit), "source": "live AGE GraphStore"}


@router.get("/evolution/rule-lifecycle")
async def rule_lifecycle() -> dict[str, Any]:
    from app.routers.evolution import get_recent_evolution

    return {"lifecycle": await get_recent_evolution(), "source": "live evolution ledger"}


@router.get("/diagnostics/audit-trail")
async def audit_trail() -> dict[str, Any]:
    from app.routers.audit import get_audit_decisions

    return {"audit": await get_audit_decisions(format="json"), "source": "live audit chain"}
