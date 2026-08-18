from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import numpy as np
import pytest
from fastapi import HTTPException

from app.domains.soc import config as soc_config
from app.models.schemas import OutcomeRequest, ProcessAlertRequest
from app.routers import triage
from app.services import rl_engine


class FakeAGE:
    def __init__(
        self,
        record=None,
        fail_triggered_evolution=False,
        sequence_count=0,
        cross_category_count=0,
    ):
        self.record = record or _decision_record()
        self.queries = []
        self.fail_triggered_evolution = fail_triggered_evolution
        self.sequence_count = sequence_count
        self.cross_category_count = cross_category_count
        self.alert = {
            "alert_id": "ALERT-RL",
            "id": "ALERT-RL",
            "alert_type": "credential_access",
            "severity": "medium",
            "source_location": "10.0.0.5",
            "asset_age_days": 100,
        }
        self.context = {
            "alert_type": "credential_access",
            "user_id": "user-1",
            "nodes_consulted": 4,
        }

    async def run_query(self, query, params=None):
        self.queries.append(query)
        if self.fail_triggered_evolution and "TRIGGERED_EVOLUTION" in query:
            raise RuntimeError("evolution write failed")
        if "RETURN d.factor_vector AS factor_vector" in query:
            return [dict(self.record)]
        if "RETURN count(alert) as reset_count" in query:
            return [{"reset_count": 1}]
        return []

    async def get_alert(self, _alert_id):
        return dict(self.alert)

    async def get_security_context(self, _alert_id):
        return dict(self.context)

    async def get_sequence_count(self, _source_id):
        return self.sequence_count

    async def get_cross_category_count(self, _user_id):
        return self.cross_category_count


def _decision_record(**overrides):
    record = {
        "factor_vector": "[0.2, 0.3, 0.4, 0.1, 0.5, 0.6]",
        "action": "escalate",
        "confidence": 0.8,
        "campaign_id": "C-1",
        "explored": False,
        "explored_but_referred": False,
        "exploration_executed": False,
        "explored_action": None,
        "category": "credential_access",
        "alert_type": "credential_access",
    }
    record.update(overrides)
    return record


class FakeLearningState:
    def __init__(self):
        self.decision_count = 42
        self.history = []

    def update(self, **_kwargs):
        self.decision_count += 1
        return SimpleNamespace(centroid_update=None)


def _patch_common_outcome(monkeypatch, harness, record=None, *, fail_triggered_evolution=False):
    rl_engine.reset_rl_state()
    decision = record or _decision_record()
    harness.graph_client.fail_triggered_evolution = fail_triggered_evolution
    monkeypatch.setattr(triage, "graph_client", harness.graph_client)
    harness.add_decision(
        decision_id="D-RL",
        category=decision["category"],
        action=decision["action"],
        confidence=decision["confidence"],
        factors={f"f{i}": value for i, value in enumerate([0.2, 0.3, 0.4, 0.1, 0.5, 0.6])},
        factor_vector=decision["factor_vector"],
        campaign_id=decision.get("campaign_id"),
        exploration_flags={
            "explored": decision.get("explored", False),
            "explored_but_referred": decision.get("explored_but_referred", False),
            "exploration_executed": decision.get("exploration_executed", False),
            "explored_action": decision.get("explored_action"),
        },
        alert_type=decision.get("alert_type", decision["category"]),
    )
    learning_state = FakeLearningState()
    monkeypatch.setattr(triage, "get_feedback_status", lambda _alert_id: {"has_feedback": False})
    monkeypatch.setattr(triage, "get_learning_state", lambda: learning_state)
    monkeypatch.setattr(triage, "save_learning_state", lambda: None)
    monkeypatch.setattr(triage.event_bus, "emit", AsyncMock())
    monkeypatch.setattr(
        triage,
        "process_outcome",
        lambda **_kwargs: SimpleNamespace(
            model_dump=lambda: {"graph_updates": [], "consequence": "ok"},
            graph_updates=[],
            consequence="ok",
        ),
    )
    monkeypatch.setattr("app.framework.audit.record_outcome", AsyncMock(return_value=None))
    monkeypatch.setattr("app.services.shadow_runner.fill_shadow_outcome", lambda *_args: None)
    return harness.graph_client, learning_state


