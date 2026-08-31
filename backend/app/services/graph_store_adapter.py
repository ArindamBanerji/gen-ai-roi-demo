"""SOC adapter for shared AGE state persistence.

The legacy ``graph_client`` remains available for the many SOC query callers.
State owned by services in this package is exposed through the GraphStore
contract and is backed by the same configured AGE graph.
"""

from __future__ import annotations

from typing import Any

from ci_platform.graph.age_sdk_adapter import AGEGraphStoreAdapter


class GraphStoreAdapter:
    """Compose the legacy AGE client with the typed GraphStore state API."""

    def __init__(self, graph_client: Any, store: Any) -> None:
        if graph_client is None:
            raise ValueError("graph_client is required")
        if store is None:
            raise ValueError("AGE GraphStore is required")
        self._graph_client = graph_client
        self._store = store

    @property
    def graph_client(self) -> Any:
        return self._graph_client

    def save_evolution(self, domain: str, key: str, payload: dict[str, Any]) -> None:
        self._store.save_evolution(domain, key, payload)

    def get_evolution(self, domain: str, key: str) -> dict[str, Any] | None:
        return self._store.get_evolution(domain, key)

    def save_posterior(self, domain: str, key: str, payload: dict[str, Any]) -> None:
        self._store.save_posterior(domain, key, payload)

    def get_posterior(self, domain: str, key: str) -> dict[str, Any] | None:
        return self._store.get_posterior(domain, key)

    def save_evolution_event(self, **kwargs: Any) -> None:
        self._store.write_evolution_event(**kwargs)

    def __getattr__(self, name: str) -> Any:
        """Delegate existing GraphStore operations to the AGE adapter."""
        return getattr(self._store, name)


def create_soc_graph_store(graph_client: Any, graph_config: Any) -> GraphStoreAdapter:
    """Build the SOC state adapter from the typed shared-graph config."""
    backend = str(getattr(graph_config, "backend", "")).lower()
    if backend != "age":
        raise ValueError(f"SOC state requires AGE backend, got {backend!r}")
    dsn = str(getattr(graph_config, "dsn", "") or "").strip()
    graph_name = str(getattr(graph_config, "graph", "") or "").strip()
    if not dsn or not graph_name:
        raise ValueError("SOC GraphConfig must provide AGE DSN and graph")
    store = AGEGraphStoreAdapter(dsn=dsn, graph_name=graph_name, domain="soc")
    return GraphStoreAdapter(graph_client, store)
