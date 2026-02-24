# SOC Copilot Demo — Session Continuation Package v7

**Date:** February 24, 2026
**Status:** v2.5.1 tagged (B1 fix). Design doc v7.0 finalized. v3.0 build ready to start.
**Next Session Focus:** v3.0 build — Session 1 (Loop 3: Prompts A1, A2, A3)
**Repositories:**
- Demo: git@github.com:ArindamBanerji/gen-ai-roi-demo.git (main, v2.5.1)
- Experiments: git@github.com:ArindamBanerji/cross-graph-experiments.git (main, v1.0 tag)
**Branch:** main (v2.5 at e63bc85, v2.5.1 at B1 fix commit)

---

## PART 1: What Is This Project?

### The Demo

The SOC Copilot Demo is a working prototype of an AI-augmented Security Operations Center (SOC) that demonstrates **compounding intelligence** — the system gets smarter over time through three learning loops feeding one living context graph. Built with FastAPI (Python) + React/TypeScript + Neo4j Aura, running on ports 8001 (backend) / 5174 (frontend).

### The Architecture: ACCP

The demo is the progressive reference implementation of the **Agentic Cognitive Control Plane (ACCP)** — an architectural pattern for governed, self-improving enterprise AI. ACCP defines five structural capabilities:

1. **Typed-Intent Bus** — normalizes signals into classified intents
2. **Situational Mesh** — scores situations using context, KPIs, and drift signals
3. **Eval Gates** — enforces structural safety checks before any action executes
4. **TRIGGERED_EVOLUTION** — writes verified outcomes back to the context graph
5. **Decision Economics** — tags every action with time, cost, and risk impact

### ACCP Progress

| Version | Capabilities | Theme |
|---|---|---|
| v1.0 | 1/20 | Context graph (the substrate) |
| v2.0 | 7/20 | Two loops + eval gates + decision economics |
| v2.5 | 10/20 | Interactivity + governance (ROI, Feedback, Policy) |
| v2.5.1 | 10/20 | Bug fix: floating point display |
| **v3.0 (building)** | **13/20** | **Three loops. Auditable. Connected.** |
| v4.0 (planned) | 17/20 | Docker + Live Graph + Prompt Hub (partner-ready) |
| v5.0 (vision) | 20/20 | Second domain copilot + Control Tower |

### The Three Learning Loops

| Loop | Name | What It Does | Where Visible |
|---|---|---|---|
| Loop 1 | Situation Analyzer | Gets smarter WITHIN each decision — classifies alerts, evaluates options with time/cost/risk | Tab 3 |
| Loop 2 | AgentEvolver | Gets smarter ACROSS decisions — tracks prompt variant performance, auto-promotes winners | Tab 2 |
| **Loop 3** | **RL Reward / Penalty** | **Governs Loops 1 and 2 — asymmetric reinforcement (20:1 penalty), encodes security-first risk preference** | **Tab 2 (v3.0)** |

### Core Thesis

"Your SIEM gets better detection rules written by humans. Our SOC copilot gets smarter automatically through validated decisions."

**Experimentally validated:** 4 controlled experiments confirm scoring convergence (69.4%), cross-graph discovery (110× above random), super-quadratic scaling (n^2.30), and sharp phase transitions. Published in cross-graph-experiments repo.

### The Four Tabs + Current Features

**Tab 1: SOC Analytics** (20% energy)
- Natural language queries → governed security metrics
- Provenance showing data sources
- Rule sprawl detection ($18K/month waste found)

**Tab 2: Runtime Evolution** (35% energy) — THE DIFFERENTIATOR
- Process alert → 4 eval gates animate → TRIGGERED_EVOLUTION
- AgentEvolver panel: variant comparison, $4,800/mo recovered
- "Simulate Failed Gate" → BLOCKED banner
- **v3.0: Loop 3 panel — cumulative r(t), asymmetric ratio, decisions governed**

