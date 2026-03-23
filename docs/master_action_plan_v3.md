# SOC Copilot — Master Action Plan v3
**Date:** March 23, 2026
**Version:** 3.0
**Supersedes:** master_action_plan_v2 (March 22, 2026)

**Governing principles (changes from v2):**

1. **MVP over versioning.** No v6/v6.5/v7 labels. Work is either MVP (what a CISO needs to see to believe the product works) or Post-MVP (everything else). Features are sequenced by customer value, not by release label.

2. **Experiments before features.** No new feature code until all P0/P1 experiments are complete. Every experiment that forces a claim to weaken is a design gap — not a language fix. The gap goes into the MVP or Post-MVP feature queue with a concrete design answer.

3. **Synthetic data is canonical.** There is no "waiting for real customer data." Customers do not have the patience for this. LLM-judge and web scraping ARE the development process — from experiment validation to UI testing to GTM materials. Every experiment and validation uses synthetic data unless a specific real-data asset (e.g. CISA KEV) is named.

4. **Claims that weaken = design gaps.** If an experiment fails and a claim must be narrowed, the correct response is: identify what architectural capability is missing, design it, add it to the feature queue. Narrowing language without a design fix is not acceptable.

5. **Code review before new features.** PROJECT_STRUCTURE files updated → code-review-graph MCP active → systematic 4-repo review → issues logged → fixes made. Only then does new feature coding begin.

6. **PostgreSQL + VPS last.** Nothing in MVP or Post-MVP depends on the data layer migration. It goes at the end.

**Current state (March 23, 2026):**
- 478 GAE + 280 SOC + 73 ci-platform tests (~935 total)
- ~104 experiments complete. A=4 confirmed. DiagonalKernel default. ReferralRules R1-R7 shipped.
- docs/ cleaned and current in both repos. §22.6 committed (first time). GTM docs P0 batch done.
- 4 repos: graph-attention-engine-v50, gen-ai-roi-demo-v4-v50, ci-platform, cross-graph-experiments.

---

## MVP DEFINITION

An MVP is a session where a CISO sits down, connects to a live instance, and sees:

| # | What they see | Feature | Status |
|---|---|---|---|
| 1 | Alert arrives → factor breakdown + NL explanation → recommendation with confidence % | Tab 1/3, GAE pipeline | ✅ Built |
| 2 | "Show your work" — 6 factors, kernel weights, why it decided | Tab 3 provenance | ✅ Built |
| 3 | IKS score and trajectory — "the system is getting smarter" | Tab 2 IKS | ✅ Built |
| 4 | Auto-approve rate and which categories are calibrated | Tab 4 economics | ✅ Built |
| 5 | ROI calculator — analyst time saved, actual numbers | Tab 4 frozen ROI | ✅ Built |
| 6 | Referral rules firing — "this goes to human because executive account" | Referral R1-R7 | ⚠️ R2/R7 silent |
| 7 | Shadow mode report — agreement rate, top disagreements | Tab 2 shadow | ✅ Built |
| 8 | Deployment qualification — GREEN/AMBER/RED, kernel selected | P28 pipeline | ⚠️ Diagonal thresholds missing |
| 9 | Conservation law visible — "learning signal healthy" | Tab 2 conservation | ✅ Built |
| 10 | Evidence Ledger export | Tab 4 evidence | ✅ Built |

**MVP is not usable today because of items 6 and 8, plus zero frontend validation (every tab may have broken layouts). These are the Phase 0 blockers.**

---

## PHASE 0: MVP COMPLETION
*No experiments, no new features. Only fixes that make the MVP usable.*

### 0A — Wiring fixes (small, each ≤40 lines)

