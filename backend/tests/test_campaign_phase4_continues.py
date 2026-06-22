"""
tests/test_campaign_phase4_continues.py -- Phase 4 temporal CONTINUES edges.

Phase 4 adds advisory temporal context only. It must not affect scorer/tensor
behavior, create BELONGS_TO, or add hot-path campaign chain reads.
"""

import asyncio
import os
import re
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.domains.soc.campaigns import (  # noqa: E402
    CampaignAsyncState,
    CampaignCorrelationEngine,
    CampaignMatcher,
    CampaignRepository,
    campaign_advisory_lock_key,
    campaign_seed_candidate,
    make_campaign_identity_key,
)


DEFAULT_CONFIG = {
    "correlation_window_hours": 24,
    "temporal_window_minutes": 60,
    "min_alerts_for_campaign": 2,
    "max_campaign_age_days": 30,
}


def run(coro):
    return asyncio.run(coro)


def _event(
    alert_id,
    *,
    user_id="user-1",
    category="credential_access",
    days=0,
    minutes=0,
):
    return {
        "alert_id": alert_id,
        "category": category,
        "source_entity_id": None,
        "user_id": user_id,
        "asset_id": None,
        "source_location": None,
        "technique_id": None,
        "ts": datetime(2026, 3, 25, 10, 0) + timedelta(days=days, minutes=minutes),
        "severity": "MEDIUM",
        "decision_id": f"decision-{alert_id}",
    }


def _campaign(prefix, *, user_id="user-1", category="credential_access", days=0):
    events = [
        _event(f"{prefix}-1", user_id=user_id, category=category, days=days, minutes=0),
        _event(f"{prefix}-2", user_id=user_id, category=category, days=days, minutes=1),
    ]
    return CampaignCorrelationEngine(DEFAULT_CONFIG).correlate(events)[0]


def _with_rule(campaign, rule_type):
    campaign.trigger_rule = rule_type
    campaign.rule_type = rule_type
    campaign.campaign_id = make_campaign_identity_key(
        rule_type,
        campaign.derived_entity_key,
        campaign.category,
        campaign.time_bucket,
    )
    return campaign


class Phase4Transaction:
    def __init__(self, graph):
        self.graph = graph

    def execute_sql(self, sql, params=None):
        self.graph.operations.append(("sql", sql, params))

    def run_cypher(self, query):
        return self.graph._run_query_sync(query)


