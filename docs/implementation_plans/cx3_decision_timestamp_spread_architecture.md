# CX3 Decision Timestamp Spread — Architecture & Implementation Plan

## 1. Executive Summary

Root cause: the audit/Evidence Room reader is preserving AGE `Decision.timestamp_epoch` values correctly, so identical audit timestamps come from graph data or an existing repair/seed path, not from frontend formatting. `rebuild_from_age()` reads `d.timestamp_epoch`, converts it from milliseconds to ISO, and passes it into `_LEDGER.append(..., timestamp=ts_iso)` (`backend/app/framework/audit.py:293-342`). Evidence Room then includes the row timestamp in each audit entry (`backend/app/services/evidence_room.py:118-158`).

The durable source of the 4,860 training decisions is the zero-day seed population. The graph-schema seed CLI defaults to `support/setup/zero_day_decisions_v5.json` (`backend/app/graph_schema.py:811-821`), and that fixture declares `total_decisions: 4860` (`backend/support/setup/zero_day_decisions_v5.json:2-8`). The on-disk v5 fixture is not fully collapsed to one timestamp because it contains historical examples at `1741046400000` and `1748736000000` (`backend/support/setup/zero_day_decisions_v5.json:8727-8728`, `backend/support/setup/zero_day_decisions_v5.json:110766-110767`). However, the v5 generator copies v4 decisions without timestamp normalization (`backend/support/setup/enrich_zero_day_v5.py:398-430`) and its validation gates do not check timestamp span or uniqueness (`backend/support/setup/enrich_zero_day_v5.py:453-486`).

Recommended fix: create a new dedicated operator script at `backend/support/setup/repair_zero_day_timestamps.py`, default it to dry-run, require explicit `--apply`, and target only `Decision` nodes with `origin='zero_day_synthetic'`. The script should update only `timestamp_epoch` and `verified_at_epoch`, preserve every node and relationship, avoid `DELETE`, `MERGE`, full-map `SET`, and `$params`, and use historical 2025 timestamps rather than `now - 90 days`.

Implementation also must stop automatic timestamp mutation at startup. Current startup imports and awaits `backfill_decision_timestamps()` (`backend/app/main.py:317-326`), and the existing service assigns timestamps across `now - 90 days` through `now` (`backend/app/services/timestamp_backfill.py:53-67`). That behavior conflicts with the historical, operator-controlled repair strategy. Do not reuse `backend/app/services/timestamp_backfill.py` as the repair CLI unless it is substantially refactored and no longer runs as an apply-mode startup side effect.

GO/NO-GO for implementation: GO, with one mandatory constraint: the implementation prompt must include removal or disabling of the startup apply call in `backend/app/main.py`. NO-GO for adding only a new script while leaving startup `backfill_decision_timestamps()` active.

## 2. Source of 4,860 Decision Nodes

