from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4


class IncidentStatus(str, Enum):
    DETECTED = "detected"
    INVESTIGATING = "investigating"
    PENDING_APPROVAL = "pending_approval"
    REMEDIATING = "remediating"
    VERIFYING = "verifying"
    RETRY_PENDING = "retry_pending"
    ROLLBACK_PENDING = "rollback_pending"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class IncidentSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Incident:
    """
    Represents one persistent operational incident.

    An incident provides a stable identity across detection,
    investigation, approval, remediation, verification,
    retry, rollback, resolution, and escalation.
    """

    def __init__(
        self,
        *,
        title: str,
        agent: str,
        severity: IncidentSeverity,
        health_snapshot: Optional[
            Dict[str, Any]
        ] = None,
        incident_id: Optional[str] = None,
        status: IncidentStatus = (
            IncidentStatus.DETECTED
        ),
        approval_id: Optional[str] = None,
        retry_count: int = 0,
        rollback_available: bool = False,
        metadata: Optional[
            Dict[str, Any]
        ] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        resolved_at: Optional[str] = None,
    ) -> None:
        if not title.strip():
            raise ValueError(
                "Incident title cannot be empty"
            )

        if not agent.strip():
            raise ValueError(
                "Incident agent cannot be empty"
            )

        if retry_count < 0:
            raise ValueError(
                "retry_count cannot be negative"
            )

        self.incident_id = (
            incident_id
            or str(uuid4())
        )

        self.title = title
        self.agent = agent
        self.severity = severity
        self.status = status

        self.health_snapshot = (
            health_snapshot or {}
        )

        self.approval_id = approval_id
        self.retry_count = retry_count

        self.rollback_available = (
            rollback_available
        )

        self.metadata = metadata or {}

        now = self._timestamp()

        self.created_at = (
            created_at or now
        )

        self.updated_at = (
            updated_at or now
        )

        self.resolved_at = resolved_at

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(
            timezone.utc
        ).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "title": self.title,
            "agent": self.agent,
            "severity": self.severity.value,
            "status": self.status.value,
            "health_snapshot": (
                self.health_snapshot
            ),
            "approval_id": self.approval_id,
            "retry_count": self.retry_count,
            "rollback_available": (
                self.rollback_available
            ),
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "resolved_at": self.resolved_at,
        }

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "Incident":
        return cls(
            incident_id=data["incident_id"],
            title=data["title"],
            agent=data["agent"],
            severity=IncidentSeverity(
                data["severity"]
            ),
            status=IncidentStatus(
                data["status"]
            ),
            health_snapshot=data.get(
                "health_snapshot",
                {},
            ),
            approval_id=data.get(
                "approval_id"
            ),
            retry_count=data.get(
                "retry_count",
                0,
            ),
            rollback_available=data.get(
                "rollback_available",
                False,
            ),
            metadata=data.get(
                "metadata",
                {},
            ),
            created_at=data.get(
                "created_at"
            ),
            updated_at=data.get(
                "updated_at"
            ),
            resolved_at=data.get(
                "resolved_at"
            ),
        )