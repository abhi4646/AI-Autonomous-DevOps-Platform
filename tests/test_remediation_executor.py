from unittest.mock import Mock

from src.approval.approval_manager import ApprovalManager
from src.remediation.executor import RemediationExecutor


def _create_approval(manager):
    return manager.create_request(
        request="Restart unhealthy kubernetes workload",
        action="remediate",
        agent="kubernetes",
        risk="high",
        metadata={
            "health_status": "unhealthy",
            "health_score": 25,
        },
    )


def test_unknown_approval_never_executes():
    manager = ApprovalManager()
    orchestrator = Mock()

    executor = RemediationExecutor(
        orchestrator=orchestrator,
        approval_manager=manager,
    )

    result = executor.execute(
        "does-not-exist"
    )

    assert result["status"] == "approval_not_found"

    orchestrator.route.assert_not_called()


def test_pending_approval_never_executes():
    manager = ApprovalManager()
    orchestrator = Mock()

    approval = _create_approval(manager)

    executor = RemediationExecutor(
        orchestrator=orchestrator,
        approval_manager=manager,
    )

    result = executor.execute(
        approval["approval_id"]
    )

    assert result["status"] == "pending_approval"

    orchestrator.route.assert_not_called()


def test_rejected_approval_never_executes():
    manager = ApprovalManager()
    orchestrator = Mock()

    approval = _create_approval(manager)

    manager.reject(
        approval["approval_id"],
        decided_by="human-admin",
        reason="Unsafe remediation",
    )

    executor = RemediationExecutor(
        orchestrator=orchestrator,
        approval_manager=manager,
    )

    result = executor.execute(
        approval["approval_id"]
    )

    assert result["status"] == "rejected"

    orchestrator.route.assert_not_called()


def test_approved_remediation_delegates_to_orchestrator():
    manager = ApprovalManager()
    orchestrator = Mock()

    approval = _create_approval(manager)

    manager.approve(
        approval["approval_id"],
        decided_by="human-admin",
        reason="Remediation reviewed",
    )

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

    result = executor.execute(
        approval["approval_id"]
    )

    assert result["status"] == "executed"

    orchestrator.route.assert_called_once_with(
        request=approval["request"],
        approval_id=approval["approval_id"],
    )

    assert result["result"]["status"] == "routed"


def test_approved_remediation_can_verify_recovery():
    manager = ApprovalManager()
    orchestrator = Mock()

    approval = _create_approval(manager)

    manager.approve(
        approval["approval_id"],
        decided_by="human-admin",
        reason="Remediation reviewed",
    )

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

    result = executor.execute(
        approval["approval_id"],
        after_health={
            "status": "healthy",
            "score": 95,
            "reasons": [],
        },
    )

    assert result["status"] == "executed"

    assert (
        result["verification"]["verified"]
        is True
    )

    assert (
        result["verification"]["recovered"]
        is True
    )

    assert (
        result["verification"]["outcome"]
        == "recovered"
    )

    assert (
        result["verification"]["before_score"]
        == 25
    )

    assert (
        result["verification"]["after_score"]
        == 95
    )


def test_approved_remediation_detects_failed_recovery():
    manager = ApprovalManager()
    orchestrator = Mock()

    approval = _create_approval(manager)

    manager.approve(
        approval["approval_id"],
        decided_by="human-admin",
        reason="Remediation reviewed",
    )

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

    result = executor.execute(
        approval["approval_id"],
        after_health={
            "status": "unhealthy",
            "score": 15,
            "reasons": [
                "Failure rate remains critical",
            ],
        },
    )

    assert result["status"] == "executed"

    assert (
        result["verification"]["recovered"]
        is False
    )

    assert (
        result["verification"]["outcome"]
        == "failed"
    )

    assert (
        result["verification"]["score_change"]
        == -10
    )


def test_execution_without_after_health_remains_compatible():
    manager = ApprovalManager()
    orchestrator = Mock()

    approval = _create_approval(manager)

    manager.approve(
        approval["approval_id"],
        decided_by="human-admin",
        reason="Remediation reviewed",
    )

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

    result = executor.execute(
        approval["approval_id"]
    )

    assert result["status"] == "executed"
    assert "verification" not in result