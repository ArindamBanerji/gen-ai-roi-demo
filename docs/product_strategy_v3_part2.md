## Part 5: Gap Analysis by Layer

### Layer 1: Domain Ontology (Configuration)

**What works:** SOC domain config clean (6 categories, 4 actions, 6 factors — A=4 confirmed, refer_to_analyst via confidence gate). S2P: 5 categories, 5 actions, 8 factors (A=5 — intentional asymmetry). DomainConfig protocol domain-agnostic. Bootstrap calibration provides warm-start. Alert type → category mapping complete (v5.5-R6 ✅ SHIPPED). S2PDomainConfig updated to d=8.

**Gaps (updated for v6.0):**

**G-L1-1** ✅ RESOLVED (v5.5). Alert type → category mapping complete. GATE-R = 100%.

**G-L1-2** Bootstrap category distribution is configurable (v5.5 ✅). Real distribution from P28 Phase 1 import replaces bootstrap within 30 days.

**G-L1-3** No mechanism to correct wrong prior centroids in production without modifying config. Fix: centroid editor UI or management API (v6.0).

**G-L1-4** S2P domain designed and DomainConfig updated (d=8, domain-level scores). S2P 10-scenario demo at v6.5. Full S2P at v7.0.

---

### Layer 2: Meta-Graph (Profile Centroids)

**What works:** μ ∈ ℝ^(6×4×6) = 144 values (SOC, A=4), all readable. Clipping to [0,1] enforced. Bootstrap warm-start converged. Centroid pull/push learning with kernel-aware gradient. Asymmetric η: η_confirm=0.05, η_override=0.01 (validated across full quality spectrum AND AMBER noise range — CLAIM-44, CLAIM-52 PROMOTED to UNCONDITIONAL at v6.0). IKS visible (v5.5 ✅). Chart A centroid drift visible (v5.5 ✅).

**Gaps (updated for v6.0):**

**G-L2-1** ✅ RESOLVED (v5.5). Chart A shows actual centroid drift per decision.

**G-L2-2** ✅ RESOLVED (v5.5). IKS (Institutional Knowledge Score) visible in Tab 2.

**G-L2-3** ✅ RESOLVED (v5.5). Bootstrap decisions tracked separately from analyst decisions.

**G-L2-4** σ synthesis bias (Loop 4) remains PROPOSAL. Gated by GATE-D/V. This is correct discipline.

**G-L2-5 (NEW v6.0):** Kernel weight evolution not yet visible. DiagonalKernel weights (1/σ²) change as P28 refines per-factor σ estimates. The CISO should see: "device_trust weight dropped from 0.12 to 0.04 as noise measured → the system learned your noise profile." This is the second compounding signal alongside centroid learning. Fix: kernel weight evolution chart in Tab 2 (v6.0).

---

### Layer 3: Mathematical Engine (GAE Library) — MAJOR UPDATE v3

**What works (v6.0):**
- ProfileScorer with **pluggable kernels: L2Kernel + DiagonalKernel** (v6.0 DEFAULT)
- KernelSelector: Phase 2 rule (noise_ratio>1.5→diagonal), Phase 3 rolling 100-window shadow, Phase 4 lock at 250 decisions. 4/4 correct in validation.
- CovarianceEstimator: online covariance collection (Ledoit-Wolf shrinkage). Collects at v6.0, does NOT affect scoring. Research asset for v7.0.
- τ=0.1, ECE=0.036 (V3B). Learning with asymmetric η + kernel-aware gradient.
- run_evaluation(), compute_judgment(), run_ablation() all implemented.
- **478 GAE tests.** Apache 2.0. PyPI published.
- gae/calibration.py: check_conservation(), derive_theta_min(), compute_optimal_tau(), compute_breach_window(), compute_eta_override().
- gae/fisher.py: estimate_fisher_information(), predict_n_half(), enrichment_multiplier().

**Previous gaps — status update:**

**G-L3-1** ✅ RESOLVED (v5.5). Category-specific threshold API shipped. PROD-4: 40%+ coverage.

