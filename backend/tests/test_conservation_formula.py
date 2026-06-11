from __future__ import annotations

import math
import warnings
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from gae.calibration import check_conservation, derive_theta_min

from app.domains.soc.config import SOCDomainConfig, compute_theta_min
from app.services.learning_health import CONSERVATIVE_THETA_MIN, LearningHealthMonitor


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


class _FakeNeo4j:
    def __init__(self, rows: list[dict]):
        self.rows = rows

    async def run_query(self, query: str) -> list[dict]:
        if "MATCH (h:HealthLog)" in query:
            return [{"red_days": 0}]
        return self.rows


def test_theta_min_canonical_examples():
    assert compute_theta_min(0.25, 200) == pytest.approx(0.4706, rel=1e-4)
    assert compute_theta_min(0.25, 50) == pytest.approx(1.8824, rel=1e-4)


def test_theta_min_alpha_is_coverage_not_learning_rate():
    coverage = 0.25
    plausible_learning_rate = 0.05
    V = 200

    coverage_threshold = compute_theta_min(coverage, V)
    learning_rate_threshold = compute_theta_min(plausible_learning_rate, V)

    assert coverage_threshold == pytest.approx(23.53 / (coverage * V))
    assert learning_rate_threshold != pytest.approx(coverage_threshold)


def test_theta_min_not_penalty_ratio():
    penalty_ratio = SOCDomainConfig().asymmetry_ratio
    coverage = 0.25
    V = 200

    assert penalty_ratio == 20.0
    assert compute_theta_min(coverage, V) == pytest.approx(23.53 / (coverage * V))
    assert compute_theta_min(penalty_ratio, V) != pytest.approx(
        compute_theta_min(coverage, V)
    )


def test_derive_theta_min_deprecated():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        value = derive_theta_min()

    assert value > 0
    assert any(item.category is DeprecationWarning for item in caught)


def test_conservation_check_matches_gae_signature():
    alpha = 0.25
    q = 0.80
    V = 200
    theta_min = compute_theta_min(alpha, V)

    result = check_conservation(alpha, q, V, theta_min)

    assert result.signal == pytest.approx(alpha * q * V)
    assert result.theta_min == pytest.approx(theta_min)
    assert result.passed is True


@pytest.mark.asyncio
async def test_learning_health_uses_soc_coverage_not_alpha_effective(monkeypatch):
    history = _history(400, alpha_effective=0.01, outcome=1)
    state = _FakeState(history)
    graph = _FakeNeo4j([
        {"category": "credential_access", "verified": 50, "correct": 40, "overrides": 5},
        {"category": "malware_execution", "verified": 50, "correct": 40, "overrides": 5},
        {"category": "lateral_movement", "verified": 50, "correct": 40, "overrides": 5},
    ])

    monkeypatch.setattr("app.services.learning_health.get_learning_state", lambda: state)
    monkeypatch.setattr("app.services.learning_health._is_learning_enabled", lambda: True)
    result = await LearningHealthMonitor.evaluate(graph)

    assert result["components"]["alpha"] == pytest.approx(0.5)
    assert result["components"]["q"] == pytest.approx(0.80)
    assert result["components"]["alpha_source"] == "soc_verified_category_coverage"
    assert result["components"]["alpha"] != pytest.approx(0.01)
    assert result["signal"] == pytest.approx(0.5 * 0.80 * result["components"]["V"])


@pytest.mark.asyncio
async def test_learning_health_zero_coverage_is_conservative(monkeypatch):
    history = _history(400, alpha_effective=0.50, outcome=1)
    state = _FakeState(history)
    graph = _FakeNeo4j([])

    monkeypatch.setattr("app.services.learning_health.get_learning_state", lambda: state)
    monkeypatch.setattr("app.services.learning_health._is_learning_enabled", lambda: True)
    result = await LearningHealthMonitor.evaluate(graph)

    assert result["components"]["alpha"] == 0.0
    assert result["components"]["q"] == 0.0
    assert result["theta_min"] == pytest.approx(CONSERVATIVE_THETA_MIN)
    assert not math.isinf(result["theta_min"])
    assert result["conservation"]["passed"] is False


@pytest.mark.asyncio
async def test_no_graph_fallback_does_not_use_legacy_learning_alpha(monkeypatch):
    history = _history(400, alpha_effective=0.50, outcome=1)
    state = _FakeState(history)

    monkeypatch.setattr("app.services.learning_health.get_learning_state", lambda: state)
    monkeypatch.setattr("app.state.graph_snapshot._snapshot", None)

    result = await LearningHealthMonitor.evaluate(None)

    assert result["components"]["alpha_source"] == "soc_coverage_unavailable"
    assert result["components"]["alpha"] == 0.0
    assert result["components"]["q"] == pytest.approx(1.0)
    assert result["components"]["alpha"] != pytest.approx(0.50)
    assert result["signal"] == 0.0
    assert result["theta_min"] == pytest.approx(CONSERVATIVE_THETA_MIN)
    assert result["conservation"]["passed"] is False
    assert result["status"] == "RED"


def test_baseline_does_not_use_legacy_learning_alpha():
    history = _history(400, alpha_effective=0.50, outcome=1)

    baseline, baseline_std = LearningHealthMonitor._build_calibration_baseline(history)

    assert baseline == 0.0
    assert baseline_std == 0.0
