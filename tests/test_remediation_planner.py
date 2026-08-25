from src.remediation.planner import RemediationPlanner


def test_healthy_system_is_observed():
    planner = RemediationPlanner()

    result = planner.plan(
        {
            "status": "healthy",
            "score": 95,
            "reasons": [],
        }
    )

    assert result["action"] == "observe"
    assert result["requires_approval"] is False
    assert result["health_status"] == "healthy"
    assert result["health_score"] == 95


def test_degraded_system_generates_recommendation():
    planner = RemediationPlanner()

    result = planner.plan(
        {
            "status": "degraded",
            "score": 65,
            "reasons": [
                "Elevated failure rate",
            ],
        }
    )

    assert result["action"] == "recommend"
    assert result["requires_approval"] is False
    assert result["health_status"] == "degraded"
    assert result["health_score"] == 65


def test_unhealthy_system_requests_remediation():
    planner = RemediationPlanner()

    result = planner.plan(
        {
            "status": "unhealthy",
            "score": 30,
            "reasons": [
                "Agent failure rate is critical",
            ],
        }
    )

    assert result["action"] == "remediate"
    assert result["requires_approval"] is True
    assert result["health_status"] == "unhealthy"
    assert result["health_score"] == 30


def test_unknown_health_status_defaults_to_observe():
    planner = RemediationPlanner()

    result = planner.plan(
        {
            "status": "unknown",
            "score": 0,
            "reasons": [
                "Insufficient telemetry",
            ],
        }
    )

    assert result["action"] == "observe"
    assert result["requires_approval"] is False
    assert result["health_status"] == "unknown"