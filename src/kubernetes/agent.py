from src.agents import BaseAgent


class KubernetesAgent(BaseAgent):

    def __init__(self):
        super().__init__("Kubernetes Agent")

    def execute(self):
        print("☸️ Managing Kubernetes deployments...")