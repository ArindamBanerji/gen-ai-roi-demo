# SOC Copilot Demo — Session Continuation Package v11

**Date:** February 26, 2026
**Status:** v3.2 complete and tagged. Product strategy + positioning completed. Sequential v4.0 → v4.5 build planned.
**Next Session Focus:** Clone v3.2 → v4 directory, verify code review fixes, begin v4.0 Phase 1 (Connectors)
**Repositories:**
- Demo: git@github.com:ArindamBanerji/gen-ai-roi-demo.git (main, v3.2 tag)
- Experiments: git@github.com:ArindamBanerji/cross-graph-experiments.git (main, v1.0 tag)
**Working directories:**
- v2 (demo-ready for prospects): gen-ai-roi-demo-v2 (main, v2.5.1)
- v3.2 (current stable demo): C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects\gen-ai-roi-demo-v3.2
- v4 (next build): clone of v3.2 → gen-ai-roi-demo-v4 (to be created)

---

## PART 1: What Is This Project?

### The Demo

The SOC Copilot Demo is a working prototype of an AI-augmented Security Operations Center (SOC) that demonstrates **compounding intelligence** — the system gets smarter over time through three learning loops feeding one living context graph. Built with FastAPI (Python) + React/TypeScript + Neo4j Aura. Runs locally on ports 8000 (backend) / 5174 (frontend).

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
- v3.0: 14/21 (+ Loop 3, External Context with live Pulsedive API, Evidence Ledger, Decision Transparency)
- v3.1.1: 14/21 (+ Tab 1 Threat Landscape, cross-context queries, seed data fix, Evidence Ledger wiring)
- **v3.2 (current): 14/18 ACCP** (domain-agnostic refactoring: core/, domains/soc/, domains/supply_chain/ stub, domain_registry.py, state_manager.py — ~14,000 lines, ~42 files)

*Note: ACCP capability count adjusted from /21 to /18 in v3.2 PROJECT_STRUCTURE. Capabilities 15-18 are planned for v3.5-v4.0.*

### Core Thesis & Positioning

**The compounding cycle:** Accumulate → Adjust → Respond → Discover

Five things compound simultaneously, each feeding the others:
1. **Semantics accumulate** — UCL entity-resolves across domains. Connected meaning, not flat facts.
2. **Judgment adjusts** — AgentEvolver rewrites routing, scoring, context policies from verified outcomes. LLM stays frozen.
3. **Response changes** — Situation Analyzer reads the same alert differently as the graph evolves. Same alert, richer graph, different decision.
4. **Dimensions discovered** — Cross-graph discovery creates new evaluation criteria nobody programmed.
5. **Signals found** — Sweeps find semi-related signals across domain boundaries. Discoveries feed the next sweep — recursive.

**Positioning lines:**
- "After ten thousand decisions, show me how your system got smarter. We can. They can't."
- "They rent intelligence. We build it. The moat is in the layer you own — the graph — not the layer you rent — the model."
- "CrowdStrike detects. Pulsedive enriches. We decide — and we get better at deciding with every verified outcome."

**Competitive position (40+ vendor market):**
- Torq ($1.2B): automates playbooks — doesn't learn. Day 1,000 = Day 1.
- Dropzone AI: accumulates facts (Context Memory) — better cheat sheet, same reasoning. LLM-dependent moat.
- Intezer: deep forensic investigation — no feedback loop. Static.
- CrowdStrike Charlotte: per-alert reasoning, locked ecosystem. No cross-alert learning.
- Us: structurally different decision-maker. Firm-specific, model-independent, temporally irreversible moat.

### The Three Learning Loops

| Loop | Name | What It Does | Where Visible |
|---|---|---|---|
| Loop 1 | Situation Analyzer | Gets smarter WITHIN each decision — classifies alerts, evaluates options with time/cost/risk | Tab 3 |
| Loop 2 | AgentEvolver | Gets smarter ACROSS decisions — tracks prompt variant performance, auto-promotes winners | Tab 2 |
| Loop 3 | RL Reward / Penalty | GOVERNS both loops — continuous reinforcement signal with 20:1 asymmetric penalty | Tab 2 + Tab 4 |

