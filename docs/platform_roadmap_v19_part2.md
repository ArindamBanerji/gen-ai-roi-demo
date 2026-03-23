
### v6.5 — Cause-Aware Conservation + Gain Scheduling + Epistemic State + Per-Analyst η Safety + NHI + Fisher Calendar + SC Plugin + S2P Demo. [Planned]

**Cause-aware conservation response (from 2D persona sweep):**

| ID | Capability | Implementation | Validation Required |
|---|---|---|---|
| D1 | Cause-aware response | q-drop → freeze category. α-drop → pause auto-approve. V-drop → informational + extend window. | V-D2 experiment (does freeze outperform ride-through?) |
| D2 | Automatic category freeze | scorer.freeze_category(cat). Temporary η=0 for affected category. Auto-release on GREEN. NOT permanent confirm-only. | **V-D2: 4 personas.** If freeze doesn't beat η=0.01 ride-through → don't ship D2. |
| D3 | Per-category conservation signal | Per-category α_cat·q_cat·V_cat. Spike detection. | **V-D3: 5 personas.** False positive rate at natural variance. Threshold may need baseline+3σ, not 1.5×. |
| D7 | Spike update cap | Cap centroid updates/day for spiking category. Prevents volume × noise accumulation. | **V-D7: 3 personas.** Sweep cap {1.1×, 1.2×, 1.5×, 2.0×} + legitimate increase (must NOT cap). |

**Level 2 enhancements (from 1B persona sweep):**

| ID | Capability | Implementation | Validation Required |
|---|---|---|---|
| D4 | Before/after Level 2 for teams 3-7 | Sequential 250-decision comparison. DomainConfig.team_size determines A/B vs before/after. | **V-D4: 6 personas.** Power at team 3, 5, 7. Can it detect 15pp? False promotion rate? |

**Per-analyst and shift-aware learning (from 1B + 1C):**

| ID | Capability | Implementation | Validation Required |
|---|---|---|---|
| D5 | Per-analyst η weighting | **Superseded by Adjustment B below** (adds ECE interlock, q̄ floor, min-20 observations). See Per-analyst η safety architecture. | **V-D5: 3 personas.** Does per-analyst beat global η=0.01? |
| D6 | Night shift attenuation | Reduce η_override for shifts where quality <0.65. OR operational recommendation in L-04. Design choice pending V-NIGHT. | **V-NIGHT: 4 personas.** Is 18pp gap consistent across compositions? Senior on night shift? |

**Calibration enhancements (from 1D + 2G + three-judge adjustments):**

| ID | Capability | Implementation | Validation Required |
|---|---|---|---|
| D8 | σ-gated gain scheduling | GainScheduler checks σ before τ tightening. If σ increased → τ widens. | V-D8: simulate σ change mid-deployment. |
| D9 | σ re-measurement on source change | Auto re-compute σ_mean when new SourceConnector registers. Reclassify GREEN/AMBER/RED **under selected kernel's thresholds** (DiagonalKernel: GREEN≤0.157; L2: GREEN≤0.105). May trigger KernelSelector re-evaluation if noise ratio changes. | Integration test on synthetic pipeline (LLM-judge simulated source connection). |
| **A** | **~~Noise-weighted L2 kernel~~ → SHIPPED AT v6.0 as DiagonalKernel.** V-MV-KERNEL factorial (390 cells) validated: +13.2pp SOC, +6.8pp S2P. This IS DiagonalKernel (1/σ²). No longer a v6.5 item. | **V-MV-KERNEL ✅ COMPLETE (390 cells).** Replaces V-KERNEL-W. |
| **G** | **Epistemic state indicator** | **Per-decision metadata: {scoring_mode, kernel_type, factors_active, centroid_age, learning_state, confidence_provenance, noise_ratio}. EU AI Act compliance mechanism + integrity feature. ~50 lines. Opus contribution.** | Design review only. No experiment needed. |

**Per-analyst η safety architecture (from Adjustment B + D — three-judge consensus):**

