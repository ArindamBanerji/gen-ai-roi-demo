import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.services.servicenow_mock import ServiceNowMock


def _create(mock: ServiceNowMock, decision_id: str = "DEC-1", confidence: float = 0.91):
    return mock.create_incident(
        decision_id=decision_id,
        alert_id="ALERT-1",
        alert_type="Impossible travel",
        category="credential_access",
        confidence=confidence,
        nl_explanation="Escalation confirmed.",
    )


def test_create_incident_returns_valid():
    incident = _create(ServiceNowMock())

    assert incident.incident_number == "INC0047000"
    assert incident.decision_id == "DEC-1"
    assert incident.alert_id == "ALERT-1"
    assert incident.short_description == "SOC Escalation: Impossible travel"
    assert incident.urgency == 1
    assert incident.status == "New"
    assert incident.created_at
    assert incident.incident_number in incident.external_url


def test_create_incident_idempotent():
    mock = ServiceNowMock()

    first = _create(mock, decision_id="DEC-1")
    second = _create(mock, decision_id="DEC-1")

    assert first is second
    assert second.incident_number == "INC0047000"
    assert len(mock.get_all_incidents()) == 1


def test_different_decisions_different_numbers():
    mock = ServiceNowMock()

    first = _create(mock, decision_id="DEC-1")
    second = _create(mock, decision_id="DEC-2")

    assert first.incident_number == "INC0047000"
    assert second.incident_number == "INC0047001"


def test_get_incident_exists():
    mock = ServiceNowMock()
    incident = _create(mock, decision_id="DEC-1")

    assert mock.get_incident("DEC-1") == incident


def test_get_incident_not_found():
    assert ServiceNowMock().get_incident("missing") is None


def test_get_all_incidents_ordered():
    mock = ServiceNowMock()
    first = _create(mock, decision_id="DEC-1")
    second = _create(mock, decision_id="DEC-2")

    incidents = mock.get_all_incidents()

    assert incidents == [second, first]


def test_update_status():
    mock = ServiceNowMock()
    _create(mock, decision_id="DEC-1")

    incident = mock.update_status("DEC-1", "Resolved")

    assert incident is not None
    assert incident.status == "Resolved"


def test_update_status_not_found():
    assert ServiceNowMock().update_status("missing", "Resolved") is None


def test_reset_clears_all():
    mock = ServiceNowMock()
    _create(mock, decision_id="DEC-1")

    mock.reset()
    incident = _create(mock, decision_id="DEC-2")

    assert mock.get_incident("DEC-1") is None
    assert incident.incident_number == "INC0047000"


def test_confidence_to_urgency_high():
    assert ServiceNowMock()._confidence_to_urgency(0.90) == 1


def test_confidence_to_urgency_medium():
    assert ServiceNowMock()._confidence_to_urgency(0.75) == 2


def test_confidence_to_urgency_low():
    assert ServiceNowMock()._confidence_to_urgency(0.74) == 3
