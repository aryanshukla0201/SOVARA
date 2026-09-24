import pytest

from app.governance.models import (
    ExecutionMethod,
    Policy,
    RiskLevel,
)


def test_policy_defaults_are_serializable():
    policy = Policy()

    assert policy.name == "default"
    assert policy.enabled is True
    assert policy.max_risk_level == RiskLevel.MEDIUM
    assert policy.max_timeout_seconds == 120


def test_policy_accepts_governance_configuration():
    policy = Policy(
        name="restricted",
        allowed_tools=frozenset({"CSVAnalyzer"}),
        denied_tools=frozenset({"CodeSandbox"}),
        allowed_permissions=frozenset({"local_files"}),
        allowed_execution_methods=frozenset({
            ExecutionMethod.LOCAL.value,
        }),
        max_risk_level=RiskLevel.LOW,
        max_timeout_seconds=60,
        approval_required_for_risk=RiskLevel.HIGH,
    )

    assert "CSVAnalyzer" in policy.allowed_tools
    assert "CodeSandbox" in policy.denied_tools
    assert "local_files" in policy.allowed_permissions
    assert "local" in policy.allowed_execution_methods
    assert policy.max_risk_level == RiskLevel.LOW
    assert policy.approval_required_for_risk == RiskLevel.HIGH


def test_policy_to_dict_is_json_compatible():
    policy = Policy(
        name="restricted",
        allowed_tools=frozenset({"CSVAnalyzer", "DocumentRetriever"}),
        denied_tools=frozenset({"CodeSandbox"}),
        allowed_permissions=frozenset({"local_files"}),
        allowed_execution_methods=frozenset({"local"}),
        max_risk_level=RiskLevel.HIGH,
        max_timeout_seconds=60,
        approval_required_for_risk=RiskLevel.HIGH,
    )

    payload = policy.to_dict()

    assert payload == {
        "name": "restricted",
        "enabled": True,
        "allowed_tools": [
            "CSVAnalyzer",
            "DocumentRetriever",
        ],
        "denied_tools": ["CodeSandbox"],
        "allowed_permissions": ["local_files"],
        "allowed_execution_methods": ["local"],
        "max_risk_level": "high",
        "max_timeout_seconds": 60,
        "approval_required_for_risk": "high",
    }


def test_policy_round_trip():
    policy = Policy(
        name="restricted",
        enabled=False,
        allowed_tools=frozenset({"CSVAnalyzer"}),
        denied_tools=frozenset({"CodeSandbox"}),
        allowed_permissions=frozenset({"local_files"}),
        allowed_execution_methods=frozenset({"local"}),
        max_risk_level=RiskLevel.LOW,
        max_timeout_seconds=60,
        approval_required_for_risk=RiskLevel.HIGH,
    )

    restored = Policy.from_dict(policy.to_dict())

    assert restored == policy


def test_policy_rejects_empty_name():
    with pytest.raises(ValueError, match="Policy name"):
        Policy(name="")


def test_policy_rejects_non_positive_timeout():
    with pytest.raises(
        ValueError,
        match="max_timeout_seconds",
    ):
        Policy(max_timeout_seconds=0)


def test_policy_rejects_low_approval_threshold():
    with pytest.raises(
        ValueError,
        match="approval_required_for_risk",
    ):
        Policy(approval_required_for_risk=RiskLevel.LOW)


def test_policy_is_immutable():
    policy = Policy()

    with pytest.raises(Exception):
        policy.name = "changed"
