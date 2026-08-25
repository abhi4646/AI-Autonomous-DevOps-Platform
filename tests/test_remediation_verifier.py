from src.remediation.verifier import (
    RemediationVerifier,
)


def test_verifier_detects_full_recovery():
    verifier = RemediationVerifier()

    result = verifier.verify(
        before={
            "status": "unhealthy",
            "score": 30,
            "reasons": [
                "High failure rate",
            ],
        },
        after={
            "status": "healthy",
            "score": 95,
            "reasons": [],
        },
    )

    assert result["verified"] is True
    assert result["recovered"] is True
    assert result["outcome"] == "recovered"
    assert result["score_change"] == 65


def test_verifier_detects_improvement():
    verifier = RemediationVerifier()

    result = verifier.verify(
        before={
            "status": "unhealthy",
            "score": 30,
            "reasons": [
                "High failure rate",
            ],
        },
        after={
            "status": "degraded",
            "score": 65,
            "reasons": [
                "Failure rate still elevated",
            ],
        },
    )

    assert result["recovered"] is True
    assert result["outcome"] == "improved"
    assert result["score_change"] == 35


def test_verifier_detects_no_change():
    verifier = RemediationVerifier()

    result = verifier.verify(
        before={
            "status": "unhealthy",
            "score": 30,
            "reasons": [
                "Agent unavailable",
            ],
        },
        after={
            "status": "unhealthy",
            "score": 30,
            "reasons": [
                "Agent unavailable",
            ],
        },
    )

    assert result["recovered"] is False
    assert result["outcome"] == "unchanged"
    assert result["score_change"] == 0


def test_verifier_detects_failed_remediation():
    verifier = RemediationVerifier()

    result = verifier.verify(
        before={
            "status": "degraded",
            "score": 60,
            "reasons": [
                "Elevated errors",
            ],
        },
        after={
            "status": "unhealthy",
            "score": 25,
            "reasons": [
                "Critical failure rate",
            ],
        },
    )

    assert result["recovered"] is False
    assert result["outcome"] == "failed"
    assert result["score_change"] == -35


def test_verifier_handles_missing_fields():
    verifier = RemediationVerifier()

    result = verifier.verify(
        before={},
        after={},
    )

    assert result["verified"] is True
    assert result["recovered"] is False
    assert result["outcome"] == "unchanged"
    assert result["before_status"] == "unknown"
    assert result["after_status"] == "unknown"