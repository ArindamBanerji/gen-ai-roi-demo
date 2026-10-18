"""Conformance checks for the renamed SOC AGE graph client module."""

from __future__ import annotations

from importlib import import_module
import logging
from pathlib import Path
from unittest.mock import AsyncMock

import pytest


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


def test_legacy_neo4j_module_removed() -> None:
    """The retired Neo4j adapter must remain absent from the SOC app."""
    with pytest.raises(ModuleNotFoundError):
        import_module("app.db.neo4j")


@pytest.mark.asyncio
async def test_registry_handle_is_permanently_dead_after_shutdown(monkeypatch, caplog) -> None:
    module = import_module("app.db.graph_client")

    class Client:
        run_query = AsyncMock(return_value=[{"ok": True}])

        def get_pool_diagnostics(self):
            return {"pool_size": 2}

        def redacted_dsn(self):
            return "redacted"

    concrete = Client()
    reset_calls: list[tuple[str, str]] = []
    monkeypatch.setattr(module, "_age_factory", lambda *, dsn, graph_name: concrete)
    monkeypatch.setattr(
        module,
        "reset_graph_client",
        lambda dsn, graph: reset_calls.append((dsn, graph)),
    )
    handle = module._RegistryBackedAGEClient("dsn", "graph")

    assert await handle.run_query("RETURN 1") == [{"ok": True}]
    with caplog.at_level(logging.INFO):
        await handle.close()

    assert reset_calls == [("dsn", "graph")]
    assert "[GRAPH] Shutdown client" in caplog.text
    with pytest.raises(RuntimeError, match="Graph client is shut down"):
        handle._current()
    with pytest.raises(RuntimeError, match="Graph client is shut down"):
        await handle.run_query("RETURN 1")


@pytest.mark.asyncio
async def test_reconfiguration_requires_a_new_registry_handle(monkeypatch) -> None:
    module = import_module("app.db.graph_client")
    concrete = type(
        "Client",
        (),
        {"run_query": AsyncMock(return_value=[{"ok": True}])},
    )()
    monkeypatch.setattr(module, "_age_factory", lambda *, dsn, graph_name: concrete)
    monkeypatch.setattr(module, "reset_graph_client", lambda dsn, graph: None)
    old_handle = module._RegistryBackedAGEClient("dsn", "graph")
    await old_handle.close()

    new_handle = module._RegistryBackedAGEClient("dsn", "graph")
    assert await new_handle.run_query("RETURN 1") == [{"ok": True}]
    with pytest.raises(RuntimeError, match="Graph client is shut down"):
        old_handle._current()
