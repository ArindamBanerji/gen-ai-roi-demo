# SOC Copilot — Product Strategy & Value Feature Roadmap

**Version:** 1.0
**Date:** February 26, 2026
**Status:** Product management document — informs v4.x–v5.x feature planning
**Parent docs:** session_continuation_v10.md, backlog_v9.md, soc_copilot_roadmap_v3.md

---

## Part 1: The Core Insight — How Institutional Judgment Actually Works

Human analysts don't just get faster at the same task. Their reasoning evolves along three axes:

**Axis 1 — Graph Accumulation.** They encounter new types of context. A junior analyst knows alert types. By month six, they've accumulated knowledge about organizational changes, travel patterns, compliance calendars, threat campaigns, vendor relationships. Each new type of knowledge is a new graph domain. The analyst doesn't just have more facts — they have more *kinds* of facts, and these kinds interact to produce insight that no single domain contains.

**Axis 2 — Context Fine-Tuning.** They continuously customize how they weigh context. Not all factors matter equally at every firm. At one organization, travel anomalies are almost always benign (global workforce). At another, they're the strongest indicator of compromised credentials. The analyst calibrates — unconsciously — through verified outcomes. The weights that drive their judgment become firm-specific.

**Axis 3 — Capability Extension.** They extend their decision-making repertoire. A new type of alert they've never seen before doesn't paralyze them — they recognize structural similarities to alerts they have seen, apply cross-domain reasoning, and invent new evaluation criteria on the spot. Their scoring matrix gains new dimensions. "I've never seen this exact pattern, but the combination of credential access + off-hours + the Singapore threat report we got last week makes me think..."

These three axes are what make a two-year analyst irreplaceable. And they are exactly what every competitor in the AI SOC market fails to replicate.

---

## Part 2: Competitive Landscape — Where They Stop

### The Market as of February 2026

The AI SOC market has 40+ players (IDC count). The funded leaders:

| Vendor | Funding | Core Mechanism | Learning Model |
|---|---|---|---|
| **Torq** | $1.2B valuation | Multi-agent workflow (Socrates) | None — agentic per-alert reasoning |
| **Dropzone AI** | Funded (undisclosed) | Autonomous investigation (OSCAR) | **Context Memory** — fact store |
| **Intezer** | Funded | Forensic AI + code analysis | Pre-trained expert modules |
| **Prophet Security** | $24M | Agentic investigation | Agentic per-alert reasoning |
| **Radiant Security** | Funded | Adaptive AI | Claims adaptive, details sparse |
| **Andesite** | $23M | "Bionic SOC" — human+AI cockpit | Investigation traceability |

Incumbents adding AI: CrowdStrike Falcon Fusion, Palo Alto XSOAR, Splunk SOAR, Swimlane Turbine.

### What They All Share (Table Stakes — 2026)

Every serious player offers: autonomous Tier-1 triage, multi-source enrichment, agentic reasoning (not static playbooks), MITRE ATT&CK mapping, auto-containment, case management with evidence trails, 85–300+ pre-built connectors.

### Where They Stop

**Torq:** Brilliant at workflow orchestration. No learning mechanism whatsoever. Day 1,000 = Day 1 except for manually updated playbooks. Their moat is integrations (200+ connectors) and speed.

**Dropzone AI — the closest competitor to our thesis:**

Dropzone's "Context Memory" is the only product in the market that explicitly claims institutional knowledge. It learns from: past investigations, analyst feedback, direct user input. An Enterprise Times review (Feb 2026) identified the critical weakness: *"This leaves customers having to wait for the major LLMs to update their information on those attack paths... It runs counter to how you would expect to learn from data."* A Gartner reviewer complained about difficulty managing Context Memory Entries.

**Why Context Memory is not compounding intelligence:**

| Property | Dropzone Context Memory | Our Compounding Intelligence |
|---|---|---|
| What accumulates | Facts ("IP X is contractor VPN") | Facts + calibrated weights + discovered relationships + new scoring dimensions |
| What changes | What the LLM reads before reasoning | How the system reasons (Eq. 4 weight matrix) |
| New knowledge types | Manual: analyst adds facts | Autonomous: cross-graph discovery finds connections between domains |
| Learning signal | Analyst feedback → stored fact | Verified outcome → asymmetric RL → weight update → graph evolution |
| Day 1 vs Day 1000 | Better fact store, same LLM reasoning | Structurally different decision-maker with firm-specific judgment |
| Model dependency | LLM quality determines ceiling | Graph compounds independently of LLM — model-independent moat |

