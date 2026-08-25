from typing import Any, Dict


class RemediationVerifier:
    """
    Verifies whether a remediation actually improved system health.

    The verifier compares health state before and after remediation
    and returns a structured recovery outcome.
    """

    SUCCESS_STATUSES = {
        "healthy",
        "degraded",
    }

    def verify(
        self,
        before: Dict[str, Any],
        after: Dict[str, Any],
    ) -> Dict[str, Any]:
        before_status = before.get(
            "status",
            "unknown",
        )
        after_status = after.get(
            "status",
            "unknown",
        )

        before_score = before.get(
            "score",
            0,
        )
        after_score = after.get(
            "score",
            0,
        )

        before_reasons = before.get(
            "reasons",
            [],
        )
        after_reasons = after.get(
            "reasons",
            [],
        )

        score_change = (
            after_score - before_score
        )

        recovered = (
            after_status in self.SUCCESS_STATUSES
            and after_score > before_score
        )

        if after_status == "healthy":
            outcome = "recovered"

        elif recovered:
            outcome = "improved"

        elif (
            after_status == before_status
            and after_score == before_score
        ):
            outcome = "unchanged"

        else:
            outcome = "failed"

        return {
            "verified": True,
            "recovered": recovered,
            "outcome": outcome,
            "before_status": before_status,
            "after_status": after_status,
            "before_score": before_score,
            "after_score": after_score,
            "score_change": score_change,
            "before_reasons": before_reasons,
            "after_reasons": after_reasons,
        }