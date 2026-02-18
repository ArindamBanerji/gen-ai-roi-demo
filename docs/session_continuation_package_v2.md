# SOC Copilot Demo — Session Continuation Package (Post v2.0)

**Date:** February 17, 2026
**Status:** v2.0 Complete, merged to main, tagged
**Next Session Focus:** ROI Calculator (v2.5), Loom demo script, Docker

---

## PART 1: V2 Demo Description (for next conversation session)

### What Is This Demo?

The SOC Copilot Demo is a working prototype of an AI-augmented Security Operations Center (SOC) that demonstrates **compounding intelligence** — the system gets smarter over time through two learning loops feeding one context graph. Built with FastAPI (Python) + React/TypeScript + Neo4j Aura, it runs locally on ports 8001 (backend) / 5174 (frontend).

### Core Thesis

"Your SIEM gets better detection rules written by humans. Our SOC copilot gets **smarter** automatically through validated decisions."

### The Two Learning Loops

| Loop | Name | What It Does | Where Visible |
|---|---|---|---|
| **Loop 1** | Situation Analyzer | Gets smarter WITHIN each decision — classifies alerts, evaluates options with time/cost/risk, shows reasoning | Tab 3 |
| **Loop 2** | AgentEvolver | Gets smarter ACROSS decisions — tracks prompt variant performance, auto-promotes winners, computes operational impact | Tab 2 |

### The Four Tabs

**Tab 1: SOC Analytics** (20% energy)
- Natural language queries → governed security metrics
- Provenance showing data sources
- Rule sprawl detection ($18K/month waste found)

**Tab 2: Runtime Evolution** (35% energy) ★ THE DIFFERENTIATOR
- Deployment registry (v3.1 prod, v3.2 canary)
- Process alert → 4 eval gate checks (sequential animation, 800ms each)
- TRIGGERED_EVOLUTION panel (pattern confidence 91% → 94%)
- **[v2 NEW]** "Simulate Failed Gate" → BLOCKED banner with red X, safety proof
- **[v2 NEW]** AgentEvolver panel: variant comparison bars (v1 71% → v2 89%), "What Changed" narrative, 5 operational impact cards ($4,800/mo saved, 0 missed threats)
- CMA labels: CONSUME ✓ on eval gate, MUTATE ✓ on evolution panels

**Tab 3: Alert Triage** (30% energy)
- Alert queue (6 alerts including ALERT-7823 travel + ALERT-7824 phishing)
- Graph traversal showing 47 nodes consulted
- **[v2 NEW]** Situation Analyzer panel: type badge (color-coded), factors checklist, options bar chart
- **[v2 NEW]** Decision Economics: each option shows resolution time, analyst cost, risk level
- **[v2 NEW]** Economics summary: "$127 cost avoided per alert, 149 analyst-hours and $25,400/month saved"
- Recommendation → Apply → 4-step closed loop (EXECUTED → VERIFIED → EVIDENCE → KPI)
- CMA labels: CONSUME on graph, ACTIVATE on closed loop

**Tab 4: Compounding Dashboard** (15% energy)
- **[v2 NEW]** Business Impact Banner: 4 animated cards (847 analyst hours, $127K/quarter, 75% MTTR reduction, 2,400 alerts eliminated)
- Week 1 vs Week 4 comparison (23→127 patterns, 68%→89% auto-close, animated counters)
- **[v2 NEW]** Two-Loop Hero Diagram: Context Graph center, Loop 1 (blue/CONSUME), Loop 2 (purple/MUTATE), TRIGGERED_EVOLUTION connection
- Evolution events timeline

### Two Alert Types

| Alert | Type | User | Situation | Action | Decision Economics |
|---|---|---|---|---|---|
| ALERT-7823 | Anomalous Login | John Smith, VP Finance | TRAVEL_LOGIN_ANOMALY (94%) | FALSE_POSITIVE_CLOSE | $127 saved, 44 min saved |
| ALERT-7824 | Phishing | Mary Chen, Engineering Lead | KNOWN_PHISHING_CAMPAIGN (96%) | AUTO_REMEDIATE | $95 saved, 29 min saved |

### Key Soundbites

