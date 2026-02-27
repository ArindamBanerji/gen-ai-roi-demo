# SOC Copilot Demo — Backlog v8

**Date:** February 24, 2026
**Status:** v3.1.1 Complete and Tagged (14/21 ACCP). Customer insights integrated. Outreach updated. Blog replacement ready.
**Environment:** Windows 11, Python 3.11, Node 20, Docker Desktop
**Repos:**
- Demo: git@github.com:ArindamBanerji/gen-ai-roi-demo.git (main, v3.1.1 tag)
- Experiments: git@github.com:ArindamBanerji/cross-graph-experiments.git (main, v1.0 tag)
**Working directories:** gen-ai-roi-demo-v2 (v2.5.1, prospect demos) / gen-ai-roi-demo-v3 (v3.1.1, current)
**Ports:** 8000 (backend) / 5173 (frontend)

---

## SECTION A: Completed Work

### v2.0–v2.5.1 (Tagged)

*(unchanged from v7 — see backlog_v7.md Section A)*

### v3.0 (Tagged — February 24, 2026)

| Session | Prompt | Feature | Status |
|---|---|---|---|
| 1 | A1 | Backend: GET /api/rl/reward-summary | ✅ Done |
| 1 | A2 | Frontend: Loop 3 panel in Tab 2 | ✅ Done |
| 1 | A3 | Frontend: Three-Loop Hero + Four Layers strip in Tab 4 | ✅ Done |
| 2 | B2 | Fix: Policy Override (amber banner + button) | ✅ Done |
| 2 | B3 | Fix: Remove ROI button pulse animation | ✅ Done |
| 3 | EC1a | Backend: Live Pulsedive API with hardcoded fallback | ✅ Done |
| 3 | EC1b | Frontend: Threat Intel badge in Tab 3 | ✅ Done |
| 4 | EL1 | Backend: Decision audit service + JSON/CSV export | ✅ Done |
| 4 | EL2 | Backend: SHA-256 tamper-evident hash chain | ✅ Done |
| 4 | EL3 | Frontend: Evidence Ledger panel in Tab 4 | ✅ Done |
| 5 | DX1 | Backend: Decision factor breakdown with live threat intel | ✅ Done |
| 5 | DX1b | Frontend: "Why This Decision?" panel in Tab 3 | ✅ Done |

### v3.1 / v3.1.1 (Tagged — February 24, 2026)

| Feature | Status |
|---|---|
| 4 cross-context metrics (travel risk, device trust, policy conflicts, TI coverage) | ✅ Done |
| Threat Landscape at a Glance panel (Tab 1) | ✅ Done |
| Cross-context query separator in Tab 1 | ✅ Done |
| Evidence Ledger wiring (record_decision in execute path) | ✅ Done |
| Seed data fix (ALERT-7824, 2 users, pattern mapping) | ✅ Done |
| Port fix (vite proxy 8001→8000) | ✅ Done |
| dotenv fix (load_dotenv path) | ✅ Done |
| Reset fix (handleResetAlerts + CompoundingTab) | ✅ Done |

### Content & Outreach (Current Status)

| Item | Version | Status |
|---|---|---|
| Design document | v8.0 | ✅ Done — v3.0 complete |
| v4 design document | v1.0 | ✅ Done — 20 prompts, 8 sessions |
| v4 planning document | v1.0 | ✅ Done |
| CI blog | v4.0 | ✅ Live — 5×→20× fixed |
| Math blog | — | ✅ Live — 5×→20× fixed |
| Blog advert replacement | **v2** | ✅ **Ready — needs Wix publish** |
| Outreach emails | **v6** | ✅ **Done** — customer pain narrative, Health-ISAC, semantic fusion |
| LinkedIn posts | **v6** | ✅ **Done** — 8 posts (A-1 thru A-5, B-1 thru B-3) |
| Loom script | **v7** | ✅ **Done** — Tab 1 opener, manual IOC workflow, semantic fusion |
| Loom v1 recording | — | ✅ Live |
| Loom v2 recording | — | **Not yet recorded** |
| Code review plan | v25 | **Needs update to v31 for v3.1 codebase** |

---

## SECTION B: Active Backlog — Outreach & Content

### B1. Blog Advert Replacement [P0 — Prospect-Readiness]

| Item | Status | Effort |
|---|---|---|
| Replace full page content in Wix with blog_advert_replacement_v2.md | ❌ Pending | 30 min (Wix) |
| Take v3.1 screenshots (Tab 1 Landscape, Tab 3 Explainer, Tab 4 Ledger) | ❌ Pending | 15 min |
| Upload screenshots to Wix | ❌ Pending | 10 min |

### B2. Loom v2 [P1 — Blocks Outreach Emails]

