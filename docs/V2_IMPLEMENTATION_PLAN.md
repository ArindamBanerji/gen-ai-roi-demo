# SOC Copilot Demo v2 — Implementation Plan

**Version:** 2.0 (Revised)
**Date:** February 17, 2026
**Status:** ✅ Complete — All 6 Waves Implemented
**Working Directory:** `gen-ai-roi-demo-v2` (branch: `feature/v2-enhancements`)

---

## Prerequisites & Current State

### What's Running
| Component | Directory | Branch | Ports | Status |
|-----------|-----------|--------|-------|--------|
| **v1 (LIVE — DO NOT TOUCH)** | `gen-ai-roi-demo` | `main` (tag: v1.0) | 8000 / 5173 | ✅ Running |
| **v2 (DEVELOPMENT)** | `gen-ai-roi-demo-v2` | `feature/v2-enhancements` | 8001 / 5174 | ✅ Running |

### Infrastructure
- **Neo4j Aura:** Shared between v1 and v2 (same `.env` credentials)
- **Git:** GitHub repo `git@github.com:ArindamBanerji/gen-ai-roi-demo.git`, v1.0 tagged
- **IDE:** VSCode with Claude Code; PowerShell terminal
- **Frontend port config:** `frontend/vite.config.ts` → `target: 'http://localhost:8001'`

### Key Reference Documents
| Document | Location | Purpose |
|----------|----------|---------|
| `demo_changes_v2.pdf` | `support/docs/` | Original 7-phase plan (restructured below) |
| `SOC_Copilot_Demo_v2_Design_Spec.md` | `docs/` | Fuller v2 vision (partially deferred) |
| `CLAUDE.md` | Root | Claude Code context file |
| `PROJECT_STRUCTURE.md` | Root | Living architecture doc (update in 6E) |
| `CODE_REVIEW.md` | Root | Living code review doc (update in 6E) |

---

## Implementation Structure: 6 Waves + Deferred Wave 7

### Design Principles
1. **Each prompt does ONE testable thing** — verify before moving to the next
2. **Backend before frontend** — data models stable before UI touches them
3. **Documentation after each wave** — not batched at the end
4. **Sequential over parallel** — Claude Code works better seeing previous output
5. **Business impact visible** — every feature should answer "so what does this do for me Monday morning?"

---

## WAVE 1: Labels + Quick Visual Wins ✅ COMPLETE

### Prompt 1A — CONSUME / MUTATE / ACTIVATE Labels ✅
Added colored badge labels to Tabs 2 and 3.

### Prompt 1B — Eval Gate Sequential Animation ✅
Eval gate checks appear one by one with 800ms delay.

### Prompt 1C — Counter Animations in Tab 4 ✅
Week 4 numbers count up over 3 seconds with ease-out.

### Additional: Version bump + animation speed tuning ✅

---

## WAVE 2: Blocking Demo ✅ COMPLETE

### Prompt 2A — Failed Gate Backend + Frontend ✅
"Simulate Failed Gate" button in Tab 2. Shows eval gate failure with BLOCKED banner.

---

## WAVE 3: Situation Analyzer — Backend ✅ COMPLETE

### Prompt 3A — Situation Models + Classification Logic ✅
Created `backend/app/services/situation.py` with SituationType enum, classify_situation(), evaluate_options(), analyze_situation().

### Prompt 3B — Wire Situation Analysis into API ✅
Added situation_analysis to /api/alert/process, /api/alert/process-blocked, and /api/alert/analyze responses.

---

## WAVE 4: Situation Analyzer — Frontend ✅ COMPLETE

### Prompt 4A — Situation Analyzer Panel in Tab 3 ✅
New panel between graph viz and recommendation showing situation type badge, factors, options bar chart, reasoning.

---

## WAVE 5: AgentEvolver + Second Alert ✅ COMPLETE

### Prompt 5A — AgentEvolver Backend ✅
Created `backend/app/services/evolver.py` with prompt tracking, promotion logic, wired into API.

### Prompt 5B — AgentEvolver Panel in Tab 2 ✅
New panel below TRIGGERED_EVOLUTION showing variant comparison bars and promotion status.

### Prompt 5C — Second Alert Type (Phishing) ✅
Added ALERT-7824 (Mary Chen phishing), PAT-PHISH-KNOWN pattern, PhishingCampaign node, seed data.

---

## WAVE 6: Business Impact + Tab 4 + Documentation (CURRENT)

**Goal:** Transform architecture language into CISO language. Make every feature answer "so what does this save me?"

### Prompt 6A — Situation Analyzer: Decision Economics
**Scope:** Add time/cost/risk dimensions to each evaluated option.

