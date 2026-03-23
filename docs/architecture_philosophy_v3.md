# Architecture Philosophy: Five Layers of Compounding Intelligence
## Technical Reference and Implementation Specification

**Version:** v3.0 · March 21, 2026
**Status:** Technical reference, implementation spec, and graphic production guide.
**Supersedes:** architecture_philosophy_v2.0 (March 17, 2026)

**Companion documents:**
| Document | What It Contains |
|---|---|
| `consolidated_capability_plan_v3.2` | v6.0/v7.0+ capabilities, experiments, implementation paths |
| `math_synopsis_v10` | All equations, three-judge validated convergence analysis, DiagonalKernel |
| `claims_registry_v6.0` | 58 claims, 6 kernel-validated, 4 forbidden kernel claims |
| `platform_roadmap_v19` | What ships when, for whom. DiagonalKernel at v6.0. |
| `multivariate_foundation_design_note_v2` | Kernel design, factorial results, S2P correlation |
| `two_bridges_revised` | Bridge A (Level 2) + Bridge B (convergence × graph) formulations |

> **Changes from v2.0 → v3.0 (March 21, 2026 — DiagonalKernel + V-MV-KERNEL factorial):**
>
> **(1)** Layer 3 updated: pluggable kernels (L2 + DiagonalKernel). DiagonalKernel is v6.0
>     default. L2 is cold-start fallback. +13.2pp on heterogeneous data (390-cell factorial).
> **(2)** KernelSelector added to Layer 5 (Control Plane). The system calibrates the distance
>     metric, not just τ. Phase 2 rule + rolling 100-window + 250-decision lock.
> **(3)** CovarianceEstimator added to Layer 4 (collects covariance data, research asset for v7.0).
> **(4)** Bridge kernel constraint updated: L2 remains architecturally irreversible (36.89pp).
>     DiagonalKernel is a strict generalization — reduces to L2 when noise is uniform.
> **(5)** ARCH-01 graphic spec Band 3 updated with kernel notation.
> **(6)** Companion documents updated: claims_registry_v4→v6, roadmap_v15→v19,
>     multivariate_foundation_design_note_v2 added.
> **(7)** 478 GAE tests + 280 SOC tests (was 38 experiments). ~935 total across repos.
> **(8)** Conservation law extension: Var(q) per-analyst tracking (v6.0 observation, v6.5 gating).

**When to use this document:**
- Producing the ARCH-01 graphic (§Graphic section)
- Implementation-level cross-reference to code artifacts (§Mapping Table)
- Internal reference: Loop 4 PROPOSAL status, safety boundary enforcement
- Understanding how the five layers, bridge, and conservation law connect

---

## The Five Layers — Reference View

The five computational layers: dependency-ordered, each with a distinct artifact and
rate of change.

| Layer | Name | Artifact | Rate of Change | Implementation |
|---|---|---|---|---|
| 5 | Control Plane | r(t), 20:1 asymmetry, conservation law, **KernelSelector** | Continuous | Loop 1/2/3 + conservation law (Eq. CL) + kernel selection |
| 4 | Live Context Graph | Factor vectors f, Decision nodes, entity relationships, **CovarianceEstimator** | Continuous | PostgreSQL + Apache AGE, FactorComputers, covariance collection |
| 3 | Mathematical Engine | ProfileScorer, τ=0.1, **pluggable kernels (L2 + DiagonalKernel)** | Frozen | `gae/profile_scorer.py`, `gae/kernels.py`, `gae/kernel_selector.py` |
| 2 | Meta-Graph | μ₀ tensor [6 × 4 × 6] = 144 values (SOC, A=4). S2P: [5 × 5 × 8] = 200 values (A=5). | Slow — (1−η)^n, N_half ≈ 14 | `get_profile_centroids()` |
| 1 | Domain Ontology | DomainConfig | Rare | SOCDomainConfig, S2PDomainConfig |

**The compounding invariant:** remove any layer and the compounding stops. Layer 2 is
where firm-specific institutional judgment physically lives. The moat is in the evolved
centroids — not copyable, because they emerged from this firm's specific verified decisions.

