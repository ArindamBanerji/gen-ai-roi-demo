"""
GAE learning state manager -- live LearningState singleton for SOC Copilot.

Single source of truth for the W matrix (n_actions x d factors) across
the backend process.  Initialized once at startup, persisted to JSON after
each outcome update.

Design:
  Serialization/deserialization LOGIC lives in app.framework.learning_state.
  Module-level singleton STATE (path, instances, metadata) lives here so
  it is patchable in tests via patch.object(gae_state, ...).

Reference: docs/soc_copilot_design_v1.md Sec.14.
"""

import asyncio
import json
import logging
import os
import threading
from contextlib import asynccontextmanager
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional, cast

import numpy as np
from copilot_sdk.scoring.dk_persistence import DKWelfordTracker, persist_dk_after_reestimate
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


@asynccontextmanager
async def acquire_scorer():
    """
    Acquire _scorer_lock then yield the live ProfileScorer.
    Use for any path that mutates scorer state (centroid update, restore).
    Raises RuntimeError if ProfileScorer is not attached.
    """
    async with _scorer_lock:
        scorer = _learning_state.profile_scorer if _learning_state is not None else None
        if scorer is None:
            raise RuntimeError("ProfileScorer not attached -- call init_learning_state() first")
        yield scorer


@asynccontextmanager
async def acquire_scorer_for_reset():
    """
    Acquire _scorer_lock to guard the reset window.
    Used only by reset_learning_state() to serialize against in-flight updates.
    Yields None -- the old scorer is being torn down.
    """
    async with _scorer_lock:
        yield


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
_learning_store: Optional[object] = None
_dk_welford_tracker: DKWelfordTracker = DKWelfordTracker()
_dk_welford_lock = threading.Lock()
_bootstrap_metadata: Optional[dict] = None
_bootstrap_result: Optional[BootstrapResult] = None   # CORR-3: exposed for bootstrap_graph writer

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
    """Return the SOC calibration profile (asymmetry 20:1, tau=0.1)."""
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

def _load_age_learning_store_adapter():
    from ci_platform.graph.age_sdk_adapter import AGEGraphStoreAdapter

    return AGEGraphStoreAdapter


def _init_learning_store() -> object | None:
    from copilot_sdk.config import GraphConfig, GraphConfigError

    try:
        graph_config = GraphConfig.load("soc")
    except GraphConfigError as exc:
        log.warning("[GAE] SOC L5 learning store unavailable: %s", exc)
        return None

    dsn = (graph_config.dsn or "").strip()
    graph_name = graph_config.graph
    if not dsn:
        log.warning(
            "[GAE] SOC L5 learning store unavailable: AGE DSN is not configured"
        )
        return None
    try:
        adapter_cls = _load_age_learning_store_adapter()
        store = adapter_cls(dsn=dsn, graph_name=graph_name)
        log.info("[GAE] SOC L5 learning store initialized (graph=%s, domain=soc)", graph_name)
        return cast(object, store)
    except Exception as exc:
        log.warning(
            "[GAE] SOC L5 learning store unavailable (graph=%s, domain=soc, error_type=%s)",
            graph_name,
            type(exc).__name__,
        )
        return None


