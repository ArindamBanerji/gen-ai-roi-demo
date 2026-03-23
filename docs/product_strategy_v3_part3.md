## Part 10: Version Assessment and ICP

### Version Conversion Summary

| Version | State | Demo Q1-Q5 | CISO Conversion | Kernel Status |
|---|---|---|---|---|
| v5.0 | Technical PoC | 3/5 — Q2 and Q3 unanswerable | Low | L2 only |
| v5.5 | Product v1 | 5/5 | High | L2 only (kernel designed, not shipped) |
| **v6.0** | **Differentiated** | **5/5 + kernel + deployment qualification** | **High + healthcare + competitive moat** | **DiagonalKernel DEFAULT. KernelSelector. 478 GAE + 280 SOC tests.** |
| v6.5 | Production-hardened | 5/5 + cause-aware conservation + gain scheduling | High + enterprise trust | Kernel stable. R score may replace gate. Var(q) gating. |
| v7.0 | Platform | 5/5 + S2P full + multi-tenant + transfer priors | High + lock-in + MSSP channel | ShrinkageKernel research (if ρ>0.8 matters). |

**The v6.0 inflection:** v5.5 made the product demonstrable. v6.0 makes it differentiated. The kernel is the differentiator — no competitor has a distance metric that adapts to the customer's noise profile, validates itself through factorial evidence, and produces a firm-specific noise fingerprint that compounds over time.

---

### The ICP — Expanded for DiagonalKernel

**v2 ICP was implicitly restricted:** The σ≤0.157 learning boundary excluded healthcare, medtech, mixed-tooling environments, and any deployment with heterogeneous noise — roughly 30-50% of the addressable market. DiagonalKernel moves the boundary to σ≤0.25, which brings these segments IN.

**Target firmographic (updated v3):**

- **Size:** 2,000-50,000 employees. Enough alert volume for compounding (V≥30/day sufficient — CLAIM-45), not large enough for CrowdStrike managed detection as default.
- **Industry:** Regulated — financial services, **healthcare (NOW INCLUDED)**, medtech, critical infrastructure, government contractors. Auditability is a compliance requirement. **Healthcare is now the #1 expansion segment, not a restriction.**
- **SOC team:** 5-100 analysts. **Lower bound reduced from 10 to 5** — DiagonalKernel's higher Day 1 accuracy makes the product viable for smaller teams (even without Level 2 A/B, the Tier 1 consistency + learning value is stronger). Teams ≥8 get full Level 2. Teams 3-7 get before/after (V-D4 pending).
- **SIEM maturity:** 1-5 years post-deployment. **Lower bound reduced from 2 to 1** — noisy early-maturity SIEMs (σ=0.15-0.22) are now learnable under DiagonalKernel. Previously these were frozen-only.
- **Noise profile:** Any noise_ratio > 1.0. DiagonalKernel handles heterogeneous noise from Day 1. Healthcare (ratio≈3×) gets the BIGGEST kernel advantage (+9-14pp over L2). **The noisier the environment, the more the product differentiates.**
- **Trigger event:** Had a visible incident in the past 18 months where post-incident review found "inconsistent triage" or "alert was deprioritized incorrectly." OR: failed a compliance audit citing decision inconsistency. OR: **experienced alert fatigue leading to analyst turnover** — the consistency + learning story addresses retention directly.

**The ICP shift in one sentence:** Under DiagonalKernel, our best customer is no longer the clean, well-instrumented SOC that needs us least. It's the noisy, heterogeneous healthcare/medtech SOC that needs us most — because that's where the kernel advantage is largest.

**The anti-ICP (updated):**
- CrowdStrike Falcon Complete customer: problem is coverage, not triage judgment
- **Fewer than 30 alerts/day** (was 500 — lowered to product floor CLAIM-45): insufficient decision volume
- Greenfield SIEM with no operational history: lacks context for centroids or kernel weights
- Academic or research org: auditability isn't a buying criterion
- **σ>0.25 with q̄<0.60:** Extreme noise + weak team. Even DiagonalKernel can't rescue this. Frozen scorer + Tier 1 consistency value only. Roughly ~5-10% of addressable market.

---

### Pricing Model — Two Tiers (updated from design_gap_analysis_v6 G8a)

Annual subscription per SOC team tier. Not per-alert (penalizes alert volume, backwards incentive). Core value story: you are building an asset.

**Tier 1 — Consistency + Frozen Scorer (available to ALL customers Day 1):**
- Every analyst gets the same recommendation from the same reasoning
- Frozen scorer accuracy (kernel-specific Day 1: ~74% healthcare, ~89% FinServ, ~93% clean)
- Auto-approve at ≥85% per-category accuracy (PROD-4)
- Evidence Ledger, compliance export, EU AI Act documentation
- Weekly executive narrative (Tab 5)
- Shadow mode validation
- **Value:** 44 min × V × auto_approve_rate × cost/hr. At V=200, 40% auto-approve: ~$70K/month.

