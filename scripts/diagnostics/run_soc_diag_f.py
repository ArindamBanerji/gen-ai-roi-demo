from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECTS_ROOT = REPO_ROOT.parent
CI_PLATFORM = PROJECTS_ROOT / "ci-platform"
BACKEND_ROOT = REPO_ROOT / "backend"
DEFAULT_CONTRACT_PATH = REPO_ROOT / "scratch" / "temp" / "soc_diag_backend_contract.json"

for path in (str(CI_PLATFORM), str(BACKEND_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)


DEFAULT_DSN = "host=localhost port=5433 dbname=soc_copilot user=postgres password=postgres"
MILESTONES = {195, 200, 201, 205, 230, 250}
SCORABLE_ACTIONS = {"escalate", "investigate", "suppress", "monitor"}
PROGRESS_PATH = REPO_ROOT / "scratch" / "temp" / "soc_diag_f_progress.json"

PASS_VERDICT = "EXTERNAL_DIAGNOSTIC_F_PASS"
DRY_RUN_VERDICT = "DRY_RUN_ONLY"
FAIL_VERDICTS = {
    "ENV_VALIDATION_FAILED",
    "BACKEND_UNREACHABLE",
    "BACKEND_RUNTIME_CONTRACT_UNVERIFIED",
    "AGE_GRAPH_READBACK_FAILED",
    "SEED_RUNTIME_FAILURE",
    "SEED_DATA_ISSUE",
    "ANALYZE_HTTP_FAILURE",
    "OUTCOME_HTTP_FAILURE",
    "LOOP_HTTP_FAILURE",
    "TARGET_CATEGORY_NOT_REACHED",
    "PHASE_TRANSITION_MISSING",
    "L5CENTROID_MISSING",
    "SHAPED_BY_MISSING",
    "L5DKWEIGHT_MISSING",
    "WELFORD_MISSING",
    "DK_DECISION_COUNT_MISSING",
    "INTERRUPTED",
    "UNEXPECTED_RUNTIME_ERROR",
}

SCENARIO_NAMES = (
    "diagnostic-e-5-decision",
    "diagnostic-f-dk",
    "c9b-final-proof",
    "sanity-one-alert",
    "seed-only-smoke",
    "l5-centroid-proof",
    "dk-threshold-proof",
)


class DiagnosticFailure(RuntimeError):
    def __init__(self, verdict: str, message: str):
        super().__init__(message)
        self.verdict = verdict


@dataclass(frozen=True)
class ScenarioConfig:
    name: str
    target_category: str
    target_outcomes: int
    max_attempts: int
    allowed_actions: set[str]
    skip_actions: set[str]
    milestones: set[int]
    input_provider: str
    pass_criteria: tuple[str, ...]


def build_scenario_config(args: argparse.Namespace) -> ScenarioConfig:
    target_category = args.target_category
    scenarios: dict[str, ScenarioConfig] = {
        "diagnostic-e-5-decision": ScenarioConfig(
            name="diagnostic-e-5-decision",
            target_category=target_category,
            target_outcomes=5,
            max_attempts=5,
            allowed_actions=SCORABLE_ACTIONS,
            skip_actions={"refer_to_analyst"},
            milestones={5},
            input_provider="fixed_c9b_stream",
            pass_criteria=("target_outcomes", "l5_centroid", "shaped_by"),
        ),
        "diagnostic-f-dk": ScenarioConfig(
            name="diagnostic-f-dk",
            target_category=target_category,
            target_outcomes=250,
            max_attempts=300,
            allowed_actions=SCORABLE_ACTIONS,
            skip_actions={"refer_to_analyst"},
            milestones=MILESTONES,
            input_provider="fixed_c9b_stream",
            pass_criteria=("target_outcomes", "l5_dk_weight", "welford", "dk_n_decisions_used"),
        ),
        "c9b-final-proof": ScenarioConfig(
            name="c9b-final-proof",
            target_category=target_category,
            target_outcomes=250,
            max_attempts=300,
            allowed_actions=SCORABLE_ACTIONS,
            skip_actions={"refer_to_analyst"},
            milestones=MILESTONES,
            input_provider="fixed_c9b_stream",
            pass_criteria=("target_outcomes", "l5_centroid", "shaped_by", "l5_dk_weight", "welford", "dk_n_decisions_used"),
        ),
        "sanity-one-alert": ScenarioConfig(
            name="sanity-one-alert",
            target_category=target_category,
            target_outcomes=1,
            max_attempts=1,
            allowed_actions=SCORABLE_ACTIONS,
            skip_actions={"refer_to_analyst"},
            milestones={1},
            input_provider="fixed_c9b_stream",
            pass_criteria=("target_outcomes",),
        ),
        "seed-only-smoke": ScenarioConfig(
            name="seed-only-smoke",
            target_category=target_category,
            target_outcomes=0,
            max_attempts=1,
            allowed_actions=SCORABLE_ACTIONS,
            skip_actions={"refer_to_analyst"},
            milestones=set(),
            input_provider="fixed_c9b_seed_only",
            pass_criteria=("seeded_alerts",),
        ),
        "l5-centroid-proof": ScenarioConfig(
            name="l5-centroid-proof",
            target_category=target_category,
            target_outcomes=5,
            max_attempts=10,
            allowed_actions=SCORABLE_ACTIONS,
            skip_actions={"refer_to_analyst"},
            milestones={5},
            input_provider="fixed_c9b_stream",
            pass_criteria=("target_outcomes", "l5_centroid", "shaped_by"),
        ),
        "dk-threshold-proof": ScenarioConfig(
            name="dk-threshold-proof",
            target_category=target_category,
            target_outcomes=250,
            max_attempts=300,
            allowed_actions=SCORABLE_ACTIONS,
            skip_actions={"refer_to_analyst"},
            milestones=MILESTONES,
            input_provider="fixed_c9b_stream",
            pass_criteria=("target_outcomes", "l5_dk_weight", "welford", "dk_n_decisions_used"),
        ),
    }
    return scenarios[args.scenario]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SOC external proof harness scenarios with deterministic runtime checks.")
    parser.add_argument("--scenario", choices=SCENARIO_NAMES, default="diagnostic-f-dk")
    parser.add_argument("--graph-name", required=True)
    parser.add_argument("--backend-url", default="http://127.0.0.1:8001")
    parser.add_argument("--prefix", default="DIAG-F2-CRED")
    parser.add_argument("--seed-count", type=int, default=None, help="Deprecated alias for --max-attempts.")
    parser.add_argument("--max-attempts", type=int, default=None)
    parser.add_argument("--target-outcomes", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--target-category", default="credential_access")
    parser.add_argument("--graph-dsn", default=os.getenv("GRAPH_DSN", DEFAULT_DSN))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--sanity-count", type=int, default=1)
    parser.add_argument("--seed-sleep-seconds", type=float, default=0.15)
    parser.add_argument("--attempt-sleep-seconds", type=float, default=0.05)
    parser.add_argument("--batch-sleep-seconds", type=float, default=2.0)
    parser.add_argument("--seed-timeout-seconds", type=float, default=60.0)
    parser.add_argument("--seed-max-retries", type=int, default=3)
    parser.add_argument("--max-seed-failures", type=int, default=3)
    parser.add_argument("--preflight-seed-count", type=int, default=5)
    parser.add_argument("--bulk-seed-first", action="store_true", help="Legacy stress mode; default proof mode streams seed/analyze/outcome.")
    parser.add_argument(
        "--seed-strategy",
        choices=("direct-age", "existing-seed-script"),
        default="direct-age",
    )
    parser.add_argument("--report-dir", type=Path, default=REPO_ROOT / "docs" / "implementation_plans")
    parser.add_argument("--backend-contract", type=Path, default=DEFAULT_CONTRACT_PATH)
    parser.add_argument(
        "--assume-backend-contract",
        action="store_true",
        help="Record a user assertion instead of requiring the backend contract file.",
    )
    args = parser.parse_args()
    if args.seed_count is not None and args.max_attempts is not None and args.seed_count != args.max_attempts:
        parser.error("--seed-count is a deprecated alias for --max-attempts; provide only one value or matching values.")
    if not args.graph_dsn:
        args.graph_dsn = DEFAULT_DSN
    args.scenario_config = build_scenario_config(args)
    if args.target_outcomes is None:
        args.target_outcomes = args.scenario_config.target_outcomes
    if args.seed_count is not None and args.max_attempts is None:
        args.max_attempts = args.seed_count
    if args.max_attempts is None:
        args.max_attempts = args.scenario_config.max_attempts
    args.seed_count = args.max_attempts
    return args


def redact_dsn(dsn: str | None) -> str | None:
    if dsn is None:
        return None
    parts = []
    for part in str(dsn).split():
        if part.lower().startswith("password="):
            parts.append("password=***")
        else:
            parts.append(part)
    return " ".join(parts)


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def source_ci_platform_import_path() -> str:
    import ci_platform.graph.age_graph_store as module

    import_path = Path(module.__file__).resolve()
    if not is_relative_to(import_path, CI_PLATFORM):
        raise DiagnosticFailure(
            "ENV_VALIDATION_FAILED",
            f"ci_platform resolves to {import_path}; expected source under {CI_PLATFORM.resolve()}",
        )
    return str(import_path)


def http_json(method: str, url: str, payload: dict[str, Any] | None = None, timeout: int = 30) -> tuple[int, Any]:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, headers=headers, method=method)
    with urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
        return response.status, json.loads(raw) if raw else None


def check_health(backend_url: str) -> dict[str, Any]:
    try:
        _, payload = http_json("GET", f"{backend_url.rstrip('/')}/health", timeout=10)
    except (HTTPError, URLError, TimeoutError) as exc:
        raise DiagnosticFailure("BACKEND_UNREACHABLE", f"/health failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise DiagnosticFailure("BACKEND_UNREACHABLE", f"/health returned non-object payload: {payload!r}")
    return payload


def validate_backend_contract(args: argparse.Namespace, payload: dict[str, Any]) -> dict[str, Any]:
    statement = (
        "Backend import path cannot be directly introspected without a debug endpoint; "
        "proof assumes backend was launched by run_soc_diag_backend.ps1 or demo.py --diag-mode "
        "with matching graph/env."
    )
    payload["backend_runtime_contract_statement"] = statement
    expected_ci = str(CI_PLATFORM.resolve())
    if args.assume_backend_contract:
        contract = {
            "mode": "user_asserted",
            "graph_name": args.graph_name,
            "graph_dsn_redacted": redact_dsn(args.graph_dsn),
            "ci_platform_import_path": None,
            "statement": statement,
        }
        payload["backend_contract"] = contract
        return contract

    if not args.backend_contract.exists():
        raise DiagnosticFailure(
            "BACKEND_RUNTIME_CONTRACT_UNVERIFIED",
            f"backend contract file missing: {args.backend_contract}",
        )
    try:
        contract = json.loads(args.backend_contract.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DiagnosticFailure(
            "BACKEND_RUNTIME_CONTRACT_UNVERIFIED",
            f"backend contract file is unreadable: {exc}",
        ) from exc

    errors: list[str] = []
    if contract.get("graph_name") != args.graph_name:
        errors.append(f"graph_name={contract.get('graph_name')!r} expected {args.graph_name!r}")
    import_path = contract.get("ci_platform_import_path")
    if not import_path or not is_relative_to(Path(str(import_path)), CI_PLATFORM):
        errors.append(f"ci_platform_import_path={import_path!r} expected under {expected_ci}")
    if contract.get("soc_learning_enabled") != "true":
        errors.append(f"soc_learning_enabled={contract.get('soc_learning_enabled')!r} expected 'true'")
    if errors:
        raise DiagnosticFailure("BACKEND_RUNTIME_CONTRACT_UNVERIFIED", "; ".join(errors))

    payload["backend_contract"] = contract
    return contract


def nested_get(payload: Any, *paths: tuple[str, ...]) -> Any:
    for path in paths:
        current = payload
        for key in path:
            if not isinstance(current, dict) or key not in current:
                current = None
                break
            current = current[key]
        if current is not None:
            return current
    return None


def alert_id(prefix: str, index: int) -> str:
    return f"{prefix}-{index:04d}"


def _literal(value: Any) -> str:
    from app.graph_schema import _S

    return _S(value)


def _props(properties: dict[str, Any]) -> str:
    return ", ".join(f"{key}: {_literal(value)}" for key, value in properties.items())


async def scalar_count(client: Any, query: str) -> int:
    rows = await client.run_query(query)
    if not rows:
        return 0
    return int(rows[0].get("cnt") or rows[0].get("total") or 0)


async def node_exists(client: Any, label: str, key: str, value: str) -> bool:
    return (
        await scalar_count(
            client,
            f"MATCH (n:{label} {{{key}: {_literal(value)}}}) RETURN count(n) AS cnt",
        )
        > 0
    )


async def edge_exists(
    client: Any,
    from_label: str,
    from_key: str,
    from_value: str,
    edge_type: str,
    to_label: str,
    to_key: str,
    to_value: str,
) -> bool:
    query = (
        f"MATCH (a:{from_label} {{{from_key}: {_literal(from_value)}}})"
        f"-[r:{edge_type}]->"
        f"(b:{to_label} {{{to_key}: {_literal(to_value)}}}) "
        "RETURN count(r) AS cnt"
    )
    return await scalar_count(client, query) > 0


async def create_node_if_missing(client: Any, label: str, key: str, value: str, properties: dict[str, Any]) -> bool:
    if await node_exists(client, label, key, value):
        return False
    await client.run_query(f"CREATE (n:{label} {{{_props(properties)}}})")
    return True


async def create_edge_if_missing(
    client: Any,
    from_label: str,
    from_key: str,
    from_value: str,
    edge_type: str,
    to_label: str,
    to_key: str,
    to_value: str,
) -> bool:
    if await edge_exists(client, from_label, from_key, from_value, edge_type, to_label, to_key, to_value):
        return False
    await client.run_query(
        f"MATCH (a:{from_label} {{{from_key}: {_literal(from_value)}}}), "
        f"(b:{to_label} {{{to_key}: {_literal(to_value)}}}) "
        f"CREATE (a)-[:{edge_type}]->(b)"
    )
    return True


async def seed_one(client: Any, payload: dict[str, Any], prefix: str, index: int, category: str) -> str:
    aid = alert_id(prefix, index)
    user_id = f"{prefix}-USER-{index:04d}"
    asset_id = f"{prefix}-ASSET-{index:04d}"
    payload["seed_attempted_count"] += 1
    exists = await node_exists(client, "Alert", "alert_id", aid)
    if not exists:
        await create_node_if_missing(
            client,
            "User",
            "user_id",
            user_id,
            {
                "user_id": user_id,
                "id": user_id,
                "name": f"Diagnostic User {index:04d}",
                "origin": "soc_diag_f_runner",
                "department": "SOC",
                "risk_level": "critical",
                "risk_score": 0.92,
                "c9b_proof": True,
            },
        )
        await create_node_if_missing(
            client,
            "Asset",
            "asset_id",
            asset_id,
            {
                "asset_id": asset_id,
                "id": asset_id,
                "hostname": f"diag-f-{index:04d}",
                "criticality": "critical",
                "origin": "soc_diag_f_runner",
                "asset_type": "workload",
                "business_unit": "security",
                "c9b_proof": True,
            },
        )
        await client.run_query(
            "CREATE (a:Alert {"
            + _props(
                {
                    "alert_id": aid,
                    "id": aid,
                    "category": category,
                    "severity": "critical",
                    "risk_score": 0.92,
                    "alert_type": "anomalous_login",
                    "status": "pending",
                    "origin": "soc_diag_f_runner",
                    "source": "soc_diag_f_runner",
                    "c9b_proof": True,
                    "timestamp_epoch": 1_725_000_000_000 + index,
                    "source_location": f"diag-f-zone-{index % 6}",
                    "user_id": user_id,
                    "asset_id": asset_id,
                    "attack_pattern_id": "",
                    "mfa_completed": False,
                    "device_fingerprint_match": False,
                    "vpn_provider": "c9b_seed",
                }
            )
            + "})"
        )
    await create_edge_if_missing(client, "Alert", "alert_id", aid, "INVOLVES", "User", "user_id", user_id)
    await create_edge_if_missing(client, "Alert", "alert_id", aid, "DETECTED_ON", "Asset", "asset_id", asset_id)
    payload["seed_completed_count"] += 1
    return aid


async def seed_batch(
    client: Any,
    payload: dict[str, Any],
    prefix: str,
    start: int,
    count: int,
    category: str,
    seed_sleep_seconds: float = 0.0,
) -> list[str]:
    seeded: list[str] = []
    for index in range(start, start + count):
        seeded.append(await seed_one(client, payload, prefix, index, category))
        if seed_sleep_seconds > 0 and index < start + count - 1:
            await asyncio.sleep(seed_sleep_seconds)
    return seeded


async def read_alert_count(client: Any, prefix: str) -> int:
    return await scalar_count(
        client,
        f"MATCH (a:Alert) WHERE a.alert_id STARTS WITH {_literal(prefix)} RETURN count(a) AS cnt",
    )


@dataclass
class LoopResult:
    alert_id: str
    analyze_status: int | None = None
    outcome_status: int | None = None
    category: str | None = None
    action: str | None = None
    confidence: float | None = None
    decision_id: str | None = None
    outcome_id: str | None = None
    skipped_reason: str | None = None


def extract_analyze(payload: dict[str, Any]) -> dict[str, Any]:
    factor_vector = nested_get(payload, ("factor_vector",), ("gae_scoring", "factor_vector"))
    return {
        "category": nested_get(payload, ("category",), ("alert_category",), ("alert", "category"), ("gae_scoring", "category")),
        "action": nested_get(
            payload,
            ("action",),
            ("recommended_action",),
            ("recommendation", "action"),
            ("recommendation", "recommended_action"),
        ),
        "confidence": nested_get(payload, ("confidence",), ("recommendation", "confidence"), ("gae_scoring", "confidence")),
        "decision_id": nested_get(payload, ("decision_id",), ("recommendation", "decision_id"), ("gae_scoring", "decision_id")),
        "factor_vector": factor_vector,
    }


async def final_readback(client: Any, prefix: str) -> dict[str, Any]:
    queries = {
        "decisions": (
            f"MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) "
            f"WHERE d.domain = 'soc' AND a.alert_id STARTS WITH {_literal(prefix)} "
            "RETURN count(d) AS cnt"
        ),
        "verified": (
            f"MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) "
            f"WHERE d.domain = 'soc' AND a.alert_id STARTS WITH {_literal(prefix)} "
            "AND d.correct = true RETURN count(d) AS cnt"
        ),
        "outcome_present": (
            f"MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) "
            f"WHERE d.domain = 'soc' AND a.alert_id STARTS WITH {_literal(prefix)} "
            "AND d.outcome IS NOT NULL RETURN count(d) AS cnt"
        ),
        "l5_centroid": "MATCH (c:L5Centroid) WHERE c.domain = 'soc' RETURN count(c) AS cnt",
        "shaped_by": "MATCH (:L5Centroid {domain: 'soc'})-[r:SHAPED_BY]->(:Decision {domain: 'soc'}) RETURN count(r) AS cnt",
        "l5_dk_weight": "MATCH (w:L5DKWeight) WHERE w.domain = 'soc' RETURN count(w) AS cnt",
        "dk_welford_rows": (
            "MATCH (w:L5DKWeight) WHERE w.domain = 'soc' "
            "RETURN w.dk_weight_id AS dk_weight_id, "
            "w.n_decisions_used AS n_decisions_used, "
            "w.n_confirmed AS n_confirmed, "
            "w.n_overridden AS n_overridden, "
            "w.confirmed_mean_json AS confirmed_mean_json, "
            "w.confirmed_m2_json AS confirmed_m2_json, "
            "w.overridden_mean_json AS overridden_mean_json, "
            "w.overridden_m2_json AS overridden_m2_json, "
            "w.all_mean_json AS all_mean_json, "
            "w.all_m2_json AS all_m2_json "
            "ORDER BY w.created_at DESC LIMIT 5"
        ),
    }
    result: dict[str, Any] = {}
    try:
        for key, query in queries.items():
            result[key] = await client.run_query(query)
    except Exception as exc:
        raise DiagnosticFailure("AGE_GRAPH_READBACK_FAILED", f"AGE readback failed: {exc}") from exc
    return result


async def progress_readback(client: Any, prefix: str) -> dict[str, Any]:
    readback = await final_readback(client, prefix)
    return {
        "decisions": first_count(readback.get("decisions")),
        "verified": first_count(readback.get("verified")),
        "outcome_present": first_count(readback.get("outcome_present")),
        "l5_centroid": first_count(readback.get("l5_centroid")),
        "shaped_by": first_count(readback.get("shaped_by")),
        "l5_dk_weight": first_count(readback.get("l5_dk_weight")),
    }


def first_count(rows: Any) -> int:
    if not isinstance(rows, list) or not rows:
        return 0
    first = rows[0]
    if not isinstance(first, dict):
        return 0
    return int(first.get("cnt") or first.get("total") or 0)


def welford_present(rows: Any) -> bool:
    if not isinstance(rows, list) or not rows:
        return False
    required = (
        "confirmed_mean_json",
        "confirmed_m2_json",
        "overridden_mean_json",
        "overridden_m2_json",
        "all_mean_json",
        "all_m2_json",
    )
    for row in rows:
        if isinstance(row, dict) and all(row.get(key) is not None for key in required):
            return True
    return False


def max_n_decisions_used(rows: Any) -> int:
    if not isinstance(rows, list):
        return 0
    values: list[int] = []
    for row in rows:
        if isinstance(row, dict):
            try:
                values.append(int(row.get("n_decisions_used") or 0))
            except (TypeError, ValueError):
                values.append(0)
    return max(values) if values else 0


def classify_verdict(args: argparse.Namespace, payload: dict[str, Any]) -> tuple[str, int, list[str]]:
    if payload["failures"]:
        first = payload["failures"][0]
        return str(first.get("verdict") or "UNEXPECTED_RUNTIME_ERROR"), 1, [str(first.get("message"))]
    if args.dry_run:
        return DRY_RUN_VERDICT, 0, ["dry-run only; no proof loop was executed"]

    criteria = set(args.scenario_config.pass_criteria)
    failures: list[str] = []
    if "target_outcomes" in criteria and payload["valid_outcomes"] < args.target_outcomes:
        failures.append(f"valid target-category outcomes {payload['valid_outcomes']} < target {args.target_outcomes}")
        return "TARGET_CATEGORY_NOT_REACHED", 1, failures
    if "seeded_alerts" in criteria and payload.get("seeded_alerts", 0) <= 0:
        failures.append("no alert was seeded")
        return "SEED_DATA_ISSUE", 1, failures
    readback = payload.get("readback") or {}
    dk_count = first_count(readback.get("l5_dk_weight"))
    l5_centroid_count = first_count(readback.get("l5_centroid"))
    shaped_by_count = first_count(readback.get("shaped_by"))
    has_welford = welford_present(readback.get("dk_welford_rows"))
    dk_n_used = max_n_decisions_used(readback.get("dk_welford_rows"))
    if "l5_centroid" in criteria and l5_centroid_count <= 0:
        failures.append("L5Centroid count is 0")
        return "L5CENTROID_MISSING", 1, failures
    if "shaped_by" in criteria and shaped_by_count <= 0:
        failures.append("SHAPED_BY count is 0")
        return "SHAPED_BY_MISSING", 1, failures
    if "l5_dk_weight" in criteria and dk_count <= 0:
        failures.append("L5DKWeight count is 0")
        return "L5DKWEIGHT_MISSING", 1, failures
    if "welford" in criteria and not has_welford:
        failures.append("Welford fields are absent or partial")
        return "WELFORD_MISSING", 1, failures
    if "dk_n_decisions_used" in criteria and dk_n_used < args.target_outcomes:
        failures.append(f"max L5DKWeight n_decisions_used {dk_n_used} < target {args.target_outcomes}")
        return "DK_DECISION_COUNT_MISSING", 1, failures
    return PASS_VERDICT, 0, []


def base_payload(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "started_epoch": time.time(),
        "graph_name": args.graph_name,
        "backend_url": args.backend_url,
        "prefix": args.prefix,
        "runner_ci_platform_import_path": None,
        "backend_contract": None,
        "health": None,
        "dry_run": args.dry_run,
        "scenario": args.scenario_config.name,
        "scenario_config": {
            "name": args.scenario_config.name,
            "target_category": args.scenario_config.target_category,
            "target_outcomes": args.target_outcomes,
            "max_attempts": args.max_attempts,
            "allowed_actions": sorted(args.scenario_config.allowed_actions),
            "skip_actions": sorted(args.scenario_config.skip_actions),
            "milestones": sorted(args.scenario_config.milestones),
            "input_provider": args.scenario_config.input_provider,
            "pass_criteria": list(args.scenario_config.pass_criteria),
        },
        "mode": "bulk_seed_first" if args.bulk_seed_first else "streaming",
        "max_attempts": args.max_attempts,
        "seed_count": args.seed_count,
        "target_outcomes": args.target_outcomes,
        "batch_size": args.batch_size,
        "sanity_count": args.sanity_count,
        "seed_strategy": args.seed_strategy,
        "seed_sleep_seconds": args.seed_sleep_seconds,
        "attempt_sleep_seconds": args.attempt_sleep_seconds,
        "batch_sleep_seconds": args.batch_sleep_seconds,
        "seed_timeout_seconds": args.seed_timeout_seconds,
        "seed_max_retries": args.seed_max_retries,
        "max_seed_failures": args.max_seed_failures,
        "preflight_seed_count": args.preflight_seed_count,
        "seed_contract_source": "duplicated_from_current_seed_contract",
        "seed_contract_todo": "P3: reuse scripts/soc_c9b_seed_alerts.py when a small proof-mode interface exists.",
        "seed_shape": {
            "alert_type": "anomalous_login",
            "category": args.target_category,
            "severity": "critical",
            "risk_score": 0.92,
            "asset_criticality": "critical",
            "mfa_completed": False,
            "device_fingerprint_match": False,
        },
        "seed_attempted_count": 0,
        "seed_completed_count": 0,
        "seeded_alerts": 0,
        "seed_failures": 0,
        "seeded_alerts_readback": 0,
        "current_attempt_index": None,
        "current_batch_index": None,
        "current_batch_start": None,
        "current_batch_end": None,
        "seed_retries": 0,
        "last_seed_error": None,
        "analyze_attempts": 0,
        "outcome_attempts": 0,
        "valid_outcomes": 0,
        "skipped_refer_to_analyst": 0,
        "other_categories": 0,
        "other_action_skips": 0,
        "one_process_loop": True,
        "latest_alert_id": None,
        "latest_action": None,
        "latest_confidence": None,
        "progress_path": str(PROGRESS_PATH),
        "failures": [],
        "last_successful_phase": "initialized",
        "exception": None,
        "milestones": {},
        "progress_readbacks": {},
        "loops": [],
        "readback": None,
        "verdict": None,
        "exit_code": None,
        "proof_passed": False,
        "criteria_failures": [],
        "report_json_path": None,
        "report_md_path": None,
    }


def add_failure(payload: dict[str, Any], verdict: str, message: str) -> None:
    payload["failures"].append({"verdict": verdict, "message": message, "time_epoch": time.time()})


def elapsed(payload: dict[str, Any]) -> float:
    return round(time.time() - float(payload.get("started_epoch") or time.time()), 2)


def progress_snapshot(
    args: argparse.Namespace,
    payload: dict[str, Any],
    status: str,
    *,
    phase: str | None = None,
    latest_alert_id: str | None = None,
    latest_action: str | None = None,
    latest_confidence: float | None = None,
    milestone: int | None = None,
    verdict: str | None = None,
    report_json_path: Path | None = None,
    report_md_path: Path | None = None,
) -> dict[str, Any]:
    snapshot = {
        "status": status,
        "scenario": args.scenario_config.name,
        "graph_name": args.graph_name,
        "prefix": args.prefix,
        "phase": phase or payload.get("last_successful_phase"),
        "max_attempts": args.max_attempts,
        "current_attempt_index": payload.get("current_attempt_index"),
        "seed_completed": payload.get("seed_completed_count", 0),
        "seeded_alerts": payload.get("seeded_alerts", 0),
        "seed_failures": payload.get("seed_failures", 0),
        "seed_count": args.seed_count,
        "current_batch_index": payload.get("current_batch_index"),
        "current_batch_start": payload.get("current_batch_start"),
        "current_batch_end": payload.get("current_batch_end"),
        "seed_retries": payload.get("seed_retries", 0),
        "last_seed_error": payload.get("last_seed_error"),
        "seed_strategy": getattr(args, "seed_strategy", None),
        "seed_sleep_seconds": getattr(args, "seed_sleep_seconds", None),
        "attempt_sleep_seconds": getattr(args, "attempt_sleep_seconds", None),
        "batch_sleep_seconds": getattr(args, "batch_sleep_seconds", None),
        "max_seed_failures": getattr(args, "max_seed_failures", None),
        "preflight_seed_count": getattr(args, "preflight_seed_count", None),
        "attempts": payload.get("analyze_attempts", 0),
        "analyze_attempts": payload.get("analyze_attempts", 0),
        "outcome_attempts": payload.get("outcome_attempts", 0),
        "valid_target_outcomes": payload.get("valid_outcomes", 0),
        "target_outcomes": args.target_outcomes,
        "latest_alert_id": latest_alert_id or payload.get("latest_alert_id"),
        "latest_action": latest_action or payload.get("latest_action"),
        "latest_confidence": latest_confidence
        if latest_confidence is not None
        else payload.get("latest_confidence"),
        "skipped_refer_to_analyst": payload.get("skipped_refer_to_analyst", 0),
        "other_categories": payload.get("other_categories", 0),
        "other_action_skips": payload.get("other_action_skips", 0),
        "failures": payload.get("failures", []),
        "milestone": milestone,
        "elapsed_seconds": elapsed(payload),
        "report_json_path": str(report_json_path) if report_json_path else payload.get("report_json_path"),
        "report_md_path": str(report_md_path) if report_md_path else payload.get("report_md_path"),
        "verdict": verdict or payload.get("verdict"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_PATH.write_text(json.dumps(snapshot, indent=2, default=str), encoding="utf-8")
    return snapshot


def log_progress(
    args: argparse.Namespace,
    payload: dict[str, Any],
    status: str,
    message: str,
    **kwargs: Any,
) -> None:
    progress_snapshot(args, payload, status, **kwargs)
    print(message, flush=True)


def is_transient_seed_error(exc: BaseException) -> bool:
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
        return True
    text = str(exc).lower()
    transient_markers = (
        "timeout",
        "connection",
        "could not connect",
        "server closed",
        "too many clients",
        "connection refused",
        "connection reset",
        "ssl syscall",
        "temporarily unavailable",
    )
    return any(marker in text for marker in transient_markers)


def seed_retry_delay(attempt: int) -> float:
    return [1.0, 3.0, 5.0][min(attempt - 1, 2)]


def make_age_client(args: argparse.Namespace) -> Any:
    from ci_platform.graph.age_client import AGEClient

    return AGEClient(dsn=args.graph_dsn, graph_name=args.graph_name)


async def seed_batch_with_retries(
    args: argparse.Namespace,
    payload: dict[str, Any],
    client: Any,
    *,
    batch_number: int,
    batch_start: int,
    count: int,
) -> tuple[Any, list[str]]:
    batch_end = batch_start + count - 1
    payload["current_batch_index"] = batch_number
    payload["current_batch_start"] = batch_start
    payload["current_batch_end"] = batch_end
    max_attempts = max(1, args.seed_max_retries + 1)
    for attempt in range(1, max_attempts + 1):
        try:
            if attempt > 1:
                client = make_age_client(args)
            seeded = await asyncio.wait_for(
                seed_batch(
                    client,
                    payload,
                    args.prefix,
                    batch_start,
                    count,
                    args.target_category,
                    args.seed_sleep_seconds,
                ),
                timeout=args.seed_timeout_seconds if args.seed_timeout_seconds > 0 else None,
            )
            payload["last_seed_error"] = None
            return client, seeded
        except Exception as exc:
            payload["last_seed_error"] = str(exc)
            if not is_transient_seed_error(exc) or attempt >= max_attempts:
                raise
            payload["seed_retries"] += 1
            delay = seed_retry_delay(attempt)
            log_progress(
                args,
                payload,
                "SEED_RETRY",
                (
                    f"[SOC DIAG F] seed retry {attempt}/{args.seed_max_retries} "
                    f"batch={batch_number} range={alert_id(args.prefix, batch_start)}..{alert_id(args.prefix, batch_end)} "
                    f"error={exc} backoff={delay}s"
                ),
                phase="seeding",
                latest_alert_id=alert_id(args.prefix, batch_start),
            )
            await asyncio.sleep(delay)
    raise RuntimeError("seed retry loop exhausted unexpectedly")


async def seed_one_with_retries(
    args: argparse.Namespace,
    payload: dict[str, Any],
    client: Any,
    *,
    index: int,
) -> tuple[Any, str | None]:
    aid = alert_id(args.prefix, index)
    payload["current_attempt_index"] = index
    payload["current_batch_index"] = None
    payload["current_batch_start"] = index
    payload["current_batch_end"] = index
    max_attempts = max(1, args.seed_max_retries + 1)
    for attempt in range(1, max_attempts + 1):
        try:
            if attempt > 1:
                client = make_age_client(args)
            seeded_id = await asyncio.wait_for(
                seed_one(client, payload, args.prefix, index, args.target_category),
                timeout=args.seed_timeout_seconds if args.seed_timeout_seconds > 0 else None,
            )
            payload["last_seed_error"] = None
            payload["seeded_alerts"] = payload.get("seed_completed_count", 0)
            return client, seeded_id
        except Exception as exc:
            payload["last_seed_error"] = str(exc)
            if not is_transient_seed_error(exc) or attempt >= max_attempts:
                payload["seed_failures"] += 1
                return client, None
            payload["seed_retries"] += 1
            delay = seed_retry_delay(attempt)
            log_progress(
                args,
                payload,
                "SEED_RETRY",
                (
                    f"[SOC DIAG F] seed retry {attempt}/{args.seed_max_retries} "
                    f"attempt_index={index} alert_id={aid} error={exc} backoff={delay}s"
                ),
                phase="streaming_seed",
                latest_alert_id=aid,
            )
            await asyncio.sleep(delay)
    payload["seed_failures"] += 1
    return client, None


def write_reports(args: argparse.Namespace, payload: dict[str, Any]) -> tuple[Path, Path]:
    args.report_dir.mkdir(parents=True, exist_ok=True)
    safe_prefix = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in args.prefix)
    json_path = args.report_dir / f"soc_c9b_diag_f_runner_{safe_prefix}.json"
    md_path = args.report_dir / f"soc_c9b_diag_f_runner_{safe_prefix}.md"
    payload["report_json_path"] = str(json_path)
    payload["report_md_path"] = str(md_path)
    json_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    md_path.write_text(
        "\n".join(
            [
                "# SOC C9B Diagnostic F Runner Result",
                "",
                f"- verdict: `{payload.get('verdict')}`",
                f"- exit_code: `{payload.get('exit_code')}`",
                f"- proof_passed: `{payload.get('proof_passed')}`",
                f"- graph: `{args.graph_name}`",
                f"- prefix: `{args.prefix}`",
                f"- dry_run: `{args.dry_run}`",
                f"- scenario: `{payload.get('scenario')}`",
                f"- mode: `{payload.get('mode')}`",
                f"- input_provider: `{(payload.get('scenario_config') or {}).get('input_provider')}`",
                f"- pass_criteria: `{(payload.get('scenario_config') or {}).get('pass_criteria')}`",
                f"- max_attempts: `{payload.get('max_attempts')}`",
                f"- seed_attempted_count: `{payload.get('seed_attempted_count', 0)}`",
                f"- seed_completed_count: `{payload.get('seed_completed_count', 0)}`",
                f"- seeded_alerts: `{payload.get('seeded_alerts', 0)}`",
                f"- seed_failures: `{payload.get('seed_failures', 0)}`",
                f"- seed_strategy: `{payload.get('seed_strategy')}`",
                f"- seed_sleep_seconds: `{payload.get('seed_sleep_seconds')}`",
                f"- attempt_sleep_seconds: `{payload.get('attempt_sleep_seconds')}`",
                f"- batch_sleep_seconds: `{payload.get('batch_sleep_seconds')}`",
                f"- max_seed_failures: `{payload.get('max_seed_failures')}`",
                f"- preflight_seed_count: `{payload.get('preflight_seed_count')}`",
                f"- current_attempt_index: `{payload.get('current_attempt_index')}`",
                f"- current_batch_index: `{payload.get('current_batch_index')}`",
                f"- current_batch_start: `{payload.get('current_batch_start')}`",
                f"- current_batch_end: `{payload.get('current_batch_end')}`",
                f"- seed_retries: `{payload.get('seed_retries', 0)}`",
                f"- last_seed_error: `{payload.get('last_seed_error')}`",
                f"- analyze_attempts: `{payload.get('analyze_attempts', 0)}`",
                f"- outcome_attempts: `{payload.get('outcome_attempts', 0)}`",
                f"- valid_outcomes: `{payload.get('valid_outcomes', 0)}`",
                f"- skipped_refer_to_analyst: `{payload.get('skipped_refer_to_analyst', 0)}`",
                f"- other_categories: `{payload.get('other_categories', 0)}`",
                f"- other_action_skips: `{payload.get('other_action_skips', 0)}`",
                f"- last_successful_phase: `{payload.get('last_successful_phase')}`",
                f"- criteria_failures: `{payload.get('criteria_failures', [])}`",
                f"- exception: `{payload.get('exception')}`",
                f"- backend_contract_statement: `{payload.get('backend_runtime_contract_statement')}`",
                f"- report_json: `{json_path}`",
                f"- report_md: `{md_path}`",
                f"- progress_json: `{PROGRESS_PATH}`",
                "",
                "## Graph Hygiene",
                "- `soc_graph_diag_f3` is contaminated by an analyze-only failed run.",
                "- `soc_graph_diag_f4` is contaminated by a partial seed failure.",
                "- `soc_graph_diag_f5` is contaminated by a partial seed failure.",
                "- Next clean proof graph should be `soc_graph_diag_f6` with prefix `DIAG-F6-CRED`.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return json_path, md_path


def _http_error_message(exc: HTTPError) -> str:
    try:
        body = exc.read().decode("utf-8")
    except Exception:
        body = ""
    return f"HTTP {exc.code} {exc.reason}: {body}".strip()


async def run_analyze_outcome_pair(
    args: argparse.Namespace,
    payload: dict[str, Any],
    aid: str,
    *,
    phase: str,
    print_outcome_status: bool = False,
) -> LoopResult:
    item = LoopResult(alert_id=aid)
    try:
        payload["analyze_attempts"] += 1
        status, analyze_payload = http_json(
            "POST",
            f"{args.backend_url.rstrip('/')}/api/alert/analyze",
            {"alert_id": aid},
        )
        item.analyze_status = status
    except HTTPError as exc:
        raise DiagnosticFailure("ANALYZE_HTTP_FAILURE", f"{phase} analyze failed for {aid}: {_http_error_message(exc)}") from exc
    except (URLError, TimeoutError) as exc:
        raise DiagnosticFailure("ANALYZE_HTTP_FAILURE", f"{phase} analyze failed for {aid}: {exc}") from exc
    except Exception as exc:
        raise DiagnosticFailure("UNEXPECTED_RUNTIME_ERROR", f"{phase} analyze failed for {aid}: {exc}") from exc

    parsed = extract_analyze(analyze_payload)
    item.category = parsed["category"]
    item.action = parsed["action"]
    item.confidence = parsed["confidence"]
    item.decision_id = parsed["decision_id"]
    payload["latest_alert_id"] = aid
    payload["latest_action"] = item.action
    payload["latest_confidence"] = item.confidence

    if item.category != args.target_category:
        payload["other_categories"] += 1
        item.skipped_reason = f"category={item.category}"
        return item
    if item.action in args.scenario_config.skip_actions:
        payload["skipped_refer_to_analyst"] += 1
        item.skipped_reason = str(item.action)
        return item
    if item.action not in args.scenario_config.allowed_actions:
        payload["other_action_skips"] += 1
        item.skipped_reason = f"action={item.action}"
        return item
    if not item.decision_id:
        payload["other_action_skips"] += 1
        item.skipped_reason = "missing decision_id"
        return item

    try:
        payload["outcome_attempts"] += 1
        outcome_body = {
            "alert_id": aid,
            "decision_id": item.decision_id,
            "outcome": "correct",
            "analyst_action": item.action,
        }
        outcome_status, outcome_payload = http_json(
            "POST",
            f"{args.backend_url.rstrip('/')}/api/alert/outcome",
            outcome_body,
        )
        item.outcome_status = outcome_status
        item.outcome_id = nested_get(outcome_payload, ("outcome_id",), ("hash",))
        payload["valid_outcomes"] += 1
        if print_outcome_status:
            print(
                f"[SOC DIAG F] {phase} outcome POST status={outcome_status} "
                f"alert_id={aid} decision_id={item.decision_id} "
                f"valid_outcomes={payload['valid_outcomes']}",
                flush=True,
            )
        return item
    except HTTPError as exc:
        raise DiagnosticFailure("OUTCOME_HTTP_FAILURE", f"{phase} outcome failed for {aid}: {_http_error_message(exc)}") from exc
    except (URLError, TimeoutError) as exc:
        raise DiagnosticFailure("OUTCOME_HTTP_FAILURE", f"{phase} outcome failed for {aid}: {exc}") from exc
    except DiagnosticFailure:
        raise
    except Exception as exc:
        raise DiagnosticFailure("UNEXPECTED_RUNTIME_ERROR", f"{phase} outcome failed for {aid}: {exc}") from exc


async def run_diagnostic(args: argparse.Namespace, payload: dict[str, Any]) -> dict[str, Any]:
    log_progress(
        args,
        payload,
        "INITIALIZING",
        (
            "[SOC DIAG F] starting "
            f"scenario={args.scenario_config.name} graph={args.graph_name} prefix={args.prefix} "
            f"max_attempts={args.max_attempts} target_outcomes={args.target_outcomes} "
            f"mode={'bulk_seed_first' if args.bulk_seed_first else 'streaming'} "
            f"backend_url={args.backend_url}"
        ),
        phase="initializing",
    )
    payload["runner_ci_platform_import_path"] = source_ci_platform_import_path()
    payload["last_successful_phase"] = "runner_env_validated"
    validate_backend_contract(args, payload)
    payload["last_successful_phase"] = "backend_contract_validated"
    log_progress(
        args,
        payload,
        "CONTRACT_VERIFIED",
        f"[SOC DIAG F] backend contract verified for graph={args.graph_name}",
        phase="backend_contract_validated",
    )
    payload["health"] = check_health(args.backend_url)
    payload["last_successful_phase"] = "backend_health_validated"
    print(f"[SOC DIAG F] /health OK payload={payload['health']}", flush=True)

    if args.seed_strategy != "direct-age":
        raise DiagnosticFailure(
            "ENV_VALIDATION_FAILED",
            f"seed_strategy={args.seed_strategy!r} is not implemented for Diagnostic F proof yet",
        )

    client = make_age_client(args)
    try:
        await client.ensure_graph()
    except Exception as exc:
        raise DiagnosticFailure("AGE_GRAPH_READBACK_FAILED", f"ensure_graph failed: {exc}") from exc
    payload["last_successful_phase"] = "age_graph_ensured"

    if args.dry_run:
        payload["dry_run_plan"] = {
            "mode": payload["mode"],
            "max_attempts": args.max_attempts,
            "bulk_seed_batches": (args.seed_count + args.batch_size - 1) // args.batch_size,
            "first_alert_id": alert_id(args.prefix, 1),
            "last_alert_id": alert_id(args.prefix, args.max_attempts),
            "note": "dry-run only; this is not Diagnostic F proof",
            "seed_strategy": args.seed_strategy,
            "seed_sleep_seconds": args.seed_sleep_seconds,
            "attempt_sleep_seconds": args.attempt_sleep_seconds,
            "batch_sleep_seconds": args.batch_sleep_seconds,
            "preflight_seed_count": args.preflight_seed_count,
            "bulk_seed_first": args.bulk_seed_first,
        }
        log_progress(
            args,
            payload,
            "WRITING_REPORT",
            "[SOC DIAG F] dry-run complete; no seed or proof loop executed",
            phase="dry_run_complete",
        )
        return payload

    if not args.bulk_seed_first:
        log_progress(
            args,
            payload,
            "STREAMING_PROOF_RUNNING",
            (
                "[SOC DIAG F] streaming proof starting "
                f"max_attempts={args.max_attempts} target_outcomes={args.target_outcomes} "
                f"sanity_count={args.sanity_count}"
            ),
            phase="streaming_proof",
        )
        if args.scenario_config.input_provider == "fixed_c9b_seed_only":
            client, seeded_id = await seed_one_with_retries(args, payload, client, index=1)
            if seeded_id is None:
                raise DiagnosticFailure(
                    "SEED_RUNTIME_FAILURE",
                    f"seed-only smoke failed for {alert_id(args.prefix, 1)}: {payload.get('last_seed_error')}",
                )
            payload["seeded_alerts_readback"] = await read_alert_count(client, args.prefix)
            payload["readback"] = await final_readback(client, args.prefix)
            payload["last_successful_phase"] = "seed_only_completed"
            progress_snapshot(
                args,
                payload,
                "ATTEMPT_OK",
                phase="seed_only_completed",
                latest_alert_id=seeded_id,
            )
            return payload

        sanity_required = max(0, args.sanity_count)
        sanity_valid = 0
        if sanity_required:
            log_progress(
                args,
                payload,
                "SANITY_RUNNING",
                f"[SOC DIAG F] sanity streaming phase starting count={sanity_required}",
                phase="sanity",
            )

        for index in range(1, args.max_attempts + 1):
            if payload["valid_outcomes"] >= args.target_outcomes:
                break

            aid = alert_id(args.prefix, index)
            payload["current_attempt_index"] = index
            client, seeded_id = await seed_one_with_retries(args, payload, client, index=index)
            if seeded_id is None:
                message = (
                    f"seed failed for {aid}: failures={payload['seed_failures']} "
                    f"max_seed_failures={args.max_seed_failures} error={payload.get('last_seed_error')}"
                )
                log_progress(
                    args,
                    payload,
                    "ATTEMPT_OK",
                    f"[SOC DIAG F] {message}",
                    phase="streaming_seed",
                    latest_alert_id=aid,
                )
                if payload["seed_failures"] >= args.max_seed_failures:
                    raise DiagnosticFailure("SEED_RUNTIME_FAILURE", message)
                if args.attempt_sleep_seconds > 0:
                    await asyncio.sleep(args.attempt_sleep_seconds)
                continue

            before_valid = payload["valid_outcomes"]
            item = await run_analyze_outcome_pair(
                args,
                payload,
                aid,
                phase="sanity" if index <= sanity_required else "proof",
                print_outcome_status=(index <= sanity_required or payload["valid_outcomes"] == 0),
            )
            payload["loops"].append(asdict(item))
            gained_valid = payload["valid_outcomes"] > before_valid

            if index <= sanity_required:
                print(
                    (
                        f"[SOC DIAG F] sanity attempt={index} alert_id={aid} "
                        f"category={item.category} action={item.action} "
                        f"decision_id={item.decision_id} outcome_status={item.outcome_status} "
                        f"valid={gained_valid}"
                    ),
                    flush=True,
                )
                if gained_valid:
                    sanity_valid += 1
                else:
                    raise DiagnosticFailure(
                        "SEED_DATA_ISSUE",
                        f"sanity failed for {aid}: category={item.category!r} action={item.action!r} reason={item.skipped_reason!r}",
                    )
                if index == sanity_required:
                    if sanity_valid < 1:
                        raise DiagnosticFailure("SEED_DATA_ISSUE", "sanity did not produce a valid target outcome")
                    payload["last_successful_phase"] = "sanity_completed"
                    log_progress(
                        args,
                        payload,
                        "SANITY_PASSED",
                        f"[SOC DIAG F] sanity PASS valid_outcomes={payload['valid_outcomes']}",
                        phase="sanity_completed",
                        latest_alert_id=aid,
                        latest_action=item.action,
                        latest_confidence=item.confidence,
                    )

            if gained_valid and payload["valid_outcomes"] in args.scenario_config.milestones:
                rb = await progress_readback(client, args.prefix)
                payload["progress_readbacks"][str(payload["valid_outcomes"])] = rb
                payload["milestones"][str(payload["valid_outcomes"])] = {
                    "alert_id": aid,
                    "decision_id": item.decision_id,
                    "time_epoch": time.time(),
                    "readback": rb,
                }
                log_progress(
                    args,
                    payload,
                    "MILESTONE_REACHED",
                    (
                        f"[SOC DIAG F] milestone {payload['valid_outcomes']} "
                        f"attempt={index} alert_id={aid} outcome_status={item.outcome_status} "
                        f"action={item.action} confidence={item.confidence} "
                        f"readback={rb} elapsed={elapsed(payload)}s"
                    ),
                    phase="streaming_proof",
                    latest_alert_id=aid,
                    latest_action=item.action,
                    latest_confidence=item.confidence,
                    milestone=payload["valid_outcomes"],
                )
            elif gained_valid and payload["valid_outcomes"] % 25 == 0:
                rb = await progress_readback(client, args.prefix)
                payload["progress_readbacks"][str(payload["valid_outcomes"])] = rb
                log_progress(
                    args,
                    payload,
                    "OUTCOME_OK",
                    (
                        f"[SOC DIAG F] progress valid={payload['valid_outcomes']} "
                        f"attempts={payload['analyze_attempts']} current_attempt={index} latest={aid} "
                        f"outcome_status={item.outcome_status} action={item.action} "
                        f"confidence={item.confidence} skipped_referral={payload['skipped_refer_to_analyst']} "
                        f"other_categories={payload['other_categories']} other_action_skips={payload['other_action_skips']} "
                        f"seed_failures={payload['seed_failures']} readback={rb} elapsed={elapsed(payload)}s"
                    ),
                    phase="streaming_proof",
                    latest_alert_id=aid,
                    latest_action=item.action,
                    latest_confidence=item.confidence,
                )
            elif gained_valid:
                progress_snapshot(
                    args,
                    payload,
                    "OUTCOME_OK",
                    phase="streaming_proof",
                    latest_alert_id=aid,
                    latest_action=item.action,
                    latest_confidence=item.confidence,
                )
            else:
                progress_snapshot(
                    args,
                    payload,
                    "ATTEMPT_OK",
                    phase="streaming_proof",
                    latest_alert_id=aid,
                    latest_action=item.action,
                    latest_confidence=item.confidence,
                )

            if args.attempt_sleep_seconds > 0 and payload["valid_outcomes"] < args.target_outcomes:
                await asyncio.sleep(args.attempt_sleep_seconds)

        payload["last_successful_phase"] = "streaming_loop_completed"
        payload["seeded_alerts_readback"] = await read_alert_count(client, args.prefix)
        payload["readback"] = await final_readback(client, args.prefix)
        payload["last_successful_phase"] = "age_readback_completed"
        return payload

    log_progress(args, payload, "SEEDING", "[SOC DIAG F] seed phase starting", phase="seeding")
    next_index = 1
    batch_number = 0
    try:
        preflight_count = max(0, min(args.preflight_seed_count, args.seed_count))
        if preflight_count:
            batch_number += 1
            log_progress(
                args,
                payload,
                "SEEDING",
                (
                    f"[SOC DIAG F] preflight seed starting count={preflight_count} "
                    f"range={alert_id(args.prefix, 1)}..{alert_id(args.prefix, preflight_count)}"
                ),
                phase="seed_preflight",
                latest_alert_id=alert_id(args.prefix, 1),
            )
            client, _ = await seed_batch_with_retries(
                args,
                payload,
                client,
                batch_number=batch_number,
                batch_start=1,
                count=preflight_count,
            )
            payload["seeded_alerts_readback"] = await read_alert_count(client, args.prefix)
            check_health(args.backend_url)
            log_progress(
                args,
                payload,
                "SEED_BATCH_OK",
                (
                    f"[SOC DIAG F] preflight seed OK "
                    f"range={alert_id(args.prefix, 1)}..{alert_id(args.prefix, preflight_count)} "
                    f"readback={payload['seeded_alerts_readback']} elapsed={elapsed(payload)}s"
                ),
                phase="seed_preflight",
                latest_alert_id=alert_id(args.prefix, preflight_count),
            )
            next_index = preflight_count + 1
            if next_index <= args.seed_count and args.batch_sleep_seconds > 0:
                await asyncio.sleep(args.batch_sleep_seconds)

        while next_index <= args.seed_count:
            count = min(args.batch_size, args.seed_count - next_index + 1)
            batch_number += 1
            batch_start = next_index
            client, _ = await seed_batch_with_retries(
                args,
                payload,
                client,
                batch_number=batch_number,
                batch_start=batch_start,
                count=count,
            )
            next_index += count
            payload["seeded_alerts_readback"] = await read_alert_count(client, args.prefix)
            check_health(args.backend_url)
            log_progress(
                args,
                payload,
                "SEED_BATCH_OK",
                (
                    f"[SOC DIAG F] seed batch {batch_number} OK "
                    f"range={alert_id(args.prefix, batch_start)}..{alert_id(args.prefix, next_index - 1)} "
                    f"readback={payload['seeded_alerts_readback']} elapsed={elapsed(payload)}s"
                ),
                phase="seeding",
                latest_alert_id=alert_id(args.prefix, next_index - 1),
            )
            if next_index <= args.seed_count and args.batch_sleep_seconds > 0:
                await asyncio.sleep(args.batch_sleep_seconds)
        payload["last_successful_phase"] = "seed_completed"
    except DiagnosticFailure:
        raise
    except Exception as exc:
        raise DiagnosticFailure(
            "SEED_RUNTIME_FAILURE",
            (
                "seed batch failed: "
                f"batch={payload.get('current_batch_index')} "
                f"start={payload.get('current_batch_start')} "
                f"end={payload.get('current_batch_end')} "
                f"retries={payload.get('seed_retries')} "
                f"error={exc}"
            ),
        ) from exc

    if payload["seeded_alerts_readback"] < min(args.seed_count, payload["seed_completed_count"]):
        raise DiagnosticFailure(
            "SEED_DATA_ISSUE",
            f"seed readback {payload['seeded_alerts_readback']} is below completed {payload['seed_completed_count']}",
        )

    sanity_count = max(0, min(args.sanity_count, args.seed_count))
    if sanity_count:
        log_progress(
            args,
            payload,
            "SANITY_RUNNING",
            f"[SOC DIAG F] sanity phase starting count={sanity_count}",
            phase="sanity",
        )
        for index in range(1, sanity_count + 1):
            aid = alert_id(args.prefix, index)
            item = await run_analyze_outcome_pair(
                args,
                payload,
                aid,
                phase="sanity",
                print_outcome_status=True,
            )
            payload["loops"].append(asdict(item))
            if item.category != args.target_category:
                raise DiagnosticFailure(
                    "SEED_DATA_ISSUE",
                    f"sanity failed for {aid}: category={item.category!r}",
                )
            if item.action in args.scenario_config.skip_actions or item.action not in args.scenario_config.allowed_actions:
                raise DiagnosticFailure(
                    "SEED_DATA_ISSUE",
                    f"sanity failed for {aid}: action={item.action!r}",
                )
            if not item.decision_id:
                raise DiagnosticFailure("SEED_DATA_ISSUE", f"sanity failed for {aid}: missing decision_id")
            if not item.outcome_status or item.outcome_status < 200 or item.outcome_status >= 300:
                raise DiagnosticFailure(
                    "LOOP_HTTP_FAILURE",
                    f"sanity failed for {aid}: outcome_status={item.outcome_status}",
                )
        payload["last_successful_phase"] = "sanity_completed"
        log_progress(
            args,
            payload,
            "SANITY_PASSED",
            f"[SOC DIAG F] sanity PASS valid_outcomes={payload['valid_outcomes']}",
            phase="sanity_completed",
        )

    log_progress(args, payload, "PROOF_RUNNING", "[SOC DIAG F] proof loop starting", phase="proof_loop")
    for index in range(sanity_count + 1, args.seed_count + 1):
        if payload["valid_outcomes"] >= args.target_outcomes:
            break
        aid = alert_id(args.prefix, index)
        item: LoopResult | None = None
        try:
            before_valid = payload["valid_outcomes"]
            item = await run_analyze_outcome_pair(
                args,
                payload,
                aid,
                phase="proof",
                print_outcome_status=payload["valid_outcomes"] == 0,
            )
            if payload["valid_outcomes"] > before_valid and payload["valid_outcomes"] in args.scenario_config.milestones:
                rb = await progress_readback(client, args.prefix)
                payload["progress_readbacks"][str(payload["valid_outcomes"])] = rb
                payload["milestones"][str(payload["valid_outcomes"])] = {
                    "alert_id": aid,
                    "decision_id": item.decision_id,
                    "time_epoch": time.time(),
                    "readback": rb,
                }
                log_progress(
                    args,
                    payload,
                    "MILESTONE_REACHED",
                    (
                        f"[SOC DIAG F] milestone {payload['valid_outcomes']} "
                        f"alert_id={aid} outcome_status={item.outcome_status} "
                        f"action={item.action} confidence={item.confidence} "
                        f"readback={rb} elapsed={elapsed(payload)}s"
                    ),
                    phase="proof_loop",
                    latest_alert_id=aid,
                    latest_action=item.action,
                    latest_confidence=item.confidence,
                    milestone=payload["valid_outcomes"],
                )
            elif payload["valid_outcomes"] > before_valid and payload["valid_outcomes"] % 25 == 0:
                rb = await progress_readback(client, args.prefix)
                payload["progress_readbacks"][str(payload["valid_outcomes"])] = rb
                log_progress(
                    args,
                    payload,
                    "PROOF_RUNNING",
                    (
                        f"[SOC DIAG F] progress valid={payload['valid_outcomes']} "
                        f"attempts={payload['analyze_attempts']} latest={aid} "
                        f"outcome_status={item.outcome_status} action={item.action} "
                        f"confidence={item.confidence} skipped_referral={payload['skipped_refer_to_analyst']} "
                        f"other_categories={payload['other_categories']} failures={len(payload['failures'])} "
                        f"readback={rb} elapsed={elapsed(payload)}s"
                    ),
                    phase="proof_loop",
                    latest_alert_id=aid,
                    latest_action=item.action,
                    latest_confidence=item.confidence,
                )
            payload["loops"].append(asdict(item))
        except DiagnosticFailure as exc:
            if isinstance(item, LoopResult):
                payload["loops"].append(asdict(item))
            raise exc
        except Exception as exc:
            raise DiagnosticFailure("UNEXPECTED_RUNTIME_ERROR", f"loop failed for {aid}: {exc}") from exc

    payload["last_successful_phase"] = "loop_completed"
    payload["readback"] = await final_readback(client, args.prefix)
    payload["last_successful_phase"] = "age_readback_completed"
    return payload


async def main_async(args: argparse.Namespace, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        await run_diagnostic(args, payload)
    except DiagnosticFailure as exc:
        payload["exception"] = str(exc)
        add_failure(payload, exc.verdict, str(exc))
        log_progress(
            args,
            payload,
            "FAIL",
            f"[SOC DIAG F] failure verdict={exc.verdict} reason={exc}",
            phase=payload.get("last_successful_phase"),
        )
    except Exception as exc:
        payload["exception"] = f"{exc}\n{traceback.format_exc()}"
        add_failure(payload, "UNEXPECTED_RUNTIME_ERROR", str(exc))
        log_progress(
            args,
            payload,
            "FAIL",
            f"[SOC DIAG F] unexpected failure reason={exc}",
            phase=payload.get("last_successful_phase"),
        )

    verdict, exit_code, criteria_failures = classify_verdict(args, payload)
    payload["verdict"] = verdict
    payload["exit_code"] = exit_code
    payload["proof_passed"] = verdict == PASS_VERDICT
    payload["criteria_failures"] = criteria_failures
    return payload


def main() -> None:
    args = parse_args()
    payload = base_payload(args)
    try:
        result = asyncio.run(main_async(args, payload))
    except KeyboardInterrupt:
        payload["exception"] = "KeyboardInterrupt"
        add_failure(payload, "INTERRUPTED", "KeyboardInterrupt")
        payload["verdict"] = "INTERRUPTED"
        payload["exit_code"] = 1
        payload["criteria_failures"] = ["interrupted by user"]
        result = payload
    except Exception as exc:
        payload["exception"] = f"{exc}\n{traceback.format_exc()}"
        add_failure(payload, "UNEXPECTED_RUNTIME_ERROR", str(exc))
        payload["verdict"] = "UNEXPECTED_RUNTIME_ERROR"
        payload["exit_code"] = 1
        payload["criteria_failures"] = [str(exc)]
        result = payload
    log_progress(
        args,
        result,
        "WRITING_REPORT",
        f"[SOC DIAG F] writing reports verdict={result.get('verdict')} exit_code={result.get('exit_code')}",
        phase="writing_report",
        verdict=result.get("verdict"),
    )
    json_path, md_path = write_reports(args, result)
    final_status = "PASS" if result.get("verdict") == PASS_VERDICT else "FAIL"
    if result.get("verdict") == "INTERRUPTED":
        final_status = "INTERRUPTED"
    progress_snapshot(
        args,
        result,
        final_status,
        phase="final",
        verdict=result.get("verdict"),
        report_json_path=json_path,
        report_md_path=md_path,
    )
    print(
        "\n".join(
            [
                "[SOC DIAG F] final verdict",
                f"  verdict={result.get('verdict')}",
                f"  exit_code={result.get('exit_code')}",
                f"  json_report={json_path}",
                f"  md_report={md_path}",
                f"  proof_passed={result.get('verdict') == PASS_VERDICT}",
            ]
        ),
        flush=True,
    )
    print(json.dumps({"result": result, "json_report": str(json_path), "md_report": str(md_path)}, indent=2, default=str), flush=True)
    sys.exit(int(result.get("exit_code") or 0))


if __name__ == "__main__":
    main()

