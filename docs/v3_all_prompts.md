# SOC Copilot v3.0 — All Prompts for Claude Code

**12 prompts, 5 sessions. Paste each into Claude Code sequentially.**

**IMPORTANT:** Before Session 1, ensure:
- Working directory: `gen-ai-roi-demo-v3`
- Branch: `feature/v3.0-enhancements` (already created)
- Backend runs on port 8001, frontend on port 5174
- `.env` has NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, PULSEDIVE_API_KEY

---

## SESSION 1: Loop 3 (3 prompts)

### Prompt A1 — Backend: RL Reward Summary Endpoint

```
This is a continuing thread for the SOC Copilot demo.
Status: v2.5.1 tagged. ACCP progress: 10/21 capabilities.
Branch: feature/v3.0-enhancements (already created)

RULES — follow these for EVERY change in this session:
1. No git commands. Never git commit, push, tag, or branch.
2. No debugger. Never launch pdb, debugger, or interactive Python sessions.
3. Read before write. Always read target files completely before modifying.
4. One concern per prompt. Do not touch files not listed below.
5. Add, don't rewrite. Find the insertion point, add new code, leave everything else untouched.
6. Show your work. After changes, show exact lines changed (before/after). Do NOT start the dev server.

TASK: Add GET /api/rl/reward-summary endpoint.

Files to modify:
- backend/app/services/feedback.py (add function)
- backend/app/routers/triage.py (add endpoint)

Read BOTH files fully first. Then:

1. In feedback.py: Add a get_reward_summary() function that aggregates the current
   in-memory feedback state. It should return a dict:
   {
     "total_decisions": int,       # count of all outcome records
     "correct": int,               # count where outcome == "correct"
     "incorrect": int,             # count where outcome == "incorrect"
     "asymmetric_ratio": 20.0,     # fixed constant
     "cumulative_r_t": float,      # sum of all deltas (+0.3 for correct, -6.0 for incorrect)
     "loop3_status": "active" | "insufficient_data",  # "active" if total_decisions > 0
     "governs": ["loop1_situation_analyzer", "loop2_agent_evolver"]
   }

2. In triage.py: Add a GET endpoint at /api/rl/reward-summary that calls
   get_reward_summary() and returns the result as JSON. Follow the existing
   endpoint patterns in triage.py.

No new Pydantic model needed — return a plain dict via JSONResponse.

VERIFICATION (do not run — human will verify):
1. curl http://localhost:8001/api/rl/reward-summary
   → returns total_decisions=0, loop3_status="insufficient_data"
2. Process alert + outcome (incorrect), then curl again
   → returns total_decisions=1, incorrect=1, cumulative_r_t=-6.0, loop3_status="active"
```

---

### Prompt A2 — Frontend: Loop 3 Panel in Tab 2

```
Continuing SOC Copilot v3.0 build on branch feature/v3.0-enhancements.

RULES:
1. No git commands. No debugger. Read before write.
2. Add only — do NOT rewrite or restructure existing code.
3. Show before/after for each change. Do NOT start the dev server.

TASK: Add Loop 3 panel to Tab 2 (Runtime Evolution).

Files to modify:
- frontend/src/lib/api.ts (add function)
- frontend/src/components/tabs/RuntimeEvolutionTab.tsx (add panel)

Read BOTH files fully first. Then:

1. In api.ts: Add getRewardSummary() function that calls GET /api/rl/reward-summary.
   Follow the existing pattern (look at how getCompoundingMetrics or similar functions work).

2. In RuntimeEvolutionTab.tsx: Add a new panel BELOW the AgentEvolver section.
   Do NOT modify any existing panels or logic.

   Panel content:
   - Title: "Loop 3: RL Reward / Penalty"
   - Subtitle: "Governs Loops 1 and 2 — continuous reinforcement signal"
   - Three metrics in a row: cumulative r(t), asymmetric ratio (20:1), decisions governed
   - One-line chip/badge: "Security-first: penalty 20× reward"
   - Visual: a simple asymmetric bar — thin green bar for +0.3, wide red bar for -6.0
     (CSS only, no charting library. Use div widths proportional to values.)
   - Fetch data on component mount and after any alert processing
   - When loop3_status is "insufficient_data", show a muted state with
     text like "Awaiting first verified outcome..."

VERIFICATION (do not run — human will verify):
1. Tab 2 shows Loop 3 panel below AgentEvolver
2. Shows "insufficient_data" state initially
3. After processing alert + incorrect outcome in Tab 3, returns to Tab 2:
   Loop 3 shows cumulative r(t) = -6.0, decisions = 1, status = active
4. Asymmetric bar shows red bar ~20× wider than green bar
5. Existing panels (eval gates, AgentEvolver) unchanged
```

