"""
Tests for Phase 4: ShadowModeService, CheckpointService, and their API endpoints.

Coverage:
  test_shadow_toggle                  -- POST toggle enables/disables shadow mode
  test_shadow_report_empty            -- GET report with no shadow decisions -> totals = 0
  test_checkpoint_create_and_list     -- create checkpoint, list returns it
  test_checkpoint_rollback            -- rollback restores state and sets frozen=True
  test_freeze_unfreeze                -- POST freeze/unfreeze returns correct frozen flag
  test_shadow_analyst_action          -- POST analyst-action returns recorded=True
  test_learning_state_shows_frozen    -- freeze then learning-state shows frozen=True
  test_shadow_report_with_decisions   -- shadow report computes agreement rate correctly
"""

import asyncio
import json
import numpy as np
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scorer(n_cat=6, n_act=5, n_fac=6, decision_count=10):
    """Return a real ProfileScorer instance (uses SOCDomainConfig)."""
    from app.domains.soc.config import SOCDomainConfig
    scorer = SOCDomainConfig().build_profile_scorer()
    return scorer


def _graph_noop():
    """Return a mock graph client that ignores writes and returns empty lists."""
    mock = MagicMock()
    mock.run_query = AsyncMock(return_value=[])
    return mock


# ---------------------------------------------------------------------------
# Test 1: shadow toggle
# ---------------------------------------------------------------------------

def test_shadow_toggle():
    """POST toggle enables then disables shadow mode."""
    from app.services.shadow_mode import ShadowModeService

    with patch("app.routers.framework_router.graph_client", _graph_noop()):
        client = TestClient(app)

        resp = client.post("/api/soc/shadow/toggle", json={"enabled": True})
        assert resp.status_code == 200, resp.text
        assert resp.json()["shadow_mode"] is True
        assert ShadowModeService.SHADOW_ENABLED is True

        resp = client.post("/api/soc/shadow/toggle", json={"enabled": False})
        assert resp.status_code == 200, resp.text
        assert resp.json()["shadow_mode"] is False
        assert ShadowModeService.SHADOW_ENABLED is False


# ---------------------------------------------------------------------------
# Test 2: shadow report with no decisions
# ---------------------------------------------------------------------------

def test_shadow_report_empty():
    """GET shadow report with no shadow decisions returns total = 0."""
    with patch("app.routers.framework_router.graph_client", _graph_noop()):
        client = TestClient(app)
        resp = client.get("/api/soc/shadow/report")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total_shadow_decisions"] == 0
    assert "overall_agreement" in data
    assert "by_category" in data
    assert "recommendation" in data


# ---------------------------------------------------------------------------
# Test 3: checkpoint create + list
# ---------------------------------------------------------------------------

def test_checkpoint_create_and_list():
    """POST create checkpoint then GET list returns at least one entry."""
    created_nodes = []

    async def fake_run_query(query, params=None):
        q = query.strip()
        if q.startswith("CREATE (cp:Checkpoint"):
            created_nodes.append(params or {})
            return []
        if q.startswith("MATCH (cp:Checkpoint)"):
            # Return the just-created checkpoints
            return [
                {
                    "id":             p.get("id", "test-id"),
                    "timestamp":      "2026-03-16T10:00:00Z",
                    "reason":         p.get("reason", "manual"),
                    "decision_count": p.get("dc", 0),
                }
                for p in created_nodes
            ]
        return []

    scorer = _make_scorer()

    with patch("app.routers.framework_router.graph_client") as mock_graph, \
         patch("app.services.gae_state.get_profile_scorer", return_value=scorer):
        mock_graph.run_query = fake_run_query
        client = TestClient(app)

        resp = client.post("/api/soc/checkpoint/create", json={"reason": "test-create"})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "checkpoint_id" in data
        assert data["reason"] == "test-create"

        resp2 = client.get("/api/soc/checkpoint/list")
        assert resp2.status_code == 200, resp2.text
        checkpoints = resp2.json()["checkpoints"]
        assert len(checkpoints) >= 1, f"Expected at least 1 checkpoint, got: {checkpoints}"


# ---------------------------------------------------------------------------
# Test 4: rollback restores state and freezes scorer
# ---------------------------------------------------------------------------

def test_checkpoint_rollback():
    """POST rollback returns frozen=True and status='rolled_back'."""
    scorer = _make_scorer()
    scorer.unfreeze()  # ensure not frozen before rollback

    cp_id   = "test-cp-001"
    mu_snap = scorer.centroids.tolist()

    async def fake_run_query(query, params=None):
        q = query.strip()
        if "MATCH (cp:Checkpoint {id:" in q:
            return [{"cp": {
                "id":               cp_id,
                "mu_snapshot":      json.dumps(mu_snap),
                "counts_snapshot":  json.dumps(scorer.counts.tolist()),
                "decision_count":   10,
                "reason":           "test",
            }}]
        return []

    with patch("app.routers.framework_router.graph_client") as mock_graph, \
         patch("app.services.gae_state.get_profile_scorer", return_value=scorer):
        mock_graph.run_query = fake_run_query
        client = TestClient(app)

        resp = client.post("/api/soc/checkpoint/rollback", json={"checkpoint_id": cp_id})

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "rolled_back", data
    assert data["frozen"] is True, data
    assert data["checkpoint_id"] == cp_id


