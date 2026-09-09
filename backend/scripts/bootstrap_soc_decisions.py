"""Bootstrap SOC experiment centroids from scorer-verified fixture decisions."""

from __future__ import annotations

import argparse
import asyncio
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
import sys
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np

from app.domains.soc.config import SCORER_ACTIONS, SOC_CATEGORIES, SOCDomainConfig
from scripts.generate_score_keyed_alerts import DEFAULT_FIXTURE
from scripts.measure_rho import FixtureFactorProvider, FixtureGraphStore, load_fixture, vectors_by_alert
from scripts.train_experiment_centroids import MIN_PER_CELL, QUALITY_GATE, centroid_quality
from scripts.value_chain_experiment_lib import write_json

OUTPUT_MU = Path("data/bootstrapped_centroids.npy")
OUTPUT_META = Path("data/bootstrapped_centroids_metadata.json")
DEFAULT_CONFIRM_RATE = 0.7
DEFAULT_MIN_DECISIONS = 200
RANDOM_SEED = 20260908


def _cell_key(category: str, action: str) -> str:
    return f"{category}:{action}"


def _score_action_index(result: Any) -> int:
    for name in ("action_index", "action_idx", "action"):
        value = getattr(result, name, None)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value in SCORER_ACTIONS:
            return int(SCORER_ACTIONS.index(value))
    raise ValueError(f"score result does not expose a SOC action index: {result!r}")


def _alternate_action_index(predicted: int, rng: random.Random) -> int:
    choices = [index for index in range(len(SCORER_ACTIONS)) if index != predicted]
    return rng.choice(choices)


async def _bootstrap_rows(
    *,
    fixture_path: str | Path,
    confirm_rate: float,
    min_decisions: int,
) -> tuple[list[dict[str, Any]], np.ndarray, dict[str, Any]]:
    if not 0.0 <= confirm_rate <= 1.0:
        raise ValueError("confirm_rate must be in [0, 1]")
    if min_decisions <= 0:
        raise ValueError("min_decisions must be positive")

    fixture = load_fixture(fixture_path)
    alerts = [dict(item) for item in fixture.get("alerts", []) if isinstance(item, dict)]
    decisions = [dict(item) for item in fixture.get("decisions", []) if isinstance(item, dict)]
    alert_by_id = {
        str(alert.get("alert_id") or alert.get("id")): alert
        for alert in alerts
        if alert.get("alert_id") or alert.get("id")
    }
    category_by_id = {
        alert_id: str(alert.get("category"))
        for alert_id, alert in alert_by_id.items()
        if alert.get("category") in SOC_CATEGORIES
    }
    vectors = vectors_by_alert(decisions)
    provider = FixtureFactorProvider(vectors)
    graph = FixtureGraphStore(alert_by_id)
    scorer = SOCDomainConfig().build_profile_scorer()
    rng = random.Random(RANDOM_SEED + int(round(confirm_rate * 1000)))

    eligible_ids = sorted(alert_id for alert_id in vectors if alert_id in category_by_id)
    if len(eligible_ids) < min_decisions:
        raise ValueError(f"only {len(eligible_ids)} eligible fixture decisions; need {min_decisions}")

    rows: list[dict[str, Any]] = []
    update_deltas: list[float] = []
    confirmed = 0
    overridden = 0
    for alert_id in eligible_ids:
        alert = alert_by_id[alert_id]
        category = category_by_id[alert_id]
        category_index = SOC_CATEGORIES.index(category)
        vector_raw, _metadata = await provider.compute(alert, graph)
        vector = np.asarray(vector_raw, dtype=np.float64).reshape(-1)
        if vector.shape != (len(SOCDomainConfig().get_factor_computers()),):
            raise ValueError(f"factor vector for {alert_id} has shape {vector.shape}")

        score = scorer.score(vector, category_index=category_index)
        predicted_index = _score_action_index(score)
        if rng.random() < confirm_rate:
            verified_index = predicted_index
            correct = True
            confirmed += 1
        else:
            verified_index = _alternate_action_index(predicted_index, rng)
            correct = False
            overridden += 1
        update = scorer.update(
            vector,
            category_index=category_index,
            action_index=predicted_index,
            correct=correct,
            gt_action_index=None if correct else verified_index,
        )
        update_deltas.append(float(getattr(update, "centroid_delta_norm", 0.0)))
        rows.append(
            {
                "alert_id": alert_id,
                "category": category,
                "predicted_action": SCORER_ACTIONS[predicted_index],
                "verified_action": SCORER_ACTIONS[verified_index],
                "action": SCORER_ACTIONS[verified_index],
                "confirmed": correct,
                "vector": [float(x) for x in vector.tolist()],
            }
        )

    grouped = _group_rows(rows)
    mu = _mean_centroids_from_verified_rows(grouped, np.asarray(scorer.centroids, dtype=np.float64))
    quality = centroid_quality(mu, grouped)
    samples_per_cell = {
        _cell_key(category, action): len(grouped.get(_cell_key(category, action), []))
        for category in SOC_CATEGORIES
        for action in SCORER_ACTIONS
    }
    sufficient_cells = sum(1 for count in samples_per_cell.values() if count >= MIN_PER_CELL)
    low_cells = sum(1 for count in samples_per_cell.values() if 0 < count < MIN_PER_CELL)
    empty_cells = [key for key, count in samples_per_cell.items() if count == 0]
    action_counts = Counter(str(row["verified_action"]) for row in rows)
    meta = {
        "shape": list(mu.shape),
        "source": "soc_fixture_score_confirm_override_learning_loop",
        "training_method": "verified_action_mean_after_profile_scorer_updates",
        "fixture": str(fixture_path),
        "total_decisions": len(rows),
        "confirm_rate": confirmed / float(len(rows)) if rows else 0.0,
        "requested_confirm_rate": confirm_rate,
        "confirmed_count": confirmed,
        "override_count": overridden,
        "random_seed": RANDOM_SEED,
        "samples_per_cell": samples_per_cell,
        "cells_sufficient": sufficient_cells,
        "cells_low_sample": low_cells,
        "cells_empty": len(empty_cells),
        "empty_cells": empty_cells,
        "min_per_cell": MIN_PER_CELL,
        "verified_action_counts": dict(sorted(action_counts.items())),
        "inter_intra_ratio": quality["inter_intra_ratio"],
        "quality_gate_threshold": QUALITY_GATE,
        "quality_gate": "PASS" if quality["inter_intra_ratio"] >= QUALITY_GATE else "FAIL",
        "mean_inter_cell_distance": quality["mean_inter_cell_distance"],
        "mean_intra_cell_variance": quality["mean_intra_cell_variance"],
        "learning_update_mean_delta": float(np.mean(update_deltas)) if update_deltas else 0.0,
        "learning_update_total_delta": float(np.sum(update_deltas)) if update_deltas else 0.0,
        "synthetic_training_data_used": False,
        "training_caveat": "Decisions are fixture-derived SOC alerts scored by the production ProfileScorer path; analyst outcomes use a deterministic confirm/override mix.",
    }
    return rows, mu, meta


