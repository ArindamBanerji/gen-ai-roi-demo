# CLAUDE.md — SOC Copilot Demo (CISO Version v1)

> This file provides context for Claude Code. Read this first before any task.

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## SECTION A: PROJECT-SPECIFIC
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## A1. Project Overview

**Project Name:** SOC Copilot Demo — CISO/Security Operations Version

**One-Line Summary:** A demo proving that AI-augmented security operations can compound intelligence through governed context, runtime evolution, and situation-aware triage.

**Domain:** Security Operations Center (SOC) — Alert triage and automated response

**Architecture Note:** This is the Invoice Exception demo with a cybersecurity domain veneer. ~80% of the codebase is identical. The architecture (two-loop compounding, TRIGGERED_EVOLUTION, eval gates) is domain-agnostic.

**Key Architecture Decision:** Simplified agent architecture — rule-based decision engine with LLM narration (~200 lines total). The demo proves the ARCHITECTURE, not agent sophistication.

### The Two Stories

| Story | Audience | What It Proves | Primary Tab |
|-------|----------|----------------|-------------|
| **"SOC Efficiency"** | CISOs / Security Leaders | Alert triage + Governance = Immediate value | Tab 1 (SOC Analytics) |
| **"Compounding Moat"** | VCs | Runtime Evolution + Two Loops = Defensibility | Tabs 2-4 |

### Tab Energy Allocation (CRITICAL)

| Tab | Name | Energy | Why |
|-----|------|--------|-----|
| 1 | SOC Analytics | **20%** | Immediate value — governed security metrics |
| 2 | Runtime Evolution | **35%** | **★ THE KEY DIFFERENTIATOR — build first and best** |
| 3 | Alert Triage | 30% | Shows closed-loop that goes beyond "detect" |
| 4 | Compounding | 15% | Two-loop visual is the hero |

### Key Outcomes
- CISOs see: Automated triage + governance + detection rule sprawl detection
- VCs see: **Runtime evolution + Graph traversal + Week 1 vs Week 4 improvement**

---

## A2. The SIEM Contrast (CRITICAL)

This is the competitive positioning. Memorize this:

| What Traditional SIEMs Show | What We Show (Our Addition) |
|-----------------------------|----------------------------|
| Alerts accumulate in queue | Alerts accumulate **AND feed runtime evolution** |
| Detection rules fire | Detection rules fire **AND agent self-tunes** |
| Decisions are logged | Decisions **trigger pattern learning** |
| One loop: Alert → Detect → Log | **Two loops** — same graph feeds both engines |

**The Soundbite:**
> "Your SIEM gets better detection rules. Our SOC Copilot gets **smarter**."

> "Splunk shows you what happened. We show you a SOC that learns."

---

## A3. Agent Architecture

### Core Insight

**The demo proves the ARCHITECTURE, not agent sophistication.**

The value proposition lives in:
- The graph schema (TRIGGERED_EVOLUTION)
- The two-loop data flow
- The closed-loop verification
- The visual representation

The agent itself is **intentionally simple** because:
1. **Demo reliability** — Rule-based = same decision every time
2. **Auditability** — CISOs need to explain decisions to auditors
3. **Faster build** — ~200 lines vs ~1000+ lines
4. **Clear separation** — Architecture proves the thesis, not AI magic

### The Simple Agent (2 Files, ~200 Lines)

```
backend/app/services/
├── agent.py       # ~150 lines — Decision engine + trace writer
└── reasoning.py   # ~50 lines  — LLM prompt templates for narration
```

### Decision Logic: 4 Primary Rules

