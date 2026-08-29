import pytest

from src.correlation.root_cause import (
    RootCauseAnalyzer,
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
    message="",
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
        message=message,
        occurred_at=occurred_at,
    )


def make_failure():
    return make_signal(
        SignalType.ALERT,
        source="monitoring",
        severity=SignalSeverity.CRITICAL,
        message="Service error rate increased",
        occurred_at=(
            "2026-08-27T10:10:00+00:00"
        ),
    )


def test_deployment_before_failure_is_candidate():
    analyzer = RootCauseAnalyzer()

    deployment = make_signal(
        SignalType.DEPLOYMENT,
        source="kubernetes",
        occurred_at=(
            "2026-08-27T10:05:00+00:00"
        ),
    )

    failure = make_failure()

    result = analyzer.score_candidate(
        deployment,
        failure,
    )

    assert result["is_candidate"] is True
    assert result["score"] >= 0.20

    assert (
        result["seconds_before_failure"]
        == 300.0
    )


def test_signal_after_failure_is_not_candidate():
    analyzer = RootCauseAnalyzer()

    failure = make_failure()

    later_deployment = make_signal(
        SignalType.DEPLOYMENT,
        source="kubernetes",
        occurred_at=(
            "2026-08-27T10:15:00+00:00"
        ),
    )

    result = analyzer.score_candidate(
        later_deployment,
        failure,
    )

    assert result["is_candidate"] is False
    assert result["score"] == 0.0

    assert (
        "Signal occurred after the failure"
        in result["evidence"]
    )


def test_failure_cannot_cause_itself():
    analyzer = RootCauseAnalyzer()

    failure = make_failure()

    result = analyzer.score_candidate(
        failure,
        failure,
    )

    assert result["is_candidate"] is False
    assert result["score"] == 0.0


def test_matching_resource_strengthens_candidate():
    analyzer = RootCauseAnalyzer()

    failure = make_failure()

    matching = make_signal(
        SignalType.DEPLOYMENT,
        source="kubernetes",
        resource="payments-api",
        occurred_at=(
            "2026-08-27T10:05:00+00:00"
        ),
    )

    different = make_signal(
        SignalType.DEPLOYMENT,
        source="kubernetes",
        resource="inventory-api",
        correlation_key="inventory-api",
        occurred_at=(
            "2026-08-27T10:05:00+00:00"
        ),
    )

    matching_result = (
        analyzer.score_candidate(
            matching,
            failure,
        )
    )

    different_result = (
        analyzer.score_candidate(
            different,
            failure,
        )
    )

    assert (
        matching_result["score"]
        > different_result["score"]
    )


def test_recent_signal_scores_higher():
    analyzer = RootCauseAnalyzer(
        causal_window_seconds=1800
    )

    failure = make_failure()

    recent = make_signal(
        SignalType.DEPLOYMENT,
        source="kubernetes",
        occurred_at=(
            "2026-08-27T10:09:00+00:00"
        ),
    )

    older = make_signal(
        SignalType.DEPLOYMENT,
        source="kubernetes",
        occurred_at=(
            "2026-08-27T09:45:00+00:00"
        ),
    )

    recent_result = (
        analyzer.score_candidate(
            recent,
            failure,
        )
    )

    older_result = (
        analyzer.score_candidate(
            older,
            failure,
        )
    )

    assert (
        recent_result["score"]
        > older_result["score"]
    )


def test_deployment_outranks_observational_metric():
    analyzer = RootCauseAnalyzer()

    failure = make_failure()

    deployment = make_signal(
        SignalType.DEPLOYMENT,
        source="kubernetes",
        occurred_at=(
            "2026-08-27T10:05:00+00:00"
        ),
    )

    metric = make_signal(
        SignalType.METRIC,
        source="monitoring",
        occurred_at=(
            "2026-08-27T10:05:00+00:00"
        ),
    )

    deployment_result = (
        analyzer.score_candidate(
            deployment,
            failure,
        )
    )

    metric_result = (
        analyzer.score_candidate(
            metric,
            failure,
        )
    )

    assert (
        deployment_result["score"]
        > metric_result["score"]
    )


