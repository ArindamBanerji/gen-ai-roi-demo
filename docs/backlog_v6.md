# SOC Copilot Demo — Backlog v6

**Date:** February 24, 2026
**Status:** v2.5.1 tagged (B1 fix). Design doc v7.0 finalized. v3.0 build ready.
**Environment:** Windows 11, Python 3.11, Node 20, Docker Desktop
**Repos:**
- Demo: git@github.com:ArindamBanerji/gen-ai-roi-demo.git (main, v2.5.1)
- Experiments: git@github.com:ArindamBanerji/cross-graph-experiments.git (main, v1.0 tag)
**Branch:** main (v2.5 at e63bc85, v2.5.1 at B1 fix). Next: `feature/v3.0-enhancements` off main.

---

## SECTION A: Completed Work

### v2.0 (Tagged)

| Capability | ACCP Primitive | Status |
|---|---|---|
| Context graph (Neo4j) | Context substrate | ✅ Done |
| Situation Analyzer (6 types) | Situational Mesh | ✅ Done |
| Eval gates (4-check + BLOCKED) | Eval Gates | ✅ Done |
| TRIGGERED_EVOLUTION | TRIGGERED_EVOLUTION | ✅ Done |
| Decision economics (time/cost/risk) | Decision Economics | ✅ Done |
| Loop 1: Situation Analyzer | Situational Mesh | ✅ Done |
| Loop 2: AgentEvolver (prompt variant tracking) | AgentEvolver | ✅ Done |
| Business impact banner + Two-Loop Hero | Visualization | ✅ Done |

### v2.5 (Tagged at e63bc85)

| Prompt | Feature | Commit | Status |
|---|---|---|---|
| 7A | ROI Calculator backend | 8862519 | ✅ Done |
| 7B | ROI Calculator frontend modal | ee05f20 | ✅ Done |
| 7C | ROI Calculator Tab 4 integration | 42d2ca8 | ✅ Done |
| 8A | Outcome Feedback backend | cd44ddc | ✅ Done |
| 8B | Outcome Feedback frontend (Tab 3) | f8240f8 | ✅ Done |
| 9A | Policy Conflict backend | 865000a | ✅ Done |
| 9B | Policy Conflict frontend (Tab 3) | e63bc85 | ✅ Done |
| fix | Stale closure bug in auto-select guard | 90438cd | ✅ Done |

### v2.5.1 (B1 Fix)

| Prompt | Feature | Status |
|---|---|---|
| B1 | Floating point display fix (.toFixed(1) on confidence scores) | ✅ Done — committed, tagged v2.5.1 |

### Experimental Validation (Complete — Feb 19, 2026)

| Item | Status | Key Result |
|---|---|---|
| Exp 1: Scoring matrix convergence (5,000 alerts, 10 seeds) | ✅ Done | 69.4% accuracy; 3 failure modes; optimal asymmetry = 20× |
| Exp 2: Cross-graph discovery (3 domain pairs) | ✅ Done | F1=0.293, 110× above random; normalization = 4× prerequisite |
| Exp 3: Multi-domain scaling (2–6 domains) | ✅ Done | D(n) ∝ n^2.30, R²=0.9995 |
| Exp 4: Sensitivity analysis (4 sweeps) | ✅ Done | Phase transition at noise_rate ≈ 0.05; dim 256 collapses to F1=0 |

### Content & Outreach (Complete through Feb 24)

| Item | Version | Status |
|---|---|---|
| Design document | v7.0 | ✅ Done — v3.0 scoped to 10 prompts, blog cross-audit complete |
| CI blog v4.0 | — | ✅ Live (needs 5×→20× fix) |
| Math blog | — | ✅ Live (needs 5×→20× fix) |
| Blurb blog | — | ✅ Live (needs Wix cleanup) |
| LinkedIn posts | v4 | ✅ Written — needs LinkedIn-native rewrites (8-10 of 16) |
| Outreach emails | v4 | ✅ Done — three loops, Loop 3 described |
| Blog asymmetry fixes guide | v1 | ✅ Done — blog_asymmetry_fixes.md |
| Loom v1 script | v5 | ✅ Done — reviewed, ready for v2 rewrite after v3.0 |

---

## SECTION B: Active Backlog — v3.0 Build

**Theme:** "Three loops. Auditable. Connected."
**Design spec:** v3_design_document_v7.md
**Branch:** feature/v3.0-enhancements off main

### B1. Session 1: Loop 3 — RL Reward/Penalty [CRITICAL — closes blog gap]

