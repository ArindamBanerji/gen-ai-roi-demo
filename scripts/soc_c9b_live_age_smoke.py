from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


REQUIRED_WELFORD_FIELDS = (
    "confirmed_mean_json",
    "confirmed_m2_json",
    "overridden_mean_json",
    "overridden_m2_json",
    "all_mean_json",
    "all_m2_json",
)


def _find_projects_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / "gen-ai-roi-demo-v4-v50").exists() and (parent / "ci-platform").exists():
            return parent
    return here.parents[2]


def _bootstrap_paths() -> tuple[Path, Path]:
    projects_root = _find_projects_root()
    repo_root = projects_root / "gen-ai-roi-demo-v4-v50"
    backend = repo_root / "backend"
    ci_platform = projects_root / "ci-platform"
    for path in (backend, ci_platform):
        text = str(path)
        if text not in sys.path:
            sys.path.insert(0, text)
    return projects_root, repo_root


PROJECTS_ROOT, REPO_ROOT = _bootstrap_paths()


def redact_dsn(dsn: str | None) -> str | None:
    if not dsn:
        return dsn
    return re.sub(r"(://[^:/@]+:)([^@]+)(@)", r"\1***\3", dsn)


def is_passwordless_graph_dsn(dsn: str | None) -> bool:
    if not dsn:
        return True
    match = re.search(r"^[a-zA-Z][a-zA-Z0-9+.-]*://([^/@:]+)(?::([^@]*))?@", dsn)
    return bool(match and not match.group(2))


def choose_database_url(database_url: str | None, graph_dsn: str | None) -> tuple[str | None, str]:
    if database_url:
        reason = "DATABASE_URL"
        if graph_dsn and is_passwordless_graph_dsn(graph_dsn):
            reason += " (ignored passwordless GRAPH_DSN)"
        return database_url, reason
    if graph_dsn and not is_passwordless_graph_dsn(graph_dsn):
        return graph_dsn, "GRAPH_DSN"
    return None, "missing DATABASE_URL; GRAPH_DSN is unset or passwordless"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SOC C9B live AGE smoke/proof readback.")
    parser.add_argument("--loops", type=int, default=210)
    parser.add_argument("--alert-prefix", default="C9B-SOC")
    parser.add_argument("--start-index", type=int, default=1)
    parser.add_argument("--max-attempts", type=int, default=None)
    parser.add_argument("--readback", action="store_true")
    parser.add_argument("--readback-only", action="store_true")
    parser.add_argument("--dk-proof-mode", action="store_true")
    parser.add_argument("--target-category", default=None)
    parser.add_argument("--graph-name", default=os.getenv("AGE_GRAPH_NAME", "soc_graph_c9b"))
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)
    if args.loops < 1:
        parser.error("--loops must be >= 1")
    if args.start_index < 0:
        parser.error("--start-index must be >= 0")
    if args.max_attempts is not None and args.max_attempts < args.loops:
        parser.error("--max-attempts must be >= --loops")
    return args


@dataclass
class RouteResult:
    attempted: int = 0
    score_ok: int = 0
    outcome_ok: int = 0
    valid_scorer_action_outcomes: int = 0
    skipped_routing_actions: int = 0
    invalid_actions: dict[str, int] = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)


def _make_store(database_url: str, graph_name: str):
    from ci_platform.graph.age_sdk_adapter import AGEGraphStoreAdapter

    return AGEGraphStoreAdapter(dsn=database_url, graph_name=graph_name)


def _run_query(store: Any, query: str) -> list[dict]:
    if hasattr(store, "_run_query"):
        return list(store._run_query(query))
    inner = getattr(store, "_store", None) or getattr(store, "store", None)
    if inner is not None and hasattr(inner, "_run_query"):
        return list(inner._run_query(query))
    raise RuntimeError("AGE readback requires AGEGraphStoreAdapter-compatible store")


def _count_by_domain(rows: list[dict]) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        domain = row.get("domain")
        if domain:
            out[str(domain)] = int(row.get("cnt") or 0)
    return out


