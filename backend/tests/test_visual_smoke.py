#!/usr/bin/env python3
"""
Visual smoke test — verify frontend + backend still work after GAE integration.

Tests the full API surface with one analyze+outcome cycle, then resets
and checks Tab 2 / compounding endpoints still respond correctly.

Usage:
    cd backend && python tests/test_visual_smoke.py

Server must be running:
    uvicorn app.main:app --reload --port 8000
"""

import sys
import requests
from requests.exceptions import RequestException

BASE = "http://localhost:8000"
TIMEOUT = 45  # seconds — generous for endpoints that hit Neo4j

results: list[bool] = []


def call(method: str, path: str, **kwargs) -> requests.Response | None:
    """Make an HTTP request, returning None on timeout/connection error."""
    kwargs.setdefault("timeout", TIMEOUT)
    try:
        return requests.request(method, f"{BASE}{path}", **kwargs)
    except RequestException as exc:
        print(f"  [REQUEST ERROR] {method} {path}: {exc}")
        return None


def test(name: str, passed: bool, detail: str = "") -> bool:
    status = "PASS" if passed else "FAIL"
    line = f"  {status} -- {name}"
    if detail:
        line += f" ({detail})"
    print(line)
    results.append(passed)
    return passed


# ============================================================================
# 0. Pre-flight reset — ensures idempotent runs regardless of prior state
# ============================================================================

r = call("POST", "/api/demo/reset-all", timeout=90)
if r is None or r.status_code != 200:
    print(f"  [WARN] Pre-flight reset failed (status={r.status_code if r else 'TIMEOUT'}), continuing anyway")

# ============================================================================
# 1. Health check
# ============================================================================

r = call("GET", "/health")
test("Health check",
     r is not None and r.status_code == 200 and r.json().get("status") == "healthy",
     f"status={r.json().get('status') if r else 'NO RESPONSE'}")

# ============================================================================
# 2. Domain registry
# ============================================================================

r = call("GET", "/api/demo/domains")
if r is not None and r.status_code == 200:
    data = r.json()
    test("Domain registry",
         data.get("active_domain") == "soc",
         f"active_domain={data.get('active_domain')}  "
         f"registered={list(data.get('registered_domains', {}).keys())}")
else:
    test("Domain registry", False,
         f"status={r.status_code if r else 'TIMEOUT'}")

# ============================================================================
# 3. Alert queue — returns {"alerts": [...]}
# ============================================================================

r = call("GET", "/api/alerts/queue")
if r is not None and r.status_code == 200:
    alerts = r.json().get("alerts", [])
    test("Alert queue", len(alerts) >= 3, f"count={len(alerts)}")
else:
    alerts = []
    test("Alert queue", False, f"status={r.status_code if r else 'TIMEOUT'}")

alert_id = alerts[0]["id"] if alerts else "ALERT-7823"

# ============================================================================
# 4-9. GAE scoring pipeline — POST /api/alert/analyze
# ============================================================================

r = call("POST", "/api/alert/analyze", json={"alert_id": alert_id})
if r is not None and r.status_code == 200:
    analyze = r.json()
else:
    analyze = {}
gae = analyze.get("gae_scoring", {})

# 4. GAE section present
test("GAE scoring block in analyze response",
     bool(analyze) and "gae_scoring" in analyze,
     f"keys={list(analyze.keys())[:5]}")

# 5. Decision ID plumbed through
decision_id = (gae.get("decision_id")
               or analyze.get("recommendation", {}).get("decision_id"))
test("Decision ID returned",
     bool(decision_id),
     f"decision_id={decision_id}")

# 6. Softmax sums to 1.0
probs = gae.get("action_probabilities", {})
prob_sum = sum(probs.values()) if probs else 0.0
test("Softmax probabilities sum to ~1.0",
     abs(prob_sum - 1.0) < 0.01,
     f"sum={prob_sum:.6f}  actions={list(probs.keys())}")

# 7. Low confidence flag (GAE-3b)
test("low_confidence flag present",
     "low_confidence" in gae,
     f"low_confidence={gae.get('low_confidence')}")

# 8. Ambiguous flag (GAE-3b)
test("ambiguous flag present",
     "ambiguous" in gae,
     f"ambiguous={gae.get('ambiguous')}")

# 9. Decision method label (GAE-3b)
method = gae.get("decision_method", "")
test("decision_method label contains 'softmax'",
     "softmax" in method.lower(),
     f"method={method[:70]}")

# ============================================================================
# 10. Outcome feedback — POST /api/alert/outcome
# ============================================================================

