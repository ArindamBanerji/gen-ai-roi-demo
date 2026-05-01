"""
FEATURE-01 upload evaluation tests.

Run from backend/:
    python -m pytest tests/test_eval_upload.py -v
"""

import io
import os
import pickle
import sys
from copy import deepcopy

import numpy as np
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.main import app
from app.services import eval_service
from app.services.eval_service import REQUIRED_COLUMNS, run_evaluation, validate_csv_rows
from app.domains.soc.config import SCORER_ACTIONS, SOC_CATEGORIES, SOC_PROFILE_CENTROIDS
from gae import ProfileScorer


def _make_csv(rows):
    buffer = io.StringIO()
    headers = ["row_id"] + REQUIRED_COLUMNS
    buffer.write(",".join(headers) + "\n")
    for row in rows:
        values = [str(row.get(header, "")) for header in headers]
        buffer.write(",".join(values) + "\n")
    return buffer.getvalue()


def _base_row(
    row_id="row-1",
    category="credential_access",
    ground_truth_action="escalate",
    values=None,
):
    values = values or [0.95, 0.90, 0.85, 0.75, 0.80, 0.10]
    row = {
        "row_id": row_id,
        "category": category,
        "ground_truth_action": ground_truth_action,
    }
    for idx, factor_name in enumerate(eval_service.SOC_FACTORS):
        row[factor_name] = values[idx]
    return row


def _service_rows(rows):
    return list(enumerate(rows, start=2))


def _make_scorer():
    return ProfileScorer(
        mu=np.array(SOC_PROFILE_CENTROIDS, dtype=np.float64),
        actions=list(SCORER_ACTIONS),
        categories=list(SOC_CATEGORIES),
        eta_override=0.01,
        auto_pause_on_amber=True,
    )


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def test_validate_missing_required_column_detected_by_router(client):
    csv_text = "row_id,category,ground_truth_action,privileged_identity_context\nx,credential_access,escalate,0.9\n"
    response = client.post(
        "/api/eval/upload",
        files={"file": ("input.csv", csv_text, "text/csv")},
    )
    assert response.status_code == 400
    payload = response.json()
    assert "missing_columns" in payload["detail"]
    assert "asset_criticality" in payload["detail"]["missing_columns"]


def test_validate_invalid_category():
    rows = _service_rows([
        _base_row(category="not_a_category"),
    ])
    clean_rows, errors, _warnings = validate_csv_rows(rows)
    assert clean_rows == []
    assert errors[0]["row_number"] == 2
    assert "category must be one of" in errors[0]["errors"][0]


def test_validate_invalid_action():
    rows = _service_rows([
        _base_row(ground_truth_action="close_case"),
    ])
    clean_rows, errors, _warnings = validate_csv_rows(rows)
    assert clean_rows == []
    assert errors[0]["row_number"] == 2
    assert "ground_truth_action must be one of" in errors[0]["errors"][0]


def test_validate_factor_out_of_range():
    rows = _service_rows([
        _base_row(values=[1.20, 0.90, 0.85, 0.75, 0.80, 0.10]),
    ])
    clean_rows, errors, _warnings = validate_csv_rows(rows)
    assert clean_rows == []
    assert errors[0]["row_number"] == 2
    assert "privileged_identity_context must be in [0.0, 1.0]" in errors[0]["errors"][0]


def test_validate_over_ten_percent_invalid_rows_rejected(client):
    rows = [
        _base_row(row_id="good-1"),
        _base_row(row_id="bad-1", category="bad_category"),
        _base_row(row_id="good-2"),
        _base_row(row_id="good-3"),
        _base_row(row_id="good-4"),
    ]
    response = client.post(
        "/api/eval/upload",
        files={"file": ("input.csv", _make_csv(rows), "text/csv")},
    )
    assert response.status_code == 422
    payload = response.json()["detail"]
    assert payload["invalid_rows"] == 1
    assert payload["total_rows"] == 5
    assert payload["row_errors"][0]["row_number"] == 3