---

### Prompt A3 — Frontend: Three-Loop Hero Diagram + Four Layers in Tab 4

```
Continuing SOC Copilot v3.0 build on branch feature/v3.0-enhancements.

RULES:
1. No git commands. No debugger. Read before write.
2. Replace ONLY the Two-Loop Hero section. Do NOT touch anything else.
3. Show before/after for each change. Do NOT start the dev server.

TASK: Replace Two-Loop Hero Diagram with Three-Loop Hero + Four Layers strip in Tab 4.

Files to modify:
- frontend/src/components/tabs/CompoundingTab.tsx (ONLY this file)

Read the ENTIRE file first. Then:

1. Find the "Two-Loop Hero Diagram" section. It has a dark slate background,
   center Neo4j graph with pulse animation, Loop 1 (blue) and Loop 2 (purple)
   panels, TRIGGERED_EVOLUTION badge, and a stats row.

2. Replace ONLY that section. Do NOT touch:
   - Business Impact Banner
   - Weekly Trend Chart
   - Evolution Events Timeline
   - ROI Calculator button or modal
   - Reset Demo Data button

3. New Three-Loop Hero content:
   - Dark slate background (same as current)
   - Center: "Living Context Graph" label with subtle pulse (reuse existing animation)
   - Three loop panels arranged around center:
     * Loop 1 (blue): "Situation Analyzer" — "Smarter within each decision"
     * Loop 2 (purple): "AgentEvolver" — "Smarter across decisions"
     * Loop 3 (amber/orange): "RL Reward / Penalty" — "Governs both loops"
   - Arrows from each loop to center graph (CSS borders/transforms, not SVG)
   - Caption: "Three cross-layer loops. One living graph. Intelligence that compounds automatically."

4. Four Layers context strip (below three-loop diagram, above stats row):
   - Single horizontal flexbox row with four labeled boxes connected by → arrows
   - Box 1 (gray): "UCL" — subtitle "CrowdStrike · Pulsedive · SIEM"
   - Box 2 (gray): "Agent Engineering" — subtitle "Runtime evolution"
   - Box 3 (highlighted, blue border): "ACCP" — subtitle "Cognitive control"
   - Box 4 (highlighted, green border): "SOC Copilot" — subtitle "Domain copilot"
   - Small label above strip: "Four Dependency-Ordered Layers"
   - Boxes 3 and 4 visually distinct (brighter/bordered) = "this is what the demo shows"
   - Keep it compact — one line of boxes, not a full diagram.

5. Stats row: keep existing stats (2→6 situation types, 0→4 prompt variants,
   pattern counts) + add "20:1 asymmetric penalty ratio"

Do NOT use SVG, canvas, or D3. Use flexbox/grid with colored cards.

VERIFICATION (do not run — human will verify):
1. Tab 4: Three-Loop Hero visible with three panels (blue, purple, amber)
2. Center graph pulse animation works
3. "Three cross-layer loops. One living graph." caption visible
4. Four Layers strip visible with four boxes: UCL → Agent Engineering → ACCP → SOC Copilot
5. ACCP and SOC Copilot boxes visually highlighted
6. Stats row shows 4+ items including asymmetric ratio
7. Business Impact Banner, ROI Calculator, Weekly Trends, Reset button all still work
```

---

## SESSION 2: Bug Fixes (2 prompts)

### Prompt B2 — Fix Policy Override of Recommendation Panel

