from __future__ import annotations

import importlib.util
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pytest


def _load_seed_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "seed_verified_decisions.py"
    spec = importlib.util.spec_from_file_location("seed_verified_decisions", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


seed_mod = _load_seed_module()


def _decisions():
    return seed_mod.build_demo_decisions(
        now=datetime(2026, 5, 5, tzinfo=timezone.utc)
    )


def test_build_demo_decisions_returns_500():
    assert len(_decisions()) == 500


def test_category_distribution_matches_canonical_distribution():
    counts = Counter(row["category"] for row in _decisions())
    assert counts == seed_mod.CATEGORY_DISTRIBUTION


def test_no_unknown_or_threat_intel_match_category():
    categories = {row["category"] for row in _decisions()}
    assert "unknown" not in categories
    assert "threat_intel_match" not in categories


def test_actions_are_canonical():
    assert {row["action"] for row in _decisions()} <= set(seed_mod.SCORER_ACTIONS)


def test_correct_and_incorrect_counts():
    rows = _decisions()
    assert sum(1 for row in rows if row["correct"]) == 425
    assert sum(1 for row in rows if not row["correct"]) == 75


def test_override_count_and_analyst_action_differs():
    overrides = [row for row in _decisions() if row["outcome"] == "overridden"]
    assert len(overrides) == 25
    assert all(row["correct"] is True for row in overrides)
    assert all(row["analyst_action"] != row["action"] for row in overrides)
    assert all(row["override_comment"] for row in overrides)


def test_timestamp_fields_are_millisecond_scale_and_ordered():
    for row in _decisions():
        assert row["timestamp_epoch"] > 1_000_000_000_000
        assert row["verified_at_epoch"] > 1_000_000_000_000
        assert row["verified_at_epoch"] > row["timestamp_epoch"]


def test_timestamp_spread_is_close_to_30_day_seed_window():
    timestamps = [row["timestamp_epoch"] for row in _decisions()]
    assert max(timestamps) - min(timestamps) >= 28 * seed_mod.MILLISECONDS_PER_DAY
    assert len(set(timestamps)) == len(timestamps)


def test_create_query_is_age_safe():
    query = seed_mod.build_create_decision_query(_decisions()[0])
    assert "CREATE (d:Decision" in query
    assert "MERGE" not in query
    assert "UNWIND" not in query
    assert "$" not in query


@pytest.mark.asyncio
async def test_double_seed_guard_skips_when_existing_count_above_threshold():
    class FakeClient:
        def __init__(self):
            self.writes = []

        async def count_verified_decisions(self):
            return 101

        async def run_query(self, query):
            self.writes.append(query)
            return []

    client = FakeClient()
    result = await seed_mod.maybe_seed_verified_decisions(client)

    assert result["skipped"] is True
    assert result["existing_count"] == 101
    assert client.writes == []
