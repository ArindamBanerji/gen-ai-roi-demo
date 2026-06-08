from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


REPO = Path(__file__).resolve().parents[2]
PROJECTS = REPO.parent
BACKEND = REPO / "backend"
CI_PLATFORM = PROJECTS / "ci-platform"
for path in (str(BACKEND), str(CI_PLATFORM)):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.graph_schema import _S  # noqa: E402
from ci_platform.graph.age_client import AGEClient  # noqa: E402


BASE_URL = os.getenv("SOC_BACKEND_URL", "http://127.0.0.1:8001").rstrip("/")
PREFIX = "DIAG-F2-CRED"
GRAPH = os.getenv("AGE_GRAPH_NAME", "soc_graph_diag_f2")
SCORER_ACTIONS = {"escalate", "investigate", "suppress", "monitor"}
MILESTONES = {195, 200, 201, 205, 215, 230, 250}


def http_json(method: str, path: str, payload: dict | None = None, timeout: int = 20) -> tuple[int, dict]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw)
        except Exception:
            body = {"raw": raw}
        return exc.code, body
    except URLError as exc:
        return 0, {"error": repr(exc)}


def props(values: dict) -> str:
    return ", ".join(f"{key}: {_S(value)}" for key, value in values.items())


async def scalar(client: AGEClient, query: str, key: str = "cnt") -> int:
    rows = await client.run_query(query)
    if not rows:
        return 0
    return int(rows[0].get(key) or 0)


async def rows(client: AGEClient, query: str) -> list[dict]:
    return await client.run_query(query)


async def seed_one(client: AGEClient, index: int) -> None:
    alert_id = f"{PREFIX}-{index:04d}"
    user_id = f"{PREFIX}-USER-{index:04d}"
    asset_id = f"{PREFIX}-ASSET-{index:04d}"
    exists = await scalar(
        client,
        f"MATCH (a:Alert {{alert_id: {_S(alert_id)}}}) RETURN count(a) AS cnt",
    )
    if not exists:
        await client.run_query(
            "CREATE (u:User {"
            + props(
                {
                    "user_id": user_id,
                    "id": user_id,
                    "name": f"Diagnostic F2 User {index:04d}",
                    "origin": "diag_f2_seed",
                    "department": "SOC",
                    "risk_level": "critical",
                    "risk_score": 0.92,
                    "c9b_proof": True,
                    "diagnostic": "F2",
                }
            )
            + "})"
        )
        await client.run_query(
            "CREATE (asset:Asset {"
            + props(
                {
                    "asset_id": asset_id,
                    "id": asset_id,
                    "hostname": f"diag-f2-cred-{index:04d}",
                    "criticality": "critical",
                    "origin": "diag_f2_seed",
                    "asset_type": "workload",
                    "business_unit": "security",
                    "c9b_proof": True,
                    "diagnostic": "F2",
                }
            )
            + "})"
        )
        await client.run_query(
            "CREATE (a:Alert {"
            + props(
                {
                    "alert_id": alert_id,
                    "id": alert_id,
                    "category": "credential_access",
                    "alert_type": "anomalous_login",
                    "severity": "critical",
                    "risk_score": 0.92,
                    "status": "pending",
                    "origin": "diag_f2_seed",
                    "source": "diag_f2_seed",
                    "c9b_proof": True,
                    "diagnostic": "F2",
                    "timestamp_epoch": 1725000000000 + index,
                    "source_location": f"diag-f2-zone-{index % 6}",
                    "user_id": user_id,
                    "asset_id": asset_id,
                    "attack_pattern_id": "",
                    "mfa_completed": False,
                    "device_fingerprint_match": False,
                    "vpn_provider": "diag_f2_seed",
                }
            )
            + "})"
        )
    inv = await scalar(
        client,
        f"MATCH (a:Alert {{alert_id: {_S(alert_id)}}})-[r:INVOLVES]->(u:User {{user_id: {_S(user_id)}}}) RETURN count(r) AS cnt",
    )
    if not inv:
        await client.run_query(
            f"MATCH (a:Alert {{alert_id: {_S(alert_id)}}}), (u:User {{user_id: {_S(user_id)}}}) CREATE (a)-[:INVOLVES]->(u)"
        )
    det = await scalar(
        client,
        f"MATCH (a:Alert {{alert_id: {_S(alert_id)}}})-[r:DETECTED_ON]->(asset:Asset {{asset_id: {_S(asset_id)}}}) RETURN count(r) AS cnt",
    )
    if not det:
        await client.run_query(
            f"MATCH (a:Alert {{alert_id: {_S(alert_id)}}}), (asset:Asset {{asset_id: {_S(asset_id)}}}) CREATE (a)-[:DETECTED_ON]->(asset)"
        )


