from __future__ import annotations

from typing import Any, Callable


class ToolExecutionHandlers:
    """Explicit allowlisted handlers for registered tools."""

    def __init__(self) -> None:
        self._handlers: dict[str, Callable[..., dict[str, Any]]] = {}

    def register(
        self,
        tool_name: str,
        handler: Callable[..., dict[str, Any]],
    ) -> None:
        if not tool_name.strip():
            raise ValueError("tool_name must not be empty")

        if tool_name in self._handlers:
            raise ValueError(
                f"Handler already registered: {tool_name}"
            )

        self._handlers[tool_name] = handler

    def has_handler(self, tool_name: str) -> bool:
        return tool_name in self._handlers

    def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            handler = self._handlers[tool_name]
        except KeyError as exc:
            raise KeyError(
                f"No execution handler registered for tool: {tool_name}"
            ) from exc

        return handler(**arguments)