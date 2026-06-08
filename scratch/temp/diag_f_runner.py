from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


REPO = Path(__file__).resolve().parents[2]
PROJECTS = REPO.parent
BACKEND = REPO / "backend"
CI_PLATFORM = PROJECTS / "ci-platform"
for p in (str(CI_PLATFORM), str(BACKEND), str(REPO)):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.graph_schema import _S  # noqa: E402
from ci_platform.graph.age_client import AGEClient  # noqa: E402


BASE_URL = "http://127.0.0.1:8001"
GRAPH_DSN = "host=localhost port=5433 dbname=soc_copilot user=postgres password=postgres"
GRAPH_NAME = "soc_graph_diag_f"
PREFIX = "DIAG-F-CRED"
SEED_COUNT = 300
LONG_LOOP_TARGET = 250
TARGET_CATEGORY = "credential_access"
SCORER_ACTIONS = {"escalate", "investigate", "suppress", "monitor"}
MILESTONE_COUNTS = {195, 200, 201, 205, 215, 230, 250}


def alert_id(index: int) -> str:
    return f"{PREFIX}-{index:04d}"


def request_json(method: str, path: str, payload: dict[str, Any] | None = None, timeout: int = 30) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = Request(
        BASE_URL + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            parsed: Any
            try:
                parsed = json.loads(body) if body else {}
            except Exception:
                parsed = body
            return {"status": resp.status, "body": parsed, "raw": body}
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = body
        return {"status": exc.code, "body": parsed, "raw": body}
    except URLError as exc:
        return {"status": None, "body": {"error": str(exc)}, "raw": str(exc)}


def get_json(path: str, timeout: int = 30) -> dict[str, Any]:
    req = Request(BASE_URL + path, method="GET")
    try:
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return {"status": resp.status, "body": json.loads(body) if body else {}, "raw": body}
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = body
        return {"status": exc.code, "body": parsed, "raw": body}
    except URLError as exc:
        return {"status": None, "body": {"error": str(exc)}, "raw": str(exc)}


async def scalar(client: AGEClient, query: str, key: str = "cnt") -> int:
    rows = await client.run_query(query)
    if not rows:
        return 0
    return int(rows[0].get(key) or 0)


async def seed_alerts(client: AGEClient) -> dict[str, Any]:
    created = 0
    existing = 0
    for i in range(1, SEED_COUNT + 1):
        aid = alert_id(i)
        user_id = f"{aid}-USER"
        asset_id = f"{aid}-ASSET"
        exists = await scalar(
            client,
            f"MATCH (a:Alert {{alert_id: {_S(aid)}}}) RETURN count(a) AS cnt",
        )
        if exists:
            existing += 1
            continue
        await client.run_query(
            "CREATE (u:User {"
            + ", ".join(
                [
                    f"user_id: {_S(user_id)}",
                    f"id: {_S(user_id)}",
                    f"name: {_S('Diagnostic F C9B User ' + str(i))}",
                    "origin: 'c9b_seed'",
                    "department: 'SOC'",
                    "risk_level: 'critical'",
                    "risk_score: 0.92",
                    "c9b_proof: true",
                    "diagnostic: 'F'",
                ]
            )
            + "})"
        )
        await client.run_query(
            "CREATE (asset:Asset {"
            + ", ".join(
                [
                    f"asset_id: {_S(asset_id)}",
                    f"id: {_S(asset_id)}",
                    f"hostname: {_S('diag-f-c9b-' + str(i))}",
                    "criticality: 'critical'",
                    "origin: 'c9b_seed'",
                    "asset_type: 'workload'",
                    "business_unit: 'security'",
                    "c9b_proof: true",
                    "diagnostic: 'F'",
                ]
            )
            + "})"
        )
        await client.run_query(
            "CREATE (a:Alert {"
            + ", ".join(
                [
                    f"alert_id: {_S(aid)}",
                    f"id: {_S(aid)}",
                    "category: 'credential_access'",
                    "severity: 'critical'",
                    "alert_type: 'anomalous_login'",
                    "status: 'pending'",
                    "origin: 'c9b_seed'",
                    "source: 'c9b_seed'",
                    "c9b_proof: true",
                    "diagnostic: 'F'",
                    f"timestamp_epoch: {1726000000000 + i}",
                    f"source_location: {_S('diag-f-zone-' + str(i % 6))}",
                    f"user_id: {_S(user_id)}",
                    f"asset_id: {_S(asset_id)}",
                    "attack_pattern_id: ''",
                    "mfa_completed: false",
                    "device_fingerprint_match: false",
                    "vpn_provider: 'c9b_seed'",
                ]
            )
            + "})"
        )
        await client.run_query(
            f"MATCH (a:Alert {{alert_id: {_S(aid)}}}), (u:User {{user_id: {_S(user_id)}}}) "
            "CREATE (a)-[:INVOLVES]->(u)"
        )
        await client.run_query(
            f"MATCH (a:Alert {{alert_id: {_S(aid)}}}), (asset:Asset {{asset_id: {_S(asset_id)}}}) "
            "CREATE (a)-[:DETECTED_ON]->(asset)"
        )
        created += 1
        if created % 50 == 0:
            print(f"seeded_created={created}", flush=True)
    return {
        "method": "scratch/temp/diag_f_runner.py direct AGEClient seed",
        "created": created,
        "existing": existing,
        "planned": SEED_COUNT,
        "first_id": alert_id(1),
        "last_id": alert_id(SEED_COUNT),
        "alert_type": "anomalous_login",
        "criticality": "critical",
        "graph": GRAPH_NAME,
    }


def extract_decision_id(body: dict[str, Any]) -> str | None:
    return (
        body.get("decision_id")
        or body.get("id")
        or body.get("recommendation", {}).get("decision_id")
        or body.get("gae_scoring", {}).get("decision_id")
    )


def extract_action(body: dict[str, Any]) -> str | None:
    return body.get("action") or body.get("recommendation", {}).get("action")


def extract_category(body: dict[str, Any]) -> str | None:
    return (
        body.get("category")
        or body.get("alert", {}).get("category")
        or body.get("situation_analysis", {}).get("category")
    )


def compact_analyze(resp: dict[str, Any]) -> dict[str, Any]:
    body = resp.get("body") if isinstance(resp.get("body"), dict) else {}
    fv = body.get("factor_vector") or body.get("gae_scoring", {}).get("factor_vector")
    return {
        "status": resp.get("status"),
        "category": extract_category(body),
        "action": extract_action(body),
        "confidence": body.get("confidence") or body.get("recommendation", {}).get("confidence"),
        "decision_id": extract_decision_id(body),
        "factor_vector": fv,
        "factor_vector_len": len(fv) if isinstance(fv, list) else None,
        "routing_zone": body.get("routing_zone")
        or body.get("recommendation", {}).get("routing_zone")
        or body.get("gae_scoring", {}).get("routing_zone"),
        "referral": body.get("referral"),
        "decision_method": body.get("decision_method"),
    }


def compact_outcome(resp: dict[str, Any]) -> dict[str, Any]:
    body = resp.get("body") if isinstance(resp.get("body"), dict) else {}
    return {
        "status": resp.get("status"),
        "outcome": body.get("outcome"),
        "centroid_update": body.get("centroid_update"),
        "l5_centroid_persisted": body.get("l5_centroid_persisted"),
        "l5_shaped_by_attempted": body.get("l5_shaped_by_attempted"),
        "l5_persistence_skipped_reason": body.get("l5_persistence_skipped_reason"),
        "l5_persistence": body.get("l5_persistence"),
    }


async def readback(client: AGEClient, decision_ids: list[str] | None = None) -> dict[str, Any]:
    prefix_lit = _S(PREFIX)
    decision_ids = decision_ids or []
    ids_json = json.dumps(decision_ids)
    queries = {
        "diag_decisions": f"""
            MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)
            WHERE d.domain = 'soc' AND a.alert_id STARTS WITH {prefix_lit}
            RETURN count(d) AS cnt
        """,
        "diag_verified": f"""
            MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)
            WHERE d.domain = 'soc' AND a.alert_id STARTS WITH {prefix_lit}
              AND d.outcome IS NOT NULL AND d.correct IS NOT NULL
            RETURN count(d) AS cnt
        """,
        "target_outcomes": f"""
            MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)
            WHERE d.domain = 'soc' AND a.alert_id STARTS WITH {prefix_lit}
              AND d.category = 'credential_access'
              AND d.action <> 'refer_to_analyst'
              AND d.outcome = 'correct' AND d.correct = true
            RETURN count(d) AS cnt
        """,
        "l5_centroid": "MATCH (c:L5Centroid) WHERE c.domain = 'soc' RETURN count(c) AS cnt",
        "shaped_by": "MATCH (c:L5Centroid)-[:SHAPED_BY]->(d:Decision) WHERE c.domain = 'soc' RETURN count(*) AS cnt",
        "l5_dk_weight": "MATCH (w:L5DKWeight) WHERE w.domain = 'soc' RETURN count(w) AS cnt",
        "l5_conservation": "MATCH (cs:L5ConservationState) WHERE cs.domain = 'soc' RETURN count(cs) AS cnt",
    }
    counts: dict[str, int] = {}
    raw: dict[str, Any] = {}
    for name, query in queries.items():
        rows = await client.run_query(query)
        raw[name] = rows
        counts[name] = int(rows[0].get("cnt") or 0) if rows else 0
    raw["category_counts"] = await client.run_query(
        f"""
        MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)
        WHERE d.domain = 'soc' AND a.alert_id STARTS WITH {prefix_lit}
        RETURN d.category AS category, count(d) AS cnt
        ORDER BY category
        """
    )
    raw["dk_weight_rows"] = await client.run_query(
        """
        MATCH (w:L5DKWeight)
        WHERE w.domain = 'soc'
        RETURN w.domain AS domain,
               w.dk_weight_id AS dk_weight_id,
               w.n_decisions_used AS n_decisions_used,
               w.n_confirmed AS n_confirmed,
               w.n_overridden AS n_overridden,
               w.confirmed_mean_json IS NOT NULL AS confirmed_mean,
               w.confirmed_m2_json IS NOT NULL AS confirmed_m2,
               w.overridden_mean_json IS NOT NULL AS overridden_mean,
               w.overridden_m2_json IS NOT NULL AS overridden_m2,
               w.all_mean_json IS NOT NULL AS all_mean,
               w.all_m2_json IS NOT NULL AS all_m2
        ORDER BY w.updated_at_epoch DESC
        """
    )
    raw["l5_centroid_rows"] = await client.run_query(
        """
        MATCH (c:L5Centroid)
        WHERE c.domain = 'soc'
        RETURN c.domain AS domain, c.category AS category, c.action AS action,
               c.caused_by_decision_id AS caused_by_decision_id,
               c.delta_norm AS delta_norm
        """
    )
    raw["conservation_rows"] = await client.run_query(
        """
        MATCH (cs:L5ConservationState)
        WHERE cs.domain = 'soc'
        RETURN cs.domain AS domain, cs.status AS status, cs.alpha AS alpha,
               cs.q AS q, cs.V AS V, cs.theta_min AS theta_min
        """
    )
    if decision_ids:
        raw["diag_dk_caused_decisions"] = await client.run_query(
            f"""
            MATCH (w:L5DKWeight)-[:TRIGGERED_BY]->(d:Decision)-[:DECIDED_ON]->(a:Alert)
            WHERE w.domain = 'soc' AND d.decision_id IN {ids_json}
            RETURN a.alert_id AS alert_id, d.decision_id AS decision_id,
                   w.n_decisions_used AS n_decisions_used
            """
        )
    return {"counts": counts, "raw": raw}


async def milestone_snapshot(client: AGEClient, total_valid: int, long_valid: int, note: str) -> dict[str, Any]:
    qs = urlencode({"category": TARGET_CATEGORY})
    state = get_json(f"/api/triage/learning-state?{qs}", timeout=30)
    rb = await readback(client)
    dk_rows = rb["raw"].get("dk_weight_rows", [])
    welford_present = False
    if dk_rows:
        row = dk_rows[0]
        welford_present = all(
            bool(row.get(k))
            for k in (
                "confirmed_mean",
                "confirmed_m2",
                "overridden_mean",
                "overridden_m2",
                "all_mean",
                "all_m2",
            )
        )
    state_body = state.get("body") if isinstance(state.get("body"), dict) else {}
    return {
        "valid_target_outcomes": total_valid,
        "long_loop_valid_target_outcomes": long_valid,
        "learning_state_status": state.get("status"),
        "phase": state_body.get("phase"),
        "decisions_in_category": state_body.get("decisions_in_category"),
        "dk_weights_endpoint": state_body.get("dk_weights"),
        "l5_centroid": rb["counts"].get("l5_centroid"),
        "shaped_by": rb["counts"].get("shaped_by"),
        "l5_dk_weight": rb["counts"].get("l5_dk_weight"),
        "welford_present": welford_present,
        "dk_weight_rows": dk_rows,
        "note": note,
    }


async def run_one(client: AGEClient, aid: str) -> dict[str, Any]:
    t0 = time.perf_counter()
    analyze_resp = request_json("POST", "/api/alert/analyze", {"alert_id": aid}, timeout=30)
    analyze = compact_analyze(analyze_resp)
    outcome_resp = None
    outcome = None
    decision_id = analyze.get("decision_id")
    action = analyze.get("action")
    if analyze.get("status") == 200 and decision_id and action in SCORER_ACTIONS:
        outcome_resp = request_json(
            "POST",
            "/api/alert/outcome",
            {
                "alert_id": aid,
                "decision_id": decision_id,
                "outcome": "correct",
                "analyst_action": action,
            },
            timeout=30,
        )
        outcome = compact_outcome(outcome_resp)
    elapsed = time.perf_counter() - t0
    return {
        "alert_id": aid,
        "elapsed_seconds": elapsed,
        "analyze": analyze,
        "outcome": outcome,
        "raw_analyze_body": analyze_resp.get("body"),
        "raw_outcome_body": outcome_resp.get("body") if outcome_resp else None,
    }


def is_valid_target(loop_result: dict[str, Any]) -> bool:
    analyze = loop_result.get("analyze") or {}
    outcome = loop_result.get("outcome") or {}
    return (
        analyze.get("status") == 200
        and analyze.get("category") == TARGET_CATEGORY
        and analyze.get("action") in SCORER_ACTIONS
        and outcome is not None
        and outcome.get("status") == 200
    )


async def main() -> int:
    start = time.perf_counter()
    client = AGEClient(dsn=GRAPH_DSN, graph_name=GRAPH_NAME)
    await client.ensure_graph()
    seed = await seed_alerts(client)
    result: dict[str, Any] = {
        "graph": GRAPH_NAME,
        "base_url": BASE_URL,
        "seed": seed,
        "started_epoch": time.time(),
        "process_note": "seed, sanity, and long loop executed in one Python process",
        "sanity": None,
        "progress": [],
        "milestones": {},
        "loops_sample": [],
        "failures": [],
        "attempts": 0,
        "long_loop_valid_target_outcomes": 0,
        "valid_target_outcomes": 0,
        "refer_to_analyst_skipped": 0,
        "other_categories": 0,
        "outcome_failures": 0,
        "analyze_failures": 0,
        "decision_ids": [],
    }

    sanity = await run_one(client, alert_id(1))
    result["sanity"] = sanity
    if is_valid_target(sanity):
        result["valid_target_outcomes"] += 1
        result["decision_ids"].append(sanity["analyze"]["decision_id"])
    if sanity["analyze"].get("category") != TARGET_CATEGORY:
        result["stop_reason"] = "sanity_category_not_target"
    elif sanity["analyze"].get("action") == "refer_to_analyst":
        result["stop_reason"] = "sanity_refer_to_analyst"
    elif not sanity.get("outcome") or sanity["outcome"].get("status") != 200:
        result["stop_reason"] = "sanity_outcome_failed"
    elif sanity["elapsed_seconds"] > 10:
        result["stop_reason"] = "sanity_elapsed_gt_10"
    if result.get("stop_reason"):
        result["final_readback"] = await readback(client, result["decision_ids"])
        Path(__file__).with_name("diag_f_results.json").write_text(
            json.dumps(result, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        print(json.dumps(result, indent=2, sort_keys=True), flush=True)
        return 2

    next_index = 2
    while result["long_loop_valid_target_outcomes"] < LONG_LOOP_TARGET and next_index <= SEED_COUNT:
        aid = alert_id(next_index)
        loop = await run_one(client, aid)
        result["attempts"] += 1
        analyze = loop.get("analyze") or {}
        outcome = loop.get("outcome") or {}
        action = analyze.get("action")
        category = analyze.get("category")
        if analyze.get("status") != 200:
            result["analyze_failures"] += 1
            result["failures"].append({"alert_id": aid, "type": "analyze", "loop": loop})
        elif category != TARGET_CATEGORY:
            result["other_categories"] += 1
            result["failures"].append({"alert_id": aid, "type": "other_category", "category": category})
        elif action == "refer_to_analyst":
            result["refer_to_analyst_skipped"] += 1
        elif action not in SCORER_ACTIONS:
            result["failures"].append({"alert_id": aid, "type": "non_scorer_action", "action": action})
        elif not outcome or outcome.get("status") != 200:
            result["outcome_failures"] += 1
            result["failures"].append({"alert_id": aid, "type": "outcome", "loop": loop})
        else:
            result["long_loop_valid_target_outcomes"] += 1
            result["valid_target_outcomes"] += 1
            result["decision_ids"].append(analyze.get("decision_id"))
            if len(result["loops_sample"]) < 10 or result["long_loop_valid_target_outcomes"] % 25 == 0:
                result["loops_sample"].append(
                    {
                        "alert_id": aid,
                        "valid_target_outcomes": result["valid_target_outcomes"],
                        "long_loop_valid_target_outcomes": result["long_loop_valid_target_outcomes"],
                        "analyze": analyze,
                        "outcome": outcome,
                    }
                )
            if result["long_loop_valid_target_outcomes"] % 25 == 0:
                progress = {
                    "long_loop_valid_target_outcomes": result["long_loop_valid_target_outcomes"],
                    "valid_target_outcomes": result["valid_target_outcomes"],
                    "attempts": result["attempts"],
                    "elapsed_seconds": time.perf_counter() - start,
                }
                result["progress"].append(progress)
                print("PROGRESS " + json.dumps(progress, sort_keys=True), flush=True)
            if result["valid_target_outcomes"] in MILESTONE_COUNTS:
                snap = await milestone_snapshot(
                    client,
                    result["valid_target_outcomes"],
                    result["long_loop_valid_target_outcomes"],
                    f"milestone {result['valid_target_outcomes']}",
                )
                result["milestones"][str(result["valid_target_outcomes"])] = snap
                print("MILESTONE " + json.dumps(snap, sort_keys=True), flush=True)
        next_index += 1

    result["elapsed_seconds"] = time.perf_counter() - start
    result["final_readback"] = await readback(client, result["decision_ids"])
    out_path = Path(__file__).with_name("diag_f_results.json")
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

