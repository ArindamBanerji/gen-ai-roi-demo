"""
Tests for app/connectors/sentinel_mock.py
"""
import json
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.connectors.sentinel_mock import SentinelMockConnector, _iso_to_epoch_ms


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_ALERT = {
    "alert_id":        "SENT-001",
    "day":             5,
    "category":        "credential_access",
    "shift":           "night",
    "severity":        "high",
    "timestamp":       "2026-03-15T02:30:00Z",
    "alert_type":      "Unfamiliar sign-in properties",
    "source_location": "Singapore",
    "asset_id":        "LAPTOP-JSMITH",
    "user_id":         "jsmith@company.com",
}

SAMPLE_ALERT_2 = {
    "alert_id":        "SENT-002",
    "day":             12,
    "category":        "lateral_movement",
    "shift":           "day",
    "severity":        "critical",
    "timestamp":       "2026-03-22T14:00:00Z",
    "alert_type":      "Impossible travel activity",
    "source_location": "London",
    "asset_id":        "SRV-DB-PROD-01",
    "user_id":         "mchen@company.com",
}


def _make_tmp_json(alerts: list) -> str:
    """Write alerts list to a temp file and return its path."""
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    )
    json.dump(alerts, f)
    f.close()
    return f.name


# ---------------------------------------------------------------------------
# Test 1 — normalize() maps Sentinel fields to SOC schema correctly
# ---------------------------------------------------------------------------

def test_normalize_maps_sentinel_fields():
    connector = SentinelMockConnector()
    result = connector.normalize(SAMPLE_ALERT)

    # Identity mapping
    assert result["id"]              == "SENT-001",                     f"id: {result['id']}"
    assert result["alert_type"]      == "Unfamiliar sign-in properties", f"alert_type: {result['alert_type']}"
    assert result["severity"]        == "high",                         f"severity: {result['severity']}"
    assert result["category"]        == "credential_access",            f"category: {result['category']}"
    assert result["source_location"] == "Singapore",                    f"source_location: {result['source_location']}"
    assert result["asset_id"]        == "LAPTOP-JSMITH",                f"asset_id: {result['asset_id']}"
    assert result["user_id"]         == "jsmith@company.com",           f"user_id: {result['user_id']}"
    assert result["day"]             == 5,                              f"day: {result['day']}"
    assert result["shift"]           == "night",                        f"shift: {result['shift']}"

    # Derived / fixed fields
    assert result["status"]          == "pending",            f"status: {result['status']}"
    assert result["source"]          == "sentinel_mock_v1",   f"source: {result['source']}"

    # timestamp → timestamp_epoch (ISO 2026-03-15T02:30:00Z → epoch ms)
    expected_epoch = _iso_to_epoch_ms("2026-03-15T02:30:00Z")
    assert result["timestamp_epoch"] == expected_epoch, (
        f"timestamp_epoch: got {result['timestamp_epoch']}, expected {expected_epoch}"
    )
    # Sanity: epoch is a positive integer in ms range (> 1_000_000_000_000)
    assert isinstance(result["timestamp_epoch"], int)
    assert result["timestamp_epoch"] > 1_000_000_000_000


# ---------------------------------------------------------------------------
# Test 2 — stream() yields dicts with correct keys
# ---------------------------------------------------------------------------

def test_stream_yields_alerts():
    path = _make_tmp_json([SAMPLE_ALERT, SAMPLE_ALERT_2])
    try:
        connector = SentinelMockConnector()
        n = connector.load(path)
        assert n == 2

        results = list(connector.stream())
        assert len(results) == 2

        required_keys = {
            "id", "alert_type", "severity", "category",
            "source_location", "asset_id", "user_id",
            "timestamp_epoch", "day", "shift", "status", "source",
        }
        for r in results:
            missing = required_keys - set(r.keys())
            assert not missing, f"Missing keys in normalized alert: {missing}"

        # day_filter excludes SENT-002 (day=12) when range is 0-10
        filtered = list(connector.stream(day_filter=(0, 10)))
        assert len(filtered) == 1
        assert filtered[0]["id"] == "SENT-001"
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# Test 3 — dry-run: stream() and normalize() make no HTTP calls
# ---------------------------------------------------------------------------

def test_dry_run_no_post():
    """
    In dry-run mode the CLI runner only calls stream()/normalize().
    Verify the connector itself makes zero network calls by confirming
    it has no httpx/requests import and normalize() returns a plain dict.
    """
    import importlib
    import app.connectors.sentinel_mock as mod

    # The module must not import httpx or requests (no HTTP client)
    src = open(mod.__file__).read()
    assert "import httpx" not in src,    "sentinel_mock.py must not import httpx"
    assert "import requests" not in src, "sentinel_mock.py must not import requests"
    assert "urllib.request" not in src,  "sentinel_mock.py must not use urllib.request"

    # normalize() returns a plain dict — no side effects, no I/O
    connector = SentinelMockConnector()
    result = connector.normalize(SAMPLE_ALERT)
    assert isinstance(result, dict)

    # stream() is a generator — calling it does not open any connections
    import types
    connector._alerts = [SAMPLE_ALERT]
    gen = connector.stream()
    assert isinstance(gen, types.GeneratorType), "stream() must be a generator"
    first = next(gen)
    assert isinstance(first, dict)