async def graph_counts(client: AGEClient) -> dict:
    queries = {
        "l5_centroid": "MATCH (c:L5Centroid) WHERE c.domain = 'soc' RETURN count(c) AS cnt",
        "shaped_by": "MATCH ()-[r:SHAPED_BY]->() RETURN count(r) AS cnt",
        "l5_dk_weight": "MATCH (w:L5DKWeight) WHERE w.domain = 'soc' RETURN count(w) AS cnt",
    }
    out = {}
    for key, query in queries.items():
        out[key] = await scalar(client, query)
    dk_rows = await rows(
        client,
        "MATCH (w:L5DKWeight) WHERE w.domain = 'soc' RETURN "
        "w.n_decisions_used AS n_decisions_used, "
        "w.confirmed_mean_json IS NOT NULL AS confirmed_mean_json, "
        "w.confirmed_m2_json IS NOT NULL AS confirmed_m2_json, "
        "w.overridden_mean_json IS NOT NULL AS overridden_mean_json, "
        "w.overridden_m2_json IS NOT NULL AS overridden_m2_json, "
        "w.all_mean_json IS NOT NULL AS all_mean_json, "
        "w.all_m2_json IS NOT NULL AS all_m2_json "
        "LIMIT 5"
    )
    out["dk_rows"] = dk_rows
    out["welford_present"] = bool(
        dk_rows
        and all(
            dk_rows[0].get(field) is True
            for field in (
                "confirmed_mean_json",
                "confirmed_m2_json",
                "overridden_mean_json",
                "overridden_m2_json",
                "all_mean_json",
                "all_m2_json",
            )
        )
    )
    return out


async def learning_state(client: AGEClient) -> dict:
    status, body = http_json("GET", "/api/triage/learning-state?" + urlencode({"category": "credential_access"}), timeout=20)
    if status == 404:
        status, body = http_json("GET", "/api/soc/learning-state?" + urlencode({"category": "credential_access"}), timeout=20)
    counts = await graph_counts(client)
    return {"status": status, "body": body, **counts}


async def analyze_outcome(alert_id: str) -> dict:
    start = time.perf_counter()
    a_status, analyze = http_json("POST", "/api/alert/analyze", {"alert_id": alert_id}, timeout=30)
    elapsed_analyze = time.perf_counter() - start
    recommendation = analyze.get("recommendation") if isinstance(analyze.get("recommendation"), dict) else {}
    gae_scoring = analyze.get("gae_scoring") if isinstance(analyze.get("gae_scoring"), dict) else {}
    alert = analyze.get("alert") if isinstance(analyze.get("alert"), dict) else {}
    provenance = analyze.get("provenance") if isinstance(analyze.get("provenance"), dict) else {}
    decision_id = (
        analyze.get("decision_id")
        or recommendation.get("decision_id")
        or gae_scoring.get("decision_id")
        or provenance.get("decision_id")
    )
    action = (
        analyze.get("action")
        or analyze.get("recommended_action")
        or recommendation.get("action")
        or provenance.get("action")
    )
    category = analyze.get("category") or alert.get("category") or provenance.get("category")
    confidence = analyze.get("confidence") or recommendation.get("confidence")
    result = {
        "alert_id": alert_id,
        "analyze_status": a_status,
        "category": category,
        "action": action,
        "confidence": confidence,
        "decision_id": decision_id,
        "elapsed_analyze": elapsed_analyze,
    }
    if a_status != 200 or not decision_id:
        result["outcome_status"] = None
        return result
    if action not in SCORER_ACTIONS:
        result["outcome_status"] = "skipped"
        return result
    o_status, outcome = http_json(
        "POST",
        "/api/alert/outcome",
        {
            "alert_id": alert_id,
            "decision_id": decision_id,
            "outcome": "correct",
            "analyst_action": action,
        },
        timeout=30,
    )
    result["outcome_status"] = o_status
    result["outcome"] = outcome
    result["elapsed_total"] = time.perf_counter() - start
    return result