**Backend changes (situation.py):**
- Update `OptionEvaluated` model to include:
  - `estimated_resolution_time`: string (e.g., "3 sec", "45 min")
  - `estimated_analyst_cost`: float (e.g., 0, 127, 43)
  - `risk_if_wrong`: string (e.g., "Low", "None", "Medium")
- Populate these fields in `evaluate_options()` for each situation type
- Add `decision_economics` summary to `SituationAnalysis`:
  - `time_saved`: string (e.g., "42 minutes vs manual triage")
  - `cost_avoided`: string (e.g., "$127 analyst cost avoided")
  - `monthly_projection`: string (e.g., "At 200 similar alerts/month: 150 analyst-hours, $25K saved")

**Frontend changes (AlertTriageTab.tsx):**
- Update options bar chart to show time/cost/risk columns alongside each bar
- Add "Decision Economics" summary box below options
- Dollar/clock icons for visual anchoring

**Verify:** Select ALERT-7823 → options show time/cost/risk → economics summary visible.

### Prompt 6B — AgentEvolver: Operational Impact Narrative
**Scope:** Translate prompt evolution into business impact language.

**Backend changes (evolver.py):**
- Update `PromptEvolution` model to include:
  - `what_changed_narrative`: string (plain English)
  - `operational_impact`: dict with fewer_false_escalations_pct, fewer_false_escalations_monthly, analyst_hours_recovered, estimated_monthly_savings, missed_threats (always 0)
- Populate based on old vs new variant success rate difference

**Frontend changes (RuntimeEvolutionTab.tsx):**
- Add "What changed" section with narrative
- Add "Operational Impact" section with business metrics
- Keep variant comparison bars with added context

**Verify:** Process alert → AgentEvolver shows narrative + operational impact numbers.

### Prompt 6C — Impact Summary Banner in Tab 4
**Scope:** Aggregate business impact into headline numbers.

**Backend changes (metrics router):**
- Update `/api/metrics/compounding` to include `business_impact` summary

**Frontend changes (CompoundingTab.tsx):**
- Prominent banner at top with 4 headline metrics:
  - Analyst Hours Saved: 847/month
  - Cost Avoided: $127K/quarter
  - MTTR Reduction: 75%
  - Alert Backlog Eliminated: 2,400/month
- Counter animation on headline numbers
- Large bold numbers with icons

**Verify:** Tab 4 shows impact banner with animated numbers.

### Prompt 6D — Two-Loop Diagram in Tab 4
**Scope:** Hero visual showing both loops feeding same graph.

**Frontend changes (CompoundingTab.tsx):**
- Two-loop diagram: Context Graph center, Loop 1 (Situation Analyzer), Loop 2 (Agent Evolver)
- Both arrows back to graph via TRIGGERED_EVOLUTION
- New metrics: situation types (2→6), prompt variants (0→4)
- Cross-alert breakdown: 47 travel, 31 phishing patterns

**Verify:** Tab 4 shows two-loop diagram with labels and stats.

### Prompt 6E — Documentation Update (PROJECT_STRUCTURE + CODE_REVIEW + CLAUDE.md)
**Scope:** Comprehensive refresh of all project docs to reflect v2 state.

**Files to update:**
- `PROJECT_STRUCTURE.md` — all new files, endpoints, components, services
- `CODE_REVIEW.md` — architecture decisions, new services, design patterns
- `CLAUDE.md` — v2 sections (Situation Analyzer, AgentEvolver, decision economics, phishing)
- `README.md` — updated feature list, v2 highlights

**Verify:** Docs reflect actual codebase. New developer could understand the project.

### Post-Wave 6
- [ ] `git add . && git commit -m "feat(v2): Wave 6 — business impact, two-loop diagram, documentation"`
- [ ] `git push origin feature/v2-enhancements`
- [ ] Consider PR to merge to main

**MILESTONE: v2 complete. CISO-ready demo with visible business impact.**

---

## DEFERRED TO v2.5 / v3

### v2.5 — Near-Term (Wave 7+)
| Feature | Estimated Effort | Notes |
|---------|-----------------|-------|
| **ROI Calculator** | 2-3 prompts | Interactive sliders; prospect inputs their numbers. Strongest CISO closer. |
| **3 Scenarios (Travel + Malware + CEO)** | 2-3 days | Scenario selector UI with 3 cards |
| **SIEM Comparison Side-by-Side** | 1 day | Split view: SIEM vs SOC Copilot |
| **Streaming "Thinking" Display (SSE)** | 2-3 days | Real-time reasoning; requires backend change |

### v3 — Longer-Term
| Feature | Notes |
|---------|-------|
| Animated graph traversal (D3/React Flow) | Major rewrite of Tab 3 graph |
| Sound design | Optional but powerful for live demos |
| Full AgentEvolver with runtime prompt swapping | Currently simulated |
| Multi-copilot support | Multiple domain copilots sharing UCL |
| Evidence Ledger with 7-year retention | Compliance feature |

