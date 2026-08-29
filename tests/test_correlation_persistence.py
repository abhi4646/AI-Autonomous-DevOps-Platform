from pathlib import Path

import pytest

from src.incident.manager import (
    IncidentManager,
)
from src.incident.model import (
    IncidentSeverity,
)
from src.persistence.database import (
    Database,
)


def make_signal(
    signal_id="signal-1",
    *,
    correlation_key="payments-api",
    occurred_at=(
        "2026-08-27T10:05:00+00:00"
    ),
):
    return {
        "signal_id": signal_id,
        "signal_type": "deployment",
        "source": "kubernetes",
        "resource": "payments-api",
        "severity": "high",
        "message": (
            "Deployment completed"
        ),
        "agent": "kubernetes",
        "environment": "production",
        "incident_id": None,
        "correlation_key": correlation_key,
        "metadata": {
            "version": "v2",
        },
        "occurred_at": occurred_at,
        "created_at": (
            "2026-08-27T10:05:01+00:00"
        ),
    }


def create_incident(
    database,
):
    manager = IncidentManager(
        database
    )

    return manager.create(
        title=(
            "Payments API failure"
        ),
        agent="kubernetes",
        severity=(
            IncidentSeverity.CRITICAL
        ),
        health_snapshot={
            "status": "unhealthy",
            "score": 25,
        },
    )


def make_rca_result():
    return {
        "failure_signal_id": (
            "failure-signal"
        ),
        "probable_root_cause": {
            "signal_id": (
                "deployment-signal"
            ),
            "signal_type": (
                "deployment"
            ),
            "score": 0.91,
        },
        "confidence": 0.91,
        "explanation": (
            "Deployment likely "
            "caused the failure"
        ),
        "chain": [
            {
                "signal_id": (
                    "deployment-signal"
                ),
                "signal_type": (
                    "deployment"
                ),
            },
            {
                "signal_id": (
                    "failure-signal"
                ),
                "signal_type": (
                    "alert"
                ),
            },
        ],
    }


def test_signal_round_trip():
    database = Database(
        ":memory:"
    )

    try:
        signal = make_signal()

        database.save_operational_signal(
            signal
        )

        stored = (
            database
            .get_operational_signal(
                signal["signal_id"]
            )
        )

        assert stored is not None
        assert (
            stored["signal_id"]
            == "signal-1"
        )
        assert (
            stored["signal_type"]
            == "deployment"
        )
        assert (
            stored["agent"]
            == "kubernetes"
        )
    finally:
        database.close()


def test_signal_metadata_round_trip():
    database = Database(
        ":memory:"
    )

    try:
        database.save_operational_signal(
            make_signal()
        )

        stored = (
            database
            .get_operational_signal(
                "signal-1"
            )
        )

        assert (
            stored["metadata"]
            == {
                "version": "v2",
            }
        )
    finally:
        database.close()


def test_unknown_signal_returns_none():
    database = Database(
        ":memory:"
    )

    try:
        assert (
            database
            .get_operational_signal(
                "missing"
            )
            is None
        )
    finally:
        database.close()


def test_signal_can_be_linked_to_incident():
    database = Database(
        ":memory:"
    )

    try:
        incident = create_incident(
            database
        )

        database.save_operational_signal(
            make_signal()
        )

        database.link_signal_to_incident(
            "signal-1",
            incident.incident_id,
        )

        stored = (
            database
            .get_operational_signal(
                "signal-1"
            )
        )

        assert (
            stored["incident_id"]
            == incident.incident_id
        )
    finally:
        database.close()


def test_signal_can_be_saved_with_incident():
    database = Database(
        ":memory:"
    )

    try:
        incident = create_incident(
            database
        )

        database.save_operational_signal(
            make_signal(),
            incident_id=(
                incident.incident_id
            ),
        )

        stored = (
            database
            .get_operational_signal(
                "signal-1"
            )
        )

        assert (
            stored["incident_id"]
            == incident.incident_id
        )
    finally:
        database.close()


def test_unknown_signal_link_raises():
    database = Database(
        ":memory:"
    )

    try:
        incident = create_incident(
            database
        )

        with pytest.raises(
            KeyError
        ):
            database.link_signal_to_incident(
                "missing-signal",
                incident.incident_id,
            )
    finally:
        database.close()


def test_get_incident_signals():
    database = Database(
        ":memory:"
    )

    try:
        incident = create_incident(
            database
        )

        database.save_operational_signal(
            make_signal(
                "signal-1"
            ),
            incident_id=(
                incident.incident_id
            ),
        )

        database.save_operational_signal(
            make_signal(
                "signal-2"
            ),
            incident_id=(
                incident.incident_id
            ),
        )

        database.save_operational_signal(
            make_signal(
                "signal-3"
            )
        )

        stored = (
            database
            .get_incident_signals(
                incident.incident_id
            )
        )

        assert len(stored) == 2

        assert {
            item["signal_id"]
            for item in stored
        } == {
            "signal-1",
            "signal-2",
        }
    finally:
        database.close()


