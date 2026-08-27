from fastapi.testclient import TestClient

from src.api.app import app
from src.api.routes import database
from src.incident.model import (
    Incident,
    IncidentSeverity,
    IncidentStatus,
)


client = TestClient(app)


def _create_incident(
    *,
    title="Kubernetes production failure",
    agent="kubernetes",
    severity=IncidentSeverity.CRITICAL,
    status=IncidentStatus.DETECTED,
):
    incident = Incident(
        title=title,
        agent=agent,
        severity=severity,
        status=status,
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

    database.save_incident(
        incident.to_dict()
    )

    return incident


def _delete_incident(
    incident_id,
):
    cursor = database.connection.cursor()

    cursor.execute(
        """
        DELETE FROM incidents
        WHERE incident_id = ?
        """,
        (incident_id,),
    )

    database.connection.commit()


def test_get_incidents_returns_list():
    response = client.get(
        "/api/v1/incidents"
    )

    assert response.status_code == 200
    assert isinstance(
        response.json(),
        list,
    )


def test_get_incident_by_id():
    incident = _create_incident()

    try:
        response = client.get(
            f"/api/v1/incidents/"
            f"{incident.incident_id}"
        )

        assert response.status_code == 200

        body = response.json()

        assert (
            body["incident_id"]
            == incident.incident_id
        )

        assert body["status"] == "detected"

        assert body["severity"] == "critical"

        assert body["agent"] == "kubernetes"

        assert (
            body["health_snapshot"]["score"]
            == 10
        )

        assert (
            body["metadata"]["environment"]
            == "production"
        )

        assert (
            body["rollback_available"]
            is True
        )

    finally:
        _delete_incident(
            incident.incident_id
        )


def test_unknown_incident_returns_404():
    response = client.get(
        "/api/v1/incidents/does-not-exist"
    )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "Incident not found"
    )


def test_incidents_can_be_filtered_by_status():
    detected = _create_incident(
        title="Detected Kubernetes failure",
        status=IncidentStatus.DETECTED,
    )

    resolved = _create_incident(
        title="Resolved Docker failure",
        agent="docker",
        severity=IncidentSeverity.MEDIUM,
        status=IncidentStatus.RESOLVED,
    )

    try:
        response = client.get(
            "/api/v1/incidents",
            params={
                "incident_status": "resolved",
            },
        )

        assert response.status_code == 200

        body = response.json()

        matching_ids = {
            item["incident_id"]
            for item in body
        }

        assert (
            resolved.incident_id
            in matching_ids
        )

        assert (
            detected.incident_id
            not in matching_ids
        )

        assert all(
            item["status"] == "resolved"
            for item in body
        )

    finally:
        _delete_incident(
            detected.incident_id
        )

        _delete_incident(
            resolved.incident_id
        )


def test_incident_response_contains_lifecycle_fields():
    incident = _create_incident()

    try:
        response = client.get(
            f"/api/v1/incidents/"
            f"{incident.incident_id}"
        )

        assert response.status_code == 200

        body = response.json()

        expected_fields = {
            "incident_id",
            "title",
            "agent",
            "severity",
            "status",
            "health_snapshot",
            "approval_id",
            "retry_count",
            "rollback_available",
            "metadata",
            "created_at",
            "updated_at",
            "resolved_at",
        }

        assert expected_fields.issubset(
            body.keys()
        )

    finally:
        _delete_incident(
            incident.incident_id
        )