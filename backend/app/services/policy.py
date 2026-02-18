"""
Policy Conflict Resolution - v2.5
Detects when multiple policies apply to an alert and resolves conflicts using
priority and security-first principles.

Answers the CISO question: "What happens when two policies conflict?"
"""
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel
import random


# ============================================================================
# Pydantic Models
# ============================================================================

class PolicyDefinition(BaseModel):
    """Security policy definition"""
    id: str
    name: str
    description: str
    action: str
    priority: int  # 1 = highest priority
    scope: str
    conditions: Dict[str, Any]


class PolicyResolution(BaseModel):
    """Resolution when policies conflict"""
    winning_policy: str
    losing_policy: str
    reason: str
    action_adjusted: str
    original_action: str
    audit_id: str
    narrative: str


class PolicyConflict(BaseModel):
    """Policy conflict detection result"""
    alert_id: str
    has_conflict: bool
    policies_applied: List[PolicyDefinition]
    conflicting_policies: List[PolicyDefinition]
    resolution: Optional[PolicyResolution] = None


# ============================================================================
# In-Memory Policy Registry (Demo Data)
# ============================================================================

POLICY_REGISTRY: Dict[str, PolicyDefinition] = {
    "POL-AUTO-CLOSE-TRAVEL": PolicyDefinition(
        id="POL-AUTO-CLOSE-TRAVEL",
        name="Auto-Close Travel Anomalies",
        description="Automatically close login anomaly alerts when user is traveling and VPN matches travel destination",
        action="false_positive_close",
        priority=3,  # Lower priority
        scope="all_users",
        conditions={
            "alert_type": "anomalous_login",
            "user_traveling": True,
            "vpn_matches_location": True
        }
    ),
    "POL-ESCALATE-HIGH-RISK": PolicyDefinition(
        id="POL-ESCALATE-HIGH-RISK",
        name="Escalate High-Risk Users",
        description="Escalate all alerts for users with risk score above 0.80 to Tier 2 analysts",
        action="escalate_tier2",
        priority=1,  # Higher priority (security-first)
        scope="high_risk_users",
        conditions={
            "user_risk_score_above": 0.80
        }
    ),
    "POL-REMEDIATE-KNOWN-PHISH": PolicyDefinition(
        id="POL-REMEDIATE-KNOWN-PHISH",
        name="Auto-Remediate Known Phishing",
        description="Automatically remediate phishing alerts that match known campaign signatures",
        action="auto_remediate",
        priority=2,
        scope="all_users",
        conditions={
            "alert_type": "phishing",
            "known_campaign_signature": True
        }
    ),
    "POL-ISOLATE-CRITICAL-ASSETS": PolicyDefinition(
        id="POL-ISOLATE-CRITICAL-ASSETS",
        name="Isolate Critical Assets",
        description="Immediately isolate any malware detection on critical infrastructure",
        action="auto_remediate",
        priority=1,  # Highest priority
        scope="critical_assets",
        conditions={
            "alert_type": "malware_detection",
            "asset_criticality": "critical"
        }
    )
}


# ============================================================================
# Conflict Resolution Tracking (Demo State)
# ============================================================================

CONFLICTS_RESOLVED: Dict[str, PolicyResolution] = {}


# ============================================================================
# Core Functions
# ============================================================================

def get_applicable_policies(alert_id: str, context: Dict[str, Any]) -> List[PolicyDefinition]:
    """
    Determine which policies apply to this alert based on context.

    Args:
        alert_id: Alert identifier
        context: Security context dictionary

    Returns:
        List of applicable PolicyDefinition objects
    """
    applicable = []

    for policy_id, policy in POLICY_REGISTRY.items():
        if _policy_matches(policy, alert_id, context):
            applicable.append(policy)

    return applicable


def _policy_matches(policy: PolicyDefinition, alert_id: str, context: Dict[str, Any]) -> bool:
    """
    Check if a policy's conditions match the alert context.

    Args:
        policy: Policy to check
        alert_id: Alert identifier
        context: Security context

    Returns:
        True if policy conditions are met
    """
    conditions = policy.conditions

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


