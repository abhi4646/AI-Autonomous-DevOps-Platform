from src.ai.decision_engine import DecisionEngine


def test_kubernetes_and_monitoring_routing():
    engine = DecisionEngine()

    ticket = {
        "summary": "Kubernetes deployment unhealthy",
        "description": "Pods are failing health checks",
    }

    result = engine.decide_agents(ticket)

    assert "kubernetes" in result["recommended_agents"]
    assert "monitoring" in result["recommended_agents"]


def test_terraform_routing():
    engine = DecisionEngine()

    ticket = {
        "summary": "Terraform infrastructure failure",
        "description": "Cloud plan failed",
    }

    result = engine.decide_agents(ticket)

    assert "terraform" in result["recommended_agents"]


def test_github_routing():
    engine = DecisionEngine()

    ticket = {
        "summary": "GitHub pull request failed",
        "description": "Repository branch requires investigation",
    }

    result = engine.decide_agents(ticket)

    assert "github" in result["recommended_agents"]


def test_multiple_agents():
    engine = DecisionEngine()

    ticket = {
        "summary": "Kubernetes deployment created with Terraform",
        "description": "Monitoring alert triggered for the cluster",
    }

    result = engine.decide_agents(ticket)

    assert "kubernetes" in result["recommended_agents"]
    assert "terraform" in result["recommended_agents"]
    assert "monitoring" in result["recommended_agents"]


def test_unknown_request_uses_safe_defaults():
    engine = DecisionEngine()

    ticket = {
        "summary": "Something unusual happened",
        "description": "Needs investigation",
    }

    result = engine.decide_agents(ticket)

    assert result["recommended_agents"] == ["github", "monitoring"]


def test_empty_ticket():
    engine = DecisionEngine()

    result = engine.decide_agents({})

    assert result["recommended_agents"] == []