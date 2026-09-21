from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.planner.models import Plan, PlanStep
from app.planner.planner import Planner
from app.planner.replanner import FailureContext, Replanner
from app.planner.tool_selector import ToolSelector
from app.state.task_state import TaskState


@dataclass
class PlanningResult:
    plan: Plan
    selected_tools: list[str] = field(default_factory=list)


class PlannerOrchestrator:
    def __init__(
        self,
        planner: Planner | None = None,
        tool_selector: ToolSelector | None = None,
        replanner: Replanner | None = None,
    ) -> None:
        self.planner = planner or Planner()
        self.tool_selector = tool_selector or ToolSelector(
            self.planner.tool_registry
        )
        self.replanner = replanner or Replanner(
            model_gateway=self.planner.model_gateway,
            tool_registry=self.planner.tool_registry,
            validator=self.planner.validator,
        )

    def create_plan(
        self,
        user_query: str,
        *,
        task_state: TaskState | None = None,
        context: dict[str, Any] | None = None,
    ) -> PlanningResult:
        plan = self.planner.create_plan(
            user_query,
            task_state=task_state,
            context=context,
        )

        selected_tools = self._select_plan_tools(
            plan,
            task_state=task_state,
        )

        return PlanningResult(
            plan=plan,
            selected_tools=selected_tools,
        )

    def replan(
        self,
        plan: Plan,
        failure: FailureContext,
        *,
        task_state: TaskState | None = None,
    ) -> PlanningResult:
        replacement = self.replanner.replan(
            plan,
            failure,
        )

        selected_tools = self._select_plan_tools(
            replacement,
            task_state=task_state,
        )

        return PlanningResult(
            plan=replacement,
            selected_tools=selected_tools,
        )

    def _select_plan_tools(
        self,
        plan: Plan,
        *,
        task_state: TaskState | None,
    ) -> list[str]:
        task_type = (
            task_state.task_type
            if task_state is not None
            else None
        )

        selected: list[str] = []
        seen: set[str] = set()

        for step in plan.steps:
            result = self.tool_selector.select_for_step(
                step,
                task_type=task_type,
            )

            if not result.selected_tools:
                reason = result.rejected_tools.get(
                    step.tool_name,
                    "Tool selection failed.",
                )
                raise ValueError(
                    f"Tool selection failed for "
                    f"{step.step_id}: {reason}"
                )

            for tool in result.selected_tools:
                if tool.tool_name not in seen:
                    selected.append(tool.tool_name)
                    seen.add(tool.tool_name)

        return selected
