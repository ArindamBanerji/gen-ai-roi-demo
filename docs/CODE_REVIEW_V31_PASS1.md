# Code Review v3.1.1 — Pass 1 (File-by-File)

**Reviewer:** Claude Opus 4.6 (different model, fresh eyes)
**Date:** 2026-02-24
**Codebase:** SOC Copilot Demo v3.1.1 (~12K lines, 30+ files)
**Purpose:** Ensure reliability for a 15-minute live demo in front of CISOs and VCs

---

## Executive Summary

**Overall assessment: DEMO-READY with caveats.**

The codebase is well-structured and the demo path works for the happy case (ALERT-7823 travel login → execute → feedback → Evidence Ledger). However, there are **3 HIGH-severity issues** that could cause visible problems during a live demo, particularly around the **reset flow** and **audit ledger integrity**. There are also **11 MEDIUM** findings (mostly Pydantic v2 deprecation warnings, timing issues, and cosmetic mismatches) and **8 LOW** findings.

**Severity counts:**

| Severity | Count | Summary |
|----------|-------|---------|
| CRITICAL | 0 | No demo-breaking bugs found in normal flow |
| HIGH | 3 | Reset doesn't clear audit/evolver state; version label wrong; stale UI after reset |
| MEDIUM | 11 | Pydantic `.dict()` deprecation (×4), dead code, missing timeout, timing races, cosmetic mismatches |
| LOW | 8 | Deprecated APIs, naming inconsistencies, code duplication, verbose logging |

**Top 3 fixes before recording the Loom:**
1. Add `reset_audit_decisions()` to audit.py and wire it into both reset endpoints
2. Change App.tsx "CISO Version v2.0" → "v3.1"
3. Clear `analysis` state in AlertTriageTab's `handleResetAlerts`

---

## Pass 1: File-by-File Findings

---

### TIER 1: Core Demo Path

---

#### 1. `backend/app/routers/triage.py` (~764 lines)

**[HIGH] H-1: `record_decision()` always stores `situation_type="unknown"` and empty `factors`**
- File: `routers/triage.py:219-222`
- In `execute_action()`:
  ```python
  record_decision(
      alert_id=alert_id,
      situation_type=context.get("situation_type", "unknown"),  # always "unknown"
      factors=list(context.get("factors_matched", [])),         # always []
  )
  ```
- The Neo4j security context (`get_security_context()`) never populates `situation_type` or `factors_matched`. The situation type comes from `analyze_situation()`, which is NOT called in the execute path.
- **Impact:** Evidence Ledger records created via the Execute button have `situation_type="unknown"` and empty factors. The current Tab 4 table doesn't display these fields (only shows Timestamp, Alert, Action, Outcome, Hash), so it's not visible during the demo. But the CSV export WILL show them.
- **Fix:** Call `analyze_situation()` in the execute path, or pass the correct values from the already-completed analysis.

**[MEDIUM] M-1: Dead code — `action` variable set but never used**
- File: `routers/triage.py:203`
  ```python
  action = request.deployment_version or "false_positive_close"  # Using this field for action
  ```
- The `action` variable is never referenced after this line. The function uses `decision.action` (from the agent) for all operations. The comment "Using this field for action" is misleading — no code uses this field.
- **Impact:** None (dead code), but confusing for anyone reading the code.
- **Fix:** Remove the dead line and comment.

**[MEDIUM] M-2: Reset endpoint doesn't clear `analysis` or `_analyzed_alerts` state**
- File: `routers/triage.py:312-355`
- `reset_demo_alerts()` resets Neo4j alerts, feedback, and policy state, but does NOT reset any analysis-related in-memory state. If `services/triage.py` maintains an `_analyzed_alerts` dict (for `get_decision_factors()`), it persists across resets.
- **Impact:** After reset, `get_decision_factors()` may still return stale factors for the previous analysis session.
- **Fix:** Add a reset function to `services/triage.py` and call it from the reset endpoint.

**[LOW] L-1: Policy check hardcodes context per alert_id instead of querying Neo4j**
- File: `routers/triage.py:463-481`
- The `/alert/policy-check` endpoint hardcodes security context for ALERT-7823 and ALERT-7824 rather than querying Neo4j.
- **Impact:** Works for the demo's fixed data, but fragile if seed data changes.

---

#### 2. `frontend/src/components/tabs/AlertTriageTab.tsx` (~1037 lines)

