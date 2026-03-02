# SOC Copilot — Backlog v22

**Date:** March 1, 2026
**Status:** v4.1 tagged. PM session complete. v4.5 prompts finalized with data collection instrumentation. GAE-CAL-1 ready to execute.
**Architecture:** Three repos — graph-attention-engine / ci-platform / soc-copilot
**Design docs:** gae_design_v7, soc_copilot_design_v3, ci_platform_design_v3, gap_analysis_v4, design_decisions_v1

> **Changes from v21:**
> (1) **Data collection instrumentation** on SIM-1 (experiment log), SIM-2 (download button), SIM-3a (ground_truth_action), NAR-2 (factor attribution). Simulation is both feature and experimentation platform.
> (2) **Phase B split:** NAR-1/NAR-2 separated from TAB2-1/TAB2-2. Narrative ships early; Tab 2 rewire deferred within v4.5.
> (3) **HC-1 added** (healthcare polish) — after Phase B, deprioritized below math/simulation core.
> (4) **Three research gaps** tracked: R1 (convergence ≠ correctness), R2 (math-algorithm integration), R3 (error-driven discovery).
> (5) **GAE backward compat NOT required** for v4.5.
> (6) **Phase C prerequisite added:** error-driven discovery design work before DISC prompts.
> (7) **INOVA context** captured but does NOT drive architecture. Math quality drives architecture.
> (8) **Execution order revised:** SIM-2 moved after SIM-3a/3b/4 (backend first, frontend last).

---

## SECTION A: Completed Work

### v2.0–v3.2 ✅ (soc-copilot repo)
### v4.0 Phase 1: 13 prompts ✅ — REAL connectors
### v4.0 Phase 5: 8 prompts ✅ — UI (data replaced by GAE)
### v4.1 GAE Foundation ✅
- GAE library: 177 tests green (70 core + 107 generic domain suite)
- SOC factors: 6 FactorComputers (4 Cypher traversal + 2 property reads)
- Full pipeline: orchestrator → score_entity → Decision nodes → outcome → weight learning
- 10-cycle compounding gate: 7/7 PASS (28.6x asymmetry measured)
- OPUS-R1: clean. 3 naming fixes applied.
- Live charts: Weight Evolution, Confidence Trajectory, Before/After, Trust Curve
- Cold-start fix: 20s → 2.5s. Convergence: min-20 threshold. Decision-id fix.

### Design & Analysis ✅
- All design docs updated (gae_design_v7, soc_copilot_design_v3, ci_platform_design_v3)
- Gap analysis v3 — 47 tracked items, 7 gaps (D1-D7)
- Design decisions v1 — 8 architectural issues resolved
- Roadmap v6, technology portfolio map v1.4
- Session continuation v19
- PM session complete — MVP strategy, math quality as CSF

---

## SECTION B: v4.5 — "Make It Real"

### Design Philosophy

Close the credibility gaps between what the blogs claim and what the product proves. Math quality is the critical success factor. Simulation is both a feature (proof of compounding) and an experimentation platform (data for v5.0 evaluation). INOVA context (healthcare, Health-ISAC) is kept but deprioritized below core math/simulation work.

### GAE Preamble (GAE repo — 2 prompts)

Must land before Phase A. GAE backward compat NOT required — refactor freely.

| Prompt | What | Gate |
|---|---|---|
| **GAE-CAL-1** | CalibrationProfile dataclass + LearningState refactor. No backward compat needed. `soc_calibration_profile()` + `s2p_calibration_profile()`. | Existing tests pass (refactored) + 6 new |
| **GAE-CAL-2** | Per-factor decay: epsilon_vector from decay_class_rates × factor name mapping. Three-layer design. | All prior + 4 new tests pass |
| **Opus Review 1** | Review GAE-CAL-1 + GAE-CAL-2. Check math correctness of per-factor decay. | PASS / NEEDS FIXES |

GAE-CAL-3 (domain schema) deferred to v5.0.

### Phase A: Simulation Mode + Alert Corpus (6 prompts, SOC repo)

**Goal:** Product proves compounding in real-time. Gaps 1-3 closed. Data collection instrumented.

