from app.planner.models import Plan, PlanStep
from app.planner.validator import PlanValidator
from app.tools.registry import ToolRegistry


def make_validator() -> PlanValidator:
    return PlanValidator(ToolRegistry())


def test_valid_linear_plan():
    plan = Plan(
        goal="Analyze a document",
        steps=[
            PlanStep(
                step_id="step_1",
                tool_name="DocumentRetriever",
            ),
            PlanStep(
                step_id="step_2",
                tool_name="CSVAnalyzer",
                depends_on=["step_1"],
            ),
        ],
    )

    result = make_validator().validate(plan)

    assert result.valid
    assert result.errors == []


def test_empty_goal_is_invalid():
    plan = Plan(goal="")

    result = make_validator().validate(plan)

    assert not result.valid
    assert "Plan goal cannot be empty." in result.errors


def test_empty_plan_is_invalid():
    plan = Plan(goal="Analyze data")

    result = make_validator().validate(plan)

    assert not result.valid
    assert "Plan must contain at least one step." in result.errors


def test_duplicate_step_ids_are_invalid():
    plan = Plan(
        goal="Test",
        steps=[
            PlanStep("step_1", "CSVAnalyzer"),
            PlanStep("step_1", "DocumentRetriever"),
        ],
    )

    result = make_validator().validate(plan)

    assert not result.valid
    assert "Duplicate step ID: step_1" in result.errors


def test_missing_dependency_is_invalid():
    plan = Plan(
        goal="Test",
        steps=[
            PlanStep(
                "step_1",
                "CSVAnalyzer",
                depends_on=["missing"],
            ),
        ],
    )

    result = make_validator().validate(plan)

    assert not result.valid
    assert (
        "Step step_1 depends on unknown step: missing"
        in result.errors
    )


def test_self_dependency_is_invalid():
    plan = Plan(
        goal="Test",
        steps=[
            PlanStep(
                "step_1",
                "CSVAnalyzer",
                depends_on=["step_1"],
            ),
        ],
    )

    result = make_validator().validate(plan)

    assert not result.valid
    assert (
        "Step step_1 cannot depend on itself."
        in result.errors
    )


def test_cycle_is_invalid():
    plan = Plan(
        goal="Test",
        steps=[
            PlanStep(
                "step_1",
                "CSVAnalyzer",
                depends_on=["step_3"],
            ),
            PlanStep(
                "step_2",
                "DocumentRetriever",
                depends_on=["step_1"],
            ),
            PlanStep(
                "step_3",
                "VisionAnalyzer",
                depends_on=["step_2"],
            ),
        ],
    )

    result = make_validator().validate(plan)

    assert not result.valid
    assert "Plan contains a dependency cycle." in result.errors


def test_unknown_tool_is_invalid():
    plan = Plan(
        goal="Test",
        steps=[
            PlanStep(
                "step_1",
                "NonExistentTool",
            ),
        ],
    )

    result = make_validator().validate(plan)

    assert not result.valid
    assert "Unknown tool: NonExistentTool" in result.errors


def test_raise_if_invalid():
    plan = Plan(
        goal="Test",
        steps=[
            PlanStep(
                "step_1",
                "NonExistentTool",
            ),
        ],
    )

    result = make_validator().validate(plan)

    try:
        result.raise_if_invalid()
        assert False
    except ValueError as exc:
        assert "Invalid plan" in str(exc)


def test_valid_dag_with_branching():
    plan = Plan(
        goal="Analyze multiple sources",
        steps=[
            PlanStep(
                "step_1",
                "DocumentRetriever",
            ),
            PlanStep(
                "step_2",
                "CSVAnalyzer",
            ),
            PlanStep(
                "step_3",
                "VisionAnalyzer",
            ),
            PlanStep(
                "step_4",
                "DocumentRetriever",
                depends_on=["step_1", "step_2", "step_3"],
            ),
        ],
    )

    result = make_validator().validate(plan)

    assert result.valid
    assert result.errors == []
