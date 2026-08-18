import os
import subprocess
from pathlib import Path

from src.agents import BaseAgent
from src.core.config import settings


class AnsibleAgent(BaseAgent):
    def __init__(self):
        super().__init__("Ansible Agent")

    def execute(self, context=None):
        # Convert:
        # C:\Users\abhis\Documents\project
        # into:
        # /mnt/c/Users/abhis/Documents/project
        windows_cwd = Path(os.getcwd())

        drive = windows_cwd.drive.rstrip(":").lower()
        rest = windows_cwd.as_posix().split(":", 1)[-1]

        linux_cwd = f"/mnt/{drive}{rest}"

        command = [
            "wsl",
            "-d",
            "Ubuntu",
            "--",
            "bash",
            "-lc",
            (
                f"cd '{linux_cwd}' && "
                f"ansible-playbook "
                f"-i '{settings.ansible_inventory_path}' "
                f"'{settings.ansible_playbook_path}'"
            ),
        ]

        if settings.app_mode == "dry_run":
            return {
                "ansible": {
                    "status": "dry_run",
                    "command": " ".join(command),
                }
            }

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        return {
            "ansible": {
                "status": "success" if result.returncode == 0 else "failed",
                "returncode": result.returncode,
                "stdout": (result.stdout or "")[-2000:],
                "stderr": (result.stderr or "")[-2000:],
            }
        }