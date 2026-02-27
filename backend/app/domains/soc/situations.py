"""
SOC-specific situation classification logic.

Extracted from services/situation.py — exact same rules, moved to the domain layer.
services/situation.py delegates classify_situation() and evaluate_options() here;
callers (routers, triage.py) are unmodified.

Exported symbols used by services/situation.py:
    classify_soc_situation(alert_type, context) -> (str, float, List[str])
    get_soc_options(situation_type, context)    -> List[Dict]

Supporting data:
    SOC_SITUATION_TYPES  — metadata for each situation type (label, description, color)
    SOC_OPTIONS          — raw option data per situation type (plain dicts, no Pydantic)
"""
from typing import Any, Dict, List, Tuple


# ============================================================================
# A. SOC_SITUATION_TYPES
# Metadata for each situation type.
# Keys: SituationType enum values (lowercase strings, as used in API responses).
# Source: SituationType enum + domains/soc/config.py situation_types (R2).
# ============================================================================

SOC_SITUATION_TYPES: Dict[str, Dict[str, str]] = {
    "travel_login_anomaly": {
        "label":       "Travel Login Anomaly",
        "description": (
            "Anomalous login where user travel record and VPN location align — "
            "likely a false positive"
        ),
        "color": "#3B82F6",   # blue
    },
    "known_phishing_campaign": {
        "label":       "Known Phishing Campaign",
        "description": (
            "Email matches a known phishing campaign signature in the pattern library"
        ),
        "color": "#F97316",   # orange
    },
    "malware_on_critical_asset": {
        "label":       "Malware on Critical Asset",
        "description": (
            "Malware detected on a critical or production system — "
            "immediate incident response required"
        ),
        "color": "#EF4444",   # red
    },
    "vip_after_hours": {
        "label":       "VIP After Hours",
        "description": (
            "Executive-level user activity outside normal business hours — "
            "requires careful verification before escalation"
        ),
        "color": "#EAB308",   # yellow
    },
    "data_exfil_attempt": {
        "label":       "Data Exfiltration Attempt",
        "description": (
            "Unusual data transfer to an external destination above volume threshold — "
            "forensics required"
        ),
        "color": "#DC2626",   # dark red
    },
    "unknown": {
        "label":       "Unknown",
        "description": (
            "Insufficient context for automated classification — "
            "manual Tier 2 review recommended"
        ),
        "color": "#6B7280",   # gray
    },
}


# ============================================================================
# A2. MITRE ATT&CK mapping (F1a)
# Maps situation type string → (technique_id, tactic_name).
# Covers both CURRENT situation types (v3.2) and the F2a expanded types
# (known_benign, travel_anomaly, etc.) so the classifier works correctly
# as soon as F2b adds those enum values.
# Source: v4_design_document_v4.md Section 4, Prompt F1a.
# ============================================================================

MITRE_ATTACK_MAP: Dict[str, Dict[str, str]] = {
    # Current situation types (v3.2 classifier)
    "travel_login_anomaly":      {"technique": "T1078", "tactic": "Initial Access"},
    "known_phishing_campaign":   {"technique": "T1566", "tactic": "Initial Access"},
    "malware_on_critical_asset": {"technique": "T1204", "tactic": "Execution"},
    "vip_after_hours":           {"technique": "T1078", "tactic": "Initial Access"},
    "data_exfil_attempt":        {"technique": "T1048", "tactic": "Exfiltration"},
    "unknown":                   {"technique": "",      "tactic": ""},

    # F2a expanded situation types (classifier added in F2b)
    "known_benign":       {"technique": "T1078", "tactic": "Initial Access"},
    "travel_anomaly":     {"technique": "T1078", "tactic": "Initial Access"},
    "suspicious_pattern": {"technique": "T1110", "tactic": "Credential Access"},
    "known_threat":       {"technique": "T1566", "tactic": "Initial Access"},
    "anomalous_behavior": {"technique": "T1071", "tactic": "Command and Control"},
    "compliance_risk":    {"technique": "T1098", "tactic": "Persistence"},
}


def get_mitre_attack(situation_type: str) -> tuple:
    """
    Return (technique_id, tactic_name) for the given situation type string.
    Returns ("", "") for unknown or unmapped types.

    Example:
        technique, tactic = get_mitre_attack("travel_login_anomaly")
        # → ("T1078", "Initial Access")
    """
    entry = MITRE_ATTACK_MAP.get(situation_type, {"technique": "", "tactic": ""})
    return entry["technique"], entry["tactic"]


# ============================================================================
# B/D. classify_soc_situation()
# Exact classification rules from services/situation.classify_situation().
# Returns plain strings instead of SituationType enum members so this file
# has no dependency on the service layer.
# services/situation.classify_situation() wraps the returned string with
# SituationType(value) to preserve its existing return type.
# ============================================================================

