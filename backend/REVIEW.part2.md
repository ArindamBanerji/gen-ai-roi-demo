# SOC Backend Line-by-Line Review — Part 2

## app/services/gae_state.py (847 lines)

### Architecture
- This module owns the process-local GAE `LearningState`/ProfileScorer lifecycle, checkpoint path, bootstrap metadata, centroid PITR backups, DeploymentState persistence, centroid export/restore, analyst eta weights, spike/freeze guards, and the `guarded_update()` wrapper used by triage outcome learning (`app/services/gae_state.py:34-847`).
- Demo and product features depending on it include startup initialization, Tab 2 profile/centroid/IKS display, outcome learning updates, conservation/spike gates, centroid export/time-machine features, bootstrap-state persistence, and demo/admin reset handlers (`app/services/gae_state.py:116-209`, `app/services/gae_state.py:365-397`, `app/services/gae_state.py:452-590`, `app/services/gae_state.py:681-735`).
- It bridges the SOC backend to GAE by constructing `CalibrationProfile`, creating/loading `LearningState`, building a SOC `ProfileScorer` via `SOCDomainConfig`, running `gae.bootstrap_calibration`, attaching the ProfileScorer to the live state, and exposing update guards around `scorer.update()` (`app/services/gae_state.py:23-30`, `app/services/gae_state.py:85-99`, `app/services/gae_state.py:129-200`, `app/services/gae_state.py:734-735`).

### Function-by-Function Review

- **get_scorer_lock** (line 37-38)
  - Purpose: Exposes the module-level `asyncio.Lock`.
  - Inputs: None.
  - Logic: Returns `_scorer_lock`.
  - Output: `asyncio.Lock`.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Callers must use it; this function does not enforce locking itself.

- **_S** (line 41-51)
  - Purpose: Serializes Python values to inline AGE-safe Cypher literals.
  - Inputs: Any value.
  - Logic: Converts `None`, bools, numbers, lists/tuples as JSON strings, and other values as escaped strings.
  - Output: String containing a Cypher literal.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Avoids named `$param` use; escapes backslashes and single quotes for scalar strings.

- **_soc_profile** (line 85-91)
  - Purpose: Builds the SOC GAE calibration profile.
  - Inputs: None.
  - Logic: Returns `CalibrationProfile(learning_rate=0.02, penalty_ratio=20.0, temperature=0.1)`.
  - Output: `gae.learning.CalibrationProfile`.
  - Side effects: None.
  - GAE calls: Instantiates GAE `CalibrationProfile`.
  - Error handling: None.
  - Invariants/guards: Encodes asymmetry 20:1 and tau 0.1.

- **_make_fresh_state** (line 94-99)
  - Purpose: Creates a fresh `LearningState` from SOC expert priors.
  - Inputs: None.
  - Logic: Reads initial `W` and factor names from `SOCDomainConfig`, then calls `_fw.make_state()`.
  - Output: `LearningState`.
  - Side effects: Imports SOC config locally.
  - GAE calls: Indirect through framework state construction with a GAE calibration profile.
  - Error handling: None.
  - Invariants/guards: Assumes initial W shape and factor-computer order match SOC runtime.

- **_load_from_file** (line 102-104)
  - Purpose: Loads a `LearningState` checkpoint.
  - Inputs: None.
  - Logic: Calls `_fw.load_from_file(_STATE_PATH, _soc_profile())`.
  - Output: `LearningState`.
  - Side effects: Reads JSON checkpoint.
  - GAE calls: Indirect framework deserialization.
  - Error handling: None here; caller catches in `init_learning_state()`.
  - Invariants/guards: Uses the module checkpoint path.

- **_read_checkpoint_metadata** (line 107-109)
  - Purpose: Reads checkpoint metadata.
  - Inputs: None.
  - Logic: Delegates to `_fw.read_checkpoint_metadata(_STATE_PATH)`.
  - Output: Dict, usually `{}` if absent.
  - Side effects: Reads JSON checkpoint.
  - GAE calls: None.
  - Error handling: Delegated.
  - Invariants/guards: None in this wrapper.

