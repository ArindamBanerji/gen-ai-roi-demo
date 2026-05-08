import logging
import re

import pytest

from app.services.cluster_history import compute_trend, get_cluster_history


NOW_MS = 1_700_000_000_000
DAY_MS = 86_400_000


class FakeGraph:
    def __init__(self, rows=None, exc=None):
        self.rows = rows or []
        self.exc = exc
        self.queries = []

    async def run_query(self, query):
        self.queries.append(query)
        if self.exc:
            raise self.exc
        return list(self.rows)


def row(index, *, correct=True, category="credential_access", action="escalate", ts=None):
    return {
        "decision_id": f"DEC-{index}",
        "category": category,
        "action": action,
        "outcome": "correct" if correct else "incorrect",
        "correct": correct,
        "confidence": 0.8,
        "timestamp_epoch": ts if ts is not None else NOW_MS - index * DAY_MS,
    }


@pytest.mark.asyncio
async def test_returns_prior_verified_decisions():
    graph = FakeGraph([row(i) for i in range(5)])

    result = await get_cluster_history("user-1", "CURRENT", graph)

    assert result is not None
    assert result.total_prior == 5
    assert len(result.recent) == 5
    assert result.current_position == 6


@pytest.mark.asyncio
async def test_excludes_current_decision_defensively():
    graph = FakeGraph([row(1), {**row(2), "decision_id": "CURRENT"}])

    result = await get_cluster_history("user-1", "CURRENT", graph)

    assert result is not None
    assert result.total_prior == 1
    assert all(entry.decision_id != "CURRENT" for entry in result.recent)


@pytest.mark.asyncio
async def test_query_filters_verified_decisions():
    graph = FakeGraph([])

    await get_cluster_history("user-1", "CURRENT", graph)

    query = graph.queries[0]
    assert "d.outcome IS NOT NULL" in query
    assert "d.verified_at_epoch IS NOT NULL" in query


@pytest.mark.asyncio
async def test_per_category_and_action_sum_to_total():
    rows = [
        row(1, category="credential_access", action="escalate"),
        row(2, category="credential_access", action="investigate"),
        row(3, category="lateral_movement", action="investigate"),
    ]

    result = await get_cluster_history("user-1", "CURRENT", FakeGraph(rows))

    assert result is not None
    assert sum(result.per_category.values()) == result.total_prior
    assert sum(result.per_action.values()) == result.total_prior
    assert result.per_category == {"credential_access": 2, "lateral_movement": 1}
    assert result.per_action == {"escalate": 1, "investigate": 2}


@pytest.mark.asyncio
async def test_precision_computation():
    rows = [row(i, correct=True) for i in range(14)]
    rows.extend(row(100 + i, correct=False) for i in range(4))

    result = await get_cluster_history("user-1", "CURRENT", FakeGraph(rows))

    assert result is not None
    assert result.total_prior == 18
    assert result.precision == pytest.approx(0.778, abs=0.001)


def test_trend_escalating():
    decisions = [row(i, ts=NOW_MS - i * DAY_MS) for i in range(1, 7)]
    decisions.extend(row(20 + i, ts=NOW_MS - (35 + i) * DAY_MS) for i in range(2))

    trend, detail = compute_trend(decisions, now_epoch=NOW_MS)

    assert trend == "escalating"
    assert "6 verified" in detail
    assert "2 in the prior" in detail


def test_trend_stable():
    decisions = [row(i, ts=NOW_MS - i * DAY_MS) for i in range(1, 4)]
    decisions.extend(row(20 + i, ts=NOW_MS - (35 + i) * DAY_MS) for i in range(3))

    trend, detail = compute_trend(decisions, now_epoch=NOW_MS)

    assert trend == "stable"
    assert "3 verified" in detail
    assert "3 in the prior" in detail


@pytest.mark.asyncio
async def test_empty_history():
    result = await get_cluster_history("user-1", "CURRENT", FakeGraph([]))

    assert result is not None
    assert result.total_prior == 0
    assert result.precision == 0.0
    assert result.trend == "new"
    assert result.current_position == 1


def test_timestamp_unit_conversion_ms():
    decisions = [
        row(1, ts=NOW_MS - DAY_MS),
        row(2, ts=NOW_MS - 40 * DAY_MS),
    ]

    trend, detail = compute_trend(decisions, now_epoch=NOW_MS, timestamp_unit="milliseconds")

    assert trend == "stable"
    assert "1 verified" in detail
    assert "1 in the prior" in detail


@pytest.mark.asyncio
async def test_query_failure_returns_none_and_logs(caplog):
    graph = FakeGraph(exc=RuntimeError("graph unavailable"))

    with caplog.at_level(logging.WARNING):
        result = await get_cluster_history("user-1", "CURRENT", graph)

    assert result is None
    assert "query failed" in caplog.text


@pytest.mark.asyncio
async def test_age_query_safety_and_string_serialization():
    graph = FakeGraph([])

    await get_cluster_history("o'hara", "CURRENT-1", graph)

    query = graph.queries[0]
    assert "$" not in query
    for token in ("MERGE", "SET", "CREATE", "DELETE"):
        assert re.search(rf"\b{token}\b", query) is None
    assert "MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)" in query
    assert "a.user_id = 'o\\'hara'" in query
    assert "d.decision_id <> 'CURRENT-1'" in query
