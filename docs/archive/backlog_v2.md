# SOC Copilot Demo — Backlog v2

**Date:** February 18, 2026 (updated from February 12, 2026)
**Status:** v2.0 Complete. Pre-work tasks mostly done. Focus shifts to v2.5 build + Docker + outreach.
**Environment:** Windows 11, Python 3.11, Node 20, Docker Desktop
**Repo:** git@github.com:ArindamBanerji/gen-ai-roi-demo.git
**Branch:** main (v2.0 tagged), feature/v2-enhancements (synced)

---

## SECTION A: Pre-Work Status (from Original Backlog)

These tasks were defined pre-v2 build. Most are complete. Updated status below.

| Task | Description | Status | Notes |
|---|---|---|---|
| Task 0: Pre-Requisite Checks | Python, Node, Docker, Neo4j verification | DONE | Environment verified |
| Task 1: Initialize Git in v1 | .gitignore, init, first commit, tag v1.0 | DONE | v1 tagged |
| Task 2: Create v2 Directory | Copy, set up git branch | DONE | gen-ai-roi-demo-v2 working dir |
| Task 3: Local Neo4j Container | Docker Neo4j for v2 dev | DONE | neo4j-v2-dev container |
| Task 4: Configure v2 Environment | .env, ports 8001/5174 | DONE | Both envs running independently |
| Task 5: Seed Local Neo4j + Verify | Run seed script, verify v2 runs | DONE | v2 running on Aura |
| Task 6: Clean Up Root Directory | Remove stale files | DONE | Cleaned |
| Task 7: v2 Dependencies Pre-Install | npm, pip installs for v2 features | DONE | All deps installed |
| Task 8: Verify Claude Code Readiness | CLAUDE.md, PROJECT_STRUCTURE.md | DONE | Updated for v2 |
| Decision 1: Cloning Strategy | Separate directory chosen | DONE | gen-ai-roi-demo-v2 |
| Decision 2: Neo4j Strategy | Local Docker for dev, Aura for demo | DONE | Using Aura for demo |
| Decision 3: Port Allocation | v1=8000/5173, v2=8001/5174 | DONE | Working |

### Remaining Pre-Work Items

| Item | Status | Action Needed |
|---|---|---|
| PR merge feature/v2-enhancements to main | DONE | Merged, tagged v2.0 |
| Push v2.0 tag to remote | **VERIFY** | Run: `git tag -l` and `git push origin v2.0` if not pushed |
| Clean up feature branch | **TODO** | Delete feature/v2-enhancements after confirming merge |

---

## SECTION B: Active Backlog — v2.5 Build

**ACCP Progress:** v2.0 = 7/18 capabilities. v2.5 target = 10/18.

### B1. ROI Calculator [ACCP: Decision Economics Extended]

**Priority: P0** — Single strongest CISO closer for partner meetings.
**Design:** See design document Section 1A.
**Prompts:** 3 (7A, 7B, 7C)

| Prompt | Scope | Files | Status |
|---|---|---|---|
| 7A | Backend: /api/roi/calculate endpoint | backend/app/routers/roi.py | Not started |
| 7B | Frontend: ROI Calculator modal with sliders | frontend/src/components/ROICalculator.tsx | Not started |
| 7C | Tab 4 integration + PDF export | CompoundingTab.tsx + export utility | Not started |

**Claude Code prompt template:**
```
Build the ROI Calculator backend endpoint. See design doc Section 1A for calculation logic.
Create /api/roi/calculate that accepts: alerts_per_day, analysts, salary, current_mttr, 
current_auto_close, escalation_cost. Returns projected savings breakdown.
Do not start debugger/servers. Do not run git commands.
```

### B2. Outcome Feedback Loop [ACCP: TRIGGERED_EVOLUTION Completed]

**Priority: P1** — Answers "does it actually learn from being wrong?"
**Design:** See design document Section 1B.
**Prompts:** 2 (8A, 8B)

| Prompt | Scope | Files | Status |
|---|---|---|---|
| 8A | Backend: /api/alert/outcome endpoint + feedback service | backend/app/routers/triage.py + backend/app/services/feedback.py | Not started |
| 8B | Frontend: Outcome Feedback panel in Tab 3 | AlertTriageTab.tsx | Not started |

### B3. Policy Conflict Resolution [ACCP: Eval Gates Extended]

**Priority: P1** — CISOs deal with conflicting policies daily.
**Design:** See design document Section 1C.
**Prompts:** 2 (9A, 9B)

| Prompt | Scope | Files | Status |
|---|---|---|---|
| 9A | Backend: Policy definitions, conflict detection, resolution | backend/app/services/policy.py | Not started |
| 9B | Frontend: Policy Conflict panel in Tab 3 | AlertTriageTab.tsx | Not started |

