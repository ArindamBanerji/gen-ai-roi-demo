"""
SOC Copilot Demo - FastAPI Backend
Main application entry point with CORS and router registration.
"""
from contextlib import asynccontextmanager
import logging
import os as _cors_os
from typing import cast

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from copilot_sdk.auth import AuthMiddleware
from copilot_sdk.backend.auth_router import create_auth_router
from dotenv import load_dotenv
from app.middleware.pii_redaction import PIIRedactionMiddleware

logger = logging.getLogger(__name__)

# Load environment variables from project root
# Copy ../.env.example to ../.env and fill in credentials before starting
load_dotenv(dotenv_path="../.env")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup_event()
    yield
    await shutdown_event()


app = FastAPI(
    title="SOC Copilot Demo API",
    description="AI-augmented Security Operations Center with Runtime Evolution",
    version="5.0.0",
    lifespan=lifespan,
)

DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173,"
    "http://localhost:5174,"
    "http://localhost:5175,"
    "http://localhost:5176,"
    "http://localhost:5177,"
    "http://127.0.0.1:5173,"
    "http://127.0.0.1:5174,"
    "http://127.0.0.1:5175,"
    "http://127.0.0.1:5176,"
    "http://127.0.0.1:5177"
)


def _cors_origins() -> list[str]:
    if _cors_os.environ.get("CORS_DEV_MODE", "").strip().lower() == "true":
        return ["*"]
    configured = _cors_os.environ.get("ALLOWED_ORIGINS")
    if configured is None:
        configured = _cors_os.environ.get("CORS_ORIGINS", DEFAULT_CORS_ORIGINS)
    return [
        origin.strip()
        for origin in configured.split(",")
        if origin.strip()
    ]

def _cors_credentials() -> bool:
    return "*" not in _cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=_cors_credentials(),
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=600,
)


app.add_middleware(AuthMiddleware)


app.add_middleware(PIIRedactionMiddleware)


def _safe_entity_cache_health() -> dict:
    try:
        from app.routers import triage

        return cast(dict, triage._soc_entity_cache_diagnostics())
    except Exception as exc:
        return {
            "available": False,
            "error": type(exc).__name__,
        }


# Health check endpoint
@app.get("/")
async def root():
    return {
        "service": "SOC Copilot Demo",
        "status": "operational",
        "version": "5.0.0"
    }

@app.get("/health")
@app.get("/api/health")
async def health():
    from app.services import rl_engine
    from app.services.posterior_store import PosteriorStore
    from copilot_sdk.config import GraphConfig

    store = getattr(rl_engine, "_posterior_store", None)
    try:
        if store is None:
            graph_config = GraphConfig.load(
                "soc",
                profile="test" if _cors_os.getenv("PYTEST_CURRENT_TEST") else "production",
            )
            store = PosteriorStore(graph_config)
        posterior_health = store.health_check()
    except Exception as exc:
        logger.exception("PosteriorStore health check failed")
        posterior_health = {
            "healthy": False,
            "status": "FAILED",
            "reason": str(exc),
            "error": str(exc),
        }

    graph_health = {
        "healthy": bool(posterior_health.get("healthy")),
        "status": "healthy" if posterior_health.get("healthy") else "FAILED",
        "source": "posterior_store",
    }
    return {
        "status": "healthy" if graph_health["healthy"] else "degraded",
        "components": {
            "graph": graph_health,
            "posterior_store": posterior_health,
            "entity_cache": _safe_entity_cache_health(),
        },
    }

# Router imports
from app.routers import evolution, triage, soc, metrics, roi, graph, audit, gae, admin, simulation, evaluation, judgment, framework_router, eval_router, governance_router, whatif_router, time_machine_router, discoveries_router, platform, shadow, soc_learning, authority, explain, soc_demo_beats, enterprise
from app.routers.servicenow_router import router as servicenow_router
from app.routers.rl_router import router as rl_router
from app.routers.cohort_status_router import router as cohort_status_router
from app.services.evolver import get_sdk_evolver
from copilot_sdk.backend.self_computation_router import mount_self_computation_router
from copilot_sdk.backend.evolution_router import create_evolution_router

