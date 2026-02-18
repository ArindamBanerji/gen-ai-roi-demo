# SOC Copilot Demo — Session Continuation Package v3

**Date:** February 18, 2026
**Status:** v2.0 Complete and tagged. ACCP roadmap formalized. Graphics, competitive posture, and blog addendum generated.
**Next Build Session Focus:** ROI Calculator (v2.5, Prompts 7A-7C)
**ACCP Progress:** 7/18 capabilities implemented (39%)

---

## PART 1: What Is This Project?

### The Demo

The SOC Copilot Demo is a working prototype of an AI-augmented Security Operations Center (SOC) that demonstrates **compounding intelligence** -- the system gets smarter over time through two learning loops feeding one context graph. Built with FastAPI (Python) + React/TypeScript + Neo4j Aura, it runs locally on ports 8001 (backend) / 5174 (frontend).

### The Architecture: ACCP

The demo is the progressive reference implementation of the **Agentic Cognitive Control Plane (ACCP)** -- an architectural pattern for governed, self-improving enterprise AI. ACCP defines five structural capabilities:

1. **Typed-Intent Bus** -- normalizes signals into classified intents
2. **Situational Mesh** -- scores situations using context, KPIs, and drift signals
3. **Eval Gates** -- enforces structural safety checks before any action
4. **TRIGGERED_EVOLUTION** -- writes verified outcomes back to the context graph
5. **Decision Economics** -- tags every action with time, cost, and risk impact

The SOC demo IS the ACCP reference implementation. Each version implements more capabilities:
- v2.0 (current): 7/18 capabilities (context graph, eval gates, situation classification, TRIGGERED_EVOLUTION, decision economics, both learning loops)
- v2.5 (next): 10/18 (adds ROI Calculator, Outcome Feedback, Policy Conflict)
- v3.0 (planned): 14/18 (adds automated outcomes, external context, compliance, process intelligence)
- v3.5/v4.0 (vision): 18/18 (formal Typed-Intent Bus, Control Tower, multi-domain)

### Core Thesis

"Your SIEM gets better detection rules written by humans. Our SOC copilot gets smarter automatically through validated decisions."

### The Two Learning Loops

| Loop | Name | What It Does | Where Visible |
|---|---|---|---|
| Loop 1 | Situation Analyzer | Gets smarter WITHIN each decision -- classifies alerts, evaluates options with time/cost/risk | Tab 3 |
| Loop 2 | AgentEvolver | Gets smarter ACROSS decisions -- tracks prompt variant performance, auto-promotes winners | Tab 2 |

### The Four Tabs

**Tab 1: SOC Analytics** (20% energy)
- Natural language queries -> governed security metrics
- Provenance showing data sources
- Rule sprawl detection ($18K/month waste found)

**Tab 2: Runtime Evolution** (35% energy) -- THE DIFFERENTIATOR
- Deployment registry (v3.1 prod, v3.2 canary)
- Process alert -> 4 eval gate checks (sequential animation, 800ms each)
- TRIGGERED_EVOLUTION panel (pattern confidence 91% -> 94%)
- "Simulate Failed Gate" -> BLOCKED banner with red X, safety proof
- AgentEvolver panel: variant comparison bars (v1 71% -> v2 89%), "What Changed" narrative, 5 operational impact cards ($4,800/mo saved, 0 missed threats)

**Tab 3: Alert Triage** (30% energy)
- Alert queue (6 alerts including ALERT-7823 travel + ALERT-7824 phishing)
- Graph traversal showing 47 nodes consulted
- Situation Analyzer panel: type badge, factors checklist, options bar chart
- Decision Economics: each option shows resolution time, analyst cost, risk level
- Economics summary: "$127 cost avoided per alert, 149 analyst-hours and $25,400/month saved"
- Recommendation -> Apply -> 4-step closed loop

**Tab 4: Compounding Dashboard** (15% energy)
- Business Impact Banner: 4 animated cards (847 analyst hours, $127K/quarter, 75% MTTR reduction, 2,400 alerts eliminated)
- Week 1 vs Week 4 comparison (23->127 patterns, 68%->89% auto-close)
- Two-Loop Hero Diagram
- Evolution events timeline

