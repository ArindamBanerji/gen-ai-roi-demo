"""
Graph Intelligence Router — Threat Intel + UCL Connector endpoints

Existing endpoint (backward compat):
  POST /api/graph/threat-intel/refresh

New endpoints added in C1 (UCL Connector base + registry):
  GET  /api/graph/connectors               — list all registered connectors + health
  POST /api/graph/connectors/refresh-all   — refresh all connectors, return combined results
"""
from fastapi import APIRouter, HTTPException

from app.services.threat_intel import refresh_threat_intel
from app.connectors.registry import registry

router = APIRouter()


# ---------------------------------------------------------------------------
# Existing endpoint — keep working (backward compat for C3 and beyond)
# ---------------------------------------------------------------------------

@router.post("/graph/threat-intel/refresh")
async def refresh_threat_intel_endpoint():
    """
    Refresh threat intelligence for all curated IOCs.

    Calls Pulsedive live API if PULSEDIVE_API_KEY is set; otherwise uses the
    hardcoded fallback set.  Writes / updates :ThreatIntel nodes in Neo4j and
    creates :ASSOCIATED_WITH relationships to relevant :Alert nodes.

    Returns a summary: source, indicators_ingested, relationships_created,
    enrichment_summary, live_attempted, live_succeeded, timestamp.
    """
    print("[GRAPH] POST /graph/threat-intel/refresh called")
    try:
        summary = await refresh_threat_intel()
        print(
            f"[GRAPH] Refresh complete — "
            f"ingested={summary['indicators_ingested']}, "
            f"relationships={summary['relationships_created']}, "
            f"source={summary['source']}"
        )
        return summary
    except Exception as exc:
        print(f"[ERROR] Threat intel refresh failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Threat intel refresh failed: {str(exc)}",
        )


# ---------------------------------------------------------------------------
# C1: UCL Connector registry endpoints
# ---------------------------------------------------------------------------

@router.get("/graph/connectors")
async def list_connectors():
    """
    List all registered UCL connectors with individual health status.

    Returns {"connectors": [...], "count": N} where each entry includes
    name, type, description, and health status from health_check().
    Before C3 (Pulsedive refactor): returns empty list.
    """
    print("[GRAPH] GET /graph/connectors called")
    connector_list = registry.list_all()

    # Run health checks for all registered connectors
    health_statuses = await registry.health_check_all()
    health_by_name = {s.source: s.to_dict() for s in health_statuses}

    # Merge static metadata with live health status
    enriched = []
    for entry in connector_list:
        enriched.append({
            **entry,
            "health": health_by_name.get(entry["name"], {"healthy": None, "message": "not checked"}),
        })

    return {
        "connectors": enriched,
        "count": len(enriched),
    }


@router.post("/graph/connectors/refresh-all")
async def refresh_all_connectors():
    """
    Trigger refresh() on every registered UCL connector.

    Each connector pulls from its source, writes to Neo4j, and returns a
    ConnectorResult summary.  Failures per connector are captured and included
    in the response rather than aborting the whole request.

    Before C3 (Pulsedive refactor): returns empty results list.
    """
    print("[GRAPH] POST /graph/connectors/refresh-all called")
    results = await registry.refresh_all()
    total_ingested = sum(r.indicators_ingested for r in results)
    total_relationships = sum(r.relationships_created for r in results)
    print(
        f"[GRAPH] refresh_all complete — "
        f"sources={len(results)}, "
        f"total_ingested={total_ingested}, "
        f"total_relationships={total_relationships}"
    )
    return {
        "results": [r.to_dict() for r in results],
        "total_sources": len(results),
        "total_indicators_ingested": total_ingested,
        "total_relationships_created": total_relationships,
    }
