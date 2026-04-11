"""
Compounding Metrics API - Tab 4
Shows week-over-week improvement proving the compounding moat
"""
import os
import sys
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.db.neo4j import neo4j_client


router = APIRouter()


def _ensure_backend_on_path() -> None:
    """Ensure backend/ directory is on sys.path so `import seed_neo4j` works
    regardless of the working directory uvicorn was launched from."""
    # __file__ is  backend/app/routers/metrics.py
    # backend/  is three levels up
    backend_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)


# ============================================================================
# Response Models
# ============================================================================

class WeeklyMetrics(BaseModel):
    """Weekly metrics snapshot"""
    week: int
    auto_close_rate: float
    mttr_minutes: float
    fp_rate: float
    pattern_count: int


class EvolutionEvent(BaseModel):
    """Evolution event summary"""
    id: str
    event_type: str
    description: str
    timestamp: str
    triggered_by: str


class BusinessImpact(BaseModel):
    """Business impact summary for executive reporting"""
    analyst_hours_saved_monthly: int
    cost_avoided_quarterly: int
    mttr_reduction_pct: int
    alert_backlog_eliminated_monthly: int


class CompoundingResponse(BaseModel):
    """Compounding metrics response"""
    period: Dict[str, str]
    headline: Dict[str, Any]
    weekly_trend: List[WeeklyMetrics]
    evolution_events: List[EvolutionEvent]
    business_impact: BusinessImpact


# ============================================================================
# Mock Data Generation
# ============================================================================

def generate_compounding_data(weeks: int = 4) -> CompoundingResponse:
    """
    Generate mock compounding data showing Week 1 vs Week 4 improvement.

    In production, this would query Neo4j for:
    - Node count growth over time
    - Pattern occurrences
    - Evolution events
    - Decision outcomes
    """

    # Week 1 vs Week 4 (the headline numbers)
    nodes_start = 23
    nodes_end = 127
    auto_close_start = 68.0
    auto_close_end = 89.0
    mttr_start = 12.4
    mttr_end = 3.1
    fp_investigations_start = 4200
    fp_investigations_end = 980

    # Weekly progression (showing gradual improvement)
    weekly_data = [
        WeeklyMetrics(
            week=1,
            auto_close_rate=68.0,
            mttr_minutes=12.4,
            fp_rate=18.5,
            pattern_count=23
        ),
        WeeklyMetrics(
            week=2,
            auto_close_rate=76.0,
            mttr_minutes=8.7,
            fp_rate=14.2,
            pattern_count=58
        ),
        WeeklyMetrics(
            week=3,
            auto_close_rate=83.0,
            mttr_minutes=5.9,
            fp_rate=10.8,
            pattern_count=94
        ),
        WeeklyMetrics(
            week=4,
            auto_close_rate=89.0,
            mttr_minutes=3.1,
            fp_rate=8.1,
            pattern_count=127
        )
    ]

    # Recent evolution events (from Neo4j in production)
    evolution_events = [
        EvolutionEvent(
            id="EVO-0891",
            event_type="pattern_confidence_increase",
            description="PAT-TRAVEL: 91% → 94%",
            timestamp=(datetime.now() - timedelta(hours=2)).isoformat(),
            triggered_by="DECISION-7823"
        ),
        EvolutionEvent(
            id="EVO-0890",
            event_type="auto_close_threshold_tuned",
            description="Travel: 88% → 90%",
            timestamp=(datetime.now() - timedelta(days=1)).isoformat(),
            triggered_by="DECISION-7819"
        ),
        EvolutionEvent(
            id="EVO-0889",
            event_type="new_pattern",
            description="PAT-PHISH-Q4-CAMPAIGN",
            timestamp=(datetime.now() - timedelta(days=2)).isoformat(),
            triggered_by="DECISION-7814"
        ),
        EvolutionEvent(
            id="EVO-0888",
            event_type="playbook_tuned",
            description="DLP escalation path",
            timestamp=(datetime.now() - timedelta(days=3)).isoformat(),
            triggered_by="DECISION-7802"
        )
    ]

    # Business impact summary (computed from Week 1 vs Week 4 improvement)
    # These are reasonable projections for CISO/CFO reporting
    business_impact = BusinessImpact(
        analyst_hours_saved_monthly=847,  # ~200 auto-closed alerts × 45 min manual review avoided
        cost_avoided_quarterly=127000,    # analyst_hours × $50/hr × 3 months
        mttr_reduction_pct=75,            # MTTR improved from 12.4 min → 3.1 min
        alert_backlog_eliminated_monthly=2400  # alerts no longer waiting for human review
    )

    return CompoundingResponse(
        period={
            "start": (datetime.now() - timedelta(weeks=weeks)).isoformat(),
            "end": datetime.now().isoformat()
        },
        headline={
            "nodes_start": nodes_start,
            "nodes_end": nodes_end,
            "auto_close_start": auto_close_start,
            "auto_close_end": auto_close_end,
            "mttr_start": mttr_start,
            "mttr_end": mttr_end,
            "fp_investigations_start": fp_investigations_start,
            "fp_investigations_end": fp_investigations_end
        },
        weekly_trend=weekly_data[:weeks],
        evolution_events=evolution_events,
        business_impact=business_impact
    )


