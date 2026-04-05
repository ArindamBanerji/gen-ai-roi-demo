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

# Block 9.1 — Per-analyst η weights (populated by apply_analyst_eta_weights).
# Keyed by analyst name; values are multiplicative weights in [0.5, 1.5].
_analyst_eta_weights: dict = {}

# Block 9.2 — Volume spike flag.
# When True, centroid updates must be skipped for the current cadence.
_volume_spike_active: bool = False

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


# =============================================================================
# Block 2.1 — Centroid tensor PITR backup helpers
# =============================================================================

_BACKUP_DIR = Path(__file__).resolve().parents[2] / "app" / "data" / "centroid_backups"


def _ensure_backup_dir() -> Path:
    _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return _BACKUP_DIR


def serialize_centroid_tensor(scorer) -> dict:
    """
    Serialize the ProfileScorer centroid tensor (mu) with a SHA-256 integrity hash.

    Returns a dict ready to be written as JSON.  The sha256 is computed over
    a canonical JSON encoding of the payload (sort_keys=True, no hash field),
    so it can be re-verified without the original object.
    """
    import hashlib
    import time

    mu = scorer.mu.tolist()
    step = getattr(scorer, "decision_count", 0)
    payload = {
        "mu":              mu,
        "shape":           list(scorer.mu.shape),
        "step":            step,
        "timestamp_epoch": int(time.time() * 1000),
        "version":         "1.0",
    }
    canonical = json.dumps(payload, sort_keys=True)
    payload["sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return payload


def write_centroid_backup(scorer) -> dict:
    """
    Serialize mu, write timestamped + latest backup files.
    Returns the payload dict (includes sha256 and backup_id).
    """
    payload = serialize_centroid_tensor(scorer)
    ts = payload["timestamp_epoch"]
    backup_id = f"centroid_backup_{ts}"
    payload["backup_id"] = backup_id

    d = _ensure_backup_dir()
    timestamped = d / f"{backup_id}.json"
    latest = d / "centroid_backup_latest.json"

    data = json.dumps(payload)
    timestamped.write_text(data)
    latest.write_text(data)

    return payload


def list_centroid_backups() -> list:
    """
    List all timestamped backup files in _BACKUP_DIR.
    Returns list of dicts: [{backup_id, timestamp_epoch, step, sha256}]
    sorted newest-first.
    """
    d = _ensure_backup_dir()
    results = []
    for f in sorted(d.glob("centroid_backup_[0-9]*.json"), reverse=True):
        try:
            raw = json.loads(f.read_text())
            results.append({
                "backup_id":       raw.get("backup_id", f.stem),
                "timestamp_epoch": raw.get("timestamp_epoch", 0),
                "step":            raw.get("step", 0),
                "sha256":          raw.get("sha256", ""),
            })
        except Exception:
            pass
    return results


def load_centroid_backup(backup_id: str | None = None) -> dict:
    """
    Load a backup payload by backup_id, or the latest if backup_id is None/empty.
    Raises FileNotFoundError if the file does not exist.
    """
    d = _ensure_backup_dir()
    if not backup_id:
        path = d / "centroid_backup_latest.json"
    else:
        path = d / f"{backup_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Backup not found: {path}")
    return json.loads(path.read_text())


# =============================================================================
# Block 2.2 — DeploymentState persistence (bootstrap μ₀ → Neo4j)
# =============================================================================

_GAE_VERSION = "0.7.20"

WRITE_DEPLOYMENT_STATE = """
MERGE (ds:DeploymentState {id: "current"})
SET ds.bootstrap_mu           = $bootstrap_mu,
    ds.bootstrap_shape        = $bootstrap_shape,
    ds.bootstrap_stored_at    = $timestamp_epoch,
    ds.gae_version            = $gae_version
RETURN ds
"""

READ_DEPLOYMENT_STATE = """
MATCH (ds:DeploymentState {id: "current"})
RETURN ds.bootstrap_mu        AS bootstrap_mu,
       ds.bootstrap_shape     AS bootstrap_shape,
       ds.bootstrap_stored_at AS stored_at,
       ds.gae_version         AS gae_version
"""


async def write_bootstrap_state(neo4j_client, scorer) -> dict:
    """
    Persist the current bootstrap centroid tensor (μ₀) to a
    DeploymentState node in Neo4j.

    Called at startup after ProfileScorer is attached so μ₀ survives
    server restarts and is available to the centroid export endpoint (Block 2.3).

    Returns the stored payload.
    """
    import time as _time
    ts = int(_time.time() * 1000)
    mu_list = scorer.mu.tolist()
    shape   = list(scorer.mu.shape)

    await neo4j_client.run_query(
        WRITE_DEPLOYMENT_STATE,
        {
            "bootstrap_mu":    mu_list,
            "bootstrap_shape": shape,
            "timestamp_epoch": ts,
            "gae_version":     _GAE_VERSION,
        },
    )
    log.info("[GAE] DeploymentState written — shape=%s gae_version=%s", shape, _GAE_VERSION)
    return {
        "bootstrap_mu":       mu_list,
        "bootstrap_shape":    shape,
        "bootstrap_stored_at": ts,
        "gae_version":        _GAE_VERSION,
    }


