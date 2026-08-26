from typing import Any, Dict


class RemediationRollbackPolicy:
    """
    Determines whether rollback should be proposed after
    remediation and bounded retry attempts fail.

    This policy never performs rollback automatically.
    Rollback always requires explicit human approval.
    """

    def evaluate(
        self,
        *,
        verification: Dict[str, Any],
        retry: Dict[str, Any],
        rollback_available: bool,
    ) -> Dict[str, Any]:
        """
        Evaluate whether rollback should be proposed.
        """

        if verification.get(
            "recovered",
            False,
        ):
            return {
                "status": "rollback_not_required",
                "rollback_recommended": False,
                "requires_approval": False,
                "reason": (
                    "System recovery was verified"
                ),
            }

        if retry.get("retry_allowed", False):
            return {
                "status": "retry_first",
                "rollback_recommended": False,
                "requires_approval": False,
                "reason": (
                    "A bounded remediation retry "
                    "is still available"
                ),
            }

        if not rollback_available:
            return {
                "status": "rollback_unavailable",
                "rollback_recommended": False,
                "requires_approval": True,
                "reason": (
                    "Recovery failed and no rollback "
                    "strategy is available"
                ),
            }

        return {
            "status": "rollback_recommended",
            "rollback_recommended": True,
            "requires_approval": True,
            "reason": (
                "Remediation retries are exhausted "
                "and rollback is available"
            ),
        }