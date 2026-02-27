# SOC Copilot Demo — Session Continuation Package v9

**Date:** February 24, 2026
**Status:** v3.1.1 complete and tagged. Customer feedback fully integrated. Outreach docs updated.
**Next Session Focus:** Blog advert replacement (Wix) → Record Loom v2 → Code review → v4.0 build
**Repositories:**
- Demo: git@github.com:ArindamBanerji/gen-ai-roi-demo.git (main, v3.1.1 tag)
- Experiments: git@github.com:ArindamBanerji/cross-graph-experiments.git (main, v1.0 tag)
**Working directories:**
- v2 (demo-ready for prospects): gen-ai-roi-demo-v2 (main, v2.5.1)
- v3 (current): gen-ai-roi-demo-v3 (main, v3.1.1)

---

## PART 1: What Is This Project?

### The Demo

The SOC Copilot Demo is a working prototype of an AI-augmented Security Operations Center (SOC) that demonstrates **compounding intelligence** — the system gets smarter over time through three learning loops feeding one living context graph. Built with FastAPI (Python) + React/TypeScript + Neo4j Aura, it runs locally on ports 8000 (backend) / 5173 (frontend).

### The Architecture: ACCP + Four Layers

The demo is the progressive reference implementation of the **Agentic Cognitive Control Plane (ACCP)** — an architectural pattern for governed, self-improving enterprise AI organized in four dependency-ordered layers:

1. **UCL (Unified Context Layer)** — governed substrate integrating CrowdStrike, Pulsedive, SIEM data
2. **Agent Engineering** — runtime evolution of prompt variants and reasoning approaches
3. **ACCP** — cognitive control plane with eval gates, decision economics, policy resolution
4. **SOC Copilot** — domain-specific copilot built on the three layers below

### ACCP Progress

- v1.0: 1/21 (context graph)
- v2.0: 7/21 (+ situation classification, eval gates, TRIGGERED_EVOLUTION, decision economics, both loops)
- v2.5: 10/21 (+ ROI Calculator, Outcome Feedback, Policy Conflict)
- v2.5.1: 10/21 (bug fix: floating point display)
- v3.0: 14/21 (+ Loop 3, External Context with live Pulsedive API, Evidence Ledger, Decision Transparency)
- **v3.1.1 (current): 14/21** (+ Tab 1 Threat Landscape, cross-context queries, seed data fix, Evidence Ledger wiring, dotenv fix)

### Core Thesis

"Your SIEM gets better detection rules written by humans. Our SOC copilot gets smarter automatically through validated decisions."

**Positioning (from customer meetings):**
- "CrowdStrike detects. Pulsedive enriches. We decide — and we get better at deciding with every verified outcome."
- "Your tools produce independent verdicts. Our graph produces fused intelligence."
- "Adding a new source is config, not a project."

### Customer Insights (Feb 24, 2026)

Three insights from customer meeting that shaped v3.1 and outreach:

1. **Manual IOC workflow:** Customer manually checks 4-5 open source IOC sites (Pulsedive, GreyNoise, Health-ISAC, etc.), then pastes into CrowdStrike explorer. ~2 hours/shift wasted on mechanical work.
2. **Health-ISAC as sector-specific feed:** https://health-isac.org/ — 15-year-old health sector ISAC, 85% of top 25 global pharma. Members still manually consume and act on shared IOCs.
3. **Semantic fusion gap:** Each source returns independent verdicts with different schemas/confidence models. Nobody fuses them. The analyst holds integration in their head — invisible, unrepeatable, gone at shift change.

### The Three Learning Loops

| Loop | Name | What It Does | Where Visible |
|---|---|---|---|
| Loop 1 | Situation Analyzer | Gets smarter WITHIN each decision — classifies alerts, evaluates options with time/cost/risk | Tab 3 |
| Loop 2 | AgentEvolver | Gets smarter ACROSS decisions — tracks prompt variant performance, auto-promotes winners | Tab 2 |
| Loop 3 | RL Reward / Penalty | GOVERNS both loops — continuous reinforcement signal with 20:1 asymmetric penalty | Tab 2 + Tab 4 |

### The Four Tabs

**Tab 1: SOC Analytics** (20% energy — upgraded in v3.1)
- **Threat Landscape at a Glance** — 4-group summary strip (Threat Intel / Active Alerts / Governance / Graph Coverage) auto-loads on mount
- Natural language queries → governed security metrics with provenance
- **Cross-context queries** — 4 new graph queries no SIEM can run (travel risk, device trust, policy conflicts, threat intel coverage)
- Cypher query previews in provenance panel
- Separated example chips: standard SOC metrics vs. cross-context queries

