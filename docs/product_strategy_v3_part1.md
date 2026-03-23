# Product Strategy, Requirements & Competitive Gap Analysis
## Compounding Intelligence Platform — SOC Copilot

**Version:** 3.0 · March 21, 2026
**Status:** Authoritative. Supersedes product_strategy_v2.0 (March 9, 2026).
**Scope:** GAE math library · SOC copilot · CI platform · S2P second domain · Competitive positioning
**Audience:** Development, product, strategic review, investor preparation

> **Changes v2 → v3 (DiagonalKernel + V-MV-KERNEL factorial + deployment qualification):**
> (1) **DiagonalKernel (1/σ²) integrated throughout.** +13.2pp on heterogeneous SOC data.
>     v6.0 default. Healthcare opens: +3.7pp learning at σ≈0.22. GREEN zone doubles.
>     KernelSelector ships: ratio>1.5→diagonal, rolling 100-window, 250 decisions.
> (2) **Parts 1-4 rewritten** for kernel-aware narrative. Scoring equation updated.
>     Accuracy table updated. Healthcare CISO conversation fixed. Competitive gaps
>     reframed with kernel advantage. CISO demo updated with kernel moment.
> (3) **Part 5 Layer 3 rewritten.** L2 only → pluggable kernels (L2 + DiagonalKernel).
>     478 GAE tests + 280 SOC tests. KernelSelector. CovarianceEstimator. ReferralRules R1-R7.
> (4) **v5.5 requirements marked SHIPPED.** All Tier 1 features delivered. NL templates,
>     IKS, shadow mode, Chart A, category thresholds, Evidence Ledger export all complete.
> (5) **v6.0 requirements updated.** DiagonalKernel, KernelSelector, P28 pipeline with
>     250-decision shadow, deployment qualification with kernel-dependent thresholds.
> (6) **ICP expanded.** Healthcare segment IN (was excluded at σ>0.20). Frozen segment
>     shrinks from ~30-50% to ~10-15%. Two-tier value proposition embedded.
> (7) **Pricing reflects two tiers.** Tier 1 (consistency) and Tier 2 (compounding)
>     with DiagonalKernel expanding Tier 2 to ~85-90% of market.
> (8) **Companion documents updated:** claims_registry_v6, platform_roadmap_v19,
>     multivariate_foundation_design_note_v2, design_gap_analysis_v6.

---

## Part 1: The Product Thesis

### What We Are Actually Building

This is not an AI that answers security questions better. It is a system that develops institutional judgment — the kind that accumulates from experience, gets calibrated against reality, and becomes increasingly difficult to replicate.

Three claims define the product:

**Claim 1 — Self-improving.** Every verified analyst decision reshapes the system's profile centroids. The system's recommendations on day 1,000 are measurably different from day 1 — and the difference is traceable to specific decisions that changed specific centroid values. This happens continuously, automatically, without vendor involvement. Under DiagonalKernel, the distance metric itself improves as per-factor noise estimates refine — a third compounding pathway alongside centroids and graph enrichment.

**Claim 2 — Firm-specific.** The centroid tensor AND its kernel weights are the product. After 1,000 decisions at a given firm, the system's internal geometry reflects that firm's specific operational reality — their risk tolerance, their noise profile, their analyst judgment, their threat landscape. A competitor with the same math cannot replicate this because the geometry comes from the firm's own decisions AND the firm's specific noise structure. The moat is the graph plus the kernel, not the model.

**Claim 3 — Auditable.** Unlike neural weights or fine-tuned model parameters, profile centroids are readable. Every value has a name. Every shift has a traceable cause. Every recommendation has a factor breakdown with kernel weights showing which factors mattered most. When a regulator asks why the system handled a category a particular way, the answer is a six-number vector with a decision trail and the kernel's weighting of each factor — not "the model learned it."

These three claims form a coherent package. Self-improving without auditability is untrustworthy. Firm-specific without self-improving is just configuration. Auditable without firm-specific is just a log file. The combination is what creates the moat.

### Why This Approach Works Technically

The mathematical core:
```
P(a|f,c) = softmax(−d(f, μ[c,a,:]) / τ)

where d is the kernel distance:
  L2 (cold start):       d = ‖f − μ‖²
  DiagonalKernel (v6.0): d = (f−μ)ᵀ · diag(1/σ²) · (f−μ)
```

Profile centroids μ ARE the institutional knowledge. Per-factor noise weights σ ARE the compiled deployment knowledge. Both are human-readable, domain-expert-configurable, and empirically calibrated by operational experience. Validated numbers:

