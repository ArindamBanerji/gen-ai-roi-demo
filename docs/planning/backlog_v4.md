# SOC Copilot Demo — Backlog v4

**Date:** February 19, 2026
**Status:** v2.5 Complete and Tagged (10/18 ACCP). Experimental validation complete. Focus shifts to Docker + Blog Publishing + Loom + v3.0 design.
**Environment:** Windows 11, Python 3.11, Node 20, Docker Desktop
**Repos:**
- Demo: git@github.com:ArindamBanerji/gen-ai-roi-demo.git (main, v2.5 tag)
- Experiments: git@github.com:ArindamBanerji/cross-graph-experiments.git (main, v1.0 tag)
**Branch:** main (v2.5 tagged at commit e63bc85)

---

## SECTION A: Completed Work

### v2.0 (Tagged)

| Capability | ACCP Primitive | Status |
|---|---|---|
| Context graph (Neo4j) | Context substrate | Done |
| Situation Analyzer (6 types) | Situational Mesh | Done |
| Eval gates (4-check + BLOCKED) | Eval Gates | Done |
| TRIGGERED_EVOLUTION | TRIGGERED_EVOLUTION | Done |
| Decision economics (time/cost/risk) | Decision Economics | Done |
| AgentEvolver (prompt variant tracking) | AgentEvolver | Done |
| Business impact banner + Two-Loop Hero | Visualization | Done |

### v2.5 (Tagged at e63bc85)

| Prompt | Feature | Commit | Status |
|---|---|---|---|
| 7A | ROI Calculator backend | 8862519 | Done |
| 7B | ROI Calculator frontend modal | ee05f20 | Done |
| 7C | ROI Calculator Tab 4 integration | 42d2ca8 | Done |
| 8A | Outcome Feedback backend | cd44ddc | Done |
| 8B | Outcome Feedback frontend (Tab 3) | f8240f8 | Done |
| 9A | Policy Conflict backend (service + wiring) | 865000a | Done |
| 9B | Policy Conflict frontend (Tab 3) | e63bc85 | Done |
| fix | Stale closure bug in auto-select guard | 90438cd | Done |

**Bug fixes applied during v2.5:**
- ROI escalation formula: fixed $2.187M → $145.8K (was 70% of total, now 13%)
- ROI payback/ROI: now varies by SOC size (was constant 5 weeks / 10x)
- Stale closure: useRef pattern replaces useState for preserveFeedbackRef
- Typo: "anomalys" → "similar alerts of this type"
- Pydantic: .dict() → .model_dump(), outcome field → Literal type
- Hardcoded timestamp → datetime.now().isoformat()

### Pre-Work (All Done)

Tasks 0-8, Decisions 1-3, PR merge, tag v2.0 — all complete. See backlog v2 for details.

### Experimental Validation (Complete — Feb 19, 2026)

| Item | Status | Output |
|---|---|---|
| Experiment 1: Scoring convergence (5000 alerts) | Done | 69.4% accuracy, 3 failure modes identified |
| Experiment 2: Cross-graph discovery (2 domains) | Done | F1=0.293 (110× above random) |
| Experiment 3: Multi-domain scaling (2-8 domains) | Done | D(n) ∝ n^2.30, R²=0.9995 |
| Experiment 4: Sensitivity analysis (grid search) | Done | Phase transition at σ=0.3-0.5 |
| 6 publication-quality charts (PDF + PNG) | Done | In cross-graph-experiments repo |
| Git repo pushed | Done | github.com/ArindamBanerji/cross-graph-experiments, v1.0 tag |

### Content & Outreach Updates (Complete — Feb 19, 2026)

| Item | Version | Status |
|---|---|---|
| Math blog addendum (arXiv conversion) | v1 | Done — 6 new sections, ~4500 words, ready to paste into Wix |
| CI blog addendum (competitive + evidence) | v1 | Done — 4 sections + 8 graphics, ready to paste into Wix |
| 3 NBP graphics (EXP1-HEATMAP, CI-FAILUREMODES, CI-WIDENINGGAP) | v1 | Done — prompt + JSON ready for Napkin.ai |
| LinkedIn posts | v3 | Done — all 3 posts updated with experimental evidence |
| Outreach emails | v3 | Done — both emails updated with validation results |
| Demo blurb | v2.5.1 | Done — new "Validated by Experiment" section |
| Competitive posture | v1 | Done — INTERNAL only, not for public blog |

---

## SECTION B: Active Backlog — Docker + Outreach

### B1. Docker for Partners [Distribution]

**Priority: P0** — Enables partner self-service demos without dev environment setup.
**Design:** See backlog v2, Section C for full specs.

