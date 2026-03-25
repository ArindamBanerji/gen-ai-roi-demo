"""
PatternHistoryFactorComputer — W2 read path tests.

Verifies:
  - Fallback (0.40) when no TRIGGERED_EVOLUTION edges exist
  - W2 path uses edge data when edges are present
  - Recency weighting (exponential decay, half-life=30)
  - Output is clipped to [0.0, 1.0]

Run from backend/ directory:
    pytest tests/test_pattern_history_w2.py -v
"""

import sys
import os
import asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import AsyncMock


def _make_alert(alert_type="credential_access"):
    return {"id": "ALERT-TEST-001", "alert_type": alert_type}


def _make_neo4j_mock(results):
    mock = AsyncMock()
    mock.run_query = AsyncMock(return_value=results)
    return mock


# ---------------------------------------------------------------------------
# Helpers to run async tests synchronously
# ---------------------------------------------------------------------------

def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_pattern_history_fallback_when_no_edges():
    """Empty Neo4j results → fallback value 0.40."""
    from app.domains.soc.factors import PatternHistoryFactorComputer

    computer = PatternHistoryFactorComputer()
    alert = _make_alert()
    neo4j = _make_neo4j_mock([])

    result = run(computer.compute(alert, neo4j, action_index=0))

    assert result == 0.40


def test_pattern_history_uses_triggered_evolution_edges():
    """5 decisions with pattern_value=0.80 (same decision_num) → result ≈ 0.80."""
    from app.domains.soc.factors import PatternHistoryFactorComputer

    computer = PatternHistoryFactorComputer()
    alert = _make_alert()

    # All same decision_number → all weights equal → plain mean = 0.80
    results = [
        {"pattern_value": 0.80, "decision_num": 42},
        {"pattern_value": 0.80, "decision_num": 42},
        {"pattern_value": 0.80, "decision_num": 42},
        {"pattern_value": 0.80, "decision_num": 42},
        {"pattern_value": 0.80, "decision_num": 42},
    ]
    neo4j = _make_neo4j_mock(results)

    result = run(computer.compute(alert, neo4j, action_index=1))

    assert abs(result - 0.80) < 0.01


def test_pattern_history_recency_weighting():
    """
    2 decisions:
      decision_num=100, pattern_value=0.90  (recent, weight=1.0)
      decision_num=70,  pattern_value=0.40  (30 decisions ago, weight=0.5)
    Expected: (0.90×1.0 + 0.40×0.5) / 1.5 ≈ 0.733
    """
    from app.domains.soc.factors import PatternHistoryFactorComputer

    computer = PatternHistoryFactorComputer()
    alert = _make_alert()

    results = [
        {"pattern_value": 0.90, "decision_num": 100},
        {"pattern_value": 0.40, "decision_num": 70},
    ]
    neo4j = _make_neo4j_mock(results)

    result = run(computer.compute(alert, neo4j, action_index=0))

    expected = (0.90 * 1.0 + 0.40 * 0.5) / 1.5  # ≈ 0.7333
    assert abs(result - expected) < 0.01


def test_pattern_history_clips_to_unit_interval():
    """pattern_value=1.20 (out of bounds) → result clamped to ≤ 1.0."""
    from app.domains.soc.factors import PatternHistoryFactorComputer

    computer = PatternHistoryFactorComputer()
    alert = _make_alert()

    results = [{"pattern_value": 1.20, "decision_num": 10}]
    neo4j = _make_neo4j_mock(results)

    result = run(computer.compute(alert, neo4j, action_index=2))

    assert result <= 1.0
