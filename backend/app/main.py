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
    version="5.0.0",
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
        "version": "5.0.0"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

# Router imports
from app.routers import evolution, triage, soc, metrics, roi, graph, audit, gae, admin, simulation, evaluation, judgment

# Register routers
app.include_router(evaluation.router, prefix="/api/soc", tags=["evaluation"])
app.include_router(judgment.router, prefix="/api/soc", tags=["judgment"])
app.include_router(evolution.router, prefix="/api", tags=["Runtime Evolution"])
app.include_router(triage.router, prefix="/api", tags=["Alert Triage"])
app.include_router(soc.router, prefix="/api", tags=["SOC Analytics"])
app.include_router(metrics.router, prefix="/api", tags=["Compounding Metrics"])
app.include_router(roi.router, prefix="/api", tags=["ROI Calculator"])
app.include_router(graph.router, prefix="/api", tags=["Graph Intelligence"])
app.include_router(audit.router, prefix="/api", tags=["Audit Trail"])
app.include_router(gae.router, prefix="/api", tags=["GAE Learning"])
app.include_router(admin.router, prefix="/api", tags=["Admin"])
app.include_router(simulation.router, prefix="/api", tags=["Simulation"])

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

    # Initialize GAE learning state (bootstrap calibration on cold start or
    # legacy checkpoint; load directly if bootstrap metadata present).
    # Must be done before registering reset handlers so the singleton is ready.
    from app.services.gae_state import init_learning_state, reset_learning_state, get_bootstrap_result, get_profile_scorer
    ls = init_learning_state()
    print(f"[GAE] LearningState ready: W.shape={ls.W.shape}, step={ls.decision_count}")

    # CORR-3: Write bootstrap Decision nodes to Neo4j if bootstrap ran this startup.
    # Skipped (get_bootstrap_result() is None) when loading an existing checkpoint.
    _bs_result = get_bootstrap_result()
    if _bs_result is not None:
        from app.services.bootstrap_neo4j import write_bootstrap_decisions
        from app.domains.soc.config import SOC_CATEGORIES
        await write_bootstrap_decisions(
            neo4j_client=neo4j_client,
            scorer=get_profile_scorer(),
            categories=list(SOC_CATEGORIES),
            decisions_per_category=_bs_result.decisions_per_category,
        )

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

    # Initialize NarrativeProvider singleton (NAR-1).
    # Reads NARRATIVE_PROVIDER env var; defaults to "template".
    import os as _os
    from app.services.narrative import create_narrative_provider, set_narrative_provider
    _narr_type = _os.getenv("NARRATIVE_PROVIDER", "template")
    set_narrative_provider(create_narrative_provider(_narr_type))
    print(f"[NARRATIVE] Provider initialized: {_narr_type}")

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

    # F6 startup recorrelation — runs only if no Campaign nodes exist yet.
    # Non-blocking: any exception is logged and swallowed.
    try:
        from app.domains.soc.campaigns import CampaignCorrelationEngine, CampaignRepository
        from app.domains.soc.config import SOCDomainConfig
        _camp_repo = CampaignRepository(neo4j_client)
        if not await _camp_repo.campaigns_exist():
            _camp_config = SOCDomainConfig.get_campaign_config()
            _camp_engine = CampaignCorrelationEngine(_camp_config)
            _camp_events = await _camp_repo.fetch_all_events()
            _campaigns = _camp_engine.correlate(_camp_events)
            for _c in _campaigns:
                await _camp_repo.write_campaign(_c)
            print(f"[F6] Startup recorrelation: {len(_campaigns)} campaigns found.")
        else:
            print("[F6] Campaign nodes exist — skipping startup recorrelation.")
    except Exception as _camp_exc:
        print(f"[F6] Startup recorrelation failed (non-blocking): {_camp_exc}")

@app.on_event("shutdown")
async def shutdown_event():
    """Close connections on shutdown"""
    from app.db.neo4j import neo4j_client
    await neo4j_client.close()
    print("[OK] Disconnected from Neo4j")
