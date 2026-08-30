import asyncio
import math
import time
from statistics import pstdev
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import promotion_gate as gate
from app.services import variant_registry as registry


def _variant(
    variant_id="variant_shadow",
    *,
    status=gate.SHADOW,
    category="credential_access",
    artifact_type="routing_rule",
    promoted_at=None,
):
    return SimpleNamespace(
        variant_id=variant_id,
        artifact_type=artifact_type,
        category=category,
        status=status,
        trigger_key=f"trigger:{variant_id}",
        graph_trigger={"campaign_id": "C-007", "category": category},
        created_at=1000.0,
        promoted_at=promoted_at,
    )


def _summary(total=gate.MIN_SHADOW_SAMPLES, win_rate=0.60, tested=True):
    return {
        "shadow_active": False,
        "shadow_tested": tested,
        "wins": int(total * win_rate),
        "total": total,
        "win_rate": win_rate,
    }


def _shadow_event(win_rate=None, metadata=None):
    return {
        "event_type": gate.SHADOW_RESULT,
        "graph_context": {} if win_rate is None else {"win_rate": win_rate},
        "metadata": metadata or {},
    }


def _registry_record(variant_id="variant_shadow", *, status=registry.SHADOW):
    return registry.VariantRecord(
        variant_id=variant_id,
        artifact_type=registry.ARTIFACT_ROUTING_RULE,
        category="credential_access",
        config={"action": "escalate"},
        status=status,
        trigger_key=f"trigger:{variant_id}",
        graph_trigger={"campaign_id": "C-007"},
        created_at=1000.0,
    )


@pytest.fixture(autouse=True)
def reset_gate():
    gate.reset_promotion_gate()
    registry.reset_variant_registry()
    yield
    gate.reset_promotion_gate()
    registry.reset_variant_registry()


@pytest.mark.asyncio
async def test_no_shadow_summary_continues(monkeypatch):
    monkeypatch.setattr(gate, "get_variant", lambda variant_id: _variant())
    monkeypatch.setattr(gate, "get_shadow_summary", lambda variant_id: None)

    result = await gate.evaluate_promotion("variant_shadow", object())

    assert result.verdict == "continue"
    assert "shadow results" in result.reason


@pytest.mark.asyncio
async def test_insufficient_samples_continues(monkeypatch):
    monkeypatch.setattr(gate, "get_variant", lambda variant_id: _variant())
    monkeypatch.setattr(gate, "get_shadow_summary", lambda variant_id: _summary(total=49))

    result = await gate.evaluate_promotion("variant_shadow", object())

    assert result.verdict == "continue"
    assert "insufficient shadow samples" in result.reason


@pytest.mark.asyncio
async def test_win_rate_below_superiority_rejects(monkeypatch):
    monkeypatch.setattr(gate, "get_variant", lambda variant_id: _variant())
    monkeypatch.setattr(gate, "get_shadow_summary", lambda variant_id: _summary(win_rate=0.54))

    result = await gate.evaluate_promotion("variant_shadow", object())

    assert result.verdict == "reject"
    assert "below promotion threshold" in result.reason


@pytest.mark.asyncio
async def test_projected_q_below_floor_rejects(monkeypatch):
    monkeypatch.setattr(gate, "get_variant", lambda variant_id: _variant())
    monkeypatch.setattr(gate, "get_shadow_summary", lambda variant_id: _summary(win_rate=0.55))
    monkeypatch.setattr(gate, "_production_q", lambda: 0.78)

    result = await gate.evaluate_promotion("variant_shadow", object())

    assert result.verdict == "reject"
    assert "projected_q" in result.reason


