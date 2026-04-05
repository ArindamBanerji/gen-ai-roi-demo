"""
Block 9.4 — D7 Spike update cap tests.
Coupled to D3 — cap only enforced when volume spike is active.
No live Neo4j required.
"""
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.services.gae_state import (
    set_volume_spike,
    is_volume_spike_active,
    set_spike_cap,
    reset_spike_counter,
    increment_spike_counter,
    get_spike_cap_status,
    _spike_update_cap,
    _spike_update_count,
)
import app.services.gae_state as _gs


# ---------------------------------------------------------------------------
# Cleanup helper — always restore module state between tests
# ---------------------------------------------------------------------------

def _reset_all():
    set_volume_spike(False)
    reset_spike_counter()
    # Reset cap directly on the module to avoid leaked state
    _gs._spike_update_cap = 0


# ---------------------------------------------------------------------------
# Test 1 — no cap enforced when spike is NOT active
# ---------------------------------------------------------------------------

def test_no_cap_when_no_spike():
    """
    increment_spike_counter() returns True unconditionally when no spike.
    Call far more than any cap would allow — must always pass.
    """
    _reset_all()
    set_spike_cap(10)   # cap would be 15 if spike were active
    assert not is_volume_spike_active()

    for _ in range(100):
        assert increment_spike_counter() is True, (
            "Counter must always return True when spike is inactive"
        )

    _reset_all()


# ---------------------------------------------------------------------------
# Test 2 — cap set correctly from baseline
# ---------------------------------------------------------------------------

def test_cap_set_from_baseline():
    """set_spike_cap(baseline_daily) stores int(1.5 × baseline_daily)."""
    _reset_all()

    set_spike_cap(100.0)
    assert _gs._spike_update_cap == 150, (
        f"Expected cap=150 for baseline=100, got {_gs._spike_update_cap}"
    )

    set_spike_cap(47.3)
    assert _gs._spike_update_cap == int(1.5 * 47.3), (
        f"Expected cap={int(1.5 * 47.3)} for baseline=47.3, got {_gs._spike_update_cap}"
    )

    _reset_all()


# ---------------------------------------------------------------------------
# Test 3 — updates allowed below cap
# ---------------------------------------------------------------------------

def test_updates_allowed_below_cap():
    """With cap=5 and spike active, first 5 calls to increment return True."""
    _reset_all()
    set_spike_cap(3.0)          # cap = int(1.5 * 3) = 4
    cap = _gs._spike_update_cap
    assert cap == 4

    try:
        set_volume_spike(True)
        for i in range(cap):
            result = increment_spike_counter()
            assert result is True, f"Call {i+1} of {cap} should be allowed, got False"
        assert _gs._spike_update_count == cap
    finally:
        _reset_all()


# ---------------------------------------------------------------------------
# Test 4 — updates blocked at cap
# ---------------------------------------------------------------------------

def test_updates_blocked_at_cap():
    """
    Once _spike_update_count reaches cap, increment_spike_counter() returns False.
    Counter does NOT increment beyond cap.
    """
    _reset_all()
    set_spike_cap(2.0)          # cap = int(1.5 * 2) = 3
    cap = _gs._spike_update_cap
    assert cap == 3

    try:
        set_volume_spike(True)
        # Exhaust the cap
        for _ in range(cap):
            increment_spike_counter()

        assert _gs._spike_update_count == cap

        # Next call must be blocked
        result = increment_spike_counter()
        assert result is False, (
            f"Expected False when cap={cap} exhausted, got True"
        )
        # Counter must not have incremented past cap
        assert _gs._spike_update_count == cap, (
            f"Counter should stay at {cap} after cap reached, got {_gs._spike_update_count}"
        )

        # get_spike_cap_status should reflect cap_reached=True
        status = get_spike_cap_status()
        assert status["cap_reached"] is True
        assert status["spike_cap"]  == cap
        assert status["updates_this_cadence"] == cap
    finally:
        _reset_all()


# ---------------------------------------------------------------------------
# Test 5 — counter resets correctly
# ---------------------------------------------------------------------------

def test_counter_resets_correctly():
    """
    After exhausting the cap and calling reset_spike_counter(),
    increment_spike_counter() allows updates again.
    """
    _reset_all()
    set_spike_cap(2.0)          # cap = 3
    cap = _gs._spike_update_cap

    try:
        set_volume_spike(True)
        # Exhaust cap
        for _ in range(cap):
            increment_spike_counter()
        assert increment_spike_counter() is False   # cap hit

        # Reset the cadence counter
        reset_spike_counter()
        assert _gs._spike_update_count == 0, (
            f"Counter should be 0 after reset, got {_gs._spike_update_count}"
        )

        # Updates allowed again
        assert increment_spike_counter() is True, (
            "After reset, first increment should return True"
        )
    finally:
        _reset_all()
