# Compounding Intelligence Platform — Product Roadmap

**Compounding Decision Intelligence Platform**
v3.0 → v8.0 · Security · Supply Chain · Financial Services

Dakshineshwari LLC · March 21, 2026 · Confidential

*v19 — March 21, 2026. V-MV-KERNEL factorial complete (390 cells). DiagonalKernel (1/σ²)
is v6.0 DEFAULT: +13.2pp SOC, +6.8pp S2P, +3.7pp healthcare learning. Noise ratio is the
whole story (r=0.990). Off-diagonal correlations add <1pp — ShrinkageKernel deprioritized
to v7.0. Factor quarantine mask DEPRECATED (mask was WORSE than L2: -6pp Day 1).
KernelSelector ships with rolling 100-window, ratio>1.5 rule, 250-decision stabilization.
Healthcare go-to-market changes from "remediate first" to "learning from Day 1."
GREEN zone nearly doubles under DiagonalKernel (σ≤0.157). GAE at 478 tests. SOC at 280 tests.*

*Changes from v18:*
- **DiagonalKernel (1/σ²) is v6.0 DEFAULT.** +13.2pp on heterogeneous SOC data. Weights come
  from P28 per-factor σ measurement. L2 is cold-start fallback (before σ measured or ratio<1.5×).
- **Factor quarantine mask DEPRECATED.** Binary mask was WORSE than L2 alone: -6pp Day 1 damage
  from zeroing factors. DiagonalKernel's continuous weighting supersedes it completely.
- **Healthcare opens at v6.0.** DiagonalKernel produces +3.7pp learning at σ≈0.22 where L2
  produced +0.3pp (flat). 4 healthcare personas confirm: corr(ratio, advantage)=0.990.
  Sales motion: "Learning from Day 1" replaces "remediate first, then learn."
- **Noise ceiling moves.** Under DiagonalKernel: GREEN≤0.157, AMBER≤0.25, RED>0.25.
  GREEN zone nearly doubles vs L2. Healthcare moves from RED to AMBER.
- **ShrinkageKernel deprioritized** from v6.5 to v7.0 research. Off-diagonal adds -0.2pp
  to +0.8pp across all tests. Explanation A confirmed: noise ratio is the whole story.
- **KernelSelector ships at v6.0.** Phase 2 rule: noise_ratio>1.5→diagonal. Phase 3: rolling
  100-window multi-kernel shadow. Phase 4: lock at 250 verified decisions. 4/4 correct.
- **P28 Phase 3 minimum:** 250 verified decisions (data-driven, not 30 days fixed).
- **ConservationMonitor:** Var(q) per-analyst observation added (logged, not gating at v6.0).
- **Adjustment A shipped at v6.0** (was v6.5). DiagonalKernel IS Adjustment A.
- **GAE at 478 tests** (was 251 at v5.5). +186 kernel/factorial session, +41 referral/coding session. SOC at 280 tests.

---

## The Core Claim

Every AI tool on the market makes better decisions on day one. **This platform makes better
decisions on day one thousand — because every verified decision writes back to a knowledge
graph that makes every subsequent decision richer.**

The mechanism: a triangle of three structural requirements. Remove any vertex and compounding stops.

| Vertex | What It Provides | Without It |
|---|---|---|
| **Context Graph** (UCL + enrichment) | Institutional knowledge that persists across analysts, shifts, and tool changes. Discovery surface grows as n^2.11 (super-quadratic, V1A validated; t^γ compounding projected — EXP-G1 pending). | Decisions don't accumulate. Day 365 = Day 1. |
| **Learning Loops** (ProfileScorer + AgentEvolver + conservation law) | Self-improvement. Centroids evolve: realistic accuracy 71.7% day 1 → 78.9% after 1K decisions (50-seed validated). Mean error decays as (1−η)^n, half-life N_half≈14. | Rich data, no learning. A library nobody updates. |
| **Decision Economics** (value per decision) | The objective function defining "better" — optimizes for institutional value, not just accuracy. SOC: $127/alert full compounding value (frozen mode: 44 min × V × auto_approve_rate × cost/hr). | Can't prove value to CFO. Loops optimize for nothing. |

