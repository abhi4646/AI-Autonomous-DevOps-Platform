class DecisionEngine:
    """
    Decision engine responsible for determining which DevOps
    agents should handle an incoming request.
    """

    ROUTING_RULES = {
        "jira": [
            "jira",
            "ticket",
            "issue",
            "kan",
        ],
        "github": [
            "github",
            "repo",
            "repository",
            "branch",
            "pull request",
            "commit",
            "code",
        ],
        "docker": [
            "docker",
            "container",
            "image",
            "build",
        ],
        "terraform": [
            "terraform",
            "infrastructure",
            "cloud",
            "tf",
            "plan",
        ],
        "kubernetes": [
            "kubernetes",
            "k8s",
            "pod",
            "deployment",
            "cluster",
        ],
        "ansible": [
            "ansible",
            "playbook",
            "configuration",
        ],
        "monitoring": [
            "monitor",
            "monitoring",
            "health",
            "metrics",
            "alert",
        ],
    }

    def decide_agents(self, ticket):
        """
        Analyze a ticket/request and recommend the appropriate
        DevOps agents with a confidence score.
        """

        # Empty request
        if not ticket:
            return {
                "recommended_agents": [],
                "matched": False,
                "confidence": 0.0,
            }

        # Support both plain strings and dictionary-style tickets
        if isinstance(ticket, str):
            text = ticket.lower()
        else:
            summary = ticket.get("summary", "")
            description = ticket.get("description", "")
            text = f"{summary} {description}".lower()

        agents = []

        # Match request text against agent routing rules
        for agent_name, keywords in self.ROUTING_RULES.items():
            if any(keyword in text for keyword in keywords):
                agents.append(agent_name)

        # At least one agent matched
        if agents:
            confidence = min(
                1.0,
                0.5 + (0.15 * len(agents))
            )

            return {
                "recommended_agents": agents,
                "matched": True,
                "confidence": confidence,
            }

        # Safe fallback when nothing matches
        return {
            "recommended_agents": ["github", "monitoring"],
            "matched": False,
            "confidence": 0.0,
        }