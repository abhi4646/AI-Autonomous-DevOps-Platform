from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api.app import app
from src.security.auth import authenticate_api_key


client = TestClient(app)


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


def test_public_health_works_without_auth_configuration(
    monkeypatch,
):
    _disable_test_auth_override()

    monkeypatch.delenv(
        "DEVOPS_API_KEY",
        raising=False,
    )

    monkeypatch.delenv(
        "DEVOPS_API_ROLE",
        raising=False,
    )

    try:
        response = client.get(
            "/api/v1/health"
        )

        assert response.status_code == 200

    finally:
        _restore_test_auth_override()


def test_missing_api_key_returns_401(
    monkeypatch,
):
    _disable_test_auth_override()

    monkeypatch.setenv(
        "DEVOPS_API_KEY",
        "configured-secret",
    )

    monkeypatch.setenv(
        "DEVOPS_API_ROLE",
        "admin",
    )

    try:
        response = client.get(
            "/api/v1/audit"
        )

        assert response.status_code == 401

        assert response.json() == {
            "detail": "API key required"
        }

        assert response.headers[
            "www-authenticate"
        ] == "ApiKey"

    finally:
        _restore_test_auth_override()


def test_blank_api_key_returns_401(
    monkeypatch,
):
    _disable_test_auth_override()

    monkeypatch.setenv(
        "DEVOPS_API_KEY",
        "configured-secret",
    )

    monkeypatch.setenv(
        "DEVOPS_API_ROLE",
        "admin",
    )

    try:
        response = client.get(
            "/api/v1/audit",
            headers={
                "X-API-Key": "   ",
            },
        )

        assert response.status_code == 401

        assert response.json() == {
            "detail": "API key required"
        }

        assert response.headers[
            "www-authenticate"
        ] == "ApiKey"

    finally:
        _restore_test_auth_override()


def test_invalid_api_key_returns_401(
    monkeypatch,
):
    _disable_test_auth_override()

    monkeypatch.setenv(
        "DEVOPS_API_KEY",
        "configured-secret",
    )

    monkeypatch.setenv(
        "DEVOPS_API_ROLE",
        "admin",
    )

    try:
        response = client.get(
            "/api/v1/audit",
            headers={
                "X-API-Key": "wrong-secret",
            },
        )

        assert response.status_code == 401

        assert response.json() == {
            "detail": "Invalid API key"
        }

        assert response.headers[
            "www-authenticate"
        ] == "ApiKey"

    finally:
        _restore_test_auth_override()


def test_missing_server_auth_configuration_returns_503(
    monkeypatch,
):
    _disable_test_auth_override()

    monkeypatch.delenv(
        "DEVOPS_API_KEY",
        raising=False,
    )

    monkeypatch.delenv(
        "DEVOPS_API_ROLE",
        raising=False,
    )

    try:
        response = client.get(
            "/api/v1/audit",
            headers={
                "X-API-Key": "anything",
            },
        )

        assert response.status_code == 503

        assert response.json() == {
            "detail": (
                "API authentication "
                "is not configured"
            )
        }

    finally:
        _restore_test_auth_override()


def test_authenticated_but_unauthorized_returns_403(
    monkeypatch,
):
    _disable_test_auth_override()

    monkeypatch.setenv(
        "DEVOPS_API_KEY",
        "viewer-secret",
    )

    monkeypatch.setenv(
        "DEVOPS_API_ROLE",
        "viewer",
    )

    try:
        response = client.get(
            "/api/v1/audit",
            headers={
                "X-API-Key": "viewer-secret",
            },
        )

        assert response.status_code == 403

        assert response.json() == {
            "detail": "Insufficient permissions"
        }

        assert (
            "www-authenticate"
            not in response.headers
        )

    finally:
        _restore_test_auth_override()


def test_missing_credentials_never_reach_orchestrator(
    monkeypatch,
):
    _disable_test_auth_override()

    monkeypatch.setenv(
        "DEVOPS_API_KEY",
        "configured-secret",
    )

    monkeypatch.setenv(
        "DEVOPS_API_ROLE",
        "operator",
    )

    try:
        with patch(
            "src.api.routes.orchestrator.route"
        ) as route_mock:

            response = client.post(
                "/api/v1/execute",
                json={
                    "request": (
                        "check system health"
                    ),
                },
            )

        assert response.status_code == 401

        route_mock.assert_not_called()

    finally:
        _restore_test_auth_override()


def test_invalid_credentials_never_reach_orchestrator(
    monkeypatch,
):
    _disable_test_auth_override()

    monkeypatch.setenv(
        "DEVOPS_API_KEY",
        "configured-secret",
    )

    monkeypatch.setenv(
        "DEVOPS_API_ROLE",
        "operator",
    )

    try:
        with patch(
            "src.api.routes.orchestrator.route"
        ) as route_mock:

            response = client.post(
                "/api/v1/execute",
                headers={
                    "X-API-Key": "wrong-secret",
                },
                json={
                    "request": (
                        "check system health"
                    ),
                },
            )

        assert response.status_code == 401

        route_mock.assert_not_called()

    finally:
        _restore_test_auth_override()