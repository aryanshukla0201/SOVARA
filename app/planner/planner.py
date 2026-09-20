from __future__ import annotations

import json
from typing import Any

from app.models.gateway import ModelGateway
from app.planner.models import Plan, PlanStep
from app.planner.validator import PlanValidator
from app.state.task_state import TaskState
from app.tools.registry import ToolRegistry


class Planner:
    def __init__(
        self,
        model_gateway: ModelGateway | None = None,
        tool_registry: ToolRegistry | None = None,
        validator: PlanValidator | None = None,
    ) -> None:
        self.model_gateway = model_gateway or ModelGateway()
        self.tool_registry = tool_registry or ToolRegistry()
        self.validator = validator or PlanValidator(
            self.tool_registry
        )

    def create_plan(
        self,
        user_query: str,
        *,
        task_state: TaskState | None = None,
        context: dict[str, Any] | None = None,
    ) -> Plan:
        if not user_query.strip():
            raise ValueError("User query cannot be empty.")

        model = self.model_gateway.resolve("reasoning")

        prompt = self._build_prompt(
            user_query=user_query,
            task_state=task_state,
            context=context or {},
        )

        schema = self._plan_schema()

        response = model.generate_structured(
            prompt=prompt,
            schema=schema,
            system_prompt=self._system_prompt(),
        )

        plan = self._parse_plan_response(
            response=response,
            user_query=user_query,
            task_state=task_state,
        )

        validation = self.validator.validate(plan)
        validation.raise_if_invalid()

        return plan

    def _build_prompt(
        self,
        *,
        user_query: str,
        task_state: TaskState | None,
        context: dict[str, Any],
    ) -> str:
        tools = [
            {
                "tool_name": tool.tool_name,
                "capability": tool.capability,
                "description": tool.description,
                "input_schema": tool.input_schema,
                "output_schema": tool.output_schema,
                "allowed_task_types": tool.allowed_task_types,
            }
            for tool in self.tool_registry.list_tools()
            if tool.enabled
        ]

        task_context = (
            task_state.model_dump()
            if task_state is not None
            else {}
        )

        return (
            "Create a structured execution plan for the user request.\n\n"
            f"USER REQUEST:\n{user_query}\n\n"
            f"TASK STATE:\n{json.dumps(task_context, indent=2)}\n\n"
            f"ADDITIONAL CONTEXT:\n{json.dumps(context, indent=2)}\n\n"
            "AVAILABLE TOOLS:\n"
            f"{json.dumps(tools, indent=2)}\n\n"
            "Rules:\n"
            "1. Use only tools from AVAILABLE TOOLS.\n"
            "2. Every step must have a unique step_id.\n"
            "3. Use depends_on to express dependencies.\n"
            "4. Do not create circular dependencies.\n"
            "5. Keep the plan minimal and task-focused.\n"
            "6. Do not execute tools.\n"
            "7. Do not invent capabilities or tool names.\n"
        )

    @staticmethod
    def _system_prompt() -> str:
        return (
            "You are SOVARA's planning engine. "
            "Convert user requests into minimal, structured, "
            "dependency-aware plans. "
            "You design plans only; you never execute tools."
        )

    @staticmethod
    def _plan_schema() -> dict[str, Any]:
        return {
            "type": "object",
            "required": ["goal", "steps"],
            "properties": {
                "goal": {
                    "type": "string",
                },
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": [
                            "step_id",
                            "tool_name",
                        ],
                        "properties": {
                            "step_id": {
                                "type": "string",
                            },
                            "tool_name": {
                                "type": "string",
                            },
                            "description": {
                                "type": "string",
                            },
                            "inputs": {
                                "type": "object",
                            },
                            "depends_on": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                },
                            },
                            "metadata": {
                                "type": "object",
                            },
                        },
                    },
                },
                "metadata": {
                    "type": "object",
                },
            },
        }

    @staticmethod
    def _parse_plan_response(
        *,
        response: dict[str, Any],
        user_query: str,
        task_state: TaskState | None,
    ) -> Plan:
        if not isinstance(response, dict):
            raise ValueError(
                "Planner model must return a dictionary."
            )

        if "steps" not in response:
            raise ValueError(
                "Planner response is missing 'steps'."
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
            for step in response["steps"]
        ]

        metadata = dict(response.get("metadata", {}))

        if task_state is not None:
            metadata.setdefault(
                "task_type",
                task_state.task_type,
            )

        return Plan(
            goal=response.get("goal", user_query),
            steps=steps,
            metadata=metadata,
        )
