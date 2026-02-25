# SOC Copilot Demo — v4.0 Planning Document

**Date:** February 24, 2026
**Status:** Planning (v3.0 in build)
**Prerequisite:** v3.0 complete and tagged
**Theme:** "Your tools, our decisions."

---

## Why This Document Exists

A customer meeting on Feb 24 reshaped v4 priorities. Before the meeting, v4 was infrastructure and polish (Docker, Live Graph, Prompt Hub). After the meeting, there's a clear customer-facing story: the demo needs to stop being standalone and start plugging into the customer's real stack.

This is a planning document — themes, backlog items, dependencies, and architectural concepts. Prompt-level specs come after v3 ships, because v3's implementation will surface interface patterns that v4 builds on.

---

## The Customer Signal

Three things the prospect said that matter:

1. **"We collect IOCs from Pulsedive, GreyNoise, ThreatYeti."** → They have multiple intelligence sources. v3 integrates one (Pulsedive). v4 should show the pattern scales to N sources.

2. **"We use CrowdStrike Falcon as our dashboard."** → They are NOT replacing CrowdStrike. Any solution must sit on top of it. This is a positioning question and a technical question.

3. **"How do we decide severity?"** → v3 answers this with the Decision Explainer. But the deeper question is: "Can your system make decisions using OUR data, not your demo data?" v4 needs to start answering that.

---

## v4 Theme: "Your tools, our decisions."

The v3 demo is self-contained — impressive but isolated. v4 makes the demo feel like it belongs in the customer's environment. The key architectural move is the **UCL Connector pattern** — a standard interface for plugging external data sources into Layer 1 (UCL), so the decision layer (Layer 3, ACCP) works the same regardless of where the data comes from.

### What v4 Proves

| Audience | What They See | What They Conclude |
|---|---|---|
| CISO | "It queries my CrowdStrike. It pulls from my Pulsedive AND GreyNoise." | "This fits my stack, not replaces it." |
| VC | "One connector pattern, N sources. Live Graph. Docker-deployable." | "This is a platform, not a prototype." |
| Partner | "docker-compose up, swap the connector config, demo in 60 seconds." | "I can sell this." |

---

## Architectural Concept: UCL Connectors

### The Pattern

The Four Layers diagram in v3 shows: `UCL → Agent Engineering → ACCP → SOC Copilot`. Currently UCL is a Neo4j graph with seeded data. In v4, UCL becomes a connector bus — multiple data sources feed into the same graph through a standard interface.

```
┌─────────────────────────────────────────────────┐
│                    UCL Layer                      │
│                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ Pulsedive│  │ GreyNoise│  │ CrowdStrike  │   │
│  │ Connector│  │ Connector│  │ Connector     │   │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘   │
│       │              │               │            │
│       ▼              ▼               ▼            │
│  ┌────────────────────────────────────────────┐  │
│  │         Unified Context Graph (Neo4j)       │  │
│  │  :ThreatIntel  :Alert  :Pattern  :User      │  │
│  └────────────────────────────────────────────┘  │
│                                                   │
└───────────────────────┬───────────────────────────┘
                        │
                        ▼
              ACCP Decision Layer
         (same scoring matrix, same loops,
          richer context = better decisions)
```

### Connector Interface

Each connector implements the same contract:

```python
class UCLConnector:
    name: str                    # "pulsedive", "greynoise", "crowdstrike"
    source_type: str             # "threat_intel", "alert_source", "enrichment"
    
    def refresh() -> ConnectorResult:
        """Pull data from source, write to Neo4j, return summary."""
        
    def health_check() -> HealthStatus:
        """Is the source reachable? API key valid? Rate limit OK?"""
        
    def get_config_schema() -> dict:
        """What .env vars does this connector need?"""
```

v3's `threat_intel.py` is already 80% of the Pulsedive connector. v4 refactors it into this pattern and adds more connectors.

### Why This Matters for Tab 1

Tab 1 currently runs natural language queries against the context graph. With UCL connectors feeding real data into that graph, Tab 1 becomes the **question layer over the customer's entire stack**:

- "Show me all IOCs from the last 24 hours that correlate with travel anomalies" → queries across CrowdStrike alerts + Pulsedive enrichment + HR calendar data in the graph
- "Which CrowdStrike detections would our scoring matrix classify differently?" → compares CrowdStrike severity with ACCP scoring
- "What's the overlap between Pulsedive indicators and our CrowdStrike detection list?" → cross-source correlation

This is NOT competing with CrowdStrike's explorer. CrowdStrike shows what happened within CrowdStrike. Tab 1 shows what it MEANS across all sources.

---

## v4 Backlog — Prioritized

### Tier 1: Customer-Facing (Build These First)

