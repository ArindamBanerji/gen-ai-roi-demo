"""
Tests for IKS v2 (§Phase-3).

Coverage:
  test_compute_iks_v2_cold_start            — 0 decisions → low score + cold-start interpretation
  test_compute_iks_v2_components_bounded    — all components in [0, 100]
  test_compute_iks_v2_grows_with_decisions  — higher decision count → higher score
  test_interpret_iks_v2_ranges             — correct interpretation string at each band
  test_iks_trend_endpoint                  — GET /api/soc/iks-trend valid structure
  test_learning_state_includes_iks_v2      — GET /api/soc/learning-state includes iks_v2
"""

import asyncio
import pytest
from unittest.mock import patch, AsyncMock

from app.services.iks import compute_iks_v2, interpret_iks_v2


# ---------------------------------------------------------------------------
# FakeNeo4j helpers
# ---------------------------------------------------------------------------

def _make_neo4j(total: int, cat_counts: dict, high_conf: int, accuracies: list):
    """Return a FakeNeo4j whose run_query answers the 4 IKS v2 queries."""

    async def run_query(query, params=None):
        q = query.strip()
        if "RETURN count(d) AS total" in q:
            return [{"total": total}]
        if "RETURN d.category AS category, count(d) AS n" in q:
            return [{"category": c, "n": n} for c, n in cat_counts.items()]
        if "d.confidence >= 0.70" in q:
            return [{"high_conf": high_conf}]
        if "d.outcome IS NOT NULL" in q:
            return [{"category": c, "accuracy": acc}
                    for c, acc in zip(cat_counts.keys(), accuracies)]
        return []

    class FakeNeo4j:
        pass

    FakeNeo4j.run_query = staticmethod(run_query)
    return FakeNeo4j()


# ---------------------------------------------------------------------------
# Test 1: cold start (0 decisions)
# ---------------------------------------------------------------------------

def test_compute_iks_v2_cold_start():
    """IKS v2 at cold start (0 decisions) returns low score + cold-start interpretation."""
    fake = _make_neo4j(total=0, cat_counts={}, high_conf=0, accuracies=[])
    result = asyncio.run(compute_iks_v2(fake))

    assert result["iks_v2"] < 30, (
        f"Cold-start IKS v2 should be < 30, got {result['iks_v2']}"
    )
    assert "Cold start" in result["interpretation"], (
        f"Expected 'Cold start' in interpretation, got: {result['interpretation']!r}"
    )
    assert result["total_decisions"] == 0
    assert result["categories_active"] == 0


# ---------------------------------------------------------------------------
# Test 2: all components bounded in [0, 100]
# ---------------------------------------------------------------------------

def test_compute_iks_v2_components_bounded():
    """All IKS v2 components are in [0, 100] and iks_v2 itself is in [0, 100]."""
    fake = _make_neo4j(
        total=50,
        cat_counts={"credential_access": 20, "lateral_movement": 15, "insider_threat": 15},
        high_conf=35,
        accuracies=[0.90, 0.85, 0.80],
    )
    result = asyncio.run(compute_iks_v2(fake))

    assert 0.0 <= result["iks_v2"] <= 100.0, f"iks_v2={result['iks_v2']} out of [0, 100]"
    for name, val in result["components"].items():
        assert 0.0 <= val <= 100.0, f"component {name}={val} out of [0, 100]"


# ---------------------------------------------------------------------------
# Test 3: score grows with decisions
# ---------------------------------------------------------------------------

def test_compute_iks_v2_grows_with_decisions():
    """IKS v2 increases when total_decisions is higher."""
    fake_low = _make_neo4j(
        total=10,
        cat_counts={"credential_access": 10},
        high_conf=7,
        accuracies=[0.70],
    )
    fake_high = _make_neo4j(
        total=200,
        cat_counts={
            "credential_access": 50, "lateral_movement": 40,
            "data_exfiltration": 35, "insider_threat": 30,
            "threat_intel_match": 25, "cloud_infrastructure": 20,
        },
        high_conf=160,
        accuracies=[0.90, 0.88, 0.85, 0.87, 0.92, 0.83],
    )
    score_low  = asyncio.run(compute_iks_v2(fake_low))["iks_v2"]
    score_high = asyncio.run(compute_iks_v2(fake_high))["iks_v2"]

    assert score_high > score_low, (
        f"Expected score to grow with decisions: low={score_low}, high={score_high}"
    )