**[HIGH] H-2: `handleResetAlerts` doesn't clear `analysis` state**
- File: `AlertTriageTab.tsx:305-320`
  ```tsx
  const handleResetAlerts = async () => {
    setResetting(true)
    try {
      await resetAlerts()
      await loadAlertQueue()
      setClosedLoop(null)        // ✓ cleared
      setPolicyResolution(null)  // ✓ cleared
      setDecisionFactors(null)   // ✓ cleared
      // MISSING: setAnalysis(null)
      // MISSING: setActiveStep(0)
    } ...
  }
  ```
- After reset, `loadAlertQueue()` auto-selects the first alert but only calls `setSelectedAlert()` — it does NOT call `analyzeAlertHandler()`. So the old Recommendation panel, Situation Analyzer panel, and Graph Visualization remain visible with stale data.
- **Impact:** During a demo, if you reset alerts, the old analysis panels are still showing. The user must manually click an alert to refresh. Looks broken.
- **Fix:** Add `setAnalysis(null)` and `setActiveStep(0)` to the reset handler.

**[MEDIUM] M-3: `setTimeout` race conditions in `executeActionHandler`**
- File: `AlertTriageTab.tsx:285-295`
  ```tsx
  for (let i = 0; i < 4; i++) {
    setTimeout(() => setActiveStep(i + 1), i * 800)
  }
  setTimeout(loadAlertQueue, 3200)
  setTimeout(() => setExecuting(false), 3200)
  ```
- Four `setTimeout` calls without cleanup. If the component unmounts or the user switches tabs during the 3.2s animation, these will fire on unmounted state. No `useEffect` cleanup.
- **Impact:** Unlikely during a controlled demo, but could cause React state update warnings in the console.
- **Fix:** Use `useRef` for timeout IDs and clear them on unmount/reset.

**[LOW] L-2: Debug `useEffect` logging alerts state on every change**
- File: `AlertTriageTab.tsx:196-199`
- `console.log` on every alerts state update. Adds noise to console during demo.

---

#### 3. `backend/app/services/triage.py` (~284 lines)

**[LOW] L-3: `get_decision_factors()` always returns 6 factors even for unknown alerts**
- For alerts not matching ALERT-7823 or ALERT-7824, returns factors with `value=0.0` and `contribution="none"` for all 6 factors. This is functional but visually unimpressive if a third alert type is ever added.

No other issues found. The `_build_threat_intel_factor()` Neo4j query handles connection failures gracefully with a try/except fallback.

---

#### 4. `backend/app/services/audit.py` (~293 lines)

**[HIGH] H-3: No reset function — `_DECISIONS` list is never cleared**
- The audit module has no `reset_audit_decisions()` or equivalent function. Neither `/alerts/reset` nor `/demo/reset-all` clears `_DECISIONS`.
- **Impact:** After a demo reset:
  1. Old decision records persist in `_DECISIONS`
  2. User re-executes an alert → `record_decision()` appends a NEW record
  3. Evidence Ledger now shows duplicate records for the same alert
  4. Hash chain remains valid (new records chain correctly), but the duplicate is confusing
- **Fix:** Add a `reset_audit_state()` function that clears `_DECISIONS`. Wire it into both reset endpoints.
  ```python
  def reset_audit_state():
      """Clear all decision records (demo reset)."""
      _DECISIONS.clear()
      print("[AUDIT] Decision ledger cleared")
  ```

**[MEDIUM] M-4: `datetime.utcnow()` deprecated in Python 3.12+**
- File: `audit.py:142`, `audit.py:218`
- `datetime.utcnow()` is deprecated in Python 3.12+ in favor of `datetime.now(timezone.utc)`. Works on Python 3.11 (the target), but generates warnings on newer versions.

**[LOW] L-4: `reconstruct_from_memory()` uses only FEEDBACK_GIVEN data**
- If a decision was executed but no feedback was given, `reconstruct_from_memory()` won't create a record for it. Only the direct `record_decision()` call creates it. This is by design but worth documenting.

---

#### 5. `backend/app/routers/soc.py` (~637 lines)

**[MEDIUM] M-5: `sprawl_alert.dict()` uses deprecated Pydantic v1 method**
- File: `soc.py:546`
  ```python
  "sprawl_alert": sprawl_alert.dict() if sprawl_alert else None,
  ```