| Item | Finding | Evidence | Notes |
|---|---|---|---|
| Protected origin | Training data uses `zero_day_synthetic`, which CLAUDE marks as 4,860 protected decisions and 540 alerts. | `CLAUDE.md:82-88`, `CLAUDE.md:146-160` | Repair must not delete this population. |
| Graph-schema seed file | `python -m app.graph_schema seed` defaults to `support/setup/zero_day_decisions_v5.json`. | `backend/app/graph_schema.py:811-821` | `--file=` can override the fixture. |
| Fixture count | v5 fixture declares 4,860 decisions. | `backend/support/setup/zero_day_decisions_v5.json:2-8` | This is the expected zero-day decision population. |
| Legacy/manual seed file | `backend/support/setup/seed_zero_day.py` defaults to `zero_day_decisions.json`, not v5, unless `--file=` is passed. | `backend/support/setup/seed_zero_day.py:32-48` | The plan must distinguish the graph-schema v5 seed path from this manual legacy/default path. |
| v5 source generator | `enrich_zero_day_v5.py` reads v4 and writes v5. | `backend/support/setup/enrich_zero_day_v5.py:1-18` | Future source hardening belongs here rather than in display code. |
| Decision timestamp write | Graph-schema seeding writes `timestamp_epoch` from each decision record into `Decision`. | `backend/app/graph_schema.py:731-752` | The manual seed script also writes `timestamp_epoch` from each decision record (`backend/support/setup/seed_zero_day.py:129-143`). |
| Origin write | Graph-schema seeding writes `origin: zero_day_synthetic` on each seeded `Decision`. | `backend/app/graph_schema.py:38`, `backend/app/graph_schema.py:747-749` | This is the repair target predicate. |
| Alert timestamp write | Graph-schema seeding writes `timestamp_epoch` on seeded `Alert` nodes from the fixture. | `backend/app/graph_schema.py:584-600` | Repair can use linked Alert timestamps as anchors. |
| DECIDED_ON creation | Graph-schema seeding atomically creates `(dd:Decision {...})-[:DECIDED_ON]->(a)`. | `backend/app/graph_schema.py:731-752` | Manual seed creates the same relationship shape (`backend/support/setup/seed_zero_day.py:129-143`). |
| v5 timestamp source gap | v5 copies v4 decisions and mutates `user_id`; it does not normalize timestamps. | `backend/support/setup/enrich_zero_day_v5.py:398-430` | Add timestamp normalization before write. |
| v5 validation gap | v5 validation checks count, required fields, factor vectors, action/category validity, orphan decision refs, and correct rate, but not timestamp spread. | `backend/support/setup/enrich_zero_day_v5.py:453-486` | Add spread/uniqueness validation gates. |
| Existing v5 range examples | v5 includes at least one decision timestamp at `1741046400000` and one at `1748736000000`. | `backend/support/setup/zero_day_decisions_v5.json:8727-8728`, `backend/support/setup/zero_day_decisions_v5.json:110766-110767` | The live all-equal graph state was not verified here because graph mutation/query operations were out of scope. |

## 3. Current Seed and Reseed Semantics

Startup does not auto-seed the zero-day decisions. `main.py` explicitly retires the old bootstrap Decision writer and states that `seed_zero_day.py` handles Decision seeding outside startup (`backend/app/main.py:252-258`). Startup does rebuild the audit ledger from AGE (`backend/app/main.py:308-315`) and currently runs timestamp backfill afterward (`backend/app/main.py:317-326`).

Graph-schema seeding is manual and has two modes. `seed_graph(clean=False)` creates without deleting and is documented to duplicate data if run twice; `seed_graph(clean=True)` deletes controlled backbone nodes plus seeded Decision/Alert origins before recreating (`backend/app/graph_schema.py:420-427`, `backend/app/graph_schema.py:466-496`). Therefore non-clean reseed is not safe on a populated graph, and clean reseed is destructive for seeded graph data.

The manual `seed_zero_day.py` path supports `--dry-run` and `--live [--clean]` (`backend/support/setup/seed_zero_day.py:1-8`). Without `--clean`, it warns if synthetic alerts already exist but does not automatically skip (`backend/support/setup/seed_zero_day.py:105-109`). With `--clean`, it deletes existing `zero_day_synthetic` Decision and Alert nodes (`backend/support/setup/seed_zero_day.py:95-103`).

Admin and metrics reset/reseed paths do not provide a safe timestamp repair path. The admin reset endpoint calls `StateManager.soft_reset()` or `StateManager.hard_reset()` (`backend/app/routers/admin.py:82-136`). StateManager preserves `zero_day_synthetic` training decisions during session deletion and hard reset (`backend/app/services/state_manager.py:48-53`, `backend/app/services/state_manager.py:113-125`, `backend/app/services/state_manager.py:198-247`). Metrics demo seed/reseed endpoints are blocked and direct operators to manual seeding (`backend/app/routers/metrics.py:321-329`, `backend/app/routers/metrics.py:395-413`).

