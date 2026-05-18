from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


def test_app_uses_lifespan_not_on_event():
    source = Path("app/main.py").read_text(encoding="utf-8")

    assert "@app.on_event" not in source
    assert "on_event(" not in source
    assert "lifespan=lifespan" in source
    assert "@asynccontextmanager" in source


def test_startup_logic_runs(monkeypatch):
    import app.main as main_module

    calls: list[str] = []

    async def fake_startup():
        calls.append("startup")

    async def fake_shutdown():
        calls.append("shutdown")

    monkeypatch.setattr(main_module, "startup_event", fake_startup)
    monkeypatch.setattr(main_module, "shutdown_event", fake_shutdown)

    with TestClient(main_module.app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert calls == ["startup"]

    assert calls == ["startup", "shutdown"]
