from src.approval.approval_manager import ApprovalManager
from src.audit.audit_logger import AuditLogger
from src.persistence.database import Database


def test_approval_manager_persists_request(tmp_path):
    database_path = tmp_path / "platform.db"

    db1 = Database(str(database_path))
    manager1 = ApprovalManager(database=db1)

    approval = manager1.create_request(
        request="Deploy application to production",
        action="review",
        agent="kubernetes",
        risk="high",
    )

    approval_id = approval["approval_id"]

    db1.close()

    db2 = Database(str(database_path))
    manager2 = ApprovalManager(database=db2)

    restored = manager2.get_request(approval_id)

    assert restored is not None
    assert restored["approval_id"] == approval_id
    assert restored["request"] == "Deploy application to production"
    assert restored["agent"] == "kubernetes"
    assert restored["status"] == "pending"
    assert restored["action"] == "review"

    db2.close()


def test_approval_decision_persists(tmp_path):
    database_path = tmp_path / "platform.db"

    db1 = Database(str(database_path))
    manager1 = ApprovalManager(database=db1)

    approval = manager1.create_request(
        request="Apply Terraform plan",
        action="review",
        agent="terraform",
        risk="high",
    )

    approval_id = approval["approval_id"]

    manager1.approve(
        approval_id,
        decided_by="human-admin",
        reason="Infrastructure reviewed",
    )

    db1.close()

    db2 = Database(str(database_path))
    manager2 = ApprovalManager(database=db2)

    restored = manager2.get_request(approval_id)

    assert restored is not None
    assert restored["status"] == "approved"
    assert restored["decided_by"] == "human-admin"
    assert restored["decided_at"] is not None
    assert restored["reason"] == "Infrastructure reviewed"
    assert manager2.can_execute(approval_id) is True

    db2.close()


def test_remediation_context_survives_restart(tmp_path):
    database_path = tmp_path / "platform.db"

    db1 = Database(str(database_path))
    manager1 = ApprovalManager(database=db1)

    approval = manager1.create_request(
        request=(
            "Remediate unhealthy agent 'kubernetes' "
            "with health score 20"
        ),
        action="remediate",
        agent="kubernetes",
        risk="high",
        metadata={
            "health_status": "unhealthy",
            "health_score": 20,
            "reasons": [
                "Critical execution failures",
            ],
            "remediation_action": "remediate",
        },
    )

    approval_id = approval["approval_id"]

    manager1.approve(
        approval_id,
        decided_by="human-admin",
        reason="Approved after incident review",
    )

    db1.close()

    db2 = Database(str(database_path))
    manager2 = ApprovalManager(database=db2)

    restored = manager2.get_request(approval_id)

    assert restored is not None
    assert restored["action"] == "remediate"
    assert restored["status"] == "approved"
    assert restored["reason"] == "Approved after incident review"

    assert restored["metadata"]["health_status"] == "unhealthy"
    assert restored["metadata"]["health_score"] == 20
    assert (
        restored["metadata"]["remediation_action"]
        == "remediate"
    )

    assert manager2.can_execute(approval_id) is True

    db2.close()


def test_audit_logger_persists_event(tmp_path):
    database_path = tmp_path / "platform.db"

    db1 = Database(str(database_path))
    logger = AuditLogger(database=db1)

    logger.log(
        request="Deploy application",
        action="execute",
        agent="kubernetes",
        allowed=True,
        risk="low",
        reason="Deployment completed",
        metadata={
            "environment": "production",
        },
    )

    db1.close()

    db2 = Database(str(database_path))

    events = db2.get_audit_events()

    assert len(events) == 1

    event = events[0]

    assert event["event_type"] == "execute"
    assert event["message"] == "Deployment completed"
    assert event["metadata"]["agent"] == "kubernetes"
    assert event["metadata"]["allowed"] is True

    db2.close()