- Should be `.model_dump()` for Pydantic v2. Works via backward compatibility but generates deprecation warnings.

**[LOW] L-5: `match_metric()` keyword matching could match wrong metric**
- File: `soc.py:316-337`
- The keyword scoring is simple (count of keyword hits). If a question contains words from multiple metrics, the highest score wins. No word boundary checks — e.g., "escalation" would match `escalation_rate` but also partial matches in other metrics.
- **Impact:** For the 9 demo example questions, this works correctly. Custom questions might hit wrong metrics.

---

#### 6. `frontend/src/components/tabs/SOCAnalyticsTab.tsx` (~637 lines)

**[LOW] L-6: Threat Landscape panel error silently caught**
- The Threat Landscape panel hides on API error (not broken, just invisible). This is correct behavior for a demo — fail gracefully.

No other issues found. The cross-context table rendering and chart types are well-implemented.

---

### TIER 2: Supporting Demo Path

---

#### 7. `backend/app/services/feedback.py` (~312 lines)

**[MEDIUM] M-6: `.dict()` used instead of `.model_dump()`**
- File: `feedback.py:212`
  ```python
  "graph_updates": [u.dict() for u in graph_updates]
  ```
- Same Pydantic v2 deprecation as M-5.

**[LOW] L-7: Pattern ID naming inconsistency**
- `feedback.py` uses `PAT-PHISH-001` for phishing feedback tracking.
- `agent.py` returns `PAT-PHISH-KNOWN` as the pattern_id.
- `seed_neo4j.py` uses `PAT-PHISH-KNOWN` in the graph.
- These are independent in-memory systems so there's no functional bug, but it's confusing.

---

#### 8. `backend/app/services/policy.py` (~441 lines)

No issues found. The priority-based resolution logic is clean. ALERT-7823 correctly triggers a conflict (POL-AUTO-CLOSE-TRAVEL vs POL-ESCALATE-HIGH-RISK). ALERT-7824 correctly has no conflict.

---

#### 9. `frontend/src/lib/api.ts` (~211 lines)

**[LOW] L-8: Verbose console logging on every request and response**
- Every `fetchJSON` call logs the URL, status, and full response data to console.
- **Impact:** Console is noisy during demo. Could expose sensitive-looking data if audience sees dev tools.
- **Fix:** Wrap in `if (import.meta.env.DEV)` or remove before recording.

**[MEDIUM] M-7: `executeAction()` doesn't send the action — relies on agent re-running**
- File: `api.ts:99-103`
  ```tsx
  export async function executeAction(alertId: string) {
    return fetchJSON('/action/execute', {
      method: 'POST',
      body: JSON.stringify({ alert_id: alertId }),
    })
  }
  ```
- Only `alert_id` is sent. The backend re-runs the agent to get the action. This is correct for the current architecture but means the action shown on the Execute button (from the prior analysis) could theoretically differ from the action actually executed (from the new analysis) if state changed between analysis and execution.
- **Impact:** In practice this doesn't happen because the agent is deterministic and context doesn't change between analysis and execution. But it's architecturally fragile.

---

#### 10. `backend/app/services/agent.py` (~375 lines)

No bugs found. The rule-based decision engine is clean and deterministic. The 4-rule structure handles all demo alert types correctly.

**Observation:** The agent has a relaxed travel match path (line 88-94) — `user_traveling and vpn_matches` without MFA/device checks still returns `false_positive_close` at 0.88 confidence. This broadens the travel detection correctly.

---

#### 11. `backend/app/routers/audit.py` (~147 lines)

**[MEDIUM] M-8: CSV export doesn't include all fields**
- The CSV export via `GET /audit/decisions?format=csv` should be verified to include all fields. The endpoint converts JSON to CSV using field names from the first record. If the first record lacks `analyst_notes` (added dynamically), the CSV won't have that column.
- **Impact:** Minor — CSV export is a secondary feature.

---

#### 12. `backend/app/services/threat_intel.py` (~357 lines)

**[MEDIUM] M-9: `ALERT_IOC_MAP` only maps ALERT-7823**
- File: `threat_intel.py` (ALERT_IOC_MAP dict)
- Only ALERT-7823 gets IOC-to-alert association. ALERT-7824 (phishing) has no mapped IOC.
- **Impact:** The "Why This Decision?" panel for ALERT-7824 shows the threat_intel_enrichment factor with value 0.0 and contribution "none". The Threat Intel badge shows global indicators (5 IOCs loaded), but the per-alert factor is empty. This mismatch is visible but not technically wrong — just not as impressive for the phishing demo.

