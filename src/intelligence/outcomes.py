from typing import Any, Dict, List

from src.intelligence.context import DecisionContext


class HistoricalOutcomeAnalyzer:
    """
    Evaluates historical execution and remediation outcomes.

    The analyzer is deterministic and read-only. It does not
    execute operations or modify incidents.
    """

    def analyze(
        self,
        context: DecisionContext,
    ) -> Dict[str, Any]:
        signals: List[str] = []

        execution_trend = "unknown"
        remediation_trend = "unknown"

        execution_rate = (
            context.execution_success_rate
        )

        remediation_rate = (
            context.remediation_success_rate
        )

        # -----------------------------------------------------
        # EXECUTION HISTORY
        # -----------------------------------------------------

        if context.previous_executions == 0:
            execution_trend = "insufficient_data"

            signals.append(
                "No historical execution data"
            )

        elif execution_rate is not None:
            if execution_rate >= 0.90:
                execution_trend = "strong"

                signals.append(
                    "Historical execution outcomes are strong"
                )

            elif execution_rate >= 0.70:
                execution_trend = "stable"

                signals.append(
                    "Historical execution outcomes are stable"
                )

            elif execution_rate >= 0.50:
                execution_trend = "degraded"

                signals.append(
                    "Historical execution outcomes are degraded"
                )

            else:
                execution_trend = "poor"

                signals.append(
                    "Historical execution outcomes are poor"
                )

        # -----------------------------------------------------
        # REMEDIATION HISTORY
        # -----------------------------------------------------

        if context.previous_remediations == 0:
            remediation_trend = "insufficient_data"

            signals.append(
                "No historical remediation data"
            )

        elif remediation_rate is not None:
            if remediation_rate >= 0.80:
                remediation_trend = "strong"

                signals.append(
                    "Historical remediation outcomes are strong"
                )

            elif remediation_rate >= 0.60:
                remediation_trend = "stable"

                signals.append(
                    "Historical remediation outcomes are stable"
                )

            elif remediation_rate >= 0.40:
                remediation_trend = "degraded"

                signals.append(
                    "Historical remediation outcomes are degraded"
                )

            else:
                remediation_trend = "poor"

                signals.append(
                    "Historical remediation outcomes are poor"
                )

        # -----------------------------------------------------
        # FAILURE PATTERN
        # -----------------------------------------------------

        repeated_execution_failure = (
            context.previous_failures >= 3
        )

        repeated_remediation_failure = (
            context.failed_remediations >= 2
        )

        if repeated_execution_failure:
            signals.append(
                "Repeated execution failure pattern detected"
            )

        if repeated_remediation_failure:
            signals.append(
                "Repeated remediation failure pattern detected"
            )

        # -----------------------------------------------------
        # ACTION GUIDANCE
        # -----------------------------------------------------

        avoid_repeat = (
            repeated_remediation_failure
            or remediation_trend == "poor"
        )

        prefer_rollback = (
            avoid_repeat
            and context.rollback_available
        )

        require_escalation = (
            avoid_repeat
            and not context.rollback_available
        )

        return {
            "execution_trend": execution_trend,
            "remediation_trend": remediation_trend,
            "execution_success_rate": (
                execution_rate
            ),
            "remediation_success_rate": (
                remediation_rate
            ),
            "repeated_execution_failure": (
                repeated_execution_failure
            ),
            "repeated_remediation_failure": (
                repeated_remediation_failure
            ),
            "avoid_repeat": avoid_repeat,
            "prefer_rollback": prefer_rollback,
            "require_escalation": (
                require_escalation
            ),
            "signals": signals,
        }