**The compounding flywheel is self-reinforcing:** As graph matures → N_half decreases → θ_min decreases → Level 2 has more freedom → better framing → more verified decisions → faster graph enrichment → N_half decreases further. The conservation law ensures this flywheel never collapses. I(n,t) ~ O(n^2.11 × t^γ).

**Two levels of institutional judgment — both compound, both are the moat:**

- **Level 1 — Decision Intelligence (ProfileScorer):** Learns *what to decide*. Per-category centroids μ[c,a,:] encode verified organizational judgment. Convergence: mean error decays as (1−η)^n, half-life N_half≈14 at q̄≥0.70 and σ≤0.157 (Borkar 2008, three-judge validated). L2 distance kernel architecturally irreversible (36.89pp over dot product). **DiagonalKernel (1/σ²) is v6.0 DEFAULT: +13.2pp on heterogeneous data. Weights = 1/σ² per factor from P28 measurement. Learns faster on reliable factors, slower on noisy factors.** Below q̄=0.70: confirmations only, ~2× timeline. Under DiagonalKernel: GREEN σ≤0.157, AMBER σ≤0.25, RED σ>0.25. Asymmetric η: η_confirm=0.05, η_override=0.01 (validated, 1C sweep, 5 quality levels).

- **Level 2 — Deployment Intelligence (AgentEvolver):** Learns *how to operate*. K=2 variants. Five-condition gate. A/B requires ≥8 analysts (validated, 1B sweep); teams 3-7 use before/after (designed, V-D4 validation pending); teams ≤2 defer to 180 days. Conservation law α(t)·q(t)·V(t) ≥ θ_min ensures Level 2 never degrades Level 1.

- **Level 3 — Self-Knowledge (v8.0 research):** Learns *about itself*. Self-model tensor Ψ[c] alongside centroid tensor μ[c,a,:]. Meta-learning from own learning dynamics. Formalism pending — same rigor as Levels 1 and 2.

**Three infrastructure layers:** UCL (one governed graph), ACCP (typed-intent routing + conservation enforcement), AgentEvolver (runtime evolution).

**Conservation law — three roles, two thresholds, cause-aware response (v6.5):**
1. Protects Level 1's correction signal (learning quality)
2. Constrains Level 2's optimization freedom (automation safety)
3. Guarantees graph enrichment rate via TRIGGERED_EVOLUTION write-back (knowledge accumulation)

Two thresholds: absolute floor (θ_min) + relative drop (0.7× baseline → AMBER, 0.5× → RED).
v6.5 response is cause-aware: q-drop → freeze category centroids; α-drop → pause auto-approve; V-drop → informational.

**Product boundaries (Phase 1 persona sweeps, 24 personas):**

| Dimension | Boundary | Evidence |
|---|---|---|
| Factor noise | **Under DiagonalKernel (v6.0 default):** GREEN σ≤0.157, AMBER 0.157<σ≤0.25, RED σ>0.25. GREEN zone nearly doubles vs L2. Healthcare (σ≈0.22) = AMBER (learning works, +3.7pp). DiagonalKernel advantage scales with noise ratio (r=0.990, 4 personas). Under L2 (cold start): GREEN σ≤0.105, AMBER 0.105<σ≤0.157, RED σ>0.157. | V-MV-KERNEL (390 cells) + 4 HC personas |
| Alert volume | V≥30 viable. All 6 categories by Day 45. | 1A sweep, 5 volumes |
| Team quality | Learning lift requires q̄≥0.70. Below: +0.5pp (no degradation). | 1C sweep, 5 quality levels |
| Team size (L2) | A/B requires ≥8 analysts. 3-7: before/after (V-D4 pending). ≤2: deferred. | 1B sweep, 5 team sizes |
| Graph enrichment | +7 to +13pp from noise reduction. No dip. Diverging→converging. | 2G sweep, 2 personas |
| Correlated error | Conservation detects within 5 days. Recovery <1 day at all tested volumes (V=50-200). | 2D + V-CL-RECOVER |

### Competitive Position

