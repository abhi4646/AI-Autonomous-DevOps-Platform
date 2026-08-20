from unittest.mock import MagicMock

from src.orchestrator.orchestrator import Orchestrator


def make_agent(name, result=None):
    agent = MagicMock()
    agent.name = name
    agent.execute.return_value = result or {"status": "ok"}
    return agent


def test_orchestrator_runs_agent():
    orchestrator = Orchestrator()
    agent = make_agent("docker")

    orchestrator.register_agent(agent)

    result = orchestrator.run()

    assert "docker" in result
    agent.execute.assert_called_once()


def test_routes_kubernetes_request():
    orchestrator = Orchestrator()
    agent = make_agent("kubernetes", {"status": "healthy"})

    orchestrator.register_agent(agent)

    result = orchestrator.route("Check Kubernetes cluster health")

    assert result["status"] == "routed"
    assert result["agent"] == "kubernetes"
    assert result["result"]["status"] == "healthy"
    agent.execute.assert_called_once()


def test_routes_jira_request():
    orchestrator = Orchestrator()
    agent = make_agent("jira", {"issue": "KAN-4"})

    orchestrator.register_agent(agent)

    result = orchestrator.route("Check Jira issue KAN-4")

    assert result["status"] == "routed"
    assert result["agent"] == "jira"
    assert result["result"]["issue"] == "KAN-4"
    agent.execute.assert_called_once()


def test_returns_no_route_for_unknown_request():
    orchestrator = Orchestrator()

    result = orchestrator.route("Make me a coffee")

    assert result["status"] == "no_route"
    assert result["message"] == "No suitable agent found"


def test_returns_agent_unavailable():
    orchestrator = Orchestrator()

    result = orchestrator.route("Build the Docker image")

    assert result["status"] == "agent_unavailable"
    assert result["agent"] == "docker"


def test_rejects_empty_request():
    orchestrator = Orchestrator()

    try:
        orchestrator.route("")
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert str(exc) == "Request cannot be empty"