```
Continuing SOC Copilot v3.0 build on branch feature/v3.0-enhancements.

RULES:
1. No git commands. No debugger. Read before write.
2. Modify ONLY AlertTriageTab.tsx. Do NOT touch any other file.
3. Show before/after for each change. Do NOT start the dev server.

TASK: Fix the policy override bug in Tab 3.

File to modify:
- frontend/src/components/tabs/AlertTriageTab.tsx (ONLY this file)

Read the ENTIRE file first. Then:

THE BUG: When the Policy Conflict panel shows "escalate wins" (POLICY-SEC-007
overrides POLICY-SOC-003), the Recommendation panel still shows "auto-close" with
a clickable "Apply Recommendation" button. A CISO sees conflicting guidance.

THE FIX:
1. Find where the Recommendation panel renders.
2. Find the state/variable holding the policy resolution result (from checkPolicy API).
3. Add a conditional: IF policy resolution exists AND resolved_action is 'escalate_tier2':
   a. Keep the Recommendation panel visible (the "AI wanted X but policy stopped it"
      narrative is valuable — do NOT remove the panel)
   b. Add an amber banner at the top: "⚠ Policy Override: Security policy requires
      escalation. See Policy Conflict panel above."
   c. Reduce panel opacity to 0.6
   d. Change button label from "Apply Recommendation" to "Apply Policy Resolution"
   e. When button is clicked, execute the escalation action (policy-resolved action),
      NOT the AI's original recommendation

4. Do NOT change any other panel behavior, layout, or the PolicyConflict component.

VERIFICATION (do not run — human will verify):
1. ALERT-7823 (travel login — triggers policy conflict):
   - Policy Conflict shows "Security Policy Wins"
   - Recommendation panel shows amber "Policy Override" banner
   - Reduced opacity, button says "Apply Policy Resolution"
   - Clicking button executes escalation, not auto-close
2. ALERT-7824 (phishing — no policy conflict):
   - Recommendation panel renders normally (full opacity, no banner, "Apply Recommendation")
```

---

### Prompt B3 — Remove Pulse Animation on ROI Button

```
Continuing SOC Copilot v3.0 build on branch feature/v3.0-enhancements.

RULES:
1. No git commands. No debugger. Read before write.
2. Modify ONLY CompoundingTab.tsx. Do NOT touch any other file.
3. Show before/after for each change. Do NOT start the dev server.

TASK: Remove the pulse animation from the ROI Calculator button in Tab 4.

File to modify:
- frontend/src/components/tabs/CompoundingTab.tsx (ONLY this file)

Read the file. Find the ROI Calculator trigger button. Remove or comment out any
animate-pulse, pulse, or similar CSS animation class. The button should be a
normal static button — visible but not pulsing.

VERIFICATION (do not run — human will verify):
1. Tab 4: ROI Calculator button visible but NOT pulsing
2. Click button → modal opens normally
3. Close modal → button remains static
```

---

## SESSION 3: Threat Intel — Live Pulsedive (2 prompts)

### Prompt EC1a — Backend: Live Threat Intel via Pulsedive API

