"""
Agent Evolver - Prompt Variant Performance Tracking
~80-100 lines. Tracks prompt variant performance across decisions.

The Agent Evolver demonstrates Loop 2: "Smarter ACROSS decisions"
by tracking which prompt variants perform best and promoting winners.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel


# ============================================================================
# In-Memory State (simulating persistent storage)
# ============================================================================

# Tracks performance of each prompt variant
PROMPT_STATS: Dict[str, Dict[str, Any]] = {
    "TRAVEL_CONTEXT_v1": {"success": 24, "total": 34, "success_rate": 0.71},
    "TRAVEL_CONTEXT_v2": {"success": 42, "total": 47, "success_rate": 0.89},
    "PHISHING_RESPONSE_v1": {"success": 31, "total": 38, "success_rate": 0.82},
    "PHISHING_RESPONSE_v2": {"success": 12, "total": 15, "success_rate": 0.80},
}

# Tracks which variant is currently active for each alert type
ACTIVE_PROMPTS: Dict[str, str] = {
    "anomalous_login": "TRAVEL_CONTEXT_v2",
    "phishing": "PHISHING_RESPONSE_v1",
}

# Tracks recent promotions for display
RECENT_PROMOTIONS: Dict[str, Dict[str, Any]] = {}

# F4a: Weight matrix evolution history — one snapshot appended per decision outcome
WEIGHT_HISTORY: List[Dict[str, Any]] = []


# ============================================================================
# Pydantic Models
# ============================================================================

class OperationalImpact(BaseModel):
    """Operational impact metrics from evolution"""
    fewer_false_escalations_pct: float
    fewer_false_escalations_monthly: int
    analyst_hours_recovered: float
    estimated_monthly_savings: float
    missed_threats: int


class PromptEvolution(BaseModel):
    """Evolution data for prompt variants"""
    current_variant: str
    current_success_rate: float
    previous_variant: Optional[str] = None
    previous_success_rate: Optional[float] = None
    promotion_occurred: bool = False
    promotion_reason: Optional[str] = None
    what_changed_narrative: Optional[str] = None
    operational_impact: Optional[OperationalImpact] = None


# ============================================================================
# Core Functions
# ============================================================================

def get_prompt_variant(alert_type: str) -> str:
    """
    Get the currently active prompt variant for an alert type.

    Args:
        alert_type: Type of alert (anomalous_login, phishing, etc.)

    Returns:
        Name of the active prompt variant
    """
    return ACTIVE_PROMPTS.get(alert_type, "DEFAULT_v1")


def get_prompt_stats() -> Dict[str, Dict[str, Any]]:
    """
    Get all prompt statistics for display.

    Returns:
        Dictionary of variant names to their stats
    """
    return PROMPT_STATS.copy()


def record_decision_outcome(
    decision_id: str,
    prompt_variant: str,
    success: bool,
    alert_type: str = "unknown",
) -> None:
    """
    Record the outcome of a decision using a specific prompt variant.
    Updates success count and total count, recalculates success rate.
    Appends a weight snapshot to WEIGHT_HISTORY (F4a).

    Args:
        decision_id:   ID of the decision
        prompt_variant: Name of the prompt variant used
        success:       Whether the decision was successful
        alert_type:    Alert type that triggered this decision (for history filtering)
    """
    if prompt_variant not in PROMPT_STATS:
        # Initialize new variant
        PROMPT_STATS[prompt_variant] = {
            "success": 0,
            "total": 0,
            "success_rate": 0.0
        }

    stats = PROMPT_STATS[prompt_variant]
    stats["total"] += 1

    if success:
        stats["success"] += 1

    # Recalculate success rate
    stats["success_rate"] = stats["success"] / stats["total"] if stats["total"] > 0 else 0.0

    # F4a: Snapshot the full weight matrix after each update
    WEIGHT_HISTORY.append({
        "decision_number": len(WEIGHT_HISTORY) + 1,
        "timestamp":       datetime.now(timezone.utc).isoformat(),
        "alert_type":      alert_type,
        "weights":         {name: s["success_rate"] for name, s in PROMPT_STATS.items()},
        "trigger":         prompt_variant,
        "outcome":         success,
    })

    print(f"[EVOLVER] Recorded outcome for {prompt_variant}: success={success}, "
          f"new stats={stats['success']}/{stats['total']} ({stats['success_rate']:.2%})")


def check_for_promotion(alert_type: str) -> Optional[Dict[str, Any]]:
    """
    Check if a better prompt variant should be promoted.
    Compares active variant with other variants of the same family.

    Args:
        alert_type: Type of alert to check

    Returns:
        Promotion info dict if promotion occurred, None otherwise
    """
    current_variant = ACTIVE_PROMPTS.get(alert_type)
    if not current_variant:
        return None

    # Get family prefix (e.g., "TRAVEL_CONTEXT" from "TRAVEL_CONTEXT_v2")
    family_prefix = "_".join(current_variant.split("_")[:-1])

    # Find all variants in the same family
    family_variants = [
        (name, stats) for name, stats in PROMPT_STATS.items()
        if name.startswith(family_prefix) and name != current_variant
    ]

    if not family_variants:
        return None

    current_stats = PROMPT_STATS.get(current_variant, {})
    current_rate = current_stats.get("success_rate", 0.0)

    # Check if any variant has >5% better success rate
    for variant_name, variant_stats in family_variants:
        variant_rate = variant_stats.get("success_rate", 0.0)

        # Require at least 10 samples for promotion
        if variant_stats.get("total", 0) < 10:
            continue

        improvement = variant_rate - current_rate

        if improvement > 0.05:  # >5% improvement
            # Promote the better variant
            old_variant = current_variant
            old_rate = current_rate
            new_variant = variant_name
            new_rate = variant_rate

            ACTIVE_PROMPTS[alert_type] = new_variant

            promotion_info = {
                "promoted": True,
                "old_variant": old_variant,
                "new_variant": new_variant,
                "old_rate": old_rate,
                "new_rate": new_rate,
                "reason": f"Variant {new_variant} outperformed {old_variant} by {improvement:.1%} ({new_rate:.1%} vs {old_rate:.1%})"
            }

            # Store for display
            RECENT_PROMOTIONS[alert_type] = promotion_info

            print(f"[EVOLVER] PROMOTION: {alert_type} promoted from {old_variant} to {new_variant}")

            return promotion_info

    return None


def generate_what_changed_narrative(alert_type: str, old_rate: float, new_rate: float) -> str:
    """
    Generate plain English explanation of what changed.

    Args:
        alert_type: Type of alert
        old_rate: Previous success rate
        new_rate: New success rate

    Returns:
        Human-readable narrative
    """
    if alert_type == "anomalous_login":
        false_escalation_pct = int((1 - old_rate) * 100)
        return (
            "Agent learned that VPN location + travel record together indicate safe access. "
            f"Previously escalated {false_escalation_pct}% of travel alerts to Tier 2 unnecessarily."
        )
    elif alert_type == "phishing":
        return (
            "Agent improved campaign signature matching. "
            "Faster identification of known phishing patterns reduces exposure window."
        )
    else:
        return "Agent behavior improved through accumulated decision outcomes."


def calculate_operational_impact(old_rate: float, new_rate: float) -> OperationalImpact:
    """
    Calculate operational impact from success rate improvement.

    Args:
        old_rate: Previous success rate
        new_rate: New success rate

    Returns:
        OperationalImpact with computed metrics
    """
    # Difference in success rate (percentage points)
    improvement_pct = (new_rate - old_rate) * 100.0

    # Assume ~200 similar alerts per month
    monthly_alerts = 200

    # Fewer false escalations per month
    fewer_escalations = int(monthly_alerts * (new_rate - old_rate))

    # Each escalation costs ~45 minutes of analyst time
    analyst_minutes_per_review = 45.0
    analyst_hours_recovered = (fewer_escalations * analyst_minutes_per_review) / 60.0

    # Each analyst review costs ~$127
    cost_per_review = 127.0
    monthly_savings = fewer_escalations * cost_per_review

    return OperationalImpact(
        fewer_false_escalations_pct=round(improvement_pct, 1),
        fewer_false_escalations_monthly=fewer_escalations,
        analyst_hours_recovered=round(analyst_hours_recovered, 1),
        estimated_monthly_savings=round(monthly_savings, 2),
        missed_threats=0  # Always 0 - eval gates prevent unsafe actions
    )


def get_evolution_summary(alert_type: str) -> PromptEvolution:
    """
    Get evolution summary for display in the UI.

    Args:
        alert_type: Type of alert

    Returns:
        PromptEvolution with current state and any recent promotion
    """
    current_variant = get_prompt_variant(alert_type)
    current_stats = PROMPT_STATS.get(current_variant, {})
    current_rate = current_stats.get("success_rate", 0.0)

    # Check if there was a recent promotion
    promotion = RECENT_PROMOTIONS.get(alert_type)

    if promotion:
        old_rate = promotion["old_rate"]
        new_rate = promotion["new_rate"]

        # Generate narrative and impact
        narrative = generate_what_changed_narrative(alert_type, old_rate, new_rate)
        impact = calculate_operational_impact(old_rate, new_rate)

        return PromptEvolution(
            current_variant=promotion["new_variant"],
            current_success_rate=promotion["new_rate"],
            previous_variant=promotion["old_variant"],
            previous_success_rate=promotion["old_rate"],
            promotion_occurred=True,
            promotion_reason=promotion["reason"],
            what_changed_narrative=narrative,
            operational_impact=impact
        )

    # No recent promotion - use implicit baseline comparison
    # Determine implicit previous variant based on alert type
    previous_variant = None
    previous_rate = None

    if alert_type == "anomalous_login":
        # Use v1 as implicit baseline for v2
        if current_variant == "TRAVEL_CONTEXT_v2":
            previous_variant = "TRAVEL_CONTEXT_v1"
            previous_stats = PROMPT_STATS.get(previous_variant, {})
            previous_rate = previous_stats.get("success_rate", 0.71)
    elif alert_type == "phishing":
        # Use v1 as implicit baseline
        if current_variant == "PHISHING_RESPONSE_v1":
            # No previous for v1, use a hardcoded baseline
            previous_rate = 0.70  # Assume pre-evolution baseline
        elif current_variant == "PHISHING_RESPONSE_v2":
            previous_variant = "PHISHING_RESPONSE_v1"
            previous_stats = PROMPT_STATS.get(previous_variant, {})
            previous_rate = previous_stats.get("success_rate", 0.82)

    # Generate narrative and impact if we have a baseline
    narrative = None
    impact = None

    if previous_rate is not None:
        narrative = generate_what_changed_narrative(alert_type, previous_rate, current_rate)
        impact = calculate_operational_impact(previous_rate, current_rate)

    return PromptEvolution(
        current_variant=current_variant,
        current_success_rate=current_rate,
        previous_variant=previous_variant,
        previous_success_rate=previous_rate,
        promotion_occurred=False,
        promotion_reason=None,
        what_changed_narrative=narrative,
        operational_impact=impact
    )


def get_variant_comparison(alert_type: str) -> Dict[str, Any]:
    """
    Get comparison data between active and alternative variants.
    Used for visualization in the UI.

    Args:
        alert_type: Type of alert

    Returns:
        Dictionary with variant comparison data
    """
    current_variant = get_prompt_variant(alert_type)
    family_prefix = "_".join(current_variant.split("_")[:-1])

    # Get all variants in family
    variants = []
    for name, stats in PROMPT_STATS.items():
        if name.startswith(family_prefix):
            variants.append({
                "name": name,
                "success_rate": stats.get("success_rate", 0.0),
                "total": stats.get("total", 0),
                "is_active": name == current_variant
            })

    # Sort by success rate descending
    variants.sort(key=lambda x: x["success_rate"], reverse=True)

    return {
        "alert_type": alert_type,
        "family": family_prefix,
        "variants": variants,
        "active_variant": current_variant
    }


def reset_evolver_state() -> None:
    """
    Reset all evolver state to initial seed values (demo reset — fixes L-14).

    PROMPT_STATS and ACTIVE_PROMPTS are restored to their startup defaults
    (not just cleared) because the UI depends on pre-seeded variant data.
    RECENT_PROMOTIONS is cleared because it accumulates during a session.
    """
    PROMPT_STATS.clear()
    PROMPT_STATS.update({
        "TRAVEL_CONTEXT_v1":    {"success": 24, "total": 34, "success_rate": 0.71},
        "TRAVEL_CONTEXT_v2":    {"success": 42, "total": 47, "success_rate": 0.89},
        "PHISHING_RESPONSE_v1": {"success": 31, "total": 38, "success_rate": 0.82},
        "PHISHING_RESPONSE_v2": {"success": 12, "total": 15, "success_rate": 0.80},
    })

    ACTIVE_PROMPTS.clear()
    ACTIVE_PROMPTS.update({
        "anomalous_login": "TRAVEL_CONTEXT_v2",
        "phishing":        "PHISHING_RESPONSE_v1",
    })

    RECENT_PROMOTIONS.clear()
    WEIGHT_HISTORY.clear()
    seed_weight_history()

    print("[EVOLVER] State reset to initial values")


def get_weight_history(alert_type_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Return the in-memory weight matrix evolution history (F4a).

    Args:
        alert_type_filter: If provided, return only snapshots for this alert type.

    Returns:
        List of snapshot dicts, oldest-first.  Each snapshot:
          decision_number  — 1-based counter across all decisions this session
          timestamp        — ISO-8601 UTC string
          alert_type       — alert type that triggered the update
          weights          — {variant_name: success_rate} for all tracked variants
          trigger          — prompt variant name whose stats were just updated
          outcome          — True if the decision was successful (gates passed)
    """
    if alert_type_filter:
        return [s for s in WEIGHT_HISTORY if s["alert_type"] == alert_type_filter]
    return list(WEIGHT_HISTORY)


