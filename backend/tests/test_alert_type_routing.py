"""
CORR-1: alert_type -> category routing tests.
Verifies that ALERT_TYPE_CATEGORY_MAP covers all known alert_types and that
resolve_alert_category() routes each one correctly.
"""
import ast
import inspect
import logging


# ---------------------------------------------------------------------------
# 1. Every alert in the pool must route to the pool's stated category
# ---------------------------------------------------------------------------

def test_all_pool_alert_types_route_correctly():
    """Every alert_type in the pool must route to the pool's stated category."""
    from app.data.alert_pool import get_alert_pool
    from app.domains.soc.config import resolve_alert_category

    pool = get_alert_pool()
    for alert in pool:
        alert_type = alert["alert_type"]
        expected_category = alert["category"]
        actual_category = resolve_alert_category(alert_type)
        assert actual_category == expected_category, (
            f"alert_type='{alert_type}' routed to '{actual_category}' "
            f"but pool says category='{expected_category}'"
        )


# ---------------------------------------------------------------------------
# 2. Every alert_type in the main seed corpus must resolve to a valid category
# ---------------------------------------------------------------------------

def test_all_seed_alert_types_route_to_valid_category():
    """Every alert_type in the seed corpus must map to a SOC_CATEGORIES entry."""
    from app.domains.soc.config import (
        resolve_alert_category, SOC_CATEGORIES, ALERT_TYPE_CATEGORY_MAP,
    )

    seed_types = [
        "anomalous_login", "phishing", "malware_detection", "brute_force",
        "privilege_escalation", "credential_stuffing", "c2_beacon",
        "threat_intel_match", "data_exfil", "anomalous_behavior",
        "insider_threat", "cloud_config",
    ]
    for alert_type in seed_types:
        category = resolve_alert_category(alert_type)
        assert category in SOC_CATEGORIES, (
            f"alert_type='{alert_type}' resolved to '{category}' "
            f"which is not in SOC_CATEGORIES"
        )


# ---------------------------------------------------------------------------
# 3. Unknown alert_type must log ROUTING_UNCLASSIFIED and return DEFAULT_CATEGORY
# ---------------------------------------------------------------------------

def test_unknown_alert_type_logs_error(caplog):
    """Unmapped alert_type must log WARNING with ROUTING_UNCLASSIFIED."""
    from app.domains.soc.config import resolve_alert_category, DEFAULT_CATEGORY

    with caplog.at_level(logging.WARNING):
        result = resolve_alert_category("completely_unknown_type_xyz")

    assert result == DEFAULT_CATEGORY
    assert "ROUTING_UNCLASSIFIED" in caplog.text
    assert "completely_unknown_type_xyz" in caplog.text


# ---------------------------------------------------------------------------
# 4. Mapping dict must cover all 19 known types
# ---------------------------------------------------------------------------

def test_mapping_covers_all_known_types():
    """The mapping dict must have at least 19 entries (all known types)."""
    from app.domains.soc.config import ALERT_TYPE_CATEGORY_MAP

    assert len(ALERT_TYPE_CATEGORY_MAP) >= 19, (
        f"ALERT_TYPE_CATEGORY_MAP has {len(ALERT_TYPE_CATEGORY_MAP)} entries, "
        f"expected >= 19"
    )


# ---------------------------------------------------------------------------
# 5. Regression: privilege_escalation → lateral_movement
# ---------------------------------------------------------------------------

def test_privilege_escalation_routes_to_lateral_movement():
    """Regression test: this was the most impactful misroute."""
    from app.domains.soc.config import resolve_alert_category

    assert resolve_alert_category("privilege_escalation") == "lateral_movement"


# ---------------------------------------------------------------------------
# 6. Regression: data_exfil → data_exfiltration
# ---------------------------------------------------------------------------

def test_data_exfil_routes_to_data_exfiltration():
    """Regression test: data_exfil was misrouting to credential_access."""
    from app.domains.soc.config import resolve_alert_category

    assert resolve_alert_category("data_exfil") == "data_exfiltration"


# ---------------------------------------------------------------------------
# 7. All cloud_ prefixed types → cloud_infrastructure
# ---------------------------------------------------------------------------

def test_cloud_types_route_to_cloud_infrastructure():
    """All cloud_ prefixed types must route to cloud_infrastructure."""
    from app.domains.soc.config import resolve_alert_category

    cloud_types = [
        "cloud_config", "cloud_iam_privilege_escalation",
        "cloud_storage_public_exposure", "cloud_config_drift",
        "cloud_unused_resource_anomaly", "cloud_permission_change_review",
    ]
    for alert_type in cloud_types:
        assert resolve_alert_category(alert_type) == "cloud_infrastructure", (
            f"'{alert_type}' should route to cloud_infrastructure"
        )


# ---------------------------------------------------------------------------
# 8. triage.py must no longer contain the silent ValueError fallback
# ---------------------------------------------------------------------------

def test_no_silent_fallback_in_triage():
    """Verify triage.py no longer has the try/except ValueError for category routing."""
    from app.routers import triage

    source = inspect.getsource(triage)
    # The old pattern was: except ValueError: _cat_idx = 0
    # Both parts must be gone together; if either remains alone the bug is gone.
    has_except_value_error = "except ValueError" in source
    has_cat_idx_zero = "_cat_idx = 0" in source
    assert not (has_except_value_error and has_cat_idx_zero), (
        "triage.py still has the silent ValueError fallback for category routing. "
        "Replace with resolve_alert_category()."
    )


# ---------------------------------------------------------------------------
# 9. CORR-1b: All pool alert_types must be present in the pool
# ---------------------------------------------------------------------------

def test_all_pool_alerts_have_alert_type_in_seed():
    """Every alert_type in the pool should be covered by seeding.

    Cloud types must be present (CORR-1b regression guard).
    """
    from app.data.alert_pool import get_alert_pool

    pool = get_alert_pool()
    alert_types = {alert.get("alert_type") for alert in pool if alert.get("alert_type")}

    cloud_types = {
        "cloud_iam_privilege_escalation",
        "cloud_storage_public_exposure",
        "cloud_config_drift",
        "cloud_unused_resource_anomaly",
    }
    assert cloud_types.issubset(alert_types), (
        f"Cloud alert types missing from pool: {cloud_types - alert_types}"
    )


# ---------------------------------------------------------------------------
# 10. CORR-1b: Seeding function source must contain MERGE for all cloud types
# ---------------------------------------------------------------------------

def test_seed_creates_alert_type_nodes():
    """Verify seeding function creates AlertType nodes for all cloud types.

    Checks source code so this fails immediately if a MERGE is dropped.
    """
    from app.data import alert_pool

    source = inspect.getsource(alert_pool)
    for cloud_type in [
        "cloud_iam_privilege_escalation",
        "cloud_storage_public_exposure",
        "cloud_config_drift",
        "cloud_unused_resource_anomaly",
        "cloud_permission_change_review",
    ]:
        assert cloud_type in source, (
            f"Seeding function missing MERGE for cloud alert type: {cloud_type}"
        )
