import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.main import app
from app.services.servicenow_mock import get_servicenow_mock


@pytest.fixture(autouse=True)
def reset_servicenow_mock():
    get_servicenow_mock().reset()
    yield
    get_servicenow_mock().reset()


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def _payload(decision_id: str = "DEC-ROUTER-1", confidence: float = 0.91):
    return {
        "decision_id": decision_id,
        "alert_id": "ALERT-ROUTER-1",
        "alert_type": "Impossible travel",
        "category": "credential_access",
        "confidence": confidence,
        "nl_explanation": "Escalation confirmed.",
        "analyst_id": "analyst_a",
    }


def test_create_incident_endpoint(client):
    response = client.post("/api/servicenow/create-incident", json=_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["incident_number"] == "INC0047000"
    assert body["decision_id"] == "DEC-ROUTER-1"
    assert body["urgency"] == 1


def test_list_incidents_endpoint(client):
    client.post("/api/servicenow/create-incident", json=_payload("DEC-1"))
    client.post("/api/servicenow/create-incident", json=_payload("DEC-2"))

    response = client.get("/api/servicenow/incidents")

    assert response.status_code == 200
    assert [item["decision_id"] for item in response.json()] == ["DEC-2", "DEC-1"]


def test_get_incident_endpoint(client):
    client.post("/api/servicenow/create-incident", json=_payload("DEC-1"))

    response = client.get("/api/servicenow/incident/DEC-1")

    assert response.status_code == 200
    assert response.json()["incident_number"] == "INC0047000"


def test_get_incident_404(client):
    response = client.get("/api/servicenow/incident/missing")

    assert response.status_code == 404


def test_update_status_endpoint(client):
    client.post("/api/servicenow/create-incident", json=_payload("DEC-1"))

    response = client.post(
        "/api/servicenow/update-status",
        json={"decision_id": "DEC-1", "status": "Resolved"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Resolved"


def test_update_status_invalid(client):
    response = client.post(
        "/api/servicenow/update-status",
        json={"decision_id": "DEC-1", "status": "Closed"},
    )

    assert response.status_code == 422


def test_create_incident_validation(client):
    high = client.post(
        "/api/servicenow/create-incident",
        json=_payload(confidence=1.01),
    )
    low = client.post(
        "/api/servicenow/create-incident",
        json=_payload(confidence=-0.01),
    )

    assert high.status_code == 422
    assert low.status_code == 422
