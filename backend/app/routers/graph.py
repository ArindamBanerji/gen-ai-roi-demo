"""
Graph Intelligence Router — Threat Intel endpoints

Exposes POST /api/graph/threat-intel/refresh which fetches from Pulsedive
(or falls back to hardcoded IOCs) and writes :ThreatIntel nodes to Neo4j.
"""
from fastapi import APIRouter, HTTPException

from app.services.threat_intel import refresh_threat_intel

router = APIRouter()


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
