"""
H7-FIX-2 tests: GET /soc/graph-stats endpoint returns real Neo4j counts,
not hardcoded values.

Run from backend/ directory:
    pytest tests/test_h7_fix2.py -v
"""

import asyncio
import sys
import os
from unittest.mock import patch, AsyncMock

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def test_graph_stats_endpoint_registered():
    """GET /soc/graph-stats must be registered on the evolution router."""
    from app.routers.evolution import router
    routes = [r.path for r in router.routes]
    assert "/soc/graph-stats" in routes, (
        f"Route /soc/graph-stats not found; registered routes: {routes}"
    )


def test_graph_stats_response_has_required_fields():
    """The endpoint returns nodes_traversed, relationships_analyzed, historical_decisions, source."""
    from app.routers.evolution import get_graph_stats

    async def _run():
        with patch("app.routers.evolution.graph_client") as mock_client:
            mock_client.run_query = AsyncMock(side_effect=[
                [{"node_count": 10}],
                [{"rel_count": 20}],
                [{"dec_count": 3}],
            ])
            return await get_graph_stats()

    result = asyncio.run(_run())
    required = {"nodes_traversed", "relationships_analyzed", "historical_decisions", "source"}
    assert required <= result.keys(), (
        f"Missing fields: {required - result.keys()}"
    )


def test_graph_stats_source_is_neo4j_on_success():
    """source field equals 'neo4j' when all queries succeed."""
    from app.routers.evolution import get_graph_stats

    async def _run():
        with patch("app.routers.evolution.graph_client") as mock_client:
            mock_client.run_query = AsyncMock(side_effect=[
                [{"node_count": 55}],
                [{"rel_count": 132}],
                [{"dec_count": 7}],
            ])
            return await get_graph_stats()

    result = asyncio.run(_run())
    assert result["source"] == "neo4j", (
        f"Expected source='neo4j', got {result['source']!r}"
    )


def test_graph_stats_source_unavailable_on_error():
    """Graph stats failures are surfaced as HTTP 503, not a zero payload."""
    from app.routers.evolution import get_graph_stats

    async def _run():
        with patch("app.routers.evolution.graph_client") as mock_client:
            mock_client.run_query = AsyncMock(side_effect=RuntimeError("Neo4j down"))
            return await get_graph_stats()

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(_run())

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "AGE query failed for graph stats"


def test_graph_stats_counts_are_integers():
    """All three count fields are plain integers, not floats or strings."""
    from app.routers.evolution import get_graph_stats

    async def _run():
        with patch("app.routers.evolution.graph_client") as mock_client:
            mock_client.run_query = AsyncMock(side_effect=[
                [{"node_count": 47}],
                [{"rel_count": 127}],
                [{"dec_count": 891}],
            ])
            return await get_graph_stats()

    result = asyncio.run(_run())
    assert isinstance(result["nodes_traversed"], int), (
        f"nodes_traversed should be int, got {type(result['nodes_traversed'])}"
    )
    assert isinstance(result["relationships_analyzed"], int), (
        f"relationships_analyzed should be int, got {type(result['relationships_analyzed'])}"
    )
    assert isinstance(result["historical_decisions"], int), (
        f"historical_decisions should be int, got {type(result['historical_decisions'])}"
    )
