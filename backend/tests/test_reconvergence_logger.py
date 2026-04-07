"""
Tests for BACKLOG-015 / EXP-G1: re-convergence event logger and
GET /api/soc/reconvergence-log endpoint.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Test 1 — endpoint returns 200
# ---------------------------------------------------------------------------

def test_reconvergence_log_endpoint_returns_200():
    resp = client.get("/api/soc/reconvergence-log")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Test 2 — response has the three required top-level fields
# ---------------------------------------------------------------------------

def test_reconvergence_log_has_required_fields():
    data = client.get("/api/soc/reconvergence-log").json()
    assert "events" in data
    assert "total_events" in data
    assert "note" in data
    assert "EXP-G1" in data["note"]


# ---------------------------------------------------------------------------
# Test 3 — if events exist, all 8 per-event fields must be present
# ---------------------------------------------------------------------------

def test_reconvergence_event_has_all_eight_fields():
    data = client.get("/api/soc/reconvergence-log").json()
    required = [
        "re_convergence_event_id", "convergence_start_decisions",
        "convergence_end_decisions", "n_reconverge",
        "graph_entity_count_at_start", "trigger_type", "domain",
        "logged_at_epoch",
    ]
    for event in data["events"]:
        for field in required:
            assert field in event, f"Event missing field: {field}"
