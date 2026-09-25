from __future__ import annotations

from fastapi.testclient import TestClient

from app import main
from app.routers import platform


client = TestClient(main.app)


def test_g037_production_cross_signals_graph_or_unavailable(monkeypatch):
    monkeypatch.setenv("SOC_PROFILE", "production")
    assert platform._load_cross_signals() == []


def test_g037_production_domain_table_graph_or_unavailable(monkeypatch):
    monkeypatch.setenv("SOC_PROFILE", "production")
    data = platform._load_domain_table()
    assert data.get("available") is False
    assert data.get("domains") == []


def test_g037_production_warm_start_graph_or_unavailable(monkeypatch):
    monkeypatch.setenv("SOC_PROFILE", "production")
    data = platform._load_warm_start_evidence()
    assert data.get("available") is False
    assert data.get("warm_start_evidence") == []


def test_g037_demo_preserves_all_loaders(monkeypatch):
    monkeypatch.setenv("SOC_PROFILE", "test")
    platform.reset_platform_caches()
    assert platform._load_cross_signals()
    assert platform._load_domain_table().get("domains")
    assert platform._load_warm_start_evidence().get("warm_start_evidence")
    assert platform._load_chain_credit_demo().get("chain_credits")
    assert platform._load_rl_reward_demo().get("reward_breakdown")
    assert platform._load_rl_exploration_demo().get("exploration_log")


def test_g037_rl_demo_endpoints_namespaced(monkeypatch):
    monkeypatch.setenv("SOC_PROFILE", "production")
    for path in (
        "/api/platform/chain-credit-demo",
        "/api/platform/rl-reward-demo",
        "/api/platform/rl-exploration-demo",
    ):
        assert client.get(path).status_code == 404

