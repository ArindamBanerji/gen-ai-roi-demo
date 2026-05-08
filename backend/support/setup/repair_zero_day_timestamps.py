"""Dry-run/apply repair for zero-day synthetic Decision timestamps.

Default mode is dry-run. Apply mode is explicit and updates only
timestamp_epoch and verified_at_epoch on zero_day_synthetic Decision nodes.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.graph_schema import _S  # noqa: E402


SYNTHETIC_ORIGIN = "zero_day_synthetic"
SEED_START_MS = 1_741_046_400_000  # 2025-03-04T00:00:00Z
SEED_END_DAY_START_MS = 1_748_736_000_000  # 2025-06-01T00:00:00Z
DAY_MS = 86_400_000
SEED_END_MS = SEED_END_DAY_START_MS + DAY_MS - 1
WORK_START_MS = 8 * 3_600_000
WORK_SPAN_MS = 10 * 3_600_000
MIN_VERIFY_DELAY_MS = 3_600_000
MAX_VERIFY_DELAY_MS = 48 * 3_600_000
MIN_UNIQUE_TIMESTAMPS = 4_000
MIN_SPAN_DAYS = 80.0
MIN_ANCHOR_UNIQUE_DAYS = 30
MIN_ANCHOR_SPAN_DAYS = 60.0


@dataclass(frozen=True)
class TimestampAssignment:
    decision_id: str
    timestamp_epoch: int
    verified_at_epoch: int


def _stable_int(*parts: str) -> int:
    digest = hashlib.sha256(":".join(parts).encode("utf-8")).hexdigest()
    return int(digest[:12], 16)


def _to_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _historical_anchor(row: dict[str, Any]) -> int | None:
    for key in ("alert_ts", "decision_ts", "timestamp_epoch"):
        ts = _to_int(row.get(key))
        if ts is not None and SEED_START_MS <= ts <= SEED_END_MS:
            return ts
    return None


def _day_start(ts: int) -> int:
    return (ts // DAY_MS) * DAY_MS


def _span_days(min_ts: int | None, max_ts: int | None) -> float:
    if min_ts is None or max_ts is None or max_ts < min_ts:
        return 0.0
    return (max_ts - min_ts) / DAY_MS


def _use_anchor_days(rows: list[dict[str, Any]]) -> bool:
    anchors = [_historical_anchor(row) for row in rows]
    anchors = [anchor for anchor in anchors if anchor is not None]
    if not anchors:
        return False
    unique_days = {_day_start(anchor) for anchor in anchors}
    return (
        len(unique_days) >= MIN_ANCHOR_UNIQUE_DAYS
        and _span_days(min(anchors), max(anchors)) >= MIN_ANCHOR_SPAN_DAYS
    )


def _distributed_day_start(ordinal: int, total: int) -> int:
    span = SEED_END_DAY_START_MS - SEED_START_MS
    distributed = SEED_START_MS + (ordinal * span // max(total - 1, 1))
    return _day_start(distributed)


def assign_timestamp(row: dict[str, Any], ordinal: int, total: int, use_anchor: bool) -> TimestampAssignment:
    decision_id = str(row.get("decision_id") or "")
    if not decision_id:
        raise ValueError("decision_id is required")

    anchor = _historical_anchor(row) if use_anchor else None
    day_start = _day_start(anchor) if anchor is not None else _distributed_day_start(ordinal, total)
    day_start = max(SEED_START_MS, min(day_start, SEED_END_DAY_START_MS))

    offset = WORK_START_MS + (_stable_int(decision_id, str(ordinal)) % WORK_SPAN_MS)
    timestamp_epoch = max(SEED_START_MS, min(day_start + offset, SEED_END_MS))

    delay_span = MAX_VERIFY_DELAY_MS - MIN_VERIFY_DELAY_MS
    delay = MIN_VERIFY_DELAY_MS + (_stable_int("verify", decision_id) % delay_span)
    verified_at_epoch = timestamp_epoch + delay
    return TimestampAssignment(decision_id, timestamp_epoch, verified_at_epoch)


def build_assignments(rows: list[dict[str, Any]]) -> list[TimestampAssignment]:
    ordered = sorted(
        rows,
        key=lambda row: (
            _historical_anchor(row) or 0,
            str(row.get("category") or ""),
            str(row.get("decision_id") or ""),
        ),
    )
    use_anchor = _use_anchor_days(ordered)
    return [
        assign_timestamp(row, index, len(ordered), use_anchor)
        for index, row in enumerate(ordered)
        if row.get("decision_id")
    ]


def summarize_timestamps(values: list[int]) -> dict[str, Any]:
    if not values:
        return {"unique_ts": 0, "min_ts": None, "max_ts": None, "span_days": 0.0, "unique_days": 0}
    min_ts = min(values)
    max_ts = max(values)
    return {
        "unique_ts": len(set(values)),
        "min_ts": min_ts,
        "max_ts": max_ts,
        "span_days": _span_days(min_ts, max_ts),
        "unique_days": len({_day_start(value) for value in values}),
    }


def normalize_current_stats(stats_row: dict[str, Any] | None, orphan_count: int = 0) -> dict[str, Any]:
    stats_row = stats_row or {}
    cnt = int(_to_int(stats_row.get("cnt")) or 0)
    unique_ts = int(_to_int(stats_row.get("unique_ts")) or 0)
    min_ts = _to_int(stats_row.get("min_ts"))
    max_ts = _to_int(stats_row.get("max_ts"))
    missing_verified = int(_to_int(stats_row.get("missing_verified")) or 0)
    return {
        "count": cnt,
        "unique_ts": unique_ts,
        "min_ts": min_ts,
        "max_ts": max_ts,
        "span_days": _span_days(min_ts, max_ts),
        "missing_verified_at_epoch": missing_verified,
        "orphan_decisions_without_decided_on": int(orphan_count),
    }


def already_sufficiently_spread(stats: dict[str, Any]) -> bool:
    return (
        int(stats.get("unique_ts") or 0) >= MIN_UNIQUE_TIMESTAMPS
        and float(stats.get("span_days") or 0.0) >= MIN_SPAN_DAYS
    )


def build_apply_query(assignment: TimestampAssignment) -> str:
    return (
        "MATCH (d:Decision) "
        f"WHERE d.origin = {_S(SYNTHETIC_ORIGIN)} "
        f"AND d.decision_id = {_S(assignment.decision_id)} "
        f"SET d.timestamp_epoch = {int(assignment.timestamp_epoch)}, "
        f"d.verified_at_epoch = {int(assignment.verified_at_epoch)}"
    )


def stats_query() -> str:
    return (
        "MATCH (d:Decision) "
        f"WHERE d.origin = {_S(SYNTHETIC_ORIGIN)} "
        "RETURN count(d) AS cnt, "
        "count(DISTINCT d.timestamp_epoch) AS unique_ts, "
        "min(d.timestamp_epoch) AS min_ts, "
        "max(d.timestamp_epoch) AS max_ts, "
        "count(CASE WHEN d.verified_at_epoch IS NULL THEN 1 END) AS missing_verified"
    )


def orphan_query() -> str:
    return (
        "MATCH (d:Decision) "
        f"WHERE d.origin = {_S(SYNTHETIC_ORIGIN)} "
        "AND NOT EXISTS((d)-[:DECIDED_ON]->()) "
        "RETURN count(d) AS orphan_count"
    )


def target_rows_query() -> str:
    return (
        "MATCH (d:Decision) "
        f"WHERE d.origin = {_S(SYNTHETIC_ORIGIN)} "
        "OPTIONAL MATCH (d)-[:DECIDED_ON]->(a:Alert) "
        "RETURN d.decision_id AS decision_id, "
        "d.category AS category, "
        "d.timestamp_epoch AS decision_ts, "
        "a.timestamp_epoch AS alert_ts "
        "ORDER BY decision_ts, category, decision_id"
    )


async def collect_current_stats(client: Any) -> dict[str, Any]:
    stats_rows = await client.run_query(stats_query())
    orphan_rows = await client.run_query(orphan_query())
    orphan_count = int(_to_int((orphan_rows[0] or {}).get("orphan_count")) or 0) if orphan_rows else 0
    return normalize_current_stats(stats_rows[0] if stats_rows else None, orphan_count)


async def fetch_target_rows(client: Any) -> list[dict[str, Any]]:
    rows = await client.run_query(target_rows_query())
    return [dict(row) for row in rows] if rows else []


def build_result(current_stats: dict[str, Any], assignments: list[TimestampAssignment]) -> dict[str, Any]:
    proposed_ts = [assignment.timestamp_epoch for assignment in assignments]
    proposed_verified = [assignment.verified_at_epoch for assignment in assignments]
    proposed = summarize_timestamps(proposed_ts)
    proposed["verified_at_epoch_min"] = min(proposed_verified) if proposed_verified else None
    proposed["verified_at_epoch_max"] = max(proposed_verified) if proposed_verified else None
    proposed["verified_delay_min_ms"] = (
        min(v - t for v, t in zip(proposed_verified, proposed_ts)) if proposed_ts else None
    )
    proposed["verified_delay_max_ms"] = (
        max(v - t for v, t in zip(proposed_verified, proposed_ts)) if proposed_ts else None
    )
    return {
        "current": current_stats,
        "proposed": proposed,
        "would_update": len(assignments),
        "verified_at_epoch_policy": "timestamp_epoch + deterministic 1h..48h, historical seed window",
    }


def print_summary(result: dict[str, Any], apply: bool, skipped: bool = False) -> None:
    mode = "APPLY" if apply else "DRY RUN"
    print(f"[repair_zero_day_timestamps] mode={mode}")
    print(f"Current: {result['current']}")
    print(f"Proposed: {result['proposed']}")
    print(f"Would update: {result['would_update']}")
    print(f"verified_at_epoch policy: {result['verified_at_epoch_policy']}")
    if skipped:
        print("Already sufficiently spread; no writes performed")
    elif not apply:
        print("DRY RUN ONLY: rerun with --apply to update AGE properties")


async def repair_zero_day_timestamps(client: Any, apply: bool = False) -> dict[str, Any]:
    current_stats = await collect_current_stats(client)
    rows = await fetch_target_rows(client)
    assignments = build_assignments(rows)
    result = build_result(current_stats, assignments)

    if not apply:
        result.update({"applied": False, "skipped": False, "updated": 0})
        print_summary(result, apply=False)
        return result

    if already_sufficiently_spread(current_stats):
        result.update({"applied": False, "skipped": True, "updated": 0})
        print_summary(result, apply=True, skipped=True)
        return result

    updated = 0
    for assignment in assignments:
        await client.run_query(build_apply_query(assignment))
        updated += 1

    result.update({"applied": True, "skipped": False, "updated": updated})
    print_summary(result, apply=True)
    print(f"Updated {updated} zero_day_synthetic Decision nodes")
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Repair zero-day synthetic Decision timestamp spread")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Compute and print repair plan without writes")
    mode.add_argument("--apply", action="store_true", help="Apply timestamp_epoch and verified_at_epoch updates")
    return parser.parse_args(argv)


async def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    apply = bool(args.apply)

    from app.db.neo4j import neo4j_client  # noqa: PLC0415

    await neo4j_client.connect()
    try:
        await repair_zero_day_timestamps(neo4j_client, apply=apply)
    finally:
        await neo4j_client.close()


if __name__ == "__main__":
    asyncio.run(main())
