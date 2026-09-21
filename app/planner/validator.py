from __future__ import annotations

from dataclasses import dataclass, field

from app.planner.models import Plan
from app.tools.registry import ToolRegistry


@dataclass
class PlanValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)

    def raise_if_invalid(self) -> None:
        if not self.valid:
            raise ValueError(
                "Invalid plan: " + "; ".join(self.errors)
            )


class PlanValidator:
    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def _tool_exists(self, tool_name: str) -> bool:
        try:
            self.registry.get(tool_name)
            return True
        except KeyError:
            return False

    def validate(self, plan: Plan) -> PlanValidationResult:
        errors: list[str] = []

        if not plan.goal.strip():
            errors.append("Plan goal cannot be empty.")

        if not plan.steps:
            errors.append("Plan must contain at least one step.")

        step_ids = [step.step_id for step in plan.steps]

        duplicates = {
            step_id
            for step_id in step_ids
            if step_ids.count(step_id) > 1
        }

        for step_id in sorted(duplicates):
            errors.append(f"Duplicate step ID: {step_id}")

        known_step_ids = set(step_ids)

        for step in plan.steps:
            if not step.step_id.strip():
                errors.append("Step ID cannot be empty.")

            if not step.tool_name.strip():
                errors.append(
                    f"Step {step.step_id or '<unknown>'} "
                    "has no tool name."
                )
            elif not self._tool_exists(step.tool_name):
                errors.append(
                    f"Unknown tool: {step.tool_name}"
                )

            if step.step_id in step.depends_on:
                errors.append(
                    f"Step {step.step_id} cannot depend on itself."
                )

            for dependency in step.depends_on:
                if dependency not in known_step_ids:
                    errors.append(
                        f"Step {step.step_id} depends on "
                        f"unknown step: {dependency}"
                    )

        if not errors and self._has_cycle(plan):
            errors.append("Plan contains a dependency cycle.")

        return PlanValidationResult(
            valid=not errors,
            errors=errors,
        )

    @staticmethod
    def _has_cycle(plan: Plan) -> bool:
        graph = {
            step.step_id: set(step.depends_on)
            for step in plan.steps
        }

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(step_id: str) -> bool:
            if step_id in visiting:
                return True

            if step_id in visited:
                return False

            visiting.add(step_id)

            for dependency in graph.get(step_id, set()):
                if visit(dependency):
                    return True

            visiting.remove(step_id)
            visited.add(step_id)

            return False

        return any(
            visit(step_id)
            for step_id in graph
        )