Repair-in-place is safer than destructive reseed because the required change is property-only on existing Decision nodes. A correct repair only sets `d.timestamp_epoch` and `d.verified_at_epoch`; it does not delete, recreate, or relink nodes. This preserves the seeded `DECIDED_ON` relationships created by the seed path (`backend/app/graph_schema.py:731-752`).

## 4. Downstream Dependency Assessment

| Consumer | Safe / Breaks / Needs Guard | Evidence | Rationale | Mitigation |
|---|---|---|---|---|
| Campaign temporal correlation | Needs guard against current-time synthetic data | Campaign queries use `Decision.timestamp_epoch` in time windows and ordering (`backend/app/domains/soc/campaigns.py:105-157`). `fetch_all_events()` excludes seed artifacts with `source_id <> 'synthetic'` (`backend/app/domains/soc/campaigns.py:524-547`), but `fetch_recent_events()` filters only by recent `d.timestamp_epoch` (`backend/app/domains/soc/campaigns.py:552-570`), and `check_alert()` uses that recent fetch (`backend/app/domains/soc/campaigns.py:739-765`). | Historical 2025 timestamps stay outside recent live campaign windows. Current-time synthetic timestamps can pollute `fetch_recent_events()` because that path does not exclude synthetic origin/source. | Keep repaired zero-day timestamps historical. Add a campaign synthetic exclusion only if a future design intentionally moves synthetic timestamps near now. |
| Alert/Decision timing and `DECIDED_ON` | Safe if repair preserves edges and anchors to alert day when possible | Seeded Alerts get `timestamp_epoch` from fixture (`backend/app/graph_schema.py:584-600`). Decisions are linked to Alerts through `DECIDED_ON` (`backend/app/graph_schema.py:731-752`). MTTD computes `d.timestamp_epoch - a.created_at_epoch` when Alert `created_at_epoch` exists (`backend/app/routers/metrics.py:657-660`). | Updating only Decision timestamps preserves edges. Deriving Decision timestamps from linked Alert timestamps when available reduces risk of strange Decision-vs-Alert timing. | Query `Decision` with optional linked `Alert.timestamp_epoch`; use linked alert day as anchor when it is inside the 2025 seed window, otherwise use deterministic 90-day ordinal distribution. |
| Conservation q-window | Safe | `LearningHealthMonitor.evaluate()` uses `get_learning_state().history` and `_extract_components(history)` (`backend/app/services/learning_health.py:150-179`). `_extract_components()` estimates `V` from in-memory history timestamps, not AGE Decision timestamps (`backend/app/services/learning_health.py:57-109`). | Repairing AGE Decision timestamps does not alter the conservation product path. | No conservation code change required. |
| Verification health and metrics | Needs historical verified timestamps | Verification health counts `d.outcome IS NOT NULL AND d.verified_at_epoch IS NOT NULL` and uses current 7-day windows on `d.timestamp_epoch` (`backend/app/services/learning_health.py:580-665`). MTTR uses `verified_at_epoch - timestamp_epoch` (`backend/app/routers/metrics.py:687-690`). | Adding `verified_at_epoch` improves verification/MTTR realism, but current-time synthetic timestamps would change recent verification health. | Add historical `verified_at_epoch = timestamp_epoch + 1h..48h`; do not use wall-clock current timestamps. |
| AE-DRIFT | Safe only with historical `verified_at_epoch` | Drift constants are 14-day windows, 3.0pp decline, and minimum 10 decisions (`backend/app/services/variant_generator.py:352-354`). The helper uses wall-clock `time.time() * 1000` (`backend/app/services/variant_generator.py:394-397`) and filters by `d.verified_at_epoch` in recent/prior windows (`backend/app/services/variant_generator.py:399-416`). | Historical 2025 verification timestamps are outside current 14-day windows. Current or recent verification timestamps can make synthetic data eligible for drift detection. | No AE-DRIFT origin guard is needed if repair stays historical. If a future repair uses current timestamps, add `d.origin <> 'zero_day_synthetic'` to both drift queries first. |
| Audit rebuild / Evidence Room | Safe after source repair | `rebuild_from_age()` reads `DECIDED_ON` Decisions, orders by `d.timestamp_epoch`, converts ms to ISO, and appends the timestamp (`backend/app/framework/audit.py:293-342`). Evidence Room audit entries expose that timestamp (`backend/app/services/evidence_room.py:118-158`). | The reader is doing the right thing; repairing source timestamps fixes the visible audit trail. | Repair graph properties and regenerate/fix seed source; do not mask in Evidence Room. |

