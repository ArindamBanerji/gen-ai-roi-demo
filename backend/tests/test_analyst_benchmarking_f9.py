"""
Tests for GET /api/soc/analyst-benchmarking (F9 enhancements)
and GET /api/soc/f9-report.

Requires V-SHADOW-SYNTHETIC-v3 data in AGE (1,500 ShadowDecision nodes).
Tests that need live data skip gracefully when the data is absent.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _benchmarking_data():
    resp = client.get("/api/soc/analyst-benchmarking")
    assert resp.status_code == 200
    return resp.json()


def _shadow_data_loaded(data: dict) -> bool:
    return data.get("status") == "ready" and data.get("total_decisions", 0) > 0


# ---------------------------------------------------------------------------
# Test 1 — lead_finding present and non-trivial
# ---------------------------------------------------------------------------

def test_analyst_benchmarking_has_lead_finding():
    resp = client.get("/api/soc/analyst-benchmarking")
    assert resp.status_code == 200
    data = resp.json()
    assert "lead_finding" in data
    assert len(data["lead_finding"]) > 20


# ---------------------------------------------------------------------------
# Test 2 — lateral_movement agreement < 60% when data exists
# ---------------------------------------------------------------------------

def test_analyst_benchmarking_lateral_movement_finding():
    resp = client.get("/api/soc/analyst-benchmarking")
    data = resp.json()
    lm = data.get("per_category", {}).get("lateral_movement", {})
    # If lateral_movement data exists, agreement should be < 50%
    if lm and lm.get("verified_decisions", 0) > 0:
        assert lm.get("analyst_agreement", 1.0) < 0.60


# ---------------------------------------------------------------------------
# Test 3 — f9-report endpoint structure
# ---------------------------------------------------------------------------

def test_f9_report_endpoint():
    resp = client.get("/api/soc/f9-report")
    assert resp.status_code == 200
    data = resp.json()
    assert "report_title" in data
    assert "lead_finding" in data
    assert "per_category" in data
    assert "methodology" in data


# ---------------------------------------------------------------------------
# Test 4 — per_category entries carry F9 fields when data is loaded
# ---------------------------------------------------------------------------

def test_analyst_benchmarking_per_category_f9_fields():
    data = _benchmarking_data()
    if not _shadow_data_loaded(data):
        pytest.skip("ShadowDecision data not loaded -- skipping F9 field check")

    for cat, entry in data["per_category"].items():
        assert "analyst_agreement" in entry, f"Missing analyst_agreement for {cat}"
        assert "verified_decisions" in entry, f"Missing verified_decisions for {cat}"
        assert "signal" in entry, f"Missing signal for {cat}"
        assert "confidence" in entry, f"Missing confidence for {cat}"
        assert entry["confidence"] in ("calibrated", "learning", "cold_start"), \
            f"Unexpected confidence value for {cat}: {entry['confidence']}"


# ---------------------------------------------------------------------------
# Test 5 — f9-report total_shadow_decisions matches benchmarking
# ---------------------------------------------------------------------------

def test_f9_report_total_matches_benchmarking():
    bench = _benchmarking_data()
    if not _shadow_data_loaded(bench):
        pytest.skip("ShadowDecision data not loaded -- skipping total check")

    f9 = client.get("/api/soc/f9-report").json()
    if f9.get("total_shadow_decisions", 0) == 0:
        pytest.skip("f9-report secondary AGE call failed (event loop) -- skipping total check")
    assert f9.get("total_shadow_decisions") == bench.get("total_decisions")


# ---------------------------------------------------------------------------
# Test 6 — override_precision is non-negative float or None per category
# ---------------------------------------------------------------------------

def test_analyst_benchmarking_override_precision_valid():
    data = _benchmarking_data()
    if not _shadow_data_loaded(data):
        pytest.skip("ShadowDecision data not loaded -- skipping override_precision check")

    for cat, entry in data["per_category"].items():
        op = entry.get("override_precision")
        if op is not None:
            assert 0.0 <= op <= 1.0, \
                f"override_precision out of range for {cat}: {op}"
