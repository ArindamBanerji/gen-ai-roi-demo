# Claims Registry — Compounding Intelligence Platform
**Version:** 3.2 · March 15, 2026
**Status:** Working document. Claims move forward only (blocked → conditional → unconditional). If an experiment fails a gate, the claim is removed or narrowed — never reinstated at prior strength.
**Supersedes:** claims_registry_v3_1 (March 14, 2026)
**Companion documents:** gae_design_v9.2, math_synopsis_v9, product_requirements_gap_analysis_v1, platform_roadmap_v13

> **Changes from v3.1 → v3.2 (March 15, 2026 — calibration science + bug fix):**
>
> (1) **CLAIM-01 routing gap CLOSED.** CORR-1a fixed 68% misroute. ALERT_TYPE_CATEGORY_MAP
>     created (20 entries). GATE-R can now run. Routing gap qualifier updated.
> (2) **CLAIM-04 updated.** Per-category ECE from PROD-4b: 0.017–0.037 at η_neg=0.05.
>     η_neg=1.0 produces ECE=0.49 — FORBIDDEN. New per-category calibration data added.
> (3) **CLAIM-19 category name corrected.** insider_behavioral → insider_threat (code reality).
> (4) **CLAIM-21 updated.** 243 → 251 tests. ProfileScorer.update() gt_action_index bug fix.
> (5) **CLAIM-25 updated.** Promotion gate revised: DISC-1 composite discriminant achieves
>     70.4% coverage at 85% precision (frozen scorer). Original "40% target" superseded.
> (6) **CLAIM-30 updated.** 243 → 251 tests.
> (7) **CLAIM-32 through CLAIM-37 added (NEW).** Frozen scorer baseline, composite
>     discriminant, update bug fix validation, η_neg design decision, IKS v2 concept.
> (8) **FUTURE-12 updated.** "40% auto-approve" → "Composite discriminant: 70% coverage
>     at 85% precision (frozen, synthetic). Production claim pending shadow validation."
> (9) **FUTURE-19 promoted to ACTIVATED.** PROD-3 complete: 71.9% overall [71.1%, 72.7%].
> (10) **§3A updated.** 28 → 34 experiments. PROD-4b/final/warmup, SHIFT-1/2, DISC-1 added.
> (11) **§4.2 routing non-claim CLOSED.** CORR-1a resolved G-L1-1.
> (12) **Appendix updated.** "40% auto-approve" forbidden claim updated with DISC-1 numbers.
>      ProfileScorer.update() bug noted in §5.2 downgrade triggers.
> (13) **C=5→6, (5,5,6)→(6,5,6), 150→180 throughout.** Ontology verified March 14.

> **Changes from v3.0 → v3.1 (March 14, 2026 — 3 experiments completed):**
> (1) **CLAIM-17 updated.** NR rate: 35% (N=20) → 38% [29%, 48%] (N=100). CI collapsed
>     from [15%, 59%]. EXP-OP2-N100 complete. P-75 paradox strengthened (28% vs 24%).
>     Baseline fragility noted: condition A has 24% NR — checkpoint+rollback is general infra.
> (2) **CLAIM-27 updated.** 25 → 28 experiments. Production companion paper added [Banerji, 2026c].
> (3) **FUTURE-03 promoted to ACTIVATED.** EXP-S2-REPRO complete (3-arm, GATE-M satisfied).
>     Poisoning resilience confirmed at production λ=0.5: 0.15pp max degradation.
> (4) **FUTURE-09 promoted to ACTIVATED.** FX-1-PROXY-REAL complete (2,430 IOCs, KL 1.88–2.58).
>     Distribution gap quantified. Motivates Mahalanobis kernel and multi-prototype extensions.
> (5) **§3B planned experiments updated.** FX-1-PROXY-REAL and EXP-S2-REPRO moved from blocking
>     to completed. EXP-OP2-N100 removed from blocking (characterization complete).
> (6) **§4.4 forbidden claims updated.** "Poisoning-resistant" conditionally promotable with
>     stated conditions (λ=0.5, σ_max clipping active, centroidal synthetic).
>     "Adapts to threat landscape" partially unblocked (GATE-M passed, GATE-D still needed).
> (7) **§5 trigger table updated.** FX-1-PROXY-REAL trigger resolved with results.
> (8) **CLAIM-15 promotion updated.** GATE-M now satisfied — promotion path clear.

> **Changes from v2 → v3 (design_strategy_updates_v1 §4.2):**
> (1) **CLAIM-31 added (new, unconditional).** The consistency claim — every analyst gets
>     the same starting recommendation from the same reasoning every time. Currently absent
>     from the registry. Highest-value claim for CISO demo and ICP trigger conversations.
> (2) **CLAIM-01 condition tag updated.** Added G-L1-1 routing gap qualifier: ~20% of
>     alert_type values fall through to default category at v5.0. Composite accuracy claim
>     cannot be made with CLAIM-01 until v5.5-R6 ships and GATE-R runs.
> (3) **CLAIM-21 updated.** Hooks 1/2/3 (DecisionRecord, OutcomeRecord, ProfileSnapshot)
>     stated as v5.0 write obligations. Without Hook 1 active from day 1, GATE-R cannot run
>     retroactively and routing data is permanently lost.
> (4) **FUTURE-18, FUTURE-19, FUTURE-20 added.** Three new future claims gating PROD-1
>     (IKS calibration), PROD-3 (shadow mode calibration baseline), and PROD-5 (category
>     convergence / onboarding calendar). These are the v5.5 demo-conversion claims.
> (5) **§4.1 two new non-claims added.** (a) N3 endogenous loop — calibration error →
>     verification selection bias → worse calibration — is an unresolved open issue with
>     no intervention point designed. (b) Minimum verification rate floor — compounding
>     not characterized below ~15% verified decisions — is an open issue blocking the
>     core product promise.
> (6) **§4.2 routing gap item added.** Correct routing from all alert types is not
>     available at v5.0 (G-L1-1 ~20% misroute). Explicit non-claim added.
> (7) **Appendix forbidden claim added.** "System accuracy compounds regardless of analyst
>     verification quality" — forbidden until GATE-V. Loop 2 learns from verified outcomes;
>     systematically biased verification produces systematically biased centroids.
> (8) **Companion doc math_synopsis_v6 → v7** in §1.5 context note and §3A experiment
>     mapping table.

**Changes from v1 → v2:**
> (1) **Section 1.5 added: Realistic Accuracy Claims.** Four new unconditional claims from math_synopsis_v6 50-seed validation. These are the honest product claims. Separate from synthetic experimental claims (§1.1).
> (2) **Section 1.6 added: Open-Source Credibility Claims.** What can be stated about GAE's open-source position. Apache 2.0, math peer-reviewable, experiments public.
> (3) **CLAIM-21 updated.** v5.0 is now COMPLETE — oracle, evaluation, judgment, ablation, users guide all shipped. 243 tests.
> (4) **Section 0 added: How to Use This Registry.** Audience-specific guidance for buyer conversations, technical evaluations, and public communications.
> (5) **Section 5 added: Claim Health — Periodic Review Protocol.** When to re-examine claims and what triggers a status downgrade.
> (6) **Section 4.2 expanded.** Three new non-claims derived from product_requirements_gap_analysis_v1 gap analysis.
> (7) **FUTURE-12 through FUTURE-17 added.** New future claims aligned with v5.5 requirements.
> (8) **Section 2.1 promotion paths updated.** CLAIM-21 promoted to reflect v5.0 complete.

