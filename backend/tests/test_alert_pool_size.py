from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


DATA_PATH = Path(__file__).resolve().parents[1] / "support" / "setup" / "zero_day_decisions_v5.json"
EXPECTED_CATEGORIES = {
    "credential_access",
    "lateral_movement",
    "data_exfiltration",
    "malware_execution",
    "insider_threat",
    "cloud_infrastructure",
}


def _data() -> dict:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def _alerts() -> list[dict]:
    return _data()["demo_alerts"]


def test_demo_alert_pool_has_100() -> None:
    alerts = _alerts()
    assert len(alerts) >= 100, f"expected at least 100 demo alerts, got {len(alerts)}"


def test_demo_alerts_cover_all_6_categories() -> None:
    categories = {alert.get("category") for alert in _alerts()}
    assert categories == EXPECTED_CATEGORIES, f"unexpected demo alert categories: {categories}"


def test_demo_alerts_balanced_distribution() -> None:
    distribution = Counter(alert["category"] for alert in _alerts())
    for category in EXPECTED_CATEGORIES:
        assert distribution[category] >= 17, (
            f"{category} has {distribution[category]} demo alerts; expected at least 17"
        )


def test_demo_alerts_required_fields() -> None:
    alerts = _alerts()
    expected_keys = set(alerts[0])
    for alert in alerts:
        assert set(alert) == expected_keys, (
            f"{alert.get('alert_id')} keys differ from schema: {sorted(set(alert) ^ expected_keys)}"
        )
        for key in expected_keys:
            assert key in alert, f"{alert.get('alert_id')} missing {key}"


def test_demo_alert_ids_unique() -> None:
    alert_ids = [alert["alert_id"] for alert in _alerts()]
    duplicates = [alert_id for alert_id, count in Counter(alert_ids).items() if count > 1]
    assert not duplicates, f"duplicate demo alert IDs: {duplicates}"


def test_demo_alerts_reference_valid_users() -> None:
    data = _data()
    valid_users = {user["user_id"] for user in data["users"]}
    bad_refs = [
        (alert["alert_id"], alert.get("user_id"))
        for alert in data["demo_alerts"]
        if alert.get("user_id") not in valid_users
    ]
    assert not bad_refs, f"demo alerts reference unknown users: {bad_refs[:10]}"


def test_demo_alerts_reference_valid_assets() -> None:
    data = _data()
    valid_assets = {asset["asset_id"] for asset in data["assets"]}
    bad_refs = [
        (alert["alert_id"], alert.get("asset_id"))
        for alert in data["demo_alerts"]
        if alert.get("asset_id") not in valid_assets
    ]
    assert not bad_refs, f"demo alerts reference unknown assets: {bad_refs[:10]}"


def test_demo_alerts_all_pending_origin() -> None:
    bad_alerts = [
        (alert["alert_id"], alert.get("origin"), alert.get("status"))
        for alert in _alerts()
        if alert.get("origin") != "zero_day_demo" or alert.get("status") != "pending"
    ]
    assert not bad_alerts, f"demo alerts with wrong origin/status: {bad_alerts[:10]}"