**G-L3-2** SynthesisProjector designed but not implemented. Correct — gated by GATE-D/V.

**G-L3-3** Cross-domain knowledge transfer: naïve transfer loses to config by 2-14pp. Transfer priors at v7.0 (gated by META-4). Each domain has its own centroid tensor + its own DiagonalKernel weights.

**G-L3-4 (NEW v6.0):** ShrinkageKernel deprioritized. Off-diagonal correlations added <1pp in 390-cell factorial (CLAIM-57). CovarianceEstimator collects data for v7.0 research. If high-ρ domains emerge (ρ>0.8), shrinkage may matter. Currently: noise ratio is the whole story.

**G-L3-5 (NEW v6.0):** N_half model is not yet kernel-aware. Under DiagonalKernel, high-noise factors learn slower (by design). Overall N_half may shift. V-MV-CONVERGENCE (analysis on factorial data) will fit N_half = f(σ, V, q̄, kernel). Gates v6.5 L-08 dynamic calendar update.

---

### Layer 4: Live Context Graph (PostgreSQL + AGE + FactorComputers)

**What works (v6.0):** 6 FactorComputers producing f ∈ [0,1]^6 via graph traversal. Decision nodes written with factor_vector, action, category, kernel_type, kernel_weights. Outcome write-back triggers kernel-aware centroid update. ThreatIndicator persistence (v5.5 ✅). PostgreSQL 16 + Apache AGE (replaced Neo4j at v2.0). Factor provenance surfaced (v5.5 ✅). CovarianceEstimator collects per-factor σ and full correlation matrix from Layer 4 data.

**Previous gaps — status update:**

**G-L4-1** ✅ RESOLVED (v5.5). Factor node provenance surfaced in Tab 3.

**G-L4-2** ✅ RESOLVED. Factor vector stored properly in PostgreSQL.

**G-L4-3** ✅ RESOLVED (v5.5). ThreatIndicator nodes persist. No re-queries for known IOCs.

**G-L4-4** ✅ RESOLVED (v5.5). CISA KEV integrated.

**G-L4-5** Attack chain correlation designed for v6.0 (L-06). "These 17 alerts are one campaign." Tier 2 pricing unlock. Entity resolution (S-02) is prerequisite.

**G-L4-6** User context enrichment: user enrichment connector at v6.0. Role, recent access changes, behavioral baseline. Critical for insider_threat accuracy.

**G-L4-7 (NEW v6.0):** Residual tracking (~30 lines, log only). Tracks decisions where system is confident AND wrong. Feeds v7.0 factor extensibility (design_note_v2 §5.1). When residual cluster reaches N≥20: candidate new factor flagged.

---

### Layer 5: Control Plane (Feedback Loops)

**What works (v6.0):** Loop 1 (Score): ProfileScorer live with DiagonalKernel. Loop 2 (Learn): kernel-aware centroid update on verified outcomes. Loop 3 (Reward/Penalize): 20:1 asymmetry + conservation law α·q·V ≥ θ_min (two thresholds: absolute floor + relative drop). ConservationMonitor with AMBER auto-pause (v6.0 ✅). Var(q) per-analyst logged. KernelSelector as control plane decision: calibrates the distance metric, not just τ.

**Previous gaps — status update:**

**G-L5-1** Loop 4 (Synthesize) remains PROPOSAL. Correct — GATE-D/V pending.

**G-L5-2** ✅ RESOLVED (v5.5). Graduated human review triggers.

**G-L5-3** ✅ RESOLVED (v6.0). Drift detection via ConservationMonitor + AMBER auto-pause. Conservation law detects quality drops within 5 days (CLAIM-46). Recovery <1 day (CLAIM-50 PROMOTED).

**G-L5-4** ✅ RESOLVED (v5.5). 40%+ auto-approve (PROD-4).

**G-L5-5 (NEW v6.0):** KernelSelector is a Layer 5 control decision. The system calibrates TWO things: sensitivity (τ via gain scheduling at v6.5) and geometry (kernel via KernelSelector at v6.0). This makes Layer 5 richer — the control plane governs not just the learning rate but the distance metric itself.