async def _call_outcome(outcome="correct", analyst_action=None):
    return await triage.report_decision_outcome(
        OutcomeRequest(
            alert_id="ALERT-RL",
            decision_id="D-RL",
            outcome=outcome,
            analyst_action=analyst_action,
        )
    )


def _outcome_decision_update_query(fake_graph):
    return next(
        query
        for query in fake_graph.queries
        if "d.analyst_action" in query and "d.was_override" in query
    )


@pytest.mark.asyncio
async def test_reward_computation_fires_on_outcome_when_flag_enabled(monkeypatch, soc_triage_harness):
    _patch_common_outcome(monkeypatch, soc_triage_harness)
    monkeypatch.setattr(soc_config, "RL_REWARD_LEDGER_ENABLED", True)

    await _call_outcome()

    entries = rl_engine.get_reward_ledger().get_entries()
    assert len(entries) == 1
    assert entries[0]["decision_id"] == "D-RL"
    assert entries[0]["graded_reward"] > 0


@pytest.mark.asyncio
async def test_outcome_persists_analyst_action_override_measurement_fields(monkeypatch, soc_triage_harness):
    _client, _learning_state = _patch_common_outcome(monkeypatch, soc_triage_harness)

    await _call_outcome(outcome="incorrect", analyst_action="suppress")

    decision = soc_triage_harness.get_decision("D-RL")
    assert decision is not None
    assert decision["outcome"] == "incorrect"
    assert decision["correct"] is False
    assert decision["analyst_action"] == "suppress"
    assert decision["final_action"] == "suppress"
    assert decision["recommended_action"] == "escalate"
    assert decision["was_override"] is True
    assert decision["quality_signal"] == 0.0


@pytest.mark.asyncio
async def test_outcome_persists_non_override_measurement_fields(monkeypatch, soc_triage_harness):
    _client, _learning_state = _patch_common_outcome(monkeypatch, soc_triage_harness)

    await _call_outcome(outcome="correct", analyst_action="escalate")

    decision = soc_triage_harness.get_decision("D-RL")
    assert decision is not None
    assert decision["analyst_action"] == "escalate"
    assert decision["final_action"] == "escalate"
    assert decision["was_override"] is False
    assert decision["quality_signal"] == 1.0


@pytest.mark.asyncio
async def test_outcome_without_analyst_action_does_not_fabricate_action(monkeypatch, soc_triage_harness):
    _client, _learning_state = _patch_common_outcome(monkeypatch, soc_triage_harness)

    await _call_outcome(outcome="correct", analyst_action=None)

    decision = soc_triage_harness.get_decision("D-RL")
    assert decision is not None
    assert decision["outcome"] == "correct"
    assert decision["correct"] is True
    assert decision.get("analyst_action") is None
    assert decision.get("final_action") is None
    assert decision["was_override"] is False
    assert decision["quality_signal"] == 1.0


@pytest.mark.asyncio
async def test_campaign_measurement_fields_share_decision_node_with_cohort_flags(monkeypatch, soc_triage_harness):
    client, _learning_state = _patch_common_outcome(
        monkeypatch,
        soc_triage_harness,
        _decision_record(campaign_id="L1-campaign"),
    )

    await _call_outcome(outcome="correct", analyst_action="escalate")

    decision = soc_triage_harness.get_decision("D-RL")
    assert decision is not None
    assert decision["metadata"]["campaign_id"] == "L1-campaign"
    assert decision["analyst_action"] == "escalate"
    assert decision["was_override"] is False
    assert decision["quality_signal"] == 1.0
    assert any("RETURN d.factor_vector AS factor_vector" in q for q, _ in client._queries)


@pytest.mark.asyncio
async def test_reward_skipped_when_flag_false(monkeypatch, soc_triage_harness):
    _patch_common_outcome(monkeypatch, soc_triage_harness)
    monkeypatch.setattr(soc_config, "RL_REWARD_LEDGER_ENABLED", False)

    await _call_outcome()

    assert rl_engine.get_reward_ledger().get_entries() == []


