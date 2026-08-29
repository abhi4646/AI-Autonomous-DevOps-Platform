from uuid import uuid4

from fastapi.testclient import TestClient

from src.api.app import app
from src.api.routes import (
    database,
    incident_manager,
)
from src.correlation.signal import (
    OperationalSignal,
    SignalSeverity,
    SignalType,
)
from src.incident.model import (
    IncidentSeverity,
)


client = TestClient(app)


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def _create_incident():
    return incident_manager.create(
        title="Payments production outage",
        agent="kubernetes",
        severity=IncidentSeverity.CRITICAL,
        health_snapshot={
            "status": "unhealthy",
            "score": 10,
            "reasons": [
                "Payments API unavailable",
            ],
        },
        rollback_available=True,
        metadata={
            "environment": "production",
        },
    )


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
# INCIDENT MANAGER SIGNAL INTEGRATION
# ---------------------------------------------------------

def test_incident_manager_attaches_signal():
    incident = _create_incident()

    try:
        signal = OperationalSignal(
            signal_type=SignalType.DEPLOYMENT,
            source="github-actions",
            resource="payments-api",
            severity=SignalSeverity.HIGH,
            message="Payments API v2 deployed",
            environment="production",
            correlation_key="payments-production",
            occurred_at=(
                "2026-08-27T10:00:00+00:00"
            ),
        )

        stored = incident_manager.add_signal(
            incident.incident_id,
            signal,
        )

        assert (
            stored.incident_id
            == incident.incident_id
        )

        signals = incident_manager.get_signals(
            incident.incident_id
        )

        assert len(signals) == 1

        assert (
            signals[0].signal_id
            == signal.signal_id
        )

    finally:
        _delete_incident(
            incident.incident_id
        )


# ---------------------------------------------------------
# RCA + PERSISTENCE INTEGRATION
# ---------------------------------------------------------

def test_incident_manager_runs_and_persists_rca():
    incident = _create_incident()

    try:
        deployment = OperationalSignal(
            signal_type=SignalType.DEPLOYMENT,
            source="github-actions",
            resource="payments-api",
            severity=SignalSeverity.HIGH,
            message="Payments API v2 deployed",
            environment="production",
            correlation_key="payments-production",
            occurred_at=(
                "2026-08-27T10:00:00+00:00"
            ),
        )

        failure = OperationalSignal(
            signal_type=SignalType.ALERT,
            source="monitoring",
            resource="payments-api",
            severity=SignalSeverity.CRITICAL,
            message="Payments API unavailable",
            environment="production",
            correlation_key="payments-production",
            occurred_at=(
                "2026-08-27T10:05:00+00:00"
            ),
        )

        incident_manager.add_signal(
            incident.incident_id,
            deployment,
        )

        incident_manager.add_signal(
            incident.incident_id,
            failure,
        )

        result = (
            incident_manager
            .analyze_root_cause(
                incident.incident_id,
                failure.signal_id,
            )
        )

        assert result["rca_id"] > 0

        assert (
            result["incident_id"]
            == incident.incident_id
        )

        assert (
            result["failure_signal_id"]
            == failure.signal_id
        )

        root_cause = result[
            "probable_root_cause"
        ]

        assert root_cause is not None

        assert (
            root_cause["signal_id"]
            == deployment.signal_id
        )

        assert (
            root_cause["signal_type"]
            == "deployment"
        )

        assert result["confidence"] > 0.0

        latest = (
            database
            .get_latest_rca_result(
                incident.incident_id
            )
        )

        assert latest is not None

        assert (
            latest["failure_signal_id"]
            == failure.signal_id
        )

    finally:
        _delete_incident(
            incident.incident_id
        )


# ---------------------------------------------------------
# COMPLETE API END-TO-END FLOW
# ---------------------------------------------------------

