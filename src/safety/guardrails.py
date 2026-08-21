class SafetyGuardrails:
    """
    Evaluates proposed autonomous DevOps actions before execution.

    The guardrail layer can:
    - allow low-risk actions
    - require human review for medium-risk actions
    - block dangerous actions
    """

    HIGH_RISK_KEYWORDS = {
        "delete",
        "destroy",
        "drop",
        "terminate",
        "remove production",
        "wipe",
        "shutdown",
        "force delete",
        "terraform destroy",
        "kubectl delete",
    }

    MEDIUM_RISK_KEYWORDS = {
        "restart",
        "deploy",
        "rollback",
        "scale",
        "apply",
        "update production",
        "change configuration",
    }

    def evaluate(self, request, policy_result=None):
        """
        Evaluate a proposed action and return a safety decision.
        """

        if not request:
            return {
                "allowed": False,
                "action": "block",
                "risk": "high",
                "reason": "Empty request cannot be executed safely",
            }

        request_text = str(request).lower()

        if any(keyword in request_text for keyword in self.HIGH_RISK_KEYWORDS):
            return {
                "allowed": False,
                "action": "block",
                "risk": "high",
                "reason": "Potentially destructive operation detected",
            }

        if any(keyword in request_text for keyword in self.MEDIUM_RISK_KEYWORDS):
            return {
                "allowed": False,
                "action": "review",
                "risk": "medium",
                "reason": "Operational change requires approval",
            }

        if policy_result:
            policy_action = policy_result.get("action")

            if policy_action == "escalate":
                return {
                    "allowed": False,
                    "action": "escalate",
                    "risk": "medium",
                    "reason": "Decision policy requires escalation",
                }

            if policy_action == "review":
                return {
                    "allowed": False,
                    "action": "review",
                    "risk": "medium",
                    "reason": "Decision policy requires review",
                }

        return {
            "allowed": True,
            "action": "execute",
            "risk": "low",
            "reason": "No unsafe operation detected",
        }