import pytest

from src.approval.approval_manager import ApprovalManager


def test_create_approval_request():
    manager = ApprovalManager()

    approval = manager.create_request(
        request="Deploy application",
        action="deploy",
        agent="kubernetes",
        risk="high",
    )

    assert approval["status"] == "pending"
    assert approval["risk"] == "high"
    assert approval["agent"] == "kubernetes"
    assert approval["approval_id"]


def test_pending_request_cannot_execute():
    manager = ApprovalManager()

    approval = manager.create_request(
        request="Deploy application",
        action="deploy",
        agent="kubernetes",
        risk="high",
    )

    assert manager.can_execute(approval["approval_id"]) is False


def test_approved_request_can_execute():
    manager = ApprovalManager()

    approval = manager.create_request(
        request="Deploy application",
        action="deploy",
        agent="kubernetes",
        risk="high",
    )

    manager.approve(
        approval["approval_id"],
        decided_by="human-admin",
        reason="Deployment reviewed",
    )

    assert manager.can_execute(approval["approval_id"]) is True


def test_rejected_request_cannot_execute():
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
        reason="Unsafe production operation",
    )

    assert result["status"] == "rejected"
    assert manager.can_execute(approval["approval_id"]) is False


def test_decision_records_human_identity():
    manager = ApprovalManager()

    approval = manager.create_request(
        request="Restart Kubernetes deployment",
        action="restart",
        agent="kubernetes",
        risk="medium",
    )

    result = manager.approve(
        approval["approval_id"],
        decided_by="abhishek",
    )

    assert result["decided_by"] == "abhishek"
    assert result["decided_at"] is not None


def test_request_cannot_be_decided_twice():
    manager = ApprovalManager()

    approval = manager.create_request(
        request="Apply Terraform plan",
        action="apply",
        agent="terraform",
        risk="high",
    )

    manager.approve(
        approval["approval_id"],
        decided_by="human-admin",
    )

    with pytest.raises(ValueError):
        manager.reject(
            approval["approval_id"],
            decided_by="human-admin",
        )


def test_unknown_approval_raises_error():
    manager = ApprovalManager()

    with pytest.raises(KeyError):
        manager.approve(
            "does-not-exist",
            decided_by="human-admin",
        )


def test_get_pending_only_returns_pending_requests():
    manager = ApprovalManager()

    first = manager.create_request(
        "Deploy service",
        "deploy",
        "kubernetes",
        "high",
    )

    manager.create_request(
        "Apply infrastructure",
        "apply",
        "terraform",
        "high",
    )

    manager.approve(first["approval_id"], "human-admin")

    pending = manager.get_pending()

    assert len(pending) == 1
    assert pending[0]["agent"] == "terraform"