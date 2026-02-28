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
