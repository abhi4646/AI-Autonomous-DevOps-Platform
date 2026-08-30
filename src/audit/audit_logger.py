from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from src.persistence.database import Database


class AuditLogger:
    """
    Records structured audit events for autonomous DevOps decisions
    and agent executions.
    """

    def __init__(
        self,
        database: Optional[Database] = None,
    ):
        self.events: List[Dict[str, Any]] = []
        self.database = database

    def log(
        self,
        request: str,
        action: str,
        agent: str = "unknown",
        allowed: bool = True,
        risk: str = "low",
        reason: str = "",
        metadata: Dict[str, Any] | None = None,
        identity: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        Record one structured audit event.

        Authenticated identity is stored as structured
        metadata. Raw API credentials must never be passed
        to this logger.

        The explicit identity argument is authoritative and
        cannot be overwritten by caller-provided metadata.
        """

        event_metadata = dict(
            metadata or {}
        )

        if identity is not None:
            event_metadata[
                "authenticated_principal"
            ] = dict(identity)

        event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "request": request,
            "action": action,
            "agent": agent,
            "allowed": allowed,
            "risk": risk,
            "reason": reason,
            "metadata": event_metadata,
        }

        self.events.append(event)

        if self.database is not None:
            self.database.save_audit_event(
                event_type=action,
                message=reason or action,
                metadata={
                    "event_id": event["event_id"],
                    "request": request,
                    "agent": agent,
                    "allowed": allowed,
                    "risk": risk,
                    "metadata": event[
                        "metadata"
                    ],
                },
            )

        return event

    def get_events(
        self,
    ) -> List[Dict[str, Any]]:
        return list(self.events)

    def get_blocked_events(
        self,
    ) -> List[Dict[str, Any]]:
        return [
            event
            for event in self.events
            if not event["allowed"]
        ]

    def clear(
        self,
    ) -> None:
        self.events.clear()