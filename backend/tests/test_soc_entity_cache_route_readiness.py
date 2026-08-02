from __future__ import annotations

import inspect

import pytest

from app import main as app_main
from app.routers import triage
from ci_platform.copilot_core import (
    EntityCache,
    EntityCacheKey,
    EntityContextCacheAdapter,
)
from ci_platform.graph.age_client import AGEClient
from app.services.soc_context_split import split_soc_security_context


def test_soc_security_context_loader_is_not_yet_safe_as_entity_cache_value():
    """Current SOC context mixes one-shot alert fields with entity context."""

    source = inspect.getsource(AGEClient.get_security_context)

    assert "MATCH (alert:Alert {alert_id: $alert_id})" in source
    assert 'for key in ["alert", "asset", "user", "location"' in source
    assert "ctx.update(val)" in source


def test_default_soc_route_is_not_wired_to_entity_cache_yet():
    source = inspect.getsource(triage.analyze_alert)

    assert "_soc_get_security_context_for_analyze(alert_id)" in source
    assert "graph_client.get_sequence_count" in source
    assert "graph_client.get_cross_category_count" in source


def test_soc_context_split_classifies_and_recomposes_current_flat_shape():
    flat_context = {
        "alert_id": "ALERT-1",
        "id": "ALERT-1",
        "alert_type": "anomalous_login",
        "severity": "medium",
        "source_location": "10.0.0.5",
        "user_id": "user-1",
        "name": "Asha Rao",
        "department": "finance",
        "risk_level": "standard",
        "user_risk_score": 0.42,
        "mfa_completed": True,
        "asset_id": "asset-1",
        "hostname": "host-1",
        "criticality": "high",
        "sequence_count": 7,
        "cross_category_count": 2,
        "decision_id": "D-1",
        "outcome": "correct",
        "dk_state": "redacted",
        "l5_centroid": "C-1",
        "conservation_status": "GREEN",
        "campaign_id": "CAMP-1",
        "indicator": "1.2.3.4",
        "nodes_consulted": 47,
        "custom_context": "needs-decision",
    }

    split = split_soc_security_context(flat_context)

    assert split.fresh_alert == {
        "alert_id": "ALERT-1",
        "id": "ALERT-1",
        "alert_type": "anomalous_login",
        "severity": "medium",
        "source_location": "10.0.0.5",
    }
    assert split.stable_entity["user_id"] == "user-1"
    assert split.stable_entity["asset_id"] == "asset-1"
    assert split.non_cacheable["sequence_count"] == 7
    assert split.non_cacheable["campaign_id"] == "CAMP-1"
    assert split.ambiguous == {"custom_context": "needs-decision"}
    assert split.cache_key is not None
    assert split.cache_key.domain == "soc"
    assert split.cache_key.kind == "user"
    assert split.cache_key.identifier == "user-1"
    assert split.recompose_for_current_route() == flat_context


class _SecurityContextClient:
    def __init__(self, contexts):
        self.contexts = list(contexts)
        self.calls = 0

    async def get_security_context(self, _alert_id):
        context = self.contexts[min(self.calls, len(self.contexts) - 1)]
        self.calls += 1
        return dict(context)


@pytest.fixture(autouse=True)
def _reset_soc_entity_cache(monkeypatch):
    monkeypatch.delenv("USE_ENTITY_CACHE", raising=False)
    triage._soc_reset_entity_cache_for_tests()
    yield
    monkeypatch.delenv("USE_ENTITY_CACHE", raising=False)
    triage._soc_reset_entity_cache_for_tests()


@pytest.mark.asyncio
async def test_route_cache_flag_false_preserves_current_security_context_path(monkeypatch):
    flat_contexts = [
        {"alert_id": "ALERT-1", "user_id": "user-1", "user_risk_score": 0.1},
        {"alert_id": "ALERT-1", "user_id": "user-1", "user_risk_score": 0.2},
    ]
    fake_client = _SecurityContextClient(flat_contexts)
    monkeypatch.setattr(triage, "graph_client", fake_client)
    monkeypatch.setenv("USE_ENTITY_CACHE", "false")

    first = await triage._soc_get_security_context_for_analyze("ALERT-1")
    second = await triage._soc_get_security_context_for_analyze("ALERT-1")

    assert first == flat_contexts[0]
    assert second == flat_contexts[1]
    assert fake_client.calls == 2
    assert triage._soc_entity_cache_diagnostics()["size"] == 0


