from __future__ import annotations

from datetime import datetime, timezone

import pytest

import app.framework.audit as audit_mod
from app.seed.config import SeedConfig
from app.seed.runner import generate_seed


class FakeClient:
    def __init__(self, rows):
        self.rows = rows
        self.queries: list[str] = []

    async def run_query(self, query: str):
        self.queries.append(query)
        return list(self.rows)


@pytest.fixture(autouse=True)
def clear_audit_ledger():
    audit_mod._LEDGER._entries.clear()
    audit_mod._SITUATION_TYPES.clear()
    yield
    audit_mod._LEDGER._entries.clear()
    audit_mod._SITUATION_TYPES.clear()


def test_timestamp_uniqueness():
    data = generate_seed()
    timestamps = [decision["timestamp_epoch"] for decision in data["decisions"]]

    assert len(set(timestamps)) == len(timestamps)


def test_timestamp_span_covers_window():
    config = SeedConfig()
    data = generate_seed(config)
    timestamps = [decision["timestamp_epoch"] for decision in data["decisions"]]
    span = max(timestamps) - min(timestamps)
    configured = config.time_range_days * 24 * 60 * 60 * 1000

    assert span >= configured * 0.8


@pytest.mark.asyncio
async def test_audit_reconstruct_uses_decision_timestamps():
    ts = 1741046400000
    rows = [_row("DEC-1", "ALERT-1", ts)]

    added = await audit_mod.rebuild_chain_from_graph(FakeClient(rows))

    assert added == 1
    entry = audit_mod._LEDGER.entries()[0]
    assert entry.timestamp == _iso(ts)


@pytest.mark.asyncio
async def test_rebuild_chain_preserves_timestamp_order():
    rows = [
        _row("DEC-1", "ALERT-1", 1741046400000),
        _row("DEC-2", "ALERT-2", 1741132800000),
        _row("DEC-3", "ALERT-3", 1741219200000),
    ]

    added = await audit_mod.rebuild_chain_from_graph(FakeClient(rows))

    assert added == 3
    assert [entry.decision_id for entry in audit_mod._LEDGER.entries()] == [
        "DEC-1",
        "DEC-2",
        "DEC-3",
    ]
    assert [entry.timestamp for entry in audit_mod._LEDGER.entries()] == [
        _iso(row["ts"]) for row in rows
    ]


@pytest.mark.asyncio
async def test_rebuild_chain_missing_timestamp_uses_utc_iso_fallback():
    rows = [_row("DEC-1", "ALERT-1", None)]

    await audit_mod.rebuild_chain_from_graph(FakeClient(rows))

    entry = audit_mod._LEDGER.entries()[0]
    parsed = datetime.fromisoformat(entry.timestamp)
    assert parsed.tzinfo is not None


def _row(decision_id: str, alert_id: str, ts: int | None):
    return {
        "decision_id": decision_id,
        "alert_id": alert_id,
        "category": "credential_access",
        "action": "escalate",
        "confidence": 0.91,
        "correct": True,
        "ts": ts,
    }


def _iso(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat()
