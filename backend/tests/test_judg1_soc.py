"""
JUDG-1-SOC: Institutional judgment display tests.

Verifies that the judgment router is registered and that
build_judgment_response() returns the correct shape and values
when called against the SOC baseline centroids.

No AGE required -- all tests use the pure build_judgment_response helper.

Run from backend/:
    pytest tests/test_judg1_soc.py -v
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# SOC_FACTORS is defined in judgment.py (not in config.py)
from app.routers.judgment import build_judgment_response, SOC_FACTORS, SOC_ACTIONS
from app.domains.soc.config import SCORER_ACTIONS  # A=4; excludes refer_to_analyst


# ============================================================================
# TEST 1 — POST /api/soc/judgment/explain route registered
# ============================================================================

def test_judgment_explain_post_endpoint_registered():
    """POST /api/soc/judgment/explain must be registered on the FastAPI app."""
    from app.main import app
    routes = [r.path for r in app.routes]
    assert "/api/soc/judgment/explain" in routes, (
        f"Route not found. Registered routes: {routes}"
    )


# ============================================================================
# TEST 2 — GET /api/soc/judgment/explain/{alert_id} route registered
# ============================================================================

def test_judgment_explain_get_endpoint_registered():
    """GET /api/soc/judgment/explain/{alert_id} must be registered."""
    from app.main import app
    routes = [r.path for r in app.routes]
    assert "/api/soc/judgment/explain/{alert_id}" in routes, (
        f"Route not found. Registered routes: {routes}"
    )


# ============================================================================
# TEST 3 — Response has all required fields
# ============================================================================

def test_judgment_response_shape():
    """POST /explain with valid inputs returns correct shape."""
    from app.domains.soc.config import SOC_PROFILE_CENTROIDS
    from gae import ProfileScorer
    import numpy as np

    scorer = ProfileScorer(
        mu=np.array(SOC_PROFILE_CENTROIDS),
        actions=SCORER_ACTIONS,
    )
    factors = {
        # Uses legacy alias; canonical key is privileged_identity_context.
        "travel_match": 0.9, "asset_criticality": 0.8,
        "threat_intel_enrichment": 0.7, "pattern_history": 0.6,
        "time_anomaly": 0.5, "device_trust": 0.3,
    }
    response = build_judgment_response(
        category="credential_access",
        factors=factors,
        scorer=scorer,
        alert_id="TEST-001",
    )
    required = {
        "action", "confidence", "confidence_tier",
        "dominant_factors", "rationale", "action_scores",
        "auto_approvable", "factor_contributions",
    }
    assert required.issubset(response.keys()), (
        f"Missing fields: {required - set(response.keys())}"
    )


# ============================================================================
# TEST 4 — action is a valid SOC action
# ============================================================================

def test_judgment_action_is_valid_soc_action():
    """build_judgment_response must return a valid SOC action name."""
    from app.domains.soc.config import SOC_PROFILE_CENTROIDS
    from gae import ProfileScorer
    import numpy as np

    scorer = ProfileScorer(
        mu=np.array(SOC_PROFILE_CENTROIDS),
        actions=SCORER_ACTIONS,
    )
    factors = {f: 0.5 for f in SOC_FACTORS}
    response = build_judgment_response(
        category="lateral_movement", factors=factors, scorer=scorer
    )
    assert response["action"] in SOC_ACTIONS, (
        f"action {response['action']!r} not in SOC_ACTIONS {SOC_ACTIONS}"
    )


# ============================================================================
# TEST 5 — confidence in [0.0, 1.0]
# ============================================================================

def test_judgment_confidence_in_range():
    """confidence must be in [0.0, 1.0] for any valid input."""
    from app.domains.soc.config import SOC_PROFILE_CENTROIDS
    from gae import ProfileScorer
    import numpy as np

    scorer = ProfileScorer(
        mu=np.array(SOC_PROFILE_CENTROIDS),
        actions=SCORER_ACTIONS,
    )
    factors = {f: 0.5 for f in SOC_FACTORS}
    response = build_judgment_response(
        category="insider_threat", factors=factors, scorer=scorer
    )
    assert 0.0 <= response["confidence"] <= 1.0, (
        f"confidence {response['confidence']} out of [0.0, 1.0]"
    )


# ============================================================================
# TEST 6 — dominant_factors are valid SOC factor names
# ============================================================================

def test_judgment_dominant_factors_are_soc_factors():
    """Every entry in dominant_factors must be a known SOC factor name."""
    from app.domains.soc.config import SOC_PROFILE_CENTROIDS
    from gae import ProfileScorer
    import numpy as np

    scorer = ProfileScorer(
        mu=np.array(SOC_PROFILE_CENTROIDS),
        actions=SCORER_ACTIONS,
    )
    factors = {f: 0.5 for f in SOC_FACTORS}
    response = build_judgment_response(
        category="data_exfiltration", factors=factors, scorer=scorer
    )
    for df in response["dominant_factors"]:
        assert df in SOC_FACTORS, (
            f"dominant factor {df!r} not in SOC_FACTORS {SOC_FACTORS}"
        )


# ============================================================================
# TEST 7 — rationale string mentions the recommended action
# ============================================================================

def test_judgment_rationale_mentions_action():
    """rationale must contain the recommended action name as a substring."""
    from app.domains.soc.config import SOC_PROFILE_CENTROIDS
    from gae import ProfileScorer
    import numpy as np

    scorer = ProfileScorer(
        mu=np.array(SOC_PROFILE_CENTROIDS),
        actions=SCORER_ACTIONS,
    )
    factors = {f: 0.5 for f in SOC_FACTORS}
    response = build_judgment_response(
        category="insider_threat", factors=factors, scorer=scorer
    )
    assert response["action"] in response["rationale"], (
        f"action {response['action']!r} not found in rationale: "
        f"{response['rationale']!r}"
    )


# ============================================================================
# TEST 8 — action_scores contains all 4 SOC actions
# ============================================================================

def test_judgment_all_action_scores_present():
    """action_scores must contain an entry for every SOC action."""
    from app.domains.soc.config import SOC_PROFILE_CENTROIDS
    from gae import ProfileScorer
    import numpy as np

    scorer = ProfileScorer(
        mu=np.array(SOC_PROFILE_CENTROIDS),
        actions=SCORER_ACTIONS,
    )
    factors = {f: 0.5 for f in SOC_FACTORS}
    response = build_judgment_response(
        category="cloud_infrastructure", factors=factors, scorer=scorer
    )
    for action in SCORER_ACTIONS:
        assert action in response["action_scores"], (
            f"action {action!r} missing from action_scores. "
            f"Present: {list(response['action_scores'].keys())}"
        )
