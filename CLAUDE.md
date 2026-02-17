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

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## V2 ADDITIONS (February 2026)
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Version:** v2.0 (Wave 6 Complete)
**Branch:** `feature/v2-enhancements`
**Base:** v1.0 frozen on `main` (tag: v1.0)

### Git Workflow

```bash
# v2 Development Branch
git checkout feature/v2-enhancements

# v2 Ports (different from v1)
Backend:  8001 (v1 uses 8000)
Frontend: 5174 (v1 uses 5173)

# Start v2
cd backend && uvicorn app.main:app --reload --port 8001
cd frontend && npx vite --port 5174

# View v2
http://localhost:5174
```

---

## V2 NEW SERVICES

### services/situation.py — Situation Analyzer (Loop 1)

**Purpose:** Smarter WITHIN each decision — classifies situations, evaluates options, provides decision economics.

**Key Exports:**
- `SituationType` enum — 6 situation types:
  - `TRAVEL_LOGIN_ANOMALY` - Travel + login pattern
  - `KNOWN_PHISHING_CAMPAIGN` - Signature match
  - `CRITICAL_ASSET_MALWARE` - High-value target
  - `DATA_EXFILTRATION_DETECTED` - Data movement alert
  - `UNKNOWN_LOGIN_PATTERN` - Novel behavior
  - `ROUTINE_MALWARE_SCAN` - Low-severity detection

- `classify_situation(alert_type, context) -> SituationType`
  - Pattern matching logic
  - Deterministic classification

- `evaluate_options(situation_type, context) -> List[OptionEvaluated]`
  - Generates 3-4 options per situation
  - **Wave 6A:** Includes decision economics:
    - `estimated_resolution_time` — "3 sec", "45 min", "2 hr"
    - `estimated_analyst_cost` — 0, 43, 127 (dollars)
    - `risk_if_wrong` — "None", "Low", "Medium", "High"

- `analyze_situation(alert_type, context) -> SituationAnalysis`
  - Full analysis combining classification and evaluation
  - **Wave 6A:** Includes `decision_economics` summary:
    - `time_saved` — "42 minutes vs manual triage"
    - `cost_avoided` — "$127 analyst cost avoided"
    - `monthly_projection` — "At 200 similar alerts/month: 150 analyst-hours, $25K saved"

**Lines:** ~280

**Tab Support:** Tab 2 (context), Tab 3 (situation panel)

---

### services/evolver.py — AgentEvolver (Loop 2)

**Purpose:** Smarter ACROSS all decisions — tracks prompt variants, promotes winners, computes operational impact.

**Key Exports:**

**In-Memory State:**
- `PROMPT_STATS` — Variant performance tracking:
  ```python
  {
    "TRAVEL_CONTEXT_v1": {"success": 24, "total": 34, "success_rate": 0.71},
    "TRAVEL_CONTEXT_v2": {"success": 42, "total": 47, "success_rate": 0.89},
    "PHISHING_RESPONSE_v1": {"success": 31, "total": 38, "success_rate": 0.82},
    "PHISHING_RESPONSE_v2": {"success": 12, "total": 15, "success_rate": 0.80}
  }
  ```

- `ACTIVE_PROMPTS` — Currently active variant per alert type:
  ```python
  {
    "anomalous_login": "TRAVEL_CONTEXT_v2",
    "phishing": "PHISHING_RESPONSE_v1"
  }
  ```

**Functions:**
- `get_prompt_variant(alert_type) -> str`
  - Returns active prompt variant

- `record_decision_outcome(decision_id, prompt_variant, success)`
  - Records outcome, updates stats, recalculates success rate

- `check_for_promotion(alert_type) -> Optional[Dict]`
  - Checks if better variant should be promoted
  - Requires >5% improvement + 10 samples
  - Automatically promotes if threshold met

- `generate_what_changed_narrative(alert_type, old_rate, new_rate) -> str` **(Wave 6B)**
  - Plain English explanation of what improved
  - Alert-specific narratives:
    - **anomalous_login:** "Agent learned that VPN location + travel record together indicate safe access. Previously escalated 29% of travel alerts to Tier 2 unnecessarily."
    - **phishing:** "Agent improved campaign signature matching. Faster identification of known phishing patterns reduces exposure window."
    - **default:** "Agent behavior improved through accumulated decision outcomes."

