# SOC Copilot — Active Backlog

Items parked pending roadmap session answers. See also
`backend/tests/test_known_issues.py` for the full backlog registry.

---

## BACKLOG-031b — test_iks_above_70_after_alerts_reset

**Status:** PARKED — investigation complete, fix pending
**Priority:** P2 — must resolve before VPS deployment
**Discovered:** April 10, 2026
**File:** tests/test_iks_stability.py:176–205

**Skip condition:** Two guards, first one triggers:
1. `get_profile_scorer()` returns `None` → `pytest.skip("ProfileScorer not initialized — startup required")` (line 187–188)
2. `compute_iks(ps.mu)["current"] <= 70` → `pytest.skip(f"IKS baseline is {iks_before:.1f} ≤ 70")` (line 191–192)

The test never reaches guard 2 because guard 1 fires first.

**Current IKS value:** 75.9 via live API (`GET /api/soc/executive-narrative`), but `None` in the pytest process because `get_profile_scorer()` returns `None` when the FastAPI startup event has not fired.

**Root cause:** `get_profile_scorer()` depends on `init_learning_state()` which runs inside the FastAPI `@app.on_event("startup")` handler. When pytest imports the app via `TestClient(app)`, the startup event fires for HTTP-based tests (test 7 passes via `/api/soc/tab/2/content`), but **direct function calls** to `get_profile_scorer()` in tests 1, 2, 5, 6 find `None` because `init_learning_state()` requires a live AGE/Neo4j connection that isn't available in the test process.

Proof: test 7 (`test_alerts_reset_preserves_iks_above_threshold`) uses the same IKS logic but fetches via `client.get("/api/soc/tab/2/content")` — it **passes** because the HTTP handler initializes the scorer lazily.

**Why 4 tests skip, not just 1:** All tests in this file that call `get_profile_scorer()` directly skip:
- `test_alerts_reset_preserves_profile_scorer` — SKIPPED
- `test_alerts_reset_does_not_collapse_iks` — SKIPPED
- `test_iks_stable_after_learning_decisions` — SKIPPED
- `test_iks_above_70_after_alerts_reset` — SKIPPED (this one)

Only tests using `TestClient` HTTP calls or pure state_manager logic pass.

**Fix path:** Two options:
1. **Refactor tests to use HTTP endpoints** (like test 7 does) instead of calling `get_profile_scorer()` directly. This sidesteps the initialization issue entirely. Lowest risk.
2. **Add a test fixture** that calls `init_learning_state()` with a mock AGE client before the direct-call tests run. This requires either a real AGE connection or a mock that returns enough data for the scorer to initialize with IKS > 70.

**Key question for roadmap session:** Is this fixable with approach 1 (HTTP-only tests), or does the test intentionally validate the direct Python API path? If direct-API coverage is required, a mock AGE fixture with synthetic centroid data (mu drifted from mu_zero) is needed.

**Effort estimate:** ~30 minutes for approach 1 (HTTP rewrite). ~2 hours for approach 2 (mock AGE fixture with synthetic centroids).

**Note:** This is actually 4 skipped tests sharing one root cause, not 1. Fixing the initialization issue would recover all 4.

---

## BACKLOG-035 — {id:} → AGE property name migration

**Status:** DONE (April 11, 2026)

**Root cause:** AGE-migrated data uses `alert_id` for Alert nodes and `decision_id` for Decision nodes, but all Cypher queries in the codebase used Neo4j convention `{id: ...}`. MATCH queries silently returned zero rows, causing Decision CREATE to fail, outcome write-back to miss, and factor/campaign/enrichment queries to return empty results.

**Files fixed:**
- `app/routers/triage.py` (7 locations — Alert MATCH, Decision CREATE/MATCH/SET)
- `app/routers/soc.py` (2 locations — Decision detail + TI lookup)
- `app/routers/graph.py` (1 location — enrichment query)
- `app/routers/evolution.py` (1 location — Decision CREATE)
- `app/db/neo4j.py` (5 locations — security context, create_decision, playbook link, evolution, get_alert)
- `app/domains/soc/factors.py` (3 locations — asset criticality, threat intel, campaign factor)
- `app/domains/soc/campaigns.py` (4 locations — alert event, member_of edges, find/join campaign)
- `app/framework/shadow_mode.py` (2 locations — shadow decision, analyst action)
- `app/framework/provenance.py` (1 location — decision provenance)
- `app/connectors/pulsedive.py` (1 location — TI-alert link)
- `app/services/simulation.py` (2 locations — Decision CREATE + outcome)
- `app/services/threat_indicator.py` (2 locations — alert link + indicator lookup)
- `app/services/triage.py` (2 locations — TI query + alert_type lookup)
- `app/data/alert_pool.py` (11 locations — Alert MERGE/MATCH in seed data)

**Locations fixed:** 44 total (34 in this pass + 10 in prior session)

---

## BACKLOG-036 — ProfileScorer index 4 out of bounds

