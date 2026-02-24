# SOC Copilot: The AI That Learns From Every Decision

**A Working Demo of Compounding Intelligence for Security Operations**

*For CISOs, Security Operations Leaders, VCs, and Consulting Partners*
*Version: 2.5.1 | February 19, 2026 — Updated with experimental validation*

---

## The 30-Second Version

Your SOC has amnesia. Every day, your analysts investigate the same patterns — the same travel login anomaly for John Smith, the same phishing campaign targeting Finance, the same false positive from the Singapore VPN. They close it, move on, and tomorrow it happens again. Nothing is learned. Nothing compounds.

We built a working demo that shows a different model: a SOC copilot where every decision feeds a context graph, and that graph makes the next decision smarter. Week 1: 23 learned patterns, 68% auto-close rate. Week 4: 127 patterns, 89% auto-close. Same model. Same code. Smarter system. Four controlled experiments validate the math: the scoring matrix converges, cross-graph discovery operates at 110× above random, and discovery capacity scales as n^2.30 — a steeper moat than theory predicted.

This isn't a pitch deck. It's running code you can interact with.

---

## The Problem: Four Structural Gaps in Enterprise AI

Most AI deployments in security operations hit the same four walls:

**Gap 1: No Enterprise Context.** AI agents process alerts in isolation. They don't know that John Smith is traveling to Singapore this week, or that his laptop was recently re-imaged, or that the VPN provider he's using matches his travel record. The context exists in your systems — calendars, HR records, asset inventory, threat intel — but the AI can't reason over it.

**Gap 2: No Operational Evolution.** You deploy an AI model. It automates 60% of Tier 1 triage. Six months later, it still automates 60%. Alert patterns have changed, attack surfaces have shifted, but the model is frozen. Getting to 70% means hiring a prompt engineer, retuning, redeploying. Linear investment for linear improvement.

**Gap 3: No Situation Analysis.** A travel login anomaly and a phishing campaign are completely different situations requiring completely different reasoning. But most AI triage tools apply the same logic to both. There's no mechanism to classify the situation and adapt the decision approach accordingly.

**Gap 4: No Decision Economics.** When the AI recommends "auto-close," nobody asks: what does that save in time? In analyst cost? What's the risk if we're wrong? Without decision economics, there's no way to measure ROI, no way to justify the investment to a CFO, and no way to compare options rationally.

**[SCREENSHOT: Four Structural Gaps graphic from blog]**

---

## The Solution: Two Learning Loops, One Context Graph

The SOC Copilot demo shows an architecture that addresses all four gaps through a single mechanism: a context graph that two learning loops read from and write back to.

### How It Works

When an alert fires, the system doesn't just pattern-match. It traverses a graph of 47 connected nodes — the user's profile, their travel calendar, their device history, known attack patterns, resolved precedents, active policies — and builds a complete situational picture. Then it reasons over that picture, evaluates options, and makes a governed decision. The decision outcome feeds back into the graph, making the next traversal richer.

**Loop 1: The Situation Analyzer** — Gets smarter WITHIN each decision. Classifies the alert into one of six situation types (travel login anomaly, known phishing campaign, zero-day indicator, etc.), then evaluates response options with explicit time, cost, and risk for each. The analyst (or the CISO watching the demo) can see exactly why auto-close saves 42 minutes and $127 versus escalation.

**Loop 2: The AgentEvolver** — Gets smarter ACROSS decisions. Tracks which prompt variants and reasoning approaches produce better outcomes, then auto-promotes winners. In the demo, one variant improved from 71% to 89% success rate — translating to $4,800/month in recovered analyst time. The system didn't just follow better rules. It learned a better way to reason.

**The compounding effect:** Both loops feed the same graph. Loop 1's situation classifications make Loop 2's evolution more targeted. Loop 2's improved reasoning makes Loop 1's classifications more accurate. This is compounding intelligence — the system literally gets smarter with each decision cycle. And it's not just a claim: controlled experiments with synthetic SOC data show the scoring matrix converges to 69.4% accuracy from a 25% random baseline, cross-graph discovery operates at 110× above random, and discovery capacity scales as a n^2.30 power law — steeper than quadratic.

**[SCREENSHOT: Tab 4 — Two-Loop Hero Diagram showing Loop 1 and Loop 2 feeding the context graph]**

---

## What the Demo Shows: Four Tabs, Twelve Minutes

### Tab 1: SOC Analytics — Governed Metrics

