"""Regression tests for campaign graph outages."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock
import pytest

from app.domains.soc.campaigns import (
    CampaignCorrelationEngine,
    CampaignDataUnavailableError,
    CampaignMatcher,
    CampaignRepository,
)


CONFIG = {
    "correlation_window_hours": 24,
    "temporal_window_minutes": 60,
    "min_alerts_for_campaign": 2,
    "max_campaign_age_days": 30,
}


def run(awaitable):
    return asyncio.run(awaitable)


def failing_repo():
    graph = AsyncMock()
    graph.run_query.side_effect = RuntimeError("graph unavailable")
    return graph, CampaignRepository(graph)


def test_event_reads_return_unavailable_instead_of_empty_data():
    graph, repo = failing_repo()
    assert run(repo.fetch_all_events()) is None
    assert run(repo.fetch_recent_events()) is None
    try:
        run(repo.fetch_single_alert_event("a-1"))
    except CampaignDataUnavailableError:
        pass
    else:
        raise AssertionError("single-alert outage must be distinguishable from not found")


def test_campaign_reads_and_existence_return_unavailable():
    graph, repo = failing_repo()
    assert run(repo.get_campaigns()) is None
    try:
        run(repo.get_campaign_detail("c-1"))
    except CampaignDataUnavailableError:
        pass
    else:
        raise AssertionError("detail outage must be distinguishable from not found")
    assert run(repo.campaigns_exist()) is None


def test_persist_seed_reports_failed_write():
    graph, repo = failing_repo()
    repo._has_transactional_graph_client = lambda: True
    async def failed_transaction(*_args, **_kwargs):
        raise RuntimeError("write unavailable")
    repo._run_campaign_locked_transaction = failed_transaction
    event = {
        "alert_id": "a-1", "category": "credential_access",
        "source_entity_id": "user-1", "ts": datetime(2026, 1, 1),
    }
    result = run(repo.persist_campaign_seed(event))
    assert result is not None
    assert result["persisted"] is False
    assert result["status"] == "failed"


def test_matcher_marks_single_alert_outage_degraded():
    graph, repo = failing_repo()
    matcher = CampaignMatcher(
        graph, CONFIG, CampaignCorrelationEngine(CONFIG), repo, background=False,
    )
    assert run(matcher.check_alert("a-1")) is None
    assert matcher.last_degraded is True
    timed = run(matcher.check_alert_timed("a-1"))
    assert timed["degraded"] is True


def test_matcher_marks_materialized_lookup_outage_degraded():
    class Repo:
        async def fetch_single_alert_event(self, *_args, **_kwargs):
            return {
                "alert_id": "a-1", "category": "credential_access",
                "source_entity_id": "u-1", "ts": datetime(2026, 1, 1),
            }

    graph = AsyncMock()
    graph.run_query.side_effect = RuntimeError("graph unavailable")
    matcher = CampaignMatcher(
        graph, CONFIG, CampaignCorrelationEngine(CONFIG), Repo(), background=True,
    )
    assert run(matcher.check_alert("a-1")) is None
    assert matcher.last_degraded is True


def test_materialization_recent_history_outage_is_degraded():
    class Repo:
        async def fetch_recent_events(self, *_args, **_kwargs):
            return None

    matcher = CampaignMatcher(
        None, CONFIG, CampaignCorrelationEngine(CONFIG), Repo(), background=False,
    )
    event = {"alert_id": "a-1", "category": "credential_access", "source_entity_id": "u-1"}
    assert run(matcher._materialize_alert("a-1", event)) is None
    assert matcher.last_degraded is True


def test_background_materialization_failure_logs_and_clears_pending(caplog):
    class Matcher(CampaignMatcher):
        async def _materialize_alert(self, *_args, **_kwargs):
            raise RuntimeError("write unavailable")

    matcher = Matcher(
        None, CONFIG, CampaignCorrelationEngine(CONFIG), object(), background=True,
    )
    assert run(matcher._materialize_in_background("a-1", "seed-1")) is None
    assert "Background campaign materialization failed" in caplog.text
    assert "seed-1" not in matcher.async_state.pending_seeds


def test_campaign_list_endpoint_uses_typed_defaults_on_outage(monkeypatch):
    from app.domains.soc import campaigns as campaigns_module
    from app.routers.soc import get_campaigns

    class Repo:
        def __init__(self, _graph):
            pass

        async def get_campaigns(self, **_kwargs):
            return None

    monkeypatch.setattr(campaigns_module, "CampaignRepository", Repo)
    body = run(get_campaigns())
    assert body["campaigns"] == []
    assert body["total"] == 0
    assert body["active_campaigns"] == 0
    assert body["data_available"] is False
    assert body["degraded"] is True


def test_campaign_detail_endpoint_distinguishes_outage_from_missing(monkeypatch):
    from app.domains.soc import campaigns as campaigns_module
    from app.routers.soc import get_campaign_detail

    class Repo:
        def __init__(self, _graph):
            pass

        async def get_campaign_detail(self, _campaign_id):
            raise CampaignDataUnavailableError("graph unavailable")

    monkeypatch.setattr(campaigns_module, "CampaignRepository", Repo)
    with pytest.raises(Exception) as raised:
        run(get_campaign_detail("c-1"))
    assert getattr(raised.value, "status_code", None) == 503
