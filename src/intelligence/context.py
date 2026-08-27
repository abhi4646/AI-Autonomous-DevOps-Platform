from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DecisionContext:
    """
    Normalized operational context used by the decision
    intelligence layer.

    This object does not make decisions itself. It collects
    the signals required by later scoring and recommendation
    components.
    """

    request: str

    agent: Optional[str] = None
    environment: str = "unknown"

    health_status: str = "unknown"
    health_score: Optional[float] = None

    incident_id: Optional[str] = None
    incident_status: Optional[str] = None
    incident_severity: Optional[str] = None

    retry_count: int = 0
    rollback_available: bool = False

    previous_executions: int = 0
    previous_successes: int = 0
    previous_failures: int = 0

    previous_incidents: int = 0
    previous_remediations: int = 0
    successful_remediations: int = 0
    failed_remediations: int = 0

    routing_confidence: float = 0.0

    reasons: List[str] = field(
        default_factory=list
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if not isinstance(self.request, str):
            raise TypeError(
                "request must be a string"
            )

        if not self.request.strip():
            raise ValueError(
                "request cannot be empty"
            )

        if self.retry_count < 0:
            raise ValueError(
                "retry_count cannot be negative"
            )

        count_fields = {
            "previous_executions": self.previous_executions,
            "previous_successes": self.previous_successes,
            "previous_failures": self.previous_failures,
            "previous_incidents": self.previous_incidents,
            "previous_remediations": self.previous_remediations,
            "successful_remediations": self.successful_remediations,
            "failed_remediations": self.failed_remediations,
        }

        for name, value in count_fields.items():
            if value < 0:
                raise ValueError(
                    f"{name} cannot be negative"
                )

        if not 0.0 <= self.routing_confidence <= 1.0:
            raise ValueError(
                "routing_confidence must be between 0.0 and 1.0"
            )

        if self.health_score is not None:
            if not 0 <= self.health_score <= 100:
                raise ValueError(
                    "health_score must be between 0 and 100"
                )

    @property
    def execution_success_rate(
        self,
    ) -> Optional[float]:
        if self.previous_executions == 0:
            return None

        return (
            self.previous_successes
            / self.previous_executions
        )

    @property
    def remediation_success_rate(
        self,
    ) -> Optional[float]:
        if self.previous_remediations == 0:
            return None

        return (
            self.successful_remediations
            / self.previous_remediations
        )

    @property
    def has_failure_history(self) -> bool:
        return (
            self.previous_failures > 0
            or self.failed_remediations > 0
        )

    @property
    def is_production(self) -> bool:
        return (
            self.environment.strip().lower()
            == "production"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request": self.request,
            "agent": self.agent,
            "environment": self.environment,
            "health_status": self.health_status,
            "health_score": self.health_score,
            "incident_id": self.incident_id,
            "incident_status": self.incident_status,
            "incident_severity": self.incident_severity,
            "retry_count": self.retry_count,
            "rollback_available": self.rollback_available,
            "previous_executions": self.previous_executions,
            "previous_successes": self.previous_successes,
            "previous_failures": self.previous_failures,
            "previous_incidents": self.previous_incidents,
            "previous_remediations": self.previous_remediations,
            "successful_remediations": self.successful_remediations,
            "failed_remediations": self.failed_remediations,
            "routing_confidence": self.routing_confidence,
            "execution_success_rate": self.execution_success_rate,
            "remediation_success_rate": self.remediation_success_rate,
            "has_failure_history": self.has_failure_history,
            "is_production": self.is_production,
            "reasons": list(self.reasons),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "DecisionContext":
        return cls(
            request=data["request"],
            agent=data.get("agent"),
            environment=data.get(
                "environment",
                "unknown",
            ),
            health_status=data.get(
                "health_status",
                "unknown",
            ),
            health_score=data.get(
                "health_score"
            ),
            incident_id=data.get(
                "incident_id"
            ),
            incident_status=data.get(
                "incident_status"
            ),
            incident_severity=data.get(
                "incident_severity"
            ),
            retry_count=data.get(
                "retry_count",
                0,
            ),
            rollback_available=data.get(
                "rollback_available",
                False,
            ),
            previous_executions=data.get(
                "previous_executions",
                0,
            ),
            previous_successes=data.get(
                "previous_successes",
                0,
            ),
            previous_failures=data.get(
                "previous_failures",
                0,
            ),
            previous_incidents=data.get(
                "previous_incidents",
                0,
            ),
            previous_remediations=data.get(
                "previous_remediations",
                0,
            ),
            successful_remediations=data.get(
                "successful_remediations",
                0,
            ),
            failed_remediations=data.get(
                "failed_remediations",
                0,
            ),
            routing_confidence=data.get(
                "routing_confidence",
                0.0,
            ),
            reasons=list(
                data.get(
                    "reasons",
                    [],
                )
            ),
            metadata=dict(
                data.get(
                    "metadata",
                    {},
                )
            ),
        )