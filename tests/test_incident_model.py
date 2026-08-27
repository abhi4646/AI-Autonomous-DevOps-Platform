import pytest

from src.incident.model import (
    Incident,
    IncidentSeverity,
    IncidentStatus,
)


def test_incident_defaults_to_detected():
    incident = Incident(
        title="Kubernetes workload unhealthy",
        agent="kubernetes",
        severity=IncidentSeverity.HIGH,
    )

    assert incident.incident_id
    assert (
        incident.status
        == IncidentStatus.DETECTED
    )
    assert incident.retry_count == 0
    assert incident.approval_id is None


def test_incident_serializes_to_dict():
    incident = Incident(
        title="Docker build failure",
        agent="docker",
        severity=IncidentSeverity.MEDIUM,
        health_snapshot={
            "status": "unhealthy",
            "score": 30,
        },
    )

    result = incident.to_dict()

    assert (
        result["incident_id"]
        == incident.incident_id
    )
    assert result["severity"] == "medium"
    assert result["status"] == "detected"
    assert (
        result["health_snapshot"]["score"]
        == 30
    )


def test_incident_round_trip():
    incident = Incident(
        title="Terraform failure",
        agent="terraform",
        severity=IncidentSeverity.CRITICAL,
        metadata={
            "environment": "production",
        },
    )

    restored = Incident.from_dict(
        incident.to_dict()
    )

    assert (
        restored.incident_id
        == incident.incident_id
    )
    assert (
        restored.severity
        == IncidentSeverity.CRITICAL
    )
    assert (
        restored.metadata["environment"]
        == "production"
    )


def test_empty_title_is_rejected():
    with pytest.raises(ValueError):
        Incident(
            title=" ",
            agent="kubernetes",
            severity=IncidentSeverity.HIGH,
        )


def test_empty_agent_is_rejected():
    with pytest.raises(ValueError):
        Incident(
            title="Failure",
            agent=" ",
            severity=IncidentSeverity.HIGH,
        )


def test_negative_retry_count_is_rejected():
    with pytest.raises(ValueError):
        Incident(
            title="Failure",
            agent="kubernetes",
            severity=IncidentSeverity.HIGH,
            retry_count=-1,
        )