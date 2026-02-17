# SOC Copilot Demo v2 — Implementation Plan

**Version:** 1.0
**Date:** February 17, 2026
**Status:** In Progress
**Working Directory:** `gen-ai-roi-demo-v2` (cloned from main, branch: `feature/v2-enhancements`)

---

## Prerequisites & Current State

### What's Running
| Component | Directory | Branch | Ports | Status |
|-----------|-----------|--------|-------|--------|
| **v1 (LIVE — DO NOT TOUCH)** | `gen-ai-roi-demo` | `main` (tag: v1.0) | 8000 / 5173 | ✅ Running |
| **v2 (DEVELOPMENT)** | `gen-ai-roi-demo-v2` | `feature/v2-enhancements` | 8001 / 5174 | ✅ Running |

### Infrastructure
- **Neo4j Aura:** Shared between v1 and v2 (same `.env` credentials)
- **Git:** GitHub repo at `github.com/[USER]/gen-ai-roi-demo`, v1.0 tagged
- **IDE:** VSCode with Claude Code; PowerShell terminal
- **Frontend port config:** `frontend/vite.config.ts` line 19 → `target: 'http://localhost:8001'`

### Key Reference Documents
| Document | Location | Purpose |
|----------|----------|---------|
| `demo_changes_v2.pdf` | `support/docs/` | Original 7-phase plan (restructured below) |
| `SOC_Copilot_Demo_v2_Design_Spec.md` | `docs/` | Fuller v2 vision (ambitious — partially deferred) |
| `CLAUDE.md` | Root | Claude Code context file |
| `PROJECT_STRUCTURE.md` | Root | Living architecture doc (update after each wave) |
| `CODE_REVIEW.md` | Root | Living code review doc (update after each wave) |

---

## Implementation Structure: 6 Waves, 15 Prompts

### Design Principles
1. **Each prompt does ONE testable thing** — verify before moving to the next
2. **Backend before frontend** — data models stable before UI touches them
3. **Documentation after each wave** — not batched at the end
4. **Sequential over parallel** — Claude Code works better seeing previous output
5. **Highest demo-impact first** — labels and blocking demo before deep features

---

## WAVE 1: Labels + Quick Visual Wins (Day 1)

**Goal:** Visually new in 2-3 hours. Zero backend changes.

### Prompt 1A — CONSUME / MUTATE / ACTIVATE Labels
**Scope:** Add colored badge labels to existing panels in Tabs 2 and 3. Pure frontend CSS + text.
**Files touched:**
- `frontend/src/components/tabs/RuntimeEvolutionTab.tsx`
- `frontend/src/components/tabs/AlertTriageTab.tsx`
- `frontend/src/index.css` (new utility classes)