| | SOAR (Torq, Swimlane) | AI SOC Analyst (Dropzone, Radiant) | Microsoft Security Copilot | **Decision Intelligence (Us)** |
|---|---|---|---|---|
| Core | Workflow orchestration | Per-alert LLM reasoning | Sentinel query + summarization | Graph attention + learning loops |
| Clock | — | Clock 1 (State) | Clock 1-2 (State + Event) | Clock 1-4 (State + Event + Decision + Insight) |
| Learning | Same playbook day 1 & day 1,000 | Better cheat sheet (rented, LLM) | Same answer day 1 & day 180 | Centroids + graph + operational adaptation (owned) |
| Moat | Integrations (replicable) | LLM quality (rented) | Distribution (E5 bundling) | Firm-specific graph (owned, compounding) |
| Our position | "We add intelligence to their workflows" | "We make the new hire a senior analyst" | "We make your Microsoft investment compound" | — |

---

## Architecture — Open Engine, Proprietary Intelligence

| Layer | Repository | License | Purpose |
|---|---|---|---|
| **Graph Attention Engine (GAE)** | graph-attention-engine | Apache 2.0 | Mathematical computation substrate — scoring, learning, convergence, evaluation, **calibration, Fisher information, pluggable kernels (L2/Diagonal), kernel selection, covariance estimation**. 478 tests. |
| **CI Platform** | ci-platform | Apache 2.0 | Shared infrastructure — domain config, schema, connectors, state, entity resolution, onboarding, **ACCP routing, conservation monitoring, gain scheduling, enrichment tracking** |
| **Domain Copilots** | gen-ai_roi (SOC), s2p-copilot | Proprietary | Domain expertise — factors, seed data, pipelines, deployment, **DomainConfig implementations** |
| **Synthetic Data Engine** | ci-platform + LLM judges | Apache 2.0 | Alert stream generation, analyst trajectory simulation, scenario synthesis. Three roles: pre-ship validation, sales preview, onboarding acceleration. Sources: LLM-judge (breadth), web-scraped TI (realism), public incidents (scenarios), SOC workforce research (personas). |

**Production data layer:** PostgreSQL 16 + Apache AGE. Cypher preserved via AGE openCypher. Critical state (centroid tensors, Evidence Ledger, decisions, outcomes) in relational tables with online backup + PITR. Graph traversals (FactorComputers, attack chain correlation) via AGE Cypher.

---

## Version Timeline

| Version | Theme | Deployment | Status |
|---|---|---|---|
| **v3.0-v5.0** | Architecture proved | Local | ✅ Complete |
| **v5.5** | Deployable + Shadow Mode + EU AI Act | Hosted | ✅ Alpha |
| **v6.0** | First Customer + DiagonalKernel + Conservation Law + Decision Economics + Deployment Qualification | Cloud pilot | **Planned — next** |
| **v6.5** | Cause-Aware Conservation + Gain Scheduling + NHI + Fisher Calendar + SC Plugin + S2P Demo | Production | Planned |
| **v7.0** | Multi-Tenant + Transfer Priors + S2P Full + Cross-Tenant Intel | Multi-tenant | Roadmap |
| **v7.5** | Partner Network (MSSP) + Hosted Demo | Partner-deployed | Vision |
| **v8.0** | Level 3: Self-Knowledge + Cross-Domain Discovery | Enterprise | Vision |

---

## Version Details

### v3.0 through v5.0 — [All Complete ✅]

Architecture settled through 25 experiments. ProfileScorer L2 distance kernel validated (36.89pp over dot product). GAE v0.6.0 on PyPI with 251 tests at v5.5 ship. Current: GAE v0.7.0 with 478 tests (+186 kernel/factorial session, +41 referral/coding session: DiagonalKernel + KernelSelector + CovarianceEstimator + ReferralRules added). See roadmap v14 for full details.

---

### v5.5 — Deployable + Shadow Mode + EU AI Act. [Alpha ✅]

All v5.5 blockers resolved. Product is customer-accessible for the first time.