**Convergence rate (three-judge validated, CLAIM-38):** Layer 2 centroids contract toward
the firm-specific optimum at rate (1−η)^n per verified decision. Half-life: N_half ≈ 14
decisions per (category, action) pair at η=0.05. Centroids track a stationary neighborhood
(Borkar 2008, Kushner & Yin 2003), not a fixed point — constant step size is an advantage
because it tracks drifting targets. Steady-state MSE = η·tr(Σ_f)/(2−η).

**Conservation law (three-judge validated, CLAIM-39):** Layer 5 enforces
α(t)·q(t)·V(t) ≥ θ_min — Level 2 operational adaptation cannot degrade Level 1's learning
signal. The two levels compound rather than conflict. θ_min derives from N_half, connecting
the conservation law to the convergence rate.

---

## The Bridge — Implementation View

The bridge spans the algorithmic world (Layers 1–3, tensor-shaped) and the operational
world (Layer 4, graph-structured).

| Component | Direction | Repository | Code Location | What It Does |
|---|---|---|---|---|
| **FactorComputers** | Graph → Math (upward) | gen-ai_roi | `services/factors/` | Traverse AGE graph → produce f ∈ [0,1]^d |
| **SituationAnalyzer** | Graph → Category (routing) | gen-ai_roi | `services/situation_analyzer.py` | Classify alert → select μ[c,:,:] slice. GATE-R: 100% routing. |
| **Decision Write-Back** | Math → Graph (downward) | gen-ai_roi | `services/triage.py` | Score + outcome → Decision node + `[:TRIGGERED_EVOLUTION]` |
| **Sentinel Write-Back** | Graph → SIEM (outward) | gen-ai_roi | `services/sentinel_writeback.py` | Campaign, IKS, confidence → Sentinel incidents (Graph Security API) |
| **Entity Resolution** | Graph → Graph (lateral) | ci-platform | `ci_platform/entity_resolution.py` | "john.smith" in AD = "jsmith" in VPN. Cross-source identity linking. |
| **Data Onboarding** | SIEM → Graph (inward) | ci-platform | `ci_platform/onboarding.py` | Bulk import 30-day history. Orchestrates S-01 + S-02 + FactorComputers in batch. |

**The kernel constraint (permanent):** The bridge kernel choice is architecturally
irreversible. L2 distance (Eq. 4-final): 97.89% zero-learning accuracy. Dot product
(v4.1): 61%. The 36.89pp gap is structural — it cannot be closed by accumulating more
decisions on the wrong kernel. Any new deployment must use L2 from day one.

**DiagonalKernel (v3.0 NEW):** P(a|f,c) = softmax(−(f−μ)ᵀ·diag(1/σ²)·(f−μ) / τ).
Weights = 1/σ² per factor from P28 measurement. +13.2pp on heterogeneous SOC data,
+6.8pp S2P (V-MV-KERNEL, 390 cells). DiagonalKernel is a strict generalization of L2 —
when noise is uniform (all σ equal), diagonal = L2. When noise is heterogeneous
(ratio > 1.5×), diagonal down-weights noisy factors and up-weights reliable ones.
**v6.0 default.** KernelSelector (Layer 5) determines which kernel based on noise ratio.
L2 is cold-start fallback before P28 measures per-factor σ.

**ShrinkageKernel (v7.0 research):** Off-diagonal factor correlations added <1pp to
scoring in 390-cell factorial (CLAIM-57). CovarianceEstimator collects full covariance
data at v6.0 but does NOT affect scoring. Deprioritized to v7.0 research.

**Graph-dependent convergence (three-judge validated, CLAIM-41):** The bridge's richness
directly affects centroid learning speed. Graph-dependent factor noise:
σ²_f(G) ≈ σ²_base / N_eff where N_eff = N_sources/(1+ρ(N_sources−1)). At ρ=0.8 (typical
SIEM cross-correlation), a second SIEM reduces factor noise by ~11%. Entity resolution
and ThreatIndicator accumulation provide additional convergence acceleration.

