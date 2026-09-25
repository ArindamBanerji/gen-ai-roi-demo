"""
tests/test_campaign_seed_materialization.py -- true Campaign Phase 2 tests.

Phase 2 scope is seed materialization / AGE safety / race safety only.
It must not introduce CONTINUES, BELONGS_TO, async enrichment, or scorer input.
"""

import pytest
from support.campaign_graph import CampaignGraphProbe

import asyncio
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.domains.soc.campaigns import (
    CampaignCorrelationEngine,
    CampaignMatcher,
    CampaignRepository,
    campaign_advisory_lock_key,
    campaign_seed_candidate,
    make_campaign_identity_key,
    make_campaign_seed_key,
)


DEFAULT_CONFIG = {
    "correlation_window_hours": 24,
    "temporal_window_minutes": 60,
    "min_alerts_for_campaign": 2,
    "max_campaign_age_days": 30,
}


def run(coro):
    return asyncio.run(coro)


def _event(alert_id, *, user_id="user-1", category="credential_access", minutes=0):
    return {
        "alert_id": alert_id,
        "category": category,
        "source_entity_id": None,
        "user_id": user_id,
        "asset_id": None,
        "source_location": None,
        "technique_id": None,
        "ts": datetime(2026, 3, 25, 10, 0) + timedelta(minutes=minutes),
        "severity": "MEDIUM",
        "decision_id": f"decision-{alert_id}",
    }


def _campaign(events):
    return CampaignCorrelationEngine(DEFAULT_CONFIG).correlate(events)[0]






def test_campaign_seed_key_deterministic():
    key1 = make_campaign_seed_key("shared_entity", "user:U1", "credential_access", 493112)
    key2 = make_campaign_seed_key("shared_entity", "user:U1", "credential_access", 493112)

    assert key1 == key2
    assert key1.startswith("S1-")


def test_campaign_seed_key_distinct_from_campaign_identity():
    campaign_key = make_campaign_identity_key("shared_entity", "user:U1", "credential_access", 493112)
    seed_key = make_campaign_seed_key("shared_entity", "user:U1", "credential_access", 493112)

    assert seed_key != campaign_key


def test_seed_uses_phase1_identity_dimensions():
    base = make_campaign_seed_key("shared_entity", "user:U1", "credential_access", 493112)

    assert base != make_campaign_seed_key("temporal", "user:U1", "credential_access", 493112)
    assert base != make_campaign_seed_key("shared_entity", "user:U2", "credential_access", 493112)
    assert base != make_campaign_seed_key("shared_entity", "user:U1", "lateral_movement", 493112)
    assert base != make_campaign_seed_key("shared_entity", "user:U1", "credential_access", 493113)


def test_campaign_advisory_lock_key_is_deterministic_int64():
    key1 = campaign_advisory_lock_key("S1-seed-a")
    key2 = campaign_advisory_lock_key("S1-seed-a")
    key3 = campaign_advisory_lock_key("S1-seed-b")

    assert key1 == key2
    assert key1 != key3
    assert isinstance(key1, int)
    assert -(2**63) <= key1 <= 2**63 - 1


@pytest.mark.age
def test_persist_seed_acquires_db_advisory_lock_before_match_create(age_graph):
    graph = CampaignGraphProbe(age_graph, alerts=["a1"])
    repo = CampaignRepository(graph)
    event = _event("a1")
    expected_seed = campaign_seed_candidate(event, 24 * 3600)

    run(repo.persist_campaign_seed(event, window_seconds=24 * 3600))

    assert graph.operations[0][0] == "sql"
    assert graph.operations[0][1] == "SELECT pg_advisory_xact_lock(%s)"
    assert graph.operations[0][2] == (campaign_advisory_lock_key(expected_seed["seed_key"]),)
    assert graph.operations[1][0] == "cypher"
    assert "MATCH (s:CampaignSeed" in graph.operations[1][1]
    assert "CREATE (s:CampaignSeed" in graph.operations[2][1]


@pytest.mark.age
def test_materialize_seed_campaign_acquires_db_advisory_lock_before_campaign_create(age_graph):
    events = [_event("a1", minutes=0), _event("a2", minutes=1)]
    campaign = _campaign(events)
    graph = CampaignGraphProbe(age_graph, alerts=["a1", "a2"])
    repo = CampaignRepository(graph)
    run(repo.persist_campaign_seed(events[0], window_seconds=24 * 3600))
    graph.operations.clear()

    run(repo.materialize_seed_campaign(campaign))

    assert graph.operations[0][0] == "sql"
    assert graph.operations[0][1] == "SELECT pg_advisory_xact_lock(%s)"
    assert graph.operations[0][2] == (campaign_advisory_lock_key(campaign.campaign_id),)
    assert graph.operations[1][0] == "cypher"
    assert "MATCH (c:Campaign" in graph.operations[1][1]
    assert any("CREATE (c:Campaign" in op[1] for op in graph.operations if op[0] == "cypher")


