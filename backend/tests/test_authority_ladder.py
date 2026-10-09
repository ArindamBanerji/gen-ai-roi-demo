"""SOC-02 authority ladder and decision-path veto tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
import pytest
from copilot_sdk.graph import InMemoryGraphStore
from app.services.authority_ladder import (AuthorityManager, SOC_ALERT_CATEGORIES, GraphPromotionStore, configure_authority_graph_store)


@pytest.fixture(autouse=True)
def graph_authority() -> None:
    configure_authority_graph_store(InMemoryGraphStore())


class ConservationSource:
    def __init__(self, status: str) -> None:
        self.status = status

    def get_state(self) -> dict[str, str]:
        return {"status": self.status}


def manager(tmp_path) -> AuthorityManager:
    return AuthorityManager(ConservationSource("GREEN"), store=GraphPromotionStore(InMemoryGraphStore()))


def test_authority_starts_at_discovered(tmp_path):
    instance = manager(tmp_path)
    assert instance.get_authority("phishing") == "observed"
    assert len(instance.get_all()) == 6
    assert {item["decision_class"] for item in instance.get_all()} == set(SOC_ALERT_CATEGORIES)


def test_triage_veto_observed_forces_referral(tmp_path):
    decision = manager(tmp_path).evaluate("phishing", "escalate", "GREEN", "decision-1")
    assert decision.allowed is False
    assert decision.reason == "authority_not_auto_approved"
    assert decision.would_have_action == "escalate"


def test_triage_veto_red_forces_referral(tmp_path):
    instance = manager(tmp_path)
    decision = instance.evaluate("phishing", "escalate", "RED", "decision-2")
    assert decision.allowed is False
    assert decision.reason == "conservation_red"
    assert instance.list_veto_audit("phishing")


def test_unknown_category_defaults_to_observed_referral(tmp_path):
    decision = manager(tmp_path).evaluate("malware_execution", "escalate", "GREEN")
    assert decision.authority == "observed"
    assert decision.allowed is False
    assert decision.reason == "unknown_category"
    assert decision.would_have_action == "escalate"


def test_auto_approve_allowed_only_at_kept(tmp_path):
    instance = manager(tmp_path)
    assert instance.advance("phishing", {"conservation_state": "GREEN"})["authority"] == "assisted"
    assert instance.advance("phishing", {"conservation_state": "GREEN", "shadow_decisions": 10})["authority"] == "shadow-qualified"
    assert instance.advance("phishing", {"conservation_state": "GREEN", "measurement_decisions": 10, "improvement": 0.1})["authority"] == "auto-approved"
    decision = instance.evaluate("phishing", "escalate", "GREEN")
    assert decision.allowed is True


def test_circuit_break_forces_referral_and_isolated(tmp_path):
    instance = manager(tmp_path)
    instance.circuit_break("phishing")
    assert instance.get_authority("phishing") == "circuit-broken"
    assert instance.get_authority("malware_delivery") == "observed"
    decision = instance.evaluate("phishing", "escalate", "GREEN")
    assert decision.reason == "circuit_broken"


def test_authority_persists_across_restart(tmp_path):
    graph = InMemoryGraphStore()
    first = AuthorityManager(ConservationSource("GREEN"), store=GraphPromotionStore(graph))
    first.advance("phishing", {"conservation_state": "GREEN"})
    second = AuthorityManager(ConservationSource("GREEN"), store=GraphPromotionStore(graph))
    assert second.get_authority("phishing") == "assisted"


def test_red_blocks_advancement():
    instance = AuthorityManager(ConservationSource("RED"), store=GraphPromotionStore(InMemoryGraphStore()))
    result = instance.advance("phishing", {"shadow_decisions": 10})
    assert result["advanced"] is False
    assert result["reason"] == "conservation_red"


def test_veto_audit_contains_would_have_action(tmp_path):
    instance = manager(tmp_path)
    decision = instance.evaluate("phishing", "investigate", "RED", "decision-3")
    rows = instance.list_veto_audit("phishing")
    assert rows and rows[0]["audit_id"] == decision.audit_id
    assert rows[0]["would_have_action"] == "investigate"
    assert rows[0]["conservation"] == "RED"


def test_authority_router_lists_all_categories():
    response = TestClient(app).get("/api/soc/authority")
    assert response.status_code == 200
    payload = response.json()
    assert {item["decision_class"] for item in payload["categories"]} == set(SOC_ALERT_CATEGORIES)


def test_authority_router_detail_and_invalid_category():
    client = TestClient(app)
    assert client.get("/api/soc/authority/phishing").status_code == 200
    assert client.get("/api/soc/authority/not-a-category").status_code == 404


def test_authority_router_circuit_break():
    category = "insider_threat"
    response = TestClient(app).post(f"/api/soc/authority/{category}/circuit-break")
    assert response.status_code == 200
    assert response.json()["authority"] == "circuit-broken"


def test_learning_is_independent_of_authority_gate(tmp_path):
    instance = manager(tmp_path)
    # The ladder only evaluates dispatch authority; it does not expose or mutate
    # scorer state, so the same category can continue to collect evidence.
    assert instance.get_authority("credential_access") == "observed"
    assert instance.evaluate("credential_access", "refer_to_analyst", "GREEN").allowed is True


def test_promotion_and_authority_are_separate_records(tmp_path):
    instance = manager(tmp_path)
    before = instance.get_record("lateral_movement").record_id
    instance.advance("lateral_movement", {"conservation_state": "GREEN"})
    assert instance.get_record("lateral_movement").record_id == before
    assert instance.get_authority("lateral_movement") == "assisted"