## 5. AE-DRIFT Interaction Verdict

AE-DRIFT uses `verified_at_epoch`, not `timestamp_epoch`, as the rolling-window field. `_get_per_category_accuracy_trends()` computes `now_ms`, `recent_cutoff`, and `prior_cutoff` from wall-clock `time.time()` (`backend/app/services/variant_generator.py:394-397`). Its recent and prior queries require `d.verified_at_epoch` to fall inside those wall-clock windows (`backend/app/services/variant_generator.py:399-416`). It then requires the category to appear in both windows, requires each window to have at least `MIN_DRIFT_DECISIONS = 10`, and only includes declines at or above `DECLINE_THRESHOLD_PP = 3.0` (`backend/app/services/variant_generator.py:352-354`, `backend/app/services/variant_generator.py:428-445`).

Implementation-ready decision: add `verified_at_epoch`, but only as a historical value derived from the repaired `timestamp_epoch`. The exact policy is:

- `verified_at_epoch = timestamp_epoch + deterministic_delay_ms`.
- `deterministic_delay_ms` must be between 1 hour and 48 hours.
- Both `timestamp_epoch` and `verified_at_epoch` must remain inside, or immediately after, the 2025 seed window, not a current wall-clock window.

On 2026-05-05, historical 2025 `verified_at_epoch` values do not fall inside AE-DRIFT’s current recent/prior 14-day windows. Therefore no AE-DRIFT origin guard is required for the recommended historical repair. The existing `timestamp_backfill.py` wall-clock approach is not acceptable for the final design because it uses `now_ms = int(time.time() * 1000)` and `start_ms = now_ms - _90_DAYS_MS` (`backend/app/services/timestamp_backfill.py:53-67`). If future work intentionally uses current-window synthetic verification timestamps, add `d.origin <> 'zero_day_synthetic'` to the AE-DRIFT recent and prior queries before applying that change.

## 6. Recommended Fix Architecture

Chosen repair path: create a new dedicated script, `backend/support/setup/repair_zero_day_timestamps.py`.

Do not reuse `backend/app/services/timestamp_backfill.py` as-is. It is an app service, is currently called during startup (`backend/app/main.py:317-326`), has no dry-run/apply operator boundary, uses a current wall-clock 90-day window (`backend/app/services/timestamp_backfill.py:53-67`), does not set `verified_at_epoch`, and its apply query matches only by `decision_id` rather than guarding with `origin='zero_day_synthetic'` (`backend/app/services/timestamp_backfill.py:64-67`). The implementation should remove or disable the startup apply call in `backend/app/main.py`; it can leave `timestamp_backfill.py` unused or replace it with a no-write diagnostic helper, but the canonical repair should be the support/setup script.

Exact target predicate:

```cypher
MATCH (d:Decision)
WHERE d.origin = 'zero_day_synthetic'
```

Every apply query must include both `d.origin = 'zero_day_synthetic'` and the specific `d.decision_id`. This protects session decisions and aligns with the repository’s protected origin contract (`CLAUDE.md:82-88`, `backend/app/services/state_manager.py:48-53`).

Exact timestamp algorithm:

