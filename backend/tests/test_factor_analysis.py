import asyncio
from unittest.mock import patch

import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.services import factor_analysis


client = TestClient(app, raise_server_exceptions=False)


def _run(awaitable):
    return asyncio.run(awaitable)


class _KernelStub:
    pass


class _ScorerStub:
    def __init__(self, centroids):
        self.centroids = np.asarray(centroids, dtype=np.float64)
        self.scoring_kernel = _KernelStub()


def _make_centroids():
    mu = np.full((6, 4, 6), 0.5, dtype=np.float64)
    for c in range(6):
        mu[c, 0, :] = [0.9, 0.8, 0.8, 0.7, 0.7, 0.2]
        mu[c, 1, :] = [0.6, 0.6, 0.6, 0.6, 0.6, 0.4]
        mu[c, 2, :] = [0.2, 0.3, 0.2, 0.2, 0.2, 0.9]
        mu[c, 3, :] = [0.4, 0.4, 0.4, 0.4, 0.4, 0.7]
    mu[4, 0, :] = [0.52, 0.50, 0.51, 0.49, 0.50, 0.50]
    mu[4, 1, :] = [0.50, 0.49, 0.50, 0.48, 0.49, 0.50]
    mu[4, 2, :] = [0.48, 0.50, 0.49, 0.51, 0.50, 0.50]
    mu[4, 3, :] = [0.51, 0.51, 0.50, 0.50, 0.51, 0.49]
    return mu


def _install_happy_path(monkeypatch):
    centroids = _make_centroids()
    bootstrap = np.full((6, 4, 6), 0.5, dtype=np.float64)
    monkeypatch.setattr(factor_analysis, "get_profile_scorer", lambda: _ScorerStub(centroids))
    monkeypatch.setattr(factor_analysis, "get_mu_zero", lambda: bootstrap)


def test_run_factor_analysis_returns_six_categories(monkeypatch):
    _install_happy_path(monkeypatch)

    result = _run(factor_analysis.run_factor_analysis())

    assert len(result["current"]["categories"]) == 6


def test_run_factor_analysis_proposal_exists_for_low_snr_category(monkeypatch):
    _install_happy_path(monkeypatch)

    result = _run(factor_analysis.run_factor_analysis())

    proposal = result["current"]["proposed_improvement"]
    assert proposal
    assert proposal["target_category"] == "insider_threat"


def test_run_factor_analysis_overall_snr_positive(monkeypatch):
    _install_happy_path(monkeypatch)

    result = _run(factor_analysis.run_factor_analysis())

    assert result["current"]["overall_snr"] > 0


def test_run_factor_analysis_ceiling_in_0_to_100(monkeypatch):
    _install_happy_path(monkeypatch)

    result = _run(factor_analysis.run_factor_analysis())

    assert 0.0 <= result["current"]["overall_ceiling"] <= 100.0


def test_run_factor_analysis_includes_bootstrap_comparison(monkeypatch):
    _install_happy_path(monkeypatch)

    result = _run(factor_analysis.run_factor_analysis())

    assert result["bootstrap"] is not None
    assert result["snr_improved"] is not None


def test_run_factor_analysis_cold_start_returns_error_status(monkeypatch):
    monkeypatch.setattr(factor_analysis, "get_profile_scorer", lambda: None)

    result = _run(factor_analysis.run_factor_analysis())

    assert result["status"] == "cold_start"
    assert "error" in result


def test_factor_analysis_endpoint_returns_503_on_cold_start():
    with patch("app.services.factor_analysis.get_profile_scorer", return_value=None):
        response = client.get("/api/soc/factor-analysis")
    assert response.status_code == 503
    body = response.json()
    assert body["detail"]["status"] == "cold_start"
    assert "error" in body["detail"]


def test_factor_analysis_endpoint_returns_200(monkeypatch):
    _install_happy_path(monkeypatch)

    response = client.get("/api/soc/factor-analysis")

    assert response.status_code == 200
    body = response.json()
    assert len(body["current"]["categories"]) == 6


def test_factor_analysis_summary_has_recommendation(monkeypatch):
    _install_happy_path(monkeypatch)

    response = client.get("/api/soc/factor-analysis/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["recommendation"]
    assert "weakest category" in body["recommendation"].lower()


def test_full_report_has_recommendation_field(monkeypatch):
    _install_happy_path(monkeypatch)

    response = client.get("/api/soc/factor-analysis")

    assert response.status_code == 200
    body = response.json()
    assert "proposed_improvement" in body["current"]
    proposal = body["current"]["proposed_improvement"]
    if proposal:
        assert "recommendation" in proposal, (
            f"proposed_improvement must have 'recommendation' key; got {list(proposal.keys())}"
        )


def test_summary_has_weakest_category_ceiling(monkeypatch):
    _install_happy_path(monkeypatch)

    response = client.get("/api/soc/factor-analysis/summary")

    assert response.status_code == 200
    body = response.json()
    assert "weakest_category_ceiling" in body, (
        f"Summary must include 'weakest_category_ceiling'; got {list(body.keys())}"
    )
