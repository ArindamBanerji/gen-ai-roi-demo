"""
SOC Copilot Demo - FastAPI Backend
Main application entry point with CORS and router registration.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables from project root
load_dotenv(dotenv_path="../.env")

app = FastAPI(
    title="SOC Copilot Demo API",
    description="AI-augmented Security Operations Center with Runtime Evolution",
    version="1.0.0",
)

# CORS configuration (allow all for demo/ngrok)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for demo purposes
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Health check endpoint
@app.get("/")
async def root():
    return {
        "service": "SOC Copilot Demo",
        "status": "operational",
        "version": "1.0.0"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

# Router imports
from app.routers import evolution, triage, soc, metrics, roi, graph, audit

# Register routers
app.include_router(evolution.router, prefix="/api", tags=["Runtime Evolution"])
app.include_router(triage.router, prefix="/api", tags=["Alert Triage"])
app.include_router(soc.router, prefix="/api", tags=["SOC Analytics"])
app.include_router(metrics.router, prefix="/api", tags=["Compounding Metrics"])
app.include_router(roi.router, prefix="/api", tags=["ROI Calculator"])
app.include_router(graph.router, prefix="/api", tags=["Graph Intelligence"])
app.include_router(audit.router, prefix="/api", tags=["Audit Trail"])

# Lifecycle events
@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    from app.db.neo4j import neo4j_client
    await neo4j_client.connect()
    print("[OK] Connected to Neo4j")

    from app.core.domain_registry import get_active_domain, get_domain_config
    config = get_domain_config()
    print(f"[DOMAIN] Active domain: {config.display_name} ({config.name})")
    print(f"[DOMAIN] Factors: {len(config.factors)}, Actions: {len(config.actions)}, Situations: {len(config.situation_types)}")

    # Register all in-memory reset handlers with state_manager.
    # Both reset endpoints call state_manager.reset_all() — adding a new
    # state store only requires registering it here, not editing every endpoint.
    from app.core.state_manager import state_manager
    from app.services.feedback import reset_feedback_state
    from app.services.policy import reset_policy_state
    from app.services.audit import reset_audit_state
    from app.services.evolver import reset_evolver_state
    state_manager.register("feedback", reset_feedback_state)
    state_manager.register("policy",   reset_policy_state)
    state_manager.register("audit",    reset_audit_state)
    state_manager.register("evolver",  reset_evolver_state)

@app.on_event("shutdown")
async def shutdown_event():
    """Close connections on shutdown"""
    from app.db.neo4j import neo4j_client
    await neo4j_client.close()
    print("[OK] Disconnected from Neo4j")
