from __future__ import annotations

from contextlib import asynccontextmanager
from copy import deepcopy
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import evolution


class _FakeScorer:
    def __init__(self) -> None:
        self.n_factors = 6
        self.n_actions = 4
        self.n_categories = 3
        self.decision_count = 7
        self.centroids = [[[0.2, 0.4, 0.6]]]
        self._conservation_status = "GREEN"

    def score(self, _factors, category_index=0):
        return SimpleNamespace(action_index=category_index % self.n_actions, confidence=0.91)

    def update(self, **_kwargs) -> None:
        self.decision_count += 1
        self.centroids[0][0][0] += 0.1
        self._conservation_status = "RED"

    def set_conservation_status(self, status: str) -> None:
        self._conservation_status = status

    def trajectory(self) -> dict:
        return {
            "decision_count": self.decision_count,
            "centroids": deepcopy(self.centroids),
            "conservation_status": self._conservation_status,
        }


def test_simulate_failure_does_not_degrade_live_scorer(monkeypatch):
    scorer = _FakeScorer()

    @asynccontextmanager
    async def fake_acquire_scorer():
        yield scorer

    monkeypatch.setattr(evolution, "acquire_scorer", fake_acquire_scorer)

    app = FastAPI()
    app.include_router(evolution.router, prefix="/api")
    client = TestClient(app)

    state_before = scorer.trajectory()
    response = client.post("/api/eval/simulate-failure")
    state_after = scorer.trajectory()

    assert response.status_code == 200
    assert response.json()["conservation_status"] == "AMBER"
    assert state_after == state_before