@pytest.mark.asyncio
async def test_posterior_update_fires_when_explored_and_not_vetoed(monkeypatch, soc_triage_harness):
    _patch_common_outcome(
        monkeypatch,
        soc_triage_harness,
        _decision_record(
            explored=True,
            explored_but_referred=False,
            exploration_executed=True,
            explored_action="investigate",
        ),
    )
    monkeypatch.setattr(soc_config, "RL_EXPLORATION_ENABLED", True)
    policy = rl_engine.ExplorationPolicy(6, 4)
    monkeypatch.setattr(rl_engine, "get_exploration_policy", lambda: policy)

    await _call_outcome()

    assert policy.alphas[0][1] == 2.0


@pytest.mark.asyncio
async def test_posterior_update_skipped_when_referral_vetoed(monkeypatch, soc_triage_harness):
    _patch_common_outcome(
        monkeypatch,
        soc_triage_harness,
        _decision_record(
            explored=True,
            explored_but_referred=True,
            exploration_executed=False,
            explored_action="investigate",
        ),
    )
    monkeypatch.setattr(soc_config, "RL_EXPLORATION_ENABLED", True)
    policy = rl_engine.ExplorationPolicy(6, 4)
    monkeypatch.setattr(rl_engine, "get_exploration_policy", lambda: policy)

    await _call_outcome()

    assert policy.alphas[0][1] == 1.0


@pytest.mark.asyncio
async def test_chain_credit_fires_on_correct_outcome_when_enabled(monkeypatch, soc_triage_harness):
    _patch_common_outcome(monkeypatch, soc_triage_harness)
    monkeypatch.setattr(soc_config, "RL_CHAIN_CREDIT_ENABLED", True)
    calls = []

    class Assigner:
        async def assign_chain_credit(self, **kwargs):
            calls.append(kwargs)
            return []

    monkeypatch.setattr(rl_engine, "get_credit_assigner", lambda: Assigner())

    await _call_outcome()

    assert calls
    assert calls[0]["source_decision_id"] == "D-RL"


@pytest.mark.asyncio
async def test_chain_credit_skipped_when_triggered_evolution_write_fails(monkeypatch, soc_triage_harness):
    _client, _learning_state = _patch_common_outcome(
        monkeypatch,
        soc_triage_harness,
        fail_triggered_evolution=True,
    )
    monkeypatch.setattr(soc_config, "RL_CHAIN_CREDIT_ENABLED", True)
    calls = []

    class Assigner:
        async def assign_chain_credit(self, **kwargs):
            calls.append(kwargs)
            return []

    monkeypatch.setattr(rl_engine, "get_credit_assigner", lambda: Assigner())

    result = await _call_outcome()

    assert result["consequence"] == "ok"
    assert calls == []


@pytest.mark.asyncio
async def test_chain_credit_skipped_when_flag_false(monkeypatch, soc_triage_harness):
    _patch_common_outcome(monkeypatch, soc_triage_harness)
    monkeypatch.setattr(soc_config, "RL_CHAIN_CREDIT_ENABLED", False)
    calls = []
    monkeypatch.setattr(
        rl_engine,
        "get_credit_assigner",
        lambda: SimpleNamespace(assign_chain_credit=lambda **kwargs: calls.append(kwargs)),
    )

    await _call_outcome()

    assert calls == []


@pytest.mark.asyncio
async def test_reward_failure_does_not_crash_outcome(monkeypatch, soc_triage_harness):
    _patch_common_outcome(monkeypatch, soc_triage_harness)
    monkeypatch.setattr(soc_config, "RL_REWARD_LEDGER_ENABLED", True)

    class BadComputer:
        def compute(self, **_kwargs):
            raise RuntimeError("reward failed")

    monkeypatch.setattr(rl_engine, "get_reward_computer", lambda: BadComputer())

    result = await _call_outcome()

    assert result["consequence"] == "ok"


