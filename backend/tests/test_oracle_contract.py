from __future__ import annotations

from app.oracle import AnalystOracle


REQUIRED_KEYS = {
    "action",
    "analyst_action",
    "was_override",
    "quality_signal",
    "correct",
}


def test_oracle_returns_all_required_fields() -> None:
    outcome = AnalystOracle(seed=42).synthetic_outcome(shown=True)

    for key in REQUIRED_KEYS:
        assert key in outcome
        assert outcome[key] is not None


def test_oracle_allows_additional_fields() -> None:
    outcome = AnalystOracle(seed=42).synthetic_outcome(shown=True)

    assert len(outcome) >= len(REQUIRED_KEYS)