---

## The Meta-Computation: Compiled Ontologies — Implementation View

```
Ontology statement → Compiled centroid (compile-time):
  "For insider_threat alerts, escalate when
   asset_criticality is high and pattern_history is low."

μ[insider_threat, escalate, :] = [0.35, 0.85, 0.60, 0.15, 0.50, 0.30]
                                    ↑      ↑                  ↑
                                 travel  asset            pattern
                                 (low)  (HIGH)             (LOW)

This centroid is not a rule. It is a point in 6-dimensional factor space.
ProfileScorer computes distance from any incoming f to this point.
Under L2: ‖f − μ‖². Under DiagonalKernel: (f−μ)ᵀ·diag(1/σ²)·(f−μ).
```

**Four implementation consequences:**
1. The GAE library has zero domain logic — it computes distances, nothing else.
   Domain knowledge is entirely in the centroid values (Layer 2), not the engine (Layer 3).
   **Per-factor σ profiles are also compiled knowledge** — a firm's noise structure
   encoded as kernel weights. DiagonalKernel weights (1/σ²) are a second form of
   compiled ontology alongside centroids.
2. Centroid learning is kernel-aware: `μ ← μ + η·K.gradient(f, μ)`, clipped to [0,1].
   Under L2: gradient = (f−μ). Under DiagonalKernel: gradient = diag(1/σ²)·(f−μ).
   **High-noise factors learn slower by design.** Mean error contracts as (1−η)^n — after
   ~14 verified decisions per (c,a) pair, the error halves.
3. The critical separation: μ is NEVER updated using σ (synthesis bias). Loop 4
   awareness signal cannot contaminate Loop 2 experience signal. Architecturally enforced
   in ProfileScorer.update() which has no σ parameter. **σ affects gradient direction
   (via kernel weights), not learning rate (which is η, scalar).**
4. **Consistency from day 1 (CLAIM-31, CLAIM-40):** Before any centroid learns anything,
   every analyst gets the same recommendation from the same reasoning. At 70% system
   acceptance, (1−ō)² = 49% of case pairs are perfectly consistent from shared acceptance
   alone. This is the day-1 value proposition — no learning required.

---

## The Three Loops as Control Plane

| Loop | Spans | Mechanism | Governs | Code |
|---|---|---|---|---|
| **Loop 1: Score** | Layer 4 → 3 → 4 | FactorComputers → ProfileScorer → Decision write | What happens on each decision | `triage.py`, `profile_scorer.py` |
| **Loop 2: Learn** | Layer 4 → 3 → 2 | Verified outcome → centroid pull/push. μ evolves at (1−η)^n. | How the system changes between decisions | `learning.py`, `profile_scorer.update()` |
| **Loop 3: Reward** | Layer 5 → Loop 2 → Loop 1 | Asymmetric r(t): incorrect penalized 20×. Conservation law α·q·V ≥ θ_min. **KernelSelector: calibrates distance metric (v6.0 NEW).** | Rate, direction, safety of evolution, and scoring geometry | `reward.py`, CalibrationProfile, `kernel_selector.py` |

**Loop 3 is the governing signal** — it does not just add a penalty, it determines how
the other two loops behave. Without Loop 3, Loops 1 and 2 learn equally from successes
and failures. Loop 3 encodes the domain's risk preference (20:1 in SOC, 5:1 in S2P)
directly into the mathematics of centroid evolution.

**The conservation law (Eq. CL, CLAIM-39) IS the formal expression of Loop 3's governance:**

```
α(t) × q(t) × V_verified(t) ≥ θ_min

where:
  α(t) = analyst override rate (fraction disagreeing with system)
  q(t) = override quality (fraction of overrides that are correct corrections)
  V_verified(t) = verified decisions per day
  θ_min ≥ N_half / T_window per active (c,a) pair
```

Connection to convergence: θ_min derives from N_half (Bridge B). As graph matures →
N_half decreases → θ_min decreases → Level 2 has more optimization freedom →
better framing → more verified decisions → faster graph enrichment. **The compounding
flywheel, formally connected.**

