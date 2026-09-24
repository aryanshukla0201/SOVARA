from typing import Any

import pytest

from app.planner.models import Plan
from app.planner.orchestrator import PlannerOrchestrator
from app.planner.replanner import FailureContext
from app.planner.planner import Planner
from app.planner.tool_selector import ToolSelector
from app.tools.registry import ToolRegistry


class FakeModel:
    def __init__(self, responses: list[dict[str, Any]]):
        self.responses = responses
        self.index = 0

    def generate_structured(
        self,
        prompt: str,
        schema: Any,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        response = self.responses[self.index]
        self.index += 1
        return response


class FakeGateway:
    def __init__(self, model: FakeModel):
        self.model = model

    def resolve(self, task_type: str, **kwargs: Any):
        return self.model


def make_orchestrator(
    responses: list[dict[str, Any]],
) -> PlannerOrchestrator:
    registry = ToolRegistry()
    model = FakeModel(responses)
    gateway = FakeGateway(model)

    planner = Planner(
        model_gateway=gateway,
        tool_registry=registry,
    )

    selector = ToolSelector(registry)

    replanner = __import__(
        "app.planner.replanner",
        fromlist=["Replanner"],
    ).Replanner(
        model_gateway=gateway,
        tool_registry=registry,
        validator=planner.validator,
    )

    return PlannerOrchestrator(
        planner=planner,
        tool_selector=selector,
        replanner=replanner,
    )


def test_create_plan_integrates_planner_and_selector():
    orchestrator = make_orchestrator(
        [
            {
                "goal": "Analyze CSV",
                "steps": [
                    {
                        "step_id": "step_1",
                        "tool_name": "CSVAnalyzer",
                    }
                ],
            }
        ]
    )

    result = orchestrator.create_plan(
        "Analyze this CSV"
    )

    assert isinstance(result.plan, Plan)
    assert result.selected_tools == ["CSVAnalyzer"]


def test_create_plan_deduplicates_tools():
    orchestrator = make_orchestrator(
        [
            {
                "goal": "Analyze",
                "steps": [
                    {
                        "step_id": "step_1",
                        "tool_name": "CSVAnalyzer",
                    },
                    {
                        "step_id": "step_2",
                        "tool_name": "CSVAnalyzer",
                    },
                ],
            }
        ]
    )

    result = orchestrator.create_plan("Analyze data")

    assert result.selected_tools == ["CSVAnalyzer"]


def test_create_plan_rejects_unavailable_tool():
    orchestrator = make_orchestrator(
        [
            {
                "goal": "Analyze",
                "steps": [
                    {
                        "step_id": "step_1",
                        "tool_name": "UnknownTool",
                    }
                ],
            }
        ]
    )

    with pytest.raises(ValueError, match="Invalid plan"):
        orchestrator.create_plan("Analyze")


def test_replan_integrates_replanner_and_selector():
    orchestrator = make_orchestrator(
        [
            {
                "goal": "Analyze",
                "steps": [
                    {
                        "step_id": "replacement",
                        "tool_name": "DocumentRetriever",
                    }
                ],
            }
        ]
    )

    original = Plan(
        goal="Analyze",
        steps=[
            __import__(
                "app.planner.models",
                fromlist=["PlanStep"],
            ).PlanStep(
                "step_1",
                "CSVAnalyzer",
            )
        ],
    )

    result = orchestrator.replan(
        original,
        FailureContext(
            failed_step_id="step_1",
            failure_reason="CSV failed",
        ),
    )

    assert result.selected_tools == [
        "DocumentRetriever"
    ]
    assert result.plan.steps[0].tool_name == (
        "DocumentRetriever"
    )
