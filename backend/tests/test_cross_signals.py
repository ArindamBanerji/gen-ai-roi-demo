import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.main import app
from app.routers import platform

client = TestClient(app)


def test_cross_signals_endpoint_returns_200():
    response = client.get("/api/platform/cross-signals")

    assert response.status_code == 200
    payload = response.json()
    assert "signals" in payload
    assert "total" in payload
    assert "active" in payload
    assert "acknowledged" in payload
    assert "note" in payload


def test_cross_signals_has_three_fixture_signals():
    response = client.get("/api/platform/cross-signals")

    payload = response.json()
    assert payload["total"] == 3
    assert len(payload["signals"]) == 3
    assert [signal["signal_id"] for signal in payload["signals"]] == [
        "XC-SOC-S2P-001",
        "XC-SOC-S2P-002",
        "XC-SOC-S2P-003",
    ]


def test_cross_signals_active_count_correct():
    response = client.get("/api/platform/cross-signals")

    payload = response.json()
    assert payload["active"] == 2
    assert payload["acknowledged"] == 1


def test_cross_signals_evidence_structure_valid():
    response = client.get("/api/platform/cross-signals")

    rhine_stahl = response.json()["signals"][0]
    assert rhine_stahl["signal_id"] == "XC-SOC-S2P-001"
    assert rhine_stahl["confidence"] == 0.82
    assert rhine_stahl["status"] == "active"
    assert len(rhine_stahl["evidence"]) == 3
    for evidence in rhine_stahl["evidence"]:
        assert {"decision_id", "category", "action", "outcome", "days_ago", "user"} <= set(evidence)


def test_cross_signals_route_is_platform_not_s2p_preview():
    platform_response = client.get("/api/platform/cross-signals")
    wrong_namespace_response = client.get("/api/s2p/preview/cross-signals")

    assert platform_response.status_code == 200
    assert wrong_namespace_response.status_code == 404


def test_cross_signals_missing_fixture_fail_open(monkeypatch, tmp_path):
    missing_path = tmp_path / "missing_cross_copilot_signals.json"
    monkeypatch.setattr(platform, "_FIXTURE_PATH", missing_path)
    platform._reset_cross_signal_cache()

    try:
        response = client.get("/api/platform/cross-signals")
    finally:
        platform._reset_cross_signal_cache()

    assert response.status_code == 200
    payload = response.json()
    assert payload["signals"] == []
    assert payload["total"] == 0
    assert payload["active"] == 0
    assert payload["acknowledged"] == 0


def test_source_domains_deterministic():
    response = client.get("/api/platform/cross-signals")

    payload = response.json()
    assert payload["source_domains"] == sorted({"SOC"})
