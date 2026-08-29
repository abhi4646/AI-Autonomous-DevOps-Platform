import hashlib
import hmac
import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader


class Role(str, Enum):
    """
    Platform roles used by the API authorization layer.
    """

    VIEWER = "viewer"
    OPERATOR = "operator"
    APPROVER = "approver"
    ADMIN = "admin"


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    """
    Identity established after successful API authentication.
    """

    subject: str
    role: Role
    api_key_id: Optional[str] = None


api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
)


def _hash_api_key(api_key: str) -> str:
    """
    Return a deterministic SHA-256 digest for an API key.

    Raw API keys should not be persisted or logged.
    """

    return hashlib.sha256(
        api_key.encode("utf-8")
    ).hexdigest()


def _configured_api_key() -> Optional[str]:
    """
    Return the API key configured for the current environment.
    """

    value = os.getenv("DEVOPS_API_KEY")

    if value is None:
        return None

    value = value.strip()

    return value or None


def _configured_role() -> Role:
    """
    Return the role assigned to the configured API key.
    """

    raw_role = os.getenv(
        "DEVOPS_API_ROLE",
        Role.ADMIN.value,
    ).strip().lower()

    try:
        return Role(raw_role)

    except ValueError as exc:
        raise RuntimeError(
            "DEVOPS_API_ROLE must be one of: "
            + ", ".join(role.value for role in Role)
        ) from exc


def authenticate_api_key(
    api_key: Optional[str] = Security(api_key_header),
) -> AuthenticatedPrincipal:
    """
    Authenticate an API request using the X-API-Key header.

    Authentication is fail-closed:

    - missing server configuration -> 503
    - missing client credential -> 401
    - invalid credential -> 401
    - valid credential -> authenticated principal
    """

    configured_key = _configured_api_key()

    if configured_key is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API authentication is not configured",
        )

    if api_key is None or not api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={
                "WWW-Authenticate": "ApiKey",
            },
        )

    if not hmac.compare_digest(
        api_key,
        configured_key,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={
                "WWW-Authenticate": "ApiKey",
            },
        )

    return AuthenticatedPrincipal(
        subject="api-key-user",
        role=_configured_role(),
        api_key_id=_hash_api_key(
            configured_key
        )[:12],
    )