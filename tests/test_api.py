from fastapi.testclient import TestClient

from src.api.app import app


client = TestClient(app)


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


def test_execute_accepts_valid_request():
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