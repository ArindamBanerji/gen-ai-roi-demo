import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.main import app
from app.routers import platform

client = TestClient(app)


def _reward_payload():
    response = client.get("/api/platform/rl-reward-demo")
    assert response.status_code == 200
    return response.json()


def _exploration_payload():
    response = client.get("/api/platform/rl-exploration-demo")
    assert response.status_code == 200
    return response.json()


def test_rl_reward_demo_endpoint_returns_200():
    payload = _reward_payload()

    assert "reward_breakdown" in payload
    assert "summary" in payload
    assert "note" in payload


def test_rl_exploration_demo_endpoint_returns_200():
    payload = _exploration_payload()

    assert "exploration_log" in payload
    assert "summary" in payload
    assert "note" in payload


def test_reward_breakdown_has_story_entries():
    breakdown = _reward_payload()["reward_breakdown"]

    assert len(breakdown) == 3
    assert [entry["severity"] for entry in breakdown] == [0.30, 0.92, 0.65]


def test_exploration_log_status_progression():
    exploration_log = _exploration_payload()["exploration_log"]

    assert len(exploration_log) == 3
    assert [entry["epoch"] for entry in exploration_log] == [1, 2, 3]
    assert [entry["status"] for entry in exploration_log] == ["active", "reduced", "paused"]


def test_reward_weight_is_proportional_for_correct_examples():
    correct_rows = {
        entry["severity"]: entry
        for entry in _reward_payload()["reward_breakdown"]
        if entry["outcome"] == "correct"
    }

    assert correct_rows[0.92]["reward_weight"] > correct_rows[0.30]["reward_weight"]
    assert correct_rows[0.30]["eta_applied"] == 0.019


def test_exploration_rate_pauses_below_margin_threshold():
    paused_rows = [
        entry
        for entry in _exploration_payload()["exploration_log"]
        if entry["conservation_margin"] < 0.03
    ]

    assert len(paused_rows) == 1
    assert paused_rows[0]["exploration_rate"] == 0.00
    assert paused_rows[0]["status"] == "paused"
    assert "AMBER" in paused_rows[0]["note"]


def test_rl_display_endpoints_are_platform_not_rl_namespace():
    assert client.get("/api/platform/rl-reward-demo").status_code == 200
    assert client.get("/api/platform/rl-exploration-demo").status_code == 200
    assert client.get("/api/rl/rl-reward-demo").status_code == 404
    assert client.get("/api/rl/rl-exploration-demo").status_code == 404


def test_missing_rl_fixtures_fail_open(monkeypatch, tmp_path):
    monkeypatch.setattr(platform, "_RL_REWARD_PATH", tmp_path / "missing_rl_reward_demo.json")
    monkeypatch.setattr(platform, "_RL_EXPLORATION_PATH", tmp_path / "missing_rl_exploration_demo.json")
    platform._reset_rl_reward_cache()
    platform._reset_rl_exploration_cache()

    try:
        reward_response = client.get("/api/platform/rl-reward-demo")
        exploration_response = client.get("/api/platform/rl-exploration-demo")
    finally:
        platform._reset_rl_reward_cache()
        platform._reset_rl_exploration_cache()

    assert reward_response.status_code == 200
    assert reward_response.json()["reward_breakdown"] == []
    assert reward_response.json()["summary"] == {}
    assert exploration_response.status_code == 200
    assert exploration_response.json()["exploration_log"] == []
    assert exploration_response.json()["summary"] == {}


def test_existing_platform_endpoints_unaffected():
    assert client.get("/api/platform/cross-signals").status_code == 200
    assert client.get("/api/platform/domain-applicability").status_code == 200
    assert client.get("/api/platform/warm-start-evidence").status_code == 200
    assert client.get("/api/platform/chain-credit-demo").status_code == 200
