class DecisionEngine:
    """Select the most appropriate DevOps agents for an incoming request."""

    ROUTING_RULES = {
        "jira": ["jira", "ticket", "issue", "kan"],
        "github": [
            "github",
            "repo",
            "repository",
            "branch",
            "pull request",
            "commit",
            "code",
        ],
        "docker": ["docker", "container", "image", "build"],
        "terraform": [
            "terraform",
            "infrastructure",
            "infra",
            "cloud",
            "plan",
        ],
        "kubernetes": [
            "kubernetes",
            "k8s",
            "pod",
            "deployment",
            "cluster",
        ],
        "ansible": ["ansible", "playbook", "configuration"],
        "monitoring": [
            "monitor",
            "monitoring",
            "health",
            "metrics",
            "alert",
        ],
    }

    def decide_agents(self, ticket):
        """Return agents recommended for a ticket or request."""

        if not ticket:
            return {
                "recommended_agents": [],
                "matched": False,
            }

        if isinstance(ticket, str):
            text = ticket.lower()
        else:
            summary = ticket.get("summary", "")
            description = ticket.get("description", "")
            text = f"{summary} {description}".lower()

        agents = []

        for agent_name, keywords in self.ROUTING_RULES.items():
            if any(keyword in text for keyword in keywords):
                agents.append(agent_name)

        if agents:
            return {
                "recommended_agents": agents,
                "matched": True,
            }

        return {
            "recommended_agents": ["github", "monitoring"],
            "matched": False,
        }