def readback(store: Any) -> dict[str, Any]:
    run = lambda q: _run_query(store, q)
    centroids = _count_by_domain(
        run("MATCH (c:L5Centroid) RETURN c.domain AS domain, count(c) AS cnt ORDER BY domain")
    )
    dk_weights = _count_by_domain(
        run("MATCH (w:L5DKWeight) RETURN w.domain AS domain, count(w) AS cnt ORDER BY domain")
    )
    shaped = _count_by_domain(
        run("MATCH (c:L5Centroid)-[:SHAPED_BY]->(d:Decision) RETURN c.domain AS domain, count(*) AS cnt ORDER BY domain")
    )
    triggered = _count_by_domain(
        run("MATCH (cs:L5ConservationState)-[:TRIGGERED_BY]->(d:Decision) RETURN cs.domain AS domain, count(*) AS cnt ORDER BY domain")
    )
    conservation_rows = run(
        "MATCH (cs:L5ConservationState) RETURN cs.domain AS domain, cs.status AS status, count(cs) AS cnt ORDER BY domain, status"
    )
    conservation: dict[str, dict[str, Any]] = {}
    for row in conservation_rows:
        domain = row.get("domain")
        if domain:
            conservation[str(domain)] = {"count": int(row.get("cnt") or 0), "status": row.get("status")}

    welford_rows = run(
        """
        MATCH (w:L5DKWeight)
        RETURN w.domain AS domain,
               w.confirmed_mean_json IS NOT NULL AS confirmed_mean,
               w.confirmed_m2_json IS NOT NULL AS confirmed_m2,
               w.overridden_mean_json IS NOT NULL AS overridden_mean,
               w.overridden_m2_json IS NOT NULL AS overridden_m2,
               w.all_mean_json IS NOT NULL AS all_mean,
               w.all_m2_json IS NOT NULL AS all_m2
        ORDER BY domain
        """
    )
    welford: dict[str, Any] = {}
    for row in welford_rows:
        domain = row.get("domain")
        if domain:
            fields = {
                "confirmed_mean": bool(row.get("confirmed_mean")),
                "confirmed_m2": bool(row.get("confirmed_m2")),
                "overridden_mean": bool(row.get("overridden_mean")),
                "overridden_m2": bool(row.get("overridden_m2")),
                "all_mean": bool(row.get("all_mean")),
                "all_m2": bool(row.get("all_m2")),
            }
            welford[str(domain)] = {"present": all(fields.values()), "fields": fields}

    samples = {
        "centroids": run(
            "MATCH (c:L5Centroid) WHERE c.domain = 'soc' RETURN c.domain AS domain, c.category AS category, c.action AS action, c.caused_by_decision_id AS caused_by_decision_id, c.delta_norm AS delta_norm LIMIT 10"
        ),
        "dk_weights": run(
            "MATCH (w:L5DKWeight) WHERE w.domain = 'soc' RETURN w.domain AS domain, w.dk_weight_id AS dk_weight_id, w.n_decisions_used AS n_decisions_used, w.n_confirmed AS n_confirmed, w.n_overridden AS n_overridden LIMIT 10"
        ),
        "conservation": run(
            "MATCH (cs:L5ConservationState) WHERE cs.domain = 'soc' RETURN cs.domain AS domain, cs.status AS status, cs.alpha AS alpha, cs.q AS q, cs.V AS V, cs.theta_min AS theta_min, cs.categories_total AS categories_total, cs.categories_with_data AS categories_with_data LIMIT 10"
        ),
        "decisions": run(
            "MATCH (d:Decision) WHERE d.decision_id IS NOT NULL RETURN d.domain AS domain, count(d) AS cnt ORDER BY domain"
        ),
    }
    return {
        "L5Centroid": centroids,
        "L5DKWeight": dk_weights,
        "L5ConservationState": conservation,
        "Welford": welford,
        "SHAPED_BY": shaped,
        "TRIGGERED_BY": triggered,
        "samples": samples,
    }