| Prompt | What | Data Collection | Gate |
|---|---|---|---|
| **SIM-FIX** | StateManager: atomic soft/hard reset. POST /api/admin/reset. TD-026. | — | Reset 200. GAE at priors after soft. |
| **SIM-1** | SimulationOrchestrator backend. Batch N alerts, same GAE pipeline, Bernoulli oracle, by_category accuracy. | **Structured experiment log** per decision: factor_vector, W_snapshot, action, confidence, outcome, correct | 10-decision API test |
| **SIM-3a** | Alert pool: 15-20 alerts, 5 categories, different dominant factors per category. | **ground_truth_action** + **dominant_factors** metadata per alert | 5 categories × 3-4 alerts |
| **SIM-3b** | Wire pool into orchestrator. Category-specific Bernoulli rates. PatternHistory by category. | **accuracy_vs_ground_truth** in results | Simulation across all categories |
| **SIM-4** | ATT&CK technique IDs on all alerts. Tab 3: badge. Tab 1: tactic grouping. | — | Technique IDs visible |
| **SIM-2** | Frontend: simulation panel, category learning curve, progress bar, speed control. | **"Download Experiment Log" button** (JSON export) | Charts update. Lines diverge. |
| **Opus Review 2** | Phase A review. 50-decision simulation gate. | — | Clear learning in charts |

**Phase A Gate:** 50-decision simulation → clear learning. Category curves diverge. Accuracy vs ground truth reported. Record 60-second screen capture.

### Phase B: Narrative (2 prompts, SOC repo — was 4)

**Goal:** CISOs hear their language. Gap-4 closed.

| Prompt | What | Data Collection | Gate |
|---|---|---|---|
| **NAR-1** | NarrativeProvider protocol + TemplateNarrativeProvider + OllamaNarrativeProvider. Graceful degradation. NARRATIVE_PROVIDER env config. | — | Template generates for any alert |
| **NAR-2** | Tab 3 narrative panel: 3-5 sentence narrative with "calibrated from N outcomes" line. | **Factor attribution**: top/bottom factors in narrative | Narrative appears with calibration line |

**Phase B Gate:** Narrative with calibration line. **Record Loom v2.**

### HC-1: Healthcare Polish (1 prompt, SOC repo — NEW, DEPRIORITIZED)

| Prompt | What | Gate |
|---|---|---|
| **HC-1** | (a) Healthcare alert categories in pool (if not already in SIM-3a). (b) 3-5 Health-ISAC indicators as seed data. (c) Healthcare ROI defaults. (d) 1-2 HIPAA policy rules. | Health-ISAC visible in Tab 1. Healthcare ROI loads. |

Runs after Phase B. Additive, not structural.

### Tab 2 Rewire (2 prompts, SOC repo — DEFERRED within v4.5)

| Prompt | What | Gate |
|---|---|---|
| **TAB2-1** | Rewire Tab 2 to GAE pipeline. Remove agent.decide(). Close TD-019. | Tab 2 uses GAE end-to-end |
| **TAB2-2** | AgentEvolver shows real GAE data. execute_action events fire. Close TD-020. | No dual decision paths |

Not demo-blocking. Tech debt cleanup.

### Phase C: Cross-Graph Discovery (6 prompts, SOC repo, HARD GATED)

**PREREQUISITE:** Error-driven discovery design session. Current Eq. 6 finds similarity; may need relevance-to-decision-quality objective. Design work before implementation.

| Prompt | What | Gate |
|---|---|---|
| **DISC-1** | EmbeddingProvider. PropertyEmbeddingProvider (numpy-only). | Embeddings produced |
| **DISC-2** | Cross-graph attention sweep (Eq. 6 — possibly revised). | Sweep runs. Candidates extracted. |
| **DISC-3** | Discovery → expand_weight_matrix. New factor registered. | Discovery triggers W expansion |
| **DISC-4** | Scenario seed data: 5 planted discovery patterns. | Patterns in graph |
| **DISC-5** | Tab 4 discovery panel. | UI shows discovery |
| **GATE-B3** | F1 > 0.2 against planted patterns. | Pass or document honestly |

**HARD GATE:** Pass → ship Axis 3. Fail → document honestly.

### v4.5 Prompt Summary (Revised)

| Phase | Prompts | Reviews | Total |
|---|---|---|---|
| GAE Preamble | 2 | 1 | 3 |
| Phase A (Simulation) | 6 | 1 | 7 |
| Phase B (Narrative) | 2 | 0 | 2 |
| HC-1 (Healthcare) | 1 | 0 | 1 |
| Tab 2 Rewire | 2 | 0 | 2 |
| Phase C (Discovery) | 6 | 0 | 6 |
| **v4.5 Total** | **19** | **2** | **21** |
| **To Loom v2** | **10** | **2** | **12** |

---

## SECTION B2: v5.0 — "GAE as Platform + SOC as Product" (unchanged)

### Three-Repo Milestone

