# SOC Backend Line-by-Line Review — Part 4

## app/services/evidence_room.py (243 lines)

### Architecture
- This module builds Act 7 evidence-room payloads from the in-memory audit chain, conservation health, and graph snapshot state (`app/services/evidence_room.py:1-243`).
- It does not write graph data or GAE state directly; it aggregates evidence for summary/export routes and degrades to empty structures when upstream audit, graph snapshot, or learning-health dependencies fail (`app/services/evidence_room.py:88-239`).
- The code comments are minimal. The active behavior is fail-soft evidence collection rather than a strict evidence verifier.

### Function-by-Function Review

- **log** (line 8)
  - Purpose: Module logger.
  - Inputs: None.
  - Logic: `logging.getLogger(__name__)`.
  - Output: Logger.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: None.

- **SUMMARY_LIMIT / EXPORT_LIMIT / FORMAT_VERSION / PRODUCT_NAME / KNOWN_STATUSES** (line 10-14)
  - Purpose: Module-level evidence serialization constants.
  - Inputs: None.
  - Logic: Summary exports first 20 audit rows; full export caps at 10,000 rows; known conservation statuses are fixed.
  - Output: Constants.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Status normalization later only allows `GREEN`, `AMBER`, `RED`, `CALIBRATING`, and `UNKNOWN`.

- **_now_iso** (line 17-18)
  - Purpose: UTC timestamp helper.
  - Inputs: None.
  - Logic: Formats `datetime.now(timezone.utc)` as second-resolution `Z` timestamp.
  - Output: String timestamp.
  - Side effects: Reads current clock.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Uses UTC timezone explicitly.

- **_safe_float** (line 21-27)
  - Purpose: Defensive float coercion.
  - Inputs: Any value and default.
  - Logic: Returns default for `None`, `TypeError`, or `ValueError`; otherwise `float(value)`.
  - Output: Float.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Swallows type/value conversion errors.
  - Invariants/guards: Does not reject NaN/Inf.

- **_safe_int** (line 30-36)
  - Purpose: Defensive integer coercion.
  - Inputs: Any value and default.
  - Logic: Returns default for `None`, `TypeError`, or `ValueError`; otherwise `int(value)`.
  - Output: Int.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Swallows type/value conversion errors.
  - Invariants/guards: None.

- **_clamp_rate** (line 39-40)
  - Purpose: Clamp rate-like values to `[0, 1]`.
  - Inputs: Any numeric-like value.
  - Logic: Calls `_safe_float()` then min/max clamps.
  - Output: Float.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Conversion errors become 0.0 via `_safe_float()`.
  - Invariants/guards: Enforces rate bounds.

- **_truncate** (line 43-45)
  - Purpose: Shorten IDs/hashes for summary display.
  - Inputs: Any value and max length.
  - Logic: Converts `None` to empty string, otherwise `str(value)`, then slices.
  - Output: String.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Fixed default length of 12.

- **_json_safe** (line 48-57)
  - Purpose: Recursively convert arbitrary payload values to JSON-compatible values.
  - Inputs: Any value.
  - Logic: Recurses into dict/list/tuple/set, passes primitive values, calls `tolist()` when present, and stringifies everything else.
  - Output: JSON-serializable structure.
  - Side effects: Iterates unordered sets into list order.
  - GAE calls: None.
  - Error handling: No explicit exception handling for failing `tolist()`.
  - Invariants/guards: Dict keys are stringified.

- **_empty_audit_trail** (line 60-61)
  - Purpose: Empty fallback for audit collection.
  - Inputs: None.
  - Logic: Returns `{"entries": [], "total": 0}`.
  - Output: Dict.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: None.

- **_empty_hash_chain** (line 64-65)
  - Purpose: Empty fallback for hash-chain verification.
  - Inputs: None.
  - Logic: Returns `verified=True`, `entries=0`, `status="VERIFIED"`.
  - Output: Dict.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: No distinction between no evidence and verified evidence.

- **_empty_conservation** (line 68-75)
  - Purpose: Empty conservation fallback.
  - Inputs: None.
  - Logic: Returns unknown status, zero signal/threshold/count, and not frozen.
  - Output: Dict.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: None.

- **_empty_override_analysis** (line 78-85)
  - Purpose: Empty override-analysis fallback.
  - Inputs: None.
  - Logic: Returns zero totals and empty per-category map.
  - Output: Dict.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: None.

- **EvidenceRoomService** (line 88-239)
  - Purpose: Aggregates evidence summary/export data.
  - Inputs: Method-specific only.
  - Logic: Calls audit, conservation, and override collectors and returns JSON-safe payloads.
  - Output: Summary/export dicts.
  - Side effects: Imports runtime services lazily and can trigger audit reconstruction from memory.
  - GAE calls: Indirectly calls `LearningHealthMonitor.evaluate()`, which reads `get_learning_state()`.
  - Error handling: Collection helpers catch broad exceptions and return degraded evidence.
  - Invariants/guards: Status normalization and JSON-safety wrappers.

