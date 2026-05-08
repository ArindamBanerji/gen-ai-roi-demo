from fastapi.testclient import TestClient

from app.domains.soc import config as soc_config
from app.domains.soc.config import SCORER_ACTIONS, SOC_CATEGORIES
from app.main import app
from app.services import rl_engine


client = TestClient(app, raise_server_exceptions=False)


def setup_function():
    rl_engine.reset_rl_state()


def teardown_function():
    rl_engine.reset_rl_state()


def _seed_reward_entry():
    result = rl_engine.RewardComputer(
        "soc",
        {"credential_access": {"base": 0.70}},
    ).compute("escalate", "correct", "credential_access", {})
    return rl_engine.get_reward_ledger().append(
        "DECISION-001",
        result,
        "credential_access",
        "escalate",
        alert_id="ALERT-001",
    )


def test_reward_ledger_summary_endpoint_200():
    response = client.get("/api/rl/reward-ledger/summary")

    assert response.status_code == 200
    assert "total" in response.json()


def test_reward_ledger_entries_endpoint_200():
    response = client.get("/api/rl/reward-ledger/entries?limit=5")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["entries"], list)
    assert body["limit"] == 5


def test_reward_ledger_entries_limit_capped():
    high = client.get("/api/rl/reward-ledger/entries?limit=999")
    low = client.get("/api/rl/reward-ledger/entries?limit=0")

    assert high.status_code == 200
    assert high.json()["limit"] == 100
    assert low.status_code == 200
    assert low.json()["limit"] == 1


def test_posterior_summary_endpoint_200():
    response = client.get("/api/rl/posteriors/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["n_categories"] == len(SOC_CATEGORIES)
    assert body["n_actions"] == len(SCORER_ACTIONS)
    assert len(body["cells"]) == len(SOC_CATEGORIES) * len(SCORER_ACTIONS)
    for cell in body["cells"]:
        assert {"category", "action", "alpha", "beta", "mean"} <= set(cell)


def test_chain_credit_endpoint_200():
    response = client.get("/api/rl/chain-credit/DECISION-001")

    assert response.status_code == 200
    body = response.json()
    assert body["decision_id"] == "DECISION-001"
    assert isinstance(body["credits_received"], list)
    assert isinstance(body["credits_given"], list)


def test_rl_status_endpoint_200():
    response = client.get("/api/rl/status")

    assert response.status_code == 200
    body = response.json()
    assert all(isinstance(value, bool) for value in body["flags"].values())
    assert {"reward_computer", "exploration_policy", "credit_assigner", "posterior_store"} <= set(
        body["components"]
    )


def test_rl_status_reads_feature_flags_per_request(monkeypatch):
    monkeypatch.setattr(soc_config, "RL_REWARD_LEDGER_ENABLED", True)
    monkeypatch.setattr(soc_config, "RL_EXPLORATION_ENABLED", True)
    monkeypatch.setattr(soc_config, "RL_ETA_MODULATION_ENABLED", True)
    monkeypatch.setattr(soc_config, "RL_CHAIN_CREDIT_ENABLED", True)

    response = client.get("/api/rl/status")

    assert response.status_code == 200
    assert response.json()["flags"] == {
        "reward_ledger": True,
        "exploration": True,
        "eta_modulation": True,
        "chain_credit": True,
    }


def test_all_endpoints_are_non_mutating():
    _seed_reward_entry()
    policy = rl_engine.ExplorationPolicy(
        n_categories=len(SOC_CATEGORIES),
        n_actions=len(SCORER_ACTIONS),
    )
    policy.update_posterior(0, 0, correct=True)
    rl_engine._exploration_policy = policy
    ledger = rl_engine.get_reward_ledger()
    ledger.add_chain_credit(rl_engine.ChainCredit("DECISION-001", "DECISION-002", 0.5, 1.0, 1))

    before_entries = ledger.get_entries(limit=100)
    before_alpha = policy.alphas[0][0]
    before_beta = policy.betas[0][0]
    before_credits = ledger.get_chain_credits()

    endpoints = [
        "/api/rl/reward-ledger/summary",
        "/api/rl/reward-ledger/entries?limit=10",
        "/api/rl/posteriors/summary",
        "/api/rl/chain-credit/DECISION-001",
        "/api/rl/status",
    ]
    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code == 200

    assert ledger.get_entries(limit=100) == before_entries
    assert policy.alphas[0][0] == before_alpha
    assert policy.betas[0][0] == before_beta
    assert ledger.get_chain_credits() == before_credits


def test_endpoints_work_with_empty_state():
    rl_engine.reset_rl_state()

    endpoints = [
        "/api/rl/reward-ledger/summary",
        "/api/rl/reward-ledger/entries",
        "/api/rl/posteriors/summary",
        "/api/rl/chain-credit/DECISION-001",
        "/api/rl/status",
    ]
    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code == 200


def test_existing_reward_summary_endpoint_not_shadowed():
    response = client.get("/api/rl/reward-summary")

    assert response.status_code == 200


def test_no_sensitive_data_exposed():
    posterior = client.get("/api/rl/posteriors/summary")
    status = client.get("/api/rl/status")

    assert posterior.status_code == 200
    assert status.status_code == 200
    text = posterior.text + status.text
    assert "postgresql://" not in text
    assert "5433" not in text
    assert "POSTERIOR_DSN" not in text
    assert "\\Users\\" not in text
    assert "/mnt/" not in text


def test_main_router_mount_exposes_rl_observability_routes():
    paths = {route.path for route in app.router.routes}

    assert "/api/rl/status" in paths
    assert "/api/rl/reward-ledger/summary" in paths
    assert "/api/rl/reward-ledger/entries" in paths
    assert "/api/rl/posteriors/summary" in paths
    assert "/api/rl/chain-credit/{decision_id}" in paths
