# Decision Data Protection — Investigation & Code Review Request
**Date:** April 14, 2026 · **Status:** BROKEN — graph is empty, needs structural fix
**Audience:** Claude Code, Roadmap Session, Codex — for independent code review

---

## 1. Executive Summary

Zero-day training data (4,860 Decision nodes in Apache AGE/PostgreSQL) has been wiped **5 times** across 3 days of development by different code paths. Each wipe requires ~10 minutes of manual backfill. A 4-layer protection architecture was implemented but failed because the filter referenced the wrong field name (`d.source` instead of `d.origin`). After fixing the field name, a manual stress test of `POST /api/admin/reset mode=hard` deleted the entire graph (all nodes, all alerts, everything). The graph is currently empty.

**What we need:** A thorough code review of `state_manager.py`, `admin.py`, `simulation.py`, and the re-seed path to understand every destructive operation, fix them all at once, and create a stress test that prevents regression.

---

## 2. Repository Structure

```
gen-ai-roi-demo-v4-v50/          (main repo — SOC Copilot)
  backend/
    app/
      main.py                    # FastAPI app, startup_event()
      db/neo4j.py                # Graph client switcher (AGE/Neo4j)
      routers/
        admin.py                 # POST /api/admin/reset (soft/hard)
        simulation.py            # POST /api/simulation/start
        triage.py                # POST /api/alerts/reset, /api/alert/analyze
        soc.py                   # Tab endpoints (290+ neo4j_client calls)
        metrics.py               # POST /api/demo/reset-all, /api/demo/reseed
      services/
        state_manager.py         # StateManager — CENTRAL reset orchestrator
        gae_state.py             # Learning state (W matrix, ProfileScorer)
        audit.py                 # Hash chain audit trail (was framework/audit.py)
      models/responses.py        # Pydantic response models
    tests/
      test_no_destructive_decision_queries.py  # Layer 3 static analysis
      conftest.py                # Layer 5 post-test safety net
    support/setup/
      seed_zero_day.py           # Creates 4,860 Decision + 540 Alert nodes
      bootstrap_learning_loop.py # Sets correct/outcome on existing nodes
  contracts/
    api_contracts.yaml           # 69 endpoint contracts (admin/reset removed)
  scripts/
    validate_contracts.py        # Hits all contracted endpoints

ci-platform/
  ci_platform/graph/
    age_client.py                # AGEClient — sync psycopg + asyncio.to_thread()
```

---

## 3. Data Architecture

### Node Types in AGE (PostgreSQL graph)

```
Alert nodes:       ~540 (seeded by seed_zero_day.py + bootstrap scripts)
Decision nodes:    ~9,346 (when healthy)
  - 4,860 with origin='zero_day_synthetic'  (persistent training data)
  - ~4,486 with origin=NULL                 (session/demo decisions)
ThreatIndicator:   ~5
ShadowDecision:    ~1,500
Campaign, AttackPattern, etc.
```

### Critical Fields on Decision Nodes

| Field | Set By | Purpose |
|---|---|---|
| `origin` | seed_zero_day.py line 138 | `'zero_day_synthetic'` = persistent training data |
| `correct` | bootstrap_learning_loop.py | `true`/`false` — used for accuracy metrics |
| `outcome` | bootstrap_learning_loop.py | `'correct'`/`'incorrect'` — used for learning |
| `decision_id` | CREATE query | UUID, unique per decision |
| `category` | CREATE query | e.g., `credential_access`, `malware_execution` |
| `confidence` | GAE scoring | 0.0-1.0 |

### The Boundary

- `origin = 'zero_day_synthetic'` → **persistent** (must survive all resets)
- `origin IS NULL` → **session/demo** (OK to clear/delete on reset)

**NOTE:** The field is `origin`, NOT `source`. seed_zero_day.py line 138 writes `origin: 'zero_day_synthetic'`. This was the root cause of the protection failure — the PERSISTENT_FILTER referenced `d.source` which doesn't exist on any node.

---

## 4. Wipe History (5 incidents)

| # | When | Trigger | Root Cause | Data Lost |
|---|---|---|---|---|
| 1 | Apr 13 | Taxonomy rename | `SET d = {category: 'x'}` wiped all other props | correct/outcome on all nodes |
| 2 | Apr 14 AM | pytest run | test_compounding_gate.py called `POST /demo/reset-all` → `hard_reset()` DETACH DELETE all | All Decision nodes |
| 3 | Apr 14 AM | Unknown | Same as #2 (second pytest run) | All Decision nodes |
| 4 | Apr 14 PM | validate_contracts.py | Hit `POST /api/admin/reset` → `soft_reset()` → `REMOVE d.correct, d.outcome` on ALL nodes | correct/outcome on all nodes |
| 5 | Apr 14 PM | Manual stress test | `POST /api/admin/reset mode=hard` → `delete_session_decisions()` with wrong field → deleted everything, then re-seed crashed | Entire graph empty (0 nodes) |