@pytest.mark.age
def test_write_campaign_acquires_db_advisory_lock_for_age_client(age_graph):
    events = [_event("a1", minutes=0), _event("a2", minutes=1)]
    campaign = _campaign(events)
    graph = CampaignGraphProbe(age_graph, alerts=["a1", "a2"])
    repo = CampaignRepository(graph)

    assert run(repo.write_campaign(campaign)) is True

    assert graph.operations[0][0] == "sql"
    assert graph.operations[0][1] == "SELECT pg_advisory_xact_lock(%s)"
    assert graph.operations[0][2] == (campaign_advisory_lock_key(campaign.campaign_id),)
    assert graph.operations[1][0] == "cypher"
    assert "MATCH (c:Campaign" in graph.operations[1][1]


@pytest.mark.age
def test_write_campaign_rechecks_campaign_under_lock(age_graph):
    events = [_event("a1", minutes=0), _event("a2", minutes=1)]
    campaign = _campaign(events)
    graph = CampaignGraphProbe(age_graph, alerts=["a1", "a2"])
    repo = CampaignRepository(graph)

    assert run(repo.write_campaign(campaign)) is True
    graph.operations.clear()
    assert run(repo.write_campaign(campaign)) is True

    assert graph.operations[0][0] == "sql"
    assert "pg_advisory_xact_lock" in graph.operations[0][1]
    assert "MATCH (c:Campaign" in graph.operations[1][1]
    assert not any("CREATE (c:Campaign" in op[1] for op in graph.operations if op[0] == "cypher")
    assert graph.campaign_create_count == 1


@pytest.mark.age
def test_write_campaign_rechecks_member_edges_under_lock(age_graph):
    events = [_event("a1", minutes=0), _event("a2", minutes=1)]
    campaign = _campaign(events)
    graph = CampaignGraphProbe(age_graph, alerts=["a1", "a2"])
    repo = CampaignRepository(graph)

    assert run(repo.write_campaign(campaign)) is True
    graph.operations.clear()
    assert run(repo.write_campaign(campaign)) is True

    assert graph.operations[0][0] == "sql"
    assert "pg_advisory_xact_lock" in graph.operations[0][1]
    assert not any(
        "CREATE (a" in op[1] and "[:MEMBER_OF]->(c)" in op[1]
        for op in graph.operations
        if op[0] == "cypher"
    )
    assert graph.member_edge_create_count == 2


@pytest.mark.age
def test_recorrelation_direct_write_campaign_uses_locked_public_path(age_graph):
    events = [_event("a1", minutes=0), _event("a2", minutes=1)]
    campaign = _campaign(events)
    graph = CampaignGraphProbe(age_graph, alerts=["a1", "a2"])
    repo = CampaignRepository(graph)

    # Recorrelation calls public write_campaign directly; it must not bypass
    # the AGE advisory lock when the graph client supports transactions.
    assert run(repo.write_campaign(campaign)) is True

    assert graph.operations[0][0] == "sql"
    assert "pg_advisory_xact_lock" in graph.operations[0][1]


@pytest.mark.age
def test_materialize_seed_campaign_uses_unlocked_internal_only_under_lock(age_graph):
    events = [_event("a1", minutes=0), _event("a2", minutes=1)]
    campaign = _campaign(events)
    graph = CampaignGraphProbe(age_graph, alerts=["a1", "a2"])
    repo = CampaignRepository(graph)
    run(repo.persist_campaign_seed(events[0], window_seconds=24 * 3600))
    graph.operations.clear()

    assert run(repo.materialize_seed_campaign(campaign)) is True

    lock_ops = [
        op for op in graph.operations
        if op[0] == "sql" and "pg_advisory_xact_lock" in op[1]
    ]
    assert len(lock_ops) == 1
    assert lock_ops[0][2] == (campaign_advisory_lock_key(campaign.campaign_id),)


