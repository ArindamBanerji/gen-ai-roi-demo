# SOC Copilot — Master Action Plan v2 (v6.0 → v7.5)
**Date:** March 22, 2026
**Version:** 2.0 (incorporates coding session review — 7 corrections, 7 adds, 6 modifications)
**Purpose:** Comprehensive sequenced action items for major release MVP.
**Principle:** Design strength first. All gaps, experiments, and validations resolved early.
No "real customer data" dependency — everything synthesized via LLM-judge/web scraping.
Statistically conclusive (multi-seed, CI-bounded, factorial where needed).

**Current state:** v5.5 alpha. 478 GAE + 280 SOC + 73 ci-platform tests (~935 total).
~104 experiments. A=4 confirmed. DiagonalKernel default. ReferralRules R1-R7 shipped.

---

## PHASE 0: IMMEDIATE FIXES (Day 1 — before anything else)
*These are small items that block experiment integrity, document accuracy, or demo readiness.*

| # | Item | What It Fixes | Effort | Reference |
|---|---|---|---|---|
| 0a | **Frontend visual validation (all 5 tabs)** | Zero frontend testing across ALL sessions. Every version reveals large errors. Flagged 🔴 in project_status_v4 and session_starter_v8. Must validate before ANY demo or GTM work. | 0.5 day | project_status_v4 |
| 0b | **θ_min harness fix (0.434→0.467)** | Persona sweeps use stale θ_min=0.434. Canonical is 0.467 (T_max=21 days). ALL future experiments using the harness will have wrong conservation thresholds. One-line fix, blocks experiment integrity. | 5 min | math_synopsis_v11 §16 |
| 0c | **soc_copilot_design 4 mechanical fixes** | Four instances of "confidence gate only" need replacing with "referral rules R1-R7." Blocks document accuracy. See soc_copilot_referral_update_note.md. | 15 min | soc_copilot_referral_update_note.md |
| 0d | **math_synopsis v11 referral integration** | §8 needs EXP-REFER-LAYERED row (already in v11 ✅). §14 needs referral rules note (already in v11 ✅). §16 needs "confidence gate is action routing only" constraint (already in v11 ✅). **Verify v11 is complete — it should be.** | 15 min (verify) | math_synopsis_v11 |
| 0e | **TD-034 DEC-DEC-XXXX double prefix** | Tab-4 Recent Evolution Events shows "DEC-DEC-XXXX" because frontend prepends "DEC-" to an ID that already starts with "DEC-". Cosmetic but visible in every demo. | 15 min | project_status_v4 |

---

## PHASE 1: DESIGN STRENGTH (Experiments, Validations, Gap Closure)
*Priority: HIGHEST. Do these first. Every unvalidated claim is a liability.*
*Claims registry updated after each batch (rolling — ~1hr per batch).*

### 1A — Critical Experiments (block claims or narrative)

