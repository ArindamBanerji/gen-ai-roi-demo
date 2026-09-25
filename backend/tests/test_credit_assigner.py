from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import numpy as np
import pytest

from app.domains.soc.config import SOCDomainConfig
from app.services import rl_engine
from app.services.rl_engine import ChainCredit, CreditAssigner, RewardLedger


def _credit_graph(age_graph, rows=()):
    for row in rows:
        identifier = age_graph.decision(correct=True, verified_correct=True, action_index=0, **row)
        literal = age_graph.client.serialize_for_age(identifier)
        age_graph.query(f"MATCH (d:Decision {{decision_id: {literal}}}) CREATE (d)-[:TRIGGERED_EVOLUTION]->(e:EvolutionEvent {{id: {literal}}}) RETURN e")
    client = age_graph.client
    client.run_query = AsyncMock(wraps=client.run_query)
    return client


class CountingScorer:
    def __init__(self):
        self.calls = 0

    def score(self, f, category_index):
        self.calls += 1
        p0 = min(max(sum(f) / len(f), 0.0), 1.0)
        return SimpleNamespace(probabilities=np.asarray([p0, 1.0 - p0]))

    def update(self, *args, **kwargs):  # pragma: no cover - must never be called
        raise AssertionError("CreditAssigner must not call update()")


@pytest.mark.asyncio
async def test_graph_client_none_returns_empty():
    result = await CreditAssigner(None).assign_chain_credit("D-2", "credential_access", 0, 100, 1.0)
    assert result == []


@pytest.mark.asyncio
@pytest.mark.age
async def test_no_historical_decisions_returns_empty(age_graph):
    graph = _credit_graph(age_graph, [])
    result = await CreditAssigner(graph).assign_chain_credit("D-2", "credential_access", 0, 100, 1.0)
    assert result == []


@pytest.mark.asyncio
@pytest.mark.age
async def test_single_historical_decision_gets_half_direct_reward(age_graph):
    graph = _credit_graph(age_graph, [{"decision_id": "D-1", "decision_number": 85}])
    result = await CreditAssigner(graph).assign_chain_credit("D-2", "credential_access", 0, 100, 1.0)
    assert len(result) == 1
    assert result[0] == ChainCredit("D-2", "D-1", 0.5, 1.0, 15)


@pytest.mark.asyncio
@pytest.mark.age
async def test_negative_reward_uses_abs_value(age_graph):
    graph = _credit_graph(age_graph, [{"decision_id": "D-1", "decision_number": 85}])
    result = await CreditAssigner(graph).assign_chain_credit("D-2", "credential_access", 0, 100, -14.0)
    assert result[0].chain_reward == pytest.approx(7.0)


@pytest.mark.asyncio
@pytest.mark.age
async def test_multiple_historical_decisions_normalize_chain_budget(age_graph):
    rows = [
        {"decision_id": "D-1", "decision_number": 95},
        {"decision_id": "D-2", "decision_number": 80},
        {"decision_id": "D-3", "decision_number": 60},
    ]
    result = await CreditAssigner(_credit_graph(age_graph, rows)).assign_chain_credit(
        "D-4", "credential_access", 0, 100, 2.0
    )
    assert len(result) == 3
    assert sum(credit.chain_reward for credit in result) <= 1.0 + 1e-12
    assert sum(credit.gamma for credit in result) == pytest.approx(1.0)


@pytest.mark.asyncio
@pytest.mark.age
async def test_zero_reward_returns_empty_without_query(age_graph):
    graph = _credit_graph(age_graph, [{"decision_id": "D-1", "decision_number": 95}])
    result = await CreditAssigner(graph).assign_chain_credit("D-2", "credential_access", 0, 100, 0.0)
    assert result == []
    graph.run_query.assert_not_called()


@pytest.mark.asyncio
async def test_query_failure_returns_empty_and_logs(caplog):
    graph = AsyncMock()
    graph.run_query.side_effect = RuntimeError("db down")
    result = await CreditAssigner(graph).assign_chain_credit("D-2", "credential_access", 0, 100, 1.0)
    assert result == []
    assert "chain-credit query failed" in caplog.text


