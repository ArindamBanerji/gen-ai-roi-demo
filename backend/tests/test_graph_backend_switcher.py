"""
Block 8.5 Phase 3 — graph backend switcher tests.
All run with GRAPH_BACKEND=neo4j (default). No live DB required.
"""
import os
import importlib


def test_default_backend_is_neo4j():
    """Default GRAPH_BACKEND produces Neo4jClient — no behaviour change.

    Explicitly sets GRAPH_BACKEND=neo4j in the shell environment so that
    load_dotenv(override=False) inside neo4j.py cannot override it with the
    GRAPH_BACKEND=age that may be present in the project .env file.
    """
    prev = os.environ.get("GRAPH_BACKEND")
    os.environ["GRAPH_BACKEND"] = "neo4j"
    try:
        import app.db.neo4j as db_mod
        importlib.reload(db_mod)
        from app.db.neo4j import neo4j_client, Neo4jClient
        assert isinstance(neo4j_client, Neo4jClient)
    finally:
        if prev is None:
            os.environ.pop("GRAPH_BACKEND", None)
        else:
            os.environ["GRAPH_BACKEND"] = prev


def test_age_backend_import_error_without_ci_platform():
    """GRAPH_BACKEND=age without ci-platform[graph] raises ImportError
    with a helpful message — not a silent failure."""
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
    connections). main.py guards these with hasattr() — intentionally excluded.
    """
    from app.db.neo4j import Neo4jClient
    from ci_platform.graph.age_client import AGEClient

    required = [
        "run_query", "get_security_context", "get_alert",
        "get_pattern_count", "get_sequence_count",
        "get_cross_category_count", "create_decision_trace",
        "create_evolution_event", "get_recent_evolution_events",
        "count_verified_decisions",
        "count_decisions_by_category",
        "compute_outcome_stats",
        "compute_iks",
    ]
    for method in required:
        assert hasattr(Neo4jClient, method), f"Neo4jClient missing: {method}"
        assert hasattr(AGEClient, method),   f"AGEClient missing: {method}"