- **EvidenceRoomService.get_evidence_summary** (line 89-99)
  - Purpose: Build compact evidence-room summary.
  - Inputs: `self`.
  - Logic: Collects non-export audit entries, conservation status, and override analysis; adds generation timestamp.
  - Output: JSON-safe dict with `generated_at`, `audit_trail`, `conservation`, `override_analysis`, and `hash_chain`.
  - Side effects: Calls `_collect_audit(export=False)`, `_collect_conservation()`, and `_collect_override_analysis()`.
  - GAE calls: Indirect through conservation.
  - Error handling: Delegated to helper methods.
  - Invariants/guards: Summary limit is applied in `_collect_audit()`.

- **EvidenceRoomService.export_evidence_pack** (line 101-116)
  - Purpose: Build full export evidence pack.
  - Inputs: `self`.
  - Logic: Collects export-mode audit entries, conservation, override analysis, and export metadata.
  - Output: JSON-safe dict with export metadata and evidence sections.
  - Side effects: Same collectors as summary path.
  - GAE calls: Indirect through conservation.
  - Error handling: Delegated to helper methods.
  - Invariants/guards: Export metadata includes format version and product name.

- **EvidenceRoomService._collect_audit** (line 118-144)
  - Purpose: Read audit rows and hash-chain verification.
  - Inputs: `export` boolean.
  - Logic: Imports audit helpers, reconstructs memory chain, reads rows and verification result, formats up to summary/export limit, and returns raw rows for later analysis.
  - Output: `(audit_trail, hash_chain, rows)` tuple.
  - Side effects: Calls `reconstruct_from_memory()`; reads in-memory audit state.
  - GAE calls: None.
  - Error handling: Broad exception logs warning and returns empty audit trail plus `_empty_hash_chain()`.
  - Invariants/guards: Export cap 10,000; summary cap 20; chain status is `"VERIFIED"` if `verification["verified"]` is truthy or missing.

- **EvidenceRoomService._format_summary_entry** (line 146-158)
  - Purpose: Compact one audit row for summary display.
  - Inputs: Audit row dict.
  - Logic: Selects decision ID, action, category, confidence, outcome, timestamp, and truncated hash.
  - Output: Dict.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Missing keys fall back to empty strings/defaults.
  - Invariants/guards: Full decision ID is retained separately as `decision_id_full`.

- **EvidenceRoomService._format_export_entry** (line 160-171)
  - Purpose: Format one audit row for export.
  - Inputs: Audit row dict.
  - Logic: Preserves full ID/hash and chain index with action/category/confidence/outcome/timestamp.
  - Output: Dict.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Missing keys fall back to empty strings/defaults.
  - Invariants/guards: Confidence coerced to float.

- **EvidenceRoomService._collect_conservation** (line 173-207)
  - Purpose: Gather conservation health and verified-decision count.
  - Inputs: `self`.
  - Logic: Calls `LearningHealthMonitor.evaluate(neo4j_client)`; normalizes status; prefers graph snapshot verified count and falls back to learning-state decision count.
  - Output: Dict with `status`, `product`, `threshold`, `verified_decisions`, and `frozen`.
  - Side effects: Imports `neo4j_client`, learning-health monitor, graph snapshot, and GAE state lazily.
  - GAE calls: Indirect `get_learning_state()` fallback and inside learning-health evaluation.
  - Error handling: Broad exceptions log warning/debug and continue with default values.
  - Invariants/guards: Unknown statuses become `"UNKNOWN"`; numeric values go through safe coercion.

- **EvidenceRoomService._collect_override_analysis** (line 209-239)
  - Purpose: Calculate override/confirmation totals and per-category counts.
  - Inputs: Raw audit rows.
  - Logic: Counts rows, counts truthy `analyst_confirmed` as overrides, counts `outcome == "correct"` as confirmations, then overlays graph snapshot totals when no audit rows are present and always reads snapshot override rate/per-category counts when available.
  - Output: Dict with totals, override rate, and per-category counts.
  - Side effects: Reads graph snapshot state.
  - GAE calls: None.
  - Error handling: Snapshot failures are debug-logged and ignored.
  - Invariants/guards: Override rate is clamped to `[0, 1]`.

- **dumps_json_safe** (line 242-243)
  - Purpose: Serialize JSON-safe payloads for export or debugging.
  - Inputs: Payload dict.
  - Logic: Runs `_json_safe()` then `json.dumps(indent=2, sort_keys=True)`.
  - Output: JSON string.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: `json.dumps()` errors propagate.
  - Invariants/guards: Sorts keys for stable output.

### Invariants Enforced
- Summary audit output is limited to 20 entries and export output to 10,000 entries (`app/services/evidence_room.py:10-11`, `app/services/evidence_room.py:129-133`).
- Conservation status is uppercased and constrained to known status values (`app/services/evidence_room.py:14`, `app/services/evidence_room.py:184-186`).
- Rate outputs are clamped to `[0, 1]` (`app/services/evidence_room.py:39-40`, `app/services/evidence_room.py:235`).
- Numeric conversions fall back instead of raising (`app/services/evidence_room.py:21-36`).
- JSON export recursively converts unsupported values to strings or lists (`app/services/evidence_room.py:48-57`).

