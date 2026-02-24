# SOC Copilot Demo — Design Document v8.0

**Version:** 8.0
**Date:** February 24, 2026
**Status:** v2.5.1 tagged. v3.0 scope finalized. Customer feedback integrated. Pulsedive API key configured.
**Repos:**
- Demo: git@github.com:ArindamBanerji/gen-ai-roi-demo.git (main, v2.5.1)
- Experiments: git@github.com:ArindamBanerji/cross-graph-experiments.git (main, v1.0 tag)
**Working directory:** gen-ai-roi-demo-v3 (separate clone for v3 development)

---

## What Changed in v8.0

| Change | Why |
|---|---|
| **EC1a upgraded: Pulsedive live API with hardcoded fallback** | Customer feedback: "your threat intel is obviously fake." Pulsedive has a free community API returning real risk scores, real enrichment data. Demo credibility jumps from "simulated" to "live intelligence." Fallback ensures demo never breaks. |
| **A3 UCL box now shows real data source names** | Customer asked "where do you fit with CrowdStrike?" The Four Layers strip now labels UCL with "CrowdStrike · Pulsedive · SIEM" — instantly positioning us as the decision layer ON TOP of their tools. |
| **New Session 5: Decision Explainer (DX1 + DX1b)** | Customer asked "how do we decide severity?" The scoring matrix already computes 6 factors × 4 actions, but this isn't surfaced clearly. New "Why This Decision?" panel in Tab 3 shows factor breakdown with visual weights. |
| **v3.0 scope: 12 prompts, 5 sessions** (was 10/4) | +2 prompts, +1 session. Manageable increase driven by real customer need. |
| **Pulsedive API key in .env** | Key configured. `.env` copied from v2 + Pulsedive key added. |
| **Development in gen-ai-roi-demo-v3** | Separate clone. v2 stays demo-ready for prospects. |

### What Changed in v7.0 (prior)

| Change | Why |
|---|---|
| **Added Four Layers context strip to Prompt A3** | CI blog claims "four dependency-ordered layers." The v6 alignment gap table flagged this as HIGH but A3's spec didn't deliver it. Now it does. |
| **Added blog content fixes as a tracked parallel task** | Both live blogs use 5× asymmetry. Experiments validated 20×. Demo uses 20:1. Blog must match before next prospect sees it. |
| **Added SECTION 11: Blog Content Fixes** | Specific edit instructions for both blogs — separate from code work, can be done in parallel. |
| **A3 verification test expanded** | Now includes four-layers strip check. |

### What Changed in v6.0 (prior)

| Change | Why |
|---|---|
| **Scoped v3.0 down from 22 prompts to 12** | v5.0 tried to ship everything in v3. That's 8 sessions and high risk. v3 should be focused; v4/v5/v6/v7 exist. |
| **Deferred Docker, Live Graph, Prompt Hub, Process Intel to v4+** | These are infrastructure (Docker), invisible improvements (Live Graph), UX polish (Prompt Hub), or future domain story (Process Intel). None create a new demo moment for a VC or CISO. |
| **Promoted Evidence Ledger from P3 to P1** | CISO buyers report to boards. "Every decision, tamper-evident, exportable" is a procurement checkbox. VC sees engineering maturity (SHA-256 chain). This is a visible demo moment. |
| **Added Threat Intel Feed as a single focused prompt** | One prompt proves the "living graph" claim. The graph updates with external context, not just decisions. Visible in Tab 3. |
| **B1 (floating point) marked DONE** | Fixed and committed as v2.5.1. |
| **Every prompt now has a verification test** | v5.0 had outcomes but no test procedures. Every prompt in v6 has exact steps to verify. |
| **Prompts are smaller** | No prompt touches more than 2 files. Large components get read-first / add-only instructions, not rewrites. |

---

## SECTION 0: What the Demo Is

The SOC Copilot Demo is the progressive reference implementation of ACCP (Agentic Cognitive Control Plane). FastAPI (Python) + React/TypeScript + Neo4j Aura, running on ports 8001/5174.

**Version roadmap (updated):**

| Version | Theme | ACCP Capabilities |
|---|---|---|
| v1.0 | Context graph (the substrate) | 1/21 |
| v2.0 | Two learning loops + eval gates + decision economics | 7/21 |
| v2.5 | Interactivity + governance (ROI, Feedback, Policy) | 10/21 |
| v2.5.1 | Bug fix: floating point display | 10/21 |
| **v3.0** | **Three loops. Auditable. Connected. Transparent.** | **14/21** |
| v4.0 | Docker + Live Graph + Prompt Hub (partner-ready) | 18/21 |
| v5.0 | Second domain copilot + Control Tower (platform thesis) | 21/21 |