---

> **Foundation Rule:** A claim stated without its condition is a false claim. The condition is not a footnote — it is part of the claim. This applies even in casual conversation.
>
> **Two Accuracy Regimes (CRITICAL):** The 97.89%/98.2% numbers (§1.1) are centroidal synthetic experiments. The 71.7%/78.9% numbers (§1.5) are 50-seed realistic product claims. These measure different things and must never be mixed in the same sentence or compared to each other without explicit context labeling.

---

## Section 0: How to Use This Registry

### 0.1 Audience-Specific Guidance

**When talking to a CISO (buyer):**
Use §1.5 Realistic Accuracy Claims. These are the honest product numbers. 71.7% static, 78.9% at 1,000 decisions, 90.7% auto-approve accuracy. Do not lead with 97.89% — it requires too much context to explain correctly, and it will come up in due diligence in a way that damages trust if it was stated without conditions.

**When talking to a technical evaluator (ML architect, SOC architect):**
Use §1.1–1.4 freely with their stated conditions. Technical evaluators want to know what the system can do mathematically. The synthetic numbers are valid here — provided the conditions are stated. They also want §4.1 (where GAE does not apply) — a system that knows its limits is more credible than one that claims universal applicability.

**When writing a blog post or LinkedIn post:**
Use ✅ UNCONDITIONAL claims without modification. Use ⚠️ CONDITIONAL claims only if the condition is stated in full. Use 🔵 INTERNAL ONLY claims never — they are not cleared for external communication.

**When writing investor materials:**
Use §1.5 (realistic numbers) as the primary performance claim. Use §1.6 (open-source) to establish credibility. Use §1.2 CLAIM-12 (b=2.11 scaling) as the "compounding moat" claim — it is unconditional. State CLAIM-13 (γ temporal) as "estimated, pending EXP-G1 confirmation."

**When responding to a challenge ("your 97.89% is synthetic"):**
Say yes, that's correct, that's why we also have 50-seed realistic validation: 71.7% static, 78.9% at 1,000 decisions. The synthetic number validates the scoring mechanism. The realistic number is the product claim. Here's the distinction: [point to §4.4 Two Regimes].

### 0.2 Status Vocabulary

| Status | Meaning | External Use |
|---|---|---|
| ✅ UNCONDITIONAL | No caveat needed internally or externally | Use freely |
| ⚠️ CONDITIONAL | Must include the stated condition every time, always | Use with condition |
| 🔵 INTERNAL ONLY | Design docs only — cannot appear in outreach | Never external |
| 🚫 FORBIDDEN | Listed in Appendix — do not make this claim | Never |

### 0.3 The Single Most Common Mistake

Citing the 97.89% number without stating it is centroidal synthetic data with ground-truth profiles. Even in casual conversation. Even to people who understand the distinction. Always include the condition. It takes 8 extra words. Omitting it takes 10 minutes to repair.

---

## Section 1: Claims We Can Make NOW

---

### 1.1 Scoring Accuracy Claims (Synthetic Centroidal Data)

> **Important context for all §1.1 claims:** These are centroidal synthetic experiments — ground-truth initialized profiles, oracle-initialized centroids, noise-free factor distributions. They validate the scoring *mechanism*. For product performance claims, see §1.5.

---

**CLAIM-01** ⚠️ CONDITIONAL
> **Statement:** The L2 centroid profiler achieves 97.89% zero-learning scoring accuracy.
> **Condition (mandatory every external use):** *Centroidal synthetic data; ground-truth initialized profiles; C=6 production SOC categories. Assumes correct category routing.*
> **Routing gap qualifier (v3.2 — CLOSED March 14):** CORR-1a created ALERT_TYPE_CATEGORY_MAP (20 entries) and resolve_alert_category(). 68% misroute eliminated. GATE-R can now run to measure routing accuracy. Until GATE-R completes, composite accuracy (routing × scoring) is unmeasured — state CLAIM-01 with the "assumes correct routing" condition.
> **Evidence:** EXP-C1
> **Promotion gate:** GATE-R (routing accuracy on real or realistic data).
> **What you CANNOT say:** "97.89% accuracy." "97.89% system accuracy." Any use without the condition and routing gap qualifier active until v5.5-R6 ships.
> **Why this exists:** Validates that the L2 distance kernel with profile centroids is the right mechanism. The 97.89% is the theoretical ceiling — it answers "does the math work?" not "does the product work?"

---

**CLAIM-02** ⚠️ CONDITIONAL
> **Statement:** With centroid learning from verified outcomes, scoring accuracy improves to 98.2%.
> **Condition:** *Centroidal synthetic data; warm-start; noise-free oracle outcomes.*
> **Evidence:** EXP-B1
> **Promotion gate:** GATE-R + real-data validation.
> **What you CANNOT say:** "Learns its way to 98.2%." Any implication of real-world trajectory.

---

**CLAIM-03** ⚠️ CONDITIONAL
> **Statement:** L2 centroid scoring maintains 98.1% accuracy with 30% oracle noise.
> **Condition:** *Centroidal synthetic data; warm-start; noise applied to oracle outcomes, not factor vectors.*
> **Evidence:** EXP-B1
> **Usage:** Noise tolerance in pitches when technical evaluators ask about imperfect analyst feedback. Valid framing: "Robust to outcome label noise." But state the condition.

---

**CLAIM-04** ⚠️ CONDITIONAL
> **Statement:** The scoring engine is well-calibrated: ECE = 0.036 at τ=0.1 (global). Per-category ECE ranges from 0.017 (cloud_infrastructure) to 0.037 (data_exfiltration) at η_neg=0.05.
> **Condition:** *Centroidal synthetic data. τ=0.1 must be used. η_neg=0.05 must be used.*
> **Evidence:** V3B (global), PROD-4b (per-category, March 14)
> **CRITICAL η_neg constraint:** At η_neg=1.0, ECE=0.490 (catastrophic miscalibration). η_neg=1.0 is FORBIDDEN in production. See soc_copilot_design_v5_6 §22.6.
> **Comparison permitted (unconditional):** "Previous architecture at τ=0.25 had ECE=0.19 — 5× worse calibration."
> **Promotion gate:** TD-034 τ recalibration on ≥200 real alerts.

---

**CLAIM-05** ⚠️ CONDITIONAL
> **Statement:** L2 centroid scoring beats XGBoost trained on 1,300 labeled samples: 94.78% vs 92.24%.
> **Condition:** *Centroidal synthetic held-out data; XGBoost trained to convergence on same synthetic data.*
> **Evidence:** V3A
> **Valid framing:** "Exceeds a trained ML baseline — and requires zero labeled samples to start."

---

**CLAIM-06** ⚠️ CONDITIONAL
> **Statement:** L2 centroid scoring achieves 94.3% accuracy at decision 1 — before XGBoost can be trained.
> **Condition:** *Centroidal synthetic data; XGBoost requires ≥1,300 samples to reach comparable performance.*
> **Evidence:** V3A
> **Valid framing:** "Operational from day one. No training window." But state the synthetic condition.

---

