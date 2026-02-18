"""
Outcome Feedback Loop - v2.5
Handles user feedback on decision outcomes and updates the graph accordingly.

Answers the CISO question: "What happens when the system is wrong?"
"""
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel


# ============================================================================
# In-Memory State (simulates persistent storage)
# ============================================================================

# Tracks which alerts have received feedback
FEEDBACK_GIVEN: Dict[str, Dict[str, Any]] = {}

# Pattern confidence scores (simulated)
PATTERN_CONFIDENCE = {
    "PAT-TRAVEL-001": 0.94,
    "PAT-PHISH-001": 0.89,
}

# Edge weights (simulated)
EDGE_WEIGHTS = {
    "User->TravelContext": 0.91,
    "User->PhishingCampaign": 0.87,
}

# Precedent counts (simulated)
PRECEDENT_COUNTS = {
    "PAT-TRAVEL-001": 127,
    "PAT-PHISH-001": 89,
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
    outcome: Literal["correct", "incorrect"]
) -> OutcomeResponse:
    """
    Process user feedback on decision outcome and update graph.

    Args:
        alert_id: Alert identifier (e.g., "ALERT-7823")
        decision_id: Decision identifier (e.g., "DEC-7823-001")
        outcome: Whether the outcome was correct or incorrect

    Returns:
        OutcomeResponse with graph updates and narrative
    """
    # Determine pattern based on alert ID
    if "7823" in alert_id:
        pattern_id = "PAT-TRAVEL-001"
        edge_key = "User->TravelContext"
        alert_type = "travel login anomaly"
    elif "7824" in alert_id:
        pattern_id = "PAT-PHISH-001"
        edge_key = "User->PhishingCampaign"
        alert_type = "phishing alert"
    else:
        # Default to travel
        pattern_id = "PAT-TRAVEL-001"
        edge_key = "User->TravelContext"
        alert_type = "alert"

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
            f"This is self-correction in action — the system learned from this mistake "
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
        "graph_updates": [u.dict() for u in graph_updates]
    }

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


def reset_feedback_state():
    """Reset all feedback state to initial values (for demo reset)"""
    global FEEDBACK_GIVEN, PATTERN_CONFIDENCE, EDGE_WEIGHTS, PRECEDENT_COUNTS

    FEEDBACK_GIVEN.clear()

    PATTERN_CONFIDENCE["PAT-TRAVEL-001"] = 0.94
    PATTERN_CONFIDENCE["PAT-PHISH-001"] = 0.89

    EDGE_WEIGHTS["User->TravelContext"] = 0.91
    EDGE_WEIGHTS["User->PhishingCampaign"] = 0.87

    PRECEDENT_COUNTS["PAT-TRAVEL-001"] = 127
    PRECEDENT_COUNTS["PAT-PHISH-001"] = 89

    print("[FEEDBACK] State reset to initial values")