@pytest.mark.age
def test_seed_persists_before_min2(age_graph):
    graph = CampaignGraphProbe(age_graph, alerts=["a1"])
    repo = CampaignRepository(graph)

    seed = run(repo.persist_campaign_seed(_event("a1"), window_seconds=24 * 3600))

    assert seed is not None
    assert set(graph.seeds) == {seed["seed_key"]}
    assert graph.campaigns == set()
    assert graph.edges == set()


@pytest.mark.age
def test_seed_promotes_to_campaign_at_min2(age_graph):
    events = [_event("a1", minutes=0), _event("a2", minutes=1)]
    campaign = _campaign(events)
    graph = CampaignGraphProbe(age_graph, alerts=["a1", "a2"])
    repo = CampaignRepository(graph)

    run(repo.persist_campaign_seed(events[0], window_seconds=24 * 3600))
    result = run(repo.materialize_seed_campaign(campaign))

    assert result is True
    assert graph.campaigns == {campaign.campaign_id}
    assert graph.edges == {("a1", campaign.campaign_id), ("a2", campaign.campaign_id)}
    seed_key = make_campaign_seed_key(campaign.rule_type, campaign.derived_entity_key, campaign.category, campaign.time_bucket)
    assert graph.seeds[seed_key]["status"] == "promoted"


@pytest.mark.age
def test_duplicate_seed_prevention(age_graph):
    graph = CampaignGraphProbe(age_graph, alerts=["a1"])
    repo = CampaignRepository(graph)
    event = _event("a1")

    seed1 = run(repo.persist_campaign_seed(event, window_seconds=24 * 3600))
    seed2 = run(repo.persist_campaign_seed(event, window_seconds=24 * 3600))

    assert seed1["seed_key"] == seed2["seed_key"]
    assert len(graph.seeds) == 1
    assert graph.seed_create_count == 1


@pytest.mark.age
def test_seed_persistence_duplicate_race_rechecks_under_lock(age_graph):
    graph = CampaignGraphProbe(age_graph, alerts=["a1"])
    repo = CampaignRepository(graph)
    event = _event("a1")

    run(repo.persist_campaign_seed(event, window_seconds=24 * 3600))
    graph.operations.clear()
    run(repo.persist_campaign_seed(event, window_seconds=24 * 3600))

    assert graph.operations[0][0] == "sql"
    assert "pg_advisory_xact_lock" in graph.operations[0][1]
    assert "MATCH (s:CampaignSeed" in graph.operations[1][1]
    assert any("SET s.alert_ids" in op[1] for op in graph.operations if op[0] == "cypher")
    assert not any("CREATE (s:CampaignSeed" in op[1] for op in graph.operations if op[0] == "cypher")
    assert graph.seed_create_count == 1


@pytest.mark.age
def test_concurrent_materialization_single_campaign(age_graph):
    events = [_event("a1", minutes=0), _event("a2", minutes=1)]
    campaign = _campaign(events)
    graph = CampaignGraphProbe(age_graph, alerts=["a1", "a2"])
    repo = CampaignRepository(graph)
    run(repo.persist_campaign_seed(events[0], window_seconds=24 * 3600))

    async def race():
        return await asyncio.gather(
            repo.materialize_seed_campaign(campaign),
            repo.materialize_seed_campaign(campaign),
        )

    assert run(race()) == [True, True]
    assert graph.campaigns == {campaign.campaign_id}
    assert graph.edges == {("a1", campaign.campaign_id), ("a2", campaign.campaign_id)}


@pytest.mark.age
def test_campaign_materialization_duplicate_race_rechecks_under_lock(age_graph):
    events = [_event("a1", minutes=0), _event("a2", minutes=1)]
    campaign = _campaign(events)
    graph = CampaignGraphProbe(age_graph, alerts=["a1", "a2"])
    repo = CampaignRepository(graph)
    run(repo.persist_campaign_seed(events[0], window_seconds=24 * 3600))

    run(repo.materialize_seed_campaign(campaign))
    graph.operations.clear()
    run(repo.materialize_seed_campaign(campaign))

    assert graph.operations[0][0] == "sql"
    assert "pg_advisory_xact_lock" in graph.operations[0][1]
    assert "MATCH (c:Campaign" in graph.operations[1][1]
    assert not any("CREATE (c:Campaign" in op[1] for op in graph.operations if op[0] == "cypher")
    assert graph.campaign_create_count == 1
    assert graph.member_edge_create_count == 2


