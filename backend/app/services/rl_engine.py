"""Phase 1/2 RL components.

This module contains reward computation, an explanatory in-memory ledger, and
Phase 2 exploration policy state. It does not touch ProfileScorer,
conservation health, graph state, or triage integration.
"""

from __future__ import annotations

import logging
import math
import os
import random
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, cast

from app.domains.soc.severity import get_severity_weights

DEFAULT_SOC_REFERENCE_REWARD = 0.50
DEFAULT_S2P_REFERENCE_REWARD = 0.30
DEFAULT_PENALTY_RATIO = 20.0  # SOC CalibrationProfile penalty_ratio; no exported config constant.
ROLLING_REFERENCE_WINDOW = 400

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RewardResult:
    graded_reward: float
    binary_outcome: bool
    reward_weight: float
    breakdown: Dict[str, Any]
    domain: str


class RewardComputer:
    """Compute graded rewards without mutating scorer or conservation state."""

    def __init__(
        self,
        domain: str = "soc",
        severity_weights: Dict[str, Dict[str, float]] | None = None,
        penalty_ratio: float = DEFAULT_PENALTY_RATIO,
        reference_reward: float | None = None,
    ) -> None:
        self.domain = domain
        self.severity_weights = severity_weights or {}
        self.penalty_ratio = float(penalty_ratio)
        if reference_reward is None:
            reference_reward = (
                DEFAULT_S2P_REFERENCE_REWARD
                if domain in {"s2p", "supply_chain"}
                else DEFAULT_SOC_REFERENCE_REWARD
            )
        self.reference_reward = float(reference_reward)
        self._reward_history: List[float] = []

    def compute(
        self,
        action: str,
        outcome: str,
        category: str,
        context: Dict[str, Any] | None = None,
    ) -> RewardResult:
        context = context or {}
        binary_outcome = outcome == "correct"

        if self.domain == "soc":
            graded_reward, breakdown = self._compute_soc(binary_outcome, category, context)
        elif self.domain in {"s2p", "supply_chain"}:
            graded_reward, breakdown = self._compute_s2p(binary_outcome, category, context)
        else:
            graded_reward, breakdown = self._compute_unknown(binary_outcome, category)

        reward_weight = self._compute_reward_weight(graded_reward)
        self._reward_history.append(graded_reward)
        return RewardResult(
            graded_reward=round(graded_reward, 6),
            binary_outcome=binary_outcome,
            reward_weight=round(reward_weight, 6),
            breakdown={**breakdown, "action": action, "outcome": outcome},
            domain=self.domain,
        )

    def _compute_soc(
        self,
        binary_outcome: bool,
        category: str,
        context: Dict[str, Any],
    ) -> tuple[float, Dict[str, Any]]:
        severity = float(self.severity_weights.get(category, {}).get("base", 0.50))
        campaign_multiplier = 1.5 if context.get("campaign_id") else 1.0
        sign = 1.0 if binary_outcome else -1.0 * self.penalty_ratio
        reward = sign * severity * campaign_multiplier
        return reward, {
            "category": category,
            "severity": severity,
            "campaign_multiplier": campaign_multiplier,
            "penalty_ratio": self.penalty_ratio,
            "formula": "soc_category_base",
        }

    def _compute_s2p(
        self,
        binary_outcome: bool,
        category: str,
        context: Dict[str, Any],
    ) -> tuple[float, Dict[str, Any]]:
        financial_impact = float(context.get("financial_impact", 0.0) or 0.0)
        reference = float(self.severity_weights.get(category, {}).get("reference", 45.0))
        impact_weight = min(financial_impact / reference, 1.0) if reference > 0 else 0.0
        cluster_multiplier = 1.3 if context.get("exception_cluster") else 1.0
        sign = 1.0 if binary_outcome else -1.0 * self.penalty_ratio
        reward = sign * impact_weight * cluster_multiplier
        return reward, {
            "category": category,
            "financial_impact": financial_impact,
            "reference": reference,
            "impact_weight": impact_weight,
            "cluster_multiplier": cluster_multiplier,
            "penalty_ratio": self.penalty_ratio,
            "formula": "s2p_financial_impact",
        }

    def _compute_unknown(
        self,
        binary_outcome: bool,
        category: str,
    ) -> tuple[float, Dict[str, Any]]:
        reward = 1.0 if binary_outcome else -1.0 * self.penalty_ratio
        return reward, {
            "category": category,
            "fallback": True,
            "penalty_ratio": self.penalty_ratio,
            "formula": "unknown_domain_fallback",
        }

    def _compute_reward_weight(self, graded_reward: float) -> float:
        reference = self._get_reference_reward()
        raw = abs(graded_reward) / reference if reference > 0 else 1.0
        return max(0.1, min(raw, 3.0))

    def _get_reference_reward(self) -> float:
        if len(self._reward_history) >= ROLLING_REFERENCE_WINDOW:
            sorted_abs = sorted(abs(r) for r in self._reward_history[-ROLLING_REFERENCE_WINDOW:])
            return sorted_abs[len(sorted_abs) // 2]
        return self.reference_reward


@dataclass(frozen=True)
class RewardLedgerEntry:
    decision_id: str
    category: str
    action: str
    binary_outcome: bool
    graded_reward: float
    reward_weight: float
    breakdown: Dict[str, Any]
    domain: str
    timestamp_epoch: int
    alert_id: str = ""
    explored: bool = False
    explored_but_referred: bool = False
    posterior_updated: bool = False
    schema_version: int = 1


@dataclass(frozen=True)
class ChainCredit:
    source_decision_id: str
    target_decision_id: str
    chain_reward: float
    gamma: float
    age: int


class RewardLedger:
    """Append-only in-memory reward ledger for Phase 1 validation."""

    MAX_ENTRIES = 10_000
    MAX_CHAIN_CREDITS = 50_000

    def __init__(self) -> None:
        self._entries: List[RewardLedgerEntry] = []
        self._chain_credits: List[ChainCredit] = []

    def append(
        self,
        decision_id: str,
        reward_result: RewardResult,
        category: str,
        action: str,
        alert_id: str = "",
        explored: bool = False,
        explored_but_referred: bool = False,
        posterior_updated: bool = False,
        timestamp_epoch: int | None = None,
    ) -> RewardLedgerEntry:
        entry = RewardLedgerEntry(
            decision_id=decision_id,
            alert_id=alert_id,
            category=category,
            action=action,
            binary_outcome=reward_result.binary_outcome,
            graded_reward=reward_result.graded_reward,
            reward_weight=reward_result.reward_weight,
            breakdown=dict(reward_result.breakdown),
            domain=reward_result.domain,
            timestamp_epoch=timestamp_epoch if timestamp_epoch is not None else int(time.time() * 1000),
            explored=bool(explored),
            explored_but_referred=bool(explored_but_referred),
            posterior_updated=bool(posterior_updated),
        )
        self._entries.append(entry)
        if len(self._entries) > self.MAX_ENTRIES:
            del self._entries[: len(self._entries) - self.MAX_ENTRIES]
        return entry

    def get_entries(self, limit: int = 100) -> List[Dict[str, Any]]:
        limit = max(0, int(limit))
        if limit == 0:
            return []
        return [asdict(entry) for entry in self._entries[-limit:]]

    def get_summary(self) -> Dict[str, Any]:
        total = len(self._entries)
        correct = sum(1 for entry in self._entries if entry.binary_outcome)
        incorrect = total - correct
        cumulative = round(sum(entry.graded_reward for entry in self._entries), 6)
        avg_weight = (
            round(sum(entry.reward_weight for entry in self._entries) / total, 6)
            if total
            else 0.0
        )
        return {
            "total_entries": total,
            "correct": correct,
            "incorrect": incorrect,
            "cumulative_graded_reward": cumulative,
            "avg_reward_weight": avg_weight,
            "schema_version": 1,
        }

    def reset(self) -> None:
        self._entries.clear()
        self._chain_credits.clear()

    def add_chain_credit(self, credit: ChainCredit) -> ChainCredit:
        self._chain_credits.append(credit)
        if len(self._chain_credits) > self.MAX_CHAIN_CREDITS:
            del self._chain_credits[: len(self._chain_credits) - self.MAX_CHAIN_CREDITS]
        return credit

    def get_chain_credits(self, target_decision_id: str | None = None) -> List[Dict[str, Any]]:
        credits = self._chain_credits
        if target_decision_id is not None:
            credits = [
                credit for credit in credits
                if credit.target_decision_id == target_decision_id
            ]
        return [asdict(credit) for credit in credits]


@dataclass(frozen=True)
class ExplorationDecision:
    original_action: int
    explored_action: int | None
    explored: bool
    exploration_rate: float = 0.0
    posterior_snapshot: Dict[str, Any] | None = None
    reason: str = ""


class ExplorationPolicy:
    """Conservation-bounded Thompson sampling over scorer actions."""

    def __init__(
        self,
        n_categories: int,
        n_actions: int,
        epsilon_base: float = 0.05,
        target_headroom: float = 10.0,
        posterior_store: Any | None = None,
    ) -> None:
        if target_headroom <= 1.0:
            raise ValueError("target_headroom must be > 1.0 for ratio-based exploration")
        self.n_categories = int(n_categories)
        self.n_actions = int(n_actions)
        self.epsilon_base = float(epsilon_base)
        self.target_headroom = float(target_headroom)
        self.posterior_store = posterior_store
        loaded: Dict[str, Any] = {}
        if posterior_store is not None:
            loaded = posterior_store.load(self.n_categories, self.n_actions)
        self.alphas = self._coerce_matrix(loaded.get("alphas"), default=1.0)
        self.betas = self._coerce_matrix(loaded.get("betas"), default=1.0)

    def propose(
        self,
        probabilities: list[float],
        category_index: int,
        headroom_ratio: float,
    ) -> ExplorationDecision:
        original_action = self._argmax(probabilities)
        rate = self._compute_rate(headroom_ratio)
        if rate == 0.0:
            return ExplorationDecision(
                original_action=original_action,
                explored_action=None,
                explored=False,
                exploration_rate=rate,
                reason="no_exploration",
            )
        if random.random() > rate:
            return ExplorationDecision(
                original_action=original_action,
                explored_action=None,
                explored=False,
                exploration_rate=rate,
                reason="random_skip",
            )

        category_index = self._safe_category_index(category_index)
        samples = [
            random.betavariate(max(alpha, 0.01), max(beta, 0.01))
            for alpha, beta in zip(self.alphas[category_index], self.betas[category_index])
        ]
        explored_action = self._argmax(samples)
        return ExplorationDecision(
            original_action=original_action,
            explored_action=explored_action,
            explored=True,
            exploration_rate=rate,
            posterior_snapshot={
                "category_index": category_index,
                "alphas": list(self.alphas[category_index]),
                "betas": list(self.betas[category_index]),
                "samples": samples,
            },
            reason="thompson_sampled",
        )

    def _compute_rate(self, headroom_ratio: float) -> float:
        headroom = float(headroom_ratio or 0.0)
        if headroom <= 1.0:
            return 0.0
        normalized = min((headroom - 1.0) / (self.target_headroom - 1.0), 1.0)
        return self.epsilon_base * normalized

    def update_posterior(self, category_index: int, action_index: int, correct: bool) -> None:
        category_index = self._safe_category_index(category_index)
        action_index = self._safe_action_index(action_index)
        if correct:
            self.alphas[category_index][action_index] += 1.0
        else:
            self.betas[category_index][action_index] += 1.0
        self._save()

    def reset_posteriors(self, reason: str = "") -> None:
        self.alphas = [[2.0 for _ in range(self.n_actions)] for _ in range(self.n_categories)]
        self.betas = [[2.0 for _ in range(self.n_actions)] for _ in range(self.n_categories)]
        self._save()
        if self.posterior_store is not None:
            self.posterior_store.log_reset(reason)

    @staticmethod
    def _argmax(values: list[float]) -> int:
        if not values:
            raise ValueError("values must not be empty")
        best_index = 0
        best_value = values[0]
        for index, value in enumerate(values[1:], start=1):
            if value > best_value:
                best_index = index
                best_value = value
        return best_index

    def _coerce_matrix(self, matrix: Any, default: float) -> list[list[float]]:
        result = [[float(default) for _ in range(self.n_actions)] for _ in range(self.n_categories)]
        if not isinstance(matrix, list):
            return result
        for category_index, row in enumerate(matrix[: self.n_categories]):
            if not isinstance(row, list):
                continue
            for action_index, value in enumerate(row[: self.n_actions]):
                result[category_index][action_index] = float(value)
        return result

    def _safe_category_index(self, category_index: int) -> int:
        if not 0 <= int(category_index) < self.n_categories:
            raise IndexError("category_index out of range")
        return int(category_index)

    def _safe_action_index(self, action_index: int) -> int:
        if not 0 <= int(action_index) < self.n_actions:
            raise IndexError("action_index out of range")
        return int(action_index)

    def _save(self) -> None:
        if self.posterior_store is None:
            return
        self.posterior_store.save(self.alphas, self.betas)


class CreditAssigner:
    """Read-only chain credit and factor attribution helper."""

    HALF_LIFE = 30
    LOOKBACK = 100
    CHAIN_DISCOUNT = 0.5

    def __init__(self, graph_client: Any | None = None) -> None:
        self.graph_client = graph_client

    async def assign_chain_credit(
        self,
        source_decision_id: str,
        category: str,
        action_index: int,
        current_decision_number: int,
        reward: float,
        reward_ledger: RewardLedger | None = None,
    ) -> list[ChainCredit]:
        if self.graph_client is None or not hasattr(self.graph_client, "run_query"):
            return []
        reward_value = float(reward)
        if reward_value == 0.0:
            return []

        try:
            action_idx = int(action_index)
            current_number = int(current_decision_number)
        except (TypeError, ValueError) as exc:
            log.warning("[CreditAssigner] invalid chain-credit numeric input: %s", exc)
            return []

        try:
            from app.graph_schema import _S

            min_decision_number = max(0, current_number - self.LOOKBACK)
            query = (
                "MATCH (d:Decision)-[:TRIGGERED_EVOLUTION]->(e:EvolutionEvent)\n"
                f"WHERE d.category = {_S(category)}\n"
                f"  AND d.action_index = {action_idx}\n"
                f"  AND d.decision_number >= {min_decision_number}\n"
                f"  AND d.decision_number < {current_number}\n"
                "  AND d.verified_correct = true\n"
                f"  AND d.decision_id <> {_S(source_decision_id)}\n"
                "RETURN d.decision_id AS decision_id, "
                "d.decision_number AS decision_number, "
                "d.factor_snapshot AS factor_snapshot, "
                "d.action_index AS action_index\n"
                "ORDER BY d.decision_number DESC"
            )
            rows = await self.graph_client.run_query(query)
        except Exception as exc:
            log.warning("[CreditAssigner] chain-credit query failed: %s", exc)
            return []

        historical: list[dict[str, Any]] = []
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            decision_id = row.get("decision_id")
            if decision_id == source_decision_id:
                continue
            try:
                decision_number = int(cast(Any, row.get("decision_number")))
            except (TypeError, ValueError):
                continue
            age = max(0, current_number - decision_number)
            if age > self.LOOKBACK:
                continue
            historical.append({
                "decision_id": str(decision_id),
                "decision_number": decision_number,
                "age": age,
            })

        if not historical:
            return []

        weights = [
            math.exp(-math.log(2) * item["age"] / self.HALF_LIFE)
            for item in historical
        ]
        total_weight = sum(weights)
        if total_weight <= 0.0:
            return []

        credits: list[ChainCredit] = []
        credit_budget = abs(reward_value) * self.CHAIN_DISCOUNT
        for item, weight in zip(historical, weights):
            gamma = weight / total_weight
            credit = ChainCredit(
                source_decision_id=str(source_decision_id),
                target_decision_id=item["decision_id"],
                chain_reward=credit_budget * gamma,
                gamma=gamma,
                age=item["age"],
            )
            credits.append(credit)
            if reward_ledger is not None:
                reward_ledger.add_chain_credit(credit)
        return credits

    def compute_factor_attribution(
        self,
        scorer: Any,
        factor_vector: Any,
        category_index: int,
        action_index: int,
        reward: float,
        delta: float = 0.01,
    ) -> dict[int, float]:
        values = [float(value) for value in factor_vector]
        attribution: dict[int, float] = {}
        for index in range(len(values)):
            f_plus = list(values)
            f_minus = list(values)
            f_plus[index] = min(f_plus[index] + delta, 1.0)
            f_minus[index] = max(f_minus[index] - delta, 0.0)
            p_plus = scorer.score(f_plus, category_index).probabilities[action_index]
            p_minus = scorer.score(f_minus, category_index).probabilities[action_index]
            attribution[index] = ((float(p_plus) - float(p_minus)) / (2.0 * delta)) * float(reward)
        return attribution


_reward_computer: RewardComputer | None = None
_reward_ledger: RewardLedger | None = None
_posterior_store: Any | None = None
_exploration_policy: ExplorationPolicy | None = None
_credit_assigner: CreditAssigner | None = None


def get_reward_computer() -> RewardComputer:
    global _reward_computer
    if _reward_computer is None:
        _reward_computer = RewardComputer(
            domain="soc",
            severity_weights=get_severity_weights(),
            penalty_ratio=DEFAULT_PENALTY_RATIO,
            reference_reward=DEFAULT_SOC_REFERENCE_REWARD,
        )
    return _reward_computer


def get_reward_ledger() -> RewardLedger:
    global _reward_ledger
    if _reward_ledger is None:
        _reward_ledger = RewardLedger()
    return _reward_ledger


def get_exploration_policy() -> ExplorationPolicy:
    global _posterior_store, _exploration_policy
    if _exploration_policy is None:
        from app.domains.soc.config import SCORER_ACTIONS, SOC_CATEGORIES

        test_mode = bool(os.environ.get("PYTEST_CURRENT_TEST"))
        try:
            from app.services.posterior_store import PosteriorStore

            _posterior_store = PosteriorStore()
        except Exception as exc:
            if not test_mode:
                raise RuntimeError("[RL] PosteriorStore is required outside test mode") from exc
            log.warning("[RL] test mode: PosteriorStore unavailable; using in-memory priors: %s", exc)
            _posterior_store = None
        try:
            _exploration_policy = ExplorationPolicy(
                n_categories=len(SOC_CATEGORIES),
                n_actions=len(SCORER_ACTIONS),
                posterior_store=_posterior_store,
            )
        except Exception as exc:
            if not test_mode:
                raise RuntimeError("[RL] PosteriorStore is required outside test mode") from exc
            log.warning("[RL] test mode: posterior load unavailable; using in-memory priors: %s", exc)
            _posterior_store = None
            _exploration_policy = ExplorationPolicy(
                n_categories=len(SOC_CATEGORIES),
                n_actions=len(SCORER_ACTIONS),
                posterior_store=None,
            )
    return _exploration_policy


def get_credit_assigner() -> CreditAssigner:
    global _credit_assigner
    if _credit_assigner is None:
        try:
            from app.db.neo4j import neo4j_client
        except Exception as exc:
            log.warning("[RL] graph client unavailable for CreditAssigner: %s", exc)
            neo4j_client = None
        _credit_assigner = CreditAssigner(neo4j_client)
    return _credit_assigner


def reset_rl_state() -> None:
    global _reward_computer, _reward_ledger, _posterior_store, _exploration_policy, _credit_assigner
    if _exploration_policy is not None:
        _exploration_policy.reset_posteriors("demo_reset")
    if _posterior_store is not None:
        _posterior_store.clear()
    _reward_computer = None
    _reward_ledger = None
    _exploration_policy = None
    _posterior_store = None
    _credit_assigner = None