```
Continuing SOC Copilot v3.0 build on branch feature/v3.0-enhancements.

RULES:
1. No git commands. No debugger. Read before write.
2. Show before/after for each change. Do NOT start the dev server.

TASK: Add threat intel refresh endpoint that calls Pulsedive live API
with hardcoded fallback.

Files to create/modify:
- backend/app/services/threat_intel.py (NEW file)
- backend/app/routers/graph.py (NEW file)
- backend/app/main.py (add ONE line to register the router)

Read backend/app/main.py first to understand the router registration pattern.
Read backend/app/services/feedback.py to see the in-memory state pattern.
Read backend/app/routers/triage.py to see the endpoint pattern.

BUILD:

1. threat_intel.py — New service with refresh_threat_intel() function:

   Configuration:
   - Read PULSEDIVE_API_KEY from os.environ (with .get(), defaulting to None)

   Curated IOC list (hardcoded in the file):
   DEMO_IOCS = [
       {"value": "103.15.42.17", "context": "Singapore IP range — ties to ALERT-7823"},
       {"value": "185.220.101.34", "context": "Known Tor exit node"},
       {"value": "cobaltstrike.github.io", "context": "C2 framework domain"},
       {"value": "45.33.32.156", "context": "Scanning source — reconnaissance"},
       {"value": "malware-traffic-analysis.net", "context": "Malware distribution tracker"},
   ]

   refresh_threat_intel() logic:
   a. If PULSEDIVE_API_KEY is set:
      - For each IOC, call: GET https://pulsedive.com/api/info.php?indicator={value}&key={key}
      - Use requests library. Handle errors per-indicator (try/except, log warning, continue).
      - Add time.sleep(0.5) between calls (rate limiting).
      - Parse response: extract risk, risk_recommended, threats array, properties.
      - Map to normalized dict: value, type (ip/domain), severity (from risk field),
        source="pulsedive_live", risk_factors, first_seen, last_updated.
      - If Pulsedive returns "Indicator not found", use hardcoded data for that IOC.
   b. If NO key or ALL calls fail: use hardcoded fallback data for all 5 IOCs
      with plausible static values, source="hardcoded_fallback".
   c. Write as :ThreatIntel nodes into Neo4j using MERGE (idempotent).
      Properties: value, type, severity, source, risk_factors, first_seen, last_updated.
   d. Create :ASSOCIATED_WITH relationships to :Alert nodes where relevant
      (match Singapore IP to alerts mentioning Singapore or travel).
   e. Return summary dict.

   Use the existing Neo4j connection pattern from other services (check how
   the app connects to Neo4j — likely via a driver in app config or dependency).

2. graph.py — New router with ONE endpoint:
   POST /api/graph/threat-intel/refresh
   Calls refresh_threat_intel(). Returns:
   {
     "source": "pulsedive_live" | "hardcoded_fallback",
     "indicators_ingested": 5,
     "relationships_created": 2,
     "enrichment_summary": [
       {"value": "103.15.42.17", "risk": "high", "threats": ["APT41"], "source": "pulsedive_live"},
       ...
     ]
   }

3. main.py — Add ONE line to register the graph router. Follow existing pattern.

VERIFICATION (do not run — human will verify):
1. With PULSEDIVE_API_KEY in .env:
   curl -X POST http://localhost:8001/api/graph/threat-intel/refresh
   → source="pulsedive_live", indicators >= 3
2. Same curl again → idempotent, no duplicates
3. Neo4j: MATCH (t:ThreatIntel) RETURN t → nodes with real risk data
4. Without API key → source="hardcoded_fallback", demo still works
```

---

### Prompt EC1b — Frontend: Threat Intel Badge in Tab 3

```
Continuing SOC Copilot v3.0 build on branch feature/v3.0-enhancements.

RULES:
1. No git commands. No debugger. Read before write.
2. Add only — do NOT modify existing panels.
3. Show before/after for each change. Do NOT start the dev server.

TASK: Add a Threat Intel status badge to Tab 3.

Files to modify:
- frontend/src/lib/api.ts (add function)
- frontend/src/components/tabs/AlertTriageTab.tsx (add badge)

Read BOTH files fully first. Then:

1. In api.ts: Add refreshThreatIntel() function calling
   POST /api/graph/threat-intel/refresh. Returns the full response
   including source and enrichment_summary.

2. In AlertTriageTab.tsx: Add a small "Threat Intel" status badge in the
   graph traversal area (near the "47 nodes traversed" display or similar).

   Badge content:
   - Icon: 🛡️ emoji
   - Text: "Threat Intel: {N} indicators · Source: {source} · Last refreshed: {timestamp}"
   - Source label: "Pulsedive (live)" in green if source=pulsedive_live,
     "Local cache" in amber if hardcoded_fallback
   - Small "Refresh" button that calls the endpoint and updates the badge
   - Overall color: green if refreshed within last hour, amber otherwise

   Add local state to track last refresh time and result.
   Do NOT auto-refresh on mount — only on button click.

   Do NOT modify the graph visualization, alert queue, situation analyzer,
   recommendation panel, policy conflict panel, or outcome feedback panel.

VERIFICATION (do not run — human will verify):
1. Tab 3: Threat Intel badge visible near graph area
2. Click Refresh → badge updates with count and "Pulsedive (live)" label
3. No other Tab 3 panels affected
4. Process an alert → badge persists through the flow
```

---

## SESSION 4: Evidence Ledger (3 prompts)

### Prompt EL1 — Backend: Decision Audit Service + Export

