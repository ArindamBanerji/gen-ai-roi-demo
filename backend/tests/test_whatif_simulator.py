from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domains.soc.config import SCORER_ACTIONS, SOC_CATEGORIES, SOC_PROFILE_CENTROIDS
from app.routers.whatif_router import router as whatif_router
import app.services.whatif_service as whatif_service
from app.services.whatif_service import PRESETS, WhatIfScenario, run_whatif


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(whatif_router, prefix="/api")
    return TestClient(app)


def test_healthy_deployment_stays_green():
    result = run_whatif(PRESETS["healthy_deployment"])
    assert result.summary["days_green"] == PRESETS["healthy_deployment"].horizon_days
    assert result.summary["days_amber"] == 0
    assert result.summary["days_red"] == 0
    assert result.summary["final_status"] == "GREEN"


def test_gradual_degradation_transitions():
    result = run_whatif(PRESETS["gradual_degradation"])
    statuses = [day["status"] for day in result.daily_trajectory]
    assert "GREEN" in statuses
    assert "AMBER" in statuses
    assert "RED" in statuses
    assert result.summary["first_amber_day"] is not None
    assert result.summary["first_red_day"] is not None


def test_sudden_disruption_triggers_red():
    result = run_whatif(PRESETS["sudden_disruption"])
    red_days = [day for day in result.daily_trajectory if day["status"] == "RED"]
    assert red_days
    assert result.summary["first_red_day"] is not None
    assert result.summary["final_status"] == "RED"


def test_low_volume_is_amber():
    result = run_whatif(PRESETS["low_volume_stress"])
    assert result.summary["final_status"] == "AMBER"
    assert result.summary["days_amber"] == PRESETS["low_volume_stress"].horizon_days


def test_high_automation_green_at_good_quality():
    result = run_whatif(PRESETS["high_automation_good_quality"])
    assert result.summary["final_status"] == "GREEN"
    assert result.summary["days_red"] == 0


def test_trajectory_length_matches_horizon():
    scenario = WhatIfScenario(horizon_days=17)
    result = run_whatif(scenario)
    assert len(result.daily_trajectory) == 17


def test_signal_equals_alpha_times_q_times_v():
    scenario = WhatIfScenario(alpha=0.25, V=20.0, q_initial=0.5, q_target=0.5, horizon_days=3)
    result = run_whatif(scenario)
    for day in result.daily_trajectory:
        assert day["signal"] == 2.5


def test_does_not_touch_production_state():
    scenario = WhatIfScenario()
    result = run_whatif(scenario)
    assert result.summary["final_status"] in {"GREEN", "AMBER", "RED"}
    assert result.scenario["name"] == "custom"
    assert "score_alert" not in run_whatif.__code__.co_names
    assert "get_profile_scorer" not in run_whatif.__code__.co_names
    assert "get_learning_state" not in run_whatif.__code__.co_names
    assert "save_learning_state" not in run_whatif.__code__.co_names


def test_presets_returns_5_scenarios():
    client = _client()
    response = client.get("/api/whatif/presets")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 5
    assert len(body["presets"]) == 5


def test_each_preset_has_required_fields():
    client = _client()
    response = client.get("/api/whatif/presets")
    body = response.json()
    required = {
        "name",
        "description",
        "alpha",
        "V",
        "q_initial",
        "q_target",
        "horizon_days",
        "eta",
        "n_half",
        "t_max_days",
    }
    for preset in body["presets"].values():
        assert required.issubset(preset.keys())


def test_preset_by_name_returns_results():
    client = _client()
    response = client.get("/api/whatif/presets/healthy_deployment")
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["final_status"] == "GREEN"
    assert len(body["daily_trajectory"]) == PRESETS["healthy_deployment"].horizon_days


def test_q_zero_is_red():
    scenario = WhatIfScenario(q_initial=0.0, q_target=0.0, horizon_days=5)
    result = run_whatif(scenario)
    assert all(day["status"] == "RED" for day in result.daily_trajectory)


def test_alpha_zero_produces_zero_signal():
    scenario = WhatIfScenario(alpha=0.0, q_initial=1.0, q_target=1.0, horizon_days=5)
    result = run_whatif(scenario)
    assert all(day["signal"] == 0.0 for day in result.daily_trajectory)
    assert all(day["status"] != "GREEN" for day in result.daily_trajectory)


