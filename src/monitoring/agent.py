from src.agents import BaseAgent


class MonitoringAgent(BaseAgent):

    def __init__(self):
        super().__init__("Monitoring Agent")

    def execute(self):
        print("📊 Validating system health and monitoring...")