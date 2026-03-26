"""
tests/test_switching_cost.py — Switching Cost Demo Moment (Feature 4) test suite.

2 tests validating the switching_cost sub-dict in GET /api/soc/profile.

Run from backend/:
    pytest tests/test_switching_cost.py -v
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from fastapi.testclient import TestClient

# Initialize learning state before the TestClient is used — mirrors the
# startup event that the TestClient does not trigger automatically.
from app.services.gae_state import init_learning_state
init_learning_state()

from app.main import app

client = TestClient(app)


# ============================================================================
# Test 1 — decisions_accumulated equals decision_count
# ============================================================================

def test_switching_cost_decisions_match_decision_count():
    """
    switching_cost.decisions_accumulated must equal iks.decision_count exactly.
    These two fields are derived from the same source — if they diverge the
    Switching Cost panel shows inconsistent numbers to the prospect.
    """
    response = client.get("/api/soc/profile")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:300]}"
    )
    body = response.json()

    assert "iks" in body, f"Response missing 'iks' key: {list(body.keys())}"
    iks = body["iks"]

    assert "switching_cost" in iks, (
        f"iks missing 'switching_cost' key: {list(iks.keys())}"
    )
    switching_cost = iks["switching_cost"]

    if switching_cost.get("decisions_accumulated") is None:
        pytest.skip("no decisions in test graph")

    assert switching_cost["decisions_accumulated"] == iks["decision_count"], (
        f"decisions_accumulated ({switching_cost['decisions_accumulated']}) "
        f"must equal decision_count ({iks['decision_count']}). "
        "These must always be identical — same source, same value."
    )


# ============================================================================
# Test 2 — competitor_iks is always 0 (static invariant)
# ============================================================================

def test_competitor_iks_always_zero():
    """
    competitor_iks must always be exactly 0.
    This is a hardcoded invariant — a competitor starting fresh has no
    institutional knowledge. It must never be derived from data.
    """
    response = client.get("/api/soc/profile")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text[:300]}"
    )
    body = response.json()

    switching_cost = body["iks"]["switching_cost"]

    assert switching_cost["competitor_iks"] == 0, (
        f"competitor_iks must always be 0 (static invariant). "
        f"Got: {switching_cost['competitor_iks']!r}"
    )
