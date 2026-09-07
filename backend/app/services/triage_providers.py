"""
SOC triage dependency providers.

This module introduces explicit testable seams for route behavior that previously
required module-level monkeypatch hooks.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import numpy as np

from app.domains.soc.config import SOCDomainConfig
from app.domains.soc.config import is_learning_enabled
from app.domains.soc.orchestrator import compute_factor_vector_with_provenance


FactorProvenance = dict[str, dict[str, Any]]


@runtime_checkable
class FactorVectorProvider(Protocol):
    async def compute(self, alert: dict[str, Any], context: Any) -> tuple[np.ndarray, FactorProvenance]:
        ...


class _RealFactorVectorProvider:
    async def compute(self, alert: dict[str, Any], context: Any) -> tuple[np.ndarray, FactorProvenance]:
        computers = SOCDomainConfig.get_factor_computers()
        f, factor_provenance = await compute_factor_vector_with_provenance(
            alert,
            computers,
            context,
        )
        return f, factor_provenance


_factor_vector_provider: FactorVectorProvider | None = None


def get_factor_vector_provider() -> FactorVectorProvider:
    global _factor_vector_provider
    if _factor_vector_provider is None:
        _factor_vector_provider = _RealFactorVectorProvider()
    return _factor_vector_provider


def set_factor_vector_provider(provider: FactorVectorProvider | None) -> None:
    global _factor_vector_provider
    _factor_vector_provider = provider


@runtime_checkable
class LearningPolicy(Protocol):
    def enabled(self) -> bool:
        ...


class _ConfigLearningPolicy:
    def enabled(self) -> bool:
        return bool(is_learning_enabled())


_learning_policy: LearningPolicy | None = None


def get_learning_policy() -> LearningPolicy:
    global _learning_policy
    if _learning_policy is None:
        _learning_policy = _ConfigLearningPolicy()
    return _learning_policy


def set_learning_policy(policy: LearningPolicy | None) -> None:
    global _learning_policy
    _learning_policy = policy
