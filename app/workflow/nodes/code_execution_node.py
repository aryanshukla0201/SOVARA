from __future__ import annotations

import uuid

from app.services.code_sandbox import CodeSandbox


class CodeExecutionNode:
    def __init__(self, sandbox=None, telemetry=None):
        self.sandbox = sandbox or CodeSandbox(telemetry=telemetry)

    def run(self, code: str) -> dict:
        result = self.sandbox.execute(code)

        return {
            "evidence_id": f"code_{uuid.uuid4().hex[:8]}",
            "evidence_type": "code_execution_result",
            "tool_used": "CodeSandbox",
            "success": result.get("success", False),
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
            "return_code": result.get("return_code", -1),
            "timeout": result.get("timeout", False),
            "docker_error": result.get("docker_error", False),
            "validation_error": result.get("validation_error", False),
        }
    