**Tab 3: Alert Triage** (30% energy)
- Alert queue → graph traversal (47 nodes) → recommendation
- Situation Analyzer with 6 classification types
- Decision Economics: 4 options with time/cost/risk
- Policy Conflict panel — detects, resolves, audits conflicting policies
- Closed Loop: EXECUTED → VERIFIED → EVIDENCE → KPI IMPACT
- Outcome Feedback — correct/incorrect buttons, asymmetric updates, self-correction
- **v3.0: Threat Intel badge — external data feed, refresh button, indicator count**

**Tab 4: Compounding Dashboard** (15% energy)
- Business Impact Banner: 847 hrs, $127K, 75% MTTR, 2,400 alerts
- Week-over-week comparison
- **v3.0: Three-Loop Hero Diagram + Four Layers context strip**
- ROI Calculator — modal with 6 input sliders, real-time projections, CFO narrative
- **v3.0: Evidence Ledger — tamper-evident decision audit, CSV export, chain verification**

---

## PART 2: Published Assets (Live)

### Live Blog Posts

| Post | URL | Status |
|---|---|---|
| Advert / demo blurb | https://www.dakshineshwari.net/post/after-ten-thousand-decisions-show-me-how-your-system-got-smarter | **LIVE — needs cleanup (5 placeholders, 3 broken links)** |
| Math blog | https://www.dakshineshwari.net/post/cross-graph-attention-mathematical-foundation-with-experimental-validation | **LIVE — needs 5×→20× fix** |
| CI blog (v4.0) | https://www.dakshineshwari.net/post/compounding-intelligence-4-0-how-enterprise-ai-develops-self-improving-judgment | **LIVE — needs 5×→20× fix** |
| Demo walkthrough | https://www.dakshineshwari.net/post/operationalizing-context-graphs-ciso-cybersecurity-ops-agent-demo | Live |

### Blog Fix: 5×→20× Asymmetry (P1 — Fix Before Loom v2)

Both blogs say `5×` asymmetry. Experiments validated `20×`. Demo shows `20:1`. Four searches per blog: `5:1`→`20:1`, `5×`→`20×`, `λ_neg = 5`→`λ_neg = 20`, `five correct`→`twenty correct`. See `blog_asymmetry_fixes.md` for full details.

### Advert Page — Outstanding Cleanup Items

1. **5 placeholder boxes still live** — delete all five (screenshots/graphics captions showing raw Wix URLs)
2. **"Go deeper" links — anchor text missing.** Three entries render as bare em-dashes. Add hyperlinked text for Math, CI, and Demo blogs.
3. **"For the VC" label** — appears before the graphic rather than after the heading.

---

## PART 3: Files and Links for Next Session

### Documents in Claude Project

| Document | Description |
|---|---|
| session_continuation_package_v7.md | THIS document |
| v3_design_document_v7.md | **v3.0 build spec — 10 prompts, 4 sessions, verification tests** |
| backlog_v6.md | Current work queue with priorities |
| blog_asymmetry_fixes.md | **5×→20× edit guide for both live blogs** |
| outreach_emails_v4.md | CISO + VC cold outreach emails |
| linkedin_posts_v4.md | LinkedIn posts (needs rewrite — see backlog) |
| loom_script_v5.docx | Loom v1 script (needs v2 rewrite for three loops) |
| code_review_plan_v25.md | Code review methodology |

### Superseded Documents (Remove from Project)

| Old Document | Replaced By |
|---|---|
| session_continuation_package_v6.md | session_continuation_package_v7.md |
| v3_design_document_v5.md | v3_design_document_v7.md |
| backlog_v5.md | backlog_v6.md |

### External Links

| # | Link | Priority |
|---|---|---|
| 1 | https://www.dakshineshwari.net/post/after-ten-thousand-decisions-show-me-how-your-system-got-smarter | **CRITICAL** |
| 2 | https://www.dakshineshwari.net/post/cross-graph-attention-mathematical-foundation-with-experimental-validation | **CRITICAL** |
| 3 | https://www.dakshineshwari.net/post/compounding-intelligence-4-0-how-enterprise-ai-develops-self-improving-judgment | **CRITICAL** |
| 4 | https://www.dakshineshwari.net/post/operationalizing-context-graphs-ciso-cybersecurity-ops-agent-demo | **CRITICAL** |
| 5 | https://github.com/ArindamBanerji/cross-graph-experiments | **HIGH** |
| 6 | https://www.loom.com/share/b45444f85a3241128d685d0eaeb59379 | **HIGH** |

