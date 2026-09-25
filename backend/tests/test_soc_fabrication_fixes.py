import os
import sys
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.connectors import greynoise, pulsedive
from app.routers import admin, metrics, soc


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(metrics.router, prefix="/api")
    app.include_router(soc.router, prefix="/api")
    app.include_router(admin.router, prefix="/api")
    return app


def test_demo_reset_all_removed():
    response = TestClient(_app()).post("/api/demo/reset-all")
    assert response.status_code in {404, 405}


def test_admin_reset_requires_confirm():
    response = TestClient(_app()).post("/api/admin/reset", json={"mode": "soft"})
    assert response.status_code == 400


def test_admin_reset_with_confirm(monkeypatch):
    class FakeStateManager:
        def __init__(self, **_kwargs):
            pass

        async def soft_reset(self):
            return {"decision_count": 0}

    import app.services.state_manager as state_manager_module

    monkeypatch.setattr(state_manager_module, "StateManager", FakeStateManager)
    response = TestClient(_app()).post(
        "/api/admin/reset", json={"mode": "soft", "confirm": True}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "reset_complete"


def test_benchmark_returns_501():
    response = TestClient(_app()).get("/api/soc/benchmarking-level2")
    assert response.status_code == 501


def test_benchmark_response_says_not_available():
    body = TestClient(_app()).get("/api/soc/benchmarking-level2").json()
    assert body["status"] == "not_available"
    assert "completed A/B" in body["reason"]


def _metrics_history(age_graph, real_week=False):
    import time
    for index in range(9):
        age_graph.decision(correct=index < 6, origin="zero_day_synthetic", created_at=time.time() - 90 * 86400)
    if real_week:
        for index in range(2):
            aid = f"current-{index}"
            age_graph.alert(alert_id=aid)
            age_graph.decision(decision_id=aid, correct=index == 0)
            age_graph.query(f"MATCH (d:Decision {{decision_id: '{aid}'}}), (a:Alert {{alert_id: '{aid}'}}) CREATE (d)-[:DECIDED_ON]->(a) RETURN d")
    return age_graph.client


@pytest.mark.asyncio
@pytest.mark.age
async def test_compounding_metrics_empty_week_zero(monkeypatch, age_graph):
    monkeypatch.setattr(metrics, "graph_client", _metrics_history(age_graph, real_week=False))
    body = await metrics.get_compounding_metrics(weeks=1)
    assert body["weekly_trend"][0]["pattern_count"] == 0
    assert body["weekly_trend"][0]["auto_close_rate"] == 0.0


@pytest.mark.asyncio
@pytest.mark.age
async def test_compounding_metrics_historical_separate(monkeypatch, age_graph):
    monkeypatch.setattr(metrics, "graph_client", _metrics_history(age_graph, real_week=False))
    body = await metrics.get_compounding_metrics(weeks=1)
    assert body["weekly_trend"][0]["pattern_count"] == 0
    assert body["historical_context"]["pattern_count"] == 9


@pytest.mark.asyncio
@pytest.mark.age
async def test_compounding_metrics_real_data_preserved(monkeypatch, age_graph):
    monkeypatch.setattr(metrics, "graph_client", _metrics_history(age_graph, real_week=True))
    body = await metrics.get_compounding_metrics(weeks=1)
    assert body["weekly_trend"][0]["pattern_count"] == 2


def _threat_history(age_graph, existing):
    from support.campaign_graph import CampaignGraphProbe
    if existing:
        for alias, props in existing.items():
            age_graph.node("GreyNoiseEnrichment" if alias == "gn" else "ThreatIntel", **props)
    return CampaignGraphProbe(age_graph)


@pytest.mark.asyncio
@pytest.mark.age
async def test_greynoise_fallback_preserves_existing(monkeypatch, age_graph):
    monkeypatch.delenv("GREYNOISE_API_KEY", raising=False)
    monkeypatch.setattr(greynoise, "DEMO_IPS", ["1.2.3.4"])
    monkeypatch.setattr(greynoise, "graph_client", _threat_history(age_graph, {"gn": {"ip": "1.2.3.4", "classification": "benign"}}))
    result = await greynoise.GreyNoiseConnector().refresh()
    assert result.enrichment_summary[0]["classification"] == "benign"
    assert result.enrichment_summary[0]["stale"] is True


@pytest.mark.asyncio
@pytest.mark.age
async def test_greynoise_fallback_new_indicator_uses_static(monkeypatch, age_graph):
    monkeypatch.delenv("GREYNOISE_API_KEY", raising=False)
    monkeypatch.setattr(greynoise, "DEMO_IPS", ["103.15.42.17"])
    monkeypatch.setattr(greynoise, "graph_client", _threat_history(age_graph, None))
    result = await greynoise.GreyNoiseConnector().refresh()
    assert result.enrichment_summary[0]["source"] == "hardcoded_fallback"
    assert result.enrichment_summary[0]["stale"] is False


@pytest.mark.asyncio
@pytest.mark.age
async def test_pulsedive_fallback_preserves_existing(monkeypatch, age_graph):
    monkeypatch.delenv("PULSEDIVE_API_KEY", raising=False)
    ioc = {"value": "example.test", "context": "test"}
    monkeypatch.setattr(pulsedive, "DEMO_IOCS", [ioc])
    monkeypatch.setattr(pulsedive, "ALERT_IOC_MAP", {})
    monkeypatch.setattr(pulsedive, "HARDCODED_FALLBACK", {"example.test": {"value": "example.test", "severity": "low"}})
    monkeypatch.setattr(pulsedive, "graph_client", _threat_history(age_graph, {"ti": {"value": "example.test", "severity": "critical"}}))
    result = await pulsedive.PulsediveConnector().refresh()
    assert result.enrichment_summary[0]["severity"] == "critical"
    assert result.enrichment_summary[0]["stale"] is True


@pytest.mark.asyncio
@pytest.mark.age
async def test_staleness_marker_added(monkeypatch, age_graph):
    monkeypatch.delenv("GREYNOISE_API_KEY", raising=False)
    monkeypatch.setattr(greynoise, "DEMO_IPS", ["1.2.3.4"])
    graph = _threat_history(age_graph, {"gn": {"ip": "1.2.3.4"}})
    monkeypatch.setattr(greynoise, "graph_client", graph)
    result = await greynoise.GreyNoiseConnector().refresh()
    assert result.enrichment_summary[0]["stale_since"]
    assert any("stale_since" in query for query in graph.queries)