**Two mechanisms in Loop 2** (two-level institutional judgment):

- **ProfileScorer** (Level 1 — Decision Intelligence): centroids μ encode *what to decide*.
  Slow-moving (months). Convergence rate (1−η)^n, half-life N_half ≈ 14 (Borkar 2008,
  three-judge validated). Each verified outcome pulls or pushes the relevant centroid.

- **AgentEvolver** (Level 2 — Deployment Intelligence): variant success rates encode *how
  to operate*. Moderate-moving (weeks). **Formalized as a conservative contextual bandit
  (Wu et al. 2016, Kazerouni et al. 2017, three-judge validated, CLAIM-42).** K prompt
  variants per (category, context). Phase-gated composite reward. Four-condition promotion
  gate:
  ```
  (1) Superiority:       P(μ_v > μ_baseline + Δ_min | data) > 1−α
  (2) Correctness floor: outcome_quality(v) ≥ outcome_quality(baseline)
  (3) Conservation law:  α(t)·q(t)·V(t) ≥ θ_min
  (4) Variance stability: σ²_{r,v} ≤ σ²_{r,baseline} × (1+δ)
  ```
  N_gate ≈ 445 per arm (one-sided, α=0.05, β=0.20). No variant promoted without
  statistical evidence of improvement AND maintenance of Level 1's learning signal.

**Known failure modes (three-judge identified):**
- **Automation complacency:** Level 2 selects high-acceptance variant → α(t) drops →
  Level 1 receives fewer corrections → compounding stalls. Conservation law (Gate 3)
  prevents by rejecting any variant pushing signal below θ_min.
- **Level 2 adversarial poisoning (Gemini finding):** Malicious analyst forces variant
  promotion. Mitigation: Gate 2 (correctness floor) + planned EXP-L2-POISON.
- **Expert fatigue secondary loop (Gemini finding):** Level 1 improves → alert volume
  drops → analyst fatigue decreases → q(t) increases → Level 1 gets better signal.
  A third compounding mechanism.

**Safety boundaries enforced by the control plane:**
- Centroid clipping to [0.0, 1.0] — prevents adversarial centroid escape (V2 validated)
- Temperature τ=0.1 — ensures well-calibrated confidence (V3B: ECE=0.036)
- LayerNorm — prevents norm explosion in enrichment (V1B: 2.9M× without it)
- Conservation law — prevents Level 2 from degrading Level 1
- Centroid support monitoring — flags (c,a) pairs that leave data support (Opus finding)
- Full provenance logging: every centroid update records f(t), r(t), μ_before, μ_after

---

## The Fourth Loop: Synthesis (PROPOSAL — gated by EXP-S1–S8)

> **Status:** Designed extension, not validated capability. The three loops above are
> validated by ~104 experiments (including V-MV-KERNEL 390-cell factorial). Loop 4 is gated by 8 experiments (EXP-S1–S8) with
> 3 decision gates (GATE-M/D/V). GATE-M PASSED (March 14, 2026). GATE-D and GATE-V
> pending. If remaining experiments fail, the three-loop model is complete.

**Layer 2 extended with a second resident:**
- μ[c,a,:] — operational centroids (experience). Source: Loop 2. Rate: slow (months).
- σ[c,a] — synthesis bias (awareness). Source: Loop 4. Rate: fast (days).

**Extended equation:**
```
P(a|f,c,σ) = softmax(−(‖f − μ[c,a,:]‖² + λ·σ[c,a]) / τ)  — Eq. 4-synthesis
```
λ=0 → exact Eq. 4-final (kill switch; no regression). τ=0.1 (fixed).
GATE-OP: λ=0.5 operative window confirmed (p=0.0008).
EXP-S2-REPRO: poisoning resilience 0.15pp max at production λ=0.5.

**Note:** τ_mod (urgency-based temperature adjustment) was **permanently rejected**
(ECE +0.138 at any τ_mod ≠ 1.0, CLAIM-11). The equation above is the final form.

