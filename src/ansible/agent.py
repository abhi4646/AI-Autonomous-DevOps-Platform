from src.agents import BaseAgent


class AnsibleAgent(BaseAgent):

    def __init__(self):
        super().__init__("Ansible Agent")

    def execute(self):
        print("⚙️ Configuring servers with Ansible...")