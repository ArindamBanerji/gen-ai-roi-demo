"""
H7-FIX-4 tests: Tab 4 weekly trends, evolution events, and decision economics
served from AGE, not static/mock generators.

Run from backend/ directory:
    pytest tests/test_h7_fix4.py -v
"""

import asyncio
import pytest
import pathlib
import sys
import os
from unittest.mock import patch, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ============================================================================
# TEST 1 — No static weekly arrays (W1/W2/W3/W4) in soc router
# ============================================================================

def test_no_static_trend_arrays_in_router():
    """soc.py must not contain hardcoded weekly labels "W1"/"W2" outside of
    context where they're paired with an estimated/note flag."""
    content = pathlib.Path("app/routers/soc.py").read_text()
    # If the literal "W1" is present it must live alongside an "estimated" guard
    assert '"W1"' not in content or "estimated" in content, (
        '"W1" found in app/routers/soc.py without accompanying estimated flag'
    )
    assert '"W2"' not in content or "estimated" in content, (
        '"W2" found in app/routers/soc.py without accompanying estimated flag'
    )


# ============================================================================
# TEST 2 — Evolution events endpoint registered
# ============================================================================

def test_evolution_events_endpoint_registered():
    """At least one route containing 'evolution' or 'event' must be
    registered on the application."""
    from app.main import app
    routes = [r.path for r in app.routes]
    event_routes = [r for r in routes if "evolution" in r or "event" in r]
    assert len(event_routes) > 0, (
        f"No evolution/event route found; registered routes: {routes}"
    )


# ============================================================================
# TEST 3 — Decision economics endpoint shape (10 decisions, 8 correct)
# ============================================================================

@pytest.mark.age
def test_economics_endpoint_shape(age_graph):
    """Seed AGE with 10 decisions / 8 correct.  Assert the response
    contains the expected computed fields."""
    from app.routers.metrics import get_decision_economics

    async def _run():
        with patch("app.routers.metrics.graph_client", age_graph.client):
            return await get_decision_economics()

    for index in range(10):
        age_graph.decision(correct=index < 8)
    result = asyncio.run(_run())
    assert result["decisions_made"] == 10, f"Expected 10, got {result['decisions_made']}"
    assert abs(result["correct_rate"] - 0.8) < 1e-6, f"Expected 0.8, got {result['correct_rate']}"
    assert abs(result["false_positive_rate"] - 0.2) < 1e-6, (
        f"Expected 0.2, got {result['false_positive_rate']}"
    )
    assert result["time_saved_estimated"] is True, (
        "time_saved_estimated must be True"
    )


# ============================================================================
# TEST 4 — Division-by-zero safe when 0 decisions
# ============================================================================

@pytest.mark.age
def test_economics_zero_decisions_safe(age_graph):
    """Read an empty AGE graph.  Endpoint must not raise and must
    return correct_rate=0.0, time_saved_hours=0.0."""
    from app.routers.metrics import get_decision_economics

    async def _run():
        with patch("app.routers.metrics.graph_client", age_graph.client):
            return await get_decision_economics()

    result = asyncio.run(_run())
    assert result["decisions_made"] == 0
    assert result["correct_rate"] == 0.0, f"Expected 0.0, got {result['correct_rate']}"
    assert result["time_saved_hours"] == 0.0, (
        f"Expected 0.0, got {result['time_saved_hours']}"
    )


# ============================================================================
# TEST 5 — Weekly trends returns estimated=True with note when no data
# ============================================================================

@pytest.mark.age
def test_weekly_trends_empty_with_note_when_no_data(age_graph):
    """Read an empty AGE graph.  Response must have estimated=True
    and a non-empty note string."""
    from app.routers.metrics import get_weekly_trends

    async def _run():
        with patch("app.routers.metrics.graph_client", age_graph.client):
            return await get_weekly_trends()

    result = asyncio.run(_run())
    assert result["data"] == [], f"Expected empty list, got {result['data']}"
    assert result["estimated"] is True, (
        f"Expected estimated=True when no decisions; got {result['estimated']}"
    )
    assert isinstance(result.get("note"), str) and len(result["note"]) > 0, (
        "note must be a non-empty string when estimated=True"
    )


# ============================================================================
# TEST 6 — Backend imports cleanly
# ============================================================================

def test_backend_import_clean():
    """Backend must import cleanly with the new Tab 4 endpoints wired in."""
    from app.main import app
    assert app is not None
