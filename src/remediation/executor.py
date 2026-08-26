from typing import Any, Dict, Optional

from src.approval.approval_manager import ApprovalManager
from src.remediation.escalation import (
    RemediationEscalationPolicy,
)
from src.remediation.retry_policy import (
    RemediationRetryPolicy,
)
from src.remediation.rollback_policy import (
    RemediationRollbackPolicy,
)
from src.remediation.verifier import RemediationVerifier


class RemediationExecutor:
    """
    Controls execution of approved remediation workflows.

    The executor never performs uncontrolled retry or rollback.

    Lifecycle:

    Approved remediation
    -> controlled execution
    -> post-remediation verification
    -> escalation decision
    -> bounded retry eligibility
    -> rollback recommendation

    Retry and rollback decisions are advisory/control-plane
    decisions only. They never trigger another execution
    automatically.
    """

    def __init__(
        self,
        orchestrator: Any,
        approval_manager: ApprovalManager,
        verifier: Optional[RemediationVerifier] = None,
        escalation_policy: Optional[
            RemediationEscalationPolicy
        ] = None,
        retry_policy: Optional[
            RemediationRetryPolicy
        ] = None,
        rollback_policy: Optional[
            RemediationRollbackPolicy
        ] = None,
    ) -> None:
        self.orchestrator = orchestrator
        self.approval_manager = approval_manager

        self.verifier = (
            verifier
            or RemediationVerifier()
        )

        self.escalation_policy = (
            escalation_policy
            or RemediationEscalationPolicy()
        )

        self.retry_policy = (
            retry_policy
            or RemediationRetryPolicy()
        )

        self.rollback_policy = (
            rollback_policy
            or RemediationRollbackPolicy()
        )

    def execute(
        self,
        approval_id: str,
        *,
        after_health: Optional[
            Dict[str, Any]
        ] = None,
        retry_count: int = 0,
        rollback_available: bool = False,
    ) -> Dict[str, Any]:
        """
        Resume an approved remediation workflow.

        Pending, rejected, unknown, or otherwise unapproved
        requests cannot reach execution.

        When after_health is supplied:

        1. Verify post-remediation health.
        2. Determine whether escalation is required.
        3. Determine whether a bounded retry may be requested.
        4. Determine whether rollback should be recommended.

        No retry or rollback is executed automatically.
        """

        approval = (
            self.approval_manager
            .get_request(approval_id)
        )

        if approval is None:
            return {
                "status": "approval_not_found",
                "approval_id": approval_id,
                "message": (
                    "Approval request was not found"
                ),
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
                "message": (
                    "Remediation was rejected"
                ),
            }

        if not self.approval_manager.can_execute(
            approval_id
        ):
            return {
                "status": "not_approved",
                "approval_id": approval_id,
                "message": (
                    "Remediation is not approved "
                    "for execution"
                ),
            }

        request = approval["request"]

        # -----------------------------------------------------
        # CONTROLLED REMEDIATION EXECUTION
        # -----------------------------------------------------

        result = self.orchestrator.route(
            request=request,
            approval_id=approval_id,
        )

        response = {
            "status": "executed",
            "approval_id": approval_id,
            "result": result,
        }

        # Preserve compatibility with callers that only want
        # controlled execution and no verification lifecycle.
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

        # -----------------------------------------------------
        # POST-REMEDIATION VERIFICATION
        # -----------------------------------------------------

        verification = self.verifier.verify(
            before=before_health,
            after=after_health,
        )

        # -----------------------------------------------------
        # ESCALATION
        # -----------------------------------------------------

        escalation = (
            self.escalation_policy
            .evaluate(verification)
        )

        # -----------------------------------------------------
        # BOUNDED RETRY DECISION
        # -----------------------------------------------------

        retry = self.retry_policy.evaluate(
            escalation,
            retry_count=retry_count,
        )

        # -----------------------------------------------------
        # ROLLBACK DECISION
        # -----------------------------------------------------

        rollback = self.rollback_policy.evaluate(
            verification=verification,
            retry=retry,
            rollback_available=rollback_available,
        )

        return {
            **response,
            "verification": verification,
            "escalation": escalation,
            "retry": retry,
            "rollback": rollback,
        }