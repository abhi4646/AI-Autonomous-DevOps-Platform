from src.agents import BaseAgent
from src.core.config import settings
from src.core.execution import run_command


class TerraformAgent(BaseAgent):
    def __init__(self):
        super().__init__("Terraform Agent")

    def plan(self):
        init_command = [
            "terraform",
            f"-chdir={settings.terraform_working_dir}",
            "init",
        ]

        plan_command = [
            "terraform",
            f"-chdir={settings.terraform_working_dir}",
            "plan",
        ]

        if settings.app_mode == "dry_run":
            return {
                "status": "dry_run",
                "commands": [
                    init_command,
                    plan_command,
                ],
            }

        init_result = run_command(
            init_command,
            timeout=300,
            output_limit=2000,
        )

        if init_result["status"] != "success":
            return {
                "status": "init_failed",
                "stage": "init",
                "result": init_result,
            }

        plan_result = run_command(
            plan_command,
            timeout=300,
            output_limit=2000,
        )

        return {
            "status": plan_result["status"],
            "stage": "plan",
            "result": plan_result,
        }

    def execute(self, context=None):
        return {
            "terraform": self.plan()
        }