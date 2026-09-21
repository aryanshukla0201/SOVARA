from __future__ import annotations

from dataclasses import dataclass, field

from app.planner.models import PlanStep
from app.tools.registry import ToolRegistry, ToolSpec


@dataclass
class ToolSelectionResult:
    selected_tools: list[ToolSpec] = field(default_factory=list)
    rejected_tools: dict[str, str] = field(default_factory=dict)

    @property
    def tool_names(self) -> list[str]:
        return [tool.tool_name for tool in self.selected_tools]


class ToolSelector:
    def __init__(self, registry: ToolRegistry | None = None) -> None:
        self.registry = registry or ToolRegistry()

    def select_for_capability(
        self,
        capability: str,
        *,
        task_type: str | None = None,
        required_permissions: list[str] | None = None,
    ) -> ToolSelectionResult:
        if not capability.strip():
            raise ValueError("Capability cannot be empty.")

        required_permissions = required_permissions or []

        candidates = self.registry.get_tools_for_capability(
            capability
        )

        selected: list[ToolSpec] = []
        rejected: dict[str, str] = {}

        for tool in candidates:
            reason = self._rejection_reason(
                tool,
                task_type=task_type,
                required_permissions=required_permissions,
            )

            if reason is None:
                selected.append(tool)
            else:
                rejected[tool.tool_name] = reason

        return ToolSelectionResult(
            selected_tools=selected,
            rejected_tools=rejected,
        )

    def select_for_step(
        self,
        step: PlanStep,
        *,
        task_type: str | None = None,
    ) -> ToolSelectionResult:
        if not step.tool_name.strip():
            raise ValueError(
                f"Step {step.step_id} has no tool name."
            )

        try:
            tool = self.registry.get(step.tool_name)
        except KeyError:
            return ToolSelectionResult(
                selected_tools=[],
                rejected_tools={
                    step.tool_name: "Unknown tool."
                },
            )

        reason = self._rejection_reason(
            tool,
            task_type=task_type,
            required_permissions=[],
        )

        if reason is not None:
            return ToolSelectionResult(
                selected_tools=[],
                rejected_tools={
                    tool.tool_name: reason
                },
            )

        return ToolSelectionResult(
            selected_tools=[tool],
        )

    @staticmethod
    def _rejection_reason(
        tool: ToolSpec,
        *,
        task_type: str | None,
        required_permissions: list[str],
    ) -> str | None:
        if not tool.enabled:
            return "Tool is disabled."

        if (
            task_type
            and tool.allowed_task_types
            and task_type not in tool.allowed_task_types
        ):
            return (
                f"Tool is not allowed for task type: "
                f"{task_type}"
            )

        missing_permissions = [
            permission
            for permission in required_permissions
            if permission not in tool.permissions
        ]

        if missing_permissions:
            return (
                "Missing required permissions: "
                + ", ".join(missing_permissions)
            )

        return None
