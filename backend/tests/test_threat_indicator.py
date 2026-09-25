"""
Tests for Phase 7: ThreatIndicatorService and alert-level threat intel endpoints.

Coverage:
  test_upsert_creates_indicator           -- upsert returns a non-empty ID
  test_upsert_idempotent                  -- two upserts with same ioc_value return same ID (MERGE)
  test_get_indicators_for_alert           -- indicators linked to an alert are returned
  test_get_all_indicators                 -- get_all returns total, by_type, by_severity
  test_threat_intel_alert_endpoint        -- GET /api/soc/threat-intel/ALERT-7824 returns indicators list
  test_enrichment_summary_includes_indicators -- GET /api/graph/enrichment/summary has threat_indicators key
"""

import asyncio
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.services.threat_indicator import ThreatIndicatorService


# ---------------------------------------------------------------------------
# FakeAGE helpers
# ---------------------------------------------------------------------------

_SAMPLE_INDICATOR = {
    "id":        "ti-fake-001",
    "name":      "DarkHook Phishing Campaign",
    "ioc_type":  "domain",
    "ioc_value": "microsofft-support.com",
    "source":    "pulsedive",
    "severity":  "high",
    "last_seen": "2026-03-16T10:00:00",
    "created_at":"2026-03-15T10:00:00",
}


# ---------------------------------------------------------------------------
# Test 1: upsert returns a non-empty ID
# ---------------------------------------------------------------------------

@pytest.mark.age
def test_upsert_creates_indicator(age_graph):
    """upsert_indicator returns a non-empty string ID."""
    graph = age_graph.client

    result_id = asyncio.run(
        ThreatIndicatorService.upsert_indicator(
            indicator_type="domain",
            indicator_value="microsofft-support.com",
            source="pulsedive",
            severity="high",
            name="DarkHook Phishing Campaign",
            graph_service=graph,
        )
    )

    assert result_id
    assert age_graph.query("MATCH (ti:ThreatIndicator) RETURN ti.id AS id") == [{"id": result_id}]


# ---------------------------------------------------------------------------
# Test 2: MERGE idempotent — same IOC twice returns same ID
# ---------------------------------------------------------------------------

@pytest.mark.age
def test_upsert_idempotent(age_graph):
    """Two upserts for the same ioc_value both return the same ID (MERGE behaviour)."""
    graph = age_graph.client

    id_first  = asyncio.run(
        ThreatIndicatorService.upsert_indicator(
            indicator_type="ip", indicator_value="10.0.3.15",
            source="greynoise", severity="critical",
            name="Known C2 IP", graph_service=graph,
        )
    )
    id_second = asyncio.run(
        ThreatIndicatorService.upsert_indicator(
            indicator_type="ip", indicator_value="10.0.3.15",
            source="greynoise", severity="critical",
            name="Known C2 IP", graph_service=graph,
        )
    )

    assert id_first
    assert age_graph.query("MATCH (ti:ThreatIndicator) RETURN count(ti) AS n") == [{"n": 1}]
    assert id_first == id_second, "MERGE must return the same ID on re-insert"


# ---------------------------------------------------------------------------
# Test 3: get_indicators_for_alert returns linked indicators
# ---------------------------------------------------------------------------

@pytest.mark.age
def test_get_indicators_for_alert(age_graph):
    """get_indicators_for_alert returns at least 1 indicator for ALERT-7824."""
    graph = age_graph.client
    age_graph.alert(alert_id="ALERT-7824")
    asyncio.run(ThreatIndicatorService.upsert_indicator("domain", "microsofft-support.com", "pulsedive", "high", "DarkHook", graph))
    asyncio.run(ThreatIndicatorService.link_to_alert("microsofft-support.com", "domain", "ALERT-7824", graph))

    result = asyncio.run(
        ThreatIndicatorService.get_indicators_for_alert("ALERT-7824", graph)
    )

    assert len(result) >= 1, f"Expected at least 1 indicator, got {len(result)}"
    assert result[0]["indicator"] == "microsofft-support.com", result[0]


# ---------------------------------------------------------------------------
# Test 4: get_all_indicators returns expected structure
# ---------------------------------------------------------------------------

@pytest.mark.age
def test_get_all_indicators(age_graph):
    """get_all_indicators returns total, by_type, by_severity dicts."""
    rows = [
        {**_SAMPLE_INDICATOR, "indicator_type": "domain", "severity": "high"},
        {**_SAMPLE_INDICATOR, "id": "ti-002", "indicator": "evil.com",
         "indicator_type": "domain", "severity": "critical"},
        {**_SAMPLE_INDICATOR, "id": "ti-003", "indicator": "10.0.0.1",
         "indicator_type": "ip", "severity": "high"},
    ]
    graph = age_graph.client
    for row in rows:
        asyncio.run(ThreatIndicatorService.upsert_indicator(row["indicator_type"], row.get("indicator", row["ioc_value"]), row["source"], row["severity"], row["name"], graph))

    result = asyncio.run(ThreatIndicatorService.get_all_indicators(graph))

    assert result["total"] == 3, f"Expected 3, got {result['total']}"
    assert "by_type"     in result, result
    assert "by_severity" in result, result
    assert result["by_type"].get("domain") == 2, result["by_type"]
    assert result["by_type"].get("ip")     == 1, result["by_type"]
    assert result["by_severity"].get("high")     == 2, result["by_severity"]
    assert result["by_severity"].get("critical") == 1, result["by_severity"]


# ---------------------------------------------------------------------------
# Test 5: GET /api/soc/threat-intel/{alert_id}
# ---------------------------------------------------------------------------

def test_threat_intel_alert_endpoint():
    """GET /api/soc/threat-intel/ALERT-7824 returns indicators list."""
    from app.main import app

    async def fake_run_query(query, params=None):
        if "ThreatIndicator" in query:
            return [_SAMPLE_INDICATOR]
        return []

    with patch("app.routers.soc.graph_client") as mock_graph:
        mock_graph.run_query = fake_run_query
        client = TestClient(app)
        resp = client.get("/api/soc/threat-intel/ALERT-7824")

    assert resp.status_code == 200, f"Status {resp.status_code}: {resp.text[:300]}"
    data = resp.json()
    assert "indicators"    in data, f"Missing indicators: {data}"
    assert "total_matches" in data, f"Missing total_matches: {data}"
    assert data["alert_id"] == "ALERT-7824"
    assert isinstance(data["indicators"], list)


# ---------------------------------------------------------------------------
# Test 6: GET /api/graph/enrichment/summary includes threat_indicators key
# ---------------------------------------------------------------------------

def test_enrichment_summary_includes_indicators():
    """GET /api/graph/enrichment/summary response includes threat_indicators key."""
    from app.main import app

    async def fake_run_query(query, params=None):
        # ThreatIndicatorService query — returns sample indicator
        if "ThreatIndicator" in query and "DETACH DELETE" not in query:
            return [_SAMPLE_INDICATOR]
        # Existing ThreatIntel enrichment queries — return empty to keep response simple
        return []

    with patch("app.routers.graph.graph_client") as mock_graph:
        mock_graph.run_query = fake_run_query
        client = TestClient(app)
        resp = client.get("/api/graph/enrichment/summary")

    assert resp.status_code == 200, f"Status {resp.status_code}: {resp.text[:300]}"
    data = resp.json()
    assert "threat_indicators" in data, (
        f"Missing threat_indicators in summary. Keys: {list(data.keys())}"
    )
    ti = data["threat_indicators"]
    assert "total"       in ti, ti
    assert "by_type"     in ti, ti
    assert "by_severity" in ti, ti
