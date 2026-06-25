import json
from src.orchestrator.orchestrator import Orchestrator
from src.jira.agent import JiraAgent
from src.github.agent import GitHubAgent
from src.docker.agent import DockerAgent
from src.terraform.agent import TerraformAgent
from src.kubernetes.agent import KubernetesAgent
from src.ansible.agent import AnsibleAgent
from src.monitoring.agent import MonitoringAgent

def main():
    orchestrator=Orchestrator()
    for agent in [JiraAgent(),GitHubAgent(),DockerAgent(),TerraformAgent(),KubernetesAgent(),AnsibleAgent(),MonitoringAgent()]: orchestrator.register_agent(agent)
    print(json.dumps(orchestrator.run(), indent=2))
if __name__=='__main__': main()
