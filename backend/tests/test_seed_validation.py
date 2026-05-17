from __future__ import annotations

import copy

from app.domains.soc.config import ALERT_TYPE_CATEGORY_MAP
from app.seed.config import SeedConfig
from app.seed.runner import generate_seed
from app.seed.validate import (
    SITUATION_TYPE_ALERT_TYPE_EXCLUSIONS,
    validate_seed,
)
from app.services.situation import SituationType


def _small_seed() -> dict:
    return generate_seed(
        SeedConfig(
            n_training_alerts=36,
            n_demo_alerts=12,
            n_decisions=72,
            n_campaigns=3,
        )
    )


def _messages(data: dict) -> list[str]:
    return validate_seed(data).errors


def test_valid_seed_passes():
    assert validate_seed(_small_seed()).errors == []


def test_situation_types_covered_by_alert_type_map():
    unmapped = {
        situation.value
        for situation in SituationType
        if situation.value not in ALERT_TYPE_CATEGORY_MAP
    }
    assert unmapped == SITUATION_TYPE_ALERT_TYPE_EXCLUSIONS


def test_validation_rejects_unmapped_alert_type():
    data = _small_seed()
    data["alerts"][0]["alert_type"] = "not_a_real_alert_type"
    errors = _messages(data)
    assert any("unmapped alert_type" in error for error in errors)


def test_validation_rejects_stale_metadata():
    data = _small_seed()
    data["metadata"]["total_demo_alerts"] = 999
    errors = _messages(data)
    assert any("metadata.total_demo_alerts" in error for error in errors)


def test_validation_rejects_orphan_decision():
    data = _small_seed()
    data["decisions"][0]["alert_id"] = "MISSING-ALERT"
    errors = _messages(data)
    assert any("missing training alert" in error for error in errors)


def test_validation_rejects_duplicate_ids():
    data = _small_seed()
    data["alerts"][1]["alert_id"] = data["alerts"][0]["alert_id"]
    errors = _messages(data)
    assert any("duplicate alert_id" in error for error in errors)


def test_validation_rejects_identical_timestamps():
    data = _small_seed()
    for decision in data["decisions"]:
        decision["timestamp_epoch"] = 123
    errors = _messages(data)
    assert any("timestamp uniqueness" in error for error in errors)
    assert any("time range" in error for error in errors)


def test_validation_rejects_missing_attack_pattern():
    data = _small_seed()
    data["alerts"][0]["attack_pattern_id"] = "T-MISSING"
    errors = _messages(data)
    assert any("missing attack_pattern_id" in error for error in errors)


def test_validation_checks_all_records():
    data = _small_seed()
    data["alerts"][-1] = copy.deepcopy(data["alerts"][-1])
    del data["alerts"][-1]["severity"]
    errors = _messages(data)
    assert any("alerts[35] missing required field severity" == error for error in errors)


def test_validation_rejects_category_mismatch():
    data = _small_seed()
    data["alerts"][0]["category"] = "malware_execution"
    errors = _messages(data)
    assert any("does not match alert_type" in error for error in errors)


def test_validation_rejects_decision_category_mismatch():
    data = _small_seed()
    data["decisions"][0]["category"] = "malware_execution"
    errors = _messages(data)
    assert any("category does not match referenced alert" in error for error in errors)


def test_validation_rejects_missing_indicator():
    data = _small_seed()
    data["alerts"][0]["indicator_ids"] = ["missing-ioc"]
    errors = _messages(data)
    assert any("missing indicator_id" in error for error in errors)


def test_validation_rejects_missing_user_asset_refs():
    data = _small_seed()
    data["demo_alerts"][0]["user_id"] = "missing-user"
    data["demo_alerts"][1]["asset_id"] = "missing-asset"
    errors = _messages(data)
    assert any("missing user_id" in error for error in errors)
    assert any("missing asset_id" in error for error in errors)


def test_validation_rejects_bad_factor_vector_length():
    data = _small_seed()
    data["decisions"][0]["factor_vector"] = [0.1, 0.2]
    errors = _messages(data)
    assert any("factor_vector length" in error for error in errors)


def test_validation_rejects_campaign_missing_member():
    data = _small_seed()
    data["campaigns"][0]["member_alert_ids"] = ["missing-alert"]
    data["campaigns"][0]["alert_count"] = 1
    errors = _messages(data)
    assert any("member_alert_ids references missing alert" in error for error in errors)


def test_validation_rejects_missing_category_coverage():
    data = _small_seed()
    kept = data["alerts"][0]["category"]
    data["alerts"] = [alert for alert in data["alerts"] if alert["category"] == kept]
    data["demo_alerts"] = [
        alert for alert in data["demo_alerts"] if alert["category"] == kept
    ]
    data["metadata"]["total_alerts"] = len(data["alerts"])
    data["metadata"]["total_demo_alerts"] = len(data["demo_alerts"])
    alert_ids = {alert["alert_id"] for alert in data["alerts"]}
    data["decisions"] = [d for d in data["decisions"] if d["alert_id"] in alert_ids]
    data["metadata"]["total_decisions"] = len(data["decisions"])
    for campaign in data["campaigns"]:
        campaign["member_alert_ids"] = [
            alert_id for alert_id in campaign["member_alert_ids"] if alert_id in alert_ids
        ]
        campaign["alert_ids"] = list(campaign["member_alert_ids"])
        campaign["alert_count"] = len(campaign["member_alert_ids"])
    errors = _messages(data)
    assert any("missing generated categories" in error for error in errors)


def test_cli_validate_only_accepts_tmp_seed(tmp_path):
    import json
    import subprocess
    import sys

    path = tmp_path / "seed.json"
    path.write_text(json.dumps(_small_seed(), indent=2), encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, "scripts/generate_seed.py", "--output", str(path), "--validate-only"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Seed validation passed" in completed.stdout
