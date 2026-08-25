from src.agents import BaseAgent
from src.core.config import settings
from src.core.execution import run_command


class KubernetesAgent(BaseAgent):
    def __init__(self):
        super().__init__("Kubernetes Agent")

    def get_pods(
        self,
        request="CLI command execution",
    ):
        command = ["kubectl"]

        if settings.kubeconfig_path:
            command.extend(
                [
                    "--kubeconfig",
                    settings.kubeconfig_path,
                ]
            )

        command.extend(
            [
                "get",
                "pods",
                "-n",
                settings.kubernetes_namespace,
            ]
        )

        if settings.app_mode == "dry_run":
            return {
                "status": "dry_run",
                "command": command,
            }

        return run_command(
            command,
            timeout=120,
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
            "kubernetes": self.get_pods(
                request=request
            )
        }