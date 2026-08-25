from unittest.mock import patch

from src.ansible.agent import AnsibleAgent


@patch("src.ansible.agent.settings")
def test_ansible_dry_run(mock_settings):
    mock_settings.app_mode = "dry_run"
    mock_settings.ansible_inventory_path = "inventory.ini"
    mock_settings.ansible_playbook_path = "site.yml"

    agent = AnsibleAgent()

    result = agent.run_playbook()

    assert result["status"] == "dry_run"

    assert result["command"] == [
        "ansible-playbook",
        "-i",
        "inventory.ini",
        "site.yml",
    ]


@patch("src.ansible.agent.run_command")
@patch("src.ansible.agent.settings")
def test_ansible_uses_hardened_runner(
    mock_settings,
    mock_run_command,
):
    mock_settings.app_mode = "live"
    mock_settings.ansible_inventory_path = "inventory.ini"
    mock_settings.ansible_playbook_path = "site.yml"

    mock_run_command.return_value = {
        "status": "success",
        "returncode": 0,
        "stdout": "playbook complete",
        "stderr": "",
        "command": [],
        "telemetry": {},
    }

    agent = AnsibleAgent()

    result = agent.run_playbook()

    mock_run_command.assert_called_once_with(
        [
            "ansible-playbook",
            "-i",
            "inventory.ini",
            "site.yml",
        ],
        timeout=300,
        output_limit=1500,
        request="CLI command execution",
        agent="Ansible Agent",
    )

    assert result["status"] == "success"


@patch("src.ansible.agent.run_command")
@patch("src.ansible.agent.settings")
def test_ansible_propagates_unavailable(
    mock_settings,
    mock_run_command,
):
    mock_settings.app_mode = "live"
    mock_settings.ansible_inventory_path = "inventory.ini"
    mock_settings.ansible_playbook_path = "site.yml"

    mock_run_command.return_value = {
        "status": "unavailable",
        "returncode": None,
        "stdout": "",
        "stderr": "Executable not found: ansible-playbook",
        "command": ["ansible-playbook"],
        "telemetry": {},
    }

    agent = AnsibleAgent()

    result = agent.run_playbook()

    assert result["status"] == "unavailable"


@patch("src.ansible.agent.run_command")
@patch("src.ansible.agent.settings")
def test_ansible_propagates_timeout(
    mock_settings,
    mock_run_command,
):
    mock_settings.app_mode = "live"
    mock_settings.ansible_inventory_path = "inventory.ini"
    mock_settings.ansible_playbook_path = "site.yml"

    mock_run_command.return_value = {
        "status": "timeout",
        "returncode": None,
        "stdout": "",
        "stderr": "",
        "command": ["ansible-playbook"],
        "telemetry": {},
    }

    agent = AnsibleAgent()

    result = agent.run_playbook()

    assert result["status"] == "timeout"


@patch("src.ansible.agent.run_command")
@patch("src.ansible.agent.settings")
def test_ansible_passes_request_to_telemetry(
    mock_settings,
    mock_run_command,
):
    mock_settings.app_mode = "live"
    mock_settings.ansible_inventory_path = "inventory.ini"
    mock_settings.ansible_playbook_path = "site.yml"

    mock_run_command.return_value = {
        "status": "success",
        "returncode": 0,
        "stdout": "complete",
        "stderr": "",
        "command": [],
        "telemetry": {
            "request": "Configure production servers",
            "agent": "Ansible Agent",
        },
    }

    agent = AnsibleAgent()

    result = agent.execute(
        {
            "request": "Configure production servers"
        }
    )

    mock_run_command.assert_called_once_with(
        [
            "ansible-playbook",
            "-i",
            "inventory.ini",
            "site.yml",
        ],
        timeout=300,
        output_limit=1500,
        request="Configure production servers",
        agent="Ansible Agent",
    )

    assert (
        result["ansible"]["telemetry"]["request"]
        == "Configure production servers"
    )