- `calculate_operational_impact(old_rate, new_rate) -> OperationalImpact` **(Wave 6B)**
  - Computes monthly savings from improvement
  - Returns:
    - `fewer_false_escalations_pct` — Percentage point improvement
    - `fewer_false_escalations_monthly` — Count reduction (assumes 200 alerts/month)
    - `analyst_hours_recovered` — Hours saved (45 min per review)
    - `estimated_monthly_savings` — Dollar amount ($127 per escalation)
    - `missed_threats` — Always 0 (eval gates prevent unsafe actions)

- `get_evolution_summary(alert_type) -> PromptEvolution`
  - Returns current state with any recent promotion
  - **Wave 6B:** Now includes `what_changed_narrative` and `operational_impact`

**Models:**
- `OperationalImpact` — Business metrics from evolution
- `PromptEvolution` — Evolution data for UI display

**Lines:** ~330

**Tab Support:** Tab 2 (AgentEvolver panel)

---

## V2 NEW ENDPOINTS

### POST /api/alert/process-blocked

**Purpose:** Simulates eval gate failure for blocking demo.

**Router:** `evolution.py`

**Request:**
```json
{
  "alert_id": "ALERT-7823"
}
```

**Response:**
```json
{
  "alert_id": "ALERT-7823",
  "routed_to": "soc_copilot_v3.1",
  "eval_gate": {
    "checks": [...],  // At least one fails
    "overall_passed": false,
    "overall_score": 0.78
  },
  "execution": {
    "status": "blocked",
    "reason": "One or more eval gates failed: Faithfulness score 0.75 below threshold 0.85"
  },
  "blocked_reason": "Eval gate blocked action due to low faithfulness score...",
  "decision_trace": {...},
  "triggered_evolution": {"occurred": false}
}
```

**Tab Support:** Tab 2 (blocking demo button)

---

### POST /api/triage/analyze (v2 enhanced)

**Purpose:** Analyze alert with situation analysis.

**Router:** `triage.py`

**Request:**
```json
{
  "alert_id": "ALERT-7823"
}
```

**Response (v2 additions):**
```json
{
  "decision": {...},
  "situation_analysis": {  // ★ NEW v2
    "type": "TRAVEL_LOGIN_ANOMALY",
    "primary_factors": [
      "User John Smith traveling to Singapore",
      "VPN connection from Singapore",
      "Known pattern PAT-TRAVEL-001 (127 occurrences)"
    ],
    "options_evaluated": [
      {
        "option": "Auto-close as false positive",
        "reasoning": "...",
        "confidence": 0.92,
        "estimated_resolution_time": "3 sec",  // ★ NEW Wave 6A
        "estimated_analyst_cost": 0,            // ★ NEW Wave 6A
        "risk_if_wrong": "Low"                  // ★ NEW Wave 6A
      },
      // ... more options
    ],
    "reasoning": "...",
    "decision_economics": {  // ★ NEW Wave 6A
      "time_saved": "42 minutes vs manual triage",
      "cost_avoided": "$127 analyst cost avoided",
      "monthly_projection": "At 200 similar alerts/month: 150 analyst-hours, $25K saved"
    }
  },
  "reasoning": "...",
  "confidence": 0.92,
  "graph_data": {...}
}
```

**Tab Support:** Tab 3 (situation panel)

---

### GET /api/metrics/compounding (v2 enhanced)

**Purpose:** Get compounding metrics with business impact.

**Router:** `metrics.py`

**Response (v2 additions):**
```json
{
  "period": {...},
  "headline": {...},
  "weekly_trend": [...],
  "evolution_events": [...],
  "business_impact": {  // ★ NEW Wave 6C
    "analyst_hours_saved_monthly": 847,
    "cost_avoided_quarterly": 127000,
    "mttr_reduction_pct": 75,
    "alert_backlog_eliminated_monthly": 2400
  }
}
```

**Tab Support:** Tab 4 (business impact banner)

---

## V2 NEW FRONTEND FEATURES

### Tab 2: Runtime Evolution (Enhanced)

**Wave 1 Additions:**
- **CMA Labels:**
  - CONSUME badge (blue) on Eval Gate panel
  - MUTATE badge (purple) on TRIGGERED_EVOLUTION panel
- **Eval Gate Sequential Animation:**
  - 800ms delay per check
  - Opacity + translate transition
  - Clock spinner during "Checking..." state

**Wave 2 Additions:**
- **"Simulate Failed Gate" button:**
  - Calls `POST /api/alert/process-blocked`
  - Danger-themed button (red/amber)
- **BLOCKED Banner:**
  - Shown when `overall_passed: false`
  - Red gradient background
  - Shield icon
  - Reason text
  - "Escalated to human reviewer" message