### B4. Prompt Hub [ACCP: Typed-Intent Bus Early]

**Priority: P2** — Improves Tab 1 usability.
**Design:** See design document Section 1D.
**Prompts:** 2 (10A, 10B)

| Prompt | Scope | Files | Status |
|---|---|---|---|
| 10A | Backend: Fuzzy matching + suggestion engine | backend/app/services/prompt_hub.py | Not started |
| 10B | Frontend: "Did you mean?" suggestions | SOCAnalyticsTab.tsx | Not started |

### v2.5 Build Sequence

```
Session A: ROI Calculator (Prompts 7A, 7B, 7C)
  -> Commit, test, push
  -> ACCP progress: 8/18

Session B: Outcome Feedback + Policy Conflict (Prompts 8A, 8B, 9A, 9B)
  -> Commit, test, push
  -> ACCP progress: 10/18

Session C (optional): Prompt Hub + Polish (Prompts 10A, 10B)
  -> Commit, test, push
  -> Tag v2.5, update docs
  -> ACCP progress: 10/18 (Prompt Hub is partial Typed-Intent, doesn't add a full capability)
```

---

## SECTION C: Dockerization — Partner Distribution

**Purpose:** Create a Docker image that consulting partners can run locally to demo the SOC Copilot without any development environment setup.

**This is separate from the dev Docker (Task 3 above).** Dev Docker = local Neo4j for development. Partner Docker = full-stack containerized demo for distribution.

### C1. Docker Compose — Full Stack

| Container | Image | Ports | Purpose |
|---|---|---|---|
| backend | Custom (FastAPI) | 8001 | API server |
| frontend | Custom (Vite/React build -> nginx) | 5174 | Static frontend |
| neo4j | neo4j:5.14 | 7474, 7687 | Graph database (pre-seeded) |

**Requirements:**
- Single `docker-compose up` starts everything
- Neo4j pre-seeded with demo data (run seed script in entrypoint or use mounted volume)
- Environment variables pre-configured (no .env editing required for partners)
- Health checks on all three containers
- Frontend configured to hit backend at correct internal Docker network address

### C2. Partner Distribution Package

| Deliverable | Description | Status |
|---|---|---|
| docker-compose.yml | Full-stack compose file | Not started |
| Dockerfile.backend | FastAPI container | Not started |
| Dockerfile.frontend | Build React, serve via nginx | Not started |
| .env.docker | Pre-configured env for Docker | Not started |
| neo4j-seed/init.sh | Auto-seed Neo4j on first run | Not started |
| PARTNER_README.md | Setup instructions (5 steps max) | Not started |
| Demo script (updated for v2) | What to click, what to say | Not started |

### C3. Partner README Requirements

The partner should need exactly this:

```
1. Install Docker Desktop
2. Clone the repo (or download ZIP)
3. Run: docker-compose up
4. Wait ~60 seconds for Neo4j to seed
5. Open http://localhost:5174
```

No Python. No Node. No .env editing. No Neo4j configuration.

### C4. Implementation Prompts

| Prompt | Scope | Status |
|---|---|---|
| D1 | Dockerfile.backend (FastAPI + dependencies) | Not started |
| D2 | Dockerfile.frontend (Vite build + nginx) | Not started |
| D3 | docker-compose.yml + .env.docker + neo4j seed script | Not started |
| D4 | PARTNER_README.md + health check verification | Not started |

**Note:** Docker prompts (D1-D4) can run in parallel with v2.5 build prompts. They don't depend on v2.5 features -- they containerize the current v2.0 demo. When v2.5 ships, rebuild the images.

---

## SECTION D: Loom / Outreach

### D1. Loom Demo Script — v2 Update

**Current state:** demo_script_v5.pdf exists for v1 (4 tabs, no learning loops, no decision economics).
**Needed:** Updated script covering v2 features.

| Section | v1 Script | v2 Additions |
|---|---|---|
| Tab 1 intro | Governed analytics, provenance | Same (minor polish) |
| Tab 2 deep dive | Eval gates, evolution | AgentEvolver panel, "Simulate Failed Gate", operational impact ($4,800/mo) |
| Tab 3 deep dive | Alert triage, graph traversal | Situation Analyzer, Decision Economics ($127/alert), second alert type |
| Tab 4 summary | Week-over-week comparison | Business Impact Banner (847 hrs, $127K), Two-Loop Hero Diagram |
| Closing | Architecture recap | Compounding intelligence framing, ACCP roadmap tease |

**Estimated length:** 10-12 minutes (v1 was ~10 min).

### D2. Short Loom Version

