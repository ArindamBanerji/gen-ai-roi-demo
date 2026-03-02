# SOC Copilot — Product Roadmap

## Compounding Decision Intelligence Platform

v3.0 → v7.5 · Security · Supply Chain · Financial Services

Dakshineshwari LLC · February 2026 · Confidential

---

## The Core Claim

Every AI tool on the market makes better decisions on day one. **This platform makes better decisions on day one thousand — because every verified decision writes back to a knowledge graph that makes every subsequent decision richer.**

The result is not just automation. It is an enterprise AI system that develops firm-specific institutional judgment over time — the same trajectory a smart new analyst follows, except it operates at machine scale and never loses what it learns.

**The mechanism: three axes of compounding intelligence.**

| Axis | What Accumulates | What Changes |
|---|---|---|
| **Graph Accumulation** | New types of knowledge — org changes, threat campaigns, compliance calendars, vendor data | Discovery surface grows as n^2.3 (super-quadratic) |
| **Context Fine-Tuning** | Verified outcomes calibrate the scoring matrix to firm-specific patterns | Weights evolve. Accuracy: 68% → 89% from calibration alone. |
| **Capability Extension** | Cross-graph discovery creates new scoring dimensions the original design didn't contain | The system extends its own evaluation criteria autonomously |

**The platform is domain-agnostic:** the same core infrastructure — loops, eval gates, discovery sweep, audit trail — runs security operations today and can run supply chain procurement or financial services compliance with a new domain module and domain graph. Adding a vertical is a configuration problem, not an infrastructure problem.

### Competitive Position: Decision Intelligence

The AI SOC market has 40+ players (IDC, February 2026). Our positioning is distinct from both legacy SOAR and the new wave of AI SOC Analysts:

| | SOAR (Torq, Swimlane) | AI SOC Analyst (Dropzone, Intezer) | **Decision Intelligence (Us)** |
|---|---|---|---|
| Core | Workflow orchestration | Per-alert LLM reasoning | Graph attention + learning loops |
| Axis 1 | ✗ | Flat fact store | ✓ New graph domains compound |
| Axis 2 | ✗ | ✗ | ✓ Weights calibrate from outcomes |
| Axis 3 | ✗ | ✗ | ✓ New scoring dimensions discovered |
| Moat | Integrations (replicable) | LLM quality (rented) | Firm-specific graph (owned) |

**Key differentiator from Dropzone AI (closest competitor):** Dropzone's "Context Memory" accumulates facts about the environment. Our system accumulates judgment — calibrated weights, discovered relationships, new scoring dimensions. Their system improves what the LLM reads. Ours improves how the system reasons. The moat is model-independent and firm-specific.

| **14 / 18** | **3** | **n²·³** | **3** |
|---|---|---|---|
| Capabilities live today | Cross-layer learning loops | Discovery surface growth | Verticals — same architecture |

---

## Version Timeline — At a Glance

| Version | Timeline | Theme | Deployment | Status |
|---|---|---|---|---|
| **v3.0** | Complete | **Three loops. Auditable. Connected.** | Local demo | ✅ Complete |
| **v3.2** | Complete | **Platform core. Multi-copilot ready.** | Local demo | ✅ Complete |
| **v4.0** | Building now | **Your tools, our decisions. Compounding proved.** | Docker + Hosted demo | 🔨 Building |
| **v4.5** | After v4.0 | **INOVA MVP + Cross-domain discovery.** | Hosted demo (customer-accessible) | Designed |
| **v5.0** | Months 1–3 | **Validated POC — real data.** | Cloud pilot (INOVA) | Designed |
| **v6.0** | Months 4–6 | **Production — single tenant.** | Production (SLA-backed) | Planned |
| **v6.5** | Months 6–9 | **Flash Tier + full streaming.** | Production + streaming | Planned |
| **v7.0** | Months 9–15 | **Multi-tenant platform. S2P + FinServ copilots.** | Multi-tenant | Roadmap |
| **v7.5** | Months 15–24 | **Partner network — MSSP-ready.** | Partner-deployed | Vision |