# Register routers
app.include_router(evaluation.router, prefix="/api/soc", tags=["evaluation"])
app.include_router(judgment.router, prefix="/api/soc", tags=["judgment"])
app.include_router(evolution.router, prefix="/api", tags=["Runtime Evolution"])
app.include_router(
    create_evolution_router(
        domain="soc",
        evolver_factory=get_sdk_evolver,
    )
)
app.include_router(triage.router, prefix="/api", tags=["Alert Triage"])
app.include_router(framework_router.router, prefix="/api", tags=["CopilotFramework"])
app.include_router(soc_learning.router, prefix="/api", tags=["SOC Learning Control Room"])
app.include_router(authority.router, prefix="/api", tags=["SOC Authority Ladder"])
app.include_router(soc_demo_beats.router, prefix="/api", tags=["SOC Demo Beats"])
app.include_router(explain.router, prefix="/api", tags=["SOC Explainability"])
app.include_router(soc.router, prefix="/api", tags=["SOC Analytics"])
app.include_router(metrics.router, prefix="/api", tags=["Compounding Metrics"])
app.include_router(roi.router, prefix="/api", tags=["ROI Calculator"])
app.include_router(graph.router, prefix="/api", tags=["Graph Intelligence"])
app.include_router(audit.router, prefix="/api", tags=["Audit Trail"])
app.include_router(governance_router.router, prefix="/api", tags=["Governance Evidence"])
app.include_router(gae.router, prefix="/api", tags=["GAE Learning"])
app.include_router(admin.router, prefix="/api", tags=["Admin"])
app.include_router(simulation.router, prefix="/api", tags=["Simulation"])
app.include_router(whatif_router.router, prefix="/api", tags=["What-If"])
app.include_router(eval_router.router, prefix="/api", tags=["Evaluation Upload"])
app.include_router(time_machine_router.router, prefix="/api", tags=["Time Machine"])
app.include_router(discoveries_router.router, prefix="/api", tags=["Cross-Graph Discovery"])
app.include_router(platform.router, prefix="/api", tags=["Platform"])
app.include_router(shadow.router, prefix="/api/soc", tags=["Shadow Promotion"])
app.include_router(cohort_status_router, prefix="/api", tags=["Campaign Cohorts"])
app.include_router(rl_router, prefix="/api", tags=["RL Observability"])
app.include_router(servicenow_router)
app.include_router(enterprise.router, prefix="/api", tags=["Enterprise Connectors"])
app.include_router(create_auth_router())


def _soc_store_provider():
    from app.services.gae_state import get_profile_scorer

    return get_profile_scorer().graph_store


def _soc_scorer_provider():
    from app.services.gae_state import get_profile_scorer

    scorer = get_profile_scorer()
    return getattr(scorer, "_compound", scorer)


# Shared centroid-history route (canonical checkpoint history).
mount_self_computation_router(
    app,
    _soc_store_provider,
    domain="soc",
    scorer_provider=_soc_scorer_provider,
    evolver_provider=get_sdk_evolver,
)