@pytest.mark.asyncio
async def test_eta_restored_when_guarded_update_raises(monkeypatch, soc_triage_harness):
    _patch_common_outcome(monkeypatch, soc_triage_harness)
    monkeypatch.setattr(triage, "LEARNING_ENABLED", True)
    monkeypatch.setattr(soc_config, "RL_REWARD_LEDGER_ENABLED", True)
    monkeypatch.setattr(soc_config, "RL_ETA_MODULATION_ENABLED", True)
    monkeypatch.setattr(
        "app.services.learning_health.LearningHealthMonitor.evaluate",
        AsyncMock(return_value={"status": "GREEN", "conservation": {"headroom": 10.0}}),
    )
    scorer = SimpleNamespace(
        eta=0.05,
        eta_neg=0.05,
        eta_override=0.01,
        set_conservation_status=lambda _status: None,
    )
    monkeypatch.setattr("app.services.gae_state.get_profile_scorer", lambda: scorer)

    @asynccontextmanager
    async def fake_acquire():
        yield scorer

    def raising_guarded_update(*_args, **_kwargs):
        raise RuntimeError("update failed")

    monkeypatch.setattr("app.services.gae_state.acquire_scorer", fake_acquire)
    monkeypatch.setattr("app.services.gae_state.guarded_update", raising_guarded_update)

    with pytest.raises(HTTPException):
        await _call_outcome()

    assert scorer.eta == 0.05
    assert scorer.eta_neg == 0.05
    assert scorer.eta_override == 0.01


def _patch_common_analyze(
    monkeypatch,
    referral_should_refer=False,
    incident_id=None,
    sequence_count=0,
    cross_category_count=0,
    referral_evaluator=None,
):
    fake_graph = FakeAGE(
        sequence_count=sequence_count,
        cross_category_count=cross_category_count,
    )
    if incident_id:
        fake_graph.alert["incident_id"] = incident_id
    monkeypatch.setattr(triage, "graph_client", fake_graph)
    monkeypatch.setattr(
        triage,
        "compute_factor_vector",
        AsyncMock(return_value=np.array([0.2, 0.3, 0.4, 0.1, 0.5, 0.6])),
    )
    monkeypatch.setattr(triage.narrator, "generate_reasoning", AsyncMock(return_value="why"))
    monkeypatch.setattr(
        triage,
        "record_decision",
        AsyncMock(return_value={"hash": "h", "chain_index": 1}),
    )
    monkeypatch.setattr(triage.event_bus, "emit", AsyncMock())
    monkeypatch.setattr(triage, "get_graph_data", AsyncMock(return_value={"nodes": [], "edges": []}))
    monkeypatch.setattr(
        "app.services.learning_health.LearningHealthMonitor.evaluate",
        AsyncMock(return_value={"conservation": {"headroom": 10.0}}),
    )
    monkeypatch.setattr(
        "app.services.composite_gate.CompositeDiscriminant.evaluate",
        AsyncMock(return_value={"auto_approve": False, "approval_score": 0.0, "reason_codes": []}),
    )

    scoring = SimpleNamespace(
        action_name="escalate",
        confidence=0.9,
        entropy=0.1,
        confidence_gap=0.6,
        probabilities=np.array([0.9, 0.05, 0.03, 0.02]),
    )
    scorer = SimpleNamespace(score=lambda *_args, **_kwargs: scoring, tau=0.1)
    monkeypatch.setattr("app.services.gae_state.get_profile_scorer", lambda: scorer)
    monkeypatch.setattr("app.services.gae_state.init_learning_state", lambda: None)
    monkeypatch.setattr(triage, "get_learning_state", lambda: SimpleNamespace(decision_count=1))

    class Referral:
        should_refer = referral_should_refer
        reason_codes = ["R"] if referral_should_refer else []
        audit_summary = "audit"

    class ReferralEngine:
        def __init__(self, rules):
            self.rules = rules

        def evaluate(self, context):
            if referral_evaluator:
                return referral_evaluator(context)
            return Referral()

    monkeypatch.setattr("gae.referral.ReferralEngine", ReferralEngine)
    monkeypatch.setattr("app.services.referral_rules.get_soc_referral_rules", lambda: [])
    return fake_graph