| Prompt | Scope | Status |
|---|---|---|
| D1 | Dockerfile.backend (FastAPI + dependencies) | Not started |
| D2 | Dockerfile.frontend (Vite build + nginx) | Not started |
| D3 | docker-compose.yml + .env.docker + neo4j seed script | Not started |
| D4 | PARTNER_README.md + health check verification | Not started |

**Partner experience target:**
```
1. Install Docker Desktop
2. Clone the repo (or download ZIP)
3. Run: docker-compose up
4. Wait ~60 seconds for Neo4j to seed
5. Open http://localhost:5174
```

### B2. Loom v2 Script + Recording [Outreach]

**Priority: P1** — Updated demo walkthrough covering v2.5 features.

| Section | Duration | v2.5 Additions |
|---|---|---|
| Opening: "Your SOC has amnesia" | 45 sec | Same |
| Tab 2: Runtime Evolution | 3-4 min | AgentEvolver, $4,800/mo, BLOCKED demo |
| Tab 3: Alert Triage | 4-5 min | **Situation Analyzer, Decision Economics, Policy Conflict, Outcome Feedback** |
| Tab 4: Compounding Dashboard | 2-3 min | **ROI Calculator walkthrough** |
| Close: Architecture recap | 1 min | ACCP progress (10/18) |

**Total: ~12 minutes**

### B3. Short Loom (3 min) [Outreach]

**Priority: P2** — For LinkedIn, email follow-ups, busy CISOs.
1. 30 sec: "Your SOC has amnesia" hook
2. 60 sec: Tab 3 — Situation Analyzer + Decision Economics (the "aha")
3. 45 sec: Tab 2 — AgentEvolver ($4,800/mo, 0 missed threats)
4. 30 sec: Tab 4 — Business Impact Banner + ROI Calculator
5. 15 sec: Close — "Same model. Same code. Smarter graph."

### B4. Outreach Content [Content]

| Item | Status | Notes |
|---|---|---|
| Outreach emails v3 (compounding + math) | **Done** | Updated with experimental validation (69.4%, 110×, n^2.30) |
| Demo blurb v2.5.1 (CISO/VC audience) | **Done** | New "Validated by Experiment" section, 18 screenshot/chart markers |
| LinkedIn posts v3 (3 posts) | **Done** | Post 3 substantially rewritten for experimental results |
| Math blog addendum (arXiv conversion) | **Done — needs Wix paste** | 6 sections, ~4500 words added |
| CI blog addendum (competitive + evidence) | **Done — needs Wix paste** | 4 sections, 8 graphics |
| NBP graphics (3 new) | **Done — needs Napkin.ai generation** | EXP1-HEATMAP, CI-FAILUREMODES, CI-WIDENINGGAP |
| Blog: SOC Copilot Demo page | TODO | Add v2.5 screenshots, update feature list |

---

## SECTION C: Future Backlog — v3.0

### C1. Prompt Hub / Smart Queries [ACCP: Typed-Intent Early]

**Moved from v2.5.** Lower CISO impact than Feedback and Policy Conflict.

| Prompt | Scope | Status |
|---|---|---|
| 10A | Backend: Fuzzy matching + suggestion engine | Not started |
| 10B | Frontend: "Did you mean?" suggestions in Tab 1 | Not started |

### C2. Live Graph Integration [Critical for Credibility]

**NEW for v3.0.** "De-fake" the backend — replace in-memory state with Neo4j reads/writes.

| Prompt | Scope | Status |
|---|---|---|
| 11A | Migrate feedback state to Neo4j | Not started |
| 11B | Migrate policy evaluation to Neo4j | Not started |
| 11C | Link feedback outcomes to decision nodes | Not started |

### C3. External Context Ingestion [ACCP: CONSUME]

| Prompt | Scope | Status |
|---|---|---|
| 12A | Threat intel feed simulation | Not started |
| 12B | Graph freshness indicators | Not started |
| 12C | Source reliability scoring | Not started |

### C4. Evidence Ledger [ACCP: Compliance]

| Prompt | Scope | Status |
|---|---|---|
| 13A | Decision audit export (PDF/CSV) | Not started |
| 13B | Tamper-evident decision chain | Not started |
| 13C | Quarterly report generation | Not started |

### C5. Process Intelligence [ACCP: Enriched Mesh]

| Prompt | Scope | Status |
|---|---|---|
| 14A | Process variant extraction | Not started |
| 14B | Bottleneck detection + visualization | Not started |

---

## SECTION D: Documentation Updates

