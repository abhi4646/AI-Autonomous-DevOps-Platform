from datetime import datetime
from typing import Any, Dict, List, Optional

from src.correlation.signal import (
    OperationalSignal,
    SignalSeverity,
    SignalType,
)


class RootCauseAnalyzer:
    """
    Ranks correlated operational signals as possible root
    causes of an incident or failure signal.

    The analyzer is deterministic and explainable.

    It does not modify incidents, execute remediation, or
    perform rollback. It only produces root-cause candidates
    and supporting evidence.
    """

    CAUSAL_TYPE_WEIGHT = {
        SignalType.CODE_CHANGE: 0.25,
        SignalType.BUILD: 0.15,
        SignalType.DEPLOYMENT: 0.35,
        SignalType.CONFIGURATION: 0.35,
        SignalType.INFRASTRUCTURE: 0.35,
        SignalType.REMEDIATION: 0.20,
        SignalType.ROLLBACK: 0.15,
        SignalType.HEALTH: 0.05,
        SignalType.METRIC: 0.05,
        SignalType.ALERT: 0.0,
        SignalType.LOG: 0.05,
        SignalType.INCIDENT: 0.0,
        SignalType.UNKNOWN: 0.0,
    }

    SEVERITY_WEIGHT = {
        SignalSeverity.INFO: 0.0,
        SignalSeverity.LOW: 0.02,
        SignalSeverity.MEDIUM: 0.04,
        SignalSeverity.HIGH: 0.06,
        SignalSeverity.CRITICAL: 0.08,
    }

    def __init__(
        self,
        *,
        causal_window_seconds: int = 1800,
        minimum_candidate_score: float = 0.20,
    ) -> None:
        if causal_window_seconds <= 0:
            raise ValueError(
                "causal_window_seconds must be positive"
            )

        if not 0.0 <= minimum_candidate_score <= 1.0:
            raise ValueError(
                "minimum_candidate_score must be between 0 and 1"
            )

        self.causal_window_seconds = (
            causal_window_seconds
        )

        self.minimum_candidate_score = (
            minimum_candidate_score
        )

    @staticmethod
    def _parse_timestamp(
        value: str,
    ) -> datetime:
        return datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        )

    def _seconds_before(
        self,
        candidate: OperationalSignal,
        failure: OperationalSignal,
    ) -> float:
        candidate_time = self._parse_timestamp(
            candidate.occurred_at
        )

        failure_time = self._parse_timestamp(
            failure.occurred_at
        )

        return (
            failure_time
            - candidate_time
        ).total_seconds()

    @staticmethod
    def _same_resource(
        candidate: OperationalSignal,
        failure: OperationalSignal,
    ) -> bool:
        return (
            candidate.resource
            == failure.resource
        )

    @staticmethod
    def _same_correlation_key(
        candidate: OperationalSignal,
        failure: OperationalSignal,
    ) -> bool:
        return bool(
            candidate.correlation_key
            and failure.correlation_key
            and candidate.correlation_key
            == failure.correlation_key
        )

    @staticmethod
    def _same_environment(
        candidate: OperationalSignal,
        failure: OperationalSignal,
    ) -> bool:
        return bool(
            candidate.environment
            and failure.environment
            and candidate.environment
            == failure.environment
        )

    def score_candidate(
        self,
        candidate: OperationalSignal,
        failure: OperationalSignal,
    ) -> Dict[str, Any]:
        """
        Score one signal as a possible cause of a later
        failure signal.
        """

        if (
            candidate.signal_id
            == failure.signal_id
        ):
            return {
                "score": 0.0,
                "is_candidate": False,
                "evidence": [
                    "Failure signal cannot cause itself"
                ],
                "seconds_before_failure": 0.0,
            }

        seconds_before = self._seconds_before(
            candidate,
            failure,
        )

        if seconds_before < 0:
            return {
                "score": 0.0,
                "is_candidate": False,
                "evidence": [
                    "Signal occurred after the failure"
                ],
                "seconds_before_failure": (
                    seconds_before
                ),
            }

        score = 0.0
        evidence: List[str] = []

        causal_weight = (
            self.CAUSAL_TYPE_WEIGHT.get(
                candidate.signal_type,
                0.0,
            )
        )

        if causal_weight:
            score += causal_weight
            evidence.append(
                (
                    f"{candidate.signal_type.value} "
                    "is a causal operation type"
                )
            )

        if self._same_correlation_key(
            candidate,
            failure,
        ):
            score += 0.25
            evidence.append(
                "Correlation key matches failure"
            )

        if self._same_resource(
            candidate,
            failure,
        ):
            score += 0.20
            evidence.append(
                "Affected resource matches failure"
            )

        if self._same_environment(
            candidate,
            failure,
        ):
            score += 0.10
            evidence.append(
                "Environment matches failure"
            )

        if (
            seconds_before
            <= self.causal_window_seconds
        ):
            proximity_ratio = (
                1.0
                - (
                    seconds_before
                    / self.causal_window_seconds
                )
            )

            proximity_bonus = (
                0.20
                * max(
                    0.0,
                    proximity_ratio,
                )
            )

            score += proximity_bonus

            evidence.append(
                "Signal occurred before failure within causal window"
            )

        severity_bonus = (
            self.SEVERITY_WEIGHT.get(
                candidate.severity,
                0.0,
            )
        )

        if severity_bonus:
            score += severity_bonus
            evidence.append(
                "Signal severity strengthens candidate"
            )

        if (
            candidate.incident_id
            and failure.incident_id
            and candidate.incident_id
            == failure.incident_id
        ):
            score += 0.10
            evidence.append(
                "Signal belongs to the same incident"
            )

        score = round(
            min(
                score,
                1.0,
            ),
            4,
        )

        return {
            "score": score,
            "is_candidate": (
                score
                >= self.minimum_candidate_score
            ),
            "evidence": evidence,
            "seconds_before_failure": (
                seconds_before
            ),
        }

    def analyze(
        self,
        failure: OperationalSignal,
        signals: List[OperationalSignal],
        *,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Rank possible root causes for a failure signal.
        """

        candidates = []

        for signal in signals:
            result = self.score_candidate(
                signal,
                failure,
            )

            if not result["is_candidate"]:
                continue

            candidates.append(
                {
                    "signal_id": (
                        signal.signal_id
                    ),
                    "signal_type": (
                        signal.signal_type.value
                    ),
                    "source": signal.source,
                    "resource": signal.resource,
                    "message": signal.message,
                    "score": result["score"],
                    "confidence": (
                        result["score"]
                    ),
                    "seconds_before_failure": (
                        result[
                            "seconds_before_failure"
                        ]
                    ),
                    "evidence": (
                        result["evidence"]
                    ),
                }
            )

        candidates.sort(
            key=lambda item: (
                item["score"],
                -item[
                    "seconds_before_failure"
                ],
            ),
            reverse=True,
        )

        if limit is not None:
            if limit < 0:
                raise ValueError(
                    "limit cannot be negative"
                )

            candidates = candidates[
                :limit
            ]

        probable_root_cause = (
            candidates[0]
            if candidates
            else None
        )

        return {
            "failure_signal_id": (
                failure.signal_id
            ),
            "failure_signal_type": (
                failure.signal_type.value
            ),
            "failure_resource": (
                failure.resource
            ),
            "probable_root_cause": (
                probable_root_cause
            ),
            "candidates": candidates,
            "candidate_count": len(
                candidates
            ),
        }