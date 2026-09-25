"""Focused tests for SOC's three-layer conservation reporting."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.learning_health import LearningHealthMonitor


def _history(correct: int, incorrect: int = 0) -> list[SimpleNamespace]:
    return [
        SimpleNamespace(outcome=1, alpha_effective=0.02)
        for _ in range(correct)
    ] + [
        SimpleNamespace(outcome=-1, alpha_effective=0.02)
        for _ in range(incorrect)
    ]


def test_soc_grate_no_fire_clean() -> None:
    layers = LearningHealthMonitor._gate_layers(_history(400), True, 10.0, 0.764)
    assert layers["g_rate"]["active"] is False
    assert layers["g_rate"]["short_window_count"] == 20


def test_soc_grate_fires_sudden_drop() -> None:
    layers = LearningHealthMonitor._gate_layers(
        _history(400) + _history(0, 20), True, 10.0, 0.764
    )
    assert layers["g_rate"]["active"] is True
    assert layers["g_rate"]["short_accuracy"] == 0.0


def test_soc_grate_insufficient_window() -> None:
    layers = LearningHealthMonitor._gate_layers(_history(19), True, 10.0, 0.764)
    assert layers["g_rate"]["active"] is False
    assert layers["g_rate"]["short_window_count"] == 19


def test_soc_grate_threshold_085() -> None:
    layers = LearningHealthMonitor._gate_layers(_history(400), True, 10.0, 0.764)
    assert layers["g_rate"]["m_rate"] == pytest.approx(0.85)
    assert layers["g_rate"]["threshold"] == pytest.approx(0.85)


def test_soc_three_layer_green() -> None:
    layers = LearningHealthMonitor._gate_layers(_history(400), True, 10.0, 0.764)
    assert not layers["g_abs"]["active"]
    assert not layers["g_rel"]["active"]
    assert not layers["g_rate"]["active"]


def test_soc_three_layer_grate_fires() -> None:
    layers = LearningHealthMonitor._gate_layers(
        _history(400) + _history(0, 20), True, 10.0, 0.764
    )
    assert layers["g_rate"]["active"]
    assert layers["g_abs"]["active"] is False


def test_soc_grate_recovery() -> None:
    layers = LearningHealthMonitor._gate_layers(
        _history(400) + _history(0, 20) + _history(20), True, 10.0, 0.764
    )
    assert layers["g_rate"]["active"] is False
    assert layers["g_rate"]["short_accuracy"] == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_soc_conservation_status_has_grate(monkeypatch: pytest.MonkeyPatch) -> None:
    state = SimpleNamespace(decision_count=420, history=_history(400) + _history(0, 20))
    monkeypatch.setattr("app.services.learning_health.get_learning_state", lambda: state)

    async def fake_components(comps: dict, graph_service: object = None) -> dict:
        return _with_soc_components(comps)

    monkeypatch.setattr(
        "app.services.learning_health.LearningHealthMonitor._apply_soc_conservation_components",
        fake_components,
    )
    result = await LearningHealthMonitor.evaluate(graph_service=None)
    assert {"g_abs", "g_rel", "g_rate"}.issubset(result)
    assert result["g_rate"]["w_short"] == 20
    assert result["g_rate"]["m_rate"] == pytest.approx(0.85)


def _with_soc_components(comps: dict) -> dict:
    updated = dict(comps)
    updated.update(
        {
            "alpha": 1.0,
            "q": 400 / 420,
            "V": 420.0,
            "n": 420,
            "categories_total": 5,
            "categories_with_data": 5,
            "verified_decisions": 420,
            "correct_verified_decisions": 400,
            "override_rate": 0.0,
            "complacency_advisory": False,
        }
    )
    return updated
