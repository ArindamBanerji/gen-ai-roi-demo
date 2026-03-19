# SOC Copilot — Technology Scorecard & Gap Analysis

**Consolidated Report v4**

| | |
|---|---|
| **Date** | February 28 – March 1, 2026 |
| **Version** | 4.0 (v3 + PM session outcomes: research gaps, data collection, error-driven discovery) |
| **Trigger** | v4.1 tagged. PM session complete. v4.5 prompts finalized with instrumentation. |
| **Status** | v4.1 tagged. v4.5 GAE preamble ready to execute. Math quality identified as critical success factor. |
| **Audience** | Internal engineering, investor due diligence, strategic planning |
| **Source Documents** | Technology Scorecard v1.1, Blog Claims Gap Analysis v1, Session Notes, design_decisions_v1.md, PM session notes (March 1, 2026) |

> **Changes from v3 → v4:**
> (1) **3 research gaps added (R1-R3).** Convergence ≠ correctness, math-algorithm integration, error-driven discovery. These are open questions, not engineering tasks.
> (2) **Data collection instrumentation** noted for SIM-1, SIM-2, SIM-3a, NAR-2. Simulation is experimentation platform.
> (3) **Phase C prerequisite added.** Error-driven discovery design session before DISC prompts. Current Eq. 6 may need revised objective function.
> (4) **Math quality as CSF.** GAE math must produce demonstrably better decisions than system without it. This frames all v4.5+ work.
> (5) **Gap count: ~50** (was 47 in v3). +3 research gaps.

---

## Executive Summary

This report consolidates three assessments conducted at the v4.1 milestone to establish an honest baseline before v4.5 planning. It combines the technology capability scorecard (26 gap items), a blog-claims-vs-implementation audit (three published blogs), and session-level engineering notes into a single reference document. Updated with outcomes from the PM session (March 1, 2026).

**What v4.1 Actually Proved (Solid Ground)**

- **Axis 2 (Context Fine-Tuning)** — live, measured, visible
- **Eq. 1, 4, 4b, 4c, 5** — implemented and tested
- **20:1 asymmetric trust** — 28.6x measured in gate test
- **Domain-agnostic** — 177 tests across 4 domains

**The Five Critical Gaps** (unchanged from v3)

1. **Simulation mode (CRITICAL)** — Every blog opens with "after ten thousand decisions." Demo shows 5 manual decisions. A "Run 50 Decisions" button transforms claim to proof. 6 prompts.

2. **ATT&CK alignment (HIGH)** — Table stakes. Every competitor has it. We have zero. 1 prompt.

3. **Alert corpus (HIGH)** — 5 alert types looks rigged. Need 15–20 across 5 categories. 2 prompts.

4. **Investigation narrative (HIGH)** — CISOs expect plain English; we show bar charts. Key line: "calibrated from 12 verified outcomes." 2 prompts.

5. **Cross-graph discovery / Axis 3 (CRITICAL but HARD)** — CI blog's marquee claim. Eq. 6–9 completely unbuilt. 6 prompts with honest gate. **v4 update:** error-driven discovery design session required before implementation.

**Three Research Gaps (NEW in v4)**

These are not engineering tasks with known solutions. They are open questions requiring experimentation.