**Loop 4 in the table:**

| Loop | Updates | Rate | Temporal role |
|---|---|---|---|
| Loop 1: Score | decisions | every alert | instant |
| Loop 2: Learn | μ (centroids) | slow — months | past experience |
| Loop 3: Reward | learning rate + conservation law | per outcome | permanent meta-signal |
| **Loop 4: Synthesize** | **σ (bias)** | **fast — days** | **current awareness** |

**The constraint is architectural:** Loop 4 updates σ. Loop 2 updates μ. They never cross.
ProfileScorer.update() has no σ parameter. Validated: Frobenius norm divergence 0.0028
(CLAIM-18, EXP-S3).

---

## Graph-Dependent Convergence — Why the Graph IS the Moat [NEW v2.0]

The convergence equations (§3.1 of math_synopsis_v10) treat factor noise Σ_f as fixed.
In practice, Σ_f depends on graph richness — because FactorComputers TRAVERSE the graph
to produce factor values. A richer graph produces more informative factors.

**Three mechanisms (three-judge validated, CLAIM-41):**

| Mechanism | How Graph Maturity Helps | Effect on Convergence |
|---|---|---|
| Multi-source noise averaging | More corroborating sources → lower σ²_f (ρ-adjusted) | Steady-state neighborhood shrinks |
| Entity resolution | Cross-source identity linking → richer per-alert context | Initial error ‖e_0‖ decreases |
| ThreatIndicator accumulation | Persistent IOC memory → enriched threat_intel factor | σ²_threat_intel decreases over time |

**The ρ correction (Gemini):** Security sources are highly correlated (ρ≈0.8), not
independent. At ρ=0.8, adding a second SIEM reduces variance by ~11%, not 50%.
N_eff = N_sources/(1+ρ(N_sources−1)).

**Connection to temporal compounding γ:** If graph richness grows with time, N_converge
decreases with time — effective learning speed increases. This is the mechanism-level
grounding for γ>1. Bridge B is the engine; γ>1 is the result. Empirical measurement
requires EXP-G1 (v7.0).

---

## How This Maps to Current Documents

| This Framework | math_synopsis_v10 | consolidated_capability_plan_v3.2 | Repository |
|---|---|---|---|
| Layer 1: Domain Ontology | Not discussed | Part 1 (DomainConfig) | gen-ai_roi |
| Layer 2: Meta-Graph | μ tensor (Eq. 4-final), §3.1 convergence | M-01, M-02 | gae, gen-ai_roi |
| Layer 3: Mathematical Engine | Eq. 4-final, 4b-final | M-01 (ProfileScorer) | gae |
| Layer 3: Pluggable Kernels | design_note_v2 §3 | CLAIM-53–58 (kernel-validated) | gae (kernels.py, kernel_selector.py) |
| Layer 4: Live Context Graph | §10.1 graph-dependent convergence | S-01, S-02, S-08, L-06 | ci-platform, gen-ai_roi |
| Layer 5: Control Plane | §5 (conservation law, Eq. CL) | M-03, M-04, L-09 | gen-ai_roi |
| The Bridge | §3 (scoring), §10.1 (graph → convergence) | Part 4 (Substrate) | ci-platform |
| Compiled Ontology | Eq. 4 (μ as compiled knowledge) | M-01 (CLAIM-19) | gae |
| Two Levels (L1/L2) | §3.1 (Level 1 convergence), §5 (Level 2 bandit) | M-02 + M-03, Bridge A + Bridge B | gae, gen-ai_roi |
| Conservation Law | Eq. CL (§5) | CLAIM-39, L-09 condition 3 | gen-ai_roi |
| Graph-Dependent Convergence | Eq. σ²_G (§10.1) | CLAIM-41, L-08, Bridge B | gae (convergence.py) |

**Four repositories:**