def init_learning_state() -> LearningState:
    """
    Initialize the live LearningState with bootstrap calibration.

    Three-path startup:
      1. Checkpoint with metadata.bootstrap=True -> load as-is (already calibrated).
      2. Legacy checkpoint (no bootstrap metadata) -> run bootstrap, overwrite.
      3. No checkpoint -> fresh state, run bootstrap, save.

    Called once in main.py startup_event().
    """
    global _learning_state, _learning_store, _bootstrap_metadata, _bootstrap_result

    from app.domains.soc.scorer_adapter import SOCCompoundingScorerAdapter
    from copilot_sdk.config import GraphConfig, GraphConfigError
    from copilot_sdk.graph.factory import create_graph_store
    from copilot_sdk.graph.dual_write_store import DualWriteStore

    # The SOC scorer must use the same typed AGE configuration as the shared
    # graph client.  In particular, do not fall back to the process-local
    # InMemoryGraphStore: B0 established that it reports V=0 while AGE has
    # the authoritative verified population.
    graph_config = GraphConfig.load("soc")
    graph_store = create_graph_store(
        domain="soc",
        backend=graph_config.backend,
        dsn=graph_config.dsn,
        graph_name=graph_config.graph,
        shared_graph_authorization=graph_config.authorized,
    )
    if isinstance(graph_store, DualWriteStore):
        raise GraphConfigError(
            "SOC scorer requires an AGE-backed store directly; "
            "dual_write reads from SQLite primary and is not authoritative"
        )
    _profile_scorer = SOCCompoundingScorerAdapter(graph_store=graph_store)
    assert _profile_scorer.eta_override is not None, (
        "ProfileScorer constructed without eta_override. "
        "SOC requires eta_override=0.01 (P0 fix -- prevents "
        "13-27pp centroid degradation from noisy overrides)."
    )

    needs_bootstrap = False

    if _STATE_PATH.exists():
        try:
            _learning_state = _load_from_file()
            checkpoint_meta = _read_checkpoint_metadata()
        except Exception as exc:
            log.warning(
                "[GAE] Could not load state from %s: %s -- using fresh state",
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
            print("[GAE] Legacy checkpoint detected -- running bootstrap")
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
            log.info("[GAE] mu0 persisted to %s (shape=%s)", _MU_ZERO_PATH, list(mu_zero.shape))
        except Exception as exc:
            log.warning("[GAE] Could not persist mu0 to %s: %s", _MU_ZERO_PATH, exc)

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

    _learning_store = _init_learning_store()
    reset_dk_welford_tracker()

    try:
        capture_result = _profile_scorer.capture_existing_state(
            capture_reason="startup_restore",
        )
        log.info("SOC startup state capture: %s", capture_result)
    except Exception as exc:
        log.warning("SOC startup state capture failed: %s", exc)

    return _learning_state


def get_learning_store():
    """Return optional L5 learning store for SOC AGE persistence."""
    return _learning_store


def reset_dk_welford_tracker() -> None:
    """Reset process-local SOC DK/Welford audit tracker."""
    global _dk_welford_tracker
    with _dk_welford_lock:
        _dk_welford_tracker = DKWelfordTracker()


def get_dk_welford_tracker() -> DKWelfordTracker:
    """Return the process-local SOC DK/Welford audit tracker."""
    return _dk_welford_tracker


def update_dk_welford_tracker(factor_vector, is_correct: bool) -> None:
    """Record one SOC verified decision in the Welford audit tracker."""
    with _dk_welford_lock:
        _dk_welford_tracker.update(factor_vector, is_correct=is_correct)


def _dk_weight_tensor_from_scorer(scorer) -> list[list[float]] | None:
    get_one = getattr(scorer, "get_dk_weights", None)
    if not callable(get_one):
        return None
    rows: list[list[float]] = []
    n_categories = int(getattr(scorer, "n_categories", 0) or 0)
    for category_index in range(n_categories):
        weights = get_one(category_index)
        if weights is None:
            return None
        rows.append(np.asarray(weights, dtype=np.float64).tolist())
    return rows


def persist_soc_dk_weights(scorer, *, logger: logging.Logger | None = None) -> bool:
    """Persist current SOC DK weights plus Welford state through the L5 store."""
    store = get_learning_store()
    if store is None:
        return False
    weights = _dk_weight_tensor_from_scorer(scorer)
    if weights is None:
        return False
    adapter = SimpleNamespace(get_dk_weights=lambda: deepcopy(weights))
    with _dk_welford_lock:
        tracker_snapshot = DKWelfordTracker.from_welford_state(
            _dk_welford_tracker.to_welford_state(),
            n_confirmed=_dk_welford_tracker.n_confirmed,
            n_overridden=_dk_welford_tracker.n_overridden,
        )
    return cast(bool, persist_dk_after_reestimate(
        domain="soc",
        scorer=adapter,
        learning_store=store,
        welford_tracker=tracker_snapshot,
        logger=logger or log,
    ))


def get_soc_category_phase(scorer, category_index: int) -> str:
    """Return canonical SOC ProfileScorer phase for a category."""
    get_phase = getattr(scorer, "get_phase", None)
    if not callable(get_phase):
        return "UNKNOWN"
    phase = get_phase(category_index)
    return cast(str, getattr(phase, "name", str(phase)))


def get_soc_centroid(scorer, category_index: int, action_index: int) -> list[float] | None:
    """Return a copy-safe SOC centroid vector."""
    centroids = getattr(scorer, "centroids", None)
    if centroids is None:
        centroids = getattr(scorer, "mu", None)
    if centroids is None:
        return None
    try:
        return cast(list[float], np.asarray(centroids[category_index, action_index], dtype=np.float64).copy().tolist())
    except Exception:
        return None


def persist_soc_centroid(
    *,
    scorer,
    category: str,
    category_index: int,
    action: str,
    action_index: int,
    caused_by_decision_id: str,
    pre_centroid: list[float] | None,
    logger: logging.Logger | None = None,
    store: object | None = None,
    raise_on_error: bool = False,
) -> bool:
    """Persist a SOC L5Centroid runtime write when centroid learning is active."""
    target_store: Any = store if store is not None else get_learning_store()
    if target_store is None or not hasattr(target_store, "update_centroid"):
        return False
    phase = get_soc_category_phase(scorer, category_index)
    if phase != "MEAN_CONVERGENCE":
        return False
    post = get_soc_centroid(scorer, category_index, action_index)
    if post is None:
        return False
    if pre_centroid is None:
        delta_norm = float(np.linalg.norm(np.asarray(post, dtype=np.float64)))
    else:
        delta_norm = float(
            np.linalg.norm(
                np.asarray(post, dtype=np.float64) - np.asarray(pre_centroid, dtype=np.float64)
            )
        )
    try:
        target_store.update_centroid(
            domain="soc",
            category=category,
            action=action,
            centroid_vector=post,
            delta_norm=delta_norm,
            caused_by_decision_id=caused_by_decision_id,
        )
    except Exception as exc:
        if raise_on_error:
            raise
        (logger or log).warning("SOC L5 centroid persistence failed: %s", exc)
        return False
    return True


async def persist_soc_outcome_and_centroid(
    *,
    store: Any,
    outcome: dict[str, Any],
    centroid: dict[str, Any],
    checkpoint_writer: Any | None = None,
    logger: logging.Logger | None = None,
) -> bool:
    """Persist the verified outcome and L5 centroid on one AGE transaction."""
    run_transaction = getattr(store, "run_transaction", None)
    if callable(run_transaction):
        def operation(transaction) -> bool:
            transaction.write_outcome(**outcome)
            centroid_persisted = persist_soc_centroid(
                **centroid,
                logger=logger,
                store=transaction,
                raise_on_error=True,
            )

            if checkpoint_writer is not None:
                checkpoint_writer(transaction)

            return centroid_persisted

        return cast(bool, await run_transaction(operation))

    # Non-AGE stores used by local/test profiles have no transaction primitive.
    # Preserve their existing behavior while production AGE remains atomic.
    store.write_outcome(**outcome)
    centroid_persisted = persist_soc_centroid(**centroid, logger=logger, store=store)
    if checkpoint_writer is not None:
        checkpoint_writer(None)
    return centroid_persisted


def get_profile_scorer():
    """Return the global ProfileScorer instance, or None if not yet initialized."""
    try:
        return get_learning_state().profile_scorer
    except RuntimeError:
        return None


def get_mu_zero():
    """
    Return mu_0 (bootstrap baseline centroid tensor) as a numpy ndarray.

    Reads from the persisted JSON file written at bootstrap time.
    Returns None if the file does not exist or cannot be parsed.
    Never raises.
    """
    import json as _json
    import numpy as _np
    try:
        if not _MU_ZERO_PATH.exists():
            log.warning("[GAE] mu0 file not found at %s", _MU_ZERO_PATH)
            return None
        with open(_MU_ZERO_PATH, "r", encoding="utf-8") as _fh:
            data = _json.load(_fh)
        arr = _np.array(data["mu_zero"], dtype=_np.float64)
        return arr
    except Exception as exc:
        log.warning("[GAE] Could not load mu0 from %s: %s", _MU_ZERO_PATH, exc)
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
            "Learning state not initialized -- call init_learning_state() at startup"
        )
    return _learning_state