### Potential Issues

#### P1
- Audit collection failure returns `_empty_hash_chain()` with `verified=True` and `status="VERIFIED"` (`app/services/evidence_room.py:64-65`, `app/services/evidence_room.py:118-124`). In an Act 7 evidence surface, an unavailable audit chain can be reported as verified rather than unknown or failed.

#### P2
- Override analysis treats truthy `analyst_confirmed` as an override count (`app/services/evidence_room.py:211-212`). If that field means analyst confirmation, as the name implies, the evidence room can invert confirmation/override reporting.
- `_collect_conservation()` catches learning-health failures and returns `UNKNOWN` with zero signal/threshold (`app/services/evidence_room.py:173-207`). This keeps the UI alive but can hide broken conservation monitoring unless logs are watched.
- `_collect_audit()` slices the first rows returned by `get_decision_rows()` without sorting (`app/services/evidence_room.py:126-133`). If the audit layer does not guarantee newest-first order, summaries may show stale evidence.
- The service reads mutable in-memory audit and snapshot state without locking (`app/services/evidence_room.py:118-239`). Concurrent outcome writes can produce internally inconsistent totals, rates, and hash-chain counts.

#### P3
- `_empty_conservation()` and `_empty_override_analysis()` are defined but `_empty_conservation()` is not used by `_collect_conservation()` (`app/services/evidence_room.py:68-85`, `app/services/evidence_room.py:173-207`).
- `_safe_float()` accepts NaN/Inf and `_json_safe()` passes floats through unchanged (`app/services/evidence_room.py:21-27`, `app/services/evidence_room.py:48-57`), which can produce non-strict JSON values.
- Export format version is hardcoded in this module with no schema object or compatibility test visible here (`app/services/evidence_room.py:12`, `app/services/evidence_room.py:101-116`).

### AGE Cypher Queries
- No Cypher query strings appear directly in `evidence_room.py`.
- AGE/Cypher behavior is indirect through `LearningHealthMonitor.evaluate(neo4j_client)` (`app/services/evidence_room.py:173-181`).

### Cross-Module Dependencies
- Depends on `app.framework.audit.get_decision_rows`, `reconstruct_from_memory`, and `verify_chain` for audit rows and hash verification (`app/services/evidence_room.py:119-123`).
- Depends on `app.services.learning_health.LearningHealthMonitor.evaluate()` and `app.db.neo4j.neo4j_client` for conservation status (`app/services/evidence_room.py:176-179`).
- Depends on `app.state.graph_snapshot.get_snapshot()` for verified decision counts, override rate, correct counts, and category counts (`app/services/evidence_room.py:189-197`, `app/services/evidence_room.py:217-229`).
- Falls back to `app.services.gae_state.get_learning_state().decision_count` when graph snapshot is unavailable (`app/services/evidence_room.py:198-204`).

## app/services/learning_health.py (708 lines)

### Architecture
- This module implements conservation monitoring, auto-pause red-day counting, alert volume spike detection, category freeze detection, analyst precision weighting, and verification-rate health (`app/services/learning_health.py:1-708`).
- Tab 2 runtime evolution, Act 7 evidence, deployment gates, and feedback safety surfaces depend on it. It bridges to GAE via `gae.calibration` helpers and `get_learning_state()` (`app/services/learning_health.py:26-28`).
- Comments explicitly describe rolling conservation semantics and AGE parameter limitations in `_count_red_days()` (`app/services/learning_health.py:1-17`, `app/services/learning_health.py:251-266`), but several later queries still use named `$param` syntax.

### Function-by-Function Review

- **log** (line 31)
  - Purpose: Module logger.
  - Inputs: None.
  - Logic: `logging.getLogger(__name__)`.
  - Output: Logger.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: None.

- **CALIBRATION_DECISIONS / CALIBRATION_DAYS / AUTO_PAUSE_RED_DAYS / AUTO_PAUSE_LOOKBACK_DAYS / WINDOW_DECISIONS** (line 33-42)
  - Purpose: Conservation and rollout threshold constants.
  - Inputs: None.
  - Logic: Sets 300-decision calibration, 30-day calibration/lookback, 14 RED-day auto-pause threshold, and 50-decision rolling alpha/V window.
  - Output: Constants.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Comments state RED counting is cumulative over lookback, not consecutive.

- **LearningHealthMonitor class constants** (line 45-51)
  - Purpose: Public class-level mirror of thresholds and sigma levels.
  - Inputs: None.
  - Logic: Copies module constants and sets amber/red sigma to 2.0/3.0.
  - Output: Class constants.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: None.