**What shipped:**
- Shadow mode (F1): zero-risk entry for enterprise SOCs
- Docker Compose VPS deployment: <5 min on clean VPS
- IKS (Institutional Knowledge Score): 0-100, κ* calibrated (PROD-1)
- NL templates: 24 templates (6×4), three layers, deterministic
- 40%+ auto-approve coverage at ≥85% per-category accuracy (PROD-4)
- Chart A centroid drift visualization
- Factor provenance trail (ProvenanceNode, EU AI Act Art. 9)
- ThreatIndicator persistence (24h TTL cache-read)
- Evidence Ledger + EU AI Act export
- Checkpoint/rollback
- SemanticRegistry (20 concepts) + QueryCatalog (15 queries)
- GAE v0.6.0: PyPI published, Apache 2.0, README, CONTRIBUTING, examples

**Experiments completed during v5.5:**

| Experiment | Result | Impact |
|---|---|---|
| GATE-R | 100% routing accuracy | Composite accuracy claim activated |
| FX-1-PROXY-REAL | 2,430 IOC records | Factor distributions characterized |
| EXP-S2-REPRO | Poisoning resilience 0.15pp at 20% poison | Safety validated |
| PROD-4 | Per-category auto-approve thresholds | 40%+ coverage |
| PROD-4-A4 | Coverage 4.4%→11.1% | Threshold table updated |
| Frozen scorer | 90.6% accuracy (A=4) | Baseline established. Composite discriminant: 70.4%@85%. |
| EXP-OP3 | ROC 0.99, 0% FA | Early-warning validated |
| P1 (Σ_f) | tr=0.34 (+44%) | L-08 calendar updated |
| PROD-1 | κ* calibrated for IKS | IKS scoring validated |

**Mathematical bridges — three-judge validated (GPT-4o, Claude Opus, Gemini):**

| Bridge | Result | Impact |
|---|---|---|
| Bridge A | Level 2 as conservative contextual bandit | Four-condition gate. Conservation law. |
| Bridge B | Convergence rate = f(graph richness). N_half≈14. | Enrichment multiplier validated. |
| Bridge B Phase C v3 | 1.42× re-convergence acceleration, p<0.0001 | γ>1 mechanism demonstrated. |
| L2-POWER | Gate detects ≥20pp only. 10pp undetectable at N≤1000. | K=2, Gate 5, three-layer defense. |
| L2-POISON | Crude attack detected. Subtle 10pp invisible to gate. | Layered: gate + verification + consistency. |
| META-3 | θ_min 33× below healthy signal at V=60. W=14 for relative threshold. | Two-threshold conservation monitor. |
| Three-judge review | No third timescale. τ = gain scheduling. | Continuous calibration, not meta-learning. |

**38+ experiments completed across v3.0-v5.5.** Full catalog in consolidated_capability_plan_v3.1.

**Phase 1 persona sweeps (run during v5.5 alpha; results inform v6.0 design):**

| Sweep | Personas | Gate | Key Finding |
|---|---|---|---|
| 1C Quality | 5 | ✅ PASS | η_override=0.01 validated across full quality spectrum (q̄=0.57-0.91) |
| 1A Volume | 5 | ✅ PASS | V=30 viable. All 6 categories by Day 45. L-08 conservative at V<50. |
| 1B Team Size | 5 | 3/4 PASS | B-A needs ≥8 analysts, not 4. Night shift 18pp quality gap. |
| 2D Correlated | 2 | 2/4 PASS | Conservation detects campaigns in 5 days. Recovery ~58 decisions. Starvation is protective. |
| 1D Noise | 5 | 3/5 PASS | σ≤0.105 safe. σ>0.157 don't deploy learning under L2. σ>0.215 degrades under L2. **(v19: DiagonalKernel extends learning to σ≤0.25. See V-MV-KERNEL.)** |
| 2G Enrichment | 2 | 2/3 PASS | No dip. +7-13pp from noise reduction. Diverging→converging. |

---

### v6.0 — First Customer + DiagonalKernel + Conservation Law + Decision Economics + Deployment Qualification. [Planned — next]

Real customer data. Revenue gate. Everything answers: "Does this close the contract or make the pilot successful?"

