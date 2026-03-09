"""
EVAL-2-SOC: Evaluation runner tests.

Verifies that the evaluation router is registered, scenarios convert
correctly to EvaluationScenario objects, and run_evaluation() produces
a well-formed EvaluationReport using the SOC baseline centroids.

Run from backend/:
    pytest tests/test_eval2_soc.py -v
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ============================================================================
# TEST 1 — /api/soc/evaluation/run route registered
# ============================================================================

def test_evaluation_run_endpoint_registered():
    """GET /api/soc/evaluation/run must be registered on the FastAPI app."""
    from app.main import app
    routes = [r.path for r in app.routes]
    assert "/api/soc/evaluation/run" in routes, (
        f"Route not found. Registered routes: {routes}"
    )


# ============================================================================
# TEST 2 — /api/soc/evaluation/summary route registered
# ============================================================================

def test_evaluation_summary_endpoint_registered():
    """GET /api/soc/evaluation/summary must be registered on the FastAPI app."""
    from app.main import app
    routes = [r.path for r in app.routes]
    assert "/api/soc/evaluation/summary" in routes, (
        f"Route not found. Registered routes: {routes}"
    )


# ============================================================================
# TEST 3 — Scenarios load and convert to EvaluationScenario objects
# ============================================================================

def test_scenarios_load_correctly():
    """Scenarios file loads and converts to EvaluationScenario objects."""
    from app.routers.evaluation import load_soc_scenarios
    import numpy as np

    scenarios = load_soc_scenarios()
    assert len(scenarios) == 36, (
        f"Expected 36 scenarios, got {len(scenarios)}"
    )
    for s in scenarios:
        assert s.factors.shape == (6,), (
            f"{s.scenario_id}: factors shape {s.factors.shape}, expected (6,)"
        )
        assert 0.0 <= s.factors.min() <= s.factors.max() <= 1.0, (
            f"{s.scenario_id}: factor values out of [0.0, 1.0]: {s.factors}"
        )


# ============================================================================
# TEST 4 — EvaluationReport has expected shape
# ============================================================================

def test_evaluation_report_shape():
    """run_evaluation returns report with expected fields."""
    from app.routers.evaluation import load_soc_scenarios, run_soc_evaluation
    from app.domains.soc.config import SOC_PROFILE_CENTROIDS, SOC_ACTIONS
    from gae import ProfileScorer
    import numpy as np

    scorer = ProfileScorer(
        mu=np.array(SOC_PROFILE_CENTROIDS),
        actions=SOC_ACTIONS,
    )
    scenarios = load_soc_scenarios()
    report = run_soc_evaluation(scorer, scenarios)

    assert 0.0 <= report.accuracy <= 1.0, (
        f"accuracy {report.accuracy} out of [0.0, 1.0]"
    )
    assert report.n_scenarios == 36, (
        f"n_scenarios expected 36, got {report.n_scenarios}"
    )
    assert len(report.by_category) == 6, (
        f"by_category expected 6 entries, got {len(report.by_category)}"
    )


# ============================================================================
# TEST 5 — Baseline accuracy above random floor (>25% for 4 actions)
# ============================================================================

def test_evaluation_accuracy_above_floor():
    """Baseline centroids should score above random (>25% for 4 actions)."""
    from app.routers.evaluation import load_soc_scenarios, run_soc_evaluation
    from app.domains.soc.config import SOC_PROFILE_CENTROIDS, SOC_ACTIONS
    from gae import ProfileScorer
    import numpy as np

    scorer = ProfileScorer(
        mu=np.array(SOC_PROFILE_CENTROIDS),
        actions=SOC_ACTIONS,
    )
    scenarios = load_soc_scenarios()
    report = run_soc_evaluation(scorer, scenarios)

    assert report.accuracy > 0.25, (
        f"Accuracy {report.accuracy} not above random baseline of 0.25"
    )


# ============================================================================
# TEST 6 — by_category contains all 6 SOC categories
# ============================================================================

def test_by_category_all_6_present():
    """EvaluationReport.by_category must contain all 6 SOC categories."""
    from app.domains.soc.config import SOC_CATEGORIES
    from app.routers.evaluation import load_soc_scenarios, run_soc_evaluation
    from app.domains.soc.config import SOC_PROFILE_CENTROIDS, SOC_ACTIONS
    from gae import ProfileScorer
    import numpy as np

    scorer = ProfileScorer(
        mu=np.array(SOC_PROFILE_CENTROIDS),
        actions=SOC_ACTIONS,
    )
    scenarios = load_soc_scenarios()
    report = run_soc_evaluation(scorer, scenarios)

    for cat in SOC_CATEGORIES:
        assert cat in report.by_category, (
            f"Category {cat!r} missing from by_category. "
            f"Present: {list(report.by_category.keys())}"
        )


# ============================================================================
# TEST 7 — Evaluation does not modify scorer (learn=False)
# ============================================================================

def test_evaluation_does_not_modify_scorer():
    """learn=False — scorer mu must not change after evaluation."""
    from app.routers.evaluation import load_soc_scenarios, run_soc_evaluation
    from app.domains.soc.config import SOC_PROFILE_CENTROIDS, SOC_ACTIONS
    from gae import ProfileScorer
    import numpy as np

    mu_original = np.array(SOC_PROFILE_CENTROIDS).copy()
    scorer = ProfileScorer(
        mu=np.array(SOC_PROFILE_CENTROIDS),
        actions=SOC_ACTIONS,
    )
    scenarios = load_soc_scenarios()
    run_soc_evaluation(scorer, scenarios)

    np.testing.assert_array_equal(
        scorer.mu, mu_original,
        err_msg="scorer.mu was modified during evaluation (learn=False expected)"
    )


# ============================================================================
# TEST 8 — EvaluationReport has all required summary fields
# ============================================================================

def test_summary_has_required_fields():
    """EvaluationReport dataclass must expose required summary fields."""
    from app.routers.evaluation import load_soc_scenarios, run_soc_evaluation
    from app.domains.soc.config import SOC_PROFILE_CENTROIDS, SOC_ACTIONS
    from gae import ProfileScorer, EvaluationReport
    import numpy as np

    scorer = ProfileScorer(
        mu=np.array(SOC_PROFILE_CENTROIDS),
        actions=SOC_ACTIONS,
    )
    scenarios = load_soc_scenarios()
    report = run_soc_evaluation(scorer, scenarios)

    required = {"accuracy", "n_scenarios", "n_correct", "by_category", "ece"}
    assert required.issubset(report.__dataclass_fields__.keys()), (
        f"Missing fields: {required - set(report.__dataclass_fields__.keys())}"
    )