### Git Context

```
Demo repo: git@github.com:ArindamBanerji/gen-ai-roi-demo.git
  Branch: main (v2.5.1 tagged)
  Working directory: gen-ai-roi-demo-v2
  Ports: 8001 (backend) / 5174 (frontend)
  Next branch: feature/v3.0-enhancements off main

Experiments repo: git@github.com:ArindamBanerji/cross-graph-experiments.git
  Branch: main (v1.0 tagged)
```

### Starting the Demo

```powershell
python scripts/check_neo4j.py
cd backend && uvicorn app.main:app --reload --port 8001
cd frontend && npx vite --port 5174
```

---

## PART 4: v3.0 Build Plan (Quick Reference)

### What's IN v3.0

| Session | Prompts | Feature | New Demo Moment |
|---|---|---|---|
| 1 | A1, A2, A3 | Loop 3 — RL Reward/Penalty | Tab 2: Loop 3 panel. Tab 4: Three-Loop Hero + Four Layers strip. |
| 2 | B2, B3 | Bug fixes | Policy override banner. Pulse removed. |
| 3 | EC1a, EC1b | Threat Intel feed | Tab 3: Threat Intel badge with refresh. |
| 4 | EL1, EL2, EL3 | Evidence Ledger | Tab 4: Tamper-evident audit table + CSV export. |

**Total: 10 prompts, 4 sessions. Tag v3.0 after Session 4.**

### What's OUT (Deferred to v4+)

Docker, Live Graph Integration, Prompt Hub, Process Intelligence. None creates a demo moment a VC/CISO remembers. See design doc v7.0 Section 7.

### Claude Code Rules (Every Prompt)

1. No git commands. No debugger.
2. Read before write. One concern per prompt.
3. Add, don't rewrite — find insertion point, leave surrounding code untouched.
4. No schema changes without explicit instruction.
5. Show your work (before/after lines). Don't start dev server.
6. Backend before frontend.

---

## PART 5: Session Openers for Claude Code

### Session 1: Loop 3 (Start Here)

```
This is a continuing thread for the SOC Copilot demo.
Status: v2.5.1 tagged. ACCP progress: 10/20 capabilities.
Repository: git@github.com:ArindamBanerji/gen-ai-roi-demo.git

Intent: Build Loop 3 — RL Reward/Penalty (Prompts A1, A2, A3).
Design spec: v3_design_document_v7.md, Feature A.
Create branch: feature/v3.0-enhancements off main

RULES: No git commands. No debugger. Read files before modifying.
Add code to existing files — do not rewrite or restructure.
Show before/after for each change. Do not start the dev server.

Start with Prompt A1: Add GET /api/rl/reward-summary endpoint.
Files: backend/app/services/feedback.py (add function),
       backend/app/routers/triage.py (add endpoint).
Read both files first.
```

### Session 2: Bug Fixes

```
Continuing SOC Copilot v3.0 build on branch feature/v3.0-enhancements.

Intent: Bug fixes — Prompts B2 and B3.
Design spec: v3_design_document_v7.md, Feature B.

RULES: No git commands. No debugger. Read before write.

Start with Prompt B2: Fix policy override of Recommendation panel.
File: frontend/src/components/tabs/AlertTriageTab.tsx (only this file).
Read fully before modifying.
```

### Session 3: Threat Intel

```
Continuing SOC Copilot v3.0 build on branch feature/v3.0-enhancements.

Intent: Threat Intel feed — Prompts EC1a and EC1b.
Design spec: v3_design_document_v7.md, Feature C.

RULES: No git commands. No debugger. Read before write.

Start with Prompt EC1a: Backend threat intel refresh endpoint.
New files: backend/app/services/threat_intel.py,
           backend/app/routers/graph.py
Modify: backend/app/main.py (add router — single line).
```

### Session 4: Evidence Ledger

