# SOC Copilot — Design Document v5.8

**Date:** April 29, 2026
**Version:** 5.8 (v5.7 + Framework v4 integration: TwoPhaseScorer display, three-channel decomposition, batch pipeline triage flow, defense-in-depth, profile state, ~2,340 tests)
**Authority:** claims_registry_v10.0 · MAP v5.51 · framework v4 (post-judge-review)
**Status:** v5.5 COMPLETE. Phase 0 ✅ Phase 1 ✅ Phase 2 ✅ Phase 3 Priority 1 ✅. Loom demo v1 unblocked. 995 GAE tests, 900 SOC backend + 183 E2E tests confirmed, 174 ci-platform tests. ~295 experiments complete.
**Repository:** soc-copilot (proprietary)
**Theme:** "Your tools, our decisions. Your environment, your intelligence."
**Companion repos:**
- graph-attention-engine (Apache 2.0, **995 tests**). Design: `gae_design_v10_2.md`
- ci-platform (Apache 2.0, **102 tests** — connectors, onboarding, qualification, entity resolution, PII, SAML). GitHub: ArindamBanerji/ci-platform
- cross-graph-experiments (~295 experiments, persona sweeps, factorial, SVM, Batch G). Catalog: `experiment_reference_catalog_v2.md` (update pending)

**Git remotes:**
- SOC copilot: git@github.com:ArindamBanerji/gen-ai-roi-demo.git (v5.0-dev branch, tag v5.0)
- GAE library: graph-attention-engine (995 tests)
- ci-platform: git@github.com:ArindamBanerji/ci-platform.git (174 tests)
- Experiments: git@github.com:ArindamBanerji/cross-graph-experiments.git

> **This document absorbs and supersedes** all prior soc_copilot_design versions (v1 through v5.4). See Appendix C.

> **Changes from v5.7 → v5.8 (April 29, 2026 — Framework v4 integration):**
>
> Driven by framework v4 (post-judge-review, 5 LLM judges, ~115 compounding experiments). No existing v5.7 behavior changed. All additions are opt-in (ContinuousStrategy remains default).
>
> **(1)** §9.1: Eq. 4-twophase added. Shrinkage-weighted scoring: w̃ = α × w_DK + (1-α).
> **(2)** §10.3: LearningStatePanel spec for Tab 3. Phase indicator, α display, DK weight visualization, novelty sparkline. Hidden when ContinuousStrategy.
> **(3)** Tab 4: Three-channel decomposition panel. Error budget. Per-channel contribution estimates.
> **(4)** §11: Triage flow updated for Phase 1/Phase 2 transition and batch pipeline position.
> **(5)** §14: SOCDomainConfig.get_learning_strategy() added.
> **(6)** §13: Claude Code rules for framework v4 constraints.
> **(7)** Conservation law q: all instances updated to "rolling verified accuracy over last 400 decisions."
> **(8)** Five compounding pathways (was four). Pathway 2: scorer metric learning.
> **(9)** Two new endpoints: /api/triage/learning-state, /api/compounding/channel-decomposition.
> **(10)** Three new feature IDs: F16 (phase display), F17 (channel decomposition), F18 (batch observability).
> **(11)** Test counts: ~2,340 total. GAE 995. SOC 900. E2E 183. ~295 experiments.
> GAE-specific content lives in `gae_design_v10`. Platform content lives in ci-platform repo.

---

> **Changes v5.5.2 → v5.5.3 (March 25, 2026 — Phase 1 closure):**
>
> **(27) Header updated.** Test counts: GAE 478→517, SOC 280→288, ci-platform 73→93.
>     Experiments ~104→~130. Status reflects Phase 0 ✅ Phase 1 ✅.
>
> **(28) §1.1 dependency graph updated.** GAE 478→517 tests, ci-platform 73→174 tests.
>
> **(29) §1.4 architecture philosophy reference updated.** `architecture_philosophy_v1_3.md`
>     → `architecture_philosophy_v4.1.md`. ACCP bounded hyperagent paragraph added
>     to §1.4 Two Levels of Institutional Judgment: Loop 1 (task agent), Loop 2 (meta
>     agent), Loop 3 (fixed governance boundary). Three Phase 3 design gaps (H1, H2, H3).
>
> **(30) NEW §5.6: PatternHistoryFactorComputer (W2 read path).** The W2 compounding
>     flywheel read path (CLAIM-W2: +10.13pp, p=0.0002). Recency-weighted
>     TRIGGERED_EVOLUTION edges. Fallback=0.40. FACTOR_INDEX=4 only.
>     Distinguishes from §5.2 PatternHistoryFactor (legacy decision accuracy read path).
>
> **(31) §5.1 factor summary updated.** PatternHistory row notes both read paths.
>
> **(32) §13 Claude Code Rules updated.** PatternHistoryFactorComputer import rule,
>     W2 read path rules, TRIGGERED_EVOLUTION edge invariants.
>
> **(33) §14 SOCDomainConfig updated.** get_factor_computers() PatternHistory entry
>     annotated with both read paths. FACTOR_INDEX=4 constraint noted.
>
> **(34) §22.3 IKS anchor separation added.** Two-artifact constraint: standard μ₀ = IKS
>     anchor (never overwritten), enriched μ₀ = live starting point only. Both stored
>     as distinct artifacts per IKS architecture decision (Option A).
>
> **(35) §22.7 NEW: Three-Signal Monitoring Architecture.** Replaces prior single-signal
>     conservation law framing. Circuit Breaker (existing) + Flywheel Health Monitor
>     (CLAIM-OLS-01 validated) + Analyst Contribution Monitor (production milestone).
>     Var(q) as gating condition: PERMANENT HARD STOP (Bernoulli mixture theorem).
>     Nomenclature corrected: "Level 1/2/3 monitoring" → Circuit Breaker / Flywheel
>     Health Monitor / Analyst Contribution Monitor.

> **Changes v5.5.1 → v5.5.2 (March 21, 2026 — referral architecture):**
>
> **(22) Header updated.** Test counts: GAE 447→478, SOC 252→280. Experiments ~100→~104.
>
> **(23) §13 Claude Code rules updated.** Referral never modifies scoring. Confidence gate
>     is action routing only — NOT referral routing.
>
> **(24) §14 SOCDomainConfig updated.** `get_referral_rules()` method added.
>
> **(25) NEW §22.6: Referral Routing Architecture.** Full spec: ReferralRules R1-R7,
>     triage VETO wiring, three-phase architecture (rules → override learning → retrain).
>     Validated: EXP-REFER-LAYERED 72.7% DR, 12% FPR, 978 net min/100 alerts.
>     Confidence gate REJECTED for referral (14% precision = active harm).
>
> **(26) §11.5 updated.** Referral VETO in triage flow. Two independent routing decisions.

> **Changes v5.5 → v5.5.1 (March 21, 2026 — kernel architecture + A=4 + P0 fix):**
>
> **(14) Header updated.** Test counts: GAE 246→447, SOC 78→252, ci-platform 0→73. Four repos. Companion docs: gae_design v9→v10, math_synopsis v8→v10, experiments_catalog_v8→v2 master.
>
> **(15) §4.4 Tensor updated.** (6,4,6)=144 values. A=4 canonical: escalate, investigate, suppress, monitor. refer_to_analyst removed as scorable action (via referral rules R1-R7, not confidence gate). Static accuracy 80.6→90.6%.
>
> **(16) §10.3/§10.6 updated.** v5.5 Tier 1/2/3 items marked SHIPPED. A=4 numbers.
>
> **(17) §14 SOCDomainConfig updated.** A=4. kernel_type, eta_confirm, eta_override, auto_pause_on_amber, learning_enabled parameters added.
>
> **(18) §22.3 IKS Service corrected.** Module-level functions (was incorrectly described as class). κ*=0.20 (PROD-1 validated).
>
> **(19) §22.5 Endpoint specs added.** GET /api/soc/centroid-evolution (flat array), GET /api/soc/learning-state, GET /api/soc/frozen-roi (FrozenROICalculator: 44min × V × cost, NOT $127/alert).
>
> **(20) Kernel integration.** DiagonalKernel default for noise_ratio>1.5. KernelSelector during shadow mode Phase 3. Factor quarantine mask DEPRECATED.
>
> **(21) §11.5 Tab-2 Section A.** Purple summary card pattern clarified.

> **Changes from v5.2 → v5.3:**
>
> **(1) §1.5 Product Identity added.** Three customer roles, ICP with trigger event, pricing tiers, four competitive gap reframes. Every design decision evaluated against this context.
>
> **(2) §1.6 S2P Co-Design Constraints added.** Explicit table of SOC decisions that must remain generalizable. Platform claim requires genuine domain-agnosticism. One known fix needed: `EvaluationReport.by_technique → by_category` (s2p_copilot v0.2 §8.1).
>
> **(3) §2 Directory updated.** `enterprise/`, `semantics/`, `queries/` added. Tab 5 frontend components listed. Shadow mode + IKS + NL template services added.
>
> **(4) §10.3 v5.0 canonical numbers table added.** 50-seed validated realistic accuracy numbers (71.7% static, 78.9% at dec 1,000). Two-regime rule stated explicitly.
>
> **(5) §10.6 v5.5 Scope — fully specified.** 13 requirements (R1–R13) ordered by demo conversion impact. Tier 1 demo-blocking, Tier 2 sales-blocking, Tier 3 enterprise-readiness. Each has spec cross-reference and gap closure.
>
> **(6) §11.5 v5.5 product flow added.** Full annotated product flow covering all three customer roles and all five tabs.
>
> **(7) §14 SOCDomainConfig updated.** `get_category_thresholds()`, `get_alert_category_mapping()`, `get_shadow_config()`, `get_drift_bounds()`, `get_semantic_concepts()`, `get_query_catalog()`, `get_source_connectors()` added. Profile centroids updated to shape (5,5,6) — fifth action `refer_to_analyst` is now a production action. S2P co-design annotation on every configurable field.
>
> **(8) §21 Shadow Mode — fully specified.** `ShadowModeService`, `ShadowReport`, `Disagreement` dataclasses, API endpoints, UI components.
>
> **(9) §22 Institutional Knowledge Score — fully specified.** Formula, `IKSService`, display locations, interpretation guide.
>
> **(10) §23 NL Template Engine — fully specified.** 24 deterministic templates across three layers (analyst / CISO / auditor). `NLTemplateEngine` class with rendering methods.
>
> **(11) §24 SemanticRegistry Integration.** `concepts.yaml` with 20 named SOC concepts. `queries.yaml` with 15 pre-built Tab 5 queries. QueryRouter fast-path rationale.
>
> **(12) §25 Enterprise Integration Hooks.** `CMDBConnectorProfile` + `IdentityConnectorProfile` YAML templates for enterprise IT. `ServiceNowIncidentAction` stub with shadow-mode-governs-activation constraint.
>
> **(13) §26 Feature Gap Closure Map.** Every gap from product_strategy_v2 §5 mapped to version and requirement ID.
>
> **(14) Appendix B tech debt updated.** TD-036 through TD-039 added. TD-030 CLOSED (τ=0.1 applied in v5.0).
>
> All v5.2 content preserved and renumbered where needed.

---

> **Changes from v5.3 → v5.4:**
>
> **(1) §6.4 Rollback semantics cross-reference added.** §6.4 specified checkpoint creation only. A cross-reference block now documents the rollback execution side: mode (rollback-and-resume), the three trigger conditions, Hook 2/3 interaction during the rolled-back period, and the ARCH-3 prerequisite constraint. §17.5 (Part 2) is flagged as not yet written — ARCH-3 is blocked until it is added.
>
> **(2) §10.6 v5.5-R11 PROD-4 derivation note added.** The 0.70 confidence floor and the ~35%/~25% alert split are design estimates, not calibration-curve-derived values. A note now states the correct derivation source (PROD-4 accuracy-vs-threshold curves) and prohibits hardcoding 0.70 as a named constant until PROD-4 runs.
>
> **(3) §10.6 v5.5-R13 EU AI Act Article 9 risk disclosure added.** The N3 endogenous feedback loop (calibration error → biased verification selection → biased learning) is a known risk with no designed intervention point. Full Article 9(2)(a)/(b) disclosure text added with mitigation (shadow mode) and residual risk level (MEDIUM). Required before v5.5 ships.
>
> **(4) §23.4 Similar Past Cases — Query Specification added.** The "similar past cases" sidebar referenced in every L1 template now has a complete spec: cosine similarity metric with rationale, all five parameters with derivation status, Neo4j GDS query with Python fallback, agreement percentage calculation including suppression logic for cold-start categories, and service location.
>
> **(5) §23.5 Acceptance Test — NL Template Judge Rubric added.** Four-criterion LLM judge rubric (Factual Accuracy, Specificity, Actionability, Non-Redundancy) with 1–5 scoring scale, pass thresholds, LLM prompt fragment for criterion 1, when-to-run schedule, and output storage location. Required before v5.5-T1-1 can be declared done.
>
> **(6) Appendix B TD-035 updated.** Sequencing constraint added: GATE-R must run after v5.5-R6 ships (complete alert_type → category mapping). Running against the v5.0 incomplete mapping measures the broken routing, not the architecture.
>
> **(7) §10.3 synthetic accuracy corrected to canonical 97.89%.** Prior text cited "94.78%" which was a pre-EXP-C1 stale number. Corrected to 97.89% (EXP-C1, zero-learning, synthetic centroidal) with explicit experiment citation. The canonical numbers table at §4.4 was already correct; this aligns §10.3 with it.
>
> **(8) §2 directory, §13 imports, and §6.4 reference corrected.** `similar_cases.py` added to services listing; `test_similar_cases.py` and `nl_template_judge_results.json` added to tests listing. `SimilarCasesService` import rule and parameter derivation constraints added to §13. `SimilarCasesService` call-order rule added (must run after `score()`, before `render_l1()`). §6.4 rollback cross-reference corrected: prior text cited "§17.5 (Part 2)" as if that section existed; it does not. Reference now correctly marks §17.5 as not yet written and blocks ARCH-3 on its completion.

---

## 1. Architecture — SOC Copilot in Three-Repo Stack

### 1.1 Dependency Graph

```
graph-attention-engine (Apache 2.0)     ← numpy-only, zero external deps, 517 tests
        ↑
ci-platform (Apache 2.0)                ← GAE + Neo4j + asyncio (v5.0+), 174 tests
  ├── SemanticRegistry                  ← graph vocabulary service (v5.5)
  ├── QueryCatalog + QueryRouter        ← pre-built query hub (v5.5)
  └── EnterpriseConnectorProfile        ← IT integration templates (v5.5)
        ↑
soc-copilot [THIS REPO] (proprietary)   ← GAE + platform + SOC domain expertise
```

SOC copilot is the **top of the stack**. Neither GAE nor ci-platform ever imports from soc-copilot. The proprietary moat lives entirely here: domain factors, seed centroids, evaluation scenarios, and (at deployment) the evolved centroid tensor reflecting a specific firm's operational history.

### 1.2 What Lives Here

| Component | Purpose | Examples |
|---|---|---|
| **Domain factors** | SOC-specific FactorComputer implementations | TravelMatch, AssetCriticality, ThreatIntelEnrichment |
| **Domain config** | SOCDomainConfig — actions, centroids, thresholds, concepts | `domains/soc/config.py` |
| **Situation classifier** | SituationAnalyzer — alert → category routing | `domains/soc/situations.py` |
| **Seed data** | SOC-specific Neo4j seed (200+ users, realistic distributions) | `domains/soc/seed_data/` |
| **Factor orchestrator** | Async Neo4j → FactorComputer → GAE assembly | `domains/soc/orchestrator.py` |
| **Connectors** | CISA KEV, NVD, Pulsedive, GreyNoise (SourceConnector impls) | `connectors/` |
| **Enterprise connectors** | CMDB, AD/LDAP YAML integration templates | `enterprise/connectors/` |
| **Semantic concepts** | concepts.yaml — 20 named SOC graph concepts | `semantics/concepts.yaml` |
| **Query catalog** | queries.yaml — 15 pre-built Tab 5 questions | `queries/queries.yaml` |
| **Frontend** | React UI (all tabs including Tab 5) | `frontend/` |
| **Routers** | FastAPI endpoints | `routers/` |
| **Deployment** | Docker Compose, VPS | `deployment/` |
| **Event bus (local)** | Lightweight bus until ci-platform provides production bus | `services/event_bus.py` |

### 1.3 What Does NOT Live Here

| Component | Lives In | Why |
|---|---|---|
| ProfileScorer (Eq. 4-final) | graph-attention-engine | Pure math, domain-agnostic |
| Profile learning (Eq. 4b-final) | graph-attention-engine | Pure math |
| FactorComputer Protocol | graph-attention-engine | Abstract interface |
| Event TYPE definitions | graph-attention-engine | Pure dataclasses |
| CalibrationProfile | graph-attention-engine | Domain-configurable, not domain-specific |
| Production event bus | ci-platform (v5.5+) | Infrastructure |
| Entity resolution (INOVA) | ci-platform (v6.5+) | Domain-agnostic |
| **SemanticRegistry** | **ci-platform (v5.5)** | **Platform service — SOC provides concepts.yaml only** |
| **QueryCatalog + QueryRouter** | **ci-platform (v5.5)** | **Platform service — SOC provides queries.yaml only** |
| **EnterpriseAction Protocol** | **ci-platform (v6.0)** | **Platform protocol — SOC provides ServiceNow impl** |
| GraphAttentionBridge | graph-attention-engine (v7.0) | Level 2 enrichment — domain-agnostic |
| DiscoveryEngine | graph-attention-engine (v8.0) | Level 3 discovery — domain-agnostic |

---

### 1.4 Architecture Philosophy (Abbreviated)

> **Full treatment:** `architecture_philosophy_v4.1.md` (outputs). Read before any cross-layer design decision. For external-facing narrative: `compounding_intelligence_v7_part1.md` (Five-Layer Computational Model) and `compounding_intelligence_v7_part3.md` (Bridge Problem, Compiled Ontologies).
>
> **v5.5.3 note:** Updated from `architecture_philosophy_v1_3.md` to `architecture_philosophy_v4.1.md`.
> v4.1 adds ACCP bounded hyperagent framing, three write sources (W1/W2/W3), and
> three Phase 3 design gaps (H1/H2/H3). All prior architectural constraints preserved.

#### The Bridge: Four Components

| Bridge Component | Direction | What It Does | Obligation |
|---|---|---|---|
| **FactorComputers** | Graph → Math | 6 Neo4j traversals → f ∈ [0,1]^6 | ✅ v4.1 |
| **SituationAnalyzer** | Graph → Routing | Alert type → category c → selects μ[c,:,:] | v5.0 (GATE-R gate) |
| **Decision + Outcome Write-Back** | Math → Graph | Scoring result, f(t), centroid snapshot → Decision node | ✅ v4.1 |
| **Data Preservation Hooks** | Level 1 → Level 2/3 substrate | DecisionRecord + OutcomeRecord + ProfileSnapshot every cycle | **v5.0 obligation** |

#### Compiled Ontology

`SOCDomainConfig.get_profile_centroids()` is domain expertise compiled into geometry. The statement "for insider_behavioral alerts, escalate when asset_criticality is high and pattern_history is low" compiles to `μ[insider_behavioral, escalate, :] = [0.35, 0.85, 0.60, 0.15, 0.50, 0.30]`. The mathematical engine computes L2 distance with zero domain knowledge — all domain knowledge has been compiled away into Layer 2's geometry.

#### Three Computational Levels (Enrichment Architecture)

| Level | What | SOC Copilot Concern | Version Target |
|---|---|---|---|
| **Level 1** | Score alert: f vs. μ[c,a,:] | ✅ Full — implement and maintain | v5.0 |
| **Level 2** | Enrich embeddings across domains | ❌ Not a soc-copilot concern — provide data hooks | v7.0 |
| **Level 3** | Discover cross-domain patterns | ❌ Not a soc-copilot concern — provide data hooks | v8.0 |

#### Two Levels of Institutional Judgment (Decision Architecture)

A second, orthogonal framing governs how the system gets smarter at two different timescales. Both levels operate within the SOC copilot; both feed the compounding loop; neither substitutes for the other.

| Level | Name | Mechanism | Timescale | What It Learns |
|---|---|---|---|---|
| **Level 1** | **Decision Intelligence** | ProfileScorer centroid evolution (Eq. 4b-final). μ[c,a,:] drifts from expert opinion toward operational reality. | Slow — months, hundreds of decisions | *What to decide*: which action is right for this category/context |
| **Level 2** | **Deployment Intelligence** | AgentEvolver variant evaluation (binding eval gates). Winning prompt variants, framing, and context structure promoted. | Moderate — weeks | *How to operate*: which operational configuration works in this deployment |

**Separation constraint (permanent):** ProfileScorer.update() has no variant parameter; AgentEvolver promotion signals never update centroids. The two mechanisms write to different state and cannot contaminate each other. This is P16 in `gae_design_v10.md` — architecturally enforced, not configurable.

**SOC copilot owns both.** GAE library provides Level 1 mechanics (ProfileScorer). The AgentEvolver implementation lives in this repo. ci-platform provides the eval gate infrastructure both levels need.

#### ACCP as Bounded Hyperagent (v5.5.3) [NEW v5.5.3]

The ACCP architecture maps directly to the bounded hyperagent pattern (Zhang et al. 2026,
arXiv:2603.19461):

| Loop | Component | Role |
|---|---|---|
| **Loop 1** | Situation Analyzer | Task agent — per-alert scoring and routing |
| **Loop 2** | ProfileScorer + AgentEvolver | Meta agent — learns from Loop 1 outcomes, promotes better variants |
| **Loop 3** | RL + Conservation Law | Fixed governance boundary — deliberate design, not a limitation |

Loop 3 is intentionally fixed. The conservation law (α·q·V ≥ θ_min) is not a constraint
that Loop 2 improves over time — it is the governance boundary that prevents Loop 2
from damaging Loop 1. This is the correct design. A hyperagent that could modify its
own governance boundary is unsafe.

**Three Phase 3 design gaps identified (architecture_philosophy_v4.1):**
- **Gap H1:** AgentEvolver v2 — editable promotion criteria. Gate parameters (Δ_min,
  penalty asymmetry, θ_min weight) adapt from deployment evidence. Loop 3 structure
  stays fixed; parameters within it evolve. Requires EXP-AEVOLVE-V2 before implementation.
- **Gap H2:** Cross-copilot AgentEvolver transfer — SOC AgentEvolver validated promotion
  patterns warm-start S2P AgentEvolver. Shared meta-registry. Evidence-gated, not automatic.
- **Gap H3:** W2 edge content enrichment — MVP edges: {category, action, verified_correct,
  timestamp}. Phase 3 adds: action_confidence_at_decision, factor_vector_snapshot,
  centroid_distance_at_decision, outcome_lead_time_hours. Richer edges → more discriminative
  future Loop 1 traversals.

**Three write sources to the context graph:**
- **W1:** Verified decision write-back via Hook 3 (PatternHistory, centroid evolution)
- **W2:** TRIGGERED_EVOLUTION edges — PatternHistoryFactorComputer reads recency-weighted
  graph context. Validated: CLAIM-W2 +10.13pp (p=0.0002, N=30). See §5.6.
- **W3:** Cross-graph enrichment — CISA KEV, entity resolution, SIEM import.

---

### 1.5 Product Identity

> **Design filter:** Every feature added to the SOC copilot must pass this question: "Is this making the compounding more *visible*, or the decisions more *accurate*? Both matter. Visibility first — because without it, accuracy improvement doesn't close contracts."

#### Three Customer Roles

**Role 1 — The Daily User (SOC Analyst)**
- **Adoption:** Recommendation is right more often than gut. Can see WHY. Routine alerts automated. After 30 days: relief.
- **Championing:** "The system knows our environment now."
- **v5.0 critical gap:** Learning is real but **invisible**. No reason to keep giving feedback if feedback disappears.

**Role 2 — The Buyer (CISO / Security Director)**
- **Signing:** Clear ROI, proof of improvement, one paragraph for the board, operational proof in trial.
- **Renewal:** Monthly metrics: "847 alerts auto-approved at 91% accuracy. 28 analyst-hours recovered."
- **v5.0 critical gap:** No proof-of-compounding surface. ROI calculator shows projected numbers. Buyers need *realized* numbers.

**Role 3 — The Technical Evaluator (SOC Architect)**
- **Approval:** Not a black box. Centroids readable. Every decision auditable. Not locked in. Apache 2.0.
- **Block:** "Can't explain to regulators." "Can't correct a wrong centroid without code changes."
- **v5.0 critical gap:** Auditability exists architecturally but isn't surfaced as a compliance-ready product feature.

#### The Five CISO Demo Questions

| Question | v5.0 | v5.5 |
|---|---|---|
| Q1: "Does it work?" | Technical factor output only | NL explanation + provenance nodes + similar past cases |
| Q2: "Is it getting smarter?" | Cannot answer | Institutional Knowledge Score + centroid drift chart |
| Q3: "What's the ROI?" | Projected estimate only | Shadow mode: realized numbers before go-live |
| Q4: "What if it's wrong?" | Safety exists but invisible | Shadow + checkpoint/rollback + UI safety controls |
| Q5: "Why not Security Copilot?" | Positioning argument only | Firm-specific threat graph + IOC memory visible in Tab 5 |

**v5.5 is the product. v5.0 is the foundation.**

#### Ideal Customer Profile (ICP)

- **Size:** 2,000–50,000 employees (500+ alerts/day; not CrowdStrike managed detection scale)
- **Industry:** Regulated — financial services, healthcare, critical infrastructure, government contractors
- **SOC team:** 10–100 analysts (inconsistency is visible; volume generates learning in 90 days)
- **SIEM maturity:** 2–5 years post-deployment; known-pattern rules tuned; alert fatigue real
- **Trigger event:** Visible incident in past 18 months where post-incident review found "inconsistent triage." This makes the consistency argument urgent rather than abstract. **Without a recent incident, the product is a nice-to-have. With one, it addresses a live organizational wound.**

**Anti-ICP:** CrowdStrike Falcon Complete customers; <500 alerts/day; greenfield SIEM; research/academic.

#### Pricing

Annual subscription per SOC team tier. Not per-alert (backwards incentive — penalizes alert volume).

| Tier | Size | Mode | Price |
|---|---|---|---|
| Pilot | <50 analysts | Shadow mode only, 90 days | $75K–150K/year |
| Standard | 50–200 analysts | Full deployment + Tab 5 | $200K–400K/year |
| Enterprise | >200 analysts or multi-domain | Full + custom integration | $500K+/year |

**Contract commitment:** Customer owns their centroid tensor. Can export it. Can deploy on alternate infrastructure. This is the "you own the intelligence" commitment made operationally concrete — and it is the switching cost that differentiates from SaaS.

#### Competitive Positioning (Four Reframes)

| Gap | Wrong Frame | Right Frame | Closes At |
|---|---|---|---|
| 71.7% accuracy | Lower than rule-based | **Consistency multiplication**: every analyst gets the same recommendation every time. Analyst agreement on same alert: 60-70%. GAE: always consistent. | v5.5: segmented accuracy + analyst agreement rate metric |
| 11.5% auto-approve | Lower than SOAR | **Wrong problem class**: SOAR handles deterministic playbooks. GAE handles judgment-intensive middle. 40%+ with category-specific thresholds + fifth action. | v5.5-R1 + refer_to_analyst |
| No real-time threat intel | Can't match Security Copilot | **SC knows what Microsoft knows. GAE knows what YOUR FIRM has learned.** IOC memory persists per firm. SC's context disappears when you stop paying. | v5.5: ThreatIndicator nodes; v6.0: σ scoring (GATE-M) |
| Explainability requires sophistication | Complex to explain | **Three layers**: analyst (factor breakdown + provenance), CISO (NL template), auditor (compliance export). Right audience gets right layer. | v5.5: NL template engine (Tier 1); v6.0: compliance export |

---

### 1.6 S2P Co-Design Constraints

> **Purpose:** The platform claim requires genuine multi-domain capability. Every SOC design decision must remain generalizable to avoid future S2P re-architecture. This section is the design conscience for that constraint.

The S2P copilot (design v0.2) validated that GAE, ci-platform, and evaluation abstractions are domain-agnostic. These constraints must hold in every new SOC design decision:

| SOC Decision | S2P Requirement | Generalization Rule |
|---|---|---|
| `actions = [..., "refer_to_analyst"]` | S2P: `["approve", "hold_for_review", "reject", "escalate_compliance", "refer_to_analyst"]` | `get_actions()` returns any list. Never hardcode action count in GAE scoring. |
| `C=5` categories | S2P: `C=5` procurement types | ProfileScorer constructor accepts any C. Never hardcode C=5 outside DomainConfig. |
| `penalty_ratio=20.0` | S2P: `penalty_ratio=5.0` | Configurable field. 20:1 is SOC-domain-specific only. |
| `temperature=0.1` | S2P: `temperature=0.4` (needs validation) | Configurable field. τ=0.1 validated for SOC synthetic data only. |
| `decay_classes: {campaign, standard, permanent}` | S2P adds "transient" (0.02) for commodity prices | `decay_class_rates` dict accepts any string key. |
| ATT&CK technique IDs | S2P: `technique_id=None` | `EvaluationScenario.technique_id` must be `Optional[str]`. |
| `EvaluationReport.by_technique` | S2P has no ATT&CK | **Fix required:** rename `by_technique → by_category`. Spec: s2p_copilot v0.2 §8.1. |
| CISA KEV, NVD, Pulsedive connectors | S2P: OFAC, D&B, LME, GeoRisk connectors | `SourceConnector` protocol is domain-agnostic. `entity_type` is a free string. Trust tiers configurable. |
| `concepts.yaml` with SOC concepts | S2P: `concepts.yaml` with procurement concepts | `SemanticRegistry` domain-agnostic. Domain is a string parameter. |
| 15 SOC Tab 5 queries | S2P: 15 procurement queries | `QueryCatalog` + `QueryRouter` domain-agnostic. `nl_patterns` are domain-specific strings. |
| 6 FactorComputers (SOC traversals) | S2P: 6 different FactorComputers (procurement traversals) | `FactorComputer` protocol domain-agnostic. Count and implementation are copilot concerns. |

**S2P co-design summary:** One GAE interface fix needed (`by_technique → by_category`). All platform services (SemanticRegistry, QueryCatalog, EnterpriseConnectorProfile) are designed domain-agnostic. All FactorComputer and DomainConfig abstractions validate cleanly for S2P. See s2p_copilot v0.2 §9.

---

## 2. Directory Structure

```
soc-copilot/
├── backend/
│   └── app/
│       ├── domains/
│       │   └── soc/
│       │       ├── __init__.py
│       │       ├── config.py               # SOCDomainConfig (§14) — domain expertise
│       │       ├── factors.py              # 6 FactorComputer implementations (§5)
│       │       ├── orchestrator.py         # async Neo4j → compute → GAE assembly (§5.4)
│       │       ├── alert_pool.py           # 25 alerts, 5 categories, ATT&CK ✅
│       │       ├── situations.py           # SituationAnalyzer — category routing (v5.0)
│       │       └── seed_data/
│       │           ├── users.json          # 200+ users, realistic distributions (SEED-2)
│       │           ├── assets.json
│       │           ├── threat_intel.json
│       │           └── travel_records.json
│       ├── connectors/                     # SourceConnector implementations
│       │   ├── cisa_kev.py                 # CISAKEVConnector — daily pull (PLAT-7) ✅
│       │   ├── nvd.py                      # NVDConnector — CVE feed (PLAT-7) ✅
│       │   ├── pulsedive.py                # Pulsedive — per-alert enrichment
│       │   └── greynoise.py                # GreyNoise — IP reputation
│       ├── enterprise/                     # Enterprise integration (v5.5)
│       │   ├── connectors/
│       │   │   ├── cmdb_profile.yaml       # CMDBConnectorProfile — IT team fills in (§25)
│       │   │   └── identity_profile.yaml   # IdentityConnectorProfile — AD/LDAP (§25)
│       │   └── actions/
│       │       └── servicenow.py           # ServiceNowIncidentAction — human-approved (v6.0, §25)
│       ├── semantics/
│       │   └── concepts.yaml              # 20 SOC SemanticConcepts for SemanticRegistry (§24.1)
│       ├── queries/
│       │   └── queries.yaml               # 15 pre-built Tab 5 queries for QueryCatalog (§24.2)
│       ├── routers/
│       │   ├── triage.py                   # POST /api/analyze → GAE scoring ✅
│       │   ├── evolution.py                # POST /alert/process → GAE pipeline ✅
│       │   ├── feedback.py                 # POST /api/feedback → GAE learning + centroid update
│       │   ├── soc.py                      # GET /api/soc/* metrics
│       │   ├── gae.py                      # GET /api/gae/weights, /convergence, /iks
│       │   ├── simulation.py               # POST /api/simulation/run ✅
│       │   ├── admin.py                    # POST /api/admin/reset ✅
│       │   ├── shadow.py                   # Shadow mode endpoints (v5.5, §21)
│       │   ├── graph_explorer.py           # Tab 1 Panel B: POST /api/{domain}/query — F14-basic (v5.5, §24)
│       │   ├── tab5.py                     # Tab 5 exec learning narrative: /api/soc/tab5/briefing (v6.0, §24)
│       │   ├── evaluation.py               # Evaluation runner (v5.0)
│       │   └── query.py                    # POST /api/soc/query → F14 foundation
│       ├── services/
│       │   ├── event_bus.py                ✅
│       │   ├── feedback.py                 ✅
│       │   ├── simulation.py               ✅
│       │   ├── narrative.py                # NarrativeProvider protocol ✅
│       │   ├── nl_templates.py             # NLTemplateEngine — 24 deterministic templates (v5.5, §23)
│       │   ├── similar_cases.py            # SimilarCasesService — cosine similarity retrieval (v5.5, §23.4)
│       │   ├── shadow.py                   # ShadowModeService (v5.5, §21)
│       │   ├── iks.py                      # InstitutionalKnowledgeScoreService (v5.5, §22)
│       │   ├── evolver.py                  ✅
│       │   ├── state_manager.py            ✅
│       │   ├── gae_state.py                ✅
│       │   ├── embedding.py                # EmbeddingProvider (v6.0+)
│       │   └── neo4j_client.py
│       ├── scripts/
│       │   └── verify_seed_data.py         ✅
│       ├── db/
│       │   ├── neo4j.py
│       │   └── seed_neo4j.py
│       ├── config.py
│       └── main.py
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── AlertTriageTab.tsx           # Tab 3 ✅
│       │   ├── RuntimeEvolutionTab.tsx      # Tab 2 ✅
│       │   ├── SOCAnalyticsTab.tsx          # Tab 1 ✅ — Panel B (Graph Explorer) added at v5.5
│       │   ├── GraphExplorerPanel.tsx       # Tab 1 Panel B: F14-basic Graph Explorer (v5.5, §24)
│       │   ├── CompoundingDashboard.tsx     # Tab 4 ✅
│       │   ├── Tab5LearningNarrative.tsx    # Tab 5: exec learning narrative (three sections) (v6.0, §24)
│       │   ├── ShadowModePanel.tsx          # Shadow mode banner + report view (v5.5)
│       │   ├── InstitutionalKnowledge.tsx   # IKS widget + trend chart (v5.5)
│       │   ├── SimulationPanel.tsx          ✅
│       │   └── ROICalculator.tsx            ✅
├── deployment/
│   ├── docker/                             # Docker Compose (v5.5-R9)
│   │   ├── docker-compose.yml
│   │   └── Dockerfile.backend
│   └── vps/                                # VPS deployment scripts (v5.5)
├── tests/
│   ├── test_factors.py
│   ├── test_triage.py
│   ├── test_feedback.py
│   ├── test_simulation.py                  ✅
│   ├── test_shadow.py                      # (v5.5)
│   ├── test_nl_templates.py                # (v5.5)
│   ├── test_similar_cases.py               # (v5.5, §23.4) — unit tests for SimilarCasesService
│   ├── nl_template_judge_results.json      # (v5.5, §23.5) — LLM judge scores per template + criterion
│   └── test_visual_smoke.py                ✅
├── pyproject.toml                           # depends on: graph-attention-engine, ci-platform
└── README.md
```

---

## 3. Imports from GAE

```python
# Core scoring + learning
from gae.scoring import score_alert, ScoringResult
from gae.profile_scorer import ProfileScorer, build_profile_scorer       # v5.0+
from gae.learning import LearningState, WeightUpdate, PendingValidation
from gae.factors import FactorComputer, assemble_factor_vector
from gae.calibration import CalibrationProfile

# Contracts + schema
from gae.contracts import SchemaContract, EmbeddingContract, PropertySpec
from gae.schema import DomainSchemaSpec

# Evaluation framework
from gae.evaluation import (
    EvaluationScenario, EvaluationReport, AblationConfig,   # NOTE: EvaluationReport.by_category (not by_technique)
    run_evaluation, run_ablation
)
from gae.judgment import InstitutionalJudgmentMetrics, compute_judgment

# Data preservation hooks — v5.0 WRITE OBLIGATION — Level 2/3 substrate
from gae.hooks import DecisionRecord, OutcomeRecord, ProfileSnapshot
```

---

## 4. Complete Build History

### 4.1 v4.1 ✅ COMPLETE
13 prompts (7 GAE + 6 SOC). GAE foundation: 6 FactorComputers, decision/outcome write-back, ProfileScorer pipeline. 10-cycle compounding verification passed. Tagged v4.1.

### 4.2 v4.5 ✅ TAGGED
13 prompts. CalibrationProfile (GAE-CAL-1, GAE-CAL-2). Simulation mode (SIM-FIX through SIM-4). CISO Readability (NAR-1, NAR-2, TAB2-1, TAB2-2). HC-1 healthcare domain. Phase C RESOLVED by 14 bridge experiments (G falsified, L2 found, ProfileScorer validated).

### 4.3 v5.0 Sprint ✅ COMPLETE (all 29 prompts, v5.0 tagged)

| Phase | Prompts | Repo | Status | Milestone |
|---|---|---|---|---|
| Phase 1: GAE ProfileScorer (GAE-PROF-1→4) | 4 | GAE | ✅ COMPLETE | — |
| Phase 2: SOC integration (SOC-PROF-1→3) | 3 | SOC | ✅ COMPLETE | — |
| Phase 3: OracleProvider (GAE-ORACLE-1) | 1 | GAE | ✅ COMPLETE | **v5.0-alpha** ✅ |
| Phase 4: H7 data realism (H7-FIX-1→4) | 4 | SOC | ✅ COMPLETE | — |
| Phase 5: Feature gaps (F2, F4) | 2 | SOC | ✅ COMPLETE | **v5.0-beta** ✅ |
| Phase 6: GAE evaluation (EVAL/ABL/JUDG/ENG/DOC) | 5 | GAE | ✅ COMPLETE | — |
| Phase 7: SOC evaluation (SEED-2, EVAL×2, ECON, JUDG) | 8 | SOC | ✅ COMPLETE | **v5.0 TAG** ✅ |
| Phase 8: ci-platform (PLAT-1→4) | 4 | Platform | ✅ COMPLETE | — |
| Phase 9: Connectors (PLAT-5→7) | 3 | Platform+SOC | ✅ COMPLETE | **v5.0-platform** ✅ |

**Post-tag (WIRING-1):** CentroidUpdate dataclass, freeze/unfreeze on ProfileScorer. 243 → 246 tests. CentroidUpdate wired to SOC triage endpoint (`centroid_delta_norm`) and Tab-3 centroid delta display.

**Deferred to v5.5:** SIT-1 (dynamic category inference), SIT-2 (cross-category disambiguation), A1-FIX (discount_strength tuning post EVAL-2).

**v5.5 first actions (in order):** PROD-3 (shadow mode baseline) → PROD-4 (threshold calibration) → FX-1-PROXY-REAL → EXP-S2-REPRO Arm 0. Do not begin v5.5 sprint feature work until PROD-3 and PROD-4 complete — they produce the calibration data that v5.5-R1 (category-specific thresholds) depends on.

### 4.4 v5.0/v6.0 Canonical Numbers

**Centroid Tensor (v6.0 canonical — A=4):** [CHANGED v5.5.1]
```
μ ∈ ℝ^(6 × 4 × 6) = 144 values
Categories (C=6): credential_access, threat_intel_match, lateral_movement,
  data_exfiltration, insider_threat, cloud_infrastructure
Actions (A=4): escalate, investigate, suppress, monitor
  NOTE: refer_to_analyst REMOVED as scorable action (v6.0 A=4 migration).
  Accessed via referral rules R1-R7 (not confidence gate) — never in centroid tensor.
Factors (d=6): travel_match, asset_criticality, threat_intel_enrichment,
  time_anomaly, pattern_history, device_trust
```

| Metric | Value | 95% CI | Condition |
|---|---|---|---|
| **A=4 static accuracy** | **90.6%** | — | **A=4 migration, noise=0** [NEW v5.5.1] |
| Static realistic accuracy | **71.7%** | [71.4%, 71.9%] | Combined realistic, 50 seeds |
| Learning at decision 1,000 | **78.9%** | [78.1%, 79.6%] | Combined realistic, 50 seeds |
| credential_access at dec 1,000 | **68.0%** | [66.7%, 69.1%] | Combined realistic |
| Auto-approve accuracy (≥0.90) | **90.7%** | [90.1%, 91.2%] | Combined realistic |
| Auto-approve coverage | **40%+** | — | **PROD-4, per-category thresholds** [CHANGED v5.5.1] |
| Zero-learning accuracy | **97.89%** | — | Synthetic centroidal (EXP-C1) |
| With-learning accuracy | **98.2%** | — | Synthetic centroidal (EXP-B1) |
| Calibration ECE | **0.036** at τ=0.1 | — | Synthetic (V3B) |
| **DiagonalKernel lift (SOC)** | **+13.2pp** | — | **Heterogeneous noise (V-MV-KERNEL)** [NEW v5.5.1] |
| **Healthcare with Diagonal** | **+3.7pp** | — | **σ=0.22, V-HC-CONFIG** [NEW v5.5.1] |

**⚠️ TWO-REGIME RULE — NEVER MIX THESE IN EXTERNAL COMMUNICATION:**
- Centroidal synthetic (97.89%, 98.2%): validates the mathematical *mechanism*. Not a product claim.
- Realistic 50-seed (71.7%, 78.9%): the honest *product claim*. Use this in all customer-facing materials.

**Asymmetric η (P0 fix):** [NEW v5.5.1]
η_confirm=0.05 (confirm path), η_override=0.01 (override path, attenuated 5×).
Prevents 13-27pp centroid degradation from realistic analyst quality.
Validated across 24 personas. Corr(noise_ratio, diagonal_advantage)=0.990.

**April 5-6 additions to canonical numbers:** [NEW v5.6]

| Metric | Value | Condition | Claim |
|---|---|---|---|
| Enrichment Day-1 lift (production config) | +42.69pp | Enriched μ₀ + DiagonalKernel | CLAIM-62 UNCONDITIONAL (SVM-003b) |
| → from enriched μ₀ initialization | +40.93pp | L2 kernel, N=30/profile, 3 profiles | CLAIM-62 (Innovation 7) |
| → from DiagonalKernel sigma-weighting | +1.76pp add-on | Healthcare 3.5× contrast → +4.13pp extra | CLAIM-62 (Innovation 4) |
| Fisher info: enrichment → learning rate | r=0.9669 empirical | Empirical = analytical (delta=0.0000) | CLAIM-64 UNCONDITIONAL (SVM-004b) |
| Graph enrichment while centroids frozen | 54.4% faster | 26/30 seeds, p<0.0001 | CLAIM-59 UNCONDITIONAL (V-CGA-FROZEN) |
| Analyst time savings (SANS-calibrated) | 30.85 min/alert | CI=[29.90,31.81], 30 personas | CL-ECON-MEASURED UNCONDITIONAL |
| Per-industry ROI | $523K–$2.8M/year | Healthcare/Midmarket/FinServ | CL-ECON-MEASURED |

**raw_weights vs weights (CLAIM-64 architecture note):**
Use `DiagonalKernel.raw_weights` (true 1/σ²) for η_eff and enrichment ROI calculations.
Use `DiagonalKernel.weights` (pre-normalized [0,1]) for scoring decisions only.
GAE 0.7.20 required — v0.7.19 had a raw_weights bug (silent scale cancellation).

---

## 5. SOC Factor Implementations

### 5.1 Factor Summary

| Factor | Cypher Pattern | Channels | Decay Class |
|---|---|---|---|
| TravelMatch | `(u:User)-[:HAS_TRAVEL]->(t:TravelRecord)` | C, D | campaign |
| AssetCriticality | `(a:Asset)-[:STORES]->(d:DataClass)` | C, D | permanent |
| ThreatIntelEnrichment | `(ti:ThreatIntel)-[:ASSOCIATED_WITH]->(a:Alert)` | C, D | campaign |
| PatternHistory (W1 path) | `(d:Decision)-[:DECIDED_ON]->(a:Alert)` — accuracy of prior decisions | A, B | standard |
| PatternHistory (W2 path) | `(d:Decision)-[:TRIGGERED_EVOLUTION]->(e:Entity)` — recency-weighted TRIGGERED_EVOLUTION edges | A | standard |
| TimeAnomaly | `(u:User)-[:ACTIVE_AT]->(ts:TimeSlot)` | C | standard |
| DeviceTrust | `(dev:Device)-[:USED_BY]->(u:User)` | C | standard |

> **Two PatternHistory read paths:** §5.2 documents PatternHistoryFactor (W1 path —
> decision accuracy). §5.6 documents PatternHistoryFactorComputer (W2 path —
> TRIGGERED_EVOLUTION recency-weighted context). Both populate FACTOR_INDEX=4.
> The W2 path supersedes the W1 path when TRIGGERED_EVOLUTION edges exist.
> See §5.6 for implementation. CLAIM-W2: +10.13pp (p=0.0002).

> **S2P Co-Design Note:** S2P's 6 factors (SupplierReliability, SpendCompliance, DualSource, GeopoliticalRisk, HistoricalApproval, PriceVariance) use the identical `FactorComputer` protocol with different Cypher traversals and a "transient" decay class. `HistoricalApproval` is S2P's `PatternHistory` equivalent — the compounding proof factor in procurement.

### 5.2 PatternHistory — The Compounding Proof Factor

```python
class PatternHistoryFactor(FactorComputer):
    """
    THE COMPOUNDING PROOF FACTOR.
    
    First alert in a category: returns 0.5 (symmetric prior — no history).
    After 15 correct decisions on same category: returns ~1.0.
    
    This is the proof of compounding to the analyst:
    The same alert type, analyzed again → different score.
    The entire difference is explained by prior decisions in the graph.
    There is no other code path that produces this effect.
    
    Cypher: MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)
            WHERE a.situation_type = $category AND d.outcome IS NOT NULL
    Score:  correct / total  (minimum 5 decisions for non-default)
    Channels: A (Decision nodes), B (outcome markings)
    """
    name = "pattern_history"
    
    async def compute(self, alert_id: str, context: dict, neo4j) -> "FactorComputerResult":
        category = context.get("situation_type", "unknown")
        result = await neo4j.execute_read("""
            MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)
            WHERE a.situation_type = $category AND d.outcome IS NOT NULL
            RETURN count(d) AS total,
                   sum(CASE WHEN d.correct THEN 1 ELSE 0 END) AS correct
        """, category=category)
        
        total = result["total"]
        if total < 5:
            return FactorComputerResult(
                value=0.5,
                provenance_nodes=[ProvenanceNode(
                    node_type="Decision", node_id="none",
                    key_property="count", key_value=str(total),
                    contribution=f"Only {total} prior decisions — symmetric prior applied"
                )]
            )
        
        accuracy = result["correct"] / total
        return FactorComputerResult(
            value=accuracy,
            provenance_nodes=[ProvenanceNode(
                node_type="Decision", node_id="aggregate",
                key_property="accuracy", key_value=f"{accuracy:.2f}",
                contribution=f"{result['correct']}/{total} correct decisions on {category}"
            )]
        )
```

### 5.3 ThreatIntelEnrichment — The Threat Graph Factor (v5.5 enhanced)

```python
class ThreatIntelEnrichmentFactor(FactorComputer):
    """
    THREAT INTEL ENRICHMENT FACTOR.
    
    v5.0: Reads ThreatIntel campaign nodes (ASSOCIATED_WITH edges to Alert).
    v5.5: Also reads ThreatIndicator nodes (persisted IOC memory).
    
    Two-pass scoring:
      Pass 1: Direct ThreatIntel campaign association (active campaigns)
      Pass 2: ThreatIndicator match on any alert IOC (firm's accumulated IOC memory)
    
    Returns: max(campaign_score, ioc_score)
    
    The IOC memory is the v5.5 differentiation from Security Copilot:
    once an IP is flagged as malicious from THIS FIRM's alert stream,
    all future alerts involving that IP benefit from the accumulated evidence.
    Security Copilot cannot provide this — it has no per-firm IOC memory.
    """
    name = "threat_intel_enrichment"
    
    async def compute(self, alert_id: str, context: dict, neo4j) -> "FactorComputerResult":
        campaign_result = await self._campaign_score(alert_id, neo4j)
        ioc_result = await self._ioc_score(context.get("source_ips", []), neo4j)
        
        best = campaign_result if campaign_result.value >= ioc_result.value else ioc_result
        return best
```

### 5.4 Factor Orchestrator (v5.5 enhanced with provenance)

```python
# domains/soc/orchestrator.py

async def compute_factor_vector(alert, computers, neo4j):
    """
    Async orchestrator. Calls each FactorComputer, assembles f vector.
    
    v5.0: Returns (f, {factor_name: float})
    v5.5: Returns (f, {factor_name: FactorComputerResult(value, provenance_nodes)})
    
    The provenance_nodes change enables Tab 3 to show:
    "travel_match=0.87 — No travel records to Singapore in 90 days (TravelRecord node absent)"
    instead of just "travel_match=0.87".
    This closes G-L4-1 and CISO Demo Question Q1.
    """
    values, names, results = [], [], {}
    for computer in computers:
        result = await computer.compute(alert["id"], alert, neo4j)
        values.append(result.value)
        names.append(computer.name)
        results[computer.name] = result  # FactorComputerResult with provenance
    
    f = assemble_factor_vector(values, names)
    return f, results
```

### 5.5 Accumulation Channels

| Channel | What Accumulates | Who Benefits | Status |
|---|---|---|---|
| A: Decision | Decision nodes with f(t), action, confidence, category | PatternHistoryFactor | ✅ v4.1 |
| B: Outcome | Decision nodes marked correct/incorrect + centroid_delta_norm | PatternHistoryFactor, centroid pull/push | ✅ v4.1 |
| C: Entity Ingestion | ThreatIntel, ThreatIndicator, Users, Assets, Devices with relationships | ThreatIntelEnrichment, TravelMatch, DeviceTrust | CISA KEV + Pulsedive connectors |
| D: Relationship Enrichment | [:CALIBRATED_BY], IOC-alert edges, analyst links | Any factor using relationship traversal | v5.5 |
| E: Structural Expansion | New scoring dimensions → μ expands | All factors, all scoring | v5.5 meta loop |

### 5.6 PatternHistoryFactorComputer — The W2 Flywheel Read Path [NEW v5.5.3]

```python
# domains/soc/factors.py (line 272)

class PatternHistoryFactorComputer(FactorComputer):
    """
    W2 FLYWHEEL READ PATH. Distinct from PatternHistoryFactor (§5.2).

    §5.2 PatternHistoryFactor reads DECISION accuracy (W1 path):
      How often were past decisions on this category correct?
      Returns: correct/total (accuracy over prior decisions)

    THIS class reads TRIGGERED_EVOLUTION graph context (W2 path):
      What pattern context has accumulated in the graph from verified decisions
      that triggered structural evolution edges? Recency-weighted.
      Returns: recency-weighted mean of factor context from TRIGGERED_EVOLUTION edges.

    CLAIM-W2 (UNCONDITIONAL): +10.13pp accuracy (CI=[+5.4,+14.9]pp, p=0.0002, N=30).
    V-TRIGGERED-EVOLUTION full. The graph is smarter at Day 90 than Day 1 — not
    because centroids changed, but because TRIGGERED_EVOLUTION edges have accumulated.

    FACTOR_INDEX = 4 (pattern_history). This computer populates ONLY index 4.
    Factors [0,1,2,3,5] are populated by their own FactorComputers and MUST NOT
    be touched by this class.

    FALLBACK = 0.40 (neutral, symmetric prior). Used when no TRIGGERED_EVOLUTION
    edges exist for this category. Do not use 0.5 — 0.40 is the calibrated neutral
    that avoids pulling toward escalate action.

    RECENCY WEIGHTING: Recent edges receive higher weight via exponential decay.
    decay_factor = exp(-days_ago / RECENCY_HALFLIFE). RECENCY_HALFLIFE = 30 days.
    All weights normalized to [0, 1] before multiplication.
    """

    name = "pattern_history"
    FACTOR_INDEX = 4
    FALLBACK = 0.40
    RECENCY_HALFLIFE = 30  # days

    async def compute(self, alert_id: str, context: dict, neo4j) -> "FactorComputerResult":
        category = context.get("situation_type", "unknown")

        # Query TRIGGERED_EVOLUTION edges for this category
        result = await neo4j.execute_read("""
            MATCH (d:Decision)-[:TRIGGERED_EVOLUTION]->(e:Entity)
            WHERE d.category = $category
              AND d.verified_correct = true
            RETURN e.factor_snapshot AS factor_snapshot,
                   duration.inDays(d.timestamp, datetime()).days AS days_ago
            ORDER BY d.timestamp DESC
            LIMIT 50
        """, category=category)

        if not result or len(result) == 0:
            return FactorComputerResult(
                value=self.FALLBACK,
                provenance_nodes=[ProvenanceNode(
                    node_type="TriggeredEvolution",
                    node_id="none",
                    key_property="count",
                    key_value="0",
                    contribution=f"No TRIGGERED_EVOLUTION edges for {category} — fallback 0.40"
                )]
            )

        # Recency-weighted mean of pattern_history dimension (index 4)
        import math
        weights = []
        values = []
        for row in result:
            snapshot = row.get("factor_snapshot", [])
            days_ago = row.get("days_ago", 0) or 0
            if snapshot and len(snapshot) > self.FACTOR_INDEX:
                w = math.exp(-days_ago / self.RECENCY_HALFLIFE)
                weights.append(w)
                values.append(snapshot[self.FACTOR_INDEX])

        if not values:
            return FactorComputerResult(
                value=self.FALLBACK,
                provenance_nodes=[ProvenanceNode(
                    node_type="TriggeredEvolution",
                    node_id="none",
                    key_property="factor_snapshot",
                    key_value="absent",
                    contribution="TRIGGERED_EVOLUTION edges exist but factor_snapshots absent — fallback 0.40"
                )]
            )

        # Normalize weights to [0, 1]
        w_sum = sum(weights)
        weighted_value = sum(v * w / w_sum for v, w in zip(values, weights))

        return FactorComputerResult(
            value=float(weighted_value),
            provenance_nodes=[ProvenanceNode(
                node_type="TriggeredEvolution",
                node_id="aggregate",
                key_property="recency_weighted_mean",
                key_value=f"{weighted_value:.3f}",
                contribution=(
                    f"{len(values)} TRIGGERED_EVOLUTION edges for {category}. "
                    f"Recency-weighted pattern context: {weighted_value:.2f}. "
                    f"W2 flywheel active."
                )
            )]
        )
```

**Design invariants (permanent):**

| Invariant | Rule |
|---|---|
| FACTOR_INDEX | Always 4. Never touch factors [0,1,2,3,5]. |
| FALLBACK | 0.40. Not 0.5. Never change without re-validating CLAIM-W2. |
| Recency weighting | Bounded to [0,1]. exp(-days/30) decay. |
| TRIGGERED_EVOLUTION only | Never mix with DECIDED_ON edges (that is §5.2). |
| verified_correct = true | Only edges from verified correct decisions accumulate. |

**Relationship to §5.2 PatternHistoryFactor:**

Both populate FACTOR_INDEX=4. PatternHistoryFactorComputer (W2) supersedes
PatternHistoryFactor (W1) when TRIGGERED_EVOLUTION edges exist. In deployments
with no W2 edges (early in deployment), both return neutral/fallback values.
The W2 path becomes the primary read path as TRIGGERED_EVOLUTION edges accumulate.

**Why +10.13pp works:**

Same alert at Day 1: no TRIGGERED_EVOLUTION edges → factor[4]=0.40 (neutral).
Same alert at Day 90: 847 TRIGGERED_EVOLUTION edges accumulated → factor[4] reflects
actual operational pattern context from verified decisions. Loop 1 traverses differently.
The kernel weights this factor based on 1/σ² — the more reliable the pattern signal,
the higher its weight. The graph is smarter; the centroid has not changed.

---

## 6. Decision & Outcome Write-Back Specifications

### 6.1 Decision Write-Back (Channel A — Hook 1: DecisionRecord)

> **Hook contract:** Satisfies `DecisionRecord` (Hook 1, gae_design_v10 §11.4). These are the canonical Hook 1 fields. DecisionRecord is also the data source for GATE-R routing accuracy (TD-035). Any change must preserve all DecisionRecord fields.

```python
async def write_decision_to_graph(alert_id, result, f, category, profile_scorer, neo4j,
                                  shadow_mode=False):
    query = """
    MATCH (a:Alert {id: $alert_id})
    CREATE (d:Decision {
        id:                randomUUID(),
        action:            $action,
        confidence:        $confidence,
        factor_vector:     $factor_vector,      // f(t) — MUST be stored (R4)
        centroid_snapshot: $centroid_snapshot,  // μ[c,a,:] at decision time
        category:          $category,           // routing category (Hook 1 field)
        kernel:            $kernel,             // similarity kernel used
        all_distances:     $all_distances,      // dist[a] for all actions (Hook 1 field)
        shadow_mode:       $shadow_mode,        // true during shadow period (v5.5)
        timestamp:         datetime()
    })
    CREATE (d)-[:DECIDED_ON]->(a)
    RETURN d.id AS decision_id
    """
    return await neo4j.execute_write(query,
        alert_id=alert_id, action=result.selected_action,
        confidence=result.confidence,
        factor_vector=f.tolist(),
        centroid_snapshot=profile_scorer.centroids[result.category_index].tolist(),
        category=category, kernel=profile_scorer.kernel,
        all_distances=result.all_distances.tolist(),
        shadow_mode=shadow_mode)
```

### 6.2 Shadow Decision Write-Back (v5.5)

```python
async def write_shadow_decision(alert_id, result, analyst_action, f, category,
                                 profile_scorer, neo4j):
    """
    Shadow mode: system decision written WITH analyst's actual decision for comparison.
    action is NOT shown in the UI during shadow period.
    agreement flag pre-computed for shadow report queries.
    """
    query = """
    MATCH (a:Alert {id: $alert_id})
    CREATE (d:Decision {
        id:             randomUUID(),
        action:         $action,             // system recommendation — NOT shown in UI
        confidence:     $confidence,
        factor_vector:  $factor_vector,
        centroid_snapshot: $centroid_snapshot,
        category:       $category,
        kernel:         $kernel,
        all_distances:  $all_distances,
        shadow_mode:    true,
        analyst_action: $analyst_action,     // what analyst actually did
        analyst_agreed: ($action = $analyst_action),
        timestamp:      datetime()
    })
    CREATE (d)-[:DECIDED_ON]->(a)
    RETURN d.id AS decision_id
    """
    return await neo4j.execute_write(query, ...)
```

### 6.3 Outcome Write-Back (Channel B — Hook 2: OutcomeRecord)

```python
async def mark_decision_outcome(decision_id, outcome, delta_norm, neo4j):
    """
    Hook 2 contract: OutcomeRecord.
    centroid_delta_norm = ‖Δμ‖ must be computed BEFORE calling this —
    read μ_before from Decision.centroid_snapshot, call ProfileScorer.update(),
    then compute ‖μ_after - μ_before‖.
    """
    query = """
    MATCH (d:Decision {id: $decision_id})
    SET d.outcome = $outcome,
        d.correct = ($outcome = 1),
        d.verified_at = datetime(),
        d.centroid_delta_norm = $delta_norm     // ‖Δμ‖ — Hook 2 field
    RETURN d.action AS action
    """
    await neo4j.execute_write(query,
        decision_id=decision_id, outcome=outcome, delta_norm=delta_norm)
```

### 6.4 ProfileSnapshot Write-Back (Hook 3 — TD-033 + Level 2/3 Substrate)

```python
async def write_profile_snapshot(profile_scorer, decision_count, trigger, neo4j):
    """
    Hook 3: ProfileSnapshot. TWO writes — both required.
    
    Neo4j write: makes snapshot queryable by Level 2 enrichment sweeps
                 and by IKSService.get_iks_trend().
    Checkpoint store write: enables in-process rollback (TD-033) without
                            a Neo4j round-trip.
    
    Trigger conditions (all mandatory):
      "scheduled"       — every 50 decisions (configured in get_checkpoint_config())
      "operator_start"  — when synthesis operator (σ) is activated
      "manual"          — explicit admin call
      "eval_run"        — before any evaluation run to preserve clean baseline
    """
    snapshot_id = str(uuid4())
    await neo4j.execute_write("""
        CREATE (ps:ProfileSnapshot {
            id:                 $id,
            centroid_array:     $centroids,
            observation_counts: $obs,
            t_decision:         $t,
            trigger:            $trigger,
            created_at:         datetime()
        })
    """, id=snapshot_id,
         centroids=profile_scorer.centroids.tolist(),
         obs=profile_scorer.observation_counts.tolist(),
         t=decision_count, trigger=trigger)
    
    # Checkpoint store — required for TD-033 rollback
    save_checkpoint(snapshot_id, profile_scorer.centroids.copy(), decision_count)
    return snapshot_id
```

**Rollback semantics (TD-033) — cross-reference:**
This section specifies checkpoint CREATION. Rollback EXECUTION semantics — trigger
conditions, execution mode, and Hook interaction during the rolled-back period — are
partially specified in §17.1 (Part 2, Reset Semantics) but require a dedicated §17.5
subsection that is not yet written. **§17.5 (Part 2) is a required addition before
ARCH-3 can be run.** Until it is written, do not build or test rollback execution.
Key facts from what is already specified:

- **Mode:** rollback-and-resume. Graph structure is preserved. Learning resumes from
  the checkpoint state after rollback completes. Rollback does NOT freeze learning.
- **Trigger conditions:** Three triggers are specified in §17.1 table (Part 2); full
  execution semantics for each trigger are **NOT YET WRITTEN** and belong in §17.5.
  Summary of known triggers: (1) IKS drop > 5 points in a single 50-decision window
  without an explicit reset; (2) admin manual rollback via `POST /api/admin/rollback`;
  (3) synthesis operator deactivated and centroid damage confirmed (EXP-OP2 finding:
  35% of cells never recover post-TTL — rollback is the only repair path).
- **Hook interaction:** OutcomeRecord (Hook 2) writes that occurred between the
  checkpoint and the rollback are cleared from the centroid learning history but
  PRESERVED in the audit trail with a ROLLBACK marker. ProfileSnapshot (Hook 3)
  writes during the rolled-back period are also preserved — they serve as the
  diagnostic evidence for why rollback was triggered.
- **ARCH-3 prerequisite:** §17.5 (Part 2) must be written and reviewed before ARCH-3
  is executed. Running ARCH-3 against an incomplete rollback spec produces
  untestable behavior.

---

## 10. v5.0 Scope — "Profiled + Evaluated + Realistic"

### 10.1 Guiding Principle

v5.0 is the technical foundation that makes v5.5 possible. It does not answer Q2 or Q3 from the Five Demo Questions. It makes the math correct, the data realistic, and the evaluation framework complete. v5.5 builds the *visibility layer* on top.

### 10.2 C=5 is Canonical for Production

```
Production SOC categories (C=5):
  [0] travel_anomaly       — T1078 Valid Accounts, VPN anomalies
  [1] credential_access    — T1078.004, T1110 Brute Force
  [2] threat_intel_match   — T1566.001, CISA KEV matches, IOC hits
  [3] insider_behavioral   — T1567 Exfiltration, T1021 Lateral Movement
  [4] cloud_infrastructure — T1048 Exfiltration over Alt Protocol

Healthcare (6th category) is SIMULATION VARIANT ONLY.
Never build a 6-category production ProfileScorer.
```

ProfileScorer shape: **(6, 4, 6)** — 6 categories × 4 actions × 6 factors. [CHANGED v5.5.1]
*Note: A=4 (escalate, investigate, suppress, monitor). refer_to_analyst removed as scorable action — accessed via referral rules R1-R7 (not confidence gate). Static accuracy improved 80.6→90.6% with A=4.*

### 10.3 v5.0 What It Proves

A CISO shown v5.0 sees:
- ProfileScorer with L2 distance scoring live
- Factor breakdown on every decision (6 values)
- Centroid values readable: `μ[credential_access, escalate,:] = [0.15, 0.88, 0.92, 0.10, 0.80, 0.20]`
- Evaluation result: "97.89% on *synthetic centroidal* data — validates the mechanism" (EXP-C1)
- Honest disclaimer: "71.7% on *realistic distributions* — your production baseline"

**What v5.0 does NOT show:** That the system is getting smarter (IKS not built). Recommendations in plain English (NL templates not built). Realized ROI (shadow mode not built). These are v5.5 obligations.

---

## 10.6 v5.5 Scope — "The Product" ✅ SHIPPED [CHANGED v5.5.1]

v5.5 closes all five CISO demo questions. **All Tier 1/2/3 items shipped March 2026.**

---

### Tier 1 — Demo-Blocking ✅ ALL SHIPPED

#### v5.5-R1: Category-Specific Auto-Approve Thresholds ✅ SHIPPED
*Gap closed: G-L3-1, G-L5-4. Closes Q3 (ROI) and Q4 (safety).*

Target: 40% overall coverage at ≥85% per-category accuracy. ✅ Achieved with A=4 + PROD-4 per-category thresholds.

**Fifth action economics:** Moving 35% of alerts from 15-min full review to 3-min `refer_to_analyst` pre-analysis recovers ~12 analyst-hours per 100 alerts — without changing auto-approve coverage.

#### v5.5-R2: Factor Provenance Nodes
*Gap closed: G-L4-1. Closes Q1 ("does it work?") by showing WHY.*

```python
@dataclass
class FactorComputerResult:
    """Extended FactorComputer output. v5.0: value only. v5.5: value + provenance."""
    value: float
    provenance_nodes: list["ProvenanceNode"] = field(default_factory=list)

@dataclass
class ProvenanceNode:
    node_type: str    # "TravelRecord", "ThreatIndicator", "Decision"
    node_id: str
    key_property: str # "destination_city"
    key_value: str    # "Singapore"
    contribution: str # "Unconfirmed travel to Singapore — no TravelRecord found in 90 days"
```

UI result: `travel_match: 0.87 — No TravelRecord to Singapore in 90 days, MDM-enrolled device, no IOC matches` instead of just `travel_match: 0.87`.

#### v5.5-R3: Centroid Drift Metric (Chart A Fix)
*Gap closed: G-L2-1. Makes learning visible on Tab 2.*

Chart A currently shows W delta norm ≈ 0.0 (ProfileScorer doesn't update W — wrong metric). Fix: replace with `‖μ_after − μ_before‖` from `OutcomeRecord.centroid_delta_norm`. Written on every `ProfileScorer.update()` call. Display: bar chart, one bar per verified decision. Spikes cluster on learning events. The story replaces the silence.

#### v5.5-R4: Institutional Knowledge Score (IKS)
*Gap closed: G-L2-2. The single most important missing feature for demo conversion. Closes Q2.*

Full specification in §22. A 0–100 score showing how far the system's operational centroids have drifted from bootstrap toward "full environment adaptation." The CISO metric for the strategic bet.

#### v5.5-R5: NL Template Engine (Layer 2 Explainability)
*Gap closed: Offering Gap 3. Closes Q1 for all three customer roles.*

Full specification in §23. 24 deterministic templates across three layers (analyst, CISO, auditor). No LLM required. The graph provides all data; templates provide the language.

#### v5.5-R5b: Tab-2 Two-Mechanism Redesign
*Gap closed: G-L2-3 (learning story not connected to triage), Offering Gap 4 (no operational learning narrative). Makes both Loop 2 mechanisms visible as a unified institutional intelligence story.*

**The architectural claim this surfaces:** Every other AI system in this space
learns to make better decisions. CI also learns to operate better. ProfileScorer
encodes what situations mean in this environment (decision intelligence).
AgentEvolver encodes how to operate in this environment (deployment intelligence).
Both compound permanently. Both must be visible — invisible learning is a black
box, not institutional intelligence.

**Four changes required:**

1. **Institutional Intelligence summary panel** (top of Tab-2, above all sections):

```
┌─ Institutional Intelligence — [deployment name] ────────────────────────┐
│                                                                           │
│  Situational Understanding        Deployment Adaptation                  │
│  (ProfileScorer)                  (AgentEvolver)                         │
│                                                                           │
│  Categories converging:  3        Active variant:   v2                   │
│  Categories adapting:    2        Promotions (session): 1                │
│  Categories cold:        1        False escalation reduction: 16.5%      │
│                                                                           │
│  847 verified decisions · Both mechanisms active · System is adapting    │
│  IKS: 47.3  ↑ +3.1 this week                                            │
└──────────────────────────────────────────────────────────────────────────┘
```

Data sources: centroid convergence status from ProfileSnapshot history;
AgentEvolver live session stats; IKS from §22.

2. **Four-section left-rail navigator** (replaces undifferentiated scroll):
   - Section A: This Decision (anchored to Tab-3 bridge link or most recent event)
   - Section B: Situational Understanding (ProfileScorer centroid story)
   - Section C: Deployment Adaptation (AgentEvolver operational story)
   - Section D: System Health (IKS, drift alerts, rollback status)

3. **Tab-3 bridge panel** (in Outcome Feedback section of Tab-3):
   After centroid update line, add:
   `→ See how this decision fits into the category learning curve  [Learning Impact]`
   Passes decision ID. Only shown when centroid_delta_norm > 0.

4. **AgentEvolver section copy correction**: Replace "demo data — live tracking in v5.0"
   label with two-layer display: seeded baseline (gray, "15 historical baseline decisions")
   + real session data (colored, labeled by session). v5.0 is now — the label is stale.

Full visualization specification: platform_visualization_design_v02.md §4.
Sprint prompt: WIRING-1 must complete before VIS-2 (Tab-2/Tab-4 frontend sprint).
Gate: Tab-3 bridge navigates to Tab-2 Section A anchored to the correct decision.



---

### Tier 2 — Sales-Blocking ✅ ALL SHIPPED

#### v5.5-R6: Alert Type → Category Mapping Completion
*Gap closed: G-L1-1 [BLOCKING]. Silently misclassifies ~20% of alerts today.*

Full mapping table in `get_alert_category_mapping()` (§14). Every unrecognized `alert_type` → ERROR log. Never silent default.

#### v5.5-R7: Threat Intelligence Persistence (ThreatIndicator Nodes)
*Gap closed: G-L4-3, G-L4-4. Closes Q5 partially ("why not Security Copilot?").*

On every Pulsedive / CISA KEV query: write ThreatIndicator node to Neo4j (MERGE — idempotent). Second query on same IOC: read from graph, zero API call. After 6 months: 400+ firm-specific IOC nodes with edges to prior alerts, categories, and outcomes. This is the IOC memory Security Copilot cannot provide.

#### v5.5-R8: Shadow Mode
*Gap closed: Offering Gaps 1, 2. Closes Q3 and Q4 entirely.*

Full specification in §21. 30-day observation period. System scores every alert, shows no recommendation. At end: shadow report with agreement rate by category, top disagreements with factor breakdowns. [ACTIVATE LIVE MODE] button after customer reviews.

#### v5.5-R9: Docker Compose VPS Deployment
*Gap closed: Offering Gap 1. Enables hosted CISO demo URL.*

Single-command deployment: `docker compose up -d && ./scripts/seed_and_verify.sh`. Includes: backend (FastAPI), frontend (React/Vite), Neo4j 5.15, Ollama (narrative LLM). Full demo with 25 alerts, 200+ users, ATT&CK labels.

#### v5.5-R10: Tab 1 Graph Explorer — F14-basic (Ask the Graph)
*Gap closed: Offering Gap 2. Partially closes Q5.*

Promotes the existing `POST /api/soc/query` endpoint (query.py) to a dedicated **Tab 1 Panel B** — "Graph Explorer". Domain-agnostic: `POST /api/{domain}/query`. 20+ structured query templates via QueryCatalog, NL fast-path routing via QueryRouter, inline 2-3 hop decision path mini-graph per result, "Explore in Bloom" deep-link. No new LLM dependency — structured queries only. Full specification in §24.

**Note:** Tab 5 (exec learning narrative) launches at v6.0, not v5.5. See §24 for the Tab 5 v6.0 spec and the distinction between the analyst Graph Explorer (Tab 1 Panel B) and the exec learning narrative (Tab 5).

---

### Tier 3 — Enterprise-Readiness ✅ ALL SHIPPED

#### v5.5-R11: Graduated Human Review Tiers
*Gap closed: G-L5-2.*

Replace binary "HUMAN REVIEW" flag:
- ≥ category_threshold → **AUTO-APPROVE** (~40% of alerts)
- 0.70 – threshold → **REFER TO ANALYST** — 3-min pre-analyzed review (~35%)
- < 0.70 → **REVIEW REQUIRED** — tier-2 analyst, full investigation (~25%)

**Design estimate note:** The 0.70 confidence floor separating REFER TO ANALYST from
REVIEW REQUIRED, and the implied ~35%/~25% split, are design estimates derived from
v4.5 UX iteration — not from the accuracy-confidence calibration curve. The
mathematically correct values are: the confidence level at which per-category accuracy
drops below an acceptable floor (estimated 65%) defines REFER TO ANALYST; below a
second floor defines REVIEW REQUIRED. Both floors must be derived empirically from
PROD-4 per-category accuracy-vs-threshold curves (experiment_reference_catalog_v2, PROD-4 entry)
before being hardcoded in `CalibrationProfile.review_thresholds`. The 0.70 estimate
may be correct but cannot be confirmed until PROD-4 runs. Do not hardcode this value
as a named constant until PROD-4 result is available.

#### v5.5-R12: Centroid Drift Alerts
*Gap closed: G-L5-3. Prevents silent centroid drift from biased feedback.*

When `‖μ[c,a,i] − μ₀[c,a,i]‖ > max_single_cell_drift` (configurable, default 0.30): admin notification + checkpoint available. Does NOT auto-revert — requires human decision.

#### v5.5-R13: Evidence Export (Compliance Format)
*Gap closed: Offering Gap 5. EU AI Act Article 9/12/13 partial compliance.*

PDF + CSV export from Evidence Ledger using Layer 3 NL templates. Fields: decision_id, timestamp, alert_id, factor_breakdown, action, confidence, outcome, analyst_override, centroid_state_hash.

**EU AI Act Article 9 — Known Risk Disclosure (mandatory before v5.5 ships):**

The following known risk must appear in the Article 9 risk management log included with
every v5.5 deployment. Omitting it before the August 2026 enforcement deadline is a
compliance gap.

> **N3 Endogenous Feedback Loop (Known Risk — no intervention point designed)**
>
> Description: The system's calibration state may influence which decisions are selected
> for analyst verification (e.g., high-confidence decisions are less likely to be
> reviewed). If verification selection is systematically biased, Loop 2 (centroid
> learning) learns from a biased sample of outcomes, which may gradually degrade
> calibration, which further biases verification selection. This is a self-reinforcing
> loop with no currently designed intervention point.
>
> Current mitigation: Shadow mode deployment (v5.5-R8) provides a 30-day baseline
> measurement period during which the system's recommendations are compared against
> analyst decisions on ALL alerts — not just verified ones. Analysis of the shadow
> report will indicate whether verification selection is systematically biased before
> live mode is activated. Full characterization requires real analyst decision data
> (EXP-S8, v6.0+).
>
> Residual risk level: MEDIUM. The loop requires both systematic calibration error AND
> systematic verification selection bias to manifest. Shadow mode measurement partially
> mitigates by providing an independent accuracy signal.

This disclosure satisfies Article 9(2)(a) (identification of risks to natural persons)
and Article 9(2)(b) (risk management measures). Full GDPR right-to-erasure for
decision nodes and Article 13 transparency notice are v6.0 scope.

---

## 11. Product Flow

### 11.1–11.4 (Preserved from v5.2 — Before GAE, After GAE v4.1, After v4.5, After v5.0)

---

### 11.5 After v5.5 — The Product (PLANNED)

```
───── TAB 3: ALERT TRIAGE (Daily driver — Role 1 adoption surface) ─────

Alert arrives → SituationAnalyzer classifies category c
  → compute_factor_vector() → f ∈ [0,1]^6 with provenance_nodes     [R2 NEW]
  → ProfileScorer: P(a|f,c) = softmax(-K(f, μ[c,a,:]) / 0.1)
  → Category-specific threshold applied                               [R1 NEW]

  TWO INDEPENDENT ROUTING DECISIONS:                                   [NEW v5.5.2]

  Action routing (from ProfileScorer, A=4):
    Confidence ≥ threshold → AUTO-APPROVE (40% of alerts)            [R1]
    Medium confidence → INVESTIGATE (analyst reviews with context)
    Low confidence → ESCALATE (full review)

  Referral routing (from ReferralEngine, independent):                [NEW v5.5.2]
    R1-R7 rules evaluated against alert context
    ANY rule fires → REFER TO ANALYST (VETO — overrides auto-approve)
    Rules are: executive account, rapid succession, compliance mandate,
      high-value data, active incident, new asset, cross-category
    Confidence gate NOT used for referral (14% precision = active harm)

  Referral is a VETO: if any rule fires, auto-approve pauses even at 95% conf.
  Evidence Ledger logs: "Referred: R1 (executive account, identity_tier=executive)"

  Decision node written with shadow_mode=False (or True if in shadow)
  Three data hooks written: DecisionRecord, ProfileSnapshot (if trigger)

  Tab 3 display per alert:
    ATT&CK badge: T1078 · Valid Accounts · Initial Access
    
    NL one-liner (Layer 1 template):                                  [R5 NEW]
      "Anomalous Singapore login (no TravelRecord, 90 days).
       MDM-enrolled device. No active IOC matches.
       SUPPRESS at 91% confidence — calibrated from 47 verified outcomes."
    
    Factor breakdown — 6 bars WITH provenance:                        [R2 NEW]
      travel_match:            0.87 → "No TravelRecord to Singapore in 90 days"
      asset_criticality:       0.42 → "MEDIUM — stores PII DataClass"
      threat_intel_enrichment: 0.21 → "No ThreatIndicator matches (412 checked)"
      pattern_history:         0.78 → "34/44 prior travel_anomaly correctly suppressed"
      time_anomaly:            0.31 → "Login at 14:32 UTC — within business hours"
      device_trust:            0.91 → "MDM-enrolled, last seen 4h ago, no alerts"
    
    Similar past cases: 3 suppress decisions on Singapore travel for this user  [NEW]
    
    After feedback submitted:                                         [R3 NEW — learning visible]
      "Your feedback updated the travel_anomaly profile.
       Centroid drift: 0.0023. suppress now weighted higher for
       MDM-enrolled devices with no recent IOC matches."

───── TAB 2: RUNTIME EVOLUTION / LEARNING IMPACT (Proof-of-compounding surface — Role 2) ─────

  ┌─ Institutional Intelligence — [deployment name] ──────────────────────────┐
  │                                                                             │
  │  Situational Understanding        Deployment Adaptation                    │
  │  (ProfileScorer)                  (AgentEvolver)                           │
  │                                                                             │
  │  Categories converging:  3        Active variant:   v2                     │
  │  Categories adapting:    2        Promotions (session): 1                  │
  │  Categories cold:        1        False escalation reduction: 16.5%        │
  │                                                                             │
  │  847 verified decisions · Both mechanisms active · System is adapting      │
  │  IKS: 47.3  ↑ +3.1 this week                                              │
  └──────────────────────────────────────────────────────────────────────────┘

  [A] This Decision  [B] Situational Understanding  [C] Deployment Adaptation  [D] System Health
  ──── left-rail section navigator ────

  Section A — This Decision (anchored from Tab-3 bridge, or most recent event): [CHANGED v5.5.1]
    Purple summary card pattern. Shows when a decision in the current session
    is matched. Does NOT attempt eval gate trace until live triage produces a
    completed decision in the same session. Before first matched decision:
    shows "Triage an alert to see decision analysis here."
    
    When matched:
    Decision: DEC-C15B for ALERT-7823
    Eval Gate: PASS (0.865)  ·  GAE Scoring: investigate 51.1% / escalate 48.8%
    Centroid update: credential_access → investigate  ‖Δμ‖ = 0.0021  ↑ Reinforced
    Policy conflict: none detected

  Section B — Situational Understanding (ProfileScorer):
    "What your environment's patterns have taught the system"
    IKS: 47.3  (+2.1 this week)                                       [R4]
    [IKS Trend Chart — 90-day history from ProfileSnapshot nodes]
    Chart A: Centroid Drift per Verified Decision                      [R3 — replaces wrong metric]
      Bar chart: one bar per decision, height = ‖Δμ‖.
      Colored: Reinforced (green) / Corrected (orange).
      "Average drift 0.0041/decision. Largest: 0.0089 on credential_access."
    Per-category convergence: [Converging × 3] [Adapting × 2] [Cold-start × 1]
    Profile Centroids table: μ values per (category, action) with n= counts.
    "What your system learned this week" (NL template):               [R5]
      "credential_access centroids shifted toward requiring higher
       threat_intel_enrichment (0.71→0.81) for suppress actions."

  Section C — Deployment Adaptation (AgentEvolver):
    "How the system has learned to operate in your environment"
    Active variant: TRAVEL_CONTEXT_v2  (promoted after 87.5% session accuracy)
    Promotions this session: 1  ·  False escalation reduction: 16.5%
    Variant performance chart:
      TRAVEL_CONTEXT_v1: 71.0%  [gray — historical baseline, 15 decisions]
      TRAVEL_CONTEXT_v2: 87.5%  [green — this session, 34 decisions]
    What changed: "System learned that VPN location + travel record together
      indicate safe access. 33 fewer Tier 2 reviews/month."

  Section D — System Health:
    IKS trend  ·  Drift alerts (if any)  ·  Rollback status  ·  Graph stats

───── TAB 4: COMPOUNDING ANALYSIS (ROI and autonomy story — Role 2) ─────

  Shadow mode status indicator (if applicable)
  
  ROI block — REALIZED numbers (not projected):                       [R8 NEW]
    "Since shadow mode activated 23 days ago:
     847 decisions recorded. 74.3% analyst agreement.
     Projected post-activation: 28.4 analyst-hours/week saved."
  
  Auto-approve coverage by category:                                  [R1 NEW]
    cloud_infrastructure:   49%  ← "routine scans — low risk, high confidence"
    threat_intel_match:     43%  ← "known-benign IOC matches"
    travel_anomaly:         31%
    credential_access:      16%
    insider_behavioral:      2%  ← CORRECT — catastrophic risk, near-zero by design
  
  Evidence export: [Download PDF] [Download CSV]                      [R13 NEW]

───── TAB 5: EXEC LEARNING NARRATIVE (v6.0 — not v5.5) ─────

  ┌─ Section 1: What Changed Since Last Time ──────────────────────────────┐
  │  IKS: 41.2 → 47.3  (+6.1 this week)                                   │
  │  Driven by 89 verified outcomes in lateral_movement, credential_access  │
  │                                                                          │
  │  Judgment shifts this week (3 categories):                               │
  │  · lateral_movement: escalation threshold tightened 18%                 │
  │    (12 decisions involving EPSS > 0.8 CVEs)                             │
  │  · credential_access: auto-approve rate up 4.3%                         │
  │  · cloud_infrastructure: no significant drift                            │
  │                                                                          │
  │  247 decisions · 31 auto-approved (12.6%, up from 9.1% last week)       │
  └──────────────────────────────────────────────────────────────────────────┘

  ┌─ Section 2: What Was Discovered ───────────────────────────────────────┐
  │  · CVE-2026-1234 added to CISA KEV — first seen in your alert queue     │
  │    4 days ago. 2 alerts retroactively re-scored. 1 disposition changed. │
  │  · Asset group "APAC-DB-tier" appeared in 7 alerts this week (up from 1)│
  │    Compound exposure flag triggered. Analyst review recommended.         │
  └──────────────────────────────────────────────────────────────────────────┘

  ┌─ Section 3: What the System Now Knows ─────────────────────────────────┐
  │  lateral_movement:    312 verified outcomes — judgment: HIGH confidence  │
  │  credential_access:   156 verified outcomes — judgment: SOLID            │
  │  cloud_infrastructure: 89 verified outcomes — judgment: DEVELOPING       │
  │  data_exfiltration:    23 verified outcomes — judgment: WEAK             │
  │    ↳ auto-approve disabled — insufficient learning                       │
  │                                                                          │
  │  IKS since deployment: ▁▂▃▄▅▆▇ 47.3  [The system is still learning]    │
  │                                                                          │
  │  [Export Board Briefing PDF]                                             │
  └──────────────────────────────────────────────────────────────────────────┘

  Note: Tab 1 Panel B (Graph Explorer) is the analyst query surface.
  Tab 5 is exec-only — no alert detail, no graph queries, no factor vectors.

───── SHADOW MODE BANNER (first deployment — any new customer) ─────

  Tab header: "SHADOW MODE — System observing, not influencing decisions"
  Progress: 847/1000 decisions recorded
  
  After threshold reached → Shadow Report generated:
    "System agreed with your analysts on 74.3% of alerts."
    "Top disagreement category: insider_behavioral (61%)."
    "12 specific disagreements for your review — with factor breakdowns."
    
    [ACTIVATE LIVE MODE] ← explicit click required. Never auto-activates.
```

### 11.6 After v6.0 — Differentiated (PLANNED, gates apply)

```
  If GATE-M passes:
    CISA KEV → σ[threat_intel_match, escalate] adjusted proactively
    "Active campaign CVE-2026-1234 affects 3 assets in your environment.
     Your triage posture for affected categories has been automatically adjusted
     before any alert fires."
  
  ServiceNow integration (human-approved by default):
    escalate → ServiceNow P2 incident created
    "Incident INC0047283 created. Analyst review required in ServiceNow."
  
  S2P copilot demo:
    "Same learning engine, different domain — procurement judgment."
    "Both compounding. Both auditable. One platform."
```

---

## 12. Build Sequence (Summary)

```
COMPLETED:
  v4.1 GAE Foundation ✅  (34 prompts)
  v4.5 Make It Real ✅    (13 prompts)
  Bridge Experiments ✅   (25 experiments — architecture settled)

IN PROGRESS:
  v5.0 (29 prompts) — Profiled + Evaluated + Realistic
    3 repos, 3 milestones: v5.0-alpha → v5.0-beta → v5.0 TAG

NEXT:
  v5.5 (~25 prompts) — The Product
    Priority: R1→R2→R3→R4→R5 (Tier 1)
              R6→R7→R8→R9→R10 (Tier 2)
              R11→R12→R13 (Tier 3)
    Platform prompts (ci-platform): SemanticRegistry, QueryCatalog,
                     EnterpriseConnectorProfile (~7 prompts)
    GAE prompts: category threshold API, IKS primitives (~3 prompts)
    SOC prompts: shadow mode, NL templates, Tab 1 Graph Explorer (F14-basic), IKS display (~15 prompts)
  
  v6.0 — First Customer + Differentiation
    σ synthesis (GATE-M), ServiceNow write-back, S2P domain, Multi-SIEM, Attack chains
  
  v7.0+ — Moat Deepens
    Cross-tenant meta-intelligence, NHI behavioral baseline, A2A/MCP
```

---

## 13. Claude Code Rules (All SOC Copilot Prompts)

```
RULES — SOC COPILOT REPO:

[Core discipline]
- Do NOT use git directly. I handle all git operations.
- Do NOT start the debugger. Log-based debugging only.
- Read before write. One concern per prompt.
- No GAE math in copilot — use gae.scoring, gae.learning, gae.factors, gae.profile_scorer.
- Language: "product" not "demo" in all comments, docstrings, UI text.

[Imports]
- ProfileScorer: from gae.profile_scorer import ProfileScorer, build_profile_scorer
- CalibrationProfile: from gae.calibration import CalibrationProfile
- ReferralEngine: from gae.referral import ReferralEngine, ReferralDecision [NEW v5.5.2]
- Referral rules: from app.services.referral_rules import get_soc_referral_rules [NEW v5.5.2]
- Data hooks: from gae.hooks import DecisionRecord, OutcomeRecord, ProfileSnapshot
- NL templates: from app.services.nl_templates import NLTemplateEngine
- Similar cases: from app.services.similar_cases import SimilarCasesService
- EvaluationReport uses by_category (not by_technique) — S2P co-design fix.

[Scoring architecture]
- ProfileScorer IS the scoring mechanism. ScoringMatrix is DEPRECATED (TD-029).
- All τ defaults = 0.1 (V3B validated ECE=0.036). Never use 0.25 (TD-030 CLOSED).
- All centroid updates MUST clip to [0.0, 1.0] (V2 validated escape at dec 6–12).
- ProfileScorer shape is (C, A, d) = (6, 4, 6). A=4: escalate, investigate, suppress, monitor. [CHANGED v5.5.1]
  refer_to_analyst removed as scorable action — via referral rules, not confidence gate.
- C=6 is production (credential_access, threat_intel_match, lateral_movement,
  data_exfiltration, insider_threat, cloud_infrastructure). HC is simulation only.
- TD-027 RESET RULE: reset μ from DomainConfig.get_profile_centroids(). Do NOT copy W→μ.
- DiagonalKernel is v6.0 default for noise_ratio > 1.5. L2 is cold-start fallback. [NEW v5.5.1]
  Dot product is forbidden (EXP-C1: 61% vs 97.89%).

[Actions]
- refer_to_analyst is accessed via REFERRAL RULES (R1-R7), not confidence gate. [CHANGED v5.5.2]
- It does NOT have a centroid profile — it is not in the centroid tensor.
- Action routing and referral routing are INDEPENDENT. Both fire on every alert.
- A=4 improves static accuracy 80.6→90.6% and eliminates dangerous action confusion.

[Referral routing — NEW v5.5.2]
- Referral is a VETO: any rule fires → refer to analyst, regardless of confidence.
- Confidence gate is for ACTION routing only (low confidence → investigate). NOT for referral.
- EXP-REFER-LAYERED validated: rules 72.7% DR, 12% FPR. Conf gate: 14% precision = harm.
- ReferralEngine imported from GAE. SOC rules in app/services/referral_rules.py.
- Rules are pure functions: no state, no ML, no side effects. Fully auditable.
- Missing context data → rule doesn't fire (safe degradation, not false positive).
- Customer configures rules during onboarding (thresholds overridable).
- OverrideDetector (v6.5): activates when ≥50 production override positives accumulated.
- Referral NEVER modifies ProfileScorer scoring or centroids. P-REF-1 is permanent.

[Factor computers]
- Factor Cypher MUST traverse relationships, not read properties (P10: TD-014/015).
- FactorComputerResult must include provenance_nodes from v5.5 onward.
- PatternHistoryFactor (§5.2, W1 path): minimum 5 decisions before non-default score (0.5 symmetric prior).
- PatternHistoryFactorComputer (§5.6, W2 path): [NEW v5.5.3]
  * Import: from domains.soc.factors import PatternHistoryFactorComputer
  * FACTOR_INDEX = 4 ONLY. Never touch factors [0,1,2,3,5].
  * FALLBACK = 0.40. Do NOT change without re-running V-TRIGGERED-EVOLUTION.
  * Reads TRIGGERED_EVOLUTION edges with verified_correct=true only.
  * Recency weighting: exp(-days/30), normalized to [0,1]. Never use raw weights.
  * When no TRIGGERED_EVOLUTION edges: return FALLBACK=0.40 (not 0.5, not 0.0).
  * NEVER mix TRIGGERED_EVOLUTION (W2) with DECIDED_ON (W1) in the same query.
  * The W2 read path is what makes CLAIM-W2 (+10.13pp) work. Do not simplify it.

[Similar past cases — SimilarCasesService]
- SIMILAR_CASES_MIN_SIM default = 0.85. This is a design estimate pending PROD-3
  empirical calibration. Do NOT raise it above 0.90 or lower below 0.75 without
  PROD-3 cosine distribution data.
- SIMILAR_CASES_CATEGORY_FILTER = True is NON-NEGOTIABLE. Never retrieve cross-
  category cases — produces misleading agreement percentages.
- Suppress the "similar cases" sidebar entirely if fewer than
  SIMILAR_CASES_MIN_DECISIONS (=5) verified decisions exist in the category.
  Return None from get_agreement_pct(); use the fallback L1 template wording.
- SimilarCasesService must be called AFTER ProfileScorer.score(), BEFORE
  NLTemplateEngine.render_l1(). The agreement_pct feeds into the L1 template context.

[Data preservation hooks — MANDATORY v5.0 write obligations]
- DecisionRecord on EVERY score() call (including shadow mode decisions).
- OutcomeRecord on EVERY update() call.
- ProfileSnapshot EVERY 50 decisions minimum AND on every operator start.
- These are the Level 2/3 substrate. Without them, GATE-R cannot run, TD-033 has no data,
  and IKSService.get_iks_trend() returns empty.

[Shadow mode]
- Shadow decisions: shadow_mode=True in Decision node. Action NOT shown in UI.
- analyst_action recorded separately on every decision. agreement flag computed.
- Shadow report generated after N decisions. NEVER auto-activates live mode.
- Explicit [ACTIVATE LIVE MODE] click required. Any auto-activation is a design violation.

[Intelligence layer — synthesis boundary]
- λ operative window: λ∈[0.5, 0.6] with Loop 2 running. Never deploy λ>0.6.
- ProfileScorer.update() has NO synthesis parameter. σ NEVER flows into update().
- Loop 2/Loop 4 firewall is permanent. Corrupting this corrupts the centroid learning signal.
- λ=0 for any untested deployment. Default: no synthesis activation.
- get_domain_constraint_spec() returns {} until domain expert review + GATE-M pass.

[Scope boundaries]
- GraphAttentionBridge + DiscoveryEngine are GAE-only concerns (v7.0, v8.0). Never here.
- S2P co-design: every configurable field must remain domain-generalizable. See §1.6.
- EvaluationReport.by_category — never by_technique. S2P has no ATT&CK.

[Enterprise integration]
- EnterpriseAction.requires_human_approval = True by default. Cannot be overridden without
  30-day shadow mode agreement rate review.
- ServiceNow write-back: shadow mode governs activation cadence. Never live before shadow.
```

---

## 14. SOCDomainConfig

```python
# backend/app/domains/soc/config.py

from gae.calibration import CalibrationProfile
from gae.factors import FactorComputer
import numpy as np
from dataclasses import dataclass, field
from typing import Optional

class SOCDomainConfig:
    """SOC domain configuration — the copilot's compiled domain expertise.
    
    This class IS the domain expertise. It contains:
      (a) Pure domain knowledge: centroids, categories, thresholds, action definitions
      (b) Infrastructure pointers: connectors, concepts, schema registrations
    
    Nothing in this class is math. The math is in GAE.
    
    SHAPE NOTE (v5.5.1 change): [CHANGED v5.5.1]
      get_profile_centroids() returns shape (6, 4, 6).
      Previously (5, 5, 6) at A=5. Now (6, 4, 6): 6 categories × 4 actions × 6 factors.
      refer_to_analyst REMOVED as scorable action — via referral rules R1-R7 (not confidence gate).
    
    KERNEL NOTE (v5.5.1): [NEW v5.5.1]
      Default kernel: DiagonalKernel(weights=1/σ²) for noise_ratio > 1.5.
      Fallback: L2Kernel. Kernel selected during P28 deployment qualification.
    
    LEARNING NOTE (v5.5.1): [NEW v5.5.1]
      learning_enabled = False by default. Enable per-customer after shadow.
      eta_confirm = 0.05, eta_override = 0.01 (P0 fix, asymmetric η).
      auto_pause_on_amber = False default (enable after conservation monitoring active).
    
    S2P CO-DESIGN: Every method here has an S2P analog.
    Constraint: no method body may hard-code SOC-specific structure.
    """

    @staticmethod
    def get_actions() -> list[str]:
        """Five production actions. ORDER IS PERMANENT — bound to centroid axis 1.
        
        S2P analog: ["approve", "hold_for_review", "reject",
                     "escalate_compliance", "refer_to_analyst"]
        """
        return ["escalate", "investigate", "suppress", "monitor"]  # A=4 [CHANGED v5.5.1]
        # NOTE: refer_to_analyst REMOVED as scorable action. Via referral rules R1-R7 (not confidence gate).

    @staticmethod
    def get_categories() -> list[str]:
        """C=6 production SOC categories. ORDER IS PERMANENT — bound to centroid axis 0. [CHANGED v5.5.1]
        
        S2P analog: ["routine_purchase", "high_value_contract", "sole_source",
                     "compliance_sensitive", "emergency_procurement"]
        """
        return [
            "credential_access",    # index 0: T1078.004, T1110
            "threat_intel_match",   # index 1: T1566, CISA KEV, IOC
            "lateral_movement",     # index 2: T1021, T1210
            "data_exfiltration",    # index 3: T1567, T1048
            "insider_threat",       # index 4: T1078, behavioral
            "cloud_infrastructure", # index 5: T1048, cloud-specific
        ]

    @staticmethod
    def get_factor_computers() -> list:
        """6 FactorComputer implementations. ORDER IS PERMANENT — bound to centroid axis 2.
        
        S2P analog: 6 procurement factors in a different order.
        """
        return [
            TravelMatchFactor(),            # index 0: travel_match
            AssetCriticalityFactor(),       # index 1: asset_criticality
            ThreatIntelEnrichmentFactor(),  # index 2: threat_intel_enrichment
            PatternHistoryFactorComputer(), # index 3: pattern_history (W2 read path — §5.6)
                                            # W2 path: TRIGGERED_EVOLUTION edges (CLAIM-W2)
                                            # W1 fallback (§5.2 PatternHistoryFactor) when no edges
                                            # FACTOR_INDEX = 4. Fallback = 0.40.
            TimeAnomalyFactor(),            # index 4: time_anomaly
            DeviceTrustFactor(),            # index 5: device_trust
        ]

    @staticmethod
    def get_profile_centroids() -> np.ndarray:
        """μ₀: (6, 4, 6) — 6 categories × 4 actions × 6 factors. [CHANGED v5.5.1]
        
        Expert-configured action profiles. These are NOT guesses — they are
        domain expertise compiled to geometry. Each μ[c, a, :] is the factor
        vector a security expert would associate with "action a is correct
        for category c."
        
        Shape: [CHANGED v5.5.1]
          Axis 0: category  [credential_access, threat_intel_match, lateral_movement,
                             data_exfiltration, insider_threat, cloud_infrastructure]
          Axis 1: action    [escalate, investigate, suppress, monitor]   (A=4)
          Axis 2: factor    [travel, asset, threat_intel, time, pattern, device]
        
        NOTE: refer_to_analyst REMOVED from centroid tensor (A=4 migration).
        Static accuracy improved 80.6→90.6%. Zero dangerous actions.
        
        Validation (on SYNTHETIC centroidal data):
          EXP-C1: 97.89% zero-learning accuracy
          EXP-B1: 98.2% with learning
        
        Production baseline (50-seed realistic):
          71.7% static, 78.9% at 1,000 decisions
        
        LEARNING NOTE: These are μ₀ — starting points. After deployment they drift
        toward the firm's actual operational reality. That drift IS the product value.
        """
        # ── Axis 2 factor order: [travel, asset, threat_intel, pattern, time, device] ──

        # Category 0: credential_access [CHANGED v5.5.1: was travel_anomaly at index 0]
        credential_access = np.array([
            # escalate: after-hours, high criticality, IOC match, novel pattern
            [0.15, 0.88, 0.92, 0.80, 0.10, 0.20],
            # investigate: anomalous but no threat intel confirmation
            [0.10, 0.60, 0.40, 0.65, 0.30, 0.40],
            # suppress: known pattern, low criticality, trusted device
            [0.08, 0.20, 0.08, 0.15, 0.85, 0.90],
            # monitor: borderline credential activity — watching
            [0.10, 0.40, 0.25, 0.40, 0.55, 0.55],
        ])

        # Category 1: threat_intel_match
        threat_intel = np.array([
            # escalate: active campaign, critical asset, confirmed IOC
            [0.20, 0.90, 0.95, 0.50, 0.15, 0.30],
            # investigate: partial IOC match — worth checking
            [0.15, 0.65, 0.60, 0.45, 0.25, 0.45],
            # suppress: known false positive campaign match
            [0.08, 0.25, 0.12, 0.20, 0.80, 0.70],
            # monitor: weak IOC signal, low-priority campaign
            [0.12, 0.40, 0.35, 0.35, 0.55, 0.50],
        ])

        # Category 2: lateral_movement [CHANGED v5.5.1]
        lateral_movement = np.array([
            # escalate: multi-hop movement, high-value target
            [0.30, 0.80, 0.55, 0.60, 0.20, 0.35],
            # investigate: single lateral hop, ambiguous intent
            [0.20, 0.55, 0.35, 0.45, 0.35, 0.45],
            # suppress: authorized admin movement, known pattern
            [0.10, 0.25, 0.10, 0.20, 0.80, 0.85],
            # monitor: lateral activity within normal scope
            [0.15, 0.35, 0.25, 0.35, 0.60, 0.55],
        ])

        # Category 3: data_exfiltration [CHANGED v5.5.1]
        data_exfiltration = np.array([
            # escalate: large volume, critical data, anomalous destination
            [0.25, 0.90, 0.70, 0.55, 0.15, 0.25],
            # investigate: unusual data access, needs context
            [0.15, 0.60, 0.45, 0.45, 0.30, 0.40],
            # suppress: routine backup, known destination, authorized
            [0.08, 0.15, 0.08, 0.15, 0.85, 0.90],
            # monitor: low-volume data movement, watching
            [0.12, 0.35, 0.25, 0.30, 0.60, 0.60],
        ])

        # Category 4: insider_threat [CHANGED v5.5.1: was insider_behavioral]
        insider_threat = np.array([
            # escalate: anomalous data access, high criticality, declining pattern
            [0.35, 0.85, 0.60, 0.55, 0.15, 0.30],
            # investigate: single behavioral anomaly — check further
            [0.28, 0.62, 0.40, 0.50, 0.35, 0.45],
            # suppress: consistent historical pattern, low-risk data
            [0.12, 0.15, 0.18, 0.15, 0.85, 0.70],
            # monitor: behavioral flag, watching for escalation
            [0.25, 0.38, 0.30, 0.40, 0.60, 0.50],
        ])

        # Category 5: cloud_infrastructure
        cloud_infrastructure = np.array([
            # escalate: unusual cloud activity, unknown device, no pattern
            [0.15, 0.55, 0.65, 0.40, 0.18, 0.20],
            # investigate: cloud anomaly worth checking
            [0.10, 0.40, 0.40, 0.38, 0.35, 0.38],
            # suppress: routine cloud access, known pattern, trusted device
            [0.08, 0.18, 0.12, 0.12, 0.82, 0.88],
            # monitor: low-risk cloud activity
            [0.10, 0.28, 0.22, 0.22, 0.65, 0.60],
        ])

        centroids = np.stack([
            credential_access, threat_intel, lateral_movement,
            data_exfiltration, insider_threat, cloud_infrastructure
        ])  # shape: (6, 4, 6) [CHANGED v5.5.1]

        assert centroids.shape == (6, 4, 6), f"Expected (6,4,6), got {centroids.shape}"
        assert centroids.min() >= 0.0 and centroids.max() <= 1.0, \
            f"Values outside [0,1]: min={centroids.min()}, max={centroids.max()}"
        return centroids

    @staticmethod
    def get_calibration_profile() -> CalibrationProfile:
        """SOC learning hyperparameters.
        
        τ=0.1: Validated synthetic (V3B, ECE=0.036). NEVER change to 0.25 (TD-030 CLOSED).
        penalty_ratio=20.0: IBM breach cost ~$4.44M vs false positive ~20min. 
        
        S2P analog: penalty_ratio=5.0 (wrong PO = overspend, not breach).
                    temperature=0.4 (procurement allows deliberation — needs validation).
        """
        return CalibrationProfile(
            learning_rate=0.01,
            penalty_ratio=20.0,       # SOC-specific. 20:1 asymmetry.
            temperature=0.1,          # τ=0.1. Validated. DO NOT CHANGE.
            epsilon_default=0.001,
            discount_strength=0.0,    # A1-FIX deferred — measure first (post EVAL-2)
            decay_class_rates={
                "campaign":  0.005,   # threat intel — evolves over weeks
                "standard":  0.001,   # normal triage patterns
                "permanent": 0.0001,  # asset criticality — stable
                # S2P adds "transient": 0.02 for commodity prices
            },
        )

    @staticmethod
    def get_category_thresholds() -> dict[str, float]:
        """Per-category auto-approve thresholds (v5.5-R1, G-L3-1, G-L5-4).
        
        VALIDATION REQUIRED: 50-seed validated, ≥40% coverage, ≥85% per-category accuracy.
        These values are PROPOSALS until validation is complete.
        
        S2P analog: thresholds based on procurement risk levels and financial exposure.
        """
        return {
            "travel_anomaly":       0.85,
            "credential_access":    0.90,
            "threat_intel_match":   0.80,
            "insider_behavioral":   0.95,  # near-zero coverage — correct (catastrophic risk)
            "cloud_infrastructure": 0.80,
        }

    @staticmethod
    def get_alert_category_mapping() -> dict[str, str]:
        """Complete alert_type → category mapping (v5.5-R6, G-L1-1 BLOCKING FIX).
        
        Rules:
          1. Every recognized alert_type maps to exactly one of the 5 canonical categories.
          2. Unrecognized alert_type → ERROR log. NEVER a silent default.
          3. Maintained by domain experts, not developers. Changes require expert sign-off.
        
        Note: This table must reach ~200+ entries via domain expert review before v5.5 ships.
        The entries below are the validated starting set.
        """
        return {
            # travel_anomaly
            "TRAVEL_ANOMALY":           "travel_anomaly",
            "VPN_ANOMALY":              "travel_anomaly",
            "UNUSUAL_LOGIN_LOCATION":   "travel_anomaly",
            "GEO_IMPOSSIBLE_TRAVEL":    "travel_anomaly",
            "CONCURRENT_SESSION":       "travel_anomaly",
            # credential_access
            "CREDENTIAL_STUFFING":      "credential_access",
            "BRUTE_FORCE":              "credential_access",
            "MFA_BYPASS":               "credential_access",
            "CLOUD_ACCOUNTS":           "credential_access",
            "T1078":                    "credential_access",
            "T1078.004":                "credential_access",
            "T1110":                    "credential_access",
            "PASSWORD_SPRAY":           "credential_access",
            # threat_intel_match
            "PHISHING_MATCH":           "threat_intel_match",
            "IOC_MATCH":                "threat_intel_match",
            "THREAT_CAMPAIGN":          "threat_intel_match",
            "T1566":                    "threat_intel_match",
            "T1566.001":                "threat_intel_match",
            "CISA_KEV_MATCH":           "threat_intel_match",
            "MALWARE_SIGNATURE":        "threat_intel_match",
            # insider_behavioral
            "DATA_EXFIL":               "insider_behavioral",
            "UNUSUAL_DATA_ACCESS":      "insider_behavioral",
            "INSIDER_THREAT":           "insider_behavioral",
            "T1567":                    "insider_behavioral",
            "LATERAL_MOVEMENT":         "insider_behavioral",
            "T1021":                    "insider_behavioral",
            "PRIVILEGE_ESCALATION":     "insider_behavioral",
            # cloud_infrastructure
            "CLOUD_STORAGE_UPLOAD":     "cloud_infrastructure",
            "CLOUD_ANOMALY":            "cloud_infrastructure",
            "T1048":                    "cloud_infrastructure",
            "CLOUD_API_ABUSE":          "cloud_infrastructure",
            # ... ~170 more entries required — domain expert review in SEED-2 sprint
        }

    @staticmethod
    def get_factor_decay_classes() -> dict[str, str]:
        """S2P analog: adds "transient" for commodity prices."""
        return {
            "travel_match":            "campaign",
            "asset_criticality":       "permanent",
            "threat_intel_enrichment": "campaign",
            "pattern_history":         "standard",
            "time_anomaly":            "standard",
            "device_trust":            "standard",
        }

    @staticmethod
    def get_kernel() -> str:
        """L2 validated (EXP-E1). DOT PRODUCT FORBIDDEN (EXP-C1: 61% vs 97.89%)."""
        return "l2"

    @staticmethod
    def get_shadow_config() -> dict:
        """Shadow mode configuration (v5.5-R8).
        S2P analog: identical structure, same activation flow.
        """
        return {
            "shadow_mode_active":          False,  # toggled at deployment
            "shadow_decision_count_target": 500,   # decisions before report generated
            "shadow_report_by_category":    True,
            "auto_activate_threshold":      None,  # NEVER auto-activate. Always explicit.
            "store_analyst_action":         True,  # record what analyst actually did
            "activation_requires_confirm":  True,
        }

    @staticmethod
    def get_drift_bounds() -> dict:
        """Centroid drift alert thresholds (v5.5-R12, G-L5-3)."""
        return {
            "max_single_cell_drift": 0.30,
            "max_category_drift":    0.20,
            "alert_on_breach":       True,
        }

    @staticmethod
    def get_domain_constraint_spec() -> dict:
        """Synthesis constraint spec (v5.5 PROPOSAL — intelligence_layer_design §9).
        
        Empty dict until: (a) domain expert review complete, (b) GATE-M passes.
        NEVER populate before both conditions are met.
        """
        return {}

    @staticmethod
    def get_checkpoint_config() -> dict:
        """Centroid checkpoint configuration (TD-033 — Loop 4 activation prerequisite)."""
        return {
            "checkpoint_every_n_decisions": 50,
            "max_checkpoints_retained":     10,
            "auto_checkpoint_on_operator_start": True,
        }

    @staticmethod
    def get_semantic_concepts() -> str:
        """Path to concepts.yaml for SemanticRegistry (ci-platform, v5.5).
        20 named SOC graph concepts — see §24.1.
        """
        return "soc-copilot/semantics/concepts.yaml"

    @staticmethod
    def get_query_catalog() -> str:
        """Path to queries.yaml for QueryCatalog (ci-platform, v5.5).
        15 pre-built queries — Tab 1 Panel B Graph Explorer (v5.5); also
        feeds Tab 5 learning narrative section data at v6.0. See §24.2.
        """
        return "soc-copilot/queries/queries.yaml"

    @staticmethod
    def get_graph_schema() -> dict:
        """Register SOC schema for PLAT-4 compliance check + Level 2/3 discovery."""
        return {
            "domain_id": "soc",
            "node_types": [
                "Alert", "Decision", "User", "Asset", "ThreatIntel",
                "ThreatIndicator", "TravelRecord", "Device", "ProfileSnapshot"
            ],
            "relationship_types": [
                "DECIDED_ON", "HAS_TRAVEL", "STORES", "ASSOCIATED_WITH",
                "ACTIVE_AT", "USED_BY", "CALIBRATED_BY", "LINKED_TO_IOC",
            ],
            "hook_fields": {
                "DecisionRecord": [
                    "id", "action", "confidence", "factor_vector",
                    "centroid_snapshot", "category", "kernel",
                    "all_distances", "shadow_mode", "timestamp"
                ],
                "OutcomeRecord": [
                    "decision_id", "action", "correct", "outcome",
                    "centroid_delta_norm", "verified_at"
                ],
                "ProfileSnapshot": [
                    "id", "centroid_array", "observation_counts",
                    "t_decision", "trigger", "created_at"
                ],
            },
        }

    @staticmethod
    def get_source_connectors() -> list:
        """SourceConnector implementations (v5.0 PLAT-7).
        S2P analog: OFACConnector, DunBradstreetConnector, CommodityIndexConnector.
        """
        from app.connectors.cisa_kev import CISAKEVConnector
        from app.connectors.nvd import NVDConnector
        return [
            CISAKEVConnector(),  # Tier 1: daily KEV pull → ThreatIndicator nodes
            NVDConnector(),      # Tier 1: CVE feed → enrichment
        ]

    @staticmethod
    def get_referral_rules() -> list:  # [NEW v5.5.2]
        """Referral rules R1-R7 for post-scoring VETO routing.
        
        Validated: EXP-REFER-LAYERED — 72.7% DR, 12% FPR, 978 net min/100 alerts.
        Confidence gate REJECTED for referral (14% precision = active harm).
        
        Referral is INDEPENDENT of action scoring. Both fire on every alert.
        Referral is a VETO — overrides auto-approve at any confidence level.
        
        Customer overrides thresholds during onboarding. All rules are
        inspectable, auditable, EU AI Act Art. 14 compliant.
        
        S2P analog: S2P implements its own referral rules via same protocol.
        """
        from app.services.referral_rules import get_soc_referral_rules
        return get_soc_referral_rules()
        # Returns 7 rules:
        #   R1: ExecutiveAccountRule (identity_tier ∈ {executive, board, c_suite})
        #   R2: RapidSuccessionRule (sequence_count ≥ 3)
        #   R3: ComplianceMandateRule (insider_threat + compliance_mode)
        #   R4: HighValueDataRule (data_exfil + criticality > 0.85 + monitor/suppress)
        #   R5: ActiveIncidentRule (incident_active flag)
        #   R6: NewAssetRule (asset_age_days < 30)
        #   R7: CrossCategoryRule (≥2 categories for same user)

    @staticmethod
    def get_initial_W() -> "np.ndarray":
        """Legacy: initial weight matrix for backward compatibility.
        
        DEPRECATED — TD-029. ProfileScorer replaces ScoringMatrix.
        Preserved to avoid breaking any code that still references it.
        Remove at v5.5 (TD-029).
        """
        import numpy as np
        return np.zeros((5, 6))  # shape (A, d) — unused by ProfileScorer
```


---

## 21. Shadow Mode — Full Specification

### 21.1 Purpose and Product Role

Shadow mode is the trust-building on-ramp for new deployments. It closes CISO Demo Questions Q3 and Q4 and converts "trust us" into "verify yourself, then decide."

**Customer story:**
1. Customer installs. Shadow mode is **on by default** for all new deployments.
2. For 30 days (or N=500 decisions, whichever comes first): every alert is scored but no recommendation shown. Analyst decisions are recorded as ground truth.
3. At threshold: shadow report generated automatically.
4. Report: "System agreed with your analysts 74.3% of the time. Here are the 26.7% disagreements and why." Categorized by alert type. Top disagreements with factor breakdowns.
5. Customer reviews report. Decides to activate.
6. **[ACTIVATE LIVE MODE]** — explicit click. System starts showing recommendations.
7. The shadow report becomes the demo artifact for subsequent prospects.

**Shadow mode is the answer to the cold-start trust problem.** Every AI product faces it. This is how we solve it for regulated enterprise buyers who cannot bet their SOC on an untested system.

### 21.2 ShadowModeService

```python
# backend/app/services/shadow.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import uuid4

@dataclass
class ShadowReport:
    report_id: str
    total_decisions: int
    overall_agreement_rate: float
    by_category: dict[str, dict]      # {cat: {agreement, total, top_disagreements}}
    top_disagreements: list["Disagreement"]
    generated_at: datetime
    recommendation: str               # NL summary of what to review before activating

@dataclass
class Disagreement:
    alert_id: str
    category: str
    technique_id: Optional[str]
    system_action: str               # what system recommended
    analyst_action: str              # what analyst actually did
    confidence: float                # system's confidence
    factor_breakdown: dict[str, float]
    provenance_summary: str          # one-sentence provenance from NL templates
    nl_explanation: str              # "travel_match=0.87 (Singapore, no TravelRecord).
                                     #  System: SUPPRESS at 91%. Analyst: INVESTIGATE.
                                     #  Likely: analyst applied context outside the 6 factors."


class ShadowModeService:
    """Shadow mode: scores without displaying. Records for agreement analysis.
    
    DESIGN INVARIANTS:
      1. SAME scoring pipeline — no shortcuts. Shadow agreement rate is only
         meaningful if computed on identical logic to live mode.
      2. Shadow decisions ARE written to the graph (shadow_mode=True) and DO
         update ProfileScorer learning. The system learns from the shadow period.
         This is correct — we want the model calibrated before going live.
      3. NEVER auto-activates live mode. Explicit customer action required.
         Any code path that calls activate_live_mode() without confirmed_by
         set to a real analyst ID is a design violation.
    """

    def __init__(self, domain_config, neo4j, nl_engine):
        self.config = domain_config.get_shadow_config()
        self.neo4j = neo4j
        self.nl_engine = nl_engine

    def is_active(self) -> bool:
        return self.config["shadow_mode_active"]

    async def get_progress(self) -> dict:
        result = await self.neo4j.execute_read("""
            MATCH (d:Decision {shadow_mode: true})
            WHERE d.analyst_action IS NOT NULL
            RETURN count(d) AS recorded
        """)
        recorded = result["recorded"]
        target = self.config["shadow_decision_count_target"]
        return {
            "active": self.is_active(),
            "decisions_recorded": recorded,
            "target": target,
            "pct_complete": min(100, round(100 * recorded / target)),
            "report_ready": recorded >= target,
        }

    async def generate_shadow_report(self) -> ShadowReport:
        """Generate agreement analysis. Called after N shadow decisions."""

        # Overall agreement
        agg = await self.neo4j.execute_read("""
            MATCH (d:Decision {shadow_mode: true})
            WHERE d.analyst_action IS NOT NULL
            RETURN count(d) AS total,
                   sum(CASE WHEN d.analyst_agreed THEN 1 ELSE 0 END) AS agreed
        """)
        total = agg["total"]
        agreed = agg["agreed"]
        overall_rate = agreed / total if total > 0 else 0.0

        # By category
        cat_rows = await self.neo4j.execute_read("""
            MATCH (d:Decision {shadow_mode: true})-[:DECIDED_ON]->(a:Alert)
            WHERE d.analyst_action IS NOT NULL
            RETURN a.situation_type AS category,
                   count(d) AS total,
                   sum(CASE WHEN d.analyst_agreed THEN 1 ELSE 0 END) AS agreed
        """)
        by_category = {
            row["category"]: {
                "total": row["total"],
                "agreed": row["agreed"],
                "agreement_rate": row["agreed"] / row["total"] if row["total"] > 0 else 0.0,
            }
            for row in cat_rows
        }

        # Top disagreements (sorted by impact = confidence × disagreement)
        disag_rows = await self.neo4j.execute_read("""
            MATCH (d:Decision {shadow_mode: true, analyst_agreed: false})-[:DECIDED_ON]->(a:Alert)
            RETURN d, a
            ORDER BY d.confidence DESC
            LIMIT 20
        """)
        disagreements = [
            Disagreement(
                alert_id=row["a"]["id"],
                category=row["a"].get("situation_type", "unknown"),
                technique_id=row["a"].get("technique_id"),
                system_action=row["d"]["action"],
                analyst_action=row["d"]["analyst_action"],
                confidence=row["d"]["confidence"],
                factor_breakdown=dict(zip(
                    ["travel_match", "asset_criticality", "threat_intel_enrichment",
                     "pattern_history", "time_anomaly", "device_trust"],
                    row["d"].get("factor_vector", [0.5]*6)
                )),
                provenance_summary="",   # populated by NL template engine
                nl_explanation=self.nl_engine.render_shadow_disagreement(row["d"], row["a"]),
            )
            for row in disag_rows
        ]

        # Generate recommendation
        worst_cat = min(by_category.items(), key=lambda x: x[1]["agreement_rate"])
        recommendation = (
            f"System agreed with analysts on {overall_rate:.1%} of decisions. "
            f"Lowest agreement: {worst_cat[0]} ({worst_cat[1]['agreement_rate']:.1%}). "
            f"Review the {len(disagreements)} listed disagreements before activating. "
            f"Pay attention to {worst_cat[0]} — those {worst_cat[1]['total'] - worst_cat[1]['agreed']} "
            f"disagreements may indicate centroid tuning is needed for this category."
        )

        return ShadowReport(
            report_id=str(uuid4()),
            total_decisions=total,
            overall_agreement_rate=overall_rate,
            by_category=by_category,
            top_disagreements=disagreements,
            generated_at=datetime.utcnow(),
            recommendation=recommendation,
        )

    async def activate_live_mode(self, confirmed_by: str, neo4j) -> None:
        """Explicit activation — requires analyst ID. Logs to audit trail.
        
        This method may ONLY be called from an explicit UI button click.
        Never call from a background task, a timer, or an automated threshold check.
        """
        if not confirmed_by:
            raise ValueError("confirmed_by must be a non-empty analyst ID")

        # Update config
        self.config["shadow_mode_active"] = False

        # Audit log
        await neo4j.execute_write("""
            CREATE (e:AuditEvent {
                event_type:    'SHADOW_MODE_DEACTIVATED',
                performed_by:  $analyst_id,
                timestamp:     datetime(),
                notes:         'Live mode activated — system recommendations now visible'
            })
        """, analyst_id=confirmed_by)
```

### 21.3 API Endpoints

```python
# backend/app/routers/shadow.py

GET  /api/shadow/status
  Returns: {"active": bool, "decisions_recorded": int, "target": int,
            "pct_complete": int, "report_ready": bool}

GET  /api/shadow/report
  Returns: ShadowReport (JSON)
  Notes: Generated on first call after threshold; cached 1h.
  Error 404 if report not yet ready (< target decisions).

POST /api/shadow/activate
  Body: {"confirm": true, "confirmed_by": "analyst_username"}
  Validation: confirm must be true; confirmed_by must be non-empty
  Returns: {"activated": true, "timestamp": "..."}
  Notes: Irreversible without admin hard reset.
         Logged to audit trail with analyst identity.
```

### 21.4 UI Components

```typescript
// ShadowModePanel.tsx

// ① Banner — shown in all tab headers when shadow mode is active
function ShadowModeBanner({ progress }) {
  return (
    <div className="shadow-banner">
      <span>SHADOW MODE — System observing, not influencing decisions</span>
      <ProgressBar current={progress.decisions_recorded} total={progress.target} />
      <span>{progress.pct_complete}% complete</span>
    </div>
  );
}

// ② Report View — shown when report_ready = true
function ShadowReportView({ report, onActivate }) {
  return (
    <div>
      <AgreementScore rate={report.overall_agreement_rate} />
      <AgreementByCategory data={report.by_category} />
      <TopDisagreements items={report.top_disagreements} />
      <div className="recommendation">{report.recommendation}</div>
      <ActivateButton
        label="ACTIVATE LIVE MODE"
        requireConfirmation
        confirmText="This will enable live recommendations. Continue?"
        onConfirm={(analystId) => onActivate(analystId)}
      />
    </div>
  );
}
```

---

## 22. Institutional Knowledge Score (IKS)

### 22.1 Purpose and Claim

The IKS is the **single most important missing feature for demo conversion** at v5.0. It is the answer to CISO Demo Question Q2: "Is it getting smarter?"

Without IKS, the claim "it learns from your environment" is abstract and unverifiable to a buyer.
With IKS: "Your IKS is 47.3. At deployment it was 0. The maximum is 100. 47.3 means your system's profile centroids have moved nearly halfway from bootstrap priors toward full adaptation to your specific environment." That is verifiable, trackable, and quotable to the board.

The IKS is the compounding claim made **concrete and quantifiable**. It is the mechanism by which the "moat is the graph" argument becomes a CISO's quarterly board talking point.

### 22.2 Formula

```
IKS(t) = 100 × min(mean_drift(t) / d_max, 1.0)

Where:
  mean_drift(t) = mean over all (c, a) pairs of ‖μ(t)[c,a,:] - μ₀[c,a,:]‖₂
  μ₀             = bootstrap centroid state (get_profile_centroids() at deployment)
  d_max          = 0.30  (max plausible drift — informed by V2 [0,1] clipping analysis)
  
Properties:
  IKS = 0:    No operational learning. System uses expert-configured priors only.
  IKS = 50:   Centroids halfway from "no experience" to "full adaptation."
  IKS = 100:  Maximum claimed adaptation — d_max reached across all cells.
              (Practically: IKS > 60 indicates deep, stable domain adaptation.)
  
Monotonicity: IKS increases under normal operation (correct learning signal).
Drift alert: IKS DROP of > 5 points without an explicit reset → TD-033 rollback trigger.
IKS requires: ProfileSnapshot Hook 3 writes to be present in Neo4j.
              Without them, get_iks_trend() returns empty and the score cannot be computed.
```

### 22.3 IKS Service [CHANGED v5.5.1]

```python
# backend/app/services/iks.py
# NOTE: Module-level functions, NOT a class. [CHANGED v5.5.1]
# Use: from app.services.iks import compute_iks, interpret

import numpy as np

D_MAX = 0.20  # [CHANGED v5.5.1: was 0.30. κ*=0.20 from PROD-1 validation.]

def compute_iks(centroids: np.ndarray, mu0: np.ndarray, n_decisions: int = 0) -> float:
    """
    Compute IKS from current centroid state vs. bootstrap baseline.
    
    Args:
        centroids: current centroid tensor, shape (C, A, d) = (6, 4, 6)
        mu0: bootstrap baseline centroids, same shape
        n_decisions: number of verified decisions (for display only)
    
    Returns:
        IKS score in [0, 100].
    """
    assert centroids.shape == mu0.shape, \
        f"Shape mismatch: {centroids.shape} vs {mu0.shape}"
    diffs = centroids - mu0                              # (C, A, d)
    per_cell_dist = np.linalg.norm(diffs, axis=-1)       # (C, A)
    mean_drift = per_cell_dist.mean()
    return round(100.0 * min(mean_drift / D_MAX, 1.0), 1)


def interpret(iks_score: float) -> str:
    """Plain English interpretation for UI display."""
    if iks_score < 5:
        return "System is using expert-configured priors. Operational learning has not yet started."
    elif iks_score < 20:
        return (f"IKS {iks_score}: Early operational learning. "
                f"The system has begun adapting to your environment.")
    elif iks_score < 50:
        return (f"IKS {iks_score}: Meaningful adaptation. "
                f"Profile centroids reflect operational patterns from verified decisions.")
    elif iks_score < 80:
        return (f"IKS {iks_score}: Deep adaptation. "
                f"The system has substantially adapted to your specific threat landscape.")
    else:
        return (f"IKS {iks_score}: Full adaptation. "
                f"Centroids reflect mature institutional knowledge.")
```

**Key changes from v5.5 [CHANGED v5.5.1]:**
- Module-level functions `compute_iks()` and `interpret()` — NOT a class.
  Use: `from app.services.iks import compute_iks, interpret`
- D_MAX = 0.20 (was 0.30). κ*=0.20 from PROD-1 validation (March 2026).
  Design estimate 0.30 was near-floor — IKS barely moved.
- Tensor shape (6, 4, 6) — matches A=4 canonical.
- μ₀ sidecar lives at `iks_bootstrap_soc.json`, shape [6,4,6].
  Generated by bootstrap.py. Do not delete or move without updating the path.

**IKS anchor separation — two distinct artifacts [NEW v5.5.3]:**

Option A architecture (confirmed, IKS bakeoff). Two artifacts MUST remain distinct:

| Artifact | Purpose | Rule |
|---|---|---|
| **Standard μ₀** (`iks_bootstrap_soc.json`) | IKS anchor — the reference point for drift measurement. IKS(t) = drift from HERE. | **NEVER overwritten post-deployment.** Any code path that writes to the anchor after bootstrap.py runs is a design violation. |
| **Enriched μ₀** (if P28 Warmstart active) | Live starting point — where centroids actually begin. Closer to μ* when enrichment was applied at P28. | May differ from standard μ₀. NEVER used as IKS anchor. |

Why this matters: if enriched μ₀ is used as IKS anchor, IKS starts at 0 but D_MAX is
smaller (centroid only needs to travel 78% of the unenriched distance). IKS never reaches
100 under standard D_MAX=0.20. The standard μ₀ anchor preserves IKS semantic correctness
regardless of whether enrichment was applied.

```python
# bootstrap.py — two artifacts, written once each
mu_zero_standard = profile_scorer.centroids.copy()   # BEFORE any calibration
persist_bootstrap_snapshot(mu_zero_standard, "iks_bootstrap_soc.json")  # IKS anchor

if enrichment_applied:
    mu_zero_enriched = profile_scorer.centroids.copy()  # AFTER enrichment bootstrap
    persist_bootstrap_snapshot(mu_zero_enriched, "enriched_bootstrap_soc.json")  # live start
    profile_scorer.reset_centroids(mu_zero_enriched)  # start from enriched position
else:
    profile_scorer.reset_centroids(mu_zero_standard)  # start from standard

# IKS ALWAYS measures drift from mu_zero_standard — never from mu_zero_enriched.
```
        elif iks < 75:
            return (f"IKS {iks}: Deep environment adaptation. "
                    f"Your system knows your environment significantly better than at deployment. "
                    f"Switching to a new system would restart from zero.")
        else:
            return (f"IKS {iks}: Full adaptation. "
                    f"Profile centroids have reached maximum expected operational drift. "
                    f"This is the moat — replicating this requires running every one of your decisions again.")
```

### 22.4 Display Locations

**Tab 2 (primary):**
```
Institutional Knowledge Score
         47.3
  ↑ +2.1 this week

[IKS Trend Chart — 90-day history]
"IKS 47.3: Deep environment adaptation. Your system knows your environment significantly
 better than at deployment. Switching costs are now real."
```

**Tab 5 Section 1 — "What Changed Since Last Time" (IKS one-liner):**
```
● Institutional Knowledge Score: 47.3  (+2.1 since last week)
```

**Tab 4 ROI block (as context):**
```
System has accumulated 847 decisions. IKS: 47.3.
Realized savings: 28.4 analyst-hours/week (shadow period data).
```

---

### 22.5 IKS Wiring Spec (VIS-2 execution target)

*Added March 11, 2026. Closes open item G. Governs how VIS-2 implements the IKS
endpoint and wires it to the Tab-2 Institutional Intelligence summary panel.*

#### Audit result (March 11, 2026)

**State C confirmed — fully absent.** IKS does not exist anywhere in:
backend, frontend, GAE library, design docs, or graph-attention-engine-v50.
The term "institutional" appears once in the entire codebase — a prose comment
in `gae/judgment.py`.

**Critical gap revealed: μ₀ is discarded.** `bootstrap.py` calibrates
ProfileScorer by mutating centroids in-place and discarding the pre-calibration
state. There is no stored μ₀ anywhere. Without μ₀, `mean_drift(t) = ‖μ(t) − μ₀‖`
cannot be computed — the reference point is permanently lost on every restart.

**Existing assets (partial foundation):**
- `ProfileScorer.mu` — live centroid array in memory ✅
- `/api/soc/profile` — returns centroid data, extensible in ~15 lines ✅
- D_MAX — absent ❌
- μ₀ as stored artifact — absent, currently unrecoverable ❌

#### Implementation order (revised from pre-audit spec)

The prerequisite structure has three layers. They must execute in order:

**Layer 0 — μ₀ persistence (prerequisite for WIRING-1):**
`bootstrap.py` must be modified to persist μ₀ before the in-place calibration
mutates centroids. Without this, every IKS computed will be wrong (drift
measured against wrong baseline) or impossible (no baseline at all).

```python
# backend/app/services/bootstrap.py  (conceptual — read §22.3 class for full spec)
# BEFORE in-place calibration:
mu_zero = profile_scorer.centroids.copy()          # capture pre-calibration state
persist_bootstrap_snapshot(mu_zero, domain_config)  # serialize to JSON sidecar

# persist_bootstrap_snapshot writes to:
# backend/app/data/iks_bootstrap_{domain}.json
# Format: {"mu_zero": <flattened list>, "shape": [C,A,d], "timestamp": "..."}
```

Storage: JSON sidecar at `backend/app/data/iks_bootstrap_{domain}.json`.
Load on startup: `InstitutionalKnowledgeScoreService.__init__()` reads this file.
If file absent: `current_iks` returns `null` with `estimated: false`;
frontend shows "Bootstrap snapshot required — restart after calibration."
Never fabricate a μ₀. Never fall back to zeros.

**Layer 1 — D_MAX and IKS service (WIRING-1 scope):**
Once μ₀ is persisted, implement `InstitutionalKnowledgeScoreService` from §22.3.
D_MAX = 0.30 (design constant — replace with PROD-1b empirical value when available).
Service location: `backend/app/services/iks.py`.

**Layer 2 — API endpoint (WIRING-1 scope, extends /api/soc/profile):**
Extend `/api/soc/profile` with an `iks` field rather than a new endpoint.
This avoids a new router and reuses an already-authenticated call path.

```
GET /api/soc/profile  (extended response)
{
  ...existing fields...,
  "iks": {
    "current":        47.3,          // null if μ₀ absent
    "delta_7d":       2.1,           // null if <7 days of snapshots
    "interpretation": "Deep environment adaptation...",
    "decision_count": 847,
    "estimated":      false,
    "trend": [                       // [] until first ProfileSnapshot (decision 50)
      {"t_decision": 50,  "timestamp": "2026-02-12T14:23Z",
       "iks": 3.1, "mean_drift": 0.0093},
      ...
    ]
  }
}
```

`estimated: true` when decision_count < 50 (before first ProfileSnapshot).
`estimated: false` once trend data exists.

#### Revised two-phase rollout

| Phase | Condition | `current_iks` | `trend` | `delta_7d` |
|---|---|---|---|---|
| Pre-Layer-0 | No μ₀ sidecar | `null` (show bootstrap prompt) | `[]` | `null` |
| Layer 0 done | μ₀ sidecar exists | ✅ Live (vs. μ₀) | `[]` | `null` |
| WIRING-1 done | ProfileSnapshot nodes writing | ✅ Live | ✅ Live | ✅ (after 7d) |

#### VIS-2 step 0 — code checks before any frontend work

```
STEP 0A: μ₀ sidecar
  Does backend/app/data/iks_bootstrap_soc.json exist?
  If YES: load μ₀ from it. Verify shape matches ProfileScorer.mu.shape.
  If NO:  μ₀ Layer 0 work required before IKS can be non-null.

STEP 0B: IKS service
  Does backend/app/services/iks.py exist?
  If YES: verify InstitutionalKnowledgeScoreService matches §22.3 spec.
  If NO:  implement from §22.3 (~50 lines).

STEP 0C: Endpoint extension
  Does GET /api/soc/profile include an "iks" key?
  If YES: verify response shape matches §22.5.
  If NO:  add iks computation to the profile endpoint handler (~15 lines).
```

Frontend work begins only after steps 0A–0C confirm `GET /api/soc/profile`
returns `iks.current` as a non-null float.

#### Frontend — Tab-2 Institutional Intelligence summary panel (conditional rendering)

The summary panel ALWAYS renders — it never hides behind a "loading" state or
disappears when trend data is absent. Two display states:

**State: Pre-WIRING-1 (trend = []):**
```
┌─ Institutional Intelligence ──────────────────────────────────────────┐
│  IKS: 47.3   "Meaningful adaptation."                                  │
│  847 decisions recorded.                                               │
│                                                                        │
│  Situational Understanding       Deployment Adaptation                 │
│  (ProfileScorer)                 (AgentEvolver)                        │
│  [centroid convergence status]   [variant + false escalation stats]   │
│                                                                        │
│  IKS trend: Trend available after first checkpoint (50 decisions)     │
│             ─────── bar chart placeholder ───────                     │
└────────────────────────────────────────────────────────────────────────┘
```

**State: Post-WIRING-1 (trend populated):**
```
┌─ Institutional Intelligence ──────────────────────────────────────────┐
│  IKS: 47.3  ↑ +2.1 this week   "Deep environment adaptation."        │
│  847 decisions · Both mechanisms active · System is adapting          │
│                                                                        │
│  Situational Understanding       Deployment Adaptation                 │
│  (ProfileScorer)                 (AgentEvolver)                        │
│  [centroid convergence status]   [variant + false escalation stats]   │
│                                                                        │
│  [IKS trend sparkline — 90-day history from ProfileSnapshot nodes]    │
└────────────────────────────────────────────────────────────────────────┘
```

`delta_7d` shows as "↑ +2.1 this week" when non-null; hides entirely when null
(not shown as "—" or "N/A" — absent data should be invisible, not emphasized).

#### Dependency on WIRING-1

WIRING-1 gates:
- IKS trend chart in Tab-2 Section B
- `delta_7d` in the summary panel header
- Chart A (centroid_delta_norm per decision) in Tab-2 Section B and Tab-4

WIRING-1 does NOT gate:
- `current_iks` in the summary panel
- IKS interpretation text
- Both-mechanisms status indicators (AgentEvolver stats come from a separate endpoint)
- Tab-2 summary panel skeleton

**VIS-2 sequencing rule:** Implement WIRING-1 first. Verify `GET /api/soc/iks`
returns trend data and `GET /api/soc/centroid-evolution` returns centroid_delta_norm
records. Only then wire the frontend charts. This prevents a frontend that renders
permanently-empty trend charts that look like bugs.

#### New Endpoints (v5.5.1) [NEW v5.5.1]

**GET /api/soc/centroid-evolution** — returns flat array (NOT `{evolution:[]}`)
```json
[
  {"id": "evo-001", "category": "credential_access", "action": "escalate",
   "delta_norm": 0.0234, "outcome": "correct", "timestamp": "2026-03-15T10:23Z"},
  ...
]
```
Frontend state: `useState<CentroidEvolutionEntry[]>([])`.

**GET /api/soc/learning-state**
```json
{
  "frozen": false,
  "checkpoint_count": 12,
  "last_checkpoint_at": "2026-03-15T10:23Z",
  "drift_since_last": 0.0147
}
```

**GET /api/soc/frozen-roi** [NEW v5.5.1]
```
Query params: alerts_per_day, analyst_hourly_cost (default $85), auto_approve_rate
Response:
{
  "time_saved_per_day_minutes": 132.0,
  "time_saved_annual_hours": 528.0,
  "consistency_value": "Eliminates 30-40% inter-analyst variance",
  "coverage_value": "40%+ auto-approve at ≥85% accuracy",
  "total_frozen_roi_annual": 44880.0,
  "methodology": "44min × V × cost — time saved per alert from pre-analyzed context"
}
```
**NOTE:** Uses 44min × V × cost, NOT $127/alert. Three value drivers: time saved,
consistency, coverage. The $127 number is a published industry average that does not
reflect our specific value proposition.

#### Kernel Integration (v6.0) [NEW v5.5.1]

Scoring uses configurable kernel via `ProfileScorer(kernel=...)`:
- **Default:** `DiagonalKernel(weights=1/σ²)` for deployments with noise_ratio > 1.5
- **Fallback:** `L2Kernel` (before P28 deployment qualification measures per-factor σ)
- **KernelSelector** runs during shadow mode (Phase 3 of P28 pipeline):
  - All kernels scored simultaneously on every alert
  - Rolling 100-decision window tracks agreement rate
  - Phase 4 (QUALIFY) locks the winning kernel for the deployment
- **Factor quarantine mask:** DEPRECATED — DiagonalKernel's continuous weighting
  supersedes binary masking (+3.7pp vs mask's -3.5pp on healthcare)

Asymmetric η: η_confirm=0.05 (confirm path), η_override=0.01 (override path).
AMBER auto-pause: conservation AMBER/RED → freeze learning until GREEN resumes.

### 22.6 Referral Routing Architecture [NEW v5.5.2]

**Purpose:** Detect alerts that need human review for reasons BEYOND system uncertainty.
The confidence gate catches "I don't know." Referral rules catch "I know this is
technically fine, but organizational context says a human should see it."

**Experimental validation (4 experiments, March 21, 2026):**

| Experiment | Finding | Impact |
|---|---|---|
| EXP-A4-DIAGONAL | A=5 refer centroid: 13pp gap, kernel-independent | refer_to_analyst does NOT belong in centroid tensor |
| EXP-REFER-LEARN | Factor vectors alone can't distinguish referrals | Signal lives in context, not geometry |
| EXP-REFER-COVERAGE | 65.5% rule-expressible, 20.7% emergent | Rules are the primary mechanism |
| EXP-REFER-LAYERED | Rules 72.7% DR / 12% FPR vs conf gate 33.3% / 34.9% | Rules strictly dominate confidence gate |

**Architecture — two independent routing decisions:**

```
Alert → Stage 1: ProfileScorer A=4 (action + confidence)
           Action routing: auto-approve / investigate / escalate
      → Stage 2: ReferralEngine (independent, post-scoring)
           Referral routing: R1-R7 rules evaluated against alert context
           ANY rule fires → REFER TO ANALYST (VETO — overrides auto-approve)
      → Final: if referral fires → analyst review (even at 95% confidence)
               if no referral → action routing determines path
```

**Key design principle: Referral is a VETO, not a fallback.**
An alert can be high-confidence suppress AND referred (executive account during M&A).
The confidence gate is for action routing only — low confidence → investigate, not refer.

**Three-phase deployment:**

| Phase | Mechanism | When active |
|---|---|---|
| Phase 1 (v6.0) | ReferralRules R1-R7 | Day 1 — configurable, deterministic, auditable |
| Phase 2 (v6.5) | + OverrideDetector | Data-gated: ≥50 production analyst override positives |
| Phase 3 (v7.0) | OverrideDetector retrains monthly | Production cadence |

**SOC referral rules (validated by EXP-REFER-COVERAGE):**

| Rule | Fires when | Configurable | Detection |
|---|---|---|---|
| R1: ExecutiveAccountRule | identity_tier ∈ {executive, board, c_suite} | tiers= | 100% |
| R2: RapidSuccessionRule | sequence_count ≥ 3 within window | threshold=, window= | 100% |
| R3: ComplianceMandateRule | insider_threat AND compliance_mode | mandated_categories= | 100% |
| R4: HighValueDataRule | data_exfil + criticality > 0.85 + monitor/suppress | thresholds | 42.6% (by design) |
| R5: ActiveIncidentRule | incident_active flag | — | 100% |
| R6: NewAssetRule | asset_age_days < 30 | age_threshold_days= | 100% |
| R7: CrossCategoryRule | ≥2 categories for same user in 1 hour | threshold= | 100% |

**R4 note:** 42.6% detection because it depends on Stage 1 predicting monitor/suppress.
When Stage 1 correctly escalates, R4 doesn't fire — but the alert is already going to human.

**Problem decomposition:**

| Fraction | Mechanism | Status |
|---|---|---|
| 65.5% rule-expressible | R1-R6 policy rules | ✅ v6.0 |
| 13.8% context-dependent | R7 graph query + R9 calendar | ✅ v6.0 (R7), v6.5 (R9) |
| 20.7% emergent | OverrideDetector (analyst override patterns) | v6.5 (data-gated) |

**Triage integration (backend/app/routers/soc.py):**

After ProfileScorer.score() returns action + confidence, before response:
1. Build alert_context dict from alert metadata + factor values + Stage 1 output
2. `referral = ReferralEngine(rules=get_soc_referral_rules()).evaluate(alert_context)`
3. If referral.should_refer → override routing to refer_to_analyst, log audit_summary
4. Response includes `referral: {should_refer, reasons, audit_summary}`

Safe defaults: sequence_count=0, cross_category_count=0, compliance_mode=False,
incident_active=False. Missing context → rule doesn't fire (false negative, not FP).

**Files:**
- GAE protocol: `gae/referral.py` (ReferralEngine, ReferralRule, OverrideDetector)
- SOC rules: `backend/app/services/referral_rules.py` (7 rules + factory)
- Triage wiring: `backend/app/routers/soc.py` (VETO insertion after scoring)

**Design properties (permanent):**
- P-REF-1: Referral NEVER modifies ProfileScorer scoring or centroids.
- P-REF-2: Missing context → rule doesn't fire (safe degradation).
- P-REF-3: Rules are inspectable, auditable, EU AI Act Art. 14 compliant.
- P-REF-4: Customer configures rules during onboarding.
- P-REF-5: OverrideDetector activates on data volume (≥50 positives), not calendar.

### 22.7 Three-Signal Monitoring Architecture [NEW v5.5.3]

The conservation law has been extended from three roles to four. The full monitoring
architecture is now settled across three named signals.

**Four roles of the conservation law:**
1. Protects Level 1's correction signal (learning quality)
2. Constrains Level 2's optimization freedom (automation safety)
3. Guarantees graph enrichment rate via TRIGGERED_EVOLUTION write-back (knowledge accumulation)
4. **Flywheel health monitoring** — detects Override Lift degradation before centroid damage

**Three-signal architecture (settled in Phase 1, March 25, 2026):**

| Signal | Name | Implementation | Status | Evidence |
|---|---|---|---|---|
| α·q·V ≥ θ_min | **Circuit Breaker** | ConservationMonitor, θ_min=0.467, absolute floor + relative drop (0.7× → AMBER, 0.5× → RED) | ✅ Validated (CLAIM-39) | Three-judge, META-3 |
| CUSUM on OLS | **Flywheel Health Monitor** | OLSMonitor, h=5.0 (OLS scale), plateau-snapshot baseline | ✅ Validated (CLAIM-OLS-01) | V-OLS-DETECT: 0% miss, p90≥50d, N=30/condition |
| Var(OLS_i) across analysts | **Analyst Contribution Monitor** | Per-analyst OLS query on DecisionRecord | ⚠️ Production milestone | Activates ≥20 overrides/analyst (~8d at V=200, α=0.25) |

**Nomenclature correction [NEW v5.5.3]:**
"Level 1/2/3 monitoring" is DEPRECATED. Replaced throughout with:
- Circuit Breaker (not Level 1 monitoring)
- Flywheel Health Monitor (not Level 2 monitoring)
- Analyst Contribution Monitor (not Level 3 monitoring)

Reason: "Level 1/2/3" collides with L1 (ProfileScorer) / L2 (AgentEvolver) learning
architecture, causing ambiguity in cross-repo conversation.

**Circuit Breaker (existing — unchanged):**

```python
# backend/app/services/conservation.py

THETA_MIN = 0.467  # θ_min=0.467, T_max=21 days canonical

def check_circuit_breaker(alpha: float, q_bar: float, V: float) -> str:
    """
    Returns: "GREEN" | "AMBER" | "RED"
    AMBER: α·q·V < 0.7 × baseline or < θ_min
    RED:   α·q·V < 0.5 × baseline
    On AMBER: LEARNING_ENABLED = False (auto-pause).
    On GREEN resume: LEARNING_ENABLED = True.
    """
    signal = alpha * q_bar * V
    if signal >= THETA_MIN:
        return "GREEN"
    elif signal >= THETA_MIN * 0.7:
        return "AMBER"
    else:
        return "RED"
```

**Flywheel Health Monitor (new — validated CLAIM-OLS-01):**

```python
# In GAE: gae/convergence.py (OLSMonitor)
# In SOC: backend/app/services/conservation.py (reads OLSMonitor output)

# OLS = P(correct | override by analyst) / P(correct | AI accepted)
# Override Lift Score > 1.0: analyst overrides beating AI baseline
# Override Lift Score < 1.0: analyst overrides degrading model

# CUSUM on OLS — KEY PARAMETERS (do not change without re-validating CLAIM-OLS-01):
CUSUM_H = 5.0         # h=5.0 on OLS scale. NOT h=15.0 (that was q̄ scale).
                       # h=5.0 validated: 0% miss rate, p90≥50d lead time.
                       # h=15.0 is WRONG for OLS scale — silently misses degradation.

# Plateau-snapshot baseline:
# T_damage = first decision where OLS stays ≥5pp below baseline for ≥10 consecutive
# decisions. NOT peak-based (peak-based fires on learning oscillations).
# Baseline frozen after centroids stabilize (plateau-snapshot).

def get_override_lift_status(ols_monitor) -> dict:
    """
    Returns OLS trajectory for Tab 2 display.
    {
      "current_ols": float,           # current Override Lift Score
      "baseline_ols": float,          # plateau-snapshot baseline
      "cusum_alarm": bool,            # True when CUSUM h=5.0 threshold crossed
      "lead_time_decisions": int,     # decisions since alarm fired (0 if no alarm)
      "interpretation": str           # NL interpretation for Tab 2
    }
    """
    ...

# COMMERCIAL FRAMING (Tab 2 display):
# "Override Lift Score: 1.23 — your analysts' overrides are generating a 23% return
#  over our AI's baseline. When this drops, we flag it at least 50 decisions before
#  centroid damage accumulates."
```

**Analyst Contribution Monitor (production milestone — data-gated):**

```python
# Per-analyst OLS variance. Detects bimodal team structure invisible to Circuit Breaker.
# Example: team q̄=0.725, but 5 analysts at q=0.90 and 5 at q=0.55.
# Circuit Breaker stays GREEN (aggregate looks healthy).
# Analyst Contribution Monitor fires (per-analyst OLS variance is high).

# Activation: ≥20 verified overrides per analyst in DecisionRecord.
# At V=200, α=0.25: ~8 days of operation.
# Data is already collected (DecisionRecord includes analyst_id + verified_correct).
# This is a query on existing data — no new instrumentation.

# PERMANENT HARD STOP: Var(q) pooled binary CANNOT replace this signal.
# Bernoulli mixture theorem: Var(Q_bimodal) = p̄(1-p̄), identical to uniform at same mean.
# Binary rolling verified accuracy observations cannot detect bimodal structure.
# This is arithmetic, not an implementation gap. No experiment will fix it.
# Per-analyst OLS (continuous, not binary) does not have this limitation.

VAR_OLS_THRESHOLD = 0.01    # validated ANALYST-CONTRIBUTION-001 parameters
N_DECISIONS_MIN = 1200      # for reliable per-analyst estimates in simulation
N_WARMUP = 400
MIN_OVERRIDES_PER_ANALYST = 20  # activation gate in production
```

**Var(q) status — PERMANENT HARD STOP [NEW v5.5.3]:**

V-MV-CONSERVATION series (v2–v10) + V-MV-CONSERVATION-BIMODAL confirmed:
Var(Q_bimodal) = p̄(1-p̄) — identical to uniform Bernoulli at same mean.
Binary rolling verified accuracy observations cannot distinguish bimodal team structure
from uniform distribution. This is the Bernoulli mixture theorem — not fixable
by any experimental design or implementation approach.

**Var(q) is a logged observability metric only.** It has no product claim, no gating
logic, and no action trigger. Do NOT wire Var(q) to any enforcement or alert pathway.
Per-analyst OLS variance (Analyst Contribution Monitor) is the correct Level 3 signal.

**Tab 2 display integration:**

```
Section A: Circuit Breaker
  "Learning signal: HEALTHY (signal=25.5, floor=0.47)"
  Sparkline: α·q·V over 90 days. Per-shift breakdown.

Section B: Flywheel Health Monitor  [Phase 3 Priority 1 — to implement]
  "Override Lift Score: 1.23"
  OLS trajectory chart (same style as IKS trend chart).
  Alarm state indicator (green/amber/red based on CUSUM).

Section C: Analyst Contribution Monitor  [activates from production data]
  Per-analyst OLS bars (shown when ≥20 overrides/analyst).
  "Analyst 7's override lift: 0.82 (below baseline). Analyst 3: 1.41 (top contributor)."
  Hidden until activation threshold met.
```

**Implementation notes for Phase 3:**
- Circuit Breaker: ✅ Already implemented in conservation.py
- Flywheel Health Monitor: OLSMonitor ships in GAE 0.7.11. Frontend display is Phase 3
  Priority 1 (small, ~3 days). Wire GET /api/soc/ols-status endpoint to Tab 2 Section B.
- Analyst Contribution Monitor: Data already in DecisionRecord. Query is a GROUP BY
  analyst_id on verified overrides. Activates automatically when threshold met.

---

## 23. NL Template Engine

### 23.1 Purpose and Design Principle

The NL Template Engine provides **deterministic**, human-readable explanations at three specificity layers. No LLM is required for any layer. The intelligence is in the graph — the templates are the rendering layer.

**Why deterministic?**
- Same inputs → same output, always. Compliance-safe.
- No latency. No API calls. No failure modes.
- Auditable: "The explanation on decision 7a3f-91c2 was generated by template L1_credential_access version 1.2." Regulators can verify.

**Distinct from NarrativeProvider:**
- `NarrativeProvider` (§16): per-alert investigation prose (3-5 sentences via Ollama/Claude). Rich but probabilistic.
- `NLTemplateEngine` (this section): structured explainability for compliance, Tab 5, and learning feedback. Deterministic.

Both are needed. They serve different audiences at different trust levels.

### 23.2 Three-Layer Model

| Layer | Audience | Source Data | Output |
|---|---|---|---|
| **L1 — Analyst** | SOC analyst — per-decision detail | Factor values + provenance nodes | "Anomalous Singapore login, no travel history, MDM device. SUPPRESS at 91%." |
| **L2 — CISO** | CISO — weekly business summary | Category + action + confidence + IKS | "847 alerts. 41% auto-approved. IKS 47.3 (+2.1)." |
| **L3 — Auditor** | Compliance — formal audit record | Decision ID + hash + all fields | "Decision 7a3f: Alert ALERT-7823 (T1078). Action: SUPPRESS (0.910). Centroid: ps-0047." |

### 23.3 NLTemplateEngine Implementation

```python
# backend/app/services/nl_templates.py

class NLTemplateEngine:
    """24 deterministic NL templates across 3 layers.
    
    Layer 1 (L1): per-decision explanations — Tab 3 and shadow disagreements
    Layer 2 (L2): CISO-level summaries — Tab 5 Section 1 (What Changed) and Tab 2 narrative
    Layer 3 (L3): compliance records — evidence export, audit reports
    """

    # ── LAYER 1: Per-Decision (Tab 3) ────────────────────────────────────────
    # 7 templates: one per category (6), one generic. [CHANGED v5.5.1: was 8, refer_to_analyst removed]

    L1_TRAVEL_ANOMALY = (
        "{user_display} accessed from {location}. "
        "{travel_context}. "       # "No TravelRecord to Singapore in past 90 days"
        "{device_context}. "       # "MDM-enrolled device, last seen 4h ago"
        "{threat_context}. "       # "No ThreatIndicator matches (412 IOCs checked)"
        "{action_display} at {confidence:.0%} confidence. "
        "Calibrated from {calibration_count} verified outcomes on {category} alerts."
    )

    L1_CREDENTIAL_ACCESS = (
        "{user_display} accessed {asset_name} ({asset_criticality} criticality). "
        "{time_context}. "         # "Login at 03:17 UTC — 4.2 SD above baseline"
        "{pattern_context}. "      # "Pattern matches 3 prior escalations this month"
        "{threat_context}. "
        "{action_display} at {confidence:.0%} confidence. "
        "Calibrated from {calibration_count} verified outcomes."
    )

    L1_THREAT_INTEL_MATCH = (
        "Alert matches {indicator_type} from {source_name}. "
        "{ioc_context}. "          # "Source IP in active APT29 campaign IOC list (CISA KEV)"
        "{asset_context}. "        # "Target: finance_server (CRITICAL, stores PII)"
        "{pattern_context}. "
        "{action_display} at {confidence:.0%} confidence. "
        "Calibrated from {calibration_count} verified outcomes."
    )

    L1_INSIDER_BEHAVIORAL = (
        "{user_display} ({user_role}) performed: {action_description}. "
        "{access_context}. "       # "47% above role baseline data volume"
        "{pattern_context}. "      # "No prior access to this DataClass"
        "{asset_context}. "
        "{action_display} at {confidence:.0%} confidence. "
        "Calibrated from {calibration_count} verified outcomes."
    )

    L1_CLOUD_INFRASTRUCTURE = (
        "{cloud_operation} from {device_description}. "
        "{device_context}. "       # "Device not in CMDB — unregistered"
        "{threat_context}. "       # "Source IP: no IOC matches"
        "{pattern_context}. "
        "{action_display} at {confidence:.0%} confidence. "
        "Calibrated from {calibration_count} verified outcomes."
    )

    L1_REFER_TO_ANALYST = (
        "Confidence {confidence:.0%} — below {category} threshold ({threshold:.0%}). "
        "Dominant signal: {dominant_factor_explanation}. "
        "Refer to tier-1 analyst for 3-minute pre-analyzed review. "
        "Pre-analysis: {rationale}."
    )

    L1_LEARNING_UPDATE = (
        "Your feedback updated the {category} profile. "
        "Centroid drift: {delta_norm:.4f}. "
        "The system now weights {shifted_factor} {direction} ({before:.2f}→{after:.2f}) "
        "for {action} decisions in {category} alerts."
    )

    L1_GENERIC = (
        "{situation_type}: {dominant_factors_description}. "
        "{action_display} at {confidence:.0%} confidence. "
        "Calibrated from {calibration_count} verified outcomes on similar alerts."
    )

    # ── LAYER 2: CISO Weekly (Tab 5 Section 1 + Tab 2) ────────────────────────
    # 8 templates

    L2_WEEKLY_SUMMARY = (
        "This week: {total_alerts} alerts processed — "
        "{auto_approved} auto-approved ({auto_approve_rate:.1%}), "
        "{escalated} escalated, "
        "{human_review} required analyst override."
    )

    L2_ACCURACY_TREND = (
        "System accuracy: {current_week:.1%} this week | "
        "{last_week:.1%} last week | "
        "{at_deployment:.1%} at deployment."
    )

    L2_LEARNING_SUMMARY = (
        "What your system learned: {shift_1}. "
        "{shift_2}. "
        "Institutional Knowledge Score: {iks:.1f} (+{iks_delta:.1f} since last week)."
    )

    L2_RISK_POSTURE = (
        "Risk posture: {open_escalations} open escalations, "
        "{active_campaigns} active threat campaigns, "
        "{cisa_kev_matches} CISA KEV matches in your asset inventory."
    )

    L2_AUTO_APPROVE_BREAKDOWN = (
        "Autonomy envelope by category: "
        "cloud infrastructure {cloud_rate:.0%} (routine scans), "
        "threat intel matches {threat_rate:.0%} (known-benign), "
        "credential access {cred_rate:.0%}. "
        "High-risk categories (insider, lateral movement) held at <3% by design."
    )

    L2_IKS_NARRATIVE = (
        "Institutional Knowledge Score: {iks:.1f}. "
        "Your system has adapted {iks:.0f}% of the way from "
        "'no operational experience' to 'full environment adaptation' "
        "based on {decision_count} verified decisions."
    )

    L2_SHADOW_STATUS = (
        "Shadow mode: {days_active} days active, {decisions_recorded} decisions observed. "
        "Agreement rate: {agreement_rate:.1%}. "
        "Shadow report ready — review before activating live mode."
    )

    L2_THREAT_GRAPH = (
        "Your firm's threat graph: {ioc_count} unique indicators observed "
        "in YOUR environment. {cisa_kev_active} from active CISA KEV advisories. "
        "This intelligence accumulates over time and belongs exclusively to your firm."
    )

    # ── LAYER 3: Audit / Compliance Records ─────────────────────────────────
    # 8 templates

    L3_DECISION_RECORD = (
        "Decision ID:        {decision_id}\n"
        "Timestamp:          {timestamp}\n"
        "Alert:              {alert_id} (type: {alert_type}, ATT&CK: {technique_id})\n"
        "Category:           {category} (index: {category_idx})\n"
        "Action:             {action} (index: {action_idx}, confidence: {confidence:.4f})\n"
        "Factor vector:      {factor_vector}\n"
        "All distances:      {all_distances}\n"
        "Centroid snapshot:  {centroid_snapshot_id}\n"
        "Kernel:             {kernel}\n"
        "Shadow mode:        {shadow_mode}\n"
        "Human override:     {analyst_override}\n"
        "Outcome:            {outcome}\n"
        "Evidence hash:      {evidence_hash}"
    )

    L3_LEARNING_EVENT = (
        "Learning Event\n"
        "Decision:           {decision_id}\n"
        "Outcome:            {outcome} (verified by: {analyst_id})\n"
        "Category/Action:    {category} / {action}\n"
        "Factor vector used: {factor_vector}\n"
        "Centroid update:    ‖Δμ‖ = {delta_norm:.4f}\n"
        "Learning rate:      {learning_rate:.4f}\n"
        "Penalty applied:    {penalty_applied} (ratio: {penalty_ratio})\n"
        "Clip enforced:      {clipped} (all values in [0.0, 1.0])"
    )

    L3_CENTROID_STATE = (
        "Centroid Export\n"
        "Domain:             SOC\n"
        "Snapshot ID:        {snapshot_id}\n"
        "Timestamp:          {timestamp}\n"
        "t_decision:         {t_decision}\n"
        "Trigger:            {trigger}\n"
        "IKS at export:      {iks:.1f}\n"
        "Mean drift:         {mean_drift:.4f}\n"
        "Values in [0,1]:    {values_valid}\n"
        "Observation counts: {obs_counts}\n"
        "[centroid_array follows in next block]"
    )

    L3_DRIFT_ALERT = (
        "Drift Alert\n"
        "Alert type:         {alert_type}\n"
        "Category / Action:  μ[{category_idx}, {action_idx}, :] — {category} / {action}\n"
        "Observed drift:     {drift:.4f} (threshold: {threshold:.4f})\n"
        "Triggered at:       {timestamp}\n"
        "Available checkpoint: {checkpoint_id}\n"
        "Recommended action: Review recent feedback for potential bias in this category.\n"
        "Admin action required — system did NOT auto-revert."
    )

    L3_RESET_EVENT = (
        "System Event: {event_type}\n"
        "Timestamp:          {timestamp}\n"
        "Performed by:       {performed_by}\n"
        "Mode:               {mode}\n"
        "Centroid state before: {snapshot_id_before}\n"
        "Centroid state after:  {snapshot_id_after}\n"
        "Evidence chain hash:   {evidence_hash}"
    )

    L3_OVERRIDE_RECORD = (
        "Analyst Override\n"
        "Decision ID:        {decision_id}\n"
        "System:             {system_action} ({system_confidence:.4f})\n"
        "Analyst action:     {analyst_action}\n"
        "Analyst ID:         {analyst_id}\n"
        "Override timestamp: {timestamp}\n"
        "Reason:             {reason}\n"
        "Learning impact:    centroid updated with analyst action as correct outcome"
    )

    L3_WEEKLY_AUDIT = (
        "Audit Summary — Week {week_id}\n"
        "Total decisions:    {total_decisions}\n"
        "Auto-approved:      {auto_approved} ({auto_approve_rate:.1%})\n"
        "Analyst overrides:  {overrides}\n"
        "Centroid snapshots: {checkpoint_count}\n"
        "IKS start/end:      {iks_start:.1f} → {iks_end:.1f}\n"
        "Drift alerts:       {drift_alerts}\n"
        "Snapshot IDs:       {snapshot_ids}"
    )

    L3_MODEL_CARD = (
        "System Model Card\n"
        "Version:            {version}\n"
        "Scoring:            ProfileScorer, L2 distance, τ={tau:.3f}\n"
        "Categories (C):     {n_categories} ({categories})\n"
        "Actions (A):        {n_actions} ({actions})\n"
        "Factors (d):        {n_factors} ({factors})\n"
        "Bootstrap decisions:{bootstrap_count}\n"
        "Live decisions:     {live_count}\n"
        "Evaluation result:  {eval_accuracy:.1%} on {eval_scenarios} scenarios\n"
        "Calibration ECE:    {ece:.4f} at τ={tau:.3f}\n"
        "Last recalibration: {last_recalibration}\n"
        "IKS at export:      {iks:.1f}"
    )

    # ── Rendering Methods ────────────────────────────────────────────────────

    def render_l1(self, category: str, context: dict) -> str:
        template_map = {
            "travel_anomaly":       self.L1_TRAVEL_ANOMALY,
            "credential_access":    self.L1_CREDENTIAL_ACCESS,
            "threat_intel_match":   self.L1_THREAT_INTEL_MATCH,
            "insider_behavioral":   self.L1_INSIDER_BEHAVIORAL,
            "cloud_infrastructure": self.L1_CLOUD_INFRASTRUCTURE,
        }
        template = template_map.get(category, self.L1_GENERIC)
        return template.format_map(context)

    def render_l1_refer(self, context: dict) -> str:
        return self.L1_REFER_TO_ANALYST.format_map(context)

    def render_l1_learning_update(self, context: dict) -> str:
        return self.L1_LEARNING_UPDATE.format_map(context)

    def render_l2(self, template_name: str, context: dict) -> str:
        template = getattr(self, f"L2_{template_name.upper()}", None)
        if template is None:
            raise ValueError(f"Unknown L2 template: {template_name}")
        return template.format_map(context)

    def render_l3(self, template_name: str, context: dict) -> str:
        template = getattr(self, f"L3_{template_name.upper()}", None)
        if template is None:
            raise ValueError(f"Unknown L3 template: {template_name}")
        return template.format_map(context)

    def render_shadow_disagreement(self, decision: dict, alert: dict) -> str:
        """Generate explanation for a shadow mode disagreement entry."""
        factors = dict(zip(
            ["travel_match", "asset_criticality", "threat_intel_enrichment",
             "pattern_history", "time_anomaly", "device_trust"],
            decision.get("factor_vector", [0.5]*6)
        ))
        dominant = max(factors.items(), key=lambda x: abs(x[1] - 0.5))
        return (
            f"{dominant[0]}={dominant[1]:.2f}. "
            f"System: {decision['action']} ({decision['confidence']:.0%}). "
            f"Analyst: {decision['analyst_action']}. "
            f"Likely: analyst applied context outside the 6 factors."
        )
```

---

### 23.4 Similar Past Cases — Query Specification

**Status:** AUTHORITATIVE — v5.4-final. Sprint prompt EXP-2 (Phase 2) reads this section
directly. The §23.4 draft in v5.4-draft is superseded by this version.

**This section must be fully implemented before v5.5-T1-1 (NL Template Engine) ships.**
Without it, the "similar past cases" reference in every L1 template has no backing
query, and the agreement percentage cited in the template has no source.

**BLOCKED note for θ:** θ must be derived from PROD-3 output (p25 of the cosine
distance distribution). If PROD-3 has not run at implementation time: use design
estimate θ=0.85, log a `WARNING` on every query:
`"PROD-3 not yet run — using design estimate θ=0.85"`, and create a TODO in
`similar_cases.py` marked `# PROD-3-calibration-needed`.

---

#### Query Algorithm

```
Given alert with factor vector f ∈ [0,1]^6 and category c:

1. Retrieve all DecisionRecords with category == c from Neo4j.
2. For each retrieved record i: compute sim(f, f_i) = cosine_similarity(f, f_i)
3. Filter to records where sim ≥ θ  (θ from PROD-3 p25; design estimate 0.85)
4. Sort by sim DESC, then created_at DESC (recency as tie-breaker)
5. Return top k = 3
6. If fewer than min_prior = 5 DecisionRecords exist for category c:
   suppress sidebar entirely.
   Display: "Not enough prior decisions in this category yet."
```

#### Similarity Metric

```
sim(f_current, f_prior) = (f_current · f_prior) / (‖f_current‖ · ‖f_prior‖)
```

Rationale: cosine measures directional similarity between factor profiles — two alerts
with the same relative factor pattern (e.g., high travel_match + high asset_criticality)
are similar even if their absolute magnitudes differ. L2 distance is the scoring metric
(Eq. 4-final); cosine is the retrieval metric. They serve different purposes and must
not be conflated.

#### Parameters

```python
SIMILAR_CASES_K          = 3       # top-k results in sidebar
SIMILAR_CASES_MIN_PRIOR  = 5       # suppress if fewer than 5 verified decisions in category
SIMILAR_CASES_CATEGORY_FILTER = True  # restrict to same-category decisions (non-negotiable)
SIMILAR_CASES_TIE_BREAK  = "recency"  # among equal-sim: most recent first
```

**θ derivation (PROD-3):**
```python
# After PROD-3 completes — set per-category if distributions differ significantly:
SIMILAR_CASES_THETA = {
    "credential_access":    None,   # PROD-3 p25 — fill after experiment
    "lateral_movement":     None,
    "insider_threat":       None,
    "data_exfiltration":    None,
    "cloud_infrastructure": None,
    "_default":             0.85,   # design estimate until PROD-3 runs
}
```

If PROD-3 shows the cosine distance distribution is compressed (most pairs > 0.90):
raise θ to p50. If sparse (few pairs > 0.80): lower θ to p10. The goal is k=3 results
on average per query for a well-warmed category (200+ decisions).

**SIMILAR_CASES_CATEGORY_FILTER = True is non-negotiable.** Cross-category "similar
cases" produce misleading agreement percentages. A `cloud_infrastructure` suppress
is not comparable to a `credential_access` suppress even if their factor vectors
are similar — the centroid geometry differs by category.

#### Neo4j Query

```cypher
// Called by: SimilarCasesService.get_similar_cases(category, factor_vector, k)
// Returns:   list of {decision_id, action, confidence, outcome, sim_score, created_at}

MATCH (d:Decision {category: $category})
WHERE d.factor_vector IS NOT NULL
  AND d.outcome IS NOT NULL          // verified decisions only
WITH d,
     gds.similarity.cosine(
         $factor_vector,
         d.factor_vector
     ) AS sim_score
WHERE sim_score >= $theta
RETURN d.id            AS decision_id,
       d.action        AS action,
       d.confidence    AS confidence,
       d.outcome       AS outcome,
       sim_score,
       d.created_at    AS created_at
ORDER BY sim_score DESC, d.created_at DESC
LIMIT $k
```

**GDS availability:** requires `gds.similarity.cosine` (Neo4j Graph Data Science plugin).
Python fallback for environments without GDS:

```python
def _cosine_similarity_python(self, v1: list, v2: list) -> float:
    import numpy as np
    a, b = np.array(v1), np.array(v2)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom > 0 else 0.0

def get_similar_cases_fallback(self, category: str,
                                factor_vector: list, k: int = 3) -> list:
    """
    Python-side cosine for environments without Neo4j GDS.
    Retrieves all verified decisions for category, computes similarity in-process.
    For N > 10,000: restrict to last 500 decisions (see performance SLA).
    """
    decisions = self._get_all_verified_for_category(category, limit=500)
    scored = [
        (d, self._cosine_similarity_python(factor_vector, d["factor_vector"]))
        for d in decisions if d.get("factor_vector")
    ]
    filtered = [(d, s) for d, s in scored if s >= self._get_theta(category)]
    filtered.sort(key=lambda x: (-x[1], x[0]["created_at"]), reverse=False)
    return [d for d, _ in filtered[:k]]
```

#### Agreement Percentage Calculation

The agreement percentage cited in L1 templates ("aligns with 74% of similar prior
decisions") uses all verified decisions above θ, not just the top-k sidebar results:

```python
def get_agreement_pct(self, category: str, factor_vector: list,
                      recommended_action: str) -> float | None:
    """
    Fraction of verified decisions above θ where outcome matches recommended_action.
    Returns None if fewer than SIMILAR_CASES_MIN_PRIOR available — caller
    then uses fallback: "Calibrated from {n} verified outcomes." (no pct cited).
    """
    theta = self._get_theta(category)
    similar = self._query_all_above_threshold(category, factor_vector, theta)
    if len(similar) < SIMILAR_CASES_MIN_PRIOR:
        return None   # suppress — cold-start category
    matching = [d for d in similar if d["outcome"] == recommended_action]
    return len(matching) / len(similar)
```

When `get_agreement_pct` returns `None`, L1 templates fall back to:
`"Calibrated from {calibration_count} verified outcomes."` — no agreement percentage.

#### Display Specification (Per Matched Case)

Each of the top-k returned cases is displayed in the sidebar with:

```
Action taken:     [escalate / investigate / suppress / refer_to_analyst / defer]
Confidence:       [XX%] at decision time
Outcome:          [correct / incorrect / pending]  (if verified)
Similarity:       [XX%] match
When:             [N days/hours ago]
Analyst:          [anonymized — no original analyst ID exposed]
```

The anonymization rule: analyst IDs are replaced with `Analyst-{hash(analyst_id) % 999}`.
This suppresses interpersonal bias (analysts seeing their own past decisions or a
specific colleague's decisions) while preserving temporal and outcome information.

#### Performance SLA

```
< 200ms P95 for N_decisions < 10,000 in category.
For N > 10,000:
  - Use category-indexed query (index on Decision.category + Decision.created_at).
  - Limit scan to last 500 verified decisions per category.
  - Accept that agreement_pct is computed over a 500-decision window, not full history.
PERF-3 will verify this SLA after the NL template engine ships.
```

#### Service Location

```
backend/app/services/similar_cases.py   # SimilarCasesService
```

Call order: after `ProfileScorer.score()`, before `NLTemplateEngine.render_l1()`.
Result passed to L1 template context as:
  - `similar_cases_count` — int (0 if suppressed)
  - `agreement_pct`       — float | None
  - `similar_cases_list`  — list[dict] (empty if suppressed)

---

### 23.5 Acceptance Test — NL Template Judge Rubric

**Status:** AUTHORITATIVE — v5.4-final. Sprint prompt EXP-1 (Phase 2) acceptance
criterion points directly at this section. The §23.5 draft in v5.4-draft is superseded.

**This rubric must exist and be executable before v5.5-T1-1 (NL Template Engine)**
**can be declared done.** Without it, there is no objective criterion for whether
the templates are working correctly. The PROD-2 partner analyst gate also uses this rubric.

> **v5.4-draft vs v5.4-final distinction:** The draft used a pure LLM judge (30
> explanations, 6×5 [NOTE: A=5 at time of writing; now A=4 → 24 templates], LLM Sonnet scoring all criteria). This version is a human analyst
> study (N=5, M=10 centroid-template pairs, 50 total judgments) with an interpretation
> accuracy gate. The LLM judge prompt in Criterion 1 is retained for the factual accuracy
> component only. The study design and interpretation gate are new.

---

#### Study Design

```
N  = 5  SOC analysts (or proxy: 5 domain-expert review sessions)
M  = 10 centroid-template pairs
Total judgments: 50  (5 analysts × 10 pairs)

Template selection rules:
  - ≥2 templates per category (5 categories × 2 minimum = 10 pairs at minimum)
  - ≥1 borderline case: centroid near-equal between two actions
    (tests whether the template's language is appropriately hedged for
     uncertain centroid states — the hardest case for Criterion 3)
  - ≥1 cold-start case: category with fewer than SIMILAR_CASES_MIN_PRIOR decisions
    (tests whether fallback language is used instead of agreement percentage)
```

#### Per-Judgment Protocol

Each analyst receives:

1. **The centroid NL template** — the text generated by `NLTemplateEngine.render_l1()`
   for a specific (category, centroid_state) pair
2. **3 test alerts** — real or realistic alerts from that category, with factor vectors
   that the analyst must use to predict the system's action

The analyst:
- Rates the template on 4 criteria (1–5 scale, see rubrics below)
- Predicts the system's recommended action for each of the 3 test alerts

**Interpretation accuracy** = fraction of the 3 alert predictions that match the actual
`ProfileScorer.score()` output for that alert. Gate: mean ≥70% across all 50 judgment
pairs (i.e., 150 total alert predictions across all analysts and pairs, ≥105 correct).

---

#### Criterion 1 — Factual Accuracy (weight: critical)

**Question:** Do the claims in the generated text match the factor values and graph
data that were passed into the template?

**Rubric:**
- 5: Every named entity (user, asset, location, IOC), every statistic (confidence %,
  calibration count, factor value), and every graph-sourced statement (TravelRecord,
  ThreatIndicator, MDM status) is accurate relative to the template context dict.
- 4: One minor inaccuracy (e.g., rounded confidence cited differently from raw value).
- 3: One factual error that would not mislead an analyst (e.g., wrong count by small
  margin, ±1 on a count).
- 2: A factual error that could mislead an analyst (e.g., wrong asset criticality
  tier cited, wrong action recommended in the explanation body).
- 1: Multiple factual errors or a hallucinated entity not in the context dict.

**Gate: mean ≥ 4.0 across all 50 judgments.**

**LLM judge component (Factual Accuracy only):**
For at-scale evaluation beyond the 50-judgment study, Factual Accuracy may be
evaluated by Claude Sonnet with this prompt fragment:

```
Given this template context dict: {context_dict}
And this generated explanation: {explanation}
Rate factual accuracy on a 1–5 scale.
For each claim in the explanation: state whether it is directly supported by
the context dict, derivable from context dict values, or unsupported/hallucinated.
Deduct one point per unsupported claim. Deduct two points if any claim could
actively mislead an analyst.
Output format: {"score": N, "claims": [{"text": "...", "supported": bool, "source_key": "..."}]}
```

---

#### Criterion 2 — Specificity (weight: high)

**Question:** Does the explanation reference at least one specific graph entity (user
name or role, asset name, location, IP address, ThreatIndicator source, or IOC type)?
A generic explanation that could apply to any alert of that category fails this criterion.

**Rubric:**
- 5: Two or more specific entities from the graph, each adding distinct information
  that differentiates this alert from a generic instance of the category.
- 4: One specific entity that materially differentiates this alert from a generic
  instance of the category.
- 3: One entity referenced but vague ("a critical asset" vs. "the domain controller
  DC-PROD-01") — not specific enough to be actionable.
- 2: No specific entities — explanation is generic to the category.
- 1: Explanation could apply to any alert in any category.

**Gate: mean ≥ 3.5 across all 50 judgments.**

---

#### Criterion 3 — Actionability (weight: high)

**Question:** Can a non-technical analyst understand what action is recommended and
why, without reading the numerical factor table?

**Rubric:**
- 5: Recommendation is unambiguous, reason is clear in plain English, analyst knows
  what to do next without any additional context (factor table, prior knowledge).
- 4: Recommendation clear, reason partially obscured by jargon or one missing context
  item that a semi-technical analyst would know.
- 3: Recommendation clear, but "why" requires reading the factor table to understand.
- 2: Recommendation present but explanation confusing, contradictory, or hedged so
  heavily that the analyst cannot confidently act on it.
- 1: Analyst cannot determine action or reason from the explanation alone.

**Gate: mean ≥ 3.5 across all 50 judgments.**

**Borderline centroid note:** For the ≥1 borderline case (near-equal centroid between
two actions), the acceptable template pattern is:
`"The system is balanced between [action A] and [action B]. At this confidence
 level, [contextual factor] is the deciding factor. Recommended: [action A]."
`
A score of 4 is appropriate for a borderline case where the hedge is accurate and
the deciding factor is stated. Score of 3 if the hedge exists but the deciding factor
is absent. Score of 2 if there is no hedge for a near-equal centroid.

---

#### Criterion 4 — Non-Redundancy (weight: medium)

**Question:** Does the explanation add information beyond what is already visible in
the numerical factor table (factor_name: value pairs)?

**Rubric:**
- 5: Explanation substantially enriches the factor table — adds graph context,
  similar case comparison, or temporal context not visible in raw numbers.
- 4: Adds moderate enrichment (one graph-sourced contextual statement, or one
  similar case reference with specifics).
- 3: Mostly restates the factor table in English — adds little new information.
- 2: Explanation is a direct English translation of the factor table.
- 1: Explanation is less informative than the factor table it is supposed to enrich.

**Gate: mean ≥ 3.0 across all 50 judgments.**

---

#### Aggregate Pass Criteria

```
Mean Factual Accuracy (Criterion 1)  ≥ 4.0   (50 judgments)
Mean Specificity (Criterion 2)        ≥ 3.5
Mean Actionability (Criterion 3)      ≥ 3.5
Mean Non-Redundancy (Criterion 4)     ≥ 3.0
No single criterion mean              < 3.0   (triggers template redesign)

Mean Interpretation Accuracy          ≥ 70%   (150 alert predictions — 5 analysts ×
                                               10 pairs × 3 alerts each)
```

**Interpretation accuracy is an independent gate.** A template can be beautifully
written (Criteria 1-4 all pass) yet fail the interpretation gate if its language does
not communicate the system's confidence regime clearly enough for analysts to predict
system behavior. Both gates must pass for T1-1 to close.

---

#### Output File Format

```json
// tests/nl_template_judge_results.json
[
  {
    "centroid_id":             "credential_access__escalate",
    "template_version":        "v1.0",
    "analyst_id":              "A001",
    "criteria_scores": {
      "factual_accuracy":      4,
      "specificity":           4,
      "actionability":         3,
      "non_redundancy":        4
    },
    "alert_predictions":       ["escalate", "escalate", "investigate"],
    "actual_system_actions":   ["escalate", "investigate", "investigate"],
    "interpretation_accuracy": 0.67,
    "notes":                   "Hedging language for borderline case was unclear.",
    "timestamp":               "2026-03-15T10:22:00Z"
  }
]
```

The aggregate summary is written to `tests/nl_template_judge_summary.json`:

```json
{
  "total_judgments": 50,
  "total_alert_predictions": 150,
  "mean_scores": {
    "factual_accuracy":      4.1,
    "specificity":           3.7,
    "actionability":         3.6,
    "non_redundancy":        3.2
  },
  "mean_interpretation_accuracy": 0.74,
  "gate_pass": {
    "factual_accuracy":          true,
    "specificity":               true,
    "actionability":             true,
    "non_redundancy":            true,
    "interpretation_accuracy":   true,
    "overall":                   true
  }
}
```

---

#### When to Run

1. After initial NLTemplateEngine implementation (all 24 templates written).
2. After any template revision affecting ≥3 templates.
3. As part of PROD-2 gate evaluation (partner analyst study — Step 2 uses same rubric
   with real partner analysts, not internal review proxies).

---

#### Remediation Paths

| Failing gate | Root cause (most likely) | Required fix |
|---|---|---|
| Factual Accuracy < 4.0 | Template is reading wrong key from context dict, or context dict is not populated correctly by the calling endpoint | Audit `factor_value → template text` mapping for all 24 templates. Add assertion: every template variable must appear in the context dict, or render fails loudly (no silent missing-key substitution). |
| Specificity < 3.5 | Templates are using generic category-level language instead of entity resolution calls | Add Neo4j entity resolution calls to the NL template engine. For each alert, resolve: user display name (from CMDB or LDAP stub), asset canonical name (from AssetCriticality factor), IOC type (from ThreatIntelEnrichment). Pass resolved entities into L1 template context. |
| Actionability < 3.5 | Confidence language is too hedged or too technical | Add explicit confidence regime language: `"system recommends escalation with {confidence}% confidence — above the {threshold}% threshold for this category."` The threshold is visible and the confidence regime is named. |
| Non-Redundancy < 3.0 | Templates are translating factor table to English, not enriching it | Add ≥1 graph-sourced contextual sentence per template that is not present in the factor table. Minimum viable enrichment: similar past cases count + agreement percentage (if available). |
| Interpretation Accuracy < 70% | Templates do not communicate how confidence maps to actions clearly enough for analysts to predict system behavior | Add explicit confidence regime table to L1 templates: `"At this category, the system escalates when confidence > {threshold_escalate}%, investigates between {threshold_investigate}% and {threshold_escalate}%..."` This makes the decision boundary visible, enabling analysts to calibrate their predictions. |

---

## 24. SemanticRegistry Integration (SOC Domain) + Tab 5 Design

### 24.0 Tab 5 vs Tab 1 Panel B — The Distinction

Two surfaces use the SemanticRegistry and QueryCatalog. They serve different audiences and ship at different versions:

| Surface | Tab | Audience | Version | What it answers |
|---|---|---|---|---|
| **Graph Explorer** | Tab 1 Panel B | SOC analyst | v5.5 (F14-basic) | "Show me the data behind this alert category / threat indicator / analyst pattern." |
| **Exec Learning Narrative** | Tab 5 | CISO / exec | v6.0 (F12) | "What has this system learned, and how has its judgment changed since last week?" |

Tab 5 is **not** a query interface. It is a changelog of institutional judgment — three sections: What Changed Since Last Time, What Was Discovered (DiscoveryRule protocol, ci-platform), What the System Now Knows. No alert detail. No factor vectors. No graph queries. If it requires reading an alert, it does not belong in Tab 5.

Tab 1 Panel B is the analyst query surface. It lives within Tab 1 (information-only tab — no shared alert state with Tab 2/Tab 3). At v5.5 it uses structured templates. At v6.0 it gains LLM NL→Cypher→NL.

### 24.1 SOC concepts.yaml (20 Named Concepts)

The SemanticRegistry (ci-platform §13.1) loads this file at startup. The 20 concepts serve two consumers: (1) the Tab 1 Panel B GraphExplorer queries at v5.5, and (2) the Tab 5 Section 1 data queries that feed the learning narrative at v6.0. See ci_platform_design_v5_1 §13.1 for SemanticRegistry architecture.

```yaml
# soc-copilot/semantics/concepts.yaml
domain: soc
version: "1.0.0"
description: "Named SOC graph concepts for Tab 1 Graph Explorer (v5.5) and Tab 5 learning narrative data queries (v6.0)"

concepts:

  - name: alerts_this_week
    description: "Total alerts processed in the past 7 days"
    cypher_template: |
      MATCH (a:Alert)
      WHERE a.timestamp > datetime() - duration({days: 7})
      RETURN count(a) AS alert_count
    parameters: {}
    aliases: ["alerts processed", "alerts this week", "total alerts", "alert volume"]
    output_schema: {type: "metric", field: "alert_count"}
    owner: "soc-team"

  - name: auto_approved_this_week
    description: "Alerts auto-approved (system confidence ≥ threshold, no override) in past 7 days"
    cypher_template: |
      MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)
      WHERE d.timestamp > datetime() - duration({days: 7})
        AND d.action = 'suppress'
        AND d.confidence >= $threshold
        AND d.shadow_mode = false
        AND d.analyst_override IS NULL
      RETURN count(d) AS auto_approved_count
    parameters: {threshold: 0.80}
    aliases: ["auto-approved", "automated decisions", "auto approved this week"]
    output_schema: {type: "metric", field: "auto_approved_count"}
    owner: "soc-team"

  - name: auto_approve_coverage
    description: "Auto-approve rate as fraction of total decisions (past 7 days)"
    cypher_template: |
      MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)
      WHERE d.timestamp > datetime() - duration({days: 7}) AND d.shadow_mode = false
      WITH count(d) AS total,
           sum(CASE WHEN d.action='suppress' AND d.confidence>=$threshold AND d.analyst_override IS NULL
                    THEN 1 ELSE 0 END) AS auto_approved
      RETURN CASE WHEN total > 0 THEN toFloat(auto_approved)/total ELSE 0.0 END AS coverage
    parameters: {threshold: 0.80}
    aliases: ["auto-approve rate", "autonomy rate", "automation coverage"]
    output_schema: {type: "metric", field: "coverage"}
    owner: "soc-team"

  - name: active_campaigns
    description: "Threat campaigns with at least one associated alert in past N days"
    cypher_template: |
      MATCH (ti:ThreatIntel)-[:ASSOCIATED_WITH]->(a:Alert)
      WHERE a.timestamp > datetime() - duration({days: $days})
      RETURN ti AS campaign, count(a) AS alert_count
      ORDER BY alert_count DESC
    parameters: {days: 30}
    aliases: ["active campaigns", "current threat campaigns", "ongoing threats",
              "active threat activity"]
    output_schema: {type: "list", node_type: "ThreatIntel", has_count: true}
    owner: "soc-team"

  - name: cisa_kev_matches
    description: "CISA KEV entries with matching indicators in this firm's alert stream"
    cypher_template: |
      MATCH (ti:ThreatIndicator {source: 'cisa_kev'})
      OPTIONAL MATCH (ti)-[:LINKED_TO_IOC]-(a:Alert)
      WHERE a.timestamp > datetime() - duration({days: $days})
      RETURN ti AS kev_entry, count(a) AS alert_count
      ORDER BY ti.cve_published DESC
    parameters: {days: 30}
    aliases: ["CISA KEV", "known exploited vulnerabilities", "KEV matches",
              "active CVEs", "cisa matches"]
    output_schema: {type: "list", node_type: "ThreatIndicator", has_count: true}
    owner: "soc-team"

  - name: open_escalations
    description: "Escalated decisions with no recorded outcome"
    cypher_template: |
      MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)
      WHERE d.action IN ['escalate'] AND d.outcome IS NULL
        AND d.shadow_mode = false
      RETURN d AS decision, a AS alert
      ORDER BY d.timestamp DESC
    parameters: {}
    aliases: ["open escalations", "unresolved escalations", "pending escalations",
              "outstanding escalations"]
    output_schema: {type: "list", node_type: "Decision"}
    owner: "soc-team"

  - name: critical_assets
    description: "Assets with criticality_score above threshold with active monitoring"
    cypher_template: |
      MATCH (a:Asset)
      WHERE a.criticality_score >= $threshold AND a.monitoring_active = true
      RETURN a AS asset
      ORDER BY a.criticality_score DESC
    parameters: {threshold: 0.8}
    aliases: ["critical assets", "high-value assets", "crown jewels", "priority assets"]
    output_schema: {type: "list", node_type: "Asset"}
    owner: "soc-team"

  - name: threat_indicator_count
    description: "Total ThreatIndicator nodes accumulated in this firm's graph"
    cypher_template: |
      MATCH (ti:ThreatIndicator)
      RETURN count(ti) AS ioc_count,
             sum(CASE WHEN ti.source='cisa_kev' THEN 1 ELSE 0 END) AS cisa_count
    parameters: {}
    aliases: ["IOC count", "threat indicator count", "known IOCs",
              "threat memory", "firm threat intelligence count"]
    output_schema: {type: "metric", fields: ["ioc_count", "cisa_count"]}
    owner: "soc-team"

  - name: accuracy_trend
    description: "System decision accuracy over rolling 7-day windows (past 90 days)"
    cypher_template: |
      MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)
      WHERE d.outcome IS NOT NULL AND d.shadow_mode = false
        AND d.timestamp > datetime() - duration({days: $lookback_days})
      WITH d.timestamp.week AS week_num, d.timestamp.year AS yr,
           count(d) AS total,
           sum(CASE WHEN d.correct THEN 1 ELSE 0 END) AS correct
      RETURN yr, week_num, total,
             CASE WHEN total > 0 THEN toFloat(correct)/total ELSE null END AS accuracy
      ORDER BY yr, week_num
    parameters: {lookback_days: 90}
    aliases: ["accuracy trend", "accuracy over time", "weekly accuracy",
              "getting smarter", "improvement trend"]
    output_schema: {type: "timeseries", fields: ["week_num", "accuracy"]}
    owner: "soc-team"

  - name: analyst_override_rate
    description: "Rate at which analysts override system recommendations, per analyst"
    cypher_template: |
      MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)
      WHERE d.shadow_mode = false
        AND d.timestamp > datetime() - duration({days: $days})
      RETURN d.analyst_override AS analyst,
             count(d) AS total_seen,
             sum(CASE WHEN d.analyst_override IS NOT NULL THEN 1 ELSE 0 END) AS overrides
      ORDER BY overrides DESC
    parameters: {days: 30}
    aliases: ["override rate", "analyst override", "analyst agreement",
              "highest override analyst", "who overrides most"]
    output_schema: {type: "list", fields: ["analyst", "total_seen", "overrides"]}
    owner: "soc-team"

  - name: category_accuracy
    description: "Per-category decision accuracy (all time with enough data)"
    cypher_template: |
      MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)
      WHERE d.outcome IS NOT NULL AND d.shadow_mode = false
      RETURN a.situation_type AS category,
             count(d) AS total,
             sum(CASE WHEN d.correct THEN 1 ELSE 0 END) AS correct,
             toFloat(sum(CASE WHEN d.correct THEN 1 ELSE 0 END))/count(d) AS accuracy
      ORDER BY accuracy DESC
    parameters: {}
    aliases: ["category accuracy", "accuracy by category", "per category accuracy",
              "which categories are best", "category performance"]
    output_schema: {type: "list", fields: ["category", "total", "accuracy"]}
    owner: "soc-team"

  - name: lateral_movement_trend
    description: "Lateral movement (insider_behavioral) alert volume and escalation rate over 30 days"
    cypher_template: |
      MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert {situation_type: 'insider_behavioral'})
      WHERE a.timestamp > datetime() - duration({days: $days})
      RETURN count(a) AS total_alerts,
             sum(CASE WHEN d.action = 'escalate' THEN 1 ELSE 0 END) AS escalations,
             count(a.timestamp.week) AS weeks_active
      ORDER BY a.timestamp.week
    parameters: {days: 30}
    aliases: ["lateral movement", "insider behavioral trend", "lateral movement alerts",
              "insider threat volume"]
    output_schema: {type: "metric", fields: ["total_alerts", "escalations"]}
    owner: "soc-team"

  - name: top_iocs
    description: "ThreatIndicator nodes seen in the most alerts (past N days)"
    cypher_template: |
      MATCH (ti:ThreatIndicator)-[:LINKED_TO_IOC]-(a:Alert)
      WHERE a.timestamp > datetime() - duration({days: $days})
      RETURN ti AS ioc, count(a) AS alert_count
      ORDER BY alert_count DESC
      LIMIT $limit
    parameters: {days: 30, limit: 10}
    aliases: ["top IOCs", "most seen threats", "frequent threat indicators",
              "common IOCs", "top indicators"]
    output_schema: {type: "list", node_type: "ThreatIndicator", has_count: true}
    owner: "soc-team"

  - name: human_review_queue
    description: "Alerts with confidence below 0.70 awaiting tier-2 analyst review"
    cypher_template: |
      MATCH (d:Decision)-[:DECIDED_ON]->(a:Alert)
      WHERE d.action = 'refer_to_analyst' OR d.confidence < 0.70
        AND d.outcome IS NULL AND d.shadow_mode = false
      RETURN d AS decision, a AS alert
      ORDER BY d.confidence ASC
    parameters: {}
    aliases: ["human review queue", "analyst queue", "review queue",
              "low confidence alerts", "alerts needing review"]
    output_schema: {type: "list", node_type: "Decision"}
    owner: "soc-team"

  - name: centroid_drift_by_category
    description: "Per-category centroid drift from bootstrap baseline (current state)"
    cypher_template: |
      MATCH (ps:ProfileSnapshot)
      RETURN ps.centroid_array AS centroids, ps.t_decision AS t
      ORDER BY ps.created_at DESC LIMIT 1
    parameters: {}
    aliases: ["centroid drift", "what the system learned", "learning progress by category",
              "category adaptation"]
    output_schema: {type: "centroid_derived", computation: "l2_per_category"}
    owner: "soc-team"

  - name: institutional_knowledge_score
    description: "Current IKS — how far centroids have drifted from bootstrap toward full adaptation"
    cypher_template: |
      MATCH (ps:ProfileSnapshot)
      RETURN ps.centroid_array AS centroids, ps.t_decision AS t, ps.created_at AS ts
      ORDER BY ps.created_at DESC LIMIT 1
    parameters: {}
    aliases: ["IKS", "institutional knowledge", "how smart is it", "knowledge score",
              "how much has it learned", "learning score"]
    output_schema: {type: "iks_derived", computation: "iks_from_centroids"}
    owner: "soc-team"

  - name: shadow_agreement_rate
    description: "Shadow mode agreement rate (if shadow mode has been active)"
    cypher_template: |
      MATCH (d:Decision {shadow_mode: true})
      WHERE d.analyst_action IS NOT NULL
      RETURN count(d) AS total,
             sum(CASE WHEN d.analyst_agreed THEN 1 ELSE 0 END) AS agreed,
             toFloat(sum(CASE WHEN d.analyst_agreed THEN 1 ELSE 0 END))/count(d) AS rate
    parameters: {}
    aliases: ["shadow agreement", "shadow mode results", "how accurate is shadow",
              "analyst agreement rate", "shadow accuracy"]
    output_schema: {type: "metric", fields: ["total", "agreed", "rate"]}
    owner: "soc-team"

  - name: blast_radius_candidates
    description: "Assets connected to active threat indicators — potential blast radius targets"
    cypher_template: |
      MATCH (ti:ThreatIndicator)-[:LINKED_TO_IOC]-(a:Alert)-[:DECIDED_ON]-(d:Decision)
      MATCH (asset:Asset)-[:STORES]->(dc:DataClass)
        WHERE dc.sensitivity = 'high'
      WHERE a.timestamp > datetime() - duration({days: $days})
      RETURN asset, count(ti) AS threat_count
      ORDER BY threat_count DESC LIMIT $limit
    parameters: {days: 7, limit: 5}
    aliases: ["blast radius", "at risk assets", "potential targets", "threatened assets"]
    output_schema: {type: "list", node_type: "Asset", has_count: true}
    owner: "soc-team"

  - name: top_centroid_changes
    description: "Top (category, action) centroid cells with largest drift from bootstrap"
    cypher_template: |
      MATCH (ps:ProfileSnapshot)
      RETURN ps.centroid_array AS centroids
      ORDER BY ps.created_at DESC LIMIT 1
    parameters: {}
    aliases: ["top centroid changes", "what changed most", "biggest learning changes",
              "most adapted categories"]
    output_schema: {type: "centroid_derived", computation: "top_drift_cells"}
    owner: "soc-team"

  - name: escalation_breakdown
    description: "Escalation decisions by category and time period"
    cypher_template: |
      MATCH (d:Decision {action: 'escalate'})-[:DECIDED_ON]->(a:Alert)
      WHERE d.timestamp > datetime() - duration({days: $days})
        AND d.shadow_mode = false
      RETURN a.situation_type AS category, count(d) AS escalation_count,
             avg(d.confidence) AS avg_confidence
      ORDER BY escalation_count DESC
    parameters: {days: 30}
    aliases: ["escalation breakdown", "escalations by category", "what gets escalated",
              "escalation distribution"]
    output_schema: {type: "list", fields: ["category", "escalation_count", "avg_confidence"]}
    owner: "soc-team"
```

### 24.2 SOC queries.yaml (15 Pre-Built Queries — Tab 1 Graph Explorer + Tab 5 Data)

The QueryCatalog (ci-platform §13.2) loads this file. At v5.5, these queries power Tab 1 Panel B (Graph Explorer — analyst surface). At v6.0, a subset also feeds the Tab 5 learning narrative section data pulls. The QueryRouter uses `nl_patterns` for fast-path matching before falling back to LLM routing.

```yaml
# soc-copilot/queries/queries.yaml
domain: soc
version: "1.0.0"

queries:

  - name: threat_posture_this_week
    description: "Summary of active threats, IOC matches, and CISA KEV exposure this week"
    nl_patterns:
      - "threat posture this week"
      - "what threats are active"
      - "what is the threat landscape"
      - "ransomware posture"
      - "current threat status"
    concept_dependencies: [active_campaigns, cisa_kev_matches, threat_indicator_count]
    output_type: narrative
    requires_synthesis: false

  - name: auto_approve_coverage
    description: "Auto-approve coverage breakdown by category with trend"
    nl_patterns:
      - "auto-approve coverage"
      - "automation rate"
      - "how many alerts are automated"
      - "what percentage does it handle automatically"
      - "autonomy envelope"
    concept_dependencies: [auto_approved_this_week, auto_approve_coverage, accuracy_trend]
    output_type: table_plus_narrative
    requires_synthesis: false

  - name: lateral_movement_trend
    description: "Insider behavioral / lateral movement volume and escalation trend"
    nl_patterns:
      - "lateral movement trend"
      - "insider behavioral trend"
      - "lateral movement alerts"
      - "how many insider threat alerts"
    concept_dependencies: [lateral_movement_trend, category_accuracy]
    output_type: chart_plus_narrative
    requires_synthesis: false

  - name: credential_access_summary
    description: "Credential access alerts: volume, escalation rate, top affected assets"
    nl_patterns:
      - "credential access summary"
      - "credential alerts this week"
      - "brute force activity"
      - "login anomaly summary"
    concept_dependencies: [category_accuracy, critical_assets]
    output_type: table_plus_narrative
    requires_synthesis: false

  - name: escalation_breakdown
    description: "Which categories get escalated, at what confidence, over what time window"
    nl_patterns:
      - "escalation breakdown"
      - "what gets escalated"
      - "escalation distribution"
      - "show escalations by category"
    concept_dependencies: [escalation_breakdown, open_escalations]
    output_type: table_plus_narrative
    requires_synthesis: false

  - name: analyst_override_rate
    description: "Analyst override rate by analyst — who overrides most, and in which categories"
    nl_patterns:
      - "analyst override rate"
      - "who overrides the system most"
      - "analyst agreement breakdown"
      - "which analyst has highest override"
      - "override breakdown"
    concept_dependencies: [analyst_override_rate]
    output_type: table
    requires_synthesis: false

  - name: institutional_knowledge_score
    description: "Current IKS with trend, interpretation, and top centroid changes"
    nl_patterns:
      - "institutional knowledge score"
      - "IKS"
      - "how smart is the system"
      - "how much has it learned"
      - "knowledge score"
      - "is it getting smarter"
    concept_dependencies: [institutional_knowledge_score, top_centroid_changes, centroid_drift_by_category]
    output_type: metric_plus_narrative
    requires_synthesis: false

  - name: shadow_mode_agreement
    description: "Shadow mode agreement rate with disagreement breakdown (if shadow data exists)"
    nl_patterns:
      - "shadow mode results"
      - "shadow agreement"
      - "how accurate was shadow"
      - "shadow report summary"
    concept_dependencies: [shadow_agreement_rate]
    output_type: narrative_plus_table
    requires_synthesis: false

  - name: top_centroid_changes
    description: "Which (category, action) centroid cells have drifted most from bootstrap"
    nl_patterns:
      - "top centroid changes"
      - "what changed most"
      - "biggest learning changes"
      - "what has the system adapted most to"
    concept_dependencies: [top_centroid_changes, centroid_drift_by_category]
    output_type: table_plus_narrative
    requires_synthesis: false

  - name: active_campaigns
    description: "Active threat campaigns in this environment with associated alert count"
    nl_patterns:
      - "active campaigns"
      - "current threat campaigns"
      - "what campaigns are active"
      - "threat campaigns this month"
    concept_dependencies: [active_campaigns]
    output_type: list_plus_narrative
    requires_synthesis: false

  - name: cisa_kev_matches
    description: "CISA KEV advisories with matching indicators in this firm's environment"
    nl_patterns:
      - "CISA KEV matches"
      - "known exploited vulnerabilities"
      - "CVE matches"
      - "active vulnerability exposure"
      - "KEV in our environment"
    concept_dependencies: [cisa_kev_matches, critical_assets]
    output_type: table_plus_narrative
    requires_synthesis: false

  - name: blast_radius_candidates
    description: "High-value assets connected to active threat indicators"
    nl_patterns:
      - "blast radius"
      - "at risk assets"
      - "potential targets"
      - "what assets are threatened"
      - "which assets are exposed"
    concept_dependencies: [blast_radius_candidates, cisa_kev_matches]
    output_type: table_plus_narrative
    requires_synthesis: false

  - name: category_accuracy_trend
    description: "Per-category accuracy trend over the past 90 days"
    nl_patterns:
      - "category accuracy"
      - "accuracy by category"
      - "which categories is it best at"
      - "per category performance"
      - "accuracy trend by type"
    concept_dependencies: [category_accuracy, accuracy_trend]
    output_type: chart_plus_table
    requires_synthesis: false

  - name: top_iocs
    description: "Most frequently seen threat indicators in this firm's alert stream"
    nl_patterns:
      - "top IOCs"
      - "most common threat indicators"
      - "frequent threats"
      - "what IOCs appear most"
      - "our IOC memory"
    concept_dependencies: [top_iocs, threat_indicator_count]
    output_type: table_plus_narrative
    requires_synthesis: false

  - name: human_review_queue
    description: "Low-confidence alerts currently in the human review queue"
    nl_patterns:
      - "human review queue"
      - "what needs review"
      - "analyst queue"
      - "low confidence alerts"
      - "what is waiting for a human"
    concept_dependencies: [human_review_queue]
    output_type: table
    requires_synthesis: false
```

---

## 25. Enterprise Integration Hooks

### 25.1 Purpose

Enterprise IT teams cannot integrate using the SourceConnector Python protocol directly — it requires understanding SourceNode, SourceEdge, and GraphIngester internals. The EnterpriseConnectorProfile pattern (ci-platform §13.3) solves this: IT teams fill in a YAML template describing their data source; the platform generates a working connector.

The SOC copilot provides two pre-built profiles: CMDB and Identity (AD/LDAP). The ServiceNow action stub is the v6.0 write-back implementation.

### 25.2 CMDBConnectorProfile

```yaml
# soc-copilot/enterprise/connectors/cmdb_profile.yaml
# CMDBConnectorProfile — IT team fills in the <PLACEHOLDERS>
# Platform generates a working SourceConnector from this file.

profile_type: CMDBConnectorProfile
tier: 1                                    # authoritative
cadence: daily
entity_type_produced: Asset

connection:
  base_url: <CMDB_API_URL>                 # e.g. https://cmdb.corp.example.com/api
  auth_type: api_key                       # api_key | oauth2 | basic
  api_key_env_var: CMDB_API_KEY            # name of the env var holding the key

entity_mappings:
  - source_field: ci_id                    # CMDB field name
    target_property: id                    # Asset node property
    required: true
  - source_field: ci_name
    target_property: name
    required: true
  - source_field: criticality_level        # CMDB's criticality field
    target_property: criticality_score     # Normalized to [0,1] by transformer
    transformer: cmdb_criticality_to_float # maps LOW/MED/HIGH/CRITICAL → 0.2/0.4/0.7/1.0
    required: true
  - source_field: monitoring_status
    target_property: monitoring_active
    transformer: yes_no_to_bool
    required: false
  - source_field: owner_team
    target_property: owner
    required: false
  - source_field: data_classification       # e.g. PII, PHI, RESTRICTED
    target_property: data_class
    required: false

semantic_registry_concept: critical_assets  # validates output against this concept
validation_query: |
  MATCH (a:Asset) WHERE a.criticality_score IS NOT NULL
  RETURN count(a) AS count
  # Must return > 0 after first successful run
```

### 25.3 IdentityConnectorProfile

```yaml
# soc-copilot/enterprise/connectors/identity_profile.yaml
# IdentityConnectorProfile — AD/LDAP/HR system integration

profile_type: IdentityConnectorProfile
tier: 1
cadence: hourly
entity_type_produced: User

connection:
  source_type: ldap                        # ldap | ad | okta | hr_api
  host: <LDAP_HOST>
  port: 636
  bind_dn_env_var: LDAP_BIND_DN
  bind_pw_env_var: LDAP_BIND_PW
  base_dn: <BASE_DN>                       # e.g. dc=corp,dc=example,dc=com
  user_filter: "(objectClass=person)"

entity_mappings:
  - source_field: sAMAccountName
    target_property: username
    required: true
  - source_field: mail
    target_property: email
    required: false
  - source_field: department
    target_property: department
    required: false
  - source_field: title
    target_property: role
    required: false
  - source_field: manager
    target_property: manager_dn
    required: false
  - source_field: memberOf                  # group memberships
    target_property: groups
    transformer: dn_list_to_group_names
    required: false
  - source_field: pwdLastSet
    target_property: last_password_change
    transformer: ad_timestamp_to_datetime
    required: false

# Relationship enrichment — creates [:IN_ROLE], [:REPORTS_TO] edges
relationship_mappings:
  - source_field: department
    relationship_type: IN_DEPARTMENT
    target_node_type: Department
    target_lookup_property: name
  - source_field: manager
    relationship_type: REPORTS_TO
    target_node_type: User
    target_lookup_property: dn

validation_query: |
  MATCH (u:User) WHERE u.username IS NOT NULL
  RETURN count(u) AS count
```

### 25.4 ServiceNowIncidentAction (v6.0 stub)

```python
# soc-copilot/enterprise/actions/servicenow.py
# ServiceNowIncidentAction — SOC domain implementation of EnterpriseAction protocol
# Status: STUB — full implementation in v6.0
# Shadow mode governs activation: 30-day shadow agreement review required before live

from dataclasses import dataclass
from typing import Optional

@dataclass
class ServiceNowIncidentAction:
    """
    Creates a ServiceNow incident from an escalated SOC decision.
    
    Implements EnterpriseAction protocol (ci-platform v6.0 §13.3).
    
    SAFETY INVARIANTS (non-negotiable):
      1. requires_human_approval = True. Always. Cannot be overridden without
         shadow mode agreement rate review.
      2. Shadow mode governs activation: customer must have completed 30-day shadow
         period and explicitly activated live mode before this action can execute.
      3. Idempotent: if ServiceNow incident already exists for this decision_id,
         do not create a duplicate (MERGE on external_correlation_id).
      4. Rollback always possible: incidents created by this action carry
         external_correlation_id = decision_id. Rollback closes the incident.
    
    S2P analog: ServiceNowPurchaseRequisitionAction (different endpoint, same protocol).
    """

    action_name: str = "create_servicenow_incident"
    domain: str = "soc"
    triggers_on: list[str] = field(default_factory=lambda: ["escalate"])
    requires_human_approval: bool = True   # NEVER change to False without shadow validation

    # Connection config (from env)
    servicenow_url: str = ""    # from SERVICENOW_URL env var
    servicenow_user: str = ""   # from SERVICENOW_USER env var
    servicenow_pass: str = ""   # from SERVICENOW_PASS env var

    def validate(self, decision: dict, context: dict) -> dict:
        """Validate inputs before any API call.
        
        Returns {"valid": bool, "errors": list[str], "proposed_payload": dict}
        """
        errors = []
        if not decision.get("action") == "escalate":
            errors.append(f"action must be 'escalate', got {decision.get('action')}")
        if not context.get("alert_id"):
            errors.append("alert_id required in context")
        if not context.get("analyst_id"):
            errors.append("analyst_id required — human approval is mandatory")

        payload = {
            "short_description": f"SOC Escalation: {context.get('alert_type', 'Unknown')}",
            "description": context.get("nl_explanation", "See SOC copilot for details."),
            "urgency": self._confidence_to_urgency(decision.get("confidence", 0)),
            "category": "Security",
            "subcategory": context.get("category", "unknown"),
            "correlation_id": decision.get("decision_id"),  # for idempotency
            "caller_id": context.get("analyst_id"),
        }

        return {"valid": len(errors) == 0, "errors": errors, "proposed_payload": payload}

    async def execute(self, decision: dict, context: dict, analyst_approved_by: str) -> dict:
        """Execute ServiceNow API call. Called ONLY after human approval.
        
        Returns {"success": bool, "external_id": str, "external_url": str}
        This stub raises NotImplementedError — v6.0 implementation fills this in.
        """
        raise NotImplementedError(
            "ServiceNowIncidentAction.execute() is a v6.0 implementation. "
            "This stub validates the EnterpriseAction protocol. "
            "See ci_platform_design_v5_1 §13.3 for the full EnterpriseAction spec."
        )

    async def rollback(self, external_id: str) -> dict:
        """Close the ServiceNow incident (rollback).
        
        Called when: operator decides the escalation was incorrect.
        """
        raise NotImplementedError("v6.0 implementation")

    def _confidence_to_urgency(self, confidence: float) -> int:
        """Map confidence to ServiceNow urgency (1=high, 2=medium, 3=low)."""
        if confidence >= 0.90: return 1
        if confidence >= 0.75: return 2
        return 3
```

---

## 26. Feature Gap Closure Map

This table maps every gap from product_strategy_v2 §5 (Gap Analysis by Layer) to the version and requirement that closes it.

| Gap ID | Description | Severity | Closes At | Requirement |
|---|---|---|---|---|
| **G-L1-1** | Alert type → category mapping incomplete — ~20% silent misclassification | BLOCKING | v5.5 | R6 (§14 `get_alert_category_mapping()`) |
| G-L1-2 | Bootstrap distribution is uniform — real SOC environments non-uniform | MED | v5.5 | Configurable bootstrap distribution in `get_calibration_profile()` |
| G-L1-3 | No centroid correction UI — must edit code | LOW | v6.0 | Centroid editor API / management endpoint |
| G-L1-4 | S2P not implemented — platform claim is theoretical | MED | v6.0 | v6.0-R4 S2P domain |
| **G-L2-1** | Learning invisible — Chart A shows W delta ≈ 0.0 (wrong metric) | HIGH IMPACT | v5.5 | R3 centroid drift chart |
| **G-L2-2** | No compounding proof metric — CISO cannot see improvement | HIGH IMPACT | v5.5 | R4 IKS (§22) |
| G-L2-3 | Bootstrap decisions not in convergence panel | MED | v5.5 | "1,200 bootstrap + N analyst decisions" display |
| G-L2-4 | σ synthesis bias not implemented | GATED | v5.5+ | Gated — GATE-M required |
| G-L3-1 | No category-specific threshold API | MED | v5.5 | R1 (`get_category_thresholds()`) |
| G-L3-2 | SynthesisProjector not implemented | GATED | Gated correctly | — |
| G-L3-3 | No cross-domain knowledge transfer | LOW | v6.5+ | EXP-D1 shows naïve transfer loses 2-14pp |
| **G-L4-1** | Factor node provenance not surfaced — analyst cannot see WHY | HIGH IMPACT | v5.5 | R2 `FactorComputerResult.provenance_nodes` |
| G-L4-2 | factor_vector stored as JSON string (fragile) | MED | v5.5 | Native Neo4j list |
| **G-L4-3** | No threat intelligence write-back — every alert re-queries | HIGH VALUE | v5.5 | R7 ThreatIndicator nodes |
| **G-L4-4** | CISA KEV not integrated | HIGH VALUE | v5.5 | R7 + CISAKEVConnector (already ✅ in v5.0) |
| G-L4-5 | Alert dependency graph not built | MED | v6.0 | Blast radius graph (v6.0-R2) |
| G-L4-6 | User context not enriched dynamically | MED | v6.0 | User enrichment connector |
| G-L5-1 | Loop 4 synthesis is PROPOSAL only | GATED | Correct — discipline must hold | — |
| G-L5-2 | Human review trigger is binary | MED | v5.5 | R11 graduated review tiers |
| G-L5-3 | No drift detection / alerting | MED | v5.5 | R12 drift bounds + alerts |
| **G-L5-4** | Auto-approve 11.5% — too low for analyst relief | CRITICAL | v5.5 | R1 category thresholds → 40% |
| **Offering-1** | Demo requires local setup — no hosted URL | HIGH | v5.5 | R9 Docker Compose |
| **Offering-2** | No proof-of-compounding surface | HIGH | v5.5/v6.0 | R4 IKS + R10 Tab 1 Graph Explorer (v5.5); Tab 5 exec learning narrative (v6.0) |
| **Offering-3** | Explainability requires sophistication | HIGH | v5.5 | R5 NL template engine (§23) |
| Offering-4 | Platform claim requires second domain | MED | v6.0 | S2P copilot (v6.0-R4) |
| Offering-5 | No regulatory compliance story | MED | v5.5/v6.0 | R13 evidence export; v6.0: full compliance package |

**Gap closure summary (v5.5):**
- All 5 HIGH IMPACT / CRITICAL gaps → closed at v5.5 (R1–R13)
- All GATED gaps → correctly gated; discipline holds
- All BLOCKING gaps → R6 closes G-L1-1 before first customer contract
- v6.0 gaps → scoped appropriately for first production customer phase

**April 5-6 session additions (v5.6) — post-MVP feature completions:**

| Item | Status | Notes |
|---|---|---|
| Block 2.3 Centroid export endpoint | ✅ DONE | GET /api/soc/centroid-export. 10-field schema, SHA-256. 5 tests. |
| Block 2.4 Centroid heat map + Noise Fingerprint | ✅ DONE | Factor weight per category×action. Tab 2 noise fingerprint demo-able. 5 tests. |
| Block 3.3 R2+R7 Neo4j wiring | ✅ DONE | sequence_count (R2) and cross_category_count (R7) wired. referral_debug in triage. 3 tests. Referral DR 72.7% live. |
| Block 3.5 Centroid drift visualization | ✅ DONE | Chart A now shows real drift from μ₀. G-L2-1 fully resolved. |
| Block 5.2 Enrichment degradation surface | ✅ DONE | Tab 2: source name + timestamp. Pulsedive/GreyNoise/CrowdStrike. 5 tests. |
| F9 Analyst Benchmarking Report | ✅ DONE | /api/soc/f9-report. Shadow data: AI vs analyst comparison. 4 tests. |
| Block 9.1–9.5 v6.5 features | ✅ DONE | Per-analyst η (CLAIM-66), spike detector (CLAIM-68), category freeze (CLAIM-69), spike cap (CLAIM-70), η rate cap (CLAIM-67 UNCONDITIONAL). |
| Block 1.1 Industry profile generator | ✅ DONE | 4 archetypes. Onboarding SLA: Day 1 evening → Day 2 morning at 90.6% accuracy. |
| Tab content Tier 1+2 tests (54 tests) | ✅ DONE | Category validation, Microsoft gate, DiagonalKernel name, jargon-free flywheel, CLAIM-OLS-01, cross-tab count consistency. |
| BACKLOG-020 IKS reset fix | ✅ DONE | E2E test reset centroid tensor. Snapshot/restore fixture. IKS stable 76.8+ after full E2E run. Regression test added. |

---

## 27. Experiment Landscape

### 27.1 Completed — Key Results by Series (~295 experiments total)

See `experiment_reference_catalog_v2.md` for full catalog. Authoritative experiment queue: MAP v5.17.

**Original foundation series (representative):**

| Experiment | Result | Key Number |
|---|---|---|
| EXP-5 (oracle) | PASS | 79.65% |
| EXP-A (gating) | G FALSIFIED | 49.27% |
| EXP-C1 (centroid oracle) | PASS | **97.89%** zero-learning |
| EXP-B1 (profile scoring) | PASS | **98.2%** with learning |
| EXP-D1 (cross-category) | Marginal | Config wins 2-14pp |
| EXP-D2 (interactions) | None significant | 75 pairs tested |
| EXP-E1 (kernels) | L2 wins 2/3 | Pluggable |
| EXP-E2 (scale) | PASS | 99.9% at 20×10×20 |
| V1A–V3B (validation suite) | All confirmed | b=2.11, τ=0.1, ECE=0.036 |
| OP1-FINAL, OP2 (synthesis) | GATE-OP PASSED | delta=+0.0041, p=0.0008 at λ=0.5 |
| Realistic 50-seed suite | COMPLETE | **71.7% static, 78.9% at dec 1,000** |

### 27.2 Selected Planned Items (substantially superseded — see MAP v5.51 for authoritative queue)

Key remaining planned experiments:
- **[RETIRED] Batch F META-4**: LLM simulation cannot measure threshold-crossing γ. Structural
  incompatibility confirmed (LLM prior dominance, 13 notebook versions). RETIRED April 7, 2026.
- **γ Theorem ✅ ESTABLISHED (April 8, 2026)**: γ > 1 proven analytically (4 LLMs, independent).
  Theorem: γ > 1 ⇔ ε_firm > α_cat · ‖Δ‖ · θ / (θ − (1−α_cat)) ≈ 0.128. All real deployments clear this.
  CC-21 → Tier 2. Simulation track CLOSED. See math_synopsis_v13.md §3.2, claims_registry_v10 §B.5.
- **EXP-G1** (pilot Day 1+ data): Measured γ from production. BACKLOG-015 ACTIVE from pilot Day 1.
  Original 8 fields ✅ DONE. 3 additional fields added April 8 (see below). CC-21 → Tier 1 gate.

**BACKLOG-015 Field Specification (complete — must all be active from pilot Day 1):**

*Original 8 fields (active ✅):*
```python
{
    "re_convergence_event_id": str,           # UUID
    "convergence_start_decisions": int,        # decisions at trigger
    "convergence_end_decisions": int,          # decisions at 85% accuracy re-achieved
    "n_reconverge": int,                       # end - start
    "graph_entity_count_at_start": int,        # W1 entity count at trigger
    "sigma_squared_per_factor_at_start": dict, # {factor: σ²} at trigger
    "trigger_type": str,                       # "threat_landscape_shift" | "new_category" | "reorganization"
    "domain": str,                             # alert category
}
```

*3 additional fields (April 8, 2026 — CRITICAL, must add before pilot Day 1):*
```python
# Per verified decision (not per re-convergence event):
{
    "centroid_distance_to_canonical": float,   # np.linalg.norm(mu - CANONICAL_CENTROID)
    "pattern_history_value": float,            # PatternHistory factor value at decision time
    "alert_category_distribution": dict,       # rolling 100-decision category mix
}
```

Why these 3 fields are critical:
- `centroid_distance_to_canonical`: model-independent convergence signal. Simulation proved
  N_half (rolling accuracy) is too noisy for 3-seed estimation; centroid distance is the
  reliable metric. EXP-G1 measures γ as centroid distance convergence rate ratio (not N_half
  ratio). Decreases monotonically under production learning dynamics.
- `pattern_history_value`: tracks W2 enrichment adaptation — Phase 2 starts enriched, Phase 1
  built enrichment gradually (temporal asymmetry is load-bearing for the γ theorem).
- `alert_category_distribution`: detects vector distribution shift during disruption — the
  third structural challenge the centroid-only theorem does not model.

Log `centroid_distance_to_canonical` per call to `POST /api/soc/triage` that produces a
verified decision. Write to Neo4j as `DecisionDistanceLog`. One line in the logging path.

- **V-MV-RISK, V-MV-CONSERVATION**: R score and Var(q) gating on existing factorial data.

### 27.3 FX Series Status

FX-1 (real SOC data): SVM-005 ✅ COMPLETE. KL=6.5–8.2 (CISA KEV survival bias noted). asset_criticality real mean=0.85.
FX-2 through FX-8: SUPERSEDED — replaced by SVM methodology (LLM-as-judge, synthetic personas, SANS calibration).

### 27.4 OP Series Summary (GATE-OP PASSED)

- GATE-OP: delta=+0.0041, p=0.0008 at λ=0.5. Operative window: λ∈[0.5, 0.6].
- OP2 finding: 35% of centroids damaged by harmful σ never recover within 400 decisions post-TTL. Checkpoint is the only repair path → TD-033 HIGH priority.
- T_recovery paradox: longer TTL delays recovery start. Short TTL + checkpoint is the correct design.
- τ_modifier: REJECTED — τ recalibration on live data required before production (TD-034).
- Update() firewall: σ NEVER flows into update(). Permanent constraint.

---

## Appendix A: Version History

| Version | Date | Changes |
|---|---|---|
| **v5.7** | **April 8, 2026** | **Block 7.1 Sentinel write-back ✅ DONE (+5 tests, fire-and-forget, action→classification enum, 3× backoff). BACKLOG-008 dry-run ✅ verified (live run before Block 8.2). Test counts: 900 SOC backend (was 532), 183 E2E confirmed. γ theorem established analytically — γ > 1 ⇔ ε_firm > 0.128 (4 LLMs independent). CC-21 → Tier 2. Simulation track CLOSED. §27.2 updated: Batch F RETIRED, EXP-G1 active, BACKLOG-015 extended (3 new fields). Authority: claims_registry_v10.0 · MAP v5.51. |
| v1.0–v3.0 | Feb 28–Mar 1, 2026 | Three-repo restructure, GAE rewire, v5.0 redesign |
| v4.0 | Mar 3, 2026 | v4.5 TAGGED. Phase A+B+HC-1 complete. Phase C → experiments. H7, F1–F10. |
| v5.0 | Mar 4, 2026 | Architecture SETTLED. ProfileScorer replaces ScoringMatrix. 29 prompts. |
| v5.1 | Mar 7, 2026 | OP series (24 experiments). GATE-OP PASSED. Tab 5 PROPOSAL. C=5 canonical. TD-033/034. |
| v5.2 | Mar 7, 2026 | Architecture Philosophy (four bridge components). GraphAttentionBridge scope boundary. Data hooks formal contract. ProfileSnapshot spec. get_graph_schema() stub. TD-035. |
| **v5.3** | **Mar 10, 2026** | **Product strategy integration (§1.5). S2P co-design constraints (§1.6). v5.5 scope fully specified (§10.6, R1–R13). Product flows for v5.5 and v6.0 (§11.5/11.6). SOCDomainConfig updated: shape (5,5,6), 7 new methods. Shadow Mode full spec (§21). IKS full spec (§22). NL Template Engine 24 templates (§23). SemanticRegistry: concepts.yaml 20 concepts (§24.1). QueryCatalog: queries.yaml 15 queries (§24.2). Enterprise Integration Hooks: CMDB, Identity profiles, ServiceNow stub (§25). Feature Gap Closure Map (§26). Appendix B: TD-036–TD-039 added.** |
| **v5.4** | **Mar 10, 2026** | **Design gap closure: §23.4 Similar Past Cases query spec (cosine similarity, 5 params, Neo4j GDS query, agreement pct formula). §23.5 NL Template Judge Rubric (4 criteria, pass thresholds, LLM prompt fragment). §6.4 rollback semantics cross-ref corrected (§17.5 flagged as not yet written, ARCH-3 blocked). §10.6-R11 PROD-4 derivation note (0.70 confidence floor is an estimate, not calibration-derived). §10.6-R13 N3 EU AI Act Article 9 disclosure (endogenous loop, MEDIUM residual risk, shadow mode mitigation). TD-035 GATE-R sequencing constraint (must run after v5.5-R6). §10.3 accuracy corrected 94.78% → 97.89% (EXP-C1). §2 directory + §13 rules updated: similar_cases.py, test_similar_cases.py, nl_template_judge_results.json, SimilarCasesService import and call-order rules.** |
| **v5.4-final** | **Mar 11, 2026** | **Sprint-unblocking deliverables: §17.5 rollback execution semantics (authoritative — rollback-and-resume mode, three trigger conditions, Hook 2/3 interaction during rolled-back period, ARCH-3 prerequisite). §23.5 LLM judge rubric (authoritative — four criteria, pass thresholds, LLM prompt fragment for criterion 1, when-to-run, output storage location). §23.4 similar past cases spec (augmented — cosine similarity rationale, five parameters with derivation status, Neo4j GDS query with Python fallback, agreement pct suppression logic).** |
| **v5.5** | **Mar 12, 2026** | **v5.0 TAGGED complete. Post-tag WIRING-1: CentroidUpdate wiring (centroid_delta_norm in triage endpoint, Tab-3 centroid delta display), freeze/unfreeze on ProfileScorer. Test count 243→246. Header updated (version, date, status). §1.1 test count updated. §1.4 architecture philosophy reference corrected (architecture_philosophy_v1_3.md outputs); Two Levels of Institutional Judgment subsection added (Decision Intelligence / Deployment Intelligence framing, separation constraint). §4.3 sprint table all phases → COMPLETE; post-tag note; v5.5 first-action sequence. Appendix B: TD-027, TD-032, TD-036, TD-039 CLOSED (all v5.0 targets shipped). Companion repo catalog updated: experiments_catalog_v8.** |
| **v5.5.1** | **Mar 21, 2026** | **Kernel architecture + A=4 migration + P0 fix.** Header: GAE 246→447, SOC 78→252, ci-platform 0→73. §4.4 tensor (6,4,6)=144, A=4 canonical (escalate/investigate/suppress/monitor), refer_to_analyst removed from centroid tensor, static accuracy 80.6→90.6%. §10.3/§10.6 v5.5 Tier 1/2/3 items marked SHIPPED. §14 SOCDomainConfig: kernel_type, eta_confirm, eta_override, auto_pause_on_amber, learning_enabled added. §22.3 IKS service corrected (module-level functions, κ*=0.20). §22.5 endpoints added (centroid-evolution, learning-state, frozen-roi). Kernel integration: DiagonalKernel default noise_ratio>1.5, KernelSelector, factor quarantine mask DEPRECATED. |
| **v5.5.2** | **Mar 21, 2026** | **Referral routing architecture.** Header: GAE 447→478, SOC 252→280, experiments ~100→~104. §13 Claude Code rules: referral never modifies scoring, confidence gate is action routing only. §14 SOCDomainConfig: get_referral_rules() added. §22.6 NEW: Referral Routing Architecture — ReferralRules R1-R7, triage VETO wiring, three-phase architecture. Validated: EXP-REFER-LAYERED 72.7% DR / 12% FPR. Confidence gate REJECTED for referral (14% precision). §11.5 updated: referral VETO in triage flow. Appendix B: TD-034 status noted (TD-034 v2 wired in Phase 1), TD-035 CLOSED (GATE-R: 100% routing accuracy), TD-037 CLOSED (R6 shipped — alert category mapping complete), TD-038 CLOSED (R2 shipped — FactorComputerResult with provenance). |
| **v5.6** | **Apr 6, 2026** | **April 5-6 coding session.** Header: GAE 517→527, SOC 288→900 backend + 183 E2E, ci-platform 93→102, ~130→~295 experiments. Phase 2 ✅ Phase 3 Priority 1 ✅. §4.4: CLAIM-59/62/64/CL-ECON-MEASURED added. §26: April 5-6 completions table (Block 2.3/2.4/3.3/3.5/5.2, F9, Block 9.1-9.5, Block 1.1, tab content tests, BACKLOG-020). §27: experiment landscape updated. Appendix B: BACKLOG-003/004/007/009/020 resolved. Footer updated. |
| **v5.5.3** | **Mar 25, 2026** | **Phase 1 closure: W2 flywheel + monitoring architecture + ACCP framing.** Header: GAE 478→517, SOC 280→288, ci-platform 73→93, experiments ~104→~130. Phase 0 ✅ Phase 1 ✅. §1.4: architecture_philosophy_v1_3.md → v4.1.md; ACCP bounded hyperagent framing (Loop 1=task agent, Loop 2=meta agent, Loop 3=governance boundary); three write sources (W1/W2/W3); three Phase 3 design gaps (H1/H2/H3). §5.1 factor summary: two PatternHistory read paths documented. §5.6 NEW: PatternHistoryFactorComputer (W2 read path) — TRIGGERED_EVOLUTION edges, recency-weighted, FACTOR_INDEX=4, FALLBACK=0.40 (CLAIM-W2: +10.13pp, p=0.0002). §13 rules: W2 read path invariants. §14 get_factor_computers() updated to PatternHistoryFactorComputer. §22.3: IKS anchor separation (standard μ₀=anchor never overwritten, enriched μ₀=live start, two distinct artifacts). §22.7 NEW: Three-Signal Monitoring Architecture — Circuit Breaker (existing) + Flywheel Health Monitor (CLAIM-OLS-01: 0% miss, p90≥50d) + Analyst Contribution Monitor (production milestone). Nomenclature: Level 1/2/3 → Circuit Breaker / Flywheel Health Monitor / Analyst Contribution Monitor. Var(q) gating: PERMANENT HARD STOP (Bernoulli mixture theorem). |

---

## Appendix B: Technical Debt Status

| ID | Description | Status | Version |
|---|---|---|---|
| TD-014 | TimeAnomaly reads properties (not relationships) | LOW | v5.5 |
| TD-015 | DeviceTrust reads properties | LOW | v5.5 |
| TD-017 | Hardening state not fully persisted | HIGH | v5.0 |
| TD-018 | Dual persistence paths | MED | v5.0 |
| TD-019 | Dual decision paths | **✅ CLOSED** v4.5 TAB2-1 | — |
| TD-020 | execute_action without events | **✅ CLOSED** v4.5 TAB2-2 | — |
| TD-023 | Backward-compat block | LOW | v5.5 |
| TD-024 | Two LearningState classes | LOW | v5.0 |
| TD-025 | No CalibrationProfile | **✅ CLOSED** v4.5 GAE-CAL-1 | — |
| TD-026 | Audit/GAE sync on reset | **✅ CLOSED** v4.5 SIM-FIX | — |
| ~~TD-027~~ | ~~ScoringMatrix → ProfileScorer RESET. Reset μ from DomainConfig — no W→μ mapping.~~ | **✅ CLOSED v5.0 SOC-PROF-1** | — |
| ~~TD-028~~ | ~~Eq. 4 dot product in math blog~~ | **✅ CLOSED** cross_graph_attention_v3 | — |
| **TD-029** | **Deprecated ScoringMatrix — remove `get_initial_W()` stub** | **Open (LOW)** | **v5.5** |
| ~~TD-030~~ | ~~τ default 0.25→0.1 in production code~~ | **✅ CLOSED** v5.0 SOC-PROF-1 | — |
| **TD-031** | **LayerNorm in Tier 5 enrichment (V1B: 2.9M× scale improvement)** | **Open (MED)** | **v5.5** |
| ~~TD-032~~ | ~~OracleProvider protocol (from retired bridge_layer)~~ | **✅ CLOSED v5.0 GAE-ORACLE-1** | — |
| **TD-033** | **Centroid checkpoint/rollback (Loop 4 prerequisite). EXP-OP2: 35% never-recover post-TTL. checkpoint() + rollback() in ProfileScorer. Every 50 decisions.** | **Open (HIGH)** | **v5.5 (prerequisite before v6.0 Tab 5 launch)** |
| ~~TD-034~~ | ~~τ recalibration gate before Loop 2 activates in production.~~ | **✅ CLOSED Phase 1 — TD-034 v2 shipped.** Auto-trigger wired to P28 Phase 3: σ_mean>0.12 OR noise_ratio>2.0×. τ=0.10 validated as default; sweep [0.08,0.18] ECE gate ≤0.05 for non-centroidal deployments. ci-platform v1.0 174 tests. | — |
| ~~TD-035~~ | ~~GATE-R routing accuracy. SituationAnalyzer routing must be measured.~~ | **✅ CLOSED v5.5 — GATE-R: 100% routing accuracy.** Run after v5.5-R6 shipped (complete alert_type→category mapping). Composite accuracy multiplier confirmed: routing_accuracy=1.0 × 0.9789 = 0.9789. | — |
| ~~TD-036~~ | ~~EvaluationReport.by_technique → by_category. S2P co-design fix.~~ | **✅ CLOSED v5.0 GAE-EVAL** | — |
| ~~TD-037~~ | ~~Alert category mapping table incomplete (~30 entries, needs ~200+). G-L1-1 BLOCKING: ~20% of alerts silently misclassified.~~ | **✅ CLOSED v5.5-R6.** Full mapping table in get_alert_category_mapping() (§14). Every unrecognized alert_type → ERROR log. Never silent default. | — |
| ~~TD-038~~ | ~~FactorComputerResult does not yet include provenance_nodes. v5.0 returns float only.~~ | **✅ CLOSED v5.5-R2.** FactorComputerResult dataclass with value + provenance_nodes. All 6 FactorComputers return FactorComputerResult. ProvenanceNode spec in §10.6-R2. | — |
| ~~TD-039~~ | ~~ProfileScorer shape (5,5,6) not yet in production code.~~ | **✅ CLOSED v5.0 SOC-PROF-1** | — |
| ~~BACKLOG-003~~ | ~~Noise Map shows "needs 10+ decisions" despite 2,000 decisions — wrong property name in query~~ | **✅ CLOSED v5.6 (April 6, 2026)** | — |
| ~~BACKLOG-004~~ | ~~IKS undersells actual learning (shows 75.7, expected ~87) — wrong property name~~ | **✅ CLOSED v5.6 (April 6, 2026)** | — |
| ~~BACKLOG-007~~ | ~~"8 of 6 categories calibrated" — unknown counted as 7th~~ | **✅ CLOSED v5.6 (April 6, 2026)** | — |
| ~~BACKLOG-009~~ | ~~Tab 1 reads a.type (Sentinel string) instead of a.category~~ | **✅ CLOSED v5.6 (Fix 1.1)** | — |
| ~~BACKLOG-020~~ | ~~IKS resets to 2.5 after E2E test — test reset centroid tensor via reset endpoint~~ | **✅ CLOSED v5.6 (April 6, 2026)** — snapshot/restore fixture, IKS stable 76.8+ | — |

---

## Appendix C: Superseded Documents

| Old Document | Status | Content Destination |
|---|---|---|
| `v4_design_document_v7.md` | Superseded | → soc_copilot_design v4, then v5 |
| `v4_5_design_v8.md` | Superseded | → soc_copilot_design v4, then v5 |
| `soc_copilot_design_v1.md` | Superseded | Absorbed into v3, carried forward |
| `soc_copilot_design_v2.md` | Superseded | Absorbed into v3, carried forward |
| `soc_copilot_design_v3.md` | Superseded | Absorbed into v4, carried forward |
| `soc_copilot_design_v4.md` | Superseded | Updated to v5 series |
| `soc_copilot_design_v5.0.md` | Superseded | → v5.1 → v5.2 → this document |
| `soc_copilot_design_v5_1.md` | Superseded | → v5.2 → this document |
| `soc_copilot_design_v5_2.md` | **Superseded by this document** | All content preserved and extended here |
| `bridge_layer_design_v1.md` | RETIRED | 95% experimentally falsified. OracleProvider → TD-032. |
| `product_requirements_gap_analysis_v1.md` | Superseded | → product_strategy_v2 |
| `competitive_gap_analysis_v1.md` | Superseded | → product_strategy_v2 |

---

*SOC Copilot — Design Document v5.6 | April 6, 2026*
*Four-repo stack: GAE (math, 995 tests) → ci-platform (infra, 174 tests) → soc-copilot (domain, 900 backend + 183 E2E) → cross-graph-experiments (~295 experiments)*
*Phase 0 ✅ Phase 1 ✅ Phase 2 ✅ Phase 3 Priority 1 ✅. Loom demo v1 unblocked.*
*DiagonalKernel validated (+13pp SOC, +7pp S2P). ReferralRules validated (72.7% DR, 12% FPR).*
*W2 flywheel: CLAIM-W2 +10.13pp. Third compounding pathway: CLAIM-59 54.4% faster (p<0.0001). Enrichment: CLAIM-62 +42.69pp. Fisher info: CLAIM-64 r=0.9669.*
*Flywheel Health Monitor: CLAIM-OLS-01 0% miss rate, p90≥50d lead time.*
*Switching cost: CLAIM-SC-01 537 decisions = full quarter. Convergence calendar: CLAIM-CONV-01 MAE=1.55d.*
*Scoring: Eq. 4-final. DiagonalKernel (default for noise_ratio>1.5) or L2. τ=0.1. C=6, A=4, d=6. Tensor (6,4,6)=144.*
*A=4: escalate, investigate, suppress, monitor. refer_to_analyst via REFERRAL RULES R1-R7 (not confidence gate).*
*Referral is a VETO — independent of scoring. Confidence gate is action routing only.*
*Three referral phases: Rules (v6.0, Day 1) → OverrideDetector (v6.5, ≥50 positives) → Monthly retrain (v7.0).*
*Asymmetric η: η_confirm=0.05, η_override=0.01 (P0 fix). AMBER auto-pause. LEARNING_ENABLED=False default.*
*Monitoring: Circuit Breaker + Flywheel Health Monitor (validated) + Analyst Contribution Monitor (production milestone).*
*Var(q) pooled binary: PERMANENT HARD STOP (Bernoulli mixture theorem). Logged metric only.*
*IKS anchor separation: standard μ₀=anchor (never overwritten), enriched μ₀=live start (two distinct artifacts).*
*ACCP bounded hyperagent: Loop 1=task agent, Loop 2=meta agent, Loop 3=fixed governance boundary.*
*Three write sources: W1 (decisions), W2 (TRIGGERED_EVOLUTION, CLAIM-W2), W3 (cross-graph enrichment).*
*raw_weights (true 1/σ²) for η_eff. weights (pre-normalized) for scoring. GAE 0.7.20 required for CLAIM-64.*
*"The distance metric itself compounds. The referral rules encode policy. The W2 flywheel is real. The graph compounds while centroids wait. Recovery is not a coincidence — it is institutional memory, quantified."*
# SOC Copilot — Design Document v5.7 (Part 2 of 3)

**Covers:** §§15–20 (Simulation Mode, NarrativeProvider, Reset Semantics, ATT&CK Integration,
Category Learning Curve, v4.5 Prompt Specifications) and §§28–30 (Response Data Realism,
Phase C Resolution, Feature Gaps F1–F15).

**Numbering note (v5.3):** §§21–27 now live in Part 1 (Shadow Mode, IKS, NL Template Engine,
SemanticRegistry, Enterprise Hooks, Feature Gap Closure Map, Experiment Landscape).
The v5.2 §§21–23 content is renumbered here as §§28–30 to avoid collision.

**Status (v5.6 — April 6, 2026):** v5.5 COMPLETE. Phase 0 ✅ Phase 1 ✅ Phase 2 ✅ Phase 3 Priority 1 ✅.
995 GAE tests. 900 SOC backend + 183 E2E tests confirmed. 174 ci-platform tests. ~295 experiments complete.
**Authority:** claims_registry_v10.0 · MAP v5.51

Changes from v5.6 → v5.7 (April 8, 2026): Header/footer updated (552 backend, MAP v5.51). §29.7 NEW. γ theorem ✅ CC-21 Tier 2. Block 7.1 ✅ DONE. BACKLOG-015 extended.

Changes from v5.5.3 → v5.6 (April 6, 2026): Header/footer updated (527/532/102, ~295 experiments, Phase 3 Priority 1 ✅). §29.6 item 9 added: April 5-6 session findings (CLAIM-59/62/64/CL-ECON-MEASURED). §30.2 F9 updated (✅ DONE, shipped April 6). §30.4 version placement updated (F9 → v5.6).

Changes from v5.5.2 → v5.5.3: Header/footer updated (517/288/93, ~130 experiments, Phase 0/1 complete).
§29.5 updated: TD-035 CLOSED (GATE-R: 100% routing accuracy). §29.5 synthetic data framing
rewritten: FX-1 is distribution coverage completion (SVM methodology), not a "real data"
validation prerequisite. Centroid calibration reframed: SVM-005 (web-scraped distributions)
is the calibration reference — no real customer data required. §29.6 item 8 added: Phase 1
experiment findings (W2 flywheel CLAIM-W2, Flywheel Health Monitor CLAIM-OLS-01, switching cost
CLAIM-SC-01, convergence calendar CLAIM-CONV-01, poisoning two-tier claims, Var(q) permanent
hard stop). §30.2 F3 EU AI Act status updated (0A-5 epistemic fields shipped).

Changes from v5.5.1 → v5.5.2: §29.6 referral architecture finding added (item 7).
Header/footer updated with 478/280 test counts.

Changes from v5.4-final → v5.5: title/status updated; §17.5.6 stray v5.4-draft fragment
(IKS-drop trigger condition) removed — the authoritative trigger conditions are the three
defined in §17.5.1 (P_max collapse, centroid drift, manual); §18.4 TD-036 reference updated
(CLOSED in v5.0); §30.2 column header updated to "v5.5 Status" and F2/F4 status updated
to reflect v5.0 completion; footer updated.

**v5.4-final note (March 11, 2026):** §17.5 Rollback Execution Specification (TD-033)
was added as the authoritative rollback spec. It corrected three errors in the v5.4-draft:
triggers are P_max-based + drift-based + manual (not IKS-drop); resume is manual-only;
Hook 2 is suspended during frozen window (not retroactively cleared). All other content
in this part was preserved from v5.3 with no substantive changes.

---

## 15. Simulation Mode

### 15.1 Design

Simulation mode runs N decisions through the identical GAE pipeline that manual triage uses. No shortcuts. No parallel scoring path. The only difference: outcomes are generated by a Bernoulli oracle instead of a human analyst.

**Why Bernoulli:** It proves the learning mechanism works without introducing confirmation bias (A1). The oracle is independent of the system's recommendation. This is honest: "Simulation mode demonstrates the learning mechanism. Accuracy numbers reflect the synthetic oracle, not real-world triage quality."

### 15.2 SimulationOrchestrator

```python
# backend/app/services/simulation.py

class SimulationOrchestrator:
    """Batch decision processing using the same GAE pipeline as manual triage.
    
    CRITICAL: Reuses EXACT same code path as triage.py:
      compute_factor_vector → score_entity → write_decision → update_learning
    Do NOT create a parallel scoring path. TD-019 taught us this lesson.
    """
    
    def __init__(self, alert_pool, neo4j_service, factor_computers, 
                 learning_state, domain_config, profile_scorer=None):
        self.alert_pool = alert_pool
        self.neo4j = neo4j_service
        self.computers = factor_computers
        self.learning_state = learning_state
        self.domain_config = domain_config
        self.profile_scorer = profile_scorer  # v5.0: ProfileScorer instance
        self.progress = {"running": False, "current": 0, "total": 0, 
                        "history": [], "by_category": {}}
        self.stop_flag = False
    
    async def run(self, n_decisions: int, correctness_rate: float = 0.8,
                  speed_ms: int = 100):
        """Run N decisions through GAE pipeline.
        
        Args:
            n_decisions:    How many decisions to simulate (1–200)
            correctness_rate: Bernoulli parameter for oracle (default 0.8)
            speed_ms:       Delay between decisions in ms (for UI update visibility)
        """
        # Atomic reset before simulation (clean learning progression)
        await self._reset_learning_state()
        
        self.progress = {
            "running": True, "current": 0, "total": n_decisions,
            "history": [], "by_category": {},
            "correctness_rate": correctness_rate,
        }
        self.stop_flag = False
        
        for i in range(n_decisions):
            if self.stop_flag:
                break
            
            # Pick alert (cycle through pool)
            alert = self.alert_pool[i % len(self.alert_pool)]
            alert_id = alert["id"]
            category = alert.get("situation_type", "unknown")
            
            # === SAME PIPELINE AS triage.py ===
            # Connector 1: Factor computation
            f, metadata = await compute_factor_vector(alert, self.computers, self.neo4j)
            
            # Connector 2: Scoring (v5.0: ProfileScorer with L2 distance)
            profile = self.domain_config.get_calibration_profile()
            if self.profile_scorer:
                # v5.0: Eq. 4-final — L2 distance to profile centroids
                result = self.profile_scorer.score(f, category=category)
            else:
                # v4.5 fallback: Eq. 4 — dot product with W
                result = score_entity(f, self.learning_state.W,
                                      self.domain_config.get_actions(),
                                      tau=profile.temperature)
            
            # Channel A: Decision write-back
            decision_id = await write_decision_to_graph(alert_id, result, f, self.neo4j)
            
            # Bernoulli oracle (independent of system recommendation)
            correct = random.random() < correctness_rate
            outcome = +1 if correct else -1
            
            # Connector 3: Learning update
            if self.profile_scorer:
                # v5.0: Centroid pull/push (Eq. 4b-final), clipped to [0,1]
                self.profile_scorer.update(
                    f=f, category=category,
                    action_index=result.selected_action_index,
                    outcome=outcome,
                )
            else:
                # v4.5 fallback: W update with 20:1 asymmetry
                update = self.learning_state.update(
                    action_index=result.selected_action_index,
                    action_name=result.selected_action,
                    outcome=outcome,
                    f=f,
                    confidence_at_decision=result.confidence,
                )
            save_learning_state(self.learning_state)
            
            # Channel B: Outcome write-back
            await mark_decision_outcome(decision_id, outcome, self.neo4j)
            # === END SAME PIPELINE ===
            
            # Track per-category accuracy
            if category not in self.progress["by_category"]:
                self.progress["by_category"][category] = {"correct": 0, "total": 0}
            self.progress["by_category"][category]["total"] += 1
            if correct:
                self.progress["by_category"][category]["correct"] += 1
            
            # Record
            self.progress["current"] = i + 1
            self.progress["history"].append({
                "decision_number": i + 1,
                "alert_id": alert_id,
                "category": category,
                "action": result.selected_action,
                "confidence": float(result.confidence),
                "correct": correct,
                "centroid_norm": float(np.linalg.norm(
                    self.profile_scorer.centroids if self.profile_scorer 
                    else self.learning_state.W
                )),
            })
            
            if speed_ms > 0:
                await asyncio.sleep(speed_ms / 1000.0)
        
        self.progress["running"] = False
        self.progress["summary"] = self._compute_summary()
    
    def _compute_summary(self) -> dict:
        """Generate summary after simulation."""
        history = self.progress["history"]
        total = len(history)
        correct = sum(1 for h in history if h["correct"])
        
        # Accuracy over time (sliding window)
        window = 10
        accuracy_curve = []
        for i in range(window, total + 1):
            window_correct = sum(1 for h in history[i-window:i] if h["correct"])
            accuracy_curve.append(window_correct / window)
        
        return {
            "total_decisions": total,
            "overall_accuracy": correct / total if total > 0 else 0,
            "accuracy_curve": accuracy_curve,
            "by_category": self.progress["by_category"],
            "final_centroid_norm": history[-1]["centroid_norm"] if history else 0,
        }
```

### 15.3 API Endpoints

```python
# backend/app/routers/simulation.py

POST /api/simulation/run
  Body: {"n_decisions": int, "correctness_rate": float, "speed_ms": int}
  Validation: 1 ≤ n ≤ 200, 0.0 ≤ rate ≤ 1.0, 0 ≤ speed_ms ≤ 2000
  Returns: {"started": true, "n_decisions": N}
  Notes: Runs in background (asyncio.create_task). Only one simulation at a time.

GET /api/simulation/status
  Returns: {
    "running": bool, "current": int, "total": int,
    "history": [...], "by_category": {...},
    "summary": {...}  (only when complete)
  }

POST /api/simulation/stop
  Returns: {"stopped": true, "completed": int}
```

### 15.4 Alert Pool (Phase A — SIM-3a/3b)

Five categories, 15–20 alerts total:

| Category | ATT&CK Technique | Count | Dominant Factors | Example |
|---|---|---|---|---|
| Travel/VPN Anomaly | T1078 (Valid Accounts) | 4 | travel_match, device_trust | Singapore login, known traveler |
| Credential/Access | T1078.004, T1110 | 3 | pattern_history, time_anomaly | After-hours credential stuffing |
| Threat Intel Match | T1566.001 (Phishing) | 3 | threat_intel, asset_criticality | Spear-phishing target matches active campaign |
| Insider/Behavioral | T1567 (Exfiltration) | 3 | pattern_history, asset_criticality | Unusual data access pattern |
| Cloud/Infrastructure | T1048 (Exfiltration over Alt Protocol) | 3 | device_trust, threat_intel | Cloud storage upload from unknown device |

Each category activates different dominant factors → the learning curve diverges per category → visible proof of institutional judgment.

---

## 16. NarrativeProvider

### 16.1 Design

Local-first, protocol-based. The product runs fully self-contained without external API dependencies.

> **v5.3 distinction:** NarrativeProvider (this section) handles per-alert investigation prose
> (3–5 sentences, LLM-generated, probabilistic). The NLTemplateEngine (§23 in Part 1) handles
> structured explainability across three customer layers (deterministic, no LLM). Both are
> needed and serve different audiences. Do not conflate them.

### 16.2 Interface

```python
# backend/app/services/narrative.py

from typing import Protocol
from dataclasses import dataclass

@dataclass
class NarrativeContext:
    """Structured input for narrative generation.
    
    All fields computed by GAE pipeline — the LLM is just
    the rendering layer. The intelligence is in the graph.
    """
    alert_id: str
    alert_type: str
    technique_id: str | None        # "T1078"
    technique_name: str | None      # "Valid Accounts"
    factors: dict[str, float]       # {"travel_match": 0.82, ...}
    dominant_factors: list[str]     # ["travel_match", "device_trust"]
    action: str                     # "suppress"
    confidence: float               # 0.91
    calibration_count: int          # How many prior outcomes inform this decision
    weight_changes: dict | None     # What changed since last similar alert
    user_context: dict | None       # User profile summary (from graph)
    asset_context: dict | None      # Asset details (from graph)

class NarrativeProvider(Protocol):
    """Protocol for investigation narrative generation."""
    async def generate(self, context: NarrativeContext) -> str: ...

class TemplateNarrativeProvider:
    """Zero-dependency fallback. Always available.
    Produces correct but mechanical narratives."""
    
    async def generate(self, context: NarrativeContext) -> str:
        technique_str = f" ({context.technique_id})" if context.technique_id else ""
        dominant = " and ".join(context.dominant_factors[:2])
        
        return (
            f"Alert {context.alert_id}: {context.alert_type}{technique_str}. "
            f"Dominant factors: {dominant}. "
            f"Recommendation: {context.action} at {context.confidence:.0%} confidence. "
            f"Calibrated from {context.calibration_count} verified outcomes."
        )

class OllamaNarrativeProvider:
    """Local LLM via Ollama. Default for production.
    No API key. No network dependency. Near-zero cost."""
    
    def __init__(self, model: str = "qwen2.5:7b",
                 base_url: str = "http://localhost:11434",
                 prompt_template: str | None = None):
        self.model = model
        self.base_url = base_url
        self.template = prompt_template or self._default_template()
    
    async def generate(self, context: NarrativeContext) -> str:
        prompt = self.template.format(**self._context_to_dict(context))
        try:
            response = await self._call_ollama(prompt)
            return response
        except Exception:
            # Graceful degradation to template
            fallback = TemplateNarrativeProvider()
            return await fallback.generate(context)
    
    def _default_template(self) -> str:
        return """You are a security operations analyst writing an investigation summary.

Alert: {alert_id} ({alert_type}, {technique_id})
Factors: {factors_formatted}
Dominant: {dominant_factors}
Recommendation: {action} at {confidence:.0%} confidence
Prior outcomes: {calibration_count} verified decisions on similar alerts

Write a 3-5 sentence investigation narrative. Be specific about the factors.
End with: "Calibrated from {calibration_count} verified outcomes."
"""

class GeminiNarrativeProvider:
    """Optional. Requires GEMINI_API_KEY in environment."""
    # ... existing Gemini integration, wrapped in NarrativeProvider protocol

class AnthropicNarrativeProvider:
    """Optional. Requires ANTHROPIC_API_KEY in environment."""
    # ... Claude API wrapper
```

### 16.3 Configuration

```bash
# .env
NARRATIVE_PROVIDER=ollama               # or: template, gemini, anthropic
NARRATIVE_MODEL=qwen2.5:7b              # model within provider
NARRATIVE_PROVIDER_SIMULATION=template  # skip LLM during batch runs
```

### 16.4 Graceful Degradation

```
If NARRATIVE_PROVIDER=ollama and Ollama not running:
  → Fall back to TemplateNarrativeProvider
  → Log warning: "Ollama not available, using template narratives"
  → UI shows narrative (template-generated) — functional but less polished

If NARRATIVE_PROVIDER=gemini and no API key:
  → Fall back to TemplateNarrativeProvider
  → Log warning

If NARRATIVE_PROVIDER=template:
  → Direct template generation, no fallback needed
```

---

## 17. Reset Semantics

### 17.1 Reset Contract

| Level | W / μ | Learning History | Convergence | Neo4j Decisions | Audit Trail | Graph Structure |
|---|---|---|---|---|---|---|
| **Soft** | → priors | Cleared | Cleared | Outcomes cleared (nodes remain) | RESET marker, new chain | Preserved |
| **Hard** | → priors | Cleared | Cleared | Nodes deleted | RESET marker, new chain | Re-seeded |
| **Checkpoint** *(TD-033)* | Snapshot saved | Not cleared | Not cleared | Not cleared | Checkpoint marker | Not changed |
| **Rollback** *(TD-033)* | → checkpoint μ | Cleared since checkpoint | Cleared since checkpoint | Outcomes cleared since checkpoint | ROLLBACK marker | Preserved |

**Checkpoint/Rollback (TD-033 — Loop 4 activation prerequisite):**
ProfileScorer must support `checkpoint(checkpoint_id)` and `rollback(checkpoint_id)`. These are the recovery mechanism when a synthesis operator (σ) causes centroid damage. EXP-OP2 proved TTL expiry alone does not repair damage — 35% of affected (category, action) cells never recover within 400 decisions post-expiry. Checkpoint is the only path back.

Checkpoint cadence: every 50 decisions minimum (configured in `SOCDomainConfig.get_checkpoint_config()`). An additional checkpoint is automatically taken when a synthesis operator is activated (`auto_checkpoint_on_operator_start=True`).

### 17.2 Implementation

```python
# backend/app/services/state_manager.py

class StateManager:
    """Coordinates reset across GAE state + audit store + Neo4j.
    
    Fixes TD-026: audit store and GAE history were out of sync on reset.
    All reset operations are atomic — partial reset is worse than no reset.
    """
    
    def __init__(self, learning_state, audit_store, neo4j_service, domain_config):
        self.learning_state = learning_state
        self.audit_store = audit_store
        self.neo4j = neo4j_service
        self.domain_config = domain_config
    
    async def soft_reset(self):
        """Reset learning state to priors. Preserve graph structure.
        Use case: evaluation runs, parameter tuning."""
        try:
            # 1. GAE state → priors
            self.learning_state.W = self.domain_config.get_initial_W()  # legacy
            self.learning_state.decision_count = 0
            self.learning_state.history = []
            self.learning_state.epsilon_vector = self.learning_state._build_epsilon_vector()
            save_learning_state(self.learning_state)
            
            # 1b. ProfileScorer centroids → configured values (v5.0)
            if hasattr(self, 'profile_scorer') and self.profile_scorer:
                self.profile_scorer.centroids = self.domain_config.get_profile_centroids().copy()
                self.profile_scorer.observation_counts = np.zeros_like(
                    self.profile_scorer.observation_counts)
            
            # 2. Neo4j: clear outcomes but keep Decision nodes
            await self.neo4j.execute_write("""
                MATCH (d:Decision) 
                SET d.outcome = null, d.correct = null, d.verified_at = null
            """)
            
            # 3. Audit trail: RESET marker + new chain
            self.audit_store.append_reset_marker("soft")
            self.audit_store.start_new_chain()
            
        except Exception as e:
            raise ResetError(f"Soft reset failed at step: {e}")
    
    async def hard_reset(self):
        """Full reset to day zero. Re-seed graph.
        Use case: development, fresh start."""
        try:
            # Steps 1, 3 same as soft reset
            self.learning_state.W = self.domain_config.get_initial_W()  # legacy
            self.learning_state.decision_count = 0
            self.learning_state.history = []
            self.learning_state.epsilon_vector = self.learning_state._build_epsilon_vector()
            save_learning_state(self.learning_state)
            
            # 1b. ProfileScorer centroids → configured values (v5.0)
            if hasattr(self, 'profile_scorer') and self.profile_scorer:
                self.profile_scorer.centroids = self.domain_config.get_profile_centroids().copy()
                self.profile_scorer.observation_counts = np.zeros_like(
                    self.profile_scorer.observation_counts)
            
            # 2. Neo4j: delete Decision nodes, re-seed
            await self.neo4j.execute_write("MATCH (d:Decision) DETACH DELETE d")
            await reseed_graph(self.neo4j)
            
            # 3. Audit trail
            self.audit_store.append_reset_marker("hard")
            self.audit_store.start_new_chain()
            
        except Exception as e:
            raise ResetError(f"Hard reset failed at step: {e}")
```

### 17.3 API Endpoint

```python
# backend/app/routers/admin.py

POST /api/admin/reset
  Body: {"mode": "soft"|"hard", "confirm": true}
  Validation: confirm must be true (prevent accidental resets)
  Returns: {"reset": "soft"|"hard", "timestamp": "..."}
  Notes: Not visible in standard UI. Development/evaluation tool only.
         Logged in audit trail as an auditable event.
```

### 17.4 Reset and Simulation

`SimulationOrchestrator` calls `state_manager.soft_reset()` before starting. This ensures:
- Clean learning progression from priors (charts start from baseline)
- Decision history in Neo4j visible (PatternHistory can read them) but outcomes cleared
- Audit trail has a RESET marker so post-simulation analysis knows the starting point

---

### 17.5 Rollback Execution Specification (TD-033)

**Status:** AUTHORITATIVE — v5.4-final. Sprint prompts TRUST-1 (Phase 4) and ARCH-3
read this section directly. Do not amend without updating those prompts.
Part 1 §6.4 specifies checkpoint creation (Hook 3 / ProfileSnapshot schedule).
This section specifies rollback execution. Both must exist before ARCH-3 builds.

> **v5.4-draft vs v5.4-final:** The v5.4-draft §17.5 used IKS-drop as trigger 1,
> automatic resume, and retroactive OutcomeRecord clearing. This section corrects all
> three: triggers are P_max-based + drift-based + manual; resume is manual-only via
> explicit POST; Hook 2 is suspended (not retroactively cleared) during the frozen window.

---

#### 17.5.1 Trigger Conditions (Three — Two Automatic, One Manual)

**Condition a — Scoring confidence collapse (automatic):**

When `ProfileScorer.score()` returns `P_max(decision) < 0.55` for `N` consecutive
decisions within the same category, `StateManager` automatically initiates rollback to
the most recent checkpoint for that category.

```python
# Configurable in CalibrationProfile (per-category)
ROLLBACK_PMAX_THRESHOLD = 0.55   # P_max below this triggers the counter
ROLLBACK_CONSECUTIVE_N  = 10     # N consecutive decisions below threshold
```

Rationale: P_max < 0.55 across 10 decisions in the same category means the centroid
for that category has drifted to a point where the scoring distribution is near-uniform
— the system has effectively lost its learned judgment for that category. This is the
most actionable early signal: it fires before an analyst or CISO notices, and it fires
in the specific category that needs repair.

N=10 is the default. Set N in `CalibrationProfile.rollback_consecutive_n[c]`
per-category. Categories with high natural variance (e.g., `cloud_infrastructure`)
may warrant N=15 to avoid false-positive rollbacks.

**Condition b — Centroid consistency failure (automatic):**

When `DriftMonitor` detects that `‖μ[c,a,:](t) − μ[c,a,:](checkpoint)‖₂ > S4_bound[c]`
in any (category, action) cell over a 50-decision rolling window:

```python
# Placeholder values — replace after PROD-1b runs
# PROD-1b derives per-cell drift causing 2pp accuracy degradation
S4_BOUNDS = {
    "credential_access":    0.30,   # placeholder
    "lateral_movement":     0.30,   # placeholder
    "insider_threat":       0.30,   # placeholder
    "data_exfiltration":    0.30,   # placeholder
    "cloud_infrastructure": 0.30,   # placeholder
}
```

Rationale: Rapid centroid movement in a single (c, a) cell indicates that a single
influential source (bad enrichment data, adversarial outcome injection, or a synthesis
operator with incorrect claims) is distorting the learned embedding for that cell.
The 50-decision window catches damage early without over-triggering on legitimate
fast learning during onboarding.

**S4_bound[c] placeholder note:** 0.30 is a structural placeholder derived from the
clip bound [0, 1] — it means "a cell has drifted by 30% of its full range." The
operationally correct value is the per-cell drift that produces 2pp accuracy
degradation at the category level, which requires PROD-1b to measure. PROD-1b is a
post-sprint design session experiment. Until it runs: 0.30 is the production value,
logged as a placeholder in `config.py` with a `# PROD-1b-placeholder` comment.

**Condition c — Manual rollback by CISO or SOC architect (explicit):**

```
POST /api/soc/rollback
Required body fields:
  operator_id:         string (CISO or SOC architect identity — logged in audit trail)
  target_checkpoint_id: string (from GET /api/soc/checkpoints — see §17.5.5)
  reason_code:         string (one of: "anomalous_scoring" | "bad_data_source" |
                                        "synthesis_operator_error" | "investigation" |
                                        "other:{free_text}")
```

This is the escape hatch for operators who observe anomalous scoring behavior that
has not yet triggered conditions a or b. Use case: CISO observes that auto-approve
decisions on `insider_threat` alerts have changed character over the past week;
pulls checkpoint list; identifies a plausible cause checkpoint; issues rollback.

---

#### 17.5.2 Rollback-and-Resume Semantics

Rollback is NOT a reset. It does not clear all learning to priors.
It restores the centroid tensor to a specific known-good past state and
locks further learning until an operator explicitly resumes.

**Step 1 — Centroid restore:**
Replace `ProfileScorer.centroids` with the tensor from `target_checkpoint_id`.
Replace `ProfileScorer.observation_counts` with the counts from `target_checkpoint_id`.
This is atomic — no partial state.

**Step 2 — Lock:**
Set `StateManager.learning_locked = True`.
While locked:
  - `ProfileScorer.score()` continues operating normally (recommendations continue).
  - `ProfileScorer.update()` does NOT apply centroid updates.
  - All `update()` calls during the locked window log `SKIPPED_ROLLBACK_FROZEN`
    to the audit store with the decision_id and timestamp. No centroid change occurs.
  - `Hook 2 (OutcomeRecord)` is suspended — no new OutcomeRecords are written
    for decisions during the frozen window. (Existing OutcomeRecords before the
    trigger are preserved untouched — no retroactive clearing.)
  - `Hook 3 (ProfileSnapshot)` continues on its 50-decision schedule.
    Snapshots taken during the frozen window carry `frozen=True` flag.

**Step 3 — Audit event:**
Immediately after centroid restore, write a `RollbackEvent` node to Neo4j:

```python
RollbackEvent {
    id:                        "RE-{uuid}",
    target_checkpoint_id:      str,
    decision_count_at_checkpoint: int,
    decision_count_at_trigger:    int,
    trigger_reason:            str,   # "pmax_collapse" | "drift_bound" | "manual"
    operator_id:               str,   # None if automatic
    timestamp:                 datetime,
    category_affected:         str,   # category that triggered conditions a or b; None if c
}
```

Link the `RollbackEvent` node to the `ProfileSnapshot` nodes for the pre-rollback
and post-rollback checkpoints with `[:ROLLED_BACK_FROM]` and `[:ROLLED_BACK_TO]`
relationships. These links are the audit trail for Tab 4 and for EU AI Act Article 9
evidence of corrective action taken.

**Step 4 — Resume (manual only):**

```
POST /api/soc/resume-learning
Required body fields:
  operator_id:   string (must match the operator_id of the initiating rollback OR
                          be a CISO-level operator)
  acknowledge:   true   (explicit acknowledgment that the cause has been investigated)
  notes:         string (free text — logged to audit store; required for Condition c
                          rollbacks; optional for automatic rollbacks)
```

On resume:
  - `StateManager.learning_locked = False`
  - All pending `SKIPPED_ROLLBACK_FROZEN` events remain in the audit store (permanent).
  - First ProfileSnapshot after resume carries `resumed=True, post_rollback=True`.
    This snapshot becomes the new drift baseline for `DriftMonitor`.
  - Emit `LEARNING_RESUMED` audit event with operator_id and acknowledge text.

**Why manual-only resume:**
Automatic rollbacks fire because the system detected damage. The damage has a cause
(bad data source, bad synthesis operator, adversarial injection). Resume before
identifying and addressing the cause will reproduce the same damage. Manual resume
forces an operator to acknowledge that an investigation occurred, creating an audit
trail that satisfies EU AI Act Article 9(2)(b) corrective action requirements.

---

#### 17.5.3 Hook Interaction During Frozen Window

| Hook | During frozen window | On resume |
|---|---|---|
| **Scoring pipeline** | Continues normally. No interruption to analyst workflow. | Unchanged. |
| **Hook 1 — DecisionRecord** | All Decision nodes continue to be written to Neo4j. Decision IDs remain valid. The routing and scoring history is permanent and not affected by rollback. | Unchanged. |
| **Hook 2 — OutcomeRecord** | **Suspended.** No new OutcomeRecords written during frozen window. `ProfileScorer.update()` calls log `SKIPPED_ROLLBACK_FROZEN` but do not modify centroids or write outcomes. Outcomes received during the frozen window are discarded permanently — they cannot be applied post-resume because the centroid state they would update has been restored. | Resumes normally on first `update()` call after `LEARNING_RESUMED`. |
| **Hook 3 — ProfileSnapshot** | **Continues** every 50 decisions on schedule. Snapshots carry `frozen=True` flag. These are diagnostic evidence for why rollback was triggered and what the centroid state looked like during the frozen period. IKS and drift analysis queries will use these. | First post-resume snapshot carries `resumed=True, post_rollback=True`. Becomes new drift baseline. |
| **Audit store** | `SKIPPED_ROLLBACK_FROZEN` logged per skipped update. `RollbackEvent` written immediately. | `LEARNING_RESUMED` written. All frozen-window events remain permanent (immutable). |

**Critical distinction — frozen window vs. retroactive clearing:**
The v5.4-draft said "clear OutcomeRecord fields for decisions since checkpoint."
This section does NOT do that. Retroactive clearing of verified outcomes violates
audit integrity and cannot be undone. Instead, during the frozen window, Hook 2 is
simply suspended — no new outcomes are written, and the restored centroids do not
incorporate any decisions from the damaged period. Pre-rollback OutcomeRecords
are unmodified and remain queryable for audit and for Tab 4 evidence export.

---

#### 17.5.4 What Rollback Does NOT Do

To prevent scope creep in ARCH-3 implementation, the following are explicitly
outside rollback scope:

```
✗ Does NOT delete DecisionRecords.
  Routing history is permanent. Every decision ever scored is queryable.

✗ Does NOT delete or modify OutcomeRecords written before the rollback trigger.
  Pre-trigger outcomes are the verified history. They are untouched.

✗ Does NOT affect the scoring pipeline.
  Analysts receive recommendations throughout. Rollback is invisible to analysts.

✗ Does NOT affect σ (synthesis bias tensor).
  Rollback is μ-only. If a synthesis operator caused the damage, it must be
  deactivated separately via POST /api/admin/synthesis/deactivate.

✗ Does NOT change the checkpoint schedule.
  Hook 3 continues to write ProfileSnapshots every 50 decisions,
  including during the frozen window (with frozen=True).

✗ Does NOT automatically resume learning.
  Resume requires an explicit POST /api/soc/resume-learning with
  operator acknowledgment. There is no timeout or automatic resume.
```

---

#### 17.5.5 Checkpoint Schedule and Admin API

**Checkpoint creation** (Hook 3 — spec in Part 1 §6.4):
```
ProfileSnapshot written every 50 decisions (existing Hook 3 schedule).
Each ProfileSnapshot IS a checkpoint — checkpoint_id = snapshot_id.
Retention: last 20 checkpoints = 1,000 decisions of rollback history.
Configurable via get_checkpoint_config() in SOCDomainConfig.
Oldest checkpoint evicted when retention limit is reached.
```

**Admin API:**

```python
GET /api/soc/checkpoints
  Returns: [
    {
      "checkpoint_id":             "PS-0047",
      "decision_count":            2350,
      "created_at":                "2026-03-09T14:22:11Z",
      "iks_at_snapshot":           47.3,
      "centroid_drift_since_prior": 0.12,   # ‖μ(t) − μ(t-1)‖_F (Frobenius norm)
      "frozen":                    false
    },
    ...
  ]
  Ordered: created_at DESC. Limited to max_checkpoints_retained (default 20).
  Use: operator selects target_checkpoint_id for manual rollback (Condition c).

POST /api/soc/rollback
  Body: {
    "operator_id":            "ciso-abanerjee",
    "target_checkpoint_id":   "PS-0047",
    "reason_code":            "anomalous_scoring"
  }
  Validation: target_checkpoint_id must exist; reason_code must be a valid enum value.
  Side-effects: centroid restore, learning lock, RollbackEvent written to Neo4j.
  Returns: {
    "rolled_back": true,
    "checkpoint_id": "PS-0047",
    "decision_count_at_checkpoint": 2350,
    "decision_count_at_trigger": 2423,
    "decisions_frozen_from_learning": 73,
    "iks_before_rollback": 34.1,
    "iks_after_rollback":  47.3,
    "timestamp": "2026-03-11T09:14:33Z"
  }
  Notes: Logged in audit store as ROLLBACK_INITIATED. Visible in Tab 4 audit view.
         Platform admin role required.

POST /api/soc/resume-learning
  Body: {
    "operator_id":  "ciso-abanerjee",
    "acknowledge":  true,
    "notes":        "Investigated: Pulsedive feed had stale TI data for 3 days.
                     Feed corrected. Resuming learning from PS-0047 baseline."
  }
  Validation: acknowledge must be true. operator_id required.
              notes required if the triggering rollback was Condition c (manual).
  Side-effects: learning unlocked, LEARNING_RESUMED event written, next ProfileSnapshot
                will carry resumed=True, post_rollback=True.
  Returns: {"resumed": true, "operator_id": "...", "timestamp": "..."}
```

---

#### 17.5.6 ARCH-3 Prerequisite Checklist

Before ARCH-3 (rollback implementation sprint prompt) executes:

```
✅ 1. Checkpoint creation spec complete — Part 1 §6.4 (ProfileSnapshot Hook 3)
✅ 2. Rollback execution spec complete — this section (§17.5, v5.4-final)
☐  3. StateManager.learning_locked flag + SKIPPED_ROLLBACK_FROZEN logging
☐  4. DriftMonitor: per-category rolling drift computation over 50-decision windows
☐  5. ProfileScorer.update() honors learning_locked flag
☐  6. RollbackEvent Neo4j schema + [:ROLLED_BACK_FROM]/[:ROLLED_BACK_TO] relationships
☐  7. GET /api/soc/checkpoints + POST /api/soc/rollback + POST /api/soc/resume-learning
☐  8. Hook 3 frozen=True / resumed=True / post_rollback=True flags
☐  9. PROD-1b run (or S4_bound placeholders explicitly logged in config.py)
```

Items 3–8 are ARCH-3 implementation scope (v5.5 Phase 4 / TRUST-1).
Item 9 is post-sprint. ARCH-3 ships with S4_bound=0.30 placeholder with
`# PROD-1b-placeholder` comment on every occurrence.

---

## 18. ATT&CK Integration

Every alert carries an ATT&CK technique ID and tactic label. This is table stakes — every competitor speaks ATT&CK language. No detection logic changes; this is labeling and display.

### 18.2 Alert Schema Addition

```python
# Each alert in the pool includes:
{
    "id": "ALERT-7823",
    "situation_type": "travel_anomaly",
    "technique_id":   "T1078",            # NEW
    "technique_name": "Valid Accounts",   # NEW
    "tactic":         "Initial Access",   # NEW
    # ... existing fields
}
```

### 18.3 UI Changes

**Tab 3 (Decision Detail):**
- Technique badge: `T1078 · Valid Accounts · Initial Access`
- Appears above the six-factor breakdown

**Tab 1 (Alert List):**
- Optional grouping: "Group by ATT&CK Tactic" toggle
- Tactic column in alert table

**Tab 4 (Compounding Metrics):**
- Per-technique accuracy in learning curve (future, post-v5.0)

### 18.4 Technique Mapping

| Situation Type | Technique | Tactic |
|---|---|---|
| travel_anomaly | T1078 Valid Accounts | Initial Access |
| credential_access | T1078.004 Cloud Accounts | Credential Access |
| threat_intel_match | T1566.001 Spearphishing Attachment | Initial Access |
| insider_behavioral | T1567 Exfiltration Over Web Service | Exfiltration |
| cloud_infrastructure | T1048 Exfiltration Over Alternative Protocol | Exfiltration |

> **S2P co-design note (v5.3):** `technique_id` is `Optional[str]` on `EvaluationScenario`
> and `alert` schema throughout. S2P has no ATT&CK. All technique-keyed groupings
> in the UI must gracefully handle `technique_id=None` without breaking. ~~See TD-036 —
> `EvaluationReport.by_technique` → `by_category` for the same reason.~~ **TD-036 CLOSED
> v5.0 GAE-EVAL: `EvaluationReport.by_technique` renamed to `by_category` in shipped code.**

---

## 19. Category Learning Curve

### 19.1 The Visual Proof of Institutional Judgment

A multi-line chart on Tab 4: x-axis is total decisions, y-axis is per-category accuracy, one line per alert category. The lines diverge over time — categories with more exposure improve faster.

This is the single most important visualization for proving compounding intelligence to a CISO or VC. "Same model, same code. Different categories learn at different rates. That's institutional judgment."

> **v5.3 note:** With v5.5-R3 (centroid drift chart) and v5.5-R4 (IKS), the category learning
> curve becomes one of three compounding-visibility surfaces. It proves *differentiation by
> category* while IKS proves *overall adaptation depth* and the drift chart proves
> *per-decision learning granularity*. All three are needed. They answer different
> sub-questions of "is it getting smarter?"

### 19.2 Data Source

`SimulationOrchestrator` tracks `by_category` accuracy during simulation. The chart updates via polling (`GET /api/simulation/status`). After simulation, the data persists in the learning state history.

For live (non-simulation) mode (v5.5+): accuracy is computed from `Decision` nodes in Neo4j using the `category_accuracy` SemanticConcept query (§24.1 in Part 1).

### 19.3 Chart Specification

```
Chart: Category Learning Curve
Type:  Multi-line time series
X-axis: Decision number (1 to N)
Y-axis: Rolling accuracy (window=10 decisions) per category
Lines:  One per alert category (5 lines)
Colors: Distinct per category — consistent with Tab 1 category color scheme
Annotations:
  - Horizontal dashed line at baseline (random = 20% for 5 actions from v5.3 — A=5)
  - Vertical line at any reset event (shows learning recovery speed)
Legend: Category name + current accuracy (rolling)
```

> **v5.3 correction:** Random baseline is now 20% (1/5 actions), not 25% (1/4 actions).
> `refer_to_analyst` is the fifth production action from v5.3 onward.

### 19.4 Implementation (SIM-2 prompt scope)

Part of the frontend simulation panel. Recharts multi-line chart. Data from `GET /api/simulation/status → by_category` accuracy per decision. The chart renders during simulation (polling updates) and persists after simulation completes.

---

## 20. v4.5 Complete Prompt Specifications

These are the archived v4.5 prompt specs. All were executed and tagged at v4.5. They are preserved here as reference for the execution pattern, test structure, and scope discipline. Do not re-execute — they are done.

> **Reading guide:** These prompts are models for how v5.0 prompts should be written.
> Note: one concern per prompt, read-before-write discipline, specific test assertions,
> no git, no debugger. The v5.0 prompts in `project_status_and_plan §4` follow the same format.

### 20.1 SIM-FIX (TD-026 — Atomic Reset) ✅ COMPLETE

```
REFERENCE: Read backend/app/services/gae_state.py. Read backend/app/core/state_manager.py
(if exists). Read backend/app/services/audit_store.py (or equivalent).

TASK [SIM-FIX]: Fix TD-026 — make reset atomic across GAE state, audit store, and Neo4j.

1. Create or update backend/app/services/state_manager.py:
   - StateManager class with soft_reset() and hard_reset() methods
   - soft_reset: W → priors, history cleared, Neo4j outcomes cleared, audit RESET marker
   - hard_reset: Everything in soft + Decision nodes deleted + re-seed
   - Both methods are atomic: if any step fails, raise error (no partial state)

2. Create backend/app/routers/admin.py:
   - POST /api/admin/reset with mode=soft|hard, confirm=true
   - Register in main.py

3. Update existing reset-all endpoint to use StateManager.hard_reset()

TESTS:
   # Test 1: StateManager imports
   python -c "from app.services.state_manager import StateManager; print('PASS')"
   
   # Test 2: API endpoint (server running)
   curl -X POST http://localhost:8000/api/admin/reset \
     -H "Content-Type: application/json" \
     -d '{"mode": "soft", "confirm": true}'
   # Should return 200 with reset confirmation

Do NOT start the debugger. Do NOT use git directly.
```

### 20.2 SIM-1 (SimulationOrchestrator) ✅ COMPLETE

Key requirements executed:
- Use CalibrationProfile from DomainConfig
- Call `state_manager.soft_reset()` before simulation start
- Track `by_category` accuracy in progress dict
- Same GAE pipeline as triage.py. No parallel scoring path (TD-019 lesson)

### 20.3 SIM-2 (Frontend Simulation Panel) ✅ COMPLETE

```
REFERENCE: Read frontend/src/tabs/ to understand tab structure.
Read backend/app/routers/simulation.py (created in SIM-1).

TASK [SIM-2]: Create frontend simulation panel with real-time updates.

1. Add simulation controls to Tab 4:
   - "Run Simulation" button with inputs: n_decisions (default 50), speed slider
   - Progress bar showing current/total
   - "Stop" button (calls POST /api/simulation/stop)

2. Category Learning Curve chart:
   - Multi-line Recharts chart
   - X: decision number, Y: rolling accuracy per category
   - One line per category (5 lines), distinct colors
   - Horizontal dashed line at 25% (random baseline — A=4) [CHANGED v5.5.1: was 20% at A=5]
   - Updates during simulation via polling (GET /api/simulation/status every 500ms)

3. Simulation summary panel (shown when complete):
   - Total decisions, overall accuracy, strongest/weakest category
   - Final centroid norm

TESTS:
   # Start simulation via API, verify frontend shows progress
   # After completion, verify category learning curve has diverging lines
   # Verify all existing tabs still work

Do NOT start the debugger. Do NOT use git directly.
```

### 20.4 NAR-1 (NarrativeProvider) ✅ COMPLETE

```
REFERENCE: Read backend/app/services/reasoning.py (existing Gemini integration).
Read backend/app/routers/triage.py (where narrative would be generated).

TASK [NAR-1]: Create NarrativeProvider protocol with three implementations.

1. Create backend/app/services/narrative.py:
   - NarrativeContext dataclass (see §16.2)
   - NarrativeProvider protocol
   - TemplateNarrativeProvider (zero dependency, always works)
   - OllamaNarrativeProvider (local Qwen via Ollama, graceful fallback to template)
   
2. Provider selection from .env:
   NARRATIVE_PROVIDER=ollama (default)
   NARRATIVE_MODEL=qwen2.5:7b (default)
   NARRATIVE_PROVIDER_SIMULATION=template

3. Wire into triage response — add narrative field to triage analysis response.

TESTS:
   python -c "
   import asyncio
   from app.services.narrative import TemplateNarrativeProvider, NarrativeContext
   provider = TemplateNarrativeProvider()
   ctx = NarrativeContext(alert_id='ALERT-7823', alert_type='TRAVEL_ANOMALY',
       technique_id='T1078', technique_name='Valid Accounts',
       factors={'travel_match': 0.82, 'device_trust': 0.91},
       dominant_factors=['travel_match', 'device_trust'],
       action='suppress', confidence=0.91, calibration_count=12,
       weight_changes=None, user_context=None, asset_context=None)
   result = asyncio.run(provider.generate(ctx))
   assert 'ALERT-7823' in result
   assert 'calibrated from 12' in result.lower() or 'Calibrated from 12' in result
   print(f'Narrative: {result}')
   print('TEST 1 PASS')
   "

Do NOT start the debugger. Do NOT use git directly.
```

### 20.5 NAR-2 (CISO Readability — Tab 2) ✅ COMPLETE

Key requirements executed:
- "Demo Deployment" header label (honesty label — fixes H7 item 10)
- "Demo data — live tracking in v5.0" in audit timeline (H7 item 11)
- "Illustrative" label on threat landscape (H7 item 12)
- "Projected" label on economic impact (H7 item 13)

### 20.6 TAB2-1 (Dual Decision Path Fix) ✅ COMPLETE (TD-019)

Fixed dual execution path — decisions were being scored twice (once in evolution.py, once in triage.py). All decisions now routed through single triage pipeline.

### 20.7 TAB2-2 (Event Bus) ✅ COMPLETE (TD-020)

`execute_action()` now emits events to `event_bus.py`. Actions no longer fire silently without an audit trail.

### 20.8 GAE-CAL-1, GAE-CAL-2 (CalibrationProfile) ✅ COMPLETE (TD-025)

CalibrationProfile dataclass added to GAE. `SOCDomainConfig.get_calibration_profile()` returns it. All scoring calls read `tau` and `penalty_ratio` from CalibrationProfile — no more hardcoded values in scoring functions.

### 20.9 HC-1 (Healthcare Domain) ✅ COMPLETE (simulation only)

Healthcare as a 6th simulation category (not production). Demonstrates domain generalization in the simulation panel. Uses a separate centroid slice — not mixed with the C=5 production centroids. Display label: "Healthcare (simulation variant)" to distinguish from production SOC categories.

### 20.10 SIM-3 (Alert Pool Expansion) ✅ COMPLETE

Alert pool expanded to 25 alerts across 5 categories. Each alert has ATT&CK technique ID, tactic, situation_type, and realistic factor profiles. ATT&CK badge displays on Tab 3.

### 20.11 SIM-4 (ATT&CK Display Integration) ✅ COMPLETE

Technique badge (`T1078 · Valid Accounts · Initial Access`) added to Tab 3 decision detail. Tactic grouping toggle added to Tab 1 alert list.

---

## 28. Response Data Realism (H7)

*(v5.2 §21 — renumbered to §28 in v5.3 to avoid collision with Shadow Mode §21)*

### 28.1 The Problem

During the v4.5 four-tab visual walkthrough before tagging, 13 instances were found where hardcoded values are presented to the user as if they were computed from live data. A technical evaluator will notice these immediately and question what else is fake.

### 28.2 Inventory

| # | Location | What's Hardcoded | Severity | Status |
|---|---|---|---|---|
| 1 | Tab 2 Outcome Feedback | PAT-TRAVEL-001 always appears regardless of alert category | **HIGH** | Open — v5.0 H7-FIX-1 |
| 2 | Tab 2 Decision Trace | "47 nodes traversed" (hardcoded) | HIGH | Open — v5.0 H7-FIX-2 |
| 3 | Tab 2 Decision Trace | "127 relationships analyzed" (hardcoded) | HIGH | Open — v5.0 H7-FIX-2 |
| 4 | Tab 2 Decision Trace | "891 historical decisions" (hardcoded) | MED | Open — v5.0 H7-FIX-2 |
| 5 | Tab 1 SOC metrics | Mock metric generators (soc.py router) | HIGH | Open — v5.0 H7-FIX-3 |
| 6 | Tab 1 Cross-context | Mock query results | MED | Open — v5.0 H7-FIX-3 |
| 7 | Tab 4 Weekly Trends | Static weekly trend data | MED | Open — v5.0 H7-FIX-4 |
| 8 | Tab 4 Evolution Events | Static evolution event list | MED | Open — v5.0 H7-FIX-4 |
| 9 | Tab 4 Decision Economics | Static economic values | LOW | Open — v5.0 H7-FIX-4 |
| 10 | Tab 2 Runtime header | "Demo Deployment" label | — | ✅ Fixed v4.5 NAR-2 |
| 11 | Tab 2 Audit Timeline | "Demo data — live tracking in v5.0" | — | ✅ Fixed v4.5 NAR-2 |
| 12 | Tab 2 Threat Landscape | "Illustrative" label | — | ✅ Fixed v4.5 NAR-2 |
| 13 | Tab 2 Economic Impact | "Projected" label | — | ✅ Fixed v4.5 NAR-2 |

### 28.3 Remediation Rule

**Every new UI element must satisfy one of:**
1. Value traces to a real computation (Neo4j query, GAE centroid, simulation result, SemanticConcept query)
2. Value carries a visible honesty label ("projected", "demo data", "illustrative")

No silent hardcoding. This rule applies to all prompts from v5.0 forward. It is codified in §13 Claude Code Rules.

> **v5.3 extension:** Shadow mode decisions (§21 Part 1) are real computation — they are
> written to the graph with `shadow_mode=True` and are queryable. The shadow report
> agreement rate is a live Neo4j aggregate, not a hardcoded estimate. Tab 5 Panel A
> (§24 Part 1) is driven entirely by SemanticConcept queries — zero hardcoded values.
> Both close the H7 spirit requirement before they ship.

---

## 29. Phase C — RESOLVED by Experiments

*(v5.2 §22 — renumbered to §29 in v5.3)*

### 29.1 What Happened (v4 context)

The original Phase C design (DISC-1 through GATE-B3) proposed implementing Eq. 6 (cross-graph attention sweep) directly in the SOC copilot. An LLM judge panel (GPT 5.3, Opus, Grok) evaluated this plan and reached unanimous consensus: don't implement as-is.

A bridge layer hypothesis was developed (`bridge_layer_design_v1`, 723 lines) proposing: Phase 1 (OracleProvider), Phase 2 (Gating Matrix G), Phase 3 (Discovery from diagnostics).

### 29.2 Experiment Results — Architecture Settled

**25 experiments executed** (9 bridge + 5 validation + 10 OP/synthesis + 1 EXP-OP3 series). Full catalog in `bridge_experiments_catalog_v7`.

| Hypothesis | Experiment | Result | Verdict |
|---|---|---|---|
| Gating Matrix G improves scoring | EXP-A (4 variants) | +0.01pp best case | **FALSIFIED** |
| Per-category W improves scoring | EXP-A2 | 51.61% (sample starvation) | **FALSIFIED** |
| Factor data has signal | EXP-C1 | 97.89% L2, 61% dot | **CONFIRMED** |
| Dot product is root cause | EXP-C1 | 36.89pp gap (dot→L2) | **CONFIRMED** |
| Profile scoring works with learning | EXP-B1 | 98.2% warm, 90.7% cold | **CONFIRMED** |
| Cross-category transfer accelerates | EXP-D1 | Config wins 2–14pp | **MARGINAL** |
| Factor interactions exist | EXP-D2 | 0 significant / 75 pairs | **FALSIFIED** |
| Pluggable kernels needed | EXP-E1 | L2 2/3, Maha mixed-scale | **CONFIRMED** |
| Architecture scales | EXP-E2 | 99.9% at 20×10×20 | **CONFIRMED** |

The v4 decision matrix was superseded. The outcome was better than any of the 7 planned scenarios: the root cause (dot product kernel) was identified and fixed, eliminating the need for G entirely.

### 29.3 What Replaced Phase C

| Original Phase C Element | Replacement | Why |
|---|---|---|
| Gating Matrix G (DISC-1, DISC-2) | **ELIMINATED** | EXP-A: +0.01pp. Diagonal projection cannot separate overlapping classes. |
| Discovery from G diagnostics (DISC-3) | **DEFERRED to v6.0+** as meta-graph reflection | Discovery is production monitoring, not scoring. EXP-D1/D2 showed marginal value. |
| OracleProvider (GATE-B1) | **GAE-ORACLE-1** in v5.0 Phase 3 | OracleProvider protocol survived. Captured as TD-032. |
| Situation classifier feeding G | **SIT-1: MoE head selector** | SituationAnalyzer selects profile centroid set (category routing), not a gating modulator. |

### 29.4 Validation Experiments (V1A–V3B) — Production Requirements

Five additional experiments prompted by independent LLM reviewer concerns:

| Experiment | Finding | Production Requirement |
|---|---|---|
| V1A | Scaling exponent b=2.11 (was 2.30) | Moat claims softened. "Structural" not "formal" correspondence. |
| V1B | 2.9M× norm explosion without LayerNorm | TD-031: LayerNorm in Tier 5 enrichment (v5.5) |
| V2 | Centroid escape at dec 6–12 adversarial | All centroid updates MUST clip to [0.0, 1.0] |
| V3A | L2 94.78% vs XGBoost 92.24% (static) | Architecture beats ML baselines |
| V3A | L2 94.3% immediate vs XGB 91.5% at 1300 samples | Compounding thesis measured (online advantage) |
| V3B | ECE=0.036 at τ=0.1 vs ECE=0.19 at τ=0.25 | TD-030: τ default changed to 0.1 everywhere |

### 29.5 Impact on SOC Copilot

The original Phase C prompts (DISC-1 through GATE-B3) are **permanently retired**, not just deferred. The scoring architecture is settled. v5.0 implements ProfileScorer (§10.2).

**Remaining from Phase C scope:**
- Meta-graph reflection for production monitoring → v6.0+
- Discovery of new scoring dimensions → v6.0+ (requires meta-graph)
- Cross-category transfer → v6.0+ (EXP-D1: marginal but useful for cold-start categories)

**Synthetic validation methodology (SVM) — validated, not provisional:** [UPDATED v5.5.3]
All bridge + validation experiments used synthetic centroidal data generated via LLM-judge
persona frameworks. This is the primary development and validation methodology for this
product — not a workaround pending real customer data. The 390-cell factorial covers
σ 0.05–0.35, q̄ 0.57–0.95, V 30–500: more of the realistic deployment parameter space than
any single real deployment ever will. FX-1-PROXY-REAL (KL divergence 1.88–2.58 between
synthetic and real IOC distributions) is the distribution coverage proof — it confirms the
synthetic distribution spans the realistic deployment range. It is methodology validation,
not a gap disclosure.

FX-1 completion (SVM-005 in master_action_plan_v4.3): extending the distribution
characterization from the current IOC-heavy subset to all 6 alert categories via
web-scraped ATT&CK frequency data and SANS alert taxonomy statistics. This is a data
calibration step (~1 day), not an architectural prerequisite. Profile centroid values in
`SOCDomainConfig` are domain expert estimates that serve as the bootstrap prior — they are
the starting point that deployment learning replaces. Calibration against external
distributions improves cold-start accuracy, validated via SVM-003 (V-CGA-FROZEN v4)
and the enrichment advisor (5 deployment profiles, 499 tests).

**GATE-R dependency on DecisionRecord (Hook 1):** [UPDATED v5.5.3] GATE-R is the routing accuracy measurement gate — it determines whether SituationAnalyzer correctly routes alerts to the right centroid slice (μ[c,:,:]) before citing 97.89% as system-level accuracy. **TD-035 CLOSED: GATE-R ran after v5.5-R6 shipped (complete alert_type→category mapping) and returned 100% routing accuracy.** Composite accuracy confirmed: routing_accuracy=1.0 × 0.9789 = 0.9789. The conditional "assuming correct routing" caveat is no longer required for external use of the 97.89% number. Full catalog entry in experiment_reference_catalog_v2.

### 29.6 OP Series Findings (10 experiments — March 7, 2026)

Ten OP/synthesis experiments validated the intelligence layer architecture. GATE-OP passed.

| Experiment | Finding | SOC Impact |
|---|---|---|
| EXP-OP1-FINAL | GATE-OP PASSED: delta=+0.0041 AUAC, p=0.0008 at λ=0.5 | σ helps — acute phase benefit confirmed |
| EXP-OP2 | T_recovery paradox: 75%-correct operator causes lasting damage, 35% never-recover | Only 100%-correct operators permitted. Checkpoint required (TD-033). |
| EXP-OP2 | Correct operator benefit: +0.0124 AUAC (p<0.001) | High-quality σ cells have real value |
| EXP-OP2 | Operative window: λ∈[0.5, 0.6] Bonferroni-significant with Loop 2 running | λ=0.5 default if Tab 5 ships. Never λ>0.6 without quality controls. |
| τ_modifier tests | ECE degradation +0.138 at any τ_mod≠1.0 | τ FIXED at 0.1 always. No synthesis condition changes temperature. |
| EXP-S3 | Loop 2 firewall Frobenius 0.0028 | update() has NO σ parameter. Firewall permanent. |
| S-series | σ_max = p10 empirical L2 margin distribution | Not fixed 1.0. Recalibrated every 500 decisions. |
| S-series | activation_threshold = 0.95 (autonomous), 0.80 (human-reviewed) | Sparse σ by default. Dense σ with incorrect cells causes T_recovery paradox. |

**SOC-specific design decisions from OP series:**

1. **Tab 5 ships at v5.5 ONLY IF GATE-M passes.** EXP-S2-REPRO at operative λ with Loop 2 running required before GATE-M decision. GATE-D also required.

2. **GATE-V failure → human review only.** If Tab 5 σ does not improve real analyst decisions by ≥3pp, σ goes to advisory mode pending root cause analysis. No auto-pivot. No silent downgrade.

3. **A=4 canonical.** `refer_to_analyst` removed as scorable action — accessed via referral rules R1-R7 (not confidence gate). Static accuracy improved 80.6→90.6%. Zero dangerous actions. [CHANGED v5.5.1]

4. **EXP-OP3 before any production σ deployment.** ResidualTracker (checkpoint-based drift measurement, not unobservable target) required. TD-033 infrastructure prerequisite.

5. **P0 fix: asymmetric η (March 19, 2026).** [NEW v5.5.1] 9-persona LLM-judge stress test (B5B-PROXY) found 13-27pp centroid degradation from realistic analyst rolling verified accuracy (q̄=0.60-0.70). The override path carries noise from analyst errors. η_override=0.01 attenuates this by 5× relative to η_confirm=0.05. Validated across 24 personas (Phase 1 quality sweep). See gae_design_v10 §9.5.

6. **DiagonalKernel is v6.0 default.** [NEW v5.5.1] V-MV-KERNEL factorial (360 cells) validated +13.2pp SOC, +6.8pp S2P on heterogeneous noise. Noise ceiling moves from σ≤0.157 (L2) to σ≤0.25 (Diagonal). Healthcare deployments open at v6.0. ShrinkageKernel deprioritized to v7.0 (off-diagonal adds <1pp in both domains). See gae_design_v10 §10.

7. **Referral routing is rules, not confidence gate.** [NEW v5.5.2] Four experiments (EXP-A4-DIAGONAL, REFER-LEARN, REFER-COVERAGE, REFER-LAYERED) settled the referral architecture. A=4 confirmed (13pp structural gap, kernel-independent). Factor-only classifiers fail (all gates fail). Confidence gate has 14% precision for referral — active harm. Policy rules R1-R7 achieve 72.7% DR at 12% FPR with 50.7% precision (978 net min/100 alerts vs 367 for confidence gate). Architecture: action routing (ProfileScorer A=4) and referral routing (ReferralEngine R1-R7) are independent. Referral is a VETO — overrides auto-approve at any confidence. Three phases: Rules (v6.0, Day 1) → OverrideDetector (v6.5, data-gated ≥50 production positives) → monthly retrain (v7.0). See gae_design_v10 §12.3, soc_copilot_design Part 1 §22.6.

8. **Phase 1 closure findings (March 25, 2026).** [NEW v5.5.3] Seven new UNCONDITIONAL claims from Phase 1 session. Key architectural findings documented in claims_registry_v8.3 and architecture_philosophy_v4.1:

   **W2 compounding flywheel validated (CLAIM-W2).** V-TRIGGERED-EVOLUTION full: +10.13pp accuracy (CI=[+5.4,+14.9]pp, p=0.0002, N=30). PatternHistoryFactorComputer (§5.6 Part 1) reads recency-weighted TRIGGERED_EVOLUTION edges. Δ_dissimilar=0.00pp — enrichment is context-specific, not indiscriminate. The W2 pathway compounds independently of centroid evolution. "Graph compounds while centroids wait" is now CLAIM-W2, not a narrative. See Part 1 §5.6.

   **Flywheel Health Monitor validated (CLAIM-OLS-01).** V-OLS-DETECT: 0% miss rate, p90≥50d lead time (both adversarial and complacency conditions, N=30 per condition). CUSUM on OLS, h=5.0 (OLS scale — not h=15.0 which was calibrated for q̄ scale). Plateau-snapshot baseline. Conservation law now has four roles — flywheel health monitoring is the fourth. See Part 1 §22.7.

   **Var(q) as gating condition: PERMANENT HARD STOP.** V-MV-CONSERVATION series (v2–v10) + V-MV-CONSERVATION-BIMODAL confirmed the Bernoulli mixture theorem: Var(Q_bimodal) = p̄(1-p̄), identical to uniform Bernoulli at same mean. Binary rolling verified accuracy observations cannot detect bimodal team structure. Not an implementation gap — it is arithmetic. Var(q) is a logged observability metric only. Per-analyst OLS variance (Analyst Contribution Monitor) is the correct Level 3 signal. See Part 1 §22.7.

   **Switching cost quantified (CLAIM-SC-01).** V-SWITCHING-COST: IKS=67 requires 537 verified analyst decisions. Full quarter at V=200, α=0.25. Common categories calibrate in ~2 weeks. Competitors starting fresh start at IKS=0. Switching cost grows every day the system runs.

   **Convergence calendar validated (CLAIM-CONV-01).** V-MV-CONVERGENCE v2: MAE=1.55d. V has NO causal effect on N_half (volume affects wall-clock time only). q̄ is the dominant driver (coefficient -3.28). "Higher analyst engagement is the single biggest driver of calibration speed." Calendar shows decisions AND days separately. Phase 3 Priority 1 feature — unblocked.

   **Two-tier poisoning resilience (CLAIM-SK-01 + CLAIM-LP-01).** EXP-S2-REPRO-A4 series at A=4 geometry: σ-perturbation mean 0.850pp at 20% rate (gate revised to ≤1.0pp mean). Label poisoning mean 3.20pp at 20% adversarial (gate ≤5pp mean). At realistic 5% adversarial rate: ~0.80pp label poisoning. Prior single-gate claim (≤0.20pp) was calibrated at A=5 geometry — A=4 migration required recalibration.

   **Enrichment safety validated (CLAIM-65).** V-ENRICHMENT-NEGATIVE v2 (GAE 0.7.8): SAFE. DiagonalKernel self-correction bounds degradation <1.2pp at adversarial multi-factor contamination (N=50). The mechanism is arithmetic — bad enrichment raises σ → W=1/σ² drops → bad signal downweighted automatically. Source trust gate (0A-6) moved to Post-MVP as enrichment provenance logging (not a safety requirement).

9. **April 5-6 session: third compounding pathway + economics validated.** [NEW v5.6]

   **Graph enrichment independent of learning (CLAIM-59 UNCONDITIONAL, April 6, 2026).** V-CGA-FROZEN PASS: 54.4% fewer decisions to reach 85% accuracy after centroid unfreeze when enrichment ran during freeze period. Paired t-test p<0.0001. 26/30 seed pairs consistent. Two-stream design (Stream A: centroid learning, no enrichment; Stream B: centroids frozen 45 days + enrichment active, then unfreeze). This is the THIRD compounding pathway alongside centroid learning (Tier 2) and W2 flywheel (all tiers). Bottom-right quadrant (~10-15%, σ>0.25 or q̄<0.70) has a validated second compounding pathway — graph enrichment works even when centroids cannot learn.

   **Enrichment Day-1 lift quantified (CLAIM-62 UNCONDITIONAL, SVM-003b).** Production configuration (enriched μ₀ + DiagonalKernel): +42.69pp Day-1 lift. Decomposed: +40.93pp from enriched μ₀ initialization (Innovation 7) + +1.76pp from DiagonalKernel sigma-weighting (Innovation 4). Cross-environment consistency confirmed across healthcare, FinServ, midmarket.

   **Fisher info path empirically confirmed (CLAIM-64 UNCONDITIONAL, SVM-004b, GAE 0.7.20).** Enrichment → lower σ → higher W_i = 1/σ² → higher η_eff (effective learning rate per decision). r=0.9669 empirical = analytical (delta=0.0000). Enrichment delivers returns at two timescales: better Day-1 accuracy (CLAIM-62) AND faster per-decision learning rate (CLAIM-64). **Architecture note:** use DiagonalKernel.raw_weights (true 1/σ²) for η_eff calculations, not .weights (pre-normalized). GAE 0.7.20 required.

   **Economics validated (CL-ECON-MEASURED UNCONDITIONAL, SVM-002b).** 30.85 min/alert (CI=[29.90,31.81]), SANS SOC Survey 2024 calibrated (43.2 min baseline, 1.7% deviation). ROI: healthcare $829K/year, FinServ $2.79M/year, midmarket $523K/year. Cross-judge range: 22.1–30.85 min (Claude Opus primary; GPT-4o 28% spread — genuine model disagreement on AI assistance magnitude, not correlated bias). **Innovation 10 (Decision Economics) gap CLOSED.** All 11 innovations now have validated claims.

---

### 29.7 Session Findings — April 7–8, 2026 (v5.7) [NEW]

**Block 7.1 — Sentinel Write-Back: ✅ DONE (April 8, 2026)**

Sentinel write-back ships fire-and-forget (async, no triage latency impact). Implementation:
action→classification enum mapping for Sentinel schema compatibility. 3× exponential backoff
on 429/503. +5 tests. Closes the bidirectional loop: alerts in (Block 4.2 ✅) + knowledge back
(Block 7.1 ✅).

**BACKLOG-015 Extended — 3 Critical EXP-G1 Fields (April 8, 2026)**

Three additional fields added to EXP-G1 logging (see Part 1 §27.2 for full spec):
- `centroid_distance_to_canonical` per verified decision: model-independent convergence signal.
  Simulation proved N_half (rolling accuracy) is too noisy; centroid distance decreases
  monotonically and is the primary EXP-G1 γ metric.
- `pattern_history_value` per decision: W2 enrichment adaptation tracking.
- `alert_category_distribution` rolling 100-decision: vector distribution shift detection.

**γ Theorem Established — CC-21 → Tier 2 (April 8, 2026)**

Re-convergence speed ratio γ = N_half,1/N_half,2 > 1 proven analytically:
- Theorem: γ > 1 ⇔ ε_firm > α_cat · ‖Δ‖ · θ / (θ − (1−α_cat)) ≈ 0.128
- Four independent LLMs confirmed (GPT-4.1, Opus 4, Grok 3, Gemini).
- Simulation binary confirmation: ε=0.05 < 0.128 → γ=0.71 < 1 ✓; ε=0.20 > 0.128 → γ=1.03 > 1 ✓.
- CC-21: Tier 2 (conditional). Tier 1 via EXP-G1 pilot data.
- Full record: synthetic_data_generation_analysis_v2.md, math_synopsis_v13.md §3.2.

**Test Counts**

900 SOC backend (was 532 entering this session). 183 E2E confirmed.
+5 Block 7.1 write-back tests. Block 3.6 +5, Block 4.2 +7 (already in v5.6).


## 30. Feature Gaps — Full Table (F1–F15)

*(v5.2 §23 — renumbered to §30 in v5.3; F12–F15 status updated for v5.3)*

### 30.1 Context

Cross-referencing the roadmap against 2026 CISO priorities, VC investment patterns, and competitor positioning identified 15 feature gaps. Full analysis in `gap_analysis_v9.1 PART 13`. Gaps F12–F15 are intelligence layer proposals — they are gated by GATE-M/GATE-D/GATE-V.

### 30.2 SOC-Relevant Feature Gaps

| ID | Feature | Why It Matters | Target | Effort | v5.5 Status |
|---|---|---|---|---|---|
| **F1** | **Shadow Mode** | Zero-risk deployment on-ramp. Graph accumulates during shadow — by go-live, already calibrated. Every 2026 enterprise deployment guide requires it. | v5.5 | HIGH | **Fully specified — §21 in Part 1. v5.5-R8.** |
| **F2** | **Detection Engineering Feedback** | Rule Quality Score from profile centroid evolution. Uniquely enabled by μ centroids. | v5.0 | LOW | **✅ COMPLETE v5.0. Centroid drift chart in Tab 4. Detection Engineering panel in Tab 3.** |
| **F3** | **EU AI Act Compliance Evidence** | Map evidence ledger to Art. 9/12/13/14/15. Aug 2, 2026 deadline (~4.5 months). Fines €35M or 7% global turnover. | v5.5/v6.0 | MED | **Partially shipped.** v5.5-R13: evidence export. 0A-5 (Phase 0): kernel_type, noise_zone, conservation_status on every decision — Art. 15 epistemic state. Full compliance package at v6.0 (L-10 compliance dashboard, five panels). |
| **F4** | **Operational Outcome Metrics** | MTTD/MTTR/FP rate trended. Compounding story in CISO language. | v5.0 | LOW | **✅ COMPLETE v5.0. MTTD/MTTR/FP overlay shipped. Economics dashboard (ECON) shipped. IKS (§22 Part 1) covers the compounding story.** |
| **F5** | **Multi-SIEM Abstraction** | SIEMConnectorProtocol. Splunk-only = 30% TAM, multi-SIEM = 80%. | v6.0 | HIGH | No change — v6.0. |
| **F6** | **Attack Chain Correlation** | Link alerts via graph entities into multi-stage ATT&CK campaigns. Tier 1 → Tier 2 value (3–5×). | v6.0 | HIGH | No change — v6.0. |
| **F7** | **NHI Behavioral Baseline** | Service accounts, API keys, AI agents as first-class graph entities. 82:1 ratio. | v6.5 | HIGH | No change — v6.5. |
| **F8** | **Cross-Tenant Meta-Intelligence** | Anonymized threat sharing. Network effect (15× → 30× multiple). | v7.0 | HIGH | No change — v7.0. |
| **F9** | **Analyst Benchmarking Report** | Formal AI vs. analyst comparison from shadow data. Benchmarks improve over time. | v5.6 ✅ | MED | **✅ DONE (April 6, 2026).** /api/soc/f9-report endpoint. Shadow data: AI vs analyst comparison. 4 tests. Most powerful single CISO claim — AI 85% vs analyst 38% on lateral movement. Now demo-able. |
| **F10** | **A2A/MCP Protocol** | Google A2A + Anthropic MCP for multi-agent interop. | v7.0+ | MED | No change — v7.0. |
| **F12** *(PROPOSAL)* | **INTSUM-Quality Threat Briefing** | Tab 5 Panel A. CISA KEV + NVD + vendor advisories synthesized to INTSUM-style briefing. σ[c,a] bias computed from claims. Gated: GATE-M + GATE-D. | v5.5 | MED | **Panel A ships deterministically via SemanticRegistry (§24 Part 1). σ scoring component gated by GATE-M.** |
| **F13** *(PROPOSAL)* | **ContextConnectors (email/Slack/docs)** | LLM+template extraction from Slack messages, CISO emails, incident reports → claims → σ. Rowboat-inspired. Gated: GATE-D. | v6.0 | HIGH | No change — v6.0, gated. EnterpriseConnectorProfile pattern (§25 Part 1) is the structural foundation. |
| **F14** *(PROPOSAL)* | **Ask the Graph** | Tab 5 Panel B. Prompt-driven executive analysis. Evolves existing POST /api/soc/query endpoint. Gated: GATE-M + GATE-D. | v5.5 | LOW | **Fully specified — §24.2 Part 1. 15 pre-built queries + QueryRouter. NL routing ships; σ scoring gated.** |
| **F15** *(PROPOSAL)* | **SynthesisNode Artifact** | Tab 5 internal. SynthesisNode as inspectable computational artifact. Gated: GATE-D + GATE-V. | v6.0 | MED | No change — v6.0, gated. |

### 30.3 What's Uniquely Enabled by Compounding Architecture

Six capabilities are structurally impossible for stateless competitors:

| Feature | Why Only Compounding Architecture |
|---|---|
| F1 Shadow Mode | Graph accumulates during observation. Competitors reset to zero at go-live. |
| F2 Detection Feedback | Requires cross-decision memory of rule quality. Centroid evolution encodes this. |
| F4 Operational Metrics | Improving MTTR requires a system that gets better. Stateless = flat metrics. |
| F6 Attack Chains | Campaign correlation through shared graph entities. LLM sees one alert; graph sees the campaign. |
| F8 Cross-Tenant | Requires persistent structured knowledge across tenants. No cross-session state = no aggregation substrate. |
| F9 Benchmarking | 71.7% → 78.9%+ over 1,000 decisions only measurable with a learning system. |
| F12 INTSUM Briefing *(PROPOSAL)* | σ[c,a] synthesis bias uses same profile centroids μ as operational scoring. Stateless systems have no μ to bias against. |
| F14 Ask the Graph *(PROPOSAL)* | Queries answered using accumulated graph + centroid state. More decisions = richer answers. |

### 30.4 SOC Copilot Version Placement (Updated v5.3)

| Version | Feature IDs |
|---|---|
| v5.0 | F2 (detection feedback primitive), F4 (operational metrics primitive) |
| v5.5 | F1 (shadow mode — full), F3 (partial compliance), F12 Panel A (deterministic), F14 (pre-built queries) |
| v5.6 ✅ | F9 (analyst benchmarking report — /api/soc/f9-report, 4 tests) |
| v6.0 | F5 (multi-SIEM), F6 (attack chains), F9 (benchmarking report), F13 (ContextConnectors — gated), F15 (SynthesisNode — gated) |
| v6.5 | F7 (NHI behavioral baseline) |
| v7.0+ | F8 (cross-tenant), F10 (A2A/MCP) |

F12–F15 version placement assumes gates pass. If GATE-M fails: F12 Panel A (deterministic briefing) ships as scheduled; σ component deferred. If GATE-D fails: F13, F14 σ component, F15 all deferred pending root cause.

---

*SOC Copilot — Design Document v5.6 (Part 2 of 3) | April 6, 2026*
*Covers: §§15–20 (simulation, narrative, reset/rollback, ATT&CK, learning curve, v4.5 prompts)*
*Covers: §§28–30 (H7 data realism, Phase C resolution, feature gaps F1–F15)*
*Phase 0 ✅ Phase 1 ✅ Phase 2 ✅ Phase 3 Priority 1 ✅. Loom demo v1 unblocked.*
*995 GAE tests, 900 SOC backend + 183 E2E tests, 174 ci-platform tests. ~295 experiments.*
*P0 fix: η_override=0.01. DiagonalKernel +13pp SOC. A=4 canonical.*
*Referral: Rules R1-R7 = 72.7% DR / 12% FPR. Confidence gate REJECTED (14% precision).*
*W2 flywheel: CLAIM-W2 +10.13pp (p=0.0002). Flywheel Health Monitor: CLAIM-OLS-01 0% miss, p90≥50d.*
*Var(q) gating: PERMANENT HARD STOP (Bernoulli mixture theorem). Switching cost: 537 decisions = full quarter.*
*TD-035 CLOSED: GATE-R 100% routing accuracy. 97.89% composite accuracy confirmed unconditional.*
*§29.5 SVM methodology: FX-1 is distribution coverage completion, not a validation prerequisite.*
*Synthetic data IS the development process. Real data is a commercial milestone, not a validation gate.*
*§29.6 updated: 9 findings. CLAIM-59 third compounding pathway. CLAIM-62 +42.69pp. CLAIM-64 r=0.9669. CL-ECON-MEASURED.*
*§29.7 NEW (v5.7): April 7-8 session. γ theorem ✅ (CC-21 Tier 2). Block 7.1 ✅. BACKLOG-015 extended. Batch F RETIRED.*
*Innovation 10 (Decision Economics) gap CLOSED. All 11 innovations have validated claims.*
*F9 Analyst Benchmarking Report ✅ DONE (April 6). AI 85% vs analyst 38% lateral movement — now demo-able.*
*Part 1 covers: §§1–14, 21–27 (architecture, product identity, shadow mode, IKS, NL templates,*
*SemanticRegistry, enterprise hooks, gap closure map, experiment landscape, appendices)*
*Part 3 covers: §§7–9 (GAE evaluation, judgment metrics, ablation — v5.0 COMPLETE)*
# SOC Copilot — Design Document v5.7 (Part 3 of 3)

**Covers:** §§7–9 (v4.1 SOC copilot prompts, end-to-end compounding verification,
v4.5 scope "Make It Real") plus the master section index for all three parts.

**Status of content in §§7–9:** All ✅ COMPLETE — executed and tagged at v4.1 and v4.5.
Preserved for historical record, execution pattern reference, and sprint discipline modeling.
These prompts are not to be re-executed. They are the foundation v5.0 builds on.

**Status of Master Section Index (updated to v5.5.3 — March 25, 2026):**
Phase 0 ✅ Phase 1 ✅ Phase 2 ✅ Phase 3 Priority 1 ✅. 995 GAE, 900 SOC backend + 120 E2E, 174 ci-platform tests.
Section index reflects all changes through v5.6: §4.4 canonical numbers updated (CLAIM-59/62/64/CL-ECON-MEASURED),
§26 April 5-6 completions, §27 experiment landscape (~175 total), Appendix A v5.6, Appendix B BACKLOG items resolved.
Changes from v5.5.3 → v5.6: Header/footer updated. Master Section Index rows updated.

Changes from v5.5.1 → v5.5.2: §14 referral rules entry added. Architecture note for referral VETO.
Changes from v5.5.2 → v5.5.3: Header/footer updated. §9.3a HC-1 shape note corrected (5,5,6)→(6,4,6),
C=5→C=6. Master Section Index: 8 rows updated, §22.7 added, architecture philosophy reference
updated to v4.1. Key Files by Task: architecture philosophy row updated.

> **v5.5.1 annotation note:** A=4 canonical (was A=5). refer_to_analyst removed as
> scorable action. Content in §§7–9 references A=4/A=5 from their historical context
> — annotations clarify where the current canonical differs.

---

## 7. v4.1 SOC Copilot Prompts (6 prompts — soc-copilot repo) ✅

> GAE repo prompts (GAE-0 through GAE-2a-protocol, 7 prompts) are in `gae_design_v10`.
> These SOC prompts begin after GAE-2a-protocol is complete.

### 7.1 SOC Prompt Sequence

| Prompt | Scope | Creates/Modifies | Test |
|---|---|---|---|
| GAE-2a-soc | TravelMatch + AssetCriticality + orchestrator + seed | `domains/soc/factors.py`, `orchestrator.py`, `seed_neo4j.py` | Queries traverse relationships. Factor values ∈ [0,1]. |
| GAE-2b | ThreatIntelEnrichment + PatternHistory + seed | `domains/soc/factors.py`, `seed_neo4j.py` | PatternHistory returns 0.5 with <5 decisions. |
| GAE-2c | TimeAnomaly + DeviceTrust (rewrite to use relationships) | `domains/soc/factors.py`, `seed_neo4j.py` | **Must traverse `[:ACTIVE_AT]`, `[:USES_DEVICE]`.** |
| GAE-2d | Wire router + Decision write-back + events | `routers/triage.py`, `config.py`, `services/event_bus.py` | Decision node EXISTS after analyze. f(t) stored. Events emitted. |
| GAE-3a | Feedback → Eq. 4b + outcome write-back + trust gate | `services/feedback.py`, `routers/feedback.py` | f(t) from GRAPH (R4). Decision marked. Re-analyze → scores differ. |
| GAE-3b | Compounding dashboard — real data | `CompoundingTab.tsx`, `routers/gae.py` | Empty on first load. Real curves after 5 decisions. |

> **v5.3 note:** GAE-3a implements Eq. 4b (centroid pull/push with 20:1 asymmetry) — the
> v4.1 version. The v5.0 sprint (GAE-PROF-1 through SOC-PROF-3) replaces the scoring
> mechanism with Eq. 4-final (L2 distance, ProfileScorer). The centroid pull/push
> mechanics of GAE-3a remain correct and are preserved in ProfileScorer.update().

### 7.2 Additional Copilot-Level Prompt

| Prompt | Scope | Creates/Modifies | Test |
|---|---|---|---|
| GAE-3c | Convergence monitoring + failure modes | `routers/gae.py` | Alternating outcomes → instability warning shown. |

**Post-sprint gate:** 10-cycle compounding verification (§8). If it passes → TAG v4.1. ✅

---

## 8. End-to-End Compounding Verification (Post-Sprint Gate) ✅

This is the canonical 10-cycle test that proved the compounding mechanism before the v4.1 tag. Every subsequent sprint uses this as the regression baseline — if this fails after any change, the causal compounding chain is broken.

```
SETUP: Fresh graph seed. Learning state reset to priors.

CYCLE 1 — BASELINE:
  Analyze ALERT-7823 (travel_anomaly).
  Record factors_1, scores_1, confidence_1.
  Verify:
    - Decision node created in Neo4j with f(t) stored
    - PatternHistory factor = 0.5 (symmetric prior — <5 decisions)
    - action_probabilities sum to 1.0

CYCLE 2 — FIRST FEEDBACK:
  Submit outcome: correct.
  Verify:
    - f(t) read from graph (R4 — not recomputed)
    - Centroid updated: μ[travel_anomaly, action, :] has moved toward f(t)
    - Decision node marked correct
    - GraphMutated event emitted

CYCLE 3 — ACCUMULATION:
  Analyze ALERT-7824 (travel_anomaly, different user).
  Verify:
    - PatternHistory finds 1 resolved Decision for travel_anomaly
    - scores_3 ≠ scores_1  ← THE COMPOUNDING PROOF
    - PatternHistory factor > 0.5

CYCLES 4–8: Submit correct outcomes for 5 more travel_anomaly alerts.
  Verify after each:
    - PatternHistory value increases monotonically
    - Centroid drift ‖μ_after − μ_before‖ > 0 each update
    - confidence trend upward for correct-action alerts

CYCLE 9 — COMPOUNDING VISIBLE:
  Analyze ALERT-7823 again (same alert as Cycle 1).
  Verify:
    - PatternHistory ≈ 1.0 (7 correct / 7 total decisions on travel_anomaly)
    - confidence >> Cycle 1 confidence
    - Tab 4 learning curve shows real upward trend (not hardcoded)

CYCLE 10 — TRUST ASYMMETRY:
  Submit outcome: incorrect.
  Verify:
    - Centroid update magnitude >> correct update (20:1 penalty_ratio)
    - action confidence drops noticeably on re-analyze
    - The system treats false suppression as 20× more costly than false escalation
```

**Pass criteria:** All verification assertions hold. Categories learn at different rates
after Cycles 1–8 (because PatternHistory is category-scoped). Trust asymmetry is measurable.

**If this passes, the system compounds. If any step fails, a causal link is broken.**
✅ Passed at v4.1 tag.

> **v5.3 note (ProfileScorer):** From v5.0 onward, the scoring mechanism is ProfileScorer
> (Eq. 4-final, L2 distance). The 10-cycle test still applies with one change:
> Cycle 1 verification reads `profile_scorer.centroids[c, :, :]` instead of W.
> Cycle 2 verification checks `‖μ_after − μ_before‖ > 0` instead of `‖W_after − W_before‖ > 0`.
> All other assertions are identical. The compounding mechanism is unchanged — only the
> geometric representation changes (L2 distance to centroids vs. dot product with W).

> **v5.3 note (random baseline):** Baseline for 5-action system (A=5, v5.3) is 20%,
> not 25%. Chart annotations in Tab 4 should reflect this.

---

## 9. v4.5 Scope — "Make It Real" ✅ TAGGED

### 9.0 Guiding Principle

v4.5 closed the credibility gaps between published blog claims and live product proof.
Three phases executed: Phase A and B completed fully, Phase C deferred to experiment-first
validation. HC-1 added healthcare domain breadth.

**The v4.5 theme:** "After ten thousand decisions — show me how your system got smarter."
Every capability built in v4.5 was chosen to make the learning mechanism *visible* to a
CISO or technical evaluator during a 20-minute live walkthrough.

### 9.1 v4.5 Structure

```
GAE Preamble (2 prompts, GAE repo)    ← CalibrationProfile + per-factor decay
        ↓
Phase A: Simulation Mode (6 prompts)  ← "After ten thousand decisions" proof
        ↓
Phase B: CISO Readability (4 prompts) ← Investigation narrative + Tab 2 rewire
        ↓ [Loom v2 recording — pending]
Phase C: Cross-Graph Discovery        ← PERMANENTLY RETIRED — see §29 (Part 2)
HC-1: Healthcare Domain (1 prompt)    ← Domain extensibility breadth
```

**Phase D from v1 (Docker/VPS) eliminated from v4.5 scope:**
- Docker/VPS deferred to v5.5 (now v5.5-R9 — see §10.6 in Part 1)
- Kept v4.5 focused on product capability, not distribution

### 9.2 GAE Preamble (GAE Repo — 2 prompts) ✅ COMPLETE

See `gae_design_v10` for full prompt specs (GAE-CAL-1, GAE-CAL-2).

**Why this comes first:** Phase A's simulation mode exercises the learning loop 50+ times.
CalibrationProfile and per-factor decay must be in place before simulation makes them
visible. Running 50 decisions through uniform decay and then changing decay semantics
forces re-validation — so preamble runs first.

**SOC copilot impact after GAE preamble:**
- `domains/soc/config.py`: `SOCDomainConfig.get_calibration_profile()` returns calibration profile
- `services/gae_state.py`: LearningState constructed with profile from DomainConfig
- `routers/triage.py`: `score_alert()` reads `temperature` and `penalty_ratio` from CalibrationProfile

### 9.3 Phase A: Simulation Mode + Alert Corpus (6 prompts) ✅ COMPLETE

**Gap closed:** GAP-1 (no simulation mode), GAP-2 (no ATT&CK), GAP-3 (limited alert corpus)

| Prompt | Scope | Creates/Modifies | Gate |
|---|---|---|---|
| **SIM-FIX** | TD-026 fix — atomic reset | `services/state_manager.py`, audit store | Soft reset: GAE + audit + Neo4j outcomes clear atomically |
| **SIM-1** | SimulationOrchestrator backend | `services/simulation.py`, `routers/simulation.py` | 10-decision API test passes |
| **SIM-2** | Frontend simulation panel | `SimulationPanel.tsx` or integration in existing tab | Real-time chart updates during simulation. Category learning curve. |
| **SIM-3a** | Alert pool expansion — 15–20 alerts | `domains/soc/alerts/`, seed data expansion | 5 categories × 3–4 alerts each. Each category activates different dominant factors. |
| **SIM-3b** | Alert pool wiring — orchestrator uses expanded pool | `services/simulation.py`, `routers/simulation.py` | Simulation runs across all categories. PatternHistory differentiates by category. |
| **SIM-4** | ATT&CK technique IDs on all alerts | Alert definitions, Tab 3, Tab 1 | T1078, T1566.001, T1021.001, T1567, T1048 visible in UI |

**Phase A Gate: ✅ PASSED.** 50-decision simulation shows clear learning in charts. Category learning curve shows per-category accuracy divergence across 6 categories (including healthcare). Weight evolution chart shows meaningful progression.

### 9.3a HC-1: Healthcare Domain (1 prompt) ✅ COMPLETE

Added after Phase A to demonstrate domain extensibility beyond cybersecurity.

| Item | What Was Built |
|---|---|
| **5 healthcare alerts** | SIM-HC-001 (PHI access anomaly), SIM-HC-002 (medical device scan), SIM-HC-003 (Health-ISAC IOC match), SIM-HC-004 (credential stuffing), SIM-HC-005 (EHR lateral movement) |
| **Neo4j seed data** | 3 healthcare users, 3 healthcare assets, PHI DataClass, 2 Health-ISAC ThreatIntel nodes |
| **Simulation** | healthcare category added (oracle_rate=0.65), 6th line in category learning curve |
| **ROI** | Healthcare preset: 50 alerts/day, 12 analysts, $95K, HIPAA/PHI note |
| **Verification** | `verify_seed_data.py`: 8 checks, standalone Neo4j verification |

> **v5.3/v5.5.3 note:** Healthcare remains a **simulation variant only** — it is not a
> production category and is NOT included in the C=6 production centroid tensor
> (shape (6,4,6), A=4 canonical as of v5.5.1). The 6th simulation category continues
> to serve its original purpose: demonstrating that the architecture is domain-generalizable
> without code changes. The S2P copilot (v6.5 demo) is the production second-domain proof
> — see §1.6 (Part 1). [Note: v5.3 original said C=5/(5,5,6) — corrected to C=6/(6,4,6)
> to reflect A=4 migration shipped in v5.5.1.]

### 9.4 Phase B: CISO Readability (4 prompts) ✅ COMPLETE

**Gap closed:** GAP-4 (no investigation narrative), TD-019 (dual decision paths), TD-020 (execute_action events)

| Prompt | Scope | What Was Built | Gate |
|---|---|---|---|
| **NAR-1** ✅ | NarrativeProvider protocol + implementations | `services/narrative.py`: TemplateNarrativeProvider, OllamaNarrativeProvider with graceful degradation. NarrativeContext dataclass. | Template generates for any alert. Calibration line present. |
| **NAR-2** ✅ | Tab 3 narrative panel | 3–5 sentence narrative with "Calibrated from N outcomes" line | Narrative appears with calibration count |
| **TAB2-1** ✅ | Rewire Tab 2 Runtime Evolution to GAE pipeline | `routers/evolution.py`: compute_factor_vector → score_alert → Decision node → events. GAE Scoring panel: 6 factor bars + action probability pills. **TD-019 CLOSED.** | Tab 2 uses GAE end-to-end |
| **TAB2-2** ✅ | AgentEvolver shows real GAE data | `services/evolver.py`: real decision_count, per-action weight norms. `execute_action()` emits DecisionMade + GraphMutated events. Honesty labels applied. **TD-020 CLOSED.** | No dual decision paths remain |

**Honesty labels applied in NAR-2 / TAB2-2 (H7 items 10–13, §28 in Part 2):**
- "Demo Deployment" runtime header
- "Demo data — live tracking in v5.0" in audit timeline
- "Illustrative" on threat landscape section
- "Projected" on economic impact section

**Phase B Gate: ✅ PASSED.** Tab 2 GAE end-to-end. Investigation narrative with calibration line. No dual decision paths. Honesty labels on all hardcoded data.

### 9.5 Phase C: Cross-Graph Discovery → **PERMANENTLY RETIRED**

See §29 (Part 2) for full experiment results. Summary:

- **LLM judge panel** (GPT 5.3, Opus, Grok): unanimous — don't implement Eq. 6 as-is.
- **25 experiments executed.** Root cause (dot product kernel, 61% accuracy) identified and fixed.
- **G (Gating Matrix) falsified** — +0.01pp best case. Not worth implementing.
- **ProfileScorer (L2 distance) confirmed** — 97.89% zero-learning, 98.2% with learning.
- **Phase C prompts (DISC-1 through GATE-B3) permanently retired.** Not deferred.
- **Replacement:** v5.0 implements ProfileScorer (§10–10.6 in Part 1). Discovery → v6.0+.

### 9.6 v4.5 Prompt Totals (Actual)

| Phase | SOC Prompts | GAE Prompts | Status |
|---|---|---|---|
| GAE Preamble | 0 | 2 | ✅ Complete |
| Phase A (Simulation) | 6 | 0 | ✅ Complete |
| Phase B (Narrative) | 4 | 0 | ✅ Complete |
| HC-1 (Healthcare) | 1 | 0 | ✅ Complete |
| Phase C (Discovery) | 0 | 0 | **RESOLVED — see §29 (Part 2)** |
| **v4.5 Executed** | **11** | **2** | **13 total** |

---

## Master Section Index — v5.5 (All Three Parts)

Use this table to locate any section across the three part files.

| Section | Title | Part | Status |
|---|---|---|---|
| §1 | Architecture — Three-Repo Stack | Part 1 | v5.6 (527/532+120/102 tests) |
| §1.4 | Architecture Philosophy — Bridge, Compiled Ontology, Three Computational Levels, Two Levels of Institutional Judgment, **ACCP Bounded Hyperagent (Loop 1/2/3 mapping), Three Write Sources (W1/W2/W3), Three Phase 3 Design Gaps (H1/H2/H3) (NEW v5.5.3)** | Part 1 | v5.5.3 |
| §1.5 | Product Identity | Part 1 | v5.3 |
| §1.6 | S2P Co-Design Constraints | Part 1 | v5.3 (TD-036 CLOSED) |
| §2 | Directory Structure | Part 1 | v5.4 |
| §3 | Imports from GAE | Part 1 | v5.4 |
| §4 | Build History + Canonical Numbers | Part 1 | v5.6 (CLAIM-59/62/64/CL-ECON-MEASURED in §4.4) |
| §5 | SOC Factor Implementations | Part 1 | v5.5.3 (two PatternHistory read paths; §5.6 NEW) |
| §5.6 | **PatternHistoryFactorComputer — W2 Flywheel Read Path (NEW v5.5.3)** | **Part 1** | **v5.5.3 — CLAIM-W2 +10.13pp** |
| §6 | Decision & Outcome Write-Back | Part 1 | v5.4 |
| **§7** | **v4.1 SOC Copilot Prompts** | **Part 3** | ✅ Complete (v4.1) |
| **§8** | **End-to-End Compounding Verification** | **Part 3** | ✅ Complete (v4.1) |
| **§9** | **v4.5 Scope — "Make It Real"** | **Part 3** | ✅ Complete (v4.5) |
| §10 | v5.0 Scope | Part 1 | v5.5 (v5.0 TAGGED) |
| §10.6 | v5.5 Scope — Fully Specified (R1–R13) | Part 1 | v5.3 |
| §11 | Product Flow | Part 1 | v5.3 |
| §12 | Build Sequence | Part 1 | v5.3 |
| §13 | Claude Code Rules | Part 1 | v5.5.3 (W2 read path invariants, PatternHistoryFactorComputer) |
| §14 | SOCDomainConfig | Part 1 | v5.5.3 (shape (6,4,6), A=4, PatternHistoryFactorComputer in get_factor_computers()) |
| **§15** | **Simulation Mode** | **Part 2** | v5.2 preserved |
| **§16** | **NarrativeProvider** | **Part 2** | v5.2 preserved |
| **§17** | **Reset Semantics** | **Part 2** | v5.2 preserved |
| **§17.5** | **Rollback Execution Specification (TD-033)** | **Part 2** | v5.4-final AUTHORITATIVE |
| **§18** | **ATT&CK Integration** | **Part 2** | v5.5 (TD-036 CLOSED) |
| **§19** | **Category Learning Curve** | **Part 2** | v5.2 preserved |
| **§20** | **v4.5 Prompt Specifications** | **Part 2** | ✅ Complete |
| §21 | Shadow Mode — Full Specification | Part 1 | v5.3 |
| §22 | Institutional Knowledge Score (IKS) | Part 1 | v5.5.3 (IKS anchor separation: standard μ₀=anchor, enriched μ₀=live start) |
| §22.6 | Referral Routing Architecture — ReferralRules R1-R7 (NEW v5.5.2) | Part 1 | v5.5.2 |
| **§22.7** | **Three-Signal Monitoring Architecture — Circuit Breaker + Flywheel Health Monitor (CLAIM-OLS-01) + Analyst Contribution Monitor. Var(q) PERMANENT HARD STOP. (NEW v5.5.3)** | **Part 1** | **v5.5.3** |
| §23 | NL Template Engine (24 templates) + §23.4 Similar Past Cases + §23.5 LLM Judge Rubric | Part 1 | v5.4-final AUTHORITATIVE |
| §24 | SemanticRegistry — concepts.yaml + queries.yaml | Part 1 | v5.3 |
| §25 | Enterprise Integration Hooks | Part 1 | v5.3 |
| §26 | Feature Gap Closure Map | Part 1 | v5.6 (April 5-6 completions table added) |
| §27 | Experiment Landscape | Part 1 | v5.6 (~295 experiments, Batch G results) |
| **§28** | **Response Data Realism (H7)** | **Part 2** | v5.2 §21 renumbered |
| **§29** | **Phase C — RESOLVED** | **Part 2** | v5.5.3 (§29.5 TD-035 CLOSED, §29.6 item 8 Phase 1 findings) |
| **§30** | **Feature Gaps F1–F15** | **Part 2** | v5.6 (F9 ✅ DONE April 6, §29.6 item 9 added) |
| Appendix A | Version History | Part 1 | v5.6 (v5.6 row added: Phase 3 ✅, April 5-6 completions) |
| Appendix B | Technical Debt (TD-001 – TD-039) | Part 1 | v5.6 (BACKLOG-003/004/007/009/020 CLOSED April 6) |
| Appendix C | Superseded Documents | Part 1 | v5.3 |

### Key Files by Task

| Task | Read First | Then Read |
|---|---|---|
| **Starting v5.5 sprint** | §13 (rules) in Part 1 | §10.6 (R1–R13 scope), §4 (PROD-3/PROD-4 first actions), §14 (config) in Part 1 |
| Implementing Shadow Mode | §21 in Part 1 | §13 rules, §6 write-back in Part 1 |
| Implementing IKS | §22 in Part 1 | §4 (canonical numbers), §6.4 (ProfileSnapshot hook) in Part 1 |
| Implementing NL templates | §23 in Part 1 | §16 (NarrativeProvider distinction) in Part 2 |
| Building Tab 5 | §24 in Part 1 | §21 (shadow), §22 (IKS), §23 (templates) in Part 1 |
| Enterprise integration | §25 in Part 1 | §13 (enterprise rules) in Part 1 |
| Running experiments | §27 in Part 1 | `experiments_catalog_v8` (Parts 1/2/3, outputs) |
| Understanding feature gaps | §26 (closure map) in Part 1 | §30 (full F-table) in Part 2 |
| Understanding what was built | §7–9 in Part 3 | §20 (v4.5 prompts) in Part 2 |
| Debugging scoring issues | §14 (SOCDomainConfig) in Part 1 | §5 (factors), §6 (write-back) in Part 1 |
| S2P co-design check | §1.6 in Part 1 | s2p_copilot_design_v0.2 §8–9 (TD-036 CLOSED — `by_category` already shipped) |
| Reset / rollback | §17.5 in Part 2 (authoritative) | §6.4 (checkpoint creation), §14 (get_checkpoint_config) in Part 1 |
| Architecture philosophy | `architecture_philosophy_v4.1.md` (outputs) — ACCP bounded hyperagent, three write sources, three Phase 3 design gaps (H1/H2/H3) | `compounding_intelligence_v7_part1.md` (Five-Layer), `compounding_intelligence_v7_part3.md` (Bridge, Compiled Ontologies) |
| Two levels of institutional judgment | §1.4 in Part 1 | `gae_design_v10.md` §5 (GAE owns Level 1) |

---

*SOC Copilot — Design Document v5.6 (Part 3 of 3) | April 6, 2026*
*Sections §§7–9: v4.1 SOC prompt sequence, 10-cycle compounding verification, v4.5 "Make It Real" (all ✅ COMPLETE).*
*These are the executed foundation. v5.0 builds on them — it does not revisit them.*
*Master Section Index updated to v5.6: §4.4 canonical numbers, §26/27/30 Appendix A/B updated.*
*Phase 0 ✅ Phase 1 ✅ Phase 2 ✅ Phase 3 Priority 1 ✅. 527/532+120/102 tests. ~295 experiments.*
*CLAIM-59: 54.4% faster (p<0.0001). CLAIM-62: +42.69pp. CLAIM-64: r=0.9669. CL-ECON-MEASURED: 30.85 min/alert.*
*All 11 innovations validated. Innovations 7 and 10 gaps CLOSED. Var(q) gating: PERMANENT HARD STOP.*
*BACKLOG-003/004/007/009/020 CLOSED April 6. architecture_philosophy_v4.1.md current authority.*
*"The distance metric compounds. The W2 flywheel is real. The graph compounds while centroids wait."*

---

## v5.8 Addendum — Framework v4 Integration

*All v5.7 content preserved above. The following sections specify how framework v4 capabilities manifest in the SOC copilot product. Cross-reference with gae_design v10.8 (engine implementation) and framework v4 (mathematical foundation).*

### §9.1 Addendum: Eq. 4-twophase (TwoPhaseStrategy Scoring)

```
P(a | f, c) = softmax(-(f − μ[c,a,:])ᵀ W̃ (f − μ[c,a,:]) / τ)

where W̃ = diag(w̃₁, ..., w̃_D)
      w̃ᵢ = α × w_DK_i + (1 - α) × 1.0

At α=0 (Phase 1 or ContinuousStrategy): W̃ = I. Reduces to existing scoring.
At α=0.5 (Phase 2, default shrinkage): interpolates DK with uniform. Quadric boundaries.
```

**w̃ vs P28 weights:** P28 weights come from deployment qualification (static, one-time). DK precision weights come from accumulated decisions via coordinate descent (dynamic, ongoing). When TwoPhaseStrategy Phase 2 is active, w̃ REPLACES P28 weights.

**Backward compatibility:** ContinuousStrategy (default): α=0 always, Eq. 4-diagonal unchanged. ProfileScorer.for_soc() → ContinuousStrategy. ProfileScorer.for_soc_twophase() → TwoPhaseStrategy (NEW).

### §10.3 Addendum: LearningStatePanel (Tab 3)

When TwoPhaseStrategy is active, Tab 3 scoring detail panel shows:

```
┌─ Learning State ──────────────────────────────────────────┐
│  Phase: ● Phase 2 — Learning dimensional importance       │
│  Shrinkage α: ████████░░ 0.50                            │
│  Novelty rate: 34% ▁▂▃▅▃▂▁ (last 200 decisions)         │
│                                                           │
│  [▸ Dimensional Importance] (expandable)                  │
│     severity:        ████████████ 3.2 (HIGH)              │
│     device_trust:    ██           0.5 (LOW)               │
│     user_anomaly:    ██████       1.5 (MODERATE)          │
│     asset_crit:      █████████    2.8 (HIGH)              │
│     cloud_indicator: █            0.3 (LOW)               │
│     pattern_history: ████████     2.1 (HIGH)              │
└───────────────────────────────────────────────────────────┘
```

**When ContinuousStrategy active:** LearningStatePanel is HIDDEN entirely. Tab 3 identical to v5.7.

**Endpoint:** GET /api/triage/learning-state?category={category}
Returns: phase, alpha, novelty_rate, dk_weights (A×D array or null), freeze_point, decisions_since_freeze, batch_pipeline status.

**Frontend component:** LearningStatePanel in AlertTriageTab.tsx. Collapsed by default (phase + α shown). Expands to show DK weights and novelty sparkline.

### Tab 4 Addendum: Three-Channel Decomposition

New section below existing compounding trajectory in Tab 4:

```
┌─ Three Channels of Improvement ───────────────────────────┐
│  ERROR BUDGET                                              │
│  ████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│  ▲ Addressed (+5.2pp)  ▲ Remaining (~4.8pp)  ▲ Irred.     │
│                                                            │
│  Channel 1 (Scorer): +3.4pp ████████                      │
│    DK precision weights from 1,847 decisions.              │
│  Channel 2 (Graph):  +1.8pp ████                          │
│    12,177 nodes. Factor precision improving.               │
│  Channel 3 (Labels): not active                            │
│    Enable LLM-as-Judge for +3-4pp additional.              │
│  TOTAL: +5.2pp over expert prior                           │
└────────────────────────────────────────────────────────────┘
```

**IMPORTANT:** Channel contributions are ESTIMATES from simulation calibration. Tooltip: "Estimated from simulation. Actual contributions depend on deployment noise, factor quality, and volume."

**Endpoint:** GET /api/compounding/channel-decomposition
Returns: per-channel label/contribution_pp/status/description, total_improvement_pp, irreducible_pp, remaining_boundary_pp.

**When ContinuousStrategy active:** Channel 1 shows centroid learning only (no DK). Channels 2/3 unchanged.

### Tab 2 Addendum: Conservation q Label

Conservation display updated: q = "rolling verified accuracy (last 400 decisions)" — not "confidence" or "override quality."

### §11 Addendum: Triage Flow — Batch Pipeline Position

Under TwoPhaseStrategy, the triage update step changes:

**Phase 1 (MEAN_CONVERGENCE):**
→ ProfileScorer.update() → centroid update (unchanged from v5.7)
→ PhasePolicy checks: should this (c,a) pair freeze?
→ If freeze triggered: pair transitions to VARIANCE_LEARNING. Centroids locked permanently. Buffering begins.

**Phase 2 (VARIANCE_LEARNING):**
→ ProfileScorer.update() → decision BUFFERED (no centroid change)
→ NoveltyTracker computes d_nn
→ If novelty accumulator > threshold: batch pipeline triggers (composition check → coordinate descent → promotion gate → deploy or reject)
→ Decision write-back to graph (unchanged — ALWAYS writes regardless of phase)

The batch pipeline runs INSIDE ProfileScorer. SOC copilot calls update() as before; the scorer handles phase logic internally.

### §11.5 Addendum: Demo Flow — Phase Transition

Shadow mode (N=0 to ~200): Phase 1 for all categories. Centroids adjusting. α=0. Tab 3: "Phase 1 — Learning class positions."

Phase transition (N ≈ 200 per category): High-volume categories transition first. Tab 3: "Phase 2 — Learning dimensional importance."

Live mode (N > 200, ongoing): DK weights learning. Batch pipeline running. Tab 3: phase, α, DK weights, novelty.

NOTE: Shadow→live and Phase 1→Phase 2 are INDEPENDENT transitions.

### §5.1 Addendum: Factor DK Weight Relationship

Under TwoPhaseStrategy Phase 2, each factor's contribution to scoring is weighted: w̃ᵢ = α × w_DK_i + (1-α). DK weights are classification-optimal importance scores (NOT P28 σ measurements). At α=0.5 default, a factor with w_DK=3.0 contributes 2.0× vs one with w_DK=0.5 (0.75×). Automatic feature selection — the scorer discovers which factors matter for each category.

### §14 Addendum: SOCDomainConfig.get_learning_strategy()

```python
@staticmethod
def get_learning_strategy() -> Optional[str]:
    """Returns None for ContinuousStrategy (default).
    Returns 'two_phase' for TwoPhaseStrategy.
    Configurable per deployment. Enable via deployment config."""
    return None  # Default: ContinuousStrategy
```

### §13 Addendum: Claude Code Rules — Framework v4

- TwoPhaseStrategy is opt-in. ContinuousStrategy default. Do NOT change without instruction.
- scorer.get_phase() returns 'MEAN_CONVERGENCE' or 'VARIANCE_LEARNING' only.
- scorer.get_dk_weights() returns ndarray (A,D) or None. None = ContinuousStrategy.
- DK weights are "dimensional importance" or "DK precision weight" — NOT "inverse variance" or "1/σ²."
- Batch pipeline is internal to ProfileScorer. SOC copilot observes via get_phase/alpha/dk_weights/novelty_rate.
- Conservation q = rolling verified accuracy (already v10.7 definition).

### §4.4 Addendum: Canonical Numbers — Framework v4

| Metric | Value | Source |
|---|---|---|
| DK improvement (N=500) | +3.2pp | REPARAM-2, 3 seeds |
| DK improvement (N=4000) | +5.4pp | REPARAM-2, 3 seeds |
| Shrinkage safety (α=0.5) | 0/21 below centroid | RATE-9, 3 seeds |
| DK effective dim reduction | ~5.5 → ~4.0 | LIFTING experiment |
| Phase 1 contribution to DK | 0.3pp | FOUNDATION |
| DK at random centroids | +52pp | FOUNDATION |
| DK gain at 5% noise | +1.5pp | DK-NOISE |
| DK gain at 50% noise | +8.1pp | DK-NOISE |

### §30.2 Addendum: Feature Table — Framework Features

| ID | Feature | Architecture | Version | Priority | Status |
|---|---|---|---|---|---|
| **F16** | Phase-aware scoring display | Tab 3 LearningStatePanel: phase, α, DK weights, novelty | v5.8 | HIGH | Spec (this doc) |
| **F17** | Three-channel decomposition | Tab 4 channel contribution panel | v5.8 | HIGH | Spec (this doc) |
| **F18** | Batch pipeline observability | Promotion history, rollback status | v6.0 | MED | Depends on FW-07 |

### §1.5 Addendum: Product Identity — Phase 2 Visibility

v5.8 makes the scorer's learning VISIBLE. Tab 3 shows which phase each category is in, how much the system trusts its learned weights (α), and which dimensions it considers most important. Tab 4 shows how three independent channels contribute to overall improvement. The analyst can see the system getting smarter — not just the centroid drifting, but the scorer concentrating on the factors that matter.

### New Endpoints Summary

| Endpoint | Method | Returns | Auth |
|---|---|---|---|
| /api/triage/learning-state | GET | phase, alpha, novelty_rate, dk_weights, batch_pipeline | Same as triage |
| /api/compounding/channel-decomposition | GET | per-channel contributions, error budget, total improvement | Same as compounding |

### Implementation Estimate

Backend: ~40 lines (2 endpoints + scorer integration). Frontend: ~160 lines (2 components). Tests: ~60 lines. Total: ~260 lines. ~2 days (FW-10 in MAP v5.51).

### Cross-References

- Framework v4 §2.2 → §9.1 Eq. 4-twophase
- Framework v4 §3.4 → Tab 4 decomposition
- Framework v4 §3.6 → §11 triage flow
- gae_design v10.8 §9.10-12 → ProfileScorer integration
- MAP v5.51 FW-10 → this spec

---

*SOC Copilot Design v5.8 · April 29, 2026*
*Framework v4 integration. 2 new endpoints. 2 new UI panels. 3 new feature IDs.*
*Zero existing behavior changes. ContinuousStrategy = default. ~260 lines, ~2 days.*
*~2,340 tests. 995 GAE. 900 SOC. 183 E2E. 174 ci-platform. ~295 experiments.*

