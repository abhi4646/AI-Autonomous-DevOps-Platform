from typing import Any, Dict, Optional

from src.incident.lifecycle import (
    IncidentLifecycle,
)
from src.incident.model import (
    Incident,
    IncidentSeverity,
    IncidentStatus,
)
from src.persistence.database import Database


class IncidentManager:
    """
    Coordinates persistent incident lifecycle operations.

    The manager provides the boundary between remediation
    workflows and incident persistence.

    All lifecycle transitions pass through IncidentLifecycle
    before being persisted.
    """

    def __init__(
        self,
        database: Database,
        lifecycle: Optional[
            IncidentLifecycle
        ] = None,
    ) -> None:
        self.database = database
        self.lifecycle = (
            lifecycle
            or IncidentLifecycle()
        )

    # ---------------------------------------------------------
    # INCIDENT CREATION
    # ---------------------------------------------------------

    def create(
        self,
        *,
        title: str,
        agent: str,
        severity: IncidentSeverity,
        health_snapshot: Optional[
            Dict[str, Any]
        ] = None,
        approval_id: Optional[str] = None,
        rollback_available: bool = False,
        metadata: Optional[
            Dict[str, Any]
        ] = None,
    ) -> Incident:
        """
        Create and persist a newly detected incident.
        """

        incident = Incident(
            title=title,
            agent=agent,
            severity=severity,
            health_snapshot=health_snapshot,
            approval_id=approval_id,
            rollback_available=(
                rollback_available
            ),
            metadata=metadata,
        )

        self.database.save_incident(
            incident.to_dict()
        )

        return incident

    # ---------------------------------------------------------
    # RETRIEVAL
    # ---------------------------------------------------------

    def get(
        self,
        incident_id: str,
    ) -> Optional[Incident]:
        """
        Retrieve a persisted incident.
        """

        data = self.database.get_incident(
            incident_id
        )

        if data is None:
            return None

        return Incident.from_dict(data)

    # ---------------------------------------------------------
    # LIFECYCLE TRANSITIONS
    # ---------------------------------------------------------

    def transition(
        self,
        incident_id: str,
        target: IncidentStatus,
    ) -> Incident:
        """
        Move an incident through a valid lifecycle transition
        and persist the resulting state.
        """

        incident = self.get(
            incident_id
        )

        if incident is None:
            raise KeyError(
                f"Incident "
                f"'{incident_id}' "
                f"does not exist"
            )

        self.lifecycle.transition(
            incident,
            target,
        )

        self.database.update_incident(
            incident.to_dict()
        )

        return incident

    # ---------------------------------------------------------
    # WORKFLOW CONTEXT
    # ---------------------------------------------------------

    def set_approval(
        self,
        incident_id: str,
        approval_id: str,
    ) -> Incident:
        """
        Associate a remediation approval with an incident.
        """

        incident = self.get(
            incident_id
        )

        if incident is None:
            raise KeyError(
                f"Incident "
                f"'{incident_id}' "
                f"does not exist"
            )

        incident.approval_id = approval_id
        incident.updated_at = (
            incident._timestamp()
        )

        self.database.update_incident(
            incident.to_dict()
        )

        return incident

    def set_retry_count(
        self,
        incident_id: str,
        retry_count: int,
    ) -> Incident:
        """
        Persist the current bounded retry count.
        """

        if retry_count < 0:
            raise ValueError(
                "retry_count cannot be negative"
            )

        incident = self.get(
            incident_id
        )

        if incident is None:
            raise KeyError(
                f"Incident "
                f"'{incident_id}' "
                f"does not exist"
            )

        incident.retry_count = retry_count
        incident.updated_at = (
            incident._timestamp()
        )

        self.database.update_incident(
            incident.to_dict()
        )

        return incident

    def set_rollback_available(
        self,
        incident_id: str,
        rollback_available: bool,
    ) -> Incident:
        """
        Persist whether rollback is available.
        """

        incident = self.get(
            incident_id
        )

        if incident is None:
            raise KeyError(
                f"Incident "
                f"'{incident_id}' "
                f"does not exist"
            )

        incident.rollback_available = (
            rollback_available
        )

        incident.updated_at = (
            incident._timestamp()
        )

        self.database.update_incident(
            incident.to_dict()
        )

        return incident