### Two Alert Types

| Alert | Type | User | Situation | Action | Economics |
|---|---|---|---|---|---|
| ALERT-7823 | Anomalous Login | John Smith, VP Finance | TRAVEL_LOGIN_ANOMALY (94%) | FALSE_POSITIVE_CLOSE | $127 saved, 44 min saved |
| ALERT-7824 | Phishing | Mary Chen, Engineering Lead | KNOWN_PHISHING_CAMPAIGN (96%) | AUTO_REMEDIATE | $95 saved, 29 min saved |

### Technical Stack

- Backend: FastAPI 0.104+, Python 3.11+, Pydantic v2
- Frontend: React 18.2, TypeScript 5.2, Vite, Tailwind CSS 3.3, Recharts, Lucide icons
- Database: Neo4j Aura 5.14+ (graph), BigQuery (mocked), Firestore (mocked)
- AI/LLM: Vertex AI / Gemini 1.5 Pro (narration only -- decisions are rule-based)

---

## PART 2: Document Inventory

### Documents to Add to Claude Project

| # | File | What It Is | Priority |
|---|---|---|---|
| 1 | CLAUDE.md | Claude Code context -- full v2 architecture | **CRITICAL** |
| 2 | PROJECT_STRUCTURE.md | File-by-file code documentation | **CRITICAL** |
| 3 | README.md | Updated demo script + feature list | HIGH |
| 4 | v2.5_v3_design_document_v2.md | Design spec with ACCP mapping (v2.5/v3.0/v4.0) | **CRITICAL** |
| 5 | backlog_v2.md | Active work items, priority queue, Docker plan | **CRITICAL** |
| 6 | competitive_posture_v3.md | Market analysis, ACCP roadmap, counter-positioning | HIGH |
| 7 | blog_addendum_compounding_intelligence_v2.md | Blog section draft + graphic placement markers | MEDIUM |
| 8 | demo_script_v5.pdf | v1 Loom script (needs v2 update) | MEDIUM |
| 9 | Docker_README.pdf | Docker deployment specs (original) | MEDIUM |
| 10 | PARTNER_ONBOARDING_GUIDE.pdf | Partner onboarding flow | MEDIUM |

### Document Relationships

```
CLAUDE.md (code context)
    |
    +-- PROJECT_STRUCTURE.md (file-level detail)
    |
    +-- v2.5_v3_design_document_v2.md (what to build next)
    |       |
    |       +-- ACCP capability map (Section 0) -- tracks progress
    |       +-- v2.5 features (Section 1) -- prompt-level specs
    |       +-- v3.0/v4.0 vision (Sections 2-3)
    |
    +-- backlog_v2.md (work queue + priorities)
    |       |
    |       +-- v2.5 build items (Section B)
    |       +-- Docker for partners (Section C)
    |       +-- Loom/outreach (Section D)
    |
    +-- competitive_posture_v3.md (market context)
            |
            +-- ACCP as demo roadmap (Section 3)
            +-- Graphics registry (Appendix C)
```

### Blog Links to Reference

| # | Link | Title | Priority |
|---|---|---|---|
| 1 | https://www.dakshineshwari.net/post/operationalizing-context-graphs-ciso-cybersecurity-ops-agent-demo | SOC Copilot Demo -- main page | **CRITICAL** |
| 2 | https://www.dakshineshwari.net/post/gen-ai-roi-in-a-box | Gen-AI ROI in a Box -- main framework | **CRITICAL** |
| 3 | https://www.dakshineshwari.net/post/the-enterprise-class-agent-engineering-stack-from-pilot-to-production-grade-agentic-systems | Agent Engineering Stack | **CRITICAL** |
| 4 | https://www.dakshineshwari.net/post/unified-context-layer-ucl-the-governed-context-substrate-for-enterprise-ai | UCL -- context graph foundation | **CRITICAL** |
| 5 | https://www.dakshineshwari.net/post/production-ai-that-delivers-consistent-kpi-backed-outcomes | Production AI -- KPI-backed outcomes | HIGH |
| 6 | https://www.dakshineshwari.net/post/self-improving-agent-systems-technical-deep-dive | Self-improving agents -- technical deep dive | HIGH |
| 7 | https://www.dakshineshwari.net/post/compounding-intelligence-how-enterprise-ai-develops-self-improving-judgment | Compounding Intelligence -- self-improving judgment | HIGH |
| 8 | https://www.dakshineshwari.net/post/cross-graph-attention-mathematical-foundation | Cross-Graph Attention -- mathematical foundation | HIGH |
| 9 | https://foundationcapital.com/context-graphs-ais-trillion-dollar-opportunity/ | Context Graphs -- VC perspective | MEDIUM |
| 10 | https://a16z.com/unbundling-the-bpo-how-ai-will-disrupt-outsourced-work/ | BPO unbundling -- market context | MEDIUM |