- **LearningHealthMonitor._extract_components** (line 58-109)
  - Purpose: Extract `alpha`, `q`, `V`, and history count from verified update history.
  - Inputs: `history`, `window=50`, `q_window=400`.
  - Logic: Uses recent alpha_effective values, last 400 outcomes for q, and timestamp spread for V with raw-count fallback.
  - Output: Dict with numeric components and `n`.
  - Side effects: Logs debug on timestamp parsing failure.
  - GAE calls: Reads GAE WeightUpdate-like objects by attribute.
  - Error handling: Empty history returns zeros; timestamp parse errors fall back to raw count.
  - Invariants/guards: Span is floored at one minute to avoid division by zero.

- **LearningHealthMonitor._compute_signal** (line 116-118)
  - Purpose: Composite conservation signal.
  - Inputs: `alpha`, `q`, `V`.
  - Logic: Multiplies the three values.
  - Output: Float.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Numeric errors propagate.
  - Invariants/guards: None.

- **LearningHealthMonitor._build_calibration_baseline** (line 121-144)
  - Purpose: Build baseline mean/std from first 300 decisions.
  - Inputs: History list.
  - Logic: Samples every 10th point, extracts rolling components for each chunk, computes signal, then mean/std.
  - Output: `(baseline_mean, baseline_std)`.
  - Side effects: None.
  - GAE calls: Indirectly processes GAE WeightUpdate-like objects.
  - Error handling: Empty calibration window/signals return zero baseline/std.
  - Invariants/guards: Uses at most first 300 decisions.

- **LearningHealthMonitor.evaluate** (line 151-244)
  - Purpose: Main conservation-health evaluation.
  - Inputs: Optional Neo4j/AGE service.
  - Logic: Reads learning state/history, extracts components, computes theta minimum and conservation result, returns calibrating before 300 decisions, otherwise compares signal with absolute and relative floors and counts RED days.
  - Output: Dict with status, signal, theta, conservation, components, baseline, red days, auto-pause, and interpretation.
  - Side effects: Reads mutable learning state and optionally graph HealthLog nodes.
  - GAE calls: `get_learning_state()`, `compute_theta_min()`, `derive_theta_min()`, and `check_conservation()`.
  - Error handling: `compute_theta_min()` `ValueError` falls back to `derive_theta_min()`; other GAE/calibration errors propagate.
  - Invariants/guards: Calibration phase before 300 decisions; RED if conservation fails or signal drops below baseline-3sigma; AMBER below baseline-2sigma.

- **LearningHealthMonitor._count_red_days** (line 251-277)
  - Purpose: Count distinct RED days within 30-day lookback.
  - Inputs: Neo4j/AGE service or `None`.
  - Logic: Computes cutoff epoch in Python, inlines integer literal into query, returns count of distinct day buckets.
  - Output: Int red-day count.
  - Side effects: Graph read.
  - GAE calls: None.
  - Error handling: `None` client or query failure returns 0.
  - Invariants/guards: Avoids `$param` by inlining computed integer; uses `red_days` alias, not `count`.

- **LearningHealthMonitor._interpret** (line 284-302)
  - Purpose: Human-readable status explanation.
  - Inputs: Status, signal, theta minimum, red days.
  - Logic: Returns fixed strings for GREEN/AMBER/RED and generic fallback otherwise.
  - Output: String.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Auto-pause wording when red-day threshold is reached.

- **_round_comps** (line 309-310)
  - Purpose: Round float component values for API output.
  - Inputs: Component dict.
  - Logic: Rounds floats to 4 decimals, preserves non-floats.
  - Output: Dict.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: None.

- **_VOLUME_WINDOW_DAYS** (line 317)
  - Purpose: Rolling window constant for volume/category baselines.
  - Inputs: None.
  - Logic: Fixed 30 days.
  - Output: Int constant.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: None.

- **compute_volume_baseline** (line 320-383)
  - Purpose: Calculate 30-day alert-volume baseline and spike threshold.
  - Inputs: `neo4j_client`.
  - Logic: Queries daily alert counts after cutoff, computes mean/std with std floor 1.0, gets current decision count, creates `GateConfig`, and derives spike sigma/threshold.
  - Output: Dict with mean, std, threshold, sigma, window, and data point count.
  - Side effects: Graph read and learning-state read.
  - GAE calls: Indirect `get_learning_state().decision_count`.
  - Error handling: Query failures log warning and return zero baseline with std floor.
  - Invariants/guards: Std floor prevents zero-variance threshold; spike sigma comes from `GateConfig`.

- **detect_volume_spike** (line 386-424)
  - Purpose: Compare today's alert count to volume baseline.
  - Inputs: `neo4j_client`, `today_count`.
  - Logic: Calls `compute_volume_baseline()`, compares count to threshold, logs warning if exceeded.
  - Output: Dict with spike flag and baseline values.
  - Side effects: Graph read through baseline and warning log on spike.
  - GAE calls: Indirect through baseline.
  - Error handling: Baseline exceptions are handled in baseline function.
  - Invariants/guards: Strict `>` threshold.

- **_FREEZE_MULTIPLIER** (line 431)
  - Purpose: Category freeze multiplier.
  - Inputs: None.
  - Logic: Fixed 2.0.
  - Output: Float constant.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: None.

