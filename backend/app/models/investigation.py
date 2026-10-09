"""SOC VLD investigation trace models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass
class InvestigationStep:
    step: int
    pattern: str
    alert_category: Optional[str]
    v_before: list[float]
    v_after: list[float]
    cat_distances_before: dict[str, float]
    cat_distances_after: dict[str, float]
    evidence_keys: list[str]
    candidate_reads: list[str]
    selected_edge: str
    propensity: float
    cost: float
    timestamp: str
    policy_version: str
    residual: float
    halt_reason: Optional[str] = None
    evidence_available: bool = True
    evidence_admitted: bool = True
    failure_reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class InvestigationResult:
    action: str
    confidence: float
    category: str
    investigated_category: Optional[str]
    routing_agreed: bool
    trace: list[InvestigationStep]
    v_final: list[float]
    steps: int
    single_pass_action: str
    single_pass_confidence: float
    agreement: bool
    fixture_source: Optional[str] = None
    conservation_emit_gate: str = "not_evaluated_read_only"
    halt_reason: str = "unknown"
    policy: str = "vld"
    evidence_available: bool = True
    degraded: bool = False
    failed_patterns: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["trace"] = [step.to_dict() for step in self.trace]
        return payload
