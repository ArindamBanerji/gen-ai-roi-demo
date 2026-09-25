"""
Block 9.1 -- D5 Per-analyst eta weighting tests.
Precision queries use real AGE; weighting and response contracts remain unit tests.
"""
import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.services.learning_health import compute_analyst_precision
from app.domains.soc.config import GateConfig
from app.services.gae_state import (
    apply_analyst_eta_weights,
    get_analyst_eta_weights,
    init_learning_state,
    get_profile_scorer,
)


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_analyst(age_graph, name, total, correct):
    for index in range(total):
        age_graph.decision(correct=index < correct, source_id=name, verified_by=name)


# ---------------------------------------------------------------------------
# Test 1 — compute_precision_returns_dict with ≥2 qualifying analysts
# ---------------------------------------------------------------------------

@pytest.mark.age
def test_compute_precision_returns_dict(age_graph):
    """When >=2 analysts each have >=10 decisions, returns precision dict."""
    for name, correct in [("alice", 8), ("bob", 7), ("carol", 6)]:
        _seed_analyst(age_graph, name, 10, correct)
    result = _run(compute_analyst_precision(age_graph.client))

    assert isinstance(result, dict), "Should return a dict"
    assert "alice" in result
    assert "bob"   in result
    assert "carol" in result
    assert result["alice"] == pytest.approx(0.8, abs=1e-6)
    assert result["bob"]   == pytest.approx(0.7, abs=1e-6)


# ---------------------------------------------------------------------------
# Test 2 — analysts with fewer than 10 decisions are excluded at query level;
#          if only 1 analyst qualifies, returns {}
# ---------------------------------------------------------------------------

@pytest.mark.age
def test_precision_excludes_analysts_below_10_decisions(age_graph):
    """
    The Cypher WHERE total >= 10 is enforced in the query. If only one analyst
    comes back (meaning only one has >=10 decisions), returns {} because
    _MIN_ANALYSTS_REQUIRED = 2.
    """
    _seed_analyst(age_graph, "alice", 10, 8)
    _seed_analyst(age_graph, "bob", 9, 9)
    assert _run(compute_analyst_precision(age_graph.client)) == {}
    age_graph.decision(correct=False, source_id="bob", verified_by="bob")
    result = _run(compute_analyst_precision(age_graph.reopen_client()))
    assert result == pytest.approx({"alice": 0.8, "bob": 0.9})



# ---------------------------------------------------------------------------
# Test 3 — eta_weights computed correctly from GateConfig.eta_weights
# ---------------------------------------------------------------------------

def test_eta_weights_computed_correctly():
    """
    precision: alice=0.90, bob=0.60  ->  mean=0.75
    alice_weight = min(1.5, max(0.5, 0.90/0.75)) = min(1.5, 1.20) = 1.20
    bob_weight   = min(1.5, max(0.5, 0.60/0.75)) = min(1.5, 0.80) = 0.80
    """
    precision = {"alice": 0.90, "bob": 0.60}
    cfg = GateConfig(
        n_decisions=2000,   # > n_min (1000) -> calibrated=True
        V=200.0,
        alpha=0.25,
        per_analyst_precision=precision,
    )
    weights = cfg.eta_weights

    assert cfg.calibrated is True
    assert weights["alice"] == pytest.approx(1.20, abs=1e-6)
    assert weights["bob"]   == pytest.approx(0.80, abs=1e-6)


# ---------------------------------------------------------------------------
# Test 4 — uniform weights before N_min decisions
# ---------------------------------------------------------------------------

def test_uniform_weights_before_nmin():
    """Before N_min decisions, all analyst weights must be 1.0."""
    precision = {"alice": 0.90, "bob": 0.60, "carol": 0.75}
    cfg = GateConfig(
        n_decisions=50,    # << n_min (1000) -> calibrated=False
        V=200.0,
        alpha=0.25,
        per_analyst_precision=precision,
    )
    assert cfg.calibrated is False
    weights = cfg.eta_weights
    for analyst, w in weights.items():
        assert w == pytest.approx(1.0, abs=1e-9), (
            f"Before N_min, analyst {analyst} weight should be 1.0, got {w}"
        )


# ---------------------------------------------------------------------------
# Test 5 — endpoint returns calibrated status and analyst breakdown
# ---------------------------------------------------------------------------

def test_endpoint_returns_calibrated_status():
    """GET /api/soc/analyst-eta-weights returns required fields."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    # Patch compute_analyst_precision to return known data
    precision_data = {"alice": 0.82, "bob": 0.68}

    with patch(
        "app.services.learning_health.compute_analyst_precision",
        new=AsyncMock(return_value=precision_data),
    ):
        resp = client.get("/api/soc/analyst-eta-weights")

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()

    assert "calibrated"  in body, "Missing 'calibrated'"
    assert "n_decisions" in body, "Missing 'n_decisions'"
    assert "n_min"       in body, "Missing 'n_min'"
    assert "analysts"    in body, "Missing 'analysts'"

    analysts = body["analysts"]
    for name in ("alice", "bob"):
        assert name in analysts, f"Missing analyst '{name}' in response"
        assert "precision"  in analysts[name]
        assert "eta_weight" in analysts[name]
