from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api.app import app
from src.security.auth import (
    AuthenticatedPrincipal,
    Role,
    authenticate_api_key,
)


client = TestClient(app)


def _authenticated_approver():
    return AuthenticatedPrincipal(
        subject="authenticated-approver",
        role=Role.APPROVER,
        api_key_id="approval-test-key",
    )


def _override_approver():
    app.dependency_overrides[
        authenticate_api_key
    ] = _authenticated_approver


def _restore_test_auth_override():
    from tests.conftest import (
        _test_admin_principal,
    )

    app.dependency_overrides[
        authenticate_api_key
    ] = _test_admin_principal


def test_approval_uses_authenticated_identity_not_payload():
    _override_approver()

    approval = {
        "status": "approved",
        "approval_id": "approval-123",
        "decided_by": "authenticated-approver",
        "decided_at": "2026-08-29T12:00:00+00:00",
        "reason": "Reviewed",
    }

    try:
        with patch(
            "src.api.routes.orchestrator."
            "approval_manager.approve",
            return_value=approval,
        ) as approve_mock:

            response = client.post(
                "/api/v1/approvals/decision",
                json={
                    "approval_id": "approval-123",
                    "decided_by": "spoofed-admin",
                    "decision": "approved",
                    "reason": "Reviewed",
                },
            )

        assert response.status_code == 200

        approve_mock.assert_called_once_with(
            approval_id="approval-123",
            decided_by="authenticated-approver",
            reason="Reviewed",
        )

        assert response.json()[
            "decided_by"
        ] == "authenticated-approver"

    finally:
        _restore_test_auth_override()


def test_rejection_uses_authenticated_identity_not_payload():
    _override_approver()

    approval = {
        "status": "rejected",
        "approval_id": "approval-456",
        "decided_by": "authenticated-approver",
        "decided_at": "2026-08-29T12:00:00+00:00",
        "reason": "Unsafe operation",
    }

    try:
        with patch(
            "src.api.routes.orchestrator."
            "approval_manager.reject",
            return_value=approval,
        ) as reject_mock:

            response = client.post(
                "/api/v1/approvals/decision",
                json={
                    "approval_id": "approval-456",
                    "decided_by": "spoofed-admin",
                    "decision": "rejected",
                    "reason": "Unsafe operation",
                },
            )

        assert response.status_code == 200

        reject_mock.assert_called_once_with(
            approval_id="approval-456",
            decided_by="authenticated-approver",
            reason="Unsafe operation",
        )

        assert response.json()[
            "decided_by"
        ] == "authenticated-approver"

    finally:
        _restore_test_auth_override()