**The one-line differentiator:** Dropzone gives the new hire a better cheat sheet every day. We make the new hire into a senior analyst.

**Intezer:** Strong forensic capabilities (code analysis, sandboxing, reverse engineering). No learning feedback loop. Their differentiation is investigation depth, not compounding.

---

## Part 3: Positioning — Decision Intelligence Platform

### The Category

Not SOAR (workflow automation). Not "AI SOC Analyst" (autonomous triage). Not XDR (extended detection).

**Compounding Decision Intelligence** — the enterprise AI architecture where every verified decision makes every subsequent decision richer.

### The Three-Sentence Pitch

"Every AI SOC tool on the market makes brilliant decisions on day one. After ten thousand decisions, they haven't learned a thing. We build the system that develops institutional judgment — the same trajectory a smart analyst follows, except at machine scale and it never loses what it learns."

### The Competitive Frame

| | SOAR | AI SOC Analyst | **Decision Intelligence** |
|---|---|---|---|
| Examples | Torq, Swimlane, Tines | Dropzone, Intezer, Prophet | **Us** |
| Core | Workflow orchestration | Per-alert LLM reasoning | Graph attention + learning loops |
| Axis 1 (Graph Accumulation) | — | Flat fact store | **New graph domains compound** |
| Axis 2 (Context Fine-Tuning) | — | — | **Weights calibrate from outcomes** |
| Axis 3 (Capability Extension) | — | — | **New scoring dimensions discovered** |
| Moat source | Integrations (replicable) | LLM quality (rented) | **Firm-specific graph (owned)** |
| Survives LLM transition? | N/A | No — LLM is the product | **Yes — graph is the product** |

### Key Positioning Lines

**For CISOs:**
- "CrowdStrike detects. Pulsedive enriches. We decide — and we get better at deciding with every verified outcome."
- "Your SIEM gets better detection rules written by humans. Our copilot gets smarter automatically through validated decisions."
- "After ten thousand decisions, show me how your system got smarter. We can. They can't."

**For VCs:**
- "Torq and Dropzone are renting intelligence — LLM API calls. We're building it — a compounding graph that appreciates with use."
- "The competitive moat is structural: firm-specific, temporally irreversible, model-independent, recursive. A competitor deploying today starts at zero."
- "Same architecture, different domain. SOC today. Supply chain, financial services — same loops, same infrastructure, new domain module."

**Against Dropzone specifically:**
- "Context Memory remembers that IP X is a contractor. Our system discovers that contractor access patterns changed the same week the Singapore threat report spiked — and creates a new scoring dimension neither the analyst nor we programmed."
- "Their system accumulates facts. Ours accumulates judgment."

---

## Part 4: Prioritized Value Features

Features are organized by the three axes of compounding intelligence, then prioritized by competitive impact and build feasibility.

### Priority Tier 1: MUST HAVE — Without These, CISOs Won't Engage

---

#### F1. MITRE ATT&CK Alignment [Credibility]

**Why:** Every SOC tool in 2026 speaks ATT&CK. CrowdStrike just scored 100% on the MITRE Enterprise 2025 evaluation. Torq's Socrates auto-maps to ATT&CK. Our demo has zero ATT&CK language. This is the single fastest credibility gap to close.

**What:** Each seed alert carries a MITRE technique ID and tactic category. The situation classifier references ATT&CK in its output. Tab 1 can group alerts by tactic.

**Example mapping:**
- ALERT-7823 (VPN travel login): T1078 — Valid Accounts (Initial Access)
- ALERT-7824 (off-hours admin access): T1078.004 — Cloud Accounts
- New phishing alert: T1566.001 — Spearphishing Attachment (Initial Access)
- New lateral movement alert: T1021.001 — Remote Desktop Protocol (Lateral Movement)

**Demo moment:** An alert arrives and the system immediately shows "T1078 — Valid Accounts | Tactic: Initial Access" alongside the situation classification. CISO sees the language they live in.

**Build effort:** Small. Taxonomy alignment on seed data + situation classifier output + minor Tab 3 UI label. ~2 Claude Code prompts.

**Axis:** None (table stakes) — but prerequisite for credibility.

---

#### F2. Realistic Alert Corpus [Credibility]