| Prompt | Scope | Files | Status |
|---|---|---|---|
| A1 | GET /api/rl/reward-summary endpoint | feedback.py (add fn), triage.py (add endpoint) | Not started |
| A2 | Loop 3 panel in Tab 2 | RuntimeEvolutionTab.tsx, api.ts | Not started |
| A3 | Three-Loop Hero + Four Layers strip in Tab 4 | CompoundingTab.tsx | Not started |

**Tag after:** `v3.0-loop3`

### B2. Session 2: Bug Fixes

| Prompt | Scope | Files | Status |
|---|---|---|---|
| B2 | Policy override of Recommendation panel | AlertTriageTab.tsx only | Not started |
| B3 | Remove ROI button pulse animation | CompoundingTab.tsx only | Not started |

### B3. Session 3: Threat Intel Feed

| Prompt | Scope | Files | Status |
|---|---|---|---|
| EC1a | Backend: threat intel refresh endpoint | threat_intel.py (new), graph.py (new), main.py | Not started |
| EC1b | Frontend: threat intel badge in Tab 3 | AlertTriageTab.tsx, api.ts | Not started |

### B4. Session 4: Evidence Ledger

| Prompt | Scope | Files | Status |
|---|---|---|---|
| EL1 | Decision audit service + JSON/CSV export | services/audit.py (new), routers/audit.py (new), main.py | Not started |
| EL2 | Tamper-evident SHA-256 hash chain | services/audit.py, routers/audit.py | Not started |
| EL3 | Evidence Ledger panel in Tab 4 | CompoundingTab.tsx, api.ts | Not started |

**Tag after Session 4:** `v3.0`

---

## SECTION C: Parallel Tasks (Manual, No Claude Code)

| Item | Priority | Status | Notes |
|---|---|---|---|
| Blog 5×→20× fix (both blogs) | **P1** | ❌ Pending | 4 searches per blog: `5:1`, `5×`, `λ_neg = 5`, `five correct`. Fix before Loom v2. |
| Advert cleanup (5 placeholders, 3 links, VC label) | **P1** | ❌ Pending | 15 min in Wix. Fix before next outreach send. |
| Upload CI blog graphics #21, #24, #34, #35, #36 | P2 | ❌ Pending | Files exist — upload to Wix manually |
| Fix CI blog graphic #22 (5≤ encoding) | P2 | ❌ Pending | Regenerate via NBP, then upload |
| LinkedIn posts — rewrite 8-10 for LinkedIn mechanics | P2 | ❌ Pending | See linkedin_posts_v4.md assessment |
| Post LinkedIn Series A + B | P2 | ❌ Pending | After rewrites |
| Update demo blog with v2.5 screenshots | P3 | ❌ Pending | After v3.0 ships (will need v3.0 screenshots anyway) |

---

## SECTION D: Future Backlog — v4.0

**Theme:** "Partner-ready. Production-credible."

### D1. Docker for Partners (5 prompts)

| Prompt | Scope | Status |
|---|---|---|
| D1 | Dockerfile.backend | Not started |
| D2 | Dockerfile.frontend | Not started |
| D3 | docker-compose.yml + .env.docker | Not started |
| D4 | Neo4j seed script | Not started |
| D5 | PARTNER_README.md + health check endpoint | Not started |

### D2. Live Graph Integration (4 prompts)

| Prompt | Scope | Status |
|---|---|---|
| LG1 | feedback.py: read/write :Pattern confidence to Neo4j | Not started |
| LG2 | feedback.py: write :DecisionTrace relationships | Not started |
| LG3 | policy.py: read :Policy nodes, write :PolicyResolution | Not started |
| LG4 | triage.py: create :ProcessedAlert, link to :Pattern/:User | Not started |

### D3. Prompt Hub / Smart Queries (2 prompts)

| Prompt | Scope | Status |
|---|---|---|
| PH1 | Backend: query registry + fuzzy matching | Not started |
| PH2 | Frontend: "Did you mean?" in Tab 1 | Not started |

### D4. Process Intelligence (2 prompts)

| Prompt | Scope | Status |
|---|---|---|
| PI1 | Process variant extraction from :DecisionTrace | Not started |
| PI2 | Bottleneck detection + Tab 3 panel | Not started |

### D5. Loom v2 Script + Recording

| Item | Status |
|---|---|
| Write v2 script (covers three loops, Evidence Ledger, Threat Intel) | Not started — after v3.0 + blog fixes |
| Record Loom v2 (12 min + 3 min LinkedIn short) | Not started |

