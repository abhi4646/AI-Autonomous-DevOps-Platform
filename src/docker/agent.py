import subprocess

from src.agents import BaseAgent
from src.core.config import settings


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
                "command": " ".join(command),
            }

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        return {
            "status": "success" if result.returncode == 0 else "failed",
            "returncode": result.returncode,
            "stdout": (result.stdout or "")[-1500:],
            "stderr": (result.stderr or "")[-1500:],
        }

    def execute(self, context=None):
        return {
            "docker": self.build()
        }