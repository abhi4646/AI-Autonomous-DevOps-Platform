from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4


class ApprovalManager:
    """Manages human approval for AI-generated DevOps actions."""

    VALID_DECISIONS = {"approved", "rejected"}

    def __init__(self) -> None:
        self.approvals: Dict[str, Dict[str, Any]] = {}

    def create_request(
        self,
        request: str,
        action: str,
        agent: str,
        risk: str = "medium",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        approval_id = str(uuid4())

        approval = {
            "approval_id": approval_id,
            "request": request,
            "action": action,
            "agent": agent,
            "risk": risk,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "decided_at": None,
            "decided_by": None,
            "reason": None,
            "metadata": metadata or {},
        }

        self.approvals[approval_id] = approval
        return approval.copy()

    def get_request(self, approval_id: str) -> Optional[Dict[str, Any]]:
        approval = self.approvals.get(approval_id)
        return approval.copy() if approval else None

    def get_pending(self) -> List[Dict[str, Any]]:
        return [
            approval.copy()
            for approval in self.approvals.values()
            if approval["status"] == "pending"
        ]

    def decide(
        self,
        approval_id: str,
        decision: str,
        decided_by: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        if approval_id not in self.approvals:
            raise KeyError(f"Approval request not found: {approval_id}")

        decision = decision.lower()

        if decision not in self.VALID_DECISIONS:
            raise ValueError("Decision must be 'approved' or 'rejected'")

        approval = self.approvals[approval_id]

        if approval["status"] != "pending":
            raise ValueError("Approval request has already been decided")

        approval["status"] = decision
        approval["decided_by"] = decided_by
        approval["decided_at"] = datetime.now(timezone.utc).isoformat()
        approval["reason"] = reason

        return approval.copy()

    def approve(
        self,
        approval_id: str,
        decided_by: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.decide(
            approval_id,
            "approved",
            decided_by,
            reason,
        )

    def reject(
        self,
        approval_id: str,
        decided_by: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.decide(
            approval_id,
            "rejected",
            decided_by,
            reason,
        )

    def is_approved(self, approval_id: str) -> bool:
        approval = self.approvals.get(approval_id)
        return bool(approval and approval["status"] == "approved")

    def can_execute(self, approval_id: str) -> bool:
        return self.is_approved(approval_id)

    def clear(self) -> None:
        self.approvals.clear()