**Status:** FULLY DONE (April 11, 2026)

**Root cause:** `get_actions()` returns A=5 routing actions (includes `refer_to_analyst` at index 4); scoring layer requires A=4 classification actions only (`SCORER_ACTIONS`). Any call site that feeds an action index into `LearningState.update()` or `ProfileScorer.update()` must use `SCORER_ACTIONS` (A=4), not `get_actions()` (A=5).

**Fix part 1 (symptom fix):** Guard in `triage.py` outcome path skips `refer_to_analyst` in learning update. Also guarded `LEARNING_ENABLED` block and snapshot path against `wu = None`.

**Fix part 2 (root cause fix — `get_actions()` audit):**
All 5 call sites audited, 3 classified as SCORING and migrated to `SCORER_ACTIONS`:
- `triage.py:173` — analyze path: `actions` renamed to `scorer_actions`, zip with probabilities now A=4
- `triage.py:920` — outcome path: action_index derived from `SCORER_ACTIONS.index()`, not `get_actions().index()`
- `simulation.py:228` — split into `actions` (A=5 for W-matrix) and `scorer_actions` (A=4 for learning); learning update + ProfileScorer.update() gated by `in scorer_actions`

2 call sites confirmed ROUTING (correct as A=5):
- `gae.py:64` — labels W(5,6) matrix rows for API display
- `simulation.py:292` — W-matrix scoring via `score_alert(f_2d, W, actions, tau)`

---

## BACKLOG-040 — ORDER BY d.timestamp_epoch fails in AGE

**Status:** DONE (April 10, 2026)

**Root cause:** After aggregation (`count(d) AS cnt`), AGE cannot ORDER BY a property not in RETURN — must use the returned alias. Similarly, when `d.timestamp_epoch` is returned as `ts`, ORDER BY must reference `ts`, not `d.timestamp_epoch`.

**Files fixed:**
- `app/domains/soc/campaigns.py` (2 locations — lines 521, 545: `ORDER BY d.timestamp_epoch` → `ORDER BY ts`)
- `app/services/reconvergence_logger.py` (1 location — line 126: `ORDER BY d.timestamp_epoch DESC` → `ORDER BY cnt DESC`)

---

## BACKLOG-039 — Campaign write isoformat error (epoch int vs datetime)

**Status:** DONE (April 10, 2026)

**Root cause:** `_to_python_dt()` in `campaigns.py` only handled `neo4j.DateTime` and Python `datetime` objects. AGE returns epoch integers (milliseconds or seconds), so `campaign.first_seen` was a raw int — calling `.isoformat()` on it crashed.

**Fix:** Added epoch integer handling to `_to_python_dt()`:
```python
if isinstance(value, (int, float)) and value > 1e9:
    divisor = 1000 if value > 1e12 else 1
    return datetime.utcfromtimestamp(value / divisor)
```

**File fixed:** `app/domains/soc/campaigns.py` (lines 30–36)

---

## BACKLOG-038 — ThreatIntel MERGE parameterized SET (list values)

**Status:** DONE (April 10, 2026)

**Root cause:** AGE does not support passing list values as Cypher parameters. The `MERGE (ti:ThreatIntel ...)` query in `pulsedive.py` passed `risk_factors` (a Python list) directly as `$risk_factors`. AGE rejects non-scalar parameters in SET clauses.

**Fix:** Serialize `risk_factors` to a JSON string via `json.dumps()` before passing as parameter. Added `import json` to `pulsedive.py`.

**File fixed:** `app/connectors/pulsedive.py` (line 329: `json.dumps(ioc.get("risk_factors", []), sort_keys=True)`)

---

## BACKLOG-037 — Log strings say "Neo4j" instead of "AGE"

**Status:** DONE (April 10, 2026)

**Root cause:** After migrating from Neo4j to Apache AGE, all print/log strings still referenced "Neo4j". Misleading during debugging and log analysis.

**Fix:** Replaced "Neo4j" → "AGE" in all print/log strings across application code.

**Files fixed (22 locations):**
- `app/connectors/pulsedive.py` (1)
- `app/connectors/greynoise.py` (1)
- `app/connectors/crowdstrike_mock.py` (1)
- `app/main.py` (2)
- `app/routers/triage.py` (3)
- `app/routers/soc.py` (4 — 3 print + 1 source string)
- `app/routers/metrics.py` (9 — 7 print + 1 note string + 1 docstring)
- `app/services/triage.py` (1)

---

## BACKLOG-041 — simulation factor_vector string crash + metrics.py d.id second call site

**Status:** DONE (April 11, 2026)

**Fix 1:** simulation.py: json.loads() guard for factor_vector string→list (AGE serialization)
**Fix 2:** metrics.py:246 inline /compounding evolution events Cypher: d.id AS id → d.decision_id AS id
  (second call site — /metrics/evolution-events at line 494 was fixed in a prior pass)
  Caught by test_compounding_evolution_uses_correct_property in test_age_contracts.py

