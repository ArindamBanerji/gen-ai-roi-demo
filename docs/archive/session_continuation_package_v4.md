# SOC Copilot Demo — Session Continuation Package v4

**Date:** February 18, 2026
**Status:** v2.5 Complete and Tagged. ACCP 10/18 (56%).
**Next Session Focus:** Docker for Partners (Prompts D1-D4) OR Loom v2 Script
**Repository:** git@github.com:ArindamBanerji/gen-ai-roi-demo.git
**Branch:** main (v2.5 tagged at commit e63bc85)

---

## PART 1: What Is This Project?

### The Demo

The SOC Copilot Demo is a working prototype of an AI-augmented Security Operations Center (SOC) that demonstrates **compounding intelligence** — the system gets smarter over time through two learning loops feeding one context graph. Built with FastAPI (Python) + React/TypeScript + Neo4j Aura, it runs locally on ports 8001 (backend) / 5174 (frontend).

### The Architecture: ACCP

The demo is the progressive reference implementation of the **Agentic Cognitive Control Plane (ACCP)** — an architectural pattern for governed, self-improving enterprise AI. ACCP defines five structural capabilities:

1. **Typed-Intent Bus** — normalizes signals into classified intents
2. **Situational Mesh** — scores situations using context, KPIs, and drift signals
3. **Eval Gates** — enforces structural safety checks before any action executes
4. **TRIGGERED_EVOLUTION** — writes verified outcomes back to the context graph
5. **Decision Economics** — tags every action with time, cost, and risk impact

### ACCP Progress

- v1.0: 1/18 (context graph)
- v2.0: 7/18 (+ situation classification, eval gates, TRIGGERED_EVOLUTION, decision economics, both loops)
- **v2.5 (current): 10/18** (+ ROI Calculator, Outcome Feedback, Policy Conflict)
- v3.0 (planned): 15/18 (+ Prompt Hub, live graph, external context, evidence ledger, process intelligence)

### Core Thesis

"Your SIEM gets better detection rules written by humans. Our SOC copilot gets smarter automatically through validated decisions."

### The Two Learning Loops

| Loop | Name | What It Does | Where Visible |
|---|---|---|---|
| Loop 1 | Situation Analyzer | Gets smarter WITHIN each decision — classifies alerts, evaluates options with time/cost/risk | Tab 3 |
| Loop 2 | AgentEvolver | Gets smarter ACROSS decisions — tracks prompt variant performance, auto-promotes winners | Tab 2 |

### The Four Tabs + v2.5 Features

**Tab 1: SOC Analytics** (20% energy)
- Natural language queries → governed security metrics
- Provenance showing data sources
- Rule sprawl detection ($18K/month waste found)

**Tab 2: Runtime Evolution** (35% energy) — THE DIFFERENTIATOR
- Process alert → 4 eval gates animate → TRIGGERED_EVOLUTION
- AgentEvolver panel: variant comparison, $4,800/mo recovered
- "Simulate Failed Gate" → BLOCKED banner
- Operational impact narrative

**Tab 3: Alert Triage** (30% energy)
- Alert queue → graph traversal (47 nodes) → recommendation
- Situation Analyzer with 6 classification types
- Decision Economics: 4 options with time/cost/risk
- **NEW (v2.5): Policy Conflict panel** — detects, resolves, audits conflicting policies
- Closed Loop: EXECUTED → VERIFIED → EVIDENCE → KPI IMPACT
- **NEW (v2.5): Outcome Feedback** — correct/incorrect buttons, asymmetric graph updates, self-correction

**Tab 4: Compounding Dashboard** (15% energy)
- Business Impact Banner: 847 hrs, $127K, 75% MTTR, 2,400 alerts
- Week-over-week comparison
- Two-Loop Hero Diagram
- **NEW (v2.5): ROI Calculator** — modal with 6 input sliders, real-time projections, CFO narrative

---

## PART 2: Files and Links for Next Session

### Documents to Add to Claude Project

| Document | Location | Description |
|---|---|---|
| session_continuation_package_v4.md | Claude Project | THIS document — overall context |
| v2.5_v3_design_document_v3.md | Claude Project | Design spec with ACCP map, v2.5 details, v3.0 plan |
| backlog_v3.md | Claude Project | Current work queue with priorities |
| outreach_emails_v2.md | Claude Project | Updated emails for compounding + math blogs |
| demo_blurb_v25.md | Claude Project | CISO/VC description with screenshot markers |

### Superseded Documents (Remove from Project)

| Old Document | Replaced By |
|---|---|
| session_continuation_package_v3.md | session_continuation_package_v4.md |
| v2.5_v3_design_document_v2.md | v2.5_v3_design_document_v3.md |
| backlog_v2.md | backlog_v3.md |

### External Links to Pre-Read