**CLAIM-07** ⚠️ CONDITIONAL
> **Statement:** The architecture scales to 20×10×20 (domains × categories × factors) at 99.9% accuracy.
> **Condition:** *Centroidal synthetic data; ground-truth profiles. Cold-start at this scale degrades to 72.7%.*
> **Evidence:** EXP-E2
> **What you CANNOT say:** "99.9% at enterprise scale." The 99.9% requires GT profiles.

---

### 1.2 Architecture and Design Claims

---

**CLAIM-08** ✅ UNCONDITIONAL
> **Statement:** The Gating Matrix G architecture is experimentally falsified. G adds +0.01pp best case. It does not generalize.
> **Evidence:** EXP-A (4 variants)
> **Usage:** Defending architecture choices. Always valid.

---

**CLAIM-09** ✅ UNCONDITIONAL
> **Statement:** Dot product is structurally inappropriate for profile matching: 61% vs L2 at 97.89% on the same data. L2 measures proximity to a known profile; dot product measures alignment. These are different geometric questions.
> **Evidence:** EXP-C1 (36.89pp gap)
> **Usage:** Kernel choice justification. Always valid.

---

**CLAIM-10** ✅ UNCONDITIONAL
> **Statement:** Centroid updates without clipping to [0,1] allow adversarial escape at decisions 6–12. Clipping is a required safety constraint, not an implementation choice.
> **Evidence:** V2
> **Usage:** Architecture security review. Always valid.

---

**CLAIM-11** ✅ UNCONDITIONAL
> **Statement:** τ_modifier (synthesis-conditioned temperature) is permanently rejected. Any τ_mod ≠ 1.0 degrades calibration by ECE +0.138. Temperature is fixed at τ=0.1 regardless of synthesis state.
> **Evidence:** OP series (τ_modifier tests)
> **Usage:** Defending temperature design. Always valid.

---

**CLAIM-12** ✅ UNCONDITIONAL
> **Statement:** The domain scaling exponent is b=2.11 ± 0.03 (R²=0.9999, n=2–15 simulated domains). Institutional intelligence surface area scales as 𝒮(n) ~ O(n^{2.11}) with the number of connected domains.
> **Precision condition:** *Simulation result measuring cross-domain pair counts. Not a real multi-domain deployment measurement.*
> **Evidence:** V1A
> **What you CANNOT say:** "Compounds exponentially." It is super-quadratic (b=2.11). Say "scales as n^2.11" or "super-quadratic scaling."

---

**CLAIM-13** 🔵 INTERNAL ONLY
> **Statement:** Temporal compounding exponent γ≈1.5 is estimated. If confirmed (γ>1.0), each enrichment sweep is more productive than the last.
> **Why internal only:** γ has not been measured. EXP-G1 is the gate (v6.0).
> **Forbidden externally:** "The system compounds over time." "Every sweep surfaces more connections than the last." These require γ>1.0 confirmed.
> **What IS valid externally (CLAIM-12):** The n^2.11 spatial scaling. That is measured.

---

**CLAIM-14** ✅ UNCONDITIONAL
> **Statement:** LayerNorm is required in cross-domain enrichment sweeps. Without it, embedding norms explode 2.9M× by sweep 5. This is not a design preference — it is a failure mode.
> **Evidence:** V1B
> **Usage:** Level 2 design justification. Always valid.

---

### 1.3 Intelligence Layer Claims (GATE-OP Results)

---

**CLAIM-15** ⚠️ CONDITIONAL
> **Statement:** Synthesis bias σ[c,a] at λ=0.5 produces a statistically significant AUAC improvement: δ=+0.0041, p=0.0008.
> **Condition (mandatory):** *Centroidal synthetic data; Loop 2 running; 100%-correct operator; acute phase only (~first 40 decisions). Benefit is not sustained indefinitely.*
> **Evidence:** EXP-OP2 (GATE-OP PASSED)
> **What you CANNOT say:** "σ improves accuracy by 0.4%." State the AUAC gain and p-value directly.

---

**CLAIM-16** ⚠️ CONDITIONAL
> **Statement:** The operative window for synthesis bias is λ∈[0.5, 0.6] (Bonferroni-significant, Loop 2 running).
> **Condition:** *Centroidal synthetic data; Loop 2 running; 100%-correct operator. Cold-start plateau is different: λ∈[0.2, 0.5].*
> **Evidence:** EXP-OP2
> **Hard rule:** Never deploy λ>0.6. Never cite the cold-start plateau as the operative window.

---

**CLAIM-17** ✅ UNCONDITIONAL
> **Statement:** A harmful operator (0% correct) causes centroid damage where 38% of affected (category, action) cells never recover within 400 decisions after TTL expiry (N=100, 95% CI [29%, 48%]; originally 35% at N=20). A 75%-correct operator (P-75) shows 28% non-recovery — worse than no operator (24%), confirming the P-75 paradox. TTL expiry alone is insufficient as a safety mechanism. Checkpoint/rollback infrastructure is required (TD-033). Baseline fragility: even condition A (no operator) has 24% NR [17%, 33%], making checkpoint+rollback general infrastructure, not just a synthesis safeguard.
> **Evidence:** EXP-OP2 (T_recovery paradox)
> **Usage:** Safety architecture justification. Always valid.

---

**CLAIM-18** ✅ UNCONDITIONAL
> **Statement:** The Loop 2 / Loop 4 firewall is validated. Running σ active with Loop 2 simultaneously produces Frobenius norm divergence of 0.0028 — statistically indistinguishable from no-σ. μ is never directly corrupted by σ at the operative window.
> **Evidence:** EXP-S3
> **Precision condition:** *Direct firewall only — update() has no σ parameter. Indirect pathway (σ-influenced decisions → centroid drift) is bounded but not yet independently quantified (EXP-OP4 planned).*

---

### 1.4 Architecture Design Claims (Non-Quantitative)

---

**CLAIM-19** ✅ UNCONDITIONAL
> **Statement:** Profile centroids are compiled domain ontologies. Expert knowledge ("for insider_threat alerts, escalate when asset_criticality is high and pattern_history is low") is compiled into a point in n_f-dimensional factor space. The mathematical engine operates on this point with no domain knowledge.
> **Usage:** Core architectural concept. Always valid.

---

**CLAIM-20** ✅ UNCONDITIONAL
> **Statement:** The SOC copilot bridge has four components: FactorComputers (graph → math), SituationAnalyzer (category routing), Decision + Outcome Write-Back (math → graph), and Data Preservation Hooks (Level 1 → Level 2/3 substrate).
> **Usage:** Architecture documentation. Always valid.

---

**CLAIM-21** ✅ UNCONDITIONAL (UPDATED v3)
> **Statement (v3.2 updated):** GAE v5.0 is fully implemented with March 15 bug fix. The public API includes: ProfileScorer (L2 scoring, update with gt_action_index for dual push/pull), OracleProvider (ground truth), run_evaluation() (scenario evaluation), compute_judgment() (decision explanation), run_ablation() (factor importance). Write-back Hooks 1/2/3 (DecisionRecord, OutcomeRecord, ProfileSnapshot) are active as v5.0 write obligations. 251 tests. Apache 2.0. Published on GitHub.
> **Bug fix note (March 15):** ProfileScorer.update() correct=False branch previously pushed ALL action centroids away from f (including ground truth). Fixed: push predicted away, pull GT toward. 246→251 tests. Validated by SHIFT-2: learning lift -9%→+2.7%.
> **Hook write obligation note:** Hook 1 (DecisionRecord) must be active from v5.0 day 1. Without it, GATE-R cannot run retroactively — every day without Hook 1 active is permanently lost routing accuracy data. Hook 2 (OutcomeRecord) is required for the Loop 2 audit trail and composite accuracy claims. Hook 3 (ProfileSnapshot every 50 decisions) is required for TD-033 checkpoint/rollback and is the Level 2/3 substrate.
> **What you CAN say:** "GAE v5.0 ships a complete scoring, learning, evaluation, judgment, and ablation pipeline, with write-back hooks for routing audit, outcome audit, and centroid checkpointing. 243 tests. Open source."
> **What you CANNOT say:** "Cross-graph attention is implemented." Level 2/3 are designed, not built. Version targets: v7.0 and v8.0.

