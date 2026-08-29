import pytest

from src.correlation.engine import (
    IncidentCorrelationEngine,
)
from src.correlation.signal import (
    OperationalSignal,
    SignalSeverity,
    SignalType,
)


def make_signal(
    signal_type,
    *,
    source,
    resource="payments-api",
    severity=SignalSeverity.INFO,
    environment="production",
    correlation_key="payments-api",
    incident_id=None,
    occurred_at="2026-08-27T10:00:00+00:00",
):
    return OperationalSignal(
        signal_type=signal_type,
        source=source,
        resource=resource,
        severity=severity,
        environment=environment,
        correlation_key=correlation_key,
        incident_id=incident_id,
        occurred_at=occurred_at,
    )


def test_matching_operational_signals_correlate():
    engine = IncidentCorrelationEngine()

    deployment = make_signal(
        SignalType.DEPLOYMENT,
        source="kubernetes",
        occurred_at=(
            "2026-08-27T10:00:00+00:00"
        ),
    )

    alert = make_signal(
        SignalType.ALERT,
        source="monitoring",
        severity=SignalSeverity.HIGH,
        occurred_at=(
            "2026-08-27T10:04:00+00:00"
        ),
    )

    result = engine.score_pair(
        deployment,
        alert,
    )

    assert result["correlated"] is True
    assert result["score"] >= 0.60


def test_different_resources_do_not_strongly_correlate():
    engine = IncidentCorrelationEngine()

    first = make_signal(
        SignalType.DEPLOYMENT,
        source="kubernetes",
        resource="payments-api",
        correlation_key="payments-api",
    )

    second = make_signal(
        SignalType.ALERT,
        source="monitoring",
        resource="inventory-api",
        correlation_key="inventory-api",
    )

    result = engine.score_pair(
        first,
        second,
    )

    assert result["correlated"] is False


def test_far_apart_signals_lose_temporal_evidence():
    engine = IncidentCorrelationEngine(
        time_window_seconds=300,
    )

    first = make_signal(
        SignalType.DEPLOYMENT,
        source="kubernetes",
        occurred_at=(
            "2026-08-27T10:00:00+00:00"
        ),
    )

    second = make_signal(
        SignalType.ALERT,
        source="monitoring",
        occurred_at=(
            "2026-08-27T11:00:00+00:00"
        ),
    )

    result = engine.score_pair(
        first,
        second,
    )

    assert (
        result["time_distance_seconds"]
        == 3600.0
    )

    assert (
        "Signals occurred within correlation window"
        not in result["evidence"]
    )


def test_same_incident_strengthens_correlation():
    engine = IncidentCorrelationEngine()

    first = make_signal(
        SignalType.HEALTH,
        source="health-monitor",
        incident_id="inc-123",
    )

    second = make_signal(
        SignalType.ALERT,
        source="monitoring",
        incident_id="inc-123",
    )

    result = engine.score_pair(
        first,
        second,
    )

    assert result["correlated"] is True

    assert (
        "Signals reference the same incident"
        in result["evidence"]
    )


def test_same_signal_is_fully_correlated():
    engine = IncidentCorrelationEngine()

    signal = make_signal(
        SignalType.ALERT,
        source="monitoring",
    )

    result = engine.score_pair(
        signal,
        signal,
    )

    assert result["score"] == 1.0
    assert result["correlated"] is True


def test_correlation_returns_related_signals():
    engine = IncidentCorrelationEngine()

    deployment = make_signal(
        SignalType.DEPLOYMENT,
        source="kubernetes",
        occurred_at=(
            "2026-08-27T10:00:00+00:00"
        ),
    )

    health = make_signal(
        SignalType.HEALTH,
        source="health-monitor",
        severity=SignalSeverity.HIGH,
        occurred_at=(
            "2026-08-27T10:03:00+00:00"
        ),
    )

    alert = make_signal(
        SignalType.ALERT,
        source="monitoring",
        severity=SignalSeverity.CRITICAL,
        occurred_at=(
            "2026-08-27T10:04:00+00:00"
        ),
    )

    result = engine.correlate(
        [
            deployment,
            health,
            alert,
        ],
        anchor=alert,
    )

    assert (
        result["anchor_signal_id"]
        == alert.signal_id
    )

    assert (
        result["correlation_count"]
        == 2
    )


def test_newest_signal_becomes_default_anchor():
    engine = IncidentCorrelationEngine()

    deployment = make_signal(
        SignalType.DEPLOYMENT,
        source="kubernetes",
        occurred_at=(
            "2026-08-27T10:00:00+00:00"
        ),
    )

    alert = make_signal(
        SignalType.ALERT,
        source="monitoring",
        occurred_at=(
            "2026-08-27T10:05:00+00:00"
        ),
    )

    result = engine.correlate(
        [
            deployment,
            alert,
        ]
    )

    assert (
        result["anchor_signal_id"]
        == alert.signal_id
    )


def test_empty_signal_collection_is_safe():
    engine = IncidentCorrelationEngine()

    result = engine.correlate([])

    assert (
        result["anchor_signal_id"]
        is None
    )

    assert (
        result["correlation_count"]
        == 0
    )

    assert (
        result["correlated_signals"]
        == []
    )


def test_invalid_time_window_is_rejected():
    with pytest.raises(
        ValueError,
        match="time_window_seconds",
    ):
        IncidentCorrelationEngine(
            time_window_seconds=0
        )


def test_invalid_threshold_is_rejected():
    with pytest.raises(
        ValueError,
        match="correlation_threshold",
    ):
        IncidentCorrelationEngine(
            correlation_threshold=1.5
        )


def test_correlation_results_are_ranked():
    engine = IncidentCorrelationEngine()

    alert = make_signal(
        SignalType.ALERT,
        source="monitoring",
        severity=SignalSeverity.CRITICAL,
        occurred_at=(
            "2026-08-27T10:05:00+00:00"
        ),
    )

    deployment = make_signal(
        SignalType.DEPLOYMENT,
        source="kubernetes",
        severity=SignalSeverity.HIGH,
        occurred_at=(
            "2026-08-27T10:02:00+00:00"
        ),
    )

    health = make_signal(
        SignalType.HEALTH,
        source="health-monitor",
        severity=SignalSeverity.MEDIUM,
        occurred_at=(
            "2026-08-27T10:04:00+00:00"
        ),
    )

    result = engine.correlate(
        [
            deployment,
            health,
            alert,
        ],
        anchor=alert,
    )

    scores = [
        item["score"]
        for item
        in result["correlated_signals"]
    ]

    assert scores == sorted(
        scores,
        reverse=True,
    )