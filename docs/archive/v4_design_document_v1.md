# SOC Copilot Demo — Design Document v4.0 (v1)

**Version:** 1.0
**Date:** February 24, 2026
**Status:** v3.0 complete and tagged. v4.0 design ready for build.
**Prerequisite:** v3.0 tagged on main
**Theme:** "Your tools, our decisions."
**Repos:**
- Demo: git@github.com:ArindamBanerji/gen-ai-roi-demo.git (main, v3.0)
- Experiments: git@github.com:ArindamBanerji/cross-graph-experiments.git (main, v1.0)

---

## SECTION 0: Why v4 Exists

A customer meeting on Feb 24 surfaced a clear gap: the v3 demo is impressive but isolated. The prospect said:

1. "We collect IOCs from Pulsedive, GreyNoise, ThreatYeti." → v3 integrates one. v4 shows the pattern scales to N.
2. "We use CrowdStrike Falcon as our dashboard." → v4 positions us ON TOP of their stack, not replacing it.
3. "Can your system work with OUR data?" → v4 starts answering that with multi-source connectors.

**v3 proved the intelligence.** v4 proves it plugs into the customer's world.

---

## SECTION 1: Version Roadmap

| Version | Theme | ACCP Capabilities | Status |
|---|---|---|---|
| v1.0 | Context graph | 1/21 | ✅ Done |
| v2.0 | Two loops + eval gates | 7/21 | ✅ Done |
| v2.5 | Interactivity + governance | 10/21 | ✅ Done |
| v3.0 | Three loops. Auditable. Connected. Transparent. | 14/21 | ✅ Done |
| **v4.0** | **Your tools, our decisions.** | **18/21** | **BUILD** |
| v5.0 | Platform thesis | 21/21 | Vision |

**v4.0 adds 4 new capabilities:**
- #17: Multi-source context ingestion (UCL Connector pattern)
- #18: Docker deployment (partner self-service)
- #19: Live Graph Integration (production-grade state)
- #20: Cross-source query intelligence (Tab 1 evolution)

---

## SECTION 2: Architecture — UCL Connectors

### The Pattern

v3's threat_intel.py is already 80% of a connector. v4 extracts the pattern into a base class that every data source implements.

```
┌───────────────────────────────────────────────────┐
│                    UCL Layer                        │
│                                                     │
│  ┌───────────┐  ┌───────────┐  ┌──────────────┐   │
│  │ Pulsedive │  │ GreyNoise │  │ CrowdStrike  │   │
│  │ Connector │  │ Connector │  │ (mock)        │   │
│  └─────┬─────┘  └─────┬─────┘  └──────┬───────┘   │
│        │               │               │            │
│        ▼               ▼               ▼            │
│  ┌──────────────────────────────────────────────┐  │
│  │         Unified Context Graph (Neo4j)         │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────┬───────────────────────────────┘
                      ▼
            ACCP Decision Layer
       (same scoring, same loops, richer context)
```

### Connector Interface

```python
# backend/app/connectors/base.py

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime

class ConnectorResult:
    source: str              # "pulsedive_live", "greynoise_live", "crowdstrike_mock"
    indicators_ingested: int
    relationships_created: int
    enrichment_summary: List[Dict]
    timestamp: str

class HealthStatus:
    healthy: bool
    source: str
    message: str             # "OK", "Rate limited", "API key invalid"
    last_checked: str

class UCLConnector(ABC):
    name: str                # "pulsedive", "greynoise", "crowdstrike"
    source_type: str         # "threat_intel", "alert_source", "enrichment"
    
    @abstractmethod
    async def refresh(self) -> ConnectorResult:
        """Pull data from source, write to Neo4j, return summary."""
        
    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """Is the source reachable? API key valid? Rate limit OK?"""
        
    @abstractmethod
    def get_config_schema(self) -> Dict:
        """What .env vars does this connector need?"""
```

### Connector Registry