### The Four Tabs

**Tab 1: SOC Analytics** — Threat Landscape at a Glance, natural language queries, cross-context graph queries
**Tab 2: Runtime Evolution** — Process alert → 4 eval gates → TRIGGERED_EVOLUTION, AgentEvolver, Loop 3 panel
**Tab 3: Alert Triage** — Alert queue → graph traversal → situation analysis → 6-factor breakdown → policy conflict → feedback
**Tab 4: Compounding Dashboard** — Business Impact Banner, Three-Loop Hero, Four Layers strip, Evidence Ledger, ROI Calculator

### Development Model

- **Design & planning:** Claude Opus (this project — breaks work into Claude Code prompts)
- **Code development:** Claude Code Sonnet (receives prompts, writes code)
- **Code review:** Claude Code Opus (separate review pass)
- **Rules for Claude Code:** No git commands. No debugger. Read before write. One concern per prompt. Add, don't rewrite. Show before/after.
- **Human handles:** Git operations, directory cloning/cleanup, server restarts, testing

---

## PART 2: What v3.2 Built

### v3.2 — Domain-Agnostic Refactoring (Complete)

| Component | What Changed |
|---|---|
| `backend/app/core/` (new) | Framework layer — `state_manager.py` (centralized reset), `domain_registry.py` (registry of domain configs) |
| `backend/app/domains/base.py` (new) | `DomainConfig` ABC — 10 abstract properties + 3 abstract methods |
| `backend/app/domains/soc/` (new) | SOC implementation extracted: `config.py`, `factors.py`, `situations.py`, `policies.py` |
| `backend/app/domains/supply_chain/` (new) | S2P stub: `config.py` with full schema, stubs for classify/compute |
| `frontend/src/lib/domain.ts` (new) | Frontend domain config singleton |
| Services updated | `situation.py`, `triage.py`, `policy.py` now delegate to domain modules |
| `GET /api/demo/domains` | New endpoint listing available domains |

**Key architectural outcome:** Adding a new domain = create `domains/new_domain/config.py` + register in `domain_registry.py`. Zero changes to `core/`.

### Code Review Status (v3.1.1 — Pass 1)

| Severity | Count | Status |
|---|---|---|
| HIGH | 3 | **Some/several fixed in v3.2 — verification needed** |
| MEDIUM | 11 | Partially addressed |
| LOW | 8 | Deferred |

**Top HIGH findings:** (1) Reset doesn't clear audit/evolver state, (2) Version label wrong, (3) Stale UI after reset. Verification prompt provided in Part 5 below.

---

## PART 3: Roadmap — Sequential v4.0 → v4.5

### Version Map

| Version | Theme | Prompts | Status | Build Approach |
|---|---|---|---|---|
| v3.2 | Platform core. Multi-copilot ready. | — | ✅ Complete | — |
| **v4.0** | **Your tools, our decisions. Compounding proved.** | **36 prompts (33 code + 3 VPS)** | **Next build** | **Sequential — ~13 sessions** |
| **v4.5** | **INOVA MVP + Flash Tier + cross-domain discovery.** | **19 prompts (15 code + 4 VPS)** | **After v4.0 tagged** | **Sequential — ~7 sessions** |
| v5.0 | Validated POC — real data. Cloud pilot. | Designed | Blocked by BAA + data agreement |
| v6.0 | Production — single tenant. | Planned | Blocked by v5 gate |
| v7.0 | Multi-tenant + S2P/FinServ copilots. | Roadmap | — |

**Key design decision:** v4.0 and v4.5 are **sequential, not parallel.** v4.0 is built, tested, and tagged first. v4.5 assumes ALL of v4.0 is complete.

### v4.0 Scope (36 prompts, 5 phases + VPS)

| Phase | What | Prompts | Sessions |
|---|---|---|---|
| Phase 1 | UCL Connectors + ATT&CK alignment (F1) + realistic alerts (F2) | C1-C5b, T1, F1-1, F1-2, F2-1 | 4 |
| Phase 2 | Docker for Partners | D1-D5 | 2 |
| Phase 2.5 | VPS Hosting (demo.dakshineshwari.net) | VPS-1, VPS-2, VPS-3 | 1 |
| Phase 3 | Live Graph Integration | LG1-LG4 | 2 |
| Phase 4 | Polish: Query Hub, fuzzy matching, Four Clocks | PH1, PH2, FC1 | 1 |
| Phase 5 | Compounding Proof: narrative (F3), proof panel (F4), trust curve (F6) | NAR-1 to NAR-3, CP-1 to CP-3, TC-1, TC-2 | 3 |

