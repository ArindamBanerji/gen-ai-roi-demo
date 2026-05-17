from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domains.soc.config import (
    ALERT_TYPE_CATEGORY_MAP,
    N_FACTORS,
    SCORER_ACTIONS,
    SOC_CATEGORIES,
)
from app.services.situation import SituationType

SITUATION_TYPE_ALERT_TYPE_EXCLUSIONS = {
    "travel_login_anomaly",
    "known_phishing_campaign",
    "malware_on_critical_asset",
    "vip_after_hours",
    "data_exfil_attempt",
    "unknown",
    "brute_force_attack",
    "privilege_escalation_detected",
    "credential_stuffing_attack",
    "c2_communication",
    "threat_intel_indicator",
    "anomalous_network_behavior",
    "cloud_misconfiguration",
}

REQUIRED_FIELDS = {
    "users": ["user_id", "name", "department", "risk_level", "origin"],
    "assets": ["asset_id", "hostname", "criticality", "asset_type", "origin"],
    "attack_patterns": ["pattern_id", "name", "mitre_id", "tactic", "category", "origin"],
    "threat_indicators": ["indicator", "indicator_type", "severity", "source", "origin"],
    "campaigns": [
        "campaign_id",
        "name",
        "severity",
        "confidence",
        "trigger_rule",
        "category_sequence",
        "shared_entities",
        "technique_sequence",
        "nl_summary",
        "member_alert_ids",
        "alert_count",
        "correlation_window_hours",
        "first_seen",
        "last_seen",
        "origin",
        "alert_ids",
    ],
    "alerts": [
        "alert_id",
        "category",
        "severity",
        "alert_type",
        "timestamp_epoch",
        "origin",
        "source_location",
        "user_id",
        "status",
        "asset_id",
        "attack_pattern_id",
        "indicator_ids",
    ],
    "demo_alerts": [
        "alert_id",
        "category",
        "severity",
        "alert_type",
        "timestamp_epoch",
        "origin",
        "source_location",
        "user_id",
        "asset_id",
        "user_name",
        "asset_hostname",
        "attack_pattern_id",
        "indicator_ids",
        "status",
    ],
    "decisions": [
        "decision_id",
        "alert_id",
        "category",
        "action",
        "factor_vector",
        "confidence",
        "correct",
        "outcome",
        "timestamp_epoch",
        "origin",
        "source_id",
        "user_id",
        "timestamp",
    ],
}


@dataclass(frozen=True)
class SeedValidationResult:
    errors: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_seed(data: dict[str, Any]) -> SeedValidationResult:
    errors: list[str] = []
    _validate_required_fields(data, errors)
    _validate_situation_types(errors)

    users = {u.get("user_id") for u in data.get("users", [])}
    assets = {a.get("asset_id") for a in data.get("assets", [])}
    patterns = {p.get("pattern_id") for p in data.get("attack_patterns", [])}
    indicators = {i.get("indicator") for i in data.get("threat_indicators", [])}
    training_alerts = {a.get("alert_id"): a for a in data.get("alerts", [])}
    all_alerts = {
        a.get("alert_id"): a
        for a in data.get("alerts", []) + data.get("demo_alerts", [])
    }

    _validate_duplicate_ids(data, errors)
    _validate_alerts(data, users, assets, patterns, indicators, errors)
    _validate_decisions(data, training_alerts, errors)
    _validate_campaigns(data, training_alerts, errors)
    _validate_metadata(data, errors)
    _validate_timestamps(data, errors)
    _validate_category_coverage(data, errors)

    if not all_alerts and (data.get("alerts") or data.get("demo_alerts")):
        errors.append("alert ID map unexpectedly empty")
    return SeedValidationResult(errors)


def _validate_required_fields(data: dict[str, Any], errors: list[str]) -> None:
    for section, fields in REQUIRED_FIELDS.items():
        if section not in data:
            errors.append(f"missing top-level section: {section}")
            continue
        for index, item in enumerate(data.get(section, [])):
            for field in fields:
                if field not in item:
                    errors.append(f"{section}[{index}] missing required field {field}")


def _validate_situation_types(errors: list[str]) -> None:
    for situation in SituationType:
        value = situation.value
        if (
            value not in ALERT_TYPE_CATEGORY_MAP
            and value not in SITUATION_TYPE_ALERT_TYPE_EXCLUSIONS
        ):
            errors.append(f"SituationType {value} is neither mapped nor explicitly excluded")


def _validate_duplicate_ids(data: dict[str, Any], errors: list[str]) -> None:
    for section, field in [
        ("users", "user_id"),
        ("assets", "asset_id"),
        ("attack_patterns", "pattern_id"),
        ("campaigns", "campaign_id"),
        ("alerts", "alert_id"),
        ("demo_alerts", "alert_id"),
        ("decisions", "decision_id"),
    ]:
        values = [item.get(field) for item in data.get(section, [])]
        duplicates = {v for v in values if v is not None and values.count(v) > 1}
        if duplicates:
            errors.append(f"{section} has duplicate {field}: {sorted(duplicates)[:3]}")

    alert_ids = [a.get("alert_id") for a in data.get("alerts", []) + data.get("demo_alerts", [])]
    duplicate_alerts = {v for v in alert_ids if v is not None and alert_ids.count(v) > 1}
    if duplicate_alerts:
        errors.append(f"alerts/demo_alerts share duplicate alert_id: {sorted(duplicate_alerts)[:3]}")