def test_signal_filter_by_correlation_key():
    database = Database(
        ":memory:"
    )

    try:
        database.save_operational_signal(
            make_signal(
                "signal-1",
                correlation_key=(
                    "payments-api"
                ),
            )
        )

        database.save_operational_signal(
            make_signal(
                "signal-2",
                correlation_key=(
                    "orders-api"
                ),
            )
        )

        stored = (
            database
            .get_operational_signals(
                correlation_key=(
                    "payments-api"
                )
            )
        )

        assert len(stored) == 1

        assert (
            stored[0]["signal_id"]
            == "signal-1"
        )
    finally:
        database.close()


def test_signals_are_chronological():
    database = Database(
        ":memory:"
    )

    try:
        database.save_operational_signal(
            make_signal(
                "later",
                occurred_at=(
                    "2026-08-27T10:10:00+00:00"
                ),
            )
        )

        database.save_operational_signal(
            make_signal(
                "earlier",
                occurred_at=(
                    "2026-08-27T10:00:00+00:00"
                ),
            )
        )

        stored = (
            database
            .get_operational_signals()
        )

        assert [
            item["signal_id"]
            for item in stored
        ] == [
            "earlier",
            "later",
        ]
    finally:
        database.close()


def test_rca_result_round_trip():
    database = Database(
        ":memory:"
    )

    try:
        incident = create_incident(
            database
        )

        database.save_operational_signal(
            {
                **make_signal(
                    "failure-signal"
                ),
                "signal_type": "alert",
            },
            incident_id=(
                incident.incident_id
            ),
        )

        rca_id = (
            database.save_rca_result(
                incident.incident_id,
                make_rca_result(),
            )
        )

        assert isinstance(
            rca_id,
            int,
        )

        results = (
            database.get_rca_results(
                incident.incident_id
            )
        )

        assert len(results) == 1

        assert (
            results[0]["confidence"]
            == 0.91
        )

        assert (
            results[0][
                "probable_root_cause"
            ]["signal_id"]
            == "deployment-signal"
        )

        assert (
            len(
                results[0]["chain"]
            )
            == 2
        )
    finally:
        database.close()


def test_latest_rca_result():
    database = Database(
        ":memory:"
    )

    try:
        incident = create_incident(
            database
        )

        database.save_operational_signal(
            {
                **make_signal(
                    "failure-signal"
                ),
                "signal_type": "alert",
            },
            incident_id=(
                incident.incident_id
            ),
        )

        first = make_rca_result()

        second = {
            **make_rca_result(),
            "confidence": 0.97,
            "explanation": (
                "Updated analysis"
            ),
        }

        database.save_rca_result(
            incident.incident_id,
            first,
        )

        database.save_rca_result(
            incident.incident_id,
            second,
        )

        latest = (
            database
            .get_latest_rca_result(
                incident.incident_id
            )
        )

        assert latest is not None

        assert (
            latest["confidence"]
            == 0.97
        )

        assert (
            latest["explanation"]
            == "Updated analysis"
        )
    finally:
        database.close()


def test_unknown_incident_has_no_rca():
    database = Database(
        ":memory:"
    )

    try:
        assert (
            database
            .get_latest_rca_result(
                "missing"
            )
            is None
        )

        assert (
            database
            .get_rca_results(
                "missing"
            )
            == []
        )
    finally:
        database.close()


def test_signal_and_rca_survive_restart(
    tmp_path,
):
    db_path = (
        Path(tmp_path)
        / "correlation.db"
    )

    database = Database(
        str(db_path)
    )

    incident = create_incident(
        database
    )

    database.save_operational_signal(
        {
            **make_signal(
                "failure-signal"
            ),
            "signal_type": "alert",
        },
        incident_id=(
            incident.incident_id
        ),
    )

    database.save_rca_result(
        incident.incident_id,
        make_rca_result(),
    )

    incident_id = (
        incident.incident_id
    )

    database.close()

    reopened = Database(
        str(db_path)
    )

    try:
        signals = (
            reopened
            .get_incident_signals(
                incident_id
            )
        )

        latest = (
            reopened
            .get_latest_rca_result(
                incident_id
            )
        )

        assert len(signals) == 1

        assert (
            signals[0]["signal_id"]
            == "failure-signal"
        )

        assert latest is not None

        assert (
            latest["confidence"]
            == 0.91
        )
    finally:
        reopened.close()
