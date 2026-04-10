# DEPENDENCIES.md — External dependency inventory

## Python Backend

| Package | Purpose | Pinned Version | Notes |
|---------|---------|----------------|-------|
| fastapi | Web framework | >=0.100 | ASGI, async |
| uvicorn | ASGI server | >=0.20 | Production runner |
| pydantic | Data validation | >=2.0 | V2 migration in progress |
| python-dotenv | .env loading | >=1.0 | Loaded in neo4j.py + main.py |
| neo4j | Neo4j async driver | >=5.0 | Lazy-imported only when GRAPH_BACKEND=neo4j |
| psycopg | PostgreSQL sync driver | >=3.1 | AGE backend, sync + to_thread |
| numpy | Tensor operations | >=1.24 | Centroid math, ProfileScorer |
| pyyaml | YAML parsing | >=6.0 | Contract validation |

## Graph Attention Engine (GAE)
| Package | Purpose | Install |
|---------|---------|---------|
| gae | Scoring, learning, factors | `pip install -e ../../graph-attention-engine` |

## CI Platform
| Package | Purpose | Install |
|---------|---------|---------|
| ci-platform[graph] | AGEClient shared graph client | `pip install -e ../ci-platform` |

## Frontend

| Package | Purpose | Notes |
|---------|---------|-------|
| react | UI framework | v18+ |
| vite | Build tool | Dev server port 5173/5174 |
| @playwright/test | E2E testing | v1.58+ |
| recharts | Charts | CompoundingTab, RuntimeEvolutionTab |

## Infrastructure

| Service | Purpose | Connection |
|---------|---------|------------|
| PostgreSQL + Apache AGE | Graph database (primary) | DATABASE_URL env var |
| Neo4j Aura | Graph database (legacy) | NEO4J_URI env var |
| Google Vertex AI | LLM narrator | GOOGLE_APPLICATION_CREDENTIALS |
