"""C8 action boundary: existing SOC E-SPLIT results plus learned-K scoring.

Pre-registration: primary metric is action_accuracy (predicted final action /
fixture action vote). At trained geometry, a K-informed strategy is material
only if it improves action_accuracy over the matched current-VLD B=2 baseline
by >3pp in at least two of the three seeds. Existing A-E results remain
single-run, all-543-alert comparisons and are reported verbatim; new learned-K
results use paired 400-train/143-test splits (seeds 42, 123, 7), so they are
reported separately rather than pooled with the legacy result.

New strategies (both post-process the same vector after at most two evidence
steps; neither reads extra dimensions):
1. K-global: online pairwise hinge metric learning on the training split,
   pooling action-distance feature weights over SOC categories; apply the
   learned weights inside the category selected by the existing router.
2. K-category: the same learner, but use category-conditioned weights inside
   the existing router's selected category.
Weights start at 1, update only from training-set category/action labels, and
are clipped to [0.25, 4]. Evaluation labels are held out. This is a
script-only action-scoring adapter; production scorer/router source is not
modified. Strategy A2 and both K strategies use the same B=2 investigation
vector within each seed.

Tier: REAL_COMPONENT SOC centroid geometry + SIMULATED synthetic fixture,
evidence and action-vote labels. No operational outcome or LLM label claim.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
import random
from statistics import mean, stdev
import sys
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.domains.soc.config import SCORER_ACTIONS, SOC_CATEGORIES
from app.services.investigation_loop import InvestigationLoop
from scripts.value_chain_experiment_lib import ExperimentContext


SEEDS = (42, 123, 7)
TRAIN_N = 400
TEST_N = 143
MAX_READ_STEPS = 2
EPOCHS = 12
LEARNING_RATE = 0.2
HINGE_MARGIN = 0.05
WEIGHT_MIN = 0.25
WEIGHT_MAX = 4.0
MATERIALITY = 0.03
EXISTING_RESULTS = {
    "default": Path("data/exp_split_enrichment.json"),
    "trained": Path("data/exp_split_enrichment_trained.json"),
    "bootstrapped": Path("data/exp_split_enrichment_bootstrapped.json"),
}
OUTPUT = ROOT / "data/c8_action_boundary_results.json"
SUMMARY = ROOT / "data/c8_action_boundary_summary.md"


async def _v_after_two_reads(ctx: ExperimentContext, alert: dict[str, Any]) -> tuple[np.ndarray, int]:
    loop = InvestigationLoop(
        ctx.scorer,
        ctx.router,
        ctx.provider,
        L_max=MAX_READ_STEPS,
        residual_threshold=0.0,
    )
    result = await loop.investigate(alert, ctx.graph)
    if result.steps > MAX_READ_STEPS:
        raise AssertionError(f"B=2 limit exceeded: {result.steps}")
    return np.asarray(result.v_final, dtype=np.float64), int(result.steps)


def _pairwise_fit(
    examples: list[tuple[str, np.ndarray, str]],
    centroids: np.ndarray,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Fit category-specific pairwise weights and their pooled mean."""
    per_category = np.ones((len(SOC_CATEGORIES), len(SCORER_ACTIONS)), dtype=np.float64)
    # The second axis is replaced below with the actual factor dimension.
    per_category = np.ones((len(SOC_CATEGORIES), centroids.shape[2]), dtype=np.float64)
    rng = random.Random(seed + 800_017)
    category_index = {name: i for i, name in enumerate(SOC_CATEGORIES)}
    action_index = {name: i for i, name in enumerate(SCORER_ACTIONS)}
    order = list(range(len(examples)))
    for _ in range(EPOCHS):
        rng.shuffle(order)
        for example_index in order:
            category, vector, truth_action = examples[example_index]
            if category not in category_index or truth_action not in action_index:
                continue
            ci = category_index[category]
            yi = action_index[truth_action]
            category_mu = centroids[ci]
            residual_sq = (category_mu - vector.reshape(1, -1)) ** 2
            distances = np.sum(per_category[ci].reshape(1, -1) * residual_sq, axis=1)
            distances[yi] = float("inf")
            negative = int(np.argmin(distances))
            difference = residual_sq[negative] - residual_sq[yi]
            weights = per_category[ci]
            gap = float(np.dot(weights, difference))
            if gap < HINGE_MARGIN:
                norm = float(np.dot(difference, difference)) + 1e-12
                update = LEARNING_RATE * (HINGE_MARGIN - gap) * difference / norm
                per_category[ci] = np.clip(weights + update, WEIGHT_MIN, WEIGHT_MAX)
    pooled = np.mean(per_category, axis=0)
    return per_category, pooled


