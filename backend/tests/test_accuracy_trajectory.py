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

def _get_trajectory(neo4j_rows=None):
    """Call GET /api/soc/accuracy-trajectory with optional Neo4j mock rows."""
    if neo4j_rows is None:
        neo4j_rows = []
    with patch(
        "app.routers.soc.graph_client.run_query",
        new_callable=AsyncMock,
        return_value=neo4j_rows,
    ):
        response = client.get("/api/soc/accuracy-trajectory")
    return response


# ============================================================================
# Test 1 — cold-start (no decisions) returns valid structure
# ============================================================================

def test_accuracy_trajectory_cold_start_structure():
    """
    With no decisions in Neo4j the endpoint must still return a valid response
    with all required top-level keys and at least one category entry.
    """
    response = _get_trajectory(neo4j_rows=[])

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

def test_accuracy_trajectory_live_data_reflected():
    """
    When Neo4j returns a category with N decisions, the response must reflect
    that count in the matching category entry.
    """
    rows = [{"category": "phishing", "cnt": 500}]
    response = _get_trajectory(neo4j_rows=rows)

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
    assert phishing["decision_count"] == 500, (
        f"Expected decision_count=500, got {phishing['decision_count']}"
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

def test_accuracy_trajectory_points_monotone():
    """
    trajectory_points in each category entry must be a non-empty list of
    {decisions, accuracy} dicts, with accuracy strictly increasing.
    """
    rows = [{"category": "malware", "cnt": 200}]
    response = _get_trajectory(neo4j_rows=rows)

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
