from pathlib import Path

from app.execution.broker import (
    ExecutionBroker,
    ExecutionRequest,
)
from app.tools.registry import ToolRegistry, ToolSpec


class FakeSandbox:
    def __init__(self, result=None):
        self.calls = []
        self.result = result or {
            "success": True,
            "stdout": "hello",
            "stderr": "",
            "return_code": 0,
            "timeout": False,
            "docker_error": False,
            "validation_error": False,
            "output_files": [],
        }

    def execute(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def make_registry() -> ToolRegistry:
    registry = ToolRegistry()

    registry.register(
        ToolSpec(
            tool_name="CodeSandbox",
            capability="code_execution",
            input_schema={
                "code": "string",
                "input_files": "array",
                "output_files": "array",
                "output_directory": "string",
            },
            output_schema={"result": "object"},
            allowed_task_types=[],
            description="Execute Python inside the secure sandbox.",
            risk_level="medium",
            permissions=["sandbox_execution"],
            execution_method="sandbox",
            timeout_seconds=10,
        )
    )

    return registry


def test_unknown_tool_is_rejected():
    broker = ExecutionBroker(
        registry=make_registry(),
        sandbox=FakeSandbox(),
    )

    result = broker.execute(
        ExecutionRequest(
            tool_name="UnknownTool",
        )
    )

    assert not result.success
    assert "Unknown tool" in result.error


def test_disabled_tool_is_rejected():
    registry = make_registry()

    registry.register(
        ToolSpec(
            tool_name="DisabledTool",
            capability="test",
            input_schema={},
            output_schema={},
            enabled=False,
        )
    )

    broker = ExecutionBroker(
        registry=registry,
        sandbox=FakeSandbox(),
    )

    result = broker.execute(
        ExecutionRequest(
            tool_name="DisabledTool",
        )
    )

    assert not result.success
    assert "disabled" in result.error


def test_unknown_execution_handler_is_rejected():
    registry = make_registry()

    registry.register(
        ToolSpec(
            tool_name="UnimplementedTool",
            capability="test",
            input_schema={},
            output_schema={},
        )
    )

    broker = ExecutionBroker(
        registry=registry,
        sandbox=FakeSandbox(),
    )

    result = broker.execute(
        ExecutionRequest(
            tool_name="UnimplementedTool",
        )
    )

    assert not result.success
    assert "No secure execution handler" in result.error


def test_empty_sandbox_code_is_rejected():
    broker = ExecutionBroker(
        registry=make_registry(),
        sandbox=FakeSandbox(),
    )

    result = broker.execute(
        ExecutionRequest(
            tool_name="CodeSandbox",
            arguments={"code": "   "},
        )
    )

    assert not result.success
    assert "non-empty code" in result.error


def test_sandbox_executes_through_secure_boundary():
    sandbox = FakeSandbox()

    broker = ExecutionBroker(
        registry=make_registry(),
        sandbox=sandbox,
    )

    result = broker.execute(
        ExecutionRequest(
            tool_name="CodeSandbox",
            arguments={
                "code": "print('hello')",
            },
        )
    )

    assert result.success
    assert result.result["stdout"] == "hello"
    assert len(sandbox.calls) == 1
    assert sandbox.calls[0]["code"] == "print('hello')"


def test_sandbox_arguments_are_forwarded():
    sandbox = FakeSandbox()

    broker = ExecutionBroker(
        registry=make_registry(),
        sandbox=sandbox,
    )

    broker.execute(
        ExecutionRequest(
            tool_name="CodeSandbox",
            arguments={
                "code": "print(1)",
                "input_files": ["input.csv"],
                "output_files": ["result.csv"],
                "output_directory": "outputs",
            },
        )
    )

    assert sandbox.calls[0] == {
        "code": "print(1)",
        "input_files": [str(Path("input.csv"))],
        "output_files": ["result.csv"],
        "output_directory": "outputs",
    }


def test_invalid_input_files_type_is_rejected():
    broker = ExecutionBroker(
        registry=make_registry(),
        sandbox=FakeSandbox(),
    )

    result = broker.execute(
        ExecutionRequest(
            tool_name="CodeSandbox",
            arguments={
                "code": "print(1)",
                "input_files": "input.csv",
            },
        )
    )

    assert not result.success
    assert "input_files must be a list" in result.error


def test_invalid_output_files_type_is_rejected():
    broker = ExecutionBroker(
        registry=make_registry(),
        sandbox=FakeSandbox(),
    )

    result = broker.execute(
        ExecutionRequest(
            tool_name="CodeSandbox",
            arguments={
                "code": "print(1)",
                "output_files": "result.csv",
            },
        )
    )

    assert not result.success
    assert "output_files must be a list" in result.error


def test_sandbox_failure_is_preserved():
    sandbox = FakeSandbox(
        {
            "success": False,
            "stdout": "",
            "stderr": "execution failed",
            "return_code": 1,
            "timeout": False,
            "docker_error": False,
            "validation_error": False,
            "output_files": [],
        }
    )

    broker = ExecutionBroker(
        registry=make_registry(),
        sandbox=sandbox,
    )

    result = broker.execute(
        ExecutionRequest(
            tool_name="CodeSandbox",
            arguments={"code": "raise Exception()"},
        )
    )

    assert not result.success
    assert result.error == "execution failed"
    assert result.result["return_code"] == 1

def test_csv_analyzer_is_executed_through_broker():
    broker = ExecutionBroker(
        registry=make_registry(),
    )

    result = broker.execute(
        ExecutionRequest(
            tool_name="CSVAnalyzer",
            arguments={
                "csv_source": "name,value\nA,10\nB,20\n",
                "user_query": "average value",
            },
        )
    )

    assert result.success
    assert result.result["analysis_type"] == "average"
    assert result.result["metric"] == "value"
    assert result.result["average"] == 15.0


def test_unhandled_registered_tool_is_rejected():
    broker = ExecutionBroker(
        registry=make_registry(),
    )

    result = broker.execute(
        ExecutionRequest(
            tool_name="DocumentRetriever",
            arguments={},
        )
    )

    assert not result.success
    assert "No secure execution handler" in result.error


def test_handler_cannot_be_used_for_unknown_tool():
    broker = ExecutionBroker(
        registry=make_registry(),
    )

    result = broker.execute(
        ExecutionRequest(
            tool_name="NotRegistered",
            arguments={},
        )
    )

    assert not result.success
    assert "Unknown tool" in result.error