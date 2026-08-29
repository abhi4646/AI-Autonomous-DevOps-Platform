from src.safety.guardrails import SafetyGuardrails
from src.security.auth import AuthenticatedPrincipal
from src.security.rbac import (
    Permission,
    has_permission,
)


def is_destructive_operation(
    request: str,
) -> bool:
    """
    Return True when a request contains language
    associated with a destructive/high-risk operation.

    The classification reuses the platform's existing
    safety guardrail vocabulary so API authorization
    and runtime safety controls remain aligned.
    """

    if not request:
        return False

    request_text = str(request).lower()

    return any(
        keyword in request_text
        for keyword in SafetyGuardrails.HIGH_RISK_KEYWORDS
    )


def can_execute_request(
    principal: AuthenticatedPrincipal,
    request: str,
) -> bool:
    """
    Determine whether a principal is authorized to
    submit the requested operation.

    Normal operations require EXECUTE_OPERATION.

    Destructive operations additionally require
    EXECUTE_DESTRUCTIVE.

    This authorization check does not bypass runtime
    safety guardrails, approval requirements, or
    orchestrator policy.
    """

    if not has_permission(
        principal,
        Permission.EXECUTE_OPERATION,
    ):
        return False

    if not is_destructive_operation(
        request
    ):
        return True

    return has_permission(
        principal,
        Permission.EXECUTE_DESTRUCTIVE,
    )