**Tab 2: Runtime Evolution** (25% energy)
- Process alert → 4 eval gates animate → TRIGGERED_EVOLUTION
- AgentEvolver panel: variant comparison, $4,800/mo recovered
- "Simulate Failed Gate" → BLOCKED banner
- Loop 3 panel — cumulative r(t), 20:1 asymmetric bar, decisions governed

**Tab 3: Alert Triage** (35% energy)
- Alert queue → graph traversal (47 nodes) → recommendation
- Situation Analyzer with 6 classification types
- Decision Economics: 4 options with time/cost/risk
- "Why This Decision?" panel — 6-factor breakdown with colored bars, including live threat intel factor
- Threat Intel badge — 🛡️ shows Pulsedive (live) or Local fallback, with refresh button
- Policy Conflict panel — detects, resolves, audits conflicting policies
- Policy Override — amber banner + "Apply Policy Resolution" button
- Closed Loop: EXECUTED → VERIFIED → EVIDENCE → KPI IMPACT
- Outcome Feedback — correct/incorrect buttons, asymmetric graph updates

**Tab 4: Compounding Dashboard** (20% energy)
- Business Impact Banner: 847 hrs, $127K, 75% MTTR, 2,400 alerts
- Three-Loop Hero Diagram — blue/purple/amber panels
- Four Layers strip — UCL → Agent Engineering → ACCP → SOC Copilot
- **Evidence Ledger** — tamper-evident SHA-256 hash chain, decision table, CSV export, chain verification (now wired to execution path)
- ROI Calculator + Week-over-week + Evolution Events

---

## PART 2: What v3.1 Built (Session Summary)

### v3.0 (Sessions 1-5)

| Session | Feature | Key Demo Moment |
|---|---|---|
| 1 | Loop 3 backend + frontend, Three-Loop Hero, Four Layers strip | Tab 2: RL panel. Tab 4: architecture diagram. |
| 2 | Policy Override fix, ROI button pulse fix | Tab 3: amber banner. |
| 3 | Live Pulsedive API with fallback, Threat Intel badge | Tab 3: 🛡️ badge. |
| 4 | Evidence Ledger with SHA-256 hash chain | Tab 4: tamper-evident audit. |
| 5 | Decision Explainer with live threat intel factor | Tab 3: "Why This Decision?" |

### v3.1 / v3.1.1 (This Session)

| Feature | What Changed |
|---|---|
| 4 cross-context queries | Tab 1: travel risk, device trust, policy conflicts, threat intel coverage |
| Threat Landscape panel | Tab 1: 4-group summary auto-loads, shows graph state before any query |
| Cross-context separator | Tab 1: visual grouping of standard vs. graph queries |
| Evidence Ledger wiring | record_decision() now called from execute_action() — ledger populates |
| Seed data fix | Added ALERT-7824, fixed 2 orphaned alerts, added 2 users, pattern mapping |
| Port fix | vite.config.ts proxy: 8001 → 8000 |
| dotenv fix | load_dotenv(dotenv_path="../.env") in main.py |
| Reset fix | handleResetAlerts no longer overrides auto-selection; CompoundingTab calls resetAlerts() |

### Customer Feedback Addressed (Cumulative)

| Customer Question | v3.0 Response | v3.1 Response |
|---|---|---|
| "Your threat intel is fake" | Live Pulsedive API (EC1a) | — |
| "Where do you fit with CrowdStrike?" | Four Layers strip (A3) | — |
| "How do you decide severity?" | Decision Explainer (DX1/DX1b) | — |
| "We check IOCs across 4-5 sites manually" | — | Tab 1 Threat Landscape + cross-context queries |
| "How do you integrate Health-ISAC?" | — | Connector pattern in outreach; Health-ISAC referenced |
| "Can you fuse Pulsedive + GreyNoise?" | — | Semantic fusion concept in outreach + Loom script |

---

## PART 3: Published Assets

### Live Blog Posts

| Post | URL | Status |
|---|---|---|
| Advert / demo blurb | https://www.dakshineshwari.net/post/after-ten-thousand-decisions-show-me-how-your-system-got-smarter | **NEEDS FULL REPLACEMENT** — blog_advert_replacement_v2.md ready |
| Math blog | https://www.dakshineshwari.net/post/cross-graph-attention-mathematical-foundation-with-experimental-validation | ✅ Live — 5×→20× fixed |
| CI blog (v4.0) | https://www.dakshineshwari.net/post/compounding-intelligence-4-0-how-enterprise-ai-develops-self-improving-judgment | ✅ Live — 5×→20× fixed |
| Demo walkthrough | https://www.dakshineshwari.net/post/operationalizing-context-graphs-ciso-cybersecurity-ops-agent-demo | ✅ Live |

