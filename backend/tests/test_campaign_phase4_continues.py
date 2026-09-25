"""
tests/test_campaign_phase4_continues.py -- Phase 4 temporal CONTINUES edges.

Phase 4 adds advisory temporal context only. It must not affect scorer/tensor
behavior, create BELONGS_TO, or add hot-path campaign chain reads.
"""

import pytest
from support.campaign_graph import CampaignGraphProbe
from types import SimpleNamespace
from unittest.mock import AsyncMock

import asyncio
import os
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






def _write(repo, campaign):
    assert run(repo.write_campaign(campaign)) is True


@pytest.mark.age
def test_adjacent_same_identity_creates_one_continues_older_to_newer(age_graph):
    older = _campaign("old", days=0)
    newer = _campaign("new", days=1)
    graph = CampaignGraphProbe(age_graph, alerts=older.member_alert_ids + newer.member_alert_ids)
    repo = CampaignRepository(graph)

    _write(repo, older)
    _write(repo, newer)

    assert graph.continues_edges.keys() == {(older.campaign_id, newer.campaign_id)}
    assert graph.continues_create_count == 1


@pytest.mark.age
def test_duplicate_write_does_not_duplicate_continues(age_graph):
    older = _campaign("old", days=0)
    newer = _campaign("new", days=1)
    graph = CampaignGraphProbe(age_graph, alerts=older.member_alert_ids + newer.member_alert_ids)
    repo = CampaignRepository(graph)

    _write(repo, older)
    _write(repo, newer)
    _write(repo, newer)

    assert graph.continues_edges.keys() == {(older.campaign_id, newer.campaign_id)}
    assert graph.continues_create_count == 1
    assert graph.duplicate_continues_pair_count() == 0


@pytest.mark.age
def test_different_derived_entity_key_does_not_link(age_graph):
    older = _campaign("old", user_id="user-1", days=0)
    newer = _campaign("new", user_id="user-2", days=1)
    graph = CampaignGraphProbe(age_graph, alerts=older.member_alert_ids + newer.member_alert_ids)
    repo = CampaignRepository(graph)

    _write(repo, older)
    _write(repo, newer)

    assert graph.continues_edges == {}


@pytest.mark.age
def test_different_category_does_not_link(age_graph):
    older = _campaign("old", category="credential_access", days=0)
    newer = _campaign("new", category="lateral_movement", days=1)
    graph = CampaignGraphProbe(age_graph, alerts=older.member_alert_ids + newer.member_alert_ids)
    repo = CampaignRepository(graph)

    _write(repo, older)
    _write(repo, newer)

    assert graph.continues_edges == {}


@pytest.mark.age
def test_different_effective_rule_type_does_not_link(age_graph):
    older = _campaign("old", days=0)
    newer = _with_rule(_campaign("new", days=1), "temporal")
    graph = CampaignGraphProbe(age_graph, alerts=older.member_alert_ids + newer.member_alert_ids)
    repo = CampaignRepository(graph)

    _write(repo, older)
    _write(repo, newer)

    assert graph.continues_edges == {}


@pytest.mark.age
def test_conflicting_legacy_rule_fields_use_rule_type_as_effective_rule(age_graph):
    older = _campaign("old", days=0)
    newer = _with_rule(_campaign("new", days=1), "temporal")
    graph = CampaignGraphProbe(age_graph, alerts=older.member_alert_ids + newer.member_alert_ids)
    repo = CampaignRepository(graph)

    _write(repo, older)
    age_graph.set_properties("Campaign", "campaign_id", older.campaign_id, trigger_rule="temporal")
    assert graph.campaign_rows[older.campaign_id]["rule_type"] == "shared_entity"
    _write(repo, newer)

    assert graph.continues_edges == {}


@pytest.mark.age
def test_missing_older_rule_type_falls_back_to_trigger_rule(age_graph):
    older = _with_rule(_campaign("old", days=0), "temporal")
    newer = _with_rule(_campaign("new", days=1), "temporal")
    graph = CampaignGraphProbe(age_graph, alerts=older.member_alert_ids + newer.member_alert_ids)
    repo = CampaignRepository(graph)

    _write(repo, older)
    age_graph.set_properties("Campaign", "campaign_id", older.campaign_id, rule_type="")
    _write(repo, newer)

    assert graph.continues_edges.keys() == {(older.campaign_id, newer.campaign_id)}


