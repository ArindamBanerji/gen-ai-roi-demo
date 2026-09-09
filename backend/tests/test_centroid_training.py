"""Tests for isolated SOC experiment centroid training."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from typing import Any, cast

import numpy as np
import pytest

from app.domains.soc.config import SCORER_ACTIONS, SOC_CATEGORIES, SOCDomainConfig
from scripts.bootstrap_soc_decisions import OUTPUT_META as BOOTSTRAPPED_META
from scripts.bootstrap_soc_decisions import OUTPUT_MU as BOOTSTRAPPED_MU
from scripts.bootstrap_soc_decisions import bootstrap_and_save
from scripts.exp_baseline_verify import run_experiment as run_baseline
from scripts.exp_split_enrichment import run_experiment as run_split
from scripts.train_experiment_centroids import OUTPUT_META, OUTPUT_MU, train_and_save
from scripts.value_chain_experiment_lib import get_experiment_scorer


def _ensure_trained() -> dict[str, Any]:
    if not OUTPUT_MU.exists() or not OUTPUT_META.exists():
        train_and_save()
    return cast(dict[str, Any], json.loads(OUTPUT_META.read_text(encoding="utf-8")))


def _ensure_bootstrapped() -> dict[str, Any]:
    if not BOOTSTRAPPED_MU.exists() or not BOOTSTRAPPED_META.exists():
        bootstrap_and_save()
    return cast(dict[str, Any], json.loads(BOOTSTRAPPED_META.read_text(encoding="utf-8")))


def test_train_experiment_centroids_produces_valid_numpy_array() -> None:
    train_and_save()
    mu = np.load(OUTPUT_MU)
    expected = SOCDomainConfig().build_profile_scorer().centroids
    assert mu.shape == np.asarray(expected).shape


def test_trained_centroids_pass_inter_intra_quality_gate() -> None:
    meta = _ensure_trained()
    assert meta["inter_intra_ratio"] >= 1.5
    assert meta["quality_gate"] == "PASS"


def test_trained_centroid_metadata_has_required_fields() -> None:
    meta = _ensure_trained()
    for key in ["inter_intra_ratio", "cells_sufficient", "cells_empty", "n_samples_per_cell"]:
        assert key in meta
    assert len(meta["n_samples_per_cell"]) == len(SOC_CATEGORIES) * len(SCORER_ACTIONS)


def test_get_experiment_scorer_trained_matches_file() -> None:
    _ensure_trained()
    scorer = get_experiment_scorer(use_trained=True)
    np.testing.assert_allclose(np.asarray(scorer.centroids), np.load(OUTPUT_MU))


def test_get_experiment_scorer_default_matches_default_config() -> None:
    default = get_experiment_scorer(use_trained=False)
    expected = SOCDomainConfig().build_profile_scorer()
    np.testing.assert_allclose(np.asarray(default.centroids), np.asarray(expected.centroids))


def test_trained_scorer_scores_centroids_self_consistently() -> None:
    _ensure_trained()
    scorer = get_experiment_scorer(use_trained=True)
    from app.services.investigation_router import InvestigationRouter

    router = InvestigationRouter({})
    for c_index, category in enumerate(SOC_CATEGORIES):
        for a_index, action in enumerate(SCORER_ACTIONS):
            best = router.score_best_from_centroids(np.asarray(scorer.centroids[c_index, a_index]), scorer)
            assert best.category == category
            assert best.action == action


@pytest.mark.asyncio
async def test_baseline_script_accepts_trained_mode_without_crashing() -> None:
    _ensure_trained()
    report = await run_baseline(use_trained=True)
    assert report["centroid_mode"] == "trained"
    assert report["all_checks_pass"] is True


@pytest.mark.asyncio
async def test_split_script_accepts_trained_mode_without_crashing() -> None:
    _ensure_trained()
    report = await run_split(use_trained=True)
    assert report["centroid_mode"] == "trained"
    assert set(report["strategies"]) == {"A_current_vld", "B_route_surface", "C_selective", "D_route_selective", "E_oracle"}


def test_bootstrap_soc_decisions_produces_valid_centroids() -> None:
    meta = bootstrap_and_save()
    mu = np.load(BOOTSTRAPPED_MU)
    expected = SOCDomainConfig().build_profile_scorer().centroids
    assert mu.shape == np.asarray(expected).shape
    assert meta["total_decisions"] >= 200
    assert meta["synthetic_training_data_used"] is False


def test_bootstrapped_centroids_quality_gate_or_documents_fixture_limit() -> None:
    meta = _ensure_bootstrapped()
    if meta["inter_intra_ratio"] >= 1.5:
        assert meta["quality_gate"] == "PASS"
    else:
        assert meta["quality_gate"] == "FAIL"
        assert meta["cells_sufficient"] < len(SOC_CATEGORIES) * len(SCORER_ACTIONS) or "fixture" in meta["training_caveat"].lower()


def test_get_experiment_scorer_bootstrapped_matches_file() -> None:
    _ensure_bootstrapped()
    scorer = get_experiment_scorer(use_bootstrapped=True)
    np.testing.assert_allclose(np.asarray(scorer.centroids), np.load(BOOTSTRAPPED_MU))


def test_experiment_scripts_accept_bootstrapped_flag() -> None:
    scripts = [
        "scripts/exp_baseline_verify.py",
        "scripts/exp_split_enrichment.py",
        "scripts/sprint/b1_dual_centroids.py",
        "scripts/sprint/c_validate_best.py",
    ]
    for script in scripts:
        result = subprocess.run(
            [sys.executable, script, "--help"],
            check=True,
            capture_output=True,
            text=True,
        )
        assert "--bootstrapped" in result.stdout


@pytest.mark.asyncio
async def test_baseline_script_accepts_bootstrapped_mode_without_crashing() -> None:
    _ensure_bootstrapped()
    report = await run_baseline(use_bootstrapped=True)
    assert report["centroid_mode"] == "bootstrapped"


@pytest.mark.asyncio
async def test_split_script_accepts_bootstrapped_mode_without_crashing() -> None:
    _ensure_bootstrapped()
    report = await run_split(use_bootstrapped=True)
    assert report["centroid_mode"] == "bootstrapped"
    assert set(report["strategies"]) == {"A_current_vld", "B_route_surface", "C_selective", "D_route_selective", "E_oracle"}
