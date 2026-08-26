from typing import Any, Dict


class RemediationRetryPolicy:
    """
    Controls whether a failed remediation may be retried.

    Retries are deliberately bounded. This policy only makes
    a decision; it never executes remediation itself.
    """

    def __init__(
        self,
        max_retries: int = 1,
    ) -> None:
        if max_retries < 0:
            raise ValueError(
                "max_retries cannot be negative"
            )

        self.max_retries = max_retries

    def evaluate(
        self,
        escalation: Dict[str, Any],
        *,
        retry_count: int = 0,
    ) -> Dict[str, Any]:
        """
        Determine whether another remediation attempt is safe.

        A retry is considered only after an escalation and is
        limited by max_retries.
        """

        if retry_count < 0:
            raise ValueError(
                "retry_count cannot be negative"
            )

        if not escalation.get(
            "escalated",
            False,
        ):
            return {
                "status": "retry_not_required",
                "retry_allowed": False,
                "retry_count": retry_count,
                "max_retries": self.max_retries,
                "requires_approval": False,
                "reason": (
                    "Remediation did not require escalation"
                ),
            }

        if retry_count >= self.max_retries:
            return {
                "status": "retry_exhausted",
                "retry_allowed": False,
                "retry_count": retry_count,
                "max_retries": self.max_retries,
                "requires_approval": True,
                "reason": (
                    "Maximum remediation retry count reached"
                ),
            }

        return {
            "status": "retry_available",
            "retry_allowed": True,
            "retry_count": retry_count,
            "next_retry_count": retry_count + 1,
            "max_retries": self.max_retries,
            "requires_approval": True,
            "reason": (
                "One bounded remediation retry is available"
            ),
        }