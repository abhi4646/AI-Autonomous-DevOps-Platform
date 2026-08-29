import pytest

from src.correlation.signal import (
    OperationalSignal,
    SignalSeverity,
    SignalType,
)


def test_signal_has_generated_identity():
    signal = OperationalSignal(
        signal_type=SignalType.ALERT,
        source="monitoring",
        resource="payments-api",
    )

    assert signal.signal_id
    assert isinstance(
        signal.signal_id,
        str,
    )


def test_signal_preserves_core_fields():
    signal = OperationalSignal(
        signal_type=SignalType.DEPLOYMENT,
        source="kubernetes",
        resource="checkout-api",
        severity=SignalSeverity.HIGH,
        message="Deployment completed",
        agent="kubernetes",
        environment="production",
        correlation_key="checkout-api",
    )

    assert (
        signal.signal_type
        == SignalType.DEPLOYMENT
    )

    assert (
        signal.source
        == "kubernetes"
    )

    assert (
        signal.resource
        == "checkout-api"
    )

    assert (
        signal.severity
        == SignalSeverity.HIGH
    )

    assert (
        signal.environment
        == "production"
    )

    assert (
        signal.correlation_key
        == "checkout-api"
    )


def test_signal_rejects_empty_source():
    with pytest.raises(
        ValueError,
        match="source",
    ):
        OperationalSignal(
            signal_type=SignalType.ALERT,
            source="",
            resource="api",
        )


def test_signal_rejects_whitespace_source():
    with pytest.raises(
        ValueError,
        match="source",
    ):
        OperationalSignal(
            signal_type=SignalType.ALERT,
            source="   ",
            resource="api",
        )


def test_signal_rejects_empty_resource():
    with pytest.raises(
        ValueError,
        match="resource",
    ):
        OperationalSignal(
            signal_type=SignalType.ALERT,
            source="monitoring",
            resource="",
        )


def test_signal_serializes_to_dictionary():
    signal = OperationalSignal(
        signal_type=SignalType.HEALTH,
        source="health-monitor",
        resource="orders-api",
        severity=SignalSeverity.CRITICAL,
        message="Service unhealthy",
        agent="monitoring",
        environment="production",
        incident_id="inc-123",
        correlation_key="orders-api",
        metadata={
            "health_score": 20,
            "region": "ca-central-1",
        },
        occurred_at=(
            "2026-08-27T01:00:00+00:00"
        ),
    )

    data = signal.to_dict()

    assert (
        data["signal_id"]
        == signal.signal_id
    )

    assert (
        data["signal_type"]
        == "health"
    )

    assert (
        data["severity"]
        == "critical"
    )

    assert (
        data["incident_id"]
        == "inc-123"
    )

    assert (
        data["metadata"][
            "health_score"
        ]
        == 20
    )


def test_signal_round_trip_serialization():
    original = OperationalSignal(
        signal_type=SignalType.CODE_CHANGE,
        source="github",
        resource="payments-api",
        severity=SignalSeverity.INFO,
        message="Commit merged",
        agent="github",
        environment="production",
        correlation_key="payments-api",
        metadata={
            "commit_sha": "abc123",
            "branch": "main",
        },
        occurred_at=(
            "2026-08-27T02:00:00+00:00"
        ),
    )

    restored = (
        OperationalSignal.from_dict(
            original.to_dict()
        )
    )

    assert (
        restored.signal_id
        == original.signal_id
    )

    assert (
        restored.signal_type
        == original.signal_type
    )

    assert (
        restored.source
        == original.source
    )

    assert (
        restored.resource
        == original.resource
    )

    assert (
        restored.severity
        == original.severity
    )

    assert (
        restored.metadata
        == original.metadata
    )

    assert (
        restored.occurred_at
        == original.occurred_at
    )


def test_signal_metadata_is_not_shared():
    metadata = {
        "version": "v2"
    }

    signal = OperationalSignal(
        signal_type=SignalType.DEPLOYMENT,
        source="kubernetes",
        resource="api",
        metadata=metadata,
    )

    metadata["version"] = "v3"

    assert (
        signal.metadata["version"]
        == "v2"
    )


def test_signal_supports_incident_link():
    signal = OperationalSignal(
        signal_type=SignalType.INCIDENT,
        source="incident-manager",
        resource="payments-api",
        incident_id="inc-456",
    )

    assert (
        signal.incident_id
        == "inc-456"
    )


def test_signal_supports_rollback_evidence():
    signal = OperationalSignal(
        signal_type=SignalType.ROLLBACK,
        source="kubernetes",
        resource="checkout-api",
        severity=SignalSeverity.HIGH,
        metadata={
            "from_version": "v2",
            "to_version": "v1",
        },
    )

    assert (
        signal.signal_type
        == SignalType.ROLLBACK
    )

    assert (
        signal.metadata[
            "from_version"
        ]
        == "v2"
    )


def test_unknown_signal_type_can_be_restored():
    data = {
        "signal_id": "sig-1",
        "signal_type": "unknown",
        "source": "external",
        "resource": "unknown-resource",
        "severity": "info",
        "message": "",
        "metadata": {},
    }

    signal = (
        OperationalSignal.from_dict(
            data
        )
    )

    assert (
        signal.signal_type
        == SignalType.UNKNOWN
    )