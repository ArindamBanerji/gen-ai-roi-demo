# SOC Copilot — Product Roadmap

## Compounding Decision Intelligence Platform

v3.0 → v7.5 · Security · Supply Chain · Financial Services

Dakshineshwari LLC · March 2026 · Confidential

> **Changes from v5:**
> (1) v4.0 renamed v4.1 — tagged and complete. Language: "product preview" not "demo."
> (2) v4.5 completely redesigned: INOVA, Docker, VPS removed. Simulation mode, NarrativeProvider, cross-graph discovery (gated) added. CalibrationProfile in GAE preamble.
> (3) v5.0 redefined: "GAE as Platform + SOC as Product." Evaluation, ablation, institutional judgment, realistic data, ROI. Three-repo milestone (GAE + ci-platform + SOC).
> (4) v5.5 added: Docker + VPS deployment. Production event bus. Schema drift detection.
> (5) v6.0 redefined: First real-customer POC. INOVA, Splunk, SAML, PII redaction moved here.
> (6) New capabilities from design decisions session: CalibrationProfile, evaluation framework, ablation, institutional judgment metrics, NarrativeProvider protocol, domain schema format.

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

**The platform is domain-agnostic:** the same core infrastructure — graph attention engine, eval gates, discovery sweep, audit trail — runs security operations today and can run supply chain procurement or financial services compliance with a new domain module and domain graph.

### Competitive Position: Decision Intelligence

| | SOAR (Torq, Swimlane) | AI SOC Analyst (Dropzone, Intezer) | **Decision Intelligence (Us)** |
|---|---|---|---|
| Core | Workflow orchestration | Per-alert LLM reasoning | Graph attention + learning loops |
| Axis 1 | ✗ | Flat fact store | ✓ New graph domains compound |
| Axis 2 | ✗ | ✗ | ✓ Weights calibrate from outcomes |
| Axis 3 | ✗ | ✗ | ✓ New scoring dimensions discovered |
| Moat | Integrations (replicable) | LLM quality (rented) | Firm-specific graph (owned) |

---

## Architecture — Open Engine, Proprietary Intelligence

| Layer | Repository | License | Purpose |
|---|---|---|---|
| **Graph Attention Engine (GAE)** | graph-attention-engine | Apache 2.0 (open-source) | Mathematical computation substrate — scoring, learning, convergence, evaluation |
| **CI Platform** | ci-platform | Apache 2.0 | Shared infrastructure — domain config, schema validation, event bus, entity resolution |
| **Domain Copilots** | soc-copilot, s2p-copilot, etc. | Proprietary | Domain expertise — factors, seed data, connectors, deployment |