**Tier 2 — Compounding Intelligence (activates when P28 Qualify passes):**
Everything in Tier 1, plus:
- Learning enabled: centroids evolve from verified decisions
- DiagonalKernel: noise-adaptive scoring (firm-specific noise fingerprint)
- IKS trajectory: visible proof of compounding
- Attack chain correlation (v6.0)
- KernelSelector: automatic kernel optimization
- Onboarding calendar with convergence predictions
- **Value:** Tier 1 value + compounding lift. $127/alert fully compounded (includes time savings + accuracy improvement + institutional judgment accumulation).

**Tier 2 activates automatically** when P28 Phase 4 (QUALIFY) passes. The customer pays more only when they get more value. Under DiagonalKernel, ~85-90% of customers qualify for Tier 2 at deployment. The remaining ~10-15% (σ>0.25 or q̄<0.60) get Tier 1 with a "path to Tier 2" remediation plan.

**Pricing tiers:**
- Pilot: <50 analysts, shadow mode + 90-day evaluation, $75K-150K/year (Tier 1 included; Tier 2 activates on qualification)
- Standard: 50-200 analysts, full deployment, $200K-400K/year
- Enterprise: >200 analysts or multi-domain (SOC + S2P), $500K+/year

Include in contract: customer owns their centroid tensor AND kernel weights, can export both, can deploy on alternate infrastructure. This is the "you own the intelligence" commitment — and the kernel weights are a SECOND owned asset that no competitor provides.

---

## Part 11: Success Criteria

### v5.5 Success — ✅ ACHIEVED

A CISO can be given a URL. They click around for 10 minutes. At the end they can answer all of:

1. "Is this getting better over time?" → Yes, IKS increased 18 points since deployment. ✅
2. "How many alerts is it handling automatically?" → 41% at 86% accuracy this month. ✅
3. "Can I explain a specific decision to a regulator?" → Yes: factor breakdown + graph provenance + NL explanation + similar past cases. ✅
4. "What happened this week?" → Weekly briefing: 847 alerts, 347 auto-approved, 12 escalated, 3 required human review. ✅
5. "Can I trust it before going live?" → Shadow mode: 30 days, agreement rate, disagreement review. ✅

---

### v6.0 Success — UPDATED for DiagonalKernel

A paying customer has been in production for 90 days:

1. **"Was the investment worth it?"** → Realized ROI: $127,000 in analyst time saved. 40%+ auto-approve rate. Accuracy improved from 74% at deployment (DiagonalKernel Day 1, healthcare) to 82% today. Frozen Mode ROI for pre-learning period: $70K/month.

2. **"Is it getting smarter?"** → IKS: 47.3. Specific centroids identified: credential_access + Singapore travel pattern now confidently suppresses. **NEW:** Kernel weights show: "device_trust weight dropped from 0.12 to 0.04 (the system learned your device data is noisy). threat_intel weight stable at 1.0 (reliable)." Two compounding signals visible.

3. **"Can we add procurement?"** → S2P copilot demo: same learning engine, same DiagonalKernel framework (+6.8pp on S2P), different domain. d=8 domain-level scores.

4. **"Does it work for our noisy healthcare environment?"** → "Yes — DiagonalKernel handles your noise from Day 1. No remediation required. 4 healthcare personas validated at r=0.990. Your noise ratio is 3.2× — the kernel advantage is +9.6pp over a system that treats all factors equally."

5. **"What about the Stryker attack?"** → Stryker/Handala analysis: six factors computed, pipeline traced, Four Clocks visualization. "A Clock 1-2 system fires an alert that joins a queue. Our system auto-escalates at 97% confidence within minutes — and the kernel weights show it trusted the threat_intel signal over the noisy device_trust signal."

---

### v6.5 Success

Production-hardened. Enterprise trust established.

1. "Is the conservation law protecting us?" → Cause-aware response: "Quality dropped in credential_access last Tuesday. System automatically froze that category's centroids. Recovered in 18 hours. No analyst intervention required."
2. "How does the calendar work?" → Fisher onboarding calendar: "credential_access: 11 decisions remaining. data_exfiltration: 28 remaining. Connect Entra ID: 14% faster across all categories."
3. "Can we see per-analyst performance?" → Per-analyst η: "Alice: agreement 0.91, full learning weight. Bob: agreement 0.64, attenuated weight. Recommendation: Bob needs training on insider_threat."
4. "What about NHI?" → "Same ProfileScorer, new entity type. 82:1 machine:human ratio. Service accounts baselined."

---

### v7.0 Success

Platform claim validated. Multi-domain compounding.

1. "Does adding S2P help our SOC?" → Cross-domain enrichment: vendor with known-malicious IP triggers SOC alert AND procurement flag simultaneously.
2. "Can we onboard faster than our first deployment?" → Transfer priors: new categories start from firm-specific prior (META-4 validated). N_half reduced by ≥15%.
3. "What about the Waze effect?" → Cross-tenant intelligence: "3 other customers saw this attack pattern last week. Your system's cold-start for this threat type was 4× faster because of anonymized shared learning."