| ID | Capability | Implementation | Validation Required |
|---|---|---|---|
| B | Agreement-rate → per-analyst η | Wire v6.0 observation data to η_effective = η_override × min(1.0, agreement_rate / 0.80). **Safety gates (hard-coded, non-negotiable):** ECE interlock (disable if ECE>0.10), q̄ floor at 0.60, min 20 observations per analyst. | **V-AGREEMENT-Q: Does agreement-rate predict actual q̄? Correlation ≥0.6 to ship.** |
| D-cap | η change-rate cap | All calibration parameters (τ, W, η_override, team_mode) capped at ±0.005 per 70-decision cadence. Prevents B→D feedback loop: η changes → different learning → different q̄ estimate → different η. Opus contribution. | **V-STABILITY: Run D5 personas with and without cap. Converges or oscillates?** |

**Existing v6.5 items (from v16, updated):**

| Capability | Details |
|---|---|
| GainScheduler + conservation gating | Periodic τ recalibration (~70 decisions/category). Conservation law gates every change. **Now σ-aware (D8).** UI: "Cloud τ: 0.10→0.07, gate PASSED." |
| Fisher onboarding calendar (dynamic) | Replaces static L-08. Per-category bars update as sources connect. **Now σ-aware.** Source impact: "Connect Entra ID → 11% faster." **GATE:** r²>0.5 across ≥4 categories (META-5). |
| S2P 10-scenario demo | S2PDomainConfig (d=8, updated from d=6). 10 procurement scenarios. L2 vs DiagonalKernel comparison. Same engine, different domain. Platform proof. |
| Conservation enforcement mode | Shadow → enforcement. **Now cause-aware (D1).** Gates auto-approve expansion. |
| Gate 5 enforcement mode | Calibrated δ_presentation from v6.0 observation. Active enforcement. |
| Outcome verification provider | 10% re-verification. Async. Majority voting. **Now feeds D5 per-analyst quality.** |
| Value-based variant evaluation | AgentEvolver uses value_per_decision, not accuracy_alone. |
| Security Copilot plugin (SC-PLG) | 5 capabilities in SC NL interface. Customer-deployed. Delegated OAuth. Cache <500ms. |
| Flash Tier | Streaming ingestion (Kafka/Kinesis). Pre-filter that compounds. |
| NHI behavioral baselines (F7) | Same ProfileScorer, new entity type. 82:1 machine:human identity ratio. 73% of CISOs investing in identity discovery/inventory. |
| Fuzzy entity resolution (INOVA) | Probabilistic matching. |
| Third SIEM connector | CrowdStrike Falcon LogScale or Elastic Security. ~80% TAM. |
| SPRT (optional) | Sequential testing for Level 2. Promotes clear winners 2-3× faster. Implement if K=2 starvation persists. |

**v6.5 Experiments:**

| Experiment | What It Gates | Personas |
|---|---|---|
| **V-D2: Category freeze vs ride-through** | **D2 ships or not** | 4 |
| **V-D3: Per-category spike FP rate** | **D3 threshold calibration** | 5 |
| **V-D4: Before/after Level 2 power** | **D4 ships or not** | 6 |
| **V-D5: Per-analyst η vs global** | **D5 ships or not** | 3 |
| **V-D7: Spike cap threshold sweep** | **D7 cap value** | 3 |
| **V-NIGHT: Night shift across compositions** | **D6 design choice** | 4 |
| **V-AGREEMENT-Q: Agreement-rate predicts q̄?** | **Adjustment B ships or not. r≥0.6 required.** | 3 |
| **V-STABILITY: η cap prevents oscillation?** | **D-cap ships or not. Convergence vs oscillation.** | 3 (reuse V-D5) |
| META-4: Transfer prior (200 seeds) | v7.0 transfer priors go/no-go. THE decisive experiment. | — |
| META-5: Fisher → N_half validation | Dynamic calendar accuracy. Partially answered by Bridge B v3. | — |
| EXP-ENRICH-1: Entity resolution → convergence | Quantifies entity resolution impact. | — |
| τ gain scheduling study (50 seeds) | Validates gain scheduling > fixed τ. | — |

**v6.5 Gate:** Any D-item whose validation experiment FAILS does NOT ship. It gets redesigned or deferred to v7.0. The experiments are the gates, not the designs.

---

### v7.0 — Multi-Tenant + Transfer Priors + S2P Full + Cross-Tenant Intel. [Roadmap]

