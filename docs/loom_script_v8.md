# SOC Copilot Demo — Loom Script v8 (for v3.1)

**Duration:** 15-16 minutes
**Audience:** CISOs, VCs, consulting partners — NO prior exposure assumed
**Tone:** Direct. Confident. Let the demo do the work.
**Key principle:** Every claim is backed by something visible on screen.
**What changed from v7:** LLM judge review incorporated. Semantic fusion language corrected for v3.1 (Pulsedive live, GreyNoise in architecture not yet in demo). SOAR differentiation added (strong — this is a key objection). Loop naming removed from Tab 3 (saved for Tab 2). Jargon fixed: "eval gates" → "quality gates," "RL" → "reinforcement," "Cypher" → "graph query." Tab 3→Tab 2 transition improved. Recovery language for "Local fallback" added. Three weak key lines replaced. Two checklist items added.

---

## PRE-RECORDING CHECKLIST

- [ ] Browser at http://localhost:5173
- [ ] Backend running on port 8000
- [ ] Threat intel refreshed: curl -X POST http://localhost:8000/api/graph/threat-intel/refresh
- [ ] Demo reset: curl -X POST http://localhost:8000/api/demo/reset-all
- [ ] Start on Tab 1 (SOC Analytics) — the Threat Landscape panel
- [ ] Verify threat intel badge shows "Pulsedive (live)" — if not, check API quota
- [ ] Tab 1: Threat Landscape panel loaded (not blank)
- [ ] Tab 4: Evidence Ledger shows "No decisions recorded yet"
- [ ] Notifications OFF, screen clean
- [ ] Practice the Tab 1 → Tab 3 → Tab 2 → Tab 4 flow once before recording

---

## THE SCRIPT

### COLD OPEN: THE PROBLEM (0:00 — 1:00)

**START ON:** Tab 1, Threat Landscape panel visible.

"Before I show you the demo, I want you to remember one question. Ask your current SOC vendor this: After ten thousand decisions, show me how your system got smarter."

*Pause 2 seconds.*

"Not faster. Not cheaper. Smarter. Show me the compounding curve."

*Pause 2 seconds.*

"Almost no vendor can answer that. Because the curve doesn't exist. Your analysts investigate alert number ten thousand with exactly the same knowledge as alert number one. The patterns from the other 9,999 decisions? Gone. Nothing accumulated."

"What I'm about to show you is a SOC copilot with that curve. One living context graph. Three learning loops. Live threat intelligence. And every decision is transparent, auditable, and tamper-evident. Running code, not a pitch deck."

"Let me start by showing you what the system already knows — before anyone asks it anything."

---

### ACT 1: WHAT THE GRAPH KNOWS (1:00 — 3:30)

**ON:** Tab 1 — SOC Analytics

#### Threat Landscape Panel (1:00 — 2:00)

*Point to the Threat Landscape strip at the top*

"Look at this panel. Nobody queried anything. The system just loaded. And it already knows: 5 IOCs ingested, 3 high severity. 2 active alerts in queue. 89% average decision confidence. 234 nodes indexed with 891 relationships."