class Phase4Graph:
    def __init__(self, alerts=None):
        self.alerts = set(alerts or [])
        self.campaigns = {}
        self.member_edges = set()
        self.continues_edges = {}
        self.operations = []
        self.queries = []
        self.continues_create_count = 0
        self.continues_create_attempts = []

    async def run_transaction(self, operation):
        return operation(Phase4Transaction(self))

    async def run_query(self, query, params=None):
        return self._run_query_sync(query)

    def _run_query_sync(self, query):
        self.queries.append(query)
        self.operations.append(("cypher", query))

        if "MATCH (older:Campaign)" in query and "RETURN older.campaign_id AS campaign_id" in query:
            return self._older_campaign_rows(query)

        if "-[:CONTINUES]->" in query and "RETURN older.campaign_id AS campaign_id" in query:
            older_id = self._node_campaign_id(query, "older")
            newer_id = self._node_campaign_id(query, "newer")
            return [{"campaign_id": older_id}] if (older_id, newer_id) in self.continues_edges else []

        if "CREATE (older)-[:CONTINUES" in query:
            older_id = self._node_campaign_id(query, "older")
            newer_id = self._node_campaign_id(query, "newer")
            pair = (older_id, newer_id)
            self.continues_create_attempts.append(pair)
            if pair not in self.continues_edges:
                self.continues_create_count += 1
                self.continues_edges[pair] = {
                    "created_at_epoch": int(self._prop(query, "created_at_epoch") or 0),
                    "gap_buckets": int(self._prop(query, "gap_buckets") or 0),
                    "rule_type": self._prop(query, "rule_type"),
                }
            return []

        if "MATCH (c:Campaign" in query and "RETURN c" in query:
            campaign_id = self._campaign_id(query)
            return [{"c": self.campaigns[campaign_id]}] if campaign_id in self.campaigns else []

        if "CREATE (c:Campaign" in query:
            campaign_id = self._campaign_id(query)
            self.campaigns[campaign_id] = self._campaign_props(query, campaign_id)
            return []

        if "SET c.first_seen" in query:
            campaign_id = self._campaign_id(query)
            self.campaigns.setdefault(campaign_id, {"campaign_id": campaign_id})
            self.campaigns[campaign_id].update(self._campaign_props(query, campaign_id))
            return []

        if "-[:MEMBER_OF]->" in query and "RETURN a.alert_id AS alert_id" in query:
            campaign_id = self._campaign_id(query)
            requested = set(self._predicate_alert_ids(query))
            return [
                {"alert_id": alert_id}
                for alert_id, cid in sorted(self.member_edges)
                if cid == campaign_id and alert_id in requested
            ]

        if "MATCH (a:Alert)" in query and "RETURN a.alert_id AS alert_id" in query:
            requested = set(self._predicate_alert_ids(query))
            return [{"alert_id": alert_id} for alert_id in sorted(requested & self.alerts)]

        if "CREATE (a" in query and "[:MEMBER_OF]->(c)" in query:
            campaign_id = self._campaign_id(query)
            for alert_id in self._create_alert_ids(query):
                if alert_id in self.alerts and campaign_id in self.campaigns:
                    self.member_edges.add((alert_id, campaign_id))
            return [{"created_count": len(self._create_alert_ids(query))}]

        if "SET s.status = 'promoted'" in query:
            return []

        return []

    def _older_campaign_rows(self, query):
        entity = self._where_prop(query, "older.derived_entity_key")
        category = self._where_prop(query, "older.category")
        bucket = int(self._where_prop(query, "older.time_bucket"))
        rows = []
        for props in self.campaigns.values():
            if (
                props.get("derived_entity_key") == entity
                and props.get("category") == category
                and int(props.get("time_bucket")) == bucket
            ):
                rows.append(
                    {
                        "campaign_id": props["campaign_id"],
                        "time_bucket": props.get("time_bucket"),
                        "rule_type": props.get("rule_type"),
                        "trigger_rule": props.get("trigger_rule"),
                        "alert_count": props.get("alert_count"),
                    }
                )
        return rows

    @staticmethod
    def _campaign_id(query):
        match = re.search(r"campaign_id: '([^']+)'", query)
        return match.group(1) if match else None

    @staticmethod
    def _node_campaign_id(query, alias):
        match = re.search(rf"{alias}:Campaign \{{campaign_id: '([^']+)'\}}", query)
        return match.group(1) if match else None

    @staticmethod
    def _prop(query, name):
        match = re.search(
            rf"{name}: '([^']*)'|{name} = '([^']*)'|{name}: ([0-9]+)|{name} = ([0-9]+)",
            query,
        )
        if not match:
            return None
        return next(group for group in match.groups() if group is not None)

    @staticmethod
    def _where_prop(query, name):
        match = re.search(rf"{re.escape(name)} = '([^']*)'|{re.escape(name)} = ([0-9]+)", query)
        if not match:
            return None
        return next(group for group in match.groups() if group is not None)

    @staticmethod
    def _predicate_alert_ids(query):
        return re.findall(r"a\.alert_id = '([^']+)'", query)

    @staticmethod
    def _create_alert_ids(query):
        return re.findall(r"MATCH \(a\d+:Alert \{alert_id: '([^']+)'\}\)", query)

    def _campaign_props(self, query, campaign_id):
        return {
            "campaign_id": campaign_id,
            "derived_entity_key": self._prop(query, "derived_entity_key"),
            "category": self._prop(query, "category"),
            "rule_type": self._prop(query, "rule_type"),
            "trigger_rule": self._prop(query, "trigger_rule"),
            "time_bucket": int(self._prop(query, "time_bucket") or 0),
            "alert_count": int(self._prop(query, "alert_count") or 0),
        }

    def duplicate_continues_pair_count(self):
        seen = set()
        duplicates = 0
        for pair in self.continues_create_attempts:
            if pair in seen:
                duplicates += 1
            seen.add(pair)
        return duplicates


def _write(repo, campaign):
    assert run(repo.write_campaign(campaign)) is True


