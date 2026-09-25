from __future__ import annotations

import asyncio
import pytest

from app.domains.soc.campaigns import (
    GET_CAMPAIGN_CONTEXT_FOR_DECISION_QUERY,
    get_campaign_context_for_decision,
)


def test_campaign_topology_query_contains_required_edges() -> None:
    assert "[:DECIDED_ON]" in GET_CAMPAIGN_CONTEXT_FOR_DECISION_QUERY
    assert "[:MEMBER_OF]" in GET_CAMPAIGN_CONTEXT_FOR_DECISION_QUERY
    assert "[:CONTINUES]" in GET_CAMPAIGN_CONTEXT_FOR_DECISION_QUERY


@pytest.mark.age
def test_campaign_shared_alerts_from_decision_context(age_graph) -> None:
    for index in (1, 2):
        age_graph.decision(decision_id=f"D-{index}")
        age_graph.alert(alert_id=f"A-{index}")
        age_graph.query(f"MATCH (d:Decision {{decision_id: 'D-{index}'}}), (a:Alert {{alert_id: 'A-{index}'}}) CREATE (d)-[:DECIDED_ON]->(a) RETURN d")
    for index in (0, 1):
        age_graph.node("Campaign", domain="soc", campaign_id=f"campaign-{index}")
    age_graph.query("MATCH (a:Alert), (c:Campaign {campaign_id: 'campaign-1'}) CREATE (a)-[:MEMBER_OF]->(c) RETURN a")
    age_graph.query("MATCH (a:Campaign {campaign_id: 'campaign-0'}), (b:Campaign {campaign_id: 'campaign-1'}) CREATE (a)-[:CONTINUES]->(b) RETURN a")
    def run_query(query, params=None):
        return asyncio.run(age_graph.client.run_query(query, params))

    context = get_campaign_context_for_decision(run_query, "D-1")

    assert context["campaign_id"] == "campaign-1"
    assert context["campaign_alerts"] == ["A-1", "A-2"]
    assert context["related_decisions"] == ["D-2"]
    assert context["previous_campaign_id"] == "campaign-0"


@pytest.mark.age
def test_campaign_traversal_returns_empty_context_for_missing_decision(age_graph) -> None:
    context = get_campaign_context_for_decision(lambda query, params=None: asyncio.run(age_graph.client.run_query(query, params)), "missing")

    assert context["decision_id"] == "missing"
    assert context["campaign_id"] is None
    assert context["campaign_alerts"] == []
    assert context["related_decisions"] == []
