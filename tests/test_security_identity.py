from src.security.auth import (
    AuthenticatedPrincipal,
    Role,
)
from src.security.identity import (
    build_authenticated_context,
    identity_from_context,
    principal_identity,
)


def principal(
    role: Role = Role.OPERATOR,
) -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        subject="api-user",
        role=role,
        api_key_id="abc123def456",
    )


def test_principal_identity_contains_safe_identity():
    identity = principal_identity(
        principal()
    )

    assert identity == {
        "subject": "api-user",
        "role": "operator",
        "api_key_id": "abc123def456",
    }


def test_principal_identity_does_not_contain_raw_api_key():
    identity = principal_identity(
        principal()
    )

    assert "api_key" not in identity
    assert "secret" not in identity


def test_build_authenticated_context_adds_identity():
    context = build_authenticated_context(
        principal()
    )

    assert context[
        "authenticated_principal"
    ] == {
        "subject": "api-user",
        "role": "operator",
        "api_key_id": "abc123def456",
    }


def test_build_authenticated_context_preserves_existing_values():
    context = build_authenticated_context(
        principal(),
        {
            "environment": "production",
            "incident_id": "INC-123",
        },
    )

    assert context[
        "environment"
    ] == "production"

    assert context[
        "incident_id"
    ] == "INC-123"

    assert context[
        "authenticated_principal"
    ]["subject"] == "api-user"


def test_authenticated_identity_cannot_be_spoofed_by_context():
    context = build_authenticated_context(
        principal(),
        {
            "authenticated_principal": {
                "subject": "attacker",
                "role": "admin",
                "api_key_id": "fake",
            }
        },
    )

    assert context[
        "authenticated_principal"
    ] == {
        "subject": "api-user",
        "role": "operator",
        "api_key_id": "abc123def456",
    }


def test_identity_from_context_returns_identity_copy():
    context = build_authenticated_context(
        principal(Role.ADMIN)
    )

    identity = identity_from_context(
        context
    )

    assert identity == {
        "subject": "api-user",
        "role": "admin",
        "api_key_id": "abc123def456",
    }

    assert (
        identity
        is not context[
            "authenticated_principal"
        ]
    )


def test_identity_from_empty_context_returns_none():
    assert identity_from_context(
        None
    ) is None

    assert identity_from_context(
        {}
    ) is None


def test_identity_from_invalid_context_returns_none():
    assert identity_from_context(
        {
            "authenticated_principal": (
                "not-a-dictionary"
            )
        }
    ) is None