| # | Link | Title | Priority |
|---|---|---|---|
| 1 | https://www.dakshineshwari.net/post/gen-ai-roi-in-a-box | Gen-AI ROI in a Box | **CRITICAL** |
| 2 | https://www.dakshineshwari.net/post/the-enterprise-class-agent-engineering-stack-from-pilot-to-production-grade-agentic-systems | Agent Engineering Stack | **CRITICAL** |
| 3 | https://www.dakshineshwari.net/post/unified-context-layer-ucl-the-governed-context-substrate-for-enterprise-ai | UCL — context graph foundation | **CRITICAL** |
| 4 | https://www.dakshineshwari.net/post/operationalizing-context-graphs-ciso-cybersecurity-ops-agent-demo | SOC Copilot Demo blog | **CRITICAL** |
| 5 | https://www.dakshineshwari.net/post/production-ai-that-delivers-consistent-kpi-backed-outcomes | Production AI — KPI outcomes | HIGH |
| 6 | https://www.dakshineshwari.net/post/compounding-intelligence-how-enterprise-ai-develops-self-improving-judgment | Compounding Intelligence blog | HIGH |
| 7 | https://www.dakshineshwari.net/post/self-improving-agent-systems-technical-deep-dive | Self-improving agents | HIGH |
| 8 | https://www.dakshineshwari.net/post/cross-graph-attention-mathematical-foundation | Cross-Graph Attention | MEDIUM |
| 9 | https://foundationcapital.com/context-graphs-ais-trillion-dollar-opportunity/ | Context Graphs — VC perspective | MEDIUM |
| 10 | https://a16z.com/unbundling-the-bpo-how-ai-will-disrupt-outsourced-work/ | BPO unbundling — market context | MEDIUM |

### Git Context

```
Repo: git@github.com:ArindamBanerji/gen-ai-roi-demo.git
Branch: main (v2.5 tagged)
Feature branch: feature/v2.5-enhancements (synced with main, can be deleted)
Working directory: gen-ai-roi-demo-v2
Ports: 8001 (backend) / 5174 (frontend)
v1 directory: gen-ai-roi-demo (ports 8000/5173, frozen)
```

### Starting the Demo

```powershell
# Check Neo4j first
python scripts/check_neo4j.py

# Backend
cd backend
uvicorn app.main:app --reload --port 8001

# Frontend (separate terminal)
cd frontend
npx vite --port 5174
```

### Key Files in Repository

```
backend/
  app/main.py                          # FastAPI app, router registration
  app/routers/triage.py                # Alert triage + outcome + policy endpoints
  app/routers/roi.py                   # ROI Calculator endpoint
  app/services/feedback.py             # Outcome Feedback service (v2.5)
  app/services/policy.py               # Policy Conflict service (v2.5)
  app/services/agent.py                # Decision engine
  app/services/reasoning.py            # LLM narration
  app/services/situation.py            # Situation Analyzer
  app/models/schemas.py                # Pydantic models

frontend/
  src/components/tabs/
    AlertTriageTab.tsx                  # Tab 3 (triage + feedback + policy)
    CompoundingTab.tsx                  # Tab 4 (dashboard + ROI button)
    RuntimeEvolutionTab.tsx             # Tab 2
    SOCAnalyticsTab.tsx                 # Tab 1
  src/components/
    OutcomeFeedback.tsx                 # Feedback panel (v2.5)
    PolicyConflict.tsx                  # Policy conflict panel (v2.5)
    ROICalculator.tsx                   # ROI modal (v2.5)
  src/lib/api.ts                       # API client functions
  src/types/roi.ts                     # ROI type definitions

docs/
  ROI_CALCULATOR_API.md                # ROI endpoint reference
  ROI_BUG_FIXES.md                     # Bug analysis
  OUTCOME_FEEDBACK_LOOP.md             # Feedback backend docs
  OUTCOME_FEEDBACK_FRONTEND.md         # Feedback frontend docs
  POLICY_CONFLICT_FRONTEND.md          # Policy frontend docs
  BUGFIX_STALE_CLOSURE.md              # Stale closure fix analysis
```

---

## PART 3: Session Openers

### Session Opener A: Docker for Partners

```
This is a continuing thread for the SOC Copilot demo.

Status: v2.5 complete and tagged on main branch.
ACCP progress: 10/18 capabilities.

Repository: git@github.com:ArindamBanerji/gen-ai-roi-demo.git

Intent for this session: Create Docker packaging so consulting partners 
can run the demo without any dev environment setup. Target: single 
"docker-compose up" command.

Key docs to read: CLAUDE.md, PROJECT_STRUCTURE.md, backlog_v3.md (Section B1)

The partner experience should be:
1. Install Docker Desktop
2. Clone repo
3. docker-compose up
4. Wait 60 seconds
5. Open http://localhost:5174

Need: Dockerfile.backend, Dockerfile.frontend, docker-compose.yml, 
.env.docker, neo4j seed script, PARTNER_README.md
```

### Session Opener B: Loom v2 Script

