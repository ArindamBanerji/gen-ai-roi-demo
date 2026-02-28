"""
GAE learning state manager — live LearningState singleton for SOC Copilot.

Single source of truth for the W matrix (4 actions × 6 factors) across
the backend process.  Initialized once at startup, persisted to JSON after
each outcome update.

Reference: docs/soc_copilot_design_v1.md §14.
"""

import json
import logging
import os
import tempfile
from pathlib import Path

import numpy as np
from gae.learning import LearningState

log = logging.getLogger(__name__)

_STATE_PATH = Path(__file__).parent.parent / "data" / "gae_learning_state.json"
_learning_state: LearningState | None = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _make_fresh_state() -> LearningState:
    """Build a LearningState from SOCDomainConfig expert priors."""
    from app.domains.soc.config import SOCDomainConfig
    W = SOCDomainConfig.get_initial_W()                      # shape (4, 6)
    factor_names = [c.name for c in SOCDomainConfig.get_factor_computers()]
    return LearningState(
        W=W.copy(),
        n_actions=4,
        n_factors=6,
        factor_names=factor_names,
    )


def _load_from_file() -> LearningState:
    """Deserialize W matrix from JSON checkpoint."""
    with open(_STATE_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    W = np.array(data["W"], dtype=np.float64)
    return LearningState(
        W=W,
        n_actions=data["n_actions"],
        n_factors=data["n_factors"],
        factor_names=data["factor_names"],
        decision_count=data.get("decision_count", 0),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def init_learning_state() -> LearningState:
    """
    Initialize the live LearningState.

    Loads from the JSON checkpoint if it exists; otherwise builds a fresh
    state from SOCDomainConfig.get_initial_W().  Called once in
    main.py startup_event().

    Returns
    -------
    LearningState
        The initialized state (also stored in module-level singleton).
    """
    global _learning_state
    if _STATE_PATH.exists():
        try:
            _learning_state = _load_from_file()
            print(
                f"[GAE] Loaded learning state from checkpoint "
                f"(step={_learning_state.decision_count}, W.shape={_learning_state.W.shape})"
            )
        except Exception as exc:
            log.warning(
                "[GAE] Could not load state from %s: %s — using fresh state",
                _STATE_PATH, exc,
            )
            _learning_state = _make_fresh_state()
    else:
        _learning_state = _make_fresh_state()
        print(
            f"[GAE] Fresh learning state initialized "
            f"(W.shape={_learning_state.W.shape})"
        )
    return _learning_state


def get_learning_state() -> LearningState:
    """
    Return the live LearningState.

    Raises
    ------
    RuntimeError
        If init_learning_state() has not been called yet.
    """
    if _learning_state is None:
        raise RuntimeError(
            "Learning state not initialized — call init_learning_state() at startup"
        )
    return _learning_state


def save_learning_state() -> None:
    """
    Atomically persist the current W matrix to the JSON checkpoint.

    Uses a temp-file + rename strategy to prevent partial writes on crash.
    No-op if the state has not been initialized.
    """
    if _learning_state is None:
        return
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "W":             _learning_state.W.tolist(),
        "n_actions":     _learning_state.n_actions,
        "n_factors":     _learning_state.n_factors,
        "factor_names":  _learning_state.factor_names,
        "decision_count": _learning_state.decision_count,
    }
    fd, tmp = tempfile.mkstemp(
        dir=_STATE_PATH.parent, suffix=".tmp", prefix=".gae_"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        os.replace(tmp, _STATE_PATH)
        log.debug(
            "[GAE] State saved to %s (step=%d)",
            _STATE_PATH, _learning_state.decision_count,
        )
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def reset_learning_state() -> None:
    """
    Reset to initial W matrix (for demo reset).
    Registered with state_manager so reset_all() covers this automatically.
    """
    global _learning_state
    _learning_state = _make_fresh_state()
    save_learning_state()
    print("[GAE] Learning state reset to initial W matrix")