@pytest.mark.asyncio
@pytest.mark.age
async def test_excludes_self_if_returned_by_graph(age_graph):
    rows = [
        {"decision_id": "D-2", "decision_number": 99},
        {"decision_id": "D-1", "decision_number": 95},
    ]
    result = await CreditAssigner(_credit_graph(age_graph, rows)).assign_chain_credit(
        "D-2", "credential_access", 0, 100, 1.0
    )
    assert [credit.target_decision_id for credit in result] == ["D-1"]


@pytest.mark.asyncio
@pytest.mark.age
async def test_query_safety(age_graph):
    graph = _credit_graph(age_graph, [])
    await CreditAssigner(graph).assign_chain_credit("D-'2", "credential_access", 0, 100, 1.0)
    query = graph.run_query.call_args.args[0]
    assert "$" not in query
    assert "MERGE" not in query
    assert " SET " not in f" {query} "
    assert "DELETE" not in query
    assert "MATCH (d:Decision)-[:TRIGGERED_EVOLUTION]->(e:EvolutionEvent)" in query
    assert "d.category = 'credential_access'" in query
    assert "D-\\'2" in query


def test_reward_ledger_add_chain_credit_records_separately():
    ledger = RewardLedger()
    credit = ChainCredit("D-2", "D-1", 0.5, 1.0, 15)
    ledger.add_chain_credit(credit)
    assert ledger.get_entries() == []
    assert ledger.get_chain_credits() == [{
        "source_decision_id": "D-2",
        "target_decision_id": "D-1",
        "chain_reward": 0.5,
        "gamma": 1.0,
        "age": 15,
    }]


def test_reward_ledger_reset_clears_chain_credits():
    ledger = RewardLedger()
    ledger.add_chain_credit(ChainCredit("D-2", "D-1", 0.5, 1.0, 15))
    ledger.reset()
    assert ledger.get_chain_credits() == []


def test_compute_factor_attribution_returns_factor_keys():
    attribution = CreditAssigner().compute_factor_attribution(
        CountingScorer(), [0.2, 0.3, 0.4], 0, 0, 1.0
    )
    assert set(attribution) == {0, 1, 2}


def test_compute_factor_attribution_calls_score_twice_per_factor():
    scorer = CountingScorer()
    CreditAssigner().compute_factor_attribution(scorer, [0.2] * 6, 0, 0, 1.0)
    assert scorer.calls == 12


def test_compute_factor_attribution_does_not_mutate_real_scorer():
    scorer = SOCDomainConfig().build_profile_scorer()
    before = scorer.mu.copy()
    factors = [0.4, 0.5, 0.6, 0.4, 0.3, 0.7]
    CreditAssigner().compute_factor_attribution(scorer, factors, 0, 0, 1.0)
    assert np.array_equal(scorer.mu, before)
    assert factors == [0.4, 0.5, 0.6, 0.4, 0.3, 0.7]


def test_reward_sign_flips_attribution_sign():
    scorer = CountingScorer()
    positive = CreditAssigner().compute_factor_attribution(scorer, [0.2] * 6, 0, 0, 1.0)
    negative = CreditAssigner().compute_factor_attribution(scorer, [0.2] * 6, 0, 0, -1.0)
    assert negative[0] == pytest.approx(-positive[0])


def test_get_credit_assigner_singleton_returns_credit_assigner():
    rl_engine.reset_rl_state()
    first = rl_engine.get_credit_assigner()
    second = rl_engine.get_credit_assigner()
    assert isinstance(first, CreditAssigner)
    assert first is second


def test_reset_rl_state_clears_credit_assigner_singleton():
    rl_engine.reset_rl_state()
    first = rl_engine.get_credit_assigner()
    rl_engine.reset_rl_state()
    second = rl_engine.get_credit_assigner()
    assert first is not second