```
Continuing SOC Copilot v3.0 build on branch feature/v3.0-enhancements.

RULES:
1. No git commands. No debugger. Read before write.
2. Show before/after for each change. Do NOT start the dev server.

TASK: Add decision audit service with JSON and CSV export endpoints.

Files to create/modify:
- backend/app/services/audit.py (NEW file)
- backend/app/routers/audit.py (NEW file)
- backend/app/main.py (add ONE line to register the router)

Read backend/app/services/feedback.py first to understand the in-memory state
and how outcomes are tracked. Read main.py for the router pattern.

BUILD:

1. services/audit.py — In-memory decision ledger:

   Data structure — each DecisionRecord is a dict with:
   id, alert_id, timestamp (ISO format), situation_type, action_taken,
   factors (list of factor names), confidence (float), outcome (nullable string),
   analyst_confirmed (bool)

   Functions:
   - record_decision(alert_id, situation_type, action_taken, factors, confidence)
     → creates and stores a new DecisionRecord, returns it
   - record_outcome(alert_id, outcome, analyst_notes=None)
     → finds the most recent record for alert_id, updates outcome field
   - get_decisions() → returns all records as a list
   - reconstruct_from_memory()
     → reads from feedback.py's in-memory state to populate the ledger
     → this avoids modifying working code in feedback.py or triage.py

   Store records in a module-level list. Use uuid4 for record IDs.
   Use datetime.utcnow().isoformat() for timestamps.

   IMPORTANT: Do NOT modify feedback.py or triage.py in this prompt. The
   reconstruct_from_memory() function reads their state without changing it.

2. routers/audit.py — Two endpoints:

   GET /api/audit/decisions?format=json
   → calls reconstruct_from_memory() then get_decisions()
   → returns JSON array of all decision records

   GET /api/audit/decisions?format=csv
   → same data but returns as CSV with Content-Disposition header
   → use csv.writer with io.StringIO
   → header row: id, alert_id, timestamp, situation_type, action_taken, factors, confidence, outcome

   Default format is json if not specified.

3. main.py — Register the audit router (single line).

VERIFICATION (do not run — human will verify):
1. Process an alert through full flow (analyze, execute, outcome feedback)
2. curl http://localhost:8001/api/audit/decisions?format=json
   → JSON array with at least 1 record, all fields present
3. curl -o audit.csv http://localhost:8001/api/audit/decisions?format=csv
   → CSV downloads, opens in spreadsheet, columns match
```

---

### Prompt EL2 — Backend: Tamper-Evident Hash Chain

```
Continuing SOC Copilot v3.0 build on branch feature/v3.0-enhancements.

RULES:
1. No git commands. No debugger. Read before write.
2. Show before/after for each change. Do NOT start the dev server.

TASK: Add SHA-256 tamper-evident hash chain to the audit service.

Files to modify:
- backend/app/services/audit.py (modify — add hashing)
- backend/app/routers/audit.py (add verify endpoint)

Read BOTH files fully first (they were created in the previous prompt). Then:

1. In services/audit.py:
   - Import hashlib and json
   - When a decision is recorded (in record_decision), compute:
     hash = SHA-256 of (previous_hash + json.dumps(decision_data, sort_keys=True))
   - First record uses seed hash: "SOC_COPILOT_GENESIS_2026"
   - Store the hash as a "hash" field on each DecisionRecord
   - Add a verify_chain() function that:
     * Walks the decision list from first to last
     * Recomputes each hash from previous_hash + decision_data
     * Returns {"chain_length": N, "verified": true/false,
       "first_record": timestamp, "last_record": timestamp}
     * If any hash doesn't match, verified=false with broken_at_index

2. In routers/audit.py:
   - Add GET /api/audit/verify endpoint
   - Calls verify_chain() and returns the result
   - Also ensure the JSON and CSV exports now include the hash field

VERIFICATION (do not run — human will verify):
1. Process 2-3 alerts through full flow
2. curl http://localhost:8001/api/audit/verify
   → verified=true, chain_length matches decision count
3. curl http://localhost:8001/api/audit/decisions?format=json
   → each record has "hash" field (64-char hex string)
```

---

### Prompt EL3 — Frontend: Evidence Ledger Panel in Tab 4

