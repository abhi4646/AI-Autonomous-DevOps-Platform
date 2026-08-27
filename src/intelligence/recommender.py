from typing import Any, Dict, Optional

from src.intelligence.context import DecisionContext
from src.intelligence.outcomes import (
    HistoricalOutcomeAnalyzer,
)
from src.intelligence.scorer import DecisionScorer


class RecommendationEngine:
    """
    Produces an explainable operational recommendation from
    decision context, risk scoring, and historical outcomes.

    This engine never executes the recommendation.

    Production-changing operations remain conservative even
    when current health and historical confidence appear good.
    """

    MUTATING_KEYWORDS = {
        "deploy",
        "apply",
        "delete",
        "destroy",
        "remove",
        "restart",
        "terminate",
        "scale",
        "rollback",
        "update",
        "modify",
        "change",
        "create",
        "push",
        "merge",
        "write",
    }

    def __init__(
        self,
        scorer: Optional[
            DecisionScorer
        ] = None,
        outcome_analyzer: Optional[
            HistoricalOutcomeAnalyzer
        ] = None,
    ) -> None:
        self.scorer = (
            scorer
            or DecisionScorer()
        )

        self.outcome_analyzer = (
            outcome_analyzer
            or HistoricalOutcomeAnalyzer()
        )

    def recommend(
        self,
        context: DecisionContext,
    ) -> Dict[str, Any]:
        score = self.scorer.score(
            context
        )

        history = (
            self.outcome_analyzer
            .analyze(context)
        )

        recommendation = "review"
        requires_approval = True

        # -----------------------------------------------------
        # HARD HISTORICAL SAFETY SIGNALS
        # -----------------------------------------------------

        if history["prefer_rollback"]:
            recommendation = "rollback"
            requires_approval = True

        elif history["require_escalation"]:
            recommendation = "escalate"
            requires_approval = True

        # -----------------------------------------------------
        # INCIDENT / RETRY STATE
        # -----------------------------------------------------

        elif (
            context.retry_count > 0
            and context.rollback_available
            and score["risk_level"]
            in {"high", "critical"}
        ):
            recommendation = "rollback"
            requires_approval = True

        elif (
            context.retry_count > 0
            and not context.rollback_available
        ):
            recommendation = "escalate"
            requires_approval = True

        # -----------------------------------------------------
        # RISK-BASED DECISION
        # -----------------------------------------------------

        elif score["risk_level"] == "critical":
            recommendation = "escalate"
            requires_approval = True

        elif score["risk_level"] == "high":
            recommendation = "review"
            requires_approval = True

        elif (
            context.health_status == "unhealthy"
        ):
            recommendation = "remediate"
            requires_approval = True

        elif (
            score["risk_level"] == "medium"
        ):
            recommendation = "review"
            requires_approval = True

        elif (
            score["risk_level"] == "low"
            and score["confidence"] >= 0.80
            and not context.is_production
        ):
            recommendation = "execute"
            requires_approval = False

        elif (
            context.health_status == "healthy"
            and score["risk_level"] == "low"
        ):
            recommendation = "observe"
            requires_approval = False

        # -----------------------------------------------------
        # PRODUCTION SAFETY OVERRIDE
        # -----------------------------------------------------

        # A production-changing request must never become an
        # autonomous execute OR a passive observe decision merely
        # because current health happens to be good.
        #
        # Example:
        #     "Deploy Kubernetes service"
        #
        # Even with healthy telemetry and high confidence,
        # deployment changes production state and therefore
        # requires human review.
        if (
            context.is_production
            and self._is_mutating_request(
                context.request
            )
            and recommendation
            in {"execute", "observe"}
        ):
            recommendation = "review"
            requires_approval = True

        explanation = self._explanation(
            recommendation,
            context,
            score,
            history,
        )

        return {
            "recommendation": recommendation,
            "requires_approval": (
                requires_approval
            ),
            "risk_score": score[
                "risk_score"
            ],
            "risk_level": score[
                "risk_level"
            ],
            "confidence": score[
                "confidence"
            ],
            "risk_factors": score[
                "risk_factors"
            ],
            "confidence_factors": score[
                "confidence_factors"
            ],
            "historical_outcomes": history,
            "explanation": explanation,
        }

    @classmethod
    def _is_mutating_request(
        cls,
        request: str,
    ) -> bool:
        """
        Return True when the request appears capable of
        changing infrastructure, code, configuration, or
        runtime state.
        """

        request_lower = request.lower()

        return any(
            keyword in request_lower
            for keyword in cls.MUTATING_KEYWORDS
        )

    @staticmethod
    def _explanation(
        recommendation: str,
        context: DecisionContext,
        score: Dict[str, Any],
        history: Dict[str, Any],
    ) -> str:
        reasons = []

        if context.is_production:
            reasons.append(
                "production environment"
            )

        if context.incident_severity:
            reasons.append(
                f"{context.incident_severity} "
                f"incident severity"
            )

        if context.health_status != "unknown":
            reasons.append(
                f"{context.health_status} "
                f"system health"
            )

        if context.retry_count > 0:
            reasons.append(
                f"{context.retry_count} "
                f"previous retry attempt(s)"
            )

        if history["avoid_repeat"]:
            reasons.append(
                "historical remediation failures"
            )

        if context.rollback_available:
            reasons.append(
                "rollback is available"
            )

        reasons.append(
            f"{score['risk_level']} risk"
        )

        reasons.append(
            f"{score['confidence']:.2f} confidence"
        )

        reason_text = ", ".join(
            reasons
        )

        return (
            f"Recommendation '{recommendation}' "
            f"was selected based on {reason_text}."
        )