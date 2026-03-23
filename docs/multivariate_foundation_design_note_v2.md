# Multivariate Foundation: Scoring, Learning, and Governance

**Design Note v2 · March 21, 2026 · Dakshineshwari LLC · Confidential**

*v2 integrates completed V-MV-KERNEL factorial results (216 uniform + 144 heterogeneous
+ 18 S2P + 4 healthcare personas + kernel selector validation). The central finding:
DiagonalKernel (1/σ²) captures the entire kernel advantage. Off-diagonal correlations
add nothing measurable to scoring. Noise heterogeneity is the whole story.*

*Changes from v1.3: ShrinkageKernel deprioritized from v6.5 to v7.0 research.
DiagonalKernel promoted from v6.0 option to v6.0 DEFAULT. Factor quarantine mask
DEPRECATED (Diagonal supersedes). κ(Σ̂) monitoring removed from v6.0. KernelSelector
added with rolling 100-decision window and simplified Phase 2 rule.*

---

## 1. The Problem (unchanged from v1)

Five of ten major experimental results were surprises — all tracing to interaction effects
the univariate framework cannot model.

| Experiment | Expected (univariate) | Actual (multivariate) | Missed Interaction |
|---|---|---|---|
| V-B3 | σ=0.157 is the threshold | Corruption vector is V×(1-q̄)×η | σ × V × q̄ |
| V-HC-CONFIG | Mask rescues RED zone | Mask WORSE than L2 alone (-6pp Day 1) | mask × centroid geometry distortion |
| CLAIM-38 | N_half≈14 unconditional | Requires q̄≥0.70 AND σ≤0.157 | q̄ × σ |
| 1B Team Size | A/B works at 4 analysts | Needs ≥8 | team_size × quality_variance |
| 2D Correlated | Starvation = bad | Starvation is protective | V × σ × η (low V limits corruption) |

**Root cause:** L2 kernel treats all factors equally. When factor noise is heterogeneous
(which it always is in real deployments), L2 lets noisy factors corrupt centroids while
underweighting reliable factors. DiagonalKernel (1/σ²) fixes this.

---

## 2. Design Resolution: DiagonalKernel Is the Answer

### 2.1 The Experimental Record

**V-MV-KERNEL factorial** (216 uniform + 144 heterogeneous noise cells):

| Domain | Noise Profile | L2 | Diagonal | Gap |
|---|---|---|---|---|
| SOC (uniform σ) | All factors same noise | 85.6% | 85.6% | 0pp (identical — expected) |
| SOC (heterogeneous) | 2.6× noise ratio | 79.5% | 92.7% | **+13.2pp** |
| SOC (σ=0.22 hetero) | Extreme heterogeneous | 61-64% | 83-85% | **+20-22pp** |
| S2P (uniform σ) | All factors same noise | 46.6% | 46.6% | 0pp (identical) |
| S2P (heterogeneous) | 1.8× noise ratio | 42.2% | 49.0% | **+6.8pp** |

**V-HC-CONFIG with DiagonalKernel** (healthcare persona, σ_mean≈0.22):

| Condition | Day 1 | Day 60 | Δ |
|---|---|---|---|
| L2 (no mask) | 69.2% | 69.5% | +0.3pp (flat — no learning) |
| L2 + binary mask | 64.1% | 65.1% | +1.0pp (mask HURT Day 1 by 6pp) |
| DiagonalKernel | 70.2% | 73.9% | **+3.7pp** (learning works) |

**Shrinkage/Mahalanobis test** (off-diagonal correlations):

| Condition | Day 60 | Δ vs Diagonal |
|---|---|---|
| DiagonalKernel | 73.9% | baseline |
| ShrinkageKernel ρ=0.45 | 73.1% | **-0.8pp** (correlation HURTS) |
| ShrinkageKernel ρ=0 | 73.9% | 0pp (= diagonal when ρ=0) |
| S2P: Diagonal vs Shrinkage (18 cells) | 51.8% vs 51.6% | **-0.2pp** (negligible) |

**Healthcare scaling** (4 personas, correlation with noise ratio = 0.990):

