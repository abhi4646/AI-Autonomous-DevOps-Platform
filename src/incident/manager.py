from typing import Any, Dict, Optional

from src.correlation.causal_chain import (
    CausalChainBuilder,
)
from src.correlation.signal import (
    OperationalSignal,
)
from src.incident.lifecycle import (
    IncidentLifecycle,
)
from src.incident.model import (
    Incident,
    IncidentSeverity,
    IncidentStatus,
)
from src.persistence.database import Database


class IncidentManager:
    """
    Coordinates persistent incident lifecycle operations.

    The manager provides the boundary between remediation,
    correlation, RCA, and incident persistence.

    All lifecycle transitions pass through IncidentLifecycle
    before being persisted.
    """

    def __init__(
        self,
        database: Database,
        lifecycle: Optional[
            IncidentLifecycle
        ] = None,
        causal_chain_builder: Optional[
            CausalChainBuilder
        ] = None,
    ) -> None:
        self.database = database

        self.lifecycle = (
            lifecycle
            or IncidentLifecycle()
        )

        self.causal_chain_builder = (
            causal_chain_builder
            or CausalChainBuilder()
        )

    # ---------------------------------------------------------
    # INCIDENT CREATION
    # ---------------------------------------------------------

    def create(
        self,
        *,
        title: str,
        agent: str,
        severity: IncidentSeverity,
        health_snapshot: Optional[
            Dict[str, Any]
        ] = None,
        approval_id: Optional[str] = None,
        rollback_available: bool = False,
        metadata: Optional[
            Dict[str, Any]
        ] = None,
    ) -> Incident:
        """
        Create and persist a newly detected incident.
        """

        incident = Incident(
            title=title,
            agent=agent,
            severity=severity,
            health_snapshot=health_snapshot,
            approval_id=approval_id,
            rollback_available=(
                rollback_available
            ),
            metadata=metadata,
        )

        self.database.save_incident(
            incident.to_dict()
        )

        return incident

    # ---------------------------------------------------------
    # RETRIEVAL
    # ---------------------------------------------------------

    def get(
        self,
        incident_id: str,
    ) -> Optional[Incident]:
        """
        Retrieve a persisted incident.
        """

        data = self.database.get_incident(
            incident_id
        )

        if data is None:
            return None

        return Incident.from_dict(data)

    # ---------------------------------------------------------
    # LIFECYCLE TRANSITIONS
    # ---------------------------------------------------------

    def transition(
        self,
        incident_id: str,
        target: IncidentStatus,
    ) -> Incident:
        """
        Move an incident through a valid lifecycle transition
        and persist the resulting state.
        """

        incident = self.get(
            incident_id
        )

        if incident is None:
            raise KeyError(
                f"Incident "
                f"'{incident_id}' "
                f"does not exist"
            )

        self.lifecycle.transition(
            incident,
            target,
        )

        self.database.update_incident(
            incident.to_dict()
        )

        return incident

    # ---------------------------------------------------------
    # WORKFLOW CONTEXT
    # ---------------------------------------------------------

    def set_approval(
        self,
        incident_id: str,
        approval_id: str,
    ) -> Incident:
        """
        Associate a remediation approval with an incident.
        """

        incident = self.get(
            incident_id
        )

        if incident is None:
            raise KeyError(
                f"Incident "
                f"'{incident_id}' "
                f"does not exist"
            )

        incident.approval_id = approval_id

        incident.updated_at = (
            incident._timestamp()
        )

        self.database.update_incident(
            incident.to_dict()
        )

        return incident

    def set_retry_count(
        self,
        incident_id: str,
        retry_count: int,
    ) -> Incident:
        """
        Persist the current bounded retry count.
        """

        if retry_count < 0:
            raise ValueError(
                "retry_count cannot be negative"
            )

        incident = self.get(
            incident_id
        )

        if incident is None:
            raise KeyError(
                f"Incident "
                f"'{incident_id}' "
                f"does not exist"
            )

        incident.retry_count = retry_count

        incident.updated_at = (
            incident._timestamp()
        )

        self.database.update_incident(
            incident.to_dict()
        )

        return incident

    def set_rollback_available(
        self,
        incident_id: str,
        rollback_available: bool,
    ) -> Incident:
        """
        Persist whether rollback is available.
        """

        incident = self.get(
            incident_id
        )

        if incident is None:
            raise KeyError(
                f"Incident "
                f"'{incident_id}' "
                f"does not exist"
            )

        incident.rollback_available = (
            rollback_available
        )

        incident.updated_at = (
            incident._timestamp()
        )

        self.database.update_incident(
            incident.to_dict()
        )

        return incident

    # ---------------------------------------------------------
    # OPERATIONAL SIGNALS
    # ---------------------------------------------------------

    def add_signal(
        self,
        incident_id: str,
        signal: OperationalSignal,
    ) -> OperationalSignal:
        """
        Persist an operational signal and link it to
        an existing incident.

        The supplied incident ID is authoritative even if
        the signal was created without an incident ID.
        """

        incident = self.get(
            incident_id
        )

        if incident is None:
            raise KeyError(
                f"Incident "
                f"'{incident_id}' "
                f"does not exist"
            )

        existing = (
            self.database
            .get_operational_signal(
                signal.signal_id
            )
        )

        if existing is not None:
            raise ValueError(
                f"Operational signal "
                f"'{signal.signal_id}' "
                f"already exists"
            )

        self.database.save_operational_signal(
            signal.to_dict(),
            incident_id=incident_id,
        )

        stored = (
            self.database
            .get_operational_signal(
                signal.signal_id
            )
        )

        if stored is None:
            raise RuntimeError(
                "Operational signal was not persisted"
            )

        return OperationalSignal.from_dict(
            stored
        )

    def get_signals(
        self,
        incident_id: str,
    ) -> list[OperationalSignal]:
        """
        Return operational signals linked to an incident
        in chronological order.
        """

        incident = self.get(
            incident_id
        )

        if incident is None:
            raise KeyError(
                f"Incident "
                f"'{incident_id}' "
                f"does not exist"
            )

        rows = (
            self.database
            .get_incident_signals(
                incident_id
            )
        )

        return [
            OperationalSignal.from_dict(
                row
            )
            for row in rows
        ]

    # ---------------------------------------------------------
    # ROOT-CAUSE ANALYSIS
    # ---------------------------------------------------------

    def analyze_root_cause(
        self,
        incident_id: str,
        failure_signal_id: str,
    ) -> Dict[str, Any]:
        """
        Analyze persisted incident signals against a
        supplied failure signal and persist the resulting
        explainable RCA.

        RCA does not mutate the incident lifecycle.
        """

        incident = self.get(
            incident_id
        )

        if incident is None:
            raise KeyError(
                f"Incident "
                f"'{incident_id}' "
                f"does not exist"
            )

        failure_data = (
            self.database
            .get_operational_signal(
                failure_signal_id
            )
        )

        if failure_data is None:
            raise KeyError(
                f"Operational signal "
                f"'{failure_signal_id}' "
                f"does not exist"
            )

        if (
            failure_data.get(
                "incident_id"
            )
            != incident_id
        ):
            raise ValueError(
                "Failure signal does not belong "
                "to the incident"
            )

        signals = self.get_signals(
            incident_id
        )

        failure_signal = next(
            (
                signal
                for signal in signals
                if signal.signal_id
                == failure_signal_id
            ),
            None,
        )

        if failure_signal is None:
            raise KeyError(
                f"Operational signal "
                f"'{failure_signal_id}' "
                f"is not linked to incident "
                f"'{incident_id}'"
            )

        result = (
            self.causal_chain_builder
            .build(
                failure_signal,
                signals,
            )
        )

        rca_id = (
            self.database
            .save_rca_result(
                incident_id,
                result,
            )
        )

        return {
            "rca_id": rca_id,
            "incident_id": incident_id,
            **result,
        }