from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4


class SignalType(str, Enum):
    """
    Categories of operational signals that may contribute
    evidence to incident correlation and root-cause analysis.
    """

    CODE_CHANGE = "code_change"
    BUILD = "build"
    DEPLOYMENT = "deployment"
    CONFIGURATION = "configuration"
    INFRASTRUCTURE = "infrastructure"
    HEALTH = "health"
    METRIC = "metric"
    ALERT = "alert"
    LOG = "log"
    INCIDENT = "incident"
    REMEDIATION = "remediation"
    ROLLBACK = "rollback"
    UNKNOWN = "unknown"


class SignalSeverity(str, Enum):
    """
    Normalized severity assigned to an operational signal.
    """

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OperationalSignal:
    """
    Represents one normalized operational event.

    Signals are immutable evidence inputs for later incident
    correlation and root-cause reasoning.

    Examples include:

    - GitHub code changes
    - Docker builds
    - Kubernetes deployments
    - Terraform changes
    - monitoring alerts
    - health degradation
    - remediation attempts
    - rollback events

    The signal model intentionally does not perform correlation.
    It only provides a consistent representation of evidence.
    """

    def __init__(
        self,
        *,
        signal_type: SignalType,
        source: str,
        resource: str,
        severity: SignalSeverity = SignalSeverity.INFO,
        message: str = "",
        signal_id: Optional[str] = None,
        agent: Optional[str] = None,
        environment: Optional[str] = None,
        incident_id: Optional[str] = None,
        correlation_key: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        occurred_at: Optional[str] = None,
        created_at: Optional[str] = None,
    ) -> None:
        if not source.strip():
            raise ValueError(
                "Signal source cannot be empty"
            )

        if not resource.strip():
            raise ValueError(
                "Signal resource cannot be empty"
            )

        self.signal_id = (
            signal_id
            or str(uuid4())
        )

        self.signal_type = signal_type
        self.source = source
        self.resource = resource
        self.severity = severity
        self.message = message

        self.agent = agent
        self.environment = environment
        self.incident_id = incident_id
        self.correlation_key = correlation_key

        self.metadata = dict(
            metadata or {}
        )

        now = self._timestamp()

        self.occurred_at = (
            occurred_at or now
        )

        self.created_at = (
            created_at or now
        )

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(
            timezone.utc
        ).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the signal into a persistence-safe dictionary.
        """

        return {
            "signal_id": self.signal_id,
            "signal_type": self.signal_type.value,
            "source": self.source,
            "resource": self.resource,
            "severity": self.severity.value,
            "message": self.message,
            "agent": self.agent,
            "environment": self.environment,
            "incident_id": self.incident_id,
            "correlation_key": self.correlation_key,
            "metadata": dict(
                self.metadata
            ),
            "occurred_at": self.occurred_at,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "OperationalSignal":
        """
        Reconstruct an OperationalSignal from serialized data.
        """

        return cls(
            signal_id=data.get(
                "signal_id"
            ),
            signal_type=SignalType(
                data.get(
                    "signal_type",
                    SignalType.UNKNOWN.value,
                )
            ),
            source=data["source"],
            resource=data["resource"],
            severity=SignalSeverity(
                data.get(
                    "severity",
                    SignalSeverity.INFO.value,
                )
            ),
            message=data.get(
                "message",
                "",
            ),
            agent=data.get(
                "agent"
            ),
            environment=data.get(
                "environment"
            ),
            incident_id=data.get(
                "incident_id"
            ),
            correlation_key=data.get(
                "correlation_key"
            ),
            metadata=data.get(
                "metadata",
                {},
            ),
            occurred_at=data.get(
                "occurred_at"
            ),
            created_at=data.get(
                "created_at"
            ),
        )