**Procurement gates (blocks contract signature):**

| Capability | ID | Implementation |
|---|---|---|
| SAML authentication (SSO) | I-01 | `gen-ai_roi::auth/saml.py` |
| PII redaction at ingestion | I-02 | `ci-platform::ci_platform/redaction.py` |
| Cloud deployment, SLA-backed | I-03 | Docker Compose + monitoring |
| Multi-SIEM (Splunk + Sentinel, bidirectional) | S-01 | `ci-platform::connectors/splunk.py`, `sentinel.py` |
| Entity resolution (deterministic) | S-02 | `ci-platform::entity_resolution.py` |

**Pilot success features (blocks value proof):**

| Capability | ID | Why It Matters |
|---|---|---|
| Data onboarding pipeline | S-08 | 30-day history in ~15 min. Graph has context before shadow mode. |
| Sentinel enrichment write-back | S-01-WB | Campaign, IKS, confidence → Sentinel incidents. "Complement Microsoft." |
| Attack chain correlation | L-06 | "These 17 alerts are one campaign." Tier 2 pricing unlock. |
| Analyst benchmarking report | L-04 | Accuracy + Level 2 adaptation + consistency. **NEW: per-shift quality breakdown** ("Day: q=0.79. Night: q=0.61. Night shift overrides near-random for juniors."). Staffing recommendation. |
| Tab 5 executive narrative | L-05 | Weekly: What Changed / Discovered / Now Knows. Deterministic, no σ required. |
| Onboarding calendar (static) | L-08 | Per-category convergence predictions. **Assumes selected kernel; N_half may differ between L2 and DiagonalKernel (V-MV-CONVERGENCE updates this at v6.5).** Qualifiers: "Conservative by up to 70% at V<50." "14-day incident adds ~20 days to convergence for affected categories." "data_exfiltration is most noise-sensitive (first to lose convergence as noise increases)." |
| Learning health monitor | L-09 | Conservation law + coverage + drift + **σ_mean (4th condition, kernel-aware thresholds: DiagonalKernel GREEN≤0.157, L2 GREEN≤0.105)**. Auto-pause. DPA clause. |

**Asymmetric η (P0 blocker — ✅ DONE):**

| Item | Implementation | Status |
|---|---|---|
| η_confirm=0.05, η_override=0.01 | ProfileScorer.update(). Override path attenuated 5×. Prevents 13-27pp centroid degradation from low-quality overrides. | ✅ Done, 478 tests passing |
| compute_eta_override() formula | gae/calibration.py. η* ∝ (2q̄-1)/(2σ²_q). Directionally correct, ~2× overestimate vs empirical. Q5 persona sweep is ground truth; per-deployment τ sweep confirms. | ✅ Done |

**Conservation law infrastructure (makes the core claim provable):**

| Capability | Layer | Implementation |
|---|---|---|
| gae/calibration.py | GAE v0.7.0 | check_conservation(), derive_theta_min(), compute_optimal_tau(), compute_breach_window(), check_meta_conservation(), compute_transfer_prior(), **compute_eta_override()**. NumPy only. ~100 lines. Ships with PyPI. Working code: calibration_example.py. |
| gae/fisher.py | GAE v0.7.0 | estimate_fisher_information(), predict_n_half(), enrichment_multiplier(). Ships with PyPI. Used by v6.5 dynamic calendar. |
| ConservationMonitor (shadow mode) | ci-platform | Windowed α·q·V tracking. **Two thresholds:** absolute floor (θ_min = 0.467 for SOC) + relative drop (0.7× baseline → AMBER, 0.5× → RED). GREEN/AMBER/RED + sparkline. **Per-shift decomposition** (day/swing/night α/q/V). **Min-50-decisions smoothing** (below 50: "CALIBRATING"). Decomposes signal drops into α/q/V components. Thresholds from shadow-mode statistics, not hardcoded. Shadow → enforcement at v6.5. **AMBER auto-pause** — when AMBER fires, LEARNING_ENABLED=False automatically. Webhook/Slack alert. ~20 lines. **NEW v19: Var(q) per-analyst observation** — logged at v6.0, gating condition at v6.5 (gated by V-MV-CONSERVATION). |
| Conservation dashboard | soc-copilot UI | "Learning signal healthy (25.5 — floor: 0.47)" + sparkline + shift breakdown. |
| Agreement-rate quality observation (NEW) | ci-platform (Hook 1/2 analysis) | Per-analyst agreement rate on high-confidence decisions (conf>0.90). **v6.0: OBSERVE ONLY — log metrics, don't wire to η.** Feeds v6.5 per-analyst η (Adjustment B). ECE interlock: disabled if ECE>0.10 (Gemini). Quality floor: never estimate below 0.60 (Opus). |

