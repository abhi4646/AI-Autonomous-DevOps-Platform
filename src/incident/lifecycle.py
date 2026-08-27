from typing import Dict, Set

from src.incident.model import (
    Incident,
    IncidentStatus,
)


class InvalidIncidentTransition(ValueError):
    """Raised when an incident transition is invalid."""


class IncidentLifecycle:
    """
    Enforces valid incident state transitions.

    State changes are explicit and deterministic.
    """

    ALLOWED_TRANSITIONS: Dict[
        IncidentStatus,
        Set[IncidentStatus],
    ] = {
        IncidentStatus.DETECTED: {
            IncidentStatus.INVESTIGATING,
            IncidentStatus.ESCALATED,
        },
        IncidentStatus.INVESTIGATING: {
            IncidentStatus.PENDING_APPROVAL,
            IncidentStatus.RESOLVED,
            IncidentStatus.ESCALATED,
        },
        IncidentStatus.PENDING_APPROVAL: {
            IncidentStatus.REMEDIATING,
            IncidentStatus.ESCALATED,
        },
        IncidentStatus.REMEDIATING: {
            IncidentStatus.VERIFYING,
            IncidentStatus.ESCALATED,
        },
        IncidentStatus.VERIFYING: {
            IncidentStatus.RESOLVED,
            IncidentStatus.RETRY_PENDING,
            IncidentStatus.ROLLBACK_PENDING,
            IncidentStatus.ESCALATED,
        },
        IncidentStatus.RETRY_PENDING: {
            IncidentStatus.REMEDIATING,
            IncidentStatus.ROLLBACK_PENDING,
            IncidentStatus.ESCALATED,
        },
        IncidentStatus.ROLLBACK_PENDING: {
            IncidentStatus.VERIFYING,
            IncidentStatus.RESOLVED,
            IncidentStatus.ESCALATED,
        },
        IncidentStatus.RESOLVED: set(),
        IncidentStatus.ESCALATED: set(),
    }

    def can_transition(
        self,
        incident: Incident,
        target: IncidentStatus,
    ) -> bool:
        return target in self.ALLOWED_TRANSITIONS[
            incident.status
        ]

    def transition(
        self,
        incident: Incident,
        target: IncidentStatus,
    ) -> Incident:
        if not self.can_transition(
            incident,
            target,
        ):
            raise InvalidIncidentTransition(
                f"Cannot transition incident "
                f"from '{incident.status.value}' "
                f"to '{target.value}'"
            )

        incident.status = target
        incident.updated_at = (
            incident._timestamp()
        )

        if target == IncidentStatus.RESOLVED:
            incident.resolved_at = (
                incident.updated_at
            )

        return incident