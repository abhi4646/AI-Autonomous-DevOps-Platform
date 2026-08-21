from src.approval.approval_manager import ApprovalManager
from src.orchestrator.orchestrator import Orchestrator


def test_high_risk_request_requires_human_approval():
    orchestrator = Orchestrator()

    result = orchestrator.route("Deploy application to production")

    assert result["status"] == "pending_approval"
    assert "approval_id" in result


def test_pending_request_does_not_execute():
    orchestrator = Orchestrator()

    result = orchestrator.route("Deploy application to production")

    assert result["status"] == "pending_approval"


def test_approval_manager_can_approve_request():
    manager = ApprovalManager()

    approval = manager.create_request(
        request="Deploy application",
        action="deploy",
        agent="kubernetes",
        risk="high",
    )

    result = manager.approve(
        approval["approval_id"],
        decided_by="human-admin",
        reason="Deployment reviewed and approved",
    )

    assert result["status"] == "approved"
    assert manager.can_execute(approval["approval_id"]) is True


def test_approval_manager_can_reject_request():
    manager = ApprovalManager()

    approval = manager.create_request(
        request="Destroy production infrastructure",
        action="destroy",
        agent="terraform",
        risk="critical",
    )

    result = manager.reject(
        approval["approval_id"],
        decided_by="human-admin",
        reason="Operation considered unsafe",
    )

    assert result["status"] == "rejected"
    assert manager.can_execute(approval["approval_id"]) is False


def test_approval_records_human_decision():
    manager = ApprovalManager()

    approval = manager.create_request(
        request="Apply Terraform infrastructure",
        action="apply",
        agent="terraform",
        risk="high",
    )

    result = manager.approve(
        approval["approval_id"],
        decided_by="abhishek",
        reason="Infrastructure change reviewed",
    )

    assert result["decided_by"] == "abhishek"
    assert result["decided_at"] is not None