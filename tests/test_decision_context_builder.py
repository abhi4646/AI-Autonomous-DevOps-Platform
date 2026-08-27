from src.intelligence.context_builder import (
    DecisionContextBuilder,
)


class FakeDatabase:
    def __init__(
        self,
        executions=None,
        incidents=None,
    ):
        self.executions = (
            executions
            or []
        )

        self.incidents = (
            incidents
            or []
        )

    def get_executions(self):
        return list(
            self.executions
        )

    def get_incident(
        self,
        incident_id,
    ):
        for incident in self.incidents:
            if (
                incident["incident_id"]
                == incident_id
            ):
                return dict(
                    incident
                )

        return None

    def get_incidents(
        self,
        *,
        status=None,
    ):
        if status is None:
            return [
                dict(item)
                for item
                in self.incidents
            ]

        return [
            dict(item)
            for item
            in self.incidents
            if item.get("status")
            == status
        ]


def test_build_minimal_context():
    database = FakeDatabase()

    builder = (
        DecisionContextBuilder(
            database
        )
    )

    context = builder.build(
        "Check Kubernetes health",
        agent="kubernetes",
    )

    assert (
        context.request
        == "Check Kubernetes health"
    )

    assert (
        context.agent
        == "kubernetes"
    )

    assert (
        context.previous_executions
        == 0
    )

    assert (
        context.previous_incidents
        == 0
    )


def test_build_execution_history():
    database = FakeDatabase(
        executions=[
            {
                "request": "Check pod",
                "agent": "kubernetes",
                "status": "success",
            },
            {
                "request": "Deploy pod",
                "agent": "kubernetes",
                "status": "failed",
            },
            {
                "request": "Check repo",
                "agent": "github",
                "status": "success",
            },
        ]
    )

    builder = (
        DecisionContextBuilder(
            database
        )
    )

    context = builder.build(
        "Check Kubernetes",
        agent="kubernetes",
    )

    assert (
        context.previous_executions
        == 2
    )

    assert (
        context.previous_successes
        == 1
    )

    assert (
        context.previous_failures
        == 1
    )


def test_agent_history_is_isolated():
    database = FakeDatabase(
        executions=[
            {
                "request": "Deploy",
                "agent": "kubernetes",
                "status": "success",
            },
            {
                "request": "Commit",
                "agent": "github",
                "status": "failed",
            },
        ]
    )

    builder = (
        DecisionContextBuilder(
            database
        )
    )

    context = builder.build(
        "Kubernetes request",
        agent="kubernetes",
    )

    assert (
        context.previous_executions
        == 1
    )

    assert (
        context.previous_successes
        == 1
    )

    assert (
        context.previous_failures
        == 0
    )


def test_incident_context_is_loaded():
    database = FakeDatabase(
        incidents=[
            {
                "incident_id": "inc-001",
                "agent": "kubernetes",
                "severity": "critical",
                "status": "open",
                "health_snapshot": {
                    "status": "unhealthy",
                    "score": 20,
                    "reasons": [
                        "Pod crash loop"
                    ],
                },
                "retry_count": 2,
                "rollback_available": True,
                "metadata": {
                    "cluster": "prod-1"
                },
            }
        ]
    )

    builder = (
        DecisionContextBuilder(
            database
        )
    )

    context = builder.build(
        "Recover service",
        incident_id="inc-001",
    )

    assert (
        context.incident_id
        == "inc-001"
    )

    assert (
        context.agent
        == "kubernetes"
    )

    assert (
        context.incident_severity
        == "critical"
    )

    assert (
        context.incident_status
        == "open"
    )

    assert (
        context.health_status
        == "unhealthy"
    )

    assert (
        context.health_score
        == 20
    )

    assert context.retry_count == 2

    assert (
        context.rollback_available
        is True
    )


