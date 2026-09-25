import os
import sys
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.routers import discoveries_router


PAIR = {
    "PL-SOC-5-KILLCHAIN-A": {
        "alert_id": "PL-SOC-5-KILLCHAIN-A",
        "alert_type": "anomalous_login",
        "category": "credential_access",
        "severity": "low",
        "user_id": "user-admin-003",
        "asset_id": "asset-dc-west-01",
    },
    "PL-SOC-5-KILLCHAIN-B": {
        "alert_id": "PL-SOC-5-KILLCHAIN-B",
        "alert_type": "lateral_movement",
        "category": "lateral_movement",
        "severity": "low",
        "user_id": "user-admin-003",
        "asset_id": "asset-dc-west-01",
    },
}

pytestmark = pytest.mark.age


@pytest.fixture
def client(age_graph, monkeypatch):
    """The router reads the same seeded AGE records it receives in production."""
    for alert in PAIR.values():
        age_graph.alert(alert_id=alert["alert_id"], **{
            key: value for key, value in alert.items() if key != "alert_id"
        })
    monkeypatch.setattr(discoveries_router, "graph_client", age_graph.client)
    app = FastAPI()
    app.include_router(discoveries_router.router, prefix="/api")
    return TestClient(app, raise_server_exceptions=False)


def test_kill_chain_detected(client):
    response = client.post(
        "/api/alert/cross-correlate",
        json={"alert_ids": ["PL-SOC-5-KILLCHAIN-A", "PL-SOC-5-KILLCHAIN-B"]},
    )

    assert response.status_code == 200
    correlation = response.json()["correlation"]
    assert correlation["kill_chain_detected"] is True
    assert correlation["kill_chain_pattern"] == "credential_access → lateral_movement"


def test_no_kill_chain(client):
    response = client.post(
        "/api/alert/cross-correlate",
        json={"alert_ids": ["PL-SOC-5-KILLCHAIN-A", "PL-SOC-5-KILLCHAIN-A"]},
    )

    assert response.status_code == 200
    correlation = response.json()["correlation"]
    assert correlation["kill_chain_detected"] is False
    assert correlation["combined_severity"] is None


def test_shared_entities(client):
    response = client.post(
        "/api/alert/cross-correlate",
        json={"alert_ids": ["PL-SOC-5-KILLCHAIN-A", "PL-SOC-5-KILLCHAIN-B"]},
    )

    assert response.json()["correlation"]["shared_entities"] == [
        "user-admin-003",
        "asset-dc-west-01",
    ]


def test_severity_elevation(client):
    response = client.post(
        "/api/alert/cross-correlate",
        json={"alert_ids": ["PL-SOC-5-KILLCHAIN-A", "PL-SOC-5-KILLCHAIN-B"]},
    )

    correlation = response.json()["correlation"]
    assert correlation["alert_1"]["severity_alone"] == "low"
    assert correlation["alert_2"]["severity_alone"] == "low"
    assert correlation["combined_severity"] == "critical"


def test_single_alert_error(client):
    response = client.post(
        "/api/alert/cross-correlate",
        json={"alert_ids": ["PL-SOC-5-KILLCHAIN-A"]},
    )

    assert response.status_code == 422