def detect_policy_conflicts(alert_id: str, context: Dict[str, Any]) -> PolicyConflict:
    """
    Detect if multiple policies apply to an alert and if they conflict.

    Args:
        alert_id: Alert identifier (e.g., "ALERT-7823")
        context: Security context with user, asset, travel info

    Returns:
        PolicyConflict object with conflict detection results
    """
    # Get all applicable policies
    applicable = get_applicable_policies(alert_id, context)

    # No conflict if 0 or 1 policy applies
    if len(applicable) <= 1:
        return PolicyConflict(
            alert_id=alert_id,
            has_conflict=False,
            policies_applied=applicable,
            conflicting_policies=[],
            resolution=None
        )

    # Check if policies have different actions (conflict)
    actions = set(policy.action for policy in applicable)

    if len(actions) > 1:
        # CONFLICT: Multiple policies with different actions
        # Resolve immediately
        resolution = resolve_conflict_internal(applicable)

        return PolicyConflict(
            alert_id=alert_id,
            has_conflict=True,
            policies_applied=applicable,
            conflicting_policies=applicable,  # All applicable policies are in conflict
            resolution=resolution
        )
    else:
        # NO CONFLICT: Multiple policies but same action
        return PolicyConflict(
            alert_id=alert_id,
            has_conflict=False,
            policies_applied=applicable,
            conflicting_policies=[],
            resolution=None
        )


def resolve_conflict(conflict: PolicyConflict) -> PolicyResolution:
    """
    Resolve a policy conflict by choosing the winner.

    Args:
        conflict: PolicyConflict object with conflicting policies

    Returns:
        PolicyResolution with winner and reasoning
    """
    if not conflict.has_conflict:
        raise ValueError("No conflict to resolve")

    if conflict.resolution:
        # Already resolved
        return conflict.resolution

    return resolve_conflict_internal(conflict.conflicting_policies)


def resolve_conflict_internal(conflicting_policies: List[PolicyDefinition]) -> PolicyResolution:
    """
    Internal conflict resolution logic.

    Args:
        conflicting_policies: List of conflicting policies

    Returns:
        PolicyResolution with winner determined by priority
    """
    # Sort by priority (1 = highest)
    sorted_policies = sorted(conflicting_policies, key=lambda p: p.priority)

    winner = sorted_policies[0]
    loser = sorted_policies[1]  # Assume 2 policies for demo simplicity

    # Generate audit ID
    audit_id = f"CON-2026-{random.randint(1000, 9999)}"

    # Build reason
    reason = (
        f"Policy {winner.id} (priority {winner.priority}) takes precedence over "
        f"Policy {loser.id} (priority {loser.priority}). "
        f"Security-first principle: higher priority policies override lower priority ones."
    )

    # Build narrative
    narrative = (
        f"Policy conflict detected and resolved. {winner.name} (priority {winner.priority}) "
        f"conflicts with {loser.name} (priority {loser.priority}). "
        f"Resolution: {winner.name} wins due to higher priority. "
        f"Original action would have been '{loser.action}', adjusted to '{winner.action}'. "
        f"This conflict has been logged for audit review (ID: {audit_id}). "
        f"Security-first principle applied: when policies conflict, the higher-priority "
        f"policy always wins to ensure no security gaps."
    )

    resolution = PolicyResolution(
        winning_policy=winner.id,
        losing_policy=loser.id,
        reason=reason,
        action_adjusted=winner.action,
        original_action=loser.action,
        audit_id=audit_id,
        narrative=narrative
    )

    # Store for tracking
    CONFLICTS_RESOLVED[audit_id] = resolution

    return resolution


def get_conflict_history() -> List[PolicyResolution]:
    """
    Get all resolved conflicts for audit/reporting.

    Returns:
        List of PolicyResolution objects
    """
    return list(CONFLICTS_RESOLVED.values())