def test_same_incident_strengthens_candidate():
    analyzer = RootCauseAnalyzer()

    failure = make_signal(
        SignalType.ALERT,
        source="monitoring",
        severity=SignalSeverity.CRITICAL,
        incident_id="inc-1",
        occurred_at=(
            "2026-08-27T10:10:00+00:00"
        ),
    )

    deployment = make_signal(
        SignalType.DEPLOYMENT,
        source="kubernetes",
        incident_id="inc-1",
        occurred_at=(
            "2026-08-27T10:05:00+00:00"
        ),
    )

    result = analyzer.score_candidate(
        deployment,
        failure,
    )

    assert (
        "Signal belongs to the same incident"
        in result["evidence"]
    )


def test_analyze_ranks_probable_root_cause():
    analyzer = RootCauseAnalyzer()

    failure = make_failure()

    code_change = make_signal(
        SignalType.CODE_CHANGE,
        source="github",
        message="Merged release commit",
        occurred_at=(
            "2026-08-27T09:55:00+00:00"
        ),
    )

    deployment = make_signal(
        SignalType.DEPLOYMENT,
        source="kubernetes",
        message="Deployed version v2",
        occurred_at=(
            "2026-08-27T10:07:00+00:00"
        ),
    )

    metric = make_signal(
        SignalType.METRIC,
        source="monitoring",
        message="Latency increased",
        occurred_at=(
            "2026-08-27T10:09:00+00:00"
        ),
    )

    result = analyzer.analyze(
        failure,
        [
            code_change,
            deployment,
            metric,
            failure,
        ],
    )

    assert (
        result["candidate_count"]
        == 3
    )

    assert (
        result[
            "probable_root_cause"
        ]["signal_id"]
        == deployment.signal_id
    )


def test_candidates_are_sorted_by_score():
    analyzer = RootCauseAnalyzer()

    failure = make_failure()

    code_change = make_signal(
        SignalType.CODE_CHANGE,
        source="github",
        occurred_at=(
            "2026-08-27T09:55:00+00:00"
        ),
    )

    deployment = make_signal(
        SignalType.DEPLOYMENT,
        source="kubernetes",
        occurred_at=(
            "2026-08-27T10:08:00+00:00"
        ),
    )

    result = analyzer.analyze(
        failure,
        [
            code_change,
            deployment,
        ],
    )

    scores = [
        candidate["score"]
        for candidate
        in result["candidates"]
    ]

    assert scores == sorted(
        scores,
        reverse=True,
    )


def test_candidate_limit_is_supported():
    analyzer = RootCauseAnalyzer()

    failure = make_failure()

    signals = [
        make_signal(
            SignalType.CODE_CHANGE,
            source="github",
            occurred_at=(
                "2026-08-27T09:55:00+00:00"
            ),
        ),
        make_signal(
            SignalType.BUILD,
            source="docker",
            occurred_at=(
                "2026-08-27T10:00:00+00:00"
            ),
        ),
        make_signal(
            SignalType.DEPLOYMENT,
            source="kubernetes",
            occurred_at=(
                "2026-08-27T10:05:00+00:00"
            ),
        ),
    ]

    result = analyzer.analyze(
        failure,
        signals,
        limit=2,
    )

    assert (
        result["candidate_count"]
        == 2
    )

    assert (
        len(result["candidates"])
        == 2
    )


def test_negative_limit_is_rejected():
    analyzer = RootCauseAnalyzer()

    failure = make_failure()

    with pytest.raises(
        ValueError,
        match="limit",
    ):
        analyzer.analyze(
            failure,
            [],
            limit=-1,
        )


def test_invalid_causal_window_is_rejected():
    with pytest.raises(
        ValueError,
        match="causal_window_seconds",
    ):
        RootCauseAnalyzer(
            causal_window_seconds=0
        )


def test_invalid_minimum_score_is_rejected():
    with pytest.raises(
        ValueError,
        match="minimum_candidate_score",
    ):
        RootCauseAnalyzer(
            minimum_candidate_score=1.5
        )