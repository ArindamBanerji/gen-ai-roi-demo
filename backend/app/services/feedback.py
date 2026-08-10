"""
Outcome Feedback Loop - v2.5
Handles user feedback on decision outcomes and updates the graph accordingly.

Answers the CISO question: "What happens when the system is wrong?"
"""
import logging
from typing import Dict, Any, List, Optional, Literal, cast
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from app.domains.soc.config import SOCDomainConfig
from app.framework.feedback_store import FEEDBACK_GIVEN  # noqa: F401 -- re-exported for callers
from app.framework.feedback_base import (  # noqa: F401 -- re-exported for callers
    TRUST_SCORES,
    TRUST_HISTORY,
    LOW_TRUST_FLAGS,
    update_trust,
    get_trust_status,
    get_all_trust_scores,
    get_reward_summary,
)

logger = logging.getLogger(__name__)
_soc_cfg = SOCDomainConfig()


# ============================================================================
# In-Memory State (simulates persistent storage)
# ============================================================================

# FEEDBACK_GIVEN lives in app.framework.feedback_store — imported above.
# TRUST_SCORES, TRUST_HISTORY, LOW_TRUST_FLAGS live in app.framework.feedback_base — imported above.

# Pattern confidence scores (simulated)
# H7-FIX-1: all 6 SOC categories + legacy demo patterns initialised
PATTERN_CONFIDENCE = {
    "PAT-TRAVEL-001":  0.94,   # legacy -- kept for backward compat
    "PAT-PHISH-001":   0.89,   # legacy -- kept for backward compat
    "PAT-CRED-001":    0.85,
    "PAT-THREAT-001":  0.82,
    "PAT-LATERAL-001": 0.80,
    "PAT-EXFIL-001":   0.83,
    "PAT-INSIDER-001": 0.78,
    "PAT-CLOUD-001":   0.81,
    "PAT-UNKNOWN-001": 0.70,
}

# Edge weights (simulated)
# H7-FIX-1: category-specific edges added alongside legacy keys
EDGE_WEIGHTS = {
    "User->TravelContext":      0.91,   # legacy
    "User->PhishingCampaign":   0.87,   # legacy
    "User->CredentialStore":    0.84,
    "Alert->ThreatFeed":        0.82,
    "User->LateralHost":        0.80,
    "Asset->ExternalEndpoint":  0.83,
    "User->SensitiveAsset":     0.79,
    "Service->CloudResource":   0.81,
    "User->Unknown":            0.70,
}

# Precedent counts (simulated)
# H7-FIX-1: all 6 SOC category patterns initialised
PRECEDENT_COUNTS = {
    "PAT-TRAVEL-001":  127,   # legacy
    "PAT-PHISH-001":    89,   # legacy
    "PAT-CRED-001":     54,
    "PAT-THREAT-001":   41,
    "PAT-LATERAL-001":  33,
    "PAT-EXFIL-001":    28,
    "PAT-INSIDER-001":  19,
    "PAT-CLOUD-001":    37,
    "PAT-UNKNOWN-001":   0,
}

# H7-FIX-1: SOC category → graph edge key
_CATEGORY_EDGE_MAP: Dict[str, str] = {
    "credential_access":    "User->CredentialStore",
    "malware_execution":    "Alert->ThreatFeed",
    "lateral_movement":     "User->LateralHost",
    "data_exfiltration":    "Asset->ExternalEndpoint",
    "insider_threat":       "User->SensitiveAsset",
    "cloud_infrastructure": "Service->CloudResource",
    "_default":             "User->Unknown",
}


# ============================================================================
# Pydantic Models
# ============================================================================

class GraphUpdate(BaseModel):
    """Represents a single graph entity update"""
    entity: str
    field: str
    before: float
    after: float
    direction: Literal["strengthened", "weakened"]


class NextAlertsOverride(BaseModel):
    """Override behavior for next N alerts"""
    action: str
    count: int
    reason: str


class OutcomeResponse(BaseModel):
    """Response after processing outcome feedback"""
    alert_id: str
    outcome: str
    graph_updates: List[GraphUpdate]
    consequence: str
    next_alerts_override: Optional[NextAlertsOverride]
    narrative: str


# ============================================================================
# Core Functions
# ============================================================================