```
Continuing SOC Copilot v3.0 build on branch feature/v3.0-enhancements.

RULES:
1. No git commands. No debugger. Read before write.
2. Add only — do NOT modify existing sections in CompoundingTab.tsx.
3. Show before/after for each change. Do NOT start the dev server.

TASK: Add Evidence Ledger panel to Tab 4.

Files to modify:
- frontend/src/lib/api.ts (add functions)
- frontend/src/components/tabs/CompoundingTab.tsx (add panel)

Read BOTH files fully first. Then:

1. In api.ts: Add two functions:
   - getAuditDecisions() → calls GET /api/audit/decisions?format=json
   - verifyAuditChain() → calls GET /api/audit/verify

2. In CompoundingTab.tsx: Add a new "Evidence Ledger" section BELOW the
   Three-Loop Hero diagram (which was added in A3).
   Do NOT modify the Three-Loop Hero, Business Impact Banner, Weekly Trends,
   ROI Calculator, or Reset button.

   Panel content:
   - Header: "Evidence Ledger" with subtitle "Tamper-evident decision audit trail"
   - Table showing last 5 decisions:
     * Columns: Timestamp, Alert Type, Action, Outcome, Hash
     * Hash column: first 8 chars + "..." in monospace font
   - "Chain verified ✓" green badge if verify returns true
     "Chain broken ✗" red badge if false
   - "Download CSV" button → opens /api/audit/decisions?format=csv in new tab
   - "Refresh" button to reload the table

   Fetch data on component mount. If no decisions exist yet, show
   "No decisions recorded yet" placeholder.

   Match existing panel styling in Tab 4 (cards with subtle borders, same fonts).

VERIFICATION (do not run — human will verify):
1. Process 2-3 alerts (Tab 3: analyze, execute, feedback)
2. Tab 4: Evidence Ledger panel visible below Three-Loop Hero
3. Table shows records with all columns, hash in monospace
4. "Chain verified ✓" badge is green
5. "Download CSV" → file downloads
6. "Refresh" → table reloads
7. All other Tab 4 sections still work
```

---

## SESSION 5: Decision Explainer (2 prompts)

### Prompt DX1 — Backend: Decision Factor Breakdown Endpoint

```
Continuing SOC Copilot v3.0 build on branch feature/v3.0-enhancements.

RULES:
1. No git commands. No debugger. Read before write.
2. Add only — do NOT rewrite existing functions.
3. Show before/after for each change. Do NOT start the dev server.

TASK: Add decision factor breakdown endpoint to triage service.

Files to modify:
- backend/app/services/triage.py (add function)
- backend/app/routers/triage.py (add endpoint)

Read BOTH files fully first. Understand how the scoring matrix / analysis
currently works in the triage service.

BUILD:

1. In services/triage.py: Add a get_decision_factors(alert_id) function.

   After an alert is analyzed, this function returns the factor breakdown:
   {
     "alert_id": "ALERT-7823",
     "factors": [
       {"name": "travel_match", "value": 0.95, "weight": 0.82, "contribution": "high",
        "explanation": "Employee calendar shows Singapore travel"},
       {"name": "asset_criticality", "value": 0.3, "weight": 0.45, "contribution": "low",
        "explanation": "Development server, non-critical"},
       {"name": "vip_status", "value": 0.0, "weight": 0.60, "contribution": "none",
        "explanation": "Standard employee, no executive flag"},
       {"name": "time_anomaly", "value": 0.7, "weight": 0.55, "contribution": "medium",
        "explanation": "3 AM in home timezone"},
       {"name": "device_trust", "value": 0.9, "weight": 0.78, "contribution": "high",
        "explanation": "Known corporate laptop, MDM enrolled"},
       {"name": "pattern_history", "value": 0.85, "weight": 0.70, "contribution": "high",
        "explanation": "127 similar alerts resolved as false positives"}
     ],
     "recommended_action": "false_positive_close",
     "confidence": 0.94,
     "decision_method": "softmax scoring matrix (6 factors × 4 actions)",
     "weights_note": "Weights calibrate automatically through verified outcomes (Loop 2 + Loop 3)"
   }

   Implementation:
   - Store the last analysis result in a module-level dict keyed by alert_id
     (same in-memory pattern as feedback.py). Populate it during the existing
     analyze function — add a few lines to save the factors AFTER analysis completes.
   - The factor values and weights may need to be constructed from whatever the
     existing analysis computes. Read the code carefully to find the right data.
     If the existing code doesn't compute per-factor values, create plausible
     values that are consistent with the analysis result (different for each alert).
   - Contribution levels: "high" if value × weight > 0.5, "medium" if > 0.25,
     "low" if > 0, "none" if value == 0.

2. In routers/triage.py: Add GET /api/triage/decision-factors/{alert_id}
   - Calls get_decision_factors(alert_id)
   - Returns 404 with {"detail": "No analysis found for alert_id"} if not analyzed yet
   - Returns the factor breakdown JSON if found

VERIFICATION (do not run — human will verify):
1. curl http://localhost:8001/api/triage/decision-factors/ALERT-7823 → 404
2. Analyze alert: curl -X POST .../api/triage/analyze -d '{"alert_id":"ALERT-7823"}'
3. curl http://localhost:8001/api/triage/decision-factors/ALERT-7823
   → 6 factors with names, values, weights, contributions, explanations
4. recommended_action matches analysis result
```