- **init_learning_state** (line 116-209)
  - Purpose: Initializes `_learning_state`, bootstrap metadata/result, and ProfileScorer.
  - Inputs: None.
  - Logic: Builds a new SOC ProfileScorer, asserts `eta_override` is present, then either loads a bootstrapped checkpoint, loads/falls back from a legacy/corrupt checkpoint and bootstraps, or creates a fresh state and bootstraps (`app/services/gae_state.py:129-198`). It persists pre-bootstrap `mu_zero`, runs `bootstrap_calibration()`, records bootstrap metadata, attaches the ProfileScorer to `_learning_state`, and saves state when bootstrap ran (`app/services/gae_state.py:166-207`).
  - Output: Live `LearningState`.
  - Side effects: Mutates `_learning_state`, `_bootstrap_metadata`, `_bootstrap_result`; writes `iks_bootstrap_soc.json`; may overwrite `gae_learning_state.json`; prints/logs startup messages.
  - GAE calls: `SOCDomainConfig.build_profile_scorer()`, `gae.bootstrap_calibration()`, `LearningState.attach_profile_scorer()`.
  - Error handling: Checkpoint load failure logs warning and uses fresh state; `mu_zero` write failure logs warning and continues; bootstrap failures are not caught.
  - Invariants/guards: Assertion requires ProfileScorer `eta_override`; checkpoint metadata flag `bootstrap=True` prevents re-bootstrap; `needs_bootstrap` controls persistence.

- **get_profile_scorer** (line 212-217)
  - Purpose: Returns the global ProfileScorer if initialized.
  - Inputs: None.
  - Logic: Calls `get_learning_state().profile_scorer`.
  - Output: ProfileScorer or `None`.
  - Side effects: None.
  - GAE calls: Reads ProfileScorer attached to GAE state.
  - Error handling: Converts `RuntimeError` from uninitialized state into `None`.
  - Invariants/guards: Does not validate scorer shape or readiness beyond initialization.

- **get_mu_zero** (line 220-240)
  - Purpose: Loads persisted bootstrap baseline centroids.
  - Inputs: None.
  - Logic: Reads `_MU_ZERO_PATH`, parses JSON key `mu_zero`, converts to `np.float64` array.
  - Output: NumPy array or `None`.
  - Side effects: File read; warning logs.
  - GAE calls: None.
  - Error handling: Missing file or parse errors return `None`.
  - Invariants/guards: Converts dtype to float64; no shape validation.

- **get_bootstrap_result** (line 243-250)
  - Purpose: Exposes the last startup bootstrap result.
  - Inputs: None.
  - Logic: Returns `_bootstrap_result`.
  - Output: `BootstrapResult` or `None`.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Existing checkpoint startup returns `None`.

- **get_learning_state** (line 253-266)
  - Purpose: Returns the live `LearningState`.
  - Inputs: None.
  - Logic: Raises if `_learning_state is None`; otherwise returns it.
  - Output: `LearningState`.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Raises `RuntimeError` before initialization.
  - Invariants/guards: Enforces startup initialization.

- **save_learning_state** (line 269-274)
  - Purpose: Persists current learning state.
  - Inputs: None.
  - Logic: Calls `_fw.save_state(_learning_state, _bootstrap_metadata, _STATE_PATH)`.
  - Output: None.
  - Side effects: Writes checkpoint file.
  - GAE calls: Indirect serialization of GAE state.
  - Error handling: None in wrapper.
  - Invariants/guards: Docstring says no-op if uninitialized, but the code always delegates `_learning_state`, even if `None`.

- **reset_learning_state** (line 277-285)
  - Purpose: Resets learning state for reset handlers.
  - Inputs: None.
  - Logic: Replaces `_learning_state` with `_make_fresh_state()`, saves it, prints reset message.
  - Output: None.
  - Side effects: Mutates singleton and checkpoint.
  - GAE calls: Indirect `LearningState` construction.
  - Error handling: None.
  - Invariants/guards: Does not attach a ProfileScorer after reset.

- **_ensure_backup_dir** (line 295-297)
  - Purpose: Ensures centroid backup directory exists.
  - Inputs: None.
  - Logic: Calls `_BACKUP_DIR.mkdir(parents=True, exist_ok=True)`.
  - Output: Backup `Path`.
  - Side effects: Creates directory.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Uses fixed path under `app/data/centroid_backups`.

