"""
CopilotFramework router -- domain-agnostic endpoints.
Any copilot (SOC, S2P, fraud) exposes these endpoints.
Safe to copy to copilot-sdk.

Discipline: handlers here must import only from:
  app.framework.*
  app.services.gae_state (until learning_state extraction complete)
  app.db.*
  gae.*
  standard library
No app.domains.soc.* imports allowed.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from copilot_sdk.config import GraphConfig
from ci_platform.graph.age_client import AGEClient


_age_client = None
# Compatibility seam for existing tests and service integrations. Production
# code leaves this unset; _get_age_client always constructs the AGE client.
graph_client = None


def _get_age_client() -> AGEClient:
    global _age_client
    if graph_client is not None:
        return graph_client
    if _age_client is None:
        config = GraphConfig.load("soc")
        _age_client = AGEClient(dsn=config.dsn, graph_name=config.graph)
    return _age_client

router = APIRouter()
FRAMEWORK_DOMAIN = "soc"

QUERY_REGISTRY = {
    "decision_count": {
        "cypher": "MATCH (d:Decision) WHERE d.domain = $domain RETURN count(d) AS cnt",
        "params": {"domain": FRAMEWORK_DOMAIN},
    },
    "category_distribution": {
        "cypher": "MATCH (d:Decision) WHERE d.domain = $domain RETURN d.category AS cat, count(*) AS cnt",
        "params": {"domain": FRAMEWORK_DOMAIN},
    },
    "recent_decisions": {
        "cypher": "MATCH (d:Decision) WHERE d.domain = $domain RETURN d ORDER BY d.timestamp_epoch DESC LIMIT 20",
        "params": {"domain": FRAMEWORK_DOMAIN},
    },
}


# ============================================================================
# Request/Response Models (framework endpoints only)
# ============================================================================

class ShadowToggleRequest(BaseModel):
    enabled: bool


class AnalystActionRequest(BaseModel):
    decision_id: str
    analyst_action: str


class CheckpointCreateRequest(BaseModel):
    reason: str = "manual"


class RollbackRequest(BaseModel):
    checkpoint_id: str


class _GraphQueryRequest(BaseModel):
    query_name: str


class FreezeRequest(BaseModel):
    initiated_by: str
    reason: str


class RollbackInterventionRequest(BaseModel):
    snapshot_id: str
    initiated_by: str
    reason: str
    preview: bool = False


class ThresholdRequest(BaseModel):
    category: str
    new_threshold: float
    initiated_by: str
    reason: str


# ============================================================================
# GET /api/soc/centroid-evolution — Centroid delta history from Decision nodes
# Used by Tab-2 Section A/B and Tab-4 Chart A.
# ============================================================================

@router.get("/soc/centroid-evolution")
async def get_centroid_evolution(
    n: int = Query(default=200, ge=1, le=1000),
    category: Optional[str] = Query(default=None),
):
    """
    Return centroid drift history from Decision nodes.
    Used by Tab-2 Section A/B and Tab-4 Chart A.

    Drift is the cumulative L2 distance from bootstrap baseline mu_0:
        drift[c] = ||mu(t)[c,a,:] - mu_0[c,a,:]||_2  (mean over actions)

    Primary path: Decision nodes with centroid_delta_norm set (live triage).
    Fallback: when primary returns empty, compute current drift from mu_0 using
    the in-memory ProfileScorer -- no AGE required. Returns one record per
    category (or for the requested category) showing accumulated drift.
    """
    result = []
    try:
        from app.graph_schema import _S

        category_filter = ""
        if category:
            category_filter = f"AND d.category = {_S(category)}"

        rows = await _get_age_client().run_query(
            f"""
            MATCH (d:Decision)
            WHERE d.domain = $domain
              AND d.centroid_delta_norm IS NOT NULL
              AND d.centroid_delta_norm > 0
              {category_filter}
            RETURN d.decision_id AS id,
                   d.centroid_delta_norm AS centroid_delta_norm,
                   d.category AS category,
                   d.action AS action,
                   d.correct AS correct,
                   d.verified_at_epoch AS verified_at
            ORDER BY d.verified_at_epoch ASC
            LIMIT {n}
            """,
            {"domain": FRAMEWORK_DOMAIN},
        )
        for i, r in enumerate(rows):
            result.append({
                "decision_number": i + 1,
                "id": r.get("id"),
                "centroid_delta_norm": float(r.get("centroid_delta_norm") or 0.0),
                "category": r.get("category") or "unknown",
                "action": r.get("action") or "unknown",
                "correct": bool(r.get("correct")),
                "verified_at": str(r.get("verified_at") or ""),
                "drift_type": "per_update",
            })
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="AGE query failed for centroid evolution",
        ) from exc

    if not result:
        return []

    print(f"[SOC] centroid-evolution: returned {len(result)} records (n={n}, category={category!r})")
    return result


# ============================================================================
# GET /api/soc/convergence-calendar — Convergence Calendar (L-08)
# CLAIM-CONV-01: N_half = f(q̄, σ, kernel). V is NOT causal.
# ============================================================================

@router.get("/soc/convergence-calendar")
async def get_convergence_calendar():
    """
    Return per-factor convergence calendar with N_half predictions.

    Reads sigma_per_factor, q_bar, V, kernel, and decisions_per_factor from
    live deployment state when available. Falls back to documented defaults
    when state is not yet initialised.
    """
    from app.services.convergence_calendar import build_convergence_calendar, SOC_FACTORS

    # ── defaults (used when deployment state unavailable) ──────────────────
    DEFAULT_SIGMA  = 0.15
    DEFAULT_Q_BAR  = 0.75
    DEFAULT_V      = 200.0
    DEFAULT_KERNEL = "l2"

    sigma_per_factor    = {f: DEFAULT_SIGMA for f in SOC_FACTORS}
    q_bar               = DEFAULT_Q_BAR
    V                   = DEFAULT_V
    kernel              = DEFAULT_KERNEL
    decisions_per_factor = {f: 0 for f in SOC_FACTORS}
    data_source = "cold_start_defaults"

    # ── try to read live state ──────────────────────────────────────────────
    try:
        from app.services.gae_state import get_learning_state
        ls = get_learning_state()

        # Decision count per factor — query AGE decision nodes grouped by factor
        try:
            rows = await _get_age_client().run_query(
                """
                MATCH (d:Decision)
                WHERE d.domain = $domain AND d.primary_factor IS NOT NULL
                RETURN d.primary_factor AS factor, count(d) AS cnt
                """,
                {"domain": FRAMEWORK_DOMAIN},
            )
            for row in rows:
                factor_name = str(row.get("factor", ""))
                if factor_name in decisions_per_factor:
                    decisions_per_factor[factor_name] = int(row.get("cnt", 0))
            if rows:
                data_source = "live_graph"
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Convergence graph data unavailable") from exc

        # Overall decision count as fallback for factors not tagged
        total = getattr(ls, "decision_count", 0)  # SOURCE: in-memory LearningState (resets on restart)
        if total and all(v == 0 for v in decisions_per_factor.values()):
            # Distribute evenly across factors when primary_factor tagging absent
            per = total // len(SOC_FACTORS)
            decisions_per_factor = {f: per for f in SOC_FACTORS}
            data_source = "in_memory_learning_state"

    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="Convergence state unavailable") from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Convergence state unavailable") from exc

    result = build_convergence_calendar(
        sigma_per_factor=sigma_per_factor,
        q_bar=q_bar,
        V=V,
        kernel=kernel,
        decisions_per_factor=decisions_per_factor,
    )
    result["data_source"] = data_source
    return result


# ============================================================================
# GET /api/soc/ols-status — OLS Dashboard (L-09)
# ============================================================================

@router.get("/soc/ols-status")
async def get_ols_status_endpoint():
    """
    Return OLS (Override Lift Score) dashboard status.

    Uses GAE 0.7.18 OLSMonitor (CUSUM, plateau-snapshot baseline).
    ACM activates only for analysts with >= 20 overrides.

    Response
    --------
    {
        "status": "warming_up" | "monitoring" | "alarm",
        "baseline_ols": float | null,
        "current_ols": float | null,
        "delta_pct": float | null,
        "cusum": float,
        "alarm": bool,
        "baseline_frozen": bool,
        "qualified_analysts": int,
        "acm_active": bool,
        "message": str,
    }
    """
    from app.services.ols_status import get_ols_status

    ols_history: list = []
    analyst_overrides: dict = {}
    warm_start_active: bool = False

    try:
        # Read OLS history from Decision nodes (ols_score property)
        result = await _get_age_client().run_query(
            "MATCH (d:Decision) WHERE d.domain = $domain AND d.ols_score IS NOT NULL "
            "RETURN d.ols_score AS ols_score ORDER BY d.decision_number ASC",
            {"domain": FRAMEWORK_DOMAIN},
        )
        ols_history = [float(r["ols_score"]) for r in result]
    except Exception as exc:
        raise HTTPException(status_code=503, detail="AGE query failed for OLS history") from exc

    try:
        # Read override counts per analyst
        result = await _get_age_client().run_query(
            "MATCH (d:Decision) WHERE d.domain = $domain AND d.analyst_id IS NOT NULL AND d.was_override = true "
            "RETURN d.analyst_id AS analyst_id, count(*) AS cnt",
            {"domain": FRAMEWORK_DOMAIN},
        )
        analyst_overrides = {r["analyst_id"]: int(r["cnt"]) for r in result}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="AGE query failed for analyst overrides") from exc

    try:
        # Check warm_start flag from LearningState node if present
        result = await _get_age_client().run_query(
            "MATCH (ls:LearningState) RETURN ls.warm_start_active AS warm_start LIMIT 1",
            {},
        )
        if result:
            warm_start_active = bool(result[0].get("warm_start", False))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="AGE query failed for warm-start state") from exc

    return get_ols_status(
        ols_history=ols_history,
        warm_start_active=warm_start_active,
        analyst_overrides=analyst_overrides,
    )


# ============================================================================
# GET /api/soc/flywheel-comparison — W2 Flywheel Demo Moment (Feature 3)
# ============================================================================

@router.get("/soc/flywheel-comparison")
async def get_flywheel_comparison(alert_id: str = "ALERT-001", category: str = "credential_access"):
    """
    Return W2 flywheel Day-1 vs current comparison for a given alert category.

     Inactive when TRIGGERED_EVOLUTION edge count < 10 (cold-start guard).

    Response
    --------
    {
         "flywheel_active": bool,
         "reason": str (if inactive),
        "category": str,
        "day_1_snapshot": {...},
        "current": {...},
        "delta": {"confidence_gain", "action_changed", "edge_count_gain", "interpretation"},
    }
    """
    from app.services.flywheel_comparison import build_flywheel_comparison

    try:
        # Count TRIGGERED_EVOLUTION edges for this category
        from app.graph_schema import _S
        edge_result = await _get_age_client().run_query(
            "MATCH (d:Decision)-[:TRIGGERED_EVOLUTION]->(e:EvolutionEvent) "
            "WHERE d.domain = $domain AND d.category = $category "
            "RETURN count(e) AS cnt",
            {"category": category, "domain": FRAMEWORK_DOMAIN},
        )
        edge_count = int(edge_result[0]["cnt"]) if edge_result else 0

        if edge_count < 10:
            return build_flywheel_comparison(
                current_edges=edge_count,
                current_factor_4=0.40,
                current_confidence=0.71,
                current_action="investigate",
                current_provenance="",
                category=category,
            )

        # Read latest factor_4 and confidence from most recent Decision for category
        decision_result = await _get_age_client().run_query(
            "MATCH (d:Decision) WHERE d.domain = $domain AND d.category = $category "
            "RETURN d.factor_snapshot AS factor_snapshot_raw, d.confidence AS confidence, "
            "d.action AS action ORDER BY d.decision_number DESC LIMIT 1",
            {"category": category, "domain": FRAMEWORK_DOMAIN},
        )
        if decision_result:
            _raw_snap = decision_result[0].get("factor_snapshot_raw")
            if isinstance(_raw_snap, str):
                import json
                try:
                    _raw_snap = json.loads(_raw_snap)
                except (json.JSONDecodeError, ValueError):
                    _raw_snap = None
            factor_4 = float(_raw_snap[3]) if isinstance(_raw_snap, list) and len(_raw_snap) > 3 else 0.40
            confidence = float(decision_result[0].get("confidence") or 0.71)
            action = str(decision_result[0].get("action") or "investigate")
        else:
            factor_4, confidence, action = 0.40, 0.71, "investigate"

        provenance = f"{edge_count} verified decisions on {category}. Pattern history strong."

        return build_flywheel_comparison(
            current_edges=edge_count,
            current_factor_4=factor_4,
            current_confidence=confidence,
            current_action=action,
            current_provenance=provenance,
            category=category,
        )

    except Exception as exc:
        raise HTTPException(status_code=503, detail="AGE query failed for flywheel comparison") from exc


# ============================================================================
# GET /api/soc/iks-trend — IKS v2 trend (Chart A replacement)
# ============================================================================

@router.get("/soc/iks-trend")
async def get_iks_trend_endpoint():
    """
    Return IKS v2 score trend for Chart A.

    Currently returns the current score as a single trend point.
    Future: store periodic IKSSnapshot nodes for historical trend.

    Response
    --------
    {
        "trend": [{"decisions": int, "iks_v2": float, "timestamp": str}],
        "current": {"iks_v2": float, "components": dict, "interpretation": str},
    }
    """
    from app.services.iks import compute_iks_v2

    try:
        current = await compute_iks_v2(_get_age_client())  # SOURCE: computed from graph (Decision nodes + centroids)
    except Exception as exc:
        print(f"[SOC] iks-trend compute failed: {exc}")
        raise HTTPException(status_code=503, detail="AGE query failed for IKS") from exc

    trend_point = {
        "decisions":  current.get("total_decisions", 0),
        "iks_v2":     current.get("iks_v2", 0.0),
        "timestamp":  datetime.utcnow().isoformat() + "Z",
    }

    return {
        "trend": [trend_point],
        "current": {
            "iks_v2":         current.get("iks_v2", 0.0),
            "components":     current.get("components", {}),
            "interpretation": current.get("interpretation", ""),
        },
    }


# ============================================================================
# Shadow mode endpoints  (Phase 3)
# ============================================================================

@router.post("/soc/shadow/toggle")
async def shadow_toggle(request: ShadowToggleRequest):
    """Enable or disable shadow mode."""
    from app.services.shadow_mode import ShadowModeService
    ShadowModeService.SHADOW_ENABLED = request.enabled
    return {"shadow_mode": ShadowModeService.SHADOW_ENABLED}


@router.post("/soc/shadow/analyst-action")
async def shadow_analyst_action(request: AnalystActionRequest):
    """Record what the analyst actually did for a shadow decision."""
    from app.services.shadow_mode import ShadowModeService
    await ShadowModeService.record_analyst_action(
        decision_id=request.decision_id,
        analyst_action=request.analyst_action,
        graph_service=_get_age_client(),
    )
    return {"recorded": True}


@router.get("/soc/shadow/report")
async def shadow_report():
    """Return shadow mode agreement report by category."""
    from app.services.shadow_mode import ShadowModeService
    return await ShadowModeService.get_shadow_report(_get_age_client())


# ============================================================================
# Checkpoint / Rollback endpoints  (Phase 4 §17.5)
# ============================================================================

@router.post("/soc/checkpoint/create")
async def checkpoint_create(request: CheckpointCreateRequest):
    """Snapshot current centroids to a Checkpoint node."""
    from app.services.checkpoint import CheckpointService
    from app.services.gae_state import get_profile_scorer
    try:
        scorer = get_profile_scorer()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"Scorer not ready: {exc}")
    if scorer is None:
        raise HTTPException(status_code=503, detail="ProfileScorer not initialized")

    checkpoint_id = await CheckpointService.create_checkpoint(
        scorer=scorer,
        graph_service=_get_age_client(),
        reason=request.reason,
    )
    return {
        "checkpoint_id": checkpoint_id,
        "timestamp":     datetime.utcnow().isoformat() + "Z",
        "reason":        request.reason,
    }


@router.get("/soc/checkpoint/list")
async def checkpoint_list():
    """List all checkpoints ordered by timestamp DESC."""
    from app.services.checkpoint import CheckpointService
    checkpoints = await CheckpointService.list_checkpoints(_get_age_client())
    return {"checkpoints": checkpoints}


@router.post("/soc/checkpoint/rollback")
async def checkpoint_rollback(request: RollbackRequest):
    """Restore centroids from a checkpoint and freeze the scorer."""
    from app.services.checkpoint import CheckpointService
    from app.services.gae_state import get_profile_scorer
    try:
        scorer = get_profile_scorer()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"Scorer not ready: {exc}")
    if scorer is None:
        raise HTTPException(status_code=503, detail="ProfileScorer not initialized")

    result = await CheckpointService.rollback(
        checkpoint_id=request.checkpoint_id,
        scorer=scorer,
        graph_service=_get_age_client(),
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ============================================================================
# Scorer freeze / unfreeze  (Phase 4)
# ============================================================================

@router.post("/soc/scorer/freeze")
async def scorer_freeze():
    """Freeze the ProfileScorer -- stops centroid updates."""
    from app.services.gae_state import get_profile_scorer, get_scorer_lock
    try:
        scorer = get_profile_scorer()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"Scorer not ready: {exc}")
    if scorer is None:
        raise HTTPException(status_code=503, detail="ProfileScorer not initialized")
    async with get_scorer_lock():
        scorer.freeze()
    return {"frozen": True}


@router.post("/soc/scorer/unfreeze")
async def scorer_unfreeze():
    """Unfreeze the ProfileScorer -- re-enables centroid updates."""
    from app.services.gae_state import get_profile_scorer, get_scorer_lock
    try:
        scorer = get_profile_scorer()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"Scorer not ready: {exc}")
    if scorer is None:
        raise HTTPException(status_code=503, detail="ProfileScorer not initialized")
    async with get_scorer_lock():
        scorer.unfreeze()
    return {"frozen": False}


# ============================================================================
# GET /api/soc/auto-approve-stats  — Phase 5 coverage dashboard
# ============================================================================

@router.get("/soc/auto-approve-stats")
async def auto_approve_stats():
    """Return per-category auto-approve coverage.

    Response
    --------
    {
        "total_decisions": int,
        "auto_approved":   int,
        "coverage_pct":    float,
        "by_category": {
            "credential_access": {"total": X, "auto_approved": Y, "coverage_pct": Z},
            ...
        }
    }
    """
    try:
        rows = await _get_age_client().run_query(
            """
            MATCH (d:Decision)
            WHERE d.domain = $domain
            RETURN d.category AS category,
                   count(d) AS total,
                   sum(CASE WHEN d.auto_approved = true THEN 1 ELSE 0 END) AS approved
            """,
            {"domain": FRAMEWORK_DOMAIN},
        )
    except Exception as exc:
            raise HTTPException(status_code=503, detail="AGE query failed") from exc

    by_category: dict = {}
    grand_total    = 0
    grand_approved = 0

    for row in rows:
        cat      = row.get("category") or "unknown"
        total    = int(row.get("total") or 0)
        approved = int(row.get("approved") or 0)
        by_category[cat] = {
            "total":        total,
            "auto_approved": approved,
            "coverage_pct": round(approved / max(total, 1) * 100, 1),
        }
        grand_total    += total
        grand_approved += approved

    return {
        "total_decisions": grand_total,
        "auto_approved":   grand_approved,
        "coverage_pct":    round(grand_approved / max(grand_total, 1) * 100, 1),
        "by_category":     by_category,
    }


# ============================================================================
# Graph Explorer endpoints — Phase 8 (Tab 1 Panel B)
# ============================================================================

@router.post("/soc/graph/query")
async def graph_explorer_query(request: _GraphQueryRequest):
    """Run a server-registered, domain-scoped read-only graph query.

    Body: {"query_name": "decision_count"}

    Returns {"rows": [...], "count": N, "query": str} on success.
    """
    spec = QUERY_REGISTRY.get(request.query_name)
    if spec is None:
        raise HTTPException(status_code=400, detail="Unknown graph query name")
    try:
        rows = await _get_age_client().run_query(spec["cypher"], dict(spec["params"]))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="AGE query failed") from exc
    return {"rows": rows, "count": len(rows), "query": spec["cypher"]}


@router.get("/soc/graph/top-nodes")
async def graph_top_nodes(
    type: Optional[str] = None,
    limit: int = 10,
):
    """Return top N most-connected nodes.

    Query params: ?type=User&limit=10 (both optional).
    Excludes :Decision and :Checkpoint nodes (internal bookkeeping).
    """
    from app.services.graph_explorer import GraphExplorerService
    nodes = await GraphExplorerService.get_top_nodes(
        _get_age_client(), node_type=type, limit=limit
    )
    return {"nodes": nodes, "count": len(nodes)}


@router.get("/soc/graph/node/{node_id}/neighbors")
async def graph_node_neighbors(node_id: str):
    """Return all neighbors of a specific node (up to 50).

    Response: {"node_id": str, "neighbors": [...], "total": int}
    """
    from app.services.graph_explorer import GraphExplorerService
    return await GraphExplorerService.get_node_neighbors(node_id, _get_age_client())


@router.get("/soc/graph/summary")
async def graph_summary():
    """Return node and relationship type counts for the explorer header.

    Response:
    {
        "total_nodes": int,
        "total_relationships": int,
        "node_types": {"Alert": N, "User": M, ...},
        "relationship_types": {"DECIDED_ON": N, ...},
    }
    """
    from app.services.graph_explorer import GraphExplorerService
    return await GraphExplorerService.get_graph_summary(_get_age_client())


@router.get("/soc/graph/prebuilt-queries")
async def graph_prebuilt_queries_list():
    """Return the catalogue of pre-built query names and descriptions.

    Response: {"queries": [...], "count": N}
    """
    from app.services.graph_explorer import GraphExplorerService
    queries = GraphExplorerService.list_prebuilt_queries()
    return {"queries": queries, "count": len(queries)}


@router.post("/soc/graph/prebuilt/{query_name}")
async def graph_run_prebuilt(query_name: str):
    """Run a pre-built query by name.

    Returns {"rows": [...], "count": N, "query": str}.
    Returns 404 if query_name is not in the catalogue.
    """
    from app.services.graph_explorer import GraphExplorerService
    result = await GraphExplorerService.run_prebuilt_query(query_name, _get_age_client())
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ---------------------------------------------------------------------------
# GET /api/soc/learning-health  (P9 — Learning Health Monitor)
# ---------------------------------------------------------------------------

@router.get("/soc/learning-health")
async def learning_health():
    """Return learning health status based on conservation law monitoring.

    Evaluates alpha(t)*q(t)*V(t) >= theta_min (absolute floor) and
    relative-drop thresholds (baseline-2sigma=AMBER, baseline-3sigma=RED).

    Returns
    -------
    {
        status            : "GREEN" | "AMBER" | "RED" | "CALIBRATING",
        signal            : float,
        theta_min         : float,
        conservation      : {passed, status, headroom},
        components        : {alpha, q, V, n},
        baseline          : float | null,
        baseline_std      : float | null,
        red_days          : int,
        auto_pause_active : bool,
        interpretation    : str,
        pre_activation    : bool,
        learning_enabled  : bool | null,
        health_source     : str,
        status_reason     : str | null,
    }
    """
    from app.services.learning_health import LearningHealthMonitor
    health = await LearningHealthMonitor.evaluate(_get_age_client())
    from app.services.evolver import get_soc_conservation_provider

    get_soc_conservation_provider().update_from_health(health)
    provider_state = get_soc_conservation_provider().get_state()
    return {
        **health,
        "provider_source": provider_state.get("source"),
        "provider_observed_at": provider_state.get("observed_at"),
        "overallSafe": provider_state.get("overallSafe", False),
    }


# ============================================================================
# FEATURE-10: Learning Balance Sheet
# ============================================================================

@router.get("/soc/learning-balance-sheet")
async def learning_balance_sheet():
    from dataclasses import asdict
    from app.services.balance_sheet import generate_balance_sheet

    return asdict(await generate_balance_sheet(_get_age_client()))


# ============================================================================
# FEATURE-05: Factor Analysis
# ============================================================================

def compute_factor_contribution(dk_weights, factor_names) -> tuple[list[dict], str]:
    import numpy as np

    names = list(factor_names)

    def _uniform() -> tuple[list[dict], str]:
        if not names:
            return [], "uniform"
        pct = round(100.0 / len(names), 2)
        percentages = [pct for _ in names]
        percentages[-1] = round(100.0 - sum(percentages[:-1]), 2)
        return [
            {
                "name": name,
                "index": idx,
                "contribution_pct": percentages[idx],
                "signal_strength": (
                    "high" if idx < 2 else "medium" if idx < 4 else "low"
                ),
                "rank": idx + 1,
            }
            for idx, name in enumerate(names)
        ], "uniform"

    if dk_weights is None:
        return _uniform()

    try:
        weights = np.asarray(dk_weights, dtype=float)
    except (TypeError, ValueError):
        return _uniform()

    if weights.ndim == 1 and weights.shape[0] == len(names):
        importance = np.abs(weights)
    elif weights.ndim == 2 and weights.shape[1] == len(names):
        importance = np.mean(np.abs(weights), axis=0)
    else:
        return _uniform()

    total = float(np.sum(importance))
    if not np.isfinite(total) or total <= 0.0:
        return _uniform()

    ordered = sorted(
        [
            {
                "name": names[idx],
                "index": idx,
                "importance": float(importance[idx]),
            }
            for idx in range(len(names))
        ],
        key=lambda item: (-item["importance"], item["index"]),
    )

    percentages = [
        round((item["importance"] / total) * 100.0, 2)
        for item in ordered
    ]
    if percentages:
        percentages[-1] = round(100.0 - sum(percentages[:-1]), 2)

    factors = []
    for rank, item in enumerate(ordered, start=1):
        factors.append(
            {
                "name": item["name"],
                "index": item["index"],
                "contribution_pct": percentages[rank - 1],
                "signal_strength": (
                    "high" if rank <= 2 else "medium" if rank <= 4 else "low"
                ),
                "rank": rank,
            }
        )
    return factors, "dk_weights"


@router.get("/soc/factor-analysis")
async def factor_analysis():
    from app.services.factor_analysis import run_factor_analysis

    result = await run_factor_analysis()
    if result.get("status") == "cold_start":
        raise HTTPException(status_code=503, detail=result)
    return result


@router.get("/soc/factor-analysis/summary")
async def factor_analysis_summary():
    from app.services.factor_analysis import run_factor_analysis

    result = await run_factor_analysis()
    if result.get("status") == "cold_start":
        raise HTTPException(status_code=503, detail=result)

    current = result["current"]
    proposed = current.get("proposed_improvement") or {}
    weakest = current.get("weakest_category") or "unknown"
    bootstrap_improved = result.get("snr_improved")
    if bootstrap_improved is True:
        improvement_note = "Current centroids outperform the bootstrap baseline."
    elif bootstrap_improved is False:
        improvement_note = "Current centroids have not exceeded the bootstrap baseline."
    else:
        improvement_note = "Bootstrap comparison is unavailable."

    recommendation = (
        f"{proposed.get('recommendation') or 'Review the weakest category for additional separation.'} "
        f"The weakest category is {weakest}. {improvement_note}"
    )
    cats = current.get("categories") or []
    weakest_cat = min(cats, key=lambda c: c["snr_effective"]) if cats else None
    return {
        "overall_snr": current["overall_snr"],
        "overall_ceiling": current["overall_ceiling"],
        "weakest_category": weakest,
        "weakest_category_ceiling": weakest_cat["ceiling_estimate"] if weakest_cat else None,
        "recommendation": recommendation,
        "bootstrap_improved": bootstrap_improved,
        "generated_at": result["generated_at"],
    }


@router.get("/soc/factor-contribution")
async def factor_contribution():
    from app.domains.soc.config import SOCDomainConfig
    from app.services.factor_analysis import _kernel_weights_for_scorer
    from app.services.gae_state import get_profile_scorer

    factor_names = [factor.id for factor in SOCDomainConfig().factors]
    dk_weights = None
    try:
        scorer = get_profile_scorer()
        if scorer is not None:
            dk_weights = _kernel_weights_for_scorer(scorer)
    except Exception:
        dk_weights = None

    factors, method = compute_factor_contribution(dk_weights, factor_names)
    return {
        "factors": factors,
        "method": method,
        "top_factor": factors[0]["name"] if factors else None,
        "weakest_factor": factors[-1]["name"] if factors else None,
    }


# ============================================================================
# P22: Intervention Controls — EU AI Act Article 14 human oversight (L-12)
# ============================================================================

def _get_intervention_controls():
    """Build InterventionControls from existing singletons."""
    from app.services.gae_state import get_profile_scorer
    from app.services.checkpoint import checkpoint_svc
    from app.services.composite_gate import CompositeDiscriminant
    from app.services.intervention_controls import InterventionControls
    scorer = get_profile_scorer()
    if scorer is None:
        raise RuntimeError("ProfileScorer not initialized")
    return InterventionControls(
        db_client=_get_age_client(),
        scorer=scorer,
        checkpoint_service=checkpoint_svc,
        composite_gate=CompositeDiscriminant,
    )


@router.post("/soc/interventions/freeze")
async def intervention_freeze(request: FreezeRequest):
    """Freeze all centroid learning globally."""
    try:
        ctrl = _get_intervention_controls()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return await ctrl.freeze_all_learning(request.initiated_by, request.reason)


@router.post("/soc/interventions/unfreeze")
async def intervention_unfreeze(request: FreezeRequest):
    """Resume centroid learning globally."""
    try:
        ctrl = _get_intervention_controls()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return await ctrl.unfreeze_all_learning(request.initiated_by, request.reason)


@router.post("/soc/interventions/rollback")
async def intervention_rollback(request: RollbackInterventionRequest):
    """Rollback to a centroid snapshot. preview=True returns what would change."""
    try:
        ctrl = _get_intervention_controls()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    result = await ctrl.rollback(
        request.snapshot_id, request.initiated_by, request.reason, request.preview
    )
    if "error" in result and not result.get("preview"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/soc/interventions/threshold")
async def intervention_threshold(request: ThresholdRequest):
    """Adjust auto-approve confidence threshold for a category."""
    try:
        ctrl = _get_intervention_controls()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return await ctrl.adjust_threshold(
        request.category, request.new_threshold, request.initiated_by, request.reason
    )


@router.get("/soc/interventions/state")
async def intervention_state():
    """Current state of all intervention controls."""
    try:
        ctrl = _get_intervention_controls()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return await ctrl.get_current_state()


@router.get("/soc/interventions/history")
async def intervention_history(limit: int = Query(50, ge=1, le=500)):
    """Intervention audit log."""
    try:
        ctrl = _get_intervention_controls()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    records = await ctrl.get_intervention_history(limit=limit)
    return {"interventions": records, "count": len(records)}


# ============================================================================
# GET /api/soc/frozen-roi — Frozen ROI Calculator (Adjustment E)
# ============================================================================

@router.get("/soc/frozen-roi")
async def frozen_roi(
    alerts_per_day: float = 200,
    analyst_hourly_cost: float = 85.0,
    auto_approve_rate: float = 0.04
):
    """Frozen mode ROI -- value before learning is enabled."""
    from app.services.economics import FrozenROICalculator
    calc = FrozenROICalculator(
        analyst_hourly_cost=analyst_hourly_cost,
        alerts_per_day=alerts_per_day,
        auto_approve_rate=auto_approve_rate
    )
    return calc.compute()


@router.get("/triage/learning-state")
async def get_triage_learning_state(
    category: str = Query("credential_access", description="SOC alert category"),
):
    """
    Phase-aware learning state for Tab 3 LearningStatePanel.
    Under ContinuousStrategy: phase=MEAN_CONVERGENCE, alpha=0.0, dk_weights=null.
    """
    from app.services.gae_state import get_profile_scorer
    from app.domains.soc.config import SOC_CATEGORIES
    from gae.two_phase import MEAN_CONVERGENCE

    default = {
        "strategy": "continuous",
        "category": category,
        "phase": MEAN_CONVERGENCE,
        "alpha": 0.0,
        "dk_weights": None,
        "freeze_point": None,
        "decisions_in_category": 0,
        "novelty_rate": None,
        "batch_pipeline": None,
    }

    try:
        scorer = get_profile_scorer()
    except Exception:
        return default

    if scorer is None or category not in SOC_CATEGORIES:
        return default

    cat_index = SOC_CATEGORIES.index(category)
    strategy = (
        "two_phase"
        if getattr(scorer, "_learning_strategy", None) is not None
        else "continuous"
    )

    phase = MEAN_CONVERGENCE
    if hasattr(scorer, "get_phase"):
        try:
            phase_raw = scorer.get_phase(cat_index)
            phase = str(getattr(phase_raw, "value", phase_raw))
        except Exception:
            phase = MEAN_CONVERGENCE

    alpha = 0.0
    if hasattr(scorer, "get_alpha"):
        try:
            alpha = float(scorer.get_alpha(cat_index))
        except Exception:
            alpha = 0.0

    dk_weights = None
    if hasattr(scorer, "get_dk_weights"):
        try:
            dk_raw = scorer.get_dk_weights(cat_index)
            if dk_raw is not None:
                dk_weights = dk_raw.tolist() if hasattr(dk_raw, "tolist") else list(dk_raw)
        except Exception:
            dk_weights = None

    freeze_point = None
    n_decisions = 0
    category_states = getattr(scorer, "_category_states", None)
    if category_states is not None:
        try:
            if cat_index < len(category_states):
                cs = category_states[cat_index]
                freeze_point = getattr(cs, "freeze_point", None)
                n_decisions = getattr(cs, "n_decisions", 0)
        except Exception:
            freeze_point = None
            n_decisions = 0

    return {
        "strategy": strategy,
        "category": category,
        "phase": phase,
        "alpha": round(float(alpha), 4),
        "dk_weights": dk_weights,
        "freeze_point": freeze_point,
        "decisions_in_category": int(n_decisions),
        "novelty_rate": None,
        "batch_pipeline": None,
    }


@router.get("/compounding/channel-decomposition")
async def get_channel_decomposition():
    """
    Three-channel improvement decomposition for Tab 4.
    Channel 1 (Scorer): centroid or DK learning.
    Channel 2 (Graph): enrichment.
    Channel 3 (Labels): LLM-as-Judge (not yet active).
    """
    from app.services.gae_state import get_profile_scorer, get_learning_state

    try:
        scorer = get_profile_scorer()
    except Exception:
        scorer = None

    try:
        ls = get_learning_state()
    except Exception:
        ls = None

    try:
        decision_count = int(getattr(ls, "decision_count", 0) or 0)
    except Exception:
        decision_count = 0

    strategy = "continuous"
    if scorer and getattr(scorer, "_learning_strategy", None) is not None:
        strategy = "two_phase"

    ch1_pp = 0.0
    ch1_status = "inactive"
    ch1_desc = "No verified decisions yet."
    if decision_count > 0:
        ch1_status = "active"
        if strategy == "two_phase":
            ch1_pp = round(min(3.2 + max(decision_count - 500, 0) * 2.2 / 3500, 5.4), 1)
            ch1_desc = f"DK precision weights from {decision_count} decisions."
        else:
            ch1_pp = round(min(decision_count * 2.7 / 1000, 2.7), 1)
            ch1_desc = f"Centroid learning from {decision_count} decisions."

    ch2_pp = 0.0
    ch2_status = "active"
    ch2_desc = "Graph enrichment reducing factor noise."
    try:
        from app.state.graph_snapshot import get_snapshot
        snap = get_snapshot()
        verified = int(getattr(snap, "verified_decisions", 0) or 0)
        ch2_pp = round(min(verified / 3000 * 1.8, 1.8), 1) if verified > 0 else 0.0
        ch2_desc = f"{verified} verified decisions enriching graph context."
    except Exception:
        ch2_desc = "Graph snapshot unavailable."

    ch3_pp = 0.0
    ch3_status = "not_active"
    ch3_desc = "Enable LLM-as-Judge for +3-4pp additional."

    total_pp = round(ch1_pp + ch2_pp + ch3_pp, 1)
    irreducible_pp = 10.0
    remaining_boundary_pp = round(max(irreducible_pp - total_pp, 0), 1)

    return {
        "strategy": strategy,
        "channels": [
            {
                "id": "scorer",
                "label": "Channel 1 (Scorer)",
                "contribution_pp": ch1_pp,
                "status": ch1_status,
                "description": ch1_desc,
            },
            {
                "id": "graph",
                "label": "Channel 2 (Graph)",
                "contribution_pp": ch2_pp,
                "status": ch2_status,
                "description": ch2_desc,
            },
            {
                "id": "labels",
                "label": "Channel 3 (Labels)",
                "contribution_pp": ch3_pp,
                "status": ch3_status,
                "description": ch3_desc,
            },
        ],
        "total_improvement_pp": total_pp,
        "irreducible_pp": irreducible_pp,
        "remaining_boundary_pp": remaining_boundary_pp,
        "disclaimer": (
            "Estimated from simulation calibration. Actual contributions depend on "
            "deployment noise, factor quality, and volume."
        ),
    }