**Timeline note:** Months are relative from first production customer agreement. v3.x and v4.x are available now as demonstrations. v4.0 and v4.5 will be hosted on a VPS for prospect self-service access. v5.0 requires a data processing agreement and HIPAA BAA. v6 and beyond require production SLA commitments.

---

## Version Details

### v3.0 — Three Loops. Auditable. Connected. [Complete]

Proves all core compounding intelligence capabilities — live code, working demo.

**Audience:** CISOs, VCs, Technical evaluators

**What's Included:**
- Three cross-layer learning loops (Situation Analyzer, AgentEvolver, RL Reward/Penalty)
- Live Neo4j context graph — 47 nodes traversed per alert decision
- Six-factor transparent decision breakdown: time saved, cost avoided, residual risk
- Policy conflict detection — automatic resolution with full audit trail
- Binding structural quality gates — enforces correctness before any action executes
- SHA-256 hash-chained tamper-evident evidence ledger
- Live Pulsedive threat intelligence connector
- ROI calculator with CFO-ready savings projection

**Value Delivered:**
- Demonstrates structural differentiation from Gen 1/2 SOC tools — visible, live, in 15 minutes
- Audit trail satisfies compliance requirements out of the box
- Decision transparency removes the 'black box' objection before it is raised

**Deployment:** Local demo only. Runs on developer laptop.

---

### v3.2 — Platform Core. Multi-Copilot Ready. [Complete]

Refactored for platform scale. The domain-agnostic substrate that makes every future vertical a configuration problem, not an infrastructure problem.

**Audience:** Technical evaluators, Platform VCs, Consulting partners

**What's Included:**
- core/ infrastructure layer extracted — UCL resolution, state management, graph write utilities shared across all domains
- domains/soc/ module — SOC copilot runs as a first-class domain plugin, not a monolith
- domain_registry.py — runtime domain selection; second domain copilot is a new module, not a new codebase
- state_manager.py — clean migration path for Live Graph (v4 LG1–LG4 phase)
- Frontend domain.ts — domain-specific labels, metrics, and tab titles isolated from platform UI

**Value Delivered:**
- Technical due diligence answer to 'how do you add verticals?': show domains/ directory, show domain_registry.py. It is already designed.
- Platform VCs: the multi-tenant, multi-vertical thesis has working code behind it today

**Deployment:** Local demo only. No functional change from v3.0 — refactoring only.

---

### v4.0 — Your Tools, Our Decisions. Compounding Proved. [In Build]

Proves the platform connects to the customer's existing stack — and makes the compounding thesis visible live. This is the version that answers both "can it work with our data?" and "show me the compounding curve."

**Audience:** CISOs with existing tool investments, VCs, MSSPs, Technical evaluators

**What's Included:**

*Phase 1–4 (Platform):*
- UCL Connector pattern — one interface for N data sources (Pulsedive, GreyNoise, CrowdStrike mock)
- MITRE ATT&CK alignment — every alert carries technique ID and tactic classification
- Realistic alert corpus — 15-20 alerts across 5 situation types (travel/VPN, credential access, threat intel, behavioral anomaly, cloud/infra)
- Multi-source threat intelligence dashboard — cross-source correlations visible in real time
- Live graph persistence — decisions survive backend restarts, graph accumulates across sessions
- Docker deployment package — partner self-service demo in under 60 seconds
- Cross-source query intelligence — Tab 1 queries span all connected sources

*Phase 5 (Compounding Proof):*
- Investigation narrative — plain-English decision summary referencing ATT&CK, calibration history, and confidence reasoning
- Visible compounding curve — weight evolution chart + confidence trajectory over decisions. "Decision #1: 72%. Decision #8: 91%. Here's exactly what changed."
- Asymmetric trust curve — 20:1 penalty/reward visualized. System earns trust slowly, loses it fast. Automatic human-routing after incorrect decisions.
- Before/after comparison — same alert type triaged early vs. late, with explicit explanation of what the graph learned

