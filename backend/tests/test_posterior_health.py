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
    assert body["status"] == "ok"
    assert body["ready"] is True
    assert body["domain"] == "soc"
    assert body["version"] == app.version
    assert "graph_status" in body
    assert "components" in body
    assert body["components"]["posterior_store"]["healthy"] is True


def test_health_returns_503_when_graph_probe_unhealthy(monkeypatch):
    monkeypatch.setattr(
        PosteriorStore,
        "health_check",
        lambda self: {"healthy": False, "error": "boom"},
    )

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["ready"] is False
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


def test_health_probes_owned_graph_without_promoting_memory_to_production():
    from copilot_sdk.backend.health_builder import build_graph_health
    from copilot_sdk.config import GraphConfig
    from copilot_sdk.graph import InMemoryGraphStore

    config = GraphConfig.load("soc")
    graph = InMemoryGraphStore(domain="soc")
    store = PosteriorStore(config, graph_store=graph)
    assert store.graph_primary is graph
    before = build_graph_health(store, config, "soc")
    assert before["node_count"] == 0
    graph.write_decision("soc", "credential_access", "monitor", 0.8, {"f0": 0.5})
    after = build_graph_health(store, config, "soc")
    assert after["node_count"] == 1
    assert after["graph_connected"] is True
    assert after["graph_backend"] == "memory"
    assert after["ready"] is False
