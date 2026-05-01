"""
GAE learning state manager — live LearningState singleton for SOC Copilot.

Single source of truth for the W matrix (n_actions × d factors) across
the backend process.  Initialized once at startup, persisted to JSON after
each outcome update.

Design:
  Serialization/deserialization LOGIC lives in app.framework.learning_state.
  Module-level singleton STATE (path, instances, metadata) lives here so
  it is patchable in tests via patch.object(gae_state, ...).

Reference: docs/soc_copilot_design_v1.md §14.
"""

import asyncio
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
    SOC_CATEGORIES, SCORER_ACTIONS,
)
import app.framework.learning_state as _fw

log = logging.getLogger(__name__)

_scorer_lock = asyncio.Lock()


def get_scorer_lock() -> asyncio.Lock:
    return _scorer_lock


def _S(val) -> str:
    """Serialize a Python value to an AGE-safe inline Cypher literal."""
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, (list, tuple)):
        return "'" + json.dumps(val).replace("'", "\\'") + "'"
    return "'" + str(val).replace("\\", "\\\\").replace("'", "\\'") + "'"

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

# Block 9.3 — Category freeze set (populated during spike events only).
# Categories in this set have their centroid updates skipped.
_frozen_categories: set = set()

# Block 9.4 — Spike update cap (D7).
# _spike_update_cap  = int(1.5 × baseline_daily); 0 means not set.
# _spike_update_count = updates processed in current cadence (resets each cadence).
_spike_update_cap:   int = 0
_spike_update_count: int = 0

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
    W = SOCDomainConfig.get_initial_W()                      # shape (n_actions, n_factors)
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
    assert _profile_scorer.eta_override is not None, (
        "ProfileScorer constructed without eta_override. "
        "SOC requires eta_override=0.01 (P0 fix — prevents "
        "13-27pp centroid degradation from noisy overrides)."
    )

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
            mu_zero = _profile_scorer.centroids.copy()
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
    """Return the global ProfileScorer instance, or None if not yet initialized."""
    try:
        return get_learning_state().profile_scorer
    except RuntimeError:
        return None


