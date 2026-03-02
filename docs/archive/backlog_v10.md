# SOC Copilot Demo — Backlog v10

**Date:** February 26, 2026
**Status:** v3.2 Complete and Tagged. Product strategy complete. Sequential v4.0 → v4.5 build planned.
**Environment:** Windows 11, Python 3.11, Node 20, Docker Desktop
**Repos:**
- Demo: git@github.com:ArindamBanerji/gen-ai-roi-demo.git (main, v3.2 tag)
- Experiments: git@github.com:ArindamBanerji/cross-graph-experiments.git (main, v1.0 tag)
**Working directories:**
- v3.2 (stable demo): gen-ai-roi-demo-v3.2
- v4 (next build): gen-ai-roi-demo-v4 (clone of v3.2 — to be created)
**Ports:** 8000 (backend) / 5174 (frontend)

---

## SECTION A: Completed Work

### v2.0–v2.5.1 (Tagged)

*(unchanged — see backlog_v8.md Section A)*

### v3.0 (Tagged)

| Session | Prompt | Feature | Status |
|---|---|---|---|
| 1 | A1–A3 | Loop 3 backend + frontend, Three-Loop Hero, Four Layers strip | ✅ Done |
| 2 | B2–B3 | Policy Override fix, ROI pulse fix | ✅ Done |
| 3 | EC1a–EC1b | Live Pulsedive API with fallback, Threat Intel badge | ✅ Done |
| 4 | EL1–EL3 | Decision audit service, SHA-256 hash chain, Evidence Ledger panel | ✅ Done |
| 5 | DX1–DX1b | Decision factor breakdown with live threat intel | ✅ Done |

### v3.1 / v3.1.1 (Tagged)

| Feature | Status |
|---|---|
| 4 cross-context metrics, Threat Landscape panel, cross-context separator | ✅ Done |
| Evidence Ledger wiring, seed data fix, port fix, dotenv fix, reset fix | ✅ Done |

### v3.2 (Tagged — February 25, 2026)

| Feature | Status |
|---|---|
| `backend/app/core/` — state_manager.py, domain_registry.py | ✅ Done |
| `backend/app/domains/base.py` — DomainConfig ABC | ✅ Done |
| `backend/app/domains/soc/` — config.py, factors.py, situations.py, policies.py | ✅ Done |
| `backend/app/domains/supply_chain/` — config.py stub (full schema, stubs for methods) | ✅ Done |
| `frontend/src/lib/domain.ts` — frontend domain config singleton | ✅ Done |
| Services delegating to domain modules (situation.py, triage.py, policy.py) | ✅ Done |
| GET /api/demo/domains endpoint | ✅ Done |
| Code review Pass 1 (Opus) — 3 HIGH, 11 MEDIUM, 8 LOW | ✅ Done |

### Product Strategy & Positioning (February 26, 2026) [NEW]

| Item | Version | Status |
|---|---|---|
| Product strategy (competitive analysis, value features, positioning) | v1.0 | ✅ Done |
| v4 design document (Phase 5 compounding proof added) | v3.0 | ✅ Done |
| v4.5 design document (F5 cross-domain discovery added) | v5.0 | ✅ Done |
| Roadmap (competitive positioning, value features, cross-vertical map) | v4.0 | ✅ Done |
| Deployment strategy (Progressive Realism, VPS hosting, cost model) | v3.0 | ✅ Done |
| Positioning graphics — 9 NBP prompts (POS-00A/B/C, POS-01–06) | v2 | ✅ Done |

### Content & Outreach (Current Status)

| Item | Version | Status |
|---|---|---|
| CI blog | v4.0 | ✅ Live |
| Math blog | — | ✅ Live |
| Demo blurb | v3.1 | ✅ Live (updated Feb 26) |
| Outreach emails | v6 | ✅ Done |
| LinkedIn posts | v6 | ✅ Done — 8 posts ready |
| Loom script | v8 | ✅ Done |
| Loom v1 recording | — | ✅ Live |
| Loom v2 recording | — | **Not yet recorded** |
| Blog advert replacement | v3 | In docs directory |
| Deck storyboards | A v3, B v5 | In docs directory |
| Roadmap deck | v2 | Customer-facing — **update with v4 roadmap + positioning** |
| Deployment strategy | **v3** | **Updated: VPS hosting, progressive realism, cost model** |
| Positioning graphics | **v2** | **9 graphics: opening sequence (3), framework (3), competitive (3)** |

