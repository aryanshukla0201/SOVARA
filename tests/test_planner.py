from typing import Any

import pytest

from app.planner.models import Plan
from app.planner.planner import Planner
from app.state.task_state import TaskState
from app.tools.registry import ToolRegistry


class FakeModel:
    name = "fake-reasoning-model"

    def __init__(self, response: dict[str, Any]):
        self.response = response
        self.calls = []

    def generate_structured(
        self,
        prompt: str,
        schema: Any,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "prompt": prompt,
                "schema": schema,
                "system_prompt": system_prompt,
            }
        )
        return self.response


class FakeGateway:
    def __init__(self, model: FakeModel):
        self.model = model
        self.requested_capability = None

    def resolve(self, task_type: str, **kwargs: Any) -> FakeModel:
        self.requested_capability = task_type
        return self.model


def test_planner_creates_valid_plan():
    model = FakeModel(
        {
            "goal": "Analyze a CSV",
            "steps": [
                {
                    "step_id": "step_1",
                    "tool_name": "CSVAnalyzer",
                    "description": "Analyze the CSV data",
                    "inputs": {"path": "data.csv"},
                    "depends_on": [],
                }
            ],
        }
    )

    gateway = FakeGateway(model)
    planner = Planner(
        model_gateway=gateway,
        tool_registry=ToolRegistry(),
    )

    plan = planner.create_plan(
        "Analyze this CSV"
    )

    assert isinstance(plan, Plan)
    assert plan.goal == "Analyze a CSV"
    assert len(plan.steps) == 1
    assert plan.steps[0].tool_name == "CSVAnalyzer"
    assert gateway.requested_capability == "reasoning"


def test_planner_supports_dependencies():
    model = FakeModel(
        {
            "goal": "Retrieve and analyze",
            "steps": [
                {
                    "step_id": "step_1",
                    "tool_name": "DocumentRetriever",
                    "description": "Retrieve evidence",
                },
                {
                    "step_id": "step_2",
                    "tool_name": "CSVAnalyzer",
                    "description": "Analyze data",
                    "depends_on": ["step_1"],
                },
            ],
        }
    )

    planner = Planner(
        model_gateway=FakeGateway(model),
        tool_registry=ToolRegistry(),
    )

    plan = planner.create_plan(
        "Retrieve evidence and analyze data"
    )

    assert plan.steps[1].depends_on == ["step_1"]


def test_planner_rejects_unknown_tool():
    model = FakeModel(
        {
            "goal": "Do something",
            "steps": [
                {
                    "step_id": "step_1",
                    "tool_name": "UnknownTool",
                }
            ],
        }
    )

    planner = Planner(
        model_gateway=FakeGateway(model),
        tool_registry=ToolRegistry(),
    )

    with pytest.raises(ValueError, match="Invalid plan"):
        planner.create_plan("Do something")


def test_planner_rejects_circular_plan():
    model = FakeModel(
        {
            "goal": "Circular",
            "steps": [
                {
                    "step_id": "step_1",
                    "tool_name": "CSVAnalyzer",
                    "depends_on": ["step_2"],
                },
                {
                    "step_id": "step_2",
                    "tool_name": "DocumentRetriever",
                    "depends_on": ["step_1"],
                },
            ],
        }
    )

    planner = Planner(
        model_gateway=FakeGateway(model),
        tool_registry=ToolRegistry(),
    )

    with pytest.raises(ValueError, match="Invalid plan"):
        planner.create_plan("Create a circular plan")


def test_planner_rejects_empty_query():
    model = FakeModel(
        {
            "goal": "unused",
            "steps": [],
        }
    )

    planner = Planner(
        model_gateway=FakeGateway(model),
        tool_registry=ToolRegistry(),
    )

    with pytest.raises(ValueError, match="User query cannot be empty"):
        planner.create_plan("   ")


def test_planner_passes_task_state_to_prompt():
    model = FakeModel(
        {
            "goal": "Analyze image",
            "steps": [
                {
                    "step_id": "step_1",
                    "tool_name": "VisionAnalyzer",
                }
            ],
        }
    )

    planner = Planner(
        model_gateway=FakeGateway(model),
        tool_registry=ToolRegistry(),
    )

    task_state = TaskState(
        intent="image_analysis",
        requires_vision=True,
        required_capabilities=["vision"],
    )

    planner.create_plan(
        "Analyze this image",
        task_state=task_state,
    )

    prompt = model.calls[0]["prompt"]

    assert "image_analysis" in prompt
    assert "VisionAnalyzer" in prompt
    assert "vision" in prompt


def test_planner_uses_only_enabled_tools():
    registry = ToolRegistry()

    registry.tools["DisabledTool"] = registry.tools[
        "CSVAnalyzer"
    ].__class__(
        tool_name="DisabledTool",
        capability="data_analysis",
        input_schema={},
        output_schema={},
        allowed_task_types=[],
        description="Disabled test tool",
        enabled=False,
    )

    model = FakeModel(
        {
            "goal": "Analyze",
            "steps": [
                {
                    "step_id": "step_1",
                    "tool_name": "CSVAnalyzer",
                }
            ],
        }
    )

    planner = Planner(
        model_gateway=FakeGateway(model),
        tool_registry=registry,
    )

    planner.create_plan("Analyze data")

    prompt = model.calls[0]["prompt"]

    assert "DisabledTool" not in prompt
    assert "CSVAnalyzer" in prompt


def test_planner_preserves_model_metadata():
    model = FakeModel(
        {
            "goal": "Analyze",
            "steps": [
                {
                    "step_id": "step_1",
                    "tool_name": "CSVAnalyzer",
                    "metadata": {
                        "reason": "primary data source"
                    },
                }
            ],
            "metadata": {
                "planner_version": "p4.4"
            },
        }
    )

    planner = Planner(
        model_gateway=FakeGateway(model),
        tool_registry=ToolRegistry(),
    )

    plan = planner.create_plan("Analyze data")

    assert plan.metadata["planner_version"] == "p4.4"
    assert (
        plan.steps[0].metadata["reason"]
        == "primary data source"
    )
