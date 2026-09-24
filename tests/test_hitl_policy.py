from app.hitl.policy import (
    ApprovalPolicy,
    ApprovalPolicyEngine,
)


def test_high_risk_requires_approval():
    policy = ApprovalPolicy(
        risk_levels_requiring_approval=frozenset({"high", "critical"})
    )

    decision = ApprovalPolicyEngine().evaluate(
        risk_level="high",
        policy=policy,
    )

    assert decision.approval_required is True
    assert decision.reason == "human approval is required"
    assert "risk_level" in decision.triggers


def test_low_risk_does_not_require_approval():
    policy = ApprovalPolicy()

    decision = ApprovalPolicyEngine().evaluate(
        risk_level="low",
        policy=policy,
    )

    assert decision.approval_required is False


def test_sensitive_permission_requires_approval():
    policy = ApprovalPolicy(
        sensitive_permissions=frozenset({"external_write"})
    )

    decision = ApprovalPolicyEngine().evaluate(
        risk_level="low",
        permissions={"external_write"},
        policy=policy,
    )

    assert decision.approval_required is True
    assert "sensitive_permission" in decision.triggers


def test_destructive_action_requires_approval():
    policy = ApprovalPolicy(
        destructive_actions=frozenset({"delete"})
    )

    decision = ApprovalPolicyEngine().evaluate(
        risk_level="low",
        action="delete",
        policy=policy,
    )

    assert decision.approval_required is True
    assert "destructive_action" in decision.triggers


def test_external_side_effect_requires_approval():
    policy = ApprovalPolicy(external_side_effects=True)

    decision = ApprovalPolicyEngine().evaluate(
        risk_level="low",
        external_side_effect=True,
        policy=policy,
    )

    assert decision.approval_required is True
    assert "external_side_effect" in decision.triggers


def test_explicit_policy_requirement_requires_approval():
    policy = ApprovalPolicy(approval_required=True)

    decision = ApprovalPolicyEngine().evaluate(
        risk_level="low",
        policy=policy,
    )

    assert decision.approval_required is True
    assert "policy_requires_approval" in decision.triggers


def test_disabled_policy_does_not_require_approval():
    policy = ApprovalPolicy(enabled=False, approval_required=True)

    decision = ApprovalPolicyEngine().evaluate(
        risk_level="critical",
        policy=policy,
    )

    assert decision.approval_required is False
    assert decision.reason == "approval policy is disabled"


def test_multiple_triggers_are_preserved():
    policy = ApprovalPolicy(
        risk_levels_requiring_approval=frozenset({"high"}),
        sensitive_permissions=frozenset({"external_write"}),
        destructive_actions=frozenset({"delete"}),
        external_side_effects=True,
    )

    decision = ApprovalPolicyEngine().evaluate(
        risk_level="high",
        permissions={"external_write"},
        action="delete",
        external_side_effect=True,
        policy=policy,
    )

    assert decision.approval_required is True
    assert decision.triggers == (
        "risk_level",
        "sensitive_permission",
        "destructive_action",
        "external_side_effect",
    )
