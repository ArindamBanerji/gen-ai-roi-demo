from __future__ import annotations

import argparse
import asyncio
import time
from typing import Any

from soc_perf_common import (
    DEFAULT_DSN,
    assert_read_only_cypher,
    configure_age_env,
    ensure_repo_paths,
    print_table,
    redact_dsn,
    run_read_query,
    timed_async,
    write_json_and_md,
)


DEFAULT_GRAPH = "soc_graph_diag_f8"
DEFAULT_PREFIX = "DIAG-F8-CRED"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only SOC/AGE benchmark 01: AGE connection and query shape.")
    parser.add_argument("--graph-name", default=DEFAULT_GRAPH)
    parser.add_argument("--prefix", default=DEFAULT_PREFIX)
    parser.add_argument("--graph-dsn", default=DEFAULT_DSN)
    parser.add_argument("--reps", type=int, default=5)
    parser.add_argument("--alert-id-early", default=f"{DEFAULT_PREFIX}-0001")
    parser.add_argument("--alert-id-late", default=f"{DEFAULT_PREFIX}-0250")
    parser.add_argument("--json-output")
    parser.add_argument("--md-output")
    return parser.parse_args()


def literal(value: str) -> str:
    escaped = str(value).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


async def make_client(args: argparse.Namespace) -> Any:
    ensure_repo_paths()
    configure_age_env(args.graph_name, args.graph_dsn)
    from ci_platform.graph.age_client import AGEClient

    return AGEClient(dsn=args.graph_dsn, graph_name=args.graph_name)


async def read_query(client: Any, query: str) -> Any:
    assert_read_only_cypher(query)
    return await run_read_query(client, query)


async def timed_query(label: str, client: Any, query: str, reps: int) -> dict[str, Any]:
    return await timed_async(label, lambda: read_query(client, query), reps)


async def get_decision_id(client: Any, alert_id: str) -> str | None:
    query = (
        "MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) "
        f"WHERE a.alert_id = {literal(alert_id)} "
        "RETURN d.decision_id AS decision_id "
        "ORDER BY d.timestamp_epoch DESC LIMIT 1"
    )
    rows = await read_query(client, query)
    if rows and isinstance(rows[0], dict):
        value = rows[0].get("decision_id")
        return str(value) if value else None
    return None


def first_avg(rows: list[dict[str, Any]], labels: tuple[str, ...]) -> float | None:
    values = [row.get("avg_s") for row in rows if row.get("label") in labels and row.get("avg_s") is not None]
    if not values:
        return None
    return sum(float(value) for value in values) / len(values)