**G-L5-6 (NEW v6.0):** R score (continuous corruption risk function) computed as DIAGNOSTIC alongside three-variable gate. R may replace the threshold gate at v6.5 (gated by V-MV-RISK). This gives Layer 5 a continuous risk signal rather than discrete GREEN/AMBER/RED.

**G-L5-7 (NEW v6.0):** Var(q) per-analyst observation logged but not yet a gating condition. At v6.5, becomes a gating condition (gated by V-MV-CONSERVATION false alarm rate). Catches bimodal teams (q̄=0.75 but half at 0.90, half at 0.60).

---

## Part 6: Gap Analysis by Product Surface

### Tab 3: Alert Triage (Daily driver)

| v5.5 State (SHIPPED) | v6.0 Addition |
|---|---|
| Factor breakdown with provenance nodes | + DiagonalKernel weight per factor: "device_trust: 0.73, weight 0.04 (noisy)" |
| NL template explanation | + kernel-aware template: "device_trust was DOWN-WEIGHTED because it's noisy in your environment" |
| Auto-approve: 40%+ at ≥85% per-category | + kernel-specific confidence calibration |
| Alert type → category routing: 100% | Unchanged |
| "This feedback updated your profile" | + "The kernel weight for this factor will update at next P28 cadence" |

---

### Tab 2: Runtime Evolution (Proof-of-compounding surface)

| v5.5 State (SHIPPED) | v6.0 Addition |
|---|---|
| Chart A: centroid drift per decision | + kernel weight evolution chart |
| IKS: 0-100, trend visible | + kernel-level IKS component: "centroids: +14 pts. kernel weights: +8 pts." |
| "The 5 decisions that moved it most" | + "Factors that changed kernel weight this cadence" |
| Bootstrap: separately tracked | Unchanged |

**What Tab 2 should answer for a CISO at v6.0:** "Is this learning? (Yes — IKS 47, up 3 this week.) How much better? (+7.2pp since deployment.) What did it learn? (Your device_trust data is noisy — weight dropped to 0.04. Threat_intel is reliable — weight stayed at 1.0. The system learned YOUR noise profile.)"

---

### Tab 4: Compounding Analysis (ROI and autonomy story)

| v5.5 State (SHIPPED) | v6.0 Addition |
|---|---|
| ROI calculator (projected) | + Frozen Mode ROI (realized Tier 1 value for RED-zone deployments) |
| Evidence Ledger compliance export | + kernel metadata in per-decision records (Adj. G) |
| 20:1 asymmetry visualization | Unchanged |
| Three-tier time savings | Unchanged |

**What Tab 4 should answer for a CFO at v6.0:** "We deployed N months ago. X decisions handled. Y% accuracy at deployment, Z% now (DiagonalKernel: +W pp from kernel alone). $V in analyst time saved. Frozen Mode value: $U/month even before learning. Here's the audit trail with kernel provenance."

---

### Tab 5: Executive Briefing

| v5.5 State (SHIPPED) | v6.0 Addition |
|---|---|
| Panel A: Weekly narrative (What Changed / Discovered / Now Knows) | + kernel section: "The system refined its noise profile this week" |
| Panel B: Ask-the-graph (15 templates) | + kernel queries: "What's the noise ratio for my deployment?" |
| Risk posture: IOC count, escalations | Unchanged |
| Autonomy envelope: % handled automatically | Unchanged |

---

### Shadow Mode

| v5.5 State (SHIPPED) | v6.0 Change |
|---|---|
| 30-day shadow, agreement rate by category | **250 verified decisions minimum** (data-driven, not calendar) |
| Shadow report: disagreements with factor breakdown | + multi-kernel shadow: both L2 and Diagonal scored. KernelSelector recommends. |
| "Activate live mode" button | + KernelSelector locks recommendation at 250 decisions |

---

## Part 7: Gap Analysis by Offering

