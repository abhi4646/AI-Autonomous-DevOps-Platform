import pytest

from src.intelligence.context import (
    DecisionContext,
)


def test_minimal_context():
    context = DecisionContext(
        request="Check Kubernetes health"
    )

    assert (
        context.request
        == "Check Kubernetes health"
    )

    assert context.agent is None
    assert context.environment == "unknown"
    assert context.health_status == "unknown"
    assert context.health_score is None
    assert context.retry_count == 0
    assert context.rollback_available is False


def test_full_context():
    context = DecisionContext(
        request="Restart Kubernetes deployment",
        agent="kubernetes",
        environment="production",
        health_status="unhealthy",
        health_score=20,
        incident_id="incident-123",
        incident_status="remediating",
        incident_severity="critical",
        retry_count=1,
        rollback_available=True,
        previous_executions=10,
        previous_successes=7,
        previous_failures=3,
        previous_incidents=4,
        previous_remediations=4,
        successful_remediations=3,
        failed_remediations=1,
        routing_confidence=0.95,
        reasons=[
            "Deployment is unhealthy",
        ],
        metadata={
            "service": "checkout",
        },
    )

    assert context.agent == "kubernetes"
    assert context.is_production is True
    assert context.has_failure_history is True

    assert (
        context.execution_success_rate
        == 0.7
    )

    assert (
        context.remediation_success_rate
        == 0.75
    )


def test_success_rates_are_none_without_history():
    context = DecisionContext(
        request="Check service"
    )

    assert (
        context.execution_success_rate
        is None
    )

    assert (
        context.remediation_success_rate
        is None
    )


def test_non_production_environment():
    context = DecisionContext(
        request="Deploy service",
        environment="staging",
    )

    assert context.is_production is False


def test_failure_history_from_execution():
    context = DecisionContext(
        request="Check Docker",
        previous_failures=1,
    )

    assert (
        context.has_failure_history
        is True
    )


def test_failure_history_from_remediation():
    context = DecisionContext(
        request="Check Kubernetes",
        failed_remediations=1,
    )

    assert (
        context.has_failure_history
        is True
    )


def test_context_to_dict():
    context = DecisionContext(
        request="Check Kubernetes",
        agent="kubernetes",
        environment="production",
        previous_executions=4,
        previous_successes=3,
        previous_failures=1,
        routing_confidence=0.8,
    )

    data = context.to_dict()

    assert data["agent"] == "kubernetes"
    assert data["is_production"] is True

    assert (
        data["execution_success_rate"]
        == 0.75
    )

    assert (
        data["routing_confidence"]
        == 0.8
    )


def test_context_round_trip():
    original = DecisionContext(
        request="Terraform production plan",
        agent="terraform",
        environment="production",
        health_status="degraded",
        health_score=65,
        incident_id="incident-abc",
        incident_status="investigating",
        incident_severity="medium",
        retry_count=1,
        rollback_available=True,
        previous_executions=5,
        previous_successes=4,
        previous_failures=1,
        previous_incidents=2,
        previous_remediations=2,
        successful_remediations=1,
        failed_remediations=1,
        routing_confidence=0.9,
        reasons=[
            "Infrastructure drift detected",
        ],
        metadata={
            "region": "ca-central-1",
        },
    )

    restored = DecisionContext.from_dict(
        original.to_dict()
    )

    assert (
        restored.request
        == original.request
    )

    assert (
        restored.agent
        == original.agent
    )

    assert (
        restored.environment
        == original.environment
    )

    assert (
        restored.health_score
        == original.health_score
    )

    assert (
        restored.retry_count
        == original.retry_count
    )

    assert (
        restored.rollback_available
        == original.rollback_available
    )

    assert (
        restored.reasons
        == original.reasons
    )

    assert (
        restored.metadata
        == original.metadata
    )


def test_empty_request_rejected():
    with pytest.raises(
        ValueError,
        match="request cannot be empty",
    ):
        DecisionContext(
            request="   "
        )


def test_non_string_request_rejected():
    with pytest.raises(
        TypeError,
        match="request must be a string",
    ):
        DecisionContext(
            request=123
        )


def test_negative_retry_count_rejected():
    with pytest.raises(
        ValueError,
        match="retry_count cannot be negative",
    ):
        DecisionContext(
            request="Restart service",
            retry_count=-1,
        )


def test_negative_history_rejected():
    with pytest.raises(
        ValueError,
        match=(
            "previous_failures "
            "cannot be negative"
        ),
    ):
        DecisionContext(
            request="Check service",
            previous_failures=-1,
        )


def test_routing_confidence_above_one_rejected():
    with pytest.raises(
        ValueError,
        match=(
            "routing_confidence must be "
            "between 0.0 and 1.0"
        ),
    ):
        DecisionContext(
            request="Check service",
            routing_confidence=1.1,
        )


def test_negative_routing_confidence_rejected():
    with pytest.raises(ValueError):
        DecisionContext(
            request="Check service",
            routing_confidence=-0.1,
        )


def test_health_score_above_100_rejected():
    with pytest.raises(
        ValueError,
        match=(
            "health_score must be "
            "between 0 and 100"
        ),
    ):
        DecisionContext(
            request="Check health",
            health_score=101,
        )


def test_negative_health_score_rejected():
    with pytest.raises(ValueError):
        DecisionContext(
            request="Check health",
            health_score=-1,
        )