from src.audit.audit_logger import AuditLogger


def test_audit_logger_records_authenticated_identity():
    logger = AuditLogger()

    identity = {
        "subject": "api-user",
        "role": "operator",
        "api_key_id": "abc123",
    }

    event = logger.log(
        request="check system health",
        action="execute",
        agent="monitoring",
        identity=identity,
    )

    assert event[
        "metadata"
    ][
        "authenticated_principal"
    ] == identity


def test_audit_logger_preserves_existing_metadata():
    logger = AuditLogger()

    event = logger.log(
        request="deploy application",
        action="approval_requested",
        metadata={
            "approval_id": "approval-123",
        },
        identity={
            "subject": "api-user",
            "role": "operator",
            "api_key_id": "abc123",
        },
    )

    assert event[
        "metadata"
    ][
        "approval_id"
    ] == "approval-123"

    assert event[
        "metadata"
    ][
        "authenticated_principal"
    ][
        "subject"
    ] == "api-user"


def test_identity_overrides_spoofed_metadata_identity():
    logger = AuditLogger()

    event = logger.log(
        request="check system health",
        action="execute",
        metadata={
            "authenticated_principal": {
                "subject": "attacker",
                "role": "admin",
                "api_key_id": "fake",
            }
        },
        identity={
            "subject": "trusted-user",
            "role": "operator",
            "api_key_id": "trusted-key",
        },
    )

    assert event[
        "metadata"
    ][
        "authenticated_principal"
    ] == {
        "subject": "trusted-user",
        "role": "operator",
        "api_key_id": "trusted-key",
    }


def test_audit_logger_remains_backward_compatible():
    logger = AuditLogger()

    event = logger.log(
        request="check docker containers",
        action="execute",
        agent="docker",
    )

    assert (
        "authenticated_principal"
        not in event["metadata"]
    )


def test_identity_is_copied_before_storage():
    logger = AuditLogger()

    identity = {
        "subject": "api-user",
        "role": "operator",
        "api_key_id": "abc123",
    }

    event = logger.log(
        request="check system health",
        action="execute",
        identity=identity,
    )

    identity["role"] = "admin"

    assert event[
        "metadata"
    ][
        "authenticated_principal"
    ][
        "role"
    ] == "operator"