async def startup_event():
    """Initialize connections on startup"""
    from app.auth.config import load_auth_config as _load_auth_config
    _auth_cfg = _load_auth_config()
    if _auth_cfg.saml_enabled:
        _auth_errors = _auth_cfg.validate()
        if _auth_errors:
            print(f"[AUTH] SAML config invalid: {_auth_errors}")
            raise SystemExit(1)
        print(f"[AUTH] SAML enabled -- IdP: {_auth_cfg.idp_entity_id}, SP: {_auth_cfg.sp_entity_id}")
    else:
        print("[AUTH] SAML disabled -- all routes open")

    from app.db.graph_client import graph_client, soc_decision_where, _GRAPH_BACKEND
    import os as _os
    import pathlib as _pathlib

    # Write actual port to root .env so Playwright and other tools
    # discover it automatically without manual configuration.
    _port = _os.getenv("PORT", "8001")
    _env_path = _pathlib.Path(__file__).parents[2] / ".env"
    try:
        if _env_path.exists():
            _lines = _env_path.read_text(encoding="utf-8").splitlines()
            _lines = [l for l in _lines if not l.startswith("BACKEND_PORT=")]
            _lines.append(f"BACKEND_PORT={_port}")
            _env_path.write_text("\n".join(_lines) + "\n", encoding="utf-8")
            print(f"[STARTUP] BACKEND_PORT={_port} written to .env")
    except (OSError, PermissionError) as e:
        log.warning(f"[STARTUP] Cannot write .env: {e}")

    _backend = _GRAPH_BACKEND

    # AGE needs an explicit connect(); AGEClient.connect() is a no-op.
    if _backend == "graph":
        await graph_client.connect()

    # ── Bootstrap verification — MANDATORY, fail-fast ─────────
    try:
        _verify = await graph_client.run_query(
            "MATCH (n) RETURN count(n) AS total"
        )
        _node_count = _verify[0]["total"] if _verify else 0
        print(
            f"[STARTUP] Backend={_backend.upper()} | "
            f"Client={type(graph_client).__name__} | "
            f"Nodes={_node_count} | "
            f"Status=VERIFIED"
        )
    except Exception as _e:
        print(
            f"[STARTUP] Backend={_backend.upper()} "
            f"verification FAILED: {_e}"
        )
        if _backend == "age":
            raise SystemExit(
                f"FATAL: AGE verification failed: {_e}"
            ) from _e
        raise
    # ──────────────────────────────────────────────────────────

    # Bootstrap correct_decisions from graph — non-blocking.
    # Mirrors support/setup/bootstrap_learning_loop.py but runs automatically
    # on every restart so correct_decisions is never stale after a reboot.
    # The separate script is still useful for bulk historical migrations.
    try:
        _total_res = await graph_client.run_query(
            f"MATCH (d:Decision) WHERE {soc_decision_where()} "
            "AND d.outcome IS NOT NULL "
            "RETURN count(d) AS total"
        )
        _correct_res = await graph_client.run_query(
            f"MATCH (d:Decision) WHERE {soc_decision_where()} "
            "AND d.correct = true "
            "RETURN count(d) AS correct"
        )
        _cd_total   = int(_total_res[0]["total"])   if _total_res   else 0
        _cd_correct = int(_correct_res[0]["correct"]) if _correct_res else 0
        _cd_pct = round(_cd_correct / _cd_total * 100, 1) if _cd_total > 0 else 0.0
        print(
            f"[STARTUP] correct_decisions={_cd_correct}, "
            f"verified={_cd_total}, "
            f"accuracy={_cd_pct}%"
        )
        if _cd_correct == 0 and _backend == "age":
            print(
                "[STARTUP] WARNING: correct_decisions=0 -- historical Decision nodes "
                "may lack outcome/correct fields. Run "
                "support/setup/bootstrap_learning_loop.py --live to backfill."
            )
    except Exception as _cd_exc:
        print(f"[STARTUP] correct_decisions bootstrap failed (non-blocking): {_cd_exc}")

    try:
        from gae.evolution import rebuild_shadow_index
        _shadow_index = await rebuild_shadow_index(graph_client)
        if _shadow_index:
            print(f"[STARTUP] Evolution shadow index rebuilt: {len(_shadow_index)} variants")
    except Exception as _shadow_exc:
        print(f"[STARTUP] Evolution shadow index rebuild failed (non-blocking): {_shadow_exc}")

    try:
        from app.services.variant_registry import rebuild_registry
        _variant_registry = await rebuild_registry(graph_client)
        _variant_count = int(_variant_registry.get("rebuilt", 0))
        if _variant_count:
            print(f"[STARTUP] Variant registry rebuilt: {_variant_count} variants")
    except Exception as _registry_exc:
        print(f"[STARTUP] Variant registry rebuild failed (non-blocking): {_registry_exc}")

    # Load analyst correct-override examples into OverrideDetector.
    # Activates automatically when >= 50 examples are found in AGE.
    from app.services.override_detector import load_from_graph as _load_od
    _od = await _load_od(graph_client)
    print(
        f"[OverrideDetector] {'ACTIVATED' if _od.activated else 'inactive'} -- "
        f"{_od.example_count} correct-override examples loaded."
    )

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

    # Configure authority only after init_learning_state has created the
    # scorer's AGE-backed GraphStore.  All migrated services must share this
    # already-initialized store rather than constructing a partial adapter.
    from app.services.authority_ladder import configure_authority_graph_store
    app.state.graph_store = get_profile_scorer().graph_store
    configure_authority_graph_store(app.state.graph_store)

    try:
        from app.services.promotion_gate import register_rollback_handler
        _rollback_registered = register_rollback_handler(graph_client)
        print(
            "[STARTUP] Promotion rollback handler "
            f"{'registered' if _rollback_registered else 'not available'}"
        )
    except Exception as _rollback_exc:
        print(f"[STARTUP] Promotion rollback handler registration failed (non-blocking): {_rollback_exc}")

    # Block 2.2: Persist bootstrap μ₀ centroid tensor to DeploymentState node.
    # Runs every startup so the centroid export endpoint always reflects current μ₀.
    try:
        from app.services.gae_state import write_bootstrap_state
        await write_bootstrap_state(graph_client, get_profile_scorer())
    except Exception as _ds_exc:
        print(f"[GAE] DeploymentState write failed (non-blocking): {_ds_exc}")

    # CORR-3: Write bootstrap Decision nodes to AGE if bootstrap ran this startup.
    # Skipped (get_bootstrap_result() is None) when loading an existing checkpoint.
    _bs_result = get_bootstrap_result()
    if _bs_result is not None:
        # RETIRED: orphan creator, replaced by support/setup/seed_zero_day.py
        # from app.services.bootstrap_graph import write_bootstrap_decisions
        pass  # seed_zero_day.py handles Decision seeding outside the startup path

    # Sync decision_count from AGE so IKS reflects historical decisions
    # on every server restart (fixes cold-start IKS = 1.7/100 regression).
    try:
        _count_result = await graph_client.run_query(
            f"MATCH (d:Decision) WHERE {soc_decision_where()} "
            "RETURN count(d) AS cnt"
        )
        _historical_count = _count_result[0]["cnt"] if _count_result else 0
        from app.services.gae_state import get_learning_state as _get_ls
        _ls = _get_ls()
        if _ls.decision_count < _historical_count:
            _ls.decision_count = _historical_count
            print(f"[STARTUP] Synced decision_count from graph: {_historical_count}")
        else:
            print(f"[STARTUP] decision_count already current ({_ls.decision_count}), skipping AGE sync")
    except Exception as _sync_exc:
        print(f"[STARTUP] decision_count sync failed (non-blocking): {_sync_exc}")

    # BACKLOG-020 Phase 1: prefer verified count over total count.
    # count_verified_decisions() counts only decisions with outcome feedback.
    # Runs after the total-count sync so it takes precedence when > 0.
    # Safe fallback: if result is 0 (empty DB / error), existing count preserved.
    try:
        _verified_count = await graph_client.count_verified_decisions()
        if _verified_count > 0:
            from app.services.gae_state import get_learning_state as _get_ls_v
            _get_ls_v().decision_count = _verified_count
            print(f"[STARTUP] Verified decision_count from graph: {_verified_count}")
    except Exception as _vd_exc:
        print(f"[STARTUP] count_verified_decisions failed (non-blocking): {_vd_exc}")

    # BACKLOG-020 Phase 7: Initialize GraphSnapshot — single source of truth for
    # all display-layer statistics that have a graph equivalent.
    # Must run AFTER count_verified_decisions sync (above) so IKS reflects
    # the current ProfileScorer state, not a stale bootstrap value.
    try:
        from app.state.graph_snapshot import GraphSnapshot, set_snapshot as _set_snapshot
        _snap = await GraphSnapshot.from_graph(graph_client)
        _set_snapshot(_snap)
        print(
            f"[SNAPSHOT] GraphSnapshot initialized: "
            f"{_snap.verified_decisions} verified decisions, "
            f"correct={_snap.correct_decisions}, "
            f"IKS={_snap.iks_score:.1f}, "
            f"override_rate={_snap.override_rate:.3f}"
        )
    except Exception as _snap_exc:
        print(f"[SNAPSHOT] GraphSnapshot init failed (non-blocking): {_snap_exc}")

    # Rebuild audit chain from AGE Decision nodes so verify_chain is non-empty
    # after restart (BACKLOG-045). Skipped on hot reload if ledger already has entries.
    try:
        from app.framework.audit import rebuild_from_age
        _rebuilt = await rebuild_from_age()
        print(f"[STARTUP] Audit ledger rebuilt: {_rebuilt} entries")
    except Exception as _audit_exc:
        print(f"[STARTUP] Audit ledger rebuild failed (non-blocking): {_audit_exc}")

    # Timestamp repair is now an explicit operator action:
    #   python support/setup/repair_zero_day_timestamps.py --dry-run
    #   python support/setup/repair_zero_day_timestamps.py --apply
    # Startup must not mutate zero_day_synthetic Decision timestamps.

    # Warm up all domain config properties.
    # Iterates every registered domain and touches all @property accessors so
    # Python initialises any lazy sub-modules now, not on the first API request.
    # Without this, GET /api/demo/domains can stall 20+ seconds on a cold server
    # immediately after a demo reset (graph reconnect + lazy S2P module init).
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
    from app.services.rl_engine import reset_rl_state
    from app.services.servicenow_mock import get_servicenow_mock
    state_manager.register("feedback",            reset_feedback_state)
    state_manager.register("trust",               reset_trust_state)
    state_manager.register("policy",              reset_policy_state)
    state_manager.register("audit",               reset_audit_state)
    state_manager.register("evolver",             reset_evolver_state)
    state_manager.register("confidence_history",  reset_confidence_history)
    state_manager.register("learning_state",      reset_learning_state)
    state_manager.register("rl_engine",           reset_rl_state)
    state_manager.register("platform_caches",     platform.reset_platform_caches)
    state_manager.register("baseline_caches",     soc.reset_baseline_caches)
    state_manager.register("servicenow_mock",     get_servicenow_mock().reset)

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
        f"[CONNECTOR] Registry initialized -- "
        f"{connector_registry.count()} connector(s) registered"
    )

    # Discovery cache warm (non-blocking — server starts even if this fails).
    # Prevents first GET /api/discoveries from triggering synchronous full refresh.
    try:
        from app.services.cross_graph_discovery import discovery_service
        await discovery_service.refresh("soc", graph_client)
        logger.info("[Discovery] Cache warmed at startup")
    except Exception as _disc_exc:
        logger.warning("[Discovery] Startup warm failed (non-blocking): %s", _disc_exc)

    # F6 startup recorrelation — runs only if no Campaign nodes exist yet.
    # Non-blocking: any exception is logged and swallowed.
    try:
        from app.domains.soc.campaigns import CampaignCorrelationEngine, CampaignRepository
        from app.domains.soc.config import SOCDomainConfig
        _camp_repo = CampaignRepository(graph_client)
        if not await _camp_repo.campaigns_exist():
            _camp_config = SOCDomainConfig.get_campaign_config()
            _camp_engine = CampaignCorrelationEngine(_camp_config)
            _camp_events = await _camp_repo.fetch_all_events()
            _campaigns = _camp_engine.correlate(_camp_events)
            for _c in _campaigns:
                await _camp_repo.write_campaign(_c)
            print(f"[F6] Startup recorrelation: {len(_campaigns)} campaigns found.")
        else:
            print("[F6] Campaign nodes exist -- skipping startup recorrelation.")
    except Exception as _camp_exc:
        print(f"[F6] Startup recorrelation failed (non-blocking): {_camp_exc}")

    # PB-03 Sentinel polling — disabled by default; non-blocking if configured.
    try:
        from app.services.sentinel_poller import start_sentinel_poller

        _sentinel_status = await start_sentinel_poller()
        if _sentinel_status.get("started"):
            logger.info("[Sentinel] Poller started")
    except Exception as _sentinel_exc:
        logger.warning("[Sentinel] Poller startup failed (non-blocking): %s", _sentinel_exc)

async def shutdown_event():
    """Close connections on shutdown"""
    try:
        from app.services.sentinel_poller import stop_sentinel_poller

        await stop_sentinel_poller()
    except Exception as _sentinel_exc:
        logger.warning("[Sentinel] Poller shutdown failed: %s", _sentinel_exc)

    from app.db.graph_client import graph_client
    if hasattr(graph_client, "close"):
        await graph_client.close()
        print("[OK] Disconnected from AGE")