- **serialize_centroid_tensor** (line 300-322)
  - Purpose: Serializes scorer centroids with integrity hash.
  - Inputs: `scorer` with `centroids` and optional `decision_count`.
  - Logic: Builds payload with `mu`, `shape`, `step`, `timestamp_epoch`, `version`, hashes canonical JSON excluding `sha256`, and returns payload.
  - Output: Dict with SHA-256.
  - Side effects: None.
  - GAE calls: Reads ProfileScorer centroid tensor.
  - Error handling: None.
  - Invariants/guards: Hash is over payload before `sha256` is added.

- **write_centroid_backup** (line 325-353)
  - Purpose: Writes timestamped and latest centroid backup files.
  - Inputs: `scorer`, optional metadata dict.
  - Logic: Serializes centroids, creates UUID-suffixed backup ID, merges metadata, writes both `{backup_id}.json` and `centroid_backup_latest.json`.
  - Output: Backup payload.
  - Side effects: File writes.
  - GAE calls: Reads ProfileScorer through serializer.
  - Error handling: None.
  - Invariants/guards: UUID suffix avoids same-millisecond collisions.

- **maybe_write_centroid_snapshot** (line 365-397)
  - Purpose: Auto-snapshots centroids every `SNAPSHOT_INTERVAL`.
  - Inputs: `scorer`, optional `decision_id`, category.
  - Logic: Increments `_snapshot_decision_count`; writes backup only when the count is a positive multiple of 10.
  - Output: Boolean written/not written.
  - Side effects: Mutates `_snapshot_decision_count`; may write backup files.
  - GAE calls: Reads ProfileScorer centroids.
  - Error handling: Catches/logs backup failures and returns False.
  - Invariants/guards: Interval gate; no lock around counter.

- **list_centroid_backups** (line 400-419)
  - Purpose: Lists timestamped centroid backups.
  - Inputs: None.
  - Logic: Reads matching JSON files sorted reverse, parses selected metadata fields, ignores unreadable files.
  - Output: List of backup summaries.
  - Side effects: Directory creation through `_ensure_backup_dir()`.
  - GAE calls: None.
  - Error handling: Bare `except Exception: pass` skips bad files.
  - Invariants/guards: Only `centroid_backup_[0-9]*.json` files included.

- **load_centroid_backup** (line 422-434)
  - Purpose: Loads a specific or latest backup payload.
  - Inputs: Optional `backup_id`.
  - Logic: Resolves path and parses JSON.
  - Output: Backup dict.
  - Side effects: Directory creation/read.
  - GAE calls: None.
  - Error handling: Raises `FileNotFoundError`; JSON parse errors propagate.
  - Invariants/guards: Uses latest when backup ID missing.

- **write_bootstrap_state** (line 452-502)
  - Purpose: Persists bootstrap centroid tensor to a graph `DeploymentState` node.
  - Inputs: `neo4j_client`, `scorer`.
  - Logic: Serializes current centroids, shape, timestamp, and GAE version; checks for `DeploymentState {id: 'current'}`; updates if present or creates otherwise; returns payload regardless of graph write success.
  - Output: Dict with bootstrap tensor metadata.
  - Side effects: Graph write and logs.
  - GAE calls: Reads ProfileScorer centroids.
  - Error handling: Catches all graph-write exceptions, logs warning, still returns payload.
  - Invariants/guards: Uses `_S()` for JSON/timestamp/version inline literals.

- **get_bootstrap_centroids** (line 505-530)
  - Purpose: Reads bootstrap centroids from graph DeploymentState.
  - Inputs: `neo4j_client`.
  - Logic: Runs `READ_DEPLOYMENT_STATE`, returns `None` if absent, parses JSON strings for `bootstrap_mu` and `bootstrap_shape`.
  - Output: Dict `{mu, shape, stored_at, gae_version}` or `None`.
  - Side effects: Graph read.
  - GAE calls: None.
  - Error handling: Catches/logs exceptions and returns `None`.
  - Invariants/guards: Handles AGE stringified nested lists.

- **build_centroid_export** (line 543-590)
  - Purpose: Builds portable centroid export artifact.
  - Inputs: `scorer`, `neo4j_client`.
  - Logic: Reads bootstrap centroids, computes mean absolute drift if available, hashes current mu, and returns export metadata.
  - Output: Dict with export version, generated time, GAE version, tensor shape, current/bootstrap mu, drift, decision count, categories, actions, hash.
  - Side effects: Graph read via `get_bootstrap_centroids()`.
  - GAE calls: Reads ProfileScorer centroids and decision count.
  - Error handling: None around drift shape mismatch or hash serialization; exceptions propagate.
  - Invariants/guards: Uses hardcoded export categories/actions and version strings.