1. Query rows:
   - `d.decision_id`
   - `d.category`
   - `d.timestamp_epoch AS decision_ts`
   - optional linked `a.timestamp_epoch AS alert_ts`
2. Sort rows by `(base_anchor_ts, category, decision_id)`.
3. For each row, choose `day_start`:
   - If linked `alert_ts` exists and is inside `[1741046400000, 1748736000000]`, use the day of `alert_ts`.
   - Else if `decision_ts` exists and is inside `[1741046400000, 1748736000000]`, use the day of `decision_ts`.
   - Else distribute by ordinal across the 90-day window from `1741046400000` to `1748736000000`.
4. Add a deterministic intra-day business-hours offset: `08:00:00` through `18:00:00` UTC.
5. Derive the offset from a stable SHA-256 hash of `decision_id` and ordinal.
6. Set `verified_at_epoch` to the new `timestamp_epoch` plus a deterministic 1h..48h delay.
7. Clamp `timestamp_epoch` to the 2025 seed window. `verified_at_epoch` may extend up to 48h after the last decision timestamp, but must not be generated from current time.

Exact idempotency criteria:

- Dry-run and apply stats include:
  - `count`
  - `unique_ts`
  - `min_ts`
  - `max_ts`
  - `span_days`
  - `missing_verified_at_epoch`
  - `orphan_decisions_without_decided_on`
  - `would_update`
- Apply skips when:
  - `count == 0`, or
  - `unique_ts >= 4000`, `span_days >= 80`, `missing_verified_at_epoch == 0`, and orphan count is reported as zero.
- Apply must not skip merely because span is greater than one day. The current backfill service skips on `max_ts - min_ts > _1_DAY_MS` (`backend/app/services/timestamp_backfill.py:38-42`), which misses a daily-bucketed 90-day source.

AGE query safety:

- No `MERGE`; AGE does not implement it and the repo contract forbids it (`CLAUDE.md:107-110`).
- No `$params`; use `_S()` or a serializer for inline values (`CLAUDE.md:25-26`, `CLAUDE.md:112-127`).
- No full-map `SET d = {...}`; only explicit property assignments (`CLAUDE.md:118-121`).
- No `DELETE` or `DETACH DELETE`; Decision training data is protected (`CLAUDE.md:146-160`).

Seed-source hardening:

- Add timestamp normalization and validation to `backend/support/setup/enrich_zero_day_v5.py` because it creates v5 from v4 (`backend/support/setup/enrich_zero_day_v5.py:1-18`) and currently copies decisions without timestamp normalization (`backend/support/setup/enrich_zero_day_v5.py:398-430`).
- Regenerate `backend/support/setup/zero_day_decisions_v5.json` after the generator change.
- Keep `backend/app/graph_schema.py` seeding as a writer of fixture values; it already writes `timestamp_epoch` from JSON (`backend/app/graph_schema.py:731-752`).

## 7. Detailed Implementation Plan

