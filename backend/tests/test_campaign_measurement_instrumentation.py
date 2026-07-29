import pytest

from ci_platform.graph.age_client import AGEClient


class FakeOutcomeStatsClient(AGEClient):
    def __init__(self):
        pass

    async def run_query(self, query, parameters=None):
        assert "d.was_override = true" in query
        assert "THEN d.quality_signal ELSE null" in query
        return [{"total": 4, "overrides": 1, "avg_quality": 1.0}]


@pytest.mark.asyncio
async def test_compute_outcome_stats_reads_written_measurement_fields():
    stats = await FakeOutcomeStatsClient().compute_outcome_stats()

    assert stats == {"override_rate": 0.25, "override_quality": 1.0}
