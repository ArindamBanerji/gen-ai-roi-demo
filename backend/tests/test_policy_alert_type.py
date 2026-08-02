from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app


class _PolicyResult:
    has_conflict = False
    conflicting_policies = []
    policies_applied = []

    def model_dump(self):
        return {
            "alert_id": "ALERT-IT-005",
            "has_conflict": False,
            "policies_applied": [],
            "conflicting_policies": [],
            "resolution": None,
        }


def test_policy_check_resolves_known_alert_type():
    captured = {}

    async def fake_run_query(query):
        captured["query"] = query
        return [{
            "alert_type": "insider_threat",
            "category": "insider_threat",
            "source_location": "Office",
            "user_risk_score": 0.72,
            "detected_asset_criticality": "high",
            "involved_asset_criticality": None,
            "travel_destination": None,
            "known_campaign_signature": False,
        }]

    def fake_detect(alert_id, context):
        captured["alert_id"] = alert_id
        captured["context"] = context
        return _PolicyResult()

    mock_neo4j = SimpleNamespace(run_query=AsyncMock(side_effect=fake_run_query))

    with patch("app.routers.triage.graph_client", mock_neo4j), \
         patch("app.routers.triage.detect_policy_conflicts", side_effect=fake_detect):
        client = TestClient(app)
        response = client.get("/api/alert/policy-check?alert_id=ALERT-IT-005")

    assert response.status_code == 200
    assert captured["alert_id"] == "ALERT-IT-005"
    assert captured["context"]["alert_type"] == "insider_threat"
    assert "$alert_id" not in captured["query"]
    assert "ALERT-IT-005" in captured["query"]


def test_policy_check_unknown_only_for_missing_type():
    captured = {}

    async def fake_run_query(query):
        captured["query"] = query
        return [{
            "alert_type": None,
            "category": None,
            "source_location": "Office",
            "user_risk_score": None,
            "detected_asset_criticality": None,
            "involved_asset_criticality": None,
            "travel_destination": None,
            "known_campaign_signature": False,
        }]

    def fake_detect(alert_id, context):
        captured["alert_id"] = alert_id
        captured["context"] = context
        return _PolicyResult()

    mock_neo4j = SimpleNamespace(run_query=AsyncMock(side_effect=fake_run_query))

    with patch("app.routers.triage.graph_client", mock_neo4j), \
         patch("app.routers.triage.detect_policy_conflicts", side_effect=fake_detect):
        client = TestClient(app)
        response = client.get("/api/alert/policy-check?alert_id=ALERT-MISSING-TYPE")

    assert response.status_code == 200
    assert captured["alert_id"] == "ALERT-MISSING-TYPE"
    assert captured["context"]["alert_type"] == "unknown"
    assert "$alert_id" not in captured["query"]
    assert "ALERT-MISSING-TYPE" in captured["query"]
