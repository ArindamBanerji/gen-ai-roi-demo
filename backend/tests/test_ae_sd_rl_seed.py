import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.main import app
from app.routers import platform

client = TestClient(app)


def _warm_start_payload():
    response = client.get("/api/platform/warm-start-evidence")
    assert response.status_code == 200
    return response.json()


def _chain_credit_payload():
    response = client.get("/api/platform/chain-credit-demo")
    assert response.status_code == 200
    return response.json()


def test_warm_start_endpoint_returns_200():
    payload = _warm_start_payload()

    assert "evidence" in payload
    assert "total" in payload
    assert "note" in payload


def test_warm_start_has_one_transfer():
    payload = _warm_start_payload()
    item = payload["evidence"][0]

    assert payload["total"] == 1
    assert item["source_domain"] == "soc"
    assert item["target_domain"] == "s2p"
    assert item["source_rule"] == "RULE-CAMPAIGN-ESCALATE"
    assert item["target_rule"] == "RULE-S2P-EXCEPTION-CLUSTER"
    assert item["warm_start_prior"] == 0.757


def test_warm_start_lifecycle_complete():
    item = _warm_start_payload()["evidence"][0]
    lifecycle = item["lifecycle"]
    shadow_result = next(event for event in lifecycle if event["event_type"] == "shadow_result")

    assert len(lifecycle) == 4
    assert lifecycle[0]["event_type"] == "variant_created"
    assert lifecycle[-1]["event_type"] == "promotion_approved"
    assert shadow_result["metadata"]["win_rate"] == 0.72
    assert shadow_result["metadata"]["comparisons"] == 25
    assert shadow_result["metadata"]["wins"] == 18


def test_warm_start_impact_matches_story():
    impact = _warm_start_payload()["evidence"][0]["impact"]

    assert impact["invoices_caught"] == 3
    assert impact["largest_catch_usd"] == 45000
    assert impact["supplier"] == "Chen-Lin Manufacturing"


def test_chain_credit_endpoint_returns_200():
    payload = _chain_credit_payload()

    assert "chain_credits" in payload
    assert "summary" in payload
    assert "note" in payload


def test_chain_credit_attribution():
    credit = _chain_credit_payload()["chain_credits"][0]

    assert credit["source_decision"]["amount_usd"] == 42000
    assert credit["target_decision"]["amount_usd"] == 45000
    assert credit["attribution"]["gamma"] == 0.068
    assert credit["attribution"]["factor_overlap"] == 0.89


def test_chain_credit_analysts():
    credit = _chain_credit_payload()["chain_credits"][0]

    assert credit["source_decision"]["analyst"] == "priya_sharma"
    assert credit["target_decision"]["analyst"] == "system_auto"


def test_endpoints_not_under_s2p_preview():
    assert client.get("/api/platform/warm-start-evidence").status_code == 200
    assert client.get("/api/platform/chain-credit-demo").status_code == 200
    assert client.get("/api/s2p/preview/warm-start-evidence").status_code == 404
    assert client.get("/api/s2p/preview/chain-credit-demo").status_code == 404


def test_missing_fixtures_fail_open(monkeypatch, tmp_path):
    monkeypatch.setattr(platform, "_WARM_START_PATH", tmp_path / "missing_warm_start.json")
    monkeypatch.setattr(platform, "_CHAIN_CREDIT_PATH", tmp_path / "missing_chain_credit.json")
    platform._reset_warm_start_cache()
    platform._reset_chain_credit_cache()

    try:
        warm_response = client.get("/api/platform/warm-start-evidence")
        chain_response = client.get("/api/platform/chain-credit-demo")
    finally:
        platform._reset_warm_start_cache()
        platform._reset_chain_credit_cache()

    assert warm_response.status_code == 200
    assert warm_response.json()["evidence"] == []
    assert warm_response.json()["total"] == 0
    assert chain_response.status_code == 200
    assert chain_response.json()["chain_credits"] == []
    assert chain_response.json()["summary"] == {}


def test_existing_cross_signals_still_works():
    response = client.get("/api/platform/cross-signals")

    assert response.status_code == 200
    assert "signals" in response.json()
