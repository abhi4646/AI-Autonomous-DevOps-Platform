from src.orchestrator.orchestrator import Orchestrator
from src.persistence.database import Database


class FakeKubernetesAgent:
    name = "kubernetes"

    def __init__(self):
        self.calls = []

    def execute(self, context):
        self.calls.append(context)

        return {
            "status": "ok",
            "operation": "completed",
        }


def create_orchestrator():
    database = Database(
        ":memory:"
    )

    orchestrator = Orchestrator(
        database=database
    )

    agent = FakeKubernetesAgent()

    orchestrator.register_agent(
        agent
    )

    return (
        orchestrator,
        database,
        agent,
    )


def test_intelligence_is_returned_for_safe_request():
    (
        orchestrator,
        database,
        agent,
    ) = create_orchestrator()

    try:
        result = orchestrator.route(
            "Check Kubernetes health",
            context={
                "environment": "development",
                "health_result": {
                    "status": "healthy",
                    "score": 95,
                    "reasons": [],
                },
            },
        )

        assert (
            result["status"]
            == "routed"
        )

        assert "intelligence" in result

        intelligence = result[
            "intelligence"
        ]

        assert (
            "risk_score"
            in intelligence
        )

        assert (
            "confidence"
            in intelligence
        )

        assert (
            "recommendation"
            in intelligence
        )

    finally:
        orchestrator.close()


def test_intelligence_reaches_agent_context():
    (
        orchestrator,
        database,
        agent,
    ) = create_orchestrator()

    try:
        result = orchestrator.route(
            "Check Kubernetes health",
            context={
                "environment": "development",
                "health_result": {
                    "status": "healthy",
                    "score": 95,
                    "reasons": [],
                },
            },
        )

        assert (
            result["status"]
            == "routed"
        )

        assert len(agent.calls) == 1

        execution_context = (
            agent.calls[0]
        )

        assert (
            "decision_intelligence"
            in execution_context
        )

    finally:
        orchestrator.close()


def test_production_mutation_requires_approval():
    (
        orchestrator,
        database,
        agent,
    ) = create_orchestrator()

    try:
        result = orchestrator.route(
            "Deploy Kubernetes service",
            context={
                "environment": "production",
                "health_result": {
                    "status": "healthy",
                    "score": 95,
                    "reasons": [],
                },
            },
        )

        assert (
            result["status"]
            == "pending_approval"
        )

        assert (
            result["intelligence"][
                "requires_approval"
            ]
            is True
        )

        assert len(agent.calls) == 0

    finally:
        orchestrator.close()


def test_approved_production_mutation_executes():
    (
        orchestrator,
        database,
        agent,
    ) = create_orchestrator()

    try:
        pending = orchestrator.route(
            "Deploy Kubernetes service",
            context={
                "environment": "production",
                "health_result": {
                    "status": "healthy",
                    "score": 95,
                    "reasons": [],
                },
            },
        )

        assert (
            pending["status"]
            == "pending_approval"
        )

        approval_id = pending[
            "approval_id"
        ]

        orchestrator.approval_manager.approve(
            approval_id,
            decided_by="operator",
            reason="Approved test deployment",
        )

        result = orchestrator.route(
            "Deploy Kubernetes service",
            context={
                "environment": "production",
                "health_result": {
                    "status": "healthy",
                    "score": 95,
                    "reasons": [],
                },
            },
            approval_id=approval_id,
        )

        assert (
            result["status"]
            == "routed"
        )

        assert len(agent.calls) == 1

    finally:
        orchestrator.close()


def test_intelligence_uses_execution_history():
    (
        orchestrator,
        database,
        agent,
    ) = create_orchestrator()

    try:
        database.save_execution(
            request="Check pod",
            agent="kubernetes",
            status="success",
            result={
                "status": "ok"
            },
        )

        database.save_execution(
            request="Check deployment",
            agent="kubernetes",
            status="failed",
            result={
                "status": "failed"
            },
        )

        result = orchestrator.route(
            "Check Kubernetes health",
            context={
                "environment": "development",
                "health_result": {
                    "status": "healthy",
                    "score": 90,
                    "reasons": [],
                },
            },
        )

        historical = result[
            "intelligence"
        ][
            "historical_outcomes"
        ]

        assert (
            historical[
                "execution_success_rate"
            ]
            == 0.5
        )

    finally:
        orchestrator.close()


def test_intelligence_uses_incident_state():
    (
        orchestrator,
        database,
        agent,
    ) = create_orchestrator()

    try:
        incident = {
            "incident_id": "inc-intel-1",
            "title": "Kubernetes failure",
            "agent": "kubernetes",
            "severity": "critical",
            "status": "investigating",
            "health_snapshot": {
                "status": "unhealthy",
                "score": 10,
                "reasons": [
                    "Pods unavailable"
                ],
            },
            "approval_id": None,
            "retry_count": 1,
            "rollback_available": True,
            "metadata": {},
            "created_at": (
                "2026-08-27T00:00:00"
            ),
            "updated_at": (
                "2026-08-27T00:00:00"
            ),
            "resolved_at": None,
        }

        database.save_incident(
            incident
        )

        result = orchestrator.route(
            "Check Kubernetes health",
            context={
                "environment": "production",
                "incident_id": (
                    "inc-intel-1"
                ),
            },
        )

        intelligence = result[
            "intelligence"
        ]

        assert (
            intelligence[
                "risk_level"
            ]
            in {
                "high",
                "critical",
            }
        )

        assert (
            intelligence[
                "historical_outcomes"
            ]
            is not None
        )

    finally:
        orchestrator.close()


def test_intelligence_is_written_to_audit_metadata():
    (
        orchestrator,
        database,
        agent,
    ) = create_orchestrator()

    try:
        result = orchestrator.route(
            "Check Kubernetes health",
            context={
                "environment": "development",
                "health_result": {
                    "status": "healthy",
                    "score": 95,
                    "reasons": [],
                },
            },
        )

        assert (
            result["status"]
            == "routed"
        )

        events = (
            database.get_audit_events()
        )

        execute_events = [
            event
            for event in events
            if event["event_type"]
            == "execute"
        ]

        assert len(
            execute_events
        ) >= 1

        metadata = execute_events[
            -1
        ]["metadata"]

        assert (
            "metadata"
            in metadata
        )

        audit_payload = metadata[
            "metadata"
        ]

        assert (
            "intelligence"
            in audit_payload
        )

        intelligence = audit_payload[
            "intelligence"
        ]

        assert (
            "recommendation"
            in intelligence
        )

        assert (
            "context"
            in intelligence
        )

    finally:
        orchestrator.close()