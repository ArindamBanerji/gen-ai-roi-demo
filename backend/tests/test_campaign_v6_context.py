import asyncio
import os
import sys
from datetime import datetime, timedelta
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.domains.soc.campaigns import (
    CampaignAsyncState,
    CampaignCorrelationEngine,
    CampaignMatcher,
    CampaignTemporalContext,
)
from app.services.soc_situation_pattern import build_campaign_context_payload


DEFAULT_CONFIG = {
    "correlation_window_hours": 24,
    "temporal_window_minutes": 60,
    "min_alerts_for_campaign": 2,
    "max_campaign_age_days": 30,
}


def run(coro):
    return asyncio.run(coro)


def _event(alert_id, *, user_id="user-1", minutes=0):
    return {
        "alert_id": alert_id,
        "category": "credential_access",
        "source_entity_id": None,
        "user_id": user_id,
        "asset_id": None,
        "source_location": None,
        "technique_id": None,
        "ts": datetime(2026, 3, 25, 10, 0) + timedelta(minutes=minutes),
        "severity": "MEDIUM",
        "decision_id": f"decision-{alert_id}",
    }


class V6Graph:
    def __init__(self):
        self.campaigns = set()
        self.queries = []
        self.materialized_lookup_count = 0

    async def run_query(self, query, params=None):
        self.queries.append(query)
        if "MATCH (c:Campaign" in query and "RETURN c.campaign_id AS campaign_id" in query:
            self.materialized_lookup_count += 1
        return []


class V6Repo:
    def __init__(self, events, graph=None):
        self.events = list(events)
        self.graph = graph or V6Graph()
        self.persist_calls = 0
        self.materialize_calls = 0
        self.edges = set()

    async def fetch_single_alert_event(self, alert_id, **_kwargs):
        return next((event for event in self.events if event["alert_id"] == alert_id), None)

    async def fetch_recent_events(self, *_args, **_kwargs):
        return list(self.events)

    async def persist_campaign_seed(self, *_args, **_kwargs):
        self.persist_calls += 1
        return None

    async def materialize_seed_campaign(self, campaign, **_kwargs):
        self.materialize_calls += 1
        self.graph.campaigns.add(campaign.campaign_id)
        for alert_id in campaign.member_alert_ids:
            self.edges.add((alert_id, campaign.campaign_id))
        return True


def _matcher(events, *, background=False, async_state=None, graph=None, repo=None):
    graph = graph or V6Graph()
    repo = repo or V6Repo(events, graph=graph)
    engine = CampaignCorrelationEngine(DEFAULT_CONFIG)
    return CampaignMatcher(
        graph,
        DEFAULT_CONFIG,
        engine,
        repo,
        background=background,
        async_state=async_state or CampaignAsyncState(),
    ), repo, graph


def test_mark_materialized_with_context_stores_campaign_context():
    state = CampaignAsyncState()

    state.mark_materialized_with_context(
        "campaign-1",
        "credential_access",
        "2026-03-25T10:00:00",
        member_count=2,
    )
    context = state.get_campaign_context("campaign-1")

    assert context is not None
    assert context.campaign_id == "campaign-1"
    assert context.category == "credential_access"
    assert context.first_seen == "2026-03-25T10:00:00"
    assert context.member_count == 2


def test_get_campaign_context_returns_none_for_unknown_campaign_id():
    assert CampaignAsyncState().get_campaign_context("missing") is None


def test_increment_member_count_increments_existing_context_only():
    state = CampaignAsyncState()
    state.mark_materialized_with_context(
        "campaign-1",
        "credential_access",
        "2026-03-25T10:00:00",
        member_count=2,
    )

    state.increment_member_count("campaign-1")
    state.increment_member_count("missing")

    assert state.get_campaign_context("campaign-1").member_count == 3
    assert state.get_campaign_context("missing") is None


def test_existing_mark_materialized_still_populates_id_cache_without_context():
    state = CampaignAsyncState()

    state.mark_materialized("campaign-1")

    assert state.materialized_campaign_id("campaign-1") == "campaign-1"
    assert state.get_campaign_context("campaign-1") is None


def test_mark_materialized_with_context_preserves_materialized_id_cache():
    state = CampaignAsyncState()

    state.mark_materialized_with_context(
        "campaign-1",
        "credential_access",
        "2026-03-25T10:00:00",
        member_count=2,
    )

    assert state.materialized_campaign_id("campaign-1") == "campaign-1"


