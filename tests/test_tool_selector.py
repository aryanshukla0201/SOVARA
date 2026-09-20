from app.planner.models import PlanStep
from app.planner.tool_selector import ToolSelector
from app.tools.registry import ToolRegistry, ToolSpec


def make_registry() -> ToolRegistry:
    registry = ToolRegistry()

    registry.register(
        ToolSpec(
            tool_name="RestrictedAnalyzer",
            capability="data_analysis",
            input_schema={},
            output_schema={},
            allowed_task_types=["data_analysis"],
            description="Restricted data analyzer",
            permissions=["local_files", "data_read"],
            risk_level="medium",
            execution_method="local",
            timeout_seconds=30,
        )
    )

    registry.register(
        ToolSpec(
            tool_name="DisabledAnalyzer",
            capability="data_analysis",
            input_schema={},
            output_schema={},
            allowed_task_types=[],
            description="Disabled analyzer",
            enabled=False,
        )
    )

    return registry


def test_selects_tools_for_capability():
    selector = ToolSelector(make_registry())

    result = selector.select_for_capability(
        "data_analysis"
    )

    assert "CSVAnalyzer" in result.tool_names
    assert "RestrictedAnalyzer" in result.tool_names
    assert "DisabledAnalyzer" not in result.tool_names


def test_empty_capability_is_rejected():
    selector = ToolSelector(make_registry())

    try:
        selector.select_for_capability("   ")
        assert False
    except ValueError as exc:
        assert "Capability cannot be empty" in str(exc)


def test_disabled_tool_is_rejected():
    selector = ToolSelector(make_registry())

    result = selector.select_for_capability(
        "data_analysis"
    )

    assert result.rejected_tools["DisabledAnalyzer"] == (
        "Tool is disabled."
    )


def test_task_type_filter_is_respected():
    selector = ToolSelector(make_registry())

    result = selector.select_for_capability(
        "data_analysis",
        task_type="image_analysis",
    )

    assert "RestrictedAnalyzer" not in result.tool_names
    assert (
        result.rejected_tools["RestrictedAnalyzer"]
        == "Tool is not allowed for task type: image_analysis"
    )


def test_task_type_filter_is_not_applied_when_tool_has_no_restrictions():
    registry = make_registry()

    registry.register(
        ToolSpec(
            tool_name="UnrestrictedAnalyzer",
            capability="data_analysis",
            input_schema={},
            output_schema={},
            allowed_task_types=[],
            description="Unrestricted analyzer",
        )
    )

    selector = ToolSelector(registry)

    result = selector.select_for_capability(
        "data_analysis",
        task_type="anything",
    )

    assert "UnrestrictedAnalyzer" in result.tool_names


def test_permission_filter():
    selector = ToolSelector(make_registry())

    result = selector.select_for_capability(
        "data_analysis",
        required_permissions=["data_read"],
    )

    assert "RestrictedAnalyzer" in result.tool_names


def test_missing_permission_rejects_tool():
    selector = ToolSelector(make_registry())

    result = selector.select_for_capability(
        "data_analysis",
        required_permissions=["network_access"],
    )

    assert "RestrictedAnalyzer" not in result.tool_names
    assert (
        result.rejected_tools["RestrictedAnalyzer"]
        == "Missing required permissions: network_access"
    )


def test_select_for_valid_step():
    selector = ToolSelector(make_registry())

    step = PlanStep(
        step_id="step_1",
        tool_name="CSVAnalyzer",
    )

    result = selector.select_for_step(step)

    assert result.tool_names == ["CSVAnalyzer"]
    assert result.rejected_tools == {}


def test_select_for_unknown_step_tool():
    selector = ToolSelector(make_registry())

    step = PlanStep(
        step_id="step_1",
        tool_name="UnknownTool",
    )

    result = selector.select_for_step(step)

    assert result.tool_names == []
    assert result.rejected_tools["UnknownTool"] == (
        "Unknown tool."
    )


def test_select_for_disabled_step_tool():
    selector = ToolSelector(make_registry())

    step = PlanStep(
        step_id="step_1",
        tool_name="DisabledAnalyzer",
    )

    result = selector.select_for_step(step)

    assert result.tool_names == []
    assert result.rejected_tools["DisabledAnalyzer"] == (
        "Tool is disabled."
    )


def test_select_for_restricted_step_tool():
    selector = ToolSelector(make_registry())

    step = PlanStep(
        step_id="step_1",
        tool_name="RestrictedAnalyzer",
    )

    result = selector.select_for_step(
        step,
        task_type="image_analysis",
    )

    assert result.tool_names == []
    assert (
        result.rejected_tools["RestrictedAnalyzer"]
        == "Tool is not allowed for task type: image_analysis"
    )