- **restore_centroid_from_backup** (line 593-622)
  - Purpose: Restores live ProfileScorer centroids from backup after checksum verification.
  - Inputs: Optional `backup_id`.
  - Logic: Loads backup, recomputes hash excluding `sha256` and `backup_id`, raises on mismatch, gets live scorer, converts `mu` to float64 array, assigns `scorer.centroids`.
  - Output: Backup payload.
  - Side effects: Mutates live ProfileScorer centroids.
  - GAE calls: Reads and mutates ProfileScorer.
  - Error handling: Raises `ValueError` on checksum mismatch, `RuntimeError` if scorer missing; file/JSON errors propagate.
  - Invariants/guards: Checksum guard; scorer readiness guard; no shape compatibility guard.

- **apply_analyst_eta_weights** (line 629-649)
  - Purpose: Stores analyst eta weights globally and on scorer.
  - Inputs: `scorer`, `eta_weights`.
  - Logic: Copies input dict to `_analyst_eta_weights`; attempts dynamic `scorer.eta_weights` attachment.
  - Output: None.
  - Side effects: Mutates module global and possibly scorer object.
  - GAE calls: Mutates ProfileScorer dynamic attribute.
  - Error handling: Dynamic attach failure logged at debug and otherwise ignored.
  - Invariants/guards: Comments state weights should be `[0.5, 1.5]`, but no bounds are enforced.

- **get_analyst_eta_weights** (line 652-654)
  - Purpose: Returns current eta weights.
  - Inputs: None.
  - Logic: Returns a shallow copy.
  - Output: Dict.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Copy prevents direct caller mutation of global dict.

- **set_volume_spike** (line 661-673)
  - Purpose: Sets global volume spike flag.
  - Inputs: `active`.
  - Logic: Casts to bool, stores `_volume_spike_active`, logs set/clear.
  - Output: None.
  - Side effects: Mutates global flag.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Does not clear frozen categories despite docstring saying they clear automatically elsewhere.

- **is_volume_spike_active** (line 676-678)
  - Purpose: Reads spike flag.
  - Inputs: None.
  - Logic: Returns `_volume_spike_active`.
  - Output: Bool.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: None.

- **guarded_update** (line 681-735)
  - Purpose: Enforces spike, category-freeze, conservation pause, and spike-cap gates before ProfileScorer updates.
  - Inputs: `scorer`, factor vector `f`, `category_index`, `action_index`, `correct`, optional `category_name`, forwarded kwargs.
  - Logic: Returns `None` if volume spike active, category frozen, scorer paused, or spike cap exhausted; otherwise calls `scorer.update(f=f, category_index=..., action_index=..., correct=..., **kwargs)`.
  - Output: CentroidUpdate-like object or `None`.
  - Side effects: May increment spike counter; may mutate ProfileScorer through update.
  - GAE calls: Direct `ProfileScorer.update()`.
  - Error handling: None around scorer update.
  - Invariants/guards: D3 spike freeze, D2 category freeze, conservation pause, D7 cap; no input bounds on indexes or vector shape.

- **set_frozen_categories** (line 742-759)
  - Purpose: Replaces frozen category set.
  - Inputs: List of category names.
  - Logic: Converts to set and logs set/clear.
  - Output: None.
  - Side effects: Mutates `_frozen_categories`.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Comment says should only be called during spike, but code does not enforce spike coupling.

- **get_frozen_categories** (line 762-764)
  - Purpose: Reads frozen categories.
  - Inputs: None.
  - Logic: Returns copy of set.
  - Output: Set.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Copy prevents direct mutation.

- **is_category_frozen** (line 767-769)
  - Purpose: Checks one category.
  - Inputs: Category string.
  - Logic: Membership test in `_frozen_categories`.
  - Output: Bool.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: None.

- **set_spike_cap** (line 776-789)
  - Purpose: Sets D7 cap to `int(1.5 * baseline_daily)`.
  - Inputs: `baseline_daily`.
  - Logic: Computes int cap and logs.
  - Output: None.
  - Side effects: Mutates `_spike_update_cap`.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: No lower bound; negative baseline creates negative cap.

