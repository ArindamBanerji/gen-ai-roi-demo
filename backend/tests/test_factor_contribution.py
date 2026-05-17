from types import SimpleNamespace

import numpy as np
from fastapi.testclient import TestClient

from app.domains.soc.config import SOCDomainConfig
from app.main import app
from app.routers.framework_router import compute_factor_contribution


client = TestClient(app, raise_server_exceptions=False)


def _factor_names():
    return [factor.id for factor in SOCDomainConfig().factors]


def _total_pct(factors):
    return sum(item["contribution_pct"] for item in factors)


def test_compute_factor_contribution_unit():
    factors, method = compute_factor_contribution(
        np.array(
            [
                [0.1, 0.8, 0.2, 0.4, 0.05, 0.3],
                [0.2, 0.6, 0.1, 0.5, 0.10, 0.4],
            ]
        ),
        _factor_names(),
    )

    assert method == "dk_weights"
    assert len(factors) == 6
    assert 99.0 <= _total_pct(factors) <= 101.0
    assert [item["rank"] for item in factors] == [1, 2, 3, 4, 5, 6]
    assert factors[0]["name"] == "asset_criticality"
    assert factors[0]["contribution_pct"] >= factors[-1]["contribution_pct"]


def test_compute_factor_contribution_uniform_fallback():
    factors, method = compute_factor_contribution(None, _factor_names())

    assert method == "uniform"
    assert len(factors) == 6
    assert 99.0 <= _total_pct(factors) <= 101.0
    assert [item["rank"] for item in factors] == [1, 2, 3, 4, 5, 6]


def test_compute_factor_contribution_unexpected_shape_falls_back_to_uniform():
    factors, method = compute_factor_contribution([[0.1, 0.2]], _factor_names())

    assert method == "uniform"
    assert len(factors) == 6
    assert 99.0 <= _total_pct(factors) <= 101.0


def test_compute_factor_contribution_zero_weights_falls_back_to_uniform():
    factors, method = compute_factor_contribution(np.zeros((2, 6)), _factor_names())

    assert method == "uniform"
    assert len(factors) == 6
    assert 99.0 <= _total_pct(factors) <= 101.0


def test_factor_contribution_endpoint_returns_200(monkeypatch):
    monkeypatch.setattr(
        "app.services.gae_state.get_profile_scorer",
        lambda: None,
    )

    response = client.get("/api/soc/factor-contribution")

    assert response.status_code == 200


def test_factor_contribution_has_six_factors(monkeypatch):
    monkeypatch.setattr(
        "app.services.gae_state.get_profile_scorer",
        lambda: None,
    )

    response = client.get("/api/soc/factor-contribution")

    assert len(response.json()["factors"]) == 6


def test_factor_contribution_percentages_sum_to_100(monkeypatch):
    monkeypatch.setattr(
        "app.services.gae_state.get_profile_scorer",
        lambda: None,
    )

    response = client.get("/api/soc/factor-contribution")

    assert 99.0 <= _total_pct(response.json()["factors"]) <= 101.0


def test_factor_contribution_sorted_by_rank(monkeypatch):
    monkeypatch.setattr(
        "app.services.gae_state.get_profile_scorer",
        lambda: None,
    )

    response = client.get("/api/soc/factor-contribution")
    factors = response.json()["factors"]

    assert [item["rank"] for item in factors] == sorted(item["rank"] for item in factors)


def test_factor_contribution_has_method(monkeypatch):
    monkeypatch.setattr(
        "app.services.gae_state.get_profile_scorer",
        lambda: None,
    )

    response = client.get("/api/soc/factor-contribution")

    assert response.json()["method"] in {"dk_weights", "uniform"}


def test_factor_contribution_top_and_weakest_differ(monkeypatch):
    monkeypatch.setattr(
        "app.services.gae_state.get_profile_scorer",
        lambda: None,
    )

    response = client.get("/api/soc/factor-contribution")
    body = response.json()

    assert body["top_factor"] is not None
    assert body["weakest_factor"] is not None
    assert body["top_factor"] != body["weakest_factor"]


def test_factor_contribution_signal_strength_valid(monkeypatch):
    monkeypatch.setattr(
        "app.services.gae_state.get_profile_scorer",
        lambda: None,
    )

    response = client.get("/api/soc/factor-contribution")
    strengths = {item["signal_strength"] for item in response.json()["factors"]}

    assert strengths <= {"high", "medium", "low"}


def test_factor_contribution_uses_kernel_weights_when_available(monkeypatch):
    scorer = SimpleNamespace(
        scoring_kernel=SimpleNamespace(
            raw_weights=np.array([0.1, 0.7, 0.2, 0.4, 0.05, 0.3])
        )
    )
    monkeypatch.setattr(
        "app.services.gae_state.get_profile_scorer",
        lambda: scorer,
    )

    response = client.get("/api/soc/factor-contribution")
    body = response.json()

    assert body["method"] == "dk_weights"
    assert body["top_factor"] == "asset_criticality"