@pytest.mark.asyncio
async def test_conservation_red_rejects(monkeypatch):
    conservation = AsyncMock(return_value={"passed": False, "status": "RED"})
    batch_std = AsyncMock()
    monkeypatch.setattr(gate, "get_variant", lambda variant_id: _variant())
    monkeypatch.setattr(gate, "get_shadow_summary", lambda variant_id: _summary(win_rate=0.60))
    monkeypatch.setattr(gate, "_estimate_projected_accuracy", lambda summary: 0.84)
    monkeypatch.setattr(gate, "_check_conservation_for_variant", conservation)
    monkeypatch.setattr(gate, "_compute_batch_std", batch_std)

    result = await gate.evaluate_promotion("variant_shadow", object())

    assert result.verdict == "reject"
    assert result.gate_evidence["conservation_status"] == "RED"
    batch_std.assert_not_awaited()


@pytest.mark.asyncio
async def test_batch_std_above_limit_rejects(monkeypatch):
    monkeypatch.setattr(gate, "get_variant", lambda variant_id: _variant())
    monkeypatch.setattr(gate, "get_shadow_summary", lambda variant_id: _summary(win_rate=0.60))
    monkeypatch.setattr(gate, "_estimate_projected_accuracy", lambda summary: 0.84)
    monkeypatch.setattr(
        gate,
        "_check_conservation_for_variant",
        AsyncMock(return_value={"passed": True, "status": "GREEN"}),
    )
    monkeypatch.setattr(
        gate,
        "_get_shadow_batch_stats",
        AsyncMock(return_value={
            "batch_count": gate.MIN_SHADOW_BATCHES,
            "batch_std": 0.11,
            "win_rates": [0.40, 0.60, 0.80],
            "paired_outcomes": [{"baseline": False, "candidate": True}] * 50,
        }),
    )

    result = await gate.evaluate_promotion("variant_shadow", object())

    assert result.verdict == "reject"
    assert "variance" in result.reason


@pytest.mark.asyncio
async def test_insufficient_shadow_batches_continues(monkeypatch):
    monkeypatch.setattr(gate, "get_variant", lambda variant_id: _variant())
    monkeypatch.setattr(gate, "get_shadow_summary", lambda variant_id: _summary(win_rate=0.60))
    monkeypatch.setattr(gate, "_estimate_projected_accuracy", lambda summary: 0.84)
    monkeypatch.setattr(
        gate,
        "_check_conservation_for_variant",
        AsyncMock(return_value={"passed": True, "status": "GREEN"}),
    )
    monkeypatch.setattr(
        gate,
        "_get_shadow_batch_stats",
        AsyncMock(return_value={
            "batch_count": gate.MIN_SHADOW_BATCHES - 1,
            "batch_std": 0.0,
            "win_rates": [0.55, 0.65],
        }),
    )

    result = await gate.evaluate_promotion("variant_shadow", object())

    assert result.verdict == "continue"
    assert f"Need {gate.MIN_SHADOW_BATCHES} shadow batches" in result.reason
    assert result.gate_evidence["shadow_batches"] == gate.MIN_SHADOW_BATCHES - 1
    assert result.gate_evidence["min_shadow_batches"] == gate.MIN_SHADOW_BATCHES


@pytest.mark.asyncio
async def test_all_gate_conditions_pass_promotes_with_evidence(monkeypatch):
    monkeypatch.setattr(gate, "get_variant", lambda variant_id: _variant())
    monkeypatch.setattr(gate, "get_shadow_summary", lambda variant_id: _summary(win_rate=0.60))
    monkeypatch.setattr(gate, "_estimate_projected_accuracy", lambda summary: 0.84)
    monkeypatch.setattr(
        gate,
        "_check_conservation_for_variant",
        AsyncMock(return_value={"passed": True, "status": "GREEN"}),
    )
    monkeypatch.setattr(
        gate,
        "_get_shadow_batch_stats",
        AsyncMock(return_value={
            "batch_count": gate.MIN_SHADOW_BATCHES,
            "batch_std": 0.02,
            "win_rates": [0.58, 0.60, 0.62],
            "paired_outcomes": [{"baseline": False, "candidate": True}] * 50,
        }),
    )

    result = await gate.evaluate_promotion("variant_shadow", object())

    assert result.verdict == "promote"
    assert result.gate_evidence["superiority_pp"] == 10.0
    assert result.gate_evidence["correctness_floor"] == gate.Q_FLOOR
    assert result.gate_evidence["conservation_status"] == "GREEN"
    assert result.gate_evidence["variance_std"] == 0.02
    assert result.gate_evidence["shadow_batches"] == gate.MIN_SHADOW_BATCHES
    assert result.gate_evidence["win_rate"] == 0.60
    assert result.gate_evidence["total"] == gate.MIN_SHADOW_SAMPLES