| Capability | Details | Gate |
|---|---|---|
| Multi-tenant (I-06) | PostgreSQL row-level security. Per-tenant graph isolation. Required for SaaS + MSSP. | Second customer signed |
| Transfer priors | TransferPriorManager + meta-conservation. compute_transfer_prior(), check_meta_conservation(). New categories start from firm-specific prior. | **HARD GATE:** META-4 ≥15% N_half improvement at p<0.05. If fails: S2P ships without. |
| Cross-tenant meta-intelligence (P-02) | "Waze effect." Anonymized threat pattern sharing. Cold-start acceleration. | Multi-tenant operational |
| S2P Copilot full (P-01) | penalty_ratio=5.0, θ_min=0.35. D&B/OFAC connectors. THE platform proof. | S2P-V3B passed |
| GraphAttentionBridge (P-03) | gae/bridge.py. | EXP-G1 passed |
| A2A/MCP protocol (I-07) | Agent-to-agent + Model Context Protocol interop. | — |
| L-10 full compliance dashboard | Five interactive panels. Live status, drill-down, export. | — |
| OPD-style variant guidance | LLM judge extracts structured hints from override comments (captured at v6.0). Informs AgentEvolver variant design. | Override comments at ≥30% populate rate during v6.0-v6.5. |
| Correlated error detection (R1) | Cross-analyst agreement metric. When >80% override same category same way in 7-day window → campaign flag. | 2D data + per-analyst tracking from v6.5 |
| Fatigue dynamics model (R2) | q(t_shift) = q_base × (1 - fatigue_factor × hours/8). Per-analyst, per-shift. Designed from synthetic trajectories (Phase 3 2E sweep); calibrated from deployment data when available. | Synthetic trajectory validation in Phase 3 |
| Category geometry analysis (R3) | Inter-centroid L2 distances per category. Per-category σ_max. Identifies "thin boundary" categories. | 1D data + centroid tensor analysis |
| **Adj. C: CGA as second compounding pathway** | **Graph enrichment compounds regardless of σ/q̄ (graph-structural, not centroid-dependent). "Your graph compounds while centroids wait." Positioning asset for high-noise/low-quality deployments (bottom-right quadrant). Three-judge consensus: narrative asset now, technical claim at v7.0 only.** | **V-CGA-FROZEN: Does graph enrichment lift frozen scorer accuracy? Must demonstrate before claiming.** |
| GAE v1.0.0 | Stable API. Full documentation. | — |
| **ShrinkageKernel research** | **Off-diagonal correlations added <1pp in V-MV-KERNEL factorial. Deprioritized from v6.5. May matter at ρ>0.8 (untested). CovarianceEstimator (collecting since v6.0) provides real Σ̂ data for investigation.** | **V-MV-REGIME + high-ρ domain discovery** |

**v7.0 Gate:** Second customer signed. Graph isolation verified. META-4 determines transfer prior scope.

---

### v7.5 — Partner Network (MSSP) + Hosted Demo. [Vision]

| Capability | Details |
|---|---|
| MSSP channel | Partner portal. 10× revenue multiplier. |
| Additional SIEMs | QRadar, LogRhythm. TAM expansion. |
| Hosted demo (demo.dakshineshwari.net) | Always-on. Synthetic data. Time-travel snapshots. Speed-run. |
| Cross-domain compounding (SOC × S2P) | b=2.11: second domain more than doubles discovery. |

---

### v8.0 — Level 3: Self-Knowledge + Cross-Domain Discovery. [Vision]

| Capability | Details |
|---|---|
| DiscoveryEngine | System extends its own evaluation criteria. Multi-domain discovery. |
| Cross-domain enrichment | SOC threat intel → S2P vendor risk. |
| Self-model tensor Ψ[c] | Accuracy vs predicted. Confusion boundaries. Per-analyst quality. |
| 60-70% auto-approve target | Centroids mature + cross-domain corroboration. |

**Formalism pending.** Level 3 deserves the same rigor as Levels 1 and 2.

---

## Microsoft Integration Strategy — Complement, Not Compete

**Positioning:** "We make your Microsoft investment compound."

