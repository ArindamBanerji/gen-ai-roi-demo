"""
tests/test_write_roundtrips.py -- Response-model and write-path roundtrip tests.

15 tests covering:
  - All 9 response_model endpoints return 200 (model mismatch -> 500)
  - ProfileScorer shape (6, 4, 6)
  - SCORER_ACTIONS has 4 items, no refer_to_analyst
  - Alert queue items use 'id' field
  - Campaign category_sequence is a list
  - Decision factors endpoint returns exactly 6 factors

Run from backend/:
    pytest tests/test_write_roundtrips.py -v
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# =============================================================================
# Response-model tests — each endpoint must return 200.
# A Pydantic validation failure causes FastAPI to return 500;
# these tests catch model/response mismatches early.
# =============================================================================

def test_response_model_alert_queue():
    r = client.get("/api/alerts/queue")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:300]}"
    body = r.json()
    assert "alerts" in body
    assert isinstance(body["alerts"], list)


def test_response_model_analytics():
    r = client.get("/api/soc/analytics")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:300]}"
    body = r.json()
    for key in ("total_alerts", "open_alerts", "total_decisions", "correct_decisions",
                "accuracy_pct", "category_breakdown", "source", "estimated_metrics"):
        assert key in body, f"Missing key: {key}"


def test_response_model_learning_state():
    r = client.get("/api/soc/learning-state")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:300]}"
    body = r.json()
    assert "frozen" in body
    assert "iks_v2" in body
    assert "iks_components" in body


def test_response_model_profile():
    r = client.get("/api/soc/profile")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:300]}"
    body = r.json()
    for key in ("categories", "actions", "centroids", "counts", "decision_count", "iks"):
        assert key in body, f"Missing key: {key}"


def test_response_model_detection_engineering():
    r = client.get("/api/soc/detection-engineering")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:300]}"
    body = r.json()
    assert "category_scores" in body
    assert "noise_map" in body
    assert isinstance(body["category_scores"], list)
    assert isinstance(body["noise_map"], list)


def test_response_model_campaigns():
    r = client.get("/api/soc/campaigns")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:300]}"
    body = r.json()
    assert "campaigns" in body
    assert "total" in body
    assert "active_campaigns" in body


def test_response_model_executive_narrative():
    r = client.get("/api/soc/executive-narrative")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:300]}"
    body = r.json()
    for key in ("headline", "what_changed", "what_discovered", "what_knows",
                "metrics", "generated_at", "pdf_available"):
        assert key in body, f"Missing key: {key}"


def test_response_model_decision_factors():
    r = client.get("/api/triage/decision-factors/SIM-CA-001")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:300]}"
    body = r.json()
    assert "alert_id" in body
    assert "factors" in body
    assert "recommended_action" in body
    assert "confidence" in body


def test_response_model_centroid_support():
    r = client.get("/api/soc/centroid-support")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:300]}"
    body = r.json()
    for key in ("support_summary", "overall_health", "warning_count",
                "threshold_sigma", "interpretation"):
        assert key in body, f"Missing key: {key}"


# =============================================================================
# Shape and invariant tests
# =============================================================================

def test_profile_scorer_shape_6_4_6():
    """ProfileScorer centroids must have shape (6, 4, 6) -- 6 categories, 4 actions, 6 factors."""
    r = client.get("/api/soc/profile")
    assert r.status_code == 200
    centroids = r.json()["centroids"]
    assert len(centroids) == 6, f"Expected 6 categories, got {len(centroids)}"
    for i, cat_row in enumerate(centroids):
        assert len(cat_row) == 4, f"Category {i}: expected 4 actions, got {len(cat_row)}"
        for j, action_row in enumerate(cat_row):
            assert len(action_row) == 6, (
                f"Category {i}, action {j}: expected 6 factors, got {len(action_row)}"
            )


def test_scorer_actions_has_4_items():
    """SCORER_ACTIONS must have exactly 4 items (escalate, investigate, suppress, monitor)."""
    from app.domains.soc.config import SCORER_ACTIONS
    assert len(SCORER_ACTIONS) == 4, (
        f"Expected 4 SCORER_ACTIONS, got {len(SCORER_ACTIONS)}: {SCORER_ACTIONS}"
    )


def test_scorer_actions_no_refer_to_analyst():
    """refer_to_analyst is a routing decision, not a ProfileScorer action."""
    from app.domains.soc.config import SCORER_ACTIONS
    assert "refer_to_analyst" not in SCORER_ACTIONS, (
        f"refer_to_analyst must not be in SCORER_ACTIONS: {SCORER_ACTIONS}"
    )


def test_alert_queue_items_use_id_field():
    """Alert queue items must have 'id' key (AGE uses alert_id; frontend expects 'id')."""
    r = client.get("/api/alerts/queue")
    assert r.status_code == 200
    alerts = r.json().get("alerts", [])
    if alerts:
        first = alerts[0]
        assert "id" in first, (
            f"Alert queue item missing 'id' field. Keys: {list(first.keys())}"
        )


def test_campaigns_category_sequence_is_list():
    """Campaign category_sequence must be a list, not a string or None."""
    r = client.get("/api/soc/campaigns")
    assert r.status_code == 200
    campaigns = r.json().get("campaigns", [])
    if campaigns:
        seq = campaigns[0].get("category_sequence")
        assert isinstance(seq, list), (
            f"category_sequence must be list, got {type(seq).__name__}: {seq!r}"
        )


def test_decision_factors_returns_6_factors():
    """GET /triage/decision-factors must return exactly 6 factors."""
    r = client.get("/api/triage/decision-factors/SIM-CA-001")
    assert r.status_code == 200
    factors = r.json().get("factors", [])
    assert len(factors) == 6, (
        f"Expected 6 decision factors, got {len(factors)}: "
        f"{[f['name'] for f in factors]}"
    )