- **compute_category_baseline** (line 434-467)
  - Purpose: Compute 30-day baseline category distribution.
  - Inputs: `neo4j_client`.
  - Logic: Queries alert counts by category after cutoff, computes fractional share per category.
  - Output: Dict category -> share.
  - Side effects: Graph read.
  - GAE calls: None.
  - Error handling: Query failure logs warning and returns `{}`.
  - Invariants/guards: Returns `{}` if total is zero; rounds shares to 6 decimals.

- **detect_frozen_categories** (line 470-519)
  - Purpose: Identify categories to freeze during an active volume spike.
  - Inputs: `neo4j_client`, today's category counts.
  - Logic: Exits unless volume spike is active, computes today's shares, compares to 2x baseline share, and returns categories exceeding threshold.
  - Output: List of category names.
  - Side effects: Reads GAE state volume-spike flag and graph category baseline; logs warnings.
  - GAE calls: `is_volume_spike_active()` from `gae_state`.
  - Error handling: Baseline query errors become empty baseline; no exception for no spike/no counts.
  - Invariants/guards: No freeze without active volume spike; zero baseline skips category.

- **_MIN_ANALYST_DECISIONS / _MIN_ANALYSTS_REQUIRED** (line 526-527)
  - Purpose: Analyst precision qualification thresholds.
  - Inputs: None.
  - Logic: Requires 10 decisions per analyst and at least 2 qualifying analysts.
  - Output: Int constants.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Used to suppress sparse analyst weighting.

- **compute_analyst_precision** (line 530-569)
  - Purpose: Compute analyst precision weights from verified Decision nodes.
  - Inputs: `neo4j_client`.
  - Logic: Queries decisions grouped by verifier, filters analysts below 10 decisions, computes precision, then suppresses output unless at least two analysts qualify.
  - Output: Dict analyst -> precision.
  - Side effects: Graph read.
  - GAE calls: None.
  - Error handling: Query failure logs warning and returns `{}`.
  - Invariants/guards: Minimum decisions and minimum analyst count.

- **compute_verification_health** (line 576-708)
  - Purpose: Calculate verification coverage/drift/conservation health.
  - Inputs: `neo4j_client`.
  - Logic: Counts total and verified decisions, computes last/prior 7-day verification rates, calls `LearningHealthMonitor.evaluate()`, and maps three conditions to GREEN/AMBER/RED.
  - Output: Dict with status, coverage/drift/conservation booleans and counts.
  - Side effects: Multiple graph reads and conservation evaluation.
  - GAE calls: Indirect `get_learning_state()` via `evaluate()`.
  - Error handling: Individual graph/conservation failures are debug-logged and default to zero/UNKNOWN.
  - Invariants/guards: Coverage healthy at >=0.20; drift healthy at >=80% of prior rate; prior zero drift treated healthy; coverage zero forces RED.

### Invariants Enforced
- Empty learning history returns zero components (`app/services/learning_health.py:75-76`).
- Timestamp span for V is floored at one minute (`app/services/learning_health.py:99-100`).
- Calibration mode holds until 300 decisions (`app/services/learning_health.py:169-188`).
- RED status is selected for failed conservation or signal below baseline-3sigma; AMBER below baseline-2sigma (`app/services/learning_health.py:197-203`).
- Auto-pause activates at 14 RED days in the 30-day lookback (`app/services/learning_health.py:207-208`, `app/services/learning_health.py:291-296`).
- Volume std is floored at 1.0 before spike threshold computation (`app/services/learning_health.py:363-364`).
- Category freeze requires an active volume spike (`app/services/learning_health.py:490-492`).
- Analyst precision excludes analysts with fewer than 10 decisions and returns no weights unless at least two analysts qualify (`app/services/learning_health.py:526-569`).
- Verification coverage zero forces RED (`app/services/learning_health.py:690-695`).

### Potential Issues

#### P1
- Several functions use named `$param` query parameters despite the same file documenting that `$param` is forbidden for AGE: `compute_volume_baseline()` (`app/services/learning_health.py:344-350`), `compute_category_baseline()` (`app/services/learning_health.py:446-452`), `compute_analyst_precision()` (`app/services/learning_health.py:544-554`), and `compute_verification_health()` last/prior window queries (`app/services/learning_health.py:628-653`). These monitoring paths can fail under the AGE rules that `_count_red_days()` explicitly follows.
- `compute_volume_baseline()` silently returns a zero mean/std baseline after query failure, then floors std to 1.0 and returns a finite spike threshold of 5.0 or 3.0 depending on gate state (`app/services/learning_health.py:344-375`). A broken graph query can therefore make spike detection compare live traffic against a synthetic low threshold.