def process_outcome(
    alert_id: str,
    decision_id: str,
    outcome: Literal["correct", "incorrect"],
    alert_category: str = "",
) -> OutcomeResponse:
    """
    Process user feedback on decision outcome and update graph.

    Args:
        alert_id:       Alert identifier (e.g., "ALERT-7823")
        decision_id:    Decision identifier (e.g., "DEC-7823-001")
        outcome:        Whether the outcome was correct or incorrect
        alert_category: SOC category string (e.g. "credential_access").
                        When provided, used to select the canonical pattern.
                        When absent, inferred from alert_id for known demo
                        alerts; unknown alerts fall back to "_default".

    Returns:
        OutcomeResponse with graph updates and narrative
    """
    # H7-FIX-1: derive pattern from category, not from hardcoded alert_id checks.
    # Caller may pass alert_category directly; fall back to demo-alert mapping
    # for the two known seed alerts so existing demos continue to work.
    if not alert_category:
        if "7823" in alert_id:
            # ALERT-7823 is a credential-access / travel-login demo alert
            alert_category = "credential_access"
        elif "7824" in alert_id:
            # ALERT-7824 is a malware-execution / phishing demo alert
            alert_category = "malware_execution"
        else:
            logger.warning(
                "[H7-FIX-1] Could not determine category for alert %s, "
                "using default pattern",
                alert_id,
            )
            alert_category = "_default"

    pattern_id = _soc_cfg.get_pattern_for_category(alert_category)
    edge_key   = _CATEGORY_EDGE_MAP.get(alert_category, _CATEGORY_EDGE_MAP["_default"])
    alert_type = alert_category.replace("_", " ")

    graph_updates = []
    consequence = ""
    next_alerts_override = None
    narrative = ""

    if outcome == "correct":
        # Positive feedback - strengthen pattern
        old_confidence = PATTERN_CONFIDENCE[pattern_id]
        new_confidence = min(old_confidence + 0.003, 0.99)  # +0.3 points, cap at 99%
        PATTERN_CONFIDENCE[pattern_id] = new_confidence

        graph_updates.append(GraphUpdate(
            entity=pattern_id,
            field="confidence",
            before=old_confidence,
            after=new_confidence,
            direction="strengthened"
        ))

        # Strengthen edge weight
        old_weight = EDGE_WEIGHTS[edge_key]
        new_weight = min(old_weight + 0.02, 0.99)
        EDGE_WEIGHTS[edge_key] = new_weight

        graph_updates.append(GraphUpdate(
            entity=edge_key,
            field="weight",
            before=old_weight,
            after=new_weight,
            direction="strengthened"
        ))

        # Increment precedent count
        old_count = PRECEDENT_COUNTS[pattern_id]
        new_count = old_count + 1
        PRECEDENT_COUNTS[pattern_id] = new_count

        graph_updates.append(GraphUpdate(
            entity=pattern_id,
            field="precedent_count",
            before=float(old_count),
            after=float(new_count),
            direction="strengthened"
        ))

        consequence = "Pattern strengthened. Added to precedent library."

        narrative = (
            f"Decision confirmed correct. Pattern {pattern_id} confidence increased "
            f"to {new_confidence*100:.1f}% (+{(new_confidence-old_confidence)*100:.1f} points). "
            f"This decision has been added to the precedent library ({new_count} validated decisions). "
            f"The system is now slightly more confident in auto-closing similar alerts of this type."
        )

        next_alerts_override = None

    else:  # outcome == "incorrect"
        # Negative feedback - weaken pattern (asymmetric, hits harder)
        old_confidence = PATTERN_CONFIDENCE[pattern_id]
        new_confidence = max(old_confidence - 0.06, 0.50)  # -6 points, floor at 50%
        PATTERN_CONFIDENCE[pattern_id] = new_confidence

        graph_updates.append(GraphUpdate(
            entity=pattern_id,
            field="confidence",
            before=old_confidence,
            after=new_confidence,
            direction="weakened"
        ))

        # Weaken edge weight
        old_weight = EDGE_WEIGHTS[edge_key]
        new_weight = max(old_weight - 0.05, 0.50)
        EDGE_WEIGHTS[edge_key] = new_weight

        graph_updates.append(GraphUpdate(
            entity=edge_key,
            field="weight",
            before=old_weight,
            after=new_weight,
            direction="weakened"
        ))

        # Trigger threshold review
        consequence = (
            "Pattern weakened. Threshold review triggered. "
            "Next 5 similar alerts routed to Tier 2."
        )

        narrative = (
            f"Decision outcome negative. Pattern {pattern_id} confidence dropped "
            f"to {new_confidence*100:.1f}% ({(new_confidence-old_confidence)*100:.1f} points). "
            f"The system has triggered a threshold review and will route the next 5 "
            f"similar alerts to Tier 2 analysts for manual review. "
            f"This is self-correction in action -- the system learned from this mistake "
            f"and adjusted its behavior."
        )

        next_alerts_override = NextAlertsOverride(
            action="escalate_tier2",
            count=5,
            reason="Confidence drop after incorrect outcome"
        )

    # Store feedback
    FEEDBACK_GIVEN[alert_id] = {
        "decision_id": decision_id,
        "outcome": outcome,
        "timestamp": datetime.now().isoformat(),
        "graph_updates": [u.model_dump() for u in graph_updates]
    }

    # F6a: Update per-category trust score (asymmetric 20:1)
    # alert_category is already resolved above — key trust on threat category,
    # not on alert_type or hardcoded alert_id substrings (BACKLOG-047).
    update_trust(alert_category, outcome)

    return OutcomeResponse(
        alert_id=alert_id,
        outcome=outcome,
        graph_updates=graph_updates,
        consequence=consequence,
        next_alerts_override=next_alerts_override,
        narrative=narrative
    )