def save_learning_state() -> None:
    """
    Atomically persist the current W matrix to the JSON checkpoint.
    No-op if the state has not been initialized.
    """
    _fw.save_state(_learning_state, _bootstrap_metadata, _STATE_PATH)


def _reset_learning_state_inner() -> None:
    """Synchronous reset body. Must only be called while _scorer_lock is held."""
    global _learning_state, _bootstrap_metadata, _bootstrap_result
    old_scorer = getattr(_learning_state, "profile_scorer", None)
    old_compound = getattr(old_scorer, "_compound", None)
    old_graph_store = getattr(old_compound, "_graph_store", None)
    for store in (old_graph_store, _learning_store):
        close = getattr(store, "close", None)
        if callable(close):
            try:
                close()
            except Exception as exc:
                log.warning("[GAE] Failed to close prior graph store during reset: %s", exc)
    _learning_state = None
    _bootstrap_metadata = {}
    _bootstrap_result = None
    init_learning_state()
    print("[GAE] Learning state reset and re-initialized with ProfileScorer")


async def reset_learning_state() -> None:
    """
    Reset to initial W matrix (for demo reset).
    Acquires _scorer_lock to serialize against in-flight centroid updates.
    Registered with state_manager so reset_all() covers this automatically.
    """
    async with acquire_scorer_for_reset():
        _reset_learning_state_inner()


