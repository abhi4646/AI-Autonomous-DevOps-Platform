class Orchestrator:

    def __init__(self):
        self.agents = []

    def register_agent(self, agent):
        self.agents.append(agent)

    def run(self):
        print("🚀 AI Autonomous DevOps Platform Started")

        for agent in self.agents:
            print(f"Running {agent.name}")
            agent.execute()