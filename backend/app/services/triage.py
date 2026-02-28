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
from datetime import datetime, timedelta, timezone
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
# F4b: Confidence trajectory tracking
# ============================================================================

# One entry appended per POST /alert/analyze call this session.
# Cleared by reset_confidence_history() via state_manager on demo reset.
CONFIDENCE_HISTORY: List[Dict[str, Any]] = []


def append_confidence_snapshot(
    alert_id: str,
    alert_type: str,
    situation_type: str,
    confidence: float,
) -> None:
    """
    Append one confidence observation to CONFIDENCE_HISTORY.
    Called from routers/triage.py after each alert analysis.

    Args:
        alert_id:       Alert ID (e.g. "ALERT-7823")
        alert_type:     Raw alert type string (e.g. "anomalous_login")
        situation_type: Classified situation from SituationAnalysis
        confidence:     Agent recommendation confidence score (0.0–1.0)
    """
    CONFIDENCE_HISTORY.append({
        "decision_number": len(CONFIDENCE_HISTORY) + 1,
        "timestamp":       datetime.now(timezone.utc).isoformat(),
        "alert_id":        alert_id,
        "alert_type":      alert_type,
        "situation_type":  situation_type,
        "confidence":      round(confidence, 4),
    })
    print(
        f"[TRIAGE] Confidence snapshot #{len(CONFIDENCE_HISTORY)}: "
        f"{situation_type} confidence={confidence:.2%}"
    )


def seed_confidence_history() -> None:
    """
    Pre-populate CONFIDENCE_HISTORY with 15 realistic historical snapshots.
    Shows three situation types improving in confidence over time:
      travel_login_anomaly   — 8 decisions, 0.68 → 0.92
      cloud_misconfiguration — 4 decisions, 0.55 → 0.88
      data_exfil_attempt     — 3 decisions, 0.60 → 0.85
    Called at end of reset_confidence_history() and on module import so
    Tab 4 charts are always populated without requiring live interaction.
    Live decisions append to this baseline (decision_number continues from 16+).
    """
    _SEED_DATA = [
        # (decision, alert_id, alert_type, situation_type, confidence)
        ( 1, "ALERT-S001", "anomalous_login",        "travel_login_anomaly",   0.68),
        ( 2, "ALERT-S002", "anomalous_login",        "travel_login_anomaly",   0.72),
        ( 3, "ALERT-S003", "anomalous_login",        "travel_login_anomaly",   0.74),
        ( 4, "ALERT-S004", "cloud_misconfiguration", "cloud_misconfiguration", 0.55),
        ( 5, "ALERT-S005", "anomalous_login",        "travel_login_anomaly",   0.78),
        ( 6, "ALERT-S006", "data_exfiltration",      "data_exfil_attempt",     0.60),
        ( 7, "ALERT-S007", "anomalous_login",        "travel_login_anomaly",   0.82),
        ( 8, "ALERT-S008", "cloud_misconfiguration", "cloud_misconfiguration", 0.66),
        ( 9, "ALERT-S009", "anomalous_login",        "travel_login_anomaly",   0.86),
        (10, "ALERT-S010", "data_exfiltration",      "data_exfil_attempt",     0.72),
        (11, "ALERT-S011", "cloud_misconfiguration", "cloud_misconfiguration", 0.77),
        (12, "ALERT-S012", "anomalous_login",        "travel_login_anomaly",   0.90),
        (13, "ALERT-S013", "data_exfiltration",      "data_exfil_attempt",     0.85),
        (14, "ALERT-S014", "cloud_misconfiguration", "cloud_misconfiguration", 0.88),
        (15, "ALERT-S015", "anomalous_login",        "travel_login_anomaly",   0.92),
    ]

    base_ts = datetime.now(timezone.utc) - timedelta(hours=15)
    for dec, alert_id, alert_type, situation_type, confidence in _SEED_DATA:
        ts = base_ts + timedelta(hours=dec)
        CONFIDENCE_HISTORY.append({
            "decision_number": dec,
            "timestamp":       ts.isoformat(),
            "alert_id":        alert_id,
            "alert_type":      alert_type,
            "situation_type":  situation_type,
            "confidence":      confidence,
        })
    print(f"[TRIAGE] Seeded {len(_SEED_DATA)} historical confidence snapshots")


# seed_confidence_history() is called explicitly from main.py startup_event()
# so charts are populated once at boot, not on every module import.


def reset_confidence_history() -> None:
    """Clear CONFIDENCE_HISTORY — registered with state_manager for demo reset."""
    CONFIDENCE_HISTORY.clear()
    seed_confidence_history()
    print("[TRIAGE] Confidence history reset to seeded baseline")


def get_confidence_trajectory() -> Dict[str, List[Dict[str, Any]]]:
    """
    Return confidence history grouped by situation_type (F4b).

    Each group is sorted by decision_number, suitable for charting a
    confidence-over-time line per situation type.

    Returns:
        {
          "travel_login_anomaly":    [{"decision": 1, "confidence": 0.92}, ...],
          "known_phishing_campaign": [{"decision": 2, "confidence": 0.94}, ...],
          ...
        }
    """
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for snap in CONFIDENCE_HISTORY:
        sit = snap["situation_type"]
        if sit not in grouped:
            grouped[sit] = []
        grouped[sit].append({
            "decision":   snap["decision_number"],
            "confidence": snap["confidence"],
        })
    return grouped


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
