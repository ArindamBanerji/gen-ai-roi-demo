"""SS-12 campaign graph outage contracts."""

from datetime import datetime

import pytest

from app.domains.soc.campaigns import (
    CampaignCorrelationEngine,
    CampaignDataUnavailableError,
    CampaignAsyncState,
    CampaignMatcher,
    CampaignRepository,
)


CONFIG = {
    "correlation_window_hours": 24,
    "temporal_window_minutes": 60,
    "min_alerts_for_campaign": 2,
    "max_campaign_age_days": 30,
}


class BrokenGraph:
    async def run_query(self, *_args, **_kwargs):
        raise RuntimeError("graph unavailable")


def repo() -> CampaignRepository:
    return CampaignRepository(BrokenGraph())


@pytest.mark.asyncio
async def test_fetch_all_events_graph_failure() -> None:
    assert await repo().fetch_all_events() is None


@pytest.mark.asyncio
async def test_fetch_recent_events_graph_failure() -> None:
    assert await repo().fetch_recent_events() is None


@pytest.mark.asyncio
async def test_fetch_single_alert_graph_failure() -> None:
    with pytest.raises(CampaignDataUnavailableError):
        await repo().fetch_single_alert_event("alert-1")


@pytest.mark.asyncio
async def test_get_campaigns_graph_failure() -> None:
    assert await repo().get_campaigns() is None


@pytest.mark.asyncio
async def test_get_campaign_detail_graph_failure() -> None:
    with pytest.raises(CampaignDataUnavailableError):
        await repo().get_campaign_detail("campaign-1")


@pytest.mark.asyncio
async def test_campaigns_exist_graph_failure() -> None:
    assert await repo().campaigns_exist() is None


@pytest.mark.asyncio
async def test_check_alert_impl_graph_failure() -> None:
    matcher = CampaignMatcher(
        BrokenGraph(), CONFIG, CampaignCorrelationEngine(CONFIG), repo(), background=False
    )
    assert await matcher._check_alert_impl("alert-1") is None
    assert matcher.last_check_available is False
    assert matcher.last_degraded is True


@pytest.mark.asyncio
async def test_check_materialized_graph_failure() -> None:
    class Repo:
        async def fetch_single_alert_event(self, *_args, **_kwargs):
            return {
                "alert_id": "alert-1",
                "category": "credential_access",
                "source_entity_id": "user-1",
                "ts": datetime(2026, 1, 1),
            }

    matcher = CampaignMatcher(
        BrokenGraph(), CONFIG, CampaignCorrelationEngine(CONFIG), Repo(), background=True
    )
    assert await matcher._check_alert_impl("alert-1") is None
    assert matcher.last_materialization_available is False


@pytest.mark.asyncio
async def test_persist_seed_graph_failure() -> None:
    campaign_repo = repo()
    campaign_repo._has_transactional_graph_client = lambda: True

    async def fail_transaction(*_args, **_kwargs):
        raise RuntimeError("write unavailable")

    campaign_repo._run_campaign_locked_transaction = fail_transaction
    event = {
        "alert_id": "alert-1",
        "category": "credential_access",
        "source_entity_id": "user-1",
        "ts": datetime(2026, 1, 1),
    }
    result = await campaign_repo.persist_campaign_seed(event)
    assert result is not None
    assert result["persisted"] is False


@pytest.mark.asyncio
async def test_materialize_background_graph_failure() -> None:
    class Matcher(CampaignMatcher):
        async def _materialize_alert(self, *_args, **_kwargs):
            raise RuntimeError("write unavailable")

    matcher = Matcher(
        BrokenGraph(), CONFIG, CampaignCorrelationEngine(CONFIG), repo(), background=True,
        async_state=CampaignAsyncState(),
    )
    assert await matcher._materialize_in_background("alert-1", "seed-1") is None
    assert matcher.async_state.materialization_failed_count == 1
    assert "seed-1" not in matcher.async_state.pending_seeds
