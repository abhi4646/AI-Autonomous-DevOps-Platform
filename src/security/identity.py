from typing import Any

from src.security.auth import AuthenticatedPrincipal


def principal_identity(
    principal: AuthenticatedPrincipal,
) -> dict[str, Any]:
    """
    Convert an authenticated principal into safe
    structured identity metadata.

    Raw API credentials are never included.
    """

    return {
        "subject": principal.subject,
        "role": principal.role.value,
        "api_key_id": principal.api_key_id,
    }


def build_authenticated_context(
    principal: AuthenticatedPrincipal,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build runtime context containing authenticated
    caller identity.

    Existing context values are preserved except for
    the reserved authenticated_principal field, which
    is always derived from the trusted authentication
    result.
    """

    authenticated_context = dict(
        context or {}
    )

    authenticated_context[
        "authenticated_principal"
    ] = principal_identity(
        principal
    )

    return authenticated_context


def identity_from_context(
    context: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """
    Safely extract authenticated identity metadata
    from an orchestration context.
    """

    if not context:
        return None

    identity = context.get(
        "authenticated_principal"
    )

    if not isinstance(
        identity,
        dict,
    ):
        return None

    return dict(identity)