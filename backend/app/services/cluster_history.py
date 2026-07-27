"""Per-alert cluster history for Tab 3 display context.

The service is read-only: it queries prior verified Decisions for the same
Alert.user_id and computes display summaries in Python.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import logging
import time
from typing import Any, Literal

from app.graph_schema import _S

logger = logging.getLogger(__name__)

Trend = Literal["escalating", "stable", "declining", "new"]


@dataclass
class ClusterEntry:
    decision_id: str
    category: str
    action: str
    outcome: str
    confidence: float
    days_ago: float


@dataclass
class ClusterHistoryResponse:
    source_user: str
    total_prior: int
    per_category: dict[str, int]
    per_action: dict[str, int]
    precision: float
    trend: Trend
    trend_detail: str
    recent: list[ClusterEntry]
    current_position: int


def _timestamp_to_seconds(value: Any, timestamp_unit: str) -> float | None:
    try:
        ts = float(value)
    except (TypeError, ValueError):
        return None
    if timestamp_unit in ("ms", "millisecond", "milliseconds"):
        return ts / 1000.0
    return ts


def compute_trend(
    decisions: list[dict[str, Any]],
    window_days: int = 30,
    now_epoch: float | None = None,
    timestamp_unit: str = "milliseconds",
) -> tuple[Trend, str]:
    """Compare recent and prior windows using Decision.timestamp_epoch."""
    if not decisions:
        return "new", "No prior verified decisions for this user."

    now_seconds = float(now_epoch if now_epoch is not None else time.time())
    if now_seconds > 1_000_000_000_000:
        now_seconds /= 1000.0

    window_seconds = window_days * 86_400
    recent_start = now_seconds - window_seconds
    prior_start = now_seconds - (2 * window_seconds)

    recent_count = 0
    prior_count = 0
    for decision in decisions:
        ts_seconds = _timestamp_to_seconds(
            decision.get("timestamp_epoch") or decision.get("timestamp"),
            timestamp_unit,
        )
        if ts_seconds is None:
            continue
        if recent_start <= ts_seconds <= now_seconds:
            recent_count += 1
        elif prior_start <= ts_seconds < recent_start:
            prior_count += 1

    if prior_count == 0 and recent_count > 0:
        trend: Trend = "new"
    elif prior_count == 0:
        trend = "stable"
    else:
        ratio = recent_count / prior_count
        if ratio > 1.5:
            trend = "escalating"
        elif ratio < 0.5:
            trend = "declining"
        else:
            trend = "stable"

    return (
        trend,
        f"{recent_count} verified decision(s) in the last {window_days}d; "
        f"{prior_count} in the prior {window_days}d.",
    )


def _row_bool(value: Any) -> bool:
    return value is True or str(value).lower() == "true"


def _entry_from_row(row: dict[str, Any], now_seconds: float) -> ClusterEntry:
    ts_seconds = _timestamp_to_seconds(row.get("timestamp_epoch"), "milliseconds")
    days_ago = 0.0
    if ts_seconds is not None:
        days_ago = max((now_seconds - ts_seconds) / 86_400, 0.0)
    return ClusterEntry(
        decision_id=str(row.get("decision_id") or ""),
        category=str(row.get("category") or "unknown"),
        action=str(row.get("action") or "unknown"),
        outcome=str(row.get("outcome") or "unknown"),
        confidence=float(row.get("confidence") or 0.0),
        days_ago=round(days_ago, 2),
    )


async def get_cluster_history(
    source_user: str | None,
    current_decision_id: str | None,
    graph_client: Any,
) -> ClusterHistoryResponse | None:
    """Fetch prior verified decisions for a user and summarize for display."""
    if not graph_client or not source_user:
        return None

    decision_id = current_decision_id or ""
    query = f"""
    MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)
    WHERE d.domain = 'soc'
      AND a.user_id = {_S(source_user)}
      AND d.outcome IS NOT NULL
      AND d.verified_at_epoch IS NOT NULL
      AND d.decision_id <> {_S(decision_id)}
    RETURN d.decision_id AS decision_id,
           d.category AS category,
           d.action AS action,
           d.outcome AS outcome,
           d.correct AS correct,
           d.confidence AS confidence,
           d.timestamp_epoch AS timestamp_epoch
    ORDER BY d.timestamp_epoch DESC
    """

    try:
        rows = await graph_client.run_query(query)
    except Exception as exc:
        logger.warning("[CLUSTER-HISTORY] query failed for user=%s: %s", source_user, exc)
        return None

    decisions = [
        dict(row)
        for row in (rows or [])
        if str(row.get("decision_id") or "") != decision_id
    ]
    total_prior = len(decisions)
    now_seconds = time.time()

    per_category = dict(Counter(str(row.get("category") or "unknown") for row in decisions))
    per_action = dict(Counter(str(row.get("action") or "unknown") for row in decisions))
    correct_count = sum(1 for row in decisions if _row_bool(row.get("correct")))
    precision = (correct_count / total_prior) if total_prior else 0.0
    trend, trend_detail = compute_trend(decisions, now_epoch=now_seconds)
    recent = [_entry_from_row(row, now_seconds) for row in decisions[:5]]

    return ClusterHistoryResponse(
        source_user=str(source_user),
        total_prior=total_prior,
        per_category=per_category,
        per_action=per_action,
        precision=round(precision, 3),
        trend=trend,
        trend_detail=trend_detail,
        recent=recent,
        current_position=total_prior + 1,
    )