Ask the system a natural language question — "Show me MTTR trends" or "Which detection rules have the highest false positive rate?" — and get governed, sourced answers. Every response shows provenance: which data sources were consulted, which governance rules applied, how confident the answer is.

The demo surfaces a concrete finding: $18K/month in wasted analyst time from redundant detection rules. This is the "quick win" a CISO can take to their next budget meeting.

**[SCREENSHOT: Tab 1 — Natural language query with provenance panel showing data sources]**

### Tab 2: Runtime Evolution — The Differentiator

This is the tab that makes the demo different from anything else in the market.

**Process an alert and watch what happens:**

1. The system receives an anomalous login alert
2. Four eval gates fire sequentially — confidence check, pattern match, risk threshold, policy compliance — each must pass before any action executes
3. When all four pass, the decision executes and writes a TRIGGERED_EVOLUTION relationship back to the graph: a new pattern learned, a confidence score updated, a precedent recorded
4. The AgentEvolver panel shows the operational impact: which prompt variant won, how many false escalations it eliminated, the dollar value of recovered analyst time

**The blocking demo:** Click "Simulate Failed Gate" and watch the system catch a bad candidate. The eval gate fires red, a BLOCKED banner appears, and the candidate is rejected. This is the answer to "What happens when the AI is wrong?" — it catches itself before acting.

**[SCREENSHOT: Tab 2 — Eval gates animating (all 4 green), with TRIGGERED_EVOLUTION panel showing pattern learned]**

**[SCREENSHOT: Tab 2 — AgentEvolver panel showing variant comparison: v1 (71%) vs v2 (89%), with "$4,800/month recovered" metric]**

**[SCREENSHOT: Tab 2 — BLOCKED banner after failed eval gate, showing the system catching itself]**

### Tab 3: Alert Triage — The Full Loop

Select an alert from the queue and watch the complete decision lifecycle:

**Step 1: Situation Classification.** The Situation Analyzer classifies ALERT-7823 as a "Travel Login Anomaly" — it recognizes that John Smith is traveling to Singapore, his VPN matches the travel record, MFA was completed, and the device fingerprint is known. Six contributing factors, weighted and scored.

**Step 2: Decision Economics.** Four response options, each with explicit time saved, cost avoided, and risk level:
- Auto-close (false positive): saves 42 minutes, $127 cost avoided, 3% residual risk
- Escalate to Tier 2: 15 minutes analyst time, $45 cost, 0.5% risk
- Enrich and wait: 8 minutes, $12 cost, 8% risk
- Isolate endpoint: 25 minutes, $89 cost, 0.1% risk

