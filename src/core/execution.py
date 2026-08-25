import subprocess
from typing import Iterable, Optional


DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_OUTPUT_LIMIT = 1500


def run_command(
    command: Iterable[str],
    *,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    output_limit: int = DEFAULT_OUTPUT_LIMIT,
    cwd: Optional[str] = None,
) -> dict:
    """
    Execute a CLI command safely and return a normalized result.

    Returns one of:
    - success
    - failed
    - timeout
    - unavailable
    - error
    """

    command = list(command)

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )

    except FileNotFoundError:
        return {
            "status": "unavailable",
            "command": command,
            "stdout": "",
            "stderr": (
                f"Executable not found: {command[0]}"
            ),
            "returncode": None,
        }

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

        return {
            "status": "timeout",
            "command": command,
            "stdout": stdout[-output_limit:],
            "stderr": stderr[-output_limit:],
            "returncode": None,
        }

    except Exception as exc:
        return {
            "status": "error",
            "command": command,
            "stdout": "",
            "stderr": str(exc),
            "returncode": None,
        }

    return {
        "status": (
            "success"
            if result.returncode == 0
            else "failed"
        ),
        "command": command,
        "stdout": result.stdout[-output_limit:],
        "stderr": result.stderr[-output_limit:],
        "returncode": result.returncode,
    }