from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.execution.default_handlers import execute_csv_analyzer
from app.execution.handlers import ToolExecutionHandlers
from app.execution.policy import ExecutionPolicyEnforcer
from app.execution.validation import ExecutionRequestValidator
from app.governance.audit import AuditEvent, AuditEventType
from app.governance.models import Policy
from app.governance.observability import Observability
from app.governance.policy import PolicyEngine
from app.services.code_sandbox import CodeSandbox
from app.tools.registry import ToolRegistry


@dataclass
class ExecutionRequest:
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    task_id: str = ""


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
        governance_policy: Policy | None = None,
        policy_engine: PolicyEngine | None = None,
        observability: Observability | None = None,
    ) -> None:
        self.registry = registry or ToolRegistry()
        self.sandbox = sandbox or CodeSandbox()
        self.validator = validator or ExecutionRequestValidator()
        self.handlers = handlers or self._build_default_handlers()
        self.policy = policy or ExecutionPolicyEnforcer()
        self.governance_policy = governance_policy or Policy()
        self.policy_engine = policy_engine or PolicyEngine()
        self.observability = observability or Observability()

    @staticmethod
    def _build_default_handlers() -> ToolExecutionHandlers:
        handlers = ToolExecutionHandlers()

        handlers.register(
            "CSVAnalyzer",
            execute_csv_analyzer,
        )

        return handlers

    def _record(
        self,
        request: ExecutionRequest,
        event_type: str,
        *,
        action: str = "",
        decision: str = "",
        reason: str = "",
        tool_name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.observability.record(
            AuditEvent.create(
                event_id=str(uuid4()),
                task_id=request.task_id,
                event_type=event_type,
                tool_name=tool_name or request.tool_name,
                action=action,
                decision=decision,
                reason=reason,
                metadata=metadata,
            )
        )

    def execute(
        self,
        request: ExecutionRequest,
    ) -> ExecutionResult:
        try:
            spec = self.registry.get(request.tool_name)
        except KeyError:
            reason = f"Unknown tool: {request.tool_name}"
            self._record(
                request,
                AuditEventType.POLICY_DENIED,
                action="execute",
                decision="deny",
                reason=reason,
            )
            return ExecutionResult(
                tool_name=request.tool_name,
                success=False,
                error=reason,
            )

        governance_decision = self.policy_engine.evaluate(
            spec,
            self.governance_policy,
        )

        if not governance_decision.allowed:
            self._record(
                request,
                AuditEventType.POLICY_DENIED,
                action="execute",
                decision="deny",
                reason=governance_decision.reason,
            )
            return ExecutionResult(
                tool_name=request.tool_name,
                success=False,
                error=governance_decision.reason,
            )

        self._record(
            request,
            AuditEventType.POLICY_ALLOWED,
            action="execute",
            decision="allow",
            reason=governance_decision.reason,
        )

        policy_errors = self.policy.validate(spec)

        if policy_errors:
            error = "; ".join(policy_errors)
            self._record(
                request,
                AuditEventType.EXECUTION_FAILED,
                action="execute",
                decision="deny",
                reason=error,
            )
            return ExecutionResult(
                tool_name=request.tool_name,
                success=False,
                error=error,
            )

        self._record(
            request,
            AuditEventType.EXECUTION_STARTED,
            action="execute",
            decision="allow",
        )

        if request.tool_name == self.SANDBOX_TOOL:
            result = self._execute_sandbox(request)
        elif not self.handlers.has_handler(request.tool_name):
            result = ExecutionResult(
                tool_name=request.tool_name,
                success=False,
                error=(
                    "No secure execution handler registered for "
                    f"tool: {request.tool_name}"
                ),
            )
        else:
            result = self._execute_registered_tool(request)

        self._record(
            request,
            (
                AuditEventType.EXECUTION_COMPLETED
                if result.success
                else AuditEventType.EXECUTION_FAILED
            ),
            action="execute",
            decision="allow" if result.success else "deny",
            reason=result.error,
        )

        return result

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