# ============================================================================
# F4c-FIX: Seed weight history for compelling demo charts
# ============================================================================

def seed_weight_history() -> None:
    """
    Pre-populate WEIGHT_HISTORY with 15 realistic historical snapshots.
    Shows TRAVEL_CONTEXT_v2 rising from 0.65 → 0.90 (the winner trajectory),
    TRAVEL_CONTEXT_v1 flat ~0.70, and phishing variants improving steadily.
    Called at end of reset_evolver_state() and on module import so Tab 4
    charts are always populated without requiring live interaction.
    Live decisions append to this baseline (decision_number continues from 16+).
    """
    _SEED_DATA = [
        # (decision, alert_type, trigger, outcome, TC_v1, TC_v2, PR_v1, PR_v2)
        ( 1, "anomalous_login", "TRAVEL_CONTEXT_v2",    True,  0.70, 0.65, 0.72, 0.68),
        ( 2, "anomalous_login", "TRAVEL_CONTEXT_v2",    True,  0.70, 0.67, 0.72, 0.69),
        ( 3, "anomalous_login", "TRAVEL_CONTEXT_v2",    True,  0.70, 0.70, 0.73, 0.70),
        ( 4, "phishing",        "PHISHING_RESPONSE_v1", True,  0.70, 0.73, 0.74, 0.71),
        ( 5, "anomalous_login", "TRAVEL_CONTEXT_v2",    True,  0.70, 0.75, 0.75, 0.72),
        ( 6, "phishing",        "PHISHING_RESPONSE_v1", True,  0.71, 0.77, 0.76, 0.73),
        ( 7, "anomalous_login", "TRAVEL_CONTEXT_v2",    True,  0.71, 0.79, 0.77, 0.74),
        ( 8, "phishing",        "PHISHING_RESPONSE_v1", False, 0.71, 0.81, 0.78, 0.75),
        ( 9, "anomalous_login", "TRAVEL_CONTEXT_v2",    True,  0.71, 0.83, 0.79, 0.76),
        (10, "phishing",        "PHISHING_RESPONSE_v2", True,  0.71, 0.84, 0.80, 0.77),
        (11, "anomalous_login", "TRAVEL_CONTEXT_v2",    True,  0.71, 0.86, 0.81, 0.78),
        (12, "anomalous_login", "TRAVEL_CONTEXT_v1",    False, 0.71, 0.87, 0.82, 0.79),
        (13, "phishing",        "PHISHING_RESPONSE_v1", True,  0.71, 0.88, 0.83, 0.80),
        (14, "anomalous_login", "TRAVEL_CONTEXT_v2",    True,  0.71, 0.89, 0.84, 0.81),
        (15, "phishing",        "PHISHING_RESPONSE_v2", True,  0.71, 0.90, 0.84, 0.82),
    ]

    base_ts = datetime.now(timezone.utc) - timedelta(hours=15)
    for dec, alert_type, trigger, outcome, tc1, tc2, pr1, pr2 in _SEED_DATA:
        ts = base_ts + timedelta(hours=dec)
        WEIGHT_HISTORY.append({
            "decision_number": dec,
            "timestamp":       ts.isoformat(),
            "alert_type":      alert_type,
            "weights": {
                "TRAVEL_CONTEXT_v1":    tc1,
                "TRAVEL_CONTEXT_v2":    tc2,
                "PHISHING_RESPONSE_v1": pr1,
                "PHISHING_RESPONSE_v2": pr2,
            },
            "trigger":  trigger,
            "outcome":  outcome,
        })
    print(f"[EVOLVER] Seeded {len(_SEED_DATA)} historical weight snapshots")


# Seed on module import so Tab 4 charts are pre-populated at startup
seed_weight_history()
