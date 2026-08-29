from uuid import uuid4

from fastapi.testclient import TestClient

from src.api.app import app
from src.api.routes import database
from src.incident.model import (
    Incident,
    IncidentSeverity,
    IncidentStatus,
)


client = TestClient(app)


# ---------------------------------------------------------
# TEST HELPERS
# ---------------------------------------------------------

def _signal_id():
    return f"signal-{uuid4()}"


def _create_incident():
    incident = Incident(
        title="Correlation API test incident",
        agent="kubernetes",
        severity=IncidentSeverity.CRITICAL,
        status=IncidentStatus.DETECTED,
        health_snapshot={
            "status": "unhealthy",
            "score": 10,
        },
        metadata={
            "environment": "production",
        },
    )

    database.save_incident(
        incident.to_dict()
    )

    return incident


def _signal_payload(
    signal_id,
    *,
    incident_id=None,
    correlation_key="payments-api",
):
    payload = {
        "signal_id": signal_id,
        "signal_type": "deployment",
        "source": "kubernetes",
        "resource": "payments-api",
        "severity": "high",
        "message": "Deployment completed",
        "agent": "kubernetes",
        "environment": "production",
        "correlation_key": correlation_key,
        "occurred_at": (
            "2026-08-27T10:05:00+00:00"
        ),
        "metadata": {
            "version": "v2",
        },
    }

    if incident_id is not None:
        payload["incident_id"] = incident_id

    return payload


def _delete_signal(
    signal_id,
):
    cursor = database.connection.cursor()

    cursor.execute(
        """
        DELETE FROM operational_signals
        WHERE signal_id = ?
        """,
        (signal_id,),
    )

    database.connection.commit()


def _delete_incident(
    incident_id,
):
    cursor = database.connection.cursor()

    cursor.execute(
        """
        DELETE FROM rca_results
        WHERE incident_id = ?
        """,
        (incident_id,),
    )

    cursor.execute(
        """
        DELETE FROM operational_signals
        WHERE incident_id = ?
        """,
        (incident_id,),
    )

    cursor.execute(
        """
        DELETE FROM incidents
        WHERE incident_id = ?
        """,
        (incident_id,),
    )

    database.connection.commit()


# ---------------------------------------------------------
# SIGNAL CREATION
# ---------------------------------------------------------

def test_create_signal():
    signal_id = _signal_id()

    try:
        response = client.post(
            "/api/v1/signals",
            json=_signal_payload(
                signal_id
            ),
        )

        assert response.status_code == 201

        body = response.json()

        assert (
            body["signal_id"]
            == signal_id
        )

        assert (
            body["signal_type"]
            == "deployment"
        )

        assert (
            body["resource"]
            == "payments-api"
        )

        assert (
            body["metadata"]["version"]
            == "v2"
        )

    finally:
        _delete_signal(
            signal_id
        )


def test_create_signal_with_incident():
    incident = _create_incident()
    signal_id = _signal_id()

    try:
        response = client.post(
            "/api/v1/signals",
            json=_signal_payload(
                signal_id,
                incident_id=(
                    incident.incident_id
                ),
            ),
        )

        assert response.status_code == 201

        assert (
            response.json()["incident_id"]
            == incident.incident_id
        )

    finally:
        _delete_incident(
            incident.incident_id
        )


def test_create_signal_with_unknown_incident_returns_404():
    signal_id = _signal_id()

    response = client.post(
        "/api/v1/signals",
        json=_signal_payload(
            signal_id,
            incident_id=(
                "does-not-exist"
            ),
        ),
    )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "Incident not found"
    )


def test_duplicate_signal_returns_409():
    signal_id = _signal_id()

    try:
        first = client.post(
            "/api/v1/signals",
            json=_signal_payload(
                signal_id
            ),
        )

        assert first.status_code == 201

        second = client.post(
            "/api/v1/signals",
            json=_signal_payload(
                signal_id
            ),
        )

        assert second.status_code == 409

        assert (
            second.json()["detail"]
            == (
                "Operational signal "
                "already exists"
            )
        )

    finally:
        _delete_signal(
            signal_id
        )


def test_invalid_signal_returns_422():
    response = client.post(
        "/api/v1/signals",
        json={
            "signal_id": "",
        },
    )

    assert response.status_code == 422


# ---------------------------------------------------------
# SIGNAL RETRIEVAL
# ---------------------------------------------------------

def test_get_signal_by_id():
    signal_id = _signal_id()

    try:
        create_response = client.post(
            "/api/v1/signals",
            json=_signal_payload(
                signal_id
            ),
        )

        assert (
            create_response.status_code
            == 201
        )

        response = client.get(
            f"/api/v1/signals/"
            f"{signal_id}"
        )

        assert response.status_code == 200

        body = response.json()

        assert (
            body["signal_id"]
            == signal_id
        )

        assert (
            body["agent"]
            == "kubernetes"
        )

        assert (
            body["environment"]
            == "production"
        )

    finally:
        _delete_signal(
            signal_id
        )


def test_unknown_signal_returns_404():
    response = client.get(
        "/api/v1/signals/does-not-exist"
    )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "Operational signal not found"
    )


def test_get_signals_returns_list():
    response = client.get(
        "/api/v1/signals"
    )

    assert response.status_code == 200
    assert isinstance(
        response.json(),
        list,
    )