| ID | Feature | Prompts (est.) | Dependencies | Demo Moment |
|---|---|---|---|---|
| **C1** | **UCL Connector base class + registry** | 1 | v3 complete | "Every data source uses the same integration pattern." |
| **C2** | **GreyNoise connector** | 1 | C1, GreyNoise API key | "Two live intelligence sources. Badge shows both." |
| **C3** | **Refactor v3 Pulsedive into connector pattern** | 1 | C1 | No new demo moment — architectural cleanup |
| **C4** | **Multi-source Threat Intel dashboard (Tab 3 upgrade)** | 2 | C1, C2, C3 | "Three sources. One graph. The more sources, the better the decisions." |
| **C5** | **CrowdStrike mock connector** | 2 | C1 | "In production, this pulls from your Falcon instance." |
| **T1** | **Tab 1: Cross-source query examples** | 1 | C3 | "Ask a question that spans CrowdStrike, Pulsedive, and your calendar." |

### Tier 2: Infrastructure (Enables Partners + Deep Dives)

| ID | Feature | Prompts (est.) | Dependencies | What It Enables |
|---|---|---|---|---|
| **D1–D5** | **Docker for Partners** | 5 | v3 complete | Partner self-service: clone → docker-compose up → demo in 60 sec |
| **LG1–LG4** | **Live Graph Integration** | 4 | D1 (ideally) | Replaces in-memory dicts with Neo4j reads/writes. 30-min deep dive credibility. |

### Tier 3: Polish (Nice-to-Have)

| ID | Feature | Prompts (est.) | Dependencies | What It Enables |
|---|---|---|---|---|
| **PH1–PH2** | **Prompt Hub / Smart Queries** | 2 | T1 | "Did you mean?" suggestions, exec-friendly query UX |
| **FC1** | **Four Clocks diagnostic display** | 1 | LG1–LG4 | Tab 4 widget showing State/Event/Decision/Insight clock rates |

### Deferred to v5+

| Feature | Why |
|---|---|
| Process Intelligence (ITSM, S2P) | Cross-domain story. Needs second domain copilot first. |
| Real CrowdStrike API integration | Requires customer sandbox access + OAuth2 + paid tier. Build when prospect offers trial. |
| Cross-graph attention computation | Needs Live Graph + embedding infrastructure. The math blog describes it; v5 computes it. |

---

## Dependency Graph

```
v3.0 (complete)
  │
  ├── C1: UCL Connector base ──┬── C2: GreyNoise connector
  │                             ├── C3: Refactor Pulsedive
  │                             ├── C5: CrowdStrike mock
  │                             └── C4: Multi-source dashboard (needs C2 + C3)
  │                                  └── T1: Tab 1 cross-source queries
  │
  ├── D1–D5: Docker ──── LG1–LG4: Live Graph ──── FC1: Four Clocks
  │                                                 PH1–PH2: Prompt Hub
  │
  └── (v5: Process Intel, real CrowdStrike, cross-graph attention)
```

---

## Build Sequence (Tentative)

```
PHASE 1: Connectors (Sessions 1–3, ~8 prompts)
  Session 1: C1 (base class) + C3 (refactor Pulsedive)
  Session 2: C2 (GreyNoise) + C4 (multi-source dashboard)
  Session 3: C5 (CrowdStrike mock) + T1 (Tab 1 queries)
  TAG: v4.0-connectors

PHASE 2: Infrastructure (Sessions 4–6, ~9 prompts)
  Session 4: D1 + D2 (Dockerfiles)
  Session 5: D3 + D4 + D5 (compose, seed, README)
  Session 6: LG1 + LG2 (feedback → Neo4j)
  TAG: v4.0-infra

PHASE 3: Polish (Sessions 7–8, ~5 prompts)
  Session 7: LG3 + LG4 (policy + triage → Neo4j)
  Session 8: PH1 + PH2 (Prompt Hub) + FC1 (Four Clocks)
  TAG: v4.0

TOTAL: ~22 prompts, 8 sessions
```

This is an estimate. Prompt-level specs come after v3 ships.

---

## API Keys Needed for v4

| Source | Key Status | How to Get |
|---|---|---|
| Pulsedive | ✅ Configured in .env | Already done |
| GreyNoise | ❌ Need to sign up | https://viz.greynoise.io/signup → free community account → API key at account page. 50 lookups/week. |
| CrowdStrike | ❌ Not needed yet | Mock connector uses simulated responses. Real connector requires customer sandbox or Falcon Go trial. |
| CISA KEV | ❌ No key needed | Free public API, no auth: `GET https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json` |

---

## CrowdStrike Connector — Design Notes

The CrowdStrike connector is intentionally a **mock** in v4. Here's why and how:

### Why Mock