def test_materialization_success_populates_context_without_double_counting():
    async def scenario():
        events = [_event("a1", minutes=0), _event("a2", minutes=1)]
        state = CampaignAsyncState()
        matcher, repo, graph = _matcher(events, background=False, async_state=state)

        campaign_id = await matcher.check_alert("a2")
        lookup_count_after_check = graph.materialized_lookup_count
        context = state.get_campaign_context(campaign_id)

        assert campaign_id is not None
        assert context is not None
        assert context.category == "credential_access"
        assert context.first_seen == events[0]["ts"].isoformat()
        assert context.member_count == 2
        assert repo.edges == {("a1", campaign_id), ("a2", campaign_id)}
        assert graph.materialized_lookup_count == lookup_count_after_check

    run(scenario())


def test_campaign_context_cache_lookup_requires_no_age_read():
    state = CampaignAsyncState()
    state.mark_materialized_with_context(
        "campaign-1",
        "credential_access",
        "2026-03-25T10:00:00",
        member_count=2,
    )

    assert state.get_campaign_context("campaign-1").member_count == 2


def test_campaign_context_payload_returns_none_for_isolated_alert():
    payload, flags = build_campaign_context_payload(
        campaign_id=None,
        async_state=CampaignAsyncState(),
        alert_id="ALERT-1",
    )

    assert payload is None
    assert flags == {
        "is_campaign_alert": False,
        "campaign_context_shown": False,
    }


def test_campaign_context_payload_suppressed_campaign_has_flags_without_payload(monkeypatch):
    monkeypatch.setattr(
        "app.services.soc_situation_pattern.banner_suppressed",
        lambda alert_id, holdout_pct=15: True,
    )

    payload, flags = build_campaign_context_payload(
        campaign_id="campaign-1",
        async_state=CampaignAsyncState(),
        alert_id="ALERT-1",
    )

    assert payload is None
    assert flags["is_campaign_alert"] is True
    assert flags["campaign_context_shown"] is False
    assert flags["campaign_advisory_version"] == "phase4_temporal_v1"


def test_cold_cache_campaign_context_payload_degrades_to_campaign_id_only(monkeypatch):
    monkeypatch.setattr(
        "app.services.soc_situation_pattern.banner_suppressed",
        lambda alert_id, holdout_pct=15: False,
    )

    payload, flags = build_campaign_context_payload(
        campaign_id="campaign-1",
        async_state=CampaignAsyncState(),
        alert_id="ALERT-1",
    )

    assert flags["is_campaign_alert"] is True
    assert flags["campaign_context_shown"] is True
    assert flags["campaign_advisory_version"] == "phase4_temporal_v1"
    assert payload["campaign_id"] == "campaign-1"
    assert payload["source"] == "graph_store_cached"
    assert payload["advisory_version"] == "phase4_temporal_v1"
    assert payload["status"] == "cold_cache"
    assert "Emerging campaign pattern" in payload["advisory"]


def test_cached_campaign_context_payload_includes_context_and_emerging_wording(monkeypatch):
    monkeypatch.setattr(
        "app.services.soc_situation_pattern.banner_suppressed",
        lambda alert_id, holdout_pct=15: False,
    )
    state = CampaignAsyncState()
    state.mark_materialized_with_context(
        "campaign-1",
        "credential_access",
        datetime.utcnow().isoformat(),
        member_count=2,
    )

    payload, flags = build_campaign_context_payload(
        campaign_id="campaign-1",
        async_state=state,
        alert_id="ALERT-1",
    )

    assert flags["campaign_context_shown"] is True
    assert payload["category"] == "credential_access"
    assert payload["member_count"] == 2
    assert payload["age_days"] == 0
    assert payload["label"] == "Emerging Campaign Pattern"
    assert "consider escalating the campaign" not in payload["advisory"].lower()


