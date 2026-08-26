import pytest

from src.remediation.retry_policy import (
    RemediationRetryPolicy,
)


def _escalated():
    return {
        "status": "escalated",
        "escalated": True,
    }


def test_retry_available_after_escalation():
    policy = RemediationRetryPolicy(
        max_retries=1
    )

    result = policy.evaluate(
        _escalated(),
        retry_count=0,
    )

    assert result["status"] == "retry_available"
    assert result["retry_allowed"] is True
    assert result["next_retry_count"] == 1
    assert result["requires_approval"] is True


def test_retry_exhausted_after_limit():
    policy = RemediationRetryPolicy(
        max_retries=1
    )

    result = policy.evaluate(
        _escalated(),
        retry_count=1,
    )

    assert result["status"] == "retry_exhausted"
    assert result["retry_allowed"] is False
    assert result["requires_approval"] is True


def test_retry_not_needed_without_escalation():
    policy = RemediationRetryPolicy()

    result = policy.evaluate(
        {
            "escalated": False,
        },
        retry_count=0,
    )

    assert result["status"] == "retry_not_required"
    assert result["retry_allowed"] is False
    assert result["requires_approval"] is False


def test_zero_retry_policy_disables_retry():
    policy = RemediationRetryPolicy(
        max_retries=0
    )

    result = policy.evaluate(
        _escalated(),
        retry_count=0,
    )

    assert result["status"] == "retry_exhausted"
    assert result["retry_allowed"] is False


def test_negative_max_retries_rejected():
    with pytest.raises(ValueError):
        RemediationRetryPolicy(
            max_retries=-1
        )


def test_negative_retry_count_rejected():
    policy = RemediationRetryPolicy()

    with pytest.raises(ValueError):
        policy.evaluate(
            _escalated(),
            retry_count=-1,
        )