# =============================================================================
# Block 2.1 — Graph-backed centroid checkpoint helpers
# =============================================================================

def _checkpoint_store() -> tuple[Any, Any]:
    """Return the live SOC scorer and its GraphStore, failing closed."""
    scorer = get_profile_scorer()
    if scorer is None:
        raise RuntimeError("SOC ProfileScorer is not initialized")
    store = scorer.graph_store
    if store is None:
        raise RuntimeError("SOC GraphStore is unavailable")
    return scorer, store


def _checkpoint_payload(checkpoint: dict[str, Any]) -> dict[str, Any]:
    """Normalize a GraphStore checkpoint to the legacy endpoint shape."""
    import hashlib
    import time

    centroids = checkpoint.get("centroids")
    if isinstance(centroids, str):
        centroids = json.loads(centroids)
    if centroids is None:
        raise RuntimeError("AGE checkpoint has no centroid tensor")
    shape = checkpoint.get("shape") or list(np.asarray(centroids).shape)
    metadata = checkpoint.get("metadata") or {}
    if isinstance(metadata, str):
        metadata = json.loads(metadata)
    timestamp_epoch = int(float(checkpoint.get("created_at", time.time())) * 1000)
    step = int(metadata.get("decision_count", checkpoint.get("decisions_count", 0)) or 0)
    canonical = {
        "mu": centroids,
        "shape": shape,
        "step": step,
        "timestamp_epoch": timestamp_epoch,
        "version": "age-checkpoint",
    }
    return {
        **canonical,
        "backup_id": checkpoint.get("checkpoint_id"),
        "sha256": hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest(),
        "metadata": metadata,
    }


def create_centroid_checkpoint() -> dict[str, Any]:
    """Persist a full SOC centroid tensor in the live GraphStore."""
    import uuid

    scorer, store = _checkpoint_store()
    checkpoint_id = f"soc:pitr:{uuid.uuid4().hex}"
    metadata = {"pitr": True, "decision_count": int(scorer.decision_count)}
    store.write_centroid_checkpoint(
        checkpoint_id=checkpoint_id,
        domain="soc",
        category="__full_tensor__",
        action="snapshot",
        centroids=scorer.centroids,
        decisions_count=int(scorer.decision_count),
        verified_count=int(store.count_verified("soc")),
        iks=0.0,
        shape=[int(value) for value in scorer.centroids.shape],
        factor_names_hash="soc",
        metadata=metadata,
    )
    checkpoints = store.get_centroid_checkpoints("soc", include_v2=True, limit=None)
    checkpoint: dict[str, Any] = next(
        (item for item in checkpoints if item.get("checkpoint_id") == checkpoint_id),
        {},
    )
    if not checkpoint:
        raise RuntimeError(f"AGE checkpoint {checkpoint_id} was not readable after write")
    return _checkpoint_payload(checkpoint)


def list_centroid_checkpoints() -> list[dict[str, Any]]:
    """List SOC centroid checkpoints from AGE, newest first."""
    _, store = _checkpoint_store()
    checkpoints = store.get_centroid_checkpoints("soc", include_v2=True, limit=None)
    return [_checkpoint_payload(checkpoint) for checkpoint in checkpoints]


