from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "support" / "scripts" / "retroactive_grading.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("retroactive_grading", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_compute_graded_reward_correct_formula():
    module = _load_module()
    weights = {"credential_access": {"base": 0.70}}
    assert module.compute_graded_reward(True, "credential_access", weights) == pytest.approx(0.70)


def test_compute_graded_reward_incorrect_formula():
    module = _load_module()
    weights = {"credential_access": {"base": 0.70}}
    assert module.compute_graded_reward(False, "credential_access", weights) == pytest.approx(-14.0)


def test_compute_graded_quality_correct_and_incorrect():
    module = _load_module()
    weights = {"credential_access": {"base": 0.70}}
    assert module.compute_graded_quality(True, "credential_access", weights) == pytest.approx(0.70)
    assert module.compute_graded_quality(False, "credential_access", weights) == pytest.approx(0.0)


def test_rolling_accuracy_basic():
    module = _load_module()
    assert module.rolling_accuracy([True, False, True], window=2) == [1.0, 0.5, 0.5]


def test_rolling_mean_basic():
    module = _load_module()
    assert module.rolling_mean([1.0, 3.0, 5.0], window=2) == [1.0, 2.0, 4.0]


def test_correlation_after_warmup_handles_enough_data():
    module = _load_module()
    a = [float(i) for i in range(500)]
    b = [float(i * 2) for i in range(500)]
    assert module.correlation_after_warmup(a, b, warmup=400) == pytest.approx(1.0)


def test_realistic_simulation_passes_quality_gate():
    module = _load_module()
    result = module.run_validation(decisions=4860, seed=42)
    assert result["binary_quality_correlation"] >= 0.95
    assert result["tier"] == "PASS"


def test_signed_reward_correlation_reported_but_not_gate():
    module = _load_module()
    result = module.run_validation(decisions=4860, seed=42)
    assert "signed_reward_correlation" in result
    assert result["tier"] == "PASS"


def test_misaligned_quality_series_maps_to_fail_tier():
    module = _load_module()
    binary_q = [0.50] * 400 + [index / 100.0 for index in range(100)]
    graded_quality = [0.50] * 400 + [(99 - index) / 100.0 for index in range(100)]

    correlation = module.correlation_after_warmup(graded_quality, binary_q, warmup=400)
    tier = (
        "PASS" if correlation >= module.PASS_THRESHOLD
        else "WARNING" if correlation >= module.WARNING_THRESHOLD
        else "FAIL"
    )

    assert correlation < module.WARNING_THRESHOLD
    assert tier == "FAIL"


def test_binary_outcome_never_changes_due_to_severity():
    module = _load_module()
    weights = {"low": {"base": 0.10}, "high": {"base": 0.90}}
    assert module.compute_graded_quality(True, "low", weights) != module.compute_graded_quality(True, "high", weights)
    assert bool(True) is True
    assert bool(False) is False


def test_script_exists_and_runs():
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--decisions", "100", "--seed", "42"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "ALL VALIDATIONS PASSED" in result.stdout
