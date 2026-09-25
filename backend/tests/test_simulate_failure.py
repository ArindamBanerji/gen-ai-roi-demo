"""Regression coverage for the SOC gate-transition demo endpoint."""

from contextlib import asynccontextmanager
from threading import Lock
from types import SimpleNamespace
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import evolution


class _LockBackedScorer:
    """Small scorer-shaped object matching the production lock failure mode."""

    def __init__(self) -> None:
        self.n_factors = 4
        self.n_actions = 3
        self.n_categories = 2
        self.decision_count = 11
        self._conservation_status = "GREEN"
        self.runtime_lock = Lock()

    def score(self, factors: list[float], category_index: int) -> Any:
        del factors, category_index
        return SimpleNamespace(action_index=0, confidence=0.95)

    def update(self, **kwargs: Any) -> None:
        del kwargs
        self.decision_count += 1

    def set_conservation_status(self, status: str) -> None:
        self._conservation_status = status


def test_simulate_failure_accepts_magnitude_and_restores_lock_backed_state(
    monkeypatch: Any,
) -> None:
    scorer = _LockBackedScorer()

    @asynccontextmanager
    async def fake_acquire_scorer() -> Any:
        yield scorer

    monkeypatch.setattr(evolution, "acquire_scorer", fake_acquire_scorer)
    app = FastAPI()
    app.include_router(evolution.router, prefix="/api")

    with TestClient(app) as client:
        response = client.post(
            "/api/eval/simulate-failure", json={"magnitude": 0.15}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["conservation_status"] == "AMBER"
    assert body["magnitude"] == 0.15
    assert body["decisions_injected"] == 20
    assert scorer.decision_count == 11
    assert scorer._conservation_status == "GREEN"
    assert scorer.runtime_lock.acquire(blocking=False)
    scorer.runtime_lock.release()


def test_simulate_failure_rejects_invalid_magnitude() -> None:
    app = FastAPI()
    app.include_router(evolution.router, prefix="/api")

    with TestClient(app) as client:
        response = client.post(
            "/api/eval/simulate-failure", json={"magnitude": 0.0}
        )

    assert response.status_code == 422
