from __future__ import annotations

import argparse
import json
import time
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from soc_perf_common import (
    DEFAULT_BACKEND_URL,
    DEFAULT_DSN,
    configure_age_env,
    ensure_repo_paths,
    print_table,
    redact_dsn,
    timed_sync,
    write_json_and_md,
    validate_network_split,
)


DEFAULT_GRAPH = "soc_graph_diag_f8"
DEFAULT_PREFIX = "DIAG-F8-CRED"
NEGATIVE_ALERT_ID = "PERF-NONEXISTENT-DO-NOT-CREATE"


SOURCE_MAP = {
    "analyze_route": {
        "endpoint": "POST /api/alert/analyze",
        "definition": "backend/app/routers/triage.py:173",
        "sequence": [
            "scorer readiness guard: backend/app/routers/triage.py:184-197",
            "alert lookup via neo4j_client.get_alert: backend/app/routers/triage.py:202-208",
            "security context lookup: backend/app/routers/triage.py:210-216",
            "category resolution before scoring: backend/app/routers/triage.py:221-238",
            "factor/scorer pipeline: backend/app/routers/triage.py:240-354",
            "Decision write and DECIDED_ON edge: backend/app/routers/triage.py:435-464",
            "synchronous audit record and Decision hash SET: backend/app/routers/triage.py:466-483",
            "additional synchronous Decision metadata SETs/events: backend/app/routers/triage.py:509-667",
        ],
        "graph_reads": [
            "neo4j_client.get_alert(alert_id): backend/app/routers/triage.py:205",
            "neo4j_client.get_security_context(alert_id): backend/app/routers/triage.py:213",
            "Decision sequence/cross-category helper calls before referral: backend/app/routers/triage.py:366-373",
        ],
        "graph_writes": [
            "CREATE Decision and DECIDED_ON edge: backend/app/routers/triage.py:444-463",
            "SET entry_hash/decision_chain_index: backend/app/routers/triage.py:479-483",
            "additional Decision SETs for snapshots/provenance/exploration: backend/app/routers/triage.py:509-667",
        ],
        "negative_path_safety": (
            "For a missing alert, source raises 404 immediately after get_alert returns empty "
            "at backend/app/routers/triage.py:205-208, before Decision creation at lines 442-463."
        ),
    },
    "outcome_route": {
        "endpoint": "POST /api/alert/outcome",
        "definition": "backend/app/routers/triage.py:1065",
        "sequence": [
            "feedback duplicate guard: backend/app/routers/triage.py:1082-1089",
            "Decision lookup and outcome/correct SET: backend/app/routers/triage.py:1125-1145",
            "outcome audit write and Decision hash SET: backend/app/routers/triage.py:1155-1170",
            "analyst history scan: backend/app/routers/triage.py:1174-1184",
            "learning_state/ProfileScorer update: backend/app/routers/triage.py:1261-1297",
            "conservation/DK/L5 centroid path: backend/app/routers/triage.py:1297-1459",
            "centroid metadata SET and snapshot/distance/evolution writes: backend/app/routers/triage.py:1496-1779",
        ],
        "graph_reads": [
            "Decision lookup by decision_id: backend/app/routers/triage.py:1125-1145",
            "analyst verified history scan: backend/app/routers/triage.py:1177-1180",
        ],
        "graph_writes": [
            "SET d.outcome/d.correct/d.verified_at_epoch: backend/app/routers/triage.py:1125-1133",
            "SET outcome_entry_hash/outcome_chain_index: backend/app/routers/triage.py:1166-1170",
            "persist_soc_centroid/L5 path: backend/app/routers/triage.py:1431-1459",
            "centroid_delta_norm Decision SET: backend/app/routers/triage.py:1496-1508",
            "evolution/log/snapshot writes: backend/app/routers/triage.py:1546-1779",
        ],
    },
    "safe_get_routes": [
        {
            "label": "h3_get_alerts_queue",
            "endpoint": "/api/alerts/queue",
            "source": "backend/app/routers/triage.py:117-137",
            "reason": "GET route performs MATCH-only pending alert read.",
        },
        {
            "label": "h3_get_outcome_status_negative",
            "endpoint": f"/api/alert/outcome/status?{urlencode({'alert_id': NEGATIVE_ALERT_ID})}",
            "source": "backend/app/routers/triage.py:1821-1838",
            "reason": "GET feedback status for non-proof alert id.",
        },
        {
            "label": "h3_get_policy_history",
            "endpoint": "/api/alert/policy-history",
            "source": "backend/app/routers/triage.py:1964-1981",
            "reason": "GET in-memory policy conflict history.",
        },
        {
            "label": "h3_get_soc_profile",
            "endpoint": "/api/soc/profile",
            "source": "backend/app/routers/triage.py:1995-2089",
            "reason": "GET ProfileScorer state; no source-level graph write in route.",
        },
    ],
    "skipped_endpoints": [
        {
            "endpoint": "POST /api/alert/outcome",
            "reason": "Always a feedback/write route; forbidden for read-only benchmark.",
        },
        {
            "endpoint": "POST /api/alert/analyze for proof alerts",
            "reason": "Normal analyze path writes Decision nodes and audit metadata.",
        },
        {
            "endpoint": "GET /api/alert/policy-check",
            "reason": "Additional conflict-detection behavior is outside the minimal safe HTTP baseline.",
        },
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only SOC perf 02: HTTP baseline and analyze/outcome source map.")
    parser.add_argument("--backend-url", default=DEFAULT_BACKEND_URL)
    parser.add_argument("--graph-name", default=DEFAULT_GRAPH)
    parser.add_argument("--prefix", default=DEFAULT_PREFIX)
    parser.add_argument("--graph-dsn", default=DEFAULT_DSN)
    parser.add_argument("--reps", type=int, default=5)
    parser.add_argument("--http-timeout", type=float, default=30.0)
    parser.add_argument("--json-output")
    parser.add_argument("--md-output")
    return parser.parse_args()


def http_request(method: str, url: str, timeout: float, body: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return {"status": response.status, "body": raw[:500]}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return {"status": exc.code, "body": raw[:500], "http_error": True}


def endpoint_url(args: argparse.Namespace, path: str) -> str:
    return f"{args.backend_url.rstrip('/')}{path}"


def safe_negative_analyze(args: argparse.Namespace) -> dict[str, Any]:
    if NEGATIVE_ALERT_ID.startswith(args.prefix):
        raise RuntimeError("negative analyze alert id unexpectedly starts with proof prefix")
    return http_request(
        "POST",
        endpoint_url(args, "/api/alert/analyze"),
        args.http_timeout,
        {"alert_id": NEGATIVE_ALERT_ID},
    )


def run_measurements(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    rows: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []

    rows.append(timed_sync("h1_get_health", lambda: http_request("GET", endpoint_url(args, "/health"), args.http_timeout), args.reps))

    rows.append(timed_sync("h2_post_analyze_negative_missing_alert", lambda: safe_negative_analyze(args), args.reps))

    for route in SOURCE_MAP["safe_get_routes"]:
        rows.append(
            timed_sync(
                str(route["label"]),
                lambda endpoint=str(route["endpoint"]): http_request("GET", endpoint_url(args, endpoint), args.http_timeout),
                args.reps,
            )
        )
    for item in SOURCE_MAP["skipped_endpoints"]:
        skipped.append({"endpoint": str(item["endpoint"]), "reason": str(item["reason"])})
    return rows, skipped


def table_md(rows: list[dict[str, Any]]) -> str:
    lines = ["| label | reps | avg_s | p50_s | p95_s | max_s | error |", "|---|---:|---:|---:|---:|---:|---|"]
    for row in rows:
        lines.append(
            f"| {row.get('label')} | {row.get('reps')} | {row.get('avg_s')} | {row.get('p50_s')} | "
            f"{row.get('p95_s')} | {row.get('max_s')} | {row.get('error') or ''} |"
        )
    return "\n".join(lines)


def source_map_md() -> str:
    return "```json\n" + json.dumps(SOURCE_MAP, indent=2) + "\n```"


def main() -> None:
    args = parse_args()
    if args.reps < 1:
        raise SystemExit("--reps must be >= 1")
    ensure_repo_paths()
    network_warnings = validate_network_split(args.graph_dsn, args.backend_url)
    configure_age_env(args.graph_name, args.graph_dsn)
    started = time.time()

    rows, skipped = run_measurements(args)
    print_table(rows)

    payload = {
        "title": "SOC Perf 02 Read-Only HTTP and Analyze Route Source Map",
        "created_at_epoch": started,
        "read_only": True,
        "no_writes_performed_by_script": True,
        "graph_name": args.graph_name,
        "prefix": args.prefix,
        "backend_url": args.backend_url,
        "graph_dsn_redacted": redact_dsn(args.graph_dsn),
        "rule40_validated": True,
        "network_split_warnings": network_warnings,
        "reps": args.reps,
        "http_timeout": args.http_timeout,
        "negative_analyze_alert_id": NEGATIVE_ALERT_ID,
        "proof_alerts_analyzed": False,
        "outcome_endpoint_called": False,
        "measurements": rows,
        "source_map": SOURCE_MAP,
        "skipped_endpoints": skipped,
        "safety": {
            "no_proof_alert_analyzed": True,
            "no_outcome_endpoint_called": True,
            "no_writes_performed_by_script": True,
            "negative_analyze_source_guard": SOURCE_MAP["analyze_route"]["negative_path_safety"],
        },
    }

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
                    f"- backend_url: `{args.backend_url}`",
                    f"- network_split_warnings: `{network_warnings}`",
                    "- no proof alert analyzed: `True`",
                    "- no outcome endpoint called: `True`",
                    "- no writes performed by script: `True`",
                    f"- negative analyze alert id: `{NEGATIVE_ALERT_ID}`",
                ]
            ),
        ),
        ("Measurements", table_md(rows)),
        ("Source Map", source_map_md()),
        ("Skipped Endpoints", "```json\n" + json.dumps(skipped, indent=2) + "\n```"),
    ]
    json_path, md_path = write_json_and_md(
        "soc_perf_02_readonly_http",
        payload,
        sections,
        json_output=args.json_output,
        md_output=args.md_output,
    )
    print(f"JSON report: {json_path}", flush=True)
    print(f"Markdown report: {md_path}", flush=True)


if __name__ == "__main__":
    main()