| Repo | License | Contains |
|---|---|---|
| **graph-attention-engine** | Apache 2.0 | Mathematical engine — scoring, learning, convergence, evaluation, **pluggable kernels (L2/Diagonal), kernel selection, covariance estimation. 478 tests.** |
| **ci-platform** | Apache 2.0 | Shared infrastructure — domain config, connectors, entity resolution, data onboarding |
| **gen-ai_roi** | Proprietary | SOC Copilot — UI, triage pipeline, FactorComputers, tabs, APIs, **ReferralRules R1-R7 (VETO mechanism). 280 SOC tests.** |
| **cross-graph-experiments** | Internal | Experiment infrastructure — simulation configs, 50-seed sweeps, bridge experiments |

**Production data layer:** PostgreSQL 16 + Apache AGE (openCypher on production-grade
infrastructure). Critical state (centroid tensors, Evidence Ledger) in relational tables
with online backup + PITR. Graph traversals via AGE Cypher queries on the same instance.

---

## The Graphic: "Five Layers of Compounding Intelligence" (ARCH-01)

**Graphic ID:** ARCH-01 (also acceptable: CI-06)
**Status:** Not yet produced. Replaces stale `soc_ai_decision_logic.png`.
**Priority:** HIGH — needed for blog publish and slide deck.

**Dimensions:** 980×700 (blog) · 1920×1080 (slide) · 800×600 (doc embed)
**Style:** Dark background, five colored horizontal bands with return-path arrows.
Match existing CI-01 through CI-05 series style.

**Band layout (bottom to top):**

**Band 1 — DOMAIN ONTOLOGY (dark blue):**
Icons: brain, checklist, shield.
Text: "Expert Knowledge: factors, actions, categories, risk preferences"
Subtext: "DomainConfig — changes rarely"
Callout: "For credential_access: asset_criticality and time_anomaly are discriminative"

**Band 2 — META-GRAPH: COMPILED PROFILES (teal):**
Central element: 3D tensor cube labeled "μ₀[c, a, :] — 6 × 4 × 6 = 144 values (SOC, A=4)"
Text: "Domain ontology compiled into geometry"
Subtext: "Convergence: (1−η)^n · N_half ≈ 14 decisions · Steady-state MSE = η·tr(Σ_f)/(2−η)"
Callout: "μ[insider_threat, escalate, :] = [0.35, 0.85, 0.60, 0.15, 0.50, 0.30]"

**Band 3 — MATHEMATICAL ENGINE (green):**
Central element: equation "P(a|f,c) = softmax(−d(f, μ) / τ)"
Text: "Pluggable kernel scoring — domain-agnostic (GAE library, Apache 2.0)"
Subtext: "L2: ‖f−μ‖² · DiagonalKernel: (f−μ)ᵀ·diag(1/σ²)·(f−μ) · +13.2pp on heterogeneous data"
Note: "DiagonalKernel is v6.0 default. L2 is cold-start fallback. 478 tests."
Arrows: "f (from graph)" upward from Band 4; "P(action) → decision" downward to Band 4

**Band 4 — LIVE CONTEXT GRAPH (amber):**
Central element: small graph (PostgreSQL + AGE style nodes and edges)
Text: "PostgreSQL + Apache AGE: alerts, decisions, outcomes, entities, relationships"
Node labels: Alert, Decision, Outcome, User, Asset, ThreatIndicator, Campaign
Subtext: "Graph enrichment → ρ-adjusted convergence acceleration (Bridge B)"

**Band 5 — CONTROL PLANE (red/orange):**
Three loop icons (Loop 1/2/3). Fourth loop icon dashed (PROPOSAL).
Central element: "α(t)·q(t)·V(t) ≥ θ_min" — the conservation law equation
Text: "Governs rate, direction, and safety of evolution"
Subtext: "Loop 3 governs Loops 1 and 2 — conservation law ensures two-level compounding"

**Right-side return arrows (prominent):**
- Large curved arrow: Layer 4 outcome → Layer 5 → Layer 2. Label: "Verified outcomes reshape the geometry — (1−η)^n convergence"
- Smaller curved arrow: Layer 4 → Layer 3. Label: "Factor vectors feed scoring"
- Dashed curved arrow: Layer 4 → Layer 2 (σ path). Label: "Awareness signal (Loop 4, PROPOSAL)"