### Git Context

```
Repo: git@github.com:ArindamBanerji/gen-ai-roi-demo.git
Branch: main (v2.0 tagged)
Feature branch: feature/v2-enhancements (synced with main, can be deleted)
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

## PART 3: Current Backlog Summary

### Priority Queue

| Priority | Item | Effort | ACCP Impact | Status |
|---|---|---|---|---|
| **P0** | ROI Calculator | 3 prompts (1 session) | Decision Economics extended | Not started |
| **P1** | Outcome Feedback Loop | 2 prompts (half session) | TRIGGERED_EVOLUTION completed | Not started |
| **P1** | Policy Conflict Resolution | 2 prompts (half session) | Eval Gates extended | Not started |
| **P2** | Docker for Partners | 4 prompts (1 session) | Distribution | Not started |
| **P2** | Prompt Hub | 2 prompts (half session) | Typed-Intent Bus (early) | Not started |
| **P2** | Loom v2 Script | 1 session (writing) | Outreach | Not started |
| **P3** | Short Loom (3 min) | After Loom v2 | Outreach | Not started |
| **P3** | Blog updates | 1-2 hours | Content | Not started |
| DONE | PR merge + tag v2.0 | -- | -- | Complete |
| DONE | Design document v2 | -- | -- | Complete |
| DONE | Competitive posture v3 | -- | -- | Complete |
| DONE | Blog addendum v2 | -- | -- | Complete |
| DONE | NBP graphics (6) | -- | -- | Complete |
| DONE | Outreach emails (2 drafts) | -- | -- | Complete |

### Recommended Session Order

```
Session 1: ROI Calculator (Prompts 7A, 7B, 7C)
Session 2: Outcome Feedback + Policy Conflict (Prompts 8A, 8B, 9A, 9B) -> Tag v2.5
Session 3: Docker for Partners (Prompts D1, D2, D3, D4)
Session 4: Loom v2 Script + Recording
Session 5 (optional): Prompt Hub + Polish
```

---

## PART 4: Key Soundbites (Quick Reference)

1. **Tab 2:** "Splunk gets better rules. Our copilot gets smarter."
2. **Tab 2 (blocking):** "What happens when the AI is wrong? Watch -- it catches itself."
3. **Tab 2 (AgentEvolver):** "$4,800/month in recovered analyst time. Zero missed threats."
4. **Tab 3:** "A SIEM stops at detect. We close the loop."
5. **Tab 3 (economics):** "Every option shows time, cost, and risk. The CFO can read this."
6. **Tab 4:** "847 analyst hours. $127K per quarter. That's the board slide."
7. **Tab 4:** "When they deploy, they start at zero. We start at 127 and growing."
8. **ACCP:** "Seven of eighteen ACCP capabilities are working today. This isn't a pitch deck -- it's a roadmap with running code."
9. **Competitive:** "Darktrace learns your baselines. We learn from your decisions. Baselines detect. Decisions compound."

---

## PART 5: Outreach Emails

### Email 1: Compounding Intelligence

**Subject:** Context graphs that get smarter -- not just bigger

Hi [Name],

I've been building something that demonstrates a concept I think is underappreciated in the AI agent space: **compounding intelligence**.

Most AI deployments are static -- they execute fixed logic, and when you want them to get better, a human rewrites the rules. We built a working SOC (Security Operations Center) copilot demo that shows a different model: two learning loops feeding one context graph, where every decision makes the next decision smarter.

Here's what makes it interesting:

**Loop 1 -- Situation Analyzer.** When an alert comes in, the system doesn't just pattern-match. It classifies the situation, evaluates multiple response options with time/cost/risk for each, and shows its reasoning. A phishing alert and a travel login anomaly take completely different paths -- same architecture, different intelligence.

**Loop 2 -- AgentEvolver.** The system tracks which prompt variants produce better outcomes and auto-promotes winners. In the demo, one variant improved from 71% to 89% success rate -- translating to 36 fewer false escalations per month and $4,800 in recovered analyst time. The agent didn't just execute better rules. It learned HOW to reason better.

**The compounding effect.** Week 1: 23 patterns, 68% auto-close rate. Week 4: 127 patterns, 89% auto-close rate. Same model. Same code. More intelligence. A competitor deploying today starts at zero. We start at 127 and growing.

The architecture behind this -- the Agentic Cognitive Control Plane (ACCP) -- is domain-agnostic. SOC is the first domain. The same pattern extends to supply chain, ITSM, AML -- any domain where intelligent copilots make repeated decisions over structured context.

The working demo is here: [link to demo page]

The architectural thinking behind it:
- Compounding Intelligence -- https://www.dakshineshwari.net/post/compounding-intelligence-how-enterprise-ai-develops-self-improving-judgment
- Context Graphs for CISO Ops -- https://www.dakshineshwari.net/post/operationalizing-context-graphs-ciso-cybersecurity-ops-agent-demo
- Gen-AI ROI in a Box -- https://www.dakshineshwari.net/post/gen-ai-roi-in-a-box
- UCL -- The Governed Context Substrate -- https://www.dakshineshwari.net/post/unified-context-layer-ucl-the-governed-context-substrate-for-enterprise-ai

Happy to walk you through the demo live if you're interested. The whole thing runs in 10 minutes and the "aha moment" hits around minute 3.

Best,
Arindam

---

### Email 2: The Math Behind Agent ROI

**Subject:** The math on why self-improving agents compound -- with a working demo

Hi [Name],

There's a math problem hiding in most enterprise AI deployments that nobody talks about: **linear investment, linear returns**. You deploy an AI agent. It automates X%. You want X+10%? Deploy more rules, hire more prompt engineers, retune. The cost scales linearly with improvement.

We built a demo that shows a different economics model. Here's the math:

**Decision Economics (per alert):**
- Manual triage: 45 minutes analyst time, $127 cost
- AI auto-close (with eval gates): 3 seconds, $0 cost
- Savings per alert: 44 minutes and $127
- At 200 similar alerts/month: 149 analyst-hours and $25,400 saved

**The compounding part:**
The system tracks which reasoning approaches work better and auto-promotes them:
- Prompt variant v1: 71% success rate
- Prompt variant v2: 89% success rate (the system discovered this itself)
- Impact: 18% fewer false escalations -> 36 fewer Tier 2 reviews/month -> 27 analyst hours recovered -> $4,800/month in additional savings -- from a single prompt improvement the system made on its own

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
- Cross-Graph Attention -- Mathematical Foundation -- https://www.dakshineshwari.net/post/cross-graph-attention-mathematical-foundation
- Gen-AI ROI in a Box -- https://www.dakshineshwari.net/post/gen-ai-roi-in-a-box
- Production AI with KPI-Backed Outcomes -- https://www.dakshineshwari.net/post/production-ai-that-delivers-consistent-kpi-backed-outcomes
- Self-Improving Agent Systems -- https://www.dakshineshwari.net/post/self-improving-agent-systems-technical-deep-dive

If you're thinking about AI agent ROI for your org, this demo makes the economics very concrete. Happy to walk through it.

Best,
Arindam

---

## PART 6: Generated Assets (This Session)

### NBP Graphics (6 total, all prompt + JSON complete)

| # | Tag | Title | Theme | Standalone? |
|---|---|---|---|---|
| 1 | CI-MARKET | Three Generations of SOC AI | Dark | No |
| 2 | CI-COMPOUND-TRIANGLE | What Makes Intelligence Compound? | Light | **YES** |
| 3 | CI-GAP | The Compounding Gap: Why It Widens | Dark | Yes |
| 4 | CI-MATRIX | What Compounds vs. What Doesn't (4-col, public) | Dark | No |
| 5 | CI-COMPETE-MATRIX-DARK | SOC AI Capability Landscape (7-col, internal) | Dark | **YES** |
| 6 | CI-COMPETE-MATRIX-LIGHT | SOC AI Capability Landscape (7-col, internal) | Light | **YES** |

### Documents Generated/Updated (This Session)

| Document | Status | Description |
|---|---|---|
| competitive_posture_v3.md | New | Full rewrite with ACCP as demo roadmap |
| blog_addendum_compounding_intelligence_v2.md | Updated | Graphic placement markers added |
| v2.5_v3_design_document_v2.md | Updated | ACCP capability map, extended to v4.0 |
| backlog_v2.md | New | Restructured with ACCP tags, Docker, outreach |
| session_continuation_package_v3.md | New | This document |

### Documents Superseded

| Old Document | Replaced By |
|---|---|
| competitive_posture_v1.md, v2.md | competitive_posture_v3.md |
| blog_addendum_compounding_intelligence.md | blog_addendum_compounding_intelligence_v2.md |
| v2.5_v3_design_document.md (v1) | v2.5_v3_design_document_v2.md |
| backlog.md (v1) | backlog_v2.md |
| session_continuation_package_v2.md | This document |
| CISO_DEMO_COMPLETE_CONTINUATION_PACKAGE.pdf | Obsolete (pre-build) |
| bootstrap_sequence_v5.md | Obsolete (demo is built) |

---

## PART 7: Next Session Suggested Opener

### For v2.5 Build Session (ROI Calculator)

```
This is a continuing thread for the SOC Copilot demo.