async def final_readback(client: AGEClient) -> dict:
    query_outputs = {}
    query_outputs["diag_decisions"] = await rows(
        client,
        f"MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) "
        f"WHERE d.domain = 'soc' AND a.alert_id STARTS WITH {_S(PREFIX)} "
        "RETURN count(d) AS cnt"
    )
    query_outputs["verified_correct"] = await rows(
        client,
        f"MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) "
        f"WHERE d.domain = 'soc' AND a.alert_id STARTS WITH {_S(PREFIX)} "
        "AND d.outcome = 'correct' AND d.correct = true RETURN count(d) AS cnt"
    )
    query_outputs["by_category"] = await rows(
        client,
        f"MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert) "
        f"WHERE d.domain = 'soc' AND a.alert_id STARTS WITH {_S(PREFIX)} "
        "RETURN d.category AS category, count(d) AS cnt ORDER BY category"
    )
    query_outputs["l5_centroid"] = await rows(
        client, "MATCH (c:L5Centroid) WHERE c.domain = 'soc' RETURN count(c) AS cnt"
    )
    query_outputs["shaped_by"] = await rows(
        client, "MATCH ()-[r:SHAPED_BY]->() RETURN count(r) AS cnt"
    )
    query_outputs["l5_dk_weight"] = await rows(
        client, "MATCH (w:L5DKWeight) WHERE w.domain = 'soc' RETURN count(w) AS cnt"
    )
    query_outputs["l5_dk_weight_fields"] = await rows(
        client,
        "MATCH (w:L5DKWeight) WHERE w.domain = 'soc' RETURN "
        "w.n_decisions_used AS n_decisions_used, "
        "w.confirmed_mean_json IS NOT NULL AS confirmed_mean_json, "
        "w.confirmed_m2_json IS NOT NULL AS confirmed_m2_json, "
        "w.overridden_mean_json IS NOT NULL AS overridden_mean_json, "
        "w.overridden_m2_json IS NOT NULL AS overridden_m2_json, "
        "w.all_mean_json IS NOT NULL AS all_mean_json, "
        "w.all_m2_json IS NOT NULL AS all_m2_json, "
        "w.updated_at_epoch AS updated_at_epoch LIMIT 10"
    )
    query_outputs["l5_conservation"] = await rows(
        client,
        "MATCH (cs:L5ConservationState) WHERE cs.domain = 'soc' RETURN "
        "cs.status AS status, cs.alpha AS alpha, cs.q AS q, cs.V AS V, "
        "cs.theta_min AS theta_min, cs.categories_with_data AS categories_with_data LIMIT 10",
    )
    return query_outputs


