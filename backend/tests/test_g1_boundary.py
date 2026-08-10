"""T-G1-SOC: production exploration must not override centroid scoring."""

import os
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    os.environ.pop("SAML_ENABLED", None)
    import app.auth.dependencies as dependencies

    dependencies._auth_config = None
    from app.main import app

    return TestClient(app, raise_server_exceptions=False)


def test_exploration_does_not_override_action() -> None:
    from app.domains.soc import config
    from pathlib import Path

    assert config.RL_EXPLORATION_ENABLED is False
    triage = Path(__file__).parents[1] / "app" / "routers" / "triage.py"
    source = triage.read_text(encoding="utf-8")
    assert "selected_action = _rl_explored_action_name" not in source


def test_exploration_flag_controls_override(monkeypatch) -> None:
    from app.domains.soc import config

    monkeypatch.setattr(config, "RL_EXPLORATION_ENABLED", False)
    assert config.RL_EXPLORATION_ENABLED is False

    # The proposal path remains in the route, but cannot override the action.
    from pathlib import Path

    triage = Path(__file__).parents[1] / "app" / "routers" / "triage.py"
    source = triage.read_text(encoding="utf-8")
    assert "gae_scoring_explore_proposed" in source
    assert "RL_EXPLORATION_ENABLED" in source
    assert "gae_scoring_explored" not in source


def test_no_gae_scoring_explored_in_prod(
    client, soc_triage_harness, monkeypatch
) -> None:
    from app.domains.soc import config

    assert config.RL_EXPLORATION_ENABLED is False
    monkeypatch.setattr(
        "app.routers.triage.narrator.generate_reasoning",
        AsyncMock(return_value="G1 test narrative"),
    )
    methods = []
    alert_ids = [
        "ALERT-7823",
        "ALERT-7820",
        "ALERT-7830",
        "ALERT-7835",
        "ALERT-7841",
        "ALERT-7845",
        "ALERT-7822",
        "ALERT-7819",
        "ALERT-7821",
        "ALERT-7824",
    ]
    for alert_id in alert_ids:
        soc_triage_harness.graph_client._alerts[alert_id] = {
            "alert_id": alert_id,
            "alert_type": "malware_execution",
            "security_context": {"alert_type": "malware_execution", "key_facts": []},
        }
        response = client.post(
            "/api/alert/analyze", json={"alert_id": alert_id}
        )
        if response.status_code == 200:
            methods.append(response.json().get("decision_method", ""))

    assert methods, "production scoring did not return any decisions"
    assert all("explored" not in method.lower() for method in methods)
