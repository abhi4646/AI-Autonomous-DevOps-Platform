from typing import Any, Dict, List

from src.intelligence.context import DecisionContext


class DecisionScorer:
    """
    Scores operational risk and decision confidence using
    normalized DecisionContext signals.

    The scorer is deterministic and side-effect free.
    It does not execute agents, create approvals, or modify
    incidents.
    """

    def score(
        self,
        context: DecisionContext,
    ) -> Dict[str, Any]:
        risk_score = 0
        confidence_score = 50

        risk_factors: List[str] = []
        confidence_factors: List[str] = []

        # -----------------------------------------------------
        # ENVIRONMENT RISK
        # -----------------------------------------------------

        if context.is_production:
            risk_score += 25
            risk_factors.append(
                "Production environment increases operational risk"
            )
        elif context.environment.lower() == "staging":
            risk_score += 10
            risk_factors.append(
                "Staging environment carries moderate operational risk"
            )

        # -----------------------------------------------------
        # INCIDENT SEVERITY
        # -----------------------------------------------------

        severity = (
            context.incident_severity
            or ""
        ).lower()

        if severity == "critical":
            risk_score += 30
            risk_factors.append(
                "Critical incident severity"
            )
        elif severity == "high":
            risk_score += 20
            risk_factors.append(
                "High incident severity"
            )
        elif severity == "medium":
            risk_score += 10
            risk_factors.append(
                "Medium incident severity"
            )
        elif severity == "low":
            risk_score += 5
            risk_factors.append(
                "Low incident severity"
            )

        # -----------------------------------------------------
        # HEALTH
        # -----------------------------------------------------

        if context.health_score is not None:
            if context.health_score <= 25:
                risk_score += 20
                risk_factors.append(
                    "Very low health score"
                )
            elif context.health_score <= 50:
                risk_score += 15
                risk_factors.append(
                    "Low health score"
                )
            elif context.health_score <= 75:
                risk_score += 5
                risk_factors.append(
                    "Degraded health score"
                )
            else:
                confidence_score += 5
                confidence_factors.append(
                    "Healthy system score"
                )

        health_status = (
            context.health_status
            or ""
        ).lower()

        if health_status == "unhealthy":
            risk_score += 15
            risk_factors.append(
                "System health is unhealthy"
            )
        elif health_status == "degraded":
            risk_score += 5
            risk_factors.append(
                "System health is degraded"
            )
        elif health_status == "healthy":
            confidence_score += 5
            confidence_factors.append(
                "System health is healthy"
            )

        # -----------------------------------------------------
        # RETRY / ROLLBACK STATE
        # -----------------------------------------------------

        if context.retry_count > 0:
            risk_score += min(
                20,
                10 * context.retry_count,
            )

            risk_factors.append(
                f"Remediation retry count is {context.retry_count}"
            )

        if not context.rollback_available:
            risk_score += 10
            risk_factors.append(
                "Rollback is unavailable"
            )
        else:
            confidence_score += 5
            confidence_factors.append(
                "Rollback is available"
            )

        # -----------------------------------------------------
        # EXECUTION HISTORY
        # -----------------------------------------------------

        if context.previous_executions == 0:
            confidence_score -= 10
            confidence_factors.append(
                "No previous execution history"
            )
        else:
            execution_rate = (
                context.execution_success_rate
            )

            if execution_rate is not None:
                if execution_rate >= 0.90:
                    confidence_score += 15
                    confidence_factors.append(
                        "Strong historical execution success rate"
                    )
                elif execution_rate >= 0.70:
                    confidence_score += 5
                    confidence_factors.append(
                        "Acceptable historical execution success rate"
                    )
                elif execution_rate < 0.50:
                    risk_score += 15
                    confidence_score -= 10
                    risk_factors.append(
                        "Poor historical execution success rate"
                    )

        if context.previous_failures >= 3:
            risk_score += 15
            risk_factors.append(
                "Repeated previous execution failures"
            )
        elif context.previous_failures > 0:
            risk_score += 5
            risk_factors.append(
                "Previous execution failure history"
            )

        # -----------------------------------------------------
        # REMEDIATION HISTORY
        # -----------------------------------------------------

        if context.previous_remediations > 0:
            remediation_rate = (
                context.remediation_success_rate
            )

            if remediation_rate is not None:
                if remediation_rate >= 0.80:
                    confidence_score += 10
                    confidence_factors.append(
                        "Strong historical remediation success rate"
                    )
                elif remediation_rate < 0.50:
                    risk_score += 15
                    confidence_score -= 10
                    risk_factors.append(
                        "Poor historical remediation success rate"
                    )

        if context.failed_remediations > 0:
            risk_score += min(
                20,
                10 * context.failed_remediations,
            )

            risk_factors.append(
                "Previous remediation failures detected"
            )

        # -----------------------------------------------------
        # ROUTING CONFIDENCE
        # -----------------------------------------------------

        routing_confidence = (
            context.routing_confidence
        )

        if routing_confidence >= 0.90:
            confidence_score += 20
            confidence_factors.append(
                "Very high routing confidence"
            )
        elif routing_confidence >= 0.75:
            confidence_score += 10
            confidence_factors.append(
                "High routing confidence"
            )
        elif routing_confidence >= 0.60:
            confidence_score += 5
            confidence_factors.append(
                "Moderate routing confidence"
            )
        elif routing_confidence > 0:
            confidence_score -= 10
            confidence_factors.append(
                "Low routing confidence"
            )
        else:
            confidence_score -= 20
            confidence_factors.append(
                "No routing confidence"
            )

        # -----------------------------------------------------
        # NORMALIZATION
        # -----------------------------------------------------

        risk_score = max(
            0,
            min(
                100,
                risk_score,
            ),
        )

        confidence_score = max(
            0,
            min(
                100,
                confidence_score,
            ),
        )

        risk_level = self._risk_level(
            risk_score
        )

        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "confidence_score": confidence_score,
            "confidence": round(
                confidence_score / 100,
                2,
            ),
            "risk_factors": risk_factors,
            "confidence_factors": (
                confidence_factors
            ),
        }

    @staticmethod
    def _risk_level(
        score: int,
    ) -> str:
        if score >= 80:
            return "critical"

        if score >= 60:
            return "high"

        if score >= 35:
            return "medium"

        return "low"