class Orchestrator:
    def __init__(self):
        self.agents = []

    def register_agent(self, agent):
        self.agents.append(agent)

    def run(self, context=None):
        """Run all registered agents."""
        return {
            agent.name: agent.execute(context)
            for agent in self.agents
        }

    def route(self, request, context=None):
        """Route a request to the most appropriate DevOps agent."""

        if not request:
            raise ValueError("Request cannot be empty")

        request_lower = request.lower()

        routing_rules = {
            "jira": ["jira", "ticket", "issue", "kan-"],
            "github": ["github", "repository", "repo", "pull request", "commit"],
            "docker": ["docker", "container", "image", "build"],
            "terraform": ["terraform", "infrastructure", "tf", "plan"],
            "kubernetes": ["kubernetes", "k8s", "pod", "deployment", "cluster"],
            "ansible": ["ansible", "playbook", "configuration"],
            "monitoring": ["monitor", "monitoring", "health", "metrics", "alert"],
        }

        selected_agent = None

        for agent_name, keywords in routing_rules.items():
            if any(keyword in request_lower for keyword in keywords):
                selected_agent = agent_name
                break

        if selected_agent is None:
            return {
                "status": "no_route",
                "request": request,
                "message": "No suitable agent found"
            }

        for agent in self.agents:
            if agent.name.lower() == selected_agent:
                return {
                    "status": "routed",
                    "request": request,
                    "agent": agent.name,
                    "result": agent.execute(context)
                }

        return {
            "status": "agent_unavailable",
            "request": request,
            "agent": selected_agent,
            "message": f"{selected_agent} agent is not registered"
        }