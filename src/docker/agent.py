from src.agents import BaseAgent


class DockerAgent(BaseAgent):

    def __init__(self):
        super().__init__("Docker Agent")

    def execute(self):
        print("🐳 Building and scanning Docker images...")