def _predict_weighted(
    vector: np.ndarray,
    ctx: ExperimentContext,
    category: str,
    weights: np.ndarray,
) -> str:
    categories = list(getattr(ctx.scorer, "categories", SOC_CATEGORIES))
    actions = list(getattr(ctx.scorer, "actions", SCORER_ACTIONS))
    category_index = categories.index(category)
    centroids = np.asarray(ctx.scorer.centroids, dtype=np.float64)[category_index]
    residual = centroids - vector.reshape(1, -1)
    distances = np.sum(weights.reshape(1, -1) * residual**2, axis=1)
    return str(actions[int(np.argmin(distances))])


async def _run_seed(seed: int) -> dict[str, Any]:
    ctx = ExperimentContext(use_trained=True)
    eligible = [
        alert for alert in ctx.eval_alerts
        if ctx.alert_id(alert) in ctx.action_truth
        and ctx.true_category(alert) in SOC_CATEGORIES
        and str(ctx.action_truth[ctx.alert_id(alert)]) in SCORER_ACTIONS
    ]
    if len(eligible) != TRAIN_N + TEST_N:
        raise AssertionError(f"Expected 543 eligible alerts, found {len(eligible)}")
    rng = random.Random(seed)
    shuffled = list(eligible)
    rng.shuffle(shuffled)
    train_alerts = shuffled[:TRAIN_N]
    test_alerts = shuffled[TRAIN_N:]

    train_rows: list[tuple[str, np.ndarray, str]] = []
    for alert in train_alerts:
        vector, _read_count = await _v_after_two_reads(ctx, alert)
        train_rows.append(
            (ctx.true_category(alert), vector, str(ctx.action_truth[ctx.alert_id(alert)]))
        )

    centroids = np.asarray(ctx.scorer.centroids, dtype=np.float64)
    category_weights, global_weights = _pairwise_fit(train_rows, centroids, seed)
    stats: dict[str, dict[str, int]] = {
        name: {"correct": 0, "n": 0, "evidence_steps": 0}
        for name in ("A_current_vld_B2", "K_global", "K_category")
    }
    for alert in test_alerts:
        alert_id = ctx.alert_id(alert)
        truth = str(ctx.action_truth[alert_id])
        vector, reads = await _v_after_two_reads(ctx, alert)
        baseline = ctx.router.score_best_from_centroids(vector, ctx.scorer)
        routed_category = str(baseline.category)
        predicted = {
            "A_current_vld_B2": str(baseline.action),
            "K_global": _predict_weighted(vector, ctx, routed_category, global_weights),
            "K_category": _predict_weighted(
                vector,
                ctx,
                routed_category,
                category_weights[SOC_CATEGORIES.index(routed_category)],
            ),
        }
        for name, action in predicted.items():
            stats[name]["n"] += 1
            stats[name]["correct"] += int(action == truth)
            stats[name]["evidence_steps"] += reads

    return {
        "seed": seed,
        "train_n": len(train_alerts),
        "test_n": len(test_alerts),
        "action_accuracy": {
            name: stats[name]["correct"] / stats[name]["n"]
            for name in stats
        },
        "correct_counts": {
            name: stats[name]["correct"] for name in stats
        },
        "evidence_steps_mean": {
            name: stats[name]["evidence_steps"] / stats[name]["n"]
            for name in stats
        },
        "k_weights_global": [float(x) for x in global_weights],
        "k_weights_by_category": {
            category: [float(x) for x in category_weights[index]]
            for index, category in enumerate(SOC_CATEGORIES)
        },
    }


def _aggregate(values: list[float]) -> tuple[float, float]:
    return mean(values), stdev(values) if len(values) > 1 else 0.0


