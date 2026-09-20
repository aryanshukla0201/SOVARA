from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.execution.default_handlers import execute_csv_analyzer
from app.execution.handlers import ToolExecutionHandlers
from app.execution.policy import ExecutionPolicyEnforcer
from app.execution.validation import ExecutionRequestValidator
from app.services.code_sandbox import CodeSandbox
from app.tools.registry import ToolRegistry


@dataclass
class ExecutionRequest:
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    tool_name: str
    success: bool
    result: dict[str, Any] = field(default_factory=dict)
    error: str = ""


class ExecutionBroker:
    SANDBOX_TOOL = "CodeSandbox"

    def __init__(
        self,
        registry: ToolRegistry | None = None,
        sandbox: CodeSandbox | None = None,
        validator: ExecutionRequestValidator | None = None,
        handlers: ToolExecutionHandlers | None = None,
        policy: ExecutionPolicyEnforcer | None = None,
    ) -> None:
        self.registry = registry or ToolRegistry()
        self.sandbox = sandbox or CodeSandbox()
        self.validator = validator or ExecutionRequestValidator()
        self.handlers = handlers or self._build_default_handlers()
        self.policy = policy or ExecutionPolicyEnforcer()

    @staticmethod
    def _build_default_handlers() -> ToolExecutionHandlers:
        handlers = ToolExecutionHandlers()

        handlers.register(
            "CSVAnalyzer",
            execute_csv_analyzer,
        )

        return handlers

    def execute(
        self,
        request: ExecutionRequest,
    ) -> ExecutionResult:
        try:
            spec = self.registry.get(request.tool_name)
        except KeyError:
            return ExecutionResult(
                tool_name=request.tool_name,
                success=False,
                error=f"Unknown tool: {request.tool_name}",
            )

        policy_errors = self.policy.validate(spec)

        if policy_errors:
            return ExecutionResult(
                tool_name=request.tool_name,
                success=False,
                error="; ".join(policy_errors),
            )

        if request.tool_name == self.SANDBOX_TOOL:
            return self._execute_sandbox(request)

        if not self.handlers.has_handler(request.tool_name):
            return ExecutionResult(
                tool_name=request.tool_name,
                success=False,
                error=(
                    "No secure execution handler registered for "
                    f"tool: {request.tool_name}"
                ),
            )

        return self._execute_registered_tool(request)

    def _execute_registered_tool(
        self,
        request: ExecutionRequest,
    ) -> ExecutionResult:
        try:
            result = self.handlers.execute(
                request.tool_name,
                request.arguments,
            )
        except Exception as exc:
            return ExecutionResult(
                tool_name=request.tool_name,
                success=False,
                result={},
                error=str(exc),
            )

        return ExecutionResult(
            tool_name=request.tool_name,
            success=True,
            result=result,
        )

    def _execute_sandbox(
        self,
        request: ExecutionRequest,
    ) -> ExecutionResult:
        arguments = request.arguments

        validation_errors = self.validator.validate(arguments)

        if validation_errors:
            error = "; ".join(validation_errors)

            if "code cannot be empty." in error:
                error = "non-empty code is not allowed."

            return ExecutionResult(
                tool_name=request.tool_name,
                success=False,
                result={},
                error=error,
            )

        result = self.sandbox.execute(
            code=arguments["code"],
            input_files=[
                str(Path(path))
                for path in arguments.get("input_files", [])
            ],
            output_files=arguments.get("output_files", []),
            output_directory=arguments.get("output_directory"),
        )

        return ExecutionResult(
            tool_name=request.tool_name,
            success=result.get("success", False),
            result=result,
            error=(
                ""
                if result.get("success", False)
                else result.get("stderr", "")
            ),
        )
