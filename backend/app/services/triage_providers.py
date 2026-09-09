"""
SOC triage dependency providers.

This module introduces explicit testable seams for route behavior that previously
required module-level monkeypatch hooks.
"""
from __future__ import annotations

from typing import Any, Protocol, cast, runtime_checkable

import numpy as np

from app.domains.soc.config import N_FACTORS, SOC_FACTORS, SOCDomainConfig
from app.domains.soc.config import is_learning_enabled
from app.domains.soc.orchestrator import compute_factor_vector_with_provenance


FactorProvenance = dict[str, dict[str, Any]]


class EvidenceScopedGraphAdapter:
    """Graph adapter exposing only VLD-admitted evidence to factor extraction."""

    def __init__(
        self,
        base_graph: Any,
        admitted_evidence: list[dict[str, Any]],
        surface_vector: np.ndarray,
    ) -> None:
        self.base_graph = base_graph
        self.admitted_evidence = list(admitted_evidence)
        self.vld_surface_vector = np.asarray(surface_vector, dtype=np.float64).copy()
        self.vld_factor_vectors = [
            np.asarray(item.get("vld_factor_vector"), dtype=np.float64)
            for item in self.admitted_evidence
            if isinstance(item.get("vld_factor_vector"), list)
        ]

    async def get_security_context(self, alert_id: str) -> dict[str, Any]:
        get_context = getattr(self.base_graph, "get_security_context", None)
        base_context: dict[str, Any] = {}
        if callable(get_context):
            raw = get_context(alert_id)
            if hasattr(raw, "__await__"):
                raw = await raw
            if isinstance(raw, dict):
                base_context = dict(raw)
        admitted: dict[str, Any] = {}
        for evidence in self.admitted_evidence:
            admitted.update(evidence)
        return {**base_context, **admitted}

    async def run_query(self, *args: Any, **kwargs: Any) -> Any:
        run_query = getattr(self.base_graph, "run_query", None)
        if not callable(run_query):
            return []
        result = run_query(*args, **kwargs)
        if hasattr(result, "__await__"):
            return await result
        return result


def build_evidence_scoped_graph(
    base_graph: Any,
    admitted_evidence: list[dict[str, Any]],
    surface_vector: np.ndarray,
) -> EvidenceScopedGraphAdapter:
    return EvidenceScopedGraphAdapter(base_graph, admitted_evidence, surface_vector)


def _apply_vld_reextraction(vector: np.ndarray, context: Any) -> np.ndarray:
    if not isinstance(context, EvidenceScopedGraphAdapter):
        return vector
    surface = context.vld_surface_vector
    evidence_vectors = context.vld_factor_vectors
    if surface is None or not evidence_vectors:
        return vector
    arrays = [np.asarray(surface, dtype=np.float64)] + [
        np.asarray(item, dtype=np.float64) for item in evidence_vectors
    ]
    if any(item.shape != arrays[0].shape for item in arrays):
        return vector
    return cast(np.ndarray, np.clip(sum(arrays) / float(len(arrays)), 0.0, 1.0))


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
        expected_dim = len(computers) or N_FACTORS
        factor_names = [getattr(computer, "name", "") for computer in computers] or list(SOC_FACTORS)
        if f.shape != (expected_dim,) and all(name in factor_provenance for name in factor_names):
            f = np.asarray(
                [factor_provenance[name]["value"] for name in factor_names],
                dtype=np.float64,
            )
        f = _apply_vld_reextraction(f, context)
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