```python
# agent.py — The entire decision engine

def decide(alert: Alert, context: SecurityContext) -> Decision:
    """
    Rule-based decision logic. Intentionally simple.
    The demo proves architecture, not agent sophistication.
    """
    
    if alert.alert_type == "anomalous_login":
        if context.user_traveling and context.vpn_matches_location:
            if context.mfa_completed and context.device_fingerprint_match:
                return Decision(
                    action="false_positive_close",
                    confidence=0.92,
                    pattern_id="PAT-TRAVEL-001"
                )
        if context.user_risk_score > 0.8:
            return Decision(
                action="escalate_incident",
                confidence=0.95,
                pattern_id=None
            )
        return Decision(action="escalate_tier2", confidence=0.78, pattern_id=None)
    
    elif alert.alert_type == "phishing":
        if context.known_campaign_signature:
            return Decision(
                action="auto_remediate",
                confidence=0.94,
                pattern_id="PAT-PHISH-KNOWN"
            )
        return Decision(action="escalate_tier2", confidence=0.85, pattern_id=None)
    
    elif alert.alert_type == "malware_detection":
        if context.asset_criticality == "critical":
            return Decision(action="escalate_incident", confidence=0.96, pattern_id=None)
        return Decision(
            action="auto_remediate",
            confidence=0.89,
            pattern_id="PAT-MALWARE-ISOLATE"
        )
    
    elif alert.alert_type == "data_exfiltration":
        return Decision(action="escalate_incident", confidence=0.97, pattern_id=None)
    
    # Default
    return Decision(action="escalate_tier2", confidence=0.60, pattern_id=None)
```

### LLM Role: Narration Only

```python
# reasoning.py — LLM generates impressive justification AFTER decision

async def generate_reasoning(alert, decision, context) -> str:
    """
    LLM makes rule-based decision sound like expert security analysis.
    This is 'intelligence theater' — the decision was already made.
    """
    prompt = f"""
    Write a 2-sentence SOC analyst justification for {decision.action}.
    Alert: {alert.alert_type} from {alert.source_location}
    User: {context.user_name} ({context.user_title})
    Context: Travel to {context.travel_destination}, VPN {context.vpn_provider}
    Pattern: {decision.pattern_id} ({context.pattern_count} cases, {context.fp_rate}% FP)
    """
    return await gemini.generate(prompt)
```

### Why This Works

| Demo Requirement | How Simple Agent Delivers |
|------------------|---------------------------|
| "47 nodes consulted" | Fixed Cypher returns predictable count |
| Graph animation | Real Neo4j queries, NVL visualizes results |
| Decision reasoning | LLM generates justification after decision |
| TRIGGERED_EVOLUTION | Deterministic rule ensures it fires |
| Predictable demo | Same input → same decision every time |

---

## A4. Application Architecture

### High-Level View

```
┌─────────────────────────────────────────────────────────────────┐
│                     SOC COPILOT DEMO                            │
├─────────────────────────────────────────────────────────────────┤
│  Tab 1: SOC Analytics    │  Tab 2: Runtime Evolution ★         │
│  Tab 3: Alert Triage     │  Tab 4: Compounding Dashboard       │
├─────────────────────────────────────────────────────────────────┤
│                   Simple Agent Layer                            │
│               (agent.py + reasoning.py ~200 lines)              │
├─────────────────────────────────────────────────────────────────┤
│   BigQuery          │    Firestore       │    Neo4j Aura       │
│   (Metrics/SLAs)    │    (Alerts/State)  │    (Security Graph) │
└─────────────────────────────────────────────────────────────────┘
```

### The Two-Loop Architecture (The VC Story)

```
              ┌─────────────────────────────────┐
              │       SECURITY GRAPH            │
              │          (Neo4j)                │
              │                                 │
              │  (:Decision)-[:TRIGGERED_EVOLUTION]->(:EvolutionEvent)
              │              ↑                  │
              │     THE KEY RELATIONSHIP        │
              └─────────────────────────────────┘
                              │
             ┌────────────────┴────────────────┐
             ▼                                 ▼
  ┌─────────────────────┐         ┌─────────────────────┐
  │   Alert Triage      │         │   Runtime Evolution │
  │     (Loop 1)        │         │     (Loop 2)        │
  │                     │         │                     │
  │ • Better context    │         │ • Better agent      │
  │ • Better precedents │         │ • Self-tuning       │
  │ • SIEM has this ✓   │         │ • SIEM LACKS ✗      │
  └─────────────────────┘         └─────────────────────┘
             │                                 │
             └────────────────┬────────────────┘
                              ▼
                        COMPOUNDING

  "Splunk gets better rules. Our copilot becomes a better copilot."
```

---

## A5. Key Concepts

