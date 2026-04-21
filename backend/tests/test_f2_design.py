"""
F2-DESIGN tests: Detection Engineering Feedback
Rule Quality Score (centroid drift) + Noise Map (per-category FP rate).

Run from backend/ directory:
    pytest tests/test_f2_design.py -v
"""

import asyncio
import sys
import os
from unittest.mock import patch, AsyncMock, MagicMock

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ============================================================================
# TEST 1 — Detection engineering endpoint registered
# ============================================================================

def test_detection_engineering_endpoint_registered():
    """GET /api/soc/detection-engineering must be registered on the app."""
    from app.main import app
    routes = [r.path for r in app.routes]
    assert "/api/soc/detection-engineering" in routes, (
        f"Route not found; registered routes: {routes}"
    )


# ============================================================================
# TEST 2 — Quality score stable at baseline (zero drift)
# ============================================================================

def test_quality_score_stable_at_baseline():
    """Mock scorer.centroids == SOC_PROFILE_CENTROIDS (zero drift).
    All category quality_scores must equal 1.0 and status == 'stable'."""
    from app.routers.soc import get_detection_engineering
    from app.domains.soc.config import SOC_PROFILE_CENTROIDS, SOC_CATEGORIES

    mock_scorer = MagicMock()
    mock_scorer.centroids = SOC_PROFILE_CENTROIDS.copy()

    async def _run():
        with patch("app.services.gae_state.get_profile_scorer", return_value=mock_scorer):
            with patch("app.routers.soc.neo4j_client") as mock_neo:
                mock_neo.run_query = AsyncMock(
                    side_effect=[[] for _ in SOC_CATEGORIES]
                )
                return await get_detection_engineering()

    result = asyncio.run(_run())
    for s in result["category_scores"]:
        assert s["quality_score"] == 1.0, (
            f"{s['category']} quality_score != 1.0: got {s['quality_score']}"
        )
        assert s["status"] == "stable", (
            f"{s['category']} status != 'stable': got {s['status']}"
        )


# ============================================================================
# TEST 3 — Quality score drifting (moderate drift = 0.10)
# ============================================================================

def test_quality_score_drifting():
    """Mock scorer.centroids = SOC_PROFILE_CENTROIDS + 0.10 (drift=0.10).
    All statuses must be 'drifting'."""
    from app.routers.soc import get_detection_engineering
    from app.domains.soc.config import SOC_PROFILE_CENTROIDS, SOC_CATEGORIES

    mock_scorer = MagicMock()
    mock_scorer.centroids = SOC_PROFILE_CENTROIDS + 0.10

    async def _run():
        with patch("app.services.gae_state.get_profile_scorer", return_value=mock_scorer):
            with patch("app.routers.soc.neo4j_client") as mock_neo:
                mock_neo.run_query = AsyncMock(
                    side_effect=[[] for _ in SOC_CATEGORIES]
                )
                return await get_detection_engineering()

    result = asyncio.run(_run())
    for s in result["category_scores"]:
        assert s["status"] == "drifting", (
            f"{s['category']} status != 'drifting': got {s['status']} (drift={s['drift']})"
        )


# ============================================================================
# TEST 4 — Quality score diverged (large drift = 0.20)
# ============================================================================

def test_quality_score_diverged():
    """Mock scorer.centroids = SOC_PROFILE_CENTROIDS + 0.20 (drift=0.20).
    All statuses must be 'diverged'."""
    from app.routers.soc import get_detection_engineering
    from app.domains.soc.config import SOC_PROFILE_CENTROIDS, SOC_CATEGORIES

    mock_scorer = MagicMock()
    mock_scorer.centroids = SOC_PROFILE_CENTROIDS + 0.20

    async def _run():
        with patch("app.services.gae_state.get_profile_scorer", return_value=mock_scorer):
            with patch("app.routers.soc.neo4j_client") as mock_neo:
                mock_neo.run_query = AsyncMock(
                    side_effect=[[] for _ in SOC_CATEGORIES]
                )
                return await get_detection_engineering()

    result = asyncio.run(_run())
    for s in result["category_scores"]:
        assert s["status"] == "diverged", (
            f"{s['category']} status != 'diverged': got {s['status']} (drift={s['drift']})"
        )