| # | Experiment | What It Resolves | Method | Statistical Rigor | Priority |
|---|---|---|---|---|---|
| 1 | **V-CGA-FROZEN** | Widest innovation-claim gap. "Graph compounds while centroids wait." If graph enrichment doesn't lift frozen scorer accuracy, the second compounding pathway claim dies. Bottom-right quadrant (~10-15%) narrative collapses. | Freeze centroids at bootstrap. Run 90 simulated days with active graph enrichment (threat intel import, entity resolution, SIEM import). At Day 90, unfreeze. **Measure: (a) σ_per_factor at Day 0 vs Day 90, (b) cold-start convergence speed at Day 0 vs Day 90, (c) IKS trajectory comparison.** | **50 seeds minimum**, 2 conditions (enrichment vs no-enrichment), paired t-test, p<0.01, report 95% CI on lift. Measure across all 6 categories independently. | **P0 — HIGHEST** |
| 2 | **V-SIM** | Full P28 pipeline end-to-end. The v6.0 customer experience validated on synthetic data. Validates KernelSelector, deployment gate, 250-decision shadow, GREEN/AMBER/RED classification. | LLM-judge generates 9 deployment-realistic streams: 3 industries (healthcare σ≈0.22, FinServ σ≈0.08, manufacturing σ≈0.15) × 3 judges. Each stream: 30 simulated days, realistic alert mix, ~200 alerts/day. Full P28 pipeline: Import → Compute → Shadow → Qualify → Enable. | **9 streams × 30 days × ~200 alerts = ~54,000 synthetic alerts.** Each stream independently assessed. KernelSelector must match expected kernel in ≥8/9 streams. Deployment gate GREEN/AMBER/RED correct in ≥8/9. | **P0 — HIGHEST** |
| 3 | **V-ENRICHMENT-NEGATIVE** | Can enrichment HURT? Must answer before claiming enrichment helps. Gap G5c — the only safety gap for the enrichment narrative. | 2 personas where graph enrichment introduces contradictory threat intel (stale CVEs, retracted advisories, conflicting actor attribution). Measure accuracy degradation. | **20 seeds per persona**, report worst-case degradation with 95% CI upper bound. If degradation >3pp: design mitigation. | **P0** |
| 4 | **TD-034 validation on LLM-judge streams** | TD-034 SOC sweep already complete: **τ=0.08 optimal (ECE=0.052), τ=0.10 ECE=0.069.** Results in `experiments/td034_tau_recalibration/`. What remains: validate these results hold on LLM-judge-generated streams with realistic factor distributions (FX-1-PROXY-REAL-informed: bimodal threat_intel, right-skewed pattern_history). Also: S2P τ sweep (no prior result). | Run existing P28 τ sweep pipeline on 3 LLM-judge streams (healthcare, FinServ, manufacturing). Confirm τ=0.08 or identify stream-specific optimal. S2P: sweep τ [0.05–0.25] on LLM-judge procurement data. | **20 seeds per stream × 7 τ values = 420 runs (SOC validation). S2P: 20 seeds × 7 τ values = 140 runs.** | **P0** |
| 5 | **P4-F** (subtle poisoning) | Adversarial analyst injecting bad overrides gradually. Safety validation. Conservation law early warning tested under adversarial conditions. | Adversarial analyst persona: starts at q̄=0.85, degrades to q̄=0.40 over 500 decisions (gradual, not sudden). Measure: when does ConservationMonitor detect? How much centroid damage before detection? | **30 seeds**, report detection latency distribution (median, p90, p99). Damage at detection time must be <5pp. If not: tighten conservation thresholds. | **P1** |
| 6 | **P4-COMPLACENCY** | Does analyst override rate (α) drop before quality drops? Conservation law early warning fidelity. | Persona where quality degrades SLOWLY while override rate stays constant (the "checked out but still clicking" scenario). Measure: does Var(q) catch it before α·q·V drops below θ_min? | **30 seeds.** Report false negative rate for quality degradation that evades α·q·V detection. If >10%: Var(q) must become gating (not just logged). | **P1** |
| 7 | **PROD-5** | Convergence calendar validation. L-08 feature: "Your insider_threat profile will calibrate by Day 42." | Run convergence sweeps across factorial data. For each (category, σ, V, kernel) combination: measure N_decisions to within 2pp of final accuracy. Fit N_half = f(σ, V, q̄, kernel). | **Use existing 390-cell factorial data.** Regression fit with R² > 0.80. Prediction error < 20% for 90% of cells. Cross-validate with holdout. | **P1** |
| 8 | **EXP-G1** (γ temporal compounding) | "Each enrichment sweep more productive than the last." Currently estimated γ≈1.5, not stated externally. Blocks Level 2 claims and the S(n,t) ~ O(n^2.11 · t^γ) formula. | Requires Level 2 pipeline (GraphAttentionBridge, item #57). Design already complete (math_synopsis_v11 §10.1, intelligence_layer_design_v2). Run multi-domain enrichment sweeps over 10 simulated months. Measure information gain per sweep. Fit γ. | **20 seeds, 10 sweeps each = 200 sweep-pairs.** Regression fit. Claim requires γ>1.0 with p<0.05. Bootstrap CI. | **P1 — run when #57 ships** |
| 8b | **EXP-S2-REPRO at A=4** | Original EXP-S2-REPRO ran at A=5 (0.15pp max degradation). A=4 migration happened after. Poisoning resilience should be reconfirmed at A=4. Low risk (A=4 is simpler geometry, likely better) but a gap in the validation chain. | Re-run EXP-S2-REPRO 3-arm design at A=4. Compare 0.15pp bound. | **20 seeds per arm × 3 arms = 60 runs.** Gate: max degradation ≤ 0.20pp. | **P2** |

### 1B — Factorial Analysis Experiments (run on EXISTING data)

| # | Experiment | What It Resolves | Method | Rigor | Priority |
|---|---|---|---|---|---|
| 9 | **V-MV-RISK** | Should continuous R score replace discrete deployment gate at v6.5? Fit R = f(σ, V, q̄, kernel, n) on factorial trajectories. | Feed 390-cell factorial accuracy trajectories to LLM-judge. Fit continuous risk model. Compare: does R predict degradation onset ≥50 decisions before threshold gate? | ROC analysis: AUC > 0.85 required for R to replace threshold. Calibration plot. | **P1** |
| 10 | **V-MV-CONVERGENCE** | Dynamic convergence calendar: N_half = f(σ, V, q̄, kernel). Blocks L-08 "days to calibration" feature. | Extract convergence points from 390-cell factorial. Fit parametric model. Validate on holdout cells. | R² > 0.80. Prediction error < 20% on holdout. | **P1** |
| 11 | **V-MV-CONSERVATION** | Var(q) false alarm rate. Should Var(q) become gating (not just logged)? | Retrospective Var(q) computation on all 390 factorial trajectories. Measure: false alarm rate (conservation fires when centroids are healthy) and detection rate (conservation stays silent when centroids degrading). | Precision > 0.70, Recall > 0.80 for Var(q) as gating signal. If not: remains logged-only. | **P1** |
| 12 | **Gap G4 interactions (untested)** | Low q̄ × small team, campaign × low q̄, enrichment × small team. 2 of 5 interaction effects still untested. | Extend factorial: add team_size=3 dimension. Add campaign injection scenarios. 2×2×2 mini-factorial: (q̄ low/high) × (team 3/8) × (campaign yes/no). | **20 seeds per cell = 160 runs.** Report interaction effects with 95% CI. Any interaction >5pp: document as product boundary. | **P1** |

### 1C — Innovation-to-Claim Gap Closure

| # | Item | Gap | Method | Priority |
|---|---|---|---|---|
| 13 | **V-UCL-VALUE** | Innovation 0 (UCL) — no claim for graph infrastructure value independent of scoring. Entity count × relationship count → IKS prediction? | Analysis on existing persona sweep data: regress IKS trajectory on graph statistics (node count, edge count, entity resolution matches). If R² > 0.50: UCL has independent predictive value. | **P1** |
| 14 | **Adj. C narrative** | "Graph compounds while centroids wait." Depends on V-CGA-FROZEN (#1 above). If V-CGA-FROZEN passes: write claim + evidence. If fails: narrow to Tier 2 only. | Claims registry update + deck update + blog update. | **P1** (blocked by #1) |
| 15 | **Adj. B shipped status** | Asymmetric η (P0 fix). Code shipped. Claims and blog need updating. Innovation note v2 has it. Push to blog. | Blog session with wix_blog_update_spec. | **P2** |
| 16 | **Adj. G epistemic state** | EU AI Act Art. 15 — kernel metadata, noise zone, confidence, conservation status in evidence ledger per decision. | Code: ~50 lines in ci-platform. Evidence ledger entry gains kernel_type, noise_zone, conservation_status, confidence fields. | **P2** |
| 16b | **Claims registry update (rolling)** | Every experiment batch in Phase 1 changes the claims landscape. claims_registry currently v3.1 in project repo; v6 in session outputs. | After each weekly batch: update claims_registry. Promotions, falsifications, new claims, forbidden claims. ~1hr per batch. | **P1 (rolling)** |

### 1D — S2P Design Validation

| # | Item | What It Resolves | Method | Priority |
|---|---|---|---|---|
| 17 | **S2P-V3B** | τ calibration for S2P domain. Currently assumes τ=0.1 transfers from SOC. | LLM-judge generates 500 S2P alerts across 5 categories. Run τ sweep [0.05–0.25]. 20 seeds per τ value. Report optimal τ for S2P. | **P1** |
| 18 | **S2P penalty_ratio** | 5:1 confirmed as design estimate. Needs cost-benefit validation. | LLM-judge generates 3 penalty scenarios: under-penalty (miss=false approve), balanced (5:1), over-penalty (20:1). 20 seeds each. Measure: false-approve rate and false-reject rate at each ratio. Find Pareto optimum. | **P1** |
| 19 | **S2P correlation structure** | 8×8 Σ matrix from two-judge research. Validated? | Run s2p_correlation_research_prompt.md against 3 additional frontier models (beyond original 2). Report consensus correlation matrix. Pairs with ρ>0.60: confirm or reject with ≥3/5 judge agreement. | **P2** |
| 20 | **S2P NL templates** | 40 templates (5 categories × 8 factors) needed. Currently 0 authored. | LLM-judge generates candidate templates. Human domain expert reviews/edits. Ship with S2P launch. | **P2** |

---

## PHASE 2: SYNTHESIS & INTELLIGENCE LAYER (GATE-D pipeline)

| # | Experiment/Item | What It Resolves | Method | Priority |
|---|---|---|---|---|
| 21 | ~~**EXP-S5a**~~ | ✅ **DONE.** 460 claims ingested, all 5 categories covered, σ_saturated=True. In experiment_reference_catalog_v2 Series 3. | — | ✅ Complete |
| 22 | ~~**EXP-S5b**~~ | ✅ **DONE.** LLM F1=0.877, template F1=0.598. In experiment_reference_catalog_v2 Series 3. | — | ✅ Complete |
| 23 | **EXP-S5** | Full intelligence pipeline end-to-end. CISA advisory → claim extraction → σ update → scoring impact. Chains completed EXP-S5a + S5b with ProfileScorer. | Measure latency (gate: <200ms P95) and accuracy lift from σ at λ=0.5. 20 seeds. | **P1** |
| 24 | **EXP-S6** | INTSUM-quality briefing from σ changes. Tab 5 Section 3 quality. | LLM-judge evaluates generated briefings against 10 reference briefings (human-written from CISA advisories). Gate: ≥80% claim coverage, LLM judge score ≥4/5. | **P2** |
| 25 | **EXP-S7** | Ask-the-Graph: does the intelligence layer improve ad-hoc graph queries? | 15 test queries across 3 difficulty levels. Gate: ≥10/15 correct answers with intelligence layer vs ≤6/15 without. | **P2** |
| 26 | **GATE-D decision** | If S5+S6+S7 pass: σ flows into scoring (Tab 5 Section 3 live). If fail: display-only. | Binary gate: all 3 pass = GATE-D PASS. (S5a/S5b already complete.) | **Gate** |
| 27 | **EXP-L2-POISON** | Level 2 safety. Can a compromised variant (prompt injection via synthesis) corrupt Level 1 centroids? | Adversarial variant injects biased σ values. Firewall test: μ must not change. Conservation law must detect quality drop. 20 seeds. | **P2** |

---

## PHASE 3: CORE PRODUCT FEATURES (code prompts)

### 3A — Remaining v6.0 Code (~150 lines ci-platform wiring)

*Note: Kernel code (KernelSelector, DiagonalKernel, CovarianceEstimator) already shipped — 478 GAE tests. What's needed is WIRING existing GAE components into the ci-platform P28 pipeline.*

| # | Item | Lines | What It Does | Reference |
|---|---|---|---|---|
| 28 | P28 Phase 2 kernel integration wiring | ~30 | Wire gae/kernel_selector.py into P28 pipeline. Per-factor σ from CovarianceEstimator → noise_ratio → KernelSelector recommendation. | design_note_v2 §4.2, gae/kernel_selector.py |
| 29 | P28 Phase 3 multi-kernel shadow wiring | ~30 | Wire both kernels into shadow scoring. Rolling 100-window comparison via existing KernelSelector.compare(). | design_note_v2 §3.4 |
| 30 | P28 Phase 4 qualification wiring | ~30 | Wire KernelSelector.lock() at 250 decisions. Deployment gate uses existing DeploymentQualifier. | design_note_v2 §4.1 |
| 31 | Deployment gate thresholds | ~10 | Kernel-dependent GREEN/AMBER/RED thresholds in DeploymentQualifier config. | roadmap_v19_part1 |
| 32 | ConservationMonitor Var(q) | ~20 | Per-analyst quality dispersion. Logged, not gating (until V-MV-CONSERVATION #11 decides). | design_note_v2 §3.5 |
| 33 | Residual tracking | ~30 | Log confident-but-wrong decisions. Factor extensibility feed. | design_note_v2 §5.1 |
| 34 | **R2/R7 graph query wiring** | ~40 | **R2:** Cypher query on DecisionRecord — count same-source alerts in temporal window (e.g., `MATCH (d:DecisionRecord) WHERE d.source_id = $src AND d.timestamp > $t - 3600 RETURN count(d)`). **R7:** Distinct-category query for same-user alerts in 60 minutes (e.g., `MATCH (d:DecisionRecord) WHERE d.user_id = $uid AND d.timestamp > $t - 3600 RETURN count(DISTINCT d.category)`). Without these, R2 and R7 default to 0 (safe but 2/7 rules never fire). | referral_rules.py |
| 35 | Adj. G epistemic state | ~50 | Evidence ledger: kernel_type, noise_zone, conservation_status, confidence per decision. EU AI Act Art. 15. | product_strategy_v3_part2 |

### 3B — SOC Feature Builds

| # | Feature | Description | Effort | Reference |
|---|---|---|---|---|
| 36 | **Attack chain correlation (F6)** | Link alerts sharing entities within temporal windows. ATT&CK progression tracking (T1566→T1078→T1021). Campaign timeline view. Tier 1→Tier 2 value (3-5× pricing). **Requires multi-hop graph schema work:** AlertNode→Asset→CVE→BlastRadius, campaign entity, ATT&CK technique nodes. | **Large (2-3 weeks)** | platform_roadmap_v14, Stryker analysis |
| 37 | **Multi-SIEM abstraction (F5)** | SplunkConnector + SentinelConnector (bidirectional). Alert normalization to canonical AlertNode. Splunk+Sentinel = 60% addressable market. | Large (1-2 weeks) | platform_roadmap_v14 |
| 38 | **Third SIEM (F5 cont.)** | CrowdStrike Falcon LogScale or Elastic Security. +20% TAM. | Medium (1 week) | planning_catalog_v1 |
| 39 | **Analyst benchmarking report (F9)** | AI vs analyst comparison from shadow data. Improving benchmarks over time. "Day 1: matched 83%. Day 90: matched 91%, identified 12 true positives analysts missed." | Medium (1 week) | platform_roadmap_v14 |
| 40 | **Tab 5 Executive Learning Narrative (F12)** | Sections 1+2 deterministic (What Changed / What Was Discovered / What the System Now Knows). Section 3 gated by GATE-D. PDF export. Weekly digest. | Medium (1 week) | platform_roadmap_v14 |
| 41 | **NHI Behavioral Baselines (F7)** | Service accounts, API keys, AI agents as first-class graph entities. Same ProfileScorer architecture — new entity type. 82:1 machine:human ratio. | Large (2 weeks) | platform_roadmap_v14 |
| 42 | **Flash Tier (pre-ingestion)** | Streaming alert ingestion (Kafka/Kinesis). Fast-path bypass for known ransomware/APT patterns. Analyst corrections compound to reduce noise over time. | Large (2 weeks) | platform_roadmap_v14 |
| 43 | **ContextConnectors (F13)** | Slack, email, vendor advisory → LLM+template extraction → claims → σ cells. Gated by GATE-D. | Medium (1 week) | platform_roadmap_v14 |
| 44 | **SynthesisNode (F15)** | σ values stored, versioned, traceable in graph. Audit trail for claim→σ provenance. Gated by GATE-D. | Small (3 days) | platform_roadmap_v14 |
| 45 | **INOVA entity resolution (F11-D)** | Fuzzy matching: "john.smith" in AD = "jsmith" in VPN. SemanticMatcher (deterministic) + INOVA (probabilistic). | Medium (1 week) | platform_roadmap_v14 |
| 46 | **Synthetic Attack Chain Simulator** | On-demand LLM-judge generation of Handala-style multi-stage attack sequences for stress testing and demo. | Medium (1 week) | roadmap_inputs_from_LLMs |
| 47 | **Override learning activation (v6.5)** | OverrideDetector activates at ≥50 positive referral examples. ML-based referral from analyst override history. | Small (3 days, architecture exists) | math_synopsis_v11 §15 |

### 3C — S2P Copilot Build

| # | Item | Description | Effort | Reference |
|---|---|---|---|---|
| 48 | **S2P copilot repo + DomainConfig** | Config exists in cross-graph-experiments (d=8, correlation prior). Needs: create s2p-copilot repo, port S2PDomainConfig, wire to ci-platform DomainRegistry, connect to ProfileScorer. **This is repo creation + wiring, not just config copy.** | **Medium (1 week)** | s2p_copilot_design_v0.4 |
| 49 | **S2P connectors** | D&B, OFAC sanctions, LME/CME commodity feeds. SourceConnectorProtocol implementations. | Medium (1 week) | s2p_copilot_design_v0.4_part2 |
| 50 | **S2P NL templates (40)** | 5 categories × 8 factors. Three-layer template engine. | Medium (LLM-judge draft + human review) | s2p_copilot_design_v0.4 |
| 51 | **S2P seed scenarios (10)** | 6 designed, 4 more needed. Demo: "same learning engine, different domain, same accuracy trajectory." | Small (3 days) | s2p_copilot_design_v0.4_part2 §15 |
| 52 | **S2P simulation (50 decisions)** | Equivalent of SOC live simulation. 50 procurement decisions, 73 seconds, learning visible. | Small (adapts existing SOC sim) | product_strategy_v2 |

### 3D — Multi-Tenant & Platform (v7.0 core)

| # | Item | Description | Effort | Reference |
|---|---|---|---|---|
| 53 | **Per-tenant graph isolation** | Tenant-scoped graph partitions. Self-service onboarding. Required for SaaS model, MSSP channel, and any multi-customer deployment. | Large (2-3 weeks) | platform_roadmap_v14 |
| 54 | **Cross-tenant meta-intelligence (F8)** | Anonymized threat pattern sharing. "37 orgs in FinServ saw T1566.001 targeting CFOs this week." Collective centroid intelligence for cold-start acceleration. Network effect. | Large (2-3 weeks) | platform_roadmap_v14 |
| 55 | **Federated learning protocol** | Formal differential privacy guarantees for cross-tenant sharing. HIPAA/DORA/CMMC-safe. | Large (quarter+) | roadmap_inputs_from_LLMs |
| 56 | **A2A/MCP protocol (F10)** | Google A2A + Anthropic MCP. SOC Copilot as decision intelligence layer in multi-agent architectures. | Medium (1-2 weeks) | platform_roadmap_v14 |
| 57 | **Level 2: GraphAttentionBridge** | Cross-domain enrichment. register_domain(), enrich(), sweep(). Periodic, not per-alert. Firewall: cannot update μ. σ is the channel. **Unblocks EXP-G1 (#8).** | Large (2-3 weeks) | platform_roadmap_v14 |
| 58 | **Four Clocks specification** | Dimensionality, encoding, concatenation rules, Decision Clock independence test. Required before Level 2/3. | Design doc (1 week) | planning_catalog_v1 |
| 59 | **MSSP partner portal** | Partner deploys for 20+ clients. Meta-graph enrichment across client base (opt-in). Partner certification. 10× revenue multiplier. | Large (3-4 weeks) | platform_roadmap_v14 |

---

## PHASE 4: GTM & DOCUMENTATION

*Note: DPA and Pilot Playbook can start Week 3 (no experiment dependency). Microsoft Threat Analysis uses Four Clocks at Clock 1-2 vs 3-4 level — this does NOT require EXP-G1 (γ validation). The Four Clocks framework is established; EXP-G1 validates the temporal compounding NUMBER, not the framework itself. Microsoft analysis proceeds without γ.*

| # | Document | Effort | Source Material | Priority |
|---|---|---|---|---|
| 60 | **DPA template** | 1 day | Centroid + kernel weight ownership, conservation law guarantees, learning health SLA, data residency. | **P0 — blocks first contract** |
| 61 | **90-Day Pilot Playbook** | 1 day | advisory_v4 Slide 23 + roadmap_v19 Phase 4 (shadow mode). Week-by-week with P28 pipeline stages. Success criteria. Expansion triggers. | **P0 — blocks first pilot** |
| 62 | **Build vs. Buy Brief** | 0.5 day | ~104 experiments, 390-cell factorial, 478+280 tests. "Your team would take 18 months." | **P0** |
| 63 | **Microsoft Threat Analysis v1** | 1 day | Four Clocks framework (Clock 1-2 vs 3-4, no γ dependency). "Microsoft operates at Clock 1-2. We operate at Clock 3-4." Killer line: "After 1,000 decisions, ask both systems how they got smarter. Only one can answer." | **P0** |
| 64 | **Regulatory Tailwind Map** | 1 day | EU AI Act August 2, 2026 = enforcement. Product IS compliance architecture (audit trail, explainability, human oversight). No competitor has made this claim. | **P0 — 4.5 months to enforcement** |
| 65 | **Three Unconditional Claims** | 0.5 day | Consistency + Readability + Ownership. No qualifiers needed. One-page messaging. | **P1** |
| 66 | **Four Clocks Investor Brief** | 0.5 day | Deck Slide 30 + Stryker Figure 4. "Clock 1-2 = opex. Clock 3-4 = capital investment that appreciates." | **P1** |
| 67 | **Stryker-style analysis template** | 0.5 day | Repeatable 48-hour process for every major public incident. Content engine: 1 analysis/month. | **P1** |
| 68 | **Competitor comparison series** | 1 day | Dropzone template (Slide 18) applied to Microsoft Security Copilot, CrowdStrike Charlotte AI, generic LLM-native. Five-row structure. | **P1** |
| 69 | **Security posture document** | 1 day | SOC 2 Type I readiness. Self-assessment against control families. | **P2** |
| 70 | **Open Source GTM Playbook** | 1 day | GAE v0.7.0, PyPI, 478 tests. Developer persona. GitHub experience. OSS → enterprise funnel. | **P2** |
| 71 | **Loom demo update** | 0.5 day | DiagonalKernel visible. P28 pipeline. Factorial evidence. Healthcare learning. | **P2** |
| 72 | **Blog v9 update** | 1 day | wix_blog_update_spec_v8_to_v9.md (340 lines). 12 kernel changes + A=4 + referral. | **P2** |
| 73 | **Insurance/underwriting attestation** | 0.5 day | Insurer-friendly: triage controls, approval flows, evidence retention, policy exceptions. | **P3** |

---

## PHASE 5: INFRASTRUCTURE (last)

| # | Item | Description | Effort | Priority |
|---|---|---|---|---|
| 74 | **PostgreSQL + AGE migration** | Production graph backend. Currently Neo4j references in code. | Large (2 weeks) | **P3** |
| 75 | **Kafka/Kinesis streaming** | Real-time alert ingestion for Flash Tier. | Medium (1 week) | **P3** |
| 76 | **Docker/Kubernetes hardening** | Production container orchestration. Health checks, auto-scaling, secret management. | Medium (1 week) | **P3** |
| 77 | **State persistence hardening** | TD-017: crash-safe state. TD-018: eliminate dual write paths. | Medium (1 week) | **P3** |
| 78 | **CI/CD pipeline** | GitHub Actions: pytest + lint + mypy + security scan on push. Auto-publish to PyPI. | Small (3 days) | **P3** |
| 79 | **Monitoring & observability** | Prometheus metrics, Grafana dashboards, alert on conservation law violations, learning health. | Medium (1 week) | **P3** |

---

## SEQUENCING SUMMARY

```
PHASE 0 (Day 1): Immediate Fixes
  0a: Frontend visual validation (all 5 tabs)
  0b: θ_min harness fix (0.434→0.467)
  0c: soc_copilot_design 4 mechanical fixes
  0d: math_synopsis v11 referral verify
  0e: TD-034 DEC-DEC double prefix fix

PHASE 1 (Weeks 1-4): Design Strength
  Week 1: V-CGA-FROZEN (50-seed, 2 conditions) — single highest risk
          V-SIM data generation (9 LLM-judge streams)
          TD-034 LLM-judge stream validation (SOC + S2P)
          Claims registry check: v3.1→v6 alignment
  Week 2: V-SIM pipeline run + analysis
          V-ENRICHMENT-NEGATIVE (2 personas × 20 seeds)
          V-MV-RISK + V-MV-CONVERGENCE + V-MV-CONSERVATION (factorial analysis)
          EXP-S2-REPRO at A=4 reconfirmation (60 runs)
          Claims registry update batch 1
  Week 3: P4-F + P4-COMPLACENCY (poisoning + complacency, 30 seeds each)
          PROD-5 convergence calendar
          Gap G4 interaction mini-factorial (8 cells × 20 seeds)
          S2P-V3B + penalty_ratio validation
  Week 4: V-UCL-VALUE analysis
          S2P correlation consensus (3 additional judges)
          All claims registry updates from experiment results
          Decision: Adj. C narrative (pass/fail from V-CGA-FROZEN)
          Claims registry update batch 2

PHASE 2 (Weeks 5-7): Intelligence Layer
  Week 5: EXP-S5 full pipeline (S5a/S5b already ✅)
  Week 6: EXP-S6 briefing quality + EXP-S7 Ask-the-Graph
  Week 7: EXP-L2-POISON safety
          GATE-D decision
          Claims registry update batch 3

PHASE 3 (Weeks 5-16): Code — overlaps with Phase 2
  Week 5-6: ci-platform P28 wiring (~150 lines) + R2/R7 Cypher + Adj. G
  Week 7-9: Attack chain correlation (F6, 2-3 weeks) + Multi-SIEM (F5)
  Week 10-11: NHI baselines (F7) + Flash Tier + INOVA entity resolution
  Week 12-13: S2P copilot build (repo + config + connectors + templates + simulation)
  Week 14-15: Multi-tenant infrastructure + cross-tenant meta-intelligence
  Week 16: A2A/MCP + Level 2 GraphAttentionBridge + MSSP portal foundation
  Post-Level 2: EXP-G1 (γ validation, #8)

PHASE 4 (Weeks 3-8): GTM — overlaps with coding
  Week 3-4: DPA + Pilot Playbook + Build vs Buy + Microsoft Threat Analysis
  Week 5-6: Regulatory Tailwind Map + Three Claims + Investor Brief
  Week 7-8: Competitor series + Stryker template + Blog v9 + Loom demo

PHASE 5 (Weeks 12-16): Infrastructure
  Week 12-13: PostgreSQL + AGE migration
  Week 14: Kafka/Kinesis + Docker hardening
  Week 15: State persistence + CI/CD
  Week 16: Monitoring + observability
```

---

## RISK REGISTER

| Risk | Impact | Mitigation | Status |
|---|---|---|---|
| **V-CGA-FROZEN fails** | Bottom-right quadrant (~10-15%) loses compounding story. S2P + healthcare messaging narrows to Tier 2 only. | Accept smaller addressable market. Reframe CGA as enrichment infrastructure, not accuracy lever. | **NOT YET RUN** |
| **TD-034 LLM-judge streams disagree with synthetic result** | τ=0.08 may not hold on realistic distributions. CalibrationProfile needs per-deployment τ. | P28 pipeline already supports per-customer τ sweep. Contained. | Not yet run |
| **V-SIM reveals KernelSelector failure** | P28 pipeline needs redesign. Deployment qualification suspect. | KernelSelector has 4/4 on known personas. V-SIM tests novel industry profiles. | Not yet run |
| **GATE-D fails** | Intelligence layer deferred. Tab 5 Section 3 display-only. σ not in scoring loop. | Tab 5 Sections 1+2 still ship. Intelligence value deferred, not lost. | S5a/S5b ✅, S5/S6/S7 pending |
| **S2P penalty_ratio wrong** | S2P false-approve rate too high or false-reject rate too high. | Ratio is configurable. Customer-tunable per deployment. 5:1 is starting point. | Design estimate only |
| **EU AI Act audit gap** | Art. 15 kernel metadata incomplete at enforcement (Aug 2, 2026). | Adj. G ships with v6.0. ~50 lines. | In plan |
| **Microsoft adds learning** | Clock 3-4 differentiation narrows. | Network effects (conservation law + graph enrichment) hard to replicate. Monitor quarterly. | Ongoing |

---

## METRICS — WHAT "DONE" LOOKS LIKE

| Milestone | Metric | Target |
|---|---|---|
| Phase 0 complete | All 5 immediate fixes applied | Day 1 |
| Design strength | All P0/P1 experiments complete with statistical significance | 0 unvalidated critical claims |
| V-CGA-FROZEN | Graph enrichment lift on frozen scorer (3 metrics: σ reduction, convergence speed, IKS trajectory) | >0pp with p<0.01 (50 seeds) |
| V-SIM | P28 pipeline correct on synthetic deployments | 8/9 streams correct |
| GATE-D | Intelligence pipeline end-to-end (S5a ✅, S5b ✅, S5+S6+S7 pending) | All 3 remaining pass |
| SOC MVP | Attack chains + Multi-SIEM + NHI + benchmarking | Tier 2 value demonstrated |
| S2P MVP | 50-decision simulation + NL templates + connectors | "Same engine, different domain" demo |
| Platform proof | Multi-tenant + cross-tenant + A2A/MCP | 2 tenants, anonymized sharing working |
| GTM ready | DPA + Pilot + Microsoft analysis + Regulatory map | Outreach can begin |
| Test count | GAE + SOC + ci-platform + experiments | >1,200 total tests |
| Experiment count | Statistically conclusive, CI-bounded | >130 experiments |

---

## v1→v2 CHANGE LOG

| Change | Source | What Changed |
|---|---|---|
| Version label v5.6→v5.5 | Coding session correction #1 | No v5.6 exists |
| TD-034 SOC marked ✅ DONE | Coding session correction #4 | τ=0.08 optimal (ECE=0.052). Remaining: LLM-judge stream validation |
| EXP-G1 reclassified | Coding session correction #8 | "P1 design now" → "P1 run when #57 ships. Design already complete." |
| EXP-S5a marked ✅ DONE | Coding session correction #21 | 460 claims, 5 categories. March 2026. |
| EXP-S5b marked ✅ DONE | Coding session correction #22 | LLM F1=0.877. March 2026. |
| Attack chain effort revised | Coding session correction #36 | 1-2 weeks → 2-3 weeks (multi-hop schema) |
| S2PDomainConfig effort revised | Coding session correction #48 | Small → Medium (needs repo creation + wiring) |
| Phase 0 added (5 items) | Coding session MISS-1 through MISS-5 | Frontend validation, θ_min fix, 4 doc fixes, DEC-DEC prefix |
| #8b EXP-S2-REPRO at A=4 added | Coding session MISS-7 | Poisoning resilience reconfirmation at A=4 |
| #16b Claims registry cadence added | Coding session MISS-8 | Rolling update after each experiment batch |
| #34 R2/R7 Cypher queries specified | Coding session MISS-5 | Actual query patterns documented |
| V-CGA-FROZEN metrics sharpened | Coding session Issue 2 | 3 specific metrics: σ_per_factor, convergence speed, IKS trajectory |
| P28 wiring clarified | Coding session corrections #28-30 | "Lines of NEW code" → "wiring existing GAE components" |
| Microsoft analysis deframed from γ | Coding session Issue 1 | Four Clocks framework ≠ γ number. Analysis proceeds without EXP-G1. |
| GATE-D updated | S5a/S5b ✅ | Binary gate now 3 remaining (S5+S6+S7), not 4 |

---

*Master Action Plan v2 · March 22, 2026*
*86 action items (79 original + 5 Phase 0 + 2 adds). 6 phases. 27 experiments (2 already ✅, 25 remaining).*
*14 corrections from coding session review applied. Design strength first.*
*No "real customer data" dependencies. Everything LLM-judge synthesizable.*
*"The moat is the graph, not the model. The accumulated intelligence is not replicable."*
