"""
Demo State Manager -- Centralized reset coordination for all in-memory state.

Each service that owns in-memory state registers a named reset handler here.
reset_all() clears every handler in one call, so reset endpoints stay thin.

Usage:
    from app.core.state_manager import state_manager

    # In a service module (called once at import time, e.g. at module bottom):
    state_manager.register("evolver", reset_evolver_state)

    # In a reset endpoint:
    await state_manager.reset_all()
"""
import inspect
from typing import Callable, Dict, List


class DemoStateManager:
    """Coordinates demo reset across all stateful services."""

    def __init__(self) -> None:
        self._handlers: Dict[str, Callable] = {}

    def register(self, name: str, reset_handler: Callable) -> None:
        """Store a named reset handler (idempotent -- overwrites if re-registered)."""
        self._handlers[name] = reset_handler
        print(f"[STATE] Registered reset handler: {name}")

    async def reset_all(self) -> None:
        """Call every registered reset handler and print a summary."""
        names = list(self._handlers.keys())
        print(f"[STATE] reset_all() -- resetting {len(names)} handler(s): {names}")
        for name, handler in self._handlers.items():
            result = handler()
            if inspect.isawaitable(result):
                await result
        print("[STATE] reset_all() -- done")

    async def reset_except(self, skip: list) -> None:
        """Call every registered handler except those named in skip.

        Use this for soft demo-cycle resets that must not disturb
        long-lived learned state (e.g. 'learning_state').
        """
        skip_set = set(skip)
        names = [n for n in self._handlers if n not in skip_set]
        print(f"[STATE] reset_except({skip}) -- resetting {len(names)} handler(s): {names}")
        for name in names:
            result = self._handlers[name]()
            if inspect.isawaitable(result):
                await result
        print("[STATE] reset_except() -- done")

    def get_registered(self) -> List[str]:
        """Return the list of registered handler names."""
        return list(self._handlers.keys())


# Module-level singleton used by all services and routers
state_manager = DemoStateManager()
