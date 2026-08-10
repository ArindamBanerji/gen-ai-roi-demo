"""
Block 8.5 Phase 3 -- graph backend switcher tests.
The legacy AGE path is tested for explicit retirement. No live DB required.
"""
import os
import importlib
import pytest

from copilot_sdk.config import GraphConfigError


def test_legacy_graph_backend_is_retired():
    """The retired Aura path fails clearly instead of constructing a client."""
    prev = os.environ.get("GRAPH_BACKEND")
    os.environ["GRAPH_BACKEND"] = "neo4j"
    try:
        import app.db.graph_client as db_mod
        with pytest.raises(GraphConfigError, match="Legacy AGE backend is retired"):
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
        import app.db.graph_client as db_mod
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


def test_graph_client_removed():
    import app.db.graph_client as db_mod

    assert not hasattr(db_mod, "GraphClient")