def test_horizon_one_day():
    scenario = WhatIfScenario(horizon_days=1, q_initial=0.9, q_target=0.6)
    result = run_whatif(scenario)
    assert len(result.daily_trajectory) == 1
    assert result.daily_trajectory[0]["q"] == 0.6


def test_disruption_on_day_zero():
    scenario = WhatIfScenario(
        alpha=0.25,
        V=30.0,
        q_initial=0.20,
        q_target=0.20,
        horizon_days=3,
        disruption_day=0,
        disruption_delta=-0.15,
    )
    result = run_whatif(scenario)
    assert result.daily_trajectory[0]["q"] == 0.05
    assert result.daily_trajectory[0]["status"] == "RED"


# FIX-13: q_ramp_days is backend-authoritative ----------------------------

def test_ramp_days_produces_gradual_transition():
    scenario = WhatIfScenario(
        q_initial=0.85,
        q_target=0.15,
        q_ramp_days=60,
        horizon_days=90,
        alpha=0.25,
        V=200.0,
    )
    result = run_whatif(scenario)
    qs = [day["q"] for day in result.daily_trajectory]
    # First day should be near q_initial, last should be at q_target
    assert qs[0] == pytest.approx(0.85, abs=1e-4)
    assert qs[-1] == pytest.approx(0.15, abs=1e-4)
    # Trajectory must be monotonically decreasing over the ramp period
    assert all(qs[i] >= qs[i + 1] for i in range(59))


def test_ramp_days_zero_is_instant():
    scenario = WhatIfScenario(
        q_initial=0.85,
        q_target=0.15,
        q_ramp_days=0,
        horizon_days=5,
    )
    result = run_whatif(scenario)
    # Every day should have q == q_target immediately
    for day in result.daily_trajectory:
        assert day["q"] == pytest.approx(0.15, abs=1e-4)


def test_ramp_with_disruption():
    scenario = WhatIfScenario(
        q_initial=0.85,
        q_target=0.85,
        q_ramp_days=0,
        horizon_days=60,
        disruption_day=30,
        disruption_delta=-0.30,
        alpha=0.25,
        V=200.0,
    )
    result = run_whatif(scenario)
    pre = result.daily_trajectory[29]["q"]
    post = result.daily_trajectory[30]["q"]
    assert pre == pytest.approx(0.85, abs=1e-4)
    assert post == pytest.approx(0.55, abs=1e-4)


# FIX-15: HTTP 400 on invalid input -------------------------------------

def test_invalid_q_rejected():
    client = _client()
    response = client.post("/api/whatif/project", json={"q_initial": 1.5, "V": 200.0})
    assert response.status_code == 400
    assert any("q_initial" in e for e in response.json()["detail"])


def test_invalid_alpha_rejected():
    client = _client()
    response = client.post("/api/whatif/project", json={"alpha": -0.1, "V": 200.0})
    assert response.status_code == 400
    assert any("alpha" in e for e in response.json()["detail"])


def test_invalid_v_rejected():
    client = _client()
    response = client.post("/api/whatif/project", json={"alpha": 0.25, "V": 0.0})
    assert response.status_code == 400
    assert any("V must" in e for e in response.json()["detail"])


def test_invalid_horizon_rejected():
    client = _client()
    response = client.post("/api/whatif/project", json={"alpha": 0.25, "V": 200.0, "horizon_days": 0})
    assert response.status_code == 400
    assert any("horizon_days" in e for e in response.json()["detail"])


class _WhatIfScorerStub:
    def __init__(self):
        self.centroids = SOC_PROFILE_CENTROIDS
        self.actions = list(SCORER_ACTIONS)
        self.categories = list(SOC_CATEGORIES)


def test_whatif_ceiling_estimate_present(monkeypatch):
    monkeypatch.setattr(whatif_service, "get_profile_scorer", lambda: _WhatIfScorerStub())
    result = run_whatif(WhatIfScenario())
    assert result.ceiling_estimate is not None
    assert isinstance(result.ceiling_estimate, float)
