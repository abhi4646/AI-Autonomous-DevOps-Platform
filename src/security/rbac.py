from enum import Enum
from typing import Callable

from fastapi import Depends, HTTPException, status

from src.security.auth import (
    AuthenticatedPrincipal,
    Role,
    authenticate_api_key,
)


class Permission(str, Enum):
    """
    Fine-grained platform permissions.

    Roles are mapped to permissions below.
    API routes should depend on permissions rather
    than checking role names directly.
    """

    READ_PLATFORM = "read_platform"
    READ_EXECUTIONS = "read_executions"
    READ_METRICS = "read_metrics"
    READ_AUDIT = "read_audit"

    EXECUTE_OPERATION = "execute_operation"

    READ_APPROVALS = "read_approvals"
    DECIDE_APPROVALS = "decide_approvals"

    READ_INCIDENTS = "read_incidents"

    READ_SIGNALS = "read_signals"
    CREATE_SIGNALS = "create_signals"

    READ_RCA = "read_rca"
    RUN_RCA = "run_rca"

    ADMIN = "admin"


ROLE_PERMISSIONS: dict[
    Role,
    frozenset[Permission],
] = {
    Role.VIEWER: frozenset(
        {
            Permission.READ_PLATFORM,
            Permission.READ_EXECUTIONS,
            Permission.READ_METRICS,
            Permission.READ_INCIDENTS,
            Permission.READ_SIGNALS,
            Permission.READ_RCA,
        }
    ),

    Role.OPERATOR: frozenset(
        {
            Permission.READ_PLATFORM,
            Permission.READ_EXECUTIONS,
            Permission.READ_METRICS,
            Permission.READ_INCIDENTS,
            Permission.READ_SIGNALS,
            Permission.CREATE_SIGNALS,
            Permission.READ_RCA,
            Permission.RUN_RCA,
            Permission.EXECUTE_OPERATION,
        }
    ),

    Role.APPROVER: frozenset(
        {
            Permission.READ_PLATFORM,
            Permission.READ_EXECUTIONS,
            Permission.READ_METRICS,
            Permission.READ_AUDIT,
            Permission.READ_APPROVALS,
            Permission.DECIDE_APPROVALS,
            Permission.READ_INCIDENTS,
            Permission.READ_SIGNALS,
            Permission.READ_RCA,
        }
    ),

    Role.ADMIN: frozenset(
        set(Permission)
    ),
}


def permissions_for_role(
    role: Role,
) -> frozenset[Permission]:
    """
    Return the immutable permission set assigned
    to a platform role.
    """

    return ROLE_PERMISSIONS.get(
        role,
        frozenset(),
    )


def has_permission(
    principal: AuthenticatedPrincipal,
    permission: Permission,
) -> bool:
    """
    Return True when the authenticated principal
    is authorized for the supplied permission.
    """

    permissions = permissions_for_role(
        principal.role
    )

    return (
        Permission.ADMIN in permissions
        or permission in permissions
    )


def require_permission(
    permission: Permission,
) -> Callable[
    [AuthenticatedPrincipal],
    AuthenticatedPrincipal,
]:
    """
    Build a reusable FastAPI dependency enforcing
    one permission.

    Authentication failures are handled first by
    authenticate_api_key.

    Authenticated users lacking the permission
    receive HTTP 403.
    """

    def dependency(
        principal: AuthenticatedPrincipal = Depends(
            authenticate_api_key
        ),
    ) -> AuthenticatedPrincipal:

        if not has_permission(
            principal,
            permission,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return principal

    return dependency


def require_any_permission(
    *permissions: Permission,
) -> Callable[
    [AuthenticatedPrincipal],
    AuthenticatedPrincipal,
]:
    """
    Build a dependency allowing access when the
    authenticated principal owns at least one of
    the requested permissions.
    """

    if not permissions:
        raise ValueError(
            "At least one permission is required"
        )

    def dependency(
        principal: AuthenticatedPrincipal = Depends(
            authenticate_api_key
        ),
    ) -> AuthenticatedPrincipal:

        if not any(
            has_permission(
                principal,
                permission,
            )
            for permission in permissions
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return principal

    return dependency