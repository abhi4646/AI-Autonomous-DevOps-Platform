from src.intelligence.context import DecisionContext
from src.intelligence.recommender import (
    RecommendationEngine,
)


def test_safe_nonproduction_action_can_execute():
    engine = RecommendationEngine()

    context = DecisionContext(
        request="Check Kubernetes health",
        agent="kubernetes",
        environment="development",
        health_status="healthy",
        health_score=95,
        rollback_available=True,
        previous_executions=10,
        previous_successes=10,
        routing_confidence=0.95,
    )

    result = engine.recommend(
        context
    )

    assert (
        result["recommendation"]
        in {"execute", "observe"}
    )

    assert (
        result["requires_approval"]
        is False
    )


def test_production_action_is_conservative():
    engine = RecommendationEngine()

    context = DecisionContext(
        request="Deploy Kubernetes service",
        agent="kubernetes",
        environment="production",
        health_status="healthy",
        health_score=95,
        rollback_available=True,
        previous_executions=20,
        previous_successes=20,
        routing_confidence=0.95,
    )

    result = engine.recommend(
        context
    )

    assert (
        result["recommendation"]
        != "execute"
    )

    assert (
        result["requires_approval"]
        is True
    )


def test_unhealthy_system_recommends_remediation():
    engine = RecommendationEngine()

    context = DecisionContext(
        request="Recover Kubernetes service",
        agent="kubernetes",
        environment="development",
        health_status="unhealthy",
        health_score=45,
        rollback_available=True,
        routing_confidence=0.9,
    )

    result = engine.recommend(
        context
    )

    assert result["recommendation"] in {
        "remediate",
        "review",
        "escalate",
    }

    assert (
        result["requires_approval"]
        is True
    )


def test_failed_remediation_history_recommends_rollback():
    engine = RecommendationEngine()

    context = DecisionContext(
        request="Recover production service",
        agent="kubernetes",
        environment="production",
        health_status="unhealthy",
        health_score=15,
        incident_severity="critical",
        rollback_available=True,
        previous_remediations=4,
        successful_remediations=1,
        failed_remediations=3,
        routing_confidence=0.9,
    )

    result = engine.recommend(
        context
    )

    assert (
        result["recommendation"]
        == "rollback"
    )

    assert (
        result["requires_approval"]
        is True
    )


def test_failed_history_without_rollback_escalates():
    engine = RecommendationEngine()

    context = DecisionContext(
        request="Recover service",
        health_status="unhealthy",
        health_score=10,
        previous_remediations=4,
        successful_remediations=1,
        failed_remediations=3,
        rollback_available=False,
        routing_confidence=0.9,
    )

    result = engine.recommend(
        context
    )

    assert (
        result["recommendation"]
        == "escalate"
    )


def test_retry_with_high_risk_prefers_rollback():
    engine = RecommendationEngine()

    context = DecisionContext(
        request="Retry failed remediation",
        environment="production",
        health_status="unhealthy",
        health_score=20,
        incident_severity="high",
        retry_count=1,
        rollback_available=True,
        routing_confidence=0.9,
    )

    result = engine.recommend(
        context
    )

    assert (
        result["recommendation"]
        == "rollback"
    )


def test_retry_without_rollback_escalates():
    engine = RecommendationEngine()

    context = DecisionContext(
        request="Retry failed remediation",
        health_status="unhealthy",
        health_score=20,
        retry_count=1,
        rollback_available=False,
        routing_confidence=0.9,
    )

    result = engine.recommend(
        context
    )

    assert (
        result["recommendation"]
        == "escalate"
    )


def test_critical_risk_requires_human_control():
    engine = RecommendationEngine()

    context = DecisionContext(
        request="Restart critical production service",
        environment="production",
        health_status="unhealthy",
        health_score=5,
        incident_severity="critical",
        rollback_available=False,
        routing_confidence=0.8,
    )

    result = engine.recommend(
        context
    )

    assert (
        result["risk_level"]
        == "critical"
    )

    assert (
        result["requires_approval"]
        is True
    )


def test_recommendation_contains_explanation():
    engine = RecommendationEngine()

    context = DecisionContext(
        request="Check service",
        environment="development",
        health_status="healthy",
        health_score=90,
        rollback_available=True,
        routing_confidence=0.9,
    )

    result = engine.recommend(
        context
    )

    assert isinstance(
        result["explanation"],
        str,
    )

    assert len(
        result["explanation"]
    ) > 20


def test_recommendation_includes_scoring_details():
    engine = RecommendationEngine()

    context = DecisionContext(
        request="Check service",
        routing_confidence=0.8,
    )

    result = engine.recommend(
        context
    )

    assert "risk_score" in result
    assert "risk_level" in result
    assert "confidence" in result
    assert "risk_factors" in result

    assert (
        "historical_outcomes"
        in result
    )