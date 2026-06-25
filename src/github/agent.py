from src.agents import BaseAgent


class GitHubAgent(BaseAgent):

    def __init__(self):
        super().__init__("GitHub Agent")

    def execute(self):
        print("🐙 Checking GitHub repositories...")