**Left-side Level 2 detail panel (new in v2.0):**
Small inset showing the two-level structure:
- "Level 1 (Decision Intelligence): μ evolves from verified outcomes. Slow."
- "Level 2 (Deployment Intelligence): variants selected by 4-condition gate. Moderate."
- "Conservation law connects them: θ_min = f(N_half)"

**Bottom-right callout:**
"The moat is in the evolved centroids. A competitor can copy the math (open source),
copy the schema, even copy the initial profiles. They cannot copy 10,000 verified
decisions that reshaped the geometry to encode this firm's institutional judgment.
And the conservation law ensures the geometry compounds safely."

**Additional graphics needed:**
TWO-LEVELS · KERNEL-COMPARE · COMPILED-ONTO · TEMPORAL-4 · CONSERVATION-LAW · FC-07
Conservation law visualization: α·q·V trajectory over time with θ_min floor line.

---

## Insertion Guidance — Math Synopsis v10

**Reference document:** `docs/math_synopsis_v10.md`
**The architecture philosophy maps to these sections:**

| This Document | math_synopsis_v10 Section |
|---|---|
| Five Layers table | §1 (architecture paragraph), §6 (centroid tensor) |
| Bridge implementation | §3 (scoring equation), §10.1 (graph-dependent convergence) |
| Compiled ontology | §3 (Eq. 4-final interpretation), §6 (centroid examples) |
| Three Loops / Control Plane | §5 (four feedback loops), §5 Level 2 formalization |
| Conservation law | §5 (Eq. CL), §16 (constraints table) |
| Convergence rate | §3.1 (Eq. CONV, MSE∞, N_CONV) |
| Graph-dependent convergence | §10.1 (Eq. σ²_G, three mechanisms) |

---

## Insertion Guidance — Consolidated Capability Plan

**Reference document:** `consolidated_capability_plan_v3.2.md`
**The architecture philosophy maps to these capabilities:**

| This Document | Plan Section |
|---|---|
| Layer 2 convergence | M-02 (centroid learning), L-08 (onboarding calendar) |
| Level 2 formalization | M-03 (AgentEvolver), Bridge A |
| Conservation law | M-04 (asymmetric RL — now formally expressed as Eq. CL), L-09 condition 3 |
| Bridge implementation | Part 4 (Substrate: S-01, S-02, S-08), Part 4A (ci-platform extraction) |
| Graph-dependent convergence | Bridge B, L-08 (onboarding calendar predictions) |
| Compiled ontology | M-01 (CLAIM-19) |
| Five Layers | Strategic Frame, v5.5 shipped table |

---

*Architecture Philosophy v3.0 · March 21, 2026*
*Technical reference and implementation spec. ~104 experiments, 478 GAE + 280 SOC tests (~935 total).*
*PostgreSQL + Apache AGE production data layer. Four repositories. 144-value centroid tensor (SOC, A=4).*
*DiagonalKernel (1/σ²) is v6.0 default: +13.2pp on heterogeneous data. L2 is cold-start fallback.*
*KernelSelector calibrates the distance metric (Layer 5). CovarianceEstimator collects (Layer 4).*
*ReferralRules R1-R7: policy-based VETO mechanism (72.7% DR, 12% FPR). Override learning v6.5.*
*Conservation law α(t)·q(t)·V(t) ≥ θ_min ensures two-level compounding (three-judge validated).*
*Level 2 formalized as conservative contextual bandit with four-condition promotion gate.*
*Convergence rate (1−η)^n, N_half ≈ 14. Graph-dependent convergence with ρ-adjusted N_eff.*
*SOC A=4 / S2P A=5 — intentional asymmetry. refer_to_analyst via confidence gate (action routing).*
*ARCH-01 graphic spec updated — do not modify without updating the brief.*
*"The moat is in the evolved centroids AND their kernel weights. Both encode firm-specific judgment."*