**Decision Economics Layer (structural — pulled from v7.0):**

| Capability | Layer | Implementation |
|---|---|---|
| Decision value tagger | ci-platform | time_saved, cost_avoided, risk_delta per decision. SOC: 44 min/alert baseline. |
| Quarterly CFO summary | soc-copilot UI | Total savings, hours recovered, ROI. CFO-auditable. |
| **Frozen Mode ROI calculator (NEW)** | soc-copilot UI | **Tier 1 value for deployments where learning is frozen (RED zone: σ>0.25 under DiagonalKernel, or σ>0.157 under L2, or q̄<0.70).** Consistency + compliance + frozen auto-approve. At V=200, 8 analysts, 40% frozen auto-approve: 3,520 min/day saved = ~$70K/month. Does NOT use $127/alert (that includes compounding value). Uses 44 min × V × auto_approve_rate × cost/hr directly. Three-judge consensus: highest-leverage non-engineering investment. ~20 lines. |
| Value-based variant evaluation | ci-platform | v6.0: tags only. v6.5: wired to AgentEvolver. |

**Deployment qualification (NEW — from persona sweeps):**

| Capability | Layer | Implementation |
|---|---|---|
| TD-034 mandatory onboarding | ci-platform (P28) | τ sweep on first 200 alerts (synthetic pre-ship, real at deployment). Output: domain_config.tau_initial. ~30 min. NOT optional. Pre-validated on LLM-judge synthetic streams. |
| **DiagonalKernel (v6.0 DEFAULT — from V-MV-KERNEL)** | GAE (ProfileScorer) | **Weights = 1/σ² per factor from P28 Phase 2 measurement.** +13.2pp on heterogeneous SOC, +6.8pp S2P. Healthcare: +3.7pp learning at σ≈0.22. KernelSelector confirms with rolling 100-window during shadow. 478 GAE tests. |
| **KernelSelector (v6.0 — from factorial)** | GAE (kernel_selector.py) | **Phase 2 rule:** noise_ratio > 1.5 → diagonal, else L2. One parameter, no ρ_max. **Phase 3:** scores every alert with both kernels during shadow, rolling 100-decision window. **Phase 4:** locks kernel at 250 verified decisions. 4/4 correct in validation. |
| Deployment gate (UPDATED for DiagonalKernel) | ci-platform (P28) | **Under DiagonalKernel:** GREEN σ_mean≤0.157, AMBER 0.157<σ_mean≤0.25, RED σ_mean>0.25. Three-variable logic (V, q̄) still applies within each band. **Under L2 (cold start):** GREEN≤0.105, AMBER≤0.157, RED>0.157. R score computed as DIAGNOSTIC alongside gate (replaces gate at v6.5 if V-MV-RISK validates). |
| Factor quarantine mask (**DEPRECATED**) | ci-platform (ProfileScorer) | **Binary mask was WORSE than L2 alone: -6pp Day 1 from zeroing factors.** DiagonalKernel's continuous weighting (device_trust at weight 0.04, not 0.0) supersedes. Mask code retained as fallback for extreme edge cases but NOT recommended. REMOVED at v7.0. |
| Noise remediation report (REFRAMED) | soc-copilot UI | Per-factor σ with kernel weight: "device_trust: σ=0.24, weight=0.04 (low influence). Connect Defender → σ drops to 0.10, weight=1.0 (full influence)." **Remediation improves learning but no longer GATES it.** Healthcare: "Learning from Day 1. Remediation accelerates convergence." |
| CovarianceEstimator (COLLECTS only) | GAE (covariance.py) | Collects full covariance data. NOT used for scoring. Research asset for v7.0 shrinkage. Tracks: per-factor σ (feeds DiagonalKernel), correlation matrix ρ (logged, diagnostic). |
| Entity resolution σ prediction | soc-copilot UI | "Connect Entra ID → σ drops 0.19→0.13 → faster convergence under DiagonalKernel." **Sales tool.** |
| Synthetic Data Engine (Phase 0) | ci-platform + LLM judges | Industry-calibrated alert streams + analyst trajectories. Pre-DPA sales preview. Prediction adds: noise ratio, predicted kernel, predicted boundary. Sources: LLM-judge, web-scraped TI, public incidents, SOC workforce research. |

