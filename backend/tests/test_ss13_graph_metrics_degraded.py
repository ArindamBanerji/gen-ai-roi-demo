"""SS-13 graph-backed outage contracts."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest


class BrokenGraph:
    async def run_query(self, *_args, **_kwargs):
        raise RuntimeError("graph unavailable")


@pytest.mark.asyncio
async def test_enrichment_summary_graph_failure():
    from app.routers import graph
    with patch.object(graph, "graph_client", BrokenGraph()):
        payload = await graph.get_enrichment_summary()
    assert payload["indicators"] == []
    assert payload["enrichment_available"] is False
    assert payload["total"] == 0
    assert payload["indicators_available"] is False
    assert payload["degraded"] is True


@pytest.mark.asyncio
async def test_enrichment_secondary_throws_before_assignment():
    from app.routers import graph
    from app.services.threat_indicator import ThreatIndicatorService

    primary = {"consensus_severity": "high", "indicator": "1.2.3.4"}
    healthy_graph = SimpleNamespace(run_query=AsyncMock(return_value=[{}]))
    with patch.object(graph, "graph_client", healthy_graph), \
         patch.object(graph, "_build_view", return_value=primary), \
         patch.object(
             ThreatIndicatorService,
             "get_all_indicators",
             new=AsyncMock(side_effect=RuntimeError("secondary down")),
         ):
        payload = await graph.get_enrichment_summary()

    assert payload["indicators"] == [primary]
    assert payload["total"] == 1
    assert payload["indicators_available"] is False
    assert payload["threat_indicators"] == {"total": 0, "by_type": {}, "by_severity": {}}
    assert payload["degraded"] is True


@pytest.mark.asyncio
async def test_enrichment_secondary_returns_failure_sentinel():
    from app.routers import graph
    from app.services.threat_indicator import ThreatIndicatorService

    healthy_graph = SimpleNamespace(run_query=AsyncMock(return_value=[]))
    with patch.object(graph, "graph_client", healthy_graph), patch.object(
        ThreatIndicatorService,
        "get_all_indicators",
        new=AsyncMock(return_value=None),
    ):
        payload = await graph.get_enrichment_summary()

    assert payload["indicators_available"] is False
    assert payload["threat_indicators"]["total"] == 0
    assert payload["degraded"] is True


@pytest.mark.asyncio
async def test_enrichment_valid_zero_secondary():
    from app.routers import graph
    from app.services.threat_indicator import ThreatIndicatorService

    healthy_graph = SimpleNamespace(run_query=AsyncMock(return_value=[]))
    with patch.object(graph, "graph_client", healthy_graph), patch.object(
        ThreatIndicatorService,
        "get_all_indicators",
        new=AsyncMock(return_value={"total": 0, "by_type": {}, "by_severity": {}, "indicators": []}),
    ):
        payload = await graph.get_enrichment_summary()

    assert payload["indicators_available"] is True
    assert payload["threat_indicators"]["total"] == 0
    assert payload["degraded"] is False


def test_enrichment_http_200_not_500():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.routers import graph
    from app.services.threat_indicator import ThreatIndicatorService

    healthy_graph = SimpleNamespace(run_query=AsyncMock(return_value=[]))
    with patch.object(graph, "graph_client", healthy_graph), patch.object(
        ThreatIndicatorService,
        "get_all_indicators",
        new=AsyncMock(side_effect=RuntimeError("secondary down")),
    ):
        response = TestClient(app).get("/api/graph/enrichment/summary")

    assert response.status_code == 200
    assert response.json()["indicators_available"] is False


@pytest.mark.parametrize(
    "run_query",
    [
        AsyncMock(side_effect=RuntimeError("primary graph down")),
        AsyncMock(return_value=None),
    ],
    ids=["raises", "returns-none"],
)
def test_enrichment_primary_failure_is_typed_http_200(run_query):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.routers import graph

    with patch.object(
        graph, "graph_client", SimpleNamespace(run_query=run_query)
    ):
        response = TestClient(app).get("/api/graph/enrichment/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["indicators"] == []
    assert payload["total"] == 0
    assert payload["by_severity"] == {
        "critical": 0, "high": 0, "medium": 0, "low": 0, "unknown": 0,
    }
    assert payload["threat_indicators"] == {
        "total": 0, "by_type": {}, "by_severity": {},
    }
    assert payload["enrichment_available"] is False
    assert payload["indicators_available"] is False
    assert payload["degraded"] is True
    assert all(value is not None for value in payload.values())


@pytest.mark.asyncio
async def test_compounding_metrics_graph_failure():
    from app.routers import metrics
    with patch.object(metrics, "graph_client", BrokenGraph()):
        payload = await metrics.get_compounding_metrics(weeks=2)
    assert payload["weekly_trend"] == []
    assert payload["weekly_available"] is False
    assert payload["degraded"] is True


@pytest.mark.asyncio
async def test_board_export_graph_failure():
    from app.routers import metrics
    with patch.object(metrics, "graph_client", BrokenGraph()):
        payload = await metrics.get_board_export()
    assert payload["metrics"]["decisions_made"] == 0
    assert payload["export_data_available"] is False


@pytest.mark.asyncio
async def test_economics_graph_failure():
    from app.routers import metrics
    with patch.object(metrics, "graph_client", BrokenGraph()):
        payload = await metrics.get_economics()
    assert payload["decisions"]["total"] == 0
    assert payload["economics_available"] is False


@pytest.mark.asyncio
async def test_refresh_threat_intel_persistence_failure():
    from app.routers import graph
    with patch.object(graph, "refresh_threat_intel", AsyncMock(return_value={"indicators_ingested": 1, "relationships_created": 0, "source": "test"})), patch.object(graph, "graph_client", SimpleNamespace(run_query=AsyncMock(return_value=[{"ioc_value": "1.2.3.4"}]))):
        with patch("app.services.threat_indicator.ThreatIndicatorService.upsert_indicator", AsyncMock(return_value=None)):
            payload = await graph.refresh_threat_intel_endpoint()
    assert payload["indicators_persisted"] == 0
    assert payload["persistence_failures"] == 1


@pytest.mark.asyncio
async def test_seed_graph_partial_failure():
    from app import graph_schema
    report = {"healthy": True, "counts": {}, "issues": []}
    data = {key: [] for key in ("alerts", "demo_alerts", "decisions", "users", "assets", "attack_patterns", "threat_indicators", "campaigns")}
    data["alerts"] = [{
        "alert_id": "alert-edge-failure",
        "category": "credential_access",
        "severity": "HIGH",
        "timestamp_epoch": 1,
        "user_id": "user-edge-failure",
    }]
    class Client:
        async def ensure_graph(self): pass
        async def run_query(self, query, *_args, **_kwargs):
            if "CREATE (alert)-[:INVOLVES]->(u)" in query:
                raise RuntimeError("edge failure")
            return []
    with patch.object(graph_schema, "_validate_seed_data"), patch.object(graph_schema, "_validate_json"), patch.object(graph_schema, "verify_graph", AsyncMock(return_value=report)), patch.object(graph_schema, "_configured_graph_store", return_value=None):
        import json, tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as fh:
            json.dump(data, fh); path = fh.name
        result = await graph_schema.seed_graph(path, client=Client(), graph_name="test_graph", profile="test")
    assert result["failed_count"] == 1
    assert result["seeding_complete"] is False


@pytest.mark.asyncio
async def test_indicators_for_alert_graph_failure():
    from app.services.threat_indicator import ThreatIndicatorService
    assert await ThreatIndicatorService.get_indicators_for_alert("a", BrokenGraph()) is None


@pytest.mark.asyncio
async def test_all_indicators_graph_failure():
    from app.services.threat_indicator import ThreatIndicatorService
    assert await ThreatIndicatorService.get_all_indicators(BrokenGraph()) is None


@pytest.mark.asyncio
async def test_upsert_indicator_graph_failure():
    from app.services.threat_indicator import ThreatIndicatorService
    assert await ThreatIndicatorService.upsert_indicator("ip", "1.2.3.4", "test", "high", "", BrokenGraph()) is None


@pytest.mark.asyncio
async def test_orchestrator_query_rows_failure():
    from app.domains.soc.orchestrator import _query_rows
    assert await _query_rows(BrokenGraph(), "MATCH (n) RETURN n") is None


def test_evidence_provider_graph_failure():
    from app.evidence_provider import SOCEvidenceProvider
    provider = SOCEvidenceProvider(BrokenGraph(), "alert-1")
    assert provider.read_evidence("d", 0, "asset_criticality") is None
    assert provider.last_evidence_available is False


@pytest.mark.asyncio
async def test_intervention_audit_write_failure():
    from app.framework.intervention_controls import InterventionControls
    scorer = SimpleNamespace(freeze=lambda: None)
    controls = InterventionControls(BrokenGraph(), scorer, None, SimpleNamespace())
    result = await controls.freeze_all_learning("test", "outage test")
    assert result["audit_persisted"] is False
    assert result["type"] == "freeze_all_learning"