1. **Tab 2:** "Splunk gets better rules. Our copilot gets **smarter**."
2. **Tab 2 (blocking):** "What happens when the AI is wrong? Watch — it catches itself."
3. **Tab 2 (AgentEvolver):** "$4,800/month in recovered analyst time. Zero missed threats."
4. **Tab 3:** "A SIEM stops at detect. We **close the loop**."
5. **Tab 3 (economics):** "Every option shows time, cost, and risk. The CFO can read this."
6. **Tab 4:** "847 analyst hours. $127K per quarter. That's the board slide."
7. **Tab 4:** "When they deploy, they start at zero. We start at 127 patterns."

### Technical Stack

- Backend: FastAPI 0.104+, Python 3.11+, Pydantic v2
- Frontend: React 18.2, TypeScript 5.2, Vite, Tailwind CSS 3.3, Recharts, Lucide icons
- Database: Neo4j Aura 5.14+ (graph), BigQuery (mocked), Firestore (mocked)
- AI/LLM: Vertex AI / Gemini 1.5 Pro (narration only — decisions are rule-based)

---

## PART 2: Documents & Links for Next Session

### Files to Add to Claude Project

| # | File | Location in Repo | Why Critical |
|---|---|---|---|
| 1 | `CLAUDE.md` | Root | Claude Code context — has full v2 architecture |
| 2 | `PROJECT_STRUCTURE.md` | Root | File-by-file code documentation |
| 3 | `README.md` | Root | Updated demo script + feature list |
| 4 | `V2_IMPLEMENTATION_PLAN.md` | `docs/` | Progress tracker, wave breakdown |
| 5 | `v2.5_v3_design_document.md` | `docs/` | Design spec for next features |
| 6 | `demo_script_v5.pdf` | `support/docs/` | v1 Loom script (needs v2 update) |
| 7 | `vc_demo_build_spec_ciso_v1.md` | `docs/` | Original CISO build spec |
| 8 | `demo_technical_briefing_ciso_v1.md` | `docs/` | Technical briefing for CISOs |
| 9 | `Docker_README.pdf` | `support/docs/` | Docker deployment specs |
| 10 | `PARTNER_ONBOARDING_GUIDE.pdf` | `support/docs/` | Partner onboarding flow |

### Blog Links to Reference

| # | Link | Title | Priority |
|---|---|---|---|
| 1 | https://www.dakshineshwari.net/post/operationalizing-context-graphs-ciso-cybersecurity-ops-agent-demo | SOC Copilot Demo — main page | **CRITICAL** |
| 2 | https://www.dakshineshwari.net/post/gen-ai-roi-in-a-box | Gen-AI ROI in a Box — main framework | **CRITICAL** |
| 3 | https://www.dakshineshwari.net/post/the-enterprise-class-agent-engineering-stack-from-pilot-to-production-grade-agentic-systems | Agent Engineering Stack | **CRITICAL** |
| 4 | https://www.dakshineshwari.net/post/unified-context-layer-ucl-the-governed-context-substrate-for-enterprise-ai | UCL — context graph foundation | **CRITICAL** |
| 5 | https://www.dakshineshwari.net/post/production-ai-that-delivers-consistent-kpi-backed-outcomes | Production AI — KPI-backed outcomes | **HIGH** |
| 6 | https://www.dakshineshwari.net/post/self-improving-agent-systems-technical-deep-dive | Self-improving agents — technical deep dive | **HIGH** |
| 7 | https://www.dakshineshwari.net/post/compounding-intelligence-how-enterprise-ai-develops-self-improving-judgment | Compounding Intelligence — self-improving judgment | **HIGH** |
| 8 | https://www.dakshineshwari.net/post/cross-graph-attention-mathematical-foundation | Cross-Graph Attention — mathematical foundation | **HIGH** |
| 9 | https://foundationcapital.com/context-graphs-ais-trillion-dollar-opportunity/ | Context Graphs — VC perspective | **MEDIUM** |
| 10 | https://a16z.com/unbundling-the-bpo-how-ai-will-disrupt-outsourced-work/ | BPO unbundling — market context | **MEDIUM** |

### Git Context

