# Build vs. Buy Brief
## Why Building This Internally Takes 18 Months — and Still Doesn't Get You There
**Version:** 1.0 · March 2026  
**Audience:** CISO / VP Engineering evaluating build-vs-buy  
**Format:** One-page leave-behind (expand to full brief as needed)

---

## The Question We Hear

*"Our team is good. We have Sentinel data, we have Python engineers, we have LLM access. Why can't we build this?"*

You can build the inference layer. You can build the dashboard. You cannot easily build what makes this valuable: the **compounding mechanism** — the system that gets smarter from your decisions and accumulates institutional knowledge that is irreplaceable.

Here is what your team would actually be building.

---

## What "Building This" Actually Requires

### Layer 1: The Math (3–6 months)

The core scoring engine is a ProfileScorer with kernel-based distance learning. This is not a call to GPT-4. It is a custom Bayesian update loop with:

- **Profile centroids** μ ∈ ℝ^(C×A×d) — institutional knowledge encoded as 144 calibrated values
- **DiagonalKernel** weighting W = diag(1/σ²) — per-factor noise estimation that adapts the distance metric to your environment
- **Asymmetric learning rate** η_confirm=0.05 / η_override=0.01 — prevents 13–27pp accuracy degradation from analyst override noise (a failure mode we discovered after running 24 personas through a stress test)
- **Conservation law** α(t)·q(t)·V(t) ≥ θ_min — prevents silent centroid corruption from low-quality override signals
- **KernelSelector** — rolling 100-decision window that empirically validates which kernel performs best on your specific data

Getting the math right took us: ~104 experiments, 390-cell factorial validation, 9 domain personas, and multiple iterations of a P0 bug that would have silently corrupted model state in production (see asymmetric η above).

**Your team's estimate:** 3–6 months for a working prototype. Add 3 months to find the P0-class bugs.

### Layer 2: The Data Pipeline (2–3 months)

- SIEM connectors (Splunk, Sentinel, bidirectional write-back) — not just read, but enrichment write-back
- PII redaction at ingestion (5 regex classes, 3 strategies)
- Entity resolution (3-pass deterministic pipeline — "john.smith" in AD = "jsmith" in VPN)
- SAML 2.0 SSO integration
- Neo4j graph schema: AlertNode, DecisionRecord, OutcomeRecord, ProfileSnapshot, EvidenceLedger node types with hash-chained tamper evidence

### Layer 3: Safety and Compliance (2–4 months)

- AMBER auto-pause: learning freezes when conservation law signals quality degradation
- Checkpoint/rollback: ProfileSnapshot every 50 decisions, rollback to any prior state
- EU AI Act Art. 9 risk log (mandatory before August 2, 2026 enforcement)
- EU AI Act Art. 14 human oversight: referral rules R1-R7 (not just a confidence gate — the confidence gate alone gives 14% precision for human escalation)
- Evidence Ledger: hash-chained audit trail exportable as PDF/CSV for compliance audits
- TD-033 checkpoint: 35% of centroids damaged by bad overrides never recover without a rollback mechanism (EXP-OP2 finding)

### Layer 4: The Deployment Qualification Pipeline (1–2 months)

Before you can trust the system in production, you need:
- 250-decision shadow mode with dual-kernel comparison
- Per-factor σ measurement and noise ratio computation
- KernelSelector lock at 250 decisions
- GREEN/AMBER/RED classification with kernel-dependent thresholds (not a single threshold — kernel matters)
- τ recalibration on your specific alert distribution

This is the part that separates a "working prototype" from a "trustworthy production system."

---

## The Validation Evidence Gap

We have:
- **478 GAE tests** in the open-source library (Apache 2.0, inspectable)
- **280 SOC tests** covering every endpoint, every learning path, every edge case
- **73 ci-platform tests** covering the deployment pipeline
- **~104 experiments** including 390-cell factorial validation, 24 domain personas, 4 healthcare-specific noise profiles
- **Multi-seed confidence intervals** on every key claim (50-seed minimum for critical experiments)

Your team starting from scratch would need 12–18 months to accumulate equivalent validation evidence. And some of what we found (the asymmetric η bug, the R4 referral precision failure, the conservation law starvation pattern) only surfaces after hundreds of controlled experiments.

---

## What You Actually Get on Day 1 vs. Month 18

| | Build (Month 1) | Build (Month 18) | Buy (Day 1) |
|---|---|---|---|
| Triage recommendations | Maybe | Yes | Yes |
| Factor breakdown / provenance | No | Maybe | Yes |
| Learning from decisions | No | Yes (prototype) | Yes (validated) |
| EU AI Act compliance artefacts | No | Maybe | Yes (Art. 9/12/14/15) |
| Deployment qualification | No | Maybe | Yes (P28 pipeline) |
| Validated safety mechanisms | No | No | Yes (104 experiments) |
| Your firm's institutional knowledge | Day 1 graph | Month 18 graph | Day 30 (shadow mode) |
| Engineering cost | $0 + team time | $800K–$1.2M (4 engineers × 18 months) | Contract value |

---

## The Irreplicability Argument

Even if your team builds it perfectly, they start with an empty centroid tensor. Your competitor — if they copy the open-source code — also starts with an empty tensor.

The GAE library is Apache 2.0. Anyone can run it. The value is not the code.

**After 1,000 decisions, your deployment has geometry that reflects your firm's specific:**
- Risk tolerance (encoded in centroid positions)
- Noise profile (encoded in kernel weights W)
- Analyst judgment patterns (encoded in centroid drift direction)
- Environmental reality (encoded in DiagonalKernel per-factor weights)

A competitor with the same code, on a different firm's data, produces different centroids. Yours are yours. They cannot be transferred, replicated, or reverse-engineered from the recommendation outputs alone.

---

## The Cost of Delay

EU AI Act enforcement begins **August 2, 2026** — 4.5 months away. High-risk AI systems (which include automated triage systems affecting natural persons) require:
- Art. 9 risk management documentation
- Art. 14 human oversight mechanisms
- Art. 15 accuracy and robustness logging

An internal build starting today cannot achieve documented compliance by August 2. Our product ships with these artefacts pre-built and auditable.

**Fines:** Up to €35M or 7% of global annual turnover for non-compliance with high-risk AI Act obligations.

---

## Our Offer

- 30-day shadow mode pilot: zero-risk evaluation. Your analysts work normally. We measure agreement rate.
- No configuration required: P28 pipeline runs in ~30 minutes.
- If agreement rate < 75% at Day 30: pilot extension at no charge.
- Open-source core: the GAE library is Apache 2.0. Your engineers can inspect every line of the scoring math.

**The question is not whether you can build this. The question is what 18 months of your engineering team's time is worth compared to having it working in 30 days.**

---

*Build vs. Buy Brief v1.0 · Compounding Intelligence Platform · March 2026*  
*All experiment results available on request. Open-source library: github.com/ArindamBanerji/graph-attention-engine*