def test_incident_rca_end_to_end_api():
    incident = _create_incident()

    correlation_key = (
        f"payments-{uuid4()}"
    )

    deployment_id = (
        f"deployment-{uuid4()}"
    )

    failure_id = (
        f"failure-{uuid4()}"
    )

    try:
        deployment_response = client.post(
            "/api/v1/signals",
            json={
                "signal_id": deployment_id,
                "signal_type": "deployment",
                "source": "github-actions",
                "resource": "payments-api",
                "severity": "high",
                "message": (
                    "Payments API v2 deployed"
                ),
                "agent": "kubernetes",
                "environment": "production",
                "incident_id": (
                    incident.incident_id
                ),
                "correlation_key": (
                    correlation_key
                ),
                "occurred_at": (
                    "2026-08-27"
                    "T10:00:00+00:00"
                ),
                "metadata": {
                    "version": "v2",
                },
            },
        )

        assert (
            deployment_response.status_code
            == 201
        )

        failure_response = client.post(
            "/api/v1/signals",
            json={
                "signal_id": failure_id,
                "signal_type": "alert",
                "source": "monitoring",
                "resource": "payments-api",
                "severity": "critical",
                "message": (
                    "Payments API unavailable"
                ),
                "agent": "monitoring",
                "environment": "production",
                "incident_id": (
                    incident.incident_id
                ),
                "correlation_key": (
                    correlation_key
                ),
                "occurred_at": (
                    "2026-08-27"
                    "T10:05:00+00:00"
                ),
                "metadata": {
                    "http_status": 503,
                },
            },
        )

        assert (
            failure_response.status_code
            == 201
        )

        analysis_response = client.post(
            (
                f"/api/v1/incidents/"
                f"{incident.incident_id}"
                f"/rca/analyze"
            ),
            params={
                "failure_signal_id": failure_id,
            },
        )

        assert (
            analysis_response.status_code
            == 200
        )

        analysis = analysis_response.json()

        assert (
            analysis["failure_signal_id"]
            == failure_id
        )

        assert (
            analysis[
                "probable_root_cause"
            ]["signal_id"]
            == deployment_id
        )

        assert (
            analysis[
                "probable_root_cause"
            ]["signal_type"]
            == "deployment"
        )

        assert (
            analysis["confidence"]
            > 0.0
        )

        assert (
            analysis["chain_length"]
            == 2
        )

        latest_response = client.get(
            (
                f"/api/v1/incidents/"
                f"{incident.incident_id}"
                f"/rca/latest"
            )
        )

        assert (
            latest_response.status_code
            == 200
        )

        latest = latest_response.json()

        assert (
            latest["failure_signal_id"]
            == failure_id
        )

        assert (
            latest[
                "probable_root_cause"
            ]["signal_id"]
            == deployment_id
        )

        history_response = client.get(
            (
                f"/api/v1/incidents/"
                f"{incident.incident_id}"
                f"/rca"
            )
        )

        assert (
            history_response.status_code
            == 200
        )

        history = history_response.json()

        assert len(history) == 1

    finally:
        _delete_incident(
            incident.incident_id
        )


# ---------------------------------------------------------
# CROSS-INCIDENT SAFETY
# ---------------------------------------------------------

def test_rca_rejects_signal_from_other_incident():
    first_incident = _create_incident()
    second_incident = _create_incident()

    failure = OperationalSignal(
        signal_type=SignalType.ALERT,
        source="monitoring",
        resource="payments-api",
        severity=SignalSeverity.CRITICAL,
        message="Payments API unavailable",
        environment="production",
        correlation_key="payments-production",
        occurred_at=(
            "2026-08-27T10:05:00+00:00"
        ),
    )

    try:
        incident_manager.add_signal(
            second_incident.incident_id,
            failure,
        )

        response = client.post(
            (
                f"/api/v1/incidents/"
                f"{first_incident.incident_id}"
                f"/rca/analyze"
            ),
            params={
                "failure_signal_id": (
                    failure.signal_id
                ),
            },
        )

        assert response.status_code == 409

        assert (
            response.json()["detail"]
            == (
                "Failure signal does not "
                "belong to the incident"
            )
        )

    finally:
        _delete_incident(
            first_incident.incident_id
        )

        _delete_incident(
            second_incident.incident_id
        )