def reset_policy_state():
    """Reset policy conflict state to initial values (for demo reset)"""
    global CONFLICTS_RESOLVED

    CONFLICTS_RESOLVED.clear()

    print("[POLICY] Policy conflict state reset to initial values")


# ============================================================================
# Demo Context Helpers
# ============================================================================

def get_demo_context_for_alert(alert_id: str) -> Dict[str, Any]:
    """
    Get simulated context for demo alerts.

    This is for testing/demo purposes only.
    In production, context comes from Neo4j.
    """
    if alert_id == "ALERT-7823":
        # John Smith - Traveling, high risk (CONFLICT scenario)
        return {
            "alert_type": "anomalous_login",
            "user_name": "John Smith",
            "user_risk_score": 0.85,
            "user_traveling": True,
            "vpn_matches_location": True,
            "mfa_completed": True,
            "device_fingerprint_match": True,
            "asset_criticality": "standard"
        }
    elif alert_id == "ALERT-7824":
        # Phishing - No conflict
        return {
            "alert_type": "phishing",
            "user_name": "Jane Doe",
            "user_risk_score": 0.45,
            "user_traveling": False,
            "known_campaign_signature": True,
            "asset_criticality": "standard"
        }
    else:
        # Default context
        return {
            "alert_type": "anomalous_login",
            "user_risk_score": 0.5,
            "user_traveling": False,
            "asset_criticality": "standard"
        }


# ============================================================================
# Self-Test
# ============================================================================

if __name__ == "__main__":
    print("[POLICY] Running self-tests...\n")

    # Test ALERT-7823 (should conflict)
    print("Test 1: ALERT-7823 (John Smith - high risk + traveling)")
    r1 = detect_policy_conflicts(
        "ALERT-7823",
        {
            "user_risk_score": 0.85,
            "user_traveling": True,
            "vpn_matches_location": True,
            "alert_type": "anomalous_login"
        }
    )
    print(f"  Conflict: {r1.has_conflict}")
    print(f"  Policies applied: {[p.id for p in r1.policies_applied]}")
    if r1.has_conflict:
        print(f"  Winner: {r1.resolution.winning_policy}")
        print(f"  Loser: {r1.resolution.losing_policy}")
        print(f"  Audit ID: {r1.resolution.audit_id}")

    assert r1.has_conflict, "ALERT-7823 should have a conflict!"
    assert len(r1.policies_applied) == 2, "Should match 2 policies"
    assert r1.resolution.winning_policy == "POL-ESCALATE-HIGH-RISK", "High-risk policy should win"
    print("  [PASS] Test 1 passed!\n")

    # Test ALERT-7824 (no conflict)
    print("Test 2: ALERT-7824 (Phishing - single policy)")
    r2 = detect_policy_conflicts(
        "ALERT-7824",
        {
            "user_risk_score": 0.45,
            "alert_type": "phishing",
            "known_campaign_signature": True
        }
    )
    print(f"  Conflict: {r2.has_conflict}")
    print(f"  Policies applied: {[p.id for p in r2.policies_applied]}")

    assert not r2.has_conflict, "ALERT-7824 should NOT have a conflict!"
    assert len(r2.policies_applied) == 1, "Should match 1 policy"
    assert r2.policies_applied[0].id == "POL-REMEDIATE-KNOWN-PHISH", "Should match phishing policy"
    print("  [PASS] Test 2 passed!\n")

    # Test no matching policies
    print("Test 3: Unknown alert (no policies match)")
    r3 = detect_policy_conflicts(
        "ALERT-9999",
        {
            "user_risk_score": 0.3,
            "alert_type": "unknown_type"
        }
    )
    print(f"  Conflict: {r3.has_conflict}")
    print(f"  Policies applied: {[p.id for p in r3.policies_applied]}")

    assert not r3.has_conflict, "Unknown alert should not conflict"
    assert len(r3.policies_applied) == 0, "Should match 0 policies"
    print("  [PASS] Test 3 passed!\n")

    print("=" * 60)
    print("[PASS] All self-tests passed!")
    print("=" * 60)
