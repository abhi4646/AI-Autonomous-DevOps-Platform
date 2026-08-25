from src.persistence.database import Database


def test_execution_metrics_empty_database():
    database = Database(":memory:")

    metrics = database.get_execution_metrics()

    assert metrics["total_executions"] == 0
    assert metrics["successful_executions"] == 0
    assert metrics["failed_executions"] == 0
    assert metrics["success_rate"] == 0.0
    assert metrics["failure_rate"] == 0.0
    assert metrics["average_duration_ms"] == 0.0
    assert metrics["status_counts"] == {}
    assert metrics["agent_activity"] == {}
    assert metrics["recent_failures"] == []

    database.close()


def test_execution_metrics_counts_statuses():
    database = Database(":memory:")

    database.save_execution(
        request="Check Kubernetes pods",
        agent="kubernetes",
        status="success",
    )

    database.save_execution(
        request="Check Docker containers",
        agent="docker",
        status="failed",
    )

    database.save_execution(
        request="Check Terraform infrastructure",
        agent="terraform",
        status="success",
    )

    metrics = database.get_execution_metrics()

    assert metrics["total_executions"] == 3
    assert metrics["successful_executions"] == 2
    assert metrics["failed_executions"] == 1

    assert metrics["status_counts"] == {
        "success": 2,
        "failed": 1,
    }

    database.close()


def test_execution_metrics_calculates_rates():
    database = Database(":memory:")

    for index in range(3):
        database.save_execution(
            request=f"Successful request {index}",
            agent="kubernetes",
            status="success",
        )

    database.save_execution(
        request="Failed request",
        agent="kubernetes",
        status="failed",
    )

    metrics = database.get_execution_metrics()

    assert metrics["total_executions"] == 4
    assert metrics["success_rate"] == 75.0
    assert metrics["failure_rate"] == 25.0

    database.close()


def test_execution_metrics_tracks_agent_activity():
    database = Database(":memory:")

    database.save_execution(
        request="Kubernetes request 1",
        agent="kubernetes",
        status="success",
    )

    database.save_execution(
        request="Kubernetes request 2",
        agent="kubernetes",
        status="success",
    )

    database.save_execution(
        request="Docker request",
        agent="docker",
        status="success",
    )

    metrics = database.get_execution_metrics()

    assert metrics["agent_activity"] == {
        "kubernetes": 2,
        "docker": 1,
    }

    database.close()


def test_execution_metrics_average_duration():
    database = Database(":memory:")

    database.save_execution(
        request="Request 1",
        agent="kubernetes",
        status="success",
        telemetry={
            "duration_ms": 100.0,
        },
    )

    database.save_execution(
        request="Request 2",
        agent="docker",
        status="success",
        telemetry={
            "duration_ms": 200.0,
        },
    )

    database.save_execution(
        request="Request 3",
        agent="terraform",
        status="success",
        telemetry={
            "duration_ms": 300.0,
        },
    )

    metrics = database.get_execution_metrics()

    assert metrics["average_duration_ms"] == 200.0

    database.close()


def test_execution_metrics_recent_failures():
    database = Database(":memory:")

    database.save_execution(
        request="Successful request",
        agent="kubernetes",
        status="success",
    )

    database.save_execution(
        request="Failed Docker build",
        agent="docker",
        status="failed",
        telemetry={
            "execution_id": "failure-1",
            "error": "Docker build failed",
        },
    )

    metrics = database.get_execution_metrics()

    assert len(metrics["recent_failures"]) == 1

    failure = metrics["recent_failures"][0]

    assert failure["execution_id"] == "failure-1"
    assert failure["request"] == "Failed Docker build"
    assert failure["agent"] == "docker"
    assert failure["status"] == "failed"
    assert failure["error"] == "Docker build failed"

    database.close()


def test_execution_metrics_limits_recent_failures_to_ten():
    database = Database(":memory:")

    for index in range(12):
        database.save_execution(
            request=f"Failed request {index}",
            agent="kubernetes",
            status="failed",
            telemetry={
                "execution_id": f"failure-{index}",
                "error": f"Failure {index}",
            },
        )

    metrics = database.get_execution_metrics()

    failures = metrics["recent_failures"]

    assert len(failures) == 10

    assert failures[0]["execution_id"] == "failure-11"
    assert failures[-1]["execution_id"] == "failure-2"

    database.close()