from __future__ import annotations

from app.execution.policy import ExecutionPolicyEnforcer


def test_low_risk_local_tool_is_allowed():
    from app.tools.registry import ToolSpec

    spec = ToolSpec(
        tool_name="SafeTool",
        capability="test",
        input_schema={},
        output_schema={},
        risk_level="low",
        permissions=["local_files"],
        execution_method="local",
    )

    enforcer = ExecutionPolicyEnforcer()

    assert enforcer.is_allowed(spec)


def test_disabled_tool_is_rejected():
    from app.tools.registry import ToolSpec

    spec = ToolSpec(
        tool_name="DisabledTool",
        capability="test",
        input_schema={},
        output_schema={},
        enabled=False,
    )

    errors = ExecutionPolicyEnforcer().validate(spec)

    assert any("disabled" in error for error in errors)


def test_high_risk_tool_is_rejected_by_default():
    from app.tools.registry import ToolSpec

    spec = ToolSpec(
        tool_name="HighRiskTool",
        capability="test",
        input_schema={},
        output_schema={},
        risk_level="high",
    )

    errors = ExecutionPolicyEnforcer().validate(spec)

    assert any("Risk level" in error for error in errors)


def test_critical_risk_tool_is_rejected():
    from app.tools.registry import ToolSpec

    spec = ToolSpec(
        tool_name="CriticalTool",
        capability="test",
        input_schema={},
        output_schema={},
        risk_level="critical",
    )

    errors = ExecutionPolicyEnforcer().validate(spec)

    assert any("Risk level" in error for error in errors)


def test_unauthorized_permission_is_rejected():
    from app.tools.registry import ToolSpec

    spec = ToolSpec(
        tool_name="NetworkTool",
        capability="test",
        input_schema={},
        output_schema={},
        permissions=["internet"],
    )

    errors = ExecutionPolicyEnforcer().validate(spec)

    assert any("internet" in error for error in errors)


def test_unauthorized_execution_method_is_rejected():
    from app.tools.registry import ToolSpec

    spec = ToolSpec(
        tool_name="RemoteTool",
        capability="test",
        input_schema={},
        output_schema={},
        execution_method="remote",
    )

    errors = ExecutionPolicyEnforcer().validate(spec)

    assert any("remote" in error for error in errors)


def test_multiple_policy_violations_are_reported():
    from app.tools.registry import ToolSpec

    spec = ToolSpec(
        tool_name="DangerousTool",
        capability="test",
        input_schema={},
        output_schema={},
        risk_level="critical",
        permissions=["internet", "shell"],
        execution_method="remote",
    )

    errors = ExecutionPolicyEnforcer().validate(spec)

    assert len(errors) == 4

def test_timeout_within_policy_is_allowed():
    from app.tools.registry import ToolSpec

    spec = ToolSpec(
        tool_name="TimedTool",
        capability="test",
        input_schema={},
        output_schema={},
        timeout_seconds=60,
    )

    assert ExecutionPolicyEnforcer().is_allowed(spec)


def test_timeout_above_policy_is_rejected():
    from app.tools.registry import ToolSpec

    spec = ToolSpec(
        tool_name="SlowTool",
        capability="test",
        input_schema={},
        output_schema={},
        timeout_seconds=121,
    )

    errors = ExecutionPolicyEnforcer().validate(spec)

    assert any("Timeout exceeds policy maximum" in error for error in errors)


def test_zero_timeout_is_rejected():
    from app.tools.registry import ToolSpec

    spec = ToolSpec(
        tool_name="InvalidTimeoutTool",
        capability="test",
        input_schema={},
        output_schema={},
        timeout_seconds=0,
    )

    errors = ExecutionPolicyEnforcer().validate(spec)

    assert any("greater than zero" in error for error in errors)