| Mechanism | Version | What It Does |
|---|---|---|
| Sentinel bidirectional connector (S-01) | v6.0 | Ingest alerts + write-back dispositions. |
| Sentinel enrichment write-back (S-01-WB) | v6.0 | Campaign, IKS, confidence → Sentinel incidents. |
| Security Copilot plugin (SC-PLG) | v6.5 | 5 capabilities in SC NL interface. Customer-deployed. |

**The killer line:** "After 1,000 decisions, your Security Copilot answers differently — because ours gave it institutional memory."

---

## EU AI Act Compliance — Live UX Surface (Enforcement: August 2, 2026)

| Article | Mechanism | Version |
|---|---|---|
| Art. 9: Risk Management | Conservation law (two thresholds, cause-aware at v6.5) + 38+ experiments + persona sweeps | v6.0 / v6.5 |
| Art. 12: Logging | Evidence Ledger: hash-chained, tamper-evident | v5.5 ✅ / v6.0 |
| Art. 13: Transparency | 144 readable centroids (SOC, A=4) + factor provenance | v5.5 ✅ / v6.0 |
| Art. 14: Human Oversight | Three-tier dispatch. Conservation law guarantees oversight. σ gate prevents unsafe learning. | v6.0 |
| Art. 15: Robustness | ECE=0.036. Poisoning 0.15pp. Three-layer L2 defense. η_override=0.01. DiagonalKernel down-weights noisy factors. KernelSelector adapts to deployment. Deployment gate kernel-aware. | v6.0 / v7.0 |

---

## Claims Registry Updates (from Persona Sweeps + V-MV-KERNEL Factorial)

| ID | Claim | Evidence | Qualifier |
|---|---|---|---|
| CL-38 (updated) | Convergence 100-200 decisions | 1C + 1D + 2D | "At q̄≥0.70 AND σ≤0.157 (L2) or σ≤0.25 (DiagonalKernel). Below q̄=0.70: ~2× timeline. Above kernel-specific RED threshold: frozen only. 14-day incident adds ~20 days." |
| CL-DETECT (new) | Conservation detects campaigns in 5 days | 2D-CE1 | "Relative threshold 0.7× baseline. AMBER at Day 24-25 (ratio 0.684). **Needs V-CAMPAIGN-INTENSITY for lower correlation rates.**" |
| CL-RECOVER (new) | Post-campaign recovery <1 day at all tested volumes | 2D + V-CL-RECOVER | "V=50: 15 decisions/1.0 day. V=100: 32.5/0.93 day. V=200: 57.8/1.2 days. Asymmetric η attenuates drift during campaigns. 3-day claim is conservative." |
| CL-LIFT (new) | Learning lift +2.5 to +3.5pp at q̄≥0.70 | 1C | "No degradation at any quality with η=0.01. +0.5pp at q̄=0.57." |
| CL-FLOOR (new) | V≥30 viable, all 6 categories by Day 45 | 1A | "At q̄=0.75, σ≈0.10. **Needs V-TRIPLE-STRESS for low-quality + moderate-noise.**" |
| CL-CEILING (REVISED v19) | Noise ceiling is kernel-dependent. DiagonalKernel: GREEN≤0.157, AMBER≤0.25, RED>0.25. L2: GREEN≤0.105, AMBER≤0.157, RED>0.157. | V-MV-KERNEL (390 cells) | "GREEN zone nearly doubles under DiagonalKernel. Healthcare (σ≈0.22) moves from L2-RED to Diagonal-AMBER." |
| CL-QUARANTINE (**DEPRECATED**) | Factor quarantine mask WORSE than L2 alone. -6pp Day 1 from zeroing factors. DiagonalKernel supersedes. | V-HC-CONFIG-DIAGONAL | "Binary mask produced -6pp Day 1 damage; DiagonalKernel produced +3.7pp learning at same σ. Mask DEPRECATED, REMOVED at v7.0." |
| **CL-KERNEL-DIAG (new — UNCONDITIONAL)** | DiagonalKernel +13.2pp over L2 on heterogeneous SOC data | V-MV-KERNEL (144 hetero cells) | "390-cell factorial. Advantage scales linearly with noise ratio (r=0.990, 4 HC personas)." |
| **CL-KERNEL-HC (new — UNCONDITIONAL)** | Healthcare learning from Day 1 under DiagonalKernel at σ≈0.22 | 4 HC personas | "+2.2pp to +14.3pp depending on noise ratio. L2 degrades at ratio>1.9×; Diagonal improves." |
| **CL-KERNEL-SELECT (new — UNCONDITIONAL)** | KernelSelector (ratio>1.5→diagonal) correct 4/4 | Selector validation | "Rolling 100-window. Stabilizes at ~250 decisions. Simplified rule: one parameter, no ρ_max." |
| **CL-SHRINKAGE-NULL (new — UNCONDITIONAL)** | Off-diagonal correlations add <1pp to scoring accuracy | V-HC-CONFIG-SHRINKAGE + V-S2P-HETERO | "Diagonal of Σ⁻¹ ≈ 1/σ² once marginalized. Noise ratio is the whole story." |
| **CL-KERNEL-MASK (new — UNCONDITIONAL)** | Binary factor mask WORSE than L2 alone (-6pp Day 1) | V-HC-CONFIG head-to-head | "Zeroing factors distorts cold-start geometry. Continuous weighting (DiagonalKernel) preserves weak signal." |
| CL-ENRICH (new) | +7 to +13pp from enrichment. No dip. | 2G | "**Needs V-ENRICHMENT-NEGATIVE for negative case.**" |
| CL-L2-TEAM (new) | A/B requires ≥8 analysts | 1B | Validated. |
| CL-TAU (new) | τ is noise-dependent. TD-034 mandatory. | 1D | "τ=0.05 for σ<0.12, τ=0.08-0.12 for σ=0.12-0.20, τ=0.15 for σ>0.20." |
| CL-NIGHT (new) | Night shift 18pp quality gap | 1B-T5 | "Single team composition. **Needs V-NIGHT for cross-validation.**" |