**Value Delivered:**
- Directly answers 'can this work with our data?' — three data source types demonstrated
- MITRE ATT&CK language matches what every SOC team already uses
- **Compounding proof is live, not claimed.** The demo shows the weight matrix shifting, confidence rising, and trust recovering — in 15 minutes. No competitor can demonstrate this.
- Docker package enables partner-led demos without engineering involvement
- The "three axes" story becomes visible: graph accumulation (multi-source), context fine-tuning (weight evolution), and capability extension (set up for v4.5 discovery)

**Deployment:** Docker + **Hosted demo on VPS.** Prospects can access a live instance via URL — no local setup required. Demo resets daily. See deployment strategy v3 for hosting details.

**Gate:** Docker package tested. Compounding curve visible in 15-minute walkthrough. Three-source cross-correlation working. Tag v4.0. **Record Loom v3 on this version.**

---

### v4.5 — INOVA Healthcare MVP + Cross-Domain Discovery. [Designed]

Architectural depth for enterprise healthcare deployment. Proves compounding claims with the live cross-domain discovery moment.

**Audience:** Healthcare CISOs, HIPAA-covered entities, Healthcare VCs, Technical leads

**What's Included:**
- UCL entity resolution service — raw IOCs governed into aligned graph entities before compounding
- TRIGGERED_EVOLUTION and CALIBRATED_BY as traversable, auditable relationships
- Cross-graph discovery sweep — autonomous relevance computation across Decision History × Threat Intelligence domain pair
- **Cross-domain discovery demo moment — the Singapore + CFO + threat spike scenario, live.** jsmith confidence drops from 89% to 34% as the system discovers a connection nobody programmed. New scoring dimension (role_recency_risk) emerges autonomously.
- Health-ISAC mock connector + live CISA KEV feed — healthcare-specific threat intelligence
- Loop 3 surfaced explicitly as governing RL signal with compliance traversal modal
- HIPAA-framed evidence ledger — 45 CFR §164.530(j) export format, SHA-256 hash per decision
- Flash Tier pre-filter mimic — synthetic batch feed proves 60-70% volume reduction

**Value Delivered:**
- **Axis 3 (Capability Extension) proved live.** The system extends its own scoring matrix from operational experience. "Nobody programmed this rule. The system discovered it."
- Healthcare-specific discovery: Royal ransomware campaign × APAC travel login pattern — found automatically, zero analyst prompting
- HIPAA compliance audit trail at decision level, not just infrastructure level
- Flash Tier mimic gives INOVA a validated architecture before committing to streaming infrastructure

**Deployment:** Hosted demo (customer-accessible). INOVA-specific demo instance with healthcare seed data. Same VPS hosting as v4.0 but separate instance with healthcare configuration.

**Gate:** Cross-domain discovery produces the role-change × threat-spike finding live. HIPAA export verified. Flash Tier mimic shows 60-70% reduction. Tag v4.5.

---

### v5.0 — Validated POC. Real Data. [Designed]

First real customer data processed safely. The architecture meets the real world.

**Audience:** INOVA SOC team, INOVA CISO, Compliance officers

**What's Included:**
- PII/PHI redaction middleware — config-driven, audited, before any graph write or LLM call
- Splunk HEC ingest endpoint — INOVA's real alerts flow into the triage pipeline
- Okta SAML authentication — role-based access (SOC Analyst, Manager, CISO)
- Cloud deployment (GCP Cloud Run or AWS ECS) — no longer running on a laptop or VPS
- Secret Manager integration — no more .env files
- ATT&CK coverage heatmap — which techniques has the system triaged, with what confidence? SOC maturity metric for the board.
- Shift handoff intelligence — "here's what changed since your last shift." Graph doesn't forget at shift change.
- 100+ real INOVA alerts processed in controlled pre-production environment

**Value Delivered:**
- Proves the architecture holds on real data without compliance exposure
- INOVA SOC team experiences the system with their actual alert types
- ATT&CK heatmap provides the board-level metric CISOs need
- Shift handoff proves institutional knowledge survives organizational events
- Compounding curve now shows real data progression, not synthetic

**Deployment:** Cloud pilot (GCP Cloud Run + Neo4j Aura Professional). Pre-production, not SLA-backed.

**Gate:** BAA signed. PHI redaction verified (manual audit or pen test). 100+ real alerts processed. INOVA SOC team walkthrough on real data.

