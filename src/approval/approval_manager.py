from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from src.persistence.database import Database


class ApprovalManager:
    """Manages human approval for AI-generated DevOps actions."""

    VALID_DECISIONS = {"approved", "rejected"}

    def __init__(
        self,
        database: Optional[Database] = None,
    ) -> None:
        self.approvals: Dict[str, Dict[str, Any]] = {}
        self.database = database

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

        if self.database is not None:
            self.database.save_approval(
                approval_id=approval_id,
                request=request,
                agent=agent,
                risk_level=risk,
                status="pending",
            )

        return approval.copy()

    def get_request(
        self,
        approval_id: str,
    ) -> Optional[Dict[str, Any]]:
        approval = self.approvals.get(approval_id)

        if approval is not None:
            return approval.copy()

        if self.database is not None:
            stored = self.database.get_approval(approval_id)

            if stored is not None:
                restored = {
                    "approval_id": stored["approval_id"],
                    "request": stored["request"],
                    "action": "review",
                    "agent": stored["agent"],
                    "risk": stored["risk_level"],
                    "status": stored["status"],
                    "created_at": stored["created_at"],
                    "decided_at": stored["decided_at"],
                    "decided_by": stored["decided_by"],
                    "reason": None,
                    "metadata": {},
                }

                self.approvals[approval_id] = restored

                return restored.copy()

        return None

    def get_pending(self) -> List[Dict[str, Any]]:
        if self.database is not None:
            stored_pending = self.database.get_pending_approvals()

            return [
                {
                    "approval_id": item["approval_id"],
                    "request": item["request"],
                    "action": "review",
                    "agent": item["agent"],
                    "risk": item["risk_level"],
                    "status": item["status"],
                    "created_at": item["created_at"],
                    "decided_at": item["decided_at"],
                    "decided_by": item["decided_by"],
                    "reason": None,
                    "metadata": {},
                }
                for item in stored_pending
            ]

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
        approval = self.get_request(approval_id)

        if approval is None:
            raise KeyError(
                f"Approval request not found: {approval_id}"
            )

        decision = decision.lower()

        if decision not in self.VALID_DECISIONS:
            raise ValueError(
                "Decision must be 'approved' or 'rejected'"
            )

        if approval["status"] != "pending":
            raise ValueError(
                "Approval request has already been decided"
            )

        approval["status"] = decision
        approval["decided_by"] = decided_by
        approval["decided_at"] = datetime.now(
            timezone.utc
        ).isoformat()
        approval["reason"] = reason

        self.approvals[approval_id] = approval

        if self.database is not None:
            self.database.update_approval(
                approval_id=approval_id,
                status=decision,
                decided_by=decided_by,
            )

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
        approval = self.get_request(approval_id)

        return bool(
            approval
            and approval["status"] == "approved"
        )

    def can_execute(self, approval_id: str) -> bool:
        return self.is_approved(approval_id)

    def clear(self) -> None:
        self.approvals.clear()