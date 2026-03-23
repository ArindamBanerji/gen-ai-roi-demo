# Microsoft Security Copilot vs. SOC Copilot
## A Four Clocks Analysis
**Version:** 1.0 · March 2026  
**Audience:** CISO / VP Security evaluating both products  
**Framing:** Complementary, not competitive — different clocks, different value

---

## The One-Line Answer

**Microsoft Security Copilot operates at Clock 1-2 (State + Event). SOC Copilot operates at Clock 3-4 (Decision + Insight). They measure fundamentally different things. You need both.**

The question is not "which AI for my SOC?" The question is "what kind of intelligence am I still missing after I deploy Microsoft?"

---

## The Four Clocks Framework

Security intelligence operates on four distinct time scales. Most tools operate on one or two. Few operate on all four.

| Clock | Measures | Time Scale | Question Answered |
|---|---|---|---|
| **Clock 1: State** | What is true right now | Real-time to minutes | "Is this asset vulnerable? Is this IP malicious?" |
| **Clock 2: Event** | What just happened | Minutes to hours | "What did this alert mean? What technique was used?" |
| **Clock 3: Decision** | How judgment evolves | Days to months | "Is our team getting better or worse at this category? Are we making the same mistakes?" |
| **Clock 4: Insight** | What the system discovered | Months to years | "What cross-domain patterns emerged that nobody noticed? What's our firm's unique threat profile?" |

---

## Where Microsoft Operates

Microsoft Security Copilot is outstanding at Clocks 1-2. It is the best-in-class answer to:

- "Explain this alert in plain language" (Clock 2)
- "Generate the KQL query for this investigation" (Clock 2)
- "What CVEs apply to this asset?" (Clock 1)
- "Summarise this incident for a stakeholder brief" (Clock 2)
- "What does MITRE ATT&CK say about T1078?" (Clock 1)

This is genuine value. Microsoft has the global threat corpus, the Sentinel integration depth, and the LLM capability to make Clock 1-2 queries faster and more accessible than any team can manage manually.

**What Microsoft cannot tell you:**

> "At your firm, after 847 decisions, how has the system's understanding of lateral_movement changed? Which factors does it now weight most heavily? Is that shift consistent with your analysts' recent feedback?"

Microsoft's Security Copilot answers the same way on Day 180 as it did on Day 1. It has global intelligence. It does not have *your* intelligence.

---

## Where SOC Copilot Operates

SOC Copilot is purpose-built for Clocks 3-4. It measures:

**Clock 3 — Decision Quality:**
- Does the system's triage judgment improve over time? (IKS score: 0–100, climbing with every verified decision)
- Which categories has the team mastered? Which are still uncertain?
- Where do night-shift analysts disagree with day-shift? (conservation law per-shift breakdown)
- Are override quality signals degrading? (AMBER auto-pause: conservation law fires before centroids corrupt)

**Clock 4 — Emergent Insight:**
- What cross-category patterns has the graph accumulated that no individual alert would reveal?
- What is this firm's specific noise profile — which factors are reliable sensors here, which are noisy? (DiagonalKernel weights = the firm's noise fingerprint as geometry)
- What does the centroid drift direction tell us about how this firm's threat landscape is evolving?

---

## The Kernel Difference

This is the technical moat that makes the Clock 3-4 claim concrete.

After 250 decisions, SOC Copilot locks a DiagonalKernel with weights W = diag(1/σ²) — where σ is the per-factor noise measured from **your** alert stream.

What this looks like in practice:

```
Your deployment's kernel weights after 250 decisions:

Factor                  σ       Weight    Meaning
travel_match           0.18    0.31×     "Your travel data is noisy — gaps in HR integration"
asset_criticality      0.06    2.78×     "Your CMDB is well-maintained — high trust"
threat_intel_enrichment 0.09   1.23×     "Reliable signal"
time_anomaly           0.07    2.04×     "Strong signal here"
pattern_history        0.21    0.23×     "Limited baseline — improves over time"
device_trust           0.08    1.56×     "Good MDM coverage"
```

These weights are **your firm's noise fingerprint**. A competitor using the same open-source GAE library on a different firm's data will produce different kernel weights. Yours cannot be reverse-engineered from recommendation outputs. They are the compiled product of your environment's specific data quality profile.

Microsoft Security Copilot applies global priors. SOC Copilot applies **your** priors.

---

## Side-by-Side Comparison

