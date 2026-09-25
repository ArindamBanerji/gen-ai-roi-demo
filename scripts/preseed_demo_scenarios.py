"""Preseed the five SOC PLANT demo scenarios.

Alert fixtures are written idempotently to the existing AGE graph. The other
fixtures use the existing simulation, frozen-comparison, and checkpoint APIs.
All records remain explicitly marked as planted/sample data.
"""

from __future__ import annotations

import argparse
import asyncio
import http.client
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "data" / "demo_fixtures"
BASE_URL = os.environ.get("SOC_URL", "http://127.0.0.1:8001").rstrip("/")
FIXTURE_NAMES = (
    "no_precedent_alert.json",
    "gate_transition_sequence.json",
    "policy_conflict_alert.json",
    "frozen_twin_init.json",
    "checkpoint_rollback.json",
    "soc_ae_events.json",
    "kill_chain_pair.json",
)


def load_fixture(name: str) -> dict[str, Any]:
    with (FIXTURE_DIR / name).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{name} must contain a JSON object")
    if payload.get("planted") is not True or payload.get("sample") is not True:
        raise ValueError(f"{name} must be tagged planted=true and sample=true")
    return payload


def http_json(method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, Any]:
    data = json.dumps(body, sort_keys=True).encode("utf-8") if body is not None else None
    url = urlsplit(BASE_URL + path)
    if url.scheme not in {"http", "https"} or not url.hostname:
        return 0, {"error": "invalid_url", "detail": "Expected http or https URL"}
    connection_type = http.client.HTTPSConnection if url.scheme == "https" else http.client.HTTPConnection
    # Large measured comparison cohorts need a complete body read. Retry only
    # read-only GET transport failures; an ambiguous write must never be replayed.
    attempts = 2 if method == "GET" else 1
    for attempt in range(attempts):
        connection = connection_type(url.hostname, url.port, timeout=30 if method == "GET" else 10)
        try:
            target = url.path + ("?" + url.query if url.query else "")
            connection.request(method, target, body=data,
                               headers={"Accept": "application/json", "Content-Type": "application/json"})
            response = connection.getresponse()
            raw = response.read().decode("utf-8")
            try:
                payload: Any = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                if response.status >= 400:
                    return response.status, raw
                return 0, {"error": "invalid_json", "detail": "Endpoint returned invalid JSON"}
            return response.status, payload
        except (OSError, http.client.HTTPException) as exc:
            if attempt + 1 == attempts:
                return 0, {"error": type(exc).__name__, "detail": str(exc)}
        finally:
            connection.close()
    raise AssertionError("HTTP attempt loop exhausted without a result")


def cypher_literal(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value))


def cypher_props(properties: dict[str, Any]) -> str:
    return ", ".join(f"{key}: {cypher_literal(value)}" for key, value in properties.items())


async def graph_query(query: str, client: Any) -> list[dict[str, Any]]:
    rows = await client.run_query(query)
    return [dict(row) for row in rows]


async def graph_count(client: Any, label: str, key: str, value: str) -> int:
    rows = await graph_query(
        f"MATCH (n:{label} {{{key}: {cypher_literal(value)}}}) RETURN count(n) AS cnt",
        client,
    )
    return int(rows[0].get("cnt") or 0) if rows else 0