**Why:** The demo has ~4 alerts, all travel-login variants. Real SOCs see phishing, credential stuffing, lateral movement, cloud misconfigs, insider anomalies — daily. Having only one alert type makes the six-factor breakdown look rigged (travel_match always lights up, other factors dormant). 15–20 alerts across 4–5 situation types make the compounding curve demonstrable.

**What:** Seed 15–20 alerts across distinct categories:

| Category | Example Alerts | Situation Type | Key Factor Activated |
|---|---|---|---|
| Travel/VPN anomaly | Singapore login, Tokyo login, VPN mismatch | KNOWN_BENIGN / TRAVEL_ANOMALY | travel_match, device_trust |
| Credential/access | Off-hours admin, privilege escalation, failed MFA | SUSPICIOUS_PATTERN | time_anomaly, asset_criticality |
| Threat intel match | Known C2 IP, IOC from feed, blacklisted domain | KNOWN_THREAT | pattern_history, threat_intel_enrichment |
| Insider/behavioral | Data exfiltration pattern, bulk download, USB activity | ANOMALOUS_BEHAVIOR | VIP_status, asset_criticality |
| Cloud/infra | SG rule change, public S3 bucket, IAM role assumption | COMPLIANCE_RISK | asset_criticality, pattern_history |

**Demo moment:** Process 5 alerts in sequence. Each lights up different factors. The audience sees the system isn't hard-coded — it genuinely reasons differently per situation type.

**Build effort:** Medium. New seed data script, new graph nodes/relationships, expanded situation classifier. ~3-4 Claude Code prompts.

**Axis:** Prerequisite for demonstrating Axis 2 (different alerts produce different factor weights → visible calibration).

---

#### F3. Investigation Narrative [Credibility]

**Why:** Every competitor produces a plain-English investigation summary. Dropzone generates narratives using OSCAR methodology. Intezer produces forensic reports. Our Tab 3 shows quantitative factors (bar charts), which is strong for the transparency claim but misses the natural-language explanation CISOs expect.

**What:** After situation analysis, generate a 3–5 sentence decision narrative:

> "ALERT-7823 classified as TRAVEL_ANOMALY (T1078 — Valid Accounts). Graph traversal: 47 nodes across 3 domains. User jsmith has 14 prior travel logins from APAC, all resolved as benign — travel_match weight elevated to 0.23 (calibrated from 12 verified outcomes). Device trust confirmed: corporate laptop, certificate valid. Pulsedive enrichment: IP 103.15.42.17 classified low-risk. Recommendation: false_positive_close at 91% confidence."

**Demo moment:** The narrative appears alongside the factor breakdown. CISOs read the reasoning in their language. The key line: "calibrated from 12 verified outcomes" — this is the compounding proof in natural language.

**Build effort:** Medium. Backend narrative generation service + Tab 3 panel. ~2-3 Claude Code prompts.

**Axis:** Supports Axis 2 visibility (narrative explicitly references calibration history).

---

### Priority Tier 2: DIFFERENTIATORS — What Competitors Cannot Replicate

---

#### F4. Visible Compounding Proof [Axis 2 — Context Fine-Tuning]

**Why:** This is the single most important feature for the competitive thesis. The CI blog claims "Week 1: 23 patterns, Week 4: 127, auto-close rate 68% → 89%." The demo needs to make this visible in 15 minutes. No competitor can show this because none of them have the mechanism.

**What:** A "Compounding Curve" panel in Tab 4 that shows:
- Weight matrix evolution: before/after comparison of factor weights as verified outcomes accumulate
- Confidence trajectory: how confidence on a specific alert type changed over decisions
- Auto-close rate progression: ticking upward as the system learns
- Decision count with learning milestones: "After 4 verified outcomes, travel_match weight adjusted from 0.15 → 0.23"

The demo flow:
1. Process alert → initial confidence 72%
2. Give feedback (correct)
3. Process a similar alert → confidence now 76%
4. Give feedback on 3 more
5. Tab 4 shows the curve — weight matrix visually shifted, confidence on that alert type now 89%
6. **The money line:** "Same model. Same code. Smarter graph. No manual intervention between steps."

**Demo moment:** Side-by-side: "Decision #1 vs Decision #8 — same alert type, different confidence. Here's exactly what changed and why." This is the moment no competitor can replicate.