#### P2
- `LearningHealthMonitor.evaluate()` reads mutable learning-state history without locking or snapshot copy before deriving alpha/q/V and baseline (`app/services/learning_health.py:151-244`). Concurrent updates can produce mixed-window health results.
- `_count_red_days()` returns 0 on query failure, disabling auto-pause even if HealthLog access is broken (`app/services/learning_health.py:251-277`).
- Calibration baseline can have zero standard deviation; then AMBER/RED relative thresholds collapse to the same baseline value (`app/services/learning_health.py:121-144`, `app/services/learning_health.py:197-203`).
- `compute_verification_health()` defaults conservation status to `UNKNOWN` and treats `UNKNOWN` as healthy (`app/services/learning_health.py:671-680`). A conservation-monitor failure can improve the health rollup.
- The total/verified decision queries return aliases `total` and `verified` instead of `cnt`; the standing AGE guidance explicitly says to avoid `count as alias` and use `cnt` (`app/services/learning_health.py:600-615`).
- `count(CASE WHEN ...)` is used for conditional verification counts (`app/services/learning_health.py:633-635`, `app/services/learning_health.py:650-652`); AGE support for this syntax should be verified because no fallback query is provided.

#### P3
- `Optional` is imported but not used (`app/services/learning_health.py:24`).
- `compute_theta_min` is imported from GAE and `GateConfig.compute_theta_min` also exists in SOC config, so the name can confuse readers about which theta formula is active (`app/services/learning_health.py:26`, `app/domains/soc/config.py:782-795`).
- The module docstring references `docs/project_status_and_plan_v3_part2.md P9` but the review did not verify that doc as part of this backend-source pass (`app/services/learning_health.py:1-17`).

### AGE Cypher Queries
- `_count_red_days()` uses inline integer cutoff and `RETURN count(DISTINCT (...)) AS red_days` (`app/services/learning_health.py:266-273`). It avoids `$param`; alias is not `count`; no `datetime()`, `labels[0]`, `ON CREATE SET`, `ON MATCH SET`, or list-parameter `IN`.
- `compute_volume_baseline()` uses `$cutoff_epoch` and a parameter dict (`app/services/learning_health.py:344-351`). This violates the no-`$param` AGE rule.
- `compute_category_baseline()` uses `$cutoff_epoch` and a parameter dict (`app/services/learning_health.py:446-453`). This violates the no-`$param` AGE rule.
- `compute_analyst_precision()` uses `$min_decisions` and a parameter dict (`app/services/learning_health.py:544-555`). This violates the no-`$param` AGE rule.
- `compute_verification_health()` total/verified count queries use no params but return aliases `total` and `verified` (`app/services/learning_health.py:600-615`), which diverges from the standing `cnt` alias convention.
- `compute_verification_health()` last/prior 7-day queries use `$last_start`, `$now`, and `$prior_start` parameter dicts (`app/services/learning_health.py:628-654`). These violate the no-`$param` AGE rule.
- No `ON CREATE SET`, `ON MATCH SET`, `datetime()`, `labels[0]`, or list-parameter `IN` patterns appear in this file.

### Cross-Module Dependencies
- GAE dependency: `gae.calibration.compute_theta_min`, `derive_theta_min`, and `check_conservation` (`app/services/learning_health.py:26`).
- GAE state dependency: `app.services.gae_state.get_learning_state()` for history/decision count and `is_volume_spike_active()` for category freeze gating (`app/services/learning_health.py:28`, `app/services/learning_health.py:490`).
- SOC config dependency: `GateConfig` drives spike sigma based on current decision count (`app/services/learning_health.py:340-341`, `app/services/learning_health.py:371-373`).
- Graph dependency: caller-supplied `neo4j_client` must support `run_query()` with the query/parameter style used in each helper.
- Evidence dependency: `EvidenceRoomService._collect_conservation()` calls `LearningHealthMonitor.evaluate()` and exposes its output (`app/services/evidence_room.py:173-207`).

## app/graph_schema.py (819 lines)

### Architecture
- This module is the declared single source of truth for SOC graph structure, seed data loading, health verification, and CLI seed/verify commands (`app/graph_schema.py:1-32`).
- It is intentionally allowed to perform destructive seed cleanup for controlled labels/origins, unlike runtime request paths (`app/graph_schema.py:20-27`, `app/graph_schema.py:420-773`).
- It bridges to `ci_platform.graph.get_graph_client()` when no client is provided and uses `_S()` for AGE-safe inline literals (`app/graph_schema.py:46-69`, `app/graph_schema.py:210-221`, `app/graph_schema.py:420-431`).

### Function-by-Function Review

- **log** (line 35)
  - Purpose: Module logger.
  - Inputs: None.
  - Logic: `logging.getLogger(__name__)`.
  - Output: Logger.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: None.

- **SYNTHETIC_ORIGIN / DEMO_ORIGIN** (line 38-39)
  - Purpose: Origin labels for protected training data and resettable demo alerts.
  - Inputs: None.
  - Logic: Static string constants.
  - Output: Constants.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Comments define ownership semantics.

- **_S** (line 46-69)
  - Purpose: Serialize Python values into inline AGE Cypher literals.
  - Inputs: Any scalar/list/tuple/numpy-like value.
  - Logic: Emits `null`, lowercase booleans, numeric strings, JSON-string-encoded list/tuple/numpy arrays, and escaped quoted strings; rejects NaN/Inf.
  - Output: Cypher literal string.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Raises `ValueError` for NaN/Inf.
  - Invariants/guards: Avoids AGE array properties by storing lists as JSON strings; escapes backslashes and single quotes.