| Term | Definition |
|------|------------|
| **SOC** | Security Operations Center — the team monitoring alerts |
| **SIEM** | Security Information and Event Management (Splunk, Sentinel) |
| **MTTR** | Mean Time to Respond — key SOC metric |
| **MTTD** | Mean Time to Detect — key SOC metric |
| **FP Rate** | False Positive Rate — % of alerts that are not real threats |
| **Auto-Close Rate** | % of alerts closed without human intervention |
| **Eval Gate** | 4 deterministic quality checks before agent action executes |
| **Decision Trace** | Full record of decision including context, reasoning, playbook |
| **EvolutionEvent** | Record of agent self-improvement triggered by a decision |
| **TRIGGERED_EVOLUTION** | The key relationship connecting decisions to agent improvement |
| **AttackPattern** | Learned alert pattern (like PAT-TRAVEL-001) |
| **Playbook** | SOC response procedure for alert type |
| **Simple Agent** | Rule-based decision engine + LLM narration (~200 lines) |

---

## A6. Technology Stack

### Data Layer

```
BigQuery (Analytics — Tab 1 primary)
├── Dataset: soc
├── Tables: metric_contracts, soc_metrics, detection_rules, rule_sprawl_registry
└── Use: Metric lookup, SLA queries, sprawl detection

Firestore (Operational — Tab 2 primary)
├── Collections: alerts, decisions, patterns, deployments, assets, users, playbooks
└── Use: Real-time state, CRUD operations

Neo4j Aura (Semantic — Tabs 3-4 primary)
├── Nodes: Asset, User, AlertType, AttackPattern, Playbook, SLA, TravelContext
├── Decision Trace Nodes: Decision, DecisionContext, EvolutionEvent
├── Relationships: DETECTED_ON, INVOLVES, MATCHES, HANDLED_BY, etc.
├── Causal Relationships: CAUSED, PRECEDENT_FOR
├── KEY Relationship: TRIGGERED_EVOLUTION (OUR DIFFERENTIATOR)
└── Use: Graph traversal, pattern matching, decision trace storage
```

### Neo4j Schema (CRITICAL)

```cypher
// Core security entities
(:Asset {id, hostname, type, criticality, business_unit})
(:User {id, name, title, department, risk_score, is_privileged})
(:AlertType {id, name, severity, mitre_technique})
(:AttackPattern {id, name, fp_rate, occurrence_count, confidence})
(:Playbook {id, name, steps, auto_actions, sla_minutes})
(:SLA {id, name, response_time_minutes, severity})
(:TravelContext {id, user_id, destination, start_date, end_date})

// Decision Trace nodes — THE KEY ADDITION
(:Decision {
    id, type, reasoning, confidence, timestamp, 
    alert_id, action_taken
})

(:DecisionContext {
    id, decision_id, 
    user_snapshot, asset_snapshot, patterns_matched, nodes_consulted
})

(:EvolutionEvent {
    id, event_type, triggered_by, 
    before_state, after_state, description, timestamp
})

// Relationships
(:Alert)-[:DETECTED_ON]->(:Asset)
(:Alert)-[:INVOLVES]->(:User)
(:Alert)-[:CLASSIFIED_AS]->(:AlertType)
(:Alert)-[:MATCHES]->(:AttackPattern)
(:AlertType)-[:HANDLED_BY]->(:Playbook)
(:User)-[:HAS_TRAVEL]->(:TravelContext)
(:Asset)-[:SUBJECT_TO]->(:SLA)

// Decision trace relationships
(:Decision)-[:HAD_CONTEXT]->(:DecisionContext)
(:Decision)-[:FOR_ALERT]->(:Alert)
(:Decision)-[:APPLIED_PLAYBOOK]->(:Playbook)
(:Decision)-[:USED_PRECEDENT {similarity}]->(:Decision)

// Causal chain relationships
(:Decision)-[:CAUSED {reason, timestamp}]->(:Decision)
(:Decision)-[:PRECEDENT_FOR {similarity, cited_in_reasoning}]->(:Decision)

// THE KEY RELATIONSHIP — What SIEMs don't have (OUR DIFFERENTIATOR)
(:Decision)-[:TRIGGERED_EVOLUTION {impact, magnitude, timestamp}]->(:EvolutionEvent)
```