### v4.5 Scope (19 prompts — after v4.0 tagged)

| Session | What | Prompts |
|---|---|---|
| A | UCL Entity Resolution + connector opt-in | INOVA-1a, INOVA-1b |
| B | TRIGGERED_EVOLUTION + CALIBRATED_BY write-back | INOVA-2 |
| C | Healthcare connectors: CISA KEV (live), Health-ISAC (mock) | INOVA-3a, INOVA-3b |
| D | Cross-graph discovery sweep (F5) + scheduler | INOVA-4a to INOVA-4c, F5-1 to F5-4 |
| E | Loop 3 governing signal + HIPAA framing + Tab 4 | INOVA-5, INOVA-6 |
| F | Flash Tier mimic | FT-MIMIC-1 to FT-MIMIC-4 |
| G | VPS multi-instance management | VPS-4 |

### Deployment Progression

| Version | Deployment | Data | Auth | Cost |
|---|---|---|---|---|
| v3.2 | Local only | Synthetic seed | None | $0 |
| v4.0 | **Docker + VPS** | Synthetic + live Pulsedive | HTTP basic | $9-18/mo |
| v4.5 | VPS multi-instance | Synthetic + multiple live feeds | Token per instance | $18/mo |
| v5.0 | Cloud pilot (GCP/AWS) | Real customer data subset | SSO/OAuth | $50-150/mo |

---

## PART 4: Published Assets & Documents

### Live Blog Posts

| Post | URL | Status |
|---|---|---|
| Demo blurb (v3.1) | https://www.dakshineshwari.net/post/after-ten-thousand-decisions-show-me-how-your-system-got-smarter-v3-1 | ✅ Live (updated Feb 26) |
| CI blog (v4.0) | https://www.dakshineshwari.net/post/compounding-intelligence-4-0-how-enterprise-ai-develops-self-improving-judgment | ✅ Live |
| Math blog | https://www.dakshineshwari.net/post/cross-graph-attention-mathematical-foundation-with-experimental-validation | ✅ Live |
| Demo walkthrough | https://www.dakshineshwari.net/post/operationalizing-context-graphs-ciso-cybersecurity-ops-agent-demo | ✅ Live |

### Design & Strategy Documents (Current)

| Document | Version | What It Contains |
|---|---|---|
| **product_strategy_v1.md** | 1.0 | Competitive analysis, three-axis framework, nine value features (F1-F9), three-tier prioritization, Dropzone/Torq/Intezer deep-dives |
| **v4_design_document_v3.md** | 3.0 | v4.0 implementation — 5 phases, 33 code prompts, Phase 5 compounding proof |
| **v4_5_design_v5.md** | 5.0 | v4.5 implementation — F5 cross-domain discovery, 18 code prompts |
| **soc_copilot_roadmap_v4.md** | 4.0 | Roadmap with competitive positioning, all nine features mapped, cross-vertical capability map, "Why the Moat Is Structural" section |
| **deployment_strategy_v3.md** | 3.0 | Progressive Realism philosophy, VPS hosting tier (Hetzner CX31), cost model ($0→$9→$150→$800), VPS prompts |

### Positioning Graphics (NBP Prompts — Current)