async def ensure_alert(client: Any, fixture: dict[str, Any]) -> str:
    alert_id = str(fixture["alert_id"])
    user_id = str(fixture["user_id"])
    asset_id = str(fixture["asset_id"])
    if await graph_count(client, "Alert", "alert_id", alert_id) == 0:
        user_props = {
            "user_id": user_id,
            "id": user_id,
            "name": user_id,
            "origin": "soc_demo_fixture",
            "sample": True,
            "planted": True,
        }
        asset_props = {
            "asset_id": asset_id,
            "id": asset_id,
            "hostname": asset_id.lower(),
            "criticality": fixture.get("asset_criticality", "high"),
            "origin": "soc_demo_fixture",
            "sample": True,
            "planted": True,
        }
        alert_props = {
            "alert_id": alert_id,
            "id": alert_id,
            "domain": "soc",
            "category": fixture["category"],
            "severity": fixture["severity"],
            "alert_type": fixture["alert_type"],
            "status": fixture.get("status", "pending"),
            "origin": "soc_demo_fixture",
            "source": "soc_demo_fixture",
            "sample": True,
            "planted": True,
            "timestamp_epoch": fixture["timestamp_epoch"],
            "source_location": fixture.get("source_location", "demo"),
            "user_id": user_id,
            "asset_id": asset_id,
            "description": fixture["description"],
            **({"synthetic_verified_action": fixture["verified_action"]}
               if "verified_action" in fixture else {}),
        }
        if await graph_count(client, "User", "user_id", user_id) == 0:
            await client.run_query(f"CREATE (n:User {{{cypher_props(user_props)}}})")
        if await graph_count(client, "Asset", "asset_id", asset_id) == 0:
            await client.run_query(f"CREATE (n:Asset {{{cypher_props(asset_props)}}})")
        await client.run_query(f"CREATE (n:Alert {{{cypher_props(alert_props)}}})")
        await client.run_query(
            f"MATCH (a:Alert {{alert_id: {cypher_literal(alert_id)}}}), "
            f"(u:User {{user_id: {cypher_literal(user_id)}}}) "
            "CREATE (a)-[:INVOLVES]->(u)"
        )
        await client.run_query(
            f"MATCH (a:Alert {{alert_id: {cypher_literal(alert_id)}}}), "
            f"(x:Asset {{asset_id: {cypher_literal(asset_id)}}}) "
            "CREATE (a)-[:DETECTED_ON]->(x)"
        )
        return "created"
    return "existing"


async def get_graph_client() -> Any:
    backend_path = ROOT / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    module = __import__("app.db.graph_client", fromlist=["graph_client"])
    return module.graph_client


def frozen_twin_alert_fixture() -> dict[str, Any]:
    """Provide an analyzable alert for the SOC-08 frozen-twin demo fixture."""

    fixture = load_fixture("frozen_twin_init.json")
    alert_id = str(fixture["fixture_id"])
    return {
        "alert_id": alert_id,
        "id": alert_id,
        "alert_type": "anomalous_login",
        "category": "credential_access",
        "severity": "medium",
        "source_location": "demo-frozen-twin",
        "timestamp_epoch": 1789657800,
        "description": (
            "Planted SOC-08 replay alert used to compare live learning with "
            "the frozen day-zero checkpoint."
        ),
        "asset_id": "PL-SOC-4-ASSET-IDENTITY-01",
        "user_id": "svc-frozen-twin-demo",
        "status": "pending",
        "asset_criticality": "high",
        "planted": True,
        "sample": True,
        "scenario": str(fixture["scenario"]),
    }


async def seed_alert_fixtures(dry_run: bool) -> dict[str, str]:
    alert_fixtures = {
        "no_precedent_alert.json": load_fixture("no_precedent_alert.json"),
        "policy_conflict_alert.json": load_fixture("policy_conflict_alert.json"),
        "frozen_twin_init.json": frozen_twin_alert_fixture(),
    }
    if dry_run:
        return {name: "planned" for name in alert_fixtures}
    client = await get_graph_client()
    result: dict[str, str] = {}
    for name, fixture in alert_fixtures.items():
        result[name] = await ensure_alert(client, fixture)
    return result


async def seed_kill_chain_alerts(dry_run: bool) -> str:
    """Seed the linked SOC-05 alert pair as Alert/User/Asset graph nodes."""

    fixture = load_fixture("kill_chain_pair.json")
    alerts = fixture.get("alerts")
    if not isinstance(alerts, list) or len(alerts) != 2:
        raise ValueError("SOC kill-chain fixture must contain exactly two alerts")
    if dry_run:
        return "planned"

    client = await get_graph_client()
    statuses = [await ensure_alert(client, dict(alert)) for alert in alerts]
    return "created" if "created" in statuses else "existing"


