import subprocess
from unittest.mock import Mock, patch

from src.core.execution import run_command


@patch("src.core.execution.subprocess.run")
def test_run_command_success(mock_run):
    mock_run.return_value = Mock(
        returncode=0,
        stdout="command succeeded",
        stderr="",
    )

    result = run_command(
        ["example", "command"]
    )

    assert result["status"] == "success"
    assert result["returncode"] == 0
    assert result["stdout"] == "command succeeded"
    assert result["stderr"] == ""
    assert result["command"] == [
        "example",
        "command",
    ]


@patch("src.core.execution.subprocess.run")
def test_run_command_failure(mock_run):
    mock_run.return_value = Mock(
        returncode=1,
        stdout="",
        stderr="command failed",
    )

    result = run_command(
        ["example"]
    )

    assert result["status"] == "failed"
    assert result["returncode"] == 1
    assert result["stderr"] == "command failed"


@patch("src.core.execution.subprocess.run")
def test_run_command_missing_executable(mock_run):
    mock_run.side_effect = FileNotFoundError()

    result = run_command(
        ["missing-tool"]
    )

    assert result["status"] == "unavailable"
    assert result["returncode"] is None
    assert "missing-tool" in result["stderr"]


@patch("src.core.execution.subprocess.run")
def test_run_command_timeout(mock_run):
    mock_run.side_effect = subprocess.TimeoutExpired(
        cmd=["slow-tool"],
        timeout=1,
        output="partial output",
        stderr="timeout error",
    )

    result = run_command(
        ["slow-tool"],
        timeout=1,
    )

    assert result["status"] == "timeout"
    assert result["returncode"] is None
    assert result["stdout"] == "partial output"
    assert result["stderr"] == "timeout error"


@patch("src.core.execution.subprocess.run")
def test_run_command_unexpected_exception(mock_run):
    mock_run.side_effect = RuntimeError(
        "unexpected problem"
    )

    result = run_command(
        ["example"]
    )

    assert result["status"] == "error"
    assert result["returncode"] is None
    assert "unexpected problem" in result["stderr"]


@patch("src.core.execution.subprocess.run")
def test_run_command_truncates_output(mock_run):
    mock_run.return_value = Mock(
        returncode=0,
        stdout="abcdefghij",
        stderr="1234567890",
    )

    result = run_command(
        ["example"],
        output_limit=5,
    )

    assert result["stdout"] == "fghij"
    assert result["stderr"] == "67890"


@patch("src.core.execution.subprocess.run")
def test_run_command_includes_telemetry(mock_run):
    mock_run.return_value = Mock(
        returncode=0,
        stdout="ok",
        stderr="",
    )

    result = run_command(
        ["example"],
        request="Test request",
        agent="test-agent",
    )

    telemetry = result["telemetry"]

    assert telemetry["execution_id"]
    assert telemetry["request"] == "Test request"
    assert telemetry["agent"] == "test-agent"
    assert telemetry["status"] == "success"
    assert telemetry["started_at"] is not None
    assert telemetry["finished_at"] is not None
    assert telemetry["duration_ms"] >= 0
    assert telemetry["command"] == ["example"]
    assert telemetry["error"] is None


@patch("src.core.execution.subprocess.run")
def test_run_command_failure_records_error_telemetry(
    mock_run,
):
    mock_run.return_value = Mock(
        returncode=1,
        stdout="",
        stderr="build failed",
    )

    result = run_command(
        ["example"],
        request="Failed operation",
        agent="docker",
    )

    telemetry = result["telemetry"]

    assert telemetry["status"] == "failed"
    assert telemetry["error"] == "build failed"


@patch("src.core.execution.subprocess.run")
def test_run_command_timeout_records_telemetry(
    mock_run,
):
    mock_run.side_effect = subprocess.TimeoutExpired(
        cmd=["slow-tool"],
        timeout=5,
    )

    result = run_command(
        ["slow-tool"],
        timeout=5,
        request="Slow operation",
        agent="terraform",
    )

    telemetry = result["telemetry"]

    assert telemetry["status"] == "timeout"
    assert telemetry["agent"] == "terraform"
    assert "5 seconds" in telemetry["error"]


@patch("src.core.execution.subprocess.run")
def test_run_command_generates_unique_execution_ids(
    mock_run,
):
    mock_run.return_value = Mock(
        returncode=0,
        stdout="ok",
        stderr="",
    )

    first = run_command(
        ["example"]
    )

    second = run_command(
        ["example"]
    )

    assert (
        first["telemetry"]["execution_id"]
        != second["telemetry"]["execution_id"]
    )