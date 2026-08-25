from src.agents import BaseAgent
from src.core.config import settings
from src.core.execution import run_command


class DockerAgent(BaseAgent):
    def __init__(self):
        super().__init__("Docker Agent")

    def build(
        self,
        request="CLI command execution",
    ):
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
            "docker": self.build(
                request=request
            )
        }