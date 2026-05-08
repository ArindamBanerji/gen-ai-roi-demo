import os
import sys
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.routers import discoveries_router


class FakeDiscoveryService:
    ttl_seconds = 60
    SUPPORTED_DOMAINS = {"soc"}

    def __init__(self):
        self.cached = None
        self.refresh = AsyncMock(return_value=self._envelope(hit=False))
        self.get_summary = AsyncMock(return_value={
            "domain": "soc",
            "source_domains": ["soc"],
            "total": 1,
            "high_count": 1,
            "medium_count": 0,
            "low_count": 0,
            "top_discoveries": [],
            "cache": {"hit": False, "stale": False, "ttl_seconds": 60},
            "errors": [],
        })

    def validate_domain(self, domain):
        if domain not in self.SUPPORTED_DOMAINS:
            raise ValueError(f"Unsupported discovery domain: {domain}")
        return domain

    def get_discoveries(self, domain="soc"):
        return self.cached

    @staticmethod
    def _envelope(hit=False):
        return {
            "domain": "soc",
            "source_domains": ["soc"],
            "generated_at": "2026-01-01T00:00:00Z",
            "as_of_epoch_ms": 1743638400000,
            "cache": {"hit": hit, "stale": False, "ttl_seconds": 60},
            "discoveries": [],
            "total": 0,
            "errors": [],
        }


@pytest.fixture
def fake_service(monkeypatch):
    service = FakeDiscoveryService()
    monkeypatch.setattr(discoveries_router, "discovery_service", service)
    return service


@pytest.fixture
def client(fake_service):
    app = FastAPI()
    app.include_router(discoveries_router.router, prefix="/api")
    return TestClient(app, raise_server_exceptions=False)


def test_get_discoveries_returns_200_for_default_soc(client, fake_service):
    response = client.get("/api/discoveries")

    assert response.status_code == 200
    body = response.json()
    assert body["domain"] == "soc"
    assert body["source_domains"] == ["soc"]
    assert "discoveries" in body
    assert "total" in body
    assert "cache" in body
    fake_service.refresh.assert_awaited_once()


def test_get_discoveries_returns_fresh_cache(client, fake_service):
    fake_service.cached = FakeDiscoveryService._envelope(hit=True)

    response = client.get("/api/discoveries?domain=soc")

    assert response.status_code == 200
    assert response.json()["cache"]["hit"] is True
    fake_service.refresh.assert_not_awaited()


def test_get_discoveries_unsupported_domain_returns_400(client):
    response = client.get("/api/discoveries?domain=s2p")

    assert response.status_code == 400
    assert "Unsupported discovery domain: s2p" in response.json()["detail"]


def test_post_refresh_returns_200_for_soc(client, fake_service):
    response = client.post("/api/discoveries/refresh?domain=soc")

    assert response.status_code == 200
    assert response.json()["domain"] == "soc"
    fake_service.refresh.assert_awaited_once()


def test_post_refresh_unsupported_domain_returns_400(client):
    response = client.post("/api/discoveries/refresh?domain=s2p")

    assert response.status_code == 400
    assert "Unsupported discovery domain: s2p" in response.json()["detail"]


def test_get_summary_returns_counts(client, fake_service):
    response = client.get("/api/discoveries/summary?domain=soc")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["high_count"] == 1
    fake_service.get_summary.assert_awaited_once()


def test_get_summary_unsupported_domain_returns_400(client):
    response = client.get("/api/discoveries/summary?domain=s2p")

    assert response.status_code == 400
    assert "Unsupported discovery domain: s2p" in response.json()["detail"]


def test_graph_failure_returns_empty_discoveries_not_500(client, fake_service):
    fake_service.refresh.side_effect = RuntimeError("graph unavailable")

    response = client.get("/api/discoveries?domain=soc")

    assert response.status_code == 200
    body = response.json()
    assert body["discoveries"] == []
    assert body["total"] == 0
    assert body["errors"] == ["graph unavailable"]


def test_discovery_routes_declare_response_models():
    by_path_method = {}
    for route in discoveries_router.router.routes:
        for method in route.methods or []:
            by_path_method[(route.path, method)] = route

    assert by_path_method[("/discoveries", "GET")].response_model is discoveries_router.DiscoveryEnvelopeModel
    assert by_path_method[("/discoveries/refresh", "POST")].response_model is discoveries_router.DiscoveryEnvelopeModel
    assert by_path_method[("/discoveries/summary", "GET")].response_model is discoveries_router.DiscoverySummaryModel


def test_main_router_mount_exposes_api_discoveries():
    from app.main import app

    paths = {route.path for route in app.router.routes}

    assert "/api/discoveries" in paths
    assert "/api/discoveries/refresh" in paths
    assert "/api/discoveries/summary" in paths
