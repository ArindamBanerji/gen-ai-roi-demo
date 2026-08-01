from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACT_PATH = REPO_ROOT / "scratch" / "temp" / "soc_diag_backend_contract.json"
DEFAULT_GRAPH_DSN = "host=localhost port=5433 dbname=soc_copilot user=postgres password=postgres"
DEFAULT_BACKEND_URL = "http://127.0.0.1:{port}"

PHASE_FALSE = "false_baseline"
PHASE_TRUE = "true_compare"
PHASE_PROOF = "proof_250"
PHASES = (PHASE_FALSE, PHASE_TRUE, PHASE_PROOF)

COMPARABLE_FIELDS = (
    "recommendation.action",
    "recommendation.confidence",
    "recommendation.routing_zone",
    "gae_scoring.factor_vector",
    "gae_scoring.factor_names",
    "gae_scoring.action_probabilities",
    "gae_scoring.routing_zone",
    "gae_scoring.softmax_sum",
    "gae_scoring.temperature",
    "gae_scoring.low_confidence",
    "gae_scoring.ambiguous",
    "referral",
    "referral_debug",
    "composite_gate",
    "decision_metadata",
)

EXCLUDED_FIELDS = (
    "decision IDs",
    "timestamps",
    "elapsed timings",
    "generated UUIDs",
    "narrative/rationale text",
)

SHADOW_SIDE_EFFECT_KEYS = (
    "decision_writes",
    "outcome_writes",
    "proof_writes",
    "counter_updates",
    "graph_mutations",
)

PERFORMANCE_LEDGER = {
    "P2E baseline": "avg analyze 0.193s at 250 outcomes, warm_fallback",
    "P3G-D clean proof": "avg analyze 0.202s, max 0.571s, avg outcome 0.440s; hits=0, misses=250, loads=250",
    "P3H benchmark conclusion": "EntityCache correct but current route wiring is not a reliable performance win",
    "buyer_facing_claim_allowed": False,
}


class RouteValidationError(RuntimeError):
    pass


@dataclass(frozen=True)
class PhaseConfig:
    name: str
    graph: str
    env: Mapping[str, str]


@dataclass(frozen=True)
class RunnerConfig:
    port: int
    prefix: str
    count: int
    phases: tuple[str, ...]
    compare_profile: str
    workloads: tuple[str, ...]
    repeat_count: int
    false_graph: str | None
    true_graph: str | None
    proof_graph: str | None
    false_env: Mapping[str, str]
    true_env: Mapping[str, str]
    proof_env: Mapping[str, str]
    out_dir: Path
    graph_dsn: str
    run_250: bool
    strict_contract: bool
    contract_path: Path
    readiness_timeout_seconds: float


