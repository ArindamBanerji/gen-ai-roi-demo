# SOC Copilot — Project Structure
**Last Updated:** March 23, 2026
**Version:** v5.5.2 (branch: v5.0-dev)
**Architecture:** GAE (scoring) + ci-platform (infrastructure) + SOC domain layer + React frontend
**Tests:** 284 passing (backend)
**Frontend:** React + TypeScript + Vite, port 5173

---

## Critical Design Decisions (read before changing anything)

| Decision | Value | Why |
|---|---|---|
| A=4 actions | escalate, investigate, suppress, monitor | `refer_to_analyst` is NOT a scorable action — it is a referral routing decision via ReferralEngine |
| SOC_ACTIONS has 5 items | includes refer_to_analyst | Used by referral policy and test assertions. SCORER_ACTIONS has 4. Use `scorer.counts.shape[1]` for tensor iteration — never `len(SOC_ACTIONS)` |
| Referral is VETO | fires after scoring, independent | ReferralRules R1-R7 in `services/referral_rules.py`. ANY rule firing overrides auto-approve. Backend sends `referral: {should_refer, reasons, audit_summary}` in every triage response. |
| R2/R7 need Neo4j data | sequence_count, cross_category_count | `db/neo4j.py` has `get_sequence_count()` + `get_cross_category_count()`. Decision nodes store `source_id` and `user_id` (added Mar 23). R2/R7 return 0 on None/exception (P-REF-2 safe degradation). |
| IKS shows 50.0 at 0 decisions | known anomaly | μ₀ sidecar may not be captured before calibration mutates centroids. Flag for Phase 2 code review. |
| Evidence Ledger | ci-platform, not local | `services/audit.py` is a thin adapter over `ci_platform.audit.evidence_ledger.EvidenceLedger`. Do NOT add hash chain logic here — it lives in ci-platform. |
| DEC- prefix | backend-only, fixed | `metrics.py` checks `_rid.upper().startswith('DEC-')` before prepending. Do not add prefix elsewhere. |

---

## Directory Tree

```
gen-ai-roi-demo-v4-v50/
├── backend/
│   └── app/
│       ├── domains/
│       │   └── soc/
│       │       ├── config.py           # SOCDomainConfig — C=6, A=4(scorer)/5(policy), d=6
│       │       ├── factors.py          # 6 FactorComputer implementations
│       │       ├── orchestrator.py     # async Neo4j → compute → GAE assembly
│       │       ├── alert_pool.py       # 25 alerts, 6 categories, ATT&CK
│       │       └── situations.py       # SituationAnalyzer — category routing
│       ├── routers/
│       │   ├── triage.py               # POST /api/alert/analyze — main triage pipeline
│       │   ├── evolution.py            # POST /alert/process — GAE pipeline
│       │   ├── feedback.py             # POST /api/feedback — learning + centroid update
│       │   ├── soc.py                  # GET /api/soc/* — profile, learning-state, frozen-roi
│       │   ├── metrics.py              # GET /api/metrics/* — compounding, evolution-events
│       │   ├── audit.py                # GET /api/audit/decisions — Evidence Ledger export
│       │   ├── simulation.py           # POST /api/simulation/run
│       │   ├── shadow.py               # Shadow mode endpoints
│       │   ├── graph_explorer.py       # POST /api/{domain}/query
│       │   └── admin.py                # POST /api/admin/reset
│       ├── services/
│       │   ├── audit.py                # Thin adapter over ci-platform EvidenceLedger (~220 lines)
│       │   ├── referral_rules.py       # R1-R7 SOC referral rules (VETO mechanism)
│       │   ├── iks.py                  # IKS — module-level functions (κ*=0.20, NOT a class)
│       │   ├── shadow.py               # ShadowModeService
│       │   ├── nl_templates.py         # NLTemplateEngine — 24 deterministic templates
│       │   ├── similar_cases.py        # SimilarCasesService — cosine similarity
│       │   ├── narrative.py            # NarrativeProvider protocol + Ollama/template impl
│       │   ├── simulation.py           # Simulation service
│       │   ├── evolver.py              # AgentEvolver
│       │   ├── state_manager.py        # State management
│       │   ├── gae_state.py            # GAE state wrappers
│       │   ├── feedback.py             # FEEDBACK_GIVEN — session state
│       │   └── neo4j_client.py         # Neo4j queries incl. get_sequence_count, get_cross_category_count
│       ├── db/
│       │   ├── neo4j.py                # Neo4j driver + query functions
│       │   └── seed_neo4j.py           # Graph seeding
│       ├── config.py                   # SOC_ACTIONS (5), SCORER_ACTIONS (4), SOC_FACTORS (6)
│       └── main.py
├── frontend/
│   └── src/
│       ├── App.tsx                     # Tab router + ErrorBoundary (key={activeTab})
│       ├── components/tabs/
│       │   ├── SOCAnalyticsTab.tsx     # Tab 1 — alert queue, threat landscape, ATT&CK
│       │   ├── RuntimeEvolutionTab.tsx # Tab 2 — IKS, centroid convergence, conservation
│       │   ├── AlertTriageTab.tsx      # Tab 3 — factor breakdown, referral callout, NL explanation
│       │   ├── CompoundingDashboard.tsx# Tab 4 — ROI, charts A-D, Evidence Ledger, evolution events
│       │   └── Tab5LearningNarrative.tsx # Tab 5 — exec narrative, Sections 1+2 deterministic
│       └── api.ts                      # fetchJSON (throws on !ok) — use this, not raw fetch()
├── tests/
│   ├── test_composite_gate.py          # AsyncMock stubs for get_sequence_count/get_cross_category_count
│   ├── test_referral_rules.py          # R1-R7 tests incl. R2/R7 threshold + safe degradation
│   └── [other test files]
├── docs/                               # Full design doc suite (18 files + gtm/)
│   ├── soc_copilot_design_v5_5_part1.md  # v5.5.2 — §22.6 Referral Routing Architecture
│   ├── soc_copilot_design_v5_5_part2.md
│   ├── soc_copilot_design_v5_5_part3.md
│   ├── gae_design_v10.md
│   ├── math_synopsis_v11.md
│   ├── master_action_plan_v3.md        # Governing plan
│   └── gtm/                           # 5 GTM docs
└── pyproject.toml                      # depends on: graph-attention-engine, ci-platform
```

