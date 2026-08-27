from src.intelligence.context import (
    DecisionContext,
)
from src.intelligence.scorer import (
    DecisionScorer,
)


def test_low_risk_context():
    scorer = DecisionScorer()

    context = DecisionContext(
        request="Check Kubernetes health",
        agent="kubernetes",
        environment="development",
        health_status="healthy",
        health_score=95,
        rollback_available=True,
        previous_executions=10,
        previous_successes=10,
        previous_failures=0,
        routing_confidence=0.95,
    )

    result = scorer.score(context)

    assert result["risk_level"] == "low"
    assert result["risk_score"] < 35
    assert result["confidence"] >= 0.8


def test_production_increases_risk():
    scorer = DecisionScorer()

    context = DecisionContext(
        request="Deploy Kubernetes service",
        environment="production",
        routing_confidence=0.9,
    )

    result = scorer.score(context)

    assert result["risk_score"] >= 25

    assert any(
        "Production environment"
        in factor
        for factor in result["risk_factors"]
    )


def test_critical_incident_is_high_risk():
    scorer = DecisionScorer()

    context = DecisionContext(
        request="Restart service",
        environment="production",
        health_status="unhealthy",
        health_score=15,
        incident_severity="critical",
        retry_count=1,
        rollback_available=False,
        routing_confidence=0.8,
    )

    result = scorer.score(context)

    assert result["risk_level"] == "critical"
    assert result["risk_score"] >= 80


def test_retry_count_increases_risk():
    scorer = DecisionScorer()

    base = DecisionContext(
        request="Restart service",
        retry_count=0,
        rollback_available=True,
        routing_confidence=0.8,
    )

    retried = DecisionContext(
        request="Restart service",
        retry_count=2,
        rollback_available=True,
        routing_confidence=0.8,
    )

    base_result = scorer.score(base)
    retried_result = scorer.score(retried)

    assert (
        retried_result["risk_score"]
        > base_result["risk_score"]
    )


def test_missing_rollback_increases_risk():
    scorer = DecisionScorer()

    with_rollback = DecisionContext(
        request="Restart service",
        rollback_available=True,
        routing_confidence=0.8,
    )

    without_rollback = DecisionContext(
        request="Restart service",
        rollback_available=False,
        routing_confidence=0.8,
    )

    first = scorer.score(
        with_rollback
    )

    second = scorer.score(
        without_rollback
    )

    assert (
        second["risk_score"]
        > first["risk_score"]
    )


def test_strong_execution_history_improves_confidence():
    scorer = DecisionScorer()

    context = DecisionContext(
        request="Check service",
        previous_executions=10,
        previous_successes=10,
        routing_confidence=0.8,
        rollback_available=True,
    )

    result = scorer.score(context)

    assert result["confidence"] >= 0.7

    assert any(
        "Strong historical execution success rate"
        in factor
        for factor in result[
            "confidence_factors"
        ]
    )


def test_poor_execution_history_adds_risk():
    scorer = DecisionScorer()

    context = DecisionContext(
        request="Deploy service",
        previous_executions=10,
        previous_successes=3,
        previous_failures=7,
        routing_confidence=0.8,
    )

    result = scorer.score(context)

    assert result["risk_score"] >= 20

    assert any(
        "Poor historical execution success rate"
        in factor
        for factor in result["risk_factors"]
    )


def test_failed_remediation_history_adds_risk():
    scorer = DecisionScorer()

    context = DecisionContext(
        request="Remediate service",
        previous_remediations=3,
        successful_remediations=1,
        failed_remediations=2,
        routing_confidence=0.8,
    )

    result = scorer.score(context)

    assert result["risk_score"] >= 20

    assert any(
        "Previous remediation failures detected"
        in factor
        for factor in result["risk_factors"]
    )


def test_high_routing_confidence_improves_confidence():
    scorer = DecisionScorer()

    low = DecisionContext(
        request="Check service",
        routing_confidence=0.2,
        rollback_available=True,
    )

    high = DecisionContext(
        request="Check service",
        routing_confidence=0.95,
        rollback_available=True,
    )

    low_result = scorer.score(low)
    high_result = scorer.score(high)

    assert (
        high_result["confidence"]
        > low_result["confidence"]
    )


def test_no_routing_confidence_reduces_confidence():
    scorer = DecisionScorer()

    context = DecisionContext(
        request="Unknown operation",
        routing_confidence=0.0,
    )

    result = scorer.score(context)

    assert result["confidence"] <= 0.4


def test_score_is_bounded():
    scorer = DecisionScorer()

    context = DecisionContext(
        request="Dangerous production remediation",
        environment="production",
        health_status="unhealthy",
        health_score=0,
        incident_severity="critical",
        retry_count=5,
        rollback_available=False,
        previous_executions=20,
        previous_successes=1,
        previous_failures=19,
        previous_remediations=10,
        successful_remediations=1,
        failed_remediations=9,
        routing_confidence=0.1,
    )

    result = scorer.score(context)

    assert 0 <= result["risk_score"] <= 100
    assert 0 <= result["confidence_score"] <= 100
    assert 0.0 <= result["confidence"] <= 1.0


def test_risk_level_thresholds():
    assert (
        DecisionScorer._risk_level(0)
        == "low"
    )

    assert (
        DecisionScorer._risk_level(34)
        == "low"
    )

    assert (
        DecisionScorer._risk_level(35)
        == "medium"
    )

    assert (
        DecisionScorer._risk_level(60)
        == "high"
    )

    assert (
        DecisionScorer._risk_level(80)
        == "critical"
    )