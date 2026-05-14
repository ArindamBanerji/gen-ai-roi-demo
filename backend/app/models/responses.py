"""
app/models/responses.py — Pydantic response models for 10 priority endpoints.

Models are derived from ACTUAL live endpoint responses (GRAPH_BACKEND=age,
AGE on port 5433). Do NOT tighten types without re-verifying against the
live endpoint — a stricter type that doesn't coerce causes a 500.

Shape annotations come from observed responses:
  profile.centroids  → list[list[list[float]]]  shape (n_categories, n_actions, n_factors)
  profile.counts     → list[list[int]]           shape (n_categories, n_actions)
"""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


# =============================================================================
# 1. GET /api/soc/learning-state  →  LearningStateResponse
# =============================================================================

class IksComponents(BaseModel):
    graph_richness: float = 0.0
    decision_maturity: float = 0.0
    trust_coverage: float = 0.0
    factor_quality: float = 0.0


class LearningStateResponse(BaseModel):
    frozen: bool
    decision_count: int
    verified_decisions: int
    last_verified_at: Optional[str] = None
    checkpoint_id: Optional[str] = None
    iks_v2: float
    iks_components: IksComponents
    iks_interpretation: str
    total_decisions: int
    categories_active: int
    bootstrap_category_weights: dict[str, float] = Field(default_factory=dict)


class TriageLearningStateResponse(BaseModel):
    strategy: str
    category: str
    phase: str
    alpha: float
    dk_weights: Optional[list] = None
    freeze_point: Optional[int] = None
    decisions_in_category: int
    novelty_rate: Optional[float] = None
    batch_pipeline: Optional[dict] = None


class ChannelContribution(BaseModel):
    id: str
    label: str
    contribution_pp: float
    status: str
    description: str


class ChannelDecompositionResponse(BaseModel):
    strategy: str
    channels: list[ChannelContribution]
    total_improvement_pp: float
    irreducible_pp: float
    remaining_boundary_pp: float
    disclaimer: str


# =============================================================================
# 2. GET /api/soc/profile  →  ProfileResponse
# =============================================================================

class SwitchingCost(BaseModel):
    decisions_accumulated: int
    equivalent_calendar: str
    common_categories_days: int
    rare_categories_note: str
    competitor_iks: float = 0.0
    decisions_per_day: float
    qualifies_one_quarter: bool
    interpretation: str


class IksData(BaseModel):
    current: float
    delta_7d: float
    interpretation: str
    decision_count: int
    estimated: float
    trend: list[Any] = Field(default_factory=list)
    switching_cost: SwitchingCost


class ProfileResponse(BaseModel):
    categories: list[str]
    actions: list[str]
    centroids: list[list[list[float]]]   # shape (n_categories, n_actions, n_factors)
    counts: list[list[int]]              # shape (n_categories, n_actions)
    decision_count: int
    iks: IksData


# =============================================================================
# 3. GET /api/soc/analytics  →  AnalyticsResponse
# =============================================================================

class CategoryBreakdownItem(BaseModel):
    category: str
    count: int


class EstimatedMetric(BaseModel):
    value: Optional[float] = None
    label: str
    estimated: bool
    note: str = ""


class AnalyticsResponse(BaseModel):
    total_alerts: int
    open_alerts: int
    total_decisions: int
    correct_decisions: int
    accuracy_pct: float
    category_breakdown: list[CategoryBreakdownItem] = Field(default_factory=list)
    source: str
    estimated_metrics: list[EstimatedMetric] = Field(default_factory=list)


# =============================================================================
# 4. GET /api/soc/detection-engineering  →  DetectionEngineeringResponse
# =============================================================================

class CategoryScoreItem(BaseModel):
    category: str
    quality_score: Optional[float] = None
    drift: Optional[float] = None
    status: str


class NoiseMapItem(BaseModel):
    category: str
    fp_rate: Optional[float] = None
    total_decisions: int
    estimated: bool