# ---------------------------------------------------------------------------
# Test 5: freeze / unfreeze via API
# ---------------------------------------------------------------------------

def test_freeze_unfreeze():
    """POST /freeze returns frozen=True; POST /unfreeze returns frozen=False."""
    scorer = _make_scorer()

    with patch("app.routers.framework_router.graph_client", _graph_noop()), \
         patch("app.services.gae_state.get_profile_scorer", return_value=scorer):
        client = TestClient(app)

        resp = client.post("/api/soc/scorer/freeze")
        assert resp.status_code == 200, resp.text
        assert resp.json()["frozen"] is True
        assert scorer._frozen is True

        resp = client.post("/api/soc/scorer/unfreeze")
        assert resp.status_code == 200, resp.text
        assert resp.json()["frozen"] is False
        assert scorer._frozen is False


# ---------------------------------------------------------------------------
# Test 6: shadow analyst-action returns recorded=True
# ---------------------------------------------------------------------------

def test_shadow_analyst_action():
    """POST /shadow/analyst-action returns recorded=True."""
    with patch("app.routers.framework_router.graph_client", _graph_noop()):
        client = TestClient(app)
        resp = client.post(
            "/api/soc/shadow/analyst-action",
            json={"decision_id": "DEC-TEST-001", "analyst_action": "escalate"},
        )
    assert resp.status_code == 200, resp.text
    assert resp.json()["recorded"] is True


# ---------------------------------------------------------------------------
# Test 7: freeze → learning-state shows frozen=True
# ---------------------------------------------------------------------------

def test_learning_state_shows_frozen():
    """After freeze, GET /learning-state returns frozen=True.

    The learning-state endpoint reads frozen from learning_state.profile_scorer._frozen,
    so we mock get_learning_state to return a mock with a frozen scorer.
    """
    scorer = _make_scorer()
    scorer.freeze()  # set _frozen=True on the scorer

    # Build a mock LearningState that exposes our frozen scorer
    mock_ls = MagicMock()
    mock_ls.decision_count = 10
    mock_ls.profile_scorer = scorer

    async def fake_run_query(query, params=None):
        # Satisfy the IKS v2 queries so the endpoint doesn't fail
        q = query.strip()
        if "RETURN count(d) AS total" in q:
            return [{"total": 10}]
        if "RETURN d.category AS category, count(d) AS n" in q:
            return [{"category": "credential_access", "n": 10}]
        if "d.confidence >= 0.70" in q:
            return [{"high_conf": 8}]
        if "d.outcome IS NOT NULL" in q and "avg(" in q:
            return [{"category": "credential_access", "accuracy": 0.80}]
        return []

    with patch("app.routers.soc.graph_client") as mock_graph, \
         patch("app.services.gae_state.get_learning_state", return_value=mock_ls):
        mock_graph.run_query = fake_run_query
        client = TestClient(app)
        resp = client.get("/api/soc/learning-state")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["frozen"] is True, f"Expected frozen=True, got: {data}"

    # Cleanup
    scorer.unfreeze()


# ---------------------------------------------------------------------------
# Test 8: shadow report with decisions computes agreement correctly
# ---------------------------------------------------------------------------

def test_shadow_report_with_decisions():
    """Shadow report computes per-category agreement rate correctly."""
    # 4 decisions in credential_access: 3 agreed, 1 disagreed → 75%
    # 2 decisions in lateral_movement: 1 agreed, 1 disagreed → 50%
    shadow_data = [
        {"category": "credential_access", "total": 4, "agreed": 3},
        {"category": "lateral_movement",  "total": 2, "agreed": 1},
    ]

    async def fake_run_query(query, params=None):
        if "shadow_mode = true" in query:
            return shadow_data
        return []

    with patch("app.routers.framework_router.graph_client") as mock_graph:
        mock_graph.run_query = fake_run_query
        client = TestClient(app)
        resp = client.get("/api/soc/shadow/report")

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total_shadow_decisions"] == 6
    cred = data["by_category"]["credential_access"]
    assert abs(cred["agreement_rate"] - 0.75) < 1e-4, f"Expected 0.75, got {cred['agreement_rate']}"
    lat = data["by_category"]["lateral_movement"]
    assert abs(lat["agreement_rate"] - 0.50) < 1e-4, f"Expected 0.50, got {lat['agreement_rate']}"
    # overall: 4/6 ≈ 0.6667
    assert abs(data["overall_agreement"] - round(4/6, 4)) < 1e-3
