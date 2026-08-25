import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class Database:
    """
    SQLite persistence layer for the Autonomous DevOps Platform.

    Stores:
    - agent executions
    - execution telemetry
    - approval requests
    - audit events

    Existing databases are migrated automatically when new
    execution telemetry columns are introduced.
    """

    def __init__(
        self,
        db_path: str = "data/devops_platform.db",
    ):
        self.db_path = db_path

        if db_path != ":memory:":
            Path(db_path).parent.mkdir(
                parents=True,
                exist_ok=True,
            )

        self.connection = sqlite3.connect(
            db_path,
            check_same_thread=False,
        )

        self.connection.row_factory = sqlite3.Row

        # Order is important:
        # 1. Create tables
        # 2. Migrate legacy execution tables
        # 3. Create indexes that depend on migrated columns
        self._create_tables()
        self._migrate_execution_table()
        self._create_indexes()

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(
            timezone.utc
        ).isoformat()

    # ---------------------------------------------------------
    # DATABASE INITIALIZATION
    # ---------------------------------------------------------

    def _create_tables(self) -> None:
        """
        Create base database tables.

        Existing tables are left intact by SQLite. Any missing
        execution telemetry columns are added by the migration
        method after this method completes.
        """

        cursor = self.connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request TEXT NOT NULL,
                agent TEXT NOT NULL,
                status TEXT NOT NULL,
                result TEXT,
                created_at TEXT NOT NULL,
                execution_id TEXT,
                started_at TEXT,
                finished_at TEXT,
                duration_ms REAL,
                command TEXT,
                error TEXT,
                telemetry_metadata TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS approvals (
                approval_id TEXT PRIMARY KEY,
                request TEXT NOT NULL,
                agent TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                status TEXT NOT NULL,
                decided_by TEXT,
                created_at TEXT NOT NULL,
                decided_at TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                message TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL
            )
            """
        )

        self.connection.commit()

    def _migrate_execution_table(self) -> None:
        """
        Upgrade an existing legacy executions table without
        deleting or replacing existing execution records.
        """

        cursor = self.connection.cursor()

        cursor.execute(
            "PRAGMA table_info(executions)"
        )

        existing_columns = {
            row["name"]
            for row in cursor.fetchall()
        }

        required_columns = {
            "execution_id": "TEXT",
            "started_at": "TEXT",
            "finished_at": "TEXT",
            "duration_ms": "REAL",
            "command": "TEXT",
            "error": "TEXT",
            "telemetry_metadata": "TEXT",
        }

        for (
            column_name,
            column_type,
        ) in required_columns.items():
            if column_name not in existing_columns:
                cursor.execute(
                    f"""
                    ALTER TABLE executions
                    ADD COLUMN {column_name} {column_type}
                    """
                )

        self.connection.commit()

    def _create_indexes(self) -> None:
        """
        Create indexes after migrations have completed.

        execution_id may not exist in a legacy database until
        _migrate_execution_table() has run.
        """

        cursor = self.connection.cursor()

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_executions_execution_id
            ON executions(execution_id)
            """
        )

        self.connection.commit()

    # ---------------------------------------------------------
    # SERIALIZATION HELPERS
    # ---------------------------------------------------------

    @staticmethod
    def _serialize(
        value: Optional[Any],
    ) -> Optional[str]:
        if value is None:
            return None

        return json.dumps(value)

    @staticmethod
    def _deserialize(
        value: Optional[str],
    ) -> Optional[Any]:
        if value is None:
            return None

        return json.loads(value)

    def _deserialize_execution(
        self,
        row,
    ) -> dict:
        item = dict(row)

        if item.get("result") is not None:
            item["result"] = self._deserialize(
                item["result"]
            )

        if item.get("command") is not None:
            item["command"] = self._deserialize(
                item["command"]
            )

        if (
            item.get("telemetry_metadata")
            is not None
        ):
            item["telemetry_metadata"] = (
                self._deserialize(
                    item["telemetry_metadata"]
                )
            )

        return item

    # ---------------------------------------------------------
    # EXECUTIONS
    # ---------------------------------------------------------

    def save_execution(
        self,
        request: str,
        agent: str,
        status: str,
        result: Optional[Any] = None,
        telemetry: Optional[dict] = None,
    ) -> int:
        """
        Persist an agent execution.

        telemetry is optional so older callers that only provide
        request, agent, status, and result remain compatible.
        """

        cursor = self.connection.cursor()

        telemetry = telemetry or {}

        execution_id = telemetry.get(
            "execution_id"
        )

        started_at = telemetry.get(
            "started_at"
        )

        finished_at = telemetry.get(
            "finished_at"
        )

        duration_ms = telemetry.get(
            "duration_ms"
        )

        command = telemetry.get(
            "command"
        )

        error = telemetry.get(
            "error"
        )

        telemetry_metadata = telemetry.get(
            "metadata"
        )

        serialized_result = self._serialize(
            result
        )

        serialized_command = self._serialize(
            command
        )

        serialized_metadata = self._serialize(
            telemetry_metadata
        )

        cursor.execute(
            """
            INSERT INTO executions (
                request,
                agent,
                status,
                result,
                created_at,
                execution_id,
                started_at,
                finished_at,
                duration_ms,
                command,
                error,
                telemetry_metadata
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                request,
                agent,
                status,
                serialized_result,
                self._timestamp(),
                execution_id,
                started_at,
                finished_at,
                duration_ms,
                serialized_command,
                error,
                serialized_metadata,
            ),
        )

        self.connection.commit()

        return cursor.lastrowid

    def get_executions(self) -> list[dict]:
        """
        Return all stored executions.
        """

        cursor = self.connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM executions
            ORDER BY id ASC
            """
        )

        return [
            self._deserialize_execution(row)
            for row in cursor.fetchall()
        ]

    def get_execution(
        self,
        execution_id: str,
    ) -> Optional[dict]:
        """
        Retrieve an execution using its telemetry execution ID.
        """

        cursor = self.connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM executions
            WHERE execution_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (execution_id,),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return self._deserialize_execution(
            row
        )

    # ---------------------------------------------------------
    # APPROVALS
    # ---------------------------------------------------------

    def save_approval(
        self,
        approval_id: str,
        request: str,
        agent: str,
        risk_level: str,
        status: str = "pending",
    ) -> None:
        """
        Persist an approval request.
        """

        cursor = self.connection.cursor()

        cursor.execute(
            """
            INSERT INTO approvals (
                approval_id,
                request,
                agent,
                risk_level,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                approval_id,
                request,
                agent,
                risk_level,
                status,
                self._timestamp(),
            ),
        )

        self.connection.commit()

    def update_approval(
        self,
        approval_id: str,
        status: str,
        decided_by: str,
    ) -> None:
        """
        Update an existing approval decision.
        """

        cursor = self.connection.cursor()

        cursor.execute(
            """
            UPDATE approvals
            SET
                status = ?,
                decided_by = ?,
                decided_at = ?
            WHERE approval_id = ?
            """,
            (
                status,
                decided_by,
                self._timestamp(),
                approval_id,
            ),
        )

        if cursor.rowcount == 0:
            raise KeyError(
                f"Approval request "
                f"'{approval_id}' does not exist"
            )

        self.connection.commit()

    def get_approval(
        self,
        approval_id: str,
    ) -> Optional[dict]:
        """
        Retrieve one approval request.
        """

        cursor = self.connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM approvals
            WHERE approval_id = ?
            """,
            (approval_id,),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return dict(row)

    def get_pending_approvals(
        self,
    ) -> list[dict]:
        """
        Return pending approval requests.
        """

        cursor = self.connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM approvals
            WHERE status = 'pending'
            ORDER BY created_at ASC
            """
        )

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

    # ---------------------------------------------------------
    # AUDIT EVENTS
    # ---------------------------------------------------------

    def save_audit_event(
        self,
        event_type: str,
        message: str,
        metadata: Optional[dict] = None,
    ) -> int:
        """
        Persist an audit event.
        """

        cursor = self.connection.cursor()

        serialized_metadata = self._serialize(
            metadata
        )

        cursor.execute(
            """
            INSERT INTO audit_events (
                event_type,
                message,
                metadata,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                event_type,
                message,
                serialized_metadata,
                self._timestamp(),
            ),
        )

        self.connection.commit()

        return cursor.lastrowid

    def get_audit_events(
        self,
    ) -> list[dict]:
        """
        Return stored audit events.
        """

        cursor = self.connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM audit_events
            ORDER BY id ASC
            """
        )

        rows = cursor.fetchall()

        events = []

        for row in rows:
            event = dict(row)

            if event["metadata"] is not None:
                event["metadata"] = (
                    self._deserialize(
                        event["metadata"]
                    )
                )

            events.append(event)

        return events

    # ---------------------------------------------------------
    # DATABASE LIFECYCLE
    # ---------------------------------------------------------

    def close(self) -> None:
        """
        Close the SQLite connection.
        """

        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        self.close()