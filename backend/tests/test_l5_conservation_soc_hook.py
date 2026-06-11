from __future__ import annotations

from datetime import datetime, timedelta
import logging
from types import SimpleNamespace

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


class _FakeGraph:
    def __init__(self, rows: list[dict] | None = None):
        self.rows = rows if rows is not None else [
            {"category": "credential_access", "verified": 100, "correct": 80, "overrides": 10},
            {"category": "malware_execution", "verified": 100, "correct": 80, "overrides": 10},
            {"category": "lateral_movement", "verified": 100, "correct": 80, "overrides": 10},
            {"category": "data_exfiltration", "verified": 100, "correct": 80, "overrides": 10},
        ]

    async def run_query(self, _query: str) -> list[dict]:
        if "MATCH (d:Decision)" in _query and "RETURN d.category AS category" in _query:
            return self.rows
        return [{"red_days": 0}]


class _FakeStore:
    def __init__(
        self,
        *,
        old_state: dict | None = None,
        get_error: Exception | None = None,
        update_error: Exception | None = None,
    ):
        self.old_state = old_state
        self.get_error = get_error
        self.update_error = update_error
        self.updates: list[dict] = []

    def get_conservation_state(self, domain: str) -> dict | None:
        if self.get_error is not None:
            raise self.get_error
        assert domain == "soc"
        return self.old_state

    def update_conservation_state(self, **kwargs) -> str:
        if self.update_error is not None:
            raise self.update_error
        self.updates.append(kwargs)
        return "soc:conservation:1"


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
async def test_l5_conservation_hook_no_store_noop(monkeypatch, healthy_state):
    monkeypatch.setattr(learning_health, "get_learning_store", lambda: None)

    result = await LearningHealthMonitor.evaluate(_FakeGraph())
    await learning_health._persist_l5_conservation_state(_with_category_coverage(result))

    assert result["status"] == "GREEN"
    assert result["components"]["alpha"] == pytest.approx(4 / 6, abs=1e-4)
    assert result["components"]["q"] == pytest.approx(0.80)


@pytest.mark.asyncio
async def test_l5_conservation_hook_first_write(monkeypatch, healthy_state):
    store = _FakeStore(old_state=None)
    monkeypatch.setattr(learning_health, "get_learning_store", lambda: store)

    result = await LearningHealthMonitor.evaluate(_FakeGraph())

    assert result["status"] == "GREEN"
    assert len(store.updates) == 1
    update = store.updates[0]
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
async def test_l5_conservation_hook_same_status_passes_old_status(monkeypatch, healthy_state):
    store = _FakeStore(old_state={"status": "GREEN"})
    monkeypatch.setattr(learning_health, "get_learning_store", lambda: store)

    result = await LearningHealthMonitor.evaluate(_FakeGraph())

    assert result["status"] == "GREEN"
    assert store.updates[0]["old_status"] == "GREEN"
    assert store.updates[0]["status"] == "GREEN"


@pytest.mark.asyncio
async def test_l5_conservation_hook_transition_passes_previous_status(monkeypatch, healthy_state):
    store = _FakeStore(old_state={"status": "AMBER"})
    monkeypatch.setattr(learning_health, "get_learning_store", lambda: store)

    result = await LearningHealthMonitor.evaluate(_FakeGraph())

    assert result["status"] == "GREEN"
    assert store.updates[0]["old_status"] == "AMBER"
    assert store.updates[0]["status"] == "GREEN"


@pytest.mark.asyncio
async def test_l5_conservation_hook_get_failure_skips_write(monkeypatch, healthy_state):
    store = _FakeStore(get_error=RuntimeError("store read failed"))
    monkeypatch.setattr(learning_health, "get_learning_store", lambda: store)

    result = await LearningHealthMonitor.evaluate(_FakeGraph())

    assert result["status"] == "GREEN"
    assert store.updates == []


@pytest.mark.asyncio
async def test_l5_conservation_hook_update_failure_non_blocking(monkeypatch, healthy_state):
    store = _FakeStore(update_error=RuntimeError("store write failed"))
    monkeypatch.setattr(learning_health, "get_learning_store", lambda: store)

    result = await LearningHealthMonitor.evaluate(_FakeGraph())

    assert result["status"] == "GREEN"


@pytest.mark.asyncio
async def test_l5_conservation_hook_skips_when_category_coverage_unavailable(
    monkeypatch, healthy_state, caplog
):
    store = _FakeStore(old_state=None)
    monkeypatch.setattr(learning_health, "get_learning_store", lambda: store)

    result = await LearningHealthMonitor.evaluate(None)

    with caplog.at_level(logging.DEBUG):
        await learning_health._persist_l5_conservation_state(result)

    assert store.updates == []
    assert "categories_with_data unavailable" in caplog.text


@pytest.mark.asyncio
async def test_l5_conservation_hook_skips_invalid_category_coverage(
    monkeypatch, healthy_state
):
    store = _FakeStore(old_state=None)
    monkeypatch.setattr(learning_health, "get_learning_store", lambda: store)

    monkeypatch.setattr(learning_health, "get_learning_store", lambda: None)
    result = await LearningHealthMonitor.evaluate(_FakeGraph())
    monkeypatch.setattr(learning_health, "get_learning_store", lambda: store)
    await learning_health._persist_l5_conservation_state(
        _with_category_coverage(result, categories_with_data=999)
    )

    assert result["status"] == "GREEN"
    assert store.updates == []


@pytest.mark.asyncio
async def test_l5_conservation_hook_uses_store_lock(monkeypatch, healthy_state):
    events: list[str] = []

    class _RecordingLock:
        async def __aenter__(self):
            events.append("enter")

        async def __aexit__(self, exc_type, exc, tb):
            events.append("exit")

    store = _FakeStore(old_state=None)
    monkeypatch.setattr(learning_health, "get_learning_store", lambda: store)
    monkeypatch.setattr(learning_health, "_L5_CONSERVATION_STORE_LOCK", _RecordingLock())

    result = await LearningHealthMonitor.evaluate(_FakeGraph())

    assert events == ["enter", "exit"]
    assert len(store.updates) == 1


@pytest.mark.asyncio
async def test_l5_conservation_hook_preserves_response_shape(monkeypatch, healthy_state):
    monkeypatch.setattr(learning_health, "get_learning_store", lambda: None)
    without_store = await LearningHealthMonitor.evaluate(_FakeGraph())

    store = _FakeStore(old_state=None)
    monkeypatch.setattr(learning_health, "get_learning_store", lambda: store)
    with_store = await LearningHealthMonitor.evaluate(_FakeGraph())

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
