from src.health.evaluator import HealthEvaluator


def test_health_unknown_without_execution_data():
    evaluator = HealthEvaluator()

    result = evaluator.evaluate(
        {
            "total_executions": 0,
            "failure_rate": 0,
            "average_duration_ms": 0,
        }
    )

    assert result["status"] == "unknown"
    assert result["score"] is None


def test_health_is_healthy_for_good_metrics():
    evaluator = HealthEvaluator()

    result = evaluator.evaluate(
        {
            "total_executions": 100,
            "failure_rate": 0.02,
            "average_duration_ms": 1000,
        }
    )

    assert result["status"] == "healthy"
    assert result["score"] == 100


def test_health_degrades_with_elevated_failure_rate():
    evaluator = HealthEvaluator()

    result = evaluator.evaluate(
        {
            "total_executions": 100,
            "failure_rate": 0.20,
            "average_duration_ms": 1000,
        }
    )

    assert result["status"] == "degraded"
    assert result["score"] == 75
    assert "Elevated execution failure rate" in result["reasons"]


def test_health_unhealthy_with_high_failure_and_duration():
    evaluator = HealthEvaluator()

    result = evaluator.evaluate(
        {
            "total_executions": 100,
            "failure_rate": 0.40,
            "average_duration_ms": 20000,
        }
    )

    assert result["status"] == "unhealthy"
    assert result["score"] == 20
    assert "High execution failure rate" in result["reasons"]
    assert "High average execution duration" in result["reasons"]