async def seed_ae_events(dry_run: bool) -> str:
    """Seed the explicit SOC-03 lifecycle counts once, without altering live events."""

    fixture = load_fixture("soc_ae_events.json")
    counts = fixture.get("counts", {})
    tested = int(counts.get("tested", 0))
    promoted = int(counts.get("promoted", 0))
    rejected = int(counts.get("rejected", 0))
    if tested != promoted + rejected or tested <= 0:
        raise ValueError("SOC AE fixture counts must satisfy tested = promoted + rejected")
    if dry_run:
        return "planned"

    client = await get_graph_client()
    existing_rows = await graph_query(
        "MATCH (e:EvolutionEvent) WHERE e.variant_id STARTS WITH 'soc-demo-ae-' "
        "RETURN count(e) AS cnt, max(e.timestamp_epoch) AS max_ts",
        client,
    )
    if existing_rows and int(existing_rows[0].get("cnt") or 0) > 0:
        # Keep the planted lifecycle in the default recent-events window on
        # every idempotent preseed run, without creating duplicate variants.
        global_rows = await graph_query(
            "MATCH (e:EvolutionEvent) RETURN max(e.timestamp_epoch) AS max_ts",
            client,
        )
        max_ts = max(
            float(existing_rows[0].get("max_ts") or 0.0),
            float(global_rows[0].get("max_ts") or 0.0) if global_rows else 0.0,
        )
        planted_epoch = max(time.time() * 1000.0, max_ts) + 1_000_000_000.0
        await client.run_query(
            "MATCH (e:EvolutionEvent) "
            "WHERE e.variant_id STARTS WITH 'soc-demo-ae-' "
            f"SET e.timestamp_epoch = {planted_epoch}"
        )
        # AGE sorts null timestamps before DESC values. Give legacy events a
        # stable earlier timestamp so the planted lifecycle is visible in the
        # endpoint's default recent-events window.
        await client.run_query(
            "MATCH (e:EvolutionEvent) WHERE e.timestamp_epoch IS NULL "
            f"SET e.timestamp_epoch = {planted_epoch - 1.0}"
        )
        return "existing"

    from gae.evolution import (
        ARTIFACT_CONTEXT_POLICY,
        ARTIFACT_ROUTING_RULE,
        PROMOTION_APPROVED,
        PROMOTION_REJECTED,
        VARIANT_CREATED,
        record_evolution_event,
    )

    global_rows = await graph_query(
        "MATCH (e:EvolutionEvent) RETURN max(e.timestamp_epoch) AS max_ts",
        client,
    )
    global_max = float(global_rows[0].get("max_ts") or 0.0) if global_rows else 0.0
    planted_epoch = max(time.time() * 1000.0, global_max) + 1_000_000_000.0

    for index in range(tested):
        variant_id = f"soc-demo-ae-{index + 1:02d}"
        artifact_type = ARTIFACT_ROUTING_RULE if index % 2 == 0 else ARTIFACT_CONTEXT_POLICY
        metadata = {
            "fixture_id": fixture["fixture_id"],
            "planted": True,
            "sample": True,
            "variant_number": index + 1,
        }
        await record_evolution_event(
            client,
            VARIANT_CREATED,
            variant_id,
            artifact_type,
            "SOC demo AE candidate evaluated against the governed promotion gate.",
            metadata=metadata,
            timestamp_override=planted_epoch + (index * 2.0),
        )
        if index < promoted:
            event_type = PROMOTION_APPROVED
            description = "Promoted after shadow evidence cleared governance checks."
        else:
            event_type = PROMOTION_REJECTED
            description = "Rejected by the governed promotion gate before production release."
        await record_evolution_event(
            client,
            event_type,
            variant_id,
            artifact_type,
            description,
            metadata=metadata,
            timestamp_override=planted_epoch + (index * 2.0) + 1.0,
        )
    await client.run_query(
        "MATCH (e:EvolutionEvent) WHERE e.timestamp_epoch IS NULL "
        f"SET e.timestamp_epoch = {planted_epoch - 1.0}"
    )
    return "created"


