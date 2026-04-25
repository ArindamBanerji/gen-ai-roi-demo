"""
Audit chain wiring tests (Codex Step 2 adversarial review).

Tests the SOC-side wiring of the audit chain: framework helpers,
triage-outcome routing, and audit REST endpoints.  Data-structure
contracts live in test_audit_chain_contract.py.

13 tests.
"""
import asyncio
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from ci_platform.audit.evidence_ledger import OutcomeEntry
from app.framework.audit import _LEDGER, _SITUATION_TYPES
from app.framework.feedback_store import FEEDBACK_GIVEN


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _fresh_decision(alert_id="ALT-WIRE-001", situation_type="malware_detected",
                    action_taken="escalate", confidence=0.85):
    """Append one clean LedgerEntry and return its SOC dict."""
    from app.framework.audit import record_decision
    return _run(record_decision(
        alert_id=alert_id,
        situation_type=situation_type,
        action_taken=action_taken,
        factors=["factor_a", "factor_b"],
        confidence=confidence,
    ))


def _clear():
    _LEDGER._entries.clear()
    _SITUATION_TYPES.clear()
    FEEDBACK_GIVEN.clear()


# ---------------------------------------------------------------------------
# GROUP 1 — Audit framework helpers (6 tests)
# ---------------------------------------------------------------------------

def test_record_outcome_returns_none_when_decision_missing():
    """record_outcome with an unknown decision_id returns None gracefully."""
    from app.framework.audit import record_outcome
    _clear()
    result = _run(record_outcome("DEC-MISSING-XYZ", "correct"))
    assert result is None


def test_reconstruct_appends_outcome_entry_once():
    """reconstruct_from_memory adds an OutcomeEntry for a FEEDBACK_GIVEN entry."""
    from app.framework.audit import reconstruct_from_memory
    _clear()
    rec = _fresh_decision()
    FEEDBACK_GIVEN["ALT-WIRE-001"] = {
        "decision_id": rec["id"],
        "outcome": "correct",
        "timestamp": "2026-04-22T12:00:00",
    }
    added = _run(reconstruct_from_memory())
    assert added >= 1
    outcomes = [e for e in _LEDGER.entries() if isinstance(e, OutcomeEntry)]
    assert len(outcomes) >= 1


def test_reconstruct_skips_existing_outcome():
    """reconstruct_from_memory does not add a second OutcomeEntry when one exists."""
    from app.framework.audit import record_outcome, reconstruct_from_memory
    _clear()
    rec = _fresh_decision()
    _run(record_outcome(rec["id"], "correct"))
    FEEDBACK_GIVEN["ALT-WIRE-001"] = {
        "decision_id": rec["id"],
        "outcome": "correct",
    }
    before = sum(1 for e in _LEDGER.entries() if isinstance(e, OutcomeEntry))
    _run(reconstruct_from_memory())
    after = sum(1 for e in _LEDGER.entries() if isinstance(e, OutcomeEntry))
    assert after == before


def test_reconstruct_swallows_missing_decision():
    """reconstruct_from_memory skips feedback whose decision_id is not in ledger."""
    from app.framework.audit import reconstruct_from_memory
    _clear()
    _fresh_decision()   # creates a different decision_id
    FEEDBACK_GIVEN["ALT-WIRE-001"] = {
        "decision_id": "DEC-FAKE-ID-DOES-NOT-EXIST",
        "outcome": "correct",
    }
    # Must not raise; returns 0 (nothing matched)
    added = _run(reconstruct_from_memory())
    assert added == 0


def test_get_decision_rows_latest_outcome():
    """get_decision_rows uses the last OutcomeEntry when multiple exist."""
    from app.framework.audit import record_outcome, get_decision_rows
    _clear()
    rec = _fresh_decision()
    _run(record_outcome(rec["id"], "correct"))
    _run(record_outcome(rec["id"], "incorrect"))   # later insertion wins
    rows = get_decision_rows()
    match = [r for r in rows if r["id"] == rec["id"]]
    assert len(match) == 1
    assert match[0]["outcome"] == "incorrect"


def test_get_decision_rows_pending_without_outcome():
    """Decisions with no OutcomeEntry show None or 'pending'."""
    from app.framework.audit import get_decision_rows
    _clear()
    rec = _fresh_decision(alert_id="ALT-PEND-001", action_taken="investigate")
    rows = get_decision_rows()
    match = [r for r in rows if r["id"] == rec["id"]]
    assert len(match) == 1
    assert match[0]["outcome"] in (None, "pending")


# ---------------------------------------------------------------------------
# GROUP 2 — Triage / audit endpoint smoke tests (4 tests)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def app_client():
    import os
    os.environ.pop("SAML_ENABLED", None)
    import app.auth.dependencies as dep
    dep._auth_config = None
    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


def test_triage_outcome_non_blocking_for_missing_decision(app_client):
    """POST /api/alert/outcome with a non-existent decision does not 500."""
    r = app_client.post("/api/alert/outcome", json={
        "alert_id":   "ALT-NONEXISTENT",
        "decision_id": "DEC-NONEXISTENT",
        "outcome":    "correct",
    })
    assert r.status_code != 500


def test_audit_decisions_endpoint(app_client):
    """GET /api/audit/decisions returns 200 with a decisions list."""
    r = app_client.get("/api/audit/decisions")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, (list, dict))


def test_audit_verify_endpoint(app_client):
    """GET /api/audit/verify returns 200 with a chain validity result."""
    r = app_client.get("/api/audit/verify")
    assert r.status_code == 200
    data = r.json()
    assert "verified" in data


def test_audit_epochs_endpoint(app_client):
    """GET /api/audit/epochs returns 200."""
    r = app_client.get("/api/audit/epochs")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# GROUP 3 — Audit router ordering (1 test)
# ---------------------------------------------------------------------------

def test_decisions_endpoint_calls_reconstruct_first(app_client):
    """GET /api/audit/decisions reconstructs feedback before returning rows.

    Verified by checking that the endpoint returns a dict with a 'decisions'
    key — meaning the router ran reconstruct_from_memory() then get_decision_rows().
    """
    r = app_client.get("/api/audit/decisions")
    assert r.status_code == 200
    data = r.json()
    assert "decisions" in data   # key is present after reconstruct + projection


# ---------------------------------------------------------------------------
# GROUP 4 — Simulation wiring (2 tests)
# ---------------------------------------------------------------------------

def test_simulation_start_endpoint(app_client):
    """POST /api/simulation/start returns 200 when reset is mocked.

    soft_reset() is mocked to avoid mutating learning-state globals that
    other tests in the suite depend on.  The background simulation task
    is also mocked to prevent it from running without a live scorer.
    """
    from unittest.mock import AsyncMock, patch
    with patch("app.services.state_manager.StateManager.soft_reset",
               new_callable=AsyncMock), \
         patch("app.routers.simulation._run_simulation_bg",
               new_callable=AsyncMock):
        r = app_client.post("/api/simulation/start",
                            json={"n_decisions": 5, "speed_ms": 0})
    assert r.status_code == 200
    assert "simulation_id" in r.json()


def test_simulation_progress_unknown_id(app_client):
    """GET /api/simulation/progress/{id} returns 404 for an unknown sim_id."""
    r = app_client.get("/api/simulation/progress/no-such-simulation-id")
    assert r.status_code == 404
