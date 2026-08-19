"""SOC-03 novelty and counterfactual explanation tests."""

from __future__ import annotations

import json

import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.services.soc_explainability import NoPrecedentDetector, WhatIfInspector


FACTOR_NAMES = (
    "privileged_identity_context",
    "asset_criticality",
    "threat_intel_enrichment",
    "pattern_history",
    "time_anomaly",
    "device_trust",
)
ACTIONS = ("escalate", "investigate", "suppress", "monitor")


def centroids() -> np.ndarray:
    return np.array(
        [
            [
                [0.8, 0.8, 0.8, 0.8, 0.8, 0.2],
                [0.6, 0.6, 0.6, 0.6, 0.6, 0.4],
                [0.2, 0.2, 0.2, 0.2, 0.2, 0.8],
                [0.3, 0.4, 0.3, 0.3, 0.3, 0.7],
            ],
            [
                [0.9, 0.9, 0.9, 0.9, 0.9, 0.1],
                [0.55, 0.55, 0.55, 0.55, 0.55, 0.45],
                [0.1, 0.1, 0.1, 0.1, 0.1, 0.9],
                [0.4, 0.4, 0.4, 0.4, 0.4, 0.6],
            ],
        ],
        dtype=float,
    )


def detector(**kwargs) -> NoPrecedentDetector:
    return NoPrecedentDetector(
        centroids(),
        categories=("credential_access", "malware_execution"),
        actions=ACTIONS,
        factor_names=FACTOR_NAMES,
        **kwargs,
    )


def test_NP_01_novel_alert_detected():
    result = detector(thresholds={"credential_access": 0.25}).detect([1, 1, 1, 1, 1, 0], "credential_access")
    assert result.is_novel is True
    assert result.min_distance > result.threshold


def test_NP_02_known_alert_not_flagged():
    result = detector(thresholds={"credential_access": 0.25}).detect([0.8, 0.8, 0.8, 0.8, 0.8, 0.2], "credential_access")
    assert result.is_novel is False
    assert result.similar_count >= 1


def test_NP_03_missing_evidence_lists_anomalous_factors():
    result = detector(thresholds={"credential_access": 0.25}).detect([0.8, 0.8, 0.1, 0.8, 0.8, 0.2], "credential_access")
    assert "threat_intel_enrichment" in result.missing_evidence


def test_NP_04_similar_count_matches_centroid_population():
    result = detector(thresholds={"credential_access": 0.7}).detect([0.6, 0.6, 0.6, 0.6, 0.6, 0.4], "credential_access")
    expected = sum(np.linalg.norm(row - np.array([0.6, 0.6, 0.6, 0.6, 0.6, 0.4])) <= 0.7 for row in centroids()[0])
    assert result.similar_count == expected


def test_NP_05_threshold_is_category_specific():
    instance = detector(thresholds={"credential_access": 0.2, "malware_execution": 0.8})
    assert instance.threshold_for("credential_access") != instance.threshold_for("malware_execution")


def test_WI_01_boundary_is_midpoint():
    result = WhatIfInspector(centroids(), categories=("credential_access", "malware_execution"), actions=ACTIONS, factor_names=FACTOR_NAMES).inspect([0.8] * 5 + [0.2], "credential_access", "escalate")
    first = result.per_factor[0]
    assert first.boundary_value == 0.7


def test_WI_02_direction_identifies_delta_sign():
    result = WhatIfInspector(centroids(), categories=("credential_access", "malware_execution"), actions=ACTIONS, factor_names=FACTOR_NAMES).inspect([0.8] * 5 + [0.2], "credential_access", "escalate")
    device = result.per_factor[-1]
    assert device.direction == "increase"


def test_WI_03_magnitude_is_actual_delta():
    result = WhatIfInspector(centroids(), categories=("credential_access", "malware_execution"), actions=ACTIONS, factor_names=FACTOR_NAMES).inspect([0.8] * 5 + [0.2], "credential_access", "escalate")
    assert result.per_factor[-1].magnitude == 0.1


def test_WI_04_nearest_alternative_action_is_correct():
    result = WhatIfInspector(centroids(), categories=("credential_access", "malware_execution"), actions=ACTIONS, factor_names=FACTOR_NAMES).inspect([0.8] * 5 + [0.2], "credential_access", "escalate")
    assert result.nearest_alternative["action"] == "investigate"


def test_WI_05_explanation_is_human_readable():
    result = WhatIfInspector(centroids(), categories=("credential_access", "malware_execution"), actions=ACTIONS, factor_names=FACTOR_NAMES).inspect([0.8] * 5 + [0.2], "credential_access", "escalate")
    assert isinstance(result.explanation, str) and result.explanation


def test_WI_06_json_safe_output():
    result = WhatIfInspector(centroids(), categories=("credential_access", "malware_execution"), actions=ACTIONS, factor_names=FACTOR_NAMES).inspect([0.8] * 5 + [0.2], "credential_access", "escalate")
    json.dumps(result.to_dict())


def test_WI_07_boundary_vector_has_no_meaningful_delta():
    # Midpoint between escalate and investigate on every dimension.
    vector = ((centroids()[0, 0] + centroids()[0, 1]) / 2.0).tolist()
    result = WhatIfInspector(centroids(), categories=("credential_access", "malware_execution"), actions=ACTIONS, factor_names=FACTOR_NAMES).inspect(vector, "credential_access", "escalate")
    assert all(item.direction == "none" for item in result.per_factor)


def test_WI_08_uses_canonical_SOC_factor_names():
    result = WhatIfInspector(centroids(), categories=("credential_access", "malware_execution"), actions=ACTIONS, factor_names=FACTOR_NAMES).inspect([0.8] * 5 + [0.2], "credential_access", "escalate")
    assert [item.factor_name for item in result.per_factor] == list(FACTOR_NAMES)


def test_RT_01_no_precedent_route_is_registered():
    paths = {route.path for route in app.routes}
    assert "/api/soc/explain/no-precedent" in paths


def test_RT_02_what_if_route_is_registered():
    paths = {route.path for route in app.routes}
    assert "/api/soc/explain/what-if" in paths


def test_RT_03_unknown_alert_returns_404():
    response = TestClient(app).get("/api/soc/explain/no-precedent?alert_id=missing-soc-alert")
    assert response.status_code == 404


def test_INT_01_score_then_novelty_then_counterfactual():
    vector = [0.8] * 5 + [0.2]
    novelty = detector(thresholds={"credential_access": 0.25}).detect(vector, "credential_access")
    counterfactual = WhatIfInspector(centroids(), categories=("credential_access", "malware_execution"), actions=ACTIONS, factor_names=FACTOR_NAMES).inspect(vector, "credential_access", novelty.nearest_action)
    assert novelty.nearest_action == "escalate"
    assert counterfactual.current_action == "escalate"


def test_INT_02_explainability_does_not_mutate_centroids():
    original = centroids()
    instance = detector()
    instance.detect([0.1] * 6, "credential_access")
    WhatIfInspector(original, categories=("credential_access", "malware_execution"), actions=ACTIONS, factor_names=FACTOR_NAMES).inspect([0.1] * 6, "credential_access", "suppress")
    np.testing.assert_array_equal(instance.centroids, original)