---

#### 13. `backend/app/routers/graph.py` (~42 lines)

No issues found. Simple endpoint that delegates to `threat_intel.refresh_threat_intel()`.

---

#### 14. `backend/app/services/seed_neo4j.py` (~364 lines)

**[MEDIUM] M-10: Uses CREATE (not MERGE) — destructive reseed**
- The seed function uses `MATCH (n) DETACH DELETE n` followed by CREATE statements. This is intentional (clean slate), but means:
  1. Any Decision/EvolutionEvent nodes created during the demo session are destroyed
  2. Running reseed during active API calls could cause transient errors
- **Impact:** The reseed is called by `/demo/reset-all` and `/demo/seed`. During a live demo, if Tab 2 "Process Alert" is running concurrently with a reset, the Neo4j state could be mid-delete. The Neo4j driver should handle this with transaction isolation, but it's worth noting.

---

#### 15. `frontend/src/components/tabs/CompoundingTab.tsx` (~920 lines)

**[MEDIUM] M-11: "Reset All Demo Data" doesn't reset audit or evolver in-memory state**
- The reset button calls `resetAllDemoData()` + `resetAlerts()`.
- `resetAllDemoData()` → POST `/demo/reset-all` → reseeds Neo4j only.
- `resetAlerts()` → POST `/alerts/reset` → resets feedback + policy state.
- **NOT reset:** `audit._DECISIONS`, `evolver.PROMPT_STATS`, `evolver.ACTIVE_PROMPTS`, `evolver.RECENT_PROMOTIONS`
- **Impact:**
  - Evidence Ledger shows records from before the reset (duplicates after re-execution)
  - Agent Evolver panel on Tab 2 shows accumulated stats instead of fresh state
- This is the frontend manifestation of H-3.

---

#### 16. `frontend/src/components/tabs/RuntimeEvolutionTab.tsx` (~922 lines)

No bugs found. The sequential eval gate animation (800ms delay), TRIGGERED_EVOLUTION panel, and Agent Evolver panel are well-implemented. The Loop 3 panel fetches reward summary correctly.

---

#### 17. `backend/app/routers/roi.py` (~283 lines)

No issues found. The ROI calculator correctly rejects `current_auto_close_pct >= 0.89` and the projections are reasonable.

---

#### 18. `frontend/src/components/ROICalculator.tsx` (~590 lines)

**[LOW] L-9: Duplicated `useCountUp` hook**
- The `useCountUp` hook is defined in both `CompoundingTab.tsx` and `ROICalculator.tsx`. Should be extracted to a shared utility.

---

### TIER 3: Infrastructure

---

#### 19. `backend/app/main.py` (~66 lines)

**[LOW] L-10: Deprecated `on_event` lifecycle**
- `@app.on_event("startup")` and `@app.on_event("shutdown")` are deprecated in favor of `lifespan` context manager.
- Works fine on current FastAPI version.

**[LOW] L-11: `load_dotenv(dotenv_path="../.env")` — relative path fragile**
- Depends on the working directory being `backend/`. If started from project root, the path won't resolve.
- Works in the demo's startup command (`cd backend && uvicorn ...`).

---

#### 20. `backend/app/models/schemas.py` (~196 lines)

No issues found. Pydantic v2 models are correctly defined.

**Observation:** `ProcessAlertRequest` has a `deployment_version` field that is used as an action parameter in triage.py (dead code, see M-1) and as a version string in evolution.py. The dual purpose is confusing.

---

#### 21. `backend/app/db/neo4j.py` (~293 lines)

**[MEDIUM] M-12: No query timeout**
- `run_query()` has no timeout parameter:
  ```python
  async def run_query(self, query, parameters=None):
      async with self.session() as session:
          result = await session.run(query, parameters or {})
          records = await result.data()
          return records
  ```
- If Neo4j Aura is slow or unresponsive, this hangs indefinitely. During a live demo, this would freeze the UI.
- **Fix:** Add a timeout to the session or use `asyncio.wait_for()`:
  ```python
  import asyncio
  records = await asyncio.wait_for(result.data(), timeout=10.0)
  ```