---

## SECTION B: v4 Pre-Work (Human Tasks)

### B0. Clone & Clean (Before First Claude Code Session)

**Step 1: Clone v3.2 → v4**
```powershell
cd C:\Users\baner\CopyFolder\IoT_thoughts\python-projects\kaggle_experiments\claude_projects
xcopy gen-ai-roi-demo-v3.2 gen-ai-roi-demo-v4 /E /I
cd gen-ai-roi-demo-v4
```

**Step 2: Clean docs directory**

Keep in `docs/` (active documents):
```
PROJECT_STRUCTURE.md          ← will be updated as v4 progresses
CODE_REVIEW_V31_PASS1.md     ← reference for verification
blog_advert_replacement_v3.md
deck_a_storyboard_v3.md
deck_b_storyboard_v5.md
linkedin_posts_v6.md
loom_script_v8.md
outreach_emails_v6.md
```

Add to `docs/` (new from this session):
```
session_continuation_package_v11.md
backlog_v10.md
product_strategy_v1.md
v4_design_document_v3.md
v4_5_design_v5.md
soc_copilot_roadmap_v4.md
deployment_strategy_v3.md
```

Move to `docs/archive/` (superseded):
```
backlog_v8.md
backlog_v9.md
session_continuation_package_v9.md
session_continuation_package_v10.md
v4_design_document_v1.md
v4_design_document_v2.md       ← superseded by v3
v4_5_design_v3.md              ← superseded by v5
v4_5_design_v4.md              ← superseded by v5
v4_planning_document_v1.md
soc_copilot_roadmap_v3.md      ← superseded by v4
deployment_strategy_v2_1.md    ← superseded by v3
v3_2_refactoring_and_s2p_domain_model_v1.md
v3_design_document_v8.md
v3_all_prompts.md
code_review_plan_v31.md
blog_advert_review.md
EXPERIMENTS.md
graphic_13_CGA04.json
graphic_13_CGA04_prompt.md
docs.txt
```

**Step 3: Verify v3.2 still runs in original directory**
```powershell
cd gen-ai-roi-demo-v3.2\backend
uvicorn app.main:app --reload --port 8000
# In separate terminal:
cd gen-ai-roi-demo-v3.2\frontend
npx vite --port 5174
# Quick smoke test in browser
```

---

## SECTION C: Active Backlog — v4.0 Build (Sequential)

**Theme:** "Your tools, our decisions. Compounding proved."
**Design doc:** v4_design_document_v3.md (source of prompt specs)
**Total:** 36 prompts (33 code + 3 VPS), ~13 sessions
**Prerequisite:** v3.2 tagged, v4 directory created

### C0. Code Review Fix Verification [P0]

| ID | Task | Status |
|---|---|---|
| CR-0 | Verify HIGH findings H-1, H-2, H-3 status in v3.2 codebase | Not started |
| CR-1 | Fix any remaining HIGH findings | Depends on CR-0 |

### C1. Phase 1: UCL Connectors + Table Stakes (Sessions 1–4, 11 prompts) [P1]

| ID | Feature | Files | Status |
|---|---|---|---|
| C1 | UCL Connector base class + registry | connectors/base.py, registry.py, graph.py, main.py | Not started |
| C3 | Refactor Pulsedive into connector pattern | connectors/pulsedive.py, main.py | Not started |
| C2 | GreyNoise connector | connectors/greynoise.py, main.py | Not started |
| C4a | Multi-source aggregation endpoint | routers/graph.py | Not started |
| C4b | Multi-source badge in Tab 3 | AlertTriageTab.tsx, api.ts | Not started |
| C5a | CrowdStrike mock connector | connectors/crowdstrike_mock.py, main.py | Not started |
| C5b | CrowdStrike in multi-source badge | AlertTriageTab.tsx | Not started |
| T1 | Tab 1: Cross-source query examples | SOCAnalyticsTab.tsx | Not started |
| F1-1 | MITRE ATT&CK alert type alignment | seed data, situation types | Not started |
| F1-2 | ATT&CK tactic badges in UI | AlertTriageTab.tsx | Not started |
| F2-1 | Realistic alert corpus (10+ alert types, field-accurate) | seed data | Not started |

**Outreach milestone:** After Phase 1, update demo blurb + LinkedIn posts with multi-source screenshots.

### C2. Phase 2: Docker for Partners (Sessions 5–6, 5 prompts) [P2]

| ID | Feature | Status |
|---|---|---|
| D1 | Backend Dockerfile | Not started |
| D2 | Frontend Dockerfile | Not started |
| D3 | docker-compose.yml | Not started |
| D4 | Seed script in Docker context | Not started |
| D5 | PARTNER_README + health endpoint | Not started |

### C2.5. Phase 2.5: VPS Hosting (Session 7, 3 prompts) [P2]

| ID | Feature | Status |
|---|---|---|
| VPS-1 | Docker Compose prod profile + Caddy reverse proxy with auto-TLS | Not started |
| VPS-2 | Demo reset endpoint + daily cron reset | Not started |
| VPS-3 | Demo banner + welcome modal + rate limiting | Not started |

**Target:** demo.dakshineshwari.net on Hetzner CX31 (~$9/mo)

### C3. Phase 3: Live Graph Integration (Sessions 8–9, 4 prompts) [P2]

| ID | Feature | Status |
|---|---|---|
| LG1 | Feedback outcome writes → Neo4j | Not started |
| LG2 | Feedback reads from Neo4j (persist across restart) | Not started |
| LG3 | Policy state → Neo4j | Not started |
| LG4 | Triage state → Neo4j | Not started |

### C4. Phase 4: Polish (Session 10, 3 prompts) [P3]

| ID | Feature | Status |
|---|---|---|
| PH1 | Query registry + fuzzy matching | Not started |
| PH2 | "Did You Mean?" in Tab 1 | Not started |
| FC1 | Four Clocks diagnostic in Tab 4 | Not started |

### C5. Phase 5: Compounding Proof (Sessions 11–13, 8 prompts) [P1]

| ID | Feature | Status |
|---|---|---|
| NAR-1 | Investigation narrative engine (backend) | Not started |
| NAR-2 | Narrative panel in Tab 3 | Not started |
| NAR-3 | Narrative evolves with feedback | Not started |
| CP-1 | Compounding proof backend (track weight evolution, pattern discovery) | Not started |
| CP-2 | Compounding proof panel (Tab 4 — "How This System Got Smarter") | Not started |
| CP-3 | Before/after comparison for demos | Not started |
| TC-1 | Trust curve backend (confidence trajectory per alert type) | Not started |
| TC-2 | Trust curve visualization in Tab 4 | Not started |

**v4.0 TAG after all phases verified.**

---

## SECTION D: Future Backlog — v4.5 Build (After v4.0 Tagged)

**Theme:** "INOVA MVP + Flash Tier + cross-domain discovery."
**Design doc:** v4_5_design_v5.md
**Total:** 19 prompts (15 code + 4 VPS/infra), ~7 sessions
**Prerequisite:** v4.0 complete and tagged

### D1. INOVA Sessions A–E (11 prompts)

| ID | Feature | Status |
|---|---|---|
| INOVA-1a | UCL Entity Resolution service (core/) | Not started |
| INOVA-1b | Opt Pulsedive + GreyNoise into UCL resolution | Not started |
| INOVA-2 | TRIGGERED_EVOLUTION + CALIBRATED_BY write-back relationships | Not started |
| INOVA-3a | CISA KEV connector (live feed) | Not started |
| INOVA-3b | Health-ISAC mock connector | Not started |
| INOVA-4a | Cross-graph discovery sweep (core/) | Not started |
| INOVA-4b | Discovery sweep UI panel (Tab 4) | Not started |
| INOVA-4c | Discovery sweep scheduler | Not started |
| INOVA-5 | Loop 3 governing signal labels + evolution trace | Not started |
| INOVA-6 | HIPAA Evidence Ledger framing + Tab 4 ordering | Not started |

### D2. Cross-Domain Discovery — F5 (4 prompts) [NEW]

| ID | Feature | Status |
|---|---|---|
| F5-1 | Discovery sweep expanded: domain-pair relevance scoring | Not started |
| F5-2 | Discovered dimension auto-creation (new scoring factors) | Not started |
| F5-3 | Discovery history panel (what the system found, when, confidence) | Not started |
| F5-4 | Recursive discovery: discoveries as entities in next sweep | Not started |

### D3. Flash Tier Session F (4 prompts)

| ID | Feature | Status |
|---|---|---|
| FT-MIMIC-1 | Synthetic feed service (core/) | Not started |
| FT-MIMIC-2 | Flash Tier scorer (core/) | Not started |
| FT-MIMIC-3 | UCL handoff (scorer → triage) | Not started |
| FT-MIMIC-4 | Flash Tier dashboard (Tab 1 panel) | Not started |

### D4. VPS Multi-Instance (1 prompt)

| ID | Feature | Status |
|---|---|---|
| VPS-4 | Per-prospect instances on same VPS with different seed data | Not started |

**v4.5 TAG after all prompts verified.**

---

## SECTION E: Active Backlog — Outreach & Content

### E1. Outreach Updates at Milestones

| Milestone | Outreach Action | Priority |
|---|---|---|
| After code review verified | Record Loom v2 using script v8 | P1 |
| After v4 Phase 1 (connectors) | Update demo blurb with multi-source. New screenshots. Update outreach emails v7. | P1 |
| After v4 Phase 1 | New LinkedIn post: "Three sources. One graph." with screenshot | P1 |
| After v4 complete | Update Loom script v9 for multi-source + Docker. Consider Loom v3. | P2 |
| After v4.5 INOVA | INOVA-specific outreach variant. Healthcare positioning. | P2 |

### E2. Standing Outreach Items

| Item | Status | Notes |
|---|---|---|
| Post LinkedIn Series A (5 posts) | ❌ Pending | Posts ready, A-4/A-5 need screenshots |
| Post LinkedIn Series B (3 posts) | ❌ Pending | Posts ready |
| Blog advert page in Wix | ❌ Pending | Replacement text ready (v3) |
| Render positioning graphics (POS-00A–POS-06) | ❌ Pending | NBP prompts ready. Run through NBP and finalize. |
| Update roadmap deck with v4 positioning | ❌ Pending | soc_copilot_roadmap_v4.md is source |

### E3. Positioning Graphics Status [NEW]

| Graphic | NBP Prompt Status | Rendered | Final |
|---|---|---|---|
| POS-00A (New Employee Problem) | ✅ v4 | ✅ Rendered | Needs stage labels (not months) verified |
| POS-00B (What Actually Compounds) | ✅ v5 (cascade) | ✅ Rendered | Sharpened text pending render |
| POS-00C (Synopsis — Four Blocks) | ✅ v2 (2 options) | ❌ Not rendered | Choose Command Center or Journey layout |
| POS-01 (Three Axes) | ✅ v2 | — | Render needed |
| POS-02 (Three Generations) | ✅ v2 | — | Render needed |
| POS-03 (Compounding Curve) | ✅ Fixed (abstract stages) | ✅ Old version rendered | Re-render with fixed prompt |
| POS-04 (vs Dropzone) | ✅ v2 | — | Render needed |
| POS-05 (Landscape Quadrant) | ✅ v2 | — | Render needed |
| POS-06 (Capability Matrix) | ✅ v2 (10 rows, cycle tags) | ✅ Old version rendered | Re-render with v2 prompt |

---

## SECTION F: S2P Readiness Tracker

S2P is **not in active backlog** but the architecture supports it. This section tracks readiness.

