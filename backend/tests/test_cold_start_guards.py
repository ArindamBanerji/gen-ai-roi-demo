"""
Cold-start guard tests -- P1 batch (Group 5).

Verifies that endpoints requiring a live ProfileScorer return 503 (not 500 / crash)
when the scorer is absent, and that the simulation service handles a None scorer
gracefully without raising.

Patches used:
  app.services.gae_state.get_profile_scorer  -- for endpoints with in-function imports
  app.routers.evolution.get_profile_scorer   -- for evolution (module-level binding)

Total: 9 tests.
"""
import os
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """Module-scoped TestClient with SAML disabled."""
    os.environ.pop("SAML_ENABLED", None)
    import app.auth.dependencies as dep
    dep._auth_config = None
    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Test 1 — POST /api/alert/analyze → 503
# ---------------------------------------------------------------------------

def test_analyze_503_when_scorer_none(client):
    """analyze_alert returns 503 when ProfileScorer is not initialized.

    Triage cold-start guard (triage.py:130-134) raises HTTPException 503
    after both the initial get_profile_scorer() and the retry after
    init_learning_state() still return None.
    """
    with patch("app.services.gae_state.get_profile_scorer", return_value=None), \
         patch("app.services.gae_state.init_learning_state", return_value=None):
        r = client.post("/api/alert/analyze", json={"alert_id": "TEST-001"})
    assert r.status_code == 503


# ---------------------------------------------------------------------------
# Test 2 — POST /api/alert/process → 503
# ---------------------------------------------------------------------------

def test_process_503_when_scorer_none(client):
    """process_alert returns 503 when ProfileScorer is None.

    The scorer guard (evolution.py:137-139) fires after the alert fetch,
    so we mock graph and the factor computation to reach the guard.
    """
    import numpy as np

    minimal_alert = {"alert_id": "TEST-001", "alert_type": "malware_execution"}
    minimal_context = {"alert_type": "malware_execution", "key_facts": []}

    with patch("app.routers.evolution.get_profile_scorer", return_value=None), \
         patch(
             "app.db.graph_client.graph_client.get_alert",
             new_callable=AsyncMock,
             return_value=minimal_alert,
         ), \
         patch(
             "app.db.graph_client.graph_client.get_security_context",
             new_callable=AsyncMock,
             return_value=minimal_context,
         ), \
         patch(
             "app.routers.evolution.compute_factor_vector",
             new_callable=AsyncMock,
             return_value=np.zeros(64),
         ):
        r = client.post("/api/alert/process", json={"alert_id": "TEST-001"})
    assert r.status_code == 503


# ---------------------------------------------------------------------------
# Test 3 — POST /api/soc/checkpoint/create → 503
# ---------------------------------------------------------------------------

def test_checkpoint_create_503_when_scorer_none(client):
    """checkpoint_create returns 503 when scorer is None."""
    with patch("app.services.gae_state.get_profile_scorer", return_value=None):
        r = client.post("/api/soc/checkpoint/create", json={"reason": "cold-start test"})
    assert r.status_code == 503


# ---------------------------------------------------------------------------
# Test 4 — POST /api/soc/checkpoint/rollback → 503
# ---------------------------------------------------------------------------

def test_checkpoint_rollback_503_when_scorer_none(client):
    """checkpoint_rollback returns 503 when scorer is None."""
    with patch("app.services.gae_state.get_profile_scorer", return_value=None):
        r = client.post(
            "/api/soc/checkpoint/rollback",
            json={"checkpoint_id": "ckpt-cold-start-test"},
        )
    assert r.status_code == 503


# ---------------------------------------------------------------------------
# Test 5 — POST /api/soc/scorer/freeze → 503
# ---------------------------------------------------------------------------

def test_scorer_freeze_503_when_scorer_none(client):
    """scorer_freeze returns 503 when scorer is None."""
    with patch("app.services.gae_state.get_profile_scorer", return_value=None):
        r = client.post("/api/soc/scorer/freeze")
    assert r.status_code == 503


# ---------------------------------------------------------------------------
# Test 6 — POST /api/soc/scorer/unfreeze → 503
# ---------------------------------------------------------------------------

def test_scorer_unfreeze_503_when_scorer_none(client):
    """scorer_unfreeze returns 503 when scorer is None."""
    with patch("app.services.gae_state.get_profile_scorer", return_value=None):
        r = client.post("/api/soc/scorer/unfreeze")
    assert r.status_code == 503


# ---------------------------------------------------------------------------
# Test 7 — POST /api/soc/interventions/freeze → 503
# ---------------------------------------------------------------------------

def test_intervention_freeze_503_when_scorer_none(client):
    """intervention_freeze returns 503 when scorer is None.

    _get_intervention_controls() raises RuntimeError when scorer is None,
    which the endpoint catches and converts to HTTPException 503.
    """
    with patch("app.services.gae_state.get_profile_scorer", return_value=None):
        r = client.post(
            "/api/soc/interventions/freeze",
            json={"initiated_by": "analyst@test.com", "reason": "cold-start test"},
        )
    assert r.status_code == 503


# ---------------------------------------------------------------------------
# Test 8 — 503 response has JSON content-type with 'detail' key
# ---------------------------------------------------------------------------

def test_cold_start_503_is_json_with_detail(client):
    """503 cold-start responses are JSON with a 'detail' field (not HTML crashes)."""
    with patch("app.services.gae_state.get_profile_scorer", return_value=None):
        r = client.post("/api/soc/scorer/freeze")
    assert r.status_code == 503
    assert "application/json" in r.headers.get("content-type", "")
    body = r.json()
    assert "detail" in body


# ---------------------------------------------------------------------------
# Test 9 — Simulation start handles None scorer gracefully
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_simulation_background_reports_error_when_scorer_missing():
    """The real simulation worker surfaces cold-start scorer absence as error status."""
    from app.routers import simulation as simulation_router

    sim_id = "cold-start-sim-test"
    simulation_router._simulations[sim_id] = {
        "sim_id": sim_id,
        "total": 1,
        "step": 0,
        "status": "running",
        "current_accuracy": 0.0,
        "category_accuracy": {},
        "latest_weight_snapshot": [],
        "result": None,
    }
    try:
        with patch(
            "app.routers.simulation._load_alert_pool",
            new_callable=AsyncMock,
            return_value=[],
        ), patch("app.services.gae_state.get_profile_scorer", return_value=None):
            await simulation_router._run_simulation_bg(sim_id, n_decisions=1, speed_ms=0)

        assert simulation_router._simulations[sim_id]["status"] == "error"
        assert "GraphStore is unavailable" in simulation_router._simulations[sim_id]["error"]
    finally:
        simulation_router._simulations.pop(sim_id, None)