**Claims that need qualification before blog/deck publish:**
- "N_half ≈ 14" → add "at q̄≥0.70 and σ≤0.157 (L2) or σ≤0.25 (Diagonal)"
- "The system gets smarter" → add "under DiagonalKernel; at σ≤0.25"
- "Conservation law prevents degradation" → add "detects in 5 days; auto-freeze at v6.5, manual at v6.0"

**New forbidden claims (from V-MV-KERNEL):**
- "Mahalanobis is always better than L2" — diagonal is better when ratio>1.5; L2 equivalent when ratio<1.5.
- "Full covariance matrix improves scoring" — off-diagonal adds <1pp.
- "Factor quarantine mask is effective" — mask was WORSE than no mask (-6pp Day 1).
- "Shrinkage kernel needed for S2P" — diagonal captures full advantage.

**Claims registry document:** v5 complete (52 claims). v6 delta document adds 6 kernel claims + 3 promotions + 4 forbidden claims + CL-CEILING/CL-QUARANTINE revisions + innovation mapping. See claims_registry_v6.md.

**FUTURE claim (pre-staged from innovation mapping §6):**
- **CL-ECON-MEASURED (Decision Economics):** "Measured time savings per decision from first deployment." Currently uses input assumptions (44 min/alert, $127/alert). First deployment produces actual measurement. Innovation 10 has no validated claim until this is measured.

---

## Experiment Pipeline (All Priorities)

**Priority 1 — Before v6.0 ships (ALL COMPLETE):**

| ID | What It Validates | Personas | Status |
|---|---|---|---|
| V-B3 | Three-variable noise ceiling (σ, V, q̄) | 4 | ✅ NUANCED — three-variable gate discovered |
| V-B1 | η=0.01 at AMBER noise (σ=0.12-0.157) | 3 | ✅ PASS — holds across full AMBER range |
| V-CL-RECOVER | Recovery at V=50, V=100, V=200 | 2 | ✅ PASS — <1 day at all volumes, claim conservative |
| V-HC-CONFIG | Healthcare factor quarantine (binary mask) | 1 | ✅ **SUPERSEDED by V-MV-KERNEL.** Mask was WORSE than L2 (-6pp Day 1). |
| **V-MV-KERNEL** | **Kernel factorial (L2 vs Diagonal vs Shrinkage)** | **390** | **✅ COMPLETE.** DiagonalKernel +13.2pp SOC, +6.8pp S2P. Off-diagonal <1pp. |
| **V-HC-CONFIG-DIAGONAL** | **DiagonalKernel at σ≈0.22 (4 HC personas)** | **4** | **✅ COMPLETE.** +3.7pp learning. corr(ratio, advantage)=0.990. |
| **KernelSelector validation** | **Phase 2 rule + rolling selector** | **4** | **✅ COMPLETE.** ratio>1.5→diagonal: 4/4 correct. 250 decisions. |

