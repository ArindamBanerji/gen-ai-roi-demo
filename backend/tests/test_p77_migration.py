from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.domains.soc.config import SCORER_ACTIONS, SOC_CATEGORIES, SOCDomainConfig
from app.domains.soc.scorer_adapter import SOCCompoundingScorerAdapter
from app.routers import triage
from app.services import gae_state


def _adapter() -> SOCCompoundingScorerAdapter:
    return SOCCompoundingScorerAdapter()


def _raw_scorer():
    return SOCDomainConfig().build_profile_scorer()


async def _zero_delta(_current_iks: float) -> float:
    return 0.0


def test_outcome_updates_centroid_through_adapter():
    scorer = _adapter()
    before = scorer.mu[0, 1].copy()

    gae_state.guarded_update(
        scorer,
        np.full(6, 0.9),
        category_index=0,
        action_index=1,
        correct=True,
        category_name="credential_access",
    )

    assert not np.array_equal(scorer.mu[0, 1], before)
    assert scorer.counts[0, 1] == 1


def test_outcome_conservation_through_adapter():
    scorer = _adapter()

    scorer.set_conservation_status("AMBER")

    assert scorer.conservation_status == "AMBER"
    assert scorer.is_paused is True


def test_outcome_reestimate_dk_through_adapter():
    scorer = _adapter()
    factors = np.full(6, 0.8)

    for _ in range(210):
        scorer.update(factors, category_index=0, action_index=1, correct=True)
    scorer.reestimate_dk()

    assert scorer.get_phase(0) == "VARIANCE_LEARNING"
    assert scorer.get_dk_weights(0) is not None


def test_outcome_l5_persistence_through_adapter(monkeypatch):
    scorer = _adapter()
    pre = scorer.centroids[0, 1].copy().tolist()
    scorer.update(np.full(6, 0.8), category_index=0, action_index=1, correct=True)
    calls: list[dict] = []

    class _Store:
        def update_centroid(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setattr(gae_state, "get_learning_store", lambda: _Store())

    persisted = gae_state.persist_soc_centroid(
        scorer=scorer,
        category="credential_access",
        category_index=0,
        action="investigate",
        action_index=1,
        caused_by_decision_id="DEC-P77",
        pre_centroid=pre,
    )

    assert persisted is True
    assert calls
    assert calls[0]["domain"] == "soc"
    assert calls[0]["category"] == "credential_access"


def test_outcome_referral_preserved():
    scorer = _adapter()
    result = scorer.score(np.full(6, 0.5), category_index=0)

    assert "refer_to_analyst" not in scorer.actions
    assert result.action_name in SCORER_ACTIONS


@pytest.mark.asyncio
async def test_profile_endpoint_returns_200(monkeypatch):
    scorer = _adapter()
    monkeypatch.setattr(triage, "get_profile_scorer", lambda: scorer)
    monkeypatch.setattr("app.services.iks._compute_delta_7d", _zero_delta)

    response = await triage.get_profile_state()

    assert response["categories"] == SOC_CATEGORIES
    assert response["actions"] == SCORER_ACTIONS


def test_profile_route_returns_frontend_contract(monkeypatch):
    from app.main import app

    scorer = _adapter()
    monkeypatch.setattr(triage, "get_profile_scorer", lambda: scorer)
    monkeypatch.setattr("app.services.iks._compute_delta_7d", _zero_delta)

    client = TestClient(app)
    response = client.get("/api/soc/profile")

    assert response.status_code == 200
    data = response.json()
    assert sorted(data.keys()) == ["actions", "categories", "centroids", "counts", "decision_count", "iks"]


@pytest.mark.asyncio
async def test_profile_has_centroids(monkeypatch):
    scorer = _adapter()
    monkeypatch.setattr(triage, "get_profile_scorer", lambda: scorer)
    monkeypatch.setattr("app.services.iks._compute_delta_7d", _zero_delta)

    response = await triage.get_profile_state()

    assert np.asarray(response["centroids"]).shape == (6, 4, 6)


@pytest.mark.asyncio
async def test_profile_has_categories(monkeypatch):
    scorer = _adapter()
    monkeypatch.setattr(triage, "get_profile_scorer", lambda: scorer)
    monkeypatch.setattr("app.services.iks._compute_delta_7d", _zero_delta)

    response = await triage.get_profile_state()

    assert response["categories"] == SOC_CATEGORIES
    assert len(response["categories"]) == 6


@pytest.mark.asyncio
async def test_profile_has_actions_and_counts(monkeypatch):
    scorer = _adapter()
    monkeypatch.setattr(triage, "get_profile_scorer", lambda: scorer)
    monkeypatch.setattr("app.services.iks._compute_delta_7d", _zero_delta)

    response = await triage.get_profile_state()

    assert response["actions"] == SCORER_ACTIONS
    assert np.asarray(response["counts"]).shape == (6, 4)


@pytest.mark.asyncio
async def test_profile_has_iks(monkeypatch):
    scorer = _adapter()
    monkeypatch.setattr(triage, "get_profile_scorer", lambda: scorer)
    monkeypatch.setattr("app.services.iks._compute_delta_7d", _zero_delta)

    response = await triage.get_profile_state()

    assert {"current", "delta_7d", "interpretation", "decision_count", "estimated", "trend"} <= set(response["iks"])


def test_adapter_is_compounding_scorer():
    scorer = _adapter()

    assert isinstance(scorer, SOCCompoundingScorerAdapter)
    assert not hasattr(scorer, "compound")
    assert scorer._compound._preset.name == "soc"


def test_adapter_exposes_soc_shape_by_delegation():
    scorer = _adapter()

    assert scorer.categories == SOC_CATEGORIES
    assert scorer.actions == SCORER_ACTIONS
    assert scorer.n_categories == 6
    assert scorer.n_actions == 4
    assert scorer.mu.shape == (6, 4, 6)


def test_no_direct_profile_scorer_construction_in_backend_app():
    offenders: list[str] = []
    app_dir = Path("app")
    for path in app_dir.rglob("*.py"):
        rel = path.as_posix()
        if rel == "app/domains/soc/config.py":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "ProfileScorer(" in text or "build_profile_scorer(" in text:
            offenders.append(rel)

    assert offenders == []


def test_old_config_still_importable_and_deprecated():
    method = SOCDomainConfig.build_profile_scorer

    assert callable(method)
    assert "DEPRECATED" in (method.__doc__ or "")


def test_1000_vectors_parity():
    raw = _raw_scorer()
    scorer = _adapter()
    rng = np.random.default_rng(77)

    for _ in range(1000):
        factors = rng.uniform(0.0, 1.0, size=6)
        category_index = int(rng.integers(0, 6))
        expected = raw.score(factors, category_index=category_index)
        actual = scorer.score(factors, category_index=category_index)

        assert actual.action_index == expected.action_index
        np.testing.assert_allclose(actual.probabilities, expected.probabilities, atol=1e-10)


def test_learn_parity_50_cycles():
    raw = _raw_scorer()
    scorer = _adapter()
    rng = np.random.default_rng(88)

    for _ in range(50):
        factors = rng.uniform(0.0, 1.0, size=6)
        category_index = int(rng.integers(0, 6))
        action_index = int(rng.integers(0, 4))
        correct = bool(rng.integers(0, 2))
        kwargs = {
            "f": factors,
            "category_index": category_index,
            "action_index": action_index,
            "correct": correct,
        }
        raw.update(**kwargs)
        scorer.update(**kwargs)

    np.testing.assert_allclose(scorer.centroids, raw.centroids, atol=1e-10)
    np.testing.assert_array_equal(scorer.counts, raw.counts)


def test_adapter_survives_restart():
    scorer = _adapter()
    for _ in range(5):
        scorer.update(np.full(6, 0.8), category_index=0, action_index=1, correct=True)
    state = scorer.get_checkpoint_state()

    restarted = _adapter()
    restarted.restore_checkpoint_state(state)

    np.testing.assert_allclose(restarted.centroids, scorer.centroids)


def test_adapter_concurrent_score():
    scorer = _adapter()
    factors = np.full(6, 0.5)

    def _score(category_index: int):
        return scorer.score(factors, category_index=category_index % 6)

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(_score, range(50)))

    assert len(results) == 50
    assert all(result.action_name in SCORER_ACTIONS for result in results)


def test_adapter_unknown_category():
    scorer = _adapter()

    with pytest.raises(ValueError):
        scorer.get_centroid("unknown_category", "escalate")


def test_gae_state_scorer_is_adapter(monkeypatch, tmp_path):
    monkeypatch.setattr(gae_state, "_STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(gae_state, "_MU_ZERO_PATH", tmp_path / "mu_zero.json")
    monkeypatch.setattr(gae_state, "_learning_state", None)
    monkeypatch.setattr(gae_state, "_learning_store", None)
    monkeypatch.setattr(gae_state, "_bootstrap_metadata", None)
    monkeypatch.setattr(gae_state, "_bootstrap_result", None)
    monkeypatch.delenv("GRAPH_DSN", raising=False)
    monkeypatch.setattr(
        gae_state,
        "bootstrap_calibration",
        lambda **_kwargs: SimpleNamespace(n_decisions=0, final_drift=0.0, converged=True),
    )
    monkeypatch.setattr(gae_state, "save_learning_state", lambda: None)

    state = gae_state.init_learning_state()

    assert isinstance(state.profile_scorer, SOCCompoundingScorerAdapter)
