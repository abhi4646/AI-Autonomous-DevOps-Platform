import pytest

from src.incident.model import (
    Incident,
    IncidentSeverity,
    IncidentStatus,
)
from src.persistence.database import Database


def _incident():
    return Incident(
        title="Kubernetes production failure",
        agent="kubernetes",
        severity=IncidentSeverity.CRITICAL,
        health_snapshot={
            "status": "unhealthy",
            "score": 10,
            "reasons": [
                "Critical workload failure",
            ],
        },
        rollback_available=True,
        metadata={
            "environment": "production",
        },
    )


def test_save_and_get_incident():
    database = Database(":memory:")

    incident = _incident()

    database.save_incident(
        incident.to_dict()
    )

    stored = database.get_incident(
        incident.incident_id
    )

    assert stored is not None

    assert (
        stored["incident_id"]
        == incident.incident_id
    )

    assert stored["status"] == "detected"

    assert stored["severity"] == "critical"

    assert (
        stored["health_snapshot"]["score"]
        == 10
    )

    assert (
        stored["metadata"]["environment"]
        == "production"
    )

    assert (
        stored["rollback_available"]
        is True
    )

    database.close()


def test_unknown_incident_returns_none():
    database = Database(":memory:")

    result = database.get_incident(
        "does-not-exist"
    )

    assert result is None

    database.close()


def test_get_incidents_returns_saved_incidents():
    database = Database(":memory:")

    first = _incident()

    second = Incident(
        title="Docker build failure",
        agent="docker",
        severity=IncidentSeverity.HIGH,
    )

    database.save_incident(
        first.to_dict()
    )

    database.save_incident(
        second.to_dict()
    )

    incidents = database.get_incidents()

    assert len(incidents) == 2

    ids = {
        incident["incident_id"]
        for incident in incidents
    }

    assert first.incident_id in ids
    assert second.incident_id in ids

    database.close()


def test_incident_can_be_updated():
    database = Database(":memory:")

    incident = _incident()

    database.save_incident(
        incident.to_dict()
    )

    incident.status = (
        IncidentStatus.INVESTIGATING
    )

    incident.retry_count = 1

    incident.updated_at = (
        incident._timestamp()
    )

    database.update_incident(
        incident.to_dict()
    )

    stored = database.get_incident(
        incident.incident_id
    )

    assert (
        stored["status"]
        == "investigating"
    )

    assert stored["retry_count"] == 1

    database.close()


def test_update_unknown_incident_raises():
    database = Database(":memory:")

    incident = _incident()

    with pytest.raises(KeyError):
        database.update_incident(
            incident.to_dict()
        )

    database.close()


def test_incidents_can_be_filtered_by_status():
    database = Database(":memory:")

    detected = _incident()

    resolved = Incident(
        title="Recovered Docker incident",
        agent="docker",
        severity=IncidentSeverity.MEDIUM,
        status=IncidentStatus.RESOLVED,
    )

    database.save_incident(
        detected.to_dict()
    )

    database.save_incident(
        resolved.to_dict()
    )

    results = database.get_incidents(
        status="resolved"
    )

    assert len(results) == 1

    assert (
        results[0]["incident_id"]
        == resolved.incident_id
    )

    database.close()


def test_incident_json_fields_round_trip():
    database = Database(":memory:")

    incident = _incident()

    database.save_incident(
        incident.to_dict()
    )

    stored = database.get_incident(
        incident.incident_id
    )

    assert stored["health_snapshot"] == {
        "status": "unhealthy",
        "score": 10,
        "reasons": [
            "Critical workload failure",
        ],
    }

    assert stored["metadata"] == {
        "environment": "production",
    }

    database.close()