if decision_id:
    r = call("POST", "/api/alert/outcome",
             json={"alert_id": alert_id,
                   "decision_id": decision_id,
                   "outcome": "correct"})
    if r is not None:
        test("Outcome feedback accepted",
             r.status_code == 200,
             f"status={r.status_code}  keys={list(r.json().keys())[:5]}")
    else:
        test("Outcome feedback accepted", False, "TIMEOUT")
else:
    test("Outcome feedback accepted", False, "skipped — no decision_id")

# ============================================================================
# 11-14. GAE endpoints after one outcome cycle
# ============================================================================

# 11. Weights
r = call("GET", "/api/gae/weights")
if r is not None and r.status_code == 200:
    weights = r.json()
    test("GAE /weights endpoint",
         "W" in weights and "decision_count" in weights,
         f"shape={weights.get('shape')}  decision_count={weights.get('decision_count')}")
else:
    weights = {}
    test("GAE /weights endpoint", False,
         f"status={r.status_code if r else 'TIMEOUT'}")

# 12. History — decision_count=1 < 3, so response is intentionally empty.
#     Smoke test verifies 200 + expected keys (empty is valid/by design).
r = call("GET", "/api/gae/history")
if r is not None and r.status_code == 200:
    hist = r.json()
    test("GAE /history endpoint (200 + valid structure)",
         "history" in hist and "total" in hist,
         f"total={hist.get('total')}  message={str(hist.get('message',''))[:50]}")
else:
    test("GAE /history endpoint (200 + valid structure)", False,
         f"status={r.status_code if r else 'TIMEOUT'}")

# 13. Convergence
r = call("GET", "/api/gae/convergence")
if r is not None and r.status_code == 200:
    conv = r.json()
    test("GAE /convergence endpoint",
         "stability" in conv and "converged" in conv,
         f"decisions={conv.get('decisions')}  converged={conv.get('converged')}  "
         f"stability={conv.get('stability', 0.0):.4f}")
else:
    conv = {}
    test("GAE /convergence endpoint", False,
         f"status={r.status_code if r else 'TIMEOUT'}")

# 14. decision_count incremented after outcome
test("decision_count incremented after outcome",
     weights.get("decision_count", 0) >= 1,
     f"decision_count={weights.get('decision_count')}")

# ============================================================================
# 15-16. Reset and verify clean state
# ============================================================================

r = call("POST", "/api/demo/reset-all", timeout=90)
test("Reset all (POST /api/demo/reset-all)",
     r is not None and r.status_code == 200,
     f"status={r.status_code if r else 'TIMEOUT'}")

r = call("GET", "/api/gae/convergence")
if r is not None and r.status_code == 200:
    conv_post = r.json()
    test("Post-reset: decisions == 0",
         conv_post.get("decisions", -1) == 0,
         f"decisions={conv_post.get('decisions')}")
else:
    test("Post-reset: decisions == 0", False,
         f"status={r.status_code if r else 'TIMEOUT'}")

# ============================================================================
# 17-18. Tab 2 still works (runtime evolution — old path, rule-based agent)
# ============================================================================

r = call("GET", "/api/deployments")
if r is not None and r.status_code == 200:
    test("Deployments (Tab 2)",
         "deployments" in r.json(),
         f"count={len(r.json().get('deployments', []))}")
else:
    test("Deployments (Tab 2)", False,
         f"status={r.status_code if r else 'TIMEOUT'}")

r = call("POST", "/api/alert/process", json={"alert_id": "ALERT-7823"})
test("Process alert (Tab 2)",
     r is not None and r.status_code == 200,
     f"status={r.status_code if r else 'TIMEOUT'}  "
     f"keys={list(r.json().keys())[:4] if r and r.status_code == 200 else '?'}")

# ============================================================================
# 19. Compounding metrics (Tab 4)
# ============================================================================

r = call("GET", "/api/metrics/compounding")
if r is not None and r.status_code == 200:
    comp = r.json()
    test("Compounding metrics",
         "weekly_trend" in comp,
         f"weeks={len(comp.get('weekly_trend', []))}")
else:
    test("Compounding metrics", False,
         f"status={r.status_code if r else 'TIMEOUT'}")

# ============================================================================
# Summary
# ============================================================================

passed = sum(results)
total = len(results)
print()
print("=" * 50)
print(f"VISUAL SMOKE TEST: {passed}/{total} passed")
print("=" * 50)
if passed < total:
    print("FAILURES PRESENT -- investigate before tagging")
    sys.exit(1)
else:
    print("ALL CLEAR -- safe to tag v4.1")
    sys.exit(0)
