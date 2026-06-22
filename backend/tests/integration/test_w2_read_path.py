"""
Integration Test 2 -- W2 read path regression.
tests/integration/test_w2_read_path.py

Prevents future regression of PatternHistoryFactorComputer after
any refactoring of factors.py, config.py, or the Neo4j layer.

Four cases:
  Case 1 -- Fallback (0.40) when no TRIGGERED_EVOLUTION edges
  Case 2 -- W2 path live when edges exist (result != fallback)
  Case 3 -- Recency weighting functional (exponential decay, half-life=30)
  Case 4 -- Only factor_snapshot[3] referenced (FACTOR_INDEX=4 in 1-based order)

Run from backend/ directory:
    pytest tests/integration/test_w2_read_path.py -v
"""

import sys
import os
import asyncio
import inspect

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from unittest.mock import AsyncMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_alert(alert_type: str = "credential_access") -> dict:
    return {"id": "ALERT-W2-INT-001", "alert_type": alert_type}


def _make_neo4j_mock(results: list) -> AsyncMock:
    """Return a mock Neo4j client whose run_query returns `results`."""
    mock = AsyncMock()
    mock.run_query = AsyncMock(return_value=results)
    return mock


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Case 1 — Fallback when no TRIGGERED_EVOLUTION edges
# ---------------------------------------------------------------------------

def test_w2_case1_fallback_when_no_edges():
    """
    With no TRIGGERED_EVOLUTION edges (empty query result), the compute
    method must return exactly the 0.40 neutral baseline.

    Verifies: _fallback_compute() is called when Neo4j returns [].
    """
    from app.domains.soc.factors import PatternHistoryFactorComputer

    computer = PatternHistoryFactorComputer()
    alert = _make_alert()
    neo4j = _make_neo4j_mock([])

    result = run(computer.compute(alert, neo4j, action_index=0))

    assert abs(result - 0.40) < 0.001, (
        f"Expected fallback 0.40, got {result}. "
        "W2 path must not activate when no edges are present."
    )


# ---------------------------------------------------------------------------
# Case 2 — W2 read path live when edges exist
# ---------------------------------------------------------------------------

def test_w2_case2_read_path_live_when_edges_exist():
    """
    When TRIGGERED_EVOLUTION edges are present, compute() must use the
    W2 path (return the edge-derived value, not the 0.40 fallback).

    Single edge: pattern_value=0.80 -> result should be ~= 0.80, not 0.40.
    Verifies: W2 path is wired and returning enriched data.
    """
    from app.domains.soc.factors import PatternHistoryFactorComputer

    computer = PatternHistoryFactorComputer()
    alert = _make_alert()
    results = [{"pattern_value": 0.80, "decision_num": 100}]
    neo4j = _make_neo4j_mock(results)

    result = run(computer.compute(alert, neo4j, action_index=1))

    assert result != 0.40, (
        f"Result was 0.40 (fallback). W2 path was NOT used even though "
        "Neo4j returned edges. Check that PatternHistoryFactorComputer "
        "reads the results list before calling _fallback_compute."
    )
    assert result > 0.40, (
        f"Expected enriched value > 0.40, got {result}. "
        "A single edge with pattern_value=0.80 must produce a result > baseline."
    )
    assert abs(result - 0.80) < 0.01, (
        f"Expected ~= 0.80 (single-edge mean), got {result}."
    )


# ---------------------------------------------------------------------------
# Case 3 — Recency weighting functional
# ---------------------------------------------------------------------------

def test_w2_case3_recency_weighting():
    """
    Two decisions 30 apart in decision_number must be weighted by the
    exponential decay formula with HALF_LIFE_DECISIONS.

    Setup:
      decision_num=100, pattern_value=0.90  (recent -- weight = 1.0)
      decision_num=70,  pattern_value=0.40  (30 ago -- weight = 2^(-30/30) = 0.5)

    Expected weighted_mean = (0.90x1.0 + 0.40x0.5) / (1.0 + 0.5)
                           = (0.90 + 0.20) / 1.5
                           = 1.10 / 1.5
                           ~= 0.7333
    """
    from app.domains.soc.factors import PatternHistoryFactorComputer

    computer = PatternHistoryFactorComputer()
    half_life = computer.HALF_LIFE_DECISIONS  # confirm constant before computing expected

    # Recompute expected using the actual constant in case it changes
    w_recent = 1.0
    w_old = 2 ** (-half_life / half_life)   # = 2^(-1) = 0.5
    expected = (0.90 * w_recent + 0.40 * w_old) / (w_recent + w_old)

    alert = _make_alert()
    results = [
        {"pattern_value": 0.90, "decision_num": 100},   # recent
        {"pattern_value": 0.40, "decision_num": 100 - half_life},  # exactly half-life ago
    ]
    neo4j = _make_neo4j_mock(results)

    result = run(computer.compute(alert, neo4j, action_index=0))

    assert abs(result - expected) < 0.01, (
        f"Recency weighting failed. "
        f"Expected ~= {expected:.4f} (half_life={half_life}), got {result:.4f}. "
        "Check that weights use 2^(-(max_dec - d) / HALF_LIFE_DECISIONS)."
    )


# ---------------------------------------------------------------------------
# Case 4 — Only factor_snapshot[3] referenced (FACTOR_INDEX=4 in 1-based)
# ---------------------------------------------------------------------------

def test_w2_case4_factor_index_isolation():
    """
    Static assertion: PatternHistoryFactorComputer's Cypher query must
    reference factor_snapshot[3] (0-based) and must NOT reference
    factor_snapshot[0], [1], [2], or [5].

    This ensures the W2 read path is isolated to the pattern_history
    factor slot and cannot silently bleed into other factor indices
    after a refactoring.

    Also confirms the class is wired at position 3 (0-based) in
    get_factor_computers(), i.e., the 4th factor in weight-matrix column
    order (travel=0, asset=1, threat=2, pattern=3, time=4, device=5).
    """
    from app.domains.soc.factors import PatternHistoryFactorComputer
    from app.domains.soc.config import SOCDomainConfig

    # --- Part A: Cypher query contains factor_snapshot[3] only ---
    source = inspect.getsource(PatternHistoryFactorComputer.compute)

    assert "factor_snapshot[3]" in source, (
        "Cypher query must read d.factor_snapshot[3] (pattern_history, 0-based). "
        "Found neither 'factor_snapshot[3]' in compute() source."
    )
    for forbidden_index in (0, 1, 2, 5):
        assert f"factor_snapshot[{forbidden_index}]" not in source, (
            f"Cypher query must NOT reference factor_snapshot[{forbidden_index}]. "
            f"Only index [3] (pattern_history) is permitted in this compute method."
        )

    # --- Part B: PatternHistoryFactorComputer is at position 3 in the pipeline ---
    config = SOCDomainConfig()
    computers = config.get_factor_computers()
    names = [c.name for c in computers]

    assert names[3] == "pattern_history", (
        f"PatternHistoryFactorComputer must be at index 3 in get_factor_computers(). "
        f"Got: {names}. "
        "Factors [0,1,2,4,5] are travel_match, asset_criticality, threat_intel_enrichment, "
        "time_anomaly, device_trust -- none of these should be index 3."
    )
    # Confirm other slots are not disturbed
    assert names[0] != "pattern_history", "pattern_history must not be at index 0"
    assert names[1] != "pattern_history", "pattern_history must not be at index 1"
    assert names[2] != "pattern_history", "pattern_history must not be at index 2"
    assert names[4] != "pattern_history", "pattern_history must not be at index 4"
    assert names[5] != "pattern_history", "pattern_history must not be at index 5"