---

### v6.0 — Production. Single Tenant. [Planned]

SLA-backed production deployment. Human authority gates. ServiceNow live.

**Audience:** First production customer (INOVA), CISO, SOC Operations

**What's Included:**
- Multi-AZ high availability — 99.5% monthly uptime SLA
- Configurable confidence thresholds per alert type — CISO-adjustable, fully audited
- Live ServiceNow ticket creation — automated incident creation with full decision context
- Circuit breakers on all connectors — graceful fallback to cached data on source failure
- Disaster recovery — Neo4j snapshot restore < 30 minutes RTO

**Value Delivered:**
- SOC Copilot becomes part of the daily operations stack
- Every autonomous action is bounded — confidence gates define what requires human approval
- SLA means the platform is a committed operational resource, not a best-effort system
- Compounding curve now measured in months, not minutes — real institutional judgment developing

**Deployment:** Production (SLA-backed). GCP Cloud Run multi-region + Neo4j Aura Enterprise.

**Gate:** SLA signed. Human authority gate scope agreed with INOVA CISO. Neo4j production deployment model decided. DR tested.

---

### v6.5 — Flash Tier + Full Streaming. [Planned]

Pre-ingestion intelligence at 1.5TB+/day. The filter itself compounds via write-backs.

**Audience:** Enterprises with large-scale telemetry, Production operations teams

**What's Included:**
- Streaming pre-ingestion pipeline (GCP Pub/Sub or AWS Kinesis — transport abstracted)
- Multi-factor forensic scoring (0–100) applied before alert reaches analyst queue
- 60–70% volume reduction (validated by v4.5 Flash Tier mimic before infrastructure investment)
- Flash Tier write-back chain: downstream corrections improve the pre-filter via TRIGGERED_EVOLUTION
- HIPAA-safe: PII/PHI stripped at ingestion, before graph or LLM sees any data
- Fast-path bypass for ransomware/APT patterns

**Value Delivered:**
- Pre-filter that compounds: the more analyst corrections, the less noise
- Reduces LLM API cost proportionally — only enriching alerts that matter
- Architecture already validated by v4.5 mimic — this is execution, not experiment

**Deployment:** Production + streaming infrastructure.

**Gate:** v6.0 in production for 30+ days (establishes baseline). Streaming infrastructure provisioned.

---

### v7.0 — Multi-Tenant Platform. S2P + FinServ Copilots. [Roadmap]

Multiple enterprise customers, isolated graphs. Supply chain and financial services copilots activated.

**Audience:** 2nd/3rd enterprise customers, VCs, MSSPs, S2P/FinServ prospects

**What's Included:**
- Per-tenant graph isolation — each customer's context graph is physically separate
- Self-service tenant onboarding — configure connectors, thresholds, users
- Supply Chain S2P copilot: 6-factor PO scoring, auto-approve/flag/dual-source actions, geopolitical risk discovery
- Financial Services copilot: regulatory compliance monitoring, position analysis, cross-regulatory discovery
- Cross-tenant meta-graph (opt-in) — anonymized pattern sharing across the customer network
- Domain framework already live from v3.2 — S2P is domains/supply_chain/ module + domain graph, not new infrastructure

**Value Delivered:**
- Second customer inherits the full connector library, platform infrastructure, and compliance machinery
- Each new domain graph added makes every existing domain smarter — n(n-1)/2 discovery surface growth
- Meta-graph opt-in: every new customer enriches the network; network enriches every customer

**Deployment:** Multi-tenant (Model A for HIPAA tenants, Model C for others).

**Gate:** Second enterprise customer signed. Graph isolation verified. Pricing model defined.

---

### v7.5 — Partner Network — MSSP-Ready. [Vision]

MSSPs and consulting partners deploy for their clients. The platform scales through the channel.

**Audience:** MSSPs, Systems integrators, Consulting partners

**What's Included:**
- MSSP partner portal — deploy and manage multiple client instances from one dashboard
- Client data never leaves client environment — partner deploys, client owns graph
- Docker bundle for partner deployment — v4.0 Docker package, now multi-tenant aware
- Meta-graph enrichment across MSSP client base (opt-in)
- Partner certification program

