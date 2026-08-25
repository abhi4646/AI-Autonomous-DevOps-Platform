from typing import Any, Dict, Optional

from src.approval.approval_manager import ApprovalManager
from src.remediation.planner import RemediationPlanner


class RemediationCoordinator:
    """
    Converts health evaluation results into controlled
    remediation workflow decisions.

    Unsafe or impactful remediation is never executed
    automatically. It must pass through human approval.
    """

    def __init__(
        self,
        planner: Optional[RemediationPlanner] = None,
        approval_manager: Optional[ApprovalManager] = None,
    ) -> None:
        self.planner = planner or RemediationPlanner()
        self.approval_manager = approval_manager

    def coordinate(
        self,
        health_result: Dict[str, Any],
        *,
        agent: str = "platform",
    ) -> Dict[str, Any]:
        """
        Convert a health evaluation into a controlled
        remediation workflow decision.
        """

        plan = self.planner.plan(health_result)

        action = plan["action"]

        base_result = {
            "action": action,
            "requires_approval": plan[
                "requires_approval"
            ],
            "health_status": plan["health_status"],
            "health_score": plan["health_score"],
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

        if action == "remediate":
            if self.approval_manager is None:
                return {
                    **base_result,
                    "status": "approval_required",
                    "approval_id": None,
                }

            reason_text = "; ".join(
                plan["reasons"]
            )

            request_text = (
                f"Remediate unhealthy agent "
                f"'{agent}' with health score "
                f"{plan['health_score']}"
            )

            approval = (
                self.approval_manager.create_request(
                    request=request_text,
                    action="remediate",
                    agent=agent,
                    risk="high",
                    metadata={
                        "health_status": (
                            plan["health_status"]
                        ),
                        "health_score": (
                            plan["health_score"]
                        ),
                        "reasons": plan["reasons"],
                        "remediation_action": action,
                    },
                )
            )

            return {
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

        return {
            **base_result,
            "status": "no_action",
        }