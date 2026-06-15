"""Domain configuration base classes.

Three shared dataclasses (DomainAction, DomainFactor, DomainSituationType)
are re-exported from copilot_sdk.domains.base - the SDK canonical source.
These are frozen dataclasses with defaults. All SOC construction sites
provide all fields, so frozen + defaults is compatible.

Two SOC-specific dataclasses (DomainPolicy, PromptVariant) remain local.
Their fields are SOC-specific and do not belong in the SDK.
See design_sdk_domain_unification_v2.md for rationale.

DomainConfig ABC remains local - it defines the SOC domain contract
with abstract methods for seed queries, graph templates, narration,
and metrics that are not generic across copilots.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List

from copilot_sdk.domains.base import (  # noqa: F401
    DomainAction,
    DomainFactor,
    DomainSituationType,
)


@dataclass
class DomainPolicy:
    """SOC-specific policy metadata.

    Fields: name, rule, priority, action_override.
    Not generic - other copilots' policies have different fields.
    Note: runtime policy engine uses app.domains.soc.policies (plain dicts),
    not this dataclass. This is metadata for counts and warm-up only.
    """

    id: str
    name: str
    rule: str
    priority: int
    action_override: str


@dataclass
class PromptVariant:
    """SOC-specific prompt variant metadata.

    Fields: category, version, description.
    Not consumed by SDK PromptVariantEvolver (which uses PromptEvolverConfig).
    This is metadata for warm-up only.
    """

    id: str
    category: str
    version: int
    description: str


class DomainConfig(ABC):
    """SOC domain contract.

    Defines abstract properties for domain identity, metadata lists,
    and SOC-specific methods (seed queries, graph templates, narration).

    SDK copilots use BaseDomainConfig (copilot_sdk.domains.base) instead.
    BaseDomainConfig is concrete with no abstract methods.
    """

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def display_name(self) -> str: ...

    @property
    @abstractmethod
    def trigger_entity(self) -> str: ...

    @property
    @abstractmethod
    def factors(self) -> List[DomainFactor]: ...

    @property
    @abstractmethod
    def actions(self) -> List[DomainAction]: ...

    @property
    @abstractmethod
    def situation_types(self) -> List[DomainSituationType]: ...

    @property
    @abstractmethod
    def policies(self) -> List[DomainPolicy]: ...

    @property
    @abstractmethod
    def asymmetry_ratio(self) -> float: ...

    @property
    @abstractmethod
    def prompt_variants(self) -> List[PromptVariant]: ...

    @property
    @abstractmethod
    def metrics_config(self) -> Dict: ...

    @abstractmethod
    def get_seed_queries(self) -> List[str]: ...

    @abstractmethod
    def get_graph_query_templates(self) -> Dict[str, str]: ...

    @abstractmethod
    def get_narration_templates(self) -> Dict[str, str]: ...


__all__ = [
    "DomainAction",
    "DomainFactor",
    "DomainSituationType",
    "DomainPolicy",
    "PromptVariant",
    "DomainConfig",
]
