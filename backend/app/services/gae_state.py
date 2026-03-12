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
from gae.learning import LearningState, WeightUpdate, CalibrationProfile
from gae import bootstrap_calibration, BootstrapResult
from app.domains.soc.config import (
    SOC_BOOTSTRAP_ROUNDS, SOC_BOOTSTRAP_SAMPLES_PER_ACTION,
    SOC_BOOTSTRAP_SIGMA, SOC_BOOTSTRAP_CONVERGENCE_TOL, SOC_BOOTSTRAP_SEED,
    SOC_CATEGORIES,
)

log = logging.getLogger(__name__)

_STATE_PATH = Path(__file__).parent.parent / "data" / "gae_learning_state.json"
_learning_state: LearningState | None = None
_bootstrap_metadata: dict | None = None


# ---------------------------------------------------------------------------
# Internal helpers
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
    W = SOCDomainConfig.get_initial_W()                      # shape (4, 6)
    factor_names = [c.name for c in SOCDomainConfig.get_factor_computers()]
    return LearningState(
        W=W.copy(),
        n_actions=4,
        n_factors=6,
        factor_names=factor_names,
        profile=_soc_profile(),
    )


def _load_from_file() -> LearningState:
    """Deserialize W matrix and history from JSON checkpoint."""
    with open(_STATE_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    W = np.array(data["W"], dtype=np.float64)
    n_a = data["n_actions"]
    n_f = data["n_factors"]
    state = LearningState(
        W=W,
        n_actions=n_a,
        n_factors=n_f,
        factor_names=data["factor_names"],
        decision_count=data.get("decision_count", 0),
        profile=_soc_profile(),
    )
    # Restore WeightUpdate history so chart endpoints have data after restart.
    history = []
    for h in data.get("history", []):
        try:
            wu = WeightUpdate(
                decision_number=        h["decision_number"],
                timestamp=              h["timestamp"],
                action_index=           h["action_index"],
                action_name=            h["action_name"],
                outcome=                h["outcome"],
                factor_vector=          np.array(h["factor_vector"], dtype=np.float64),
                delta_applied=          np.array(h["delta_applied"], dtype=np.float64),
                W_before=               np.zeros((n_a, n_f), dtype=np.float64),
                W_after=                np.array(h["W_after"], dtype=np.float64),
                alpha_effective=        h["alpha_effective"],
                confidence_at_decision= h["confidence_at_decision"],
            )
            history.append(wu)
        except Exception as exc:
            log.warning("[GAE] Skipping malformed history entry: %s", exc)
    state.history = history
    return state


def _read_checkpoint_metadata() -> dict:
    """Read the metadata field from the checkpoint. Returns {} if absent."""
    with open(_STATE_PATH, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data.get("metadata", {})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def init_learning_state() -> LearningState:
    """
    Initialize the live LearningState with bootstrap calibration.

    Three-path startup:
      1. Checkpoint with metadata.bootstrap=True → load as-is (already calibrated).
         Log: [GAE] Loaded bootstrap checkpoint (step={n}, drift={drift:.4f})
      2. Legacy checkpoint (no bootstrap metadata) → run bootstrap, overwrite.
         Log: [GAE] Legacy checkpoint detected — running bootstrap
      3. No checkpoint → fresh state, run bootstrap, save.
         Log: [GAE] Bootstrap calibration complete (decisions={n}, ...)

    Called once in main.py startup_event().

    Returns
    -------
    LearningState
        The initialized state (also stored in module-level singleton).
    """
    global _learning_state, _bootstrap_metadata

    # Build ProfileScorer from SOC_PROFILE_CENTROIDS (always fresh)
    from app.domains.soc.config import SOCDomainConfig as _SOCDomainConfig
    _soc_cfg = _SOCDomainConfig()
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
            # Path 1: already bootstrapped — restore metadata and log
            _bootstrap_metadata = checkpoint_meta
            print(
                f"[GAE] Loaded bootstrap checkpoint "
                f"(step={_learning_state.decision_count}, "
                f"drift={checkpoint_meta.get('drift', 0.0):.4f})"
            )
        else:
            # Path 2: legacy checkpoint — run bootstrap, overwrite
            print("[GAE] Legacy checkpoint detected — running bootstrap")
            needs_bootstrap = True
    else:
        # Path 3: no checkpoint — fresh state, run bootstrap
        _learning_state = _make_fresh_state()
        needs_bootstrap = True

    if needs_bootstrap:
        # Change 0: persist μ₀ (pre-bootstrap centroid state) for IKS computation.
        # bootstrap_calibration() mutates scorer.mu in-place; capture the prior first.
        _mu_zero_path = _STATE_PATH.parent / "iks_bootstrap_soc.json"
        try:
            mu_zero = _profile_scorer.mu.copy()
            _mu_zero_path.parent.mkdir(parents=True, exist_ok=True)
            with open(_mu_zero_path, "w", encoding="utf-8") as _fh:
                json.dump({"mu_zero": mu_zero.tolist()}, _fh)
            log.info("[GAE] μ₀ persisted to %s (shape=%s)", _mu_zero_path, list(mu_zero.shape))
        except Exception as _exc:
            log.warning("[GAE] Could not persist μ₀ to %s: %s", _mu_zero_path, _exc)

        result: BootstrapResult = bootstrap_calibration(
            scorer=_profile_scorer,
            categories=list(SOC_CATEGORIES),
            n_rounds=SOC_BOOTSTRAP_ROUNDS,
            samples_per_action=SOC_BOOTSTRAP_SAMPLES_PER_ACTION,
            sigma=SOC_BOOTSTRAP_SIGMA,
            convergence_tol=SOC_BOOTSTRAP_CONVERGENCE_TOL,
            seed=SOC_BOOTSTRAP_SEED,
        )
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
    history_data = []
    for wu in _learning_state.history:
        history_data.append({
            "decision_number":        wu.decision_number,
            "timestamp":              wu.timestamp,
            "action_index":           wu.action_index,
            "action_name":            wu.action_name,
            "outcome":                wu.outcome,
            "alpha_effective":        wu.alpha_effective,
            "confidence_at_decision": wu.confidence_at_decision,
            "factor_vector":          wu.factor_vector.tolist(),
            "delta_applied":          wu.delta_applied.tolist(),
            "W_after":                wu.W_after.tolist(),
        })
    payload = {
        "W":             _learning_state.W.tolist(),
        "n_actions":     _learning_state.n_actions,
        "n_factors":     _learning_state.n_factors,
        "factor_names":  _learning_state.factor_names,
        "decision_count": _learning_state.decision_count,
        "history":       history_data,
    }
    if _bootstrap_metadata:
        payload["metadata"] = _bootstrap_metadata
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
