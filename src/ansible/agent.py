import shutil
import subprocess

from src.agents import BaseAgent
from src.core.config import settings


class AnsibleAgent(BaseAgent):
    def __init__(self):
        super().__init__("Ansible Agent")

    def execute(self, context=None):
        command = [
            "ansible-playbook",
            "-i",
            settings.ansible_inventory_path,
            settings.ansible_playbook_path,
        ]

        # Ansible is normally run from Linux/macOS/WSL.
        # Do not crash the whole platform if it is unavailable.
        if shutil.which("ansible-playbook") is None:
            return {
                "ansible": {
                    "status": "not_installed",
                    "message": (
                        "ansible-playbook is not available on this host. "
                        "Use WSL/Linux for live Ansible execution."
                    ),
                    "command": " ".join(command),
                }
            }

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
        )

        return {
            "ansible": {
                "status": "success" if result.returncode == 0 else "failed",
                "returncode": result.returncode,
                "stdout": result.stdout[-1500:],
                "stderr": result.stderr[-1500:],
            }
        }