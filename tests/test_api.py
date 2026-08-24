import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.routes import orchestrator


client = TestClient(app)


# ---------------------------------------------------------
# BASIC API TESTS
# ---------------------------------------------------------

def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "running"
    assert body["platform"] == (
        "AI Autonomous DevOps Platform"
    )


def test_health_endpoint():
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_execute_rejects_short_request():
    response = client.post(
        "/api/v1/execute",
        json={
            "request": "x",
        },
    )

    assert response.status_code == 422


def test_execute_accepts_valid_request(monkeypatch):
    kubernetes_agent = next(
        agent
        for agent in orchestrator.agents
        if agent.name == "kubernetes"
    )

    monkeypatch.setattr(
        kubernetes_agent,
        "execute",
        lambda context=None: {
            "kubernetes": {
                "status": "success",
                "test": True,
            }
        },
    )

    response = client.post(
        "/api/v1/execute",
        json={
            "request": "Check Kubernetes pod health",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert "status" in body


def test_get_executions():
    response = client.get(
        "/api/v1/executions"
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_audit_events():
    response = client.get(
        "/api/v1/audit"
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_pending_approvals():
    response = client.get(
        "/api/v1/approvals"
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_unknown_approval_returns_404():
    response = client.get(
        "/api/v1/approvals/does-not-exist"
    )

    assert response.status_code == 404


# ---------------------------------------------------------
# MULTI-AGENT REGISTRATION
# ---------------------------------------------------------

def test_health_lists_all_registered_agents():
    response = client.get("/api/v1/health")

    assert response.status_code == 200

    body = response.json()

    assert body["registered_agents"] == [
        "ansible",
        "docker",
        "github",
        "jira",
        "kubernetes",
        "monitoring",
        "terraform",
    ]


# ---------------------------------------------------------
# MULTI-AGENT ROUTING
# ---------------------------------------------------------

@pytest.mark.parametrize(
    ("request_text", "expected_agent"),
    [
        (
            "Check Jira issue KAN-4",
            "jira",
        ),
        (
            "Check Docker container health",
            "docker",
        ),
        (
            "Check GitHub repository",
            "github",
        ),
        (
            "Check Terraform infrastructure",
            "terraform",
        ),
        (
            "Check Ansible configuration",
            "ansible",
        ),
        (
            "Check monitoring health",
            "monitoring",
        ),
        (
            "Check Kubernetes pods",
            "kubernetes",
        ),
    ],
)
def test_routes_request_to_expected_agent(
    monkeypatch,
    request_text,
    expected_agent,
):
    """
    Verify DecisionEngine -> Orchestrator routing without
    executing real infrastructure commands.
    """

    selected_agent = next(
        agent
        for agent in orchestrator.agents
        if agent.name == expected_agent
    )

    monkeypatch.setattr(
        selected_agent,
        "execute",
        lambda context=None: {
            "status": "success",
            "test_mode": True,
        },
    )

    response = client.post(
        "/api/v1/execute",
        json={
            "request": request_text,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "routed"
    assert body["agent"] == expected_agent