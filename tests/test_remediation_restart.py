from unittest.mock import Mock

from src.approval.approval_manager import ApprovalManager
from src.persistence.database import Database
from src.remediation.executor import RemediationExecutor


def test_approved_remediation_resumes_after_restart(
    tmp_path,
):
    database_path = tmp_path / "platform.db"

    # ---------------------------------------------------------
    # PROCESS 1:
    # Create and approve remediation
    # ---------------------------------------------------------

    db1 = Database(str(database_path))

    manager1 = ApprovalManager(
        database=db1
    )

    approval = manager1.create_request(
        request=(
            "Restart unhealthy kubernetes workload"
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
        reason="Incident reviewed and approved",
    )

    db1.close()

    # ---------------------------------------------------------
    # PROCESS 2:
    # Simulate application restart
    # ---------------------------------------------------------

    db2 = Database(str(database_path))

    manager2 = ApprovalManager(
        database=db2
    )

    restored = manager2.get_request(
        approval_id
    )

    assert restored is not None
    assert restored["status"] == "approved"
    assert restored["action"] == "remediate"
    assert restored["agent"] == "kubernetes"

    assert (
        restored["metadata"]["health_status"]
        == "unhealthy"
    )

    assert (
        restored["metadata"]["health_score"]
        == 20
    )

    assert (
        restored["reason"]
        == "Incident reviewed and approved"
    )

    # ---------------------------------------------------------
    # CONTROLLED EXECUTION AFTER RESTART
    # ---------------------------------------------------------

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
        approval_manager=manager2,
    )

    result = executor.execute(
        approval_id
    )

    assert result["status"] == "executed"

    orchestrator.route.assert_called_once_with(
        request=(
            "Restart unhealthy kubernetes workload"
        ),
        approval_id=approval_id,
    )

    assert (
        result["result"]["status"]
        == "routed"
    )

    db2.close()