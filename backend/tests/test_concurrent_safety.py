"""
Concurrent write safety tests (A-09).

Verifies that the scorer lock exists as a module-level singleton
and is the same object on repeated calls (no new lock per call).
"""
import asyncio


def test_scorer_lock_exists():
    from app.services.gae_state import get_scorer_lock
    lock = get_scorer_lock()
    assert isinstance(lock, asyncio.Lock)


def test_scorer_lock_is_singleton():
    from app.services.gae_state import get_scorer_lock
    lock1 = get_scorer_lock()
    lock2 = get_scorer_lock()
    assert lock1 is lock2