| Dimension | Microsoft Security Copilot | SOC Copilot |
|---|---|---|
| **Primary value** | Analyst productivity — faster investigation | Analyst quality — better decisions over time |
| **Intelligence type** | Global threat corpus (Microsoft's data) | Firm-specific institutional knowledge (your data) |
| **Clock** | 1-2 (State + Event) | 3-4 (Decision + Insight) |
| **Learns from your decisions** | No — same Day 180 as Day 1 | Yes — IKS climbs with every verified decision |
| **Knows your noise profile** | No — global priors | Yes — DiagonalKernel, σ per factor |
| **Explainability** | LLM prose (probabilistic) | Six-number factor vector + kernel weight (deterministic, auditable) |
| **EU AI Act Art. 14** | Human-in-the-loop varies | Referral rules R1-R7 (auditable VETO, not confidence gate) |
| **Audit trail** | Sentinel logs | Hash-chained Evidence Ledger (every decision traceable) |
| **Owns your intelligence** | No — Microsoft hosts | Yes — centroid tensor is exportable, Apache 2.0 |
| **Cold start** | Immediate (global model) | Day 30 (shadow mode, kernel calibration) |
| **After 1,000 decisions** | Same as Day 1 | 78.9% accuracy, firm-specific geometry |

---

## The Question That Only One System Can Answer

After 1,000 decisions at your firm, ask both systems:

> *"How did you get smarter over the last 90 days? What specifically changed in how you handle insider_threat alerts? And which factors do you now trust most in this environment?"*

**Microsoft Security Copilot:** Cannot answer. It has no memory of your firm's decisions.

**SOC Copilot:** 
```
"insider_threat centroid drift: +0.12 on threat_intel_enrichment (analysts 
consistently validated this as the strongest signal). -0.08 on time_anomaly 
(your environment has high weekend access by legitimate remote workers — 
time signals are less reliable here than in the baseline).

Kernel weight for device_trust increased to 1.56× after MDM coverage 
expanded in Month 2 — your data quality improved and the system noticed.

IKS: 47.3 (was 12 at Day 30). The graph now contains 1,247 decision nodes, 
3,891 entity relationships, and 89 cross-category connection patterns."
```

That answer is yours. It cannot be purchased from Microsoft. It cannot be replicated by a competitor. It is the accumulated product of your analysts' judgment, your environment's data, and 1,000 verified decisions.

---

## Deployment Architecture: Complementary, Not Competing

The right architecture for a mature SOC uses both:

```
Alert arrives
    │
    ▼
Microsoft Security Copilot
  • Enriches with global threat intel
  • Generates KQL if investigation needed
  • Adds ATT&CK technique context
    │
    ▼
SOC Copilot (GAE pipeline)
  • Scores against firm-specific centroids (Clock 3)
  • Applies DiagonalKernel with your noise weights
  • Checks referral rules R1-R7
  • Logs to Evidence Ledger
  • Updates centroids from verified outcome
    │
    ▼
Analyst (for referred/uncertain cases)
  • Sees both Microsoft enrichment + SOC Copilot recommendation
  • Factor breakdown shows WHAT the system knew and WHY it decided
  • Override feeds back into centroid update
```

Microsoft makes analysts faster. SOC Copilot makes them smarter — and makes the system smarter every time they decide.

---

## The Pitch Line

*"Microsoft tells you what happened. We tell you what your firm has learned. After 1,000 decisions, ask both systems how they got smarter. Only one can answer. And the one that can will show you exactly which parts of your environment it learned to trust — encoded as geometry, not prose."*

---

## Objection Handling

**"We're already paying for E5 / Copilot for Security. Why add another tool?"**

Copilot for Security is a productivity tool — it makes your analysts faster at Clock 1-2 tasks. SOC Copilot is a learning system — it accumulates firm-specific intelligence at Clock 3-4. These are additive. The ROI calculation is independent: we measure time saved on triage decisions (44 min/alert baseline), not overlap with Microsoft's investigation assistance.

**"Microsoft will add learning capabilities eventually."**

Possibly. But the centroid tensor you build today is yours. When (if) Microsoft adds learning, you will be starting that journey 18–24 months ahead. And Microsoft's learning will reflect their global prior — yours reflects your firm. The geometry diverges from Day 1.

**"CrowdStrike Falcon already learns from threat data globally."**

CrowdStrike learns from threats across their customer base — they get smarter about the global threat landscape. That is Clock 1 intelligence (what is true globally). SOC Copilot learns from your analysts' decisions on your alerts — Clock 3 intelligence (how your firm's judgment evolves). CrowdStrike tells you about the attacker. We tell you about your defenders. Different clocks.

---

*Microsoft Threat Analysis v1.0 · Compounding Intelligence Platform · March 2026*  
*Four Clocks framework. Positioning: complementary, not competitive.*  
*Next: Regulatory Tailwind Map (gtm_regulatory_tailwind_v1.md)*
