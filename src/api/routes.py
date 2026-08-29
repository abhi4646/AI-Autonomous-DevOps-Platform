import os

from fastapi import APIRouter, Depends, HTTPException, status

from src.ansible.agent import AnsibleAgent
from src.api.models import (
    ApprovalDecision,
    ExecuteRequest,
    OperationalSignalRequest,
)
from src.docker.agent import DockerAgent
from src.github.agent import GitHubAgent
from src.incident.manager import IncidentManager
from src.jira.agent import JiraAgent
from src.kubernetes.agent import KubernetesAgent
from src.monitoring.agent import MonitoringAgent
from src.orchestrator.orchestrator import Orchestrator
from src.persistence.database import Database
from src.security.auth import AuthenticatedPrincipal
from src.security.identity import build_authenticated_context
from src.security.operations import can_execute_request
from src.security.rbac import (
    Permission,
    require_permission,
)
from src.terraform.agent import TerraformAgent


router = APIRouter(
    prefix="/api/v1",
    tags=["DevOps API"],
)


# ---------------------------------------------------------
# PLATFORM DEPENDENCIES
# ---------------------------------------------------------

# Normal application:
#     data/devops_platform.db
#
# Tests can override this using:
#     DEVOPS_DB_PATH
#
# This prevents pytest from writing fake test data into
# the real development database.
database_path = os.getenv(
    "DEVOPS_DB_PATH",
    "data/devops_platform.db",
)

database = Database(database_path)

orchestrator = Orchestrator(
    database=database,
)

incident_manager = IncidentManager(
    database=database,
)


# ---------------------------------------------------------
# REGISTER DEVOPS AGENTS
# ---------------------------------------------------------

agents = [
    ("ansible", AnsibleAgent()),
    ("docker", DockerAgent()),
    ("github", GitHubAgent()),
    ("jira", JiraAgent()),
    ("kubernetes", KubernetesAgent()),
    ("monitoring", MonitoringAgent()),
    ("terraform", TerraformAgent()),
]

for routing_name, agent in agents:
    agent.name = routing_name
    orchestrator.register_agent(agent)


# ---------------------------------------------------------
# HEALTH
# ---------------------------------------------------------

@router.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "AI Autonomous DevOps Platform",
        "registered_agents": [
            agent.name
            for agent in orchestrator.agents
        ],
    }


# ---------------------------------------------------------
# EXECUTION
# ---------------------------------------------------------

@router.post("/execute")
def execute(
    payload: ExecuteRequest,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.EXECUTE_OPERATION
        )
    ),
):
    """
    Submit a DevOps request to the orchestrator.

    If approval_id is supplied, the orchestrator attempts
    to resume a previously approved workflow.
    """

    if not can_execute_request(
        principal,
        payload.request,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Destructive operation requires "
                "elevated permissions"
            ),
        )

    authenticated_context = (
        build_authenticated_context(
            principal
        )
    )

    try:
        result = orchestrator.route(
            request=payload.request,
            approval_id=payload.approval_id,
            context=authenticated_context,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return result


# ---------------------------------------------------------
# EXECUTION HISTORY
# ---------------------------------------------------------

@router.get("/executions")
def get_executions(
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.READ_EXECUTIONS
        )
    ),
):
    """Return persisted agent execution history."""

    return database.get_executions()


# ---------------------------------------------------------
# METRICS
# ---------------------------------------------------------

@router.get("/metrics")
def get_metrics(
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.READ_METRICS
        )
    ),
):
    """
    Return aggregate execution metrics.
    """

    return database.get_execution_metrics()


# ---------------------------------------------------------
# AUDIT EVENTS
# ---------------------------------------------------------

@router.get("/audit")
def get_audit_events(
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.READ_AUDIT
        )
    ),
):
    """Return persisted audit events."""

    return database.get_audit_events()


# ---------------------------------------------------------
# APPROVALS
# ---------------------------------------------------------

@router.get("/approvals")
def get_pending_approvals(
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.READ_APPROVALS
        )
    ),
):
    """Return pending human approval requests."""

    return orchestrator.approval_manager.get_pending()


@router.get("/approvals/{approval_id}")
def get_approval(
    approval_id: str,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.READ_APPROVALS
        )
    ),
):
    """Return one approval request."""

    approval = (
        orchestrator
        .approval_manager
        .get_request(approval_id)
    )

    if approval is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval request not found",
        )

    return approval


@router.post("/approvals/decision")
def decide_approval(
    payload: ApprovalDecision,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.DECIDE_APPROVALS
        )
    ),
):
    """
    Approve or reject a pending operation.
    """

    try:
        if payload.decision == "approved":
            approval = (
                orchestrator
                .approval_manager
                .approve(
                    approval_id=payload.approval_id,
                    decided_by=payload.decided_by,
                    reason=payload.reason,
                )
            )

        else:
            approval = (
                orchestrator
                .approval_manager
                .reject(
                    approval_id=payload.approval_id,
                    decided_by=payload.decided_by,
                    reason=payload.reason,
                )
            )

    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return {
        "status": approval["status"],
        "approval_id": approval["approval_id"],
        "decided_by": approval["decided_by"],
        "decided_at": approval["decided_at"],
        "reason": approval["reason"],
    }