**Purpose:** 3-minute cut for LinkedIn, email follow-ups, busy CISOs.
**Structure:**
1. 30 sec: "Your SOC has amnesia" hook + the problem
2. 60 sec: Tab 3 — alert triage with Situation Analyzer + Decision Economics (the "aha")
3. 45 sec: Tab 2 — AgentEvolver showing compounding ($4,800/mo, 0 missed threats)
4. 30 sec: Tab 4 — Business Impact Banner (847 hrs, $127K)
5. 15 sec: Close — "Same model. Same code. Smarter graph. Let's talk."

### D3. Outreach Emails

**Status:** Two emails drafted in session continuation package v2.
- Email 1: Compounding Intelligence (narrative-driven)
- Email 2: The Math Behind Agent ROI (numbers-driven)

**Needed:** Update both to reference ACCP and v2 demo features.

### D4. Blog Updates

| Blog | Update Needed | Priority |
|---|---|---|
| SOC Copilot Demo page | Add v2 screenshots, update feature list | P2 |
| Compounding Intelligence blog | Add "Why Today's AI Approaches Don't Compound" section (see blog addendum v2) | P2 |

---

## SECTION E: Documentation Updates

| Document | Update Needed | Status |
|---|---|---|
| CLAUDE.md | Add ACCP capability map, v2.5 context | TODO |
| PROJECT_STRUCTURE.md | Update if new files added in v2.5 | TODO (after v2.5 build) |
| README.md | Add v2.5 features when shipped | TODO (after v2.5 build) |
| V2_IMPLEMENTATION_PLAN.md | Mark v2.0 complete, add v2.5 plan | TODO |
| competitive_posture_v3.md | Living document -- update after RSA 2026 | Current |
| blog_addendum_v2.md | Ready for Wix integration | Current |

---

## SECTION F: Master Priority Queue

| Priority | Item | Section | Effort | ACCP Impact |
|---|---|---|---|---|
| **P0** | ROI Calculator | B1 | 3 prompts (1 session) | Decision Economics extended |
| **P1** | Outcome Feedback Loop | B2 | 2 prompts (half session) | TRIGGERED_EVOLUTION completed |
| **P1** | Policy Conflict Resolution | B3 | 2 prompts (half session) | Eval Gates extended |
| **P2** | Prompt Hub | B4 | 2 prompts (half session) | Typed-Intent Bus (early) |
| **P2** | Docker for Partners | C | 4 prompts (1 session) | — (distribution) |
| **P2** | Loom v2 Script | D1 | 1 session (writing) | — (outreach) |
| **P3** | Short Loom (3 min) | D2 | After D1 | — (outreach) |
| **P3** | Outreach emails (ACCP update) | D3 | 30 min | — (outreach) |
| **P3** | Blog updates | D4 | 1-2 hours | — (content) |
| **P3** | Doc updates (CLAUDE.md etc.) | E | After v2.5 build | — (maintenance) |

### Recommended Session Order

```
Session 1: ROI Calculator (B1: Prompts 7A, 7B, 7C)
  -> Most impactful, self-contained, unblocks partner demos

Session 2: Outcome Feedback + Policy Conflict (B2+B3: Prompts 8A, 8B, 9A, 9B)
  -> Completes TRIGGERED_EVOLUTION cycle, adds governance demo
  -> Tag v2.5 after this session

Session 3: Docker for Partners (C: Prompts D1, D2, D3, D4)
  -> Can run anytime, containerizes whatever version is current
  -> Enables partner self-service demos

Session 4: Loom v2 Script + Recording
  -> Needs v2.5 features to be complete for best demo
  -> Write script, record, edit

Session 5 (optional): Prompt Hub + Polish (B4: Prompts 10A, 10B)
  -> Nice-to-have, lowest impact
```

---

## SECTION G: Docker Container Lifecycle (Reference)

The local Neo4j dev container persists across restarts (named volume neo4j-v2-data):

```powershell
# Stop (preserves data)
docker stop neo4j-v2-dev

# Start again
docker start neo4j-v2-dev

# View logs
docker logs neo4j-v2-dev --tail 20

# Complete reset (destroys data, re-seed needed)
docker rm -f neo4j-v2-dev
docker volume rm neo4j-v2-data
# Then re-run the docker run command from original Task 3
```

---

## SECTION H: Version History

| Version | Date | Changes |
|---|---|---|
| 1.0 | Feb 10, 2026 | Initial backlog (pre-work tasks, Decisions 1-3, Tasks 0-8) |
| 1.1 | Feb 12, 2026 | Minor updates to task details |
| 2.0 | Feb 18, 2026 | Major restructure. Marked pre-work tasks done. Added v2.5 build items with ACCP tags. Added Dockerization section. Added Loom/outreach section. Added master priority queue. Integrated with competitive posture v3 and design document v2. |

---

*SOC Copilot Demo -- Backlog v2.0 | February 18, 2026*
*Next action: Session 1 (ROI Calculator, Prompts 7A-7C)*
