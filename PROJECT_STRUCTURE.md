# SOC Copilot Demo - Project Structure

**Last Updated:** February 17, 2026
**Version:** v2.0 (Wave 6 Complete)
**Total Files:** 25 code files (~3,800 lines)
**Architecture:** Two-loop compounding intelligence with runtime evolution, situation analysis, and agent evolution

---

## Table of Contents

- [Directory Tree](#directory-tree)
- [v2 Enhancements](#v2-enhancements)
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
gen-ai-roi-demo-v2/
│
├── .gitignore                       # Git ignore (includes .claude/)
│
├── backend/
│   ├── requirements.txt              # Python dependencies
│   ├── seed_neo4j.py                 # Neo4j seed data script (updated for v2)
│   └── app/
│       ├── main.py                   # FastAPI application entry point
│       ├── routers/
│       │   ├── __init__.py
│       │   ├── soc.py                # Tab 1: SOC Analytics
│       │   ├── evolution.py          # Tab 2: Runtime Evolution (v2: blocking, situation, evolver)
│       │   ├── triage.py             # Tab 3: Alert Triage (v2: situation analysis)
│       │   └── metrics.py            # Tab 4: Compounding Metrics (v2: business impact)
│       ├── services/
│       │   ├── __init__.py
│       │   ├── agent.py              # Simple rule-based decision engine
│       │   ├── reasoning.py          # LLM narration service
│       │   ├── situation.py          # ★ NEW v2: Situation Analyzer (6 types, decision economics)
│       │   ├── evolver.py            # ★ NEW v2: AgentEvolver (prompt tracking, operational impact)
│       │   └── seed_neo4j.py         # Neo4j seed data (service module, updated for v2)
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
        ├── App.tsx                   # 4-tab navigation root (v2: version 2.0)
        ├── lib/
        │   └── api.ts                # Backend API client (v2: processAlertBlocked)
        └── components/
            └── tabs/
                ├── SOCAnalyticsTab.tsx       # Tab 1
                ├── RuntimeEvolutionTab.tsx   # Tab 2 (v2: CMA labels, animation, blocking, AgentEvolver)
                ├── AlertTriageTab.tsx        # Tab 3 (v2: CMA labels, Situation Analyzer)
                └── CompoundingTab.tsx        # Tab 4 (v2: counter animations, impact banner, two-loop diagram)
```

---

## v2 Enhancements

**Branch:** `feature/v2-enhancements`
**Base:** v1.0 (frozen on `main`)

### Wave 1: Labels + Visual Polish ✅
- **Files:** RuntimeEvolutionTab.tsx, AlertTriageTab.tsx, CompoundingTab.tsx, App.tsx
- **Features:**
  - CONSUME/MUTATE/ACTIVATE labels on Tabs 2 & 3
  - Eval gate sequential animation (800ms per check)
  - Counter animations in Tab 4 (3-second count-up)
  - Version bump to v2.0

### Wave 2: Blocking Demo ✅
- **Files:** evolution.py, RuntimeEvolutionTab.tsx, api.ts
- **Features:**
  - POST /api/alert/process-blocked endpoint
  - "Simulate Failed Gate" button in Tab 2
  - BLOCKED banner when eval gate fails
  - Safety layer demonstration

### Wave 3: Situation Analyzer — Backend ✅
- **Files:** situation.py (NEW), evolution.py, triage.py
- **Features:**
  - 6 situation types (TRAVEL_LOGIN_ANOMALY, KNOWN_PHISHING_CAMPAIGN, etc.)
  - classify_situation() — pattern matching logic
  - evaluate_options() — multi-option assessment
  - analyze_situation() — full situation analysis
  - situation_analysis in API responses

### Wave 4: Situation Analyzer — Frontend ✅
- **Files:** AlertTriageTab.tsx
- **Features:**
  - Situation panel between graph and recommendation
  - Type badge with color coding
  - Key factors display
  - Options bar chart (3-4 options per situation)
  - Situation reasoning text

### Wave 5: AgentEvolver + Second Alert ✅
- **Files:** evolver.py (NEW), evolution.py, RuntimeEvolutionTab.tsx, seed_neo4j.py
- **Features:**
  - Prompt variant tracking (TRAVEL_CONTEXT_v1 vs v2, etc.)
  - Promotion logic (>5% improvement → promote)
  - AgentEvolver panel in Tab 2 (variant bars, promotion status)
  - Second alert type: ALERT-7824 (phishing - Mary Chen)
  - PAT-PHISH-KNOWN pattern
  - PhishingCampaign node (Operation DarkHook)

### Wave 6: Business Impact + Documentation ✅
- **Files:** situation.py, evolver.py, metrics.py, RuntimeEvolutionTab.tsx, AlertTriageTab.tsx, CompoundingTab.tsx, CLAUDE.md, PROJECT_STRUCTURE.md
- **Features:**
  - **6A:** Decision economics (time/cost/risk per option)
  - **6B:** Operational impact narrative (what changed, monthly savings)
  - **6C:** Business impact banner in Tab 4 (847 hrs saved, $127K avoided/qtr, 75% MTTR reduction, 2,400 backlog eliminated)
  - **6D:** Two-loop hero diagram in Tab 4 (dark theme, center graph, Loop 1 & 2 boxes, stats row)
  - **6E:** Documentation updates (this file + CLAUDE.md)

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
- Keyword-based metric matching
- Rule sprawl detection
- Mock BigQuery data (no GCP setup required)

---

#### `backend/app/routers/evolution.py`

**Purpose:** Tab 2 (Runtime Evolution) API endpoints showing TRIGGERED_EVOLUTION - the key differentiator.

**v2 Updates:**
- Added POST /api/alert/process-blocked endpoint for blocking demo
- Integrated situation_analysis from situation.py
- Integrated prompt_evolution from evolver.py
- Returns situation_analysis and prompt_evolution in responses

**Key Functions/Exports:**
- `router` - FastAPI APIRouter instance
- `get_deployments()` - GET /api/deployments
  - Returns: v3.1 (active, 90%) and v3.2 (canary, 10%)
- `process_alert(request: ProcessAlertRequest)` - POST /api/alert/process
  - **THE KEY FLOW:** 9 steps (v2 expanded from 7)
    1. Get security context (47 nodes from Neo4j)
    2. **Situation analysis (v2 new)**
    3. Agent decision (rule-based)
    4. LLM reasoning (narration)
    5. Eval gate (4 checks)
    6. Create decision trace in Neo4j
    7. Check if evolution triggers
    8. Create TRIGGERED_EVOLUTION relationship
    9. **Get prompt evolution summary (v2 new)**
  - Returns: decision, situation_analysis, eval_gate, triggered_evolution, prompt_evolution, execution_stats
- `process_alert_blocked(request: ProcessAlertRequest)` - POST /api/alert/process-blocked (v2 new)
  - Simulates eval gate failure for demo
  - Shows blocked state with detailed reason

**Dependencies:**
```python
from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from app.db.neo4j import neo4j_client
from app.services.agent import SecurityAgent
from app.services.reasoning import ReasoningNarrator
from app.services.situation import analyze_situation  # v2 new
from app.services.evolver import get_evolution_summary  # v2 new
from app.models.schemas import ProcessAlertRequest
```

**Tab Support:** Tab 2 (Runtime Evolution) ★ THE DIFFERENTIATOR

**Lines:** ~350 (expanded from ~250)

**Notable Features:**
- Integration point between agent, Neo4j, LLM, situation analyzer, and evolver
- TRIGGERED_EVOLUTION relationship creation
- Eval gate with 4 deterministic checks
- Decision trace persistence
- Blocking demo simulation

---

#### `backend/app/routers/triage.py`

**Purpose:** Tab 3 (Alert Triage) API endpoints for graph-based alert analysis and closed-loop execution.

**v2 Updates:**
- Integrated situation_analysis from situation.py
- Added situation_analysis to analyze_alert response

**Key Functions/Exports:**
- `router` - FastAPI APIRouter instance
- `get_alert_queue()` - GET /api/triage/alerts
  - Returns: 5 pending alerts from seed data (v2: now includes ALERT-7824 phishing)
- `analyze_alert(alert_id: str)` - POST /api/triage/analyze
  - Graph traversal + situation analysis + recommendation
  - Returns: decision, situation_analysis (v2 new), reasoning, confidence, graph_data (nodes/edges)
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
from app.services.situation import analyze_situation  # v2 new
```

**Tab Support:** Tab 3 (Alert Triage)

**Lines:** ~450 (expanded from ~400)

**Notable Features:**
- Simple graph visualization
- 4-step closed-loop execution with verification
- KPI impact calculation (MTTR improvement)
- Situation analysis integration

---

#### `backend/app/routers/metrics.py`

**Purpose:** Tab 4 (Compounding Dashboard) API endpoints showing week-over-week intelligence growth.

**v2 Updates:**
- Added BusinessImpact model
- Added business_impact to CompoundingResponse
- Returns business_impact with 4 key metrics for CFO reporting

**Key Functions/Exports:**
- `router` - FastAPI APIRouter instance
- `get_compounding_metrics(weeks: int = 4)` - GET /api/metrics/compounding
  - Returns: headline (Week 1 vs Week 4), weekly_trend, evolution_events, business_impact (v2 new)
  - Week 1: 23 patterns, 68% auto-close
  - Week 4: 127 patterns, 89% auto-close
  - Business Impact: 847 hrs saved/mo, $127K avoided/qtr, 75% MTTR reduction, 2,400 backlog eliminated
- `get_evolution_events(limit: int = 10)` - GET /api/metrics/evolution-events
  - Returns: Recent evolution events list
- `seed_neo4j()` - POST /api/demo/seed (v2 new)
  - Seeds Neo4j with canonical test data
- `reset_all_demo_data()` - POST /api/demo/reset-all (v2 new)
  - Comprehensive reset via re-seeding
- `reset_demo_data()` - POST /api/demo/reset (legacy)
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

**Lines:** ~350 (expanded from ~270)

**Notable Features:**
- Mock data showing gradual improvement (4 weeks)
- Evolution events timeline
- Business impact summary for CFO reporting
- Demo reset functionality for repeated presentations

---

### Services

#### `backend/app/services/agent.py`

**Purpose:** Simple rule-based decision engine. Intentionally deterministic for demo reliability.

**Key Functions/Exports:**
- `SecurityAgent` class
  - `decide(alert_type: str, context: SecurityContext) -> Decision`
    - 4 primary rules for alert types (v2: now includes phishing)
    - Returns: action, confidence, pattern_id
  - `evaluate_gates(decision, context, reasoning) -> EvalGateResult`
    - 4 checks: Faithfulness, Safe Action, Playbook Match, SLA
    - Returns: 4 gate scores with pass/fail
  - `maybe_trigger_evolution(decision, context) -> EvolutionTrigger | None`
    - Checks if pattern_id exists and occurrence threshold met
    - Returns: event details if evolution triggered

**Alert Types Handled:**
1. **anomalous_login** - Travel matching
2. **phishing** - Known campaign signature check (v2 enhanced)
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

---

#### `backend/app/services/reasoning.py`

**Purpose:** LLM narration service using Gemini 1.5 Pro. Makes rule-based decisions sound like expert security analysis.

**Key Functions/Exports:**
- `ReasoningNarrator` class
  - `generate_reasoning(alert_type, decision, context) -> str`
    - Generates 2-3 sentence justification AFTER decision made
    - Uses Gemini 1.5 Pro via Vertex AI
    - Falls back to template if LLM unavailable

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

---

#### `backend/app/services/situation.py` ★ NEW v2

**Purpose:** Situation Analyzer — classifies alert situations, evaluates options with decision economics.

**Key Functions/Exports:**
- `SituationType` enum - 6 situation types:
  - TRAVEL_LOGIN_ANOMALY
  - KNOWN_PHISHING_CAMPAIGN
  - CRITICAL_ASSET_MALWARE
  - DATA_EXFILTRATION_DETECTED
  - UNKNOWN_LOGIN_PATTERN
  - ROUTINE_MALWARE_SCAN
- `classify_situation(alert_type, context) -> SituationType`
  - Pattern matching logic for situation classification
- `evaluate_options(situation_type, context) -> List[OptionEvaluated]`
  - Generates 3-4 options per situation
  - **v2 Wave 6A:** Includes decision economics (time, cost, risk)
  - Returns: option name, reasoning, confidence, estimated_resolution_time, estimated_analyst_cost, risk_if_wrong
- `analyze_situation(alert_type, context) -> SituationAnalysis`
  - Full situation analysis combining classification and evaluation
  - **v2 Wave 6A:** Includes decision_economics summary (time saved, cost avoided, monthly projection)
  - Returns: type, primary_factors, options_evaluated, reasoning, decision_economics

**Dependencies:**
```python
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
```

**Tab Support:** Tab 2 (situation context), Tab 3 (situation panel)

**Lines:** ~280

**Notable Features:**
- 6 situation types covering common SOC scenarios
- Multi-option evaluation (not just binary)
- Decision economics for CISO/CFO reporting
- Deterministic classification for demo reliability

---

#### `backend/app/services/evolver.py` ★ NEW v2

**Purpose:** AgentEvolver — tracks prompt variant performance, promotes winners, computes operational impact.

**Key Functions/Exports:**
- `PROMPT_STATS` - In-memory prompt performance tracking
  - TRAVEL_CONTEXT_v1: 24/34 (71%)
  - TRAVEL_CONTEXT_v2: 42/47 (89%)
  - PHISHING_RESPONSE_v1: 31/38 (82%)
  - PHISHING_RESPONSE_v2: 12/15 (80%)
- `ACTIVE_PROMPTS` - Currently active variant per alert type
- `get_prompt_variant(alert_type) -> str`
  - Returns active prompt variant
- `record_decision_outcome(decision_id, prompt_variant, success)`
  - Records outcome, updates stats
- `check_for_promotion(alert_type) -> Optional[Dict]`
  - Checks if better variant should be promoted (>5% improvement)
  - Promotes automatically if threshold met
- `generate_what_changed_narrative(alert_type, old_rate, new_rate) -> str` (v2 Wave 6B)
  - Plain English explanation of what improved
  - Alert-specific narratives
- `calculate_operational_impact(old_rate, new_rate) -> OperationalImpact` (v2 Wave 6B)
  - Computes monthly savings from improvement
  - Returns: fewer_false_escalations_pct, fewer_false_escalations_monthly, analyst_hours_recovered, estimated_monthly_savings, missed_threats (always 0)
- `get_evolution_summary(alert_type) -> PromptEvolution`
  - Returns current state with any recent promotion
  - **v2 Wave 6B:** Now includes what_changed_narrative and operational_impact

**Models:**
- `OperationalImpact` - Business metrics from evolution
- `PromptEvolution` - Evolution data for UI display

**Dependencies:**
```python
from typing import Dict, Any, Optional
from pydantic import BaseModel
```

**Tab Support:** Tab 2 (AgentEvolver panel)

**Lines:** ~330

**Notable Features:**
- Automatic promotion of better variants
- Operational impact calculation for CISO reporting
- What-changed narratives in plain English
- Demo-friendly in-memory state

---

#### `backend/app/services/seed_neo4j.py`

**Purpose:** Neo4j seed data constants as a service module. Contains canonical test data.

**v2 Updates:**
- Added ALERT-7824 (phishing - Mary Chen)
- Added Mary Chen user definition
- Added PAT-PHISH-KNOWN pattern
- Added PhishingCampaign node (Operation DarkHook)

**Key Functions/Exports:**
- `ASSETS` - List of 5 asset definitions
- `USERS` - List of 5 user definitions (v2: added Mary Chen)
- `ALERT_TYPES` - List of 4 alert type definitions
- `PATTERNS` - List of 5+ attack pattern definitions (v2: added PAT-PHISH-KNOWN)
- `PLAYBOOKS` - List of 4 playbook definitions

**Dependencies:**
```python
from typing import Dict, Any, List
from app.db.neo4j import neo4j_client
```

**Tab Support:** Tab 2, Tab 3 (provides canonical seed data)

**Lines:** ~600+ (expanded from ~500+)

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
  - `create_decision_trace(decision_id, alert_id, decision, context, reasoning)`
    - Creates (:Decision), (:DecisionContext) nodes
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

**v2 Updates:**
- Added SituationAnalysis, SituationType, OptionEvaluated models
- Added PromptEvolution, OperationalImpact models
- Updated ProcessResult to include situation_analysis and prompt_evolution
- Added DecisionEconomics model

**Key Classes/Exports:**

**Tab 1 Models:** (unchanged)
- `SOCQueryRequest`, `MetricContract`, `MetricDataPoint`, `Provenance`, `SprawlAlert`

**Tab 2 Models:**
- `ProcessAlertRequest`, `Deployment`, `EvalGateCheck`, `EvalGateResult`
- `TriggeredEvolution`, `ExecutionStats`
- `PromptEvolution` (v2 new) - includes operational_impact, what_changed_narrative
- `OperationalImpact` (v2 new) - business metrics

**Tab 3 Models:**
- `AlertSummary`, `ActionRequest`, `Receipt`, `Verification`, `Evidence`, `KpiImpact`
- `SituationAnalysis` (v2 new), `SituationType` (v2 new), `OptionEvaluated` (v2 new)
- `DecisionEconomics` (v2 new) - time/cost/risk metrics

**Tab 4 Models:**
- `WeeklyMetrics`, `EvolutionEvent`, `CompoundingResponse`
- `BusinessImpact` (v2 new) - CFO reporting metrics

**Core Models:**
- `SecurityContext`, `Decision`, `EvolutionTrigger`

**Dependencies:**
```python
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
```

**Tab Support:** All tabs (data validation layer)

**Lines:** ~550 (expanded from ~400)

---

### Utilities

#### `backend/seed_neo4j.py`

**Purpose:** Seed Neo4j database with demo data.

**v2 Updates:**
- Added ALERT-7824 (phishing - Mary Chen, susanmorgan@phishmail.com)
- Added Mary Chen user node
- Added PAT-PHISH-KNOWN pattern (214 occurrences, 82% FP rate)
- Added PhishingCampaign node (Operation DarkHook, November 2025)
- Added relationships connecting phishing alert to campaign

**Key Functions/Exports:**
- `seed_neo4j()` - Main seeding function
  - Creates 5 users (v2: added Mary Chen, Marketing Manager)
  - Creates 5 assets
  - Creates 4 alert types
  - Creates 6+ attack patterns (v2: added PAT-PHISH-KNOWN)
  - Creates 4 playbooks
  - Creates 6 alerts (v2: added ALERT-7824)
  - Creates travel context for John Smith
  - Creates phishing campaign node (v2 new)

**Dependencies:**
```python
from neo4j import GraphDatabase
import os
from datetime import datetime, timedelta
```

**Tab Support:** Tab 2, Tab 3 (provides graph data)

**Lines:** ~250 (expanded from ~200)

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

**v2 Updates:**
- Version bumped to v2.0

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

**(No v2 changes)**

**Key Components/Exports:**
- `SOCAnalyticsTab` - Main tab component
  - Natural language query input
  - 5 example question chips
  - Metric result with chart (Recharts)
  - Metric contract panel
  - Provenance panel
  - Rule sprawl alert

**API Calls:**
- POST /api/soc/query

**Tab Support:** Tab 1 (SOC Analytics)

**Lines:** ~476

---

#### `frontend/src/components/tabs/RuntimeEvolutionTab.tsx`

**Purpose:** Tab 2 - Runtime evolution showing TRIGGERED_EVOLUTION. THE KEY DIFFERENTIATOR.

**v2 Updates:**
- **Wave 1:** Added CONSUME/MUTATE/ACTIVATE labels
- **Wave 1:** Added eval gate sequential animation (800ms per check)
- **Wave 2:** Added "Simulate Failed Gate" button and BLOCKED banner
- **Wave 5:** Added AgentEvolver panel (variant comparison bars, promotion status)
- **Wave 6B:** Added operational impact metrics (what changed narrative, 5 impact cards: false escalation %, monthly reviews, hours recovered, monthly savings, missed threats)

**Key Components/Exports:**
- `RuntimeEvolutionTab` - Main tab component
  - Deployment registry table
  - Process Alert button (ALERT-7823)
  - Simulate Failed Gate button (v2 new)
  - Eval Gate panel with sequential animation (v2: 800ms per check)
  - BLOCKED banner (v2 new) - shown when eval gate fails
  - Decision Trace panel
  - **TRIGGERED_EVOLUTION panel (purple, THE KEY FEATURE)**
  - **AgentEvolver panel (v2 new)** - Loop 2 visualization:
    - Variant comparison bars (current vs previous)
    - Promotion status badge
    - What changed narrative (v2 Wave 6B)
    - Operational impact cards (v2 Wave 6B): fewer escalations, hours recovered, monthly savings, missed threats
  - Execution Stats

**Key Features:**
- CMA labels (CONSUME/MUTATE badges)
- Sequential gate animation (800ms timing)
- Blocking demo simulation
- Prompt evolution tracking
- Operational impact visualization

**Dependencies:**
```typescript
import { useState, useEffect } from 'react'
import { getDeployments, processAlert, processAlertBlocked } from '../../lib/api'
import { Activity, CheckCircle, XCircle, AlertTriangle, Zap, Clock, Sparkles, Shield, TrendingUp, Lightbulb, DollarSign } from 'lucide-react'
```

**API Calls:**
- GET /api/deployments
- POST /api/alert/process
- POST /api/alert/process-blocked (v2 new)

**Tab Support:** Tab 2 (Runtime Evolution) ★ THE DIFFERENTIATOR

**Lines:** ~710 (expanded from ~470)

**Soundbites:**
- "Splunk gets better rules. Our copilot gets **smarter**."
- "Loop 2 makes the agent smarter ACROSS decisions by learning which prompts work best."

---

#### `frontend/src/components/tabs/AlertTriageTab.tsx`

**Purpose:** Tab 3 - Graph-based alert triage with closed-loop execution.

**v2 Updates:**
- **Wave 1:** Added CONSUME/MUTATE/ACTIVATE label
- **Wave 4:** Added Situation Analyzer panel (type badge, factors, options bar chart, reasoning)
- **Wave 6A:** Added decision economics (time/cost/risk columns in options, economics summary box)

**Key Components/Exports:**
- `AlertTriageTab` - Main tab component
  - Alert Queue sidebar (5+ alerts, v2: includes ALERT-7824 phishing)
  - **Situation Analyzer panel (v2 new):**
    - Situation type badge with color coding
    - Key factors list
    - Options bar chart with confidence %
    - **Decision economics (v2 Wave 6A):** time, cost, risk per option
    - Situation reasoning text
    - **Economics summary (v2 Wave 6A):** time saved, cost avoided, monthly projection
  - Simple graph visualization (colored boxes)
  - Recommendation panel
  - Closed Loop Execution panel (4 steps)

**Key Features:**
- CMA label (ACTIVATE badge)
- Situation classification (6 types)
- Multi-option evaluation
- Decision economics visualization
- Sequential animation (800ms per step)

**Dependencies:**
```typescript
import { useState, useEffect } from 'react'
import { getAlerts, analyzeAlert, executeAction } from '../../lib/api'
import { Shield, AlertCircle, CheckCircle, Clock, Database, FileText, Activity, TrendingUp, DollarSign } from 'lucide-react'
```

**API Calls:**
- GET /api/triage/alerts
- POST /api/triage/analyze
- POST /api/triage/execute

**Tab Support:** Tab 3 (Alert Triage)

**Lines:** ~680 (expanded from ~518)

**Soundbite:** "A SIEM stops at detect. We **close the loop**."

---

#### `frontend/src/components/tabs/CompoundingTab.tsx`

**Purpose:** Tab 4 - Compounding intelligence dashboard proving the moat.

**v2 Updates:**
- **Wave 1:** Added counter animations (3-second count-up with ease-out)
- **Wave 6C:** Added business impact banner (847 hrs saved, $127K avoided, 75% MTTR reduction, 2,400 backlog eliminated) with animated counters
- **Wave 6D:** Replaced two-loop visual with hero diagram (dark theme, center graph with pulse, Loop 1 & 2 panels, TRIGGERED_EVOLUTION badge, stats row)

**Key Components/Exports:**
- `CompoundingTab` - Main tab component
  - `useCountUp` hook (v2 new) - custom counter animation with ease-out
  - **Business Impact Banner (v2 Wave 6C):**
    - 4 animated metric cards (analyst hours, cost avoided, MTTR reduction, backlog eliminated)
    - Executive summary styling
    - CFO reporting focus
  - **The Headline** - Week 1 vs Week 4 visual comparison (with animated counters)
  - **Weekly Trend Chart** - Recharts LineChart
  - **Two-Loop Hero Diagram (v2 Wave 6D):**
    - Dark slate background
    - Center: Context Graph (Neo4j) with pulse animation
    - Left: Loop 1 - Situation Analyzer (blue theme)
    - Right: Loop 2 - Agent Evolver (purple theme)
    - Bottom: TRIGGERED_EVOLUTION connection badge
    - Stats row: Situation types (2→6), Prompt variants (0→4), Cross-alert patterns (47 travel, 31 phishing)
  - **Recent Evolution Events** - Timeline
  - **The Moat Message** - Purple-to-blue gradient banner
  - **Reset Demo Button** - Comprehensive reset

**Key Features:**
- Counter animations (3 seconds, ease-out)
- Business impact visualization
- Two-loop architectural diagram
- Visual graph growth
- Evolution event timeline

**Dependencies:**
```typescript
import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { getCompoundingMetrics, resetAllDemoData } from '../../lib/api'
import { TrendingUp, Database, Activity, RefreshCw, Clock, DollarSign, TrendingDown, CheckCircle } from 'lucide-react'
```

**API Calls:**
- GET /api/metrics/compounding?weeks=4
- POST /api/demo/reset-all

**Tab Support:** Tab 4 (Compounding Dashboard)

**Lines:** ~680 (expanded from ~417)

**Soundbites:**
- "When they deploy, they start at zero. We start at **127 patterns**."
- "SIEMs get better rules. Our copilot **becomes** a better copilot."

---

### API Client

#### `frontend/src/lib/api.ts`

**Purpose:** Centralized API client for all backend communication.

**v2 Updates:**
- Added processAlertBlocked() function for blocking demo

**Key Functions/Exports:**

**Helper:**
- `fetchJSON<T>(url, options)` - Typed fetch wrapper

**Tab 1: SOC Analytics**
- `queryMetric(query: string)` - POST /api/soc/query

**Tab 2: Runtime Evolution**
- `getDeployments()` - GET /api/deployments
- `processAlert(alertId, simulateFailure)` - POST /api/alert/process
- `processAlertBlocked(alertId)` - POST /api/alert/process-blocked (v2 new)

**Tab 3: Alert Triage**
- `getAlerts()` - GET /api/triage/alerts
- `analyzeAlert(alertId)` - POST /api/triage/analyze
- `executeAction(alertId, action)` - POST /api/triage/execute

**Tab 4: Compounding Metrics**
- `getCompoundingMetrics(weeks)` - GET /api/metrics/compounding?weeks=4
- `getEvolutionEvents(limit)` - GET /api/metrics/evolution-events?limit=10
- `resetAllDemoData()` - POST /api/demo/reset-all (v2 new)

**Dependencies:**
```typescript
// None - pure TypeScript
```

**Tab Support:** All tabs (API abstraction layer)

**Lines:** ~110 (expanded from ~90)

---

## Dependency Diagram

### Backend Dependency Flow (v2)

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
│  • situation.py ★│  │  • situation.py ★│  │                  │
│  • evolver.py ★  │  │  • neo4j.py      │  │  No external     │
│  • neo4j.py      │  │  • schemas.py    │  │  dependencies    │
│  • schemas.py    │  └──────────────────┘  └──────────────────┘
└──────────────────┘           │
        │                      └──────────────┐
        └─────────────────────┼───────────────┼─────────────────┐
                              ▼               ▼                 ▼
                    ┌──────────────────┐  ┌──────────────────┐
                    │   metrics.py     │  │   situation.py ★ │
                    │  (Tab 4 API)     │  │ (Loop 1 Service) │
                    │                  │  │                  │
                    │  Imports:        │  │  Imports:        │
                    │  • datetime      │  │  • schemas.py    │
                    │  • pydantic      │  │  • pydantic      │
                    └──────────────────┘  └──────────────────┘
                              │                      │
                              ▼                      ▼
                    ┌──────────────────┐  ┌──────────────────┐
                    │   evolver.py ★   │  │   agent.py       │
                    │ (Loop 2 Service) │  │ (Decision Engine)│
                    │                  │  │                  │
                    │  Imports:        │  │  Imports:        │
                    │  • pydantic      │  │  • schemas.py    │
                    └──────────────────┘  └──────────────────┘
                                                   │
                                                   ▼
                                          ┌──────────────────┐
                                          │  reasoning.py    │
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

★ = New in v2
```

### Frontend Dependency Flow (v2)

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
│                         v2.0 ★                                  │
│                                                                 │
│  Manages: Active tab state                                      │
│  Renders: Tab components conditionally                          │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│SOCAnalyticsTab   │  │RuntimeEvolution  │  │ AlertTriageTab   │
│    (Tab 1)       │  │    Tab (Tab 2) ★ │  │    (Tab 3) ★     │
│                  │  │                  │  │                  │
│  Imports:        │  │  v2 adds:        │  │  v2 adds:        │
│  • api.ts        │  │  • CMA labels    │  │  • CMA label     │
│  • Recharts      │  │  • Animation     │  │  • Situation     │
│  • lucide-react  │  │  • Blocking      │  │    panel         │
│                  │  │  • AgentEvolver  │  │  • Economics     │
└──────────────────┘  └──────────────────┘  └──────────────────┘
        │                      │                     │
        └──────────────────────┼─────────────────────┘
                               ▼                     │
                    ┌──────────────────┐            │
                    │ CompoundingTab ★ │            │
                    │    (Tab 4)       │            │
                    │                  │            │
                    │  v2 adds:        │            │
                    │  • Counters      │            │
                    │  • Impact banner │            │
                    │  • Hero diagram  │            │
                    └──────────────────┘            │
                               │                    │
                               └────────────────────┘
                                        ▼
                               ┌──────────────────┐
                               │     api.ts ★     │
                               │  (API Client)    │
                               │                  │
                               │  v2 adds:        │
                               │  • processAlert  │
                               │    Blocked()     │
                               │  • resetAllDemo  │
                               │    Data()        │
                               └──────────────────┘

★ = Enhanced in v2
```

---

## Tab Support Matrix (v2)

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
| `services/situation.py` ★ | - | ✓ | ✓ | - | Situation analysis (Loop 1) |
| `services/evolver.py` ★ | - | ✓ | - | - | Agent evolution (Loop 2) |
| `services/seed_neo4j.py` | - | ✓ | ✓ | - | Seed data module |
| `db/neo4j.py` | - | ✓ | ✓ | - | Graph operations |
| `models/schemas.py` | ✓ | ✓ | ✓ | ✓ | Data validation |
| `seed_neo4j.py` | - | ✓ | ✓ | - | Demo data |
| **Frontend** |
| `main.tsx` | ✓ | ✓ | ✓ | ✓ | React entry |
| `App.tsx` | ✓ | ✓ | ✓ | ✓ | Tab navigation (v2.0) |
| `tabs/SOCAnalyticsTab.tsx` | ✓ | - | - | - | Tab 1 UI |
| `tabs/RuntimeEvolutionTab.tsx` | - | ✓ | - | - | Tab 2 UI ★ (CMA, blocking, evolver) |
| `tabs/AlertTriageTab.tsx` | - | - | ✓ | - | Tab 3 UI (CMA, situation, economics) |
| `tabs/CompoundingTab.tsx` | - | - | - | ✓ | Tab 4 UI (counters, impact, diagram) |
| `lib/api.ts` | ✓ | ✓ | ✓ | ✓ | API client |

★ = New or significantly enhanced in v2

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

### 5. Two-Loop Architecture (v2)
**Files:** `services/situation.py` (Loop 1), `services/evolver.py` (Loop 2)

**Loop 1 - Situation Analyzer:** Smarter WITHIN each decision
- Classifies situations (6 types)
- Evaluates multiple options
- Provides decision economics

**Loop 2 - Agent Evolver:** Smarter ACROSS all decisions
- Tracks prompt variant performance
- Promotes better variants automatically
- Computes operational impact

**Both loops write to the same graph → COMPOUNDING**

---

## File Size Summary (v2)

| Category | Files | Total Lines | Avg Lines/File |
|----------|-------|-------------|----------------|
| **Backend Routers** | 4 | ~1,553 | ~388 |
| **Backend Services** | 5 | ~1,360 | ~272 |
| **Backend DB** | 1 | ~300 | ~300 |
| **Backend Models** | 1 | ~550 | ~550 |
| **Backend Utils** | 1 | ~250 | ~250 |
| **Frontend Tabs** | 4 | ~2,546 | ~637 |
| **Frontend Core** | 2 | ~90 | ~45 |
| **Frontend API** | 1 | ~110 | ~110 |
| **Total** | **19** | **~6,759** | **~356** |

*Note: v2 added 2 new service files (situation.py, evolver.py) and significantly expanded existing files.*

---

## v2 Git Workflow

### Branch Structure
```
main (v1.0 frozen, tag: v1.0)
  └── feature/v2-enhancements (v2 development)
```

### Ports
- **Backend:** 8001 (v1 uses 8000)
- **Frontend:** 5174 (v1 uses 5173)

### Commands
```bash
# Start v2 backend
cd backend
uvicorn app.main:app --reload --port 8001

# Start v2 frontend
cd frontend
npx vite --port 5174

# View v2 in browser
http://localhost:5174
```

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

## The Five Key Files (Core v2 Demo)

If you read only 5 files to understand the v2 demo:

1. **`routers/evolution.py`** - The entire Tab 2 flow including situation, evolution, and blocking
2. **`services/situation.py`** ★ - Loop 1: Situation Analyzer with decision economics
3. **`services/evolver.py`** ★ - Loop 2: AgentEvolver with operational impact
4. **`services/agent.py`** - The simple decision engine proving architecture > sophistication
5. **`tabs/RuntimeEvolutionTab.tsx`** - The UI showing both loops and their value

These 5 files (~1,570 lines) contain the core v2 demo thesis.

---

**Last Updated:** February 17, 2026
**Status:** v2.0 Wave 6 Complete — All tabs operational with business impact features
**Total Code:** ~6,759 lines across 19 core files
**Key Principle:** The demo proves the ARCHITECTURE (two loops → compounding), not agent sophistication.
**v2 Focus:** Making the business impact visible to CISOs and CFOs through decision economics and operational metrics.