- **GRAPH_CONTRACT** (line 76-195)
  - Purpose: Declarative graph-node/edge/invariant contract.
  - Inputs: None.
  - Logic: Defines required node labels, min counts, required/optional fields, edge counts/endpoints, and invariant query strings.
  - Output: Dict constant.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Verification code later consumes these required fields and count thresholds.

- **_BACKBONE_LABELS / _DATA_LABELS / _DATA_ORIGINS** (line 200-203)
  - Purpose: Clean-phase label/origin allowlists.
  - Inputs: None.
  - Logic: Backbone labels are fully owned and deleted wholesale; Decision/Alert are deleted only for synthetic/demo origins.
  - Output: Lists.
  - Side effects: None at import.
  - GAE calls: None.
  - Error handling: None.
  - Invariants/guards: Intended to constrain destructive seed cleanup.

- **verify_graph** (line 210-356)
  - Purpose: Validate the live graph against `GRAPH_CONTRACT`.
  - Inputs: Optional client.
  - Logic: Lazily obtains graph client, checks node counts and sample fields, edge counts and endpoint labels, then invariant queries.
  - Output: Report dict with `healthy`, `issues`, `warnings`, and `counts`.
  - Side effects: Sets default `GRAPH_BACKEND=age` if no client is supplied; graph reads.
  - GAE calls: None.
  - Error handling: Count/sample/edge/invariant query failures are captured as issues or warnings.
  - Invariants/guards: Counts always populated; missing required fields mark unhealthy; unexpected fields become warnings.

- **_validate_json** (line 363-413)
  - Purpose: Validate seed JSON before graph mutation.
  - Inputs: Parsed JSON dict.
  - Logic: Checks top-level sections, required fields on first three items in each section, decision-alert references, and campaign-alert references.
  - Output: None on success.
  - Side effects: None.
  - GAE calls: None.
  - Error handling: Raises `ValueError` with accumulated errors.
  - Invariants/guards: Only samples first three items for field validation; referential checks cover all decisions and campaign alert IDs.

- **seed_graph** (line 420-773)
  - Purpose: Load and optionally clean/recreate the complete SOC graph from v5 JSON.
  - Inputs: `json_path`, `clean=False`, optional client.
  - Logic: Gets graph client, loads/validates JSON, optionally deletes owned labels/origins, creates nodes, creates relationships, creates training decisions with `DECIDED_ON` edges atomically, then runs `verify_graph()`.
  - Output: Verification report.
  - Side effects: Reads JSON file, prints progress, mutates graph extensively, can delete graph nodes when `clean=True`, sets `GRAPH_BACKEND=age`, and calls `client.ensure_graph()`.
  - GAE calls: None.
  - Error handling: JSON validation fails before mutation; many edge/decision creation errors are logged/count-tracked and seeding continues; verification result is returned even if unhealthy.
  - Invariants/guards: Decision + `DECIDED_ON` edge are created in one query; seed lists are serialized through `_S()`.

- **CLI entry point** (line 780-819)
  - Purpose: Support `python -m app.graph_schema verify` and `seed`.
  - Inputs: `sys.argv`.
  - Logic: Sets graph backend and Python path, validates command, adjusts Windows event-loop policy, runs verify/seed, and exits nonzero on unhealthy/not found cases.
  - Output: Console output and process exit code.
  - Side effects: Mutates `os.environ`, `sys.path`, event loop policy, and graph state for seed command.
  - GAE calls: None.
  - Error handling: Bad usage or missing file exits 1; unhealthy verify/seed exits 1.
  - Invariants/guards: Seed defaults to `support/setup/zero_day_decisions_v5.json`.

### Invariants Enforced
- `_S()` rejects NaN/Inf and serializes lists as JSON strings to avoid AGE array properties (`app/graph_schema.py:46-69`).
- `verify_graph()` enforces minimum counts for labels and edge types from `GRAPH_CONTRACT` (`app/graph_schema.py:224-244`, `app/graph_schema.py:288-307`).
- `verify_graph()` samples synthetic-origin nodes for required fields and flags unexpected fields as warnings (`app/graph_schema.py:247-282`).
- `verify_graph()` checks declared edge endpoint labels when edges exist (`app/graph_schema.py:310-327`).
- Contract invariants enforce no orphan decisions, no missing synthetic outcomes, pending demo alert presence, non-null decision categories, and seeded alerts with users/assets (`app/graph_schema.py:145-195`, `app/graph_schema.py:331-356`).
- `_validate_json()` raises before graph mutation when required top-level keys, sampled required fields, or referential integrity checks fail (`app/graph_schema.py:363-413`).
- `seed_graph()` keeps session decisions with `origin=NULL` during clean, according to comments and query filters (`app/graph_schema.py:446-494`).
- Training decisions and `DECIDED_ON` edges are created atomically in one query (`app/graph_schema.py:725-750`).

### Potential Issues