**[LOW] L-12: "47 nodes" count varies by 2-4 for different alert types**
- `get_security_context()` line 86: `base_nodes + 39 as nodes_consulted`
- For ALERT-7823 (travel, pattern, playbook, sla all present): base_nodes = 8, total = 47 ✓
- For ALERT-7824 (pattern, playbook, no travel, no sla): base_nodes ≈ 6, total = 45
- The AlertTriageTab header hardcodes "47 nodes consulted" in text, but the actual count shown is `[{analysis.context.nodes_count} nodes]` which could show 45.
- **Impact:** Minor visual inconsistency for non-travel alerts.

---

#### 22. `frontend/vite.config.ts` (~24 lines)

No issues found. Proxy correctly targets `http://localhost:8000`. Port 5173 for frontend. Ngrok domains allowed.

---

#### 23. `backend/app/services/reasoning.py` (~98 lines)

**[MEDIUM] M-13: Global `ReasoningNarrator` created at import time**
- File: `reasoning.py:97`
  ```python
  narrator = ReasoningNarrator()
  ```
- The constructor calls `vertexai.init()` and creates a `GenerativeModel`. If Vertex AI credentials are not configured (missing `PROJECT_ID` env var), this will crash the entire backend at import time, before any request is served.
- **Impact:** In the demo environment (credentials configured), this works fine. But anyone cloning the repo without Vertex AI credentials will get a crash on startup.
- **Fix:** Lazy initialization — create the model on first call, not at import time.

**[LOW] L-13: Fallback reasoning hardcodes "94% confidence"**
- File: `reasoning.py:74`
- `"Pattern PAT-TRAVEL-001 has 94% confidence"` is hardcoded even though the actual confidence changes with feedback (0.88–0.99 range).
- Only triggers if the LLM call fails, so unlikely during a demo.

---

#### 24. `backend/app/services/situation.py` (~491 lines)

No issues found. Clean, well-structured rule-based classification. All 6 situation types are handled. The `calculate_decision_economics()` function correctly compares against human baseline.

---

#### 25. `backend/app/services/evolver.py` (~360 lines)

**[LOW] L-14: No reset function for evolver state**
- `PROMPT_STATS`, `ACTIVE_PROMPTS`, and `RECENT_PROMOTIONS` are never cleared by any reset path.
- Related to H-3/M-11 — part of the incomplete reset problem.
- **Fix:** Add `reset_evolver_state()` function.

---

#### 26. `backend/app/routers/evolution.py` (~499 lines)

**[MEDIUM] M-14: `process_alert_blocked` creates real Decision nodes in Neo4j**
- File: `evolution.py:297-316`
- Clicking "Simulate Failed Gate" creates a real Decision node in Neo4j (with action "BLOCKED"). Clicking it repeatedly accumulates blocked decision nodes.
- **Impact:** During a demo, typically clicked once. But multiple clicks create noise in the graph.

---

#### 27. `backend/app/routers/metrics.py` (~367 lines)

**[MEDIUM] M-15: `.dict()` used instead of `.model_dump()` (×3)**
- File: `metrics.py:197` — `return data.dict()`
- File: `metrics.py:357` — `[e.dict() for e in events[:limit]]`
- Pydantic v2 deprecation warnings.

**[MEDIUM] M-16: `/demo/reset-all` only reseeds Neo4j — no in-memory state reset**
- File: `metrics.py:250-286`
- `reset_all_demo_data()` calls `seed_neo4j_database()` and `verify_neo4j_seed()` but does NOT reset feedback, policy, audit, or evolver state.
- The frontend compensates by also calling `/alerts/reset` (which resets feedback + policy), but audit and evolver are still missed.
- This is the backend manifestation of H-3.

**[LOW] L-15: `/demo/reset` (legacy) does nothing**
- File: `metrics.py:293-331`
- Returns a success message without actually resetting anything. The comment says "For this demo, it just returns a success message." This is unused dead code.

---

#### 28. `frontend/src/App.tsx` (~141 lines)

**[HIGH] H-4: Header shows "CISO Version v2.0" — should be v3.1**
- File: `App.tsx:75`
  ```tsx
  <div>CISO Version v2.0</div>
  ```
- The codebase is v3.1.1 but the header still shows v2.0. This is visible to the audience throughout the entire demo.
- **Fix:** Change to `v3.1` or `v3.0`.

---