### D6. Documentation Updates (In-Repo)

| Document | Update Needed | Status |
|---|---|---|
| CLAUDE.md | Three loops, v3.0 features, ACCP 13/20 | ❌ After v3.0 |
| PROJECT_STRUCTURE.md | New files from v3.0 | ❌ After v3.0 |
| README.md | Three loops, v3.0 features | ❌ After v3.0 |

---

## SECTION E: Master Priority Queue

| Priority | Item | Section | Prompts | Blocking What |
|---|---|---|---|---|
| **P0** | Loop 3 (RL Reward/Penalty) | B1 | 3 | Demo-blog alignment |
| **P0** | Bug fixes (policy override, pulse) | B2 | 2 | Demo visual credibility |
| **P0** | Threat Intel feed | B3 | 2 | "Living graph" claim |
| **P0** | Evidence Ledger | B4 | 3 | CISO compliance story |
| **P1** | Blog 5×→20× fix | C | Manual | Blog-demo consistency |
| **P1** | Advert Wix cleanup | C | Manual | Outreach credibility |
| **P1** | Upload pending CI blog graphics | C | Manual | Blog completeness |
| **P2** | LinkedIn post rewrites | C | Manual | Lead generation |
| **P2** | Docker for Partners | D1 | 5 | Partner self-service |
| **P2** | Live Graph Integration | D2 | 4 | 30-min demo credibility |
| **P2** | Loom v2 | D5 | 1 session | Outreach |
| **P3** | Prompt Hub | D3 | 2 | Exec UX |
| **P3** | Process Intelligence | D4 | 2 | Cross-domain story |
| **P3** | In-repo doc updates | D6 | 1 session | Maintainability |

---

## SECTION F: Build Sequence

```
v3.0 BUILD (branch: feature/v3.0-enhancements):

  SESSION 1: Loop 3 → A1, A2, A3 → tag v3.0-loop3
  SESSION 2: Bug Fixes → B2, B3 → commit
  SESSION 3: Threat Intel → EC1a, EC1b → commit
  SESSION 4: Evidence Ledger → EL1, EL2, EL3 → commit

  MERGE: git merge feature/v3.0-enhancements → tag v3.0

PARALLEL (anytime):
  Blog 5×→20× fix (before Loom v2)
  Advert Wix cleanup
  Upload CI blog graphics
  LinkedIn post rewrites

AFTER v3.0:
  Loom v2 script → record → post
  v4.0 planning (Docker + Live Graph + Prompt Hub + Process Intel)
```

---

## SECTION G: Git History Reference

```
[v2.5.1] fix: round confidence scores to 1 decimal in OutcomeFeedback display (B1)
e63bc85 (tag: v2.5) feat: Policy Conflict frontend panel in Tab 3 (v2.5, 9B)
90438cd fix: stale closure bug in Outcome Feedback auto-select guard
f8240f8 feat: Outcome Feedback frontend panel in Tab 3 (v2.5, 8B)
865000a feat: Policy Conflict Resolution backend (v2.5, 9A)
cd44ddc feat: Outcome Feedback Loop backend (v2.5, 8A)
42d2ca8 feat: integrate ROI Calculator into Tab 4 (v2.5, 7C)
ee05f20 feat: ROI Calculator frontend modal (v2.5, 7B)
8862519 feat: ROI Calculator backend (v2.5, 7A)
1c3dde8 chore: add .claude/ to gitignore
984e3b1 docs: add ACCP-integrated design doc v2 + backlog v2
```

---

## SECTION H: Version History

| Version | Date | Changes |
|---|---|---|
| 1.0–4.0 | Feb 10–19 | Initial through experimental validation and content v3 |
| 5.0 | Feb 21 | Three-loop architecture. Loop 3 as P0. Docker 5 prompts. LinkedIn/emails v4. |
| **6.0** | **Feb 24** | **v3.0 scoped to 10 prompts (from 22). Deferred Docker/LiveGraph/PromptHub/ProcessIntel to v4. Promoted Evidence Ledger to v3. B1 done. Blog 5×→20× tracked as P1. Session openers updated for 4-session v3 build. Superseded doc list updated.** |

---

*SOC Copilot Demo — Backlog v6.0 | February 24, 2026*
*Next action: Session 1 — Loop 3 (A1, A2, A3). Parallel: blog 5×→20× fix, advert cleanup.*
