from __future__ import annotations

import ipaddress
import json
from pathlib import Path

from app.domains.soc.config import SCORER_ACTIONS, SOC_CATEGORIES


SEED_PATH = Path(__file__).resolve().parents[1] / "support" / "setup" / "zero_day_decisions_v5.json"
JDOE_ALERT_IDS = ["ALT-JDOE-001", "ALT-JDOE-002", "ALT-JDOE-003"]


def _load_seed() -> dict:
    return json.loads(SEED_PATH.read_text(encoding="utf-8"))


def _jdoe_alerts(data: dict) -> list[dict]:
    by_id = {alert["alert_id"]: alert for alert in data["alerts"]}
    return [by_id[alert_id] for alert_id in JDOE_ALERT_IDS]


def _jdoe_decisions(data: dict) -> dict[str, dict]:
    return {
        decision["decision_id"]: decision
        for decision in data["decisions"]
        if decision["decision_id"].startswith("DEC-JDOE-")
    }


def test_jdoe_alerts_exist_in_seed():
    data = _load_seed()
    alert_ids = {alert["alert_id"] for alert in data["alerts"]}

    assert set(JDOE_ALERT_IDS).issubset(alert_ids)


def test_jdoe_cross_category_pattern():
    data = _load_seed()
    alerts = _jdoe_alerts(data)

    assert {alert["category"] for alert in alerts} >= {"credential_access", "lateral_movement"}
    assert {alert["user_id"] for alert in alerts} == {"jdoe"}
    assert {alert["asset_id"] for alert in alerts} == {"DC-PROD-07"}

    timestamps = [alert["timestamp_epoch"] for alert in alerts]
    assert max(timestamps) - min(timestamps) <= 48 * 60 * 60 * 1000


def test_jdoe_pattern_history_escalates():
    data = _load_seed()
    alerts = _jdoe_alerts(data)

    pattern_history = [alert["factors"]["pattern_history"] for alert in alerts]

    assert pattern_history == [0.35, 0.55, 0.78]
    assert pattern_history == sorted(pattern_history)


def test_jdoe_ti_match_consistent():
    data = _load_seed()
    alerts = _jdoe_alerts(data)
    advisory_id = "CISA-AA-2026-0419"
    singapore_range = ipaddress.ip_network("103.253.40.0/22")

    for alert in alerts:
        assert advisory_id in alert["indicator_ids"]
        assert alert["ti_match"]["advisory"] == advisory_id
        assert alert["ti_match"]["ip_ranges"] == [str(singapore_range)]
        assert ipaddress.ip_address(alert["source_location"]) in singapore_range


def test_jdoe_prior_decisions_exist_and_pending_alert_has_none():
    data = _load_seed()
    decisions = _jdoe_decisions(data)
    decisions_by_alert = {decision["alert_id"]: decision for decision in decisions.values()}

    assert set(decisions) == {"DEC-JDOE-001", "DEC-JDOE-002"}
    assert decisions_by_alert["ALT-JDOE-001"]["decision_id"] == "DEC-JDOE-001"
    assert decisions_by_alert["ALT-JDOE-002"]["decision_id"] == "DEC-JDOE-002"
    assert "ALT-JDOE-003" not in decisions_by_alert

    for decision in decisions.values():
        assert decision["correct"] is True
        assert decision["outcome"] == "correct"


def test_jdoe_seed_uses_live_property_names():
    data = _load_seed()

    for alert in _jdoe_alerts(data):
        for field in ("user_id", "asset_id", "timestamp_epoch", "category", "source_location", "attack_pattern_id"):
            assert field in alert
        assert "source_user" not in alert
        assert "source_ip" not in alert
        assert "technique_id" not in alert
        assert alert["category"] in SOC_CATEGORIES

    for decision in _jdoe_decisions(data).values():
        assert decision["category"] in SOC_CATEGORIES
        assert decision["action"] in SCORER_ACTIONS
        assert "verified" not in decision
        assert "analyst" not in decision


def test_jdoe_seed_references_existing_graph_entities():
    data = _load_seed()
    alerts = _jdoe_alerts(data)
    decisions = _jdoe_decisions(data)

    users = {user["user_id"] for user in data["users"]}
    assets = {asset["asset_id"] for asset in data["assets"]}
    patterns = {pattern["pattern_id"] for pattern in data["attack_patterns"]}
    indicators = {indicator["indicator"] for indicator in data["threat_indicators"]}
    alert_ids = {alert["alert_id"] for alert in data["alerts"]}

    assert "jdoe" in users
    assert "DC-PROD-07" in assets

    for alert in alerts:
        assert alert["user_id"] in users
        assert alert["asset_id"] in assets
        assert alert["attack_pattern_id"] in patterns
        assert set(alert["indicator_ids"]).issubset(indicators)

    for decision in decisions.values():
        assert decision["alert_id"] in alert_ids


def test_jdoe_seed_metadata_counts_match_sections():
    data = _load_seed()
    metadata = data["metadata"]

    assert metadata["total_alerts"] == len(data["alerts"])
    assert metadata["total_demo_alerts"] == len(data["demo_alerts"])
    assert metadata["total_decisions"] == len(data["decisions"])
    assert metadata["total_users"] == len(data["users"])
    assert metadata["total_assets"] == len(data["assets"])
    assert metadata["total_attack_patterns"] == len(data["attack_patterns"])
    assert metadata["total_threat_indicators"] == len(data["threat_indicators"])