| Step | Status | Notes |
|---|---|---|
| ~~Update Loom script for v3.1 features~~ | ✅ Done (v7) | Tab 1 opener, semantic fusion, manual IOC workflow |
| Run LLM judge on Loom script v7 | ❌ TODO | Quality check before recording |
| Record Loom v2 | ❌ TODO | ~15 min. Use script v7. Refresh Pulsedive early. |
| Cut 3-min LinkedIn short | ❌ TODO | After full recording |

### B3. Outreach Push [P1 — After Loom v2]

| Item | Status | Notes |
|---|---|---|
| ~~Update outreach emails~~ | ✅ Done (v6) | All 3 variants rewritten |
| ~~Update LinkedIn posts~~ | ✅ Done (v6) | A-4 rewritten, A-5 new |
| Post LinkedIn Series A (5 posts) | ❌ Pending | Posts ready, A-4/A-5 need screenshots |
| Post LinkedIn Series B (3 posts) | ❌ Pending | Posts ready, graphics exist |

### B4. Code Review [P1 — Before v4 Build]

| Step | Status | Notes |
|---|---|---|
| Update code review plan for v3.1 codebase | ❌ TODO | New files: services/triage.py, services/audit.py, routers/audit.py |
| Run 3-pass review (file-by-file, architecture, demo resilience) | ❌ TODO | ~2 sessions |
| Fix critical/high findings | ❌ TODO | Before v4 |

---

## SECTION C: Future Backlog — v4.0 Build

**Theme:** "Your tools, our decisions."
**Full spec:** v4_design_document_v1.md
**Estimated:** ~20 prompts, 8 sessions

### Phase 1: UCL Connectors (Sessions 1–3, ~8 prompts)

| ID | Feature | Status |
|---|---|---|
| C1 | UCL Connector base class + registry | Not started |
| C2 | GreyNoise connector | Not started (API key configured) |
| C3 | Refactor Pulsedive into connector pattern | Not started |
| C4a | Multi-source aggregation endpoint | Not started |
| C4b | Multi-source badge in Tab 3 | Not started |
| C5a | CrowdStrike mock connector | Not started |
| C5b | CrowdStrike in multi-source badge | Not started |
| T1 | Tab 1: Cross-source query examples | **Partially done (v3.1 queries reference multi-source)** |

### Phase 2: Docker + Live Graph (Sessions 4–7, ~9 prompts)

| ID | Feature | Status |
|---|---|---|
| D1–D5 | Docker for Partners | Not started |
| LG1–LG4 | Live Graph Integration | Not started |

### Phase 3: Polish (Session 8, ~3 prompts)

| ID | Feature | Status |
|---|---|---|
| PH1–PH2 | Query Hub + fuzzy matching | Not started |
| FC1 | Four Clocks diagnostic | Not started |

---

## SECTION D: Master Priority Queue

| Priority | Item | Section | Effort | Blocking What |
|---|---|---|---|---|
| **P0** | Replace blog advert in Wix | B1 | 30 min | Prospect-readiness |
| **P0** | Take v3.1 screenshots | B1 | 15 min | Blog + LinkedIn posts |
| **P1** | LLM judge on Loom script v7 | B2 | 30 min | Loom v2 quality |
| **P1** | Record Loom v2 | B2 | 1 hour | Outreach emails |
| **P1** | Post LinkedIn (8 posts) | B3 | Manual | Social presence |
| **P1** | Code review (3-pass) | B4 | 2 sessions | v4 build confidence |
| **P2** | v4.0 Phase 1: UCL Connectors | C | 3 sessions | Platform thesis |
| **P2** | v4.0 Phase 2: Docker + Live Graph | C | 3 sessions | Partner self-service |
| **P3** | v4.0 Phase 3: Polish | C | 1 session | Exec UX |
| **P3** | In-repo doc updates | D | 1 session | Maintainability |

---

## SECTION E: Version History

| Version | Date | Changes |
|---|---|---|
| 1.0–6.0 | Feb 10–24 | Initial through v3.0 scope finalization |
| 7.0 | Feb 24 | v3.0 COMPLETE (14/21). 12 prompts, 5 sessions. |
| **8.0** | **Feb 24** | **v3.1.1 tagged. Tab 1 Threat Landscape + cross-context queries. Evidence Ledger wired. Seed data fixed. Outreach v6/v7 done. Blog replacement ready. Customer insights (manual IOC workflow, Health-ISAC, semantic fusion) integrated into all outreach docs.** |

---

*SOC Copilot Demo — Backlog v8 | February 24, 2026*
*v3.1.1 shipped. Outreach updated. Next: Wix blog replacement, Loom v2, code review, then v4.0.*
