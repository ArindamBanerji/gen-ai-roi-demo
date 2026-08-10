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
from unittest.mock import patch, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


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

def test_mttd_estimated_when_no_timestamps():
    """Mock AGE returning sample_size=0 for MTTD.
    Assert mttd['estimated']=True and mttd['value_minutes']=None."""
    from app.routers.metrics import get_operational_metrics

    async def _run():
        with patch("app.routers.metrics.graph_client") as mock_neo:
            mock_neo.run_query = AsyncMock(side_effect=[
                [{"avg_mttd_seconds": None, "sample_size": 0}],   # MTTD
                [{"avg_mttr_seconds": None, "sample_size": 0}],   # MTTR
                [{"total": 0, "fp_count": 0}],                     # FP rate
            ])
            return await get_operational_metrics()

    result = asyncio.run(_run())
    assert result["mttd"]["estimated"] is True, (
        f"mttd.estimated should be True, got {result['mttd']['estimated']}"
    )
    assert result["mttd"]["value_minutes"] is None, (
        f"mttd.value_minutes should be None, got {result['mttd']['value_minutes']}"
    )


# ============================================================================
# TEST 4 — MTTR estimated when no verified outcomes
# ============================================================================

def test_mttr_estimated_when_no_verified_outcomes():
    """Mock AGE returning sample_size=0 for MTTR query.
    Assert mttr['estimated']=True and mttr['value_minutes']=None."""
    from app.routers.metrics import get_operational_metrics

    async def _run():
        with patch("app.routers.metrics.graph_client") as mock_neo:
            mock_neo.run_query = AsyncMock(side_effect=[
                [{"avg_mttd_seconds": None, "sample_size": 0}],   # MTTD
                [{"avg_mttr_seconds": None, "sample_size": 0}],   # MTTR
                [{"total": 0, "fp_count": 0}],                     # FP rate
            ])
            return await get_operational_metrics()

    result = asyncio.run(_run())
    assert result["mttr"]["estimated"] is True, (
        f"mttr.estimated should be True, got {result['mttr']['estimated']}"
    )
    assert result["mttr"]["value_minutes"] is None, (
        f"mttr.value_minutes should be None, got {result['mttr']['value_minutes']}"
    )


# ============================================================================
# TEST 5 — FP rate computed correctly
# ============================================================================

def test_fp_rate_computed_correctly():
    """Mock AGE: total=20, fp_count=4.
    Assert fp_rate['rate']=0.2, fp_rate['estimated']=False."""
    from app.routers.metrics import get_operational_metrics

    async def _run():
        with patch("app.routers.metrics.graph_client") as mock_neo:
            mock_neo.run_query = AsyncMock(side_effect=[
                [{"avg_mttd_seconds": None, "sample_size": 0}],   # MTTD
                [{"avg_mttr_seconds": None, "sample_size": 0}],   # MTTR
                [{"total": 20, "fp_count": 4}],                    # FP rate
            ])
            return await get_operational_metrics()

    result = asyncio.run(_run())
    assert result["fp_rate"]["rate"] == 0.2, (
        f"fp_rate.rate expected 0.2, got {result['fp_rate']['rate']}"
    )
    assert result["fp_rate"]["estimated"] is False, (
        f"fp_rate.estimated should be False when data present"
    )


# ============================================================================
# TEST 6 — FP rate zero decisions safe (no ZeroDivisionError)
# ============================================================================

def test_fp_rate_zero_decisions_safe():
    """Mock AGE: total=0. Assert fp_rate['rate']=None. No ZeroDivisionError."""
    from app.routers.metrics import get_operational_metrics

    async def _run():
        with patch("app.routers.metrics.graph_client") as mock_neo:
            mock_neo.run_query = AsyncMock(side_effect=[
                [{"avg_mttd_seconds": None, "sample_size": 0}],   # MTTD
                [{"avg_mttr_seconds": None, "sample_size": 0}],   # MTTR
                [{"total": 0, "fp_count": 0}],                     # FP rate
            ])
            return await get_operational_metrics()

    result = asyncio.run(_run())
    assert result["fp_rate"]["rate"] is None, (
        f"fp_rate.rate should be None when total=0, got {result['fp_rate']['rate']}"
    )


# ============================================================================
# TEST 7 — Board export shape
# ============================================================================

def test_board_export_shape():
    """Mock AGE calls. Assert response contains all required fields."""
    from app.routers.metrics import get_board_export

    async def _run():
        with patch("app.routers.metrics.graph_client") as mock_neo:
            mock_neo.run_query = AsyncMock(side_effect=[
                [{"total": 5}],                        # decision count
                [{"correct": 4}],                      # correct count
                [{"total": 5, "fp_count": 1}],         # FP count
            ])
            return await get_board_export()

    result = asyncio.run(_run())

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