def _validate_alerts(
    data: dict[str, Any],
    users: set[str],
    assets: set[str],
    patterns: set[str],
    indicators: set[str],
    errors: list[str],
) -> None:
    for section in ("alerts", "demo_alerts"):
        for index, alert in enumerate(data.get(section, [])):
            prefix = f"{section}[{index}]"
            alert_type = alert.get("alert_type")
            category = alert.get("category")
            mapped = ALERT_TYPE_CATEGORY_MAP.get(alert_type)
            if mapped is None:
                errors.append(f"{prefix} unmapped alert_type: {alert_type}")
            elif mapped != category:
                errors.append(f"{prefix} category {category} does not match alert_type {alert_type}")
            if category not in SOC_CATEGORIES:
                errors.append(f"{prefix} invalid category: {category}")
            if alert.get("user_id") not in users:
                errors.append(f"{prefix} references missing user_id: {alert.get('user_id')}")
            if alert.get("asset_id") not in assets:
                errors.append(f"{prefix} references missing asset_id: {alert.get('asset_id')}")
            attack_pattern_id = alert.get("attack_pattern_id")
            if attack_pattern_id and attack_pattern_id not in patterns:
                errors.append(f"{prefix} references missing attack_pattern_id: {attack_pattern_id}")
            for indicator_id in alert.get("indicator_ids") or []:
                if indicator_id not in indicators:
                    errors.append(f"{prefix} references missing indicator_id: {indicator_id}")
            if section == "alerts" and alert.get("status") == "pending":
                errors.append(f"{prefix} training alert must not be pending")
            if section == "demo_alerts" and alert.get("status") != "pending":
                errors.append(f"{prefix} demo alert must be pending")


def _validate_decisions(
    data: dict[str, Any],
    training_alerts: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    for index, decision in enumerate(data.get("decisions", [])):
        prefix = f"decisions[{index}]"
        alert = training_alerts.get(decision.get("alert_id"))
        if alert is None:
            errors.append(f"{prefix} references missing training alert: {decision.get('alert_id')}")
            continue
        if decision.get("category") not in SOC_CATEGORIES:
            errors.append(f"{prefix} invalid category: {decision.get('category')}")
        if decision.get("category") != alert.get("category"):
            errors.append(f"{prefix} category does not match referenced alert")
        if decision.get("action") not in SCORER_ACTIONS:
            errors.append(f"{prefix} invalid action: {decision.get('action')}")
        vector = decision.get("factor_vector")
        if not isinstance(vector, list) or len(vector) != N_FACTORS:
            errors.append(f"{prefix} factor_vector length must be {N_FACTORS}")
        elif any(not isinstance(v, (int, float)) or v < 0 or v > 1 for v in vector):
            errors.append(f"{prefix} factor_vector values must be in [0, 1]")


def _validate_campaigns(
    data: dict[str, Any],
    training_alerts: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    for index, campaign in enumerate(data.get("campaigns", [])):
        for field in ("member_alert_ids", "alert_ids"):
            for alert_id in campaign.get(field) or []:
                if alert_id not in training_alerts:
                    errors.append(
                        f"campaigns[{index}] {field} references missing alert: {alert_id}"
                    )
        if campaign.get("alert_count") != len(campaign.get("member_alert_ids") or []):
            errors.append(f"campaigns[{index}] alert_count does not match member_alert_ids")


def _validate_metadata(data: dict[str, Any], errors: list[str]) -> None:
    metadata = data.get("metadata", {})
    expected = {
        "total_alerts": len(data.get("alerts", [])),
        "total_demo_alerts": len(data.get("demo_alerts", [])),
        "total_decisions": len(data.get("decisions", [])),
        "total_users": len(data.get("users", [])),
        "total_assets": len(data.get("assets", [])),
        "total_attack_patterns": len(data.get("attack_patterns", [])),
        "total_threat_indicators": len(data.get("threat_indicators", [])),
        "total_campaigns": len(data.get("campaigns", [])),
    }
    for key, value in expected.items():
        if metadata.get(key) != value:
            errors.append(f"metadata.{key}={metadata.get(key)} does not match {value}")


def _validate_timestamps(data: dict[str, Any], errors: list[str]) -> None:
    timestamps = [d.get("timestamp_epoch") for d in data.get("decisions", [])]
    if not timestamps:
        return
    unique = len(set(timestamps))
    if unique < min(10, len(timestamps)):
        errors.append(f"decision timestamp uniqueness too low: {unique}")
    days = data.get("metadata", {}).get("days_simulated")
    if days and len(timestamps) > 1:
        span = max(timestamps) - min(timestamps)
        required = int(days) * 24 * 60 * 60 * 1000 * 0.8
        if span < required:
            errors.append("decision timestamps do not cover configured time range")


def _validate_category_coverage(data: dict[str, Any], errors: list[str]) -> None:
    alerts = data.get("alerts", []) + data.get("demo_alerts", [])
    if len(alerts) >= len(SOC_CATEGORIES):
        categories = {a.get("category") for a in alerts}
        missing = set(SOC_CATEGORIES) - categories
        if missing:
            errors.append(f"missing generated categories: {sorted(missing)}")