| File | Change | Rationale | Risk | Tests |
|---|---|---|---|---|
| `backend/support/setup/repair_zero_day_timestamps.py` | New dry-run/apply repair script with pure helpers for stats, deterministic assignment, query construction, and apply. | A dedicated operator script avoids startup side effects and follows the manual seed-script pattern (`backend/support/setup/seed_zero_day.py:1-8`). | Medium only when `--apply` is used. | Dry-run no-write, apply query origin guard, no forbidden Cypher, idempotency, historical timestamps, verified delay. |
| `backend/app/main.py` | Remove or disable the startup call to `backfill_decision_timestamps()`; optionally replace with no-write diagnostics only. | Startup currently runs apply-mode timestamp mutation (`backend/app/main.py:317-326`). | Medium: startup behavior changes, but removes unsafe graph mutation. | Test or static assertion that startup no longer imports/calls apply repair. |
| `backend/support/setup/enrich_zero_day_v5.py` | Add deterministic timestamp normalization and validation gates before writing v5. | v5 currently copies decisions without timestamp normalization and lacks spread validation (`backend/support/setup/enrich_zero_day_v5.py:398-430`, `backend/support/setup/enrich_zero_day_v5.py:453-486`). | Low-medium: changes generated fixture semantics. | Deterministic spread, span >= 80 days, unique >= 4000, valid categories/actions still pass. |
| `backend/support/setup/zero_day_decisions_v5.json` | Regenerate fixture from the updated generator. | Graph-schema seed writes JSON values as-is (`backend/app/graph_schema.py:731-752`). | Low if generator tests pass. | Fixture load test. |
| `backend/tests/test_zero_day_timestamp_spread.py` | New focused tests for repair helpers and fixture/generator behavior. | Existing validation does not cover timestamp spread (`backend/support/setup/enrich_zero_day_v5.py:453-486`). | Low. | All cases listed in Section 9. |
| `backend/app/services/timestamp_backfill.py` | Prefer no change except possible deprecation comment if allowed; do not use it as canonical repair. | Existing service is unsafe as final repair due to startup call and wall-clock behavior (`backend/app/services/timestamp_backfill.py:18-71`). | Low if left unused. | Covered indirectly by startup no-call test. |
| `backend/app/services/variant_generator.py` | No change under the recommended historical repair. | AE-DRIFT only needs an origin guard if synthetic verified timestamps move into current windows (`backend/app/services/variant_generator.py:394-416`). | None. | Test historical repaired rows do not enter current drift windows. |

Pseudocode: timestamp generation

```python
SEED_START_MS = 1741046400000  # 2025-03-04T00:00:00Z, from v5 source examples
SEED_END_MS = 1748736000000    # 2025-06-01T00:00:00Z, from v5 source examples
DAY_MS = 86_400_000
WORK_START_MS = 8 * 3_600_000
WORK_SPAN_MS = 10 * 3_600_000
MIN_VERIFY_DELAY_MS = 3_600_000
MAX_VERIFY_DELAY_MS = 48 * 3_600_000

def stable_int(*parts: str) -> int:
    digest = sha256(":".join(parts).encode("utf-8")).hexdigest()
    return int(digest[:12], 16)

def day_start_from_anchor(row: dict, ordinal: int, total: int) -> int:
    for key in ("alert_ts", "decision_ts"):
        value = row.get(key)
        if value is not None:
            ts = int(value)
            if SEED_START_MS <= ts <= SEED_END_MS:
                return (ts // DAY_MS) * DAY_MS
    span = SEED_END_MS - SEED_START_MS
    distributed = SEED_START_MS + (ordinal * span // max(total - 1, 1))
    return (distributed // DAY_MS) * DAY_MS

def assign_timestamps(row: dict, ordinal: int, total: int) -> tuple[int, int]:
    day_start = day_start_from_anchor(row, ordinal, total)
    offset = WORK_START_MS + stable_int(row["decision_id"], str(ordinal)) % WORK_SPAN_MS
    timestamp_epoch = min(max(day_start + offset, SEED_START_MS), SEED_END_MS)
    delay_span = MAX_VERIFY_DELAY_MS - MIN_VERIFY_DELAY_MS
    delay = MIN_VERIFY_DELAY_MS + stable_int("verify", row["decision_id"]) % delay_span
    return timestamp_epoch, timestamp_epoch + delay
```

Pseudocode: dry-run stats query

```cypher
MATCH (d:Decision)
WHERE d.origin = 'zero_day_synthetic'
RETURN count(d) AS cnt,
       count(DISTINCT d.timestamp_epoch) AS unique_ts,
       min(d.timestamp_epoch) AS min_ts,
       max(d.timestamp_epoch) AS max_ts,
       count(CASE WHEN d.verified_at_epoch IS NULL THEN 1 END) AS missing_verified
```

