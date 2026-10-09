"""Deterministic cold-start coverage; these tests need no live backend."""

from __future__ import annotations

import asyncio
import json
from http.client import IncompleteRead
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import conftest
from app.middleware.startup_gate import StartupGateMiddleware


@pytest.mark.parametrize("case", ["ready", "not_ready", "missing", "warming", "stale", "malformed"])
def test_readiness_requires_complete_health_contract(case: str, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "ready": case != "not_ready",
        "graph_status": {"components": {"decisions": "ready", "topology": "ready", "learning_restore": "ready"}},
        "learning_counts_stale": case == "stale",
    }
    if case == "missing":
        del payload["graph_status"]
    elif case == "warming":
        payload["graph_status"] = {"components": {"decisions": "ready", "topology": "ready", "learning_restore": "initializing"}}
    elif case == "malformed":
        payload["graph_status"] = None
    response = SimpleNamespace(status=200, read=lambda: json.dumps(payload).encode())
    opener = MagicMock()
    opener.return_value.__enter__.return_value = response
    monkeypatch.setattr(conftest.urllib.request, "urlopen", opener)
    monkeypatch.setenv("SOC_BACKEND_URL", "http://example.invalid:8123/")
    assert conftest._backend_is_ready() is (case == "ready")
    opener.assert_called_once_with("http://example.invalid:8123/api/health", timeout=5.0)


@pytest.mark.parametrize("error", [OSError("offline"), ValueError("bad JSON"), IncompleteRead(b"partial")])
def test_readiness_probe_failure_returns_false(error: Exception, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(conftest.urllib.request, "urlopen", MagicMock(side_effect=error))
    assert conftest._backend_is_ready() is False


def test_health_wait_polls_until_hydrated(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    clock = [0.0]
    monkeypatch.setattr(conftest.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(conftest.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))
    probe = MagicMock(side_effect=[False, False, True])
    monkeypatch.setattr(conftest, "_backend_is_ready", probe)
    conftest._wait_until_backend_ready()
    assert probe.call_count == 3
    assert clock[0] == 1.0
    assert "Waiting for SOC backend readiness" in capsys.readouterr().out


def test_health_wait_timeout_warns_without_raising(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = [0.0]
    monkeypatch.setattr(conftest.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(conftest.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))
    monkeypatch.setattr(conftest, "_HEALTH_TIMEOUT", 1.0)
    probe = MagicMock(return_value=False)
    monkeypatch.setattr(conftest, "_backend_is_ready", probe)
    with pytest.warns(RuntimeWarning, match="did not become ready within 1s"):
        conftest._wait_until_backend_ready()
    assert clock[0] == 1.0
    assert probe.call_count == 2
    assert all(call.kwargs["timeout"] <= 1.0 for call in probe.call_args_list)


def test_session_fixture_does_not_wait_without_live_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    wait = MagicMock()
    monkeypatch.setattr(conftest, "_wait_until_backend_ready", wait)
    request = SimpleNamespace(session=SimpleNamespace(items=[SimpleNamespace(get_closest_marker=lambda name: None)]))
    fixture_body = getattr(conftest._wait_for_backend_ready, "__wrapped__")
    fixture_body(request)
    wait.assert_not_called()


def _gated_app() -> FastAPI:
    app = FastAPI()
    app.state.startup_complete = False
    app.add_middleware(StartupGateMiddleware)

    @app.get("/api/health")
    @app.get("/health")
    async def health() -> dict[str, bool]:
        return {"ready": False}

    @app.get("/business")
    async def business() -> dict[str, bool]:
        return {"served": True}

    return app


@pytest.mark.parametrize("path", ["/api/health", "/health"])
def test_startup_gate_middleware_allows_health(path: str) -> None:
    response = TestClient(_gated_app()).get(path)
    assert response.status_code == 200
    assert response.json() == {"ready": False}
    assert "retry-after" not in response.headers


def test_startup_gate_sets_retry_after_and_releases_on_completion() -> None:
    app = _gated_app()
    client = TestClient(app)
    blocked = client.get("/business")
    assert blocked.status_code == 503
    assert blocked.headers["retry-after"] == "2"
    assert blocked.json() == {"detail": "Backend initializing", "retry_after_seconds": 2}
    app.state.startup_complete = True
    ready = client.get("/business")
    assert ready.status_code == 200
    assert ready.json() == {"served": True}
    assert "retry-after" not in ready.headers


@pytest.mark.asyncio
async def test_real_lifespan_keeps_gate_closed_until_initialization_finishes(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.main as main

    app = _gated_app()
    started = asyncio.Event()
    finish = asyncio.Event()

    async def startup() -> None:
        started.set()
        await finish.wait()

    async def shutdown() -> None:
        pass

    monkeypatch.setattr(main, "startup_event", startup)
    monkeypatch.setattr(main, "shutdown_event", shutdown)
    lifecycle = main.lifespan(app)
    enter = asyncio.create_task(lifecycle.__aenter__())
    await started.wait()
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            assert (await client.get("/api/health")).status_code == 200
            assert (await client.get("/business")).status_code == 503
            finish.set()
            await enter
            assert (await client.get("/business")).status_code == 200
    finally:
        finish.set()
        await enter
        await lifecycle.__aexit__(None, None, None)