**Offering Gap 1: The Demo Problem** — ✅ RESOLVED (v5.5). Docker Compose deployment. Hosted preview available. One URL, zero setup. Live simulation: 50 decisions, 73 seconds.

**Offering Gap 2: The Proof Problem** — ✅ RESOLVED (v5.5). IKS: 0-100 score increasing over time. Chart A: visible centroid drift. v6.0 adds kernel weight evolution as second proof dimension.

**Offering Gap 3: The Explain Problem** — ✅ RESOLVED (v5.5). NL template engine: 24 templates (6×4), three layers, deterministic. v6.0 adds kernel weight explanation layer.

**Offering Gap 4: The Second Domain Problem** — IN PROGRESS. S2PDomainConfig updated (d=8, domain-level scores). 10-scenario demo at v6.5. Full S2P at v7.0. DiagonalKernel validated on S2P (+6.8pp). Same kernel framework, different noise profile.

**Offering Gap 5: The Regulatory Story** — ✅ LARGELY RESOLVED (v5.5/v6.0). EU AI Act documentation shipped. Evidence Ledger export. Factor provenance. v6.0 adds: DiagonalKernel in Art. 15 (Robustness), KernelSelector metadata in per-decision records (Adj. G), deployment qualification audit trail.

**Offering Gap 6 (NEW v3): The Healthcare Story** — ✅ RESOLVED by DiagonalKernel. Healthcare was the #1 target vertical (Stryker analysis) but the #1 segment where learning didn't work. DiagonalKernel fixes this: +3.7pp learning at σ≈0.22. 4 personas confirm (r=0.990). Sales motion: "Learning from Day 1." See design_gap_analysis_v6 G1.

---

## Part 8: v5.5 Requirements — ALL SHIPPED ✅

All v5.5 Tier 1-3 requirements from v2.0 have been delivered. Status summary:

**Tier 1 — Demo-blocking:** ALL SHIPPED

| Requirement | Status | Evidence |
|---|---|---|
| v5.5-T1-1: NL Template Engine | ✅ SHIPPED | 24 templates (6×4), three layers, deterministic |
| v5.5-R4: Institutional Knowledge Score | ✅ SHIPPED | 0-100, κ* calibrated (PROD-1) |
| v5.5-R3: Chart A — Centroid Drift | ✅ SHIPPED | Per-decision centroid delta, color-coded |
| v5.5-R8: Shadow Mode | ✅ SHIPPED | Zero-risk entry for enterprise SOCs |
| v5.5-R1: Auto-Approve 40%+ | ✅ SHIPPED | PROD-4: ≥85% per-category accuracy |

**Tier 2 — Sales-blocking:** ALL SHIPPED

| Requirement | Status | Evidence |
|---|---|---|
| v5.5-R2: Factor Node Provenance | ✅ SHIPPED | Provenance in Tab 3 |
| v5.5-R7: Threat Intel Persistence | ✅ SHIPPED | ThreatIndicator nodes, 24h TTL |
| v5.5-R5: Tab 5 Panel A — Executive Briefing | ✅ SHIPPED | Weekly narrative, no σ required |
| v5.5-R6: Alert Type → Category Mapping | ✅ SHIPPED | GATE-R = 100% routing |
| v5.5 (new): ReferralRules R1-R7 | ✅ SHIPPED | Policy-based VETO referral routing (72.7% DR, 12% FPR). Confidence gate for action routing only. 280 SOC tests. |

**Tier 3 — Enterprise-readiness:** ALL SHIPPED

| Requirement | Status |
|---|---|
| Docker Compose VPS Deployment | ✅ SHIPPED — <5 min on clean VPS |
| Compliance Export | ✅ SHIPPED — Evidence Ledger + EU AI Act export |
| Checkpoint/Rollback (TD-033) | ✅ SHIPPED |

**v5.5 Experiment Track:** ALL COMPLETE