- Real Falcon API requires OAuth2 client credentials, a paid subscription, and tenant-specific endpoints
- No free tier or developer sandbox with instant access
- Customer data in CrowdStrike is sensitive — we can't demo with their real data without authorization
- The PATTERN of integration matters more than the data for a demo

### How the Mock Works

The CrowdStrike mock connector generates realistic-looking alert data that mirrors CrowdStrike Falcon's detection schema:

```python
class CrowdStrikeMockConnector(UCLConnector):
    """
    Generates CrowdStrike-like detections. In production,
    replace with real Falcon API calls.
    """
    
    def refresh(self):
        # Returns 10-15 simulated detections matching Falcon schema:
        # detection_id, severity, tactic (MITRE), technique,
        # hostname, user, timestamp, disposition
        
        # Key: some detections deliberately OVERLAP with Pulsedive IOCs
        # This creates cross-source correlation moments in the demo
```

The demo narrative: "In production, this connector calls your Falcon API. Today we're using simulated detections that mirror CrowdStrike's schema. Watch what happens when we cross-correlate them with live Pulsedive intelligence..."

### What Makes It Credible

- Schema matches real CrowdStrike detection output (available in public docs)
- Some detections deliberately overlap with Pulsedive IOCs → creates visible cross-source discovery
- Tab 1 can query "show me CrowdStrike detections that match Pulsedive high-risk indicators"
- The connector interface is identical to real connectors — swapping mock for real is a config change

### Production Path (When Customer Offers Sandbox)

1. Customer provides Falcon API client ID + secret
2. Replace mock with real OAuth2 flow + API calls
3. Everything downstream (graph, scoring, decisions) works unchanged
4. That's the platform thesis: swap the connector, keep the intelligence

---

## Tab 1 Evolution — From Analytics to Question Layer

### Current State (v2.5)
Tab 1 runs natural language queries against static context graph data. Example queries: "show me security metrics," "find rule sprawl." It works, but it's generic analytics.

### v4 State
With UCL connectors feeding real/simulated data from multiple sources into the graph, Tab 1's queries become cross-source intelligence questions:

| Current Query | v4 Query |
|---|---|
| "Show me security metrics" | "Show me security metrics across CrowdStrike and Pulsedive sources" |
| "Find rule sprawl" | "Which CrowdStrike rules overlap with Pulsedive threat feeds?" |
| (none) | "Cross-reference yesterday's CrowdStrike detections with travel calendar anomalies" |
| (none) | "Which Falcon alerts would our scoring matrix classify as false positives?" |

The backend change is minimal — Tab 1 already queries the Neo4j graph. The graph just has richer data in it from the connectors. The frontend change is mostly new example queries + source attribution in results ("Source: CrowdStrike mock | Pulsedive live | Internal graph").

### v5+ Vision
Tab 1 becomes a true cross-source intelligence workbench. Natural language in, correlated intelligence out, with source provenance and confidence scores. This is where the cross-graph attention math from the blog paper actually runs.

---

## Risk and Open Questions

| Question | Impact | When to Resolve |
|---|---|---|
| Does GreyNoise free tier (50/week) work for repeated demos? | If not, cache aggressively or use mock fallback | Before C2 prompt spec |
| CrowdStrike Falcon schema — is public docs enough to mock accurately? | Credibility of mock connector | Research before C5 prompt spec |
| Live Graph migration — do we break existing demo flows? | Regression risk | Needs careful testing plan in LG1–LG4 specs |
| Docker + Neo4j Aura — can partners use the same cloud instance? | Partner isolation | Design decision during D3 |
| Will customers accept a mock CrowdStrike connector? | Credibility in meetings | Gauge reaction during next prospect call |

---

## Version Roadmap (Updated)

| Version | Theme | ACCP Capabilities | Key Demo Moment |
|---|---|---|---|
| v1.0 | Context graph | 1/21 | "The substrate exists" |
| v2.0 | Two loops + eval gates | 7/21 | "It learns from decisions" |
| v2.5 | Interactivity + governance | 10/21 | "Plug in YOUR numbers" |
| v2.5.1 | Bug fix | 10/21 | — |
| **v3.0 (building)** | **Three loops. Auditable. Connected. Transparent.** | **14/21** | **"Live Pulsedive. Tamper-evident. Explainable."** |
| **v4.0 (this doc)** | **Your tools, our decisions.** | **18/21** | **"CrowdStrike + Pulsedive + GreyNoise. One graph. Docker-deployable."** |
| v5.0 | Platform thesis | 21/21 | "Second domain. Control Tower. Cross-graph attention runs live." |

---

*SOC Copilot Demo — v4.0 Planning Document | February 24, 2026*
*Status: Planning. Build after v3.0 ships. Prompt-level specs after v3 implementation surfaces interface patterns.*
