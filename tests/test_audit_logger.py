from src.audit.audit_logger import AuditLogger


def test_log_creates_audit_event():
    logger = AuditLogger()

    event = logger.log(
        request="Deploy application",
        action="execute",
        agent="kubernetes",
        allowed=True,
        risk="low",
        reason="Deployment approved",
    )

    assert event["request"] == "Deploy application"
    assert event["action"] == "execute"
    assert event["agent"] == "kubernetes"
    assert event["allowed"] is True
    assert event["risk"] == "low"
    assert "event_id" in event
    assert "timestamp" in event


def test_event_is_stored():
    logger = AuditLogger()

    logger.log(
        request="Check pod health",
        action="execute",
        agent="kubernetes",
    )

    events = logger.get_events()

    assert len(events) == 1
    assert events[0]["request"] == "Check pod health"


def test_blocked_events_are_filtered():
    logger = AuditLogger()

    logger.log(
        request="Check Kubernetes health",
        action="execute",
        allowed=True,
    )

    logger.log(
        request="kubectl delete production pods",
        action="block",
        allowed=False,
        risk="high",
        reason="Potentially destructive operation detected",
    )

    blocked = logger.get_blocked_events()

    assert len(blocked) == 1
    assert blocked[0]["allowed"] is False
    assert blocked[0]["risk"] == "high"


def test_metadata_is_recorded():
    logger = AuditLogger()

    event = logger.log(
        request="Deploy service",
        action="execute",
        metadata={
            "environment": "staging",
            "service": "payments",
        },
    )

    assert event["metadata"]["environment"] == "staging"
    assert event["metadata"]["service"] == "payments"


def test_clear_removes_events():
    logger = AuditLogger()

    logger.log(
        request="Check infrastructure",
        action="execute",
    )

    logger.clear()

    assert logger.get_events() == []