---

### 1.5 Realistic Accuracy Claims — 50-Seed Validated (NEW v2)

> **Context for all §1.5 claims:** These numbers come from math_synopsis_v7, validated with 50 independent random seeds across realistic SOC factor distributions. These are the **honest product claims** — use these when someone asks "how accurate is the system in practice?"

---

**CLAIM-22** ✅ UNCONDITIONAL
> **Statement:** The system achieves 71.7% [71.4%, 71.9%] static accuracy on realistic SOC alert distributions.
> **Condition (precision only):** *Combined realistic distributions, 50 seeds, before learning from verified outcomes. This is the initial deployment accuracy.*
> **Evidence:** math_synopsis_v7 (50-seed validation)
> **Usage:** The honest starting-point claim. "Day 1 realistic accuracy: 71.7%."
> **What you CANNOT say:** This is below most SOAR baselines — but that is the wrong comparison. This system starts at 71.7% and improves with every verified decision. SOAR rule-based systems don't improve at all.

---

**CLAIM-23** ✅ UNCONDITIONAL
> **Statement:** After 1,000 verified decisions, the system achieves 78.9% [78.1%, 79.6%] accuracy on the credential_access category.
> **Condition (precision only):** *Credential_access category; combined realistic distributions; 50 seeds.*
> **Evidence:** math_synopsis_v7
> **Usage:** The compounding story claim. "71.7% on day 1. 78.9% after 1,000 decisions. The system gets better." State the condition if challenged.

---

**CLAIM-24** ✅ UNCONDITIONAL
> **Statement:** At the ≥0.90 confidence threshold, the system achieves 90.7% [90.1%, 91.2%] accuracy on auto-approved decisions.
> **Condition (precision only):** *Realistic distributions; 50 seeds; auto-approve applied to suppress action at global ≥0.90 threshold.*
> **Evidence:** math_synopsis_v7
> **Usage:** "When the system is confident enough to act autonomously, it is right 9 times out of 10."

---

**CLAIM-25** ⚠️ CONDITIONAL
> **Statement:** 11.5% ± 0.70% of alerts reach the ≥0.90 confidence threshold for autonomous action.
> **Condition:** *Global ≥0.90 threshold; realistic distributions; 50 seeds. Coverage increases with per-category thresholds — see v5.5-R1.*
> **Evidence:** math_synopsis_v7
> **v3.2 update:** DISC-1 (March 15) showed frozen scorer with composite discriminant achieves 70.4% coverage at 85% precision and 33.0% at 90% precision. The 11.5% number is from the old confidence-only gate and is superseded by composite gating.
> **Promotion gate:** v5.5-R1: composite discriminant validated in shadow mode on real alerts.

---

**CLAIM-26** ✅ UNCONDITIONAL
> **Statement:** The system's 50-seed validated realistic accuracy (71.7% static, 78.9% learning) is deliberately disclosed alongside the synthetic experimental accuracy (97.89%, 98.2%). These are two different measurements that answer two different questions.
> **Usage:** Trust and credibility argument. "We show both numbers because they measure different things. The synthetic number validates the scoring mechanism. The realistic number is the honest product claim."
> **Why unconditional:** This is a statement about what we disclose, not a performance number. Always valid.

---

### 1.6 Open-Source Credibility Claims (NEW v2)

> **Context:** These claims are about the GAE library's open-source position. All are unconditional — they are statements about what exists and what we've published.

---

**CLAIM-27** ✅ UNCONDITIONAL
> **Statement:** The mathematical foundation for GAE is published and peer-reviewable. The scoring equations, 28 experiments, and 88+ paper figures are publicly available at github.com/ArindamBanerji/cross-graph-experiments. A companion production architecture paper [Banerji, 2026c] validates adversarial robustness, poisoning resilience, and the μ/σ separation across 10 additional experiments (29 total in companion, 28 in primary catalog).
> **Usage:** Trust argument. "You don't have to take our word for it. The math is published."

---

**CLAIM-28** ✅ UNCONDITIONAL
> **Statement:** GAE is Apache 2.0 licensed. It can be used in commercial products, modified, and redistributed without royalty obligations.
> **Usage:** Enterprise procurement evaluation. "Zero licensing risk for your organization."

---

**CLAIM-29** ✅ UNCONDITIONAL
> **Statement:** GAE has zero external runtime dependencies. Only NumPy is required. This is intentional: 24 multiply-adds per scoring operation does not require PyTorch.
> **Usage:** Enterprise deployment. "Installs in 30 seconds. Runs anywhere NumPy runs."

---

**CLAIM-30** ⚠️ CONDITIONAL
> **Statement:** GAE is available as an installable Python library at version 0.5.0, with 251 tests and a complete user guide.
> **Condition:** *Currently pip install -e . from GitHub. PyPI release is a v5.5 deliverable.*
> **Usage:** Engineering evaluators. Will become unconditional after PyPI publish.
> **Promotion gate:** v5.5: `pip install graph-attention-engine` succeeds from PyPI.

---

### 1.7 Operational Consistency Claims (NEW v3)

> **Context:** These claims require no experiments and no conditions. They are true by architecture at v5.0 and remain true in all future versions unless the architecture fundamentally changes. They are among the strongest claims available for CISO and ICP-trigger conversations because they address the specific failure mode that drives purchase decisions: inconsistency across analysts.

---

**CLAIM-31** ✅ UNCONDITIONAL
> **Statement:** Every analyst on your team gets the same starting recommendation from the same reasoning every time. Given identical factor vectors and current profile centroids, the system always produces the same action probability distribution and the same recommendation — regardless of which analyst is reviewing, what time it is, or how fatigued the team is.
> **Why unconditional:** This is a deterministic architectural property of L2 centroid scoring. It requires no experiments to validate, no conditions to state, and no real data to demonstrate. It was true at v4.5, is true at v5.0, and will remain true at all future versions.
> **Audience:** CISO demo (ICP trigger: "we had three analysts handle the same alert type three different ways last month"), sales outreach, investor materials. This is the single claim that most directly addresses the consistency multiplication argument from compounding_intelligence_v6.
> **What you CAN say:** "Consistency multiplication: every analyst starts from the same recommendation based on the same reasoning. The system doesn't have a bad day. It doesn't treat Tuesday afternoon differently from Monday morning."
> **What you CANNOT say:** "The system is more accurate than your analysts." Accuracy comparison requires real deployment data (FUTURE-08, FUTURE-11). CLAIM-31 is about consistency, not accuracy level.

### 1.8 Calibration Science Claims (NEW v3.2 — March 15, 2026)

> **Context:** These claims derive from the PROD-4b/SHIFT-2/DISC-1 experimental series (March 14-15). They establish the frozen scorer baseline and the composite discriminant as the auto-approve mechanism.