@pytest.mark.age
def test_non_adjacent_bucket_does_not_link_in_v1(age_graph):
    older = _campaign("old", days=0)
    newer = _campaign("new", days=2)
    graph = CampaignGraphProbe(age_graph, alerts=older.member_alert_ids + newer.member_alert_ids)
    repo = CampaignRepository(graph)

    _write(repo, older)
    _write(repo, newer)

    assert graph.continues_edges == {}


@pytest.mark.age
def test_missing_identity_fields_skip_safely(age_graph):
    older = _campaign("old", days=0)
    newer = _campaign("new", days=1)
    newer.derived_entity_key = ""
    graph = CampaignGraphProbe(age_graph, alerts=older.member_alert_ids + newer.member_alert_ids)
    repo = CampaignRepository(graph)

    _write(repo, older)
    _write(repo, newer)

    assert graph.continues_edges == {}


@pytest.mark.age
def test_continues_edge_properties_are_written(age_graph):
    older = _campaign("old", days=0)
    newer = _campaign("new", days=1)
    graph = CampaignGraphProbe(age_graph, alerts=older.member_alert_ids + newer.member_alert_ids)
    repo = CampaignRepository(graph)

    _write(repo, older)
    _write(repo, newer)

    props = graph.continues_edges[(older.campaign_id, newer.campaign_id)]
    assert props["created_at_epoch"] > 0
    assert props["gap_buckets"] == 1
    assert props["rule_type"] == "shared_entity"


@pytest.mark.age
def test_materialize_seed_campaign_uses_same_locked_continues_path(age_graph):
    older = _campaign("old", days=0)
    newer = _campaign("new", days=1)
    graph = CampaignGraphProbe(age_graph, alerts=older.member_alert_ids + newer.member_alert_ids)
    repo = CampaignRepository(graph)

    assert run(repo.materialize_seed_campaign(older)) is True
    assert run(repo.materialize_seed_campaign(newer)) is True

    assert graph.operations[0] == (
        "sql",
        "SELECT pg_advisory_xact_lock(%s)",
        (campaign_advisory_lock_key(older.campaign_id),),
    )
    assert (older.campaign_id, newer.campaign_id) in graph.continues_edges


@pytest.mark.age
def test_no_belongs_to_or_campaign_seed_writes_from_phase4_direct_path(age_graph):
    older = _campaign("old", days=0)
    newer = _campaign("new", days=1)
    graph = CampaignGraphProbe(age_graph, alerts=older.member_alert_ids + newer.member_alert_ids)
    repo = CampaignRepository(graph)

    _write(repo, older)
    _write(repo, newer)

    all_text = "\n".join(graph.queries)
    assert "BELONGS_TO" not in all_text
    assert "CREATE (s:CampaignSeed" not in all_text


@pytest.mark.age
def test_temporal_context_cache_updates_after_success(age_graph):
    older = _campaign("old", days=0)
    newer = _campaign("new", days=1)
    graph = CampaignGraphProbe(age_graph, alerts=older.member_alert_ids + newer.member_alert_ids)
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
    graph = SimpleNamespace(run_query=AsyncMock(side_effect=AssertionError("unexpected graph read")), queries=[])
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
    graph.run_query.assert_not_awaited()


def test_m8_style_unit_cache_hit_remains_fast():
    event = _event("hot-1")
    seed_campaign = campaign_seed_candidate(
        event,
        CampaignCorrelationEngine(DEFAULT_CONFIG).window_seconds,
    )["campaign_id"]
    state = CampaignAsyncState()
    state.mark_materialized(seed_campaign)
    graph = SimpleNamespace(run_query=AsyncMock(side_effect=AssertionError("unexpected graph read")))
    matcher = CampaignMatcher(
        graph,
        DEFAULT_CONFIG,
        CampaignCorrelationEngine(DEFAULT_CONFIG),
        HotPathRepo(event),
        background=True,
        async_state=state,
    )

    timed = run(matcher.check_alert_timed("hot-1"))

    assert timed["campaign_id"] == seed_campaign
    graph.run_query.assert_not_awaited()
    assert timed["measurement_mode"] == "mock/unit"
    assert timed["elapsed_ms"] < 5.0