def classify_soc_situation(
    alert_type: str,
    context: Dict[str, Any],
) -> Tuple[str, float, List[str]]:
    """
    Classify the alert situation based on alert type and context.

    Returns:
        (situation_type_id, confidence, factors_detected)
        situation_type_id is a SituationType enum VALUE string
        (e.g. "travel_login_anomaly"), not the enum member itself.

    Logic is identical to services/situation.classify_situation().
    """

    factors: List[str] = []

    # ====================================================================
    # Rule 1: Travel Login Anomaly
    # ====================================================================
    if alert_type == "anomalous_login" and context.get("user_traveling", False):
        factors = [
            "active_travel_record",
            f"destination_matches ({context.get('travel_destination', 'Unknown')})",
        ]
        if context.get("vpn_matches_location"):
            factors.append("vpn_location_match")
        if context.get("mfa_completed"):
            factors.append("mfa_completed")
        if context.get("device_fingerprint_match"):
            factors.append("device_known")
        return "travel_login_anomaly", 0.94, factors

    # ====================================================================
    # Rule 2: Known Phishing Campaign
    # ====================================================================
    if alert_type == "phishing":
        factors = ["phishing_alert"]
        if context.get("known_campaign_signature"):
            factors.append("known_campaign_signature")
            factors.append("similar_emails_blocked")
            return "known_phishing_campaign", 0.96, factors
        else:
            factors.append("novel_phishing_attempt")
            return "known_phishing_campaign", 0.72, factors

    # ====================================================================
    # Rule 3: Malware on Critical Asset
    # ====================================================================
    if alert_type == "malware_detection" and context.get("asset_criticality") == "critical":
        factors = [
            "malware_detected",
            f"critical_asset ({context.get('asset_hostname', 'Unknown')})",
            "production_system",
        ]
        return "malware_on_critical_asset", 0.97, factors

    # ====================================================================
    # Rule 4: Data Exfiltration Attempt
    # ====================================================================
    if alert_type == "data_exfiltration":
        factors = [
            "unusual_data_transfer",
            "external_destination",
            "volume_threshold_exceeded",
        ]
        return "data_exfil_attempt", 0.95, factors

    # ====================================================================
    # Rule 5: VIP After Hours
    # ====================================================================
    user_title = context.get("user_title", "").lower()
    is_vip = any(
        vip_term in user_title
        for vip_term in ["ceo", "cfo", "ciso", "vp", "chief", "executive"]
    )

    if is_vip and context.get("after_hours", False):
        factors = [
            f"vip_user ({context.get('user_name', 'Unknown')})",
            "after_hours_activity",
            "unusual_timing",
        ]
        return "vip_after_hours", 0.78, factors

    # ====================================================================
    # Default: Unknown Situation
    # ====================================================================
    factors = ["insufficient_context", f"alert_type_{alert_type}"]
    return "unknown", 0.45, factors


# ============================================================================
# C. SOC_OPTIONS
# Raw option data per situation type.  Plain dicts — no Pydantic dependency.
# Keys: SituationType enum values (same as SOC_SITUATION_TYPES).
# services/situation.evaluate_options() wraps these with OptionEvaluated(**opt).
# Data is identical to the hardcoded OptionEvaluated(...) calls in situation.py.
# ============================================================================