#### P1
- `seed_graph(clean=True)` deletes all nodes for `_BACKBONE_LABELS` without origin filtering (`app/graph_schema.py:446-482`). The comments say these labels are fully owned, but if runtime campaign correlation or non-seed data also writes `User`, `Asset`, `Campaign`, `ThreatIndicator`, or `AttackPattern`, a seed clean can destroy non-seed graph data.
- `_validate_json()` checks required fields only on the first three items of each section (`app/graph_schema.py:377-392`). Later malformed rows can pass validation and then fail mid-seed, leaving a partially rebuilt graph after the clean phase.
- `seed_graph()` continues after edge and decision creation failures, then returns the verification report rather than rolling back (`app/graph_schema.py:603-756`). With `clean=True`, a partially seeded graph can remain live after failures.

#### P2
- `verify_graph()` samples only one synthetic-origin node per label for required field presence (`app/graph_schema.py:247-282`). It can report healthy while most nodes of that label are missing required fields.
- `seed_graph(clean=False)` always uses `CREATE` and comments acknowledge it duplicates data if run twice (`app/graph_schema.py:420-427`). There is no duplicate-detection guard before non-clean seeding.
- `GRAPH_CONTRACT["Decision"]["required_fields"]` includes `factor_vector` but the seed path serializes list values to JSON strings via `_S()` (`app/graph_schema.py:83-86`, `app/graph_schema.py:735-738`). Consumers expecting a list must parse the string consistently.
- Clean-phase deletion of `Decision`/`Alert` is scoped by origin, but verification count requirements include all nodes with the label (`app/graph_schema.py:224-244`, `app/graph_schema.py:486-494`). Existing session decisions can affect health counts and warnings.
- CLI mutates `sys.path` using `os.path.join(os.path.dirname(__file__), "..")` (`app/graph_schema.py:785`). When run from unusual working directories, module resolution may differ from the package runtime.

#### P3
- The module docstring says "Three public symbols" but several module constants and CLI behavior are also operationally significant (`app/graph_schema.py:1-32`, `app/graph_schema.py:38-203`, `app/graph_schema.py:780-819`).
- `_validate_json()` does not validate field types, numeric ranges, category/action vocabularies, or factor-vector length (`app/graph_schema.py:363-413`).
- Progress output uses `print()` throughout `seed_graph()` instead of structured logging (`app/graph_schema.py:433-771`).
- `verify_graph()` treats unexpected fields as warnings based on a single sampled node, which can be noisy when data evolves intentionally (`app/graph_schema.py:268-275`).

### AGE Cypher Queries
- `GRAPH_CONTRACT` invariant queries use `count(...) AS n` and inline origin constants (`app/graph_schema.py:145-195`). They do not use `$param`, `datetime()`, `labels[0]`, `ON CREATE SET`, or `ON MATCH SET`.
- `verify_graph()` node and edge counts use `RETURN count(...) AS cnt` (`app/graph_schema.py:224-227`, `app/graph_schema.py:288-291`, `app/graph_schema.py:314-317`). This follows the `cnt` alias convention.
- `verify_graph()` sample query inlines `_S(SYNTHETIC_ORIGIN)` (`app/graph_schema.py:247-250`). No named params.
- `seed_graph(clean=True)` uses `DETACH DELETE` for backbone labels and scoped Decision/Alert origins (`app/graph_schema.py:476-494`). This is a destructive query by design and is explicitly documented as special-case seed behavior.
- Seed node/edge creation uses `CREATE`, `MATCH`, and inline `_S()` literals throughout phases 2-8 (`app/graph_schema.py:515-750`). No `MERGE`, named `$param`, `ON CREATE SET`, `ON MATCH SET`, `datetime()`, `labels[0]`, or list-parameter `IN` appears.
- `_S()` serializes list-like values as JSON strings, avoiding AGE array properties but requiring consumers to parse strings for fields such as `category_sequence` and `factor_vector` (`app/graph_schema.py:57-62`, `app/graph_schema.py:549-554`, `app/graph_schema.py:735-738`).
- No APOC calls appear in this file.

### Cross-Module Dependencies
- Depends on `ci_platform.graph.get_graph_client()` when no graph client is injected (`app/graph_schema.py:216-221`, `app/graph_schema.py:426-431`).
- `conftest.py` and the CLI depend on `verify_graph()` according to the module docstring (`app/graph_schema.py:8-18`).
- Tests around destructive decision queries must allowlist this file because seed clean uses `DETACH DELETE` (`app/graph_schema.py:20-27`).
- Factor and triage paths depend on seeded relationships such as `INVOLVES`, `DETECTED_ON`, `CLASSIFIED_AS`, `HAS_INDICATOR`, `MEMBER_OF`, and `DECIDED_ON` (`app/graph_schema.py:583-750`).
- Runtime W2/feedback paths depend on Decision fields and `TRIGGERED_EVOLUTION` edges, but this seed path only declares a zero-min-count `TRIGGERED_EVOLUTION` contract and does not create evolution events (`app/graph_schema.py:139`, `app/graph_schema.py:76-195`, `app/graph_schema.py:725-750`).