def test_current_health_overrides_incident_snapshot():
    database = FakeDatabase(
        incidents=[
            {
                "incident_id": "inc-002",
                "agent": "kubernetes",
                "severity": "high",
                "status": "open",
                "health_snapshot": {
                    "status": "unhealthy",
                    "score": 20,
                    "reasons": [
                        "Old failure"
                    ],
                },
                "retry_count": 0,
                "rollback_available": True,
                "metadata": {},
            }
        ]
    )

    builder = (
        DecisionContextBuilder(
            database
        )
    )

    context = builder.build(
        "Verify service",
        incident_id="inc-002",
        health_result={
            "status": "healthy",
            "score": 95,
            "reasons": [],
        },
    )

    assert (
        context.health_status
        == "healthy"
    )

    assert (
        context.health_score
        == 95
    )

    assert context.reasons == []


def test_routing_confidence_is_preserved():
    database = FakeDatabase()

    builder = (
        DecisionContextBuilder(
            database
        )
    )

    context = builder.build(
        "Deploy service",
        agent="kubernetes",
        routing_confidence=0.91,
    )

    assert (
        context.routing_confidence
        == 0.91
    )


def test_previous_incidents_are_counted_by_agent():
    database = FakeDatabase(
        incidents=[
            {
                "incident_id": "inc-1",
                "agent": "kubernetes",
            },
            {
                "incident_id": "inc-2",
                "agent": "kubernetes",
            },
            {
                "incident_id": "inc-3",
                "agent": "github",
            },
        ]
    )

    builder = (
        DecisionContextBuilder(
            database
        )
    )

    context = builder.build(
        "Check cluster",
        agent="kubernetes",
    )

    assert (
        context.previous_incidents
        == 2
    )


def test_remediation_history_is_detected():
    database = FakeDatabase(
        executions=[
            {
                "request": (
                    "Remediate unhealthy "
                    "kubernetes agent"
                ),
                "agent": "kubernetes",
                "status": "success",
            },
            {
                "request": (
                    "Retry remediation"
                ),
                "agent": "kubernetes",
                "status": "failed",
            },
            {
                "request": "Check health",
                "agent": "kubernetes",
                "status": "success",
            },
        ]
    )

    builder = (
        DecisionContextBuilder(
            database
        )
    )

    context = builder.build(
        "Recover service",
        agent="kubernetes",
    )

    assert (
        context.previous_remediations
        == 2
    )

    assert (
        context.successful_remediations
        == 1
    )

    assert (
        context.failed_remediations
        == 1
    )


def test_telemetry_action_detects_remediation():
    database = FakeDatabase(
        executions=[
            {
                "request": "Service operation",
                "agent": "kubernetes",
                "status": "success",
                "telemetry_metadata": {
                    "action": "rollback"
                },
            }
        ]
    )

    builder = (
        DecisionContextBuilder(
            database
        )
    )

    context = builder.build(
        "Check service",
        agent="kubernetes",
    )

    assert (
        context.previous_remediations
        == 1
    )

    assert (
        context.successful_remediations
        == 1
    )


def test_metadata_is_merged():
    database = FakeDatabase(
        incidents=[
            {
                "incident_id": "inc-003",
                "agent": "kubernetes",
                "severity": "medium",
                "status": "open",
                "health_snapshot": {},
                "retry_count": 0,
                "rollback_available": False,
                "metadata": {
                    "cluster": "prod-1",
                    "region": "ca-central-1",
                },
            }
        ]
    )

    builder = (
        DecisionContextBuilder(
            database
        )
    )

    context = builder.build(
        "Check service",
        incident_id="inc-003",
        metadata={
            "source": "decision-engine",
            "region": "updated-region",
        },
    )

    assert (
        context.metadata["cluster"]
        == "prod-1"
    )

    assert (
        context.metadata["source"]
        == "decision-engine"
    )

    assert (
        context.metadata["region"]
        == "updated-region"
    )


def test_missing_incident_is_safe():
    database = FakeDatabase()

    builder = (
        DecisionContextBuilder(
            database
        )
    )

    context = builder.build(
        "Check service",
        agent="monitoring",
        incident_id="missing",
    )

    assert (
        context.incident_id
        is None
    )

    assert (
        context.health_status
        == "unknown"
    )


def test_environment_is_preserved():
    database = FakeDatabase()

    builder = (
        DecisionContextBuilder(
            database
        )
    )

    context = builder.build(
        "Deploy service",
        agent="kubernetes",
        environment="production",
    )

    assert (
        context.environment
        == "production"
    )