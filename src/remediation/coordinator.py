from typing import Any, Dict, Optional

from src.approval.approval_manager import ApprovalManager
from src.incident.manager import IncidentManager
from src.incident.model import (
    IncidentSeverity,
    IncidentStatus,
)
from src.remediation.planner import RemediationPlanner


class RemediationCoordinator:
    """
    Converts health evaluation results into controlled
    remediation workflow decisions.

    Unsafe or impactful remediation is never executed
    automatically. It must pass through human approval.

    When an IncidentManager is supplied, unhealthy health
    evaluations are also tracked through a persistent
    incident lifecycle.
    """

    def __init__(
        self,
        planner: Optional[RemediationPlanner] = None,
        approval_manager: Optional[ApprovalManager] = None,
        incident_manager: Optional[IncidentManager] = None,
    ) -> None:
        self.planner = planner or RemediationPlanner()
        self.approval_manager = approval_manager
        self.incident_manager = incident_manager

    @staticmethod
    def _severity_for_health(
        health_result: Dict[str, Any],
    ) -> IncidentSeverity:
        status = health_result.get(
            "status",
            "unknown",
        )

        score = health_result.get(
            "score"
        )

        if status == "unhealthy":
            if isinstance(score, (int, float)) and score <= 25:
                return IncidentSeverity.CRITICAL

            return IncidentSeverity.HIGH

        if status == "degraded":
            return IncidentSeverity.MEDIUM

        return IncidentSeverity.LOW

    def coordinate(
        self,
        health_result: Dict[str, Any],
        *,
        agent: str = "platform",
        rollback_available: bool = False,
    ) -> Dict[str, Any]:
        """
        Convert a health evaluation into a controlled
        remediation workflow decision.

        If incident persistence is configured, unhealthy
        remediation workflows are represented by a stable
        incident ID.
        """

        plan = self.planner.plan(
            health_result
        )

        action = plan["action"]

        base_result = {
            "action": action,
            "requires_approval": plan[
                "requires_approval"
            ],
            "health_status": plan[
                "health_status"
            ],
            "health_score": plan[
                "health_score"
            ],
            "reasons": plan["reasons"],
        }

        if action == "observe":
            return {
                **base_result,
                "status": "observing",
            }

        if action == "recommend":
            return {
                **base_result,
                "status": "recommendation",
            }

        if action != "remediate":
            return {
                **base_result,
                "status": "no_action",
            }

        incident = None

        if self.incident_manager is not None:
            incident = self.incident_manager.create(
                title=(
                    f"Unhealthy agent: {agent}"
                ),
                agent=agent,
                severity=self._severity_for_health(
                    health_result
                ),
                health_snapshot={
                    "status": plan[
                        "health_status"
                    ],
                    "score": plan[
                        "health_score"
                    ],
                    "reasons": plan[
                        "reasons"
                    ],
                },
                rollback_available=(
                    rollback_available
                ),
                metadata={
                    "remediation_action": action,
                },
            )

            self.incident_manager.transition(
                incident.incident_id,
                IncidentStatus.INVESTIGATING,
            )

        if self.approval_manager is None:
            result = {
                **base_result,
                "status": "approval_required",
                "approval_id": None,
            }

            if incident is not None:
                result["incident_id"] = (
                    incident.incident_id
                )

            return result

        reason_text = "; ".join(
            plan["reasons"]
        )

        request_text = (
            f"Remediate unhealthy agent "
            f"'{agent}' with health score "
            f"{plan['health_score']}"
        )

        approval_metadata = {
            "health_status": plan[
                "health_status"
            ],
            "health_score": plan[
                "health_score"
            ],
            "reasons": plan[
                "reasons"
            ],
            "remediation_action": action,
        }

        if incident is not None:
            approval_metadata[
                "incident_id"
            ] = incident.incident_id

        approval = (
            self.approval_manager
            .create_request(
                request=request_text,
                action="remediate",
                agent=agent,
                risk="high",
                metadata=approval_metadata,
            )
        )

        if incident is not None:
            self.incident_manager.set_approval(
                incident.incident_id,
                approval["approval_id"],
            )

            self.incident_manager.transition(
                incident.incident_id,
                IncidentStatus.PENDING_APPROVAL,
            )

        result = {
            **base_result,
            "status": "pending_approval",
            "approval_id": approval[
                "approval_id"
            ],
            "approval_status": approval[
                "status"
            ],
            "reason": reason_text,
        }

        if incident is not None:
            result["incident_id"] = (
                incident.incident_id
            )

        return result