def maybe_write_centroid_snapshot(*_args: Any, **_kwargs: Any) -> bool:
    """Compatibility hook for callers that used the retired file snapshot trigger.

    Learning checkpoints are written by the scorer through GraphStore.  This hook
    deliberately performs no persistence and exists only so older integrations
    can remove their call sites without creating filesystem state.
    """
    return False


async def restore_centroid_checkpoint(checkpoint_id: str | None = None) -> dict[str, Any]:
    """Restore a full SOC centroid tensor from an AGE checkpoint."""
    _, store = _checkpoint_store()
    checkpoints = store.get_centroid_checkpoints("soc", include_v2=True, limit=None)
    if not checkpoints:
        raise FileNotFoundError("No SOC centroid checkpoints exist in AGE")
    if checkpoint_id:
        checkpoint = next(
            (item for item in checkpoints if item.get("checkpoint_id") == checkpoint_id),
            None,
        )
    else:
        checkpoint = max(checkpoints, key=lambda item: float(item.get("created_at", 0.0)))
    if checkpoint is None:
        raise FileNotFoundError(f"AGE checkpoint not found: {checkpoint_id}")
    payload = _checkpoint_payload(checkpoint)
    scorer, _ = _checkpoint_store()
    tensor = np.asarray(payload["mu"], dtype=np.float64)
    if list(tensor.shape) != list(scorer.centroids.shape):
        raise ValueError(
            f"AGE checkpoint shape {list(tensor.shape)} does not match "
            f"live scorer shape {list(scorer.centroids.shape)}"
        )
    async with acquire_scorer():
        scorer.centroids = tensor
    return payload


# =============================================================================
# Block 2.2 — DeploymentState persistence (bootstrap μ₀ → AGE)
# =============================================================================

_GAE_VERSION = "0.7.20"

READ_DEPLOYMENT_STATE = """
MATCH (ds:DeploymentState {id: "current"})
RETURN ds.bootstrap_mu        AS bootstrap_mu,
       ds.bootstrap_shape     AS bootstrap_shape,
       ds.bootstrap_stored_at AS stored_at,
       ds.gae_version         AS gae_version
"""