@pytest.mark.age
def test_no_process_local_lock_as_only_correctness_mechanism(age_graph):
    events = [_event("a1", minutes=0), _event("a2", minutes=1)]
    graph = CampaignGraphProbe(age_graph, alerts=["a1", "a2"])
    repo = CampaignRepository(graph)

    run(repo.persist_campaign_seed(events[0], window_seconds=24 * 3600))
    run(repo.materialize_seed_campaign(_campaign(events)))

    lock_sql_ops = [
        op for op in graph.operations
        if op[0] == "sql" and "pg_advisory_xact_lock" in op[1]
    ]
    assert len(lock_sql_ops) >= 2


@pytest.mark.age
def test_no_merge_used(age_graph):
    events = [_event("a1", minutes=0), _event("a2", minutes=1)]
    graph = CampaignGraphProbe(age_graph, alerts=["a1", "a2"])
    repo = CampaignRepository(graph)

    run(repo.persist_campaign_seed(events[0], window_seconds=24 * 3600))
    run(repo.materialize_seed_campaign(_campaign(events)))

    assert all("MERGE" not in query.upper() for query in graph.queries)


@pytest.mark.age
def test_no_continues_created(age_graph):
    events = [_event("a1", minutes=0), _event("a2", minutes=1)]
    graph = CampaignGraphProbe(age_graph, alerts=["a1", "a2"])
    repo = CampaignRepository(graph)

    run(repo.persist_campaign_seed(events[0], window_seconds=24 * 3600))
    run(repo.materialize_seed_campaign(_campaign(events)))

    assert graph.continues_edges == {}


@pytest.mark.age
def test_no_belongs_to_created(age_graph):
    events = [_event("a1", minutes=0), _event("a2", minutes=1)]
    graph = CampaignGraphProbe(age_graph, alerts=["a1", "a2"])
    repo = CampaignRepository(graph)

    run(repo.persist_campaign_seed(events[0], window_seconds=24 * 3600))
    run(repo.materialize_seed_campaign(_campaign(events)))

    assert all("BELONGS_TO" not in query for query in graph.queries)


@pytest.mark.age
def test_orphan_seed_cleanup_marks_or_removes_only_unmaterialized_seed(age_graph):
    graph = CampaignGraphProbe(age_graph, alerts=["a1"])
    repo = CampaignRepository(graph)
    seed = run(repo.persist_campaign_seed(_event("a1"), window_seconds=24 * 3600))
    age_graph.set_properties("CampaignSeed", "seed_key", seed["seed_key"], updated_at_epoch=1)

    expired = run(repo.cleanup_orphan_campaign_seeds(ttl_seconds=1))

    assert expired == 1
    assert graph.seeds[seed["seed_key"]]["status"] == "expired"


@pytest.mark.age
def test_cleanup_does_not_delete_campaign_or_member_edges(age_graph):
    events = [_event("a1", minutes=0), _event("a2", minutes=1)]
    campaign = _campaign(events)
    graph = CampaignGraphProbe(age_graph, alerts=["a1", "a2"])
    repo = CampaignRepository(graph)
    run(repo.persist_campaign_seed(events[0], window_seconds=24 * 3600))
    run(repo.materialize_seed_campaign(campaign))

    expired = run(repo.cleanup_orphan_campaign_seeds(ttl_seconds=1))

    assert expired == 0
    assert graph.campaigns == {campaign.campaign_id}
    assert graph.edges == {("a1", campaign.campaign_id), ("a2", campaign.campaign_id)}


def test_campaign_check_latency_budget():
    class FastRepo:
        def __init__(self):
            self.persisted = []
            self.materialized = []

        async def fetch_recent_events(self, *_args, **_kwargs):
            return [_event("a1", minutes=0), _event("a2", minutes=1)]

        async def fetch_single_alert_event(self, *_args, **_kwargs):
            return _event("a2", minutes=1)

        async def persist_campaign_seed(self, event, **_kwargs):
            self.persisted.append(event["alert_id"])
            return campaign_seed_candidate(event, 24 * 3600)

        async def materialize_seed_campaign(self, campaign, **_kwargs):
            self.materialized.append(campaign.campaign_id)
            return True

    repo = FastRepo()
    matcher = CampaignMatcher(None, DEFAULT_CONFIG, CampaignCorrelationEngine(DEFAULT_CONFIG), repo, background=False)

    result = run(matcher.check_alert_timed("a2"))

    assert result["campaign_id"] == repo.materialized[0]
    assert result["measurement_mode"] == "mock/unit"
    assert result["elapsed_ms"] <= 5.0
