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

def test_validate_safe_query():
    """Only exact reviewed queries pass; surrounding whitespace is harmless."""
    for meta in PREBUILT_QUERIES.values():
        assert GraphExplorerService.validate_query(meta["cypher"]) is True
        assert GraphExplorerService.validate_query("  " + meta["cypher"] + "\n") is True


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


def test_validate_rejects_call_procedures():
    assert GraphExplorerService.validate_query("CALL db.labels()") is False


def test_validate_rejects_uncatalogued_read_only_match():
    assert GraphExplorerService.validate_query("MATCH (n) RETURN n LIMIT 10") is False


# ---------------------------------------------------------------------------
# Test 3: GET /api/soc/graph/top-nodes returns nodes list
# ---------------------------------------------------------------------------

@pytest.mark.age
def test_top_nodes_endpoint(age_graph, monkeypatch):
    from app.main import app
    age_graph.node("User", id="alice", domain="soc", name="Alice")
    age_graph.alert(alert_id="A1")
    age_graph.query("MATCH (u:User {id: 'alice'}), (a:Alert {alert_id: 'A1'}) CREATE (a)-[:INVOLVES]->(u) RETURN u")
    monkeypatch.setattr("app.routers.framework_router.graph_client", age_graph.client)
    monkeypatch.setattr(app.state, "graph_store", age_graph.store, raising=False)
    data = TestClient(app).get("/api/soc/graph/top-nodes").json()
    assert data["count"] == 2
    assert {row["id"] for row in data["nodes"]} == {"alice", "A1"}
    assert all(row["connections"] == 1 for row in data["nodes"])


# ---------------------------------------------------------------------------
# Test 4: GET /api/soc/graph/summary returns total_nodes > 0
# ---------------------------------------------------------------------------

@pytest.mark.age
def test_graph_summary(age_graph, monkeypatch):
    from app.main import app
    age_graph.alert(alert_id="A1")
    age_graph.alert(alert_id="A2")
    age_graph.node("User", id="alice", domain="soc", name="Alice")
    age_graph.node("User", id="foreign", domain="s2p", name="Foreign")
    age_graph.query("MATCH (u:User {id: 'alice'}), (a:Alert {alert_id: 'A1'}) CREATE (a)-[:INVOLVES]->(u) RETURN u")
    monkeypatch.setattr("app.routers.framework_router.graph_client", age_graph.client)
    data = TestClient(app).get("/api/soc/graph/summary").json()
    assert data["total_nodes"] == 3
    assert data["total_relationships"] == 1
    age_graph.alert(alert_id="A3")
    assert TestClient(app).get("/api/soc/graph/summary").json()["total_nodes"] == 4


# ---------------------------------------------------------------------------
# Test 5: GET /api/soc/graph/prebuilt-queries returns 5 queries
# ---------------------------------------------------------------------------

def test_prebuilt_queries_list():
    """GET /api/soc/graph/prebuilt-queries returns exactly 5 pre-built queries."""
    from app.main import app

    with patch("app.routers.framework_router.graph_client"):
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

@pytest.mark.age
def test_prebuilt_query_run(age_graph, monkeypatch):
    from app.main import app
    for name, risk, domain in [("John Smith", .92, "soc"), ("Alice Lee", .78, "soc"), ("Foreign", 1.0, "s2p")]:
        age_graph.node("User", name=name, department="Finance", risk_level=risk, domain=domain)
    monkeypatch.setattr("app.routers.framework_router.graph_client", age_graph.client)
    response = TestClient(app).post("/api/soc/graph/prebuilt/top_risk_users")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    assert [row["name"] for row in data["rows"]] == ["John Smith", "Alice Lee"]
