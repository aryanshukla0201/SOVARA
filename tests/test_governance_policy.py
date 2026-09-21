from app.governance.models import Policy, RiskLevel
from app.governance.policy import PolicyEngine
from app.tools.registry import ToolSpec


def make_tool(**overrides) -> ToolSpec:
    values = {
        "tool_name": "TestTool",
        "capability": "test",
        "input_schema": {},
        "output_schema": {},
        "risk_level": "low",
        "permissions": ["local_files"],
        "execution_method": "local",
        "timeout_seconds": 30,
        "enabled": True,
    }
    values.update(overrides)
    return ToolSpec(**values)


def test_policy_engine_allows_permitted_tool():
    policy = Policy(
        allowed_tools=frozenset({"TestTool"}),
        allowed_permissions=frozenset({"local_files"}),
        allowed_execution_methods=frozenset({"local"}),
    )

    decision = PolicyEngine().evaluate(make_tool(), policy)

    assert decision.allowed is True
    assert decision.reason == "tool permitted by policy"


def test_policy_engine_denies_disabled_policy():
    policy = Policy(enabled=False)

    decision = PolicyEngine().evaluate(make_tool(), policy)

    assert decision.allowed is False
    assert decision.reason == "policy is disabled"


def test_policy_engine_denies_disabled_tool():
    decision = PolicyEngine().evaluate(
        make_tool(enabled=False),
        Policy(),
    )

    assert decision.allowed is False
    assert "disabled" in decision.reason


def test_policy_engine_denies_explicitly_denied_tool():
    policy = Policy(
        denied_tools=frozenset({"TestTool"}),
    )

    decision = PolicyEngine().evaluate(make_tool(), policy)

    assert decision.allowed is False
    assert "denied by policy" in decision.reason


def test_policy_engine_denies_tool_not_in_allow_list():
    policy = Policy(
        allowed_tools=frozenset({"OtherTool"}),
    )

    decision = PolicyEngine().evaluate(make_tool(), policy)

    assert decision.allowed is False
    assert "not permitted by policy" in decision.reason


def test_policy_engine_denies_unauthorized_execution_method():
    policy = Policy(
        allowed_execution_methods=frozenset({"sandbox"}),
    )

    decision = PolicyEngine().evaluate(make_tool(), policy)

    assert decision.allowed is False
    assert "execution method local is not permitted" in decision.reason


def test_policy_engine_denies_unauthorized_permission():
    policy = Policy(
        allowed_permissions=frozenset({"local_documents"}),
    )

    decision = PolicyEngine().evaluate(make_tool(), policy)

    assert decision.allowed is False
    assert "local_files" in decision.reason


def test_policy_engine_denies_excessive_risk():
    policy = Policy(
        max_risk_level=RiskLevel.LOW,
    )

    decision = PolicyEngine().evaluate(
        make_tool(risk_level="medium"),
        policy,
    )

    assert decision.allowed is False
    assert "exceeds policy maximum" in decision.reason


def test_policy_engine_denies_excessive_timeout():
    policy = Policy(max_timeout_seconds=30)

    decision = PolicyEngine().evaluate(
        make_tool(timeout_seconds=31),
        policy,
    )

    assert decision.allowed is False
    assert "exceeds policy maximum" in decision.reason


def test_policy_engine_denies_unknown_risk():
    decision = PolicyEngine().evaluate(
        make_tool(risk_level="unknown"),
        Policy(),
    )

    assert decision.allowed is False
    assert "unknown risk level" in decision.reason


def test_policy_engine_denies_non_positive_timeout():
    decision = PolicyEngine().evaluate(
        make_tool(timeout_seconds=0),
        Policy(),
    )

    assert decision.allowed is False
    assert "greater than zero" in decision.reason


def test_policy_engine_requires_approval_for_configured_risk():
    policy = Policy(
        max_risk_level=RiskLevel.HIGH,
        approval_required_for_risk=RiskLevel.HIGH,
    )

    decision = PolicyEngine().evaluate(
        make_tool(risk_level="high"),
        policy,
    )

    assert decision.allowed is False
    assert "requires approval" in decision.reason


def test_empty_allow_lists_do_not_deny_by_themselves():
    decision = PolicyEngine().evaluate(
        make_tool(),
        Policy(),
    )

    assert decision.allowed is True
