"""
Situation Analyzer - Classification and Option Evaluation
~100-120 lines. Rule-based situation classification for Loop 1 (Context).

The Situation Analyzer classifies alert scenarios and evaluates multiple response
options with scores, demonstrating "smarter WITHIN each decision."
"""
from enum import Enum
from typing import Dict, Any, List
from pydantic import BaseModel, Field


# ============================================================================
# Situation Types
# ============================================================================

class SituationType(str, Enum):
    """Alert situation classifications"""
    TRAVEL_LOGIN_ANOMALY = "travel_login_anomaly"
    KNOWN_PHISHING_CAMPAIGN = "known_phishing_campaign"
    MALWARE_ON_CRITICAL_ASSET = "malware_on_critical_asset"
    VIP_AFTER_HOURS = "vip_after_hours"
    DATA_EXFIL_ATTEMPT = "data_exfil_attempt"
    UNKNOWN = "unknown"


# ============================================================================
# Pydantic Models
# ============================================================================

class OptionEvaluated(BaseModel):
    """A single response option with score and factors"""
    action: str
    score: float = Field(ge=0.0, le=1.0)
    factors: List[str]


class SituationAnalysis(BaseModel):
    """Complete situation analysis result"""
    situation_type: str
    situation_confidence: float = Field(ge=0.0, le=1.0)
    factors_detected: List[str]
    options_evaluated: List[OptionEvaluated]
    selected_option: str
    selection_reasoning: str


# ============================================================================
# Classification Logic
# ============================================================================

def classify_situation(alert_type: str, context: Dict[str, Any]) -> tuple[SituationType, float, List[str]]:
    """
    Classify the alert situation based on alert type and context.
    Rule-based logic similar to agent.py.

    Args:
        alert_type: Type of alert (anomalous_login, phishing, malware_detection, data_exfiltration)
        context: Security context from graph traversal

    Returns:
        (situation_type, confidence, factors_detected)
    """

    factors = []

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

        return SituationType.TRAVEL_LOGIN_ANOMALY, 0.94, factors

    # ====================================================================
    # Rule 2: Known Phishing Campaign
    # ====================================================================
    if alert_type == "phishing":
        factors = ["phishing_alert"]
        if context.get("known_campaign_signature"):
            factors.append("known_campaign_signature")
            factors.append("similar_emails_blocked")
            return SituationType.KNOWN_PHISHING_CAMPAIGN, 0.96, factors
        else:
            factors.append("novel_phishing_attempt")
            return SituationType.KNOWN_PHISHING_CAMPAIGN, 0.72, factors

    # ====================================================================
    # Rule 3: Malware on Critical Asset
    # ====================================================================
    if alert_type == "malware_detection" and context.get("asset_criticality") == "critical":
        factors = [
            "malware_detected",
            f"critical_asset ({context.get('asset_hostname', 'Unknown')})",
            "production_system"
        ]
        return SituationType.MALWARE_ON_CRITICAL_ASSET, 0.97, factors

    # ====================================================================
    # Rule 4: Data Exfiltration Attempt
    # ====================================================================
    if alert_type == "data_exfiltration":
        factors = [
            "unusual_data_transfer",
            "external_destination",
            "volume_threshold_exceeded"
        ]
        return SituationType.DATA_EXFIL_ATTEMPT, 0.95, factors

    # ====================================================================
    # Rule 5: VIP After Hours
    # ====================================================================
    user_title = context.get("user_title", "").lower()
    is_vip = any(vip_term in user_title for vip_term in ["ceo", "cfo", "ciso", "vp", "chief", "executive"])

    if is_vip and context.get("after_hours", False):
        factors = [
            f"vip_user ({context.get('user_name', 'Unknown')})",
            "after_hours_activity",
            "unusual_timing"
        ]
        return SituationType.VIP_AFTER_HOURS, 0.78, factors

    # ====================================================================
    # Default: Unknown Situation
    # ====================================================================
    factors = ["insufficient_context", f"alert_type_{alert_type}"]
    return SituationType.UNKNOWN, 0.45, factors


# ============================================================================
# Option Evaluation Logic
# ============================================================================