def get_mu_zero():
    """
    Return μ₀ (bootstrap baseline centroid tensor) as a numpy ndarray.

    Reads from the persisted JSON file written at bootstrap time.
    Returns None if the file does not exist or cannot be parsed.
    Never raises.
    """
    import json as _json
    import numpy as _np
    try:
        if not _MU_ZERO_PATH.exists():
            log.warning("[GAE] μ₀ file not found at %s", _MU_ZERO_PATH)
            return None
        with open(_MU_ZERO_PATH, "r", encoding="utf-8") as _fh:
            data = _json.load(_fh)
        arr = _np.array(data["mu_zero"], dtype=_np.float64)
        return arr
    except Exception as exc:
        log.warning("[GAE] Could not load μ₀ from %s: %s", _MU_ZERO_PATH, exc)
        return None


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

    mu = scorer.centroids.tolist()
    step = getattr(scorer, "decision_count", 0)
    payload = {
        "mu":              mu,
        "shape":           list(scorer.centroids.shape),
        "step":            step,
        "timestamp_epoch": int(time.time() * 1000),
        "version":         "1.0",
    }
    canonical = json.dumps(payload, sort_keys=True)
    payload["sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return payload


def write_centroid_backup(scorer, metadata: dict | None = None) -> dict:
    """
    Serialize mu, write timestamped + latest backup files.
    Returns the payload dict (includes sha256 and backup_id).

    Parameters
    ----------
    scorer   : ProfileScorer — source of centroids.
    metadata : optional dict merged into the JSON payload (trigger, decision_id, …).
    """
    import uuid as _uuid
    payload = serialize_centroid_tensor(scorer)
    ts = payload["timestamp_epoch"]
    # UUID suffix guarantees uniqueness even when two snapshots occur in the
    # same millisecond (common in tests and high-throughput simulation runs).
    backup_id = f"centroid_backup_{ts}_{_uuid.uuid4().hex[:8]}"
    payload["backup_id"] = backup_id
    if metadata:
        payload["metadata"] = metadata

    d = _ensure_backup_dir()
    timestamped = d / f"{backup_id}.json"
    latest = d / "centroid_backup_latest.json"

    data = json.dumps(payload)
    timestamped.write_text(data)
    latest.write_text(data)

    return payload


# =============================================================================
# Block 2.1b — Auto-snapshot trigger (FEATURE-04 Centroid Time Machine)
# =============================================================================

SNAPSHOT_INTERVAL: int = 10   # snapshot every N verified decisions

_snapshot_decision_count: int = 0


def maybe_write_centroid_snapshot(
    scorer,
    decision_id: str = "",
    category: str = "",
) -> bool:
    """Auto-snapshot centroids every SNAPSHOT_INTERVAL verified decisions.

    Increments a module-level counter on every call and writes a backup when
    the counter is a positive multiple of SNAPSHOT_INTERVAL.  Returns True
    if a backup was written, False otherwise.  Never raises — all errors are
    logged as warnings so callers can fire-and-forget.
    """
    global _snapshot_decision_count
    _snapshot_decision_count += 1
    if _snapshot_decision_count % SNAPSHOT_INTERVAL != 0:
        return False
    try:
        metadata = {
            "trigger":        "auto",
            "decision_count": _snapshot_decision_count,
            "decision_id":    decision_id,
            "category":       category,
        }
        write_centroid_backup(scorer, metadata=metadata)
        log.info(
            "[SNAPSHOT] Auto-snapshot #%d written (every %d decisions)",
            _snapshot_decision_count,
            SNAPSHOT_INTERVAL,
        )
        return True
    except Exception as e:
        log.warning("[SNAPSHOT] Auto-snapshot failed: %s", e)
        return False


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
    ts      = int(_time.time() * 1000)
    mu_list = scorer.centroids.tolist()
    shape   = list(scorer.centroids.shape)

    _mu_s    = _S(json.dumps(mu_list))
    _shape_s = _S(json.dumps(shape))
    _ts_s    = _S(ts)
    _ver_s   = _S(_GAE_VERSION)

    try:
        existing = await neo4j_client.run_query(
            "MATCH (ds:DeploymentState {id: 'current'}) RETURN ds"
        )
        if existing:
            await neo4j_client.run_query(
                f"MATCH (ds:DeploymentState {{id: 'current'}})"
                f" SET ds.bootstrap_mu = {_mu_s},"
                f"     ds.bootstrap_shape = {_shape_s},"
                f"     ds.bootstrap_stored_at = {_ts_s},"
                f"     ds.gae_version = {_ver_s}"
            )
        else:
            await neo4j_client.run_query(
                f"CREATE (ds:DeploymentState {{"
                f" id: 'current',"
                f" bootstrap_mu: {_mu_s},"
                f" bootstrap_shape: {_shape_s},"
                f" bootstrap_stored_at: {_ts_s},"
                f" gae_version: {_ver_s}"
                f"}})"
            )
        log.info("[GAE] DeploymentState written — shape=%s gae_version=%s", shape, _GAE_VERSION)
    except Exception as e:
        log.warning("DeploymentState persist failed: %s", e)
    return {
        "bootstrap_mu":        mu_list,
        "bootstrap_shape":     shape,
        "bootstrap_stored_at": ts,
        "gae_version":         _GAE_VERSION,
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
        # AGE stores nested lists as JSON strings — parse back to Python list.
        mu = r["bootstrap_mu"]
        if isinstance(mu, str):
            mu = json.loads(mu)
        shape = r["bootstrap_shape"]
        if isinstance(shape, str):
            shape = json.loads(shape)
        return {
            "mu":         mu,
            "shape":      shape,
            "stored_at":  r["stored_at"],
            "gae_version": r.get("gae_version", "unknown"),
        }
    except Exception as exc:
        log.warning("[GAE] get_bootstrap_centroids failed: %s", exc)
        return None


_EXPORT_CATEGORIES = [
    "credential_access", "lateral_movement",
    "data_exfiltration", "malware_execution",
    "insider_threat", "cloud_infrastructure",
]
_EXPORT_ACTIONS = list(SCORER_ACTIONS)
_EXPORT_VERSION = "1.0"
_EXPORT_GAE_VERSION = "0.7.21"


async def build_centroid_export(scorer, neo4j_client) -> dict:
    """
    Build the 10-field portable centroid export artifact.

    Fields
    ------
    export_version       : str   — "1.0"
    generated_at_epoch   : int   — ms since epoch
    gae_version          : str   — "0.7.21"
    tensor_shape         : list  — [n_categories, n_actions, n_factors]
    current_mu           : list  — full centroid tensor (nested list)
    bootstrap_mu         : list|None — μ₀ from DeploymentState, or None
    drift_from_bootstrap : float|None — mean(|current - bootstrap|), or None
    decision_count       : int   — scorer.decision_count
    categories           : list[str]
    actions              : list[str]
    sha256               : str   — SHA-256 over canonical JSON of current_mu
    """
    import hashlib
    import json
    import time as _time

    bootstrap = await get_bootstrap_centroids(neo4j_client)
    current_mu = scorer.centroids.tolist()

    if bootstrap and bootstrap.get("mu") is not None:
        boot_arr = np.array(bootstrap["mu"], dtype=np.float64)
        curr_arr = np.array(current_mu,      dtype=np.float64)
        drift: float | None = float(np.mean(np.abs(curr_arr - boot_arr)))
    else:
        drift = None

    canonical = json.dumps({"mu": current_mu}, sort_keys=True)
    sha256 = hashlib.sha256(canonical.encode()).hexdigest()

    return {
        "export_version":       _EXPORT_VERSION,
        "generated_at_epoch":   int(_time.time() * 1000),
        "gae_version":          _EXPORT_GAE_VERSION,
        "tensor_shape":         list(scorer.centroids.shape),
        "current_mu":           current_mu,
        "bootstrap_mu":         bootstrap["mu"] if bootstrap else None,
        "drift_from_bootstrap": drift,
        "decision_count":       scorer.decision_count,
        "categories":           _EXPORT_CATEGORIES,
        "actions":              _EXPORT_ACTIONS,
        "sha256":               sha256,
    }


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
    scorer.centroids = mu_array
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
                   correct: bool, category_name: str = "", **kwargs):
    """
    Spike-guarded + category-freeze wrapper around ProfileScorer.update().

    Guards (checked in order):
      1. D3 global spike flag — skip all updates when volume spike active.
      2. D2 category freeze — skip updates for over-represented categories
         during a spike (coupled to D3; frozen_categories is empty when no spike).
      3. D7 spike cap — skip updates once 1.5× baseline daily count is reached.

    Parameters
    ----------
    scorer         : ProfileScorer — the live scorer
    f              : np.ndarray — factor vector
    category_index : int
    action_index   : int
    correct        : bool
    category_name  : str — human-readable category name for D2 freeze check
    **kwargs       : forwarded to scorer.update() (e.g. gt_action_index, confidence)

    Returns
    -------
    CentroidUpdate on success, None when update was frozen by any guard.
    """
    if _volume_spike_active:
        log.warning(
            "[D3] guarded_update: spike active — skipping centroid update "
            "(category=%d/%s, action=%d, correct=%s)",
            category_index, category_name or "?", action_index, correct,
        )
        return None
    if category_name and is_category_frozen(category_name):
        log.warning(
            "[D2] guarded_update: category '%s' frozen — skipping update "
            "(action=%d, correct=%s)",
            category_name, action_index, correct,
        )
        return None
    if getattr(scorer, 'is_paused', False) is True:
        log.warning(
            "[B5] guarded_update: conservation paused — skipping centroid update "
            "(category=%d/%s, action=%d, correct=%s)",
            category_index, category_name or "?", action_index, correct,
        )
        return None
    if not increment_spike_counter():
        log.warning(
            "[D7] guarded_update: spike cap reached (%d) — skipping update "
            "(category=%d/%s, action=%d)",
            _spike_update_cap, category_index, category_name or "?", action_index,
        )
        return None
    return scorer.update(f=f, category_index=category_index,
                         action_index=action_index, correct=correct, **kwargs)


# =============================================================================
# Block 9.3 — Category freeze (volume spikes only)
# =============================================================================

def set_frozen_categories(categories: list) -> None:
    """
    Replace the frozen-category set.

    Must only be called when a volume spike is active (D3 coupled constraint).
    Clears automatically when set_volume_spike(False) is called, but callers
    should also call set_frozen_categories([]) on spike clearance.

    Parameters
    ----------
    categories : list[str] — category names to freeze
    """
    global _frozen_categories
    _frozen_categories = set(categories)
    if _frozen_categories:
        log.warning("[D2] Frozen categories set: %s", sorted(_frozen_categories))
    else:
        log.info("[D2] Frozen categories cleared")


def get_frozen_categories() -> set:
    """Return the current set of frozen category names (may be empty)."""
    return set(_frozen_categories)


def is_category_frozen(category: str) -> bool:
    """Return True if the given category name is currently frozen."""
    return category in _frozen_categories


# =============================================================================
# Block 9.4 — Spike update cap (D7, coupled to D3)
# =============================================================================

def set_spike_cap(baseline_daily: float) -> None:
    """
    Set the per-cadence update cap to 1.5 × baseline_daily.

    Call this when a volume spike is detected, passing daily_mean from
    compute_volume_baseline(). Cap of 0 disables D7 enforcement.

    Parameters
    ----------
    baseline_daily : float — mean daily alert/decision count from 30-day window
    """
    global _spike_update_cap
    _spike_update_cap = int(1.5 * baseline_daily)
    log.info("[D7] Spike update cap set: %d (1.5 × %.1f)", _spike_update_cap, baseline_daily)


def reset_spike_counter() -> None:
    """
    Reset the per-cadence update counter to 0.

    Call at the start of each cadence (each day or scoring batch).
    """
    global _spike_update_count
    _spike_update_count = 0
    log.debug("[D7] Spike update counter reset")


def increment_spike_counter() -> bool:
    """
    Increment the cadence update counter and check against the cap.

    Returns True if the update is allowed; False if the cap is reached.
    Always returns True when no spike is active or cap is not set.

    Returns
    -------
    bool : True → proceed with update; False → skip (cap reached)
    """
    global _spike_update_count, _spike_update_cap
    if not _volume_spike_active:
        return True          # no cap outside of spike
    if _spike_update_cap <= 0:
        return True          # cap not configured
    if _spike_update_count >= _spike_update_cap:
        return False         # cap exhausted
    _spike_update_count += 1
    return True


def get_spike_cap_status() -> dict:
    """
    Return current spike cap state for the endpoint and monitoring.

    Returns
    -------
    dict:
      spike_active          : bool
      spike_cap             : int   — 0 means not set
      updates_this_cadence  : int
      cap_reached           : bool
    """
    cap_reached = (
        _volume_spike_active
        and _spike_update_cap > 0
        and _spike_update_count >= _spike_update_cap
    )
    return {
        "spike_active":         _volume_spike_active,
        "spike_cap":            _spike_update_cap,
        "updates_this_cadence": _spike_update_count,
        "cap_reached":          cap_reached,
    }