| Graphic | Title | Purpose | Source File |
|---|---|---|---|
| **POS-00A** | The New Employee Problem | Opening hook — the analogy every CISO has lived | nbp_pos00_v4_final.md |
| **POS-00B** | What Actually Compounds (Cascade) | Five mechanisms ascending: accumulate→adjust→respond→discover | nbp_pos00_final_pair.md |
| **POS-00C** | Synopsis — Four Blocks | Complete story: Problem / Mechanism / Field / Moat | nbp_pos00c_two_designs.md (2 options) |
| **POS-01** | Three Axes of Compounding Intelligence | Framework — how institutional judgment develops | nbp_positioning_prompts_v2.md |
| **POS-02** | Three Generations — What Evolves? | Row-by-row comparison: SOAR vs AI SOC vs Decision Intelligence | nbp_positioning_prompts_v2.md |
| **POS-03** | The Compounding Curve | Abstract stages: Baseline→Early Learning→Calibrated→Compounding | nbp_batch2_prompts.md |
| **POS-04** | Dropzone vs. Compounding Intelligence | Deep-dive on closest competitor | nbp_positioning_prompts_v2.md |
| **POS-05** | AI SOC Competitive Landscape (2×2 Quadrant) | 40+ players positioned on Learning × Depth axes | nbp_positioning_prompts_v2.md |
| **POS-06** | SOC AI Capability Landscape (10×7 Matrix) | Table stakes vs. compounding layer — the receipts slide | nbp_pos06_v2.md |

### Outreach Documents

| Document | Version | Status |
|---|---|---|
| Outreach emails | v6 | ✅ Current — update after v4.0 Phase 1 |
| LinkedIn posts | v6 | ✅ Current — 8 posts (A-1 thru A-5, B-1 thru B-3) |
| Loom script | v8 | ✅ Current — Loom v2 not yet recorded |
| Blog advert replacement | v3 | In docs directory |
| Deck storyboards | A v3, B v5 | In docs directory |

### Loom Videos

| Version | URL | Status |
|---|---|---|
| v1 | https://www.loom.com/share/b45444f85a3241128d685d0eaeb59379 | ✅ Live |
| v2 | — | Script ready (v8). Record after code review fixes verified. |

---

## PART 5: Claude Code Session Openers

### Pre-Work (Human — before first Claude Code session)

```
1. Clone gen-ai-roi-demo-v3.2 → gen-ai-roi-demo-v4
2. Clean docs directory (see backlog_v10.md Section B0)
3. Add new docs: session_continuation_package_v11.md, backlog_v10.md, product_strategy_v1.md, v4_design_document_v3.md, v4_5_design_v5.md, soc_copilot_roadmap_v4.md, deployment_strategy_v3.md
4. Verify v3.2 demo still runs in original directory
```

### Session Opener 0: Verify Code Review Fixes

```
This is a continuing thread for the SOC Copilot demo.
Status: v3.2 complete and tagged. Domain-agnostic refactoring done.
Repository: gen-ai-roi-demo-v4 (cloned from v3.2)
Ports: 8000 (backend) / 5174 (frontend)

RULES:
- Do NOT use git directly. I handle all git operations.
- Do NOT start the debugger. Log-based debugging only.
- Read before write. Check existing code before making changes.
- One concern per prompt. Don't touch unrelated code.

DOCS TO READ FIRST:
- docs/PROJECT_STRUCTURE.md (architecture overview, file map)
- docs/CODE_REVIEW_V31_PASS1.md (the review findings)

TASK: Verify the three HIGH findings from the v3.1.1 code review:

H-1: "Reset doesn't clear audit trail or evolver state"
→ Check if state_manager.py (v3.2) now clears these on reset.

H-2: "Version label shows wrong version"
→ Check if version label was updated to v3.2 in app_state.py.

H-3: "Stale UI after reset"
→ Check if frontend refreshes properly after /api/demo/reset.

For each: report FIXED, PARTIALLY FIXED, or NOT FIXED.
If NOT FIXED, describe what needs to change (but don't change it yet — just report).
```

### Session Opener 1: v4.0 Phase 1, Prompt C1 (Connector Base Class)