def test_adjacent_same_identity_creates_one_continues_older_to_newer():
    older = _campaign("old", days=0)
    newer = _campaign("new", days=1)
    graph = Phase4Graph(alerts=older.member_alert_ids + newer.member_alert_ids)
    repo = CampaignRepository(graph)

    _write(repo, older)
    _write(repo, newer)

    assert graph.continues_edges.keys() == {(older.campaign_id, newer.campaign_id)}
    assert graph.continues_create_count == 1


def test_duplicate_write_does_not_duplicate_continues():
    older = _campaign("old", days=0)
    newer = _campaign("new", days=1)
    graph = Phase4Graph(alerts=older.member_alert_ids + newer.member_alert_ids)
    repo = CampaignRepository(graph)

    _write(repo, older)
    _write(repo, newer)
    _write(repo, newer)

    assert graph.continues_edges.keys() == {(older.campaign_id, newer.campaign_id)}
    assert graph.continues_create_count == 1
    assert graph.duplicate_continues_pair_count() == 0


def test_different_derived_entity_key_does_not_link():
    older = _campaign("old", user_id="user-1", days=0)
    newer = _campaign("new", user_id="user-2", days=1)
    graph = Phase4Graph(alerts=older.member_alert_ids + newer.member_alert_ids)
    repo = CampaignRepository(graph)

    _write(repo, older)
    _write(repo, newer)

    assert graph.continues_edges == {}


def test_different_category_does_not_link():
    older = _campaign("old", category="credential_access", days=0)
    newer = _campaign("new", category="lateral_movement", days=1)
    graph = Phase4Graph(alerts=older.member_alert_ids + newer.member_alert_ids)
    repo = CampaignRepository(graph)

    _write(repo, older)
    _write(repo, newer)

    assert graph.continues_edges == {}


def test_different_effective_rule_type_does_not_link():
    older = _campaign("old", days=0)
    newer = _with_rule(_campaign("new", days=1), "temporal")
    graph = Phase4Graph(alerts=older.member_alert_ids + newer.member_alert_ids)
    repo = CampaignRepository(graph)

    _write(repo, older)
    _write(repo, newer)

    assert graph.continues_edges == {}


def test_conflicting_legacy_rule_fields_use_rule_type_as_effective_rule():
    older = _campaign("old", days=0)
    newer = _with_rule(_campaign("new", days=1), "temporal")
    graph = Phase4Graph(alerts=older.member_alert_ids + newer.member_alert_ids)
    repo = CampaignRepository(graph)

    _write(repo, older)
    graph.campaigns[older.campaign_id]["trigger_rule"] = "temporal"
    assert graph.campaigns[older.campaign_id]["rule_type"] == "shared_entity"
    _write(repo, newer)

    assert graph.continues_edges == {}


def test_missing_older_rule_type_falls_back_to_trigger_rule():
    older = _with_rule(_campaign("old", days=0), "temporal")
    newer = _with_rule(_campaign("new", days=1), "temporal")
    graph = Phase4Graph(alerts=older.member_alert_ids + newer.member_alert_ids)
    repo = CampaignRepository(graph)

    _write(repo, older)
    graph.campaigns[older.campaign_id]["rule_type"] = ""
    _write(repo, newer)

    assert graph.continues_edges.keys() == {(older.campaign_id, newer.campaign_id)}


def test_non_adjacent_bucket_does_not_link_in_v1():
    older = _campaign("old", days=0)
    newer = _campaign("new", days=2)
    graph = Phase4Graph(alerts=older.member_alert_ids + newer.member_alert_ids)
    repo = CampaignRepository(graph)

    _write(repo, older)
    _write(repo, newer)

    assert graph.continues_edges == {}


def test_missing_identity_fields_skip_safely():
    older = _campaign("old", days=0)
    newer = _campaign("new", days=1)
    newer.derived_entity_key = ""
    graph = Phase4Graph(alerts=older.member_alert_ids + newer.member_alert_ids)
    repo = CampaignRepository(graph)

    _write(repo, older)
    _write(repo, newer)

    assert graph.continues_edges == {}


def test_continues_edge_properties_are_written():
    older = _campaign("old", days=0)
    newer = _campaign("new", days=1)
    graph = Phase4Graph(alerts=older.member_alert_ids + newer.member_alert_ids)
    repo = CampaignRepository(graph)

    _write(repo, older)
    _write(repo, newer)

    props = graph.continues_edges[(older.campaign_id, newer.campaign_id)]
    assert props["created_at_epoch"] > 0
    assert props["gap_buckets"] == 1
    assert props["rule_type"] == "shared_entity"