---

**CLAIM-32** ✅ UNCONDITIONAL
> **Statement:** The frozen expert-prior scorer (μ₀, no learning) achieves 80.4% accuracy and 92.9% coverage at the 85% precision gate on synthetic data with zero oracle noise. At 10% noise: 72.5% accuracy, 62.6% coverage.
> **Evidence:** SHIFT-2 (March 15, 50 seeds, η_neg=0.05, τ=0.1)
> **Usage:** Baseline product claim. "The system is accurate from day one using expert-configured profiles."
> **Why unconditional:** Frozen scorer has no learning dynamics to caveat.

---

**CLAIM-33** ⚠️ CONDITIONAL
> **Statement:** A composite discriminant using 13 scorer + context features achieves 70.4% coverage at 85% precision on synthetic data with the frozen scorer — a +7.8pp lift over confidence-only gating (62.6%).
> **Condition:** *Centroidal synthetic data; frozen scorer; logistic regression fitted with 5-fold CV. rolling_accuracy is the strongest orthogonal signal (coefficient=5.06, correlation with confidence=0.09).*
> **Evidence:** DISC-1 (March 15, 50 seeds)
> **Promotion gate:** Shadow mode validation on real alerts.

---

**CLAIM-34** ✅ UNCONDITIONAL
> **Statement:** ProfileScorer.update() with the corrected dual push/pull rule (gt_action_index) produces positive learning lift when prior mismatch exists: +2.7% accuracy at noise=0/δ=0.10, +1.5% at noise=0.10/δ=0.10. Learning works when there is signal to learn from.
> **Evidence:** SHIFT-2 post-fix (March 15, 50 seeds)
> **What you CANNOT say:** "Learning always helps." At δ=0 (no mismatch), learning is slightly negative (-1.4%) because the expert prior is already near-optimal for the synthetic generator.

---

**CLAIM-35** ✅ UNCONDITIONAL
> **Statement:** η_neg=1.0 (20:1 asymmetric learning rate) produces catastrophic miscalibration: ECE=0.490, 40% accuracy at P≥0.90 (65.7% coverage of junk predictions). η_neg=0.05 is the only validated production setting.
> **Evidence:** PROD-4b (March 14, 20 seeds per condition)
> **Usage:** Defending the symmetric learning rate design. "We tested aggressive asymmetry. It destroys the system."

---

**CLAIM-36** ✅ UNCONDITIONAL
> **Statement:** The ProfileScorer.update() bug (correct=False pushing ALL centroids, including ground truth) was present from initial implementation through March 15, 2026. It caused learning to degrade performance at every tested condition (SHIFT-2 pre-fix: -9% to -17% accuracy lift). The fix (dual push/pull with gt_action_index) reversed the degradation (post-fix: +2.7% lift).
> **Evidence:** SHIFT-1 (pre-fix), SHIFT-2 pre/post comparison
> **Usage:** Transparency about bugs found and fixed. Builds trust with technical evaluators.

---

**CLAIM-37** ⚠️ CONDITIONAL
> **Statement:** IKS v2 (Institutional Knowledge Score based on discriminant input quality, not centroid drift) shows a trajectory from 43 to 82 over 1000 decisions, driven by graph richness, decision maturity, and trust coverage accumulation.
> **Condition:** *Synthetic simulation with proxy graph enrichment signals. Production IKS v2 trajectory depends on real graph enrichment rates.*
> **Evidence:** DISC-1 Part B (March 15)
> **What you CANNOT say:** "IKS measures how smart the system is." IKS v2 measures the quality of the discriminant's inputs — a necessary but not sufficient condition for decision quality.

---

### 2.1 Promoting Current Conditional Claims

| Claim | Current Condition | Promotion Gate | Promoted Statement | Version |
|---|---|---|---|---|
| CLAIM-01 (97.89%) | Synthetic, GT profiles, assumes correct routing | GATE-R | "97.89% scoring accuracy (synthetic centroidal). Composite system accuracy = [routing%] × 97.89% = [X%]" | v5.5 |
| CLAIM-02 (98.2%) | Synthetic, warm-start | GATE-R + FX-1-PROXY-REAL | Add realistic learning trajectory data alongside | v6.0 |
| CLAIM-04 (ECE 0.036) | Synthetic, τ=0.1, η_neg=0.05 | TD-034: ≥200 real alerts | "ECE [X] at τ=[Y] on real SOC data" | v5.5 deploy gate |
| CLAIM-05 (vs XGBoost) | Synthetic held-out | FX-1-PROXY-REAL | Add real-data comparison note | v6.0 |
| CLAIM-07 (20×10×20) | GT profiles, cold 72.7% | Real multi-domain deployment | "Validated at scale. Cold-start realistic floor: [measured]" | v7.0 |
| CLAIM-15 (GATE-OP δ=+0.0041) | Synthetic, 100%-correct op, acute phase | ✅ GATE-M SATISFIED (Mar 14) | "σ improves accuracy at operative λ, Loop 2 running — GATE-M PASSED. Poisoning resilience: 0.15pp max." | **ready** |
| CLAIM-25 (11.5% coverage) | Global threshold, realistic | v5.5-R1: composite discriminant | "70%+ coverage at ≥85% precision with composite discriminant (frozen scorer, synthetic)" | v5.5 |
| CLAIM-30 (PyPI) | GitHub only | PyPI publish | Remove condition entirely | v5.5 |

---

### 2.2 Future Claims: Unlock Path