**Wave 5 Additions:**
- **AgentEvolver Panel (purple theme):**
  - Variant comparison bars (current vs previous success rate)
  - Promotion status badge (green "Promoted ✓" or gray "Active (monitoring)")
  - Promotion reason text

**Wave 6B Additions:**
- **"What Changed" box:**
  - Lightbulb icon
  - Italic plain English narrative
  - Subtle bordered box
- **Operational Impact Cards (5 cards):**
  - Card 1: Fewer false escalations % (green)
  - Card 2: Fewer Tier 2 reviews/mo (green)
  - Card 3: Analyst hours recovered/mo (green)
  - Card 4: Monthly savings (green, $, bold)
  - Card 5: Missed threats (blue, shield icon, always 0)

**Key Message:**
> "Loop 2 makes the agent smarter ACROSS decisions by learning which prompts work best."

---

### Tab 3: Alert Triage (Enhanced)

**Wave 1 Additions:**
- **CMA Label:**
  - ACTIVATE badge (green) on recommendation panel

**Wave 4 Additions:**
- **Situation Analyzer Panel:**
  - Situation type badge with color coding (blue, green, orange, red, gray, yellow)
  - Key factors list (3-5 bullet points)
  - Options bar chart (Recharts horizontal bars, confidence %)
  - Situation reasoning text

**Wave 6A Additions:**
- **Decision Economics in Options:**
  - Time column: "3 sec", "45 min", "2 hr"
  - Cost column: "$0", "$43", "$127"
  - Risk column: "None", "Low", "Medium", "High"
  - Color-coded risk (green/yellow/orange/red)
- **Economics Summary Box:**
  - Time saved
  - Cost avoided
  - Monthly projection
  - Clock + dollar icons

**Alert Queue Updates:**
- Now includes ALERT-7824 (phishing - Mary Chen)

---

### Tab 4: Compounding Dashboard (Enhanced)

**Wave 1 Additions:**
- **Counter Animations:**
  - `useCountUp` custom hook
  - 3-second count-up with ease-out easing
  - Applied to Week 4 numbers: nodes, auto-close rate, MTTR, FP investigations

**Wave 6C Additions:**
- **Business Impact Banner:**
  - Positioned at top, below header
  - 4 animated metric cards in flex row:
    1. **Analyst Hours Saved / Month:** 847 (clock icon, green)
    2. **Cost Avoided / Quarter:** $127K (dollar icon, blue, bold)
    3. **MTTR Reduction:** 75% (trending-down icon, purple)
    4. **Alert Backlog Eliminated / Month:** 2,400 (check-circle icon, emerald)
  - Executive summary styling (gradient, borders)
  - CFO reporting message

**Wave 6D Additions:**
- **Two-Loop Hero Diagram:**
  - Dark slate background (from-slate-900 via-slate-800)
  - **Center:** Context Graph (Neo4j) with pulse animation, yellow border, Database icon
  - **Left:** Loop 1 - Situation Analyzer (blue theme):
    - Title: "LOOP 1: SITUATION ANALYZER"
    - Subtitle: "Smarter WITHIN each decision"
    - 3 bullets: Classifies, Evaluates, Reasons
    - Footer: "Demo: Tab 3 →"
  - **Right:** Loop 2 - Agent Evolver (purple theme):
    - Title: "LOOP 2: AGENT EVOLVER"
    - Subtitle: "Smarter ACROSS all decisions"
    - 3 bullets: Tracks, Evolves, Promotes
    - Footer: "Demo: Tab 2 →"
  - **Bottom:** TRIGGERED_EVOLUTION connection badge (gradient, yellow border)
  - **Stats Row (3 cards):**
    - Situation Types: 2 → 6
    - Prompt Variants Evolved: 0 → 4
    - Cross-Alert Patterns: Travel: 47 | Phish: 31
  - **Key Message:** "SIEMs get better rules. Our copilot becomes a better copilot."

---

## V2 NEW ALERT TYPE

### ALERT-7824: Phishing (Mary Chen)

**Added in:** Wave 5C

**Details:**
- **User:** Mary Chen (mary.chen@company.com)
- **Title:** Marketing Manager
- **Department:** Marketing
- **Asset:** LAPTOP-MC-003
- **Alert Type:** phishing
- **Source:** susanmorgan@phishmail.com
- **Subject:** "Urgent: Update your email password"
- **Pattern:** PAT-PHISH-KNOWN (214 occurrences, 82% FP rate)
- **Campaign:** Operation DarkHook (PhishingCampaign node, November 2025)
- **Recommended Action:** auto_remediate (quarantine, block sender domain)
- **Confidence:** 94%
- **Situation Type:** KNOWN_PHISHING_CAMPAIGN

