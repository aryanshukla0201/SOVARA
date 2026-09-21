from app.planner.models import (
    Plan,
    PlanStatus,
    PlanStep,
    PlanStepStatus,
)


def test_plan_step_defaults():
    step = PlanStep(
        step_id="step_1",
        tool_name="CSVAnalyzer",
    )

    assert step.status == PlanStepStatus.PENDING
    assert step.inputs == {}
    assert step.depends_on == []
    assert step.metadata == {}


def test_plan_step_supports_dependencies():
    step = PlanStep(
        step_id="step_2",
        tool_name="Calculator",
        depends_on=["step_1"],
    )

    assert step.depends_on == ["step_1"]


def test_plan_generates_id():
    plan = Plan(goal="Analyze CSV")

    assert plan.plan_id
    assert plan.status == PlanStatus.PENDING


def test_plan_preserves_step_order():
    steps = [
        PlanStep("step_1", "DocumentRetriever"),
        PlanStep(
            "step_2",
            "CSVAnalyzer",
            depends_on=["step_1"],
        ),
    ]

    plan = Plan(
        goal="Analyze document",
        steps=steps,
    )

    assert [step.step_id for step in plan.steps] == [
        "step_1",
        "step_2",
    ]


def test_plan_get_step():
    step = PlanStep("step_1", "CSVAnalyzer")

    plan = Plan(
        goal="Analyze data",
        steps=[step],
    )

    assert plan.get_step("step_1") is step


def test_plan_get_unknown_step():
    plan = Plan(goal="Test")

    try:
        plan.get_step("missing")
        assert False
    except KeyError as exc:
        assert "missing" in str(exc)


def test_plan_serialization_round_trip():
    original = Plan(
        plan_id="plan_123",
        task_id="task_123",
        goal="Analyze report",
        steps=[
            PlanStep(
                step_id="step_1",
                tool_name="DocumentRetriever",
                description="Retrieve evidence",
                inputs={"query": "revenue"},
                metadata={"source": "planner"},
            ),
            PlanStep(
                step_id="step_2",
                tool_name="Calculator",
                description="Calculate growth",
                inputs={"expression": "10 / 5"},
                depends_on=["step_1"],
            ),
        ],
        metadata={"version": 1},
    )

    restored = Plan.from_dict(original.to_dict())

    assert restored.to_dict() == original.to_dict()


def test_step_status_serializes_as_string():
    step = PlanStep(
        step_id="step_1",
        tool_name="CSVAnalyzer",
        status=PlanStepStatus.COMPLETED,
    )

    data = step.to_dict()

    assert data["status"] == "completed"


def test_plan_status_serializes_as_string():
    plan = Plan(
        goal="Test",
        status=PlanStatus.RUNNING,
    )

    data = plan.to_dict()

    assert data["status"] == "running"
