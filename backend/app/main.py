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
from app.routers import evolution, triage, soc, metrics, roi, graph, audit, gae

# Register routers
app.include_router(evolution.router, prefix="/api", tags=["Runtime Evolution"])
app.include_router(triage.router, prefix="/api", tags=["Alert Triage"])
app.include_router(soc.router, prefix="/api", tags=["SOC Analytics"])
app.include_router(metrics.router, prefix="/api", tags=["Compounding Metrics"])
app.include_router(roi.router, prefix="/api", tags=["ROI Calculator"])
app.include_router(graph.router, prefix="/api", tags=["Graph Intelligence"])
app.include_router(audit.router, prefix="/api", tags=["Audit Trail"])
app.include_router(gae.router, prefix="/api", tags=["GAE Learning"])

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

    # Initialize GAE learning state (loads checkpoint or builds fresh W matrix).
    # Must be done before registering reset handlers so the singleton is ready.
    from app.services.gae_state import init_learning_state, reset_learning_state
    ls = init_learning_state()
    print(f"[GAE] LearningState ready: W.shape={ls.W.shape}, step={ls.decision_count}")

    # Warm up all domain config properties.
    # Iterates every registered domain and touches all @property accessors so
    # Python initialises any lazy sub-modules now, not on the first API request.
    # Without this, GET /api/demo/domains can stall 20+ seconds on a cold server
    # immediately after a demo reset (neo4j reconnect + lazy S2P module init).
    import time as _time
    _wu_start = _time.perf_counter()
    from app.core.domain_registry import _DOMAIN_CONFIGS
    for _domain_cfg in _DOMAIN_CONFIGS.values():
        _ = _domain_cfg.factors
        _ = _domain_cfg.actions
        _ = _domain_cfg.situation_types
        _ = _domain_cfg.policies
        _ = _domain_cfg.asymmetry_ratio
        _ = _domain_cfg.prompt_variants
        _ = _domain_cfg.metrics_config
    _wu_elapsed = _time.perf_counter() - _wu_start
    print(f"[WARMUP] Domain warm-up complete in {_wu_elapsed:.1f}s")

    # Warm up LLM narrator (pays the ~8s vertexai import cost at boot).
    # _ensure_init() is idempotent — safe to call multiple times.
    try:
        from app.services.reasoning import narrator as _narrator
        _narrator._ensure_init()
        print("[WARMUP] LLM narrator initialized")
    except Exception as _exc:
        print(f"[WARMUP] LLM narrator init failed (will retry on first request): {_exc}")

    # Register all in-memory reset handlers with state_manager.
    # Both reset endpoints call state_manager.reset_all() — adding a new
    # state store only requires registering it here, not editing every endpoint.
    from app.core.state_manager import state_manager
    from app.services.feedback import reset_feedback_state, reset_trust_state, seed_trust_history
    from app.services.policy import reset_policy_state
    from app.services.audit import reset_audit_state
    from app.services.evolver import reset_evolver_state
    from app.services.triage import reset_confidence_history, seed_confidence_history
    state_manager.register("feedback",            reset_feedback_state)
    state_manager.register("trust",               reset_trust_state)
    state_manager.register("policy",              reset_policy_state)
    state_manager.register("audit",               reset_audit_state)
    state_manager.register("evolver",             reset_evolver_state)
    state_manager.register("confidence_history",  reset_confidence_history)
    state_manager.register("learning_state",      reset_learning_state)

    # Pre-populate demo charts (previously done at module import).
    # Called here so they run once at boot regardless of import order.
    seed_trust_history()
    seed_confidence_history()

    # Initialize UCL Connector registry (C1).
    # Concrete connectors are registered per build prompt:
    #   C3 → PulsediveConnector
    #   C2 → GreyNoiseConnector
    #   C5 → CrowdStrikeMockConnector
    from app.connectors.registry import registry as connector_registry
    print(
        f"[CONNECTOR] Registry initialized — "
        f"{connector_registry.count()} connector(s) registered"
    )

@app.on_event("shutdown")
async def shutdown_event():
    """Close connections on shutdown"""
    from app.db.neo4j import neo4j_client
    await neo4j_client.close()
    print("[OK] Disconnected from Neo4j")