def _existing_results() -> dict[str, Any]:
    names = {
        "A_current_vld": "A_current_vld",
        "B_route_surface": "B_route_surface",
        "C_selective": "C_selective",
        "D_route_selective": "D_route_selective",
        "E_oracle": "E_oracle",
    }
    result: dict[str, Any] = {}
    for geometry, path in EXISTING_RESULTS.items():
        data = json.loads(path.read_text(encoding="utf-8"))
        strategies = data.get("strategies", {})
        result[geometry] = {
            "existing_strategies": {
                out_name: {
                    "accuracy": strategies[source_name].get("accuracy"),
                    "delta_vs_sp": strategies[source_name].get("delta_vs_sp"),
                    "n": strategies[source_name].get("n"),
                }
                for out_name, source_name in names.items()
            },
            "new_strategies": {},
            "single_pass_accuracy": data.get("single_pass_accuracy"),
            "verdict": data.get("verdict"),
            "strategy_a_matches_phase1b": data.get("strategy_a_matches_phase1b"),
            "source": "existing",
        }
    return result


async def build_payload() -> dict[str, Any]:
    existing = _existing_results()
    per_seed: dict[str, dict[str, Any]] = {}
    seed_hashes: dict[str, str] = {}
    for seed in SEEDS:
        first = await _run_seed(seed)
        second = await _run_seed(seed)
        first_bytes = json.dumps(first, sort_keys=True, separators=(",", ":")).encode("utf-8")
        second_bytes = json.dumps(second, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if first_bytes != second_bytes:
            raise RuntimeError(f"Two-rebuild mismatch at seed {seed}")
        seed_hashes[str(seed)] = hashlib.sha256(first_bytes).hexdigest()
        per_seed[str(seed)] = first

    trained = existing["trained"]
    trained["source"] = "existing plus new matched-seed action-scoring runs"
    baseline_old = float(trained["existing_strategies"]["A_current_vld"]["accuracy"])
    for strategy, description in (
        (
            "K_global_weighted_action",
            "Pairwise-learned pooled K feature weights re-score actions inside the B=2 baseline's routed category.",
        ),
        (
            "K_category_weighted_action",
            "Pairwise-learned category-conditioned K feature weights re-score actions inside the B=2 baseline's routed category.",
        ),
    ):
        accuracy_key = "K_global" if strategy.startswith("K_global") else "K_category"
        scores = [float(per_seed[str(seed)]["action_accuracy"][accuracy_key]) for seed in SEEDS]
        base_scores = [
            float(per_seed[str(seed)]["action_accuracy"]["A_current_vld_B2"])
            for seed in SEEDS
        ]
        deltas = [scores[index] - base_scores[index] for index in range(len(SEEDS))]
        acc_mean, acc_std = _aggregate(scores)
        delta_mean, delta_std = _aggregate(deltas)
        trained["new_strategies"][strategy] = {
            "description": description,
            "per_seed": {
                str(seed): {
                    "action_accuracy": scores[index],
                    "delta_vs_A": deltas[index],
                    "matched_A_action_accuracy": base_scores[index],
                    "n": TEST_N,
                    "evidence_steps_mean": per_seed[str(seed)]["evidence_steps_mean"][accuracy_key],
                }
                for index, seed in enumerate(SEEDS)
            },
            "aggregate": {
                "action_mean": acc_mean,
                "action_std": acc_std,
                "delta_vs_A": delta_mean,
                "delta_std_vs_A": delta_std,
                "beats_A_by_3pp": sum(value > MATERIALITY for value in deltas),
                "legacy_A_all_543_action_accuracy": baseline_old,
                "legacy_comparison_note": "Existing A is a single-run all-543 result and is not a matched comparison; decision rule uses per-seed matched B=2 A baseline.",
            },
        }

    return {
        "soc": existing,
        "metadata": {
            "scope": "SOC only",
            "scope_limitation": "Only SOC has a compatible category/action centroid scorer, patterns, and 543-alert fixture in this repo. supply_chain/S2P is a config stub without build_profile_scorer or compatible fixture; Trading, Purchasing, DataOps configs are absent.",
            "existing_result_files": [str(path).replace("\\", "/") for path in EXISTING_RESULTS.values()],
            "seeds": list(SEEDS),
            "new_run_split": "per-seed shuffled 400 train / 143 held-out alerts from the same 543-alert fixture",
            "pre_registered_rule": ">3pp action_accuracy over matched current-VLD B=2 baseline at trained geometry for >=2/3 seeds",
            "read_cap": "current-VLD baseline and K action scorers use the same investigation vector with at most two evidence steps",
            "k_training": "supervised pairwise hinge updates from training-only fixture action votes and categories; evaluation labels excluded from fitting",
            "tier": "REAL_COMPONENT geometry + SIMULATED streams/fixture action labels",
            "fixture": "support/setup/zero_day_decisions_v5.json; same 543-alert fixture and SHA-256 as C1 historical external-baseline comparison",
            "existing_runs_seed_variance": "not measured; existing A-E artifacts are single-run",
            "two_rebuild_byte_identical_sha256_per_seed": seed_hashes,
            "c7_cross_reference": "SOC C7 A0 action_accuracy=.8867 and A3 depth3=.9267 (+4pp); routing_quality .7567 vs .7600 (+.33pp), a separate geometry/simulator and non-comparable cohort",
            "c6_cross_reference": "Trading action_accuracy abstention lift +0.16pp and S2P +0.25pp at 75% selection target; C6 is risk-coverage abstention, not an action-scorer ceiling test",
            "rho_measurement_report": "missing; existing E-SPLIT artifacts retain their stored strategy-A match flags/verdicts",
            "metrics": {
                "action_accuracy": "predicted final action equals synthetic fixture action vote",
                "routing_quality": "not measured for C8 action rescoring; no claim inferred from action_accuracy",
                "category_accuracy": "not measured in the new K action-scoring sweep",
            },
        },
    }


def _summary(payload: dict[str, Any]) -> str:
    lines = [
        "# C8 — Action-Value Boundary",
        "",
        "Tier: REAL_COMPONENT SOC centroid geometry + SIMULATED synthetic fixture/evidence/action-vote labels. Metric: action_accuracy (predicted action equals fixture action vote). `routing_quality` is not measured for the new action-rescoring sweep; `category_accuracy` is not measured there either.",
        "",
        "## Scope",
        "",
        "SOC only. This repository has a SOC scorer/pattern harness and the 543-alert fixture. The only other domain config is supply_chain/S2P, a smoke-test stub without `build_profile_scorer()` or a compatible fixture; Trading, Purchasing, and DataOps domain configs are absent. The copilot-SDK geometry files are not application configs/fixtures for this harness.",
        "",
        "## Existing SOC A–E results",
        "",
        "| Geometry | A current VLD | B route+surface | C selective | D route+selective | E oracle-category | Single-pass | Harness verdict |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for geometry in ("default", "trained", "bootstrapped"):
        row = payload["soc"][geometry]
        acc = row["existing_strategies"]
        cells = [f"{100*float(acc[key]['accuracy']):.2f}%" for key in (
            "A_current_vld", "B_route_surface", "C_selective", "D_route_selective", "E_oracle"
        )]
        lines.append(
            f"| {geometry} | " + " | ".join(cells) +
            f" | {100*float(row['single_pass_accuracy']):.2f}% | {row['verdict']} |"
        )
    trained = payload["soc"]["trained"]["existing_strategies"]
    oracle_delta_pp = 100.0 * (
        float(trained["E_oracle"]["accuracy"]) - float(trained["A_current_vld"]["accuracy"])
    )
    lines.extend([
        "",
        "The existing artifacts contain one evaluation run per geometry, each n=543; seed variance was not measured. Default and bootstrapped verdicts are ARCHITECTURE ISSUE (oracle action_accuracy is no better than single-pass). Trained verdict is VLD VALUE = SELECTIVE ENRICHMENT. At trained geometry, E is the top A–E strategy and exceeds A by "
        f"{oracle_delta_pp:.3f}pp, just below the preregistered 3pp boundary. The strategy-A/Phase-1b match flags are retained from the original harness.",
        "",
        "## New K-informed action scoring (trained geometry)",
        "",
        "Both strategies learn pairwise feature weights on 400 training alerts per seed and re-score within the category chosen by current VLD, using the same B=2 evidence vector. K-global pools learned weights across categories; K-category retains category-specific weights. The matched baseline is current VLD with the same B=2 cap and held-out 143 alerts. Existing A–E scores are retained separately and are not compared as if they were matched to these new splits.",
        "",
        "| Strategy | action_accuracy mean ± SD | Per-seed action_accuracy (Δ vs matched A) | Seeds >3pp |",
        "|---|---:|---|---:|",
    ])
    any_material = False
    for name, data in payload["soc"]["trained"]["new_strategies"].items():
        agg = data["aggregate"]
        per_seed = ", ".join(
            f"{seed}: {100*data['per_seed'][str(seed)]['action_accuracy']:.2f}% "
            f"({100*data['per_seed'][str(seed)]['delta_vs_A']:+.2f}pp)"
            for seed in SEEDS
        )
        lines.append(
            f"| {name} | {100*agg['action_mean']:.2f}% ± {100*agg['action_std']:.2f}pp | {per_seed} | {agg['beats_A_by_3pp']}/3 |"
        )
        any_material = any_material or int(agg["beats_A_by_3pp"]) >= 2
    lines.extend([
        "",
        "K-informed scoring is architecturally feasible as a standalone scorer adapter: the function can use centroid residuals, the routed category, and learned K weights without changing source or adding evidence reads. The current production path does not pass K weights into action scoring; production integration would require a separately reviewed architecture change.",
        "",
        "## Boundary, cross-campaign context, and paper wording",
        "",
    ])
    if any_material:
        lines.extend([
            "At least one K strategy crossed the preregistered >3pp action_accuracy threshold in at least two seeds. The present action-scoring boundary is exceeded for this trained SOC split; the architecture should include the winning K-informed scorer, subject to independent validation.",
            "",
            "Paper sentence: ‘On the trained SOC geometry, the tested K-informed action scorer improved held-out action_accuracy by more than 3pp in at least two of three seeded splits over matched B=2 VLD; action-scoring integration is warranted for this configuration.’",
        ])
    else:
        lines.extend([
            "Neither K strategy beat matched current-VLD B=2 by >3pp in at least two seeds. Under this test the current action-scoring boundary is not materially exceeded, but the result does not establish the geometry's absolute ceiling or rule out other learning/scoring rules.",
            "",
            "Paper sentence: ‘Across three seeded 400/143 splits of the synthetic SOC fixture at trained geometry, the tested global and category-conditioned K-weighted action scorers did not improve held-out action_accuracy by more than 3pp in at least two seeds over matched B=2 VLD; this bounds these K-scoring variants, not all possible action models.’",
        ])
    lines.extend([
        "",
        "C7 cross-reference: the separate VLD experiment found SOC action_accuracy +4pp from depth-3 rescoring while `routing_quality` moved only +0.33pp; C8 keeps these metrics separate. C6's Trading/S2P abstention lifts at 75% selection were +0.16pp/+0.25pp, but risk-coverage abstention is not an action-scoring ceiling experiment and does not establish a lower ceiling.",
        "",
        "Fixture note: E-SPLIT uses all 543 alerts from `support/setup/zero_day_decisions_v5.json`, SHA-256 `1b7c30d517d29565794746209f9d3afdd5ad16dc9185ed92fe4067f1ad102032`, also used by C1's historical external-baseline comparison. The C1 ordered 400/143 split and C8's seeded shuffled 400/143 splits differ; cross-reference values are not treated as paired.",
        "",
        "Null-stakes: a >3pp result would justify a candidate action-scoring change only for the tested trained geometry and fixture; it would not upgrade routing_quality or operational action accuracy. A null result only bounds these two K-weighted variants. Existing geometry-state outputs remain single-run and do not identify seed uncertainty.",
        "",
        "Two independent rebuilds matched byte-for-byte for each new seed. Full per-seed weights, held-out counts, paired deltas, and rebuild hashes are in the JSON.",
        "",
    ])
    return "\n".join(lines)


async def _main() -> None:
    payload = await build_payload()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    SUMMARY.write_text(_summary(payload), encoding="utf-8")
    print(f"Wrote {OUTPUT}")
    print(f"Wrote {SUMMARY}")
    for name, result in payload["soc"]["trained"]["new_strategies"].items():
        agg = result["aggregate"]
        print(
            f"{name}: action_accuracy={agg['action_mean']:.4f} "
            f"±{agg['action_std']:.4f}, delta_vs_A={agg['delta_vs_A']:+.4f}, "
            f">3pp seeds={agg['beats_A_by_3pp']}/3"
        )


if __name__ == "__main__":
    asyncio.run(_main())