@pytest.mark.asyncio
async def test_route_cache_flag_true_recomposes_with_parity_and_cache_hit(monkeypatch):
    flat_context = {
        "alert_id": "ALERT-1",
        "alert_type": "anomalous_login",
        "severity": "medium",
        "user_id": "user-1",
        "user_risk_score": 0.42,
        "mfa_completed": True,
        "vpn_matches_location": True,
        "location": "Seattle",
        "asset_id": "asset-1",
        "criticality": "high",
        "nodes_consulted": 47,
    }
    fake_client = _SecurityContextClient([flat_context, flat_context])
    monkeypatch.setattr(triage, "graph_client", fake_client)
    monkeypatch.setenv("USE_ENTITY_CACHE", "true")

    first = await triage._soc_get_security_context_for_analyze("ALERT-1")
    second = await triage._soc_get_security_context_for_analyze("ALERT-1")

    assert first == flat_context
    assert second == flat_context
    diagnostics = triage._soc_entity_cache_diagnostics()
    assert diagnostics["enabled"] is True
    assert diagnostics["misses"] == 1
    assert diagnostics["hits"] == 1
    assert diagnostics["loads"] == 1
    assert diagnostics["size"] == 1


@pytest.mark.asyncio
async def test_route_cache_keeps_alert_subject_fresh_for_same_entity(monkeypatch):
    flat_contexts = [
        {
            "alert_id": "ALERT-1",
            "alert_type": "anomalous_login",
            "severity": "low",
            "user_id": "user-1",
            "user_risk_score": 0.42,
        },
        {
            "alert_id": "ALERT-2",
            "alert_type": "impossible_travel",
            "severity": "critical",
            "user_id": "user-1",
            "user_risk_score": 0.99,
        },
    ]
    fake_client = _SecurityContextClient(flat_contexts)
    monkeypatch.setattr(triage, "graph_client", fake_client)
    monkeypatch.setenv("USE_ENTITY_CACHE", "true")

    first = await triage._soc_get_security_context_for_analyze("ALERT-1")
    second = await triage._soc_get_security_context_for_analyze("ALERT-2")

    assert first["alert_id"] == "ALERT-1"
    assert first["severity"] == "low"
    assert second["alert_id"] == "ALERT-2"
    assert second["alert_type"] == "impossible_travel"
    assert second["severity"] == "critical"
    assert second["user_risk_score"] == 0.42
    assert triage._soc_entity_cache_diagnostics()["hits"] == 1


@pytest.mark.asyncio
async def test_route_cache_invalidation_reloads_updated_stable_context(monkeypatch):
    flat_contexts = [
        {"alert_id": "ALERT-1", "user_id": "user-1", "user_risk_score": 0.42},
        {"alert_id": "ALERT-2", "user_id": "user-1", "user_risk_score": 0.73},
    ]
    fake_client = _SecurityContextClient(flat_contexts)
    monkeypatch.setattr(triage, "graph_client", fake_client)
    monkeypatch.setenv("USE_ENTITY_CACHE", "true")

    first = await triage._soc_get_security_context_for_analyze("ALERT-1")
    assert triage._soc_invalidate_entity_context("soc", "user", "user-1") is True
    second = await triage._soc_get_security_context_for_analyze("ALERT-2")

    assert first["user_risk_score"] == 0.42
    assert second["user_risk_score"] == 0.73
    diagnostics = triage._soc_entity_cache_diagnostics()
    assert diagnostics["invalidations"] == 1
    assert diagnostics["loads"] == 2


@pytest.mark.asyncio
async def test_health_exposes_entity_cache_diagnostics(monkeypatch):
    triage._soc_reset_entity_cache_for_tests()
    flat_context = {
        "alert_id": "ALERT-1",
        "alert_type": "anomalous_login",
        "severity": "medium",
        "user_id": "user-1",
        "user_risk_score": 0.42,
    }
    fake_client = _SecurityContextClient([flat_context, flat_context])
    monkeypatch.setattr(triage, "graph_client", fake_client)
    monkeypatch.setenv("USE_ENTITY_CACHE", "true")

    await triage._soc_get_security_context_for_analyze("ALERT-1")
    await triage._soc_get_security_context_for_analyze("ALERT-1")

    payload = await app_main.health()
    diagnostics = payload["components"]["entity_cache"]

    assert diagnostics["enabled"] is True
    assert diagnostics["hits"] == 1
    assert diagnostics["misses"] == 1
    assert diagnostics["loads"] == 1
    assert diagnostics["size"] == 1
    assert "user_risk_score" not in diagnostics


