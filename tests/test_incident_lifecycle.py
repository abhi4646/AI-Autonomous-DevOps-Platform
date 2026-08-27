import pytest

from src.incident.lifecycle import (
    IncidentLifecycle,
    InvalidIncidentTransition,
)
from src.incident.model import (
    Incident,
    IncidentSeverity,
    IncidentStatus,
)


def _incident():
    return Incident(
        title="Production service unhealthy",
        agent="kubernetes",
        severity=IncidentSeverity.HIGH,
    )


def test_normal_incident_lifecycle():
    incident = _incident()
    lifecycle = IncidentLifecycle()

    lifecycle.transition(
        incident,
        IncidentStatus.INVESTIGATING,
    )

    lifecycle.transition(
        incident,
        IncidentStatus.PENDING_APPROVAL,
    )

    lifecycle.transition(
        incident,
        IncidentStatus.REMEDIATING,
    )

    lifecycle.transition(
        incident,
        IncidentStatus.VERIFYING,
    )

    lifecycle.transition(
        incident,
        IncidentStatus.RESOLVED,
    )

    assert (
        incident.status
        == IncidentStatus.RESOLVED
    )
    assert incident.resolved_at is not None


def test_failed_verification_can_request_retry():
    incident = _incident()
    lifecycle = IncidentLifecycle()

    lifecycle.transition(
        incident,
        IncidentStatus.INVESTIGATING,
    )
    lifecycle.transition(
        incident,
        IncidentStatus.PENDING_APPROVAL,
    )
    lifecycle.transition(
        incident,
        IncidentStatus.REMEDIATING,
    )
    lifecycle.transition(
        incident,
        IncidentStatus.VERIFYING,
    )
    lifecycle.transition(
        incident,
        IncidentStatus.RETRY_PENDING,
    )

    assert (
        incident.status
        == IncidentStatus.RETRY_PENDING
    )


def test_retry_can_return_to_remediation():
    incident = _incident()
    lifecycle = IncidentLifecycle()

    incident.status = (
        IncidentStatus.RETRY_PENDING
    )

    lifecycle.transition(
        incident,
        IncidentStatus.REMEDIATING,
    )

    assert (
        incident.status
        == IncidentStatus.REMEDIATING
    )


def test_verification_can_request_rollback():
    incident = _incident()
    lifecycle = IncidentLifecycle()

    incident.status = IncidentStatus.VERIFYING

    lifecycle.transition(
        incident,
        IncidentStatus.ROLLBACK_PENDING,
    )

    assert (
        incident.status
        == IncidentStatus.ROLLBACK_PENDING
    )


def test_incident_can_escalate():
    incident = _incident()
    lifecycle = IncidentLifecycle()

    lifecycle.transition(
        incident,
        IncidentStatus.ESCALATED,
    )

    assert (
        incident.status
        == IncidentStatus.ESCALATED
    )


def test_invalid_transition_is_rejected():
    incident = _incident()
    lifecycle = IncidentLifecycle()

    with pytest.raises(
        InvalidIncidentTransition
    ):
        lifecycle.transition(
            incident,
            IncidentStatus.RESOLVED,
        )


def test_resolved_incident_is_terminal():
    incident = _incident()
    lifecycle = IncidentLifecycle()

    incident.status = IncidentStatus.RESOLVED

    assert (
        lifecycle.can_transition(
            incident,
            IncidentStatus.REMEDIATING,
        )
        is False
    )


def test_escalated_incident_is_terminal():
    incident = _incident()
    lifecycle = IncidentLifecycle()

    incident.status = IncidentStatus.ESCALATED

    assert (
        lifecycle.can_transition(
            incident,
            IncidentStatus.REMEDIATING,
        )
        is False
    )