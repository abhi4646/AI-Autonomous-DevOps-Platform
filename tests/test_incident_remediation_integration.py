from unittest.mock import Mock

from src.approval.approval_manager import (
    ApprovalManager,
)
from src.incident.manager import IncidentManager
from src.incident.model import IncidentStatus
from src.persistence.database import Database
from src.remediation.coordinator import (
    RemediationCoordinator,
)
from src.remediation.executor import (
    RemediationExecutor,
)


def _setup():
    database = Database(":memory:")

    approval_manager = ApprovalManager(
        database=database
    )

    incident_manager = IncidentManager(
        database=database
    )

    coordinator = RemediationCoordinator(
        approval_manager=approval_manager,
        incident_manager=incident_manager,
    )

    orchestrator = Mock()

    orchestrator.route.return_value = {
        "status": "routed",
        "agent": "kubernetes",
        "result": {
            "status": "success",
        },
    }

    executor = RemediationExecutor(
        orchestrator=orchestrator,
        approval_manager=approval_manager,
        incident_manager=incident_manager,
    )

    return (
        database,
        approval_manager,
        incident_manager,
        coordinator,
        executor,
        orchestrator,
    )


def _unhealthy_health():
    return {
        "status": "unhealthy",
        "score": 20,
        "reasons": [
            "Critical workload failure",
        ],
    }


def test_coordinator_creates_incident_and_approval():
    (
        database,
        approval_manager,
        incident_manager,
        coordinator,
        executor,
        orchestrator,
    ) = _setup()

    result = coordinator.coordinate(
        _unhealthy_health(),
        agent="kubernetes",
        rollback_available=True,
    )

    assert result["status"] == "pending_approval"
    assert result["approval_id"] is not None
    assert result["incident_id"] is not None

    incident = incident_manager.get(
        result["incident_id"]
    )

    assert incident is not None
    assert (
        incident.status
        == IncidentStatus.PENDING_APPROVAL
    )

    assert (
        incident.approval_id
        == result["approval_id"]
    )

    database.close()


def test_successful_remediation_resolves_incident():
    (
        database,
        approval_manager,
        incident_manager,
        coordinator,
        executor,
        orchestrator,
    ) = _setup()

    workflow = coordinator.coordinate(
        _unhealthy_health(),
        agent="kubernetes",
        rollback_available=True,
    )

    approval_manager.approve(
        workflow["approval_id"],
        decided_by="human-admin",
        reason="Approved remediation",
    )

    result = executor.execute(
        workflow["approval_id"],
        after_health={
            "status": "healthy",
            "score": 95,
            "reasons": [],
        },
        retry_count=0,
        rollback_available=True,
    )

    incident = incident_manager.get(
        workflow["incident_id"]
    )

    assert result["verification"]["recovered"] is True

    assert (
        incident.status
        == IncidentStatus.RESOLVED
    )

    assert incident.resolved_at is not None

    orchestrator.route.assert_called_once()

    database.close()


def test_failed_remediation_enters_retry_pending():
    (
        database,
        approval_manager,
        incident_manager,
        coordinator,
        executor,
        orchestrator,
    ) = _setup()

    workflow = coordinator.coordinate(
        _unhealthy_health(),
        agent="kubernetes",
        rollback_available=True,
    )

    approval_manager.approve(
        workflow["approval_id"],
        decided_by="human-admin",
    )

    result = executor.execute(
        workflow["approval_id"],
        after_health={
            "status": "unhealthy",
            "score": 10,
            "reasons": [
                "Workload remains unhealthy",
            ],
        },
        retry_count=0,
        rollback_available=True,
    )

    incident = incident_manager.get(
        workflow["incident_id"]
    )

    assert result["retry"]["retry_allowed"] is True

    assert (
        incident.status
        == IncidentStatus.RETRY_PENDING
    )

    assert incident.retry_count == 0

    orchestrator.route.assert_called_once()

    database.close()


def test_retry_exhaustion_enters_rollback_pending():
    (
        database,
        approval_manager,
        incident_manager,
        coordinator,
        executor,
        orchestrator,
    ) = _setup()

    workflow = coordinator.coordinate(
        _unhealthy_health(),
        agent="kubernetes",
        rollback_available=True,
    )

    approval_manager.approve(
        workflow["approval_id"],
        decided_by="human-admin",
    )

    result = executor.execute(
        workflow["approval_id"],
        after_health={
            "status": "unhealthy",
            "score": 10,
            "reasons": [
                "Recovery failed",
            ],
        },
        retry_count=1,
        rollback_available=True,
    )

    incident = incident_manager.get(
        workflow["incident_id"]
    )

    assert (
        result["retry"]["status"]
        == "retry_exhausted"
    )

    assert (
        result["rollback"][
            "rollback_recommended"
        ]
        is True
    )

    assert (
        incident.status
        == IncidentStatus.ROLLBACK_PENDING
    )

    assert incident.retry_count == 1

    database.close()


def test_failed_recovery_without_rollback_escalates():
    (
        database,
        approval_manager,
        incident_manager,
        coordinator,
        executor,
        orchestrator,
    ) = _setup()

    workflow = coordinator.coordinate(
        _unhealthy_health(),
        agent="kubernetes",
        rollback_available=False,
    )

    approval_manager.approve(
        workflow["approval_id"],
        decided_by="human-admin",
    )

    result = executor.execute(
        workflow["approval_id"],
        after_health={
            "status": "unhealthy",
            "score": 5,
            "reasons": [
                "Service remains unhealthy",
            ],
        },
        retry_count=1,
        rollback_available=False,
    )

    incident = incident_manager.get(
        workflow["incident_id"]
    )

    assert (
        result["rollback"]["status"]
        == "rollback_unavailable"
    )

    assert (
        incident.status
        == IncidentStatus.ESCALATED
    )

    database.close()