@pytest.mark.parametrize("status", [gate.ACTIVE, gate.REJECTED])
@pytest.mark.asyncio
async def test_non_shadow_variants_are_not_promoted(monkeypatch, status):
    monkeypatch.setattr(gate, "get_variant", lambda variant_id: _variant(status=status))

    result = await gate.evaluate_promotion("variant_shadow", object())

    assert result.verdict == "continue"
    assert result.gate_evidence == {"status": status}


@pytest.mark.asyncio
async def test_execute_promotion_records_ledger_then_transitions_active(monkeypatch):
    calls = []

    async def fake_record(**kwargs):
        calls.append("ledger")
        return {"id": "evo_1"}

    def fake_transition(variant_id, new_status):
        calls.append("transition")
        return _variant(status=new_status)

    monkeypatch.setattr(gate, "get_variant", lambda variant_id: _variant())
    monkeypatch.setattr(gate, "record_evolution_event", fake_record)
    monkeypatch.setattr(gate, "transition_status", fake_transition)

    result = await gate.execute_promotion("variant_shadow", {"win_rate": 0.60}, object())

    assert result.status == gate.ACTIVE
    assert calls == ["ledger", "transition"]


@pytest.mark.asyncio
async def test_execute_promotion_uses_promotion_approved_event(monkeypatch):
    ledger = AsyncMock(return_value={"id": "evo_1"})
    transition = MagicMock(return_value=_variant(status=gate.ACTIVE))
    monkeypatch.setattr(gate, "get_variant", lambda variant_id: _variant())
    monkeypatch.setattr(gate, "record_evolution_event", ledger)
    monkeypatch.setattr(gate, "transition_status", transition)

    await gate.execute_promotion("variant_shadow", {"win_rate": 0.60}, object())

    kwargs = ledger.await_args.kwargs
    assert kwargs["event_type"] == gate.PROMOTION_APPROVED
    assert kwargs["variant_id"] == "variant_shadow"
    assert kwargs["before_state"] == {"status": gate.SHADOW}
    assert kwargs["after_state"] == {"status": gate.ACTIVE}
    transition.assert_called_once_with("variant_shadow", gate.ACTIVE)


@pytest.mark.asyncio
async def test_execute_rejection_records_ledger_then_transitions_rejected(monkeypatch):
    calls = []

    async def fake_record(**kwargs):
        calls.append("ledger")
        return {"id": "evo_2"}

    def fake_transition(variant_id, new_status):
        calls.append("transition")
        return _variant(status=new_status)

    monkeypatch.setattr(gate, "get_variant", lambda variant_id: _variant())
    monkeypatch.setattr(gate, "record_evolution_event", fake_record)
    monkeypatch.setattr(gate, "transition_status", fake_transition)

    result = await gate.execute_rejection("variant_shadow", "unsafe", object())

    assert result.status == gate.REJECTED
    assert calls == ["ledger", "transition"]


@pytest.mark.asyncio
async def test_execute_rejection_uses_promotion_rejected_event(monkeypatch):
    ledger = AsyncMock(return_value={"id": "evo_2"})
    transition = MagicMock(return_value=_variant(status=gate.REJECTED))
    monkeypatch.setattr(gate, "get_variant", lambda variant_id: _variant())
    monkeypatch.setattr(gate, "record_evolution_event", ledger)
    monkeypatch.setattr(gate, "transition_status", transition)

    await gate.execute_rejection("variant_shadow", "unsafe", object())

    kwargs = ledger.await_args.kwargs
    assert kwargs["event_type"] == gate.PROMOTION_REJECTED
    assert kwargs["metadata"]["reason"] == "unsafe"
    transition.assert_called_once_with("variant_shadow", gate.REJECTED)