- **reset_spike_counter** (line 792-800)
  - Purpose: Resets cadence counter.
  - Inputs: None.
  - Logic: Sets `_spike_update_count=0`.
  - Output: None.
  - Side effects: Mutates global counter.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: None.

- **increment_spike_counter** (line 803-822)
  - Purpose: Applies D7 counter/cap.
  - Inputs: None.
  - Logic: Returns True outside spike or without cap; returns False if cap exhausted; otherwise increments counter and returns True.
  - Output: Bool allow/deny.
  - Side effects: Mutates `_spike_update_count` only when active and cap configured.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Cap check before increment.

- **get_spike_cap_status** (line 825-847)
  - Purpose: Returns spike/cap state for endpoint/monitoring.
  - Inputs: None.
  - Logic: Computes `cap_reached` and returns state dict.
  - Output: Dict.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: `cap_reached` requires active spike and positive cap.

### Invariants Enforced
- `get_learning_state()` raises before initialization (`app/services/gae_state.py:253-266`).
- `init_learning_state()` asserts ProfileScorer has `eta_override` (`app/services/gae_state.py:129-136`).
- Bootstrapped checkpoint metadata skips re-bootstrap; legacy/missing checkpoint runs bootstrap (`app/services/gae_state.py:140-166`).
- `mu_zero` and checkpoint files are persisted on bootstrap, and ProfileScorer is attached before returning (`app/services/gae_state.py:166-209`).
- `_S()` avoids `$param` by producing inline AGE literals (`app/services/gae_state.py:41-51`).
- Centroid backups carry SHA-256 hashes, and restore verifies the hash before mutation (`app/services/gae_state.py:300-322`, `app/services/gae_state.py:603-621`).
- Auto-snapshot writes only on multiples of `SNAPSHOT_INTERVAL=10` (`app/services/gae_state.py:360-397`).
- DeploymentState parsing handles AGE JSON strings for nested lists (`app/services/gae_state.py:515-521`).
- `guarded_update()` blocks on volume spike, frozen category, conservation pause, and spike cap before calling `scorer.update()` (`app/services/gae_state.py:681-735`).
- Getter functions return copies for eta weights and frozen categories (`app/services/gae_state.py:652-654`, `app/services/gae_state.py:762-764`).

### Potential Issues

#### P1
- `reset_learning_state()` replaces `_learning_state` with `_make_fresh_state()` and saves it, but does not attach a ProfileScorer (`app/services/gae_state.py:277-285`). Any later `get_profile_scorer()` call can return missing/invalid scorer state even though `_learning_state` is initialized, which can break analyze/profile flows after a hard reset.
- `restore_centroid_from_backup()` verifies checksum but does not validate restored tensor shape against the live scorer before assigning `scorer.centroids = mu_array` (`app/services/gae_state.py:603-621`). A valid backup with incompatible dimensions can corrupt live scorer state.

#### P2
- Module-level state is broadly mutable and mostly unlocked: `_learning_state`, `_bootstrap_metadata`, `_analyst_eta_weights`, spike flags/counters, frozen categories, and snapshot counter can be read/written concurrently (`app/services/gae_state.py:55-78`, `app/services/gae_state.py:360-397`, `app/services/gae_state.py:629-847`). Only callers that explicitly use `get_scorer_lock()` are protected.
- `_scorer_lock = asyncio.Lock()` is created at import time (`app/services/gae_state.py:34`). If tests or server lifecycle create/reuse event loops differently, an import-time lock can be awkward; current code assumes one process/event-loop lifecycle.
- `save_learning_state()` docstring says no-op when uninitialized, but code delegates `_learning_state` unconditionally (`app/services/gae_state.py:269-274`). Actual behavior depends on `_fw.save_state()` and may not match the comment.
- `set_volume_spike(False)` does not clear `_frozen_categories`, despite `set_frozen_categories()` docstring saying frozen categories clear automatically when spike clears (`app/services/gae_state.py:661-673`, `app/services/gae_state.py:742-749`). Stale frozen categories can block later updates if `guarded_update()` reaches the category check.
- `write_bootstrap_state()` catches graph-write failures and still returns a payload that looks successfully stored (`app/services/gae_state.py:472-502`). Callers cannot distinguish persisted vs only computed state.
- `build_centroid_export()` assumes bootstrap/current centroid shapes match; shape mismatch raises during drift computation (`app/services/gae_state.py:565-571`).

