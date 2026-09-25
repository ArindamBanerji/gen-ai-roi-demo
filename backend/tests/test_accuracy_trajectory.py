"""
tests/test_accuracy_trajectory.py -- accuracy-trajectory endpoint (C1b).

4 tests validating GET /api/soc/accuracy-trajectory.

Run from backend/:
    pytest tests/test_accuracy_trajectory.py -v
"""

import sys
import os
from unittest.mock import patch, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from fastapi.testclient import TestClient

from app.services.gae_state import init_learning_state
init_learning_state()

from app.main import app

client = TestClient(app)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_trajectory(age_graph):
    """Read the disposable graph through the production endpoint."""
    with patch("app.routers.soc.graph_client", age_graph.client), patch.object(app.state, "graph_store", age_graph.store, create=True):
        return client.get("/api/soc/accuracy-trajectory")


# ============================================================================
# Test 1 — cold-start (no decisions) returns valid structure
# ============================================================================

@pytest.mark.age
def test_accuracy_trajectory_cold_start_structure(age_graph):
    """
    With no decisions in AGE the endpoint must still return a valid response
    with all required top-level keys and at least one category entry.
    """
    response = _get_trajectory(age_graph)

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:300]}"
    )
    body = response.json()

    for key in ("categories", "enriched_plateau", "decisions_per_day", "source"):
        assert key in body, f"Response missing top-level key '{key}': {list(body.keys())}"

    assert isinstance(body["categories"], list), "categories must be a list"
    assert len(body["categories"]) >= 1, "categories must have at least one entry"
    assert body["source"] == "cold_start", (
        f"Expected source='cold_start' when no decisions, got {body['source']!r}"
    )


# ============================================================================
# Test 2 — live decision count flows through to category entry
# ============================================================================

@pytest.mark.age
def test_accuracy_trajectory_live_data_reflected(age_graph):
    """
    When AGE returns a category with N decisions, the response must reflect
    that count in the matching category entry.
    """
    for _ in range(5):
        age_graph.decision(category="phishing")
    age_graph.decision(category="phishing", domain="s2p")
    response = _get_trajectory(age_graph)

    assert response.status_code == 200
    body = response.json()

    assert body["source"] == "live", (
        f"Expected source='live' with live data, got {body['source']!r}"
    )

    phishing = next(
        (c for c in body["categories"] if c["category"] == "phishing"), None
    )
    assert phishing is not None, (
        f"Category 'phishing' not found in response: {[c['category'] for c in body['categories']]}"
    )
    assert phishing["decision_count"] == 5, (
        f"Expected decision_count=5, got {phishing['decision_count']}"
    )


# ============================================================================
# Test 3 — current_accuracy in [0, enriched_plateau] for any decision count
# ============================================================================

def test_accuracy_trajectory_accuracy_in_valid_range():
    """
    current_accuracy must be in [0.0, enriched_plateau] for any decision count.
    Test three representative counts: 0, 500, 3000+.
    """
    from app.services.accuracy_trajectory import build_trajectory_for_category
    from app.domains.soc.constants import ENRICHED_PLATEAU

    for count in [0, 500, 5000]:
        result = build_trajectory_for_category("test", count)
        acc = result["current_accuracy"]
        assert 0.0 <= acc <= ENRICHED_PLATEAU, (
            f"current_accuracy={acc} out of [0, {ENRICHED_PLATEAU}] at count={count}"
        )


# ============================================================================
# Test 4 — trajectory_points are present and monotonically increasing
# ============================================================================

@pytest.mark.age
def test_accuracy_trajectory_points_monotone(age_graph):
    """
    trajectory_points in each category entry must be a non-empty list of
    {decisions, accuracy} dicts, with accuracy strictly increasing.
    """
    for _ in range(2):
        age_graph.decision(category="malware")
    response = _get_trajectory(age_graph)

    assert response.status_code == 200
    body = response.json()

    malware = next(
        (c for c in body["categories"] if c["category"] == "malware"), None
    )
    assert malware is not None

    points = malware["trajectory_points"]
    assert isinstance(points, list) and len(points) > 0, (
        "trajectory_points must be a non-empty list"
    )

    accuracies = [p["accuracy"] for p in points]
    assert all(
        accuracies[i] < accuracies[i + 1] for i in range(len(accuracies) - 1)
    ), f"trajectory_points not monotonically increasing: {accuracies}"