def evaluate_options(alert_type: str, context: Dict[str, Any], situation_type: SituationType) -> List[OptionEvaluated]:
    """
    Evaluate response options for the given situation.
    Returns 3 options with scores that sum to ~1.0.

    Args:
        alert_type: Type of alert
        context: Security context
        situation_type: Classified situation type

    Returns:
        List of OptionEvaluated objects (sorted by score, descending)
    """

    # ====================================================================
    # TRAVEL_LOGIN_ANOMALY - Likely false positive
    # ====================================================================
    if situation_type == SituationType.TRAVEL_LOGIN_ANOMALY:
        return [
            OptionEvaluated(
                action="false_positive_close",
                score=0.92,
                factors=["travel_match", "mfa_ok", "device_known"]
            ),
            OptionEvaluated(
                action="escalate_tier2",
                score=0.06,
                factors=["verify_travel_legitimacy"]
            ),
            OptionEvaluated(
                action="enrich_and_wait",
                score=0.02,
                factors=["monitor_additional_activity"]
            )
        ]

    # ====================================================================
    # KNOWN_PHISHING_CAMPAIGN - Auto-remediate
    # ====================================================================
    if situation_type == SituationType.KNOWN_PHISHING_CAMPAIGN:
        return [
            OptionEvaluated(
                action="auto_remediate",
                score=0.94,
                factors=["known_signature", "playbook_exists", "low_risk"]
            ),
            OptionEvaluated(
                action="escalate_tier2",
                score=0.04,
                factors=["verify_campaign_match"]
            ),
            OptionEvaluated(
                action="enrich_and_wait",
                score=0.02,
                factors=["gather_more_samples"]
            )
        ]

    # ====================================================================
    # MALWARE_ON_CRITICAL_ASSET - Escalate to incident
    # ====================================================================
    if situation_type == SituationType.MALWARE_ON_CRITICAL_ASSET:
        return [
            OptionEvaluated(
                action="escalate_incident",
                score=0.97,
                factors=["critical_asset", "production_impact", "high_risk"]
            ),
            OptionEvaluated(
                action="auto_remediate",
                score=0.02,
                factors=["isolate_system"]
            ),
            OptionEvaluated(
                action="enrich_and_wait",
                score=0.01,
                factors=["assess_blast_radius"]
            )
        ]

    # ====================================================================
    # DATA_EXFIL_ATTEMPT - Escalate to incident
    # ====================================================================
    if situation_type == SituationType.DATA_EXFIL_ATTEMPT:
        return [
            OptionEvaluated(
                action="escalate_incident",
                score=0.96,
                factors=["data_loss_risk", "external_connection", "volume_anomaly"]
            ),
            OptionEvaluated(
                action="enrich_and_wait",
                score=0.03,
                factors=["identify_data_type"]
            ),
            OptionEvaluated(
                action="auto_remediate",
                score=0.01,
                factors=["block_connection"]
            )
        ]

    # ====================================================================
    # VIP_AFTER_HOURS - Enrich and wait
    # ====================================================================
    if situation_type == SituationType.VIP_AFTER_HOURS:
        return [
            OptionEvaluated(
                action="enrich_and_wait",
                score=0.76,
                factors=["vip_caution", "verify_legitimacy", "context_needed"]
            ),
            OptionEvaluated(
                action="escalate_tier2",
                score=0.18,
                factors=["manual_review"]
            ),
            OptionEvaluated(
                action="false_positive_close",
                score=0.06,
                factors=["workaholic_pattern"]
            )
        ]

    # ====================================================================
    # UNKNOWN - Default conservative approach
    # ====================================================================
    return [
        OptionEvaluated(
            action="escalate_tier2",
            score=0.60,
            factors=["insufficient_confidence", "manual_review_needed"]
        ),
        OptionEvaluated(
            action="enrich_and_wait",
            score=0.30,
            factors=["gather_more_context"]
        ),
        OptionEvaluated(
            action="escalate_incident",
            score=0.10,
            factors=["err_on_caution"]
        )
    ]


# ============================================================================
# Main Analysis Function
# ============================================================================

def analyze_situation(alert_type: str, context: Dict[str, Any]) -> SituationAnalysis:
    """
    Perform complete situation analysis.
    Combines classification and option evaluation.

    Args:
        alert_type: Type of alert
        context: Security context from graph traversal

    Returns:
        SituationAnalysis with all fields populated
    """

    # Step 1: Classify the situation
    situation_type, confidence, factors = classify_situation(alert_type, context)

    # Step 2: Evaluate options
    options = evaluate_options(alert_type, context, situation_type)

    # Step 3: Select the highest-scored option
    selected = options[0]  # Already sorted by score descending

    # Step 4: Generate selection reasoning
    reasoning = generate_selection_reasoning(situation_type, selected, factors)

    return SituationAnalysis(
        situation_type=situation_type.value,
        situation_confidence=confidence,
        factors_detected=factors,
        options_evaluated=options,
        selected_option=selected.action,
        selection_reasoning=reasoning
    )


def generate_selection_reasoning(situation_type: SituationType, selected: OptionEvaluated, factors: List[str]) -> str:
    """Generate a brief explanation for the selected option"""

    if situation_type == SituationType.TRAVEL_LOGIN_ANOMALY:
        return "Travel record confirms user location. All authentication factors align with legitimate access."

    if situation_type == SituationType.KNOWN_PHISHING_CAMPAIGN:
        return "Email matches known campaign signature. Automated remediation is safe and effective."

    if situation_type == SituationType.MALWARE_ON_CRITICAL_ASSET:
        return "Critical production asset requires immediate incident response to prevent business impact."

    if situation_type == SituationType.DATA_EXFIL_ATTEMPT:
        return "Unusual data transfer to external destination requires immediate investigation and containment."

    if situation_type == SituationType.VIP_AFTER_HOURS:
        return "VIP user activity requires careful verification before escalation to avoid false alarms."

    return "Insufficient context for automated decision. Manual review by Tier 2 analyst recommended."
