"""
PB-03 Sentinel production integration tests.

All tests use mocks or empty local configuration. They do not call Microsoft
Sentinel, OAuth endpoints, KQL APIs, or a real AGE instance.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


class _FakeHealthConnector:
    def __init__(self, configured=True, token="fake-token", error=None):
        self.configured = configured
        self.token = token
        self.error = error
        self.tenant_id = "tenant-secret"
        self.client_id = "client-secret"
        self.client_secret = "super-secret"

    def is_configured(self):
        return self.configured

    async def get_token(self):
        if self.error:
            raise self.error
        return self.token


def _clear_sentinel_env(monkeypatch):
    for name in (
        "SENTINEL_TENANT_ID",
        "SENTINEL_CLIENT_ID",
        "SENTINEL_CLIENT_SECRET",
        "SENTINEL_WORKSPACE_ID",
    ):
        monkeypatch.delenv(name, raising=False)


def test_sentinel_health_not_configured(monkeypatch):
    _clear_sentinel_env(monkeypatch)
    import app.connectors.sentinel_real as sentinel_real

    monkeypatch.setattr(sentinel_real, "_connector", None)

    resp = client.get("/api/admin/sentinel-health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "not_configured"
    assert body["token_valid"] is False


def test_sentinel_health_configured_mock(monkeypatch):
    fake = _FakeHealthConnector(configured=True, token="fake-token")
    monkeypatch.setattr(
        "app.connectors.sentinel_real.get_sentinel_connector",
        lambda: fake,
    )
    monkeypatch.setattr("app.routers.admin.importlib_util.find_spec", lambda name: object())

    resp = client.get("/api/admin/sentinel-health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "configured"
    assert body["token_valid"] is True


def test_sentinel_health_auth_error(monkeypatch):
    fake = _FakeHealthConnector(
        configured=True,
        error=RuntimeError("auth failed for super-secret"),
    )
    monkeypatch.setattr(
        "app.connectors.sentinel_real.get_sentinel_connector",
        lambda: fake,
    )
    monkeypatch.setattr("app.routers.admin.importlib_util.find_spec", lambda name: object())

    resp = client.get("/api/admin/sentinel-health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "auth_error"
    assert body["token_valid"] is False
    assert "super-secret" not in resp.text


def test_sentinel_health_msal_missing(monkeypatch):
    fake = _FakeHealthConnector(configured=True, token="fake-token")
    monkeypatch.setattr(
        "app.connectors.sentinel_real.get_sentinel_connector",
        lambda: fake,
    )
    monkeypatch.setattr("app.routers.admin.importlib_util.find_spec", lambda name: None)

    resp = client.get("/api/admin/sentinel-health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "auth_error"
    assert body["token_valid"] is False
    assert "msal not installed" in body["error"]


def _install_analyze_patches(monkeypatch, action="escalate", confidence=0.9):
    import app.routers.triage as triage_router

    alert = {
        "alert_id": "SENT-ALERT-1",
        "id": "SENT-ALERT-1",
        "alert_type": "anomalous_login",
        "severity": "high",
        "source_location": "10.0.1.54",
        "user_id": "user-1",
        "asset_id": "asset-1",
        "status": "pending",
        "incident_id": "INC-SENT-1",
    }
    context = {
        "alert_type": "anomalous_login",
        "user_id": "user-1",
        "nodes_consulted": 4,
        "mfa_completed": True,
    }
    graph = MagicMock()
    graph.get_alert = AsyncMock(return_value=alert)
    graph.get_security_context = AsyncMock(return_value=context)
    graph.run_query = AsyncMock(return_value=[])
    graph.get_sequence_count = AsyncMock(return_value=0)
    graph.get_cross_category_count = AsyncMock(return_value=0)
    monkeypatch.setattr(triage_router, "graph_client", graph)
    monkeypatch.setattr(
        triage_router,
        "compute_factor_vector",
        AsyncMock(return_value=np.array([0.2, 0.3, 0.4, 0.1, 0.5, 0.6])),
    )
    monkeypatch.setattr(
        triage_router.narrator,
        "generate_reasoning",
        AsyncMock(return_value="mock Sentinel reasoning"),
    )
    monkeypatch.setattr(
        triage_router,
        "record_decision",
        AsyncMock(return_value={"hash": "hash-1", "chain_index": 1}),
    )
    monkeypatch.setattr(triage_router.event_bus, "emit", AsyncMock())
    monkeypatch.setattr(triage_router, "get_graph_data", AsyncMock(return_value={"nodes": [], "edges": []}))

    scoring = SimpleNamespace(
        action_name=action,
        confidence=confidence,
        entropy=0.1,
        confidence_gap=0.7,
        probabilities=np.array([0.9, 0.05, 0.03, 0.02]),
    )
    scorer = MagicMock()
    scorer.score.return_value = scoring
    scorer.tau = 0.1

    learning_state = SimpleNamespace(decision_count=1)
    monkeypatch.setattr("app.services.gae_state.get_profile_scorer", lambda: scorer)
    monkeypatch.setattr("app.services.gae_state.init_learning_state", lambda: None)
    monkeypatch.setattr("app.services.gae_state.get_learning_state", lambda: learning_state)
    monkeypatch.setattr(triage_router, "get_learning_state", lambda: learning_state)

    class _NarrativeProvider:
        def generate(self, *_args, **_kwargs):
            return {"summary": "mock narrative"}

    monkeypatch.setattr(triage_router, "get_narrative_provider", lambda: _NarrativeProvider())
    return graph


def test_sentinel_alert_through_analyze(monkeypatch):
    _install_analyze_patches(monkeypatch, action="monitor", confidence=0.8)

    resp = client.post("/api/alert/analyze", json={"alert_id": "SENT-ALERT-1"})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["alert"]["incident_id"] == "INC-SENT-1"
    assert body["recommendation"]["action"] == "monitor"
    assert body["recommendation"]["confidence"] == pytest.approx(0.8)


def test_write_back_trigger_reachable(monkeypatch):
    _install_analyze_patches(monkeypatch, action="escalate", confidence=0.9)

    pushed = []

    class _WriteBackConnector:
        async def push_incident_update(self, **kwargs):
            pushed.append(kwargs)
            return {"success": True}

    created = []

    def fake_create_task(coro):
        created.append(coro)
        coro.close()
        return SimpleNamespace(done=lambda: True)

    monkeypatch.setattr(
        "app.connectors.sentinel_real.get_sentinel_connector",
        lambda: _WriteBackConnector(),
    )
    monkeypatch.setattr(asyncio, "create_task", fake_create_task)

    resp = client.post("/api/alert/analyze", json={"alert_id": "SENT-ALERT-1"})

    assert resp.status_code == 200, resp.text
    assert len(created) == 1
    assert pushed == []


@pytest.mark.asyncio
async def test_sentinel_graceful_degradation_empty_env(monkeypatch):
    _clear_sentinel_env(monkeypatch)
    from app.connectors.sentinel_real import SentinelRealConnector

    connector = SentinelRealConnector()

    assert connector.is_configured() is False
    assert await connector.fetch_alerts() == []


@pytest.mark.asyncio
async def test_sentinel_disposition_mapping_all_actions(monkeypatch):
    from app.connectors.sentinel_real import SentinelRealConnector

    payloads = []

    class _FakeResponse:
        status_code = 204
        text = ""

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def patch(self, url, headers=None, json=None):
            payloads.append(json)
            return _FakeResponse()

    connector = SentinelRealConnector()
    connector.tenant_id = "tenant"
    connector.client_id = "client"
    connector.client_secret = "secret"
    connector.workspace_id = "workspace"
    monkeypatch.setattr(connector, "get_token", AsyncMock(return_value="token"))
    monkeypatch.setattr("httpx.AsyncClient", _FakeAsyncClient)

    expected = {
        "escalate": "truePositive",
        "investigate": "truePositive",
        "suppress": "falsePositive",
        "monitor": "benignPositive",
    }
    for action in expected:
        result = await connector.push_incident_update(
            incident_id=f"INC-{action}",
            action=action,
            confidence=0.91,
            decision_id=f"DEC-{action}",
        )
        assert result["success"] is True

    assert [p["classification"] for p in payloads] == list(expected.values())


@pytest.mark.asyncio
async def test_poller_disabled_by_default(monkeypatch):
    from app.services import sentinel_poller

    monkeypatch.delenv("SENTINEL_POLLING_ENABLED", raising=False)
    await sentinel_poller.stop_sentinel_poller()

    status = await sentinel_poller.start_sentinel_poller()

    assert status == {"started": False, "reason": "disabled"}
    assert sentinel_poller._poller is None


@pytest.mark.asyncio
async def test_poller_module_start_is_idempotent(monkeypatch):
    from app.services import sentinel_poller

    class _FetchConnector:
        def is_configured(self):
            return True

        async def fetch_alerts(self):
            return []

    monkeypatch.setenv("SENTINEL_POLLING_ENABLED", "true")
    monkeypatch.setenv("SENTINEL_POLL_INTERVAL_SECONDS", "0.01")
    monkeypatch.setattr(
        "app.connectors.sentinel_real.get_sentinel_connector",
        lambda: _FetchConnector(),
    )
    await sentinel_poller.stop_sentinel_poller()

    try:
        first_status = await sentinel_poller.start_sentinel_poller()
        first_poller = sentinel_poller._poller
        first_task = first_poller._task

        second_status = await sentinel_poller.start_sentinel_poller()

        assert first_status["started"] is True
        assert second_status == {"started": True, "reason": "already_running"}
        assert sentinel_poller._poller is first_poller
        assert sentinel_poller._poller._task is first_task
        assert first_poller.is_running is True
    finally:
        await sentinel_poller.stop_sentinel_poller()


@pytest.mark.asyncio
async def test_poller_module_stop_clears_handle(monkeypatch):
    from app.services import sentinel_poller

    class _FetchConnector:
        def is_configured(self):
            return True

        async def fetch_alerts(self):
            return []

    monkeypatch.setenv("SENTINEL_POLLING_ENABLED", "true")
    monkeypatch.setenv("SENTINEL_POLL_INTERVAL_SECONDS", "0.01")
    monkeypatch.setattr(
        "app.connectors.sentinel_real.get_sentinel_connector",
        lambda: _FetchConnector(),
    )
    await sentinel_poller.stop_sentinel_poller()

    await sentinel_poller.start_sentinel_poller()
    assert sentinel_poller._poller is not None

    await sentinel_poller.stop_sentinel_poller()

    assert sentinel_poller._poller is None


@pytest.mark.asyncio
async def test_poller_calls_fetch_when_enabled(monkeypatch):
    from app.services import sentinel_poller

    called = asyncio.Event()

    class _FetchConnector:
        def is_configured(self):
            return True

        async def fetch_alerts(self):
            called.set()
            return [{"alert_id": "SENT-1"}]

    monkeypatch.setenv("SENTINEL_POLLING_ENABLED", "true")
    monkeypatch.setenv("SENTINEL_POLL_INTERVAL_SECONDS", "0.01")
    monkeypatch.setattr(
        "app.connectors.sentinel_real.get_sentinel_connector",
        lambda: _FetchConnector(),
    )
    await sentinel_poller.stop_sentinel_poller()

    try:
        status = await sentinel_poller.start_sentinel_poller()
        assert status["started"] is True
        await asyncio.wait_for(called.wait(), timeout=1.0)
    finally:
        await sentinel_poller.stop_sentinel_poller()

    assert sentinel_poller._poller is None


@pytest.mark.asyncio
async def test_poller_handles_errors_and_stops_cleanly(caplog):
    from app.services.sentinel_poller import SentinelPoller

    class _ErrorConnector:
        def is_configured(self):
            return True

        async def fetch_alerts(self):
            raise RuntimeError("fetch failed")

    poller = SentinelPoller(connector=_ErrorConnector(), interval_seconds=0.01)
    caplog.set_level("WARNING")

    summary = await poller.poll_once()
    await poller.stop()

    assert summary["errors"] == 1
    assert "Sentinel poll failed" in caplog.text


@pytest.mark.asyncio
async def test_poller_ingestion_errors_do_not_crash_poll_once(caplog):
    from app.services.sentinel_poller import SentinelPoller

    class _FetchConnector:
        def is_configured(self):
            return True

        async def fetch_alerts(self):
            return [{"alert_id": "SENT-INGEST-1"}]

    def _bad_ingest(_alert):
        raise RuntimeError("boom")

    poller = SentinelPoller(
        connector=_FetchConnector(),
        interval_seconds=0.01,
        ingest_func=_bad_ingest,
    )
    caplog.set_level("WARNING")

    summary = await poller.poll_once()

    assert summary["errors"] == 1
    assert summary["ingested"] == 0
    assert "Sentinel alert ingestion failed" in caplog.text


@pytest.mark.asyncio
async def test_poller_run_forever_continues_after_ingestion_error():
    from app.services.sentinel_poller import SentinelPoller

    second_ingest = asyncio.Event()
    fetch_count = 0
    ingest_count = 0

    class _FetchConnector:
        def is_configured(self):
            return True

        async def fetch_alerts(self):
            nonlocal fetch_count
            fetch_count += 1
            return [{"alert_id": f"SENT-CYCLE-{fetch_count}"}]

    def _flaky_ingest(_alert):
        nonlocal ingest_count
        ingest_count += 1
        if ingest_count == 1:
            raise RuntimeError("boom")
        second_ingest.set()

    poller = SentinelPoller(
        connector=_FetchConnector(),
        interval_seconds=0.01,
        ingest_func=_flaky_ingest,
    )
    assert await poller.start() is True
    try:
        await asyncio.wait_for(second_ingest.wait(), timeout=1.0)
    finally:
        await poller.stop()

    assert fetch_count >= 2
    assert ingest_count >= 2
