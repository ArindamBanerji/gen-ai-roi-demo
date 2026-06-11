from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.request import urlopen


REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECTS_ROOT = REPO_ROOT.parent
CI_PLATFORM = PROJECTS_ROOT / "ci-platform"
BACKEND_ROOT = REPO_ROOT / "backend"
DEFAULT_DSN = "host=localhost port=5433 dbname=soc_copilot user=postgres password=postgres"
RULE40_HINT = (
    "RULE #40: Windows-side AGE/PostgreSQL DSNs must use localhost, not 127.0.0.1. "
    "Only commands running inside WSL2 may use 127.0.0.1."
)

for path in (str(CI_PLATFORM), str(BACKEND_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only SOC diagnostic graph prefix probe.")
    parser.add_argument("--graph-name", required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--graph-dsn", default=DEFAULT_DSN)
    parser.add_argument("--backend-url", default="http://localhost:8001")
    parser.add_argument("--alert-id")
    parser.add_argument("--decision-id")
    return parser.parse_args()


def redact_dsn(dsn: str) -> str:
    parts = []
    for part in str(dsn).split():
        parts.append("password=***" if part.lower().startswith("password=") else part)
    return " ".join(parts)


def configure_age_env(args: argparse.Namespace) -> None:
    if os.name == "nt" and "127.0.0.1" in str(args.graph_dsn):
        raise SystemExit(f"{RULE40_HINT} Received --graph-dsn={redact_dsn(args.graph_dsn)!r}.")
    os.environ["GRAPH_BACKEND"] = "age"
    os.environ["GRAPH_DSN"] = args.graph_dsn
    os.environ["AGE_GRAPH_NAME"] = args.graph_name


def _literal(value: Any) -> str:
    from app.graph_schema import _S

    return _S(value)


async def run_probe(args: argparse.Namespace) -> dict[str, Any]:
    configure_age_env(args)
    from ci_platform.graph.age_client import AGEClient

    client = AGEClient(dsn=args.graph_dsn, graph_name=args.graph_name)
    queries = {
        "decisions": (
            "MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) "
            f"WHERE d.domain = 'soc' AND a.alert_id STARTS WITH {_literal(args.prefix)} "
            "RETURN count(d) AS cnt"
        ),
        "verified": (
            "MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) "
            f"WHERE d.domain = 'soc' AND a.alert_id STARTS WITH {_literal(args.prefix)} "
            "AND d.correct = true RETURN count(d) AS cnt"
        ),
        "outcome_present": (
            "MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) "
            f"WHERE d.domain = 'soc' AND a.alert_id STARTS WITH {_literal(args.prefix)} "
            "AND d.outcome IS NOT NULL RETURN count(d) AS cnt"
        ),
        "latest_alert": (
            "MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) "
            f"WHERE d.domain = 'soc' AND a.alert_id STARTS WITH {_literal(args.prefix)} "
            "RETURN a.alert_id AS alert_id, d.decision_id AS decision_id, d.action AS action, "
            "d.outcome AS outcome, d.correct AS correct, d.timestamp_epoch AS timestamp_epoch "
            "ORDER BY a.alert_id DESC LIMIT 1"
        ),
        "l5_centroid": "MATCH (c:L5Centroid {domain: 'soc'}) RETURN count(c) AS cnt",
        "shaped_by": "MATCH (:L5Centroid {domain: 'soc'})-[r:SHAPED_BY]->(:Decision {domain: 'soc'}) RETURN count(r) AS cnt",
        "l5_dk_weight": "MATCH (w:L5DKWeight {domain: 'soc'}) RETURN count(w) AS cnt",
        "dk_welford": (
            "MATCH (w:L5DKWeight {domain: 'soc'}) "
            "RETURN w.n_decisions_used AS n_decisions_used, "
            "w.confirmed_mean_json AS confirmed_mean_json, w.confirmed_m2_json AS confirmed_m2_json, "
            "w.overridden_mean_json AS overridden_mean_json, w.overridden_m2_json AS overridden_m2_json, "
            "w.all_mean_json AS all_mean_json, w.all_m2_json AS all_m2_json "
            "ORDER BY w.created_at DESC LIMIT 5"
        ),
    }
    if args.alert_id:
        queries["specific_alert"] = (
            "MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) "
            f"WHERE a.alert_id = {_literal(args.alert_id)} "
            "RETURN a.alert_id AS alert_id, a.category AS category, d.decision_id AS decision_id, "
            "d.action AS action, d.confidence AS confidence, d.outcome AS outcome, d.correct AS correct, "
            "d.verified_at_epoch AS verified_at_epoch, d.timestamp_epoch AS timestamp_epoch "
            "ORDER BY d.timestamp_epoch DESC LIMIT 5"
        )
    if args.decision_id:
        queries["specific_decision"] = (
            f"MATCH (d:Decision {{decision_id: {_literal(args.decision_id)}}}) "
            "RETURN d.decision_id AS decision_id, d.outcome AS outcome, d.correct AS correct, "
            "d.verified_at_epoch AS verified_at_epoch, d.outcome_entry_hash AS outcome_entry_hash"
        )
    results = {name: await client.run_query(query) for name, query in queries.items()}
    welford_rows = results.get("dk_welford") or []
    welford_present = any(
        row.get("confirmed_mean_json") is not None
        and row.get("confirmed_m2_json") is not None
        and row.get("overridden_mean_json") is not None
        and row.get("overridden_m2_json") is not None
        and row.get("all_mean_json") is not None
        and row.get("all_m2_json") is not None
        for row in welford_rows
    )
    max_n = max([int(row.get("n_decisions_used") or 0) for row in welford_rows] or [0])
    health = None
    try:
        with urlopen(f"{args.backend_url.rstrip('/')}/health", timeout=10) as response:
            raw = response.read().decode("utf-8")
            health = json.loads(raw) if raw else {"status_code": response.status}
    except Exception as exc:
        health = {"error": str(exc)}
    return {
        "graph_name": args.graph_name,
        "prefix": args.prefix,
        "graph_dsn_redacted": redact_dsn(args.graph_dsn),
        "rule40_validated": not (os.name == "nt" and "127.0.0.1" in str(args.graph_dsn)),
        "backend_health": health,
        "max_n_decisions_used": max_n,
        "welford_present": welford_present,
        "raw": results,
    }


def main() -> None:
    args = parse_args()
    result = asyncio.run(run_probe(args))
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