def seed_twin_sequence(dry_run: bool) -> dict[str, str]:
    result: dict[str, str] = {}
    if dry_run:
        return {"frozen_twin_init.json": "planned", "soc-08-post-freeze-decisions": "planned"}
    # Production day zero remains immutable. A fresh demo comparison is a
    # separately archived operation, enabled explicitly on the running server.
    # Probe validation without mutating a snapshot. Downloading the full OpenAPI
    # document can time out even when this route is ready.
    probe_status, _ = http_json("POST", "/api/demo/learning/re-freeze", {})
    if probe_status != 422:
        result["frozen_twin_init.json"] = f"failed:demo re-freeze preflight returned {probe_status}; expected validation 422"
    else:
        # Check demo read availability. Reads may have their own persistent
        # flag; re-freeze still independently requires reseed write permission.
        comparison_status, _ = http_json("GET", "/api/soc/learning/frozen-comparison?demo=true")
        if comparison_status not in {200, 404}:
            return {"frozen_twin_init.json": f"failed:demo comparison preflight {comparison_status}; requires SOC_DEMO_RESEED_ENABLED=true"}
        status, _payload = http_json("POST", "/api/soc/learning/frozen-comparison/freeze")
        # These are labelled synthetic outcomes, not accuracy evidence.
        # Correct outcomes do not guarantee a positive confidence change.
        before = seed_post_freeze_decisions(False, count=30, phase="PRE", check_gap=False) if status == 201 else f"failed:{status}"
        if not before.startswith("verified:"):
            result["frozen_twin_init.json"] = before
        else:
            status, _payload = http_json("POST", "/api/demo/learning/re-freeze", {"confirm_demo_reseed": True})
            result["frozen_twin_init.json"] = "verified" if status == 201 else f"failed:demo re-freeze {status}; requires SOC_DEMO_RESEED_ENABLED=true"
            if status == 201:
                result["soc-08-post-freeze-decisions"] = seed_post_freeze_decisions(
                    False, count=60, phase="POST", check_gap=True)
    return result


def run_api_fixtures(dry_run: bool) -> dict[str, str]:
    result = seed_twin_sequence(dry_run)
    if dry_run:
        return {**result, "gate_transition_sequence.json": "planned", "checkpoint_rollback.json": "planned"}
    # Keep failure simulation out of the before/freeze/after comparison sequence.
    status, payload = http_json("POST", "/api/eval/simulate-failure")
    result["gate_transition_sequence.json"] = (
        "verified" if status == 200 and bool(payload.get("simulated")) else f"failed:{status}"
    )

    list_status, list_payload = http_json("GET", "/api/soc/checkpoint/list")
    existing_checkpoint = None
    if list_status == 200 and isinstance(list_payload, dict):
        for checkpoint in list_payload.get("checkpoints", []):
            if isinstance(checkpoint, dict) and checkpoint.get("reason") == "SOC-10 planted rollback proof":
                existing_checkpoint = checkpoint.get("id") or checkpoint.get("checkpoint_id")
                break
    if existing_checkpoint:
        result["checkpoint_rollback.json"] = "existing_verified"
        return result

    create_status, create_payload = http_json(
        "POST", "/api/soc/checkpoint/create", {"reason": "SOC-10 planted rollback proof"}
    )
    checkpoint_id = create_payload.get("checkpoint_id") if isinstance(create_payload, dict) else None
    if create_status == 200 and checkpoint_id:
        http_json("POST", "/api/eval/simulate-failure")
        rollback_status, rollback_payload = http_json(
            "POST", "/api/soc/checkpoint/rollback", {"checkpoint_id": checkpoint_id}
        )
        restored = isinstance(rollback_payload, dict) and "error" not in rollback_payload
        result["checkpoint_rollback.json"] = "verified" if rollback_status == 200 and restored else f"failed:{rollback_status}"
    else:
        result["checkpoint_rollback.json"] = f"failed:{create_status}"
    return result


