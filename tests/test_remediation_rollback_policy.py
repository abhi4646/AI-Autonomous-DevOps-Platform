from src.remediation.rollback_policy import (
    RemediationRollbackPolicy,
)


def test_recovered_system_needs_no_rollback():
    policy = RemediationRollbackPolicy()

    result = policy.evaluate(
        verification={
            "recovered": True,
        },
        retry={
            "retry_allowed": False,
        },
        rollback_available=True,
    )

    assert (
        result["status"]
        == "rollback_not_required"
    )
    assert (
        result["rollback_recommended"]
        is False
    )
    assert (
        result["requires_approval"]
        is False
    )


def test_retry_is_preferred_before_rollback():
    policy = RemediationRollbackPolicy()

    result = policy.evaluate(
        verification={
            "recovered": False,
        },
        retry={
            "retry_allowed": True,
        },
        rollback_available=True,
    )

    assert result["status"] == "retry_first"
    assert (
        result["rollback_recommended"]
        is False
    )


def test_rollback_recommended_after_retry_exhausted():
    policy = RemediationRollbackPolicy()

    result = policy.evaluate(
        verification={
            "recovered": False,
        },
        retry={
            "retry_allowed": False,
        },
        rollback_available=True,
    )

    assert (
        result["status"]
        == "rollback_recommended"
    )
    assert (
        result["rollback_recommended"]
        is True
    )
    assert (
        result["requires_approval"]
        is True
    )


def test_missing_rollback_strategy_escalates():
    policy = RemediationRollbackPolicy()

    result = policy.evaluate(
        verification={
            "recovered": False,
        },
        retry={
            "retry_allowed": False,
        },
        rollback_available=False,
    )

    assert (
        result["status"]
        == "rollback_unavailable"
    )
    assert (
        result["rollback_recommended"]
        is False
    )
    assert (
        result["requires_approval"]
        is True
    )