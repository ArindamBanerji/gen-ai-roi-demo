from __future__ import annotations

import copy
import json
import subprocess
import sys

import pytest

from app.domains.soc.config import (
    ALERT_TYPE_CATEGORY_MAP,
    N_FACTORS,
    SCORER_ACTIONS,
    SOC_CATEGORIES,
)
from app.seed.config import SeedConfig
from app.seed.entities import load_existing_seed
from app.seed.runner import generate_seed
from app.seed.validate import validate_seed


@pytest.fixture(scope="module")
def generated_seed() -> dict:
    return generate_seed()


def test_generated_schema_matches_current(generated_seed):
    current = load_existing_seed()
    assert list(generated_seed.keys()) == list(current.keys())
    for section in [
        "users",
        "assets",
        "attack_patterns",
        "threat_indicators",
        "campaigns",
        "alerts",
        "demo_alerts",
        "decisions",
    ]:
        assert set(generated_seed[section][0]) == set(current[section][0])


def test_alert_generator_uses_alert_type_map(generated_seed):
    for alert in generated_seed["alerts"] + generated_seed["demo_alerts"]:
        assert alert["alert_type"] in ALERT_TYPE_CATEGORY_MAP


def test_alert_category_matches_alert_type_map(generated_seed):
    for alert in generated_seed["alerts"] + generated_seed["demo_alerts"]:
        assert alert["category"] == ALERT_TYPE_CATEGORY_MAP[alert["alert_type"]]


def test_metadata_counts_derived(generated_seed):
    metadata = generated_seed["metadata"]
    assert metadata["total_alerts"] == len(generated_seed["alerts"])
    assert metadata["total_demo_alerts"] == len(generated_seed["demo_alerts"])
    assert metadata["total_decisions"] == len(generated_seed["decisions"])
    assert metadata["total_users"] == len(generated_seed["users"])
    assert metadata["total_assets"] == len(generated_seed["assets"])
    assert metadata["total_attack_patterns"] == len(generated_seed["attack_patterns"])
    assert metadata["total_threat_indicators"] == len(generated_seed["threat_indicators"])
    assert metadata["total_campaigns"] == len(generated_seed["campaigns"])


def test_decisions_reference_existing_alerts(generated_seed):
    alert_ids = {alert["alert_id"] for alert in generated_seed["alerts"]}
    assert {decision["alert_id"] for decision in generated_seed["decisions"]} <= alert_ids


def test_alerts_reference_existing_users_assets(generated_seed):
    user_ids = {user["user_id"] for user in generated_seed["users"]}
    asset_ids = {asset["asset_id"] for asset in generated_seed["assets"]}
    for alert in generated_seed["alerts"] + generated_seed["demo_alerts"]:
        assert alert["user_id"] in user_ids
        assert alert["asset_id"] in asset_ids


def test_campaign_member_alerts_exist(generated_seed):
    alert_ids = {alert["alert_id"] for alert in generated_seed["alerts"]}
    for campaign in generated_seed["campaigns"]:
        assert set(campaign["member_alert_ids"]) <= alert_ids
        assert set(campaign["alert_ids"]) <= alert_ids


def test_indicator_refs_exist(generated_seed):
    indicator_ids = {indicator["indicator"] for indicator in generated_seed["threat_indicators"]}
    for alert in generated_seed["alerts"] + generated_seed["demo_alerts"]:
        assert set(alert["indicator_ids"]) <= indicator_ids


def test_generator_deterministic_same_seed():
    first = generate_seed(SeedConfig(n_training_alerts=30, n_demo_alerts=12, n_decisions=60))
    second = generate_seed(SeedConfig(n_training_alerts=30, n_demo_alerts=12, n_decisions=60))
    assert first == second


def test_generator_changes_with_different_seed():
    first = generate_seed(SeedConfig(n_training_alerts=30, n_demo_alerts=12, n_decisions=60, seed=42))
    second = generate_seed(SeedConfig(n_training_alerts=30, n_demo_alerts=12, n_decisions=60, seed=43))
    assert first["alerts"] != second["alerts"]
    assert first["decisions"] != second["decisions"]


def test_all_six_categories_present(generated_seed):
    categories = {alert["category"] for alert in generated_seed["alerts"] + generated_seed["demo_alerts"]}
    assert categories == set(SOC_CATEGORIES)


def test_demo_training_origin_split_preserved(generated_seed):
    assert {alert["origin"] for alert in generated_seed["alerts"]} == {"zero_day_synthetic"}
    assert {alert["status"] for alert in generated_seed["alerts"]} == {"decided"}
    assert {alert["origin"] for alert in generated_seed["demo_alerts"]} == {"zero_day_demo"}
    assert {alert["status"] for alert in generated_seed["demo_alerts"]} == {"pending"}


