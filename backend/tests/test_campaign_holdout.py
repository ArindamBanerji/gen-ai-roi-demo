import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.domains.soc.campaign_holdout import banner_suppressed


def test_banner_suppressed_is_deterministic_for_same_alert_id():
    first = banner_suppressed("ALERT-123")
    second = banner_suppressed("ALERT-123")

    assert first is second


def test_banner_suppressed_returns_booleans_for_different_alert_ids():
    values = [banner_suppressed(f"ALERT-{idx}") for idx in range(20)]

    assert all(isinstance(value, bool) for value in values)
    assert values == [banner_suppressed(f"ALERT-{idx}") for idx in range(20)]


def test_banner_suppressed_zero_percent_never_suppresses():
    assert all(
        banner_suppressed(f"ALERT-{idx}", holdout_pct=0) is False
        for idx in range(100)
    )


def test_banner_suppressed_hundred_percent_always_suppresses():
    assert all(
        banner_suppressed(f"ALERT-{idx}", holdout_pct=100) is True
        for idx in range(100)
    )


def test_banner_suppressed_default_is_approximately_fifteen_percent():
    total = 1000
    suppressed = sum(
        1 for idx in range(total) if banner_suppressed(f"ALERT-{idx}")
    )

    assert 120 <= suppressed <= 180
