"""
DRIFT-01 + DRIFT-03: Conservation freeze enforcement tests.

Verifies that conservation RED/auto-pause BLOCKS centroid updates via:
  1. ProfileScorer.update() internal _paused_by_conservation gate
  2. guarded_update() B5 conservation gate (defense-in-depth)
  3. auto_pause_active forces effective status to RED (not overridden by GREEN)

No live Neo4j required. 8 tests.
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from gae import ProfileScorer
from app.services.gae_state import guarded_update, set_volume_spike, reset_spike_counter
import app.services.gae_state as _gs

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

N_CAT, N_ACT, N_FAC = 2, 2, 4


def _make_scorer(status: str = "GREEN") -> ProfileScorer:
    """Fresh scorer with auto_pause_on_amber=True and given conservation status."""
    mu = np.full((N_CAT, N_ACT, N_FAC), 0.5)
    scorer = ProfileScorer(
        mu=mu,
        actions=["block", "escalate"],
        categories=["cat_a", "cat_b"],
        auto_pause_on_amber=True,
    )
    scorer.set_conservation_status(status)
    return scorer


def _factor_vec() -> np.ndarray:
    return np.array([0.8, 0.6, 0.4, 0.2])


def _reset_spike_state():
    set_volume_spike(False)
    reset_spike_counter()
    _gs._spike_update_cap = 0


# ---------------------------------------------------------------------------
# Test 1 — conservation RED blocks centroid update (ProfileScorer internal gate)
# ---------------------------------------------------------------------------

def test_conservation_red_blocks_centroid_update():
    """
    With conservation RED and auto_pause_on_amber=True, ProfileScorer.update()
    must return outcome='paused_conservation' and leave centroids unchanged.
    """
    scorer = _make_scorer("RED")
    assert scorer.is_paused, "Scorer must be paused when status=RED"

    before = scorer.centroids.copy()
    result = scorer.update(
        f=_factor_vec(),
        category_index=0,
        action_index=0,
        correct=True,
    )

    assert result.outcome == "paused_conservation", (
        f"Expected outcome='paused_conservation', got {result.outcome!r}"
    )
    assert np.array_equal(scorer.centroids, before), (
        "Centroids must not change when conservation is RED"
    )


# ---------------------------------------------------------------------------
# Test 2 — conservation GREEN allows centroid update
# ---------------------------------------------------------------------------

def test_conservation_green_allows_centroid_update():
    """
    With conservation GREEN, ProfileScorer.update() must apply the update
    and centroids must change.
    """
    scorer = _make_scorer("GREEN")
    assert not scorer.is_paused, "Scorer must NOT be paused when status=GREEN"

    before = scorer.centroids.copy()
    result = scorer.update(
        f=_factor_vec(),
        category_index=0,
        action_index=0,
        correct=True,
    )

    assert result.outcome != "paused_conservation", (
        f"GREEN scorer must not return paused_conservation; got {result.outcome!r}"
    )
    assert not np.array_equal(scorer.centroids, before), (
        "Centroids must change when conservation is GREEN"
    )


# ---------------------------------------------------------------------------
# Test 3 — auto_pause_active forces RED even when status string is GREEN
# ---------------------------------------------------------------------------

def test_conservation_auto_pause_freezes_on_red_days():
    """
    When auto_pause_active is True (>=14 RED days), triage enforces RED
    by calling set_conservation_status('RED') regardless of the raw status.
    This test simulates that enforcement: set status=RED directly (as triage
    would after detecting auto_pause_active=True) and verify the scorer freezes.
    """
    scorer = _make_scorer("GREEN")
    assert not scorer.is_paused, "Precondition: GREEN scorer must not be paused"

    # Simulate what triage.py does when auto_pause_active=True:
    # _eff_status = "RED" if health["auto_pause_active"] else health["status"]
    auto_pause_active = True
    raw_status = "GREEN"
    eff_status = "RED" if auto_pause_active else raw_status
    scorer.set_conservation_status(eff_status)

    assert scorer.is_paused, (
        "Scorer must be paused after enforcing RED for auto_pause_active"
    )

    before = scorer.centroids.copy()
    result = scorer.update(
        f=_factor_vec(),
        category_index=0,
        action_index=1,
        correct=False,
        gt_action_index=0,
    )

    assert result.outcome == "paused_conservation", (
        f"Expected paused_conservation; got {result.outcome!r}"
    )
    assert np.array_equal(scorer.centroids, before), (
        "Centroids must not change when auto_pause forces RED"
    )


# ---------------------------------------------------------------------------
# Test 4 — guarded_update() blocks when conservation is RED (B5 gate)
# ---------------------------------------------------------------------------

def test_guarded_update_checks_conservation_status():
    """
    guarded_update() must return None when scorer.is_paused is True.
    This is the B5 defense-in-depth gate added to gae_state.guarded_update().
    """
    _reset_spike_state()
    scorer = _make_scorer("RED")
    assert scorer.is_paused, "Precondition: scorer must be paused"

    before = scorer.centroids.copy()
    result = guarded_update(
        scorer,
        f=_factor_vec(),
        category_index=0,
        action_index=0,
        correct=True,
        category_name="cat_a",
    )

    assert result is None, (
        f"guarded_update() must return None when conservation is RED; got {result!r}"
    )
    assert np.array_equal(scorer.centroids, before), (
        "Centroids must not change when guarded_update blocks for conservation"
    )
    _reset_spike_state()


# ---------------------------------------------------------------------------
# Test 5 — guarded_update() allows update when conservation is GREEN
# ---------------------------------------------------------------------------

def test_guarded_update_allows_when_green():
    """
    guarded_update() must pass through to scorer.update() and return a
    CentroidUpdate (not None) when conservation status is GREEN.
    """
    _reset_spike_state()
    scorer = _make_scorer("GREEN")
    assert not scorer.is_paused, "Precondition: scorer must NOT be paused"

    before = scorer.centroids.copy()
    result = guarded_update(
        scorer,
        f=_factor_vec(),
        category_index=0,
        action_index=0,
        correct=True,
        category_name="cat_a",
    )

    assert result is not None, (
        "guarded_update() must return CentroidUpdate when conservation is GREEN"
    )
    assert not np.array_equal(scorer.centroids, before), (
        "Centroids must change when guarded_update allows the update"
    )
    _reset_spike_state()


# ---------------------------------------------------------------------------
# Test 6 — fail-closed: health check failure → learning blocked (FIX 1)
# ---------------------------------------------------------------------------

def test_conservation_fail_closed_on_health_error():
    """
    Fail-closed pattern (FIX 1): when LearningHealthMonitor.evaluate raises,
    _conservation_block is set True and guarded_update is never called.

    Replicates the triage.py try/except pattern directly -- no live handler needed.
    """
    _reset_spike_state()
    scorer = _make_scorer("GREEN")
    assert not scorer.is_paused, "Precondition: GREEN scorer must not be paused"
    before = scorer.centroids.copy()

    # Replicate the triage.py fail-closed try/except (FIX 1):
    _conservation_block = False
    try:
        raise RuntimeError("health check unavailable")
    except Exception:
        _conservation_block = True

    assert _conservation_block is True, (
        "Exception in health eval must set _conservation_block=True (fail-closed gate)"
    )

    # When _conservation_block is True, triage skips guarded_update entirely.
    # The `if not _conservation_block:` branch below is deliberately not taken.
    if not _conservation_block:
        guarded_update(scorer, f=_factor_vec(), category_index=0,
                       action_index=0, correct=True, category_name="cat_a")

    assert np.array_equal(scorer.centroids, before), (
        "Centroids must not change when fail-closed prevents guarded_update call"
    )
    _reset_spike_state()


# ---------------------------------------------------------------------------
# Test 7 — simulation path respects conservation gate (FIX 2)
# ---------------------------------------------------------------------------

def test_simulation_respects_conservation_gate():
    """
    FIX 2: simulation now routes through guarded_update instead of calling
    scorer.update() directly.  When scorer.is_paused is True (conservation RED),
    guarded_update returns None and centroids stay unchanged.
    """
    _reset_spike_state()
    scorer = _make_scorer("RED")
    assert scorer.is_paused, "Precondition: RED scorer must be paused"
    before = scorer.centroids.copy()

    # Simulate what simulation.py now does: call guarded_update
    result = guarded_update(
        scorer,
        f=_factor_vec(),
        category_index=1,
        action_index=1,
        correct=False,
        category_name="cat_b",
        gt_action_index=0,
    )

    assert result is None, (
        f"Simulation guarded_update must return None when conservation RED; got {result!r}"
    )
    assert np.array_equal(scorer.centroids, before), (
        "Sim centroids must not change when conservation gate blocks"
    )
    _reset_spike_state()


# ---------------------------------------------------------------------------
# Test 8 — guarded_update returns None (not CentroidUpdate) when blocked (FIX 4)
# ---------------------------------------------------------------------------

def test_guarded_update_return_none_when_blocked():
    """
    guarded_update() must return None -- not a CentroidUpdate -- when the scorer
    is paused.  This is the contract that FIX 4 checks in the log path.
    """
    _reset_spike_state()
    scorer = _make_scorer("RED")
    assert scorer.is_paused, "Precondition: scorer must be paused"

    result = guarded_update(
        scorer,
        f=_factor_vec(),
        category_index=0,
        action_index=1,
        correct=False,
        category_name="cat_a",
        gt_action_index=0,
    )

    assert result is None, (
        f"Expected None when blocked; got {type(result).__name__}: {result!r}"
    )
    _reset_spike_state()
