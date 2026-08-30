import pytest
from fastapi import HTTPException

from src.security.auth import (
    AuthenticatedPrincipal,
    Role,
    _configured_role,
    _hash_api_key,
    authenticate_api_key,
)


@pytest.fixture(autouse=True)
def clean_auth_environment(monkeypatch):
    monkeypatch.delenv(
        "DEVOPS_API_KEY",
        raising=False,
    )
    monkeypatch.delenv(
        "DEVOPS_API_ROLE",
        raising=False,
    )


def test_hash_api_key_is_deterministic():
    first = _hash_api_key("secret-key")
    second = _hash_api_key("secret-key")

    assert first == second
    assert first != "secret-key"
    assert len(first) == 64


def test_default_role_is_admin():
    assert _configured_role() == Role.ADMIN


@pytest.mark.parametrize(
    ("configured", "expected"),
    [
        ("viewer", Role.VIEWER),
        ("operator", Role.OPERATOR),
        ("approver", Role.APPROVER),
        ("admin", Role.ADMIN),
        ("ADMIN", Role.ADMIN),
    ],
)
def test_configured_role(
    monkeypatch,
    configured,
    expected,
):
    monkeypatch.setenv(
        "DEVOPS_API_ROLE",
        configured,
    )

    assert _configured_role() == expected


def test_invalid_configured_role_raises(
    monkeypatch,
):
    monkeypatch.setenv(
        "DEVOPS_API_ROLE",
        "superuser",
    )

    with pytest.raises(
        RuntimeError,
        match="DEVOPS_API_ROLE must be one of",
    ):
        _configured_role()


def test_authentication_fails_closed_when_unconfigured():
    with pytest.raises(HTTPException) as exc_info:
        authenticate_api_key(None)

    assert exc_info.value.status_code == 503
    assert (
        exc_info.value.detail
        == "API authentication is not configured"
    )


def test_missing_api_key_is_unauthorized(
    monkeypatch,
):
    monkeypatch.setenv(
        "DEVOPS_API_KEY",
        "correct-secret",
    )

    with pytest.raises(HTTPException) as exc_info:
        authenticate_api_key(None)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "API key required"


def test_blank_api_key_is_unauthorized(
    monkeypatch,
):
    monkeypatch.setenv(
        "DEVOPS_API_KEY",
        "correct-secret",
    )

    with pytest.raises(HTTPException) as exc_info:
        authenticate_api_key("   ")

    assert exc_info.value.status_code == 401


def test_invalid_api_key_is_unauthorized(
    monkeypatch,
):
    monkeypatch.setenv(
        "DEVOPS_API_KEY",
        "correct-secret",
    )

    with pytest.raises(HTTPException) as exc_info:
        authenticate_api_key(
            "wrong-secret"
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid API key"


def test_valid_api_key_returns_principal(
    monkeypatch,
):
    monkeypatch.setenv(
        "DEVOPS_API_KEY",
        "correct-secret",
    )
    monkeypatch.setenv(
        "DEVOPS_API_ROLE",
        "operator",
    )

    principal = authenticate_api_key(
        "correct-secret"
    )

    assert isinstance(
        principal,
        AuthenticatedPrincipal,
    )
    assert principal.subject == "api-key-user"
    assert principal.role == Role.OPERATOR
    assert principal.api_key_id is not None
    assert len(principal.api_key_id) == 12


def test_raw_api_key_not_exposed_in_principal(
    monkeypatch,
):
    secret = "do-not-expose-this"

    monkeypatch.setenv(
        "DEVOPS_API_KEY",
        secret,
    )

    principal = authenticate_api_key(
        secret
    )

    assert secret not in repr(principal)
    assert principal.api_key_id != secret