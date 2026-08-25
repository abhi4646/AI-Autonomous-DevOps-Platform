from unittest.mock import patch

from src.kubernetes.agent import KubernetesAgent


@patch("src.kubernetes.agent.settings")
def test_kubernetes_dry_run(mock_settings):
    mock_settings.app_mode = "dry_run"
    mock_settings.kubeconfig_path = ""
    mock_settings.kubernetes_namespace = "default"

    agent = KubernetesAgent()

    result = agent.get_pods()

    assert result["status"] == "dry_run"

    assert result["command"] == [
        "kubectl",
        "get",
        "pods",
        "-n",
        "default",
    ]


@patch("src.kubernetes.agent.run_command")
@patch("src.kubernetes.agent.settings")
def test_kubernetes_uses_hardened_runner(
    mock_settings,
    mock_run_command,
):
    mock_settings.app_mode = "live"
    mock_settings.kubeconfig_path = ""
    mock_settings.kubernetes_namespace = "production"

    mock_run_command.return_value = {
        "status": "success",
        "returncode": 0,
        "stdout": "pods",
        "stderr": "",
        "command": [],
        "telemetry": {},
    }

    agent = KubernetesAgent()

    result = agent.get_pods()

    mock_run_command.assert_called_once_with(
        [
            "kubectl",
            "get",
            "pods",
            "-n",
            "production",
        ],
        timeout=120,
        output_limit=1500,
        request="CLI command execution",
        agent="Kubernetes Agent",
    )

    assert result["status"] == "success"


@patch("src.kubernetes.agent.run_command")
@patch("src.kubernetes.agent.settings")
def test_kubernetes_uses_kubeconfig(
    mock_settings,
    mock_run_command,
):
    mock_settings.app_mode = "live"
    mock_settings.kubeconfig_path = "config/kubeconfig"
    mock_settings.kubernetes_namespace = "default"

    mock_run_command.return_value = {
        "status": "success",
        "returncode": 0,
        "stdout": "",
        "stderr": "",
        "command": [],
        "telemetry": {},
    }

    agent = KubernetesAgent()

    agent.get_pods()

    command = (
        mock_run_command
        .call_args
        .args[0]
    )

    assert command == [
        "kubectl",
        "--kubeconfig",
        "config/kubeconfig",
        "get",
        "pods",
        "-n",
        "default",
    ]


@patch("src.kubernetes.agent.run_command")
@patch("src.kubernetes.agent.settings")
def test_kubernetes_propagates_failure(
    mock_settings,
    mock_run_command,
):
    mock_settings.app_mode = "live"
    mock_settings.kubeconfig_path = ""
    mock_settings.kubernetes_namespace = "default"

    mock_run_command.return_value = {
        "status": "failed",
        "returncode": 1,
        "stdout": "",
        "stderr": "cluster unavailable",
        "command": ["kubectl"],
        "telemetry": {},
    }

    agent = KubernetesAgent()

    result = agent.get_pods()

    assert result["status"] == "failed"
    assert (
        result["stderr"]
        == "cluster unavailable"
    )


@patch("src.kubernetes.agent.run_command")
@patch("src.kubernetes.agent.settings")
def test_kubernetes_passes_request_to_telemetry(
    mock_settings,
    mock_run_command,
):
    mock_settings.app_mode = "live"
    mock_settings.kubeconfig_path = ""
    mock_settings.kubernetes_namespace = "production"

    mock_run_command.return_value = {
        "status": "success",
        "returncode": 0,
        "stdout": "pods",
        "stderr": "",
        "command": [],
        "telemetry": {
            "request": "Check production pods",
            "agent": "Kubernetes Agent",
        },
    }

    agent = KubernetesAgent()

    result = agent.execute(
        {
            "request": "Check production pods"
        }
    )

    mock_run_command.assert_called_once_with(
        [
            "kubectl",
            "get",
            "pods",
            "-n",
            "production",
        ],
        timeout=120,
        output_limit=1500,
        request="Check production pods",
        agent="Kubernetes Agent",
    )

    assert (
        result["kubernetes"]
        ["telemetry"]["request"]
        == "Check production pods"
    )

    assert (
        result["kubernetes"]
        ["telemetry"]["agent"]
        == "Kubernetes Agent"
    )