| Experiment | Status |
|---|---|
| FX-1-PROXY-REAL | ✅ COMPLETE — 2,430 IOC records |
| GATE-R | ✅ COMPLETE — 100% routing accuracy |
| EXP-S2-REPRO | ✅ COMPLETE — 0.15pp at 20% poison |
| Phase 1 persona sweeps (6 sweeps, 24 personas) | ✅ COMPLETE |

**v6.0-design Experiment Track (ran post-v5.5 alpha, informs v6.0 design):** ALL COMPLETE

| Experiment | Status |
|---|---|
| V-B1 / V-B3 / V-CL-RECOVER | ✅ COMPLETE — Priority 1 pre-ship |
| V-MV-KERNEL factorial (390 cells) | ✅ COMPLETE — DiagonalKernel validated |
| V-HC-CONFIG-DIAGONAL (4 personas) | ✅ COMPLETE — Healthcare learning confirmed |
| KernelSelector validation (4 deployments) | ✅ COMPLETE — ratio>1.5 rule 4/4 correct |

---

## Part 9: v6.0 Requirements — UPDATED for DiagonalKernel

v6.0 is the revenue gate. First customer signs DPA, connects SIEM, runs the product.

### v6.0 Core — DiagonalKernel + Deployment Qualification (NEW)

| Requirement | Layer | Status |
|---|---|---|
| **DiagonalKernel (1/σ², v6.0 DEFAULT)** | GAE (kernels.py) | **✅ DONE** — 478 tests. +13.2pp SOC, +6.8pp S2P. |
| **KernelSelector** (ratio>1.5→diagonal, rolling 100-window, 250 decisions) | GAE (kernel_selector.py) | **✅ DONE** — 4/4 correct. |
| **CovarianceEstimator** (collects only, v7.0 research) | GAE (covariance.py) | **✅ DONE** |
| **P28 deployment qualification pipeline** (6 phases, 250-decision shadow) | ci-platform | ~90 lines remaining (Phase 2 kernel integration, Phase 3 multi-kernel shadow, Phase 4 qualification) |
| **Deployment gate** (kernel-dependent: Diagonal GREEN≤0.157, AMBER≤0.25, RED>0.25) | ci-platform | ~10 lines |
| **ConservationMonitor Var(q) observation** | ci-platform | ~20 lines (logged, not gating) |
| **Residual tracking** (log only, feeds v7.0 factor extensibility) | ci-platform | ~30 lines |

### v6.0 Procurement Gates (blocks contract signature)

| Requirement | Implementation | Status |
|---|---|---|
| SAML authentication (SSO) | gen-ai_roi::auth/saml.py | Planned |
| PII redaction at ingestion | ci-platform::redaction.py | Planned |
| Cloud deployment, SLA-backed | Docker Compose + monitoring | Planned |
| Multi-SIEM (Splunk + Sentinel, bidirectional) | ci-platform::connectors/ | Planned |
| Entity resolution (deterministic) | ci-platform::entity_resolution.py | Planned |

### v6.0 Pilot Success (blocks value proof)

| Requirement | Why It Matters |
|---|---|
| Data onboarding pipeline (S-08) | 30-day history in ~15 min. Graph has context before shadow. |
| Sentinel enrichment write-back (S-01-WB) | Campaign, IKS, confidence → Sentinel. "Complement Microsoft." |
| Attack chain correlation (L-06) | "These 17 alerts are one campaign." Tier 2 pricing unlock. |
| Analyst benchmarking report (L-04) | Per-shift quality breakdown. Staffing recommendation. |
| Tab 5 executive narrative (L-05) | What Changed / Discovered / Now Knows. Retention mechanism. |
| Onboarding calendar (L-08) | Kernel-aware convergence predictions. V-MV-CONVERGENCE updates at v6.5. |
| Learning health monitor (L-09) | Conservation + coverage + drift + σ_mean (kernel-aware thresholds). |

### v6.0 Decision Economics

| Requirement | Implementation |
|---|---|
| Decision value tagger | time_saved, cost_avoided, risk_delta per decision. SOC: 44 min/alert. |
| Quarterly CFO summary | Total savings, hours recovered, ROI. CFO-auditable. |
| **Frozen Mode ROI calculator** | Tier 1 value for RED-zone deployments. 44 min × V × auto_approve_rate × cost/hr. |
| Value-based variant evaluation | v6.0: tags only. v6.5: wired to AgentEvolver. |

