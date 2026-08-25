from unittest.mock import Mock

from src.approval.approval_manager import ApprovalManager
from src.remediation.executor import RemediationExecutor


def _create_approved_remediation(manager):
    approval = manager.create_request(
        request="Restart unhealthy kubernetes workload",
        action="remediate",
        agent="kubernetes",
        risk="high",
        metadata={
            "health_status": "unhealthy",
            "health_score": 25,
            "reasons": [
                "Critical failure rate",
            ],
        },
    )

    manager.approve(
        approval["approval_id"],
        decided_by="human-admin",
        reason="Remediation reviewed",
    )

    return approval


def test_successful_recovery_closes_workflow():
    manager = ApprovalManager()
    orchestrator = Mock()

    approval = _create_approved_remediation(manager)

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

    assert result["verification"]["recovered"] is True
    assert result["escalation"]["status"] == "resolved"
    assert result["escalation"]["action"] == "close"
    assert result["escalation"]["requires_human"] is False


def test_failed_recovery_escalates_to_human():
    manager = ApprovalManager()
    orchestrator = Mock()

    approval = _create_approved_remediation(manager)

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

    assert result["verification"]["recovered"] is False
    assert result["escalation"]["status"] == "escalated"
    assert result["escalation"]["action"] == "human_review"
    assert result["escalation"]["requires_human"] is True
    assert result["escalation"]["retry_allowed"] is False


def test_failed_verification_does_not_retry():
    manager = ApprovalManager()
    orchestrator = Mock()

    approval = _create_approved_remediation(manager)

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
            "score": 20,
            "reasons": [
                "System remains unhealthy",
            ],
        },
    )

    orchestrator.route.assert_called_once()

    assert result["escalation"]["retry_allowed"] is False
    assert result["escalation"]["requires_human"] is True