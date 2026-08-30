"""Enterprise system health and process-fusion routes."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.connectors.celonis import CelonisConnector
from app.connectors.sap import SAPConnector


router = APIRouter()
_sap = SAPConnector()
_celonis = CelonisConnector()


class EnterpriseHealthResponse(BaseModel):
    status: str
    connectors: list[dict[str, Any]]


class ProcessTimelineResponse(BaseModel):
    status: str
    sources: list[dict[str, Any]]
    timeline: list[dict[str, str]] = Field(default_factory=list)


@router.get("/enterprise-health", response_model=EnterpriseHealthResponse)
async def enterprise_health() -> EnterpriseHealthResponse:
    sap, celonis = await asyncio.gather(_sap.health_check(), _celonis.health_check())
    return EnterpriseHealthResponse(status="operational", connectors=[sap, celonis])


@router.get("/enterprise/process-timeline", response_model=ProcessTimelineResponse)
async def process_timeline() -> ProcessTimelineResponse:
    sap, celonis = await asyncio.gather(_sap.fetch(), _celonis.fetch())
    timeline = [
        {"stage": "ERP event", "detail": "Supplier and purchasing records", "source": sap["label"]},
        {"stage": "Process signal", "detail": "Bottleneck and exception activity", "source": celonis["label"]},
        {"stage": "Fusion", "detail": "Reason over the process with enterprise context", "source": "Compounding Intelligence"},
    ]
    return ProcessTimelineResponse(status="operational", sources=[sap, celonis], timeline=timeline)