### v6.0-R1: Synthesis Layer — σ [GATE-M dependent]

**Gate:** GATE-M — EXP-S2-REPRO passed (0.15pp at 20% poison). GATE-D and GATE-V still pending.

**If GATE-D passes:** Live σ from CISA KEV. Daily pull → claim extraction → σ update. Auto-approve safety interlock for active campaigns.

**If GATE-D fails:** σ stays display-only in Tab 5. Intelligence layer deferred.

**Non-negotiable:** μ NEVER updated from σ. Loop 2 uses verified outcomes only.

### v6.0-R2: Attack Chain Correlation (L-06)

"If this alert is real, what else is at risk?" Multi-hop graph query. UI: blast radius estimate in Tab 3. Foundation for campaign detection + Tier 2 pricing. Entity resolution (S-02) is prerequisite.

### v6.0-R3: First Production Customer

Gates: v5.5 hosted 30+ days. Customer DPA signed. P28 pipeline complete (250-decision shadow with KernelSelector). DiagonalKernel validated on their data. All validation pre-ship — shadow mode CONFIRMS predictions, not discovers bugs.

Customer story (updated for DiagonalKernel):
1. Signs DPA → connects SIEM
2. P28 Phase 2: per-factor σ measured, noise_ratio computed, KernelSelector recommends diagonal
3. Shadow mode: 250 decisions, both kernels scored, rolling window tracks agreement
4. KernelSelector locks: "DiagonalKernel selected (ratio=3.2×, confirmed at 250 decisions)"
5. Deployment gate: GREEN under DiagonalKernel (σ_mean=0.15, was AMBER under L2)
6. Learning activates Day 1 — no remediation required
7. 90 days later: IKS 47, 40%+ auto-approve, kernel weights show firm-specific noise profile

### v6.0-R4: S2P Domain (second vertical — platform proof)

S2PDomainConfig: d=8 domain-level scores (Supplier, Logistics, Demand, Inventory, Regulatory, Geopolitical, Financial, Environmental). penalty_ratio=5.0. θ_min=0.35. 10 seed scenarios. DiagonalKernel validated on S2P (+6.8pp). Demo: "same learning engine, same kernel framework, different domain, +6.8pp from kernel alone."

### v6.0-R5: Multi-SIEM Connector

SourceConnectorProtocol: Splunk + Microsoft Sentinel. Bidirectional (ingest + write-back). Entity resolution: same user across SIEMs → same graph node. Alert normalization to canonical schema. σ re-measurement on source change (D9, kernel-aware thresholds).

### v6.0 Experiment Track (remaining):

| Experiment | What It Gates | Status |
|---|---|---|
| P4-F: Subtle poisoning | Gate 5 validation | Run before v6.0 |
| P4-COMPLACENCY: Conservation early warning | Conservation law story | Run before v6.0 |
| TD-034: τ on synthetic alert streams | Blocks going live | Run before v6.0 |
| PROD-5: Convergence calendar | L-08 feature | Run before v6.0 |
| **V-SIM: Full pipeline on synthetic data** | **P28 end-to-end (3 industries × 3 judges = 9 streams)** | **Run before v6.0** |

### v6.0 GTM Readiness

| Item | Effort |
|---|---|
| DPA template (centroid ownership, conservation law, kernel weights, learning health) | 1 day |
| Security posture document (SOC 2 Type I readiness) | 1 day |
| Vendor Security Questionnaire (VSQ) pre-fill | 0.5 day |
| Loom demo update (DiagonalKernel, P28, factorial evidence) | 0.5 day |
| 90-Day Pilot Playbook (from advisory session Slide 23) | 1 day |
| Build vs. Buy Brief (~104 experiments, 390-cell factorial) | 0.5 day |
| Microsoft Threat Analysis v1 (Four Clocks framework) | 1 day |
