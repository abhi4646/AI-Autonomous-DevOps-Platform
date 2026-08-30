import os
import tempfile
from pathlib import Path

import pytest

from src.security.auth import (
    AuthenticatedPrincipal,
    Role,
    authenticate_api_key,
)


# ---------------------------------------------------------
# PYTEST DATABASE ISOLATION
# ---------------------------------------------------------

_test_database_path = (
    Path(tempfile.gettempdir())
    / "autonomous_devops_platform_pytest.db"
)

if _test_database_path.exists():
    try:
        _test_database_path.unlink()
    except PermissionError:
        pass

os.environ["DEVOPS_DB_PATH"] = str(
    _test_database_path
)


# ---------------------------------------------------------
# TEST AUTHENTICATION
# ---------------------------------------------------------

def _test_admin_principal():
    """
    Default authenticated identity used by the existing
    API regression tests.

    Dedicated security tests may temporarily remove this
    dependency override to exercise real authentication.
    """

    return AuthenticatedPrincipal(
        subject="pytest-admin",
        role=Role.ADMIN,
        api_key_id="pytest-key",
    )


@pytest.fixture(
    scope="session",
    autouse=True,
)
def configure_test_authentication():
    """
    Authenticate existing API tests without requiring
    every legacy request to manually send an API key.
    """

    from src.api.app import app

    app.dependency_overrides[
        authenticate_api_key
    ] = _test_admin_principal

    yield

    app.dependency_overrides.pop(
        authenticate_api_key,
        None,
    )


def pytest_sessionfinish(
    session,
    exitstatus,
):
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
        pass