| Claim ID | Statement | Required | Gate | Version |
|---|---|---|---|---|
| **FUTURE-01** | "Composite system accuracy: [X%]" (routing × scoring) | GATE-R | GATE-R passes | v5.5 |
| **FUTURE-02** | "Calibrated to real SOC at ECE [X]" | TD-034: ≥200 real alerts | τ recalibration gate | v5.5 deploy |
| **FUTURE-03** ✅ **ACTIVATED** | "σ with Loop 2 at operative λ: 0.15pp max poisoning degradation at 20% poison, AUAC nearly flat (0.9389→0.9374). GATE-M PASSED." | ✅ EXP-S2-REPRO complete (Mar 14) | ✅ GATE-M satisfied | **done** |
| **FUTURE-04** | "INTSUM-quality threat briefing validated end-to-end" | EXP-S5a + EXP-S5b + EXP-S5 | GATE-D | v6.0 |
| **FUTURE-05** | "Ask the Graph answers [X/15] synthesis queries correctly" | EXP-S7 | GATE-D | v5.5/v6.0 |
| **FUTURE-06** | "Synthesis bias improves real analyst decisions by ≥3pp" | EXP-S8 (real op, real scenarios) | GATE-V | v6.0+ |
| **FUTURE-07** | "Temporal compounding confirmed: γ=[X]>1.0, p<0.05" | EXP-G1 | EXP-G1 passes | v6.0 |
| **FUTURE-08** | "Deployed in production: [X%] accuracy over [N] decisions" | Shadow Mode + real SIEM + ≥200 verified | Production deploy | v5.5+ |
| **FUTURE-09** ✅ **ACTIVATED** | "Real SOC factor distributions characterized: KL 1.88–2.58 across 3 factors from 2,430 IOCs. Bimodal threat intel, right-skewed pattern history, high-mean asset criticality." | ✅ FX-1-PROXY-REAL complete (Mar 14) | ✅ complete | **done** |
| **FUTURE-10** | "Fourth feedback loop fully operational — all three gates passed" | GATE-M + GATE-D + GATE-V + TD-033 | All three gates | v6.5 |
| **FUTURE-11** | "L2 beats XGBoost on real SOC alert distributions" | FX-1-PROXY-REAL + real baseline | Real data comparison | v6.0 |
| **FUTURE-12** | "Composite discriminant: 70%+ coverage at ≥85% precision in production" | v5.5-R1: composite gate + shadow mode validation on real alerts | v5.5-R1 accepted in shadow | v5.5 |
| **FUTURE-13** | "System is measurably more accurate than deployment day" | Institutional Knowledge Score live + 90-day deployment | v5.5-R4 | v5.5 |
| **FUTURE-14** | "Shadow mode agreement rate: [X%] with analysts before live deployment" | v5.5-R8: shadow mode, 30-day pilot | First customer | v5.5 |
| **FUTURE-15** | "S2P second domain: same learning trajectory as SOC" | S2P DomainConfig + 10 seed scenarios + basic demo | v6.0-R4 | v6.0 |
| **FUTURE-16** | "pip install graph-attention-engine works — PyPI release" | PyPI publish, CI passing | v5.5 open-source prep | v5.5 |
| **FUTURE-17** | "Routing accuracy measured at [X%]" | GATE-R execution (DecisionRecord Hook 1 writing) | GATE-R | v5.5 |
| **FUTURE-18** | "IKS ≥ 15 after 200 decisions in ≥90% of simulation seeds — κ* calibrated" | PROD-1 (IKS sensitivity analysis, κ sweep across 50 seeds) | PROD-1 passes | v5.5 |
| **FUTURE-19** ✅ **ACTIVATED** | "Shadow mode agreement rate: 71.9% overall [71.1%, 72.7%] — calibration baseline for first customer shadow report" | ✅ PROD-3 complete (March 14, 50 seeds, C=6, A=5) | ✅ PROD-3 completes | **done** |
| **FUTURE-20** | "Category [c] reaches accuracy plateau after [T_plateau] verified decisions at [V] alerts/day — the onboarding calendar" | PROD-5 (category convergence rate) + SOC-SEED-2 (simulation pool with realistic arrival rates) | PROD-5 + SEED-2 completes | v6.0 |

---

### 2.3 Intelligence Layer Gate Outcomes

| GATE-M | GATE-D | GATE-V | What Ships | Claims Available |
|---|---|---|---|---|
| PASS | PASS | PASS | Full intelligence layer (σ active, Loop 4) | FUTURE-03 → FUTURE-10 |
| PASS | PASS | FAIL | Tab 5 + advisory mode (σ display only) | FUTURE-03, FUTURE-04, FUTURE-05 |
| FAIL | PASS | — | Tab 5 display-only, no σ scoring | FUTURE-04, FUTURE-05 (display only) |
| FAIL | FAIL | — | Tab 5 does not ship | None from intelligence layer |

---

## Section 3: Experiment → Claim Mapping

### 3A: Completed Experiments (34)

| Experiment | Claims Enabled | Claims Constrained |
|---|---|---|
| EXP-C1 | CLAIM-01 (97.89%), CLAIM-09 (dot rejected) | CLAIM-01: routing condition |
| EXP-B1 | CLAIM-02 (98.2%), CLAIM-03 (noise) | Both: synthetic condition |
| EXP-A | CLAIM-08 (G falsified) | — |
| EXP-E1 | CLAIM-09 (L2 wins 2/3) | — |
| EXP-E2 | CLAIM-07 (scales 20×10×20) | Conditional: GT profiles |
| V1A | CLAIM-12 (b=2.11) | Constrains CLAIM-13 (γ unknown) |
| V1B | CLAIM-14 (LayerNorm required) | — |
| V2 | CLAIM-10 (clipping required) | — |
| V3A | CLAIM-05 (vs XGBoost), CLAIM-06 (cold-start) | Both: synthetic |
| V3B | CLAIM-04 (ECE=0.036) | Synthetic; τ=0.1 must be stated |
| EXP-S1 | Supports CLAIM-15 (cold-start σ) | Not GATE-OP result directly |
| EXP-S2 | Supports CLAIM-17 (poisoning, cold-start) | Confirmed at operative λ by EXP-S2-REPRO |
| EXP-S3 | CLAIM-18 (Loop 2 firewall 0.0028) | Direct firewall only |
| EXP-S4 | Supports CLAIM-16 (cold-start λ plateau) | Cold-start only |
| EXP-OP2/GATE-OP | CLAIM-15, CLAIM-16, CLAIM-17, CLAIM-11 | All: synthetic, 100%-correct op |
| SYNTH-EXP-0 | Infrastructure — enables S1-S5b | No direct claims |
| math_synopsis_v7 | **CLAIM-22, CLAIM-23, CLAIM-24, CLAIM-25** | Realistic (not centroidal synthetic) |
| PROD-3 | **FUTURE-19 ACTIVATED** (71.9% shadow agreement) | η_neg=1.0 convention — absolute numbers not transferable |
| PROD-4 (original) | None — INVALID (η_neg=1.0 produced catastrophic miscalibration) | Retracted: 0/6 gate was artifact |
| PROD-4b | **CLAIM-35** (η_neg ECE comparison), **CLAIM-04** (per-category ECE) | Resolved η_neg design decision |
| PROD-4 final (η_neg=0.05) | Enables CLAIM-25 promotion | Per-category thresholds: 0.720–0.870 |
| PROD-4 warmup sweep | Diagnostic — coverage flat 200→2000 | Triggered circularity investigation |
| SHIFT-1 | Diagnostic — learning negative all conditions (pre-fix) | Triggered update() bug investigation |
| SHIFT-2 | **CLAIM-34** (learning +2.7% post-fix), **CLAIM-36** (bug validation), **CLAIM-32** (frozen baseline) | Definitive learning validation |
| DISC-1 | **CLAIM-33** (composite 70.4%), **CLAIM-37** (IKS v2) | Composite discriminant architecture |

### 3B: Planned Experiments → Claims Blocked