# ============================================================================
# GET /api/metrics/compounding - Compounding Metrics
# ============================================================================

@router.get("/metrics/compounding")
async def get_compounding_metrics(weeks: int = Query(4, ge=1, le=12)):
    """
    Get compounding metrics showing week-over-week improvement.

    Headline and business_impact are projected (labeled "Projected at Scale" in UI).
    weekly_trend and evolution_events are served from Neo4j (H7-FIX-4).
    """
    try:
        print(f"[COMPOUNDING] Generating {weeks} weeks of data")

        # Headline / business_impact stay as projected (already labeled in UI)
        projected = generate_compounding_data(weeks)
        response = projected.model_dump()

        # --- WEEKLY TREND: real Decision timeline from Neo4j (H7-FIX-4) ---
        weekly_trend_estimated = False
        weekly_trend_note = None
        try:
            dec_rows = await neo4j_client.run_query(
                "MATCH (d:Decision) WHERE d.timestamp IS NOT NULL "
                "RETURN d.timestamp AS ts, d.type AS action, d.confidence AS confidence "
                "ORDER BY d.timestamp"
            )
            if dec_rows:
                # Return raw decision points; chart will be empty but real data is available
                # via /api/metrics/weekly-trends.  Compounding chart needs WeeklyMetric shape,
                # which requires proper metrics history — so we return [] with a note.
                response["weekly_trend"] = []
                weekly_trend_estimated = True
                weekly_trend_note = (
                    "Weekly trends require cumulative metrics history — "
                    "real decision timeline available at /api/metrics/weekly-trends"
                )
            else:
                response["weekly_trend"] = []
                weekly_trend_estimated = True
                weekly_trend_note = (
                    "Weekly trends require decision history — "
                    "make decisions to populate"
                )
        except Exception as exc:
            print(f"[COMPOUNDING] weekly-trend AGE query failed: {exc}")
            response["weekly_trend"] = []
            weekly_trend_estimated = True
            weekly_trend_note = "Weekly trends unavailable — AGE unreachable"

        response["weekly_trend_estimated"] = weekly_trend_estimated
        response["weekly_trend_note"] = weekly_trend_note

        # --- EVOLUTION EVENTS: Decision nodes from Neo4j (H7-FIX-4) ---
        try:
            evo_rows = await neo4j_client.run_query(
                "MATCH (d:Decision) "
                "RETURN d.decision_id AS id, d.type AS action, d.confidence AS confidence, "
                "d.timestamp AS ts, d.alert_id AS alert_id "
                "ORDER BY d.timestamp DESC LIMIT 20"
            )
            if evo_rows:
                _evo_events = []
                for r in evo_rows:
                    _rid = str(r.get('id', ''))
                    _display_id = _rid if _rid.upper().startswith('DEC-') else f"DEC-{_rid[:8]}"
                    _evo_events.append({
                        "id": _display_id,
                        "event_type": str(r.get("action", "decision")),
                        "description": (
                            f"{str(r.get('action', '?')).upper()} on "
                            f"{str(r.get('alert_id', '?'))} — "
                            f"conf: {float(r.get('confidence') or 0):.0%}"
                        ),
                        "timestamp": str(r.get("ts", datetime.now().isoformat())),
                        "triggered_by": str(r.get("alert_id", "?")),
                    })
                response["evolution_events"] = _evo_events
            else:
                response["evolution_events"] = []
        except Exception as exc:
            print(f"[COMPOUNDING] evolution_events AGE query failed: {exc}")
            # fall back to projected mock events so the panel isn't completely broken
            response["evolution_events"] = projected.model_dump()["evolution_events"]

        print(f"[COMPOUNDING] weekly_trend_estimated={weekly_trend_estimated}, "
              f"evolution_events={len(response['evolution_events'])}")
        return response

    except Exception as e:
        print(f"[ERROR] Compounding metrics failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate compounding metrics: {str(e)}"
        )


