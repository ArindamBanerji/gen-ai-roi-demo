"""SOC authority state and vetoes use the same real graph."""
from copilot_sdk.graph import InMemoryGraphStore
from app.services.authority_ladder import AuthorityManager, GraphPromotionStore


def test_authority_reopen_reads_graph_stage_history() -> None:
    graph = InMemoryGraphStore()
    first = AuthorityManager(store=GraphPromotionStore(graph))
    first.advance("phishing", {"conservation_state": "GREEN"})
    second = AuthorityManager(store=GraphPromotionStore(graph))
    assert second.get_authority("phishing") == "assisted"
    assert second.get_record("phishing").stage_history == first.get_record("phishing").stage_history


def test_veto_audit_is_persisted_in_graph_and_visible_to_another_manager() -> None:
    graph = InMemoryGraphStore()
    first = AuthorityManager(store=GraphPromotionStore(graph))
    result = first.evaluate("phishing", "escalate", "RED")
    rows = AuthorityManager(store=GraphPromotionStore(graph)).list_veto_audit("phishing")
    assert len(rows) == 1
    assert rows[0]["audit_id"] == result.audit_id
    assert rows[0]["reason"] == "conservation_red"
    assert graph.get_promotion("soc", f"veto:{result.audit_id}")["veto_audit"] == rows[0]


def test_unrelated_graph_state_is_not_a_promotion_record() -> None:
    graph = InMemoryGraphStore()
    graph.save_promotion("soc", "unrelated", {"snapshot": {}})
    manager = AuthorityManager(store=GraphPromotionStore(graph))
    assert len(manager.get_all()) == 6
