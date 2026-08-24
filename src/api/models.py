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