**Priority 2 — Before v6.5 ships (31 personas + 3 analysis-only):**

| ID | What It Validates | Personas | Gates |
|---|---|---|---|
| V-D2 | Category freeze vs ride-through | 4 | D2 ships or not |
| V-D3 | Per-category spike FP rate | 5 | D3 threshold |
| V-D4 | Before/after Level 2 power | 6 | D4 ships or not |
| V-D5 | Per-analyst η vs global | 3 | D5 ships or not |
| V-D7 | Spike cap sweep | 3 | D7 cap value |
| V-NIGHT | Night shift across compositions | 4 | D6 design |
| **V-AGREEMENT-Q** | **Agreement-rate predicts actual q̄ (r≥0.6)** | **3** | **Adjustment B ships or not** |
| **V-STABILITY** | **η cap prevents calibration oscillation** | **3 (reuse V-D5)** | **D-cap ships or not** |
| **V-MV-RISK** | **R score vs three-variable gate (analysis on existing factorial data)** | **0 (analysis only)** | **R replaces gate at v6.5 or not** |
| **V-MV-CONVERGENCE** | **N_half = f(σ, V, q̄, kernel) fitted from factorial data** | **0 (analysis only)** | **L-08 calendar update** |
| **V-MV-CONSERVATION** | **Var(q) false alarm rate on factorial trajectories** | **0 (analysis only)** | **Var(q) becomes gating condition at v6.5 or not** |
| **V-CGA-FROZEN** | **Does graph enrichment lift frozen scorer accuracy? The WIDEST innovation-claim gap (§6 claims v6). If fails: Adj. C "second compounding pathway" narrative collapses.** | **TBD** | **HIGH — Adj. C claim + bottom-right quadrant sales narrative** |

**Priority 3 — Pre-ship synthetic validation (replaces "during pilot" — no customer dependency):**

| ID | What It Validates |
|---|---|
| V-SIM | Full P28 pipeline on LLM-judge synthetic alert streams (3 industries × 3 judges = 9 streams) |
| V-TRIPLE-STRESS | V=30 + q̄=0.60 + σ=0.15 on synthetic stream (micro-SOC worst case) |
| V-CAMPAIGN-INTENSITY | Conservation detection at 40%/60% correlation on synthetic campaign streams |
| V-INCIDENT-TYPES | Convergence delay across synthetic incident types (APT, insider, compliance audit) |
| V-ENRICHMENT-NEGATIVE | Synthetic source that adds noise (not reduces it) — can enrichment hurt? |
| **V-UCL-VALUE** | **Does graph entity count × relationship count predict IKS/deployment value? Analysis on existing persona sweep data. No new harness run. UCL innovation-claim gap (§6 claims v6).** |

**Priority 4 — Phase 2 sweeps + v7.0 research (v6.5-v7.0 development):**

2E fatigue dynamics, 2F analyst turnover, Level 3 cross-dimension interactions (V×q, skew×noise, team×shift), Level 4 industry edge cases (healthcare, finserv, tech, gov, critical infrastructure).

**v7.0 kernel research (deprioritized — off-diagonal adds <1pp in all current tests):**

| ID | What It Tests | Cells | Priority |
|---|---|---|---|
| V-MV-REGIME | Covariance estimator tracks regime shift (Regime A→B at decision 500) | 18 | LOW |
| V-MV-INCOMPLETE | Factor omission robustness (Financial Risk removed) | 36 | LOW |
| V-MV-HIGH-RHO | ShrinkageKernel at ρ>0.8 (extreme correlation — untested) | TBD | LOW |

---

## Critical Path Dependency Graph

