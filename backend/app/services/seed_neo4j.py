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

    # RETIRED: bootstrap Decision node writer removed (orphan creator).
    # Replaced by support/setup/seed_zero_day.py.
    # from app.services.gae_state import get_profile_scorer
    # from app.services.bootstrap_neo4j import write_bootstrap_decisions
    # from app.domains.soc.config import SOC_CATEGORIES, BOOTSTRAP_CATEGORY_WEIGHTS
    # from app.db.neo4j import neo4j_client as _neo4j
    # ... (write_bootstrap_decisions call removed)


async def verify_neo4j_seed():
    """Placeholder verification."""
    return {"status": "seeded"}
