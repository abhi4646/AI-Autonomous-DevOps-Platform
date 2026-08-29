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


def test_health_is_public(
    monkeypatch,
):
    _disable_test_auth_override()

    monkeypatch.delenv(
        "DEVOPS_API_KEY",
        raising=False,
    )

    try:
        response = client.get(
            "/api/v1/health"
        )

        assert response.status_code == 200

    finally:
        _restore_test_auth_override()


def test_protected_route_requires_api_key(
    monkeypatch,
):
    _disable_test_auth_override()

    monkeypatch.setenv(
        "DEVOPS_API_KEY",
        "test-secret",
    )

    try:
        response = client.get(
            "/api/v1/executions"
        )

        assert response.status_code == 401

        assert (
            response.json()["detail"]
            == "API key required"
        )

    finally:
        _restore_test_auth_override()


def test_invalid_api_key_is_rejected(
    monkeypatch,
):
    _disable_test_auth_override()

    monkeypatch.setenv(
        "DEVOPS_API_KEY",
        "correct-secret",
    )

    try:
        response = client.get(
            "/api/v1/executions",
            headers={
                "X-API-Key": "wrong-secret",
            },
        )

        assert response.status_code == 401

        assert (
            response.json()["detail"]
            == "Invalid API key"
        )

    finally:
        _restore_test_auth_override()


def test_viewer_can_read_executions(
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
            "/api/v1/executions",
            headers={
                "X-API-Key": "viewer-secret",
            },
        )

        assert response.status_code == 200

    finally:
        _restore_test_auth_override()


def test_viewer_cannot_read_audit(
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

        assert (
            response.json()["detail"]
            == "Insufficient permissions"
        )

    finally:
        _restore_test_auth_override()


def test_approver_can_read_audit(
    monkeypatch,
):
    _disable_test_auth_override()

    monkeypatch.setenv(
        "DEVOPS_API_KEY",
        "approver-secret",
    )
    monkeypatch.setenv(
        "DEVOPS_API_ROLE",
        "approver",
    )

    try:
        response = client.get(
            "/api/v1/audit",
            headers={
                "X-API-Key": "approver-secret",
            },
        )

        assert response.status_code == 200

    finally:
        _restore_test_auth_override()


def test_operator_cannot_read_audit(
    monkeypatch,
):
    _disable_test_auth_override()

    monkeypatch.setenv(
        "DEVOPS_API_KEY",
        "operator-secret",
    )
    monkeypatch.setenv(
        "DEVOPS_API_ROLE",
        "operator",
    )

    try:
        response = client.get(
            "/api/v1/audit",
            headers={
                "X-API-Key": "operator-secret",
            },
        )

        assert response.status_code == 403

    finally:
        _restore_test_auth_override()


def test_admin_can_read_audit(
    monkeypatch,
):
    _disable_test_auth_override()

    monkeypatch.setenv(
        "DEVOPS_API_KEY",
        "admin-secret",
    )
    monkeypatch.setenv(
        "DEVOPS_API_ROLE",
        "admin",
    )

    try:
        response = client.get(
            "/api/v1/audit",
            headers={
                "X-API-Key": "admin-secret",
            },
        )

        assert response.status_code == 200

    finally:
        _restore_test_auth_override()