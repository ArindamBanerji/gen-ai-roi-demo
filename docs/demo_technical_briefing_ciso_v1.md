# SOC Copilot Demo: Technical Briefing v1

**Document Type:** Detailed Design Document + Implementation Plan  
**Target Audience:** AI Coding Assistants (Claude Code, OpenAI Codex), Technical Partners  
**Domain:** Security Operations Center (SOC) — AI-powered alert triage and response  
**Build Time:** 2 weeks

---

## Document Purpose

This document provides everything an AI coding assistant needs to build the SOC Copilot demo from scratch. It includes:

1. **Architecture specifications** — What to build and why
2. **Complete schemas** — Database tables, Neo4j nodes/relationships, API contracts
3. **Code templates** — Ready-to-use patterns for all major components
4. **Implementation sequence** — Exact order of operations
5. **Verification procedures** — How to confirm correctness at each step

**Design Principle:** The demo proves the ARCHITECTURE, not agent sophistication. The agent is intentionally simple (~200 lines) because the value lives in the two-loop data flow and the TRIGGERED_EVOLUTION relationship.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Technology Stack](#3-technology-stack)
4. [Data Layer Specifications](#4-data-layer-specifications)
5. [Neo4j Schema (Complete)](#5-neo4j-schema-complete)
6. [API Specifications](#6-api-specifications)
7. [Agent Implementation](#7-agent-implementation)
8. [Frontend Specifications](#8-frontend-specifications)
9. [Implementation Sequence](#9-implementation-sequence)
10. [Verification Procedures](#10-verification-procedures)
11. [Seed Data Reference](#11-seed-data-reference)
12. [Code Templates](#12-code-templates)

---

## 1. Executive Summary

### What This Demo Is

A working application proving enterprise AI can **compound intelligence over time** — not just execute tasks, but get measurably smarter through governed context and runtime learning.

### The Two Stories

| Story | Audience | Demo Focus | Key Tabs |
|-------|----------|------------|----------|
| **"SOC Efficiency"** | CISOs / Security Leaders | Alert triage + Governance | Tab 1 (SOC Analytics) |
| **"Compounding Moat"** | VCs | Runtime Evolution + Two Loops | Tabs 2-4 |

### Tab Energy Allocation (CRITICAL)

| Tab | Name | Energy | Duration | Why |
|-----|------|--------|----------|-----|
| 1 | SOC Analytics | **20%** | 2-3 min | Immediate value — governed security metrics |
| 2 | Runtime Evolution | **35%** | 4-5 min | **★ THE DIFFERENTIATOR** — what SIEMs don't show |
| 3 | Alert Triage | 30% | 3-4 min | Shows closed-loop execution beyond "detect" |
| 4 | Compounding | 15% | 2 min | Two-loop visual is the hero |

### The Key Differentiator

```
What Traditional SIEMs Have:
  Alert → Detect → Log → Manual Tuning (one loop)

What We Add:
  Alert → Detect → Log → Manual Tuning (Loop 1: Better Detection)
                     └─→ TRIGGERED_EVOLUTION → Better Agent (Loop 2: Self-Improvement)
                         ↑
                THE KEY RELATIONSHIP
```

**Soundbite:** "Your SIEM gets better rules. Our SOC Copilot gets **smarter**."

---

## 2. Architecture Overview

### The "Dual Input, Dual Loop" Design

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DUAL INPUT STREAMS                                    │
│                                                                                 │
│   SOC (Structure)                         Agent Engineering (Runtime)           │
│   ─────────────────                       ──────────────────────────            │
│   • Metric contracts                      • Evaluation results                  │
│   • Asset definitions                     • Decision traces                     │
│   • SLAs by severity                      • Resolution patterns                 │
│   • Playbook procedures                   • Outcome feedback                    │
│                                                                                 │
│            │                                       │                            │
│            └───────────────────┬───────────────────┘                            │
│                                ▼                                                │
│                 ┌─────────────────────────────────┐                            │
│                 │       SEMANTIC GRAPHS           │                            │
│                 │          (Neo4j)                │                            │
│                 │                                 │                            │
│                 │  (:Decision)-[:TRIGGERED_EVOLUTION]->(:EvolutionEvent)       │
│                 │               ↑                                              │
│                 │      THE KEY RELATIONSHIP                                    │
│                 └─────────────────────────────────┘                            │
│                                │                                                │
│                 ┌──────────────┴──────────────┐                                │
│                 ▼                             ▼                                │
│      ┌─────────────────────┐       ┌─────────────────────┐                    │
│      │   Alert Triage      │       │   Runtime Evolution │                    │
│      │     (Loop 1)        │       │     (Loop 2) ★      │                    │
│      │                     │       │                     │                    │
│      │ • Better search     │       │ • Better agent      │                    │
│      │ • Better precedent  │       │ • Self-tuning       │                    │
│      │ • SIEMs have this ✓ │       │ • SIEMs LACK this ✗ │                    │
│      └──────────┬──────────┘       └──────────┬──────────┘                    │
│                 │                              │                               │
│                 └──────────────┬───────────────┘                               │
│                                │ FEEDBACK                                      │
│                                ▼                                               │
│                 ┌─────────────────────────┐                                    │
│                 │    Back to Graph        │                                    │
│                 │    (COMPOUNDING)        │                                    │
│                 └─────────────────────────┘                                    │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Why Three Databases?

| Database | What It Holds | Primary Tab | Why This DB |
|----------|---------------|-------------|-------------|
| **BigQuery** | Metric contracts, time-series SOC data | Tab 1 | Fast analytics, SQL interface |
| **Firestore** | Alerts, decisions, deployments | Tab 2 | Real-time, document model |
| **Neo4j** | Entities, patterns, **decision traces** | Tabs 3-4 | Graph traversal, pattern matching |

### Agent Architecture

The agent is **intentionally simple** — 2 files, ~200 lines total:

```
backend/app/services/
├── agent.py       # ~150 lines — Rule-based decision engine + trace writer
└── reasoning.py   # ~50 lines  — LLM prompt templates for narration only
```

**Why simple?**

| Benefit | Explanation |
|---------|-------------|
| **Demo reliability** | Rule-based = same decision every time |
| **Auditability** | CISOs need to explain decisions to auditors |
| **Faster build** | ~200 lines vs ~1000+ lines |
| **Clear separation** | Architecture proves the thesis, not AI magic |

---

## 3. Technology Stack

```yaml
# Complete technology stack for SOC Copilot Demo

frontend:
  framework: React 18.2+
  language: TypeScript 5.0+
  styling: Tailwind CSS 3.4+
  components: shadcn/ui
  charts: Recharts 2.10+
  graph_viz: NVL (Neo4j Visualization Library) or React Force Graph
  state: useState only (no Redux/Zustand)
  build: Vite 5+

backend:
  framework: FastAPI 0.109+
  language: Python 3.11+
  validation: Pydantic v2
  async: asyncio + httpx

databases:
  analytics: Google BigQuery
  operational: Google Firestore (Native mode)
  semantic: Neo4j Aura (Free tier sufficient for demo)

ai:
  provider: Google Vertex AI
  model: Gemini 1.5 Pro (gemini-1.5-pro-002)
  usage: NARRATION ONLY (not decision-making)

infrastructure:
  compute: Google Cloud Run
  region: us-central1
  project_id: soc-copilot-demo

development:
  ai_assistant: Claude Code (primary), OpenAI Codex (secondary)
  ide: VS Code with Python + TypeScript extensions
  notebook: Google Colab Pro (for infrastructure setup)
```

### Package Versions (Pin These)

```
# backend/requirements.txt
fastapi==0.109.2
pydantic==2.6.1
uvicorn==0.27.1
google-cloud-bigquery==3.17.2
google-cloud-firestore==2.14.0
google-cloud-aiplatform==1.42.1
neo4j==5.17.0
python-dotenv==1.0.1
httpx==0.26.0

# frontend/package.json (key dependencies)
"react": "^18.2.0"
"typescript": "^5.3.3"
"tailwindcss": "^3.4.1"
"recharts": "^2.10.4"
"@radix-ui/react-*": "latest"  # shadcn/ui dependencies
```

---

## 4. Data Layer Specifications

### 4.1 BigQuery Schema

**Dataset:** `soc`

#### Table: `metric_contracts`

```sql
CREATE TABLE `soc.metric_contracts` (
  metric_id STRING NOT NULL,
  version INT64 NOT NULL,
  name STRING NOT NULL,
  definition STRING,
  formula STRING,
  owner_email STRING,
  grain ARRAY<STRING>,
  source_tables ARRAY<STRING>,
  join_logic STRING,
  filters_allowed ARRAY<STRING>,
  freshness_sla_hours INT64,
  quality_threshold FLOAT64,
  status STRING,  -- 'active', 'deprecated', 'draft'
  deprecated_by STRING,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

#### Table: `soc_metrics`

```sql
CREATE TABLE `soc.soc_metrics` (
  date DATE NOT NULL,
  severity STRING NOT NULL,  -- 'critical', 'high', 'medium', 'low'
  alert_type STRING,
  alerts_received INT64,
  alerts_auto_closed INT64,
  alerts_escalated_tier2 INT64,
  alerts_escalated_ir INT64,
  avg_mttr_minutes FLOAT64,
  avg_mttd_minutes FLOAT64,
  fp_count INT64,
  tp_count INT64
);
```

#### Table: `detection_rules`

```sql
CREATE TABLE `soc.detection_rules` (
  rule_id STRING NOT NULL,
  name STRING NOT NULL,
  description STRING,
  mitre_technique STRING,
  severity STRING,
  alerts_last_30d INT64,
  fp_rate FLOAT64,
  status STRING,  -- 'active', 'deprecated', 'testing'
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

#### Table: `rule_sprawl_registry`

```sql
CREATE TABLE `soc.rule_sprawl_registry` (
  rule_id STRING NOT NULL,
  similar_rule_id STRING NOT NULL,
  similarity_score FLOAT64,
  pipeline_count INT64,
  monthly_alert_impact INT64,
  estimated_monthly_cost FLOAT64,
  status STRING,  -- 'reviewing', 'approved', 'ignored'
  detected_at TIMESTAMP
);
```

### 4.2 Firestore Collections

**Database:** `(default)` Native Mode

#### Collection: `alerts`

```typescript
interface Alert {
  alert_id: string;           // "ALERT-7823"
  alert_type: string;         // "anomalous_login" | "phishing" | "malware_detection" | "data_exfiltration"
  severity: string;           // "critical" | "high" | "medium" | "low"
  source: string;             // "Splunk" | "CrowdStrike" | "Proofpoint" | "DLP"
  source_rule_id: string;
  asset_id: string;
  asset_hostname: string;
  user_id: string;
  source_location: string;
  source_ip: string;
  timestamp: Timestamp;
  status: string;             // "pending" | "investigating" | "resolved" | "escalated"
  description: string;
  dlp_classification?: string; // for data_exfiltration alerts
}
```

#### Collection: `assets`

```typescript
interface Asset {
  asset_id: string;           // "LAPTOP-JSMITH"
  hostname: string;
  type: string;               // "endpoint" | "server" | "network" | "cloud"
  os: string;
  criticality: string;        // "critical" | "high" | "medium" | "low"
  business_unit: string;
  owner_id: string;
  last_seen: Timestamp;
}
```

#### Collection: `users`

```typescript
interface User {
  user_id: string;            // "jsmith@company.com"
  name: string;
  title: string;
  department: string;
  risk_score: number;         // 0.0 - 1.0
  is_privileged: boolean;
  manager: string | null;
}
```

#### Collection: `playbooks`

```typescript
interface Playbook {
  playbook_id: string;        // "PB-LOGIN-001"
  name: string;
  description: string;
  alert_types: string[];
  steps: string[];
  auto_actions: string[];     // "false_positive_close", "auto_remediate"
  escalation_actions: string[];
  sla_minutes: number;
  owner: string;
}
```

#### Collection: `patterns`

```typescript
interface AttackPattern {
  pattern_id: string;         // "PAT-TRAVEL-001"
  name: string;
  description: string;
  alert_types: string[];
  match_criteria: Record<string, any>;
  fp_rate: number;            // 0.0 - 1.0
  occurrence_count: number;
  confidence: number;         // 0.0 - 1.0
  recommended_action: string;
  created_at: Timestamp;
  updated_at: Timestamp;
}
```

#### Collection: `deployments`

```typescript
interface Deployment {
  deployment_id: string;      // "soc-copilot-v3.1"
  agent_name: string;
  version: string;
  status: string;             // "active" | "canary" | "inactive"
  traffic_pct: number;
  deployed_at: Timestamp;
  config: {
    auto_close_threshold: number;
    escalation_threshold: number;
    model: string;
  };
  metrics_7d: {
    alerts_processed: number;
    auto_close_rate: number;
    avg_confidence: number;
    escalation_rate: number;
  };
}
```

#### Collection: `decisions`

```typescript
interface Decision {
  decision_id: string;        // "DEC-7823"
  alert_id: string;
  action: string;             // "false_positive_close" | "auto_remediate" | "escalate_tier2" | "escalate_incident"
  confidence: number;
  pattern_id: string | null;
  reasoning: string;
  eval_gate_passed: boolean;
  executed_at: Timestamp;
  created_by: string;         // deployment version
}
```

#### Collection: `travel`

```typescript
interface TravelRecord {
  travel_id: string;
  user_id: string;
  destination: string;
  start_date: string;         // "YYYY-MM-DD"
  end_date: string;
  purpose: string;
  vpn_expected: string[];
  approved_by: string;
}
```

---

## 5. Neo4j Schema (Complete)

### 5.1 Node Definitions

```cypher
// ═══════════════════════════════════════════════════════════════════════════════
// CORE SECURITY ENTITIES
// ═══════════════════════════════════════════════════════════════════════════════

// Asset — devices, servers, network equipment
(:Asset {
  id: string,               // "LAPTOP-JSMITH"
  hostname: string,
  type: string,             // "endpoint", "server", "network", "cloud"
  os: string,
  criticality: string,      // "critical", "high", "medium", "low"
  business_unit: string,
  owner_id: string
})

// User — employees, service accounts
(:User {
  id: string,               // "jsmith@company.com"
  name: string,
  title: string,
  department: string,
  risk_score: float,        // 0.0 - 1.0
  is_privileged: boolean
})

// AlertType — categories of security alerts
(:AlertType {
  id: string,               // "anomalous_login"
  name: string,
  severity: string,
  mitre_technique: string
})

// AttackPattern — learned patterns from historical decisions
(:AttackPattern {
  id: string,               // "PAT-TRAVEL-001"
  name: string,
  fp_rate: float,
  occurrence_count: integer,
  confidence: float
})

// Playbook — SOC response procedures
(:Playbook {
  id: string,               // "PB-LOGIN-001"
  name: string,
  sla_minutes: integer
})

// SLA — service level agreements by severity
(:SLA {
  id: string,               // "SLA-CRITICAL"
  name: string,
  response_time_minutes: integer,
  severity: string
})

// TravelContext — employee travel records
(:TravelContext {
  id: string,               // "TRAVEL-001"
  user_id: string,
  destination: string,
  start_date: date,
  end_date: date
})

// Alert — security alert instance (for demo)
(:Alert {
  id: string,               // "ALERT-7823"
  alert_type: string,
  severity: string,
  source: string,
  source_location: string,
  timestamp: datetime,
  status: string,
  description: string
})

// ═══════════════════════════════════════════════════════════════════════════════
// DECISION TRACE ENTITIES (THE KEY DIFFERENTIATOR)
// ═══════════════════════════════════════════════════════════════════════════════

// Decision — a triage decision made by the agent
(:Decision {
  id: string,               // "DEC-7823"
  type: string,             // "alert_triage"
  reasoning: string,        // LLM-generated explanation
  confidence: float,
  timestamp: datetime,
  alert_id: string,
  action_taken: string      // "false_positive_close", "auto_remediate", etc.
})

// DecisionContext — snapshot of all context at decision time
(:DecisionContext {
  id: string,               // "CTX-7823"
  decision_id: string,
  user_snapshot: string,    // JSON string of user state
  asset_snapshot: string,   // JSON string of asset state
  patterns_matched: [string],
  nodes_consulted: integer  // Total graph nodes examined
})

// EvolutionEvent — record of agent self-improvement
(:EvolutionEvent {
  id: string,               // "EVO-0891"
  event_type: string,       // "pattern_confidence", "threshold_adjustment", "new_pattern"
  triggered_by: string,     // Decision ID that caused this
  before_state: string,     // JSON of state before
  after_state: string,      // JSON of state after
  description: string,
  timestamp: datetime
})
```

### 5.2 Relationship Definitions

```cypher
// ═══════════════════════════════════════════════════════════════════════════════
// CORE ENTITY RELATIONSHIPS
// ═══════════════════════════════════════════════════════════════════════════════

// User owns/uses Asset
(:User)-[:ASSIGNED_TO]->(:Asset)

// User has travel context
(:User)-[:HAS_TRAVEL]->(:TravelContext)

// Asset subject to SLA (via criticality)
(:Asset)-[:SUBJECT_TO]->(:SLA)

// AlertType handled by Playbook
(:AlertType)-[:HANDLED_BY]->(:Playbook)

// Alert relationships
(:Alert)-[:DETECTED_ON]->(:Asset)
(:Alert)-[:INVOLVES]->(:User)
(:Alert)-[:CLASSIFIED_AS]->(:AlertType)
(:Alert)-[:MATCHES]->(:AttackPattern)

// ═══════════════════════════════════════════════════════════════════════════════
// DECISION TRACE RELATIONSHIPS
// ═══════════════════════════════════════════════════════════════════════════════

// Decision had context
(:Decision)-[:HAD_CONTEXT]->(:DecisionContext)

// Decision was for alert
(:Decision)-[:FOR_ALERT]->(:Alert)

// Decision followed playbook
(:Decision)-[:FOLLOWED]->(:Playbook)

// Decision matched pattern
(:Decision)-[:MATCHED_PATTERN]->(:AttackPattern)

// ═══════════════════════════════════════════════════════════════════════════════
// CAUSAL CHAIN RELATIONSHIPS (Neo4j compatible)
// ═══════════════════════════════════════════════════════════════════════════════

// Decision caused another decision (causal chain)
(:Decision)-[:CAUSED {
  reason: string,
  timestamp: datetime,
  mechanism: string
}]->(:Decision)

// Decision serves as precedent for another
(:Decision)-[:PRECEDENT_FOR {
  similarity: float,
  precedent_type: string,
  cited_in_reasoning: boolean
}]->(:Decision)

// ═══════════════════════════════════════════════════════════════════════════════
// THE KEY RELATIONSHIP — WHAT SIEMS DON'T HAVE
// ═══════════════════════════════════════════════════════════════════════════════

// Decision TRIGGERED agent evolution
(:Decision)-[:TRIGGERED_EVOLUTION {
  impact: string,           // "pattern_confidence_increase", "threshold_adjustment", "new_pattern_created"
  magnitude: float,         // Quantified impact (e.g., 0.03 for 3% increase)
  timestamp: datetime
}]->(:EvolutionEvent)
```

### 5.3 Expected Node Counts

| Node Type | Count | Notes |
|-----------|-------|-------|
| Asset | 5 | Mix of endpoints and servers |
| User | 5 | Various risk levels |
| AlertType | 4 | anomalous_login, phishing, malware, data_exfil |
| AttackPattern | 5 | Learned patterns |
| Playbook | 4 | Response procedures |
| SLA | 3 | By severity |
| TravelContext | 2 | Active travel records |
| Alert | 5 | Sample alerts |
| Decision | 5 | Sample decisions |
| DecisionContext | 5 | Context snapshots |
| EvolutionEvent | 3 | Agent improvements |
| **TOTAL** | **~46** | |

### 5.4 Expected Relationship Counts

| Relationship Type | Count | Notes |
|-------------------|-------|-------|
| ASSIGNED_TO | 3 | User → Asset |
| HAS_TRAVEL | 2 | User → TravelContext |
| SUBJECT_TO | 5 | Asset → SLA |
| HANDLED_BY | 4 | AlertType → Playbook |
| DETECTED_ON | 5 | Alert → Asset |
| INVOLVES | 5 | Alert → User |
| CLASSIFIED_AS | 5 | Alert → AlertType |
| MATCHES | 3 | Alert → AttackPattern |
| HAD_CONTEXT | 5 | Decision → DecisionContext |
| FOR_ALERT | 5 | Decision → Alert |
| **TRIGGERED_EVOLUTION** | **3** | **Decision → EvolutionEvent (THE KEY)** |
| CAUSED | 2 | Decision → Decision |
| PRECEDENT_FOR | 2 | Decision → Decision |
| **TOTAL** | **~49** | |

---

## 6. API Specifications

### 6.1 Base Configuration

```yaml
base_url: /api
version: v1
content_type: application/json
authentication: none (demo)
```

### 6.2 Tab 1: SOC Analytics

#### POST /api/soc/query

Natural language query for SOC metrics.

```yaml
request:
  question: string          # "What was MTTR by severity last week?"
  
response:
  matched_metric:
    id: string              # "mttr_by_severity"
    name: string
    owner: string
    definition: string
    version: integer
    
  result:
    data: array
      - label: string       # "critical", "high", etc.
        value: number       # 8.2, 14.7, etc.
    chart_type: string      # "bar" | "line" | "number"
    unit: string            # "minutes", "percent", etc.
    
  provenance:
    sources: string[]       # ["Splunk", "ServiceNow"]
    freshness_hours: number
    quality_score: number   # 0.0 - 1.0
    query_preview: string   # SQL or query explanation
    
  sprawl_alert: object | null
    duplicate_rule: string
    active_in_pipelines: number
    monthly_alert_impact: number
    estimated_monthly_cost: number
```

### 6.3 Tab 2: Runtime Evolution

#### GET /api/deployments

List agent deployments.

```yaml
response:
  deployments: array
    - deployment_id: string
      agent_name: string
      version: string
      status: string        # "active" | "canary" | "inactive"
      traffic_pct: number
      deployed_at: string   # ISO datetime
      config:
        auto_close_threshold: number
        escalation_threshold: number
        model: string
      metrics_7d:
        alerts_processed: number
        auto_close_rate: number
        avg_confidence: number
        escalation_rate: number
```

#### POST /api/alert/process

Process an alert through the agent.

```yaml
request:
  alert_id: string
  deployment_version: string  # optional, for canary routing
  
response:
  alert_id: string
  routed_to: string           # deployment version that handled it
  
  eval_gate:
    checks: array
      - name: string          # "Faithfulness", "Safe Action", etc.
        score: number
        threshold: number
        passed: boolean
    overall_passed: boolean
    
  decision:
    decision_id: string
    action: string            # "false_positive_close", etc.
    confidence: number
    pattern_matched: string | null
    reasoning: string         # LLM-generated explanation
    
  execution:
    status: string            # "executed" | "blocked"
    reason: string | null     # if blocked
    
  triggered_evolution: object | null
    evolution_id: string
    event_type: string
    description: string
    before_state: object
    after_state: object
```

#### POST /api/eval/simulate-failure

Simulate a failed eval gate for demo.

```yaml
request:
  alert_id: string
  fail_check: string          # "safe_action" | "faithfulness" | etc.
  
response:
  # Same as POST /api/alert/process but with:
  eval_gate:
    overall_passed: false
  execution:
    status: "blocked"
    reason: string
```

### 6.4 Tab 3: Alert Triage

#### GET /api/alerts/queue

Get pending alerts.

```yaml
response:
  alerts: array
    - alert_id: string
      alert_type: string
      severity: string
      asset_hostname: string
      user_name: string
      source_location: string
      timestamp: string
      description: string
      status: string
```

#### POST /api/alert/analyze

Analyze an alert with full graph traversal.

```yaml
request:
  alert_id: string
  
response:
  alert: object              # Full alert details
  
  context:
    user:
      name: string
      title: string
      risk_score: number
      travel_status: object | null
    asset:
      hostname: string
      criticality: string
      os: string
    patterns_checked: array
      - pattern_id: string
        name: string
        match_score: number
        matched: boolean
    playbook:
      id: string
      name: string
      sla_minutes: number
      
  graph_stats:
    nodes_consulted: number   # e.g., 47
    subgraphs_traversed: array  # ["user", "asset", "patterns", "history"]
    query_time_ms: number
    
  recommendation:
    action: string
    confidence: number
    reasoning: string
    pattern_matched: string | null
```

#### POST /api/action/execute

Execute a recommended action.

```yaml
request:
  alert_id: string
  decision_id: string
  action: string
  
response:
  execution:
    step_1_execute:
      status: string          # "completed"
      detail: string          # "Alert status updated in SIEM"
    step_2_verify:
      status: string
      detail: string          # "No follow-up ticket created"
    step_3_evidence:
      status: string
      detail: string          # "Decision trace DEC-7823 captured"
    step_4_kpi_impact:
      status: string
      detail: string          # "MTTR improved by 4.2 minutes"
      
  closed_loop_complete: boolean
```

### 6.5 Tab 4: Compounding Dashboard

#### GET /api/metrics/compounding

Get compounding metrics over time.

```yaml
query_params:
  weeks: number               # default 4
  
response:
  headline:
    week_1:
      auto_close_rate: number
      mttr_minutes: number
      patterns_count: number
      graph_nodes: number
    week_current:
      auto_close_rate: number
      mttr_minutes: number
      patterns_count: number
      graph_nodes: number
    improvements:
      auto_close_delta: string  # "+21 pts"
      mttr_delta: string        # "-75%"
      patterns_delta: string    # "+452%"
      
  time_series: array
    - week: number
      auto_close_rate: number
      mttr_minutes: number
      patterns_count: number
      
  evolution_events: array
    - id: string
      event_type: string
      description: string
      triggered_by: string
      timestamp: string
      
  two_loop_stats:
    loop_1_decisions: number
    loop_2_evolutions: number
    feedback_ratio: number    # evolutions / decisions
```

### 6.6 Utility Endpoints

#### POST /api/demo/reset

Reset demo data to initial state.

```yaml
response:
  status: string              # "reset_complete"
  alerts_reset: number
  decisions_cleared: number
```

#### GET /api/health

Health check.

```yaml
response:
  status: string              # "healthy"
  bigquery: boolean
  firestore: boolean
  neo4j: boolean
  vertex_ai: boolean
```

---

## 7. Agent Implementation

### 7.1 File Structure

```
backend/app/services/
├── agent.py           # ~150 lines — Decision engine + trace writer
├── reasoning.py       # ~50 lines  — LLM prompt templates
├── eval_gate.py       # ~80 lines  — Four deterministic checks
└── evolution.py       # ~60 lines  — Trigger evolution events
```

### 7.2 Decision Engine (agent.py)

```python
# backend/app/services/agent.py
"""
SOC Copilot Decision Engine

This is the core agent logic. It is INTENTIONALLY SIMPLE because:
1. Demo reliability — rule-based = same decision every time
2. Auditability — CISOs need to explain decisions
3. Faster build — ~150 lines vs ~1000+ lines
4. Clear separation — architecture proves thesis, not AI magic

The LLM is used for NARRATION ONLY (reasoning.py).
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum
from datetime import datetime
import uuid

class Action(Enum):
    FALSE_POSITIVE_CLOSE = "false_positive_close"
    AUTO_REMEDIATE = "auto_remediate"
    ENRICH_AND_WAIT = "enrich_and_wait"
    ESCALATE_TIER2 = "escalate_tier2"
    ESCALATE_INCIDENT = "escalate_incident"

@dataclass
class Decision:
    action: Action
    confidence: float
    pattern_id: Optional[str]
    reasoning_context: dict

@dataclass
class SecurityContext:
    """Context gathered from graph traversal."""
    # User context
    user_name: str
    user_title: str
    user_risk_score: float
    user_traveling: bool = False
    travel_destination: Optional[str] = None
    
    # Asset context
    asset_hostname: str
    asset_criticality: str
    
    # Authentication context
    vpn_matches_location: bool = False
    vpn_provider: Optional[str] = None
    mfa_completed: bool = False
    device_fingerprint_match: bool = False
    
    # Alert-specific context
    known_campaign_signature: bool = False
    campaign_id: Optional[str] = None
    hash_confirmed: bool = False
    data_classification: Optional[str] = None
    
    # Graph stats
    nodes_consulted: int = 0

def decide(alert: dict, context: SecurityContext) -> Decision:
    """
    Rule-based decision logic. Intentionally simple.
    The demo proves architecture, not agent sophistication.
    
    Args:
        alert: Alert document from Firestore
        context: Security context gathered from graph traversal
        
    Returns:
        Decision with action, confidence, and reasoning context
    """
    alert_type = alert.get("alert_type", "")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RULE 1: Anomalous Login
    # ═══════════════════════════════════════════════════════════════════════════
    if alert_type == "anomalous_login":
        # Check travel context first (most common FP case)
        if context.user_traveling and context.vpn_matches_location:
            if context.mfa_completed and context.device_fingerprint_match:
                return Decision(
                    action=Action.FALSE_POSITIVE_CLOSE,
                    confidence=0.92,
                    pattern_id="PAT-TRAVEL-001",
                    reasoning_context={
                        "template": "travel_false_positive",
                        "travel_dest": context.travel_destination,
                        "vpn_provider": context.vpn_provider,
                        "nodes_consulted": context.nodes_consulted
                    }
                )
        
        # High-value target without travel context → escalate immediately
        if context.user_risk_score > 0.8:
            return Decision(
                action=Action.ESCALATE_INCIDENT,
                confidence=0.95,
                pattern_id=None,
                reasoning_context={
                    "template": "high_value_target",
                    "risk_score": context.user_risk_score,
                    "user_title": context.user_title
                }
            )
        
        # Known VPN provider → likely FP
        if context.vpn_provider and context.device_fingerprint_match:
            return Decision(
                action=Action.FALSE_POSITIVE_CLOSE,
                confidence=0.88,
                pattern_id="PAT-VPN-KNOWN",
                reasoning_context={
                    "template": "known_vpn",
                    "vpn_provider": context.vpn_provider
                }
            )
        
        # Default: escalate to Tier 2 for review
        return Decision(
            action=Action.ESCALATE_TIER2,
            confidence=0.72,
            pattern_id=None,
            reasoning_context={"template": "default_escalate"}
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RULE 2: Phishing
    # ═══════════════════════════════════════════════════════════════════════════
    elif alert_type == "phishing":
        if context.known_campaign_signature:
            return Decision(
                action=Action.AUTO_REMEDIATE,
                confidence=0.94,
                pattern_id="PAT-PHISH-KNOWN",
                reasoning_context={
                    "template": "known_phishing",
                    "campaign_id": context.campaign_id,
                    "auto_action": "quarantine_email"
                }
            )
        
        # Unknown phishing → escalate for analysis
        return Decision(
            action=Action.ESCALATE_TIER2,
            confidence=0.85,
            pattern_id=None,
            reasoning_context={"template": "unknown_phishing"}
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RULE 3: Malware Detection
    # ═══════════════════════════════════════════════════════════════════════════
    elif alert_type == "malware_detection":
        # Critical asset → always escalate to IR
        if context.asset_criticality == "critical":
            return Decision(
                action=Action.ESCALATE_INCIDENT,
                confidence=0.96,
                pattern_id=None,
                reasoning_context={
                    "template": "critical_asset_malware",
                    "hostname": context.asset_hostname,
                    "auto_action": "isolate_endpoint"
                }
            )
        
        # Non-critical with confirmed hash → auto-remediate
        if context.hash_confirmed:
            return Decision(
                action=Action.AUTO_REMEDIATE,
                confidence=0.91,
                pattern_id="PAT-MALWARE-ISOLATE",
                reasoning_context={
                    "template": "confirmed_malware",
                    "auto_action": "isolate_endpoint"
                }
            )
        
        # Default: escalate
        return Decision(
            action=Action.ESCALATE_TIER2,
            confidence=0.78,
            pattern_id=None,
            reasoning_context={"template": "malware_review"}
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RULE 4: Data Exfiltration
    # ═══════════════════════════════════════════════════════════════════════════
    elif alert_type == "data_exfiltration":
        # Data exfil ALWAYS escalates — no auto-close
        if context.data_classification in ["confidential", "restricted"]:
            return Decision(
                action=Action.ESCALATE_INCIDENT,
                confidence=0.97,
                pattern_id=None,
                reasoning_context={
                    "template": "data_exfil_sensitive",
                    "classification": context.data_classification,
                    "user_privileged": context.user_risk_score > 0.5
                }
            )
        
        return Decision(
            action=Action.ESCALATE_TIER2,
            confidence=0.88,
            pattern_id=None,
            reasoning_context={"template": "data_exfil_review"}
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # FALLBACK: Unknown alert type
    # ═══════════════════════════════════════════════════════════════════════════
    return Decision(
        action=Action.ESCALATE_TIER2,
        confidence=0.50,
        pattern_id=None,
        reasoning_context={"template": "unknown_alert_type"}
    )


def generate_decision_id() -> str:
    """Generate a unique decision ID."""
    return f"DEC-{uuid.uuid4().hex[:8].upper()}"


async def write_decision_trace(
    decision: Decision,
    alert: dict,
    context: SecurityContext,
    neo4j_session
) -> str:
    """
    Write decision trace to Neo4j.
    This is what makes our demo different — capturing the full context.
    """
    decision_id = generate_decision_id()
    context_id = f"CTX-{decision_id[4:]}"
    
    # Create Decision node
    await neo4j_session.run("""
        CREATE (d:Decision {
            id: $decision_id,
            type: 'alert_triage',
            reasoning: $reasoning,
            confidence: $confidence,
            timestamp: datetime(),
            alert_id: $alert_id,
            action_taken: $action
        })
    """, {
        "decision_id": decision_id,
        "reasoning": "",  # Will be filled by LLM
        "confidence": decision.confidence,
        "alert_id": alert["alert_id"],
        "action": decision.action.value
    })
    
    # Create DecisionContext node
    await neo4j_session.run("""
        CREATE (c:DecisionContext {
            id: $context_id,
            decision_id: $decision_id,
            user_snapshot: $user_snapshot,
            asset_snapshot: $asset_snapshot,
            patterns_matched: $patterns,
            nodes_consulted: $nodes
        })
    """, {
        "context_id": context_id,
        "decision_id": decision_id,
        "user_snapshot": f'{{"name": "{context.user_name}", "risk_score": {context.user_risk_score}}}',
        "asset_snapshot": f'{{"hostname": "{context.asset_hostname}", "criticality": "{context.asset_criticality}"}}',
        "patterns": [decision.pattern_id] if decision.pattern_id else [],
        "nodes": context.nodes_consulted
    })
    
    # Create HAD_CONTEXT relationship
    await neo4j_session.run("""
        MATCH (d:Decision {id: $decision_id})
        MATCH (c:DecisionContext {id: $context_id})
        CREATE (d)-[:HAD_CONTEXT]->(c)
    """, {"decision_id": decision_id, "context_id": context_id})
    
    # Create FOR_ALERT relationship
    await neo4j_session.run("""
        MATCH (d:Decision {id: $decision_id})
        MATCH (a:Alert {id: $alert_id})
        CREATE (d)-[:FOR_ALERT]->(a)
    """, {"decision_id": decision_id, "alert_id": alert["alert_id"]})
    
    return decision_id
```

### 7.3 LLM Narration (reasoning.py)

```python
# backend/app/services/reasoning.py
"""
LLM Narration Module

The LLM's ONLY job is to make rule-based decisions sound intelligent.
It does NOT make decisions — that's done by agent.py.
"""

from vertexai.generative_models import GenerativeModel

# Prompt templates for each decision scenario
TEMPLATES = {
    "travel_false_positive": """
Write a 2-sentence security analyst justification for closing this login alert as a false positive.

Context:
- User is traveling to {travel_dest}
- Login originated from VPN provider: {vpn_provider}
- MFA was completed successfully
- Device fingerprint matched known device
- {nodes_consulted} graph nodes were consulted

Write as if you are the SOC Copilot explaining your reasoning to a senior analyst.
""",

    "high_value_target": """
Write a 2-sentence security analyst justification for escalating this alert to incident response.

Context:
- User: {user_title}
- User risk score: {risk_score:.0%} (high-value target)
- Anomalous login detected without valid travel context

Write as if you are the SOC Copilot explaining why immediate escalation is required.
""",

    "known_phishing": """
Write a 2-sentence security analyst justification for auto-remediating this phishing alert.

Context:
- Email matched known phishing campaign: {campaign_id}
- Action taken: {auto_action}
- Campaign signature has 94% confidence

Write as if you are the SOC Copilot explaining the auto-remediation.
""",

    "critical_asset_malware": """
Write a 2-sentence security analyst justification for escalating this malware alert.

Context:
- Asset: {hostname}
- Asset criticality: CRITICAL (production database)
- Immediate isolation recommended

Write as if you are the SOC Copilot explaining why IR escalation is required.
""",

    "known_vpn": """
Write a 2-sentence security analyst justification for closing this login alert.

Context:
- Login from known VPN provider: {vpn_provider}
- Device fingerprint matched known device
- Pattern PAT-VPN-KNOWN matched (96% confidence)

Write as if you are the SOC Copilot explaining the false positive determination.
""",

    "default_escalate": """
Write a 2-sentence security analyst justification for escalating this alert for human review.

Context:
- Alert requires additional context that automated analysis cannot provide
- Escalating to Tier 2 analyst for investigation

Write as if you are the SOC Copilot explaining why human review is needed.
"""
}


async def generate_reasoning(decision_context: dict) -> str:
    """
    Generate LLM narration for a decision.
    
    Args:
        decision_context: Dictionary with 'template' key and context variables
        
    Returns:
        2-sentence reasoning explanation
    """
    template_name = decision_context.get("template", "default_escalate")
    template = TEMPLATES.get(template_name, TEMPLATES["default_escalate"])
    
    # Fill in template variables
    prompt = template.format(**{
        k: v for k, v in decision_context.items() 
        if k != "template"
    })
    
    model = GenerativeModel("gemini-1.5-pro-002")
    response = await model.generate_content_async(
        prompt,
        generation_config={
            "temperature": 0.3,  # Low temperature for consistency
            "max_output_tokens": 150,
        }
    )
    
    return response.text.strip()
```

### 7.4 Eval Gate (eval_gate.py)

```python
# backend/app/services/eval_gate.py
"""
Evaluation Gate — Four Deterministic Quality Checks

All checks must pass before any action is executed.
This is production-grade safety, not demo-grade.
"""

from dataclasses import dataclass
from typing import List

@dataclass
class EvalCheck:
    name: str
    score: float
    threshold: float
    passed: bool
    
@dataclass
class EvalGateResult:
    checks: List[EvalCheck]
    overall_passed: bool


def run_eval_gate(
    decision_action: str,
    decision_confidence: float,
    asset_criticality: str,
    playbook_match_score: float,
    sla_remaining_pct: float
) -> EvalGateResult:
    """
    Run four deterministic quality checks.
    
    Checks:
    1. Faithfulness — Is the decision consistent with gathered context?
    2. Safe Action — Is this action safe for this asset criticality?
    3. Playbook Match — Does the decision align with the playbook?
    4. SLA Compliance — Is there enough time remaining in SLA?
    
    Returns:
        EvalGateResult with all check details and overall pass/fail
    """
    checks = []
    
    # Check 1: Faithfulness (using confidence as proxy)
    faithfulness_score = decision_confidence
    faithfulness_threshold = 0.85
    checks.append(EvalCheck(
        name="Faithfulness",
        score=faithfulness_score,
        threshold=faithfulness_threshold,
        passed=faithfulness_score >= faithfulness_threshold
    ))
    
    # Check 2: Safe Action
    # Auto-actions on critical assets are blocked
    is_auto_action = decision_action in ["false_positive_close", "auto_remediate"]
    is_critical = asset_criticality == "critical"
    
    if is_auto_action and is_critical:
        safe_action_score = 0.0
    else:
        safe_action_score = 1.0
    
    safe_action_threshold = 1.0
    checks.append(EvalCheck(
        name="Safe Action",
        score=safe_action_score,
        threshold=safe_action_threshold,
        passed=safe_action_score >= safe_action_threshold
    ))
    
    # Check 3: Playbook Match
    playbook_threshold = 0.80
    checks.append(EvalCheck(
        name="Playbook Match",
        score=playbook_match_score,
        threshold=playbook_threshold,
        passed=playbook_match_score >= playbook_threshold
    ))
    
    # Check 4: SLA Compliance
    sla_threshold = 0.10  # At least 10% of SLA remaining
    checks.append(EvalCheck(
        name="SLA Compliance",
        score=sla_remaining_pct,
        threshold=sla_threshold,
        passed=sla_remaining_pct >= sla_threshold
    ))
    
    # Overall: ALL checks must pass
    overall_passed = all(check.passed for check in checks)
    
    return EvalGateResult(checks=checks, overall_passed=overall_passed)
```

### 7.5 Evolution Trigger (evolution.py)

```python
# backend/app/services/evolution.py
"""
Evolution Event Trigger

This is THE KEY DIFFERENTIATOR — decisions trigger agent self-improvement.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any

async def maybe_trigger_evolution(
    decision_id: str,
    decision_action: str,
    pattern_id: Optional[str],
    confidence: float,
    neo4j_session
) -> Optional[Dict[str, Any]]:
    """
    Check if this decision should trigger an evolution event.
    
    Evolution triggers:
    1. Pattern confidence increase — if pattern matched and high confidence
    2. Threshold adjustment — if sustained high accuracy
    3. New pattern creation — if novel decision with high confidence
    
    Returns:
        Evolution event details if triggered, None otherwise
    """
    
    # Only trigger on successful auto-actions
    if decision_action not in ["false_positive_close", "auto_remediate"]:
        return None
    
    # Only trigger if confidence is high enough
    if confidence < 0.88:
        return None
    
    evolution_id = f"EVO-{uuid.uuid4().hex[:4].upper()}"
    
    # Scenario 1: Pattern matched — increase pattern confidence
    if pattern_id:
        # Get current pattern state
        result = await neo4j_session.run("""
            MATCH (p:AttackPattern {id: $pattern_id})
            RETURN p.confidence as confidence, p.occurrence_count as count
        """, {"pattern_id": pattern_id})
        
        record = await result.single()
        if record:
            old_confidence = record["confidence"]
            old_count = record["count"]
            
            # Increase confidence slightly (diminishing returns)
            new_confidence = min(0.99, old_confidence + 0.03 * (1 - old_confidence))
            new_count = old_count + 1
            
            # Update pattern
            await neo4j_session.run("""
                MATCH (p:AttackPattern {id: $pattern_id})
                SET p.confidence = $new_conf, p.occurrence_count = $new_count
            """, {
                "pattern_id": pattern_id,
                "new_conf": new_confidence,
                "new_count": new_count
            })
            
            # Create EvolutionEvent
            await neo4j_session.run("""
                CREATE (e:EvolutionEvent {
                    id: $evo_id,
                    event_type: 'pattern_confidence',
                    triggered_by: $decision_id,
                    before_state: $before,
                    after_state: $after,
                    description: $desc,
                    timestamp: datetime()
                })
            """, {
                "evo_id": evolution_id,
                "decision_id": decision_id,
                "before": f'{{"confidence": {old_confidence:.2f}, "occurrence_count": {old_count}}}',
                "after": f'{{"confidence": {new_confidence:.2f}, "occurrence_count": {new_count}}}',
                "desc": f"Pattern {pattern_id} confidence increased based on successful resolution"
            })
            
            # Create TRIGGERED_EVOLUTION relationship — THE KEY
            await neo4j_session.run("""
                MATCH (d:Decision {id: $decision_id})
                MATCH (e:EvolutionEvent {id: $evo_id})
                CREATE (d)-[:TRIGGERED_EVOLUTION {
                    impact: 'pattern_confidence_increase',
                    magnitude: $magnitude,
                    timestamp: datetime()
                }]->(e)
            """, {
                "decision_id": decision_id,
                "evo_id": evolution_id,
                "magnitude": new_confidence - old_confidence
            })
            
            return {
                "evolution_id": evolution_id,
                "event_type": "pattern_confidence",
                "description": f"Pattern {pattern_id} confidence: {old_confidence:.0%} → {new_confidence:.0%}",
                "before_state": {"confidence": old_confidence, "count": old_count},
                "after_state": {"confidence": new_confidence, "count": new_count}
            }
    
    return None
```

---

## 8. Frontend Specifications

### 8.1 Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/                    # shadcn/ui components
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── table.tsx
│   │   │   └── ...
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   ├── TabNavigation.tsx
│   │   │   └── Footer.tsx
│   │   ├── tab1/                  # SOC Analytics
│   │   │   ├── SOCQueryInput.tsx
│   │   │   ├── MetricResult.tsx
│   │   │   ├── GovernancePanel.tsx
│   │   │   └── RuleSprawlAlert.tsx
│   │   ├── tab2/                  # Runtime Evolution
│   │   │   ├── DeploymentRegistry.tsx
│   │   │   ├── CanaryComparison.tsx
│   │   │   ├── EvalGatePanel.tsx
│   │   │   ├── DecisionTrace.tsx
│   │   │   └── TriggeredEvolution.tsx
│   │   ├── tab3/                  # Alert Triage
│   │   │   ├── AlertQueue.tsx
│   │   │   ├── AlertDetail.tsx
│   │   │   ├── GraphVisualization.tsx
│   │   │   ├── ContextPanel.tsx
│   │   │   └── ClosedLoopExecution.tsx
│   │   └── tab4/                  # Compounding
│   │       ├── HeadlineComparison.tsx
│   │       ├── TwoLoopDiagram.tsx
│   │       ├── MetricsTrend.tsx
│   │       └── EvolutionEventsList.tsx
│   ├── pages/
│   │   ├── Tab1Page.tsx
│   │   ├── Tab2Page.tsx
│   │   ├── Tab3Page.tsx
│   │   └── Tab4Page.tsx
│   ├── api/
│   │   └── client.ts              # API client functions
│   ├── types/
│   │   └── index.ts               # TypeScript interfaces
│   ├── App.tsx
│   └── main.tsx
├── package.json
├── tsconfig.json
├── tailwind.config.js
└── vite.config.ts
```

### 8.2 Component Specifications

#### Tab 2: TriggeredEvolution Component (THE KEY)

```tsx
// frontend/src/components/tab2/TriggeredEvolution.tsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface TriggeredEvolutionProps {
  evolution: {
    evolution_id: string;
    event_type: string;
    description: string;
    before_state: Record<string, any>;
    after_state: Record<string, any>;
  } | null;
}

export function TriggeredEvolution({ evolution }: TriggeredEvolutionProps) {
  if (!evolution) return null;
  
  return (
    <Card className="border-purple-500 bg-purple-50">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-purple-700">
          <span className="text-lg">🔗</span>
          TRIGGERED EVOLUTION
          <span className="text-sm font-normal text-purple-500">
            (What SIEMs don't have)
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-gray-700 mb-3">
          This decision trace triggered:
        </p>
        <ul className="space-y-1 text-sm">
          <li>
            • {evolution.description}
          </li>
          <li>
            • Evolution event: <code className="bg-purple-100 px-1">
              {evolution.evolution_id}
            </code> created
          </li>
        </ul>
        <p className="mt-4 text-sm font-medium text-purple-800 italic">
          "Splunk gets better rules. Our copilot gets SMARTER."
        </p>
      </CardContent>
    </Card>
  );
}
```

#### Tab 2: EvalGatePanel Component

```tsx
// frontend/src/components/tab2/EvalGatePanel.tsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CheckCircle, XCircle } from "lucide-react";

interface EvalCheck {
  name: string;
  score: number;
  threshold: number;
  passed: boolean;
}

interface EvalGatePanelProps {
  alertId: string;
  checks: EvalCheck[];
  overallPassed: boolean;
}

export function EvalGatePanel({ alertId, checks, overallPassed }: EvalGatePanelProps) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">
          EVAL GATE — {alertId}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500">
              <th className="pb-2">CHECK</th>
              <th className="pb-2 text-right">SCORE</th>
              <th className="pb-2 text-right">THRESH</th>
              <th className="pb-2 text-right">STATUS</th>
            </tr>
          </thead>
          <tbody>
            {checks.map((check) => (
              <tr key={check.name} className="border-t">
                <td className="py-2">{check.name}</td>
                <td className="py-2 text-right">{check.score.toFixed(2)}</td>
                <td className="py-2 text-right text-gray-500">
                  &gt; {check.threshold.toFixed(2)}
                </td>
                <td className="py-2 text-right">
                  {check.passed ? (
                    <span className="text-green-600 flex items-center justify-end gap-1">
                      <CheckCircle size={14} /> PASS
                    </span>
                  ) : (
                    <span className="text-red-600 flex items-center justify-end gap-1">
                      <XCircle size={14} /> FAIL
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        
        <div className={`mt-4 p-2 rounded text-center font-medium ${
          overallPassed 
            ? "bg-green-100 text-green-800" 
            : "bg-red-100 text-red-800"
        }`}>
          VERDICT: {overallPassed ? "✓ ALL GATES PASSED" : "✗ BLOCKED"}
          <br />
          <span className="text-sm font-normal">
            {overallPassed ? "Action authorized" : "Action not authorized"}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
```

#### Tab 4: TwoLoopDiagram Component

```tsx
// frontend/src/components/tab4/TwoLoopDiagram.tsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function TwoLoopDiagram() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Two-Loop Architecture (Our Differentiator)</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="font-mono text-xs whitespace-pre bg-gray-50 p-4 rounded">
{`
┌─────────────────────────────────────────────────────────────┐
│                    SECURITY ALERT                           │
│                         │                                   │
│                         ▼                                   │
│              ┌─────────────────────┐                       │
│              │    SEMANTIC GRAPH   │                       │
│              │      (Neo4j)        │                       │
│              └──────────┬──────────┘                       │
│                         │                                   │
│           ┌─────────────┴─────────────┐                    │
│           ▼                           ▼                    │
│   ┌───────────────┐          ┌───────────────┐            │
│   │   LOOP 1      │          │   LOOP 2      │            │
│   │  Alert Triage │          │   Runtime     │            │
│   │               │          │   Evolution ★ │            │
│   │ • Better      │          │               │            │
│   │   search      │          │ • Better      │            │
│   │ • SIEMs have  │          │   agent       │            │
│   │   this ✓      │          │ • SIEMs LACK  │            │
│   │               │          │   this ✗      │            │
│   └───────┬───────┘          └───────┬───────┘            │
│           │                          │                     │
│           │    TRIGGERED_EVOLUTION   │                     │
│           │    ◄─────────────────────┘                     │
│           │                                                │
│           └─────────────► COMPOUNDING                      │
│                                                            │
└─────────────────────────────────────────────────────────────┘
`}
        </div>
        <p className="mt-4 text-center text-sm text-gray-600">
          <strong>SIEMs:</strong> One loop — alerts improve detection rules.
          <br />
          <strong>SOC Copilot:</strong> Two loops — alerts improve detection
          <em> AND </em> the copilot itself.
        </p>
      </CardContent>
    </Card>
  );
}
```

---

## 9. Implementation Sequence

### 9.1 Week 1: Core Demo

| Day | Task | Deliverable | Verification |
|-----|------|-------------|--------------|
| 1 | Project setup | Repo, deps, folder structure | `npm run dev` works |
| 1 | Backend scaffold | FastAPI app with health check | `/api/health` returns 200 |
| 2 | BigQuery setup | Tables created, seed data | Query returns 10 metrics |
| 2 | Firestore setup | Collections created, seed data | Read 5 alerts |
| 3 | Neo4j setup | Graph seeded via notebook | 46 nodes, 49 relationships |
| 3 | Neo4j verify | TRIGGERED_EVOLUTION exists | Count = 3 |
| 4 | Agent implementation | agent.py, reasoning.py | Unit tests pass |
| 4 | Eval gate | eval_gate.py | Blocking demo works |
| 5 | Tab 2 backend | All Tab 2 endpoints | API tests pass |
| 5 | Tab 2 frontend | All Tab 2 components | Visual review |

### 9.2 Week 2: Polish + Demo Prep

| Day | Task | Deliverable | Verification |
|-----|------|-------------|--------------|
| 6 | Tab 1 backend | SOC query endpoint | Returns governed metrics |
| 6 | Tab 1 frontend | Query + governance UI | Visual review |
| 7 | Tab 3 backend | Alert triage endpoints | Graph traversal works |
| 7 | Tab 3 frontend | Graph viz + closed loop | 47 nodes displayed |
| 8 | Tab 4 backend | Compounding metrics | Week 1 vs Week 4 data |
| 8 | Tab 4 frontend | Two-loop diagram | Visual review |
| 9 | Integration | All tabs working together | Full demo flow |
| 9 | Bug fixes | Known issues resolved | Demo checklist |
| 10 | Demo prep | Practice runs, timing | 15-min flow verified |

### 9.3 Critical Milestones

| Milestone | Day | Must Pass |
|-----------|-----|-----------|
| Tab 2 blocking demo works | 4 | Eval gate blocks bad candidate |
| TRIGGERED_EVOLUTION visible | 5 | Purple panel shows evolution |
| Closed-loop works | 7 | Execute → Verify → Evidence → KPI |
| Two-loop visual renders | 8 | Diagram clearly shows two loops |
| Full 15-min demo | 10 | End-to-end without errors |

---

## 10. Verification Procedures

### 10.1 Infrastructure Verification

```bash
# Run after completing infrastructure setup

# 1. BigQuery
bq query --use_legacy_sql=false \
  "SELECT COUNT(*) as count FROM soc.metric_contracts"
# Expected: 10

# 2. Firestore
# Use Firebase console or:
firebase firestore:indexes
# Expected: alerts, assets, users, playbooks, patterns, deployments collections

# 3. Neo4j
# Run in Neo4j Browser:
MATCH (n) RETURN labels(n)[0] as type, count(n) as count ORDER BY type
# Expected: ~46 total nodes

MATCH ()-[r:TRIGGERED_EVOLUTION]->()
RETURN count(r) as triggered_evolution_count
# Expected: 3
```

### 10.2 API Verification

```bash
# Health check
curl http://localhost:8000/api/health
# Expected: {"status": "healthy", "bigquery": true, "firestore": true, "neo4j": true}

# Tab 1: SOC Query
curl -X POST http://localhost:8000/api/soc/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is MTTR by severity?"}'
# Expected: matched_metric.id = "mttr_by_severity"

# Tab 2: Process Alert
curl -X POST http://localhost:8000/api/alert/process \
  -H "Content-Type: application/json" \
  -d '{"alert_id": "ALERT-7823"}'
# Expected: eval_gate.overall_passed = true, triggered_evolution != null

# Tab 2: Simulate Failed Gate
curl -X POST http://localhost:8000/api/eval/simulate-failure \
  -H "Content-Type: application/json" \
  -d '{"alert_id": "ALERT-7821", "fail_check": "safe_action"}'
# Expected: execution.status = "blocked"
```

### 10.3 Demo Flow Verification

```
□ Tab 1: Type "What is MTTR by severity?" → Chart appears
□ Tab 1: Governance panel shows provenance
□ Tab 1: Sprawl alert shows $18K cost
□ Tab 2: Deployment registry shows v3.1 (active) and v3.2 (canary)
□ Tab 2: Click "Process Next Alert" → Eval gate shows 4 checks PASS
□ Tab 2: TRIGGERED_EVOLUTION panel appears (purple)
□ Tab 2: Click "Simulate Failed Gate" → Shows BLOCKED verdict
□ Tab 3: Click ALERT-7823 → Graph shows 47 nodes consulted
□ Tab 3: Recommendation appears with confidence
□ Tab 3: Execute → 4-step closed loop completes
□ Tab 4: Week 1 vs Week 4 shows 68% → 89% auto-close
□ Tab 4: Two-loop diagram renders correctly
□ Tab 4: Evolution events list shows EVO-0891, EVO-0890, EVO-0889
```

---

## 11. Seed Data Reference

### 11.1 Sample Alerts

| ID | Type | Severity | Asset | User | Location |
|----|------|----------|-------|------|----------|
| ALERT-7823 | anomalous_login | medium | LAPTOP-JSMITH | John Smith | Singapore |
| ALERT-7822 | phishing | high | MAIL-GW-01 | Finance Team | External |
| ALERT-7821 | malware_detection | critical | SRV-DB-PROD-01 | system | Internal |
| ALERT-7820 | data_exfiltration | high | LAPTOP-MCHEN | Mary Chen | Internal |
| ALERT-7819 | anomalous_login | low | LAPTOP-AGARCIA | Ana Garcia | Denver |

### 11.2 Attack Patterns

| ID | Name | FP Rate | Occurrences | Confidence |
|----|------|---------|-------------|------------|
| PAT-TRAVEL-001 | Travel Login FP | 94% | 127 | 92% |
| PAT-PHISH-KNOWN | Known Phishing | 2% | 89 | 96% |
| PAT-MALWARE-ISOLATE | Malware Isolation | 8% | 34 | 91% |
| PAT-VPN-KNOWN | Known VPN Provider | 96% | 245 | 94% |
| PAT-LOGIN-NORMAL | Normal Location Login | 98% | 2,847 | 97% |

### 11.3 Users

| ID | Name | Title | Risk Score | Privileged |
|----|------|-------|------------|------------|
| jsmith@company.com | John Smith | VP Finance | 0.85 | Yes |
| mchen@company.com | Mary Chen | Director Engineering | 0.72 | Yes |
| agarcia@company.com | Ana Garcia | Senior Developer | 0.35 | No |
| cjohnson@company.com | Chris Johnson | CEO | 0.95 | Yes |
| blee@company.com | Bob Lee | SOC Analyst | 0.25 | No |

### 11.4 Key Metrics (Week 1 → Week 4)

| Metric | Week 1 | Week 4 | Change |
|--------|--------|--------|--------|
| Auto-Close Rate | 68% | 89% | +21 pts |
| MTTR | 12.4 min | 3.1 min | -75% |
| Patterns | 23 | 127 | +452% |
| FP Investigations | 4,200/wk | 980/wk | -77% |

---

## 12. Code Templates

### 12.1 FastAPI Router Template

```python
# backend/app/routers/evolution.py
"""Tab 2: Runtime Evolution API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/api", tags=["evolution"])

class ProcessAlertRequest(BaseModel):
    alert_id: str
    deployment_version: Optional[str] = None

class EvalCheck(BaseModel):
    name: str
    score: float
    threshold: float
    passed: bool

class ProcessAlertResponse(BaseModel):
    alert_id: str
    routed_to: str
    eval_gate: dict
    decision: dict
    execution: dict
    triggered_evolution: Optional[dict]

@router.post("/alert/process", response_model=ProcessAlertResponse)
async def process_alert(request: ProcessAlertRequest):
    """Process an alert through the SOC Copilot agent."""
    # Implementation here
    pass

@router.get("/deployments")
async def get_deployments():
    """Get all agent deployments."""
    # Implementation here
    pass
```

### 12.2 React Page Template

```tsx
// frontend/src/pages/Tab2Page.tsx
import { useState, useEffect } from "react";
import { DeploymentRegistry } from "@/components/tab2/DeploymentRegistry";
import { CanaryComparison } from "@/components/tab2/CanaryComparison";
import { EvalGatePanel } from "@/components/tab2/EvalGatePanel";
import { DecisionTrace } from "@/components/tab2/DecisionTrace";
import { TriggeredEvolution } from "@/components/tab2/TriggeredEvolution";
import { Button } from "@/components/ui/button";
import { processAlert, getDeployments } from "@/api/client";

export function Tab2Page() {
  const [deployments, setDeployments] = useState([]);
  const [lastResult, setLastResult] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getDeployments().then(setDeployments);
  }, []);

  const handleProcessAlert = async () => {
    setLoading(true);
    try {
      const result = await processAlert({ alert_id: "ALERT-7823" });
      setLastResult(result);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 p-6">
      <h1 className="text-2xl font-bold">
        SOC Copilot Evolution — "The Agent That Gets Smarter"
      </h1>
      
      <DeploymentRegistry deployments={deployments} />
      
      <div className="grid grid-cols-2 gap-6">
        <CanaryComparison deployments={deployments} />
        {lastResult && (
          <EvalGatePanel 
            alertId={lastResult.alert_id}
            checks={lastResult.eval_gate.checks}
            overallPassed={lastResult.eval_gate.overall_passed}
          />
        )}
      </div>
      
      <div className="flex gap-4">
        <Button onClick={handleProcessAlert} disabled={loading}>
          {loading ? "Processing..." : "Process Next Alert"}
        </Button>
        <Button variant="outline">
          Simulate Failed Gate
        </Button>
      </div>
      
      {lastResult && (
        <>
          <DecisionTrace decision={lastResult.decision} />
          <TriggeredEvolution evolution={lastResult.triggered_evolution} />
        </>
      )}
    </div>
  );
}
```

### 12.3 API Client Template

```typescript
// frontend/src/api/client.ts
const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

export async function getDeployments() {
  const res = await fetch(`${API_BASE}/deployments`);
  if (!res.ok) throw new Error("Failed to fetch deployments");
  return res.json();
}

export async function processAlert(request: { alert_id: string; deployment_version?: string }) {
  const res = await fetch(`${API_BASE}/alert/process`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!res.ok) throw new Error("Failed to process alert");
  return res.json();
}

export async function simulateFailedGate(request: { alert_id: string; fail_check: string }) {
  const res = await fetch(`${API_BASE}/eval/simulate-failure`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!res.ok) throw new Error("Failed to simulate");
  return res.json();
}

export async function querySOC(question: string) {
  const res = await fetch(`${API_BASE}/soc/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) throw new Error("Failed to query");
  return res.json();
}
```

---

## Appendix A: Environment Variables

```bash
# .env file for local development

# GCP
PROJECT_ID=soc-copilot-demo
REGION=us-central1

# BigQuery
BIGQUERY_DATASET=soc

# Neo4j Aura
NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password-here

# Vertex AI
VERTEX_AI_LOCATION=us-central1

# Frontend
VITE_API_URL=http://localhost:8000/api
```

---

## Appendix B: Soundbites (Memorize)

| Context | Soundbite |
|---------|-----------|
| Tab 1 | "This is sellable today. 90-day ROI." |
| Tab 2 | "Your SIEM gets better rules. Our copilot gets **smarter**." |
| Tab 3 | "A SIEM stops at detect. We **close the loop**." |
| Tab 4 | "They start at zero patterns. We start at **127**." |
| Overall | "Your SIEM **remembers**. Our copilot **learns**." |

---

## Appendix C: SIEM Contrast Table

| Aspect | Traditional SIEM | SOC Copilot |
|--------|-----------------|-------------|
| Alert Processing | Detect → Log → Queue | Detect → Analyze → **Decide** → Execute |
| Learning | Manual rule tuning | **Automatic pattern learning** |
| Agent Evolution | None | **TRIGGERED_EVOLUTION** |
| Closed Loop | None | Execute → Verify → Evidence → KPI |
| Intelligence | Static rules | **Compounding intelligence** |
| Loops | One (detection) | **Two (detection + self-improvement)** |

---

*Technical Briefing for SOC Copilot Demo v1 | January 2026*
*Optimized for: Claude Code, OpenAI Codex, Technical Implementation*
*Build time: 2 weeks | Agent: ~200 lines | Tabs: 4 | Key: TRIGGERED_EVOLUTION*
