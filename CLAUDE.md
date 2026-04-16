# ⚠️ GROUNDING CONTRACT (non-negotiable)

**These rules apply to every AI coding agent working in this repo.**

1. **Docs are aspirational until proven in code.** Never treat design docs,
   specs, or planning documents as implemented. Check the actual source files.

2. **Cite file + line for every behavioral claim.** "The reset endpoint filters
   by origin" is not acceptable. "triage.py:L816 filters by origin" is.

3. **Code and tests beat docs.** If a spec says "use MERGE" but the code uses
   CREATE, the code is correct. Report the discrepancy as DRIFT.

4. **DRIFT = stop.** If code and docs/specs disagree, label it DRIFT, report it
   to the user, and do not propose fixes based on the docs. The code is the
   source of truth.

5. **Check downstream consumers before changing data formats.** Before changing
   alert ID prefixes, field names, or response shapes: grep the frontend, E2E
   tests, and contract files for the current format. List all consumers.

6. **Verify after every change.** Run the verification ladder before claiming
   anything works: grep → curl → validate_contracts.py → targeted test → full suite.

7. **No $param named parameters in AGE Cypher.** AGE does not support them.
   Use `_S()` or `serialize_for_age()` for inline values.

8. **Post-session gate.** After every Claude Code session, run `check_drift.py`
   and `query_graph4_final.py` before accepting any output.

---

## How to Think (read first, every session)

### 1. State Assumptions Before Coding
- Before implementing, state your assumptions explicitly.
- If multiple interpretations exist, present them — don't pick silently.
- NEVER silently pick a property name, field type, or API path — state it.

### 2. Minimum Code That Solves the Problem
- No features beyond what was asked. No abstractions for single-use code.
- If 200 lines could be 50, rewrite it.

### 3. Surgical Changes
- Touch only what you must. Don't "improve" adjacent code.
- Every changed line traces directly to the request.

### 4. Goal-Driven Execution
- Before starting: Step → verify: [specific check] for each step.
- "This should work" is never verification. Show the output.

### 5. Dual Representation Rule
- Before adding any constant/tensor/property: check if it exists under a
  different name first. Grep for it.

---

## Architecture

```
PostgreSQL+AGE (WSL2, port 5433)
    ↓
AGEClient (ci-platform/ci_platform/graph/age_client.py)
    ↓  single choke point — every Cypher query passes through here
neo4j.py switcher (backend/app/db/neo4j.py)
    ↓  290+ call sites in routers
FastAPI routers (backend/app/routers/*.py, port 8001)
    ↓
React frontend (frontend/, port 5173)
```

### Critical Files (read before modifying)

| File | Purpose | Modify with extreme care |
|---|---|---|
| backend/app/graph_schema.py | Graph contract, verify, seed | Hand-craft only |
| backend/app/services/state_manager.py | Data protection gateway | All destructive Cypher here |
| backend/app/routers/triage.py | Alert queue, analyze, execute | 195 call sites |
| backend/app/routers/soc.py | 50+ SOC endpoints | 388 call sites, complexity risk |
| backend/conftest.py | Pre/post test safety net | Blocks test suite if data wiped |

### Data Origins (two classes, different protection)

| Origin | Meaning | Protected by StateManager | Reset behavior |
|---|---|---|---|
| `zero_day_synthetic` | Training data (4,860 decisions, 540 alerts) | YES — pre-check blocks deletion | Survives all resets |
| `zero_day_demo` | Demo alerts (30 pending alerts) | NO — ephemeral | Reset to pending by POST /api/alerts/reset |
| `NULL` (no origin) | Session data from user actions | NO | Cleared on soft/hard reset |

### Alert ID Convention

| Prefix | Source | Appears in queue | E2E regex |
|---|---|---|---|
| `ALERT-` | Demo alerts (v5 JSON demo_alerts) | YES (status=pending) | `/^(SIM-\|ALERT-)/` |
| `SYN-` | Training alerts (v5 JSON alerts) | NO (status=decided) | Not matched |
| `SIM-` | Simulation engine (Tab 4) | YES when sim runs | `/SIM-/` |

**E2E tests match these exact prefixes.** Changing them breaks 28+ tests.

---

## AGE Is Not Neo4j — Why Constraints Exist

AGE wraps Cypher in `SELECT * FROM cypher('graph', $$ CYPHER_HERE $$) AS (col agtype)`.
This PostgreSQL function layer means several Neo4j features don't work:

### 1. No MERGE
AGE does not implement MERGE. Queries containing MERGE either error or silently
produce no result. Use CREATE (for new nodes) or MATCH + SET (for updates).
AGEClient._check_safe_cypher() rejects MERGE with ValueError.

