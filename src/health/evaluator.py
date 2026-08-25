from typing import Any


class HealthEvaluator:
    """
    Evaluate platform health from aggregate execution metrics.

    The evaluator is intentionally deterministic. It does not perform
    remediation or execute agents; it only classifies observed health.
    """

    HEALTHY_FAILURE_RATE = 0.10
    DEGRADED_FAILURE_RATE = 0.30

    HEALTHY_DURATION_MS = 5_000
    DEGRADED_DURATION_MS = 15_000

    def evaluate(self, metrics: dict[str, Any]) -> dict[str, Any]:
        total_executions = int(metrics.get("total_executions", 0) or 0)
        failure_rate = float(metrics.get("failure_rate", 0) or 0)
        average_duration_ms = float(
            metrics.get("average_duration_ms", 0) or 0
        )

        reasons = []
        score = 100

        if total_executions == 0:
            return {
                "status": "unknown",
                "score": None,
                "reasons": ["No execution data available"],
                "metrics": metrics,
            }

        if failure_rate >= self.DEGRADED_FAILURE_RATE:
            score -= 50
            reasons.append("High execution failure rate")
        elif failure_rate >= self.HEALTHY_FAILURE_RATE:
            score -= 25
            reasons.append("Elevated execution failure rate")

        if average_duration_ms >= self.DEGRADED_DURATION_MS:
            score -= 30
            reasons.append("High average execution duration")
        elif average_duration_ms >= self.HEALTHY_DURATION_MS:
            score -= 15
            reasons.append("Elevated average execution duration")

        score = max(score, 0)

        if score >= 80:
            status = "healthy"
        elif score >= 50:
            status = "degraded"
        else:
            status = "unhealthy"

        if not reasons:
            reasons.append("Execution metrics are within healthy thresholds")

        return {
            "status": status,
            "score": score,
            "reasons": reasons,
            "metrics": metrics,
        }