"""
Decision Factor Breakdown Service — Explainability for agent decisions

Provides a weighted 6-factor matrix showing how the agent scored each
decision. The sixth factor (threat_intel_enrichment) is queried live
from Neo4j, using the ASSOCIATED_WITH relationship written by
services/threat_intel.py during Threat Intel refresh.

Factor schema:
  name          str   — factor identifier
  value         float — 0.0–1.0 signal strength
  weight        float — importance in decision matrix
  contribution  str   — "high" / "medium" / "low" / "none"
  explanation   str   — plain English reason

Endpoint:
  GET /api/triage/decision-factors/{alert_id}
"""
import asyncio
from typing import Any, Dict, List, Optional

from app.db.neo4j import neo4j_client


# ============================================================================
# Severity → numeric value mapping (mirrors threat_intel.py SEVERITY_SCORE)
# ============================================================================

_SEVERITY_VALUE: Dict[str, float] = {
    "critical": 1.0,
    "high":     0.8,
    "medium":   0.5,
    "low":      0.2,
    "none":     0.0,
}


# ============================================================================
# Helpers (private)
# ============================================================================

async def _build_threat_intel_factor(alert_id: str) -> Dict[str, Any]:
    """
    Query Neo4j for ThreatIntel nodes linked to alert_id via ASSOCIATED_WITH.
    Returns a factor dict for threat_intel_enrichment.

    Relationship direction (confirmed from threat_intel.py):
        (ThreatIntel)-[:ASSOCIATED_WITH]->(Alert)
    """
    from app.domains.soc.factors import _contribution
    query = """
    MATCH (t:ThreatIntel)-[:ASSOCIATED_WITH]->(a:Alert {id: $alert_id})
    RETURN t.value AS ioc_value, t.severity AS severity, t.source AS source
    """
    try:
        results = await neo4j_client.run_query(query, {"alert_id": alert_id})
    except Exception as exc:
        print(f"[TRIAGE] Neo4j threat-intel query failed for {alert_id}: {exc}")
        results = []

    if not results:
        return {
            "name":         "threat_intel_enrichment",
            "value":        0.0,
            "weight":       0.75,
            "contribution": "none",
            "explanation":  "No threat intel data — click Refresh Threat Intel in Tab 3",
        }

    # Pick the highest-severity IOC
    best_row = None
    best_val = -1.0
    for row in results:
        sev = (row.get("severity") or "none").lower()
        val = _SEVERITY_VALUE.get(sev, 0.0)
        if val > best_val:
            best_val = val
            best_row = row

    sev_str    = (best_row.get("severity") or "none").lower()
    source     = best_row.get("source", "unknown")
    ioc_val    = best_row.get("ioc_value", "unknown")
    count      = len(results)
    source_lbl = "Pulsedive (live)" if "pulsedive" in str(source).lower() else "local fallback"
    explanation = (
        f"{source_lbl}: {ioc_val} — risk={sev_str} "
        f"({count} associated IOC{'s' if count != 1 else ''})"
    )

    return {
        "name":         "threat_intel_enrichment",
        "value":        best_val,
        "weight":       0.75,
        "contribution": _contribution(best_val, 0.75),
        "explanation":  explanation,
    }


# ============================================================================
# Public API
# ============================================================================

async def _get_alert_type(alert_id: str) -> str:
    """
    Query Neo4j for the alert_type property of the given alert_id.
    Returns "" on miss or error (compute_soc_factors falls back to _default).
    """
    query = "MATCH (a:Alert {id: $alert_id}) RETURN a.alert_type AS alert_type LIMIT 1"
    try:
        results = await neo4j_client.run_query(query, {"alert_id": alert_id})
        if results:
            return results[0].get("alert_type") or ""
    except Exception as exc:
        print(f"[TRIAGE] alert_type lookup failed for {alert_id}: {exc}")
    return ""


async def get_decision_factors(alert_id: str) -> Optional[Dict[str, Any]]:
    """
    Return the 6-factor decision breakdown for alert_id.

    Builds 5 static factors from SOC_FACTOR_TEMPLATES (keyed first by
    alert_id, then by alert_type, then "_default"), queries Neo4j for the
    live threat_intel_enrichment factor, inserts it at index 2, and returns
    the full factor matrix.

    Final factor order:
      [0] primary factor (varies by alert type)
      [1] secondary factor
      [2] threat_intel_enrichment  ← live Neo4j query
      [3] time_anomaly
      [4] device/source/pattern factor
      [5] pattern_history
    """
    from app.domains.soc.factors import compute_soc_factors
    alert_type, ti_factor = await asyncio.gather(
        _get_alert_type(alert_id),
        _build_threat_intel_factor(alert_id),
    )
    result = compute_soc_factors(alert_id, ti_factor, alert_type)
    print(
        f"[TRIAGE] get_decision_factors({alert_id}): "
        f"alert_type={alert_type!r}, "
        f"{len(result['factors'])} factors, "
        f"ti_contribution={ti_factor['contribution']}"
    )
    return result