### 2. No $param Named Parameters
AGE's Cypher parser doesn't support `$param`. AGEClient does naive string
substitution in _sync_execute(), but `$analyst` collides with `$analyst_action`
(shorter match replaces inside longer). Use `_S()` or `serialize_for_age()` to
build inline values instead.

### 3. SET n = {props} Wipes All Properties
`SET d = {category: 'x'}` destroys every other property on the node.
Use `SET d.category = 'x'` (single property) or `SET d += {a: 1, b: 2}` (merge).
AGEClient rejects the destructive form with ValueError.

### 4. No date() Function
Use epoch integers (milliseconds). Store as `timestamp_epoch: 1741046400000`.

### 5. No Array Properties
Lists must be serialized as JSON strings: `_S([1,2,3])` → `'[1,2,3]'`.

### 6. Column Alias `count` Is Reserved
Use `cnt` instead: `RETURN count(n) AS cnt` not `RETURN count(n) AS count`.

### 7. Atomic Decision Creation
```cypher
-- CORRECT: Decision + edge in one query
MATCH (a:Alert {alert_id: 'ALERT-001'})
CREATE (d:Decision {decision_id: 'D-001', ...})-[:DECIDED_ON]->(a)

-- WRONG: Two separate queries (orphan risk)
CREATE (d:Decision {decision_id: 'D-001', ...})
-- then later:
MATCH (d:Decision), (a:Alert) CREATE (d)-[:DECIDED_ON]->(a)
```

---

## Decision Data Protection

Training data (`origin = 'zero_day_synthetic'`, 4,860 decisions) must survive
ALL resets. Five enforcement layers:

| Layer | Mechanism | File |
|---|---|---|
| 1 | StateManager._verify_deletion_safety() pre-check | state_manager.py |
| 2 | seed_neo4j.py RuntimeError guard on AGE | seed_neo4j.py (both copies) |
| 3 | metrics.py demo/seed + demo/reseed blocked | routers/metrics.py |
| 4 | Static analysis scans for destructive Cypher | test_no_destructive_decision_queries.py |
| 5 | conftest.py pytest.exit if < 3000 decisions | conftest.py |

**ALLOWED_FILES for destructive Decision Cypher:** `state_manager.py`, `graph_schema.py`.
Do NOT add files to this list — route through StateManager instead.

---

## Rules
- Do NOT use git directly. User handles all git operations.
- Do NOT start the debugger. Log-based debugging only.
- Read before write. One concern per prompt.
- Import from gae library: `from gae.scoring import score_alert`
- Factor Cypher queries MUST traverse relationships, not read properties.
- Every graph mutation (decision, outcome) MUST emit events.
- asyncio.run() not asyncio.get_event_loop() (broken on Windows Python 3.11+).

## GAE Library
Installed via: `pip install -e ../../graph-attention-engine`

Key imports:
```python
from gae.scoring import score_alert, ScoringResult
from gae.learning import LearningState, WeightUpdate
from gae.factors import FactorComputer, assemble_factor_vector
from gae.contracts import SchemaContract
from gae.store import save_state, load_state
from gae.convergence import get_convergence_metrics
```

## Ports (from root .env — never hardcode)
- Backend: 8001
- Frontend: 5173
- AGE (PostgreSQL): 5433

## Commands
```bash
# Start AGE (after reboot)
Start-AGE

# Backend
cd backend
uvicorn app.main:app --port 8001 --reload

# Frontend
cd frontend
npx vite --port 5173

# Seed graph (replaces old seed_neo4j.py)
cd backend
python -m app.graph_schema seed --clean

# Seed ShadowDecisions (separate source)
python support/setup/seed_shadow_decisions.py

# Verify
python -m app.graph_schema verify
python scripts/validate_contracts.py --port 8001
python check_drift.py
python query_graph4_final.py
```

## Verification Ladder (never skip levels)
```
grep (0s) → curl (2s) → validate_contracts.py (5s) → targeted Playwright (30s) → full Playwright (10m)
```

### Boundary Rules
- **Boundary 1 (AGE→Python):** AGEClient._normalize_value handles all type
  conversion. No consumer calls json.loads() on AGEClient results.
- **Boundary 2 (Python→API):** Every frontend-consumed endpoint has a Pydantic
  response_model. List fields are list[X], never Optional.
- **Boundary 3 (API→React):** Never call .map() on API data without
  ensureArray() from src/lib/guards.ts. Use safeKey() for React keys.
- **F12 Console rule:** When frontend crashes, open DevTools F12 → Console.
  Read the JS error. Never fix backend to resolve a frontend crash without
  seeing the JS error first.

### No Silent Failure on Displayed Metrics
- If a try/except computes a NUMBER shown in the UI: the except block
  must set a flag (estimated=True, source="fallback") — never bare pass.
- If a try/except computes OPTIONAL enrichment: bare pass is acceptable.
- NEVER hardcode a number that looks like a computed metric without a comment.