| Repo | Prompts | Theme |
|---|---|---|
| GAE v0.2.0 | 7 | Platform breadth: evaluation, ablation, judgment, schema, API surface, example, docs |
| ci-platform v0.1.0 | 3-5 | First real code: DomainConfig ABC, StateManager, schema parser, ContractChecker |
| SOC copilot | 8 | Product polish: realistic data, evaluation, ROI, judgment display, situation classification |
| **v5.0 Total** | **18-20** | |

### GAE v5.0 Prompts

| Prompt | Creates |
|---|---|
| GAE-EVAL-1 | evaluation.py: EvaluationScenario, run_evaluation, EvaluationReport |
| GAE-JUDG-1 | judgment.py: InstitutionalJudgmentMetrics |
| GAE-ABL-1 | ablation.py: four baselines (static, flat learning, no graph, full system) |
| GAE-ENG-1 | Public API surface: clean __init__.py, import lint |
| GAE-ENG-2 | examples/minimal_domain/: Hello World DomainConfig (~50 lines) |
| GAE-ENG-3 | Independent engine test suite (no SOC imports) |
| GAE-DOC-1 | GAE Users Guide (README, concepts, getting started) |

**v5.0 GAE priority note:** GAE-ENG-2 and GAE-DOC-1 are critical for the open-source strategy. They make the engine accessible to researchers who can run experiments against it.

### ci-platform v5.0 Prompts (unchanged)

| Prompt | Creates |
|---|---|
| PLAT-1 | domains/base.py (DomainConfig ABC), platform/domain_registry.py |
| PLAT-2 | platform/schema/parser.py, platform/schema/contract_checker.py |
| PLAT-3 | platform/state_manager.py (extracted from SOC) |
| PLAT-4 (optional) | Startup validation hook |

### SOC v5.0 Prompts (unchanged)

| Prompt | Creates |
|---|---|
| SEED-2 | Realistic seed data: 200+ users, power-law alerts, 10% missing properties |
| EVAL-1-SOC | 30-40 evaluation scenarios from ATT&CK × graph context |
| EVAL-2-SOC | Run evaluation + produce report |
| ECON-1 | ROI dashboard (analyst hours, auto-triage rate, MTTR) |
| JUDG-1-SOC | Institutional judgment display on Tab 4 |
| A1-FIX | Tune discount_strength from evaluation results |
| SIT-1 | Scoring-based situation classification |
| SIT-2 | Classification learning from analyst corrections |

---

## SECTION C: Scorecard Credibility Guardrails (Updated)

### What We CAN Claim at v4.1

| Claim | Evidence |
|---|---|
| Mathematical foundation published | Blog with 4 experiments |
| Scoring engine implements Eq. 4 | GAE library (open-source, 177 tests) |
| 20:1 asymmetric trust | 28.6x measured |
| Compounding visible in real time | 4 live charts from real GAE data |
| Domain-agnostic architecture | 177 tests across 4 domains |
| Opus-reviewed architecture | OPUS-R1 passed |

### What We Can Claim After v4.5 Phase A

| Claim | Evidence |
|---|---|
| "Watch 50 decisions compound in 30 seconds" | Simulation mode |
| ATT&CK-aligned alert taxonomy | Technique IDs on 15-20 alerts |
| Different categories learn at different rates | Category learning curve chart |
| Accuracy against known-correct decisions: X% | ground_truth_action comparison (NEW) |

### What We Can Claim After v4.5 Phase B

| Claim | Evidence |
|---|---|
| Investigation narrative with calibration history | "Calibrated from N verified outcomes" |
| Factor attribution in natural language | Top/bottom factor identification (NEW) |

### What We Can Claim After v5.0

| Claim | Evidence |
|---|---|
| Ground truth evaluation: X% accuracy | EvaluationReport |
| Ablation: full system beats all baselines | AblationReport (4 baselines) |
| Math contribution quantified vs. algorithmic loops | Ablation comparison (NEW — addresses R2) |
| Institutional Judgment Score: N/100 | judgment_score after 200 decisions |
| ROI: N analyst hours saved per month | ROI dashboard |

### What We CANNOT Claim Until Phase C Gate Passes

| Claim | Requires |
|---|---|
| "New scoring dimensions discovered autonomously" | GATE-B3 pass |
| Axis 3 (Capability Extension) proved live | GATE-B3 pass |
| Cross-graph discovery at scale | GATE-B3 pass |

---

## SECTION D: Tech Debt (Updated)