class DetectionEngineeringResponse(BaseModel):
    overall_quality_score: Optional[float] = None
    category_scores: list[CategoryScoreItem] = Field(default_factory=list)
    noise_map: list[NoiseMapItem] = Field(default_factory=list)
    decisions_required_for_noise: int
    note: str = ""


# =============================================================================
# 5. GET /api/soc/campaigns  →  CampaignsResponse
# =============================================================================

class CampaignItem(BaseModel):
    campaign_id: str
    first_seen: str
    last_seen: str
    alert_count: int
    category_sequence: list[str] = Field(default_factory=list)
    shared_entities: list[Any] = Field(default_factory=list)
    confidence: float
    trigger_rule: str
    severity: str
    nl_summary: str


class CampaignsResponse(BaseModel):
    campaigns: list[CampaignItem] = Field(default_factory=list)
    total: int
    active_campaigns: int


# =============================================================================
# 6. GET /api/alerts/queue  →  AlertQueueResponse
# =============================================================================

class AlertSummary(BaseModel):
    id: str
    alert_type: str
    severity: str
    asset_hostname: str
    user_name: str
    timestamp: int
    status: str
    source_location: str


class AlertQueueResponse(BaseModel):
    alerts: list[AlertSummary] = Field(default_factory=list)


# =============================================================================
# 7. GET /api/soc/executive-narrative  →  ExecutiveNarrativeResponse
# =============================================================================

class TopShift(BaseModel):
    label: str
    magnitude: float
    description: str


class WhatChanged(BaseModel):
    total_verified: int
    total_centroid_updates: int
    top_shifts: list[TopShift] = Field(default_factory=list)
    iks_delta: float


class NewEntities(BaseModel):
    users: int = 0
    assets: int = 0
    threat_indicators: int = 0


class GraphGrowth(BaseModel):
    nodes_added: int = 0
    relationships_added: int = 0


class WhatDiscovered(BaseModel):
    attack_chains_detected: int
    chain_summaries: list[str] = Field(default_factory=list)
    new_entities: NewEntities
    graph_growth: GraphGrowth


class WhatKnows(BaseModel):
    iks_current: float
    categories_calibrated: int
    categories_total: int
    health_status: str
    operational_knowledge_status: str | None = None
    pre_activation: bool | None = None
    learning_enabled: bool | None = None
    health_source: str | None = None
    status_reason: str | None = None
    conservation_narrative: str


class NarrativeMetrics(BaseModel):
    alerts_total: int
    decisions_verified: int
    campaigns_detected: int
    iks_current: float


class ExecutiveNarrativeResponse(BaseModel):
    headline: str
    what_changed: WhatChanged
    what_discovered: WhatDiscovered
    what_knows: WhatKnows
    metrics: NarrativeMetrics
    generated_at: str
    pdf_available: bool
    sections: list[dict[str, Any]] | None = None


# =============================================================================
# 8. GET /api/triage/decision-factors/{alert_id}  →  DecisionFactorsResponse
# =============================================================================

class DecisionFactor(BaseModel):
    name: str
    value: float
    weight: float
    contribution: str
    explanation: str


class DecisionFactorsResponse(BaseModel):
    alert_id: str
    factors: list[DecisionFactor] = Field(default_factory=list)
    recommended_action: str
    confidence: float
    decision_method: str
    weights_note: str
    kernel_note: Optional[str] = None


# =============================================================================
# 9. GET /api/simulation/progress/{simulation_id}  →  SimulationProgressResponse
# =============================================================================

class SimulationProgressResponse(BaseModel):
    step: int
    total: int
    status: str
    current_accuracy: float
    category_accuracy: dict[str, float] = Field(default_factory=dict)
    latest_weight_snapshot: list[Any] = Field(default_factory=list)


# =============================================================================
# 10. GET /api/soc/centroid-support  →  CentroidSupportResponse
# =============================================================================

class CentroidSupportResponse(BaseModel):
    support_summary: dict[str, Any] = Field(default_factory=dict)
    overall_health: str
    warning_count: int
    threshold_sigma: float
    interpretation: str
    note: str = ""
