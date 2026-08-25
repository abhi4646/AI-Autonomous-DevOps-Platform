from typing import Any, Dict, Optional

from src.approval.approval_manager import ApprovalManager
from src.remediation.verifier import RemediationVerifier


class RemediationExecutor:
    """
    Controls execution of approved remediation workflows.

    This component never performs remediation directly.
    It validates the associated approval and then delegates
    execution through the platform orchestrator.

    When post-remediation health information is supplied,
    the execution result is also verified against the health
    state that existed when remediation was requested.
    """

    def __init__(
        self,
        orchestrator: Any,
        approval_manager: ApprovalManager,
        verifier: Optional[RemediationVerifier] = None,
    ) -> None:
        self.orchestrator = orchestrator
        self.approval_manager = approval_manager
        self.verifier = verifier or RemediationVerifier()

    def execute(
        self,
        approval_id: str,
        *,
        after_health: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Resume an approved remediation workflow.

        Pending, rejected, and unknown approvals are never
        allowed to reach agent execution.

        If after_health is supplied, compare it with the
        pre-remediation health snapshot stored in approval
        metadata.
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
                "message": (
                    "Remediation approval is still pending"
                ),
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

        response = {
            "status": "executed",
            "approval_id": approval_id,
            "result": result,
        }

        if after_health is None:
            return response

        metadata = approval.get(
            "metadata",
            {},
        )

        before_health = {
            "status": metadata.get(
                "health_status",
                "unknown",
            ),
            "score": metadata.get(
                "health_score",
                0,
            ),
            "reasons": metadata.get(
                "reasons",
                [],
            ),
        }

        verification = self.verifier.verify(
            before=before_health,
            after=after_health,
        )

        return {
            **response,
            "verification": verification,
        }