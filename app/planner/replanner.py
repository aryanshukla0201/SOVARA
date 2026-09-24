from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.models.gateway import ModelGateway
from app.planner.models import Plan, PlanStep
from app.planner.validator import PlanValidator
from app.tools.registry import ToolRegistry
from app.governance.budget import ResourceBudgetGovernor


@dataclass
class FailureContext:
    failed_step_id: str
    failure_reason: str
    completed_step_ids: list[str] = field(default_factory=list)
    attempt: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class Replanner:
    def __init__(
        self,
        model_gateway: ModelGateway | None = None,
        tool_registry: ToolRegistry | None = None,
        validator: PlanValidator | None = None,
        max_attempts: int = 3,
        budget_governor: ResourceBudgetGovernor | None = None,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1.")

        self.model_gateway = model_gateway or ModelGateway()
        self.tool_registry = tool_registry or ToolRegistry()
        self.validator = validator or PlanValidator(
            self.tool_registry
        )
        self.max_attempts = max_attempts
        self.budget_governor = budget_governor
        if budget_governor is not None:
            self.model_gateway = model_gateway or ModelGateway(
                budget_governor=budget_governor
            )

    def replan(
        self,
        plan: Plan,
        failure: FailureContext,
    ) -> Plan:
        if failure.attempt >= self.max_attempts:
            raise RuntimeError(
                "Maximum replanning attempts exceeded."
            )

        failed_step = plan.get_step(failure.failed_step_id)

        completed = set(failure.completed_step_ids)

        remaining_steps = [
            step
            for step in plan.steps
            if step.step_id not in completed
            and step.step_id != failure.failed_step_id
        ]

        if self.budget_governor is not None:
            self.budget_governor.reserve_repair_attempt()

        model = self.model_gateway.resolve("reasoning")

        prompt = self._build_prompt(
            plan=plan,
            failure=failure,
            failed_step=failed_step,
            remaining_steps=remaining_steps,
        )

        response = model.generate_structured(
            prompt=prompt,
            schema=self._schema(),
            system_prompt=self._system_prompt(),
        )

        replacement = self._parse_response(
            response=response,
            original_plan=plan,
            failure=failure,
            completed_step_ids=completed,
        )

        validation = self.validator.validate(replacement)
        validation.raise_if_invalid()

        return replacement

    def _build_prompt(
        self,
        *,
        plan: Plan,
        failure: FailureContext,
        failed_step: PlanStep,
        remaining_steps: list[PlanStep],
    ) -> str:
        available_tools = [
            {
                "tool_name": tool.tool_name,
                "capability": tool.capability,
                "description": tool.description,
                "input_schema": tool.input_schema,
                "output_schema": tool.output_schema,
            }
            for tool in self.tool_registry.list_tools()
            if tool.enabled
        ]

        return (
            "Repair the following execution plan after a step failure.\n\n"
            f"ORIGINAL GOAL:\n{plan.goal}\n\n"
            f"FAILED STEP:\n{failed_step.to_dict()}\n\n"
            f"FAILURE:\n{failure.failure_reason}\n\n"
            f"COMPLETED STEPS:\n{failure.completed_step_ids}\n\n"
            f"REMAINING STEPS:\n"
            f"{[step.to_dict() for step in remaining_steps]}\n\n"
            f"AVAILABLE TOOLS:\n{available_tools}\n\n"
            "Rules:\n"
            "1. Preserve completed work.\n"
            "2. Replace or repair the failed work.\n"
            "3. Do not create circular dependencies.\n"
            "4. Use only available tools.\n"
            "5. Keep the replacement plan minimal.\n"
            "6. Do not execute tools.\n"
        )

    @staticmethod
    def _system_prompt() -> str:
        return (
            "You are SOVARA's replanning engine. "
            "Recover from execution failures by producing "
            "a valid replacement plan. Preserve completed work "
            "and never execute tools."
        )

    @staticmethod
    def _schema() -> dict[str, Any]:
        return {
            "type": "object",
            "required": ["goal", "steps"],
            "properties": {
                "goal": {"type": "string"},
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["step_id", "tool_name"],
                        "properties": {
                            "step_id": {"type": "string"},
                            "tool_name": {"type": "string"},
                            "description": {"type": "string"},
                            "inputs": {"type": "object"},
                            "depends_on": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "metadata": {"type": "object"},
                        },
                    },
                },
                "metadata": {"type": "object"},
            },
        }

    @staticmethod
    def _parse_response(
        *,
        response: dict[str, Any],
        original_plan: Plan,
        failure: FailureContext,
        completed_step_ids: set[str],
    ) -> Plan:
        if not isinstance(response, dict):
            raise ValueError(
                "Replanner model must return a dictionary."
            )

        steps = [
            PlanStep(
                step_id=step["step_id"],
                tool_name=step["tool_name"],
                description=step.get("description", ""),
                inputs=step.get("inputs", {}),
                depends_on=step.get("depends_on", []),
                metadata=step.get("metadata", {}),
            )
            for step in response.get("steps", [])
        ]

        metadata = dict(original_plan.metadata)
        metadata.update(response.get("metadata", {}))
        metadata["replan_attempt"] = failure.attempt + 1
        metadata["failed_step_id"] = failure.failed_step_id

        return Plan(
            plan_id=original_plan.plan_id,
            task_id=original_plan.task_id,
            goal=response.get("goal", original_plan.goal),
            steps=steps,
            metadata=metadata,
        )
