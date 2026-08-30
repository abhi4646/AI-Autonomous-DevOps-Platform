import pytest

from src.security.auth import (
    AuthenticatedPrincipal,
    Role,
)
from src.security.operations import (
    can_execute_request,
    is_destructive_operation,
)


def principal(
    role: Role,
) -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        subject="test-user",
        role=role,
        api_key_id="test-key",
    )


@pytest.mark.parametrize(
    "request_text",
    [
        "terraform destroy production",
        "kubectl delete deployment api",
        "delete the production database",
        "destroy the infrastructure",
        "drop database",
        "terminate production instance",
        "wipe persistent storage",
        "shutdown production",
        "force delete pod",
        "remove production deployment",
    ],
)
def test_destructive_operations_are_detected(
    request_text,
):
    assert is_destructive_operation(
        request_text
    )


@pytest.mark.parametrize(
    "request_text",
    [
        "check docker containers",
        "show terraform plan",
        "inspect kubernetes pods",
        "get system health",
        "restart api service",
        "deploy application",
        "terraform apply",
    ],
)
def test_non_destructive_operations_are_not_classified_as_destructive(
    request_text,
):
    assert not is_destructive_operation(
        request_text
    )


def test_empty_request_is_not_destructive():
    assert not is_destructive_operation("")


def test_viewer_cannot_execute_normal_operation():
    assert not can_execute_request(
        principal(Role.VIEWER),
        "check docker containers",
    )


def test_operator_can_execute_normal_operation():
    assert can_execute_request(
        principal(Role.OPERATOR),
        "check docker containers",
    )


def test_operator_cannot_execute_destructive_operation():
    assert not can_execute_request(
        principal(Role.OPERATOR),
        "terraform destroy production",
    )


def test_approver_cannot_execute_operation():
    assert not can_execute_request(
        principal(Role.APPROVER),
        "check docker containers",
    )


def test_admin_can_submit_normal_operation():
    assert can_execute_request(
        principal(Role.ADMIN),
        "check docker containers",
    )


def test_admin_can_submit_destructive_operation():
    assert can_execute_request(
        principal(Role.ADMIN),
        "terraform destroy production",
    )