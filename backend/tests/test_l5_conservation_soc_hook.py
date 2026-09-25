from __future__ import annotations

from datetime import datetime, timedelta
import logging
from types import SimpleNamespace
from unittest.mock import Mock
from copilot_sdk.graph.memory_store import InMemoryGraphStore

import pytest

from app.services import learning_health
from app.services.learning_health import LearningHealthMonitor


def _history(count: int, *, alpha_effective: float = 0.01, outcome: int = 1) -> list:
    start = datetime(2026, 1, 1, 0, 0, 0)
    return [
        SimpleNamespace(
            alpha_effective=alpha_effective,
            outcome=outcome,
            timestamp=(start + timedelta(minutes=i)).isoformat(),
        )
        for i in range(count)
    ]


class _FakeState:
    def __init__(self, history: list):
        self.history = history
        self.decision_count = len(history)


@pytest.fixture
def conservation_graph(age_graph):
    for category in ["credential_access", "malware_execution", "lateral_movement", "data_exfiltration"]:
        for index in range(10):
            age_graph.decision(category=category, correct=index < 8, was_override=index < 1)
    return age_graph.client


def _conservation_store(monkeypatch, *, old_state=None, get_error=None, update_error=None):
    store = InMemoryGraphStore(domain="soc")
    if old_state is not None:
        store.update_conservation_state(domain="soc", status=old_state["status"], alpha=1.0,
            q=0.8, V=400, theta_min=0.1, product=320.0, categories_total=6,
            categories_with_data=6, baseline_product=320.0, relative_threshold=1.0, complacency_flag="false")
    if get_error is not None:
        monkeypatch.setattr(store, "get_conservation_state", Mock(side_effect=get_error))
    monkeypatch.setattr(store, "update_conservation_state", Mock(wraps=store.update_conservation_state, side_effect=update_error))
    return store


def _with_category_coverage(health: dict, categories_with_data: int = 4) -> dict:
    updated = dict(health)
    updated["components"] = dict(health["components"])
    updated["components"]["categories_with_data"] = categories_with_data
    return updated


@pytest.fixture
def healthy_state(monkeypatch):
    state = _FakeState(_history(400, alpha_effective=0.01, outcome=1))
    monkeypatch.setattr(learning_health, "get_learning_state", lambda: state)
    return state


@pytest.mark.asyncio
@pytest.mark.age
async def test_l5_conservation_hook_no_store_noop(monkeypatch, healthy_state, conservation_graph):
    monkeypatch.setattr(learning_health, "get_learning_store", lambda: None)

    result = await LearningHealthMonitor.evaluate(conservation_graph)
    await learning_health._persist_l5_conservation_state(_with_category_coverage(result))

    assert result["status"] == "GREEN"
    assert result["components"]["alpha"] == pytest.approx(4 / 6, abs=1e-4)
    assert result["components"]["q"] == pytest.approx(0.80)


@pytest.mark.asyncio
@pytest.mark.age
async def test_l5_conservation_hook_first_write(monkeypatch, healthy_state, conservation_graph):
    store = _conservation_store(monkeypatch, old_state=None)
    monkeypatch.setattr(learning_health, "get_learning_store", lambda: store)

    result = await LearningHealthMonitor.evaluate(conservation_graph)

    assert result["status"] == "GREEN"
    assert store.update_conservation_state.call_count == 1
    update = store.update_conservation_state.call_args_list[0].kwargs
    assert store.get_conservation_state("soc")["status"] == "GREEN"
    assert update["domain"] == "soc"
    assert update["status"] == "GREEN"
    assert update["old_status"] is None
    assert update["alpha"] == pytest.approx(4 / 6, abs=1e-4)
    assert update["q"] == pytest.approx(0.80)
    assert isinstance(update["V"], int)
    assert update["theta_min"] == pytest.approx(result["theta_min"])
    assert update["product"] == pytest.approx(result["signal"])
    assert isinstance(update["categories_total"], int)
    assert update["categories_total"] > 1
    assert update["categories_with_data"] == 4
    assert update["categories_with_data"] < update["categories_total"]
    assert update["baseline_product"] == pytest.approx(result["baseline"])
    assert update["relative_threshold"] == pytest.approx(
        result["baseline"]
        - LearningHealthMonitor.AMBER_SIGMA * result["baseline_std"]
    )
    assert update["complacency_flag"] == "false"
    assert update["caused_by_decision_id"] is None


@pytest.mark.asyncio
@pytest.mark.age
async def test_l5_conservation_hook_same_status_passes_old_status(monkeypatch, healthy_state, conservation_graph):
    store = _conservation_store(monkeypatch, old_state={"status": "GREEN"})
    monkeypatch.setattr(learning_health, "get_learning_store", lambda: store)

    result = await LearningHealthMonitor.evaluate(conservation_graph)

    assert result["status"] == "GREEN"
    assert store.update_conservation_state.call_args_list[0].kwargs["old_status"] == "GREEN"
    assert store.update_conservation_state.call_args_list[0].kwargs["status"] == "GREEN"


