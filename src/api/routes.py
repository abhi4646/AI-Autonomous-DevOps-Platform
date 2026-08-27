import os

from fastapi import APIRouter, HTTPException, status

from src.ansible.agent import AnsibleAgent
from src.api.models import (
    ApprovalDecision,
    ExecuteRequest,
)
from src.docker.agent import DockerAgent
from src.github.agent import GitHubAgent
from src.jira.agent import JiraAgent
from src.kubernetes.agent import KubernetesAgent
from src.monitoring.agent import MonitoringAgent
from src.orchestrator.orchestrator import Orchestrator
from src.persistence.database import Database
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


# ---------------------------------------------------------
# REGISTER DEVOPS AGENTS
# ---------------------------------------------------------

# DecisionEngine routes requests using these lowercase keys:
#
# ansible
# docker
# github
# jira
# kubernetes
# monitoring
# terraform
#
# Individual agent classes use human-readable display names,
# so normalize their names to the routing keys before
# registering them with the orchestrator.

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
def execute(payload: ExecuteRequest):
    """
    Submit a DevOps request to the orchestrator.

    If approval_id is supplied, the orchestrator attempts
    to resume a previously approved workflow.
    """

    try:
        result = orchestrator.route(
            request=payload.request,
            approval_id=payload.approval_id,
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
def get_executions():
    """Return persisted agent execution history."""

    return database.get_executions()


# ---------------------------------------------------------
# METRICS
# ---------------------------------------------------------

@router.get("/metrics")
def get_metrics():
    """
    Return aggregate execution metrics.

    Includes:
    - total executions
    - success and failure counts
    - success and failure rates
    - average execution duration
    - per-status counts
    - per-agent activity
    - recent failures
    """

    return database.get_execution_metrics()


# ---------------------------------------------------------
# AUDIT EVENTS
# ---------------------------------------------------------

@router.get("/audit")
def get_audit_events():
    """Return persisted audit events."""

    return database.get_audit_events()


# ---------------------------------------------------------
# APPROVALS
# ---------------------------------------------------------

@router.get("/approvals")
def get_pending_approvals():
    """Return pending human approval requests."""

    return orchestrator.approval_manager.get_pending()


@router.get("/approvals/{approval_id}")
def get_approval(
    approval_id: str,
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
):
    """
    Approve or reject a pending operation.

    An approved request can subsequently be resumed by
    calling /execute with the same approval_id.
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
