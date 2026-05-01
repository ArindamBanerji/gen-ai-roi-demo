"""
In-memory ServiceNow mock for demo incident creation.

This module intentionally performs no network calls and persists nothing.
State is process-local and is reset when the backend restarts.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional


@dataclass
class MockIncident:
    incident_number: str
    decision_id: str
    alert_id: str
    short_description: str
    description: str
    urgency: int
    category: str
    status: str = "New"
    created_at: str = ""
    external_url: str = ""


class ServiceNowMock:
    """Process-local mock incident store keyed by decision_id."""

    def __init__(self) -> None:
        self._incidents: Dict[str, MockIncident] = {}
        self._counter = 47000

    def create_incident(
        self,
        decision_id: str,
        alert_id: str,
        alert_type: str = "Unknown",
        category: str = "Security",
        confidence: float = 0.5,
        nl_explanation: str = "",
        analyst_id: str = "analyst_a",
    ) -> MockIncident:
        existing = self._incidents.get(decision_id)
        if existing is not None:
            return existing

        incident_number = f"INC{self._counter:07d}"
        self._counter += 1
        description = nl_explanation or (
            f"SOC escalation for alert {alert_id} from decision {decision_id}."
        )
        if analyst_id:
            description = f"{description}\nAnalyst: {analyst_id}"

        created_at = self._created_at()
        incident = MockIncident(
            incident_number=incident_number,
            decision_id=decision_id,
            alert_id=alert_id,
            short_description=f"SOC Escalation: {alert_type or 'Unknown'}",
            description=description,
            urgency=self._confidence_to_urgency(confidence),
            category=category or "Security",
            created_at=created_at,
            external_url=f"https://demo.servicenow.local/nav_to.do?uri=incident.do?sysparm_query=number={incident_number}",
        )
        self._incidents[decision_id] = incident
        return incident

    def get_incident(self, decision_id: str) -> Optional[MockIncident]:
        return self._incidents.get(decision_id)

    def get_all_incidents(self) -> List[MockIncident]:
        return sorted(
            self._incidents.values(),
            key=lambda incident: incident.created_at,
            reverse=True,
        )

    def update_status(self, decision_id: str, status: str) -> Optional[MockIncident]:
        incident = self._incidents.get(decision_id)
        if incident is None:
            return None
        incident.status = status
        return incident

    def reset(self) -> None:
        self._incidents.clear()
        self._counter = 47000

    def _confidence_to_urgency(self, confidence: float) -> int:
        if confidence >= 0.90:
            return 1
        if confidence >= 0.75:
            return 2
        return 3

    def _created_at(self) -> str:
        now = datetime.now(timezone.utc)
        if not self._incidents:
            return now.isoformat()

        latest = max(
            datetime.fromisoformat(incident.created_at)
            for incident in self._incidents.values()
        )
        if now <= latest:
            now = latest + timedelta(microseconds=1)
        return now.isoformat()


_mock: Optional[ServiceNowMock] = None


def get_servicenow_mock() -> ServiceNowMock:
    global _mock
    if _mock is None:
        _mock = ServiceNowMock()
    return _mock