**Why open-source the engine?** The mathematical foundation is [published and peer-reviewable](https://www.dakshineshwari.net/post/cross-graph-attention-mathematical-foundation-with-experimental-validation). The competitive advantage lives in the firm-specific knowledge graph and domain expertise, not in the equations. A competitor with the same engine but no accumulated graph starts at zero.

---

## Version Timeline — At a Glance

| Version | Theme | Deployment | Status |
|---|---|---|---|
| **v3.0** | **Three loops. Auditable. Connected.** | Local | ✅ Complete |
| **v3.2** | **Platform core. Multi-copilot ready.** | Local | ✅ Complete |
| **v4.1** | **Graph Attention Engine. Compounding proved.** | Local | ✅ **Tagged** |
| **v4.5** | **Make It Real — simulation, narrative, discovery.** | Local (product preview) | 🔨 Next |
| **v5.0** | **GAE as Platform + SOC as Product.** | Local (evaluated product) | Designed |
| **v5.5** | **Deployable. Docker + VPS.** | Hosted (customer-accessible) | Designed |
| **v6.0** | **First customer POC — real data.** | Cloud pilot | Planned |
| **v6.5** | **Flash Tier + streaming.** | Production + streaming | Planned |
| **v7.0** | **Multi-tenant. S2P + FinServ copilots.** | Multi-tenant | Roadmap |
| **v7.5** | **Partner network — MSSP-ready.** | Partner-deployed | Vision |

**Timeline note:** Months are relative from first production customer agreement. v3.x through v5.x are self-funded development. v5.5 produces a hosted product preview accessible to prospects. v6.0 requires a customer data processing agreement.

---

## Version Details

### v3.0 — Three Loops. Auditable. Connected. [Complete]

Proves all core compounding intelligence capabilities — live code, working product preview.

**What's Included:**
- Three cross-layer learning loops (Situation Analyzer, AgentEvolver, RL Reward/Penalty)
- Live Neo4j context graph — 47 nodes traversed per alert decision
- Six-factor transparent decision breakdown
- SHA-256 hash-chained tamper-evident evidence ledger
- Live Pulsedive threat intelligence connector
- ROI calculator with CFO-ready savings projection

**Deployment:** Local only.

---

### v3.2 — Platform Core. Multi-Copilot Ready. [Complete]

Refactored for platform scale. Domain-agnostic substrate.

**What's Included:**
- core/ infrastructure layer extracted
- domains/soc/ module — SOC as first-class domain plugin
- domain_registry.py — runtime domain selection
- state_manager.py — clean migration path

**Deployment:** Local only.

---

### v4.1 — Graph Attention Engine. Compounding Proved. [Tagged ✅]

The mathematical foundation becomes real code. Every blog claim is backed by a working implementation. GAE is a separate open-sourceable library.

**What's Included:**
- GAE v0.1.0: scoring (Eq. 4), learning (Eq. 4b, 4c), convergence monitoring, 177 tests
- Six FactorComputers computing from graph traversal (not property reads)
- Decision + outcome write-back to Neo4j (Channels A + B)
- Measured: 28.6x asymmetric trust (exceeds 20:1 target), cold-start 2.5s
- Tab 1: Alert triage with GAE pipeline. Tab 4: Convergence metrics
- 10-cycle compounding verification passed

**Value Delivered:**
- Blog claims verified in code. Technical evaluators can trace every equation.
- GAE library pip-installable with single dependency (NumPy)

**Deployment:** Local only.

---

### v4.5 — Make It Real. [Next — 18-19 prompts]

Closes credibility gaps between published claims and live product proof. A technical evaluator can see learning happen in real-time, read investigation narratives with calibration context, and (if the gate passes) see cross-graph discovery surface new relationships.

**What's Included:**

**GAE Preamble (GAE repo — 2-3 prompts):**
- CalibrationProfile: domain-configurable learning hyperparameters (learning rate, penalty ratio, temperature, decay classes, confirmation bias discount)
- Per-factor temporal decay: permanent knowledge decays slowly, campaign knowledge decays fast
- Backward compatible: default CalibrationProfile produces identical v4.1 behavior

**Phase A — Simulation Mode (6 prompts):**
- SimulationOrchestrator: batch decision processing through the identical GAE pipeline as manual triage
- Bernoulli oracle outcomes (no confirmation bias — independent of system recommendation)
- 15-20 alerts across 5 categories, each activating different dominant factors
- Category learning curve chart: per-category accuracy diverges over time (THE institutional judgment proof)
- ATT&CK technique IDs on all alerts (T1078, T1566.001, T1021.001, T1567, T1048)
- Atomic reset (TD-026 fix): GAE state + audit + Neo4j clear atomically

**Phase B — CISO Readability (4 prompts):**
- NarrativeProvider protocol with Ollama/Qwen default (local, no API key) and template fallback
- Tab 3 investigation narrative: "Calibrated from N verified outcomes on similar alerts"
- Tab 2 rewired to GAE pipeline (closes TD-019 dual decision paths, TD-020 missing events)
- Graceful degradation: no LLM? Template narrative. No Ollama? Template fallback.

**Phase C — Cross-Graph Discovery (6 prompts, HARD GATED):**
- EmbeddingProvider protocol: PropertyEmbeddingProvider (numpy-only, default) + TransformerEmbeddingProvider (optional)
- Cross-graph attention sweep (Eq. 6) + discovery extraction (Eq. 8a-8c)
- Discovery → expand_weight_matrix integration
- 5 planted discovery patterns in scenario seed data
- Tab 4 discovery panel
- **B3 Gate: F1 > 0.2 against planted patterns. Pass → ship Axis 3. Fail → document honestly.**

**Value Delivered:**
- "Run 50 Decisions" → watch learning happen in real-time. Category learning curve proves institutional judgment.
- Investigation narratives a CISO can read. Calibration line shows the system earns trust, not asserts it.
- Cross-graph discovery (if gate passes) proves Axis 3: the system extends its own evaluation criteria.
- Fully self-contained: GAE (numpy), narratives (Ollama), graph (Neo4j). No external API keys.

**Deployment:** Local product preview. Loom v2 recorded after Phase B.

**Gate:** 50-decision simulation with clear learning. Narrative with calibration line. Phase C: B3 F1 > 0.2.

---

### v5.0 — GAE as Platform + SOC as Product. [Designed — 18-20 prompts across 3 repos]

GAE becomes broad and usable (like HuggingFace Transformers). SOC copilot reaches product quality with ground truth evaluation, realistic data, and institutional judgment quantification. ci-platform gets its first real code.

**What's Included:**

**GAE v0.2.0 (platform breadth — 7 prompts):**
- Evaluation framework: EvaluationScenario, run_evaluation, EvaluationReport
- Ablation framework: four baselines prove each architectural component's value
- Institutional judgment metrics: prior divergence, accuracy improvement, recovery speed, judgment score
- Domain schema format + parser
- API surface design + import lint (no domain imports in engine)
- Example domain: "Hello World" DomainConfig in ~50 lines
- GAE Users Guide

**ci-platform v0.1.0 (first real code — 3-5 prompts):**
- DomainConfig ABC extracted from SOC
- StateManager extracted from SOC
- Domain registry
- Schema parser (YAML → DomainSchemaSpec)
- ContractChecker (schema + graph validation at startup)

**SOC Copilot (product polish — 8 prompts):**
- SEED-2: Realistic seed data (200+ users, power-law distributions, 10% missing properties, cold-start users, planted patterns for discovery)
- EVAL-1/2-SOC: 30-40 evaluation scenarios from ATT&CK × graph context. Ground truth with "right answer, right reasons."
- ECON-1: ROI dashboard (analyst hours saved, auto-triage rate, MTTR reduction, CFO-ready)
- Institutional Judgment Score + category learning curve on Tab 4
- Confirmation bias mitigation tuned (discount_strength from evaluation results)
- Scoring-based situation classification (from GAE factors, not hardcoded)
- Ablation comparison display

**Value Delivered:**
- Technical evaluator can run ablation: "Full system 89%. Without learning: 68%. Without graph context: 61%."
- CISO sees institutional judgment score: "After 200 decisions: 47/100. Strongest: travel_anomaly (94%)."
- CFO sees ROI: "47 analyst hours saved this month. Auto-triage rate: 73%."
- GAE is pip-installable, documented, with a Hello World example. Community can build new domain copilots.
- Three-repo milestone: GAE + ci-platform + SOC all have tagged releases.

**Deployment:** Local, evaluated product. Screen captures and metrics for outreach.

**Gate:** Evaluation accuracy > 80% on high-confidence scenarios. Ablation shows full system beats all baselines. Institutional judgment score > 0 (learning happened).

---

### v5.5 — Deployable. Docker + VPS. [Designed]

The product becomes accessible to prospects without a developer laptop.

**What's Included:**
- Docker Compose with named volumes (accumulated intelligence persists across restarts)
- VPS hosting: public product preview (auto-reset every 4h) + partner instance (no auto-reset, backup cron)
- PARTNER_README: volumes contain accumulated intelligence, backup/restore commands
- GraphEventBus: production async event dispatch (replaces SOC's local lightweight bus)
- Schema drift detection (C1 monitoring): coverage check, emit SchemaRegression if degraded
- Per-factor decay rates tuned from production data (A2)
- Holistic review of B3 discovery patterns + institutional judgment metrics

**Value Delivered:**
- Prospect self-service: visit URL, see the product, run simulation, read narratives
- Partner deployment: Docker bundle, partner deploys in their environment
- Production event infrastructure ready for v6.0 customer deployment

**Deployment:** Hosted product preview (VPS). Docker for partners.

**Gate:** Docker up + 50-decision simulation completes + named volumes persist state across restart.

---

### v6.0 — First Customer POC. [Planned]

Real customer data, real SIEM integration, real analyst feedback. The product operates on live alerts.

**What's Included:**
- Splunk ingest connector (customer's SIEM → SOC copilot alerts)
- SAML authentication (customer SSO)
- PII redaction at ingestion (before graph or LLM sees any data, HIPAA-safe)
- INOVA entity resolution (discovers relationships between entities from different sources)
- DomainOntology + SchemaValidator (write-path enforcement, Level 2 ontology maturity)
- Agent pipeline infrastructure (foundation for Tier 6 artifact evolution)
- Delayed outcome validation for autonomous decisions (C3 hardening)
- Cloud deployment (customer-accessible, SLA-backed)

**Value Delivered:**
- First customer generating real institutional judgment from their own operational data
- Entity resolution finds connections human analysts missed
- Compliance: audit trail + PII redaction + SAML SSO

**Deployment:** Cloud pilot with customer data processing agreement.

**Gate:** v5.5 hosted for 30+ days. Customer agreement signed. Data processing agreement executed.

---

### v6.5 — Flash Tier + Streaming. [Planned]

Pre-ingestion volume reduction validated in production. Streaming infrastructure for real-time alert flow.

**What's Included:**
- Flash Tier: pre-filter that compounds (analyst corrections reduce noise over time)
- Streaming alert ingestion (Kafka/Kinesis)
- Fast-path bypass for ransomware/APT patterns
- Reduces LLM API cost proportionally — only enriching alerts that matter

**Deployment:** Production + streaming infrastructure.

---

### v7.0 — Multi-Tenant. S2P + FinServ Copilots. [Roadmap]

Multiple enterprise customers, isolated graphs. Second and third domain copilots.

**What's Included:**
- Per-tenant graph isolation
- Self-service tenant onboarding
- S2P copilot: 6-factor PO scoring, auto-approve/flag/dual-source, geopolitical risk discovery
- Financial Services copilot: regulatory compliance monitoring, cross-regulatory discovery
- Cross-tenant meta-graph (opt-in, anonymized)

**Gate:** Second enterprise customer signed. Graph isolation verified.

---

### v7.5 — Partner Network — MSSP-Ready. [Vision]

MSSPs and consulting partners deploy for their clients.

**What's Included:**
- MSSP partner portal
- Docker bundle (multi-tenant aware)
- Meta-graph enrichment across client base (opt-in)
- Partner certification program

---

## Cross-Vertical Capability Map — UPDATED

| Capability | Security (SOC) | Supply Chain (S2P) | Financial Services |
|---|---|---|---|
| Domain-agnostic platform core | ✅ v3.2 | ✅ v3.2 | ✅ v3.2 |
| Context graph — live decision enrichment | ✅ v3.0 | v7.0 | v7.0 |
| Graph Attention Engine (open-source) | ✅ v4.1 | v7.0 | v7.0 |
| CalibrationProfile (domain-configurable) | v4.5 | v7.0 | v7.0 |
| Simulation mode | v4.5 | v7.0 | v7.0 |
| Investigation narrative (NarrativeProvider) | v4.5 | v7.0 | v7.0 |
| MITRE ATT&CK alignment | v4.5 | N/A | N/A |
| Cross-domain discovery (Axis 3, gated) | v4.5 | v7.0 | v7.0 |
| Evaluation framework (ground truth) | v5.0 | v7.0 | v7.0 |
| Ablation comparison | v5.0 | v7.0 | v7.0 |
| Institutional judgment metrics | v5.0 | v7.0 | v7.0 |
| ROI dashboard ($/time/risk) | v5.0 | v7.0 | v7.0 |
| Realistic seed data | v5.0 | v7.0 | v7.0 |
| Docker + VPS deployment | v5.5 | v7.0 | v7.0 |
| UCL entity resolution (INOVA) | v6.0 | v7.0 | v7.0 |
| SIEM connector (Splunk) | v6.0 | N/A | N/A |
| Autonomous operation | v6.0 | v7.0 | v7.0 |
| Pre-ingestion volume filter | v6.5 | v7.5 | v7.5 |
| Multi-tenant isolation | v7.0 | v7.0 | v7.0 |

---

## Why the Moat Is Structural

**The competitive advantage is not the model. It is the layer you own.**

- **Firm-specific:** discoveries emerge from this firm's operational history.
- **Temporally irreversible:** each discovery was enabled by a specific graph state that no longer exists.
- **Model-independent:** the graph, write-backs, and discoveries survive any LLM transition.
- **Recursive:** discoveries feed future discoveries. The richer the graph, the more sophisticated the next sweep.
- **Open engine, closed intelligence:** The math is open-source. The firm-specific graph is the irreplaceable asset.

**A competitor deploying today does not start six months behind. They start at zero.**

---

## Published Materials

| Material | URL | Purpose |
|---|---|---|
| Mathematical Foundation | [dakshineshwari.net/post/cross-graph-attention...](https://www.dakshineshwari.net/post/cross-graph-attention-mathematical-foundation-with-experimental-validation) | Peer-reviewable math |
| Compounding Intelligence 4.0 | [dakshineshwari.net/post/compounding-intelligence-4-0...](https://www.dakshineshwari.net/post/compounding-intelligence-4-0-how-enterprise-ai-develops-self-improving-judgment) | Architecture overview |
| Demo walkthrough (v1) | [Loom video](https://www.loom.com/share/b45444f85a3241128d685d0eaeb59379) | 15-minute live demonstration |
| Demo blurb (v3.1) | [dakshineshwari.net/post/after-ten-thousand-decisions...](https://www.dakshineshwari.net/post/after-ten-thousand-decisions-show-me-how-your-system-got-smarter-v3-1) | Positioning summary |

---

*Dakshineshwari LLC · SOC Copilot Platform Roadmap v6 · March 2026 · Confidential*
*v4.1 tagged. v4.5: Make It Real (18-19 prompts). v5.0: Platform + Product (18-20 prompts).*
*v5.5: Deployable. v6.0: First customer. v7.0+: Multi-tenant, multi-vertical.*
*arindam@dakshineshwari.net · www.dakshineshwari.net*