| Document | Update Needed | Status |
|---|---|---|
| CLAUDE.md | Add v2.5 features, ACCP capability map | TODO |
| PROJECT_STRUCTURE.md | Add new files from v2.5 | TODO |
| README.md | Add v2.5 features | TODO |
| V2_IMPLEMENTATION_PLAN.md | Mark v2.5 complete | TODO |
| Design document | Updated to v3 this session | **Done** |
| Backlog | Updated to v3 this session | **Done** |
| Session continuation package | Updated to v4 this session | **Done** |

---

## SECTION E: Master Priority Queue

| Priority | Item | Section | Effort | ACCP Impact |
|---|---|---|---|---|
| **P0** | Docker for Partners | B1 | 4 prompts (1 session) | Distribution |
| **P0** | Publish blog addenda to Wix + generate 3 NBP graphics | B4 | 1-2 hours manual | Credibility |
| **P1** | Loom v2 Script + Recording | B2 | 1 session | Outreach |
| **P2** | Short Loom (3 min) | B3 | After B2 | Outreach |
| **P2** | Post LinkedIn v3 content | B4 | 30 min manual | Outreach |
| **P2** | Doc updates (CLAUDE.md etc.) | D | 1 session | Maintenance |
| **P2** | Prompt Hub | C1 | 2 prompts | Typed-Intent early |
| **P3** | Live Graph Integration | C2 | 3 prompts | Credibility |
| **P3** | External Context Ingestion | C3 | 3 prompts | CONSUME |
| **P3** | Evidence Ledger | C4 | 3 prompts | Compliance |
| **P3** | Process Intelligence | C5 | 2 prompts | Situational Mesh |

### Recommended Session Order

```
Session 1: Docker for Partners (B1: Prompts D1-D4)
  -> Enables partner self-service, unblocks outreach

Parallel (manual): Publish blog addenda + generate NBP graphics
  -> Math addendum → Wix paste → publish
  -> CI addendum → Wix paste → publish
  -> 3 NBP graphics → Napkin.ai → download → insert into blogs
  -> Post LinkedIn v3 content

Session 2: Loom v2 Script + Recording (B2)
  -> Needs v2.5 features complete (they are)
  -> Write script, record, edit

Session 3: Doc Updates + Blog (B4, D)
  -> CLAUDE.md, PROJECT_STRUCTURE.md, README.md
  -> Blog screenshots and content updates

Session 4: Prompt Hub (C1: Prompts 10A, 10B)
  -> First v3.0 feature, improves Tab 1 usability

Session 5: Live Graph Integration (C2: Prompts 11A-11C)
  -> "De-fakes" the backend, critical for 30-min deep dives
  -> Tag v3.0 after this session
```

---

## SECTION F: Git History Reference

```
e63bc85 (HEAD -> main, tag: v2.5) feat: Policy Conflict frontend panel in Tab 3 (v2.5, Prompt 9B)
90438cd fix: stale closure bug in Outcome Feedback auto-select guard
f8240f8 feat: Outcome Feedback frontend panel in Tab 3 (v2.5, Prompt 8B)
865000a feat: Policy Conflict Resolution backend (v2.5, Prompt 9A)
cd44ddc feat: Outcome Feedback Loop backend (v2.5, Prompt 8A)
42d2ca8 feat: integrate ROI Calculator into Tab 4 (v2.5, Prompt 7C)
ee05f20 feat: ROI Calculator frontend modal (v2.5, Prompt 7B)
8862519 feat: ROI Calculator backend (v2.5, Prompt 7A)
1c3dde8 chore: add .claude/ to gitignore
984e3b1 docs: add ACCP-integrated design doc v2 + backlog v2
```

---

## SECTION G: Version History

| Version | Date | Changes |
|---|---|---|
| 1.0 | Feb 10, 2026 | Initial backlog (pre-work tasks) |
| 2.0 | Feb 18, 2026 | Added v2.5 build items, Docker, Loom, ACCP tags |
| 3.0 | Feb 18, 2026 | v2.5 complete. Updated all statuses. Moved Prompt Hub to v3.0. Added v3.0 items. Updated priority queue. Added git history. |
| 4.0 | Feb 19, 2026 | Added experimental validation (4 experiments, repo pushed). Added content updates (LinkedIn v3, emails v3, blurb v2.5.1, blog addenda, NBP graphics). Updated priority queue with blog publishing as P0. Added cross-graph-experiments repo link. |

---

*SOC Copilot Demo — Backlog v4.0 | February 19, 2026*
*Next action: Docker for Partners (D1-D4) + Publish blog addenda (manual)*