| ID | Severity | Issue | Fix When | Status |
|---|---|---|---|---|
| TD-014 | Low | TimeAnomaly reads properties | v5.5 | Open |
| TD-015 | Low | DeviceTrust reads properties | v5.5 | Open |
| TD-017 | High | Hardening state not fully persisted | v5.0 | Open |
| TD-018 | Med | Dual persistence paths | v5.0 | Open |
| TD-019 | Med | Dual decision paths (agent.decide vs GAE) | **v4.5 Tab 2 rewire (TAB2-1)** | Open |
| TD-020 | Med | execute_action writes graph without events | **v4.5 Tab 2 rewire (TAB2-2)** | Open |
| TD-023 | Low | Backward-compat block in soc/factors.py | v5.5 | Open |
| TD-024 | Low | Two LearningState classes | v5.0 | Open |
| TD-025 | Med | No CalibrationProfile | **v4.5 GAE preamble (GAE-CAL-1)** | Open |
| TD-026 | Med | Audit/GAE sync on reset | **v4.5 Phase A (SIM-FIX)** | Open |

---

## SECTION E: Outreach Track (Updated)

| Item | Status | Blocked By | Target |
|---|---|---|---|
| Demo blurb update (simulation + charts) | ❌ Pending | Phase A complete | After Phase A (single update, not two) |
| **Loom v2 recording** | ❌ Pending | **Phase B complete** | After Phase B |
| LinkedIn post: simulation mode proof | ❌ Pending | Phase A complete | After Phase A |
| LinkedIn post: investigation narrative | ❌ Pending | Phase B complete | After Phase B |
| Outreach emails v7 (simulation proof) | ❌ Pending | Phase A complete | After Phase A |
| Blog: CI 5.0 (if discovery works) | ❌ Pending | Phase C gate | If B3 passes |
| Blog: GAE calibration guide | ❌ Pending | v5.0 GAE-DOC-1 | After v5.0 |
| Positioning graphics (NBP format) | ❌ Pending | — | Can start anytime |
| **INOVA leave-behind doc** | ❌ Pending | Phase B complete | After Loom v2 |

---

## SECTION F: Priority Queue (Revised)

| Priority | Item | Status |
|---|---|---|
| **P0** | **GAE-CAL-1 → GAE-CAL-2 → Opus Review (GAE repo)** | **NEXT** |
| **P0** | **Phase A: SIM-FIX → SIM-1 → SIM-3a → SIM-3b → SIM-4 → SIM-2 → Opus Review** | **After preamble** |
| P1 | Phase B: NAR-1 → NAR-2 | After Phase A |
| P1 | Loom v2 recording | After Phase B |
| P2 | HC-1 (healthcare polish) | After Phase B |
| P2 | TAB2-1, TAB2-2 (Tab 2 rewire) | After Phase B |
| P2 | Outreach: demo blurb, LinkedIn, emails v7 | After Phase A |
| P3 | Error-driven discovery design session | Before Phase C |
| P3 | Phase C: DISC-1 through GATE-B3 | After design session |
| P4 | v5.0 GAE prompts (7) | After v4.5 tagged |
| P4 | v5.0 ci-platform prompts (3-5) | After v4.5 tagged |
| P4 | v5.0 SOC prompts (8) | After v4.5 tagged |

---

## SECTION G: Research Questions (NEW)

These inform v5.0+ design but are tracked here for visibility.

| ID | Question | First Data Point | Full Answer |
|---|---|---|---|
| R1 | Does Hebbian update converge to correct decisions? | v4.5 Phase A (ground_truth comparison) | v5.0 evaluation (EVAL-1) |
| R2 | How much do 3 loops contribute vs. the math? | v5.0 ablation (GAE-ABL-1) | Ongoing experimentation |
| R3 | Should discovery be error-driven, not similarity-driven? | Design session before Phase C | v5.5+ implementation |

---

## SECTION H: Version History

| Version | Date | Changes |
|---|---|---|
| 1.0–19.0 | Feb 10–28 | Through v4.1 pre-tag |
| 20.0 | Mar 1 | v4.1 tagged. Gap analysis. v4.5 redesigned. |
| 21.0 | Mar 1 | Design decisions (8 issues). GAE preamble. Phase D eliminated. v5.0 added. |
| **22.0** | **Mar 1** | **PM session complete. Data collection instrumentation on 4 prompts. Phase B split (narrative vs Tab 2). HC-1 added (deprioritized). 3 research gaps (R1-R3). GAE backward compat dropped. Error-driven discovery design prerequisite for Phase C. Execution order revised (backend before frontend). 12 units to Loom v2 readiness.** |

---

*SOC Copilot — Backlog v22 | March 1, 2026*
*GAE-CAL-1 NEXT → Phase A (simulation + instrumentation) → Phase B (narrative) → HC-1 → Tab 2 → Phase C (gated).*
*v4.5: 19 prompts + 2 reviews = 21 units. 12 to Loom v2. Math quality is the critical success factor.*
*"The moat is the graph, not the model. The math must prove it."*
