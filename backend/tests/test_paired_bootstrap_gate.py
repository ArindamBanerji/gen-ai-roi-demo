from app.services.promotion_gate import paired_bootstrap_test


def test_paired_bootstrap_requires_minimum_sample_count():
    result = paired_bootstrap_test(
        [{"baseline": False, "candidate": True}] * 29
    )

    assert result["passed"] is False
    assert result["n"] == 29
    assert result["min_n"] == 30
    assert result["reason"] == "insufficient_samples"


def test_paired_bootstrap_passes_clear_improvement_below_fpr_threshold():
    outcomes = ([{"baseline": False, "candidate": True}] * 24
                + [{"baseline": True, "candidate": False}] * 6)

    result = paired_bootstrap_test(outcomes, resamples=1000)

    assert result["passed"] is True
    assert result["n"] == 30
    assert result["p_value"] < 0.05
    assert result["fpr_threshold"] == 0.05


def test_paired_bootstrap_rejects_no_improvement():
    result = paired_bootstrap_test(
        [{"baseline": True, "candidate": True}] * 30
    )

    assert result["passed"] is False
    assert result["reason"] == "not_significant"
    assert result["observed_delta"] == 0.0


def test_paired_bootstrap_rejects_regression():
    result = paired_bootstrap_test(
        [{"baseline": True, "candidate": False}] * 30
    )

    assert result["passed"] is False
    assert result["observed_delta"] < 0
