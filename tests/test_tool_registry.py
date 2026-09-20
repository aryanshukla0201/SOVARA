import pytest

from app.tools.registry import ToolRegistry, ToolSpec


def test_default_tools_are_registered():
    registry = ToolRegistry()

    assert {
        "DocumentRetriever",
        "CSVAnalyzer",
        "VisionAnalyzer",
    } == {tool.tool_name for tool in registry.list_tools()}


def test_get_tool():
    registry = ToolRegistry()

    tool = registry.get("CSVAnalyzer")

    assert tool.tool_name == "CSVAnalyzer"
    assert tool.capability == "data_analysis"


def test_get_unknown_tool():
    registry = ToolRegistry()

    with pytest.raises(KeyError):
        registry.get("UnknownTool")


def test_capability_lookup():
    registry = ToolRegistry()

    tools = registry.get_tools_for_capability("vision_analysis")

    assert [tool.tool_name for tool in tools] == [
        "VisionAnalyzer"
    ]


def test_task_type_lookup():
    registry = ToolRegistry()

    tools = registry.get_allowed_tools("data_analysis")

    assert [tool.tool_name for tool in tools] == [
        "CSVAnalyzer"
    ]


def test_available_tools_only_returns_enabled_tools():
    registry = ToolRegistry()

    registry.register(
        ToolSpec(
            tool_name="DisabledTool",
            capability="testing",
            input_schema={},
            output_schema={},
            enabled=False,
        )
    )

    available = registry.get_available_tools()

    assert "DisabledTool" not in {
        tool.tool_name for tool in available
    }


def test_duplicate_registration_is_rejected():
    registry = ToolRegistry()

    with pytest.raises(ValueError):
        registry.register(
            ToolSpec(
                tool_name="CSVAnalyzer",
                capability="other",
                input_schema={},
                output_schema={},
            )
        )


def test_custom_tool_registration():
    registry = ToolRegistry()

    tool = ToolSpec(
        tool_name="Calculator",
        capability="calculation",
        description="Perform deterministic calculations.",
        input_schema={"type": "expression"},
        output_schema={"type": "number"},
        allowed_task_types=["calculation"],
        risk_level="low",
        permissions=["computation"],
        execution_method="local",
        timeout_seconds=10,
    )

    registry.register(tool)

    result = registry.get("Calculator")

    assert result is tool
    assert result.description == "Perform deterministic calculations."
    assert result.permissions == ["computation"]
    assert result.timeout_seconds == 10


@pytest.mark.parametrize(
    "field,value",
    [
        ("tool_name", ""),
        ("capability", ""),
        ("execution_method", ""),
    ],
)
def test_invalid_required_metadata(field, value):
    kwargs = {
        "tool_name": "TestTool",
        "capability": "testing",
        "input_schema": {},
        "output_schema": {},
    }
    kwargs[field] = value

    registry = ToolRegistry()

    with pytest.raises(ValueError):
        registry.register(ToolSpec(**kwargs))


def test_invalid_timeout_is_rejected():
    registry = ToolRegistry()

    with pytest.raises(ValueError):
        registry.register(
            ToolSpec(
                tool_name="TestTool",
                capability="testing",
                input_schema={},
                output_schema={},
                timeout_seconds=0,
            )
        )


@pytest.mark.parametrize(
    "risk_level",
    ["invalid", "", "extreme"],
)
def test_invalid_risk_level_is_rejected(risk_level):
    registry = ToolRegistry()

    with pytest.raises(ValueError):
        registry.register(
            ToolSpec(
                tool_name="TestTool",
                capability="testing",
                input_schema={},
                output_schema={},
                risk_level=risk_level,
            )
        )


def test_metadata_of_default_tools():
    registry = ToolRegistry()

    document = registry.get("DocumentRetriever")
    csv = registry.get("CSVAnalyzer")
    vision = registry.get("VisionAnalyzer")

    assert document.risk_level == "low"
    assert "local_documents" in document.permissions

    assert csv.risk_level == "low"
    assert "local_files" in csv.permissions

    assert vision.risk_level == "low"
    assert "local_images" in vision.permissions