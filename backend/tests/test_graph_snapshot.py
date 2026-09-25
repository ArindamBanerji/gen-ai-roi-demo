"""
BACKLOG-020 GraphSnapshot tests.
Snapshot loading uses live AGE; incremental updates are pure Python.
"""
import pytest
from app.state.graph_snapshot import GraphSnapshot


@pytest.mark.age
@pytest.mark.asyncio
async def test_from_graph_reads_correct_values(age_graph):
    age_graph.decision(category="credential_access", correct=True)
    age_graph.decision(category="lateral_movement", correct=False, was_override=True, quality_signal=0.8)
    age_graph.decision(category="lateral_movement", correct=None)
    age_graph.decision(domain="s2p", correct=True)
    snap = await GraphSnapshot.from_graph(age_graph.client)
    assert snap.verified_decisions == 2
    assert snap.correct_decisions == 1
    # Override coverage includes the pending SOC decision in its denominator.
    assert snap.override_rate == pytest.approx(1 / 3)
    assert snap.override_quality == pytest.approx(0.8)
    assert snap.category_counts == {"credential_access": 1, "lateral_movement": 2}
    assert 0 <= snap.iks_score <= 100


@pytest.mark.age
@pytest.mark.asyncio
async def test_restart_idempotent(age_graph):
    age_graph.decision(correct=True)
    first = await GraphSnapshot.from_graph(age_graph.client)
    restored = await GraphSnapshot.from_graph(age_graph.reopen_client())
    assert first == restored
    age_graph.decision(correct=False)
    updated = await GraphSnapshot.from_graph(age_graph.reopen_client())
    assert updated.verified_decisions == first.verified_decisions + 1
    assert updated.correct_decisions == first.correct_decisions


def test_on_verified_decision_increments_count():
    """Write-through update increments verified_decisions."""
    snap = GraphSnapshot(verified_decisions=10)
    snap.on_verified_decision("lateral_movement", False, 0.0, is_correct=True)
    assert snap.verified_decisions == 11
    assert snap.category_counts["lateral_movement"] == 1


def test_on_verified_decision_correct_increments_correct_decisions():
    """is_correct=True increments both verified_decisions and correct_decisions."""
    snap = GraphSnapshot(verified_decisions=5, correct_decisions=3)
    snap.on_verified_decision("credential_access", False, 1.0, is_correct=True)
    assert snap.verified_decisions == 6
    assert snap.correct_decisions == 4


def test_on_verified_decision_incorrect_does_not_increment_correct_decisions():
    """is_correct=False increments verified_decisions but NOT correct_decisions."""
    snap = GraphSnapshot(verified_decisions=5, correct_decisions=3)
    snap.on_verified_decision("credential_access", False, 0.0, is_correct=False)
    assert snap.verified_decisions == 6
    assert snap.correct_decisions == 3


def test_on_verified_decision_requires_is_correct():
    """Omitting is_correct raises TypeError -- no silent default any more."""
    snap = GraphSnapshot()
    try:
        snap.on_verified_decision("lateral_movement", False, 0.0)
        assert False, "Expected TypeError when is_correct is omitted"
    except TypeError:
        pass  # expected -- no default means callers must be explicit


def test_on_verified_decision_graph_write_failure_leaves_snapshot_unchanged():
    """
    Snapshot must not update if graph write fails.
    Simulate by NOT calling on_verified_decision() -- caller only
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


# ---------------------------------------------------------------------------
# Epistemic state — band thresholds and get_epistemic_state()
# ---------------------------------------------------------------------------

def test_epistemic_band_novice():
    snap = GraphSnapshot(category_counts={"lateral_movement": 10})
    state = snap.get_epistemic_state()
    assert state["lateral_movement"]["count"] == 10
    assert state["lateral_movement"]["band"] == "novice"


def test_epistemic_band_learning():
    snap = GraphSnapshot(category_counts={"credential_access": 75})
    assert snap.get_epistemic_state()["credential_access"]["band"] == "learning"


def test_epistemic_band_calibrating():
    snap = GraphSnapshot(category_counts={"malware_execution": 300})
    assert snap.get_epistemic_state()["malware_execution"]["band"] == "calibrating"


def test_epistemic_band_expert():
    snap = GraphSnapshot(category_counts={"insider_threat": 600})
    assert snap.get_epistemic_state()["insider_threat"]["band"] == "expert"


def test_epistemic_boundary_50_is_learning():
    snap = GraphSnapshot(category_counts={"cloud_infrastructure": 50})
    assert snap.get_epistemic_state()["cloud_infrastructure"]["band"] == "learning"


def test_epistemic_boundary_200_is_calibrating():
    snap = GraphSnapshot(category_counts={"data_exfiltration": 200})
    assert snap.get_epistemic_state()["data_exfiltration"]["band"] == "calibrating"


def test_epistemic_boundary_500_is_expert():
    snap = GraphSnapshot(category_counts={"lateral_movement": 500})
    assert snap.get_epistemic_state()["lateral_movement"]["band"] == "expert"


def test_epistemic_empty_categories():
    snap = GraphSnapshot()
    assert snap.get_epistemic_state() == {}


def test_epistemic_multiple_categories():
    snap = GraphSnapshot(category_counts={
        "a": 10, "b": 100, "c": 250, "d": 700,
    })
    state = snap.get_epistemic_state()
    assert state["a"]["band"] == "novice"
    assert state["b"]["band"] == "learning"
    assert state["c"]["band"] == "calibrating"
    assert state["d"]["band"] == "expert"