Pseudocode: row collection query

```cypher
MATCH (d:Decision)
WHERE d.origin = 'zero_day_synthetic'
OPTIONAL MATCH (d)-[:DECIDED_ON]->(a:Alert)
RETURN d.decision_id AS decision_id,
       d.category AS category,
       d.timestamp_epoch AS decision_ts,
       a.timestamp_epoch AS alert_ts
ORDER BY decision_ts, category, decision_id
```

Pseudocode: orphan validation

```cypher
MATCH (d:Decision)
WHERE d.origin = 'zero_day_synthetic'
  AND NOT EXISTS((d)-[:DECIDED_ON]->())
RETURN count(d) AS orphan_count
```

Pseudocode: apply query

```cypher
MATCH (d:Decision)
WHERE d.origin = 'zero_day_synthetic'
  AND d.decision_id = '<_S escaped decision id>'
SET d.timestamp_epoch = <new_ts>,
    d.verified_at_epoch = <verified_ts>
```

Pseudocode: script behavior

```python
if args.apply is False:
    print(dry_run_stats)
    print("DRY RUN ONLY: rerun with --apply to update")
    return

if already_sufficiently_spread(stats):
    print("Already sufficiently spread; no writes")
    return

for row in rows:
    timestamp_epoch, verified_at_epoch = assign_timestamps(row, ordinal, total)
    await neo4j_client.run_query(build_apply_query(row["decision_id"], timestamp_epoch, verified_at_epoch))
```

## 8. Re-seed / Repair Procedure

Non-destructive repair procedure:

```powershell
cd "C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50\backend"
python support/setup/repair_zero_day_timestamps.py --dry-run
```

Review the dry-run output. It must show the target count, unique timestamp count, span days, missing verified timestamps, orphan count, and would-update count. Then apply explicitly:

```powershell
cd "C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50\backend"
python support/setup/repair_zero_day_timestamps.py --apply
```

Restart backend so startup rebuilds the audit ledger from repaired AGE timestamps:

```powershell
cd "C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50\backend"
uvicorn app.main:app --port 8001 --reload
```

Validate graph contract:

```powershell
cd "C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50\backend"
python -m app.graph_schema verify
```

Validate cross-tab output:

```powershell
cd "C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50"
python .\scripts\collect_tab_content.py
```

Recommended pre-apply backup:

- Use the deployment’s graph backup/export process before `--apply`.
- If no export process is available, save the dry-run output as the minimal operational audit trail. This investigation did not identify a repository-native safe AGE export command.

Destructive fallback only if property repair cannot establish consistency:

```powershell
cd "C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50\backend"
python -m app.graph_schema seed --clean
```

This fallback is destructive for controlled backbone and seeded Decision/Alert origins because `clean=True` deletes and recreates those populations (`backend/app/graph_schema.py:420-427`, `backend/app/graph_schema.py:466-496`). Do not use it as the default timestamp fix.

## 9. Test Plan

Create `backend/tests/test_zero_day_timestamp_spread.py` with these tests:

- `test_source_v5_or_generated_decisions_have_large_spread`
  - Assert 4,860 decisions, span >= 80 days, unique `timestamp_epoch` >= 4,000 after normalization.
- `test_timestamp_assignment_is_deterministic`
  - Same input rows produce identical `timestamp_epoch` and `verified_at_epoch`.
- `test_timestamp_assignment_uses_alert_timestamp_anchor_when_available`
  - A row with historical `alert_ts` gets a timestamp on the same UTC day plus business-hours offset.
- `test_timestamp_assignment_distributes_when_anchor_missing_or_out_of_range`
  - Missing/out-of-range anchors are distributed across the 2025 seed window.
- `test_verified_at_epoch_added_after_timestamp`
  - Delay is >= 1 hour and <= 48 hours.
- `test_dry_run_does_not_write`
  - Mock client records no `SET` query without `--apply`.