def _patch_campaign_check(monkeypatch, *, campaign_id=None, context=None, suppressed=False):
    class FakeCampaignEngine:
        def __init__(self, _config):
            self.config = _config

    class FakeCampaignRepository:
        def __init__(self, _client):
            self.client = _client

    class FakeCampaignMatcher:
        def __init__(self, *_args, **_kwargs):
            self.async_state = SimpleNamespace(
                get_campaign_context=lambda cid: context if cid == campaign_id else None,
                get_temporal_context=lambda cid: getattr(context, "temporal_context", None)
                if cid == campaign_id
                else None,
            )

        async def check_alert(self, _alert_id):
            return campaign_id

    monkeypatch.setattr(
        "app.domains.soc.campaigns.CampaignCorrelationEngine",
        FakeCampaignEngine,
    )
    monkeypatch.setattr(
        "app.domains.soc.campaigns.CampaignRepository",
        FakeCampaignRepository,
    )
    monkeypatch.setattr(
        "app.domains.soc.campaigns.CampaignMatcher",
        FakeCampaignMatcher,
    )
    monkeypatch.setattr(
        "app.services.soc_situation_pattern.banner_suppressed",
        lambda alert_id, holdout_pct=15: suppressed,
    )


def _decision_creation_query(fake_graph):
    return next(
        query
        for query in fake_graph.queries
        if "CREATE (d:Decision" in query
    )


def _campaign_flag_query(fake_graph):
    return next(
        query
        for query in fake_graph.queries
        if "d.is_campaign_alert" in query
        and "d.campaign_context_shown" in query
    )


@pytest.mark.asyncio
async def test_campaign_context_treatment_response_and_decision_flags(monkeypatch):
    fake_graph = _patch_common_analyze(monkeypatch)
    _patch_campaign_check(
        monkeypatch,
        campaign_id="campaign-1",
        context=SimpleNamespace(
            campaign_id="campaign-1",
            category="credential_access",
            first_seen="2026-06-18T10:00:00",
            member_count=3,
        ),
        suppressed=False,
    )

    response = await triage.analyze_alert(ProcessAlertRequest(alert_id="ALERT-RL"))

    payload = response["campaign_context"]
    assert payload["campaign_id"] == "campaign-1"
    assert payload["source"] == "graph_store_cached"
    assert payload["category"] == "credential_access"
    assert payload["member_count"] == 3
    assert "Consider escalating the campaign" in payload["advisory"]
    flag_query = _campaign_flag_query(fake_graph)
    assert "d.campaign_id = 'campaign-1'" in flag_query
    assert "d.is_campaign_alert = true" in flag_query
    assert "d.campaign_context_shown = true" in flag_query
    assert "d.campaign_advisory_version = 'phase4_temporal_v1'" in flag_query


@pytest.mark.asyncio
async def test_campaign_context_suppressed_response_and_decision_flags(monkeypatch):
    fake_graph = _patch_common_analyze(monkeypatch)
    _patch_campaign_check(
        monkeypatch,
        campaign_id="campaign-1",
        context=SimpleNamespace(
            campaign_id="campaign-1",
            category="credential_access",
            first_seen="2026-06-18T10:00:00",
            member_count=3,
        ),
        suppressed=True,
    )

    response = await triage.analyze_alert(ProcessAlertRequest(alert_id="ALERT-RL"))

    assert response["campaign_context"] is None
    flag_query = _campaign_flag_query(fake_graph)
    assert "d.campaign_id = 'campaign-1'" in flag_query
    assert "d.is_campaign_alert = true" in flag_query
    assert "d.campaign_context_shown = false" in flag_query
    assert "d.campaign_advisory_version = 'phase4_temporal_v1'" in flag_query


@pytest.mark.asyncio
async def test_campaign_context_isolated_response_and_decision_flags(monkeypatch):
    fake_graph = _patch_common_analyze(monkeypatch)
    _patch_campaign_check(monkeypatch, campaign_id=None)

    response = await triage.analyze_alert(ProcessAlertRequest(alert_id="ALERT-RL"))

    assert response["campaign_context"] is None
    flag_query = _campaign_flag_query(fake_graph)
    assert "d.campaign_id =" not in flag_query
    assert "d.is_campaign_alert = false" in flag_query
    assert "d.campaign_context_shown = false" in flag_query