def test_demo_alert_pool_has_100(generated_seed):
    assert len(generated_seed["demo_alerts"]) >= 100


def test_no_orphan_decisions_after_generated_seed(generated_seed):
    alert_ids = {alert["alert_id"] for alert in generated_seed["alerts"]}
    orphans = [d for d in generated_seed["decisions"] if d["alert_id"] not in alert_ids]
    assert orphans == []


def test_seed_config_defaults_match_current():
    current = load_existing_seed()
    config = SeedConfig()
    assert config.n_training_alerts == len(current["alerts"])
    assert config.n_demo_alerts == len(current["demo_alerts"])
    assert config.n_decisions == len(current["decisions"])
    assert config.n_users == len(current["users"])
    assert config.n_assets == len(current["assets"])
    assert config.n_campaigns == len(current["campaigns"])
    assert config.n_attack_patterns == len(current["attack_patterns"])
    assert config.n_threat_indicators == len(current["threat_indicators"])
    assert config.time_range_days == current["metadata"]["days_simulated"]


def test_seed_config_validates_category_weights():
    bad_weights = dict.fromkeys(SOC_CATEGORIES, 0.1)
    with pytest.raises(ValueError, match="sum"):
        SeedConfig(category_weights=bad_weights)


def test_demo_alerts_have_display_fields(generated_seed):
    for alert in generated_seed["demo_alerts"]:
        assert alert["user_name"]
        assert alert["asset_hostname"]


def test_decision_category_matches_alert(generated_seed):
    alerts = {alert["alert_id"]: alert for alert in generated_seed["alerts"]}
    for decision in generated_seed["decisions"]:
        assert decision["category"] == alerts[decision["alert_id"]]["category"]


def test_decision_factor_vector_length(generated_seed):
    for decision in generated_seed["decisions"]:
        assert len(decision["factor_vector"]) == N_FACTORS
        assert all(0.0 <= value <= 1.0 for value in decision["factor_vector"])


def test_generator_scalable_counts():
    config = SeedConfig(
        n_training_alerts=60,
        n_demo_alerts=18,
        n_decisions=120,
        n_users=10,
        n_assets=8,
        n_campaigns=2,
    )
    data = generate_seed(config)
    assert len(data["alerts"]) == 60
    assert len(data["demo_alerts"]) == 18
    assert len(data["decisions"]) == 120
    assert len(data["users"]) == 10
    assert len(data["assets"]) == 8
    assert len(data["campaigns"]) == 2


def test_attack_pattern_count_overrides_keep_valid_references():
    for n_attack_patterns in [0, 1, 2]:
        data = generate_seed(
            SeedConfig(
                n_training_alerts=60,
                n_demo_alerts=18,
                n_decisions=120,
                n_users=21,
                n_assets=16,
                n_campaigns=2,
                n_attack_patterns=n_attack_patterns,
            )
        )
        pattern_ids = {pattern["pattern_id"] for pattern in data["attack_patterns"]}
        referenced = {
            alert["attack_pattern_id"]
            for alert in data["alerts"] + data["demo_alerts"]
            if alert["attack_pattern_id"]
        }

        assert validate_seed(data).errors == []
        assert referenced <= pattern_ids


def test_timestamp_spacing_spans_configured_window():
    data = generate_seed(SeedConfig(n_training_alerts=40, n_demo_alerts=12, n_decisions=80))
    timestamps = [d["timestamp_epoch"] for d in data["decisions"]]
    span_days = (max(timestamps) - min(timestamps)) / 86400000
    assert len(set(timestamps)) == len(timestamps)
    assert span_days >= 72


def test_t1537_template_added_for_current_reference(generated_seed):
    pattern_ids = {pattern["pattern_id"] for pattern in generated_seed["attack_patterns"]}
    assert "T1537" in pattern_ids
    for alert in generated_seed["alerts"] + generated_seed["demo_alerts"]:
        if alert["attack_pattern_id"]:
            assert alert["attack_pattern_id"] in pattern_ids


def test_cli_writes_tmp_output(tmp_path):
    output = tmp_path / "seed.json"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/generate_seed.py",
            "--output",
            str(output),
            "--n-training-alerts",
            "20",
            "--n-demo-alerts",
            "12",
            "--n-decisions",
            "40",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(output.read_text(encoding="utf-8"))
    assert "Wrote seed JSON" in completed.stdout
    assert len(data["alerts"]) == 20
    assert len(data["demo_alerts"]) == 12
    assert len(data["decisions"]) == 40


def test_actions_from_scorer_action_names(generated_seed):
    assert {decision["action"] for decision in generated_seed["decisions"]} <= set(SCORER_ACTIONS)


def test_generated_seed_is_json_serializable(generated_seed):
    clone = copy.deepcopy(generated_seed)
    encoded = json.dumps(clone, indent=2)
    assert '"metadata"' in encoded