| Claim Blocked | Blocking Experiment | Why | Priority |
|---|---|---|---|
| FUTURE-01, FUTURE-17 | **GATE-R** ⚠️ execution blocked until v5.5-R6 | No routing measurement without DecisionRecord Hook 1; ~20% alerts misroute at v5.0 (G-L1-1) | **HIGHEST — v5.5** |
| ~~FUTURE-09~~ → **ACTIVATED** | ~~**FX-1-PROXY-REAL**~~ ✅ COMPLETE (Mar 14) | KL 1.88–2.58. Distribution gap quantified. | **done** |
| FUTURE-11 | FX-1-PROXY-REAL complete; still needs **real baseline comparison** | FX1 results available; real labeled data still needed | v6.0 |
| FUTURE-07 | **EXP-G1** | γ not measured; t^γ is projected | v6.0 |
| ~~FUTURE-03~~ → **ACTIVATED** | ~~**EXP-S2-REPRO**~~ ✅ COMPLETE (Mar 14) | GATE-M formally satisfied. 0.15pp max at production λ. | **done** |
| FUTURE-02 | **TD-034** | τ validated on synthetic; needs real alert calibration | v5.5 deploy |
| FUTURE-04 | EXP-S5a + EXP-S5b + EXP-S5 | CISA/NVD → σ not yet tested | v6.0 |
| FUTURE-05 | EXP-S7 | Ask-the-Graph accuracy not yet measured | v5.5 |
| FUTURE-06 | EXP-S8 | Requires real analyst decisions and operator | v6.0+ |
| FUTURE-08 | Shadow Mode + real SIEM | No production deployment | v5.5+ |
| FUTURE-10 | GATE-M + GATE-D + GATE-V + TD-033 | All three gates required | v6.5 |
| FUTURE-12 | v5.5-R1 (composite discriminant + shadow validation) | DISC-1 validated synthetic; production validation needed | v5.5 |
| FUTURE-13 | Institutional Knowledge Score + 90-day | Score not yet built | v5.5 |
| FUTURE-14 | Shadow mode implementation | Shadow mode not yet built | v5.5 |
| FUTURE-15 | S2P DomainConfig | Second domain not yet implemented | v6.0 |
| FUTURE-16 | PyPI publish | Open-source prep not yet done | v5.5 |
| **FUTURE-18** | **PROD-1** (IKS κ sensitivity, 50-seed sweep) | IKS normalization constant κ is a design guess; IKS trajectory is unmeasured | v5.5 |
| ~~**FUTURE-19**~~ → **ACTIVATED** | ~~**PROD-3**~~ ✅ COMPLETE (March 14) | 71.9% overall [71.1%, 72.7%]. Per-category θ values computed. | **done** |
| **FUTURE-20** | **PROD-5** + SOC-SEED-2 | Category convergence timeline requires realistic arrival rates and simulation pool with extended horizon | v6.0 |

---

## Section 4: Non-Claims, Boundaries, and Real Data

### 4.1 Where GAE Does NOT Apply

These are structural boundaries of the approach. Do not claim them, do not imply them, do not suggest they are on the roadmap without a fundamentally different architecture.

| Non-Claim | Why Not in Scope | What Applies Instead |
|---|---|---|
| **Unstructured alert triage without factors** | GAE requires FactorComputers producing bounded [0,1] values. Raw log streams without traversable graph relationships cannot produce a valid factor vector. | LLM triage → FactorComputer hybrid |
| **Zero-shot generalization to new domains** | Each domain requires DomainConfig with expert-configured initial centroids. No transfer from SOC → Procurement without domain expert authoring. | Domain extensibility is real but requires expert configuration |
| **Predicting unknown threat types** | Profile centroids encode known categories. A genuinely novel attack type has no centroid. It will be mis-routed to the closest existing category. | Anomaly detection outside GAE |
| **Legal/audit explainability** | GAE produces factor weights and distances — interpretable but not a legal audit trail or EU AI Act Article 13 explainability framework. | Evidence ledger + F3 (Legal Explainability) are separate requirements |
| **Threat intelligence generation** | The synthesis layer consumes external intelligence. It does not generate it. | CISA KEV, NVD, vendor feeds are the sources |
| **Supervised learning from labeled datasets** | GAE learns from verified operational outcomes, not pre-labeled training sets. It cannot be "trained" in the ML sense. | Initial centroid configuration from domain expertise is the substitute |
| **Cross-domain knowledge transfer without expert curation** | EXP-D1 showed cross-category transfer is marginal (config wins by 2-14pp). Cross-domain is v6.5+. | Each domain has its own centroid tensor |
| **"The system's calibration improves without feedback degradation"** (v3 NEW) | The N3 endogenous loop is an unresolved open issue: calibration error → systematically biased verification selection → centroids learn the bias rather than ground truth. No intervention point is designed. Disclosed in v5.5 EU AI Act Article 9 risk log. Measurement opportunity: v6.0 first customer shadow mode data. | Intervention design is a future research item. Not available as a claim at any version until the feedback loop is characterized and mitigated. |
| **"The system compounds regardless of analyst verification rate"** (v3 NEW) | The minimum verification fraction f_min below which Loop 2 learning degrades has not been characterized. If production SOCs verify fewer than an estimated ~15% of decisions, centroid drift from noise-induced updates may exceed the signal from correct updates, causing Loop 2 to degrade rather than compound. This gates the core product promise. | f_min derivation pending math_synopsis_v7 §14 (analytical) + simulation pool empirical validation. Cannot be stated as a claim before v6.0 first customer characterization. |

### 4.2 Claims NOT Available at v5.0 (NEW v2 — from product requirements gap analysis)

These are things the system could plausibly claim but CANNOT yet because the product surface doesn't exist.

| Non-Claim | Why Unavailable | Required For |
|---|---|---|
| "You can see the system getting smarter" | Chart A metric fixed in v5.6. IKS v2 (DISC-1 validated) replaces centroid-drift IKS. | v5.5-R3 + R4 |
| "Auto-approve 40% of your alerts" | DISC-1 (March 15): frozen scorer + composite discriminant achieves 70.4% coverage at 85% precision on synthetic data. Production claim pending shadow validation. | v5.5-R1 (composite gate) |
| "Here's your weekly threat briefing" | Tab 5 Panel A not yet built | v5.5-R5 |
| "The system agreed with your analysts X% of the time before you went live" | Shadow mode not yet built | v5.5-R8 |
| "See which graph nodes drove this decision" | Factor node provenance (provenance_nodes) not yet surfaced | v5.5-R2 |
| "Second domain (procurement) working the same way" | S2P DomainConfig not yet built | v6.0-R4 |
| ~~**"Correct routing from all alert types"**~~ ✅ **CLOSED (v3.2)** | ~~At v5.0, approximately 20% of alert_type values misroute~~ CORR-1a (March 14) created ALERT_TYPE_CATEGORY_MAP (20 entries). 68% misroute eliminated. GATE-R can now run. | ~~v5.5-R6 + GATE-R~~ **GATE-R only** |

### 4.3 The Two Accuracy Regimes — Full Statement

This distinction must be preserved in all technical communications.

| | Regime 1 (Centroidal Synthetic) | Regime 2 (Realistic) |
|---|---|---|
| **What it measures** | Does the scoring mechanism work? | What does the product do in practice? |
| **Accuracy (static)** | 97.89% (CLAIM-01) | 71.7% (CLAIM-22) |
| **Accuracy (learning)** | 98.2% (CLAIM-02) | 78.9% at 1k decisions (CLAIM-23) |
| **Data** | Centroidal synthetic, GT profiles | Realistic distributions, 50 seeds |
| **Oracle** | GTAlignedOracle (aligns with geometry) | Realistic outcome distribution |
| **Who this matters to** | Technical evaluators, math reviewers | CISOs, buyers, production pilots |
| **External use** | With stated conditions | Without conditions (§1.5 unconditional) |

### 4.4 Real Data Acquisition Roadmap

**F-TIER-0 (Public, Available Now, No Partner Required):**

| Source | Data Type | Experiment Enabled | What It Validates |
|---|---|---|---|
| CISA KEV (JSON) | ~1,100 actively exploited CVEs | EXP-S5a + FX-1-PROXY-REAL | Real threat_intel distributions |
| NVD API | CVSS scores, descriptions | EXP-S5a + FX-1-PROXY-REAL | Severity-based asset_criticality distributions |
| AlienVault OTX | IOC pulses | FX-1-PROXY-REAL | ThreatIntelEnrichment distributions |
| Abuse.ch | Malicious URLs/hashes | FX-1-PROXY-REAL | Threat signal validation |
| MITRE ATT&CK | Technique IDs, tactics | FX-1-PROXY-REAL + alert pool | SituationAnalyzer routing validation |

