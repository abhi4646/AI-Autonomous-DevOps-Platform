from datetime import datetime
from typing import Any, Dict, List, Optional

from src.correlation.signal import (
    OperationalSignal,
    SignalSeverity,
    SignalType,
)


class IncidentCorrelationEngine:
    """
    Correlates operational signals that may belong to the
    same incident.

    Correlation is based on deterministic evidence:

    - matching correlation key,
    - matching resource,
    - matching environment,
    - temporal proximity,
    - operational relationship between signal types.

    The engine does not mutate incidents or persist data.
    It produces an explainable correlation result for later
    incident and root-cause workflows.
    """

    RELATED_SIGNAL_TYPES = {
        SignalType.CODE_CHANGE: {
            SignalType.BUILD,
            SignalType.DEPLOYMENT,
            SignalType.CONFIGURATION,
        },
        SignalType.BUILD: {
            SignalType.CODE_CHANGE,
            SignalType.DEPLOYMENT,
        },
        SignalType.DEPLOYMENT: {
            SignalType.CODE_CHANGE,
            SignalType.BUILD,
            SignalType.HEALTH,
            SignalType.METRIC,
            SignalType.ALERT,
            SignalType.LOG,
            SignalType.REMEDIATION,
            SignalType.ROLLBACK,
        },
        SignalType.CONFIGURATION: {
            SignalType.CODE_CHANGE,
            SignalType.INFRASTRUCTURE,
            SignalType.HEALTH,
            SignalType.ALERT,
        },
        SignalType.INFRASTRUCTURE: {
            SignalType.CONFIGURATION,
            SignalType.HEALTH,
            SignalType.METRIC,
            SignalType.ALERT,
        },
        SignalType.HEALTH: {
            SignalType.DEPLOYMENT,
            SignalType.CONFIGURATION,
            SignalType.INFRASTRUCTURE,
            SignalType.METRIC,
            SignalType.ALERT,
            SignalType.LOG,
            SignalType.INCIDENT,
            SignalType.REMEDIATION,
            SignalType.ROLLBACK,
        },
        SignalType.METRIC: {
            SignalType.DEPLOYMENT,
            SignalType.INFRASTRUCTURE,
            SignalType.HEALTH,
            SignalType.ALERT,
            SignalType.LOG,
        },
        SignalType.ALERT: {
            SignalType.DEPLOYMENT,
            SignalType.CONFIGURATION,
            SignalType.INFRASTRUCTURE,
            SignalType.HEALTH,
            SignalType.METRIC,
            SignalType.LOG,
            SignalType.INCIDENT,
            SignalType.REMEDIATION,
            SignalType.ROLLBACK,
        },
        SignalType.LOG: {
            SignalType.DEPLOYMENT,
            SignalType.HEALTH,
            SignalType.METRIC,
            SignalType.ALERT,
        },
        SignalType.INCIDENT: {
            SignalType.HEALTH,
            SignalType.ALERT,
            SignalType.REMEDIATION,
            SignalType.ROLLBACK,
        },
        SignalType.REMEDIATION: {
            SignalType.DEPLOYMENT,
            SignalType.HEALTH,
            SignalType.ALERT,
            SignalType.INCIDENT,
            SignalType.ROLLBACK,
        },
        SignalType.ROLLBACK: {
            SignalType.DEPLOYMENT,
            SignalType.HEALTH,
            SignalType.ALERT,
            SignalType.INCIDENT,
            SignalType.REMEDIATION,
        },
    }

    SEVERITY_WEIGHT = {
        SignalSeverity.INFO: 0.0,
        SignalSeverity.LOW: 0.05,
        SignalSeverity.MEDIUM: 0.10,
        SignalSeverity.HIGH: 0.15,
        SignalSeverity.CRITICAL: 0.20,
    }

    def __init__(
        self,
        *,
        time_window_seconds: int = 900,
        correlation_threshold: float = 0.60,
    ) -> None:
        if time_window_seconds <= 0:
            raise ValueError(
                "time_window_seconds must be positive"
            )

        if not 0.0 <= correlation_threshold <= 1.0:
            raise ValueError(
                "correlation_threshold must be between 0 and 1"
            )

        self.time_window_seconds = time_window_seconds
        self.correlation_threshold = correlation_threshold

    @staticmethod
    def _parse_timestamp(
        value: str,
    ) -> datetime:
        """
        Parse an ISO-8601 signal timestamp.
        """

        return datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        )

    def _time_distance_seconds(
        self,
        first: OperationalSignal,
        second: OperationalSignal,
    ) -> float:
        first_time = self._parse_timestamp(
            first.occurred_at
        )

        second_time = self._parse_timestamp(
            second.occurred_at
        )

        return abs(
            (
                second_time
                - first_time
            ).total_seconds()
        )

    def _types_related(
        self,
        first: SignalType,
        second: SignalType,
    ) -> bool:
        if first == second:
            return True

        related = self.RELATED_SIGNAL_TYPES.get(
            first,
            set(),
        )

        return second in related

    def score_pair(
        self,
        first: OperationalSignal,
        second: OperationalSignal,
    ) -> Dict[str, Any]:
        """
        Score the likelihood that two signals belong to the
        same operational incident.

        The result is intentionally explainable.
        """

        score = 0.0
        evidence: List[str] = []

        same_signal = (
            first.signal_id
            == second.signal_id
        )

        if same_signal:
            return {
                "score": 1.0,
                "correlated": True,
                "evidence": [
                    "Signals have the same identity"
                ],
                "time_distance_seconds": 0.0,
            }

        # -----------------------------------------------------
        # CORRELATION KEY
        # -----------------------------------------------------

        if (
            first.correlation_key
            and second.correlation_key
            and first.correlation_key
            == second.correlation_key
        ):
            score += 0.35
            evidence.append(
                "Correlation keys match"
            )

        # -----------------------------------------------------
        # RESOURCE
        # -----------------------------------------------------

        if (
            first.resource
            == second.resource
        ):
            score += 0.25
            evidence.append(
                "Resources match"
            )

        # -----------------------------------------------------
        # ENVIRONMENT
        # -----------------------------------------------------

        if (
            first.environment
            and second.environment
            and first.environment
            == second.environment
        ):
            score += 0.10
            evidence.append(
                "Environments match"
            )

        # -----------------------------------------------------
        # TEMPORAL PROXIMITY
        # -----------------------------------------------------

        time_distance = (
            self._time_distance_seconds(
                first,
                second,
            )
        )

        if (
            time_distance
            <= self.time_window_seconds
        ):
            score += 0.15
            evidence.append(
                "Signals occurred within correlation window"
            )

        # -----------------------------------------------------
        # OPERATIONAL RELATIONSHIP
        # -----------------------------------------------------

        if self._types_related(
            first.signal_type,
            second.signal_type,
        ):
            score += 0.10
            evidence.append(
                "Signal types are operationally related"
            )

        # -----------------------------------------------------
        # INCIDENT LINK
        # -----------------------------------------------------

        if (
            first.incident_id
            and second.incident_id
            and first.incident_id
            == second.incident_id
        ):
            score += 0.30
            evidence.append(
                "Signals reference the same incident"
            )

        # -----------------------------------------------------
        # SEVERITY SUPPORT
        # -----------------------------------------------------

        severity_bonus = max(
            self.SEVERITY_WEIGHT.get(
                first.severity,
                0.0,
            ),
            self.SEVERITY_WEIGHT.get(
                second.severity,
                0.0,
            ),
        )

        if severity_bonus:
            score += severity_bonus
            evidence.append(
                "Signal severity strengthens correlation"
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
            "correlated": (
                score
                >= self.correlation_threshold
            ),
            "evidence": evidence,
            "time_distance_seconds": (
                time_distance
            ),
        }

    def correlate(
        self,
        signals: List[OperationalSignal],
        *,
        anchor: Optional[
            OperationalSignal
        ] = None,
    ) -> Dict[str, Any]:
        """
        Correlate a collection of signals around an anchor.

        When no explicit anchor is supplied, the newest signal
        becomes the anchor. This is useful when a newly observed
        alert or health failure arrives and the platform needs
        to search backward for related operational evidence.
        """

        if not signals:
            return {
                "anchor_signal_id": None,
                "correlated_signals": [],
                "uncorrelated_signals": [],
                "correlation_count": 0,
            }

        if anchor is None:
            anchor = max(
                signals,
                key=lambda signal: (
                    self._parse_timestamp(
                        signal.occurred_at
                    )
                ),
            )

        correlated_signals = []
        uncorrelated_signals = []

        for signal in signals:
            if (
                signal.signal_id
                == anchor.signal_id
            ):
                continue

            result = self.score_pair(
                anchor,
                signal,
            )

            entry = {
                "signal_id": signal.signal_id,
                "signal_type": (
                    signal.signal_type.value
                ),
                "source": signal.source,
                "resource": signal.resource,
                "score": result["score"],
                "evidence": result["evidence"],
                "time_distance_seconds": (
                    result[
                        "time_distance_seconds"
                    ]
                ),
            }

            if result["correlated"]:
                correlated_signals.append(
                    entry
                )
            else:
                uncorrelated_signals.append(
                    entry
                )

        correlated_signals.sort(
            key=lambda item: item["score"],
            reverse=True,
        )

        uncorrelated_signals.sort(
            key=lambda item: item["score"],
            reverse=True,
        )

        return {
            "anchor_signal_id": (
                anchor.signal_id
            ),
            "anchor_signal_type": (
                anchor.signal_type.value
            ),
            "anchor_resource": (
                anchor.resource
            ),
            "correlated_signals": (
                correlated_signals
            ),
            "uncorrelated_signals": (
                uncorrelated_signals
            ),
            "correlation_count": len(
                correlated_signals
            ),
        }