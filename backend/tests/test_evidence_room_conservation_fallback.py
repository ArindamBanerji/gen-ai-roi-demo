from __future__ import annotations

import pytest

from app.services.evidence_room import EvidenceRoomService


class _Snapshot:
    verified_decisions = 500


async def _health(status: str, signal: float, **extra) -> dict:
    result = {
        "status": status,
        "signal": signal,
        "theta_min": 1.23,
        "auto_pause_active": False,
    }
    result.update(extra)
    return result


def _patch_snapshot(monkeypatch):
    monkeypatch.setattr(
        "app.state.graph_snapshot.get_snapshot",
        lambda: _Snapshot(),
    )


@pytest.mark.asyncio
async def test_zero_product_red_with_green_iks_returns_green(monkeypatch):
    _patch_snapshot(monkeypatch)
    monkeypatch.setattr(
        "app.services.learning_health.LearningHealthMonitor.evaluate",
        lambda _client: _health("RED", 0.0),
    )

    async def fake_iks(_client):
        return 65.0

    monkeypatch.setattr("app.services.iks.compute_visible_iks", fake_iks)

    result = await EvidenceRoomService()._collect_conservation()

    assert result["status"] == "GREEN"
    assert result["product"] == 0.0
    assert result["health_source"] == "iks_fallback"
    assert result["fallback_reason"] == "zero_product_learning_health"


@pytest.mark.asyncio
async def test_zero_product_red_with_amber_iks_returns_amber(monkeypatch):
    _patch_snapshot(monkeypatch)
    monkeypatch.setattr(
        "app.services.learning_health.LearningHealthMonitor.evaluate",
        lambda _client: _health("RED", 0.0),
    )

    async def fake_iks(_client):
        return 25.0

    monkeypatch.setattr("app.services.iks.compute_visible_iks", fake_iks)

    result = await EvidenceRoomService()._collect_conservation()

    assert result["status"] == "AMBER"
    assert result["health_source"] == "iks_fallback"


@pytest.mark.asyncio
async def test_zero_product_red_with_unhealthy_iks_remains_red(monkeypatch):
    _patch_snapshot(monkeypatch)
    monkeypatch.setattr(
        "app.services.learning_health.LearningHealthMonitor.evaluate",
        lambda _client: _health("RED", 0.0),
    )

    async def fake_iks(_client):
        return 10.0

    monkeypatch.setattr("app.services.iks.compute_visible_iks", fake_iks)

    result = await EvidenceRoomService()._collect_conservation()

    assert result["status"] == "RED"
    assert result["health_source"] == "learning_health"
    assert result["fallback_reason"] is None


@pytest.mark.asyncio
async def test_nonzero_product_is_not_overridden(monkeypatch):
    _patch_snapshot(monkeypatch)
    monkeypatch.setattr(
        "app.services.learning_health.LearningHealthMonitor.evaluate",
        lambda _client: _health("RED", 0.5),
    )

    async def fake_iks(_client):
        return 65.0

    monkeypatch.setattr("app.services.iks.compute_visible_iks", fake_iks)

    result = await EvidenceRoomService()._collect_conservation()

    assert result["status"] == "RED"
    assert result["product"] == 0.5
    assert result["health_source"] == "learning_health"


@pytest.mark.asyncio
async def test_iks_failure_preserves_learning_health_result(monkeypatch):
    _patch_snapshot(monkeypatch)
    monkeypatch.setattr(
        "app.services.learning_health.LearningHealthMonitor.evaluate",
        lambda _client: _health("UNKNOWN", 0.0),
    )

    async def fake_iks(_client):
        raise RuntimeError("IKS unavailable")

    monkeypatch.setattr("app.services.iks.compute_visible_iks", fake_iks)

    result = await EvidenceRoomService()._collect_conservation()

    assert result["status"] == "UNKNOWN"
    assert result["health_source"] == "learning_health"
    assert result["fallback_reason"] is None


@pytest.mark.asyncio
async def test_calibrating_pre_activation_passes_through_without_iks_fallback(monkeypatch):
    _patch_snapshot(monkeypatch)
    monkeypatch.setattr(
        "app.services.learning_health.LearningHealthMonitor.evaluate",
        lambda _client: _health(
            "CALIBRATING",
            0.0,
            pre_activation=True,
            learning_enabled=False,
            health_source="learning_health_pre_activation",
            status_reason="learning_disabled_no_live_history",
        ),
    )

    async def fail_if_called(_client):
        raise AssertionError("IKS fallback should not run for CALIBRATING")

    monkeypatch.setattr("app.services.iks.compute_visible_iks", fail_if_called)

    result = await EvidenceRoomService()._collect_conservation()

    assert result["status"] == "CALIBRATING"
    assert result["product"] == 0.0
    assert result["health_source"] == "learning_health_pre_activation"
    assert result["fallback_reason"] is None
    assert result["pre_activation"] is True
    assert result["learning_enabled"] is False
    assert result["status_reason"] == "learning_disabled_no_live_history"
