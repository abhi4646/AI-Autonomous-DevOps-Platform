from src.remediation.escalation import (
    RemediationEscalationPolicy,
)


def test_recovered_remediation_is_resolved():
    policy = RemediationEscalationPolicy()

    result = policy.evaluate(
        {
            "recovered": True,
            "outcome": "recovered",
            "after_status": "healthy",
            "score_change": 60,
        }
    )

    assert result["status"] == "resolved"
    assert result["action"] == "close"
    assert result["escalated"] is False
    assert result["retry_allowed"] is False
    assert result["requires_human"] is False


def test_improved_remediation_is_resolved():
    policy = RemediationEscalationPolicy()

    result = policy.evaluate(
        {
            "recovered": True,
            "outcome": "improved",
            "after_status": "degraded",
            "score_change": 25,
        }
    )

    assert result["status"] == "resolved"
    assert result["escalated"] is False
    assert result["requires_human"] is False


def test_failed_remediation_is_escalated():
    policy = RemediationEscalationPolicy()

    result = policy.evaluate(
        {
            "recovered": False,
            "outcome": "failed",
            "after_status": "unhealthy",
            "score_change": -20,
        }
    )

    assert result["status"] == "escalated"
    assert result["action"] == "human_review"
    assert result["escalated"] is True
    assert result["retry_allowed"] is False
    assert result["requires_human"] is True


def test_unchanged_remediation_is_escalated():
    policy = RemediationEscalationPolicy()

    result = policy.evaluate(
        {
            "recovered": False,
            "outcome": "unchanged",
            "after_status": "unhealthy",
            "score_change": 0,
        }
    )

    assert result["status"] == "escalated"
    assert result["action"] == "human_review"
    assert result["retry_allowed"] is False
    assert result["requires_human"] is True


def test_unknown_verification_is_escalated_safely():
    policy = RemediationEscalationPolicy()

    result = policy.evaluate({})

    assert result["status"] == "verification_inconclusive"
    assert result["action"] == "human_review"
    assert result["escalated"] is True
    assert result["retry_allowed"] is False
    assert result["requires_human"] is True