**v3.0 adds exactly 4 new capabilities:** Loop 3 (#11), External Context (#14), Evidence Ledger (#15), Decision Transparency (#16). Plus 2 bug fixes.

---

## SECTION 1: ACCP Capability Map

| # | ACCP Capability | Version | Status |
|---|---|---|---|
| 1 | Context graph substrate | v1.0 | ✅ Done |
| 2 | Situation classification | v2.0 | ✅ Done |
| 3 | Eval gates (structural safety) | v2.0 | ✅ Done |
| 4 | TRIGGERED_EVOLUTION | v2.0 | ✅ Done |
| 5 | Decision economics | v2.0 | ✅ Done |
| 6 | Loop 1: Situation Analyzer (within-decision) | v2.0 | ✅ Done |
| 7 | Loop 2: AgentEvolver (across-decisions) | v2.0 | ✅ Done |
| 8 | ROI Calculator | v2.5 | ✅ Done |
| 9 | Outcome Feedback | v2.5 | ✅ Done |
| 10 | Policy Conflict Resolution | v2.5 | ✅ Done |
| **11** | **Loop 3: RL Reward/Penalty** | **v3.0** | **BUILD** |
| 12 | Live Graph Integration | v4.0 | Deferred |
| 13 | Prompt Hub / Smart Queries | v4.0 | Deferred |
| **14** | **External Context Ingestion (Threat Intel — live Pulsedive API)** | **v3.0** | **BUILD** |
| **15** | **Evidence Ledger** | **v3.0** | **BUILD** |
| **16** | **Decision Transparency (factor breakdown)** | **v3.0** | **BUILD** |
| 17 | Process Intelligence | v4.0 | Deferred |
| 18 | Docker for Partners | v4.0 | Deferred |
| 19 | Full Situational Mesh | v5.0 | Vision |
| 20 | Second domain copilot | v5.0 | Vision |
| 21 | Control Tower routing | v5.0 | Vision |

---

## SECTION 2: Demo-Blog Alignment Gap + Customer Feedback Gap

| Blog/Customer Claim | Demo Reality | Gap? | Fix In |
|---|---|---|---|
| "Three cross-layer loops" | Demo shows two loops | **CRITICAL** | v3.0 — Feature A |
| "Four dependency-ordered layers" | Tab 4 hero shows two loops, not four layers | **HIGH** | v3.0 — Prompt A3 |
| "Decision economics ($/time/risk)" | Tab 3 shows time/cost/risk per option | ✅ Aligned | — |
| "Eval gates (structural safety)" | Tab 2 shows 4-check animation + BLOCKED | ✅ Aligned | — |
| "TRIGGERED_EVOLUTION" | Tab 2 shows writes | ✅ Aligned | — |
| "Asymmetric reinforcement: 20:1 penalty" | Outcome Feedback: -6.0 vs +0.3 | ✅ Demo aligned, **BLOG WRONG** (both blogs say 5×) | Blog fix — Section 11 |
| "Cross-domain discovery" | No discovery visualization | Medium | v3.0 — Prompt EC1 (partial) |
| "$127K/quarter cost avoided" | Tab 4 banner | ✅ Aligned | — |
| "Audit trail / compliance" | Policy audit exists, no decision audit export | **HIGH** | v3.0 — Feature D |
| **Customer: "We use real IOC sources"** | Demo uses hardcoded fake indicators | **HIGH** | **v3.0 — EC1a (Pulsedive API)** |
| **Customer: "Where do you fit with CrowdStrike?"** | Four Layers strip doesn't name real tools | **MEDIUM** | **v3.0 — A3 (UCL labels)** |
| **Customer: "How do you decide severity?"** | Scoring matrix computed but not surfaced clearly | **HIGH** | **v3.0 — Feature E (DX1/DX1b)** |

---

## SECTION 3: Current State (v2.5.1)

### What's Working

All v2.5 features confirmed working. Plus:
- **B1 floating point fix** — committed and tagged v2.5.1. Confidence scores display cleanly.

### Known Bugs (Fix in v3.0)

| Bug | Severity | File | Fix In |
|---|---|---|---|
| ~~Floating point display~~ | ~~Low~~ | ~~OutcomeFeedback.tsx~~ | ~~✅ DONE v2.5.1~~ |
| Policy Conflict doesn't override Recommendation panel | Design gap | AlertTriageTab.tsx | v3.0 — Prompt B2 |
| Pulse animation on ROI button | Cosmetic | CompoundingTab.tsx | v3.0 — Prompt B3 |

---

## SECTION 4: v3.0 — Feature Specifications

**Theme:** "Three loops. Auditable. Connected. Transparent."

**Scope:** 12 prompts across 5 sessions. Each prompt: ≤ 3 files, one concern, verification test included.

**Branch:** `feature/v3.0-enhancements` off main.

**What's IN v3:** Loop 3, Evidence Ledger, Threat Intel (live Pulsedive API), Decision Explainer, bug fixes B2/B3.

**What's OUT (deferred to v4):** Docker, Live Graph Integration, Prompt Hub, Process Intelligence. These are valuable but none creates a new demo moment a VC/CISO remembers. v3 is about moments.

---

### Feature A: Loop 3 — RL Reward/Penalty [CRITICAL — closes blog gap]

**Why:** The CI blog claims three cross-layer loops. The demo shows two. This is the #1 misalignment. Loop 3's backend logic already exists in feedback.py (the asymmetric +0.3/-6.0 delta). What's missing is surfacing and labeling it as Loop 3.

**What's already there:**
- `feedback.py` computes the asymmetric delta (+0.3 / -6.0)
- `OutcomeFeedback.tsx` shows the update
- The math is correct. The labeling and visual framing are missing.

#### Prompt A1 — Backend: RL Reward Summary Endpoint

**Scope:** Add one endpoint to an existing router + one schema
**Files touched:** `backend/app/routers/triage.py`, `backend/app/models/schemas.py`

**What to build:**
```
GET /api/rl/reward-summary
Returns:
{
  "total_decisions": int,
  "correct": int,
  "incorrect": int,
  "asymmetric_ratio": 20.0,
  "cumulative_r_t": float,
  "loop3_status": "active" | "insufficient_data",
  "governs": ["loop1_situation_analyzer", "loop2_agent_evolver"]
}
```

Reads from existing in-memory feedback state in `feedback.py`. No new service file. Add a `get_reward_summary()` function to `feedback.py` that aggregates the current state.

Wait — that's 3 files. Let me restructure:
- Add `get_reward_summary()` to `feedback.py` (it already has the data)
- Add the endpoint to `triage.py` (which already imports from feedback)
- The schema can be a simple dict return — no new Pydantic model needed for a GET endpoint returning JSON

**Revised files touched:** `backend/app/services/feedback.py` (add function), `backend/app/routers/triage.py` (add endpoint)

**Verification test:**
```
1. Start backend: cd backend && uvicorn app.main:app --reload --port 8001
2. curl http://localhost:8001/api/rl/reward-summary
3. VERIFY: returns JSON with total_decisions=0, loop3_status="insufficient_data"
4. Process an alert + record outcome (Incorrect):
   curl -X POST http://localhost:8001/api/triage/analyze -H "Content-Type: application/json" -d '{"alert_id": "ALERT-7823"}'
   curl -X POST http://localhost:8001/api/triage/execute -H "Content-Type: application/json" -d '{"alert_id": "ALERT-7823", "action": "auto_close"}'
   curl -X POST http://localhost:8001/api/alert/outcome -H "Content-Type: application/json" -d '{"alert_id": "ALERT-7823", "decision_id": "DEC-001", "outcome": "incorrect"}'
5. curl http://localhost:8001/api/rl/reward-summary
6. VERIFY: total_decisions=1, incorrect=1, cumulative_r_t=-6.0, loop3_status="active", asymmetric_ratio=20.0
```

---

#### Prompt A2 — Frontend: Loop 3 Panel in Tab 2

**Scope:** Add Loop 3 panel to RuntimeEvolutionTab.tsx + add API call to api.ts
**Files touched:** `frontend/src/components/tabs/RuntimeEvolutionTab.tsx`, `frontend/src/lib/api.ts`

**Instructions for Claude Code:**
1. Read `RuntimeEvolutionTab.tsx` fully. Identify where the AgentEvolver panel ends.
2. Read `api.ts` fully. Identify the pattern for adding new API calls.
3. In `api.ts`: Add `getRewardSummary()` function that calls `GET /api/rl/reward-summary`. Follow the existing pattern (e.g., `getCompoundingMetrics`).
4. In `RuntimeEvolutionTab.tsx`: Add a new panel BELOW the AgentEvolver section. Do NOT modify any existing panels or logic.

**Panel content (add only — no rewrites):**
- Title: "Loop 3: RL Reward / Penalty"
- Subtitle: "Governs Loops 1 and 2 — continuous reinforcement signal"
- Three metrics in a row: cumulative r(t), asymmetric ratio (20:1), decisions governed
- One-line chip: "Security-first: penalty 20× reward"
- Visual: a simple asymmetric bar — thin green bar for +0.3, wide red bar for -6.0 (CSS only, no charting library)
- Fetch data on component mount and after any alert processing

**Verification test:**
```
1. Start backend (port 8001) and frontend (port 5174)
2. Open http://localhost:5174, go to Tab 2
3. VERIFY: Loop 3 panel visible below AgentEvolver
4. VERIFY: Shows "insufficient_data" state (no decisions yet)
5. Go to Tab 3, process ALERT-7823 through full flow including Outcome Feedback (click Incorrect)
6. Return to Tab 2
7. VERIFY: Loop 3 panel now shows: cumulative r(t) = -6.0, decisions = 1, status = active
8. VERIFY: Asymmetric bar shows red bar ~20× wider than green bar
9. VERIFY: Existing panels (eval gates, AgentEvolver) unchanged and working
```

---

#### Prompt A3 — Frontend: Three-Loop Hero Diagram in Tab 4

**Scope:** Replace the Two-Loop Hero Diagram section in CompoundingTab.tsx
**Files touched:** `frontend/src/components/tabs/CompoundingTab.tsx`

**Instructions for Claude Code:**
1. Read `CompoundingTab.tsx` fully.
2. Find the "Two-Loop Hero Diagram" section. It has a dark slate background, center Neo4j graph with pulse animation, Loop 1 (blue) and Loop 2 (purple) panels, TRIGGERED_EVOLUTION badge, and a stats row.
3. Replace ONLY that section. Do NOT touch: Business Impact Banner, Weekly Trend Chart, Evolution Events Timeline, ROI Calculator button, or Reset Demo Data button.
4. The new Three-Loop Hero should maintain the same visual language (dark slate background, colored panels, center graph).

**New hero diagram content:**
- Dark slate background (same as current)
- Center: "Living Context Graph" label with subtle pulse (reuse existing animation)
- Three loop panels arranged around center:
  - Loop 1 (blue): "Situation Analyzer" — "Smarter within each decision"
  - Loop 2 (purple): "AgentEvolver" — "Smarter across decisions"  
  - Loop 3 (amber/orange): "RL Reward / Penalty" — "Governs both loops"
- Arrows from each loop pointing to center graph (CSS borders/transforms, not SVG)
- Bottom caption: "Three cross-layer loops. One living graph. Intelligence that compounds automatically."
- **Four Layers context strip** (below the three-loop diagram, above the stats row):
  - A single horizontal flexbox row with four labeled boxes, connected by right-pointing arrows (→)
  - Box 1 (gray): "UCL" — subtitle "CrowdStrike · Pulsedive · SIEM"
  - Box 2 (gray): "Agent Engineering" — subtitle "Runtime evolution"
  - Box 3 (highlighted, e.g. blue border or slightly brighter): "ACCP" — subtitle "Cognitive control"
  - Box 4 (highlighted, e.g. green border): "SOC Copilot" — subtitle "Domain copilot"
  - Small label above the strip: "Four Dependency-Ordered Layers"
  - Boxes 3 and 4 should be visually distinct (brighter, border highlight) to indicate "this is what the demo shows"
  - Keep it compact — one line of boxes, not a full diagram. This is context, not the hero.
- Stats row updated: keep existing stats (2→6 situation types, 0→4 prompt variants, pattern counts) + add "20:1 asymmetric penalty ratio"

**Do NOT** use SVG, canvas, or D3. Use flexbox/grid with colored cards — same approach as the existing Two-Loop Hero.

**Verification test:**
```
1. Open http://localhost:5174, go to Tab 4
2. VERIFY: Three-Loop Hero visible with three loop panels (blue, purple, amber)
3. VERIFY: Center graph pulse animation still works
4. VERIFY: "Three cross-layer loops. One living graph." caption visible
5. VERIFY: Four Layers strip visible below the three-loop diagram
6. VERIFY: Four boxes labeled UCL → Agent Engineering → ACCP → SOC Copilot
7. VERIFY: ACCP and SOC Copilot boxes are visually highlighted (brighter/bordered)
8. VERIFY: Stats row shows 4 items including asymmetric ratio
9. VERIFY: Business Impact Banner above hero still shows 847 hrs, $127K, etc.
10. VERIFY: ROI Calculator button still opens modal
11. VERIFY: Weekly Trend Chart still renders
12. VERIFY: Reset Demo Data button still works
```

---

### Feature B: Bug Fixes

#### Prompt B2 — Fix Policy Override of Recommendation Panel

**Scope:** Conditional rendering in AlertTriageTab.tsx
**Files touched:** `frontend/src/components/tabs/AlertTriageTab.tsx` only

**The bug:** When the Policy Conflict panel shows "escalate wins" (POLICY-SEC-007 overrides POLICY-SOC-003), the Recommendation panel still shows "auto-close" with a clickable "Apply Recommendation" button. A sharp CISO sees conflicting guidance on screen.

**The fix (Option B+C from prior analysis):**
1. Read AlertTriageTab.tsx fully. Find where the Recommendation panel renders.
2. Find the state/variable that holds the policy resolution result (from the `checkPolicy` API call).
3. Add a conditional: IF policy resolution exists AND resolved_action is 'escalate_tier2', THEN:
   - Keep the Recommendation panel visible (do NOT remove it — the "AI wanted X but policy stopped it" narrative is valuable)
   - Add an amber banner at the top of the panel: "⚠ Policy Override: Security policy requires escalation. See Policy Conflict panel above."
   - Reduce the panel opacity to 0.6
   - Change the button label from "Apply Recommendation" to "Apply Policy Resolution"
   - When the button is clicked, it should execute the escalation action (the policy-resolved action), NOT the AI's original recommendation
4. Do NOT change any other panel behavior, layout, or the PolicyConflict component itself.

**Verification test:**
```
1. Start backend + frontend
2. Go to Tab 3, select ALERT-7823 (the travel login that triggers policy conflict)
3. Click "Analyze Alert"
4. VERIFY: Policy Conflict panel shows "Security Policy Wins (Priority 1)"
5. VERIFY: Recommendation panel shows amber "Policy Override" banner
6. VERIFY: Recommendation panel is at reduced opacity
7. VERIFY: Button says "Apply Policy Resolution" not "Apply Recommendation"
8. Click "Apply Policy Resolution"
9. VERIFY: Closed loop executes with escalation action, not auto-close
10. Now select ALERT-7824 (phishing — no policy conflict)
11. Click "Analyze Alert"
12. VERIFY: Recommendation panel renders normally (full opacity, no override banner, "Apply Recommendation" button)
```

---

#### Prompt B3 — Remove Pulse Animation on ROI Button

**Scope:** One CSS/class change
**Files touched:** `frontend/src/components/tabs/CompoundingTab.tsx` only

**The fix:** Find the ROI Calculator trigger button in CompoundingTab.tsx. Remove or comment out any `animate-pulse`, `pulse`, or similar CSS animation class. The button should be a normal static button.

**Verification test:**
```
1. Open http://localhost:5174, go to Tab 4
2. VERIFY: ROI Calculator button is visible but NOT pulsing
3. Click it — VERIFY: modal opens normally
4. Close modal — VERIFY: button remains static
```

---

### Feature C: Threat Intel Feed — Live Pulsedive API [Shows "living graph" with real data]

**Why:** The blog says "cross-domain discovery" and "living graph." Customer feedback: "We collect IOCs from Pulsedive, GreyNoise, ThreatYeti." The current demo graph is static. This feature adds a real external data feed — live API call to Pulsedive returning real risk scores, real enrichment. Hardcoded fallback ensures demo never breaks.

#### Prompt EC1a — Backend: Live Threat Intel via Pulsedive API

**Scope:** New service file + new router + register in main.py
**Files touched:** `backend/app/services/threat_intel.py` (new), `backend/app/routers/graph.py` (new), `backend/app/main.py` (add router)

NOTE: This is 3 files, but two are new (no risk of breaking existing code) and the main.py change is a single line (adding the router import + registration).

**What to build:**

- **Configuration:** Read `PULSEDIVE_API_KEY` from environment (same pattern as NEO4J_URI in existing code). Import from `os.environ` or use existing config pattern.

- **Curated IOC list:** Define 5 demo-relevant indicators to look up:
  ```python
  DEMO_IOCS = [
      {"value": "103.15.42.17", "context": "Singapore IP range — ties to ALERT-7823 travel login"},
      {"value": "185.220.101.34", "context": "Known Tor exit node — credential stuffing campaigns"},
      {"value": "cobaltstrike.github.io", "context": "C2 framework domain — lateral movement indicator"},
      {"value": "45.33.32.156", "context": "Scanning source — reconnaissance activity"},
      {"value": "malware-traffic-analysis.net", "context": "Malware distribution tracker"},
  ]
  ```
  (These should be IPs/domains known to Pulsedive. If any return "not found", that's fine — the fallback data covers it.)

- **`threat_intel.py`:** Provides `refresh_threat_intel()` function:
  1. Check if `PULSEDIVE_API_KEY` is set
  2. If YES: For each IOC in DEMO_IOCS, call `GET https://pulsedive.com/api/info.php?indicator={value}&key={key}`
     - Parse response: extract `risk` (none/low/medium/high/critical), `risk_recommended`, `threats` array, `attributes`, `properties`
     - Map to a normalized `ThreatIndicator` dict: indicator_id, type (ip/domain), value, severity (from risk field), source ("pulsedive_live"), risk_factors (from response), first_seen, last_updated
     - Handle per-indicator errors gracefully (skip that IOC, log warning, continue)
     - Rate limit: Add 0.5s sleep between calls (Pulsedive rate limits free tier)
  3. If NO key or all API calls fail: Fall back to hardcoded data (same 5 IOCs with plausible static values, source="hardcoded_fallback")
  4. Write as `:ThreatIntel` nodes into Neo4j with all properties from API response
  5. Create `:ASSOCIATED_WITH` relationships to relevant `:Alert` nodes (match on IP ranges or domain patterns)
  6. Make it idempotent: MERGE on indicator value, update timestamps if exists

- **`graph.py`:** One endpoint: `POST /api/graph/threat-intel/refresh`. Calls `refresh_threat_intel()`. Returns:
  ```json
  {
      "source": "pulsedive_live" | "hardcoded_fallback",
      "indicators_ingested": 5,
      "relationships_created": 2,
      "enrichment_summary": [
          {"value": "103.15.42.17", "risk": "high", "threats": ["APT41"], "source": "pulsedive_live"},
          {"value": "185.220.101.34", "risk": "medium", "threats": [], "source": "pulsedive_live"}
      ]
  }
  ```

- **`main.py`:** Register the graph router (single line).

**Verification test:**
```
1. Ensure PULSEDIVE_API_KEY is set in .env
2. Start backend: cd backend && uvicorn app.main:app --reload --port 8001
3. curl -X POST http://localhost:8001/api/graph/threat-intel/refresh
4. VERIFY: returns source="pulsedive_live", indicators_ingested >= 3
5. VERIFY: enrichment_summary shows real risk levels from Pulsedive
6. Run the same curl again
7. VERIFY: idempotent — no duplicate nodes. Same counts.
8. Verify in Neo4j: MATCH (t:ThreatIntel) RETURN t — should show nodes with real risk data
9. Verify relationships: MATCH (t:ThreatIntel)-[:ASSOCIATED_WITH]->(a:Alert) RETURN t,a

FALLBACK TEST:
10. Remove PULSEDIVE_API_KEY from .env (or rename it), restart backend
11. curl -X POST http://localhost:8001/api/graph/threat-intel/refresh
12. VERIFY: returns source="hardcoded_fallback" — demo still works
13. VERIFY: Neo4j still has :ThreatIntel nodes (with static data)
```

---

#### Prompt EC1b — Frontend: Threat Intel Badge in Tab 3

**Scope:** Small addition to AlertTriageTab.tsx
**Files touched:** `frontend/src/components/tabs/AlertTriageTab.tsx`, `frontend/src/lib/api.ts`

**Instructions:**
1. In `api.ts`: Add `refreshThreatIntel()` function calling `POST /api/graph/threat-intel/refresh`. Returns the full response including source and enrichment_summary.
2. In `AlertTriageTab.tsx`: Add a small "Threat Intel" status badge in the graph traversal area (near the "47 nodes traversed" display). The badge shows:
   - Icon: shield or radar icon (use emoji 🛡️ if no icon library available)
   - Text: "Threat Intel: {N} indicators · Source: {source} · Last refreshed: {timestamp}"
   - Source label: "Pulsedive (live)" in green if source=pulsedive_live, "Local cache" in amber if hardcoded_fallback
   - A small "Refresh" button that calls the endpoint and updates the badge
   - Color: green if refreshed within last hour, amber otherwise

**Add only.** Do NOT modify the graph visualization, alert queue, situation analyzer, or any other panel.

**Verification test:**
```
1. Start backend + frontend, go to Tab 3
2. VERIFY: Threat Intel badge is visible near graph area
3. Click "Refresh" on the badge
4. VERIFY: Badge updates with indicator count and "Pulsedive (live)" source label
5. VERIFY: No other Tab 3 panels are affected
6. Process an alert (Analyze + Apply) — VERIFY: badge persists through the flow
```

---

### Feature D: Evidence Ledger [CISO compliance + VC engineering depth]

**Why this is in v3:** CISOs report to boards. Every CISO who sees the demo will ask: "Can I prove what the AI decided and why?" The Evidence Ledger answers that. For VCs, the SHA-256 tamper-evident chain signals engineering maturity — blockchain-grade integrity without the blockchain overhead.

#### Prompt EL1 — Backend: Decision Audit Service + Export Endpoint

**Scope:** New service + new router + register in main.py
**Files touched:** `backend/app/services/audit.py` (new), `backend/app/routers/audit.py` (new), `backend/app/main.py` (add router)

**What to build:**
- `services/audit.py`: An in-memory decision ledger. Provides:
  - `record_decision(alert_id, situation_type, action_taken, factors, confidence)` — called when an alert is processed
  - `record_outcome(alert_id, outcome, analyst_notes)` — called when outcome feedback is given
  - `get_decisions() -> List[DecisionRecord]` — returns all recorded decisions
  - Each `DecisionRecord` has: id, alert_id, timestamp, situation_type, action_taken, factors (list), confidence, outcome (nullable), analyst_confirmed (bool)
  
- `routers/audit.py`: Two endpoints:
  - `GET /api/audit/decisions?format=json` — returns decisions as JSON array
  - `GET /api/audit/decisions?format=csv` — returns as CSV download with Content-Disposition header
  
- `main.py`: Register the audit router.

**IMPORTANT:** The audit service needs to be called from existing code. But do NOT modify triage.py or feedback.py in this prompt. Instead, the audit service will provide a `reconstruct_from_memory()` function that reads from the existing in-memory state in feedback.py to populate the ledger. This avoids touching working code. The hook-based approach (calling record_decision from triage.py) can be done in v4 when we do Live Graph Integration.

**Verification test:**
```
1. Start backend
2. Process an alert through the full flow (analyze, execute, outcome feedback)
3. curl http://localhost:8001/api/audit/decisions?format=json
4. VERIFY: returns JSON array with at least 1 decision record
5. VERIFY: record has all fields (alert_id, timestamp, situation_type, action_taken, factors, confidence, outcome)
6. curl -o audit.csv http://localhost:8001/api/audit/decisions?format=csv
7. VERIFY: CSV file downloads and opens correctly in any spreadsheet app
8. VERIFY: column headers match JSON field names
```

---

#### Prompt EL2 — Backend: Tamper-Evident Hash Chain

**Scope:** Enhancement to existing audit service
**Files touched:** `backend/app/services/audit.py` (modify), `backend/app/routers/audit.py` (add endpoint)

**What to add:**
1. In `services/audit.py`: When a decision is recorded, compute SHA-256 hash of `(previous_hash + json.dumps(decision_data, sort_keys=True))`. First record uses seed hash `"SOC_COPILOT_GENESIS_2026"`. Store hash as a field on each DecisionRecord.

2. In `routers/audit.py`: Add `GET /api/audit/verify` endpoint that:
   - Walks the decision chain from first to last
   - Recomputes each hash from previous_hash + decision_data
   - Returns `{"chain_length": N, "verified": true/false, "first_record": timestamp, "last_record": timestamp}`
   - If any hash doesn't match, returns `verified: false` with the index of the broken record

**Verification test:**
```
1. Process 2-3 alerts through full flow
2. curl http://localhost:8001/api/audit/verify
3. VERIFY: returns verified=true, chain_length matches number of decisions
4. curl http://localhost:8001/api/audit/decisions?format=json
5. VERIFY: each record has a "hash" field (64-char hex string)
6. VERIFY: first record's hash = SHA-256("SOC_COPILOT_GENESIS_2026" + first_record_data)
```

---

#### Prompt EL3 — Frontend: Evidence Ledger Panel in Tab 4

**Scope:** Add section to CompoundingTab.tsx + add API calls to api.ts
**Files touched:** `frontend/src/components/tabs/CompoundingTab.tsx`, `frontend/src/lib/api.ts`

**Instructions:**
1. In `api.ts`: Add `getAuditDecisions()` and `verifyAuditChain()` functions.
2. In `CompoundingTab.tsx`: Add a new "Evidence Ledger" section BELOW the Three-Loop Hero diagram (which was added in A3). Do NOT modify any existing sections.

**Panel content:**
- Header: "Evidence Ledger" with subtitle "Tamper-evident decision audit trail"
- Table showing last 5 decisions: timestamp, alert type, action, outcome, hash (first 8 chars + "...")
- "Chain verified ✓" green badge if verify returns true; "Chain broken ✗" red badge if false
- "Download CSV" button that triggers the CSV export endpoint (open in new tab or trigger download)
- "Refresh" button to reload the table

**Visual approach:** Match the existing panel styling in Tab 4 (cards with subtle borders, same font sizes). The hash column should use monospace font.

**Verification test:**
```
1. Process 2-3 alerts through full flow (Tab 3: analyze, execute, feedback)
2. Go to Tab 4
3. VERIFY: Evidence Ledger panel visible below Three-Loop Hero
4. VERIFY: Table shows decision records with all columns
5. VERIFY: Hash column shows truncated hex strings in monospace
6. VERIFY: "Chain verified ✓" badge is green
7. Click "Download CSV" — VERIFY: CSV file downloads
8. Click "Refresh" — VERIFY: table reloads
9. VERIFY: Business Impact Banner, Three-Loop Hero, Weekly Trends, ROI Calculator all still work
```

---

### Feature E: Decision Explainer [Customer-driven — "How do you decide severity?"]

**Why this is in v3:** Direct customer feedback. A prospect asked: "How do you decide whether a threat is severe?" The scoring matrix (6 factors × 4 actions) already computes this, but it's not surfaced visibly. The Decision Explainer shows the factors, their weights, and their contributions for each decision — making the AI's reasoning transparent and auditable. For CISOs: "I can see WHY the AI made that call." For VCs: "Explainable AI, not a black box."

#### Prompt DX1 — Backend: Decision Factor Breakdown Endpoint

**Scope:** Add endpoint to existing router + add function to existing service
**Files touched:** `backend/app/routers/triage.py` (add endpoint), `backend/app/services/triage.py` (add function)

**What to build:**

`GET /api/triage/decision-factors/{alert_id}` returns the factor breakdown for the most recent analysis of that alert:

```json
{
    "alert_id": "ALERT-7823",
    "factors": [
        {"name": "travel_match", "value": 0.95, "weight": 0.82, "contribution": "high", "explanation": "Employee calendar shows Singapore travel"},
        {"name": "asset_criticality", "value": 0.3, "weight": 0.45, "contribution": "low", "explanation": "Development server, non-critical"},
        {"name": "vip_status", "value": 0.0, "weight": 0.60, "contribution": "none", "explanation": "Standard employee, no executive flag"},
        {"name": "time_anomaly", "value": 0.7, "weight": 0.55, "contribution": "medium", "explanation": "3 AM in home timezone"},
        {"name": "device_trust", "value": 0.9, "weight": 0.78, "contribution": "high", "explanation": "Known corporate laptop, MDM enrolled"},
        {"name": "pattern_history", "value": 0.85, "weight": 0.70, "contribution": "high", "explanation": "127 similar alerts resolved as false positives"}
    ],
    "recommended_action": "false_positive_close",
    "confidence": 0.94,
    "decision_method": "softmax scoring matrix (6 factors × 4 actions)",
    "weights_note": "Weights calibrate automatically through verified outcomes (Loop 2 + Loop 3)"
}
```

**Implementation approach:**
1. Read `triage.py` (service) to understand how the scoring matrix currently works.
2. The factor data is mostly already computed during analysis. The function should capture/reconstruct the factor breakdown from the most recent analysis state.
3. If no analysis has been done for that alert_id, return 404.
4. Factor contribution levels: "high" if value × weight > 0.5, "medium" if > 0.25, "low" if > 0, "none" if 0.
5. Store the last analysis result in a module-level dict keyed by alert_id (same in-memory pattern as feedback.py).

**Verification test:**
```
1. Start backend
2. curl http://localhost:8001/api/triage/decision-factors/ALERT-7823
3. VERIFY: returns 404 (no analysis yet)
4. Analyze an alert: curl -X POST http://localhost:8001/api/triage/analyze -H "Content-Type: application/json" -d '{"alert_id": "ALERT-7823"}'
5. curl http://localhost:8001/api/triage/decision-factors/ALERT-7823
6. VERIFY: returns 6 factors with names, values, weights, contributions, explanations
7. VERIFY: recommended_action matches the analysis result
8. VERIFY: contribution levels are consistent (high factors have value × weight > 0.5)
```

---

#### Prompt DX1b — Frontend: "Why This Decision?" Panel in Tab 3

**Scope:** Add panel to AlertTriageTab.tsx + add API call to api.ts
**Files touched:** `frontend/src/components/tabs/AlertTriageTab.tsx`, `frontend/src/lib/api.ts`

**Instructions:**
1. In `api.ts`: Add `getDecisionFactors(alertId: string)` function that calls `GET /api/triage/decision-factors/{alertId}`.
2. In `AlertTriageTab.tsx`: Add a "Why This Decision?" panel that appears AFTER analysis completes. Position it between the Situation Analyzer panel and the Recommendation panel. Do NOT modify any existing panels.

**Panel content (add only — no rewrites):**
- Header: "Why This Decision?" with a collapse/expand toggle (default: expanded)
- Subtitle: "Factor breakdown for this alert"
- For each factor: horizontal bar showing contribution
  - Left: factor name in readable form (e.g., "Travel Match" not "travel_match")
  - Middle: colored bar proportional to (value × weight). Color: green for high, amber for medium, gray for low/none
  - Right: contribution label + brief explanation text
- Below the bars: one-line summary: "Decision method: softmax scoring matrix (6 factors × 4 actions)"
- Footer: "Weights calibrate automatically through verified outcomes" in small text

**Visual approach:** Same card styling as other Tab 3 panels. Bars are simple CSS divs with percentage width — no charting library needed.

**Do NOT** fetch decision factors until an analysis has been completed (check for analysis state before calling API). If no analysis, don't render the panel.

**Verification test:**
```
1. Start backend + frontend, go to Tab 3
2. Select ALERT-7823 — VERIFY: "Why This Decision?" panel is NOT visible (no analysis yet)
3. Click "Analyze Alert"
4. VERIFY: "Why This Decision?" panel appears after analysis completes
5. VERIFY: Shows 6 horizontal bars with factor names and contribution levels
6. VERIFY: travel_match, device_trust, pattern_history show green (high)
7. VERIFY: time_anomaly shows amber (medium)
8. VERIFY: asset_criticality shows gray (low), vip_status shows gray (none)
9. VERIFY: Panel is collapsible
10. VERIFY: "Decision method: softmax scoring matrix" text visible
11. VERIFY: All other panels (Situation Analyzer, Recommendation, Policy Conflict, Outcome Feedback) unaffected
12. Select ALERT-7824 (different alert) and analyze
13. VERIFY: Panel updates with different factor values for the new alert
```

---

## SECTION 5: v3.0 Build Sequence

```
PRE-WORK:
  git checkout -b feature/v3.0-enhancements

SESSION 1: Loop 3 (3 prompts)
  Prompt A1: Backend RL reward endpoint
  Prompt A2: Frontend Loop 3 panel in Tab 2
  Prompt A3: Three-Loop Hero Diagram + Four Layers strip in Tab 4
  TEST: All 3 verification procedures pass
  COMMIT + TAG: v3.0-loop3

SESSION 2: Bug Fixes (2 prompts)
  Prompt B2: Policy override of Recommendation panel
  Prompt B3: Remove ROI button pulse
  TEST: Both verification procedures pass
  COMMIT

SESSION 3: Threat Intel — Live Pulsedive (2 prompts)
  Prompt EC1a: Backend — Pulsedive API with hardcoded fallback
  Prompt EC1b: Frontend — Threat Intel badge in Tab 3 (shows live source)
  TEST: Both verification procedures pass (including fallback test)
  COMMIT

SESSION 4: Evidence Ledger (3 prompts)
  Prompt EL1: Backend audit service + export
  Prompt EL2: Tamper-evident hash chain
  Prompt EL3: Frontend Evidence Ledger panel in Tab 4
  TEST: All 3 verification procedures pass
  COMMIT

SESSION 5: Decision Explainer (2 prompts)
  Prompt DX1: Backend decision factor breakdown endpoint
  Prompt DX1b: Frontend "Why This Decision?" panel in Tab 3
  TEST: Both verification procedures pass
  COMMIT

MERGE + TAG:
  git checkout main
  git merge feature/v3.0-enhancements
  git tag -a v3.0 -m "v3.0: Three loops. Auditable. Connected. Transparent."
  git push origin main v3.0
```

**Total: 12 prompts across 5 sessions. Each prompt: ≤ 3 files (new files don't count against risk), one concern, verification test included.**

---

## SECTION 6: Claude Code Rules (Apply to Every Prompt)

1. **No git commands.** Never `git commit`, `git push`, `git tag`, or `git branch`. Human handles all git operations.
2. **No debugger.** Never launch debugger, `pdb`, or interactive Python sessions.
3. **Read before write.** Always read the target file(s) completely before modifying. State what you see.
4. **One concern per prompt.** If you need to touch more than 3 files, stop and ask.
5. **Add, don't rewrite.** When adding a panel to an existing 700+ line component, find the insertion point, add the new code, and leave everything else untouched. Do NOT restructure, reformat, or "clean up" surrounding code.
6. **No schema changes without explicit instruction.** Don't add Neo4j constraints, indexes, or new node types unless the prompt spec lists them.
7. **Show your work.** After making changes, show the exact lines changed (before/after). Do NOT start the dev server — the human will verify.
8. **Backend before frontend.** Always implement and test the endpoint before writing UI that calls it.

---

## SECTION 7: What's Deferred to v4.0

These are all valuable. None was cut because it's unimportant — it was cut because it doesn't create a new demo moment for a VC or CISO.

| Feature | Why Deferred | What It Enables When Built |
|---|---|---|
| **Docker** | Infrastructure, not a demo moment. No VC or CISO remembers "it ran in Docker." | Partner self-service. Clone → docker-compose up → demo in 60 sec. |
| **Live Graph Integration** | Invisible improvement. Replaces Python dicts with Neo4j reads/writes. Demo works the same. | 30-min deep dive credibility. No in-memory state artifacts. |
| **Prompt Hub** | UX polish for Tab 1. Tab 1 is already 20% of demo energy. | Exec-friendly queries. "Did you mean?" suggestions. |
| **Process Intelligence** | Future domain story (ITSM, S2P). Not a SOC differentiator. | Cross-domain platform narrative. |

**v4.0 theme: "Partner-ready. Production-credible."**
v4 prompt count estimate: Docker (5) + Live Graph (4) + Prompt Hub (2) + Process Intel (2) + GreyNoise multi-source (1) = 14 prompts.

---

## SECTION 8: Experimental Validation (Complete — No Changes)

**Repo:** github.com/ArindamBanerji/cross-graph-experiments (v1.0 tag)

| # | Experiment | Key Result |
|---|---|---|
| 1 | Scoring matrix convergence | 69.4% from 25% random — validates 68%→89% trajectory |
| 2 | Cross-graph discovery | F1=0.293 (110× above random) |
| 3 | Multi-domain scaling | D(n) ∝ n^2.30 (R²=0.9995) |
| 4 | Sensitivity analysis | Phase transition at σ=0.3-0.5 (cliff not slope) |

**Three failure modes:** Action Confusion, Over-Correction Oscillation, Treadmill Effect.

---

## SECTION 9: Key Soundbites (Updated for v3.0)

### For CISOs

| Feature | Soundbite |
|---|---|
| Three loops | "Every alert improves within the decision. Every decision improves across decisions. A continuous RL signal governs both — automatically." |
| Evidence Ledger | "Every decision the AI made, why it made it, and whether it was right. Tamper-evident. Exportable. Take it to your board." |
| Threat Intel (live) | "That's not simulated data. We just pulled live intelligence from Pulsedive. The graph absorbed it. The next decision is richer." |
| Decision Explainer | "Six factors. Weighted. Transparent. You can see exactly WHY the AI made that call — and the weights calibrate automatically." |
| Stack positioning | "CrowdStrike detects. Pulsedive enriches. We decide — and we get better at deciding with every verified outcome." |
| Policy Conflict | "You have conflicting policies right now. You just don't know it." |
| ROI Calculator | "Plug in your numbers. See your savings. Take this to your CFO." |

### For VCs

| Feature | Soundbite |
|---|---|
| Three loops | "Loop 1 makes decisions smarter. Loop 2 makes the system smarter. Loop 3 governs both. Three loops, one graph — that's the moat." |
| Evidence Ledger | "SHA-256 hash chain. Blockchain-grade integrity without the blockchain overhead. Every decision is an immutable record." |
| Threat Intel (live) | "Live Pulsedive API. One integration today, but the pattern works for any source — GreyNoise, CrowdStrike, CISA KEV. Each source makes the graph richer." |
| Decision Explainer | "Explainable AI that explains itself with real factor weights, not post-hoc rationalizations. The weights learn from outcomes." |
| ACCP Progress | "Fourteen of twenty-one ACCP capabilities running. Code, not slides." |
| Moat equation | "The gap widens as n^2.3. A competitor starting 12 months late faces a permanently widening deficit." |

---

## SECTION 10: Post-v3.0 Demo Flow (Updated)

The 12-minute Loom script should cover:

| Beat | Tab | Duration | What's New in v3 |
|---|---|---|---|
| Opening: "Your SOC has amnesia" | — | 45 sec | Same |
| Runtime Evolution + Loop 3 | Tab 2 | 3–4 min | **Loop 3 panel, three-loop narrative** |
| Alert Triage + Decision Factors + Policy + Feedback | Tab 3 | 4–5 min | **"Why This Decision?" panel, Threat Intel badge (live Pulsedive), policy override fix** |
| Compounding + Evidence + ROI | Tab 4 | 3–4 min | **Three-Loop Hero + Four Layers (with CrowdStrike/Pulsedive labels), Evidence Ledger, ROI Calculator** |
| Close: Architecture recap | — | 1 min | "14 of 21 ACCP capabilities. Three loops. Auditable. Connected. Transparent." |

---

## SECTION 11: Blog Content Fixes (Parallel — No Code)

**Priority:** P0. Must be done before next prospect sees both blog and demo. The demo shows 20:1 asymmetry. Both blogs say 5×. A technical reader will catch this.

**See companion document: `blog_asymmetry_fixes.md` for exact edit locations and replacement text.**

**Summary of fixes needed:**

| Blog | Section | Current Text | Correct Text | Why |
|---|---|---|---|---|
| Math blog (cross-graph attention) | Section 3, Eq. 4b | `λ_neg = 5.0` | `λ_neg = 20.0` | Experiment 1 validated 20× as optimal |
| Math blog | Section 3, "Why asymmetric?" paragraph | "5:1 asymmetry" | "20:1 asymmetry" | Consistency with experiments |
| Math blog | Section 3, δ(t) definition | `λ_neg = 5.0 if r(t) = −1 (penalize failures 5× harder)` | `λ_neg = 20.0 if r(t) = −1 (penalize failures 20× harder)` | Match validated optimal |
| CI blog (compounding intelligence) | Three-loop table, Loop 3 row | "incorrect outcomes penalised 5× harder than correct outcomes are rewarded" | "incorrect outcomes penalised 20× harder than correct outcomes are rewarded" | Match demo + experiments |
| CI blog | "The Math Across the Stack" table, r(t) row | "δ(t): incorrect penalised 5×" | "δ(t): incorrect penalised 20×" | Same |
| CI blog | Weight update rule (if Eq. 4b is restated) | Any `5×` or `λ_neg = 5.0` reference | `20×` / `λ_neg = 20.0` | Same |

**Also verify:** The "A single missed threat erases the benefit of five correct auto-closes" sentence in the Math blog. With 20:1, the correct statement is "A single missed threat erases the benefit of twenty correct auto-closes." Update if present.

**Effort:** 15 minutes in Wix editor. No code changes. No republishing of graphics.

---

## SECTION 12: Customer Feedback Context (Feb 24, 2026)

**Source:** Meeting with potential customer. Key observations:

1. **They use real IOC sources:** ThreatYeti (threatyeti.com), Pulsedive (pulsedive.com), GreyNoise (viz.greynoise.io) — all open source / free tier.
2. **CrowdStrike Falcon is their dashboard.** They are NOT replacing CrowdStrike. Any solution must sit alongside or on top of it.
3. **Decision framework is the core question.** "How do we decide whether a threat is severe?" — this is the buying question.

**How v3.0 addresses each:**

| Customer Need | v3.0 Feature | Demo Moment |
|---|---|---|
| Real IOC sources | EC1a — live Pulsedive API | "That's live data from Pulsedive. Real risk scores. Real enrichment." |
| CrowdStrike positioning | A3 — UCL box labels | "CrowdStrike is your data layer. We're the decision layer on top." |
| Decision transparency | DX1/DX1b — "Why This Decision?" | "Six factors. Weighted. The AI shows its reasoning — and the weights learn." |

**API Reference — Pulsedive (configured in .env):**

```
Endpoint: GET https://pulsedive.com/api/info.php
Params: indicator={ip_or_domain}&key={PULSEDIVE_API_KEY}
Auth: API key in query param (free community tier)
Rate limit: Generous for demo use; add 0.5s sleep between calls
Returns: risk, risk_recommended, threats[], attributes{}, properties{}
Docs: https://pulsedive.com/api/
```

**Future integrations (v4+):**

| Source | API | Tier | What It Adds |
|---|---|---|---|
| GreyNoise | `GET /v3/community/{ip}` | Free (50/week) | Noise classification — is this IP scanning the internet? |
| ThreatYeti | Web lookup (no public API) | Free | Visual threat mapping — manual enrichment for now |
| CrowdStrike Falcon | OAuth2 + REST | Paid | Alert ingestion from production SIEM — requires customer trial |
| CISA KEV | `GET /vuln/known-exploited` | Free, no auth | Known exploited vulnerabilities — adds CVE context |

---

## Appendix A: Version History

| Version | Date | Changes |
|---|---|---|
| 1.0–4.0 | Feb 17–19 | Initial through experimental validation |
| 5.0 | Feb 21 | Three-loop architecture. 22-prompt v3 plan. Demo-blog audit. |
| 6.0 | Feb 24 | Scoped v3 to 10 prompts (from 22). Deferred Docker/LiveGraph/PromptHub/ProcessIntel to v4. Promoted Evidence Ledger to v3. Added Threat Intel. B1 done. Verification tests on every prompt. |
| 7.0 | Feb 24 | Blog cross-audit against both live blogs. Added Four Layers context strip to A3. Added Section 11: Blog Content Fixes (5×→20× asymmetry). |
| **8.0** | **Feb 24** | **Customer feedback integrated. EC1a upgraded to live Pulsedive API with hardcoded fallback. A3 UCL box labels real data sources (CrowdStrike/Pulsedive/SIEM). New Feature E: Decision Explainer (DX1, DX1b) — "Why This Decision?" panel. v3 scope: 12 prompts, 5 sessions. ACCP map expanded to /21. Development in gen-ai-roi-demo-v3 clone.** |

---

## Appendix B: Git History Reference

```
[v2.5.1] fix: round confidence scores to 1 decimal in OutcomeFeedback display (B1)
e63bc85 (tag: v2.5) feat: Policy Conflict frontend panel in Tab 3 (v2.5, 9B)
90438cd fix: stale closure bug in Outcome Feedback auto-select guard
f8240f8 feat: Outcome Feedback frontend panel in Tab 3 (v2.5, 8B)
865000a feat: Policy Conflict Resolution backend (v2.5, 9A)
cd44ddc feat: Outcome Feedback Loop backend (v2.5, 8A)
42d2ca8 feat: integrate ROI Calculator into Tab 4 (v2.5, 7C)
ee05f20 feat: ROI Calculator frontend modal (v2.5, 7B)
8862519 feat: ROI Calculator backend (v2.5, 7A)
```