def build_diagnosis(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_label = {row["label"]: row for row in rows}
    fresh = by_label.get("tier_a_fresh_client_return_1", {}).get("avg_s")
    warm = by_label.get("tier_a_warm_client_return_1", {}).get("avg_s")
    fresh_warm_ratio = round(float(fresh) / float(warm), 3) if fresh and warm else None
    point_avg = first_avg(
        rows,
        (
            "tier_b_alert_exact_early",
            "tier_b_alert_exact_late",
            "tier_b_decision_join_early",
            "tier_b_decision_join_late",
            "tier_b_decision_by_id_early",
            "tier_b_decision_by_id_late",
        ),
    )
    prefix_avg = first_avg(
        rows,
        (
            "tier_c_alerts_prefix_count",
            "tier_c_decisions_prefix_count",
            "tier_c_verified_prefix_count",
            "tier_c_outcome_present_prefix_count",
        ),
    )
    prefix_scan_ratio = round(float(prefix_avg) / float(point_avg), 3) if prefix_avg and point_avg else None
    candidates: list[str] = []
    if fresh_warm_ratio and fresh_warm_ratio > 5:
        candidates.append("fresh_vs_warm_ratio_high_connection_pool_or_connection_setup")
    if point_avg and point_avg > 0.100:
        candidates.append("point_lookup_slow_possible_missing_index_or_label_scan")
    if prefix_scan_ratio and prefix_scan_ratio > 5:
        candidates.append("prefix_scan_much_slower_than_point_lookup_possible_o_n_query")
    if not candidates:
        candidates.append("no_age_read_only_gate_exceeded_by_script_01")
    return {
        "fresh_warm_ratio": fresh_warm_ratio,
        "point_lookup_avg_s": round(point_avg, 6) if point_avg else None,
        "point_lookup_slow": bool(point_avg and point_avg > 0.100),
        "prefix_scan_avg_s": round(prefix_avg, 6) if prefix_avg else None,
        "prefix_scan_ratio": prefix_scan_ratio,
        "likely_root_cause_candidates": candidates,
    }


def rows_to_markdown_table(rows: list[dict[str, Any]]) -> str:
    lines = ["| label | reps | avg_s | p50_s | p95_s | max_s | error |", "|---|---:|---:|---:|---:|---:|---|"]
    for row in rows:
        lines.append(
            "| {label} | {reps} | {avg_s} | {p50_s} | {p95_s} | {max_s} | {error} |".format(
                label=row.get("label"),
                reps=row.get("reps"),
                avg_s=row.get("avg_s"),
                p50_s=row.get("p50_s"),
                p95_s=row.get("p95_s"),
                max_s=row.get("max_s"),
                error=row.get("error") or "",
            )
        )
    return "\n".join(lines)


async def main_async() -> int:
    args = parse_args()
    if args.reps < 1:
        raise SystemExit("--reps must be >= 1")
    ensure_repo_paths()
    configure_age_env(args.graph_name, args.graph_dsn)
    started = time.time()

    client = await make_client(args)
    early_decision_id = await get_decision_id(client, args.alert_id_early)
    late_decision_id = await get_decision_id(client, args.alert_id_late)

    rows: list[dict[str, Any]] = []

    async def fresh_return_1() -> Any:
        fresh_client = await make_client(args)
        return await read_query(fresh_client, "RETURN 1 AS ok")

    rows.append(await timed_async("tier_a_fresh_client_return_1", fresh_return_1, args.reps))
    rows.append(await timed_query("tier_a_warm_client_return_1", client, "RETURN 1 AS ok", args.reps))
    rows.append(await timed_query("tier_a_warm_count_nodes", client, "MATCH (n) RETURN count(n) AS total", args.reps))

    early = literal(args.alert_id_early)
    late = literal(args.alert_id_late)
    prefix = literal(args.prefix)
    rows.append(await timed_query("tier_b_alert_exact_early", client, f"MATCH (a:Alert) WHERE a.alert_id = {early} RETURN count(a) AS cnt", args.reps))
    rows.append(await timed_query("tier_b_alert_exact_late", client, f"MATCH (a:Alert) WHERE a.alert_id = {late} RETURN count(a) AS cnt", args.reps))
    rows.append(
        await timed_query(
            "tier_b_decision_join_early",
            client,
            f"MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) WHERE a.alert_id = {early} RETURN count(d) AS cnt",
            args.reps,
        )
    )
    rows.append(
        await timed_query(
            "tier_b_decision_join_late",
            client,
            f"MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) WHERE a.alert_id = {late} RETURN count(d) AS cnt",
            args.reps,
        )
    )
    if early_decision_id:
        rows.append(
            await timed_query(
                "tier_b_decision_by_id_early",
                client,
                f"MATCH (d:Decision) WHERE d.decision_id = {literal(early_decision_id)} RETURN count(d) AS cnt",
                args.reps,
            )
        )
    if late_decision_id:
        rows.append(
            await timed_query(
                "tier_b_decision_by_id_late",
                client,
                f"MATCH (d:Decision) WHERE d.decision_id = {literal(late_decision_id)} RETURN count(d) AS cnt",
                args.reps,
            )
        )

    rows.append(await timed_query("tier_c_alerts_prefix_count", client, f"MATCH (a:Alert) WHERE a.alert_id STARTS WITH {prefix} RETURN count(a) AS cnt", args.reps))
    rows.append(
        await timed_query(
            "tier_c_decisions_prefix_count",
            client,
            f"MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) WHERE a.alert_id STARTS WITH {prefix} RETURN count(d) AS cnt",
            args.reps,
        )
    )
    rows.append(
        await timed_query(
            "tier_c_verified_prefix_count",
            client,
            f"MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) WHERE a.alert_id STARTS WITH {prefix} AND d.correct = true RETURN count(d) AS cnt",
            args.reps,
        )
    )
    rows.append(
        await timed_query(
            "tier_c_outcome_present_prefix_count",
            client,
            f"MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) WHERE a.alert_id STARTS WITH {prefix} AND d.outcome IS NOT NULL RETURN count(d) AS cnt",
            args.reps,
        )
    )

    rows.append(await timed_query("tier_d_l5_centroid_count", client, "MATCH (c:L5Centroid {domain: 'soc'}) RETURN count(c) AS cnt", args.reps))
    rows.append(await timed_query("tier_d_shaped_by_count", client, "MATCH (:L5Centroid {domain: 'soc'})-[r:SHAPED_BY]->(:Decision {domain: 'soc'}) RETURN count(r) AS cnt", args.reps))
    rows.append(await timed_query("tier_d_l5_dk_weight_count", client, "MATCH (w:L5DKWeight {domain: 'soc'}) RETURN count(w) AS cnt", args.reps))
    rows.append(
        await timed_query(
            "tier_d_dk_welford_read",
            client,
            "MATCH (w:L5DKWeight {domain: 'soc'}) "
            "RETURN max(w.n_decisions_used) AS max_n_decisions_used, "
            "count(w.confirmed_mean_json) AS confirmed_mean_count, "
            "count(w.confirmed_m2_json) AS confirmed_m2_count, "
            "count(w.overridden_mean_json) AS overridden_mean_count, "
            "count(w.overridden_m2_json) AS overridden_m2_count, "
            "count(w.all_mean_json) AS all_mean_count, "
            "count(w.all_m2_json) AS all_m2_count",
            args.reps,
        )
    )
    rows.append(await timed_query("tier_d_count_all_nodes", client, "MATCH (n) RETURN count(n) AS total", args.reps))
    rows.append(await timed_query("tier_d_count_all_edges", client, "MATCH ()-[r]->() RETURN count(r) AS total", args.reps))

    diagnosis = build_diagnosis(rows)
    payload = {
        "title": "SOC Perf 01 Read-Only AGE Benchmark",
        "created_at_epoch": started,
        "read_only": True,
        "no_writes_performed": True,
        "graph_name": args.graph_name,
        "prefix": args.prefix,
        "graph_dsn_redacted": redact_dsn(args.graph_dsn),
        "rule40_validated": True,
        "reps": args.reps,
        "alert_id_early": args.alert_id_early,
        "alert_id_late": args.alert_id_late,
        "early_decision_id_found": bool(early_decision_id),
        "late_decision_id_found": bool(late_decision_id),
        "measurements": rows,
        "diagnosis": diagnosis,
        "safety": {
            "read_only": True,
            "graph_name": args.graph_name,
            "rule40_validated": True,
            "no_writes_performed": True,
            "analyze_endpoint_called": False,
            "outcome_endpoint_called": False,
        },
    }

    print_table(rows)
    sections = [
        (
            "Safety",
            "\n".join(
                [
                    f"- read_only: `{payload['read_only']}`",
                    f"- graph_name: `{args.graph_name}`",
                    f"- prefix: `{args.prefix}`",
                    f"- graph_dsn_redacted: `{payload['graph_dsn_redacted']}`",
                    f"- Rule40 validated: `{payload['rule40_validated']}`",
                    "- no writes performed: `True`",
                    "- analyze/outcome endpoints called: `False`",
                ]
            ),
        ),
        ("Measurements", rows_to_markdown_table(rows)),
        ("Diagnosis", "```json\n" + __import__("json").dumps(diagnosis, indent=2) + "\n```"),
    ]
    json_path, md_path = write_json_and_md(
        "soc_perf_01_readonly_age",
        payload,
        sections,
        json_output=args.json_output,
        md_output=args.md_output,
    )
    print(f"JSON report: {json_path}", flush=True)
    print(f"Markdown report: {md_path}", flush=True)
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(main_async()))


if __name__ == "__main__":
    main()
