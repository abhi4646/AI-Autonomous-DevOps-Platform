from src.agents import BaseAgent
from src.core.config import settings
from src.core.execution import run_command


class DockerAgent(BaseAgent):
    def __init__(self):
        super().__init__("Docker Agent")

    def build(self):
        command = [
            "docker",
            "build",
            "-t",
            settings.docker_image_name,
            ".",
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
        )

    def execute(self, context=None):
        return {
            "docker": self.build()
        }