from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app


def _neo4j_noop():
    mock = MagicMock()
    mock.run_query = AsyncMock(return_value=[])
    return mock


class _ContinuousScorer:
    def get_phase(self, category_index):
        return "MEAN_CONVERGENCE"

    def get_alpha(self, category_index):
        return 0.0

    def get_dk_weights(self, category_index):
        return None


def _client():
    return TestClient(app, raise_server_exceptions=False)


def _patch_channel_state(decision_count=1000, verified_decisions=1500, scorer=None):
    return (
        patch("app.services.gae_state.get_profile_scorer", return_value=scorer or _ContinuousScorer()),
        patch(
            "app.services.gae_state.get_learning_state",
            return_value=SimpleNamespace(decision_count=decision_count),
        ),
        patch(
            "app.state.graph_snapshot.get_snapshot",
            return_value=SimpleNamespace(verified_decisions=verified_decisions),
        ),
    )


def test_triage_learning_state_returns_200():
    with patch("app.services.gae_state.get_profile_scorer", return_value=_ContinuousScorer()):
        response = _client().get("/api/triage/learning-state")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["strategy"] in ("continuous", "two_phase")
    assert body["phase"] in ("MEAN_CONVERGENCE", "VARIANCE_LEARNING")
    assert isinstance(body["alpha"], (int, float))
    assert body["alpha"] >= 0


def test_triage_learning_state_category_param():
    with patch("app.services.gae_state.get_profile_scorer", return_value=_ContinuousScorer()):
        response = _client().get("/api/triage/learning-state?category=lateral_movement")

    assert response.status_code == 200, response.text
    assert response.json()["category"] == "lateral_movement"


def test_triage_learning_state_unknown_category_defaults():
    with patch("app.services.gae_state.get_profile_scorer", return_value=_ContinuousScorer()):
        response = _client().get("/api/triage/learning-state?category=nonexistent_xyz")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["category"] == "nonexistent_xyz"
    assert body["strategy"] == "continuous"
    assert body["phase"] == "MEAN_CONVERGENCE"
    assert body["alpha"] == 0.0


def test_triage_learning_state_default_continuous():
    with patch("app.services.gae_state.get_profile_scorer", return_value=_ContinuousScorer()):
        response = _client().get("/api/triage/learning-state")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["strategy"] == "continuous"
    assert body["alpha"] == 0.0
    assert body["dk_weights"] is None


def test_triage_learning_state_no_scorer():
    with patch("app.services.gae_state.get_profile_scorer", return_value=None):
        response = _client().get("/api/triage/learning-state")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["strategy"] == "continuous"
    assert body["phase"] == "MEAN_CONVERGENCE"
    assert body["decisions_in_category"] == 0


def test_channel_decomposition_returns_200():
    contexts = _patch_channel_state()
    with contexts[0], contexts[1], contexts[2]:
        response = _client().get("/api/compounding/channel-decomposition")

    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["channels"]) == 3
    assert body["irreducible_pp"] == 10.0
    assert body["disclaimer"]


def test_channel_decomposition_channel_ids():
    contexts = _patch_channel_state()
    with contexts[0], contexts[1], contexts[2]:
        response = _client().get("/api/compounding/channel-decomposition")

    assert response.status_code == 200, response.text
    assert [channel["id"] for channel in response.json()["channels"]] == [
        "scorer",
        "graph",
        "labels",
    ]


def test_channel_decomposition_labels_not_active():
    contexts = _patch_channel_state()
    with contexts[0], contexts[1], contexts[2]:
        response = _client().get("/api/compounding/channel-decomposition")

    assert response.status_code == 200, response.text
    labels = response.json()["channels"][2]
    assert labels["status"] == "not_active"
    assert labels["contribution_pp"] == 0.0


def test_channel_decomposition_has_three_channels():
    contexts = _patch_channel_state()
    with contexts[0], contexts[1], contexts[2]:
        response = _client().get("/api/compounding/channel-decomposition")

    assert response.status_code == 200, response.text
    channels = response.json()["channels"]
    assert len(channels) == 3
    for channel in channels:
        assert {"id", "label", "contribution_pp", "status", "description"} <= set(channel)


def test_channel_decomposition_remaining_boundary_math():
    contexts = _patch_channel_state()
    with contexts[0], contexts[1], contexts[2]:
        response = _client().get("/api/compounding/channel-decomposition")

    assert response.status_code == 200, response.text
    body = response.json()
    expected = round(max(body["irreducible_pp"] - body["total_improvement_pp"], 0), 1)
    assert body["remaining_boundary_pp"] == expected
    assert body["total_improvement_pp"] + body["remaining_boundary_pp"] <= body["irreducible_pp"]


def test_channel_decomposition_no_inverse_variance_wording():
    contexts = _patch_channel_state()
    with contexts[0], contexts[1], contexts[2]:
        response = _client().get("/api/compounding/channel-decomposition")

    assert response.status_code == 200, response.text
    assert "inverse variance" not in response.text.lower()