**Value Delivered:**
- MSSPs offer compounding intelligence as a managed service — differentiated from commodity SOC
- The moat scales through the partner network — accelerates graph accumulation beyond direct sales

**Deployment:** Partner-deployed, self-service.

**Gate:** v7.0 multi-tenant working. Partner portal MVP. Pricing model for partner channel.

---

## Cross-Vertical Capability Map

| Capability | Security (SOC) | Supply Chain (S2P) | Financial Services |
|---|---|---|---|
| Domain-agnostic platform core | ✅ v3.2 | ✅ v3.2 | ✅ v3.2 |
| Context graph — live decision enrichment | ✅ v3.0 | v7.0 | v7.0 |
| Three learning loops | ✅ v3.0 | v7.0 | v7.0 |
| MITRE ATT&CK alignment | ✅ v4.0 | N/A | N/A |
| Multi-source connector pattern | ✅ v4.0 | v7.0 | v7.0 |
| Visible compounding proof | ✅ v4.0 | v7.0 | v7.0 |
| Asymmetric trust governance | ✅ v4.0 | v7.0 | v7.0 |
| Investigation narrative | ✅ v4.0 | v7.0 | v7.0 |
| UCL entity resolution | ✅ v4.5 | v7.0 | v7.0 |
| Cross-domain discovery (Axis 3) | ✅ v4.5 | v7.0 | v7.0 |
| Decision economics ($/time/risk) | ✅ v3.0 | v7.0 | v7.0 |
| Tamper-evident audit trail | ✅ v3.0 | v7.0 | v7.0 |
| Compliance framing (HIPAA/SOX/NIS2) | ✅ v4.5 | v7.0 | v7.0 |
| ATT&CK coverage heatmap | v5.0 | N/A | N/A |
| Shift handoff intelligence | v5.0 | v7.0 | v7.0 |
| Pre-ingestion volume filter — validated | ✅ v4.5 | v7.5 | v7.5 |
| Pre-ingestion volume filter — production | v6.5 | v7.5 | v7.5 |
| Multi-tenant isolation | v7.0 | v7.0 | v7.0 |

---

## Why the Moat Is Structural

**The competitive advantage is not the model. It is the layer you own.**

- **Firm-specific:** discoveries emerge from this firm's operational history — identical architecture at a competitor produces different intelligence because their patterns, exceptions, and threat landscape differ.

- **Temporally irreversible:** each discovery was enabled by a specific graph state at a specific moment. That state no longer exists and cannot be replayed.

- **Model-independent:** the context graph, TRIGGERED_EVOLUTION write-backs, and cross-domain discoveries survive any LLM transition. The moat is in the layer you own — the graph — not the layer you rent — the model.

- **Recursive:** discoveries feed future discoveries. The richer the graph, the more sophisticated the next discovery sweep. The system develops judgment about its own judgment.

- **Domain-agnostic:** the platform core is shared across all verticals. Every decision made in the SOC copilot makes the infrastructure that runs S2P and FinServ smarter.

**A competitor deploying today in any vertical does not start six months behind. They start at zero.**

### Against Specific Competitors

**vs. Torq ($1.2B):** Torq automates workflows. We develop judgment. Torq's system on day 1,000 runs the same playbooks as day 1 unless humans manually update them. Ours is a structurally different decision-maker.

**vs. Dropzone AI (Context Memory):** Dropzone accumulates facts about the environment. We accumulate institutional judgment. Their system improves what the LLM reads. Ours improves how the system reasons. When their LLM vendor raises prices or a competitor adopts the same model, Dropzone's advantage narrows. Ours is embedded in a firm-specific graph that cannot be replicated.

**vs. Intezer (Forensic AI):** Strong investigation depth (code analysis, sandboxing). No learning feedback loop. Day 1,000 investigates with the same reasoning as day 1.

---

*Dakshineshwari LLC · SOC Copilot Platform Roadmap v4 · February 2026 · Confidential*

*arindam@dakshineshwari.net · www.dakshineshwari.net*
