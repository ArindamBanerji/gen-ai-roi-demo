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
    # F2b: expanded corpus (8 new alert types)
    BRUTE_FORCE_ATTACK = "brute_force_attack"
    PRIVILEGE_ESCALATION_DETECTED = "privilege_escalation_detected"
    CREDENTIAL_STUFFING_ATTACK = "credential_stuffing_attack"
    C2_COMMUNICATION = "c2_communication"
    THREAT_INTEL_INDICATOR = "threat_intel_indicator"
    ANOMALOUS_NETWORK_BEHAVIOR = "anomalous_network_behavior"
    INSIDER_THREAT_DETECTED = "insider_threat_detected"
    CLOUD_MISCONFIGURATION = "cloud_misconfiguration"


# ============================================================================
# Pydantic Models
# ============================================================================

class OptionEvaluated(BaseModel):
    """A single response option with score and factors"""
    action: str
    score: float = Field(ge=0.0, le=1.0)
    factors: List[str]
    estimated_resolution_time: str = ""
    estimated_analyst_cost: float = 0.0
    risk_if_wrong: str = ""


class DecisionEconomics(BaseModel):
    """Economic impact summary of the decision"""
    time_saved: str
    cost_avoided: str
    monthly_projection: str


class SituationAnalysis(BaseModel):
    """Complete situation analysis result"""
    situation_type: str
    situation_confidence: float = Field(ge=0.0, le=1.0)
    factors_detected: List[str]
    options_evaluated: List[OptionEvaluated]
    selected_option: str
    selection_reasoning: str
    decision_economics: DecisionEconomics
    mitre_technique: str = ""   # e.g. "T1078"  — populated from MITRE_ATTACK_MAP (F1a)
    mitre_tactic: str = ""      # e.g. "Initial Access"


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

    from app.domains.soc.situations import classify_soc_situation
    situation_value, confidence, factors = classify_soc_situation(alert_type, context)
    return SituationType(situation_value), confidence, factors


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

    from app.domains.soc.situations import get_soc_options
    raw_options = get_soc_options(situation_type.value, context)
    return [OptionEvaluated(**opt) for opt in raw_options]


# ============================================================================
# Decision Economics Calculation
# ============================================================================

def calculate_decision_economics(selected: OptionEvaluated, all_options: List[OptionEvaluated]) -> DecisionEconomics:
    """
    Calculate economic impact of the decision.
    Compares selected option against the next-best human-involved option (usually escalate_tier2).

    Args:
        selected: The selected option
        all_options: All evaluated options

    Returns:
        DecisionEconomics with savings calculations
    """

    # Find the most expensive human-involved option (usually escalate_tier2 or escalate_incident)
    human_options = [opt for opt in all_options if opt.action in ["escalate_tier2", "escalate_incident"]]

    if not human_options:
        # No human option to compare against
        return DecisionEconomics(
            time_saved="N/A",
            cost_avoided="N/A",
            monthly_projection="N/A"
        )

    # Use the first human option (likely escalate_tier2) as baseline
    baseline = human_options[0]

    # Calculate savings
    cost_saved = baseline.estimated_analyst_cost - selected.estimated_analyst_cost

    # Parse time strings for comparison (rough conversion)
    def parse_time_to_minutes(time_str: str) -> float:
        """Convert time string to minutes"""
        if "second" in time_str:
            return float(time_str.split()[0]) / 60.0
        elif "minute" in time_str:
            return float(time_str.split()[0])
        elif "hour" in time_str:
            return float(time_str.split()[0]) * 60.0
        return 0.0

    selected_minutes = parse_time_to_minutes(selected.estimated_resolution_time)
    baseline_minutes = parse_time_to_minutes(baseline.estimated_resolution_time)
    time_saved_minutes = baseline_minutes - selected_minutes

    # Format time saved
    if time_saved_minutes > 60:
        time_saved_str = f"{time_saved_minutes / 60:.1f} hours vs manual triage"
    else:
        time_saved_str = f"{int(time_saved_minutes)} minutes vs manual triage"

    # Format cost avoided
    cost_avoided_str = f"${int(cost_saved)} analyst cost avoided per alert" if cost_saved > 0 else "No cost savings"

    # Monthly projection (assume ~200 similar alerts/month)
    monthly_alerts = 200
    monthly_cost_saved = int(cost_saved * monthly_alerts)
    monthly_hours_saved = int((time_saved_minutes / 60.0) * monthly_alerts)

    monthly_projection_str = (
        f"At ~{monthly_alerts} similar alerts/month: {monthly_hours_saved} analyst-hours and ${monthly_cost_saved:,} saved"
    )

    return DecisionEconomics(
        time_saved=time_saved_str,
        cost_avoided=cost_avoided_str,
        monthly_projection=monthly_projection_str
    )


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

    # Step 2: Look up MITRE ATT&CK mapping for the classified situation type (F1a)
    from app.domains.soc.situations import get_mitre_attack
    mitre_technique, mitre_tactic = get_mitre_attack(situation_type.value)

    # Step 3: Evaluate options
    options = evaluate_options(alert_type, context, situation_type)

    # Step 4: Select the highest-scored option
    selected = options[0]  # Already sorted by score descending

    # Step 5: Generate selection reasoning
    reasoning = generate_selection_reasoning(situation_type, selected, factors)

    # Step 6: Calculate decision economics
    economics = calculate_decision_economics(selected, options)

    return SituationAnalysis(
        situation_type=situation_type.value,
        situation_confidence=confidence,
        factors_detected=factors,
        options_evaluated=options,
        selected_option=selected.action,
        selection_reasoning=reasoning,
        decision_economics=economics,
        mitre_technique=mitre_technique,
        mitre_tactic=mitre_tactic,
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

    if situation_type == SituationType.BRUTE_FORCE_ATTACK:
        return "Repeated authentication failures confirm automated attack. Source blocking prevents account compromise."

    if situation_type == SituationType.PRIVILEGE_ESCALATION_DETECTED:
        return "Unauthorized privilege escalation requires immediate containment to prevent lateral movement."

    if situation_type == SituationType.CREDENTIAL_STUFFING_ATTACK:
        return "Multiple accounts targeted with leaked credentials. Bulk password reset prevents takeover at scale."

    if situation_type == SituationType.C2_COMMUNICATION:
        return "Active C2 channel detected. Isolating the host severs attacker control and stops potential exfiltration."

    if situation_type == SituationType.THREAT_INTEL_INDICATOR:
        return "Confirmed IOC match from threat intelligence feed. Immediate incident escalation contains the threat."

    if situation_type == SituationType.ANOMALOUS_NETWORK_BEHAVIOR:
        return "Unusual traffic pattern requires additional context before action. Enrichment reduces false positive risk."

    if situation_type == SituationType.INSIDER_THREAT_DETECTED:
        return "Suspected insider activity requires escalation with HR involvement. Confidential investigation warranted."

    if situation_type == SituationType.CLOUD_MISCONFIGURATION:
        return "Exposed cloud resource remediation is low-risk and immediate. Auto-fix closes exposure window in seconds."

    return "Insufficient context for automated decision. Manual review by Tier 2 analyst recommended."