#### P3
- Top docstring says "single source of truth for the W matrix" (`app/services/gae_state.py:1-6`), but active code is mostly ProfileScorer/centroid based and W-matrix comments are stale relative to current behavior.
- `_GAE_VERSION` is `"0.7.20"` for DeploymentState while export `_EXPORT_GAE_VERSION` is `"0.7.21"` (`app/services/gae_state.py:441`, `app/services/gae_state.py:540`), which may confuse artifact comparisons.
- Several comments state policy constraints without enforcement, including eta weight bounds and category-freeze coupling (`app/services/gae_state.py:60-62`, `app/services/gae_state.py:637-640`, `app/services/gae_state.py:742-748`).
- `list_centroid_backups()` silently skips bad files with bare `except` (`app/services/gae_state.py:408-419`), hiding backup corruption.

### Cross-Module Dependencies
- Depends on `gae.learning.LearningState`, `CalibrationProfile`, `gae.bootstrap_calibration`, and `BootstrapResult` for learning and bootstrap lifecycle (`app/services/gae_state.py:23-24`).
- Depends on `app.domains.soc.config` for SOC bootstrap constants, categories, scorer actions, initial W, factor computers, and ProfileScorer construction (`app/services/gae_state.py:25-30`, `app/services/gae_state.py:94-99`, `app/services/gae_state.py:129-131`).
- Depends on `app.framework.learning_state` for state serialization/deserialization/checkpoint metadata (`app/services/gae_state.py:30`, `app/services/gae_state.py:94-109`, `app/services/gae_state.py:269-274`).
- Triage outcome code assumes `guarded_update()` enforces conservation/spike/freeze and calls ProfileScorer update, and uses `get_scorer_lock()` externally for thread safety (`app/services/gae_state.py:37-38`, `app/services/gae_state.py:681-735`).
- Centroid export/backup routes and time-machine features assume backup files are JSON at `_BACKUP_DIR` and DeploymentState has `bootstrap_mu`, `bootstrap_shape`, `bootstrap_stored_at`, and `gae_version` (`app/services/gae_state.py:292-353`, `app/services/gae_state.py:443-530`).

## app/services/feedback.py (451 lines)

### Architecture
- This module implements the in-memory feedback/trust simulation used after outcome submission. It defines response models, mutable simulated pattern/edge/precedent state, maps SOC categories to edge keys, records whether feedback was already given, mutates trust, seeds trust history, and resets demo state (`app/services/feedback.py:12-451`).
- Demo flows depending on it include `POST /api/alert/outcome`, `GET /api/alert/outcome/status`, `GET /api/rl/reward-summary`, reset handlers, and Tab 3 outcome narrative/graph update display (`app/services/feedback.py:122-314`, `app/services/feedback.py:336-451`).
- It does not bridge directly to GAE. GAE outcome learning, `guarded_update()`, ProfileScorer updates, conservation checks, audit-chain writes, and `TRIGGERED_EVOLUTION` graph writes are performed in `app/routers/triage.py`; this file only handles local feedback/trust/pattern simulation (`app/services/feedback.py:122-289`).

### Function-by-Function Review

- **GraphUpdate** (line 92-98)
  - Purpose: Pydantic model for one simulated graph update.
  - Inputs: `entity`, `field`, `before`, `after`, `direction`.
  - Logic: Pydantic validates fields; `direction` is limited to `"strengthened"` or `"weakened"`.
  - Output: Model instance.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Pydantic validation errors if fields invalid.
  - Invariants/guards: Literal direction validation.

- **NextAlertsOverride** (line 101-105)
  - Purpose: Pydantic model for manual-review override guidance.
  - Inputs: `action`, `count`, `reason`.
  - Logic: Pydantic validation only.
  - Output: Model instance.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Pydantic validation errors.
  - Invariants/guards: No bounds on `count`.

- **OutcomeResponse** (line 108-115)
  - Purpose: Pydantic model returned by `process_outcome()`.
  - Inputs: Alert/outcome fields, update list, consequence, optional next override, narrative.
  - Logic: Pydantic validation and nested model coercion.
  - Output: Model instance.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Pydantic validation errors.
  - Invariants/guards: `graph_updates` must be a list of `GraphUpdate`.