@pytest.mark.asyncio
async def test_ledger_failure_prevents_transition(monkeypatch):
    transition = MagicMock()
    monkeypatch.setattr(gate, "get_variant", lambda variant_id: _variant())
    monkeypatch.setattr(gate, "record_evolution_event", AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(gate, "transition_status", transition)

    with pytest.raises(RuntimeError):
        await gate.execute_promotion("variant_shadow", {"win_rate": 0.60}, object())

    transition.assert_not_called()


def test_projected_accuracy_uses_production_q(monkeypatch):
    monkeypatch.setattr(gate, "_get_health_components", lambda: {"q": 0.84})

    projected = gate._estimate_projected_accuracy({"win_rate": 0.70})

    assert projected == 0.88


def test_projected_accuracy_falls_back_to_q_floor(monkeypatch):
    monkeypatch.setattr(gate, "_get_health_components", lambda: None)

    projected = gate._estimate_projected_accuracy({"win_rate": 0.60})

    assert projected == 0.82


def test_health_components_use_learning_health_extraction(monkeypatch):
    state = SimpleNamespace(history=["verified-update"])
    monkeypatch.setattr("app.services.gae_state.get_learning_state", lambda: state)
    extract = MagicMock(return_value={"q": 0.84, "alpha": 0.25, "V": 400.0, "n": 50})
    monkeypatch.setattr(
        "app.services.learning_health.LearningHealthMonitor._extract_components",
        staticmethod(extract),
    )

    assert gate._get_health_components() == {
        "q": 0.84,
        "alpha": 0.25,
        "V": 400.0,
        "source": "learning_health",
    }
    extract.assert_called_once_with(state.history)


def test_health_components_alpha_fallback_does_not_invent_q_or_v(monkeypatch):
    scorer = SimpleNamespace(get_alpha=MagicMock(return_value=0.20))
    monkeypatch.setattr("app.services.gae_state.get_learning_state", MagicMock(side_effect=RuntimeError("offline")))
    monkeypatch.setattr("app.services.gae_state.get_profile_scorer", lambda: scorer)

    assert gate._get_health_components() == {"alpha": 0.20, "source": "profile_scorer"}
    scorer.get_alpha.assert_called_once_with(0)


@pytest.mark.asyncio
async def test_conservation_uses_alpha_v_and_theta_formula(monkeypatch):
    monkeypatch.setattr(gate, "_get_health_components", lambda: {"alpha": 0.25, "V": 400.0})

    result = await gate._check_conservation_for_variant(0.85, object())

    assert result["passed"] is True
    assert result["status"] == "GREEN"
    assert result["alpha"] == 0.25
    assert result["V"] == 400.0
    assert result["signal"] == 85.0
    assert math.isclose(result["theta_min"], 0.2353, rel_tol=1e-4)


@pytest.mark.asyncio
async def test_conservation_unavailable_is_unknown_fail_open(monkeypatch):
    monkeypatch.setattr(gate, "_get_health_components", lambda: None)

    result = await gate._check_conservation_for_variant(0.85, object())

    assert result == {"passed": True, "status": "UNKNOWN"}


@pytest.mark.parametrize("components", [{"alpha": 0, "V": 200}, {"alpha": 0.25, "V": 0}])
@pytest.mark.asyncio
async def test_conservation_alpha_or_v_zero_is_cold_start(monkeypatch, components):
    monkeypatch.setattr(gate, "_get_health_components", lambda: components)

    result = await gate._check_conservation_for_variant(0.85, object())

    assert result["passed"] is True
    assert result["status"] == "COLD_START"


@pytest.mark.asyncio
async def test_batch_std_uses_three_shadow_result_events(monkeypatch):
    rates = [0.55, 0.65, 0.60]
    monkeypatch.setattr(
        gate,
        "get_variant_history",
        AsyncMock(return_value=[_shadow_event(rate) for rate in rates]),
    )

    result = await gate._compute_batch_std("variant_shadow", object())

    assert result == round(pstdev(rates), 6)


@pytest.mark.asyncio
async def test_batch_std_uses_metadata_when_graph_context_missing(monkeypatch):
    monkeypatch.setattr(
        gate,
        "get_variant_history",
        AsyncMock(return_value=[
            _shadow_event(metadata={"wins": 3, "total": 5}),
            _shadow_event(metadata={"win_rate": 0.8}),
            _shadow_event(metadata={"wins": 2, "total": 5}),
        ]),
    )

    result = await gate._compute_batch_std("variant_shadow", object())

    assert result == round(pstdev([0.6, 0.8, 0.4]), 6)


@pytest.mark.asyncio
async def test_shadow_batch_stats_reports_count_std_and_rates(monkeypatch):
    rates = [0.55, 0.65, 0.60]
    monkeypatch.setattr(
        gate,
        "get_variant_history",
        AsyncMock(return_value=[_shadow_event(rate) for rate in rates]),
    )

    result = await gate._get_shadow_batch_stats("variant_shadow", object())

    assert result == {
        "batch_count": 3,
        "batch_std": round(pstdev(rates), 6),
        "win_rates": rates,
    }


@pytest.mark.asyncio
async def test_batch_std_below_min_batches_is_zero(monkeypatch):
    monkeypatch.setattr(
        gate,
        "get_variant_history",
        AsyncMock(return_value=[_shadow_event(0.55), _shadow_event(0.65)]),
    )

    assert await gate._compute_batch_std("variant_shadow", object()) == 0.0


@pytest.mark.asyncio
async def test_batch_std_with_no_events_is_zero(monkeypatch):
    monkeypatch.setattr(gate, "get_variant_history", AsyncMock(return_value=[]))

    assert await gate._compute_batch_std("variant_shadow", object()) == 0.0


@pytest.mark.asyncio
async def test_no_active_variants_returns_none(monkeypatch):
    monkeypatch.setattr(gate, "get_all_variants", lambda status_filter=None: [])

    assert await gate.check_rollback(object()) is None


@pytest.mark.asyncio
async def test_recent_active_variant_within_window_rolls_back(monkeypatch):
    recent = _variant("recent", status=gate.ACTIVE, promoted_at=time.time())
    rollback = AsyncMock(return_value="rolled")
    client = object()
    monkeypatch.setattr(gate, "get_all_variants", lambda status_filter=None: [recent])
    monkeypatch.setattr(gate, "_get_daily_volume", lambda: 200.0)
    monkeypatch.setattr(gate, "_execute_rollback", rollback)

    result = await gate.check_rollback(client)

    assert result == "rolled"
    rollback.assert_awaited_once_with(recent, client)


@pytest.mark.asyncio
async def test_outside_rollback_window_does_not_rollback(monkeypatch):
    old = _variant("old", status=gate.ACTIVE, promoted_at=time.time() - 49 * 3600)
    rollback = AsyncMock()
    monkeypatch.setattr(gate, "get_all_variants", lambda status_filter=None: [old])
    monkeypatch.setattr(gate, "_get_daily_volume", lambda: 200.0)
    monkeypatch.setattr(gate, "_execute_rollback", rollback)

    assert await gate.check_rollback(object()) is None
    rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_execute_rollback_records_ledger_then_transitions_rolled_back(monkeypatch):
    calls = []

    async def fake_record(**kwargs):
        calls.append("ledger")
        return {"id": "evo_rollback"}

    def fake_transition(variant_id, new_status):
        calls.append("transition")
        return _variant(status=new_status)

    monkeypatch.setattr(gate, "record_evolution_event", fake_record)
    monkeypatch.setattr(gate, "transition_status", fake_transition)

    result = await gate._execute_rollback(_variant(status=gate.ACTIVE), object())

    assert result.status == gate.ROLLED_BACK
    assert calls == ["ledger", "transition"]


@pytest.mark.asyncio
async def test_execute_rollback_uses_rollback_event(monkeypatch):
    ledger = AsyncMock(return_value={"id": "evo_rollback"})
    transition = MagicMock(return_value=_variant(status=gate.ROLLED_BACK))
    monkeypatch.setattr(gate, "record_evolution_event", ledger)
    monkeypatch.setattr(gate, "transition_status", transition)

    await gate._execute_rollback(_variant(status=gate.ACTIVE), object())

    assert ledger.await_args.kwargs["event_type"] == gate.ROLLBACK
    transition.assert_called_once_with("variant_shadow", gate.ROLLED_BACK)


def test_rollback_window_high_volume_is_48_hours():
    assert gate._rollback_window_hours(200.0) == gate.ROLLBACK_MIN_HOURS


def test_rollback_window_low_volume_is_longer():
    assert gate._rollback_window_hours(10.0) == 240.0


def test_rollback_window_non_positive_volume_is_five_days():
    assert gate._rollback_window_hours(0) == gate.ROLLBACK_MIN_HOURS * 5


def test_get_daily_volume_fallback(monkeypatch):
    monkeypatch.setattr(gate, "_get_health_components", lambda: None)

    assert gate._get_daily_volume() == 200.0


def test_get_daily_volume_uses_health_v(monkeypatch):
    monkeypatch.setattr(gate, "_get_health_components", lambda: {"V": 123.0})

    assert gate._get_daily_volume() == 123.0


@pytest.mark.asyncio
async def test_global_rollback_selects_most_recent_active_variant(monkeypatch):
    older = _variant("older", status=gate.ACTIVE, promoted_at=time.time() - 10)
    newer = _variant("newer", status=gate.ACTIVE, promoted_at=time.time())
    rollback = AsyncMock(return_value="newer")
    client = object()
    monkeypatch.setattr(gate, "get_all_variants", lambda status_filter=None: [older, newer])
    monkeypatch.setattr(gate, "_get_daily_volume", lambda: 200.0)
    monkeypatch.setattr(gate, "_execute_rollback", rollback)

    result = await gate.check_rollback(client)

    assert result == "newer"
    rollback.assert_awaited_once_with(newer, client)


@pytest.mark.asyncio
async def test_category_rollback_filters_active_variants(monkeypatch):
    matching = _variant("matching", status=gate.ACTIVE, category="credential_access", promoted_at=time.time())
    other = _variant("other", status=gate.ACTIVE, category="lateral_movement", promoted_at=time.time() + 10)
    rollback = AsyncMock(return_value="matching")
    client = object()
    monkeypatch.setattr(gate, "get_all_variants", lambda status_filter=None: [matching, other])
    monkeypatch.setattr(gate, "_get_daily_volume", lambda: 200.0)
    monkeypatch.setattr(gate, "_execute_rollback", rollback)

    result = await gate.check_rollback(client, category="credential_access")

    assert result == "matching"
    rollback.assert_awaited_once_with(matching, client)


def test_register_rollback_handler_registers_sync_handlers(monkeypatch):
    class FakeStateMachine:
        def __init__(self):
            self.calls = []

        def register_handler(self, from_state, to_state, handler):
            self.calls.append((from_state, to_state, handler))

    state_machine = FakeStateMachine()
    scorer = SimpleNamespace(conservation_state_machine=state_machine)
    monkeypatch.setattr("app.services.gae_state.get_profile_scorer", lambda: scorer)

    assert gate.register_rollback_handler(object()) is True
    assert [(call[0], call[1]) for call in state_machine.calls] == [
        ("*", "AMBER"),
        ("*", "RED"),
    ]
    assert callable(state_machine.calls[0][2])


def test_registered_handler_schedules_async_task(monkeypatch):
    class FakeStateMachine:
        def __init__(self):
            self.calls = []

        def register_handler(self, from_state, to_state, handler):
            self.calls.append((from_state, to_state, handler))

    class FakeLoop:
        def __init__(self):
            self.coroutines = []

        def create_task(self, coro):
            self.coroutines.append(coro)
            coro.close()
            return SimpleNamespace(done=lambda: False)

    state_machine = FakeStateMachine()
    scorer = SimpleNamespace(conservation_state_machine=state_machine)
    fake_loop = FakeLoop()
    monkeypatch.setattr("app.services.gae_state.get_profile_scorer", lambda: scorer)
    monkeypatch.setattr(gate.asyncio, "get_running_loop", lambda: fake_loop)

    assert gate.register_rollback_handler(object()) is True
    state_machine.calls[0][2]("GREEN", "AMBER")

    assert len(fake_loop.coroutines) == 1


def test_registered_handler_uses_captured_loop_when_invoked_without_running_loop(monkeypatch):
    class FakeStateMachine:
        def __init__(self):
            self.calls = []

        def register_handler(self, from_state, to_state, handler):
            self.calls.append((from_state, to_state, handler))

    class FakeLoop:
        def __init__(self):
            self.scheduled = []

        def is_closed(self):
            return False

        def call_soon_threadsafe(self, callback, *args):
            self.scheduled.append((callback, args))
            callback(*args)

        def create_task(self, coro):
            coro.close()
            return SimpleNamespace(done=lambda: False)

    state_machine = FakeStateMachine()
    scorer = SimpleNamespace(conservation_state_machine=state_machine)
    fake_loop = FakeLoop()
    monkeypatch.setattr("app.services.gae_state.get_profile_scorer", lambda: scorer)
    monkeypatch.setattr(gate.asyncio, "get_running_loop", lambda: fake_loop)

    assert gate.register_rollback_handler(object()) is True

    def no_running_loop():
        raise RuntimeError("no running event loop")

    monkeypatch.setattr(gate.asyncio, "get_running_loop", no_running_loop)
    state_machine.calls[0][2]("GREEN", "AMBER")

    assert len(fake_loop.scheduled) == 1


def test_registered_handler_warns_when_no_loop_available(monkeypatch, caplog):
    class FakeStateMachine:
        def __init__(self):
            self.calls = []

        def register_handler(self, from_state, to_state, handler):
            self.calls.append((from_state, to_state, handler))

    state_machine = FakeStateMachine()
    scorer = SimpleNamespace(conservation_state_machine=state_machine)

    def no_running_loop():
        raise RuntimeError("no running event loop")

    monkeypatch.setattr("app.services.gae_state.get_profile_scorer", lambda: scorer)
    monkeypatch.setattr(gate.asyncio, "get_running_loop", no_running_loop)

    assert gate.register_rollback_handler(object()) is True
    with caplog.at_level("WARNING", logger=gate.log.name):
        state_machine.calls[0][2]("GREEN", "AMBER")

    assert "without an available event loop" in caplog.text


def test_register_rollback_handler_scorer_none_returns_false(monkeypatch):
    monkeypatch.setattr("app.services.gae_state.get_profile_scorer", lambda: None)

    assert gate.register_rollback_handler(object()) is False


def test_register_rollback_handler_missing_state_machine_returns_false(monkeypatch):
    monkeypatch.setattr("app.services.gae_state.get_profile_scorer", lambda: SimpleNamespace())

    assert gate.register_rollback_handler(object()) is False


def test_register_rollback_handler_is_idempotent(monkeypatch):
    class FakeStateMachine:
        def __init__(self):
            self.calls = []

        def register_handler(self, from_state, to_state, handler):
            self.calls.append((from_state, to_state, handler))

    state_machine = FakeStateMachine()
    scorer = SimpleNamespace(conservation_state_machine=state_machine)
    monkeypatch.setattr("app.services.gae_state.get_profile_scorer", lambda: scorer)

    assert gate.register_rollback_handler(object()) is True
    assert gate.register_rollback_handler(object()) is True

    assert len(state_machine.calls) == 2


def test_promote_evaluate_missing_variant_id_returns_400():
    response = TestClient(app).post("/api/admin/promote-evaluate")

    assert response.status_code == 400
    assert response.json()["detail"] == "variant_id is required"


def test_promote_evaluate_unknown_variant_returns_404():
    response = TestClient(app).post("/api/admin/promote-evaluate?variant_id=missing")

    assert response.status_code == 404


def test_promote_evaluate_promote_calls_execute_promotion(monkeypatch):
    registry.register_variant(_registry_record())
    evaluate = AsyncMock(return_value=gate.PromotionResult(
        "promote",
        "all promotion gates passed",
        {"win_rate": 0.70},
    ))
    execute_promotion = AsyncMock()
    execute_rejection = AsyncMock()
    monkeypatch.setattr(gate, "evaluate_promotion", evaluate)
    monkeypatch.setattr(gate, "execute_promotion", execute_promotion)
    monkeypatch.setattr(gate, "execute_rejection", execute_rejection)

    response = TestClient(app).post("/api/admin/promote-evaluate?variant_id=variant_shadow")

    assert response.status_code == 200
    assert response.json()["verdict"] == "promote"
    evaluate.assert_awaited_once()
    execute_promotion.assert_awaited_once()
    execute_rejection.assert_not_awaited()


def test_promote_evaluate_reject_calls_execute_rejection(monkeypatch):
    registry.register_variant(_registry_record())
    evaluate = AsyncMock(return_value=gate.PromotionResult(
        "reject",
        "conservation check failed",
        {"conservation_status": "RED"},
    ))
    execute_promotion = AsyncMock()
    execute_rejection = AsyncMock()
    monkeypatch.setattr(gate, "evaluate_promotion", evaluate)
    monkeypatch.setattr(gate, "execute_promotion", execute_promotion)
    monkeypatch.setattr(gate, "execute_rejection", execute_rejection)

    response = TestClient(app).post("/api/admin/promote-evaluate?variant_id=variant_shadow")

    assert response.status_code == 200
    assert response.json()["verdict"] == "reject"
    execute_promotion.assert_not_awaited()
    execute_rejection.assert_awaited_once()


def test_promote_evaluate_continue_does_not_transition(monkeypatch):
    registry.register_variant(_registry_record())
    evaluate = AsyncMock(return_value=gate.PromotionResult(
        "continue",
        "insufficient shadow samples",
        {"total": 10},
    ))
    execute_promotion = AsyncMock()
    execute_rejection = AsyncMock()
    monkeypatch.setattr(gate, "evaluate_promotion", evaluate)
    monkeypatch.setattr(gate, "execute_promotion", execute_promotion)
    monkeypatch.setattr(gate, "execute_rejection", execute_rejection)

    response = TestClient(app).post("/api/admin/promote-evaluate?variant_id=variant_shadow")

    assert response.status_code == 200
    assert response.json()["verdict"] == "continue"
    execute_promotion.assert_not_awaited()
    execute_rejection.assert_not_awaited()


def test_startup_event_contains_promotion_rollback_registration():
    import inspect
    import app.main as main_module

    source = inspect.getsource(main_module.startup_event)

    assert "register_rollback_handler" in source


def test_reset_evolver_state_calls_reset_promotion_gate(monkeypatch):
    from app.services import evolver

    called = []
    monkeypatch.setattr("gae.evolution.reset_evolution_ledger", lambda: None)
    monkeypatch.setattr("app.services.shadow_runner.reset_shadow_runner", lambda: None)
    monkeypatch.setattr("app.services.variant_registry.reset_variant_registry", lambda: None)
    monkeypatch.setattr("app.services.promotion_gate.reset_promotion_gate", lambda: called.append("promotion"))

    evolver.reset_evolver_state()

    assert called == ["promotion"]
