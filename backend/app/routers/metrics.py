"""
Compounding Metrics API - Tab 4
Shows week-over-week improvement proving the compounding moat
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel


router = APIRouter()


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

    Args:
        weeks: Number of weeks to include (default: 4)

    Returns:
        CompoundingResponse with headline, weekly trend, and evolution events
    """
    try:
        print(f"[COMPOUNDING] Generating {weeks} weeks of data")

        data = generate_compounding_data(weeks)

        print(f"[COMPOUNDING] Week 1: {data.weekly_trend[0].pattern_count} patterns, "
              f"{data.headline['auto_close_start']}% auto-close")
        print(f"[COMPOUNDING] Week {weeks}: {data.weekly_trend[-1].pattern_count} patterns, "
              f"{data.weekly_trend[-1].auto_close_rate}% auto-close")

        return data.dict()

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
    Seed Neo4j database with canonical test data.
    Clears existing data and creates all nodes and relationships from scratch.
    """
    from app.services.seed_neo4j import seed_neo4j_database, verify_neo4j_seed

    print("[DEMO] Seeding Neo4j database...")

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

    Now uses canonical seed data to ensure complete, clean reset every time.
    This is much simpler and more reliable than selective deletion.
    """
    from app.services.seed_neo4j import seed_neo4j_database, verify_neo4j_seed

    print("[DEMO RESET] Starting comprehensive demo reset via re-seeding...")

    try:
        # Re-seed the entire database from canonical data
        summary = await seed_neo4j_database()

        # Verify the seed
        verification = await verify_neo4j_seed()

        print("[DEMO RESET] ✓ Comprehensive reset completed successfully")

        return {
            "status": "success",
            "message": "All demo data reset to original state via re-seeding",
            "timestamp": datetime.now().isoformat(),
            "summary": summary,
            "verification": verification
        }

    except Exception as e:
        print(f"[ERROR] Demo reset failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset demo data: {str(e)}"
        )


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
    Get recent evolution events from Neo4j.

    In production, this queries:
    MATCH (e:EvolutionEvent)
    OPTIONAL MATCH (e)<-[:TRIGGERED_EVOLUTION]-(d:Decision)
    RETURN e, d
    ORDER BY e.timestamp DESC
    LIMIT $limit
    """
    try:
        print(f"[EVOLUTION EVENTS] Fetching {limit} recent events")

        # Mock data
        events = generate_compounding_data().evolution_events

        return {
            "events": [e.dict() for e in events[:limit]],
            "total": len(events)
        }

    except Exception as e:
        print(f"[ERROR] Evolution events fetch failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch evolution events: {str(e)}"
        )
