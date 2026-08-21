from src.safety.guardrails import SafetyGuardrails


def test_safe_request_is_allowed():
    guardrails = SafetyGuardrails()

    result = guardrails.evaluate(
        "Check Kubernetes pod health"
    )

    assert result["allowed"] is True
    assert result["action"] == "execute"
    assert result["risk"] == "low"


def test_destructive_request_is_blocked():
    guardrails = SafetyGuardrails()

    result = guardrails.evaluate(
        "kubectl delete production pods"
    )

    assert result["allowed"] is False
    assert result["action"] == "block"
    assert result["risk"] == "high"


def test_terraform_destroy_is_blocked():
    guardrails = SafetyGuardrails()

    result = guardrails.evaluate(
        "Run terraform destroy on production"
    )

    assert result["allowed"] is False
    assert result["action"] == "block"
    assert result["risk"] == "high"


def test_deployment_requires_review():
    guardrails = SafetyGuardrails()

    result = guardrails.evaluate(
        "Deploy the new application version"
    )

    assert result["allowed"] is False
    assert result["action"] == "review"
    assert result["risk"] == "medium"


def test_policy_review_is_respected():
    guardrails = SafetyGuardrails()

    policy_result = {
        "action": "review",
        "confidence": 0.65,
    }

    result = guardrails.evaluate(
        "Check application status",
        policy_result
    )

    assert result["allowed"] is False
    assert result["action"] == "review"
    assert result["risk"] == "medium"


def test_policy_escalation_is_respected():
    guardrails = SafetyGuardrails()

    policy_result = {
        "action": "escalate",
        "confidence": 0.0,
    }

    result = guardrails.evaluate(
        "Investigate unusual application behavior",
        policy_result
    )

    assert result["allowed"] is False
    assert result["action"] == "escalate"
    assert result["risk"] == "medium"


def test_empty_request_is_blocked():
    guardrails = SafetyGuardrails()

    result = guardrails.evaluate("")

    assert result["allowed"] is False
    assert result["action"] == "block"
    assert result["risk"] == "high"