def classify_readiness(rb: dict[str, Any]) -> tuple[str, list[dict[str, str]], str]:
    missing: list[dict[str, str]] = []
    if int(rb.get("L5Centroid", {}).get("soc", 0)) <= 0:
        missing.append({"domain": "soc", "cell": "L5Centroid", "reason": "count is zero"})
    if int(rb.get("L5DKWeight", {}).get("soc", 0)) <= 0:
        missing.append({"domain": "soc", "cell": "L5DKWeight", "reason": "count is zero"})
    conservation = rb.get("L5ConservationState", {}).get("soc", {})
    if int(conservation.get("count", 0)) <= 0:
        missing.append({"domain": "soc", "cell": "L5ConservationState", "reason": "count is zero"})
    if not rb.get("Welford", {}).get("soc", {}).get("present"):
        missing.append({"domain": "soc", "cell": "Welford", "reason": "six fields not present"})
    if int(rb.get("SHAPED_BY", {}).get("soc", 0)) <= 0:
        missing.append({"domain": "soc", "cell": "SHAPED_BY", "reason": "edge count is zero"})
    conservation_samples = rb.get("samples", {}).get("conservation", [])
    if conservation_samples:
        theta = conservation_samples[0].get("theta_min")
        if theta in (None, "Infinity", "inf", "Infinity::float"):
            missing.append({"domain": "soc", "cell": "theta_min", "reason": "not finite"})
    decision_domains = {
        str(row.get("domain")): int(row.get("cnt") or row.get("count") or 0)
        for row in rb.get("samples", {}).get("decisions", [])
        if row.get("domain") is not None
    }
    if int(decision_domains.get("soc", 0)) <= 0:
        missing.append({"domain": "soc", "cell": "Decision.domain", "reason": "no proof Decisions with domain=soc"})
    transition = "transition not exercised"
    if int(rb.get("TRIGGERED_BY", {}).get("soc", 0)) > 0:
        transition = "present"
    return ("READY_FOR_C9B_PROOF" if not missing else "PARTIAL_SEE_MISSING"), missing, transition


def _format_alert_id(prefix: str, index: int) -> str:
    return f"{prefix}-{index:04d}"


def extract_decision_id(body: dict[str, Any]) -> str | None:
    for key in ("decision_id", "id"):
        value = body.get(key)
        if value:
            return str(value)
    for key in ("recommendation", "gae_scoring", "decision"):
        nested = body.get(key)
        if isinstance(nested, dict):
            value = nested.get("decision_id") or nested.get("id")
            if value:
                return str(value)
    return None


def extract_recommended_action(body: dict[str, Any]) -> str | None:
    for key in ("recommended_action", "action"):
        value = body.get(key)
        if value:
            return str(value)
    for key in ("recommendation", "gae_scoring", "decision"):
        nested = body.get(key)
        if isinstance(nested, dict):
            value = nested.get("recommended_action") or nested.get("action")
            if value:
                return str(value)
    return None


def seed_guidance(prefix: str, count: int) -> str:
    return f"Run scripts\\soc_c9b_seed_alerts.py --count {count} --prefix {prefix} first"


def run_route_loops(
    loops: int,
    *,
    alert_prefix: str = "C9B-SOC",
    start_index: int = 1,
    max_attempts: int | None = None,
) -> RouteResult:
    from fastapi.testclient import TestClient
    from app.main import app

    actions = ["escalate", "investigate", "suppress", "monitor"]
    max_attempts = max_attempts or loops * 5
    result = RouteResult()
    attempt = 0
    with TestClient(app, raise_server_exceptions=False) as client:
        while result.valid_scorer_action_outcomes < loops and attempt < max_attempts:
            alert_id = _format_alert_id(alert_prefix, start_index + attempt)
            result.attempted += 1
            score = client.post("/api/alert/analyze", json={"alert_id": alert_id})
            if score.status_code != 200:
                result.failures.append(f"analyze {attempt}: HTTP {score.status_code} {score.text[:160]}")
                attempt += 1
                continue
            result.score_ok += 1
            body = score.json()
            decision_id = extract_decision_id(body)
            if not decision_id:
                result.failures.append(f"analyze {attempt}: missing decision_id")
                attempt += 1
                continue
            action = extract_recommended_action(body) or actions[attempt % len(actions)]
            if action not in actions:
                result.skipped_routing_actions += 1
                result.invalid_actions[action] = result.invalid_actions.get(action, 0) + 1
                attempt += 1
                continue
            outcome = client.post(
                "/api/alert/outcome",
                json={
                    "alert_id": alert_id,
                    "decision_id": decision_id,
                    "outcome": "correct",
                    "analyst_action": action,
                },
            )
            if outcome.status_code != 200:
                result.failures.append(f"outcome {attempt}: HTTP {outcome.status_code} {outcome.text[:160]}")
                attempt += 1
                continue
            result.outcome_ok += 1
            result.valid_scorer_action_outcomes += 1
            attempt += 1
    if result.valid_scorer_action_outcomes < loops:
        result.failures.append(
            "valid scorer-action outcomes "
            f"{result.valid_scorer_action_outcomes}/{loops} after {result.attempted} analyze attempts"
        )
    return result


