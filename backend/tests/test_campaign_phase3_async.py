"""
tests/test_campaign_phase3_async.py -- Campaign Phase 3 async materialization.

Phase 3 changes when seed/campaign writes run, not how the 1b-2 locked
materialization path writes graph data.
"""

import asyncio
import logging
import os
import re
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.domains.soc.campaigns import (
    CampaignAsyncState,
    CampaignCorrelationEngine,
    CampaignMatcher,
    campaign_seed_candidate,
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


class Phase3Graph:
    def __init__(self):
        self.campaigns = set()
        self.queries = []
        self.materialized_lookup_count = 0

    async def run_query(self, query, params=None):
        self.queries.append(query)
        if "MATCH (c:Campaign" in query and "RETURN c.campaign_id AS campaign_id" in query:
            self.materialized_lookup_count += 1
            campaign_id = self._campaign_id(query)
            if campaign_id in self.campaigns:
                return [{"campaign_id": campaign_id}]
        return []

    @staticmethod
    def _campaign_id(query):
        match = re.search(r"campaign_id: '([^']+)'", query)
        return match.group(1) if match else None


class Phase3Repo:
    def __init__(self, events, graph=None):
        self.events = list(events)
        self.graph = graph or Phase3Graph()
        self.seeds = {}
        self.edges = set()
        self.persist_calls = 0
        self.materialize_calls = 0
        self.fail_materialize = False
        self.materialize_started = asyncio.Event()
        self.release_materialize = None

    async def fetch_single_alert_event(self, alert_id, **_kwargs):
        return next((event for event in self.events if event["alert_id"] == alert_id), None)

    async def fetch_recent_events(self, *_args, **_kwargs):
        return list(self.events)

    async def persist_campaign_seed(self, event, *, window_seconds, **_kwargs):
        self.persist_calls += 1
        seed = campaign_seed_candidate(event, window_seconds)
        if seed:
            self.seeds.setdefault(seed["seed_key"], {**seed, "status": "open"})
        return seed

    async def materialize_seed_campaign(self, campaign, **_kwargs):
        self.materialize_calls += 1
        self.materialize_started.set()
        if self.release_materialize is not None:
            await self.release_materialize.wait()
        if self.fail_materialize:
            raise RuntimeError("injected background failure")
        self.graph.campaigns.add(campaign.campaign_id)
        for alert_id in campaign.member_alert_ids:
            self.edges.add((alert_id, campaign.campaign_id))
        return True

    async def write_campaign(self, campaign, **kwargs):
        return await self.materialize_seed_campaign(campaign, **kwargs)


def _matcher(events, *, background=True, graph=None, async_state=None, repo=None):
    graph = graph or Phase3Graph()
    engine = CampaignCorrelationEngine(DEFAULT_CONFIG)
    repo = repo or Phase3Repo(events, graph=graph)
    matcher = CampaignMatcher(
        graph,
        DEFAULT_CONFIG,
        engine,
        repo,
        background=background,
        async_state=async_state or CampaignAsyncState(),
    )
    return matcher, repo, graph


def test_background_false_check_alert_returns_correct_match_when_campaign_exists():
    events = [_event("a1", minutes=0), _event("a2", minutes=1)]
    matcher, repo, _graph = _matcher(events, background=False)

    result = run(matcher.check_alert("a2"))

    assert result is not None
    assert repo.materialize_calls == 1
    assert repo.edges == {("a1", result), ("a2", result)}


def test_background_false_check_alert_returns_null_when_no_campaign_exists():
    matcher, repo, _graph = _matcher([_event("a1")], background=False)

    result = run(matcher.check_alert("a1"))

    assert result is None
    assert repo.persist_calls == 1
    assert repo.materialize_calls == 0


def test_background_false_materialization_creates_seed_and_member_edges():
    events = [_event("a1", minutes=0), _event("a2", minutes=1)]
    matcher, repo, _graph = _matcher(events, background=False)

    result = run(matcher.check_alert("a2"))

    assert result is not None
    assert len(repo.seeds) == 1
    assert repo.edges == {("a1", result), ("a2", result)}


def test_background_false_materialization_remains_idempotent():
    events = [_event("a1", minutes=0), _event("a2", minutes=1)]
    matcher, repo, _graph = _matcher(events, background=False)

    first = run(matcher.check_alert("a2"))
    second = run(matcher.check_alert("a2"))

    assert first == second
    assert len(repo.seeds) == 1
    assert len(repo.edges) == 2


def test_background_false_uses_existing_materialization_path():
    events = [_event("a1", minutes=0), _event("a2", minutes=1)]
    matcher, repo, _graph = _matcher(events, background=False)

    run(matcher.check_alert("a2"))

    assert repo.persist_calls == 1
    assert repo.materialize_calls == 1


def test_background_true_retains_task_and_done_callback_cleans_up():
    async def scenario():
        matcher, repo, _graph = _matcher(
            [_event("a1", minutes=0), _event("a2", minutes=1)],
            background=True,
        )
        repo.release_materialize = asyncio.Event()

        assert await matcher.check_alert("a2") is None
        await repo.materialize_started.wait()
        assert len(matcher._bg_tasks) == 1
        repo.release_materialize.set()
        await asyncio.gather(*list(matcher._bg_tasks))
        await asyncio.sleep(0)

        assert matcher._bg_tasks == set()
        assert matcher._pending_seeds == set()

    run(scenario())


def test_async_state_shared_across_matcher_instances():
    async def scenario():
        events = [_event("a1", user_id="user-1"), _event("a2", user_id="user-1", minutes=1)]
        graph = Phase3Graph()
        repo = Phase3Repo(events, graph=graph)
        shared_state = CampaignAsyncState()
        matcher_a, _repo, _graph = _matcher(
            events,
            background=True,
            graph=graph,
            repo=repo,
            async_state=shared_state,
        )
        matcher_b, _repo, _graph = _matcher(
            events,
            background=True,
            graph=graph,
            repo=repo,
            async_state=shared_state,
        )
        repo.release_materialize = asyncio.Event()

        assert await matcher_a.check_alert("a1") is None
        await repo.materialize_started.wait()
        seed = campaign_seed_candidate(
            events[0],
            DEFAULT_CONFIG["correlation_window_hours"] * 3600,
        )

        assert seed["seed_key"] in matcher_b._pending_seeds
        assert matcher_b._pending_seed_campaigns[seed["seed_key"]] == seed["campaign_id"]
        repo.release_materialize.set()
        await asyncio.gather(*list(shared_state.bg_tasks))
        await asyncio.sleep(0)

    run(scenario())


def test_same_seed_storm_across_matcher_instances_spawns_one_task():
    async def scenario():
        events = [_event(f"a{i}", user_id="user-1", minutes=i) for i in range(100)]
        graph = Phase3Graph()
        repo = Phase3Repo(events, graph=graph)
        shared_state = CampaignAsyncState()
        matchers = [
            _matcher(
                events,
                background=True,
                graph=graph,
                repo=repo,
                async_state=shared_state,
            )[0]
            for _ in events
        ]
        repo.release_materialize = asyncio.Event()

        results = await asyncio.gather(
            *(matcher.check_alert(event["alert_id"]) for matcher, event in zip(matchers, events))
        )
        await repo.materialize_started.wait()

        assert len(shared_state.bg_tasks) == 1
        assert repo.materialize_calls == 1
        assert any(result is not None for result in results[1:])
        repo.release_materialize.set()
        await asyncio.gather(*list(shared_state.bg_tasks))
        await asyncio.sleep(0)

        assert shared_state.bg_tasks == set()
        assert shared_state.pending_seeds == set()

    run(scenario())


def test_seed_key_dedup_storm_spawns_one_background_task():
    async def scenario():
        events = [_event(f"a{i}", user_id="user-1", minutes=i) for i in range(100)]
        matcher, repo, _graph = _matcher(events, background=True)
        repo.release_materialize = asyncio.Event()

        results = await asyncio.gather(*(matcher.check_alert(e["alert_id"]) for e in events))
        await repo.materialize_started.wait()

        assert len(matcher._bg_tasks) == 1
        assert repo.materialize_calls == 1
        assert any(result is not None for result in results[1:])
        repo.release_materialize.set()
        await asyncio.gather(*list(matcher._bg_tasks))
        await asyncio.sleep(0)

        assert matcher._bg_tasks == set()

    run(scenario())


def test_storm_converges_to_one_seed_after_background_completion():
    async def scenario():
        events = [_event(f"a{i}", user_id="user-1", minutes=i) for i in range(100)]
        matcher, repo, _graph = _matcher(events, background=True)
        repo.release_materialize = asyncio.Event()

        await asyncio.gather(*(matcher.check_alert(e["alert_id"]) for e in events))
        repo.release_materialize.set()
        await asyncio.gather(*list(matcher._bg_tasks))
        await asyncio.sleep(0)

        assert len(repo.seeds) == 1
        assert matcher._pending_seeds == set()

    run(scenario())


def test_background_failure_logs_warning_and_does_not_affect_caller(caplog):
    async def scenario():
        matcher, repo, _graph = _matcher(
            [_event("a1", minutes=0), _event("a2", minutes=1)],
            background=True,
        )
        repo.fail_materialize = True
        caplog.set_level(logging.WARNING)

        assert await matcher.check_alert("a2") is None
        await asyncio.gather(*list(matcher._bg_tasks))
        await asyncio.sleep(0)

        assert "Background campaign materialization failed" in caplog.text
        assert matcher._bg_tasks == set()
        assert matcher._pending_seeds == set()

    run(scenario())


def test_pending_seed_check_returns_provisional_match_while_pending():
    async def scenario():
        events = [_event("a1", user_id="user-1"), _event("a2", user_id="user-1", minutes=1)]
        matcher, repo, _graph = _matcher(events, background=True)
        repo.release_materialize = asyncio.Event()

        first = await matcher.check_alert("a1")
        await repo.materialize_started.wait()
        second = await matcher.check_alert("a2")

        assert first is None
        assert second is not None
        repo.release_materialize.set()
        await asyncio.gather(*list(matcher._bg_tasks))

    run(scenario())


def test_pending_provisional_match_visible_across_request_like_matchers():
    async def scenario():
        events = [_event("a1", user_id="user-1"), _event("a2", user_id="user-1", minutes=1)]
        graph = Phase3Graph()
        repo = Phase3Repo(events, graph=graph)
        shared_state = CampaignAsyncState()
        matcher_a, _repo, _graph = _matcher(
            events,
            background=True,
            graph=graph,
            repo=repo,
            async_state=shared_state,
        )
        matcher_b, _repo, _graph = _matcher(
            events,
            background=True,
            graph=graph,
            repo=repo,
            async_state=shared_state,
        )
        repo.release_materialize = asyncio.Event()

        first = await matcher_a.check_alert("a1")
        await repo.materialize_started.wait()
        second = await matcher_b.check_alert("a2")

        assert first is None
        assert second is not None
        repo.release_materialize.set()
        await asyncio.gather(*list(shared_state.bg_tasks))
        await asyncio.sleep(0)

    run(scenario())


def test_pending_seed_check_does_not_override_materialized_match():
    async def scenario():
        event = _event("a1")
        matcher, _repo, graph = _matcher([event], background=True)
        seed = campaign_seed_candidate(event, DEFAULT_CONFIG["correlation_window_hours"] * 3600)
        matcher._pending_seeds.add(seed["seed_key"])
        matcher._pending_seed_campaigns[seed["seed_key"]] = "pending-campaign"
        matcher.async_state.mark_materialized(seed["campaign_id"])

        result = await matcher.check_alert("a1")

        assert result == seed["campaign_id"]
        assert graph.materialized_lookup_count == 0

    run(scenario())


def test_materialized_cache_hit_avoids_age_campaign_lookup():
    async def scenario():
        event = _event("a1")
        shared_state = CampaignAsyncState()
        seed = campaign_seed_candidate(
            event,
            DEFAULT_CONFIG["correlation_window_hours"] * 3600,
        )
        shared_state.mark_materialized(seed["campaign_id"])
        matcher, _repo, graph = _matcher(
            [event],
            background=True,
            async_state=shared_state,
        )

        result = await matcher.check_alert("a1")
        await asyncio.gather(*list(shared_state.bg_tasks))
        await asyncio.sleep(0)

        assert result == seed["campaign_id"]
        assert graph.materialized_lookup_count == 0

    run(scenario())


def test_materialized_cache_hit_does_not_schedule_background_materialization():
    async def scenario():
        event = _event("a1")
        shared_state = CampaignAsyncState()
        seed = campaign_seed_candidate(
            event,
            DEFAULT_CONFIG["correlation_window_hours"] * 3600,
        )
        shared_state.mark_materialized(seed["campaign_id"])
        matcher, repo, graph = _matcher(
            [event],
            background=True,
            async_state=shared_state,
        )

        result = await matcher.check_alert("a1")

        assert result == seed["campaign_id"]
        assert graph.materialized_lookup_count == 0
        assert shared_state.bg_tasks == set()
        assert shared_state.pending_seeds == set()
        assert repo.persist_calls == 0
        assert repo.materialize_calls == 0

    run(scenario())


def test_age_fallback_hit_populates_materialized_cache():
    async def scenario():
        event = _event("a1")
        shared_state = CampaignAsyncState()
        matcher, _repo, graph = _matcher(
            [event],
            background=True,
            async_state=shared_state,
        )
        seed = campaign_seed_candidate(
            event,
            DEFAULT_CONFIG["correlation_window_hours"] * 3600,
        )
        graph.campaigns.add(seed["campaign_id"])

        first = await matcher.check_alert("a1")
        await asyncio.gather(*list(shared_state.bg_tasks))
        await asyncio.sleep(0)
        first_lookup_count = graph.materialized_lookup_count
        second = await matcher.check_alert("a1")
        await asyncio.gather(*list(shared_state.bg_tasks))
        await asyncio.sleep(0)

        assert first == seed["campaign_id"]
        assert second == seed["campaign_id"]
        assert shared_state.materialized_campaign_id(seed["campaign_id"]) == seed["campaign_id"]
        assert first_lookup_count == 1
        assert graph.materialized_lookup_count == first_lookup_count

    run(scenario())


def test_age_materialized_fallback_hit_populates_cache_and_does_not_schedule():
    async def scenario():
        event = _event("a1")
        shared_state = CampaignAsyncState()
        matcher, repo, graph = _matcher(
            [event],
            background=True,
            async_state=shared_state,
        )
        seed = campaign_seed_candidate(
            event,
            DEFAULT_CONFIG["correlation_window_hours"] * 3600,
        )
        graph.campaigns.add(seed["campaign_id"])

        first = await matcher.check_alert("a1")
        first_lookup_count = graph.materialized_lookup_count
        second = await matcher.check_alert("a1")

        assert first == seed["campaign_id"]
        assert second == seed["campaign_id"]
        assert shared_state.materialized_campaign_id(seed["campaign_id"]) == seed["campaign_id"]
        assert first_lookup_count == 1
        assert graph.materialized_lookup_count == first_lookup_count
        assert shared_state.bg_tasks == set()
        assert shared_state.pending_seeds == set()
        assert repo.persist_calls == 0
        assert repo.materialize_calls == 0

    run(scenario())


def test_materialized_cache_takes_precedence_over_pending():
    async def scenario():
        event = _event("a1")
        shared_state = CampaignAsyncState()
        seed = campaign_seed_candidate(
            event,
            DEFAULT_CONFIG["correlation_window_hours"] * 3600,
        )
        shared_state.mark_pending(seed["seed_key"], "pending-campaign")
        shared_state.mark_materialized(seed["campaign_id"])
        matcher, _repo, graph = _matcher(
            [event],
            background=True,
            async_state=shared_state,
        )

        result = await matcher.check_alert("a1")

        assert result == seed["campaign_id"]
        assert graph.materialized_lookup_count == 0

    run(scenario())


def test_pending_provisional_hit_does_not_schedule_duplicate_work():
    async def scenario():
        event = _event("a1")
        shared_state = CampaignAsyncState()
        seed = campaign_seed_candidate(
            event,
            DEFAULT_CONFIG["correlation_window_hours"] * 3600,
        )
        assert shared_state.mark_pending(seed["seed_key"], seed["campaign_id"]) is True
        matcher, repo, graph = _matcher(
            [event],
            background=True,
            async_state=shared_state,
        )

        result = await matcher.check_alert("a1")

        assert result == seed["campaign_id"]
        assert graph.materialized_lookup_count == 0
        assert shared_state.bg_tasks == set()
        assert shared_state.pending_seeds == {seed["seed_key"]}
        assert repo.persist_calls == 0
        assert repo.materialize_calls == 0

    run(scenario())


def test_true_miss_is_only_path_that_schedules_background():
    async def scenario():
        events = [_event("a1", minutes=0), _event("a2", minutes=1)]
        shared_state = CampaignAsyncState()
        matcher, repo, graph = _matcher(
            events,
            background=True,
            async_state=shared_state,
        )
        repo.release_materialize = asyncio.Event()

        result = await matcher.check_alert("a2")
        await repo.materialize_started.wait()

        assert result is None
        assert graph.materialized_lookup_count == 1
        assert len(shared_state.bg_tasks) == 1
        assert len(shared_state.pending_seeds) == 1
        assert repo.persist_calls == 1
        assert repo.materialize_calls == 1
        repo.release_materialize.set()
        await asyncio.gather(*list(shared_state.bg_tasks))
        await asyncio.sleep(0)

    run(scenario())


def test_background_materialization_success_updates_cache():
    async def scenario():
        events = [_event("a1", minutes=0), _event("a2", minutes=1)]
        shared_state = CampaignAsyncState()
        matcher, repo, _graph = _matcher(
            events,
            background=True,
            async_state=shared_state,
        )

        assert await matcher.check_alert("a2") is None
        await asyncio.gather(*list(shared_state.bg_tasks))
        await asyncio.sleep(0)

        assert repo.graph.campaigns
        campaign_id = next(iter(repo.graph.campaigns))
        assert shared_state.materialized_campaign_id(campaign_id) == campaign_id
        assert shared_state.pending_seeds == set()

    run(scenario())


def test_cache_is_shared_across_request_like_matchers():
    async def scenario():
        event = _event("a1")
        graph = Phase3Graph()
        repo = Phase3Repo([event], graph=graph)
        shared_state = CampaignAsyncState()
        matcher_a, _repo, _graph = _matcher(
            [event],
            background=True,
            graph=graph,
            repo=repo,
            async_state=shared_state,
        )
        matcher_b, _repo, _graph = _matcher(
            [event],
            background=True,
            graph=graph,
            repo=repo,
            async_state=shared_state,
        )
        seed = campaign_seed_candidate(
            event,
            DEFAULT_CONFIG["correlation_window_hours"] * 3600,
        )
        graph.campaigns.add(seed["campaign_id"])

        assert await matcher_a.check_alert("a1") == seed["campaign_id"]
        await asyncio.gather(*list(shared_state.bg_tasks))
        await asyncio.sleep(0)
        first_lookup_count = graph.materialized_lookup_count
        assert await matcher_b.check_alert("a1") == seed["campaign_id"]
        await asyncio.gather(*list(shared_state.bg_tasks))
        await asyncio.sleep(0)

        assert first_lookup_count == 1
        assert graph.materialized_lookup_count == first_lookup_count

    run(scenario())


def test_no_negative_cache_authority():
    async def scenario():
        event = _event("a1")
        shared_state = CampaignAsyncState()
        matcher, _repo, graph = _matcher(
            [event],
            background=True,
            async_state=shared_state,
        )
        seed = campaign_seed_candidate(
            event,
            DEFAULT_CONFIG["correlation_window_hours"] * 3600,
        )

        assert await matcher.check_alert("a1") is None
        await asyncio.gather(*list(shared_state.bg_tasks))
        await asyncio.sleep(0)
        assert shared_state.materialized_campaign_id(seed["campaign_id"]) is None

        graph.campaigns.add(seed["campaign_id"])
        assert await matcher.check_alert("a1") == seed["campaign_id"]

        assert shared_state.materialized_campaign_id(seed["campaign_id"]) == seed["campaign_id"]
        assert graph.materialized_lookup_count == 2

    run(scenario())


def test_rule_identity_cache_key_matches_materialization_identity_for_supported_path():
    events = [_event("a1", minutes=0), _event("a2", minutes=1)]
    engine = CampaignCorrelationEngine(DEFAULT_CONFIG)
    seed = campaign_seed_candidate(
        events[0],
        DEFAULT_CONFIG["correlation_window_hours"] * 3600,
        rule_type="shared_entity",
    )

    campaigns = engine.correlate(events)

    assert campaigns
    assert campaigns[0].trigger_rule == "shared_entity"
    assert campaigns[0].campaign_id == seed["campaign_id"]


def test_materialized_cache_hit_unit_timing_under_budget_without_age_lookup():
    async def scenario():
        event = _event("a1")
        shared_state = CampaignAsyncState()
        seed = campaign_seed_candidate(
            event,
            DEFAULT_CONFIG["correlation_window_hours"] * 3600,
        )
        shared_state.mark_materialized(seed["campaign_id"])
        matcher, _repo, graph = _matcher(
            [event],
            background=True,
            async_state=shared_state,
        )

        result = await matcher.check_alert_timed("a1")
        await asyncio.gather(*list(shared_state.bg_tasks))
        await asyncio.sleep(0)

        assert result["campaign_id"] == seed["campaign_id"]
        assert result["measurement_mode"] == "mock/unit"
        assert result["elapsed_ms"] < 5.0
        assert graph.materialized_lookup_count == 0

    run(scenario())


def test_task_retention_is_shared_process_lifetime_not_instance_lifetime():
    async def scenario():
        events = [_event("a1", user_id="user-1"), _event("a2", user_id="user-1", minutes=1)]
        shared_state = CampaignAsyncState()
        matcher, repo, _graph = _matcher(events, background=True, async_state=shared_state)
        repo.release_materialize = asyncio.Event()

        assert await matcher.check_alert("a1") is None
        await repo.materialize_started.wait()
        del matcher

        assert len(shared_state.bg_tasks) == 1
        repo.release_materialize.set()
        await asyncio.gather(*list(shared_state.bg_tasks))
        await asyncio.sleep(0)

        assert shared_state.bg_tasks == set()
        assert shared_state.pending_seeds == set()

    run(scenario())


def test_pending_state_cleanup_after_success_and_failure_across_matchers(caplog):
    async def success_scenario():
        events = [_event("a1", user_id="user-1"), _event("a2", user_id="user-1", minutes=1)]
        graph = Phase3Graph()
        repo = Phase3Repo(events, graph=graph)
        shared_state = CampaignAsyncState()
        matcher_a, _repo, _graph = _matcher(
            events,
            background=True,
            graph=graph,
            repo=repo,
            async_state=shared_state,
        )
        repo.release_materialize = asyncio.Event()

        await matcher_a.check_alert("a1")
        await repo.materialize_started.wait()
        repo.release_materialize.set()
        await asyncio.gather(*list(shared_state.bg_tasks))
        await asyncio.sleep(0)

        matcher_b, _repo, _graph = _matcher(
            events,
            background=True,
            graph=graph,
            repo=repo,
            async_state=shared_state,
        )
        assert matcher_b._pending_seeds == set()
        assert matcher_b._pending_seed_campaigns == {}

    async def failure_scenario():
        events = [_event("b1", user_id="user-2"), _event("b2", user_id="user-2", minutes=1)]
        graph = Phase3Graph()
        repo = Phase3Repo(events, graph=graph)
        repo.fail_materialize = True
        shared_state = CampaignAsyncState()
        matcher_a, _repo, _graph = _matcher(
            events,
            background=True,
            graph=graph,
            repo=repo,
            async_state=shared_state,
        )

        await matcher_a.check_alert("b1")
        await asyncio.gather(*list(shared_state.bg_tasks))
        await asyncio.sleep(0)

        matcher_b, _repo, _graph = _matcher(
            events,
            background=True,
            graph=graph,
            repo=repo,
            async_state=shared_state,
        )
        assert matcher_b._pending_seeds == set()
        assert matcher_b._pending_seed_campaigns == {}

    caplog.set_level(logging.WARNING)
    run(success_scenario())
    run(failure_scenario())
    assert "Background campaign materialization failed" in caplog.text


def test_hot_path_returns_before_background_materialization_completes():
    async def scenario():
        matcher, repo, _graph = _matcher(
            [_event("a1", minutes=0), _event("a2", minutes=1)],
            background=True,
        )
        repo.release_materialize = asyncio.Event()

        started = time.perf_counter()
        result = await matcher.check_alert("a2")
        elapsed_ms = (time.perf_counter() - started) * 1000
        await repo.materialize_started.wait()

        assert result is None
        assert elapsed_ms < 5.0
        assert len(matcher._bg_tasks) == 1
        repo.release_materialize.set()
        await asyncio.gather(*list(matcher._bg_tasks))

    run(scenario())


def test_background_phase_does_not_create_continues_or_belongs_to_edges():
    async def scenario():
        events = [_event("a1", minutes=0), _event("a2", minutes=1)]
        matcher, repo, graph = _matcher(events, background=True)

        await matcher.check_alert("a2")
        await asyncio.gather(*list(matcher._bg_tasks))

        all_text = "\n".join(graph.queries)
        assert "CONTINUES" not in all_text
        assert "BELONGS_TO" not in all_text
        assert all(edge[1] for edge in repo.edges)

    run(scenario())