| # | Item | Repo | What | Effort |
|---|---|---|---|---|
| 0A-1 | **R2/R7 Neo4j Cypher wiring** | gen-ai-roi-demo-v4-v50 | sequence_count + cross_category_count queries. Without these, 2 of 7 referral rules never fire in production. Cypher: `MATCH (d:DecisionRecord) WHERE d.source_id=$src AND d.timestamp > $t-3600 RETURN count(d)` (R2) + distinct category query per user (R7). | ~40 lines |
| 0A-2 | **P28 DiagonalKernel thresholds** | ci-platform | Add kernel-dependent GREEN/AMBER/RED to DeploymentQualifier. Currently classifies DiagonalKernel deployments against L2 thresholds (wrong zone). GREEN≤0.157, AMBER≤0.25, RED>0.25 under Diagonal. Add kernel_recommendation + noise_ratio to qualification report. | ~20 lines + ≥3 tests (target: 76 ci-platform tests) |
| 0A-3 | **DEC-DEC double prefix** | gen-ai-roi-demo-v4-v50 | Tab 4 Recent Evolution Events shows "DEC-DEC-XXXX". Frontend prepends "DEC-" to ID already starting with "DEC-". | ~5 lines |
| 0A-4 | **θ_min 0.434→0.467 in harness** | cross-graph-experiments | One-line fix. Conservation floor stale — all future experiments use wrong threshold. | 1 line |
| 0A-5 | **Adj.G evidence ledger epistemic state** | ci-platform | Add kernel_type, noise_zone, conservation_status, confidence per decision to Evidence Ledger entry. EU AI Act Art. 15 compliance. | ~50 lines |

### 0B — Frontend validation

*Prerequisite: backend running at localhost:8000. Neo4j running. Frontend at localhost:5174.*

Every version of this product has had large frontend errors that were invisible until visual inspection. This has been deferred across multiple sessions. It cannot be deferred again.

Run each tab. Record what's broken. Fix. Repeat until clean.

| Tab | Known risks | Test |
|---|---|---|
| Tab 1 — Alert Triage | Alerts load, factor breakdown renders, confidence %, NL explanation, similar cases sidebar | Click 3+ alerts |
| Tab 2 — Institutional Intelligence | IKS header (non-null), purple summary card Section A, IKS trend chart (may be empty), AgentEvolver stats, left-rail nav | Check all sections |
| Tab 3 — Alert Detail | Factor breakdown + provenance nodes, bridge link to Tab 2 works, category + action display | Check bridge link specifically |
| Tab 4 — Decision Economics | ROI calculator, DEC-DEC prefix (fixed by 0A-3), frozen ROI endpoint returns data | Check after 0A-3 fix |
| Tab 5 — Executive | Section 1+2 render (deterministic, no GATE-D needed), IKS trajectory displayed | Check without data |

**Rule:** If a tab is broken, fix it before moving on. Do not log and defer.

### 0C — PROJECT_STRUCTURE files (all 4 repos)

The code-review-graph MCP builds its index from PROJECT_STRUCTURE.md. Stale files = stale MCP context = wasted code review effort. Update these before Phase 2 code review.

Each file should accurately describe: repo purpose, key modules, critical design decisions, current test count, known gaps/TODOs, what not to change and why.

| Repo | Key facts to include |
|---|---|
| graph-attention-engine-v50 | GAE library Apache 2.0 v0.7.0, 478 tests. ProfileScorer A=4 (escalate/investigate/suppress/monitor). DiagonalKernel default noise_ratio>1.5. KernelSelector rolling 100-window. ReferralEngine VETO independent of scoring. OverrideDetector stub (v6.5, data-gated). AMBER auto-pause. η_override=0.01. θ_min=0.467. |
| gen-ai-roi-demo-v4-v50 | SOC Copilot 280 tests. FastAPI backend, React/TypeScript/Vite frontend, Neo4j. 5 tabs. IKS module-level functions (κ*=0.20). 24 deterministic NL templates. ReferralRules R1-R7 (R2+R7 need Neo4j wiring — sequence_count/cross_category_count default 0). DEC-DEC prefix bug Tab 4. Shadow mode. Auto-approve. |
| ci-platform | 73 tests. P28 6-phase deployment qualification. DeploymentQualifier GREEN/AMBER/RED (L2 thresholds only — DiagonalKernel thresholds pending 0A-2). SAML auth. PII redaction 5 patterns. Entity resolution 3-pass. Sentinel/Splunk connectors. |
| cross-graph-experiments | ~104 experiments Series 1-13. Harness run_harness.py (θ_min stale at 0.434 — fix 0A-4). S2PDomainConfig d=8. Key results: V-MV-KERNEL 390 cells, referral Series 13 4 experiments. |

