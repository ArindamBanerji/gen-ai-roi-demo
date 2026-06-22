"""
SOC Evaluation API -- EVAL-2-SOC

Runs the 36 ground-truth evaluation scenarios through the live ProfileScorer
and returns an EvaluationReport. Does NOT trigger learning.

Reference: docs/soc_copilot_design_v1.md Sec.17; gae/evaluation.py.
"""

import json
from pathlib import Path
from typing import List

import numpy as np
from fastapi import APIRouter, HTTPException

from gae.evaluation import EvaluationScenario, EvaluationReport, run_evaluation
from app.domains.soc.config import SOC_FACTORS

# Backward-compat map: new factor name → old JSON key (FEATURE-05B rename)
_LEGACY_FACTOR_NAMES: dict[str, str] = {
    "privileged_identity_context": "travel_match",
}

router = APIRouter()

_SCENARIOS_PATH = (
    Path(__file__).parent.parent / "data" / "soc_eval_scenarios.json"
)


# ============================================================================
# Helpers — exported so tests can call them directly
# ============================================================================

def load_soc_scenarios() -> List[EvaluationScenario]:
    """
    Load and deserialise all 36 SOC evaluation scenarios from JSON.

    Factor vector order matches SOC_PROFILE_CENTROIDS (SOC_FACTORS order).
    Handles both current factor names and legacy names (pre-FEATURE-05B rename).
    """
    raw = json.loads(_SCENARIOS_PATH.read_text(encoding="utf-8"))
    scenarios: List[EvaluationScenario] = []
    for s in raw:
        f = s["factors"]
        factors_list = [
            f.get(fname, f.get(_LEGACY_FACTOR_NAMES.get(fname, fname), 0.5))
            for fname in SOC_FACTORS
        ]
        scenarios.append(
            EvaluationScenario(
                scenario_id=s["scenario_id"],
                domain=s["domain"],
                category=s["category"],
                category_index=s["category_index"],
                factors=np.array(factors_list, dtype=np.float64),
                expected_action=s["expected_action"],
                expected_action_index=s["expected_action_index"],
                confidence_tier=s.get("confidence_tier", "high"),
                description=s.get("description", ""),
                expected_dominant_factors=s.get("dominant_factors", []),
            )
        )
    return scenarios


def run_soc_evaluation(scorer, scenarios: List[EvaluationScenario]) -> EvaluationReport:
    """
    Run evaluation against scenarios without modifying the scorer.
    Thin wrapper around gae.evaluation.run_evaluation with learn=False.
    """
    return run_evaluation(scorer, scenarios, oracle=None, learn=False)


# ============================================================================
# GET /evaluation/run
# ============================================================================

@router.get("/evaluation/run")
async def run_evaluation_endpoint():
    """
    Run ProfileScorer against all 36 SOC evaluation scenarios.
    Returns accuracy, per-category breakdown, ECE, and per-scenario results.
    Does NOT trigger learning -- evaluation only.
    """
    from app.services.gae_state import get_profile_scorer

    # Resolve scorer
    scorer_source = "live"
    try:
        scorer = get_profile_scorer()
    except Exception:
        scorer = None

    if scorer is None:
        raise HTTPException(
            status_code=503,
            detail={"error": "ProfileScorer not available", "status": "unavailable"},
        )

    # Load scenarios and run
    try:
        scenarios = load_soc_scenarios()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load evaluation scenarios: {exc}",
        )

    try:
        report = run_soc_evaluation(scorer, scenarios)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Evaluation run failed: {exc}",
        )

    return {
        "accuracy": report.accuracy,
        "n_scenarios": report.n_scenarios,
        "n_correct": report.n_correct,
        "by_category": report.by_category,
        "precision_per_action": report.precision_per_action,
        "recall_per_action": report.recall_per_action,
        "ece": report.ece,
        "scenario_results": report.scenario_results,
        "scorer_source": scorer_source,
        "note": "Evaluation run without learning. Scorer not modified.",
    }


# ============================================================================
# GET /evaluation/summary
# ============================================================================

@router.get("/evaluation/summary")
async def get_evaluation_summary():
    """
    Compact evaluation summary for dashboard display.
    Same evaluation logic as /run but omits per-scenario results.
    """
    from app.services.gae_state import get_profile_scorer

    scorer_source = "live"
    try:
        scorer = get_profile_scorer()
    except Exception:
        scorer = None

    if scorer is None:
        raise HTTPException(
            status_code=503,
            detail={"error": "ProfileScorer not available", "status": "unavailable"},
        )

    try:
        scenarios = load_soc_scenarios()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load evaluation scenarios: {exc}",
        )

    try:
        report = run_soc_evaluation(scorer, scenarios)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Evaluation run failed: {exc}",
        )

    top_action = (
        max(report.precision_per_action, key=report.precision_per_action.get)
        if report.precision_per_action
        else None
    )
    lowest_cat = (
        min(report.by_category, key=report.by_category.get)
        if report.by_category
        else None
    )

    return {
        "accuracy": report.accuracy,
        "n_scenarios": report.n_scenarios,
        "n_correct": report.n_correct,
        "by_category": report.by_category,
        "ece": report.ece,
        "top_action_precision": top_action,
        "lowest_category_accuracy": lowest_cat,
        "scorer_source": scorer_source,
    }