- **process_outcome** (line 122-289)
  - Purpose: Processes correct/incorrect outcome into simulated pattern, edge, precedent, feedback, trust, and narrative state.
  - Inputs: `alert_id`, `decision_id`, `outcome: Literal["correct", "incorrect"]`, optional `alert_category`.
  - Logic: If category missing, maps alert IDs containing `7823` to `credential_access`, `7824` to `malware_execution`, otherwise `_default` (`app/services/feedback.py:143-159`). It gets a pattern ID from `SOCDomainConfig`, an edge key from `_CATEGORY_EDGE_MAP`, then for correct outcomes increases pattern confidence by `0.003` capped at `0.99`, edge weight by `0.02` capped at `0.99`, increments precedent count, and builds positive narrative (`app/services/feedback.py:161-219`). For incorrect outcomes it decreases pattern confidence by `0.06` floored at `0.50`, edge weight by `0.05` floored at `0.50`, and returns a next-5-alerts Tier 2 override (`app/services/feedback.py:221-267`). It stores `FEEDBACK_GIVEN[alert_id]`, calls `update_trust(alert_category, outcome)`, and returns `OutcomeResponse` (`app/services/feedback.py:269-289`).
  - Output: `OutcomeResponse`.
  - Side effects: Mutates `PATTERN_CONFIDENCE`, `EDGE_WEIGHTS`, `PRECEDENT_COUNTS`, imported `FEEDBACK_GIVEN`, and trust state in `feedback_base`.
  - GAE calls: None.
  - Error handling: None; missing pattern IDs/edge keys or invalid outcomes can propagate exceptions if caller bypasses Pydantic validation.
  - Invariants/guards: Confidence caps/floors; edge caps/floors; correct/incorrect branch; fallback category mapping.

- **get_feedback_status** (line 292-314)
  - Purpose: Reports whether feedback has already been submitted for an alert.
  - Inputs: `alert_id`.
  - Logic: Looks up `FEEDBACK_GIVEN` and returns status dict with immutable flag.
  - Output: Dict.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Once present, `can_modify=False`.

- **get_current_pattern_state** (line 317-333)
  - Purpose: Returns current simulated pattern and edge state for display.
  - Inputs: None.
  - Logic: Builds a pattern dict with confidence and precedent count; returns a shallow copy of edges.
  - Output: Dict.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Edge dict is copied; nested pattern data is newly built.

- **seed_trust_history** (line 336-390)
  - Purpose: Seeds trust history with a 12-point asymmetry demo.
  - Inputs: None.
  - Logic: Creates timestamped entries for nine correct, one incorrect, two correct outcomes; appends them to `TRUST_HISTORY`; sets `TRUST_SCORES["travel_login_anomaly"] = 0.23`; sets low-trust flag true.
  - Output: None.
  - Side effects: Mutates imported trust lists/dicts and prints.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Fixed final trust `0.23`; no idempotence guard.

- **reset_trust_state** (line 397-406)
  - Purpose: Resets trust state to seeded baseline.
  - Inputs: None.
  - Logic: Clears trust dict/list/flags, calls `seed_trust_history()`, prints.
  - Output: None.
  - Side effects: Mutates imported trust state.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Clears before seeding, making it idempotent.

- **reset_feedback_state** (line 409-451)
  - Purpose: Resets feedback and simulated graph state to initial values.
  - Inputs: None.
  - Logic: Clears `FEEDBACK_GIVEN`; assigns initial values for all pattern confidences, edge weights, and precedent counts.
  - Output: None.
  - Side effects: Mutates imported feedback store and local module dicts.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Does not delete extra keys that may have been added to pattern/edge/precedent dicts.

### Invariants Enforced
- `GraphUpdate.direction` is limited to `"strengthened"`/`"weakened"` by `Literal` (`app/services/feedback.py:92-98`).
- Correct outcome caps pattern confidence at `0.99` and edge weight at `0.99` (`app/services/feedback.py:170-200`).
- Incorrect outcome floors pattern confidence and edge weight at `0.50` (`app/services/feedback.py:221-238`).
- Unknown category falls back to `_default` only when caller omitted `alert_category`; supplied unknown categories rely on config/map behavior (`app/services/feedback.py:146-163`).
- Feedback is stored by `alert_id`, and status reports it immutable (`app/services/feedback.py:269-280`, `app/services/feedback.py:292-314`).
- `reset_trust_state()` clears trust stores before reseeding (`app/services/feedback.py:397-406`).
- `reset_feedback_state()` clears feedback and restores known baseline values (`app/services/feedback.py:409-451`).