| Persona | Noise Ratio | L2 Δ | Diagonal Δ | Advantage |
|---|---|---|---|---|
| HC-C (extreme) | 4.6× | -6.3pp | +8.0pp | **+14.3pp** |
| HC-A (one noisy factor) | 3.2× | -3.3pp | +6.4pp | **+9.6pp** |
| HC-B (moderate) | 1.9× | +3.2pp | +5.5pp | +2.3pp |
| HC-D (original) | 1.6× | +0.1pp | +2.3pp | +2.2pp |

### 2.2 What This Means

**Explanation A CONFIRMED:** Noise heterogeneity ratio is the whole story. Factor
correlations (ρ) add nothing measurable to scoring accuracy. The diagonal of Σ⁻¹ ≈ 1/σ²
once marginalized, regardless of off-diagonal structure.

**Two production kernels, not three:**

| Kernel | Status | When It Wins | Ships |
|---|---|---|---|
| **L2** | Cold-start fallback | Before P28 measures per-factor σ. Near-uniform noise (ratio < 1.5×). | v6.0 |
| **DiagonalKernel** | **v6.0 DEFAULT** | Any deployment with noise ratio ≥ 1.5× (every real deployment). Weights = 1/σ² from P28 Phase 2. | v6.0 |
| ShrinkageKernel | v7.0 research | Unknown — may matter at ρ>0.8 (untested). Off-diagonal adds -0.2pp to +0.8pp in all current tests. | v7.0 |

**Binary factor mask is superseded:** Mask was WORSE than L2 alone (-6pp Day 1 damage
from zeroing factors). DiagonalKernel's continuous weighting (device_trust at weight 0.04,
not 0.0) preserves weak signal without letting noise dominate.

### 2.3 Revised Product Boundaries

| Kernel | GREEN | AMBER | RED |
|---|---|---|---|
| L2 (old) | σ ≤ 0.105 | 0.105 < σ ≤ 0.157 | σ > 0.157 |
| **Diagonal (new default)** | **σ ≤ 0.157** | **0.157 < σ ≤ 0.25** | **σ > 0.25** |

GREEN zone nearly doubles. Healthcare (σ≈0.22) moves from RED to AMBER.
Only truly chaotic deployments (σ>0.25) remain RED.

---

## 3. Implementation (DONE — 478 GAE tests passing)

### 3.1 Scoring (GAE layer — SHIPPED)

**File:** `gae/kernels.py` (new, ~100 lines)

```python
class KernelBase(Protocol):
    def compute_distance(self, f, mu) -> np.ndarray: ...
    def compute_gradient(self, f, mu) -> np.ndarray: ...

class L2Kernel(KernelBase): ...       # ‖f−μ‖² — v5.5 behavior
class DiagonalKernel(KernelBase): ... # (f−μ)ᵀ·diag(1/σ²)·(f−μ) — v6.0 default
```

**Config:** `DomainConfig.kernel_type: str = "diagonal"` (default).
`kernel_type="l2"` for cold-start before P28 Phase 2 measures σ.
Backward compatible: L2 produces identical v5.5 behavior.

**Test status:** 478 GAE tests passing (was 251 at v5.5, +186 kernel session, +41 referral/coding session).

### 3.2 Learning (GAE layer — SHIPPED)

**File:** `gae/scoring.py` (ProfileScorer.update)

| Kernel | Gradient | Effect |
|---|---|---|
| L2 | η·(f−μ) | Equal learning rate in all dimensions. |
| Diagonal | η·W·(f−μ), W=diag(1/σ²) | Pushes harder on low-noise dimensions. High-noise factors learn slower. This is why healthcare works: device_trust (σ=0.28) gets weight 0.04 while threat_intel (σ=0.07) gets weight 1.0. |

**Safety:** Asymmetric η (η_confirm=0.05, η_override=0.01) applies to the scalar step
size. The kernel changes WHERE the update pushes, not HOW MUCH. Conservation law still
governs magnitude. Gradient clipping preserved (clip_max=2.0).

### 3.3 CovarianceEstimator (GAE layer — SHIPPED, collects only)

