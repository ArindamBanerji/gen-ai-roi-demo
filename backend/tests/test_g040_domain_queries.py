"""G040 catalogue rejection and live AGE same-identifier collision tests."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock

import pytest

from ci_platform.graph.age_graph_store import AGEGraphStore
from app.domains.soc.campaigns import (
    Campaign, CampaignRepository, TECHNIQUE_SEQUENCE_QUERY,
    GET_CAMPAIGNS_QUERY, GET_CAMPAIGN_DETAIL_QUERY, get_campaign_context_for_decision,
)
from app.services.graph_explorer import GraphExplorerService, PREBUILT_QUERIES


@pytest.mark.asyncio
@pytest.mark.parametrize("query", [
    "MATCH (n) RETURN n", "MATCH (d:Decision) WHERE d.domain='trading' RETURN d",
    PREBUILT_QUERIES["recent_decisions"]["cypher"] + " UNION MATCH (n) RETURN n",
    PREBUILT_QUERIES["recent_decisions"]["cypher"] + "; MATCH (n) RETURN n",
    PREBUILT_QUERIES["recent_decisions"]["cypher"].replace("'soc'", "'trading'"),
    "/* MATCH */ CALL db.labels()", "MATCH (n) SET n.domain='soc' RETURN n",
])
async def test_g040_explorer_rejects_arbitrary_cypher_before_io(query: str, monkeypatch: Any) -> None:
    monkeypatch.setenv("SOC_PROFILE", "production")
    client = AsyncMock()
    result = await GraphExplorerService.run_safe_query(query, client, domain="soc")
    assert "catalogue" in result["error"]
    client.run_query.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("domain", [None, "", "trading", "SOC", "soc OR true"])
async def test_g040_explorer_missing_or_foreign_domain_rejected(domain: Any) -> None:
    client = AsyncMock()
    result = await GraphExplorerService.run_safe_query(PREBUILT_QUERIES["recent_decisions"]["cypher"], client, domain=domain)
    assert "domain" in result["error"]
    client.run_query.assert_not_called()


@pytest.mark.asyncio
async def test_g040_catalogue_query_runs_and_preserves_graph_failure() -> None:
    client = AsyncMock()
    client.run_query.return_value = [{"id": "soc-only"}]
    query = PREBUILT_QUERIES["recent_decisions"]["cypher"]
    result = await GraphExplorerService.run_safe_query(query, client, domain="soc")
    assert result["rows"] == [{"id": "soc-only"}]
    client.run_query.assert_awaited_once_with(query)
    client.run_query.side_effect = RuntimeError("AGE unavailable")
    result = await GraphExplorerService.run_prebuilt_query("recent_decisions", client)
    assert result["error"] == "AGE unavailable" and "rows" not in result


def test_g040_campaign_same_id_and_foreign_intermediates(soc_stress_test_graph: Any) -> None:
    dsn, graph = soc_stress_test_graph
    store = AGEGraphStore(dsn, graph)
    try:
        store._run_query("""
        CREATE (foreign:Decision {decision_id: 'same', domain: 'trading'}),
               (foreign_alert:Alert {alert_id: 'same_alert', domain: 'trading'}),
               (foreign_campaign:Campaign {campaign_id: 'same_campaign', domain: 'trading'}),
               (own:Decision {decision_id: 'same', domain: 'soc'}),
               (a:Alert {alert_id: 'same_alert', domain: 'soc'}),
               (c:Campaign {campaign_id: 'same_campaign', domain: 'soc'}),
               (related:Decision {decision_id: 'soc_related', domain: 'soc'}),
               (ra:Alert {alert_id: 'soc_related_alert', domain: 'soc'}),
               (leak:Decision {decision_id: 'foreign_related_leak', domain: 'dataops'}),
               (wrong_bridge:Alert {alert_id: 'foreign_bridge_leak', domain: 'trading'}),
               (through_wrong:Decision {decision_id: 'foreign_bridge_decision_leak', domain: 'soc'}),
               (foreign)-[:DECIDED_ON]->(foreign_alert), (foreign_alert)-[:MEMBER_OF]->(foreign_campaign),
               (own)-[:DECIDED_ON]->(a), (a)-[:MEMBER_OF]->(c),
               (related)-[:DECIDED_ON]->(ra), (ra)-[:MEMBER_OF]->(c),
               (leak)-[:DECIDED_ON]->(ra), (through_wrong)-[:DECIDED_ON]->(wrong_bridge),
               (wrong_bridge)-[:MEMBER_OF]->(c), (c)-[:CONTINUES]->(foreign_campaign)
        """)
        context = get_campaign_context_for_decision(
            lambda query, params: store._run(store._client.run_query(query, params)), "same"
        )
        assert context["campaign_id"] == "same_campaign"
        assert context["related_decisions"] == ["soc_related"]
        assert sorted(context["campaign_alerts"]) == ["same_alert", "soc_related_alert"]
        assert context["next_campaign_id"] is None
    finally:
        store.close()


@pytest.mark.asyncio
async def test_g040_explorer_scopes_roots_neighbors_catalogue_and_counts(soc_stress_test_graph: Any) -> None:
    dsn, graph = soc_stress_test_graph
    store = AGEGraphStore(dsn, graph)
    client = store._client
    try:
        await client.run_query("""
        CREATE (s:User {id: 'same', name: 'SOC user', domain: 'soc'}),
               (t:User {id: 'same', name: 'Foreign user', domain: 'trading'}),
               (a:Asset {id: 'own_asset', name: 'Own asset', domain: 'soc'}),
               (x:Asset {id: 'foreign_asset', domain: 'dataops'}),
               (legacy:Asset {id: 'missing_domain'}),
               (sd:Decision {decision_id: 'same_decision', domain: 'soc'}),
               (td:Decision {decision_id: 'same_decision', domain: 'trading'}),
               (s)-[:RELATED]->(a), (s)-[:RELATED]->(x), (s)-[:RELATED]->(legacy),
               (t)-[:RELATED]->(a)
        """)
        neighbors = await GraphExplorerService.get_node_neighbors("same", client)
        assert [r["neighbor_id"] for r in neighbors["neighbors"]] == ["own_asset"]
        users = await GraphExplorerService.run_prebuilt_query("top_risk_users", client)
        assert [r["name"] for r in users["rows"]] == ["SOC user"]
        decisions = await GraphExplorerService.run_prebuilt_query("recent_decisions", client)
        assert decisions["count"] == 1
        top = await GraphExplorerService.get_top_nodes(client, node_type="User")
        assert [(r["id"], r["connections"]) for r in top] == [("same", 1)]
        summary = await GraphExplorerService.get_graph_summary(client)
        assert summary["total_nodes"] == 3
        assert summary["total_relationships"] == 1
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_g040_campaign_write_binds_every_member_in_batch(soc_stress_test_graph: Any) -> None:
    dsn, graph = soc_stress_test_graph
    store = AGEGraphStore(dsn, graph)
    client = store._client
    now = datetime.now(timezone.utc)
    campaign = Campaign(
        campaign_id="collision", first_seen=now, last_seen=now, alert_count=2,
        category_sequence=["risk"], shared_entities=[], technique_sequence=[],
        confidence=0.7, trigger_rule="shared_entity", severity="HIGH",
        member_decision_ids=[], member_alert_ids=["a1", "a2"],
        correlation_window_hours=24, nl_summary="Test-owned collision fixture",
    )
    try:
        await client.run_query("""
        CREATE (:Campaign {campaign_id: 'collision', domain: 'trading', alert_count: 99}),
               (:Alert {alert_id: 'a1', domain: 'soc'}),
               (:Alert {alert_id: 'a2', domain: 'soc'}),
               (:Alert {alert_id: 'a1', domain: 'trading'}),
               (:Alert {alert_id: 'a2', domain: 'trading'})
        """)
        repository = CampaignRepository(client)
        assert await repository.write_campaign(campaign)
        rows = await client.run_query("MATCH (a:Alert)-[:MEMBER_OF]->(c:Campaign) RETURN a.domain AS a_domain, c.domain AS c_domain, a.alert_id AS alert_id")
        assert sorted((r["a_domain"], r["c_domain"], r["alert_id"]) for r in rows) == [("soc", "soc", "a1"), ("soc", "soc", "a2")]
        foreign = await client.run_query("MATCH (c:Campaign) WHERE c.domain='trading' RETURN c.alert_count AS n")
        assert foreign == [{"n": 99}]
    finally:
        await client.close()


def test_g040_campaign_catalogue_scopes_foreign_chains(soc_stress_test_graph: Any) -> None:
    dsn, graph = soc_stress_test_graph
    store = AGEGraphStore(dsn, graph)
    try:
        store._run_query("""
        CREATE (s:Decision {decision_id: 'start', domain: 'soc', alert_id: 'a1', timestamp_epoch: 10}),
               (t:Decision {decision_id: 'own_target', domain: 'soc', alert_id: 'a2', timestamp_epoch: 20}),
               (x:Decision {decision_id: 'foreign', domain: 'trading', alert_id: 'a3', timestamp_epoch: 15}),
               (leak:Decision {decision_id: 'via_foreign', domain: 'soc', alert_id: 'a4', timestamp_epoch: 30}),
               (a:Alert {alert_id: 'a1', domain: 'soc'}),
               (c:Campaign {campaign_id: 'own', domain: 'soc'}),
               (:Campaign {campaign_id: 'foreign', domain: 'trading'}),
               (s)-[:TRIGGERED_EVOLUTION]->(t), (s)-[:TRIGGERED_EVOLUTION]->(x),
               (x)-[:TRIGGERED_EVOLUTION]->(leak), (s)-[:DECIDED_ON]->(a), (a)-[:MEMBER_OF]->(c)
        """)
        chains = store._run(store._client.run_query(TECHNIQUE_SEQUENCE_QUERY, {"window_start": 0, "limit": 10}))
        assert [r["decision_ids"] for r in chains] == [["start", "own_target"]]
        campaigns = store._run(store._client.run_query(GET_CAMPAIGNS_QUERY, {"limit": 10}))
        assert [r["campaign_id"] for r in campaigns] == ["own"]
        detail = store._run(store._client.run_query(GET_CAMPAIGN_DETAIL_QUERY, {"campaign_id": "own"}))
        assert detail[0]["member_decision_ids"] == ["start"]
    finally:
        store.close()
