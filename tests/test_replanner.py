from typing import Any

import pytest

from app.planner.models import Plan, PlanStep
from app.planner.replanner import FailureContext, Replanner
from app.tools.registry import ToolRegistry


class FakeModel:
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
        self.calls.append(prompt)
        return self.response


class FakeGateway:
    def __init__(self, model):
        self.model = model
        self.requested = None

    def resolve(self, task_type: str, **kwargs):
        self.requested = task_type
        return self.model


def base_plan() -> Plan:
    return Plan(
        plan_id="plan_1",
        task_id="task_1",
        goal="Analyze data",
        steps=[
            PlanStep(
                "step_1",
                "DocumentRetriever",
            ),
            PlanStep(
                "step_2",
                "CSVAnalyzer",
                depends_on=["step_1"],
            ),
            PlanStep(
                "step_3",
                "VisionAnalyzer",
                depends_on=["step_2"],
            ),
        ],
    )


def test_replanner_creates_replacement_plan():
    model = FakeModel(
        {
            "goal": "Analyze data",
            "steps": [
                {
                    "step_id": "step_1",
                    "tool_name": "DocumentRetriever",
                },
                {
                    "step_id": "step_2_retry",
                    "tool_name": "DocumentRetriever",
                    "depends_on": ["step_1"],
                },
                {
                    "step_id": "step_3",
                    "tool_name": "VisionAnalyzer",
                    "depends_on": ["step_2_retry"],
                },
            ],
        }
    )

    gateway = FakeGateway(model)
    replanner = Replanner(
        model_gateway=gateway,
        tool_registry=ToolRegistry(),
    )

    result = replanner.replan(
        base_plan(),
        FailureContext(
            failed_step_id="step_2",
            failure_reason="CSV parsing failed",
            completed_step_ids=["step_1"],
            attempt=0,
        ),
    )

    assert result.plan_id == "plan_1"
    assert result.task_id == "task_1"
    assert result.metadata["replan_attempt"] == 1
    assert result.metadata["failed_step_id"] == "step_2"
    assert gateway.requested == "reasoning"


def test_replanner_preserves_completed_step():
    model = FakeModel(
        {
            "goal": "Analyze data",
            "steps": [
                {
                    "step_id": "step_1",
                    "tool_name": "DocumentRetriever",
                },
                {
                    "step_id": "step_2_retry",
                    "tool_name": "CSVAnalyzer",
                    "depends_on": ["step_1"],
                },
            ],
        }
    )

    replanner = Replanner(
        model_gateway=FakeGateway(model),
        tool_registry=ToolRegistry(),
    )

    result = replanner.replan(
        base_plan(),
        FailureContext(
            failed_step_id="step_2",
            failure_reason="temporary failure",
            completed_step_ids=["step_1"],
        ),
    )

    assert result.steps[0].step_id == "step_1"


def test_replanner_rejects_unknown_tool():
    model = FakeModel(
        {
            "goal": "Analyze data",
            "steps": [
                {
                    "step_id": "replacement",
                    "tool_name": "UnknownTool",
                }
            ],
        }
    )

    replanner = Replanner(
        model_gateway=FakeGateway(model),
        tool_registry=ToolRegistry(),
    )

    with pytest.raises(ValueError, match="Invalid plan"):
        replanner.replan(
            base_plan(),
            FailureContext(
                failed_step_id="step_2",
                failure_reason="failure",
            ),
        )


def test_replanner_rejects_circular_plan():
    model = FakeModel(
        {
            "goal": "Analyze",
            "steps": [
                {
                    "step_id": "a",
                    "tool_name": "CSVAnalyzer",
                    "depends_on": ["b"],
                },
                {
                    "step_id": "b",
                    "tool_name": "DocumentRetriever",
                    "depends_on": ["a"],
                },
            ],
        }
    )

    replanner = Replanner(
        model_gateway=FakeGateway(model),
        tool_registry=ToolRegistry(),
    )

    with pytest.raises(ValueError, match="Invalid plan"):
        replanner.replan(
            base_plan(),
            FailureContext(
                failed_step_id="step_2",
                failure_reason="failure",
            ),
        )


def test_replanner_enforces_attempt_limit():
    replanner = Replanner(
        model_gateway=FakeGateway(FakeModel({})),
        tool_registry=ToolRegistry(),
        max_attempts=2,
    )

    with pytest.raises(
        RuntimeError,
        match="Maximum replanning attempts exceeded",
    ):
        replanner.replan(
            base_plan(),
            FailureContext(
                failed_step_id="step_2",
                failure_reason="failure",
                attempt=2,
            ),
        )


def test_replanner_rejects_unknown_failed_step():
    replanner = Replanner(
        model_gateway=FakeGateway(FakeModel({})),
        tool_registry=ToolRegistry(),
    )

    with pytest.raises(KeyError):
        replanner.replan(
            base_plan(),
            FailureContext(
                failed_step_id="missing",
                failure_reason="failure",
            ),
        )


def test_replanner_increments_attempt_metadata():
    model = FakeModel(
        {
            "goal": "Analyze",
            "steps": [
                {
                    "step_id": "replacement",
                    "tool_name": "CSVAnalyzer",
                }
            ],
        }
    )

    replanner = Replanner(
        model_gateway=FakeGateway(model),
        tool_registry=ToolRegistry(),
    )

    result = replanner.replan(
        base_plan(),
        FailureContext(
            failed_step_id="step_2",
            failure_reason="failure",
            attempt=2,
        ),
    )

    assert result.metadata["replan_attempt"] == 3


def test_replanner_prompt_contains_failure_context():
    model = FakeModel(
        {
            "goal": "Analyze",
            "steps": [
                {
                    "step_id": "replacement",
                    "tool_name": "CSVAnalyzer",
                }
            ],
        }
    )

    replanner = Replanner(
        model_gateway=FakeGateway(model),
        tool_registry=ToolRegistry(),
    )

    replanner.replan(
        base_plan(),
        FailureContext(
            failed_step_id="step_2",
            failure_reason="permission denied",
            completed_step_ids=["step_1"],
        ),
    )

    prompt = model.calls[0]

    assert "permission denied" in prompt
    assert "step_2" in prompt
    assert "step_1" in prompt