@pytest.mark.asyncio
async def test_campaign_context_cold_cache_response(monkeypatch):
    fake_graph = _patch_common_analyze(monkeypatch)
    _patch_campaign_check(monkeypatch, campaign_id="campaign-cold", context=None)

    response = await triage.analyze_alert(ProcessAlertRequest(alert_id="ALERT-RL"))

    payload = response["campaign_context"]
    assert payload["campaign_id"] == "campaign-cold"
    assert payload["source"] == "graph_store_cached"
    assert payload["status"] == "cold_cache"
    assert "Emerging campaign pattern" in payload["advisory"]
    flag_query = _campaign_flag_query(fake_graph)
    assert "d.is_campaign_alert = true" in flag_query
    assert "d.campaign_context_shown = true" in flag_query
    assert "d.campaign_advisory_version = 'phase4_temporal_v1'" in flag_query


@pytest.mark.asyncio
async def test_exploration_proposal_in_analyze_when_enabled(monkeypatch):
    fake_graph = _patch_common_analyze(monkeypatch)
    monkeypatch.setattr(soc_config, "RL_EXPLORATION_ENABLED", True)
    monkeypatch.setattr(triage, "LEARNING_ENABLED", True)
    policy = rl_engine.ExplorationPolicy(6, 4, epsilon_base=1.0, target_headroom=2.0)
    policy.alphas[0] = [1.0, 5.0, 1.0, 1.0]
    monkeypatch.setattr(rl_engine, "get_exploration_policy", lambda: policy)
    monkeypatch.setattr(rl_engine.random, "betavariate", lambda alpha, beta: alpha)

    response = await triage.analyze_alert(ProcessAlertRequest(alert_id="ALERT-RL"))

    # Exploration is a proposal only; the live centroid action remains
    # authoritative for the decision path.
    assert response["recommendation"]["action"] == "refer_to_analyst"
    assert any("d.explored                = true" in query for query in fake_graph.queries)


@pytest.mark.asyncio
async def test_no_exploration_when_flag_false(monkeypatch):
    fake_graph = _patch_common_analyze(monkeypatch)
    monkeypatch.setattr(soc_config, "RL_EXPLORATION_ENABLED", False)

    response = await triage.analyze_alert(ProcessAlertRequest(alert_id="ALERT-RL"))

    assert response["recommendation"]["action"] == "refer_to_analyst"
    assert not any("d.explored                = true" in query for query in fake_graph.queries)


@pytest.mark.asyncio
async def test_no_exploration_when_headroom_tight(monkeypatch):
    fake_graph = _patch_common_analyze(monkeypatch)
    monkeypatch.setattr(soc_config, "RL_EXPLORATION_ENABLED", True)
    monkeypatch.setattr(
        "app.services.learning_health.LearningHealthMonitor.evaluate",
        AsyncMock(return_value={"conservation": {"headroom": 1.0}}),
    )

    response = await triage.analyze_alert(ProcessAlertRequest(alert_id="ALERT-RL"))

    assert response["recommendation"]["action"] == "refer_to_analyst"
    assert not any("d.explored                = true" in query for query in fake_graph.queries)


@pytest.mark.asyncio
async def test_rapid_succession_referral_count_includes_current_decision(monkeypatch):
    # RapidSuccessionRule default threshold is 3 in referral_rules.py.
    def referral_evaluator(context):
        should_refer = context["sequence_count"] >= 3
        return SimpleNamespace(
            should_refer=should_refer,
            reason_codes=["R2"] if should_refer else [],
            audit_summary="rapid succession",
        )

    fake_graph = _patch_common_analyze(
        monkeypatch,
        sequence_count=2,
        referral_evaluator=referral_evaluator,
    )

    response = await triage.analyze_alert(ProcessAlertRequest(alert_id="ALERT-RL"))

    assert response["recommendation"]["action"] == "refer_to_analyst"
    assert triage.record_decision.await_args.kwargs["action_taken"] == "refer_to_analyst"
    decision_events = [
        call.args[0]
        for call in triage.event_bus.emit.await_args_list
        if call.args and call.args[0].__class__.__name__ == "DecisionMade"
    ]
    assert decision_events[0].action == "refer_to_analyst"
    assert "action:                'refer_to_analyst'" in _decision_creation_query(fake_graph)


