from typing import Any, Dict

from src.approval.approval_manager import ApprovalManager


class RemediationExecutor:
    """
    Controls execution of approved remediation workflows.

    This component never performs remediation directly.
    It validates the associated approval and then delegates
    execution through the platform orchestrator.
    """

    def __init__(
        self,
        orchestrator: Any,
        approval_manager: ApprovalManager,
    ) -> None:
        self.orchestrator = orchestrator
        self.approval_manager = approval_manager

    def execute(
        self,
        approval_id: str,
    ) -> Dict[str, Any]:
        """
        Resume an approved remediation workflow.

        Pending, rejected, and unknown approvals are never
        allowed to reach agent execution.
        """

        approval = self.approval_manager.get_request(
            approval_id
        )

        if approval is None:
            return {
                "status": "approval_not_found",
                "approval_id": approval_id,
                "message": "Approval request was not found",
            }

        if approval["status"] == "pending":
            return {
                "status": "pending_approval",
                "approval_id": approval_id,
                "message": "Remediation approval is still pending",
            }

        if approval["status"] == "rejected":
            return {
                "status": "rejected",
                "approval_id": approval_id,
                "message": "Remediation was rejected",
            }

        if not self.approval_manager.can_execute(
            approval_id
        ):
            return {
                "status": "not_approved",
                "approval_id": approval_id,
                "message": (
                    "Remediation is not approved for execution"
                ),
            }

        request = approval["request"]

        result = self.orchestrator.route(
            request=request,
            approval_id=approval_id,
        )

        return {
            "status": "executed",
            "approval_id": approval_id,
            "result": result,
        }