---

## Docker & Partner Enablement (Post v2)

Deferred to after v2 features complete. Plan:
1. `docker/` directory with Dockerfiles, compose, scripts
2. Three-tier: Zero Cloud / Cloud-Lite / Full Cloud
3. Partner onboarding guide (exists in `support/docs/PARTNER_ONBOARDING_GUIDE.pdf`)
4. Docker specs in `support/docs/Docker_README.pdf`

---

## Session Continuity Notes

### If resuming in a new conversation:
1. Reference this document: `docs/V2_IMPLEMENTATION_PLAN.md`
2. Check git log: `git log --oneline -10`
3. Check branch: `git branch` → should be `feature/v2-enhancements`
4. Ports: 8001 (backend) / 5174 (frontend)
5. Start backend: `cd backend && uvicorn app.main:app --reload --port 8001`
6. Start frontend: `cd frontend && npx vite --port 5174`
7. If Neo4j is paused: resume at https://console.neo4j.io

### Git workflow:
```bash
# After each prompt or wave
git add .
git commit -m "feat(v2): Wave N — description"
git push origin feature/v2-enhancements

# When v2 complete: PR feature/v2-enhancements → main on GitHub
```

### Key files created/modified in v2:
```
NEW FILES:
  backend/app/services/situation.py    — Situation Analyzer (Wave 3)
  backend/app/services/evolver.py      — AgentEvolver (Wave 5)
  docs/V2_IMPLEMENTATION_PLAN.md       — This file

MODIFIED FILES:
  frontend/src/App.tsx                 — Version bump (Wave 1)
  frontend/src/components/tabs/RuntimeEvolutionTab.tsx  — Labels, animation, blocking, AgentEvolver panel
  frontend/src/components/tabs/AlertTriageTab.tsx       — Labels, Situation Analyzer panel
  frontend/src/components/tabs/CompoundingTab.tsx       — Counter animations
  frontend/src/lib/api.ts              — processAlertBlocked() function
  backend/app/routers/evolution.py     — Blocking endpoint, situation + evolver wiring
  backend/app/routers/triage.py        — Situation analysis wiring
  backend/seed_neo4j.py                — Phishing alert seed data
  .gitignore                           — Added .claude/
```

---

## Session Log

| Session | Date | Waves Completed | Key Notes |
|---------|------|-----------------|-----------|
| Session 1 | 2026-02-17 | Wave 1 + Wave 2 | CMA labels, eval gate animation, counter animation, blocking demo. |
| Session 2 | 2026-02-17 | Waves 3-5 | Situation Analyzer, AgentEvolver, phishing alert. Both loops visible. |
| Session 3 | 2026-02-17 | Wave 6 (complete) | Decision economics, operational impact, impact banner, two-loop diagram, comprehensive documentation. All v2 features complete. |

---

## Progress Tracker

| Wave | Prompt | Description | Status | Date |
|------|--------|-------------|--------|------|
| 1 | 1A | CONSUME/MUTATE/ACTIVATE labels | ✅ Complete | 2026-02-17 |
| 1 | 1B | Eval gate sequential animation | ✅ Complete | 2026-02-17 |
| 1 | 1C | Counter animations Tab 4 | ✅ Complete | 2026-02-17 |
| 2 | 2A | Blocking demo (backend + frontend) | ✅ Complete | 2026-02-17 |
| 3 | 3A | Situation models + classification | ✅ Complete | 2026-02-17 |
| 3 | 3B | Wire into API | ✅ Complete | 2026-02-17 |
| 4 | 4A | Situation Analyzer panel (Tab 3) | ✅ Complete | 2026-02-17 |
| 5 | 5A | AgentEvolver backend | ✅ Complete | 2026-02-17 |
| 5 | 5B | AgentEvolver panel (Tab 2) | ✅ Complete | 2026-02-17 |
| 5 | 5C | Second alert type (phishing) | ✅ Complete | 2026-02-17 |
| 6 | 6A | Decision economics (Situation Analyzer) | ✅ Complete | 2026-02-17 |
| 6 | 6B | Operational impact (AgentEvolver) | ✅ Complete | 2026-02-17 |
| 6 | 6C | Impact summary banner (Tab 4) | ✅ Complete | 2026-02-17 |
| 6 | 6D | Two-loop diagram (Tab 4) | ✅ Complete | 2026-02-17 |
| 6 | 6E | Documentation (PROJECT_STRUCTURE + CLAUDE.md + README + V2_PLAN) | ✅ Complete | 2026-02-17 |

---

*V2 Implementation Plan v2.0 | February 17, 2026*
*Revised: Added business impact enhancements (6A-6C) to strengthen CISO "so what"*
