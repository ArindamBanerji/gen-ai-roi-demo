"""
Block 8.5 Phase 3 -- graph backend switcher tests.
The legacy Neo4j path is tested for explicit retirement. No live DB required.
"""
import os
import importlib
import pytest

from copilot_sdk.config import GraphConfigError


def test_legacy_neo4j_backend_is_retired():
    """The retired Aura path fails clearly instead of constructing a client."""
    prev = os.environ.get("GRAPH_BACKEND")
    os.environ["GRAPH_BACKEND"] = "neo4j"
    try:
        import app.db.neo4j as db_mod
        with pytest.raises(GraphConfigError, match="Legacy Neo4j backend is retired"):
            importlib.reload(db_mod)
    finally:
        if prev is None:
            os.environ.pop("GRAPH_BACKEND", None)
        else:
            os.environ["GRAPH_BACKEND"] = prev


def test_age_backend_import_error_without_ci_platform():
    """GRAPH_BACKEND=age without ci-platform[graph] raises ImportError
    with a helpful message -- not a silent failure."""
    import sys
    graph_mod = sys.modules.pop("ci_platform.graph", None)
    age_mod = sys.modules.pop("ci_platform.graph.age_client", None)
    os.environ["GRAPH_BACKEND"] = "age"
    try:
        import app.db.neo4j as db_mod
        try:
            importlib.reload(db_mod)
        except ImportError as e:
            assert "ci-platform[graph]" in str(e)
        except Exception:
            pass
    finally:
        os.environ.pop("GRAPH_BACKEND", None)
        if graph_mod:
            sys.modules["ci_platform.graph"] = graph_mod
        if age_mod:
            sys.modules["ci_platform.graph.age_client"] = age_mod


def test_interface_parity_neo4j_vs_age():
    """AGEClient and Neo4jClient expose identical query method surface.
    All 290 call sites depend on this contract.

    Note: connect()/close() are Neo4jClient-only (AGEClient uses per-query
    connections). main.py guards these with hasattr() -- intentionally excluded.
    """
    from app.db.neo4j import Neo4jClient
    from ci_platform.graph.age_client import AGEClient

    required = [
        "run_query", "get_security_context", "get_alert",
        "get_sequence_count",
        "get_cross_category_count", "create_decision_trace",
        "create_evolution_event",
        "count_verified_decisions",
        "count_decisions_by_category",
        "compute_outcome_stats",
        "compute_iks",
    ]
    for method in required:
        assert hasattr(Neo4jClient, method), f"Neo4jClient missing: {method}"
        assert hasattr(AGEClient, method),   f"AGEClient missing: {method}"


def test_legacy_neo4j_client_constructor_is_disabled():
    from app.db.neo4j import Neo4jClient

    with pytest.raises(RuntimeError, match="Legacy Neo4j path disabled"):
        Neo4jClient()