### AI Layer

```
Gemini 1.5 Pro (via Vertex AI)
├── Model: gemini-1.5-pro-002
├── Location: us-central1
└── Use: NARRATION ONLY
    └── generate_reasoning() — Makes rule-based decisions sound intelligent

Decision Making: Rule-based engine
├── agent.py: decide() — 4 primary rules
├── Pattern: alert_type + context checks → action
└── Benefit: Deterministic, auditable, demo-reliable
```

### Frontend

```
React 18 + TypeScript + Vite
├── Styling: Tailwind CSS
├── Components: shadcn/ui
├── Charts: Recharts
├── Graph Viz: NVL (preferred) or React Force Graph
└── State: useState only (no Redux/Zustand — minimal complexity)
```

### Backend

```
Python 3.11+ + FastAPI
├── Validation: Pydantic v2
├── Async: Throughout
├── Clients: BigQuery, Firestore, Neo4j, Vertex AI
└── Agent: 2 files, ~200 lines
    ├── agent.py (~150 lines)
    └── reasoning.py (~50 lines)
```

---

## A7. Project Structure

```
soc-copilot-demo/
├── CLAUDE.md                     # THIS FILE
├── README.md
├── .env                          # From Colab setup
├── .env.example
├── .gitignore
│
├── docs/
│   ├── vc_demo_build_spec_ciso_v1.md  # Build specification
│   └── DEMO_SCRIPT.md            # Minute-by-minute narration
│
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx               # 4-tab layout
│       ├── main.tsx
│       ├── index.css
│       ├── components/
│       │   ├── ui/               # shadcn/ui
│       │   ├── tabs/
│       │   │   ├── SOCAnalyticsTab.tsx
│       │   │   ├── RuntimeEvolutionTab.tsx
│       │   │   ├── AlertTriageTab.tsx
│       │   │   └── CompoundingTab.tsx
│       │   └── common/
│       │       ├── AlertQueue.tsx
│       │       ├── SecurityGraph.tsx
│       │       ├── EvalGatePanel.tsx
│       │       └── ClosedLoop.tsx
│       └── lib/
│           └── api.ts
│
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py               # FastAPI app
│   │   ├── routers/
│   │   │   ├── soc.py            # Tab 1
│   │   │   ├── evolution.py      # Tab 2
│   │   │   ├── triage.py         # Tab 3
│   │   │   └── metrics.py        # Tab 4
│   │   ├── services/
│   │   │   ├── agent.py          # ~150 lines (THE AGENT)
│   │   │   └── reasoning.py      # ~50 lines (LLM narration)
│   │   ├── models/
│   │   │   └── schemas.py
│   │   └── db/
│   │       ├── bigquery.py
│   │       ├── firestore.py
│   │       └── neo4j.py
│   └── tests/
│
└── infrastructure/
    ├── ciso_setup_notebook_v1.py  # Colab setup
    └── .env.example
```

---

## A8. The Four Tabs

### Tab 1: SOC Analytics (20%)

**Purpose:** Governed security metrics with provenance

**Demo:**
1. Type: "What was MTTR last week by severity?"
2. Show: Chart + metric contract + data provenance
3. Bonus: Detection rule sprawl alert

**Key Components:**
- `SOCQueryInput` — Natural language input
- `MetricResult` — Chart with governance panel
- `RuleSprawlAlert` — Duplicate detection rule warning

### Tab 2: Runtime Evolution (35%) ★ THE DIFFERENTIATOR

**Purpose:** Show that decisions trigger agent evolution

**Demo:**
1. Show deployment registry (active + canary)
2. Click "Process Alert"
3. Watch eval gate checks
4. See TRIGGERED_EVOLUTION panel light up

**Key Components:**
- `DeploymentRegistry` — Active/canary versions
- `EvalGatePanel` — 4 checks with scores
- `TriggeredEvolution` — The purple panel (MOST IMPORTANT)

**Soundbite:** "Splunk gets better rules. Our copilot gets smarter."

### Tab 3: Alert Triage (30%)

**Purpose:** Graph-based reasoning + closed-loop execution