Status: v2.0 is complete, merged to main, tagged. The demo implements 7 of 18 ACCP 
capabilities. See CLAUDE.md and PROJECT_STRUCTURE.md for full architecture.

Repository: git@github.com:ArindamBanerji/gen-ai-roi-demo.git

Intent for this session: Build the ROI Calculator (v2.5, Prompts 7A-7C).
- See v2.5_v3_design_document_v2.md, Section 1A for full spec
- Backend: /api/roi/calculate endpoint
- Frontend: ROI Calculator modal triggered from Tab 4
- PDF export capability

Key docs to read: CLAUDE.md, v2.5_v3_design_document_v2.md (Section 1A), 
backlog_v2.md (Section B1)

Do not start debugger/servers. Do not run git commands. One testable thing at a time.
```

### For Docker Session

```
This is a continuing thread for the SOC Copilot demo.

Status: v2.0 (or v2.5 if built) is complete. Need Docker containerization for 
partner distribution.

Repository: git@github.com:ArindamBanerji/gen-ai-roi-demo.git

Intent for this session: Create Docker packaging so consulting partners can run 
the demo with a single docker-compose up.
- See backlog_v2.md, Section C for full spec
- Dockerfile.backend (FastAPI)
- Dockerfile.frontend (Vite build -> nginx)  
- docker-compose.yml with Neo4j pre-seeding
- PARTNER_README.md (5-step setup)

Key docs to read: CLAUDE.md, PROJECT_STRUCTURE.md, Docker_README.pdf

Do not start debugger/servers. Do not run git commands. One testable thing at a time.
```

---

## PART 8: Version History

| Version | Date | Focus |
|---|---|---|
| v1 | Feb 17, 2026 | Initial continuation package (post v2.0 build) |
| v2 | Feb 17, 2026 | Added outreach emails, backlog table, document links |
| v3 | Feb 18, 2026 | ACCP integration, updated document inventory, generated assets registry, superseded documents list, session openers for v2.5 and Docker |

---

*Session Continuation Package v3.0 | February 18, 2026*
