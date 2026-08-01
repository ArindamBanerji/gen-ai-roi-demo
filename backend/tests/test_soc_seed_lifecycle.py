from __future__ import annotations

import ast
from pathlib import Path

import pytest

from copilot_sdk.config import GraphConfigError, require_shared_graph


GRAPH_SCHEMA = Path(__file__).parents[1] / "app" / "graph_schema.py"


def _source() -> str:
    return GRAPH_SCHEMA.read_text(encoding="utf-8")


def test_seed_uses_authorized_graph() -> None:
    source = _source()
    assert 'GraphConfig.load("soc", profile=profile)' in source
    assert 'graph="soc_graph"' in source or 'graph = "soc_graph"' in Path(
        GRAPH_SCHEMA.parents[2] / ".." / "copilot-sdk" / "graph_config.toml"
    ).read_text(encoding="utf-8")
    assert "require_shared_graph(" in source
    assert "create_graph_store(" in source


def test_seed_rejects_unauthorized_graph() -> None:
    with pytest.raises(GraphConfigError, match="requires graph 'soc_graph'"):
        require_shared_graph(
            backend="age",
            graph="other_graph",
            domain="soc",
            profile="production",
        )


def test_seed_schema_creation_idempotent() -> None:
    tree = ast.parse(_source())
    ensure_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "ensure_graph"
    ]
    assert len(ensure_calls) == 1
    assert "await client.ensure_graph()" in _source()


def test_seed_disposable_test_graph_allowed() -> None:
    require_shared_graph(
        backend="age",
        graph="soc_graph_test_seed",
        domain="soc",
        profile="test",
    )


def test_seed_does_not_construct_raw_client_outside_config() -> None:
    tree = ast.parse(_source())
    raw_constructions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "AGEClient"
    ]
    assert raw_constructions == []

    client_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "get_graph_client"
    ]
    assert len(client_calls) == 1
    assert _source().index("require_shared_graph(") < _source().index(
        "get_graph_client"
    )