**Onboarding pipeline (P28 redesigned — 6 phases):**

```
Phase 0: PREVIEW → Synthetic Data Engine generates industry-calibrated alert stream.
         Predicts noise ratio, kernel, deployment boundary.
         Output: "Healthcare: predict diagonal (ratio≈3×), AMBER, learning from Day 1."
Phase 1: IMPORT (S-08) → Connect SIEM, ingest 30 days, graph populated
Phase 2: COMPUTE → TD-034 τ sweep + per-factor σ + noise ratio + kernel recommendation (~30 min)
         KernelSelector Phase 2 rule: ratio > 1.5 → diagonal, else L2.
         Delta report: "Predicted ratio=3.0×, actual ratio=3.4×. Kernel: diagonal confirmed."
         Correlation matrix ρ computed (diagnostic, not for kernel selection).
Phase 3: SHADOW → KernelSelector runs BOTH L2 and Diagonal on every alert.
         Rolling 100-decision window tracks per-kernel agreement rate.
         ConservationMonitor runs. Var(q) logged.
         Minimum: 250 verified decisions (not 30 days fixed).
         At V=200: ~4 days. At V=50: ~17 days.
Phase 4: QUALIFY → KernelSelector recommendation locked.
         Deployment gate evaluated under selected kernel's thresholds.
         (DiagonalKernel: GREEN≤0.157, AMBER≤0.25, RED>0.25)
         Conservation stable? Shift quality measured?
Phase 5: ENABLE → Selected kernel active for scoring + learning. η_confirm=0.05, η_override=0.01.
         AMBER auto-pause armed. Frozen Mode ROI calculated for RED-zone categories.
```

**Level 2 redesign (from L2-POWER):**

| Capability | Layer | Implementation |
|---|---|---|
| K=2 variant architecture | ci-platform | Two variants per cycle. N/2 decisions each. Power doubles vs K=5. |
| Gate 5: acceptance-outcome divergence | ci-platform | Observation at v6.0. ≥10pp at N=250, ~88% power. Enforcement at v6.5. |
| Three-layer defense | Claims registry | Gate (≥20pp) + verification (v6.5) + consistency (v6.5). Combined: ~5pp residual. |

**Data capture for future:**

| Capability | Why Now |
|---|---|
| Override comment in Hook 2 | `override_comment: str | None`. Enables OPD at v7.0+. Irreplaceable. |
| Async verification interface | 10% sampling queue. Provider at v6.5. Never blocks pipeline. |

**EU AI Act (enforcement Aug 2, 2026):** L-10 (compliance evidence), L-11 (transparency), L-12 (intervention controls).

**Infrastructure:** ci-platform extraction (~1-2 days), PostgreSQL+AGE migration (~8 days), GAE v0.7.0 (ships PyPI).

**GTM readiness (before any customer/VC conversation):**

| Item | Effort |
|---|---|
| DPA template (centroid ownership, conservation law, learning health clauses) | 1 day |
| Security posture document (SOC 2 Type I readiness, encryption, access controls) | 1 day |
| Vendor Security Questionnaire (VSQ) pre-fill | 0.5 day |
| Loom demo update (v5.5+ capabilities, persona sweep results) | 0.5 day |

**v6.0 Experiments:**