### 0D — Remaining GTM docs (C2-C5)

These complete the GTM P0/P1 batch and are independent of experiment outcomes.

| Doc | Content |
|---|---|
| C2: Security Posture | Architecture: on-premise, no cloud egress. SAML 2.0. PII redaction (5 patterns, 3 strategies). Evidence Ledger hash-chained. Kernel provenance. Checkpoint/rollback. SOC 2 Type I readiness self-assessment. |
| C3: VSQ Pre-fill | Standard VSQ questions pre-answered: encryption, access control, incident response, AI/ML specifics (EU AI Act Art. 9 N3 risk disclosed), third-party risk (zero sub-processors base deployment). |
| C4: Loom Script | 3-minute demo flow: alert → factor breakdown → IKS → auto-approve → shadow → ROI → consistency claim. Uses current validated numbers. |
| C5: LinkedIn / Outreach | 150-word post + 100-word cold email. CISO target. CLAIM-31 consistency (unconditional). No unqualified accuracy numbers. |

---

## PHASE 1: EXPERIMENT + DESIGN GAP PASS
*No new features start until this phase is complete.*
*Rule: if an experiment forces a claim to weaken, identify the missing design capability and add it to Phase 2 scope. Do not soften language without a concrete design fix.*
*All experiments use LLM-judge synthetic data unless a specific real-data source is named. Synthetic data is the development process — not a workaround.*

### Batch 1 — Highest architectural risk (run first, others depend on results)

| # | Experiment | What it tests | If claim weakens, design gap is |
|---|---|---|---|
| 1 | **V-CGA-FROZEN** | Does graph enrichment lift frozen scorer accuracy? 50 seeds, 2 conditions, paired t-test p<0.01. 3 metrics: σ_per_factor reduction, cold-start convergence speed, IKS trajectory. | "Second compounding pathway" doesn't exist architecturally. Need to build enrichment-to-centroid bridge (GraphAttentionBridge stub exists, needs wiring) before claiming "graph compounds while centroids wait." Design fix: specify bridge protocol, add to Phase 3 scope. |
| 2 | **V-ENRICHMENT-NEGATIVE** | Can graph enrichment hurt accuracy? 2 personas with contradictory threat intel (stale CVEs, retracted advisories). 20 seeds, worst-case 95% CI. | Enrichment needs quality filter on graph write path. Design fix: add source trust score gate before σ update — low-trust sources quarantined. |

**Gate:** If V-CGA-FROZEN FAILS — "graph compounds while centroids wait" becomes a forward-looking design goal, not a current claim. Adj. C narrative is removed from all current GTM materials until the bridge is built and validated. This is a product gap, not a messaging gap.

### Batch 2 — Validate existing architecture (run after Batch 1)

| # | Experiment | What it validates | Design gap if fails |
|---|---|---|---|
| 3 | **V-SIM** | P28 pipeline end-to-end on 9 LLM-judge streams (3 industries × 3 judges). KernelSelector correct ≥8/9. Deployment gate GREEN/AMBER/RED correct ≥8/9. | KernelSelector rule needs domain-specific tuning. Currently: ratio>1.5→diagonal. May need industry-prior adjustment. |
| 4 | **EXP-S2-REPRO at A=4** | Poisoning resilience at A=4. Original ran at A=5. 60 runs (20 seeds × 3 arms). Gate: max degradation ≤0.20pp. | Conservation law requires tighter threshold at A=4 geometry. |
| 5 | **TD-034 LLM-judge streams** | τ=0.08 holds on realistic factor distributions (bimodal threat_intel, right-skewed pattern_history). SOC validation + S2P τ sweep. | Per-deployment τ sweep becomes mandatory (P28 already supports this — likely contained). |

### Batch 3 — Free analysis on existing data (no new harness runs)

These run on the 390-cell factorial already complete. Each takes hours of analysis, not days of new computation.

