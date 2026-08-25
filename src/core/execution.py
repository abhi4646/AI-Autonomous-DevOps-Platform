import subprocess
from time import perf_counter
from typing import Iterable, Optional

from src.core.telemetry import ExecutionTelemetry


DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_OUTPUT_LIMIT = 1500


def run_command(
    command: Iterable[str],
    *,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    output_limit: int = DEFAULT_OUTPUT_LIMIT,
    cwd: Optional[str] = None,
    request: str = "CLI command execution",
    agent: str = "unknown",
) -> dict:
    """
    Execute a CLI command safely and return a normalized result.

    Returns one of:
    - success
    - failed
    - timeout
    - unavailable
    - error

    Each execution also includes structured telemetry.
    """

    command = list(command)

    telemetry = ExecutionTelemetry.start(
        request=request,
        agent=agent,
        command=command,
    )

    started = perf_counter()

    def finalize(
        result: dict,
        *,
        error: Optional[str] = None,
    ) -> dict:
        duration_ms = (
            perf_counter() - started
        ) * 1000

        telemetry.finish(
            status=result["status"],
            duration_ms=duration_ms,
            error=error,
        )

        result["telemetry"] = telemetry.to_dict()

        return result

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )

    except FileNotFoundError:
        message = (
            f"Executable not found: {command[0]}"
        )

        return finalize(
            {
                "status": "unavailable",
                "command": command,
                "stdout": "",
                "stderr": message,
                "returncode": None,
            },
            error=message,
        )

    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""

        if isinstance(stdout, bytes):
            stdout = stdout.decode(
                errors="replace"
            )

        if isinstance(stderr, bytes):
            stderr = stderr.decode(
                errors="replace"
            )

        message = (
            f"Command timed out after "
            f"{timeout} seconds"
        )

        return finalize(
            {
                "status": "timeout",
                "command": command,
                "stdout": stdout[-output_limit:],
                "stderr": stderr[-output_limit:],
                "returncode": None,
            },
            error=message,
        )

    except Exception as exc:
        message = str(exc)

        return finalize(
            {
                "status": "error",
                "command": command,
                "stdout": "",
                "stderr": message,
                "returncode": None,
            },
            error=message,
        )

    status = (
        "success"
        if result.returncode == 0
        else "failed"
    )

    normalized = {
        "status": status,
        "command": command,
        "stdout": result.stdout[-output_limit:],
        "stderr": result.stderr[-output_limit:],
        "returncode": result.returncode,
    }

    return finalize(
        normalized,
        error=(
            result.stderr[-output_limit:]
            if status == "failed"
            else None
        ),
    )