def twin_learning_failure(status: int, payload: Any) -> str | None:
    """An accepted verification is not proof that centroid learning persisted."""
    if status not in (200, 201) or not isinstance(payload, dict):
        return f"outcome_http_{status}"
    reason = payload.get("l5_persistence_skipped_reason")
    if reason:
        return str(reason)
    if payload.get("l5_centroid_persisted") is not True:
        return "centroid_not_persisted"
    update = payload.get("centroid_update")
    if not isinstance(update, dict):
        return "centroid_update_missing"
    movement = update.get("centroid_delta_norm")
    if (not isinstance(movement, (int, float)) or isinstance(movement, bool)
            or not math.isfinite(movement) or movement <= 0):
        return "no_measured_centroid_movement"
    return None


def frozen_twin_learning_fixture() -> dict[str, Any]:
    """A disclosed synthetic monitoring cohort, separate from SOC-06 geometry.

    The analyst label is fixed fixture data, independent of model predictions.
    Distinct IDs keep the older credential-access samples immutable.
    """
    base = frozen_twin_alert_fixture()
    return {**base, "alert_id": f"{base['alert_id']}-VERIFIED-LM",
            "category": "lateral_movement", "alert_type": "lateral_movement",
            "source_location": "demo-frozen-twin-verified-lm",
            "user_id": "svc-frozen-twin-verified-lm", "asset_id": "PL-SOC-4-ASSET-LM",
            "verified_action": "monitor",
            "description": "Synthetic reviewed lateral activity; analyst fixture classification: monitor."}


