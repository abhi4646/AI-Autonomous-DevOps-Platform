from unittest.mock import patch

from src.terraform.agent import TerraformAgent


@patch("src.terraform.agent.settings")
def test_terraform_dry_run(mock_settings):
    mock_settings.app_mode = "dry_run"
    mock_settings.terraform_working_dir = "terraform"

    agent = TerraformAgent()

    result = agent.plan()

    assert result["status"] == "dry_run"

    assert result["commands"] == [
        [
            "terraform",
            "-chdir=terraform",
            "init",
        ],
        [
            "terraform",
            "-chdir=terraform",
            "plan",
        ],
    ]


@patch("src.terraform.agent.run_command")
@patch("src.terraform.agent.settings")
def test_terraform_stops_when_init_fails(
    mock_settings,
    mock_run_command,
):
    mock_settings.app_mode = "live"
    mock_settings.terraform_working_dir = "terraform"

    mock_run_command.return_value = {
        "status": "failed",
        "returncode": 1,
        "stdout": "",
        "stderr": "init failed",
        "command": [],
    }

    agent = TerraformAgent()

    result = agent.plan()

    assert result["status"] == "init_failed"
    assert result["stage"] == "init"

    assert mock_run_command.call_count == 1


@patch("src.terraform.agent.run_command")
@patch("src.terraform.agent.settings")
def test_terraform_runs_plan_after_init(
    mock_settings,
    mock_run_command,
):
    mock_settings.app_mode = "live"
    mock_settings.terraform_working_dir = "terraform"

    mock_run_command.side_effect = [
        {
            "status": "success",
            "returncode": 0,
            "stdout": "initialized",
            "stderr": "",
            "command": [],
        },
        {
            "status": "success",
            "returncode": 0,
            "stdout": "plan complete",
            "stderr": "",
            "command": [],
        },
    ]

    agent = TerraformAgent()

    result = agent.plan()

    assert result["status"] == "success"
    assert result["stage"] == "plan"
    assert result["result"]["stdout"] == "plan complete"

    assert mock_run_command.call_count == 2


@patch("src.terraform.agent.run_command")
@patch("src.terraform.agent.settings")
def test_terraform_propagates_plan_timeout(
    mock_settings,
    mock_run_command,
):
    mock_settings.app_mode = "live"
    mock_settings.terraform_working_dir = "terraform"

    mock_run_command.side_effect = [
        {
            "status": "success",
            "returncode": 0,
            "stdout": "",
            "stderr": "",
            "command": [],
        },
        {
            "status": "timeout",
            "returncode": None,
            "stdout": "",
            "stderr": "",
            "command": [],
        },
    ]

    agent = TerraformAgent()

    result = agent.plan()

    assert result["status"] == "timeout"
    assert result["stage"] == "plan"