### Outreach Documents

| Document | Version | Status |
|---|---|---|
| Outreach emails | **v6** | ✅ Updated — customer pain narrative, Health-ISAC, semantic fusion |
| LinkedIn posts | **v6** | ✅ Updated — A-4 rewritten, A-5 new (Threat Landscape), 8 posts total |
| Loom script | **v7** | ✅ Updated — Tab 1 as Act 1, manual IOC workflow, semantic fusion, ports fixed |
| Blog advert replacement | **v2** | ✅ Ready — full rewrite with v3.1 features + customer insights |

### Advert Page Cleanup Items (Still Pending)

1. **FULL REPLACEMENT** — use blog_advert_replacement_v2.md (replaces entire page content)
2. Update screenshots to v3.1 (Tab 1 Landscape, Tab 3 Decision Explainer, Tab 4 Evidence Ledger)
3. Fix "Go deeper" link formatting

---

## PART 4: Files and Links for Next Session

### Documents in Claude Project (update these)

| Document | Current | Update To |
|---|---|---|
| session_continuation_package | v8 | **v9 (this document)** |
| backlog | v7 | **v8** |
| outreach_emails | v4 (project) / v6 (outputs) | **v6** |
| linkedin_posts | v4 (project) / v6 (outputs) | **v6** |
| loom_script | v5 (project) / v7 (outputs) | **v7** |
| code_review_plan | v25 | **v31 (update for v3.1 codebase)** |
| v4_design_document | v1 | v1 (no changes needed yet) |

### External Links

| # | Link | Status |
|---|---|---|
| 1 | https://www.dakshineshwari.net/post/after-ten-thousand-decisions-show-me-how-your-system-got-smarter | **REPLACE with blog_advert_replacement_v2.md** |
| 2 | https://www.dakshineshwari.net/post/cross-graph-attention-mathematical-foundation-with-experimental-validation | ✅ Live |
| 3 | https://www.dakshineshwari.net/post/compounding-intelligence-4-0-how-enterprise-ai-develops-self-improving-judgment | ✅ Live |
| 4 | https://www.dakshineshwari.net/post/operationalizing-context-graphs-ciso-cybersecurity-ops-agent-demo | ✅ Live |
| 5 | https://github.com/ArindamBanerji/cross-graph-experiments | ✅ Live |
| 6 | https://www.loom.com/share/b45444f85a3241128d685d0eaeb59379 | v1 — **v2 not yet recorded** |

### Git Context

```
Demo repo: git@github.com:ArindamBanerji/gen-ai-roi-demo.git
  Branch: main (v3.1.1 tagged)
  v2 directory: gen-ai-roi-demo-v2 (v2.5.1 — keep for prospect demos)
  v3 directory: gen-ai-roi-demo-v3 (v3.1.1 — current)
  Ports: 8000 (backend) / 5173 (frontend)

Experiments repo: git@github.com:ArindamBanerji/cross-graph-experiments.git
  Branch: main (v1.0 tagged)
```

### API Keys (.env in project root)

```
NEO4J_URI=<configured>
NEO4J_USER=<configured>
NEO4J_PASSWORD=<configured>
PULSEDIVE_API_KEY=<configured> (50/day free tier — resets midnight UTC)
GREYNOISE_API_KEY=<configured — for v4>
```

### Starting the Demo

```powershell
cd gen-ai-roi-demo-v3

# Terminal 1 — backend
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm run dev

# Optional: refresh threat intel (costs API calls — 5 per refresh)
curl -X POST http://localhost:8000/api/graph/threat-intel/refresh

# Reset demo state
curl -X POST http://localhost:8000/api/demo/reset-all
```

**Pulsedive note:** Free tier = 50 calls/day. One refresh = 5 calls. Budget ~10 refreshes/day. For Loom recording, refresh once early, don't burn calls on testing.

---

## PART 5: Session Openers for Claude Code

### Session Opener A: Code Review (PRIORITY)

```
This is a continuing thread for the SOC Copilot demo.
Status: v3.1.1 complete and tagged. ACCP progress: 14/21 capabilities.
Repository: gen-ai-roi-demo-v3
Ports: 8000 (backend) / 5173 (frontend)

RULES:
1. No git commands. No debugger. Read before write.
2. Do not start dev servers.

TASK: Comprehensive code review of v3.1.1 codebase.
Read every file in backend/app/ and frontend/src/.
Perform three review passes per code_review_plan_v31.md.
Output: docs/CODE_REVIEW_V31.md
```

### Session Opener B: v4.0 Build (UCL Connectors)