**Neo4j Relationships:**
```cypher
(alert:Alert {id: "ALERT-7824"})
  -[:DETECTED_ON]-> (laptop:Asset {hostname: "LAPTOP-MC-003"})
  -[:INVOLVES]-> (user:User {name: "Mary Chen"})
  -[:CLASSIFIED_AS]-> (type:AlertType {id: "phishing"})
  -[:MATCHES]-> (pattern:AttackPattern {id: "PAT-PHISH-KNOWN"})
  -[:PART_OF]-> (campaign:PhishingCampaign {name: "Operation DarkHook"})
```

---

## V2 ALERT TYPES TABLE (Updated)

| Type | Alert ID | User | Action | Situation Type |
|------|----------|------|--------|----------------|
| **anomalous_login** | ALERT-7823 | John Smith (travel to Singapore) | false_positive_close | TRAVEL_LOGIN_ANOMALY |
| **phishing** | ALERT-7824 | Mary Chen (suspicious email) | auto_remediate | KNOWN_PHISHING_CAMPAIGN |
| malware_detection | ALERT-7822 | (existing) | auto_remediate / escalate | CRITICAL_ASSET_MALWARE / ROUTINE_MALWARE_SCAN |
| data_exfiltration | ALERT-7821 | (existing) | escalate_incident | DATA_EXFILTRATION_DETECTED |

---

## V2 KEY ARCHITECTURE CONCEPTS

### Loop 1: Situation Analyzer (NEW)

**Concept:** Smarter WITHIN each decision.

**How it works:**
1. **Classify** the situation (6 types based on alert + context patterns)
2. **Evaluate** multiple options (3-4 per situation, not just binary)
3. **Provide economics** (time/cost/risk per option)
4. **Show reasoning** (why this situation type was chosen)

**Example:**
```
Alert: anomalous_login
Context: user_traveling=True, vpn_matches_location=True, mfa_completed=True

→ Situation Type: TRAVEL_LOGIN_ANOMALY

→ Options:
  1. Auto-close as false positive (3 sec, $0, Low risk) — 92% confidence ★
  2. Enrich with more data (2 min, $5, None risk) — 78% confidence
  3. Escalate to Tier 2 (45 min, $127, None risk) — 65% confidence

→ Economics: Saves 42 minutes vs manual triage, avoids $127 analyst cost
→ Monthly: 200 alerts × 42 min = 150 hours, $25K saved
```

**Value Proposition:**
- CISOs see: **Time and cost saved per decision**
- CFOs see: **Monthly projections in dollars**

**Tab Support:** Tab 3 (situation panel)

---

### Loop 2: Agent Evolver (NEW)

**Concept:** Smarter ACROSS all decisions.

**How it works:**
1. **Track** prompt variant performance (success rate per variant)
2. **Compare** variants within the same family (v1 vs v2)
3. **Promote** better variants automatically (>5% improvement + 10 samples)
4. **Compute** operational impact (what changed, monthly savings)

**Example:**
```
Alert Type: anomalous_login
Active Variant: TRAVEL_CONTEXT_v2 (89% success rate)
Previous: TRAVEL_CONTEXT_v1 (71% success rate)

→ Improvement: +18 percentage points

→ What Changed: "Agent learned that VPN location + travel record together indicate safe access. Previously escalated 29% of travel alerts to Tier 2 unnecessarily."

→ Operational Impact:
  - 18% fewer false escalations
  - 36 fewer Tier 2 reviews/month
  - 27 analyst hours recovered/month
  - $4,572 saved/month
  - 0 missed threats (eval gates prevent unsafe actions)
```

**Value Proposition:**
- CISOs see: **Proof that the agent improves over time**
- CFOs see: **Monthly savings from evolution**
- VCs see: **Compounding moat (competitors start at zero, we start at 127 patterns)**

**Tab Support:** Tab 2 (AgentEvolver panel)

---

### Decision Economics (NEW - Wave 6A)

**Concept:** Every option shows time, cost, and risk.

**Why it matters:**
- **CISOs** need to justify automation decisions to auditors
- **CFOs** need to see ROI in dollars and hours
- **Compliance** requires risk assessment documentation

