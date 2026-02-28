"""
Outcome Feedback Loop - v2.5
Handles user feedback on decision outcomes and updates the graph accordingly.

Answers the CISO question: "What happens when the system is wrong?"
"""
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime, timedelta, timezone
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

# F6a: Asymmetric trust per situation type.
# Starting trust: 0.5.  Correct: +0.03 (cap 1.0).  Incorrect: −0.60 (floor 0.0).
# That 20:1 ratio is the "wrong answer costs 20× more than a right answer helps".
TRUST_SCORES: Dict[str, float] = {}    # situation_type → current trust (0.0–1.0)
TRUST_HISTORY: List[Dict[str, Any]] = []  # one entry per trust update
LOW_TRUST_FLAGS: Dict[str, bool] = {}  # situation_type → human_review_required


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
        "graph_updates": [u.model_dump() for u in graph_updates]
    }

    # F6a: Update per-situation-type trust score (asymmetric 20:1)
    _SIT_MAP = {"7823": "travel_login_anomaly", "7824": "known_phishing_campaign"}
    sit_type = next((v for k, v in _SIT_MAP.items() if k in alert_id), "travel_login_anomaly")
    update_trust(sit_type, outcome)

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


def get_reward_summary() -> Dict[str, Any]:
    """
    Aggregate current in-memory feedback state into an RL reward summary.

    Reward signal:
        correct   → +0.3  (reinforces good decisions)
        incorrect → -6.0  (asymmetric penalty, ratio 20:1)

    Returns:
        Dictionary with totals, cumulative reward, and loop governance info.
    """
    total_decisions = len(FEEDBACK_GIVEN)
    correct = sum(1 for v in FEEDBACK_GIVEN.values() if v["outcome"] == "correct")
    incorrect = sum(1 for v in FEEDBACK_GIVEN.values() if v["outcome"] == "incorrect")
    cumulative_r_t = round(correct * 0.3 + incorrect * (-6.0), 4)

    return {
        "total_decisions": total_decisions,
        "correct": correct,
        "incorrect": incorrect,
        "asymmetric_ratio": 20.0,
        "cumulative_r_t": cumulative_r_t,
        "loop3_status": "active" if total_decisions > 0 else "insufficient_data",
        "governs": ["loop1_situation_analyzer", "loop2_agent_evolver"],
    }


# ============================================================================
# F6a: Trust Score Functions
# ============================================================================

def update_trust(situation_type: str, outcome: Literal["correct", "incorrect"]) -> Dict[str, Any]:
    """
    Update trust score for a situation type after a decision outcome.

    Asymmetric deltas (20:1 ratio):
        correct   → +0.03  (slow build-up of trust)
        incorrect → −0.60  (fast destruction of trust)

    Sets LOW_TRUST_FLAGS[situation_type] = True when trust drops below 0.3,
    which signals that human review should be required for this situation type.

    Args:
        situation_type: Classified situation (e.g. "travel_login_anomaly")
        outcome:        "correct" or "incorrect"

    Returns:
        The snapshot dict appended to TRUST_HISTORY.
    """
    if situation_type not in TRUST_SCORES:
        TRUST_SCORES[situation_type] = 0.5     # first encounter — start at neutral

    old_trust = TRUST_SCORES[situation_type]

    if outcome == "correct":
        delta = 0.03
        new_trust = min(old_trust + delta, 1.0)
    else:
        delta = -0.60
        new_trust = max(old_trust + delta, 0.0)

    new_trust = round(new_trust, 4)
    TRUST_SCORES[situation_type] = new_trust
    LOW_TRUST_FLAGS[situation_type] = new_trust < 0.3

    snap: Dict[str, Any] = {
        "decision_number": len(TRUST_HISTORY) + 1,
        "timestamp":       datetime.now(timezone.utc).isoformat(),
        "situation_type":  situation_type,
        "trust_score":     new_trust,
        "delta":           round(delta, 4),
        "outcome":         outcome,
    }
    TRUST_HISTORY.append(snap)

    print(
        f"[TRUST] {situation_type}: {old_trust:.3f} → {new_trust:.3f} "
        f"(delta={delta:+.2f}, outcome={outcome})"
    )
    if LOW_TRUST_FLAGS[situation_type]:
        print(f"[TRUST] ⚠ {situation_type} trust={new_trust:.2f} < 0.30 — human review required")

    return snap


def get_trust_status(situation_type: str) -> Dict[str, Any]:
    """
    Get trust status for a single situation type.

    Args:
        situation_type: Classified situation (e.g. "travel_login_anomaly")

    Returns:
        {
          "situation_type":        str,
          "trust_score":           float (0.0–1.0),
          "human_review_required": bool   (True when trust < 0.3)
        }
    """
    trust_score = TRUST_SCORES.get(situation_type, 0.5)
    return {
        "situation_type":        situation_type,
        "trust_score":           round(trust_score, 4),
        "human_review_required": trust_score < 0.3,
    }


def get_all_trust_scores() -> Dict[str, Any]:
    """
    Return all current trust scores and the full update history.
    Used by GET /api/evolution/trust-scores.

    Returns:
        {
          "trust_scores":        {situation_type: {trust_score, human_review_required}},
          "history":             [snapshots, oldest-first],
          "total_updates":       int,
          "low_trust_situations": [situation_types currently below 0.3]
        }
    """
    scores = {
        sit: {
            "trust_score":           round(score, 4),
            "human_review_required": score < 0.3,
        }
        for sit, score in TRUST_SCORES.items()
    }
    return {
        "trust_scores":         scores,
        "history":              list(TRUST_HISTORY),
        "total_updates":        len(TRUST_HISTORY),
        "low_trust_situations": [s for s, flag in LOW_TRUST_FLAGS.items() if flag],
    }


def seed_trust_history() -> None:
    """
    Pre-populate TRUST_HISTORY with 12 realistic historical snapshots for
    travel_login_anomaly, telling the asymmetry story from first load:

      Decisions 1–9  : correct  (+0.03 each) → trust rises 0.50 → 0.77
      Decision  10   : incorrect (−0.60)     → trust crashes   0.77 → 0.17
      Decisions 11–12: correct  (+0.03 each) → recovery starts 0.17 → 0.23

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
        ("correct",   0.77),   #  9  ← peak before the crash
        ("incorrect", 0.17),   # 10  ← one wrong answer wipes 9 correct ones
        ("correct",   0.20),   # 11  ← slow recovery
        ("correct",   0.23),   # 12  ← still in danger zone (< 0.3)
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
        f"[TRUST] Seeded {len(_ENTRIES)} historical trust snapshots for '{situation_type}' — "
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

    PATTERN_CONFIDENCE["PAT-TRAVEL-001"] = 0.94
    PATTERN_CONFIDENCE["PAT-PHISH-001"] = 0.89

    EDGE_WEIGHTS["User->TravelContext"] = 0.91
    EDGE_WEIGHTS["User->PhishingCampaign"] = 0.87

    PRECEDENT_COUNTS["PAT-TRAVEL-001"] = 127
    PRECEDENT_COUNTS["PAT-PHISH-001"] = 89

    print("[FEEDBACK] State reset to initial values")
