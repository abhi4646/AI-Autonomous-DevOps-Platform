from src.agents import BaseAgent
from src.core.config import settings
from src.core.execution import run_command


class AnsibleAgent(BaseAgent):
    def __init__(self):
        super().__init__("Ansible Agent")

    def run_playbook(
        self,
        request="CLI command execution",
    ):
        command = [
            "ansible-playbook",
            "-i",
            settings.ansible_inventory_path,
            settings.ansible_playbook_path,
        ]

        if settings.app_mode == "dry_run":
            return {
                "status": "dry_run",
                "command": command,
            }

        return run_command(
            command,
            timeout=300,
            output_limit=1500,
            request=request,
            agent=self.name,
        )

    def execute(self, context=None):
        request = "CLI command execution"

        if isinstance(context, dict):
            request = context.get(
                "request",
                request,
            )

        return {
            "ansible": self.run_playbook(
                request=request
            )
        }