**Step 3: Policy Conflict Detection (v2.5).** For John Smith specifically, two policies apply and conflict: "Auto-close travel anomalies" (priority 3) versus "Escalate all high-risk users" (priority 1, because Smith's risk score is 0.85). The system detects the conflict, resolves by priority — security-first — and creates an audit trail (CON-2026-0847).

**Step 4: Closed Loop Execution.** Apply the recommendation and watch four verification steps animate: EXECUTED → VERIFIED → EVIDENCE → KPI IMPACT. This is what SIEMs don't do. They stop at detection. We close the loop and prove it worked.

**Step 5: Outcome Feedback (v2.5).** After the decision executes, the demo asks: "Was this decision correct?" Click "Confirmed Correct" and the pattern confidence increases by 0.3 points. Click "Incorrect — Real Threat" and confidence drops 6 points (a 20:1 asymmetry), the next 5 similar alerts route to Tier 2 for human review, and a threshold review triggers. This is self-correction in action.

**[SCREENSHOT: Tab 3 — Situation Analyzer showing "Travel Login Anomaly" classification with 6 contributing factors]**

**[SCREENSHOT: Tab 3 — Decision Economics panel showing 4 options with time/cost/risk for each]**

**[SCREENSHOT: Tab 3 — Policy Conflict panel showing two conflicting policies with resolution and audit ID]**

**[SCREENSHOT: Tab 3 — Closed Loop animation with all 4 steps green, showing execution receipt]**

**[SCREENSHOT: Tab 3 — Outcome Feedback panel with "Confirmed Correct" and "Incorrect" buttons, graph update table showing confidence changes]**

### Tab 4: Compounding Dashboard — The Board Slide

This is the tab a CISO takes to their CFO:

**847 analyst hours recovered per month. $127K cost avoided per quarter. 75% MTTR reduction. 2,400 false positive alerts eliminated weekly.**

The week-over-week comparison shows the compounding trajectory: auto-close rate climbing from 68% to 89%, MTTR dropping from 12.4 to 3.1 minutes, pattern library growing from 23 to 127 — all without any manual intervention.

The Two-Loop Hero Diagram at the bottom connects it back to the architecture: Loop 1 and Loop 2 feeding the same context graph, both reading and writing, creating the compounding effect.

**ROI Calculator (v2.5):** Click "Calculate Your ROI" and input your SOC's actual numbers — alert volume, analyst headcount, average salary, current MTTR, current auto-close rate. The system projects your specific savings. A mid-size SOC (500 alerts/day, 8 analysts at $85K) shows $1.08M annual savings with a 6-week payback and 9x ROI. The breakdown is transparent: $894K analyst time, $146K escalation costs, $40K compliance automation. A CFO-ready narrative is generated automatically.

**[SCREENSHOT: Tab 4 — Business Impact Banner showing 847 hrs, $127K, 75% MTTR, 2,400 alerts]**

**[SCREENSHOT: Tab 4 — Week-over-week comparison table showing compounding trajectory]**

**[SCREENSHOT: Tab 4 — ROI Calculator modal with sliders on left, projected savings on right, showing $1.08M annual savings]**

---

## Why This Is Different

### vs. Traditional SIEMs (Splunk, Microsoft Sentinel, QRadar)

SIEMs detect and log. They don't learn. When Splunk fires an alert, it goes to a human queue. The human investigates, closes it, and Splunk learns nothing. Tomorrow, the same alert fires again. After a year, Splunk has the same detection rules plus whatever a human wrote manually. Our demo shows a system that starts with the same detection rules but accumulates intelligence automatically — 23 patterns in Week 1, 127 in Week 4, trending toward 500+ by month 3. Our experiments validate this: discovery capacity scales as n^2.30 with each connected knowledge domain.

### vs. SOAR Platforms (Palo Alto XSOAR, Swimlane)

SOAR automates playbooks — static, if/then logic written by humans. When the world changes, the playbook doesn't. Our architecture runs playbooks AND evolves them. The AgentEvolver tracks which reasoning approaches work better and promotes winners automatically. The playbook isn't a fixed artifact — it's a living thing that gets smarter.

### vs. AI Security Vendors (Darktrace, SentinelOne)

Darktrace learns your baseline behavior. We learn from your decisions. Baselines detect anomalies. Decisions compound intelligence. The difference: Darktrace notices John Smith logged in from Singapore. We know it's his third trip this quarter, his VPN matches, his MFA completed, and the last 127 similar patterns were all false positives — so we auto-close with 94% confidence, log the decision trace, and update the graph. Our experiments measured cross-graph discovery at 110× above random baseline — that's the quantitative difference between "detecting anomalies" and "discovering institutional patterns."

---

## Validated by Experiment: Four Tests, Six Charts

The architecture claims above aren't just design assertions — we validated the mathematical framework through four controlled experiments using synthetic SOC data. This is what separates the demo from a concept deck.

### Experiment 1: Scoring Matrix Convergence

**Question:** Does the weight update rule actually cause the scoring matrix to converge?

**Setup:** 5,000 synthetic alerts with known ground-truth optimal actions. Weight matrix initialized randomly. Online learning with asymmetric penalties — failures penalized 5× harder than successes are rewarded.

**Result:** Convergence to **69.4% accuracy** from a 25% random baseline. Three distinct learning phases: random exploration (0-200 decisions), rapid calibration (200-1500), and diminishing returns (1500-5000) as remaining errors reflect genuinely ambiguous alerts.

**Three failure modes identified:**
- **Action Confusion:** When two actions have similar factor profiles, the system hedges instead of deciding. Fix: design maximally distinguishable action sets.
- **Over-Correction Oscillation:** Asymmetric penalties cause damped oscillation after bad outcomes. Fix: tune the penalty ratio to the domain (SOC: 5-10×, ITSM: 1.5-2×).
- **Treadmill Effect:** If the forgetting rate is too close to the learning rate, new knowledge erases before it consolidates. Fix: maintain a 20:1 learning-to-forgetting ratio.

**What this validates:** The 68% → 89% trajectory in the demo is consistent with the controlled experiment. Production accuracy is higher because real alert distributions have more structure than synthetic data.

**[CHART: exp1_scoring_convergence.pdf — Convergence curve with three phases annotated]**

### Experiment 2: Cross-Graph Discovery

**Question:** Does cross-attention between entity embeddings discover semantically meaningful relationships?

**Setup:** Two synthetic graph domains — Security Context (100 entities) and Threat Intelligence (80 entities) — with 15 "planted" true discoveries among 8,000 possible entity pairs (signal-to-noise: 0.19%).

**Result:** With properly normalized embeddings, cross-graph attention discovered true relationships at **110× above random baseline** (F1 = 0.293). Without normalization, performance dropped to 23× — a 4× difference from a single preprocessing step.

**Why this matters for the demo:** The Singapore recalibration example in Tab 3 isn't a scripted scenario — it's the kind of discovery the cross-attention mechanism produces measurably. Embedding normalization is a prerequisite, not an optimization.

**[CHART: exp2_cross_graph_f1.pdf — Two-bar F1 comparison: raw vs. normalized]**

### Experiment 3: Multi-Domain Scaling

**Question:** How does discovery capacity scale with the number of connected graph domains?

**Setup:** Variable domains (2-8), fixed domain size (50 entities each), normalized embeddings.

**Result:** Discovery follows a power law: **D(n) ∝ n^2.30** (R² = 0.9995). Super-quadratic — steeper than the theoretical n² lower bound. The excess exponent (0.30) comes from cross-discovery amplification: discoveries from one domain pair enrich entities, making them more discoverable by other domain pairs.

**Why this matters for the moat:** The gap between a system with 6 connected domains and one with 3 isn't 2× — it's closer to 5×. And this multiplies with operating time. The updated moat equation: I(n,t) ~ O(n^2.3 · t^1.5). A competitor starting 12 months late faces a gap that's nearly twice their total accumulated intelligence.

**[CHART: exp3_domain_scaling.pdf — Log-log plot with power law fit and n² reference line]**

### Experiment 4: Sensitivity & Phase Transitions

**Question:** How robust is cross-graph discovery to parameter variations?

**Setup:** Systematic grid search across embedding dimension, discovery threshold, graph density, and embedding quality.

**Key finding:** A **sharp phase transition** in discovery quality. F1 holds steady as embedding quality degrades — then collapses suddenly between σ = 0.3 and σ = 0.5. Not gradual degradation. A cliff. Below the threshold, attention filters noise. Above it, discoveries become random.

**Seven design principles** derived from the sensitivity analysis, from "normalize embeddings before cross-attention" (non-negotiable) to "target 8-16 edges/node in graph construction" (sweet spot for discovery quality).

**Why this matters for production:** Systems need to monitor embedding quality and alert before crossing the critical boundary. This is a previously unreported finding with direct operational implications.

**[CHART: exp4_sensitivity.pdf — 2×2 heatmap grid showing phase transition boundary]**

### What the Experiments Mean for This Demo

The demo shows the architecture working. The experiments show *why* it works and *where it breaks*. Together, they provide something no other AI SOC vendor can offer: a mathematically grounded, experimentally validated framework for self-improving decision systems — with documented failure modes and production design guidance.

Full mathematical framework with 17 equations, 6 charts, and worked examples: https://www.dakshineshwari.net/post/cross-graph-attention-mathematical-foundation

---

## The Architecture: ACCP

The SOC demo is the reference implementation of the Agentic Cognitive Control Plane (ACCP) — an architectural pattern for governed, self-improving enterprise AI built on five structural capabilities:

1. **Typed-Intent Bus** — normalizes signals into classified intents
2. **Situational Mesh** — scores situations using context, KPIs, and drift signals
3. **Eval Gates** — enforces structural safety checks before any action
4. **TRIGGERED_EVOLUTION** — writes verified outcomes back to the context graph
5. **Decision Economics** — tags every action with time, cost, and risk impact

v2.5 implements 10 of 18 ACCP capabilities. The architecture is domain-agnostic — SOC is the first domain. The same pattern applies to ITSM (incident management), Source-to-Pay (procurement), and AML (anti-money laundering). The context graph and learning loops are the same; only the domain entities change.

---

## The Technology

The demo is built with production-grade tools, not notebook prototypes:

- **Backend:** FastAPI (Python), async endpoints, Pydantic v2 validation
- **Frontend:** React 18 + TypeScript, Tailwind CSS, Recharts for visualization
- **Graph Database:** Neo4j Aura — 47 nodes, 52 relationships per alert context
- **Architecture:** Two learning loops, eval gates, closed-loop execution, decision traces
- **Agent:** Rule-based decision engine (~200 lines) with LLM narration — intentionally simple because the demo proves the architecture, not agent sophistication

The entire demo runs locally. No cloud dependencies at runtime (Neo4j Aura for the graph, everything else local). Docker packaging for partner distribution is in progress.

---

## What's Next

**Completed:** Mathematical framework experimentally validated — 4 experiments, 6 charts, 3 failure modes documented, 7 design principles derived, moat equation updated to I(n,t) ~ O(n^2.3 · t^1.5).

**v3.0 (in design):** Automated outcome detection (no manual feedback button — the system watches SIEM re-opens), external threat intel ingestion (CVE feeds into the graph), compliance-grade evidence ledger (immutable decision records for SOC2/NIST/ISO audits), and process intelligence integration.

**v3.5/v4.0 (vision):** Formal intent routing bus, multi-domain copilots sharing one context graph (SOC + ITSM + Finance), and a Control Tower that routes intents to specialist copilots. This is the platform thesis: not one copilot, but a substrate that makes every copilot smarter from day one.

---

## See It Live

The demo runs in 12 minutes. The "aha moment" typically hits around minute 3, when the eval gates fire and the system either validates or catches itself. By minute 8, most CISOs have pulled out a calculator. By minute 10, they're asking about deployment timelines.

Contact: arindam@dakshineshwari.net

**Background Reading:**
- Operationalizing Context Graphs — https://www.dakshineshwari.net/post/operationalizing-context-graphs-ciso-cybersecurity-ops-agent-demo
- Compounding Intelligence — https://www.dakshineshwari.net/post/compounding-intelligence-how-enterprise-ai-develops-self-improving-judgment
- Cross-Graph Attention (Math + Experiments) — https://www.dakshineshwari.net/post/cross-graph-attention-mathematical-foundation
- Gen-AI ROI in a Box — https://www.dakshineshwari.net/post/gen-ai-roi-in-a-box
- Enterprise Agent Engineering Stack — https://www.dakshineshwari.net/post/the-enterprise-class-agent-engineering-stack-from-pilot-to-production-grade-agentic-systems
- Unified Context Layer (UCL) — https://www.dakshineshwari.net/post/unified-context-layer-ucl-the-governed-context-substrate-for-enterprise-ai

---

## Screenshot Inventory (For Final Production)

| Marker | Tab | What to Capture | Notes |
|---|---|---|---|
| SCREENSHOT-01 | Blog | Four Structural Gaps graphic | Already exists on Wix |
| SCREENSHOT-02 | Tab 4 | Two-Loop Hero Diagram | Full width, show both loops |
| SCREENSHOT-03 | Tab 1 | NL query with provenance | Query: "Show MTTR trends" |
| SCREENSHOT-04 | Tab 2 | Eval gates all green + TRIGGERED_EVOLUTION | After processing alert |
| SCREENSHOT-05 | Tab 2 | AgentEvolver panel | Show variant comparison + $4,800 |
| SCREENSHOT-06 | Tab 2 | BLOCKED banner | After "Simulate Failed Gate" |
| SCREENSHOT-07 | Tab 3 | Situation Analyzer | ALERT-7823, travel anomaly |
| SCREENSHOT-08 | Tab 3 | Decision Economics | 4 options with time/cost/risk |
| SCREENSHOT-09 | Tab 3 | Policy Conflict panel | Amber conflict, two cards |
| SCREENSHOT-10 | Tab 3 | Closed Loop animation | All 4 steps green |
| SCREENSHOT-11 | Tab 3 | Outcome Feedback | After clicking correct/incorrect |
| SCREENSHOT-12 | Tab 4 | Business Impact Banner | 847 hrs, $127K, 75%, 2,400 |
| SCREENSHOT-13 | Tab 4 | Week-over-week comparison | 4-week table |
| SCREENSHOT-14 | Tab 4 | ROI Calculator modal | Sliders + $1.08M result |
| CHART-EXP1 | Experiment | Scoring convergence curve | exp1_scoring_convergence.pdf |
| CHART-EXP2 | Experiment | F1 bar comparison | exp2_cross_graph_f1.pdf |
| CHART-EXP3 | Experiment | Power law scaling plot | exp3_domain_scaling.pdf |
| CHART-EXP4 | Experiment | Sensitivity phase transition grid | exp4_sensitivity.pdf |

*SOC Copilot Demo Description v2.5.1 | February 19, 2026 — Updated with experimental validation*