**Implementation:**
- Each option in `evaluate_options()` includes:
  - `estimated_resolution_time`: "3 sec" / "45 min" / "2 hr"
  - `estimated_analyst_cost`: $0 / $43 / $127
  - `risk_if_wrong`: "None" / "Low" / "Medium" / "High"

**Display:**
- Tab 3: Time/Cost/Risk columns alongside option bars
- Tab 3: Economics summary box (time saved, cost avoided, monthly projection)

---

### Business Impact (NEW - Wave 6C)

**Concept:** Aggregate savings visible in Tab 4 banner.

**Metrics:**
- **Analyst Hours Saved / Month:** 847 hours
- **Cost Avoided / Quarter:** $127K
- **MTTR Reduction:** 75% (12.4 min → 3.1 min)
- **Alert Backlog Eliminated / Month:** 2,400 alerts

**Why it matters:**
- **CISOs** can present these numbers to their CFO
- **CFOs** see quarterly cost avoidance in dollars
- **Board** sees operational efficiency improvement

**Implementation:**
- Backend: `business_impact` object in `/api/metrics/compounding` response
- Frontend: 4 animated metric cards at top of Tab 4
- Animation: Counter animation (3-second count-up with ease-out)

---

### Two-Loop Diagram (NEW - Wave 6D)

**Concept:** Hero visual for VCs showing architectural differentiation.

**Layout:**
```
       ┌─────────────────────────────┐
       │   CONTEXT GRAPH (Neo4j)     │
       │   [pulse animation]         │
       └─────────────────────────────┘
                │         │
        ┌───────┘         └───────┐
        ▼                         ▼
┌─────────────────┐     ┌─────────────────┐
│  LOOP 1 (blue)  │     │  LOOP 2 (purple)│
│  Situation      │     │  Agent          │
│  Analyzer       │     │  Evolver        │
│                 │     │                 │
│  • Classifies   │     │  • Tracks       │
│  • Evaluates    │     │  • Evolves      │
│  • Reasons      │     │  • Promotes     │
└─────────────────┘     └─────────────────┘
        │                         │
        └───────┐         ┌───────┘
                ▼         ▼
       ┌─────────────────────────────┐
       │  TRIGGERED_EVOLUTION        │
       └─────────────────────────────┘
```

**Stats Row:**
- Situation Types: 2 → 6
- Prompt Variants: 0 → 4
- Cross-Alert Patterns: Travel 47 | Phishing 31

**Value Proposition:**
- **VCs** see: "Both loops write to the same graph → compounding intelligence"
- **SIEMs** have only Loop 1 (better context)
- **We** have Loop 1 + Loop 2 (better context + better agent)

**Soundbite:**
> "SIEMs get better rules. Our copilot becomes a better copilot."

**Tab Support:** Tab 4 (two-loop hero diagram)

---

## V2 SUMMARY: What Changed

| Wave | Focus | Files Changed | Key Addition |
|------|-------|---------------|--------------|
| **1** | Labels + Animation | Tab 2, 3, 4, App.tsx | CMA labels, 800ms eval gate animation, counter animations |
| **2** | Blocking Demo | evolution.py, Tab 2, api.ts | process-blocked endpoint, BLOCKED banner |
| **3** | Situation Backend | situation.py (NEW), evolution.py, triage.py | classify_situation(), evaluate_options(), 6 situation types |
| **4** | Situation Frontend | Tab 3 | Situation panel with type badge, factors, options chart |
| **5** | AgentEvolver | evolver.py (NEW), evolution.py, Tab 2, seed_neo4j.py | Prompt tracking, promotion, AgentEvolver panel, phishing alert |
| **6A** | Decision Economics | situation.py, Tab 3 | Time/cost/risk per option, economics summary |
| **6B** | Operational Impact | evolver.py, Tab 2 | What-changed narrative, 5 impact cards |
| **6C** | Business Banner | metrics.py, Tab 4 | 4 animated metrics: hours, cost, MTTR, backlog |
| **6D** | Two-Loop Diagram | Tab 4 | Hero diagram with center graph, Loop 1 & 2, stats |
| **6E** | Documentation | CLAUDE.md, PROJECT_STRUCTURE.md | V2 additions documented |

---

*CLAUDE.md for SOC Copilot Demo v2.0 | February 17, 2026*
*v1 Core (January 2026): Adapted for cybersecurity/SOC domain*
*v2 Enhancements (February 2026): Two-loop architecture with business impact visibility*
*Key principle: The demo proves the ARCHITECTURE (two loops → compounding), not agent sophistication.*
*v2 Focus: Making the business case visible to CISOs and CFOs.*