| # | Analysis | Output |
|---|---|---|
| 6 | **V-MV-RISK** | Should continuous R score replace discrete deployment gate? Fit R = f(σ, V, q̄, kernel, n) on factorial trajectories. AUC > 0.85 required to promote. |
| 7 | **V-MV-CONVERGENCE** | N_half = f(σ, V, q̄, kernel). Blocks convergence calendar feature. R² > 0.80 required. |
| 8 | **V-MV-CONSERVATION** | Var(q) false alarm rate on factorial data. Precision > 0.70, Recall > 0.80 required for Var(q) to become gating (vs logged-only). |
| 9 | **V-UCL-VALUE** | Regress IKS trajectory on graph statistics (node count, edge count, entity resolution matches). R² > 0.50 → UCL has independent predictive claim. |
| 10 | **Gap G4 interaction mini-factorial** | (q̄ low/high) × (team 3/8) × (campaign yes/no). 8 cells × 20 seeds = 160 runs. Any interaction >5pp → document as product boundary. |

### Batch 4 — Safety validation (can run in parallel with Batch 3)

| # | Experiment | What it tests | Stakes |
|---|---|---|---|
| 11 | **P4-F (adversarial analyst)** | q̄ degrades from 0.85 to 0.40 gradually over 500 decisions. Does ConservationMonitor detect before >5pp centroid damage? 30 seeds. | If detection latency p90 > 50 decisions before damage reaches 5pp: tighten conservation thresholds. |
| 12 | **P4-COMPLACENCY** | Quality degrades while override rate stays constant. Does Var(q) catch it before α·q·V drops? 30 seeds. | If false negative rate > 10%: Var(q) becomes gating condition, not optional logging. |

### Claims registry update after each batch

After each batch completes: update claims_registry → update design_gap_analysis → update GTM materials.

**Hard rule:** A claim stays at its current strength until a design fix is shipped, not just designed. "We're planning to fix this" does not allow a claim to stay unconditional.

---

## PHASE 2: CODE REVIEW PASS

*Prerequisite: Phase 0C (PROJECT_STRUCTURE files) complete. code-review-graph MCP active.*
*No new features until this phase is complete.*

### Review scope

Use the code-review-graph MCP to systematically review all 4 repos. The MCP provides 6.8× token reduction on reviews — use it for full-repo analysis, not just targeted searches.

| Focus area | What to look for |
|---|---|
| API contract consistency | GAE ↔ SOC ↔ ci-platform interface contracts match design docs |
| Integration gaps | Calls between repos that silently default (like R2/R7 → 0) |
| Test coverage | Integration tests between repos (not just unit tests within) |
| Stale TODOs | TODOs that became settled design decisions but weren't cleaned up |
| Safety invariants | μ ∈ [0,1]^d clip on every update path. η_override=0.01 on every override path. No σ into update(). |
| Design doc vs code drift | Any code that doesn't match what the design docs specify |

### Fix criteria

- Safety invariant violations: fix immediately, add test.
- API contract gaps: fix before Phase 3 features that depend on them.
- Coverage gaps: add integration tests, especially cross-repo.
- Stale TODOs: resolve (fix or close), document decision.

---

## PHASE 3: POST-MVP FEATURES
*Sequenced strictly by customer value. Experiments in Phase 1 may reorder or add items.*
*Batch 1 results from Phase 1 gate items 1 and 2 below.*