#### 29. `frontend/src/components/OutcomeFeedback.tsx` (~274 lines)

No issues found. Correctly checks feedback status before showing buttons. Handles error states.

---

#### 30. `frontend/src/components/PolicyConflict.tsx` (~259 lines)

No issues found. Correctly detects and displays policy conflicts for ALERT-7823.

---

## Pass 2: Architecture Review (Cross-Cutting)

---

### A1. Reset Completeness

| State | `/alerts/reset` | `/demo/reset-all` | Combined |
|-------|-----|-----|-----|
| Neo4j alerts → pending | ✓ | ✓ (reseed) | ✓ |
| Neo4j Decision/Evolution nodes | ✗ | ✓ (reseed clears all) | ✓ |
| `feedback.FEEDBACK_GIVEN` | ✓ | ✗ | ✓ (via combined call) |
| `feedback.PATTERN_CONFIDENCE` | ✓ | ✗ | ✓ (via combined call) |
| `policy.CONFLICTS_RESOLVED` | ✓ | ✗ | ✓ (via combined call) |
| `audit._DECISIONS` | **✗** | **✗** | **✗ NOT RESET** |
| `evolver.PROMPT_STATS` | **✗** | **✗** | **✗ NOT RESET** |
| `evolver.ACTIVE_PROMPTS` | **✗** | **✗** | **✗ NOT RESET** |
| `evolver.RECENT_PROMOTIONS` | **✗** | **✗** | **✗ NOT RESET** |
| Frontend: analysis state | **✗** | **✗** | **✗ NOT RESET** |
| Frontend: closedLoop | ✓ | ✓ | ✓ |

**Verdict:** Reset is incomplete. Audit ledger and evolver state persist across resets.

---

### A2. Audit Chain Integrity

- Hash chain computation is correct: SHA-256 over (previous_hash + JSON of immutable fields).
- Mutable fields (outcome, analyst_confirmed) are correctly excluded from the hash.
- `verify_chain()` correctly walks the chain from genesis.
- **Risk:** Concurrent writes to `_DECISIONS` (e.g., two alerts executed simultaneously) could interleave and produce a valid chain, but the ordering might not match wall-clock time. In practice, the demo is single-user, so this is theoretical.
- **Risk:** After reset, old records persist and new records chain off the last old record. The chain is still valid, but there's no "break" indicating a reset occurred.

---

### A3. Decision Factor Consistency

- `services/triage.py` defines 6 factors with specific templates per alert type.
- `AlertTriageTab.tsx` renders all 6 factors with bar charts.
- The factors match between backend and frontend.
- **Gap:** The threat_intel_enrichment factor queries Neo4j for `ThreatIntel` nodes. For ALERT-7824, no IOC association exists, so the factor shows value 0.0 / contribution "none". This is technically correct but visually less impressive.

---

### A4. Threat Intel Data Flow

```
Pulsedive API → threat_intel.py → Neo4j (ThreatIntel nodes)
                                      ↓
                              ASSOCIATED_WITH → Alert
                                      ↓
                              services/triage.py queries for decision factors
                                      ↓
                              AlertTriageTab renders threat_intel_enrichment factor
```

- **End-to-end flow works** for ALERT-7823 (mapped to IOC 103.15.42.17).
- **Breaks** for ALERT-7824 — no IOC mapping, so the decision factor shows no enrichment.
- The Threat Intel badge (top of Tab 3) shows global indicators regardless of alert — this is correct.

---

### A5. Port Consistency

- `vite.config.ts`: proxy target = `http://localhost:8000` ✓
- `api.ts`: uses relative `/api` prefix (proxied) ✓
- No hardcoded `localhost:8001` references found ✓
- CLAUDE.md documents both 8000 (v3) and 8001 (v2) — v2 references are in the historical section, not the active config ✓

---

### A6. Pydantic v2 Deprecation

Four files use `.dict()` instead of `.model_dump()`:

| File | Line | Context |
|------|------|---------|
| `soc.py` | 546 | `sprawl_alert.dict()` |
| `feedback.py` | 212 | `u.dict() for u in graph_updates` |
| `metrics.py` | 197 | `data.dict()` |
| `metrics.py` | 357 | `e.dict() for e in events` |

These all generate `DeprecationWarning` in the console. They won't break the demo but add noise.

---

## Pass 3: Demo Resilience

---