def test_materialize_seed_campaign_uses_same_locked_continues_path():
    older = _campaign("old", days=0)
    newer = _campaign("new", days=1)
    graph = Phase4Graph(alerts=older.member_alert_ids + newer.member_alert_ids)
    repo = CampaignRepository(graph)

    assert run(repo.materialize_seed_campaign(older)) is True
    assert run(repo.materialize_seed_campaign(newer)) is True

    assert graph.operations[0] == (
        "sql",
        "SELECT pg_advisory_xact_lock(%s)",
        (campaign_advisory_lock_key(older.campaign_id),),
    )
    assert (older.campaign_id, newer.campaign_id) in graph.continues_edges


def test_no_belongs_to_or_campaign_seed_writes_from_phase4_direct_path():
    older = _campaign("old", days=0)
    newer = _campaign("new", days=1)
    graph = Phase4Graph(alerts=older.member_alert_ids + newer.member_alert_ids)
    repo = CampaignRepository(graph)

    _write(repo, older)
    _write(repo, newer)

    all_text = "\n".join(graph.queries)
    assert "BELONGS_TO" not in all_text
    assert "CREATE (s:CampaignSeed" not in all_text


def test_temporal_context_cache_updates_after_success():
    older = _campaign("old", days=0)
    newer = _campaign("new", days=1)
    graph = Phase4Graph(alerts=older.member_alert_ids + newer.member_alert_ids)
    repo = CampaignRepository(graph)
    state = CampaignAsyncState()

    _write(repo, older)
    _write(repo, newer)
    state.mark_temporal_context(repo.get_temporal_context(newer.campaign_id))

    context = state.get_temporal_context(newer.campaign_id)
    assert context is not None
    assert context.previous_campaign_id == older.campaign_id
    assert context.chain_length_buckets == 2
    assert context.total_alert_count == older.alert_count + newer.alert_count
    state.reset_for_tests()
    assert state.get_temporal_context(newer.campaign_id) is None


class HotPathRepo:
    def __init__(self, event):
        self.event = event
        self.materialize_calls = 0

    async def fetch_single_alert_event(self, alert_id, **_kwargs):
        return self.event if self.event["alert_id"] == alert_id else None

    async def fetch_recent_events(self, *_args, **_kwargs):
        return [self.event]

    async def persist_campaign_seed(self, *_args, **_kwargs):
        raise AssertionError("cache-hit path must not persist seeds")

    async def materialize_seed_campaign(self, *_args, **_kwargs):
        self.materialize_calls += 1
        raise AssertionError("cache-hit path must not materialize")


def test_check_alert_cache_hit_has_no_continues_or_chain_lookup():
    event = _event("hot-1")
    seed_campaign = campaign_seed_candidate(
        event,
        CampaignCorrelationEngine(DEFAULT_CONFIG).window_seconds,
    )["campaign_id"]
    state = CampaignAsyncState()
    state.mark_materialized(seed_campaign)
    graph = Phase4Graph(alerts=["hot-1"])
    matcher = CampaignMatcher(
        graph,
        DEFAULT_CONFIG,
        CampaignCorrelationEngine(DEFAULT_CONFIG),
        HotPathRepo(event),
        background=True,
        async_state=state,
    )

    result = run(matcher.check_alert("hot-1"))

    assert result == seed_campaign
    assert all("CONTINUES" not in query for query in graph.queries)
    assert all("older:Campaign" not in query for query in graph.queries)


def test_m8_style_unit_cache_hit_remains_fast():
    event = _event("hot-1")
    seed_campaign = campaign_seed_candidate(
        event,
        CampaignCorrelationEngine(DEFAULT_CONFIG).window_seconds,
    )["campaign_id"]
    state = CampaignAsyncState()
    state.mark_materialized(seed_campaign)
    matcher = CampaignMatcher(
        Phase4Graph(alerts=["hot-1"]),
        DEFAULT_CONFIG,
        CampaignCorrelationEngine(DEFAULT_CONFIG),
        HotPathRepo(event),
        background=True,
        async_state=state,
    )

    timed = run(matcher.check_alert_timed("hot-1"))

    assert timed["campaign_id"] == seed_campaign
    assert timed["measurement_mode"] == "mock/unit"
    assert timed["elapsed_ms"] < 5.0
