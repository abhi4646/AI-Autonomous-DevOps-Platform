from typing import Any, Dict, Optional

from src.intelligence.context import DecisionContext


class DecisionContextBuilder:
    """
    Builds DecisionContext objects from persisted platform
    state and current routing information.

    The builder is read-only. It does not create incidents,
    modify executions, request approvals, or perform
    remediation.
    """

    SUCCESS_STATUSES = {
        "success",
        "routed",
    }

    FAILURE_STATUSES = {
        "failed",
        "failure",
        "error",
        "timeout",
        "unavailable",
        "blocked",
    }

    REMEDIATION_KEYWORDS = {
        "remediate",
        "remediation",
        "retry",
        "rollback",
        "recover",
        "recovery",
    }

    def __init__(
        self,
        database: Any,
    ) -> None:
        self.database = database

    def build(
        self,
        request: str,
        *,
        agent: Optional[str] = None,
        environment: str = "unknown",
        routing_confidence: float = 0.0,
        incident_id: Optional[str] = None,
        health_result: Optional[
            Dict[str, Any]
        ] = None,
        metadata: Optional[
            Dict[str, Any]
        ] = None,
    ) -> DecisionContext:
        """
        Assemble normalized decision context from:

        - current request,
        - routing information,
        - persisted execution history,
        - persisted incident state,
        - current health information.

        Explicit current health information takes precedence
        over an older incident health snapshot.
        """

        executions = (
            self.database.get_executions()
        )

        incident = self._get_incident(
            incident_id
        )

        history = self._execution_history(
            executions,
            agent=agent,
        )

        remediation_history = (
            self._remediation_history(
                executions,
                agent=agent,
            )
        )

        incident_health = {}

        if incident is not None:
            incident_health = (
                incident.get(
                    "health_snapshot"
                )
                or {}
            )

        current_health = (
            health_result
            or incident_health
            or {}
        )

        health_status = (
            current_health.get("status")
            or "unknown"
        )

        health_score = (
            current_health.get("score")
        )

        reasons = list(
            current_health.get(
                "reasons",
                [],
            )
            or []
        )

        context_metadata = {}

        if incident is not None:
            context_metadata.update(
                incident.get(
                    "metadata",
                    {},
                )
                or {}
            )

        if metadata:
            context_metadata.update(
                metadata
            )

        return DecisionContext(
            request=request,
            agent=(
                agent
                or self._incident_value(
                    incident,
                    "agent",
                )
            ),
            environment=environment,
            health_status=health_status,
            health_score=health_score,
            incident_id=(
                self._incident_value(
                    incident,
                    "incident_id",
                )
            ),
            incident_status=(
                self._incident_value(
                    incident,
                    "status",
                )
            ),
            incident_severity=(
                self._incident_value(
                    incident,
                    "severity",
                )
            ),
            retry_count=(
                self._incident_value(
                    incident,
                    "retry_count",
                    0,
                )
            ),
            rollback_available=bool(
                self._incident_value(
                    incident,
                    "rollback_available",
                    False,
                )
            ),
            previous_executions=history[
                "total"
            ],
            previous_successes=history[
                "successes"
            ],
            previous_failures=history[
                "failures"
            ],
            previous_incidents=(
                self._count_incidents(
                    agent=(
                        agent
                        or self._incident_value(
                            incident,
                            "agent",
                        )
                    )
                )
            ),
            previous_remediations=(
                remediation_history[
                    "total"
                ]
            ),
            successful_remediations=(
                remediation_history[
                    "successes"
                ]
            ),
            failed_remediations=(
                remediation_history[
                    "failures"
                ]
            ),
            routing_confidence=(
                routing_confidence
            ),
            reasons=reasons,
            metadata=context_metadata,
        )

    def _get_incident(
        self,
        incident_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        if incident_id is None:
            return None

        return self.database.get_incident(
            incident_id
        )

    @staticmethod
    def _incident_value(
        incident: Optional[
            Dict[str, Any]
        ],
        key: str,
        default: Any = None,
    ) -> Any:
        if incident is None:
            return default

        value = incident.get(
            key,
            default,
        )

        if value is None:
            return default

        return value

    def _execution_history(
        self,
        executions: list[dict],
        *,
        agent: Optional[str],
    ) -> Dict[str, int]:
        relevant = self._filter_by_agent(
            executions,
            agent,
        )

        successes = 0
        failures = 0

        for execution in relevant:
            status = str(
                execution.get(
                    "status",
                    "",
                )
            ).lower()

            if status in self.SUCCESS_STATUSES:
                successes += 1

            if status in self.FAILURE_STATUSES:
                failures += 1

        return {
            "total": len(relevant),
            "successes": successes,
            "failures": failures,
        }

    def _remediation_history(
        self,
        executions: list[dict],
        *,
        agent: Optional[str],
    ) -> Dict[str, int]:
        relevant = self._filter_by_agent(
            executions,
            agent,
        )

        remediations = []

        for execution in relevant:
            request = str(
                execution.get(
                    "request",
                    "",
                )
            ).lower()

            telemetry = (
                execution.get(
                    "telemetry_metadata"
                )
                or {}
            )

            action = str(
                telemetry.get(
                    "action",
                    "",
                )
            ).lower()

            is_remediation = (
                any(
                    keyword in request
                    for keyword
                    in self.REMEDIATION_KEYWORDS
                )
                or action
                in self.REMEDIATION_KEYWORDS
            )

            if is_remediation:
                remediations.append(
                    execution
                )

        successes = 0
        failures = 0

        for execution in remediations:
            status = str(
                execution.get(
                    "status",
                    "",
                )
            ).lower()

            if status in self.SUCCESS_STATUSES:
                successes += 1

            if status in self.FAILURE_STATUSES:
                failures += 1

        return {
            "total": len(remediations),
            "successes": successes,
            "failures": failures,
        }

    def _count_incidents(
        self,
        *,
        agent: Optional[str],
    ) -> int:
        incidents = (
            self.database.get_incidents()
        )

        if agent is None:
            return len(incidents)

        return sum(
            1
            for incident in incidents
            if incident.get("agent")
            == agent
        )

    @staticmethod
    def _filter_by_agent(
        executions: list[dict],
        agent: Optional[str],
    ) -> list[dict]:
        if agent is None:
            return list(executions)

        return [
            execution
            for execution in executions
            if execution.get("agent")
            == agent
        ]