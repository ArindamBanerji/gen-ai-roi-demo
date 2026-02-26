"""
SOC-specific policy definitions and applicability logic.

Extracted from services/policy.py — exact same policies and matching rules, moved
to the domain layer. services/policy.py delegates the "which policies apply?" question
here; the conflict resolution mechanism (priority comparison, audit ID generation,
narrative building) remains in services/policy.py and will move to
core/policy_engine.py in a later prompt.

Exported symbols used by services/policy.py:
    get_applicable_soc_policies(alert_id, context)  -> List[Dict[str, Any]]

Supporting data:
    SOC_POLICIES  — the 4 SOC policy definitions as plain dicts (no Pydantic)

No Pydantic dependency — services/policy.py wraps returned dicts with
PolicyDefinition(**p) to preserve its existing return types.
"""
from typing import Any, Dict, List


# ============================================================================
# A. SOC_POLICIES
# The 4 SOC policy definitions as plain dicts.
# Keys match PolicyDefinition fields exactly (id, name, description, action,
# priority, scope, conditions).
# Source: POLICY_REGISTRY in services/policy.py.
# Same IDs, priorities, action_override values, and scope rules — not renamed.
# ============================================================================

SOC_POLICIES: List[Dict[str, Any]] = [
    {
        "id":          "POL-AUTO-CLOSE-TRAVEL",
        "name":        "Auto-Close Travel Anomalies",
        "description": (
            "Automatically close login anomaly alerts when user is traveling "
            "and VPN matches travel destination"
        ),
        "action":      "false_positive_close",
        "priority":    3,           # Lower priority
        "scope":       "all_users",
        "conditions": {
            "alert_type":          "anomalous_login",
            "user_traveling":      True,
            "vpn_matches_location": True,
        },
    },
    {
        "id":          "POL-ESCALATE-HIGH-RISK",
        "name":        "Escalate High-Risk Users",
        "description": (
            "Escalate all alerts for users with risk score above 0.80 "
            "to Tier 2 analysts"
        ),
        "action":      "escalate_tier2",
        "priority":    1,           # Higher priority (security-first)
        "scope":       "high_risk_users",
        "conditions": {
            "user_risk_score_above": 0.80,
        },
    },
    {
        "id":          "POL-REMEDIATE-KNOWN-PHISH",
        "name":        "Auto-Remediate Known Phishing",
        "description": (
            "Automatically remediate phishing alerts that match known "
            "campaign signatures"
        ),
        "action":      "auto_remediate",
        "priority":    2,
        "scope":       "all_users",
        "conditions": {
            "alert_type":               "phishing",
            "known_campaign_signature": True,
        },
    },
    {
        "id":          "POL-ISOLATE-CRITICAL-ASSETS",
        "name":        "Isolate Critical Assets",
        "description": (
            "Immediately isolate any malware detection on critical infrastructure"
        ),
        "action":      "auto_remediate",
        "priority":    1,           # Highest priority
        "scope":       "critical_assets",
        "conditions": {
            "alert_type":       "malware_detection",
            "asset_criticality": "critical",
        },
    },
]


# ============================================================================
# B. _policy_matches()
# Checks whether a single policy's conditions are satisfied by the context.
# Logic is identical to services/policy._policy_matches() but operates on
# plain dicts instead of PolicyDefinition objects.
# ============================================================================

def _policy_matches(policy: Dict[str, Any], alert_id: str, context: Dict[str, Any]) -> bool:
    """Return True if all of the policy's conditions are met by the context."""
    conditions = policy["conditions"]

    # Check alert type
    if "alert_type" in conditions:
        if context.get("alert_type") != conditions["alert_type"]:
            return False

    # Check user traveling
    if "user_traveling" in conditions:
        if context.get("user_traveling") != conditions["user_traveling"]:
            return False

    # Check VPN matches location
    if "vpn_matches_location" in conditions:
        if context.get("vpn_matches_location") != conditions["vpn_matches_location"]:
            return False

    # Check MFA completed
    if "mfa_completed" in conditions:
        if context.get("mfa_completed") != conditions["mfa_completed"]:
            return False

    # Check user risk score
    if "user_risk_score_above" in conditions:
        threshold = conditions["user_risk_score_above"]
        if context.get("user_risk_score", 0) <= threshold:
            return False

    # Check known campaign signature
    if "known_campaign_signature" in conditions:
        if context.get("known_campaign_signature") != conditions["known_campaign_signature"]:
            return False

    # Check asset criticality
    if "asset_criticality" in conditions:
        if context.get("asset_criticality") != conditions["asset_criticality"]:
            return False

    return True


# ============================================================================
# C. get_applicable_soc_policies()
# Returns the subset of SOC_POLICIES whose conditions match the alert context.
# Logic is identical to services/policy.get_applicable_policies() +
# services/policy._policy_matches(), but returns plain dicts.
# services/policy.detect_policy_conflicts() wraps results with PolicyDefinition(**p).
# ============================================================================

def get_applicable_soc_policies(
    alert_id: str,
    context: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Return plain policy dicts whose conditions are satisfied by the context.

    Args:
        alert_id: Alert identifier (e.g. "ALERT-7823"). Reserved for future
                  per-alert overrides; currently unused in matching logic.
        context:  Security context dict (alert_type, user_risk_score,
                  user_traveling, vpn_matches_location, etc.)

    Returns:
        List of plain policy dicts from SOC_POLICIES that match.
        services/policy.py wraps each with PolicyDefinition(**p).
    """
    return [p for p in SOC_POLICIES if _policy_matches(p, alert_id, context)]