**FX-1-PROXY-REAL: ✅ COMPLETE (March 14, 2026).** Pulled 2,430 records from CISA KEV + NVD + MITRE ATT&CK. Mapped to SOC factor space. Factor distributions are non-centroidal (KL 1.88–2.58). Real-data calibration of initial centroids motivated. Mahalanobis kernel and multi-prototype extensions motivated by bimodal/skewed structure. Results documented in production paper [Banerji, 2026c] §9.1 and arxiv paper [Banerji, 2026a] §7.

**F-TIER-1 (Partner-Assisted, Anonymized):**
Anonymized alert corpus (≥200 labeled decisions) unlocks FUTURE-01, FUTURE-02, FUTURE-11.

**F-TIER-2 (Full Partner Deployment):**
Live SOC with SIEM integration — not available until v5.5 hosted deployment.

---

## Section 5: Claim Health — Periodic Review Protocol (NEW v2)

> **Purpose:** Claims can become stale. New experiments can qualify previous claims. New product requirements can reveal gaps. This section specifies when to review claims and what triggers a downgrade.

### 5.1 Review Triggers

| Trigger | Action |
|---|---|
| New experiment completes | Review all claims in §3B that were blocked by that experiment. Promote or add as appropriate. |
| New product version ships | Review §4.2 (non-claims due to unavailable product surfaces) — some may now be available. |
| Customer engagement starts | Review §0.1 audience-specific guidance — buyer context changes what to lead with. |
| External challenge received | Locate the challenged claim in §1. If the challenge reveals the condition is unstated, treat as a downgrade until resolved. |
| Experiment fails a gate | Remove or narrow affected claims immediately. Claims never move backward from UNCONDITIONAL to CONDITIONAL. |
| ~~FX-1-PROXY-REAL completes~~ ✅ **RESOLVED (Mar 14)** | Factor distributions are non-centroidal (confirmed): KL 1.88–2.58. Bimodal threat intel (kurtosis -1.1), right-skewed pattern history (skewness 2.8), high-mean asset criticality (0.646 vs 0.50). Qualification added to arxiv papers §7. Real-data calibration of initial centroids is a priority for FX-1 (partner-required). Motivates Mahalanobis kernel and multi-prototype extensions. |

### 5.2 What Constitutes a Downgrade

These situations require immediate claim status downgrade:

- An experiment at a higher λ or different conditions fails to replicate a prior result
- A technical reviewer identifies a methodological issue with the experiment that produced a claim
- A bug is found in the experiment code that affects the result
- A real-world measurement contradicts the synthetic prediction (e.g., real ECE is much worse than 0.036)

**On downgrade:** The claim is either removed from §1 or moved to "Disputed" status. A disputed claim cannot be used externally. The path back is a new, corrected experiment.

### 5.3 The Claims Hierarchy

When multiple claims could be cited for the same point, prefer in this order:

1. Real-data validated (production deployment) — strongest
2. Realistic 50-seed validated (§1.5) — second strongest
3. Synthetic with stated conditions (§1.1) — conditionally usable
4. Future claims (§2.2) — never cite externally

---

## Appendix: Claims Forbidden in External Communications

| Forbidden Claim | Why Forbidden | Gate That Unlocks It |
|---|---|---|
| "97.89% accuracy" (unqualified) | Assumes correct routing; synthetic centroidal only; ~20% misroute at v5.0 (G-L1-1) | GATE-R + v5.5-R6 (FUTURE-01, FUTURE-17) |
| "The system compounds over time" | γ not measured; t^γ is projected | EXP-G1 (FUTURE-07) |
| "Graph attention computation" without qualification | Level 2/3 not implemented; ProfileScorer is centroid-based L2 | CLAIM-21 clarifies what is implemented |
| "Adapts to the threat landscape" | ⚠️ **Partially unblocked (v3.1).** GATE-M passed — σ mechanism validated. But Tab 5 / σ not in production scoring; GATE-D still required for real threat intel → σ pipeline. | GATE-D (FUTURE-04) — GATE-M no longer blocking |
| "INTSUM-quality briefing" | GATE-D not run; EXP-S5a/5b not run | GATE-D (FUTURE-04) |
| "Fourth feedback loop active" | Loop 4 is PROPOSAL; σ not in production scoring | All three gates + TD-033 (FUTURE-10) |
| "Real-world accuracy of X%" | All measurements are synthetic or 50-seed simulated | Production deployment (FUTURE-08) |
| "Beats any ML baseline on real data" | V3A result is synthetic | FUTURE-11 (real data comparison) |
| "Poisoning-resistant" without condition | ⚠️ **Conditionally promotable (v3.1).** EXP-S2-REPRO passed: 0.15pp max at λ=0.5. May now state: "Poisoning-resilient under production conditions (≤0.15pp AUAC degradation at 20% poison, λ=0.5, σ_max clipping active) on centroidal synthetic data." Realistic distribution resilience also confirmed (Arm B). Remains forbidden without the stated conditions. | ✅ EXP-S2-REPRO complete → GATE-M passed |
| "40% auto-approve day-one" | Synthetic frozen scorer shows 62-70% at 85% precision; production claim requires shadow validation | v5.5-R1 + shadow (FUTURE-12) |
| "You can see the system getting smarter" | Chart A shows ≈0.0 (wrong metric) | v5.5-R3 centroid drift fix |
| "pip install graph-attention-engine" | PyPI release is v5.5 target | FUTURE-16 |
| "The system is 97.89% accurate" | No current SOC deployment achieves this; synthetic only; routing gap active | v5.5-R6 + GATE-R + FUTURE-01 |
| **"The system's accuracy compounds regardless of analyst verification quality"** (v3 NEW) | Loop 2 learns from verified outcomes. Systematically biased analyst verification (e.g., analysts always escalate uncertain alerts, or always close false positives quickly) produces systematically biased centroids — the system learns the bias, not ground truth. This failure mode is the N3 endogenous loop. No intervention point designed. GATE-V (EXP-S8) must characterize analyst judgment quality before this claim can be made. | GATE-V (EXP-S8) — analyst judgment quality characterized in real deployment |

---

*Claims Registry v3.2 · March 15, 2026 · Dakshineshwari LLC*
*34 experiments completed. GATE-OP PASSED. GATE-M PASSED. v5.0 TAGGED. 251 GAE tests, 111 SOC tests.*
*Three accuracy regimes: centroidal synthetic (97.89%), realistic 50-seed (71.7%→78.9%), frozen baseline (80.4%, 92.9% coverage).*
*37 claims (CLAIM-01 through CLAIM-37). 20 future claims. FUTURE-03, FUTURE-09, FUTURE-19 ACTIVATED.*
*ProfileScorer.update() bug found and fixed (CLAIM-36). Composite discriminant validated (CLAIM-33: 70.4% coverage).*
*η_neg=0.05 canonical; η_neg=1.0 FORBIDDEN (ECE=0.49). Frozen scorer is cold-start default.*
*Remaining priority: GATE-R (routing fix done, ready to run) → composite gate shadow validation → EXP-G1.*
*"A claim stated without its condition is a false claim. The condition is not a footnote."*
*"We show both numbers because they measure different things. That is not weakness — it is precision."*
