import pytest
from fastapi import HTTPException

from src.security.auth import (
    AuthenticatedPrincipal,
    Role,
)
from src.security.rbac import (
    Permission,
    has_permission,
    permissions_for_role,
    require_any_permission,
    require_permission,
)


def principal(
    role: Role,
) -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        subject="test-user",
        role=role,
        api_key_id="test-key",
    )


def test_viewer_has_read_permissions():
    user = principal(Role.VIEWER)

    assert has_permission(
        user,
        Permission.READ_PLATFORM,
    )

    assert has_permission(
        user,
        Permission.READ_EXECUTIONS,
    )

    assert has_permission(
        user,
        Permission.READ_INCIDENTS,
    )

    assert has_permission(
        user,
        Permission.READ_SIGNALS,
    )

    assert has_permission(
        user,
        Permission.READ_RCA,
    )


def test_viewer_cannot_execute():
    user = principal(Role.VIEWER)

    assert not has_permission(
        user,
        Permission.EXECUTE_OPERATION,
    )


def test_viewer_cannot_create_signals():
    user = principal(Role.VIEWER)

    assert not has_permission(
        user,
        Permission.CREATE_SIGNALS,
    )


def test_viewer_cannot_decide_approvals():
    user = principal(Role.VIEWER)

    assert not has_permission(
        user,
        Permission.DECIDE_APPROVALS,
    )


def test_operator_can_execute():
    user = principal(Role.OPERATOR)

    assert has_permission(
        user,
        Permission.EXECUTE_OPERATION,
    )


def test_operator_can_create_signals():
    user = principal(Role.OPERATOR)

    assert has_permission(
        user,
        Permission.CREATE_SIGNALS,
    )


def test_operator_can_run_rca():
    user = principal(Role.OPERATOR)

    assert has_permission(
        user,
        Permission.RUN_RCA,
    )


def test_operator_cannot_decide_approvals():
    user = principal(Role.OPERATOR)

    assert not has_permission(
        user,
        Permission.DECIDE_APPROVALS,
    )


def test_approver_can_read_approvals():
    user = principal(Role.APPROVER)

    assert has_permission(
        user,
        Permission.READ_APPROVALS,
    )


def test_approver_can_decide_approvals():
    user = principal(Role.APPROVER)

    assert has_permission(
        user,
        Permission.DECIDE_APPROVALS,
    )


def test_approver_can_read_audit():
    user = principal(Role.APPROVER)

    assert has_permission(
        user,
        Permission.READ_AUDIT,
    )


def test_approver_cannot_execute():
    user = principal(Role.APPROVER)

    assert not has_permission(
        user,
        Permission.EXECUTE_OPERATION,
    )


@pytest.mark.parametrize(
    "permission",
    list(Permission),
)
def test_admin_has_every_permission(
    permission,
):
    user = principal(Role.ADMIN)

    assert has_permission(
        user,
        permission,
    )


def test_permissions_are_immutable():
    permissions = permissions_for_role(
        Role.VIEWER
    )

    assert isinstance(
        permissions,
        frozenset,
    )


def test_require_permission_allows_authorized_user():
    dependency = require_permission(
        Permission.EXECUTE_OPERATION
    )

    user = principal(Role.OPERATOR)

    result = dependency(user)

    assert result is user


def test_require_permission_rejects_unauthorized_user():
    dependency = require_permission(
        Permission.EXECUTE_OPERATION
    )

    user = principal(Role.VIEWER)

    with pytest.raises(
        HTTPException
    ) as exc_info:
        dependency(user)

    assert exc_info.value.status_code == 403
    assert (
        exc_info.value.detail
        == "Insufficient permissions"
    )


def test_require_any_permission_allows_matching_permission():
    dependency = require_any_permission(
        Permission.EXECUTE_OPERATION,
        Permission.DECIDE_APPROVALS,
    )

    user = principal(Role.APPROVER)

    result = dependency(user)

    assert result is user


def test_require_any_permission_rejects_without_match():
    dependency = require_any_permission(
        Permission.EXECUTE_OPERATION,
        Permission.DECIDE_APPROVALS,
    )

    user = principal(Role.VIEWER)

    with pytest.raises(
        HTTPException
    ) as exc_info:
        dependency(user)

    assert exc_info.value.status_code == 403


def test_require_any_permission_requires_permissions():
    with pytest.raises(
        ValueError,
        match="At least one permission is required",
    ):
        require_any_permission()