"""
Decision Factor Breakdown Service -- Explainability for agent decisions

Provides a weighted 6-factor matrix showing how the agent scored each
decision. The sixth factor (threat_intel_enrichment) is queried live
from AGE, using the ASSOCIATED_WITH relationship written by
services/threat_intel.py during Threat Intel refresh.

Factor schema:
  name          str   -- factor identifier
  value         float -- 0.0-1.0 signal strength
  weight        float -- importance in decision matrix
  contribution  str   -- "high" / "medium" / "low" / "none"
  explanation   str   -- plain English reason

Endpoint:
  GET /api/triage/decision-factors/{alert_id}
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, cast

from app.db.graph_client import graph_client
from app.domains.soc.factor_vector import validated_factor_vector
from copilot_sdk.backend.graph_access import GRAPH_CONNECTION_ERRORS

logger = logging.getLogger(__name__)


class FactorReadUnavailable(Exception):
    """Graph or factor service read failed; factors cannot be computed."""


def validated_decision_factors(result: Any) -> tuple[list[str], list[float]]:
    """Validate the provider payload before explanation or action side effects."""
    if not isinstance(result, dict) or not isinstance(result.get("factors"), list):
        raise FactorReadUnavailable("Decision factor response is unavailable")
    factors = result["factors"]
    if any(not isinstance(item, dict) or "value" not in item
           or not isinstance(item.get("name"), str) for item in factors):
        raise FactorReadUnavailable("Decision factor response is malformed")
    try:
        vector = validated_factor_vector([item["value"] for item in factors])
    except ValueError as exc:
        raise FactorReadUnavailable("Decision factor vector is invalid") from exc
    return [item["name"] for item in factors], vector


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
        confidence:     Agent recommendation confidence score (0.0-1.0)
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
      travel_login_anomaly   -- 8 decisions, 0.68 -> 0.92
      cloud_misconfiguration -- 4 decisions, 0.55 -> 0.88
      data_exfil_attempt     -- 3 decisions, 0.60 -> 0.85
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
    """Clear CONFIDENCE_HISTORY -- registered with state_manager for demo reset."""
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

async def _build_threat_intel_factor(alert_id: str) -> Optional[Dict[str, Any]]:
    """
    Query AGE for ThreatIntel nodes linked to alert_id via ASSOCIATED_WITH.
    Returns a factor dict for threat_intel_enrichment.

    Relationship direction (confirmed from threat_intel.py):
        (ThreatIntel)-[:ASSOCIATED_WITH]->(Alert)
    """
    from app.domains.soc.factors import _contribution
    query = """
    MATCH (t:ThreatIntel)-[:ASSOCIATED_WITH]->(a:Alert {alert_id: $alert_id})
    RETURN t.value AS ioc_value, t.severity AS severity, t.source AS source
    """
    try:
        results = await graph_client.run_query(query, {"alert_id": alert_id})
    except GRAPH_CONNECTION_ERRORS as exc:
        logger.warning("Threat-intel factor read unavailable for %s: %s", alert_id, exc)
        raise FactorReadUnavailable("Threat-intel factor read unavailable") from exc

    if not isinstance(results, list) or any(not isinstance(row, dict) for row in results):
        raise FactorReadUnavailable("Threat-intel factor read returned no valid result")

    if not results:
        return {
            "name":         "threat_intel_enrichment",
            "value":        0.0,
            "weight":       0.75,
            "contribution": "none",
            "explanation":  "No threat intel data -- click Refresh Threat Intel in Tab 3",
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

    best_row = cast(Dict[str, Any], best_row)
    sev_str    = (best_row.get("severity") or "none").lower()
    source     = best_row.get("source", "unknown")
    ioc_val    = best_row.get("ioc_value", "unknown")
    count      = len(results)
    source_lbl = "Pulsedive (live)" if "pulsedive" in str(source).lower() else "local fallback"
    explanation = (
        f"{source_lbl}: {ioc_val} -- risk={sev_str} "
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
    Query AGE for the alert_type property of the given alert_id.
    Returns "" on miss (compute_soc_factors falls back to _default).
    Raises when the AGE lookup fails.
    """
    query = "MATCH (a:Alert {alert_id: $alert_id}) RETURN a.alert_type AS alert_type LIMIT 1"
    try:
        results = await graph_client.run_query(query, {"alert_id": alert_id})
        if not isinstance(results, list) or any(not isinstance(row, dict) for row in results):
            raise FactorReadUnavailable("Alert type read returned no valid result")
        if results:
            return results[0].get("alert_type") or ""
    except GRAPH_CONNECTION_ERRORS as exc:
        logger.warning("Alert type read unavailable for %s: %s", alert_id, exc)
        raise FactorReadUnavailable("Alert type read unavailable") from exc
    return ""


async def get_decision_factors(alert_id: str) -> Dict[str, Any]:
    """
    Return the 6-factor decision breakdown for alert_id.

    Builds 5 static factors from SOC_FACTOR_TEMPLATES (keyed first by
    alert_id, then by alert_type, then "_default"), queries AGE for the
    live threat_intel_enrichment factor, inserts it at index 2, and returns
    the full factor matrix.

    Final factor order:
      [0] primary factor (varies by alert type)
      [1] secondary factor
      [2] threat_intel_enrichment  <- live AGE query
      [3] time_anomaly
      [4] device/source/pattern factor
      [5] pattern_history
    """
    from app.domains.soc.factors import compute_soc_factors
    # Both reads precede factor construction. Only connectivity failures are
    # classified as unavailable; programming errors must remain visible.
    try:
        alert_type, ti_factor = await asyncio.gather(
            _get_alert_type(alert_id),
            _build_threat_intel_factor(alert_id),
        )
    except GRAPH_CONNECTION_ERRORS as exc:
        logger.warning("Decision factor read unavailable for %s: %s", alert_id, exc)
        raise FactorReadUnavailable("Decision factor read unavailable") from exc
    if (not isinstance(alert_type, str) or not isinstance(ti_factor, dict)
            or not {"name", "value", "weight", "contribution", "explanation"}.issubset(ti_factor)):
        logger.warning("Decision factor inputs unavailable for %s", alert_id)
        raise FactorReadUnavailable("Decision factor inputs unavailable")
    result = compute_soc_factors(alert_id, ti_factor, alert_type)
    validated_decision_factors(result)
    print(
        f"[TRIAGE] get_decision_factors({alert_id}): "
        f"alert_type={alert_type!r}, "
        f"{len(result['factors'])} factors, "
        f"ti_contribution={ti_factor['contribution']}"
    )
    return result
