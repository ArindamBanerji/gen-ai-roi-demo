## How to Think (read first, every session)

### 1. State Assumptions Before Coding
- Before implementing, state your assumptions explicitly
- If multiple interpretations exist, present them — don't pick silently
- NEVER silently pick a property name, field type, or API path — state it

Example of WRONG: "I'll use {id: $val} in the Cypher query"
Example of CORRECT: "Assuming property 'id'. Verifying: grep shows 'alert_id'. Using that."

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
- Before adding any constant/tensor/property: check if it exists under a different name.
- Grep: get_actions(), SCORER_ACTIONS, SOC_PROFILE_CENTROIDS, alert_id, decision_id

# CLAUDE.md — SOC Copilot

## Repository
gen-ai-roi-demo-v4 — SOC domain copilot (proprietary).
Built on top of graph-attention-engine (pip-installed).

## Rules
- Do NOT use git directly. I handle all git operations.
- Do NOT start the debugger. Log-based debugging only.
- Read before write. One concern per prompt.
- Import from gae library: `from gae.scoring import score_alert`
- Factor Cypher queries MUST traverse relationships, not read properties (P10).
- Every graph mutation (decision, outcome) MUST emit events.
- f(t) stored in graph (Decision node), not in-memory cache (R4).
- No GAE math in copilot — use gae.scoring, gae.learning, gae.factors.

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

## Ports
- Backend: 8000
- Frontend: 5174

## Commands
```bash
# Backend
cd backend
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npx vite --port 5174

# Seed Neo4j
python backend/seed_neo4j.py
```

## Design Reference
- SOC copilot spec: docs/soc_copilot_design_v1.md
- GAE spec: ../graph-attention-engine/docs/gae_design_v5.md

### Boundary Rules
- **Boundary 1 (AGE→Python):** AGEClient._normalize_value handles all type conversion. No consumer calls json.loads() on AGEClient results.
- **Boundary 2 (Python→API):** Every frontend-consumed endpoint has a Pydantic response_model. list fields are list[X], never Optional.
- **Boundary 3 (API→React):** Never call .map() on API data without ensureArray() from src/lib/guards.ts. Use safeKey() for React keys.
- **F12 Console rule:** When frontend crashes, open DevTools F12 → Console. Read the JS error. Never fix backend to resolve a frontend crash without seeing the JS error first.
- **Graph schema:** Every Decision node MUST have a DECIDED_ON edge. Edgeless = orphan = delete.

### No Silent Failure on Displayed Metrics
- If a try/except computes a NUMBER shown in the UI: the except block
  must set a flag (estimated=True, source="fallback") — never bare pass
- If a try/except computes OPTIONAL enrichment: bare pass is acceptable
- NEVER hardcode a number that looks like a computed metric (0.89, 23, 127)
  without a comment explaining why it's a constant and not computed
- The test: if the graph is empty, does the UI show zeros or plausible-looking
  fake numbers? If fake numbers: it's a mockup, not a fallback.

### AGE Is Not Neo4j — Three Critical Differences

1. **SET n = {props} WIPES all other properties**
   - NEVER: `SET d = {category: 'x'}` — destroys every other property
   - ALWAYS: `SET d.category = 'x'` — preserves all other properties
   - SAFE for bulk: `SET d += {a: 1, b: 2}` — merges, preserves existing
   - AGEClient rejects the destructive form with ValueError

2. **Concurrent writes to the same node fail**
   - "Entity failed to be updated: 3" = PostgreSQL row lock conflict
   - AGEClient retries with jitter (3 attempts, 100-250ms backoff)
   - Avoid concurrent writes to the same node when possible

3. **Decision nodes must be created atomically with their edge**
   - ALWAYS: `MATCH (a:Alert) CREATE (d:Decision {...})-[:DECIDED_ON]->(a)`
   - NEVER: CREATE Decision as one query, then edge as a second
   - If MATCH finds no Alert, no Decision is created (proven atomic)

### Decision Data Protection — Four Invariants

Zero-day training data (`origin = 'zero_day_synthetic'`) must survive ALL resets.
- `origin = 'zero_day_synthetic'` → persistent training data (4,860 nodes from seed_zero_day.py)
- `origin IS NULL` → session/demo data (safe to clear/delete on reset)

**Rule:** All destructive Cypher on Decision nodes routes through `StateManager` only.
- `soft_reset()` → `clear_session_decisions()` — REMOVE correct/outcome, training data kept
- `hard_reset()` → `delete_session_decisions()` — DETACH DELETE, training data kept
- `PERSISTENT_FILTER = "WHERE d.origin IS NULL OR d.origin <> 'zero_day_synthetic'"`

**Enforcement (build-time):** `tests/test_no_destructive_decision_queries.py`
- Scans all `app/**/*.py` for `MATCH (:Decision)...DETACH DELETE` / `REMOVE d.correct` / `REMOVE d.outcome`
- Only `app/services/state_manager.py` is in the allow-list
- Do NOT add files to the allow-list — fix violations by routing through StateManager

**Do NOT:**
- Write `MATCH (d:Decision)...DETACH DELETE` anywhere outside state_manager.py
- Write `MATCH (d:Decision)...REMOVE d.correct` anywhere outside state_manager.py
- Leave `DETACH DELETE` in commented-out code — the static analysis regex uses re.DOTALL and will fire
