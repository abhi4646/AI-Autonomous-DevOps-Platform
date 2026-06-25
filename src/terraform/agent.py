from src.agents import BaseAgent


class TerraformAgent(BaseAgent):

    def __init__(self):
        super().__init__("Terraform Agent")

    def execute(self):
        print("🌍 Planning infrastructure with Terraform...")