**What to add:**
| Tab | Panel | Label | Color |
|-----|-------|-------|-------|
| Tab 2 | Eval gate section | CONSUME ✓ | Blue (#3B82F6) |
| Tab 2 | TRIGGERED_EVOLUTION panel | MUTATE ✓ | Purple (#8B5CF6) |
| Tab 3 | Graph traversal | CONSUME | Blue (#3B82F6) |
| Tab 3 | Closed loop panel | ACTIVATE | Green (#10B981) |

**Verify:** All 4 tabs still work. Labels appear in correct positions.

### Prompt 1B — Eval Gate Sequential Animation
**Scope:** Tab 2 only. The 4 eval gate checks (Faithfulness, Safe Action, Playbook, SLA) appear one by one with 400ms delay instead of all at once.
**Files touched:**
- `frontend/src/components/tabs/RuntimeEvolutionTab.tsx`

**Verify:** Click "Process Alert" → eval checks appear sequentially, ~1.6s total.

### Prompt 1C — Counter Animations in Tab 4
**Scope:** Tab 4 only. Week 1 → Week 4 numbers count up instead of static display.
**Files touched:**
- `frontend/src/components/tabs/CompoundingTab.tsx`

**Implementation:** Simple `useEffect` + `requestAnimationFrame` counter hook, or install `react-countup`. Duration: 1.5s, easing: ease-out. Triggered when tab becomes visible.

**Verify:** Switch to Tab 4 → numbers count up from Week 1 to Week 4 values.

### Post-Wave 1
- [ ] Run documentation update prompt (PROJECT_STRUCTURE.md, CODE_REVIEW.md)
- [ ] `git add . && git commit -m "feat(v2): Wave 1 — CMA labels, eval gate animation, counter animation"`
- [ ] `git push origin feature/v2-enhancements`

---

## WAVE 2: Blocking Demo (Day 2)

**Goal:** Highest demo-impact per line of code. CISOs always ask "what if the AI is wrong?"

### Prompt 2A — Failed Gate Backend + Frontend
**Scope:** Self-contained feature. ~30 lines backend + ~40 lines frontend.
**Backend changes:**
- Add `POST /api/alert/process-blocked` endpoint in `routers/evolution.py`
- Returns eval gate response with one check failing (e.g., `safe_action`)
- Include `blocked: true`, `failed_check`, `reason` fields

**Frontend changes:**
- Add "Simulate Failed Gate" button below "Process Alert" in RuntimeEvolutionTab.tsx
- When clicked: show eval gate with one check failing (red X + blocked message)
- Clear visual distinction from success path (red border, warning icon)

**Verify:**
1. Click "Process Alert" → all 4 checks pass (green) → success
2. Click "Simulate Failed Gate" → one check fails (red) → blocked message

### Post-Wave 2
- [ ] Run documentation update prompt
- [ ] `git add . && git commit -m "feat(v2): Wave 2 — eval gate blocking demo"`
- [ ] `git push origin feature/v2-enhancements`

---

## WAVE 3: Situation Analyzer — Backend (Days 3-4)

**Goal:** Data foundation before touching UI.

### Prompt 3A — Situation Models + Classification Logic
**Scope:** Backend only. New service file + model updates.
**Files to create:**
- `backend/app/services/situation.py` (~100 lines)

**Files to update:**
- `backend/app/models/schemas.py` (add new Pydantic models)

**Contents of situation.py:**
- `SituationType` enum: TRAVEL_LOGIN_ANOMALY, KNOWN_PHISHING_CAMPAIGN, MALWARE_ON_CRITICAL_ASSET, VIP_AFTER_HOURS, DATA_EXFIL_ATTEMPT, UNKNOWN
- `classify_situation(alert, context)` — rule-based, mirrors agent.py style
- `evaluate_options(alert, context, situation_type)` — returns list of `{action, score, factors}`, scores sum to ~1.0
- `SituationAnalysis` Pydantic model: situation_type, situation_confidence, factors_detected, options_evaluated, selected_option, selection_reasoning

**Verify:** Import works, no syntax errors. Unit test with sample data.

### Prompt 3B — Wire Situation Analysis into API
**Scope:** Update API to call `analyze_situation()` and return results.
**Files to update:**
- `backend/app/routers/evolution.py` or `routers/triage.py` (update `/api/alert/process`)

**Changes:** Call `analyze_situation()` in the process flow, add `situation_analysis` to response JSON. Frontend ignores extra fields (no breakage).

**Verify:** `curl -X POST http://localhost:8001/api/alert/process -H "Content-Type: application/json" -d '{"alert_id":"ALERT-7823"}'` returns `situation_analysis` object with type, confidence, factors, options.

### Post-Wave 3
- [ ] Run documentation update prompt
- [ ] `git add . && git commit -m "feat(v2): Wave 3 — Situation Analyzer backend (models + API)"`
- [ ] `git push origin feature/v2-enhancements`

---

## WAVE 4: Situation Analyzer — Frontend (Days 4-5)

**Goal:** Make Loop 1 visible in Tab 3.

### Prompt 4A — Situation Analyzer Panel in Tab 3
**Scope:** Largest single UI change. New panel between graph viz and recommendation.
**Files to update:**
- `frontend/src/components/tabs/AlertTriageTab.tsx`
- Possibly extract to new component: `SituationAnalyzerPanel.tsx`

**Panel contents:**
1. Situation type badge (e.g., "TRAVEL_LOGIN_ANOMALY") with colored background
2. Classification confidence percentage
3. Factors detected — checkmark list (✓ Active travel record, ✓ MFA completed, etc.)
4. Options evaluated — horizontal bar chart (3 bars showing scores: FALSE_POSITIVE_CLOSE 92%, ESCALATE_TIER2 6%, ENRICH_AND_WAIT 2%)
5. Selected option highlighted with distinct styling

**Reads from:** `situation_analysis` field added in Prompt 3B.

**Verify:** Select alert in Tab 3 → see situation classification + options bar chart before the recommendation panel.

### Post-Wave 4
- [ ] Run documentation update prompt
- [ ] `git add . && git commit -m "feat(v2): Wave 4 — Situation Analyzer panel in Tab 3 (Loop 1 visible)"`
- [ ] `git push origin feature/v2-enhancements`

**MILESTONE: Loop 1 story is now visible and demoable.**

---

## WAVE 5: AgentEvolver + Second Alert (Days 5-7)

**Goal:** Complete the "two loops" narrative.

### Prompt 5A — AgentEvolver Backend
**Scope:** New service file + API wiring.
**Files to create:**
- `backend/app/services/evolver.py` (~80 lines)

**Files to update:**
- `backend/app/routers/evolution.py` (add `prompt_evolution` to response)
- `backend/app/models/schemas.py` (add PromptVariant model)

**Contents of evolver.py:**
- In-memory `PROMPT_STATS` dict: `{"TRAVEL_CONTEXT_v1": {success: 24, total: 34}, "TRAVEL_CONTEXT_v2": {success: 42, total: 47}, ...}`
- `ACTIVE_PROMPTS` dict: `{"anomalous_login": "TRAVEL_CONTEXT_v2", "phishing": "PHISHING_RESPONSE_v1"}`
- `get_prompt_variant(alert_type)` → returns active prompt name
- `record_decision_outcome(decision_id, prompt_variant, success)` → updates stats
- `check_for_promotion(alert_type)` → checks if a better variant should be promoted

**Verify:** API response includes `prompt_evolution` field with variant name, success rate, comparison.

### Prompt 5B — AgentEvolver Panel in Tab 2
**Scope:** New UI section in RuntimeEvolutionTab.tsx below TRIGGERED_EVOLUTION panel.
**Files to update:**
- `frontend/src/components/tabs/RuntimeEvolutionTab.tsx`

**Panel contents:**
1. Header: "Agent Evolution (Loop 2: Smarter ACROSS decisions)"
2. Current prompt variant name + success rate
3. Comparison bar: v1 (71%) vs v2 (89%)
4. "Promoted ✓" badge if evolution occurred
5. MUTATE label (purple)

**Verify:** Click "Process Alert" → see AgentEvolver panel below TRIGGERED_EVOLUTION with prompt comparison.

### Prompt 5C — Second Alert Type (Phishing)
**Scope:** Backend data + minimal frontend.
**Files to update:**
- `backend/app/services/agent.py` (ensure phishing rules work)
- `backend/app/services/situation.py` (add KNOWN_PHISHING_CAMPAIGN classification)
- `backend/seed_neo4j.py` (add ALERT-7824 phishing data, PAT-PHISH-KNOWN pattern)
- `frontend/src/components/tabs/AlertTriageTab.tsx` (alert queue shows both alerts)

**New data:**
- ALERT-7824: Phishing attempt on Mary Chen, Engineering Lead
- PAT-PHISH-KNOWN pattern with campaign matching
- KNOWN_PHISHING_CAMPAIGN situation type

**Verify:**
1. Tab 3 alert queue shows 2+ alerts including ALERT-7824
2. Selecting ALERT-7824 shows different situation type (KNOWN_PHISHING_CAMPAIGN)
3. Different options evaluated (AUTO_REMEDIATE dominant instead of FALSE_POSITIVE_CLOSE)

### Post-Wave 5
- [ ] Run documentation update prompt
- [ ] `git add . && git commit -m "feat(v2): Wave 5 — AgentEvolver + phishing alert (both loops complete)"`
- [ ] `git push origin feature/v2-enhancements`

**MILESTONE: Both loops visible. Two alert types. Core v2 narrative complete.**

---

## WAVE 6: Tab 4 Enhancement + Final Polish (Days 7-8)

**Goal:** Hero visual for VCs. Complete the compounding story.

### Prompt 6A — Two-Loop Diagram in Tab 4
**Scope:** New visual component in CompoundingTab.tsx.
**Files to update:**
- `frontend/src/components/tabs/CompoundingTab.tsx`

**Visual:** Two-loop diagram showing:
- Context Graph (center) — "Neo4j"
- Loop 1: Situation Analyzer — "Smarter WITHIN each decision" → Demo: Tab 3
- Loop 2: Agent Evolver — "Smarter ACROSS all decisions" → Demo: Tab 2
- Both arrows pointing back to graph: "TRIGGERED_EVOLUTION"
- Built with React divs + CSS or SVG (no heavy library)

**New metrics to add:**
- Situation types handled: Week 1 (2) → Week 4 (6)
- Prompt variants evolved: Week 1 (0) → Week 4 (4)

**Verify:** Tab 4 shows the two-loop diagram with proper labels and new metrics.

### Prompt 6B — Cross-Alert Statistics in Tab 4
**Scope:** Add pattern breakdown by alert type.
**Files to update:**
- `backend/app/routers/metrics.py` (add by-type breakdown to compounding endpoint)
- `frontend/src/components/tabs/CompoundingTab.tsx`

**Shows:** "47 travel patterns, 31 phishing patterns" — proves generalization.

**Verify:** Tab 4 shows breakdown section with per-alert-type pattern counts.

### Prompt 6C — Final Documentation Update
**Scope:** Comprehensive update to all project docs.
**Files to update:**
- `PROJECT_STRUCTURE.md` — new files, new endpoints, new components
- `CODE_REVIEW.md` — updated architecture notes
- `CLAUDE.md` — add v2 sections (Situation Analyzer, AgentEvolver, second alert type)
- `README.md` — update feature list, screenshots placeholder

**Verify:** All docs reflect current state of codebase.

### Post-Wave 6
- [ ] `git add . && git commit -m "feat(v2): Wave 6 — Tab 4 two-loop diagram + cross-alert stats + docs"`
- [ ] `git push origin feature/v2-enhancements`
- [ ] Consider PR to merge to main when ready

**MILESTONE: v2 complete. All 6 waves done. Full demo flow operational.**

---

## DEFERRED TO v2.5 / v3

These features are from `SOC_Copilot_Demo_v2_Design_Spec.md` and are valuable but not critical for the next demo round.

### v2.5 — Near-Term Additions
| Feature | Spec Reference | Estimated Effort | Notes |
|---------|---------------|-----------------|-------|
| **3 Scenarios (Travel + Malware + CEO)** | Design Spec §2.1 | 2-3 days | Scenario selector UI with 3 cards; needs 2 more seed alerts + agent rules |
| **ROI Calculator** | Design Spec §3.1 | 1-2 days | Interactive sliders; prospect inputs their numbers, sees savings |
| **SIEM Comparison Side-by-Side** | Design Spec §2.3 | 1 day | Split view: Traditional SIEM vs SOC Copilot handling same alert |
| **Streaming "Thinking" Display (SSE)** | Design Spec §1.1 | 2-3 days | Backend sends Server-Sent Events for reasoning steps; high visual impact but requires architecture change |

### v3 — Longer-Term Vision
| Feature | Notes |
|---------|-------|
| Animated graph traversal (D3/React Flow) | Major rewrite of Tab 3 graph component |
| Sound design | Howler.js; optional but powerful for live demos |
| Full AgentEvolver with runtime prompt swapping | Currently simulated; would need actual prompt A/B testing |
| Multi-copilot support | Multiple domain copilots sharing the same UCL |
| Evidence Ledger with 7-year retention | Compliance feature for enterprise sales |
| Governance-as-code | Policy engine integration |

---

## Docker & Partner Enablement (Post v2)

Docker setup was initially prioritized but deferred to after v2 features are complete. The plan:

1. Create `docker/` directory with Dockerfiles, compose, scripts
2. Three-tier approach: Zero Cloud / Cloud-Lite / Full Cloud
3. Partner onboarding guide (already in `support/docs/PARTNER_ONBOARDING_GUIDE.pdf`)
4. Specs exist in `support/docs/Docker_README.pdf`

Will be implemented as a separate feature branch after v2 merges to main.

---

## Session Continuity Notes

### If resuming in a new conversation:
1. Reference this document: `docs/V2_IMPLEMENTATION_PLAN.md`
2. Check which waves are complete by looking at git log: `git log --oneline`
3. Check current branch: should be `feature/v2-enhancements`
4. The v2 directory runs on ports 8001 (backend) / 5174 (frontend)
5. Start backend: `uvicorn app.main:app --reload --port 8001`
6. Start frontend: `npx vite --port 5174`

### Claude Code prompt format:
Each prompt in this plan maps to one Claude Code instruction. The prompts should:
- Reference this plan by wave/prompt number (e.g., "Implement Prompt 1A from V2_IMPLEMENTATION_PLAN.md")
- Include the specific files to create/modify
- Include verification steps
- Ask Claude Code to NOT touch files outside the listed scope

### Git workflow:
```bash
# After each wave
git add .
git commit -m "feat(v2): Wave N — description"
git push origin feature/v2-enhancements

# When v2 is complete
# Create PR on GitHub: feature/v2-enhancements → main
# After merge, update v1 directory: cd gen-ai-roi-demo && git pull origin main
```

---

## Session Log

| Session | Date | Waves Completed | Key Notes |
|---------|------|-----------------|-----------|
| Session 1 | 2026-02-17 | Wave 1 + Wave 2 | CMA labels, eval gate animation, counter animation, blocking demo. All verified working on ports 8001/5174. |

---

## Progress Tracker

| Wave | Prompt | Description | Status | Date |
|------|--------|-------------|--------|------|
| 1 | 1A | CONSUME/MUTATE/ACTIVATE labels | ✅ Complete | 2026-02-17 |
| 1 | 1B | Eval gate sequential animation | ✅ Complete | 2026-02-17 |
| 1 | 1C | Counter animations Tab 4 | ✅ Complete | 2026-02-17 |
| 1 | Doc | Update PROJECT_STRUCTURE + CODE_REVIEW | ⬜ Deferred to Wave 6C | |
| 2 | 2A | Blocking demo (backend + frontend) | ✅ Complete | 2026-02-17 |
| 2 | Doc | Update docs | ⬜ Deferred to Wave 6C | |
| 3 | 3A | Situation models + classification | ⬜ Not started | |
| 3 | 3B | Wire into API | ⬜ Not started | |
| 3 | Doc | Update docs | ⬜ Not started | |
| 4 | 4A | Situation Analyzer panel (Tab 3) | ⬜ Not started | |
| 4 | Doc | Update docs | ⬜ Not started | |
| 5 | 5A | AgentEvolver backend | ⬜ Not started | |
| 5 | 5B | AgentEvolver panel (Tab 2) | ⬜ Not started | |
| 5 | 5C | Second alert type (phishing) | ⬜ Not started | |
| 5 | Doc | Update docs | ⬜ Not started | |
| 6 | 6A | Two-loop diagram (Tab 4) | ⬜ Not started | |
| 6 | 6B | Cross-alert statistics | ⬜ Not started | |
| 6 | 6C | Final documentation update | ⬜ Not started | |

---

*V2 Implementation Plan v1.0 | February 17, 2026*
*Source specs: demo_changes_v2.pdf, SOC_Copilot_Demo_v2_Design_Spec.md*
