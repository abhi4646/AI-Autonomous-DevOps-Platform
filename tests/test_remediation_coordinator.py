from src.approval.approval_manager import (
    ApprovalManager,
)
from src.remediation.coordinator import (
    RemediationCoordinator,
)


def test_healthy_health_result_is_observed():
    coordinator = RemediationCoordinator()

    result = coordinator.coordinate(
        {
            "status": "healthy",
            "score": 95,
            "reasons": [],
        }
    )

    assert result["status"] == "observing"
    assert result["action"] == "observe"
    assert result["requires_approval"] is False


def test_degraded_health_result_is_recommended():
    coordinator = RemediationCoordinator()

    result = coordinator.coordinate(
        {
            "status": "degraded",
            "score": 65,
            "reasons": [
                "Elevated failure rate",
            ],
        }
    )

    assert result["status"] == "recommendation"
    assert result["action"] == "recommend"
    assert result["requires_approval"] is False


def test_unhealthy_without_manager_requires_approval():
    coordinator = RemediationCoordinator()

    result = coordinator.coordinate(
        {
            "status": "unhealthy",
            "score": 30,
            "reasons": [
                "Critical execution failures",
            ],
        }
    )

    assert result["status"] == "approval_required"
    assert result["action"] == "remediate"
    assert result["requires_approval"] is True
    assert result["approval_id"] is None


def test_unhealthy_creates_pending_approval():
    approval_manager = ApprovalManager()

    coordinator = RemediationCoordinator(
        approval_manager=approval_manager,
    )

    result = coordinator.coordinate(
        {
            "status": "unhealthy",
            "score": 25,
            "reasons": [
                "Critical execution failures",
            ],
        },
        agent="kubernetes",
    )

    assert result["status"] == "pending_approval"
    assert result["requires_approval"] is True
    assert result["approval_status"] == "pending"
    assert result["approval_id"] is not None

    approval = approval_manager.get_request(
        result["approval_id"]
    )

    assert approval is not None
    assert approval["status"] == "pending"
    assert approval["agent"] == "kubernetes"
    assert approval["risk"] == "high"
    assert approval["action"] == "remediate"


def test_healthy_does_not_create_approval():
    approval_manager = ApprovalManager()

    coordinator = RemediationCoordinator(
        approval_manager=approval_manager,
    )

    result = coordinator.coordinate(
        {
            "status": "healthy",
            "score": 98,
            "reasons": [],
        },
        agent="kubernetes",
    )

    assert result["status"] == "observing"
    assert approval_manager.get_pending() == []


def test_coordinator_preserves_health_context():
    coordinator = RemediationCoordinator()

    result = coordinator.coordinate(
        {
            "status": "degraded",
            "score": 55,
            "reasons": [
                "High timeout rate",
                "Agent reliability degraded",
            ],
        }
    )

    assert result["health_status"] == "degraded"
    assert result["health_score"] == 55

    assert result["reasons"] == [
        "High timeout rate",
        "Agent reliability degraded",
    ]