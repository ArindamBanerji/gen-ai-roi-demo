from __future__ import annotations

from typing import List, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.servicenow_mock import MockIncident, get_servicenow_mock


router = APIRouter(prefix="/api/servicenow", tags=["servicenow"])


class CreateIncidentRequest(BaseModel):
    decision_id: str
    alert_id: str
    alert_type: str = "Unknown"
    category: str = "Security"
    confidence: float = Field(ge=0.0, le=1.0)
    nl_explanation: str = ""
    analyst_id: str = "analyst_a"


class UpdateStatusRequest(BaseModel):
    decision_id: str
    status: Literal["New", "In Progress", "Resolved"]


class IncidentResponse(BaseModel):
    incident_number: str
    decision_id: str
    alert_id: str
    short_description: str
    urgency: int
    category: str
    status: str
    created_at: str
    external_url: str


def _to_response(incident: MockIncident) -> IncidentResponse:
    return IncidentResponse(
        incident_number=incident.incident_number,
        decision_id=incident.decision_id,
        alert_id=incident.alert_id,
        short_description=incident.short_description,
        urgency=incident.urgency,
        category=incident.category,
        status=incident.status,
        created_at=incident.created_at,
        external_url=incident.external_url,
    )


@router.post("/create-incident", response_model=IncidentResponse)
async def create_incident(request: CreateIncidentRequest):
    incident = get_servicenow_mock().create_incident(
        decision_id=request.decision_id,
        alert_id=request.alert_id,
        alert_type=request.alert_type,
        category=request.category,
        confidence=request.confidence,
        nl_explanation=request.nl_explanation,
        analyst_id=request.analyst_id,
    )
    return _to_response(incident)


@router.get("/incidents", response_model=List[IncidentResponse])
async def list_incidents():
    return [_to_response(incident) for incident in get_servicenow_mock().get_all_incidents()]


@router.get("/incident/{decision_id}", response_model=IncidentResponse)
async def get_incident(decision_id: str):
    incident = get_servicenow_mock().get_incident(decision_id)
    if incident is None:
        raise HTTPException(status_code=404, detail=f"Incident for decision {decision_id} not found")
    return _to_response(incident)


@router.post("/update-status", response_model=IncidentResponse)
async def update_status(request: UpdateStatusRequest):
    incident = get_servicenow_mock().update_status(
        decision_id=request.decision_id,
        status=request.status,
    )
    if incident is None:
        raise HTTPException(status_code=404, detail=f"Incident for decision {request.decision_id} not found")
    return _to_response(incident)