```
This is a continuing thread for the SOC Copilot demo.
Status: v3.1.1 complete and tagged. ACCP progress: 14/21 capabilities.
Repository: gen-ai-roi-demo-v3

RULES:
1. No git commands. No debugger. Read before write.
2. Add, don't rewrite. Show before/after.

Intent: Build UCL Connector base class and refactor Pulsedive into connector pattern.
Key docs: v4_design_document_v1.md (Prompts C1, C3)
```

### Session Opener C: Docker for Partners

```
This is a continuing thread for the SOC Copilot demo.
Status: v3.1.1 complete and tagged. ACCP progress: 14/21.

RULES:
1. No git commands. No debugger. Read before write.
2. Add, don't rewrite. Show before/after.

Intent: Docker packaging for consulting partners.
Key docs: v4_design_document_v1.md (Prompts D1-D5)
```

---

## PART 6: Key Soundbites (Updated for v3.1)

1. **Tab 1 (Landscape):** "This is what the graph knows before a single query. Your SIEM shows alerts. We show context."
2. **Tab 1 (Manual workflow):** "Five browser tabs. Copy-paste. Two hours per shift. This replaces that."
3. **Tab 1 (Cross-context):** "Six data sources. One query. Your SIEM can't do this."
4. **Tab 2:** "Splunk gets better rules. Our copilot gets smarter."
5. **Tab 2 (Loop 3):** "Penalty is 20× reward. The system earns trust slowly and loses it fast."
6. **Tab 2 (blocking):** "What happens when the AI is wrong? Watch — it catches itself."
7. **Tab 3:** "A SIEM stops at detect. We close the loop."
8. **Tab 3 (Decision Explainer):** "Six factors. Weighted. Transparent. The system shows its work."
9. **Tab 3 (Semantic fusion):** "Two sources, different schemas — fused on a single graph node."
10. **Tab 3 (Threat Intel):** "That's not simulated data. Live Pulsedive. Real risk scores."
11. **Tab 3 (policy):** "You have conflicting policies. We detect, resolve, and audit them."
12. **Tab 3 (policy override):** "The AI said auto-close. Policy said escalate. Policy wins."
13. **Tab 4 (Four Layers):** "CrowdStrike detects. Pulsedive enriches. We decide."
14. **Tab 4 (Connectors):** "Adding a new source is config, not a project."
15. **Tab 4 (Evidence Ledger):** "Every decision. Tamper-evident. SHA-256 chain. Take it to your board."
16. **Tab 4 (ROI):** "Plug in YOUR numbers. See YOUR savings. Take this to YOUR CFO."
17. **ACCP:** "Fourteen of twenty-one capabilities. Running code, not a pitch deck."
18. **Moat:** "They don't start six months behind. They start at zero."

---

## PART 7: Known Issues

| Issue | Severity | Notes |
|---|---|---|
| Blog advert page outdated | **P0** | Replacement text ready (blog_advert_replacement_v2.md) |
| Pulsedive: 50/day free tier | Low | Rate limit exhausted during testing. Resets midnight UTC. Consider $50/mo upgrade. |
| Loom v2 not recorded | **P1** | Script v7 ready. Record after blog replacement. |
| Code review not done for v3.1 | **P1** | Codebase grew significantly. Review before v4. |
| 20 pre-existing TypeScript errors | Low | In untouched files. Not blocking. |
| Backend services use in-memory state | Medium | Fine for demo, fix in v4 (Live Graph phase) |

---

## PART 8: Priority Queue

| Priority | Item | Effort | Blocking What |
|---|---|---|---|
| **P0** | Replace blog advert in Wix | 30 min | Prospect-readiness |
| **P0** | Take v3.1 screenshots for blog | 15 min | Blog advert |
| **P1** | Record Loom v2 using script v7 | 1 hour | Outreach emails |
| **P1** | Post LinkedIn Series A + B (8 posts) | Manual | Social presence |
| **P1** | Code review (3-pass, v3.1.1 codebase) | 2 sessions | v4 build confidence |
| **P2** | v4.0 Phase 1: UCL Connectors | 3 sessions | Platform thesis |
| **P2** | v4.0 Phase 2: Docker + Live Graph | 3 sessions | Partner self-service |
| **P3** | v4.0 Phase 3: Prompt Hub + Polish | 2 sessions | Exec UX |
| **P3** | In-repo doc updates (CLAUDE.md, README) | 1 session | Maintainability |

---

*SOC Copilot Demo — Session Continuation Package v9 | February 24, 2026*
*Status: v3.1.1 (14/21 ACCP). Blog advert replacement ready. Outreach v6/v7. Customer insights integrated. Next: Wix update, Loom v2, code review, then v4.*
