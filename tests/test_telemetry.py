from src.core.telemetry import ExecutionTelemetry


def test_telemetry_start():
    telemetry = ExecutionTelemetry.start(
        request="Check Kubernetes pods",
        agent="kubernetes",
    )

    assert telemetry.execution_id
    assert telemetry.request == "Check Kubernetes pods"
    assert telemetry.agent == "kubernetes"
    assert telemetry.status == "running"
    assert telemetry.started_at is not None
    assert telemetry.finished_at is None


def test_telemetry_finish():
    telemetry = ExecutionTelemetry.start(
        request="Run Terraform plan",
        agent="terraform",
    )

    telemetry.finish(
        status="success",
        duration_ms=125.5,
    )

    assert telemetry.status == "success"
    assert telemetry.finished_at is not None
    assert telemetry.duration_ms == 125.5
    assert telemetry.error is None


def test_telemetry_records_error():
    telemetry = ExecutionTelemetry.start(
        request="Build Docker image",
        agent="docker",
    )

    telemetry.finish(
        status="failed",
        duration_ms=50.0,
        error="Docker build failed",
    )

    assert telemetry.status == "failed"
    assert telemetry.error == "Docker build failed"


def test_telemetry_to_dict():
    telemetry = ExecutionTelemetry.start(
        request="Check monitoring",
        agent="monitoring",
        command=["health-check"],
        metadata={"source": "api"},
    )

    result = telemetry.to_dict()

    assert result["execution_id"]
    assert result["request"] == "Check monitoring"
    assert result["agent"] == "monitoring"
    assert result["command"] == ["health-check"]
    assert result["metadata"] == {
        "source": "api"
    }