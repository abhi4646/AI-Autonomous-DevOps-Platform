from typing import Any, Dict


class RemediationEscalationPolicy:
    """
    Determines what should happen when post-remediation
    verification does not confirm recovery.

    This component never executes another remediation.
    It only produces a controlled escalation decision.

    Automatic retry and rollback are intentionally kept
    outside this policy so failed remediation cannot create
    an uncontrolled execution loop.
    """

    ESCALATION_OUTCOMES = {
        "failed",
        "unchanged",
    }

    def evaluate(
        self,
        verification: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Evaluate a remediation verification result.

        Successful recovery closes the remediation workflow.

        Failed or unchanged health requires escalation to a
        human operator. No automatic retry is authorized.
        """

        outcome = verification.get(
            "outcome",
            "unknown",
        )

        recovered = verification.get(
            "recovered",
            False,
        )

        score_change = verification.get(
            "score_change",
            0,
        )

        after_status = verification.get(
            "after_status",
            "unknown",
        )

        if recovered:
            return {
                "status": "resolved",
                "action": "close",
                "escalated": False,
                "retry_allowed": False,
                "requires_human": False,
                "verification_outcome": outcome,
                "after_status": after_status,
                "score_change": score_change,
                "reason": (
                    "Post-remediation verification "
                    "confirmed recovery"
                ),
            }

        if outcome in self.ESCALATION_OUTCOMES:
            return {
                "status": "escalated",
                "action": "human_review",
                "escalated": True,
                "retry_allowed": False,
                "requires_human": True,
                "verification_outcome": outcome,
                "after_status": after_status,
                "score_change": score_change,
                "reason": (
                    "Remediation did not restore "
                    "acceptable system health"
                ),
            }

        return {
            "status": "verification_inconclusive",
            "action": "human_review",
            "escalated": True,
            "retry_allowed": False,
            "requires_human": True,
            "verification_outcome": outcome,
            "after_status": after_status,
            "score_change": score_change,
            "reason": (
                "Remediation verification was "
                "inconclusive"
            ),
        }