"""
F4-OVERLAY tests: Operational Outcome Metrics on the ROI dashboard.
MTTD / MTTR / FP rate served from AGE, with estimated=True when no data.
Board-ready JSON export endpoint.

Run from backend/ directory:
    pytest tests/test_f4_overlay.py -v
"""

import asyncio
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture
def metrics_graph(age_graph, monkeypatch):
    """Use an isolated production AGE client, never canned aggregate rows."""
    from app.routers import metrics
    monkeypatch.setattr(metrics, "graph_client", age_graph.client)
    return age_graph


def _decision(graph, identifier, *, correct=True, outcome=None, **props):
    graph.decision(decision_id=identifier, correct=correct, **props)
    if outcome is not None:
        graph.set_properties("Decision", "decision_id", identifier, _domain="soc", outcome=outcome)


# ============================================================================
# TEST 1 — Operational metrics endpoint registered
# ============================================================================

def test_operational_metrics_endpoint_registered():
    """GET /api/soc/operational-metrics must be registered on the app."""
    from app.main import app
    routes = [r.path for r in app.routes]
    assert "/api/soc/operational-metrics" in routes, (
        f"Route not found; registered routes: {routes}"
    )


# ============================================================================
# TEST 2 — Board export endpoint registered
# ============================================================================

def test_board_export_endpoint_registered():
    """GET /api/soc/board-export must be registered on the app."""
    from app.main import app
    routes = [r.path for r in app.routes]
    assert "/api/soc/board-export" in routes, (
        f"Route not found; registered routes: {routes}"
    )


# ============================================================================
# TEST 3 — MTTD estimated when no timestamps
# ============================================================================

@pytest.mark.age
def test_mttd_estimated_when_no_timestamps(metrics_graph):
    """Mock AGE returning sample_size=0 for MTTD.
    Assert mttd['estimated']=True and mttd['value_minutes']=None."""
    from app.routers.metrics import get_operational_metrics

    result = asyncio.run(get_operational_metrics())
    assert result["mttd"]["estimated"] is True, (
        f"mttd.estimated should be True, got {result['mttd']['estimated']}"
    )
    assert result["mttd"]["value_minutes"] is None, (
        f"mttd.value_minutes should be None, got {result['mttd']['value_minutes']}"
    )


# ============================================================================
# TEST 4 — MTTR estimated when no verified outcomes
# ============================================================================

@pytest.mark.age
def test_mttr_estimated_when_no_verified_outcomes(metrics_graph):
    """Mock AGE returning sample_size=0 for MTTR query.
    Assert mttr['estimated']=True and mttr['value_minutes']=None."""
    from app.routers.metrics import get_operational_metrics

    result = asyncio.run(get_operational_metrics())
    assert result["mttr"]["estimated"] is True, (
        f"mttr.estimated should be True, got {result['mttr']['estimated']}"
    )
    assert result["mttr"]["value_minutes"] is None, (
        f"mttr.value_minutes should be None, got {result['mttr']['value_minutes']}"
    )


# ============================================================================
# TEST 5 — FP rate computed correctly
# ============================================================================

@pytest.mark.age
def test_fp_rate_computed_correctly(metrics_graph):
    """Mock AGE: total=20, fp_count=4.
    Assert fp_rate['rate']=0.2, fp_rate['estimated']=False."""
    from app.routers.metrics import get_operational_metrics

    for index in range(20):
        _decision(metrics_graph, f"FP-{index}", correct=index >= 4, outcome="incorrect" if index < 4 else "correct")
    result = asyncio.run(get_operational_metrics())
    assert result["fp_rate"]["rate"] == 0.2, (
        f"fp_rate.rate expected 0.2, got {result['fp_rate']['rate']}"
    )
    assert result["fp_rate"]["estimated"] is False, (
        f"fp_rate.estimated should be False when data present"
    )


# ============================================================================
# TEST 6 — FP rate zero decisions safe (no ZeroDivisionError)
# ============================================================================

@pytest.mark.age
def test_fp_rate_zero_decisions_safe(metrics_graph):
    """Mock AGE: total=0. Assert fp_rate['rate']=None. No ZeroDivisionError."""
    from app.routers.metrics import get_operational_metrics

    result = asyncio.run(get_operational_metrics())
    assert result["fp_rate"]["rate"] is None, (
        f"fp_rate.rate should be None when total=0, got {result['fp_rate']['rate']}"
    )


# ============================================================================
# TEST 7 — Board export shape
# ============================================================================

@pytest.mark.age
def test_board_export_shape(metrics_graph):
    """Mock AGE calls. Assert response contains all required fields."""
    from app.routers.metrics import get_board_export

    for index in range(5):
        _decision(metrics_graph, f"BOARD-{index}", correct=index > 0, outcome="incorrect" if index == 0 else "correct")
    result = asyncio.run(get_board_export())

    assert "generated_at" in result, "Missing 'generated_at'"
    assert "product" in result, "Missing 'product'"
    assert "version" in result, "Missing 'version'"
    assert "data_quality" in result, "Missing 'data_quality'"

    metrics = result.get("metrics", {})
    required_keys = [
        "decisions_made", "correct_rate_pct", "fp_rate_pct",
        "mttd_minutes", "mttr_minutes", "time_saved_hours",
    ]
    for key in required_keys:
        assert key in metrics, f"metrics missing '{key}'"

    # Verify computed values from mocked data (5 decisions, 4 correct, 1 fp)
    assert metrics["decisions_made"] == 5, (
        f"decisions_made expected 5, got {metrics['decisions_made']}"
    )
    assert result["data_quality"] == "live", (
        f"data_quality should be 'live' when decisions exist"
    )
