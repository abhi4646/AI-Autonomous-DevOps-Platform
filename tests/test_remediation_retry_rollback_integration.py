from unittest.mock import Mock

from src.approval.approval_manager import (
    ApprovalManager,
)
from src.remediation.executor import (
    RemediationExecutor,
)


def _approved_remediation():
    manager = ApprovalManager()

    approval = manager.create_request(
        request="Restart unhealthy kubernetes workload",
        action="remediate",
        agent="kubernetes",
        risk="high",
        metadata={
            "health_status": "unhealthy",
            "health_score": 20,
            "reasons": [
                "Critical workload failure",
            ],
        },
    )

    manager.approve(
        approval["approval_id"],
        decided_by="human-admin",
        reason="Remediation approved",
    )

    return manager, approval


def _executor(manager):
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
        approval_manager=manager,
    )

    return executor, orchestrator


def test_recovery_requires_no_retry_or_rollback():
    manager, approval = _approved_remediation()

    executor, orchestrator = _executor(manager)

    result = executor.execute(
        approval["approval_id"],
        after_health={
            "status": "healthy",
            "score": 95,
            "reasons": [],
        },
        retry_count=0,
        rollback_available=True,
    )

    assert result["verification"]["recovered"] is True

    assert (
        result["escalation"]["status"]
        == "resolved"
    )

    assert (
        result["retry"]["status"]
        == "retry_not_required"
    )

    assert (
        result["rollback"]["status"]
        == "rollback_not_required"
    )

    orchestrator.route.assert_called_once()


def test_failed_recovery_offers_one_bounded_retry():
    manager, approval = _approved_remediation()

    executor, orchestrator = _executor(manager)

    result = executor.execute(
        approval["approval_id"],
        after_health={
            "status": "unhealthy",
            "score": 15,
            "reasons": [
                "Workload remains unhealthy",
            ],
        },
        retry_count=0,
        rollback_available=True,
    )

    assert result["verification"]["recovered"] is False

    assert (
        result["escalation"]["status"]
        == "escalated"
    )

    assert (
        result["retry"]["status"]
        == "retry_available"
    )

    assert result["retry"]["retry_allowed"] is True
    assert result["retry"]["requires_approval"] is True

    assert (
        result["rollback"]["status"]
        == "retry_first"
    )

    # Important: policy does not perform another execution.
    orchestrator.route.assert_called_once()


def test_exhausted_retry_recommends_rollback():
    manager, approval = _approved_remediation()

    executor, orchestrator = _executor(manager)

    result = executor.execute(
        approval["approval_id"],
        after_health={
            "status": "unhealthy",
            "score": 10,
            "reasons": [
                "Remediation retry did not recover service",
            ],
        },
        retry_count=1,
        rollback_available=True,
    )

    assert (
        result["retry"]["status"]
        == "retry_exhausted"
    )

    assert result["retry"]["retry_allowed"] is False

    assert (
        result["rollback"]["status"]
        == "rollback_recommended"
    )

    assert (
        result["rollback"]["rollback_recommended"]
        is True
    )

    assert (
        result["rollback"]["requires_approval"]
        is True
    )

    # Rollback is recommendation only.
    orchestrator.route.assert_called_once()


def test_exhausted_retry_without_rollback_escalates():
    manager, approval = _approved_remediation()

    executor, orchestrator = _executor(manager)

    result = executor.execute(
        approval["approval_id"],
        after_health={
            "status": "unhealthy",
            "score": 10,
            "reasons": [
                "Service remains unhealthy",
            ],
        },
        retry_count=1,
        rollback_available=False,
    )

    assert (
        result["retry"]["status"]
        == "retry_exhausted"
    )

    assert (
        result["rollback"]["status"]
        == "rollback_unavailable"
    )

    assert (
        result["rollback"]["requires_approval"]
        is True
    )

    orchestrator.route.assert_called_once()


def test_retry_decision_never_executes_second_attempt():
    manager, approval = _approved_remediation()

    executor, orchestrator = _executor(manager)

    result = executor.execute(
        approval["approval_id"],
        after_health={
            "status": "unhealthy",
            "score": 15,
            "reasons": [
                "Recovery not verified",
            ],
        },
        retry_count=0,
        rollback_available=True,
    )

    assert result["retry"]["retry_allowed"] is True

    # Eligibility does not equal authorization/execution.
    assert orchestrator.route.call_count == 1