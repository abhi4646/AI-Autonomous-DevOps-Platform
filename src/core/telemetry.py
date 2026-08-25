from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4


@dataclass
class ExecutionTelemetry:
    execution_id: str
    request: str
    agent: str
    status: str
    started_at: str
    finished_at: Optional[str] = None
    duration_ms: Optional[float] = None
    command: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[dict] = None

    @classmethod
    def start(
        cls,
        request: str,
        agent: str,
        command: Optional[Any] = None,
        metadata: Optional[dict] = None,
    ) -> "ExecutionTelemetry":
        return cls(
            execution_id=str(uuid4()),
            request=request,
            agent=agent,
            status="running",
            started_at=datetime.now(
                timezone.utc
            ).isoformat(),
            command=command,
            metadata=metadata or {},
        )

    def finish(
        self,
        status: str,
        duration_ms: float,
        error: Optional[str] = None,
    ) -> None:
        self.status = status
        self.finished_at = datetime.now(
            timezone.utc
        ).isoformat()
        self.duration_ms = duration_ms
        self.error = error

    def to_dict(self) -> dict:
        return asdict(self)