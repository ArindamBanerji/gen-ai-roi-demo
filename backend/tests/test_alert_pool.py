"""
Tests for alert pool integrity -- no healthcare, all valid SOC categories,
cloud_infrastructure and refer_to_analyst coverage.
"""

from app.data.alert_pool import get_alert_pool
from app.domains.soc.config import SOC_CATEGORIES, SOC_ACTIONS


def test_no_healthcare_alerts_in_pool():
    pool = get_alert_pool()
    healthcare = [a for a in pool if a.get("category") == "healthcare"]
    assert len(healthcare) == 0, (
        f"Found {len(healthcare)} healthcare alerts. "
        f"Healthcare is not in SOC_CATEGORIES."
    )


def test_all_pool_alerts_have_valid_category():
    pool = get_alert_pool()
    for alert in pool:
        cat = alert["category"]
        assert cat in SOC_CATEGORIES, (
            f"Alert '{alert.get('alert_type', '?')}' has category '{cat}' "
            f"not in SOC_CATEGORIES"
        )


def test_pool_has_at_least_15_alerts():
    """After removing 5 healthcare, pool should still have ~20 alerts."""
    pool = get_alert_pool()
    assert len(pool) >= 15, f"Pool too small after cleanup: {len(pool)}"


def test_cloud_infrastructure_alerts_exist():
    pool = get_alert_pool()
    cloud = [a for a in pool if a.get("category") == "cloud_infrastructure"]
    assert len(cloud) >= 4, (
        f"Expected >= 4 cloud_infrastructure alerts, found {len(cloud)}"
    )


def test_refer_to_analyst_ground_truth_exists():
    pool = get_alert_pool()
    refer = [a for a in pool if a.get("ground_truth_action") == "refer_to_analyst"]
    assert len(refer) >= 3, (
        f"Expected >= 3 refer_to_analyst ground truth alerts, found {len(refer)}"
    )


def test_all_ground_truth_actions_are_valid():
    pool = get_alert_pool()
    for alert in pool:
        gt = alert.get("ground_truth_action", "investigate")
        assert gt in SOC_ACTIONS, (
            f"Alert '{alert.get('alert_type')}' has ground_truth_action='{gt}' "
            f"not in SOC_ACTIONS"
        )


def test_each_category_has_at_least_one_alert():
    pool = get_alert_pool()
    for cat in SOC_CATEGORIES:
        cat_alerts = [a for a in pool if a["category"] == cat]
        assert len(cat_alerts) >= 1, (
            f"Category '{cat}' has zero alerts in pool"
        )


def test_pool_size_after_expansion():
    """20 original + 4 cloud + 3 refer = 27"""
    pool = get_alert_pool()
    assert len(pool) >= 27, f"Expected >= 27 alerts, got {len(pool)}"
