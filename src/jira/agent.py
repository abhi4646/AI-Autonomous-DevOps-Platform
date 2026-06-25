from src.agents import BaseAgent


class JiraAgent(BaseAgent):

    def __init__(self):
        super().__init__("Jira Agent")

    def execute(self):
        print("📋 Checking Jira for new tickets...")