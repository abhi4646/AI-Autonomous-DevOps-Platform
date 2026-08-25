from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api.app import app


client = TestClient(app)


@patch(
    "src.api.routes.database.get_execution_metrics"
)
def test_metrics_endpoint_returns_metrics(
    mock_get_metrics,
):
    mock_get_metrics.return_value = {
        "total_executions": 10,
        "successful_executions": 8,
        "failed_executions": 2,
        "success_rate": 80.0,
        "failure_rate": 20.0,
        "average_duration_ms": 125.5,
        "status_counts": {
            "success": 8,
            "failed": 2,
        },
        "agent_activity": {
            "kubernetes": 6,
            "docker": 4,
        },
        "recent_failures": [],
    }

    response = client.get(
        "/api/v1/metrics"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total_executions"] == 10
    assert body["successful_executions"] == 8
    assert body["failed_executions"] == 2
    assert body["success_rate"] == 80.0
    assert body["failure_rate"] == 20.0
    assert body["average_duration_ms"] == 125.5

    mock_get_metrics.assert_called_once_with()


def test_metrics_endpoint_has_expected_structure():
    response = client.get(
        "/api/v1/metrics"
    )

    assert response.status_code == 200

    body = response.json()

    expected_fields = {
        "total_executions",
        "successful_executions",
        "failed_executions",
        "success_rate",
        "failure_rate",
        "average_duration_ms",
        "status_counts",
        "agent_activity",
        "recent_failures",
    }

    assert expected_fields.issubset(
        body.keys()
    )

    assert isinstance(
        body["status_counts"],
        dict,
    )

    assert isinstance(
        body["agent_activity"],
        dict,
    )

    assert isinstance(
        body["recent_failures"],
        list,
    )