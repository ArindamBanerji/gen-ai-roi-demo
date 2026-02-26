"""Abstract interface for domain modules. Every domain (SOC, Supply Chain, etc.) implements this."""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class DomainAction:
    """One possible action the system can take."""
    id: str              # "false_positive_close", "auto_approve_po"
    label: str           # "Close as False Positive", "Auto-Approve PO"
    time_saved_min: float
    cost_dollars: float
    risk_level: str      # "low", "medium", "high", "critical"


@dataclass
class DomainFactor:
    """One scoring factor in the decision vector."""
    id: str              # "travel_match", "price_variance"
    label: str           # "Travel Match", "Price Variance"
    description: str


@dataclass
class DomainSituationType:
    """One situation classification type."""
    id: str              # "TRAVEL_LOGIN_ANOMALY", "SUPPLY_RISK"
    label: str           # "Travel Login Anomaly", "Supply Risk"
    description: str
    color: str           # hex color for UI badge, e.g. "#3B82F6"


@dataclass
class DomainPolicy:
    """One policy in the domain's policy registry."""
    id: str              # "POLICY-SOC-003"
    name: str            # "Auto-Close Travel Anomalies"
    rule: str            # human-readable rule description
    priority: int        # lower number = higher priority
    action_override: str # which action this policy forces


@dataclass
class PromptVariant:
    """One prompt variant tracked by the AgentEvolver."""
    id: str              # "TRAVEL_CONTEXT_v1"
    category: str        # "anomalous_login", "phishing"
    version: int         # 1, 2
    description: str     # "Base travel context prompt"


class DomainConfig(ABC):
    """Every domain implements this interface.

    The framework (core/) calls these methods/properties.
    The domain module (domains/soc/, domains/supply_chain/) provides the content.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier. 'soc', 'supply_chain'"""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable. 'SOC Copilot', 'Procurement Copilot'"""

    @property
    @abstractmethod
    def trigger_entity(self) -> str:
        """Primary entity that triggers decisions. 'Alert' for SOC, 'PurchaseOrder' for S2P."""

    @property
    @abstractmethod
    def factors(self) -> List[DomainFactor]:
        """The scoring factors (dimensions of the factor vector f)."""

    @property
    @abstractmethod
    def actions(self) -> List[DomainAction]:
        """The possible actions (columns of the weight matrix W)."""

    @property
    @abstractmethod
    def situation_types(self) -> List[DomainSituationType]:
        """The situation classifications."""

    @property
    @abstractmethod
    def policies(self) -> List[DomainPolicy]:
        """Domain policy registry."""

    @property
    @abstractmethod
    def asymmetry_ratio(self) -> float:
        """Penalty multiplier for incorrect decisions. 20.0 for SOC."""

    @property
    @abstractmethod
    def prompt_variants(self) -> List[PromptVariant]:
        """Prompt variants tracked by the AgentEvolver."""

    @property
    @abstractmethod
    def metrics_config(self) -> Dict:
        """Business impact numbers for Tab 4. Keys: hrs_saved_monthly, cost_avoided_quarterly, mttr_reduction_pct, backlog_eliminated."""

    @abstractmethod
    def get_seed_queries(self) -> List[str]:
        """Cypher queries to seed the demo graph for this domain."""

    @abstractmethod
    def get_graph_query_templates(self) -> Dict[str, str]:
        """Named Cypher query templates. Key=query_name, Value=Cypher string."""

    @abstractmethod
    def get_narration_templates(self) -> Dict[str, str]:
        """LLM prompt templates for reasoning narration. Key=alert_type, Value=template."""
