from typing import Any, Dict, Optional

from src.approval.approval_manager import ApprovalManager
from src.incident.manager import IncidentManager
from src.incident.model import IncidentStatus
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

    Lifecycle:

    Approved remediation
    -> controlled execution
    -> post-remediation verification
    -> escalation decision
    -> bounded retry eligibility
    -> rollback recommendation

    When IncidentManager is configured, the same workflow
    advances a persistent incident through the matching
    lifecycle states.

    Retry and rollback decisions never trigger additional
    execution automatically.
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
        incident_manager: Optional[
            IncidentManager
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

        self.incident_manager = (
            incident_manager
        )

    def _incident_id_from_approval(
        self,
        approval: Dict[str, Any],
    ) -> Optional[str]:
        metadata = approval.get(
            "metadata",
            {},
        )

        return metadata.get(
            "incident_id"
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

        incident_id = (
            self._incident_id_from_approval(
                approval
            )
        )

        if (
            incident_id is not None
            and self.incident_manager is not None
        ):
            incident = self.incident_manager.get(
                incident_id
            )

            if (
                incident is not None
                and incident.status
                == IncidentStatus.PENDING_APPROVAL
            ):
                self.incident_manager.transition(
                    incident_id,
                    IncidentStatus.REMEDIATING,
                )

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

        if incident_id is not None:
            response["incident_id"] = (
                incident_id
            )

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

        if (
            incident_id is not None
            and self.incident_manager is not None
        ):
            incident = self.incident_manager.get(
                incident_id
            )

            if (
                incident is not None
                and incident.status
                == IncidentStatus.REMEDIATING
            ):
                self.incident_manager.transition(
                    incident_id,
                    IncidentStatus.VERIFYING,
                )

        verification = self.verifier.verify(
            before=before_health,
            after=after_health,
        )

        escalation = (
            self.escalation_policy
            .evaluate(verification)
        )

        retry = self.retry_policy.evaluate(
            escalation,
            retry_count=retry_count,
        )

        rollback = self.rollback_policy.evaluate(
            verification=verification,
            retry=retry,
            rollback_available=rollback_available,
        )

        if (
            incident_id is not None
            and self.incident_manager is not None
        ):
            self.incident_manager.set_retry_count(
                incident_id,
                retry_count,
            )

            self.incident_manager.set_rollback_available(
                incident_id,
                rollback_available,
            )

            if verification.get(
                "recovered",
                False,
            ):
                self.incident_manager.transition(
                    incident_id,
                    IncidentStatus.RESOLVED,
                )

            elif retry.get(
                "retry_allowed",
                False,
            ):
                self.incident_manager.transition(
                    incident_id,
                    IncidentStatus.RETRY_PENDING,
                )

            elif rollback.get(
                "rollback_recommended",
                False,
            ):
                self.incident_manager.transition(
                    incident_id,
                    IncidentStatus.ROLLBACK_PENDING,
                )

            else:
                self.incident_manager.transition(
                    incident_id,
                    IncidentStatus.ESCALATED,
                )

        return {
            **response,
            "verification": verification,
            "escalation": escalation,
            "retry": retry,
            "rollback": rollback,
        }