class DecisionPolicy:
    """
    Converts DecisionEngine output into an execution policy.

    Possible actions:
    - execute: confidence is high enough for autonomous execution
    - review: confidence is moderate and should be reviewed
    - escalate: confidence is too low or no reliable match exists
    """

    def __init__(
        self,
        execute_threshold=0.80,
        review_threshold=0.60,
    ):
        self.execute_threshold = execute_threshold
        self.review_threshold = review_threshold

    def evaluate(self, decision):
        if not decision:
            return {
                "action": "escalate",
                "reason": "No decision data provided",
            }

        matched = decision.get("matched", False)
        confidence = decision.get("confidence", 0.0)
        agents = decision.get("recommended_agents", [])

        if not matched:
            return {
                "action": "escalate",
                "reason": "No reliable agent match",
                "confidence": confidence,
                "recommended_agents": agents,
            }

        if confidence >= self.execute_threshold:
            return {
                "action": "execute",
                "reason": "Confidence meets autonomous execution threshold",
                "confidence": confidence,
                "recommended_agents": agents,
            }

        if confidence >= self.review_threshold:
            return {
                "action": "review",
                "reason": "Confidence requires review before execution",
                "confidence": confidence,
                "recommended_agents": agents,
            }

        return {
            "action": "escalate",
            "reason": "Confidence below minimum review threshold",
            "confidence": confidence,
            "recommended_agents": agents,
        }