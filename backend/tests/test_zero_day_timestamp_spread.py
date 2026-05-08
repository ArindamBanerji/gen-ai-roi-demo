from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path

import pytest


def _load_repair_module():
    path = Path(__file__).resolve().parents[1] / "support" / "setup" / "repair_zero_day_timestamps.py"
    spec = importlib.util.spec_from_file_location("repair_zero_day_timestamps", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


repair_mod = _load_repair_module()


def _rows(count: int = 120) -> list[dict]:
    rows = []
    for index in range(count):
        rows.append(
            {
                "decision_id": f"SYN-DEC-{index:04d}",
                "category": "credential_access" if index % 2 == 0 else "malware_execution",
                "decision_ts": repair_mod.SEED_END_DAY_START_MS,
                "alert_ts": None,
            }
        )
    return rows


def test_timestamp_assignment_is_deterministic():
    first = repair_mod.build_assignments(_rows())
    second = repair_mod.build_assignments(_rows())
    assert first == second


def test_generated_timestamps_are_historical_not_current_wall_clock():
    assignments = repair_mod.build_assignments(_rows())
    now_ms = int(time.time() * 1000)
    assert all(repair_mod.SEED_START_MS <= row.timestamp_epoch <= repair_mod.SEED_END_MS for row in assignments)
    assert max(row.timestamp_epoch for row in assignments) < now_ms - 180 * repair_mod.DAY_MS


def test_timestamp_spread_has_many_days_and_large_span():
    assignments = repair_mod.build_assignments(_rows())
    timestamps = [row.timestamp_epoch for row in assignments]
    summary = repair_mod.summarize_timestamps(timestamps)
    assert summary["unique_days"] >= 30
    assert summary["span_days"] >= 80


def test_generated_timestamps_are_not_all_identical():
    assignments = repair_mod.build_assignments(_rows())
    assert len({row.timestamp_epoch for row in assignments}) > 1


def test_verified_at_epoch_after_timestamp_with_historical_delay():
    assignments = repair_mod.build_assignments(_rows())
    for assignment in assignments:
        delay = assignment.verified_at_epoch - assignment.timestamp_epoch
        assert delay >= repair_mod.MIN_VERIFY_DELAY_MS
        assert delay <= repair_mod.MAX_VERIFY_DELAY_MS
        assert assignment.verified_at_epoch < int(time.time() * 1000) - 180 * repair_mod.DAY_MS


def test_uses_alert_timestamp_anchor_when_anchor_spread_is_usable():
    rows = []
    for index in range(90):
        alert_ts = repair_mod.SEED_START_MS + index * repair_mod.DAY_MS
        rows.append(
            {
                "decision_id": f"SYN-DEC-{index:04d}",
                "category": "credential_access",
                "decision_ts": repair_mod.SEED_END_DAY_START_MS,
                "alert_ts": alert_ts,
            }
        )
    assignments = repair_mod.build_assignments(rows)
    assert repair_mod._day_start(assignments[0].timestamp_epoch) == repair_mod.SEED_START_MS


def test_apply_query_has_origin_guard_and_only_timestamp_sets():
    query = repair_mod.build_apply_query(
        repair_mod.TimestampAssignment(
            decision_id="SYN-DEC-0001",
            timestamp_epoch=repair_mod.SEED_START_MS + repair_mod.WORK_START_MS,
            verified_at_epoch=repair_mod.SEED_START_MS + repair_mod.WORK_START_MS + repair_mod.MIN_VERIFY_DELAY_MS,
        )
    )
    upper = query.upper()
    assert "MATCH (D:DECISION)" in upper
    assert "D.ORIGIN = 'zero_day_synthetic'".upper() in upper
    assert "D.DECISION_ID" in upper
    assert "SET D.TIMESTAMP_EPOCH" in upper
    assert "D.VERIFIED_AT_EPOCH" in upper
    assert "MERGE" not in upper
    assert "$" not in query
    assert "DELETE" not in upper
    assert "DETACH" not in upper
    assert "SET D =" not in upper
    assert "CREATE" not in upper
    assert "DECIDED_ON" not in upper


@pytest.mark.asyncio
async def test_dry_run_executes_no_set_write_query():
    class FakeClient:
        def __init__(self):
            self.queries = []

        async def run_query(self, query):
            self.queries.append(query)
            if "RETURN count(d) AS cnt" in query:
                return [{"cnt": 120, "unique_ts": 1, "min_ts": repair_mod.SEED_END_DAY_START_MS, "max_ts": repair_mod.SEED_END_DAY_START_MS, "missing_verified": 120}]
            if "orphan_count" in query:
                return [{"orphan_count": 0}]
            if "RETURN d.decision_id AS decision_id" in query:
                return _rows()
            raise AssertionError(f"Unexpected query: {query}")

    client = FakeClient()
    result = await repair_mod.repair_zero_day_timestamps(client, apply=False)
    assert result["applied"] is False
    assert result["updated"] == 0
    assert not any(" SET " in query.upper() for query in client.queries)


@pytest.mark.asyncio
async def test_apply_skips_when_current_stats_are_already_sufficiently_spread():
    class FakeClient:
        def __init__(self):
            self.queries = []

        async def run_query(self, query):
            self.queries.append(query)
            if "RETURN count(d) AS cnt" in query:
                return [{"cnt": 4860, "unique_ts": 4000, "min_ts": repair_mod.SEED_START_MS, "max_ts": repair_mod.SEED_START_MS + 81 * repair_mod.DAY_MS, "missing_verified": 0}]
            if "orphan_count" in query:
                return [{"orphan_count": 0}]
            if "RETURN d.decision_id AS decision_id" in query:
                return _rows()
            raise AssertionError(f"Unexpected query: {query}")

    client = FakeClient()
    result = await repair_mod.repair_zero_day_timestamps(client, apply=True)
    assert result["skipped"] is True
    assert result["updated"] == 0
    assert not any(" SET " in query.upper() for query in client.queries)


def test_daily_buckets_do_not_count_as_sufficiently_spread():
    stats = {
        "unique_ts": 90,
        "span_days": 89.0,
    }
    assert repair_mod.already_sufficiently_spread(stats) is False


def test_historical_verified_timestamps_outside_ae_drift_windows():
    assignments = repair_mod.build_assignments(_rows())
    now_ms = int(time.time() * 1000)
    prior_cutoff = now_ms - 28 * repair_mod.DAY_MS
    assert max(row.verified_at_epoch for row in assignments) < prior_cutoff


def test_startup_no_longer_applies_timestamp_repair():
    main_path = Path(__file__).resolve().parents[1] / "app" / "main.py"
    text = main_path.read_text(encoding="utf-8")
    assert "backfill_decision_timestamps" not in text
    assert "repair_zero_day_timestamps.py --apply" in text
