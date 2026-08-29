from datetime import datetime
from typing import Any, Dict, List, Optional

from src.correlation.root_cause import (
    RootCauseAnalyzer,
)
from src.correlation.signal import (
    OperationalSignal,
)


class CausalChainBuilder:
    """
    Builds an explainable causal timeline from operational
    signals leading to a failure.

    The builder does not claim absolute causation. It combines
    deterministic temporal ordering with RootCauseAnalyzer
    scoring to produce an evidence-backed RCA representation.
    """

    def __init__(
        self,
        analyzer: Optional[
            RootCauseAnalyzer
        ] = None,
    ) -> None:
        self.analyzer = (
            analyzer
            or RootCauseAnalyzer()
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

    def _seconds_between(
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

        return (
            second_time
            - first_time
        ).total_seconds()

    def build(
        self,
        failure: OperationalSignal,
        signals: List[OperationalSignal],
    ) -> Dict[str, Any]:
        """
        Build an ordered causal chain ending with the supplied
        failure signal.
        """

        failure_time = self._parse_timestamp(
            failure.occurred_at
        )

        prior_signals = [
            signal
            for signal in signals
            if (
                signal.signal_id
                != failure.signal_id
                and self._parse_timestamp(
                    signal.occurred_at
                )
                <= failure_time
            )
        ]

        prior_signals.sort(
            key=lambda signal: (
                self._parse_timestamp(
                    signal.occurred_at
                )
            )
        )

        analysis = self.analyzer.analyze(
            failure,
            prior_signals,
        )

        candidate_scores = {
            candidate["signal_id"]: candidate
            for candidate
            in analysis["candidates"]
        }

        chain = []

        previous_signal = None

        for signal in prior_signals:
            candidate = candidate_scores.get(
                signal.signal_id
            )

            if candidate is None:
                continue

            seconds_from_previous = None

            if previous_signal is not None:
                seconds_from_previous = (
                    self._seconds_between(
                        previous_signal,
                        signal,
                    )
                )

            chain.append(
                {
                    "signal_id": signal.signal_id,
                    "signal_type": (
                        signal.signal_type.value
                    ),
                    "source": signal.source,
                    "resource": signal.resource,
                    "message": signal.message,
                    "occurred_at": (
                        signal.occurred_at
                    ),
                    "seconds_from_previous": (
                        seconds_from_previous
                    ),
                    "root_cause_score": (
                        candidate["score"]
                    ),
                    "evidence": list(
                        candidate["evidence"]
                    ),
                }
            )

            previous_signal = signal

        seconds_from_previous = None

        if previous_signal is not None:
            seconds_from_previous = (
                self._seconds_between(
                    previous_signal,
                    failure,
                )
            )

        failure_entry = {
            "signal_id": failure.signal_id,
            "signal_type": (
                failure.signal_type.value
            ),
            "source": failure.source,
            "resource": failure.resource,
            "message": failure.message,
            "occurred_at": failure.occurred_at,
            "seconds_from_previous": (
                seconds_from_previous
            ),
            "root_cause_score": None,
            "evidence": [
                "Observed failure signal"
            ],
        }

        chain.append(
            failure_entry
        )

        probable_root_cause = analysis[
            "probable_root_cause"
        ]

        explanation = self._build_explanation(
            failure,
            probable_root_cause,
        )

        return {
            "failure_signal_id": (
                failure.signal_id
            ),
            "failure_resource": (
                failure.resource
            ),
            "probable_root_cause": (
                probable_root_cause
            ),
            "confidence": (
                probable_root_cause["score"]
                if probable_root_cause
                else 0.0
            ),
            "explanation": explanation,
            "chain": chain,
            "chain_length": len(chain),
        }

    @staticmethod
    def _build_explanation(
        failure: OperationalSignal,
        root_cause: Optional[
            Dict[str, Any]
        ],
    ) -> str:
        if root_cause is None:
            return (
                "No sufficiently supported root-cause "
                "candidate was identified."
            )

        signal_type = root_cause[
            "signal_type"
        ]

        resource = root_cause[
            "resource"
        ]

        seconds = root_cause[
            "seconds_before_failure"
        ]

        return (
            f"Probable root cause is {signal_type} "
            f"on '{resource}', observed "
            f"{seconds:.0f} seconds before the "
            f"{failure.signal_type.value} failure. "
            f"Confidence score: "
            f"{root_cause['score']:.2f}."
        )