#!/usr/bin/env python3
"""Measure committed Phase-3-like AGE transaction cost on a scratch graph.

This script is diagnostic-only. It writes synthetic nodes/edges to a scratch
graph, optionally cleans only those synthetic rows by run_id/prefix, and never
touches backend routes or proof runners.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
import statistics
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import psycopg
except ImportError as exc:  # pragma: no cover - environment dependent
    raise SystemExit("psycopg is required for this diagnostic script") from exc

from soc_perf_common import DEFAULT_DSN, redact_dsn, validate_rule40_dsn, write_json_and_md


DEFAULT_GRAPH = "soc_graph_phase3_commit_spike_1"
DEFAULT_PREFIX = "PHASE3-SPIKE"
SPIKE_TYPE = "phase3_commit_measurement"
PROHIBITED_GRAPH_NAMES = {"soc_graph_diag_f8", "soc_graph_c9b_pre_hotpath_2"}
PROHIBITED_GRAPH_SUBSTRINGS = ("c9b_pre_hotpath", "diag_f8")
GRAPH_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _cypher_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and not math.isfinite(value):
            return "null"
        return str(value)
    return json.dumps(str(value), separators=(",", ":"))


def _cypher_sql(graph_name: str, cypher: str, columns: str) -> str:
    return f"SELECT * FROM cypher('{graph_name}', $$\n{cypher}\n$$) AS ({columns})"


def _parse_int(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    text = str(value).strip().strip('"')
    try:
        return int(float(text))
    except ValueError:
        return 0


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * pct
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[int(rank)]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower)


def _summary(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {"count": 0, "avg_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0, "max_ms": 0.0, "min_ms": 0.0}
    return {
        "count": len(values),
        "avg_ms": statistics.fmean(values),
        "p50_ms": _percentile(values, 0.50),
        "p95_ms": _percentile(values, 0.95),
        "max_ms": max(values),
        "min_ms": min(values),
    }


def _validate_graph_name(graph_name: str) -> None:
    lowered = graph_name.lower()
    if graph_name in PROHIBITED_GRAPH_NAMES or any(token in lowered for token in PROHIBITED_GRAPH_SUBSTRINGS):
        raise SystemExit(f"Refusing to run against protected/proof graph: {graph_name}")
    if not GRAPH_NAME_RE.match(graph_name):
        raise SystemExit("Graph name must match ^[A-Za-z_][A-Za-z0-9_]*$ for safe AGE SQL.")


def _connect(dsn: str) -> psycopg.Connection:
    conn = psycopg.connect(dsn, autocommit=True)
    conn.execute("LOAD 'age'")
    conn.execute('SET search_path = ag_catalog, "$user", public')
    return conn


def _ensure_graph(conn: psycopg.Connection, graph_name: str) -> bool:
    row = conn.execute("SELECT count(*) FROM ag_catalog.ag_graph WHERE name = %s", (graph_name,)).fetchone()
    exists = bool(row and row[0])
    if not exists:
        conn.execute(f"SELECT create_graph('{graph_name}')")
    return not exists


def _run_cypher(conn: psycopg.Connection, graph_name: str, cypher: str, columns: str) -> list[tuple[Any, ...]]:
    return list(conn.execute(_cypher_sql(graph_name, cypher, columns)).fetchall())


def _count_synthetic_nodes(conn: psycopg.Connection, graph_name: str, run_id: str, prefix: str) -> int:
    rows = _run_cypher(
        conn,
        graph_name,
        f"""
        MATCH (n)
        WHERE n.run_id = {_cypher_value(run_id)}
          AND n.prefix = {_cypher_value(prefix)}
          AND n.spike_type = {_cypher_value(SPIKE_TYPE)}
        RETURN count(n) AS synthetic_count
        """,
        "synthetic_count agtype",
    )
    return _parse_int(rows[0][0]) if rows else 0


def _count_synthetic_edges(conn: psycopg.Connection, graph_name: str, run_id: str, prefix: str) -> int:
    rows = _run_cypher(
        conn,
        graph_name,
        f"""
        MATCH (n)-[r]->()
        WHERE n.run_id = {_cypher_value(run_id)}
          AND n.prefix = {_cypher_value(prefix)}
          AND n.spike_type = {_cypher_value(SPIKE_TYPE)}
        RETURN count(r) AS synthetic_edge_count
        """,
        "synthetic_edge_count agtype",
    )
    return _parse_int(rows[0][0]) if rows else 0


def _create_counter(conn: psycopg.Connection, graph_name: str, run_id: str, prefix: str) -> None:
    now = time.time()
    _run_cypher(
        conn,
        graph_name,
        f"""
        CREATE (:Phase3SpikeCounter {{
          spike_id: {_cypher_value(run_id + "-counter")},
          run_id: {_cypher_value(run_id)},
          prefix: {_cypher_value(prefix)},
          spike_type: {_cypher_value(SPIKE_TYPE)},
          created_at_epoch: {now},
          updated_at_epoch: {now},
          phase3_count: 0
        }})
        RETURN 1 AS created
        """,
        "created agtype",
    )


def _phase3_shape(
    conn: psycopg.Connection,
    graph_name: str,
    run_id: str,
    prefix: str,
    rep_index: int,
    mode: str,
    counter_value: int,
) -> None:
    now = time.time()
    decision_id = f"{run_id}-{mode}-decision-{rep_index:04d}"
    audit_id = f"{run_id}-{mode}-audit-{rep_index:04d}"
    _run_cypher(
        conn,
        graph_name,
        f"""
        CREATE (d:Phase3SpikeDecision {{
          spike_id: {_cypher_value(decision_id)},
          decision_id: {_cypher_value(decision_id)},
          run_id: {_cypher_value(run_id)},
          prefix: {_cypher_value(prefix)},
          spike_type: {_cypher_value(SPIKE_TYPE)},
          mode: {_cypher_value(mode)},
          rep_index: {rep_index},
          action: "diagnostic",
          confidence: 0.5,
          created_at_epoch: {now}
        }})
        CREATE (a:Phase3SpikeAudit {{
          spike_id: {_cypher_value(audit_id)},
          audit_id: {_cypher_value(audit_id)},
          run_id: {_cypher_value(run_id)},
          prefix: {_cypher_value(prefix)},
          spike_type: {_cypher_value(SPIKE_TYPE)},
          mode: {_cypher_value(mode)},
          rep_index: {rep_index},
          created_at_epoch: {now}
        }})
        CREATE (d)-[:PHASE3_SPIKE_AUDIT {{
          run_id: {_cypher_value(run_id)},
          prefix: {_cypher_value(prefix)},
          spike_type: {_cypher_value(SPIKE_TYPE)}
        }}]->(a)
        RETURN 1 AS created
        """,
        "created agtype",
    )
    _run_cypher(
        conn,
        graph_name,
        f"""
        MATCH (c:Phase3SpikeCounter {{
          run_id: {_cypher_value(run_id)},
          prefix: {_cypher_value(prefix)},
          spike_type: {_cypher_value(SPIKE_TYPE)}
        }})
        SET c.phase3_count = {counter_value},
            c.updated_at_epoch = {now}
        RETURN c.phase3_count AS phase3_count
        """,
        "phase3_count agtype",
    )
    _run_cypher(
        conn,
        graph_name,
        f"""
        MATCH (d:Phase3SpikeDecision {{spike_id: {_cypher_value(decision_id)}}}),
              (c:Phase3SpikeCounter {{
                run_id: {_cypher_value(run_id)},
                prefix: {_cypher_value(prefix)},
                spike_type: {_cypher_value(SPIKE_TYPE)}
              }})
        CREATE (d)-[:PHASE3_SPIKE_COUNTED_FOR {{
          run_id: {_cypher_value(run_id)},
          prefix: {_cypher_value(prefix)},
          spike_type: {_cypher_value(SPIKE_TYPE)}
        }}]->(c)
        RETURN 1 AS created
        """,
        "created agtype",
    )


def _measure_transaction(
    conn: psycopg.Connection,
    graph_name: str,
    run_id: str,
    prefix: str,
    rep_index: int,
    mode: str,
    counter_value: int,
    commit: bool,
) -> float:
    start = time.perf_counter()
    conn.execute("BEGIN")
    try:
        _phase3_shape(conn, graph_name, run_id, prefix, rep_index, mode, counter_value)
        conn.execute("COMMIT" if commit else "ROLLBACK")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return (time.perf_counter() - start) * 1000.0


def _cleanup_synthetic(conn: psycopg.Connection, graph_name: str, run_id: str, prefix: str) -> dict[str, int]:
    before_nodes = _count_synthetic_nodes(conn, graph_name, run_id, prefix)
    before_edges = _count_synthetic_edges(conn, graph_name, run_id, prefix)
    _run_cypher(
        conn,
        graph_name,
        f"""
        MATCH (n)-[r]-()
        WHERE n.run_id = {_cypher_value(run_id)}
          AND n.prefix = {_cypher_value(prefix)}
          AND n.spike_type = {_cypher_value(SPIKE_TYPE)}
        DELETE r
        RETURN 1 AS deleted
        """,
        "deleted agtype",
    )
    _run_cypher(
        conn,
        graph_name,
        f"""
        MATCH (n)
        WHERE n.run_id = {_cypher_value(run_id)}
          AND n.prefix = {_cypher_value(prefix)}
          AND n.spike_type = {_cypher_value(SPIKE_TYPE)}
        DELETE n
        RETURN 1 AS deleted
        """,
        "deleted agtype",
    )
    return {
        "before_nodes": before_nodes,
        "before_edges": before_edges,
        "after_nodes": _count_synthetic_nodes(conn, graph_name, run_id, prefix),
        "after_edges": _count_synthetic_edges(conn, graph_name, run_id, prefix),
    }


def _report_sections(payload: dict[str, Any]) -> list[tuple[str, str]]:
    committed = payload["committed_summary"]
    rollback = payload["rollback_summary"]
    cleanup = payload["cleanup"]
    safety = "\n".join(
        [
            f"- Graph: `{payload['graph_name']}`",
            f"- DSN: `{payload['graph_dsn_redacted']}`",
            f"- Run ID: `{payload['run_id']}`",
            f"- Prefix: `{payload['prefix']}`",
            f"- Synthetic spike type: `{SPIKE_TYPE}`",
            f"- Cleanup performed: `{cleanup['performed']}`",
            f"- Synthetic nodes after cleanup/readback: `{cleanup['after_nodes']}`",
            f"- Synthetic edges after cleanup/readback: `{cleanup['after_edges']}`",
        ]
    )
    results = "\n".join(
        [
            "| mode | count | avg_ms | p50_ms | p95_ms | max_ms | min_ms |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            (
                f"| committed | {committed['count']} | {committed['avg_ms']:.3f} | "
                f"{committed['p50_ms']:.3f} | {committed['p95_ms']:.3f} | "
                f"{committed['max_ms']:.3f} | {committed['min_ms']:.3f} |"
            ),
            (
                f"| rollback | {rollback['count']} | {rollback['avg_ms']:.3f} | "
                f"{rollback['p50_ms']:.3f} | {rollback['p95_ms']:.3f} | "
                f"{rollback['max_ms']:.3f} | {rollback['min_ms']:.3f} |"
            ),
            "",
            f"- Commit overhead estimate: `{payload['commit_overhead_estimate_ms']:.3f} ms`",
        ]
    )
    interpretation = "\n".join(
        [
            "- The committed measurement is authoritative for this Package 0 planning check.",
            "- The rollback measurement is secondary context only.",
            "- These are diagnostic dev-box numbers, not buyer-facing latency claims.",
            "- WSL2 dev-box fsync/WAL behavior may differ from pilot storage and must be re-confirmed.",
        ]
    )
    return [
        (
            "Summary",
            "Diagnostic-only measurement of a committed Phase-3-like AGE transaction on a scratch graph.",
        ),
        ("Safety", safety),
        ("Results", results),
        ("Interpretation", interpretation),
    ]


def _default_report_name(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_prefix = re.sub(r"[^A-Za-z0-9_.-]+", "_", prefix).lower()
    return f"soc_perf_03_phase3_commit_spike_{safe_prefix}_{stamp}"


def run(args: argparse.Namespace) -> dict[str, Any]:
    _validate_graph_name(args.graph_name)
    validate_rule40_dsn(args.graph_dsn)
    dsn_warning = ""
    if "host=localhost" not in args.graph_dsn.lower():
        dsn_warning = (dsn_warning + " " if dsn_warning else "") + "Expected Rule #40 AGE DSN to include host=localhost."

    run_id = f"{args.prefix}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    psycopg_pool_available = importlib.util.find_spec("psycopg_pool") is not None
    committed_ms: list[float] = []
    rollback_ms: list[float] = []

    with _connect(args.graph_dsn) as conn:
        graph_created = _ensure_graph(conn, args.graph_name)
        _create_counter(conn, args.graph_name, run_id, args.prefix)

        for index in range(args.warmup):
            _measure_transaction(conn, args.graph_name, run_id, args.prefix, index + 1, "warmup_rollback", -1, False)

        for index in range(args.reps):
            committed_ms.append(
                _measure_transaction(
                    conn, args.graph_name, run_id, args.prefix, index + 1, "committed", index + 1, True
                )
            )

        committed_readback = {
            "synthetic_nodes": _count_synthetic_nodes(conn, args.graph_name, run_id, args.prefix),
            "synthetic_edges": _count_synthetic_edges(conn, args.graph_name, run_id, args.prefix),
        }

        for index in range(args.reps):
            rollback_ms.append(
                _measure_transaction(
                    conn, args.graph_name, run_id, args.prefix, index + 1, "rollback", 100000 + index, False
                )
            )

        if args.keep_graph:
            cleanup = {
                "performed": False,
                "before_nodes": committed_readback["synthetic_nodes"],
                "before_edges": committed_readback["synthetic_edges"],
                "after_nodes": committed_readback["synthetic_nodes"],
                "after_edges": committed_readback["synthetic_edges"],
            }
        else:
            cleanup = {"performed": True, **_cleanup_synthetic(conn, args.graph_name, run_id, args.prefix)}

    committed_summary = _summary(committed_ms)
    rollback_summary = _summary(rollback_ms)
    report_name = _default_report_name(args.prefix)

    payload: dict[str, Any] = {
        "run_id": run_id,
        "title": "SOC Phase-3 Committed Transaction Spike",
        "graph_name": args.graph_name,
        "graph_created": graph_created,
        "graph_dsn_redacted": redact_dsn(args.graph_dsn),
        "dsn_warning": dsn_warning,
        "prefix": args.prefix,
        "spike_type": SPIKE_TYPE,
        "reps": args.reps,
        "warmup": args.warmup,
        "psycopg_pool_available": psycopg_pool_available,
        "connection_model": "single warm psycopg connection reused for measurement transactions",
        "committed_ms": committed_ms,
        "rollback_ms": rollback_ms,
        "committed_summary": committed_summary,
        "rollback_summary": rollback_summary,
        "commit_overhead_estimate_ms": float(committed_summary["avg_ms"]) - float(rollback_summary["avg_ms"]),
        "committed_readback": committed_readback,
        "cleanup": cleanup,
        "storage_caveat": "WSL2 dev-box fsync/WAL behavior may differ from pilot storage; re-confirm before buyer-facing claims.",
        "interpretation": {
            "committed_measurement": "diagnostic-only committed Phase-3-like AGE transaction cost",
            "rollback_measurement": "secondary context only",
            "buyer_facing_latency_claim": "not supported by this diagnostic alone",
        },
    }

    json_path, md_path = write_json_and_md(
        report_name,
        payload,
        _report_sections(payload),
        json_output=args.json_output,
        md_output=args.md_output,
    )
    payload["json_report"] = str(json_path)
    payload["md_report"] = str(md_path)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Measure committed Phase-3-like AGE transaction cost on a scratch graph."
    )
    parser.add_argument("--graph-name", default=DEFAULT_GRAPH)
    parser.add_argument("--graph-dsn", default=DEFAULT_DSN)
    parser.add_argument("--reps", type=int, default=10)
    parser.add_argument("--prefix", default=DEFAULT_PREFIX)
    parser.add_argument("--json-output")
    parser.add_argument("--md-output")
    parser.add_argument("--keep-graph", action="store_true")
    parser.add_argument("--warmup", type=int, default=1)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.reps < 1:
        parser.error("--reps must be >= 1")
    if args.warmup < 0:
        parser.error("--warmup must be >= 0")

    payload = run(args)
    committed = payload["committed_summary"]
    rollback = payload["rollback_summary"]
    print("SOC Phase-3 committed transaction spike")
    print(f"graph={payload['graph_name']}")
    print(f"dsn={payload['graph_dsn_redacted']}")
    if payload["dsn_warning"]:
        print(f"dsn_warning={payload['dsn_warning']}")
    print(f"psycopg_pool_available={payload['psycopg_pool_available']}")
    print(
        "committed_ms "
        f"avg={committed['avg_ms']:.3f} p50={committed['p50_ms']:.3f} "
        f"p95={committed['p95_ms']:.3f} max={committed['max_ms']:.3f}"
    )
    print(
        "rollback_ms "
        f"avg={rollback['avg_ms']:.3f} p50={rollback['p50_ms']:.3f} "
        f"p95={rollback['p95_ms']:.3f} max={rollback['max_ms']:.3f}"
    )
    print(f"commit_overhead_estimate_ms={payload['commit_overhead_estimate_ms']:.3f}")
    print(
        "cleanup "
        f"performed={payload['cleanup']['performed']} "
        f"after_nodes={payload['cleanup']['after_nodes']} "
        f"after_edges={payload['cleanup']['after_edges']}"
    )
    print(f"json_report={payload['json_report']}")
    print(f"md_report={payload['md_report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