def _group_rows(rows: list[dict[str, Any]]) -> dict[str, list[np.ndarray]]:
    grouped: dict[str, list[np.ndarray]] = defaultdict(list)
    for row in rows:
        grouped[_cell_key(str(row["category"]), str(row["verified_action"]))].append(
            np.asarray(row["vector"], dtype=np.float64)
        )
    return grouped


def _mean_centroids_from_verified_rows(
    grouped: dict[str, list[np.ndarray]],
    fallback_mu: np.ndarray,
) -> np.ndarray:
    mu = np.asarray(fallback_mu, dtype=np.float64).copy()
    for c_index, category in enumerate(SOC_CATEGORIES):
        for a_index, action in enumerate(SCORER_ACTIONS):
            vectors = grouped.get(_cell_key(category, action), [])
            if vectors:
                mu[c_index, a_index] = np.mean(vectors, axis=0)
    return cast(np.ndarray, mu)


def bootstrap_and_save(
    *,
    fixture_path: str | Path = DEFAULT_FIXTURE,
    output_mu: str | Path = OUTPUT_MU,
    output_meta: str | Path = OUTPUT_META,
    confirm_rate: float = DEFAULT_CONFIRM_RATE,
    min_decisions: int = DEFAULT_MIN_DECISIONS,
) -> dict[str, Any]:
    _rows, mu, meta = asyncio.run(
        _bootstrap_rows(
            fixture_path=fixture_path,
            confirm_rate=confirm_rate,
            min_decisions=min_decisions,
        )
    )
    output_mu_path = Path(output_mu)
    output_mu_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(output_mu_path, mu)
    write_json(output_meta, meta)
    return meta


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE))
    parser.add_argument("--output", default=str(OUTPUT_MU))
    parser.add_argument("--metadata", default=str(OUTPUT_META))
    parser.add_argument("--confirm-rate", type=float, default=DEFAULT_CONFIRM_RATE)
    parser.add_argument("--min-decisions", type=int, default=DEFAULT_MIN_DECISIONS)
    args = parser.parse_args()

    meta = bootstrap_and_save(
        fixture_path=args.fixture,
        output_mu=args.output,
        output_meta=args.metadata,
        confirm_rate=args.confirm_rate,
        min_decisions=args.min_decisions,
    )
    print("=== Bootstrap SOC decisions ===")
    print(f"Shape: {tuple(meta['shape'])}")
    print(f"Inter/intra: {meta['inter_intra_ratio']:.3f}")
    print(f"Gate: {meta['quality_gate']}")
    print(f"Total decisions: {meta['total_decisions']}")
    print(f"Confirm rate: {meta['confirm_rate']:.1%}")
    for cell, count in meta.get("samples_per_cell", {}).items():
        print(f"  {cell}: {count} samples")


if __name__ == "__main__":
    main()
