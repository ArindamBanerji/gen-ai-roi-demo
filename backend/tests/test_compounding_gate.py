#!/usr/bin/env python3
"""
10-cycle compounding verification gate.

Runs 10 analyze→outcome cycles against the live backend, then asserts 7 gates
that prove the compounding learning pipeline is working end-to-end.

Cycle schedule:
  Cycles 1-6  : anomalous_login alerts, correct outcomes
                (same alert_type drives PatternHistoryFactor accumulation)
  Cycles 7-8  : phishing alerts, correct outcomes
  Cycle  9    : malware_detection alert, INCORRECT outcome (tests 20:1 penalty)
  Cycle  10   : phishing alert, correct outcome (tests W recovery)

Gate summary:
  Gate 1: W matrix evolved — ||W_final - W_initial||_F > 0.001
  Gate 2: PatternHistory accumulates — ph_cycle6 > ph_cycle1
          (PH = 0.5 for cycles 1-5 due to _MIN_DECISIONS=5;
           PH = 1.0 for cycle 6 when 5 prior correct outcomes exist)
  Gate 3: 20:1 asymmetric delta — delta_norm(cycle9) / delta_norm(cycle8) > 10
  Gate 4: W updates after cycle 10 correct — delta_norm(cycle10) > 0
  Gate 5: Final W_norm differs from initial W_norm
  Gate 6: decision_count == 10 (all outcomes stored in LearningState)
  Gate 7: history total == 10 (WeightUpdate records complete)

Usage:
    cd backend && python tests/test_compounding_gate.py

Prerequisites:
    Backend running at http://localhost:8000 (uvicorn app.main:app --port 8000)
    pip install requests
"""

import math
import sys

import requests

BASE = "http://localhost:8000/api"
TIMEOUT = 30  # seconds per request

# ---------------------------------------------------------------------------
# Alert schedule: 10 different IDs.
#
# First 6 are anomalous_login so PatternHistoryFactor can accumulate:
#   PatternHistoryFactor._MIN_DECISIONS = 5 — factor returns 0.5 until
#   5+ resolved decisions exist for the alert_type.  After cycle 5's
#   outcome is committed, cycle 6's ANALYZE call sees 5 prior correct
#   anomalous_login decisions → PatternHistory = 5/5 = 1.0.
#
# Cycle 9 uses a different type (malware_detection) and is INCORRECT to
# exercise the 20:1 asymmetric penalty (LAMBDA_NEG = 20.0).
# ---------------------------------------------------------------------------

ALERT_SCHEDULE = [
    # (alert_id,       alert_type,          outcome)
    ("ALERT-7823", "anomalous_login",    "correct"),   # cycle 1  — PH=0.5 (0 prior)
    ("ALERT-7820", "anomalous_login",    "correct"),   # cycle 2  — PH=0.5 (1 prior <5)
    ("ALERT-7830", "anomalous_login",    "correct"),   # cycle 3  — PH=0.5 (2 prior <5)
    ("ALERT-7835", "anomalous_login",    "correct"),   # cycle 4  — PH=0.5 (3 prior <5)
    ("ALERT-7841", "anomalous_login",    "correct"),   # cycle 5  — PH=0.5 (4 prior <5)
    ("ALERT-7845", "anomalous_login",    "correct"),   # cycle 6  — PH=1.0 (5 prior >=5!)
    ("ALERT-7822", "phishing",           "correct"),   # cycle 7
    ("ALERT-7819", "phishing",           "correct"),   # cycle 8  — delta_norm reference
    ("ALERT-7821", "malware_detection",  "incorrect"), # cycle 9  — INCORRECT → 20x penalty
    ("ALERT-7824", "phishing",           "correct"),   # cycle 10 — recovery step
]