**Demo:**
1. Select alert from queue
2. Watch graph animate (nodes light up)
3. See recommendation with confidence
4. Click action → closed loop executes

**Key Components:**
- `AlertQueue` — Pending alerts
- `SecurityGraph` — NVL visualization
- `Recommendation` — Decision + reasoning
- `ClosedLoop` — 4-step execution panel

**Soundbite:** "A SIEM stops at detect. We close the loop."

### Tab 4: Compounding (15%)

**Purpose:** Prove the moat is growing

**Demo:**
1. Show Week 1 vs Week 4 comparison
2. Highlight: Same model, more intelligence
3. Show two-loop diagram

**Key Numbers:**
- Week 1: 23 patterns, 68% auto-close
- Week 4: 127 patterns, 89% auto-close

**Soundbite:** "When a competitor deploys, they start at zero. We start at 127 patterns."

---

## A9. Environment Variables

```bash
# GCP
PROJECT_ID=soc-copilot-demo
REGION=us-central1

# BigQuery
BIGQUERY_DATASET=soc

# Firestore
FIRESTORE_DATABASE=(default)

# Neo4j Aura
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password

# Vertex AI
VERTEX_AI_LOCATION=us-central1
```

---

## A10. Success Criteria

### Must Work

| Criterion | Tab | Test |
|-----------|-----|------|
| SOC metric query works | 1 | Type "MTTR by severity" |
| Rule sprawl detected | 1 | Duplicate rule flagged |
| Deployment registry shows versions | 2 | Active + canary visible |
| Eval gate shows 4 checks | 2 | All with scores |
| TRIGGERED_EVOLUTION fires | 2 | Purple panel appears |
| Graph animates | 3 | Nodes light up on select |
| "47 nodes" counter accurate | 3 | Matches query |
| Closed loop shows 4 steps | 3 | Sequential animation |
| Week 1 vs Week 4 different | 4 | Numbers clearly different |
| Two-loop diagram renders | 4 | Hero visual visible |

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## SECTION B: CLAUDE CODE GUIDANCE
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## B1. Priority Order

When building, follow this order:

1. **Tab 2 first** — Runtime Evolution is THE differentiator
2. **Tab 3 second** — Alert Triage shows closed loop
3. **Tab 1 third** — SOC Analytics is simpler
4. **Tab 4 last** — Compounding is mostly display

Within each tab:
1. API endpoint (backend)
2. Component (frontend)
3. Wiring (API → Component)
4. Polish (animations, loading states)

---

## B2. Key Files to Create First

```
Day 1:
├── backend/app/services/agent.py      # THE AGENT (~150 lines)
├── backend/app/services/reasoning.py  # LLM narration (~50 lines)
├── backend/app/routers/evolution.py   # Tab 2 API
└── frontend/src/components/tabs/RuntimeEvolutionTab.tsx

Day 2:
├── backend/app/routers/triage.py      # Tab 3 API
├── frontend/src/components/tabs/AlertTriageTab.tsx
└── frontend/src/components/common/SecurityGraph.tsx

Day 3:
├── backend/app/routers/soc.py         # Tab 1 API
└── frontend/src/components/tabs/SOCAnalyticsTab.tsx

Day 4:
├── backend/app/routers/metrics.py     # Tab 4 API
└── frontend/src/components/tabs/CompoundingTab.tsx
```

---

## B3. Code Patterns

### Agent Pattern (agent.py)

```python
# Simple, deterministic, testable
def decide(alert: Alert, context: SecurityContext) -> Decision:
    if alert.alert_type == "anomalous_login":
        if context.user_traveling and context.vpn_matches_location:
            return Decision(action="false_positive_close", confidence=0.92)
    # ... more rules
    return Decision(action="escalate_tier2", confidence=0.60)
```

### LLM Narration Pattern (reasoning.py)

```python
# LLM only generates text AFTER decision is made
async def generate_reasoning(alert, decision, context) -> str:
    prompt = build_prompt(alert, decision, context)
    return await gemini.generate(prompt)
```

### Neo4j Query Pattern