```python
# backend/app/connectors/registry.py

class ConnectorRegistry:
    _connectors: Dict[str, UCLConnector] = {}
    
    def register(self, connector: UCLConnector):
        self._connectors[connector.name] = connector
    
    def get(self, name: str) -> Optional[UCLConnector]:
        return self._connectors.get(name)
    
    def list_all(self) -> List[Dict]:
        return [{"name": c.name, "type": c.source_type} for c in self._connectors.values()]
    
    async def refresh_all(self) -> List[ConnectorResult]:
        results = []
        for connector in self._connectors.values():
            try:
                results.append(await connector.refresh())
            except Exception as e:
                results.append(ConnectorResult(source=f"{connector.name}_error", ...))
        return results
    
    async def health_check_all(self) -> List[HealthStatus]:
        return [await c.health_check() for c in self._connectors.values()]

# Global instance
registry = ConnectorRegistry()
```

---

## SECTION 3: Claude Code Rules (Apply to Every Prompt)

1. **No git commands.** Never `git commit`, `git push`, `git tag`, or `git branch`. Human handles all git operations.
2. **No debugger.** Never launch debugger, `pdb`, or interactive Python sessions.
3. **Read before write.** Always read the target file(s) completely before modifying. State what you see.
4. **One concern per prompt.** If you need to touch more than 3 files, stop and ask.
5. **Add, don't rewrite.** Find the insertion point, add new code, leave surrounding code untouched.
6. **No schema changes without explicit instruction.** Don't add Neo4j constraints, indexes, or new node types unless the prompt spec lists them.
7. **Show your work.** After making changes, show the exact lines changed (before/after). Do NOT start the dev server.
8. **Backend before frontend.** Always implement and test the endpoint before writing UI that calls it.

---

## SECTION 4: Feature Specifications

### Phase 1: UCL Connectors (Sessions 1–3)

---

#### Prompt C1 — Backend: UCL Connector Base Class + Registry

**Scope:** New directory + base class + registry + registration in main.py
**Files touched:**
- `backend/app/connectors/__init__.py` (new)
- `backend/app/connectors/base.py` (new)
- `backend/app/connectors/registry.py` (new)
- `backend/app/routers/graph.py` (modify — add registry endpoints)
- `backend/app/main.py` (register connectors at startup)

**What to build:**

1. `base.py`: Abstract base class `UCLConnector` with:
   - Properties: name, source_type, description
   - Abstract methods: refresh(), health_check(), get_config_schema()
   - Dataclasses: ConnectorResult, HealthStatus (as described in Section 2)

2. `registry.py`: ConnectorRegistry with:
   - register(), get(), list_all(), refresh_all(), health_check_all()
   - Module-level `registry` instance

3. `graph.py` (modify existing): Add two new endpoints:
   - `GET /api/graph/connectors` → lists all registered connectors with health status
   - `POST /api/graph/connectors/refresh-all` → calls registry.refresh_all(), returns combined results
   - Keep existing `POST /api/graph/threat-intel/refresh` working (backward compat)