---

## Part 12: The Strategic Bet — SHARPENED

This platform succeeds or fails on one claim: **the accumulated graph AND its kernel weights are worth more than the math.**

Every competitor can access capable LLMs and AI reasoning engines. The math in GAE is open source (Apache 2.0, 478 tests, PyPI published). What is NOT replicable:

1. **The evolved centroid tensor.** 10,000 verified decisions from a specific firm's SOC encoded as 144 geometric coordinates (6×4×6, A=4). A competitor starting from zero cannot access this.

2. **The kernel weights.** DiagonalKernel weights (1/σ² per factor) encode THIS firm's noise fingerprint. device_trust at 0.04, threat_intel at 1.0 — that's a healthcare medtech firm with BYOD and legacy systems but clean threat feeds. A financial services firm has different weights. A tech firm has different weights. The weights are as firm-specific as the centroids, and they compound: as σ estimates refine with more data, the weights become more precise.

3. **The correlation research data.** CovarianceEstimator collects the full factor correlation matrix at v6.0. By v7.0, this data informs regime detection, residual analysis, and potentially shrinkage kernel activation. No competitor has this data because no competitor collects it.

4. **The graph itself.** ThreatIndicator nodes, entity relationships, decision trails, campaign links — accumulated over months of operation. The graph IS the institutional memory.

**The competitive moat has three layers:**
- Layer 1 (replicable in months): The math. GAE is open source. Any team can build this.
- Layer 2 (replicable in 6-12 months): The infrastructure. ci-platform, connectors, P28 pipeline, deployment qualification. Hard work but not defensible.
- Layer 3 (NOT replicable): The accumulated graph + evolved centroids + kernel weights + correlation data. This compounds with every decision. A competitor who starts today is 10,000 decisions behind — and that gap WIDENS because the conservation law ensures compounding doesn't collapse.

**DiagonalKernel deepens the moat in a specific way:** It adds a second dimension of firm-specific learning (noise profile) alongside the first (centroid evolution). A competitor copying the code gets L2 performance. They need the customer's specific noise data to initialize DiagonalKernel — and they need 250 verified decisions to confirm the kernel selection. The kernel weights are a SECOND switching cost the customer feels.

**But this bet only wins if the accumulation is visible.**

If customers cannot see the system getting smarter, they don't feel the switching cost, they don't feel the value, and they churn. At v5.5, IKS made centroid compounding visible. At v6.0, kernel weight evolution makes noise adaptation visible. Two compounding signals the CISO can point to in board meetings.

**The through-line for everything built after v5.5:**

> "Is this feature making the compounding more visible, or making the decisions more accurate? Both matter. Visibility first — because without it, accuracy improvement doesn't close contracts. The kernel is the first feature that does BOTH: +13.2pp accuracy AND a visible noise fingerprint the CISO can show to the board."

**And the positioning line that no competitor can honestly say:**

> "After 1,000 decisions, the system knows what YOUR firm has learned about YOUR environment. The centroids encode your judgment. The kernel weights encode your noise. Microsoft knows what Microsoft knows. CrowdStrike knows what its population knows. We know what you know — and we know what to trust and what to discount in your data. That's two kinds of institutional intelligence, and you own both."

**The CGA risk (from claims_registry_v6 §6):**

The strategic bet includes a third compounding pathway: "the graph compounds while centroids wait" (Adjustment C). This is the narrative for the bottom-right quadrant (σ>0.25, q̄<0.60) — customers where centroids are frozen but the graph still enriches. This narrative has NO validated claim. V-CGA-FROZEN (Priority 2, HIGH) is the experiment that validates or kills it. If it fails, the bottom-right quadrant has no path beyond Tier 1 consistency value. This is the highest-risk claim in the product portfolio.

---

*Product Strategy, Requirements & Competitive Gap Analysis v3.0 · March 21, 2026*
*Supersedes: product_strategy_v2.0 (March 9, 2026)*
*DiagonalKernel (1/σ²) is v6.0 default: +13.2pp SOC, +6.8pp S2P, +3.7pp healthcare.*
*Healthcare segment IN. GREEN zone doubles. Frozen segment shrinks from ~30-50% to ~10-15%.*
*5 demo questions: v5.5 = product v1 (✅ shipped), v6.0 = differentiated (kernel + deployment qualification).*
*ICP expanded: healthcare #1 expansion segment. SOC team floor 5 analysts. SIEM maturity floor 1 year.*
*Two-tier pricing: Tier 1 (consistency, all customers), Tier 2 (compounding, ~85-90% qualify under DiagonalKernel).*
*478 GAE + 280 SOC tests (~935 total). 390-cell factorial. ~104 experiments. 58 claims.*
*"The moat is the graph + the kernel weights. After 1,000 decisions, the system knows what you know — and what to trust."*
