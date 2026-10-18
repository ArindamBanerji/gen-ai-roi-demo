"""SOC AGE graph client. Uses GraphConfig → AGEClient.

Historical name was graph.py — renamed to reflect actual AGE backend
(no AGE dependency).
"""

import asyncio
import logging
import pathlib as _pathlib
import threading
from typing import Any, cast

from copilot_sdk.config import GraphConfig, GraphConfigError, require_shared_graph

log = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv as _load_dotenv
    _env_path = _pathlib.Path(__file__).parents[3] / ".env"
    _load_dotenv(_env_path, override=False)
except ImportError:
    pass


def soc_decision_where(alias: str = "d", active_only: bool = True) -> str:
    """Emit the exact SOC domain and optional active predicate."""
    parts = [f"{alias}.domain = 'soc'"]
    if active_only:
        parts.append(f"({alias}.archived IS NULL OR {alias}.archived <> true)")
    return " AND ".join(parts)


_GRAPH_CONFIG = GraphConfig.load("soc")
_GRAPH_BACKEND = _GRAPH_CONFIG.backend
require_shared_graph(
    backend=_GRAPH_CONFIG.backend,
    graph=_GRAPH_CONFIG.graph,
    domain=_GRAPH_CONFIG.domain,
    profile="production",
    test_mode=_GRAPH_CONFIG.active_test_mode,
)

if _GRAPH_BACKEND != "age":
    raise GraphConfigError(
        "SOC Decision operations require GRAPH_BACKEND=age; "
        f"resolved backend {_GRAPH_BACKEND!r}."
    )

try:
    from ci_platform.graph import (
        get_graph_client as _age_factory,
        reset_graph_client,
    )

    # ``importlib.reload()`` retains the module dictionary. Configuration
    # tests and controlled runtime reconfiguration can therefore leave a
    # client for the previous DSN/graph bound here. Remove that exact registry
    # key first; reset_graph_client drains and closes its owned pool.
    _previous_client = globals().get("graph_client")
    if _previous_client is not None:
        # Close the object itself before consulting the registry. Tests may
        # reload ci_platform.graph.age_client, in which case the previous
        # client belongs to an older registry that the current reset helper
        # cannot see.
        _previous_close = getattr(_previous_client, "close_sync", None)
        if callable(_previous_close):
            _diagnostics = getattr(_previous_client, "get_pool_diagnostics", None)
            _pool_size = 0
            if callable(_diagnostics):
                try:
                    _pool_size = int(_diagnostics().get("pool_size", 0) or 0)
                except Exception:
                    log.debug("Unable to read pool size before client replacement", exc_info=True)
            log.info(
                "[GRAPH] Replacing client for (%s, %s). Closing old pool (%d connections).",
                getattr(_previous_client, "redacted_dsn", lambda: "unknown")(),
                getattr(_previous_client, "_graph", "unknown"),
                _pool_size,
            )
            _previous_close()
        _previous_dsn = getattr(_previous_client, "_dsn", None)
        _previous_graph = getattr(_previous_client, "_graph", None)
        if _previous_dsn and _previous_graph:
            reset_graph_client(str(_previous_dsn), str(_previous_graph))
    reset_graph_client(_GRAPH_CONFIG.dsn, _GRAPH_CONFIG.graph)
    class _RegistryBackedAGEClient:
        """Stable SOC handle that resolves the current keyed AGE client.

        Concrete AGEClient objects remain permanently closed after replacement;
        this composition handle prevents module-level imports from retaining a
        stale concrete client across controlled registry resets.
        """

        def __init__(self, dsn: str, graph: str) -> None:
            self._dsn = dsn
            self._graph = graph
            self._shutdown = False
            self._shutdown_lock = threading.Lock()

        def _current(self) -> Any:
            with self._shutdown_lock:
                if self._shutdown:
                    raise RuntimeError("Graph client is shut down")
                return _age_factory(dsn=self._dsn, graph_name=self._graph)

        def _begin_shutdown(self) -> tuple[bool, Any | None]:
            with self._shutdown_lock:
                if self._shutdown:
                    return False, None
                client = _age_factory(dsn=self._dsn, graph_name=self._graph)
                self._shutdown = True
                return True, client

        def _log_shutdown(self, client: Any) -> None:
            diagnostics = getattr(client, "get_pool_diagnostics", None)
            pool_size = 0
            if callable(diagnostics):
                try:
                    pool_size = int(diagnostics().get("pool_size", 0) or 0)
                except (AttributeError, TypeError, ValueError):
                    log.debug("Unable to read pool size before graph shutdown", exc_info=True)
            log.info(
                "[GRAPH] Shutdown client for (%s, %s). Closing pool (%d connections).",
                getattr(client, "redacted_dsn", lambda: "unknown")(),
                self._graph,
                pool_size,
            )

        async def connect(self) -> None:
            await self._current().connect()

        async def close(self) -> None:
            started, client = self._begin_shutdown()
            if not started or client is None:
                return
            self._log_shutdown(client)
            await asyncio.to_thread(reset_graph_client, self._dsn, self._graph)

        def close_sync(self) -> None:
            started, client = self._begin_shutdown()
            if not started or client is None:
                return
            self._log_shutdown(client)
            reset_graph_client(self._dsn, self._graph)

        def redacted_dsn(self) -> str:
            return cast(str, self._current().redacted_dsn())

        def get_pool_diagnostics(self) -> dict[str, Any]:
            return dict(self._current().get_pool_diagnostics())

        def __getattr__(self, name: str) -> Any:
            return getattr(self._current(), name)

    # Validate construction eagerly so production startup still fails closed.
    _age_factory(dsn=_GRAPH_CONFIG.dsn, graph_name=_GRAPH_CONFIG.graph)
    graph_client = _RegistryBackedAGEClient(
        _GRAPH_CONFIG.dsn,
        _GRAPH_CONFIG.graph,
    )
except Exception as _exc:
    raise SystemExit(f"FATAL: AGEClient init failed: {_exc}") from _exc

graph_client = graph_client  # backward compat, will be removed
