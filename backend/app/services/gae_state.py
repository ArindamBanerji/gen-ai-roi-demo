"""
GAE learning state manager — live LearningState singleton for SOC Copilot.

Single source of truth for the W matrix (n_actions × 6 factors) across
the backend process.  Initialized once at startup, persisted to JSON after
each outcome update.

Design:
  Serialization/deserialization LOGIC lives in app.framework.learning_state.
  Module-level singleton STATE (path, instances, metadata) lives here so
  it is patchable in tests via patch.object(gae_state, ...).

Reference: docs/soc_copilot_design_v1.md §14.
"""

import json
import logging
from pathlib import Path
from typing import Optional

import numpy as np
from gae.learning import LearningState, CalibrationProfile
from gae import bootstrap_calibration, BootstrapResult
from app.domains.soc.config import (
    SOC_BOOTSTRAP_ROUNDS, SOC_BOOTSTRAP_SAMPLES_PER_ACTION,
    SOC_BOOTSTRAP_SIGMA, SOC_BOOTSTRAP_CONVERGENCE_TOL, SOC_BOOTSTRAP_SEED,
    SOC_CATEGORIES,
)
import app.framework.learning_state as _fw

log = logging.getLogger(__name__)

# ── Module-level singleton state (owned here for test-patchability) ──────────

_STATE_PATH = Path(__file__).parent.parent / "data" / "gae_learning_state.json"
_learning_state: Optional[LearningState] = None
_bootstrap_metadata: Optional[dict] = None
_bootstrap_result: Optional[BootstrapResult] = None   # CORR-3: exposed for bootstrap_neo4j writer

_MU_ZERO_PATH = Path(__file__).parent.parent / "data" / "iks_bootstrap_soc.json"


# ---------------------------------------------------------------------------
# SOC-specific helpers
# ---------------------------------------------------------------------------

def _soc_profile() -> CalibrationProfile:
    """Return the SOC calibration profile (asymmetry 20:1, τ=0.1)."""
    return CalibrationProfile(
        learning_rate   = 0.02,
        penalty_ratio   = 20.0,   # asymmetry_ratio from SOCDomainConfig
        temperature     = 0.1,    # V3B validated ECE=0.036. Never use 0.25.
    )


def _make_fresh_state() -> LearningState:
    """Build a LearningState from SOCDomainConfig expert priors."""
    from app.domains.soc.config import SOCDomainConfig
    W = SOCDomainConfig.get_initial_W()                      # shape (n_actions, 6)
    factor_names = [c.name for c in SOCDomainConfig.get_factor_computers()]
    return _fw.make_state(W, factor_names, _soc_profile())


def _load_from_file() -> LearningState:
    """Deserialize W matrix and history from JSON checkpoint."""
    return _fw.load_from_file(_STATE_PATH, _soc_profile())


def _read_checkpoint_metadata() -> dict:
    """Read the metadata field from the checkpoint. Returns {} if absent."""
    return _fw.read_checkpoint_metadata(_STATE_PATH)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def init_learning_state() -> LearningState:
    """
    Initialize the live LearningState with bootstrap calibration.

    Three-path startup:
      1. Checkpoint with metadata.bootstrap=True → load as-is (already calibrated).
      2. Legacy checkpoint (no bootstrap metadata) → run bootstrap, overwrite.
      3. No checkpoint → fresh state, run bootstrap, save.

    Called once in main.py startup_event().
    """
    global _learning_state, _bootstrap_metadata, _bootstrap_result

    from app.domains.soc.config import SOCDomainConfig
    _soc_cfg = SOCDomainConfig()
    _profile_scorer = _soc_cfg.build_profile_scorer()

    needs_bootstrap = False

    if _STATE_PATH.exists():
        try:
            _learning_state = _load_from_file()
            checkpoint_meta = _read_checkpoint_metadata()
        except Exception as exc:
            log.warning(
                "[GAE] Could not load state from %s: %s — using fresh state",
                _STATE_PATH, exc,
            )
            _learning_state = _make_fresh_state()
            checkpoint_meta = {}

        if checkpoint_meta.get("bootstrap") is True:
            _bootstrap_metadata = checkpoint_meta
            print(
                f"[GAE] Loaded bootstrap checkpoint "
                f"(step={_learning_state.decision_count}, "
                f"drift={checkpoint_meta.get('drift', 0.0):.4f})"
            )
        else:
            print("[GAE] Legacy checkpoint detected — running bootstrap")
            needs_bootstrap = True
    else:
        _learning_state = _make_fresh_state()
        needs_bootstrap = True

    if needs_bootstrap:
        # Persist μ₀ (pre-bootstrap centroid state) for IKS computation.
        try:
            mu_zero = _profile_scorer.mu.copy()
            _MU_ZERO_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(_MU_ZERO_PATH, "w", encoding="utf-8") as _fh:
                json.dump({"mu_zero": mu_zero.tolist()}, _fh)
            log.info("[GAE] μ₀ persisted to %s (shape=%s)", _MU_ZERO_PATH, list(mu_zero.shape))
        except Exception as exc:
            log.warning("[GAE] Could not persist μ₀ to %s: %s", _MU_ZERO_PATH, exc)

        result: BootstrapResult = bootstrap_calibration(
            scorer=_profile_scorer,
            categories=list(SOC_CATEGORIES),
            n_rounds=SOC_BOOTSTRAP_ROUNDS,
            samples_per_action=SOC_BOOTSTRAP_SAMPLES_PER_ACTION,
            sigma=SOC_BOOTSTRAP_SIGMA,
            convergence_tol=SOC_BOOTSTRAP_CONVERGENCE_TOL,
            seed=SOC_BOOTSTRAP_SEED,
        )
        _bootstrap_result = result
        _learning_state.decision_count = result.n_decisions
        _bootstrap_metadata = {
            "bootstrap": True,
            "drift": result.final_drift,
            "n_decisions": result.n_decisions,
            "converged": result.converged,
        }
        print(
            f"[GAE] Bootstrap calibration complete "
            f"(decisions={result.n_decisions}, converged={result.converged}, "
            f"drift={result.final_drift:.4f})"
        )

    _learning_state.attach_profile_scorer(_profile_scorer)
    print(
        f"[GAE] ProfileScorer attached "
        f"(actions={_profile_scorer.actions}, tau={_profile_scorer.tau})"
    )

    if needs_bootstrap:
        save_learning_state()

    return _learning_state


def get_profile_scorer():
    """Return the global ProfileScorer instance."""
    return get_learning_state().profile_scorer


def get_bootstrap_result() -> Optional[BootstrapResult]:
    """
    Return the BootstrapResult from the last bootstrap run, or None.

    Returns None when the server loaded an existing bootstrapped checkpoint.
    Returns a BootstrapResult when bootstrap_calibration() ran this startup.
    """
    return _bootstrap_result


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
    No-op if the state has not been initialized.
    """
    _fw.save_state(_learning_state, _bootstrap_metadata, _STATE_PATH)


def reset_learning_state() -> None:
    """
    Reset to initial W matrix (for demo reset).
    Registered with state_manager so reset_all() covers this automatically.
    """
    global _learning_state
    _learning_state = _make_fresh_state()
    save_learning_state()
    print("[GAE] Learning state reset to initial W matrix")
