from typing import Any, Optional

from pydantic import BaseModel, Field


class ExecuteRequest(BaseModel):
    request: str = Field(..., min_length=3)
    approval_id: Optional[str] = None


class ExecuteResponse(BaseModel):
    status: str
    request: Optional[str] = None
    agent: Optional[str] = None
    risk: Optional[str] = None
    message: Optional[str] = None
    approval_id: Optional[str] = None
    result: Optional[Any] = None


class ApprovalDecision(BaseModel):
    approval_id: str = Field(..., min_length=1)
    decided_by: str = Field(..., min_length=1)
    decision: str = Field(
        ...,
        pattern="^(approved|rejected)$",
    )
    reason: Optional[str] = None


class OperationalSignalRequest(BaseModel):
    signal_id: str = Field(..., min_length=1)
    signal_type: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    resource: str = Field(..., min_length=1)
    severity: str = Field(..., min_length=1)
    message: str = ""
    agent: Optional[str] = None
    environment: Optional[str] = None
    incident_id: Optional[str] = None
    correlation_key: Optional[str] = None
    occurred_at: str = Field(..., min_length=1)
    created_at: Optional[str] = None
    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )