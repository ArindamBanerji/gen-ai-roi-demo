"""Wrapper for seed_neo4j standalone script."""
import sys
from pathlib import Path

# Add backend root to path so we can import the standalone script
_backend_root = str(Path(__file__).resolve().parent.parent.parent)
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from seed_neo4j import seed_data


async def seed_neo4j_database():
    """Called by POST /api/demo/seed endpoint."""
    await seed_data()

    # Re-create bootstrap Decision nodes wiped by seed_data()'s DETACH DELETE.
    # Build directly from the current ProfileScorer — does not depend on
    # get_bootstrap_result(), which is None when loading from a checkpoint.
    from app.services.gae_state import get_profile_scorer
    from app.services.bootstrap_neo4j import write_bootstrap_decisions
    from app.domains.soc.config import SOC_CATEGORIES, BOOTSTRAP_CATEGORY_WEIGHTS
    from app.db.neo4j import neo4j_client as _neo4j

    scorer = get_profile_scorer()
    if scorer is not None:
        # 300 total = SOC_BOOTSTRAP_ROUNDS(10) × SOC_BOOTSTRAP_SAMPLES_PER_ACTION(5) × 6 cats
        _BOOTSTRAP_TOTAL = 300
        decisions_per_category = {
            cat: round(_BOOTSTRAP_TOTAL * BOOTSTRAP_CATEGORY_WEIGHTS.get(cat, 1 / len(SOC_CATEGORIES)))
            for cat in SOC_CATEGORIES
        }
        # Absorb any rounding delta in the largest-weight category
        _delta = _BOOTSTRAP_TOTAL - sum(decisions_per_category.values())
        if _delta != 0:
            _largest = max(decisions_per_category, key=decisions_per_category.get)
            decisions_per_category[_largest] += _delta

        await write_bootstrap_decisions(
            neo4j_client=_neo4j,
            scorer=scorer,
            categories=list(SOC_CATEGORIES),
            decisions_per_category=decisions_per_category,
        )


async def verify_neo4j_seed():
    """Placeholder verification."""
    return {"status": "seeded"}