---

## BACKLOG-042 — Simulation W_matrix attractor state

**Status:** DONE (April 11, 2026)

**Root cause:** Three referral alerts (SIM-CA-REF-001, SIM-LM-REF-001, SIM-CI-REF-001) appeared
consecutively at steps 24-26 in the simulation pool. The W_matrix took a large negative update
from oracle_outcome=-1 on refer_to_analyst predictions, pushing the matrix into a region where
refer_to_analyst scored highest for every factor_vector. Because refer_to_analyst is not in
SCORER_ACTIONS, no corrective centroid signal could pull the matrix out. W_matrix frozen from
step 26 onward, all 73 remaining steps predicted refer_to_analyst.

**Fix:** app/routers/simulation.py: filter refer_to_analyst alerts from simulation pool before
running. Pool 27→24 alerts. get_alert_pool() itself unchanged. Referral alerts remain in
production triage pool.

**Remaining latent issue:** simulation.py:295 still calls get_actions() (A=5) for the scoring
path — refer_to_analyst can still be selected by centroid geometry even without the referral
alerts. Should be changed to SCORER_ACTIONS (A=4). Low priority after pool filter fix.

---

## BACKLOG-043 — A=5 dual representation audit

**Status:** ABSORBED into Boundary Hardening Plan Phase 4 (BACKLOG-044)

---

## BACKLOG-044 — Boundary Hardening Plan (6 workstreams)

**Status:** OPEN — P1 before VPS
**Effort:** ~13.5 hours across 3-4 sessions
**Document:** systemic_fix_plan_april11.md

**Root cause diagnosis:** Every bug found April 8-11 was the same class — unvalidated data
crossing a layer boundary. Three boundaries, three fixes.

**Workstreams:**
- WS-1: ci-platform AGEClient _normalize_value + serialize_for_age + 25 tests (2h)
- WS-2: SOC backend Pydantic response models for 10 endpoints (3h)
- WS-3: SOC frontend guards.ts: ensureArray, ensureNumber, safeKey (1.5h)
- WS-4: Dual representation cleanup — single source for action space (2h)
- WS-5: GAE API_CONTRACT.md + TEST_CATEGORIES.md + 20 contract tests (3h)
- WS-6: S2P domain isolation + copilot-sdk discipline tests (2h)

**Gate before VPS:** All 6 workstreams complete, browser F12 console zero red errors.

---

## BACKLOG-045 — Audit chain breaks on E2E reset

**Status:** OPEN — P3, before VPS
**Discovered:** April 11, 2026

**Root cause:** decision_flow.spec.ts calls POST /api/alerts/reset in beforeEach (line 15).
Reset clears the in-memory audit ledger and starts a new hash chain from a fresh genesis hash.
Any session that runs E2E tests will show verify_chain → verified=False because decisions
before and after reset form disconnected chains with non-linking hashes.

**NOT a production bug.** POST /api/alerts/reset is a dev/test operation only. In production
the reset endpoint is never called mid-session.

**Test documenting behavior:** backend/tests/test_audit_chain.py
  test_audit_chain_breaks_after_reset: asserts verified=False after reset — documents the
  known failure mode, not asserts correctness.

**Architectural fix (two parts):**
Part 1 — On reset: archive+epoch rather than clear. Each epoch independently verifiable.
Part 2 — On startup: rebuild hash chain from AGE Decision nodes ordered by timestamp.
  After rebuild, in-memory chain is consistent with AGE and verify_chain returns True.
  Also fixes session restart survival (IKS and decision counts survive WSL2 reboot).
Effort: ~1 day. Must complete before VPS deployment.

---

## BACKLOG-046 — internal_scan_ambiguous has no category mapping

**Status:** OPEN — P1
**Discovered:** April 11, 2026

**Symptom:** Backend log: [MITRE] Unrecognized alert_type='internal_scan_ambiguous' — no technique mapped
  [H7-FIX-1] Could not determine category for alert SIM-LM-REF-001, using default pattern
  [TRIAGE] Confidence snapshot: unknown confidence=78.46%

**Fix:** Map alert_type='internal_scan_ambiguous' → category='lateral_movement' in the
alert_type→category mapping table used by H7-FIX-1 and the MITRE technique mapper.
File: find with Select-String -Pattern "internal_scan_ambiguous|alert_type.*category"

---

## BACKLOG-047 — Trust signal reads alert_type not category

**Status:** OPEN — P2
**Discovered:** April 11, 2026

**Symptom:** Backend log: [TRUST] travel_login_anomaly: 0.230 -> 0.260 firing for
  SIM-LM-REF-001 (a lateral_movement alert, not a travel_login alert).
  Trust system reads alert.alert_type instead of alert.category.

**Fix:** Find trust signal update path. Change field read from alert_type to category.
  Trust updates should be keyed on threat category (credential_access, lateral_movement, etc.)
  not on the raw alert_type string.
