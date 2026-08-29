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
    - incidents

    Existing databases are migrated automatically when new
    execution telemetry or approval workflow columns are introduced.
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
        # 1. Create base tables
        # 2. Migrate legacy tables
        # 3. Create indexes that depend on migrated columns
        self._create_tables()
        self._migrate_execution_table()
        self._migrate_approval_table()
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

        Existing tables are left intact by SQLite.
        Missing columns are added by migration methods.
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
                decided_at TEXT,
                action TEXT,
                reason TEXT,
                approval_metadata TEXT
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

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS incidents (
                incident_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                agent TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT NOT NULL,
                health_snapshot TEXT,
                approval_id TEXT,
                retry_count INTEGER NOT NULL DEFAULT 0,
                rollback_available INTEGER NOT NULL DEFAULT 0,
                incident_metadata TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                resolved_at TEXT
            )
            """
        )


        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS operational_signals (
                signal_id TEXT PRIMARY KEY,
                incident_id TEXT,
                signal_type TEXT NOT NULL,
                source TEXT NOT NULL,
                resource TEXT NOT NULL,
                message TEXT NOT NULL,
                severity TEXT NOT NULL,
                environment TEXT,
                agent TEXT,
                correlation_key TEXT,
                occurred_at TEXT NOT NULL,
                signal_metadata TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (incident_id)
                    REFERENCES incidents(incident_id)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS rca_results (
                rca_id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id TEXT NOT NULL,
                failure_signal_id TEXT NOT NULL,
                probable_root_cause TEXT,
                confidence REAL NOT NULL DEFAULT 0.0,
                explanation TEXT NOT NULL,
                causal_chain TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (incident_id)
                    REFERENCES incidents(incident_id),
                FOREIGN KEY (failure_signal_id)
                    REFERENCES operational_signals(signal_id)
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

    def _migrate_approval_table(self) -> None:
        """
        Upgrade existing approval tables with persistent
        workflow context without deleting existing records.
        """

        cursor = self.connection.cursor()

        cursor.execute(
            "PRAGMA table_info(approvals)"
        )

        existing_columns = {
            row["name"]
            for row in cursor.fetchall()
        }

        required_columns = {
            "action": "TEXT",
            "reason": "TEXT",
            "approval_metadata": "TEXT",
        }

        for (
            column_name,
            column_type,
        ) in required_columns.items():
            if column_name not in existing_columns:
                cursor.execute(
                    f"""
                    ALTER TABLE approvals
                    ADD COLUMN {column_name} {column_type}
                    """
                )

        self.connection.commit()

    def _create_indexes(self) -> None:
        """
        Create indexes after migrations have completed.
        """

        cursor = self.connection.cursor()

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_executions_execution_id
            ON executions(execution_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_incidents_status
            ON incidents(status)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_incidents_agent
            ON incidents(agent)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_incidents_created_at
            ON incidents(created_at)
            """
        )


        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_operational_signals_incident_id
            ON operational_signals(incident_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_operational_signals_correlation_key
            ON operational_signals(correlation_key)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_operational_signals_occurred_at
            ON operational_signals(occurred_at)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_rca_results_incident_id
            ON rca_results(incident_id)
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

    def _deserialize_approval(
        self,
        row,
    ) -> dict:
        item = dict(row)

        if item.get("approval_metadata") is not None:
            item["approval_metadata"] = self._deserialize(
                item["approval_metadata"]
            )

        return item

    def _deserialize_incident(
        self,
        row,
    ) -> dict:
        item = dict(row)

        if item.get("health_snapshot") is not None:
            item["health_snapshot"] = self._deserialize(
                item["health_snapshot"]
            )
        else:
            item["health_snapshot"] = {}

        if item.get("incident_metadata") is not None:
            item["metadata"] = self._deserialize(
                item["incident_metadata"]
            )
        else:
            item["metadata"] = {}

        item.pop(
            "incident_metadata",
            None,
        )

        item["rollback_available"] = bool(
            item.get(
                "rollback_available",
                0,
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

    # ---------------------------------------------------------
    # EXECUTION METRICS
    # ---------------------------------------------------------

    def get_execution_metrics(self) -> dict:
        """
        Return aggregate metrics derived from persisted
        execution telemetry.
        """

        executions = self.get_executions()

        total_executions = len(executions)

        successful_statuses = {
            "success",
            "routed",
        }

        failed_statuses = {
            "failed",
            "failure",
            "error",
            "timeout",
            "unavailable",
            "blocked",
        }

        successful_executions = 0
        failed_executions = 0

        status_counts = {}
        agent_activity = {}
        durations = []
        recent_failures = []

        for execution in executions:
            execution_status = (
                execution.get("status")
                or "unknown"
            )

            agent = (
                execution.get("agent")
                or "unknown"
            )

            status_counts[execution_status] = (
                status_counts.get(
                    execution_status,
                    0,
                )
                + 1
            )

            agent_activity[agent] = (
                agent_activity.get(
                    agent,
                    0,
                )
                + 1
            )

            if execution_status in successful_statuses:
                successful_executions += 1

            if execution_status in failed_statuses:
                failed_executions += 1

                recent_failures.append(
                    {
                        "execution_id": execution.get(
                            "execution_id"
                        ),
                        "request": execution.get(
                            "request"
                        ),
                        "agent": agent,
                        "status": execution_status,
                        "error": execution.get(
                            "error"
                        ),
                        "created_at": execution.get(
                            "created_at"
                        ),
                    }
                )

            duration_ms = execution.get(
                "duration_ms"
            )

            if isinstance(
                duration_ms,
                (int, float),
            ):
                durations.append(
                    duration_ms
                )

        success_rate = (
            round(
                (
                    successful_executions
                    / total_executions
                )
                * 100,
                2,
            )
            if total_executions
            else 0.0
        )

        failure_rate = (
            round(
                (
                    failed_executions
                    / total_executions
                )
                * 100,
                2,
            )
            if total_executions
            else 0.0
        )

        average_duration_ms = (
            round(
                sum(durations)
                / len(durations),
                2,
            )
            if durations
            else 0.0
        )

        recent_failures = (
            recent_failures[-10:]
        )

        recent_failures.reverse()

        return {
            "total_executions": total_executions,
            "successful_executions": (
                successful_executions
            ),
            "failed_executions": (
                failed_executions
            ),
            "success_rate": success_rate,
            "failure_rate": failure_rate,
            "average_duration_ms": (
                average_duration_ms
            ),
            "status_counts": status_counts,
            "agent_activity": agent_activity,
            "recent_failures": recent_failures,
        }

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
        action: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """
        Persist an approval request and its workflow context.
        """

        cursor = self.connection.cursor()

        serialized_metadata = self._serialize(
            metadata
        )

        cursor.execute(
            """
            INSERT INTO approvals (
                approval_id,
                request,
                agent,
                risk_level,
                status,
                created_at,
                action,
                approval_metadata
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                approval_id,
                request,
                agent,
                risk_level,
                status,
                self._timestamp(),
                action,
                serialized_metadata,
            ),
        )

        self.connection.commit()

    def update_approval(
        self,
        approval_id: str,
        status: str,
        decided_by: str,
        reason: Optional[str] = None,
    ) -> None:
        """
        Update and persist an approval decision.
        """

        cursor = self.connection.cursor()

        cursor.execute(
            """
            UPDATE approvals
            SET
                status = ?,
                decided_by = ?,
                decided_at = ?,
                reason = ?
            WHERE approval_id = ?
            """,
            (
                status,
                decided_by,
                self._timestamp(),
                reason,
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

        return self._deserialize_approval(
            row
        )

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
            self._deserialize_approval(row)
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
    # INCIDENTS
    # ---------------------------------------------------------

    def save_incident(
        self,
        incident: dict,
    ) -> None:
        """
        Persist a newly detected operational incident.
        """

        cursor = self.connection.cursor()

        cursor.execute(
            """
            INSERT INTO incidents (
                incident_id,
                title,
                agent,
                severity,
                status,
                health_snapshot,
                approval_id,
                retry_count,
                rollback_available,
                incident_metadata,
                created_at,
                updated_at,
                resolved_at
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                incident["incident_id"],
                incident["title"],
                incident["agent"],
                incident["severity"],
                incident["status"],
                self._serialize(
                    incident.get(
                        "health_snapshot",
                        {},
                    )
                ),
                incident.get(
                    "approval_id"
                ),
                incident.get(
                    "retry_count",
                    0,
                ),
                int(
                    incident.get(
                        "rollback_available",
                        False,
                    )
                ),
                self._serialize(
                    incident.get(
                        "metadata",
                        {},
                    )
                ),
                incident["created_at"],
                incident["updated_at"],
                incident.get(
                    "resolved_at"
                ),
            ),
        )

        self.connection.commit()

    def update_incident(
        self,
        incident: dict,
    ) -> None:
        """
        Persist the latest state of an existing incident.
        """

        cursor = self.connection.cursor()

        cursor.execute(
            """
            UPDATE incidents
            SET
                title = ?,
                agent = ?,
                severity = ?,
                status = ?,
                health_snapshot = ?,
                approval_id = ?,
                retry_count = ?,
                rollback_available = ?,
                incident_metadata = ?,
                updated_at = ?,
                resolved_at = ?
            WHERE incident_id = ?
            """,
            (
                incident["title"],
                incident["agent"],
                incident["severity"],
                incident["status"],
                self._serialize(
                    incident.get(
                        "health_snapshot",
                        {},
                    )
                ),
                incident.get(
                    "approval_id"
                ),
                incident.get(
                    "retry_count",
                    0,
                ),
                int(
                    incident.get(
                        "rollback_available",
                        False,
                    )
                ),
                self._serialize(
                    incident.get(
                        "metadata",
                        {},
                    )
                ),
                incident["updated_at"],
                incident.get(
                    "resolved_at"
                ),
                incident["incident_id"],
            ),
        )

        if cursor.rowcount == 0:
            raise KeyError(
                f"Incident "
                f"'{incident['incident_id']}' "
                f"does not exist"
            )

        self.connection.commit()

    def get_incident(
        self,
        incident_id: str,
    ) -> Optional[dict]:
        """
        Retrieve one incident by its stable incident ID.
        """

        cursor = self.connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM incidents
            WHERE incident_id = ?
            """,
            (incident_id,),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return self._deserialize_incident(
            row
        )

    def get_incidents(
        self,
        *,
        status: Optional[str] = None,
    ) -> list[dict]:
        """
        Return incidents, optionally filtered by status.
        """

        cursor = self.connection.cursor()

        if status is None:
            cursor.execute(
                """
                SELECT *
                FROM incidents
                ORDER BY created_at DESC
                """
            )
        else:
            cursor.execute(
                """
                SELECT *
                FROM incidents
                WHERE status = ?
                ORDER BY created_at DESC
                """,
                (status,),
            )

        return [
            self._deserialize_incident(row)
            for row in cursor.fetchall()
        ]


    # ---------------------------------------------------------
    # OPERATIONAL SIGNALS
    # ---------------------------------------------------------

    def save_operational_signal(
        self,
        signal: dict,
        *,
        incident_id: Optional[str] = None,
    ) -> None:
        """
        Persist an operational signal.

        The signal may already contain an incident_id.
        An explicitly supplied incident_id takes precedence.
        """

        cursor = self.connection.cursor()

        linked_incident_id = (
            incident_id
            if incident_id is not None
            else signal.get("incident_id")
        )

        cursor.execute(
            """
            INSERT INTO operational_signals (
                signal_id,
                incident_id,
                signal_type,
                source,
                resource,
                message,
                severity,
                environment,
                agent,
                correlation_key,
                occurred_at,
                signal_metadata,
                created_at
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                signal["signal_id"],
                linked_incident_id,
                signal["signal_type"],
                signal["source"],
                signal["resource"],
                signal.get(
                    "message",
                    "",
                ),
                signal["severity"],
                signal.get(
                    "environment"
                ),
                signal.get(
                    "agent"
                ),
                signal.get(
                    "correlation_key"
                ),
                signal["occurred_at"],
                self._serialize(
                    signal.get(
                        "metadata",
                        {},
                    )
                ),
                signal.get(
                    "created_at",
                    self._timestamp(),
                ),
            ),
        )

        self.connection.commit()

    def get_operational_signal(
        self,
        signal_id: str,
    ) -> Optional[dict]:
        """
        Retrieve one operational signal.
        """

        cursor = self.connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM operational_signals
            WHERE signal_id = ?
            """,
            (
                signal_id,
            ),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return (
            self._deserialize_operational_signal(
                row
            )
        )

    def get_operational_signals(
        self,
        *,
        incident_id: Optional[str] = None,
        correlation_key: Optional[str] = None,
    ) -> list[dict]:
        """
        Retrieve operational signals.

        Results are ordered chronologically.
        """

        cursor = self.connection.cursor()

        query = """
            SELECT *
            FROM operational_signals
        """

        conditions = []
        parameters = []

        if incident_id is not None:
            conditions.append(
                "incident_id = ?"
            )

            parameters.append(
                incident_id
            )

        if correlation_key is not None:
            conditions.append(
                "correlation_key = ?"
            )

            parameters.append(
                correlation_key
            )

        if conditions:
            query += (
                " WHERE "
                + " AND ".join(
                    conditions
                )
            )

        query += (
            " ORDER BY occurred_at ASC"
        )

        cursor.execute(
            query,
            tuple(parameters),
        )

        return [
            self._deserialize_operational_signal(
                row
            )
            for row in cursor.fetchall()
        ]

    def get_incident_signals(
        self,
        incident_id: str,
    ) -> list[dict]:
        """
        Retrieve signals linked to one incident.
        """

        return (
            self.get_operational_signals(
                incident_id=incident_id
            )
        )

    def link_signal_to_incident(
        self,
        signal_id: str,
        incident_id: str,
    ) -> None:
        """
        Link an existing operational signal
        to an incident.
        """

        cursor = self.connection.cursor()

        cursor.execute(
            """
            UPDATE operational_signals
            SET incident_id = ?
            WHERE signal_id = ?
            """,
            (
                incident_id,
                signal_id,
            ),
        )

        if cursor.rowcount == 0:
            raise KeyError(
                f"Operational signal "
                f"'{signal_id}' "
                f"does not exist"
            )

        self.connection.commit()

    def _deserialize_operational_signal(
        self,
        row: sqlite3.Row,
    ) -> dict:
        """
        Convert an operational signal row
        into a dictionary.
        """

        signal = dict(row)

        metadata = signal.pop(
            "signal_metadata",
            None,
        )

        signal["metadata"] = (
            self._deserialize(
                metadata
            )
            if metadata is not None
            else {}
        )

        return signal

    # ---------------------------------------------------------
    # ROOT-CAUSE ANALYSIS
    # ---------------------------------------------------------

    def save_rca_result(
        self,
        incident_id: str,
        result: dict,
    ) -> int:
        """
        Persist one explainable RCA result.
        """

        cursor = self.connection.cursor()

        cursor.execute(
            """
            INSERT INTO rca_results (
                incident_id,
                failure_signal_id,
                probable_root_cause,
                confidence,
                explanation,
                causal_chain,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                incident_id,
                result["failure_signal_id"],
                self._serialize(
                    result.get(
                        "probable_root_cause"
                    )
                ),
                result.get(
                    "confidence",
                    0.0,
                ),
                result.get(
                    "explanation",
                    "",
                ),
                self._serialize(
                    result.get(
                        "chain",
                        [],
                    )
                ),
                result.get(
                    "created_at",
                    self._timestamp(),
                ),
            ),
        )

        self.connection.commit()

        return cursor.lastrowid

    def get_rca_results(
        self,
        incident_id: str,
    ) -> list[dict]:
        """
        Retrieve RCA history for an incident.
        """

        cursor = self.connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM rca_results
            WHERE incident_id = ?
            ORDER BY rca_id ASC
            """,
            (
                incident_id,
            ),
        )

        return [
            self._deserialize_rca_result(
                row
            )
            for row in cursor.fetchall()
        ]

    def get_latest_rca_result(
        self,
        incident_id: str,
    ) -> Optional[dict]:
        """
        Retrieve the most recent RCA result.
        """

        cursor = self.connection.cursor()

        cursor.execute(
            """
            SELECT *
            FROM rca_results
            WHERE incident_id = ?
            ORDER BY rca_id DESC
            LIMIT 1
            """,
            (
                incident_id,
            ),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return self._deserialize_rca_result(
            row
        )

    def _deserialize_rca_result(
        self,
        row: sqlite3.Row,
    ) -> dict:
        """
        Convert an RCA row into a dictionary.
        """

        result = dict(row)

        probable_root_cause = (
            result.get(
                "probable_root_cause"
            )
        )

        result[
            "probable_root_cause"
        ] = (
            self._deserialize(
                probable_root_cause
            )
            if probable_root_cause
            is not None
            else None
        )

        causal_chain = result.pop(
            "causal_chain",
            None,
        )

        result["chain"] = (
            self._deserialize(
                causal_chain
            )
            if causal_chain is not None
            else []
        )

        return result

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