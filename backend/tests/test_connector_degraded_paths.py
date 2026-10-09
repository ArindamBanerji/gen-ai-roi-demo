"""SS-10 connector outage and partial-write regression tests."""

from unittest.mock import AsyncMock

import pytest

from app.connectors import crowdstrike_mock, greynoise, pulsedive


def failing_graph():
    graph = AsyncMock()
    graph.run_query.side_effect = RuntimeError("graph unavailable")
    return graph


@pytest.mark.asyncio
async def test_greynoise_fallback_marks_graph_unavailable(monkeypatch):
    monkeypatch.delenv("GREYNOISE_API_KEY", raising=False)
    monkeypatch.setattr(greynoise, "DEMO_IPS", ["1.2.3.4"])
    monkeypatch.setattr(greynoise, "HARDCODED_FALLBACK", {
        "1.2.3.4": {"ip": "1.2.3.4", "classification": "unknown"},
    })
    monkeypatch.setattr(greynoise, "graph_client", failing_graph())
    result = await greynoise.GreyNoiseConnector().refresh()
    assert result.enrichment_summary[0]["fallback_used"] is True
    assert result.enrichment_summary[0]["fallback_reason"] == "graph_unavailable"


@pytest.mark.asyncio
async def test_pulsedive_fallback_marks_graph_unavailable(monkeypatch):
    monkeypatch.delenv("PULSEDIVE_API_KEY", raising=False)
    ioc = {"value": "example.test", "context": "test"}
    monkeypatch.setattr(pulsedive, "DEMO_IOCS", [ioc])
    monkeypatch.setattr(pulsedive, "ALERT_IOC_MAP", {})
    monkeypatch.setattr(pulsedive, "HARDCODED_FALLBACK", {
        "example.test": {"value": "example.test", "severity": "low"},
    })
    monkeypatch.setattr(pulsedive, "graph_client", failing_graph())
    result = await pulsedive.PulsediveConnector().refresh()
    assert result.enrichment_summary[0]["fallback_used"] is True
    assert result.enrichment_summary[0]["fallback_reason"] == "graph_unavailable"


@pytest.mark.asyncio
async def test_crowdstrike_reports_failed_writes(monkeypatch):
    monkeypatch.setattr(crowdstrike_mock, "graph_client", failing_graph())
    result = await crowdstrike_mock.CrowdStrikeMockConnector().refresh()
    assert result.write_failures > 0
    assert result.to_dict()["write_failures"] == result.write_failures
    assert result.to_dict()["degraded"] is True


@pytest.mark.asyncio
async def test_greynoise_reports_failed_writes(monkeypatch):
    monkeypatch.delenv("GREYNOISE_API_KEY", raising=False)
    monkeypatch.setattr(greynoise, "DEMO_IPS", ["1.2.3.4"])
    monkeypatch.setattr(greynoise, "HARDCODED_FALLBACK", {
        "1.2.3.4": {"ip": "1.2.3.4", "classification": "unknown"},
    })
    monkeypatch.setattr(greynoise, "graph_client", failing_graph())
    result = await greynoise.GreyNoiseConnector().refresh()
    assert result.write_failures > 0


@pytest.mark.asyncio
async def test_pulsedive_reports_failed_writes(monkeypatch):
    monkeypatch.delenv("PULSEDIVE_API_KEY", raising=False)
    ioc = {"value": "example.test", "context": "test"}
    monkeypatch.setattr(pulsedive, "DEMO_IOCS", [ioc])
    monkeypatch.setattr(pulsedive, "ALERT_IOC_MAP", {})
    monkeypatch.setattr(pulsedive, "HARDCODED_FALLBACK", {
        "example.test": {"value": "example.test", "severity": "low"},
    })
    monkeypatch.setattr(pulsedive, "graph_client", failing_graph())
    result = await pulsedive.PulsediveConnector().refresh()
    assert result.write_failures > 0

