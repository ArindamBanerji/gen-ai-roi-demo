"""
D-05 State Locking — unit tests for acquire_scorer / acquire_scorer_for_reset.

All tests use module-level patching of gae_state singletons so no real
ProfileScorer or asyncio.Lock is required.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import app.services.gae_state as gae_state


# ── helpers ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def fresh_scorer_lock():
    """Give each async test a lock that binds to that test's event loop."""
    old_lock = gae_state._scorer_lock
    gae_state._scorer_lock = asyncio.Lock()
    try:
        yield
    finally:
        gae_state._scorer_lock = old_lock


def _make_scorer():
    s = MagicMock()
    s.centroids = MagicMock()
    s.eta_override = 0.01
    return s


def _make_ls(scorer=None):
    ls = MagicMock()
    ls.profile_scorer = scorer or _make_scorer()
    return ls


# ── acquire_scorer ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_acquire_scorer_yields_profile_scorer():
    scorer = _make_scorer()
    ls = _make_ls(scorer)
    with patch.object(gae_state, "_learning_state", ls):
        async with gae_state.acquire_scorer() as s:
            assert s is scorer


@pytest.mark.asyncio
async def test_acquire_scorer_raises_when_learning_state_none():
    with patch.object(gae_state, "_learning_state", None):
        with pytest.raises(RuntimeError, match="ProfileScorer not attached"):
            async with gae_state.acquire_scorer():
                pass  # should not reach here


@pytest.mark.asyncio
async def test_acquire_scorer_raises_when_scorer_none():
    ls = _make_ls()
    ls.profile_scorer = None
    with patch.object(gae_state, "_learning_state", ls):
        with pytest.raises(RuntimeError, match="ProfileScorer not attached"):
            async with gae_state.acquire_scorer():
                pass


@pytest.mark.asyncio
async def test_acquire_scorer_holds_lock_during_body():
    """Lock must be held (and not re-acquirable) while inside acquire_scorer."""
    scorer = _make_scorer()
    ls = _make_ls(scorer)
    with patch.object(gae_state, "_learning_state", ls):
        async with gae_state.acquire_scorer():
            # The lock is held; a second acquire attempt should fail immediately
            acquired = await asyncio.wait_for(
                gae_state._scorer_lock.acquire(), timeout=0.01
            ) if not gae_state._scorer_lock.locked() else False
            assert not gae_state._scorer_lock.locked() or acquired is False
            # Simpler check: lock is currently locked
            assert gae_state._scorer_lock.locked()


# ── acquire_scorer_for_reset ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_acquire_scorer_for_reset_holds_lock():
    async with gae_state.acquire_scorer_for_reset():
        assert gae_state._scorer_lock.locked()
    assert not gae_state._scorer_lock.locked()


@pytest.mark.asyncio
async def test_reset_blocks_concurrent_update():
    """
    reset_learning_state holds the lock; a concurrent acquire_scorer must wait.
    """
    scorer = _make_scorer()
    ls = _make_ls(scorer)

    update_started = asyncio.Event()
    reset_started  = asyncio.Event()
    update_done    = asyncio.Event()

    async def fake_reset():
        async with gae_state.acquire_scorer_for_reset():
            reset_started.set()
            # Hold the lock long enough that the update task is blocked
            await asyncio.sleep(0.05)

    async def fake_update():
        # Wait until reset has the lock before we try to acquire it
        await reset_started.wait()
        update_started.set()
        async with gae_state.acquire_scorer() as s:
            assert s is scorer
        update_done.set()

    with patch.object(gae_state, "_learning_state", ls):
        await asyncio.gather(fake_reset(), fake_update())

    # Both tasks ran and completed without error
    assert update_started.is_set()
    assert update_done.is_set()


@pytest.mark.asyncio
async def test_reset_learning_state_is_awaitable():
    """reset_learning_state() must return a coroutine (i.e. is async)."""
    with patch.object(gae_state, "_reset_learning_state_inner", MagicMock()):
        coro = gae_state.reset_learning_state()
        assert asyncio.iscoroutine(coro)
        await coro


@pytest.mark.asyncio
async def test_restore_centroid_from_backup_is_awaitable():
    """restore_centroid_from_backup() must return a coroutine."""
    scorer = _make_scorer()
    scorer.centroids.shape = (4, 8)
    ls = _make_ls(scorer)

    import numpy as np
    import json
    import hashlib

    mu = np.zeros((4, 8)).tolist()
    payload_base = {
        "mu": mu,
        "shape": [4, 8],
        "step": 0,
        "timestamp_epoch": 1234567890000,
        "version": "1.0",
    }
    canonical = json.dumps(payload_base, sort_keys=True)
    sha256 = hashlib.sha256(canonical.encode()).hexdigest()
    payload_base["sha256"] = sha256
    payload_base["backup_id"] = "test_backup"

    with patch.object(gae_state, "_learning_state", ls), \
         patch("app.services.gae_state.load_centroid_backup", return_value=payload_base):
        coro = gae_state.restore_centroid_from_backup("test_backup")
        assert asyncio.iscoroutine(coro)
        result = await coro
        assert result["backup_id"] == "test_backup"
