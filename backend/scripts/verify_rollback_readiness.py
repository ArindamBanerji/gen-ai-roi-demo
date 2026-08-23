"""Produce read-only evidence that SOC can roll back from AGE.

The script never mutates AGE or SQLite.  It records the configured graph,
best-effort live node counts, and the configured SQLite fallback path so the
evidence can be generated repeatedly without changing system state.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = Path(__file__).resolve()
DEFAULT_FALLBACK_PATHS = (
    BACKEND_DIR / "data" / "soc.db",
    BACKEND_DIR / "data" / "graph.db",
)
FALLBACK_ENV_NAMES = (
    "SOC_ROLLBACK_SQLITE_PATH",
    "ROLLBACK_SQLITE_PATH",
    "SQLITE_FALLBACK_PATH",
)
DOMAINS = ("soc", "trading", "purchasing", "dataops", "s2p")


def _fallback_paths() -> list[Path]:
    configured = [Path(os.environ[name]) for name in FALLBACK_ENV_NAMES if os.environ.get(name)]
    data_dir = os.environ.get("CI_DATA_DIR")
    if data_dir:
        configured.append(Path(data_dir) / "soc.db")
    return configured + [path for path in DEFAULT_FALLBACK_PATHS if path not in configured]


def _graph_config_evidence() -> dict[str, Any]:
    try:
        from copilot_sdk.config import GraphConfig

        config = GraphConfig.load("soc")
        return {
            "loaded": True,
            "backend": config.backend,
            "expected_backend": config.expected_backend,
            "graph": config.graph,
            "dsn_configured": bool(config.dsn),
            "source": dict(config.sources),
        }
    except (ImportError, ValueError, OSError) as exc:
        return {"loaded": False, "error": str(exc)}


def _read_node_counts(dsn: str | None, graph: str | None) -> dict[str, Any]:
    if not dsn or not graph:
        return {"available": False, "reason": "GRAPH_DSN or graph is not configured", "counts": {}}
    if re.fullmatch(r"[A-Za-z0-9_]+", graph) is None:
        return {"available": False, "graph": graph, "reason": "graph name is not a safe AGE identifier", "counts": {}}

    try:
        import psycopg
    except ImportError as exc:
        return {"available": False, "graph": graph, "reason": f"psycopg unavailable: {exc}", "counts": {}}

    try:
        counts: dict[str, int] = {}
        with psycopg.connect(dsn, connect_timeout=3, autocommit=True) as conn:
            conn.execute("LOAD 'age'")
            conn.execute('SET search_path = ag_catalog, "$user", public')
            for domain in DOMAINS:
                cypher = (
                    "MATCH (n) WHERE n.domain = "
                    f"'{domain}' RETURN count(n) AS cnt"
                )
                result = conn.execute(
                    f"SELECT * FROM cypher('{graph}', $${cypher}$$) AS (cnt agtype)",
                ).fetchone()
                raw_count = result[0] if result else 0
                counts[domain] = int(str(raw_count).strip('"'))
        return {"available": True, "graph": graph, "counts": counts}
    except psycopg.OperationalError as exc:
        return {"available": False, "graph": graph, "reason": f"AGE connection failed: {exc}", "counts": {}}
    except psycopg.Error as exc:
        return {"available": False, "graph": graph, "reason": f"AGE count query failed: {exc}", "counts": {}}
    except (ValueError, TypeError, OSError) as exc:
        return {"available": False, "graph": graph, "reason": f"AGE count query failed: {exc}", "counts": {}}


def build_evidence() -> dict[str, Any]:
    config = _graph_config_evidence()
    fallback_candidates = _fallback_paths()
    existing_fallbacks = [str(path) for path in fallback_candidates if path.is_file()]
    configured_fallbacks = [
        str(path)
        for path in fallback_candidates
        if path.exists() or any(str(path) == os.environ.get(name) for name in FALLBACK_ENV_NAMES)
    ]
    graph_dsn = os.environ.get("GRAPH_DSN")
    graph_name = os.environ.get("GRAPH_NAME") or config.get("graph")
    node_counts = _read_node_counts(graph_dsn, str(graph_name) if graph_name else None)
    rollback_script = {
        "path": str(SCRIPT_PATH),
        "exists": SCRIPT_PATH.is_file(),
        "read_only": True,
        "idempotent": SCRIPT_PATH.is_file(),
    }
    fallback = {
        "configured_paths": configured_fallbacks,
        "existing_files": existing_fallbacks,
        "configured": bool(configured_fallbacks),
    }
    return {
        "rollback_ready": bool(fallback["configured"] and rollback_script["exists"]),
        "evidence": {
            "graph_config": config,
            "node_counts_per_domain": node_counts,
            "sqlite_fallback": fallback,
            "rollback_script": rollback_script,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Write JSON evidence to this file")
    args = parser.parse_args()
    evidence = build_evidence()
    payload = json.dumps(evidence, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0 if evidence["rollback_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
