from unittest.mock import patch, MagicMock

from src.docker.agent import DockerAgent
from src.kubernetes.agent import KubernetesAgent
from src.terraform.agent import TerraformAgent
from src.ansible.agent import AnsibleAgent
from src.monitoring.agent import MonitoringAgent


def mock_success(stdout="OK"):
    result = MagicMock()
    result.returncode = 0
    result.stdout = stdout
    result.stderr = ""
    return result


@patch("src.docker.agent.subprocess.run")
def test_docker_agent(mock_run):
    mock_run.return_value = mock_success("Docker build successful")

    result = DockerAgent().execute()

    assert "docker" in result
    assert result["docker"]["status"] == "success"


@patch("src.kubernetes.agent.subprocess.run")
def test_kubernetes_agent(mock_run):
    mock_run.return_value = mock_success("Kubernetes OK")

    result = KubernetesAgent().execute()

    assert "kubernetes" in result
    assert result["kubernetes"]["status"] == "success"


@patch("src.terraform.agent.subprocess.run")
def test_terraform_agent(mock_run):
    mock_run.return_value = mock_success("Terraform OK")

    result = TerraformAgent().execute()

    assert "terraform" in result
    assert result["terraform"]["status"] == "success"


@patch("src.ansible.agent.subprocess.run")
def test_ansible_agent(mock_run):
    mock_run.return_value = mock_success("Ansible OK")

    result = AnsibleAgent().execute()

    assert "ansible" in result
    assert result["ansible"]["status"] == "success"


def test_monitoring_agent():
    result = MonitoringAgent().execute()

    assert "monitoring" in result
    assert result["monitoring"]["status"] == "healthy"