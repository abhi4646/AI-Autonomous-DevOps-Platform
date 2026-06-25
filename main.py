from src.orchestrator.orchestrator import Orchestrator
from src.jira.agent import JiraAgent
from src.github.agent import GitHubAgent
from src.docker.agent import DockerAgent
from src.kubernetes.agent import KubernetesAgent
from src.terraform.agent import TerraformAgent
from src.ansible.agent import AnsibleAgent
from src.monitoring.agent import MonitoringAgent


def main():
    orchestrator = Orchestrator()

    orchestrator.register_agent(JiraAgent())
    orchestrator.register_agent(GitHubAgent())
    orchestrator.register_agent(DockerAgent())
    orchestrator.register_agent(KubernetesAgent())
    orchestrator.register_agent(TerraformAgent())
    orchestrator.register_agent(AnsibleAgent())
    orchestrator.register_agent(MonitoringAgent())

    orchestrator.run()


if __name__ == "__main__":
    main()