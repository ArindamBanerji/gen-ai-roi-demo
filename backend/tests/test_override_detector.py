"""
tests/test_override_detector.py -- OverrideDetector activation threshold tests.

2 tests:
  - 49 examples -> NOT activated
  - 50 examples -> ACTIVATED

Run from backend/:
    pytest tests/test_override_detector.py -v
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import asyncio
from unittest.mock import AsyncMock

from app.framework.override_detector import OverrideDetector


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_examples(n: int) -> list:
    """Return n minimal correct-override dicts."""
    return [
        {
            "alert_idx":      i,
            "category":       "credential_access",
            "analyst_action": "escalate",
            "ai_action":      "suppress",
            "reasoning":      f"example-{i}",
        }
        for i in range(n)
    ]


# ============================================================================
# Test 1 — 49 examples → detector NOT activated
# ============================================================================

def test_override_detector_not_activated_at_49():
    """
    Loading 49 examples must NOT activate the detector.
    The threshold is 50; one short must remain inactive.
    """
    detector = OverrideDetector()
    detector.load(_make_examples(49))

    assert not detector.activated, (
        f"Detector must NOT be activated with 49 examples. "
        f"example_count={detector.example_count}, threshold=50"
    )
    assert detector.example_count == 49, (
        f"example_count must be 49. Got {detector.example_count}"
    )


# ============================================================================
# Test 2 — 50 examples → detector ACTIVATED
# ============================================================================

def test_override_detector_activated_at_50():
    """
    Loading exactly 50 examples must activate the detector.
    Threshold is inclusive (>= 50).
    """
    detector = OverrideDetector()
    detector.load(_make_examples(50))

    assert detector.activated, (
        f"Detector MUST be activated with 50 examples. "
        f"example_count={detector.example_count}, threshold=50"
    )
    assert detector.example_count == 50, (
        f"example_count must be 50. Got {detector.example_count}"
    )


# ============================================================================
# Test 3 — load_from_graph wires run_query results into the detector
# ============================================================================

def test_load_from_graph_activates_with_50_results():
    """
    load_from_graph must call run_query with the correct source filter
    and activate the singleton when AGE returns >= 50 rows.
    """
    from app.services.override_detector import load_from_graph, override_detector

    mock_graph = AsyncMock()
    mock_graph.run_query.return_value = _make_examples(50)

    asyncio.run(load_from_graph(mock_graph))

    assert override_detector.activated, (
        f"override_detector singleton must be ACTIVATED after loading 50 rows. "
        f"Got example_count={override_detector.example_count}"
    )
    # Verify the correct query was issued (source filter present)
    call_args = mock_graph.run_query.call_args
    query_str = call_args[0][0]
    assert "v_shadow_synthetic_v3" in query_str, (
        f"Query must filter by source='v_shadow_synthetic_v3'. Got: {query_str!r}"
    )
    assert "analyst_correct" in query_str, (
        f"Query must filter by analyst_correct. Got: {query_str!r}"
    )


# ============================================================================
# Test 4 — load_from_graph stays inactive with 49 results
# ============================================================================

def test_load_from_graph_inactive_with_49_results():
    """
    load_from_graph must leave the detector inactive when AGE returns < 50.
    """
    from app.services.override_detector import load_from_graph, override_detector

    mock_graph = AsyncMock()
    mock_graph.run_query.return_value = _make_examples(49)

    asyncio.run(load_from_graph(mock_graph))

    assert not override_detector.activated, (
        f"override_detector must NOT be activated with 49 rows. "
        f"Got example_count={override_detector.example_count}"
    )
