"""RL Phase 0 eta-contract validation.

These tests intentionally exercise live ProfileScorer and gae_state contracts
without changing production code. They document the corrected Phase 0 pattern:
temporary mutation of scorer.eta / scorer.eta_neg / scorer.eta_override under
the existing scorer lock, never an eta_weight kwarg.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import numpy as np
import pytest

import app.services.gae_state as gae_state
from app.domains.soc.config import SOCDomainConfig
from app.services.gae_state import acquire_scorer, guarded_update
from gae.calibration import CalibrationProfile


def _make_scorer():
    scorer = SOCDomainConfig().build_profile_scorer()
    scorer.set_conservation_status("GREEN")
    return scorer


def _safe_factor_for(scorer, category_index: int = 0, action_index: int = 0) -> np.ndarray:
    """Return a nearby factor vector that avoids MAX_ETA_DELTA clipping."""
    return np.clip(scorer.mu[category_index, action_index, :] + 0.02, 0.0, 1.0)


def _capture_eta(scorer) -> dict[str, float | None]:
    return {
        "eta": scorer.eta,
        "eta_neg": scorer.eta_neg,
        "eta_override": scorer.eta_override,
    }


def _apply_eta_multiplier(scorer, multiplier: float) -> dict[str, float | None]:
    original = _capture_eta(scorer)
    scorer.eta = original["eta"] * multiplier
    scorer.eta_neg = original["eta_neg"] * multiplier
    if original["eta_override"] is not None:
        scorer.eta_override = original["eta_override"] * multiplier
    return original


def _restore_eta(scorer, original: dict[str, float | None]) -> None:
    scorer.eta = original["eta"]
    scorer.eta_neg = original["eta_neg"]
    scorer.eta_override = original["eta_override"]


def _reset_gae_guards() -> None:
    gae_state.set_volume_spike(False)
    gae_state.set_frozen_categories([])
    gae_state.reset_spike_counter()


def test_calibration_eta_fields_are_mutable():
    profile = CalibrationProfile()
    original_learning_rate = profile.learning_rate
    original_extensions = dict(profile.extensions)

    try:
        profile.learning_rate = 0.123
        profile.extensions["eta"] = 0.077
        profile.extensions["eta_neg"] = 0.055

        assert profile.learning_rate == pytest.approx(0.123)
        assert profile.extensions["eta"] == pytest.approx(0.077)
        assert profile.extensions["eta_neg"] == pytest.approx(0.055)
    finally:
        profile.learning_rate = original_learning_rate
        profile.extensions.clear()
        profile.extensions.update(original_extensions)

    assert profile.learning_rate == pytest.approx(original_learning_rate)
    assert profile.extensions == original_extensions


def test_temporary_eta_multiplier_pattern_restores_after_update():
    scorer = _make_scorer()
    original = _apply_eta_multiplier(scorer, 2.0)
    before = scorer.mu.copy()

    try:
        update = scorer.update(
            f=_safe_factor_for(scorer),
            category_index=0,
            action_index=0,
            correct=True,
        )
    finally:
        _restore_eta(scorer, original)

    assert update.centroid_delta_norm > 0.0
    assert not np.array_equal(scorer.mu, before)
    assert _capture_eta(scorer) == original


def test_temporary_eta_multiplier_restores_on_exception():
    scorer = _make_scorer()
    original = _apply_eta_multiplier(scorer, 2.0)

    with pytest.raises(RuntimeError, match="forced eta test failure"):
        try:
            raise RuntimeError("forced eta test failure")
        finally:
            _restore_eta(scorer, original)

    assert _capture_eta(scorer) == original


def test_eta_multiplier_affects_centroid_delta():
    scorer_base = _make_scorer()
    scorer_scaled = _make_scorer()
    f = _safe_factor_for(scorer_base)

    base_original = _apply_eta_multiplier(scorer_base, 1.0)
    scaled_original = _apply_eta_multiplier(scorer_scaled, 2.0)
    try:
        base_update = scorer_base.update(
            f=f,
            category_index=0,
            action_index=0,
            correct=True,
        )
        scaled_update = scorer_scaled.update(
            f=f,
            category_index=0,
            action_index=0,
            correct=True,
        )
    finally:
        _restore_eta(scorer_base, base_original)
        _restore_eta(scorer_scaled, scaled_original)

    ratio = scaled_update.centroid_delta_norm / base_update.centroid_delta_norm
    assert ratio == pytest.approx(2.0, rel=0.05)


def test_eta_multiplier_clip_bound_values():
    scorer = _make_scorer()
    assert scorer.eta == pytest.approx(0.05)
    assert scorer.eta_override == pytest.approx(0.01)

    multipliers = [0.1, 0.5, 1.0, 2.0, 3.0]
    confirm_rates = [scorer.eta * m for m in multipliers]
    override_rates = [scorer.eta_override * m for m in multipliers]

    assert confirm_rates == pytest.approx([0.005, 0.025, 0.05, 0.10, 0.15])
    assert override_rates == pytest.approx([0.001, 0.005, 0.01, 0.02, 0.03])


@pytest.mark.asyncio
async def test_guarded_update_with_temporary_eta(monkeypatch):
    _reset_gae_guards()
    scorer = _make_scorer()
    monkeypatch.setattr(
        gae_state,
        "_learning_state",
        SimpleNamespace(profile_scorer=scorer),
    )
    before = scorer.mu.copy()

    async with acquire_scorer() as locked_scorer:
        original = _apply_eta_multiplier(locked_scorer, 2.0)
        try:
            update = guarded_update(
                locked_scorer,
                f=_safe_factor_for(locked_scorer),
                category_index=0,
                action_index=0,
                correct=True,
                category_name="credential_access",
            )
        finally:
            _restore_eta(locked_scorer, original)

    assert update is not None
    assert update.centroid_delta_norm > 0.0
    assert not np.array_equal(scorer.mu, before)
    assert _capture_eta(scorer) == original
    _reset_gae_guards()


@pytest.mark.asyncio
async def test_acquire_scorer_exclusive_for_temporary_eta(monkeypatch):
    scorer = _make_scorer()
    monkeypatch.setattr(
        gae_state,
        "_learning_state",
        SimpleNamespace(profile_scorer=scorer),
    )

    first_entered = asyncio.Event()
    release_first = asyncio.Event()
    second_acquired = asyncio.Event()
    original = _capture_eta(scorer)

    async def first_holder():
        async with acquire_scorer() as locked_scorer:
            locked_scorer.eta = original["eta"] * 3.0
            first_entered.set()
            try:
                await release_first.wait()
            finally:
                _restore_eta(locked_scorer, original)

    async def second_holder():
        await first_entered.wait()
        async with acquire_scorer() as locked_scorer:
            second_acquired.set()
            assert _capture_eta(locked_scorer) == original

    first_task = asyncio.create_task(first_holder())
    second_task = asyncio.create_task(second_holder())

    await first_entered.wait()
    await asyncio.sleep(0.05)
    assert not second_acquired.is_set()
    assert scorer.eta == pytest.approx(original["eta"] * 3.0)

    release_first.set()
    await asyncio.wait_for(asyncio.gather(first_task, second_task), timeout=2.0)
    assert second_acquired.is_set()
    assert _capture_eta(scorer) == original