@pytest.mark.asyncio
async def test_rapid_succession_referral_count_below_threshold_after_current(monkeypatch):
    def referral_evaluator(context):
        should_refer = context["sequence_count"] >= 3
        return SimpleNamespace(
            should_refer=should_refer,
            reason_codes=["R2"] if should_refer else [],
            audit_summary="rapid succession",
        )

    fake_graph = _patch_common_analyze(
        monkeypatch,
        sequence_count=1,
        referral_evaluator=referral_evaluator,
    )

    response = await triage.analyze_alert(ProcessAlertRequest(alert_id="ALERT-RL"))

    assert response["recommendation"]["action"] == "refer_to_analyst"
    assert "action:                'refer_to_analyst'" in _decision_creation_query(fake_graph)


@pytest.mark.asyncio
async def test_cross_category_referral_count_includes_current_decision(monkeypatch):
    # CrossCategoryRule default threshold is 2 in referral_rules.py.
    def referral_evaluator(context):
        should_refer = context["cross_category_count"] >= 2
        return SimpleNamespace(
            should_refer=should_refer,
            reason_codes=["R7"] if should_refer else [],
            audit_summary="cross category",
        )

    fake_graph = _patch_common_analyze(
        monkeypatch,
        cross_category_count=1,
        referral_evaluator=referral_evaluator,
    )

    response = await triage.analyze_alert(ProcessAlertRequest(alert_id="ALERT-RL"))

    assert response["recommendation"]["action"] == "refer_to_analyst"
    assert triage.record_decision.await_args.kwargs["action_taken"] == "refer_to_analyst"
    assert "action:                'refer_to_analyst'" in _decision_creation_query(fake_graph)


@pytest.mark.asyncio
async def test_adjusted_count_referral_veto_blocks_explored_side_effects(monkeypatch):
    def referral_evaluator(context):
        should_refer = context["sequence_count"] >= 3
        return SimpleNamespace(
            should_refer=should_refer,
            reason_codes=["R2"] if should_refer else [],
            audit_summary="rapid succession",
        )

    fake_graph = _patch_common_analyze(
        monkeypatch,
        sequence_count=2,
        incident_id="INC-RL",
        referral_evaluator=referral_evaluator,
    )
    monkeypatch.setattr(soc_config, "RL_EXPLORATION_ENABLED", True)
    monkeypatch.setattr(triage, "LEARNING_ENABLED", True)
    policy = rl_engine.ExplorationPolicy(6, 4, epsilon_base=1.0, target_headroom=2.0)
    policy.alphas[0] = [1.0, 5.0, 1.0, 1.0]
    monkeypatch.setattr(rl_engine, "get_exploration_policy", lambda: policy)
    monkeypatch.setattr(rl_engine.random, "betavariate", lambda alpha, beta: alpha)
    sentinel_calls = []

    async def push_incident_update(**kwargs):
        sentinel_calls.append(kwargs)

    monkeypatch.setattr(
        "app.connectors.sentinel_real.get_sentinel_connector",
        lambda: SimpleNamespace(push_incident_update=push_incident_update),
    )

    response = await triage.analyze_alert(ProcessAlertRequest(alert_id="ALERT-RL"))

    assert response["recommendation"]["action"] == "refer_to_analyst"
    assert "action:                'refer_to_analyst'" in _decision_creation_query(fake_graph)
    assert triage.record_decision.await_args.kwargs["action_taken"] == "refer_to_analyst"
    decision_events = [
        call.args[0]
        for call in triage.event_bus.emit.await_args_list
        if call.args and call.args[0].__class__.__name__ == "DecisionMade"
    ]
    assert decision_events[0].action == "refer_to_analyst"
    assert sentinel_calls == []
    metadata_query = "\n".join(fake_graph.queries)
    assert "d.explored_but_referred   = true" in metadata_query
    assert "d.original_action         = 'escalate'" in metadata_query
    assert "d.explored_action         = 'investigate'" in metadata_query


