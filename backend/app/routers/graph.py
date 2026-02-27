"""
Graph Intelligence Router — Threat Intel + UCL Connector endpoints

Existing endpoint (backward compat):
  POST /api/graph/threat-intel/refresh

New endpoints added in C1 (UCL Connector base + registry):
  GET  /api/graph/connectors               — list all registered connectors + health
  POST /api/graph/connectors/refresh-all   — refresh all connectors, return combined results

New endpoints added in C4a (multi-source aggregation):
  GET  /api/graph/enrichment/aggregate/{indicator}  — unified enrichment for one indicator
  GET  /api/graph/enrichment/summary                — unified enrichment for ALL indicators

New endpoint added in C4b (bug fix — alert-id keyed enrichment):
  GET  /api/graph/enrichment/by-alert/{alert_id}    — enrichment for a specific alert via graph traversal
"""
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from app.connectors.registry import registry
from app.db.neo4j import neo4j_client
from app.services.threat_intel import refresh_threat_intel

router = APIRouter()


# ---------------------------------------------------------------------------
# C4a: Private helpers — multi-source aggregation
# ---------------------------------------------------------------------------

def _consensus_severity(sources: Dict[str, Dict]) -> str:
    """
    Derive a single severity label from all source-specific values.

    Priority order:
      1. Any source "critical" or "malicious"  → "critical"
      2. Any source "high"                     → "high"
      3. All sources "low" or "benign"         → "low"
      4. Otherwise                             → "medium"
    """
    all_values: List[str] = []
    for data in sources.values():
        raw = data.get("severity") or data.get("classification") or ""
        if raw:
            all_values.append(raw.lower())

    if not all_values:
        return "unknown"
    if any(v in ("critical", "malicious") for v in all_values):
        return "critical"
    if any(v == "high" for v in all_values):
        return "high"
    if all(v in ("low", "benign") for v in all_values):
        return "low"
    return "medium"


