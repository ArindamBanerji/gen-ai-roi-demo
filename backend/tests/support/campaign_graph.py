"""Record production AGE operations; inspect persisted state independently."""
from __future__ import annotations

from typing import Any
import json
import asyncio

from ci_platform.graph.age_client import AGEClient


def pattern_history(graph: Any, rows: list[dict[str, Any]], action_index: int = 0) -> Any:
    """Add history through production decision writes and real evolution edges."""
    for row in rows:
        snapshot = row.get("factor_snapshot", json.dumps(
            [0.11, 0.22, 0.33, row.get("pattern_value", 0.4), 0.55, 0.66]))
        identifier = graph.decision(correct=True, action_index=action_index,
            verified_correct=True, decision_number=row["decision_num"], factor_snapshot=snapshot)
        literal = AGEClient.serialize_for_age(identifier)
        graph.query(f"MATCH (d:Decision {{decision_id: {literal}}}) "
                    f"CREATE (d)-[:TRIGGERED_EVOLUTION]->(e:EvolutionEvent {{id: {literal}}}) RETURN e")
    return CampaignGraphProbe(graph)


class CampaignGraphProbe:
    def __init__(self, graph: Any, alerts: Any = (), campaigns: Any = (),
                 edges: Any = (), fail_on: str | None = None,
                 suppress_member_create: bool = False) -> None:
        self.graph = graph
        self.client = graph.client
        self.queries: list[str] = []
        self.operations: list[tuple[Any, ...]] = []
        self.fail_on = fail_on
        self.suppress_member_create = suppress_member_create
        for identifier in set(alerts):
            graph.alert(alert_id=identifier)
        for identifier in set(campaigns) | {cid for _, cid in edges}:
            graph.node("Campaign", domain="soc", campaign_id=identifier)
        for alert_id, campaign_id in edges:
            graph.query(
                "MATCH (a:Alert {alert_id: " + AGEClient.serialize_for_age(alert_id)
                + "}), (c:Campaign {campaign_id: " + AGEClient.serialize_for_age(campaign_id)
                + "}) CREATE (a)-[:MEMBER_OF]->(c) RETURN c"
            )

    def _record(self, query: str) -> bool:
        self.queries.append(query)
        self.operations.append(("cypher", query))
        if self.fail_on and self.fail_on in query:
            raise RuntimeError("injected graph failure")
        # Deliberate missing acknowledgement fault; other operations reach AGE.
        return self.suppress_member_create and "CREATE (a0)-[:MEMBER_OF]->(c)" in query

    async def run_query(self, query: str, params: Any = None) -> Any:
        if self._record(query):
            return []
        return await self.client.run_query(query, params)

    async def run_transaction(self, operation: Any) -> Any:
        return await self.client.run_transaction(
            lambda transaction: operation(_TransactionRecorder(self, transaction))
        )

    def count_queries_containing(self, text: str) -> int:
        return sum(text in query for query in self.queries)

    @property
    def materialized_lookup_count(self) -> int:
        return self.count_queries_containing("RETURN c.campaign_id AS campaign_id")

    @property
    def campaign_rows(self) -> dict[str, Any]:
        return {row["c"]["campaign_id"]: row["c"] for row in
                self.graph.query("MATCH (c:Campaign) RETURN properties(c) AS c")}

    @property
    def campaigns(self) -> set[str]:
        return set(self.campaign_rows)

    @property
    def seeds(self) -> dict[str, Any]:
        return {row["s"]["seed_key"]: row["s"] for row in
                self.graph.query("MATCH (s:CampaignSeed) RETURN properties(s) AS s")}

    @property
    def edges(self) -> set[tuple[str, str]]:
        return {(row["a"], row["c"]) for row in self.graph.query(
            "MATCH (a:Alert)-[:MEMBER_OF]->(c:Campaign) RETURN a.alert_id AS a, c.campaign_id AS c")}

    @property
    def continues_edges(self) -> dict[tuple[str, str], Any]:
        return {(row["a"], row["b"]): row["r"] for row in self.graph.query(
            "MATCH (a:Campaign)-[r:CONTINUES]->(b:Campaign) "
            "RETURN a.campaign_id AS a, b.campaign_id AS b, properties(r) AS r")}

    def _count(self, pattern: str) -> int:
        return int(self.graph.query(f"MATCH {pattern} RETURN count(*) AS n")[0]["n"])

    @property
    def seed_create_count(self) -> int:
        return self._count("(:CampaignSeed)")

    @property
    def campaign_create_count(self) -> int:
        return self._count("(:Campaign)")

    @property
    def member_edge_create_count(self) -> int:
        return self._count("()-[:MEMBER_OF]->()")

    @property
    def continues_create_count(self) -> int:
        return self._count("()-[:CONTINUES]->()")

    def duplicate_continues_pair_count(self) -> int:
        return self.continues_create_count - len(self.continues_edges)


class _TransactionRecorder:
    def __init__(self, probe: CampaignGraphProbe, transaction: Any) -> None:
        self.probe = probe
        self.transaction = transaction

    def execute_sql(self, sql: str, parameters: Any = None) -> Any:
        self.probe.operations.append(("sql", sql, parameters))
        return self.transaction.execute_sql(sql, parameters)

    def run_cypher(self, query: str, parameters: Any = None) -> Any:
        if self.probe._record(query):
            return []
        return self.transaction.run_cypher(query, parameters)


class MaterializationObserver:
    """Control scheduling around real persistence; input events are supplied explicitly."""
    def __init__(self, events: Any, graph: CampaignGraphProbe) -> None:
        from app.domains.soc.campaigns import CampaignRepository
        self.events = list(events)
        self.graph = graph
        self.repository = CampaignRepository(graph)
        self.persist_calls = 0
        self.materialize_calls = 0
        self.materialize_started = asyncio.Event()
        self.release_materialize: asyncio.Event | None = None
        self.fail_materialize = False

    async def fetch_single_alert_event(self, alert_id: str, **kwargs: Any) -> Any:
        return next((event for event in self.events if event["alert_id"] == alert_id), None)

    async def fetch_recent_events(self, *args: Any, **kwargs: Any) -> Any:
        return list(self.events)

    async def persist_campaign_seed(self, event: Any, **kwargs: Any) -> Any:
        self.persist_calls += 1
        return await self.repository.persist_campaign_seed(event, **kwargs)

    async def materialize_seed_campaign(self, campaign: Any, **kwargs: Any) -> Any:
        self.materialize_calls += 1
        self.materialize_started.set()
        if self.release_materialize is not None:
            await self.release_materialize.wait()
        if self.fail_materialize:
            raise RuntimeError("injected background failure")
        return await self.repository.materialize_seed_campaign(campaign, **kwargs)

    @property
    def seeds(self) -> Any:
        return self.graph.seeds

    @property
    def edges(self) -> Any:
        return self.graph.edges

    def get_temporal_context(self, campaign_id: str) -> Any:
        return self.repository.get_temporal_context(campaign_id)