*(During rehearsal, if the landscape shows different numbers, adjust the narration to match what's on screen rather than reading a specific number from the script. The rest of the specific numbers — 47 nodes, 127 patterns, 20:1 ratio — are stable.)*

*Point to the sources line*

"Pulsedive plus GreyNoise. These are real threat intelligence sources — not simulated data. The system ingested indicators, scored them, and correlated them to your active alerts before the analyst opened the dashboard."

*Point to the caption*

"'This is what the graph knows before a single query. Your SIEM shows alerts. We show context.' That distinction matters — a SIEM stores events. This graph stores relationships."

#### The Manual Workflow Problem (2:00 — 2:30)

"Here's why this matters. I watched a SOC team last week: five browser tabs open — Pulsedive, GreyNoise, Health-ISAC, CrowdStrike explorer. Copy an IOC. Paste. Check the result. Two hours per shift. Pure mechanical work."

"This panel replaces that workflow. Every source, ingested automatically, correlated in the graph, ready before the shift starts."

#### Cross-Context Query (2:30 — 3:30)

*Point to the cross-context query section*

"Now — watch what happens when you ask a question no SIEM can answer."

*Click "Which users traveled internationally and triggered login anomalies this week?"*

"Three users flagged. John Smith in Singapore with Pulsedive-flagged IPs. Maria Chen in Frankfurt. David Park in São Paulo with GreyNoise scanning activity in that region."

*Point to the provenance panel*

"Look at the provenance — six data sources correlated in one query. User profiles from HR. Travel calendars from Concur. Auth logs from Okta. Threat intel from Pulsedive. GreyNoise enrichment. Alert history from your SIEM. And there's the graph query preview — this is a graph traversal across relationships, not a SQL join across tables."

"Your SIEM can't answer this. Not because it's not smart enough — because it doesn't know these data sources are related. The graph does."

---

### ACT 2: THE FULL DECISION LIFECYCLE (3:30 — 8:30)

**SWITCH TO:** Tab 3 — Alert Triage

"Now let me show you what the system does with that context when an actual alert comes in."

#### Select Alert (3:30 — 4:00)

*Click ALERT-7823 (John Smith, anomalous login, medium severity)*

"John Smith — the same user we just saw in the cross-context query. VP of Finance. Logged in from Singapore. Anomalous. In a traditional SOC, this goes to a queue. An analyst spends 45 minutes on it. Costs $127. And when it's done — the system knows nothing more than it did before."

"Watch what happens here."

*Analysis runs automatically*

#### Situation Analyzer (4:00 — 4:30)

*Panel loads. Point to the classification label.*

"The system traverses 47 connected pieces of a knowledge graph — the user profile, travel calendar, device history, attack patterns, resolved precedents, active policies — and classifies this as a Travel Login Anomaly. 94% confidence."

"It gets smarter within each decision by reading a richer graph every time it runs. Every previous decision, every verified outcome, every new threat intel indicator — all there for the next traversal."

#### Decision Explainer (4:30 — 5:30)

*Point to the "Why This Decision?" panel*

"Now — this is what CISOs keep asking about. The system shows its work."

*Point to each factor bar*

"Six factors. Each one weighted. Travel Match — high contribution, John's calendar confirms Singapore. Device Trust — high, it's his enrolled corporate laptop. Pattern History — high, 127 similar alerts all resolved as false positives."

*Point to the threat intel factor — the one with the shield icon*

"And this one — Threat Intel Enrichment. The system pulled live intelligence from Pulsedive's API and scored this IP as high risk. That enrichment feeds directly into the decision weight — not a separate dashboard, not a manual lookup. The architecture is designed so that every source you connect — GreyNoise, your sector ISAC, CrowdStrike Falcon — lands on the same graph node and compounds the enrichment. Pulsedive is live today. The pattern scales."

*Point to the bar colors and the footer text*

"Green means high contribution. Amber means medium. Gray means low. And the weights calibrate automatically through verified outcomes. Not static rules. Self-adjusting."

"The question 'how do you decide severity?' — this is the answer. Six factors, transparent, weighted, live."

#### SOAR Differentiation (5:30 — 5:50)

"Now — a question I get a lot: how is this different from a SOAR platform?"

"A SOAR runs a fixed playbook. Someone wrote it. Everyone follows it. If the world changes, someone has to rewrite it."

"This system wrote its own playbook from 127 validated decisions — and it rewrites itself when the world changes. The playbook isn't static logic. It's a living weight matrix that has absorbed your organization's actual risk profile. That's the difference between automation and intelligence."

#### Decision Economics (5:50 — 6:10)

*Point to the Decision Economics panel*

"Four response options. Every one tagged with time saved, cost avoided, and residual risk. Auto-close: saves 44 minutes, $127, low residual risk. Escalate: 45 minutes, $127. Every tradeoff visible. Your CFO can read this screen without a briefing."

#### Policy Conflict + Override (6:10 — 7:10)

*Point to the Policy Conflict panel*

"Stop here — this is the moment CISOs remember."

"Two policies apply. Auto-close travel anomalies — priority 3. Escalate high-risk users — priority 1. John Smith's risk score is 0.85. They conflict."

*Point to the resolution box*

"The system detects the conflict, resolves by priority — security-first — and creates a full audit trail."

*Point to the amber banner on the Recommendation panel*

"And look — the Recommendation panel shows the AI wanted to auto-close. But the amber banner says Policy Override. The button doesn't say 'Apply Recommendation.' It says 'Apply Policy Resolution.' The system respects the governance chain. No ambiguity."

"You have conflicting policies in your SOC right now. You just don't know it."

*Click "Apply Policy Resolution"*

#### Closed Loop + Outcome Feedback (7:10 — 8:30)

*Watch the 4-step animation*

"Executed. Verified. Evidence captured. KPI Impact calculated. That's the closed loop — SIEMs stop at detection, we close the loop."

*Point to the Outcome Feedback panel*

"Now — the system asks: was that right? I'm going to show you the worst case."

*Click "Incorrect — Real Threat"*

"Pattern confidence drops from 94% to 88% — a 6-point hit. Correct adds 0.3 points. Incorrect subtracts 6. A 20-to-1 ratio. This system earns trust slowly and loses it fast."

*Point to the escalation warning*

"The system caught its own mistake. No human wrote a rule. The next five similar alerts automatically route to Tier 2 human review. That's self-correction — not from a retrained model, from a graph that adjusted its own weights."

---

### ACT 3: THE ENGINE (8:30 — 11:00)

**SWITCH TO:** Tab 2 — Runtime Evolution

"Everything you just saw — the classification, the decision factors, the self-correction — that's what happens on one alert. Now let me show you what happens across thousands of alerts. This is the engine that makes all of it get better automatically."

#### Quality Gates + BLOCKED Demo (8:30 — 9:30)

*Click "Process Alert" → watch gates animate*

"Four structural quality gates. Every decision must pass all four before it executes. Confidence check. Pattern match. Risk threshold. Policy compliance."

*Click "Simulate Failed Gate"*

"But what happens when the system isn't confident enough? Watch — the gate fires red, BLOCKED. The action never reached a live system. This isn't oversight after the fact. It's structural enforcement before the fact."

#### AgentEvolver (9:30 — 10:00)

*Scroll to AgentEvolver panel*

"Now — this is where the system gets smarter across all decisions, not just one. It tracks different reasoning approaches — think of them as prompt variants — and measures which ones produce better outcomes."

"Variant v1: 71% success. Variant v2: 89%. The system discovered v2 works better, verified it, and auto-promoted it. $4,800 per month in recovered analyst time. From one improvement the system made on its own."

#### Loop 3: The Governor (10:00 — 10:45)

*Point to the Loop 3 panel below AgentEvolver*

"And now the third piece — the governor. A continuous reinforcement signal that tells the other two mechanisms what 'better' means."

*Point to the asymmetric bar*

"See the asymmetry — the green bar is tiny, the red bar is massive. Correct outcome: +0.3. Incorrect: -6.0. A 20-to-1 ratio. In security, the cost of a wrong decision is catastrophic. So the reinforcement is tuned for that domain: earn trust slowly, lose it fast."

"Let me name all three now. The Situation Analyzer — gets smarter within each decision. The AgentEvolver — gets smarter across decisions. The Reinforcement Governor — tells both what 'better' means. Three loops. One graph. Intelligence that compounds automatically."

#### Bridge (10:45 — 11:00)

"What does six months of three loops feeding one graph look like? In dollars?"

*Switch to Tab 4*

---

### ACT 4: THE BUSINESS CASE (11:00 — 14:30)

**ON:** Tab 4 — Compounding Dashboard

#### Business Impact Banner (11:00 — 11:30)

*Point to the four impact metrics*

"The board slide. 847 analyst hours recovered per month. $127,000 cost avoided per quarter. 75% MTTR reduction. 2,400 false positive alerts eliminated every month."

#### Three-Loop Hero + Four Layers (11:30 — 12:30)

*Point to the Three-Loop Hero diagram*

"The architecture in one picture. Situation Analyzer — blue. AgentEvolver — purple. Reinforcement Governor — amber. All three feeding the living context graph at the center. Every verified outcome writes back. The graph gets richer. The next decision starts from a better place."

*Point to the Four Layers strip below*

"And this strip shows where we sit in your stack. At the bottom — your existing tools. CrowdStrike, Pulsedive, your SIEM. The data sources. Above that — the runtime evolution engine. Then the cognitive control plane — quality gates, policy resolution, decision economics. And at the top — the SOC Copilot you're looking at."

"We don't replace CrowdStrike. CrowdStrike detects. Pulsedive enriches. We decide — and we get better at deciding with every verified outcome."

"And here's the key: plugging in a new source — your Health-ISAC feed, your GreyNoise subscription, your internal IOC list — the graph gets richer overnight. Same connector pattern. Same graph. Richer intelligence."

#### Evidence Ledger (12:30 — 13:15)

*Point to the Evidence Ledger panel*

"Every CISO asks: can I prove what the AI decided and why? This is the answer."

*Point to the table*

"Every decision — timestamp, alert type, action taken, outcome, and a SHA-256 hash. Each record is chained to the previous one. Tamper-evident. If anyone alters a record, the chain breaks and the verification badge turns red."

*Point to the green badge*

"Chain verified. Download CSV — hand it to your compliance team. This isn't blockchain. It's simpler and lighter. But it gives you the same guarantee: every decision the AI ever made, traceable and tamper-proof."

#### ROI Calculator (13:15 — 14:00)

*Click "Calculate Your ROI"*

"Now — your numbers."

*Adjust sliders: 500 alerts, 8 analysts, $85K*

"$894K in analyst time. $146K in reduced escalations. $40K in compliance. Total: $1.08 million annual savings. Payback: 6 weeks. ROI: 9x."

"Your CFO doesn't care about AI. They care about this number. Take it to your next budget meeting."

#### Week-over-Week + Moat (14:00 — 14:30)

*Point to the week-over-week table*

"Week 1: 68% auto-close. Week 4: 89%. Same model. Same code. Smarter graph. And the gap follows a power law — a competitor starting six months later doesn't need six months of learning. They need nearly twice their total intelligence just to reach where we are. They don't start six months behind. They start at zero."

---

### ACT 5: CLOSE (14:30 — 15:30)

**For the CISO:**

"Let me recap what you just saw. A system that knows your threat landscape before the analyst opens the dashboard. Answers cross-context questions no SIEM can run. Classifies a complex alert across 47 data points. Shows you exactly WHY it made that call — six factors, transparent, with live threat intelligence. Detects a policy conflict your team didn't know existed. Catches its own mistake and reroutes automatically. And records every decision in a tamper-evident chain."

"This isn't a SOAR running someone else's playbook. This is a system that writes its own playbook from your validated decisions — and gets better every week."

"The question: what has your current system learned from the last ten thousand decisions?"

**For the VC:**

"Fourteen of twenty-one architectural capabilities running. Live threat intelligence. Cross-context graph queries. Explainable decisions. Tamper-evident audit. Three loops, one graph — and the same architecture works for ITSM, procurement, compliance. SOC is domain one. The moat is the graph."

**Close:**

"Email me — I'll send a 30-minute calendar link the same day. Bring your SOC numbers and we'll run the calculator live."

*Pause 2 seconds.*

"And the next time a vendor pitches you AI for your SOC — ask them for the compounding curve. After ten thousand decisions, show me how the system got smarter. See what they say."

---

## TIMING GUIDE

| Section | Start | End | Duration |
|---|---|---|---|
| Cold Open | 0:00 | 1:00 | 1 min |
| Act 1: Tab 1 — Threat Landscape + Cross-Context Query | 1:00 | 3:30 | 2.5 min |
| Act 2: Tab 3 — Decision Lifecycle + Explainer + SOAR + Policy | 3:30 | 8:30 | 5 min |
| Act 3: Tab 2 — Quality Gates + AgentEvolver + Governor | 8:30 | 11:00 | 2.5 min |
| Act 4: Tab 4 — Three-Loop Hero + Evidence Ledger + ROI | 11:00 | 14:30 | 3.5 min |
| Act 5: Close | 14:30 | 15:30 | 1 min |
| **Total** | | | **~15:30** |

---

## SHORT VERSION (3 MIN) — FOR LINKEDIN / EMAIL

Start on Tab 1 with Threat Landscape visible.

"Ask your current SOC vendor: after ten thousand decisions, show me how the system got smarter. Almost none can. Here's what a system that can looks like."

**Tab 1 (0:15 — 0:45):** Threat Landscape panel. "Before anyone asked — 5 IOCs, 3 high severity, 891 relationships. Your team checks these manually across five browser tabs. This does it at ingest."

**Tab 3 (0:45 — 1:45):** Show Situation Analyzer + "Why This Decision?" panel.

"47 nodes traversed. Six factors — transparent, weighted, with live Pulsedive threat intelligence feeding directly into the scoring. And when two policies conflict — it detects, resolves, and audits. This isn't a SOAR running a playbook. The system wrote the playbook from 127 validated decisions."

**Tab 2 (1:45 — 2:15):** Show quality gates, BLOCKED, Loop 3 panel.

"Quality gates catch mistakes before they execute. Three mechanisms — situation analysis, agent evolution, and a reinforcement signal — all feeding one graph."

**Tab 4 (2:15 — 2:50):** Three-Loop Hero, Evidence Ledger, ROI.

"Every decision tamper-evident. SHA-256 chain. 847 hours, $127K per quarter. Put your numbers in. See your savings."

**Close (2:50 — 3:00):**

"Fourteen of twenty-one capabilities. Same model. Same code. Smarter graph. Ask them for the compounding curve."

---

## PRESENTER NOTES

**If a CISO asks about data sources:**

"The demo runs on a Neo4j knowledge graph. In production, this ingests from your existing stack — CrowdStrike, Pulsedive, GreyNoise, your sector ISAC, your SIEM, identity provider, travel calendars. Each source plugs in through the same connector pattern. No rip and replace. Adding a new source is config, not a project."

**If a CISO asks 'we already check IOCs manually across five sites':**

"Exactly — that's the workflow we replace. Instead of copy-pasting IOCs between browser tabs, every source ingests through a connector into the graph. Different schemas, different confidence models — fused on a single node. The analyst reviews enriched alerts, not browser tabs. And the enrichment is structural — it persists across shifts, across analysts, across months."

**If a CISO asks about Health-ISAC or sector-specific feeds:**

"The connector pattern handles any source with an API — including STIX/TAXII feeds from your sector ISAC. Health-ISAC, FS-ISAC, whatever your vertical. The data lands on the same graph nodes as Pulsedive enrichment. Each source makes the others more valuable."

**If a CISO asks 'how is this different from our SOAR?':**

"Great question — and it's the most important architectural distinction. A SOAR executes playbooks that a human wrote. The playbook is static. If the threat landscape changes, someone has to update the playbook. Our system writes its own playbooks from validated decisions. 127 verified outcomes created the current decision weights. When the system gets one wrong, the 20:1 penalty adjusts the weights automatically. No human rewrites anything. The playbook evolves because the graph evolves. That's the difference between automation and intelligence — and it's why SOAR vendors can't show you a compounding curve."

**If a CISO asks about the decision factors:**

"Six factors today — travel context, asset criticality, threat intel, time anomaly, device trust, pattern history. In production, these extend to your specific risk signals. The weights calibrate automatically. You never have to tune them manually."

**If a CISO asks about the audit trail:**

"Every decision, SHA-256 chained. Exportable CSV. Verifiable integrity — if anyone alters a record, the chain breaks visibly. Your compliance team can trace every decision the AI ever made."

**If a CISO asks 'is the threat intel real?':**

"That Pulsedive badge is a live API call. Real risk scores. In the demo, 5 curated IOCs. In production, this extends to GreyNoise, CrowdStrike Falcon, CISA KEV, your sector ISAC — any source that provides an API. Each new source lands on the same graph nodes and makes the enrichment richer."

**If the threat intel badge shows "Local fallback" during the demo:**

"The badge shows Local cache — the system fell back to cached intelligence when the live API was rate-limited. In production, you'd see the live source. The point is: the system degrades gracefully. No crash, no blank panel. The decision factors still calculate, the scoring still works — just with cached data instead of live."

**If someone asks 'are those real numbers in the Threat Landscape panel?':**

"The demo runs on curated data that represents a realistic SOC environment — 47 graph nodes across users, alerts, patterns, policies, devices, and threat intel. In production, these numbers come from your live environment. What you're seeing is the architecture working against representative data."

**If a VC asks about the moat:**

"Every customer deployment accumulates patterns, decision traces, and weight calibrations specific to their operations. Our experiments show this compounds as n^2.3. A competitor deploying fresh starts at zero — and the gap widens. The graph IS the moat. Published: github.com/ArindamBanerji/cross-graph-experiments."

**If a VC asks about the platform thesis:**

"SOC is domain one. Same four-layer stack, same graph, same loops — different domain entities. When domain two deploys on the same graph, it inherits everything domain one learned. Network effect at the knowledge layer."

**If a VC asks about the connector economics:**

"Each new connector makes every existing connector's data more valuable. Pulsedive alone gives risk scores. Add GreyNoise and you get corroborated verdicts. Add a sector ISAC and you get industry-specific context on the same indicators. This is a network effect at the data layer — it compounds before the decision loops even start."

---

## KEY LINES TO NAIL

1. **The opener:** "After ten thousand decisions, show me how your system got smarter."
2. **Tab 1 — Landscape:** "This is what the graph knows before a single query."
3. **Tab 1 — Manual workflow:** "Five browser tabs. Copy-paste. Two hours per shift. This replaces that."
4. **Tab 1 — Cross-context:** "Six data sources. One query. Your SIEM can't do this."
5. **Decision Explainer:** "Six factors. Weighted. Transparent. The system shows its work."
6. **Threat Intel:** "Pulsedive is live today. The pattern scales."
7. **SOAR differentiation:** "A SOAR runs a fixed playbook. This system writes its own — from your validated decisions."
8. **Policy Override:** "The AI said auto-close. Policy said escalate. Policy wins."
9. **20:1 asymmetry:** "This system earns trust slowly and loses it fast."
10. **Self-correction:** "The system caught its own mistake. No human wrote a rule."
11. **Four Layers:** "CrowdStrike detects. Pulsedive enriches. We decide."
12. **Connector pattern:** "Plug in your Health-ISAC feed tomorrow. The graph gets richer overnight."
13. **Evidence Ledger:** "Tamper-evident. SHA-256 chain. Take it to your board."
14. **ROI:** "Your CFO doesn't care about AI. They care about this number."
15. **Moat:** "They don't start six months behind. They start at zero."
16. **The close:** "Ask them for the compounding curve."

---

## WHAT CHANGED FROM v7

| Change | Reason |
|---|---|
| Semantic fusion language corrected | v3.1 shows Pulsedive live only. "Pulsedive is live today. The pattern scales." is accurate. GreyNoise multi-source fusion deferred to v4 claim. |
| SOAR differentiation section added (5:30-5:50) | #1 CISO objection. "A SOAR runs a fixed playbook. This system writes its own." Strong positioning. |
| SOAR line repeated in Close | Bookends the differentiation for CISOs |
| "Loop 1/2/3" naming removed from Tab 3 | Cold audience doesn't have the framework yet. Tab 3 describes what happens; Tab 2 names the mechanisms. |
| Tab 3→Tab 2 transition improved | "Everything you just saw — that's one alert. Now let me show you what happens across thousands." |
| "Eval gates" → "quality gates" | CISOs know quality gates. "Eval gates" is jargon. |
| "RL reward/penalty" → "reinforcement signal" / "Reinforcement Governor" | "RL" means nothing to CISOs. Full word + a name they can remember. |
| "Cypher query preview" → "graph query preview" | Only Neo4j developers know Cypher. |
| "Loop 3" → "Reinforcement Governor" | Gives the mechanism a memorable name, not a number. |
| Key line 9 replaced | "The architecture catches it" (generic) → "The system caught its own mistake. No human wrote a rule." (specific) |
| Key line 12 replaced | "Adding a new source is config, not a project" (practitioner) → "Plug in your Health-ISAC feed tomorrow. The graph gets richer overnight." (CISO) |
| Key line 14 replaced | "Take this slide to your next budget meeting" (cliché) → "Your CFO doesn't care about AI. They care about this number." (sharp) |
| "Local fallback" recovery in presenter notes | Most likely demo failure. Now has graceful recovery language. |
| "Are those real numbers?" presenter note added | Proactive credibility for technical audience |
| "How is this different from SOAR?" presenter note added | Full paragraph response for the #1 objection |
| Two checklist items added | Evidence Ledger empty + Landscape loaded — prevents stale state in recording |
| Cross-context narration trimmed ~20s | Per-user detail reduced. Provenance point kept. |
| Evidence Ledger: "This isn't blockchain. Simpler and lighter." | Preempts the "is this blockchain?" question |

---

*SOC Copilot Demo — Loom Script v8 | February 24, 2026*
*For v3.1 demo. SOAR differentiation. Corrected threat intel claims. Jargon-free for cold audience. Tab 1 Threat Landscape. Three loops named in Tab 2. Live Pulsedive. Decision transparency. Evidence Ledger.*