```
Continuing SOC Copilot v3.0 build on branch feature/v3.0-enhancements.

Intent: Evidence Ledger — Prompts EL1, EL2, EL3.
Design spec: v3_design_document_v7.md, Feature D.

RULES: No git commands. No debugger. Read before write.

Start with Prompt EL1: Decision audit service + export endpoint.
New files: backend/app/services/audit.py,
           backend/app/routers/audit.py
Modify: backend/app/main.py (add router — single line).
```

### Loom v2 Script (After v3.0 Ships)

```
This is a continuing thread for the SOC Copilot demo.
Status: v3.0 complete. ACCP progress: 13/20 capabilities.

Intent: Write the Loom v2 demo script covering v3.0 features.
Read v1 Loom: https://www.loom.com/share/b45444f85a3241128d685d0eaeb59379
Key additions: Loop 3 panel (Tab 2), Threat Intel badge (Tab 3),
Three-Loop Hero + Four Layers + Evidence Ledger (Tab 4).
Target: 12-minute script + 3-minute LinkedIn short.
```

---

## PART 6: Key Soundbites (Quick Reference)

### v2.5 (Existing)

1. **Tab 2:** "Splunk gets better rules. Our copilot gets smarter."
2. **Tab 2 (blocking):** "What happens when the AI is wrong? Watch — it catches itself."
3. **Tab 2 (AgentEvolver):** "$4,800/month in recovered analyst time. Zero missed threats."
4. **Tab 3:** "A SIEM stops at detect. We close the loop."
5. **Tab 3 (economics):** "Every option shows time, cost, and risk. The CFO can read this."
6. **Tab 3 (policy):** "You have conflicting policies. We detect, resolve, and audit them."
7. **Tab 3 (feedback):** "Incorrect drops 6 points. Next 5 go to a human. That's self-correction."
8. **Tab 4:** "847 analyst hours. $127K per quarter. That's the board slide."
9. **Tab 4 (ROI):** "Plug in YOUR numbers. See YOUR savings. Take this to YOUR CFO."

### v3.0 (New)

10. **Tab 2 (Loop 3):** "Loop 1 makes decisions smarter. Loop 2 makes the system smarter. Loop 3 governs both. Three loops, one graph — that's the moat."
11. **Tab 3 (Threat Intel):** "The graph absorbed 7 new threat indicators. The next decision is richer because the context is richer."
12. **Tab 4 (Evidence Ledger):** "Every decision the AI made, why, and whether it was right. Tamper-evident. Exportable. Take it to your board."
13. **Tab 4 (Four Layers):** "UCL, Agent Engineering, ACCP, Domain Copilots — four dependency-ordered layers. Remove any one, compounding stops."
14. **ACCP:** "Thirteen of twenty ACCP capabilities. Running code, not a pitch deck."
15. **Moat:** "The gap widens as n^2.3. A competitor starting 12 months late faces a permanently widening deficit."

---

## PART 7: Known Issues and Polish Items

| Issue | Severity | Where | Status |
|---|---|---|---|
| ~~Floating point display~~ | ~~Low~~ | ~~OutcomeFeedback.tsx~~ | **✅ DONE (v2.5.1)** |
| Advert placeholder boxes still live | High | Wix advert post | ❌ Pending (manual) |
| Advert "Go deeper" links broken | High | Wix advert post | ❌ Pending (manual) |
| Blog 5×→20× asymmetry | **P1** | Both live blogs | **❌ Fix before Loom v2** |
| Policy override doesn't suppress Recommendation | Design gap | Tab 3 | Fix in v3.0 (B2) |
| ROI button pulse animation | Cosmetic | Tab 4 | Fix in v3.0 (B3) |
| Backend services use in-memory state | Medium | feedback.py, policy.py | Defer to v4.0 (Live Graph) |
| LinkedIn posts need rewrite | Medium | linkedin_posts_v4.md | 8-10 posts need LinkedIn-native rewrites |
| Loom v2 not yet recorded | Medium | Loom | After v3.0 ships + blog fixes |

---

*SOC Copilot Demo — Session Continuation Package v7.0 | February 24, 2026*
*Status: v2.5.1 tagged. Design doc v7.0 finalized. Ready for v3.0 Session 1 (Loop 3).*
*Parallel: Blog 5×→20× fix, advert cleanup, LinkedIn post rewrites.*