---

## Triage Pipeline (the main flow)

```
POST /api/alert/analyze
  → SituationAnalyzer.classify(alert) → category c
  → FactorComputers × 6 → factor vector f
  → ProfileScorer.score(f, c) → action, confidence, ScoringResult
  → CompositeGate → routing_zone (auto_approve / investigate / full_review)
  → get_sequence_count(source_id) → sequence_count    ← Neo4j (R2)
  → get_cross_category_count(user_id) → cross_cat     ← Neo4j (R7)
  → ReferralEngine(R1-R7).evaluate(alert_context) → ReferralDecision
  → if should_refer → VETO (overrides auto_approve)
  → EvidenceLedger.append(LedgerEntry with epistemic fields)
  → response: {action, confidence, explanation, referral: {should_refer, reasons, audit_summary}}
```

---

## Frontend Rules

- **Always use `api.ts` fetchJSON** — it throws on `!ok`. Never use raw `fetch().then(r => r.json())`.
- **ErrorBoundary wraps each tab** with `key={activeTab}` — a crash in one tab resets on tab switch.
- **Referral callout** in AlertTriageTab renders amber box with R1-R7 human-readable labels when `should_refer === true`. Renders nothing when false.
- **Tab 5** Sections 1+2 are deterministic — no external gate needed. Section 3 gated by GATE-D.

---

## Known Issues (log, don't fix ad-hoc)

| Issue | Location | Notes |
|---|---|---|
| IKS=50.0 at 0 decisions | Tab 2 | μ₀ sidecar timing. Phase 2 code review. |
| R2/R7 default to 0 for historical Decision nodes | neo4j.py | Nodes created before Mar 23 lack source_id/user_id. Correct behavior — safe degradation. |
| No frontend test suite | frontend/ | Add Vitest after Phase 0B findings are stable. |

---

## API Endpoints Quick Reference

| Endpoint | Method | Returns |
|---|---|---|
| /api/alerts/queue | GET | 47 alerts |
| /api/alert/analyze | POST | action, confidence, explanation, referral |
| /api/soc/profile | GET | categories, actions (4), iks, decision_count |
| /api/soc/learning-state | GET | learning enabled/disabled, conservation status |
| /api/soc/frozen-roi | GET | ROI at current auto-approve rate |
| /api/audit/decisions | GET | Evidence Ledger entries |
| /api/metrics/evolution-events | GET | Recent evolution events (DEC- prefix fixed) |

---

*gen-ai-roi-demo-v4-v50 · v5.5.2 · 284 tests · March 23, 2026*
