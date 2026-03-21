from app.services.economics import FrozenROICalculator


def test_frozen_roi_positive():
    calc = FrozenROICalculator()
    result = calc.compute()
    assert result['total_frozen_roi'] > 0


def test_frozen_roi_hours_saved():
    calc = FrozenROICalculator(alerts_per_day=200)
    result = calc.compute()
    assert result['hours_saved_annually'] > 1000


def test_frozen_roi_scales_with_volume():
    low = FrozenROICalculator(alerts_per_day=50).compute()
    high = FrozenROICalculator(alerts_per_day=500).compute()
    assert high['total_frozen_roi'] > low['total_frozen_roi']


def test_frozen_roi_scales_with_cost():
    low = FrozenROICalculator(analyst_hourly_cost=50).compute()
    high = FrozenROICalculator(analyst_hourly_cost=120).compute()
    assert high['total_frozen_roi'] > low['total_frozen_roi']


def test_frozen_roi_assumptions_present():
    result = FrozenROICalculator().compute()
    assert 'assumptions' in result
    assert result['assumptions']['baseline_triage_minutes'] == 44.0


def test_frozen_roi_no_127():
    """Verify $127/alert is NOT used."""
    result = FrozenROICalculator().compute()
    # At 200 alerts/day, if using $127/alert: annual = 200*365*127 ≈ $9.3M
    # Frozen ROI should be much less (time-saved only)
    assert result['total_frozen_roi'] < 5_000_000