def build_summary(args: argparse.Namespace) -> dict[str, Any]:
    dsn, dsn_source = choose_database_url(args.database_url, os.getenv("GRAPH_DSN"))
    env = {
        "database_url": redact_dsn(dsn),
        "dsn_source": dsn_source,
        "graph_name": args.graph_name,
        "soc_learning_enabled": os.getenv("SOC_LEARNING_ENABLED"),
        "dk_proof_mode": args.dk_proof_mode,
        "target_category": args.target_category,
    }
    if dsn is None:
        return {
            "verdict": "BLOCKED_ENV",
            "environment": env,
            "route": None,
            "readback": {},
            "missing_cells": [{"domain": "soc", "cell": "environment", "reason": dsn_source}],
            "triggered_by": "not checked",
            "next_action": "set DATABASE_URL to a live AGE/Postgres DSN",
        }

    if args.dry_run:
        return {
            "verdict": "PARTIAL_SEE_MISSING",
            "environment": env,
            "route": {
                "planned_loops": args.loops,
                "alert_prefix": args.alert_prefix,
                "start_index": args.start_index,
                "method": "TestClient /api/alert/analyze -> /api/alert/outcome",
            },
            "readback": {},
            "missing_cells": [{"domain": "soc", "cell": "dry_run", "reason": "route/readback not executed"}],
            "triggered_by": "not checked",
            "next_action": "run without --dry-run",
        }

    os.environ["GRAPH_DSN"] = dsn
    os.environ["GRAPH_BACKEND"] = os.environ.get("GRAPH_BACKEND") or "age"
    os.environ["AGE_GRAPH_NAME"] = args.graph_name
    os.environ["SOC_LEARNING_ENABLED"] = os.environ.get("SOC_LEARNING_ENABLED") or "1"

    route = None
    if not args.readback_only:
        route_result = run_route_loops(
            args.loops,
            alert_prefix=args.alert_prefix,
            start_index=args.start_index,
            max_attempts=args.max_attempts or (args.loops * 4 if args.dk_proof_mode else args.loops * 5),
        )
        route = route_result.__dict__
        if route_result.outcome_ok == 0 and route_result.failures:
            missing_alert_inputs = all(
                ("Alert " in failure or "Context for " in failure) and "not found" in failure
                for failure in route_result.failures
            )
            return {
                "verdict": "BLOCKED_ENV" if missing_alert_inputs else "FAIL_NEEDS_FIXER",
                "environment": env,
                "route": route,
                "readback": {},
                "missing_cells": [{"domain": "soc", "cell": "route", "reason": "no outcome loops succeeded"}],
                "triggered_by": "not checked",
                "next_action": (
                    seed_guidance(args.alert_prefix, args.start_index + args.loops - 1)
                    if missing_alert_inputs
                    else "fix SOC route/live environment blocker"
                ),
            }

    rb = readback(_make_store(dsn, args.graph_name)) if (args.readback or args.readback_only) else {}
    verdict, missing, triggered = classify_readiness(rb) if rb else ("PARTIAL_SEE_MISSING", [], "not checked")
    return {
        "verdict": verdict,
        "environment": env,
        "route": route,
        "readback": rb,
        "missing_cells": missing,
        "triggered_by": triggered,
        "next_action": "generate C9B proof report" if verdict == "READY_FOR_C9B_PROOF" else "inspect missing cells",
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = build_summary(args)
    if args.json:
        print(json.dumps(summary, indent=None, sort_keys=True, default=str))
    else:
        print("SOC C9B live AGE smoke")
        print(f"verdict: {summary['verdict']}")
        print(f"graph: {summary['environment']['graph_name']}")
        print(f"dsn: {summary['environment']['database_url']}")
        print(f"dsn_source: {summary['environment']['dsn_source']}")
        print(f"route: {json.dumps(summary.get('route'), default=str)}")
        print(f"missing_cells: {json.dumps(summary.get('missing_cells'), default=str)}")
        print(f"triggered_by: {summary.get('triggered_by')}")
        print(f"next_action: {summary.get('next_action')}")
    return 0 if summary["verdict"] != "BLOCKED_ENV" else 2


if __name__ == "__main__":
    raise SystemExit(main())