```python
# Fixed Cypher queries — no dynamic generation
async def get_security_context(alert_id: str) -> SecurityContext:
    query = """
    MATCH (alert:Alert {id: $alert_id})-[:DETECTED_ON]->(asset:Asset)
    MATCH (alert)-[:INVOLVES]->(user:User)
    OPTIONAL MATCH (user)-[:HAS_TRAVEL]->(travel:TravelContext)
    // ... rest of fixed query
    """
    result = await neo4j.run(query, alert_id=alert_id)
    return SecurityContext.from_result(result)
```

### Frontend Component Pattern

```tsx
// Simple state, clear data flow
export function RuntimeEvolutionTab() {
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState<ProcessResult | null>(null);

  const processAlert = async (alertId: string) => {
    setProcessing(true);
    const res = await api.processAlert(alertId);
    setResult(res);
    setProcessing(false);
  };

  return (
    <div>
      <DeploymentRegistry deployments={deployments} />
      <EvalGatePanel result={result?.evalGate} />
      <TriggeredEvolution evolution={result?.triggeredEvolution} />
    </div>
  );
}
```

---

## B4. Common Tasks

### "Create Tab 2 (Runtime Evolution)"

```
1. Read vc_demo_build_spec_ciso_v1.md Tab 2 section
2. Create backend/app/routers/evolution.py with endpoints
3. Create frontend/src/components/tabs/RuntimeEvolutionTab.tsx
4. Create EvalGatePanel.tsx component
5. Wire up API calls
6. Test: Process alert → see TRIGGERED_EVOLUTION
```

### "Add new alert type"

```
1. Add rule to agent.py decide() function
2. Add template to reasoning.py TEMPLATES
3. Add AlertType node to Neo4j
4. Add seed data to setup notebook
5. Test: New alert type triggers correct action
```

### "Debug why TRIGGERED_EVOLUTION doesn't fire"

```
1. Check pattern_id in Decision (must not be None)
2. Check occurrence_count threshold in maybe_trigger_evolution()
3. Check Neo4j write in TRIGGERED_EVOLUTION creation
4. Check frontend is reading triggered_evolution from response
```

---

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## SECTION C: QUICK REFERENCE
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### Alert Types

| Type | Action (typical) | Pattern |
|------|------------------|---------|
| anomalous_login | false_positive_close or escalate | PAT-TRAVEL-001 |
| phishing | auto_remediate or escalate | PAT-PHISH-KNOWN |
| malware_detection | auto_remediate or escalate_incident | PAT-MALWARE-ISOLATE |
| data_exfiltration | escalate_incident | None (always escalate) |

### Actions

| Action | Description | Auto-Executable |
|--------|-------------|-----------------|
| false_positive_close | Close alert, no threat | ✓ |
| auto_remediate | Quarantine/isolate automatically | ✓ |
| enrich_and_wait | Gather more context | ✓ |
| escalate_tier2 | Senior analyst review | ✗ |
| escalate_incident | Create IR ticket | ✗ |

### Key Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| MTTR | Mean Time to Respond | < 15 min |
| MTTD | Mean Time to Detect | < 5 min |
| Auto-Close Rate | % closed without human | > 75% |
| FP Rate | % false positives | < 20% |

### Soundbites (Memorize These)

1. **Tab 2:** "Splunk gets better rules. Our copilot gets **smarter**."
2. **Tab 3:** "A SIEM stops at detect. We **close the loop**."
3. **Tab 4:** "When they deploy, they start at zero. We start at **127 patterns**."
4. **Overall:** "Your SIEM **remembers**. Our copilot **learns**."

### Domain Mapping (from Invoice Demo)

| Invoice Term | CISO Term |
|--------------|-----------|
| Invoice Exception | Security Alert |
| Vendor | Asset |
| Contract | SLA |
| Policy | Playbook |
| Pattern | Attack Pattern |
| OTIF, DPO | MTTD, MTTR |
| AP Analyst | SOC Analyst |

---

*CLAUDE.md for SOC Copilot Demo (CISO Version) v1 | January 2026*
*Key changes: Adapted for cybersecurity/SOC domain with security-specific terminology*
*Core principle: The demo proves the ARCHITECTURE, not agent sophistication. Tab 2 is THE differentiator.*
