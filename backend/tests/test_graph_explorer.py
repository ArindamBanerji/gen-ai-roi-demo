"""
Tests for Phase 8: GraphExplorerService and graph explorer endpoints.

Coverage:
  test_validate_safe_query         -- MATCH query passes validation
  test_validate_blocks_mutation    -- DELETE / CREATE / SET queries fail validation
  test_top_nodes_endpoint          -- GET /api/soc/graph/top-nodes returns nodes list
  test_graph_summary               -- GET /api/soc/graph/summary returns total_nodes > 0
  test_prebuilt_queries_list       -- GET /api/soc/graph/prebuilt-queries returns 5 queries
  test_prebuilt_query_run          -- POST /api/soc/graph/prebuilt/top_risk_users returns rows
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.services.graph_explorer import GraphExplorerService, PREBUILT_QUERIES


# ---------------------------------------------------------------------------
# Shared mock helpers
# ---------------------------------------------------------------------------

def _fake_neo4j_for_summary():
    """Returns two different result sets depending on which summary query is called."""
    call_count = [0]

    async def run_query(query, params=None):
        call_count[0] += 1
        if "labels(n)" in query:
            # node-count query
            return [
                {"label": "Alert",   "cnt": 6},
                {"label": "User",    "cnt": 4},
                {"label": "Asset",   "cnt": 5},
            ]
        if "type(r)" in query:
            # relationship-count query
            return [
                {"type": "INVOLVES",    "cnt": 6},
                {"type": "DECIDED_ON",  "cnt": 3},
            ]
        return []

    class _FakeNeo4j:
        pass
    _FakeNeo4j.run_query = staticmethod(run_query)
    return _FakeNeo4j()


def _fake_neo4j_rows(rows: list):
    async def run_query(query, params=None):
        return rows
    class _FakeNeo4j:
        pass
    _FakeNeo4j.run_query = staticmethod(run_query)
    return _FakeNeo4j()


# ---------------------------------------------------------------------------
# Test 1: validate_query accepts MATCH
# ---------------------------------------------------------------------------

def test_validate_safe_query():
    """MATCH queries pass validation; RETURN / WITH / OPTIONAL MATCH also pass."""
    assert GraphExplorerService.validate_query("MATCH (n:User) RETURN n.name") is True
    assert GraphExplorerService.validate_query("  match (n) return n  ") is True   # case-insensitive
    assert GraphExplorerService.validate_query("RETURN 1 AS one") is True
    assert GraphExplorerService.validate_query(
        "OPTIONAL MATCH (n:Alert) RETURN n.id"
    ) is True


# ---------------------------------------------------------------------------
# Test 2: validate_query blocks mutation keywords
# ---------------------------------------------------------------------------

def test_validate_blocks_mutation():
    """DELETE, CREATE, SET, MERGE queries are blocked."""
    bad_queries = [
        "DELETE (n:Alert)",
        "MATCH (n) DELETE n",
        "CREATE (n:User {name: 'x'})",
        "MATCH (n) SET n.foo = 1",
        "MERGE (n:Alert {id: 'x'})",
        "MATCH (n) DETACH DELETE n",
        "DROP INDEX ON :User(id)",
    ]
    for q in bad_queries:
        assert GraphExplorerService.validate_query(q) is False, (
            f"Expected False for blocked query: {q!r}"
        )


# ---------------------------------------------------------------------------
# Test 3: GET /api/soc/graph/top-nodes returns nodes list
# ---------------------------------------------------------------------------

def test_top_nodes_endpoint():
    """GET /api/soc/graph/top-nodes returns {"nodes": [...], "count": N}."""
    from app.main import app

    sample_rows = [
        {"id": "jsmith@company.com", "type": "User",  "display_name": "John Smith", "connections": 5},
        {"id": "ALERT-7823",          "type": "Alert", "display_name": "ALERT-7823", "connections": 3},
    ]

    async def fake_run_query(query, params=None):
        return sample_rows

    with patch("app.routers.framework_router.neo4j_client") as mock_neo4j:
        mock_neo4j.run_query = fake_run_query
        client = TestClient(app)
        resp = client.get("/api/soc/graph/top-nodes")

    assert resp.status_code == 200, f"Status {resp.status_code}: {resp.text[:300]}"
    data = resp.json()
    assert "nodes" in data, f"Missing 'nodes': {data}"
    assert "count" in data, f"Missing 'count': {data}"
    assert isinstance(data["nodes"], list)
    assert data["count"] == len(data["nodes"])


# ---------------------------------------------------------------------------
# Test 4: GET /api/soc/graph/summary returns total_nodes > 0
# ---------------------------------------------------------------------------

def test_graph_summary():
    """GET /api/soc/graph/summary returns total_nodes, total_relationships, dicts."""
    from app.main import app

    call_index = [0]

    async def fake_run_query(query, params=None):
        call_index[0] += 1
        if "labels(n)" in query:
            return [{"label": "Alert", "cnt": 6}, {"label": "User", "cnt": 4}]
        if "type(r)" in query:
            return [{"type": "INVOLVES", "cnt": 6}]
        return []

    with patch("app.routers.framework_router.neo4j_client") as mock_neo4j:
        mock_neo4j.run_query = fake_run_query
        client = TestClient(app)
        resp = client.get("/api/soc/graph/summary")

    assert resp.status_code == 200, f"Status {resp.status_code}: {resp.text[:300]}"
    data = resp.json()
    assert "total_nodes"         in data, data
    assert "total_relationships" in data, data
    assert "node_types"          in data, data
    assert "relationship_types"  in data, data
    assert data["total_nodes"] > 0, f"total_nodes should be > 0: {data}"


# ---------------------------------------------------------------------------
# Test 5: GET /api/soc/graph/prebuilt-queries returns 5 queries
# ---------------------------------------------------------------------------

def test_prebuilt_queries_list():
    """GET /api/soc/graph/prebuilt-queries returns exactly 5 pre-built queries."""
    from app.main import app

    with patch("app.routers.framework_router.neo4j_client"):
        client = TestClient(app)
        resp = client.get("/api/soc/graph/prebuilt-queries")

    assert resp.status_code == 200, f"Status {resp.status_code}: {resp.text[:300]}"
    data = resp.json()
    assert "queries" in data, data
    assert "count"   in data, data
    assert data["count"] == 5, (
        f"Expected 5 pre-built queries, got {data['count']}: "
        f"{[q['key'] for q in data['queries']]}"
    )
    keys = {q["key"] for q in data["queries"]}
    assert keys == set(PREBUILT_QUERIES.keys()), (
        f"Pre-built query keys mismatch: {keys}"
    )


# ---------------------------------------------------------------------------
# Test 6: POST /api/soc/graph/prebuilt/top_risk_users returns rows
# ---------------------------------------------------------------------------

def test_prebuilt_query_run():
    """POST /api/soc/graph/prebuilt/top_risk_users returns rows list."""
    from app.main import app

    sample_user_rows = [
        {"name": "John Smith",  "dept": "Finance",    "risk": 0.92},
        {"name": "Alice Lee",   "dept": "Engineering", "risk": 0.78},
    ]

    async def fake_run_query(query, params=None):
        return sample_user_rows

    with patch("app.routers.framework_router.neo4j_client") as mock_neo4j:
        mock_neo4j.run_query = fake_run_query
        client = TestClient(app)
        resp = client.post("/api/soc/graph/prebuilt/top_risk_users")

    assert resp.status_code == 200, f"Status {resp.status_code}: {resp.text[:300]}"
    data = resp.json()
    assert "rows"  in data, f"Missing 'rows': {data}"
    assert "count" in data, f"Missing 'count': {data}"
    assert data["count"] == 2
    assert data["rows"][0]["name"] == "John Smith"
