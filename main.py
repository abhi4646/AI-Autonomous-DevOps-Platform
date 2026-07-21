from pathlib import Path
from dotenv import load_dotenv
import json

# Load .env
ENV_FILE = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_FILE, override=True)

from src.orchestrator.orchestrator import Orchestrator
from src.jira.agent import JiraAgent
from src.github.agent import GitHubAgent
from src.docker.agent import DockerAgent
from src.terraform.agent import TerraformAgent
from src.kubernetes.agent import KubernetesAgent
from src.ansible.agent import AnsibleAgent
from src.monitoring.agent import MonitoringAgent


def main():
    orchestrator = Orchestrator()

    agents = [
        JiraAgent(),
        GitHubAgent(),
        DockerAgent(),
        TerraformAgent(),
        KubernetesAgent(),
        AnsibleAgent(),
        MonitoringAgent(),
    ]

    for agent in agents:
        orchestrator.register_agent(agent)

    result = orchestrator.run()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()