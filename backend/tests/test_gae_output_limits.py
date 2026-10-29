"""Behavioral coverage for bounded GAE chart output."""

import asyncio
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import gae


ENDPOINTS = (
    ("confidence-trajectory", "trajectories"),
    ("weight-evolution", "evolution"),
    ("trust-curve", "curves"),
)


def _state(history_count: int) -> SimpleNamespace:
    history = [
        SimpleNamespace(
            decision_number=index,
            action_name="escalate" if index % 2 else "investigate",
            outcome=1 if index % 3 else -1,
            confidence_at_decision=0.5 + (index % 40) / 100,
            timestamp=1_700_000_000.0 + index,
            delta_applied=np.full(6, index / 10_000),
            W_after=np.full((4, 6), index / 1_000),
        )
        for index in range(1, history_count + 1)
    ]
    return SimpleNamespace(history=history, decision_count=history_count)


def _get(endpoint: str, history_count: int, limit: int | None = None):
    test_app = FastAPI()
    test_app.include_router(gae.router, prefix="/api")
    params = {} if limit is None else {"limit": limit}
    with patch.object(gae, "get_learning_state", return_value=_state(history_count)):
        return TestClient(test_app).get(f"/api/gae/{endpoint}", params=params)


def _points(payload: dict, data_key: str) -> list[dict]:
    data = payload[data_key]
    if isinstance(data, list):
        return data
    return [point for series in data.values() for point in series]


@pytest.mark.parametrize(("endpoint", "data_key"), ENDPOINTS)
def test_default_limit(endpoint: str, data_key: str) -> None:
    payload = _get(endpoint, 1205).json()
    assert len(_points(payload, data_key)) == 500
    assert payload["returned_count"] == 500
    assert payload["clamped"] is False


@pytest.mark.parametrize(("endpoint", "data_key"), ENDPOINTS)
def test_explicit_limit(endpoint: str, data_key: str) -> None:
    payload = _get(endpoint, 25, limit=10).json()
    assert len(_points(payload, data_key)) == 10
    assert payload["returned_count"] == 10


@pytest.mark.parametrize(("endpoint", "data_key"), ENDPOINTS)
def test_max_limit_clamped(endpoint: str, data_key: str) -> None:
    response = _get(endpoint, 1205, limit=2000)
    assert response.status_code == 200
    payload = response.json()
    assert len(_points(payload, data_key)) == 1000
    assert payload["returned_count"] == 1000
    assert payload["clamped"] is True


@pytest.mark.parametrize(("endpoint", "data_key"), ENDPOINTS)
def test_newest_retained(endpoint: str, data_key: str) -> None:
    payload = _get(endpoint, 25, limit=10).json()
    decision_numbers = {
        point["decision_number"] for point in _points(payload, data_key)
    }
    assert 25 in decision_numbers
    assert min(decision_numbers) == 16


@pytest.mark.parametrize(("endpoint", "data_key"), ENDPOINTS)
def test_grouping_preserved(endpoint: str, data_key: str) -> None:
    payload = _get(endpoint, 20, limit=10).json()
    data = payload[data_key]
    if endpoint == "weight-evolution":
        assert {point["action"] for point in data} == {"escalate", "investigate"}
    else:
        assert set(data) == {"escalate", "investigate"}
        assert sum(len(series) for series in data.values()) == 10


@pytest.mark.parametrize(("endpoint", "data_key"), ENDPOINTS)
def test_empty_state(endpoint: str, data_key: str) -> None:
    payload = _get(endpoint, 0).json()
    assert payload[data_key] == ([] if data_key == "evolution" else {})
    assert payload["total_available"] == 0
    assert payload["returned_count"] == 0
    assert payload["clamped"] is False


@pytest.mark.parametrize(("endpoint", "data_key"), ENDPOINTS)
def test_response_envelope(endpoint: str, data_key: str) -> None:
    payload = _get(endpoint, 12, limit=10).json()
    assert isinstance(payload["total_available"], int)
    assert isinstance(payload["returned_count"], int)
    assert isinstance(payload["clamped"], bool)
    assert payload["total_available"] == 12
    assert payload["returned_count"] == 10
    assert payload["clamped"] is False
    assert "message" in payload


@pytest.mark.parametrize(("endpoint", "data_key"), ENDPOINTS)
def test_limit_zero(endpoint: str, data_key: str) -> None:
    response = _get(endpoint, 25, limit=0)

    assert response.status_code == 422


@pytest.mark.parametrize(("endpoint", "data_key"), ENDPOINTS)
def test_limit_negative(endpoint: str, data_key: str) -> None:
    response = _get(endpoint, 25, limit=-1)

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("endpoint_function", "data_key"),
    (
        (gae.gae_confidence_trajectory, "trajectories"),
        (gae.gae_weight_evolution, "evolution"),
        (gae.gae_trust_curve, "curves"),
    ),
)
def test_limit_none_direct_call(endpoint_function, data_key: str) -> None:
    with patch.object(gae, "get_learning_state", return_value=_state(1205)):
        payload = asyncio.run(endpoint_function())

    assert len(_points(payload, data_key)) == 500
    assert payload["returned_count"] == 500
    assert payload["clamped"] is False


@pytest.mark.parametrize(("endpoint", "data_key"), ENDPOINTS)
def test_clamped_flag(endpoint: str, data_key: str) -> None:
    payload = _get(endpoint, 1205, limit=2000).json()

    assert payload["returned_count"] == 1000
    assert payload["clamped"] is True


@pytest.mark.parametrize(("endpoint", "data_key"), ENDPOINTS)
def test_not_clamped(endpoint: str, data_key: str) -> None:
    payload = _get(endpoint, 1205, limit=100).json()

    assert payload["returned_count"] == 100
    assert payload["clamped"] is False


def test_trust_curve_limit_preserves_cumulative_values() -> None:
    full = _get("trust-curve", 80, limit=1000).json()
    limited = _get("trust-curve", 80, limit=10).json()
    full_by_decision = {
        point["decision_number"]: point["trust_level"]
        for point in _points(full, "curves")
    }
    limited_by_decision = {
        point["decision_number"]: point["trust_level"]
        for point in _points(limited, "curves")
    }

    assert limited_by_decision == {
        decision_number: full_by_decision[decision_number]
        for decision_number in limited_by_decision
    }