# Factor vector index for pattern_history.
# Order from SOCDomainConfig.get_factor_computers():
#   [0] TravelMatchFactor          → "travel_match"
#   [1] AssetCriticalityFactor     → "asset_criticality"
#   [2] ThreatIntelEnrichmentFactor→ "threat_intel_enrichment"
#   [3] PatternHistoryFactor       → "pattern_history"   ← index 3
#   [4] TimeAnomalyFactor          → "time_anomaly"
#   [5] DeviceTrustFactor          → "device_trust"
PATTERN_HISTORY_IDX_DEFAULT = 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get(path: str) -> dict:
    resp = requests.get(f"{BASE}{path}", timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def post(path: str, body: dict) -> dict:
    resp = requests.post(f"{BASE}{path}", json=body, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def frobenius(matrix_a: list, matrix_b: list) -> float:
    """||A - B||_F for two list-of-lists matrices of the same shape."""
    total = 0.0
    for row_a, row_b in zip(matrix_a, matrix_b):
        for a, b in zip(row_a, row_b):
            total += (a - b) ** 2
    return math.sqrt(total)


def w_norm(matrix: list) -> float:
    """Frobenius norm of a list-of-lists matrix."""
    return math.sqrt(sum(x * x for row in matrix for x in row))


# ---------------------------------------------------------------------------
# Main test runner
# ---------------------------------------------------------------------------

def run() -> None:  # noqa: C901 (allowed — it's a self-contained integration test)
    gate_results: list[tuple[int, str, bool, str]] = []
    failures: list[tuple[int, str, str]] = []

    def gate(num: int, label: str, passed: bool, detail: str = "") -> None:
        status = "PASS" if passed else "FAIL"
        line = f"  Gate {num}: [{status}] {label}"
        if detail:
            line += f"\n          {detail}"
        print(line)
        gate_results.append((num, label, passed, detail))
        if not passed:
            failures.append((num, label, detail))

    print("=" * 62)
    print("COMPOUNDING VERIFICATION GATE")
    print("=" * 62)

    # ================================================================
    # SETUP: comprehensive reset → clean Neo4j + clean LearningState
    # ================================================================
    print("\n[SETUP] POST /demo/reset-all ...")
    post("/demo/reset-all", {})
    print("        Done — Neo4j re-seeded, all in-memory state cleared.\n")

    # Snapshot initial W before any learning
    initial_weights = get("/gae/weights")
    initial_W = initial_weights["W"]
    initial_wn = w_norm(initial_W)
    initial_decision_count = initial_weights["decision_count"]
    factor_names_from_api = initial_weights.get("factor_names", [])
    ph_idx = (
        factor_names_from_api.index("pattern_history")
        if "pattern_history" in factor_names_from_api
        else PATTERN_HISTORY_IDX_DEFAULT
    )
    print(
        f"[SETUP] W_norm={initial_wn:.4f}, decision_count={initial_decision_count}, "
        f"factor_names={factor_names_from_api}"
    )
    print(f"[SETUP] pattern_history at factor index {ph_idx}\n")

    # ================================================================
    # 10 CYCLES: analyze → outcome → record W state
    # ================================================================
    ph_by_cycle: dict[int, float] = {}         # cycle_num → PH value at analyze time
    delta_norm_by_decision: dict[int, float] = {}  # decision_number (1-based) → delta_norm
    w_norm_after_cycle: dict[int, float] = {}   # cycle_num → W_norm after outcome

    for cycle_idx, (alert_id, alert_type, outcome) in enumerate(ALERT_SCHEDULE):
        cycle_num = cycle_idx + 1
        print(f"--- Cycle {cycle_num:2d}/{len(ALERT_SCHEDULE)}: {alert_id} ({alert_type}, {outcome}) ---")

        # Step 1: Analyze
        analyze_resp = post("/alert/analyze", {"alert_id": alert_id})
        gae = analyze_resp.get("gae_scoring", {})
        fv = gae.get("factor_vector", [])
        factor_names = gae.get("factor_names", factor_names_from_api)

        # Re-check ph_idx in case factor_names changed (shouldn't, but defensive)
        if "pattern_history" in factor_names:
            ph_idx = factor_names.index("pattern_history")

        ph_val = fv[ph_idx] if fv and ph_idx < len(fv) else 0.5
        ph_by_cycle[cycle_num] = ph_val

        decision_id = (
            gae.get("decision_id")
            or analyze_resp.get("recommendation", {}).get("decision_id")
        )
        selected_action = max(
            gae.get("action_probabilities", {}).items(),
            key=lambda kv: kv[1],
            default=("?", 0.0),
        )
        print(
            f"        analyze: action={selected_action[0]}({selected_action[1]:.3f}), "
            f"fv={[round(v, 3) for v in fv]}, ph={ph_val:.3f}, decision_id={decision_id}"
        )

        # Step 2: Submit outcome
        outcome_resp = post(
            "/alert/outcome",
            {
                "alert_id": alert_id,
                "decision_id": decision_id,
                "outcome": outcome,
            },
        )
        print(f"        outcome: {outcome} -> consequence={outcome_resp.get('consequence', 'ok')}")

        # Step 3: Record post-outcome W state
        weights_resp = get("/gae/weights")
        wn_now = w_norm(weights_resp["W"])
        w_norm_after_cycle[cycle_num] = wn_now
        print(
            f"        W_norm={wn_now:.4f}, "
            f"decision_count={weights_resp['decision_count']}"
        )

    # ================================================================
    # POST-CYCLE: read history and final weights
    # ================================================================
    print("\n[POST-CYCLE] GET /gae/history ...")
    history_resp = get("/gae/history?limit=50")
    history = history_resp.get("history", [])
    total_history = history_resp.get("total", 0)
    print(f"             total={total_history}, entries={len(history)}")

    for entry in history:
        dn = entry["decision_number"]
        delta_norm_by_decision[dn] = entry["delta_norm"]

    final_weights = get("/gae/weights")
    final_W = final_weights["W"]
    final_decision_count = final_weights["decision_count"]
    final_wn = w_norm(final_W)

    # ================================================================
    # GATE ASSERTIONS
    # ================================================================
    print("\n" + "=" * 62)
    print("GATE RESULTS")
    print("=" * 62)

    # Gate 1: W matrix evolved — non-trivial Frobenius distance from initial
    diff = frobenius(initial_W, final_W)
    gate(
        1,
        "W matrix evolved after 10 cycles",
        diff > 0.001,
        f"||W_final - W_initial||_F = {diff:.4f}  (threshold > 0.001)",
    )

    # Gate 2: PatternHistory accumulates (cycle 1 PH=0.5 → cycle 6 PH=1.0)
    ph_c1 = ph_by_cycle.get(1, 0.5)
    ph_c6 = ph_by_cycle.get(6, 0.5)
    gate(
        2,
        "PatternHistory accumulates: ph_cycle6 > ph_cycle1",
        ph_c6 > ph_c1,
        f"ph_cycle1={ph_c1:.3f}  ph_cycle6={ph_c6:.3f}  "
        f"(expect 1.0 > 0.5 once >=5 resolved anomalous_login decisions exist)",
    )

    # Gate 3: 20:1 asymmetric penalty
    # Cycle 8 (correct) → decision_number 8
    # Cycle 9 (incorrect) → decision_number 9
    dn_correct   = delta_norm_by_decision.get(8)
    dn_incorrect = delta_norm_by_decision.get(9)

    if dn_correct is not None and dn_incorrect is not None and dn_correct > 1e-9:
        ratio = dn_incorrect / dn_correct
        gate(
            3,
            "20:1 asymmetric penalty: delta_norm(cycle9) / delta_norm(cycle8) > 10",
            ratio > 10.0,
            f"delta_norm(cycle8,correct)={dn_correct:.5f}  "
            f"delta_norm(cycle9,incorrect)={dn_incorrect:.5f}  "
            f"ratio={ratio:.1f}x  (expect ~20x, LAMBDA_NEG=20)",
        )
    else:
        gate(
            3,
            "20:1 asymmetric penalty: delta_norm(cycle9) / delta_norm(cycle8) > 10",
            False,
            f"Could not compute ratio: dn_correct={dn_correct}  dn_incorrect={dn_incorrect}",
        )

    # Gate 4: W updates after cycle 10 correct (recovery step recorded)
    dn_cycle10 = delta_norm_by_decision.get(10)
    wn_after_9  = w_norm_after_cycle.get(9, 0.0)
    wn_after_10 = w_norm_after_cycle.get(10, 0.0)
    gate(
        4,
        "W updates after cycle 10 correct (recovery step recorded)",
        dn_cycle10 is not None and dn_cycle10 > 1e-9,
        f"delta_norm(cycle10,correct)={dn_cycle10}  "
        f"W_norm: after_9={wn_after_9:.4f}  after_10={wn_after_10:.4f}",
    )

    # Gate 5: Final W_norm differs from initial W_norm
    gate(
        5,
        "Final W_norm differs from initial W_norm",
        abs(final_wn - initial_wn) > 0.001,
        f"initial_W_norm={initial_wn:.4f}  final_W_norm={final_wn:.4f}  "
        f"delta={final_wn - initial_wn:+.4f}",
    )

    # Gate 6: decision_count == 10
    gate(
        6,
        "decision_count == 10 (all outcomes stored in LearningState)",
        final_decision_count == 10,
        f"decision_count={final_decision_count}",
    )

    # Gate 7: history total == 10
    gate(
        7,
        "history total == 10 (WeightUpdate records complete)",
        total_history == 10,
        f"total={total_history}",
    )

    # ================================================================
    # SUMMARY
    # ================================================================
    print("\n" + "=" * 62)
    n_passed = sum(1 for _, _, ok, _ in gate_results if ok)
    n_total  = len(gate_results)
    print(f"RESULT: {n_passed}/{n_total} gates passed")

    if failures:
        print("\nFAILED GATES:")
        for num, label, detail in failures:
            print(f"  Gate {num}: {label}")
            if detail:
                print(f"    {detail}")
        print()
        sys.exit(1)
    else:
        print("\nAll gates passed. Compounding learning pipeline verified.\n")
        sys.exit(0)


if __name__ == "__main__":
    run()
