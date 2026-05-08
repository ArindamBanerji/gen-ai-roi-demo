from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.admin import _CsvConnector, _write_manifest_to_graph


SAMPLE_ALERTS = [
    {
        "SystemAlertId": "A-001",
        "AlertName": "Brute Force",
        "AlertSeverity": "High",
        "CompromisedEntity": "john@firm.com",
        "TimeGenerated": "2026-03-01T10:00:00Z",
        "ProviderName": "Sentinel",
        "Description": "Multiple failed logins from 192.168.1.100",
        "asset_hostname": "SRV-WEB-01",
    },
    {
        "SystemAlertId": "A-002",
        "AlertName": "Data Upload",
        "AlertSeverity": "Medium",
        "CompromisedEntity": "jane@firm.com",
        "TimeGenerated": "2026-03-02T14:00:00Z",
        "ProviderName": "Sentinel",
        "Description": "Large upload to external storage",
        "asset_hostname": "LAPTOP-JANE",
    },
]


def test_csv_mode_with_two_alerts_success():
    client = TestClient(app)
    with patch(
        "app.routers.admin._write_manifest_to_graph",
        new=AsyncMock(
            return_value={
                "nodes_attempted": 5,
                "nodes_written": 5,
                "relationships_attempted": 3,
                "relationships_written": 3,
                "errors": [],
                "errors_count": 0,
            }
        ),
    ):
        response = client.post(
            "/api/admin/ingest",
            json={"mode": "csv", "alerts": SAMPLE_ALERTS, "limit": 100},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["mode"] == "csv"
    assert data["stages"]
    assert data["manifest"]["node_count"] >= 1
    assert data["graph_write"]["nodes_written"] == 5
    assert "recommended_config" in data


def test_unknown_mode_returns_400():
    client = TestClient(app)
    response = client.post(
        "/api/admin/ingest",
        json={"mode": "bogus", "alerts": []},
    )

    assert response.status_code == 400
    assert "mode must be one of" in response.json()["detail"]


def test_empty_alerts_success_zero_imports_or_clear_behavior():
    client = TestClient(app)
    with patch(
        "app.routers.admin._write_manifest_to_graph",
        new=AsyncMock(
            return_value={
                "nodes_attempted": 0,
                "nodes_written": 0,
                "relationships_attempted": 0,
                "relationships_written": 0,
                "errors": [],
                "errors_count": 0,
            }
        ),
    ):
        response = client.post(
            "/api/admin/ingest",
            json={"mode": "csv", "alerts": []},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["alerts_imported"] == 0
    assert data["manifest"]["node_count"] == 0


def test_recommended_config_keys():
    client = TestClient(app)
    with patch(
        "app.routers.admin._write_manifest_to_graph",
        new=AsyncMock(return_value={"skipped": False, "errors": [], "errors_count": 0}),
    ):
        response = client.post(
            "/api/admin/ingest",
            json={"mode": "csv", "alerts": SAMPLE_ALERTS, "write_graph": False},
        )

    assert response.status_code == 200
    config = response.json()["recommended_config"]
    assert "learning_recommended" in config
    assert "sigma_mean" in config
    assert "tau_initial" in config


@pytest.mark.asyncio
async def test_graph_write_helper_uses_idempotent_pattern():
    manifest = SimpleNamespace(
        nodes=[
            {
                "id": "alert:A-001",
                "type": "Alert",
                "alert_id": "A-001",
                "alert_type": "O'Hare Login",
                "severity": "high",
            },
            {"id": "alerttype:login", "type": "AlertType", "name": "Login"},
        ],
        relationships=[
            {
                "type": "CLASSIFIED_AS",
                "from": "alert:A-001",
                "to": "alerttype:login",
            }
        ],
    )
    graph_client = SimpleNamespace(run_query=AsyncMock(return_value=[]))

    summary = await _write_manifest_to_graph(manifest, graph_client)

    assert summary["nodes_written"] == 2
    assert summary["relationships_written"] == 1
    queries = [call.args[0] for call in graph_client.run_query.call_args_list]
    joined = "\n".join(queries)
    assert "MERGE" not in joined
    assert "$" not in joined
    assert "MATCH (n:Alert {id:" in joined
    assert "MATCH (src:Alert {id:" in joined
    assert "MATCH (dst:AlertType {id:" in joined
    assert "O\\'Hare Login" in joined


def test_pipeline_failure_returns_structured_failure(monkeypatch):
    from ci_platform.onboarding.pipeline import PipelineResult, StageResult

    async def fake_run(self, days_back=30, limit=10000, progress_callback=None, shadow_decisions=None):
        return PipelineResult(
            success=False,
            stages=[
                StageResult(
                    stage="extract",
                    success=False,
                    duration_seconds=0.0,
                    records_in=0,
                    records_out=0,
                    details={"error": "connection refused"},
                )
            ],
            total_duration_seconds=0.0,
            alerts_imported=0,
            entities_resolved=0,
            redactions_applied=0,
            load_manifest=None,
            recommended_config=None,
        )

    from ci_platform.onboarding.pipeline import OnboardingPipeline

    monkeypatch.setattr(OnboardingPipeline, "run", fake_run)
    client = TestClient(app)
    response = client.post(
        "/api/admin/ingest",
        json={"mode": "csv", "alerts": SAMPLE_ALERTS},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["stages"][0]["details"]["error"] == "connection refused"


@pytest.mark.asyncio
async def test_limit_truncates_alerts():
    connector = _CsvConnector(SAMPLE_ALERTS)

    alerts = await connector.fetch_alerts(since=None, limit=1)

    assert alerts == SAMPLE_ALERTS[:1]


def test_sentinel_mode_rejected_without_credentials_or_unwired():
    client = TestClient(app)
    response = client.post(
        "/api/admin/ingest",
        json={"mode": "sentinel"},
    )

    assert response.status_code == 400
    assert "sentinel_config is required" in response.json()["detail"]
