"""
Permanent W2 Pattern History flywheel contract tests.

These tests prove the read side using persisted AGE decisions with the
Decision.factor_snapshot contract written by the outcome path:

    {"factor_snapshot": "[... six SOC factors ...]", "decision_num": N}

Graph cases use disposable AGE graphs; extraction cases remain unit tests.
"""

import pytest
from support.campaign_graph import pattern_history

import asyncio
import json
import os
import sys
from unittest.mock import AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.domains.soc.config import SOC_FACTORS, SOCDomainConfig
from app.domains.soc.factors import (
    PatternHistoryFactorComputer,
    _extract_pattern_history_from_factor_snapshot,
)


def _run(coro):
    return asyncio.run(coro)


def _make_alert(category="credential_access"):
    return {
        "id": "ALERT-W2-FLYWHEEL-001",
        "category": category,
        "alert_type": category,
    }


def _factor_snapshot(pattern_history_value):
    """Return the JSON string shape stored in Decision.factor_snapshot."""
    return json.dumps([0.11, 0.22, 0.33, pattern_history_value, 0.55, 0.66])




def test_extract_pattern_history_parses_factor_snapshot_json_string():
    snapshot = _factor_snapshot(0.76)

    result = _extract_pattern_history_from_factor_snapshot(snapshot)

    assert result == 0.76


def test_extract_pattern_history_handles_none_safely():
    result = _extract_pattern_history_from_factor_snapshot(None)

    assert result == 0.40


def test_extract_pattern_history_handles_malformed_json_safely():
    result = _extract_pattern_history_from_factor_snapshot("{bad json")

    assert result == 0.40


def test_extract_pattern_history_handles_short_json_array_safely():
    result = _extract_pattern_history_from_factor_snapshot(json.dumps([0.1, 0.2, 0.3]))

    assert result == 0.40


def test_extract_pattern_history_accepts_numeric_compatibility_value():
    result = _extract_pattern_history_from_factor_snapshot(0.62)

    assert result == 0.62


@pytest.mark.age
def test_pattern_history_compute_returns_safe_default_with_zero_prior_decisions(age_graph):
    computer = PatternHistoryFactorComputer()
    graph = pattern_history(age_graph, [])

    result = _run(computer.compute(_make_alert(), graph))

    assert result == 0.40


@pytest.mark.age
def test_pattern_history_compute_uses_factor_snapshot_json_rows(age_graph):
    computer = PatternHistoryFactorComputer()
    rows = [
        {"factor_snapshot": _factor_snapshot(0.76), "decision_num": 100},
    ]
    graph = pattern_history(age_graph, rows)

    result = _run(computer.compute(_make_alert(), graph))

    assert result == 0.76
    assert result > 0.0
    assert result != 0.40

    query = graph.queries[0]
    assert "TRIGGERED_EVOLUTION" in query
    assert "d.factor_snapshot AS factor_snapshot" in query
    assert "d.decision_number AS decision_num" in query
    assert "d.verified_correct = true" in query


@pytest.mark.age
def test_pattern_history_compute_changes_when_decision_history_changes(age_graph):
    computer = PatternHistoryFactorComputer()
    alert = _make_alert()

    one_decision_rows = [
        {"factor_snapshot": _factor_snapshot(0.76), "decision_num": 100},
    ]
    mixed_history_rows = [
        {"factor_snapshot": _factor_snapshot(0.76), "decision_num": 100},
        {"factor_snapshot": _factor_snapshot(0.20), "decision_num": 70},
    ]

    one_decision = _run(computer.compute(alert, pattern_history(age_graph, one_decision_rows)))
    mixed_history = _run(computer.compute(alert, pattern_history(age_graph, mixed_history_rows[1:])))

    expected_mixed = (0.76 * 1.0 + 0.20 * 0.5) / 1.5
    assert one_decision == 0.76
    assert abs(mixed_history - expected_mixed) < 0.001
    assert mixed_history != one_decision


def test_pattern_history_factor_index_matches_soc_config_ordering():
    computers = SOCDomainConfig().get_factor_computers()
    computer_names = [computer.name for computer in computers]

    assert SOC_FACTORS.index("pattern_history") == 3
    assert SOC_FACTORS[3] == "pattern_history"
    assert computer_names == SOC_FACTORS
    assert computer_names[3] == "pattern_history"
