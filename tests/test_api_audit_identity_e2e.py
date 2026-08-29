import hashlib

from fastapi.testclient import TestClient

from src.api.app import app
from src.api.routes import database
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


def test_authenticated_identity_is_persisted_in_audit(
    monkeypatch,
):
    _disable_test_auth_override()

    api_key = "phase27e-admin-secret"

    monkeypatch.setenv(
        "DEVOPS_API_KEY",
        api_key,
    )

    monkeypatch.setenv(
        "DEVOPS_API_ROLE",
        "admin",
    )

    expected_key_id = hashlib.sha256(
        api_key.encode("utf-8")
    ).hexdigest()[:12]

    before_events = (
        database.get_audit_events()
    )

    before_ids = {
        event["id"]
        for event in before_events
    }

    try:
        response = client.post(
            "/api/v1/execute",
            headers={
                "X-API-Key": api_key,
            },
            json={
                "request": (
                    "terraform destroy production"
                ),
            },
        )

        assert response.status_code == 200

        body = response.json()

        assert body[
            "status"
        ] == "blocked"

        events = (
            database.get_audit_events()
        )

        new_events = [
            event
            for event in events
            if event["id"] not in before_ids
        ]

        assert len(new_events) >= 1

        block_events = [
            event
            for event in new_events
            if event[
                "event_type"
            ] == "block"
        ]

        assert len(block_events) == 1

        audit_event = block_events[0]

        persisted_metadata = (
            audit_event["metadata"]
        )

        assert (
            persisted_metadata[
                "request"
            ]
            == "terraform destroy production"
        )

        identity = (
            persisted_metadata[
                "metadata"
            ][
                "authenticated_principal"
            ]
        )

        assert identity == {
            "subject": "api-key-user",
            "role": "admin",
            "api_key_id": expected_key_id,
        }

        assert (
            api_key
            not in str(audit_event)
        )

    finally:
        _restore_test_auth_override()


def test_audit_endpoint_returns_persisted_identity(
    monkeypatch,
):
    _disable_test_auth_override()

    api_key = "phase27e-audit-secret"

    monkeypatch.setenv(
        "DEVOPS_API_KEY",
        api_key,
    )

    monkeypatch.setenv(
        "DEVOPS_API_ROLE",
        "admin",
    )

    expected_key_id = hashlib.sha256(
        api_key.encode("utf-8")
    ).hexdigest()[:12]

    try:
        execute_response = client.post(
            "/api/v1/execute",
            headers={
                "X-API-Key": api_key,
            },
            json={
                "request": (
                    "terraform destroy production"
                ),
            },
        )

        assert (
            execute_response.status_code
            == 200
        )

        audit_response = client.get(
            "/api/v1/audit",
            headers={
                "X-API-Key": api_key,
            },
        )

        assert (
            audit_response.status_code
            == 200
        )

        events = audit_response.json()

        matching_events = [
            event
            for event in events
            if (
                event["event_type"]
                == "block"
                and event[
                    "metadata"
                ].get(
                    "request"
                )
                == (
                    "terraform destroy production"
                )
            )
        ]

        assert matching_events

        latest_event = (
            matching_events[-1]
        )

        identity = (
            latest_event[
                "metadata"
            ][
                "metadata"
            ][
                "authenticated_principal"
            ]
        )

        assert identity[
            "subject"
        ] == "api-key-user"

        assert identity[
            "role"
        ] == "admin"

        assert identity[
            "api_key_id"
        ] == expected_key_id

        assert (
            api_key
            not in str(latest_event)
        )

    finally:
        _restore_test_auth_override()