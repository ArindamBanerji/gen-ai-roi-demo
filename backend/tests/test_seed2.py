"""
test_seed2.py — SEED-2 unit tests (no Neo4j required).

Tests the generation logic in app/scripts/seed_realistic.py.
All tests are pure-Python and deterministic.

Run from backend/:
    pytest tests/test_seed2.py -v
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ============================================================================
# TEST 1 — seed_realistic is importable and callable
# ============================================================================

def test_seed_realistic_importable():
    """seed_realistic must be an async callable."""
    from app.scripts.seed_realistic import seed_realistic
    assert callable(seed_realistic), "seed_realistic must be callable"


# ============================================================================
# TEST 2 — DEPARTMENT_DISTRIBUTION totals exactly 200
# ============================================================================

def test_user_distribution_totals_200():
    """DEPARTMENT_DISTRIBUTION values must sum to 200."""
    from app.scripts.seed_realistic import DEPARTMENT_DISTRIBUTION

    total = sum(DEPARTMENT_DISTRIBUTION.values())
    assert total == 200, (
        f"DEPARTMENT_DISTRIBUTION should total 200, got {total}. "
        f"Values: {DEPARTMENT_DISTRIBUTION}"
    )


# ============================================================================
# TEST 3 — Generation is fully deterministic (no random)
# ============================================================================

def test_deterministic_generation():
    """Building the same user list twice must produce identical results."""
    from app.scripts.seed_realistic import build_user_properties

    list1 = [build_user_properties(f"REAL-USR-{n:04d}") for n in range(1, 21)]
    list2 = [build_user_properties(f"REAL-USR-{n:04d}") for n in range(1, 21)]

    assert list1 == list2, (
        "build_user_properties is not deterministic — two calls with the same "
        "input produced different results."
    )


# ============================================================================
# TEST 4 — Planted users (0001–0005) are suspicious
# ============================================================================

def test_planted_users_are_suspicious():
    """REAL-USR-0001 must have access_level='privileged' and travel_frequency='frequent'."""
    from app.scripts.seed_realistic import build_user_properties

    user = build_user_properties("REAL-USR-0001")

    assert user["access_level"] == "privileged", (
        f"REAL-USR-0001 access_level expected 'privileged', got {user['access_level']!r}"
    )
    assert user["travel_frequency"] == "frequent", (
        f"REAL-USR-0001 travel_frequency expected 'frequent', got {user['travel_frequency']!r}"
    )


# ============================================================================
# TEST 5 — Alert IDs follow the "REAL-{CODE}-{n:03d}" convention
# ============================================================================

def test_alert_ids_follow_convention():
    """build_alert_id must return 'REAL-CA-001' for credential_access, n=1."""
    from app.scripts.seed_realistic import build_alert_id

    alert_id = build_alert_id("credential_access", 1)

    assert alert_id.startswith("REAL-"), (
        f"Alert ID should start with 'REAL-', got {alert_id!r}"
    )
    assert "001" in alert_id, (
        f"Alert ID should contain '001', got {alert_id!r}"
    )
    # Full value check
    assert alert_id == "REAL-CA-001", (
        f"Expected 'REAL-CA-001', got {alert_id!r}"
    )


# ============================================================================
# TEST 6 — ~15% of users are missing device_type (20–40 out of 200)
# ============================================================================

def test_15_percent_missing_device_type():
    """
    About 15% of users should omit device_type.
    Accept 20–40 missing (10%–20%) to allow for the exact modulo pattern used.
    """
    from app.scripts.seed_realistic import build_user_properties

    users = [build_user_properties(f"REAL-USR-{n:04d}") for n in range(200)]
    missing = sum(1 for u in users if "device_type" not in u)

    assert 20 <= missing <= 40, (
        f"Expected ~15% missing device_type (20–40 / 200), got {missing}/200 "
        f"({missing / 200:.1%})"
    )


# ============================================================================
# TEST 7 — ALERT_CATEGORY_DISTRIBUTION covers all 6 SOC categories
# ============================================================================

def test_category_distribution_covers_all_6():
    """Every SOC_CATEGORIES entry must appear as a key in ALERT_CATEGORY_DISTRIBUTION."""
    from app.scripts.seed_realistic import ALERT_CATEGORY_DISTRIBUTION
    from app.domains.soc.config import SOC_CATEGORIES

    for cat in SOC_CATEGORIES:
        assert cat in ALERT_CATEGORY_DISTRIBUTION, (
            f"SOC category '{cat}' missing from ALERT_CATEGORY_DISTRIBUTION. "
            f"Present keys: {list(ALERT_CATEGORY_DISTRIBUTION.keys())}"
        )