# ============================================================================
# TEST 5 — Overall quality is mean of category scores (rounded to 3dp)
# ============================================================================

def test_overall_quality_is_mean_of_categories():
    """Given any known drift, overall_quality_score must equal
    round(mean(category quality_scores), 3)."""
    from app.routers.soc import get_detection_engineering
    from app.domains.soc.config import SOC_PROFILE_CENTROIDS, SOC_CATEGORIES

    mock_scorer = MagicMock()
    mock_scorer.centroids = SOC_PROFILE_CENTROIDS + 0.07  # asymmetric drift value

    async def _run():
        with patch("app.services.gae_state.get_profile_scorer", return_value=mock_scorer):
            with patch("app.routers.soc.neo4j_client") as mock_neo:
                mock_neo.run_query = AsyncMock(
                    side_effect=[[] for _ in SOC_CATEGORIES]
                )
                return await get_detection_engineering()

    result = asyncio.run(_run())
    scores = result["category_scores"]
    expected = round(
        sum(s["quality_score"] for s in scores) / len(scores), 3
    )
    assert result["overall_quality_score"] == expected, (
        f"Expected overall={expected}, got {result['overall_quality_score']}"
    )


# ============================================================================
# TEST 6 — Noise map null when no decisions
# ============================================================================

def test_noise_map_null_when_no_decisions():
    """Mock Neo4j returning total=0 for all categories.
    All fp_rate must be None and estimated=True."""
    from app.routers.soc import get_detection_engineering
    from app.domains.soc.config import SOC_PROFILE_CENTROIDS, SOC_CATEGORIES

    mock_scorer = MagicMock()
    mock_scorer.centroids = SOC_PROFILE_CENTROIDS.copy()

    async def _run():
        with patch("app.services.gae_state.get_profile_scorer", return_value=mock_scorer):
            with patch("app.routers.soc.neo4j_client") as mock_neo:
                mock_neo.run_query = AsyncMock(
                    side_effect=[[] for _ in SOC_CATEGORIES]
                )
                return await get_detection_engineering()

    result = asyncio.run(_run())
    for entry in result["noise_map"]:
        assert entry["fp_rate"] is None, (
            f"{entry['category']} fp_rate should be None, got {entry['fp_rate']}"
        )
        assert entry["estimated"] is True, (
            f"{entry['category']} estimated should be True"
        )


# ============================================================================
# TEST 7 — Noise map FP rate computed correctly
# ============================================================================

def test_noise_map_fp_rate_computed_correctly():
    """Mock Neo4j: total=10, fp_count=3 for credential_access.
    fp_rate must equal 0.3 for that category."""
    from app.routers.soc import get_detection_engineering
    from app.domains.soc.config import SOC_PROFILE_CENTROIDS, SOC_CATEGORIES

    mock_scorer = MagicMock()
    mock_scorer.centroids = SOC_PROFILE_CENTROIDS.copy()

    # credential_access is index 0 in SOC_CATEGORIES
    side_effects = (
        [[{"total": 10, "fp_count": 3}]]
        + [[] for _ in range(len(SOC_CATEGORIES) - 1)]
    )

    async def _run():
        with patch("app.services.gae_state.get_profile_scorer", return_value=mock_scorer):
            with patch("app.routers.soc.neo4j_client") as mock_neo:
                mock_neo.run_query = AsyncMock(side_effect=side_effects)
                return await get_detection_engineering()

    result = asyncio.run(_run())
    cred = next(
        e for e in result["noise_map"] if e["category"] == "credential_access"
    )
    assert cred["fp_rate"] == 0.3, (
        f"credential_access fp_rate expected 0.3, got {cred['fp_rate']}"
    )
    assert cred["total_decisions"] == 10, (
        f"credential_access total_decisions expected 10, got {cred['total_decisions']}"
    )
    assert cred["estimated"] is False, (
        "estimated should be False when fp_rate is known"
    )