async def main() -> int:
    started = time.time()
    client = AGEClient()
    summary: dict = {
        "model": "gpt-5.3",
        "base_url": BASE_URL,
        "graph": GRAPH,
        "prefix": PREFIX,
        "seed_batches": [],
        "progress": [],
        "milestones": {},
        "errors": [],
    }

    for batch_start in range(1, 301, 25):
        batch_end = min(300, batch_start + 24)
        for index in range(batch_start, batch_end + 1):
            await seed_one(client, index)
        count = await scalar(
            client,
            f"MATCH (a:Alert) WHERE a.alert_id STARTS WITH {_S(PREFIX)} RETURN count(a) AS cnt",
        )
        h_status, h_body = http_json("GET", "/health", timeout=10)
        batch = {"range": [batch_start, batch_end], "readback_count": count, "health_status": h_status, "health": h_body}
        summary["seed_batches"].append(batch)
        print("SEED_BATCH " + json.dumps(batch, sort_keys=True), flush=True)
        if h_status != 200:
            summary["verdict"] = "SEED_RUNTIME_FAILURE"
            print("SUMMARY_JSON " + json.dumps(summary, sort_keys=True), flush=True)
            return 2

    summary["final_seed_count"] = await scalar(
        client,
        f"MATCH (a:Alert) WHERE a.alert_id STARTS WITH {_S(PREFIX)} RETURN count(a) AS cnt",
    )
    if summary["final_seed_count"] != 300:
        summary["verdict"] = "SEED_RUNTIME_FAILURE"
        print("SUMMARY_JSON " + json.dumps(summary, sort_keys=True), flush=True)
        return 2

    sanity = await analyze_outcome(f"{PREFIX}-0001")
    sanity["learning_state"] = await learning_state(client)
    summary["one_loop"] = sanity
    print("ONE_LOOP " + json.dumps(sanity, sort_keys=True), flush=True)
    if sanity.get("category") != "credential_access" or sanity.get("action") == "refer_to_analyst":
        summary["verdict"] = "SEED_DATA_ISSUE"
        print("SUMMARY_JSON " + json.dumps(summary, sort_keys=True), flush=True)
        return 3
    if sanity.get("outcome_status") != 200:
        summary["verdict"] = "REQUEST_FORMAT_ISSUE"
        print("SUMMARY_JSON " + json.dumps(summary, sort_keys=True), flush=True)
        return 4
    if sanity.get("elapsed_total", 999) > 10:
        summary["verdict"] = "UNEXPECTED_RUNTIME_ERROR"
        summary["errors"].append("one-loop elapsed_total exceeded 10 seconds")
        print("SUMMARY_JSON " + json.dumps(summary, sort_keys=True), flush=True)
        return 5

    valid = 0
    attempts = 0
    skipped_referral = 0
    other_categories = 0
    failures = 0
    for index in range(2, 301):
        attempts += 1
        alert_id = f"{PREFIX}-{index:04d}"
        result = await analyze_outcome(alert_id)
        action = result.get("action")
        category = result.get("category")
        if result.get("analyze_status") != 200 or not result.get("decision_id"):
            failures += 1
            summary["errors"].append({"alert_id": alert_id, "stage": "analyze", "result": result})
            continue
        if category != "credential_access":
            other_categories += 1
            continue
        if action == "refer_to_analyst" or action not in SCORER_ACTIONS:
            skipped_referral += 1
            continue
        if result.get("outcome_status") == 200:
            valid += 1
        else:
            failures += 1
            summary["errors"].append({"alert_id": alert_id, "stage": "outcome", "result": result})
            continue

        cumulative_target = valid + 1
        if valid % 25 == 0:
            progress = {
                "long_loop_valid": valid,
                "cumulative_target_including_one_loop": cumulative_target,
                "attempts": attempts,
                "last_alert": alert_id,
                "elapsed_seconds": round(time.time() - started, 3),
            }
            summary["progress"].append(progress)
            print("PROGRESS " + json.dumps(progress, sort_keys=True), flush=True)
        if valid in MILESTONES or cumulative_target in MILESTONES:
            key = str(valid if valid in MILESTONES else cumulative_target)
            state = await learning_state(client)
            state.update(
                {
                    "long_loop_valid": valid,
                    "cumulative_target_including_one_loop": cumulative_target,
                    "attempts": attempts,
                    "last_alert": alert_id,
                }
            )
            summary["milestones"][key] = state
            print("MILESTONE " + key + " " + json.dumps(state, sort_keys=True), flush=True)
        if valid >= 250:
            break

    summary["run_summary"] = {
        "attempts": attempts,
        "valid_target_outcomes": valid,
        "cumulative_target_outcomes_including_one_loop": valid + 1,
        "refer_to_analyst_skipped": skipped_referral,
        "other_categories": other_categories,
        "failures": failures,
        "one_uninterrupted_process": True,
    }
    summary["final_readback"] = await final_readback(client)
    dk_count = int((summary["final_readback"]["l5_dk_weight"] or [{"cnt": 0}])[0].get("cnt") or 0)
    dk_fields = summary["final_readback"]["l5_dk_weight_fields"]
    welford_present = bool(
        dk_fields
        and all(
            dk_fields[0].get(field) is True
            for field in (
                "confirmed_mean_json",
                "confirmed_m2_json",
                "overridden_mean_json",
                "overridden_m2_json",
                "all_mean_json",
                "all_m2_json",
            )
        )
    )
    phases = [
        (key, value.get("body", {}).get("phase"))
        for key, value in summary["milestones"].items()
        if isinstance(value.get("body"), dict)
    ]
    has_variance = any(phase == "VARIANCE_LEARNING" for _, phase in phases)
    if valid < 230:
        summary["verdict"] = "TARGET_CATEGORY_NOT_REACHED"
    elif dk_count <= 0:
        summary["verdict"] = "L5DKWEIGHT_MISSING"
    elif not welford_present:
        summary["verdict"] = "WELFORD_MISSING"
    elif not has_variance and dk_count <= 0:
        summary["verdict"] = "PHASE_TRANSITION_MISSING"
    else:
        summary["verdict"] = "DIAGNOSTIC_F_PASS"
    print("SUMMARY_JSON " + json.dumps(summary, sort_keys=True), flush=True)
    return 0 if summary["verdict"] == "DIAGNOSTIC_F_PASS" else 10


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
