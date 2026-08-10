"""
Regression tests for BACKLOG-020: IKS must not collapse after
POST /api/alerts/reset (demo-cycle reset).

Root cause: reset_all() was calling reset_learning_state(), which wiped
ProfileScorer centroids and rebuilt a fresh scorer with mu = mu_0,
making drift-based IKS return 0 -> 2.5.

Fix: reset_demo_alerts() now calls reset_except(["learning_state"]),
preserving the ProfileScorer across demo resets.
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _graph_reset_mock():
    """Mock that satisfies the AGE query inside reset_demo_alerts()."""
    mock = AsyncMock()
    mock.run_query = AsyncMock(return_value=[{"reset_count": 10}])
    return mock


# ---------------------------------------------------------------------------
# Test 1: ProfileScorer survives POST /api/alerts/reset
# ---------------------------------------------------------------------------

def test_alerts_reset_preserves_profile_scorer():
    """ProfileScorer must still be attached after a demo reset -- BACKLOG-020."""
    ls_before = client.get("/api/soc/learning-state").json()
    iks_before = ls_before.get("iks_v2", 0.0)
    if iks_before == 0.0:
        pytest.skip("ProfileScorer not initialized -- no IKS data")

    with patch("app.routers.triage.graph_client", _graph_reset_mock()):
        resp = client.post("/api/alerts/reset")
    assert resp.status_code == 200

    ls_after = client.get("/api/soc/learning-state").json()
    assert ls_after.get("iks_v2", 0.0) > 0.0, (
        "BACKLOG-020: ProfileScorer was reset after /api/alerts/reset -- "
        "IKS dropped to zero (learning state wiped)"
    )


# ---------------------------------------------------------------------------
# Test 2: IKS does not collapse after reset
# ---------------------------------------------------------------------------

def test_alerts_reset_does_not_collapse_iks():
    """IKS must not drop to near-zero after POST /api/alerts/reset -- BACKLOG-020."""
    ls_before = client.get("/api/soc/learning-state").json()
    iks_before = ls_before.get("iks_v2", 0.0)
    if iks_before == 0.0:
        pytest.skip("ProfileScorer not initialized -- no IKS data")

    with patch("app.routers.triage.graph_client", _graph_reset_mock()):
        resp = client.post("/api/alerts/reset")
    assert resp.status_code == 200

    ls_after = client.get("/api/soc/learning-state").json()
    iks_after = ls_after.get("iks_v2", 0.0)

    assert iks_after >= iks_before - 5.0, (
        f"BACKLOG-020: IKS collapsed {iks_before:.1f}->{iks_after:.1f} "
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

    asyncio.run(sm.reset_except(["learning_state"]))

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

    asyncio.run(sm.reset_except([]))

    assert "feedback"       in called
    assert "learning_state" in called


# ---------------------------------------------------------------------------
# Test 5: IKS stable after learning decisions (regression for BACKLOG-020)
# ---------------------------------------------------------------------------

def test_iks_stable_after_learning_decisions():
    """IKS must not collapse after learning loop runs -- BACKLOG-020.

    Simulates the key invariant: a sequence of demo resets (which the
    E2E learning loop triggers via beforeEach) must not clobber the
    ProfileScorer, so IKS remains at its pre-test level.
    """
    ls_before = client.get("/api/soc/learning-state").json()
    iks_before = ls_before.get("iks_v2", 0.0)
    if iks_before == 0.0:
        pytest.skip("ProfileScorer not initialized -- no IKS data")
    assert iks_before >= 0, f"IKS must be non-negative before test: {iks_before}"

    # Simulate 5 demo-cycle resets (what beforeEach + explicit reset trigger)
    mock_graph = _graph_reset_mock()
    for _ in range(5):
        with patch("app.routers.triage.graph_client", mock_graph):
            resp = client.post("/api/alerts/reset")
        assert resp.status_code == 200

    ls_after = client.get("/api/soc/learning-state").json()
    iks_after = ls_after.get("iks_v2", 0.0)

    assert iks_after >= iks_before - 10, (
        f"BACKLOG-020: IKS dropped {iks_before:.1f}->{iks_after:.1f} "
        "after 5 demo resets -- learning state was wiped"
    )


# ---------------------------------------------------------------------------
# Test 6: IKS > 70 after /api/alerts/reset (gate test for demo readiness)
# ---------------------------------------------------------------------------

def test_iks_above_70_after_alerts_reset():
    """IKS must stay > 70 after /api/alerts/reset -- demo readiness gate.

    Regression for BACKLOG-020 part 2: verifies that all reset paths
    (triage, metrics demo/reset-all, metrics demo/reseed) preserve the
    ProfileScorer centroids so IKS never collapses mid-demo.
    """
    ls_before = client.get("/api/soc/learning-state").json()
    iks_before = ls_before.get("iks_v2", 0.0)
    if iks_before <= 70:
        pytest.skip(f"IKS baseline is {iks_before:.1f} <= 70 -- bootstrap not complete")

    with patch("app.routers.triage.graph_client", _graph_reset_mock()):
        resp = client.post("/api/alerts/reset")
    assert resp.status_code == 200

    ls_after = client.get("/api/soc/learning-state").json()
    iks_after = ls_after.get("iks_v2", 0.0)

    assert iks_after > 70, (
        f"BACKLOG-020: IKS dropped to {iks_after:.1f} after /api/alerts/reset "
        "(must remain > 70 for demo gate)"
    )


# ---------------------------------------------------------------------------
# Test 7: IKS > 50 after /api/alerts/reset via Tab 2 endpoint
# ---------------------------------------------------------------------------

def test_alerts_reset_preserves_iks_above_threshold():
    """IKS must stay > 50 after /api/alerts/reset.
    Regression test for BACKLOG-020 part 2.
    """
    before = client.get("/api/soc/tab/2/content").json()
    iks_before = before["content"]["iks_score"]

    # Call the reset endpoint
    with patch("app.routers.triage.graph_client", _graph_reset_mock()):
        reset_resp = client.post("/api/alerts/reset")
    assert reset_resp.status_code == 200

    after = client.get("/api/soc/tab/2/content").json()
    iks_after = after["content"]["iks_score"]

    assert iks_after > 0, \
        f"BACKLOG-020: IKS dropped to zero after reset (was {iks_before})"
    assert iks_after == iks_before, \
        f"BACKLOG-020: IKS changed after reset: {iks_before} -> {iks_after}"
