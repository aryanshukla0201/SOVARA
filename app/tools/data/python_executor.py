from __future__ import annotations

from typing import Any


class PythonExecutor:
    def execute(self, expression: str) -> Any:
        local_scope: dict[str, Any] = {"__builtins__": __builtins__}
        return eval(expression, local_scope, local_scope)
