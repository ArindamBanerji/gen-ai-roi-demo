# SOC Copilot Demo — Design Document v4.0 (v4)

**Version:** 4.0
**Date:** February 26, 2026
**Status:** v3.2 complete and tagged. v4.0 design ready for build.
**Prerequisite:** v3.2 tagged on main (core/ + domains/ + domain_registry.py + state_manager.py)
**Theme:** "Your tools, our decisions."
**Repos:**
- Demo: git@github.com:ArindamBanerji/gen-ai-roi-demo.git (main, v3.2)
- Experiments: git@github.com:ArindamBanerji/cross-graph-experiments.git (main, v1.0)

> **Changes from v3.0:**
> (1) Phase 1 session groupings revised for smaller prompts per session. Session 2 reduced
> from 4 prompts to 3; Session 3 expanded from 3 to 4 (F1b moved to Session 3).
> (2) F2a alert corpus expanded from 16 to 17 alerts (5 travel instead of 4) to support
> Phase 5 compounding curve with sufficient data points.
> (3) New `demo_priority` field on all alerts — enables documented "fast path" (5 alerts,
> ~8 min) and "deep path" (17 alerts, full compounding demo).
> (4) F2a prompt spec now includes explicit factor profiles per alert (HIGH/MEDIUM/LOW
> per factor) to ensure visually distinct six-factor breakdowns.
> (5) Pre-work section updated: .env copy step added (gitignored, not in clone).
> v4 copy verification step added.
> (6) Build sequence (Section 5) updated to reflect revised session plan.
> (7) Risk section updated: "demo too long" question resolved with fast/deep path design.
> (8) All Phase 2–5 prompt specs unchanged from v3.0.

---

## SECTION 0: Why v4 Exists

A customer meeting on Feb 24 surfaced a clear gap: the v3 demo is impressive but isolated. The prospect said:

1. "We collect IOCs from Pulsedive, GreyNoise, ThreatYeti." → v3 integrates one. v4 shows the pattern scales to N.
2. "We use CrowdStrike Falcon as our dashboard." → v4 positions us ON TOP of their stack, not replacing it.
3. "Can your system work with OUR data?" → v4 starts answering that with multi-source connectors.

**v3 proved the intelligence.** v4 proves it plugs into the customer's world — and makes the compounding thesis visible.

### Competitive Context

The AI SOC market has 40+ players (IDC). Key competitors: Torq ($1.2B, workflow orchestration), Dropzone AI (autonomous investigation with "Context Memory"), Intezer (forensic AI). All offer autonomous Tier-1 triage, MITRE ATT&CK mapping, and multi-source enrichment as table stakes.

**Our differentiation — Compounding Decision Intelligence — rests on three axes:**
1. Graph Accumulation: new types of knowledge compound (not just more facts)
2. Context Fine-Tuning: weights calibrate to firm-specific patterns from verified outcomes
3. Capability Extension: new scoring dimensions discovered autonomously

v4.0 Phase 5 makes all three axes visible in the demo. Without Phase 5, the compounding claim is a blog assertion. With it, the demo proves it live.

---

## SECTION 1: Version Roadmap

| Version | Theme | ACCP Capabilities | Status |
|---|---|---|---|
| v1.0 | Context graph | 1/21 | ✅ Done |
| v2.0 | Two loops + eval gates | 7/21 | ✅ Done |
| v2.5 | Interactivity + governance | 10/21 | ✅ Done |
| v3.0 | Three loops. Auditable. Connected. Transparent. | 14/18 | ✅ Done |
| v3.2 | Platform core. Multi-copilot ready. | 14/18 | ✅ Done |
| **v4.0** | **Your tools, our decisions. Compounding proved.** | **18/18** | **BUILD** |
| v4.5 | INOVA healthcare MVP + Flash Tier validated. | 18/18 + INOVA | Designed (after v4.0) |
| v5.0 | Platform thesis | 21/21 | Vision |