def parse_env_assignments(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    result: dict[str, str] = {}
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        if "=" not in item:
            raise ValueError(f"invalid env assignment {item!r}; expected KEY=VALUE")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError("env assignment has empty key")
        result[key] = value.strip()
    return result


def resolve_phases(phase: str, *, run_250: bool) -> tuple[str, ...]:
    if phase == "all":
        phases = [PHASE_FALSE, PHASE_TRUE]
        if run_250:
            phases.append(PHASE_PROOF)
        return tuple(phases)
    if phase not in PHASES:
        raise ValueError(f"unsupported phase {phase!r}")
    if phase == PHASE_PROOF and not run_250:
        return (PHASE_PROOF,)
    return (phase,)


def phase_plan(config: RunnerConfig) -> list[PhaseConfig]:
    plan: list[PhaseConfig] = []
    for phase in config.phases:
        if phase == PHASE_FALSE:
            if not config.false_graph:
                raise ValueError("--false-graph is required for false_baseline")
            plan.append(PhaseConfig(phase, config.false_graph, dict(config.false_env)))
        elif phase == PHASE_TRUE:
            if not config.true_graph:
                raise ValueError("--true-graph is required for true_compare")
            plan.append(PhaseConfig(phase, config.true_graph, dict(config.true_env)))
        elif phase == PHASE_PROOF:
            if not config.proof_graph:
                raise ValueError("--proof-graph is required for proof_250")
            plan.append(PhaseConfig(phase, config.proof_graph, dict(config.proof_env)))
        else:
            raise ValueError(f"unsupported phase {phase!r}")
    return plan


def deterministic_alert_ids(prefix: str, count: int) -> list[str]:
    return [f"{prefix}-{index:04d}" for index in range(1, count + 1)]


def build_workloads(alert_ids: Sequence[str], *, selected: Iterable[str], repeat_count: int) -> dict[str, list[str]]:
    if not alert_ids:
        raise ValueError("at least one alert id is required")
    selected_set = {item.strip() for item in selected if item.strip()}
    supported = {"unique_once", "repeat_same", "mixed_reuse"}
    unknown = selected_set - supported
    if unknown:
        raise ValueError(f"unsupported workloads: {sorted(unknown)}")
    workloads: dict[str, list[str]] = {}
    if "unique_once" in selected_set:
        workloads["unique_once"] = list(alert_ids)
    if "repeat_same" in selected_set:
        workloads["repeat_same"] = [alert_ids[0]] * repeat_count
    if "mixed_reuse" in selected_set:
        if len(alert_ids) < 5:
            raise ValueError("mixed_reuse requires at least five alert ids")
        workloads["mixed_reuse"] = [
            alert_ids[0],
            alert_ids[1],
            alert_ids[0],
            alert_ids[2],
            alert_ids[0],
            alert_ids[3],
            alert_ids[4],
            alert_ids[0],
        ]
    return workloads


def latency_stats(latencies: Sequence[float], *, request_count: int | None = None) -> dict[str, Any]:
    count = len(latencies)
    expected = request_count if request_count is not None else count
    if count == 0:
        return {
            "request_count": expected,
            "success_count": 0,
            "failure_count": expected,
            "avg_seconds": None,
            "median_seconds": None,
            "p95_seconds": None,
            "max_seconds": None,
            "latencies_seconds": [],
        }
    ordered = sorted(latencies)
    p95_index = max(0, math.ceil(0.95 * count) - 1)
    median = (
        ordered[count // 2]
        if count % 2
        else (ordered[count // 2 - 1] + ordered[count // 2]) / 2
    )
    return {
        "request_count": expected,
        "success_count": count,
        "failure_count": expected - count,
        "avg_seconds": sum(latencies) / count,
        "median_seconds": median,
        "p95_seconds": ordered[p95_index],
        "max_seconds": max(latencies),
        "latencies_seconds": list(latencies),
    }


def get_path(payload: Mapping[str, Any], dotted_path: str) -> Any:
    current: Any = payload
    for part in dotted_path.split("."):
        if isinstance(current, Mapping) and part in current:
            current = current[part]
        else:
            return None
    return current


def project_comparable_fields(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {field: get_path(payload, field) for field in COMPARABLE_FIELDS}


def compare_projected_outputs(
    false_by_id: Mapping[str, Mapping[str, Any]],
    true_by_id: Mapping[str, Mapping[str, Any]],
    alert_ids: Sequence[str],
) -> dict[str, Any]:
    differences: list[dict[str, Any]] = []
    field_status: dict[str, str] = {}
    for field in COMPARABLE_FIELDS:
        present_any = False
        failed = False
        for alert_id in alert_ids:
            false_value = false_by_id.get(alert_id, {}).get(field)
            true_value = true_by_id.get(alert_id, {}).get(field)
            if false_value is not None or true_value is not None:
                present_any = True
            if false_value != true_value:
                failed = True
                differences.append(
                    {
                        "alert_id": alert_id,
                        "field": field,
                        "false": false_value,
                        "true": true_value,
                    }
                )
        field_status[field] = "FAIL" if failed else ("PASS" if present_any else "NOT_PRESENT")
    return {
        "matched": not differences,
        "field_status": field_status,
        "differences": differences,
        "excluded_fields": list(EXCLUDED_FIELDS),
    }


def first_capture_by_alert(phase_artifact: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for workload in phase_artifact.get("workloads", {}).values():
        if not isinstance(workload, Mapping):
            continue
        for capture in workload.get("captures", []):
            if isinstance(capture, Mapping) and capture.get("alert_id") not in result:
                result[str(capture.get("alert_id"))] = capture.get("comparable", {})
    return result


def compare_latency(false_artifact: Mapping[str, Any], true_artifact: Mapping[str, Any]) -> dict[str, Any]:
    comparison: dict[str, Any] = {}
    for workload, true_payload in true_artifact.get("workloads", {}).items():
        true_summary = true_payload.get("summary", {})
        false_summary = (
            false_artifact.get("workloads", {})
            .get(workload, {})
            .get("summary", {})
        )
        false_avg = false_summary.get("avg_seconds")
        true_avg = true_summary.get("avg_seconds")
        delta = None
        delta_percent = None
        if isinstance(false_avg, (int, float)) and isinstance(true_avg, (int, float)):
            delta = true_avg - false_avg
            delta_percent = (delta / false_avg * 100.0) if false_avg else None
        comparison[workload] = {
            "false_avg_seconds": false_avg,
            "true_avg_seconds": true_avg,
            "delta_seconds": delta,
            "delta_percent": delta_percent,
            "shadow_overhead": bool(delta is not None and delta > 0),
        }
    return comparison


def validate_shadow_profile(captures: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    diagnostics = [capture.get("diagnostics", {}).get("soc_decision_pipeline_shadow") for capture in captures]
    present = bool(diagnostics) and all(isinstance(item, Mapping) for item in diagnostics)
    matched = all(item.get("matched") is True for item in diagnostics if isinstance(item, Mapping))
    differences_empty = all(item.get("differences") == [] for item in diagnostics if isinstance(item, Mapping))
    shadow_failed = any(item.get("status") == "shadow_failed" for item in diagnostics if isinstance(item, Mapping))
    side_effects = {
        key: all(
            isinstance(item, Mapping)
            and isinstance(item.get("side_effects"), Mapping)
            and item["side_effects"].get(key) == 0
            for item in diagnostics
        )
        for key in SHADOW_SIDE_EFFECT_KEYS
    }
    return {
        "profile": "shadow",
        "passed": present and matched and differences_empty and not shadow_failed and all(side_effects.values()),
        "diagnostics_present": present,
        "matched_true": matched,
        "differences_empty": differences_empty,
        "shadow_failed": shadow_failed,
        "side_effect_zero": side_effects,
    }


def validate_entity_cache_profile(health: Mapping[str, Any], *, expect_enabled: bool) -> dict[str, Any]:
    entity_cache = (
        health.get("components", {}).get("entity_cache", {})
        if isinstance(health.get("components"), Mapping)
        else {}
    )
    required = ("enabled", "hits", "misses", "loads", "size", "max_size")
    visible = all(key in entity_cache for key in required)
    enabled_matches = entity_cache.get("enabled") is expect_enabled if visible else False
    sensitive_terms = ("user_id", "asset_id", "alert_id", "security_context", "nodes")
    serialized = json.dumps(entity_cache, sort_keys=True)
    sensitive_exposed = any(term in serialized for term in sensitive_terms)
    return {
        "profile": "entity_cache",
        "passed": visible and enabled_matches and not sensitive_exposed,
        "visible": visible,
        "enabled_matches": enabled_matches,
        "sensitive_values_exposed": sensitive_exposed,
        "diagnostics": entity_cache,
    }


def validate_generic_profile() -> dict[str, Any]:
    return {"profile": "generic", "passed": True}


def profile_failed_checks(profile_result: Mapping[str, Any] | None, *, prefix: str = "") -> list[str]:
    if not profile_result:
        return []
    if profile_result.get("passed") is True:
        return []
    label = f"{prefix}." if prefix else ""
    failed: list[str] = []
    for key, value in profile_result.items():
        if key in {"profile", "diagnostics"}:
            continue
        if value is False:
            failed.append(f"{label}{key}")
        elif isinstance(value, Mapping):
            for child_key, child_value in value.items():
                if child_value is False:
                    failed.append(f"{label}{key}.{child_key}")
    if not failed:
        failed.append(f"{label}profile_failed")
    return failed


def phase_failed_checks(artifact: Mapping[str, Any]) -> list[str]:
    failed: list[str] = []
    if artifact.get("status") in {"FAIL", "BLOCKED"}:
        failed.extend(str(item) for item in artifact.get("failed_checks", []) if item)
        if not failed:
            failed.append("phase.status")
    if artifact.get("contract", {}).get("verified") is False:
        failed.append("contract.verified")
    if artifact.get("queue", {}).get("queue_visible") is False:
        failed.append("queue.queue_visible")
    phase_profile = artifact.get("profile_validation")
    failed.extend(profile_failed_checks(phase_profile, prefix="profile_validation"))
    for workload_name, workload in artifact.get("workloads", {}).items():
        if not isinstance(workload, Mapping):
            continue
        if workload.get("failures"):
            failed.append(f"workloads.{workload_name}.failures")
        failed.extend(
            profile_failed_checks(
                workload.get("profile_validation"),
                prefix=f"workloads.{workload_name}.profile_validation",
            )
        )
    return failed


def validate_contract(
    contract: Mapping[str, Any],
    *,
    expected_graph: str,
    expected_port: int,
    expected_env: Mapping[str, str],
    phase_started_at: float | None = None,
    contract_path: Path | None = None,
    strict: bool = True,
) -> dict[str, Any]:
    errors: list[str] = []
    if contract.get("launcher") != "copilot-sdk/demo.py --diag-mode":
        errors.append("launcher mismatch")
    if contract.get("graph_name") != expected_graph:
        errors.append("graph mismatch")
    try:
        port_value = int(contract.get("backend_port"))
    except (TypeError, ValueError):
        port_value = None
    if port_value != expected_port:
        errors.append("port mismatch")
    if not contract.get("connection_mode"):
        errors.append("connection_mode missing")
    if "USE_ENTITY_CACHE" in expected_env and "use_entity_cache" in contract:
        if str(contract.get("use_entity_cache")).lower() != expected_env["USE_ENTITY_CACHE"].lower():
            errors.append("use_entity_cache mismatch")
    elif strict and "USE_ENTITY_CACHE" in expected_env:
        errors.append("use_entity_cache missing")
    if "AGE_USE_POOL" in expected_env:
        expected_pool = expected_env["AGE_USE_POOL"].lower()
        if "age_use_pool_requested" not in contract:
            errors.append("age_use_pool_requested missing")
        elif str(contract["age_use_pool_requested"]).lower() != expected_pool:
            errors.append("age_use_pool_requested mismatch")
        if "age_use_pool" not in contract:
            errors.append("age_use_pool missing")
        elif str(contract["age_use_pool"]).lower() != expected_pool:
            errors.append("age_use_pool mismatch")
    if "USE_SOC_DECISION_PIPELINE_SHADOW" in expected_env and "use_soc_decision_pipeline_shadow" in contract:
        if (
            str(contract.get("use_soc_decision_pipeline_shadow")).lower()
            != expected_env["USE_SOC_DECISION_PIPELINE_SHADOW"].lower()
        ):
            errors.append("use_soc_decision_pipeline_shadow mismatch")
    if phase_started_at is not None and contract_path is not None and contract_path.exists():
        # Allow a small filesystem/clock granularity margin while rejecting obvious stale contracts.
        if contract_path.stat().st_mtime < phase_started_at - 2.0:
            errors.append("contract file timestamp predates phase start")
    launched_at = contract.get("launched_at")
    if phase_started_at is not None and isinstance(launched_at, str):
        try:
            launched = datetime.strptime(launched_at, "%Y-%m-%dT%H:%M:%S%z")
            phase_started = datetime.fromtimestamp(phase_started_at, tz=timezone.utc)
            if launched < phase_started.astimezone(launched.tzinfo) and (
                phase_started.astimezone(launched.tzinfo) - launched
            ).total_seconds() > 2.0:
                errors.append("contract launched_at predates phase start")
        except ValueError:
            if strict:
                errors.append("launched_at malformed")
    return {
        "verified": not errors,
        "errors": errors,
        "launcher": contract.get("launcher"),
        "graph": contract.get("graph_name"),
        "port": contract.get("backend_port"),
        "connection_mode": contract.get("connection_mode"),
        "path": str(contract_path) if contract_path else None,
    }


def parse_proof_summary_text(text: str) -> dict[str, Any]:
    keys = (
        "valid_outcomes",
        "l5_dk_weight",
        "dk_welford_rows",
        "max_n_decisions_used",
        "avg_analyze_seconds",
        "max_analyze_seconds",
        "avg_outcome_seconds",
        "graph_truth_proof_authority_preserved",
    )
    parsed: dict[str, Any] = {}
    for key in keys:
        match = re.search(rf"{re.escape(key)}:\s*`?([^`\r\n]+)`?", text)
        if not match:
            continue
        raw_value = match.group(1).strip()
        if key in {"valid_outcomes", "l5_dk_weight", "dk_welford_rows", "max_n_decisions_used"}:
            try:
                parsed[key] = int(raw_value)
            except ValueError:
                parsed[key] = raw_value
        elif key == "graph_truth_proof_authority_preserved":
            parsed[key] = raw_value.strip().lower() in {"yes", "true", "1"}
        else:
            try:
                parsed[key] = float(raw_value)
            except ValueError:
                parsed[key] = raw_value
    return parsed


def validate_proof_output(stdout: str, *, returncode: int) -> dict[str, Any]:
    summary = parse_proof_summary_text(stdout)
    errors: list[str] = []
    if returncode != 0:
        errors.append(f"proof runner exited {returncode}")
    if "EXTERNAL_DIAGNOSTIC_F_PASS" not in stdout:
        errors.append("EXTERNAL_DIAGNOSTIC_F_PASS missing")
    expected = {
        "valid_outcomes": 250,
        "l5_dk_weight": 1,
        "dk_welford_rows": 1,
        "max_n_decisions_used": 250,
    }
    for key, value in expected.items():
        if key not in summary:
            errors.append(f"{key} missing")
        elif summary[key] != value:
            errors.append(f"{key} expected {value} got {summary[key]}")
    graph_truth = summary.get("graph_truth_proof_authority_preserved")
    if graph_truth is not None and graph_truth is not True:
        errors.append(f"graph_truth_proof_authority_preserved expected true got {graph_truth}")
    return {
        "passed": not errors,
        "errors": errors,
        "summary": summary,
        "expected": {
            "verdict": "EXTERNAL_DIAGNOSTIC_F_PASS",
            "valid_outcomes": 250,
            "l5_dk_weight": 1,
            "dk_welford_rows": 1,
            "max_n_decisions_used": 250,
            "graph_truth_proof_authority_preserved": True,
        },
    }


def clear_contract_path(path: Path) -> dict[str, Any]:
    existed = path.exists()
    if existed:
        path.unlink()
    return {"path": str(path), "existed": existed, "cleared": True}


def http_json(method: str, url: str, payload: Mapping[str, Any] | None = None, *, timeout: float = 60.0) -> Any:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else None


def check_health(backend_url: str) -> Mapping[str, Any]:
    payload = http_json("GET", f"{backend_url.rstrip('/')}/health", timeout=10)
    if not isinstance(payload, Mapping):
        raise RouteValidationError("/health returned non-object payload")
    return payload


def wait_for_health(backend_url: str, *, timeout_seconds: float) -> Mapping[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            return check_health(backend_url)
        except (RouteValidationError, urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            time.sleep(0.5)
    raise RouteValidationError(f"backend health not ready within {timeout_seconds}s: {last_error}")


def wait_for_contract_file(
    path: Path,
    *,
    phase: str,
    graph: str,
    port: int,
    timeout_seconds: float,
    poll_interval_seconds: float = 0.5,
) -> Path:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if path.exists():
            return path
        time.sleep(poll_interval_seconds)
    raise RouteValidationError(
        "backend contract missing after readiness wait "
        f"(phase={phase}, graph={graph}, port={port}, path={path}, timeout_seconds={timeout_seconds})"
    )


def load_contract_json(path: Path) -> Mapping[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RouteValidationError(f"backend contract malformed JSON: {path}: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise RouteValidationError(f"backend contract is not a JSON object: {path}")
    return payload


def await_backend_readiness(
    phase: PhaseConfig,
    config: RunnerConfig,
    *,
    backend_url: str,
    phase_started_at: float,
) -> tuple[Mapping[str, Any], Mapping[str, Any], dict[str, Any]]:
    health = wait_for_health(backend_url, timeout_seconds=config.readiness_timeout_seconds)
    wait_for_contract_file(
        config.contract_path,
        phase=phase.name,
        graph=phase.graph,
        port=config.port,
        timeout_seconds=config.readiness_timeout_seconds,
    )
    contract = load_contract_json(config.contract_path)
    contract_status = validate_contract(
        contract,
        expected_graph=phase.graph,
        expected_port=config.port,
        expected_env=phase.env,
        phase_started_at=phase_started_at,
        contract_path=config.contract_path,
        strict=config.strict_contract,
    )
    if config.strict_contract and not contract_status["verified"]:
        raise RouteValidationError(f"strict contract failed: {contract_status['errors']}")
    return health, contract, contract_status


def stop_stale_backend(port: int) -> None:
    if os.name != "nt":
        return
    script = (
        f"$ids = Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue "
        "| Select-Object -ExpandProperty OwningProcess -Unique; "
        "foreach ($id in $ids) { if ($id) { Stop-Process -Id $id -Force -ErrorAction SilentlyContinue } }"
    )
    completed = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RouteValidationError(
            f"failed to clear stale backend on port {port}: {completed.stderr.strip() or completed.stdout.strip()}"
        )


def start_backend(phase: PhaseConfig, config: RunnerConfig) -> subprocess.Popen[Any]:
    env = os.environ.copy()
    env.update(phase.env)
    script = REPO_ROOT / "scripts" / "diagnostics" / "run_soc_diag_backend.ps1"
    command = [
        "powershell",
        "-NoProfile",
        "-File",
        str(script),
        "-GraphName",
        phase.graph,
        "-Port",
        str(config.port),
    ]
    if phase.env.get("AGE_USE_POOL", "").lower() == "true":
        command.append("-AgeUsePool")
    return subprocess.Popen(command, cwd=REPO_ROOT, env=env)


def stop_backend(process: subprocess.Popen[Any] | None) -> None:
    if process and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired as exc:
                raise RouteValidationError("backend process did not stop after terminate/kill") from exc


def write_failure_artifact(
    phase: PhaseConfig,
    config: RunnerConfig,
    *,
    started_at: float,
    error: Exception,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    artifact: dict[str, Any] = {
        "phase": phase.name,
        "status": "FAIL",
        "graph": phase.graph,
        "env": dict(phase.env),
        "prefix": config.prefix,
        "count": config.count,
        "started_at": datetime.fromtimestamp(started_at, tz=timezone.utc).isoformat(),
        "contract_path": str(config.contract_path),
        "error_type": type(error).__name__,
        "error": str(error),
        "failed_checks": [f"{phase.name}.failed"],
        "performance_ledger": PERFORMANCE_LEDGER,
    }
    if extra:
        artifact.update(extra)
    write_json(config.out_dir / artifact_name(phase.name), artifact)
    return artifact


def seed_alerts(prefix: str, count: int, graph: str, graph_dsn: str) -> Mapping[str, Any]:
    command = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "soc_c9b_seed_alerts.py"),
        "--count",
        str(count),
        "--prefix",
        prefix,
        "--graph-name",
        graph,
        "--database-url",
        graph_dsn,
        "--json",
    ]
    completed = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    return json.loads(completed.stdout)


def verify_queue(backend_url: str, alert_ids: Sequence[str]) -> dict[str, Any]:
    queue = http_json("GET", f"{backend_url.rstrip('/')}/api/alerts/queue", timeout=30)
    serialized = json.dumps(queue)
    missing = [alert_id for alert_id in alert_ids if alert_id not in serialized]
    return {"queue_visible": not missing, "missing_ids": missing}


def capture_workloads(
    backend_url: str,
    workloads: Mapping[str, Sequence[str]],
    *,
    compare_profile: str,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for workload, alert_ids in workloads.items():
        latencies: list[float] = []
        captures: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []
        for index, alert_id in enumerate(alert_ids):
            started = time.perf_counter()
            try:
                response = http_json(
                    "POST",
                    f"{backend_url.rstrip('/')}/api/alert/analyze",
                    {"alert_id": alert_id},
                    timeout=90,
                )
                elapsed = time.perf_counter() - started
                latencies.append(elapsed)
                diagnostics = response.get("_diagnostics", {}) if isinstance(response, Mapping) else {}
                captures.append(
                    {
                        "alert_id": alert_id,
                        "request_index": index,
                        "latency_seconds": elapsed,
                        "comparable": project_comparable_fields(response),
                        "diagnostics": diagnostics,
                    }
                )
            except Exception as exc:
                failures.append(
                    {
                        "alert_id": alert_id,
                        "request_index": index,
                        "error_type": type(exc).__name__,
                        "error": str(exc)[:200],
                    }
                )
        profile_result = validate_generic_profile()
        if compare_profile == "shadow":
            profile_result = validate_shadow_profile(captures)
        result[workload] = {
            "summary": latency_stats(latencies, request_count=len(alert_ids)),
            "captures": captures,
            "failures": failures,
            "profile_validation": profile_result,
        }
    return result


def artifact_name(phase: str) -> str:
    if phase == PHASE_FALSE:
        return "route_validation_false_baseline.json"
    if phase == PHASE_TRUE:
        return "route_validation_true_compare.json"
    if phase == PHASE_PROOF:
        return "route_validation_250_summary.json"
    raise ValueError(f"unsupported phase {phase!r}")


def run_route_phase(phase: PhaseConfig, config: RunnerConfig) -> dict[str, Any]:
    backend_url = DEFAULT_BACKEND_URL.format(port=config.port)
    alert_ids = deterministic_alert_ids(config.prefix, config.count)
    workloads = build_workloads(alert_ids, selected=config.workloads, repeat_count=config.repeat_count)
    process: subprocess.Popen[Any] | None = None
    started_at = time.time()
    try:
        stop_stale_backend(config.port)
        clear_contract_path(config.contract_path)
        started_at = time.time()
        process = start_backend(phase, config)
        health, _contract, contract_status = await_backend_readiness(
            phase,
            config,
            backend_url=backend_url,
            phase_started_at=started_at,
        )
        seed = seed_alerts(config.prefix, config.count, phase.graph, config.graph_dsn)
        queue = verify_queue(backend_url, alert_ids)
        if not queue["queue_visible"]:
            raise RouteValidationError(f"seeded alerts not queue-visible: {queue['missing_ids']}")
        workload_compare_profile = config.compare_profile
        if (
            config.compare_profile == "shadow"
            and phase.env.get("USE_SOC_DECISION_PIPELINE_SHADOW", "false").lower() != "true"
        ):
            workload_compare_profile = "generic"
        captured = capture_workloads(backend_url, workloads, compare_profile=workload_compare_profile)
        health_after = check_health(backend_url)
        profile_result = (
            validate_entity_cache_profile(
                health_after,
                expect_enabled=phase.env.get("USE_ENTITY_CACHE", "false").lower() == "true",
            )
            if config.compare_profile == "entity_cache"
            else None
        )
        artifact = {
            "phase": phase.name,
            "status": "PASS",
            "graph": phase.graph,
            "env": dict(phase.env),
            "prefix": config.prefix,
            "count": config.count,
            "started_at": datetime.fromtimestamp(started_at, tz=timezone.utc).isoformat(),
            "contract_path": str(config.contract_path),
            "health": health,
            "health_after": health_after,
            "contract": contract_status,
            "seed": seed,
            "queue": queue,
            "alert_ids": alert_ids,
            "workloads": captured,
            "profile_validation": profile_result,
            "comparable_fields": list(COMPARABLE_FIELDS),
            "excluded_fields": list(EXCLUDED_FIELDS),
            "performance_ledger": PERFORMANCE_LEDGER,
        }
        failed_checks = phase_failed_checks(artifact)
        artifact["failed_checks"] = failed_checks
        artifact["status"] = "FAIL" if failed_checks else "PASS"
        write_json(config.out_dir / artifact_name(phase.name), artifact)
        return artifact
    except Exception as exc:
        return write_failure_artifact(phase, config, started_at=started_at, error=exc)
    finally:
        stop_backend(process)


def run_proof_phase(phase: PhaseConfig, config: RunnerConfig) -> dict[str, Any]:
    backend_url = DEFAULT_BACKEND_URL.format(port=config.port)
    process: subprocess.Popen[Any] | None = None
    started_at = time.time()
    try:
        stop_stale_backend(config.port)
        clear_contract_path(config.contract_path)
        started_at = time.time()
        process = start_backend(phase, config)
        _health, _contract, contract_status = await_backend_readiness(
            phase,
            config,
            backend_url=backend_url,
            phase_started_at=started_at,
        )
        command = [
            sys.executable,
            str(REPO_ROOT / "scripts" / "diagnostics" / "run_soc_diag_f.py"),
            "--scenario",
            "diagnostic-f-dk",
            "--graph-name",
            phase.graph,
            "--backend-url",
            backend_url,
            "--prefix",
            f"{config.prefix}250",
            "--target-outcomes",
            "250",
            "--max-attempts",
            "300",
            "--backend-contract",
            str(config.contract_path),
            "--expect-age-pool",
        ]
        env = os.environ.copy()
        env.update(phase.env)
        completed = subprocess.run(command, cwd=REPO_ROOT, env=env, capture_output=True, text=True, check=False)
        proof_validation = validate_proof_output(completed.stdout, returncode=completed.returncode)
        proof = {
            "phase": phase.name,
            "status": "PASS" if proof_validation["passed"] else "FAIL",
            "graph": phase.graph,
            "env": dict(phase.env),
            "prefix": config.prefix,
            "count": config.count,
            "started_at": datetime.fromtimestamp(started_at, tz=timezone.utc).isoformat(),
            "contract_path": str(config.contract_path),
            "returncode": completed.returncode,
            "contract": contract_status,
            "stdout_tail": completed.stdout[-4000:],
            "stderr_tail": completed.stderr[-4000:],
            "proof_validation": proof_validation,
            "failed_checks": list(proof_validation["errors"]),
            "performance_ledger": PERFORMANCE_LEDGER,
        }
        write_json(config.out_dir / artifact_name(phase.name), proof)
        return proof
    except Exception as exc:
        return write_failure_artifact(phase, config, started_at=started_at, error=exc)
    finally:
        stop_backend(process)


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def build_comparison(false_artifact: Mapping[str, Any], true_artifact: Mapping[str, Any]) -> dict[str, Any]:
    alert_ids = list(false_artifact.get("alert_ids") or true_artifact.get("alert_ids") or [])
    parity = compare_projected_outputs(
        first_capture_by_alert(false_artifact),
        first_capture_by_alert(true_artifact),
        alert_ids,
    )
    false_failed = phase_failed_checks(false_artifact)
    true_failed = phase_failed_checks(true_artifact)
    failed_checks: list[str] = []
    if false_artifact.get("prefix") and true_artifact.get("prefix") and false_artifact.get("prefix") != true_artifact.get("prefix"):
        failed_checks.append("artifact.prefix_mismatch")
    if false_artifact.get("count") and true_artifact.get("count") and false_artifact.get("count") != true_artifact.get("count"):
        failed_checks.append("artifact.count_mismatch")
    if not parity["matched"]:
        failed_checks.extend(f"parity.{item['alert_id']}.{item['field']}" for item in parity["differences"])
    failed_checks.extend(f"false_baseline.{item}" for item in false_failed)
    failed_checks.extend(f"true_compare.{item}" for item in true_failed)
    passed = not failed_checks
    return {
        "status": "PASS" if passed else "FAIL",
        "pass": passed,
        "failed_checks": failed_checks,
        "phase_status": {
            "false_baseline": "FAIL" if false_failed else false_artifact.get("status", "UNKNOWN"),
            "true_compare": "FAIL" if true_failed or not parity["matched"] else true_artifact.get("status", "UNKNOWN"),
        },
        "profile_status": {
            "false_baseline": collect_profile_summary(false_artifact),
            "true_compare": collect_profile_summary(true_artifact),
        },
        "final_summary_status_contribution": "PASS" if passed else "FAIL",
        "false_graph": false_artifact.get("graph"),
        "true_graph": true_artifact.get("graph"),
        "input_ids_compared": alert_ids,
        "parity": parity,
        "latency": compare_latency(false_artifact, true_artifact),
        "diagnostics_summary": {
            "false_profile": collect_profile_summary(false_artifact),
            "true_profile": collect_profile_summary(true_artifact),
        },
        "performance_ledger": PERFORMANCE_LEDGER,
        "route_latency_claim": False,
        "buyer_facing_claim_allowed": False,
    }


def collect_profile_summary(artifact: Mapping[str, Any]) -> dict[str, Any]:
    summaries: dict[str, Any] = {}
    for workload, payload in artifact.get("workloads", {}).items():
        if isinstance(payload, Mapping):
            summaries[workload] = payload.get("profile_validation")
    return summaries


def build_final_summary(results: Mapping[str, Any]) -> dict[str, Any]:
    comparison = results.get("comparison", {})
    proof = results.get(PHASE_PROOF, {})
    return {
        "status": "PASS"
        if all(payload.get("status") == "PASS" for payload in results.values() if isinstance(payload, Mapping))
        else "FAIL",
        "phases_run": [key for key in (PHASE_FALSE, PHASE_TRUE, PHASE_PROOF) if key in results],
        "graphs": {
            key: value.get("graph")
            for key, value in results.items()
            if isinstance(value, Mapping) and value.get("graph")
        },
        "contract_status": {
            key: value.get("contract", {}).get("verified")
            for key, value in results.items()
            if isinstance(value, Mapping) and "contract" in value
        },
        "parity_status": comparison.get("status"),
        "diagnostics_status": comparison.get("diagnostics_summary"),
        "proof_status": proof.get("status"),
        "performance_ledger": PERFORMANCE_LEDGER,
        "buyer_facing_claim_allowed": False,
    }


def blocked_phase_artifact(
    phase: PhaseConfig,
    config: RunnerConfig,
    *,
    reason: str,
) -> dict[str, Any]:
    artifact = {
        "phase": phase.name,
        "status": "BLOCKED",
        "graph": phase.graph,
        "env": dict(phase.env),
        "prefix": config.prefix,
        "count": config.count,
        "started_at": datetime.now(tz=timezone.utc).isoformat(),
        "contract_path": str(config.contract_path),
        "blocked_reason": reason,
        "failed_checks": [reason],
        "performance_ledger": PERFORMANCE_LEDGER,
    }
    write_json(config.out_dir / artifact_name(phase.name), artifact)
    return artifact


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run configurable SOC route architecture validation phases.")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--prefix", default="P5DSHADOW")
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--phase", choices=("false_baseline", "true_compare", "proof_250", "all"), default="all")
    parser.add_argument("--false-graph")
    parser.add_argument("--true-graph")
    parser.add_argument("--proof-graph")
    parser.add_argument("--false-env", default="")
    parser.add_argument("--true-env", default="")
    parser.add_argument("--proof-env", default="")
    parser.add_argument("--compare-profile", choices=("shadow", "entity_cache", "generic"), default="generic")
    parser.add_argument("--workloads", default="unique_once,repeat_same,mixed_reuse")
    parser.add_argument("--repeat-count", type=int, default=5)
    parser.add_argument("--run-250", action="store_true")
    parser.add_argument("--strict-contract", action="store_true", default=True)
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "scratch" / "temp")
    parser.add_argument("--graph-dsn", default=DEFAULT_GRAPH_DSN)
    parser.add_argument("--backend-contract", type=Path, default=DEFAULT_CONTRACT_PATH)
    parser.add_argument("--readiness-timeout-seconds", type=float, default=60.0)
    return parser.parse_args(argv)


def config_from_args(args: argparse.Namespace) -> RunnerConfig:
    phases = resolve_phases(args.phase, run_250=args.run_250)
    return RunnerConfig(
        port=args.port,
        prefix=args.prefix,
        count=args.count,
        phases=phases,
        compare_profile=args.compare_profile,
        workloads=tuple(item.strip() for item in args.workloads.split(",") if item.strip()),
        repeat_count=args.repeat_count,
        false_graph=args.false_graph,
        true_graph=args.true_graph,
        proof_graph=args.proof_graph,
        false_env=parse_env_assignments(args.false_env),
        true_env=parse_env_assignments(args.true_env),
        proof_env=parse_env_assignments(args.proof_env),
        out_dir=args.out_dir,
        graph_dsn=args.graph_dsn,
        run_250=args.run_250,
        strict_contract=args.strict_contract,
        contract_path=args.backend_contract,
        readiness_timeout_seconds=args.readiness_timeout_seconds,
    )


def run(config: RunnerConfig) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for phase in phase_plan(config):
        if phase.name == PHASE_TRUE and PHASE_FALSE in results and results[PHASE_FALSE].get("status") != "PASS":
            results[phase.name] = blocked_phase_artifact(
                phase,
                config,
                reason="false_baseline_failed",
            )
            continue
        if phase.name == PHASE_PROOF and PHASE_TRUE in results and results[PHASE_TRUE].get("status") != "PASS":
            results[phase.name] = blocked_phase_artifact(
                phase,
                config,
                reason="true_compare_failed",
            )
            continue
        if phase.name == PHASE_PROOF:
            results[phase.name] = run_proof_phase(phase, config)
        else:
            results[phase.name] = run_route_phase(phase, config)
    if (
        PHASE_FALSE in results
        and PHASE_TRUE in results
        and results[PHASE_FALSE].get("status") == "PASS"
        and results[PHASE_TRUE].get("status") == "PASS"
    ):
        comparison = build_comparison(results[PHASE_FALSE], results[PHASE_TRUE])
        results["comparison"] = comparison
        if comparison["status"] != "PASS":
            true_failed_checks = list(results[PHASE_TRUE].get("failed_checks", []))
            if "comparison" not in true_failed_checks:
                true_failed_checks.append("comparison")
            results[PHASE_TRUE]["failed_checks"] = true_failed_checks
            results[PHASE_TRUE]["status"] = "FAIL"
            write_json(config.out_dir / artifact_name(PHASE_TRUE), results[PHASE_TRUE])
        write_json(config.out_dir / "route_validation_comparison.json", comparison)
    summary = build_final_summary(results)
    results["summary"] = summary
    write_json(config.out_dir / "route_validation_summary.json", summary)
    return results


def main(argv: Sequence[str] | None = None) -> int:
    try:
        config = config_from_args(parse_args(argv))
        results = run(config)
        print(json.dumps(results["summary"], indent=2, sort_keys=True))
        return 0 if results["summary"]["status"] == "PASS" else 1
    except Exception as exc:
        summary = {
            "status": "FAIL",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "performance_ledger": PERFORMANCE_LEDGER,
            "buyer_facing_claim_allowed": False,
        }
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
