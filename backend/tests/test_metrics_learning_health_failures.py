import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_metrics_evolution_failure_is_503_and_empty_is_valid():
    from app.routers.metrics import get_evolution_events

    with patch("app.routers.metrics.neo4j_client") as client:
        client.run_query = AsyncMock(side_effect=RuntimeError("AGE down"))
        with pytest.raises(HTTPException) as error:
            await get_evolution_events()
        assert error.value.status_code == 503

        client.run_query = AsyncMock(return_value=[])
        result = await get_evolution_events()
        assert result["events"] == []


@pytest.mark.asyncio
async def test_metrics_weekly_trends_failure_is_503_and_empty_is_valid():
    from app.routers.metrics import get_weekly_trends

    with patch("app.routers.metrics.neo4j_client") as client:
        client.run_query = AsyncMock(side_effect=RuntimeError("AGE down"))
        with pytest.raises(HTTPException) as error:
            await get_weekly_trends()
        assert error.value.status_code == 503

        client.run_query = AsyncMock(return_value=[])
        result = await get_weekly_trends()
        assert result["data"] == []


@pytest.mark.asyncio
async def test_metrics_decision_economics_failure_is_503_and_empty_is_valid():
    from app.routers.metrics import get_decision_economics

    with patch("app.routers.metrics.neo4j_client") as client:
        client.run_query = AsyncMock(side_effect=RuntimeError("AGE down"))
        with pytest.raises(HTTPException) as error:
            await get_decision_economics()
        assert error.value.status_code == 503

        client.run_query = AsyncMock(return_value=[])
        result = await get_decision_economics()
        assert result["decisions_made"] == 0


@pytest.mark.asyncio
async def test_metrics_operational_failure_is_503_and_empty_is_valid():
    from app.routers.metrics import get_operational_metrics

    with patch("app.routers.metrics.neo4j_client") as client:
        client.run_query = AsyncMock(side_effect=RuntimeError("AGE down"))
        with pytest.raises(HTTPException) as error:
            await get_operational_metrics()
        assert error.value.status_code == 503

        client.run_query = AsyncMock(
            side_effect=[
                [{"avg_mttd_seconds": None, "sample_size": 0}],
                [{"avg_mttr_seconds": None, "sample_size": 0}],
                [{"total": 0, "fp_count": 0}],
            ]
        )
        result = await get_operational_metrics()
        assert result["mttd"]["sample_size"] == 0
        assert result["mttr"]["sample_size"] == 0
        assert result["fp_rate"]["total_decisions"] == 0


@pytest.mark.asyncio
async def test_learning_health_red_days_failure_raises_and_empty_is_zero():
    from app.services.learning_health import LearningHealthMonitor

    client = AsyncMock()
    client.run_query = AsyncMock(side_effect=RuntimeError("AGE down"))
    with pytest.raises(RuntimeError, match="RED-day"):
        await LearningHealthMonitor._count_red_days(client)

    client.run_query = AsyncMock(return_value=[])
    assert await LearningHealthMonitor._count_red_days(client) == 0


@pytest.mark.asyncio
async def test_learning_health_conservation_failure_raises_and_empty_is_valid():
    from app.services.learning_health import _query_soc_verified_conservation_stats

    client = AsyncMock()
    client.run_query = AsyncMock(side_effect=RuntimeError("AGE down"))
    with pytest.raises(RuntimeError, match="conservation"):
        await _query_soc_verified_conservation_stats(client)

    client.run_query = AsyncMock(return_value=[])
    result = await _query_soc_verified_conservation_stats(client)
    assert result["verified_decisions"] == 0


@pytest.mark.asyncio
async def test_learning_health_category_baseline_failure_raises_and_empty_is_valid():
    from app.services.learning_health import compute_category_baseline

    client = AsyncMock()
    client.run_query = AsyncMock(side_effect=RuntimeError("AGE down"))
    with pytest.raises(RuntimeError, match="category baseline"):
        await compute_category_baseline(client)

    client.run_query = AsyncMock(return_value=[])
    assert await compute_category_baseline(client) == {}


@pytest.mark.asyncio
async def test_learning_health_precision_failure_raises_and_empty_is_valid():
    from app.services.learning_health import compute_analyst_precision

    client = AsyncMock()
    client.run_query = AsyncMock(side_effect=RuntimeError("AGE down"))
    with pytest.raises(RuntimeError, match="analyst precision"):
        await compute_analyst_precision(client)

    client.run_query = AsyncMock(return_value=[])
    assert await compute_analyst_precision(client) == {}