SOC_OPTIONS: Dict[str, List[Dict[str, Any]]] = {

    # TRAVEL_LOGIN_ANOMALY — Likely false positive
    "travel_login_anomaly": [
        {
            "action":                   "false_positive_close",
            "score":                    0.92,
            "factors":                  ["travel_match", "mfa_ok", "device_known"],
            "estimated_resolution_time": "3 seconds",
            "estimated_analyst_cost":   0.0,
            "risk_if_wrong":            "Low — auto-reopen if flagged",
        },
        {
            "action":                   "escalate_tier2",
            "score":                    0.06,
            "factors":                  ["verify_travel_legitimacy"],
            "estimated_resolution_time": "45 minutes",
            "estimated_analyst_cost":   127.0,
            "risk_if_wrong":            "None — human reviews",
        },
        {
            "action":                   "enrich_and_wait",
            "score":                    0.02,
            "factors":                  ["monitor_additional_activity"],
            "estimated_resolution_time": "15 minutes",
            "estimated_analyst_cost":   43.0,
            "risk_if_wrong":            "Low — delayed but monitored",
        },
    ],

    # KNOWN_PHISHING_CAMPAIGN — Auto-remediate
    "known_phishing_campaign": [
        {
            "action":                   "auto_remediate",
            "score":                    0.94,
            "factors":                  ["known_signature", "playbook_exists", "low_risk"],
            "estimated_resolution_time": "8 seconds",
            "estimated_analyst_cost":   0.0,
            "risk_if_wrong":            "Low — quarantine reversible",
        },
        {
            "action":                   "escalate_tier2",
            "score":                    0.04,
            "factors":                  ["verify_campaign_match"],
            "estimated_resolution_time": "30 minutes",
            "estimated_analyst_cost":   95.0,
            "risk_if_wrong":            "None — human reviews",
        },
        {
            "action":                   "enrich_and_wait",
            "score":                    0.02,
            "factors":                  ["gather_more_samples"],
            "estimated_resolution_time": "20 minutes",
            "estimated_analyst_cost":   62.0,
            "risk_if_wrong":            "Medium — exposure window",
        },
    ],

    # MALWARE_ON_CRITICAL_ASSET — Escalate to incident
    "malware_on_critical_asset": [
        {
            "action":                   "escalate_incident",
            "score":                    0.97,
            "factors":                  ["critical_asset", "production_impact", "high_risk"],
            "estimated_resolution_time": "2 hours",
            "estimated_analyst_cost":   310.0,
            "risk_if_wrong":            "None — appropriate for criticality",
        },
        {
            "action":                   "auto_remediate",
            "score":                    0.02,
            "factors":                  ["isolate_system"],
            "estimated_resolution_time": "5 minutes",
            "estimated_analyst_cost":   15.0,
            "risk_if_wrong":            "High — production downtime",
        },
        {
            "action":                   "enrich_and_wait",
            "score":                    0.01,
            "factors":                  ["assess_blast_radius"],
            "estimated_resolution_time": "30 minutes",
            "estimated_analyst_cost":   95.0,
            "risk_if_wrong":            "Critical — malware spreads",
        },
    ],

    # DATA_EXFIL_ATTEMPT — Escalate to incident
    "data_exfil_attempt": [
        {
            "action":                   "escalate_incident",
            "score":                    0.96,
            "factors":                  ["data_loss_risk", "external_connection", "volume_anomaly"],
            "estimated_resolution_time": "3 hours",
            "estimated_analyst_cost":   465.0,
            "risk_if_wrong":            "None — forensics required",
        },
        {
            "action":                   "enrich_and_wait",
            "score":                    0.03,
            "factors":                  ["identify_data_type"],
            "estimated_resolution_time": "45 minutes",
            "estimated_analyst_cost":   127.0,
            "risk_if_wrong":            "Critical — data already exfiltrated",
        },
        {
            "action":                   "auto_remediate",
            "score":                    0.01,
            "factors":                  ["block_connection"],
            "estimated_resolution_time": "10 seconds",
            "estimated_analyst_cost":   0.0,
            "risk_if_wrong":            "High — may block legitimate traffic",
        },
    ],

    # VIP_AFTER_HOURS — Enrich and wait
    "vip_after_hours": [
        {
            "action":                   "enrich_and_wait",
            "score":                    0.76,
            "factors":                  ["vip_caution", "verify_legitimacy", "context_needed"],
            "estimated_resolution_time": "20 minutes",
            "estimated_analyst_cost":   62.0,
            "risk_if_wrong":            "Low — monitored closely",
        },
        {
            "action":                   "escalate_tier2",
            "score":                    0.18,
            "factors":                  ["manual_review"],
            "estimated_resolution_time": "40 minutes",
            "estimated_analyst_cost":   118.0,
            "risk_if_wrong":            "None — human judgment",
        },
        {
            "action":                   "false_positive_close",
            "score":                    0.06,
            "factors":                  ["workaholic_pattern"],
            "estimated_resolution_time": "5 seconds",
            "estimated_analyst_cost":   0.0,
            "risk_if_wrong":            "Medium — may miss real threat",
        },
    ],

    # UNKNOWN — Default conservative approach
    "unknown": [
        {
            "action":                   "escalate_tier2",
            "score":                    0.60,
            "factors":                  ["insufficient_confidence", "manual_review_needed"],
            "estimated_resolution_time": "50 minutes",
            "estimated_analyst_cost":   143.0,
            "risk_if_wrong":            "None — human reviews",
        },
        {
            "action":                   "enrich_and_wait",
            "score":                    0.30,
            "factors":                  ["gather_more_context"],
            "estimated_resolution_time": "25 minutes",
            "estimated_analyst_cost":   71.0,
            "risk_if_wrong":            "Medium — delayed response",
        },
        {
            "action":                   "escalate_incident",
            "score":                    0.10,
            "factors":                  ["err_on_caution"],
            "estimated_resolution_time": "2.5 hours",
            "estimated_analyst_cost":   388.0,
            "risk_if_wrong":            "Low — over-escalation cost",
        },
    ],
}


# ============================================================================
# E. get_soc_options()
# Returns the raw option list for a given situation type string.
# Falls back to "unknown" options for unrecognised situation types.
# services/situation.evaluate_options() wraps results with OptionEvaluated(**opt).
# ============================================================================

def get_soc_options(
    situation_type: str,
    context: Dict[str, Any],  # noqa: ARG001 — reserved for future context-aware options
) -> List[Dict[str, Any]]:
    """
    Return option dicts for the given situation type.
    Logic is identical to services/situation.evaluate_options().
    situation_type must be a SituationType enum value string.
    """
    return SOC_OPTIONS.get(situation_type, SOC_OPTIONS["unknown"])