| Metric | Value | Condition |
|---|---|---|
| Zero-learning accuracy | 97.89% | Synthetic centroidal, GT profiles (validates mechanism) |
| With-learning accuracy | 98.2% | Synthetic, warm-start (validates learning) |
| Realistic static accuracy | 71.7% [71.4%, 71.9%] | 50-seed realistic distributions, L2 baseline (DiagonalKernel adds +13.2pp on heterogeneous data — see row below) |
| Realistic at 1,000 decisions | 78.9% [78.1%, 79.6%] | 50-seed (compounding trajectory) |
| **DiagonalKernel advantage** | **+13.2pp SOC, +6.8pp S2P** | **390-cell factorial, heterogeneous noise (v6.0 NEW)** |
| **Healthcare learning** | **+3.7pp at σ≈0.22** | **4 personas, corr(ratio, advantage)=0.990 (v6.0 NEW)** |
| Auto-approve coverage | 40%+ at ≥85% per-category | PROD-4 validated |
| Calibration ECE | 0.036 at τ=0.1 | Synthetic (V3B) |
| Domain scaling | n^2.11, R²=0.9999 | Simulation (V1A) |
| GAE tests | 478 | Apache 2.0, PyPI published. +280 SOC tests (~935 total). |

The math works. The architecture is settled. The kernel question is resolved (390-cell factorial). The gaps are not in the math. They are in making the compounding visible, the decisions explainable to buyers, and the infrastructure production-ready.

---

## Part 2: Three Customer Roles

Every enterprise product has three distinct relationships that must each be satisfied. Failure at any one kills the product at a different stage.

### Role 1 — The Daily User (SOC Analyst)

**What makes them adopt:** The recommendation is right more often than their gut. They can see WHY — including which factors the kernel weighted most heavily. Routine alerts are handled automatically so they focus on hard ones. After 30 days, they feel relief — alert queue is shorter, explanations are ready, feedback is acknowledged.

**What makes them champion the product:** "The system learned that our device_trust data is noisy and stopped relying on it. But it kept learning from threat_intel — and it's getting smarter."

**Current satisfaction: 70%** (was 45% at v2.0 — v5.5 shipped NL templates, IKS, shadow mode, category thresholds)

| Need | Have | Gap |
|---|---|---|
| Correct recommendations | 78.9% at 1,000 decisions (+13.2pp under DiagonalKernel for noisy envs) | Approaching "trust it" threshold |
| Routine alerts handled automatically | 40%+ auto-approve (PROD-4) | ✅ Relief threshold met |
| See why — graph nodes that drove each factor | Factor values + provenance + kernel weights | Source graph nodes visible. Kernel weight adds "device_trust mattered less because it's noisy." |
| Trust built through explanation | Evidence Ledger + NL templates (v5.5 ✅) | ✅ Shipped |
| System learns my environment | IKS score visible (v5.5 ✅) + kernel adapts to noise | ✅ Learning visible. Kernel adds second compounding signal. |

**Remaining gap:** Per-analyst learning visibility. "Did MY feedback specifically change a centroid?" — not yet surfaced. Feeds v6.5 per-analyst η (Adjustment B).

---

### Role 2 — The Buyer (CISO / Security Director)

**What makes them sign the contract:** Clear ROI, demonstration that the system improves over time, ability to explain it to their board in one paragraph, operational proof during the trial period.

**What makes them renew:** Monthly metrics showing improvement. "Your system auto-approved 847 alerts this month at 91% accuracy. That's 28 analyst-hours recovered. The kernel down-weighted device_trust noise and your learning accelerated."

**Current satisfaction: 55%** (was 30% at v2.0 — IKS, shadow mode, Tab 5 weekly narrative shipped)

| Need | Have | Gap |
|---|---|---|
| Proof of self-improvement | IKS score + Tab 5 "What Changed This Week" (v5.5 ✅) | ✅ Shipped |
| ROI quantification | Frozen Mode ROI calculator (v6.0) + full ROI | Frozen mode shows Tier 1 value. Full ROI after learning. |
| Board-ready summary | Tab 5 executive narrative (v5.5 ✅) | ✅ Shipped |
| Accuracy trend over time | Chart A centroid drift (v5.5 ✅) | ✅ Shipped |
| Autonomy claim | 40%+ auto-approve (PROD-4 ✅) | ✅ Sufficient for conversations |
| **Healthcare learning story** | **DiagonalKernel +3.7pp at σ≈0.22 (v6.0 NEW)** | **✅ "Learning from Day 1" — no remediation required** |

