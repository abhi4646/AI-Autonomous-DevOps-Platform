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
    - approval requests
    - audit events

    SQLite is used for the initial implementation so the platform
    can run locally without requiring an external database service.
    """

    def __init__(self, db_path: str = "data/devops_platform.db"):
        self.db_path = db_path

        # Special SQLite in-memory database
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.connection = sqlite3.connect(
            db_path,
            check_same_thread=False,
        )

        self.connection.row_factory = sqlite3.Row

        self._create_tables()

    @staticmethod
    def _timestamp() -> str:
        """Return a UTC ISO-8601 timestamp."""
        return datetime.now(timezone.utc).isoformat()

    def _create_tables(self) -> None:
        """Create database tables if they do not already exist."""

        cursor = self.connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request TEXT NOT NULL,
                agent TEXT NOT NULL,
                status TEXT NOT NULL,
                result TEXT,
                created_at TEXT NOT NULL
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

    # ---------------------------------------------------------
    # EXECUTIONS
    # ---------------------------------------------------------

    def save_execution(
        self,
        request: str,
        agent: str,
        status: str,
        result: Optional[Any] = None,
    ) -> int:
        """Persist an agent execution."""

        cursor = self.connection.cursor()

        serialized_result = (
            json.dumps(result)
            if result is not None
            else None
        )

        cursor.execute(
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
                request,
                agent,
                status,
                serialized_result,
                self._timestamp(),
            ),
        )

        self.connection.commit()

        return cursor.lastrowid

    def get_executions(self) -> list[dict]:
        """Return all stored executions."""

        cursor = self.connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM executions
            ORDER BY id ASC
            """
        )

        rows = cursor.fetchall()

        results = []

        for row in rows:
            item = dict(row)

            if item["result"] is not None:
                item["result"] = json.loads(item["result"])

            results.append(item)

        return results

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
        """Persist an approval request."""

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
        """Update an existing approval decision."""

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
                f"Approval request '{approval_id}' does not exist"
            )

        self.connection.commit()

    def get_approval(
        self,
        approval_id: str,
    ) -> Optional[dict]:
        """Retrieve one approval request."""

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

    def get_pending_approvals(self) -> list[dict]:
        """Return all pending approval requests."""

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
        """Persist an audit event."""

        cursor = self.connection.cursor()

        serialized_metadata = (
            json.dumps(metadata)
            if metadata is not None
            else None
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

    def get_audit_events(self) -> list[dict]:
        """Return stored audit events."""

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
                event["metadata"] = json.loads(
                    event["metadata"]
                )

            events.append(event)

        return events

    # ---------------------------------------------------------
    # DATABASE LIFECYCLE
    # ---------------------------------------------------------

    def close(self) -> None:
        """Close the SQLite connection."""

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