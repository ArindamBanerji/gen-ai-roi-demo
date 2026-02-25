# LLM Judge: Loom Script v7 Review

## Purpose
Use a fresh Claude conversation (no project context) or GPT-4o as an independent judge. Copy the full loom_script_v7.md and this prompt.

---

## Prompt for the LLM Judge

```
You are a senior B2B SaaS marketing consultant who has reviewed hundreds of product demo scripts. You specialize in enterprise security products sold to CISOs and VCs.

I'm sharing a 15-minute Loom demo script for an AI-powered SOC (Security Operations Center) copilot. The product demonstrates "compounding intelligence" — an AI system that gets smarter over time through three learning loops feeding a knowledge graph.

The demo is aimed at:
- CISOs who are evaluating AI SOC solutions and care about transparency, audit trails, and integration with their existing stack (CrowdStrike, Pulsedive, etc.)
- VCs who are evaluating the platform thesis and moat durability
- Cold audience — no prior exposure to the product or concepts like "ACCP" or "context graphs"

Review the script on these dimensions:

### 1. COLD AUDIENCE ACCESSIBILITY
- Will someone with NO prior exposure understand the concepts as introduced?
- Are there jargon terms that need definition on first use? (e.g., "ACCP", "UCL", "eval gates", "context graph", "TRIGGERED_EVOLUTION")
- Is the progression from simple → complex well-paced?
- Would a CISO lose interest at any point? Where and why?

### 2. NARRATIVE ARC
- Does the demo tell a story, or is it a feature tour?
- Is there a clear problem → solution → proof → business case flow?
- Does the emotional peak land at the right moment?
- Is the close compelling? Would you send the calendar link?

### 3. TIMING & PACING
- 15:30 is long for a cold Loom. Is every minute justified?
- What would you cut to get to 12 minutes?
- Are there sections that drag or repeat?
- Is the Tab 1 opener (2.5 min) worth the time investment?

### 4. CREDIBILITY & CLAIMS
- Are any claims unsupported by what's visible on screen?
- Does the script oversell or undersell?
- "Running code, not a pitch deck" — does the script deliver on this promise?
- Are the ROI numbers believable? Too precise? Too round?

### 5. COMPETITIVE POSITIONING
- Is "CrowdStrike detects. Pulsedive enriches. We decide." clear positioning?
- Does the script adequately address the "why not just use [existing tool]" objection?
- Is the moat argument convincing for VCs?

### 6. KEY LINES
- Which of the 16 "key lines to nail" are genuinely memorable?
- Which are forgettable or generic?
- Suggest 3 replacement lines for the weakest ones.

### 7. DEMO RESILIENCE
- What happens if something goes wrong during recording?
- Are there graceful degradation points in the script?
- What if the threat intel shows "Local fallback" instead of "Pulsedive (live)"?

### 8. TOP 5 IMPROVEMENTS
Rank your top 5 suggested improvements by impact.

[PASTE FULL loom_script_v7.md HERE]
```

---

# Code Review Plan v31 — Updated for v3.1.1 Codebase

## Changes from v25

The codebase has grown significantly since v2.5:
- v2.5: ~8,700 lines across 24 files
- v3.1.1: ~12,000+ lines across 30+ files
- New backend services: services/triage.py (283 lines), services/audit.py (~200 lines)
- New backend routers: routers/audit.py (~100 lines)
- Modified routers: triage.py grew from ~300 to ~753 lines, soc.py grew to ~636 lines
- Modified frontend: AlertTriageTab.tsx grew to ~1,039 lines, SOCAnalyticsTab.tsx to ~626 lines
- New frontend features: Threat Landscape panel, Decision Explainer, Evidence Ledger, cross-context queries
- Seed data: seed_neo4j.py expanded (6 alerts, 7 users, 6 pattern mappings)

## Updated File Review Order

### Tier 1: Core Demo Path (Review First)

| # | File | Lines | Why Critical | New in v3? |
|---|---|---|---|---|
| 1 | backend/app/routers/triage.py | ~753 | Largest router. Handles Tab 3 + feedback + policy + decision factors + execution with audit recording | Heavily modified |
| 2 | frontend/src/components/tabs/AlertTriageTab.tsx | ~1039 | Most complex component. Decision Explainer, Threat Intel badge, Policy Override, Outcome Feedback | Heavily modified |
| 3 | backend/app/services/triage.py | ~283 | Decision factor breakdown. Live Neo4j query for threat intel factor | **NEW** |
| 4 | backend/app/services/audit.py | ~200 | Hash chain integrity. In-memory _DECISIONS list. reconstruct_from_memory() | **NEW** |
| 5 | backend/app/routers/soc.py | ~636 | Tab 1: 4 new metrics + threat landscape endpoint with Neo4j fallback | Heavily modified |
| 6 | frontend/src/components/tabs/SOCAnalyticsTab.tsx | ~626 | Threat Landscape panel, table rendering, cross-context separator | Heavily modified |
| 7 | backend/app/services/feedback.py | ~280 | Outcome feedback. 20:1 asymmetry math. State reset | Unchanged |
| 8 | backend/app/services/policy.py | ~440 | Policy conflict detection | Unchanged |
| 9 | frontend/src/lib/api.ts | ~210 | All API calls including new endpoints | Modified |
| 10 | backend/app/services/agent.py | ~200 | Core decision engine | Unchanged |

### Tier 2: Supporting Demo Path

