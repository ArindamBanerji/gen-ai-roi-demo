import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import model_swap
from app.services.gae_state import get_profile_scorer, init_learning_state


def _ensure_scorer_ready():
    if get_profile_scorer() is None:
        init_learning_state()


def _trial_signature(result):
    return [
        (
            row["alert_id"],
            row["category"],
            row["action_name"],
            round(float(row["confidence"]), 10),
            list(row["probabilities"]),
        )
        for row in result.alerts
    ]


@pytest.mark.asyncio
async def test_model_swap_trial_has_required_fields_and_zero_llm_calls(monkeypatch):
    _ensure_scorer_ready()
    monkeypatch.setenv("NARRATIVE_PROVIDER", "template")

    result = await model_swap.run_model_swap_trial(n_alerts=4)

    assert result.ok is True
    assert result.status == "ok"
    assert result.llm_calls_made == 0
    assert result.llm_dependency is False
    assert result.narrative_affects_scoring is False
    assert result.narrative_llm_used == "template"
    assert result.scoring_method == "deterministic centroid tensor + softmax scoring"
    assert "Zero LLM calls" in result.summary
    assert "deterministic centroid tensor + softmax scoring" in result.summary
    assert "narrative affects scoring: False" in result.summary
    assert result.n_alerts_requested == 4
    assert result.n_alerts_processed == 4
    assert len(result.alerts) == 4
    assert result.reproducibility_check["passed"] is True
    assert len(result.reproducibility_check["first_run"]["probabilities"]) > 0
    for row in result.alerts:
        assert {"alert_id", "category", "category_index", "action_name", "confidence", "probabilities", "factor_vector"} <= set(row)
        assert isinstance(row["probabilities"], list)
        assert isinstance(row["factor_vector"], list)


@pytest.mark.asyncio
async def test_model_swap_trial_is_deterministic(monkeypatch):
    _ensure_scorer_ready()
    monkeypatch.setenv("NARRATIVE_PROVIDER", "template")

    result_a = await model_swap.run_model_swap_trial(n_alerts=5)
    result_b = await model_swap.run_model_swap_trial(n_alerts=5)

    assert result_a.status == "ok"
    assert result_b.status == "ok"
    assert _trial_signature(result_a) == _trial_signature(result_b)
    assert result_a.reproducibility_check["passed"] is True
    assert result_b.reproducibility_check["passed"] is True


@pytest.mark.asyncio
async def test_narrative_does_not_affect_scoring(monkeypatch):
    _ensure_scorer_ready()

    monkeypatch.setenv("NARRATIVE_PROVIDER", "template")
    template_result = await model_swap.run_model_swap_trial(n_alerts=3)

    monkeypatch.setenv("NARRATIVE_PROVIDER", "ollama")
    ollama_result = await model_swap.run_model_swap_trial(n_alerts=3)

    assert template_result.narrative_affects_scoring is False
    assert ollama_result.narrative_affects_scoring is False
    assert template_result.llm_calls_made == 0
    assert ollama_result.llm_calls_made == 0
    assert template_result.llm_dependency is False
    assert ollama_result.llm_dependency is False
    assert _trial_signature(template_result) == _trial_signature(ollama_result)
    assert template_result.alerts == ollama_result.alerts
    assert template_result.summary == ollama_result.summary
    assert template_result.narrative_llm_used == "template"
    assert ollama_result.narrative_llm_used == "ollama"


@pytest.mark.asyncio
async def test_model_swap_trial_cold_start(monkeypatch):
    monkeypatch.setattr(model_swap, "get_profile_scorer", lambda: None)

    result = await model_swap.run_model_swap_trial(n_alerts=2)

    assert result.ok is False
    assert result.status == "error"
    assert result.n_alerts_processed == 0
    assert result.llm_calls_made == 0
    assert result.llm_dependency is False
    assert result.narrative_affects_scoring is False
    assert result.alerts == []
    assert "Scorer not ready" in result.summary


def test_model_swap_endpoint_returns_200(monkeypatch):
    _ensure_scorer_ready()
    monkeypatch.setenv("NARRATIVE_PROVIDER", "template")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/api/soc/model-swap-trial", params={"n_alerts": 3})

    assert response.status_code == 200
    payload = response.json()
    assert payload["llm_calls_made"] == 0
    assert payload["llm_dependency"] is False
    assert payload["narrative_affects_scoring"] is False
    assert "Zero LLM calls" in payload["summary"]
    assert payload["reproducibility_check"]["passed"] is True