| ID | Research Question | First Data | Full Answer |
|---|---|---|---|
| R1 | Does Hebbian update converge to correct decisions, or just stable ones? | v4.5 Phase A (ground_truth comparison) | v5.0 evaluation (EVAL-1) |
| R2 | How much do the 3 algorithmic loops contribute vs. the GAE math? | v5.0 ablation (GAE-ABL-1) | Ongoing experimentation |
| R3 | Should cross-graph discovery be error-driven (find what's missing from wrong decisions) rather than similarity-driven (find similar entities)? | Design session before Phase C | v5.5+ implementation |

**Critical Success Factor (NEW in v4):** The GAE math must produce demonstrably better decisions than a system without it. The three algorithmic loops (SituationAnalyzer, AgentEvolver, ReinforcementGovernor) add value heuristically but are not mathematically formalized. Whether the right path forward is more loops, more math, or a unified framework is an open question that v5.0 ablation will begin to answer.

**Scorecard Headline**

**22 of 26 capability gaps closed or mostly closed (85%).** 10/10 CRITICALs addressed. All remaining opens are MEDIUM priority. Beneath the scorecard: 6 hidden engineering gaps, 4 architectural limitations, 3 unknowns requiring experiments, 3 interaction effects, 5 engine gaps from the open-source decision, 7 design gaps from the design decisions session, and 3 research gaps from the PM session.

**Redesigned v4.5 Roadmap (19 prompts + 2 reviews, 3 phases + cleanup)**

> v4 update: Phase B split (narrative vs Tab 2 rewire). HC-1 added. Data collection instrumentation on 4 prompts. 12 execution units to Loom v2 readiness.

- **GAE Preamble** (2 prompts + review): CalibrationProfile + per-factor decay
- **Phase A** (6 prompts + review): Simulation + alerts + ATT&CK + instrumentation
- **Phase B** (2 prompts): Narrative only
- **HC-1** (1 prompt): Healthcare polish (deprioritized)
- **Tab 2 Rewire** (2 prompts): Tech debt cleanup (deferred within v4.5)
- **Phase C** (6 prompts): Cross-graph discovery — gated, requires design session first

---

## PART 1: Blog Claims vs. Implementation

Each of the three published blogs was audited line-by-line against the v4.1 codebase. Every claim is scored as built (✅), partially built, or not implemented (❌).

### Blog 1: CI 4.0 — "How Enterprise AI Develops Self-Improving Judgment"

| **Claim** | **Built?** | **Gap** |
|---|---|---|
| Three axes of compounding | Axis 2 proved. Axis 1 partial. Axis 3 not built. | **HIGH** |
| Weight calibration from verified outcomes (Eq. 4) | ✅ GAE scoring + learning pipeline | — |
| 20:1 asymmetric trust | ✅ 28.6x measured in gate test | — |
| Cross-graph discovery creates new scoring dimensions | ❌ Not implemented | **CRITICAL** |
| Four dependency-ordered layers (UCL → AE → ACCP → Copilots) | Architecture exists conceptually. UCL not built. AE partial. | **HIGH** |
| Singapore + CFO + threat spike scenario | ❌ Not implemented — blog's marquee example | **CRITICAL** |
| "System develops institutional judgment" | Partially — weight learning proves it for Axis 2. No Axis 3. | **MEDIUM** |
| Agent evolves operational artifacts at runtime | Tab 2 AgentEvolver exists but uses old path (not GAE) | **MEDIUM** |

### Blog 2: Math Foundation — "Cross-Graph Attention with Experimental Validation"

| **Equation** | **Built?** | **Gap** |
|---|---|---|
| Eq. 1: Scaled dot-product attention | ✅ gae/primitives.py | — |
| Eq. 2: Multi-head attention formula | ❌ Not in GAE library (design only) | LOW |
| Eq. 3: Residual connections | ❌ Not in GAE library | LOW |
| Eq. 4: Scoring matrix = single-query attention | ✅ gae/scoring.py score_entity() | — |
| Eq. 4b/4c: Hebbian weight update + asymmetry | ✅ gae/learning.py | — |
| Eq. 5: Convergence proof | ✅ gae/convergence.py | — |
| Eq. 6: Cross-graph entity discovery | ❌ Not implemented | **HIGH** |
| Eq. 7: Discovery relevance scoring | ❌ Not implemented | **HIGH** |
| Eq. 8: Discovery threshold function | ❌ Not implemented | **HIGH** |
| Eq. 9: Multi-domain multi-head attention | ❌ Not implemented | **HIGH** |
| Experiment 1: Scoring convergence | ✅ 7/7 gate test | — |
| Experiment 2: Cross-graph discovery F1 | ❌ Not implemented | **HIGH** |
| Experiment 3: Super-quadratic scaling | ❌ Not implemented | **HIGH** |
| Experiment 4: Sensitivity landscape | ❌ Not implemented | **MEDIUM** |

### Blog 3: Demo Blurb v3.1 — "After ten thousand decisions..."

| **Claim** | **Built?** | **Gap** |
|---|---|---|
| "Fourteen of twenty-one capabilities" | Needs recount after v4.1 | LOW |
| Six-factor breakdown | ✅ Real GAE factors with Cypher traversal | — |
| Live Pulsedive connector | ✅ Phase 1 connectors | — |
| Policy conflicts detection | ✅ Tab 3 | — |
| Quality gates (eval gates) | ✅ Tab 2 | — |
| Evidence ledger with SHA-256 | ✅ Real audit trail | — |
| Three learning loops | Loop 1 ✅, Loop 2 partial, Loop 3 ✅ | **MEDIUM** |
| "Alert ten thousand is triaged with more intelligence" | ✅ NOW PROVED with live charts | — |
| MITRE ATT&CK language | ❌ Zero ATT&CK references in demo | **HIGH** |
| "After ten thousand decisions" | Can only show 5–10 manual decisions. No simulation mode. | **HIGH** |

---

## The Five Critical Gaps (Detailed)

### Gap 1: No Real-Time Simulation Mode

**Severity: CRITICAL** | Affects ALL blog claims | Design difficulty: LOW–MEDIUM

**The problem:** Every blog opens with "after ten thousand decisions." The demo requires manual click-through: analyze → execute → feedback × N. At 2 minutes per decision, showing 10 decisions takes 20 minutes. Showing meaningful compounding (50+ decisions) is impossible in a live demo.

**What's needed:** An "Auto-Pilot / Run Simulation" button that processes N alerts automatically (configurable: 10, 25, 50, 100), cycles through different alert types, auto-selects action from GAE scoring, auto-generates outcomes (configurable correctness rate), updates compounding charts in real-time via WebSocket, and shows the learning curve building over 30–60 seconds.

**Why this matters:** This single feature transforms the demo from "trust me, it compounds" to "watch it compound in front of you." It's the difference between a claim and a proof.

### Gap 2: ATT&CK Alignment

**Severity: HIGH** | Credibility table stakes | Design difficulty: LOW

**The problem:** Every competitor speaks ATT&CK. CrowdStrike scored 100% on MITRE 2025 eval. Torq's Socrates auto-maps. Our demo has zero ATT&CK language. CISOs notice this immediately.

**What's needed:** Each alert carries a MITRE technique ID (T1078, T1566.001, etc.). Situation classifier references ATT&CK in output. Tab 3 shows technique + tactic alongside factor breakdown. Tab 1 can group/filter by tactic.

### Gap 3: Realistic Alert Corpus

**Severity: HIGH** | Demo variety | Design difficulty: MEDIUM

**The problem:** ~5 alert types, mostly travel logins. Real SOCs see phishing, lateral movement, cloud misconfigs, insider threats daily. With one dominant type, the six-factor breakdown looks rigged.

**What's needed:** 15–20 alerts across 5 categories: Travel/VPN anomaly, Credential/access, Threat intel match, Insider/behavioral, Cloud/infra. Each type activates DIFFERENT factors.

### Gap 4: Investigation Narrative

**Severity: HIGH** | CISO readability | Design difficulty: MEDIUM

**The problem:** Tab 3 shows quantitative factors (bar charts). CISOs expect plain-English investigation summaries. Every competitor produces them (Dropzone, Intezer).

> *ALERT-7823 classified as TRAVEL_ANOMALY (T1078). Graph traversal: 47 nodes. User jsmith has 14 prior travel logins from APAC — travel_match weight elevated to 0.23 (calibrated from 12 verified outcomes). Recommendation: false_positive_close at 91% confidence.*

**Key line:** "calibrated from 12 verified outcomes" — this is compounding proof in natural language.

> **v3 addition:** NarrativeProvider protocol (D5) — Ollama/Qwen default + template fallback. Local-first, no API key dependency. Graceful degradation.

### Gap 5: Cross-Graph Discovery / Axis 3

**Severity: CRITICAL** | The hardest problem | Design difficulty: HIGH

**The problem:** The CI blog's marquee claim is Axis 3 — capability extension. "Nobody programmed this rule. The system discovered it." The Singapore + CFO + threat spike scenario is completely unbuilt. Requires Eq. 6–9 from the math blog.

**What's needed:** Embedding-based entity comparison across graph domains, cross-graph attention sweep that discovers relationships, new scoring dimension (role_recency_risk) emerges from discovery, confidence drops from 89% → 34% for affected alerts, expand_weight_matrix() adds the new column to W.

**Assessment:** Attempt at v4.5 with honest gates. If embedding quality isn't sufficient, document as "designed and validated mathematically, production implementation requires [X]."

> **v3 update:** EmbeddingProvider protocol (from v6 addendum) with B3 gate F1 > 0.2. PropertyEmbeddingProvider (numpy-only, default) tested first. If fail: document honestly.

---

## Simulation Mode Design (Gap 1 — Most Impactful)

### Why This Is the #1 Priority

The simulation mode doesn't just close one gap — it transforms every gap already closed:

- Weight evolution chart: goes from 5 data points to 50+
- Trust curve: shows multiple drops and recoveries, not just one
- Confidence trajectory: shows clear convergence over time
- Before/after: dramatic improvement visible
- "Ten thousand decisions" claim: 50–100 decisions in 60 seconds

### Architecture

Three-layer design: Tab 4 simulation panel → backend SimulationOrchestrator → frontend real-time chart updates.

- **Tab 4 UI:** "Run Simulation" button with configurable decisions (10/25/50/100), correctness rate (70%/80%/90%), and speed (Fast/Medium/Slow).
- **Backend:** SimulationOrchestrator picks alerts from pool (rotating types), analyzes via GAE pipeline, auto-selects top action, generates outcome (Bernoulli), writes back to GAE learning, emits progress event. POST /api/simulation/run, GET /api/simulation/status.
- **Frontend:** Poll /status every 500ms, update charts incrementally, show progress bar (17/50), final summary comparison.

### Demo Flow

1. Open Tab 4 — empty charts, all placeholders
2. Click "Run 50 Decisions" (80% correct rate)
3. Watch: progress bar fills over 30 seconds
4. Watch: Weight Evolution bars grow in real-time
5. Watch: Trust curve builds — a few sharp drops, slow recoveries
6. Watch: Confidence trajectory lines climb
7. Simulation completes — before/after shows dramatic improvement
8. **The line:** "50 decisions. 30 seconds. Same model, same code. Watch the judgment develop."

### What the Simulation Proves

| **Claim** | **How Simulation Proves It** |
|---|---|
| "After ten thousand decisions" | 50–100 decisions visible, curve extrapolates |
| Weight calibration | W visibly different from initial |
| 20:1 asymmetry | Red spikes at incorrect decisions |
| Trust earns slowly | Gradual climb visible |
| Trust loses fast | Sharp drops visible |
| Recovery after error | Climb resumes after drop |
| Different alert types learn differently | Multiple lines in trajectory |
| Convergence → correctness (R1) | ground_truth_action comparison (NEW in v4) |

> **v4 addition: Data Collection Instrumentation.** The simulation is both a feature and an experimentation platform. Each decision logs a structured experiment record: `{alert_id, category, factor_vector, W_snapshot, predicted_action, confidence, oracle_outcome, correct}`. Alerts carry `ground_truth_action` and `dominant_factors` metadata. A "Download Experiment Log" button exports the full dataset for offline analysis. This data feeds v5.0 evaluation and ablation work.

---

## PART 2: Technology Capability Scorecard

Each of 26 gap items from the Technology Realization Gap Analysis is scored against five progressive conditions: Demo reality (v3.2/v4.0), GAE alone (Design v2 Tiers 1–5), + Ontology (Addendum §2), + INOVA (v4.5 entity resolution), + ARC/SC Portfolio.

**Scores: CLOSED** (gap eliminated), **MOSTLY CLOSED** (substance addressed, residual polish), **PARTIALLY CLOSED** (meaningful progress, significant work remains), **OPEN** (not addressed).

### 2.1 Complete Gap Item Inventory

> **v3 corrections:** L1-3 version corrected to v6.0 (INOVA deferred). L2-1, L3-1, L3-4, L3-5 version corrected to v4.1 ✅ (already implemented and tagged).

| **ID** | **Layer** | **Item** | **Sev.** | **Status** | **Closed By** | **Version** |
|---|---|---|---|---|---|---|
| L1-1 | UCL | Unified semantic layer | HIGH | **MOSTLY CLOSED** | SchemaContracts + DomainOntology | v5.0/v6.0 |
| L1-2 | UCL | Consistent embeddings | CRIT | **MOSTLY CLOSED** | Tier 4 + EmbeddingContracts | v5.5 |
| L1-3 | UCL | Entity resolution | HIGH | **CLOSED** | INOVA-1a/1b | **v6.0** ‡ |
| L1-4 | UCL | Governed write paths | HIGH | **CLOSED** | DomainOntology + SchemaValidator | v6.0 |
| L1-5 | UCL | KPI contracts | MED | PARTIALLY | PropertySpec foundation | v5.5+ |
| L2-1 | Agent | Eq. 4b weight evolution | CRIT | **CLOSED** | Tier 3 learning.py | **v4.1 ✅** ‡ |
| L2-2 | Agent | Candidate artifact generation | CRIT | **MOSTLY CLOSED** | ARC + SC meta-prompt + GAE fitness | v6.0 |
| L2-3 | Agent | Binding eval gates | HIGH | **MOSTLY CLOSED** | SC Safeguard + R×T×Q + GAE convergence | v6.0 |
| L2-4 | Agent | Prompt module evolution | HIGH | **MOSTLY CLOSED** | SC Meta-Prompt Agent + eval framework | v6.0 |
| L2-5 | Agent | Experience pool | HIGH | **CLOSED** | Tier 3 learning state | v5.0 |
| L3-1 | ACCP | Situation Analyzer | CRIT | **CLOSED** | GAE-4a/4b | **v4.1 ✅** ‡ |
| L3-2 | ACCP | Scoring matrix | CRIT | **CLOSED** | Tier 2 scoring.py | v5.0 |
| L3-3 | ACCP | Decision economics | MED | OPEN | — | v6.0 |
| L3-4 | ACCP | Typed-Intent Bus | LOW | **CLOSED** | ARC ACCP pattern | **v4.1 ✅** ‡ |
| L3-5 | ACCP | RL signal r(t) | HIGH | **CLOSED** | Tier 3 Eq. 4b | **v4.1 ✅** ‡ |
| L3-6 | ACCP | Asymmetric 20:1 | HIGH | **CLOSED** | Tier 3 λ_neg=20.0 | v5.0 |
| L4-1 | Copilots | Closed-loop micro-agencies | MED | OPEN | — | v6.0 |
| L4-2 | Copilots | Autonomous operation | MED | OPEN | — | v6.0 |
| L4-3 | Copilots | Verified outcomes → r(t) | HIGH | **CLOSED** | GAE-3a feedback | v5.0 |
| L4-4 | Copilots | Investigation narratives | HIGH | **CLOSED** | GAE-5 LLM narratives | v5.0 |
| CS-1 | Stack | Factor Computation | CRIT | **CLOSED** | Tier 1 + contracts | v5.0 |
| CS-2 | Stack | Scoring Matrix | CRIT | **CLOSED** | Tier 2 scoring.py | v5.0 |
| CS-3 | Stack | Weight Update | CRIT | **CLOSED** | Tier 3 learning.py | v5.0 |
| CS-4 | Stack | Entity Embeddings | CRIT | **CLOSED** | Tier 4 + embed contracts | v5.5 |
| CS-5 | Stack | Cross-Graph Attention | CRIT | **CLOSED** | Tier 5 attention.py | v5.5 |
| CS-6 | Stack | LLM Reasoning | HIGH | **CLOSED** | GAE-5 | v5.0 |

‡ Version corrected in v3

**Summary**

| **Status** | **Count** | **Percentage** |
|---|---|---|
| **CLOSED or MOSTLY CLOSED** | **22** | **85%** |
| PARTIALLY CLOSED | 1 | 4% |
| OPEN | 3 | 12% |

**CRITICALs: 10/10 addressed** (9 closed, 1 mostly closed). All remaining opens are MEDIUM priority.

**Portfolio Source Attribution**

| **Source** | **Gap Items Closed/Addressed** |
|---|---|
| **GAE Design v2** | CS-1–CS-6, L2-1, L2-5, L3-1, L3-2, L3-5, L3-6, L4-3, L4-4 |
| **Ontology (Addendum §2)** | L1-1, L1-2, L1-4, L1-5 (strengthens CS-1, CS-4, CS-5) |
| **INOVA (v6.0)** | L1-3 |
| **ARC abstract** | L2-2 (partial), L3-4 |
| **SC multi-agent platform** | L2-2 (partial), L2-3, L2-4 |

---

## PART 3: Hidden Engineering Gaps

The scorecard measures "does a design exist for this capability." It does not measure integration risk, data realism, evaluation quality, or commercial viability. This section identifies issues that cut across scorecard line items or exist between them.

**H1. Promotion Pipeline Concentration Risk**

**Severity: HIGH**

**Problem:** Three MOSTLY CLOSED items (L2-2, L2-3, L2-4) all depend on one unbuilt component: the promotion state machine + shadow/canary orchestrator. If the promotion pipeline slips, all three regress simultaneously.

**Recommended action:** Build the state machine as a standalone module at v5.5, before v6.0 agent integration. Test lifecycle state transitions against mock evaluation results.

**H2. Embedding Sophistication Gap**

**Severity: MEDIUM→HIGH**

**Problem:** Property-based embeddings are to entity representation what bag-of-words is to text. They work at demo scale (50 entities) but may produce meaningless attention scores at production scale (50,000 entities with 20% missing data).

**Recommended action:** Multi-scale factor windows at v5.5 (immediate improvement, low cost). Hybrid property + structural embeddings at v6.5. GNN-learned embeddings at v7.0+ if needed.

**H3. The Autonomy Cluster**

**Severity: HIGH (combined)**

**Problem:** Individually MEDIUM. Together, the difference between "recommendation engine with good math" and "copilot that actually reduces analyst workload." Every ROI projection assumes the system ACTS, not just RECOMMENDS.

**Recommended action:** Graduated autonomy by action type (design thresholds at v5.0, implement at v6.0). Auto-close (lowest risk) gets autonomous processing first. Escalation stays human-gated.

**H4. Decision Economics as Buyer Proof**

**Severity: HIGH (commercial)**

**Problem:** The system cannot quantify its own economic value. "Weights improved 15%" is meaningless to a CISO. "$19,295 analyst hours saved this month" is meaningful.

**Recommended action:** ROI dashboard at v5.0 using real decision counts × configurable per-action costs (ECON-1 prompt).

**H5. Data Realism Gap**

**Severity: HIGH (credibility)**

**Problem:** Everything runs on 50 clean users with no noise, no missing data, no drift, no temporal patterns. The scorecard measures capability design, not whether that capability works on realistic data.

**Recommended action:** Realistic seed data generator at v5.0 (SEED-2 prompt). Power-law distributions, cold-start users, missing properties, temporal clustering.

**H6. Evaluation Ground Truth Gap**

**Severity: MEDIUM–HIGH**

**Problem:** The R×T×Q framework needs ground truth. In SOC, "known-correct" is rarely clean binary — experienced analysts disagree on 10–30% of triage decisions.

**Recommended action:** 20–50 hand-verified evaluation scenarios at v5.0 (EVAL-1 prompt). Tiered confidence scoring at v6.0.

---

## PART 4: Engine Gaps (Open-Source Decision)

The decision to open-source the GAE engine (Addendum v4 §11) creates five new engineering requirements not captured by the original capability scorecard.

**E1. Engine API Surface Design [HIGH]**

Every class and function in core/ that a domain module can call must be defined, versioned, and tested for backward compatibility. Today core/ has internal APIs that work for the SOC product but are not designed for external consumption. Addressed by ENG-1 at v5.0.

**E2. Engine/Product Dependency Enforcement [HIGH]**

Build-time check that core/ never imports from domains/soc/, connectors/, routers/, or frontend/. Today this is a convention. For an open-source engine, it must be enforced by CI. Addressed by ENG-1 lint rule at v5.0.

**E3. Example Domain [MEDIUM]**

A minimal domain module (~50 lines) demonstrating the DomainConfig pattern. The SOC domain is too complex for a tutorial. The engine needs a "Hello World" domain that runs the full loop (factor → score → learn → converge) on a synthetic graph. Addressed by ENG-2 at v5.0.

**E4. Engine Test Suite [MEDIUM]**

Engine tests must pass without product code installed. Current tests may assume SOC domain availability. Separation needed before release. Addressed naturally by v5.0 test structure.

**E5. Engine Documentation [MEDIUM]**

> **v3 change from v1.1:** Moved from v5.5 to v5.0. v5.0 redefined to include GAE Users Guide (GAE-DOC-1).

README, API reference, quickstart guide, migration guide. The math blog and CI 4.0 serve double duty but need supplementation. Addressed at v5.0 (GAE-DOC-1).

---

## PART 5: Architectural Gaps, Unknowns & Interaction Effects

Structural properties of the current design — consequences of equation choices that constrain what the system can do. Not bugs or missing features; they require design changes, not just more code.

### Architectural Limitations

**A1. The Confirmation Bias Loop**

**Severity: HIGH** | Solution status: PARTIALLY KNOWN

> **v3 change:** Moved from v5.5–v6.0 to v4.5 (measured) + v5.0 (fixed). CalibrationProfile infrastructure at v4.5 makes discount_strength trivial to add. Shipping known bias with designed fix is hard to defend.

Analyst sees the system's recommendation before providing feedback. r(t) = +1 from confirmation is confounded by the system's influence. Weight matrix converges toward self-confirming beliefs.

**Design response:** Confidence-discounted learning rate. α_effective = α × (1 - discount_strength × max(P)). Measured at v4.5 (via CalibrationProfile), discount_strength tuned at v5.0.

**A2. Uniform Temporal Decay**

**Severity: MEDIUM→HIGH** | Solution status: KNOWN

> **v3 change:** Moved from v5.5 to v4.5 GAE preamble. Per-factor decay via CalibrationProfile + decay_class in SchemaContract. Must land before Phase A simulation.

Eq. 4c applies ε=0.001 to all knowledge. Permanent patterns decay at the same rate as transient campaign TTPs.

**Design response:** Three-layer decay design: domain schema declares decay classes → CalibrationProfile maps to rates → GAE learning loop consumes. Per-factor decay rates via SchemaContract.decay_rate field: "permanent" (ε=0.0001), "standard" (ε=0.001), "campaign" (ε=0.003), "transient" (ε=0.01). Implemented at v4.5 via CalibrationProfile.

**A3. Cross-Graph Attention Quadratic Scaling**

**Severity: LOW→HIGH** | Solution status: KNOWN

n(n-1)/2 pairwise heads with n^2.3 scaling. At 6 domains: 15 heads (fine). At 20 domains (v7.0): 190 heads (expensive).

**Design response:** Domain clustering at v7.0. The primitives.py backend-swappable design already supports this.

**A4. False Discovery Self-Propagation**

**Severity: MEDIUM** | Solution status: PARTIALLY KNOWN

F1=0.293 means ~70% of discovery candidates are false positives. Connector 5 can expand W from false discoveries. W can grow but never shrink.

**Design response:** Soft expansion with accelerated decay. New dimensions enter as "provisional" with 10× normal decay. After 50+ reinforcements, transition to "established." v5.5.

### Unknowns — Where We Lack Theory

Questions where we cannot predict the answer from the design documents. They require experiments.

**B1. Ground Truth Noise Propagation Through Meta-Learning**

**Question:** If the meta-prompt agent optimizes prompt variants against noisy labels (~85% accurate analysts), does it: (a) match analyst accuracy? (b) exceed it? (c) oscillate? (d) amplify noise?

**Experiment needed:** Run R×T×Q with synthetic analyst decisions at known noise levels (5%, 10%, 20%, 30%). Measure winning variant accuracy on clean test cases.

**When:** v5.5

**B2. Weight Learning × Artifact Evolution Interaction Dynamics**

**Question:** Weight learning (Connector 3) and artifact evolution (Connector 6) are described as "orthogonal." They are not. Do the two loops converge to a joint optimum, oscillate, one dominates, or create a feedback spiral?

**Experiment needed:** Simulation with simplified model: synthetic alerts, simulated analyst, weight learning loop, periodic artifact swap. 10,000 decisions. Measure convergence.

**When:** v5.5

**B3. Property-Based Embeddings at Production Scale**

**Question:** F1=0.293 on clean 50-entity synthetic data. What happens at 50,000 entities with 20% missing properties, type inconsistencies, and temporal drift?

> **v3 change:** Moved from v5.0 to v4.5 Phase C (test) + v5.5 (holistic revisit). Test property-based first at v4.5. Threshold F1 > 0.2. Revisit holistically at v5.5 with downstream accuracy.

**Experiment needed:** SEED-2 realistic seed generator. Generate 5,000 entities with realistic noise. Run discovery sweep. Measure F1 against planted patterns.

**When:** v4.5 Phase C (initial gate) + v5.5 (revisit with downstream accuracy)

### Interaction Effects

**C1. Ontology Drift × Weight Learning**

**Severity: MEDIUM**

Schema drift between startups causes factors to return 0.0 for structural reasons. Weight matrix adjusts away from the "broken" factor.

**Design response:** Runtime schema monitoring. If coverage drops below threshold, pause learning for affected factors. v6.0.

**C2. Discovery Expansion × Artifact Evaluation Timing**

**Severity: MEDIUM**

If W expands during an artifact evaluation cycle, the evaluation compares variants against a scoring baseline that changed mid-evaluation.

**Design response:** Lock W shape during artifact evaluation. Snapshot W at evaluation start. Queue expansion until evaluation completes. v6.0.

**C3. Autonomy × Confirmation Bias**

**Severity: HIGH**

The most dangerous interaction. Autonomous auto-closes are r(t) = +1 until a missed threat surfaces — potentially 30 days later. By then, 200+ positive reinforcements accumulated. The 20:1 penalty from one miss doesn't overcome 200+ positives.

**Design response:** Delayed outcome validation for autonomous decisions. Auto-closed alerts enter "pending validation" state. After configurable window (14–30 days), if no incident linked → r(t) = +1. If incident linked → r(t) = -1. v6.0.

---

**These three experiments (B1-B3) are gate checks, not optional research.** They must be resolved BEFORE the engine is open-sourced at v5.5, because releasing an engine with known-untested failure modes undermines the credibility the open-source strategy is designed to build.

---

## PART 6: New Gaps from Design Decisions Session (D1-D7)

> **v3 addition:** The design decisions session surfaced 7 latent gaps that existed but weren't tracked. All have clear owners, target versions, and prompt assignments.

**D1. Ablation Framework**

**Severity: MEDIUM** | Target: v5.0 (GAE-ABL-1) | Owner: GAE

Four-baseline comparison (static, flat learning, no graph, full system) to prove each architectural component's value. GAE-level capability. Standard ML methodology — required for credible research claims.

**D2. Institutional Judgment Metrics**

**Severity: HIGH** | Target: v4.5 (partial: SIM-2 category learning curve) + v5.0 (full: GAE-JUDG-1) | Owner: GAE + SOC

"The system gets smarter" must be measurable, not just asserted. Full metrics: prior divergence, accuracy improvement, recovery speed, judgment score. Domain copilots translate abstract metrics to CISO/CPO language.

**D3. Domain Schema Format**

**Severity: HIGH** | Target: v4.5 (design) + v5.0 (implement) | Owner: GAE + Platform

Single source of truth for factor metadata (decay class, required graph structure). GAE defines format (DomainSchemaSpec), copilots provide content (YAML), ci-platform validates at startup.

**D4. ci-platform Extraction**

**Severity: MEDIUM** | Target: v5.0 (PLAT-1 through PLAT-4) | Owner: Platform

DomainConfig ABC, StateManager, domain_registry extracted from SOC copilot into ci-platform. Pattern: build concrete in SOC at v4.5, extract at v5.0.

**D5. NarrativeProvider Abstraction**

**Severity: MEDIUM** | Target: v4.5 Phase B (NAR-1) | Owner: SOC

Protocol + Ollama/Qwen default + template fallback. Local-first, no API key dependency. Graceful degradation ensures narrative capability works without external services.

**D6. Organizational Specificity Test**

**Severity: MEDIUM** | Target: v5.0 | Owner: GAE + SOC

Train two instances on different scenario distributions. Swap evaluation scenarios. Proves learning is firm-specific, not generic — validates the "institutional judgment" claim.

**D7. S2P Validation Walkthrough**

**Severity: MEDIUM** | Target: v5.0 | Owner: Platform

Design check that all platform abstractions work for a second domain (Source-to-Pay procurement). No implementation — validates that CalibrationProfile, DomainSchemaSpec, and evaluation framework are genuinely domain-agnostic.

---

## PART 7: Consolidated Assessment

### 7.1 Four-Layer Gap Summary

| **Layer** | **Count** | **Categories** |
|---|---|---|
| **Capability scorecard** | 22/26 closed/mostly (85%) | 4 remaining: 1 partial (L1-5), 3 open (L3-3, L4-1, L4-2) |
| **Hidden engineering gaps** | 6 identified (H1–H6) | 3 need v5.0 action (H4, H5, H6); 3 need v5.5–v6.0 |
| **Architectural gaps** | 10 identified (4+3+3) | 4 known solutions; 3 partial; 3 genuinely unknown |
| **Engine gaps** | 5 identified (E1–E5) | 4 need v5.0 action (E1–E4); 1 needs v5.0 (E5) |
| **Design decisions gaps** | 7 identified (D1–D7) | 2 critical, 2 high, 3 medium |

### 7.2 What Has Known Solutions (Engineering)

| **Gap** | **Solution** | **Version** | **Effort** | **Scope** |
|---|---|---|---|---|
| A2. Uniform decay | Per-factor decay rates via CalibrationProfile | **v4.5** ‡ | Config change | ENGINE |
| A3. Quadratic scaling | Domain clustering | v7.0 | New primitive | ENGINE |
| C1. Schema drift | Runtime monitoring + learning pause | v6.0 | Monitoring hook | ENGINE |
| C2. Eval timing | W shape lock during evaluation | v6.0 | Concurrency control | ENGINE |
| H4. Decision economics | ROI dashboard | v5.0 | 1 prompt (ECON-1) | PRODUCT |
| H5. Data realism | Realistic seed generator | v5.0 | 1–2 prompts (SEED-2) | ENGINE+PRODUCT |
| H6. Eval ground truth | Curated scenarios | v5.0 | 1 prompt (EVAL-1) | ENGINE+PRODUCT |
| E1. Engine API surface | Public API exports + import lint | v5.0 | 1 prompt (ENG-1) | ENGINE |
| E2. Dependency enforcement | CI lint rule | v5.0 | Part of ENG-1 | ENGINE |
| E3. Example domain | Hello World DomainConfig | v5.0 | 1 prompt (ENG-2) | ENGINE |
| E4. Engine test suite | Product-independent tests | v5.0 | Follows ENG-1 | ENGINE |
| E5. Engine documentation | README, API ref, quickstart | **v5.0** ‡ | Pre-release | ENGINE |

‡ Version corrected in v3

### 7.3 What Has Partial Solutions (Needs Calibration)

| **Gap** | **Solution Concept** | **Unknown** | **Version** | **Scope** |
|---|---|---|---|---|
| A1. Confirmation bias | Confidence-discounted α | discount_strength requires empirical tuning | **v4.5 (measured) + v5.0 (fixed)** ‡ | ENGINE |
| A4. False discovery | Soft expansion + accelerated decay | Establishment threshold requires tuning | v5.5 | ENGINE |
| C3. Autonomy × confirmation | Delayed outcome validation | Optimal validation window length | v6.0 | ENGINE |

‡ Version corrected in v3

### 7.4 What Is Genuinely Unknown (Needs Experiments)

| **Gap** | **Experiment** | **Gate Decision** | **Version** | **Scope** |
|---|---|---|---|---|
| **B3. Embeddings at scale** | SEED-2 data → discovery sweep → F1 | If F1 < 0.1: replace Tier 4 before v5.5 | **v4.5 Phase C (test) + v5.5 (revisit)** ‡ | ENGINE |
| **B1. Noisy ground truth** | Synthetic noise → R×T×Q cycles → convergence | If divergent: redesign ground truth before v6.0 | **v5.5** | ENGINE |
| **B2. Loop interaction** | Simulation → 10K decisions → joint convergence | If oscillating: add loop coupling damping | **v5.5** | ENGINE |

‡ Version corrected in v3

---

## PART 8: Complete Gap Registry — Current State

### Critical (must address for product preview)

| ID | Gap | Status | Target | Owner |
|---|---|---|---|---|
| GAP-1 | No simulation mode | OPEN → v4.5 Phase A | SIM-1 through SIM-4 | SOC |
| GAP-2 | No ATT&CK | OPEN → v4.5 Phase A | SIM-4 | SOC |
| GAP-3 | Limited alert corpus | OPEN → v4.5 Phase A | SIM-3a/3b | SOC |
| GAP-5 | No cross-graph discovery (Axis 3) | OPEN → v4.5 Phase C (gated) | DISC-1 through GATE-B3 | SOC + GAE |
| D2 | Institutional Judgment metrics | NEW | v4.5 (partial: SIM-2 chart) + v5.0 (full) | GAE + SOC |
| D3 | Domain schema format | NEW | v4.5 (design) + v5.0 (implement) | GAE + Platform |

### High (product credibility)

| ID | Gap | Status | Target | Owner |
|---|---|---|---|---|
| GAP-4 | No investigation narrative | OPEN → v4.5 Phase B | NAR-1/NAR-2 | SOC |
| A1 | Confirmation bias | MOVED from v5.5 | v4.5 (measured) + v5.0 (fixed: discount_strength tuned) | GAE |
| A2 | Uniform temporal decay | MOVED from v5.5 | v4.5 GAE preamble (per-factor via CalibrationProfile) | GAE |
| H4 | Decision economics | OPEN | v5.0 (ECON-1: ROI dashboard) | SOC |
| H5 | Data realism | OPEN | v5.0 (SEED-2: 200+ users, power-law, noise) | SOC |
| H6 | Evaluation ground truth | OPEN | v5.0 (EVAL-1-SOC: 30–40 scenarios) | SOC + GAE |
| E1 | Engine API surface | OPEN | v5.0 (GAE-ENG-1: public exports, import lint) | GAE |
| E2 | Dependency enforcement | OPEN | v5.0 (GAE-ENG-1: lint rule) | GAE |
| D5 | NarrativeProvider abstraction | NEW | v4.5 Phase B (NAR-1) | SOC |

### Medium (platform maturity)

| ID | Gap | Status | Target | Owner |
|---|---|---|---|---|
| E3 | Example domain | OPEN | v5.0 (GAE-ENG-2: Hello World DomainConfig) | GAE |
| E4 | Engine test suite | OPEN | v5.0 (GAE-ENG-3: independent of SOC) | GAE |
| E5 | Engine documentation | MOVED from v5.5 | v5.0 (GAE-DOC-1: Users Guide) | GAE |
| D1 | Ablation framework | NEW | v5.0 (GAE-ABL-1: four baselines) | GAE |
| D4 | ci-platform extraction | NEW | v5.0 (PLAT-1 through PLAT-4) | Platform |
| D6 | Organizational specificity test | NEW | v5.0 (cross-trained evaluation) | GAE + SOC |
| D7 | S2P validation walkthrough | NEW | v5.0 (design check, no implementation) | Platform |
| TD-026 | Audit/GAE sync on reset | OPEN → v4.5 | SIM-FIX (first v4.5 SOC prompt) | SOC |

### Deferred (v5.5+)

| ID | Gap | Status | Target | Owner |
|---|---|---|---|---|
| A3 | Cross-graph quadratic scaling | Unchanged | v7.0 (Flash Attention backend) | GAE |
| A4 | False discovery propagation | Unchanged | v5.5 (only matters if Phase C gate passes) | GAE |
| B1 | Ground truth noise propagation | Unchanged | v5.5 | GAE |
| B2 | Weight learning × artifact evolution | Unchanged | v5.5 | Platform |
| B3 | Embeddings at scale (revisit) | MOVED from v5.0 | v5.5 (holistic review with downstream accuracy) | GAE |
| C1 | Ontology drift × weight learning | Unchanged | v6.0 | Platform |
| C2 | Discovery expansion × eval timing | Unchanged | v6.0 | Platform |
| C3 | Autonomy × confirmation bias | Unchanged | v6.0 | GAE + SOC |
| H1 | Promotion pipeline concentration | Unchanged | v5.5 | Platform |
| H2 | Embedding sophistication | Unchanged | v5.5–v6.5 | GAE |
| H3 | Autonomy cluster | Unchanged | v6.0 | Platform + SOC |

### Research (open questions, not engineering tasks — NEW in v4)

| ID | Gap | Severity | First Data | Full Answer | Owner |
|---|---|---|---|---|---|
| R1 | Convergence ≠ correctness: Hebbian update converges but may not converge to RIGHT weights | HIGH | v4.5 Phase A (ground_truth_action comparison in simulation) | v5.0 evaluation (EVAL-1-SOC: 30-40 scenarios) | GAE |
| R2 | Math-algorithm integration: GAE math and 3 algorithmic loops are independent layers; math can't quantify loop contributions | RESEARCH | v5.0 ablation (GAE-ABL-1: full system vs no-loops vs no-math vs static) | Ongoing experimentation | GAE + SOC |
| R3 | Error-driven discovery: Eq. 6 finds similar entities (similarity); should find entities that would change wrong decisions (relevance to decision quality) | RESEARCH | Design session before Phase C | v5.5+ implementation; may require revised Eq. 6 | GAE |

**Context for R1:** The 10-cycle gate at v4.1 proved convergence (28.6x asymmetry measured). But convergence to stable weights ≠ convergence to correct weights. The simulation at Phase A with ground_truth_action fields on alerts will produce the first data on correctness. If accuracy vs ground truth is poor despite convergence, the learning rule may need augmentation.

**Context for R2:** The system has two layers of intelligence: formalized math (GAE, Eq. 1-9) that scores and learns, and algorithmic loops (SituationAnalyzer routes alerts, AgentEvolver evolves strategies, ReinforcementGovernor verifies outcomes) that operate around the math. Neither models the other. The v5.0 ablation will produce the first data on relative contribution. If the loops dominate, the math needs strengthening. If the math dominates, the loops need tighter integration.

**Context for R3:** The CI blog's marquee claim is that cross-graph discovery creates new scoring dimensions. Current Eq. 6 uses embedding similarity. But the analyst analogy in the blog suggests discovery is error-driven: the analyst discovers the Singapore + CFO connection because they made a wrong decision. Mathematically: high-confidence errors indicate missing factors. The error signal from Eq. 4b should drive where discovery looks, not embedding similarity. This may require a new objective function for cross-graph attention.

### Closed at v4.1

| ID | Gap | Closed By |
|---|---|---|
| L2-1 | Eq. 4b weight evolution | Tier 3 learning.py |
| L2-6 | Asymmetric reinforcement | δ(t) with λ_neg=20.0, measured 28.6x |
| L3-1 | Scoring matrix (Eq. 4) | scoring.py — score_alert() |
| L3-4 | RL reward signal | learning.py — Eq. 4b update |
| L3-5 | Convergence monitoring | convergence.py — three failure modes |
| Multiple | SchemaContract, EmbeddingContract, events, store, primitives | All tested |

### Gap Count Summary

| Severity | Count | Change from v3 |
|---|---|---|
| CRITICAL | 6 | Unchanged |
| HIGH | 9 | Unchanged (+R1 tracked separately) |
| MEDIUM | 11 | Unchanged |
| RESEARCH | 3 | **+R1, +R2, +R3 (NEW category)** |
| DEFERRED | 11 | Unchanged |
| CLOSED | 10+ | Unchanged |
| **Total tracked** | **~50** | **+3 research gaps** |

**Interpretation:** Total gap count increased by 3 from the PM session. These are categorized as RESEARCH rather than engineering gaps because they are open questions without known solutions. R1 will produce first data at v4.5 Phase A (ground_truth comparison). R2 at v5.0 (ablation). R3 requires a design session before Phase C. The PM session also established that math quality is the critical success factor for the product — the GAE must demonstrably produce better decisions than alternatives.

---

## PART 9: Recommended v4.5 Sequence

> **v3 change:** Phase D eliminated. CalibrationProfile moved to GAE preamble (GAE-CAL-1). Docker/VPS moved to v5.5.

Priority reordered based on gap analysis. "Make it real" first, then "make it deep."

### Phase A: Simulation Mode + Alert Corpus (make the demo self-proving)

| **Prompt** | **What** | **Why First** |
|---|---|---|
| SIM-FIX | Atomic reset via StateManager | Prerequisite for simulation (TD-026) |
| SIM-1 | Backend SimulationOrchestrator (batch + progress) | Core capability |
| SIM-2 | Frontend simulation panel + real-time chart updates + category learning curve | Visible proof + D2 partial |
| SIM-3a/3b | Alert pool expansion (15–20 across 5 categories) | Variety for simulation |
| SIM-4 | ATT&CK technique IDs on all alerts + UI labels | Credibility |

### Phase B: Investigation Narrative + Tab 2 Rewiring (close the CISO gaps)

| **Prompt** | **What** | **Why** |
|---|---|---|
| NAR-1 | NarrativeProvider protocol + Ollama/Qwen default + template fallback (D5) | CISO readability |
| NAR-2 | Tab 3 narrative panel + "calibrated from N outcomes" line | Compounding in natural language |
| TAB2-1 | Rewire Tab 2 Runtime Evolution to use GAE pipeline | Remove dual-path tech debt (TD-019) |
| TAB2-2 | AgentEvolver shows real GAE weight changes | Loop 2 uses real data |

### Phase C: Cross-Graph Discovery (the hard problem — gated)

> **v4 addition:** Error-driven discovery design session required as prerequisite. Current Eq. 6 finds similarity in embedding space. PM session identified that discovery should be error-driven: find entities that would have changed high-confidence wrong decisions (R3). Design work may result in revised objective function for Eq. 6.

| **Prompt** | **What** | **Why** |
|---|---|---|
| DISC-1 | Entity embedding service (EmbeddingProvider protocol) | Prerequisite for Eq. 6 |
| DISC-2 | Cross-graph attention sweep (Eq. 6 — possibly revised) | Core discovery mechanism |
| DISC-3 | Discovery → expand_weight_matrix integration | New scoring dimension emerges |
| DISC-4 | Singapore + CFO + threat spike scenario seed data | The marquee demo moment |
| DISC-5 | Tab 4 discovery panel + confidence drop visualization | Visible Axis 3 proof |
| GATE-B3 | Embedding quality gate experiment (F1 > 0.2 threshold) | Honest assessment of production readiness |

---

## Blog Update Implications

**Demo Blurb (update after Phase A)**

- Add: "Run 50 automated decisions and watch the learning curve build in real-time"
- Add: ATT&CK technique references
- Update screenshots with simulation results

**CI Blog 4.0 → 5.0 (update after Phase C)**

- IF discovery works: "Axis 3 proved in live demo"
- IF discovery needs more work: "Axis 3 validated mathematically, production embedding research ongoing"
- Either way: honest about what's proved vs. designed

**Math Blog (no update needed)**

- Experimental validation stands as-is
- Implementation status documented separately in GAE Users Guide

**Loom v2 (record after Phase B)**

- Three-axis demo with simulation mode
- Show 50-decision run in real-time
- Show investigation narrative and ATT&CK alignment

---

## The Honest Framing

**The scorecard says:** 85% of capability gaps are closed. 10/10 CRITICALs addressed.

**This analysis adds:** Beneath the scorecard, there are 4 architectural limitations, 3 unknowns that can only be resolved by experiment, 3 interaction effects, 6 hidden engineering gaps, 5 engine gaps from the open-source decision, and 7 newly surfaced design gaps. Of these 28 additional items: 12 have known engineering solutions, 3 have solutions requiring calibration, 3 need experiments before solutions can be designed, 3 are v6.0+ timing issues, and 7 are newly tracked with clear prompt assignments.

**The key finding:** The three unknowns are all testable before they're needed. B3 at v4.5 Phase C, B1 and B2 at v5.5. They should be treated as roadmap gates — and they must be resolved BEFORE the engine is open-sourced at v5.5.

---

*Technology Scorecard & Gap Analysis — Consolidated Report v4 | February 28 – March 1, 2026*
*v3 + PM session outcomes: 3 research gaps (R1-R3), data collection instrumentation, error-driven discovery prerequisite*
*Capability scorecard: 22/26 closed or mostly (85%). 10/10 CRITICALs addressed.*
*Hidden engineering gaps: 6 (H1–H6). Engine gaps: 5 (E1–E5). Design gaps: 7 (D1–D7). Research gaps: 3 (R1-R3).*
*Total tracked: ~50 items across 5 severity levels, 3 repos, 6 target versions.*
*v4.5: 19 prompts + 2 reviews. v5.0: 18-20 prompts.*
*Math quality is the critical success factor.*
*"The moat is the graph, not the model. The math must prove it."*