# ---------------------------------------------------------------------------
# Test 4: interpret_iks_v2 bands
# ---------------------------------------------------------------------------

def test_interpret_iks_v2_ranges():
    """Interpretation strings match the correct score ranges."""
    assert "Cold start"  in interpret_iks_v2(5),  f"Got: {interpret_iks_v2(5)!r}"
    assert "Early"       in interpret_iks_v2(20), f"Got: {interpret_iks_v2(20)!r}"
    assert "Developing"  in interpret_iks_v2(45), f"Got: {interpret_iks_v2(45)!r}"
    assert "Mature"      in interpret_iks_v2(70), f"Got: {interpret_iks_v2(70)!r}"
    assert "Expert"      in interpret_iks_v2(90), f"Got: {interpret_iks_v2(90)!r}"


# ---------------------------------------------------------------------------
# Test 5: GET /api/soc/iks-trend — valid structure
# ---------------------------------------------------------------------------

def test_iks_trend_endpoint():
    """GET /api/soc/iks-trend returns valid structure with trend and current keys."""
    from fastapi.testclient import TestClient
    from app.main import app

    async def _fake_run_query(query, params=None):
        q = query.strip()
        if "RETURN count(d) AS total" in q:
            return [{"total": 50}]
        if "RETURN d.category AS category, count(d) AS n" in q:
            return [{"category": "credential_access", "n": 50}]
        if "d.confidence >= 0.70" in q:
            return [{"high_conf": 40}]
        if "d.outcome IS NOT NULL" in q:
            return [{"category": "credential_access", "accuracy": 0.88}]
        return []

    with patch("app.routers.soc.neo4j_client") as mock_neo4j:
        mock_neo4j.run_query = _fake_run_query
        client = TestClient(app)
        response = client.get("/api/soc/iks-trend")

    assert response.status_code == 200, f"Status: {response.status_code}, body: {response.text}"
    data = response.json()
    assert "trend" in data,   f"Missing 'trend' key: {data}"
    assert "current" in data, f"Missing 'current' key: {data}"
    assert isinstance(data["trend"], list), "'trend' must be a list"
    assert "iks_v2" in data["current"],     f"Missing 'iks_v2' in current: {data['current']}"
    assert "components" in data["current"], f"Missing 'components' in current: {data['current']}"


# ---------------------------------------------------------------------------
# Test 6: GET /api/soc/learning-state — includes iks_v2 field
# ---------------------------------------------------------------------------

def test_learning_state_includes_iks_v2():
    """GET /api/soc/learning-state includes iks_v2 field."""
    from fastapi.testclient import TestClient
    from app.main import app

    async def _fake_run_query(query, params=None):
        q = query.strip()
        if "RETURN count(d) AS total" in q:
            return [{"total": 20}]
        if "RETURN d.category AS category, count(d) AS n" in q:
            return [{"category": "credential_access", "n": 20}]
        if "d.confidence >= 0.70" in q:
            return [{"high_conf": 15}]
        if "d.outcome IS NOT NULL" in q and "avg(" in q:
            return [{"category": "credential_access", "accuracy": 0.85}]
        if "verified_at" in q:
            return []
        return []

    with patch("app.routers.soc.neo4j_client") as mock_neo4j:
        mock_neo4j.run_query = _fake_run_query
        client = TestClient(app)
        response = client.get("/api/soc/learning-state")

    assert response.status_code == 200, f"Status: {response.status_code}, body: {response.text}"
    data = response.json()
    assert "iks_v2" in data, f"'iks_v2' missing from learning-state response: {list(data.keys())}"
    assert "iks_components" in data, f"'iks_components' missing: {list(data.keys())}"
    assert "iks_interpretation" in data, f"'iks_interpretation' missing: {list(data.keys())}"
