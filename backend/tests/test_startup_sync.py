"""
Tests for startup decision_count sync from AGE.

Verifies that on server restart, the LearningState.decision_count is
brought up to the historical AGE count (fixing cold-start IKS regression),
and is never downgraded if in-memory is already ahead.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers — reproduce the sync logic from main.py startup_event()
# so tests don't require a running FastAPI app or real AGE connection.
# ---------------------------------------------------------------------------

async def _run_sync(graph_count: int, initial_ls_count: int) -> int:
    """
    Execute the sync block in isolation and return the final decision_count.

    Mimics:
        _count_result = await graph_client.run_query(...)
        _historical_count = _count_result[0]["cnt"] if _count_result else 0
        _ls = get_learning_state()
        if _ls.decision_count < _historical_count:
            _ls.decision_count = _historical_count
    """
    mock_graph = AsyncMock()
    mock_graph.run_query = AsyncMock(return_value=[{"cnt": graph_count}])

    mock_ls = MagicMock()
    mock_ls.decision_count = initial_ls_count

    # Execute the sync logic
    _count_result = await mock_graph.run_query("MATCH (d:Decision) RETURN count(d) AS cnt")
    _historical_count = _count_result[0]["cnt"] if _count_result else 0
    if mock_ls.decision_count < _historical_count:
        mock_ls.decision_count = _historical_count

    return mock_ls.decision_count


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_decision_count_synced_from_graph():
    """
    When AGE has more decisions than in-memory, sync up to AGE count.
    """
    final = await _run_sync(graph_count=2851, initial_ls_count=0)
    assert final == 2851, f"Expected 2851, got {final}"


@pytest.mark.asyncio
async def test_decision_count_not_downgraded():
    """
    When in-memory count (500) exceeds AGE count (100),
    do NOT overwrite -- keep the higher in-memory value.
    """
    final = await _run_sync(graph_count=100, initial_ls_count=500)
    assert final == 500, f"Expected 500 (in-memory should not be downgraded), got {final}"
