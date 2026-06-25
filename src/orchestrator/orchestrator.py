class Orchestrator:
    def __init__(self): self.agents=[]
    def register_agent(self, agent): self.agents.append(agent)
    def run(self, context=None): return {agent.name: agent.execute(context) for agent in self.agents}
