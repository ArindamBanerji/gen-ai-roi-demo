"""Referral policy for refer_to_analyst action (v5.5).

refer_to_analyst is not a pure centroid action. It requires:
1. Centroid proximity (geometric region)
2. Confidence band (medium range)
3. Margin gate (top-2 actions are close)
4. Category-specific red-flag overrides

Design: LLM judge consensus (3-model review, March 2026).
Rationale: Centroids alone capture 28-36% of factor space volume.
With activation policy, effective capture is ~16-22%.

If the centroid winner is refer_to_analyst but policy blocks it,
the caller should fall back to the second-best action via get_fallback_action().
"""

import numpy as np
from typing import Optional

# Action index for refer_to_analyst in SOC_ACTIONS
REFER_ACTION_INDEX = 4

# Confidence band: only refer when top probability is in this range.
# Below CONFIDENCE_BAND_LOW → too uncertain, keep routing to escalate/investigate.
# Above CONFIDENCE_BAND_HIGH → system is confident enough, trust the centroid winner.
CONFIDENCE_BAND_LOW  = 0.30
CONFIDENCE_BAND_HIGH = 0.70

# Margin gate: top-2 action probabilities must be within this margin.
# If a clear winner exists (margin > threshold), don't second-guess with a referral.
MARGIN_THRESHOLD = 0.20

# Category-specific factor thresholds that override refer → investigate/escalate.
# These represent "red flag" combinations where referral is too risky.
# Factor indices: 1=asset_criticality, 2=threat_intel_enrichment,
#                 3=pattern_history, 4=time_anomaly
CATEGORY_OVERRIDES = {
    "threat_intel_match": {
        "condition": "threat_intel_enrichment > threshold",
        "factor_index": 2,
        "threshold": 0.50,
        "override_reason": "Strong IOC signal — investigate, never refer",
    },
    "data_exfiltration": {
        "condition": "asset_criticality > t1 AND time_anomaly > t2",
        "factor_indices": [1, 4],
        "thresholds": [0.70, 0.60],
        "logic": "AND",
        "override_reason": "High-value asset + timing anomaly — investigate/escalate",
    },
    "insider_threat": {
        "condition": "pattern_history > t1 AND time_anomaly > t2",
        "factor_indices": [3, 4],
        "thresholds": [0.70, 0.70],
        "logic": "AND",
        "override_reason": "Strong behavioral deviation + timing — investigate/escalate",
    },
}


def should_refer_to_analyst(
    probabilities: np.ndarray,
    confidence: float,
    action_index: int,
    category: str,
    factors: np.ndarray,
) -> bool:
    """Determine if refer_to_analyst should activate.

    Returns True only if ALL conditions are met:
    1. refer_to_analyst is geometrically competitive (top-1 or close top-2)
    2. Confidence is in the medium band [0.30, 0.70)
    3. Top-2 margin is small (no clear winner exists)
    4. No category-specific red-flag override fires

    If False and the centroid winner was refer_to_analyst, the caller should
    fall back to the second-best action via get_fallback_action().

    Parameters
    ----------
    probabilities : np.ndarray shape (5,)
        Softmax probabilities from ProfileScorer.score().
    confidence : float
        Confidence value from ProfileScorer.score().
    action_index : int
        Winning action index from ProfileScorer.score().
    category : str
        Alert category string (e.g. "credential_access").
    factors : np.ndarray shape (6,)
        Factor vector for the alert.
    """
    # Condition 1: refer must be top-1 or be a competitive top-2 contender
    refer_prob = probabilities[REFER_ACTION_INDEX]
    if action_index != REFER_ACTION_INDEX and refer_prob < 0.15:
        return False

    # Condition 2: confidence band check
    if confidence >= CONFIDENCE_BAND_HIGH or confidence < CONFIDENCE_BAND_LOW:
        return False

    # Condition 3: margin gate — top-2 probabilities must be close
    sorted_probs = np.sort(probabilities)[::-1]
    margin = float(sorted_probs[0] - sorted_probs[1])
    if margin > MARGIN_THRESHOLD:
        return False

    # Condition 4: category-specific red-flag overrides
    if category in CATEGORY_OVERRIDES:
        override = CATEGORY_OVERRIDES[category]
        if "factor_index" in override:
            # Single factor threshold
            if float(factors[override["factor_index"]]) > override["threshold"]:
                return False
        elif "factor_indices" in override:
            # Multi-factor AND/OR logic
            checks = [
                float(factors[idx]) > thresh
                for idx, thresh in zip(override["factor_indices"], override["thresholds"])
            ]
            if override["logic"] == "AND" and all(checks):
                return False
            elif override["logic"] == "OR" and any(checks):
                return False

    return True


def get_fallback_action(probabilities: np.ndarray) -> int:
    """When refer_to_analyst wins geometrically but policy blocks it,
    return the second-best action index (excluding refer_to_analyst).

    Parameters
    ----------
    probabilities : np.ndarray shape (5,)
        Softmax probabilities from ProfileScorer.score().

    Returns
    -------
    int
        Action index of the highest-probability non-refer action.
    """
    masked = probabilities.copy().astype(float)
    masked[REFER_ACTION_INDEX] = -1.0
    return int(np.argmax(masked))