def test_cached_campaign_context_payload_active_campaign_wording(monkeypatch):
    monkeypatch.setattr(
        "app.services.soc_situation_pattern.banner_suppressed",
        lambda alert_id, holdout_pct=15: False,
    )
    state = CampaignAsyncState()
    state.mark_materialized_with_context(
        "campaign-1",
        "credential_access",
        datetime.utcnow().isoformat(),
        member_count=3,
    )

    payload, _flags = build_campaign_context_payload(
        campaign_id="campaign-1",
        async_state=state,
        alert_id="ALERT-1",
    )

    assert payload["label"] == "Active Campaign"
    assert "Active 3-member campaign" in payload["advisory"]
    assert "Started today" in payload["advisory"]
    assert "Consider escalating the campaign" in payload["advisory"]
    assert "campaign-unaware" not in payload["advisory"]


def test_campaign_context_payload_includes_cached_phase4_temporal_context(monkeypatch):
    monkeypatch.setattr(
        "app.services.soc_situation_pattern.banner_suppressed",
        lambda alert_id, holdout_pct=15: False,
    )
    state = CampaignAsyncState()
    state.mark_materialized_with_context(
        "campaign-new",
        "credential_access",
        datetime.utcnow().isoformat(),
        member_count=4,
    )
    state.mark_temporal_context(
        CampaignTemporalContext(
            campaign_id="campaign-new",
            previous_campaign_id="campaign-old",
            chain_start_campaign_id="campaign-old",
            chain_start_bucket=20622,
            chain_length_buckets=2,
            total_alert_count=7,
            member_count_by_campaign={"campaign-old": 3, "campaign-new": 4},
        )
    )

    payload, flags = build_campaign_context_payload(
        campaign_id="campaign-new",
        async_state=state,
        alert_id="ALERT-temporal",
    )

    assert flags["campaign_context_shown"] is True
    assert payload["chain_day"] == 2
    assert payload["total_alerts_across_chain"] == 7
    assert payload["temporal_context"]["previous_campaign_ids"] == ["campaign-old"]
    assert payload["temporal_context"]["chain_campaign_ids"] == [
        "campaign-old",
        "campaign-new",
    ]
    assert payload["temporal_context"]["source"] == "graph_store_cached"
    assert "Ongoing incident context" in payload["advisory"]
    assert "temporal intelligence" in payload["advisory"]
    assert "campaign-unaware" in payload["advisory"]
    assert "compounding intelligence" not in payload["advisory"].lower()


def test_single_bucket_temporal_cache_does_not_overclaim_continuity(monkeypatch):
    monkeypatch.setattr(
        "app.services.soc_situation_pattern.banner_suppressed",
        lambda alert_id, holdout_pct=15: False,
    )
    state = CampaignAsyncState()
    state.mark_materialized_with_context(
        "campaign-single",
        "credential_access",
        datetime.utcnow().isoformat(),
        member_count=4,
    )
    state.mark_temporal_context(
        CampaignTemporalContext(
            campaign_id="campaign-single",
            chain_start_campaign_id="campaign-single",
            chain_start_bucket=20623,
            chain_length_buckets=1,
            total_alert_count=4,
            member_count_by_campaign={"campaign-single": 4},
        )
    )

    payload, flags = build_campaign_context_payload(
        campaign_id="campaign-single",
        async_state=state,
        alert_id="ALERT-single-bucket",
    )

    assert flags["campaign_context_shown"] is True
    assert payload["campaign_id"] == "campaign-single"
    assert payload["member_count"] == 4
    assert "temporal_context" not in payload
    assert "chain_day" not in payload
    assert "total_alerts_across_chain" not in payload
    assert "Ongoing incident context" not in payload["advisory"]
    assert "temporal chain" not in payload["advisory"]
    assert "temporal intelligence" not in payload["advisory"]


def test_campaign_context_payload_helper_does_not_call_age():
    class CacheOnlyState:
        def __init__(self):
            self.graph_calls = 0

        def get_campaign_context(self, campaign_id):
            return SimpleNamespace(
                campaign_id=campaign_id,
                category="credential_access",
                first_seen=datetime.utcnow().isoformat(),
                member_count=3,
            )

        async def run_query(self, *_args, **_kwargs):
            self.graph_calls += 1
            raise AssertionError("campaign context helper must not query AGE")

    state = CacheOnlyState()

    payload, flags = build_campaign_context_payload(
        campaign_id="campaign-1",
        async_state=state,
        alert_id="ALERT-no-age",
        holdout_pct=0,
    )

    assert flags["is_campaign_alert"] is True
    assert flags["campaign_context_shown"] is True
    assert payload["campaign_id"] == "campaign-1"
    assert state.graph_calls == 0
