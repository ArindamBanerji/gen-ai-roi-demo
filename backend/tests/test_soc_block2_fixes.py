from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import servicenow_router
from app.services.servicenow_mock import get_servicenow_mock


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(servicenow_router.router)
    return TestClient(app)


def _payload() -> dict[str, object]:
    return {
        "decision_id": "D-BLOCK2-001",
        "alert_id": "A-BLOCK2-001",
        "confidence": 0.91,
    }


def test_servicenow_create_demo_mode(monkeypatch):
    monkeypatch.setenv("SOC_DEMO_MODE", "true")
    get_servicenow_mock().reset()
    response = _client().post("/api/servicenow/create-incident", json=_payload())
    assert response.status_code == 200
    assert response.json()["simulation"] is True


def test_servicenow_create_production_mode(monkeypatch):
    monkeypatch.delenv("SOC_DEMO_MODE", raising=False)
    response = _client().post("/api/servicenow/create-incident", json=_payload())
    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "reason": "ServiceNow integration not configured",
        "mode": "production",
    }


def test_servicenow_list_demo(monkeypatch):
    monkeypatch.setenv("SOC_DEMO_MODE", "1")
    get_servicenow_mock().reset()
    _client().post("/api/servicenow/create-incident", json=_payload())
    response = _client().get("/api/servicenow/incidents")
    assert response.status_code == 200
    assert response.json()[0]["simulation"] is True


def test_incident_response_has_simulation_flag(monkeypatch):
    monkeypatch.setenv("SOC_DEMO_MODE", "yes")
    get_servicenow_mock().reset()
    body = _client().post("/api/servicenow/create-incident", json=_payload()).json()
    assert "simulation" in body
    assert body["simulation"] is True


def test_no_pytest_detection_main():
    source = Path("app/main.py").read_text(encoding="utf-8")
    assert "PYTEST_CURRENT_TEST" not in source
    assert "SOC_PROFILE" in source


def test_no_pytest_detection_rl():
    source = Path("app/services/rl_engine.py").read_text(encoding="utf-8")
    assert "PYTEST_CURRENT_TEST" not in source
    assert "SOC_PROFILE" in source


def test_no_pytest_detection_posterior():
    source = Path("app/services/posterior_store.py").read_text(encoding="utf-8")
    assert "PYTEST_CURRENT_TEST" not in source
    assert "SOC_PROFILE" in source


def test_profile_from_soc_profile_env(monkeypatch):
    from app.services.posterior_store import _soc_profile

    monkeypatch.setenv("SOC_PROFILE", "demo")
    assert _soc_profile() == "demo"
    monkeypatch.setenv("SOC_PROFILE", "unexpected")
    assert _soc_profile() == "production"