**The healthcare CISO conversation — FIXED (was the #1 gap in design_gap_analysis):**

OLD conversation (v2.0):
- Sales: "After 1,000 decisions, the system develops institutional judgment."
- CISO: "Our environment is noisy — medical devices, BYOD, legacy systems."
- Sales: "Your σ is 0.21. Learning would be disabled."
- CISO: "So it doesn't get smarter for us?"
- *(deal dies)*

NEW conversation (v3.0):
- Sales: "After 1,000 decisions, the system develops institutional judgment."
- CISO: "Our environment is noisy — medical devices, BYOD, legacy systems."
- Sales: "Your noise ratio is 3.0×. The kernel handles this — it automatically
  down-weights your noisy device_trust factor and up-weights your reliable
  threat_intel factor. Learning works from Day 1."
- CISO: "What if we connect Defender later?"
- Sales: "That reduces device_trust noise — the kernel gives it more weight,
  and learning accelerates. But you're already learning today."
- *(pilot starts)*

**Remaining gap:** Realized ROI from first deployment. Projected ROI exists (Frozen Mode calculator). Actual measured time savings = CL-ECON-MEASURED (pre-staged, waiting for deployment data).

---

### Role 3 — The Technical Evaluator (SOC Architect / Security Engineering Lead)

**What makes them approve:** The system is not a black box. They can audit every decision. The centroids are readable and correctable. The kernel weights show which factors matter. They're not locked into a vendor's model. Apache 2.0.

**What makes them block:** "We can't explain this to regulators." "We can't correct a wrong decision without touching code."

**Current satisfaction: 75%** (was 65% at v2.0 — Evidence Ledger export, EU AI Act documentation shipped)

| Need | Have | Gap |
|---|---|---|
| Decision auditability | Hash-chained Evidence Ledger, compliance export (v5.5 ✅) | ✅ Shipped |
| Explainability | Factor breakdown + NL templates + kernel weights (v5.5/v6.0 ✅) | ✅ Kernel weights add: "device_trust: weight 0.04 (noisy), threat_intel: weight 1.0 (reliable)" |
| Data residency / local deployment | Docker Compose deployment (v5.5 ✅) | Cloud deployment needed for pilot ease (v6.0) |
| Regulatory compliance | EU AI Act documentation (v5.5 ✅) | Art. 15 robustness now includes DiagonalKernel + KernelSelector |
| **Architecture credibility** | **478 GAE + 280 SOC tests, 390-cell factorial, ~104 experiments** | **Strongest evidence base of any AI SOC product** |
| **Kernel transparency** | **KernelSelector: noise_ratio>1.5→diagonal, 4/4 correct** | **"The system explains WHY it chose this kernel for your deployment"** |

**Remaining gap:** No production deployment reference. First customer pilot provides this.

---

## Part 3: The Competitive Landscape — Four Gaps Reframed

The original gap analysis (v1) used wrong comparison frames. v2 reframed each gap. v3 adds the kernel advantage — which changes the competitive story in all four gaps.

---

### Gap 1: "71.7% Static Accuracy vs Rule-Based Triage" — NOW +13.2pp UNDER DIAGONAL

**The v2 reframe stands:** The right metric is consistency, not accuracy competition against rules. GAE is weakest where rules are strongest (routine known patterns) and strongest where rules are weakest (novel variants, firm-specific context).

**What v3 adds:** Under DiagonalKernel, accuracy on heterogeneous data jumps +13.2pp (SOC) and +6.8pp (S2P). Healthcare Day 1 accuracy improves from ~71% (L2) to ~74% (Diagonal). After 1,000 decisions with DiagonalKernel at healthcare noise levels: ~78% (where L2 would plateau at ~72%).

The accuracy gap against rules narrows significantly for noisy environments — precisely the environments where rules are also noisiest. The segmented accuracy table now looks different:

| Alert Type | L2 Day 1 | Diagonal Day 1 | Diagonal Day 1,000 | Rule-based |
|---|---|---|---|---|
| Known pattern, matches rule | ~80% | ~82% | ~90% | 90-95% |
| Known category, novel variant | ~70% | ~76% | ~83% | 30-50% |
| Novel pattern, no rule | ~65% | ~72% | ~79% | 5-20% |
| Routine suppress (known benign) | ~85% | ~88% | ~93% | 95%+ |

**The gap that narrows most is the consequential one:** novel variants and novel patterns, where DiagonalKernel's noise handling matters most.

**Closure path update:**
- **v5.5:** ✅ Shipped (segmented accuracy, analyst agreement rate).
- **v6.0:** Head-to-head includes DiagonalKernel. P28 Phase 0 PREVIEW shows kernel-specific Day 1 prediction. "For your noise profile under DiagonalKernel: predicted Day 1 accuracy: 89%."

---

### Gap 2: "11.5% Auto-Approve vs SOAR Automation" — NOW 40%+ (SHIPPED)

**The v2 reframe stands:** SOAR handles the deterministic tail. GAE handles the judgment-intensive middle. They are complementary.

**What v3 adds:** PROD-4 shipped. 40%+ coverage at ≥85% per-category accuracy. Category-specific thresholds with cost-weighted risk. ReferralRules R1-R7 (policy-based VETO mechanism) recover ~12 analyst-hours per 100 alerts. Confidence gate for action routing only — rules handle referral routing.

**Status: CLOSED.** The 11.5% → 40%+ gap is resolved. Remaining expansion: 60-70% coverage realistic at year 3-4 as centroids mature + cross-domain enrichment at v7.0.

---

### Gap 3: "No Real-Time Threat Intel vs Security Copilot" — NOW KERNEL-DIFFERENTIATED

**The v2 reframe stands:** Microsoft knows global threat intel. GAE knows what happened in THIS firm's environment. Different intelligence.

**What v3 adds:** The Four Clocks framework (from the advisory session) structures this gap:

**Microsoft operates at Clock 1-2** (State + Event). Security Copilot tells you what's true right now and what happened. It queries Sentinel, summarizes alerts, generates KQL. Very good analyst assistant. But it doesn't learn from your decisions. On day 180, it answers the same way it did on day 1.

**SOC Copilot operates at Clock 3-4** (Decision + Insight). It measures how judgment evolves and what the system discovered that nobody asked about. On day 180, it knows your firm's patterns, your false positive profile, your noise structure (via DiagonalKernel weights), and the cross-domain connections no individual source reveals.

**The kernel adds a new differentiation layer:** "Microsoft tells you what happened. We tell you what we learned. After 1,000 decisions, ask both systems how they got smarter. Only one can answer. And our kernel weights show you WHAT it learned was noisy and WHAT was reliable — that's your firm's noise fingerprint encoded as geometry."

**Honest comparison updated for v6.0:**

| Capability | Security Copilot | SOC Copilot v6.0 |
|---|---|---|
| Global threat intelligence | ✓ Microsoft corpus | CISA KEV + NVD + Pulsedive + accumulated IOC graph |
| Firm-specific IOC memory | ✗ Stateless per query | ✓ ThreatIndicator nodes accumulated since deployment |
| Learns from your decisions | ✗ Same answer day 1 & 180 | ✓ Centroids evolve, kernel weights refine |
| Adapts to your noise profile | ✗ | ✓ DiagonalKernel: device_trust weight 0.04, threat_intel weight 1.0 |
| Customer owns intelligence | ✗ Microsoft only | ✓ Apache 2.0. Centroid tensor + kernel weights exportable. |
| Price | "Free" with E5 | $75K-400K/year — but you own the asset |

**The killer line:** "After 1,000 decisions, your Security Copilot answers differently — because ours gave it institutional memory. And the kernel weights show you exactly which parts of your environment it learned to trust."

---

### Gap 4: "Explainability Requires a Sophisticated Buyer" — NOW KERNEL-ENHANCED

**The v2 reframe stands:** Three-layer explainability (analyst, CISO, auditor). NL templates ship deterministic, auditable explanations without LLM dependency.

**What v3 adds:** DiagonalKernel weights add a fourth explanation dimension: factor reliability.

**Layer 1 — Analyst** (Tab 3): Factor breakdown + provenance + kernel weight per factor.
"device_trust: 0.73, weight: 0.04 (noisy — low influence on scoring).
threat_intel: 0.91, weight: 1.0 (reliable — primary scoring driver)."
The analyst sees not just WHAT the factors are but HOW MUCH each one matters.

**Layer 2 — CISO** (Tab 5): Kernel adds a plain-English narrative:
"The system learned that your device trust data is unreliable (medical devices, BYOD).
It down-weighted this factor to 4% influence while keeping threat intelligence at full
weight. This is why learning works in your environment despite the noise."

**Layer 3 — Auditor** (Evidence Ledger): Kernel metadata in per-decision records.
EU AI Act Art. 15 (Robustness): "DiagonalKernel with noise_ratio=3.2×. KernelSelector
confirmed at 250 decisions. Factor weights: [0.04, 1.0, 0.25, 0.08, 0.50, 0.33]."

**Closure path update:**
- **v5.5:** ✅ Shipped (NL templates, factor provenance, Evidence Ledger export).
- **v6.0:** Kernel weights in Layer 1-3. Adjustment G (epistemic state indicator) adds kernel_type, noise_ratio to per-decision metadata.

---

## Part 4: The Minimum Viable CISO Demo

**The test:** A skeptical CISO — one who has seen 40 vendor demos this year, knows "AI" is a marketing word, and whose last security vendor over-promised — sits across from you for 20 minutes. They ask five questions.

---

**Q1: "Does it actually work?" (minutes 1-5)**

What they want: a live alert, a recommendation, an explanation they can understand, a confidence value that feels honest.

| v5.5 (shipped) | v6.0 (next) |
|---|---|
| Plain English: "Singapore login, critical asset, no prior travel" | Same + "device_trust weighted at 4% (noisy), threat_intel at 100%" |
| Confidence: 89% + "aligns with 74% of similar prior decisions" | Same + kernel-specific confidence calibration |
| Factor provenance: graph nodes shown | Same + per-factor kernel weight shown |

**Closes with:** NL template engine (v5.5 ✅). Kernel weights (v6.0).

---

**Q2: "Show me it's getting smarter" (minutes 6-12)**

This question HAS an answer now at v5.5. At v6.0 it gets a second dimension.

| v5.5 (shipped) | v6.0 (next) |
|---|---|
| IKS: 47/100 (up 3.2 this week) | Same + "kernel weights refined: device_trust weight dropped from 0.12 to 0.04 as noise measured" |
| Chart A: centroid drift per decision | Same + kernel weight evolution chart |
| "The 5 decisions that moved it most" | Same + "the kernel now treats 4/6 factors as reliable (was 3/6 at deployment)" |

**Closes with:** IKS (v5.5 ✅). Kernel weight evolution (v6.0). **The kernel adds a second compounding signal the CISO can see: "Not only are the centroids getting smarter — the distance metric itself is getting smarter."**

---

**Q3: "What does it cost me and what do I get back?" (minutes 13-16)**

| v5.5 (shipped) | v6.0 (next) |
|---|---|
| Shadow mode: "your analysts agreed with us 74% over 30 days" | Shadow + Frozen Mode ROI: "$70K/month even before learning activates" |
| Realized numbers from shadow period | DiagonalKernel: "Learning activated on Day 1. No remediation required." |

**The kernel changes this conversation for healthcare/noisy customers.** Previously: "You need to remediate first (6 weeks) before learning starts." Now: "Learning starts immediately. Remediation makes it faster, not possible."

---

**Q4: "What if it's wrong?" (minutes 16-18)**

| v5.5 (shipped) | v6.0 (next) |
|---|---|
| Shadow mode: 30-day before live | 250-decision shadow (data-driven, not calendar) |
| Checkpoint/rollback | Same + AMBER auto-pause (conservation law) |
| Conservative bias settings | Same + KernelSelector explains: "ratio>1.5→diagonal selected, 4/4 correct in validation" |
| Learning freeze control | Same + per-factor control via kernel weights: "The system already ignores your noisy factors" |

---

**Q5: "Why not just use Security Copilot or CrowdStrike?" (minutes 18-20)**

The answer no competitor can give them:

> "Microsoft Security Copilot knows what Microsoft knows. After 1,000 decisions at your firm, this system knows what YOUR firm has learned about YOUR environment. Those are different kinds of intelligence.
>
> CrowdStrike Falcon learns from threats across all their customers. Powerful — but it reflects the average threat landscape, not your specific environment.
>
> Here's what neither of them can do: learn that YOUR device_trust data is noisy and automatically down-weight it while keeping your threat_intel at full weight. That's a firm-specific noise fingerprint. It compounds. After a year, the kernel weights encode your entire operational reality.
>
> The centroids are readable. The kernel weights are readable. You own both. When you stop paying us, they don't disappear."

**Demo conversion summary (updated):**

| Question | v5.0 | v5.5 | v6.0 |
|---|---|---|---|
| Q1: Does it work? | Partial | ✓ NL + similar cases | ✓ + kernel weights |
| Q2: Getting smarter? | ✗ | ✓ IKS | ✓ + kernel evolution |
| Q3: What's the ROI? | Projected | ✓ Shadow realized | ✓ + Frozen Mode ROI + Day 1 learning |
| Q4: What if wrong? | Invisible | ✓ Shadow + checkpoint | ✓ + AMBER auto-pause + KernelSelector |
| Q5: Why not SC? | Argument only | ✓ + threat graph | ✓ + kernel differentiation |

**v5.5 is the product. v6.0 is the differentiation. The kernel is the competitive moat others cannot replicate.**