async def get_bootstrap_centroids(neo4j_client) -> dict | None:
    """
    Read bootstrap_centroids from the DeploymentState node.
    Returns {mu, shape, stored_at, gae_version} or None if not set.
    """
    try:
        rows = await neo4j_client.run_query(READ_DEPLOYMENT_STATE)
        if not rows or rows[0].get("bootstrap_mu") is None:
            return None
        r = rows[0]
        return {
            "mu":         r["bootstrap_mu"],
            "shape":      r["bootstrap_shape"],
            "stored_at":  r["stored_at"],
            "gae_version": r.get("gae_version", "unknown"),
        }
    except Exception as exc:
        log.warning("[GAE] get_bootstrap_centroids failed: %s", exc)
        return None


def restore_centroid_from_backup(backup_id: str | None = None) -> dict:
    """
    Load backup, verify SHA-256, and restore mu into the live ProfileScorer.

    Returns the payload dict on success.
    Raises ValueError on checksum mismatch.
    Raises RuntimeError if ProfileScorer is not attached.
    """
    import hashlib

    payload = load_centroid_backup(backup_id)

    # Re-compute canonical hash (same fields as serialize, minus sha256)
    verify_payload = {k: v for k, v in payload.items()
                      if k not in ("sha256", "backup_id")}
    canonical = json.dumps(verify_payload, sort_keys=True)
    expected = hashlib.sha256(canonical.encode()).hexdigest()
    if payload.get("sha256") != expected:
        raise ValueError(
            f"Checksum mismatch: stored={payload.get('sha256')!r} "
            f"computed={expected!r}"
        )

    scorer = get_profile_scorer()
    if scorer is None:
        raise RuntimeError("ProfileScorer not attached — call init_learning_state() first")

    mu_array = np.array(payload["mu"], dtype=np.float64)
    scorer.mu[:] = mu_array
    return payload


# =============================================================================
# Block 9.1 — Per-analyst η weight management
# =============================================================================

def apply_analyst_eta_weights(scorer, eta_weights: dict) -> None:
    """
    Store per-analyst η weights on the module-level singleton and on the scorer.

    Sets module-level _analyst_eta_weights for endpoint reads, and attaches
    the dict to the scorer as a dynamic attribute so callers that hold a scorer
    reference can also read it without re-importing gae_state.

    Parameters
    ----------
    scorer      : ProfileScorer instance (attached to the live LearningState)
    eta_weights : dict mapping analyst name → weight in [0.5, 1.5]
    """
    global _analyst_eta_weights
    _analyst_eta_weights = dict(eta_weights)
    # Attach to scorer for convenient access at update time
    try:
        scorer.eta_weights = dict(eta_weights)
    except Exception as exc:
        log.debug("[D5] Could not attach eta_weights to scorer: %s", exc)
    log.info("[D5] Analyst η weights updated: %s", _analyst_eta_weights)


def get_analyst_eta_weights() -> dict:
    """Return the current module-level analyst η weights (may be empty dict)."""
    return dict(_analyst_eta_weights)


# =============================================================================
# Block 9.2 — Volume spike flag + guarded update
# =============================================================================

def set_volume_spike(active: bool) -> None:
    """
    Set the volume spike flag.

    When active=True, callers must skip centroid updates this cadence to
    prevent bulk-alert poisoning. Typically set by detect_volume_spike().
    """
    global _volume_spike_active
    _volume_spike_active = bool(active)
    if active:
        log.warning("[D3] Volume spike flag SET — centroid updates frozen this cadence")
    else:
        log.info("[D3] Volume spike flag CLEARED — centroid updates resumed")


def is_volume_spike_active() -> bool:
    """Return True if a volume spike is currently active."""
    return _volume_spike_active


def guarded_update(scorer, f, category_index: int, action_index: int,
                   correct: bool, **kwargs):
    """
    Spike-guarded wrapper around ProfileScorer.update().

    Checks is_volume_spike_active() before delegating to scorer.update().
    If a spike is active, skips the update and returns None so cadence
    callers can detect the skip.

    Parameters
    ----------
    scorer         : ProfileScorer — the live scorer
    f              : np.ndarray — factor vector
    category_index : int
    action_index   : int
    correct        : bool
    **kwargs       : forwarded to scorer.update() (e.g. gt_action_index, confidence)

    Returns
    -------
    CentroidUpdate on success, None when update was frozen by spike guard.
    """
    if _volume_spike_active:
        log.warning(
            "[D3] guarded_update: spike active — skipping centroid update "
            "(category=%d, action=%d, correct=%s)",
            category_index, action_index, correct,
        )
        return None
    return scorer.update(f=f, category_index=category_index,
                         action_index=action_index, correct=correct, **kwargs)
