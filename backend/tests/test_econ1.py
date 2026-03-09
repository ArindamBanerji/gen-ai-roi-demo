"""
test_econ1.py — ECON-1 unit tests (no live Neo4j required).

Tests the /api/soc/economics endpoint added to metrics.py.

Run from backend/:
    pytest tests/test_econ1.py -v
"""

import asyncio
import sys
import os
from unittest.mock import patch, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Constants mirrored from the endpoint for expected-value calculations
_ANALYST_HOURLY        = 85.0
_MANUAL_TRIAGE_HOURS   = 0.75
_AI_TRIAGE_HOURS       = 0.133
_BREACH_COST           = 150_000.0
_BREACH_PROB           = 0.02


def _dec_row(total=0, correct=0, escalations=0, suppressions=0,
             investigations=0, monitors=0):
    return [{
        "total": total,
        "correct_count": correct,
        "escalations": escalations,
        "suppressions": suppressions,
        "investigations": investigations,
        "monitors": monitors,
    }]


def _usr_row(total_users=0, privileged_users=0, elevated_users=0):
    return [{"total_users": total_users,
             "privileged_users": privileged_users,
             "elevated_users": elevated_users}]


# ============================================================================
# TEST 1 — /api/soc/economics route is registered
# ============================================================================

def test_economics_endpoint_registered():
    """GET /api/soc/economics must be registered on the FastAPI app."""
    from app.main import app
    routes = [r.path for r in app.routes]
    assert "/api/soc/economics" in routes, (
        f"Route not found. Registered routes: {routes}"
    )


# ============================================================================
# TEST 2 — Zero decisions: no ZeroDivisionError, all zeros
# ============================================================================

def test_economics_zero_decisions_safe():
    """Mock Neo4j: 0 decisions, 0 users. Assert safe zero-state response."""
    from app.routers.metrics import get_economics

    async def _run():
        with patch("app.routers.metrics.neo4j_client") as mock_neo:
            mock_neo.run_query = AsyncMock(side_effect=[
                _dec_row(0, 0, 0, 0, 0, 0),
                _usr_row(0, 0, 0),
            ])
            return await get_economics()

    result = asyncio.run(_run())
    assert result["decisions"]["correct_rate"] == 0.0, (
        f"correct_rate expected 0.0, got {result['decisions']['correct_rate']}"
    )
    assert result["economics"]["time_saved_hours"] == 0.0, (
        f"time_saved_hours expected 0.0, got {result['economics']['time_saved_hours']}"
    )
    assert result["economics"]["cost_saved_usd"] == 0.0, (
        f"cost_saved_usd expected 0.0, got {result['economics']['cost_saved_usd']}"
    )


# ============================================================================
# TEST 3 — Cost calculation: 100 decisions, 80 correct, 20 escalations
# ============================================================================

def test_economics_cost_calculation():
    """
    Mock: 100 decisions, 80 correct, 20 escalations.
    time_saved = 100 * (0.75 - 0.133) = 61.7 hours
    cost_saved = 61.7 * 85 = $5,244.50
    """
    from app.routers.metrics import get_economics

    async def _run():
        with patch("app.routers.metrics.neo4j_client") as mock_neo:
            mock_neo.run_query = AsyncMock(side_effect=[
                _dec_row(100, 80, 20, 30, 30, 20),
                _usr_row(200, 20, 40),
            ])
            return await get_economics()

    result = asyncio.run(_run())
    expected_time = round(100 * (_MANUAL_TRIAGE_HOURS - _AI_TRIAGE_HOURS), 1)
    expected_cost = round(expected_time * _ANALYST_HOURLY, 2)

    assert abs(result["economics"]["time_saved_hours"] - expected_time) <= 0.1, (
        f"time_saved_hours expected ~{expected_time}, "
        f"got {result['economics']['time_saved_hours']}"
    )
    assert abs(result["economics"]["cost_saved_usd"] - expected_cost) <= 0.01, (
        f"cost_saved_usd expected ~{expected_cost}, "
        f"got {result['economics']['cost_saved_usd']}"
    )


# ============================================================================
# TEST 4 — Risk reduction: 20 escalations, correct_rate=0.8
# ============================================================================

def test_risk_reduction_calculation():
    """
    Mock: 100 decisions, 80 correct, 20 escalations.
    correct_escalations = 20 * 0.8 = 16
    risk_reduction = 16 * 150_000 * 0.02 = $48,000
    """
    from app.routers.metrics import get_economics

    async def _run():
        with patch("app.routers.metrics.neo4j_client") as mock_neo:
            mock_neo.run_query = AsyncMock(side_effect=[
                _dec_row(100, 80, 20, 0, 0, 0),
                _usr_row(0, 0, 0),
            ])
            return await get_economics()

    result = asyncio.run(_run())
    correct_rate = 80 / 100
    expected_risk = round(20 * correct_rate * _BREACH_COST * _BREACH_PROB, 2)

    assert abs(result["economics"]["risk_reduction_usd"] - expected_risk) <= 0.01, (
        f"risk_reduction_usd expected ~{expected_risk}, "
        f"got {result['economics']['risk_reduction_usd']}"
    )


# ============================================================================
# TEST 5 — total_value_usd == cost_saved + risk_reduction
# ============================================================================

def test_total_value_is_sum():
    """total_value_usd must equal cost_saved_usd + risk_reduction_usd."""
    from app.routers.metrics import get_economics

    async def _run():
        with patch("app.routers.metrics.neo4j_client") as mock_neo:
            mock_neo.run_query = AsyncMock(side_effect=[
                _dec_row(50, 40, 10, 15, 15, 10),
                _usr_row(100, 10, 20),
            ])
            return await get_economics()

    result = asyncio.run(_run())
    econ = result["economics"]
    expected_total = round(econ["cost_saved_usd"] + econ["risk_reduction_usd"], 2)

    assert abs(econ["total_value_usd"] - expected_total) <= 0.01, (
        f"total_value_usd={econ['total_value_usd']} != "
        f"cost_saved + risk_reduction = {expected_total}"
    )


# ============================================================================
# TEST 6 — economics.estimated is always True
# ============================================================================

def test_economics_estimated_flag_always_true():
    """Economics estimates are always labeled estimated=True regardless of data."""
    from app.routers.metrics import get_economics

    async def _run():
        with patch("app.routers.metrics.neo4j_client") as mock_neo:
            mock_neo.run_query = AsyncMock(side_effect=[
                _dec_row(10, 8, 2, 3, 3, 2),
                _usr_row(50, 5, 10),
            ])
            return await get_economics()

    result = asyncio.run(_run())
    assert result["economics"]["estimated"] is True, (
        f"economics.estimated should always be True, "
        f"got {result['economics']['estimated']}"
    )


# ============================================================================
# TEST 7 — Population counts propagate correctly
# ============================================================================

def test_population_counts_in_response():
    """Mock user query: total=200, privileged=20, elevated=40.
    Assert population fields match."""
    from app.routers.metrics import get_economics

    async def _run():
        with patch("app.routers.metrics.neo4j_client") as mock_neo:
            mock_neo.run_query = AsyncMock(side_effect=[
                _dec_row(0, 0, 0, 0, 0, 0),
                _usr_row(200, 20, 40),
            ])
            return await get_economics()

    result = asyncio.run(_run())
    assert result["population"]["total_users"] == 200, (
        f"total_users expected 200, got {result['population']['total_users']}"
    )
    assert result["population"]["privileged_users"] == 20, (
        f"privileged_users expected 20, got {result['population']['privileged_users']}"
    )
