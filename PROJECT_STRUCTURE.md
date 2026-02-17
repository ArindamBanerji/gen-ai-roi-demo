# SOC Copilot Demo - Project Structure

**Last Updated:** February 9, 2026
**Total Files:** 21 code files (~2,500 lines)
**Architecture:** Two-loop compounding intelligence with runtime evolution

---

## Table of Contents

- [Directory Tree](#directory-tree)
- [Backend Files](#backend-files)
  - [Main Application](#main-application)
  - [Routers](#routers)
  - [Services](#services)
  - [Database Clients](#database-clients)
  - [Models](#models)
  - [Utilities](#utilities)
- [Frontend Files](#frontend-files)
  - [Core Application](#core-application)
  - [Tab Components](#tab-components)
  - [API Client](#api-client)
- [Dependency Diagram](#dependency-diagram)
- [Import Flow](#import-flow)
- [Tab Support Matrix](#tab-support-matrix)

---

## Directory Tree

```
gen-ai-roi-demo/
│
├── backend/
│   ├── requirements.txt              # Python dependencies
│   ├── seed_neo4j.py                 # Neo4j seed data script
│   └── app/
│       ├── main.py                   # FastAPI application entry point
│       ├── routers/
│       │   ├── __init__.py
│       │   ├── soc.py                # Tab 1: SOC Analytics
│       │   ├── evolution.py          # Tab 2: Runtime Evolution
│       │   ├── triage.py             # Tab 3: Alert Triage
│       │   └── metrics.py            # Tab 4: Compounding Metrics
│       ├── services/
│       │   ├── __init__.py
│       │   ├── agent.py              # Simple rule-based decision engine
│       │   ├── reasoning.py          # LLM narration service
│       │   └── seed_neo4j.py         # Neo4j seed data (service module)
│       ├── db/
│       │   ├── __init__.py
│       │   └── neo4j.py              # Neo4j Aura client
│       └── models/
│           ├── __init__.py
│           └── schemas.py            # Pydantic models
│
└── frontend/
    ├── package.json
    └── src/
        ├── main.tsx                  # React entry point
        ├── App.tsx                   # 4-tab navigation root
        ├── lib/
        │   └── api.ts                # Backend API client
        └── components/
            └── tabs/
                ├── SOCAnalyticsTab.tsx       # Tab 1
                ├── RuntimeEvolutionTab.tsx   # Tab 2
                ├── AlertTriageTab.tsx        # Tab 3
                └── CompoundingTab.tsx        # Tab 4
```

---

## Backend Files

### Main Application

#### `backend/app/main.py`

**Purpose:** FastAPI application entry point with CORS configuration and router registration.

**Key Functions/Exports:**
- `app` - FastAPI application instance
- `root()` - Health check endpoint (GET /)
- `health()` - Health check endpoint (GET /health)
- `startup_event()` - Initialize Neo4j connection on startup
- `shutdown_event()` - Close Neo4j connection on shutdown

**Dependencies:**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.routers import evolution, triage, soc, metrics
from app.db.neo4j import neo4j_client
```

**Tab Support:** All tabs (provides API infrastructure)

**Lines:** ~62

---

### Routers

#### `backend/app/routers/soc.py`

**Purpose:** Tab 1 (SOC Analytics) API endpoints for governed security metrics with natural language queries.

**Key Functions/Exports:**
- `router` - FastAPI APIRouter instance
- `query_soc_metrics(request: SOCQueryRequest)` - POST /api/soc/query
  - Natural language metric query endpoint
  - Returns: matched metric, chart data, provenance, sprawl alert
- `list_metrics()` - GET /api/soc/metrics
  - Lists all available metrics for discovery
- `match_metric(question: str)` - Internal keyword matching logic
- `get_metric_data(metric_id: str)` - Mock data generators
- `get_provenance(metric_id: str)` - Data provenance information
- `check_for_sprawl(metric_id: str)` - Detection rule sprawl checker

**Key Data Structures:**
- `METRIC_REGISTRY` - 6 metrics (MTTR, auto-close, FP rate, escalation, MTTD, analyst efficiency)
- Mock data generators for each metric

**Dependencies:**
```python
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import re
```

**Tab Support:** Tab 1 (SOC Analytics)

**Lines:** ~403

**Notable Features:**
- Keyword-based metric matching (e.g., "auto close", "auto-close", "autoclose")
- Rule sprawl detection for fp_rate_by_rule query
- Mock BigQuery data (no GCP setup required)

---

#### `backend/app/routers/evolution.py`

**Purpose:** Tab 2 (Runtime Evolution) API endpoints showing TRIGGERED_EVOLUTION - the key differentiator.

**Key Functions/Exports:**
- `router` - FastAPI APIRouter instance
- `get_deployments()` - GET /api/deployments
  - Returns: v3.1 (active, 90%) and v3.2 (canary, 10%)
- `process_alert(request: ProcessAlertRequest)` - POST /api/alert/process
  - **THE KEY FLOW:** 7 steps
    1. Get security context (47 nodes from Neo4j)
    2. Agent decision (rule-based)
    3. LLM reasoning (narration)
    4. Eval gate (4 checks)
    5. Create decision trace in Neo4j
    6. Check if evolution triggers
    7. Create TRIGGERED_EVOLUTION relationship
  - Returns: decision, eval_gate, triggered_evolution, execution_stats

**Dependencies:**
```python
from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from app.db.neo4j import neo4j_client
from app.services.agent import SecurityAgent
from app.services.reasoning import ReasoningNarrator
from app.models.schemas import ProcessAlertRequest
```

**Tab Support:** Tab 2 (Runtime Evolution) ★ THE DIFFERENTIATOR

**Lines:** ~250

**Notable Features:**
- Integration point between agent, Neo4j, and LLM
- TRIGGERED_EVOLUTION relationship creation
- Eval gate with 4 deterministic checks
- Decision trace persistence

---

#### `backend/app/routers/triage.py`

**Purpose:** Tab 3 (Alert Triage) API endpoints for graph-based alert analysis and closed-loop execution.

**Key Functions/Exports:**
- `router` - FastAPI APIRouter instance
- `get_alert_queue()` - GET /api/triage/alerts
  - Returns: 5 pending alerts from seed data
- `analyze_alert(alert_id: str)` - POST /api/triage/analyze
  - Graph traversal + recommendation
  - Returns: decision, reasoning, confidence, graph_data (nodes/edges)
- `execute_action(request: ActionRequest)` - POST /api/triage/execute
  - 4-step closed loop:
    1. EXECUTED - Send action to target system
    2. VERIFIED - Confirm system response
    3. EVIDENCE - Capture artifact
    4. KPI IMPACT - Calculate MTTR improvement
  - Returns: receipt, verification, evidence, kpi_impact
- `get_graph_data(alert_id: str)` - Extract nodes/edges for visualization

**Dependencies:**
```python
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
from app.db.neo4j import neo4j_client
from app.services.agent import SecurityAgent
from app.services.reasoning import ReasoningNarrator
```

**Tab Support:** Tab 3 (Alert Triage)

**Lines:** ~400

**Notable Features:**
- Simple graph visualization (colored boxes, not complex library)
- 4-step closed-loop execution with verification
- KPI impact calculation (MTTR improvement)

---

#### `backend/app/routers/metrics.py`

**Purpose:** Tab 4 (Compounding Dashboard) API endpoints showing week-over-week intelligence growth.

**Key Functions/Exports:**
- `router` - FastAPI APIRouter instance
- `get_compounding_metrics(weeks: int = 4)` - GET /api/metrics/compounding
  - Returns: headline (Week 1 vs Week 4), weekly_trend, evolution_events
  - Week 1: 23 patterns, 68% auto-close
  - Week 4: 127 patterns, 89% auto-close
- `get_evolution_events(limit: int = 10)` - GET /api/metrics/evolution-events
  - Returns: Recent evolution events list
- `reset_demo_data()` - POST /api/demo/reset
  - Resets demo to Week 1 state
- `generate_compounding_data(weeks: int)` - Mock data generator

**Dependencies:**
```python
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel
```

**Tab Support:** Tab 4 (Compounding Dashboard)

**Lines:** ~270

**Notable Features:**
- Mock data showing gradual improvement (4 weeks)
- Evolution events timeline (EVO-0891, 0890, 0889, 0888)
- Demo reset functionality for repeated presentations

---

### Services

#### `backend/app/services/agent.py`

**Purpose:** Simple rule-based decision engine with 3-tier travel matching. Intentionally deterministic for demo reliability.

**Key Functions/Exports:**
- `SecurityAgent` class
  - `decide(alert_type: str, context: SecurityContext) -> Decision`
    - 4 primary rules for alert types
    - 3-tier travel matching (strong/good/moderate)
    - Returns: action, confidence, pattern_id
  - `evaluate_gates(decision, context, reasoning) -> EvalGateResult`
    - 4 checks: Faithfulness, Safe Action, Playbook Match, SLA
    - Context-aware faithfulness scoring (3 tiers)
    - Returns: 4 gate scores with pass/fail
  - `maybe_trigger_evolution(decision, context) -> EvolutionTrigger | None`
    - Checks if pattern_id exists and occurrence threshold met
    - Returns: event details if evolution triggered
  - `_calculate_faithfulness(decision, context, reasoning) -> float`
    - Tier 1: Action keywords (0.88)
    - Tier 2: Pattern-specific (0.94)
    - Tier 3: Context-aware indicator counting (0.92-0.96)

**Alert Types Handled:**
1. **anomalous_login** - 3-tier travel matching
2. **phishing** - Known campaign signature check
3. **malware_detection** - Asset criticality check
4. **data_exfiltration** - Always escalate to incident

**Dependencies:**
```python
from typing import Dict, Any, Optional
from datetime import datetime
from app.models.schemas import Decision, SecurityContext, EvalGateResult, EvolutionTrigger
```

**Tab Support:** Tab 2 (decision engine), Tab 3 (recommendations)

**Lines:** ~250

**Notable Features:**
- Deterministic decisions (same input → same output)
- 3-tier travel matching (FIXED for better coverage)
- Context-aware faithfulness scoring (FIXED for eval gate)
- Pattern-based evolution triggering

---

#### `backend/app/services/reasoning.py`

**Purpose:** LLM narration service using Gemini 1.5 Pro. Makes rule-based decisions sound like expert security analysis.

**Key Functions/Exports:**
- `ReasoningNarrator` class
  - `generate_reasoning(alert_type, decision, context) -> str`
    - Generates 2-3 sentence justification AFTER decision made
    - Uses Gemini 1.5 Pro via Vertex AI
    - Falls back to template if LLM unavailable
  - `_build_prompt(alert_type, decision, context) -> str`
    - Constructs prompt with alert details, context, pattern info
  - `_fallback_reasoning(alert_type, decision) -> str`
    - Template-based reasoning if LLM fails

**Dependencies:**
```python
import os
from typing import Dict, Any
from google.cloud import aiplatform
from vertexai.generative_models import GenerativeModel
from app.models.schemas import Decision, SecurityContext
```

**Tab Support:** Tab 2 (narration), Tab 3 (recommendation text)

**Lines:** ~50

**Notable Features:**
- LLM role: Narration ONLY, not decision-making
- Fallback templates ensure demo reliability
- "Intelligence theater" - makes rules sound smart

---

#### `backend/app/services/seed_neo4j.py`

**Purpose:** Neo4j seed data constants as a service module. Contains canonical test data that can be imported by other services.

**Key Functions/Exports:**
- `ASSETS` - List of 5 asset definitions (LAPTOP-JSMITH, SRV-DB-PROD-01, etc.)
- `USERS` - List of 5 user definitions (John Smith, Mary Chen, etc.)
- `ALERT_TYPES` - List of 4 alert type definitions (anomalous_login, phishing, etc.)
- `PATTERNS` - List of 5 attack pattern definitions (PAT-TRAVEL-001, etc.)
- `PLAYBOOKS` - List of 4 playbook definitions (PB-LOGIN-001, etc.)

**Difference from `backend/seed_neo4j.py`:**
- **This file:** Service module with data constants (can be imported)
- **Root file:** Standalone async script (run from command line)

**Dependencies:**
```python
from typing import Dict, Any, List
from app.db.neo4j import neo4j_client
```

**Tab Support:** Tab 2, Tab 3 (provides canonical seed data)

**Lines:** ~500+

**Usage:**
```python
from app.services.seed_neo4j import ASSETS, USERS, PATTERNS
```

---

### Database Clients

#### `backend/app/db/neo4j.py`

**Purpose:** Neo4j Aura client for security graph operations, decision traces, and evolution events.

**Key Functions/Exports:**
- `Neo4jClient` class
  - `connect()` - Establish Neo4j connection
  - `close()` - Close connection
  - `get_security_context(alert_id: str) -> SecurityContext`
    - Traverses graph to get 47 nodes
    - Returns: user, asset, travel, patterns, playbook, SLA info
    - **Key query:** Fixed Cypher returning predictable node count
  - `create_decision_trace(decision_id, alert_id, decision, context, reasoning)`
    - Creates (:Decision), (:DecisionContext) nodes
    - Links via relationships
  - `create_evolution_event(event_id, triggered_by, event_type, description)`
    - Creates (:EvolutionEvent) node
    - **KEY:** Creates (:Decision)-[:TRIGGERED_EVOLUTION]->(:EvolutionEvent)
  - `get_alert_details(alert_id: str) -> Dict`
    - Fetch alert with asset, user, type info
  - `get_precedent_decisions(alert_type: str, limit: int) -> List[Dict]`
    - Find similar past decisions

**Dependencies:**
```python
import os
from typing import Dict, Any, List, Optional
from neo4j import AsyncGraphDatabase, AsyncDriver
from datetime import datetime
from app.models.schemas import SecurityContext
```

**Tab Support:** Tab 2 (context + evolution), Tab 3 (graph traversal)

**Lines:** ~300

**Notable Features:**
- Fixed Cypher queries (no dynamic generation)
- TRIGGERED_EVOLUTION relationship (OUR DIFFERENTIATOR)
- Connection pooling
- 47 nodes traversal for context

---

### Models

#### `backend/app/models/schemas.py`

**Purpose:** Pydantic v2 models for request/response validation across all endpoints.

**Key Classes/Exports:**

**Tab 1 Models:**
- `SOCQueryRequest` - Natural language query input
- `MetricContract` - Metric definition with owner, version
- `MetricDataPoint` - Chart data point (label, value)
- `Provenance` - Data sources, freshness, query preview
- `SprawlAlert` - Rule sprawl warning

**Tab 2 Models:**
- `ProcessAlertRequest` - Alert processing request (FIXED from query params)
- `Deployment` - Deployment version (active/canary)
- `EvalGateCheck` - Single eval gate result
- `EvalGateResult` - All 4 gate checks
- `TriggeredEvolution` - Evolution event details
- `ExecutionStats` - Processing time, routing info

**Tab 3 Models:**
- `AlertSummary` - Alert queue item
- `ActionRequest` - Action execution request
- `Receipt` - Action confirmation
- `Verification` - System verification
- `Evidence` - Captured artifact
- `KpiImpact` - MTTR improvement calculation

**Tab 4 Models:**
- `WeeklyMetrics` - Week snapshot (auto-close, MTTR, FP rate, pattern count)
- `EvolutionEvent` - Evolution event summary
- `CompoundingResponse` - Full compounding metrics response

**Core Models:**
- `SecurityContext` - 47 nodes context snapshot
- `Decision` - Agent decision with action, confidence, pattern_id
- `EvolutionTrigger` - Evolution event trigger info

**Dependencies:**
```python
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
```

**Tab Support:** All tabs (data validation layer)

**Lines:** ~400

---

### Utilities

#### `backend/seed_neo4j.py`

**Purpose:** Seed Neo4j database with demo data (5 alerts, 3 users, 3 assets, patterns, playbooks).

**Key Functions/Exports:**
- `seed_neo4j()` - Main seeding function
  - Creates users (John Smith, Sarah Chen, Mike Johnson)
  - Creates assets (LAPTOP-JS-001, SERVER-DB-PROD, WORKSTATION-SC-002)
  - Creates alert types (anomalous_login, phishing, malware, data_exfiltration)
  - Creates attack patterns (PAT-TRAVEL-001 with 127 occurrences)
  - Creates playbooks (anomalous_login_playbook, etc.)
  - Creates 5 alerts (ALERT-7823 through ALERT-7819)
  - Creates travel context for John Smith to Singapore

**Dependencies:**
```python
from neo4j import GraphDatabase
import os
from datetime import datetime, timedelta
```

**Tab Support:** Tab 2, Tab 3 (provides graph data)

**Lines:** ~200

**Usage:**
```bash
python backend/seed_neo4j.py
```

---

## Frontend Files

### Core Application

#### `frontend/src/main.tsx`

**Purpose:** React 18 application entry point with StrictMode.

**Key Functions/Exports:**
- Mounts React app to DOM
- Wraps `<App />` in `<React.StrictMode>`

**Dependencies:**
```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'
```

**Tab Support:** All tabs (entry point)

**Lines:** ~10

---

#### `frontend/src/App.tsx`

**Purpose:** Root component with 4-tab navigation. Starts on Tab 2 (THE DIFFERENTIATOR).

**Key Functions/Exports:**
- `App` component
  - Tab state management
  - Tab navigation UI
  - Renders active tab component

**Tab Order:**
1. SOC Analytics (Tab 1)
2. Runtime Evolution (Tab 2) ★ DEFAULT
3. Alert Triage (Tab 3)
4. Compounding (Tab 4)

**Dependencies:**
```typescript
import { useState } from 'react'
import SOCAnalyticsTab from './components/tabs/SOCAnalyticsTab'
import RuntimeEvolutionTab from './components/tabs/RuntimeEvolutionTab'
import AlertTriageTab from './components/tabs/AlertTriageTab'
import CompoundingTab from './components/tabs/CompoundingTab'
```

**Tab Support:** All tabs (navigation shell)

**Lines:** ~80

---

### Tab Components

#### `frontend/src/components/tabs/SOCAnalyticsTab.tsx`

**Purpose:** Tab 1 - Natural language security metric queries with governance and provenance.

**Key Components/Exports:**
- `SOCAnalyticsTab` - Main tab component
  - Natural language query input
  - 5 example question chips
  - Metric result with chart (Recharts)
  - Metric contract panel (owner, version, definition)
  - Provenance panel (sources, freshness, query preview)
  - Rule sprawl alert (orange/red banner)

**Key Features:**
- Keyword matching for 6 metrics
- Bar charts (MTTR, FP rate, MTTD, analyst efficiency)
- Line charts (auto-close rate, escalation rate)
- Freshness indicator (green < 2hrs, yellow 2-6hrs, red > 6hrs)
- Value formatting (%, min, hours)

**Dependencies:**
```typescript
import { useState } from 'react'
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { queryMetric } from '../../lib/api'
import { Search, AlertTriangle, Database, Clock, FileText } from 'lucide-react'
```

**API Calls:**
- POST /api/soc/query

**Tab Support:** Tab 1 (SOC Analytics)

**Lines:** ~476

---

#### `frontend/src/components/tabs/RuntimeEvolutionTab.tsx`

**Purpose:** Tab 2 - Runtime evolution showing TRIGGERED_EVOLUTION. THE KEY DIFFERENTIATOR.

**Key Components/Exports:**
- `RuntimeEvolutionTab` - Main tab component
  - Deployment registry table (v3.1 active 90%, v3.2 canary 10%)
  - Process Alert button (ALERT-7823)
  - Eval Gate panel (4 checks with scores)
    - Faithfulness (>0.85)
    - Safe Action (>0.80)
    - Playbook Match (>0.90)
    - SLA Compliant (>0.95)
  - Decision Trace panel (decision details, reasoning)
  - **TRIGGERED_EVOLUTION panel (purple, THE KEY FEATURE)**
    - Event ID (EVO-XXXX)
    - Event type (pattern_confidence_increase)
    - Description (PAT-TRAVEL: 91% → 94%)
    - Impact level
  - Execution Stats (processing time, routing, event ID)

**Key Features:**
- Real-time processing simulation
- Color-coded gate checks (green pass, red fail)
- Purple TRIGGERED_EVOLUTION highlight
- Processing time display

**Dependencies:**
```typescript
import { useState, useEffect } from 'react'
import { getDeployments, processAlert } from '../../lib/api'
import { Activity, CheckCircle, XCircle, AlertTriangle, Zap, Clock } from 'lucide-react'
```

**API Calls:**
- GET /api/deployments
- POST /api/alert/process

**Tab Support:** Tab 2 (Runtime Evolution) ★ THE DIFFERENTIATOR

**Lines:** ~470

**Soundbite:** "Splunk gets better rules. Our copilot gets **smarter**."

---

#### `frontend/src/components/tabs/AlertTriageTab.tsx`

**Purpose:** Tab 3 - Graph-based alert triage with closed-loop execution.

**Key Components/Exports:**
- `AlertTriageTab` - Main tab component
  - Alert Queue sidebar (5 alerts, severity badges)
  - Simple graph visualization (colored boxes)
    - Blue: Asset nodes
    - Green: User nodes
    - Purple: Alert Type nodes
    - Yellow: Pattern nodes
    - Orange: Playbook nodes
  - Recommendation panel (action, confidence %, reasoning)
  - Closed Loop Execution panel (4 steps)
    - Step 1: EXECUTED (action sent, 800ms animation)
    - Step 2: VERIFIED (system confirmed, 800ms)
    - Step 3: EVIDENCE (artifact captured, 800ms)
    - Step 4: KPI IMPACT (MTTR -8.2 min, 800ms)

**Key Features:**
- Sequential animation (800ms per step)
- "47 nodes consulted" counter
- Color-coded graph nodes
- Real-time execution feedback

**Dependencies:**
```typescript
import { useState, useEffect } from 'react'
import { getAlerts, getAlertContext, executeAction } from '../../lib/api'
import { Shield, AlertCircle, CheckCircle, Clock, Database, FileText } from 'lucide-react'
```

**API Calls:**
- GET /api/triage/alerts
- POST /api/triage/analyze
- POST /api/triage/execute

**Tab Support:** Tab 3 (Alert Triage)

**Lines:** ~518

**Soundbite:** "A SIEM stops at detect. We **close the loop**."

---

#### `frontend/src/components/tabs/CompoundingTab.tsx`

**Purpose:** Tab 4 - Compounding intelligence dashboard proving the moat.

**Key Components/Exports:**
- `CompoundingTab` - Main tab component
  - **The Headline** - Week 1 vs Week 4 visual comparison
    - Week 1: 23 nodes (9 blue dots, sparse)
    - Week 4: 127 nodes (25 purple dots, dense)
    - Three headline metrics with improvements
  - **Weekly Trend Chart** - Recharts LineChart
    - Purple line: Auto-Close % (68 → 89)
    - Blue line: MTTR (12.4 → 3.1 min)
    - Red line: FP Rate % (18.5 → 8.1)
  - **Two-Loop Visual** - Architecture comparison
    - Traditional SIEM (one loop): Alert → Detect → Log → Manual
    - Our SOC Copilot (two loops): Alert → Graph → Better Triage + Better Agent → COMPOUNDING
  - **Recent Evolution Events** - Timeline
    - EVO-0891: Pattern confidence increase (2h ago)
    - EVO-0890: Auto-close threshold tuned (1d ago)
    - EVO-0889: New pattern discovered (2d ago)
    - EVO-0888: Playbook tuned (3d ago)
  - **The Moat Message** - Purple-to-blue gradient banner
  - **Reset Demo Button** - Restart to Week 1

**Key Features:**
- Visual graph growth (dots)
- Week-by-week progression
- Evolution event timeline
- Percentage improvements

**Dependencies:**
```typescript
import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { getCompoundingMetrics, resetDemoData } from '../../lib/api'
import { TrendingUp, Database, Activity, RefreshCw } from 'lucide-react'
```

**API Calls:**
- GET /api/metrics/compounding?weeks=4
- POST /api/demo/reset

**Tab Support:** Tab 4 (Compounding Dashboard)

**Lines:** ~417

**Soundbite:** "When they deploy, they start at zero. We start at **127 patterns**."

---

### API Client

#### `frontend/src/lib/api.ts`

**Purpose:** Centralized API client for all backend communication.

**Key Functions/Exports:**

**Helper:**
- `fetchJSON<T>(url, options)` - Typed fetch wrapper

**Tab 1: SOC Analytics**
- `queryMetric(query: string)` - POST /api/soc/query

**Tab 2: Runtime Evolution**
- `getDeployments()` - GET /api/deployments
- `processAlert(alertId, simulateFailure)` - POST /api/alert/process (FIXED to use JSON body)
- `simulateFailedGate()` - POST /api/eval/simulate-failure

**Tab 3: Alert Triage**
- `getAlerts()` - GET /api/triage/alerts
- `getAlertContext(alertId)` - GET /api/triage/context/{alertId}
- `executeAction(alertId, action)` - POST /api/triage/execute

**Tab 4: Compounding Metrics**
- `getCompoundingMetrics(weeks)` - GET /api/metrics/compounding?weeks=4
- `getEvolutionEvents(limit)` - GET /api/metrics/evolution-events?limit=10
- `resetDemoData()` - POST /api/demo/reset

**Dependencies:**
```typescript
// None - pure TypeScript
```

**Tab Support:** All tabs (API abstraction layer)

**Lines:** ~90

---

## Dependency Diagram

### Backend Dependency Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         main.py                                 │
│                    (FastAPI Entry Point)                        │
│                                                                 │
│  Registers: evolution, triage, soc, metrics routers            │
│  Manages: Neo4j connection lifecycle                           │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  evolution.py    │  │    triage.py     │  │     soc.py       │
│  (Tab 2 API)     │  │  (Tab 3 API)     │  │  (Tab 1 API)     │
│                  │  │                  │  │                  │
│  Imports:        │  │  Imports:        │  │  Imports:        │
│  • agent.py      │  │  • agent.py      │  │  • datetime      │
│  • reasoning.py  │  │  • reasoning.py  │  │  • pydantic      │
│  • neo4j.py      │  │  • neo4j.py      │  │                  │
│  • schemas.py    │  │  • schemas.py    │  │  No external     │
└──────────────────┘  └──────────────────┘  │  dependencies    │
        │                     │              └──────────────────┘
        └─────────────────────┼─────────────────────┐
                              ▼                     ▼
                    ┌──────────────────┐  ┌──────────────────┐
                    │   metrics.py     │  │   agent.py       │
                    │  (Tab 4 API)     │  │ (Decision Engine)│
                    │                  │  │                  │
                    │  Imports:        │  │  Imports:        │
                    │  • datetime      │  │  • schemas.py    │
                    │  • pydantic      │  └──────────────────┘
                    │                  │           │
                    │  No external     │           ▼
                    │  dependencies    │  ┌──────────────────┐
                    └──────────────────┘  │  reasoning.py    │
                                          │ (LLM Narration)  │
                                          │                  │
                                          │  Imports:        │
                                          │  • schemas.py    │
                                          │  • Vertex AI     │
                                          └──────────────────┘
                                                   │
                    ┌──────────────────────────────┤
                    ▼                              ▼
           ┌──────────────────┐         ┌──────────────────┐
           │    neo4j.py      │         │   schemas.py     │
           │  (Graph Client)  │         │ (Pydantic Models)│
           │                  │         │                  │
           │  Imports:        │         │  Imports:        │
           │  • schemas.py    │         │  • pydantic      │
           │  • neo4j driver  │         │  • typing        │
           └──────────────────┘         └──────────────────┘
```

### Frontend Dependency Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         main.tsx                                │
│                    (React Entry Point)                          │
│                                                                 │
│  Mounts: <App />                                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                          App.tsx                                │
│                      (4-Tab Navigation)                         │
│                                                                 │
│  Manages: Active tab state                                      │
│  Renders: Tab components conditionally                          │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│SOCAnalyticsTab   │  │RuntimeEvolution  │  │ AlertTriageTab   │
│    (Tab 1)       │  │    Tab (Tab 2)   │  │    (Tab 3)       │
│                  │  │                  │  │                  │
│  Imports:        │  │  Imports:        │  │  Imports:        │
│  • api.ts        │  │  • api.ts        │  │  • api.ts        │
│  • Recharts      │  │  • lucide-react  │  │  • lucide-react  │
│  • lucide-react  │  └──────────────────┘  └──────────────────┘
└──────────────────┘           │                     │
        │                      └─────────────────────┘
        └──────────────────────┐                     │
                               ▼                     ▼
                    ┌──────────────────┐   ┌──────────────────┐
                    │ CompoundingTab   │   │     api.ts       │
                    │    (Tab 4)       │   │  (API Client)    │
                    │                  │   │                  │
                    │  Imports:        │   │  Exports:        │
                    │  • api.ts        │   │  • queryMetric() │
                    │  • Recharts      │   │  • getDeployments│
                    │  • lucide-react  │   │  • processAlert()│
                    └──────────────────┘   │  • getAlerts()   │
                               │            │  • executeAction()│
                               └────────────│  • getCompounding│
                                            │  • resetDemo()   │
                                            └──────────────────┘
```

---

## Import Flow

### Backend Request Flow (Tab 2 Example)

```
1. HTTP Request
   POST /api/alert/process
   Body: { alert_id: "ALERT-7823" }
        │
        ▼
2. main.py
   FastAPI routes to evolution.router
        │
        ▼
3. evolution.py
   async def process_alert(request: ProcessAlertRequest)
        │
        ├──▶ neo4j.py
        │    get_security_context(alert_id)
        │    └─▶ Returns: SecurityContext with 47 nodes
        │
        ├──▶ agent.py
        │    SecurityAgent.decide(alert_type, context)
        │    └─▶ Returns: Decision with action, confidence
        │
        ├──▶ reasoning.py
        │    ReasoningNarrator.generate_reasoning(...)
        │    └─▶ Returns: 2-3 sentence justification
        │
        ├──▶ agent.py
        │    SecurityAgent.evaluate_gates(decision, context, reasoning)
        │    └─▶ Returns: EvalGateResult with 4 scores
        │
        ├──▶ neo4j.py
        │    create_decision_trace(...)
        │    └─▶ Creates (:Decision), (:DecisionContext) nodes
        │
        ├──▶ agent.py
        │    SecurityAgent.maybe_trigger_evolution(decision, context)
        │    └─▶ Returns: EvolutionTrigger if pattern threshold met
        │
        └──▶ neo4j.py (if evolution triggered)
             create_evolution_event(...)
             └─▶ Creates (:Decision)-[:TRIGGERED_EVOLUTION]->(:EvolutionEvent)
        │
        ▼
4. HTTP Response
   {
     decision: {...},
     eval_gate: {...},
     triggered_evolution: {...},  ← THE KEY FEATURE
     execution_stats: {...}
   }
```

### Frontend Component Flow (Tab 2 Example)

```
1. RuntimeEvolutionTab.tsx
   User clicks "Process Alert"
        │
        ▼
2. api.ts
   processAlert("ALERT-7823")
   └─▶ POST /api/alert/process
        │
        ▼
3. Backend processing (see above)
        │
        ▼
4. api.ts
   Returns Promise<ProcessResult>
        │
        ▼
5. RuntimeEvolutionTab.tsx
   setResult(processResult)
   └─▶ Triggers re-render
        │
        ├──▶ EvalGatePanel shows 4 checks
        ├──▶ DecisionTrace shows reasoning
        └──▶ TriggeredEvolution shows evolution event ★
```

---

## Tab Support Matrix

| File | Tab 1 | Tab 2 | Tab 3 | Tab 4 | Purpose |
|------|-------|-------|-------|-------|---------|
| **Backend** |
| `main.py` | ✓ | ✓ | ✓ | ✓ | Application entry |
| `routers/soc.py` | ✓ | - | - | - | Natural language queries |
| `routers/evolution.py` | - | ✓ | - | - | Runtime evolution ★ |
| `routers/triage.py` | - | - | ✓ | - | Alert triage |
| `routers/metrics.py` | - | - | - | ✓ | Compounding metrics |
| `services/agent.py` | - | ✓ | ✓ | - | Decision engine |
| `services/reasoning.py` | - | ✓ | ✓ | - | LLM narration |
| `services/seed_neo4j.py` | - | ✓ | ✓ | - | Seed data module |
| `db/neo4j.py` | - | ✓ | ✓ | - | Graph operations |
| `models/schemas.py` | ✓ | ✓ | ✓ | ✓ | Data validation |
| `seed_neo4j.py` | - | ✓ | ✓ | - | Demo data |
| **Frontend** |
| `main.tsx` | ✓ | ✓ | ✓ | ✓ | React entry |
| `App.tsx` | ✓ | ✓ | ✓ | ✓ | Tab navigation |
| `tabs/SOCAnalyticsTab.tsx` | ✓ | - | - | - | Tab 1 UI |
| `tabs/RuntimeEvolutionTab.tsx` | - | ✓ | - | - | Tab 2 UI ★ |
| `tabs/AlertTriageTab.tsx` | - | - | ✓ | - | Tab 3 UI |
| `tabs/CompoundingTab.tsx` | - | - | - | ✓ | Tab 4 UI |
| `lib/api.ts` | ✓ | ✓ | ✓ | ✓ | API client |

---

## Key Architectural Patterns

### 1. Simple Rule-Based Agent
**Files:** `services/agent.py`

The agent is intentionally simple (~250 lines) with deterministic rules. This proves the ARCHITECTURE, not agent sophistication.

**Why:**
- Demo reliability (same input → same output)
- Auditability (CISOs can explain decisions)
- Faster build (no complex LLM orchestration)
- Clear separation (architecture ≠ AI magic)

### 2. LLM as Narrator Only
**Files:** `services/reasoning.py`

Gemini 1.5 Pro generates justification AFTER the decision is made. This is "intelligence theater."

**Why:**
- Decision already made by rules
- LLM makes rules sound like expert analysis
- Fallback templates ensure reliability
- No LLM = no demo breakage

### 3. Fixed Cypher Queries
**Files:** `db/neo4j.py`

All Neo4j queries are fixed, no dynamic generation.

**Why:**
- Predictable results (47 nodes always)
- Faster execution
- Safer (no injection risks)
- Demo reliability

### 4. TRIGGERED_EVOLUTION Relationship
**Files:** `db/neo4j.py`, `routers/evolution.py`

The key differentiator: `(:Decision)-[:TRIGGERED_EVOLUTION]->(:EvolutionEvent)`

**Why:**
- SIEMs don't have this
- Proves compounding intelligence
- Visual in Tab 2 (purple panel)
- The moat

### 5. Mock Data for Tab 1
**Files:** `routers/soc.py`

Tab 1 uses mock BigQuery data, no GCP setup required.

**Why:**
- Faster setup
- No credentials needed
- Deterministic for demos
- Easy to customize

---

## File Size Summary

| Category | Files | Total Lines | Avg Lines/File |
|----------|-------|-------------|----------------|
| **Backend Routers** | 4 | ~1,323 | ~331 |
| **Backend Services** | 3 | ~800 | ~267 |
| **Backend DB** | 1 | ~300 | ~300 |
| **Backend Models** | 1 | ~400 | ~400 |
| **Backend Utils** | 1 | ~200 | ~200 |
| **Frontend Tabs** | 4 | ~1,881 | ~470 |
| **Frontend Core** | 2 | ~90 | ~45 |
| **Frontend API** | 1 | ~90 | ~90 |
| **Total** | **17** | **~5,084** | **~299** |

---

## Critical Dependencies

### Backend
```
fastapi==0.104.1
pydantic==2.5.0
neo4j==5.14.0
google-cloud-aiplatform==1.38.0
python-dotenv==1.0.0
```

### Frontend
```
react@18.2.0
typescript@5.2.2
recharts@2.10.3
lucide-react@0.294.0
tailwindcss@3.3.5
```

---

## Environment Variables

```bash
# GCP
PROJECT_ID=soc-copilot-demo
REGION=us-central1

# Neo4j Aura
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password

# Vertex AI
VERTEX_AI_LOCATION=us-central1
```

---

## Testing the Architecture

### 1. Backend Only
```bash
cd backend
uvicorn app.main:app --reload --port 8000
curl http://localhost:8000/api/soc/metrics
```

### 2. Full Stack
```bash
# Terminal 1
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2
cd frontend
npm run dev

# Browser
http://localhost:5173
```

### 3. Individual Endpoints
```bash
# Tab 1
curl -X POST http://localhost:8000/api/soc/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Show MTTR by severity"}'

# Tab 2
curl -X POST http://localhost:8000/api/alert/process \
  -H "Content-Type: application/json" \
  -d '{"alert_id": "ALERT-7823"}'

# Tab 3
curl http://localhost:8000/api/triage/alerts

# Tab 4
curl http://localhost:8000/api/metrics/compounding?weeks=4
```

---

## The Three Key Files (Core Demo)

If you read only 3 files to understand the demo:

1. **`routers/evolution.py`** - The entire Tab 2 flow including TRIGGERED_EVOLUTION
2. **`services/agent.py`** - The simple decision engine proving architecture > sophistication
3. **`tabs/RuntimeEvolutionTab.tsx`** - The UI showing the key differentiator

These 3 files (~970 lines) contain the core demo thesis.

---

**Last Updated:** February 9, 2026
**Status:** All 4 tabs complete and operational
**Total Code:** ~5,084 lines across 17 files
**Key Principle:** The demo proves the ARCHITECTURE, not agent sophistication.
