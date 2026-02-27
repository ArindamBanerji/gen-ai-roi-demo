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

    # -------------------------------------------------------------------------
    # F2b: alert-type-keyed templates (fallback when alert_id not found)
    # Keys match the alert_type strings used in seed_neo4j.py.
    # Lookup order in compute_soc_factors(): alert_id → alert_type → "_default"
    # -------------------------------------------------------------------------

    "brute_force": {
        "recommended_action": "auto_remediate",
        "confidence": 0.93,
        "factors": [
            {
                "name":        "failure_rate",
                "value":       0.95,
                "weight":      0.85,
                "explanation": "Auth failure rate 47/min exceeds brute-force threshold (>10 failures/min)",
            },
            {
                "name":        "asset_criticality",
                "value":       0.65,
                "weight":      0.55,
                "explanation": "Target account holds elevated permissions on production system",
            },
            {
                "name":        "time_anomaly",
                "value":       0.88,
                "weight":      0.70,
                "explanation": "Attack began 02:34 — outside business hours, low analyst coverage",
            },
            {
                "name":        "source_reputation",
                "value":       0.90,
                "weight":      0.80,
                "explanation": "Source IP blacklisted in 3 threat feeds — known attack infrastructure",
            },
            {
                "name":        "pattern_history",
                "value":       0.82,
                "weight":      0.72,
                "explanation": "Similar brute-force pattern seen in 34 prior incidents — high confidence block",
            },
        ],
    },

    "privilege_escalation": {
        "recommended_action": "escalate_incident",
        "confidence": 0.91,
        "factors": [
            {
                "name":        "escalation_severity",
                "value":       0.90,
                "weight":      0.85,
                "explanation": "Root-level privilege obtained on production host — full system access",
            },
            {
                "name":        "asset_criticality",
                "value":       0.90,
                "weight":      0.85,
                "explanation": "Critical production server — potential for wide business impact",
            },
            {
                "name":        "time_anomaly",
                "value":       0.78,
                "weight":      0.60,
                "explanation": "Escalation occurred outside normal change windows — unplanned activity",
            },
            {
                "name":        "device_trust",
                "value":       0.60,
                "weight":      0.50,
                "explanation": "Originating process not in approved whitelist — potentially malicious",
            },
            {
                "name":        "pattern_history",
                "value":       0.70,
                "weight":      0.65,
                "explanation": "Privilege escalation path matches known attacker TTPs in MITRE T1068",
            },
        ],
    },

    "credential_stuffing": {
        "recommended_action": "auto_remediate",
        "confidence": 0.90,
        "factors": [
            {
                "name":        "account_volume",
                "value":       0.88,
                "weight":      0.80,
                "explanation": "142 distinct accounts targeted — automated stuffing pattern confirmed",
            },
            {
                "name":        "credential_exposure",
                "value":       0.85,
                "weight":      0.78,
                "explanation": "Credentials match recent breach dataset — verified leaked pairs",
            },
            {
                "name":        "time_anomaly",
                "value":       0.75,
                "weight":      0.60,
                "explanation": "High-velocity login attempts span 3-hour window — automated bot pattern",
            },
            {
                "name":        "source_reputation",
                "value":       0.88,
                "weight":      0.80,
                "explanation": "Source IPs rotate across 18 countries — residential botnet pattern",
            },
            {
                "name":        "pattern_history",
                "value":       0.75,
                "weight":      0.68,
                "explanation": "PAT-CREDSTUFF-001: 34 prior incidents, 78% success rate blocking at this stage",
            },
        ],
    },

    "c2_beacon": {
        "recommended_action": "escalate_incident",
        "confidence": 0.95,
        "factors": [
            {
                "name":        "c2_confidence",
                "value":       0.96,
                "weight":      0.92,
                "explanation": "Destination IP confirmed C2 infrastructure across 4 threat intelligence feeds",
            },
            {
                "name":        "asset_criticality",
                "value":       0.82,
                "weight":      0.75,
                "explanation": "Beaconing host has read access to sensitive data stores",
            },
            {
                "name":        "time_anomaly",
                "value":       0.65,
                "weight":      0.55,
                "explanation": "Regular 60-second beacon interval — automated implant, not user-initiated",
            },
            {
                "name":        "traffic_volume",
                "value":       0.80,
                "weight":      0.72,
                "explanation": "Low-volume but persistent traffic — classic C2 check-in heartbeat pattern",
            },
            {
                "name":        "pattern_history",
                "value":       0.90,
                "weight":      0.82,
                "explanation": "C2 domain matches threat actor infrastructure from Q3 2025 campaign",
            },
        ],
    },

    "threat_intel_match": {
        "recommended_action": "escalate_incident",
        "confidence": 0.93,
        "factors": [
            {
                "name":        "ioc_confidence",
                "value":       0.94,
                "weight":      0.90,
                "explanation": "IOC confirmed across 3 threat intelligence feeds with high fidelity",
            },
            {
                "name":        "asset_criticality",
                "value":       0.70,
                "weight":      0.60,
                "explanation": "Affected host is a production workstation with domain access",
            },
            {
                "name":        "time_anomaly",
                "value":       0.55,
                "weight":      0.45,
                "explanation": "Activity during business hours — potential user-initiated or phishing lure",
            },
            {
                "name":        "indicator_age",
                "value":       0.85,
                "weight":      0.75,
                "explanation": "IOC first seen 14 days ago — active threat campaign, not stale data",
            },
            {
                "name":        "pattern_history",
                "value":       0.88,
                "weight":      0.80,
                "explanation": "IOC associated with known threat actor group targeting financial sector",
            },
        ],
    },

    "data_exfil": {
        "recommended_action": "escalate_incident",
        "confidence": 0.95,
        "factors": [
            {
                "name":        "transfer_volume",
                "value":       0.93,
                "weight":      0.88,
                "explanation": "47 GB outbound to external cloud storage — 23x above host baseline",
            },
            {
                "name":        "asset_criticality",
                "value":       0.85,
                "weight":      0.78,
                "explanation": "Source server contains customer records and intellectual property",
            },
            {
                "name":        "time_anomaly",
                "value":       0.88,
                "weight":      0.80,
                "explanation": "Transfer initiated at 01:15 — off-hours, minimal monitoring coverage",
            },
            {
                "name":        "destination_risk",
                "value":       0.90,
                "weight":      0.85,
                "explanation": "Destination IP not in approved vendor list — unsanctioned cloud provider",
            },
            {
                "name":        "pattern_history",
                "value":       0.60,
                "weight":      0.55,
                "explanation": "No prior external transfers from this host — novel behavior, low FP rate",
            },
        ],
    },

    "anomalous_behavior": {
        "recommended_action": "enrich_and_wait",
        "confidence": 0.87,
        "factors": [
            {
                "name":        "traffic_anomaly",
                "value":       0.75,
                "weight":      0.70,
                "explanation": "Network traffic 8x above baseline — significant deviation from normal",
            },
            {
                "name":        "asset_criticality",
                "value":       0.65,
                "weight":      0.58,
                "explanation": "Mid-tier server — moderate blast radius if lateral movement succeeds",
            },
            {
                "name":        "time_anomaly",
                "value":       0.80,
                "weight":      0.70,
                "explanation": "Anomaly began after business hours — low-noise window for attacker",
            },
            {
                "name":        "connection_pattern",
                "value":       0.72,
                "weight":      0.65,
                "explanation": "Internal hosts contacted in sequential sweep — lateral movement indicators",
            },
            {
                "name":        "pattern_history",
                "value":       0.50,
                "weight":      0.50,
                "explanation": "Novel behavior pattern — limited historical precedent, enrichment needed",
            },
        ],
    },

    "insider_threat": {
        "recommended_action": "escalate_incident",
        "confidence": 0.89,
        "factors": [
            {
                "name":        "access_anomaly",
                "value":       0.82,
                "weight":      0.78,
                "explanation": "Bulk data access 12x above user baseline in 2-hour window",
            },
            {
                "name":        "asset_criticality",
                "value":       0.88,
                "weight":      0.82,
                "explanation": "Customer PII database accessed — regulatory and reputational exposure",
            },
            {
                "name":        "time_anomaly",
                "value":       0.85,
                "weight":      0.75,
                "explanation": "Access at 11 PM, 2 weeks before voluntary departure — high-risk timing",
            },
            {
                "name":        "device_trust",
                "value":       0.90,
                "weight":      0.80,
                "explanation": "Registered corporate device — access is deliberate, not accidental",
            },
            {
                "name":        "pattern_history",
                "value":       0.65,
                "weight":      0.60,
                "explanation": "Access pattern matches 7 prior insider incidents in case library",
            },
        ],
    },

    "cloud_config": {
        "recommended_action": "auto_remediate",
        "confidence": 0.88,
        "factors": [
            {
                "name":        "exposure_severity",
                "value":       0.90,
                "weight":      0.85,
                "explanation": "S3 bucket with public-read ACL containing sensitive configuration files",
            },
            {
                "name":        "asset_criticality",
                "value":       0.75,
                "weight":      0.68,
                "explanation": "Cloud resource attached to production environment — active exposure",
            },
            {
                "name":        "time_anomaly",
                "value":       0.30,
                "weight":      0.30,
                "explanation": "Misconfiguration present since last deployment 3 days ago — drift detected",
            },
            {
                "name":        "data_sensitivity",
                "value":       0.80,
                "weight":      0.75,
                "explanation": "Exposed content includes API keys and database connection strings",
            },
            {
                "name":        "pattern_history",
                "value":       0.70,
                "weight":      0.62,
                "explanation": "Third cloud misconfiguration this quarter — systemic IaC policy gap",
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
    alert_type: str = "",
) -> Dict[str, Any]:
    """
    Build the full 6-factor decision breakdown for alert_id.

    Lookup order:
      1. alert_id  — exact match (ALERT-7823, ALERT-7824)
      2. alert_type — type-keyed template (brute_force, c2_beacon, …)
      3. "_default" — conservative fallback

    Args:
        alert_id:   Alert identifier (e.g. "ALERT-7823").
        ti_factor:  Pre-built threat_intel_enrichment factor dict.
                    Built by _build_threat_intel_factor() in services/triage.py
                    and passed here (Option A) so this module stays free of I/O.
                    If None, inserts a zeroed-out placeholder factor.
        alert_type: Alert type string (e.g. "brute_force") for type-level fallback.

    Returns:
        Dict matching the return format of services/triage.get_decision_factors().

    Final factor order:
      [0] primary factor (varies by alert type)
      [1] secondary factor
      [2] threat_intel_enrichment  ← passed in from Neo4j (or placeholder)
      [3] time_anomaly
      [4] device/source/pattern factor
      [5] pattern_history
    """
    template = (
        SOC_FACTOR_TEMPLATES.get(alert_id)
        or SOC_FACTOR_TEMPLATES.get(alert_type)
        or SOC_FACTOR_TEMPLATES["_default"]
    )

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
