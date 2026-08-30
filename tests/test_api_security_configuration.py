from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api.app import app
from src.security.auth import authenticate_api_key


client = TestClient(
    app,
    raise_server_exceptions=False,
)


def _disable_test_auth_override():
    app.dependency_overrides.pop(
        authenticate_api_key,
        None,
    )


def _restore_test_auth_override():
    from tests.conftest import (
        _test_admin_principal,
    )

    app.dependency_overrides[
        authenticate_api_key
    ] = _test_admin_principal


def test_invalid_server_role_configuration_fails_closed(
    monkeypatch,
):
    _disable_test_auth_override()

    monkeypatch.setenv(
        "DEVOPS_API_KEY",
        "configured-secret",
    )

    monkeypatch.setenv(
        "DEVOPS_API_ROLE",
        "superuser",
    )

    try:
        response = client.get(
            "/api/v1/audit",
            headers={
                "X-API-Key": "configured-secret",
            },
        )

        assert response.status_code == 503

        assert response.json() == {
            "detail": (
                "API authorization "
                "is misconfigured"
            )
        }

    finally:
        _restore_test_auth_override()


def test_invalid_role_never_reaches_orchestrator(
    monkeypatch,
):
    _disable_test_auth_override()

    monkeypatch.setenv(
        "DEVOPS_API_KEY",
        "configured-secret",
    )

    monkeypatch.setenv(
        "DEVOPS_API_ROLE",
        "invalid-role",
    )

    try:
        with patch(
            "src.api.routes.orchestrator.route"
        ) as route_mock:

            response = client.post(
                "/api/v1/execute",
                headers={
                    "X-API-Key": "configured-secret",
                },
                json={
                    "request": (
                        "check system health"
                    ),
                },
            )

        assert response.status_code == 503

        route_mock.assert_not_called()

    finally:
        _restore_test_auth_override()


def test_role_configuration_is_case_insensitive(
    monkeypatch,
):
    _disable_test_auth_override()

    monkeypatch.setenv(
        "DEVOPS_API_KEY",
        "configured-secret",
    )

    monkeypatch.setenv(
        "DEVOPS_API_ROLE",
        "ADMIN",
    )

    try:
        response = client.get(
            "/api/v1/audit",
            headers={
                "X-API-Key": "configured-secret",
            },
        )

        assert response.status_code == 200

    finally:
        _restore_test_auth_override()


def test_role_configuration_ignores_outer_whitespace(
    monkeypatch,
):
    _disable_test_auth_override()

    monkeypatch.setenv(
        "DEVOPS_API_KEY",
        "configured-secret",
    )

    monkeypatch.setenv(
        "DEVOPS_API_ROLE",
        "  admin  ",
    )

    try:
        response = client.get(
            "/api/v1/audit",
            headers={
                "X-API-Key": "configured-secret",
            },
        )

        assert response.status_code == 200

    finally:
        _restore_test_auth_override()