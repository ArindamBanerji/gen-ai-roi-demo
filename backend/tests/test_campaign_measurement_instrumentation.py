import pytest


@pytest.mark.age
@pytest.mark.asyncio
async def test_compute_outcome_stats_reads_written_measurement_fields(age_graph):
    for index in range(4):
        age_graph.decision(correct=True, was_override=index == 0,
                           quality_signal=1.0 if index == 0 else 0.0)
    stats = await age_graph.reopen_client().compute_outcome_stats()
    assert stats == {"override_rate": 0.25, "override_quality": 1.0}
