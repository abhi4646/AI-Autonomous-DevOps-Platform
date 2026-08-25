import sqlite3

from src.persistence.database import Database


def test_execution_table_has_telemetry_columns():
    db = Database(":memory:")

    cursor = db.connection.cursor()
    cursor.execute("PRAGMA table_info(executions)")

    columns = {
        row["name"]
        for row in cursor.fetchall()
    }

    expected = {
        "execution_id",
        "started_at",
        "finished_at",
        "duration_ms",
        "command",
        "error",
        "telemetry_metadata",
    }

    assert expected.issubset(columns)

    db.close()


def test_existing_execution_table_is_migrated(tmp_path):
    db_path = tmp_path / "legacy.db"

    connection = sqlite3.connect(db_path)

    connection.execute(
        """
        CREATE TABLE executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request TEXT NOT NULL,
            agent TEXT NOT NULL,
            status TEXT NOT NULL,
            result TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

    connection.execute(
        """
        INSERT INTO executions (
            request,
            agent,
            status,
            result,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "Legacy request",
            "legacy-agent",
            "success",
            '{"status": "success"}',
            "2026-08-24T00:00:00+00:00",
        ),
    )

    connection.commit()
    connection.close()

    db = Database(str(db_path))

    cursor = db.connection.cursor()
    cursor.execute("PRAGMA table_info(executions)")

    columns = {
        row["name"]
        for row in cursor.fetchall()
    }

    assert "execution_id" in columns
    assert "duration_ms" in columns
    assert "started_at" in columns
    assert "finished_at" in columns
    assert "command" in columns
    assert "error" in columns
    assert "telemetry_metadata" in columns

    executions = db.get_executions()

    assert len(executions) == 1
    assert executions[0]["request"] == "Legacy request"

    db.close()


def test_save_execution_persists_telemetry():
    db = Database(":memory:")

    telemetry = {
        "execution_id": "exec-123",
        "request": "Check production pods",
        "agent": "Kubernetes Agent",
        "status": "success",
        "started_at": "2026-08-25T00:00:00+00:00",
        "finished_at": "2026-08-25T00:00:01+00:00",
        "duration_ms": 1000.0,
        "command": [
            "kubectl",
            "get",
            "pods",
        ],
        "error": None,
        "metadata": {
            "environment": "production",
        },
    }

    db.save_execution(
        request="Check production pods",
        agent="Kubernetes Agent",
        status="success",
        result={
            "status": "success",
        },
        telemetry=telemetry,
    )

    executions = db.get_executions()

    assert len(executions) == 1

    execution = executions[0]

    assert execution["execution_id"] == "exec-123"
    assert (
        execution["started_at"]
        == "2026-08-25T00:00:00+00:00"
    )
    assert (
        execution["finished_at"]
        == "2026-08-25T00:00:01+00:00"
    )
    assert execution["duration_ms"] == 1000.0

    assert execution["command"] == [
        "kubectl",
        "get",
        "pods",
    ]

    assert execution["error"] is None

    assert execution["telemetry_metadata"] == {
        "environment": "production",
    }

    db.close()


def test_save_execution_without_telemetry_still_works():
    db = Database(":memory:")

    db.save_execution(
        request="Legacy compatible request",
        agent="legacy-agent",
        status="success",
        result={
            "status": "success",
        },
    )

    executions = db.get_executions()

    assert len(executions) == 1

    execution = executions[0]

    assert (
        execution["request"]
        == "Legacy compatible request"
    )

    assert execution["execution_id"] is None
    assert execution["duration_ms"] is None

    db.close()


def test_get_execution_by_execution_id():
    db = Database(":memory:")

    telemetry = {
        "execution_id": "exec-find-me",
        "request": "Inspect cluster",
        "agent": "Kubernetes Agent",
        "status": "success",
        "started_at": "2026-08-25T00:00:00+00:00",
        "finished_at": "2026-08-25T00:00:00+00:00",
        "duration_ms": 25.5,
        "command": [
            "kubectl",
            "get",
            "pods",
        ],
        "error": None,
        "metadata": {},
    }

    db.save_execution(
        request="Inspect cluster",
        agent="Kubernetes Agent",
        status="success",
        result={
            "status": "success",
        },
        telemetry=telemetry,
    )

    execution = db.get_execution(
        "exec-find-me"
    )

    assert execution is not None
    assert (
        execution["execution_id"]
        == "exec-find-me"
    )
    assert execution["request"] == "Inspect cluster"

    db.close()