| Priority | Feature | Value | Blocker | Effort |
|---|---|---|---|---|
| **1** | **Attack chain correlation (F6)** | "These 17 alerts are one campaign." Tier 1→Tier 2 pricing unlock. The single strongest demo moment that doesn't exist yet. | None (V-CGA-FROZEN result may affect enrichment design but not basic attack chain schema) | Large (2-3 weeks): multi-hop schema, campaign entity, ATT&CK progression |
| **2** | **Analyst benchmarking report (F9)** | Shadow data already being collected. AI vs analyst comparison. Improves over time. "Day 90: matched 91%, caught 12 TPs analysts missed." | Shadow mode (✅ built). Needs 30+ days shadow data for first deployment. | Medium (1 week) |
| **3** | **Tab 5 Executive Narrative Sections 1+2 (F12)** | What Changed / What Was Discovered / What System Now Knows. Deterministic, no GATE-D needed. CFO-quotable. PDF export. | None | Medium (1 week) |
| **4** | **Multi-SIEM abstraction (F5)** | Splunk + Sentinel bidirectional. 30% TAM → 60%. | SourceConnectorProtocol already exists | Large (1-2 weeks) |
| **5** | **Override learning activation** | OverrideDetector fires at ≥50 production override positives. Architecture exists (stub). Adds the 20.7% emergent referral fraction. | ≥50 positive examples in production OR synthetic generation of override history via LLM-judge | Small (3 days, architecture complete) |
| **6** | **S2P copilot** | "Same engine, different domain." Platform proof. Pricing unlock. | V-CGA-FROZEN result + S2P-V3B τ calibration (Phase 1 Batch 2 item 5) + repo creation | Medium (1 week after experiments) |
| **7** | **NHI behavioral baselines (F7)** | Service accounts, API keys, AI agents. 82:1 machine:human ratio. | F6 (attack chain schema) recommended first | Large (2 weeks) |
| **8** | **Flash Tier (streaming ingestion)** | Kafka/Kinesis fast path for known patterns. | Infrastructure (Phase 4 prerequisite) | Large |

### Experiments-informed additions to Phase 3

These slots are reserved for design fixes that Phase 1 experiments may generate:

- **If V-CGA-FROZEN fails:** GraphAttentionBridge specification and implementation becomes P0 in Phase 3. "Second compounding pathway" is the widest innovation-claim gap — it needs a real answer.
- **If V-ENRICHMENT-NEGATIVE shows degradation >3pp:** Source trust score gate on graph write path.
- **If P4-COMPLACENCY false negative rate >10%:** Var(q) gating mechanism (currently logged only).
- **If V-MV-CONVERGENCE R² > 0.80:** Convergence calendar feature (L-08) unblocked.

---

## PHASE 4: REMAINING GTM + DOCUMENTATION

Items from MAP v2 Phase 4 not yet done:

| # | Item | Effort | Notes |
|---|---|---|---|
| Build vs Buy Brief | ✅ Done | — | Written this session |
| Microsoft Threat Analysis | ✅ Done | — | Written this session |
| Regulatory Tailwind Map | ✅ Done | — | Written this session |
| DPA Template | ✅ Done | — | Written this session |
| 90-Day Pilot Playbook | ✅ Done | — | Written this session |
| Three Unconditional Claims (one-pager) | 0.5 day | Consistency + Readability + Ownership. No qualifiers. |
| Four Clocks Investor Brief | 0.5 day | Deck Slide 30 + Stryker Figure 4. |
| Stryker-style analysis template | 0.5 day | Repeatable 48hr process for public incidents. |
| Competitor comparison series | 1 day | Microsoft, CrowdStrike, Charlotte AI, generic LLM-native. |
| Open Source GTM Playbook | 1 day | GAE v0.7.0, PyPI, 478 tests. Developer funnel. |
| Blog v9 update | 1 day | 12 kernel changes + A=4 + referral architecture. |
| 90-Day Pilot Playbook | ✅ Done | — | Written this session |

---

## PHASE 5: INFRASTRUCTURE (last)

Nothing in Phases 0-4 depends on this. Do not start until Phase 3 MVP feature set is stable.

| Item | Effort | Notes |
|---|---|---|
| PostgreSQL + AGE migration | 2 weeks | Neo4j → PostgreSQL 16 + Apache AGE. Cypher preserved via openCypher. |
| VPS production deployment | 1 week | Docker Compose hardening. Health checks. Secret management. |
| Kafka/Kinesis streaming | 1 week | Real-time alert ingestion for Flash Tier (Phase 3 item 8). |
| CI/CD pipeline | 3 days | GitHub Actions: pytest + lint + mypy + security scan. Auto-PyPI publish. |
| Monitoring + observability | 1 week | Prometheus, Grafana, conservation law violation alerts. |