def test_filter_signals_by_correlation_key():
    first_id = _signal_id()
    second_id = _signal_id()

    unique_key = (
        f"payments-{uuid4()}"
    )

    other_key = (
        f"orders-{uuid4()}"
    )

    try:
        first = client.post(
            "/api/v1/signals",
            json=_signal_payload(
                first_id,
                correlation_key=(
                    unique_key
                ),
            ),
        )

        second = client.post(
            "/api/v1/signals",
            json=_signal_payload(
                second_id,
                correlation_key=(
                    other_key
                ),
            ),
        )

        assert first.status_code == 201
        assert second.status_code == 201

        response = client.get(
            "/api/v1/signals",
            params={
                "correlation_key": (
                    unique_key
                ),
            },
        )

        assert response.status_code == 200

        body = response.json()

        assert len(body) == 1

        assert (
            body[0]["signal_id"]
            == first_id
        )

    finally:
        _delete_signal(
            first_id
        )

        _delete_signal(
            second_id
        )


# ---------------------------------------------------------
# INCIDENT SIGNALS
# ---------------------------------------------------------

def test_get_incident_signals():
    incident = _create_incident()

    first_id = _signal_id()
    second_id = _signal_id()

    try:
        first = client.post(
            "/api/v1/signals",
            json=_signal_payload(
                first_id,
                incident_id=(
                    incident.incident_id
                ),
            ),
        )

        second = client.post(
            "/api/v1/signals",
            json=_signal_payload(
                second_id,
                incident_id=(
                    incident.incident_id
                ),
            ),
        )

        assert first.status_code == 201
        assert second.status_code == 201

        response = client.get(
            f"/api/v1/incidents/"
            f"{incident.incident_id}"
            f"/signals"
        )

        assert response.status_code == 200

        body = response.json()

        signal_ids = {
            item["signal_id"]
            for item in body
        }

        assert first_id in signal_ids
        assert second_id in signal_ids

    finally:
        _delete_incident(
            incident.incident_id
        )


def test_unknown_incident_signals_returns_404():
    response = client.get(
        "/api/v1/incidents/"
        "does-not-exist/signals"
    )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "Incident not found"
    )


# ---------------------------------------------------------
# RCA API
# ---------------------------------------------------------

def test_get_incident_rca_history():
    incident = _create_incident()

    failure_signal_id = _signal_id()

    try:
        create_response = client.post(
            "/api/v1/signals",
            json={
                **_signal_payload(
                    failure_signal_id,
                    incident_id=(
                        incident.incident_id
                    ),
                ),
                "signal_type": "alert",
            },
        )

        assert (
            create_response.status_code
            == 201
        )

        database.save_rca_result(
            incident.incident_id,
            {
                "failure_signal_id": (
                    failure_signal_id
                ),
                "probable_root_cause": {
                    "signal_id": (
                        "deployment-1"
                    ),
                    "signal_type": (
                        "deployment"
                    ),
                    "score": 0.91,
                },
                "confidence": 0.91,
                "explanation": (
                    "Deployment likely "
                    "caused failure"
                ),
                "chain": [
                    {
                        "signal_id": (
                            "deployment-1"
                        ),
                        "signal_type": (
                            "deployment"
                        ),
                    },
                    {
                        "signal_id": (
                            failure_signal_id
                        ),
                        "signal_type": (
                            "alert"
                        ),
                    },
                ],
            },
        )

        response = client.get(
            f"/api/v1/incidents/"
            f"{incident.incident_id}"
            f"/rca"
        )

        assert response.status_code == 200

        body = response.json()

        assert len(body) == 1

        assert (
            body[0]["confidence"]
            == 0.91
        )

    finally:
        _delete_incident(
            incident.incident_id
        )


def test_get_latest_incident_rca():
    incident = _create_incident()

    failure_signal_id = _signal_id()

    try:
        create_response = client.post(
            "/api/v1/signals",
            json={
                **_signal_payload(
                    failure_signal_id,
                    incident_id=(
                        incident.incident_id
                    ),
                ),
                "signal_type": "alert",
            },
        )

        assert (
            create_response.status_code
            == 201
        )

        database.save_rca_result(
            incident.incident_id,
            {
                "failure_signal_id": (
                    failure_signal_id
                ),
                "probable_root_cause": {
                    "signal_id": (
                        "deployment-1"
                    ),
                    "signal_type": (
                        "deployment"
                    ),
                    "score": 0.96,
                },
                "confidence": 0.96,
                "explanation": (
                    "Deployment is the "
                    "probable root cause"
                ),
                "chain": [],
            },
        )

        response = client.get(
            f"/api/v1/incidents/"
            f"{incident.incident_id}"
            f"/rca/latest"
        )

        assert response.status_code == 200

        body = response.json()

        assert (
            body["confidence"]
            == 0.96
        )

        assert (
            body["failure_signal_id"]
            == failure_signal_id
        )

    finally:
        _delete_incident(
            incident.incident_id
        )


def test_latest_rca_without_analysis_returns_404():
    incident = _create_incident()

    try:
        response = client.get(
            f"/api/v1/incidents/"
            f"{incident.incident_id}"
            f"/rca/latest"
        )

        assert response.status_code == 404

        assert (
            response.json()["detail"]
            == (
                "Root-cause analysis "
                "not found"
            )
        )

    finally:
        _delete_incident(
            incident.incident_id
        )


def test_unknown_incident_rca_returns_404():
    response = client.get(
        "/api/v1/incidents/"
        "does-not-exist/rca"
    )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "Incident not found"
    )