- `test_apply_query_has_origin_guard`
  - Every apply query includes `d.origin = 'zero_day_synthetic'` and a specific `d.decision_id`.
- `test_apply_query_preserves_nodes_and_properties`
  - Query contains no `DELETE`, no `DETACH DELETE`, no `MERGE`, no `$`, and no `SET d =`.
- `test_orphan_validation_query_present`
  - Dry-run includes a query for zero-day Decisions without `DECIDED_ON`.
- `test_idempotency_skips_already_spread_graph`
  - Stats with `unique_ts >= 4000`, `span_days >= 80`, no missing `verified_at_epoch`, and zero orphans skip apply.
- `test_idempotency_does_not_skip_daily_buckets`
  - Stats with high span but low uniqueness do not skip. This protects against the current `span > 1 day` skip behavior (`backend/app/services/timestamp_backfill.py:38-42`).
- `test_historical_verified_timestamps_do_not_enter_ae_drift_windows`
  - Historical 2025 `verified_at_epoch` rows are outside current wall-clock windows used by AE-DRIFT (`backend/app/services/variant_generator.py:394-416`).
- `test_audit_rebuild_preserves_repaired_timestamps`
  - Mock `rebuild_from_age()` rows and assert converted timestamps are passed into `_LEDGER.append()` (`backend/app/framework/audit.py:324-342`).
- `test_startup_no_longer_applies_timestamp_repair`
  - Static or monkeypatch test that `main.py` no longer imports/calls an apply-mode timestamp repair at startup.
- `test_enrich_zero_day_v5_validates_timestamp_spread`
  - Generator validation fails if decisions collapse to one timestamp or remain below unique/span thresholds.

Run targeted validation after implementation:

```powershell
cd "C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50\backend"
python -m pytest tests/test_zero_day_timestamp_spread.py -v --timeout=120
```

Run relevant regression after targeted tests pass:

```powershell
cd "C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v4-v50\backend"
python -m pytest tests/test_learning_health.py tests/test_evidence_room.py tests/test_variant_generator.py -q --timeout=120
```

Do not run `repair_zero_day_timestamps.py --apply`, `seed_graph --clean`, reset endpoints, or seed scripts during unit-test validation.

## 10. Open Questions / Blockers

None for architecture implementation.

Operational unknown: the live AGE instance was not queried during this review, by rule. The implementation should rely on dry-run output before `--apply` to confirm the live count, uniqueness, span, and orphan state.

## Reading Log

- `CLAUDE.md`: lines 5-16, 25-26, 82-88, 107-127, 132-160.
- `docs/implementation_plans/cx3_decision_timestamp_spread_architecture.md`: full existing file, lines 1-287 before update.
- `backend/app/graph_schema.py`: lines 38-48, 420-427, 466-496, 584-600, 731-752, 811-821.
- `backend/support/setup/enrich_zero_day_v5.py`: lines 1-18, 398-430, 453-486, 556-560.
- `backend/support/setup/seed_zero_day.py`: lines 1-8, 32-48, 95-109, 129-143, 153-159.
- `backend/support/setup/zero_day_decisions_v5.json`: lines 1-8, 8727-8728, 110766-110767.
- `backend/app/services/timestamp_backfill.py`: lines 1-71.
- `backend/app/framework/audit.py`: lines 235-345.
- `backend/app/services/variant_generator.py`: lines 352-416, 428-445.
- `backend/app/domains/soc/campaigns.py`: lines 105-157, 524-570, 739-765.
- `backend/app/routers/metrics.py`: lines 206-220, 272-279, 321-329, 395-413, 526-528, 657-660, 687-690.
- `backend/app/services/state_manager.py`: lines 48-53, 113-125, 198-247.
- `backend/app/services/evidence_room.py`: lines 118-158.
- `backend/app/main.py`: lines 248-330.
- `backend/app/routers/admin.py`: lines 1-180.