def seed_post_freeze_decisions(dry_run: bool, count: int = 20, *,
                               phase: str = "POST", check_gap: bool = True) -> str:
    """Create verified post-freeze evidence for the SOC-08 demo beat.

    The loop deliberately uses the public analyze/outcome contract.  This keeps
    the fixture on the same path as an analyst's verified decision and avoids
    writing fabricated scorer or twin state from the preseed process.
    """

    if dry_run:
        return "planned"
    base = frozen_twin_learning_fixture()
    completed = 0
    for index in range(1, count + 1):
        alert_id = f"{base['alert_id']}-{phase}-{index:02d}"
        fixture = dict(base)
        fixture.update(
            {
                "alert_id": alert_id,
                "id": alert_id,
                "timestamp_epoch": int(base["timestamp_epoch"]) + index,
                "description": (
                    f"Planted SOC-08 {phase} synthetic verified decision "
                    f"{index:02d}; analyst fixture classification: {base['verified_action']}."
                ),
            }
        )

        # Reuse the async graph helper without adding a second graph client
        # lifecycle to the script's main path.
        async def ensure_and_score() -> tuple[int, Any, int, Any]:
            graph_client = await get_graph_client()
            await ensure_alert(graph_client, fixture)
            analyze_status, analyze_payload = http_json(
                "POST", "/api/alert/analyze", {"alert_id": alert_id}
            )
            if analyze_status != 200 or not isinstance(analyze_payload, dict):
                return analyze_status, analyze_payload, 0, None
            recommendation = analyze_payload.get("recommendation") or {}
            decision_id = recommendation.get("decision_id")
            if not decision_id:
                return analyze_status, analyze_payload, 0, None
            # Read the scored proposal saved before referral. Never reconstruct
            # legacy predictions from today's model or rewrite routed decisions.
            rows = await graph_client.run_query(
                f"MATCH (d:Decision {{decision_id: {cypher_literal(str(decision_id))}}}) "
                "WHERE d.domain = 'soc' RETURN d.original_action AS original_action"
            )
            original_action = rows[0].get("original_action") if rows else None
            if original_action not in {"escalate", "investigate", "suppress", "monitor"}:
                return analyze_status, analyze_payload, 0, {
                    "l5_persistence_skipped_reason": "stored_scorer_action_missing",
                }
            # Never rewrite a scored/audited decision. Synthetic ground truth
            # enters only through the same outcome API as analyst verification.
            actual_action = base["verified_action"]
            correct = original_action == actual_action
            outcome_status, outcome_payload = http_json(
                "POST",
                "/api/alert/outcome",
                {
                    "alert_id": alert_id,
                    "decision_id": str(decision_id),
                    "outcome": "correct" if correct else "incorrect",
                    "analyst_action": actual_action,
                    "override_comment": f"SOC-08 {phase} planted synthetic verification (T-sim)",
                },
            )
            return analyze_status, analyze_payload, outcome_status, outcome_payload

        analyze_status, analyze_payload, outcome_status, outcome_payload = asyncio.run(
            ensure_and_score()
        )
        if analyze_status != 200:
            return f"failed:analyze_http_{analyze_status}:learned={completed}/{count}"
        if outcome_status == 0:
            reason = (outcome_payload or {}).get("l5_persistence_skipped_reason", "missing_scorable_decision")
            gates = {key: analyze_payload.get(key) for key in ("authority", "referral")}
            return f"failed:{reason}:learned={completed}/{count}:gates={json.dumps(gates, sort_keys=True)}"
        failure = twin_learning_failure(outcome_status, outcome_payload)
        if failure:
            return f"failed:learning_blocked:{failure}:learned={completed}/{count}"
        completed += 1

    if completed < count:
        return f"failed:verified={completed}/{count}"
    if not check_gap:
        return f"verified:count={completed},synthetic_ground_truth={base['verified_action']}"
    check_status, check_payload = http_json("GET", "/api/soc/learning/frozen-comparison?demo=true")
    if check_status == 200 and isinstance(check_payload, dict):
        decisions = int(check_payload.get("decisions_since_freeze") or 0)
        points = check_payload.get("comparison_points", [])
        deltas = [float(point["confidence_delta"]) for point in points]
        mean_delta = sum(deltas) / len(deltas) if deltas else 0.0
        if decisions > 0 and deltas and mean_delta > 0:
            return f"verified:compared={len(deltas)},mean_confidence_delta={mean_delta:.6f}"
        return f"failed:no_positive_confidence_change:compared={len(deltas)},mean={mean_delta:.6f}"
    return f"failed:comparison_status={check_status}:detail={check_payload}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="validate and report without mutating AGE or API state")
    parser.add_argument("--twin-only", action="store_true", help="Seed only SOC-08; leave evolution and failure simulation untouched")
    args = parser.parse_args()
    if args.twin_only:
        result = seed_twin_sequence(args.dry_run)
        print(json.dumps(result, indent=2))
        return int(any(not (value == "planned" or value.startswith("verified")) for value in result.values()))

    for name in FIXTURE_NAMES:
        load_fixture(name)
        print(f"fixture {name}: planted=true sample=true")

    graph_results = asyncio.run(seed_alert_fixtures(args.dry_run))
    graph_results["kill_chain_pair.json"] = asyncio.run(seed_kill_chain_alerts(args.dry_run))
    graph_results["soc_ae_events.json"] = asyncio.run(seed_ae_events(args.dry_run))
    api_results = run_api_fixtures(args.dry_run)
    results = {**graph_results, **api_results}
    for name, value in results.items():
        print(f"{name}: {value}")
    succeeded = sum(
        value in {"planned", "created", "existing", "existing_verified", "verified"}
        or value.startswith("verified")
        for value in results.values()
    )
    print(f"verified_or_planned={succeeded}/{len(results)} dry_run={args.dry_run}")
    return 0 if succeeded == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