```
v5.5 (SHIPPED)
├── Hook 1/2/3, ProfileScorer, DomainConfig ← ALL SHIPPED
└── Phase 1 persona sweeps ← ✅ COMPLETE (24 personas)

v6.0 (NEXT)
├── Procurement gates: SAML, PII, cloud, Multi-SIEM, entity resolution
├── Pilot success: attack chains, benchmarking, Tab 5, L-08, L-09
├── P0 fix: asymmetric η (✅ DONE, 478 tests)
├── **DiagonalKernel (1/σ²) — v6.0 DEFAULT** ← V-MV-KERNEL ✅ COMPLETE (390 cells)
├── **KernelSelector** (ratio>1.5→diagonal, rolling 100-window, 250 decisions)
├── **CovarianceEstimator** (COLLECTS data, does NOT score — research asset for v7.0)
├── P28 redesign: PREVIEW → Import → Compute (TD-034 + σ + ratio + kernel) → Shadow (250 dec min, multi-kernel) → Qualify → Enable
├── Deployment gate UPDATED for DiagonalKernel (GREEN≤0.157, AMBER≤0.25, RED>0.25)
├── Factor quarantine mask **DEPRECATED** (mask was WORSE than L2: -6pp Day 1)
├── AMBER auto-pause (~20 lines, LEARNING_ENABLED=False on AMBER)
├── Frozen Mode ROI calculator (RED zone: σ>0.25 under Diagonal)
├── Agreement-rate quality observation (log only, feeds v6.5 Adjustment B)
├── Var(q) per-analyst observation (log only, feeds v6.5 conservation extension)
├── Residual tracking (~30 lines, log only, feeds v7.0 factor extensibility)
├── gae/calibration.py + fisher.py + kernels.py + kernel_selector.py + covariance.py (ships PyPI)
├── ConservationMonitor (shadow, per-shift, min-50, AMBER auto-pause, Var(q) logged)
├── Decision value tagger
├── K=2 + Gate 5 (observation)
├── Override comment + async verification interface
├── Entity resolution dashboard + σ prediction
├── GTM: DPA template, Loom update, security posture, VSQ
├── V-MV-KERNEL ✅ + V-HC-CONFIG-DIAGONAL ✅ + KernelSelector ✅ (all Priority 1 COMPLETE)
├── V-SIM: full pipeline on synthetic streams ← MUST PASS
└── First customer shadow CONFIRMS predictions, not discovers bugs

v6.5
├── D1-D3: Cause-aware conservation ← GATED by V-D2, V-D3
├── D4: Before/after Level 2 ← GATED by V-D4
├── D5-D6: Per-analyst + shift-aware η ← GATED by V-D5, V-NIGHT
├── D7: Spike cap ← GATED by V-D7
├── D8-D9: σ-gated gain scheduling + re-measurement (kernel-aware)
├── **Adj. A: SHIPPED AT v6.0** (DiagonalKernel IS Adjustment A)
├── **Adj. B: Agreement-rate → per-analyst η** ← GATED by V-AGREEMENT-Q (r≥0.6)
├── **Adj. D-cap: η change-rate cap ±0.005/cadence** ← GATED by V-STABILITY
├── **Adj. G: Epistemic state indicator** (+ kernel_type, noise_ratio metadata)
├── **R score replaces deployment gate** ← GATED by V-MV-RISK
├── **Var(q) as gating condition** ← GATED by V-MV-CONSERVATION
├── **N_half multivariate model in L-08** ← GATED by V-MV-CONVERGENCE
├── GainScheduler, Fisher calendar, enforcement mode
├── SC plugin, NHI, INOVA, Flash Tier, 3rd SIEM
├── S2P 10-scenario demo (d=8, L2 vs Diagonal comparison)
├── SPRT (optional, if K=2 starvation persists)
├── Factor quarantine mask code REMOVED
└── Phase 2 persona sweeps (30-35 personas)

v7.0 (GATED by META-4)
├── Transfer priors ← META-4 ≥15% at p<0.05
├── S2P full ← multi-tenant
├── R1 correlated error detection, R2 fatigue, R3 geometry
├── OPD variant guidance ← override comments ≥30% populate rate
├── **ShrinkageKernel research** ← V-MV-REGIME + V-MV-HIGH-RHO (deprioritized)
└── **Factor space extensibility** ← residual tracking data from v6.0
```

---

## Design Document Index