### Wipe #5 Detail (current state)

The error message from the hard reset:
```
hard_reset failed after ['learning_state', 'neo4j_delete', 'audit']:
function date does not exist
```

Three steps committed before the crash:
1. `learning_state` — W reset to priors ✓
2. `neo4j_delete` — **Decision nodes deleted** ✓ (THIS IS THE DAMAGE)
3. `audit` — chain cleared ✓
4. Re-seed — **CRASHED** (AGE doesn't have a `date()` function)

The deletion used `PERSISTENT_FILTER` with `d.source` (wrong field), so it matched ALL nodes (since `d.source IS NULL` on everything). All 9,346 decisions were deleted. Then the re-seed step crashed, leaving an empty graph.

---

## 5. What Was Built (4-Layer Architecture)

### Layer 1: StateManager Gateway (`state_manager.py`)

```python
PERSISTENT_FILTER = "WHERE d.origin IS NULL OR d.origin <> 'zero_day_synthetic'"

async def clear_session_decisions(self):
    """REMOVE correct/outcome from session decisions only."""
    # Uses PERSISTENT_FILTER — only touches origin=NULL nodes

async def delete_session_decisions(self):
    """DETACH DELETE session decisions only."""
    # Uses PERSISTENT_FILTER — only deletes origin=NULL nodes

# soft_reset() calls clear_session_decisions()
# hard_reset() calls delete_session_decisions() + re-seed
```

**Status:** Filter was wrong (`d.source`), fixed to `d.origin`. But hard_reset re-seed step crashes on AGE `date()` function, and deletion may still be wrong.

### Layer 3: Static Analysis Test (`test_no_destructive_decision_queries.py`)

Scans all `app/**/*.py` for destructive Decision Cypher outside `state_manager.py`. 1 violation found and fixed (metrics.py).

**Status:** Working. 1 test, passes.

### Layer 4: CLAUDE.md + Contract Validator

- "Decision Data Protection — Four Invariants" section in CLAUDE.md
- `POST /api/admin/reset` removed from `api_contracts.yaml` (69 contracts, was 70)

**Status:** Done.

### Layer 5: Post-Test Safety Net (`conftest.py`)

Session-scoped fixture counts zero-day nodes with `correct` field after all tests. Fails if < 3,000.

**Status:** Query was `d.source` (wrong), fixed to `d.origin`. Untested since fix.

---

## 6. Known Code Paths That Can Destroy Data

| Code Path | What It Does | Currently Protected? |
|---|---|---|
| `StateManager.soft_reset()` | REMOVE correct/outcome | ✅ Uses PERSISTENT_FILTER (after fix) |
| `StateManager.hard_reset()` | DETACH DELETE + re-seed | ❓ Deletion uses filter, but re-seed crashes |
| `POST /api/admin/reset` | Calls soft_reset or hard_reset | ❓ Depends on StateManager |
| `POST /api/simulation/start` | Calls soft_reset before sim | ❓ Depends on StateManager |
| `POST /api/alerts/reset` | Resets alert statuses only | ✅ Does not touch Decision nodes |
| `POST /api/demo/reset-all` | May call hard_reset | ❓ Unknown current state |
| `POST /api/demo/reseed` | May delete+recreate | ❓ Unknown current state |
| `validate_contracts.py` | Hits all endpoints | ✅ admin/reset removed from yaml |
| `bootstrap_learning_loop.py` | SET correct/outcome | ✅ Only sets, doesn't delete |
| `seed_zero_day.py` | CREATE nodes with origin | ✅ Only creates |
| `AGEClient SET n = {}` | Wipes all properties | ✅ Rejected with ValueError |

---

## 7. Questions for Code Review

### Q1: What does `hard_reset()` actually do right now?

Need to read the full current code of `state_manager.py` lines 126-211. Specifically:
- What query deletes Decision nodes?
- Does it also delete Alert nodes?
- What does the re-seed step do? Why does it call `date()` (which doesn't exist in AGE)?
- Is there a separate re-seed script/function it calls?

### Q2: What does `POST /api/demo/reset-all` do?

Is it wired to `StateManager.hard_reset()`? Or does it have its own deletion logic in `metrics.py`?

### Q3: Does `simulation.py` call `soft_reset()` correctly?

Line ~179 in simulation.py. Does it go through StateManager or run its own Cypher?

### Q4: What creates the `date()` crash?

The re-seed step in hard_reset uses a `date()` function that doesn't exist in AGE (PostgreSQL). This means hard_reset has NEVER worked correctly on AGE — it always crashes after deletion, leaving an empty graph.

### Q5: Should hard_reset delete Alert nodes?

After wipe #5, `POST /api/alerts/reset` returned `reset_count=0` — suggesting all Alert nodes were also deleted. Does `delete_session_decisions()` have a query that deletes Alerts too?

### Q6: Is the PERSISTENT_FILTER correct now?

Current filter: `WHERE d.origin IS NULL OR d.origin <> 'zero_day_synthetic'`

Verification shows 4,860 nodes have `origin='zero_day_synthetic'`. After E2E tests (which call soft_reset via simulation), check_origin.py confirmed 4,860 zero-day nodes survived. But the correct/outcome fields on session nodes (origin=NULL) were correctly cleared — this is expected behavior.

### Q7: What is the re-seed path?

After hard_reset deletes session decisions, what re-seeds the graph? Is it a function call, a script, or inline Cypher? Does it create Alerts? Decisions? Both?

---

## 8. Files to Read (Priority Order)

1. `backend/app/services/state_manager.py` — **THE** file. Read every line.
2. `backend/app/routers/admin.py` — POST /api/admin/reset handler
3. `backend/app/routers/simulation.py` — specifically the soft_reset call (~line 179)
4. `backend/app/routers/metrics.py` — POST /api/demo/reset-all handler
5. `backend/support/setup/seed_zero_day.py` — how origin field gets set (line 138)
6. `backend/app/routers/triage.py` — POST /api/alerts/reset handler
7. `backend/tests/conftest.py` — Layer 5 safety net fixture
8. `backend/tests/test_no_destructive_decision_queries.py` — Layer 3 static analysis

---

## 9. Current State

```
Total Decision nodes: 0
Total Alert nodes: 0 (probably — reset_count=0 from alerts/reset)
Graph: EMPTY
```

Recovery requires:
1. Fix the hard_reset re-seed crash (date() function)
2. Re-run seed_zero_day.py to recreate alerts + decisions
3. Re-run bootstrap_learning_loop.py to set correct/outcome
4. Verify with check_origin.py

---

## 10. What We Want From the Review

1. **Read all 8 files** listed in §8. Map every destructive query.
2. **Identify the date() crash** — where does it come from? Fix or remove.
3. **Verify PERSISTENT_FILTER** is applied in every destructive path.
4. **Answer all 7 questions** in §7 with code references.
5. **Propose a fix** for hard_reset that:
   - Preserves origin='zero_day_synthetic' nodes
   - Does NOT crash on AGE (no date() or other Neo4j-only functions)
   - Re-seeds session data correctly (or skips re-seed and lets the graph stay clean)
   - Preserves Alert nodes always (never delete Alerts)
6. **Write the stress test** (`test_decision_data_protection_stress.py`) that exercises every vector from §6 and verifies zero-day data survives.

---

## 11. Environment

| Component | Host | Port |
|---|---|---|
| FastAPI backend | localhost | 8001 |
| Vite frontend | localhost | 5173 |
| PostgreSQL + AGE (WSL2) | localhost | 5433 |

**Graph DB:** Apache AGE (PostgreSQL extension), NOT Neo4j.
**AGE limitations:**
- No `date()` function (use epoch integers)
- No `ON CREATE SET` / `ON MATCH SET` (use MERGE + SET)
- `SET n = {}` wipes all properties (AGEClient rejects this)
- No `NOT (pattern)` — use `NOT EXISTS((pattern))`
- `'count'` is reserved — use `cnt` as alias

**Recovery commands:**
```powershell
cd $env:CLAUDE_SOC
python backend/support/setup/seed_zero_day.py        # Creates 540 alerts + 4860 decisions
python backend/support/setup/seed_zero_day.py --backfill  # Sets correct/outcome from JSON
python backend/support/setup/bootstrap_learning_loop.py --live  # Sets correct/outcome on remaining
python check_state.py                                 # Gate: correct >= 3000
python check_origin.py                                # Gate: zero_day_synthetic = 4860
```

---

## 12. Standing Rules

1. No git from Claude Code — user handles all git
2. `origin` field (NOT `source`) is the data class boundary
3. `origin = 'zero_day_synthetic'` = persistent (survives resets)
4. `origin IS NULL` = session/demo (cleared by resets)
5. No `SET n = {}` — AGEClient rejects with ValueError
6. Decision nodes must be created atomically with DECIDED_ON edge
7. No test may call `demo/reset-all`, `demo/reseed`, or `demo/seed`
8. All destructive Decision Cypher must go through StateManager
9. `test_no_destructive_decision_queries.py` enforces rule 8 at build time

---

*Document version: v1 · April 14, 2026*
*For use by: Claude Code, Roadmap Session, Codex*
*This document is self-contained — no external context required*
