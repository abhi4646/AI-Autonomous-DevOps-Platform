from src.correlation.causal_chain import (
    CausalChainBuilder,
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
    message="",
    severity=SignalSeverity.INFO,
    occurred_at,
):
    return OperationalSignal(
        signal_type=signal_type,
        source=source,
        resource=resource,
        message=message,
        severity=severity,
        environment="production",
        correlation_key="payments-api",
        occurred_at=occurred_at,
    )


def build_scenario():
    code_change = make_signal(
        SignalType.CODE_CHANGE,
        source="github",
        message="Release commit merged",
        occurred_at=(
            "2026-08-27T10:00:00+00:00"
        ),
    )

    build = make_signal(
        SignalType.BUILD,
        source="docker",
        message="Container image built",
        occurred_at=(
            "2026-08-27T10:03:00+00:00"
        ),
    )

    deployment = make_signal(
        SignalType.DEPLOYMENT,
        source="kubernetes",
        message="Version v2 deployed",
        severity=SignalSeverity.HIGH,
        occurred_at=(
            "2026-08-27T10:05:00+00:00"
        ),
    )

    metric = make_signal(
        SignalType.METRIC,
        source="monitoring",
        message="Error rate increased",
        severity=SignalSeverity.HIGH,
        occurred_at=(
            "2026-08-27T10:08:00+00:00"
        ),
    )

    failure = make_signal(
        SignalType.ALERT,
        source="monitoring",
        message="Critical service alert",
        severity=SignalSeverity.CRITICAL,
        occurred_at=(
            "2026-08-27T10:10:00+00:00"
        ),
    )

    return (
        code_change,
        build,
        deployment,
        metric,
        failure,
    )


def test_chain_ends_with_failure():
    builder = CausalChainBuilder()

    (
        code_change,
        build,
        deployment,
        metric,
        failure,
    ) = build_scenario()

    result = builder.build(
        failure,
        [
            code_change,
            build,
            deployment,
            metric,
            failure,
        ],
    )

    assert (
        result["chain"][-1][
            "signal_id"
        ]
        == failure.signal_id
    )


def test_chain_is_chronologically_ordered():
    builder = CausalChainBuilder()

    (
        code_change,
        build,
        deployment,
        metric,
        failure,
    ) = build_scenario()

    result = builder.build(
        failure,
        [
            metric,
            deployment,
            code_change,
            build,
            failure,
        ],
    )

    timestamps = [
        item["occurred_at"]
        for item in result["chain"]
    ]

    assert timestamps == sorted(
        timestamps
    )


def test_deployment_is_probable_root_cause():
    builder = CausalChainBuilder()

    (
        code_change,
        build,
        deployment,
        metric,
        failure,
    ) = build_scenario()

    result = builder.build(
        failure,
        [
            code_change,
            build,
            deployment,
            metric,
        ],
    )

    assert (
        result[
            "probable_root_cause"
        ]["signal_id"]
        == deployment.signal_id
    )


def test_confidence_matches_root_cause_score():
    builder = CausalChainBuilder()

    (
        code_change,
        build,
        deployment,
        metric,
        failure,
    ) = build_scenario()

    result = builder.build(
        failure,
        [
            code_change,
            build,
            deployment,
            metric,
        ],
    )

    assert (
        result["confidence"]
        == result[
            "probable_root_cause"
        ]["score"]
    )


def test_explanation_contains_root_cause_type():
    builder = CausalChainBuilder()

    (
        code_change,
        build,
        deployment,
        metric,
        failure,
    ) = build_scenario()

    result = builder.build(
        failure,
        [
            code_change,
            build,
            deployment,
            metric,
        ],
    )

    assert (
        "deployment"
        in result[
            "explanation"
        ]
    )


def test_chain_contains_timing_information():
    builder = CausalChainBuilder()

    (
        code_change,
        build,
        deployment,
        metric,
        failure,
    ) = build_scenario()

    result = builder.build(
        failure,
        [
            code_change,
            build,
            deployment,
            metric,
        ],
    )

    chain = result["chain"]

    assert (
        chain[0][
            "seconds_from_previous"
        ]
        is None
    )

    assert (
        chain[-1][
            "seconds_from_previous"
        ]
        == 120.0
    )


def test_future_signal_is_excluded():
    builder = CausalChainBuilder()

    (
        code_change,
        build,
        deployment,
        metric,
        failure,
    ) = build_scenario()

    future = make_signal(
        SignalType.ROLLBACK,
        source="kubernetes",
        occurred_at=(
            "2026-08-27T10:15:00+00:00"
        ),
    )

    result = builder.build(
        failure,
        [
            code_change,
            deployment,
            future,
        ],
    )

    ids = [
        item["signal_id"]
        for item in result["chain"]
    ]

    assert (
        future.signal_id
        not in ids
    )


def test_failure_only_chain_is_safe():
    builder = CausalChainBuilder()

    failure = make_signal(
        SignalType.ALERT,
        source="monitoring",
        severity=SignalSeverity.CRITICAL,
        occurred_at=(
            "2026-08-27T10:10:00+00:00"
        ),
    )

    result = builder.build(
        failure,
        []
    )

    assert (
        result["probable_root_cause"]
        is None
    )

    assert (
        result["confidence"]
        == 0.0
    )

    assert (
        result["chain_length"]
        == 1
    )

    assert (
        result["chain"][0][
            "signal_id"
        ]
        == failure.signal_id
    )


def test_no_candidate_has_safe_explanation():
    builder = CausalChainBuilder()

    failure = make_signal(
        SignalType.ALERT,
        source="monitoring",
        occurred_at=(
            "2026-08-27T10:10:00+00:00"
        ),
    )

    result = builder.build(
        failure,
        []
    )

    assert (
        "No sufficiently supported"
        in result["explanation"]
    )


def test_chain_reports_length():
    builder = CausalChainBuilder()

    (
        code_change,
        build,
        deployment,
        metric,
        failure,
    ) = build_scenario()

    result = builder.build(
        failure,
        [
            code_change,
            build,
            deployment,
            metric,
        ],
    )

    assert (
        result["chain_length"]
        == len(result["chain"])
    )

    assert (
        result["chain_length"]
        == 5
    )