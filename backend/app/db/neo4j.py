"""SOC shared AGE graph client and domain predicates.

The legacy Neo4j client has been removed.  Decision access is provided by
the GraphConfig-resolved AGE client below.
"""

import os
import pathlib as _pathlib

from copilot_sdk.config import GraphConfig, GraphConfigError

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


try:
    _GRAPH_CONFIG = GraphConfig.load("soc")
    _GRAPH_BACKEND = _GRAPH_CONFIG.backend
except GraphConfigError:
    if os.getenv("GRAPH_BACKEND", "").strip().lower() == "neo4j":
        raise GraphConfigError(
            "Legacy Neo4j backend is retired. Use GRAPH_BACKEND=age with "
            "GraphConfig."
        ) from None
    raise

if _GRAPH_BACKEND != "age":
    raise GraphConfigError(
        "SOC Decision operations require GRAPH_BACKEND=age; "
        f"resolved backend {_GRAPH_BACKEND!r}."
    )

try:
    from ci_platform.graph import get_graph_client as _age_factory

    import ci_platform.graph.age_client as _age_mod

    _age_mod._client = None
    neo4j_client = _age_factory(
        dsn=_GRAPH_CONFIG.dsn,
        graph_name=_GRAPH_CONFIG.graph,
    )
except Exception as _exc:
    raise SystemExit(f"FATAL: AGEClient init failed: {_exc}") from _exc