def _build_view(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a raw Neo4j record into the unified enrichment view shape.

    The record is expected to contain columns returned by _ENRICHMENT_QUERY_*:
      value, type, severity, context, risk_factors  (from :ThreatIntel)
      gn_classification, gn_noise, gn_riot, gn_name (from :GreyNoiseEnrichment)
    gn_* columns are None when the OPTIONAL MATCH found no node.
    """
    sources: Dict[str, Any] = {}

    # Pulsedive data — present whenever a :ThreatIntel node exists
    pd: Dict[str, Any] = {}
    if record.get("type"):
        pd["type"] = record["type"]
    if record.get("severity"):
        pd["severity"] = record["severity"]
    if record.get("context"):
        pd["context"] = record["context"]
    if record.get("risk_factors"):
        pd["risk_factors"] = record["risk_factors"]
    if pd:
        sources["pulsedive"] = pd

    # GreyNoise data — only present when :ENRICHED_BY link exists
    if record.get("gn_classification") is not None:
        sources["greynoise"] = {
            "classification": record["gn_classification"],
            "noise":          record.get("gn_noise"),
            "riot":           record.get("gn_riot"),
            "name":           record.get("gn_name"),
        }

    return {
        "indicator":          record.get("value", ""),
        "sources":            sources,
        "source_count":       len(sources),
        "consensus_severity": _consensus_severity(sources),
    }


# Cypher queries shared by both aggregate endpoints

_ENRICHMENT_QUERY_ONE = """
MATCH (ti:ThreatIntel {value: $indicator})
OPTIONAL MATCH (ti)-[:ENRICHED_BY]->(gn:GreyNoiseEnrichment)
RETURN
    ti.value          AS value,
    ti.type           AS type,
    ti.severity       AS severity,
    ti.context        AS context,
    ti.risk_factors   AS risk_factors,
    gn.classification AS gn_classification,
    gn.noise          AS gn_noise,
    gn.riot           AS gn_riot,
    gn.name           AS gn_name
"""

_ENRICHMENT_QUERY_ALL = """
MATCH (ti:ThreatIntel)
OPTIONAL MATCH (ti)-[:ENRICHED_BY]->(gn:GreyNoiseEnrichment)
RETURN
    ti.value          AS value,
    ti.type           AS type,
    ti.severity       AS severity,
    ti.context        AS context,
    ti.risk_factors   AS risk_factors,
    gn.classification AS gn_classification,
    gn.noise          AS gn_noise,
    gn.riot           AS gn_riot,
    gn.name           AS gn_name
ORDER BY ti.value
"""

# C4b — alert-keyed enrichment: traverse (ThreatIntel)-[:ASSOCIATED_WITH]->(Alert)
# OPTIONAL MATCH means: if no ThreatIntel is linked the query returns one row of NULLs
_ENRICHMENT_QUERY_BY_ALERT = """
MATCH (alert:Alert {id: $alert_id})
OPTIONAL MATCH (ti:ThreatIntel)-[:ASSOCIATED_WITH]->(alert)
OPTIONAL MATCH (ti)-[:ENRICHED_BY]->(gn:GreyNoiseEnrichment)
RETURN
    ti.value          AS value,
    ti.type           AS type,
    ti.severity       AS severity,
    ti.context        AS context,
    ti.risk_factors   AS risk_factors,
    gn.classification AS gn_classification,
    gn.noise          AS gn_noise,
    gn.riot           AS gn_riot,
    gn.name           AS gn_name
"""


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


# ---------------------------------------------------------------------------
# C4a: Multi-source enrichment aggregation endpoints
# ---------------------------------------------------------------------------

@router.get("/graph/enrichment/aggregate/{indicator}")
async def get_enrichment_aggregate(indicator: str):
    """
    Return a unified enrichment view for a single indicator (IP or domain).

    Queries Neo4j for the :ThreatIntel node matching the indicator value and
    any linked :GreyNoiseEnrichment node (:ENRICHED_BY relationship).

    Response shape:
        {
          "indicator": "103.15.42.17",
          "sources": {
            "pulsedive":  {"type": "ip", "severity": "high", "context": "..."},
            "greynoise":  {"classification": "malicious", "noise": true, "riot": false, "name": "Unknown"}
          },
          "source_count": 2,
          "consensus_severity": "critical"
        }

    Returns 404 when the indicator is not found in the graph.
    """
    print(f"[GRAPH] GET /graph/enrichment/aggregate/{indicator} called")
    try:
        records = await neo4j_client.run_query(
            _ENRICHMENT_QUERY_ONE, {"indicator": indicator}
        )
    except Exception as exc:
        print(f"[ERROR] Enrichment aggregate query failed for {indicator!r}: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Enrichment query failed: {str(exc)}",
        )

    if not records:
        raise HTTPException(
            status_code=404,
            detail=f"Indicator {indicator!r} not found in enrichment graph",
        )

    view = _build_view(records[0])
    print(
        f"[GRAPH] Aggregate for {indicator!r}: "
        f"sources={list(view['sources'].keys())}, "
        f"consensus={view['consensus_severity']}"
    )
    return view


@router.get("/graph/enrichment/summary")
async def get_enrichment_summary():
    """
    Return unified enrichment views for ALL indicators in the graph.

    Queries every :ThreatIntel node and joins any linked :GreyNoiseEnrichment
    data, returning a list sorted by indicator value.

    Response shape:
        {
          "indicators": [...],   // list of unified view objects
          "total": N,
          "by_severity": {"critical": 1, "high": 2, "medium": 1, "low": 0, "unknown": 0}
        }
    """
    print("[GRAPH] GET /graph/enrichment/summary called")
    try:
        records = await neo4j_client.run_query(_ENRICHMENT_QUERY_ALL, {})
    except Exception as exc:
        print(f"[ERROR] Enrichment summary query failed: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Enrichment summary query failed: {str(exc)}",
        )

    views = [_build_view(r) for r in records]

    # Tally by consensus severity for dashboard convenience
    by_severity: Dict[str, int] = {
        "critical": 0, "high": 0, "medium": 0, "low": 0, "unknown": 0
    }
    for v in views:
        sev = v["consensus_severity"]
        by_severity[sev] = by_severity.get(sev, 0) + 1

    print(
        f"[GRAPH] Enrichment summary: total={len(views)}, "
        f"by_severity={by_severity}"
    )
    return {
        "indicators":   views,
        "total":        len(views),
        "by_severity":  by_severity,
    }


@router.get("/graph/enrichment/by-alert/{alert_id}")
async def get_enrichment_by_alert(alert_id: str):
    """
    Return unified multi-source enrichment for a specific alert (C4b fix).

    Traverses the graph path:
        (ThreatIntel)-[:ASSOCIATED_WITH]->(Alert {id: alert_id})
        (ThreatIntel)-[:ENRICHED_BY]->(GreyNoiseEnrichment)

    The :ASSOCIATED_WITH relationship is created by the Pulsedive connector
    (ALERT_IOC_MAP).  This endpoint is the correct way to look up enrichment
    for an alert because:
      - Alert.source_location is a city name, not an IP
      - Alert.source_ip may differ from the enriched IOC value
      - Only the graph relationship reliably connects alerts to indicators

    Always returns HTTP 200.  Use `has_enrichment` / `source_count` to detect
    the empty state — no 404 is raised.

    Response shape:
        {
          "alert_id": "ALERT-7823",
          "has_enrichment": true,
          "indicators": ["103.15.42.17"],
          "sources": {
            "pulsedive":  {"type": "ip", "severity": "high", "context": "..."},
            "greynoise":  {"classification": "malicious", "noise": true, "riot": false}
          },
          "source_count": 2,
          "consensus_severity": "critical"
        }
    """
    print(f"[GRAPH] GET /graph/enrichment/by-alert/{alert_id} called")
    try:
        records = await neo4j_client.run_query(
            _ENRICHMENT_QUERY_BY_ALERT, {"alert_id": alert_id}
        )
    except Exception as exc:
        print(f"[ERROR] Enrichment by-alert query failed for {alert_id!r}: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Enrichment query failed: {str(exc)}",
        )

    # Filter out the all-NULL row that OPTIONAL MATCH produces when no ThreatIntel
    # is linked to the alert.
    valid_records = [r for r in records if r.get("value") is not None]

    if not valid_records:
        print(f"[GRAPH] No ThreatIntel linked to {alert_id!r}")
        return {
            "alert_id":           alert_id,
            "has_enrichment":     False,
            "indicators":         [],
            "sources":            {},
            "source_count":       0,
            "consensus_severity": "unknown",
        }

    # Aggregate enrichment across all linked ThreatIntel nodes (usually just one)
    merged_sources: Dict[str, Any] = {}
    indicators: List[str] = []

    for record in valid_records:
        view = _build_view(record)
        indicator_value = view.get("indicator", "")
        if indicator_value and indicator_value not in indicators:
            indicators.append(indicator_value)
        # Merge source dicts — per-source name, later records overwrite earlier
        # duplicates (same IOC queried twice is impossible via OPTIONAL MATCH)
        merged_sources.update(view["sources"])

    result = {
        "alert_id":           alert_id,
        "has_enrichment":     True,
        "indicators":         indicators,
        "sources":            merged_sources,
        "source_count":       len(merged_sources),
        "consensus_severity": _consensus_severity(merged_sources),
    }

    print(
        f"[GRAPH] Enrichment for {alert_id!r}: "
        f"indicators={indicators}, "
        f"sources={list(merged_sources.keys())}, "
        f"consensus={result['consensus_severity']}"
    )
    return result
