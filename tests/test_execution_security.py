from __future__ import annotations

from pathlib import Path

from app.execution.broker import ExecutionBroker, ExecutionRequest
from app.execution.policy import ExecutionPolicy, ExecutionPolicyEnforcer
from app.tools.registry import ToolRegistry, ToolSpec


def test_unknown_tool_cannot_execute():
    broker = ExecutionBroker()

    result = broker.execute(
        ExecutionRequest(
            tool_name="ArbitraryCommand",
            arguments={"command": "whoami"},
        )
    )

    assert not result.success
    assert "Unknown tool" in result.error


def test_disabled_tool_cannot_execute():
    registry = ToolRegistry()

    registry.register(
        ToolSpec(
            tool_name="DisabledTool",
            capability="test",
            input_schema={},
            output_schema={},
            enabled=False,
        )
    )

    broker = ExecutionBroker(registry=registry)

    result = broker.execute(
        ExecutionRequest(
            tool_name="DisabledTool",
            arguments={},
        )
    )

    assert not result.success
    assert "disabled" in result.error.lower()


def test_network_permission_is_rejected():
    spec = ToolSpec(
        tool_name="NetworkTool",
        capability="network",
        input_schema={},
        output_schema={},
        permissions=["internet"],
    )

    errors = ExecutionPolicyEnforcer().validate(spec)

    assert any("internet" in error for error in errors)


def test_remote_execution_method_is_rejected():
    spec = ToolSpec(
        tool_name="RemoteTool",
        capability="remote",
        input_schema={},
        output_schema={},
        execution_method="remote",
    )

    errors = ExecutionPolicyEnforcer().validate(spec)

    assert any("remote" in error for error in errors)


def test_critical_tool_is_rejected():
    spec = ToolSpec(
        tool_name="CriticalTool",
        capability="dangerous",
        input_schema={},
        output_schema={},
        risk_level="critical",
    )

    errors = ExecutionPolicyEnforcer().validate(spec)

    assert any("Risk level" in error for error in errors)


def test_excessive_timeout_is_rejected():
    spec = ToolSpec(
        tool_name="SlowTool",
        capability="test",
        input_schema={},
        output_schema={},
        timeout_seconds=121,
    )

    errors = ExecutionPolicyEnforcer().validate(spec)

    assert any("Timeout exceeds policy maximum" in error for error in errors)


def test_absolute_input_path_is_rejected():
    from app.execution.validation import ExecutionRequestValidator

    errors = ExecutionRequestValidator().validate(
        {
            "code": "print(1)",
            "input_files": [str(Path.cwd() / "secret.txt")],
        }
    )

    assert any("Absolute input path" in error for error in errors)


def test_parent_traversal_input_path_is_rejected():
    from app.execution.validation import ExecutionRequestValidator

    errors = ExecutionRequestValidator().validate(
        {
            "code": "print(1)",
            "input_files": ["..\\secret.txt"],
        }
    )

    assert any("Parent traversal" in error for error in errors)


def test_absolute_output_path_is_rejected():
    from app.execution.validation import ExecutionRequestValidator

    errors = ExecutionRequestValidator().validate(
        {
            "code": "print(1)",
            "output_files": [str(Path.cwd() / "result.txt")],
        }
    )

    assert any("Absolute output path" in error for error in errors)


def test_nested_output_path_is_rejected():
    from app.execution.validation import ExecutionRequestValidator

    errors = ExecutionRequestValidator().validate(
        {
            "code": "print(1)",
            "output_files": ["nested\\result.txt"],
        }
    )

    assert any("Nested output path" in error for error in errors)


def test_code_length_limit_is_enforced():
    from app.execution.validation import ExecutionRequestValidator

    errors = ExecutionRequestValidator().validate(
        {
            "code": "x" * (
                ExecutionRequestValidator.MAX_CODE_LENGTH + 1
            ),
        }
    )

    assert any("maximum length" in error for error in errors)


def test_input_file_count_limit_is_enforced():
    from app.execution.validation import ExecutionRequestValidator

    errors = ExecutionRequestValidator().validate(
        {
            "code": "print(1)",
            "input_files": [
                f"file_{index}.txt"
                for index in range(
                    ExecutionRequestValidator.MAX_INPUT_FILES + 1
                )
            ],
        }
    )

    assert any("too many input files" in error for error in errors)


def test_output_file_count_limit_is_enforced():
    from app.execution.validation import ExecutionRequestValidator

    errors = ExecutionRequestValidator().validate(
        {
            "code": "print(1)",
            "output_files": [
                f"file_{index}.txt"
                for index in range(
                    ExecutionRequestValidator.MAX_OUTPUT_FILES + 1
                )
            ],
        }
    )

    assert any("too many output files" in error for error in errors)