@pytest.mark.asyncio
async def test_health_survives_entity_cache_diagnostics_failure(monkeypatch):
    def _raise_diagnostics():
        raise RuntimeError("sensitive user_risk_score=0.42 should not leak")

    monkeypatch.setattr(triage, "_soc_entity_cache_diagnostics", _raise_diagnostics)

    payload = await app_main.health()
    diagnostics = payload["components"]["entity_cache"]

    assert payload["status"] == "healthy"
    assert diagnostics == {
        "available": False,
        "error": "RuntimeError",
    }
    assert "user_risk_score" not in str(diagnostics)
    assert "0.42" not in str(diagnostics)


@pytest.mark.asyncio
async def test_alert_subject_loader_is_always_fresh_and_not_entity_cached():
    cache = EntityCache(max_size=8)
    adapter = EntityContextCacheAdapter(cache, enabled=True)
    calls = 0

    async def alert_loader():
        nonlocal calls
        calls += 1
        return {"alert_id": "ALERT-1", "severity": f"v{calls}"}

    first = await alert_loader()
    second = await alert_loader()

    assert first == {"alert_id": "ALERT-1", "severity": "v1"}
    assert second == {"alert_id": "ALERT-1", "severity": "v2"}
    with pytest.raises(ValueError):
        await adapter.get_context("soc", "alert", "ALERT-1", alert_loader)
    assert cache.stats().size == 0


@pytest.mark.asyncio
async def test_soc_route_shaped_cache_flag_disabled_preserves_current_loader_path():
    cache = EntityCache(max_size=8)
    adapter = EntityContextCacheAdapter(cache, enabled=False)
    calls = 0

    async def current_stable_entity_context_loader():
        nonlocal calls
        calls += 1
        return {
            "user_id": "user-1",
            "user_risk_score": 0.42,
            "mfa_completed": True,
        }

    first = await adapter.get_context(
        "soc", "user", "user-1", current_stable_entity_context_loader
    )
    second = await adapter.get_context(
        "soc", "user", "user-1", current_stable_entity_context_loader
    )

    assert first == {
        "user_id": "user-1",
        "user_risk_score": 0.42,
        "mfa_completed": True,
    }
    assert second == first
    assert calls == 2
    assert adapter.stats().size == 0


@pytest.mark.asyncio
async def test_soc_route_shaped_enabled_cache_path_has_loader_parity_and_hit():
    cache = EntityCache(max_size=8)
    adapter = EntityContextCacheAdapter(cache, enabled=True)
    calls = 0

    async def current_stable_entity_context_loader():
        nonlocal calls
        calls += 1
        return {
            "user_id": "user-1",
            "user_risk_score": 0.42,
            "mfa_completed": True,
        }

    current_loader_result = await current_stable_entity_context_loader()
    calls = 0

    first = await adapter.get_context(
        "soc", "user", "user-1", current_stable_entity_context_loader
    )
    second = await adapter.get_context(
        "soc", "user", "user-1", current_stable_entity_context_loader
    )

    assert first == current_loader_result
    assert second == current_loader_result
    assert calls == 1
    assert adapter.stats().misses == 1
    assert adapter.stats().hits == 1
    assert adapter.stats().loads == 1


@pytest.mark.asyncio
async def test_soc_route_shaped_cache_invalidation_reloads_updated_context():
    cache = EntityCache(max_size=8)
    adapter = EntityContextCacheAdapter(cache, enabled=True)
    source_context = {
        "user_id": "user-1",
        "user_risk_score": 0.42,
        "mfa_completed": True,
    }

    async def current_stable_entity_context_loader():
        return dict(source_context)

    assert await adapter.get_context(
        "soc", "user", "user-1", current_stable_entity_context_loader
    ) == {
        "user_id": "user-1",
        "user_risk_score": 0.42,
        "mfa_completed": True,
    }
    source_context["user_risk_score"] = 0.73
    assert await adapter.get_context(
        "soc", "user", "user-1", current_stable_entity_context_loader
    ) == {
        "user_id": "user-1",
        "user_risk_score": 0.42,
        "mfa_completed": True,
    }

    assert adapter.invalidate("soc", "user", "user-1") is True

    assert await adapter.get_context(
        "soc", "user", "user-1", current_stable_entity_context_loader
    ) == {
        "user_id": "user-1",
        "user_risk_score": 0.73,
        "mfa_completed": True,
    }
    assert adapter.stats().invalidations == 1


def test_soc_route_shaped_cache_rejects_non_cacheable_data():
    adapter = EntityContextCacheAdapter(EntityCache(max_size=8), enabled=True)

    for kind in ("alert", "subject"):
        with pytest.raises(ValueError):
            adapter.invalidate("soc", kind, "ALERT-1")

    for kind in (
        "counter",
        "proof",
        "dk",
        "l5",
        "decision",
        "outcome",
        "conservation",
    ):
        with pytest.raises(ValueError):
            EntityCacheKey("soc", kind, "X1")