4. `main.py`: Import registry at startup. No connectors registered yet (that's C3).

**Verification test:**
```
1. Start backend
2. curl http://localhost:8001/api/graph/connectors
   → returns {"connectors": [], "count": 0}
3. curl -X POST http://localhost:8001/api/graph/connectors/refresh-all
   → returns {"results": [], "total_sources": 0}
4. curl -X POST http://localhost:8001/api/graph/threat-intel/refresh
   → still works (backward compat) — returns Pulsedive data as before
```

---

#### Prompt C3 — Backend: Refactor Pulsedive into Connector Pattern

**Scope:** Wrap existing threat_intel.py in connector interface
**Files touched:**
- `backend/app/connectors/pulsedive.py` (new)
- `backend/app/services/threat_intel.py` (no change — used internally by connector)
- `backend/app/main.py` (register Pulsedive connector)

**What to build:**

1. `pulsedive.py`: PulsediveConnector(UCLConnector) that:
   - name = "pulsedive", source_type = "threat_intel"
   - refresh() → calls existing refresh_threat_intel() from threat_intel.py, wraps result in ConnectorResult
   - health_check() → checks if PULSEDIVE_API_KEY is set, optionally pings API with a test indicator
   - get_config_schema() → returns {"PULSEDIVE_API_KEY": {"required": True, "description": "..."}}

2. `main.py`: Import PulsediveConnector, register with registry at startup:
   ```python
   from app.connectors.pulsedive import PulsediveConnector
   from app.connectors.registry import registry
   registry.register(PulsediveConnector())
   ```

**Do NOT modify threat_intel.py.** The connector wraps it.

**Verification test:**
```
1. Start backend
2. curl http://localhost:8001/api/graph/connectors
   → returns [{"name": "pulsedive", "type": "threat_intel", "healthy": true/false}]
3. curl -X POST http://localhost:8001/api/graph/connectors/refresh-all
   → returns results with pulsedive data
4. curl -X POST http://localhost:8001/api/graph/threat-intel/refresh
   → still works (backward compat)
```

---

#### Prompt C2 — Backend: GreyNoise Connector

**Scope:** New connector + register
**Files touched:**
- `backend/app/connectors/greynoise.py` (new)
- `backend/app/main.py` (register)

**What to build:**

1. `greynoise.py`: GreyNoiseConnector(UCLConnector):
   - name = "greynoise", source_type = "enrichment"
   - Read GREYNOISE_API_KEY from os.environ
   - Curated IP list (reuse 3 IPs from Pulsedive demo IOCs + 2 new):
     ```python
     DEMO_IPS = [
         "185.220.101.34",   # Tor exit node (also in Pulsedive)
         "45.33.32.156",     # Scanning source (also in Pulsedive)
         "71.6.135.131",     # Known scanner (Shodan)
         "198.235.24.2",     # Known benign (Microsoft)
         "8.8.8.8",          # Google DNS (RIOT)
     ]
     ```
   - refresh():
     - For each IP: `GET https://api.greynoise.io/v3/community/{ip}` with header `key: {api_key}`
     - Parse: noise (bool), riot (bool), classification (benign/malicious/unknown), name, last_seen
     - Write as `:GreyNoiseEnrichment` nodes to Neo4j (MERGE on IP)
     - Create `:ENRICHED_BY` relationships to existing `:ThreatIntel` nodes with matching IPs
     - Fallback if no key or errors: hardcoded data, source="greynoise_fallback"
     - Rate limit: 0.5s between calls. Free tier = 50/week, so be conservative.
   - health_check(): Check key exists + test with 8.8.8.8 (always returns RIOT data)
   - get_config_schema(): {"GREYNOISE_API_KEY": {"required": True}}

**Verification test:**
```
1. Ensure GREYNOISE_API_KEY in .env
2. Start backend
3. curl http://localhost:8001/api/graph/connectors
   → shows both pulsedive and greynoise
4. curl -X POST http://localhost:8001/api/graph/connectors/refresh-all
   → both sources return data
5. Neo4j: MATCH (g:GreyNoiseEnrichment) RETURN g → nodes with classification data
6. Neo4j: MATCH (g:GreyNoiseEnrichment)-[:ENRICHED_BY]->(t:ThreatIntel) RETURN g,t
   → cross-source relationships for overlapping IPs
```

---

#### Prompt C4a — Backend: Multi-Source Aggregation Endpoint

**Scope:** New endpoint that aggregates across all connectors
**Files touched:**
- `backend/app/routers/graph.py` (add endpoint)

**What to build:**

`GET /api/graph/threat-intel/summary` returns a unified view:
```json
{
    "sources": [
        {"name": "pulsedive", "type": "threat_intel", "indicators": 5, "last_refreshed": "...", "status": "live"},
        {"name": "greynoise", "type": "enrichment", "indicators": 5, "last_refreshed": "...", "status": "live"}
    ],
    "total_indicators": 10,
    "cross_source_correlations": 2,
    "enrichment_coverage": "40%"
}
```

- Queries Neo4j for :ThreatIntel and :GreyNoiseEnrichment node counts
- Counts :ENRICHED_BY relationships (cross-source correlations)
- enrichment_coverage = IOCs with at least 2 sources / total IOCs

**Verification test:**
```
1. Refresh all connectors first
2. curl http://localhost:8001/api/graph/threat-intel/summary
   → shows both sources with counts and correlations
```

---

#### Prompt C4b — Frontend: Multi-Source Threat Intel Dashboard (Tab 3 upgrade)

**Scope:** Upgrade the threat intel badge to show multiple sources
**Files touched:**
- `frontend/src/lib/api.ts` (add function)
- `frontend/src/components/tabs/AlertTriageTab.tsx` (upgrade badge)

**What to build:**

Replace the single-source badge with a multi-source status row:

```
🛡️ Threat Intel: 10 indicators from 2 sources
   Pulsedive (live) · 5 indicators  |  GreyNoise (live) · 5 indicators
   2 cross-source correlations · Last refreshed: 14:23:01  [Refresh All]
```

- Call `GET /api/graph/threat-intel/summary` instead of the old single-source endpoint
- "Refresh All" calls `POST /api/graph/connectors/refresh-all`
- Each source shows its own status (live/fallback) in green/amber
- Cross-source correlations highlighted — this is the demo moment

**Verification test:**
```
1. Tab 3: multi-source badge visible
2. Shows both Pulsedive and GreyNoise with individual counts
3. Cross-source correlations count visible
4. Refresh All updates both sources
5. Decision Explainer threat_intel_enrichment factor still works
```

---

#### Prompt C5a — Backend: CrowdStrike Mock Connector

**Scope:** New connector with simulated Falcon detections
**Files touched:**
- `backend/app/connectors/crowdstrike_mock.py` (new)
- `backend/app/main.py` (register)

**What to build:**

CrowdStrikeMockConnector(UCLConnector):
- name = "crowdstrike_mock", source_type = "alert_source"
- refresh() generates 10 simulated detections matching Falcon's schema:
  ```python
  MOCK_DETECTIONS = [
      {
          "detection_id": "ldt:abc123:456",
          "severity": 4,  # CrowdStrike uses 1-5
          "tactic": "Credential Access",
          "technique": "T1110 - Brute Force",
          "hostname": "DESKTOP-JSMITH",
          "user": "john.smith",  # DELIBERATE overlap with ALERT-7823
          "timestamp": "2026-02-24T03:15:00Z",
          "disposition": "Detection",
      },
      # ... 9 more, including:
      # - 2 that overlap with Pulsedive IOC IPs (cross-source)
      # - 1 that matches a travel login pattern
      # - Mix of severities and MITRE tactics
  ]
  ```
- Writes as `:CrowdStrikeDetection` nodes to Neo4j
- Creates `:CORRELATED_WITH` relationships to `:Alert` and `:ThreatIntel` nodes where user/IP overlap
- No API call — entirely simulated
- health_check() always returns healthy (it's mock data)

**Key design choice:** Some detections deliberately overlap with existing demo data:
- john.smith → links to ALERT-7823
- IPs overlapping with Pulsedive IOCs → cross-source correlation
- This creates the "watch what happens when we cross-correlate" moment

**Verification test:**
```
1. curl -X POST http://localhost:8001/api/graph/connectors/refresh-all
   → three sources, CrowdStrike shows mock data
2. curl http://localhost:8001/api/graph/threat-intel/summary
   → 3 sources, cross-source correlations increased
3. Neo4j: MATCH (c:CrowdStrikeDetection) RETURN c → 10 nodes
4. Neo4j: MATCH (c:CrowdStrikeDetection)-[:CORRELATED_WITH]->(a:Alert) RETURN c,a
   → at least 1 correlation (john.smith)
```

---

#### Prompt C5b — Frontend: CrowdStrike Source in Multi-Source Badge

**Scope:** Add CrowdStrike to the multi-source dashboard
**Files touched:**
- `frontend/src/components/tabs/AlertTriageTab.tsx` (minor update)

**What to build:**

The multi-source badge (from C4b) should now show three sources:
```
🛡️ Threat Intel: 20 indicators from 3 sources
   Pulsedive (live) · 5  |  GreyNoise (live) · 5  |  CrowdStrike (mock) · 10
   4 cross-source correlations  [Refresh All]
```

CrowdStrike labeled as "(mock)" in a blue/neutral color (not green like live sources).

If this already works from C4b (because it reads from the summary endpoint dynamically), then this prompt is just verification + possible label styling. May be a no-op.

**Verification test:**
```
1. Tab 3: badge shows 3 sources
2. CrowdStrike labeled "(mock)" in distinct color
3. Cross-source correlations reflect CrowdStrike overlaps
```

---

#### Prompt T1 — Frontend: Cross-Source Query Examples in Tab 1

**Scope:** Update Tab 1 with cross-source query examples
**Files touched:**
- `frontend/src/components/tabs/SOCAnalyticsTab.tsx` (modify query list)

**What to build:**

Find the list of example queries in Tab 1 (likely hardcoded in the component). Replace or augment with cross-source queries:

```
"Cross-reference CrowdStrike detections with travel calendar anomalies"
"Which Pulsedive high-risk indicators appear in CrowdStrike alerts?"
"Show me IOCs enriched by both Pulsedive and GreyNoise"
"Which Falcon alerts would our scoring matrix classify as false positives?"
"Show threat intel coverage — which alerts have no external enrichment?"
```

These still hit the existing Neo4j graph — the graph now has richer data from connectors. No backend change needed. Results should include source attribution ("Source: CrowdStrike mock | Pulsedive live").

**Verification test:**
```
1. Tab 1: new cross-source queries visible in example list
2. Click a query → results show with source attribution
3. Existing queries still work
```

---

### Phase 2: Docker for Partners (Sessions 4–5)

---

#### Prompt D1 — Dockerfile.backend

**Scope:** New file
**Files touched:** `Dockerfile.backend` (new, project root)

**What to build:**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

Add a `.dockerignore` if not present: `__pycache__`, `.env`, `*.pyc`, `node_modules`.

**Verification test:**
```
1. docker build -f Dockerfile.backend -t soc-copilot-backend .
2. VERIFY: builds without errors
3. Do NOT run yet — docker-compose handles that
```

---

#### Prompt D2 — Dockerfile.frontend

**Scope:** New file
**Files touched:** `Dockerfile.frontend` (new, project root)

**What to build:**

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY frontend/package*.json .
RUN npm ci
COPY frontend/ .
EXPOSE 5174
CMD ["npx", "vite", "--host", "0.0.0.0", "--port", "5174"]
```

For production, consider a build step + nginx serve. For demo purposes, dev server is fine.

**Verification test:**
```
1. docker build -f Dockerfile.frontend -t soc-copilot-frontend .
2. VERIFY: builds without errors
```

---

#### Prompt D3 — docker-compose.yml + .env.docker

**Scope:** New files
**Files touched:** `docker-compose.yml` (new), `.env.docker` (new)

**What to build:**

```yaml
version: '3.8'
services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "8001:8001"
    env_file:
      - .env.docker
    depends_on:
      - neo4j-check
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/api/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "5174:5174"
    depends_on:
      backend:
        condition: service_healthy

  neo4j-check:
    image: curlimages/curl
    command: ["sh", "-c", "echo 'Neo4j Aura is external — no local container needed'"]
```

`.env.docker`:
```
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
PULSEDIVE_API_KEY=your-key
GREYNOISE_API_KEY=your-key
```

Note: Neo4j Aura is a cloud service — no local Neo4j container. Partners provide their own Aura credentials.

**Verification test:**
```
1. Copy .env to .env.docker with real credentials
2. docker-compose up --build
3. Wait 30 seconds
4. Open http://localhost:5174 → demo loads
5. All 4 tabs work
```

---

#### Prompt D4 — Neo4j Seed Script

**Scope:** New file
**Files touched:** `scripts/seed_neo4j_docker.py` (new)

**What to build:**

A script that seeds a fresh Neo4j Aura instance with the demo data:
- Alert nodes (ALERT-7823, ALERT-7824, etc.)
- User nodes (John Smith, etc.)
- Pattern nodes
- Policy nodes
- Any baseline relationships

Reads from `.env.docker` for credentials. Idempotent (MERGE, not CREATE).

**Verification test:**
```
1. Point to a clean Neo4j Aura instance
2. python scripts/seed_neo4j_docker.py
3. VERIFY: nodes created
4. Start demo → all tabs work with seeded data
```

---

#### Prompt D5 — PARTNER_README.md + Health Check

**Scope:** New files
**Files touched:** `PARTNER_README.md` (new), `backend/app/routers/health.py` (new), `backend/app/main.py` (register)

**What to build:**

1. `health.py`: Simple health check endpoint:
   - `GET /api/health` → `{"status": "healthy", "neo4j": "connected"|"disconnected", "version": "3.0"}`

2. `PARTNER_README.md`: Partner-facing quickstart:
   ```
   # SOC Copilot Demo — Partner Setup
   
   ## Prerequisites
   - Docker Desktop
   - Neo4j Aura free account (https://neo4j.com/cloud/aura-free/)
   
   ## Setup (5 minutes)
   1. Clone this repo
   2. Copy .env.docker.example to .env.docker, fill in your Neo4j credentials
   3. Run: python scripts/seed_neo4j_docker.py
   4. Run: docker-compose up
   5. Open http://localhost:5174
   
   ## Demo Flow
   - Tab 3 → Tab 2 → Tab 4 (recommended order)
   - Click "Refresh" on the Threat Intel badge to load live data
   ```

**Verification test:**
```
1. curl http://localhost:8001/api/health → status=healthy
2. Follow PARTNER_README from scratch → demo works
```

---

### Phase 3: Live Graph Integration (Sessions 6–7)

---

#### Prompt LG1 — Backend: Feedback State → Neo4j

**Scope:** Write feedback outcomes to Neo4j instead of only in-memory
**Files touched:** `backend/app/services/feedback.py` (modify)

**What to build:**

When process_outcome() is called, IN ADDITION to the existing in-memory update:
- Write a `:DecisionOutcome` node to Neo4j with: alert_id, outcome, delta, timestamp, pattern_id
- Create `:RESULTED_IN` relationship from `:Alert` to `:DecisionOutcome`
- Update `:Pattern` node's confidence score in Neo4j (MERGE + SET)

Keep in-memory state working as before (backward compat). Neo4j writes are additive.

**Verification test:**
```
1. Process alert + outcome
2. Neo4j: MATCH (d:DecisionOutcome) RETURN d → new node
3. Existing in-memory state still works
4. All tabs still function
```

---

#### Prompt LG2 — Backend: Feedback Reads from Neo4j

**Scope:** Read pattern confidence from Neo4j instead of in-memory dicts
**Files touched:** `backend/app/services/feedback.py` (modify)

**What to build:**

get_reward_summary() and get_current_pattern_state() should read from Neo4j :DecisionOutcome and :Pattern nodes. Fall back to in-memory state if Neo4j read fails.

**Verification test:**
```
1. Restart backend (clears in-memory state)
2. curl http://localhost:8001/api/rl/reward-summary
   → returns data from Neo4j (persisted from previous session)
3. Tab 2 Loop 3 panel shows persisted data
```

---

#### Prompt LG3 — Backend: Policy State → Neo4j

**Scope:** Write policy resolutions to Neo4j
**Files touched:** `backend/app/services/policy.py` (modify)

**What to build:**

When a policy conflict is detected and resolved:
- Write `:PolicyResolution` node with: alert_id, winning_policy, losing_policy, action_adjusted, audit_id, timestamp
- Create relationships to the relevant `:Alert` and `:Policy` nodes

**Verification test:**
```
1. Analyze ALERT-7823 (triggers policy conflict)
2. Neo4j: MATCH (p:PolicyResolution) RETURN p → resolution node exists
```

---

#### Prompt LG4 — Backend: Triage State → Neo4j

**Scope:** Write triage decisions to Neo4j
**Files touched:** `backend/app/services/triage.py` (modify)

**What to build:**

After analysis completes:
- Write `:ProcessedAlert` node with analysis results
- Create `:ANALYZED_BY` relationship from `:Alert`
- Write decision factors as properties on the node

**Verification test:**
```
1. Analyze an alert
2. Neo4j: MATCH (p:ProcessedAlert) RETURN p → analysis node
3. Decision factors endpoint still works
```

---

### Phase 4: Polish (Session 8)

---

#### Prompt PH1 — Backend: Query Registry + Fuzzy Matching

**Scope:** New service for Tab 1 smart queries
**Files touched:** `backend/app/services/query_hub.py` (new), `backend/app/routers/soc.py` (add endpoint)

**What to build:**

- Registry of ~20 canned queries with categories (security, threat_intel, cross_source, compliance)
- `GET /api/soc/queries?q={partial}` → fuzzy match using difflib.get_close_matches or similar
- Returns top 5 matching queries with descriptions

**Verification test:**
```
1. curl http://localhost:8001/api/soc/queries?q=crowd
   → returns queries mentioning CrowdStrike
```

---

#### Prompt PH2 — Frontend: "Did You Mean?" in Tab 1

**Scope:** Add suggestion dropdown to Tab 1
**Files touched:** `frontend/src/components/tabs/SOCAnalyticsTab.tsx`, `frontend/src/lib/api.ts`

**What to build:**

As the user types in Tab 1's query box, debounce-call the fuzzy match endpoint and show a dropdown of suggestions below the input. Clicking a suggestion fills the input and executes.

**Verification test:**
```
1. Tab 1: type "crowd" → dropdown shows CrowdStrike-related queries
2. Click suggestion → query executes
3. Full manual typing still works
```

---

#### Prompt FC1 — Frontend: Four Clocks Diagnostic Display

**Scope:** Add widget to Tab 4
**Files touched:** `frontend/src/components/tabs/CompoundingTab.tsx`

**What to build:**

Small panel showing the four clock rates from the CI blog:
- State Clock: graph nodes / sec
- Event Clock: alerts processed / hour
- Decision Clock: decisions / hour
- Insight Clock: patterns discovered / week

Static values for demo. Positioned below Evidence Ledger, above Reset button.

**Verification test:**
```
1. Tab 4: Four Clocks widget visible
2. Shows 4 rates with labels
3. Other Tab 4 sections unaffected
```

---

## SECTION 5: Build Sequence

```
PRE-WORK:
  git clone gen-ai-roi-demo into gen-ai-roi-demo-v4
  git checkout -b feature/v4.0-enhancements

PHASE 1: Connectors (Sessions 1–3, 8 prompts)
  Session 1: C1 (base class + registry) + C3 (Pulsedive refactor)
  Session 2: C2 (GreyNoise) + C4a (aggregation endpoint) + C4b (multi-source badge)
  Session 3: C5a (CrowdStrike mock) + C5b (badge update) + T1 (Tab 1 queries)
  TEST: All verification procedures pass
  COMMIT + TAG: v4.0-connectors

PHASE 2: Docker (Sessions 4–5, 5 prompts)
  Session 4: D1 (backend Dockerfile) + D2 (frontend Dockerfile)
  Session 5: D3 (compose) + D4 (seed) + D5 (README + health)
  TEST: docker-compose up works end-to-end
  COMMIT + TAG: v4.0-docker

PHASE 3: Live Graph (Sessions 6–7, 4 prompts)
  Session 6: LG1 (feedback writes) + LG2 (feedback reads)
  Session 7: LG3 (policy writes) + LG4 (triage writes)
  TEST: Restart backend, data persists
  COMMIT + TAG: v4.0-live-graph

PHASE 4: Polish (Session 8, 3 prompts)
  Session 8: PH1 (query registry) + PH2 (did you mean) + FC1 (four clocks)
  TEST: Tab 1 suggestions work, Tab 4 clocks visible
  COMMIT

MERGE + TAG:
  git checkout main
  git merge feature/v4.0-enhancements
  git tag -a v4.0 -m "v4.0: Your tools, our decisions."
  git push origin main v4.0
```

**Total: 20 prompts across 8 sessions.**

---

## SECTION 6: Demo-Blog Alignment (Post-v4)

| Blog Claim | v3 Reality | v4 Reality |
|---|---|---|
| "Three cross-layer loops" | ✅ Demo shows three | ✅ Same |
| "Four dependency-ordered layers" | ✅ Four Layers strip | ✅ UCL now has real connectors |
| "Cross-domain discovery" | Partial (Pulsedive only) | **✅ Three sources, cross-correlations visible** |
| "Living graph" | Partial (in-memory state) | **✅ Neo4j reads/writes persist** |
| "$127K/quarter cost avoided" | ✅ Banner | ✅ Same |
| "Audit trail / compliance" | ✅ Evidence Ledger | ✅ Same |

---

## SECTION 7: Key Soundbites (v4-specific)

### For CISOs

| Feature | Soundbite |
|---|---|
| Multi-source | "Pulsedive, GreyNoise, and CrowdStrike. Three sources. One graph. Each source makes every decision richer." |
| Stack positioning | "We're not replacing CrowdStrike. We're the decision layer on top. Your tools, our decisions." |
| Cross-correlation | "That IP appeared in both Pulsedive and GreyNoise with different classifications. The system reconciles them automatically." |
| Docker | "Clone the repo. Docker-compose up. Demo in 60 seconds." |

### For VCs

| Feature | Soundbite |
|---|---|
| Connector pattern | "One interface, N sources. Each new connector makes the platform smarter without touching the decision layer." |
| Platform proof | "Three different data source types — threat intel, enrichment, alert source — all feeding one graph through the same pattern." |
| ACCP progress | "Eighteen of twenty-one capabilities. Docker-deployable. Partner-ready." |

---

## SECTION 8: API Keys

| Source | Status | Notes |
|---|---|---|
| Pulsedive | ✅ Configured | Free community tier |
| GreyNoise | ✅ Configured | Free community tier, 50 lookups/week |
| CrowdStrike | N/A | Mock connector, no key needed |
| CISA KEV | No key needed | Free public API (optional v4+ enhancement) |

---

## SECTION 9: Risk and Open Questions

| Question | Impact | When to Resolve |
|---|---|---|
| GreyNoise 50/week rate limit for repeated demos | May need aggressive caching or fallback | Test during C2 build |
| CrowdStrike Falcon public schema accuracy | Mock credibility | Research before C5 |
| Live Graph migration breaks existing flows | Regression risk | Careful testing in LG1-LG4 |
| Docker + Neo4j Aura — partner isolation | Each partner needs own Aura instance | Document in PARTNER_README |
| Tab 1 query results with multi-source data | May need result formatting update | Test after C4b |

---

## Appendix: Version History

| Version | Date | Changes |
|---|---|---|
| **1.0** | **Feb 24, 2026** | **Initial v4 design document. 20 prompts, 8 sessions. UCL Connector pattern, GreyNoise + CrowdStrike mock, Docker, Live Graph, Prompt Hub, Four Clocks. Full prompt-level specs based on v3 implementation patterns.** |

---

*SOC Copilot Demo — v4.0 Design Document v1 | February 24, 2026*
*Theme: "Your tools, our decisions." | 20 prompts, 8 sessions | Prerequisite: v3.0 tagged*