def test_validate_empty_csv_rejected(client):
    response = client.post(
        "/api/eval/upload",
        files={"file": ("input.csv", "", "text/csv")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded CSV is empty"


def test_run_evaluation_returns_accuracy_and_convergence_trajectories(monkeypatch):
    scorer = _make_scorer()
    rows = [
        _base_row(row_id="row-1"),
        _base_row(row_id="row-2", category="malware_execution", ground_truth_action="investigate",
                  values=[0.20, 0.75, 0.65, 0.70, 0.45, 0.35]),
    ]
    clean_rows, errors, _warnings = validate_csv_rows(_service_rows(rows))
    assert errors == []

    monkeypatch.setattr(eval_service, "get_profile_scorer", lambda: scorer)
    monkeypatch.setattr(
        eval_service,
        "get_mu_zero",
        lambda: np.array(SOC_PROFILE_CENTROIDS, dtype=np.float64),
    )

    result = run_evaluation(clean_rows)
    assert len(result.accuracy_trajectory) == 2
    assert len(result.convergence_trajectory) == 2
    assert result.accuracy_trajectory[-1]["decision_number"] == 2
    assert "drift_from_mu_zero" in result.convergence_trajectory[-1]


def test_run_evaluation_does_not_mutate_production_scorer(monkeypatch):
    scorer = _make_scorer()
    before_bytes = pickle.dumps(scorer)
    before_centroids = scorer.centroids.copy()
    before_counts = scorer.counts.copy()
    before_eta_override = scorer.eta_override
    before_decision_count = scorer.decision_count

    rows = [
        _base_row(row_id="row-1"),
        _base_row(
            row_id="row-2",
            category="credential_access",
            ground_truth_action="suppress",
            values=[0.10, 0.15, 0.15, 0.10, 0.15, 0.90],
        ),
    ]
    clean_rows, errors, _warnings = validate_csv_rows(_service_rows(rows))
    assert errors == []

    monkeypatch.setattr(eval_service, "get_profile_scorer", lambda: scorer)
    monkeypatch.setattr(
        eval_service,
        "get_mu_zero",
        lambda: np.array(SOC_PROFILE_CENTROIDS, dtype=np.float64),
    )

    result = run_evaluation(clean_rows)
    assert result.evaluated_rows == 2
    assert pickle.dumps(scorer) == before_bytes
    np.testing.assert_array_equal(scorer.centroids, before_centroids)
    np.testing.assert_array_equal(scorer.counts, before_counts)
    assert scorer.eta_override == before_eta_override
    assert scorer.decision_count == before_decision_count


class _ImprovingFakeScorer:
    def __init__(self):
        self.actions = list(SCORER_ACTIONS)
        self.categories = list(SOC_CATEGORIES)
        self.centroids = np.zeros((6, 4, 6), dtype=np.float64)
        self.counts = np.zeros((6, 4), dtype=np.int64)
        self.decision_count = 0
        self.eta_override = 0.01
        self.kernel = "fake"
        self._correct_mode = False

    def __deepcopy__(self, memo):
        copied = _ImprovingFakeScorer()
        copied.centroids = self.centroids.copy()
        copied.counts = self.counts.copy()
        copied.decision_count = self.decision_count
        copied.eta_override = self.eta_override
        copied.kernel = self.kernel
        copied._correct_mode = self._correct_mode
        return copied

    def score(self, f, category_index):
        class _Result:
            pass

        result = _Result()
        if self._correct_mode:
            result.action_index = 0
            result.action_name = "escalate"
            result.confidence = 0.91
            result.probabilities = np.array([0.91, 0.03, 0.03, 0.03], dtype=np.float64)
        else:
            result.action_index = 1
            result.action_name = "investigate"
            result.confidence = 0.55
            result.probabilities = np.array([0.20, 0.55, 0.15, 0.10], dtype=np.float64)
        return result

    def update(self, f, category_index, action_index, correct, gt_action_index=None, confidence=None):
        self._correct_mode = True
        self.centroids[category_index, gt_action_index or 0, :] += 0.1
        self.counts[category_index, action_index] += 1
        self.decision_count += 1
        return None


def test_accuracy_improves_over_decisions(monkeypatch):
    scorer = _ImprovingFakeScorer()
    rows = [
        _base_row(row_id="row-1", ground_truth_action="escalate"),
        _base_row(row_id="row-2", ground_truth_action="escalate"),
        _base_row(row_id="row-3", ground_truth_action="escalate"),
    ]
    clean_rows, errors, _warnings = validate_csv_rows(_service_rows(rows))
    assert errors == []

    monkeypatch.setattr(eval_service, "get_profile_scorer", lambda: scorer)
    monkeypatch.setattr(eval_service, "get_mu_zero", lambda: np.zeros((6, 4, 6), dtype=np.float64))

    result = run_evaluation(clean_rows)
    acc_values = [point["accuracy"] for point in result.accuracy_trajectory]
    assert acc_values[0] < acc_values[-1]


def test_run_evaluation_handles_single_category(monkeypatch):
    scorer = _make_scorer()
    rows = [
        _base_row(row_id="row-1", category="credential_access"),
        _base_row(row_id="row-2", category="credential_access"),
    ]
    clean_rows, errors, _warnings = validate_csv_rows(_service_rows(rows))
    assert errors == []

    monkeypatch.setattr(eval_service, "get_profile_scorer", lambda: scorer)
    monkeypatch.setattr(
        eval_service,
        "get_mu_zero",
        lambda: np.array(SOC_PROFILE_CENTROIDS, dtype=np.float64),
    )

    result = run_evaluation(clean_rows)
    assert set(result.category_counts.keys()) == {"credential_access"}


def test_run_evaluation_handles_all_categories(monkeypatch):
    scorer = _make_scorer()
    rows = [
        _base_row(row_id="row-1", category="credential_access"),
        _base_row(row_id="row-2", category="malware_execution", ground_truth_action="investigate",
                  values=[0.20, 0.75, 0.65, 0.70, 0.45, 0.35]),
        _base_row(row_id="row-3", category="lateral_movement", ground_truth_action="investigate",
                  values=[0.35, 0.80, 0.55, 0.85, 0.55, 0.25]),
        _base_row(row_id="row-4", category="data_exfiltration", ground_truth_action="monitor",
                  values=[0.30, 0.60, 0.45, 0.40, 0.55, 0.70]),
        _base_row(row_id="row-5", category="insider_threat", ground_truth_action="suppress",
                  values=[0.15, 0.40, 0.20, 0.25, 0.15, 0.85]),
        _base_row(row_id="row-6", category="cloud_infrastructure", ground_truth_action="monitor",
                  values=[0.15, 0.55, 0.25, 0.30, 0.35, 0.80]),
    ]
    clean_rows, errors, _warnings = validate_csv_rows(_service_rows(rows))
    assert errors == []

    monkeypatch.setattr(eval_service, "get_profile_scorer", lambda: scorer)
    monkeypatch.setattr(
        eval_service,
        "get_mu_zero",
        lambda: np.array(SOC_PROFILE_CENTROIDS, dtype=np.float64),
    )

    result = run_evaluation(clean_rows)
    assert set(result.category_counts.keys()) == set(SOC_CATEGORIES)


def test_cold_start_returns_503(client, monkeypatch):
    monkeypatch.setattr(eval_service, "get_profile_scorer", lambda: None)
    csv_text = _make_csv([_base_row()])
    response = client.post(
        "/api/eval/upload",
        files={"file": ("input.csv", csv_text, "text/csv")},
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "ProfileScorer not initialized"


def test_upload_endpoint_accepts_csv(client, monkeypatch):
    scorer = _make_scorer()
    monkeypatch.setattr(eval_service, "get_profile_scorer", lambda: scorer)
    monkeypatch.setattr(
        eval_service,
        "get_mu_zero",
        lambda: np.array(SOC_PROFILE_CENTROIDS, dtype=np.float64),
    )

    response = client.post(
        "/api/eval/upload",
        files={"file": ("input.csv", _make_csv([_base_row()]), "text/csv")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["evaluated_rows"] == 1
    assert len(payload["accuracy_trajectory"]) == 1


def test_upload_endpoint_rejects_invalid_csv(client):
    response = client.post(
        "/api/eval/upload",
        files={"file": ("input.txt", "not,csv", "text/plain")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Expected a CSV upload"


def test_templates_endpoint_returns_formats(client):
    response = client.get("/api/eval/templates")
    assert response.status_code == 200
    payload = response.json()
    assert {item["format"] for item in payload["formats"]} == {"generic", "sentinel", "splunk"}


def test_template_download_returns_csv(client):
    response = client.get("/api/eval/templates/generic.csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    body = response.text
    assert "row_id,category,ground_truth_action" in body


class _ConvergingFakeScorer:
    """Centroids start far from mu_zero (zeros) and shrink toward it each update."""

    def __init__(self):
        self.actions = list(SCORER_ACTIONS)
        self.categories = list(SOC_CATEGORIES)
        self.centroids = np.ones((6, 4, 6), dtype=np.float64) * 10.0
        self.counts = np.zeros((6, 4), dtype=np.int64)
        self.decision_count = 0
        self.eta_override = 0.01
        self.kernel = "fake"

    def __deepcopy__(self, memo):
        copied = _ConvergingFakeScorer()
        copied.centroids = self.centroids.copy()
        copied.counts = self.counts.copy()
        copied.decision_count = self.decision_count
        copied.eta_override = self.eta_override
        return copied

    def score(self, f, category_index):
        class _R:
            action_index = 0
            action_name = "escalate"
            confidence = 0.75
            probabilities = np.array([0.75, 0.1, 0.1, 0.05], dtype=np.float64)
        return _R()

    def update(self, f, category_index, action_index, correct, gt_action_index=None, confidence=None):
        self.centroids *= 0.85
        self.counts[category_index, action_index] += 1
        self.decision_count += 1


class _StaticProbabilityFakeScorer:
    def __init__(self, confidence, probabilities):
        self.actions = list(SCORER_ACTIONS)
        self.categories = list(SOC_CATEGORIES)
        self.centroids = np.zeros((6, 4, 6), dtype=np.float64)
        self.counts = np.zeros((6, 4), dtype=np.int64)
        self.decision_count = 0
        self.eta_override = 0.01
        self.kernel = "fake"
        self._confidence = float(confidence)
        self._probabilities = np.array(probabilities, dtype=np.float64)

    def __deepcopy__(self, memo):
        copied = _StaticProbabilityFakeScorer(self._confidence, self._probabilities.copy())
        copied.centroids = self.centroids.copy()
        copied.counts = self.counts.copy()
        copied.decision_count = self.decision_count
        copied.eta_override = self.eta_override
        copied.kernel = self.kernel
        return copied

    def score(self, f, category_index):
        class _R:
            pass

        result = _R()
        result.action_index = int(np.argmax(self._probabilities))
        result.action_name = self.actions[result.action_index]
        result.confidence = self._confidence
        result.probabilities = self._probabilities.copy()
        return result

    def update(self, f, category_index, action_index, correct, gt_action_index=None, confidence=None):
        self.counts[category_index, action_index] += 1
        self.decision_count += 1


def test_eval_returns_direction_fields(monkeypatch):
    scorer = _make_scorer()
    rows = [_base_row(row_id=f"row-{i}") for i in range(3)]
    clean_rows, errors, _warnings = validate_csv_rows(_service_rows(rows))
    assert errors == []

    monkeypatch.setattr(eval_service, "get_profile_scorer", lambda: scorer)
    monkeypatch.setattr(
        eval_service,
        "get_mu_zero",
        lambda: np.array(SOC_PROFILE_CENTROIDS, dtype=np.float64),
    )

    result = run_evaluation(clean_rows)
    assert hasattr(result, "learning_direction")
    assert hasattr(result, "distance_change_pct")
    assert hasattr(result, "calibration_warning")
    assert result.learning_direction in {"correct", "wrong", "insufficient_data"}
    assert isinstance(result.distance_change_pct, float)
    assert isinstance(result.calibration_warning, bool)


def test_eval_insufficient_data_with_few_rows(monkeypatch):
    scorer = _make_scorer()
    rows = [_base_row(row_id="row-1"), _base_row(row_id="row-2")]
    clean_rows, errors, _warnings = validate_csv_rows(_service_rows(rows))
    assert errors == []

    monkeypatch.setattr(eval_service, "get_profile_scorer", lambda: scorer)
    monkeypatch.setattr(
        eval_service,
        "get_mu_zero",
        lambda: np.array(SOC_PROFILE_CENTROIDS, dtype=np.float64),
    )

    result = run_evaluation(clean_rows)
    assert result.learning_direction == "insufficient_data"


def test_eval_correct_direction_when_converging(monkeypatch):
    scorer = _ConvergingFakeScorer()
    rows = [_base_row(row_id=f"row-{i}", ground_truth_action="escalate") for i in range(50)]
    clean_rows, errors, _warnings = validate_csv_rows(_service_rows(rows))
    assert errors == []

    monkeypatch.setattr(eval_service, "get_profile_scorer", lambda: scorer)
    monkeypatch.setattr(eval_service, "get_mu_zero", lambda: np.zeros((6, 4, 6), dtype=np.float64))

    result = run_evaluation(clean_rows)
    assert result.learning_direction == "correct"
    assert result.distance_change_pct < 0


def test_eval_includes_majority_baseline(monkeypatch):
    scorer = _make_scorer()
    rows = [
        _base_row(row_id="row-1", ground_truth_action="escalate"),
        _base_row(row_id="row-2", ground_truth_action="investigate"),
        _base_row(row_id="row-3", ground_truth_action="escalate"),
    ]
    clean_rows, errors, _warnings = validate_csv_rows(_service_rows(rows))
    assert errors == []

    monkeypatch.setattr(eval_service, "get_profile_scorer", lambda: scorer)
    monkeypatch.setattr(
        eval_service,
        "get_mu_zero",
        lambda: np.array(SOC_PROFILE_CENTROIDS, dtype=np.float64),
    )

    result = run_evaluation(clean_rows)
    assert hasattr(result, "majority_baseline")
    assert "accuracy" in result.majority_baseline
    assert "per_category" in result.majority_baseline
    assert "credential_access" in result.majority_baseline["per_category"]
    entry = result.majority_baseline["per_category"]["credential_access"]
    assert "majority_action" in entry
    assert "accuracy" in entry
    assert entry["majority_action"] == "escalate"


def test_eval_majority_accuracy_in_valid_range(monkeypatch):
    scorer = _make_scorer()
    rows = [_base_row(row_id=f"row-{i}") for i in range(5)]
    clean_rows, errors, _warnings = validate_csv_rows(_service_rows(rows))
    assert errors == []

    monkeypatch.setattr(eval_service, "get_profile_scorer", lambda: scorer)
    monkeypatch.setattr(
        eval_service,
        "get_mu_zero",
        lambda: np.array(SOC_PROFILE_CENTROIDS, dtype=np.float64),
    )

    result = run_evaluation(clean_rows)
    acc = result.majority_baseline.get("accuracy", -1)
    assert 0.0 <= acc <= 1.0, f"majority accuracy {acc} not in [0, 1]"


def test_eval_learning_advantage_computed(monkeypatch):
    scorer = _make_scorer()
    rows = [_base_row(row_id=f"row-{i}") for i in range(5)]
    clean_rows, errors, _warnings = validate_csv_rows(_service_rows(rows))
    assert errors == []

    monkeypatch.setattr(eval_service, "get_profile_scorer", lambda: scorer)
    monkeypatch.setattr(
        eval_service,
        "get_mu_zero",
        lambda: np.array(SOC_PROFILE_CENTROIDS, dtype=np.float64),
    )

    result = run_evaluation(clean_rows)
    assert hasattr(result, "learning_advantage_over_majority")
    assert isinstance(result.learning_advantage_over_majority, float)
    majority_acc = result.majority_baseline["accuracy"]
    expected_advantage = round(result.accuracy - majority_acc, 6)
    assert abs(result.learning_advantage_over_majority - expected_advantage) < 1e-5


def test_eval_ceiling_estimate_present(monkeypatch):
    scorer = _make_scorer()
    rows = [_base_row(row_id="row-1")]
    clean_rows, errors, _warnings = validate_csv_rows(_service_rows(rows))
    assert errors == []

    monkeypatch.setattr(eval_service, "get_profile_scorer", lambda: scorer)
    monkeypatch.setattr(
        eval_service,
        "get_mu_zero",
        lambda: np.array(SOC_PROFILE_CENTROIDS, dtype=np.float64),
    )

    result = run_evaluation(clean_rows)
    assert "overall" in result.ceiling_estimate
    assert isinstance(result.ceiling_estimate["overall"], float)
    assert result.ceiling_estimate["overall"] > 0.0
    assert "Approximate structural estimate" in result.ceiling_estimate["note"]


def test_eval_ceiling_per_category_has_all_categories(monkeypatch):
    scorer = _make_scorer()
    rows = [_base_row(row_id="row-1")]
    clean_rows, errors, _warnings = validate_csv_rows(_service_rows(rows))
    assert errors == []

    monkeypatch.setattr(eval_service, "get_profile_scorer", lambda: scorer)
    monkeypatch.setattr(
        eval_service,
        "get_mu_zero",
        lambda: np.array(SOC_PROFILE_CENTROIDS, dtype=np.float64),
    )

    result = run_evaluation(clean_rows)
    assert set(result.ceiling_estimate["per_category"].keys()) == set(SOC_CATEGORIES)
    assert all(
        isinstance(result.ceiling_estimate["per_category"][category], float)
        for category in SOC_CATEGORIES
    )


def test_eval_confidence_note_present_when_low(monkeypatch):
    scorer = _StaticProbabilityFakeScorer(0.26, [0.26, 0.25, 0.25, 0.24])
    rows = [_base_row(row_id=f"row-{i}") for i in range(3)]
    clean_rows, errors, _warnings = validate_csv_rows(_service_rows(rows))
    assert errors == []

    monkeypatch.setattr(eval_service, "get_profile_scorer", lambda: scorer)
    monkeypatch.setattr(eval_service, "get_mu_zero", lambda: np.zeros((6, 4, 6), dtype=np.float64))

    result = run_evaluation(clean_rows)
    assert result.confidence_note is not None
    assert "random baseline (0.25)" in result.confidence_note


def test_eval_confidence_note_null_when_high(monkeypatch):
    scorer = _StaticProbabilityFakeScorer(0.75, [0.75, 0.1, 0.1, 0.05])
    rows = [_base_row(row_id="row-1")]
    clean_rows, errors, _warnings = validate_csv_rows(_service_rows(rows))
    assert errors == []

    monkeypatch.setattr(eval_service, "get_profile_scorer", lambda: scorer)
    monkeypatch.setattr(eval_service, "get_mu_zero", lambda: np.zeros((6, 4, 6), dtype=np.float64))

    result = run_evaluation(clean_rows)
    assert result.confidence_note is None


def test_eval_convergence_pct_per_category(monkeypatch):
    scorer = _make_scorer()
    rows = [
        _base_row(row_id="row-1", category="credential_access"),
        _base_row(row_id="row-2", category="credential_access"),
        _base_row(
            row_id="row-3",
            category="malware_execution",
            ground_truth_action="investigate",
            values=[0.20, 0.75, 0.65, 0.70, 0.45, 0.35],
        ),
    ]
    clean_rows, errors, _warnings = validate_csv_rows(_service_rows(rows))
    assert errors == []

    monkeypatch.setattr(eval_service, "get_profile_scorer", lambda: scorer)
    monkeypatch.setattr(
        eval_service,
        "get_mu_zero",
        lambda: np.array(SOC_PROFILE_CENTROIDS, dtype=np.float64),
    )

    result = run_evaluation(clean_rows)
    assert result.per_category_results
    by_category = {entry["category"]: entry for entry in result.per_category_results}
    assert by_category["credential_access"]["verified_count"] == 2
    assert 0.0 <= by_category["credential_access"]["convergence_pct"] <= 100.0
    assert by_category["credential_access"]["decisions_to_90pct"] >= 0
    assert 0.0 <= by_category["malware_execution"]["convergence_pct"] <= 100.0
    assert by_category["malware_execution"]["decisions_to_90pct"] >= 0


def test_eval_convergence_summary_present(monkeypatch):
    scorer = _make_scorer()
    rows = [_base_row(row_id=f"row-{i}") for i in range(5)]
    clean_rows, errors, _warnings = validate_csv_rows(_service_rows(rows))
    assert errors == []

    monkeypatch.setattr(eval_service, "get_profile_scorer", lambda: scorer)
    monkeypatch.setattr(
        eval_service,
        "get_mu_zero",
        lambda: np.array(SOC_PROFILE_CENTROIDS, dtype=np.float64),
    )

    result = run_evaluation(clean_rows)
    assert "average_convergence_pct" in result.convergence_summary
    assert "total_verified" in result.convergence_summary
    assert "note" in result.convergence_summary
    assert result.convergence_summary["total_verified"] == 5
    assert 0.0 <= result.convergence_summary["average_convergence_pct"] <= 100.0
    assert "N_half=13.51" in result.convergence_summary["note"]


def test_eval_ambiguous_decisions_flagged(monkeypatch):
    scorer = _StaticProbabilityFakeScorer(0.28, [0.28, 0.24, 0.24, 0.24])
    rows = [_base_row(row_id="row-1")]
    clean_rows, errors, _warnings = validate_csv_rows(_service_rows(rows))
    assert errors == []

    monkeypatch.setattr(eval_service, "get_profile_scorer", lambda: scorer)
    monkeypatch.setattr(eval_service, "get_mu_zero", lambda: np.zeros((6, 4, 6), dtype=np.float64))

    result = run_evaluation(clean_rows)
    assert result.per_decision_log[0]["ambiguous"] is True
    assert "ambiguity_note" in result.per_decision_log[0]
    assert result.per_decision_log[0]["probabilities"] == [0.28, 0.24, 0.24, 0.24]


def test_eval_ambiguity_summary_count(monkeypatch):
    scorer = _StaticProbabilityFakeScorer(0.28, [0.28, 0.24, 0.24, 0.24])
    rows = [_base_row(row_id=f"row-{i}") for i in range(2)]
    clean_rows, errors, _warnings = validate_csv_rows(_service_rows(rows))
    assert errors == []

    monkeypatch.setattr(eval_service, "get_profile_scorer", lambda: scorer)
    monkeypatch.setattr(eval_service, "get_mu_zero", lambda: np.zeros((6, 4, 6), dtype=np.float64))

    result = run_evaluation(clean_rows)
    assert result.ambiguity_summary["ambiguous_decisions"] == 2
    assert result.ambiguity_summary["ambiguous_pct"] == 100.0
    assert "structural ties, not system errors" in result.ambiguity_summary["note"]
