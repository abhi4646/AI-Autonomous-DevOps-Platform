from src.ai.decision_engine import DecisionEngine


class Orchestrator:
    def __init__(self):
        self.agents = []
        self.decision_engine = DecisionEngine()

    def register_agent(self, agent):
        self.agents.append(agent)

    def run(self, context=None):
        """Run all registered agents."""
        return {
            agent.name: agent.execute(context)
            for agent in self.agents
        }

    def route(self, request, context=None):
        """Use the DecisionEngine to route a request to an agent."""

        if not request:
            raise ValueError("Request cannot be empty")

        decision = self.decision_engine.decide_agents(request)

        if not decision["matched"]:
            return {
                "status": "no_route",
                "request": request,
                "message": "No suitable agent found",
            }

        recommended_agents = decision["recommended_agents"]

        if not recommended_agents:
            return {
                "status": "no_route",
                "request": request,
                "message": "No suitable agent found",
            }

        selected_agent = recommended_agents[0]

        for agent in self.agents:
            if agent.name.lower() == selected_agent:
                return {
                    "status": "routed",
                    "request": request,
                    "agent": agent.name,
                    "result": agent.execute(context),
                }

        return {
            "status": "agent_unavailable",
            "request": request,
            "agent": selected_agent,
            "message": f"{selected_agent} agent is not registered",
        }