```
This is a continuing thread for the SOC Copilot demo.

Status: v2.5 complete and tagged. All features working.
ACCP progress: 10/18 capabilities.

Intent for this session: Write the Loom v2 demo script covering all 
v2.5 features (ROI Calculator, Outcome Feedback, Policy Conflict).
The v1 script (demo_script_v5.pdf) is in the project — read it first.

Key additions for v2:
- Tab 3: Show Policy Conflict detection + Outcome Feedback loop
- Tab 4: Show ROI Calculator walkthrough
- Updated soundbites reflecting v2.5

Target: 12-minute script, plus a 3-minute short version for LinkedIn.
```

### Session Opener C: v3.0 Build (Prompt Hub)

```
This is a continuing thread for the SOC Copilot demo.

Status: v2.5 complete. Starting v3.0 features.
ACCP progress: 10/18 capabilities.

Repository: git@github.com:ArindamBanerji/gen-ai-roi-demo.git

Intent for this session: Build the Prompt Hub / Smart Queries feature 
(Prompts 10A-10B). This improves Tab 1 with fuzzy matching and "did 
you mean?" suggestions.

Key docs to read: CLAUDE.md, v2.5_v3_design_document_v3.md (Section 1A)

Create branch: feature/v3.0-enhancements off main (v2.5 tag)
```

---

## PART 4: Key Soundbites (Quick Reference)

1. **Tab 2:** "Splunk gets better rules. Our copilot gets smarter."
2. **Tab 2 (blocking):** "What happens when the AI is wrong? Watch — it catches itself."
3. **Tab 2 (AgentEvolver):** "$4,800/month in recovered analyst time. Zero missed threats."
4. **Tab 3:** "A SIEM stops at detect. We close the loop."
5. **Tab 3 (economics):** "Every option shows time, cost, and risk. The CFO can read this."
6. **Tab 3 (policy):** "You have conflicting policies. We detect, resolve, and audit them."
7. **Tab 3 (feedback):** "Incorrect drops 6 points. Next 5 go to a human. That's self-correction."
8. **Tab 4:** "847 analyst hours. $127K per quarter. That's the board slide."
9. **Tab 4 (ROI):** "Plug in YOUR numbers. See YOUR savings. Take this to YOUR CFO."
10. **ACCP:** "Ten of eighteen capabilities are working today. Running code, not a pitch deck."
11. **Competitive:** "Darktrace learns your baselines. We learn from your decisions. Baselines detect. Decisions compound."

---

## PART 5: Generated Assets Registry

### This Session (v2.5 Build)

| Asset | Type | Location |
|---|---|---|
| ROI Calculator backend | Code | backend/app/routers/roi.py |
| ROI Calculator frontend | Code | frontend/src/components/ROICalculator.tsx |
| Outcome Feedback backend | Code | backend/app/services/feedback.py |
| Outcome Feedback frontend | Code | frontend/src/components/OutcomeFeedback.tsx |
| Policy Conflict backend | Code | backend/app/services/policy.py |
| Policy Conflict frontend | Code | frontend/src/components/PolicyConflict.tsx |
| API docs (ROI, Feedback, Policy) | Docs | docs/*.md (6 files) |
| Outreach emails v2 | Content | outreach_emails_v2.md (Claude Project) |
| Demo blurb v2.5 | Content | demo_blurb_v25.md (Claude Project) |
| Design document v3 | Spec | v2.5_v3_design_document_v3.md (Claude Project) |
| Backlog v3 | Spec | backlog_v3.md (Claude Project) |
| Session continuation v4 | Context | THIS document |

### Previous Sessions

| Asset | Type | Location |
|---|---|---|
| Competitive posture v3 | Analysis | competitive_posture_v3.md (Claude Project) |
| Blog addendum v2 | Content | blog_addendum_v2.md (Claude Project) |
| NBP graphics (6) | Graphics | Wix media library |
| v1 Loom video + script | Video | demo_script_v5.pdf |

---

## PART 6: Known Issues and Polish Items

| Issue | Severity | Where | Notes |
|---|---|---|---|
| Backend services use in-memory state | Medium | feedback.py, policy.py | Fine for 10-min demo, fails 30-min deep dive. Fix in v3.0 (Live Graph Integration). |
| Floating point display (0.8300000001) | Low | Outcome Feedback | Frontend should round to 1 decimal. |
| Pulse animation on ROI button | Low | Tab 4 | May feel gimmicky for CISO audience. Tone down if needed. |
| Policy Conflict doesn't override Recommendation | Design gap | Tab 3 | Policy says escalate, Recommendation says auto-close. Presenter narrates the override. Fix in v3.0. |
| Tab 1 regression check needed | Low | Tab 1 | Quick pass to verify NL queries still work after v2.5 changes. |

---

*SOC Copilot Demo — Session Continuation Package v4.0 | February 18, 2026*
*Status: v2.5 Complete. Next: Docker OR Loom.*