| Scenario | Expected | Actual | Risk |
|----------|----------|--------|------|
| **Happy path: ALERT-7823 → Execute → Feedback → Evidence Ledger** | Works end-to-end | ✓ Works correctly | None |
| **Happy path: ALERT-7824 → Execute → Feedback** | Works end-to-end | ✓ Works correctly | None |
| **Pulsedive rate limited (429)** | Badge shows "Local fallback" | ✓ Fallback works | Low |
| **Execute then switch tabs** | Evidence Ledger shows record on Tab 4 refresh | ✓ Works (manual refresh needed) | Low |
| **Reset All then Tab 3** | 6 alerts, first auto-selected | ⚠ Alerts reload but old analysis panels remain | **Medium — see H-2** |
| **Reset then re-execute same alert** | Single clean record | ⚠ Duplicate records in Evidence Ledger | **Medium — see H-3** |
| **Click all 4 cross-context queries rapidly** | Each renders correctly | ✓ Previous query result replaced | Low |
| **Neo4j connection drops mid-demo** | All endpoints fall back to static data | ⚠ Most endpoints throw 500 errors. Only `soc.py:threat-landscape` and `evolution.py:get_recent_evolution` have fallbacks. | **Medium** |
| **Threat Landscape panel fails to load** | Tab 1 still shows query input | ✓ Panel hidden, query input visible | Low |
| **"Simulate Failed Gate" clicked multiple times** | Clean blocked state each time | ⚠ Accumulates Decision nodes in Neo4j | Low |
| **Vertex AI credentials missing** | Graceful fallback to static reasoning | ✗ Backend crashes at import time | **High if env not set** |

---

## Prioritized Fix List

### Before Loom Recording (30 min)

| # | Finding | Severity | Fix | Effort |
|---|---------|----------|-----|--------|
| 1 | H-3: Add `reset_audit_state()` to `audit.py` | HIGH | Add function + wire into both reset endpoints | 10 min |
| 2 | H-4: App.tsx version label "v2.0" → "v3.1" | HIGH | One-line change | 1 min |
| 3 | H-2: Clear `analysis` state on reset | HIGH | Add `setAnalysis(null); setActiveStep(0)` to `handleResetAlerts` | 2 min |
| 4 | L-14: Add `reset_evolver_state()` to `evolver.py` | LOW | Add function + wire into reset endpoints | 5 min |
| 5 | M-5/M-6/M-15: Replace `.dict()` with `.model_dump()` | MEDIUM | Find-and-replace across 4 files | 5 min |
| 6 | M-1: Remove dead `action` variable in triage.py | MEDIUM | Delete one line | 1 min |

### Before v4 Build (Optional)

| # | Finding | Severity | Fix | Effort |
|---|---------|----------|-----|--------|
| 7 | H-1: Fix situation_type/factors in execute endpoint | HIGH | Call analyze_situation() or pass correct values | 15 min |
| 8 | M-12: Add Neo4j query timeout | MEDIUM | Wrap in `asyncio.wait_for()` | 10 min |
| 9 | M-13: Lazy-init ReasoningNarrator | MEDIUM | Move init to first call | 10 min |
| 10 | M-3: Clean up setTimeout race conditions | MEDIUM | Use refs + cleanup | 15 min |
| 11 | M-9: Add IOC mapping for ALERT-7824 | MEDIUM | Add to ALERT_IOC_MAP + seed | 10 min |
| 12 | M-14: Skip Decision trace creation in blocked flow | MEDIUM | Conditional in process_blocked | 5 min |
| 13 | L-8: Suppress verbose API logging | LOW | Wrap in dev check | 5 min |

---

## Summary

The codebase is solid for its purpose — a 15-minute live demo. The happy-path flow (analyze → execute → feedback → evidence ledger → compounding view) works correctly for both ALERT-7823 and ALERT-7824. The architecture (three-loop diagram, eval gates, TRIGGERED_EVOLUTION) is well-implemented and visually compelling.

The main risks are around the **reset flow** (items 1, 3, 4 above) and the **version label** (item 2). These are all quick fixes. With those 4 fixes applied, the demo is reliable for recording.

---

*Code Review v3.1.1 Pass 1 | 2026-02-24*
*Reviewed by Claude Opus 4.6 | 30+ files, ~12K lines*
*Finding counts: 0 CRITICAL, 3 HIGH, 16 MEDIUM+, 15 LOW*