| Prerequisite | Status | Notes |
|---|---|---|
| domain_registry.py | ✅ v3.2 | Supports adding domains without touching core |
| domains/supply_chain/config.py | ✅ v3.2 | Full schema, stubs for classify/compute |
| domains/base.py (DomainConfig ABC) | ✅ v3.2 | 10 properties + 3 methods |
| S2P situations.py | ❌ Not built | 6 situation types designed in use_case_change doc |
| S2P factors.py | ❌ Not built | 6-factor vector designed |
| S2P policies.py | ❌ Not built | 4 policies + conflict scenario designed |
| S2P Neo4j seed data | ❌ Not built | ~50 nodes: suppliers, materials, POs, events |
| S2P frontend domain.ts | ❌ Not built | Labels, metrics, tab titles |
| Domain expert validation | ❌ Not done | Procurement practitioner review needed |

**Estimated effort when ready:** 4–5 Claude Code prompts for demo-grade S2P module.
**Roadmap placement:** v7.0 (production), but stub demo possible any time after v3.2.

---

## SECTION G: Master Priority Queue

| Priority | Item | Section | Effort | Blocking What |
|---|---|---|---|---|
| **P0** | Clone v3.2 → v4 + clean docs + add new docs | B0 | 30 min (human) | Everything |
| **P0** | Verify code review fixes | C0 | 1 prompt | v4 build confidence |
| **P0** | Fix any remaining HIGH findings | C0 | 1-2 prompts | Loom v2 + v4 |
| **P1** | v4.0 Phase 1: UCL Connectors + table stakes (F1, F2) | C1 | 11 prompts, 4 sessions | Multi-source demo |
| **P1** | v4.0 Phase 5: Compounding Proof (F3, F4, F6) | C5 | 8 prompts, 3 sessions | "Show me it compounds" |
| **P1** | Outreach update after Phase 1 | E1 | 1 session | Prospect readiness |
| **P1** | Record Loom v2 | E1 | 1 hour (human) | Outreach emails |
| **P2** | v4.0 Phase 2: Docker | C2 | 5 prompts, 2 sessions | Partner self-service |
| **P2** | v4.0 Phase 2.5: VPS hosting | C2.5 | 3 prompts, 1 session | demo.dakshineshwari.net |
| **P2** | v4.0 Phase 3: Live Graph | C3 | 4 prompts, 2 sessions | State persistence |
| **P2** | Post LinkedIn (8 posts) | E2 | Manual | Social presence |
| **P2** | Render + finalize positioning graphics | E3 | Manual (NBP) | Pitch deck |
| **P3** | v4.0 Phase 4: Polish | C4 | 3 prompts, 1 session | Exec UX |
| **P3** | Blog advert replacement in Wix | E2 | 30 min (Wix) | Blog freshness |
| **P4** | v4.5: INOVA + F5 discovery (after v4 tagged) | D1+D2 | 15 prompts, 5 sessions | INOVA customer path |
| **P4** | v4.5: Flash Tier (after v4 tagged) | D3 | 4 prompts, 1 session | Volume reduction |
| **P4** | v4.5: VPS multi-instance | D4 | 1 prompt | Per-prospect demos |

---

## SECTION H: Version History

| Version | Date | Changes |
|---|---|---|
| 1.0–8.0 | Feb 10–24 | Initial through v3.1.1 completion |
| 9.0 | Feb 26 | v3.2 complete (domain-agnostic refactoring). Sequential v4.0 → v4.5 design. |
| **10.0** | **Feb 26** | **Product strategy v1 created. Design docs updated (v4→v3 with Phase 5, v4.5→v5 with F5). Roadmap v4 with competitive positioning + value features. Deployment v3 with VPS hosting. Nine positioning graphics (POS-00A/B/C, POS-01–06). v4.0 scope expanded to 36 prompts (added Phase 5 + VPS). v4.5 scope expanded to 19 prompts (added F5 + VPS-4). Compounding cycle articulated: accumulate→adjust→respond→discover. Outreach graphics tracking section added.** |

---

*SOC Copilot Demo — Backlog v10 | February 26, 2026*
*v3.2 shipped. Product strategy + positioning complete. Sequential v4.0 (36 prompts) → v4.5 (19 prompts). Nine positioning graphics ready for render.*