| Experiment | What It Gates | Status |
|---|---|---|
| Phase 1 persona sweeps (6 sweeps, 24 personas) | Product boundaries | ✅ COMPLETE |
| META-3: Breach window | ConservationMonitor | ✅ COMPLETE |
| Bridge B Phase C v3 | γ>1 mechanism | ✅ COMPLETE |
| L2-POWER + L2-POISON | Level 2 redesign | ✅ COMPLETE |
| V-B1: η=0.01 at moderate noise | η holds at σ=0.12-0.157? | ✅ PASS. η=0.01 holds across full AMBER range. |
| V-CL-RECOVER: Recovery at low volume | Recovery claim volume-normalized? | ✅ PASS. <1 day at all volumes. 3-day claim CONSERVATIVE. |
| V-B3: σ threshold cross-validation | σ=0.157 correct at q̄=0.60 and V=50? | ✅ NUANCED. Three-variable ceiling discovered. **(v19: thresholds are L2-specific; DiagonalKernel extends GREEN to σ≤0.157. See V-MV-KERNEL.)** |
| V-HC-CONFIG: Healthcare (binary mask) | Factor quarantine validates? | ✅ **SUPERSEDED by V-MV-KERNEL.** Mask was WORSE than L2 (-6pp Day 1). DiagonalKernel rescues healthcare: +3.7pp. |
| **V-MV-KERNEL: Factorial (390 cells)** | **Which kernel wins? Does correlation matter?** | **✅ COMPLETE.** DiagonalKernel +13.2pp SOC, +6.8pp S2P. Off-diagonal adds <1pp. Noise ratio is the whole story (r=0.990). |
| **V-HC-CONFIG-DIAGONAL: Healthcare (4 personas)** | **DiagonalKernel at σ≈0.22?** | **✅ COMPLETE.** +3.7pp learning. L2: +0.3pp. Mask: -6pp Day 1. 4 personas, corr(ratio, advantage)=0.990. |
| **KernelSelector validation** | **Phase 2 rule + rolling selector correct?** | **✅ COMPLETE.** ratio>1.5→diagonal: 4/4 correct. Rolling 100-window stabilizes at 250 decisions. |
| P4-F: Subtle poisoning (Condition F) | Gate 5 validation | Run before v6.0 |
| P4-COMPLACENCY: Conservation early warning | Conservation law story | Run before v6.0 |
| TD-034: τ on synthetic alert streams | Blocks going live | **RUN BEFORE v6.0** — LLM-judge streams |
| PROD-5: Convergence calendar | L-08 feature | **RUN BEFORE v6.0** — on synthetic streams |
| Tier E: convergence.py, onboarding calendar | L-08 numbers | **RUN BEFORE v6.0** — on synthetic streams |
| **V-SIM: Full pipeline on synthetic data** | **P28 end-to-end on LLM-judge generated alert streams. 3 industries × 3 judges = 9 streams.** | **RUN BEFORE v6.0** (9 streams) |

**v6.0 Gate:**

```
v5.5 hosted 30+ days.
Customer DPA signed.
TD-034 passed on synthetic alert streams (3 industries × 3 judges agree on τ).
Per-factor σ measured. Noise ratio computed. KernelSelector Phase 2: ratio>1.5 → diagonal.
Deployment gate under selected kernel:
  DiagonalKernel: GREEN σ≤0.157 / AMBER σ≤0.25 / RED σ>0.25.
  L2 (cold start): GREEN σ≤0.105 / AMBER σ≤0.157 / RED σ>0.157.
  Three-variable logic (V, q̄) still applies within each band.
Shadow mode: 250 verified decisions minimum (KernelSelector stabilization).
  Both L2 and Diagonal scored on every alert. Rolling 100-window tracks agreement.
  KernelSelector locks recommendation at 250 decisions.
ConservationMonitor: AMBER auto-pause active. Var(q) logged.
V-MV-KERNEL factorial: ✅ COMPLETE (390 cells). DiagonalKernel validated.
R score computed as DIAGNOSTIC alongside gate.
All validation is pre-ship. First customer shadow mode CONFIRMS predictions, not discovers bugs.
```

---
