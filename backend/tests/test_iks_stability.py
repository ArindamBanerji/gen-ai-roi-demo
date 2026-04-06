"""
Regression tests for BACKLOG-020: IKS must not collapse after
POST /api/alerts/reset (demo-cycle reset).

Root cause: reset_all() was calling reset_learning_state(), which wiped
ProfileScorer centroids and rebuilt a fresh scorer with mu = mu_0,
making drift-based IKS return 0 → 2.5.

Fix: reset_demo_alerts() now calls reset_except(["learning_state"]),
preserving the ProfileScorer across demo resets.
"""

import os
import sys
from unittest.mock import AsyncMock, patch

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _neo4j_reset_mock():
    """Mock that satisfies the Neo4j query inside reset_demo_alerts()."""
    mock = AsyncMock()
    mock.run_query = AsyncMock(return_value=[{"reset_count": 10}])
    return mock


# ---------------------------------------------------------------------------
# Test 1: ProfileScorer survives POST /api/alerts/reset
# ---------------------------------------------------------------------------

def test_alerts_reset_preserves_profile_scorer():
    """ProfileScorer must still be attached after a demo reset — BACKLOG-020."""
    from app.services.gae_state import get_profile_scorer

    ps_before = get_profile_scorer()
    if ps_before is None:
        pytest.skip("ProfileScorer not initialized — startup required")

    with patch("app.routers.triage.neo4j_client", _neo4j_reset_mock()):
        resp = client.post("/api/alerts/reset")
    assert resp.status_code == 200

    ps_after = get_profile_scorer()
    assert ps_after is not None, (
        "BACKLOG-020: ProfileScorer was None after /api/alerts/reset — "
        "learning state was wiped"
    )


# ---------------------------------------------------------------------------
# Test 2: IKS does not collapse after reset
# ---------------------------------------------------------------------------

def test_alerts_reset_does_not_collapse_iks():
    """IKS must not drop to near-zero after POST /api/alerts/reset — BACKLOG-020."""
    from app.services.gae_state import get_profile_scorer
    from app.services.iks import compute_iks

    ps = get_profile_scorer()
    if ps is None:
        pytest.skip("ProfileScorer not initialized — startup required")

    iks_before = compute_iks(ps.mu)["current"]

    with patch("app.routers.triage.neo4j_client", _neo4j_reset_mock()):
        resp = client.post("/api/alerts/reset")
    assert resp.status_code == 200

    ps_after = get_profile_scorer()
    assert ps_after is not None
    iks_after = compute_iks(ps_after.mu)["current"]

    assert iks_after >= iks_before - 5.0, (
        f"BACKLOG-020: IKS collapsed {iks_before:.1f}→{iks_after:.1f} "
        "after /api/alerts/reset"
    )


# ---------------------------------------------------------------------------
# Test 3: reset_except skips named handlers
# ---------------------------------------------------------------------------

def test_state_manager_reset_except_skips_named_handler():
    """reset_except(['learning_state']) must not call the learning_state handler."""
    from unittest.mock import MagicMock
    from app.core.state_manager import DemoStateManager

    sm = DemoStateManager()
    called = []
    sm.register("feedback",       lambda: called.append("feedback"))
    sm.register("audit",          lambda: called.append("audit"))
    sm.register("learning_state", lambda: called.append("learning_state"))

    sm.reset_except(["learning_state"])

    assert "feedback"       in called
    assert "audit"          in called
    assert "learning_state" not in called, (
        "reset_except must not call learning_state handler"
    )


# ---------------------------------------------------------------------------
# Test 4: reset_except with empty skip list behaves like reset_all
# ---------------------------------------------------------------------------

def test_state_manager_reset_except_empty_skip_calls_all():
    """reset_except([]) must call all registered handlers."""
    from app.core.state_manager import DemoStateManager

    sm = DemoStateManager()
    called = []
    sm.register("feedback",       lambda: called.append("feedback"))
    sm.register("learning_state", lambda: called.append("learning_state"))

    sm.reset_except([])

    assert "feedback"       in called
    assert "learning_state" in called


# ---------------------------------------------------------------------------
# Test 5: IKS stable after learning decisions (regression for BACKLOG-020)
# ---------------------------------------------------------------------------

def test_iks_stable_after_learning_decisions():
    """IKS must not collapse after learning loop runs — BACKLOG-020.

    Simulates the key invariant: a sequence of demo resets (which the
    E2E learning loop triggers via beforeEach) must not clobber the
    ProfileScorer, so IKS remains at its pre-test level.
    """
    from app.services.gae_state import get_profile_scorer
    from app.services.iks import compute_iks

    ps = get_profile_scorer()
    if ps is None:
        pytest.skip("ProfileScorer not initialized — startup required")

    iks_before = compute_iks(ps.mu)["current"]
    assert iks_before >= 0, f"IKS must be non-negative before test: {iks_before}"

    # Simulate 5 demo-cycle resets (what beforeEach + explicit reset trigger)
    mock_neo4j = _neo4j_reset_mock()
    for _ in range(5):
        with patch("app.routers.triage.neo4j_client", mock_neo4j):
            resp = client.post("/api/alerts/reset")
        assert resp.status_code == 200

    ps_after = get_profile_scorer()
    assert ps_after is not None
    iks_after = compute_iks(ps_after.mu)["current"]

    assert iks_after >= iks_before - 10, (
        f"BACKLOG-020: IKS dropped {iks_before:.1f}→{iks_after:.1f} "
        "after 5 demo resets — learning state was wiped"
    )
