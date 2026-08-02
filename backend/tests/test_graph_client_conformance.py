"""Conformance checks for the renamed SOC AGE graph client module."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path


GRAPH_CLIENT_SOURCE = Path(__file__).parents[1] / "app" / "db" / "graph_client.py"


def test_graph_client_uses_graphconfig() -> None:
    module = import_module("app.db.graph_client")
    source = GRAPH_CLIENT_SOURCE.read_text(encoding="utf-8")

    assert module.graph_client is not None
    assert 'GraphConfig.load("soc")' in source


def test_graph_client_resolves_soc_graph() -> None:
    module = import_module("app.db.graph_client")

    assert module._GRAPH_CONFIG.graph == "soc_graph"


def test_no_neo4j_package_dependency() -> None:
    source = GRAPH_CLIENT_SOURCE.read_text(encoding="utf-8")
    import_lines = [
        line.strip()
        for line in source.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]

    assert not any(line == "import neo4j" or line.startswith("from neo4j ") for line in import_lines)


def test_backward_compat_alias_exists() -> None:
    graph_module = import_module("app.db.graph_client")
    legacy_module = import_module("app.db.neo4j")

    assert legacy_module.neo4j_client is graph_module.graph_client