async def write_bootstrap_state(graph_client, scorer) -> dict:
    """
    Persist the current bootstrap centroid tensor (mu_0) to a
    DeploymentState node in AGE.

    Called at startup after ProfileScorer is attached so mu_0 survives
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
        existing = await graph_client.run_query(
            "MATCH (ds:DeploymentState {id: 'current'}) RETURN ds"
        )
        if existing:
            await graph_client.run_query(
                f"MATCH (ds:DeploymentState {{id: 'current'}})"
                f" SET ds.bootstrap_mu = {_mu_s},"
                f"     ds.bootstrap_shape = {_shape_s},"
                f"     ds.bootstrap_stored_at = {_ts_s},"
                f"     ds.gae_version = {_ver_s}"
            )
        else:
            await graph_client.run_query(
                f"CREATE (ds:DeploymentState {{"
                f" id: 'current',"
                f" bootstrap_mu: {_mu_s},"
                f" bootstrap_shape: {_shape_s},"
                f" bootstrap_stored_at: {_ts_s},"
                f" gae_version: {_ver_s}"
                f"}})"
            )
        log.info("[GAE] DeploymentState written -- shape=%s gae_version=%s", shape, _GAE_VERSION)
    except Exception as e:
        log.warning("DeploymentState persist failed: %s", e)
    return {
        "bootstrap_mu":        mu_list,
        "bootstrap_shape":     shape,
        "bootstrap_stored_at": ts,
        "gae_version":         _GAE_VERSION,
    }


async def get_bootstrap_centroids(graph_client) -> dict | None:
    """
    Read bootstrap_centroids from the DeploymentState node.
    Returns {mu, shape, stored_at, gae_version} or None if not set.
    """
    try:
        rows = await graph_client.run_query(READ_DEPLOYMENT_STATE)
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


async def build_centroid_export(scorer, graph_client) -> dict:
    """
    Build the 10-field portable centroid export artifact.

    Fields
    ------
    export_version       : str   -- "1.0"
    generated_at_epoch   : int   -- ms since epoch
    gae_version          : str   -- "0.7.21"
    tensor_shape         : list  -- [n_categories, n_actions, n_factors]
    current_mu           : list  -- full centroid tensor (nested list)
    bootstrap_mu         : list|None -- mu_0 from DeploymentState, or None
    drift_from_bootstrap : float|None -- mean(|current - bootstrap|), or None
    decision_count       : int   -- scorer.decision_count
    categories           : list[str]
    actions              : list[str]
    sha256               : str   -- SHA-256 over canonical JSON of current_mu
    """
    import hashlib
    import json
    import time as _time

    bootstrap = await get_bootstrap_centroids(graph_client)
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


# =============================================================================
# Block 9.1 — Per-analyst η weight management
# =============================================================================

def apply_analyst_eta_weights(scorer, eta_weights: dict) -> None:
    """
    Store per-analyst eta weights on the module-level singleton and on the scorer.

    Sets module-level _analyst_eta_weights for endpoint reads, and attaches
    the dict to the scorer as a dynamic attribute so callers that hold a scorer
    reference can also read it without re-importing gae_state.

    Parameters
    ----------
    scorer      : ProfileScorer instance (attached to the live LearningState)
    eta_weights : dict mapping analyst name -> weight in [0.5, 1.5]
    """
    global _analyst_eta_weights
    _analyst_eta_weights = dict(eta_weights)
    # Attach to scorer for convenient access at update time
    try:
        scorer.eta_weights = dict(eta_weights)
    except Exception as exc:
        log.debug("[D5] Could not attach eta_weights to scorer: %s", exc)
    log.info("[D5] Analyst eta weights updated: %s", _analyst_eta_weights)


def get_analyst_eta_weights() -> dict:
    """Return the current module-level analyst eta weights (may be empty dict)."""
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
        log.warning("[D3] Volume spike flag SET -- centroid updates frozen this cadence")
    else:
        set_frozen_categories([])
        reset_spike_counter()
        log.info("[D3] Volume spike flag CLEARED -- centroid updates resumed")


def is_volume_spike_active() -> bool:
    """Return True if a volume spike is currently active."""
    return _volume_spike_active


def guarded_update(scorer, f, category_index: int, action_index: int,
                   correct: bool, category_name: str = "", **kwargs):
    """
    Spike-guarded + category-freeze wrapper around ProfileScorer.update().

    Guards (checked in order):
      1. D3 global spike flag -- skip all updates when volume spike active.
      2. D2 category freeze -- skip updates for over-represented categories
         during a spike (coupled to D3; frozen_categories is empty when no spike).
      3. D7 spike cap -- skip updates once 1.5x baseline daily count is reached.

    Parameters
    ----------
    scorer         : ProfileScorer -- the live scorer
    f              : np.ndarray -- factor vector
    category_index : int
    action_index   : int
    correct        : bool
    category_name  : str -- human-readable category name for D2 freeze check
    **kwargs       : forwarded to scorer.update() (e.g. gt_action_index, confidence)

    Returns
    -------
    CentroidUpdate on success, None when update was frozen by any guard.
    """
    if _volume_spike_active:
        log.warning(
            "[D3] guarded_update: spike active -- skipping centroid update "
            "(category=%d/%s, action=%d, correct=%s)",
            category_index, category_name or "?", action_index, correct,
        )
        return None
    if category_name and is_category_frozen(category_name):
        log.warning(
            "[D2] guarded_update: category '%s' frozen -- skipping update "
            "(action=%d, correct=%s)",
            category_name, action_index, correct,
        )
        return None
    if getattr(scorer, 'is_paused', False) is True:
        log.warning(
            "[B5] guarded_update: conservation paused -- skipping centroid update "
            "(category=%d/%s, action=%d, correct=%s)",
            category_index, category_name or "?", action_index, correct,
        )
        return None
    if not increment_spike_counter():
        log.warning(
            "[D7] guarded_update: spike cap reached (%d) -- skipping update "
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
    categories : list[str] -- category names to freeze
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
    Set the per-cadence update cap to 1.5 x baseline_daily.

    Call this when a volume spike is detected, passing daily_mean from
    compute_volume_baseline(). Cap of 0 disables D7 enforcement.

    Parameters
    ----------
    baseline_daily : float -- mean daily alert/decision count from 30-day window
    """
    global _spike_update_cap
    _spike_update_cap = int(1.5 * baseline_daily)
    log.info("[D7] Spike update cap set: %d (1.5 x %.1f)", _spike_update_cap, baseline_daily)


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
    bool : True -> proceed with update; False -> skip (cap reached)
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
      spike_cap             : int   -- 0 means not set
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