---

### Prompt DX1b — Frontend: "Why This Decision?" Panel in Tab 3

```
Continuing SOC Copilot v3.0 build on branch feature/v3.0-enhancements.

RULES:
1. No git commands. No debugger. Read before write.
2. Add only — do NOT modify existing panels.
3. Show before/after for each change. Do NOT start the dev server.

TASK: Add "Why This Decision?" panel to Tab 3.

Files to modify:
- frontend/src/lib/api.ts (add function)
- frontend/src/components/tabs/AlertTriageTab.tsx (add panel)

Read BOTH files fully first. Then:

1. In api.ts: Add getDecisionFactors(alertId: string) function that calls
   GET /api/triage/decision-factors/{alertId}.

2. In AlertTriageTab.tsx: Add a "Why This Decision?" panel that appears
   AFTER analysis completes. Position it between the Situation Analyzer panel
   and the Recommendation panel.

   Do NOT modify any existing panels (Situation Analyzer, Recommendation,
   Policy Conflict, Outcome Feedback).

   Panel content:
   - Header: "Why This Decision?" with collapse/expand toggle (default: expanded)
   - Subtitle: "Factor breakdown for this alert"
   - For each factor: horizontal bar showing contribution
     * Left side: factor name in readable form ("Travel Match" not "travel_match")
     * Middle: colored bar proportional to (value × weight)
       - Green for "high" contribution
       - Amber for "medium"
       - Gray for "low" or "none"
     * Right side: contribution label + brief explanation text
   - Below bars: "Decision method: softmax scoring matrix (6 factors × 4 actions)"
   - Footer (small text): "Weights calibrate automatically through verified outcomes"

   Bars are simple CSS divs with percentage width — no charting library.
   Same card styling as other Tab 3 panels.

   Do NOT render the panel until analysis is complete. Check for analysis state
   before calling the API. If no analysis has been done, don't show the panel.

   When a different alert is selected and analyzed, fetch new factors and update.

VERIFICATION (do not run — human will verify):
1. Tab 3: select ALERT-7823 → "Why This Decision?" NOT visible (no analysis)
2. Click "Analyze Alert"
3. Panel appears with 6 horizontal bars
4. travel_match, device_trust, pattern_history → green (high)
5. time_anomaly → amber (medium)
6. asset_criticality → gray (low), vip_status → gray (none)
7. Panel is collapsible
8. "Decision method: softmax scoring matrix" visible
9. All other panels unaffected
10. Select ALERT-7824, analyze → panel updates with different values
```

---

## POST-SESSION: Commit + Tag Sequence

After all 5 sessions pass verification, run these git commands yourself (NOT Claude Code):

```powershell
cd gen-ai-roi-demo-v3
git add -A
git commit -m "feat: v3.0 — Three loops. Auditable. Connected. Transparent.

Session 1: Loop 3 (A1 backend, A2 frontend Tab 2, A3 hero Tab 4)
Session 2: Bug fixes (B2 policy override, B3 pulse removal)
Session 3: Threat Intel — live Pulsedive API with fallback (EC1a, EC1b)
Session 4: Evidence Ledger — SHA-256 chain + CSV export (EL1, EL2, EL3)
Session 5: Decision Explainer — factor breakdown (DX1, DX1b)

ACCP capabilities: 14/21"

git tag -a v3.0 -m "v3.0: Three loops. Auditable. Connected. Transparent."
git push origin feature/v3.0-enhancements
```