---

## SYNTHETIC DATA POLICY

Synthetic data via LLM-judge and web scraping is the canonical development method. It is not a workaround until real customers exist — it is how this product is built.

**LLM-judge is used for:**
- Experiment validation (every experiment in Phase 1)
- UI/frontend testing data generation (realistic alert streams, varied factor distributions)
- Claim validation (generating adversarial scenarios to stress-test claims before a real customer can)
- GTM materials (scenario-based demos, Loom script walkthroughs)
- S2P domain bootstrap (procurement alerts, supplier profiles)

**Web scraping is used for:**
- CISA KEV daily pull (already built, EXP-S5a ✅)
- NVD CVE feed (already built)
- Public incident reconstruction for Stryker-style analyses

**The co-agent (roadmap session) supports:**
- Design issue discussion when architecture decisions are unclear
- Synthetic data generation for specific experiment needs
- Review of experiment designs before running

**Rule:** Never write "pending real customer data" in any document. If a validation requires real data and no synthetic proxy exists, design the synthetic proxy first.

---

## METRICS — WHAT DONE LOOKS LIKE

| Phase | Done When |
|---|---|
| Phase 0 | All 5 tabs visually validated and working. R2/R7 fire in production. P28 DiagonalKernel thresholds correct. DEC-DEC fixed. PROJECT_STRUCTURE files accurate. C2-C5 GTM docs written. |
| Phase 1 | All 12 experiments complete with statistical conclusions. Claims registry updated. Design gap register updated. No claim is weaker than Phase 0 without a concrete design fix in Phase 3 queue. |
| Phase 2 | Code review complete across all 4 repos. Safety invariants verified by test. API contracts match design docs. Integration tests between repos exist. |
| Phase 3 | Attack chains demo-able (F6). Analyst benchmarking works (F9). Tab 5 Sections 1+2 complete (F12). Multi-SIEM connected (F5). IKS trajectory on live data. |
| MVP | A CISO can sit down for 45 minutes, see all 10 MVP items, and say "I understand what this does and I want to pilot it." |
| Post-MVP | >1,200 total tests. >130 experiments. All P0 design gaps closed. GTM batch complete. |

---

## v2 → v3 CHANGE LOG

| Change | Source | What Changed |
|---|---|---|
| Version labels removed | Point 1 | No v6/v6.5/v7 anywhere. MVP / Post-MVP. |
| Experiments front-loaded as discrete Phase 1 | Point 2 | Phase 1 completes before any Phase 3 feature starts. |
| Claims weakening = design gap | Point 3 | V-CGA-FROZEN failure triggers GraphAttentionBridge spec, not language narrowing. Hard rule added. |
| PostgreSQL/VPS moved to Phase 5 (last) | Point 4 | Nothing in Phases 0-4 depends on it. |
| Code review pass added as Phase 2 | Point 5 | PROJECT_STRUCTURE files in Phase 0C. MCP-based review in Phase 2 before new features. |
| PROJECT_STRUCTURE files added to Phase 0 | Point 6 | Prerequisite for MCP code review. 4 repos. |
| Synthetic data policy section added | Point 2+3 | Canonical statement. No "pending real customer data." Co-agent role defined. |
| Phase 0 immediate fixes consolidated | This session | 0A-1 through 0A-5 (R2/R7, P28, DEC-DEC, θ_min, Adj.G). All ≤50 lines each. |
| GTM P0 batch marked done | This session | DPA, Pilot Playbook, Build vs Buy, Microsoft Analysis, Regulatory Tailwind. |
| Document fixes marked done | This session | 8 confidence-gate-only instances fixed. §22.6 committed (first time). |
| MAP v2 Phase 3 feature list resequenced | Points 1+2 | Attack chain first (Tier 2 pricing). S2P after experiments. Override learning after data. |
| 86 action items → structured phases | All points | Clarity over completeness. |

---

*Master Action Plan v3 · March 23, 2026*
*"Experiments before features. Synthetic data is the process. Claims that weaken are design gaps."*
*"There is no such thing as waiting for real customer data."*
