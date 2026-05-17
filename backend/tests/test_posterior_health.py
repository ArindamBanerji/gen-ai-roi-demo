from fastapi.testclient import TestClient

from app.main import app
from app.services import rl_engine
from app.services.posterior_store import PosteriorStore


client = TestClient(app, raise_server_exceptions=False)


def teardown_function():
    rl_engine.reset_rl_state()


def _posterior_component(response):
    body = response.json()
    return body["components"]["posterior_store"]


def test_health_endpoint_includes_posterior_field(monkeypatch):
    monkeypatch.setattr(PosteriorStore, "health_check", lambda self: {"healthy": True})

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert "components" in body
    assert body["components"]["posterior_store"]["healthy"] is True


def test_health_returns_200_even_when_posterior_unhealthy(monkeypatch):
    monkeypatch.setattr(
        PosteriorStore,
        "health_check",
        lambda self: {"healthy": False, "error": "boom"},
    )

    response = client.get("/health")

    assert response.status_code == 200
    component = _posterior_component(response)
    assert component["healthy"] is False
    assert component["error"] == "boom"


def test_posterior_health_check_returns_dict(monkeypatch):
    monkeypatch.setattr(PosteriorStore, "_ping_storage", lambda self: None)

    result = PosteriorStore("postgresql://unit-test").health_check()

    assert isinstance(result, dict)
    assert result["healthy"] is True


def test_posterior_healthy_with_valid_storage(monkeypatch):
    calls = []

    def fake_ping(self):
        calls.append(self._dsn)

    monkeypatch.setattr(PosteriorStore, "_ping_storage", fake_ping)

    result = PosteriorStore("postgresql://unit-test").health_check()

    assert result == {"healthy": True}
    assert calls == ["postgresql://unit-test"]


def test_posterior_unhealthy_with_bad_storage(monkeypatch):
    def fake_ping(self):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(PosteriorStore, "_ping_storage", fake_ping)

    result = PosteriorStore("postgresql://bad-storage").health_check()

    assert result["healthy"] is False
    assert "connection refused" in result["error"]