**v4.0 adds 4 ACCP capabilities (#17–#20) plus 3 value features (F1+F2 in Phase 1, F3+F4+F6 in Phase 5).**

---

## SECTION 2: Architecture — UCL Connectors

*(Unchanged from v2.0 — see v4_design_document_v2.md Section 2)*

---

## SECTION 3: Claude Code Rules (Apply to Every Prompt)

*(Unchanged from v2.0 — see v4_design_document_v2.md Section 3)*

**Additional rules (v4.0):**
- Do NOT use git directly. Human handles all git operations.
- Do NOT start the debugger. Log-based debugging only.
- Read before write. Check existing code before making changes.
- One concern per prompt. Don't touch unrelated code.
- Add, don't rewrite. Preserve existing behavior unless explicitly told otherwise.
- Show before/after for any file modification.

---

## SECTION 4: Feature Specifications — Phase 1

### Phase 1: UCL Connectors + Credibility Foundation (Sessions 1–4, 13 prompts)

**Dependency chain:**
```
C1 (base) → C3 (Pulsedive refactor) → C2 (GreyNoise) → C4a (aggregation) → C4b (badge)
                                                                              → C5a (CrowdStrike) → C5b (badge update)
F1a (ATT&CK seed+classifier) → F1b (ATT&CK badge UI)
F1a → F2a (expanded corpus needs ATT&CK fields) → F2b (classifier) → F2c (queue UI)
T1 (Tab 1 cross-source) — requires C2+ connectors present
```

**Session plan (max 3–4 prompts per session, test between each):**

| Session | Prompts | What | Rationale |
|---|---|---|---|
| **1** | C1 → C3 → F1a | Connector base + Pulsedive refactor + ATT&CK seed data | C1 and C3 tightly coupled (C3 uses C1's base class). F1a touches different files (seed data, situations). All backend. Three small-medium prompts. |
| **2** | C2 → C4a → C4b | GreyNoise connector + multi-source aggregation + multi-source badge | C2 follows the C3 pattern exactly (same interface, different API). C4a needs both connectors present. C4b is the frontend badge for C4a. Clean backend→frontend flow. |
| **3** | F1b → F2a → F2b → F2c | ATT&CK badge UI + expanded corpus + classifier expansion + queue UI | All "credibility foundation" work. F1b is a small frontend add. F2a is medium (seed data). F2b ensures classifier handles them. F2c is the queue UI. By end: 17 varied alerts with ATT&CK badges and a sortable queue. |
| **4** | C5a → C5b → T1 | CrowdStrike mock + badge update + Tab 1 cross-source queries | CrowdStrike follows established connector pattern. C5b updates existing badge. T1 is Tab 1 polish. Clean finish to Phase 1. |

**Within-session test flow (Session 1 example):**
```
Prompt C1 → Test: backend starts, ConnectorBase and ConnectorRegistry importable
Prompt C3 → Test: Pulsedive works through new connector pattern, existing enrichment unchanged
Prompt F1a → Test: curl /api/triage/alerts shows ATT&CK fields on each alert
```

---

*(Prompts C1, C3, C2, C4a, C4b, C5a, C5b, T1 — specs unchanged from v2.0)*

---

#### Prompt F1a — Backend: MITRE ATT&CK Alignment — Seed Data + Classifier

**Scope:** Add ATT&CK technique IDs to seed alerts and situation classifier output
**Files touched:**
- `backend/seed_neo4j.py` (modify — add technique_id, tactic fields to alert nodes)
- `backend/app/services/situation.py` (modify — include ATT&CK in classification output)
- `backend/app/domains/soc/situations.py` (modify — map situation types to ATT&CK tactics)

**What to build:**

1. Each seed alert gets two new properties:
   - `mitre_technique`: e.g. "T1078" (Valid Accounts)
   - `mitre_tactic`: e.g. "Initial Access"

2. Situation type → ATT&CK mapping:
   ```
   KNOWN_BENIGN → T1078 (Valid Accounts) — Initial Access
   TRAVEL_ANOMALY → T1078 (Valid Accounts) — Initial Access
   SUSPICIOUS_PATTERN → T1110 (Brute Force) — Credential Access
   KNOWN_THREAT → T1566 (Phishing) — Initial Access
   ANOMALOUS_BEHAVIOR → T1071 (Application Layer Protocol) — Command and Control
   COMPLIANCE_RISK → T1098 (Account Manipulation) — Persistence
   ```

3. `analyze_situation()` return object includes `mitre_technique` and `mitre_tactic` fields.

**Verification test:**
```
1. Start backend
2. curl http://localhost:8000/api/triage/alerts
   → each alert has mitre_technique and mitre_tactic fields
3. Analyze an alert → response includes ATT&CK classification
```

---

#### Prompt F1b — Frontend: ATT&CK Badge in Tab 3

**Scope:** Show ATT&CK technique badge alongside alert ID
**Files touched:**
- `frontend/src/components/tabs/AlertTriageTab.tsx` (modify — add badge)
- `frontend/src/lib/api.ts` (modify — include new fields in types)

**What to build:**

In the alert detail panel (Tab 3), next to the alert ID and severity, show:
```
ALERT-7823 | ⚠️ High | T1078 — Valid Accounts | Initial Access
```

Small color-coded badge. Tactic in lighter text. Links to ATT&CK technique definition (optional).

**Verification test:**
```
1. Tab 3: select an alert
2. ATT&CK badge visible next to alert ID
3. Badge shows correct technique for each alert type
```

---

#### Prompt F2a — Backend: Expanded Alert Corpus — Seed Data [UPDATED in v4]

**Scope:** Expand seed_neo4j.py with 17 alerts across 5 situation types, with demo path and factor profiles
**Files touched:**
- `backend/seed_neo4j.py` (modify — add new alerts with varied profiles)

**What to build:**

17 alerts across 5 categories. Each alert has a `demo_priority` field (1 = fast path, 2 = deep path).

| Category | Count | Alert IDs | Situation Type | ATT&CK | Demo Priority |
|---|---|---|---|---|---|
| Travel/VPN | **5** | ALERT-7823★, ALERT-7830, ALERT-7835, ALERT-7841, ALERT-7845 | KNOWN_BENIGN / TRAVEL_ANOMALY | T1078 | 7823=1, rest=2 |
| Credential/Access | 4 | ALERT-7824★, ALERT-7831, ALERT-7836, ALERT-7842 | SUSPICIOUS_PATTERN | T1110 | 7824=1, rest=2 |
| Threat Intel Match | 3 | ALERT-7825★, ALERT-7832, ALERT-7837 | KNOWN_THREAT | T1566 | 7825=1, rest=2 |
| Behavioral Anomaly | 3 | ALERT-7826★, ALERT-7833, ALERT-7838 | ANOMALOUS_BEHAVIOR | T1071 | 7826=1, rest=2 |
| Cloud/Infrastructure | 2 | ALERT-7827★, ALERT-7834 | COMPLIANCE_RISK | T1098 | 7827=1, 7834=2 |

★ = fast path alert (demo_priority: 1). Five fast-path alerts, one per category.

**Factor profiles — each alert must specify HIGH/MEDIUM/LOW per factor:**

| Category | travel_match | asset_criticality | threat_intel | time_anomaly | device_trust | pattern_history |
|---|---|---|---|---|---|---|
| Travel/VPN | **HIGH** (0.7-1.0) | LOW (0.0-0.2) | MEDIUM (0.3-0.6) | LOW | **HIGH** | LOW |
| Credential/Access | LOW | **HIGH** | LOW | **HIGH** | MEDIUM | MEDIUM |
| Threat Intel Match | LOW | MEDIUM | **HIGH** | LOW | LOW | **HIGH** |
| Behavioral Anomaly | LOW | **HIGH** | LOW | MEDIUM | MEDIUM | LOW |
| Cloud/Infrastructure | LOW | **HIGH** | LOW | LOW | LOW | **HIGH** |

This ensures the six-factor bar chart in Tab 3 is visually distinct per alert type — not just slightly different values on the same bars. When you process a phishing alert vs. a travel login, DIFFERENT factors light up.

**Within each category, vary the factor values** so that alerts of the same type aren't identical:
- ALERT-7823 (travel): travel_match=0.92, device_trust=0.85 (very benign)
- ALERT-7841 (travel): travel_match=0.58, device_trust=0.45 (more ambiguous — interesting for compounding story)

Each alert needs: distinct user, distinct asset, factor profile per the table above, severity (Critical/High/Medium/Low), ATT&CK fields, demo_priority.

**Critical:** Existing ALERT-7823 and ALERT-7824 must remain unchanged (demo scripts reference them). New alerts ADD to the corpus. The demo_priority field is added to existing alerts.

**Verification test:**
```
1. Run seed_neo4j.py
2. curl http://localhost:8000/api/triage/alerts
   → returns 17 alerts with varied types and severities
3. Existing ALERT-7823 and ALERT-7824 still present and unchanged
4. Each alert has demo_priority field (1 or 2)
5. curl http://localhost:8000/api/triage/alerts?demo_priority=1
   → returns 5 fast-path alerts, one per category
```

---

#### Prompt F2b — Backend: Situation Classifier Expansion

**Scope:** Ensure situation classifier handles all new alert types correctly
**Files touched:**
- `backend/app/services/situation.py` (modify — handle new types)
- `backend/app/domains/soc/situations.py` (modify — add new situation type logic if needed)
- `backend/app/domains/soc/factors.py` (modify — ensure factor computation works for all alert profiles)

**What to build:**

For each new alert category, the situation classifier must:
1. Correctly classify into the mapped situation type
2. Compute all 6 factors using the factor profiles from F2a (some will be LOW for certain types — that's correct)
3. Generate appropriate action options (the 4 actions remain the same, but factor profiles differ)

The key outcome: when you process a phishing alert vs. a travel login, DIFFERENT factors light up in the six-factor breakdown. travel_match is HIGH for travel alerts but LOW for phishing. pattern_history is HIGH for threat-intel matches. This makes the factor breakdown visually distinct per alert type.

**Verification test:**
```
1. Analyze a travel alert → travel_match and device_trust dominant
2. Analyze a credential alert → time_anomaly and asset_criticality dominant
3. Analyze a threat-intel alert → pattern_history and threat_intel dominant
4. Analyze a behavioral alert → VIP_status and asset_criticality dominant
5. Six-factor breakdown visually distinct for each type
```

---

#### Prompt F2c — Frontend: Alert Queue Enhancements

**Scope:** Update Tab 3 alert queue for richer corpus
**Files touched:**
- `frontend/src/components/tabs/AlertTriageTab.tsx` (modify — add sort/filter)

**What to build:**

Alert queue shows all 17 alerts with:
- Sort by severity (default), type, or tactic
- Visual severity indicators (color-coded: Critical/High/Medium/Low)
- ATT&CK tactic label on each row
- Count indicator: "17 alerts | 5 types | 4 ATT&CK tactics"
- Demo path filter: toggle to show "Fast Path (5)" or "All (17)"

**Verification test:**
```
1. Tab 3: alert queue shows 17 alerts
2. Sort by severity works
3. ATT&CK tactic visible on each row
4. Count indicator accurate
5. Fast path filter shows 5 alerts (one per category)
```

---

### Demo Path Design [NEW in v4]

The expanded corpus creates two demo paths for different time constraints:

**Fast Path (~8 minutes, 5 alerts):**
For time-constrained Loom recordings and live demos. Process one alert per category to show the system reasons differently per situation type.

| Order | Alert | Category | Purpose |
|---|---|---|---|
| 1 | ALERT-7823 | Travel/VPN | travel_match dominant — the familiar benign case |
| 2 | ALERT-7824 | Credential | time_anomaly + asset_criticality — different factors light up |
| 3 | ALERT-7825 | Threat Intel | pattern_history + threat_intel — external data changes the decision |
| 4 | ALERT-7826 | Behavioral | VIP_status — organizational context matters |
| 5 | ALERT-7827 | Cloud/Infra | asset_criticality + pattern_history — compliance dimension |

**Deep Path (~20 minutes, 17 alerts):**
For the Phase 5 compounding demo. Process all 5 travel alerts in sequence with feedback to show the compounding curve (confidence rising from ~72% to ~91%). Then process credential alerts to show a second curve. The before/after comparison (F4d) uses the travel sequence.

**Why 5 travel alerts (not 4):** Phase 5 needs enough data points for a convincing compounding curve. With 5 sequential decisions + feedback, the weight evolution chart has 5 data points — enough to show a clear trend. With 4, it's borderline.

---

### Phases 2–4

*(Prompts D1–D5, LG1–LG4, PH1–PH2, FC1 — unchanged from v2.0)*

---

### Phase 5: Compounding Proof (Sessions 10–11, 8 prompts)

**Theme:** Make the compounding thesis visible in 15 minutes.
**Prerequisite:** Phase 1 (alerts + ATT&CK) complete. Phase 3 (Live Graph) complete is ideal but not blocking.

---

#### Prompt F3a — Backend: Investigation Narrative Service

**Scope:** Generate plain-English decision narrative from situation analysis
**Files touched:**
- `backend/app/services/narrative.py` (new)
- `backend/app/routers/triage.py` (modify — add narrative to analysis response)

**What to build:**

New service that takes situation analysis result and produces a 3–5 sentence narrative:

```python
def generate_narrative(analysis_result: dict) -> str:
    """
    Example output:
    "ALERT-7823 classified as TRAVEL_ANOMALY (T1078 — Valid Accounts).
    Graph traversal: 47 nodes across 3 domains. User jsmith has 14 prior
    travel logins from APAC, all resolved as benign — travel_match weight
    elevated to 0.23 (calibrated from 12 verified outcomes). Device trust
    confirmed: corporate laptop, certificate valid. Pulsedive enrichment:
    IP 103.15.42.17 classified low-risk.
    Recommendation: false_positive_close at 91% confidence."
    """
```

Key elements of the narrative:
- Alert ID + situation type + ATT&CK reference
- Graph traversal scope (node count, domain count)
- Dominant factor explanation with calibration history reference
- Threat intel enrichment result
- Recommendation + confidence

The narrative is template-based with variable substitution — not LLM-generated. This keeps it deterministic and fast.

**Verification test:**
```
1. Analyze an alert
2. Response includes narrative field with 3-5 sentence summary
3. Narrative references ATT&CK technique, factor weights, calibration history
4. Different alert types produce different narratives
```

---

#### Prompt F3b — Frontend: Narrative Panel in Tab 3

**Scope:** Display investigation narrative alongside factor breakdown
**Files touched:**
- `frontend/src/components/tabs/AlertTriageTab.tsx` (modify — add narrative panel)

**What to build:**

Below the six-factor bar chart, add a "Decision Narrative" panel:
- Collapsible card with the narrative text
- Key phrases highlighted (ATT&CK ID, confidence %, calibration reference)
- "calibrated from N verified outcomes" in a distinct color (this is the compounding proof in natural language)

**Verification test:**
```
1. Analyze an alert → narrative panel appears below factors
2. ATT&CK reference, confidence, and calibration history highlighted
3. Panel collapses/expands
4. Different alerts produce different narratives
```

---

#### Prompt F4a — Backend: Weight Matrix Evolution History

**Scope:** Track and expose weight matrix changes over time
**Files touched:**
- `backend/app/services/evolution.py` (modify — store weight snapshots after each update)
- `backend/app/routers/evolution.py` (modify — add endpoint)

**What to build:**

1. After each weight update (AgentEvolver), store a snapshot:
   ```python
   weight_history.append({
       "decision_number": N,
       "timestamp": "...",
       "alert_type": "TRAVEL_ANOMALY",
       "weights": {"travel_match": 0.23, "asset_criticality": 0.15, ...},
       "trigger": "verified_outcome",
       "outcome": "correct"
   })
   ```

2. New endpoint: `GET /api/evolution/weight-history`
   - Returns the full weight history array
   - Optional `?alert_type=TRAVEL_ANOMALY` filter

**Verification test:**
```
1. Process 3 alerts and give feedback on each
2. curl http://localhost:8000/api/evolution/weight-history
   → returns 3 snapshots showing weight progression
3. Weights visibly different between snapshot 1 and snapshot 3
```

---

#### Prompt F4b — Backend: Confidence Trajectory Endpoint

**Scope:** Track confidence scores per alert type over time
**Files touched:**
- `backend/app/services/triage.py` (modify — store confidence per decision)
- `backend/app/routers/metrics.py` (modify — add endpoint)

**What to build:**

1. After each analysis, store: `{alert_type, confidence, decision_number, timestamp}`

2. New endpoint: `GET /api/metrics/confidence-trajectory`
   - Returns per-alert-type confidence over decisions
   - Format: `{"TRAVEL_ANOMALY": [{"decision": 1, "confidence": 0.72}, {"decision": 4, "confidence": 0.76}, ...], ...}`

**Verification test:**
```
1. Analyze 5 travel alerts (deep path) with feedback after each
2. curl http://localhost:8000/api/metrics/confidence-trajectory
   → TRAVEL_ANOMALY shows rising confidence across 5 data points
```

---

#### Prompt F4c — Frontend: Compounding Curve Panel in Tab 4

**Scope:** Visualize weight evolution and confidence trajectory
**Files touched:**
- `frontend/src/components/tabs/CompoundingTab.tsx` (modify — add panel)
- `frontend/src/lib/api.ts` (add functions)

**What to build:**

New "Compounding Proof" panel in Tab 4 (above Evidence Ledger):

**Section A: Weight Evolution Chart**
- Line chart showing weight values over decision count
- One line per factor (6 lines, color-coded)
- X-axis: decision number. Y-axis: weight value.
- Callout on significant changes: "travel_match: 0.15 → 0.23 after 4 verified outcomes"

**Section B: Confidence Trajectory**
- Line chart showing confidence per alert type over time
- One line per alert type (5 types)
- Ascending trend is the visual proof of compounding

**Section C: Summary Metrics**
- "Decisions processed: N"
- "Patterns learned: M"
- "Auto-close rate: X% → Y%"
- "Weight adjustments: K"

Header: "The Compounding Curve — Same model, same code, smarter graph."

**Verification test:**
```
1. Process 5+ alerts with feedback (deep path — all 5 travel alerts)
2. Tab 4: Compounding Proof panel visible
3. Weight evolution chart shows changing lines across 5 data points
4. Confidence trajectory shows upward trend
5. Summary metrics accurate
```

---

#### Prompt F4d — Frontend: Before/After Comparison Mode

**Scope:** Show same alert type triaged early vs. late, highlighting the difference
**Files touched:**
- `frontend/src/components/tabs/CompoundingTab.tsx` (modify — add comparison)

**What to build:**

Within the Compounding Proof panel, a "Compare" section:
- Side-by-side cards: "Decision #1" vs "Decision #5" for the same alert type (travel alerts from deep path)
- Shows: confidence score, dominant factor, weight at time of decision
- Highlighted delta: "Confidence improved 19 percentage points"
- Explainer: "Why: 4 verified outcomes calibrated travel_match weight from 0.15 to 0.23"

This is the single most important demo moment: visible proof that the system got smarter.

**Verification test:**
```
1. Process 5 travel alerts with feedback (deep path)
2. Tab 4 comparison shows Decision #1 (72%) vs Decision #5 (91%)
3. Delta and explanation clearly visible
```

---

#### Prompt F6a — Backend: Asymmetric Trust — Wrong-Decision Response

**Scope:** When feedback marks a decision incorrect, flag similar alerts for human review
**Files touched:**
- `backend/app/services/feedback.py` (modify — add trust tracking + human-routing flag)
- `backend/app/services/triage.py` (modify — check trust level before auto-close)

**What to build:**

1. Trust score per alert type, starting at 0.5:
   - Correct decision: trust += 0.03 (capped at 1.0)
   - Incorrect decision: trust -= 0.60 (floored at 0.0)
   - This is the 20:1 asymmetry

2. When trust drops below 0.3 for an alert type:
   - Flag: "HUMAN_REVIEW_REQUIRED" for next N similar alerts
   - Auto-close is blocked for that type until trust recovers

3. New endpoint: `GET /api/evolution/trust-scores`
   - Returns per-alert-type trust scores with history

**Verification test:**
```
1. Process 3 correct travel alerts → trust rises slowly
2. Mark one incorrect → trust drops sharply
3. Next travel alert shows "HUMAN_REVIEW_REQUIRED" flag
4. GET /api/evolution/trust-scores → shows the asymmetry
```

---

#### Prompt F6b — Frontend: Trust Curve Visualization

**Scope:** Visualize the asymmetric trust trajectory
**Files touched:**
- `frontend/src/components/tabs/RuntimeEvolutionTab.tsx` or `CompoundingTab.tsx` (modify — add panel)

**What to build:**

"Trust Curve" panel showing:
- Line chart: trust score over decisions (one line per alert type)
- The asymmetry is visually dramatic: slow climb, sharp drop, gradual recovery
- Annotation on drop: "Incorrect decision at #N → trust dropped from 0.62 to 0.02"
- When trust is below threshold: red "HUMAN REVIEW" badge
- Recovery annotation: "Trust recovered to 0.30 after 5 human-verified decisions"

Header: "This system earns trust slowly and loses it fast."

**Verification test:**
```
1. Process alerts with mostly correct + one incorrect feedback
2. Trust curve shows asymmetric pattern
3. "HUMAN REVIEW" badge appears after incorrect decision
4. Recovery visible after subsequent correct decisions
```

---

## SECTION 5: Build Sequence (Updated in v4)

```
PRE-WORK (human):
  1. Copy gen-ai-roi-demo-v3.2 directory → gen-ai-roi-demo-v4
  2. Copy backend\.env from v3.2 → v4 (gitignored, not in clone)
     → Verify: PULSEDIVE_API_KEY, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, GEMINI_API_KEY
     → Also check if frontend has a .env
  3. Clean docs/ per backlog Section B0
  4. Add new docs to docs/ (session_continuation_v11, backlog_v10, product_strategy_v1,
     v4_design_document_v4, v4_5_design_v6, soc_copilot_roadmap_v4, deployment_strategy_v3)
  5. Verify CLAUDE.md port references (8000/5174)
  6. Verify v3.2 still runs in ORIGINAL directory
  7. Verify v4 copy runs (confirms .env copied correctly)

SESSION 0: Verify Code Review Fixes (1 prompt)
  CR-0: Check H-1, H-2, H-3 status
  CR-1: Fix any remaining HIGH findings (if needed)
  TEST: All HIGH findings verified or fixed

PHASE 1: Connectors + Credibility (Sessions 1–4, 13 prompts)
  Session 1: C1 (base + registry) → C3 (Pulsedive refactor) → F1a (ATT&CK seed data)
    TEST: Connectors importable, Pulsedive works, alerts have ATT&CK fields
  Session 2: C2 (GreyNoise) → C4a (aggregation) → C4b (multi-source badge)
    TEST: GreyNoise enrichment works, multi-source badge shows in Tab 3
  Session 3: F1b (ATT&CK badge) → F2a (expanded corpus) → F2b (classifier) → F2c (queue UI)
    TEST: 17 alerts, ATT&CK badges, sortable queue, fast path filter
  Session 4: C5a (CrowdStrike mock) → C5b (badge update) → T1 (Tab 1 queries)
    TEST: Three sources in badge, cross-source queries in Tab 1
  PHASE 1 COMPLETE: All connectors + 17 alerts + ATT&CK + multi-source working

PHASE 2: Docker (Sessions 5–6, 5 prompts)
  Session 5: D1 (backend Dockerfile) + D2 (frontend Dockerfile)
  Session 6: D3 (compose) + D4 (seed) + D5 (README + health)
  TEST: docker-compose up works end-to-end

PHASE 2.5: VPS Hosting (Session 6.5, 3 prompts)
  VPS-1 (deploy script) + VPS-2 (reset + cron) + VPS-3 (banner + rate limit)
  TEST: demo.dakshineshwari.net accessible

PHASE 3: Live Graph (Sessions 7–8, 4 prompts)
  Session 7: LG1 (feedback writes) + LG2 (feedback reads)
  Session 8: LG3 (policy writes) + LG4 (triage writes)
  TEST: Restart backend, data persists

PHASE 4: Polish (Session 9, 3 prompts)
  Session 9: PH1 (query registry) + PH2 (did you mean) + FC1 (four clocks)
  TEST: Tab 1 suggestions work, Tab 4 clocks visible

PHASE 5: Compounding Proof (Sessions 10–11, 8 prompts)
  Session 10: F3a (narrative service) + F3b (narrative UI) + F4a (weight history) + F4b (confidence trajectory)
  Session 11: F4c (compounding curve panel) + F4d (before/after) + F6a (trust backend) + F6b (trust UI)
  TEST: Run deep path (17 alerts). Tab 4 shows compounding curve with 5 travel data points.
        Before/after comparison visible. Trust curve shows asymmetry.
        15-minute demo proves compounding live. Loom v3 can be recorded.

TAG: v4.0 — "Your tools, our decisions. Compounding proved."
```

**Total: 33 code prompts + 3 VPS prompts = 36 prompts across ~13 sessions.**

---

## SECTION 6: Demo-Blog Alignment (Post-v4)

| Blog Claim | v3 Reality | v4 Reality |
|---|---|---|
| "Three cross-layer loops" | ✅ Demo shows three | ✅ Same |
| "Four dependency-ordered layers" | ✅ Four Layers strip | ✅ UCL now has real connectors |
| "Cross-domain discovery" | Partial (Pulsedive only) | **✅ Three sources, cross-correlations visible** |
| "Living graph" | Partial (in-memory state) | **✅ Neo4j reads/writes persist** |
| "$127K/quarter cost avoided" | ✅ Banner | ✅ Same |
| "Audit trail / compliance" | ✅ Evidence Ledger | ✅ Same |
| "MITRE ATT&CK alignment" | ✗ No ATT&CK language | **✅ Technique IDs + tactic labels on every alert** |
| "Compounding curve visible" | ✗ Claimed in blog, not shown | **✅ Weight evolution + confidence trajectory + before/after (5 data points per type)** |
| "Asymmetric trust (20:1)" | Partial (Loop 3 panel) | **✅ Trust curve + HUMAN_REVIEW auto-routing** |
| "Investigation narrative" | ✗ Quantitative only | **✅ Plain-English decision summary** |

---

## SECTION 7: Key Soundbites (v4-specific)

### For CISOs

| Feature | Soundbite |
|---|---|
| Multi-source | "Pulsedive, GreyNoise, and CrowdStrike. Three sources. One graph." |
| ATT&CK | "Every alert carries a MITRE technique ID. Your team speaks this language. So does our system." |
| Compounding proof | "Decision #1: 72% confidence. Decision #5: 91%. Same alert type. Here's exactly what changed." |
| Trust asymmetry | "Watch what happens when the system gets one wrong. Twenty-to-one penalty. It earns trust slowly and loses it fast." |
| Investigation narrative | "Six factors plus a plain-English explanation. No black box." |
| Competitive | "Torq automates your playbooks. Dropzone remembers your facts. We develop your institutional judgment." |

### For VCs

| Feature | Soundbite |
|---|---|
| Three axes | "Graph accumulation, context fine-tuning, capability extension. Three axes of compounding. No competitor has any of them." |
| Moat | "They rent intelligence — LLM API calls. We build it — a compounding graph that appreciates with use." |
| Platform | "Same architecture, different domain. SOC today. Supply chain, financial services — same loops, new domain module." |
| Dropzone comparison | "Their Context Memory accumulates facts. Our system accumulates judgment. There's a structural difference." |

---

## SECTION 8: API Keys

*(Unchanged from v2.0)*

---

## SECTION 9: Risk and Open Questions (Updated in v4)

| Question | Impact | When to Resolve | Status |
|---|---|---|---|
| GreyNoise 50/week rate limit for repeated demos | May need aggressive caching or fallback | Test during C2 build | Open |
| CrowdStrike Falcon public schema accuracy | Mock credibility | Research before C5 | Open |
| Live Graph migration breaks existing flows | Regression risk | Careful testing in LG1-LG4 | Open |
| Docker + Neo4j Aura — partner isolation | Each partner needs own Aura instance | Document in PARTNER_README | Open |
| Can F4 compounding proof be convincing with synthetic data? | **High — this is the thesis** | Test during Phase 5 build | Open |
| ~~Will 15-20 alerts make the demo too long?~~ | ~~Medium~~ | ~~Design fast path~~ | **Resolved: Fast path (5 alerts, ~8 min) and deep path (17 alerts) designed. demo_priority field + queue filter.** |
| ATT&CK technique mapping accuracy | Medium — don't over-engineer | Start with taxonomy labels, add detection logic later | Open |
| Narrative template quality | Medium — must sound credible to analysts | Review with domain knowledge before Loom v3 | Open |

---

## Appendix: Version History

| Version | Date | Changes |
|---|---|---|
| **1.0** | **Feb 24, 2026** | Initial v4 design. 20 prompts, 8 sessions. |
| **2.0** | **Feb 26, 2026** | Sequential build. Prerequisite updated to v3.2. |
| **3.0** | **Feb 26, 2026** | Value features merged. F1 + F2 in Phase 1. F3 + F4 + F6 as Phase 5. 33 prompts, 11 sessions. |
| **4.0** | **Feb 26, 2026** | **Phase 1 sessions rebalanced (max 3–4 prompts each). F2a corpus expanded to 17 alerts (5 travel). demo_priority field + fast/deep path design. Explicit factor profiles (HIGH/MEDIUM/LOW) per alert category. Pre-work updated with .env copy + v4 verification. F2c adds fast path filter. F4b/F4c/F4d verification tests reference 5 travel data points. "Demo too long" risk resolved.** |

---

*SOC Copilot Demo — v4.0 Design Document v4 | February 26, 2026*
*Theme: "Your tools, our decisions. Compounding proved." | 33 code + 3 VPS prompts, ~13 sessions | Prerequisite: v3.2 tagged*
