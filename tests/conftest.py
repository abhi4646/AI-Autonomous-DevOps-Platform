import os
import tempfile
from pathlib import Path


# ---------------------------------------------------------
# PYTEST DATABASE ISOLATION
# ---------------------------------------------------------

# Use a dedicated temporary database path for API tests.
#
# We intentionally do NOT use TemporaryDirectory here because
# the API owns a module-level SQLite connection. On Windows,
# SQLite can keep that file locked until interpreter shutdown,
# which prevents TemporaryDirectory from cleaning itself up.
_test_database_path = (
    Path(tempfile.gettempdir())
    / "autonomous_devops_platform_pytest.db"
)

# Remove any database left behind by an earlier test run.
if _test_database_path.exists():
    try:
        _test_database_path.unlink()
    except PermissionError:
        pass

# This environment variable is set before pytest imports
# src.api.app -> src.api.routes.
os.environ["DEVOPS_DB_PATH"] = str(_test_database_path)


def pytest_sessionfinish(session, exitstatus):
    """
    Close the API SQLite connection and remove the temporary
    test database after the complete pytest session.
    """

    try:
        from src.api.routes import database

        database.close()
    except (ImportError, AttributeError):
        pass

    try:
        if _test_database_path.exists():
            _test_database_path.unlink()
    except PermissionError:
        # Windows may briefly retain a file handle during shutdown.
        # The next test session will attempt cleanup again.
        pass