@pytest.mark.asyncio
@pytest.mark.age
async def test_l5_conservation_hook_transition_passes_previous_status(monkeypatch, healthy_state, conservation_graph):
    store = _conservation_store(monkeypatch, old_state={"status": "AMBER"})
    monkeypatch.setattr(learning_health, "get_learning_store", lambda: store)

    result = await LearningHealthMonitor.evaluate(conservation_graph)

    assert result["status"] == "GREEN"
    assert store.update_conservation_state.call_args_list[0].kwargs["old_status"] == "AMBER"
    assert store.update_conservation_state.call_args_list[0].kwargs["status"] == "GREEN"


@pytest.mark.asyncio
@pytest.mark.age
async def test_l5_conservation_hook_get_failure_skips_write(monkeypatch, healthy_state, conservation_graph):
    store = _conservation_store(monkeypatch, get_error=RuntimeError("store read failed"))
    monkeypatch.setattr(learning_health, "get_learning_store", lambda: store)

    result = await LearningHealthMonitor.evaluate(conservation_graph)

    assert result["status"] == "GREEN"
    store.update_conservation_state.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.age
async def test_l5_conservation_hook_update_failure_non_blocking(monkeypatch, healthy_state, conservation_graph):
    store = _conservation_store(monkeypatch, update_error=RuntimeError("store write failed"))
    monkeypatch.setattr(learning_health, "get_learning_store", lambda: store)

    result = await LearningHealthMonitor.evaluate(conservation_graph)

    assert result["status"] == "GREEN"


@pytest.mark.asyncio
async def test_l5_conservation_hook_skips_when_category_coverage_unavailable(
    monkeypatch, healthy_state, caplog
):
    store = _conservation_store(monkeypatch, old_state=None)
    monkeypatch.setattr(learning_health, "get_learning_store", lambda: store)

    result = await LearningHealthMonitor.evaluate(None)

    with caplog.at_level(logging.DEBUG):
        await learning_health._persist_l5_conservation_state(result)

    store.update_conservation_state.assert_not_called()
    assert "categories_with_data unavailable" in caplog.text


@pytest.mark.asyncio
@pytest.mark.age
async def test_l5_conservation_hook_skips_invalid_category_coverage(monkeypatch, healthy_state, conservation_graph):
    store = _conservation_store(monkeypatch, old_state=None)
    monkeypatch.setattr(learning_health, "get_learning_store", lambda: store)

    monkeypatch.setattr(learning_health, "get_learning_store", lambda: None)
    result = await LearningHealthMonitor.evaluate(conservation_graph)
    monkeypatch.setattr(learning_health, "get_learning_store", lambda: store)
    await learning_health._persist_l5_conservation_state(
        _with_category_coverage(result, categories_with_data=999)
    )

    assert result["status"] == "GREEN"
    store.update_conservation_state.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.age
async def test_l5_conservation_hook_uses_store_lock(monkeypatch, healthy_state, conservation_graph):
    events: list[str] = []

    class _RecordingLock:
        async def __aenter__(self):
            events.append("enter")

        async def __aexit__(self, exc_type, exc, tb):
            events.append("exit")

    store = _conservation_store(monkeypatch, old_state=None)
    monkeypatch.setattr(learning_health, "get_learning_store", lambda: store)
    monkeypatch.setattr(learning_health, "_L5_CONSERVATION_STORE_LOCK", _RecordingLock())

    result = await LearningHealthMonitor.evaluate(conservation_graph)

    assert events == ["enter", "exit"]
    assert store.update_conservation_state.call_count == 1


@pytest.mark.asyncio
@pytest.mark.age
async def test_l5_conservation_hook_preserves_response_shape(monkeypatch, healthy_state, conservation_graph):
    monkeypatch.setattr(learning_health, "get_learning_store", lambda: None)
    without_store = await LearningHealthMonitor.evaluate(conservation_graph)

    store = _conservation_store(monkeypatch, old_state=None)
    monkeypatch.setattr(learning_health, "get_learning_store", lambda: store)
    with_store = await LearningHealthMonitor.evaluate(conservation_graph)

    assert set(with_store) == set(without_store)
    assert with_store["status"] == without_store["status"]
    assert with_store["signal"] == without_store["signal"]
    assert with_store["theta_min"] == without_store["theta_min"]


def test_l5_conservation_hook_does_not_import_stale_adapter_or_wire_feedback():
    source = learning_health.__loader__.get_source(learning_health.__name__)

    assert "AGESDKAdapter" not in source
    assert "AGEGraphStoreAdapter" not in source
    assert "feedback" not in source
    assert "guarded_update" not in source
