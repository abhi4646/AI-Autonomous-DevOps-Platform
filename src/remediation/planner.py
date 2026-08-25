class RemediationPlanner:
    """
    Converts platform health evaluation results into
    safe remediation recommendations.

    This planner does NOT execute remediation.
    It only decides what action should be considered.
    """

    def plan(self, health):
        status = health.get("status", "unknown")
        score = health.get("score", 0)
        reasons = health.get("reasons", [])

        # Healthy system: continue observation.
        if status == "healthy":
            return {
                "action": "observe",
                "requires_approval": False,
                "health_status": status,
                "health_score": score,
                "reasons": reasons,
            }

        # Degraded system: recommend remediation,
        # but do not execute anything automatically.
        if status == "degraded":
            return {
                "action": "recommend",
                "requires_approval": False,
                "health_status": status,
                "health_score": score,
                "reasons": reasons,
            }

        # Unhealthy system: remediation is appropriate,
        # but human approval is required before execution.
        if status == "unhealthy":
            return {
                "action": "remediate",
                "requires_approval": True,
                "health_status": status,
                "health_score": score,
                "reasons": reasons,
            }

        # Unknown or unexpected states fail safely.
        return {
            "action": "observe",
            "requires_approval": False,
            "health_status": status,
            "health_score": score,
            "reasons": reasons,
        }