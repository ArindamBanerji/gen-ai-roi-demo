"""Regression tests for SOC conservation wiring fixes."""

from types import SimpleNamespace
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
import numpy as np
import pytest

from app.routers import compat_router, framework_router, triage
from app.services import learning_health


def _learning_state() -> SimpleNamespace:
    return SimpleNamespace(
        W=np.zeros((4, 6), dtype=np.float64),
        n_actions=4,
        n_factors=6,
        profile=SimpleNamespace(learning_rate=0.02),
        decision_count=0,
        history=[],
    )


def test_outcome_appends_history() -> None:
    state = _learning_state()
    triage._append_verified_outcome_history(state, correct=True, confidence=0.9)
    assert len(state.history) == 1


def test_history_contains_correctness() -> None:
    state = _learning_state()
    triage._append_verified_outcome_history(state, correct=False, confidence=0.4)
    assert state.history[0].outcome == -1
    assert state.history[0].confidence_at_decision == 0.4


def test_age_failure_returns_503(monkeypatch: Any) -> None:
    async def fail(_graph: Any) -> dict[str, Any]:
        raise RuntimeError("AGE query failed for SOC conservation stats")

    monkeypatch.setattr(learning_health.LearningHealthMonitor, "evaluate", fail)
    app = FastAPI()
    app.include_router(framework_router.router, prefix="/api")
    response = TestClient(app).get("/api/soc/learning-health")
    assert response.status_code == 503


def test_503_has_structured_body(monkeypatch: Any) -> None:
    async def fail(_graph: Any) -> dict[str, Any]:
        raise RuntimeError("AGE unavailable")

    monkeypatch.setattr(learning_health.LearningHealthMonitor, "evaluate", fail)
    app = FastAPI()
    app.include_router(framework_router.router, prefix="/api")
    body = TestClient(app).get("/api/soc/learning-health").json()
    assert body == {
        "status": "UNAVAILABLE",
        "reason": "Conservation dependency unavailable",
        "detail": "AGE unavailable",
    }


def test_calibration_includes_layers(monkeypatch: Any) -> None:
    state = _learning_state()
    state.decision_count = 10
    state.history = [SimpleNamespace(outcome=1, alpha_effective=0.02) for _ in range(10)]

    async def components(_comps: dict[str, Any], _graph: Any) -> dict[str, Any]:
        return {"alpha": 1.0, "q": 1.0, "V": 10.0, "n": 10}

    monkeypatch.setattr(learning_health, "get_learning_state", lambda: state)
    monkeypatch.setattr(learning_health, "_is_learning_enabled", lambda: True)
    monkeypatch.setattr(
        learning_health.LearningHealthMonitor,
        "_apply_soc_conservation_components",
        staticmethod(components),
    )
    result = __import__("asyncio").run(learning_health.LearningHealthMonitor.evaluate(None))
    assert result["status"] == "CALIBRATING"
    assert "g_rel" in result
    assert "g_rate" in result


def test_amber_text_grate() -> None:
    text = learning_health.LearningHealthMonitor._interpret(
        "AMBER", 1.0, 2.0, 0,
        {"g_rate": {"active": True}, "g_rel": {"active": False}},
    )
    assert text == "Short-window accuracy dropped below threshold"


def test_amber_text_grel() -> None:
    text = learning_health.LearningHealthMonitor._interpret(
        "AMBER", 1.0, 2.0, 0,
        {"g_rate": {"active": False}, "g_rel": {"active": True}},
    )
    assert text == "Accuracy below 70% of baseline"


def test_compat_alias_catches_error(monkeypatch: Any) -> None:
    async def fail() -> dict[str, Any]:
        raise RuntimeError("AGE unavailable")

    monkeypatch.setattr(framework_router, "learning_health", fail)
    app = FastAPI()
    app.include_router(compat_router.router, prefix="/api")
    response = TestClient(app).get("/api/conservation/status")
    assert response.status_code == 503
    assert response.json()["status"] == "UNAVAILABLE"


@pytest.mark.asyncio
async def test_conservation_and_verified_count_same_population() -> None:
    queries: list[str] = []

    class Graph:
        async def run_query(self, query: str):
            queries.append(query)
            return [{"category": "credential_access", "verified": 3, "correct": 2, "overrides": 0}]

    result = await learning_health._query_soc_verified_conservation_stats(Graph())
    assert result is not None
    assert result["verified_decisions"] == 3
    predicate = learning_health._soc_verified_predicate("d")
    assert len(queries) == 1
    assert predicate in queries[0]


def test_conservation_predicate_documented() -> None:
    assert "verified_at_epoch" in learning_health.SOC_VERIFIED_POPULATION_RULE
    assert "canonical SOC categories" in learning_health.SOC_VERIFIED_POPULATION_RULE