def get_feedback_status(alert_id: str) -> Dict[str, Any]:
    """
    Get feedback status for an alert.

    Args:
        alert_id: Alert identifier

    Returns:
        Dictionary with feedback status
    """
    if alert_id in FEEDBACK_GIVEN:
        feedback = FEEDBACK_GIVEN[alert_id]
        return {
            "has_feedback": True,
            "outcome": feedback["outcome"],
            "timestamp": feedback["timestamp"],
            "can_modify": False  # Once given, feedback is immutable in this demo
        }
    else:
        return {
            "has_feedback": False,
            "can_modify": True
        }


def get_feedback_record(alert_id: str, decision_id: str) -> Optional[Dict[str, Any]]:
    """Return the stored feedback only when it belongs to ``decision_id``."""
    feedback = FEEDBACK_GIVEN.get(alert_id)
    if feedback is None or feedback.get("decision_id") != decision_id:
        return None
    return cast(Dict[str, Any], feedback)


def get_current_pattern_state() -> Dict[str, Any]:
    """
    Get current state of patterns and edges for display.

    Returns:
        Dictionary with current confidence scores and weights
    """
    return {
        "patterns": {
            pattern_id: {
                "confidence": confidence,
                "precedent_count": PRECEDENT_COUNTS.get(pattern_id, 0)
            }
            for pattern_id, confidence in PATTERN_CONFIDENCE.items()
        },
        "edges": EDGE_WEIGHTS.copy()
    }


def seed_trust_history() -> None:
    """
    Pre-populate TRUST_HISTORY with 12 realistic historical snapshots for
    travel_login_anomaly, telling the asymmetry story from first load:

      Decisions 1-9  : correct  (+0.03 each) -> trust rises 0.50 -> 0.77
      Decision  10   : incorrect (-0.60)     -> trust crashes   0.77 -> 0.17
      Decisions 11-12: correct  (+0.03 each) -> recovery starts 0.17 -> 0.23

    Final state: trust=0.23, human_review_required=True.

    Called at end of reset_trust_state() AND at module import so charts
    are always populated without requiring live interaction.
    Live decisions append to this baseline (decision_number continues from 13+).
    """
    situation_type = "travel_login_anomaly"

    # (outcome, trust_score_after_this_entry)
    _ENTRIES = [
        ("correct",   0.53),   #  1: 0.50 + 0.03
        ("correct",   0.56),   #  2
        ("correct",   0.59),   #  3
        ("correct",   0.62),   #  4
        ("correct",   0.65),   #  5
        ("correct",   0.68),   #  6
        ("correct",   0.71),   #  7
        ("correct",   0.74),   #  8
        ("correct",   0.77),   #  9  <- peak before the crash
        ("incorrect", 0.17),   # 10  <- one wrong answer wipes 9 correct ones
        ("correct",   0.20),   # 11  <- slow recovery
        ("correct",   0.23),   # 12  <- still in danger zone (< 0.3)
    ]

    base_ts = datetime.now(timezone.utc) - timedelta(hours=12)
    for dec, (outcome, trust_after) in enumerate(_ENTRIES, start=1):
        ts = base_ts + timedelta(hours=dec)
        delta = 0.03 if outcome == "correct" else -0.60
        TRUST_HISTORY.append({
            "decision_number": dec,
            "timestamp":       ts.isoformat(),
            "situation_type":  situation_type,
            "trust_score":     trust_after,
            "delta":           delta,
            "outcome":         outcome,
        })

    # Set current live state to match end-of-seed values
    final_trust = _ENTRIES[-1][1]   # 0.23
    TRUST_SCORES[situation_type] = final_trust
    LOW_TRUST_FLAGS[situation_type] = final_trust < 0.3  # True

    print(
        f"[TRUST] Seeded {len(_ENTRIES)} historical trust snapshots for '{situation_type}' -- "
        f"current trust={final_trust:.2f}, human_review_required={LOW_TRUST_FLAGS[situation_type]}"
    )


