"""
SOC-specific factor definitions and computation.

Extracted from services/triage.py — exact same data and logic, moved to the domain
layer. services/triage.py delegates get_decision_factors() here; callers (routers)
are unmodified.

Neo4j dependency: Option A chosen.
  _build_threat_intel_factor() stays in services/triage.py (it owns the Neo4j query).
  The built threat_intel factor dict is passed into compute_soc_factors() as a
  parameter so this module remains free of I/O dependencies.

Exported symbols used by services/triage.py:
    compute_soc_factors(alert_id, ti_factor)  -> Dict[str, Any]
    _contribution(value, weight)              -> str   (also imported by triage.py)

Supporting data:
    SOC_FACTOR_TEMPLATES  — static factor data per alert_id + "_default" fallback
"""
from typing import Any, Dict, List, Optional


# ============================================================================
# A. SOC_FACTOR_TEMPLATES
# Static factor templates per known alert (5 non-threat-intel factors).
# threat_intel_enrichment is inserted dynamically at index 2 by compute_soc_factors().
#
# Keys:
#   "ALERT-7823"  — travel login anomaly  (John Smith)
#   "ALERT-7824"  — phishing campaign     (Mary Chen)
#   "_default"    — fallback for unknown alert IDs
#
# Source: _ALERT_FACTORS + _DEFAULT_FACTORS in services/triage.py.
# Data is copied exactly — same IDs, same values, same explanations.
# ============================================================================

SOC_FACTOR_TEMPLATES: Dict[str, Dict[str, Any]] = {

    # Travel login anomaly — likely false positive
    "ALERT-7823": {
        "recommended_action": "false_positive_close",
        "confidence": 0.94,
        "factors": [
            {
                "name":        "travel_match",
                "value":       0.95,
                "weight":      0.82,
                "explanation": "Employee calendar shows Singapore travel — VPN origin matches destination",
            },
            {
                "name":        "asset_criticality",
                "value":       0.30,
                "weight":      0.45,
                "explanation": "Development server (non-critical) — lower blast radius if wrong",
            },
            {
                "name":        "time_anomaly",
                "value":       0.70,
                "weight":      0.55,
                "explanation": "Login at 3 AM home timezone — moderate anomaly given travel context",
            },
            {
                "name":        "device_trust",
                "value":       0.90,
                "weight":      0.78,
                "explanation": "Known corporate laptop, MDM enrolled, device fingerprint matched",
            },
            {
                "name":        "pattern_history",
                "value":       0.85,
                "weight":      0.70,
                "explanation": "PAT-TRAVEL-001: 127 similar alerts resolved as false positives (92% FP rate)",
            },
        ],
    },

    # Known phishing campaign — auto-remediate
    "ALERT-7824": {
        "recommended_action": "auto_remediate",
        "confidence": 0.94,
        "factors": [
            {
                "name":        "campaign_signature_match",
                "value":       0.94,
                "weight":      0.90,
                "explanation": "Operation DarkHook campaign signature matched — known phishing kit",
            },
            {
                "name":        "sender_domain_risk",
                "value":       0.92,
                "weight":      0.85,
                "explanation": "phishmail.com domain flagged in threat feed, used in 47 prior campaigns",
            },
            {
                "name":        "time_anomaly",
                "value":       0.40,
                "weight":      0.40,
                "explanation": "Received during business hours — low time-based anomaly",
            },
            {
                "name":        "asset_criticality",
                "value":       0.40,
                "weight":      0.45,
                "explanation": "Laptop endpoint, moderate criticality — quarantine is low-blast-radius action",
            },
            {
                "name":        "pattern_history",
                "value":       0.82,
                "weight":      0.70,
                "explanation": "PAT-PHISH-KNOWN: 214 similar alerts auto-remediated (82% FP rate)",
            },
        ],
    },

    # Default — conservative fallback for unknown alert IDs
    "_default": {
        "recommended_action": "escalate_tier2",
        "confidence":         0.60,
        "factors": [
            {
                "name":        "alert_severity",
                "value":       0.50,
                "weight":      0.60,
                "explanation": "Alert severity classified as medium — manual review warranted",
            },
            {
                "name":        "asset_criticality",
                "value":       0.50,
                "weight":      0.45,
                "explanation": "Asset criticality undetermined — defaulting to conservative action",
            },
            {
                "name":        "time_anomaly",
                "value":       0.50,
                "weight":      0.50,
                "explanation": "Activity detected outside normal business hours",
            },
            {
                "name":        "device_trust",
                "value":       0.50,
                "weight":      0.55,
                "explanation": "Device trust level undetermined",
            },
            {
                "name":        "pattern_history",
                "value":       0.30,
                "weight":      0.60,
                "explanation": "Limited pattern history for this alert type",
            },
        ],
    },
}


# ============================================================================
# B. _contribution()
# Maps value × weight to a contribution label.
# Also imported by services/triage._build_threat_intel_factor().
# Logic is identical to the private helper in services/triage.py.
# ============================================================================

def _contribution(value: float, weight: float) -> str:
    """Map value × weight to a contribution label."""
    score = value * weight
    if score > 0.5:
        return "high"
    if score > 0.25:
        return "medium"
    if score > 0:
        return "low"
    return "none"


# ============================================================================
# C. compute_soc_factors()
# Builds the full 6-factor decision breakdown for an alert_id.
# Exact logic from services/triage.get_decision_factors(), minus the Neo4j call.
# ============================================================================

def compute_soc_factors(
    alert_id: str,
    ti_factor: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build the full 6-factor decision breakdown for alert_id.

    Args:
        alert_id:  Alert identifier (e.g. "ALERT-7823").
        ti_factor: Pre-built threat_intel_enrichment factor dict.
                   Built by _build_threat_intel_factor() in services/triage.py
                   and passed here (Option A) so this module stays free of I/O.
                   If None, inserts a zeroed-out placeholder factor.

    Returns:
        Dict matching the return format of services/triage.get_decision_factors().

    Final factor order:
      [0] travel_match / campaign_signature_match / alert_severity
      [1] asset_criticality / sender_domain_risk
      [2] threat_intel_enrichment  ← passed in from Neo4j (or placeholder)
      [3] time_anomaly
      [4] device_trust / asset_criticality
      [5] pattern_history
    """
    template = SOC_FACTOR_TEMPLATES.get(alert_id, SOC_FACTOR_TEMPLATES["_default"])

    # Build static factors with computed contribution labels
    static_factors: List[Dict[str, Any]] = []
    for f in template["factors"]:
        static_factors.append({
            "name":         f["name"],
            "value":        f["value"],
            "weight":       f["weight"],
            "contribution": _contribution(f["value"], f["weight"]),
            "explanation":  f["explanation"],
        })

    # Threat intel factor — placeholder if not provided
    if ti_factor is None:
        ti_factor = {
            "name":         "threat_intel_enrichment",
            "value":        0.0,
            "weight":       0.75,
            "contribution": "none",
            "explanation":  "No threat intel data — click Refresh Threat Intel in Tab 3",
        }

    # Insert at position 2 (between asset_criticality and time_anomaly)
    factors = static_factors[:2] + [ti_factor] + static_factors[2:]

    return {
        "alert_id":           alert_id,
        "factors":            factors,
        "recommended_action": template["recommended_action"],
        "confidence":         template["confidence"],
        "decision_method":    "softmax scoring matrix (6 factors × 4 actions)",
        "weights_note":       (
            "Weights calibrate automatically through verified outcomes "
            "(Loop 2 + Loop 3)"
        ),
    }
