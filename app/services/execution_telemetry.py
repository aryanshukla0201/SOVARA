from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionTelemetry:
    """
    Request-scoped execution telemetry.

    Tracks SOVARA-owned model, tool, sandbox, and file execution.
    It does NOT claim that the entire computer made zero
    network traffic.
    """

    llm_calls: int = 0
    external_api_calls: int = 0
    network_calls: int = 0
    cloud_uploads: int = 0

    models_used: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    files_processed: int = 0

    sandbox_executions: int = 0
    sandbox_successes: int = 0
    sandbox_failures: int = 0
    sandbox_timeouts: int = 0

    execution_events: list[dict[str, Any]] = field(default_factory=list)

    local_inference: bool = True
    processing_location: str = "local"

    def record_llm_call(
        self,
        model_name: str,
        local: bool = True,
    ) -> None:
        self.llm_calls += 1

        if model_name and model_name not in self.models_used:
            self.models_used.append(model_name)

        if not local:
            self.external_api_calls += 1
            self.local_inference = False
            self.processing_location = "external"

    def record_external_api_call(self) -> None:
        self.external_api_calls += 1

    def record_network_call(self) -> None:
        self.network_calls += 1

    def record_cloud_upload(self) -> None:
        self.cloud_uploads += 1

    def record_tool(self, tool_name: str) -> None:
        if tool_name and tool_name not in self.tools_used:
            self.tools_used.append(tool_name)

    def record_sandbox_execution(
        self,
        *,
        success: bool,
        return_code: int,
        duration_ms: float | None = None,
        timeout: bool = False,
    ) -> None:
        self.record_tool("CodeSandbox")

        self.sandbox_executions += 1

        if timeout:
            self.sandbox_timeouts += 1
        elif success:
            self.sandbox_successes += 1
        else:
            self.sandbox_failures += 1

        self.execution_events.append(
            {
                "type": "sandbox_execution",
                "tool": "CodeSandbox",
                "success": success,
                "return_code": return_code,
                "duration_ms": duration_ms,
                "timeout": timeout,
            }
        )

    def record_file(self) -> None:
        self.files_processed += 1

    def summary(self) -> dict[str, Any]:
        return {
            "local_inference": self.local_inference,
            "processing_location": self.processing_location,
            "models_used": self.models_used,
            "llm_calls": self.llm_calls,
            "external_api_calls": self.external_api_calls,
            "network_calls": self.network_calls,
            "cloud_uploads": self.cloud_uploads,
            "files_processed": self.files_processed,
            "tools_used": self.tools_used,
            "sandbox_executions": self.sandbox_executions,
            "sandbox_successes": self.sandbox_successes,
            "sandbox_failures": self.sandbox_failures,
            "sandbox_timeouts": self.sandbox_timeouts,
            "execution_events": self.execution_events,
            "no_external_calls": (
                self.external_api_calls == 0
                and self.network_calls == 0
            ),
        }