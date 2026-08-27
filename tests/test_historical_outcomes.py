from src.intelligence.context import DecisionContext
from src.intelligence.outcomes import (
    HistoricalOutcomeAnalyzer,
)


def test_no_history_reports_insufficient_data():
    analyzer = HistoricalOutcomeAnalyzer()

    context = DecisionContext(
        request="Check Kubernetes"
    )

    result = analyzer.analyze(
        context
    )

    assert (
        result["execution_trend"]
        == "insufficient_data"
    )

    assert (
        result["remediation_trend"]
        == "insufficient_data"
    )


def test_strong_execution_history():
    analyzer = HistoricalOutcomeAnalyzer()

    context = DecisionContext(
        request="Check service",
        previous_executions=10,
        previous_successes=9,
        previous_failures=1,
    )

    result = analyzer.analyze(
        context
    )

    assert (
        result["execution_trend"]
        == "strong"
    )


def test_poor_execution_history():
    analyzer = HistoricalOutcomeAnalyzer()

    context = DecisionContext(
        request="Check service",
        previous_executions=10,
        previous_successes=3,
        previous_failures=7,
    )

    result = analyzer.analyze(
        context
    )

    assert (
        result["execution_trend"]
        == "poor"
    )

    assert (
        result[
            "repeated_execution_failure"
        ]
        is True
    )


def test_strong_remediation_history():
    analyzer = HistoricalOutcomeAnalyzer()

    context = DecisionContext(
        request="Remediate service",
        previous_remediations=5,
        successful_remediations=4,
        failed_remediations=1,
    )

    result = analyzer.analyze(
        context
    )

    assert (
        result["remediation_trend"]
        == "strong"
    )

    assert result["avoid_repeat"] is False


def test_repeated_remediation_failure_avoids_repeat():
    analyzer = HistoricalOutcomeAnalyzer()

    context = DecisionContext(
        request="Remediate service",
        previous_remediations=4,
        successful_remediations=1,
        failed_remediations=3,
    )

    result = analyzer.analyze(
        context
    )

    assert result["avoid_repeat"] is True

    assert (
        result[
            "repeated_remediation_failure"
        ]
        is True
    )


def test_failed_remediation_prefers_rollback():
    analyzer = HistoricalOutcomeAnalyzer()

    context = DecisionContext(
        request="Remediate service",
        previous_remediations=4,
        successful_remediations=1,
        failed_remediations=3,
        rollback_available=True,
    )

    result = analyzer.analyze(
        context
    )

    assert result["prefer_rollback"] is True
    assert result["require_escalation"] is False


def test_failed_remediation_escalates_without_rollback():
    analyzer = HistoricalOutcomeAnalyzer()

    context = DecisionContext(
        request="Remediate service",
        previous_remediations=4,
        successful_remediations=1,
        failed_remediations=3,
        rollback_available=False,
    )

    result = analyzer.analyze(
        context
    )

    assert result["prefer_rollback"] is False
    assert result["require_escalation"] is True