| # | File | Lines | Why | New? |
|---|---|---|---|---|
| 11 | backend/app/routers/audit.py | ~100 | Evidence Ledger endpoints, CSV export, chain verification | **NEW** |
| 12 | backend/app/services/threat_intel.py | ~150 | Pulsedive API with rate limiting and fallback | **NEW** |
| 13 | backend/app/routers/graph.py | ~100 | Threat intel refresh endpoint | **NEW** |
| 14 | backend/app/services/seed_neo4j.py | ~300+ | Alert/user/pattern seed data. Recently fixed. | Modified |
| 15 | frontend/src/components/tabs/CompoundingTab.tsx | ~400+ | Evidence Ledger, Three-Loop Hero, reset handling | Modified |
| 16 | frontend/src/components/tabs/RuntimeEvolutionTab.tsx | ~300+ | Loop 3 panel | Modified |
| 17 | backend/app/routers/roi.py | ~280 | ROI Calculator | Unchanged |
| 18 | frontend/src/components/ROICalculator.tsx | ~590 | Slider state management | Unchanged |

### Tier 3: Infrastructure

| # | File | Lines | Why |
|---|---|---|---|
| 19 | backend/app/main.py | ~70 | Router registration, CORS, dotenv fix |
| 20 | backend/app/models/schemas.py | ~100 | Pydantic models |
| 21 | backend/app/db/neo4j.py | ~80 | Neo4j connection |
| 22 | frontend/vite.config.ts | ~25 | Proxy config (recently fixed) |

## New Review Questions (v3.1 Specific)

**services/triage.py:** Does get_decision_factors() handle all alert types? What happens with an unknown alert? Does the Neo4j query for threat_intel_enrichment handle connection failures gracefully?

**services/audit.py:** Is the SHA-256 hash chain computation correct? Can records be added out of order? What happens if record_outcome() is called before record_decision()? Is reconstruct_from_memory() idempotent?

**routers/triage.py:** Does execute_action() correctly call record_decision() for ALL execution paths (both "Apply Recommendation" and "Apply Policy Resolution")? Does the decision factors endpoint return 404 for unanalyzed alerts?

**soc.py (threat-landscape):** Does the Neo4j fallback activate cleanly? Are all hardcoded values reasonable for a demo? Does the endpoint handle Neo4j timeout?

**seed_neo4j.py:** Are all 6 alerts correctly wired to users and patterns? Is the seed idempotent (MERGE not CREATE)?

**AlertTriageTab.tsx:** Does the Decision Explainer render correctly for all alert types, not just ALERT-7823? What happens with rapid alert switching while decision factors are loading? Does the reset flow correctly clear all panel state?

**SOCAnalyticsTab.tsx:** Does the Threat Landscape panel handle API failure gracefully (hidden, not broken)? Do table-type metrics render correctly for all 4 new queries?

**CompoundingTab.tsx:** Does "Reset All Demo Data" correctly reset BOTH Neo4j AND in-memory state? Does the Evidence Ledger refresh show records from the current session?

## Pass 2: Architecture Review — New Checks

| Check | What to Look For | Files |
|---|---|---|
| **Audit chain integrity** | Is the hash chain continuous? Can concurrent writes break it? | audit.py |
| **Decision factor consistency** | Do the 6 factors in triage.py match what the frontend renders? | services/triage.py, AlertTriageTab.tsx |
| **Threat intel data flow** | Does the Pulsedive fallback → Neo4j write → decision factor query chain work end-to-end? | threat_intel.py, graph.py, triage.py |
| **Reset completeness** | Does reset-all clear: Neo4j, feedback state, policy state, audit _DECISIONS, frontend? | metrics.py, triage.py, feedback.py, policy.py, audit.py, CompoundingTab.tsx, AlertTriageTab.tsx |
| **Port consistency** | Is 8000 used everywhere? No leftover 8001 references? | vite.config.ts, all docs, CLAUDE.md |

## Pass 3: Demo Resilience — New Scenarios

| Scenario | Expected Behavior | Risk |
|---|---|---|
| Pulsedive rate limited (429) | Badge shows "Local fallback" (amber). Factors still calculate. | Low — tested |
| Execute alert then immediately switch tabs | Evidence Ledger should show record on Tab 4 refresh | Medium — async timing |
| Reset All Demo Data then immediate Tab 3 | Should show 6 alerts, first auto-selected | Medium — recently fixed |
| Click all 4 cross-context queries rapidly | Each should render correctly, replace previous | Low |
| Neo4j connection drops mid-demo | All endpoints should fall back to static data | Medium |
| Threat Landscape panel fails to load | Tab 1 should still show query input and examples | Low — implemented |

## Timeline

| Step | Effort | When |
|---|---|---|
| Run Pass 1: File-by-file (30 files) | 3-4 hours | Before v4 build |
| Run Pass 2: Architecture review | 1-2 hours | Same session |
| Run Pass 3: Demo resilience + manual testing | 1-2 hours | Same or next session |
| Triage findings | 1 hour | After automated passes |
| Fix critical + high | 1-2 sessions | Before v4 build |

**Recommendation:** Run the review BEFORE v4 build. The codebase grew 40% in v3. Better to fix foundation issues before adding connectors and Docker.

---

*Code Review Plan v31 | February 24, 2026*
*Updated for v3.1.1 codebase. 30+ files, ~12K lines. New services: triage.py, audit.py, threat_intel.py.*