# seed_trust_history() is called explicitly from main.py startup_event()
# so charts are populated once at boot, not on every module import.


def reset_trust_state() -> None:
    """
    Reset all trust tracking state to seeded baseline (for demo reset).
    Registered with state_manager so reset_all() covers this automatically.
    """
    TRUST_SCORES.clear()
    TRUST_HISTORY.clear()
    LOW_TRUST_FLAGS.clear()
    seed_trust_history()
    print("[TRUST] Trust state reset to seeded baseline")


def reset_feedback_state():
    """Reset all feedback state to initial values (for demo reset)"""
    global FEEDBACK_GIVEN, PATTERN_CONFIDENCE, EDGE_WEIGHTS, PRECEDENT_COUNTS

    FEEDBACK_GIVEN.clear()

    # Legacy demo patterns
    PATTERN_CONFIDENCE["PAT-TRAVEL-001"]  = 0.94
    PATTERN_CONFIDENCE["PAT-PHISH-001"]   = 0.89
    # H7-FIX-1: category-based patterns
    PATTERN_CONFIDENCE["PAT-CRED-001"]    = 0.85
    PATTERN_CONFIDENCE["PAT-THREAT-001"]  = 0.82
    PATTERN_CONFIDENCE["PAT-LATERAL-001"] = 0.80
    PATTERN_CONFIDENCE["PAT-EXFIL-001"]   = 0.83
    PATTERN_CONFIDENCE["PAT-INSIDER-001"] = 0.78
    PATTERN_CONFIDENCE["PAT-CLOUD-001"]   = 0.81
    PATTERN_CONFIDENCE["PAT-UNKNOWN-001"] = 0.70

    # Legacy edges
    EDGE_WEIGHTS["User->TravelContext"]     = 0.91
    EDGE_WEIGHTS["User->PhishingCampaign"]  = 0.87
    # H7-FIX-1: category edges
    EDGE_WEIGHTS["User->CredentialStore"]   = 0.84
    EDGE_WEIGHTS["Alert->ThreatFeed"]       = 0.82
    EDGE_WEIGHTS["User->LateralHost"]       = 0.80
    EDGE_WEIGHTS["Asset->ExternalEndpoint"] = 0.83
    EDGE_WEIGHTS["User->SensitiveAsset"]    = 0.79
    EDGE_WEIGHTS["Service->CloudResource"]  = 0.81
    EDGE_WEIGHTS["User->Unknown"]           = 0.70

    # Legacy precedents
    PRECEDENT_COUNTS["PAT-TRAVEL-001"]  = 127
    PRECEDENT_COUNTS["PAT-PHISH-001"]   =  89
    # H7-FIX-1: category precedents
    PRECEDENT_COUNTS["PAT-CRED-001"]    =  54
    PRECEDENT_COUNTS["PAT-THREAT-001"]  =  41
    PRECEDENT_COUNTS["PAT-LATERAL-001"] =  33
    PRECEDENT_COUNTS["PAT-EXFIL-001"]   =  28
    PRECEDENT_COUNTS["PAT-INSIDER-001"] =  19
    PRECEDENT_COUNTS["PAT-CLOUD-001"]   =  37
    PRECEDENT_COUNTS["PAT-UNKNOWN-001"] =   0

    print("[FEEDBACK] State reset to initial values")