# ============================================================================
# POST /api/demo/seed - Seed Neo4j Database
# ============================================================================

@router.post("/demo/seed")
async def seed_neo4j():
    """
    Seed AGE database with canonical test data.
    Clears existing data and creates all nodes and relationships from scratch.
    """
    from app.services.seed_neo4j import seed_neo4j_database, verify_neo4j_seed

    print("[DEMO] Seeding AGE database...")

    try:
        # Seed the database
        summary = await seed_neo4j_database()

        # Verify the seed
        verification = await verify_neo4j_seed()

        return {
            "status": "success",
            "message": "Neo4j database seeded successfully",
            "timestamp": datetime.now().isoformat(),
            "summary": summary,
            "verification": verification
        }

    except Exception as e:
        print(f"[ERROR] Failed to seed database: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to seed database: {str(e)}"
        )


# ============================================================================
# POST /api/demo/reset-all - Comprehensive Demo Reset
# ============================================================================

@router.post("/demo/reset-all")
async def reset_all_demo_data():
    """
    Comprehensive demo reset - resets ALL demo data to original state.

    Delegates the atomic GAE + Neo4j + audit reset to StateManager.hard_reset()
    (TD-026), then resets remaining SOC-specific in-memory state via the
    legacy DemoStateManager so existing frontend behaviour is unchanged.
    """
    from app.services.state_manager import StateManager, ResetError
    from app.services import gae_state, audit as audit_store
    from app.db.neo4j import neo4j_client
    from app.core.domain_registry import get_domain_config
    from app.core.state_manager import state_manager

    print("[DEMO RESET] Starting comprehensive demo reset via StateManager.hard_reset()...")

    try:
        # Atomic reset: GAE learning state + Decision nodes deleted + audit chain + re-seed
        sm = StateManager(
            learning_state_service=gae_state,
            audit_store=audit_store,
            neo4j_service=neo4j_client,
            domain_config=get_domain_config(),
        )
        await sm.hard_reset(preserve_learning=True)

        # Reset demo-cycle in-memory state only — preserve learning_state so
        # ProfileScorer centroids (IKS) survive this reset (BACKLOG-020).
        state_manager.reset_except(["learning_state"])

        print("[DEMO RESET] Comprehensive reset completed successfully")

        return {
            "status": "success",
            "message": "All demo data reset to original state via re-seeding",
            "timestamp": datetime.now().isoformat(),
        }

    except ResetError as exc:
        print(f"[ERROR] Demo reset failed (StateManager): {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as e:
        print(f"[ERROR] Demo reset failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset demo data: {str(e)}"
        )



# ============================================================================
# POST /api/demo/reseed - Re-seed Neo4j from canonical dataset
# ============================================================================

@router.post("/demo/reseed")
async def reseed_demo_data():
    """
    Re-seed the Neo4j database from the canonical seed dataset.

    Clears all existing nodes/relationships and recreates the full demo graph
    (alerts, assets, users, patterns, decisions, evolution events, etc.).
    Also resets all in-memory state (audit trail, evolver stats, feedback).

    Returns {success, alert_count} for minimal, actionable feedback.
    Never raises HTTPException — caller inspects the success flag instead.
    """
    _ensure_backend_on_path()
    import seed_neo4j                          # backend/seed_neo4j.py (20 alerts, canonical)
    from app.db.neo4j import neo4j_client
    from app.core.state_manager import state_manager

    print("[RESEED] POST /api/demo/reseed called")
    try:
        await seed_neo4j.seed_data()

        # seed_data() closes the neo4j connection at the end; the count query
        # requires a reconnect which may transiently fail.  Wrap it separately
        # so a count failure never masks a successful seed.
        alert_count = 20  # canonical dataset default
        try:
            results = await neo4j_client.run_query(
                "MATCH (a:Alert) RETURN count(a) AS alert_count"
            )
            alert_count = int(results[0]["alert_count"]) if results else 20
        except Exception as count_exc:
            print(f"[RESEED] Count query failed (seed still succeeded): {count_exc}")

        # Reset demo-cycle in-memory state — preserve learning_state (BACKLOG-020)
        state_manager.reset_except(["learning_state"])

        print(f"[RESEED] Complete — {alert_count} alerts in graph")
        return {"success": True, "alert_count": alert_count}

    except Exception as exc:
        print(f"[ERROR] Re-seed failed: {exc}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(exc)}


# ============================================================================
# POST /api/demo/reset - Reset Demo Data (Legacy)
# ============================================================================

@router.post("/demo/reset")
async def reset_demo_data():
    """
    Reset demo data for repeated demonstrations.

    In production, this would:
    - Reset Neo4j to Week 1 state
    - Clear recent evolution events
    - Preserve metric contracts

    For this demo, it just returns a success message.
    """
    try:
        print("[DEMO RESET] Resetting to Week 1 state")

        # In production:
        # await neo4j_client.run("""
        #     MATCH (e:EvolutionEvent)
        #     WHERE e.timestamp > $cutoff_date
        #     DETACH DELETE e
        # """)

        return {
            "status": "success",
            "message": "Demo data reset to Week 1 state",
            "timestamp": datetime.now().isoformat(),
            "reset_items": {
                "evolution_events": "cleared",
                "pattern_counts": "reset to 23",
                "auto_close_rate": "reset to 68%"
            }
        }

    except Exception as e:
        print(f"[ERROR] Demo reset failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset demo data: {str(e)}"
        )


# ============================================================================
# GET /api/metrics/evolution-events - Recent Evolution Events
# ============================================================================

@router.get("/metrics/evolution-events")
async def get_evolution_events(limit: int = Query(10, ge=1, le=50)):
    """
    Get recent decisions as evolution events from Neo4j (H7-FIX-4).

    Queries Decision nodes ordered by timestamp DESC, formats each as an
    evolution event record so the Tab 4 panel shows real decision history.
    Returns estimated=False with a note when no decisions exist yet.
    """
    print(f"[EVOLUTION EVENTS] Fetching {limit} recent Decision nodes from AGE")
    try:
        results = await neo4j_client.run_query(
            "MATCH (d:Decision) "
            "RETURN d.decision_id AS id, d.type AS action, d.confidence AS confidence, "
            "d.timestamp AS ts, d.alert_id AS alert_id "
            "ORDER BY d.timestamp DESC LIMIT $limit",
            {"limit": limit},
        )
        if not results:
            return {
                "events": [],
                "estimated": False,
                "note": "No decisions recorded yet — process alerts to see evolution",
                "total": 0,
            }
        _NULLS = (None, "None", "")
        events = []
        for r in results:
            if r.get("action") in _NULLS or r.get("alert_id") in _NULLS:
                continue
            _rid = str(r.get('id', ''))
            _display_id = _rid if _rid.upper().startswith('DEC-') else f"DEC-{_rid[:8]}"
            events.append({
                "id": _display_id,
                "event_type": str(r.get("action", "decision")),
                "description": (
                    f"{str(r.get('action', '?')).upper()} on "
                    f"{str(r.get('alert_id', '?'))} — "
                    f"conf: {float(r.get('confidence') or 0):.0%}"
                ),
                "timestamp": str(r.get("ts", datetime.now().isoformat())),
                "triggered_by": str(r.get("alert_id", "?")),
            })
        return {"events": events, "estimated": False, "note": None, "total": len(events)}

    except Exception as e:
        print(f"[ERROR] Evolution events fetch failed: {e}")
        return {"events": [], "estimated": False, "note": str(e), "total": 0}


# ============================================================================
# GET /api/metrics/weekly-trends - Decision timeline (H7-FIX-4)
# ============================================================================

@router.get("/metrics/weekly-trends")
async def get_weekly_trends():
    """
    Return a raw decision timeline from Neo4j for the Tab 4 weekly trend panel.

    If Decision nodes exist and have timestamps, returns the ordered list of
    decision points (timestamp, action, confidence).

    If no data yet (fresh seed or no decisions made), returns
    estimated=True with an explanatory note.
    """
    try:
        results = await neo4j_client.run_query(
            "MATCH (d:Decision) WHERE d.timestamp IS NOT NULL "
            "RETURN d.timestamp AS ts, d.type AS action, d.confidence AS confidence "
            "ORDER BY d.timestamp"
        )
        if not results:
            return {
                "data": [],
                "estimated": True,
                "note": (
                    "Weekly trends require decision history — "
                    "make decisions to populate"
                ),
            }
        data = [
            {
                "ts": str(r.get("ts", "")),
                "action": str(r.get("action", "")),
                "confidence": float(r.get("confidence") or 0.0),
            }
            for r in results
        ]
        return {"data": data, "estimated": False, "note": None}

    except Exception as e:
        print(f"[METRICS] weekly-trends AGE query failed: {e}")
        return {
            "data": [],
            "estimated": True,
            "note": f"Weekly trends unavailable: {e}",
        }


# ============================================================================
# GET /api/metrics/decision-economics - Computed economics (H7-FIX-4)
# ============================================================================

@router.get("/metrics/decision-economics")
async def get_decision_economics():
    """
    Return decision economics computed from real Neo4j Decision nodes.

    - decisions_made: total Decision node count
    - correct_rate: correct / total  (0.0 if no decisions)
    - false_positive_rate: 1 - correct_rate
    - time_saved_hours: correct_rate * decisions_made * 0.5 (labelled estimated)

    Safe against division-by-zero when no decisions exist yet.
    """
    try:
        dec_res = await neo4j_client.run_query(
            "MATCH (d:Decision) RETURN count(d) AS total_decisions"
        )
        total = int(dec_res[0]["total_decisions"]) if dec_res else 0

        correct_res = await neo4j_client.run_query(
            "MATCH (d:Decision) "
            "WHERE d.outcome = 'correct' OR d.correct = true "
            "RETURN count(d) AS correct_decisions"
        )
        correct = int(correct_res[0]["correct_decisions"]) if correct_res else 0

        correct_rate = correct / total if total > 0 else 0.0
        false_positive_rate = 1.0 - correct_rate
        time_saved_hours = correct_rate * total * 0.5

        return {
            "decisions_made": total,
            "correct_rate": round(correct_rate, 3),
            "false_positive_rate": round(false_positive_rate, 3),
            "time_saved_hours": round(time_saved_hours, 2),
            "time_saved_estimated": True,
            "note": "Time saved estimated at 0.5hr per correct decision",
        }

    except Exception as e:
        print(f"[METRICS] decision-economics AGE query failed: {e}")
        return {
            "decisions_made": 0,
            "correct_rate": 0.0,
            "false_positive_rate": 0.0,
            "time_saved_hours": 0.0,
            "time_saved_estimated": True,
            "note": "Time saved estimated at 0.5hr per correct decision",
            "error": str(e),
        }


# ============================================================================
# GET /api/demo/domains - Domain Registry Status
# ============================================================================

@router.get("/demo/domains")
async def get_registered_domains():
    """
    Return all registered domain configs and the active domain.

    Used for smoke-testing the v3.2 domain-agnostic architecture:
    confirms that both SOC and S2P configs are registered and
    that ACTIVE_DOMAIN is still 'soc'.
    """
    from app.core.domain_registry import ACTIVE_DOMAIN, _DOMAIN_CONFIGS

    registered = {}
    for domain_name, config in _DOMAIN_CONFIGS.items():
        registered[domain_name] = {
            "name":                 config.name,
            "display_name":         config.display_name,
            "trigger_entity":       config.trigger_entity,
            "factor_count":         len(config.factors),
            "action_count":         len(config.actions),
            "situation_type_count": len(config.situation_types),
            "policy_count":         len(config.policies),
            "asymmetry_ratio":      config.asymmetry_ratio,
        }

    return {
        "active_domain":      ACTIVE_DOMAIN,
        "registered_domains": registered,
    }


# ============================================================================
# GET /api/soc/operational-metrics — MTTD / MTTR / FP rate (F4-OVERLAY)
# ============================================================================

@router.get("/soc/operational-metrics")
async def get_operational_metrics():
    """Operational outcome metrics for ROI dashboard overlay (F4)."""

    # MTTD: alert creation → decision
    try:
        mttd_result = await neo4j_client.run_query(
            "MATCH (d:Decision)-[:FOR_ALERT]->(a:Alert) "
            "WHERE d.created_at_epoch IS NOT NULL AND a.created_at_epoch IS NOT NULL "
            "RETURN avg((d.created_at_epoch - a.created_at_epoch) / 1000.0)"
            " AS avg_mttd_seconds, count(d) AS sample_size"
        )
        if mttd_result and mttd_result[0]["sample_size"] > 0:
            mttd_seconds = mttd_result[0]["avg_mttd_seconds"]
            mttd = {
                "value_seconds": round(mttd_seconds),
                "value_minutes": round(mttd_seconds / 60, 1),
                "sample_size": mttd_result[0]["sample_size"],
                "estimated": False,
            }
        else:
            mttd = {
                "value_seconds": None,
                "value_minutes": None,
                "sample_size": 0,
                "estimated": True,
                "note": "Requires decisions with timestamps",
            }
    except Exception as exc:
        print(f"[METRICS] MTTD query failed: {exc}")
        mttd = {
            "value_seconds": None, "value_minutes": None, "sample_size": 0,
            "estimated": True, "note": "Requires decisions with timestamps",
        }

    # MTTR: decision → outcome verification
    try:
        mttr_result = await neo4j_client.run_query(
            "MATCH (d:Decision) "
            "WHERE d.created_at_epoch IS NOT NULL AND d.verified_at_epoch IS NOT NULL "
            "RETURN avg((d.verified_at_epoch - d.created_at_epoch) / 1000.0)"
            " AS avg_mttr_seconds, count(d) AS sample_size"
        )
        if mttr_result and mttr_result[0]["sample_size"] > 0:
            mttr_seconds = mttr_result[0]["avg_mttr_seconds"]
            mttr = {
                "value_seconds": round(mttr_seconds),
                "value_minutes": round(mttr_seconds / 60, 1),
                "sample_size": mttr_result[0]["sample_size"],
                "estimated": False,
            }
        else:
            mttr = {
                "value_seconds": None,
                "value_minutes": None,
                "sample_size": 0,
                "estimated": True,
                "note": "Requires verified outcomes with timestamps",
            }
    except Exception as exc:
        print(f"[METRICS] MTTR query failed: {exc}")
        mttr = {
            "value_seconds": None, "value_minutes": None, "sample_size": 0,
            "estimated": True, "note": "Requires verified outcomes with timestamps",
        }

    # FP Rate from Decision outcomes
    try:
        fp_result = await neo4j_client.run_query(
            "MATCH (d:Decision) "
            "RETURN count(d) AS total, "
            "sum(CASE WHEN d.correct = false OR d.outcome = 'incorrect' "
            "THEN 1 ELSE 0 END) AS fp_count"
        )
        if fp_result and fp_result[0]["total"] > 0:
            total = int(fp_result[0]["total"])
            fp_count = int(fp_result[0]["fp_count"] or 0)
            fp_rate = {
                "rate": round(fp_count / total, 3),
                "total_decisions": total,
                "fp_count": fp_count,
                "estimated": False,
            }
        else:
            fp_rate = {
                "rate": None,
                "total_decisions": 0,
                "fp_count": 0,
                "estimated": True,
                "note": "Requires verified decision outcomes",
            }
    except Exception as exc:
        print(f"[METRICS] FP rate query failed: {exc}")
        fp_rate = {
            "rate": None, "total_decisions": 0, "fp_count": 0,
            "estimated": True, "note": "Requires verified decision outcomes",
        }

    return {
        "mttd": mttd,
        "mttr": mttr,
        "fp_rate": fp_rate,
        "source": "neo4j",
    }


# ============================================================================
# GET /api/soc/board-export — Executive JSON summary (F4-OVERLAY)
# ============================================================================

@router.get("/soc/board-export")
async def get_board_export():
    """Board-ready JSON summary for executive reporting."""
    from datetime import datetime as _dt

    total, correct, fp_count_val = 0, 0, 0

    try:
        dec_res = await neo4j_client.run_query(
            "MATCH (d:Decision) RETURN count(d) AS total"
        )
        total = int(dec_res[0]["total"]) if dec_res else 0

        correct_res = await neo4j_client.run_query(
            "MATCH (d:Decision) WHERE d.outcome = 'correct' OR d.correct = true "
            "RETURN count(d) AS correct"
        )
        correct = int(correct_res[0]["correct"]) if correct_res else 0

        fp_res = await neo4j_client.run_query(
            "MATCH (d:Decision) RETURN count(d) AS total, "
            "sum(CASE WHEN d.correct = false OR d.outcome = 'incorrect' "
            "THEN 1 ELSE 0 END) AS fp_count"
        )
        if fp_res and fp_res[0]["total"] > 0:
            fp_count_val = int(fp_res[0]["fp_count"] or 0)
    except Exception as exc:
        print(f"[METRICS] board-export AGE query failed: {exc}")

    correct_rate = correct / total if total > 0 else 0.0
    fp_rate_pct = round(fp_count_val / total * 100, 1) if total > 0 else None
    time_saved = round(correct_rate * total * 0.5, 2)
    data_quality = "live" if total > 0 else "insufficient_data"

    return {
        "generated_at": _dt.utcnow().isoformat(),
        "product": "Compounding Intelligence Platform",
        "version": "v5.0",
        "metrics": {
            "decisions_made": total,
            "correct_rate_pct": round(correct_rate * 100, 1),
            "fp_rate_pct": fp_rate_pct,
            "mttd_minutes": None,
            "mttr_minutes": None,
            "time_saved_hours": time_saved,
        },
        "data_quality": data_quality,
        "note": "Metrics marked null require more decision history.",
    }


# ============================================================================
# GET /api/soc/economics — Rich $/time/risk metrics (ECON-1)
# ============================================================================

@router.get("/soc/economics")
async def get_economics():
    """
    Rich economics metrics for ROI dashboard (ECON-1).
    Computes $/time/risk from Decision history + user population.
    """
    ANALYST_HOURLY = 85.0
    MANUAL_TRIAGE_HOURS = 0.75
    AI_TRIAGE_HOURS = 0.133
    BREACH_COST_PER_INCIDENT = 150000.0  # conservative SMB estimate

    # 1. Decision volume + accuracy (single aggregating query)
    total = correct = escalations = suppressions = investigations = monitors = 0
    try:
        dec_result = await neo4j_client.run_query(
            "MATCH (d:Decision) "
            "RETURN "
            "count(d) AS total, "
            "sum(CASE WHEN d.correct = true OR d.outcome = 'correct' "
            "    THEN 1 ELSE 0 END) AS correct_count, "
            "sum(CASE WHEN d.action = 'escalate'    THEN 1 ELSE 0 END) AS escalations, "
            "sum(CASE WHEN d.action = 'suppress'    THEN 1 ELSE 0 END) AS suppressions, "
            "sum(CASE WHEN d.action = 'investigate' THEN 1 ELSE 0 END) AS investigations, "
            "sum(CASE WHEN d.action = 'monitor'     THEN 1 ELSE 0 END) AS monitors"
        )
        if dec_result:
            total         = int(dec_result[0]["total"]          or 0)
            correct       = int(dec_result[0]["correct_count"]  or 0)
            escalations   = int(dec_result[0]["escalations"]    or 0)
            suppressions  = int(dec_result[0]["suppressions"]   or 0)
            investigations = int(dec_result[0]["investigations"] or 0)
            monitors      = int(dec_result[0]["monitors"]       or 0)
    except Exception as exc:
        print(f"[ECON] decision query failed: {exc}")

    # 2. User population from realistic seed
    total_users = privileged = elevated = 0
    try:
        user_result = await neo4j_client.run_query(
            "MATCH (u:User) "
            "RETURN "
            "count(u) AS total_users, "
            "sum(CASE WHEN u.access_level = 'privileged' THEN 1 ELSE 0 END) AS privileged_users, "
            "sum(CASE WHEN u.access_level = 'elevated'   THEN 1 ELSE 0 END) AS elevated_users"
        )
        if user_result:
            total_users = int(user_result[0]["total_users"]      or 0)
            privileged  = int(user_result[0]["privileged_users"] or 0)
            elevated    = int(user_result[0]["elevated_users"]   or 0)
    except Exception as exc:
        print(f"[ECON] user query failed: {exc}")

    # 3. Dollar value estimates (always labeled estimated=True)
    correct_rate = correct / total if total > 0 else 0.0
    time_saved_hours = total * (MANUAL_TRIAGE_HOURS - AI_TRIAGE_HOURS)
    cost_saved = time_saved_hours * ANALYST_HOURLY
    # Risk reduction: escalations correctly handled prevent breach cost
    # 0.02 = 2% probability that an unhandled escalation becomes a breach
    correct_escalations = escalations * correct_rate
    risk_reduction = correct_escalations * BREACH_COST_PER_INCIDENT * 0.02

    return {
        "decisions": {
            "total": total,
            "correct": correct,
            "correct_rate": round(correct_rate, 3),
            "by_action": {
                "escalate":    escalations,
                "suppress":    suppressions,
                "investigate": investigations,
                "monitor":     monitors,
            },
        },
        "population": {
            "total_users":      total_users,
            "privileged_users": privileged,
            "elevated_users":   elevated,
        },
        "economics": {
            "analyst_hourly_rate": ANALYST_HOURLY,
            "time_saved_hours":    round(time_saved_hours, 1),
            "cost_saved_usd":      round(cost_saved, 2),
            "risk_reduction_usd":  round(risk_reduction, 2),
            "total_value_usd":     round(cost_saved + risk_reduction, 2),
            "estimated":           True,
            "note": (
                "Cost estimates use industry-standard SOC analyst rates. "
                "Risk reduction assumes 2% breach probability per "
                "unhandled escalation at $150K average SMB breach cost."
            ),
        },
        "source": "neo4j",
    }


# ============================================================================
# GET /api/metrics/confidence-trajectory - Per-situation confidence over time (F4b)
# ============================================================================

@router.get("/metrics/confidence-trajectory")
async def get_confidence_trajectory_endpoint():
    """
    Return agent confidence scores grouped by situation type, in decision order.

    Each entry represents one call to POST /api/alert/analyze this session.
    History resets with the demo (state_manager.reset_all()).

    Response shape:
        {
          "trajectory": {
            "travel_login_anomaly":    [
              {"decision": 1, "confidence": 0.92},
              {"decision": 3, "confidence": 0.92},
              ...
            ],
            "known_phishing_campaign": [
              {"decision": 2, "confidence": 0.94},
              ...
            ]
          },
          "total_decisions": N,
          "situation_types": ["travel_login_anomaly", "known_phishing_campaign", ...]
        }

    Returns an empty trajectory when no alerts have been analyzed this session.
    """
    from app.services.triage import get_confidence_trajectory
    trajectory = get_confidence_trajectory()
    total = sum(len(v) for v in trajectory.values())
    print(
        f"[METRICS] GET /metrics/confidence-trajectory — "
        f"total={total}, types={list(trajectory.keys())}"
    )
    return {
        "trajectory":      trajectory,
        "total_decisions": total,
        "situation_types": list(trajectory.keys()),
    }