@pytest.mark.asyncio
async def test_referral_veto_overrides_exploration_and_sets_veto_metadata(monkeypatch):
    fake_graph = _patch_common_analyze(
        monkeypatch,
        referral_should_refer=True,
        incident_id="INC-RL",
    )
    monkeypatch.setattr(soc_config, "RL_EXPLORATION_ENABLED", True)
    monkeypatch.setattr(triage, "LEARNING_ENABLED", True)
    policy = rl_engine.ExplorationPolicy(6, 4, epsilon_base=1.0, target_headroom=2.0)
    policy.alphas[0] = [1.0, 5.0, 1.0, 1.0]
    monkeypatch.setattr(rl_engine, "get_exploration_policy", lambda: policy)
    monkeypatch.setattr(rl_engine.random, "betavariate", lambda alpha, beta: alpha)
    sentinel_calls = []

    async def push_incident_update(**kwargs):
        sentinel_calls.append(kwargs)

    monkeypatch.setattr(
        "app.connectors.sentinel_real.get_sentinel_connector",
        lambda: SimpleNamespace(push_incident_update=push_incident_update),
    )

    response = await triage.analyze_alert(ProcessAlertRequest(alert_id="ALERT-RL"))

    assert response["recommendation"]["action"] == "refer_to_analyst"
    assert "action:                'refer_to_analyst'" in _decision_creation_query(fake_graph)
    triage.record_decision.assert_awaited()
    assert triage.record_decision.await_args.kwargs["action_taken"] == "refer_to_analyst"
    decision_events = [
        call.args[0]
        for call in triage.event_bus.emit.await_args_list
        if call.args and call.args[0].__class__.__name__ == "DecisionMade"
    ]
    assert decision_events
    assert decision_events[0].action == "refer_to_analyst"
    assert sentinel_calls == []
    metadata_query = "\n".join(fake_graph.queries)
    assert "d.explored_but_referred   = true" in metadata_query
    assert "d.exploration_executed    = false" in metadata_query
    assert "d.original_action         = 'escalate'" in metadata_query
    assert "d.explored_action         = 'investigate'" in metadata_query


@pytest.mark.asyncio
async def test_explored_action_drives_side_effects_when_not_referred(monkeypatch):
    fake_graph = _patch_common_analyze(monkeypatch)
    monkeypatch.setattr(soc_config, "RL_EXPLORATION_ENABLED", True)
    monkeypatch.setattr(triage, "LEARNING_ENABLED", True)
    policy = rl_engine.ExplorationPolicy(6, 4, epsilon_base=1.0, target_headroom=2.0)
    policy.alphas[0] = [1.0, 5.0, 1.0, 1.0]
    monkeypatch.setattr(rl_engine, "get_exploration_policy", lambda: policy)
    monkeypatch.setattr(rl_engine.random, "betavariate", lambda alpha, beta: alpha)

    response = await triage.analyze_alert(ProcessAlertRequest(alert_id="ALERT-RL"))

    # Exploration is recorded for learning/shadow evaluation but does not
    # override the centroid-selected action.
    assert response["recommendation"]["action"] == "refer_to_analyst"
    assert triage.record_decision.await_args.kwargs["action_taken"] == "refer_to_analyst"
    decision_events = [
        call.args[0]
        for call in triage.event_bus.emit.await_args_list
        if call.args and call.args[0].__class__.__name__ == "DecisionMade"
    ]
    assert decision_events
    assert decision_events[0].action == "refer_to_analyst"
    metadata_query = "\n".join(fake_graph.queries)
    assert "d.explored_but_referred   = false" in metadata_query


@pytest.mark.asyncio
async def test_exploration_failure_does_not_crash_analyze(monkeypatch):
    _patch_common_analyze(monkeypatch)
    monkeypatch.setattr(soc_config, "RL_EXPLORATION_ENABLED", True)

    class BadPolicy:
        def propose(self, *_args, **_kwargs):
            raise RuntimeError("bad policy")

    monkeypatch.setattr(rl_engine, "get_exploration_policy", lambda: BadPolicy())

    response = await triage.analyze_alert(ProcessAlertRequest(alert_id="ALERT-RL"))

    assert response["recommendation"]["action"] == "refer_to_analyst"


def test_exploration_metadata_query_uses_s_serializer_and_no_params():
    source = open(triage.__file__, encoding="utf-8").read()
    metadata_block = source.split("d.explored                = true", 1)[1].split("_referral_debug", 1)[0]
    assert "$" not in metadata_block
    assert "_S(decision_id)" in source
    assert "_S(_rl_original_action_name)" in metadata_block
    assert "_S(_rl_explored_action_name or '')" in metadata_block