```
This is a continuing thread for the SOC Copilot demo.
Status: v4.0 build starting. v3.2 domain-agnostic refactoring is the base.
Repository: gen-ai-roi-demo-v4
Ports: 8000 (backend) / 5174 (frontend)

RULES:
- Do NOT use git directly. I handle all git operations.
- Do NOT start the debugger. Log-based debugging only.
- Read before write.
- One concern per prompt.

DOCS TO READ FIRST:
- docs/PROJECT_STRUCTURE.md
- docs/v4_design_document_v3.md (Section 4.1 — Phase 1 prompt specs)

TASK [C1]: Create the UCL Connector base class and registry.

This establishes the connector pattern that Pulsedive, GreyNoise, and CrowdStrike will use.

Files to create:
- backend/app/connectors/base.py — ConnectorBase ABC
- backend/app/connectors/registry.py — ConnectorRegistry (discover, register, query)
- backend/app/connectors/__init__.py

Files to modify:
- backend/app/services/graph.py — import ConnectorRegistry
- backend/app/main.py — initialize ConnectorRegistry on startup

See v4_design_document_v3.md Section 4.1, Prompt C1 for full spec.

DO NOT touch domains/, core/, or any frontend files.
Show me the files before and after.
```

---

## PART 6: Key Insights from This Session (Product Strategy)

### The Compounding Cycle

The central insight that emerged during positioning work: the moat is not "we have learning loops." It's a four-part cycle where each step feeds the next:

1. **Accumulate** — Semantics compound in the living graph. UCL entity-resolves across domains. Connected meaning, not flat facts.
2. **Adjust** — AgentEvolver rewrites operational DNA (routing, scoring, context policies) from verified outcomes. The implementation itself evolves. LLM stays frozen.
3. **Respond** — Situation Analyzer reads the SAME alert differently as the graph evolves. Not a new rule — a different situation reading from enriched context.
4. **Discover** — Cross-domain sweeps find semi-related signals and create NEW evaluation criteria. Discoveries feed the next sweep. Recursive.

This cycle maps to the demo: Accumulate (UCL + connectors), Adjust (AgentEvolver + TRIGGERED_EVOLUTION), Respond (Situation Analyzer in Tab 3), Discover (cross-graph sweep in v4.5).

### Nine Value Features (F1-F9)

| ID | Feature | Version | Priority |
|---|---|---|---|
| F1 | MITRE ATT&CK alignment | v4.0 Phase 1 | Tier 1 |
| F2 | Realistic alert corpus | v4.0 Phase 1 | Tier 1 |
| F3 | Investigation narrative | v4.0 Phase 5 | Tier 1 |
| F4 | Compounding proof panel | v4.0 Phase 5 | Tier 1 |
| F5 | Cross-domain discovery | v4.5 | Tier 2 |
| F6 | Trust curve + asymmetric trace | v4.0 Phase 5 | Tier 2 |
| F7 | ATT&CK coverage heatmap | v5.0 | Tier 3 |
| F8 | Shift handoff intelligence | v5.0 | Tier 3 |
| F9 | Multi-domain compounding proof | v5.0+ | Tier 3 |

### Competitive Positioning Summary

| Competitor | What They Do | What They Don't |
|---|---|---|
| Torq ($1.2B) | 200+ connectors, multi-agent workflows | No learning. Day 1,000 = Day 1 |
| Dropzone AI | Context Memory — accumulates facts | Facts in, facts out. Same reasoning. LLM-dependent |
| Intezer | Deep forensic investigation | No feedback loop. Static |
| CrowdStrike Charlotte | Deep per-alert reasoning in Falcon | Locked ecosystem. No cross-alert learning |
| **Us** | **Compounding cycle. Firm-specific graph. Model-independent** | **Market awareness. Scale. Funding.** |

---

## PART 7: Version History

| Version | Date | Changes |
|---|---|---|
| 1.0–9.0 | Feb 10–25 | Initial through v3.1.1 completion |
| 10.0 | Feb 26 | v3.2 complete. Sequential v4.0 → v4.5 design. Docs cleanup plan. |
| **11.0** | **Feb 26** | **Product strategy + competitive positioning completed. Roadmap v4 with value features. Deployment strategy v3 with VPS hosting. Design docs updated (v4→v3, v4.5→v5). Nine NBP positioning graphics created (POS-00A/B/C through POS-06). Compounding cycle articulated (accumulate→adjust→respond→discover). v4.0 scope: 36 prompts (33 code + 3 VPS). v4.5 scope: 19 prompts.** |

---

*SOC Copilot Demo — Session Continuation Package v11 | February 26, 2026*
*v3.2 shipped. Product strategy complete. Sequential v4.0 (36 prompts) → v4.5 (19 prompts). Nine positioning graphics ready.*