| Short Name | Full Title | Status |
|---|---|---|
| **research_note_v3_consolidated** | Continuous Calibration + Graph Enrichment | 1,542 lines. Conservation law worked examples. API specs. |
| **innovation_note_for_blog** | The Innovations: What We Built, Why It's New | 884 lines. 11 innovations, 3 tiers, triangle. |
| **coding_session_v6_brief** | v6.0 Implementation Items | 392 lines. For kernel implementation, see multivariate_foundation_design_note_v2 §3. |
| **roadmap_recommendations** | Roadmap Change Recommendations | 401 lines. 10 recs. Source for v16 changes. |
| **calibration_example.py** | Working Code: Conservation + Calibration | 280 lines, runs end-to-end. |
| **openclaw_rl_coding_note** | OpenClaw-RL Lessons | Override comments, async verification, OPD. |
| **stryker_handala_ci_analysis** | Stryker/Handala Attack Analysis | Sales weapon. Six factors. Four Clocks. |
| **claims_registry_v5** | Claims Registry v5 | 953 lines. 52 claims. Needs v6 update with kernel claims. |
| **design_gap_analysis_v5_claims** | Design Gap Analysis from v5 Claims | 320 lines. 8 gaps, 23 design changes. G1 (Healthcare) RESOLVED by DiagonalKernel. |
| **design_adjustments_and_judge_prompt** | Design Adjustments A-G + Three-Judge Prompt | 465 lines. Adj. A SHIPPED at v6.0 as DiagonalKernel. |
| **multivariate_foundation_design_note_v2** | Multivariate Foundation: Scoring, Learning, Governance | 542 lines. 390-cell factorial. DiagonalKernel +13.2pp. KernelSelector. S2P d=8. Correlation research. Replaces v1/v1.3. |
| **s2p_correlation_research_prompt** | LLM Prompt: S2P Cross-Domain Correlation Analysis | Self-contained prompt. Two-judge validated (GPT-4o + Opus). 28 pairs, 3 regimes, 8×8 Σ matrix. |
| **factorial_soc_streams.json** | V-MV-KERNEL SOC Factorial Personas | 108 personas. 3 kernels × 3 σ × 2 q̄ × 2 V × 3 ρ. |
| **factorial_s2p_streams.json** | V-MV-KERNEL S2P Factorial Personas | 108 personas. Same factorial. d=8 domain-level scores. Two-judge Σ matrix. |
| **factorial_s2p_regime_shift.json** | V-MV-REGIME S2P Personas | 18 personas. Regime A→B at decision 500. |
| **factorial_s2p_incomplete.json** | V-MV-INCOMPLETE S2P Personas | 36 personas. Financial Risk omitted. |
| **s2p_copilot_design_v0.3** | S2P Copilot Design | Updated: d=6→8 (domain-level scores). penalty_ratio=5.0. |
| **architecture_philosophy_v1_3** | Architecture Philosophy | Five layers, bridge, compiled ontologies. Needs v2 update with kernels.py. |
| **consolidated_capability_plan_v3.1** | Capability & Research Plan | v6.0/v7.0+ planning reference. |
| **coding_session_briefing** | Briefing: Calibration + Graph Enrichment | Bridge B v3 implications for P4/P5. |
| **persona_sweep_JSONs (×6)** | Phase 1 Validation Datasets | 24 personas across 6 sweeps. |

---

*Dakshineshwari LLC · Platform Roadmap v19 Part 2 · March 21, 2026 · Confidential*

*V-MV-KERNEL factorial complete (390 cells). DiagonalKernel is v6.0 default (+13.2pp SOC, +6.8pp S2P).*
*Noise ratio is the whole story (r=0.990). Off-diagonal adds <1pp. Shrinkage → v7.0 research.*
*Factor mask DEPRECATED (-6pp Day 1). Healthcare: learning from Day 1. GREEN zone doubles.*
*KernelSelector: ratio>1.5→diagonal, rolling 100-window, 250 decisions. 4/4 correct.*
*Every adjustment gated by its own validation experiment. If experiment fails, adjustment doesn't ship.*
*Same model. Same code. Smarter graph. Smarter kernel.*
*"The moat isn't the model. The moat is the three loops feeding one living graph — and the graph develops judgment."*
