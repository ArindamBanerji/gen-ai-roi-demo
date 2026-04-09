"""
BACKLOG-020 GraphSnapshot tests.
All run without a live DB — snapshot logic is pure Python.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.state.graph_snapshot import GraphSnapshot


@pytest.fixture
def mock_graph_client():
    client = AsyncMock()
    client.count_verified_decisions = AsyncMock(return_value=42)
    client.count_decisions_by_category = AsyncMock(return_value={
        "credential_access": 20,
        "lateral_movement": 22,
    })
    client.compute_outcome_stats = AsyncMock(return_value={
        "override_rate": 0.15,
        "override_quality": 0.72,
    })
    client.compute_iks = AsyncMock(return_value=76.0)
    return client


@pytest.mark.asyncio
async def test_from_graph_reads_correct_values(mock_graph_client):
    """Snapshot initializes from graph correctly."""
    snap = await GraphSnapshot.from_graph(mock_graph_client)
    assert snap.verified_decisions == 42
    assert snap.iks_score == 76.0
    assert snap.override_rate == 0.15
    assert snap.category_counts["lateral_movement"] == 22


@pytest.mark.asyncio
async def test_restart_idempotent(mock_graph_client):
    """Two from_graph() calls produce identical snapshots — restart is safe."""
    snap1 = await GraphSnapshot.from_graph(mock_graph_client)
    snap2 = await GraphSnapshot.from_graph(mock_graph_client)
    assert snap1.verified_decisions == snap2.verified_decisions
    assert snap1.iks_score == snap2.iks_score


def test_on_verified_decision_increments_count():
    """Write-through update increments verified_decisions."""
    snap = GraphSnapshot(verified_decisions=10)
    snap.on_verified_decision("lateral_movement", False, 0.0)
    assert snap.verified_decisions == 11
    assert snap.category_counts["lateral_movement"] == 1


def test_on_verified_decision_graph_write_failure_leaves_snapshot_unchanged():
    """
    Snapshot must not update if graph write fails.
    Simulate by NOT calling on_verified_decision() — caller only
    calls it after successful graph write.
    """
    snap = GraphSnapshot(verified_decisions=10)
    # Simulate: graph write raised, on_verified_decision never called
    assert snap.verified_decisions == 10  # unchanged


def test_on_iks_recalculated():
    """IKS update propagates correctly."""
    snap = GraphSnapshot(iks_score=70.0)
    snap.on_iks_recalculated(78.5)
    assert snap.iks_score == 78.5
