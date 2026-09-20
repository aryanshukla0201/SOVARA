from __future__ import annotations

import pytest

from app.execution.handlers import ToolExecutionHandlers


def test_handler_can_be_registered_and_executed():
    handlers = ToolExecutionHandlers()

    handlers.register(
        "TestTool",
        lambda value: {"value": value},
    )

    assert handlers.has_handler("TestTool")

    result = handlers.execute(
        "TestTool",
        {"value": 42},
    )

    assert result == {"value": 42}


def test_duplicate_handler_registration_is_rejected():
    handlers = ToolExecutionHandlers()

    handlers.register(
        "TestTool",
        lambda: {},
    )

    with pytest.raises(ValueError, match="Handler already registered"):
        handlers.register(
            "TestTool",
            lambda: {},
        )


def test_unknown_handler_is_rejected():
    handlers = ToolExecutionHandlers()

    with pytest.raises(
        KeyError,
        match="No execution handler registered",
    ):
        handlers.execute(
            "MissingTool",
            {},
        )


def test_empty_handler_name_is_rejected():
    handlers = ToolExecutionHandlers()

    with pytest.raises(ValueError, match="tool_name"):
        handlers.register(
            "",
            lambda: {},
        )