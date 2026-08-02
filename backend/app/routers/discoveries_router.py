"""FEATURE-07 Cross-Graph Discovery API routes."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.db.graph_client import graph_client
from app.services.cross_graph_discovery import discovery_service


router = APIRouter()


class DiscoveryCacheModel(BaseModel):
    hit: bool = False
    stale: bool = False
    ttl_seconds: int | None = None


class DiscoveryItemModel(BaseModel):
    discovery_id: str
    domain: str
    source_domains: list[str] = Field(default_factory=list)
    type: str
    severity: str
    title: str
    description: str
    score: float
    discovered_at: str
    involved_entity_ids: list[str] = Field(default_factory=list)
    involved_alert_ids: list[str] = Field(default_factory=list)
    involved_decision_ids: list[str] = Field(default_factory=list)
    threat_indicator_ids: list[str] = Field(default_factory=list)
    entity_summary: str = ""
    category_summary: str = ""
    temporal_summary: str = ""
    factor_summary: str = ""


class DiscoveryEnvelopeModel(BaseModel):
    domain: str
    source_domains: list[str] = Field(default_factory=list)
    generated_at: str | None = None
    as_of_epoch_ms: int | None = None
    cache: DiscoveryCacheModel
    discoveries: list[DiscoveryItemModel] = Field(default_factory=list)
    total: int
    errors: list[str] = Field(default_factory=list)


class DiscoverySummaryModel(BaseModel):
    domain: str
    source_domains: list[str] = Field(default_factory=list)
    total: int
    high_count: int
    medium_count: int
    low_count: int
    top_discoveries: list[DiscoveryItemModel] = Field(default_factory=list)
    cache: DiscoveryCacheModel
    errors: list[str] = Field(default_factory=list)


def _validate_domain(domain: str) -> str:
    try:
        return discovery_service.validate_domain(domain)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/discoveries", response_model=DiscoveryEnvelopeModel)
async def get_discoveries(domain: str = Query("soc")):
    domain = _validate_domain(domain)
    cached = discovery_service.get_discoveries(domain)
    if cached is not None:
        return cached
    try:
        return await discovery_service.refresh(domain, graph_client)
    except Exception as exc:
        return {
            "domain": domain,
            "source_domains": [domain],
            "generated_at": None,
            "as_of_epoch_ms": None,
            "cache": {
                "hit": False,
                "stale": False,
                "ttl_seconds": discovery_service.ttl_seconds,
            },
            "discoveries": [],
            "total": 0,
            "errors": [str(exc)],
        }


@router.post("/discoveries/refresh", response_model=DiscoveryEnvelopeModel)
async def refresh_discoveries(domain: str = Query("soc")):
    domain = _validate_domain(domain)
    try:
        return await discovery_service.refresh(domain, graph_client)
    except Exception as exc:
        return {
            "domain": domain,
            "source_domains": [domain],
            "generated_at": None,
            "as_of_epoch_ms": None,
            "cache": {
                "hit": False,
                "stale": False,
                "ttl_seconds": discovery_service.ttl_seconds,
            },
            "discoveries": [],
            "total": 0,
            "errors": [str(exc)],
        }


@router.get("/discoveries/summary", response_model=DiscoverySummaryModel)
async def get_discoveries_summary(domain: str = Query("soc")):
    domain = _validate_domain(domain)
    try:
        return await discovery_service.get_summary(domain, graph_client)
    except Exception as exc:
        return {
            "domain": domain,
            "source_domains": [domain],
            "total": 0,
            "high_count": 0,
            "medium_count": 0,
            "low_count": 0,
            "top_discoveries": [],
            "cache": {
                "hit": False,
                "stale": False,
                "ttl_seconds": discovery_service.ttl_seconds,
            },
            "errors": [str(exc)],
        }