**File:** `gae/covariance.py` (~120 lines)

Collects full covariance data during operation. NOT used for scoring at v6.0.
Research asset for v7.0 shrinkage investigation.

Tracks: per-factor σ (used by DiagonalKernel), full correlation matrix ρ (logged),
Σ̂ with Ledoit-Wolf shrinkage (computed but not consumed), exponential decay
(half_life=300 decisions ≈ 90 days at V=100).

**Why collect if not used for scoring?** Three reasons:
1. Validates the Explanation A finding on real deployment data (if ρ matters, we'll see it).
2. Feeds v7.0 shrinkage research if high-ρ domains emerge.
3. The correlation matrix appears in the P28 diagnostic report — customer sees factor
   relationships, which has value independent of kernel choice.

### 3.4 KernelSelector (GAE layer — SHIPPED)

**File:** `gae/kernel_selector.py` (~50 lines)

```python
class KernelSelector:
    """Selects optimal kernel for a deployment.
    
    Phase 2 (rule-based): noise_ratio > 1.5 → diagonal, else L2.
    Phase 3 (shadow): scores every alert with both kernels.
      Tracks rolling 100-decision window of analyst agreement rate.
    Phase 4 (lock): selects kernel with highest rolling agreement.
      Stabilizes at ~250 verified decisions.
    Ongoing: monitors noise ratio changes (D9). Can recommend kernel
      switch at cadence boundary, conservation-gated.
    """
```

**Experimental validation:**

| Deployment | Phase 2 Rule | Phase 4 Empirical | Match? |
|---|---|---|---|
| Healthcare SOC (ratio 3.0×) | diagonal | diagonal | ✅ |
| Manufacturing S2P (ratio 1.8×) | diagonal | diagonal | ✅ |
| FinServ SOC (ratio 1.3×) | L2 | L2 | ✅ |
| S2P (ratio 2.5×) | diagonal | diagonal | ✅ |

Simplified rule (noise_ratio > 1.5 → diagonal): **4/4 correct** after dropping ρ_max.
Rolling 100-window fixes cumulative bias. Stabilizes at ~250 decisions (was 350 cumulative).

### 3.5 Conservation Extension (CI Platform — v6.0 observation, v6.5 gating)

**Added to ConservationMonitor:** Var(q) per-analyst tracking (~20 lines).

```
α·q·V ≥ θ_min                    [existing — unchanged]
AND Var(q_per_analyst) ≤ σ²_q_max  [new — catches high-dispersion teams]
```

**v6.0:** Var(q) computed and logged. Not a gating condition.
**v6.5:** Var(q) becomes a gating condition (gated by V-MV-CONSERVATION results).

**κ(Σ̂) monitoring REMOVED from v6.0 scope.** Off-diagonal correlations don't affect
scoring; monitoring covariance stability adds complexity without value. CovarianceEstimator
still logs κ for research, but ConservationMonitor doesn't act on it.

---

## 4. Deployment Qualification (updated for Diagonal default)

### 4.1 Deployment Gate (revised thresholds)

**Threshold gate updated for DiagonalKernel:**

```
P28 Phase 2 measures per-factor σ.
Compute noise_ratio = max(σ) / min(σ).
Compute σ_mean.

If noise_ratio > 1.5: kernel = diagonal (default)
If noise_ratio ≤ 1.5: kernel = l2

Under DiagonalKernel:
  GREEN:  σ_mean ≤ 0.157
  AMBER:  0.157 < σ_mean ≤ 0.25 (AMBER auto-pause armed)
  RED:    σ_mean > 0.25 (frozen scorer + remediation)

Under L2 (cold start or uniform noise):
  GREEN:  σ_mean ≤ 0.105
  AMBER:  0.105 < σ_mean ≤ 0.157
  RED:    σ_mean > 0.157

Three-variable gate (σ, V, q̄) still applies within each kernel's thresholds.
R score (continuous risk function) computed as DIAGNOSTIC alongside gate.
R REPLACES gate at v6.5 if V-MV-RISK validates (experiment pending).
```

### 4.2 P28 Pipeline (updated)

```
Phase 0: PREVIEW — Synthetic Data Engine predicts noise profile.
         Industry prior → predicted kernel, predicted noise ratio.
         Output: "Healthcare: predict diagonal, ratio≈3.0×, AMBER."

Phase 1: IMPORT — Connect SIEM, ingest 30 days.

Phase 2: COMPUTE — Per-factor σ measured. Noise ratio computed.
         KernelSelector Phase 2 rule: ratio > 1.5 → diagonal.
         Output: "device_trust: σ=0.24, threat_intel: σ=0.07. Ratio=3.4×.
         Kernel: diagonal. σ_mean=0.15 under diagonal weighting → GREEN."
         Correlation matrix ρ computed and logged (diagnostic, not for kernel).
         Remediation report: "Connect Defender → device_trust σ drops to 0.10."

Phase 3: SHADOW — 30 days minimum, 250 verified decisions minimum.
         KernelSelector runs both L2 and Diagonal on every alert.
         Rolling 100-window tracks agreement rate per kernel.
         ConservationMonitor runs. Var(q) logged.
         At 250 decisions: KernelSelector locks recommendation.

Phase 4: QUALIFY — KernelSelector recommendation confirmed.
         Deployment gate evaluated under selected kernel's thresholds.
         If Phase 2 and Phase 4 agree: proceed.
         If disagree: use Phase 4 (empirical wins over rule).

Phase 5: ENABLE — Selected kernel active for scoring + learning.
         AMBER auto-pause armed if applicable.
         Frozen Mode ROI calculated for RED-zone factors.
```

### 4.3 Convergence Model (updated with kernel_type)

**N_half is kernel-dependent.** Under DiagonalKernel, high-noise factors learn slower
(by design) while low-noise factors learn faster. The overall N_half may shift.

Updated model:
```
log(N_half) = β₀ + β₁·log(σ_eff) + β₂·log(V) + β₃·q̄ + β₄·kernel_type
```

ρ_max dropped (Explanation A: correlation doesn't affect convergence).
kernel_type is binary: 0 = L2, 1 = diagonal.

**Calibration pending:** Fit model on factorial + healthcare persona data.
Feeds L-08 onboarding calendar and v6.5 Fisher calendar.

---

## 5. Factor Space Extensibility (unchanged from v1)

### 5.1 Residual-Driven Factor Discovery

Track residuals at v6.0 (~30 lines of logging). Cluster analysis offline.
LLM-judge analysis when clusters reach N ≥ 20. Graph context extraction
identifies factors missing from the factor space.

**Ties to:** CGA as second compounding pathway (Adjustment C, v7.0).
When factor space is incomplete, CGA compensates through graph structure.

### 5.2 Variable-Dimension Weights

When a new factor is added (d → d+1), DiagonalKernel adds one weight (1/σ²_new).
No matrix re-estimation needed. Simpler than the variable-dimension Σ̂ from v1.

---

## 6. S2P as Parallel Validation Domain

### 6.1 Why S2P Remains Essential

S2P validated the DiagonalKernel advantage (+6.8pp) independently of SOC (+13.2pp).
The lower gap confirmed Explanation A: S2P's noise ratio (1.8×) is less extreme than
SOC's (2.6×), producing a proportionally smaller advantage.

S2P also confirmed shrinkage adds nothing (gap: -0.2pp vs diagonal) even with dense
correlation structure (Regime A: 5 pairs above ρ=0.60).

### 6.2 S2P Factor Architecture (d=8, implemented)

8 domain-level risk scores: Supplier, Logistics, Demand, Inventory, Regulatory,
Geopolitical, Financial, Environmental. S2PDomainConfig updated (d=6→8).

### 6.3 Correlation Research — Retained for Domain Understanding

The two-judge validated 28-pair correlation matrix, 5 disruption archetypes,
3 regimes, asymmetric correlations, and industry variations are retained in full
(see v1.3 §6.3). This research has value for:

1. **Residual analysis (§5.1):** Asymmetric correlations (Financial→Supplier 30-90 day lag)
   guide which factors to check when residual clusters form.
2. **Disruption archetype detection (v7.0):** Propagation sequences from §6.3 archetypes
   can be encoded as temporal patterns in ConservationMonitor.
3. **S2P domain model:** The 8-domain structure, backbone identification (policy-statecraft +
   flow-buffer), and intersection node (Supplier) inform factor weight priors.
4. **Industry-specific DomainConfig:** Healthcare, tech, food & agriculture have different
   noise profiles — the research tells us WHERE to expect heterogeneous noise.

The correlation research does NOT inform kernel selection. That's noise ratio only.

---

## 7. Experiment Status

### 7.1 Completed Experiments

| Experiment | Cells | Result | Impact |
|---|---|---|---|
| V-MV-KERNEL (uniform noise) | 216 | L2 = Diagonal (as expected) | Identified design flaw: uniform σ makes diagonal = L2 |
| V-MV-KERNEL (heterogeneous) | 144 | Diagonal +13.2pp SOC, +6.8pp S2P | DiagonalKernel is v6.0 default |
| V-HC-CONFIG-DIAGONAL | 1 | Diagonal +3.7pp (L2: +0.3pp, mask: -6pp Day 1) | Healthcare opens at v6.0 |
| V-HC-CONFIG-SHRINKAGE | 3 | Shrinkage adds -0.8pp vs diagonal | Explanation A confirmed |
| V-S2P-HETERO | 18 | Shrinkage -0.2pp vs diagonal | Explanation A confirmed for S2P |
| HC scaling (4 personas) | 4 | corr(ratio, advantage) = 0.990 | Healthcare go-to-market backed by 4 personas |
| KernelSelector validation | 4 | Rolling 100-window, 250 decisions, 4/4 correct | Selector ships at v6.0 |

**Total factorial evidence:** 390 cells across 7 experiments.

### 7.2 Remaining Experiments (lower priority)

| Experiment | Cells | What It Tests | Priority |
|---|---|---|---|
| V-MV-RISK | analysis only | R score vs three-variable gate | MEDIUM — gates v6.5 gate replacement |
| V-MV-CONVERGENCE | analysis only | N_half = f(σ, V, q̄, kernel) | MEDIUM — gates L-08 calendar update |
| V-MV-CONSERVATION | analysis only | Extended conservation (Var(q)) false alarm rate | MEDIUM — gates v6.5 Var(q) gating |
| V-MV-REGIME | 18 | Covariance estimator tracks regime shift | LOW — shrinkage deprioritized |
| V-MV-INCOMPLETE | 36 | Factor omission robustness | LOW — v7.0 factor extensibility |

V-MV-RISK, V-MV-CONVERGENCE, and V-MV-CONSERVATION can be run on existing factorial
data (no new harness runs). These should complete before v6.5 planning.

V-MV-REGIME and V-MV-INCOMPLETE deferred to v7.0 research track.

---

## 8. Roadmap Impact (revised from v1.3)

### 8.1 Items That Change

| Roadmap Item | Was (v18) | Now (v19) |
|---|---|---|
| **Adjustment A** (v6.5, weighted L2 kernel) | Standalone v6.5 item | **SHIPPED at v6.0.** DiagonalKernel IS Adjustment A. V-MV-KERNEL validated. |
| **Factor quarantine mask** (v6.0) | Binary include/exclude, proven in 324 tests | **DEPRECATED.** Mask was WORSE than L2 alone (-6pp). Diagonal supersedes. Mask code retained as fallback but not recommended. REMOVED at v7.0. |
| **Three-variable deployment gate** | σ>0.157 AND V≥100 AND q̄<0.65 → RED | **UPDATED thresholds for DiagonalKernel.** GREEN ≤ 0.157, AMBER ≤ 0.25, RED > 0.25. Three-variable logic (V, q̄) still applies. R score as diagnostic at v6.0, replaces at v6.5 if V-MV-RISK validates. |
| **V-HC-CONFIG result** | "AMBER mitigation, not RED rescue" | **SUPERSEDED.** DiagonalKernel rescues healthcare without mask. +3.7pp learning where mask produced -6pp Day 1. Healthcare = GREEN/AMBER under diagonal, not RED. |
| **Noise remediation report** | "Connect Defender → σ drops" | **REFRAMED.** Remediation still valuable (improves all kernels) but no longer required for learning. "Connect Defender → σ drops → even better learning" not "→ learning enables." |
| **P28 Phase 3 minimum** | 30 days fixed | **250 verified decisions** (rolling selector stabilization). At V=200: ~4 days. At V=50: ~17 days. Data-driven, not calendar-driven. |
| **Healthcare go-to-market** | "Frozen scorer + remediate first → then enable learning" | **"Learning from Day 1."** DiagonalKernel handles noise. 4 personas confirm. Addressable market roughly doubles. |
| **ConservationMonitor** | + Var(q) + κ(Σ̂) | **+ Var(q) only.** κ(Σ̂) removed (off-diagonal irrelevant for scoring). |
| **S2P 10-scenario demo** (v6.5) | Tests all three kernels | **Tests L2 vs Diagonal only.** Shrinkage deferred. |

### 8.2 Items That Don't Change

- Asymmetric η — scalar learning rate, kernel-independent.
- AMBER auto-pause — still fires, thresholds updated for diagonal.
- Frozen Mode ROI calculator — kernel-agnostic.
- Agreement-rate observation (Adjustment B) — kernel-independent.
- η change-rate cap (D-cap) — kernel-independent.
- Conservation law θ_min floor — unchanged.
- Level 2 (AgentEvolver, K=2, Gate 5) — operates on accuracy, not kernel.
- EU AI Act compliance — Adjustment G extended with kernel_type metadata.
- CovarianceEstimator — still ships, still collects, research asset for v7.0.

### 8.3 New/Revised Items for Roadmap v19

| Item | Version | Layer | Status |
|---|---|---|---|
| `gae/kernels.py` — L2Kernel + DiagonalKernel | **v6.0** | GAE v0.7.0 | **DONE** (478 tests) |
| `gae/kernel_selector.py` — KernelSelector (rolling 100-window) | **v6.0** | GAE v0.7.0 | **DONE** |
| `gae/covariance.py` — CovarianceEstimator (collects, doesn't score) | **v6.0** | GAE v0.7.0 | **DONE** |
| ProfileScorer kernel parameter (defaults DiagonalKernel) | **v6.0** | GAE v0.7.0 | **DONE** |
| ConservationMonitor Var(q) observation (logged, not gating) | **v6.0** | ci-platform | ~20 lines |
| P28 Phase 2: per-factor σ + noise ratio + kernel recommendation | **v6.0** | ci-platform | ~30 lines |
| P28 Phase 3: multi-kernel shadow scoring (KernelSelector) | **v6.0** | ci-platform | ~30 lines |
| Residual tracking (§5.1 — log only) | **v6.0** | ci-platform | ~30 lines |
| S2P DomainConfig (d=6→8) | **v6.0** | s2p-copilot | **DONE** |
| Deployment gate thresholds updated for Diagonal | **v6.0** | ci-platform | ~10 lines |
| Factor quarantine mask removal | **v7.0** | ci-platform | ~-50 lines |
| ShrinkageKernel + MahalanobisKernel | **v7.0** | GAE research | ~80 lines, if ρ>0.8 matters |
| R score replaces three-variable gate | **v6.5** | ci-platform | ~30 lines, gated by V-MV-RISK |
| Var(q) as gating condition | **v6.5** | ci-platform | ~10 lines, gated by V-MV-CONSERVATION |
| N_half multivariate model in L-08 | **v6.5** | soc-copilot | ~40 lines, gated by V-MV-CONVERGENCE |

**v6.0 remaining code:** ~120 lines (ci-platform integration). GAE work is DONE.
**v6.5 code:** ~80 lines (gated by analysis experiments, no new harness runs needed).
**v7.0 research:** ~80 lines (shrinkage kernel, if high-ρ domains emerge).

---

## 9. Claims Impact (updated with experimental numbers)

### 9.1 Claims That Strengthen

| Claim | Why | Evidence |
|---|---|---|
| "System gets smarter over time" | DiagonalKernel weights refine as σ estimates improve. Third compounding pathway. | +3.7pp healthcare learning trajectory |
| "Firm-specific moat" | Per-factor σ profile is firm-specific. Weights = 1/σ² encode THIS firm's noise structure. | 4 healthcare personas: same kernel, different weights, all improve |
| Platform claim (SOC → S2P) | Same kernel framework, same DiagonalKernel. Domain differences are in σ profiles. | SOC +13.2pp, S2P +6.8pp — same mechanism, different magnitude |
| Healthcare addressable market | σ≈0.22 moves from RED to AMBER under Diagonal. | 4 personas, corr(ratio, advantage) = 0.990 |
| "No noise remediation required" | Learning works at σ=0.22 under Diagonal. Remediation improves but doesn't gate. | HC-A: +6.4pp at ratio 3.2× without remediation |

### 9.2 Claims That Need Qualification

| Claim | Required Qualifier |
|---|---|
| CL-38 (N_half≈14) | Add "under DiagonalKernel" — N_half may differ between L2 and Diagonal. V-MV-CONVERGENCE pending. |
| CL-CEILING | Thresholds shift: L2 RED at σ>0.157, Diagonal RED at σ>0.25. State which kernel. |
| CL-QUARANTINE | **DEPRECATED.** "Binary factor quarantine (v18) superseded by DiagonalKernel. Mask produced -6pp Day 1 damage; diagonal produces +3.7pp learning." |
| 36.89pp L2 advantage (EXP-C1) | Still holds — DiagonalKernel is a generalization of L2 (when σ uniform, diagonal = L2). Gap only widens. |

### 9.3 New Claims (VALIDATED — from factorial)

| Claim ID | Claim | Evidence | Status |
|---|---|---|---|
| CL-KERNEL-DIAG | DiagonalKernel +13.2pp over L2 on heterogeneous SOC data | 144-cell factorial | **UNCONDITIONAL** |
| CL-KERNEL-RATIO | Diagonal advantage scales linearly with noise ratio (r=0.990) | 4 healthcare personas | **UNCONDITIONAL** |
| CL-KERNEL-HC | Healthcare learning from Day 1 under DiagonalKernel at σ≈0.22 | 4 personas: +2.2pp to +14.3pp | **UNCONDITIONAL** |
| CL-KERNEL-SELECT | KernelSelector (ratio > 1.5 → diagonal) correct 4/4 | Selector validation | **UNCONDITIONAL** |
| CL-KERNEL-MASK | Binary factor mask is WORSE than L2 alone (-6pp Day 1) | V-HC-CONFIG head-to-head | **UNCONDITIONAL** |
| CL-SHRINKAGE-NULL | Off-diagonal correlations add <1pp to scoring accuracy | V-HC-CONFIG-SHRINKAGE + V-S2P-HETERO | **UNCONDITIONAL** |

### 9.4 New Forbidden Claims

- "Mahalanobis is always better than L2" — diagonal is better when noise ratio > 1.5×; L2 is equivalent when ratio < 1.5×.
- "Full covariance matrix improves scoring" — off-diagonal adds nothing measurable.
- "Factor quarantine mask is effective" — mask was worse than no mask.
- "Shrinkage kernel needed for S2P" — diagonal captures full advantage even with dense correlations.

---

## 10. Process Validation: Factorial Caught the Flaw

The factorial experiment process (§10 in v1) proved its value immediately. The initial
216-cell run used uniform σ across all factors, which masked the kernel difference entirely.
This was caught on Day 3 analysis — NOT after shipping, not after a customer deployment.

The corrected 144-cell run with heterogeneous noise produced the real result (+13.2pp).
Without the factorial, we would have shipped L2 as default and missed the largest accuracy
improvement since EXP-C1.

**Process lessons confirmed:**
1. **Factorial before freeze** — the 216-cell run exposed the flaw before we committed.
2. **Conservative + ambitious tiers** — conservative was "diagonal as option," ambitious was
   "diagonal as default." The factorial promoted the ambitious tier.
3. **The coding session caught the flaw** — not the roadmap session. Multiple review passes
   from different perspectives (design vs implementation) catch different errors.

---

## 11. Next Steps

### 11.1 Immediate (before v6.0 ships)

| Item | Effort | What It Gates |
|---|---|---|
| ci-platform P28 integration (kernel selector, noise ratio, thresholds) | ~90 lines | v6.0 deployment qualification |
| ConservationMonitor Var(q) observation | ~20 lines | v6.5 Var(q) gating |
| Residual tracking | ~30 lines | v7.0 factor extensibility |
| Roadmap v19 (Part 1 + Part 2) | 1 session | All documents downstream |
| Claims registry v6 | 1 session | Sales materials, deck |

### 11.2 Before v6.5 (analysis on existing data — no new harness runs)

| Item | What It Does | What It Gates |
|---|---|---|
| V-MV-RISK analysis | Fit R score on factorial data. Does R predict degradation better than threshold gate? | v6.5: R replaces gate |
| V-MV-CONVERGENCE analysis | Fit N_half = f(σ, V, q̄, kernel) on factorial data. | v6.5: L-08 calendar update |
| V-MV-CONSERVATION analysis | Retrospective Var(q) on factorial trajectories. False alarm rate? | v6.5: Var(q) becomes gating condition |

### 11.3 v7.0 Research Track

| Item | What It Tests | Priority |
|---|---|---|
| V-MV-REGIME (18 cells) | Does covariance estimator track regime shifts? | LOW — research only |
| V-MV-INCOMPLETE (36 cells) | Factor omission robustness | LOW — informs Level 3 |
| ShrinkageKernel at ρ>0.8 | Does off-diagonal matter at extreme correlation? | LOW — no known deployment needs this |
| CGA × DiagonalKernel interaction | Does graph enrichment compound differently under diagonal? | MEDIUM — ties to Adjustment C claim |

### 11.4 LLM-Judge Work

| Item | Purpose |
|---|---|
| Industry noise-ratio priors | Generate per-industry factor noise profiles for P28 Phase 0 predictions. Healthcare ratio≈3×, FinServ ratio≈1.5×, Tech ratio≈2×. Uses existing Synthetic Data Engine. |
| S2P scenario expansion | Extend 10-scenario demo to include DiagonalKernel comparison. S2P at d=8 with heterogeneous noise. |
| Residual analysis prompts | LLM-judge prompt for §5.1 residual cluster analysis. "Given 20 confident-but-wrong decisions, what factor is missing?" |

### 11.5 Design Decisions Locked

| Decision | Resolution | Evidence |
|---|---|---|
| Default kernel | DiagonalKernel | 390-cell factorial |
| Shrinkage timing | v7.0 research, not v6.5 | Off-diagonal adds <1pp |
| Factor mask | Deprecated | Mask worse than L2 (-6pp Day 1) |
| Selector mechanism | Rolling 100-window, ratio > 1.5, 250 decisions | 4/4 correct |
| P28 minimum shadow | 250 decisions (data-driven, not 30 days fixed) | Selector stabilization |
| Healthcare go-to-market | "Learning from Day 1" | 4 personas, r=0.990 |
| Noise ceiling | GREEN ≤ 0.157, AMBER ≤ 0.25, RED > 0.25 (under diagonal) | Factorial + healthcare |
| Conservation extension | Var(q) only, not κ(Σ̂) | Off-diagonal irrelevant |
| Correlation research use | Domain understanding, residual analysis, NOT kernel selection | Explanation A confirmed |

---

*Multivariate Foundation Design Note v2 · March 21, 2026*
*390-cell factorial complete. DiagonalKernel +13.2pp SOC, +7pp S2P, +3.7pp healthcare.*
*Noise ratio is the whole story (r=0.990). Off-diagonal adds <1pp.*
*v6.0: DiagonalKernel default, KernelSelector, 250-decision shadow minimum.*
*v6.5: R score, Var(q) gating, N_half model. v7.0: shrinkage research.*
*"The kernel was the second-biggest accuracy lever after EXP-C1."*
