"""
H7-FIX-3 tests: Tab 1 SOC metrics served from real AGE queries, not mock
generators.

Run from backend/ directory:
    pytest tests/test_h7_fix3.py -v
"""

import asyncio
import pytest
import pathlib
import sys
import os
from unittest.mock import patch, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ============================================================================
# TEST 1 — No random generators in soc router
# ============================================================================

def test_no_random_generators_in_soc_router():
    """soc.py must not contain any random.random(), random.randint(), or
    random.uniform() calls -- every number must trace to AGE or carry
    estimated=True."""
    content = pathlib.Path("app/routers/soc.py").read_text()
    assert "random.random()" not in content, (
        "random.random() found in app/routers/soc.py"
    )
    assert "random.randint(" not in content, (
        "random.randint( found in app/routers/soc.py"
    )
    assert "random.uniform(" not in content, (
        "random.uniform( found in app/routers/soc.py"
    )


# ============================================================================
# TEST 2 — Metrics endpoint registered
# ============================================================================

def test_metrics_endpoint_registered():
    """At least one route containing 'metric', 'stat', 'dashboard', or
    'analytics' must be registered on the app."""
    from app.main import app
    routes = [r.path for r in app.routes]
    metric_routes = [
        r for r in routes
        if any(x in r for x in ["metric", "stat", "dashboard", "analytics"])
    ]
    assert len(metric_routes) > 0, (
        f"No metrics endpoint found; registered routes: {routes}"
    )


# ============================================================================
# TEST 3 — Metrics response is deterministic (no random generators)
# ============================================================================

@pytest.mark.age
def test_metrics_response_has_no_random_floats(age_graph):
    """Calling the analytics endpoint twice with the same persisted AGE data
    must produce identical responses.  Random generators would break this."""
    from app.routers.soc import get_soc_analytics

    for index in range(5):
        age_graph.alert(category="credential_access")
    for index in range(3):
        age_graph.decision(correct=index < 2)
    async def _run():
        with patch("app.routers.soc.graph_client", age_graph.client):
            return await get_soc_analytics(), await get_soc_analytics()

    first, second = asyncio.run(_run())
    assert first["source"] == "graph"
    assert first["total_alerts"] == 5
    assert first["total_decisions"] == 3
    assert first["correct_decisions"] == 2
    assert first == second, (
        f"Two identical calls returned different results:\nfirst={first}\nsecond={second}"
    )


# ============================================================================
# TEST 4 — estimated flag has note field
# ============================================================================

@pytest.mark.age
def test_estimated_flag_populated_when_used(age_graph):
    """Any metric with estimated=True must also have a non-empty 'note'."""
    from app.routers.soc import get_soc_analytics

    async def _run():
        with patch("app.routers.soc.graph_client", age_graph.client):
            return await get_soc_analytics()

    result = asyncio.run(_run())
    assert result["source"] == "graph"
    for item in result.get("estimated_metrics", []):
        if item.get("estimated"):
            assert "note" in item and item["note"], (
                f"Estimated metric {item.get('label')!r} has estimated=True "
                f"but no non-empty 'note' field"
            )


# ============================================================================
# TEST 5 — Category breakdown shape
# ============================================================================

@pytest.mark.age
def test_category_breakdown_shape(age_graph):
    """category_breakdown must be a list of dicts with 'category' (str) and
    'count' (int >= 0) keys."""
    from app.routers.soc import get_soc_analytics

    for category, count in [("credential_access", 5), ("data_exfiltration", 3), ("insider_threat", 2)]:
        for _ in range(count):
            age_graph.alert(category=category)
    async def _run():
        with patch("app.routers.soc.graph_client", age_graph.client):
            return await get_soc_analytics()

    result = asyncio.run(_run())
    breakdown = result["category_breakdown"]
    assert {row["category"]: row["count"] for row in breakdown} == {"credential_access": 5, "data_exfiltration": 3, "insider_threat": 2}
    assert isinstance(breakdown, list), (
        f"category_breakdown should be list, got {type(breakdown)}"
    )
    for item in breakdown:
        assert "category" in item, f"Missing 'category' key in {item}"
        assert "count" in item, f"Missing 'count' key in {item}"
        assert isinstance(item["count"], int), (
            f"'count' should be int, got {type(item['count'])} in {item}"
        )
        assert item["count"] >= 0, f"'count' should be >= 0, got {item['count']}"


# ============================================================================
# TEST 6 — Backend imports cleanly
# ============================================================================

def test_backend_import_clean():
    """Backend must import cleanly with the new analytics endpoint wired in."""
    from app.main import app
    assert app is not None