# ---------------------------------------------------------
# INCIDENTS
# ---------------------------------------------------------

@router.get("/incidents")
def get_incidents(
    incident_status: str | None = None,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.READ_INCIDENTS
        )
    ),
):
    """
    Return persisted operational incidents.

    Optionally filter incidents by lifecycle status using:

        /api/v1/incidents?incident_status=resolved
    """

    return database.get_incidents(
        status=incident_status,
    )


@router.get("/incidents/{incident_id}")
def get_incident(
    incident_id: str,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.READ_INCIDENTS
        )
    ),
):
    """
    Return one operational incident by its stable incident ID.
    """

    incident = database.get_incident(
        incident_id
    )

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )

    return incident


# ---------------------------------------------------------
# OPERATIONAL SIGNALS
# ---------------------------------------------------------

@router.post(
    "/signals",
    status_code=status.HTTP_201_CREATED,
)
def create_operational_signal(
    payload: OperationalSignalRequest,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.CREATE_SIGNALS
        )
    ),
):
    """
    Persist a new operational signal.

    A signal may optionally be linked directly to an
    existing incident using incident_id.
    """

    signal = payload.model_dump(
        exclude_none=True,
    )

    incident_id = signal.get(
        "incident_id"
    )

    if incident_id is not None:
        incident = database.get_incident(
            incident_id
        )

        if incident is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Incident not found",
            )

    if database.get_operational_signal(
        payload.signal_id
    ) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Operational signal already exists",
        )

    try:
        database.save_operational_signal(
            signal
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    stored = database.get_operational_signal(
        payload.signal_id
    )

    return stored


@router.get("/signals")
def get_operational_signals(
    incident_id: str | None = None,
    correlation_key: str | None = None,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.READ_SIGNALS
        )
    ),
):
    """
    Return persisted operational signals.

    Results may be filtered by incident_id,
    correlation_key, or both.
    """

    return database.get_operational_signals(
        incident_id=incident_id,
        correlation_key=correlation_key,
    )


@router.get("/signals/{signal_id}")
def get_operational_signal(
    signal_id: str,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.READ_SIGNALS
        )
    ),
):
    """
    Return one operational signal.
    """

    signal = database.get_operational_signal(
        signal_id
    )

    if signal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Operational signal not found",
        )

    return signal


# ---------------------------------------------------------
# INCIDENT CORRELATION / RCA
# ---------------------------------------------------------

@router.get(
    "/incidents/{incident_id}/signals"
)
def get_incident_signals(
    incident_id: str,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.READ_SIGNALS
        )
    ),
):
    """
    Return all operational signals linked
    to an incident.
    """

    incident = database.get_incident(
        incident_id
    )

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )

    return database.get_incident_signals(
        incident_id
    )


@router.get(
    "/incidents/{incident_id}/rca"
)
def get_incident_rca_history(
    incident_id: str,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.READ_RCA
        )
    ),
):
    """
    Return persisted RCA history for an incident.
    """

    incident = database.get_incident(
        incident_id
    )

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )

    return database.get_rca_results(
        incident_id
    )


@router.get(
    "/incidents/{incident_id}/rca/latest"
)
def get_latest_incident_rca(
    incident_id: str,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.READ_RCA
        )
    ),
):
    """
    Return the latest RCA result for an incident.
    """

    incident = database.get_incident(
        incident_id
    )

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )

    result = database.get_latest_rca_result(
        incident_id
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Root-cause analysis "
                "not found"
            ),
        )

    return result


@router.post(
    "/incidents/{incident_id}/rca/analyze"
)
def analyze_incident_root_cause(
    incident_id: str,
    failure_signal_id: str,
    principal: AuthenticatedPrincipal = Depends(
        require_permission(
            Permission.RUN_RCA
        )
    ),
):
    """
    Run explainable root-cause analysis for an incident
    using its persisted operational signals.

    The failure signal must already be linked to the
    supplied incident.
    """

    incident = database.get_incident(
        incident_id
    )

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )

    failure_signal = (
        database
        .get_operational_signal(
            failure_signal_id
        )
    )

    if failure_signal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Operational signal not found",
        )

    if (
        failure_signal.get(
            "incident_id"
        )
        != incident_id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Failure signal does not belong "
                "to the incident"
            ),
        )

    try:
        return (
            incident_manager
            .analyze_root_cause(
                incident_id,
                failure_signal_id,
            )
        )

    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc