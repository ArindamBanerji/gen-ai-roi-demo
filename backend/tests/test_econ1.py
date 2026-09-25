"""
test_econ1.py -- ECON-1 unit tests (no live AGE required).

Tests the /api/soc/economics endpoint added to metrics.py.

Run from backend/:
    pytest tests/test_econ1.py -v
"""

import asyncio
import sys
import os
import pytest

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


def _seed_economics_graph(age_graph, *, total=0, correct=0, escalations=0,
                          suppressions=0, investigations=0, monitors=0,
                          users=0, privileged=0, elevated=0):
    """Seed the production AGE adapter; endpoint aggregates must read it."""
    for index in range(total):
        action = (
            "escalate" if index < escalations else "suppress" if index < escalations + suppressions
            else "investigate" if index < escalations + suppressions + investigations else "monitor"
        )
        age_graph.decision(decision_id=f"ECON-{index}", action=action, correct=index < correct)
    for index in range(users):
        level = "privileged" if index < privileged else "elevated" if index < privileged + elevated else "standard"
        age_graph.node("User", id=f"econ-user-{index}", access_level=level)


@pytest.fixture
def economics(age_graph, monkeypatch):
    from app.routers import metrics
    monkeypatch.setattr(metrics, "graph_client", age_graph.client)
    return age_graph


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

@pytest.mark.age
def test_economics_zero_decisions_safe(economics):
    """Mock AGE: 0 decisions, 0 users. Assert safe zero-state response."""
    from app.routers.metrics import get_economics

    _seed_economics_graph(economics)
    result = asyncio.run(get_economics())
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

@pytest.mark.age
def test_economics_cost_calculation(economics):
    """
    Mock: 100 decisions, 80 correct, 20 escalations.
    time_saved = 100 * (0.75 - 0.133) = 61.7 hours
    cost_saved = 61.7 * 85 = $5,244.50
    """
    from app.routers.metrics import get_economics

    _seed_economics_graph(economics, total=100, correct=80, escalations=20, suppressions=30, investigations=30, monitors=20, users=200, privileged=20, elevated=40)
    result = asyncio.run(get_economics())
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

@pytest.mark.age
def test_risk_reduction_calculation(economics):
    """
    Mock: 100 decisions, 80 correct, 20 escalations.
    correct_escalations = 20 * 0.8 = 16
    risk_reduction = 16 * 150_000 * 0.02 = $48,000
    """
    from app.routers.metrics import get_economics

    _seed_economics_graph(economics, total=100, correct=80, escalations=20)
    result = asyncio.run(get_economics())
    correct_rate = 80 / 100
    expected_risk = round(20 * correct_rate * _BREACH_COST * _BREACH_PROB, 2)

    assert abs(result["economics"]["risk_reduction_usd"] - expected_risk) <= 0.01, (
        f"risk_reduction_usd expected ~{expected_risk}, "
        f"got {result['economics']['risk_reduction_usd']}"
    )


# ============================================================================
# TEST 5 — total_value_usd == cost_saved + risk_reduction
# ============================================================================

@pytest.mark.age
def test_total_value_is_sum(economics):
    """total_value_usd must equal cost_saved_usd + risk_reduction_usd."""
    from app.routers.metrics import get_economics

    _seed_economics_graph(economics, total=50, correct=40, escalations=10, suppressions=15, investigations=15, monitors=10, users=100, privileged=10, elevated=20)
    result = asyncio.run(get_economics())
    econ = result["economics"]
    expected_total = round(econ["cost_saved_usd"] + econ["risk_reduction_usd"], 2)

    assert abs(econ["total_value_usd"] - expected_total) <= 0.01, (
        f"total_value_usd={econ['total_value_usd']} != "
        f"cost_saved + risk_reduction = {expected_total}"
    )


# ============================================================================
# TEST 6 — economics.estimated is always True
# ============================================================================

@pytest.mark.age
def test_economics_estimated_flag_always_true(economics):
    """Economics estimates are always labeled estimated=True regardless of data."""
    from app.routers.metrics import get_economics

    _seed_economics_graph(economics, total=10, correct=8, escalations=2, suppressions=3, investigations=3, monitors=2, users=50, privileged=5, elevated=10)
    result = asyncio.run(get_economics())
    assert result["economics"]["estimated"] is True, (
        f"economics.estimated should always be True, "
        f"got {result['economics']['estimated']}"
    )


# ============================================================================
# TEST 7 — Population counts propagate correctly
# ============================================================================

@pytest.mark.age
def test_population_counts_in_response(economics):
    """Mock user query: total=200, privileged=20, elevated=40.
    Assert population fields match."""
    from app.routers.metrics import get_economics

    _seed_economics_graph(economics, users=200, privileged=20, elevated=40)
    result = asyncio.run(get_economics())
    assert result["population"]["total_users"] == 200, (
        f"total_users expected 200, got {result['population']['total_users']}"
    )
    assert result["population"]["privileged_users"] == 20, (
        f"privileged_users expected 20, got {result['population']['privileged_users']}"
    )
