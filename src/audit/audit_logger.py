from datetime import datetime, timezone
from typing import Any, Dict, List
import uuid


class AuditLogger:
    """
    Records structured audit events for autonomous DevOps decisions
    and agent executions.
    """

    def __init__(self):
        self.events: List[Dict[str, Any]] = []

    def log(
        self,
        request: str,
        action: str,
        agent: str = "unknown",
        allowed: bool = True,
        risk: str = "low",
        reason: str = "",
        metadata: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:

        event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request": request,
            "action": action,
            "agent": agent,
            "allowed": allowed,
            "risk": risk,
            "reason": reason,
            "metadata": metadata or {},
        }

        self.events.append(event)

        return event

    def get_events(self) -> List[Dict[str, Any]]:
        return list(self.events)

    def get_blocked_events(self) -> List[Dict[str, Any]]:
        return [
            event
            for event in self.events
            if not event["allowed"]
        ]

    def clear(self) -> None:
        self.events.clear()