import pytest

from src.incident.lifecycle import (
    InvalidIncidentTransition,
)
from src.incident.manager import IncidentManager
from src.incident.model import (
    IncidentSeverity,
    IncidentStatus,
)
from src.persistence.database import Database


def _manager():
    database = Database(":memory:")

    return (
        IncidentManager(database),
        database,
    )


def test_manager_creates_persistent_incident():
    manager, database = _manager()

    incident = manager.create(
        title="Kubernetes failure",
        agent="kubernetes",
        severity=IncidentSeverity.CRITICAL,
        health_snapshot={
            "status": "unhealthy",
            "score": 20,
        },
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

    database.close()


def test_manager_retrieves_incident():
    manager, database = _manager()

    created = manager.create(
        title="Docker failure",
        agent="docker",
        severity=IncidentSeverity.HIGH,
    )

    restored = manager.get(
        created.incident_id
    )

    assert restored is not None

    assert (
        restored.incident_id
        == created.incident_id
    )

    assert (
        restored.severity
        == IncidentSeverity.HIGH
    )

    database.close()


def test_manager_returns_none_for_unknown_incident():
    manager, database = _manager()

    assert (
        manager.get("missing")
        is None
    )

    database.close()


def test_manager_persists_transition():
    manager, database = _manager()

    incident = manager.create(
        title="Terraform failure",
        agent="terraform",
        severity=IncidentSeverity.HIGH,
    )

    updated = manager.transition(
        incident.incident_id,
        IncidentStatus.INVESTIGATING,
    )

    assert (
        updated.status
        == IncidentStatus.INVESTIGATING
    )

    stored = database.get_incident(
        incident.incident_id
    )

    assert (
        stored["status"]
        == "investigating"
    )

    database.close()


def test_manager_rejects_invalid_transition():
    manager, database = _manager()

    incident = manager.create(
        title="Failure",
        agent="kubernetes",
        severity=IncidentSeverity.HIGH,
    )

    with pytest.raises(
        InvalidIncidentTransition
    ):
        manager.transition(
            incident.incident_id,
            IncidentStatus.RESOLVED,
        )

    database.close()


def test_manager_associates_approval():
    manager, database = _manager()

    incident = manager.create(
        title="Failure",
        agent="kubernetes",
        severity=IncidentSeverity.HIGH,
    )

    manager.set_approval(
        incident.incident_id,
        "approval-123",
    )

    stored = database.get_incident(
        incident.incident_id
    )

    assert (
        stored["approval_id"]
        == "approval-123"
    )

    database.close()


def test_manager_updates_retry_count():
    manager, database = _manager()

    incident = manager.create(
        title="Failure",
        agent="kubernetes",
        severity=IncidentSeverity.HIGH,
    )

    manager.set_retry_count(
        incident.incident_id,
        1,
    )

    stored = database.get_incident(
        incident.incident_id
    )

    assert stored["retry_count"] == 1

    database.close()


def test_manager_rejects_negative_retry_count():
    manager, database = _manager()

    incident = manager.create(
        title="Failure",
        agent="kubernetes",
        severity=IncidentSeverity.HIGH,
    )

    with pytest.raises(ValueError):
        manager.set_retry_count(
            incident.incident_id,
            -1,
        )

    database.close()


def test_manager_updates_rollback_availability():
    manager, database = _manager()

    incident = manager.create(
        title="Failure",
        agent="kubernetes",
        severity=IncidentSeverity.HIGH,
    )

    manager.set_rollback_available(
        incident.incident_id,
        True,
    )

    stored = database.get_incident(
        incident.incident_id
    )

    assert (
        stored["rollback_available"]
        is True
    )

    database.close()


def test_manager_unknown_transition_raises():
    manager, database = _manager()

    with pytest.raises(KeyError):
        manager.transition(
            "missing",
            IncidentStatus.INVESTIGATING,
        )

    database.close()