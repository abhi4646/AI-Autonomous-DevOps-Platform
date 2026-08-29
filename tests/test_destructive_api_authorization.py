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


def test_operator_destructive_request_is_forbidden(
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
        with patch(
            "src.api.routes.orchestrator.route"
        ) as route_mock:

            response = client.post(
                "/api/v1/execute",
                headers={
                    "X-API-Key": "operator-secret",
                },
                json={
                    "request": (
                        "terraform destroy production"
                    ),
                },
            )

        assert response.status_code == 403

        assert response.json() == {
            "detail": (
                "Destructive operation requires "
                "elevated permissions"
            )
        }

        route_mock.assert_not_called()

    finally:
        _restore_test_auth_override()


def test_operator_normal_request_reaches_orchestrator(
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

    expected_result = {
        "status": "ok",
        "agent": "monitoring",
    }

    try:
        with patch(
            "src.api.routes.orchestrator.route",
            return_value=expected_result,
        ) as route_mock:

            response = client.post(
                "/api/v1/execute",
                headers={
                    "X-API-Key": "operator-secret",
                },
                json={
                    "request": (
                        "check system health"
                    ),
                },
            )

        assert response.status_code == 200
        assert response.json() == expected_result

        route_mock.assert_called_once()

        call_kwargs = (
            route_mock.call_args.kwargs
        )

        assert call_kwargs[
            "request"
        ] == "check system health"

        assert call_kwargs[
            "approval_id"
        ] is None

        identity = call_kwargs[
            "context"
        ][
            "authenticated_principal"
        ]

        assert identity[
            "subject"
        ] == "api-key-user"

        assert identity[
            "role"
        ] == "operator"

        assert identity[
            "api_key_id"
        ] is not None

        assert (
            "operator-secret"
            not in str(
                call_kwargs["context"]
            )
        )

    finally:
        _restore_test_auth_override()


def test_admin_destructive_request_reaches_safety_pipeline(
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

    expected_result = {
        "status": "blocked",
        "risk": "high",
        "message": (
            "Potentially destructive operation detected"
        ),
    }

    try:
        with patch(
            "src.api.routes.orchestrator.route",
            return_value=expected_result,
        ) as route_mock:

            response = client.post(
                "/api/v1/execute",
                headers={
                    "X-API-Key": "admin-secret",
                },
                json={
                    "request": (
                        "terraform destroy production"
                    ),
                },
            )

        assert response.status_code == 200
        assert response.json() == expected_result

        route_mock.assert_called_once()

        call_kwargs = (
            route_mock.call_args.kwargs
        )

        assert call_kwargs[
            "request"
        ] == (
            "terraform destroy production"
        )

        assert call_kwargs[
            "approval_id"
        ] is None

        identity = call_kwargs[
            "context"
        ][
            "authenticated_principal"
        ]

        assert identity[
            "subject"
        ] == "api-key-user"

        assert identity[
            "role"
        ] == "admin"

        assert identity[
            "api_key_id"
        ] is not None

        assert (
            "admin-secret"
            not in str(
                call_kwargs["context"]
            )
        )

    finally:
        _restore_test_auth_override()


def test_viewer_cannot_execute_before_operation_check(
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
        with patch(
            "src.api.routes.orchestrator.route"
        ) as route_mock:

            response = client.post(
                "/api/v1/execute",
                headers={
                    "X-API-Key": "viewer-secret",
                },
                json={
                    "request": (
                        "check system health"
                    ),
                },
            )

        assert response.status_code == 403

        assert response.json() == {
            "detail": "Insufficient permissions"
        }

        route_mock.assert_not_called()

    finally:
        _restore_test_auth_override()