```
Repo: git@github.com:ArindamBanerji/gen-ai-roi-demo.git
Branch: main (v2.0 tagged)
Feature branch: feature/v2-enhancements (synced with main)
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

---

## PART 3: Outreach Emails

### Email 1: Compounding Intelligence

**Subject:** Context graphs that get smarter — not just bigger

Hi [Name],

I've been building something that demonstrates a concept I think is underappreciated in the AI agent space: **compounding intelligence**.

Most AI deployments are static — they execute fixed logic, and when you want them to get better, a human rewrites the rules. We built a working SOC (Security Operations Center) copilot demo that shows a different model: two learning loops feeding one context graph, where every decision makes the next decision smarter.

Here's what makes it interesting:

**Loop 1 — Situation Analyzer.** When an alert comes in, the system doesn't just pattern-match. It classifies the situation, evaluates multiple response options with time/cost/risk for each, and shows its reasoning. A phishing alert and a travel login anomaly take completely different paths — same architecture, different intelligence.

**Loop 2 — AgentEvolver.** The system tracks which prompt variants produce better outcomes and auto-promotes winners. In the demo, one variant improved from 71% to 89% success rate — translating to 36 fewer false escalations per month and $4,800 in recovered analyst time. The agent didn't just execute better rules. It learned HOW to reason better.

**The compounding effect.** Week 1: 23 patterns, 68% auto-close rate. Week 4: 127 patterns, 89% auto-close rate. Same model. Same code. More intelligence. A competitor deploying today starts at zero. We start at 127 and growing.

The working demo is here: [link to demo page]

The architectural thinking behind it:
- [Compounding Intelligence — How Enterprise AI Develops Self-Improving Judgment](https://www.dakshineshwari.net/post/compounding-intelligence-how-enterprise-ai-develops-self-improving-judgment)
- [Context Graphs for CISO Ops](https://www.dakshineshwari.net/post/operationalizing-context-graphs-ciso-cybersecurity-ops-agent-demo)
- [Gen-AI ROI in a Box](https://www.dakshineshwari.net/post/gen-ai-roi-in-a-box)
- [UCL — The Governed Context Substrate](https://www.dakshineshwari.net/post/unified-context-layer-ucl-the-governed-context-substrate-for-enterprise-ai)

Happy to walk you through the demo live if you're interested. The whole thing runs in 10 minutes and the "aha moment" hits around minute 3.

Best,
Arindam

---

### Email 2: The Math Behind Agent ROI

**Subject:** The math on why self-improving agents compound — with a working demo

Hi [Name],

There's a math problem hiding in most enterprise AI deployments that nobody talks about: **linear investment, linear returns**. You deploy an AI agent. It automates X%. You want X+10%? Deploy more rules, hire more prompt engineers, retune. The cost scales linearly with improvement.

We built a demo that shows a different economics model. Here's the math:

**Decision Economics (per alert):**
- Manual triage: 45 minutes analyst time, $127 cost
- AI auto-close (with eval gates): 3 seconds, $0 cost
- Savings per alert: 44 minutes and $127
- At 200 similar alerts/month: **149 analyst-hours and $25,400 saved**

**The compounding part:**
The system doesn't just execute at a fixed rate. It tracks which reasoning approaches work better and auto-promotes them. In the demo:
- Prompt variant v1: 71% success rate
- Prompt variant v2: 89% success rate (the system discovered this itself)
- Impact of that evolution: 18% fewer false escalations → 36 fewer Tier 2 reviews/month → 27 analyst hours recovered → **$4,800/month in additional savings** — from a single prompt improvement the system made on its own

**Week-over-week compounding:**

| Week | Patterns | Auto-Close Rate | MTTR |
|------|----------|-----------------|------|
| 1 | 23 | 68% | 12.4 min |
| 2 | 58 | 74% | 8.1 min |
| 3 | 89 | 82% | 5.2 min |
| 4 | 127 | 89% | 3.1 min |

The improvement curve is sublinear in cost but superlinear in value. Each learned pattern makes the next pattern cheaper to learn. That's the moat.

The full demo with decision economics is here: [link to demo page]

The framework behind the math:
- [Cross-Graph Attention — Mathematical Foundation](https://www.dakshineshwari.net/post/cross-graph-attention-mathematical-foundation)
- [Gen-AI ROI in a Box](https://www.dakshineshwari.net/post/gen-ai-roi-in-a-box)
- [Production AI with KPI-Backed Outcomes](https://www.dakshineshwari.net/post/production-ai-that-delivers-consistent-kpi-backed-outcomes)
- [Self-Improving Agent Systems — Technical Deep Dive](https://www.dakshineshwari.net/post/self-improving-agent-systems-technical-deep-dive)

If you're thinking about AI agent ROI for your org, this demo makes the economics very concrete. Happy to walk through it.

Best,
Arindam

---

## PART 4: Session Continuation & Backlog Review

### Memory Updates (already applied)

| # | Memory Entry | Status |
|---|---|---|
| 1 | User's full name is Arindam Banerji | ✅ Existing |
| 2 | SOC Copilot Demo v2 COMPLETE (Feb 17 2026). All 6 waves done. | ✅ Added |
| 3 | v2 next steps priority: PR merge → ROI Calc → design doc → Docker → Loom | ✅ Added |
| 4 | v2 dev env: ports, directories, Neo4j shared | ✅ Added |
| 5 | Claude Code tips: no debugger, no git, one testable thing | ✅ Added |
| 6 | Key docs: V2_IMPLEMENTATION_PLAN, PROJECT_STRUCTURE, CLAUDE.md | ✅ Added |

### Backlog — Current State

| # | Item | Status | Priority | Notes |
|---|---|---|---|---|
| 1 | PR merge to main + tag v2.0 | ✅ DONE | — | Merged, tagged |
| 2 | ROI Calculator (v2.5) | ⬜ Not started | **P0** | 3 prompts (7A, 7B, 7C) |
| 3 | v2.5/v3 design document | ✅ DONE | — | `docs/v2.5_v3_design_document.md` |
| 4 | Outcome Feedback Loop (v2.5) | ⬜ Not started | **P1** | 2 prompts (8A, 8B) |
| 5 | Policy Conflict Resolution (v2.5) | ⬜ Not started | **P1** | 2 prompts (9A, 9B) |
| 6 | Prompt Hub enhancement (v2.5) | ⬜ Not started | **P2** | 2 prompts (10A, 10B) |
| 7 | Docker for partners | ⬜ Not started | **P2** | Specs exist in Docker_README.pdf |
| 8 | Loom demo script (v2) | ⬜ Not started | **P2** | Update demo_script_v5 for v2 features |
| 9 | Shorter Loom version | ⬜ Not started | **P3** | 3-minute cut of the 10-minute demo |
| 10 | Outreach emails | ✅ DRAFTED | — | See Part 3 above |
| 11 | Neo4j health check script | ✅ DONE | — | `scripts/check_neo4j.py` |
| 12 | Blog post updates | ⬜ Not started | **P3** | Update demo blog with v2 screenshots |

### What Changed Since Last Continuation Package

The `CISO_DEMO_COMPLETE_CONTINUATION_PACKAGE.pdf` in the project is outdated — it was written pre-build. The documents that now serve as the continuation package are:

| Old Document | Replaced By |
|---|---|
| `CISO_DEMO_CONTINUATION_SUMMARY.md` | This document + `CLAUDE.md` (v2 section) |
| `CISO_DEMO_BACKLOG_UPDATED.md` | Backlog table above + `V2_IMPLEMENTATION_PLAN.md` |
| `CISO_DEMO_NEXT_THREAD_SETUP.md` | Part 2 of this document |
| `bootstrap_sequence_v5.md` | No longer needed — demo is built |

### Next Session Suggested Opener

```
This is a continuing thread for the SOC Copilot demo.

Status: v2.0 is complete, merged to main, tagged. See CLAUDE.md and 
PROJECT_STRUCTURE.md for full architecture.

Repository: git@github.com:ArindamBanerji/gen-ai-roi-demo.git

Intent for this session: [pick from backlog]
- Build ROI Calculator (v2.5, Prompts 7A-7C from design doc)
- Update Loom demo script for v2
- Docker containerization
- [other]

Key docs to read: CLAUDE.md, docs/v2.5_v3_design_document.md, 
docs/V2_IMPLEMENTATION_PLAN.md

Blog links: [include relevant ones from Part 2]
```
