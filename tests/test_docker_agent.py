from unittest.mock import patch

from src.docker.agent import DockerAgent


@patch("src.docker.agent.settings")
def test_docker_dry_run(mock_settings):
    mock_settings.app_mode = "dry_run"
    mock_settings.docker_image_name = "test-image"

    agent = DockerAgent()

    result = agent.build()

    assert result["status"] == "dry_run"
    assert result["command"] == [
        "docker",
        "build",
        "-t",
        "test-image",
        ".",
    ]


@patch("src.docker.agent.run_command")
@patch("src.docker.agent.settings")
def test_docker_uses_hardened_runner(
    mock_settings,
    mock_run_command,
):
    mock_settings.app_mode = "live"
    mock_settings.docker_image_name = "test-image"

    mock_run_command.return_value = {
        "status": "success",
        "returncode": 0,
        "stdout": "built",
        "stderr": "",
        "command": [],
    }

    agent = DockerAgent()

    result = agent.build()

    mock_run_command.assert_called_once_with(
        [
            "docker",
            "build",
            "-t",
            "test-image",
            ".",
        ],
        timeout=300,
        output_limit=1500,
    )

    assert result["status"] == "success"


@patch("src.docker.agent.run_command")
@patch("src.docker.agent.settings")
def test_docker_propagates_unavailable(
    mock_settings,
    mock_run_command,
):
    mock_settings.app_mode = "live"
    mock_settings.docker_image_name = "test-image"

    mock_run_command.return_value = {
        "status": "unavailable",
        "returncode": None,
        "stdout": "",
        "stderr": "Executable not found: docker",
        "command": ["docker"],
    }

    agent = DockerAgent()

    result = agent.build()

    assert result["status"] == "unavailable"


@patch("src.docker.agent.run_command")
@patch("src.docker.agent.settings")
def test_docker_propagates_timeout(
    mock_settings,
    mock_run_command,
):
    mock_settings.app_mode = "live"
    mock_settings.docker_image_name = "test-image"

    mock_run_command.return_value = {
        "status": "timeout",
        "returncode": None,
        "stdout": "",
        "stderr": "",
        "command": ["docker"],
    }

    agent = DockerAgent()

    result = agent.build()

    assert result["status"] == "timeout"