**Build effort:** Medium-High. Requires the weight update mechanism to be more visible (it exists in AgentEvolver but isn't surfaced clearly). New Tab 4 panel. ~4-5 Claude Code prompts.

**Axis:** Axis 2 — Context Fine-Tuning. The audience watches the system's judgment calibrate in real time.

---

#### F5. Cross-Domain Discovery Moment [Axis 1 + Axis 3 — Graph Accumulation + Capability Extension]

**Why:** This is the "wow" moment that makes the CI thesis tangible. The CI blog describes it: Singapore login + CFO promotion + threat spike = a connection no analyst programmed. This needs to be a live demo event, not a blog claim. It demonstrates both Axis 1 (multiple graph domains interacting) and Axis 3 (new scoring dimension emerges).

**What:** Two-part demo sequence:

**Part A — Setup (seed the conditions):**
- Organizational graph: jsmith promoted to CFO 3 weeks ago (access pattern change)
- Threat intel graph: Singapore credential stuffing campaign up 340% this week
- Decision history: 14 prior Singapore logins for jsmith, all resolved benign

**Part B — Discovery (live):**
- Process the new Singapore login for jsmith
- The cross-graph attention mechanism detects: role_change (Org graph) + threat_spike (TI graph) + historical_pattern (Decision graph) co-occur
- A new relationship is written to the graph: [:DISCOVERED_PATTERN {source: "cross_graph_sweep", domains: ["organizational", "threat_intel", "decision_history"]}]
- Tab 4 shows: "Discovery: role-change correlation with threat-landscape change. New scoring dimension: role_recency_risk added to evaluation."
- The confidence for this alert drops from 89% (historical pattern says benign) to 34% (discovery says re-evaluate)
- **The moment:** "Nobody programmed this rule. The system discovered it by reasoning across three graph domains simultaneously."

**Demo moment:** Show the graph visualization with the new discovery relationship highlighted. Show the confidence dropping. Show the new scoring dimension. Ask: "Can your current tool do this?"

**Build effort:** High. Requires cross-graph attention to be demonstrable (the math exists in the experiments repo but isn't wired into the demo). New seed data for the scenario. New Tab 4 panel for discoveries. ~6-8 Claude Code prompts across multiple sessions.

**Axis:** Axis 1 (multiple graph domains interacting) + Axis 3 (new scoring dimension emerges autonomously).

---

#### F6. Asymmetric Trust Curve [Axis 2 — Context Fine-Tuning]

**Why:** The 20:1 penalty/reward ratio addresses the #1 CISO objection: "What if the AI is wrong?" The IBM 2025 breach cost is $4.44M average. The system needs to earn trust slowly and lose it fast — and this needs to be visible, not just claimed.

**What:** A trust curve visualization in Tab 2 or Tab 4:
- X-axis: decisions over time
- Y-axis: system confidence / trust level
- Show the asymmetry: 10 correct decisions slowly build confidence. 1 wrong decision drops it sharply.
- After a wrong decision: show the system automatically routing similar alerts to human review for the next N decisions
- Show the recovery: the system earns back trust through verified human-reviewed outcomes

**Demo moment:** "Watch what happens when the system gets one wrong." Demonstrate the wrong-decision scenario. Show the confidence crash. Show the automatic human-routing. Show the slow recovery. "This system is designed to earn trust slowly and lose it fast. That's not a bug — it's the architecture."

**Build effort:** Medium. Loop 3 visualization exists but needs to be more dramatic/clear. The auto-routing-to-human on confidence drop is a new behavior. ~3-4 Claude Code prompts.

**Axis:** Axis 2 — Context Fine-Tuning (trust calibration is a form of weight adjustment).

---

### Priority Tier 3: MARKET EXPANSION — Opens New Buyer Segments

---

#### F7. ATT&CK Coverage Heatmap [Axis 1 — Graph Accumulation]

**Why:** CISOs need metrics for their board. A heatmap showing which ATT&CK techniques the system has triaged, learned from, and developed confidence on is a SOC maturity metric that compounds over time. The heatmap filling in IS the compounding curve, expressed in the language CISOs use with their boards.

**What:** Tab 4 panel showing a simplified ATT&CK matrix (top 20-30 techniques relevant to the alert corpus). Color-coded by confidence level. Clickable to show decision count and weight calibration per technique.

**Demo moment:** "After 6 months, here's what your system knows. After 12 months, here's how the coverage expanded. This heatmap is your system's institutional judgment — and it's an asset that appreciates."

**Build effort:** Medium. Requires ATT&CK taxonomy (F1) + alert corpus (F2) + compounding data (F4). ~3-4 Claude Code prompts.

**Axis:** Axis 1 — visualizes graph accumulation across technique domains.

---

#### F8. Shift Handoff Intelligence [Axis 1 — Graph Accumulation]

**Why:** 79% of orgs experience peak alert fatigue at shift transitions (SANS 2025). Institutional knowledge walks out the door at every shift change. The graph doesn't forget. Making this explicit — "here's what changed since your last shift" — is a feature no human SOC team can match.

**What:** A "Shift Summary" panel accessible from Tab 1:
- New patterns discovered since last shift
- Confidence changes on key alert types
- Threat landscape changes (new TI ingested)
- Decisions that were auto-routed to human review (and why)
- Open items requiring human attention

**Demo moment:** "Your night shift discovered a pattern that changes how your day shift evaluates travel logins. In a human SOC, that's a Slack message that gets lost. In our system, it's a calibrated weight that persists."

**Build effort:** Medium. Aggregation of existing data into a new view. ~3 Claude Code prompts.

**Axis:** Axis 1 — demonstrates that accumulated graph knowledge survives organizational events.

---

#### F9. Compliance Framing [Credibility — Regulated Industries]

**Why:** Alert fatigue delays breach detection beyond NIS2, GDPR, and CIRCIA reporting windows. Our evidence ledger (SHA-256 chain) already provides the audit trail. Adding explicit compliance framing opens healthcare (HIPAA), financial services (SOX, SEC), and EU (NIS2) buyers.

**What:** Evidence Ledger export with compliance header metadata. HIPAA §164.530(j) format option. Configurable retention period labels. "Compliance verified" badge on Tab 4. Not deep implementation — labeling and framing of existing capability.

**Demo moment:** "Export this to your compliance team. SHA-256 chained. Every decision traceable. HIPAA-ready."

**Build effort:** Small. Mostly UI framing + export format enhancement. ~2 Claude Code prompts.

**Axis:** None directly — but unlocks regulated-industry buyers.

---

## Part 5: Feature Sequencing Across Versions

### How Features Map to the Existing Roadmap

The existing v4.0 and v4.5 scope stays as-is. Value features integrate alongside or between existing phases.

| Feature | Earliest Version | Dependencies | Claude Code Prompts |
|---|---|---|---|
| F1: MITRE ATT&CK Alignment | **v4.0 Phase 1** (alongside connectors) | None — taxonomy only | 2 |
| F2: Realistic Alert Corpus | **v4.0 Phase 1** (alongside connectors) | F1 (ATT&CK technique IDs) | 3-4 |
| F3: Investigation Narrative | **v4.0 Phase 4** (polish) | F2 (needs varied alerts) | 2-3 |
| F4: Visible Compounding Proof | **v4.0 Phase 4** or **v4.1** | F2 (needs varied alerts for visible calibration) | 4-5 |
| F5: Cross-Domain Discovery | **v4.5** (aligns with INOVA-4a discovery sweep) | F2 + F4 + Live Graph (LG1-LG4) | 6-8 |
| F6: Asymmetric Trust Curve | **v4.0 Phase 4** or **v4.1** | F2 (needs enough alerts to show curve) | 3-4 |
| F7: ATT&CK Coverage Heatmap | **v4.1** or **v4.5** | F1 + F2 + F4 | 3-4 |
| F8: Shift Handoff Intelligence | **v5.0** (production feature) | F4 + Live Graph | 3 |
| F9: Compliance Framing | **v4.5** (aligns with INOVA-6 HIPAA framing) | Existing evidence ledger | 2 |

### Recommended Build Order

**Phase A — Credibility Foundation (v4.0 Phase 1, alongside connector work):**
F1 → F2 (ATT&CK alignment + realistic alert corpus)

**Phase B — Demonstration Power (v4.0 Phase 4 or v4.1):**
F3 → F4 → F6 (narrative + compounding proof + asymmetric trust)

**Phase C — Differentiation (v4.5):**
F5 → F7 → F9 (cross-domain discovery + heatmap + compliance)

**Phase D — Production (v5.0+):**
F8 (shift handoff)

### Total New Effort: ~28-37 Claude Code Prompts

This is in addition to the existing v4.0 (20 prompts) and v4.5 (15 prompts). However, F1 and F2 naturally fit into the v4.0 Phase 1 sessions. F3 and F6 fit into Phase 4. F5, F7, F9 align with existing v4.5 scope. So the incremental effort is lower than the raw prompt count suggests.

---

## Part 6: Demonstrating Each Axis — The 15-Minute Story

The demo script (Loom v2/v3) should be restructured around the three axes. Each axis gets a clear demo moment:

### Axis 1 — Graph Accumulation (Tab 1 + Tab 4)

**What the audience sees:** Multiple data sources feeding one graph. Cross-source correlations visible. The graph grows with each ingested source.

**Setup:** Tab 1 shows Threat Landscape with data from Pulsedive + GreyNoise + CrowdStrike (v4 connectors). The graph has organizational data, threat intel, decision history — multiple domains.

**Demo beat:** "Your SIEM stores events. We store relationships. And when a second source confirms what the first source suspected, the graph creates a connection that enriches every future decision."

**Proof point (v4.5 — F5):** The cross-domain discovery moment. Singapore + CFO + threat spike. "This connection was discovered autonomously."

### Axis 2 — Context Fine-Tuning (Tab 2 + Tab 3 + Tab 4)

**What the audience sees:** Confidence scores changing across decisions. Weight matrix visibly shifting. The system getting better at this firm's specific patterns.

**Setup:** Process 5 alerts. Give feedback on 3. Come back to Tab 4.

**Demo beat:** "Same model. Same code. Smarter graph. Decision #1: 72% confidence. Decision #8: 91%. Here's exactly what changed — travel_match weight calibrated from 0.15 to 0.23 based on 4 verified outcomes at this firm."

**Proof point (F4):** The compounding curve — visible weight evolution.

**Follow-up (F6):** "Now watch what happens when the system gets one wrong." Show the asymmetric trust crash and human-routing.

### Axis 3 — Capability Extension (Tab 4 + Tab 3)

**What the audience sees:** A new scoring dimension that didn't exist in the original design, discovered by the system from operational experience.

**Setup:** The cross-domain discovery (F5) has found the role-change correlation.

**Demo beat:** "The system now evaluates every alert against role_recency_risk — a dimension that wasn't in the original design. Nobody programmed this rule. The system extended its own decision-making capability by reasoning across three graph domains."

**Proof point (F7):** The ATT&CK heatmap — coverage expanding over time as the system encounters and learns from new technique types.

### The Closing Line

"Torq automates your playbooks. Dropzone remembers your facts. We develop your institutional judgment. After ten thousand decisions, show me how your system got smarter. Here's ours."

---

## Part 7: What This Changes in Outreach

### Demo Blurb Update (after F1 + F2 ship)

Current: "Fourteen of twenty-one capabilities" / single alert type focus
Updated: ATT&CK technique language / multiple alert categories / multi-source / decision intelligence positioning

### Loom Script v9 (after F3 + F4 ship)

Restructured around the three axes. Opens with the same "ten thousand decisions" question. Now can prove it live with the compounding curve.

### Competitive Positioning One-Pager (can write now)

Three-column comparison: SOAR vs AI SOC Analyst vs Decision Intelligence. With the Dropzone Context Memory specific comparison. For CISO and VC audiences.

### LinkedIn Post Series (after F4 ships)

- "Every AI SOC tool resets at midnight. Ours doesn't. Here's the math."
- "Dropzone remembers your facts. We develop your judgment. Here's the difference."
- "After ten thousand decisions: the compounding curve that no competitor can show."

---

## Part 8: Risk and Open Questions

| Question | Impact | When to Resolve |
|---|---|---|
| Can F4 (compounding proof) be demonstrated convincingly with synthetic data? | High — this is the thesis | Test during v4.0 Phase 4 build |
| How realistic does the cross-domain discovery (F5) need to be? | High — if it looks scripted, it backfires | Design the seed data scenario carefully |
| Does ATT&CK mapping (F1) require technique-specific detection logic? | Medium — don't over-engineer | Start with taxonomy labels only, add logic later |
| Will 15-20 seed alerts make the demo too long for 15 minutes? | Medium — demo flow matters | Design a "fast path" (5 alerts) and "deep path" (15 alerts) |
| Is "Decision Intelligence" a recognized category? | Low — we're creating it | Gartner doesn't have it yet — that's an opportunity |

---

*SOC Copilot — Product Strategy & Value Feature Roadmap v1 | February 26, 2026*
*Three axes of compounding. Nine value features. One thesis: institutional judgment that appreciates with use.*