### Potential Issues

#### P1
- No P1 issue found in `feedback.py` itself. The graph/audit/ProfileScorer outcome risks are in the router path that calls this module, not in this file.

#### P2
- All feedback, pattern, edge, precedent, and trust state is process-local mutable state with no lock (`app/services/feedback.py:12-24`, `app/services/feedback.py:36-85`, `app/services/feedback.py:269-280`, `app/services/feedback.py:397-451`). Concurrent outcome submissions or resets can race.
- `process_outcome()` is not idempotent; duplicate calls for the same alert mutate pattern/edge/precedent/trust again before/without an internal duplicate guard (`app/services/feedback.py:170-280`). The router checks duplicate feedback, but the service does not enforce it.
- `seed_trust_history()` appends fixed baseline entries without clearing first (`app/services/feedback.py:336-390`). It is safe through `reset_trust_state()` but duplicate direct calls duplicate seeded history.
- `reset_feedback_state()` restores known keys but does not remove unknown extra keys from `PATTERN_CONFIDENCE`, `EDGE_WEIGHTS`, or `PRECEDENT_COUNTS` (`app/services/feedback.py:409-451`).

#### P3
- Module docstring says it "updates the graph" (`app/services/feedback.py:1-5`), but this file only updates in-memory simulated dictionaries; graph writes happen elsewhere.
- `alert_type = alert_category.replace("_", " ")` is assigned and unused (`app/services/feedback.py:163`).
- Imported `get_trust_status`, `get_all_trust_scores`, and `get_reward_summary` are re-exported for callers but not used internally (`app/services/feedback.py:13-21`); that is intentional per comments but easy to mistake for dead imports.
- Comments for `seed_trust_history()` say "Called at end of reset_trust_state() AND at module import" (`app/services/feedback.py:347-349`), while active code says it is called explicitly from `main.py` startup, not import (`app/services/feedback.py:393-394`).

### Cross-Module Dependencies
- Imports `FEEDBACK_GIVEN` from `app.framework.feedback_store` and re-exports it for callers (`app/services/feedback.py:12`).
- Imports trust stores/functions from `app.framework.feedback_base`, including `TRUST_SCORES`, `TRUST_HISTORY`, `LOW_TRUST_FLAGS`, `update_trust`, and reward/trust query functions (`app/services/feedback.py:13-21`).
- Depends on `SOCDomainConfig.get_pattern_for_category()` to map SOC category to pattern ID (`app/services/feedback.py:11`, `app/services/feedback.py:161`).
- `app/routers/triage.py` depends on `process_outcome()`, `get_feedback_status()`, `get_reward_summary()`, `reset_feedback_state()`, `reset_trust_state()`, and `seed_trust_history()` for outcome and reset flows.
- The service assumes caller-level request validation for `outcome` and duplicate-feedback prevention; direct callers can bypass both.

### AGE Cypher Queries
- `gae_state.py` has graph queries in DeploymentState helpers:
  - `write_bootstrap_state()` existence read: `MATCH (ds:DeploymentState {id: 'current'}) RETURN ds` (`app/services/gae_state.py:473-475`). No `MERGE`, `$param`, `datetime()`, `labels[0]`, list-parameter `IN`, `ON CREATE SET`, or reserved `count` alias.
  - `write_bootstrap_state()` update: `MATCH ... SET ds.bootstrap_mu = ..., ds.bootstrap_shape = ..., ds.bootstrap_stored_at = ..., ds.gae_version = ...` (`app/services/gae_state.py:477-483`). Uses property-level `SET`, not destructive `SET n = {props}`; uses `_S()` inline values.
  - `write_bootstrap_state()` create: `CREATE (ds:DeploymentState {...})` (`app/services/gae_state.py:485-493`). Uses `_S()` inline values; no `MERGE`.
  - `get_bootstrap_centroids()` read via `READ_DEPLOYMENT_STATE`: `MATCH (ds:DeploymentState {id: "current"}) RETURN ...` (`app/services/gae_state.py:443-449`, `app/services/gae_state.py:511`). No listed anti-pattern.
- `feedback.py` contains no Cypher or graph-client calls. Its comments say "graph updates," but the active code mutates in-memory dicts and returns simulated update models (`app/services/feedback.py:122-289`).
